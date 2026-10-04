"""Summarise pert_icx.jsonl (E3): per perturbation, mean over cases of each metric."""
import json
import sys
from collections import defaultdict

import numpy as np

rows = [json.loads(l) for l in open(sys.argv[1])]
K = ['dice', 'nsd05', 'cldice', 'macro_dice', 'class_cldice', 'beta0_err', 'class_comp_excess', 'seg_det',
     'rooted_recall', 'cl_label_acc', 'tf1']
by = defaultdict(list)
for r in rows:
    by[r['kind']].append(r)
cases = sorted({r['case'] for r in rows})
print('cases', cases)
print('kind'.ljust(12), 'n', ' '.join(k[:9].rjust(9) for k in K))
order = ['identity', 'erode1', 'dilate1', 'gaps5', 'gaps5_thick', 'drop_term30', 'thin_lost', 'fp5', 'carina5',
         'carina10', 'side_swap', 'd1_as_lcx', 'im_as_lad', 'lm_as_lad', 'islands']
for k in order:
    if k not in by:
        continue
    rs = by[k]
    vals = []
    for m in K:
        v = [r[m] for r in rs if r.get(m) is not None]
        vals.append(f'{np.mean(v):9.3f}' if v else ' ' * 9)
    print(k.ljust(12), len(rs), ' '.join(vals))
