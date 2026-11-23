"""Janus 1-F round 3 (Delta): summarise census620.jsonl (ruling §5 items 1 and 5).

  A. Converter counts against F-A18's expected line; SegQueue collapse against D25; contact fallbacks.
  B. The scorer of record's reference pieces against Atlas's census_r2.jsonl (what F-A15's lines were simulated on):
     per case and class, the same pieces (voxel count and length).
  C. F-A22's stage-2 numbers on stand-ins (see census620.py): the false-fail of L1 (0.02), L2 (30 mm, 95 %) and K1
     (0.05) for a stage-2 model whose only error is an ostium painted k voxels too wide, on locked-100-sized (L1, L2)
     and fit-check-sized (K1) random draws from the 620. Bounds as F-A22: one-sided 1.25 %, bootstrap by case.
Usage: python summarise_census.py <census620.jsonl> <census_r2.jsonl> <out.json>
"""
import json, sys
import numpy as np

rows = sorted((json.loads(l) for l in open(sys.argv[1])), key=lambda r: r['case'])
atlas = {r['case']: r for r in (json.loads(l) for l in open(sys.argv[2]))}
out = {'n_cases': len(rows)}
# ---------------------------------------------------------------- A
keys = ('d3', 'd4_to_lad', 'other_lcx', 'other_nearest', 'other_ignore')
out['converter'] = {k: sum(r['other'][k] for r in rows) for k in keys}
out['converter_expected_620'] = {'d3': 47, 'd4_to_lad': 2, 'other_lcx': 20, 'other_nearest': 1, 'other_ignore': 8}
out['collapse_mismatch_vox_nonother'] = sum(r['collapse_mismatch_vox_nonother'] for r in rows)
out['collapse_mismatch_other_vox'] = sum(r['collapse_mismatch_other_vox'] for r in rows)
out['collapse_mismatch_other_cases'] = sum(r['collapse_mismatch_other_vox'] > 0 for r in rows)
out['contact'] = {k: sum(r['contact'][k] for r in rows) for k in ('components', 'fallback', 'fallbackTie',
                                                                 'fallbackUnattached')}
out['contact']['to_LCx'] = sum(r['contact']['byParent']['LCx'] for r in rows)
# ---------------------------------------------------------------- B
cls = ('D1', 'D2', 'D3', 'OM1', 'OM2', 'Ramus', 'PDA', 'PLB')
diff_cases, diff_classes = [], {c: 0 for c in cls}
for r in rows:
    a = atlas[r['case']]
    bad = [c for c in cls if r['pieces'][c] != a['pieces'][c]]
    if bad:
        diff_cases.append(r['case'])
        for c in bad:
            diff_classes[c] += 1
out['pieces_vs_census_r2'] = {'cases_compared': len(rows), 'cases_differing': len(diff_cases),
                              'by_class': diff_classes, 'first': diff_cases[:5]}
out['pieces_per_case'] = {c: {str(k): sum(len(r['pieces'][c]) == k for r in rows) for k in range(0, 5)} for c in cls}
# ---------------------------------------------------------------- C
rng = np.random.default_rng(0)
NSUB, NBOOT = 2000, 1000
Q = 0.0125


def ub_ratio(num, den, idx):
    """one-sided 1.25 % upper bootstrap bound of sum(num)/sum(den) over the cases in idx."""
    b = rng.integers(0, len(idx), size=(NBOOT, len(idx)))
    nn, dd = num[idx][b].sum(1), den[idx][b].sum(1)
    return np.quantile(nn / np.maximum(dd, 1), 1 - Q), num[idx].sum() / max(den[idx].sum(), 1)


groups = ('LAD', 'LCx', 'RCA')
bleeds = ('bleed0', 'bleed1', 'bleed2')
stage2 = {}
n = len(rows)
for bl in bleeds:
    res = {}
    # L1 per host group: centreline theft share, pooled over 100 cases
    for g in groups:
        num = np.array([(r['stage2'][g] or {}).get(bl, {}).get('theft_pts', 0) for r in rows], float)
        den = np.array([(r['stage2'][g] or {}).get('trunk_cl_pts', 0) for r in rows], float)
        pts, ubs = [], []
        for _ in range(NSUB):
            idx = rng.choice(n, size=min(100, n), replace=False)
            u, p = ub_ratio(num, den, idx)
            ubs.append(u); pts.append(p)
        res[f'L1_{g}'] = {'share_620': round(num.sum() / max(den.sum(), 1), 4),
                          'case_p95': round(float(np.quantile(num / np.maximum(den, 1), 0.95)), 4),
                          'P_point_gt_0.02': float(np.mean(np.array(pts) > 0.02)),
                          'P_ub_gt_0.02': float(np.mean(np.array(ubs) > 0.02)),
                          'ub_median': round(float(np.median(ubs)), 4)}
    # L1 as proposed: only stolen runs >= 3 mm of trunk centreline count (an ostium painted wide is not theft)
    for g in groups:
        gm = np.array([float(np.prod(r['zooms'])) ** (1 / 3) for r in rows])
        num = np.array([sum(x for x in (r['stage2'][g] or {}).get(bl, {}).get('theft_runs_mm', []) if x >= 3.0)
                        for r in rows], float)
        den = np.array([(r['stage2'][g] or {}).get('trunk_cl_pts', 0) for r in rows], float) * gm
        ubs = [ub_ratio(num, den, rng.choice(n, size=min(100, n), replace=False))[0] for _ in range(NSUB)]
        runs = [x for r in rows for x in (r['stage2'][g] or {}).get(bl, {}).get('theft_runs_mm', [])]
        res[f'L1runs3_{g}'] = {'share_620': round(num.sum() / max(den.sum(), 1), 4),
                               'P_ub_gt_0.02': float(np.mean(np.array(ubs) > 0.02)),
                               'longest_run_mm': max(runs) if runs else 0.0,
                               'runs_ge_3mm': int(sum(x >= 3.0 for x in runs))}
    # L2: per case, the largest distance of any stand-in voxel from the rest of the tree
    for kind in ('far_mm', 'island_far_mm'):
        far = np.array([max([(r['stage2'][g] or {}).get(bl, {}).get(kind, 0.0) for g in groups]) for r in rows])
        byg = {g: np.array([(r['stage2'][g] or {}).get(bl, {}).get(kind, np.nan) for r in rows]) for g in groups}
        ok = far <= 30.0
        fails_point, fails_lb = [], []
        for _ in range(NSUB):
            idx = rng.choice(n, size=min(100, n), replace=False)
            k = ok[idx].sum()
            fails_point.append(k / len(idx) < 0.95)
            # one-sided 1.25 % lower bound of the passing share (bootstrap)
            b = rng.integers(0, len(idx), size=(NBOOT, len(idx)))
            fails_lb.append(np.quantile(ok[idx][b].mean(1), Q) < 0.95)
        res[f'L2_{kind}'] = {'share_cases_le_30mm': round(float(ok.mean()), 4),
                             'case_max_mm_p50_p90_p95_max': [round(float(np.quantile(far, q)), 1)
                                                              for q in (0.5, 0.9, 0.95, 1.0)],
                             'by_group_p95_mm': {g: round(float(np.nanquantile(v, 0.95)), 1) if np.isfinite(v).any()
                                                 else None for g, v in byg.items()},
                             'by_group_share_gt_30mm': {g: round(float(np.nanmean(v > 30)), 3) for g, v in byg.items()},
                             'P_fail_point': float(np.mean(fails_point)), 'P_fail_lb': float(np.mean(fails_lb))}
        for thr in (35.0, 40.0, 45.0, 50.0):
            res[f'L2_{kind}'][f'share_cases_le_{int(thr)}mm'] = round(float((far <= thr).mean()), 4)
    # K1 per stand-in group, pooled over 20 cases
    for g in groups:
        num = np.array([(r['stage2'][g] or {}).get(bl, {}).get('s2_in_traced', 0) for r in rows], float)
        den = np.array([(r['stage2'][g] or {}).get(bl, {}).get('s2_vox', 0) for r in rows], float)
        core = np.array([(r['stage2'][g] or {}).get(bl, {}).get('s2_in_traced_core', 0) for r in rows], float)
        pts, pc = [], []
        for _ in range(NSUB):
            idx = rng.choice(n, size=min(20, n), replace=False)
            pts.append(num[idx].sum() / max(den[idx].sum(), 1))
            pc.append(core[idx].sum() / max(den[idx].sum(), 1))
        res[f'K1_{g}'] = {'share_620': round(num.sum() / max(den.sum(), 1), 4),
                          'P_gt_0.05_on_20': float(np.mean(np.array(pts) > 0.05)),
                          'p95_on_20': round(float(np.quantile(pts, 0.95)), 4),
                          'core_share_620': round(core.sum() / max(den.sum(), 1), 4),
                          'core_P_gt_0.05_on_20': float(np.mean(np.array(pc) > 0.05)),
                          'core_p95_on_20': round(float(np.quantile(pc, 0.95)), 4)}
    stage2[bl] = res
out['stage2_standins'] = stage2
json.dump(out, open(sys.argv[3], 'w'), indent=1)
print(json.dumps(out, indent=1)[:6000])
