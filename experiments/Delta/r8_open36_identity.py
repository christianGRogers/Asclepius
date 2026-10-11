"""Round 8, A1c test 3 on the other run-1 predictions: the 36 clean open cases (atlas2 open36), new tf1
hash vs the frozen 3c737cbc copy, A1 aorta ostium; fallback scored where a class has no centreline.
Usage: python r8_open36_identity.py <out.jsonl> case [case ...]"""
import importlib.util
import json
import sys

import nibabel as nib
import numpy as np

sys.path.insert(0, '/home/user/Asclepius/experiments/Delta')
import r8_miss_census as C  # noqa: E402
from segtrain import tf1 as NEW  # noqa: E402

spec = importlib.util.spec_from_file_location('tf1_3c737cbc', '/home/user/Asclepius/experiments/Delta/tf1_3c737cbc.py')
OLD = importlib.util.module_from_spec(spec)
sys.modules['tf1_3c737cbc'] = OLD
spec.loader.exec_module(OLD)
PRED = f'{C.SCR}/round6/atlas2/open36/pred'


def run(case):
    M = C.M
    mpath = f'{C.SCR}/data/masks/{case}.nii.gz'
    L, _, _ = M.AP.make_label(mpath, M.T.icx_path(case))
    sp = np.array(nib.load(mpath).header.get_zooms()[:3], float)
    P = np.asarray(nib.load(f'{PRED}/{case}.nii.gz').dataobj).astype(np.uint8)
    ao = np.asarray(nib.load(f'{C.AORTA}/{case}_aorta.nii.gz').dataobj) > 0
    u = (L > 0) | (P > 0) | ao
    idx = [np.nonzero(u.any(axis=tuple(j for j in range(3) if j != k)))[0] for k in range(3)]
    mv = np.ceil(C.MARGIN_MM / sp).astype(int)
    lo = np.maximum([a[0] for a in idx] - mv, 0)
    hi = np.minimum([a[-1] + 1 for a in idx] + mv, L.shape)
    sl = tuple(slice(int(a), int(b)) for a, b in zip(lo, hi))
    R, P, ao = L[sl].copy(), P[sl].copy(), ao[sl].copy()
    del L
    rep = NEW.find_ostia(R, sp, aorta=ao)
    n = NEW.tree_f1(R, P, sp, ostia=rep)
    o = OLD.tree_f1(R, P, sp, ostia=rep)
    out = dict(case=case, identical=(n.per_class == o.per_class and n.recall == o.recall
                                     and n.precision == o.precision and n.tf1 == o.tf1),
               missing=n.classes_without_centreline, tf1=n.tf1,
               per_class={int(k): v for k, v in n.per_class.items()},
               flagged=[x.as_row() for x in rep.ostia if x.flagged])
    if n.classes_without_centreline:
        f = NEW.tree_f1(R, P, sp, ostia=rep, fallback_centreline=True)
        out['fallback'] = dict(tf1=f.tf1, per_class={int(k): v for k, v in f.per_class.items()})
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
