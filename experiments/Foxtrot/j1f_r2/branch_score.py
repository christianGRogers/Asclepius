"""Janus 1-F round 2 (Foxtrot): the branch scorer of F-A6 / §5 item 2, as a reference implementation to freeze by hash.

Inputs: a 1-F reference `ref` and prediction `pred` (values 0-12, ref may hold 255), voxel spacing `z` (mm).
Per branch class c in D1, D2, D3, OM1, OM2, Ramus, PDA, PLB:
  * centreline   -- the skeleton of the whole reference tree (ref > 0, 255 included so the tree stays connected),
                    restricted to class c; a reference piece with no skeleton voxel uses its maximal-EDT voxel.
  * piece        -- a 26-connected component of ref == c. Each piece is one reference branch (R-PDA can be two).
  * detected     -- >= 50 % of the piece's centreline lies within 1.5 mm (D3) of predicted vessel of ANY class.
  * named        -- among a detected piece's covered centreline points, the class of the nearest predicted voxel;
                    the piece is named right iff c is the strict majority (plurality, ties count as wrong).
  * presence     -- ref: class-c centreline >= 5.0 mm; pred: the skeleton of pred > 0 labelled c is >= 5.0 mm
                    (skeleton voxels x mean voxel side, as Delta's census).
  * branch tF1   -- `segtrain.tf1.tree_f1` at the pinned A1c hash (24441cf8...), on {c -> 1, other vessel -> 2},
                    with ONE ostium per reference piece: the piece's centreline point nearest its parent
                    (D1-D3 -> LAD; OM1, OM2, Ramus -> LCx; PDA, PLB -> whichever of LCx/RCA the piece touches most).
                    tF1_c = per_class[1]. Unrooted predicted pieces lose recall, as in A1c.
Case-level aggregation is left to the caller: recall = detected pieces / pieces (pooled over cases);
naming = named / detected (pooled); presence agreement = share of cases where ref and pred presence agree.
"""
import os, sys
import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../src'))
from segtrain.tf1 import tree_f1, Ostium, OstiumReport  # noqa: E402

BRANCH = {5: 'D1', 6: 'D2', 7: 'D3', 8: 'OM1', 9: 'OM2', 10: 'Ramus', 11: 'PDA', 12: 'PLB'}
PARENTS = {5: [2], 6: [2], 7: [2], 8: [3], 9: [3], 10: [3], 11: [3, 4], 12: [3, 4]}
TOL, DET, PRES = 1.5, 0.5, 5.0
S26 = np.ones((3, 3, 3), bool)


def _parent_of(ref, piece, c):
    cand = PARENTS[c]
    if len(cand) == 1:
        return cand[0]
    ring = ndi.binary_dilation(piece, S26, iterations=2) & ~piece
    v = ref[ring]
    nl = int(np.isin(v, [3, 8, 9, 10]).sum()); nr = int((v == 4).sum())
    return 3 if nl > nr else 4


def score_case(ref, pred, z, with_tf1=False, classes=tuple(BRANCH)):
    z = np.asarray(z, float); step = float(z.mean())
    tree = ref > 0
    rsk = skeletonize(tree)
    rsk &= (ref != 255)
    pm = pred > 0
    if pm.any():
        dist, ind = ndi.distance_transform_edt(~pm, sampling=z, return_indices=True)
    else:
        dist, ind = np.full(ref.shape, np.inf), None
    psk = skeletonize(pm) if pm.any() else np.zeros_like(pm)
    pdist = {}
    out = {}
    for c in classes:
        m = ref == c
        r_len = float((rsk & m).sum()) * step
        p_len = float((psk & (pred == c)).sum()) * step
        row = {'ref_present': r_len >= PRES, 'pred_present': p_len >= PRES, 'ref_mm': round(r_len, 1),
               'pred_mm': round(p_len, 1), 'pieces': []}
        if m.any():
            comp, n = ndi.label(m, S26)
            ostia = []
            for i in range(1, n + 1):
                p = comp == i
                pts = np.argwhere(rsk & p)
                if not len(pts):
                    e = ndi.distance_transform_edt(p, sampling=z)
                    pts = np.argwhere(e == e.max())[:1]
                d = dist[tuple(pts.T)]
                cov = d <= TOL
                det = bool(cov.mean() >= DET)
                named = None
                if det and ind is not None:
                    q = pts[cov]
                    labs = pred[ind[0][tuple(q.T)], ind[1][tuple(q.T)], ind[2][tuple(q.T)]]
                    cnt = np.bincount(labs, minlength=13)
                    top = cnt.max()
                    named = bool(cnt[c] == top and (cnt == top).sum() == 1)
                row['pieces'].append({'mm': round(len(pts) * step, 1), 'covered': round(float(cov.mean()), 3),
                                      'detected': det, 'named': named})
                par = _parent_of(ref, p, c)
                if par not in pdist and (ref == par).any():
                    pdist[par] = ndi.distance_transform_edt(ref != par, sampling=z)
                if par in pdist:
                    pd_ = pdist[par][tuple(pts.T)]
                    o = tuple(int(v) for v in pts[int(np.argmin(pd_))])
                else:
                    o = tuple(int(v) for v in pts[0])
                ostia.append(Ostium(tree=i, point=o, rule='origin'))
            if with_tf1:
                r2 = np.where(m, 1, np.where(tree, 2, 0)).astype(np.uint8)
                p2 = np.where(pred == c, 1, np.where(pm, 2, 0)).astype(np.uint8)
                t = tree_f1(r2, p2, z, ostia=OstiumReport(ostia, provisional=False, rules=('origin',)))
                row['tf1'] = t.per_class.get(1, float('nan'))
                row['tf1_recall'] = t.recall.get(1, float('nan'))
                row['tf1_precision'] = t.precision.get(1, float('nan'))
        out[BRANCH[c]] = row
    return out


def aggregate(rows):
    """rows: list of score_case outputs (one per case). Pooled recall, naming, presence agreement, mean tF1."""
    agg = {}
    for nm in BRANCH.values():
        pcs = [p for r in rows for p in r[nm]['pieces']]
        det = [p for p in pcs if p['detected']]
        pres = [r[nm]['ref_present'] == r[nm]['pred_present'] for r in rows]
        t = [r[nm]['tf1'] for r in rows if 'tf1' in r[nm] and r[nm]['pieces']]
        agg[nm] = {'ref_cases': sum(r[nm]['ref_present'] for r in rows), 'pieces': len(pcs),
                   'recall': len(det) / len(pcs) if pcs else None,
                   'naming': sum(p['named'] for p in det) / len(det) if det else None,
                   'presence_agreement': float(np.mean(pres)) if rows else None,
                   'tf1_mean': float(np.nanmean(t)) if t else None}
    return agg
