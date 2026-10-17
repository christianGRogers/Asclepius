"""Counts, case-level bootstrap 95 % CIs and threshold sensitivity for fp_triage.py output."""
import json, sys
import numpy as np
rows = [json.loads(l) for l in open(sys.argv[1]) if 'error' not in l]
K = ['vein', 'artery_branch', 'mask_artefact', 'calcium_other', 'indeterminate']
cases = sorted(set(r['case'] for r in rows)); rng = np.random.default_rng(0)
def counts(rs, key='cls'): return {k: sum(r[key] == k for r in rs) for k in K}
print('components', len(rows), 'cases', len(cases), 'census categories', {k: sum(r['census_category'] == k for r in rows) for k in set(r['census_category'] for r in rows)})
for key in ('cls', 'cls_065', 'cls_085'):
    print(key, counts(rows, key))
bs = {k: [] for k in K}
for _ in range(5000):
    pick = rng.choice(cases, len(cases)); rs = [r for c in pick for r in rows if r['case'] == c]
    for k in K: bs[k].append(sum(r['cls'] == k for r in rs) / max(len(rs), 1))
for k in K:
    n = sum(r['cls'] == k for r in rows)
    print(f'{k:14s} {n:2d}/{len(rows)} = {n/len(rows):.0%}  case-bootstrap 95% CI [{np.percentile(bs[k],2.5):.0%}, {np.percentile(bs[k],97.5):.0%}]')
co = [r for r in rows if r['census_category'] == 'confident_other']
print('confident_other only:', len(co), counts(co))
for f in ('r_art', 'r_ao', 'core_hu', 'art_hu', 'ring_hu', 'diam_mm', 'len_mm', 'dist_ref_mm', 'along'):
    a = np.array([r[f] for r in rows]); print(f'{f:12s} median {np.median(a):7.2f}  IQR [{np.percentile(a,25):.2f}, {np.percentile(a,75):.2f}]')
print('companion', {k: sum(r['companion'] == k for r in rows) for k in ('LM', 'LAD', 'LCx', 'RCA')})
print('veins by companion', {k: sum(r['companion'] == k and r['cls'] == 'vein' for r in rows) for k in ('LM', 'LAD', 'LCx', 'RCA')})
for r in rows:
    print(r['case'], r['voxels'], r['census_category'][:5] if r['census_category'] else None, r['cls'], 'r_art %.2f r_ao %.2f ring %.0f diam %.1f len %.0f dref %.1f along %.2f %s' % (
        r['r_art'], r['r_ao'], r['ring_hu'], r['diam_mm'], r['len_mm'], r['dist_ref_mm'], r['along'], r['companion']))
