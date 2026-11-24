"""Janus 1-F round 3 (Foxtrot): F-A22's stage-2 rules applied to stage2_620.jsonl (see stage2_falsefail.py).
False-fail = share of 100-case sets (drawn without replacement from the 620, 400 draws) on which a CORRECT stage-2
prediction fails the rule; inner bound by a 2000-resample case bootstrap (percentile), one-sided 1.25 %.
Usage: python summarise_stage2.py [n_draws]   (writes results/stage2_summary.json)"""
import json, os, sys
import numpy as np
from scipy.stats import beta

HERE = os.path.dirname(os.path.abspath(__file__))
rows = [json.loads(l) for l in open(os.path.join(HERE, 'results/stage2_620.jsonl'))]
fit20 = set(json.load(open(os.path.join(HERE, '../j1f_r2/results/fitcheck20.json')))['fitcheck20'])
ND = int(sys.argv[1]) if len(sys.argv) > 1 else 400
rng = np.random.default_rng(20261123)
LENS, RADII = (10, 20, 30, 40, 50, 60), (0.6, 0.75, 1.0)
n = len(rows)
out = {'cases': n, 'cases_with_3_tubes': sum(len(r['tubes']) == 3 for r in rows), 'draws': ND}


def ub(num, den, B=2000):
    """98.75th percentile of the pooled ratio over a case bootstrap (vectorised)."""
    idx = rng.integers(0, len(num), (B, len(num)))
    return float(np.percentile(num[idx].sum(1) / np.maximum(den[idx].sum(1), 1), 98.75))


def ff_ratio(num, den, line=0.02):
    fails, pts = 0, []
    for _ in range(ND):
        s = rng.choice(len(num), 100, replace=len(num) < 100)
        u = ub(num[s], den[s], 1000)
        fails += u > line; pts.append(u)
    return {'pooled_620': round(float(num.sum() / den.sum()), 4), 'median_upper_bound': round(float(np.median(pts)), 4),
            'false_fail': round(fails / ND, 3)}


def cp_lower(x, k, a=0.0125):
    return 0.0 if x == 0 else float(beta.ppf(a, x, k - x + 1))


def ff_cases(flag, need=0.95):
    pt = bd = 0
    for _ in range(ND):
        s = rng.choice(len(flag), 100, replace=len(flag) < 100)
        ok = int((~flag[s]).sum())
        pt += ok / 100 < need; bd += cp_lower(ok, 100) < need
    return {'flagged_cases_620': int(flag.sum()), 'false_fail_point': round(pt / ND, 3),
            'false_fail_with_CP_bound': round(bd / ND, 3)}


den = np.array([r['centreline_pts']['LAD'] for r in rows], float)
L1 = {}
for r_ in RADII:
    for Ln in (10, 30, 60):
        for key, tag in (('stolen_LAD', 'L1'), ('stolen_LAD_runs', 'L1r')):
            num = np.array([sum(t[f'r{r_}_L{Ln}'][key] for t in r['tubes']) for r in rows], float)
            L1[f'{tag} septals r={r_} L={Ln}'] = ff_ratio(num, den)
for key, tag in (('stolen_LAD', 'L1'), ('stolen_LAD_runs', 'L1r')):
    num = np.array([sum(t['thief'][key] for t in r['tubes']) for r in rows], float)
    L1[f'{tag} POWER thief (+-5 mm of LAD at each origin)'] = ff_ratio(num, den)
for name, g in (('D2', 'LAD'), ('OM2', 'LCx'), ('PLB', 'RCA')):
    rr = [r for r in rows if name in r['proxy']]
    for key, tag in (('stolen', 'L1'), ('stolen_runs', 'L1r')):
        L1[f'{tag} proxy {name} ({g} group), {len(rr)} cases'] = ff_ratio(
            np.array([r['proxy'][name][key] for r in rr], float), np.array([r['proxy'][name]['group_pts'] for r in rr], float))
out['L1_theft_line_0.02'] = L1
L2 = {}
for Ln in LENS:
    flag = np.array([any(t['L2_maxdist'][str(Ln)] > 30 for t in r['tubes']) for r in rows])
    L2[f'septals L={Ln} mm, line 30 mm'] = ff_cases(flag)
for line in (30, 40, 45, 50):
    flag = np.array([any(t['L2_maxdist']['60'] > line for t in r['tubes']) for r in rows])
    L2[f'septals L=60 mm, line {line} mm'] = ff_cases(flag)
for name in ('D2', 'OM2', 'PLB'):
    flag = np.array([r['proxy'].get(name, {}).get('L2_maxdist', 0) > 30 for r in rows])
    L2[f'proxy {name} (real branch tip vs the rest of the tree), line 30 mm'] = ff_cases(flag)
tipd = np.array([max(t['L2_maxdist']['60'] for t in r['tubes']) for r in rows if r['tubes']])
out['septal_L60_max_distance_mm_percentiles'] = {p: round(float(np.percentile(tipd, p)), 1) for p in (50, 90, 95, 99, 100)}
out['to_pda_mm_percentiles'] = {p: round(float(np.percentile([t['to_pda_mm'] for r in rows for t in r['tubes']], p)), 1)
                                for p in (5, 50, 95)}
out['L2_far_paint'] = L2
K1 = {}
fr = [r for r in rows if r['case'] in fit20]
out['K1_fitcheck_cases_available'] = len(fr)
for r_ in RADII:
    for Ln in LENS:
        sh = {}
        for i, nm in enumerate(('S1@15%', 'S2@30%', 'S3@45%')):
            ts = [t for r in fr for t in r['tubes'] if abs(t['frac'] - (.15, .30, .45)[i]) < 1e-6]
            v = sum(t[f'r{r_}_L{Ln}']['vox'] for t in ts); il = sum(t[f'r{r_}_L{Ln}']['in_lumen'] for t in ts)
            sh[nm] = round(il / max(v, 1), 4)
        K1[f'r={r_} L={Ln}'] = {'share_in_lumen': sh, 'fires_at_0.05': any(x > 0.05 for x in sh.values())}
out['K1_inside_traced_lumen_line_0.05'] = K1
K1r = {}
for r_ in RADII:
    for Ln in (10, 30, 60):
        num = sum(t[f'r{r_}_L{Ln}']['stolen_LAD_runs'] for r in fr for t in r['tubes'])
        K1r[f'r={r_} L={Ln}'] = round(num / max(sum(r['centreline_pts']['LAD'] for r in fr), 1), 4)
num = sum(t['thief']['stolen_LAD_runs'] for r in fr for t in r['tubes'])
K1r['POWER thief'] = round(num / max(sum(r['centreline_pts']['LAD'] for r in fr), 1), 4)
out['K1r_L1r_on_fitcheck20'] = K1r
json.dump(out, open(os.path.join(HERE, 'results/stage2_summary.json'), 'w'), indent=1)
print(json.dumps(out, indent=1))
