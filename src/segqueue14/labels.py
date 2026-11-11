"""The four coronary classes, as SegQueue14 segments.

One table, imported by the Girder plugin (the default ``segqueue14.project``
setting), the Slicer module (the prelabel import and the submit check) and the
tests that pin ``configs/labels/coronary_icx4.yaml`` to it. A prelabel, a
submission and a training label all mean the same thing by the same integer.

Decisions (vault/Plans/Human decisions.md):

* D25 -- four classes again (reverses D9): LM, LAD, LCx, RCA, side branches by
  territory (D1: a branch takes its parent's class) and the ramus intermedius
  always LCx (D1b). ImageCAS-X's 14 classes collapse to these by
  ``icx14_to_four`` (``ICX14_TO_4``, and "Other" to the nearest LAD/LCx).
* D8, D12 -- the lumen is ImageCAS-X's; annotators may freely redraw the outline
  to the contrast-filled lumen.
* D13 -- LAD, LCx and RCA are expected to be non-empty; LM is optional (some
  patients have separate LAD and LCx ostia and no left main).
* D26 -- on a seeded case every class starts as a full copy of the vessel seed,
  hidden; the annotator shows one class at a time and cuts it down to that
  vessel, so that no voxel is in two classes.

The project lead's instruction of 2026-11-02 (#270) removed submit-time
enforcement of D13 and D26: neither the module nor the server refuses a
submission or a reviewer's revision for an empty or overlapping class.
``missing_required`` is still used by the scoring worker, which flags an empty
required class for review; ``missing_required_message`` and ``overlap_message``
are no longer shown at submit.

**The extended classes (D44, #280).** 17 optional classes on top of the four:
three materials (stent, calcified and non-calcified plaque) and 14 named side
branches. They are SegQueue-only: ``NAMES``, ``LABEL_VALUES`` and ``N_CLASSES``
stay the four vessels -- the headline every score, the training labels and the
label config are about -- and the extras live in ``EXTRA_NAMES`` and friends.
An extended read is collapsed to the four before it is scored
(``collapse_to_four``): each branch is unioned into its parent; materials go
into no vessel. Label values 5-21 are fixed here and never reused.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, Optional, Sequence

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

#: The classes expected to be non-empty (D13); flagged for review, not refused.
REQUIRED: List[str] = [row[1] for row in _TABLE if row[3]]

#: What annotators are told (D25, D26, D12). Shown in the SegQueue14 panel and served
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
    "outline to the contrast-filled lumen. Note anything unusual."
)

#: Project name served by default.
PROJECT_NAME = "Coronary segmentation, 4 classes"

#: Name of the label config this table must match (configs/labels/<name>.yaml).
LABEL_SET_NAME = "coronary_icx4"


# ----------------------------------------------------- extended classes (D44)

#: Groups of the extended classes, in panel order. "Vessels" is the four above.
GROUP_VESSELS = "Vessels"
GROUP_MATERIALS = "Materials"
GROUP_LAD = "LAD branches"
GROUP_LCX = "LCx branches"
GROUP_RCA = "RCA branches"
GROUP_OTHER = "Other"
GROUPS = (GROUP_VESSELS, GROUP_LAD, GROUP_LCX, GROUP_OTHER, GROUP_RCA, GROUP_MATERIALS)

#: ``(label, name, colour, group, parent, hint)`` in label order. ``parent`` is the
#: vessel a branch is folded into for scoring (D44; PDA, PLB and SN always RCA, the
#: ramus always LCx as D1b); a material has none. Label values are pinned: a draft
#: or a stored read keeps them forever, so a value is never reassigned or reused.
#: Colours: branches are shades of their parent's colour, materials stand apart.
_EXTRA_TABLE = (
    (5, "Stent", (0.80, 0.80, 0.86), GROUP_MATERIALS, None,
     "The stent: its metal struts, end to end. Leave the lumen inside it in its "
     "vessel class too; overlap is fine."),
    (6, "Calcified plaque", (0.95, 0.30, 0.85), GROUP_MATERIALS, None,
     "Calcified plaque: the bright, calcium-dense plaque in or on the vessel wall."),
    (7, "Non-calcified plaque", (0.55, 0.20, 0.65), GROUP_MATERIALS, None,
     "Non-calcified (soft) plaque: lower-density plaque in the vessel wall."),
    (8, "D1", (0.55, 0.92, 0.45), GROUP_LAD, "LAD",
     "First diagonal: the first diagonal branch off the LAD, over the lateral wall."),
    (9, "D2", (0.30, 0.85, 0.65), GROUP_LAD, "LAD",
     "Second diagonal off the LAD."),
    (10, "D3", (0.08, 0.50, 0.35), GROUP_LAD, "LAD",
     "Third diagonal off the LAD."),
    (11, "S1", (0.78, 0.88, 0.22), GROUP_LAD, "LAD",
     "First septal perforator: the first branch off the LAD into the septum."),
    (12, "S2", (0.52, 0.66, 0.08), GROUP_LAD, "LAD",
     "Second septal perforator off the LAD."),
    (13, "S3", (0.32, 0.42, 0.12), GROUP_LAD, "LAD",
     "Third septal perforator off the LAD."),
    (14, "OM1", (0.45, 0.70, 1.00), GROUP_LCX, "LCx",
     "First obtuse marginal off the LCx, over the lateral wall."),
    (15, "OM2", (0.15, 0.22, 0.62), GROUP_LCX, "LCx",
     "Second obtuse marginal off the LCx."),
    (16, "SN", (1.00, 0.92, 0.50), GROUP_RCA, "RCA",
     "Sinus node artery, to the sinus node (folded into RCA when scored, whichever "
     "artery it comes off)."),
    (17, "Conus", (0.95, 0.55, 0.08), GROUP_RCA, "RCA",
     "Conus branch: usually the first RCA branch, to the right ventricular outflow "
     "tract."),
    (18, "RMA", (0.78, 0.42, 0.20), GROUP_RCA, "RCA",
     "Right (acute) marginal: off the RCA along the acute margin of the right "
     "ventricle."),
    (19, "PDA", (0.62, 0.32, 0.04), GROUP_RCA, "RCA",
     "Posterior descending artery, in the posterior interventricular groove "
     "(folded into RCA when scored, whichever artery it comes off)."),
    (20, "PLB", (1.00, 0.68, 0.52), GROUP_RCA, "RCA",
     "Posterolateral branch, beyond the crux (folded into RCA when scored, "
     "whichever artery it comes off)."),
    (21, "Ramus", (0.15, 0.82, 0.92), GROUP_OTHER, "LCx",
     "Ramus intermedius: a third branch from the left main, between the LAD and "
     "LCx (folded into LCx when scored, D1b)."),
)

#: The 17 extended class names, in label order.
EXTRA_NAMES: List[str] = [row[1] for row in _EXTRA_TABLE]
#: The materials: never folded into a vessel.
MATERIALS: List[str] = [row[1] for row in _EXTRA_TABLE if row[4] is None]
#: ``{branch: parent vessel}`` for the 14 named branches.
PARENT: Dict[str, str] = {row[1]: row[4] for row in _EXTRA_TABLE if row[4]}
#: ``{name: group}`` for all 21 classes.
GROUP_OF: Dict[str, str] = {**{name: GROUP_VESSELS for name in NAMES},
                             **{row[1]: row[3] for row in _EXTRA_TABLE}}
#: All 21 names in label order: the channel order of an extended class stack.
ALL_NAMES: List[str] = NAMES + EXTRA_NAMES
#: ``{name: label value}`` for all 21.
ALL_LABEL_VALUES: Dict[str, int] = {**LABEL_VALUES,
                                     **{row[1]: row[0] for row in _EXTRA_TABLE}}
#: All 21 names grouped by parent, for the panel: each vessel followed by its
#: branches, then the materials.
DISPLAY_ORDER: List[str] = (
    ["LM", "LAD"] + [n for n in EXTRA_NAMES if GROUP_OF[n] == GROUP_LAD]
    + ["LCx"] + [n for n in EXTRA_NAMES if GROUP_OF[n] in (GROUP_LCX, GROUP_OTHER)]
    + ["RCA"] + [n for n in EXTRA_NAMES if GROUP_OF[n] == GROUP_RCA]
    + MATERIALS)

#: What annotators are told about the extended classes (D44), shown in the panel
#: when they are turned on; each class's own hint is in ``extra_segment_dicts``.
EXTENDED_INSTRUCTIONS = (
    "Extended classes are optional: leave any of them empty. LM, LAD, LCx and RCA "
    "start as before. To use a branch class, move that branch out of its parent "
    "into its class: D1-D3 and S1-S3 come out of LAD; OM1, OM2 and the ramus out "
    "of LCx; SN, conus, RMA, PDA and PLB out of RCA. Branches beyond the third "
    "diagonal or septal, or the second marginal, stay in the parent. Paint stent, "
    "calcified and non-calcified plaque where you see them; they may overlap the "
    "vessels. Every class is saved whole, overlaps included. When scored, each "
    "branch counts towards its parent; materials are scored on their own.")


def extra_segment_dicts() -> List[dict]:
    """The 17 extended classes as ``SegmentSpec.to_dict()``-shaped dicts, plus
    ``group`` and ``parent`` (which ``SegmentSpec`` ignores)."""
    return [
        {"name": name, "label": label, "color": list(colour), "required": False,
         "hint": hint, "group": group, "parent": parent}
        for label, name, colour, group, parent, hint in _EXTRA_TABLE
    ]


def extra_segment_specs() -> list:
    """The 17 extended classes as ``segqueue.protocol.SegmentSpec`` objects."""
    from segqueue.protocol import SegmentSpec

    return [SegmentSpec.from_dict(d) for d in extra_segment_dicts()]


def is_extended(names: Iterable[str]) -> bool:
    """Whether a read with these classes has any of the 17 extended ones."""
    extras = set(EXTRA_NAMES)
    return any(str(n) in extras for n in names)


def stack_names(extended: bool) -> List[str]:
    """The channels of a class stack: the four, or all 21 in label order."""
    return list(ALL_NAMES if extended else NAMES)


def collapse_to_four(masks, names: Sequence[str]):
    """``(4, ...)`` 0/1 masks in ``NAMES`` order from ``(C, ...)`` masks named ``names``.

    Each of the four vessels is its own mask unioned with every branch whose parent
    it is (``PARENT``, D44); materials and unknown names go into no vessel. A
    four-class read comes back unchanged (as uint8 0/1), so a 4-class read scores
    exactly as before, and an extended read scores like the same voxels drawn into
    the parents.
    """
    import numpy as np

    masks = np.asarray(masks)
    names = [str(n) for n in names]
    if masks.shape[0] != len(names):
        raise ValueError(f"{masks.shape[0]} channels for {len(names)} class names")
    out = np.zeros((len(NAMES),) + masks.shape[1:], np.uint8)
    index = {name: i for i, name in enumerate(NAMES)}
    for channel, name in enumerate(names):
        target = index.get(name, index.get(PARENT.get(name, ""), None))
        if target is not None:
            out[target] |= (masks[channel] != 0)
    return out


#: ImageCAS-X's 14 label values -> these four (D1 territory, D1b ramus -> LCx).
#: ImageCAS-X "Other" (14: D3/D4, OM3/OM4) has no fixed parent and is not in this
#: table; ``icx14_to_four`` gives it the nearest LAD/LCx class (D25), as the
#: training labels do.
ICX14_TO_4: Dict[int, int] = {
    1: 1,                                   # LM
    2: 2, 4: 2, 5: 2,                       # LAD, D1, D2
    3: 3, 6: 3, 7: 3, 8: 3, 12: 3, 13: 3,   # LCx, OM1, OM2, IM, L-PDA, L-PLA
    9: 4, 10: 4, 11: 4,                     # RCA, R-PDA, R-PLA
}

#: ImageCAS-X's "Other" label value (D3/D4, OM3/OM4).
ICX_OTHER = 14


def icx14_to_four(icx14, spacing=None):
    """An ImageCAS-X 14-class label array in the project's four classes (D25).

    Values 1-13 go by ``ICX14_TO_4``. "Other" (14) takes the class of the nearest
    LAD or LCx voxel, measured in mm with ``spacing`` (voxel size in the array's
    axis order; for a SimpleITK or Slicer array that is the image spacing
    reversed). This is the rule the icx4 training labels use
    (``trillium/icx4/lib/territory.py``, ``segtrain.reads.icx_to_territory``);
    tests pin all three together. Other with no LAD/LCx in the volume, and any
    value outside 1-14, becomes background.

    This is what a SegQueue14 case's reference asset always is
    (``referenceFileId``, ``protocol.ASSET_REFERENCE``: a file from
    ``SegQueue/imagecas-x/segmentations``), so callers collapse the reference
    because it is the reference, never because of its highest value: an
    ImageCAS-X file with no RCA has nothing above 4 and is still 14-class (#57).
    Reads, prelabels and seeds already speak the four and are never collapsed.

    numpy is imported here, not at module level, so this module still imports
    on a bare Python; scipy is used when present (the server's scoring extra)
    and a plain numpy search otherwise (Slicer may not ship scipy).
    """
    import numpy as np

    icx = np.asarray(icx14).astype(np.int64)
    table = np.zeros(ICX_OTHER + 1, np.uint8)
    for value, cls in ICX14_TO_4.items():
        table[value] = cls
    out = table[np.clip(icx, 0, ICX_OTHER)]
    out[(icx < 0) | (icx > ICX_OTHER)] = 0
    other = icx == ICX_OTHER
    if other.any():
        src = np.isin(out, (LABEL_VALUES["LAD"], LABEL_VALUES["LCx"]))
        if src.any():
            sp = np.ones(icx.ndim) if spacing is None else np.asarray(spacing, float)[:icx.ndim]
            src_pts = np.argwhere(src)
            other_pts = np.argwhere(other)
            near = _nearest(src_pts * sp, other_pts * sp)
            out[tuple(other_pts.T)] = out[tuple(src_pts[near].T)]
    return out


def _nearest(points, queries, use_scipy=True, budget=1 << 21):
    """Index into ``points`` of the nearest point to each of ``queries``.

    Without scipy, queries go in chunks of about ``budget`` distances at a time
    (16 MB of float64), so a whole coronary tree stays small in memory.
    """
    import numpy as np

    if use_scipy:
        try:
            from scipy.spatial import cKDTree
        except ImportError:
            pass
        else:
            return cKDTree(points).query(queries)[1]
    best = np.empty(len(queries), np.int64)
    chunk = max(1, budget // max(1, len(points)))
    for start in range(0, len(queries), chunk):
        q = queries[start:start + chunk]
        d2 = np.zeros((len(q), len(points)))
        for axis in range(points.shape[1]):
            d2 += (q[:, None, axis] - points[None, :, axis]) ** 2
        best[start:start + chunk] = d2.argmin(axis=1)
    return best


def segment_dicts() -> List[dict]:
    """The table as ``SegmentSpec.to_dict()``-shaped dicts (the setting's form)."""
    return [
        {"name": name, "label": label, "color": list(colour),
         "required": required, "hint": hint}
        for label, name, colour, required, hint in _TABLE
    ]


def segment_specs() -> list:
    """The table as ``segqueue.protocol.SegmentSpec`` objects."""
    from segqueue.protocol import SegmentSpec

    return [SegmentSpec.from_dict(d) for d in segment_dicts()]


def missing_required(voxel_counts: Mapping[str, int],
                     required: Optional[Iterable[str]] = None) -> List[str]:
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
