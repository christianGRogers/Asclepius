"""Janus 1-F round 1 (Delta): tables from census.json and ordinal.json (train 620 and locked 100 apart).
Usage: python summary.py census.json ordinal.json > summary.md"""
import json, sys
from collections import Counter

import numpy as np

cen = json.load(open(sys.argv[1]))
orde = {r['case']: r for r in json.load(open(sys.argv[2]))} if len(sys.argv) > 2 else {}
TRAIN = {'train560', 'dev44', 'train_open16'}
LOCK = {'val80', 'locked_open20'}
NAMES = ['LM', 'LAD', 'LCx', 'RCA', 'D1', 'D2', 'OM1', 'OM2', 'IM', 'R-PDA', 'R-PLA', 'L-PDA', 'L-PLA', 'Other']


def q(a, p):
    return float(np.percentile(a, p)) if len(a) else float('nan')


for title, groups in (('Train 620', TRAIN), ('Locked 100', LOCK)):
    rows = [r for r in cen['rows'] if r['group'] in groups]
    n = len(rows)
    print(f'\n### {title} (n = {n})\n')
    print('| Class | cases (%) | median mm³ | median centreline mm | median radius mm | p10 radius mm | cases with > 1 piece |')
    print('|---|---|---|---|---|---|---|')
    for c in NAMES:
        s = [r['classes'][c] for r in rows if c in r['classes']]
        print(f"| {c} | {len(s)} ({100 * len(s) / n:.1f}) | {q([x['mm3'] for x in s], 50):.0f} | "
              f"{q([x['cl_mm'] for x in s], 50):.0f} | {q([x['r_med_mm'] for x in s if x['r_med_mm']], 50):.2f} | "
              f"{q([x['r_p10_mm'] for x in s if x['r_p10_mm']], 50):.2f} | {sum(x['pieces'] > 1 for x in s)} |")
    # dominance
    rp = sum('R-PDA' in r['classes'] for r in rows)
    lp = sum('L-PDA' in r['classes'] for r in rows)
    both = sum('R-PDA' in r['classes'] and 'L-PDA' in r['classes'] for r in rows)
    lpl = sum('L-PLA' in r['classes'] for r in rows)
    lonly = sum(('L-PDA' in r['classes'] or 'L-PLA' in r['classes']) and 'R-PDA' not in r['classes'] for r in rows)
    print(f'\nPDA: R-PDA {rp}, L-PDA {lp}, both {both}; L-PLA {lpl}; a left PDA/PLA and no R-PDA: {lonly}')
    # Other
    oth = [r['other_sides'] for r in rows if r['other_sides']]
    lad_n = Counter(o['lad'] for o in oth)
    lcx_n = Counter(o['lcx'] for o in oth)
    print(f'Other present in {len(oth)} cases; LAD-side pieces per case {dict(sorted(lad_n.items()))}; '
          f'LCx-side pieces per case {dict(sorted(lcx_n.items()))}; unassigned {sum(o["none"] for o in oth)}')
    # unnamed side branches in parent classes
    for key, nm in (('lad_side_branches', 'LAD'), ('lcx_side_branches', 'LCx'), ('rca_side_branches', 'RCA')):
        br = [b for r in rows for b in r[key]]
        per = [len(r[key]) for r in rows]
        print(f'{nm} class, unnamed side branches >= 5 mm: {len(br)} in {sum(p > 0 for p in per)} cases '
              f'(per case mean {np.mean(per):.2f}, max {max(per)}); length median {q([b["mm"] for b in br], 50):.1f} mm, '
              f'p90 {q([b["mm"] for b in br], 90):.1f}; radius median {q([b["r_med_mm"] for b in br], 50):.2f} mm')
    br = [b for r in rows for b in r['lad_side_branches'] if b['mm'] >= 10]
    print(f'  LAD side branches >= 10 mm: {len(br)} in {sum(any(b["mm"] >= 10 for b in r["lad_side_branches"]) for r in rows)} cases')
    br = [b for r in rows for b in r['rca_side_branches'] if b['mm'] >= 10]
    print(f'  RCA side branches >= 10 mm: {len(br)} in {sum(any(b["mm"] >= 10 for b in r["rca_side_branches"]) for r in rows)} cases')
    z = np.array([r['zooms'] for r in rows])
    print(f'Voxel size: in-plane {z[:, 0].min():.3f}-{z[:, 0].max():.3f} mm, slice {z[:, 2].min():.3f}-{z[:, 2].max():.3f} mm')
    if orde:
        o = [orde[r['case']] for r in rows if r['case'] in orde and 'error' not in orde[r['case']]]
        d12 = [x for x in o if x.get('D1') is not None and x.get('D2') is not None]
        om = [x for x in o if x.get('OM1') is not None and x.get('OM2') is not None]
        print(f'\nOrdinal: D1 attaches before D2 in {sum(x["D1"] < x["D2"] for x in d12)} of {len(d12)}; '
              f'OM1 before OM2 in {sum(x["OM1"] < x["OM2"] for x in om)} of {len(om)}')
        ol = [x for x in o if x['other_lad']]
        after = [x for x in ol if x.get('D2') is not None]
        print(f'LAD-side Other: {len(ol)} cases; first piece attaches after D2 in '
              f'{sum(x["other_lad"][0]["attach_mm"] > x["D2"] for x in after)} of {len(after)} with a D2; '
              f'cases with no D2 but LAD-side Other: {sum(x.get("D2") is None for x in ol)}')
        k = Counter(len(x['other_lad']) for x in ol)
        print(f'LAD-side Other pieces per case: {dict(sorted(k.items()))} '
              f'-> D3 candidates (first piece): {len(ol)}; extra pieces (D4 -> LAD): {sum(len(x["other_lad"]) - 1 for x in ol)}')
        olx = [x for x in o if x['other_lcx']]
        aft = [x for x in olx if x.get('OM2') is not None]
        print(f'LCx-side Other: {len(olx)} cases; first piece after OM2 in '
              f'{sum(x["other_lcx"][0]["attach_mm"] > x["OM2"] for x in aft)} of {len(aft)} with an OM2')
        print('errors:', [x['case'] for x in orde.values() if 'error' in x])
