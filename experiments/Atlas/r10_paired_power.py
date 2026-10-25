"""Atlas, Round 10 (#113): what a D35 decision set of n pool patients can resolve, from measured paired noise.

A wave-1 fine-tune question (A17, A22) is a paired comparison of two models on the same decision-set patients,
each scored against the same reads. Its noise has two parts:
  * a per-case part: the per-case difference d_i = tF1_B(i) - tF1_A(i) varies from case to case. A paired case
    bootstrap (or t interval) over the decision set sees it, and it shrinks as 1/sqrt(n);
  * a model-level part (sigma_g per arm): a whole-model shift from the training run itself (seed, data order, GPU
    nondeterminism) that is common to every case. No number of cases removes it; only more runs per arm do.
A22 carries sigma_seed = 0.013 on macro tF1 as a prior. Whether that is per-case noise (already inside a case CI)
or model-level (outside it) decides whether a larger decision set buys anything.

Two measured pairs exist in the repo, both on the same 80 ImageCAS val cases (thick D0-era reference, so only
ratios are carried to Janus 0):
  * warm replicate: Atlas run 3, F0 vs F1 (trillium-results/round7/atlas3). Both warm from run 2's B, A17a
    trainer, seed 12345, the same data stream, 200 epochs; F1 adds an FP term that stayed at 1e-4 of the loss
    ("too weak to test"). So F1 - F0 is, to a very good approximation, a replicate of one warm fine-tune that
    differs only by GPU nondeterminism and a negligible loss term;
  * scratch pair: Atlas run 2, run 1 vs B (trillium-results/round6/atlas2). Two from-scratch trainings (fixed vs
    default window, 412 vs 368 epochs), judged a tie. An upper bound on per-case noise between two separately
    trained models of one recipe.

Janus 0's own per-case spread comes from its posted CIs (#43): the val-80 decisive macro CI [0.8802, 0.9316] and
Delta's per-class CIs. The per-case file ($SCRATCH/icx4/r9_tf1_val.json) is on Fir; `--janus0` takes it.

Output: per pair, the per-case SD of differences (macro and per class), the ratio to the per-case SD of the arms,
a 1-df estimate of sigma_g; then the minimum detectable effect (80 % power, two-sided 5 %) of a paired decision on
n patients, for pool spread f x val spread, with and without a model-level term.

    python experiments/Atlas/r10_paired_power.py --out experiments/Atlas/r10/paired_power.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
Z = 1.959964 + 0.841621          # two-sided 5 %, 80 % power
CLS = ['1', '2', '3', '4']
NAMES = dict(zip(CLS, ['LM', 'LAD', 'LCx', 'RCA']))

PAIRS = {
    'warm_replicate_F0_F1': ('trillium-results/round7/atlas3/per_case_F0.json',
                             'trillium-results/round7/atlas3/per_case_F1.json'),
    'scratch_pair_run1_B': ('trillium-results/round6/atlas2/results/per_case_run1.json',
                            'trillium-results/round6/atlas2/results/per_case_b.json'),
}

# Janus 0, val 80, from #43 (r9 scorer decisive macro CI; Delta's per-class CIs, expert ostia, same predictions)
JANUS0_MACRO = {'mean': 0.9094, 'ci': (0.8802, 0.9316), 'n': 80}
JANUS0_CLASS = {'1': (0.9546, 0.9235, 0.9774, 78), '2': (0.9148, 0.8836, 0.9389, 80),
                '3': (0.8673, 0.8347, 0.8939, 80), '4': (0.9375, 0.9174, 0.9532, 75)}


def decisive(r):
    """icx4 report.decisive_case_score: macro over unflagged classes (A1b); provisional decides nothing (A1a)."""
    if r.get('provisional'):
        return None
    flagged = {str(c) for c in r.get('flagged_classes', [])}
    v = [x for c, x in r['per_class'].items() if str(c) not in flagged and x is not None]
    return statistics.mean(v) if v else None


def load(path):
    rows = json.load(open(os.path.join(REPO, path)))
    rows = rows.get('per_case', rows) if isinstance(rows, dict) else rows
    return {r['case']: r for r in rows}


def sd(x):
    x = np.asarray(x, float)
    return float(x.std(ddof=1))


def pair_stats(pa, pb):
    a, b = load(pa), load(pb)
    cases = sorted(set(a) & set(b))
    out = {'n_cases': len(cases)}
    da = [decisive(a[c]) for c in cases]
    db = [decisive(b[c]) for c in cases]
    keep = [i for i in range(len(cases)) if da[i] is not None and db[i] is not None]
    x, y = np.array([da[i] for i in keep]), np.array([db[i] for i in keep])
    d = y - x
    out['macro'] = {
        'n': len(keep), 'mean_a': round(float(x.mean()), 4), 'mean_b': round(float(y.mean()), 4),
        'mean_diff': round(float(d.mean()), 4), 'sd_diff': round(sd(d), 4),
        'se_diff': round(sd(d) / math.sqrt(len(d)), 4),
        'sd_case_a': round(sd(x), 4), 'sd_case_b': round(sd(y), 4),
        'corr': round(float(np.corrcoef(x, y)[0, 1]), 3),
        'ratio_sd_diff_to_sd_case': round(sd(d) / math.sqrt((sd(x) ** 2 + sd(y) ** 2) / 2), 3),
        # 1-df estimate of the model-level term per arm: E[mean_d^2] = 2 sigma_g^2 + SE^2
        'sigma_g_1df': round(math.sqrt(max(float(d.mean()) ** 2 - (sd(d) ** 2 / len(d)), 0) / 2), 4),
        'share_cases_identical': round(float(np.mean(np.abs(d) < 1e-9)), 3),
    }
    per = {}
    for c in CLS:
        xs, ys = [], []
        for cs in cases:
            ra, rb = a[cs], b[cs]
            fa = {str(k) for k in ra.get('flagged_classes', [])} | {str(k) for k in rb.get('flagged_classes', [])}
            va, vb = ra['per_class'].get(c), rb['per_class'].get(c)
            if c in fa or va is None or vb is None:
                continue
            xs.append(va)
            ys.append(vb)
        xs, ys = np.array(xs), np.array(ys)
        dd = ys - xs
        per[NAMES[c]] = {'n': len(dd), 'mean_diff': round(float(dd.mean()), 4), 'sd_diff': round(sd(dd), 4),
                         'sd_case': round(math.sqrt((sd(xs) ** 2 + sd(ys) ** 2) / 2), 4),
                         'ratio': round(sd(dd) / math.sqrt((sd(xs) ** 2 + sd(ys) ** 2) / 2), 3)}
    out['per_class'] = per
    return out


def janus0_sd(janus0_path=None):
    """Per-case SD of Janus 0's val decisive tF1: from the per-case file if given, else from the posted CIs
    (SD ~ CI width / 3.92 * sqrt(n); a percentile bootstrap of a skewed bounded score, so approximate)."""
    if janus0_path:
        rows = json.load(open(janus0_path))
        rows = rows.get('per_case', rows) if isinstance(rows, dict) else rows
        dec = [decisive(r) for r in rows if 'error' not in r]
        dec = [x for x in dec if x is not None]
        return {'source': janus0_path, 'macro': round(sd(dec), 4), 'n': len(dec)}
    lo, hi = JANUS0_MACRO['ci']
    out = {'source': 'CI-derived (#43)', 'macro': round((hi - lo) / 3.92 * math.sqrt(JANUS0_MACRO['n']), 4)}
    for c, (m, lo, hi, n) in JANUS0_CLASS.items():
        out[NAMES[c]] = round((hi - lo) / 3.92 * math.sqrt(n), 4)
    return out


def mde(sd_diff, n, sigma_g=0.0, runs_per_arm=1):
    return Z * math.sqrt(sd_diff ** 2 / n + 2 * sigma_g ** 2 / runs_per_arm)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--janus0', help="Janus 0's val per-case JSON (r9_score_icx4.py output), if available")
    a = ap.parse_args()

    res = {'pairs': {k: pair_stats(*v) for k, v in PAIRS.items()}, 'janus0_sd_case': janus0_sd(a.janus0)}
    # calibration check of the CI -> SD conversion on run 1, whose per-case file exists
    r1 = load(PAIRS['scratch_pair_run1_B'][0])
    dec = np.array([x for x in (decisive(r) for r in r1.values()) if x is not None])
    rng = np.random.default_rng(0)
    boots = np.array([dec[rng.integers(0, len(dec), len(dec))].mean() for _ in range(4000)])
    lo, hi = np.percentile(boots, [2.5, 97.5])
    res['ci_to_sd_check_run1'] = {'sd_direct': round(sd(dec), 4),
                                  'sd_from_ci': round((hi - lo) / 3.92 * math.sqrt(len(dec)), 4)}

    sd_j0 = res['janus0_sd_case']['macro']
    rw = res['pairs']['warm_replicate_F0_F1']['macro']['ratio_sd_diff_to_sd_case']
    rs = res['pairs']['scratch_pair_run1_B']['macro']['ratio_sd_diff_to_sd_case']
    table = []
    for label, ratio in (('warm (F0/F1 ratio)', rw), ('scratch (run1/B ratio)', rs)):
        for f in (1.0, 1.25, 1.5):
            sdd = ratio * sd_j0 * f
            row = {'pair_type': label, 'f': f, 'sd_diff_pool': round(sdd, 4)}
            for n in (20, 26, 35, 50, 61, 80):
                row[f'mde_n{n}'] = round(mde(sdd, n), 4)
                row[f'mde_n{n}_sg013'] = round(mde(sdd, n, 0.013), 4)
                row[f'mde_n{n}_sg013_2runs'] = round(mde(sdd, n, 0.013, 2), 4)
            table.append(row)
    res['mde_table'] = table
    res['notes'] = ('mde = 2.80 * sqrt(sd_diff^2 / n + 2 sigma_g^2 / runs_per_arm); sd_diff on the pool = ratio x '
                    "Janus 0's val per-case SD x f; _sg013 adds A22's 0.013 as a model-level term per arm")
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(res, open(a.out, 'w'), indent=1)
    print(json.dumps({k: res[k] for k in ('pairs', 'janus0_sd_case', 'ci_to_sd_check_run1')}, indent=1))
    print('MDE (macro tF1, 80 % power):')
    for r in table:
        print(f"  {r['pair_type']:24s} f={r['f']:.2f} sd_d={r['sd_diff_pool']:.3f}  " +
              '  '.join(f"n{n}: {r[f'mde_n{n}']:.3f}/{r[f'mde_n{n}_sg013']:.3f}" for n in (26, 35, 50, 61, 80)))


if __name__ == '__main__':
    main()
