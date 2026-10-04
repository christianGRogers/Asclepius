"""Summarise conv.jsonl (E2 + E7)."""
import json
import sys

import numpy as np

rows = [json.loads(l) for l in open(sys.argv[1])]
rows = [r for r in rows if 'error' not in r]
print('cases', len(rows))


def q(v):
    v = np.array([x for x in v if x is not None], float)
    return f'{np.median(v):.3f} [{np.quantile(v, .25):.3f}-{np.quantile(v, .75):.3f}] (min {v.min():.3f})'


for src in ('orig', 'icx'):
    print('==', src)
    for k in ('skel_len_mm', 'nseg3', 'nterm3', 'median_diam_mm', 'frac_lt3vox', 'frac_lt4vox', 'frac_lt6vox',
              'frac_lt1_5mm', 'frac_lt2mm', 'ncomp'):
        print(f'  {k}: {q([r[src][k] for r in rows])}')
    h = np.array([r[src]['len_by_diam_mm'] for r in rows]); h = h / h.sum(1, keepdims=True)
    print('  share of length by diameter bin [0-1,1-1.5,1.5-2,2-2.5,2.5-3,3-4,>4 mm] median:', np.median(h, 0).round(3))
print('== agreement (orig vs ICX)')
for k in ('dice', 'nsd05', 'nsd10', 'cldice', 'icx_skel_in_orig', 'orig_skel_in_icx', 'icx_skel_within1mm_orig',
          'orig_skel_within1mm_icx', 'icx_seg_found_in_orig', 'orig_seg_found_in_icx'):
    print(f'  {k}: {q([r[k] for r in rows])}')
vr = [r['orig']['skel_len_mm'] / r['icx']['skel_len_mm'] for r in rows]
print('  skeleton length ratio orig/icx', q(vr))
