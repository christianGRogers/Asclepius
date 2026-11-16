"""Summarise census_r2.jsonl (620 training cases) -> census_r2_summary.json. Usage: summarise_r2.py <in.jsonl> <out.json>"""
import collections
import json
import sys

import numpy as np

rows = [json.loads(line) for line in open(sys.argv[1])]
out = {'n_cases': len(rows)}

# 1. contact rule vs ImageCAS-X's L-/R- side, per component and per case
agree = collections.Counter()
case_dis = set()
vox_dis = 0
vox_all = 0
for r in rows:
    for c in r['contact']['components']:
        want = 'LCx' if c['icx_side'] == 'L' else 'RCA'
        ok = want == c['rule']
        agree[(c['cls'], c['icx_side'], c['rule'])] += 1
        vox_all += c['vox']
        if not ok:
            case_dis.add(r['case'])
            vox_dis += c['vox']
fb = collections.Counter()
for r in rows:
    for k in ('fallback', 'fallbackUnattached', 'fallbackTie'):
        fb[k] += r['contact'][k]
    if r['contact']['fallback']:
        fb['cases_with_fallback'] += 1
comp_total = sum(agree.values())
comp_ok = sum(v for (cl, s, rule), v in agree.items() if (s == 'L') == (rule == 'LCx'))
out['contact'] = {'components': comp_total, 'agree_with_icx_side': comp_ok,
                  'table': {f'{cl} icx {s} -> {rule}': v for (cl, s, rule), v in sorted(agree.items())},
                  'cases_with_any_disagreement': len(case_dis), 'disagreeing_cases': sorted(case_dis),
                  'voxel_share_disagreeing': round(vox_dis / max(vox_all, 1), 5), 'fallbacks': dict(fb)}

# 2. bands
tree = np.array([r['tree_mm3'] for r in rows])
out['tree_mm3_median'] = float(np.median(tree))
out['band'] = {}
for d in ('4.0', '8.0', '15.0'):
    a = np.array([r['band'][d]['all_mm3'] for r in rows])
    h = np.array([r['band'][d]['host_mm3'] for r in rows])
    both = np.array([r['band'][d]['host_LAD_and_RCA_both_mm3'] for r in rows])
    sides = {s: np.array([r['band'][d]['by_side_mm3'][s] for r in rows]) for s in ('LAD', 'LCx', 'RCA', 'LM')}
    out['band'][d] = {
        'all_mm3_median': float(np.median(a)), 'all_mm3_p10_p90': [float(np.percentile(a, 10)), float(np.percentile(a, 90))],
        'all_over_tree_median': round(float(np.median(a / tree)), 1),
        'host_mm3_median': float(np.median(h)), 'host_over_tree_median': round(float(np.median(h / tree)), 1),
        'host_share_of_all_median': round(float(np.median(h / a)), 3),
        'LAD_and_RCA_overlap_mm3_median': float(np.median(both)),
        'LAD_and_RCA_overlap_share_of_host_median': round(float(np.median(both / h)), 4),
        'by_side_share_median': {s: round(float(np.median(v / a)), 3) for s, v in sides.items()}}

# 3. trunk twigs
out['twigs'] = {}
for t in ('LAD', 'LCx', 'RCA'):
    out['twigs'][t] = {}
    for cut in (3.0, 5.0):
        n = [sum(x >= cut for x in r['twigs_mm'][t]) for r in rows]
        out['twigs'][t][f'>={cut:g}mm'] = {'cases_with_any': int(sum(k > 0 for k in n)),
                                            'twigs_total': int(sum(n)), 'max_per_case': int(max(n))}
json.dump(out, open(sys.argv[2], 'w'), indent=1)
print(json.dumps(out, indent=1))
