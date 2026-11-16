"""Summarise census.jsonl (Janus 1-F round 1, Atlas). Usage: python summarise.py <census.jsonl> <out.json>"""
import sys, json
import numpy as np
rows = [json.loads(l) for l in open(sys.argv[1])]
n = len(rows)
NAMES = ['LM', 'LAD', 'LCx', 'D1', 'D2', 'OM1', 'OM2', 'IM', 'RCA', 'R-PDA', 'R-PLA', 'L-PDA', 'L-PLA', 'Other']
out = {'n_cases': n, 'classes': {}}
tot = {k: sum(r['cls'].get(k, {}).get('vox', 0) for r in rows) for k in NAMES}
allv = sum(tot.values())
q = lambda a, p: round(float(np.percentile(a, p)), 2) if len(a) else None
for k in NAMES:
    have = [r['cls'][k] for r in rows if k in r['cls']]
    dm = [h['diam_med'] for h in have if 'diam_med' in h]
    out['classes'][k] = {
        'cases': len(have), 'share_cases': round(len(have) / n, 3),
        'share_of_tree_voxels': round(tot[k] / allv, 4),
        'mm3_median': q([h['mm3'] for h in have], 50),
        'diam_med_mm_median': q(dm, 50), 'diam_med_mm_p10': q(dm, 10),
        'diam_in_0.5mm_voxels_median': round(q(dm, 50) / 0.5, 1) if dm else None,
        'skel_len_mm_median': q([h['skel_len_mm'] for h in have if 'skel_len_mm' in h], 50),
        'cases_more_than_1_component': sum(h['components'] > 1 for h in have),
        'end_points_median': q([h['end_points'] for h in have if 'end_points' in h], 50),
        'cases_with_ge3_end_points': sum(h.get('end_points', 0) >= 3 for h in have),
    }
# 'Other': sides, and D3 as the most proximal LAD-side component
side_counts = {'LAD': 0, 'LCx': 0, 'both': 0, 'none': 0}
cases_lad_other = cases_lcx_other = 0
lad_other_per_case = []
d3_after_d2 = d3_before_d2 = d3_no_d2 = 0
for r in rows:
    o = r.get('other', [])
    for c in o:
        side_counts[c['side']] += 1
    lad = [c for c in o if c['side'] == 'LAD']
    lad_other_per_case.append(len(lad))
    cases_lad_other += bool(lad)
    cases_lcx_other += any(c['side'] == 'LCx' for c in o)
    fm = r.get('first_mm', {})
    lad_o = [c['origin_mm'] for c in lad if c.get('origin_mm') is not None]
    if lad_o:
        if 'D2' in fm:
            if min(lad_o) > fm['D2']: d3_after_d2 += 1
            else: d3_before_d2 += 1
        else:
            d3_no_d2 += 1
out['other'] = {'components_ge20vox_by_side': side_counts,
                'cases_with_LAD_side_other (a D3 candidate)': cases_lad_other,
                'share_cases_with_LAD_side_other': round(cases_lad_other / n, 3),
                'cases_with_LCx_side_other (OM3/OM4)': cases_lcx_other,
                'LAD_side_other_components_per_case_hist': {str(k): lad_other_per_case.count(k) for k in sorted(set(lad_other_per_case))},
                'proximal_LAD_side_other_origin_distal_to_D2_origin': d3_after_d2,
                'proximal_LAD_side_other_origin_proximal_to_D2_origin': d3_before_d2,
                'LAD_side_other_without_D2': d3_no_d2}
# ordinal consistency: D1 before D2, OM1 before OM2 (origin, geodesic from LM)
def order(a, b):
    ok = bad = 0; diffs = []
    for r in rows:
        fm = r.get('first_mm', {})
        if a in fm and b in fm:
            d = fm[b] - fm[a]; diffs.append(d)
            ok += d > 0; bad += d <= 0
    return {'pairs': ok + bad, f'{a}_proximal': ok, f'{b}_proximal_or_equal': bad,
            'share_consistent': round(ok / max(ok + bad, 1), 3), 'gap_mm_median': q(diffs, 50)}
out['ordinal'] = {'D1_vs_D2': order('D1', 'D2'), 'OM1_vs_OM2': order('OM1', 'OM2')}
out['ordinal']['D2_without_D1'] = sum('D2' in r['cls'] and 'D1' not in r['cls'] for r in rows)
out['ordinal']['OM2_without_OM1'] = sum('OM2' in r['cls'] and 'OM1' not in r['cls'] for r in rows)
out['ordinal']['cases_without_LM'] = sum('first_mm' not in r for r in rows)
# dominance vs which PDA/PLA is labelled
dom = {}
for r in rows:
    d = r.get('dominance', '?')
    e = dom.setdefault(str(d), {'cases': 0, 'R-PDA': 0, 'R-PLA': 0, 'L-PDA': 0, 'L-PLA': 0, 'no_PDA': 0})
    e['cases'] += 1
    for k in ('R-PDA', 'R-PLA', 'L-PDA', 'L-PLA'):
        e[k] += k in r['cls']
    e['no_PDA'] += not ({'R-PDA', 'L-PDA'} & set(r['cls']))
out['dominance'] = dom
out['both_R_and_L_PDA'] = sum({'R-PDA', 'L-PDA'} <= set(r['cls']) for r in rows)
out['zooms_z_hist'] = {str(k): v for k, v in zip(*np.unique([r['zooms'][2] for r in rows], return_counts=True))}
json.dump(out, open(sys.argv[2], 'w'), indent=1, default=int)
print(json.dumps(out, indent=1, default=int))
