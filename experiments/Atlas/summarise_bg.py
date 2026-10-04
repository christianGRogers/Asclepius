"""Summarise branch_geometry.py output: label resampling round-trip Dice and centreline EDT (calibre) per class."""
import json, sys, numpy as np
R = [json.loads(l) for l in open(sys.argv[1])]
print('cases', len(R))
for t in ['0.5', '0.8']:
    for c in ['LM', 'LAD', 'LCx', 'RCA']:
        v = np.array([r['rt_dice'][t][c] for r in R if c in r['rt_dice'].get(t, {})])
        print(f'roundtrip {t} mm {c:4s} mean {v.mean():.4f} p5 {np.percentile(v,5):.4f} min {v.min():.4f} (n={len(v)})')
sp = np.array([r['sp'][0] for r in R]); lad = np.array([r['rt_dice']['0.5']['LAD'] for r in R])
print('corr(in-plane spacing, 0.5 roundtrip LAD Dice) = %.2f' % np.corrcoef(sp, lad)[0, 1], ' finest-spacing cases:', [(round(a,3), round(b,4)) for a, b in sorted(zip(sp, lad))[:3]])
for c in ['LM', 'LAD', 'LCx', 'RCA', 'side']:
    v = np.concatenate([r['radius_mm'][c] for r in R])
    print(f'centreline EDT {c:5s} n={len(v):6d} p5 {np.percentile(v,5):.2f} p10 {np.percentile(v,10):.2f} p25 {np.percentile(v,25):.2f} median {np.median(v):.2f} p90 {np.percentile(v,90):.2f} mm;'
          f' frac EDT<0.75mm {np.mean(v<0.75):.2f}')
