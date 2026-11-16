"""Summarise census14_per_case.json (Janus 1-F round 1, Foxtrot) into summary.json and a markdown table on stdout.
Also: the D3-in-Other rule (diagonal-side Other components, ordered by distance to the LM/LAD join), dominance,
twig counts, calibre against a 0.5 mm voxel, and the reads-per-class sizes for reporting.
Usage: python3 summarise14.py results/census14_per_case.json results/summary.json"""
import json, sys, statistics as st
import numpy as np

R = json.load(open(sys.argv[1])); N = len(R)
SEG = ['LM', 'LAD', 'LCx', 'D1', 'D2', 'OM1', 'OM2', 'IM', 'RCA', 'R-PDA', 'R-PLA', 'L-PDA', 'L-PLA', 'Other']
out = {'n_cases': N, 'classes': {}}
q = lambda v, p: round(float(np.percentile(v, p)), 2) if v else None
print(f'n = {N}\n\n| ICX class | cases | % | median mm3 | median length mm | median diam mm (p10) | diam < 1.0 mm (cases) | >1 component |')
print('|---|---|---|---|---|---|---|---|')
for s in SEG:
    rows = [r['cls'][s] for r in R if s in r['cls']]
    d = [x['diam_mm'] for x in rows]
    o = {'cases': len(rows), 'pct': round(100 * len(rows) / N, 1), 'mm3_med': q([x['mm3'] for x in rows], 50),
         'len_med': q([x['len_mm'] for x in rows], 50), 'diam_med': q(d, 50), 'diam_p10': q(d, 10),
         'diam_lt1': sum(x < 1.0 for x in d), 'multi_comp': sum(x['ncomp'] > 1 for x in rows)}
    out['classes'][s] = o
    print(f"| {s} | {o['cases']} | {o['pct']} | {o['mm3_med']} | {o['len_med']} | {o['diam_med']} ({o['diam_p10']}) | {o['diam_lt1']} | {o['multi_comp']} |")

# Other
ndiag = [sum(c['side'] == 'diag' for c in r['other_components']) for r in R]
nmarg = [sum(c['side'] == 'marg' for c in r['other_components']) for r in R]
nboth = [sum(c['side'] in ('both', 'none') for c in r['other_components']) for r in R]
has_d2 = ['D2' in r['cls'] for r in R]
o = {'cases_with_other': sum(bool(r['other_components']) for r in R),
     'components': sum(len(r['other_components']) for r in R),
     'diag_side_components': sum(ndiag), 'marg_side_components': sum(nmarg), 'ambiguous_components': sum(nboth),
     'cases_with_>=1_diag_side': sum(x >= 1 for x in ndiag), 'cases_with_>=2_diag_side': sum(x >= 2 for x in ndiag),
     'cases_with_>=1_diag_side_and_D2_labelled': sum(x >= 1 and h for x, h in zip(ndiag, has_d2)),
     'cases_with_>=1_diag_side_but_no_D2': sum(x >= 1 and not h for x, h in zip(ndiag, has_d2)),
     'cases_with_>=1_marg_side': sum(x >= 1 for x in nmarg),
     'touch_sets': {}}
for r in R:
    for c in r['other_components']:
        k = '+'.join(c['touch']) or 'none'; o['touch_sets'][k] = o['touch_sets'].get(k, 0) + 1
o['touch_sets'] = dict(sorted(o['touch_sets'].items(), key=lambda kv: -kv[1]))
out['other'] = o
print('\nOther:', json.dumps(o, indent=1))

# twigs
for v in ('LAD', 'RCA'):
    tw = [r.get(f'{v}_twigs', {}).get('twigs', []) for r in R]
    n3 = [len(t) for t in tw]; n10 = [sum(x['len_mm'] >= 10 for x in t) for t in tw]
    allt = [x for t in tw for x in t]
    out[f'{v}_twigs'] = {'cases_with_twig_ge3mm': sum(x > 0 for x in n3), 'twigs_ge3mm': sum(n3),
                         'cases_with_twig_ge10mm': sum(x > 0 for x in n10), 'twigs_ge10mm': sum(n10),
                         'twig_len_med': q([x['len_mm'] for x in allt], 50), 'twig_diam_med': q([x['diam_mm'] for x in allt], 50),
                         'trunk_diam_med': q([r[f'{v}_twigs'].get('trunk_diam_mm', 0) for r in R if f'{v}_twigs' in r], 50)}
    print(f'\n{v} twigs:', out[f'{v}_twigs'])

# dominance
dom = {}
for r in R:
    dom[r['dominance']] = dom.get(r['dominance'], 0) + 1
out['dominance_from_labels'] = dom
lp = {k: sum(k in r['cls'] for r in R) for k in ('L-PDA', 'L-PLA', 'R-PDA', 'R-PLA')}
out['posterior'] = lp
out['L-PDA_with_R-PDA'] = sum('L-PDA' in r['cls'] and 'R-PDA' in r['cls'] for r in R)
out['L-PLA_with_R-PLA'] = sum('L-PLA' in r['cls'] and 'R-PLA' in r['cls'] for r in R)
out['L-PLA_without_L-PDA'] = sum('L-PLA' in r['cls'] and 'L-PDA' not in r['cls'] for r in R)
print('\ndominance:', dom, lp, {k: out[k] for k in ('L-PDA_with_R-PDA', 'L-PLA_with_R-PLA', 'L-PLA_without_L-PDA')})

# reads per class: n for a 95 % CI half-width h on a mean with SD s, and on a detection rate p
sd = {'D1': 28.7, 'D2': 24.3, 'OM1': 32.3, 'OM2': 29.1, 'IM': 24.5, 'R-PDA': 21.9, 'R-PLA': 18.6, 'L-PDA': 29.0,
      'L-PLA': 27.2, 'Other': 17.0}  # ImageCAS-X Table 1 inter-observer DSC SD (points)
nr = {}
for k, s in sd.items():
    nr[k] = {f'h{h}': int(np.ceil((1.96 * s / 100 / h) ** 2)) for h in (0.05, 0.10, 0.15)}
nr['detection_p0.85'] = {f'h{h}': int(np.ceil(1.96 ** 2 * .85 * .15 / h ** 2)) for h in (0.05, 0.10, 0.15)}
out['n_for_ci_halfwidth'] = nr
print('\nn present cases for a 95% CI half-width h:', json.dumps(nr))
json.dump(out, open(sys.argv[2], 'w'), indent=1)
