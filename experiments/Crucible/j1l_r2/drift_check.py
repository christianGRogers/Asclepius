"""Crucible, Janus 1-L Round 2: Rule T, a label-free check that t* still sits at the same operating point on the
candidate network, decided without any locked-100 number (Janus 1-L Round 1, section 5 item 3).

Why. t* is chosen by Rule W on Janus 0's probabilities for the tuning 60 (L-A4). It is applied to Janus 1-L's
candidate C (E, or a1; Crucible v2 section 1). If the fine-tune moved the network's rim calibration, the same t gives C a
different lumen width than it gave Janus 0, and nothing before the locked-100 look would show it. Every ImageCAS-X case
with a label is now either trained on (620), locked (100) or sealed (80), so a calibration check with labels is
impossible without a look. The check must therefore be label-free and run on CTs outside all three sets.

The set U. ImageCAS's 200 quality-0 cases (ImageCAS-X's `exclude.txt`) have no ImageCAS-X label and are in no D45 list.
U = those 200 minus the 20 sealed (A14), minus the 24 declared development cases, minus any pool-sealed name (D27,
`segtrain.pool_seal`, exclude mode), ranked by sha256('asclepius-j1l-drift:' + id); the first 40. No label of any U case
is read, ever: the check uses predicted volumes only. Caveat: quality-0 scans were left out of ImageCAS-X for image
quality, so the *absolute* volumes on U mean little; the check compares two networks on the same scans.

The rule (pre-registered; `decide`):
  V_M(c, t) = voxels where the summed vessel probability of network M is >= t (t = 0.5 reproduces argmax).
  r(t)      = median over U of V_C(c, t) / V_J0(c, t*).
  If 0.97 <= r(t*) <= 1.03: C is exported at t* (the frozen rule stands; the expected case).
  Otherwise: C is exported at t_C = the t on the grid 0.300, 0.325, ..., 0.500 whose r(t) is closest to 1
  (ties to the larger t). This keeps the *volume* at which Rule W found Janus 0's Dice optimum: the label of a case
  does not change between networks, so matching C's predicted volume to Janus 0's at t* keeps the volume ratio
  Rule W chose.
  The result (`drift.json`) and its sha256 are posted on #302 before the locked 100 is scored. It is applied once.

Why a band and not always matching: a fine-tune that genuinely widened the lumen at 0.5 should keep that gain, and the
band leaves t* alone unless the shift is larger than about a quarter of the correction t* is expected to make (Rule W's
prediction: volume ratio 0.867 -> about 0.95, i.e. +9-10 %).

Usage:
  python drift_check.py select --exclude <ImageCAS-X exclude.txt> > $W/drift_cases.json       # the 40 ids
  python drift_check.py decide --j0 $W/drift/janus0 --cand $W/drift/cand --tstar <t*> > $W/drift.json
  python drift_check.py --selftest
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
SALT = 'asclepius-j1l-drift:'
N_U = 40
GRID = [round(0.300 + 0.025 * i, 3) for i in range(9)]
BAND = (0.97, 1.03)


def select(exclude_txt, sealed_json=os.path.join(ROOT, 'trillium', 'sealed_test.json'), lists_json=None):
    S = json.load(open(sealed_json))
    q0 = ['c%04d' % (int(x) - 1) for x in open(exclude_txt).read().split()]
    assert len(q0) == 200, len(q0)
    drop = set(S['sealed_quality0']) | set(S['excluded_dev_cases_in_quality0']) | set(S['sealed_icx_test'])
    L = json.load(open(lists_json or os.path.join(ROOT, 'experiments', 'Crucible', 'j1l_r1', 'lists.json')))
    drop |= set(L['locked100']) | set(L['train620'])
    ok = [c for c in q0 if c not in drop]
    try:
        sys.path.insert(0, os.path.join(ROOT, 'src'))
        from segtrain.pool_seal import EXCLUDE, apply
        ok = apply(ok, mode=EXCLUDE, what='Janus 1-L drift set U')
    except ImportError:
        sys.exit('[drift] REFUSING: segtrain.pool_seal is not importable, so D27 cannot be checked')
    ranked = sorted(ok, key=lambda c: hashlib.sha256((SALT + c).encode()).hexdigest())
    return dict(salt=SALT, n_available=len(ok), U=sorted(ranked[:N_U]))


def volumes(npz, grid):
    p = np.load(npz)['probabilities'].astype(np.float32)
    v = p[1:].sum(0)
    out = {t: int((v >= t).sum()) for t in grid}
    out[0.5] = int((p.argmax(0) > 0).sum())      # t = 0.5 is the argmax export (threshold_export.py)
    return out


def decide(j0_dir, cand_dir, tstar, U=None):
    tstar = round(float(tstar), 3)
    files = sorted(glob.glob(os.path.join(j0_dir, '*.npz')))
    cases = [os.path.basename(f)[:-4] for f in files]
    if U is not None and sorted(cases) != sorted(U):
        sys.exit(f'[drift] REFUSING: {j0_dir} does not hold exactly the drift set U')
    ratios = {t: [] for t in GRID}
    for c in cases:
        vj = volumes(os.path.join(j0_dir, c + '.npz'), [tstar])[tstar]
        vc = volumes(os.path.join(cand_dir, c + '.npz'), GRID)
        if vj == 0:
            continue
        for t in GRID:
            ratios[t].append(vc[t] / vj)
    r = {t: float(np.median(v)) for t, v in ratios.items() if v}
    r_star = r[tstar]
    if BAND[0] <= r_star <= BAND[1]:
        chosen, why = tstar, f'r(t*) = {r_star:.4f} inside {BAND}: t* stands'
    else:
        chosen = min(GRID, key=lambda t: (abs(r[t] - 1.0), -t))
        why = f'r(t*) = {r_star:.4f} outside {BAND}: volume-matched t_C = {chosen}'
    return dict(rule='Crucible v2 Rule T', tstar=tstar, n_cases=len(ratios[tstar]), r={str(t): round(v, 4)
                for t, v in r.items()}, chosen_t=chosen, reason=why)


def selftest():
    import tempfile
    rng = np.random.default_rng(0)
    d = tempfile.mkdtemp()
    for name, shift in (('j0', 0.0), ('same', 0.0), ('wider', 0.08)):
        os.makedirs(os.path.join(d, name))
        for i in range(6):
            r = np.linspace(0, 1, 4000).reshape(10, 20, 20)            # a "rim" of graded probabilities
            fg = np.clip(r + shift + rng.normal(0, 0.001, r.shape), 0, 1)
            p = np.stack([1 - fg, fg * 0.25, fg * 0.25, fg * 0.25, fg * 0.25]).astype(np.float32)
            np.savez(os.path.join(d, name, f'c{i:04d}.npz'), probabilities=p)
    a = decide(os.path.join(d, 'j0'), os.path.join(d, 'same'), 0.4)
    assert a['chosen_t'] == 0.4, a
    b = decide(os.path.join(d, 'j0'), os.path.join(d, 'wider'), 0.4)
    assert b['chosen_t'] > 0.4 and abs(b['r'][str(b['chosen_t'])] - 1) < 0.03, b
    print('[drift] selftest OK: no shift keeps t*, a wider network gets a higher, volume-matched t')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', nargs='?', choices=['select', 'decide'])
    ap.add_argument('--exclude'); ap.add_argument('--j0'); ap.add_argument('--cand'); ap.add_argument('--tstar')
    ap.add_argument('--cases'); ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.mode == 'select':
        print(json.dumps(select(a.exclude), indent=1))
    elif a.mode == 'decide':
        U = json.load(open(a.cases))['U'] if a.cases else None
        print(json.dumps(decide(a.j0, a.cand, a.tstar, U), indent=1))


if __name__ == '__main__':
    main()
