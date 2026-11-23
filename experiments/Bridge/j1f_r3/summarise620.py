"""Summarise run620.jsonl (the scorer of record on the 620 training references) against Atlas's census_r2.jsonl, the
piece distribution F-A15's lines were simulated on. Usage: python3 summarise620.py run620.jsonl > run620_summary.json"""
import json, os, sys
from collections import Counter
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
rows = {json.loads(l)['case']: json.loads(l) for l in open(sys.argv[1])}
atlas = {json.loads(l)['case']: json.loads(l) for l in open(os.path.join(HERE, '../../Atlas/j1f_r2/census_r2.jsonl'))}
CL = ('D1', 'D2', 'D3', 'OM1', 'OM2', 'Ramus', 'PDA', 'PLB')
GATED = ('D1', 'D2', 'OM1', 'OM2', 'PDA', 'PLB')
out = {'cases': len(rows), 'same_case_set_as_census': sorted(rows) == sorted(atlas)}
tot = Counter()
for r in rows.values():
    tot.update(r['other'])
out['converter_totals'] = dict(tot)
out['converter_totals_match_F_A18'] = dict(tot) == {'d3': 47, 'd4_to_lad': 2, 'other_lcx': 20, 'other_nearest': 1,
                                                    'other_ignore': 8}
out['collapse_mismatch_voxels_outside_other'] = sum(r['collapse_mismatch_vox'] for r in rows.values())
out['collapse_fallbacks'] = sum(r['collapse_fallback'] for r in rows.values())
out['collapse_PDA_PLB_components'] = sum(r['collapse_components'] for r in rows.values())
per = {}
for c in CL:
    mine = [len(rows[k]['pieces'][c]) for k in sorted(rows)]
    theirs = [len(atlas[k]['pieces'][c]) for k in sorted(rows)]
    len_diff = sum(1 for k in rows if [round(x, 2) for x in rows[k]['pieces'][c]] != [p['len'] for p in atlas[k]['pieces'][c]])
    vox_diff = sum(1 for k in rows if rows[k]['pieces_vox'][c] != [p['vox'] for p in atlas[k]['pieces'][c]])
    pres = [sum(rows[k]['pieces'][c]) >= 5.0 for k in sorted(rows)]
    in_absent = sum(n for n, p in zip(mine, pres) if not p)
    short = sum(1 for k in rows for x in rows[k]['pieces'][c] if x < 5.0)
    idt = [rows[k]['identity'][c] for k in rows]
    per[c] = {'cases_with_piece': sum(1 for n in mine if n), 'cases_present_5mm': int(sum(pres)),
              'pieces': int(sum(mine)), 'pieces_per_case_dist': {int(k): v for k, v in sorted(Counter(n for n in mine if n).items())},
              'census_pieces_per_case_dist': {int(k): v for k, v in sorted(Counter(n for n in theirs if n).items())},
              'cases_piece_count_differs': sum(a != b for a, b in zip(mine, theirs)),
              'cases_piece_lengths_differ': len_diff, 'cases_piece_voxels_differ': vox_diff,
              'pieces_in_cases_absent_at_5mm': int(in_absent), 'pieces_shorter_than_5mm': short,
              'identity_detected': sum(x['det'] for x in idt), 'identity_named': sum(x['named'] for x in idt),
              'identity_presence_agree': sum(x['pres_ref'] == x['pres_pred'] for x in idt)}
out['per_class'] = per
out['all_pieces_match_census'] = all(v['cases_piece_count_differs'] == 0 and v['cases_piece_lengths_differ'] == 0
                                     and v['cases_piece_voxels_differ'] == 0 for v in per.values())
out['identity_perfect'] = all(v['identity_detected'] == v['pieces'] == v['identity_named'] and
                              v['identity_presence_agree'] == len(rows) for v in per.values())
t = [r['t_s'] for r in rows.values()]
out['seconds_per_case'] = {'median': float(np.median(t)), 'p90': float(np.percentile(t, 90))}
print(json.dumps(out, indent=1))
