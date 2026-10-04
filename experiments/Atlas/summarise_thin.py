"""Summarise thin_roundtrip_tf1.py output."""
import json, sys, numpy as np
R = {}
for l in open(sys.argv[1]):
    r = json.loads(l); R[r['case']] = r
R = list(R.values()); print('cases', len(R))
for t in ('0.5', '0.8'):
    for k in ('tf1', 'tf1_rec', 'rooted_recall', 'class_cldice', 'macro_dice', 'swap_rate'):
        v = np.array([r[t][k] for r in R]); print(f'{t} {k:14s} mean {v.mean():.4f} min {v.min():.4f}')
    b = np.array([r[t]['beta0_err'] for r in R]); ex = np.array([r[t]['class_comp_excess'] for r in R])
    print(f'{t} beta0_err mean {b.mean():.2f} max {b.max()}  class_comp_excess mean {ex.mean():.2f} max {ex.max()}  cases tF1<0.99: {sum(r[t]["tf1"]<0.99 for r in R)}')
print('spacings', sorted(round(r['sp'][0], 3) for r in R))
