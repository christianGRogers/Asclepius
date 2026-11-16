"""Atlas, Janus 1-L round 2 (#302, Round-1 ruling §5 item 3): Rule T, a label-free check of t* transfer.

t* is chosen on Janus 0's probabilities (Rule W, L-A4). The fine-tune a1 may come out sharper or softer at the
lumen rim, and then the same t* moves its boundary by a different amount. No ImageCAS-X case outside the locked 100
is left to measure this with labels, so Rule T measures it **without labels**, on cases that are in no decision set:

  * U40: 40 of the 180 ImageCAS cases that ImageCAS-X does not label and that are not sealed (the 200 unlabelled
    ImageCAS cases of D22 minus the 20 sealed quality-0). They are in neither the train 620, the locked 100, the
    sealed ImageCAS-X 80, the pool seal (no ImageCAS volume is in the pool list) nor D35. Chosen by the smallest
    sha256('asclepius-j1l-transfer:' + id). No label of them is read: only each model's own probabilities.
  * Inflation curve of a model M:  r_M(t) = sum over U40 of vol_M(t) / sum over U40 of vol_M(0.50), where vol_M(t) is
    the number of voxels whose summed vessel probability (1 - p_background) is >= t. It is how much a threshold
    widens M's tree relative to M's own argmax-like export, and it does not depend on M's extent.
  * The rule: target = r_J0(t*). t_T = the grid t in {0.50, 0.45, 0.40, 0.35, 0.30} whose r_a1(t) is closest to the
    target (ties to the larger t). If a1's own vol(0.50) already reaches Janus 0's vol(t*) on U40, t_T = 0.50
    (a1 has learned the width itself). If t* = 0.50, t_T = 0.50.
  * t_T is written to transfer.json, whose sha256 is posted on #302 before the locked 100 is scored. The candidate
    is a1 at t_T (Atlas v2 §3). When nothing shifted, t_T = t*.

Usage (Trillium, after a1 and Janus 0 have predicted U40 with --save_probabilities; CPU, a few minutes):
  python r2_transfer.py u40 > u40.json                                  # the case list (also printed with its pin)
  python r2_transfer.py curve --probs DIR_J0 --cases u40.json > curve_janus0.json
  python r2_transfer.py curve --probs DIR_A1 --cases u40.json > curve_a1.json
  python r2_transfer.py rule --j0 curve_janus0.json --a1 curve_a1.json --tstar 0.40 > transfer.json
  python r2_transfer.py --selftest
"""
import hashlib
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
GRID = ('0.50', '0.45', '0.40', '0.35', '0.30')
SALT = 'asclepius-j1l-transfer:'


def u40(lists_json=None, sealed_json=None):
    L = json.load(open(lists_json or os.path.join(ROOT, 'experiments', 'Crucible', 'j1l_r1', 'lists.json')))
    S = json.load(open(sealed_json or os.path.join(ROOT, 'trillium', 'sealed_test.json')))
    labelled = set(L['train620']) | set(L['locked100']) | set(S['sealed_icx_test'])
    assert len(labelled) == 800, len(labelled)
    pool = sorted({f'c{i:04d}' for i in range(1000)} - labelled - set(S['sealed_quality0']))
    assert len(pool) == 180, len(pool)
    pick = sorted(sorted(pool, key=lambda c: hashlib.sha256((SALT + c).encode()).hexdigest())[:40])
    return pool, pick


def pin(ids):
    return hashlib.sha256('\n'.join(sorted(ids)).encode()).hexdigest()


def refuse(ids):
    pool, _ = u40()
    bad = sorted(set(ids) - set(pool))
    if bad:
        sys.exit(f'[transfer] REFUSING: not in the unlabelled, unsealed 180: {bad[:5]}')


def vessel_prob(npz_path):
    p = np.load(npz_path)['probabilities']            # nnU-Net: (classes, ...) with class 0 = background
    return 1.0 - p[0].astype(np.float32)


def curve(prob_dir, cases):
    refuse(cases)
    vol = {t: 0 for t in GRID}
    for c in cases:
        v = vessel_prob(os.path.join(prob_dir, f'{c}.npz'))
        for t in GRID:
            vol[t] += int((v >= float(t)).sum())
    return {'n': len(cases), 'cases_sha256': pin(cases), 'vol': vol,
            'r': {t: vol[t] / vol['0.50'] if vol['0.50'] else None for t in GRID}}


def rule(j0, a1, tstar):
    tstar = f'{float(tstar):.2f}'
    assert j0['cases_sha256'] == a1['cases_sha256'], 'the two curves are not on the same cases'
    target = j0['r'][tstar]
    if tstar == '0.50':
        t, why = '0.50', 't* = 0.50: nothing to transfer'
    elif a1['vol']['0.50'] >= j0['vol'][tstar]:
        t, why = '0.50', "a1's own export already reaches Janus 0's volume at t*"
    else:
        best = min(abs(a1['r'][g] - target) for g in GRID)
        t = max((g for g in GRID if abs(a1['r'][g] - target) <= best + 1e-12), key=float)
        why = 'closest inflation to Janus 0 at t*'
    return {'rule': 'Atlas v2 section 3.3 (Rule T)', 't_star': tstar, 'target_r': target,
            'r_janus0': j0['r'], 'r_a1': a1['r'], 't_T': t, 'shifted': t != tstar, 'why': why}


def selftest():
    import tempfile
    pool, pick = u40()
    assert len(pick) == 40 and set(pick) <= set(pool)
    L = json.load(open(os.path.join(ROOT, 'experiments', 'Crucible', 'j1l_r1', 'lists.json')))
    try:
        refuse(pick[:3] + L['locked100'][:1])
        raise AssertionError('locked id not refused')
    except SystemExit as e:
        assert 'REFUSING' in str(e)
    # a tube whose rim probability falls linearly from 0.6 to 0.2: a sharper model has the same profile squeezed
    g = np.indices((40, 40, 20)).astype(float)
    d = np.sqrt((g[0] - 20) ** 2 + (g[1] - 20) ** 2)

    def model(scale):
        v = np.clip(0.95 - (d - 4) * 0.12 * scale, 0, 0.95) * (d < 12)
        return np.stack([1 - v, v])
    with tempfile.TemporaryDirectory() as W:
        for name, s in (('j0', 1.0), ('same', 1.0), ('sharp', 2.0)):
            os.makedirs(f'{W}/{name}')
            for c in pick[:3]:
                np.savez_compressed(f'{W}/{name}/{c}.npz', probabilities=model(s).astype(np.float16))
        cj = curve(f'{W}/j0', pick[:3])
        same = rule(cj, curve(f'{W}/same', pick[:3]), 0.40)
        sharp = rule(cj, curve(f'{W}/sharp', pick[:3]), 0.40)
        assert same['t_T'] == '0.40' and not same['shifted'], same
        assert float(sharp['t_T']) < 0.40, sharp           # a sharper rim needs a lower t for the same widening
        assert rule(cj, cj, 0.50)['t_T'] == '0.50'
    print(f'[transfer] self-test passed: U40 pin {pin(pick)[:12]}…; same calibration keeps t*; '
          f'a sharper rim moves t* {sharp["t_star"]} -> {sharp["t_T"]}; locked ids refused')


def main(a):
    if a[:1] == ['--selftest']:
        return selftest()
    if a[:1] == ['u40']:
        pool, pick = u40()
        return print(json.dumps({'salt': SALT, 'from_n': len(pool), 'from_sha256': pin(pool),
                                 'u40': pick, 'u40_sha256': pin(pick)}, indent=1))
    if a[:1] == ['curve']:
        cases = json.load(open(a[a.index('--cases') + 1]))['u40']
        return print(json.dumps(curve(a[a.index('--probs') + 1], cases), indent=1))
    if a[:1] == ['rule']:
        j0 = json.load(open(a[a.index('--j0') + 1]))
        a1 = json.load(open(a[a.index('--a1') + 1]))
        return print(json.dumps(rule(j0, a1, a[a.index('--tstar') + 1]), indent=1))
    sys.exit(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:])
