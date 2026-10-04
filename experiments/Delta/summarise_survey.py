"""Summarise survey_*.jsonl (E1): spacing, connectivity, ROI size."""
import glob
import json
import sys

import numpy as np

W = sys.argv[1]
rows = [json.loads(l) for f in sorted(glob.glob(W + '/survey_*.jsonl')) for l in open(f)]
rows = [r for r in rows if 'error' not in r]
print('cases', len(rows))
sp = np.array([r['spacing'] for r in rows]); sh = np.array([r['shape'] for r in rows])
print('inplane spacing min/med/max', sp[:, 0].min(), np.median(sp[:, 0]), sp[:, 0].max())
print('z spacing values', dict(zip(*np.unique(sp[:, 2].round(3), return_counts=True))))
print('z slices min/med/max', sh[:, 2].min(), np.median(sh[:, 2]), sh[:, 2].max(),
      'xy shapes', set(map(tuple, sh[:, :2].tolist())))
print('axcodes', dict(zip(*np.unique([r['axcodes'] for r in rows], return_counts=True))))
print('dtype', set(r['dtype'] for r in rows))
nc = np.array([r['ncomp'] for r in rows])
print('ncomp distribution', dict(zip(*np.unique(nc, return_counts=True))))
# component size structure
small = []
third = []
for r in rows:
    s = [c['size'] for c in r['comps']]
    third.append(s[2] if len(s) > 2 else 0)
    small += s[2:]
third = np.array(third)
print('cases with a 3rd component', (third > 0).sum(), ' 3rd comp size voxels: median', np.median(third[third > 0]) if (third > 0).any() else None,
      ' >=1000 vox:', (third >= 1000).sum(), ' >=100:', (third >= 100).sum(), ' <100:', ((third > 0) & (third < 100)).sum())
two = np.array([r['comps'][1]['size'] / r['comps'][0]['size'] if len(r['comps']) > 1 else 0 for r in rows])
print('size ratio 2nd/1st comp: quantiles', np.quantile(two, [0, .05, .25, .5, .75, 1]).round(3))
print('cases with 1 component', (nc == 1).sum())
fg = np.array([r['fg'] for r in rows]); vol = sh.prod(1)
print('fg fraction of volume median %.5f  min %.5f max %.5f' % (np.median(fg / vol), (fg / vol).min(), (fg / vol).max()))
ext = np.array([r['tree_ext_mm'] for r in rows])
print('tree extent mm (x,y,z) median', np.median(ext, 0).round(1), ' p95', np.quantile(ext, .95, 0).round(1), ' max', ext.max(0).round(1))
for m in ('0', '10', '20'):
    fr = np.array([r['roi'][m]['frac'] for r in rows]); vx = np.array([np.prod(r['roi'][m]['vox']) for r in rows])
    print(f'ROI margin {m} mm: frac of volume median {np.median(fr):.3f} p95 {np.quantile(fr, .95):.3f} max {fr.max():.3f};'
          f' Mvox median {np.median(vx) / 1e6:.1f} p95 {np.quantile(vx, .95) / 1e6:.1f}; 256^3 patches to tile (no overlap) median'
          f' {np.median(vx / 256 ** 3):.2f}')
print('full volume Mvox median', np.median(vol) / 1e6, ' 256^3/vol median', np.median(256 ** 3 / vol).round(3))
# tree position: bbox touching the volume edge?
edge = sum(any(lo == 0 for lo in r['tree_lo']) or any(hi == s for hi, s in zip(r['tree_hi'], r['shape'])) for r in rows)
print('tree bbox touching a volume face', edge)
zlo = np.array([r['tree_lo'][2] for r in rows]); zhi = np.array([r['tree_hi'][2] for r in rows])
print('tree touches z=0 face', (zlo == 0).sum(), ' top face', (zhi == sh[:, 2]).sum())
