"""Round 6 (Q1, fine-tuning recipe): how precisely can one wave's decision be judged on a val set of n cases?
Inputs are the round-5 GPU results only (no case data):
  * training-to-training paired noise: Crucible's six arms (same data, 300 epochs each, 50 test cases); the paired SD
    of a comparison is recovered from its bootstrap 95 % CI as sd = (hi - lo) / 3.92 * sqrt(50);
  * same-model, different-naming noise: Bridge's R/H/O arms vs D on Atlas run 1 (80 val cases, per-case JSON).
Outputs the minimal detectable paired difference (two-sided 5 %, 80 % power: 2.80 sd / sqrt(n)), the CI half-width
(1.96 sd / sqrt(n)), and the n needed for a non-inferiority test at margin m with true difference 0
(one-sided 5 %, 80 % power: ((1.645 + 0.842) sd / m)^2).
Usage: python r6_wave_power.py  (writes r6_wave_power.json next to this file)"""
import glob
import json
import os
import re

import numpy as np

R5 = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'trillium-results', 'round5')
out = {}
s = open(f'{R5}/crucible/results/SUMMARY.md').read()
cru = {}
for m in re.finditer(r'- (\S+): ([+-][0-9.]+) \[([+-][0-9.]+), ([+-][0-9.]+)\]', s):
    lo, hi = float(m.group(3)), float(m.group(4))
    cru[m.group(1)] = dict(mean=float(m.group(2)), ci=[lo, hi], sd=(hi - lo) / 3.92 * np.sqrt(50))
out['crucible_paired'] = cru
cs = [json.load(open(f)) for f in sorted(glob.glob(f'{R5}/bridge/results/cases/*.json'))]
D = np.array([c['D']['tf1'] for c in cs])
out['bridge_paired'] = {a: dict(mean=float((np.array([c[a]['tf1'] for c in cs]) - D).mean()),
                                sd=float((np.array([c[a]['tf1'] for c in cs]) - D).std(ddof=1))) for a in 'RHO'}
out['per_case_tf1_sd'] = float(D.std(ddof=1))
# noise regimes: near-null retraining (agree vs both: labels differ only in a thin ignore band), typical retraining
regimes = {'near_null_retraining (agree-both)': cru['agree-both_vs_T']['sd'],
           'label-form change (median of single-arm comparisons)': float(np.median([v['sd'] for k, v in cru.items() if 'single' in k])),
           'renaming on one model (Bridge H-D)': out['bridge_paired']['H']['sd']}
ns = (36, 80, 124, 160, 300)
out['regimes'] = {}
for name, sd in regimes.items():
    out['regimes'][name] = dict(sd=sd, mde={n: 2.80 * sd / np.sqrt(n) for n in ns},
                                ci_half={n: 1.96 * sd / np.sqrt(n) for n in ns},
                                n_noninferior={m: int(np.ceil(((1.645 + 0.842) * sd / m) ** 2)) for m in (0.005, 0.01, 0.02)})
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'r6_wave_power.json'), 'w'), indent=1)
for name, r in out['regimes'].items():
    print(f"{name}: sd {r['sd']:.3f}")
    print('   MDE   ', {n: round(v, 4) for n, v in r['mde'].items()})
    print('   CI±   ', {n: round(v, 4) for n, v in r['ci_half'].items()})
    print('   n for non-inferiority (margin: n)', r['n_noninferior'])
