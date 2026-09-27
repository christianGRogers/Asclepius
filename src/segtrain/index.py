"""Build the dataset index for a bring-your-own labelled dataset.

TotalSegmentator ships a ``meta.csv`` carrying its published train/val/test
split, and the whole pipeline reads it: splits, conversion and
`segtrain status` all go through ``segtrain.splits.read_meta``.
Your own CCTA data has no such file.

Rather than teach every one of those to work without an index, this writes the
index -- same semicolon-delimited format, same columns -- by scanning a directory
of cases. Everything downstream then works unchanged.

Expected layout, which is the same shape TotalSegmentator uses::

    <root>/<case>/ct.nii.gz
    <root>/<case>/segmentations/left_main.nii.gz        one binary mask per
    <root>/<case>/segmentations/left_circumflex.nii.gz  structure ...

or, for data labelled as a single volume (what you get out of Slicer's
segmentation exporter)::

    <root>/<case>/ct.nii.gz
    <root>/<case>/labels.nii.gz     one integer volume, background 0

Both are detected per case, so a dataset part-way through relabelling still
indexes. `segtrain convert` reads whichever form it finds.

**Split assignment is stable under growth.** Cases are assigned by hashing the
case id, not by shuffling a list. Adding case 200 to a 199-case dataset therefore
leaves the first 199 exactly where they were. The alternative -- shuffle and
slice -- silently reassigns cases every time the dataset grows, which moves
yesterday's test cases into today's training set and quietly invalidates every
number you have measured. That failure is invisible: nothing crashes, the model
just scores better than it should.
"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .splits import SPLIT_TEST, SPLIT_TRAIN, SPLIT_VAL, CaseMeta

# Candidate image filenames, most specific first. `ct.nii.gz` matches the
# TotalSegmentator layout the rest of the pipeline grew up on.
IMAGE_NAMES = ("ct.nii.gz", "image.nii.gz", "img.nii.gz", "ccta.nii.gz")

# Candidate single-file multilabel names, checked when there is no
# segmentations/ directory.
MULTILABEL_NAMES = ("labels.nii.gz", "label.nii.gz", "seg.nii.gz",
                    "segmentation.nii.gz", "mask.nii.gz")

SEGMENTATIONS_DIR = "segmentations"

# ---------------------------------------------------------------- flat layout
#
# ImageCAS does not ship one directory per case. It ships two files per case in
# one directory::
#
#     <root>/1.img.nii.gz
#     <root>/1.label.nii.gz
#
# which the nested scanner above sees as an empty root. Rather than ask anyone
# to reshuffle 1000 pairs of files into directories before they can index them,
# the flat form is detected and paired here.
#
# Pairing is by *marker*, not by position: a file whose stem ends in one of
# these is the label for the case named by the rest of the stem. Checked
# longest-first so ``.segmentation`` is not mistaken for ``.seg``.
LABEL_MARKERS = (".segmentation", "_segmentation", ".label", "_label",
                 ".seg", "_seg", "_gt", ".gt", ".mask", "_mask")

#: Same idea for the image half. A file with no marker at all is taken as the
#: image, which is how ``1.nii.gz`` + ``1.label.nii.gz`` datasets are named.
IMAGE_MARKERS = (".image", "_image", ".img", "_img", ".ccta", "_ccta", ".ct", "_ct")

NIFTI_SUFFIX = ".nii.gz"


def _strip_marker(stem: str, markers: tuple[str, ...]) -> Optional[str]:
    """``("1.label", LABEL_MARKERS) -> "1"``; None when no marker matches."""
    for marker in sorted(markers, key=len, reverse=True):
        if stem.endswith(marker) and len(stem) > len(marker):
            return stem[: -len(marker)]
    return None


def scan_flat(root: Path) -> list[ScannedCase]:
    """Cases stored as ``<id><image marker>.nii.gz`` beside ``<id><label marker>.nii.gz``.

    A case with an image and no label is still returned, so a partially
    delivered dataset indexes and `segtrain index` can report what is missing
    rather than silently listing fewer cases than arrived.
    """
    root = Path(root)
    images: dict[str, Path] = {}
    labels: dict[str, Path] = {}

    for path in sorted(root.glob("*" + NIFTI_SUFFIX)):
        stem = path.name[: -len(NIFTI_SUFFIX)]

        case_id = _strip_marker(stem, LABEL_MARKERS)
        if case_id is not None:
            labels[case_id] = path
            continue

        case_id = _strip_marker(stem, IMAGE_MARKERS)
        images[case_id if case_id is not None else stem] = path

    return [
        ScannedCase(case_id, images[case_id], None, labels.get(case_id))
        for case_id in sorted(images)
    ]


def looks_flat(root: Path) -> bool:
    """True when ``root`` holds NIfTI files directly and no case directories.

    Deliberately conservative: a root holding both is treated as nested, since
    stray exports sitting beside real case directories are far more common than
    a genuinely mixed dataset.
    """
    root = Path(root)
    if any(p.is_dir() and find_image(p) is not None for p in root.iterdir()):
        return False
    return any(root.glob("*" + NIFTI_SUFFIX))



class IndexError_(RuntimeError):
    """Named with a trailing underscore to avoid shadowing the builtin."""


@dataclass(frozen=True)
class ScannedCase:
    case_id: str
    image: Path
    seg_dir: Optional[Path] = None
    multilabel: Optional[Path] = None

    @property
    def label_form(self) -> str:
        if self.seg_dir is not None:
            return "per-structure"
        if self.multilabel is not None:
            return "multilabel"
        return "none"

    @property
    def has_labels(self) -> bool:
        return self.label_form != "none"


def find_image(case_dir: Path) -> Optional[Path]:
    for name in IMAGE_NAMES:
        candidate = case_dir / name
        if candidate.is_file():
            return candidate
    # Fall back to <case>.nii.gz, which is how a lot of exports are named.
    candidate = case_dir / f"{case_dir.name}.nii.gz"
    return candidate if candidate.is_file() else None


def find_labels(case_dir: Path) -> tuple[Optional[Path], Optional[Path]]:
    """``(segmentations_dir, multilabel_file)`` -- at most one is not None.

    A segmentations/ directory wins when both are present: it carries per
    structure provenance, so a partially-labelled case is detectable rather than
    being flattened into an integer volume where "absent" and "background" look
    identical.
    """
    seg_dir = case_dir / SEGMENTATIONS_DIR
    if seg_dir.is_dir() and any(seg_dir.glob("*.nii.gz")):
        return seg_dir, None
    for name in MULTILABEL_NAMES:
        candidate = case_dir / name
        if candidate.is_file():
            return None, candidate
    return None, None


def scan(root: Path, layout: str = "auto") -> list[ScannedCase]:
    """Every case under ``root`` that has an image.

    ``layout`` is ``nested`` (one directory per case), ``flat`` (two files per
    case in one directory, as ImageCAS ships), or ``auto`` to decide by looking.
    """
    root = Path(root)
    if not root.is_dir():
        raise IndexError_(f"dataset root does not exist: {root}")
    if layout not in ("auto", "nested", "flat"):
        raise IndexError_(f"unknown layout {layout!r}; expected auto, nested or flat")

    if layout == "flat" or (layout == "auto" and looks_flat(root)):
        return scan_flat(root)

    cases: list[ScannedCase] = []
    for case_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        image = find_image(case_dir)
        if image is None:
            continue
        seg_dir, multilabel = find_labels(case_dir)
        cases.append(ScannedCase(case_dir.name, image, seg_dir, multilabel))
    return cases


def assign_split(
    case_id: str,
    val_fraction: float,
    test_fraction: float,
    seed: int = 12345,
) -> str:
    """Deterministic split for one case, from its id alone.

    Hashing rather than shuffling is what makes this stable as the dataset grows;
    see the module docstring. It also means two people running this on the same
    data get the same split without exchanging a file.

    SHA-256 rather than ``hash()``: Python salts string hashing per process, so
    ``hash()`` would put a case in train today and test tomorrow.
    """
    digest = hashlib.sha256(f"{seed}:{case_id}".encode()).digest()
    # 53 bits keeps the ratio exactly representable in a float.
    position = int.from_bytes(digest[:8], "big") / 2**64

    if position < test_fraction:
        return SPLIT_TEST
    if position < test_fraction + val_fraction:
        return SPLIT_VAL
    return SPLIT_TRAIN


def build_rows(
    cases: list[ScannedCase],
    val_fraction: float = 0.15,
    test_fraction: float = 0.15,
    seed: int = 12345,
    study_type: str = "ccta",
    overrides: Optional[dict[str, str]] = None,
) -> list[CaseMeta]:
    """Assign a split to each case, honouring any explicit overrides."""
    if val_fraction < 0 or test_fraction < 0:
        raise IndexError_("fractions must not be negative")
    if val_fraction + test_fraction >= 1.0:
        raise IndexError_(
            f"val_fraction + test_fraction = {val_fraction + test_fraction:.2f} "
            "leaves nothing to train on"
        )

    overrides = overrides or {}
    rows = []
    for case in cases:
        split = overrides.get(case.case_id) or assign_split(
            case.case_id, val_fraction, test_fraction, seed
        )
        rows.append(CaseMeta(case_id=case.case_id, split=split, study_type=study_type))
    return rows


def read_overrides(path: Path) -> dict[str, str]:
    """Read a two-column ``case_id,split`` CSV pinning specific cases.

    For the cases you have a reason to place by hand -- a known-difficult study
    you want in the test set, or cases from one scanner you want kept together.
    Accepts comma or semicolon, with or without a header.
    """
    path = Path(path)
    if not path.is_file():
        raise IndexError_(f"split override file not found: {path}")

    valid = {SPLIT_TRAIN, SPLIT_VAL, SPLIT_TEST}
    out: dict[str, str] = {}
    with open(path, newline="", encoding="utf-8-sig") as fh:
        sample = fh.read(4096)
        fh.seek(0)
        delimiter = ";" if sample.count(";") > sample.count(",") else ","
        for line in csv.reader(fh, delimiter=delimiter):
            if len(line) < 2:
                continue
            case_id, split = line[0].strip(), line[1].strip().lower()
            if not case_id or split not in valid:
                continue  # header row, or a typo we report on below
            out[case_id] = split

    if not out:
        raise IndexError_(
            f"{path}: no usable rows. Expected 'case_id,split' with split one of "
            f"{sorted(valid)}"
        )
    return out


def write_meta(path: Path, rows: list[CaseMeta]) -> Path:
    """Write meta.csv in the format ``segtrain.splits.read_meta`` expects.

    Semicolon-delimited with an ``image_id`` column -- matching TotalSegmentator's
    own file, so there is exactly one index format in the codebase rather than
    one per data source.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, delimiter=";")
        writer.writerow(["image_id", "split", "study_type", "institute", "manufacturer"])
        for row in rows:
            writer.writerow([row.case_id, row.split, row.study_type,
                             row.institute, row.manufacturer])
    return path


def summarize(
    cases: list[ScannedCase],
    rows: list[CaseMeta],
    val_fraction: Optional[float] = None,
    test_fraction: Optional[float] = None,
) -> str:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.split] = counts.get(row.split, 0) + 1

    forms: dict[str, int] = {}
    for case in cases:
        forms[case.label_form] = forms.get(case.label_form, 0) + 1

    lines = [
        f"{len(cases)} case(s) with an image",
        f"  splits:  {counts.get(SPLIT_TRAIN, 0)} train / "
        f"{counts.get(SPLIT_VAL, 0)} val / {counts.get(SPLIT_TEST, 0)} test",
        "  labels:  " + ", ".join(f"{n} {form}" for form, n in sorted(forms.items())),
    ]

    # Hashing gives the requested proportions only in expectation. On a few dozen
    # cases the realised split can look badly off -- 12 cases at 15/15 came out
    # 6/5/1 in testing -- and that is the method working, not a bug. Say so,
    # because the natural reaction is to re-run with a different seed until it
    # looks right, which is choosing a split by peeking at it.
    if val_fraction is not None and test_fraction is not None and cases:
        expected_val = val_fraction * len(cases)
        expected_test = test_fraction * len(cases)
        got_val, got_test = counts.get(SPLIT_VAL, 0), counts.get(SPLIT_TEST, 0)
        if len(cases) < 60 and (abs(got_val - expected_val) > 0.5 + 0.5 * expected_val
                                or abs(got_test - expected_test) > 0.5 + 0.5 * expected_test):
            lines.append(
                f"  note:    asked for ~{expected_val:.0f} val / ~{expected_test:.0f} "
                f"test and got {got_val} / {got_test}. Hashing hits the requested\n"
                "           proportions only in expectation, and small datasets are "
                "lumpy. Use --overrides to\n"
                "           place cases deliberately; do not re-roll --seed until "
                "the split looks good, which is\n"
                "           choosing a test set by looking at it."
            )

    unlabelled = [c.case_id for c in cases if not c.has_labels]
    if unlabelled:
        lines.append(
            f"  WARNING: {len(unlabelled)} case(s) have no labels and will fail to "
            f"convert, e.g. {', '.join(unlabelled[:5])}"
        )
    return "\n".join(lines)
