"""Atlas, Round 10 (#113): A10 power at the pool seal (150 / 200 / 250 patients) on Janus 0's own val spread
(Round 9 A31.1), and what a seed-anchoring offset does to it.

Bridge's power model (experiments/Bridge/wave1/power.py, reproduced exactly in Round 9) resamples per-case tF1
from a base distribution per class: model-vs-read with spread f x base, inter-read an independent draw with spread
k x f x base, and a class passes when the lower 95 % bound of mean(model - inter + delta) > -0.05 (D6). Round 9
ran it on run 1's per-case spread (thick reference). Janus 0's per-case file is on Fir, so here the base is run 2
B's per-case per-class tF1 on the same 80 val cases (atlas2, in the repo), linearly rescaled to Janus 0's per-class
mean and SD from its posted CIs (#43; the CI -> SD conversion reproduces run 1's direct SD to 0.0002, see
r10_paired_power.py), clipped to [0, 1]. ``--janus0`` uses the real file instead.

delta: the mean offset of model-vs-read below inter-read. 0 = a model as good as a second reader; -0.02 Round 9's
second row; -0.03 / -0.05 what seed-anchored reads could cost (r10_anchoring.py).

    python experiments/Atlas/r10_seal_power.py --out experiments/Atlas/r10/seal_power.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'experiments', 'Bridge', 'wave1'))
from power import p_pass  # noqa: E402

B_FILE = os.path.join(REPO, 'trillium-results', 'round6', 'atlas2', 'results', 'per_case_b.json')
RUN1_FILE = os.path.join(REPO, 'trillium-results', 'round6', 'atlas2', 'results', 'per_case_run1.json')
# Janus 0, val 80 (#43): per-class decisive mean (r9 scorer, TotalSegmentator ostia) and the SD from Delta's
# per-class CIs (expert ostia, same predictions; the SD is what is borrowed)
J0_MEAN = {1: 0.9449, 2: 0.9035, 3: 0.8566, 4: 0.9375}
J0_CI = {1: (0.9235, 0.9774, 78), 2: (0.8836, 0.9389, 80), 3: (0.8347, 0.8939, 80), 4: (0.9174, 0.9532, 75)}
KEEP = {1: 78 / 80, 2: 1.0, 3: 1.0, 4: 75 / 80}        # scorable (unflagged, present) share per class on val
NAMES = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA'}


def per_class(path):
    rows = json.load(open(path))
    out = {c: [] for c in NAMES}
    for r in rows:
        fl = {int(x) for x in r.get('flagged_classes', [])}
        for c in NAMES:
            v = r['per_class'].get(str(c))
            if v is not None and c not in fl:
                out[c].append(float(v))
    return {c: np.array(v) for c, v in out.items()}


def janus0_base(janus0=None):
    if janus0:
        rows = json.load(open(janus0))
        rows = rows.get('per_case', rows) if isinstance(rows, dict) else rows
        tmp = os.path.join(os.path.dirname(os.path.abspath(janus0)), '.j0_rows.json')
        json.dump([r for r in rows if 'error' not in r and not r.get('provisional')], open(tmp, 'w'))
        return per_class(tmp), 'Janus 0 per-case file'
    b = per_class(B_FILE)
    base = {}
    for c, x in b.items():
        lo, hi, n = J0_CI[c]
        sd_t = (hi - lo) / 3.92 * math.sqrt(n)
        y = J0_MEAN[c] + (x - x.mean()) * (sd_t / x.std(ddof=1))
        base[c] = np.clip(y, 0.0, 1.0)
    return base, 'run 2 B val per-case shape, rescaled to Janus 0 per-class mean and CI-derived SD (#43)'


def p_pass_corr(base, f, k, keep, n, delta=0.0, rho=0.0, sims=4000, seed=20261018):
    """As power.p_pass, but the inter-read score of a case shares a fraction rho of its deviation with the
    model's score on the same case (hard cases are hard for readers too). rho = 0 is power.p_pass."""
    rng = np.random.default_rng(seed)
    passes = np.ones(sims, bool)
    per = {}
    for c, x in base.items():
        x = np.asarray(x, float)
        nc = max(5, int(round(n * keep[c])))
        mu = x.mean()
        i = rng.integers(0, len(x), (sims, nc))
        j = rng.integers(0, len(x), (sims, nc))
        model = mu + f[c] * (x[i] - mu)
        inter = mu + k[c] * f[c] * (rho * (x[i] - mu) + math.sqrt(1 - rho ** 2) * (x[j] - mu))
        d = model - inter + delta
        lo = d.mean(1) - 1.96 * d.std(1, ddof=1) / math.sqrt(nc)
        p = lo > -0.05
        per[c] = round(float(p.mean()), 3)
        passes &= p
    return round(float(passes.mean()), 3), per


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--janus0')
    ap.add_argument('--sims', type=int, default=4000)
    a = ap.parse_args()
    base, src = janus0_base(a.janus0)
    run1 = per_class(RUN1_FILE)
    res = {'base': src,
           'base_sd': {NAMES[c]: round(float(x.std(ddof=1)), 4) for c, x in base.items()},
           'base_mean': {NAMES[c]: round(float(x.mean()), 4) for c, x in base.items()},
           'run1_sd (Round 9 base)': {NAMES[c]: round(float(x.std(ddof=1)), 4) for c, x in run1.items()},
           'rows': []}
    # Round 9 reproduction check on run 1's base (Bridge: 0.966 at n = 150, f = k = 1, delta = 0)
    keep1 = {c: 1.0 for c in NAMES}
    res['check_run1_n150'] = p_pass(run1, {c: 1.0 for c in NAMES}, {c: 1.0 for c in NAMES}, keep1, 150,
                                    sims=a.sims)[0]
    for f in (1.0, 1.25, 1.5):
        for k in (1.0, 1.2):
            for delta in (0.0, -0.02, -0.03, -0.05):
                row = {'f': f, 'k': k, 'delta': delta}
                for n in (150, 200, 250):
                    p, per = p_pass(base, {c: f for c in NAMES}, {c: k for c in NAMES}, KEEP, n, delta,
                                    sims=a.sims)
                    row[f'n{n}'] = p
                    row[f'n{n}_per_class'] = {NAMES[c]: v for c, v in per.items()}
                res['rows'].append(row)
    res['correlated'] = []
    for rho in (0.0, 0.3, 0.5):
        for f in (1.0, 1.25):
            for delta in (0.0, -0.02):
                row = {'rho': rho, 'f': f, 'k': 1.0, 'delta': delta}
                for n in (150, 200, 250):
                    row[f'n{n}'] = p_pass_corr(base, {c: f for c in NAMES}, {c: 1.0 for c in NAMES}, KEEP, n,
                                               delta, rho, sims=a.sims)[0]
                res['correlated'].append(row)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(res, open(a.out, 'w'), indent=1)
    print('base:', src)
    print('base SD', res['base_sd'], '| run 1 SD', res['run1_sd (Round 9 base)'])
    print('check (run 1 base, n 150, f = k = 1, delta 0):', res['check_run1_n150'], '(Round 9: 0.966)')
    print(f"{'f':>5} {'k':>4} {'delta':>6} | {'n150':>6} {'n200':>6} {'n250':>6} | binding class at n150")
    for r in res['rows']:
        worst = min(r['n150_per_class'], key=r['n150_per_class'].get)
        print(f"{r['f']:5.2f} {r['k']:4.1f} {r['delta']:6.2f} | {r['n150']:6.3f} {r['n200']:6.3f} {r['n250']:6.3f} | "
              f"{worst} {r['n150_per_class'][worst]:.3f}")
    print('correlated model and inter-read (k = 1):')
    for r in res['correlated']:
        print(f"  rho {r['rho']:.1f} f {r['f']:.2f} delta {r['delta']:5.2f} | {r['n150']:.3f} {r['n200']:.3f} {r['n250']:.3f}")


if __name__ == '__main__':
    main()
