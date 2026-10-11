"""Summarise r8_miss_census.py: where run 1's remaining tF1 loss lives, per class (unflagged trees,
the decisive set), plus the two A1c checks.
Usage: python summarise_r8_census.py census.jsonl"""
import collections
import json
import sys

import numpy as np

N = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA'}
RB = ['r<0.75', '0.75-1', '1-1.5', '>1.5']
GB = ['0-20', '20-60', '60-100', '>100']
rows = [json.loads(line) for line in open(sys.argv[1])]
err = [r['case'] for r in rows if 'error' in r]
rows = [r for r in rows if 'error' not in r]
print(f'cases {len(rows)}; errors {err}')

print('\n## A1c test 3 (run-1 predictions): new hash vs atlas2 (old hash) per_class')
print('identical:', sum(r['identical_to_atlas2'] for r in rows), '/', len(rows),
      '| not identical:', [r['case'] for r in rows if not r['identical_to_atlas2']])
print('classes_without_centreline:', [(r['case'], r['missing']) for r in rows if r['missing']])

print('\n## A1c test 8: paired default vs fallback (macro, and the centreline-less class)')
fb = [r for r in rows if 'fallback' in r]
for r in fb:
    c = r['missing'][0]
    print(f"  {r['case']}: macro {r['tf1']:.4f} -> {r['fallback']['tf1']:.4f}; class {N[c]} "
          f"(absent) -> {r['fallback']['per_class'][str(c)]:.4f}; flagged {r['flagged_classes']}")
d = [r['fallback']['tf1'] - r['tf1'] for r in fb]
allm = np.mean([r['tf1'] for r in rows])
allf = np.mean([r['fallback']['tf1'] if 'fallback' in r else r['tf1'] for r in rows])
print(f'  7-case mean macro change {np.mean(d):+.4f}; all 80 macro {allm:.4f} -> {allf:.4f} ({allf - allm:+.4f})')
lm_old = [r['per_class'].get('1') for r in rows if '1' in r['per_class']]
lm_new = [(r['fallback']['per_class'] if 'fallback' in r else r['per_class']).get('1') for r in rows]
lm_new = [v for v in lm_new if v is not None]
print(f'  LM: n {len(lm_old)} mean {np.mean(lm_old):.4f} (default) -> n {len(lm_new)} mean {np.mean(lm_new):.4f} (fallback)')

print('\n## Census (unflagged classes): mean per case, as a fraction of the class reference centreline')
for c in (1, 2, 3, 4):
    v = [r['census'][str(c)] for r in rows if str(c) in r['census'] and c not in r['flagged_classes']]
    if not v:
        continue
    kinds = collections.Counter()
    rb, gb, icx = collections.Counter(), collections.Counter(), collections.Counter()
    for x in v:
        for kind, rbin, gbin, traced, n in x['lost']:
            f = n / x['n_ref']
            kinds[kind] += f
            rb[RB[rbin]] += f
            gb[GB[gbin]] += f
            icx['icx-traced' if traced else 'mask-only'] += f
    k = len(v)
    rec = np.mean([x['recall'] for x in v])
    prec = np.mean([x['precision'] for x in v])
    fpk = collections.Counter()
    for x in v:
        for kind, n in x['fp'].items():
            fpk[kind] += n / max(x['n_pred'], 1)
    mo = np.mean([1 - x['ref_icx_frac'] for x in v])
    dist = [x['lost_dist_to_pred_mm'][1] for x in v if x['lost_dist_to_pred_mm']]
    print(f'### {N[c]} (n {k}): recall {rec:.3f}, precision {prec:.3f}; mask-only share of reference centreline {mo:.3f}')
    print('  recall loss by kind:', {a: round(b / k, 4) for a, b in kinds.most_common()})
    print('  recall loss by radius:', {a: round(rb[a] / k, 4) for a in RB})
    print('  recall loss by distance from ostium (mm):', {a: round(gb[a] / k, 4) for a in GB})
    print('  recall loss traced by ImageCAS-X?:', {a: round(b / k, 4) for a, b in icx.items()})
    print('  precision loss by kind:', {a: round(b / k, 4) for a, b in fpk.most_common()})
    print(f'  median distance of lost centreline to the prediction: {np.median(dist):.2f} mm (per-case medians)')
