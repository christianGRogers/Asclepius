"""Summarise ost.jsonl (E9): distance from each ImageCAS-X start point to the rule's ostium."""
import json, sys
import numpy as np
rows = [json.loads(l) for l in open(sys.argv[1])]
err = [r for r in rows if 'error' in r]
rows = [r for r in rows if 'error' not in r]
print('cases', len(rows), 'errors', len(err), [e['case'] for e in err][:5])
for side in ('left', 'right'):
    rs = [r[side] for r in rows if side in r]
    print(f'== {side}: {len(rs)} trees, true start points {sum(x["n_true"] for x in rs)}')
    for rule in ('thick', 'pool_nearest', 'pool_thick', 'aorta5', 'aorta_nearest'):
        d = [v for x in rs if x.get(rule) for v in x[rule]]
        missing = sum(x['n_true'] for x in rs if not x.get(rule))
        if not d:
            continue
        d = np.array(d)
        print(f'  {rule:14s} n={len(d):3d} (+{missing} no candidate)  <=2mm {np.mean(d <= 2):.3f}  <=5mm {np.mean(d <= 5):.3f}'
              f'  median {np.median(d):.2f} mm  p90 {np.quantile(d, .9):.1f}  max {d.max():.1f}')
multi = [r['case'] for r in rows if r.get('left', {}).get('n_true', 0) > 1]
print('left trees with >1 true start (separate LAD/LCx ostia):', multi)
