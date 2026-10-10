"""A1b: flag rate of the revised A1 rule (segtrain.tf1.find_ostia with a TotalSegmentator aorta, plus the
CT for pool_thick where one is on disk), per reference tree, on the 84 cases with aorta masks; and how many
flagged / unflagged trees have their ostium within 5 mm of the expert start point.
Usage: python r6_flags.py <aorta_dir> <out.jsonl> case [case ...]"""
import json
import os
import sys

import nibabel as nib
import numpy as np

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
    ctp = f'{M.SCR}/data/ct/{case}.nii.gz'
    ct = np.asanyarray(nib.load(ctp).dataobj)[sl].astype(np.float32) if os.path.exists(ctp) else None
    rep = S.find_ostia(R, sp, aorta=ao, ct=ct)
    true = {}
    for side in ('left', 'right'):
        for d in M.CL_DIRS:
            p = f'{d}/{icx_id}.coronary_{side}_centerline.vtk'
            if os.path.exists(p):
                P = np.array(M.starts(p))
                true[side] = (np.linalg.inv(A) @ np.c_[P, np.ones(len(P))].T).T[:, :3] - lo
                break
    rows = []
    for o in rep.ostia:
        side = o.side if o.side in ('left', 'right') else ('right' if R[o.point] == 4 else 'left')
        P = true.get(side)
        d = float(np.min(np.linalg.norm((P - np.array(o.point)) * sp, axis=1))) if P is not None else None
        rows.append(dict(side=side, rule=o.rule, flagged=o.flagged, rules=sorted(o.candidates),
                         disagreement_mm=round(o.disagreement_mm, 2), d_true_mm=None if d is None else round(d, 2)))
    return dict(case=case, has_ct=ct is not None, trees=rows)


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
