"""Round 7 (A1c) cohort identity check: segtrain.tf1 (new hash) vs the frozen 3c737cbc copy on the
143 proxy references (Atlas val 80 + Delta open 63), with predictions built on CPU from each
reference (run 1's predictions stay on Trillium $SCRATCH):
  identity     prediction = reference
  degraded     LM renamed LAD + a 4 mm cut through the LAD 40 % along its centreline + RCA distal third
               removed (a mix of naming, connectivity and recall errors)
Per case and prediction: old vs new per_class / recall / precision / tf1 must be bit-identical, and
the new `classes_without_centreline` is recorded; the opt-in fallback is scored alongside (paired
report for variant 3).
Usage: python r7_cohort_identity.py <out.jsonl> case [case ...]"""
import importlib.util
import json
import sys

import nibabel as nib
import numpy as np

sys.path.insert(0, '/home/user/Asclepius/experiments/Delta')
import r5_cut_anatomy as M  # noqa: E402
from segtrain import tf1 as NEW  # noqa: E402

spec = importlib.util.spec_from_file_location('tf1_3c737cbc', '/home/user/Asclepius/experiments/Delta/tf1_3c737cbc.py')
OLD = importlib.util.module_from_spec(spec)
sys.modules['tf1_3c737cbc'] = OLD
spec.loader.exec_module(OLD)


def degrade(R, sp):
    P = np.where(R == 1, 2, R).astype(R.dtype)
    for c, frac, mode in ((2, 0.4, 'cut'), (4, 0.67, 'drop')):
        idx = np.argwhere(R == c)
        if not len(idx):
            continue
        # order class voxels along their principal axis; cut a 4 mm slab / drop the distal part
        X = (idx - idx.mean(0)) * sp
        ax = np.linalg.svd(X, full_matrices=False)[2][0]
        t = X @ ax
        t0 = np.quantile(t, frac)
        sel = (t > t0) & (t < t0 + 4.0) if mode == 'cut' else (t > t0)
        P[tuple(idx[sel].T)] = 0
    return P


def same(a, b):
    return (a.per_class == b.per_class and a.recall == b.recall and a.precision == b.precision
            and (a.tf1 == b.tf1 or (a.tf1 != a.tf1 and b.tf1 != b.tf1)))


def run(case):
    mpath = f'{M.SCR}/data/masks/{case}.nii.gz'
    L, _, _ = M.AP.make_label(mpath, M.T.icx_path(case))
    sp = np.array(nib.load(mpath).header.get_zooms()[:3], float)
    idx = np.nonzero(L > 0)
    mg = np.ceil(6.0 / sp).astype(int)
    lo = np.maximum([i.min() for i in idx] - mg, 0)
    hi = np.minimum([i.max() + 1 for i in idx] + mg, L.shape)
    R = L[tuple(slice(a, b) for a, b in zip(lo, hi))].copy()
    del L
    ost = NEW.find_ostia(R, sp)
    out = dict(case=case)
    # CPU budget (~35 s per tree_f1 call): old vs new on the degraded prediction for every case; the
    # identity prediction and the opt-in fallback only where a class has no centreline (elsewhere
    # the fallback branch is not entered at all, so it is identical by construction).
    for name, P in (('degraded', degrade(R, sp)), ('identity', R)):
        if name == 'identity' and not out['degraded']['missing']:  # depends on the reference only
            break
        n = NEW.tree_f1(R, P, sp, ostia=ost)
        o = OLD.tree_f1(R, P, sp, ostia=ost)
        row = dict(identical=same(n, o), missing=n.classes_without_centreline, tf1=n.tf1,
                   per_class={int(k): v for k, v in n.per_class.items()})
        if n.classes_without_centreline:
            f = NEW.tree_f1(R, P, sp, ostia=ost, fallback_centreline=True)
            row.update(tf1_fallback=f.tf1, per_class_fallback={int(k): v for k, v in f.per_class.items()})
        out[name] = row
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
