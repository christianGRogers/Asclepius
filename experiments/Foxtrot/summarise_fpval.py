"""Summarise fp_roi_val.py output and check it against atlas2's per_case_run1.json. Usage: summarise_fpval.py fpval.jsonl"""
import json, sys
import numpy as np
P = {x['case']: x for x in json.load(open('/home/user/Asclepius/trillium-results/round6/atlas2/results/per_case_run1.json'))}
rows = [json.loads(l) for l in open(sys.argv[1])]
ok = [r for r in rows if 'error' not in r]
print('cases', len(rows), 'ok', len(ok), 'errors', [r['case'] for r in rows if 'error' in r])
mism = [(r['case'], r['before']['fp'], P[r['case']]['fp_components'], round(r['before']['tf1'] - P[r['case']]['tf1'], 6))
        for r in ok if r['before']['fp'] != P[r['case']]['fp_components'] or abs(r['before']['tf1'] - P[r['case']]['tf1']) > 1e-9]
print('reproduces atlas2 (fp and tF1 exact):', len(ok) - len(mism), '/', len(ok), 'mismatches', mism)
fp = [c for r in ok for c in r['comps'] if c['fp'] and c['voxels'] >= 0]
print('raw FP components (>=100 vox):', len(fp), 'categories', {k: sum(c.get('category') == k for c in fp) for k in set(c.get('category') for c in fp)})
d = np.array([c['min_roi_mm'] for c in fp])
print('FP min distance to heart∪aorta (mm): quantiles 10/25/50/75/90', np.percentile(d, [10, 25, 50, 75, 90]).round(1).tolist(), 'max', d.max())
print('FP beyond 25 mm:', int((d > 25).sum()), f'({(d > 25).mean():.1%})', '; beyond 15:', int((d > 15).sum()), '; beyond 10:', int((d > 10).sum()))
co = np.array([c['min_roi_mm'] for c in fp if c.get('category') == 'confident_other'])
print('confident_other n', len(co), 'quantiles', np.percentile(co, [10, 25, 50, 75, 90]).round(1).tolist(), 'max', co.max(),
      'bins <=0,0-5,5-10,10-15,15-25,>25:', np.histogram(co, [-1, 0.001, 5, 10, 15, 25, 1e9])[0].tolist())
print('reference max to ROI per case: max', max(r['ref_max_roi_mm'] for r in ok))
b = np.array([r['before']['fp'] for r in ok]); a = np.array([r['after']['fp'] for r in ok])
print('FP/case before', b.mean().round(3), 'after', a.mean().round(3), 'deleted comps', sum(r['deleted'] for r in ok),
      'deleted touching ref', sum(r['deleted_touching_ref'] for r in ok))
dt = np.array([r['after']['tf1'] - r['before']['tf1'] for r in ok])
dd = [ (r['after']['decisive'] or 0) - (r['before']['decisive'] or 0) for r in ok]
print('tF1 change: mean', dt.mean(), 'max |.|', np.abs(dt).max(), '; decisive change max |.|', max(abs(x) for x in dd))
print('heart vox min', min(r['heart_vox3mm'] for r in ok))
