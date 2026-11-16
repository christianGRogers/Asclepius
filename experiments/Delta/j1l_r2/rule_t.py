"""Delta, Janus 1-L round 2: Rule T, the label-free transfer of t* from Janus 0 to the candidate C.

t* is chosen on Janus 0's probabilities for the tuning 60 (Rule W, L-A4). C (the ensemble E, or a1) trained on those
60 cases, and no labelled ImageCAS-X case is left outside the locked 100, so C's own best threshold cannot be measured
without a look. Rule T carries the *width* instead of the threshold, on cases neither model trained on and no rule
reads a label of:

  data   the drift set D60 (drift60.json: 60 unsealed, non-development ImageCAS quality-0 cases);
  ref    Janus 0 at t*: its skeleton S (frozen metric's skeletonize) and its local radius r0 = EDT(J0(t*)) on S;
  per t  over every point of S that C(t) also covers: dr(t) = EDT(C(t)) - r0, in mm; pooled over the 60 cases,
         10 %-trimmed mean;
  rule   t_C = the grid t <= 0.50 with the smallest |dr(t)|; ties within 0.005 mm go to t*, then to the larger t.
         Grid: 0.60, 0.55, 0.50, 0.45, 0.40, 0.35, 0.30, 0.25 (0.60 and 0.55 are reported, never chosen: the
         export lever only widens, as Rule W's does).
  scope  Rule T applies only when t* was chosen by Dice and not held back by Rule W's guards: Janus 0's tuning-60
         Dice at t* is within 0.002 of its best Dice over all five Rule W thresholds (select.json). Otherwise
         Janus 0 at t* is not the Dice-calibrated width, and t_C = t* (the ruling's frozen rule).
Only the shared centreline is compared, so extra extent or missed branches in either model do not move t_C (a plain
volume match would: transfer_phantom.py). t_C is frozen (its JSON's sha256 posted on #302) before any locked-100
number of C is computed.

Input: thresholded exports from Crucible's threshold_export.py (`<dir>/t<t>/<case>.nii.gz`), for Janus 0 (at least
t*) and for C (the whole grid), on D60. Any case outside D60 is refused, and so is a sealed case.

Usage:
  python rule_t.py --j0 $W/d60_j0 --cand $W/d60_C --select $JOB0/select.json --out $W/rule_t.json --np 8
  python rule_t.py --selftest
"""
import argparse
import hashlib
import json
import os
import sys
import tempfile
from multiprocessing import Pool

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
GRID = (0.60, 0.55, 0.50, 0.45, 0.40, 0.35, 0.30, 0.25)
TIE_MM = 0.005


def skeleton(mask):
    from skimage.morphology import skeletonize
    return skeletonize(mask.astype(bool)).astype(bool) if mask.any() else np.zeros(mask.shape, bool)


def case_diffs(m0, masks, sp):
    """m0: Janus 0 at t*; masks: {t: C(t)}. Returns {t: array of local radius differences on the shared skeleton}."""
    sk = skeleton(m0)
    r0 = ndimage.distance_transform_edt(m0, sampling=sp)
    out = {}
    for t, m in masks.items():
        shared = sk & m
        out[t] = (ndimage.distance_transform_edt(m, sampling=sp)[shared] - r0[shared]) if shared.any() else np.zeros(0)
    return out


def trimmed(x, g=0.10):
    if len(x) == 0:
        return float('nan')
    x = np.sort(x); k = int(round(g * len(x)))
    return float(x[k:len(x) - k].mean())


def choose(dr, tstar):
    finite = {t: v for t, v in dr.items() if np.isfinite(v) and t <= 0.50 + 1e-9}
    best = min(abs(v) for v in finite.values())
    cands = [t for t, v in finite.items() if abs(v) <= best + TIE_MM]
    return tstar if tstar in cands else max(cands)


def _one(job):
    import nibabel as nib
    c, j0dir, cdir, tstar = job
    img = nib.load(os.path.join(j0dir, f't{tstar:.2f}', c + '.nii.gz'))
    sp = np.array(img.header.get_zooms()[:3], float)
    m0 = np.asarray(img.dataobj) > 0
    masks = {t: np.asarray(nib.load(os.path.join(cdir, f't{t:.2f}', c + '.nii.gz')).dataobj) > 0 for t in GRID}
    d = case_diffs(m0, masks, sp)
    return c, {f'{t:.2f}': d[t].astype(np.float32) for t in GRID}, int(m0.sum())


def dice_bound(select_json, tstar):
    """True when t* is Rule W's Dice optimum, not a guard-limited choice (select.json from Crucible's decide.py)."""
    m = json.load(open(select_json))['per_threshold']
    best = max(v['dice'] for v in m.values())
    return m[f'{tstar:.2f}']['dice'] >= best - 0.002


def run(j0dir, cdir, tstar, cases, n_proc):
    with Pool(n_proc) as p:
        res = p.map(_one, [(c, j0dir, cdir, tstar) for c in cases], chunksize=1)
    pooled = {t: np.concatenate([r[1][f'{t:.2f}'] for r in res]) for t in GRID}
    dr = {t: trimmed(pooled[t]) for t in GRID}
    tC = choose(dr, tstar)
    return dict(rule='Delta v2 Rule T', t_star=tstar, t_C=tC, grid=list(GRID),
                dr_mm={f'{t:.2f}': round(v, 4) for t, v in dr.items()},
                n_shared_points={f'{t:.2f}': int(len(pooled[t])) for t in GRID},
                per_case_dr_at_tstar={r[0]: round(trimmed(r[1][f'{tstar:.2f}']), 4) for r in res},
                n_cases=len(res))


def check(cases):
    D = json.load(open(os.path.join(HERE, 'drift60.json')))
    S = json.load(open(os.path.join(ROOT, 'trillium', 'sealed_test.json')))
    bad = sorted(set(cases) - set(D['drift60'])) + sorted(set(cases) & (set(S['sealed_icx_test']) | set(S['sealed_quality0'])))
    if bad:
        sys.exit(f'[rule_t] REFUSING: cases outside D60 or sealed: {bad[:5]}')


def selftest():
    sp = np.array([0.5, 0.5, 0.5])
    z, y, x = np.indices((40, 40, 60)) * 0.5
    d = np.hypot(z - 10, y - 10)

    def tube(R, extra=False):
        m = (d <= R)
        if extra:
            m |= (np.hypot(z - 3, y - 15) <= 0.8)       # a branch only C draws
        return m
    m0 = tube(1.5)
    # C's radius at threshold t is 1.50 + 2.5 (0.50 - t) mm: 1.50 mm (= Janus 0 at t*) at t = 0.50, wider below
    # (C is already as wide at 0.50 as Janus 0 at t*). C also draws a branch Janus 0 does not. t_C must be 0.50
    # although t* = 0.40.
    masks = {t: tube(1.50 + 2.5 * (0.50 - t), extra=True) for t in GRID}
    dd = case_diffs(m0, masks, sp)
    dr = {t: trimmed(v) for t, v in dd.items()}
    assert abs(dr[0.50]) < 0.03, dr
    assert choose(dr, 0.40) == 0.50, (dr, choose(dr, 0.40))
    assert choose({t: 0.0 for t in GRID}, 0.40) == 0.40                # no drift: t* stays
    assert choose({t: 0.60 - t for t in GRID}, 0.40) == 0.50          # never thinner than argmax
    with tempfile.TemporaryDirectory() as W:
        sel = os.path.join(W, 'select.json')
        json.dump({'chosen_t': '0.45', 'per_threshold': {'0.50': {'dice': 0.88}, '0.45': {'dice': 0.89},
                                                          '0.40': {'dice': 0.91}}}, open(sel, 'w'))
        assert not dice_bound(sel, 0.45)                                # a guard held t* above the Dice optimum
        assert dice_bound(sel, 0.40)
    try:
        check(['c0000'])
        raise AssertionError('a non-D60 case was not refused')
    except SystemExit as e:
        assert 'REFUSING' in str(e)
    print('[rule_t] self-test passed: width carried on the shared centreline (extra branch ignored); '
          'no drift keeps t*; non-D60 refused')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--j0'); ap.add_argument('--cand'); ap.add_argument('--select', help="Job 0's select.json")
    ap.add_argument('--out'); ap.add_argument('--np', type=int, default=8)
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    cases = json.load(open(os.path.join(HERE, 'drift60.json')))['drift60']
    check(cases)
    tstar = round(float(json.load(open(a.select))['chosen_t']), 2)
    res = run(a.j0, a.cand, tstar, cases, a.np)
    res['select_sha256'] = hashlib.sha256(open(a.select, 'rb').read()).hexdigest()
    res['t_star_dice_bound'] = dice_bound(a.select, tstar)
    if not res['t_star_dice_bound']:
        res['t_C'] = tstar
        res['note'] = "t* was limited by Rule W's guards: Rule T does not apply; t_C = t*"
    res['drift60_sha256'] = json.load(open(os.path.join(HERE, 'drift60.json')))['drift60_sha256_sorted_newline']
    s = json.dumps(res, indent=1)
    open(a.out, 'w').write(s)
    print(s)
    print('sha256', hashlib.sha256(s.encode()).hexdigest())


if __name__ == '__main__':
    main()
