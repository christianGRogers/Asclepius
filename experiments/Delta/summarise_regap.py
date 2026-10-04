"""Summarise regap.jsonl (E11): first pass vs gap-centred re-inference, +/- 3 mm bridging."""
import json, sys
import numpy as np
last = {}
for l in open(sys.argv[1]):
    r = json.loads(l); last[r['case']] = r
rows = [last[c] for c in sorted(last)]
V = ['first', 'regap_mean', 'regap_max', 'first+bridge3', 'regap_mean+bridge3', 'regap_max+bridge3']
print('cases', len(rows), [r['case'] for r in rows], 'anchor', {r['case']: r['anchor_kind'] for r in rows})
print('sites per case', [r['n_sites'] for r in rows], 'mean seconds', np.mean([r['seconds'] for r in rows]).round())
print('variant              dice   tF1@0  tF1@1.5 rooted@1.5  FPcomp  ncomp')
for v in V:
    g = lambda k: np.mean([r[v][k] for r in rows])
    print(f'{v:20s} {g("dice"):.3f}  {g("tf1_0"):.3f}  {g("tf1_15"):.3f}   {g("rooted_15"):.3f}    {g("fp_components"):.2f}   {g("ncomp"):.2f}')
d = np.array([r['regap_max+bridge3']['tf1_15'] - r['first']['tf1_15'] for r in rows])
d2 = np.array([r['regap_max']['tf1_15'] - r['first']['tf1_15'] for r in rows])
print('per-case delta tF1@1.5 regap_max+bridge3 - first:', d.round(3), 'mean %.3f' % d.mean(), 'worse in', (d < -0.001).sum())
print('per-case delta tF1@1.5 regap_max - first:', d2.round(3), 'mean %.3f' % d2.mean())
rng = np.random.default_rng(0)
bs = [rng.choice(d, len(d)).mean() for _ in range(10000)]
print('bootstrap 95%% CI of mean delta (regap_max+bridge3): [%.3f, %.3f]' % tuple(np.quantile(bs, [.025, .975])))
for r in rows:
    print(' ', r['case'], 'first %.3f -> regap_max %.3f -> +bridge3 %.3f  fp %d->%d' % (
        r['first']['tf1_15'], r['regap_max']['tf1_15'], r['regap_max+bridge3']['tf1_15'],
        r['first']['fp_components'], r['regap_max+bridge3']['fp_components']))
