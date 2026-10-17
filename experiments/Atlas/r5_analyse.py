import json, numpy as np, collections
from scipy.stats import spearmanr, mannwhitneyu
R = '/home/user/Asclepius/trillium-results/round5'
g = {}
for f in ('/home/user/Asclepius/experiments/Atlas/r5_reference_geometry.jsonl',):
    for l in open(f):
        x = json.loads(l); g[x['case']] = x
a = {x['case']: x for x in json.load(open(f'{R}/atlas/results/per_case_val.json'))}
b = {c: json.load(open(f'{R}/bridge/results/cases/{c}.json'))['D'] for c in a}
err = [c for c in g if 'error' in g[c]]; print('n', len(g), 'errors', err)
cs = [c for c in a if c in g and 'error' not in g[c]]
# 1. left ostium accuracy
for rule in ('atlas', 'bridge', 'delta'):
    d = [g[c]['roots'].get(f'{rule}_left', {}).get('to_truth_mm') for c in cs]
    d = np.array([x for x in d if x is not None]); print(rule, 'left to truth: n', len(d), 'median', np.median(d).round(2), '>5mm', (d > 5).sum())
# right truth cases
rt = [c for c in cs if g[c]['roots'].get('atlas_right', {}).get('to_truth_mm') is not None]
print('right-truth cases', len(rt))
for c in rt:
    r = g[c]['roots']; h = g[c].get('rca_heur', {})
    print(c, 'atlas', round(r['atlas_right']['to_truth_mm'], 1), 'bridge', round(r.get('bridge_right', {}).get('to_truth_mm') or -1, 1), 'heur', round(h.get('to_truth_mm') or -1, 1), 'heur-left', round(h.get('to_left_mm', -1), 1))
# 2. RCA root vs heuristic, and RCA tf1 zero
print('\ncase  atlasRCA bridgeRCA  a_to_heur b_to_heur  a_r b_r heur_r  heur_to_left  refcomp  nend')
rows = []
for c in cs:
    r = g[c]['roots']; h = g[c].get('rca_heur')
    if '4' not in a[c]['tf1_per_class'] or h is None: continue
    ar = r.get('atlas_right', {}); br = r.get('bridge_right', {})
    rows.append((c, a[c]['tf1_per_class']['4'], b[c]['tf1_per_class'].get('4'), ar.get('to_heur_mm'), br.get('to_heur_mm'), ar.get('r_mm'), br.get('r_mm'), h['r_mm'], h['to_left_mm'], g[c]['ref_components'], g[c]['n_end_rca'], a[c]['cldice_per_class']['4']))
for x in rows:
    if x[1] < 0.3 or (x[2] or 0) < 0.3:
        print(x[0], *[round(v, 2) if isinstance(v, float) else v for v in x[1:]])
ok = [x for x in rows if x[1] >= 0.3]; bad = [x for x in rows if x[1] < 0.3]
print('atlas RCA root within 10mm of heur: ok cases', np.mean([x[3] < 10 for x in ok]), 'zero cases', np.mean([x[3] < 10 for x in bad]))
print('heur to left: median', np.median([x[8] for x in rows]))
# 3. FP vs ICX outside
fp = np.array([a[c]['fp_components'] for c in cs])
for k in ('icx_outside_pieces_ge100', 'icx_detached_pieces_ge100', 'icx_outside_vox', 'icx_outside_frac', 'ref_components', 'mask_vox'):
    v = np.array([g[c][k] for c in cs]); print(k, 'mean', v.mean().round(3), 'spearman with FP', spearmanr(fp, v))
