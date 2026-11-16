"""Two annotators' reads of one case, voxel against voxel (#335).

The reviewer's "Compare reads" view in the module: which reads of a case there
are to compare, and, for the two picked, where they agree and where they do not.
Pure numpy (imported on use), so the module runs it inside Slicer and the tests
run it without; importing this module stays stdlib-clean.

**Which reads** (``comparable_reads``): annotator reads only -- a reviewer's
revision is not a read. By default the reads the server pairs and scores: the
latest annotator submission on each assignment, and not a read reopened for its
annotator's own revision (#315). A reopened read is recognised from the row's
``reopened`` flag when the server sends one, else from its assignment being back
in the annotator's hands (``assigned``/``downloaded``), or superseded by a later
submission on the same assignment once the annotator has resubmitted. With
``include_reopened`` every annotator read is offered.

**Which classes** (``align``), as the issue and D44/D47 say:

* a four-class read against anything: both are collapsed to the four
  (``labels.collapse_to_four``, PDA/PLB/SN by contact, D47 Q1) and compared as
  LM, LAD, LCx and RCA -- exactly what the server's pair score compares;
* two extended reads: class by class, every class both reads have (the four
  vessels as drawn, each branch, each material).

**The numbers** (``agreement``): per class the voxels in both reads, in A only and
in B only, and the Dice ``2|A&B| / (|A|+|B|)`` -- ``segtrain.metrics.dice_score``,
rounded to four places as the server stores it, ``None`` when the class is in
neither. ``mean_dice`` is the mean over the classes in either read, as the
server's. ``compare_reads`` adds ``headline``: the four-class collapse, which is
the server's pair score whatever the mode (for two extended reads it is the
number the quality report shows, and the class-by-class map is the detail).
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Mapping, Optional, Sequence

from . import labels

#: Comparing after the collapse to the four vessels (either read is four-class).
MODE_FOUR = "four"
#: Comparing class by class (both reads are extended).
MODE_CLASSES = "classes"

#: Read keys, in the order reads are offered: A and B are the agreement pair.
KEYS = tuple("ABCDEFGH")

#: One colour per read for the side-by-side view, by ``KEYS`` position. Chosen to
#: be told apart from each other and from the CT's grey, not from the classes.
READ_COLOURS = (
    (0.90, 0.25, 0.25),   # A red
    (0.20, 0.70, 0.95),   # B sky blue
    (0.95, 0.80, 0.15),   # C yellow
    (0.65, 0.40, 0.90),   # D violet
    (0.30, 0.80, 0.40),   # E green
    (0.95, 0.55, 0.15),   # F orange
    (0.90, 0.45, 0.75),   # G pink
    (0.60, 0.60, 0.60),   # H grey
)

#: The agreement map's three categories: (key, label, colour).
BOTH = "both"
A_ONLY = "a_only"
B_ONLY = "b_only"
CATEGORIES = (
    (BOTH, "both", (0.95, 0.95, 0.95)),
    (A_ONLY, "A only", READ_COLOURS[0]),
    (B_ONLY, "B only", READ_COLOURS[1]),
)

#: The class selector's "every class" entry.
ALL_CLASSES = "All classes"

#: Assignment states that mean a read went back to its annotator (#315 reopen).
_BACK_WITH_ANNOTATOR = frozenset({"assigned", "downloaded"})


# ----------------------------------------------------------------- the reads


def is_annotator_read(row: Mapping) -> bool:
    """Whether a case-submissions row is an annotator's read (not a revision)."""
    return (row.get("authorRole") or "annotator") == "annotator" and bool(
        row.get("submissionId"))


def reopened_ids(rows: Sequence[Mapping]) -> set:
    """The submission ids among ``rows`` that are not live annotator reads.

    The server's ``reopened`` flag where a row has it; otherwise a read whose
    assignment is back with the annotator, or one a later annotator submission on
    the same assignment replaced. ``rows`` are oldest first, as the server sends.
    """
    out = set()
    latest = {}
    for row in rows:
        if not is_annotator_read(row):
            continue
        sid = row["submissionId"]
        if row.get("reopened"):
            out.add(sid)
        elif "reopened" not in row and row.get("state") in _BACK_WITH_ANNOTATOR:
            out.add(sid)
        assignment = row.get("assignmentId")
        if assignment:
            if assignment in latest:
                out.add(latest[assignment])
            latest[assignment] = sid
    return out


def comparable_reads(rows: Sequence[Mapping], include_reopened: bool = False) -> List[dict]:
    """The annotator reads of a case to offer, oldest first, each keyed A, B, ...

    Each is the row with ``key`` and ``reopened`` added. At most ``len(KEYS)``.
    """
    stale = reopened_ids(rows)
    out = []
    for row in rows:
        if not is_annotator_read(row):
            continue
        reopened = row["submissionId"] in stale
        if reopened and not include_reopened:
            continue
        if len(out) == len(KEYS):
            break
        entry = dict(row)
        entry["key"] = KEYS[len(out)]
        entry["reopened"] = reopened
        out.append(entry)
    return out


def read_label(read: Mapping) -> str:
    """``A: login, attempt 2 (extended)`` -- how a read is named in the panel."""
    login = (read.get("annotator") or {}).get("login") or "?"
    text = "{}: {}".format(read.get("key", "?"), login)
    attempt = read.get("benchmarkAttempt") or read.get("attempt")
    try:
        if int(attempt) > 1:
            text += f", attempt {int(attempt)}"
    except (TypeError, ValueError):
        pass
    if read.get("extended"):
        text += " (extended)"
    if read.get("reopened"):
        text += " [reopened]"
    return text


def read_colour(key: str):
    """The side-by-side colour of read ``key``."""
    index = KEYS.index(key) if key in KEYS else len(READ_COLOURS) - 1
    return READ_COLOURS[index % len(READ_COLOURS)]


# --------------------------------------------------------------- the classes


def mode_for(a_names: Iterable[str], b_names: Iterable[str]) -> str:
    """``MODE_CLASSES`` when both reads are extended, else ``MODE_FOUR``."""
    a_names, b_names = list(a_names), list(b_names)
    if labels.is_extended(a_names) and labels.is_extended(b_names):
        return MODE_CLASSES
    return MODE_FOUR


def align(a, a_names: Sequence[str], b, b_names: Sequence[str],
          mode: Optional[str] = None):
    """``(names, a, b, mode)``: both reads as ``(class, ...)`` masks over ``names``.

    ``a`` and ``b`` are ``(C, z, y, x)`` masks on the same grid, named ``a_names``
    and ``b_names``. ``mode`` defaults to ``mode_for``.
    """
    import numpy as np

    a_names = [str(n) for n in a_names]
    b_names = [str(n) for n in b_names]
    mode = mode or mode_for(a_names, b_names)
    a = np.asarray(a)
    b = np.asarray(b)
    if a.shape[1:] != b.shape[1:]:
        raise ValueError(f"the reads are on different grids: {a.shape[1:]} != {b.shape[1:]}")
    if mode == MODE_FOUR:
        return (list(labels.NAMES), labels.collapse_to_four(a, a_names),
                labels.collapse_to_four(b, b_names), mode)
    names = [n for n in labels.ALL_NAMES if n in a_names and n in b_names]
    pick_a = [a_names.index(n) for n in names]
    pick_b = [b_names.index(n) for n in names]
    return (names, (a[pick_a] != 0).astype(np.uint8),
            (b[pick_b] != 0).astype(np.uint8), mode)


# --------------------------------------------------------------- the numbers


def dice(both: int, voxels_a: int, voxels_b: int) -> Optional[float]:
    """``segtrain.metrics.dice_score`` from counts, rounded as the server stores it."""
    if voxels_a == 0 and voxels_b == 0:
        return None
    return round(2.0 * both / (voxels_a + voxels_b), 4)


def class_agreement(a, b) -> dict:
    """``{both, a_only, b_only, voxels_a, voxels_b, dice}`` for one class's masks."""
    import numpy as np

    a = np.asarray(a) != 0
    b = np.asarray(b) != 0
    if a.shape != b.shape:
        raise ValueError(f"shapes differ: {a.shape} != {b.shape}")
    voxels_a = int(np.count_nonzero(a))
    voxels_b = int(np.count_nonzero(b))
    both = int(np.count_nonzero(a & b))
    return {"both": both, "a_only": voxels_a - both, "b_only": voxels_b - both,
            "voxels_a": voxels_a, "voxels_b": voxels_b,
            "dice": dice(both, voxels_a, voxels_b)}


def agreement(a, b, names: Sequence[str]) -> dict:
    """``{"names", "per_class": {name: class_agreement}, "mean_dice", "n_scored"}``."""
    per_class = {name: class_agreement(a[i], b[i]) for i, name in enumerate(names)}
    scored = [entry["dice"] for entry in per_class.values() if entry["dice"] is not None]
    mean = round(sum(scored) / len(scored), 4) if scored else None
    return {"names": list(names), "per_class": per_class, "mean_dice": mean,
            "n_scored": len(scored)}


def compare_reads(a, a_names: Sequence[str], b, b_names: Sequence[str]) -> dict:
    """``agreement`` of two reads in their mode, plus ``mode`` and ``headline``.

    ``headline`` is always the four-class collapse: the server's pair score.
    ``masks`` holds the aligned ``(names, a, b)`` for drawing the map.
    """
    names, a_al, b_al, mode = align(a, a_names, b, b_names)
    result = agreement(a_al, b_al, names)
    result["mode"] = mode
    if mode == MODE_FOUR:
        result["headline"] = {k: result[k] for k in ("per_class", "mean_dice", "n_scored")}
    else:
        four, a4, b4, _ = align(a, a_names, b, b_names, mode=MODE_FOUR)
        head = agreement(a4, b4, four)
        result["headline"] = {k: head[k] for k in ("per_class", "mean_dice", "n_scored")}
    result["masks"] = (names, a_al, b_al)
    return result


def category_masks(a, b) -> Dict[str, object]:
    """``{BOTH, A_ONLY, B_ONLY: bool mask}`` for one class's two masks."""
    import numpy as np

    a = np.asarray(a) != 0
    b = np.asarray(b) != 0
    return {BOTH: a & b, A_ONLY: a & ~b, B_ONLY: b & ~a}


def summary_lines(result: Mapping, selected: str = ALL_CLASSES) -> List[str]:
    """Plain-text lines for the panel: one per class, then the server's headline."""
    lines = []
    for name in result["names"]:
        if selected not in (ALL_CLASSES, name):
            continue
        entry = result["per_class"][name]
        if not entry["voxels_a"] and not entry["voxels_b"]:
            lines.append(f"{name}: in neither read")
            continue
        lines.append("{}: Dice {}  |  both {:,}  A only {:,}  B only {:,}".format(
            name, "--" if entry["dice"] is None else "{:.3f}".format(entry["dice"]),
            entry["both"], entry["a_only"], entry["b_only"]))
    mean = result.get("mean_dice")
    if result.get("mode") == MODE_CLASSES:
        head = (result.get("headline") or {}).get("mean_dice")
        lines.append("Mean Dice, class by class: {}".format(
            "--" if mean is None else f"{mean:.3f}"))
        lines.append("Mean Dice after the four-class collapse (the pair score): {}".format(
            "--" if head is None else f"{head:.3f}"))
    else:
        lines.append("Mean Dice (the pair score): {}".format(
            "--" if mean is None else f"{mean:.3f}"))
    return lines


# ------------------------------------------------------------ cropping helper


def bounding_box(mask, margin: int = 2):
    """The slices of ``mask``'s bounding box ``margin`` voxels wider, or None if empty."""
    import numpy as np

    mask = np.asarray(mask) != 0
    if not mask.any():
        return None
    out = []
    for axis in range(mask.ndim):
        other = tuple(i for i in range(mask.ndim) if i != axis)
        hit = np.flatnonzero(mask.any(axis=other))
        out.append(slice(max(0, int(hit[0]) - margin),
                         min(mask.shape[axis], int(hit[-1]) + 1 + margin)))
    return tuple(out)


def union_box(boxes: Iterable, shape: Sequence[int]):
    """The smallest box holding every box in ``boxes`` (Nones skipped), or a 1-voxel
    box at the origin when all are None."""
    boxes = [b for b in boxes if b is not None]
    if not boxes:
        return tuple(slice(0, 1) for _ in shape)
    return tuple(slice(min(b[d].start for b in boxes), max(b[d].stop for b in boxes))
                 for d in range(len(shape)))
