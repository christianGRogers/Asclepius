"""Summarise pass620.jsonl for §5 items 1 and 5. Usage: python summarise.py <pass620.jsonl> <out.json>"""
import hashlib
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import j1f_scorer as S  # noqa: E402

rows = [json.loads(l) for l in open(sys.argv[1])]
rows.sort(key=lambda r: r['case'])
cases = [r['case'] for r in rows]
atlas = {json.loads(l)['case']: json.loads(l) for l in open(os.path.join(HERE, '../../Atlas/j1f_r2/census_r2.jsonl'))}
G = S.load_gates(os.path.join(HERE, 'j1f_gates.json'))
GATED = [S.NAMES[c] for c in S.GATED]
out = {'n_cases': len(rows)}

# ---- item 1: pieces equal to the distribution the lines were simulated on
diff = [r['case'] for r in rows if r['pieces'] != atlas[r['case']]['pieces']]
out['item1_piece_rows_differing_from_census_r2'] = diff
dist = {}
for k in GATED + ['D3', 'Ramus']:
    n = [len(r['pieces'][k]) for r in rows]
    a = [len(atlas[c]['pieces'][k]) for c in cases]
    dist[k] = {'cases_with': sum(x > 0 for x in n), 'pieces': sum(n), 'multi_piece_cases': sum(x > 1 for x in n),
               'census_r2_cases_with': sum(x > 0 for x in a), 'census_r2_pieces': sum(a)}
out['item1_piece_distribution'] = dist
out['item1_collapse'] = {'components': sum(r['collapse']['components'] for r in rows),
                         'fallback': sum(r['collapse']['fallback'] for r in rows),
                         'mismatch_vox_vs_D25_outside_Other_and_255': sum(r['collapse']['mismatch_vox'] for r in rows),
                         'cases_with_fallback': [r['case'] for r in rows if r['collapse']['fallback']]}
out['item1_converter_counts'] = {k: sum(r['other'][k] for r in rows) for k in rows[0]['other']}


def agg(tag):
    res = {}
    for k in GATED:
        det = [d for r in rows for d in r[tag][k]['det']]
        nam = [d for r in rows for d in r[tag][k]['named']]
        pres = [r[tag][k]['pr'] == r[tag][k]['pp'] for r in rows]
        res[k] = {'pieces': len(det), 'recall': round(sum(det) / len(det), 4),
                  'naming': round(sum(nam) / max(sum(det), 1), 4), 'presence': round(float(np.mean(pres)), 4)}
        ln = G['lines'][k]
        res[k]['passes_lines'] = all(res[k][m] >= ln[m] for m in ('recall', 'presence', 'naming'))
    return res


out['item1_identity'] = agg('identity')
out['item1_erode1'] = agg('erode1')

# ---- item 5: stage-2 numbers on references as predictions (traced branches as proxies)
z = 2.2414  # one-sided 1.25 %
rng = np.random.default_rng(1)
B = 4000
st = [r['stage2'] for r in rows if r['stage2'].get('has_proxy')]
res5 = {'n_cases_with_proxy': len(st)}
for form in ('nearest', 'prox'):
    for tag in ('exact', 'bleed1'):
        for g in ('LAD', 'LCx', 'RCA'):
            num = np.array([s[tag]['L1'][g]['n'] * s[tag]['L1'][g][form] for s in st if s[tag]['L1'][g]])
            den = np.array([s[tag]['L1'][g]['n'] for s in st if s[tag]['L1'][g]], float)
            pooled = num.sum() / den.sum()
            ff = 0
            for _ in range(B):
                i = rng.integers(0, len(den), 100)
                ratio = num[i].sum() / den[i].sum()
                # linearised SE of a ratio estimator
                se = np.sqrt(np.var(num[i] - ratio * den[i], ddof=1) / 100) / den[i].mean()
                ff += ratio + z * se > 0.02
            res5[f'L1_{form}_{tag}_{g}'] = {'pooled': round(float(pooled), 4), 'p90_case': round(float(np.percentile(
                num / den, 90)), 4), 'false_fail_at_0.02': round(ff / B, 4)}
for tag in ('exact', 'bleed1'):
    for form, key in (('voxel', 'L2_voxel_max_mm'), ('component', 'L2_component_gap_max_mm')):
        v = np.array([s[tag][key] for s in st])
        ok = v <= 30.0
        ff_point = ff_bound = 0
        from scipy.stats import beta
        for _ in range(B):
            i = rng.integers(0, len(v), 100)
            k = int(ok[i].sum())
            ff_point += k / 100 < 0.95
            lo = beta.ppf(0.0125, k, 100 - k + 1) if k > 0 else 0.0
            ff_bound += lo < 0.95
        res5[f'L2_{form}_{tag}'] = {'share_cases_within_30mm': round(float(ok.mean()), 4),
                                    'p50_mm': round(float(np.median(v)), 2), 'p95_mm': round(float(np.percentile(v, 95)), 2),
                                    'max_mm': round(float(v.max()), 2),
                                    'false_fail_point_0.95': round(ff_point / B, 4),
                                    'false_fail_lower_bound_0.95': round(ff_bound / B, 4)}
fit = sorted(cases, key=lambda c: hashlib.sha256(('asclepius-j1f-fitcheck:' + c).encode()).hexdigest())[:20]
for tag in ('exact', 'dilate1'):
    v = np.array([r['stage2']['K1'][tag] for r in rows if r['stage2'].get('has_proxy')])
    fv = [r['stage2']['K1'][tag] for r in rows if r['case'] in fit and r['stage2'].get('has_proxy')]
    draws = [np.mean(v[rng.integers(0, len(v), 20)]) for _ in range(B)]
    res5[f'K1_{tag}'] = {'mean_620': round(float(v.mean()), 4), 'p95_case': round(float(np.percentile(v, 95)), 4),
                         'fitcheck20_mean': round(float(np.mean(fv)), 4) if fv else None,
                         'false_fail_at_0.05_any20': round(float(np.mean(np.array(draws) > 0.05)), 4)}
for g in ('LAD', 'LCx', 'RCA'):
    v = np.array([r['stage2']['K1_group'][g] for r in rows if g in r['stage2'].get('K1_group', {})])
    draws = [np.mean(v[rng.integers(0, len(v), 20)]) for _ in range(B)]
    res5[f'K1_dilate1_group_{g}'] = {'n_cases': int(len(v)), 'mean': round(float(v.mean()), 4),
                                     'p95_case': round(float(np.percentile(v, 95)), 4),
                                     'false_fail_at_0.05_any20': round(float(np.mean(np.array(draws) > 0.05)), 4)}
out['item5'] = res5
out['fitcheck20'] = fit if len(rows) == 620 else None
json.dump(out, open(sys.argv[2], 'w'), indent=1)
print(json.dumps(out, indent=1))
