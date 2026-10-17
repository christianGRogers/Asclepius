"""Round 8: is the reference centreline that run 1 misses contrast-filled lumen? HU (CT, 0.7 mm Gaussian)
at reference centreline voxels of each class, split by ImageCAS-X-traced vs mask-only and recalled vs
lost (same definitions as r8_miss_census.py). Val cases with a CT on disk only.
Usage: python r8_hu_lost.py <out.jsonl> case [case ...]"""
import json
import sys

import nibabel as nib
import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, '/home/user/Asclepius/experiments/Delta')
import r8_miss_census as C  # noqa: E402
from segtrain import tf1 as T  # noqa: E402


def run(case):
    M = C.M
    mpath = f'{C.SCR}/data/masks/{case}.nii.gz'
    L, _, _ = M.AP.make_label(mpath, M.T.icx_path(case))
    sp = np.array(nib.load(mpath).header.get_zooms()[:3], float)
    P = np.asarray(nib.load(f'{C.PRED}/{case}.nii.gz').dataobj).astype(np.uint8)
    ao = np.asarray(nib.load(f'{C.AORTA}/{case}_aorta.nii.gz').dataobj) > 0
    raw = np.asarray(nib.load(M.T.icx_path(case)).dataobj) > 0
    ct = np.asarray(nib.load(f'{C.SCR}/data/ct/{case}.nii.gz').dataobj)
    u = (L > 0) | (P > 0) | ao
    idx = [np.nonzero(u.any(axis=tuple(j for j in range(3) if j != k)))[0] for k in range(3)]
    mv = np.ceil(C.MARGIN_MM / sp).astype(int)
    lo = np.maximum([a[0] for a in idx] - mv, 0)
    hi = np.minimum([a[-1] + 1 for a in idx] + mv, L.shape)
    sl = tuple(slice(int(a), int(b)) for a, b in zip(lo, hi))
    R, P, ao, icx = L[sl].copy(), P[sl].copy(), ao[sl].copy(), raw[sl].copy()
    hu = ndi.gaussian_filter(ct[sl].astype(np.float32), sigma=0.7 / sp)
    del L, raw, ct
    rep = T.find_ostia(R, sp, aorta=ao)
    pred = np.where(T.remove_small_components(P > 0, T.MIN_COMPONENT_VOXELS), P, 0)
    cl = T._Centreline(R > 0, sp)
    pm = pred > 0
    gl, _ = T.components(ndi.binary_dilation(pm, structure=T._ball(T.TOLERANCE_MM / 2.0, sp)))
    cop = np.where(pm, gl, 0)
    reach = max(T.TOLERANCE_MM, float(sp.max()))
    rr = np.ceil(reach / sp).astype(int)
    rooted_comps = set()
    for p in rep.points:
        win = tuple(slice(max(p[k] - rr[k], 0), min(p[k] + rr[k] + 1, R.shape[k])) for k in range(3))
        sub = cop[win]
        g = np.argwhere(sub > 0)
        if len(g):
            off = np.array([s.start for s in win])
            d = np.linalg.norm((g + off - np.array(p)) * sp, axis=1)
            rooted_comps |= set(sub[tuple(g[d <= reach].T)].tolist())
    pts = cl.pts
    rl, pl = R[tuple(pts.T)], pred[tuple(pts.T)]
    rooted = np.isin(cop[tuple(pts.T)], list(rooted_comps))
    traced = ndi.distance_transform_edt(~icx, sampling=sp)[tuple(pts.T)] <= 1.0
    h = hu[tuple(pts.T)]
    aorta_hu = float(np.median(hu[ao])) if ao.any() else None
    out = dict(case=case, aorta_hu=aorta_hu, classes={})
    for c in T.CLASSES:
        g = rl == c
        if not g.any():
            continue
        ok = (pl == c) & rooted
        cell = {}
        for tname, tm in (('traced', traced), ('mask_only', ~traced)):
            for oname, om in (('recalled', ok), ('lost', ~ok)):
                s = g & tm & om
                cell[f'{tname}_{oname}'] = [int(s.sum()), float(np.median(h[s])) if s.any() else None]
        out['classes'][int(c)] = cell
    return out


if __name__ == '__main__':
    with open(sys.argv[1], 'a') as fh:
        for c in sys.argv[2:]:
            try:
                r = run(c)
            except Exception as e:  # noqa
                r = dict(case=c, error=repr(e))
            fh.write(json.dumps(r) + '\n')
            fh.flush()
            print(c, r.get('error', ''), flush=True)
