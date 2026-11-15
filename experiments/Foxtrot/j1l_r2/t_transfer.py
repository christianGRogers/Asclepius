"""Foxtrot, track 1-L round 2: does Janus 0's export threshold t* transfer to a Janus 1-L network? A label-free check
and a pre-registered switch (Foxtrot v2 section 3; Judgement Round 1 section 5, item 3).

Rule W chose t* on Janus 0's probabilities for the tuning 60, which Janus 1-L then trains on. No labelled ImageCAS-X
case is left outside the locked 100, so the transfer cannot be checked against labels before the one look. It can be
checked without labels: on images that no model trained on, compare how much foreground each network draws.

The 60 images are results/calib60.json (calib_cases.py): open ImageCAS quality-0 cases, never labelled for this
project, never trained on, not sealed, not in the 620 or the locked 100. **No label is read.**

For each case, f = summed vessel probability (1 - p_background), and V(t) = the number of voxels with f >= t.
  * Target: Janus 0's foreground at t*, V_J0(t*), per case. That is the width Rule W found best on the tuning 60.
  * t_C: the t in {0.30, 0.35, 0.40, 0.45, 0.50} (Rule W's grid) whose median over cases of V_C(t) / V_J0(t*) is
    closest to 1 (to 3 decimals); ties to the t nearest t*, then to the larger t.
  * Shift: s = median V_C(t*) / V_J0(t*). s < 1: the candidate draws less at t* than Janus 0 (sharper or thinner);
    s > 1: more.
  * **Switch (pre-registered): the candidate is exported at t_C if |t_C - t*| >= 0.10 (two grid steps); otherwise at
    t*.** The choice is written (`transfer.json`, its sha256 posted on #302) before any locked-100 number of that
    candidate is computed.

Lead's commands: in Foxtrot v2 section 5 (Job 0b for Janus 0; the E job for the candidate). Inputs are nnU-Net v2
`--save_probabilities` folders (`<case>.npz`, key `probabilities`, shape (5, ...)); only volumes are kept, so the
probability files can be deleted after `volumes`.
  python t_transfer.py volumes --probs DIR --out vol_<model>.json [--np 4]
  python t_transfer.py decide --vol-j0 vol_janus0.json --vol vol_<model>.json --tstar 0.40 --out transfer_<model>.json
Self-test (synthetic tubes):  python t_transfer.py --selftest
"""
import argparse
import hashlib
import json
import os
import sys
import tempfile
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
GRID = (0.30, 0.35, 0.40, 0.45, 0.50)
FINE = tuple(round(x, 3) for x in np.arange(0.20, 0.6001, 0.025))
SWITCH = 0.10


def calib60():
    c = json.load(open(os.path.join(HERE, 'results', 'calib60.json')))['calib60']
    S = json.load(open(os.path.join(ROOT, 'trillium', 'sealed_test.json')))
    assert len(c) == 60 and not set(c) & (set(S['sealed_icx_test']) | set(S['sealed_quality0']))
    return c


def volumes(path):
    """V(t) for every t in FINE (and GRID), from one probabilities file."""
    p = np.load(path)['probabilities']
    f = 1.0 - p[0].astype(np.float32)
    return {f'{t:.3f}': int((f >= t - 1e-6).sum()) for t in sorted(set(FINE) | set(GRID))}


def _vols(args):
    case, d = args
    path = os.path.join(d, f'{case}.npz')
    return case, (volumes(path) if os.path.exists(path) else None)


def decide(v0, vc, tstar):
    """v0, vc: {case: {t: V}}. Returns the transfer record."""
    cases = sorted(c for c in v0 if v0[c] and vc.get(c) and v0[c][f'{tstar:.3f}'] > 0)
    key = f'{tstar:.3f}'
    ratio = {t: float(np.median([vc[c][f'{t:.3f}'] / v0[c][key] for c in cases])) for t in sorted(set(FINE) | set(GRID))}
    best = min(GRID, key=lambda t: (round(abs(ratio[t] - 1.0), 3), abs(t - tstar), -t))
    s = ratio[tstar]
    use = best if abs(best - tstar) >= SWITCH - 1e-9 else tstar
    return {'n_cases': len(cases), 't_star': tstar, 'shift_s_median_ratio_at_tstar': round(s, 4),
            't_C_volume_matched': best, 'switch_rule': f'|t_C - t*| >= {SWITCH}', 'export_t': use,
            'switched': use != tstar, 'median_ratio_by_t': {f'{t:.3f}': round(r, 4) for t, r in ratio.items()},
            'janus0_vs_itself_at_0.5': None}


def volume_table(d, cases, n_proc):
    with Pool(n_proc) as p:
        return dict(p.map(_vols, [(c, d) for c in cases], chunksize=1))


def decide_tables(v0, vc, tstar, cases):
    missing = sorted(c for c in cases if not v0.get(c) or not vc.get(c))
    res = decide(v0, vc, tstar)
    key = f'{tstar:.3f}'
    res['janus0_vs_itself_at_0.5'] = round(float(np.median([v0[c]['0.500'] / v0[c][key] for c in cases
                                                            if v0.get(c) and v0[c][key]])), 4)
    res['missing'] = missing
    return res


def run(d0, dc, tstar, cases, n_proc):
    v0, vc = volume_table(d0, cases, n_proc), volume_table(dc, cases, n_proc)
    return decide_tables(v0, vc, tstar, cases), v0, vc


def selftest():
    shape = (20, 64, 64)
    g = np.indices(shape).astype(np.float32)
    d = np.sqrt((g[1] - 32) ** 2 + (g[2] - 32) ** 2) / 4.0     # sub-voxel radius units

    def tube(r0, w):
        f = 1 / (1 + np.exp(-(r0 - d) / w))
        p = np.zeros((5,) + shape, np.float32)
        p[0] = 1 - f
        p[2] = f
        return p
    with tempfile.TemporaryDirectory() as W:
        dirs = {}
        for name, (r0, w) in {'j0': (3.0, 1.0), 'same': (3.0, 1.0), 'wider': (4.0, 1.0),
                              'sharper': (3.0, 0.3)}.items():
            dirs[name] = os.path.join(W, name)
            os.makedirs(dirs[name])
            for c in ('c9001', 'c9002', 'c9003'):
                np.savez_compressed(os.path.join(dirs[name], f'{c}.npz'), probabilities=tube(r0, w))
        cases = ['c9001', 'c9002', 'c9003']
        same = run(dirs['j0'], dirs['same'], 0.40, cases, 2)[0]
        wider = run(dirs['j0'], dirs['wider'], 0.40, cases, 2)[0]
        sharp = run(dirs['j0'], dirs['sharper'], 0.40, cases, 2)[0]
    assert same['t_C_volume_matched'] == 0.40 and not same['switched'] and abs(same['shift_s_median_ratio_at_tstar'] - 1) < 1e-9
    assert wider['shift_s_median_ratio_at_tstar'] > 1 and wider['t_C_volume_matched'] == 0.50 and wider['switched']
    assert sharp['shift_s_median_ratio_at_tstar'] < 1 and sharp['t_C_volume_matched'] == 0.30 and sharp['switched']
    c = calib60()
    print('[transfer] self-test passed: identical network keeps t* 0.40; a wider one ->', wider['export_t'],
          f"(s = {wider['shift_s_median_ratio_at_tstar']}); a sharper one ->", sharp['export_t'],
          f"(s = {sharp['shift_s_median_ratio_at_tstar']}); calib60 has {len(c)} cases, none sealed")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', nargs='?', choices=('volumes', 'decide'))
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--probs', help='volumes: a --save_probabilities folder for the calib60')
    ap.add_argument('--vol-j0'); ap.add_argument('--vol', help='decide: the candidate volume table')
    ap.add_argument('--tstar', type=float); ap.add_argument('--out'); ap.add_argument('--np', type=int, default=4)
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    cases = calib60()
    if a.mode == 'volumes':
        v = volume_table(a.probs, cases, a.np)
        miss = sorted(c for c in cases if v[c] is None)
        json.dump({'probs': a.probs, 'missing': miss, 'volumes': v}, open(a.out, 'w'), indent=1, sort_keys=True)
        print(f'[transfer] volumes of {len(cases) - len(miss)} of {len(cases)} calib60 cases -> {a.out}; missing {miss}')
        return
    if round(a.tstar, 3) not in GRID:
        sys.exit(f'[transfer] t* {a.tstar} is not on Rule W grid {GRID}')
    v0 = json.load(open(a.vol_j0))['volumes']
    vc = json.load(open(a.vol))['volumes']
    res = decide_tables(v0, vc, round(a.tstar, 2), cases)
    res.update(vol_j0=a.vol_j0, vol=a.vol)
    blob = json.dumps(res, indent=1, sort_keys=True)
    open(a.out, 'w').write(blob)
    print(blob)
    print('sha256', hashlib.sha256(blob.encode()).hexdigest(), a.out)


if __name__ == '__main__':
    main()
