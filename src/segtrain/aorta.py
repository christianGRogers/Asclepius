"""Aorta masks for the tree-F1 ostium (A1, A1a, A21): a batch TotalSegmentator step.

The ostium of record in :mod:`segtrain.tf1` is the reference centreline voxel nearest the
aorta, and a tF1 computed without an aorta mask is provisional and decides nothing (A1a). This
module produces those masks outside a Trillium job: TotalSegmentator's fast ``total`` model with
``roi_subset=['aorta']``, one CT at a time, written as ``<case>_aorta.nii.gz`` (uint8 0/1) on the
CT's own grid.

* **Resumable.** A mask that already exists is checked against the CT header and kept; a finished
  mask is written to a temporary name first and renamed, so an interrupted run never leaves a
  half-written mask under the final name.
* **Loud.** Every case either ends with a valid mask or is listed as failed (reason included), and
  :func:`produce_aortas` raises :class:`AortaBatchError` at the end if any case failed. An empty
  aorta, a grid mismatch or a crash is a failure, never a skip. One bad case does not stop the
  others.
* **Sealed cases are refused** before any work (A14), when a sealed list is given.
* **Memory.** TotalSegmentator on a whole CCTA volume needs about 7 GB on CPU. With ``reference``
  (the coronary mask or 4-class label on the same grid) the CT is cropped to the tree's bounding box
  plus ``margin_mm`` (40 mm holds the aortic root and both ostia) and the mask is pasted back.
  Validated this way on 84 cases (vault: *Delta - On the thick reference the cheap ostium rules miss
  1 in 8 ostia silently...*), about 40 s per case on one CPU core.

TotalSegmentator is an optional dependency, imported only when a mask is actually computed
(``pip install segtrain[aorta]``). On clusters whose wheelhouse lacks ``vtk`` (Compute Canada /
Trillium), install it without its preview stack, as ``trillium/atlas2`` does::

    pip install --no-deps "TotalSegmentator==2.18.0"
    pip install tqdm requests dicom2nifti xmltodict blosc      # not fury/vtk/imgkit, not pyarrow

Weights must be downloaded where there is internet (``totalseg_download_weights -t total_fast``)
into ``$TOTALSEG_HOME_DIR``; compute nodes then run offline.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

import nibabel as nib
import numpy as np

#: Crop margin around the reference tree; the aortic root and both ostia lie inside it.
CROP_MARGIN_MM = 40.0
DEVICES = ("cpu", "gpu", "mps")
PathLike = Union[str, Path]
#: ``segmenter(ct_path, device) -> nibabel image`` of the aorta on that CT's grid.
Segmenter = Callable[[str, str], "nib.Nifti1Image"]


class AortaError(RuntimeError):
    """One case could not produce a valid aorta mask."""


class AortaBatchError(RuntimeError):
    """At least one case failed; ``report`` lists them all."""

    def __init__(self, report: AortaReport):
        self.report = report
        lines = [f"{c}: {why}" for c, why in sorted(report.failed.items())]
        super().__init__(f"{len(report.failed)} aorta mask(s) failed:\n  " + "\n  ".join(lines))


@dataclass
class AortaReport:
    out_dir: str
    made: list = field(default_factory=list)  # computed in this run
    kept: list = field(default_factory=list)  # already present and valid
    failed: dict = field(default_factory=dict)  # case -> reason
    seconds: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.failed

    def as_dict(self) -> dict:
        return {
            "out_dir": self.out_dir,
            "made": sorted(self.made),
            "kept": sorted(self.kept),
            "failed": dict(sorted(self.failed.items())),
            "seconds": {k: round(v, 1) for k, v in sorted(self.seconds.items())},
        }


def aorta_path(out_dir: PathLike, case: str) -> Path:
    """Where the mask of ``case`` lives: ``<out_dir>/<case>_aorta.nii.gz``."""
    return Path(out_dir) / f"{case}_aorta.nii.gz"


def _totalsegmentator() -> Segmenter:
    try:
        from totalsegmentator.python_api import totalsegmentator
    except ImportError as e:
        raise ImportError(
            "segtrain.aorta needs TotalSegmentator: pip install 'segtrain[aorta]', or on clusters "
            "without vtk: pip install --no-deps TotalSegmentator==2.18.0 && "
            "pip install tqdm requests dicom2nifti xmltodict blosc"
        ) from e

    def run(ct_path: str, device: str):
        return totalsegmentator(
            ct_path,
            None,
            fast=True,
            roi_subset=["aorta"],
            device=device,
            nr_thr_resamp=1,
            nr_thr_saving=1,
            quiet=True,
        )

    return run


def _crop_box(reference: np.ndarray, spacing: np.ndarray, margin_mm: float) -> tuple:
    idx = np.nonzero(reference)
    if not len(idx[0]):
        raise AortaError("reference mask is empty; cannot crop around the tree")
    m = np.ceil(margin_mm / spacing).astype(int)
    lo = np.maximum([i.min() for i in idx] - m, 0)
    hi = np.minimum([i.max() + 1 for i in idx] + m, reference.shape)
    return tuple(slice(int(a), int(b)) for a, b in zip(lo, hi))


def _same_grid(a: nib.Nifti1Image, b: nib.Nifti1Image) -> bool:
    return tuple(a.shape[:3]) == tuple(b.shape[:3]) and np.allclose(a.affine, b.affine, atol=1e-3)


def segment_aorta(
    ct_path: PathLike,
    dest: PathLike,
    *,
    device: str = "cpu",
    reference: Optional[PathLike] = None,
    margin_mm: float = CROP_MARGIN_MM,
    segmenter: Optional[Segmenter] = None,
    min_voxels: int = 1,
) -> Path:
    """Compute one aorta mask and write it atomically to ``dest`` on the CT's grid.

    ``reference`` (a coronary mask or label on the same grid) crops the CT to the tree +
    ``margin_mm`` before segmentation. ``segmenter`` replaces TotalSegmentator (tests). Raises
    :class:`AortaError` on an empty aorta (< ``min_voxels``), a grid mismatch, or any segmenter
    failure."""
    if device not in DEVICES and not device.startswith("gpu:"):
        raise ValueError(f"device must be one of {DEVICES} or 'gpu:N', not {device!r}")
    dest = Path(dest)
    ct = nib.load(str(ct_path))
    run = segmenter or _totalsegmentator()
    with tempfile.TemporaryDirectory(dir=dest.parent, prefix=".aorta_") as tmp:
        src, box = str(ct_path), None
        if reference is not None:
            ref = nib.load(str(reference))
            if not _same_grid(ref, ct):
                raise AortaError(f"reference {reference} is not on the CT grid")
            sp = np.asarray(ct.header.get_zooms()[:3], float)
            box = _crop_box(np.asanyarray(ref.dataobj) > 0, sp, margin_mm)
            sub = np.asanyarray(ct.dataobj)[box]
            aff = ct.affine.copy()
            aff[:3, 3] = aff[:3, :3] @ np.array([s.start for s in box]) + aff[:3, 3]
            src = os.path.join(tmp, "crop.nii.gz")
            nib.save(nib.Nifti1Image(np.asarray(sub, dtype=np.int16), aff), src)
        try:
            res = run(src, device)
        except Exception as e:  # noqa: BLE001 -- any segmenter failure is this case's failure
            raise AortaError(f"TotalSegmentator failed: {e!r}") from e
        if res is None:
            raise AortaError("TotalSegmentator returned no image")
        a = np.asanyarray(res.dataobj) > 0
        expect = tuple(s.stop - s.start for s in box) if box else tuple(ct.shape[:3])
        if a.shape != expect:
            raise AortaError(f"aorta grid {a.shape} does not match the input {expect}")
        if box is not None:
            full = np.zeros(ct.shape[:3], bool)
            full[box] = a
            a = full
        if int(a.sum()) < min_voxels:
            raise AortaError("TotalSegmentator found no aorta (empty mask)")
        part = os.path.join(tmp, "aorta.nii.gz")
        out = nib.Nifti1Image(a.astype(np.uint8), ct.affine)
        out.set_qform(ct.affine, code=1)
        out.set_sform(ct.affine, code=1)
        nib.save(out, part)
        os.replace(part, dest)
    return dest


def check_aorta(mask_path: PathLike, ct_path: PathLike) -> None:
    """Raise :class:`AortaError` unless ``mask_path`` is a non-empty mask on ``ct_path``'s grid."""
    try:
        m = nib.load(str(mask_path))
        ct = nib.load(str(ct_path))
    except Exception as e:  # noqa: BLE001
        raise AortaError(f"unreadable: {e!r}") from e
    if not _same_grid(m, ct):
        raise AortaError(f"{mask_path} is not on the CT grid")
    if not (np.asanyarray(m.dataobj) > 0).any():
        raise AortaError(f"{mask_path} is empty")


def produce_aortas(
    cases: Mapping[str, PathLike],
    out_dir: PathLike,
    *,
    device: str = "cpu",
    references: Optional[Mapping[str, PathLike]] = None,
    sealed: Optional[Iterable[str]] = None,
    overwrite: bool = False,
    margin_mm: float = CROP_MARGIN_MM,
    segmenter: Optional[Segmenter] = None,
    log: Callable[[str], None] = print,
) -> AortaReport:
    """Aorta masks for ``cases`` (``{case: ct_path}``) into ``out_dir``, resumably.

    Existing valid masks are kept (unless ``overwrite``); an existing *invalid* mask is recomputed.
    Every case is attempted; failures are collected, written with the rest to
    ``<out_dir>/aorta_report.json``, and raised together as :class:`AortaBatchError`.
    ``sealed`` cases are refused before any work. ``references`` (``{case: mask path}``) crops each
    CT around its tree (recommended on CPU)."""
    if device not in DEVICES and not device.startswith("gpu:"):
        raise ValueError(f"device must be one of {DEVICES} or 'gpu:N', not {device!r}")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    blocked = sorted(set(cases) & set(sealed or ()))
    if blocked:
        raise ValueError(
            f"refusing sealed cases (A14): {blocked[:8]}{' ...' if len(blocked) > 8 else ''}"
        )
    rep = AortaReport(out_dir=str(out))
    for case in sorted(cases):
        dest = aorta_path(out, case)
        ct = cases[case]
        if dest.exists() and not overwrite:
            try:
                check_aorta(dest, ct)
                rep.kept.append(case)
                continue
            except AortaError as e:
                log(f"[aorta] {case}: existing mask invalid ({e}); recomputing")
        t = time.time()
        try:
            if not Path(ct).is_file():
                raise AortaError(f"CT not found: {ct}")
            ref = references.get(case) if references else None
            if references is not None and ref is None:
                raise AortaError("no reference given for this case (needed to crop)")
            segment_aorta(
                ct, dest, device=device, reference=ref, margin_mm=margin_mm, segmenter=segmenter
            )
            rep.made.append(case)
            rep.seconds[case] = time.time() - t
            log(f"[aorta] {case} {time.time() - t:.0f}s")
        except (AortaError, OSError, ValueError) as e:
            rep.failed[case] = str(e)
            log(f"[aorta] {case} FAILED: {e}")
    (out / "aorta_report.json").write_text(json.dumps(rep.as_dict(), indent=1), encoding="utf-8")
    log(f"[aorta] {len(rep.made)} made, {len(rep.kept)} kept, {len(rep.failed)} failed -> {out}")
    if rep.failed:
        raise AortaBatchError(rep)
    return rep
