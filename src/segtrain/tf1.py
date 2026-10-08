"""Tree-F1: the master plan's deciding metric (amendment A9), with its ostium (A1) and gates (A2).

This is the one implementation. The Trillium experiments and the vault notes each carried a copy
(``experiments/Delta/perturb_metrics.py``, ``trillium/delta/deltalib.py``,
``trillium/atlas/lib/tf1.py``, ``trillium/bridge/py/tf1.py``); ``tests/test_tf1.py`` pins this
module to their numbers on small fixtures. The reasoning is in the vault:
*Delta - Dice cannot see the errors that break a coronary tree* (why), *Delta - Two cheap ostium
rules find 116 of 116 true ostia* (the ostium), *Delta - Real bridging on 17 nnU-Net predictions…*
(the gate and the audit).

What tree-F1 measures
---------------------
Per class ``c`` present in the reference (1 LM, 2 LAD, 3 LCx, 4 RCA):

* **recall_c** -- the fraction of the reference's class-``c`` centreline that is predicted as class
  ``c`` *and* lies in a predicted piece connected to an ostium of the reference. Pieces closer than
  ``tol_mm`` count as connected (Human decision D3: 1.5 mm), and an ostium is reached when a
  predicted voxel of the piece lies within ``max(tol_mm, largest voxel side)`` of it.
* **precision_c** -- the fraction of the predicted class-``c`` centreline that lies inside reference
  class-``c`` voxels.
* ``tF1_c`` is their harmonic mean; ``tF1`` is the mean over the classes present in the reference.

A prediction that cuts a vessel off from the aorta loses that vessel's recall however good its
overlap is -- which is the point: Dice and per-class clDice both score a tree cut at the LM almost
as highly as an intact one.

What it does not see: an isolated false-positive blob has almost no centreline, so it barely moves
precision. That is what :func:`fp_components` (the A2 gate) is for. Report both, always.

The ostium (A1)
---------------
Per reference tree component (so a heart with separate LAD and LCx ostia gets two left ostia):

* ``aorta`` -- the reference centreline endpoints within 5 mm of a supplied aorta mask
  (TotalSegmentator); the thickest of them is the ostium. This is the rule of record.
* ``thick`` -- the thickest centreline endpoint (median radius over ~20 neighbouring centreline
  voxels), LM-labelled endpoints preferred.
* ``pool_thick`` -- among the endpoints within 3 mm of the endpoint nearest the contrast blood pool
  (needs the CT), the thickest.

When the rules available for a tree disagree by more than 5 mm the tree is **flagged** for a human:
it is still scored with the rule of record, and the flag travels with the result so that it is
never averaged in silently. Without an aorta mask the result is marked ``provisional`` and scored
with ``thick``; with neither aorta nor CT there is no cross-check and every tree is provisional.

Arrays are indexed in the same axis order as ``spacing`` (nibabel's x, y, z in this repository).
Labels are integer class maps (0 background); a binary prediction is accepted for everything but
tree-F1's naming condition.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy import ndimage

#: Gap tolerance of the deciding metric, fixed by the clinical lead (Human decisions D3).
TOLERANCE_MM = 1.5
#: An endpoint is an aorta-contact ostium when it lies this close to the aorta mask (A1).
AORTA_CONTACT_MM = 5.0
#: Two ostium rules further apart than this flag the tree for a human (A1).
DISAGREEMENT_MM = 5.0
#: Predicted components smaller than this are noise and dropped before anything is scored (A2).
MIN_COMPONENT_VOXELS = 100
#: Reference components smaller than this are not trees and get no ostium.
MIN_TREE_VOXELS = 1000
CLASSES = (1, 2, 3, 4)
CLASS_NAMES = {1: "left_main", 2: "left_anterior_descending", 3: "left_circumflex",
               4: "right_coronary_artery"}

_S26 = np.ones((3, 3, 3), dtype=bool)
_OFFSETS = [(a, b, c) for a in (-1, 0, 1) for b in (-1, 0, 1) for c in (-1, 0, 1)
            if (a, b, c) > (0, 0, 0)]  # half of the 26-neighbourhood: each pair once


# --------------------------------------------------------------------------------- results
@dataclass
class Ostium:
    """One ostium of one reference tree component."""
    tree: int                     # reference component id (26-connectivity)
    point: tuple                  # voxel index of the chosen ostium
    rule: str                     # rule of record used: "aorta" or "thick"
    candidates: dict = field(default_factory=dict)   # rule -> voxel index, every rule that ran
    disagreement_mm: float = 0.0  # largest pairwise distance between the rules' choices
    flagged: bool = False         # rules disagree by > DISAGREEMENT_MM: a human must look

    def as_row(self) -> dict:
        return {"tree": self.tree, "point": [int(v) for v in self.point], "rule": self.rule,
                "candidates": {k: [int(v) for v in p] for k, p in self.candidates.items()},
                "disagreement_mm": round(float(self.disagreement_mm), 2), "flagged": self.flagged}


@dataclass
class OstiumReport:
    ostia: list
    provisional: bool             # no aorta mask: scored on the cheap rules only
    rules: tuple                  # rules that ran

    @property
    def points(self) -> list:
        return [o.point for o in self.ostia]

    @property
    def flagged(self) -> list:
        return [o for o in self.ostia if o.flagged]


@dataclass
class TreeF1:
    """Result of :func:`tree_f1`. ``tf1`` is NaN when the reference is empty."""
    tf1: float
    per_class: dict               # class -> tF1_c (classes present in the reference only)
    recall: dict
    precision: dict
    rooted_fraction: float        # reference centreline reached from an ostium (any class)
    tol_mm: float
    ostia: OstiumReport
    n_reference_centreline: int = 0

    @property
    def provisional(self) -> bool:
        return self.ostia.provisional

    @property
    def flagged(self) -> bool:
        return bool(self.ostia.flagged)

    def as_row(self) -> dict:
        return {"tf1": self.tf1, "tol_mm": self.tol_mm, "rooted_fraction": self.rooted_fraction,
                **{f"tf1_{CLASS_NAMES[c]}": v for c, v in self.per_class.items()},
                "ostium_provisional": self.provisional, "ostium_flagged": self.flagged,
                "ostia": [o.as_row() for o in self.ostia.ostia]}


@dataclass
class BridgeAudit:
    """A2 bridge audit: what a gap-bridging step joined, and whether the joins were real."""
    rows: list                    # one dict per bridge
    fp_components_before: int     # the gate's number, on the raw prediction
    fp_components_after: int      # after bridging -- never the gate's number (bridges hide FPs)

    @property
    def n_bridges(self) -> int:
        return len(self.rows)

    @property
    def n_fp_joins(self) -> int:
        return sum(not r["touches_reference"] for r in self.rows)

    @property
    def n_cross_tree(self) -> int:
        return sum(r["cross_tree"] for r in self.rows)

    def as_row(self) -> dict:
        return {"n_bridges": self.n_bridges, "n_fp_joins": self.n_fp_joins,
                "n_cross_tree": self.n_cross_tree,
                "fp_components_before": self.fp_components_before,
                "fp_components_after": self.fp_components_after, "bridges": self.rows}


# --------------------------------------------------------------------------------- helpers
def _skeletonise(mask: np.ndarray) -> np.ndarray:
    try:
        from skimage.morphology import skeletonize
    except ImportError as e:  # pragma: no cover - environment problem, not a code path
        raise ImportError("segtrain.tf1 needs scikit-image (skeletonize)") from e
    if not mask.any():
        return np.zeros(mask.shape, dtype=bool)
    return skeletonize(mask.astype(bool)).astype(bool)


def _ball(r_mm: float, spacing: np.ndarray) -> np.ndarray:
    rr = np.ceil(r_mm / spacing).astype(int)
    g = np.ogrid[tuple(slice(-k, k + 1) for k in rr)]
    return sum((g[i] * spacing[i]) ** 2 for i in range(3)) <= r_mm ** 2 + 1e-9


def components(binary: np.ndarray) -> tuple[np.ndarray, int]:
    """26-connected components (the connectivity every tree-F1 copy uses)."""
    lab, n = ndimage.label(binary, structure=_S26)
    return lab, int(n)


def remove_small_components(binary: np.ndarray,
                            min_voxels: int = MIN_COMPONENT_VOXELS) -> np.ndarray:
    """Drop 26-connected components smaller than ``min_voxels`` (A2's raw-prediction hygiene).

    Never keep-largest: a coronary prediction is two or more trees, and the largest-component rule
    deletes whole vessels."""
    lab, n = components(binary)
    if n == 0:
        return binary.astype(bool)
    keep = np.bincount(lab.ravel()) >= min_voxels
    keep[0] = False
    return keep[lab]


def raw_prediction(prediction: np.ndarray, threshold: float = 0.5,
                   min_voxels: int = MIN_COMPONENT_VOXELS) -> np.ndarray:
    """The 'raw' prediction A2's gate is read on: labels (or a probability map thresholded at
    ``threshold``) with components < ``min_voxels`` removed, before any bridging or repair.
    Returns the label map with the small components zeroed."""
    pred = np.asarray(prediction)
    if np.issubdtype(pred.dtype, np.floating):
        pred = (pred >= threshold).astype(np.uint8)
    keep = remove_small_components(pred > 0, min_voxels)
    return np.where(keep, pred, 0).astype(pred.dtype)


class _Centreline:
    """Skeleton voxels of a mask as a graph (26-neighbourhood), with radius per voxel."""

    def __init__(self, mask: np.ndarray, spacing: np.ndarray):
        skel = _skeletonise(mask)
        self.pts = np.argwhere(skel)
        n = len(self.pts)
        index = -np.ones(mask.shape, dtype=np.int64)
        index[tuple(self.pts.T)] = np.arange(n)
        pad = np.pad(index, 1, constant_values=-1)
        a_list, b_list = [], []
        for o in _OFFSETS:
            nb = pad[tuple(self.pts[:, k] + 1 + o[k] for k in range(3))]
            ok = nb >= 0
            a_list.append(np.nonzero(ok)[0])
            b_list.append(nb[ok])
        a = np.concatenate(a_list) if a_list else np.zeros(0, int)
        b = np.concatenate(b_list) if b_list else np.zeros(0, int)
        src = np.concatenate([a, b])
        dst = np.concatenate([b, a])
        order = np.argsort(src, kind="stable")
        self._dst = dst[order]
        self._start = np.searchsorted(src[order], np.arange(n + 1))
        self.degree = np.diff(self._start)
        self.radius = ndimage.distance_transform_edt(mask, sampling=spacing)[tuple(self.pts.T)] \
            if n else np.zeros(0)
        self.skel = skel

    def neighbours(self, v: int) -> np.ndarray:
        return self._dst[self._start[v]:self._start[v + 1]]

    def median_radius_near(self, v: int, hops: int = 20) -> float:
        seen = {v}
        q = deque([(v, 0)])
        while q:
            u, d = q.popleft()
            if d == hops:
                continue
            for w in self.neighbours(u):
                w = int(w)
                if w not in seen:
                    seen.add(w)
                    q.append((w, d + 1))
        return float(np.median(self.radius[list(seen)]))


def blood_pool(ct: np.ndarray, spacing: Sequence[float],
               exclude: Optional[np.ndarray] = None, thr_hu: float = 200.0,
               open_mm: float = 3.0, min_cc_mm3: float = 2000.0) -> np.ndarray:
    """Large contrast-filled pools (aortic root, chambers) for the ``pool_thick`` ostium rule.

    Smooth (sigma 0.7 mm), threshold > ``thr_hu``, remove ``exclude`` (the coronary mask) dilated by
    two voxels, open with a ``open_mm`` ball (removes vessel-calibre structures), keep components of
    at least ``min_cc_mm3``."""
    sp = np.asarray(spacing, float)
    g = ndimage.gaussian_filter(np.asarray(ct, np.float32), sigma=0.7 / sp)
    m = g > thr_hu
    if exclude is not None:
        m &= ~ndimage.binary_dilation(exclude, iterations=2)
    eroded = ndimage.distance_transform_edt(m, sampling=sp) > open_mm
    m = ndimage.distance_transform_edt(~eroded, sampling=sp) <= open_mm
    lab, n = components(m)
    if n == 0:
        return m
    vol = np.bincount(lab.ravel()) * float(np.prod(sp))
    vol[0] = 0
    return np.isin(lab, np.nonzero(vol >= min_cc_mm3)[0])


# --------------------------------------------------------------------------------- ostia (A1)
def find_ostia(reference: np.ndarray, spacing: Sequence[float], *,
               aorta: Optional[np.ndarray] = None, ct: Optional[np.ndarray] = None,
               aorta_contact_mm: float = AORTA_CONTACT_MM,
               disagreement_mm: float = DISAGREEMENT_MM, min_tree_voxels: int = MIN_TREE_VOXELS,
               _centreline: Optional[_Centreline] = None) -> OstiumReport:
    """Ostia of every reference tree component, by the A1 procedure (module docstring).

    ``aorta`` (bool mask) and ``ct`` (HU) are optional and on the reference's grid. Returns
    an :class:`OstiumReport`; trees whose rules disagree by more than ``disagreement_mm`` are
    flagged."""
    sp = np.asarray(spacing, float)
    ref = np.asarray(reference)
    m = ref > 0
    rules = ((("aorta",) if aorta is not None else ()) + ("thick",)
             + (("pool_thick",) if ct is not None else ()))
    if not m.any():
        return OstiumReport([], provisional=aorta is None, rules=rules)
    cl = _centreline or _Centreline(m, sp)
    comp, n = components(m)
    sizes = np.bincount(comp.ravel())
    csk = comp[tuple(cl.pts.T)] if len(cl.pts) else np.zeros(0, int)
    lsk = ref[tuple(cl.pts.T)] if len(cl.pts) else np.zeros(0, int)
    d_ao = ndimage.distance_transform_edt(~aorta.astype(bool), sampling=sp) \
        if aorta is not None and np.asarray(aorta).any() else None
    d_pool = None
    if ct is not None:
        pool = blood_pool(ct, sp, exclude=m)
        if pool.any():
            d_pool = ndimage.distance_transform_edt(~pool, sampling=sp)
    ostia = []
    for k in range(1, n + 1):
        if sizes[k] < min_tree_voxels:
            continue
        ends = np.nonzero((csk == k) & (cl.degree == 1))[0]
        if len(ends) == 0:
            continue
        rmed = {int(v): cl.median_radius_near(int(v)) for v in ends}

        def thickest(cand, rmed=rmed):
            return max(cand, key=lambda u: rmed[int(u)])

        lm = ends[lsk[ends] == 1]
        cand = {"thick": int(thickest(lm if len(lm) else ends))}
        if d_pool is not None:
            dp = d_pool[tuple(cl.pts[ends].T)]
            cand["pool_thick"] = int(thickest(ends[dp <= dp.min() + 3.0]))
        rule = "thick"
        if d_ao is not None:
            de = d_ao[tuple(cl.pts[ends].T)]
            near = ends[de <= aorta_contact_mm]
            if len(near):
                cand["aorta"] = int(thickest(near))
                rule = "aorta"
        pts_mm = {r: cl.pts[v] * sp for r, v in cand.items()}
        names = list(pts_mm)
        dis = max((float(np.linalg.norm(pts_mm[a] - pts_mm[b])) for i, a in enumerate(names)
                   for b in names[i + 1:]), default=0.0)
        # aorta mask given but no endpoint touches it: that is itself a disagreement worth a look
        flagged = dis > disagreement_mm or (d_ao is not None and rule != "aorta")
        ostia.append(Ostium(tree=k, point=tuple(int(x) for x in cl.pts[cand[rule]]),
                            rule=rule,
                            candidates={r: tuple(int(x) for x in cl.pts[v])
                                        for r, v in cand.items()},
                            disagreement_mm=dis, flagged=bool(flagged)))
    return OstiumReport(ostia, provisional=aorta is None, rules=rules)


# --------------------------------------------------------------------------------- tree-F1
def tree_f1(reference: np.ndarray, prediction: np.ndarray, spacing: Sequence[float], *,
            tol_mm: float = TOLERANCE_MM, ostia: Optional[OstiumReport] = None,
            aorta: Optional[np.ndarray] = None, ct: Optional[np.ndarray] = None,
            min_component_voxels: int = MIN_COMPONENT_VOXELS) -> TreeF1:
    """Tree-F1 of a 4-class ``prediction`` against a 4-class ``reference`` (same grid).

    ``tol_mm`` is the gap tolerance (1.5 mm is the decided value; 0 gives the strict variant).
    Ostia come from ``ostia`` if given, else from :func:`find_ostia` with ``aorta`` / ``ct``.
    The prediction is cleaned of components < ``min_component_voxels`` first, as the raw
    prediction always is. A binary prediction is accepted but then every voxel is 'class 1'."""
    sp = np.asarray(spacing, float)
    ref = np.asarray(reference)
    pred = np.where(remove_small_components(np.asarray(prediction) > 0, min_component_voxels),
                    np.asarray(prediction), 0)
    if not (ref > 0).any():
        return TreeF1(float("nan"), {}, {}, {}, float("nan"), tol_mm,
                      OstiumReport([], provisional=aorta is None, rules=()))
    cl = _Centreline(ref > 0, sp)
    report = ostia if ostia is not None else find_ostia(ref, sp, aorta=aorta, ct=ct, _centreline=cl)
    pm = pred > 0
    grown = (ndimage.binary_dilation(pm, structure=_ball(tol_mm / 2.0, sp))
             if (tol_mm > 0 and pm.any()) else pm)
    gl, _ = components(grown)
    comp_of_pred = np.where(pm, gl, 0)
    reach = max(tol_mm, float(sp.max()))
    rr = np.ceil(reach / sp).astype(int)
    rooted_comps = set()
    for p in report.points:
        win = tuple(slice(max(p[k] - rr[k], 0), min(p[k] + rr[k] + 1, ref.shape[k]))
                    for k in range(3))
        sub = comp_of_pred[win]
        g = np.argwhere(sub > 0)
        if len(g):
            off = np.array([s.start for s in win])
            d = np.linalg.norm((g + off - np.array(p)) * sp, axis=1)
            rooted_comps |= set(sub[tuple(g[d <= reach].T)].tolist())
    rpts = cl.pts
    rlab = ref[tuple(rpts.T)]
    plab_at_ref = pred[tuple(rpts.T)]
    rooted = np.isin(comp_of_pred[tuple(rpts.T)], list(rooted_comps)) if rooted_comps \
        else np.zeros(len(rpts), dtype=bool)
    psk = _skeletonise(pm)
    plab_sk = pred[psk]
    rlab_at_pred = ref[psk]
    per, rec_d, prec_d = {}, {}, {}
    for c in CLASSES:
        g = rlab == c
        if not g.any():
            continue
        rec = float(((plab_at_ref == c) & rooted & g).sum() / g.sum())
        pc = plab_sk == c
        prec = float((rlab_at_pred[pc] == c).mean()) if pc.any() else 0.0
        rec_d[c], prec_d[c] = rec, prec
        per[c] = 2 * rec * prec / (rec + prec) if rec + prec else 0.0
    rooted_fraction = float((rooted & (plab_at_ref > 0)).mean()) if len(rpts) else float("nan")
    return TreeF1(tf1=float(np.mean(list(per.values()))) if per else float("nan"), per_class=per,
                  recall=rec_d, precision=prec_d, rooted_fraction=rooted_fraction,
                  tol_mm=tol_mm, ostia=report, n_reference_centreline=int(len(rpts)))


# --------------------------------------------------------------------------------- gates (A2)
def fp_components(reference: np.ndarray, prediction: np.ndarray, *, threshold: float = 0.5,
                  min_voxels: int = MIN_COMPONENT_VOXELS) -> int:
    """A2's FP gate: predicted components (26-conn, after dropping those < ``min_voxels``) that
    touch no reference voxel. Read it on the **raw** prediction -- never after bridging, which
    hides false positives by attaching them to the tree (measured: 1.18 -> 0.88 per case)."""
    pm = raw_prediction(prediction, threshold, min_voxels) > 0
    lab, n = components(pm)
    touched = set(np.unique(lab[pm & (np.asarray(reference) > 0)]).tolist()) - {0}
    return int(n - len(touched))


def audit_bridges(reference: np.ndarray, before: np.ndarray, after: np.ndarray,
                  bridges: Iterable[dict], spacing: Sequence[float], *,
                  off_reference_mm: float = 1.0) -> BridgeAudit:
    """A2's bridge audit. ``before`` is the prediction a bridging step received, ``after`` what it
    returned, ``bridges`` its record: one dict per join with ``p`` (a voxel of the joined orphan
    piece, index tuple), ``q`` (the anchor-side voxel it was joined to) and ``gap_mm``.

    Per bridge: orphan size, whether the orphan touches the reference at all (no -> a false-positive
    blob was attached), whether it joined left to right (classes 1-3 vs 4 in the reference), and
    the number of added voxels further than ``off_reference_mm`` from any reference voxel."""
    sp = np.asarray(spacing, float)
    ref = np.asarray(reference)
    b_mask = np.asarray(before) > 0
    added = (np.asarray(after) > 0) & ~b_mask
    far = ndimage.distance_transform_edt(ref == 0, sampling=sp) > off_reference_mm
    lab, _ = components(b_mask)
    side = np.where(ref == 4, 2, np.where(ref > 0, 1, 0))
    if (ref > 0).any():
        _, inds = ndimage.distance_transform_edt(ref == 0, sampling=sp, return_indices=True)
        nearest_side = side[tuple(inds)]
    else:
        nearest_side = side
    rows = []
    for b in bridges:
        p, q = tuple(int(x) for x in b["p"]), tuple(int(x) for x in b["q"])
        k = lab[p]
        orphan = lab == k if k > 0 else np.zeros_like(b_mask)
        touches = bool((orphan & (ref > 0)).any())
        o_side = np.bincount(side[orphan & (ref > 0)], minlength=3)[1:]
        o_side = int(o_side.argmax() + 1) if o_side.any() else 0
        a_side = int(nearest_side[q])
        rows.append({"gap_mm": round(float(b.get("gap_mm", float("nan"))), 2),
                     "orphan_voxels": int(orphan.sum()), "touches_reference": touches,
                     "cross_tree": bool(o_side and a_side and o_side != a_side)})
    total_added = int(added.sum())
    if rows:
        rows[-1]["added_voxels_total"] = total_added
        rows[-1]["added_voxels_off_reference"] = int((added & far).sum())
    return BridgeAudit(rows=rows,
                       fp_components_before=fp_components(ref, before),
                       fp_components_after=fp_components(ref, after))
