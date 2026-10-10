"""Round 6 (Q2): per-class failure taxonomy from the round-5 GPU scores + r6_attrs.py reference attributes.

Scores (no predictions on CPU):
  val  (Atlas run 1, 80 cases): per class tF1, clDice (same precision, no rooting), Dice  [Atlas per_case_val]
                                 naming headroom = oracle-names tF1 - direct tF1          [Bridge cases/, O - D]
  open (Delta run, 63 cases):   per class tF1 at 1.5 mm, s05 raw                       [Delta per_case.jsonl]
Loss per class c and case = 1 - tF1_c, split (val) into
  ostium   clDice - tF1 when the provisional root is > 5 mm from the expert ostium
  cut      clDice - tF1 otherwise (real disconnection)
  naming   max(O - D, 0)
  segment  1 - clDice - naming  (missed or extra centreline of the right name; recall/precision not separable
           from round-5 outputs -- run 2 Phase A reports both)
The segment loss is then stratified by reference attribute: field-of-view truncation, dominance, RCA length,
distal calibre (thin fraction), convention mismatch (mask voxels ImageCAS-X does not name; ImageCAS-X vessel
outside the mask). Attributable cost = prevalence x (mean loss in stratum - mean loss outside it).
Usage: python r6_taxonomy.py attrs.jsonl"""
import glob
import json
import sys

import numpy as np
from scipy import stats

ROOT = '/home/user/Asclepius/trillium-results/round5'
R5 = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad/work/Delta/r5'
N = {'1': 'LM', '2': 'LAD', '3': 'LCx', '4': 'RCA'}

att = {}
for line in open(sys.argv[1]):
    r = json.loads(line)
    if 'error' not in r:
        att[r['case']] = r
A = {x['case']: x for x in json.load(open(f'{ROOT}/atlas/results/per_case_val.json'))}
B = {}
for f in glob.glob(f'{ROOT}/bridge/results/cases/*.json'):
    r = json.load(open(f))
    B[r['case']] = r
D = {}
for line in open(f'{ROOT}/delta/results/per_case.jsonl'):
    r = json.loads(line)
    if r['base'] == 's05':
        D[r['case']] = r


def root_bad(a, side):
    ds = [o['d_true_mm'] for o in a['ostia_thick'] if o['side'] == side and o['d_true_mm'] is not None]
    return None if not ds else any(d > 5 for d in ds)


def atlas_root_bad(case, side):
    for p in ('an_a.jsonl', 'an_b.jsonl'):
        for line in open(f'{R5}/{p}'):
            r = json.loads(line)
            if r['case'] == case:
                ds = [o['d_true_mm'] for o in r['atlas_roots'] if o['side'] == side]
                ds = [d for d in ds if d == d]
                return None if not ds else any(d > 5 for d in ds)
    return None


rows = []
for c, x in A.items():
    if c not in att:
        continue
    for k in x['tf1_per_class']:
        side = 'right' if k == '4' else 'left'
        t, cl = x['tf1_per_class'][k], x['cldice_per_class'][k]
        bad = atlas_root_bad(c, side)
        nm = max(B[c]['O']['tf1_per_class'].get(k, 0) - B[c]['D']['tf1_per_class'].get(k, 0), 0) if c in B else 0.0
        a = att[c]['classes'].get(k)
        if a is None:
            continue
        rows.append(dict(set='val', case=c, k=k, loss=1 - t, ostium=(cl - t) if bad else 0.0,
                         cut=0.0 if bad else cl - t, naming=nm, segment=max(1 - cl - nm, 0.0), root_bad=bad,
                         dice=x['dice_per_class'][k], dom=att[c]['dominance'], joined=att[c]['rca_joined_left'], **a))
for c, r in D.items():
    if c not in att:
        continue
    for k, t in r['raw']['per_class_15'].items():
        side = 'right' if k == '4' else 'left'
        a = att[c]['classes'].get(k)
        if a is None:
            continue
        rows.append(dict(set='open', case=c, k=k, loss=1 - t, root_bad=root_bad(att[c], side),
                         dom=att[c]['dominance'], joined=att[c]['rca_joined_left'], **a))


def mean(v):
    return float(np.mean(v)) if len(v) else float('nan')


print(f'cases with attributes: val {len({r["case"] for r in rows if r["set"] == "val"})}, '
      f'open {len({r["case"] for r in rows if r["set"] == "open"})}')
print('\n## val: loss decomposition per class (mean per case)')
print('class n | 1-tF1 | ostium | cut | naming | segment | 1-Dice')
for k in N:
    v = [r for r in rows if r['set'] == 'val' and r['k'] == k]
    print(N[k], len(v), ' '.join(f'{mean([r[q] for r in v]):.3f}' for q in
                                ('loss', 'ostium', 'cut', 'naming', 'segment')), f'{mean([1 - r["dice"] for r in v]):.3f}')

print('\n## open: provisional root misplaced (> 5 mm) and its tF1 cost (thick-only roots, as scored)')
for k in N:
    v = [r for r in rows if r['set'] == 'open' and r['k'] == k]
    bad = [r for r in v if r['root_bad']]
    ok = [r for r in v if r['root_bad'] is False]
    print(N[k], f'n {len(v)} root>5mm {len(bad)} loss there {mean([r["loss"] for r in bad]):.3f} vs '
          f'{mean([r["loss"] for r in ok]):.3f} (attributable {len(bad) / max(len(v), 1) * (mean([r["loss"] for r in bad]) - mean([r["loss"] for r in ok])):.3f})')

STRATA = {
    'fov_truncated (centreline within 2 mm of a scan face)': lambda r: r['min_face_mm'] is not None and r['min_face_mm'] <= 2.0,
    'left_dominant (L-PDA/L-PLA, no R-PDA/R-PLA)': lambda r: r['dom'] == 'left',
    'short (< 25th pct length of its class)': None,
    'thin (> 75th pct of centreline r < 1 mm)': None,
    'mask_unnamed > 10 % (mask vessel ImageCAS-X does not name)': lambda r: r['mask_unnamed'] > 0.10,
    'icx_outside_mask > 10 % (ImageCAS-X vessel the mask lacks)': lambda r: r['icx_outside_mask'] > 0.10,
    'reference split (> 1 component in class)': lambda r: r['n_comp'] > 1,
    'RCA joined to left tree in the reference': lambda r: r['joined'],
}
for setname, target in (('val', 'segment'), ('open', 'loss')):
    print(f'\n## {setname}: {target} loss by stratum (prevalence, mean in / out, attributable per case)')
    for k in N:
        v = [r for r in rows if r['set'] == setname and r['k'] == k and (setname == 'val' or r['root_bad'] is not True)]
        if not v:
            continue
        L = np.array([r['length_mm'] for r in v])
        th = np.array([r['thin100'] or 0 for r in v])
        print(f'### {N[k]} (n {len(v)})')
        for name, f in STRATA.items():
            if name.startswith('short'):
                f = (lambda q: (lambda r: r['length_mm'] < q))(np.percentile(L, 25))
            if name.startswith('thin'):
                f = (lambda q: (lambda r: (r['thin100'] or 0) > q))(np.percentile(th, 75))
            if k != '4' and name.startswith(('left_dominant', 'RCA joined')):
                continue
            ins = [r[target] for r in v if f(r)]
            out = [r[target] for r in v if not f(r)]
            if not ins:
                print(f'  {name}: 0 cases')
                continue
            p = len(ins) / len(v)
            pv = stats.mannwhitneyu(ins, out).pvalue if ins and out else float('nan')
            print(f'  {name}: {len(ins)}/{len(v)}  {mean(ins):.3f} / {mean(out):.3f}  attributable {p * (mean(ins) - mean(out)):+.4f}  (MWU p={pv:.2g})')
        for q in ('length_mm', 'thin100', 'median_r', 'mask_unnamed', 'icx_outside_mask', 'near_face5'):
            x = [r[q] or 0 for r in v]
            rho, pv = stats.spearmanr(x, [r[target] for r in v])
            print(f'  rho({q}, {target}) = {rho:+.2f} (p={pv:.2g})')
json.dump(rows, open(sys.argv[1].replace('.jsonl', '_rows.json'), 'w'))
