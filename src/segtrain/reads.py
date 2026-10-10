"""Two reads per case: convention monitor, scoring, fusion targets and the wave-1 report.

Every case is labelled twice (decision D2), by annotators who split the original
ImageCAS mask into LM / LAD / LCx / RCA (D0, D4). This module is what turns those
reads into training targets and into numbers, as the master plan specifies:

- **A3, convention monitor.** A read must be a split of the ImageCAS mask, not a
  thinner re-drawing of the lumen. :func:`convention_check` flags a read as *thin*
  when the union of its classes has Dice < 0.9 against the mask, or when its calibre
  (share of centreline in lumen under 4 voxels across) sits nearer an ImageCAS-X
  lumen than the mask. :func:`wave_halts` stops a wave when more than 10 % of its
  reads are flagged.
- **A10, scoring and acceptance.** A model is scored per case by the mean tree-F1
  against each read (:func:`score_vs_reads`). It is accepted per class if it is
  non-inferior to the inter-read tF1 of the same cases within 0.02: the lower bound
  of the paired bootstrap 95 % CI of (model - inter-read) must exceed -0.02
  (:func:`acceptance`). No fused reference is ever built for scoring.
- **A11', training targets (Round 5).** Each read is its own training sample and keeps
  its own names and extent: no name-conflict ``ignore`` (:func:`a11_targets`; the old
  A11 rule survives only behind ``conflict_ignore=True`` for the conditional A11 test).
  Decision-level disagreements send the case to a third reader
  (:func:`third_read_triggers`), except a disagreement confined to a ramus candidate
  (D1b).
- **A12, the first-50 report** (:func:`first_reads_report`, runnable on a folder of
  reads), including the A12a annotator-habit test and the A12b carina anchor
  against ImageCAS-X, with the measured convention floor: +0.7 mm offset subtracted,
  medians not means, offsets beyond 5 mm sent to review
  (vault: "Crucible - The carina anchor has a sub-millimetre floor ...").

tree-F1 itself is not implemented here. There is exactly one implementation
(``segtrain.tf1``, amendment A9); every function that needs it takes a ``scorer``
callable, and :func:`default_scorer` adapts ``segtrain.tf1``. A scorer is
``scorer(reference, prediction, spacing) -> {class: tF1}`` over the classes present
in the reference.

Labels: 0 background, 1 LM, 2 LAD, 3 LCx, 4 RCA; ``IGNORE`` = 5 (nnU-Net requires
the ignore label to be the highest value).
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Callable, Optional

import numpy as np
from scipy import ndimage
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

from .proxy import (  # noqa: F401  (the one case-identity implementation)
    case_id,
    load_sealed,
    read_name,
    sealed_reason,
)

LM, LAD, LCX, RCA = 1, 2, 3, 4
CLASSES = (LM, LAD, LCX, RCA)
CLASS_NAMES = {
    LM: "left_main",
    LAD: "left_anterior_descending",
    LCX: "left_circumflex",
    RCA: "right_coronary_artery",
}
IGNORE = 5

# A3
THIN_DICE_THRESHOLD = 0.9
WAVE_HALT_FRACTION = 0.10
CALIBRE_VOXELS = 4
# A10
NONINFERIORITY_MARGIN = 0.02
# A11 third-read triggers (Atlas v3 / Round 3 A11)
THIRD_READ_TF1 = 0.80
THIRD_READ_DISTANCE_MM = 5.0
THIRD_READ_SWAP = 0.05
# A12b, measured on 124 non-sealed cases (robust SD 0.62 mm)
ANCHOR_CONVENTION_OFFSET_MM = 0.7
ANCHOR_BIAS_MM = 1.0
ANCHOR_REVIEW_MM = 5.0
ANCHOR_REVIEW_EUCLID_MM = 3.0
# A12a
HABIT_DIFFERENCE_MM = 1.0

# ImageCAS-X 14 classes -> 4 (territory D1, ramus -> LCx D1b, "Other" resolved by nearest LAD/LCx)
_ICX_TERRITORY = np.zeros(15, np.uint8)
_ICX_TERRITORY[[1]] = LM
_ICX_TERRITORY[[2, 4, 5]] = LAD
_ICX_TERRITORY[[3, 6, 7, 8, 12, 13]] = LCX
_ICX_TERRITORY[[9, 10, 11]] = RCA
_S26 = np.ones((3, 3, 3), bool)

Scorer = Callable[[np.ndarray, np.ndarray, Sequence[float]], Mapping[int, float]]


# ----------------------------------------------------------------------------- helpers
def _dice(a: np.ndarray, b: np.ndarray) -> float:
    s = int(a.sum()) + int(b.sum())
    return float(2 * np.logical_and(a, b).sum() / s) if s else float("nan")


def icx_to_territory(icx14: np.ndarray) -> np.ndarray:
    """ImageCAS-X 14-class labels -> 4 classes under D1 (territory) and D1b (ramus -> LCx).

    ImageCAS-X's "Other" (D3/D4/OM3/OM4) does not say which parent it hangs from; it
    takes the class of the nearest LAD or LCx voxel.
    """
    icx14 = np.asarray(icx14).astype(np.int64)
    out = _ICX_TERRITORY[np.clip(icx14, 0, 14)].copy()
    other = icx14 == 14
    if other.any():
        src = np.isin(out, (LAD, LCX))
        if src.any():
            _, ind = ndimage.distance_transform_edt(~src, return_indices=True)
            out[other] = out[tuple(ind)][other]
    return out


def default_scorer(**tf1_kwargs) -> Scorer:
    """The project's one tree-F1 (``segtrain.tf1.tree_f1``, A9) as ``scorer(ref, pred, spacing)``.

    ``tf1_kwargs`` are passed through (``aorta=`` for the A1 ostium of record, ``tol_mm=``).
    Returns ``{"per_class": {c: tF1}, "provisional": bool, "flagged": bool}`` from
    ``TreeF1``. Without an aorta mask the result is ``provisional`` (A1a: it decides
    nothing); ``flagged`` marks a tree whose ostium rules disagree (A1b: excluded from
    decisive aggregates until reviewed).
    """
    from .tf1 import tree_f1  # lazy: tf1 is owned by another module

    def scorer(ref, pred, spacing):
        res = tree_f1(ref, pred, spacing, **tf1_kwargs)
        return {
            "per_class": {int(k): float(v) for k, v in res.per_class.items() if np.isfinite(v)},
            "provisional": bool(res.provisional),
            "flagged": bool(res.flagged),
        }

    return scorer


def _unpack(res) -> tuple[dict, bool, bool]:
    """A scorer result -> (per_class, provisional, flagged).

    A plain ``{class: tF1}`` mapping (a stand-in scorer) carries no ostium information and
    is therefore treated as provisional.
    """
    if isinstance(res, Mapping) and "per_class" in res:
        per = {int(k): float(v) for k, v in dict(res["per_class"]).items()}
        return per, bool(res.get("provisional", True)), bool(res.get("flagged", False))
    if hasattr(res, "per_class"):
        per = {int(k): float(v) for k, v in res.per_class.items()}
        return per, bool(getattr(res, "provisional", True)), bool(getattr(res, "flagged", False))
    return {int(k): float(v) for k, v in dict(res).items()}, True, False


# ----------------------------------------------------------------------------- A3
def calibre_fraction(
    mask: np.ndarray, spacing: Sequence[float], voxels: int = CALIBRE_VOXELS
) -> float:
    """Share of centreline lying in lumen narrower than ``voxels`` in-plane voxels.

    Local diameter at a centreline voxel is 2 x EDT - in-plane spacing (the EDT to the
    nearest background voxel centre overshoots the boundary by half a voxel). Delta's E7:
    about 4 % on the original ImageCAS masks, about 65 % on the ImageCAS-X lumen.
    """
    from skimage.morphology import skeletonize

    m = np.asarray(mask) > 0
    if not m.any():
        return float("nan")
    sp = np.asarray(spacing, float)
    inplane = float(min(sp[:2]))
    sk = skeletonize(m)
    if not sk.any():
        return float("nan")
    diam = 2 * ndimage.distance_transform_edt(m, sampling=sp)[sk] - inplane
    return float(np.mean(diam < voxels * inplane))


@dataclass
class ConventionCheck:
    union_dice_vs_mask: float
    calibre_read: float
    calibre_mask: float
    calibre_icx: Optional[float]
    thin: bool
    reasons: list = field(default_factory=list)


def convention_check(
    read: np.ndarray,
    mask: np.ndarray,
    spacing: Sequence[float],
    icx_lumen: Optional[np.ndarray] = None,
    dice_threshold: float = THIN_DICE_THRESHOLD,
) -> ConventionCheck:
    """A3: is this read a split of the ImageCAS mask (pass) or a thin re-drawing (flag)?"""
    union = np.asarray(read) > 0
    m = np.asarray(mask) > 0
    d = _dice(union, m)
    c_read = calibre_fraction(union, spacing)
    c_mask = calibre_fraction(m, spacing)
    c_icx = calibre_fraction(np.asarray(icx_lumen) > 0, spacing) if icx_lumen is not None else None
    reasons = []
    if not d >= dice_threshold:
        reasons.append(f"union Dice vs ImageCAS mask {d:.3f} < {dice_threshold}")
    if c_icx is not None and np.isfinite(c_read) and abs(c_read - c_icx) < abs(c_read - c_mask):
        reasons.append(
            f"calibre {c_read:.2f} nearer ImageCAS-X ({c_icx:.2f}) than the mask ({c_mask:.2f})"
        )
    return ConventionCheck(d, c_read, c_mask, c_icx, bool(reasons), reasons)


def wave_halts(checks: Iterable[ConventionCheck], max_fraction: float = WAVE_HALT_FRACTION) -> bool:
    """A3: halt the wave for re-instruction if more than ``max_fraction`` of reads are thin."""
    checks = list(checks)
    return bool(checks) and sum(c.thin for c in checks) / len(checks) > max_fraction


# ----------------------------------------------------------------------------- A11
def name_conflict(read_a: np.ndarray, read_b: np.ndarray) -> np.ndarray:
    """Voxels both reads call vessel but name differently (reported by A12; not ignored)."""
    a, b = np.asarray(read_a), np.asarray(read_b)
    if a.shape != b.shape:
        raise ValueError(f"reads differ in shape: {a.shape} vs {b.shape}")
    return (a > 0) & (b > 0) & (a != b)


def a11_targets(
    read_a: np.ndarray,
    read_b: np.ndarray,
    ignore_label: int = IGNORE,
    conflict_ignore: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    """A11' (Round 5): one training target per read, each keeping its own labels.

    The default returns the two reads unchanged (as uint8): no name-conflict ``ignore``.
    ``conflict_ignore=True`` reproduces the retired A11 rule (name conflicts -> ``ignore``
    in both), kept only as the comparison arm of the conditional A11 test.
    """
    a = np.asarray(read_a).astype(np.uint8)
    b = np.asarray(read_b).astype(np.uint8)
    conflict = name_conflict(a, b)
    if not conflict_ignore:
        return a.copy(), b.copy()
    return (
        np.where(conflict, ignore_label, a).astype(np.uint8),
        np.where(conflict, ignore_label, b).astype(np.uint8),
    )


def lm_landmarks(read: np.ndarray) -> tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """(ostium, LM end) of a read, in voxel coordinates.

    LM end = centroid of LM voxels touching LAD/LCx; ostium = the LM voxel farthest
    (Euclidean, voxel units) from LAD/LCx. Either is None when the read has no LM or no
    LM/LAD-LCx contact (e.g. separate ostia).
    """
    r = np.asarray(read)
    lm = r == LM
    if not lm.any():
        return None, None
    lr = np.isin(r, (LAD, LCX))
    end = None
    if lr.any():
        j = lm & ndimage.binary_dilation(lr, _S26)
        if j.any():
            end = np.argwhere(j).mean(0)
        dist = ndimage.distance_transform_edt(~lr)
        pts = np.argwhere(lm)
        ost = pts[np.argmax(dist[lm])].astype(float)
    else:
        ost = np.argwhere(lm).mean(0)
    return ost, end


@dataclass
class ThirdRead:
    needed: bool
    inter_read_tf1: Optional[float]
    ostium_mm: Optional[float]
    lm_end_mm: Optional[float]
    lad_lcx_swap: float
    ramus_only: bool
    reasons: list = field(default_factory=list)


def third_read_triggers(
    read_a: np.ndarray,
    read_b: np.ndarray,
    spacing: Sequence[float],
    scorer: Optional[Scorer] = None,
    ramus_mask: Optional[np.ndarray] = None,
) -> ThirdRead:
    """A11 case level: does this pair need a third read?

    Triggers: inter-read macro tF1 < 0.80 (if a scorer is given); ostium or LM end more
    than 5 mm apart; LAD<->LCx swap > 5 % of the voxels both reads call LAD or LCx; an LM in
    one read only (Round 6 A21: a decision disagreement). Two reads that agree there is no LM
    (separate ostia) trigger nothing on LM or ostium (A4 absent-LM guard). A disagreement
    confined to ``ramus_mask`` (the ramus, resolved by D1b) never triggers.
    Bridge's decision extractor (``segtrain.namer``) adds its own triggers upstream.
    """
    a = np.asarray(read_a)
    b = np.asarray(read_b)
    sp = np.asarray(spacing, float)
    reasons = []
    both = np.isin(a, (LAD, LCX)) & np.isin(b, (LAD, LCX))
    swapped = both & (a != b)
    swap = float(swapped.sum() / both.sum()) if both.any() else 0.0
    ramus_only = bool(
        ramus_mask is not None
        and swapped.any()
        and not (swapped & ~np.asarray(ramus_mask, bool)).any()
    )
    if swap > THIRD_READ_SWAP and not ramus_only:
        reasons.append(f"LAD/LCx swap {swap:.1%} > {THIRD_READ_SWAP:.0%}")
    (oa, ea), (ob, eb) = lm_landmarks(a), lm_landmarks(b)
    ost = float(np.linalg.norm((oa - ob) * sp)) if oa is not None and ob is not None else None
    end = float(np.linalg.norm((ea - eb) * sp)) if ea is not None and eb is not None else None
    if (oa is None) != (ob is None):
        reasons.append("LM present in one read only")
    if ost is not None and ost > THIRD_READ_DISTANCE_MM:
        reasons.append(f"ostium {ost:.1f} mm apart")
    if end is not None and end > THIRD_READ_DISTANCE_MM:
        reasons.append(f"LM end {end:.1f} mm apart")
    tf = None
    if scorer is not None:
        ir = inter_read_tf1(a, b, spacing, scorer)
        tf = ir["macro"]
        # A1a: a provisional tF1 (no aorta) decides nothing, so it cannot trigger a third read
        if tf < THIRD_READ_TF1 and not ir["provisional"] and not ir["flagged"]:
            reasons.append(f"inter-read tF1 {tf:.3f} < {THIRD_READ_TF1}")
    return ThirdRead(bool(reasons), tf, ost, end, swap, ramus_only, reasons)


# ----------------------------------------------------------------------------- A10
def _macro(per: Mapping[int, float]) -> float:
    vals = [v for v in per.values() if np.isfinite(v)]
    return float(np.mean(vals)) if vals else float("nan")


def score_vs_reads(
    prediction: np.ndarray,
    reads: Sequence[np.ndarray],
    spacing: Sequence[float],
    scorer: Optional[Scorer] = None,
) -> dict:
    """A10: per-class tF1 of ``prediction`` against each read, averaged over the reads.

    A class enters the mean over reads for every read in which it is present.
    Returns ``{"per_class", "macro", "per_read", "provisional", "flagged"}``: the result is
    ``provisional`` if any read was scored without the A1 ostium of record (A1a), and
    ``flagged`` if any read's tree carries a flagged ostium (A1b).
    """
    scorer = scorer or default_scorer()
    unpacked = [_unpack(scorer(np.asarray(r), np.asarray(prediction), spacing)) for r in reads]
    per_read = [u[0] for u in unpacked]
    per = {}
    for c in CLASSES:
        v = [p[c] for p in per_read if c in p and np.isfinite(p[c])]
        if v:
            per[c] = float(np.mean(v))
    return {
        "per_class": per,
        "macro": _macro(per),
        "per_read": per_read,
        "provisional": any(u[1] for u in unpacked),
        "flagged": any(u[2] for u in unpacked),
    }


def inter_read_tf1(
    read_a: np.ndarray,
    read_b: np.ndarray,
    spacing: Sequence[float],
    scorer: Optional[Scorer] = None,
) -> dict:
    """Inter-read tF1: mean of A scored against B and B scored against A, per class.

    Carries ``provisional`` / ``flagged`` (A1a / A1b) like :func:`score_vs_reads`.
    """
    scorer = scorer or default_scorer()
    ab, pab, fab = _unpack(scorer(np.asarray(read_b), np.asarray(read_a), spacing))
    ba, pba, fba = _unpack(scorer(np.asarray(read_a), np.asarray(read_b), spacing))
    per = {}
    for c in CLASSES:
        v = [d[c] for d in (ab, ba) if c in d and np.isfinite(d[c])]
        if v:
            per[c] = float(np.mean(v))
    return {
        "per_class": per,
        "macro": _macro(per),
        "provisional": pab or pba,
        "flagged": fab or fba,
    }


def acceptance(
    model: Sequence[Mapping[int, float]],
    inter: Sequence[Mapping[int, float]],
    margin: float = NONINFERIORITY_MARGIN,
    n_boot: int = 5000,
    seed: int = 0,
    classes: Sequence[int] = CLASSES,
    provisional: Optional[Sequence[bool]] = None,
    flagged: Optional[Sequence[bool]] = None,
) -> dict:
    """A10 per-class non-inferiority on the same cases.

    ``flagged[i]`` (A1b) drops case i from the test until a human has reviewed its ostium;
    ``provisional[i]`` (A1a) keeps it but marks the whole result ``decisive=False``: a tF1
    without the aorta-contact ostium decides nothing.

    ``model[i]`` and ``inter[i]`` are per-class tF1 dicts for case i (model vs reads, and
    inter-read). Per class, over the cases where both have the class: the paired
    bootstrap 95 % CI of mean(model - inter); the class passes when its lower bound is
    > -margin. Returns per class n, mean difference, CI and pass, plus ``accepted`` (all
    tested classes pass). The Round 3 ruling allows the LM result to be reported rather
    than gated if its CI is too wide at n = 100; that call is the caller's, not this
    function's.
    """
    if len(model) != len(inter):
        raise ValueError("model and inter must list the same cases")
    n = len(model)
    flagged = list(flagged) if flagged is not None else [False] * n
    provisional = list(provisional) if provisional is not None else [True] * n
    keep = [i for i in range(n) if not flagged[i]]
    model = [model[i] for i in keep]
    inter = [inter[i] for i in keep]
    rng = np.random.default_rng(seed)
    out = {}
    for c in classes:
        d = np.array(
            [
                m[c] - i[c]
                for m, i in zip(model, inter)
                if c in m and c in i and np.isfinite(m[c]) and np.isfinite(i[c])
            ]
        )
        if not len(d):
            continue
        boots = d[rng.integers(0, len(d), (n_boot, len(d)))].mean(1)
        lo, hi = np.percentile(boots, [2.5, 97.5])
        out[c] = {
            "n": int(len(d)),
            "mean_diff": float(d.mean()),
            "ci95": [float(lo), float(hi)],
            "pass": bool(lo > -margin),
        }
    decisive = not any(provisional[i] for i in keep)
    return {
        "per_class": out,
        "margin": margin,
        "accepted": bool(out) and all(v["pass"] for v in out.values()),
        "decisive": decisive,
        "n_flagged_excluded": int(n - len(keep)),
    }


# ----------------------------------------------------------------------------- A12b anchor
def _skeleton_graph(mask: np.ndarray, spacing: np.ndarray):
    from skimage.morphology import skeletonize

    sk = skeletonize(mask)
    pts = np.argwhere(sk)
    n = len(pts)
    idx = -np.ones(sk.shape, np.int64)
    idx[tuple(pts.T)] = np.arange(n)
    rows, cols, w = [], [], []
    for o in np.argwhere(np.ones((3, 3, 3))) - 1:
        if not o.any():
            continue
        q = pts + o
        ok = np.all((q >= 0) & (q < sk.shape), 1)
        j = idx[tuple(q[ok].T)]
        good = j >= 0
        rows.append(np.nonzero(ok)[0][good])
        cols.append(j[good])
        w.append(np.full(int(good.sum()), float(np.linalg.norm(o * spacing))))
    if rows:
        rows, cols, w = np.concatenate(rows), np.concatenate(cols), np.concatenate(w)
    g = coo_matrix((w, (rows, cols)), shape=(n, n)).tocsr()
    return pts, g


@dataclass
class AnchorReading:
    offset_mm: Optional[float]
    review: bool
    reason: str = ""


def carina_offset(
    read: np.ndarray, icx4: np.ndarray, mask: np.ndarray, spacing: Sequence[float]
) -> AnchorReading:
    """A12b: geodesic offset (mm) of a read's LM end from ImageCAS-X's, along the mask's centreline.

    Both carinas (centroid of LM voxels touching LAD/LCx) are projected onto the
    skeleton of the left tree of the ImageCAS ``mask``; distances run from the ostium
    (ImageCAS-X's LM voxel farthest from LAD/LCx). Positive = the read's carina lies
    distal of ImageCAS-X's. ``review`` is set when the reading cannot be trusted: no LM
    in either labelling, a carina not reachable on the centreline, the read's carina more
    than 3 mm from the centreline, or |offset| > 5 mm (on 124 measured cases, offsets that
    large were skeleton failures). Reviewed readings are excluded from the bias and habit
    statistics and go to a human.
    """
    sp = np.asarray(spacing, float)
    r = np.asarray(read)
    i4 = np.asarray(icx4)
    m = np.asarray(mask) > 0
    o_i, e_i = lm_landmarks(i4)
    _, e_r = lm_landmarks(r)
    if o_i is None or e_i is None:
        return AnchorReading(None, True, "no LM / carina in ImageCAS-X (separate ostia?)")
    if e_r is None:
        return AnchorReading(None, True, "no LM / carina in the read")
    lab, _ = ndimage.label(m, _S26)
    lmv = lab[(i4 == LM) & m]
    if not len(lmv) or np.bincount(lmv).argmax() == 0:
        return AnchorReading(None, True, "ImageCAS-X LM outside the mask")
    left = lab == np.bincount(lmv[lmv > 0]).argmax()
    pts, g = _skeleton_graph(left, sp)
    if not len(pts):
        return AnchorReading(None, True, "empty skeleton")

    def near(p):
        return int(np.argmin((((pts - p) * sp) ** 2).sum(1)))

    d = dijkstra(g, indices=near(o_i))
    n_i, n_r = near(e_i), near(e_r)
    if not (np.isfinite(d[n_i]) and np.isfinite(d[n_r])):
        return AnchorReading(None, True, "carina not reachable on the centreline")
    off = float(d[n_r] - d[n_i])
    proj = float(np.linalg.norm((pts[n_r] - e_r) * sp))
    if abs(off) > ANCHOR_REVIEW_MM:
        return AnchorReading(
            off, True, f"offset {off:.1f} mm > {ANCHOR_REVIEW_MM} mm (measurement failure?)"
        )
    if proj > ANCHOR_REVIEW_EUCLID_MM:
        return AnchorReading(off, True, f"read's carina {proj:.1f} mm off the centreline")
    return AnchorReading(off, False)


def _boot_median_ci(x: np.ndarray, n_boot: int, rng) -> tuple[float, float]:
    b = np.median(x[rng.integers(0, len(x), (n_boot, len(x)))], 1)
    lo, hi = np.percentile(b, [2.5, 97.5])
    return float(lo), float(hi)


def team_bias(
    offsets: Iterable[Optional[float]],
    previous_flag: bool = False,
    convention_offset: float = ANCHOR_CONVENTION_OFFSET_MM,
    threshold: float = ANCHOR_BIAS_MM,
    n_boot: int = 4000,
    seed: int = 0,
) -> dict:
    """A12b: team-wide carina bias from per-read anchor offsets (reviewed readings excluded).

    bias = median(offset) - 0.7 mm (the measured convention offset), bootstrap 95 % CI.
    ``detected``: the CI excludes 0. ``flagged``: the CI lies entirely beyond +-1 mm.
    ``reinstruct``: flagged in this wave and the previous one (``previous_flag``), or flagged
    with n >= 80 -- the median test's false-alarm rate is about 0.09 at n = 50.
    """
    x = np.array([o for o in offsets if o is not None and np.isfinite(o)], float)
    if not len(x):
        return {
            "n": 0,
            "bias_mm": None,
            "ci95": None,
            "detected": False,
            "flagged": False,
            "reinstruct": False,
        }
    rng = np.random.default_rng(seed)
    lo, hi = _boot_median_ci(x, n_boot, rng)
    lo, hi = lo - convention_offset, hi - convention_offset
    flagged = bool(lo > threshold or hi < -threshold)
    return {
        "n": int(len(x)),
        "bias_mm": float(np.median(x) - convention_offset),
        "ci95": [lo, hi],
        "detected": bool(lo > 0 or hi < 0),
        "flagged": flagged,
        "reinstruct": bool(flagged and (previous_flag or len(x) >= 80)),
    }


def habit_test(
    per_annotator: Mapping[str, Iterable[Optional[float]]],
    threshold: float = HABIT_DIFFERENCE_MM,
    n_perm: int = 4000,
    seed: int = 0,
    min_reads: int = 5,
) -> dict:
    """A12a: do annotators differ systematically (carina offset, or any per-read measure)?

    For every pair of annotators with >= ``min_reads`` usable readings: the difference of
    medians and a two-sided permutation p-value. A pair has a habit difference when
    |difference| > ``threshold`` and p < 0.05. Medians, not means: about 3 % of anchor
    readings are measurement failures of 5-140 mm. Power at 25 + 25 reads: 0.96 for 1 mm.
    """
    rng = np.random.default_rng(seed)
    vals = {
        k: np.array([v for v in vs if v is not None and np.isfinite(v)], float)
        for k, vs in per_annotator.items()
    }
    vals = {k: v for k, v in vals.items() if len(v) >= min_reads}
    names = sorted(vals)
    pairs = []
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            x, y = vals[a], vals[b]
            obs = float(np.median(x) - np.median(y))
            pool = np.concatenate([x, y])
            cnt = 0
            for _ in range(n_perm):
                p = rng.permutation(pool)
                cnt += abs(np.median(p[: len(x)]) - np.median(p[len(x) :])) >= abs(obs) - 1e-12
            pval = (cnt + 1) / (n_perm + 1)
            pairs.append(
                {
                    "a": a,
                    "b": b,
                    "n_a": int(len(x)),
                    "n_b": int(len(y)),
                    "median_diff": obs,
                    "p": float(pval),
                    "habit": bool(abs(obs) > threshold and pval < 0.05),
                }
            )
    return {
        "annotators": {
            k: {"n": int(len(v)), "median": float(np.median(v))} for k, v in vals.items()
        },
        "pairs": pairs,
        "habits": any(p["habit"] for p in pairs),
    }


def truncation_radius(
    read: np.ndarray, mask: np.ndarray, spacing: Sequence[float]
) -> Optional[float]:
    """A12a: median lumen radius (mm) of the mask's centreline where the read stops.

    Stop points are centreline voxels the read covers that touch centreline voxels it does
    not. None when the read covers the whole centreline (no truncation).
    """
    from skimage.morphology import skeletonize

    m = np.asarray(mask) > 0
    r = np.asarray(read) > 0
    sk = skeletonize(m)
    if not sk.any():
        return None
    rad = ndimage.distance_transform_edt(m, sampling=np.asarray(spacing, float))
    covered = sk & r
    uncovered = sk & ~r
    stop = covered & ndimage.binary_dilation(uncovered, _S26)
    return float(np.median(rad[stop])) if stop.any() else None


# ----------------------------------------------------------------------------- A12 attribution
DECISION_BRANCH_MM3 = 20.0  # a disagreement blob this large is a whole branch named differently


def naming_attribution(
    read_a: np.ndarray,
    read_b: np.ndarray,
    affine,
    *,
    carina_band_mm: float = 10.0,
    use_namer: bool = True,
    ramus_candidates: Optional[np.ndarray] = None,
) -> dict:
    """A12 (Bridge): is the naming disagreement between two reads a few *decisions* or diffuse?

    Uses ``segtrain.namer.compare`` (read A as reference) for the name-conflict voxels and the
    wholesale flags, and, with ``use_namer``, ``segtrain.namer.name_tree`` on the union of the
    reads for the ramus candidates (D1b exemption). Each name-conflict voxel is attributed to
    a decision if it lies within ``carina_band_mm`` of either read's LM end (the LM-end /
    LAD-LCx split decision) or in a conflict blob of >= 20 mm^3 (a whole branch named
    differently: a side-branch or tree decision); the rest is diffuse boundary jitter. The
    pre-registered expectation (Bridge) is a decision share >= 0.8.
    """
    from . import namer

    a = np.asarray(read_a)
    b = np.asarray(read_b)
    A = namer.as_affine(affine)
    sp = np.sqrt((np.asarray(A, float)[:3, :3] ** 2).sum(0))
    ramus = ramus_candidates
    if ramus is None and use_namer and ((a > 0) | (b > 0)).any():
        ramus = namer.name_tree((a > 0) | (b > 0), A).ramus_candidates
    rep = namer.compare(a, b, A, ramus_candidates=ramus)
    conflict = rep.ignore
    n = int(conflict.sum())
    out = {
        "n_conflict_voxels": n,
        "flags": list(rep.flags),
        "wholesale": bool(rep.wholesale),
        "ramus_only": bool(rep.ramus_only),
        "tree_swap": bool(rep.tree_swap),
        "decision_share": None,
        "carina_share": None,
        "branch_share": None,
    }
    if not n:
        return out
    near = np.zeros(conflict.shape, bool)
    for r in (a, b):
        _, end = lm_landmarks(r)
        if end is not None:
            pts = np.argwhere(conflict)
            d = np.sqrt((((pts - end) * sp) ** 2).sum(1))
            near[tuple(pts[d <= carina_band_mm].T)] = True
    lab, k = ndimage.label(conflict, _S26)
    vol = np.bincount(lab.ravel()) * float(np.prod(sp))
    big = np.isin(lab, np.nonzero(vol >= DECISION_BRANCH_MM3)[0]) & (lab > 0)
    out["carina_share"] = float((near & conflict).sum() / n)
    out["branch_share"] = float((big & ~near).sum() / n)
    out["decision_share"] = float(((near | big) & conflict).sum() / n)
    return out


# ----------------------------------------------------------------------------- A12 report
@dataclass
class CaseReads:
    case: str
    reads: dict  # annotator -> label array
    spacing: tuple
    mask: Optional[np.ndarray] = None
    icx4: Optional[np.ndarray] = None
    affine: Optional[np.ndarray] = None  # NIfTI affine of the reads (left/right for the namer)
    aorta: Optional[np.ndarray] = None  # TotalSegmentator aorta on the same grid (A1 ostium)


EXPORT_SEGMENTS = {
    "left_main": LM,
    "left_anterior_descending": LAD,
    "left_circumflex": LCX,
    "right_coronary_artery": RCA,
}
_NOT_READS = ("ct", "image", "img", "mask", "coronary_arteries", "seed", "heart")


def _to_grid(img, ref_affine, ref_shape, what: str) -> np.ndarray:
    """Data of ``img`` on the reference grid. Axis flips and permutations (same physical grid,
    different storage order: how SegQueue submissions are stored) are undone exactly; any
    other mismatch raises, because voxel-by-voxel comparison would then be meaningless."""
    import nibabel as nib

    data = np.asarray(img.dataobj)
    aff = np.asarray(img.affine, float)
    if not (data.shape == tuple(ref_shape) and np.allclose(aff, ref_affine, atol=1e-3)):
        o_src = nib.orientations.io_orientation(aff)
        o_ref = nib.orientations.io_orientation(ref_affine)
        t = nib.orientations.ornt_transform(o_src, o_ref)
        data = nib.orientations.apply_orientation(data, t)
        aff = aff @ nib.orientations.inv_ornt_aff(t, img.shape)
        if not (data.shape == tuple(ref_shape) and np.allclose(aff, ref_affine, atol=1e-3)):
            raise ValueError(
                f"{what}: grid does not match the reference (shape {data.shape} "
                f"vs {tuple(ref_shape)}); resample it before the report"
            )
    return data


def _read_from_segmentations(seg_dir: str):
    """SegQueue export: one binary NIfTI per vessel -> one 4-class read (and its image)."""
    import nibabel as nib

    lab, img0 = None, None
    for f in sorted(os.listdir(seg_dir)):
        name = f.split(".nii")[0]
        if name not in EXPORT_SEGMENTS:
            continue
        img = nib.load(os.path.join(seg_dir, f))
        v = np.asarray(img.dataobj) > 0.5
        if lab is None:
            lab, img0 = np.zeros(v.shape, np.uint8), img
        lab[v & (lab == 0)] = EXPORT_SEGMENTS[name]
    return lab, img0


def load_read_folder(
    root: str,
    mask_dir: Optional[str] = None,
    icx_dir: Optional[str] = None,
    aorta_dir: Optional[str] = None,
    *,
    sealed: Optional[set] = None,
    milestone: bool = False,
    refused: Optional[list] = None,
) -> list[CaseReads]:
    """Load a wave of double reads. Two layouts are accepted:

    - ``<root>/<case>/<annotator>.nii.gz``: one 4-class file per read (files named like a CT,
      mask or seed are never taken for a read);
    - the SegQueue export (``segqueue-export --replicas all``):
      ``<root>/<case>[__rK]/segmentations/<vessel>.nii.gz`` plus ``ct.nii.gz``; replica
      folders of one case are merged, reads are named ``r1``, ``r2`` ...; ``imagecas_NNNN``
      names become ``c{NNNN-1}``.

    Every read (and the ImageCAS-X labels) is brought onto the grid of the case's mask, or
    of its first read when no mask is given; axis flips/permutations are undone, any other
    mismatch raises. ``mask_dir`` holds ``<case>.nii.gz`` or ``<case>/coronary_arteries.nii.gz``;
    ``icx_dir`` holds ``<n>.coronary.nii.gz``, n = case number + 1. ``aorta_dir`` holds the
    TotalSegmentator aorta per case as ``<case>_aorta.nii.gz`` (``segtrain.aorta``),
    ``<case>.nii.gz``, ``<case>/aorta.nii.gz`` or ``<case>/segmentations/aorta.nii.gz``.
    **A14:** every folder whose name maps to a sealed case (any form: ``cNNNN``,
    ``imagecas_NNNN``, ``__r2`` ...), or to no case at all, is skipped before anything of it
    is opened and listed in ``refused``; ``milestone=True`` (sealed-test scoring only) lifts
    the filter;
    it is brought onto the same grid and makes the
    report's tF1 use the A1 ostium of record (non-provisional). Sealed cases must not be
    passed here before a milestone (A14).
    """
    import warnings

    import nibabel as nib

    # A14: sealed reads are never inspected before a milestone. The filter runs on folder names,
    # before any file of a refused case (or its mask) is opened; names that map to no case are
    # refused too (proxy.sealed_reason). ``sealed`` defaults to trillium/sealed_test.json.
    if not milestone:
        sealed = load_sealed() if sealed is None else set(sealed)
    groups: dict = {}
    for entry in sorted(os.listdir(root)):
        cdir = os.path.join(root, entry)
        if not os.path.isdir(cdir):
            continue
        if not milestone:
            why = sealed_reason(entry, sealed)
            if why:
                if refused is not None:
                    refused.append(why)
                warnings.warn(f"reads: skipped {why}", stacklevel=2)
                continue
        seg = os.path.join(cdir, "segmentations")
        if os.path.isdir(seg):
            lab, img = _read_from_segmentations(seg)
            if lab is not None:
                groups.setdefault(case_id(entry), []).append((read_name(entry), lab, img))
            continue
        for f in sorted(os.listdir(cdir)):
            if not f.endswith((".nii.gz", ".nii")):
                continue
            name = f.split(".nii")[0]
            if name.lower() in _NOT_READS:
                continue
            img = nib.load(os.path.join(cdir, f))
            groups.setdefault(case_id(entry), []).append((name, None, img))
    out = []
    for case in sorted(groups):
        items = sorted(groups[case], key=lambda t: t[0])
        mask_img = None
        if mask_dir:
            for cand in (
                os.path.join(mask_dir, f"{case}.nii.gz"),
                os.path.join(mask_dir, case, "coronary_arteries.nii.gz"),
            ):
                if os.path.exists(cand):
                    mask_img = nib.load(cand)
                    break
        ref = mask_img if mask_img is not None else items[0][2]
        ref_aff, ref_shape = np.asarray(ref.affine, float), ref.shape[:3]
        reads = {}
        for name, lab, img in items:
            if lab is not None:
                img = nib.Nifti1Image(lab, img.affine)
            reads[name] = _to_grid(img, ref_aff, ref_shape, f"{case}/{name}").astype(np.uint8)
        mask = None
        if mask_img is not None:
            mask = np.asarray(mask_img.dataobj) > 0.5
        icx = None
        if icx_dir and case[1:].isdigit():
            pth = os.path.join(icx_dir, f"{int(case[1:]) + 1}.coronary.nii.gz")
            if os.path.exists(pth):
                icx = icx_to_territory(_to_grid(nib.load(pth), ref_aff, ref_shape, f"{case}/icx"))
        spacing = tuple(float(z) for z in ref.header.get_zooms()[:3])
        aorta = None
        if aorta_dir:
            for cand in (
                os.path.join(aorta_dir, f"{case}_aorta.nii.gz"),  # segtrain.aorta's output name
                os.path.join(aorta_dir, f"{case}.nii.gz"),
                os.path.join(aorta_dir, case, "aorta.nii.gz"),
                os.path.join(aorta_dir, case, "segmentations", "aorta.nii.gz"),
            ):
                if os.path.exists(cand):
                    aorta = _to_grid(nib.load(cand), ref_aff, ref_shape, f"{case}/aorta") > 0.5
                    break
        out.append(CaseReads(case, reads, spacing, mask, icx, ref_aff, aorta))
    return out


CROP_MARGIN_MM = 12.0  # > the 10 mm carina band and the 5 mm aorta-contact rule (A1)


def crop_case(cr: CaseReads, margin_mm: float = CROP_MARGIN_MM) -> CaseReads:
    """The case restricted to the bounding box of its reads and mask (+ ``margin_mm``).

    Every distance transform in the report then runs on the tree box instead of the full CT
    grid (Echo E4: one 512x512x275 case took 791 s and ~4.5 GB uncropped). The ImageCAS-X
    labels and the aorta are cut to the same box; the affine is shifted so that world
    coordinates (left/right for the namer) are unchanged.
    """
    arrays = [r for r in cr.reads.values()] + ([cr.mask] if cr.mask is not None else [])
    occ = np.zeros(np.asarray(arrays[0]).shape, bool)
    for a in arrays:
        occ |= np.asarray(a) > 0
    if not occ.any():
        return cr
    sp = np.asarray(cr.spacing, float)
    mv = np.ceil(margin_mm / sp).astype(int)
    idx = [np.nonzero(occ.any(axis=tuple(j for j in range(3) if j != k)))[0] for k in range(3)]
    lo = np.maximum([i[0] for i in idx] - mv, 0)
    hi = np.minimum([i[-1] + 1 for i in idx] + mv, occ.shape)
    sl = tuple(slice(int(a), int(b)) for a, b in zip(lo, hi))

    def cut(x):
        return None if x is None else np.asarray(x)[sl]

    aff = None
    if cr.affine is not None:
        aff = np.asarray(cr.affine, float).copy()
        aff[:3, 3] = aff[:3, :3] @ lo + aff[:3, 3]
    return CaseReads(
        cr.case,
        {k: cut(v) for k, v in cr.reads.items()},
        cr.spacing,
        cut(cr.mask),
        cut(cr.icx4),
        aff,
        cut(cr.aorta),
    )


def first_reads_report(
    cases: Sequence[CaseReads],
    scorer: Optional[Scorer] = None,
    previous_bias_flag: bool = False,
    carina_band_mm: float = 10.0,
    use_namer: bool = True,
    per_case_tf1: bool = False,
) -> dict:
    """A12: the single wave-1 report on the first double-read cases.

    Per case (first two reads; a third read, if present, is only counted): A3 convention
    check per read (both A3 triggers when ImageCAS-X is loaded); inter-read tF1 per class;
    the name-conflict fraction (reported only: A11' trains on each read as it is) and the
    share of it within ``carina_band_mm`` of the carina; components of A&B vs each read;
    third-read triggers (ours plus the namer's wholesale flags); naming-disagreement
    attribution (decision vs diffuse, ``naming_attribution``); LM-end distance between reads
    and truncation radius per read
    (the noise-model refit inputs); A12b anchor offset per read. Wave level: A3 halt,
    adjudication rate, noise-model refit summary, A12a habits (anchor offset and
    truncation radius per annotator), A12b team bias. Returns a JSON-able dict; render it
    with :func:`report_markdown`. ``per_case_tf1=True`` scores tF1 per case with that case's
    aorta (``CaseReads.aorta``, from ``load_read_folder(aorta_dir=...)``), so cases with an
    aorta are non-provisional (A1a); otherwise ``scorer`` (or none) is used for every case.
    """
    rows, checks = [], []
    per_annot_offset: dict = {}
    per_annot_trunc: dict = {}
    offsets = []
    for cr in cases:
        cr = crop_case(cr)  # E4: all distance transforms on the tree box, never the full grid
        names = list(cr.reads)
        row = {"case": cr.case, "annotators": names, "n_reads": len(names)}
        if cr.mask is not None:
            row["convention"] = {}
            for n in names:
                cc = convention_check(
                    cr.reads[n],
                    cr.mask,
                    cr.spacing,
                    icx_lumen=(cr.icx4 > 0) if cr.icx4 is not None else None,
                )
                row["convention"][n] = asdict(cc)
                checks.append(cc)
        if len(names) >= 2:
            a, b = cr.reads[names[0]], cr.reads[names[1]]
            ign = name_conflict(a, b)  # reported only: A11' trains on each read as it is
            vessel = (a > 0) | (b > 0)
            row["name_conflict_fraction"] = float(ign.sum() / max(1, vessel.sum()))
            _, end_a = lm_landmarks(a)
            if ign.any() and end_a is not None:
                sp = np.asarray(cr.spacing, float)
                pts = np.argwhere(ign)
                dist = np.sqrt((((pts - end_a) * sp) ** 2).sum(1))
                row["name_conflict_within_carina_band"] = float(np.mean(dist <= carina_band_mm))
            inter_c = ndimage.label((a > 0) & (b > 0), _S26)[1]
            row["components"] = {
                "A_and_B": int(inter_c),
                names[0]: int(ndimage.label(a > 0, _S26)[1]),
                names[1]: int(ndimage.label(b > 0, _S26)[1]),
            }
            aff = cr.affine if cr.affine is not None else cr.spacing
            ramus = None
            if use_namer:
                from . import namer

                if vessel.any():
                    ramus = namer.name_tree(vessel, namer.as_affine(aff)).ramus_candidates
            sc = scorer
            if per_case_tf1:  # tF1 with this case's aorta (A1 ostium); provisional without one
                sc = default_scorer(aorta=cr.aorta) if cr.aorta is not None else default_scorer()
            tr = third_read_triggers(a, b, cr.spacing, sc, ramus_mask=ramus)
            if use_namer:
                att = naming_attribution(
                    a, b, aff, carina_band_mm=carina_band_mm, ramus_candidates=ramus
                )
                row["naming_attribution"] = att
                if att["wholesale"] and not tr.needed:  # Bridge's decision triggers (A11)
                    tr.needed = True
                    tr.reasons.append("namer: " + ",".join(att["flags"]))
            row["third_read"] = asdict(tr)
            if sc is not None:
                row["inter_read_tf1"] = inter_read_tf1(a, b, cr.spacing, sc)
            row["lm_end_distance_mm"] = tr.lm_end_mm
        for n in names:
            if cr.mask is not None:
                t = truncation_radius(cr.reads[n], cr.mask, cr.spacing)
                row.setdefault("truncation_radius_mm", {})[n] = t
                per_annot_trunc.setdefault(n, []).append(t)
            if cr.mask is not None and cr.icx4 is not None:
                ar = carina_offset(cr.reads[n], cr.icx4, cr.mask, cr.spacing)
                row.setdefault("anchor", {})[n] = asdict(ar)
                if not ar.review:
                    per_annot_offset.setdefault(n, []).append(ar.offset_mm)
                    offsets.append(ar.offset_mm)
        rows.append(row)

    def _stats(v):
        v = np.array([x for x in v if x is not None and np.isfinite(x)], float)
        return (
            None
            if not len(v)
            else {
                "n": int(len(v)),
                "median": float(np.median(v)),
                "p10": float(np.percentile(v, 10)),
                "p90": float(np.percentile(v, 90)),
            }
        )

    pairs = [r for r in rows if "third_read" in r]
    inter = {}
    for c in CLASSES:
        v = [
            r["inter_read_tf1"]["per_class"][c]
            for r in pairs
            if "inter_read_tf1" in r and c in r["inter_read_tf1"]["per_class"]
        ]
        if v:
            inter[CLASS_NAMES[c]] = _stats(v)
    lm_d = [r["lm_end_distance_mm"] for r in pairs]
    wave = {
        "n_cases": len(rows),
        "a3_thin_reads": int(sum(c.thin for c in checks)),
        "a3_reads_checked": len(checks),
        "a3_halt": wave_halts(checks),
        "adjudication_rate": (
            float(np.mean([r["third_read"]["needed"] for r in pairs])) if pairs else None
        ),
        "inter_read_tf1": inter,
        # A1a / A1b: any provisional (no aorta) or flagged tF1 makes the tF1 numbers non-decisive
        "tf1_provisional": any(
            r["inter_read_tf1"].get("provisional", True) for r in pairs if "inter_read_tf1" in r
        ),
        "tf1_flagged_cases": [
            r["case"] for r in pairs if r.get("inter_read_tf1", {}).get("flagged", False)
        ],
        "name_conflict_fraction": _stats([r.get("name_conflict_fraction") for r in pairs]),
        "name_conflict_within_carina_band": _stats(
            [r.get("name_conflict_within_carina_band") for r in pairs]
        ),
        "refit": {
            # LM-end distance ~ |s_a - s_b|; independent shifts: SD(s) ~ RMS(diff)/sqrt(2)
            "lm_end_distance_mm": _stats(lm_d),
            "carina_sd_mm_est": _rms_over_sqrt2(lm_d),
            "truncation_radius_mm": _stats([t for v in per_annot_trunc.values() for t in v]),
            "lad_lcx_swap": _stats([r["third_read"]["lad_lcx_swap"] for r in pairs]),
        },
        "naming_decision_share": _stats(
            [r["naming_attribution"]["decision_share"] for r in pairs if "naming_attribution" in r]
        ),
        "a12a_habits_carina": habit_test(per_annot_offset) if per_annot_offset else None,
        "a12a_habits_truncation": habit_test(per_annot_trunc, threshold=0.1)
        if per_annot_trunc
        else None,
        "a12b_team_bias": team_bias(offsets, previous_flag=previous_bias_flag) if offsets else None,
        "anchor_reviewed": int(
            sum(1 for r in rows for v in r.get("anchor", {}).values() if v["review"])
        ),
    }
    return {"wave": wave, "cases": rows}


def _rms_over_sqrt2(values) -> Optional[float]:
    v = np.array([x for x in values if x is not None and np.isfinite(x)], float)
    return float(np.sqrt(np.mean(v**2) / 2)) if len(v) else None


def report_markdown(report: Mapping) -> str:
    """Render :func:`first_reads_report` as the Markdown page the labelling lead reads."""
    w = report["wave"]
    lines = [
        "# Wave-1 double-read report (A12)",
        "",
        f"Cases: {w['n_cases']}. Reads checked by the convention monitor: {w['a3_reads_checked']}, "
        f"flagged thin: {w['a3_thin_reads']} -> wave halt: **{w['a3_halt']}** (A3, > 10 %).",
        f"Adjudication (third-read) rate: {w['adjudication_rate']}.",
        "",
        "## Inter-read tF1 per class (A10's reference level)"
        + (
            " -- PROVISIONAL: no aorta ostium (A1a), decides nothing"
            if w.get("tf1_provisional")
            else ""
        ),
        "",
    ]
    for k, v in (w["inter_read_tf1"] or {}).items():
        lines.append(f"- {k}: median {v['median']:.3f} (p10 {v['p10']:.3f}, n={v['n']})")
    lines += [
        "",
        "## Name conflicts between reads (A11': reported, not ignored)",
        "",
        f"- name-conflict fraction of vessel voxels: {w['name_conflict_fraction']}",
        "- share of name conflicts within 10 mm of the carina: "
        f"{w['name_conflict_within_carina_band']}",
        "- naming disagreement attributable to decisions (Bridge; expect >= 0.8): "
        f"{w.get('naming_decision_share')}",
        "",
        "## Noise-model refit inputs",
        "",
        f"```\n{json.dumps(w['refit'], indent=1)}\n```",
        "",
        "## A12a annotator habits",
        "",
    ]
    for key in ("a12a_habits_carina", "a12a_habits_truncation"):
        h = w[key]
        if h:
            lines.append(f"- {key}: habits = **{h['habits']}**")
            for p in h["pairs"]:
                lines.append(
                    f"  - {p['a']} vs {p['b']}: median diff {p['median_diff']:+.2f}, "
                    f"p = {p['p']:.3f}"
                    f"{' (habit)' if p['habit'] else ''}"
                )
    tb = w["a12b_team_bias"]
    lines += ["", "## A12b carina anchor (diagnostic only)", ""]
    if tb:
        lines.append(
            f"- team bias (median - 0.7 mm): {tb['bias_mm']:+.2f} mm, CI {tb['ci95']}, "
            f"n = {tb['n']}; detected {tb['detected']}, flagged {tb['flagged']}, "
            f"re-instruct **{tb['reinstruct']}**"
        )
    lines.append(f"- anchor readings sent to review: {w['anchor_reviewed']}")
    return "\n".join(lines) + "\n"
