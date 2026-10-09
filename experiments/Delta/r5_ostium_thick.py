"""Round 5: do the cheap ostium rules survive the THICK reference (the binding convention, D0)?

The 116/116 validation (vault: 'Two cheap ostium rules find 116 of 116 true ostia') was on the
ImageCAS-X lumen. Atlas's short R1 is scored on the projected proxy -- the ImageCAS mask split into 4
classes -- and r5_cut_anatomy.py found Atlas's `thick` ostium tens of mm from the expert ostium on
cases whose whole RCA scored tF1 = 0. Here, on every case with a local CT and ImageCAS-X truth, per
reference tree component of the proxy:

  thick        thickest centreline endpoint, LM endpoints preferred (Atlas's and segtrain's no-CT rule)
  pool_thick   thickest endpoint within 3 mm of the endpoint nearest the blood pool (segtrain, CT given)
  pool_near    the centreline voxel of ANY degree nearest the blood pool (proposed: the thick mask's
               ostium is often a pass-through point, e.g. where a conus branch leaves at the ostium)
  pool_near_r  among centreline voxels within 2 mm of the pool-nearest one, the thickest

Each expert start point is matched to the tree containing it; distances in mm.
Usage: python r5_ostium_thick.py <out.jsonl> case [case ...]"""
import json
import os
import sys

import nibabel as nib
import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, '/home/user/Asclepius/experiments/Delta')
import r5_cut_anatomy as M  # noqa: E402
from segtrain import tf1 as S  # noqa: E402


def run(case):
    icx_id = int(case[1:]) + 1
    mpath = f'{M.SCR}/data/masks/{case}.nii.gz'
    lab_full, A, _ = M.AP.make_label(mpath, M.T.icx_path(case))
    sp = np.array(nib.load(mpath).header.get_zooms()[:3], float)
    idx = np.nonzero(lab_full > 0)
    mg = np.ceil(10.0 / sp).astype(int)
    lo = np.maximum([i.min() for i in idx] - mg, 0)
    hi = np.minimum([i.max() + 1 for i in idx] + mg, lab_full.shape)
    sl = tuple(slice(a, b) for a, b in zip(lo, hi))
    R = lab_full[sl].copy()
    del lab_full
    ct = np.asanyarray(nib.load(f'{M.SCR}/data/ct/{case}.nii.gz').dataobj)[sl].astype(np.float32)
    Rm = R > 0
    cl = S._Centreline(Rm, sp)
    rep_thick = S.find_ostia(R, sp, _centreline=cl)
    rep_pool = S.find_ostia(R, sp, ct=ct, _centreline=cl)
    pool = S.blood_pool(ct, sp, exclude=Rm)
    d_pool = ndi.distance_transform_edt(~pool, sampling=sp) if pool.any() else None
    comps, n = S.components(Rm)
    csk = comps[tuple(cl.pts.T)]
    choice = {}
    for o in rep_thick.ostia:
        choice.setdefault(o.tree, {})['thick'] = np.array(o.point)
    for o in rep_pool.ostia:
        if 'pool_thick' in o.candidates:
            choice.setdefault(o.tree, {})['pool_thick'] = np.array(o.candidates['pool_thick'])
    if d_pool is not None:
        dsk = d_pool[tuple(cl.pts.T)]
        P = cl.pts * sp
        for k in choice:
            on = np.nonzero(csk == k)[0]
            v = on[int(np.argmin(dsk[on]))]
            choice[k]['pool_near'] = cl.pts[v]
            near = on[np.linalg.norm(P[on] - P[v], axis=1) <= 2.0]
            choice[k]['pool_near_r'] = cl.pts[near[int(np.argmax(cl.radius[near]))]]
            choice[k]['_pool_mm'] = float(dsk[v])
    S_ = []
    for side in ('left', 'right'):
        for d in M.CL_DIRS:
            p = f'{d}/{icx_id}.coronary_{side}_centerline.vtk'
            if os.path.exists(p):
                S_ += [(side, s) for s in M.starts(p)]
                break
    _, inds = ndi.distance_transform_edt(comps == 0, return_indices=True)
    out = dict(case=case, pool_found=d_pool is not None, matches=[])
    for side, w in S_:
        v = (np.linalg.inv(A) @ np.r_[w, 1])[:3] - lo
        vi = np.clip(np.round(v).astype(int), 0, np.array(R.shape) - 1)
        k = int(comps[tuple(inds[:, vi[0], vi[1], vi[2]])])
        if k not in choice:
            out['matches'].append(dict(side=side, tree=k, missing=True))
            continue
        dd = {r: round(float(np.linalg.norm((p - v) * sp)), 2) for r, p in choice[k].items() if r[0] != '_'}
        out['matches'].append(dict(side=side, tree=k, lm=bool((R == 1).any()),
                                   pool_mm=round(choice[k].get('_pool_mm', float('nan')), 2), **dd))
    return out


if __name__ == '__main__':
    with open(sys.argv[1], 'a') as f:
        for c in sys.argv[2:]:
            try:
                r = run(c)
            except Exception as e:  # noqa
                r = dict(case=c, error=repr(e))
            f.write(json.dumps(r) + '\n')
            f.flush()
            print(c, r.get('error', ''), flush=True)
