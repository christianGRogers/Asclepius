"""Janus 1-F round 2 (Foxtrot): tables -> results/summary.md + summary.json.
Usage: python3 summarise.py pass1.jsonl selftest.jsonl band.jsonl recheck_collapse.json"""
import json, sys
import numpy as np

HERE = __import__('os').path.dirname(__import__('os').path.abspath(__file__))
sys.path.insert(0, HERE)
from branch_score import aggregate  # noqa

p1 = [json.loads(l) for l in open(sys.argv[1])]
st = [json.loads(l) for l in open(sys.argv[2])]
bd = [json.loads(l) for l in open(sys.argv[3])] if len(sys.argv) > 3 else []
rc = json.load(open(sys.argv[4])) if len(sys.argv) > 4 else None
out, md = {}, []
N = len(p1)
md.append(f'# Foxtrot j1f round 2: summary ({N} of the 620 in pass 1; {len(bd)} in the band pass)\n')

# 1. labels
keys = ['d3', 'd4_to_lad', 'other_lcx', 'other_nearest', 'other_ignore']
lab = {k: sum(r['info'][k] for r in p1) for k in keys}
lab['cases_with_D3'] = sum(r['info']['d3'] > 0 for r in p1)
lab['collapse_mismatch_voxels'] = sum(r['collapse_mismatch'] for r in p1)
lab['collapse_mismatch_cases'] = sum(r['collapse_mismatch'] > 0 for r in p1)
lab['collapse_mismatch_left_pda_voxels'] = sum(r['collapse_mismatch_left_pda'] for r in p1)
lab['ignore_voxels'] = sum(r['ignore_voxels'] for r in p1)
lab['ignore_share_of_tree'] = sum(r['ignore_voxels'] for r in p1) / sum(r['tree_voxels'] for r in p1)
out['labels'] = lab
if rc:
    lab['recheck_with_grouped_posterior'] = {'n_rechecked': rc['n_rechecked'], **rc['total'], 'cases_with_mismatch': rc['cases_with_mismatch']}
md.append('## 1. Stage-1 labels (D47 Q1 = A, F-A3) and the origin collapse vs territory.to_four\n')
md.append('```\n' + json.dumps(lab, indent=1) + '\n```\n')

# 2. scorer self-tests
ident = aggregate([r['identity'] for r in p1])
ident_st = aggregate([r['identity'] for r in st])
tf = [r for r in st if 'perturb' in r]
out['identity'] = ident
md.append('## 2. Branch scorer self-tests\n')
md.append(f'Identity (reference scored against itself, {N} cases; branch tF1 on the {len(st)} fit-check cases):\n')
md.append('| class | ref cases (>= 5 mm) | pieces | recall | naming | presence agr. | tF1 |\n|---|---|---|---|---|---|---|')
for c, a in ident.items():
    md.append(f"| {c} | {a['ref_cases']} | {a['pieces']} | {a['recall']} | {a['naming']} | {a['presence_agreement']} | {ident_st[c]['tf1_mean']} |")
pert = {}
for k in ('swap_D1_D2', 'drop_OM2', 'types_to_parent', 'erode_branches'):
    ag = aggregate([r['perturb'][k] for r in tf])
    pert[k] = ag
out['perturb'] = pert
md.append(f'\nPerturbations (the {len(tf)} fit-check cases): recall / naming / presence agreement / tF1\n')
md.append('| perturbation | ' + ' | '.join(ident) + ' |\n|---|' + '---|' * len(ident))
for k, ag in pert.items():
    fmt = lambda v: '-' if v is None else round(v, 3)
    md.append(f'| {k} | ' + ' | '.join(' / '.join(str(fmt(a[m])) for m in ('recall', 'naming', 'presence_agreement', 'tf1_mean'))
                                     for a in ag.values()) + ' |')

# 3. census for the simulation
cen = {}
for c in ident:
    pcs = [len(r['census'][c]['pieces_mm']) for r in p1 if r['census'][c]['pieces_mm']]
    mm = [r['census'][c]['ref_mm'] for r in p1 if r['census'][c]['pieces_mm']]
    cen[c] = {'cases_any': len(pcs), 'cases_ge5mm': sum(m >= 5 for m in mm), 'cases_ge3mm': sum(m >= 3 for m in mm),
              'pieces_mean': round(float(np.mean(pcs)), 3) if pcs else None,
              'cases_ge2_pieces': sum(p >= 2 for p in pcs),
              'median_cl_mm': float(np.median(mm)) if mm else None}
out['census'] = cen
md.append('\n## 3. Census used by the gate simulation (620)\n')
md.append('| class | cases with any voxel | cl >= 5 mm | cl >= 3 mm | pieces / case | cases >= 2 pieces | median cl mm |\n|---|---|---|---|---|---|---|')
for c, v in cen.items():
    md.append(f"| {c} | {v['cases_any']} | {v['cases_ge5mm']} | {v['cases_ge3mm']} | {v['pieces_mean']} | {v['cases_ge2_pieces']} | {v['median_cl_mm']} |")

# 4. twigs by three methods
tw = {}
for meth in ('delta', 'foxtrot', 'crucible'):
    tw[meth] = {}
    for v in ('LAD', 'LCx', 'RCA'):
        L = [r['twigs'][meth][v] for r in p1]
        tw[meth][v] = {f'cases_ge{t}': sum(any(x >= t for x in l) for l in L) for t in (3, 5, 10)}
        tw[meth][v]['twigs_ge5'] = sum(sum(x >= 5 for x in l) for l in L)
out['twigs'] = tw
md.append('\n## 4. Unnamed trunk twigs, three round-1 methods on the same cases\n')
md.append('| method | vessel | cases >= 3 mm | cases >= 5 mm | cases >= 10 mm | twigs >= 5 mm |\n|---|---|---|---|---|---|')
for meth, d in tw.items():
    for v, x in d.items():
        md.append(f"| {meth} | {v} | {x['cases_ge3']} | {x['cases_ge5']} | {x['cases_ge10']} | {x['twigs_ge5']} |")

# 5. dominance
def dom(p):
    R, Lf = p['R-PDA'], p['L-PDA']
    if R and not Lf: return 'right'
    if Lf and not R: return 'left'
    if R and Lf: return 'co (both PDAs)'
    return 'no PDA: ' + ('left PLA' if p['L-PLA'] and not p['R-PLA'] else 'right PLA' if p['R-PLA'] and not p['L-PLA'] else 'both/none')
dd = {}
for r in p1:
    k = dom(r['post']); dd[k] = dd.get(k, 0) + 1
anyleft = sum(r['post']['L-PDA'] or r['post']['L-PLA'] for r in p1)
coany = sum((r['post']['R-PDA'] or r['post']['R-PLA']) and (r['post']['L-PDA'] or r['post']['L-PLA']) for r in p1)
out['dominance'] = {'by_PDA': dd, 'cases_with_left_PDA_or_PLA': anyleft, 'cases_with_any_left_and_any_right_posterior': coany}
md.append('\n## 5. Dominance from labels\n')
md.append('```\n' + json.dumps(out['dominance'], indent=1) + '\n```\n')

# 6. band
if bd:
    md.append(f'\n## 6. Stage-2 background band ({len(bd)} cases, ids divisible by 20 among the 620)\n')
    md.append('| w (mm) | S band cm3 | N band cm3 | R band cm3 | union cm3 | union / 256^3 patch | union / bg within 25 mm | S prox/mid/dist | traced branch vol within w of LAD |\n|---|---|---|---|---|---|---|---|---|')
    bo = {}
    for w in ('4', '8', '15', '25'):
        g = lambda k: float(np.median([r['bands'][w][k] for r in bd]))
        pmd = np.array([r['bands'][w]['S_prox_mid_dist'] for r in bd if r['bands'][w]['S_prox_mid_dist']]).mean(0)
        bo[w] = {k: g(k) for k in ('S', 'N', 'R', 'union', 'union_patch_share', 'union_share_bg25', 'traced_branch_within_w_of_LAD_share')}
        bo[w]['S_pmd'] = pmd.round(3).tolist()
        md.append(f"| {w} | {bo[w]['S']/1e3:.1f} | {bo[w]['N']/1e3:.1f} | {bo[w]['R']/1e3:.1f} | {bo[w]['union']/1e3:.1f} | {bo[w]['union_patch_share']:.3f} | {bo[w]['union_share_bg25']:.3f} | {bo[w]['S_pmd']} | {bo[w]['traced_branch_within_w_of_LAD_share']:.3f} |")
    md.append(f"\nMedians over cases. Traced tree volume, median {np.median([r['traced_mm3'] for r in bd])/1e3:.2f} cm3.\n")
    syn = [s for r in bd for s in r['synthetic_septals']]
    md.append(f'Synthetic septals ({len(syn)} tubes): mean share of the centreline inside the band (unpenalised by CE)\n')
    md.append('| length mm | w=4 | w=8 | w=15 | w=25 | hits a traced vessel |\n|---|---|---|---|---|---|')
    so = {}
    for Ln in ('10', '20', '30', '40', '60'):
        so[Ln] = {w: round(float(np.mean([s[Ln][w] for s in syn])), 3) for w in ('4', '8', '15', '25')}
        so[Ln]['hits'] = round(float(np.mean([s[Ln]['hits_traced'] for s in syn])), 3)
        md.append(f"| {Ln} | {so[Ln]['4']} | {so[Ln]['8']} | {so[Ln]['15']} | {so[Ln]['25']} | {so[Ln]['hits']} |")
    out['band'] = bo; out['synthetic'] = so
json.dump(out, open(f'{HERE}/results/summary.json', 'w'), indent=1)
open(f'{HERE}/results/summary.md', 'w').write('\n'.join(md) + '\n')
print('\n'.join(md))
