"""Summarise census.jsonl (620 D45 training cases) into the tables of the round-1 note. Usage: summarise.py <census.jsonl>"""
import json, sys
from collections import Counter
import numpy as np

NAMES = [None, 'LM', 'LAD', 'LCx', 'D1', 'D2', 'OM1', 'OM2', 'IM', 'RCA', 'R-PDA', 'R-PLA', 'L-PDA', 'L-PLA', 'Other']
R = [json.loads(l) for l in open(sys.argv[1])]
n = len(R)
print(f'cases: {n}; spacing: {Counter(tuple(r["spacing"]) for r in R).most_common(3)}')
print('\n| Class | cases (>= 10 vox) | median mm3 where present | median centreline mm | radius p50 (median of cases) | '
      'share of skeleton points with r < 0.5 mm |')
print('|---|---|---|---|---|---|')
for c in range(1, 15):
    pres = [r for r in R if r['voxels'][c] >= 10]
    mm3 = np.median([r['mm3'][c] for r in pres]) if pres else 0
    L = np.median([r['length_mm'].get(str(c), 0) for r in pres]) if pres else 0
    p50 = np.median([r['radius_mm'][str(c)]['p50'] for r in pres if str(c) in r['radius_mm']]) if pres else 0
    # pooled share of thin skeleton points: approximate from per-case p10/p50 is not enough; use p10 < 0.5 count
    thin = np.mean([r['radius_mm'][str(c)]['p10'] < 0.5 for r in pres if str(c) in r['radius_mm']]) if pres else 0
    print(f'| {NAMES[c]} | {len(pres)} ({len(pres)/n:.1%}) | {mm3:.0f} | {L:.0f} | {p50:.2f} | p10 < 0.5 mm in {thin:.0%} of cases |')

print('\n## Dominance (ImageCAS-X naming)')
has = lambda r, c: r['voxels'][c] >= 10
lp = [r for r in R if has(r, 12) or has(r, 13)]
both = [r for r in R if (has(r, 12) or has(r, 13)) and (has(r, 10) or has(r, 11))]
none = [r for r in R if not any(has(r, c) for c in (10, 11, 12, 13))]
print(f'L-PDA or L-PLA: {len(lp)} ({len(lp)/n:.1%}); L-PDA {sum(has(r,12) for r in R)}, L-PLA {sum(has(r,13) for r in R)}; '
      f'with an R-PDA/R-PLA too: {len(both)}; no PDA/PLA of either side: {len(none)}')
lcx_terr = lambda r: sum(r['mm3'][c] for c in (3, 6, 7, 8, 12, 13))
share = [(r['mm3'][12] + r['mm3'][13]) / lcx_terr(r) for r in lp if lcx_terr(r) > 0]
print(f'L-PDA+L-PLA share of the D25 LCx territory (excl. Other) in those cases: median {np.median(share):.3f}, '
      f'p90 {np.percentile(share, 90):.3f}, max {max(share):.3f}')

print('\n## Other pieces (>= 10 voxels)')
fam = Counter(); dcount = Counter(); cases_other = 0
for r in R:
    ps = r['other_pieces']
    if ps:
        cases_other += 1
    for p in ps:
        fam[p['family']] += 1
    dcount[sum(p['family'] == 'D' for p in ps)] += 1
print(f'cases with Other: {cases_other}; pieces by family: {dict(fam)}')
print(f'D-family pieces per case: {dict(sorted(dcount.items()))}  (D-family = touches LAD/D1/D2 only)')
dcases = [r for r in R if any(p['family'] == 'D' for p in r['other_pieces'])]
print(f'cases with >= 1 D-family piece (a traced D3 or later diagonal): {len(dcases)} ({len(dcases)/n:.1%}); '
      f'of which also D2 present: {sum(has(r,5) for r in dcases)}; touching D1/D2 rather than LAD: '
      f'{sum(any(p["family"]=="D" and 2 not in p["touch"] for p in r["other_pieces"]) for r in dcases)}')
print(f'cases with D1: {sum(has(r,4) for r in R)}, D2: {sum(has(r,5) for r in R)}, OM1: {sum(has(r,6) for r in R)}, '
      f'OM2: {sum(has(r,7) for r in R)}, IM: {sum(has(r,8) for r in R)}')

print('\n## Unnamed branches >= 5 mm inside trunk classes (after removing the trunk end, one per class)')
for c, k in (('2', 1), ('3', 1), ('9', 1)):
    cnt = [max(len(r['twigs_mm'].get(c, [])) - k, 0) for r in R]
    lens = [L for r in R for L in sorted(r['twigs_mm'].get(c, []), reverse=True)[k:]]
    tot = [r['length_mm'].get(c, 0) for r in R]
    extra = [sum(sorted(r['twigs_mm'].get(c, []), reverse=True)[k:]) for r in R]
    print(f'{NAMES[int(c)]}: cases with >= 1: {sum(x > 0 for x in cnt)} ({np.mean([x>0 for x in cnt]):.1%}); per case mean '
          f'{np.mean(cnt):.2f}, max {max(cnt)}; twig length median {np.median(lens) if lens else 0:.1f} mm; '
          f'share of the class centreline in such twigs: {sum(extra)/sum(tot):.3f}')
errs = [r['case'] for r in R if 'skeleton_error' in r]
print(f'\nskeleton errors: {len(errs)} {errs[:5]}')
print('\nraw terminal trunk-class branches >= 5 mm per case (before removing the trunk end):')
for c in ('2', '3', '9'):
    print(NAMES[int(c)], dict(sorted(Counter(len(r['twigs_mm'].get(c, [])) for r in R).items())))
