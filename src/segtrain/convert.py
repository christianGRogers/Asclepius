"""Convert a case-per-directory dataset into an nnU-Net raw dataset.

Source layout (read-only, never modified). Either one binary mask per
structure::

    <data_root>/<case>/ct.nii.gz
    <data_root>/<case>/segmentations/<structure>.nii.gz

or a single integer label volume, which is what a case hand-labelled in Slicer
usually looks like::

    <data_root>/<case>/ct.nii.gz
    <data_root>/<case>/labels.nii.gz

The form is detected per case, so a dataset part-way through relabelling still
converts. For the second form the label set's ``source_values`` says which
integer means which structure; see ``segtrain.config.LabelSet``.

nnU-Net layout::

    <nnUNet_raw>/Dataset710_Coronary/imagesTr/<case>_0000.nii.gz
    <nnUNet_raw>/Dataset710_Coronary/labelsTr/<case>.nii.gz   one uint8 multilabel
    <nnUNet_raw>/Dataset710_Coronary/imagesTs/, labelsTs/     held-out test cases
    <nnUNet_raw>/Dataset710_Coronary/dataset.json

Two things make this cheap:

* **Merging shrinks the labels.** Separate gzipped masks are mostly header
  overhead and near-empty volume; the merged uint8 volume is a fraction of the
  size. Across TotalSegmentator's 1228 cases, 9.1 GB of masks become ~0.3 GB.
* **Images are linked, not copied.** A hardlink costs nothing and nnU-Net only
  needs the ``_0000`` filename convention. Copying would duplicate the whole
  image set once per task.
"""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Iterable, Sequence
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import nibabel as nib
import numpy as np

from .config import Config, TaskConfig
from .splits import SPLIT_TEST, CaseMeta

# Geometry agreement is checked as a physical displacement, not as an element-wise
# tolerance on the affine. Obliquely-acquired volumes in this dataset carry
# rotation terms that differ between the CT and its masks in the 5th decimal
# place -- pure float32 round-tripping through NIfTI headers. An element-wise
# atol flags those as mismatches even though the worst-case voxel displacement is
# ~0.02 mm, about 1/75th of a voxel. Comparing where the volume's corners
# actually land answers the question that matters: would using this mask shift
# anatomy relative to the image?
#
# 0.1 voxel is far tighter than any error that could affect training, while
# leaving three orders of magnitude of headroom over float32 noise.
GEOMETRY_TOLERANCE_VOXELS = 0.1

# How to resolve a voxel claimed by two structures. See resolve_overlap().
OVERLAP_SMALLER_WINS = "smaller_wins"
OVERLAP_LABEL_ORDER = "label_order"

# nnU-Net's image reader. This default is not cosmetic -- it is required for this
# dataset to train on all of its data.
#
# nnU-Net defaults to SimpleITK, and ITK refuses any NIfTI whose direction cosines
# are not orthonormal to its tolerance ("ITK only supports orthonormal direction
# cosines"). 136 of the 1228 TotalSegmentator volumes -- 11.1% -- are obliquely
# acquired and, stored as float32, fall just outside that tolerance. Under the
# default reader those cases fail to preprocess, so 11% of the training data
# would be silently lost, including whole study types like the angiography
# series. nibabel reads all 1228 without complaint.
#
# WithReorient additionally brings every volume to a canonical RAS orientation
# before training and restores the original orientation when writing predictions,
# which is worth having across a dataset whose acquisitions are this varied.
DEFAULT_READER_WRITER = "NibabelIOWithReorient"


class ConvertError(RuntimeError):
    pass


@dataclass
class CaseResult:
    """What happened for one case. Aggregated into a report at the end."""

    case_id: str
    ok: bool
    n_labels_written: int = 0
    missing: list[str] = field(default_factory=list)
    overlaps: int = 0
    # Label data that could not be used and was dropped: a mask whose geometry
    # disagrees with the CT, or an integer value the label set does not account
    # for. Dropping is reported loudly because the alternative -- a structure
    # silently becoming background -- looks exactly like a model that failed to
    # learn it.
    geometry_mismatch: list[str] = field(default_factory=list)
    error: str = ""
    skipped: bool = False


def link_or_copy(src: Path, dst: Path, mode: str = "hardlink") -> str:
    """Materialise ``src`` at ``dst``, degrading gracefully.

    Hardlinks need the same filesystem; symlinks need privilege on Windows
    (Developer Mode or admin). Rather than fail a multi-hour conversion on a
    permissions detail, fall back to copying and report which mode was used.
    """
    if dst.exists():
        return "exists"
    dst.parent.mkdir(parents=True, exist_ok=True)

    if mode == "hardlink":
        try:
            os.link(src, dst)
            return "hardlink"
        except OSError:
            pass
    if mode in ("hardlink", "symlink"):
        try:
            os.symlink(src, dst)
            return "symlink"
        except OSError:
            pass

    shutil.copy2(src, dst)
    return "copy"


def geometry_offset_mm(a: np.ndarray, b: np.ndarray, shape: Sequence[int]) -> float:
    """Worst-case physical displacement between two affines over a volume's extent.

    Evaluates both affines at the eight corners of the voxel grid and returns the
    largest distance between corresponding points, in millimetres. This is the
    quantity that actually matters -- a rotation difference too small to matter at
    the origin can still displace anatomy at the far corner, and vice versa.
    """
    nx, ny, nz = (int(s) - 1 for s in shape[:3])
    corners = np.array(
        [[x, y, z, 1.0] for x in (0, nx) for y in (0, ny) for z in (0, nz)],
        dtype=np.float64,
    ).T
    return float(np.linalg.norm((a @ corners - b @ corners)[:3], axis=0).max())


def resolve_overlap(
    out: np.ndarray,
    mask: np.ndarray,
    index: int,
    sizes: dict,
    policy: str,
) -> int:
    """Assign ``index`` to ``mask``, deciding who wins voxels already claimed.

    The TotalSegmentator masks genuinely overlap: each structure was segmented by
    its own model, so adjacent structures disagree by a voxel or two along shared
    interfaces -- colon against small bowel, heart against the inferior vena cava,
    L5 against the sacrum. It is a fraction of a percent of voxels, but a
    multilabel volume must pick one owner per voxel.

    ``smaller_wins`` (default) gives contested voxels to whichever structure is
    smaller in this case. Overlaps sit at interfaces between a bulky structure
    and a thinner one, and letting the bulky one win erodes the thin one -- the
    IVC would lose voxels to the heart, the aorta to the heart, costal cartilages
    to the sternum. Losing a voxel matters far more to a structure two voxels
    thick than to a liver.

    ``label_order`` reproduces the naive behaviour (higher label index wins),
    which is alphabetical and therefore anatomically meaningless. It exists only
    so the effect of the choice can be measured.

    Either way the rule is deterministic given the data, so a case converts
    identically every time.
    """
    collision = mask & (out != 0)
    n_collisions = int(collision.sum())

    if n_collisions == 0:
        out[mask] = index
        return 0

    if policy == OVERLAP_LABEL_ORDER:
        out[mask] = index
        return n_collisions

    # smaller_wins: take the uncontested voxels outright, then take contested
    # ones only from structures that are larger than this one.
    out[mask & (out == 0)] = index
    my_size = sizes[index]
    for prev in np.unique(out[collision]):
        if prev == 0:
            continue
        if sizes.get(int(prev), 0) > my_size:
            out[collision & (out == prev)] = index
    return n_collisions


def merge_masks(
    seg_dir: Path,
    names: Sequence[str],
    reference: nib.Nifti1Image,
    overlap_policy: str = OVERLAP_SMALLER_WINS,
) -> tuple[np.ndarray, list[str], int, list[str]]:
    """Stack binary masks into one uint8 label volume.

    Returns ``(labels, missing, n_overlap_voxels, geometry_mismatch)``.
    """
    shape = reference.shape
    out = np.zeros(shape, dtype=np.uint8)
    missing: list[str] = []
    mismatch: list[str] = []
    overlaps = 0
    sizes: dict = {}

    zooms = [float(z) for z in reference.header.get_zooms()[:3]]
    tolerance_mm = GEOMETRY_TOLERANCE_VOXELS * min(zooms or [1.0])

    for index, name in enumerate(names, start=1):
        path = seg_dir / f"{name}.nii.gz"
        if not path.is_file():
            # A structure absent from this case is normal in principle (partial
            # field of view), though this dataset ships all 117 for every case.
            missing.append(name)
            continue

        img = nib.load(str(path))
        if img.shape != shape:
            mismatch.append(f"{name}: shape {img.shape} != {shape}")
            continue
        offset = geometry_offset_mm(img.affine, reference.affine, shape)
        if offset > tolerance_mm:
            mismatch.append(f"{name}: geometry differs from CT by {offset:.3f} mm")
            continue

        mask = np.asanyarray(img.dataobj) > 0
        count = int(mask.sum())
        if count == 0:
            continue

        sizes[index] = count
        overlaps += resolve_overlap(out, mask, index, sizes, overlap_policy)

    return out, missing, overlaps, mismatch


def remap_multilabel(
    label_path: Path,
    label_set,
    reference: nib.Nifti1Image,
) -> tuple[np.ndarray, list[str], list[str]]:
    """Read a single integer label volume and remap it onto our indices.

    Returns ``(labels, missing, problems)``, where ``missing`` names structures
    with no voxels in this case and ``problems`` holds anything that made a
    voxel unusable.

    There is no overlap resolution to do here: an integer volume already has one
    owner per voxel. What replaces it is a harder question -- whether the values
    in the file mean what we think they mean. Values not covered by the label
    set are **dropped and reported** rather than passed through. Passing them
    through would put a foreign index into the training labels; silently zeroing
    them would turn a whole structure into background and read as a model that
    simply never learned it.
    """
    img = nib.load(str(label_path))
    problems: list[str] = []

    if img.shape != reference.shape:
        return (np.zeros(reference.shape, dtype=np.uint8), [],
                [f"labels shape {img.shape} != CT {reference.shape}"])

    zooms = [float(z) for z in reference.header.get_zooms()[:3]]
    tolerance_mm = GEOMETRY_TOLERANCE_VOXELS * min(zooms or [1.0])
    offset = geometry_offset_mm(img.affine, reference.affine, reference.shape)
    if offset > tolerance_mm:
        return (np.zeros(reference.shape, dtype=np.uint8), [],
                [f"labels geometry differs from CT by {offset:.3f} mm"])

    source = np.asanyarray(img.dataobj)
    mapping = label_set.source_to_index()

    out = np.zeros(reference.shape, dtype=np.uint8)
    present: set[int] = set()
    for value in np.unique(source):
        value = int(value)
        if value == 0:
            continue
        target = mapping.get(value)
        if target is None:
            n = int((source == value).sum())
            problems.append(
                f"unmapped label value {value} ({n} voxels) dropped -- declare it "
                "in the label set's source_values, or remove it from the file"
            )
            continue
        out[source == value] = target
        present.add(target)

    missing = [n for n, i in sorted(label_set.labels.items(), key=lambda kv: kv[1])
               if i not in present]
    return out, missing, problems


def convert_case(
    case_id: str,
    zenodo_root: Path,
    images_dir: Path,
    labels_dir: Path,
    label_set,
    link_mode: str,
    overwrite: bool,
    overlap_policy: str = OVERLAP_SMALLER_WINS,
) -> CaseResult:
    """Convert one subject. Runs in a worker process; must not raise.

    Handles both source forms: one binary mask per structure (TotalSegmentator,
    and the form that carries the most information), or a single integer volume
    (what a hand-labelled case exported from Slicer usually looks like). Which
    one a case uses is detected per case, so a dataset part-way through
    relabelling still converts.
    """
    try:
        from .index import find_image, find_labels

        subject = Path(zenodo_root) / case_id
        names = label_set.names

        ct_path = find_image(subject)
        if ct_path is None:
            return CaseResult(case_id, False,
                              error=f"no image found in {subject} "
                                    f"(looked for ct.nii.gz, image.nii.gz, "
                                    f"{case_id}.nii.gz)")
        seg_dir, multilabel = find_labels(subject)
        if seg_dir is None and multilabel is None:
            return CaseResult(case_id, False,
                              error=f"no labels found in {subject} (neither a "
                                    "segmentations/ directory nor labels.nii.gz)")

        label_path = Path(labels_dir) / f"{case_id}.nii.gz"
        image_path = Path(images_dir) / f"{case_id}_0000.nii.gz"

        if label_path.exists() and image_path.exists() and not overwrite:
            return CaseResult(case_id, True, skipped=True)

        ct = nib.load(str(ct_path))
        if seg_dir is not None:
            labels, missing, overlaps, mismatch = merge_masks(
                seg_dir, names, ct, overlap_policy=overlap_policy
            )
        else:
            labels, missing, mismatch = remap_multilabel(multilabel, label_set, ct)
            overlaps = 0

        # Write via a temp name then rename, so an interrupted run never leaves a
        # truncated .nii.gz that a later run would happily skip as "done".
        label_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = label_path.with_suffix(".tmp.nii.gz")
        out_img = nib.Nifti1Image(labels, ct.affine, ct.header)
        out_img.set_data_dtype(np.uint8)
        nib.save(out_img, str(tmp))
        os.replace(tmp, label_path)

        link_or_copy(ct_path, image_path, link_mode)

        return CaseResult(
            case_id,
            True,
            n_labels_written=int(labels.max()),
            missing=missing,
            overlaps=overlaps,
            geometry_mismatch=mismatch,
        )
    except Exception as exc:  # worker boundary: report, never crash the pool
        return CaseResult(case_id, False, error=f"{type(exc).__name__}: {exc}")


def write_dataset_json(
    raw_dir: Path,
    task: TaskConfig,
    n_training: int,
    n_test: int = 0,
    reader_writer: str = DEFAULT_READER_WRITER,
) -> Path:
    """Write nnU-Net v2 dataset.json."""
    payload = {
        "channel_names": {"0": "CT"},
        "labels": task.label_set.to_nnunet_labels(),
        "numTraining": n_training,
        "file_ending": ".nii.gz",
        # Load-bearing. See DEFAULT_READER_WRITER: without this, nnU-Net's
        # default SimpleITK reader fails on 136 of the 1228 cases (11%).
        "overwrite_image_reader_writer": reader_writer,
        # Provenance, ignored by nnU-Net but invaluable when several datasets
        # with similar names accumulate on a training box.
        "description": (
            f"{task.dataset_name}: label set '{task.label_set.name}' "
            f"({task.label_set.n_classes} classes) at {task.spacing_label}; "
            f"generated by segtrain"
        ),
        "numTest": n_test,
    }
    raw_dir.mkdir(parents=True, exist_ok=True)
    path = raw_dir / "dataset.json"
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
    return path


@dataclass
class ConvertReport:
    task: str
    overlap_policy: str = OVERLAP_SMALLER_WINS
    n_train: int = 0
    n_test: int = 0
    n_skipped: int = 0
    failures: list[CaseResult] = field(default_factory=list)
    with_missing: list[CaseResult] = field(default_factory=list)
    with_overlaps: list[CaseResult] = field(default_factory=list)
    with_mismatch: list[CaseResult] = field(default_factory=list)

    def add(self, r: CaseResult, is_test: bool) -> None:
        if not r.ok:
            self.failures.append(r)
            return
        if r.skipped:
            self.n_skipped += 1
        if is_test:
            self.n_test += 1
        else:
            self.n_train += 1
        if r.missing:
            self.with_missing.append(r)
        if r.overlaps:
            self.with_overlaps.append(r)
        if r.geometry_mismatch:
            self.with_mismatch.append(r)

    def render(self) -> str:
        lines = [
            f"{self.task}: {self.n_train} training, {self.n_test} test cases converted"
            + (f" ({self.n_skipped} already present, skipped)" if self.n_skipped else "")
        ]
        if self.with_missing:
            n = len(self.with_missing)
            ex = self.with_missing[0]
            lines.append(
                f"  {n} case(s) had absent structures, e.g. {ex.case_id}: "
                f"{', '.join(ex.missing[:4])}{'...' if len(ex.missing) > 4 else ''}"
            )
        if self.with_overlaps:
            # Expected, not alarming: the source masks are independently produced
            # per structure and disagree by a voxel or two at shared interfaces.
            n = len(self.with_overlaps)
            worst = max(self.with_overlaps, key=lambda r: r.overlaps)
            total = sum(r.overlaps for r in self.with_overlaps)
            lines.append(
                f"  {n} case(s) had overlapping source masks "
                f"({total} voxels total, worst {worst.case_id}: {worst.overlaps}); "
                f"resolved by policy '{self.overlap_policy}'"
            )
        if self.with_mismatch:
            n = len(self.with_mismatch)
            ex = self.with_mismatch[0]
            lines.append(
                f"  WARNING: {n} case(s) had unusable label data, e.g. "
                f"{ex.case_id}: {ex.geometry_mismatch[0]}. Those labels were DROPPED."
            )
        if self.failures:
            lines.append(f"  FAILED: {len(self.failures)} case(s)")
            for r in self.failures[:10]:
                lines.append(f"    {r.case_id}: {r.error}")
            if len(self.failures) > 10:
                lines.append(f"    ... and {len(self.failures) - 10} more")
        return "\n".join(lines)

    @property
    def ok(self) -> bool:
        return not self.failures


def convert_dataset(
    cfg: Config,
    task: TaskConfig,
    rows: list[CaseMeta],
    limit: Optional[int] = None,
    overwrite: bool = False,
    include_test: bool = True,
    dry_run: bool = False,
    progress: Optional[callable] = None,
) -> ConvertReport:
    """Convert every case for one task."""
    raw_dir = task.raw_dir(cfg)
    names = task.label_set.names

    train_ids = [r.case_id for r in rows if r.split != SPLIT_TEST]
    test_ids = [r.case_id for r in rows if r.split == SPLIT_TEST] if include_test else []
    if limit:
        train_ids = train_ids[:limit]
        test_ids = test_ids[: max(1, limit // 8)] if test_ids else []

    report = ConvertReport(task=task.nnunet_name, overlap_policy=cfg.overlap_policy)

    if dry_run:
        print(f"[dry-run] {task.nnunet_name} -> {raw_dir}")
        print(f"[dry-run]   {len(names)} structures from label set '{task.label_set.name}'")
        print(f"[dry-run]   {len(train_ids)} training + {len(test_ids)} test cases")
        print(f"[dry-run]   images via {cfg.link_mode}, labels written as uint8 multilabel")
        report.n_train, report.n_test = len(train_ids), len(test_ids)
        return report

    jobs: list[tuple[str, Path, Path, bool]] = []
    for case_id in train_ids:
        jobs.append((case_id, raw_dir / "imagesTr", raw_dir / "labelsTr", False))
    for case_id in test_ids:
        jobs.append((case_id, raw_dir / "imagesTs", raw_dir / "labelsTs", True))

    for _, img_dir, lbl_dir, _ in jobs:
        img_dir.mkdir(parents=True, exist_ok=True)
        lbl_dir.mkdir(parents=True, exist_ok=True)

    n_workers = max(1, min(cfg.n_workers(), len(jobs)))
    done = 0
    with ProcessPoolExecutor(max_workers=n_workers) as pool:
        futures = {
            pool.submit(
                convert_case,
                case_id,
                cfg.zenodo_root,
                img_dir,
                lbl_dir,
                task.label_set,
                cfg.link_mode,
                overwrite,
                cfg.overlap_policy,
            ): is_test
            for case_id, img_dir, lbl_dir, is_test in jobs
        }
        for fut in as_completed(futures):
            report.add(fut.result(), futures[fut])
            done += 1
            if progress:
                progress(done, len(jobs))

    write_dataset_json(
        raw_dir,
        task,
        n_training=report.n_train,
        n_test=report.n_test,
        reader_writer=cfg.reader_writer,
    )
    return report


def iter_case_ids(zenodo_root: Path) -> Iterable[str]:
    """Subject directories actually present on disk, for cross-checking meta.csv."""
    for p in sorted(Path(zenodo_root).iterdir()):
        if p.is_dir() and (p / "ct.nii.gz").is_file():
            yield p.name
