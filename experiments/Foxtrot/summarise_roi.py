"""Summarise heart_roi_ref.py output: how much of the ImageCAS reference lies beyond a heart+aorta ROI dilated by d mm,
and how many reference components a component-level ROI rule (delete a component whose every voxel is > d mm from the ROI)
would delete. Usage: python3 summarise_roi.py roi.jsonl"""
import json, sys
import numpy as np
rows = [json.loads(l) for l in open(sys.argv[1])]
ok = [r for r in rows if 'error' not in r]
print('cases', len(rows), 'ok', len(ok), 'errors', [r['case'] for r in rows if 'error' in r])
mx = np.array([r['max_d'] for r in ok]); p99 = np.array([r['p99_d'] for r in ok])
print('max distance of any reference voxel to ROI (mm): median %.1f, p90 %.1f, max %.1f' % (np.median(mx), np.percentile(mx, 90), mx.max()))
print('per-case p99 distance: median %.1f, max %.1f' % (np.median(p99), p99.max()))
for t in ('0', '5', '10', '15', '20'):
    fr = np.array([r['frac_vox_beyond'][t] for r in ok]); n = sum(r['vox_beyond'][t] > 0 for r in ok)
    print(f'beyond {t:>2} mm: cases with any voxel {n}/{len(ok)}; voxel fraction median {np.median(fr):.4f}, max {fr.max():.4f}, pooled {sum(r["vox_beyond"][t] for r in ok)/sum(r["n_ref_vox"] for r in ok):.5f}')
print('reference components per case: median', np.median([r['n_comp'] for r in ok]), 'max', max(r['n_comp'] for r in ok))
for d in (5, 10, 15, 20, 25):
    dele = [(r['case'], c['size']) for r in ok for c in r['comps'] if c['min_d'] > d]
    print(f'component rule d={d:>2} mm: deletes {len(dele)} reference components in {len(set(x[0] for x in dele))} cases; voxels {sum(x[1] for x in dele)}; sizes {sorted(x[1] for x in dele)[-8:]}')
far = sorted(((r['max_d'], r['case']) for r in ok), reverse=True)[:8]
print('cases with the farthest reference voxel:', [(c, round(m, 1)) for m, c in far])
small = [r['case'] for r in ok if r['heart_vox3mm'] < 5000]
print('cases with a suspiciously small heart mask (<5000 3-mm voxels):', small)
