"""Summarise br.jsonl (E10)."""
import json, sys
from collections import defaultdict
import numpy as np
rows = [json.loads(l) for f in sys.argv[1:] for l in open(f)]
last = {}
for r in rows:  # later files supersede earlier rows for the same case and gap
    last[(r['case'], r['gap'])] = r
rows = list(last.values())
by = defaultdict(list)
for r in rows:
    by[r['gap']].append(r)
print('cases', sorted({r['case'] for r in rows}))
print('gap  n  bridges  FPjoined  crossTree  tubeVox offRef   dice   tF1@0  tF1@1.5  rooted@0 rooted@1.5  FPcomp')
for g in sorted(by):
    rs = by[g]; br = [b for r in rs for b in r['bridges']]
    print(f"{g:4.1f} {len(rs):2d} {len(br):7d} {sum(not b['orphan_touches_ref'] for b in br):8d} {sum(b['cross_tree'] for b in br):9d}"
          f" {sum(r['tube_vox'] for r in rs):7d} {sum(r['tube_vox_off_ref'] for r in rs):6d}"
          f" {np.mean([r['dice'] for r in rs]):.3f}  {np.mean([r['tf1_0'] for r in rs]):.3f}  {np.mean([r['tf1_15'] for r in rs]):.3f}"
          f"    {np.mean([r['rooted_0'] for r in rs]):.3f}     {np.mean([r['rooted_15'] for r in rs]):.3f}   {np.mean([r['fp_components'] for r in rs]):.2f}")
print('per case tF1@1.5 by gap:')
for c in sorted({r['case'] for r in rows}):
    print(' ', c, [(r['gap'], round(r['tf1_15'], 3), r['n_bridges']) for r in rows if r['case'] == c])
