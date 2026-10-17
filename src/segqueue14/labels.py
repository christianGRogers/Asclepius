"""The four coronary classes, as SegQueue14 segments.

One table, imported by the Girder plugin (the default ``segqueue14.project``
setting), the Slicer module (the prelabel import and the submit check) and the
tests that pin ``configs/labels/coronary_icx4.yaml`` to it. A prelabel, a
submission and a training label all mean the same thing by the same integer.

Decisions (vault/Plans/Human decisions.md):

* D25 -- four classes again (reverses D9): LM, LAD, LCx, RCA, side branches by
  territory (D1: a branch takes its parent's class) and the ramus intermedius
  always LCx (D1b). ImageCAS-X's 14 classes collapse to these by
  ``ICX14_TO_4``.
* D8, D12 -- the lumen is ImageCAS-X's; annotators may freely redraw the outline
  to the contrast-filled lumen.
* D13 -- LAD, LCx and RCA must be non-empty to submit; LM is optional (some
  patients have separate LAD and LCx ostia and no left main).
* D26 -- on a seeded case every class starts as a full copy of the vessel seed,
  hidden; the annotator shows one class at a time and cuts it down to that
  vessel. A case is refused while any voxel is in two classes.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Mapping

#: ``(label, name, colour, required, hint)`` in label order. Names are the short
#: ImageCAS-X names; they are also the per-class file names in a training export
#: (``segmentations/<name>.nii.gz``) and the keys of the label config.
_TABLE = (
    (1, "LM", (0.95, 0.25, 0.20), False,
     "Left main, ostium to the LAD/LCx split; empty if separate ostia."),
    (2, "LAD", (0.20, 0.70, 0.30), True,
     "LAD and all its branches: every diagonal and septal."),
    (3, "LCx", (0.25, 0.45, 0.90), True,
     "LCx, all marginals, the ramus intermedius, and a left-sided PDA/PLA."),
    (4, "RCA", (0.95, 0.75, 0.15), True,
     "RCA and all its branches, including a right-sided PDA/PLA."),
)

#: Number of foreground classes.
N_CLASSES = len(_TABLE)

#: ``[name, ...]`` in label order.
NAMES: List[str] = [row[1] for row in _TABLE]

#: ``{name: label value}``.
LABEL_VALUES: Dict[str, int] = {row[1]: row[0] for row in _TABLE}

#: The classes that must be non-empty to submit (D13).
REQUIRED: List[str] = [row[1] for row in _TABLE if row[3]]

#: What annotators are told (D10, D12). Shown in the SegQueue14 panel and served
#: as the default ``segqueue14.project`` instructions.
INSTRUCTIONS = (
    "Each of the four classes -- LM, LAD, LCx, RCA -- starts as a full copy of the "
    "vessel seed (an automatic, uncorrected mask of the whole coronary tree) and is "
    "hidden. Show one class at a time (the eye in the segment list) and cut it down "
    "to that vessel: erase everything that belongs to another class. Every side "
    "branch takes the class of the vessel it comes off: diagonals are LAD, obtuse "
    "marginals are LCx, a PDA or posterolateral branch is the class of the artery "
    "it arises from. A ramus intermedius is always LCx. Also add vessel the seed "
    "missed, delete anything that is not a coronary artery, and trim or extend the "
    "outline to the contrast-filled lumen. A case cannot be submitted while any "
    "voxel is in two classes. Note anything unusual."
)

#: Project name served by default.
PROJECT_NAME = "Coronary segmentation, 4 classes"

#: Name of the label config this table must match (configs/labels/<name>.yaml).
LABEL_SET_NAME = "coronary_icx4"


#: ImageCAS-X's 14 label values -> these four (D1 territory, D1b ramus -> LCx).
#: ImageCAS-X "Other" (14: D3/D4, OM3/OM4) has no fixed parent and maps to 0
#: here; ``segtrain.reads.icx_to_territory`` gives it the nearest LAD/LCx class,
#: which is what training labels use.
ICX14_TO_4: Dict[int, int] = {
    1: 1,                                   # LM
    2: 2, 4: 2, 5: 2,                       # LAD, D1, D2
    3: 3, 6: 3, 7: 3, 8: 3, 12: 3, 13: 3,   # LCx, OM1, OM2, IM, L-PDA, L-PLA
    9: 4, 10: 4, 11: 4,                     # RCA, R-PDA, R-PLA
}


def segment_dicts() -> List[dict]:
    """The table as ``SegmentSpec.to_dict()``-shaped dicts (the setting's form)."""
    return [
        {"name": name, "label": label, "color": list(colour),
         "required": required, "hint": hint}
        for label, name, colour, required, hint in _TABLE
    ]


def segment_specs():
    """The table as ``segqueue.protocol.SegmentSpec`` objects."""
    from segqueue.protocol import SegmentSpec

    return [SegmentSpec.from_dict(d) for d in segment_dicts()]


def missing_required(voxel_counts: Mapping[str, int],
                     required: Iterable[str] = None) -> List[str]:
    """The required classes with no voxels, in label order.

    ``voxel_counts`` is ``{segment name: voxels}``; a name absent from it counts
    as empty -- a client that forgot to report LAD has not shown LAD is there.
    """
    wanted = list(REQUIRED if required is None else required)
    out = []
    for name in wanted:
        try:
            n = int(voxel_counts.get(name, 0) or 0)
        except (TypeError, ValueError):
            n = 0
        if n <= 0:
            out.append(name)
    return out


def missing_required_message(missing: Iterable[str]) -> str:
    """The annotator-facing refusal for ``missing_required``."""
    names = list(missing)
    if not names:
        return ""
    if len(names) == 1:
        listed = names[0]
    else:
        listed = ", ".join(names[:-1]) + " and " + names[-1]
    return ("{} {} empty. LAD, LCx and RCA must each have at least some vessel "
            "before the case can be submitted. If one is genuinely absent or not "
            "visible in this scan, give the case back and say why in the case "
            "note.".format(listed, "is" if len(names) == 1 else "are"))


def overlap_message(pairs: Iterable) -> str:
    """The annotator-facing refusal for classes that share voxels (D26).

    ``pairs`` is ``[(name, name, voxels), ...]``.
    """
    rows = [(str(a), str(b), int(n)) for a, b, n in pairs]
    if not rows:
        return ""
    listed = "; ".join(f"{a} and {b} share {n} voxels" for a, b, n in rows)
    return (f"{listed}. Every vessel voxel must be in exactly one class. Each class starts "
            "as a full copy of the seed: show one class at a time and erase from it "
            "what belongs to another class. A class you have not cut down yet still "
            "holds the whole tree.")
