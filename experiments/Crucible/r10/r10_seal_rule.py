"""Crucible, Round 10: two rules for sizing the A10 seal from wave-1 reads, compared on simulated worlds.

Rule F/K (Round 9 A31.1, as implemented in experiments/Bridge/wave1/report_wave1.py): on the wave-1 patients,
estimate f = SD(model-vs-read) / SD(val model) and k = SD(inter-read) / SD(model-vs-read) per class; if any
f or k > 1.2, extend to 200, or to the maximum if Bridge's power re-run at 200 (with the measured f, k) is < 0.8.

Rule D (Crucible v11 §3): on the D35 patients, take the per-patient A10 contrast d = model-vs-read - inter-read per
class *as measured* (so f, k and their correlation enter together), centre it at 0 (a human-level model), and
choose the smallest seal in {150, 200, max} whose bootstrap P(all four classes pass) >= 0.8.

Worlds: Janus 0-shaped per-class per-case tF1 (r10_power.janus0_shaped), pool spread f in {1, 1.2, 1.5}, k = 1,
correlation rho between a patient's model-vs-read and inter-read deviations in {0, 0.5}. Per world, 400 wave-1
samples of 30 patients; for each, the size each rule picks and the *true* P(pass at human level) at that size.
max = 227 (the seal's 150 + its extension order once the D35 draw is skipped; d35_proposal.json).
Usage: python3 r10_seal_rule.py > r10_seal_rule.json
"""
from __future__ import annotations

import json
import math
import sys

import numpy as np

import r10_power as P

KEEP = {'LM': 0.85, 'LAD': 0.95, 'LCx': 0.95, 'RCA': 0.95}
SIZES = (150, 200, 227)
N_WAVE = 30
REPS = 400


def draw(base, f, rho, n, rng):
    """Per class: (model-vs-read, inter-read) for n patients."""
    out = {}
    for c, x in base.items():
        mu = x.mean()
        e1 = x[rng.integers(0, len(x), n)] - mu
        e2 = x[rng.integers(0, len(x), n)] - mu
        out[c] = (mu + f * e1, mu + f * (rho * e1 + math.sqrt(1 - rho * rho) * e2))
    return out


def p_pass_d(dists, n, sims=1500, rng=None):
    """P(all four pass) at seal size n, resampling each class's centred contrast."""
    rng = rng or np.random.default_rng(1)
    ok = np.ones(sims, bool)
    for c, d in dists.items():
        d = np.asarray(d) - np.mean(d)
        nc = max(5, int(round(n * KEEP[c])))
        s = d[rng.integers(0, len(d), (sims, nc))]
        lo = s.mean(1) - 1.96 * s.std(1, ddof=1) / math.sqrt(nc)
        ok &= lo > -0.05
    return float(ok.mean())


def rule_d(sample, rng):
    dists = {c: m - i for c, (m, i) in sample.items()}
    for n in SIZES:
        if p_pass_d(dists, n, rng=rng) >= 0.8:
            return n
    return SIZES[-1]


def rule_fk(sample, base, rng):
    f = {c: np.std(m, ddof=1) / base[c].std(ddof=1) for c, (m, i) in sample.items()}
    k = {c: np.std(i, ddof=1) / max(np.std(m, ddof=1), 1e-9) for c, (m, i) in sample.items()}
    if max(max(f.values()), max(k.values())) <= 1.2:
        return 150
    p200, _ = P.bridge_power.p_pass(base, f, k, KEEP, 200, sims=1500)
    return 200 if p200 >= 0.8 else SIZES[-1]


def true_p(base, f, rho, n):
    p, _ = P.p_pass_rho(base, f, 1.0, KEEP, n, rho, sims=4000)
    return p


def main():
    base = P.janus0_shaped()
    rng = np.random.default_rng(20261025)
    rows = []
    for f in (1.0, 1.2, 1.5):
        for rho in (0.0, 0.5):
            tp = {n: true_p(base, f, rho, n) for n in SIZES}
            picks = {'D': [], 'FK': []}
            for _ in range(REPS):
                s = draw(base, f, rho, N_WAVE, rng)
                picks['D'].append(rule_d(s, rng))
                picks['FK'].append(rule_fk(s, base, rng))
            row = dict(f=f, rho=rho, true_p_pass={str(n): v for n, v in tp.items()})
            for r, v in picks.items():
                v = np.array(v)
                row[r] = dict(share={str(n): round(float((v == n).mean()), 3) for n in SIZES},
                              mean_size=round(float(v.mean()), 1),
                              expected_true_p=round(float(np.mean([tp[int(x)] for x in v])), 3))
            rows.append(row)
    json.dump({'n_wave': N_WAVE, 'reps': REPS, 'sizes': SIZES, 'rows': rows}, sys.stdout, indent=1)


if __name__ == '__main__':
    main()
