"""Round 5: the A1 rule of record (TotalSegmentator aorta contact) on the THICK reference.

Per reference tree component of Atlas's proxy, with a TotalSegmentator aorta mask (aorta_ts.py):
  aorta_end   thickest centreline ENDPOINT within 5 mm of the aorta (segtrain.tf1 as implemented)
  aorta_any   the centreline voxel of any degree nearest the aorta (proposed: the thick mask's ostium
              is often a pass-through point of the skeleton, so it is not an endpoint)
  thick       for reference
Each expert ostium (ImageCAS-X centreline start) is matched to the tree containing it.
Usage: python r5_aorta_rule.py <aorta_dir> <out.jsonl> case [case ...]"""
import json
import os
import sys

import nibabel as nib
import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, '/home/user/Asclepius/experiments/Delta')
import r5_cut_anatomy as M  # noqa: E402
from segtrain import tf1 as S  # noqa: E402


def run(case, aorta_dir):
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
    ao = np.asanyarray(nib.load(f'{aorta_dir}/{case}_aorta.nii.gz').dataobj)[sl] > 0
    Rm = R > 0
    cl = S._Centreline(Rm, sp)
    rep = S.find_ostia(R, sp, aorta=ao, _centreline=cl)
    comps, _ = S.components(Rm)
    csk = comps[tuple(cl.pts.T)]
    d_ao = ndi.distance_transform_edt(~ao, sampling=sp) if ao.any() else None
    choice = {}
    for o in rep.ostia:
        c = choice.setdefault(o.tree, {})
        c['thick'] = np.array(o.candidates['thick'])
        if 'aorta' in o.candidates:
            c['aorta_end'] = np.array(o.candidates['aorta'])
        c['_flag'] = o.flagged
        if d_ao is not None:
            on = np.nonzero(csk == o.tree)[0]
            dv = d_ao[tuple(cl.pts[on].T)]
            v = on[int(np.argmin(dv))]
            c['aorta_any'] = cl.pts[v]
            c['_ao_mm'] = float(dv.min())
    new = S.find_ostia(R, sp, aorta=ao, _centreline=cl)  # segtrain.tf1 as revised in Round 5
    out = dict(case=case, aorta_vox=int(ao.sum()), matches=[])
    for side in ('left', 'right'):
        for d in M.CL_DIRS:
            p = f'{d}/{icx_id}.coronary_{side}_centerline.vtk'
            if not os.path.exists(p):
                continue
            _, inds = ndi.distance_transform_edt(comps == 0, return_indices=True)
            for w in M.starts(p):
                v = (np.linalg.inv(A) @ np.r_[w, 1])[:3] - lo
                vi = np.clip(np.round(v).astype(int), 0, np.array(R.shape) - 1)
                k = int(comps[tuple(inds[:, vi[0], vi[1], vi[2]])])
                if k not in choice:
                    out['matches'].append(dict(side=side, tree=k, missing=True))
                    continue
                c = dict(choice[k])
                if d_ao is not None:  # per component AND side: a proxy can join left and right trees
                    lsk = R[tuple(cl.pts.T)]
                    on = np.nonzero((csk == k) & ((lsk == 4) if side == 'right' else np.isin(lsk, (1, 2, 3))))[0]
                    if len(on):
                        dv = d_ao[tuple(cl.pts[on].T)]
                        c['aorta_any_side'] = cl.pts[on[int(np.argmin(dv))]]
                        c['_ao_side_mm'] = float(dv.min())
                dd = {r: round(float(np.linalg.norm((q - v) * sp)), 2) for r, q in c.items() if r[0] != '_'}
                dd['ao_side_mm'] = round(c.get('_ao_side_mm', float('nan')), 2)
                mine = [o for o in new.ostia if o.tree == k and o.side in (side, 'tree')]
                if mine:
                    dd['new'] = round(float(np.linalg.norm((np.array(mine[0].point) - v) * sp)), 2)
                    dd['new_rule'] = mine[0].rule
                    dd['new_flag'] = mine[0].flagged
                out['matches'].append(dict(side=side, tree=k, flagged=c['_flag'],
                                           ao_mm=round(c.get('_ao_mm', float('nan')), 2), **dd))
            break
    return out


if __name__ == '__main__':
    ad, outp = sys.argv[1:3]
    with open(outp, 'a') as f:
        for c in sys.argv[3:]:
            try:
                r = run(c, ad)
            except Exception as e:  # noqa
                r = dict(case=c, error=repr(e))
            f.write(json.dumps(r) + '\n')
            f.flush()
            print(c, r.get('error', ''), flush=True)
