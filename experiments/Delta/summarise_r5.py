"""Join r5_cut_anatomy.py output with Atlas's per-case validation numbers.

Usage: python summarise_r5.py per_case_val.json anatomy.jsonl [anatomy.jsonl ...]"""
import collections
import json
import sys

import numpy as np

NAMES = {'1': 'LM', '2': 'LAD', '3': 'LCx', '4': 'RCA'}
BAD_MM = 5.0

val = {x['case']: x for x in json.load(open(sys.argv[1]))}
an = {}
for p in sys.argv[2:]:
    for line in open(p):
        r = json.loads(line)
        an[r['case']] = r
rows = []
for c, x in val.items():
    a = an.get(c)
    if a is None or 'error' in a:
        print('missing', c, a and a.get('error'))
        continue
    gap = {NAMES[k]: x['cldice_per_class'][k] - x['tf1_per_class'][k] for k in x['tf1_per_class']}
    cut = {k: v for k, v in gap.items() if v > 0.10}
    # Atlas's ostia: per side, distance to the expert ostium
    roots = {r['side']: r for r in a['atlas_roots']}
    bad_root = {s: r['d_true_mm'] for s, r in roots.items() if not r['d_true_mm'] <= BAD_MM}
    mine_bad = [m['d_true_mm'] for m in a['mine'] if not m['d_true_mm'] <= BAD_MM]
    whole = [k for k, v in cut.items() if x['tf1_per_class'][{v2: k2 for k2, v2 in NAMES.items()}[k]] < 0.02]
    side_of = lambda k: 'right' if k == 'RCA' else 'left'  # noqa: E731
    kind = {}
    for k in cut:
        if side_of(k) in bad_root:
            kind[k] = 'ostium_misplaced'
        elif k in whole:
            kind[k] = 'whole_class_unrooted_ostium_ok'
        else:
            kind[k] = 'partial_cut'
    rows.append(dict(case=c, tf1=x['tf1'], cut=cut, kind=kind, bad_root=bad_root, mine_bad=mine_bad,
                     lm=a['lm_present'], fp=x['fp_components'],
                     orphans=x['pred_components'] - x['fp_components'] - x['ref_components'],
                     tol_gain=x['tf1'] - x['tf1_tol0']))
cut_rows = [r for r in rows if r['cut']]
print(f'cases {len(rows)}; with cut {len(cut_rows)}')
print('cut classes by kind:', collections.Counter(v for r in cut_rows for v in r['kind'].values()))
print('cases by kind (any):', collections.Counter(
    'ostium_misplaced' if 'ostium_misplaced' in r['kind'].values() else
    ('whole' if 'whole_class_unrooted_ostium_ok' in r['kind'].values() else 'partial') for r in cut_rows))
print('Atlas root misplaced (> 5 mm) in uncut cases:', sum(bool(r['bad_root']) for r in rows if not r['cut']),
      '/', sum(not r['cut'] for r in rows))
print('Atlas root misplaced, by side, all cases:',
      collections.Counter(s for r in rows for s in r['bad_root']))
print('segtrain thick-only ostia misplaced (> 5 mm), all cases:', sum(len(r['mine_bad']) for r in rows))
for r in sorted(cut_rows, key=lambda r: r['tf1']):
    print(r['case'], round(r['tf1'], 3), {k: round(v, 2) for k, v in r['cut'].items()}, r['kind'],
          {s: round(d, 1) for s, d in r['bad_root'].items()}, 'LM' if r['lm'] else 'noLM',
          'fp', r['fp'], 'orph', r['orphans'])


def fixed_tf1(r):
    """tF1 if every misplaced-ostium class scored its clDice (an upper bound on the artefact)."""
    x = val[r['case']]
    per = dict(x['tf1_per_class'])
    for k, kind in r['kind'].items():
        if kind == 'ostium_misplaced':
            kk = {v: k2 for k2, v in NAMES.items()}[k]
            per[kk] = x['cldice_per_class'][kk]
    return float(np.mean(list(per.values())))


print('macro tF1 as reported %.3f; with misplaced-ostium classes at their clDice (upper bound) %.3f'
      % (np.mean([r['tf1'] for r in rows]), np.mean([fixed_tf1(r) for r in rows])))
fp = np.array([r['fp'] for r in rows])
print('FP comps: mean %.2f, median %.0f, cases >1: %d, cases 0: %d' % (fp.mean(), np.median(fp),
                                                                       (fp > 1).sum(), (fp == 0).sum()))
print('orphans (pred comps touching ref beyond one per ref tree): mean %.2f, cases >0: %d'
      % (np.mean([max(r['orphans'], 0) for r in rows]), sum(r['orphans'] > 0 for r in rows)))
