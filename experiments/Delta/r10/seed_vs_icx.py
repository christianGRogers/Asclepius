"""Delta, Round 10: how far the D23 seed (TotalSegmentator `coronary_arteries`, binary) departs from ImageCAS-X's
extent, measured on the val 80 before any team read exists. This calibrates A31.2 (seed anchoring, L5): if reads
keep the seed's extent, A10 on the pool measures agreement with this seed, not with ImageCAS-X.

The seed is named with the reference's own classes (each seed voxel takes the class of the nearest ImageCAS-X voxel,
in mm), as Bridge's wave-1 seed comparison names it with a read's classes. Seed components with no voxel within 2 mm
of the reference are dropped and counted, since a reader deletes those whole. Then, per class, with ImageCAS-X as
the reference and the A1 ostium (TotalSegmentator aorta):
  recall    the share of ImageCAS-X's centreline the seed reaches (extent short of ImageCAS-X shows here);
  precision the share of the seed's centreline on ImageCAS-X (extent beyond it shows here);
  tF1, and seed-vs-Janus-0 if --pred is given (what an anchored read would cost Janus 0, from the seed alone).
tF1 is the pinned segtrain.tf1 (A1c). Val only; sealed cases refused.

Usage on Fir, after the seeds exist (see the plan, Fir job S):
  python experiments/Delta/r10/seed_vs_icx.py --seeds $SCRATCH/seedcal/seeds --icx $SCRATCH/icx4/icx \
      --aorta $SCRATCH/icx4/aorta --splits $SCRATCH/icx4/splits.json --pred $SCRATCH/icx4/predictions \
      --out $SCRATCH/seedcal/seed_vs_icx.json --np 10
  python experiments/Delta/r10/seed_vs_icx.py --selftest"""
import argparse
import hashlib
import json
import os
import sys
from multiprocessing import Pool

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'src'))
sys.path.insert(0, os.path.join(REPO, 'trillium', 'icx4', 'lib'))
PIN = '24441cf8df0f000bd956c7dd9d8ae1daac866cfb14df1d174441d00e54f05254'
NAMES = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA'}
KEEP_MM = 2.0
MARGIN_MM = 8.0
A = None


def name_seed(seed, ref, sp):
    """Seed voxels take the nearest reference class; components > KEEP_MM from the reference are dropped."""
    out = np.zeros(ref.shape, np.uint8)
    if not seed.any() or not (ref > 0).any():
        return out, 0
    d_ref = ndimage.distance_transform_edt(ref == 0, sampling=sp)
    lab, n = ndimage.label(seed, structure=np.ones((3, 3, 3)))
    keep = np.zeros(n + 1, bool)
    mins = ndimage.minimum(d_ref, lab, index=np.arange(1, n + 1)) if n else []
    keep[1:] = np.asarray(mins) <= KEEP_MM
    s = keep[lab] & seed
    rp = np.argwhere(ref > 0)
    sv = np.argwhere(s)
    _, i = cKDTree(rp * sp).query(sv * sp)
    out[tuple(sv.T)] = ref[tuple(rp[i].T)]
    return out, int(n - keep[1:].sum())


def score_arrays(ref, seed, sp, aorta, pred=None):
    from segtrain import tf1 as T
    named, dropped = name_seed(seed > 0, ref, sp)
    rep = T.find_ostia(ref, sp, aorta=aorta)
    t = T.tree_f1(ref, named, sp, ostia=rep)
    row = dict(dropped_components=dropped, provisional=bool(rep.provisional), flagged=bool(rep.flagged),
               tf1={NAMES[c]: float(v) for c, v in t.per_class.items()},
               recall={NAMES[c]: float(v) for c, v in t.recall.items()},
               precision={NAMES[c]: float(v) for c, v in t.precision.items()},
               seed_volume_ratio=float((named > 0).sum() / max((ref > 0).sum(), 1)))
    if pred is not None and (named > 0).any():
        rs = T.find_ostia(named, sp, aorta=aorta)      # the anchored read's own ostium, as A10 would place it
        tp = T.tree_f1(named, pred, sp, ostia=rs)
        row['janus0_vs_seed_tf1'] = {NAMES[c]: float(v) for c, v in tp.per_class.items()}
        tr = T.tree_f1(ref, pred, sp, ostia=rep)
        row['janus0_vs_icx_tf1'] = {NAMES[c]: float(v) for c, v in tr.per_class.items()}
    return row


def one(c):
    import nibabel as nib
    from territory import to_four
    try:
        i = int(c[1:]) + 1
        li = nib.load(os.path.join(A.icx, f'{i}.coronary.nii.gz'))
        sp = np.asarray(li.header.get_zooms()[:3], float)
        ref = to_four(np.asarray(li.dataobj).astype(np.int64), sp).astype(np.uint8)
        si = nib.load(os.path.join(A.seeds, f'{c}.nii.gz'))
        seed = np.asarray(si.dataobj) > 0
        if seed.shape != ref.shape or not np.allclose(si.affine, li.affine, atol=1e-3):
            return dict(case=c, error=f'seed grid {seed.shape} vs {ref.shape}')
        aorta = np.asarray(nib.load(os.path.join(A.aorta, f'{c}_aorta.nii.gz')).dataobj) > 0
        pred = None
        if A.pred:
            pred = np.asarray(nib.load(os.path.join(A.pred, f'{c}.nii.gz')).dataobj).astype(np.uint8)
        u = (ref > 0) | seed
        nz = np.argwhere(u)
        mv = np.ceil(MARGIN_MM / sp).astype(int)
        sl = tuple(slice(max(a - m, 0), min(b + 1 + m, s)) for a, b, m, s in zip(nz.min(0), nz.max(0), mv, ref.shape))
        return dict(case=c, **score_arrays(ref[sl], seed[sl], sp, aorta[sl], None if pred is None else pred[sl]))
    except Exception as e:  # noqa: BLE001
        return dict(case=c, error=repr(e)[:300])


def summarise(rows):
    ok = [r for r in rows if 'error' not in r and not r.get('provisional')]
    s = dict(n=len(rows), n_scored=len(ok), errors=[r for r in rows if 'error' in r][:5])
    for key in ('tf1', 'recall', 'precision', 'janus0_vs_seed_tf1', 'janus0_vs_icx_tf1'):
        s[key] = {NAMES[c]: round(float(np.mean(v)), 4) if (v := [r[key][NAMES[c]] for r in ok
                                                                   if key in r and NAMES[c] in r[key]]) else None
                  for c in NAMES}
    s['seed_volume_ratio_median'] = round(float(np.median([r['seed_volume_ratio'] for r in ok])), 3) if ok else None
    s['dropped_components_mean'] = round(float(np.mean([r['dropped_components'] for r in ok])), 2) if ok else None
    return s


def selftest():
    sp = np.array([0.5, 0.5, 0.5])
    ref = np.zeros((40, 140, 40), np.uint8)
    zz, yy, xx = np.mgrid[:40, :140, :40]
    r2 = (zz - 20) ** 2 + (xx - 20) ** 2
    ref[(r2 <= 9) & (yy >= 20) & (yy < 40)] = 1
    ref[(r2 <= 9) & (yy >= 40) & (yy < 130)] = 2
    aorta = np.zeros_like(ref, bool)
    aorta[5:35, 0:17, 5:35] = True
    full = score_arrays(ref, ref > 0, sp, aorta, pred=ref)
    assert abs(full['tf1']['LAD'] - 1.0) < 1e-6 and full['dropped_components'] == 0, full
    short = (ref > 0) & (yy < 110)                      # the seed stops 10 mm short of the LAD's end
    vein = np.zeros_like(short)
    vein[5:8, 60:80, 35:38] = True                      # a component > 2 mm away: dropped
    r = score_arrays(ref, short | vein, sp, aorta, pred=ref)
    assert r['dropped_components'] == 1, r
    assert r['recall']['LAD'] < 0.85 and r['precision']['LAD'] > 0.99, r
    assert r['janus0_vs_seed_tf1']['LAD'] < r['janus0_vs_icx_tf1']['LAD'], r
    print('[seed_vs_icx] self-test passed:', json.dumps({k: r[k] for k in ('recall', 'precision', 'janus0_vs_seed_tf1')}))


def main():
    global A
    ap = argparse.ArgumentParser()
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--seeds'); ap.add_argument('--icx'); ap.add_argument('--aorta'); ap.add_argument('--splits')
    ap.add_argument('--pred'); ap.add_argument('--out'); ap.add_argument('--np', type=int, default=8)
    A = ap.parse_args()
    h = hashlib.sha256(open(os.path.join(REPO, 'src/segtrain/tf1.py'), 'rb').read()).hexdigest()
    if h != PIN:
        sys.exit(f'tf1.py sha256 {h} is not the A1c pin')
    if A.selftest:
        return selftest()
    S = json.load(open(os.path.join(REPO, 'trillium/sealed_test.json')))
    sealed = set(S['sealed_icx_test']) | set(S['sealed_quality0'])
    val = json.load(open(A.splits))['val']
    if set(val) & sealed:
        sys.exit('sealed case in val: refusing')
    with Pool(A.np) as p:
        rows = p.map(one, sorted(val))
    res = dict(tf1_sha256=h, summary=summarise(rows), rows=rows)
    json.dump(res, open(A.out, 'w'), indent=1)
    print(json.dumps(res['summary'], indent=1))


if __name__ == '__main__':
    main()
