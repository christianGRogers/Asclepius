"""Janus 1-F round 3 (Atlas): summary of check_620.jsonl (items 1, 3 and 5 of the round-2 ruling's §5).

1. SegQueue's collapse vs D25 on the 620 (outside "Other" and 255), and SegQueue's fallback counts.
2. F-A18's expected 'Other' line.
3. The round-3 scorer's reference pieces vs round 2's census_r2.jsonl (the distribution F-A15 was simulated on):
   per case and class, piece count, voxels and length; presence at 5 mm.
4. Stage-2 numbers (F-A22) under the surrogate described in check_620.py, as false-fail rates of a model that paints
   its stage-2 class exactly (k = 0) or 1-2 voxels too wide (k = 1, 2):
   L1  pooled theft share per host on 100-case draws from the 620: P(share > 0.02) and P(upper 98.75 % bound > 0.02);
   K1  pooled in-lumen share per host on 20-case draws: P(share > 0.05);
   L2  case-level, as written ("no voxel of a stage-2 class more than 30 mm from predicted coronary foreground"):
       the stage-2 class excluded from the foreground, per voxel (max distance) or per component (min distance);
       P(cases failing > 5 % of 100) on 100-case draws; and the max-distance quantiles per host.
5. Disk: the 620's grid sizes x 13 channels (uncompressed npz ceiling).
Usage: python summarise_620.py <check_620.jsonl> <census_r2.jsonl> <out.json>
"""
import json
import sys

import numpy as np

HOSTS = ('LAD', 'LCx', 'RCA')
Z9875 = 2.2414


def boot(rng, n, size, reps=10000):
    return rng.integers(0, n, (reps, size))


def main(chk, cen, outp):
    rows = [json.loads(l) for l in open(chk)]
    old = {r['case']: r for r in (json.loads(l) for l in open(cen))}
    n = len(rows)
    out = {'n_cases': n}
    # 1-2
    out['collapse'] = {
        'mismatch_vox_outside_other_and_255': int(sum(r['collapse_mismatch_outside_other'] for r in rows)),
        'cases_with_mismatch_outside_other': int(sum(r['collapse_mismatch_outside_other'] > 0 for r in rows)),
        'mismatch_vox_in_other': int(sum(r['collapse_mismatch_vox'] - r['collapse_mismatch_outside_other']
                                         for r in rows)),
        'cases_with_mismatch_in_other': int(sum(r['collapse_mismatch_vox'] > r['collapse_mismatch_outside_other']
                                                for r in rows)),
        'sq_components': int(sum(r['sq_stats'].get('components', 0) for r in rows)),
        'sq_fallback': int(sum(r['sq_stats'].get('fallback', 0) for r in rows)),
        'sq_byParent': {p: int(sum(r['sq_stats'].get('byParent', {}).get(p, 0) for r in rows)) for p in ('RCA', 'LCx')}}
    keys = ('d3', 'd4_to_lad', 'other_lcx', 'other_nearest', 'other_ignore')
    out['other_counts'] = {k: int(sum(r['other'][k] for r in rows)) for k in keys}
    # 3
    diff = {'count': 0, 'vox': 0, 'len_gt_0.01mm': 0, 'cases_missing_in_census': 0}
    pieces_hist, present = {}, {}
    for r in rows:
        o = old.get(r['case'])
        if o is None:
            diff['cases_missing_in_census'] += 1
            continue
        for c, ps in r['pieces'].items():
            q = o['pieces'][c]
            pieces_hist.setdefault(c, {}).setdefault(len(ps), 0)
            pieces_hist[c][len(ps)] += 1
            if len(ps) != len(q):
                diff['count'] += 1; continue
            for a, b in zip(sorted(ps, key=lambda x: x['vox']), sorted(q, key=lambda x: x['vox'])):
                diff['vox'] += a['vox'] != b['vox']
                diff['len_gt_0.01mm'] += abs(a['len'] - b['len']) > 0.01
        for c, v in r['present'].items():
            present[c] = present.get(c, 0) + int(v)
    out['pieces_vs_census_r2'] = diff
    out['pieces_per_case_hist'] = {c: dict(sorted(v.items())) for c, v in pieces_hist.items()}
    out['present_5mm'] = present
    # 4
    rng = np.random.default_rng(20261123)
    i100, i20 = boot(rng, n, 100), boot(rng, n, 20)
    s2 = {}
    for h in HOSTS:
        H = [r['s2'][h] for r in rows]
        den = np.array([x['trunk_pts'] for x in H], float)
        d = {}
        for k in (0, 1, 2):
            a = np.array([x[f'l1_stolen_k{k}'] for x in H], float)
            A, D = a[i100].sum(1), den[i100].sum(1)
            share = A / D
            res = a[i100] - share[:, None] * den[i100]
            se = np.sqrt((res ** 2).sum(1) * 100 / 99) / D
            ki = np.array([x[f'k1_in_traced_k{k}'] for x in H], float)
            kp = np.array([x[f'k1_pred_vox_k{k}'] for x in H], float)
            ksh = ki[i20].sum(1) / np.maximum(kp[i20].sum(1), 1)
            d[f'k{k}'] = {'L1_share_620': round(float(a.sum() / den.sum()), 5),
                          'L1_P_share_gt_0.02': round(float((share > 0.02).mean()), 4),
                          'L1_P_upper_gt_0.02': round(float((share + Z9875 * se > 0.02).mean()), 4),
                          'L1_share_p95_of_draws': round(float(np.percentile(share, 95)), 5),
                          'K1_share_620': round(float(ki.sum() / max(kp.sum(), 1)), 5),
                          'K1_P_share_gt_0.05_20cases': round(float((ksh > 0.05).mean()), 4),
                          'K1_share_p95_of_20case_draws': round(float(np.percentile(ksh, 95)), 5)}
        mx = [max([p[0] for p in x['l2_pieces_max_min_mm']], default=0.0) for x in H]
        mn = [max([p[1] for p in x['l2_pieces_max_min_mm']], default=0.0) for x in H]
        allmax = np.array([p[0] for x in H for p in x['l2_pieces_max_min_mm']])
        allmin = np.array([p[1] for x in H for p in x['l2_pieces_max_min_mm']])
        fv, fc = np.array(mx) > 30, np.array(mn) > 30
        d['L2'] = {'pieces': int(len(allmax)),
                   'piece_max_dist_mm_p50_p90_p95_max': [round(float(np.percentile(allmax, q)), 1)
                                                         for q in (50, 90, 95, 100)],
                   'piece_min_dist_mm_p50_p99_max': [round(float(np.percentile(allmin, q)), 2) for q in (50, 99, 100)],
                   'cases_fail_per_voxel_30mm': int(fv.sum()),
                   'P_fail_per_voxel_100cases': round(float((fv[i100].mean(1) > 0.05).mean()), 4),
                   'cases_fail_per_component_30mm': int(fc.sum()),
                   'P_fail_per_component_100cases': round(float((fc[i100].mean(1) > 0.05).mean()), 4),
                   'per_voxel_threshold_for_95pct_of_cases_mm': round(float(np.percentile(mx, 95)), 1)}
        s2[h] = d
    out['stage2_surrogate'] = s2
    # 5
    vox = np.array([np.prod(r['shape']) for r in rows], float)
    out['grid_voxels'] = {'median': int(np.median(vox)), 'max': int(vox.max())}
    out['npz_ceiling_GB_13ch'] = {dt: {'median_case': round(float(np.median(vox)) * 13 * b / 1e9, 2),
                                       'max_case': round(float(vox.max()) * 13 * b / 1e9, 2),
                                       'chunk_of_10_at_max': round(float(vox.max()) * 13 * b * 10 / 1e9, 1),
                                       'all_100_at_median': round(float(np.median(vox)) * 13 * b * 100 / 1e9, 1)}
                                  for dt, b in (('float32', 4), ('float16', 2))}
    json.dump(out, open(outp, 'w'), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main(*sys.argv[1:4])
