"""Summarise extent_sampling.py output (es.jsonl)."""
import json, sys, numpy as np
R = [json.loads(l) for l in open(sys.argv[1])]
print('cases', len(R))
NAMES = ['LM', 'LAD', 'LCx', 'RCA']
pres = {c: np.mean([r['vox'][c] > 0 for r in R]) for c in NAMES}
print('presence', {c: round(v, 3) for c, v in pres.items()})
for c in NAMES + ['left_trunk']:
    v = np.array([r['vox'][c] for r in R if r['vox'][c] > 0]) * np.array([np.prod(r['sp']) for r in R if r['vox'][c] > 0])
    print(f'{c:10s} volume mm3 median {np.median(v):.0f} p10 {np.percentile(v,10):.0f} p90 {np.percentile(v,90):.0f}')
tot = np.array([sum(r['vox'][c] for c in NAMES) for r in R])
for c in NAMES: print(c, 'share of 4-class fg %.3f' % np.mean([r['vox'][c] / t for r, t in zip(R, tot)]))
print('fg fraction of volume (4 classes) median %.5f' % np.median(tot / np.array([np.prod(r['shape']) for r in R])))
for k in ['all', 'left', 'right', 'LAD', 'LCx', 'RCA']:
    e = np.array([r['ext_mm'][k] for r in R if r['ext_mm'][k]])
    print(f'extent {k:6s} x/y/z mm median', np.round(np.median(e, 0), 1), 'p90', np.round(np.percentile(e, 90, 0), 1), 'p100', np.round(e.max(0), 1))
for pn in R[0]['samp']:
    S = [r['samp'][pn] for r in R if r['samp'][pn]]
    fits = {k: np.mean([s['fits'][k] for s in S if s['fits'][k] is not None]) for k in ['LAD', 'LCx', 'RCA', 'left', 'right', 'all']}
    best = {k: np.mean([s['best_frac'][k] for s in S if s['best_frac'][k] is not None]) for k in ['left', 'right', 'all']}
    prand = {k: np.mean([s['p_contains_random'][k] for s in S]) for k in NAMES}
    anc = {a: {b: round(np.mean([s['p_contains_anchored'][a][b] for s in S if a in s['p_contains_anchored']]), 3) for b in NAMES} for a in NAMES}
    print(pn, 'n', len(S)); print('  fits(frac cases)', {k: round(v, 3) for k, v in fits.items()})
    print('  best-patch fraction of tree', {k: round(v, 3) for k, v in best.items()})
    print('  P(random patch contains)', {k: round(v, 3) for k, v in prand.items()})
    print('  anchored on row, contains col', anc)
