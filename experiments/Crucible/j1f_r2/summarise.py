"""Summarise census620.jsonl (items 2, 4, 10). Usage: summarise.py <census620.jsonl>"""
import json, sys
import numpy as np

R = [json.loads(l) for l in open(sys.argv[1])]
n = len(R)
BR = ['D1', 'D2', 'D3', 'OM1', 'OM2', 'Ramus', 'PDA', 'PLB']
print(f'cases {n}')

# --- label map and collapse (F-A3, F-A4 under D47 Q1 (A))
m = {k: sum(r['map'][k] for r in R) for k in R[0]['map']}
print('map totals', m, '| cases with ignore', sum(r['ignore_voxels'] > 0 for r in R))
print('collapse4(1-F) != territory.to_four outside Other: voxels', sum(r['collapse_mismatch'] for r in R),
      'cases', sum(r['collapse_mismatch'] > 0 for r in R), '| inside Other: voxels',
      sum(r['collapse_mismatch_other'] for r in R), 'cases', sum(r['collapse_mismatch_other'] > 0 for r in R))

# --- branches (item 2): pieces at 5 mm, pieces 3-5 mm, presence at 3 vs 5 mm
print('\nclass | cases with >=1 piece >=5mm | pieces>=5mm | cases with 2+ pieces | pieces 3-5mm | cases present@3 not @5 '
      '| median piece mm | p10 piece mm')
for c in BR:
    p5 = [r['pieces5'][c] for r in R]
    p3 = [r['pieces3'][c] for r in R]
    L = np.array([x for v in p5 for x in v]) if any(p5) else np.array([0.0])
    pres5 = np.array([r['class_mm'][c] >= 5 for r in R])
    pres3 = np.array([r['class_mm'][c] >= 3 for r in R])
    print(f"{c} | {sum(bool(v) for v in p5)} | {sum(len(v) for v in p5)} | {sum(len(v) >= 2 for v in p5)} | "
          f"{sum(len(a) - len(b) for a, b in zip(p3, p5))} | {int((pres3 & ~pres5).sum())} | "
          f"{np.median(L):.1f} | {np.percentile(L, 10):.1f}")
# pieces present but under 5 mm (class drawn but no scorable branch)
for c in BR:
    k = sum((r['class_mm'][c] > 0) and not r['pieces5'][c] for r in R)
    if k:
        print(f'  {c}: {k} cases with the class drawn but no piece >= 5 mm')

# --- self-score and perturbations
S = [r for r in R if r.get('score', {}).get('self')]
print(f'\nself-score and perturbations on {len(S)} cases')
for kind in ('self', 'swapD', 'dropOM2', 'PDAasRCA'):
    tot = {c: np.sum([r['score'][kind]['dn'][c] for r in S], 0) for c in BR}
    pa = {c: np.mean([r['score'][kind]['pres_agree'][c] for r in S]) for c in BR}
    line = ' '.join(f"{c}:det {t[1]}/{t[0]} name {t[2]}/{max(t[1], 1)} pres {pa[c]:.2f}" for c, t in tot.items() if t[0])
    print(kind, line)
    if 'tf1' in S[0]['score'][kind]:
        tf = {c: [r['score'][kind]['tf1'][c] for r in S if r['score'][kind]['tf1'][c] is not None]
              for c in S[0]['score'][kind]['tf1']}
        print('   branch tF1', {c: (round(float(np.mean(v)), 4), len(v)) for c, v in tf.items()})

# --- bands (item 4)
print('\nbackground released by the band (mm^3, median [p10, p90] over cases) and per mm^3 of traced tree')
tree = np.array([r['bands']['tree_mm3'] for r in R])
print('tree mm3 median', np.median(tree))
for b in ('8', '15'):
    for h in ('LADtree', 'RCA', 'proxRCA', 'proxLCx', 'LADtree&RCA', 'union'):
        v = np.array([r['bands'][b].get(h, 0.0) for r in R])
        print(f'  {b} mm {h:12s} {np.median(v):9.0f} [{np.percentile(v, 10):.0f}, {np.percentile(v, 90):.0f}]'
              f'  x tree {np.median(v / tree):.1f}')

# --- twigs (item 10)
print('\ntrunk twigs (unnamed branch >= L mm inside a trunk class, trunk end excluded): cases, share of cases')
E = [r for r in R if 'twigs' in r]
print('cases with twig census', len(E), 'errors', sum('twigs_error' in r for r in R))
for t in ('LAD', 'LCx', 'RCA'):
    for L in (3, 5, 10):
        k = sum(any(x >= L for x in r['twigs'].get(t, [])) for r in E)
        tot = sum(sum(x >= L for x in r['twigs'].get(t, [])) for r in E)
        print(f'  {t} >= {L} mm: {k} cases ({100 * k / max(len(E), 1):.1f} %), {tot} twigs')

# --- dominance (item 10): by labels
lp = sum((r['class_mm']['PDA'] > 0 or r['class_mm']['PLB'] > 0) for r in R)
print('\ncases with any PDA/PLB label', lp)
