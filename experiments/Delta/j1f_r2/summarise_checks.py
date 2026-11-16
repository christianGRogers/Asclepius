"""Summarise label_checks.json -> label_checks_summary.md. Usage: python summarise_checks.py <label_checks.json>"""
import json, sys
import numpy as np

d = json.load(open(sys.argv[1])); g = d['group']
L = []
for grp in ('train620', 'locked100'):
    rows = [r for r in d['collapse'] if g[r['case']] == grp]
    comp = sum(r['stats'].get('components', 0) for r in rows)
    fb = sum(r['stats'].get('fallback', 0) for r in rows)
    fbu = sum(r['stats'].get('fallbackUnattached', 0) for r in rows)
    fbt = sum(r['stats'].get('fallbackTie', 0) for r in rows)
    lcx_comp = sum(r['stats'].get('byParent', {}).get('LCx', 0) for r in rows)
    w2r = sum(r['lcx_ref_voxels_sent_to_rca'] for r in rows); w2l = sum(r['rca_ref_voxels_sent_to_lcx'] for r in rows)
    left = sum(r['left_branch_voxels'] for r in rows)
    bad = [r['case'] for r in rows if r['lcx_ref_voxels_sent_to_rca'] or r['rca_ref_voxels_sent_to_lcx']]
    L.append(f'**{grp}** ({len(rows)} cases): {comp} PDA/PLB components decided; {lcx_comp} to the LCx; fallbacks {fb} '
             f'(unattached {fbu}, tie {fbt}). Left-sided (L-PDA/L-PLA) voxels {left}; LCx-reference voxels sent to the '
             f'RCA {w2r}; RCA-reference voxels sent to the LCx {w2l}; cases with any mismatch: {len(bad)} {bad[:12]}')
L.append('')
B = d['band']
L.append(f'**Band** ({len(B)} training cases, hash-chosen). Released background (mm³), median [p10, p90] per case, and '
         'as a multiple of the case\'s tree volume:')
L.append('')
L.append('| Host | ' + ' | '.join(f'{w} mm' for w in (4, 8, 15, 25)) + ' |')
L.append('|---|---|---|---|---|')
for h in ('LAD', 'LCx', 'RCA', 'union'):
    cells = []
    for w in (4, 8, 15, 25):
        v = np.array([b['release_mm3'].get(f'{h}_{w}', np.nan) for b in B]); t = np.array([b['tree_mm3'] for b in B])
        cells.append(f'{np.nanmedian(v)/1e3:.0f}k [{np.nanpercentile(v,10)/1e3:.0f}k, {np.nanpercentile(v,90)/1e3:.0f}k]; '
                     f'×{np.nanmedian(v/t):.0f}')
    L.append(f'| {h} | ' + ' | '.join(cells) + ' |')
L.append('')
L.append('A 256³ patch at 0.5 mm is 2 097k mm³.')
L.append('')
L.append('Share of a **traced** side branch\'s voxels within w of its own trunk (median over cases [p10]); p90 and max '
         'distance (median over cases):')
L.append('')
L.append('| Branch (trunk) | 4 mm | 8 mm | 15 mm | 25 mm | p90 dist mm | max dist mm | cases |')
L.append('|---|---|---|---|---|---|---|---|')
for k, nm in (('4', 'D1 (LAD)'), ('5', 'D2 (LAD)'), ('6', 'OM1 (LCx)'), ('7', 'OM2 (LCx)'), ('10', 'R-PDA (RCA)'),
              ('11', 'R-PLA (RCA)')):
    cv = [b['cover'][k] for b in B if k in b['cover']]
    cells = [f"{np.median([c[str(w)] for c in cv]):.2f} [{np.percentile([c[str(w)] for c in cv],10):.2f}]"
             for w in (4, 8, 15, 25)]
    L.append(f'| {nm} | ' + ' | '.join(cells) + f" | {np.median([c['p90_mm'] for c in cv]):.1f} | "
             f"{np.median([c['max_mm'] for c in cv]):.1f} | {len(cv)} |")
open(sys.argv[1].replace('.json', '_summary.md') if len(sys.argv) < 3 else sys.argv[2], 'w').write('\n'.join(L) + '\n')
print('\n'.join(L))
