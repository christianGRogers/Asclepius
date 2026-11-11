"""Per-class scores for a SegQueue14 read, and the rule that sends one to review.

Server-side only (the scoring worker and the tests): the array functions import
numpy on use, so importing this module stays stdlib-clean for the Slicer side,
which never calls them.

The metric is ``segtrain.metrics.agreement`` -- the same Dice and HD95 the live
SegQueue scores gold and duplicate cases with, and the training pipeline reports
-- applied to the project's classes (``labels.NAMES``), each scored from its
own mask (``score_masks``): a class-stack submission keeps every class whole,
overlaps included (D39), and an old label volume is split by value first. Two
additions:

* **presence** per class: is the vessel there in the read, in the reference, and
  do they agree. A missed L-PDA is a Dice of 0 *and* a presence disagreement; the
  second is the one a reviewer can act on at a glance.
* **extended reads** (D44): a read with the 17 extended classes is collapsed to
  the four first (``labels.collapse_to_four``: each branch into its parent;
  materials into nothing), so the headline stays four-class and a 4-class read
  scores exactly as before. ``score_reads`` does that and adds a per-material Dice
  (``materials``) for each material *both* reads have.
* **cropping** to the union of both labellings before scoring. Dice and HD95 are
  unchanged by it (the margin keeps every surface voxel's neighbourhood), and it
  turns one distance transform per class over a whole chest CT into one per class
  over the heart.
"""

from __future__ import annotations

from typing import Dict, List, Mapping, Optional, Sequence

from segqueue.policy import usable_score as _usable

from . import labels

#: Background voxels kept around the union bounding box. >= 1 is what keeps the
#: erosion in ``segtrain.metrics._surface`` identical to the uncropped one.
CROP_MARGIN = 2


def crop_to_union(a, b, margin: int = CROP_MARGIN):
    """``(a, b)`` cut to the bounding box of ``(a > 0) | (b > 0)`` plus a margin.

    3D label volumes, or 4D class stacks ``(class, z, y, x)``: a stack is cut on
    its three spatial axes, every class alike.
    """
    import numpy as np

    either = (a > 0) | (b > 0)
    stacked = either.ndim == 4
    if stacked:
        either = either.any(axis=0)
    lead = (slice(None),) if stacked else ()
    if not either.any():
        return a[lead + (slice(0, 1),) * 3], b[lead + (slice(0, 1),) * 3]
    slices = []
    for axis in range(either.ndim):
        other = tuple(i for i in range(either.ndim) if i != axis)
        hit = np.flatnonzero(either.any(axis=other))
        lo = max(0, int(hit[0]) - margin)
        hi = min(either.shape[axis], int(hit[-1]) + 1 + margin)
        slices.append(slice(lo, hi))
    window = lead + tuple(slices)
    return a[window], b[window]


def as_masks(volume, names: Optional[Sequence[str]] = None):
    """``(class, z, y, x)`` 0/1 masks: a class stack as it is, a label volume by value.

    A 3D array is an old single-label submission (or a reference) in the
    project's values, ``names[i]`` being label ``i + 1``; a 4D one is already a
    class stack in ``names`` order.
    """
    import numpy as np

    names = list(labels.NAMES if names is None else names)
    volume = np.asarray(volume)
    if volume.ndim == 4:
        if volume.shape[0] != len(names):
            raise ValueError(f"{volume.shape[0]} channels for {len(names)} classes")
        return (volume != 0).astype(np.uint8)
    return np.stack([(volume == i) for i in range(1, len(names) + 1)]).astype(np.uint8)


def mask_counts(masks, names: Optional[Sequence[str]] = None) -> Dict[str, int]:
    """``{class name: voxels}`` from ``(class, ...)`` masks, each class counted whole."""
    import numpy as np

    names = list(labels.NAMES if names is None else names)
    return {name: int(np.count_nonzero(masks[i])) for i, name in enumerate(names)}


def voxel_counts(volume, names: Optional[Sequence[str]] = None) -> Dict[str, int]:
    """``{class name: voxels}`` for a label volume in the project's label values.

    ``names[i]`` is the class written as label ``i + 1``.
    """
    import numpy as np

    names = list(labels.NAMES if names is None else names)
    counts = np.bincount(np.asarray(volume, dtype=np.int64).ravel(),
                         minlength=len(names) + 1)
    return {name: int(counts[i]) for i, name in enumerate(names, start=1)
            if i < len(counts)}


def score_labels(read, reference, spacing: Sequence[float],
                 names: Optional[Sequence[str]] = None) -> dict:
    """Score a read against a reference on the same grid.

    ``read`` and ``reference`` are integer arrays in the same index order with the
    same shape; ``spacing`` is per axis in that order. Returns the
    ``segtrain.metrics.agreement`` dict with ``voxels_read`` / ``voxels_ref`` and
    presence per class, plus ``presence_agreement`` and ``required_min_dice``.
    """
    names = list(labels.NAMES if names is None else names)
    return score_masks(as_masks(read, names), as_masks(reference, names), spacing, names)


def score_masks(read, reference, spacing: Sequence[float],
                names: Optional[Sequence[str]] = None) -> dict:
    """``score_labels`` from ``(class, z, y, x)`` masks: each class from its own.

    Where classes overlap (D39) each keeps all of its voxels, so a read whose four
    classes are full copies of the tree scores every class against the
    reference, not only the one a label volume would have kept.
    """
    from segtrain.metrics import agreement_masks

    names = list(labels.NAMES if names is None else names)
    if read.shape != reference.shape:
        raise ValueError(f"shapes differ: {read.shape} != {reference.shape}")
    a, b = crop_to_union(read, reference)
    result = agreement_masks(a, b, names, spacing)

    agree = 0
    for name in names:
        entry = result["per_structure"][name]
        entry["voxels_read"] = entry.pop("voxels_a")
        entry["voxels_ref"] = entry.pop("voxels_b")
        entry["present_read"] = entry["voxels_read"] > 0
        entry["present_ref"] = entry["voxels_ref"] > 0
        entry["presence_agrees"] = entry["present_read"] == entry["present_ref"]
        agree += int(entry["presence_agrees"])
    result["presence_agreement"] = round(agree / float(len(names)), 4) if names else None
    result["required_min_dice"] = required_min_dice(result)
    return result


def score_reads(read, read_names: Sequence[str], reference,
                reference_names: Sequence[str], spacing: Sequence[float]) -> dict:
    """Score two class stacks whose classes may differ (D44).

    ``read`` and ``reference`` are ``(class, z, y, x)`` masks on the same grid,
    named ``read_names`` and ``reference_names`` (the four, or all 21). Both are
    collapsed to the four and scored by ``score_masks``: the headline. A material
    that both name gets its own entry under ``materials``; a material only one of
    them has is not scored (one annotator not using a class is not disagreement).
    ``extended`` (only when either side has extended classes) says which.
    """
    a = labels.collapse_to_four(read, read_names)
    b = labels.collapse_to_four(reference, reference_names)
    result = score_masks(a, b, spacing)
    materials = material_scores(read, read_names, reference, reference_names, spacing)
    if materials:
        result["materials"] = materials
    extended = {"read": labels.is_extended(read_names),
                "reference": labels.is_extended(reference_names)}
    if any(extended.values()):
        # Only when there is something to say: a 4-class pair's stored score is
        # exactly what it was before D44.
        result["extended"] = extended
    return result


def material_scores(read, read_names: Sequence[str], reference,
                    reference_names: Sequence[str], spacing: Sequence[float]) -> dict:
    """``{material: {dice, hd95, voxels_read, voxels_ref}}`` for each material in both."""
    from segtrain.metrics import agreement_masks

    mine = {str(n): i for i, n in enumerate(read_names)}
    theirs = {str(n): i for i, n in enumerate(reference_names)}
    out = {}
    for name in labels.MATERIALS:
        if name not in mine or name not in theirs:
            continue
        a, b = crop_to_union(read[mine[name]] != 0, reference[theirs[name]] != 0)
        entry = agreement_masks([a], [b], [name], spacing)["per_structure"][name]
        out[name] = {"dice": entry["dice"], "hd95": entry["hd95"],
                     "voxels_read": entry["voxels_a"], "voxels_ref": entry["voxels_b"]}
    return out


def required_min_dice(result: Mapping,
                      required: Optional[Sequence[str]] = None) -> Optional[float]:
    """Lowest Dice among the required classes that are in either volume."""
    values = []
    for name in (labels.REQUIRED if required is None else required):
        dice = (result.get("per_structure", {}).get(name) or {}).get("dice")
        if dice is not None:
            values.append(float(dice))
    return min(values) if values else None


def reference_flags(result: Optional[Mapping], thresholds: Mapping) -> List[str]:
    """Plain-language reasons a reference-scored read needs a reviewer, or []."""
    if not result:
        return []
    if result.get("error"):
        return [f"could not be scored against ImageCAS-X: {result['error']}"]
    reasons = []
    mean = result.get("mean_dice")
    flag = thresholds.get("mean_dice_flag")
    if _usable(mean) and _usable(flag) and mean < flag:
        reasons.append(f"mean Dice {mean:.2f} against ImageCAS-X (< {flag:.2f})")
    low = result.get("required_min_dice")
    flag = thresholds.get("required_dice_flag")
    if _usable(low) and _usable(flag) and low < flag:
        worst = [n for n in labels.REQUIRED
                 if (result["per_structure"].get(n) or {}).get("dice") == low]
        reasons.append("{} Dice {:.2f} against ImageCAS-X (< {:.2f})".format(
            "/".join(worst) or "a required class", low, flag))
    for name, flag in sorted((thresholds.get("class_dice_flags") or {}).items()):
        dice = (result.get("per_structure", {}).get(name) or {}).get("dice")
        if _usable(dice) and _usable(flag) and dice < flag:
            reasons.append(f"{name} Dice {dice:.2f} against ImageCAS-X (< {flag:.2f})")
    return reasons


def duplicate_flags(result: Optional[Mapping], thresholds: Mapping) -> List[str]:
    """Reasons a two-read pair disagrees enough to need a reviewer, or []."""
    if not result:
        return []
    if result.get("error"):
        return [f"could not be compared with the other read: {result['error']}"]
    mean = result.get("mean_dice")
    flag = thresholds.get("duplicate_mean_dice_flag")
    if _usable(mean) and _usable(flag) and mean < flag:
        return [f"mean Dice {mean:.2f} against the other read (< {flag:.2f})"]
    return []


def headline_dice(score: Optional[Mapping]) -> Optional[float]:
    """The one number a list shows: reference mean if scored, else the pair's."""
    if not score:
        return None
    for key in ("reference", "duplicate"):
        mean = (score.get(key) or {}).get("mean_dice")
        if _usable(mean):
            return mean
    return None
