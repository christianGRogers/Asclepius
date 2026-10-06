"""Re-summarise evaluate.py output under the binding rules D1/D1b: ImageCAS-X IM (ramus) counted as LCx
(territory), 'Other' (D3/D4/OM3/OM4) still unscored. Splits dev (devset3) / held-out."""
import sys, json, numpy as np
f, devf = sys.argv[1], sys.argv[2]
dev = set(open(devf).read().replace('\n', '').split(','))
R = [json.loads(l) for l in open(f)]
for name, S in (('dev', [r for r in R if r['case'] in dev]), ('held-out', [r for r in R if r['case'] not in dev]), ('all', R)):
    S = [r for r in S if r.get('conf')]
    ds, ok, sw, pooled = [], [], [], np.zeros((5, 5))
    for r in S:
        C = np.array(r['conf'], float)
        C[3] += C[5]  # ramus -> LCx
        M = C[1:5, 1:5]; pooled[1:, 1:] += M
        d = {}
        for k in range(4):
            den = M[k].sum() + M[:, k].sum()
            if den > 0:
                d[k] = 2 * M[k, k] / den
        ds.append(d); ok.append(all(v >= 0.8 for v in d.values())); sw.append(any(v < 0.5 for v in d.values()))
    names = ['LM', 'LAD', 'LCx', 'RCA']
    print(f'{name}: n={len(S)}  all4>=0.8 {np.mean(ok):.3f}  swap(any<0.5) {np.mean(sw):.3f}  pooled acc {np.trace(pooled)/pooled.sum():.4f}  ' +
          ' '.join(f'{names[k]} {np.mean([x[k] for x in ds if k in x]):.3f}' for k in range(4)))
