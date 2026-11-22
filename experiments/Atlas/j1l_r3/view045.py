"""Atlas, Janus 1-L round 3 (§5 item 3): does a 256^3 patch at 0.45 mm (115.2 mm) still see what a 0.5 mm one
(128 mm) sees, on the 620 D45 training cases?

S's 0.45 mm form keeps Janus 0's network and its 256^3 patch (the plans edit in Atlas v3 §3), so its field of view
shrinks from 128 mm to 115.2 mm. A four-class model names a branch from what one patch holds (round 1's
"A 128 mm patch at 0.5 mm holds the whole tree and the LM in almost every training patch"). This measures, per case,
on ImageCAS-X collapsed to four by `territory.to_four` (D25, D1, D1b):

  fits[P][s]     one P-mm box holds every voxel of structure s (LAD, left tree LM+LAD+LCx, right tree RCA, whole);
                 an axis on which the image is shorter than P always fits (nnU-Net pads);
  ctr[P][a->b]   nnU-Net's forced-foreground patch centred on a voxel of class a (lower corner clamped,
                 `nnUNetDataLoader.get_bbox`; rotation padding ignored) contains a voxel of class b; mean over a's
                 voxels. Pairs: LAD->LM, LAD->LCx, LCx->LM, RCA->LM (the naming evidence: the LM bifurcation);
  z_frac[P]      the share of the image height one inference window spans (256 slices x spacing / height).
Grid: 1 mm presence (max over voxels), so a box is placed to within 1 mm.

Pre-registered pass rule for the 0.45 mm form (written before this was first run; round 1's 128 mm values on 153
cases, less 0.02): over the 620, left tree fits in >= 0.98 of cases, right tree >= 0.97, and the mean LAD->LM and
LCx->LM forced-centre containments are >= 0.95 and >= 0.97. If any fails, S keeps 0.5 mm whatever Job 0 says.

Reads only the 620 (fetch_train620.py checks the pin and refuses sealed and locked ids again here).
Usage: python view045.py <icx620 dir> <out.json> [--np 8]
       python view045.py --selftest
"""
import json
import os
import sys
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'trillium', 'icx4', 'lib'))
sys.path.insert(0, HERE)

G = 1.0
PATCH_MM = {'0.50': 256 * 0.50, '0.45': 256 * 0.45}
PAIRS = (('LAD', 'LM'), ('LAD', 'LCx'), ('LCx', 'LM'), ('RCA', 'LM'))
CLS = {'LM': (1,), 'LAD': (2,), 'LCx': (3,), 'RCA': (4,)}
STRUCT = {'LAD': (2,), 'left': (1, 2, 3), 'right': (4,), 'whole': (1, 2, 3, 4)}
RULE = {'fits_left': 0.98, 'fits_right': 0.97, 'ctr_LAD->LM': 0.95, 'ctr_LCx->LM': 0.97}


def presence(lab, sp):
    """Max-pool the label to a G-mm grid. Returns (grid of max label per class bitmask, cell size mm)."""
    f = np.maximum(np.round(G / np.asarray(sp)).astype(int), 1)
    sh = [int(np.ceil(s / k)) * k for s, k in zip(lab.shape, f)]
    out = {}
    for c in (1, 2, 3, 4):
        p = np.zeros(sh, bool)
        p[:lab.shape[0], :lab.shape[1], :lab.shape[2]] = lab == c
        out[c] = p.reshape(sh[0] // f[0], f[0], sh[1] // f[1], f[1], sh[2] // f[2], f[2]).any((1, 3, 5))
    return out, f * np.asarray(sp, float)


def integral(a):
    return np.pad(a.astype(np.int32), [(1, 0)] * 3).cumsum(0).cumsum(1).cumsum(2)


def boxsum(I, lo, hi):
    """Sum over boxes [lo, hi) (arrays (n, 3), already clipped to the grid) of the array behind integral I."""
    x0, y0, z0 = lo.T
    x1, y1, z1 = hi.T
    return (I[x1, y1, z1] - I[x0, y1, z1] - I[x1, y0, z1] - I[x1, y1, z0]
            + I[x0, y0, z1] + I[x0, y1, z0] + I[x1, y0, z0] - I[x0, y0, z0])


def measure(lab, sp):
    sp = np.asarray(sp, float)
    img_mm = np.asarray(lab.shape) * sp
    pres, cell = presence(lab, sp)
    shape = np.asarray(pres[1].shape)
    row = {'img_mm': img_mm.round(1).tolist(), 'fits': {}, 'ctr': {}, 'z_frac': {}, 'extent_mm': {}}
    for s, cs in STRUCT.items():
        m = np.isin(lab, cs)
        if not m.any():
            row['extent_mm'][s] = None
            continue
        idx = [np.nonzero(m.any(axis=tuple(j for j in range(3) if j != k)))[0] for k in range(3)]
        row['extent_mm'][s] = [round(float((a[-1] - a[0] + 1) * sp[k]), 1) for k, a in enumerate(idx)]
    for key, P in PATCH_MM.items():
        row['fits'][key] = {}
        for s in STRUCT:
            e = row['extent_mm'][s]
            row['fits'][key][s] = None if e is None else bool(all(ek <= P or im <= P for ek, im in zip(e, img_mm)))
        k = np.maximum(np.floor(P / cell).astype(int), 1)
        lbs = -np.maximum(k - shape, 0) // 2                    # nnU-Net pads an axis shorter than the patch
        row['ctr'][key] = {}
        for a, b in PAIRS:
            va = np.argwhere(np.any([pres[c] for c in CLS[a]], axis=0))
            pb = np.any([pres[c] for c in CLS[b]], axis=0)
            if len(va) == 0 or not pb.any():
                row['ctr'][key][f'{a}->{b}'] = None
                continue
            lo = np.maximum(lbs, va - k // 2)
            hi = np.clip(lo + k, 0, shape)
            lo = np.clip(lo, 0, shape)
            row['ctr'][key][f'{a}->{b}'] = float((boxsum(integral(pb), lo, hi) > 0).mean())
        row['z_frac'][key] = round(float(min(1.0, P / img_mm[2])), 3)
    return row


def one(path):
    import nibabel as nib
    from territory import to_four
    img = nib.load(path)
    sp = img.header.get_zooms()[:3]
    lab = to_four(np.asarray(img.dataobj).astype(np.int64), sp).astype(np.uint8)
    case = 'c%04d' % (int(os.path.basename(path).split('.')[0]) - 1)
    return dict(case=case, spacing=[float(x) for x in sp], **measure(lab, sp))


def summarise(rows):
    out = {'n': len(rows)}
    for key in PATCH_MM:
        s = {'patch_mm': PATCH_MM[key]}
        for st in STRUCT:
            v = [r['fits'][key][st] for r in rows if r['fits'][key][st] is not None]
            s[f'fits_{st}'] = round(float(np.mean(v)), 4)
        for a, b in PAIRS:
            v = [r['ctr'][key][f'{a}->{b}'] for r in rows if r['ctr'][key][f'{a}->{b}'] is not None]
            s[f'ctr_{a}->{b}'] = round(float(np.mean(v)), 4)
            s[f'ctr_{a}->{b}_p05'] = round(float(np.percentile(v, 5)), 4)
        s['z_frac_min'] = min(r['z_frac'][key] for r in rows)
        s['z_frac_median'] = float(np.median([r['z_frac'][key] for r in rows]))
        out[key] = s
    for st in ('whole', 'left'):
        e = np.array([r['extent_mm'][st] for r in rows if r['extent_mm'][st] is not None])
        out[f'extent_{st}_mm'] = {'median': np.median(e, 0).round(1).tolist(), 'p90': np.percentile(e, 90, 0).round(1).tolist(),
                                  'max': e.max(0).round(1).tolist()}
    drop = [r['case'] for r in rows if r['ctr']['0.45']['LAD->LM'] is not None and
            r['ctr']['0.50']['LAD->LM'] - r['ctr']['0.45']['LAD->LM'] > 0.05]
    out['n_cases_LAD->LM_drop_gt_0.05'] = len(drop)
    q = out['0.45']
    out['rule'] = RULE
    out['rule_passes'] = {k: bool(q[k] >= v) for k, v in RULE.items()}
    out['view_check_passes'] = all(out['rule_passes'].values())
    return out


def selftest():
    sp = (0.5, 0.5, 0.5)
    lab = np.zeros((300, 300, 300), np.uint8)
    lab[100:110, 100:110, 100:110] = 1                    # LM
    lab[110:110 + 200, 105, 105] = 2                      # LAD 100 mm long: fits 115.2 and 128
    lab[100:110, 110:280, 105] = 3                        # LCx 85 mm
    lab[20:30, 20:30, 250:290] = 4                        # RCA far away
    r = measure(lab, sp)
    assert r['fits']['0.50']['LAD'] and r['fits']['0.45']['LAD'], r['fits']
    assert not r['fits']['0.45']['whole'], r['extent_mm']
    # distal LAD voxels (> 57.6 mm from the LM) lose it first in the smaller box
    assert r['ctr']['0.50']['LAD->LM'] >= r['ctr']['0.45']['LAD->LM'] > 0.5, r['ctr']
    # boxsum agrees with brute force
    rng = np.random.default_rng(0)
    a = rng.random((9, 8, 7)) > 0.7
    I = integral(a)
    lo = np.array([[1, 2, 0], [0, 0, 0]]); hi = np.array([[5, 8, 4], [9, 8, 7]])
    bf = [a[l[0]:h[0], l[1]:h[1], l[2]:h[2]].sum() for l, h in zip(lo, hi)]
    assert (boxsum(I, lo, hi) == bf).all()
    from fetch_train620 import train620
    assert len(train620()) == 620
    print('[view045] self-test passed: fits, forced-centre containment, box sums, the 620 pin')


def main():
    if sys.argv[1:2] == ['--selftest']:
        return selftest()
    from fetch_train620 import train620
    d, out = sys.argv[1], sys.argv[2]
    n = int(sys.argv[sys.argv.index('--np') + 1]) if '--np' in sys.argv else 8
    want = {f'{int(c[1:]) + 1}.coronary.nii.gz' for c in train620()}
    files = sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith('.coronary.nii.gz'))
    if {os.path.basename(f) for f in files} - want:
        sys.exit('[view045] REFUSING: a file outside the 620')
    with Pool(n) as p:
        rows = p.map(one, files, chunksize=4)
    res = {'summary': summarise(rows), 'rows': rows}
    json.dump(res, open(out, 'w'), indent=1)
    print(json.dumps(res['summary'], indent=1))


if __name__ == '__main__':
    main()
