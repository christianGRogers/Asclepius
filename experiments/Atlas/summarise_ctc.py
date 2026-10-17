"""Summarise ct_contrast.py output."""
import json, sys, numpy as np
R = [json.loads(l) for l in open(sys.argv[1])]
seen = {}; [seen.setdefault(r['case'], r) for r in R]; R = list(seen.values())
print('cases', len(R), [r['case'] for r in R])
bins = list(R[0]['contrast_native'])
for b in bins:
    n = sum(r['contrast_native'][b][0] for r in R)
    out = []
    for t in ['0.5', '0.7']:
        rat = [r['contrast_' + t][b][1] / r['contrast_native'][b][1] for r in R if r['contrast_native'][b][1]]
        out.append(f'{t}: retention mean {np.mean(rat):.3f} min {np.min(rat):.3f}')
    nat = np.mean([r['contrast_native'][b][1] for r in R if r['contrast_native'][b][1]])
    print(f'EDT bin {b} mm: pts {n}, native contrast {nat:.0f} HU |', ' | '.join(out))
for t in ['0.5', '0.7']:
    rat = [r['noise_' + t] / r['noise_native'] for r in R]
    print('noise ratio', t, np.round(np.mean(rat), 3))
for c in ['LM', 'LAD', 'LCx', 'RCA']:
    print(c, ' '.join(f"{t}:{np.mean([r['contrast_by_class_'+t][c]/r['contrast_by_class_native'][c] for r in R if r['contrast_by_class_native'][c]]):.3f}" for t in ['0.5','0.7']))
print('in-plane spacing of cases', sorted(round(r['sp'][0], 3) for r in R))
