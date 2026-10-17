"""Upper bound, for all 80 val cases, on the share of raw FP components that the A20 rule (d = 25 mm) could remove,
from atlas2's census alone (no heart mask needed).
A component can lie > d from heart ∪ aorta only if (a) dist_to_aorta > d (the aorta is part of the ROI) and
(b) dist_to_ref > d − R, where R bounds the reference-to-ROI distance (triangle inequality: for an FP voxel v and the
nearest reference voxel r, dist(v, ROI) <= |v − r| + dist(r, ROI) <= dist_to_ref + R). R = 16.5 mm is the maximum over the
92 non-sealed cases measured (an assumption for val cases not measured). Usage: fp_roi_bound.py census.json ..."""
import json, sys
import numpy as np
D, R = 25.0, 16.5
for fn in sys.argv[1:]:
    rows = json.load(open(fn))
    def can(r, R=R):
        return r.get('dist_to_aorta_mm', np.inf) > D and r['dist_to_ref_mm'] > D - R
    for cat in (None, 'confident_other'):
        rs = [r for r in rows if cat is None or r['category'] == cat]
        k = sum(can(r) for r in rs)
        print(f'{fn.split("/")[-1]} {cat or "all"}: n={len(rs)}; could be > {D} mm (upper bound): {k} ({k/len(rs):.1%}); '
              f'dist_to_aorta > {D}: {sum(r.get("dist_to_aorta_mm", np.inf) > D for r in rs)}; '
              f'dist_to_ref > {D-R}: {sum(r["dist_to_ref_mm"] > D-R for r in rs)}')
    co = [r for r in rows if r['category'] == 'confident_other']
    for key in ('dist_to_ref_mm', 'dist_to_aorta_mm'):
        a = np.array([r[key] for r in co])
        print(f'  confident_other {key}: quantiles 10/25/50/75/90 = {np.percentile(a, [10, 25, 50, 75, 90]).round(1).tolist()}, max {a.max():.1f}')
    a = np.array([r['dist_to_ref_mm'] for r in co])
    print('  confident_other dist_to_ref bins (mm) <2,2-5,5-8.5,8.5-15,15-25,>25:',
          np.histogram(a, [0, 2, 5, 8.5, 15, 25, 1e9])[0].tolist())
