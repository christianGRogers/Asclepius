"""Summarise icx_topo.jsonl (E6)."""
import json
import sys

import numpy as np

rows = [json.loads(l) for l in open(sys.argv[1])]
rows = [r for r in rows if 'error' not in r]
n = len(rows)
print('cases', n)
lc = np.array([r['lumen_ncomp'] for r in rows])
print('ICX lumen components', dict(zip(*np.unique(lc, return_counts=True))))
third = [r['lumen_sizes'][2] for r in rows if len(r['lumen_sizes']) > 2]
print('3rd lumen comp sizes: n', len(third), 'median', np.median(third) if third else None,
      '>=100', sum(t >= 100 for t in third))
names = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA'}
for conv in ('subtree', 'trunk'):
    print('==', conv)
    for c in (1, 2, 3, 4):
        k = str(c)
        pres = [r[conv][k]['vox'] > 0 for r in rows]
        nc = np.array([r[conv][k]['ncomp'] for r in rows if r[conv][k]['vox'] > 0])
        # pieces >= 20 voxels
        nc20 = np.array([sum(s >= 20 for s in r[conv][k]['sizes']) for r in rows if r[conv][k]['vox'] > 0])
        frac2 = [r[conv][k]['sizes'][1] / r[conv][k]['vox'] for r in rows if r[conv][k]['ncomp'] > 1]
        print(f'{names[c]}: present {sum(pres)}/{n}; ncomp==1 in {(nc == 1).sum()}/{len(nc)}; '
              f'>1 piece (any size) {(nc > 1).sum()}, >1 piece >=20vox {(nc20 > 1).sum()}; '
              f'2nd piece share median {np.median(frac2) if frac2 else 0:.3f}')
    for key in ('lad_lm', 'lcx_lm', 'lad_lcx', 'rca_left'):
        v = [r[conv][key] for r in rows]
        print(f'  {key}: True {sum(x is True for x in v)}, False {sum(x is False for x in v)}, n/a {sum(x is None for x in v)}')
lm_absent = [r['case'] for r in rows if r['trunk']['1']['vox'] == 0]
print('LM absent:', len(lm_absent), lm_absent[:10])
im = sum(8 in r['raw_present'] for r in rows); print('IM present', im, '/', n)
oth = sum(14 in r['raw_present'] for r in rows); print('Other(14) present', oth)
lpd = sum((12 in r['raw_present']) or (13 in r['raw_present']) for r in rows); print('L-PDA/L-PLA present', lpd)
# share of left-tree voxels that are side branches (subtree minus trunk)
for c in (2, 3, 4):
    sh = [1 - r['trunk'][str(c)]['vox'] / r['subtree'][str(c)]['vox'] for r in rows if r['subtree'][str(c)]['vox'] > 0]
    print(f'{names[c]} side-branch share of subtree voxels: median {np.median(sh):.3f} IQR {np.quantile(sh, .25):.3f}-{np.quantile(sh, .75):.3f}')
