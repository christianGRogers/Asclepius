"""The 14 ImageCAS-X classes, as SegQueue14 segments.

One table, imported by the Girder plugin (the default ``segqueue14.project``
setting), the Slicer module (the prelabel import and the submit check) and the
tests that pin ``configs/labels/coronary_icx14.yaml`` to it. Label values are
ImageCAS-X's own (Suppl. Table 4), which are also the values the 14-class model
writes into its predictions (``trillium/icx14/README.md``), so a prelabel, a
submission, an ImageCAS-X reference and a training label all mean the same thing
by the same integer.

Decisions (vault/Plans/Human decisions.md):

* D9  -- all 14 ImageCAS-X classes, no grouping into four vessels.
* D12 -- annotators may freely redraw the outline to the contrast-filled lumen.
* D13 -- LAD, LCx and RCA must be non-empty to submit; the other 11 are optional.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Mapping

#: ``(label, name, colour, required, hint)`` in label order. Names are the short
#: ImageCAS-X names; they are also the per-class file names in a training export
#: (``segmentations/<name>.nii.gz``) and the keys of the label config.
_TABLE = (
    (1, "LM", (0.95, 0.25, 0.20), False,
     "Left main: ostium to the LAD/LCx (or trifurcation) split."),
    (2, "LAD", (0.20, 0.70, 0.30), True,
     "LAD trunk in the anterior interventricular groove, to the apex."),
    (3, "LCx", (0.25, 0.45, 0.90), True,
     "LCx trunk in the left atrioventricular groove."),
    (4, "D1", (0.60, 0.90, 0.30), False,
     "First diagonal branch of the LAD."),
    (5, "D2", (0.10, 0.45, 0.20), False,
     "Second diagonal branch of the LAD."),
    (6, "OM1", (0.45, 0.75, 1.00), False,
     "First obtuse marginal branch of the LCx."),
    (7, "OM2", (0.15, 0.20, 0.60), False,
     "Second obtuse marginal branch of the LCx."),
    (8, "IM", (0.65, 0.35, 0.85), False,
     "Ramus intermedius, between the LAD and the LCx."),
    (9, "RCA", (0.95, 0.75, 0.15), True,
     "RCA trunk in the right atrioventricular groove."),
    (10, "R-PDA", (0.95, 0.50, 0.10), False,
     "Posterior descending artery arising from the RCA."),
    (11, "R-PLA", (0.70, 0.45, 0.15), False,
     "Posterolateral branch arising from the RCA."),
    (12, "L-PDA", (0.10, 0.75, 0.75), False,
     "Posterior descending artery arising from the LCx."),
    (13, "L-PLA", (0.95, 0.45, 0.70), False,
     "Posterolateral branch arising from the LCx."),
    (14, "Other", (0.65, 0.65, 0.65), False,
     "Later diagonals and marginals: D3/D4, OM3/OM4."),
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
    "You are given a prediction of the coronary tree in 14 classes. Correct it: "
    "fix wrong names, add vessel the model missed, delete anything that is not a "
    "coronary artery (veins, other structures), and trim or extend the outline to "
    "the contrast-filled lumen. D1/D2 are the first and second diagonals and "
    "OM1/OM2 the first and second obtuse marginals; later diagonals and marginals "
    "(D3/D4, OM3/OM4) go in Other. A ramus intermedius is IM. PDA and PLA take the "
    "side they arise from (R- or L-). Note anything unusual."
)

#: Project name served by default.
PROJECT_NAME = "Coronary segmentation, 14 classes (prelabel correction)"

#: Name of the label config this table must match (configs/labels/<name>.yaml).
LABEL_SET_NAME = "coronary_icx14"


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
