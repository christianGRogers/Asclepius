"""Atlas, Janus 1-L round 3: the tuning-60 volume ratio that L-A23's grid-trigger row reads.

L-A23: "Dice at t* more than 0.03 below 0.934, with volume ratio >= 0.95 -> the grid binds; the 0.45 mm form of S".
Job 0 writes Dice per threshold (`select.json`) but no volume ratio: the scorer's rows carry none, and
`threshold_export.py`'s `voxels.json` has the predicted counts only. This computes, per threshold, the whole-tree
volume ratio sum(pred > 0) / sum(ref > 0) per case (ImageCAS-X collapsed by `territory.to_four`) and its mean and
median over the tuning 60, and applies the row. CPU, about 10 min with --np 4. Counts only are printed.

Refuses every case outside the tuning 60.
Usage: python vol60.py --thr $W/thr --icx $J0/icx --select $W/select.json --np 4 --out $W/scores/vol60.json
       python vol60.py --selftest
"""
import argparse
import json
import os
import sys
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'trillium', 'icx4', 'lib'))
GRID = ('0.50', '0.45', '0.40', '0.35', '0.30')
DICE_CEIL, DICE_GAP, VOL_MIN = 0.934, 0.03, 0.95


def tuning60():
    L = json.load(open(os.path.join(ROOT, 'experiments', 'Crucible', 'j1l_r1', 'lists.json')))
    S = json.load(open(os.path.join(ROOT, 'trillium', 'sealed_test.json')))
    t = sorted(L['tuning60'])
    assert len(t) == 60 and not set(t) & (set(L['locked100']) | set(S['sealed_icx_test']) | set(S['sealed_quality0']))
    return t


def one(job):
    import nibabel as nib
    from territory import to_four
    c, thr, icx = job
    li = nib.load(os.path.join(icx, f'{int(c[1:]) + 1}.coronary.nii.gz'))
    ref = int((to_four(np.asarray(li.dataobj).astype(np.int64), li.header.get_zooms()[:3]) > 0).sum())
    out = {'case': c}
    for t in GRID:
        p = os.path.join(thr, f't{t}', c + '.nii.gz')
        out[t] = int((np.asarray(nib.load(p).dataobj) > 0).sum()) / ref if os.path.exists(p) and ref else None
    return out


def row_applies(select, vol):
    """L-A23's grid row: Dice at t* < 0.934 - 0.03 and mean volume ratio at t* >= 0.95."""
    t = '%.2f' % float(select['chosen_t'])
    d = select['per_threshold'][t]['dice']
    return dict(t_star=t, dice_t_star=round(d, 4), vol_ratio_t_star=vol[t]['mean'],
                grid_binds=bool(d < DICE_CEIL - DICE_GAP and vol[t]['mean'] >= VOL_MIN))


def summarise(rows):
    return {t: dict(mean=round(float(np.mean(v)), 4), median=round(float(np.median(v)), 4), n=len(v))
            for t in GRID if (v := [r[t] for r in rows if r[t] is not None])}


def selftest():
    rows = [{'case': 'a', '0.50': 0.87, '0.45': 0.93, '0.40': 0.97, '0.35': 1.0, '0.30': 1.03}] * 3
    vol = summarise(rows)
    sel = {'chosen_t': '0.40', 'per_threshold': {'0.40': {'dice': 0.90}}}
    assert row_applies(sel, vol)['grid_binds']
    sel = {'chosen_t': '0.40', 'per_threshold': {'0.40': {'dice': 0.91}}}
    assert not row_applies(sel, vol)['grid_binds']
    sel = {'chosen_t': '0.45', 'per_threshold': {'0.45': {'dice': 0.89}}}
    assert not row_applies(sel, vol)['grid_binds']                       # volume 0.93 < 0.95
    assert len(tuning60()) == 60
    print('[vol60] self-test passed: the L-A23 grid row on fixtures; the tuning-60 list')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--thr'); ap.add_argument('--icx'); ap.add_argument('--select'); ap.add_argument('--out')
    ap.add_argument('--np', type=int, default=4)
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    with Pool(a.np) as p:
        rows = p.map(one, [(c, a.thr, a.icx) for c in tuning60()], chunksize=1)
    vol = summarise(rows)
    res = dict(volume_ratio=vol, L_A23_grid_row=row_applies(json.load(open(a.select)), vol))
    json.dump(res, open(a.out, 'w'), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
