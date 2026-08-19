"""Reading a TotalSegmentator-style case tree, without Girder and without numpy.

The default source for SegQueue is the TotalSegmentator release on Zenodo
(record 10047292). It is convenient for two reasons that are easy to miss:

* Every case is already **presegmented** into 117 structures, so a case that
  contains a heart can be recognised from filenames alone -- no image is opened
  to decide whether it is worth annotating.
* A handful of cases additionally carry a ``coronary_arteries`` mask. That mask
  is a single binary lumen, not per-branch labels, so it is not the answer to
  this project's task -- but it is an enormous head start on it. Splitting an
  existing tree into LM / LAD / LCx / RCA is minutes of work; drawing the tree
  from scratch is an hour.

What this module does *not* do is read pixels. Everything here is filename and
directory logic, which is why it lives in the shared stdlib-only package: the
ingest CLI runs it on the server and the test suite runs it on a laptop with no
Girder, no numpy and no dataset.

    <root>/s0011/ct.nii.gz
    <root>/s0011/segmentations/heart.nii.gz              -> case is eligible
    <root>/s0011/segmentations/coronary_arteries.nii.gz  -> case ships a seed
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Optional

#: Where the dataset comes from, quoted in CLI help so nobody has to go looking.
ZENODO_URL = "https://zenodo.org/records/10047292"

#: Recognised names for a case's CT, most specific first. ``ct.nii.gz`` is what
#: TotalSegmentator uses; the rest are what a bring-your-own CCTA tree tends to
#: use, and cost nothing to accept.
IMAGE_NAMES = ("ct.nii.gz", "ct.nrrd", "image.nii.gz", "img.nii.gz", "ccta.nii.gz")

#: Per-structure masks live here.
SEGMENTATIONS_DIR = "segmentations"

#: Extensions a mask may carry, in preference order.
MASK_SUFFIXES = (".nii.gz", ".nii", ".nrrd", ".nhdr", ".mha", ".mhd")

#: A case is only worth annotating if the scan actually contains a heart. In
#: TotalSegmentator v2 that is one structure; v1 split it into four chambers plus
#: myocardium, and both releases are in circulation, so both are accepted.
#: Finding *any* of these is the eligibility test.
HEART_STRUCTURES = (
    "heart",
    "heart_myocardium",
    "heart_atrium_left",
    "heart_atrium_right",
    "heart_ventricle_left",
    "heart_ventricle_right",
)

#: Preferred order for the mask sent to the client as the "heart region". The
#: whole-heart mask is far more useful than one chamber for framing the view and
#: for confining edits, so it wins when both exist.
REGION_PREFERENCE = HEART_STRUCTURES

#: A pre-existing coronary lumen mask, if the case happens to have one. Binary,
#: not per-branch -- see the module docstring.
CORONARY_STRUCTURES = (
    "coronary_arteries",
    "coronary_artery",
    "coronary_tree",
    "coronaries",
)


@dataclass(frozen=True)
class CaseFiles:
    """One case's paths, after scanning. Nothing here has been opened."""

    name: str
    #: The CT. Always present -- a case without one is not returned at all.
    volume: str
    #: Whole-heart or chamber mask, when the case has one. Used client-side to
    #: frame the view and to confine editing; never submitted.
    region: Optional[str] = None
    #: Binary coronary lumen mask, when the case has one. Loaded as a starting
    #: point for the annotator to split into branches.
    seed: Optional[str] = None
    #: Expert per-branch reference, from a separate gold directory.
    gold: Optional[str] = None

    @property
    def has_heart(self) -> bool:
        return self.region is not None

    @property
    def has_seed(self) -> bool:
        return self.seed is not None


def _find_one(directory: str, stems) -> Optional[str]:
    """First existing ``<directory>/<stem><suffix>``, trying stems in order."""
    if not directory or not os.path.isdir(directory):
        return None
    for stem in stems:
        for suffix in MASK_SUFFIXES:
            candidate = os.path.join(directory, stem + suffix)
            if os.path.isfile(candidate):
                return candidate
    return None


def find_volume(caseDir: str) -> Optional[str]:
    for name in IMAGE_NAMES:
        candidate = os.path.join(caseDir, name)
        if os.path.isfile(candidate):
            return candidate
    return None


def find_region(caseDir: str) -> Optional[str]:
    """The heart mask for a case, or None. Whole heart preferred over a chamber."""
    return _find_one(os.path.join(caseDir, SEGMENTATIONS_DIR), REGION_PREFERENCE)


def find_seed(caseDir: str) -> Optional[str]:
    """A pre-existing coronary mask for a case, or None."""
    return _find_one(os.path.join(caseDir, SEGMENTATIONS_DIR), CORONARY_STRUCTURES)


def find_gold(name: str, goldRoot: Optional[str]) -> Optional[str]:
    """The expert reference for a case, from a directory kept apart from the pool.

    Apart on purpose: a mis-scoped source root that swept expert references into
    the case pool would hand annotators the answers to the very cases used to
    measure them, and nothing downstream would notice.
    """
    if not goldRoot:
        return None
    for suffix in MASK_SUFFIXES:
        candidate = os.path.join(goldRoot, name + suffix)
        if os.path.isfile(candidate):
            return candidate
    return None


def case_dirs(root: str) -> Iterator[str]:
    """Immediate subdirectories of ``root``, sorted, that look like cases."""
    try:
        entries = sorted(os.listdir(root))
    except OSError:
        return
    for entry in entries:
        path = os.path.join(root, entry)
        if os.path.isdir(path) and find_volume(path) is not None:
            yield path


def find_cases(root: str, requireHeart: bool = True,
               goldRoot: Optional[str] = None) -> Iterator[CaseFiles]:
    """Every eligible case under ``root``, in sorted order.

    ``requireHeart`` is the filter the project actually wants: TotalSegmentator
    is a whole-body dataset and most of it is legs, heads and abdomens with no
    coronary anatomy in the field of view at all. Assigning those to an annotator
    wastes the one resource this project is short of.
    """
    for caseDir in case_dirs(root):
        name = os.path.basename(caseDir.rstrip(os.sep))
        region = find_region(caseDir)
        if requireHeart and region is None:
            continue
        yield CaseFiles(
            name=name,
            volume=find_volume(caseDir),
            region=region,
            seed=find_seed(caseDir),
            gold=find_gold(name, goldRoot),
        )


def scan_summary(root: str, goldRoot: Optional[str] = None) -> dict:
    """Counts for the dry run, so an operator can sanity-check before a big import.

    Deliberately reports the *rejected* count too. A scan that quietly returns
    12 cases out of 1,200 looks identical to a correct one until somebody asks
    why the project is nearly finished.
    """
    total = withHeart = withSeed = withGold = 0
    for caseDir in case_dirs(root):
        total += 1
        name = os.path.basename(caseDir.rstrip(os.sep))
        if find_region(caseDir) is not None:
            withHeart += 1
        if find_seed(caseDir) is not None:
            withSeed += 1
        if find_gold(name, goldRoot) is not None:
            withGold += 1
    return {
        "cases": total,
        "with_heart": withHeart,
        "without_heart": total - withHeart,
        "with_coronary_seed": withSeed,
        "with_gold": withGold,
    }
