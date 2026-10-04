# Aggregate compare_icx / rule_naming / hu_disagreement logs into the tables used in the experiment notes.
import json, numpy as np, glob, sys
W = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad/work/Crucible'
NAMES = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'D1', 5: 'D2', 6: 'OM1', 7: 'OM2', 8: 'IM', 9: 'RCA', 10: 'R-PDA', 11: 'R-PLA',
         12: 'L-PDA', 13: 'L-PLA', 14: 'Other'}


def q(a): a = np.asarray([x for x in a if x is not None], float); return f'{a.mean():.3f} (med {np.median(a):.3f}, p10 {np.percentile(a,10):.3f}, n={len(a)})'


what = sys.argv[1]
if what == 'compare':
    rows = []
    for f in glob.glob(W + '/compare_icx_*.json'): rows += json.load(open(f))
    print('cases', len(rows), 'hdr_ok', sum(r['hdr_ok'] for r in rows))
    for k in ['dice', 'icx_cov_by_ours', 'ours_cov_by_icx', 'ours_within1_icx', 'icx_within1_ours', 'ours_far_frac']:
        print(k, q([r[k] for r in rows]))
    print('vol ratio ours/icx', q([r['our_vox'] / r['icx_vox'] for r in rows]))
    print('ncomp ours', q([r['our_ncomp'] for r in rows]), 'icx', q([r['icx_ncomp'] for r in rows]))
    tot = sum(r['icx_vox'] for r in rows)
    for k in range(1, 15):
        n = sum(r[f'n{k}'] for r in rows); pres = sum(r[f'n{k}'] > 0 for r in rows)
        print(f'{NAMES[k]:6s} present {pres:4d}/{len(rows)}  share of ICX lumen {100*n/tot:5.1f}%  covered by our mask {q([r[f"cov{k}"] for r in rows])}')
elif what == 'naming':
    rows = [json.loads(l) for f in glob.glob(W + '/naming_*.log') for l in open(f) if l.startswith('{')]
    print('cases', len(rows))
    for key in ['A_terr', 'A_main', 'B_terr']:
        ok = [r for r in rows if isinstance(r.get(key), dict)]
        print(key, 'failures', len(rows) - len(ok), 'voxel acc', q([r[key + '_acc'] for r in ok]))
        for c, n in zip('1234', ['LM', 'LAD', 'LCx', 'RCA']):
            v = [r[key][c] for r in ok]
            print('   ', n, q(v), ' cases <0.8:', sum(1 for x in v if x is not None and x < 0.8))
    bad = sorted(rows, key=lambda r: r['A_terr_acc'] if isinstance(r.get('A_terr'), dict) else -1)[:8]
    print('worst A_terr', [(r['id'], round(r.get('A_terr_acc', -1), 3)) for r in bad])
