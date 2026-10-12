"""Per-class scores for a SegQueue14 read, and the rule that sends one to review.

Server-side only (the scoring worker and the tests): the array functions import
numpy on use, so importing this module stays stdlib-clean for the Slicer side,
which never calls them.

The metric is ``segtrain.metrics.agreement`` -- the same Dice and HD95 the live
SegQueue scores gold and duplicate cases with, and the training pipeline reports
-- applied to the 14 ImageCAS-X classes, with two additions:

* **presence** per class: is the vessel there in the read, in the reference, and
  do they agree. A missed L-PDA is a Dice of 0 *and* a presence disagreement; the
  second is the one a reviewer can act on at a glance.
* **cropping** to the union of both labellings before scoring. Dice and HD95 are
  unchanged by it (the margin keeps every surface voxel's neighbourhood), and it
  turns fourteen distance transforms over a whole chest CT into fourteen over the
  heart.
"""

from __future__ import annotations

from typing import Dict, List, Mapping, Optional, Sequence

from . import labels

#: Background voxels kept around the union bounding box. >= 1 is what keeps the
#: erosion in ``segtrain.metrics._surface`` identical to the uncropped one.
CROP_MARGIN = 2


def crop_to_union(a, b, margin: int = CROP_MARGIN):
    """``(a, b)`` cut to the bounding box of ``(a > 0) | (b > 0)`` plus a margin."""
    import numpy as np

    either = (a > 0) | (b > 0)
    if not either.any():
        return a[:1, :1, :1], b[:1, :1, :1]
    slices = []
    for axis in range(either.ndim):
        other = tuple(i for i in range(either.ndim) if i != axis)
        hit = np.flatnonzero(either.any(axis=other))
        lo = max(0, int(hit[0]) - margin)
        hi = min(either.shape[axis], int(hit[-1]) + 1 + margin)
        slices.append(slice(lo, hi))
    window = tuple(slices)
    return a[window], b[window]


def voxel_counts(volume, names: Sequence[str] = None) -> Dict[str, int]:
    """``{class name: voxels}`` for a label volume with ImageCAS-X values."""
    import numpy as np

    names = list(labels.NAMES if names is None else names)
    counts = np.bincount(np.asarray(volume, dtype=np.int64).ravel(),
                         minlength=len(names) + 1)
    return {name: int(counts[i]) for i, name in enumerate(names, start=1)
            if i < len(counts)}


def score_labels(read, reference, spacing: Sequence[float],
                 names: Sequence[str] = None) -> dict:
    """Score a read against a reference on the same grid.

    ``read`` and ``reference`` are integer arrays in the same index order with the
    same shape; ``spacing`` is per axis in that order. Returns the
    ``segtrain.metrics.agreement`` dict with ``voxels_read`` / ``voxels_ref`` and
    presence per class, plus ``presence_agreement`` and ``required_min_dice``.
    """
    from segtrain.metrics import agreement

    names = list(labels.NAMES if names is None else names)
    if read.shape != reference.shape:
        raise ValueError(f"shapes differ: {read.shape} != {reference.shape}")
    a, b = crop_to_union(read, reference)
    result = agreement(a, b, names, spacing)

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


def required_min_dice(result: Mapping, required: Sequence[str] = None) -> Optional[float]:
    """Lowest Dice among the required classes that are in either volume."""
    values = []
    for name in (labels.REQUIRED if required is None else required):
        dice = (result.get("per_structure", {}).get(name) or {}).get("dice")
        if dice is not None:
            values.append(float(dice))
    return min(values) if values else None


def _usable(value) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return value == value and value not in (float("inf"), float("-inf"))


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
