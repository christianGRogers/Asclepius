# Summarise r2_eval logs: per run mean tF1@0/1.5, recall, precision, class clDice, binary Dice, comps, FP comps, cuts;
# paired per-case differences with bootstrap 95% CI for chosen pairs.
import json, sys, numpy as np
rows = [json.loads(l) for f in sys.argv[1:] for l in open(f) if l.startswith('{')]
runs = sorted({r['run'] for r in rows}, key=lambda x: [r['run'] for r in rows].index(x))
K = ['tf1@0.0', 'tf1@1.5', 'rec@1.5', 'prec', 'class_cldice', 'rec_unrooted', 'dice_bin', 'vol_ratio', 'ncomp', 'fp_comp']
print('run n ' + ' '.join(K) + ' cuts')
by = {}
for u in runs:
    R = [r for r in rows if r['run'] == u]; by[u] = {r['case']: r for r in R}
    print(u, len(R), ' '.join(f"{np.mean([r[k] for r in R]):.3f}" for k in K), sum(r['cut'] for r in R))
    for c in (1, 2, 3, 4):
        v = [r['perclass@1.5'].get(str(c)) for r in R if str(c) in r['perclass@1.5']]
        print('   class', c, f'{np.mean(v):.3f}', end='')
    print()
rng = np.random.default_rng(0)
for a, b in [('thin4_s0', 'thick4_s0'), ('thin14_s0', 'thin4_s0')]:
    if a in by and b in by:
        cs = sorted(set(by[a]) & set(by[b]))
        for k in ('tf1@1.5', 'tf1@0.0', 'prec', 'rec@1.5'):
            d = np.array([by[a][c][k] - by[b][c][k] for c in cs])
            bs = [rng.choice(d, len(d)).mean() for _ in range(5000)]
            print(f'{a} - {b} {k}: mean {d.mean():+.3f} CI [{np.percentile(bs,2.5):+.3f}, {np.percentile(bs,97.5):+.3f}] wins {int((d>0).sum())}/{len(d)}')
