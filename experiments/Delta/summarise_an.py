"""Summarise an.jsonl (E8)."""
import json
import sys
from collections import defaultdict

import numpy as np

rows = [json.loads(l) for f in sys.argv[1:] for l in open(f)]
last = {}
for r in rows:  # a case/variant re-analysed later supersedes the earlier row
    last[(r['case'], r['variant'])] = r
rows = sorted(last.values(), key=lambda r: r['case'])
by = defaultdict(list)
for r in rows:
    by[r['variant']].append(r)
print('cases', sorted({r['case'] for r in rows}))
K = ['dice', 'nsd05', 'cldice', 'macro_dice', 'class_cldice', 'beta0_err', 'ncomp', 'seg_det', 'rooted_recall',
     'tf1', 'rooted_tol1.5', 'tf1_tol1.5', 'rooted_tol3.0', 'tf1_tol3.0', 'fp_components']
print('variant', ' '.join(k[:8].rjust(8) for k in K))
for v in ('t50', 't30', 'hyst20', 'hyst10'):
    rs = by[v]
    print(v.ljust(7), ' '.join(f'{np.mean([r[k] for r in rs if k in r]):8.3f}' if any(k in r for r in rs) else '     n/a' for k in K))
print('\nper case t50 / hyst10:')
for r50, r10 in zip(by['t50'], by['hyst10']):
    print(r50['case'], 'ncomp_gt', r50['ncomp_gt'], 'ncomp', r50['ncomp'], '->', r10['ncomp'],
          'rooted %.3f -> %.3f' % (r50['rooted_recall'], r10['rooted_recall']),
          'tf1 %.3f -> %.3f' % (r50['tf1'], r10['tf1']), 'dice %.3f -> %.3f' % (r50['dice'], r10['dice']),
          'class rooted', {k: round(x, 3) for k, x in r50['class_rooted_recall'].items()})
print('\nmissed stretches at t50 (all cases):')
ms = [m for r in by['t50'] for m in r['missed']]
inter = [m for m in ms if m['interior']]
ends = [m for m in ms if m['touches_end']]
tot = sum(m['len_mm'] for m in ms)
print(f'  total missed centreline {tot:.1f} mm in {len(ms)} stretches;'
      f' interior gaps {len(inter)} ({sum(m["len_mm"] for m in inter):.1f} mm),'
      f' distal truncations {len(ends)} ({sum(m["len_mm"] for m in ends):.1f} mm)')
for name, grp in (('interior', inter), ('distal', ends)):
    if not grp:
        continue
    L = np.array([m['len_mm'] for m in grp]); D = np.array([m['med_diam_mm'] for m in grp])
    P = np.array([m['max_prob'] for m in grp])
    w = L / L.sum()
    print(f'  {name}: length mm median {np.median(L):.1f} max {L.max():.1f}; ref diameter (EDT) median {np.median(D):.2f} mm;'
          f' max prob along stretch: <0.1 in {(P < 0.1).sum()}, 0.1-0.5 in {((P >= 0.1) & (P < 0.5)).sum()}, >=0.5 in {(P >= 0.5).sum()}'
          f'  (length-weighted share with max prob >= 0.1: {w[P >= 0.1].sum():.2f})')
    print('   ', [(round(m['len_mm'], 1), round(m['med_diam_mm'], 2), round(m['max_prob'], 3), m['cls']) for m in
                  sorted(grp, key=lambda m: -m['len_mm'])[:12]])
cls_len = defaultdict(float)
for m in ms:
    cls_len[m['cls']] += m['len_mm']
print('  missed length by class', dict(cls_len))
