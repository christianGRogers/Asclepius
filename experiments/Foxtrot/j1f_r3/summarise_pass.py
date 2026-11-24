"""Janus 1-F round 3 (Foxtrot): summary of pass_r3_620.jsonl against the piece distribution F-A15 was simulated on
(Atlas's census_r2.jsonl), and Atlas's gate_sim.proposed_lines re-derived from the amended scorer's pieces.
Usage: python summarise_pass.py   (writes results/pass_summary.json, prints it)"""
import json, os, sys
from collections import Counter
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../../Atlas/j1f_r2'))
import gate_sim as GS  # noqa: E402

ours = {r['case']: r for r in map(json.loads, open(os.path.join(HERE, 'results/pass_r3_620.jsonl')))}
atlas = {r['case']: r for r in map(json.loads, open(os.path.join(HERE, '../../Atlas/j1f_r2/census_r2.jsonl')))}
assert len(ours) == 620 and set(ours) == set(atlas)
CL = ('D1', 'D2', 'D3', 'OM1', 'OM2', 'Ramus', 'PDA', 'PLB')
out = {'cases': len(ours)}
same_pieces = {c: sum(ours[k]['pieces'][c] == atlas[k]['pieces'][c] for k in ours) for c in CL}
out['cases_with_identical_pieces(vox,len)'] = same_pieces
out['pieces_total'] = {c: [sum(len(ours[k]['pieces'][c]) for k in ours), sum(len(atlas[k]['pieces'][c]) for k in atlas)]
                       for c in CL}
out['pieces_per_present_case'] = {c: dict(sorted(Counter(len(ours[k]['pieces'][c]) for k in ours
                                                        if ours[k]['pieces'][c]).items())) for c in CL}
pres = lambda r, c, mm: sum(p['len'] for p in r['pieces'][c]) >= mm
out['present_5mm'] = {c: sum(pres(ours[k], c, 5) for k in ours) for c in CL}
tot = Counter()
for r in ours.values():
    tot.update(r['other_atlas'])
out['converter_counts'] = dict(tot)
out['converter_counts_foxtrot_labels_r2'] = dict(sum((Counter(r['other_foxtrot']) for r in ours.values()), Counter()))
out['converter_voxel_differences'] = sum(r['converter_diff_vox'] for r in ours.values())
out['collapse_mismatch_vox'] = sum(r['collapse_mismatch_vox'] for r in ours.values())
mb = Counter()
for r in ours.values():
    mb.update({int(k): v for k, v in r['collapse_mismatch_by_icx'].items()})
out['collapse_mismatch_by_icx_class'] = dict(mb)
out['collapse_mismatch_cases'] = sum(r['collapse_mismatch_vox'] > 0 for r in ours.values())
ct = Counter()
for r in ours.values():
    c = r['contact']
    ct.update({'components': c.get('components', 0), 'fallback': c.get('fallback', 0),
               'LCx': c.get('byParent', {}).get('LCx', 0), 'RCA': c.get('byParent', {}).get('RCA', 0)})
out['contact'] = dict(ct)
out['ignore_vox'] = sum(r['ignore_vox'] for r in ours.values())
# Atlas's line rule on our pieces: write a census-shaped temp file and re-derive proposed lines
tmp = os.path.join(HERE, 'results/_pieces_tmp.jsonl')
with open(tmp, 'w') as f:
    for k in sorted(ours):
        f.write(json.dumps({'pieces': ours[k]['pieces']}) + '\n')
pd_ours, pd_atlas = GS.pieces_dist(tmp), GS.pieces_dist(os.path.join(HERE, '../../Atlas/j1f_r2/census_r2.jsonl'))
os.remove(tmp)
out['gate_sim_piece_dist_identical'] = {c: sorted(pd_ours[c]) == sorted(pd_atlas[c]) for c in GS.T1}
free = {'recall': 0, 'naming': 0, 'presence_margin': 1, 'k_of_6': 0}
wr = GS.simulate(GS.params(0.12), pd_ours, free, 0.0, 0.12, seed=3)
wn = GS.simulate(GS.params(0.05), pd_ours, free, 1.0, 0.05, seed=4)
out['proposed_lines_from_amended_scorer'] = {c: {'recall': float(np.floor(wr[c]['recall_p05'] * 100) / 100),
    'naming': float(np.floor(wn[c]['naming_p05'] * 100) / 100),
    'presence': float(np.floor(min(wr[c]['presence_p05'], wn[c]['presence_p05']) * 100) / 100)} for c in GS.T1}
json.dump(out, open(os.path.join(HERE, 'results/pass_summary.json'), 'w'), indent=1)
print(json.dumps(out, indent=1))
