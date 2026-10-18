"""Summarise r9_territory_audit.py output, leaving out the sealed cases (A14) so no figure rests on them.
Usage: r9_territory_summ.py <audit.json> <sealed_test.json>"""
import json, sys, statistics as st
from collections import Counter
S = json.load(open(sys.argv[2])); SEALED = set(S['sealed_icx_test']) | set(S['sealed_quality0'])
R = [r for r in json.load(open(sys.argv[1])) if r['case'] not in SEALED]
N = ['LM', 'LAD', 'LCx', 'RCA']
print('cases', len(R), Counter(r['split'] for r in R))
tot = {k: sum(r['vox'][k] for r in R) for k in N}; T = sum(tot.values())
for k in N:
    pres = sum(r['vox'][k] > 0 for r in R)
    ss = [r['side_share'][k] for r in R if r['vox'][k] > 0]
    vml = [r['vox'][k] * r['voxel_mm3'] for r in R if r['vox'][k] > 0]
    multi = sum(1 for r in R if k in r['components'] and r['components'][k]['n_ge10'] > 1)
    sec = [r['components'][k]['second_vox'] for r in R if k in r['components'] and r['components'][k]['n_ge10'] > 1]
    print(f"{k}: present {pres}/{len(R)}; share of tree voxels {tot[k]/T:.3f}; median volume {st.median(vml):.0f} mm3; "
          f"side-branch share median {st.median(ss):.3f} mean {st.mean(ss):.3f} p90 {sorted(ss)[int(.9*len(ss))]:.3f}; "
          f"cases with >1 component(>=10 vox) {multi}; median 2nd comp {st.median(sec) if sec else 0} vox")
print('tree components >=10 vox:', Counter(r['tree_components_ge10'] for r in R).most_common(8))
for c in ('LM-RCA', 'LAD-RCA', 'LCx-RCA'):
    xs = [r['contacts'][c] for r in R]
    print(c, 'cases with contact', sum(x > 0 for x in xs), 'median voxels when >0', st.median([x for x in xs if x] or [0]))
oc = [r for r in R if r['other_vox'] > 0]
print('Other present', len(oc), 'cases; by split', Counter(r['split'] for r in oc), '; share of all tree voxels',
      round(sum(r['other_vox'] for r in R) / T, 4))
P = [p for r in R for p in r['other_pieces']]
print('Other pieces', len(P), 'voxels', sum(p['vox'] for p in P))
agree = [p for p in P if p['touches'] != 'none' and p['assigned'] == p['touches']]
dis = [p for p in P if p['touches'] != 'none' and p['assigned'] != p['touches']]
none = [p for p in P if p['touches'] == 'none']
mixed = [p for p in P if p['mixed_assignment']]
print('touching a named vessel: agree', len(agree), sum(p['vox'] for p in agree), 'vox; disagree', len(dis),
      sum(p['vox'] for p in dis), 'vox; isolated', len(none), sum(p['vox'] for p in none), 'vox; split across classes', len(mixed),
      sum(p['vox'] for p in mixed))
print('disagreements (assigned->touches):', Counter((p['assigned'], p['touches']) for p in dis).most_common())
print('isolated pieces assigned:', Counter(p['assigned'] for p in none))
cases_dis = [r['case'] for r in R if any(p['touches'] != 'none' and p['assigned'] != p['touches'] for p in r['other_pieces'])]
print('cases with a disagreeing Other piece', len(cases_dis), cases_dis[:20])
