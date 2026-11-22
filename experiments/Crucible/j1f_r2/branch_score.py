"""Janus 1-F round 2 (Crucible): the branch scorer's definitions, as one frozen module (Round 1 section 5, item 2).

Every function here is the definition proposed for `trillium/janus1f`'s branch scorer; the PR freezes this file by its
sha256 (printed by `selftest.py`). Arrays are 1-F stage-1 class maps on the label grid, axis order = `spacing` (nibabel).

1-F stage-1 classes (F-A3): 0 bg, 1 LM, 2 LAD, 3 LCx, 4 RCA, 5 D1, 6 D2, 7 D3, 8 OM1, 9 OM2, 10 Ramus, 11 PDA, 12 PLB;
255 = ignore (an ImageCAS-X "Other" piece touching neither the LAD side nor the LCx side). 255 is background for every
definition below except `to_1f`, which makes it.

Definitions (each is one function):
  * reference branch (`pieces`): one 26-connected component of one branch class in the reference, whose centreline
    (the whole tree's skeleton, `segtrain.tf1._skeletonise`, restricted to the piece) is >= PRESENT_MM long. Shorter
    pieces are not branches: they are neither detected nor missed.
  * centreline length (`length_mm`): sum of the 26-neighbour edge lengths between skeleton voxels, in mm.
  * presence (`presence`): a class is present in a case when its centreline (reference: as above; prediction: the
    skeleton of the predicted foreground, labelled by predicted class) totals >= PRESENT_MM. Presence agreement of a
    class = share of cases where reference and prediction agree.
  * detection (`detect_and_name`): a reference branch is detected when >= 50 % of its centreline voxels lie within
    TOL_MM (D3: 1.5 mm) of predicted foreground of ANY class. Detection recall of a class = detected / reference
    branches, pooled over cases (a ratio of sums, not a mean of per-case ratios).
  * naming (`detect_and_name`): each covered centreline voxel (within TOL_MM) takes the class of its nearest predicted
    foreground voxel; a detected branch is named right when strictly more than half of its covered voxels take its
    reference class. Naming accuracy of a class = named right / detected, pooled.
  * branch tF1 (`branch_tf1`): A1c's `segtrain.tf1.tree_f1` (sha256 24441cf8...5254, unchanged), run on class c alone
    (reference = pieces of c, prediction = predicted c), with one root per reference piece: the piece's centreline
    voxel nearest to the rest of the reference tree (its origin). R-PDA in two pieces gets two roots.
  * four-class collapse by origin (`collapse4`; D25, D1, D1b, D47 Q1 (A), F-A4): D1-D3 -> LAD; OM1, OM2, Ramus -> LCx;
    each 26-connected PDA/PLB component goes to whichever of LCx or RCA has more voxels in its one-voxel ring
    (ties and no contact -> RCA). `rca_always=True` is Q1 (C), kept for the record; D47 chose (A).
  * hierarchical decoding (`decode_hier`; F-A4): territory = argmax of summed probabilities over {bg}, {LM},
    {LAD, D1, D2, D3}, {LCx, OM1, OM2, Ramus}, {RCA, PDA, PLB}; class = argmax inside the territory. Reading T replaces
    the territory with Janus 0's argmax (`decode_T`).
"""
from __future__ import annotations

import os
import sys

import numpy as np
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'src'))
from segtrain import tf1 as A1c  # noqa: E402  (pinned 24441cf8...5254)

PRESENT_MM = 5.0
TOL_MM = 1.5
BRANCHES = {5: 'D1', 6: 'D2', 7: 'D3', 8: 'OM1', 9: 'OM2', 10: 'Ramus', 11: 'PDA', 12: 'PLB'}
GATED = (5, 6, 8, 9, 11, 12)
NAMES = ['bg', 'LM', 'LAD', 'LCx', 'RCA', 'D1', 'D2', 'D3', 'OM1', 'OM2', 'Ramus', 'PDA', 'PLB']
TERR = {0: (0,), 1: (1,), 2: (2, 5, 6, 7), 3: (3, 8, 9, 10), 4: (4, 11, 12)}
S26 = np.ones((3, 3, 3), bool)
_OFF = [(a, b, c) for a in (-1, 0, 1) for b in (-1, 0, 1) for c in (-1, 0, 1) if (a, b, c) > (0, 0, 0)]


# ----------------------------------------------------------------------------------------------- labels (F-A3)
def to_1f(icx: np.ndarray, zooms) -> tuple[np.ndarray, dict]:
    """ImageCAS-X 14 classes -> 1-F stage-1 map under D47 Q1 (A) and F-A3: Delta v1's `j1f_labels.map_case` with
    `--left-pda name`, except that "Other" pieces touching neither side become 255 (Foxtrot), not the nearest class."""
    sys.path.insert(0, os.path.join(HERE, '..', '..', 'Delta', 'j1f_r1'))
    import j1f_labels as D  # Delta v1, round 1 (the plan in force)
    from census import LAD_SIDE, LCX_SIDE
    out, info = D.map_case(icx, np.asarray(zooms, float), left_pda='name')
    info['ignore'] = 0
    o = icx == 14
    if o.any():
        comp, nc = ndi.label(o, S26)
        for i in range(1, nc + 1):
            p = comp == i
            ring = ndi.binary_dilation(p, S26, iterations=2) & ~p
            v = icx[ring]
            if not np.isin(v, list(LAD_SIDE | LCX_SIDE)).any():
                out[p] = 255
                info['ignore'] += 1
    return out, info


# ------------------------------------------------------------------------------------------------- geometry
def length_mm(skel: np.ndarray, sp) -> float:
    """Centreline length: sum of 26-neighbour edge lengths between skeleton voxels (each edge once)."""
    sp = np.asarray(sp, float)
    tot = 0.0
    for off in _OFF:
        a = skel[tuple(slice(max(-o, 0), skel.shape[k] - max(o, 0)) for k, o in enumerate(off))]
        b = skel[tuple(slice(max(o, 0), skel.shape[k] - max(-o, 0)) for k, o in enumerate(off))]
        tot += float((a & b).sum()) * float(np.linalg.norm(np.array(off) * sp))
    return tot


def skeleton_labels(m: np.ndarray) -> np.ndarray:
    """Whole-tree skeleton of a class map (255 and 0 are background), labelled by class (0 off the skeleton)."""
    fg = (m > 0) & (m != 255)
    sk = A1c._skeletonise(fg) if fg.any() else np.zeros_like(fg)
    return np.where(sk, m, 0).astype(np.uint8)


def pieces(ref: np.ndarray, sp, ref_skel: np.ndarray | None = None, classes=BRANCHES, min_mm=PRESENT_MM):
    """Reference branches: per class, (component mask, its skeleton mask, length mm) for each piece >= min_mm."""
    rs = skeleton_labels(ref) if ref_skel is None else ref_skel
    out = {c: [] for c in classes}
    for c in classes:
        comp, n = ndi.label(ref == c, S26)
        for i, sl in enumerate(ndi.find_objects(comp), start=1):
            if sl is None:
                continue
            sl = tuple(slice(max(s.start - 1, 0), s.stop + 1) for s in sl)
            L = length_mm((comp[sl] == i) & (rs[sl] == c), sp)
            if L >= min_mm:
                p = comp == i
                out[c].append((p, p & (rs == c), L))
    return out


def presence(m: np.ndarray, sp, skel: np.ndarray | None = None, classes=BRANCHES) -> dict:
    sk = skeleton_labels(m) if skel is None else skel
    return {c: length_mm(sk == c, sp) >= PRESENT_MM for c in classes}


# --------------------------------------------------------------------------------------- detection and naming
def detect_and_name(ref: np.ndarray, pred: np.ndarray, sp, ref_pieces=None) -> dict:
    """Per class: [n_ref_branches, n_detected, n_named_right], counted per reference branch."""
    sp = np.asarray(sp, float)
    rp = pieces(ref, sp) if ref_pieces is None else ref_pieces
    pfg = (pred > 0) & (pred != 255)
    res = {c: [0, 0, 0] for c in BRANCHES}
    if not pfg.any():
        for c in BRANCHES:
            res[c][0] = len(rp[c])
        return res
    dist, idx = ndi.distance_transform_edt(~pfg, sampling=sp, return_indices=True)
    for c in BRANCHES:
        for _, s, _ in rp[c]:
            pts = np.argwhere(s)
            d = dist[tuple(pts.T)]
            cov = d <= TOL_MM
            res[c][0] += 1
            if cov.mean() >= 0.5:
                res[c][1] += 1
                near = idx[(slice(None),) + tuple(pts[cov].T)]
                lab = pred[tuple(near)]
                if (lab == c).sum() * 2 > len(lab):
                    res[c][2] += 1
    return res


# ------------------------------------------------------------------------------------------------- branch tF1
def origin(piece_skel: np.ndarray, rest: np.ndarray, sp) -> tuple:
    """The piece's centreline voxel nearest the rest of the reference tree (its origin)."""
    sp = np.asarray(sp, float)
    pts = np.argwhere(piece_skel)
    if not rest.any():
        return tuple(int(v) for v in pts[0])
    d = ndi.distance_transform_edt(~rest, sampling=sp)
    return tuple(int(v) for v in pts[np.argmin(d[tuple(pts.T)])])


def branch_tf1(ref: np.ndarray, pred: np.ndarray, sp, c: int, ref_pieces=None):
    """A1c tree-F1 of class c alone, rooted at each reference piece's origin. None if c has no reference branch."""
    rp = (pieces(ref, sp) if ref_pieces is None else ref_pieces)[c]
    if not rp:
        return None
    rest = (ref > 0) & (ref != 255) & (ref != c)
    ost = [A1c.Ostium(tree=i, point=origin(s, rest, sp), rule='origin') for i, (_, s, _) in enumerate(rp)]
    rmask = np.zeros(ref.shape, np.uint8)
    for p, _, _ in rp:
        rmask[p] = 1
    r = A1c.tree_f1(rmask, (pred == c).astype(np.uint8), sp,
                    ostia=A1c.OstiumReport(ost, provisional=False, rules=('origin',)))
    return r.per_class.get(1, 0.0)


# ------------------------------------------------------------------------------------------- collapse, decode
def collapse4(m: np.ndarray, rca_always: bool = False) -> np.ndarray:
    lut = np.array([0, 1, 2, 3, 4, 2, 2, 2, 3, 3, 3, 4, 4], np.uint8)
    mm = np.where(m == 255, 0, m)
    out = lut[mm]
    if rca_always:
        return out
    pp = np.isin(mm, (11, 12))
    if pp.any():
        comp, n = ndi.label(pp, S26)
        for i in range(1, n + 1):
            p = comp == i
            ring = ndi.binary_dilation(p, S26) & ~p
            v = out[ring]
            out[p] = 3 if (v == 3).sum() > (v == 4).sum() else 4
    return out


def decode_hier(prob: np.ndarray) -> np.ndarray:
    """prob: (13, ...) softmax. Territory by summed probability, then the class inside it."""
    ts = np.stack([prob[list(TERR[t])].sum(0) for t in range(5)])
    return _within(prob, ts.argmax(0))


def decode_T(prob: np.ndarray, janus0_argmax: np.ndarray) -> np.ndarray:
    """Reading T: Janus 0's argmax territory (0-4), 1-F's class inside it."""
    return _within(prob, janus0_argmax)


def _within(prob, terr):
    out = np.zeros(terr.shape, np.uint8)
    for t, cl in TERR.items():
        sel = terr == t
        if len(cl) == 1:
            out[sel] = cl[0]
        else:
            out[sel] = np.array(cl, np.uint8)[prob[list(cl)][:, sel].argmax(0)]
    return out


# ------------------------------------------------------------------------------------------------- one case
def score_case(ref: np.ndarray, pred: np.ndarray, sp, with_tf1: bool = True) -> dict:
    """Everything the B gates and F-A9 reports need for one case."""
    rs = skeleton_labels(ref)
    rp = pieces(ref, sp, rs)
    out = {'presence_ref': {NAMES[c]: v for c, v in presence(ref, sp, rs).items()},
           'presence_pred': {NAMES[c]: v for c, v in presence(pred, sp).items()},
           'detect_name': {NAMES[c]: v for c, v in detect_and_name(ref, pred, sp, rp).items()},
           'piece_mm': {NAMES[c]: [round(L, 2) for _, _, L in rp[c]] for c in BRANCHES}}
    if with_tf1:
        out['branch_tf1'] = {NAMES[c]: branch_tf1(ref, pred, sp, c, rp) for c in BRANCHES}
    return out
