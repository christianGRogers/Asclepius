"""Summarise r9_icx4_reference.py output (one JSON line per case; duplicates from restarts dropped).
Usage: summarise_r9.py <r9.jsonl> [val.txt]"""
import json, sys
import numpy as np

rows = {}
for line in open(sys.argv[1]):
    r = json.loads(line)
    rows[r['case']] = r
R = list(rows.values())
val = {int(x) for x in open(sys.argv[2]).read().split()} if len(sys.argv) > 2 else set()
print(f'cases: {len(R)} (val {sum(r["icx_id"] in val for r in R)})')
C = ['LM', 'LAD', 'LCx', 'RCA']
print('present:', {c: sum(c in r.get('present', []) for r in R) for c in C})
print('more than one piece:', {c: sum(r.get('pieces', {}).get(c, 0) > 1 for r in R) for c in C})
print('trees (components) per case:', dict(zip(*np.unique([r.get('trees', 0) for r in R], return_counts=True))))
print('cases with Other voxels:', sum(r['other_voxels'] > 0 for r in R))
cw = [r['case'] + ':' + ','.join(r['classes_without_centreline']) for r in R if r.get('classes_without_centreline')]
print(f'classes without centreline: {len(cw)} cases {cw[:12]}')
lm = np.array([r['lm_centreline_mm'] for r in R if 'LM' in r.get('present', [])])
print(f'LM centreline mm: median {np.median(lm):.1f}, <3 mm: {(lm < 3).sum()}, p10 {np.percentile(lm, 10):.1f}')
print('expert leaf candidates (left,right) counts:',
      dict(zip(*np.unique([f"{r['expert_leaf_candidates'].get('left')},{r['expert_leaf_candidates'].get('right')}"
                           for r in R], return_counts=True))))
for side in ('left', 'right'):
    d = np.array([r[f'{side}_expert_to_centreline_mm'] for r in R if f'{side}_expert_to_centreline_mm' in r])
    t = np.array([r[f'{side}_thick_vs_expert_mm'] for r in R if r.get(f'{side}_thick_vs_expert_mm') is not None])
    print(f'{side}: expert ostium to our centreline: n {len(d)} median {np.median(d):.2f} p95 {np.percentile(d, 95):.2f} '
          f'max {d.max():.2f}; thick rule vs expert: median {np.median(t):.2f}, >2 mm {(t > 2).sum()}, '
          f'>5 mm {(t > 5).sum()} ({100 * (t > 5).mean():.1f} %)')
fl_t = sum(any(o['flagged'] for o in r['ostia_thick']) for r in R)
fl_e = sum(any(o['flagged'] for o in (r['ostia_expert'] or [])) for r in R)
rule = [o['rule'] for r in R for o in (r['ostia_expert'] or [])]
print(f'flagged cases: thick-only {fl_t} (no cross-check possible without CT), expert-ostium {fl_e}; '
      f'expert-ostium trees by rule: {dict(zip(*np.unique(rule, return_counts=True)))}')
Q = [r for r in R if 'tf1_cut_expert' in r]
if Q:
    print(f'\nQ3 cut test on {len(Q)} cases')
    for c in C:
        dz = [r['dice_cut'][c] for r in Q if c in r['dice_cut'] and r['dice_cut'][c] is not None]
        te = [r['tf1_cut_expert'][c] for r in Q if c in r['tf1_cut_expert']]
        tt = [r['tf1_cut_thick'][c] for r in Q if c in r.get('tf1_cut_thick', {})]
        print(f'  {c}: Dice median {np.median(dz):.3f} (min {np.min(dz):.3f}); tF1 expert ostia median '
              f'{np.median(te):.3f} (max {np.max(te):.3f}); tF1 thick ostia median {np.median(tt):.3f} (max {np.max(tt):.3f})')
    tree = [r['dice_cut_tree'] for r in Q]
    me = [r['tf1_cut_expert_macro'] for r in Q]
    mt = [r['tf1_cut_thick_macro'] for r in Q if 'tf1_cut_thick_macro' in r]
    print(f'  whole-tree Dice median {np.median(tree):.3f} (min {np.min(tree):.3f}); macro tF1 expert median '
          f'{np.median(me):.3f}, thick median {np.median(mt):.3f}')
    dis = [r['case'] for r in Q if abs(r.get('tf1_cut_thick_macro', 0) - r['tf1_cut_expert_macro']) > 0.05]
    print(f'  cases where thick vs expert ostia change the cut macro by > 0.05: {len(dis)} {dis[:10]}')
    hid = sum(1 for r in Q for c in ('LAD', 'LCx') if r['dice_cut'].get(c) is not None and r['dice_cut'][c] >= 0.95
              and r['tf1_cut_expert'].get(c, 1) < 0.5)
    print(f'  LAD/LCx with Dice >= 0.95 but tF1 < 0.5 (a cut Dice cannot see): {hid} of '
          f'{sum(1 for r in Q for c in ("LAD", "LCx") if c in r["dice_cut"])}')
    print('  self-score tF1 == 1:', sum(r.get('tf1_self') == 1.0 for r in Q), 'of', len(Q))
