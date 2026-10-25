"""Bridge, Round 10 (A31.1): re-power A10 (D6) on Janus 0's own per-case val spread.

Round 9's power (0.966 at n = 150) used run 1's per-class per-case tF1, a model on the retired thick convention.
Janus 0 (icx4, D34) is the base model now. Its per-case val tF1 lives on Fir (`$SCRATCH/icx4/r9_tf1_val.json`);
what is in the repository is its per-class decisive means (r9 scorer, TotalSegmentator ostia) and per-class 95 %
bootstrap CIs on the same 80 cases (Delta's scorer, expert ostia; #43). So, by default, this script builds a
**surrogate** per-case distribution for each class:

    run 1's per-case shape on the same val 80 (atlas2 `per_case_run1.json`, unflagged trees),
    mapped affinely to Janus 0's mean and to the SD recovered from its CI, sd = (hi - lo) / 3.92 * sqrt(n),
    clipped to [0, 1] and re-fitted (three passes).

With ``--val r9_tf1_val.json`` it uses Janus 0's real rows instead; that is the exact re-power A31.1 asks for, and
the plan pre-registers that the exact numbers replace the surrogate ones (one CPU minute on the Fir login node).

The power model is Round 9's (`experiments/Bridge/wave1/power.py`, reproduced by the judge), extended by one
parameter, rho: the within-patient correlation between model-vs-read and inter-read tF1 (hard cases are hard for
both). rho = 0 is Round 9's independent model, the cautious one.

Usage:
    python3 experiments/Bridge/r10/power_r10.py --out experiments/Bridge/r10/power_r10.json
    python3 experiments/Bridge/r10/power_r10.py --val $SCRATCH/icx4/r9_tf1_val.json --out power_exact.json
"""
from __future__ import annotations

import argparse
import json
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
RUN1 = os.path.join(REPO, 'trillium-results', 'round6', 'atlas2', 'results', 'per_case_run1.json')
CLASSES = ['LM', 'LAD', 'LCx', 'RCA']
NUM = {'LM': '1', 'LAD': '2', 'LCx': '3', 'RCA': '4'}
MARGIN = 0.05

# Janus 0 on val 80 (#43; vault/Plans/Experiments/icx4 - Results.md).
# mean: r9 scorer, decisive (TotalSegmentator ostia, A1 as written).
# ci, n: Delta's scorer on the same predictions (expert ostia; P2's sensitivity run). The left-tree means differ by
# about 0.01 between the two; the spread is taken from Delta's CI because the r9 summary has no per-class CI.
JANUS0 = {
    'LM': {'mean': 0.9449, 'ci': (0.9235, 0.9774), 'n': 78},
    'LAD': {'mean': 0.9035, 'ci': (0.8836, 0.9389), 'n': 80},
    'LCx': {'mean': 0.8566, 'ci': (0.8347, 0.8939), 'n': 80},
    'RCA': {'mean': 0.9375, 'ci': (0.9174, 0.9532), 'n': 75},
}
KEEP = {'LM': 78 / 80, 'LAD': 1.0, 'LCx': 1.0, 'RCA': 75 / 80}   # decisive trees per case on val (flags out)


def sd_from_ci(ci, n):
    return (ci[1] - ci[0]) / 3.92 * math.sqrt(n)


def fit(shape, mean, sd, passes=3):
    """Affine map of `shape` to (mean, sd), clipped to [0, 1], re-fitted a few times."""
    x = np.asarray(shape, float)
    y = x.copy()
    for _ in range(passes):
        z = (x - x.mean()) / x.std(ddof=1)
        a, b = sd, mean
        y = np.clip(b + a * z, 0, 1)
        # correct for clipping: nudge targets by the error
        mean += mean - y.mean() if passes > 1 else 0
        sd *= sd / max(y.std(ddof=1), 1e-9) if passes > 1 else 1
    return y


def surrogate():
    run1 = json.load(open(RUN1))
    base = {}
    for c in CLASSES:
        k = NUM[c]
        shape = [r['per_class'][k] for r in run1 if r['per_class'].get(k) is not None
                 and int(k) not in r['flagged_classes']]
        target_sd = sd_from_ci(JANUS0[c]['ci'], JANUS0[c]['n'])
        y = fit(shape, JANUS0[c]['mean'], target_sd)
        base[c] = y
    return base


def exact(path):
    d = json.load(open(path))
    rows = d['rows'] if isinstance(d, dict) and 'rows' in d else d
    rows = rows.values() if isinstance(rows, dict) else rows
    base = {c: [] for c in CLASSES}
    for r in rows:
        if r.get('provisional'):
            continue
        flagged = {str(f) for f in r.get('flagged_classes', [])}
        for c in CLASSES:
            v = r['per_class'].get(c, r['per_class'].get(NUM[c]))
            if v is None or c in flagged or NUM[c] in flagged:
                continue
            base[c].append(v)
    return {c: np.asarray(v, float) for c, v in base.items()}


def p_pass(base, f, k, n, delta=0.0, rho=0.0, sims=4000, seed=20261025):
    """Round 9's model: model-vs-read per patient resampled from `base` with spread x f; inter-read with
    spread x k f; correlation rho between the two within a patient. Pass a class when the lower 95 % bound of
    mean(model - inter + delta) > -0.05; all four must pass."""
    rng = np.random.default_rng(seed)
    allp = np.ones(sims, bool)
    per = {}
    for c in CLASSES:
        x = np.asarray(base[c], float)
        mu = x.mean()
        nc = max(5, int(round(n * KEEP[c])))
        i = rng.integers(0, len(x), (sims, nc))
        j = rng.integers(0, len(x), (sims, nc))
        dm = x[i] - mu
        dj = x[j] - mu
        model = mu + f * dm
        inter = mu + k * f * (rho * dm + math.sqrt(1 - rho ** 2) * dj)
        d = model - inter + delta
        lo = d.mean(1) - 1.96 * d.std(1, ddof=1) / math.sqrt(nc)
        p = lo > -MARGIN
        per[c] = round(float(p.mean()), 3)
        allp &= p
    return round(float(allp.mean()), 3), per


def run1_base():
    run1 = json.load(open(RUN1))
    return {c: np.asarray([r['per_class'][NUM[c]] for r in run1 if r['per_class'].get(NUM[c]) is not None
                           and int(NUM[c]) not in r['flagged_classes']], float) for c in CLASSES}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--val', help="Janus 0's r9_tf1_val.json (exact re-power); default: the surrogate")
    ap.add_argument('--out')
    ap.add_argument('--sims', type=int, default=4000)
    a = ap.parse_args()
    base = exact(a.val) if a.val else surrogate()
    desc = {c: {'n': int(len(v)), 'mean': round(float(np.mean(v)), 4), 'sd': round(float(np.std(v, ddof=1)), 4)}
            for c, v in base.items()}
    r1 = run1_base()
    desc_r1 = {c: {'n': int(len(v)), 'mean': round(float(np.mean(v)), 4), 'sd': round(float(np.std(v, ddof=1)), 4)}
               for c, v in r1.items()}
    grid = []
    for n in (100, 150, 200, 250, 300):
        for f, k in ((1.0, 1.0), (1.2, 1.0), (1.0, 1.2), (1.2, 1.2), (1.5, 1.0), (1.5, 1.2)):
            for delta in (0.0, -0.02):
                for rho in (0.0, 0.5):
                    p, per = p_pass(base, f, k, n, delta, rho, a.sims)
                    grid.append({'n': n, 'f': f, 'k': k, 'delta': delta, 'rho': rho, 'p_all': p, 'per_class': per})
    check = p_pass(r1, 1.0, 1.0, 150, 0.0, 0.0, a.sims)
    out = {'source': a.val or 'surrogate: run-1 shape fitted to Janus 0 mean and CI-recovered SD',
           'janus0_inputs': JANUS0, 'base': desc, 'run1_base': desc_r1,
           'round9_check_run1_n150': check, 'grid': grid}
    for g in grid:
        if g['rho'] == 0.0 and g['delta'] == 0.0:
            print(f"n={g['n']:3d} f={g['f']} k={g['k']}  P(all)={g['p_all']:.3f}  {g['per_class']}")
    print('base', json.dumps(desc))
    print('Round 9 check (run 1, n=150, f=k=1):', check)
    if a.out:
        json.dump(out, open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
