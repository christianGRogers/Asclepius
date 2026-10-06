"""tree-F1 @ 1.5 mm (Delta's definition, as re-implemented in experiments/Crucible/r2_eval.py; provisional per A9).
Per class: recall = reference centreline predicted as that class AND in a predicted component (gaps < tol joined)
touching a reference ostium (within 1.5 mm); precision = predicted centreline of that class inside reference voxels of
that class. Macro over classes present in the reference. Ostia passed in (thickest LM voxel / RCA, see sim.ostia)."""
import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

S26 = np.ones((3, 3, 3))


def drop_small(p4, n=100):
    lab, k = ndi.label(p4 > 0, S26)
    if k == 0: return p4
    sz = np.bincount(lab.ravel()); keep = sz >= n; keep[0] = False
    return np.where(keep[lab], p4, 0).astype(np.uint8)


def score(ref, p4, sp, rts, tol=1.5):
    refsk = skeletonize(ref > 0); pm = p4 > 0
    pd = (ndi.distance_transform_edt(~pm, sampling=sp) <= tol / 2) if tol > 0 else pm
    comp, _ = ndi.label(pd, S26); rc = set(); r = np.ceil(1.5 / sp).astype(int)
    for rt in rts:
        sl = tuple(slice(max(a - b, 0), a + b + 1) for a, b in zip(rt, r))
        g = np.stack(np.meshgrid(*[np.arange(s.start, min(s.stop, n)) for s, n in zip(sl, ref.shape)], indexing='ij'), -1)
        d = np.sqrt((((g - rt) * sp) ** 2).sum(-1)); sub = comp[sl][: d.shape[0], : d.shape[1], : d.shape[2]]
        rc |= set(np.unique(sub[(d <= 1.5) & (sub > 0)]).tolist())
    pts = np.argwhere(refsk); gl = ref[tuple(pts.T)]; pl = p4[tuple(pts.T)]
    rooted = np.isin(comp[tuple(pts.T)], list(rc)) if rc else np.zeros(len(pts), bool)
    psk = skeletonize(pm) if pm.any() else pm
    pp = np.argwhere(psk); ppl = p4[tuple(pp.T)]; ppr = ref[tuple(pp.T)]
    out = {}
    for c in (1, 2, 3, 4):
        g = gl == c
        if not g.any(): continue
        rec = float(((pl == c) & rooted & g).sum() / g.sum()); rec_u = float(((pl == c) & g).sum() / g.sum())
        pc = ppl == c; prec = float((ppr[pc] == c).mean()) if pc.any() else 0.0
        dice = float(2 * ((p4 == c) & (ref == c)).sum() / max(1, (p4 == c).sum() + (ref == c).sum()))
        out[c] = dict(rec=rec, rec_unrooted=rec_u, prec=prec, dice=dice,
                      tf1=2 * rec * prec / (rec + prec) if rec + prec else 0.0)
    return out


def macro(s, key='tf1'):
    return float(np.mean([v[key] for v in s.values()])) if s else float('nan')
