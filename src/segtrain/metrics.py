"""Segmentation metrics: Dice, normalized surface distance, and HD95.

Dice and NSD are the two metrics the reference paper reports, and they answer different
questions. Dice measures volumetric overlap and is dominated by the interior of
a structure, so it flatters large organs and punishes thin ones -- a rib can be
segmented perfectly well and still score poorly simply because a one-voxel
boundary error removes a large fraction of a structure two voxels thick. NSD
measures how much of the *surface* is within a tolerance of the reference, which
is closer to "would a human have to fix this", and is the metric to trust for
ribs, vessels and muscle interfaces.

HD95 -- the 95th percentile of the symmetric surface distance -- came later, for
SegQueue's quality assurance: it is the number that says *how far off* a
disagreement is, in millimetres, which is what a reviewer deciding whether two
annotators drew the same vessel actually wants. It lives here rather than in the
platform code so that "how good is the model" and "how well do two students
agree" are computed by one implementation. Two implementations would eventually
disagree in a way nobody could explain, and both sets of numbers end up in the
same paper.

Absent structures are reported as NaN rather than 0, and NaN is excluded from
means. Scoring an absent structure as 0 would drag every whole-body average down
in proportion to how often the field of view is limited, which measures the
dataset's framing rather than the model.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy import ndimage

# Default NSD tolerance in mm. At 1.5 mm isotropic this is one voxel: it asks
# "is the boundary in the right place to within a voxel", which is about the
# level of agreement two human annotators would reach.
DEFAULT_NSD_TOLERANCE_MM = 1.5


@dataclass
class ClassScore:
    name: str
    label: int
    dice: float
    nsd: float
    ref_voxels: int
    pred_voxels: int

    @property
    def present_in_reference(self) -> bool:
        return self.ref_voxels > 0

    def as_row(self) -> dict:
        return {
            "structure": self.name,
            "label": self.label,
            "dice": self.dice,
            "nsd": self.nsd,
            "ref_voxels": self.ref_voxels,
            "pred_voxels": self.pred_voxels,
        }


def dice_score(pred: np.ndarray, ref: np.ndarray) -> float:
    """Dice for two boolean masks. NaN when the structure is in neither."""
    n_pred = int(pred.sum())
    n_ref = int(ref.sum())
    if n_pred == 0 and n_ref == 0:
        return float("nan")  # absent from both: nothing to score
    inter = int(np.logical_and(pred, ref).sum())
    return 2.0 * inter / (n_pred + n_ref)


def _surface(mask: np.ndarray) -> np.ndarray:
    """Boundary voxels: those in the mask with at least one background neighbour.

    A 6-connected structuring element is used so that a one-voxel-thick sheet is
    entirely surface, which is the correct reading for structures like ribs.
    """
    if not mask.any():
        return np.zeros_like(mask, dtype=bool)
    eroded = ndimage.binary_erosion(mask, ndimage.generate_binary_structure(3, 1),
                                    border_value=0)
    return np.logical_and(mask, ~eroded)


def surface_distances(
    pred: np.ndarray,
    ref: np.ndarray,
    spacing: Sequence[float],
) -> tuple[np.ndarray, np.ndarray]:
    """Distances from each predicted surface voxel to the reference surface, and back.

    Both directions are needed: one alone cannot distinguish a prediction that
    misses part of the structure from one that adds a spurious lobe.
    """
    pred_s = _surface(pred)
    ref_s = _surface(ref)
    if not pred_s.any() or not ref_s.any():
        return np.array([]), np.array([])

    # distance_transform_edt measures distance to the nearest *zero*, so invert
    # the surface masks. `sampling` makes the result physical millimetres.
    dt_to_ref = ndimage.distance_transform_edt(~ref_s, sampling=spacing)
    dt_to_pred = ndimage.distance_transform_edt(~pred_s, sampling=spacing)
    return dt_to_ref[pred_s], dt_to_pred[ref_s]


def normalized_surface_distance(
    pred: np.ndarray,
    ref: np.ndarray,
    spacing: Sequence[float],
    tolerance_mm: float = DEFAULT_NSD_TOLERANCE_MM,
) -> float:
    """Fraction of both surfaces lying within ``tolerance_mm`` of the other."""
    n_pred, n_ref = int(pred.sum()), int(ref.sum())
    if n_pred == 0 and n_ref == 0:
        return float("nan")
    if n_pred == 0 or n_ref == 0:
        return 0.0

    d_pred_to_ref, d_ref_to_pred = surface_distances(pred, ref, spacing)
    total = d_pred_to_ref.size + d_ref_to_pred.size
    if total == 0:
        return float("nan")
    within = int((d_pred_to_ref <= tolerance_mm).sum()) + int(
        (d_ref_to_pred <= tolerance_mm).sum()
    )
    return within / total


def hausdorff95(
    pred: np.ndarray,
    ref: np.ndarray,
    spacing: Sequence[float],
) -> float:
    """95th-percentile symmetric Hausdorff distance, in millimetres.

    Added for the annotation platform rather than for training. NSD answers
    "how much of the boundary is right", which is what you want when comparing
    models; HD95 answers "how far wrong is the worst part", which is what you
    want when deciding whether a student has misplaced a whole vessel. A
    gold-standard case can score a respectable Dice while an entire distal
    branch sits ten millimetres away, and only HD95 says so.

    The 95th percentile rather than the maximum, for the usual reason: a single
    voxel of noise should not decide the number.

    NaN when the structure is absent from both, and +inf when it is present in
    exactly one -- there is no finite distance to an empty set, and returning a
    large finite number instead would quietly pollute any mean taken over it.
    """
    n_pred, n_ref = int(pred.sum()), int(ref.sum())
    if n_pred == 0 and n_ref == 0:
        return float("nan")
    if n_pred == 0 or n_ref == 0:
        return float("inf")

    d_pred_to_ref, d_ref_to_pred = surface_distances(pred, ref, spacing)
    if d_pred_to_ref.size == 0 or d_ref_to_pred.size == 0:
        return float("nan")
    return float(max(
        np.percentile(d_pred_to_ref, 95),
        np.percentile(d_ref_to_pred, 95),
    ))


def agreement(
    a_labels: np.ndarray,
    b_labels: np.ndarray,
    names: Sequence[str],
    spacing: Sequence[float],
) -> dict:
    """Per-structure Dice and HD95 between two labellings of the same case.

    Used two ways by SegQueue, with no difference in the computation: against an
    expert reference (a gold case) and against a second annotator (a blind
    duplicate). Keeping it symmetric is deliberate -- for a duplicate pair there
    is no ground truth, so any metric that treated one argument as correct would
    be reporting something it cannot know.

    ``inf`` is serialised as ``None`` so the result drops straight into JSON.
    """
    if a_labels.shape != b_labels.shape:
        raise ValueError(
            f"shapes differ: {a_labels.shape} != {b_labels.shape}"
        )

    per_structure = {}
    dices = []
    for idx, name in enumerate(names, start=1):
        a = a_labels == idx
        b = b_labels == idx
        d = dice_score(a, b)
        h = hausdorff95(a, b, spacing)
        per_structure[name] = {
            "dice": None if d != d else round(d, 4),
            "hd95": None if (h != h or h == float("inf")) else round(h, 3),
            "voxels_a": int(a.sum()),
            "voxels_b": int(b.sum()),
        }
        dices.append(d)

    return {
        "mean_dice": nanmean(dices),
        "per_structure": per_structure,
    }


def score_case(
    pred_labels: np.ndarray,
    ref_labels: np.ndarray,
    names: Sequence[str],
    spacing: Sequence[float],
    tolerance_mm: float = DEFAULT_NSD_TOLERANCE_MM,
    compute_nsd: bool = True,
    only_labels: Optional[Iterable[int]] = None,
) -> list[ClassScore]:
    """Score every class of one case.

    ``names`` is in label-index order, so ``names[i]`` is label ``i + 1``.

    NSD is far more expensive than Dice -- two distance transforms over the whole
    volume per class -- so ``compute_nsd=False`` is the right choice for the
    live previews during training, where speed matters and relative movement is
    what you are watching.
    """
    if pred_labels.shape != ref_labels.shape:
        raise ValueError(
            f"prediction shape {pred_labels.shape} != reference shape {ref_labels.shape}"
        )

    wanted = set(only_labels) if only_labels is not None else None
    scores: list[ClassScore] = []

    for idx, name in enumerate(names, start=1):
        if wanted is not None and idx not in wanted:
            continue
        pred = pred_labels == idx
        ref = ref_labels == idx
        d = dice_score(pred, ref)
        if compute_nsd:
            n = normalized_surface_distance(pred, ref, spacing, tolerance_mm)
        else:
            n = float("nan")
        scores.append(
            ClassScore(
                name=name,
                label=idx,
                dice=d,
                nsd=n,
                ref_voxels=int(ref.sum()),
                pred_voxels=int(pred.sum()),
            )
        )
    return scores


def nanmean(values: Iterable[float]) -> float:
    """Mean over present structures. NaN if nothing was present at all."""
    vals = [v for v in values if v == v]  # NaN != NaN
    return float(np.mean(vals)) if vals else float("nan")


def summarize_case(scores: Sequence[ClassScore]) -> dict:
    return {
        "mean_dice": nanmean(s.dice for s in scores),
        "mean_nsd": nanmean(s.nsd for s in scores),
        "n_present": sum(1 for s in scores if s.present_in_reference),
        "n_classes": len(scores),
    }


def dice_dict(scores: Sequence[ClassScore]) -> dict[str, float]:
    """Per-structure Dice as a plain dict, for embedding in a preview event.

    NaN is dropped rather than serialised: JSON has no NaN, and an absent
    structure is better represented by absence than by a null the UI must
    special-case.
    """
    return {s.name: round(s.dice, 4) for s in scores if s.dice == s.dice}


def aggregate(
    per_case: dict[str, Sequence[ClassScore]],
) -> dict[str, dict[str, float]]:
    """Average each structure's metrics across cases.

    Keyed by structure name; each value carries mean Dice, mean NSD, and how many
    cases actually contained the structure. That count is essential context: a
    Dice of 0.62 over 3 cases and over 80 cases mean very different things.
    """
    by_structure: dict[str, list[ClassScore]] = {}
    for scores in per_case.values():
        for s in scores:
            by_structure.setdefault(s.name, []).append(s)

    out: dict[str, dict[str, float]] = {}
    for name, scores in by_structure.items():
        present = [s for s in scores if s.present_in_reference]
        out[name] = {
            "dice": nanmean(s.dice for s in scores),
            "nsd": nanmean(s.nsd for s in scores),
            "n_cases_present": len(present),
            "n_cases": len(scores),
        }
    return out
