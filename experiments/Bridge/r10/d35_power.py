"""Bridge, Round 10: what a D35 decision set of n pool patients can resolve, for paired fine-tune comparisons.

A fine-tune question (A17, A22) compares two models on the same decision-set patients, scored by tF1 against the
patients' two reads. Its resolution has two parts:

  * the **case term**: paired per-case SD of the difference between the two models, sd_pair / sqrt(n);
  * the **seed term** (A22): run-to-run noise of a whole training, sigma_run * sqrt(1/m_a + 1/m_b) for m seeds
    per arm. It does not shrink with n.

Measured inputs (all per-case decisive tF1 on the same ImageCAS val 80, from the repository):

  * atlas3 F1 - F0: two **warm fine-tunes from one base checkpoint** (atlas2's B), same seed, same data stream,
    200 epochs; they differ by an FP loss term that was under 0.1 % of the loss (Atlas: "too weak to test"). This
    is as close as the repository gets to two re-runs of the same fine-tune: the warm fine-tune noise floor.
  * atlas2 B - run 1: two **from-scratch trainings** (412 epochs) differing in the CT window: a training-to-
    training comparison with a small real change.

From each pair: sd_pair (macro and per class), the macro difference d with its case SE, and the 1-df estimate
sigma_run = sqrt(max(d^2 - SE^2, 0) / 2) (Atlas v11 R4's estimator).

Pool scaling: the decision set is pool patients, scored against team reads; f (the pool's spread relative to val)
multiplies sd_pair. f is measured on wave 1 (A31.1); the table shows f = 1, 1.2, 1.5.

Usage: python3 experiments/Bridge/r10/d35_power.py --out experiments/Bridge/r10/d35_power.json
"""
from __future__ import annotations

import argparse
import json
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
TR = os.path.join(REPO, 'trillium-results')
PAIRS = {
    'warm_ft_rerun (atlas3 F1-F0)': (os.path.join(TR, 'round7', 'atlas3', 'per_case_F1.json'),
                                     os.path.join(TR, 'round7', 'atlas3', 'per_case_F0.json')),
    'scratch_retrain (atlas2 B-run1)': (os.path.join(TR, 'round6', 'atlas2', 'results', 'per_case_b.json'),
                                        os.path.join(TR, 'round6', 'atlas2', 'results', 'per_case_run1.json')),
}
NUM = {'LM': '1', 'LAD': '2', 'LCx': '3', 'RCA': '4'}
SIGMA_SEED_A22 = 0.013   # Round 8 A22 prior (Crucible's small from-scratch model)


def decisive_macro(r):
    """Mean over unflagged classes present (the decisive macro of segtrain.tf1 rows)."""
    if 'decisive' in r and r['decisive'] is not None:
        return r['decisive']
    fl = {int(x) for x in r.get('flagged_classes', [])}
    v = [x for k, x in r['per_class'].items() if x is not None and int(k) not in fl]
    return float(np.mean(v)) if v else None


def paired(a_path, b_path):
    A = {r['case']: r for r in json.load(open(a_path))}
    B = {r['case']: r for r in json.load(open(b_path))}
    cases = sorted(set(A) & set(B))
    out = {'n_cases': len(cases)}
    # macro: same definition on both sides (mean of classes unflagged in both)
    d = []
    for c in cases:
        fl = {int(x) for x in A[c].get('flagged_classes', [])} | {int(x) for x in B[c].get('flagged_classes', [])}
        ks = [k for k in NUM.values() if int(k) not in fl and A[c]['per_class'].get(k) is not None
              and B[c]['per_class'].get(k) is not None]
        if ks:
            d.append(np.mean([A[c]['per_class'][k] for k in ks]) - np.mean([B[c]['per_class'][k] for k in ks]))
    d = np.asarray(d)
    se = d.std(ddof=1) / math.sqrt(len(d))
    out['macro'] = {'n': len(d), 'mean_diff': round(float(d.mean()), 4), 'sd_pair': round(float(d.std(ddof=1)), 4),
                    'se_case': round(float(se), 4),
                    'sigma_run_1df': round(math.sqrt(max(d.mean() ** 2 - se ** 2, 0) / 2), 4),
                    'share_cases_identical': round(float(np.mean(np.abs(d) < 1e-9)), 3)}
    for cl, k in NUM.items():
        x = [A[c]['per_class'][k] - B[c]['per_class'][k] for c in cases
             if A[c]['per_class'].get(k) is not None and B[c]['per_class'].get(k) is not None
             and int(k) not in {int(f) for f in A[c].get('flagged_classes', [])}
             and int(k) not in {int(f) for f in B[c].get('flagged_classes', [])}]
        x = np.asarray(x)
        out[cl] = {'n': len(x), 'mean_diff': round(float(x.mean()), 4), 'sd_pair': round(float(x.std(ddof=1)), 4)}
    return out


def sigma_run_pooled(pairs):
    """Pooled run-to-run SD from paired macro differences: each d_j ~ N(0, 2 sigma^2 + SE_j^2) if the two runs
    differ only by noise. Point: maximum likelihood on a grid; upper 95 %: the sigma at which
    sum d_j^2 / (2 sigma^2 + SE_j^2) equals the chi-square 5 % point with len(pairs) df (2 df: 0.1026)."""
    from math import log
    chi2_05 = {1: 0.00393, 2: 0.1026, 3: 0.3518}[len(pairs)]
    grid = np.linspace(0, 0.05, 5001)
    ll = [sum(-0.5 * (log(2 * g * g + se * se) + d * d / (2 * g * g + se * se)) for d, se in pairs) for g in grid]
    point = float(grid[int(np.argmax(ll))])
    up = next(float(g) for g in grid if sum(d * d / (2 * g * g + se * se) for d, se in pairs) <= chi2_05)
    return round(point, 4), round(up, 4)


def mde(sd_pair, n, sigma_run=0.0, m_a=1, m_b=1, alpha_z=1.96, power_z=0.8416):
    """Two-sided 5 %, 80 % power. SE^2 = sd_pair^2 / n + sigma_run^2 (1/m_a + 1/m_b)."""
    se = math.sqrt(sd_pair ** 2 / n + sigma_run ** 2 * (1 / m_a + 1 / m_b))
    return (alpha_z + power_z) * se


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out')
    a = ap.parse_args()
    meas = {name: paired(*p) for name, p in PAIRS.items()}
    for name, m in meas.items():
        print(name, json.dumps(m))
    pooled = sigma_run_pooled([(m['macro']['mean_diff'], m['macro']['se_case']) for m in meas.values()])
    print('pooled sigma_run (point, upper 95 %):', pooled)
    sd_ft = meas['warm_ft_rerun (atlas3 F1-F0)']['macro']['sd_pair']
    sd_sc = meas['scratch_retrain (atlas2 B-run1)']['macro']['sd_pair']
    table = []
    for label, sd, sig, m in (
            ('warm FT vs fixed Janus 0, 2 seeds, sigma = pooled upper 95 %', sd_ft, pooled[1], 2),
            ('warm FT vs warm FT, 1 seed each, sigma_run 0.005', sd_ft, 0.005, 1),
            ('warm FT vs warm FT, 1 seed each, sigma_run = A22 prior 0.013', sd_ft, SIGMA_SEED_A22, 1),
            ('warm FT vs warm FT, 2 seeds each, sigma_run 0.013', sd_ft, SIGMA_SEED_A22, 2),
            ('scratch vs warm (or scratch), 1 seed each, sigma 0.013', sd_sc, SIGMA_SEED_A22, 1),
            ('scratch vs warm, 2 seeds each, sigma 0.013', sd_sc, SIGMA_SEED_A22, 2),
            ('case term only (sd = warm FT floor)', sd_ft, 0.0, 1),
            ('case term only (sd = scratch retrain)', sd_sc, 0.0, 1)):
        for f in (1.0, 1.2, 1.5):
            row = {'design': label, 'f': f, 'sd_pair': round(sd * f, 4), 'sigma_run': sig, 'seeds_per_arm': m}
            for n in (20, 25, 30, 35, 40, 50, 61, 80):
                row[f'mde_n{n}'] = round(mde(sd * f, n, sig, m, float('inf') if 'fixed' in label else m), 4)
            table.append(row)
    for r in table:
        if r['f'] in (1.0, 1.5):
            print(f"{r['design'][:62]:62s} f={r['f']} sd={r['sd_pair']:.3f} " +
                  ' '.join(f"n{n}:{r[f'mde_n{n}']:.3f}" for n in (20, 30, 40, 50, 61)))
    if a.out:
        json.dump({'measured': meas, 'sigma_run_pooled_point_upper95': pooled, 'mde_table': table,
                   'note': 'MDE two-sided 5 %, 80 % power; SE^2 = sd_pair^2/n + sigma_run^2 (1/m_a + 1/m_b)'},
                  open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
