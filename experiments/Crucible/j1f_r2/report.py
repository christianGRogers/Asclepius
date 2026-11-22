"""Build the markdown tables of the candidate and the Experiments note from the committed outputs.
Usage: report.py <census620.jsonl> <sim.json>  -> prints a JSON dict {placeholder: markdown}"""
import hashlib, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
R = [json.loads(l) for l in open(sys.argv[1])]
SIM = json.load(open(sys.argv[2]))
TOY = [json.loads(l) for l in open(os.path.join(HERE, 'dice_toy.jsonl'))]
DOM = json.load(open(os.path.join(HERE, 'dominance620.json')))
BR = ['D1', 'D2', 'D3', 'OM1', 'OM2', 'Ramus', 'PDA', 'PLB']
G6 = ['D1', 'D2', 'OM1', 'OM2', 'PDA', 'PLB']
NL = {'D1': 98, 'D2': 64, 'OM1': 84, 'OM2': 40, 'PDA': 96, 'PLB': 96}
A = {'D1': .969, 'D2': .894, 'OM1': .944, 'OM2': .875, 'PDA': .988, 'PLB': .962}
out = {}
n = len(R)
out['BSHA'] = hashlib.sha256(open(os.path.join(HERE, 'branch_score.py'), 'rb').read()).hexdigest()

# ---- sim table
rules = [k for k in SIM if k.startswith('R')]
short = {rules[0]: 'F-A6 as ruled', rules[1]: 'R2, proposed', rules[2]: 'R3, looser'}
scen = list(SIM[rules[0]].keys())
lines = ['| Scenario | Lines | ' + ' | '.join(G6) + ' | ≥ 4 of 6 | 6 of 6 |', '|---' * (len(G6) + 4) + '|']
for sc in scen:
    for rn in rules[:2]:
        o = SIM[rn][sc]
        lines.append(f'| {sc} | {short[rn]} | ' + ' | '.join(f'{o[c][3]:.2f}' for c in G6) +
                     f" | {o['P(>=4 of 6)']:.3f} | {o['P(6 of 6)']:.3f} |")
out['SIMTABLE'] = '\n'.join(lines) + (
    '\n\n- Each class cell is the share of draws in which that class passes B1 and B2. '
    'R3 (recall ≥ 0.75, presence ≥ A − 0.07, naming ≥ 0.80) is in `sim_gates.json`; it is looser than R2 and buys '
    'little.\n- Pieces per present case, from the 620: ' +
    ', '.join(f"{c} {SIM['pieces_per_present_case'][c][0]:.2f}" for c in G6) + '.')
hr = SIM['human_recall_expected(f=.5,m=.03)']
out['LINES'] = '\n'.join(f'| {c} | {NL[c]} | **{round(hr[c] - .10, 2):.2f}** (human {hr[c]:.3f}) | {A[c] - .05:.3f} | 0.80 |'
                         for c in G6)

# ---- self-test
S = [r for r in R if r.get('score', {}).get('self')]
out['NSELF'] = str(len(S))
rows = ['| Test | Expected | Measured (Σ over cases) |', '|---|---|---|']
def tot(kind, c, k):
    return int(sum(r['score'][kind]['dn'][c][k] for r in S))
def pa(kind, c):
    return np.mean([r['score'][kind]['pres_agree'][c] for r in S])
selfok = all(tot('self', c, 0) == tot('self', c, 1) == tot('self', c, 2) for c in BR) and all(pa('self', c) == 1 for c in BR)
rows.append(f"| Reference vs itself: detection, naming, presence, every class | all 1 | "
            f"{'all 1' if selfok else 'NOT all 1'} ({sum(tot('self', c, 0) for c in BR)} branches) |")
tf = {c: [r['score']['self']['tf1'][c] for r in S if r['score']['self'].get('tf1', {}).get(c) is not None] for c in ('D1', 'D2', 'OM1', 'PDA')}
rows.append('| Reference vs itself: branch tF1 (D1, D2, OM1, PDA) | 1 | ' +
            ', '.join(f'{c} {np.mean(v):.4f} (n {len(v)})' for c, v in tf.items()) + ' |')
tfs = {c: [r['score']['swapD']['tf1'][c] for r in S if r['score']['swapD'].get('tf1', {}).get(c) is not None] for c in ('D1', 'D2', 'OM1', 'PDA')}
rows.append(f"| D1 ↔ D2 swapped | D1, D2 detected all, named 0; branch tF1 0; others 1 | D1 named {tot('swapD','D1',2)}/{tot('swapD','D1',1)}, "
            f"D2 named {tot('swapD','D2',2)}/{tot('swapD','D2',1)}; tF1 " + ', '.join(f'{c} {np.mean(v):.3f}' for c, v in tfs.items()) + ' |')
prevOM2 = np.mean([bool(r['pieces5']['OM2']) for r in S])
rows.append(f"| OM2 deleted | OM2 detected 0; presence agreement = 1 − OM2 prevalence ({1 - prevOM2:.2f}) | detected "
            f"{tot('dropOM2','OM2',1)}/{tot('dropOM2','OM2',0)}; presence {pa('dropOM2','OM2'):.2f} |")
rows.append(f"| PDA relabelled RCA | PDA detected all, named 0 | detected {tot('PDAasRCA','PDA',1)}/{tot('PDAasRCA','PDA',0)}, "
            f"named {tot('PDAasRCA','PDA',2)} |")
mm = sum(r['collapse_mismatch'] for r in R)
mo = sum(r['collapse_mismatch_other'] for r in R)
mo_c = sum(r['collapse_mismatch_other'] > 0 for r in R)
rows.append(f"| collapse4(`to_1f`) vs `territory.to_four`, all {n} cases | 0 voxels outside \"Other\" | {mm} voxels outside "
            f"\"Other\"; {mo} voxels in \"Other\" in {mo_c} cases (Delta's 40 in 2) |")
out['SELFTEST'] = '\n'.join(rows)

# ---- pieces, presence 3 vs 5
rows = ['| Class | Cases with a branch ≥ 5 mm | Branches ≥ 5 mm | Cases with ≥ 2 | Extra pieces of 3–5 mm | Cases present at 3 mm, not 5 mm | Median / p10 branch length (mm) |',
        '|---|---|---|---|---|---|---|']
for c in BR:
    p5 = [r['pieces5'][c] for r in R]
    p3 = [r['pieces3'][c] for r in R]
    L = np.array([x for v in p5 for x in v]) if any(p5) else np.array([0.])
    pres5 = np.array([r['class_mm'][c] >= 5 for r in R]); pres3 = np.array([r['class_mm'][c] >= 3 for r in R])
    rows.append(f"| {c} | {sum(bool(v) for v in p5)} | {sum(len(v) for v in p5)} | {sum(len(v) >= 2 for v in p5)} | "
                f"{sum(len(a) - len(b) for a, b in zip(p3, p5))} | {int((pres3 & ~pres5).sum())} | {np.median(L):.0f} / {np.percentile(L, 10):.0f} |")
out['PIECES'] = '\n'.join(rows)

# ---- bands
tree = np.array([r['bands']['tree_mm3'] for r in R])
rows = ['| Host | 8 mm: mm³ (median [p10, p90]) | × traced tree | 15 mm: mm³ | × traced tree |', '|---|---|---|---|---|']
for h, lab in (('LADtree', 'LAD + D1–D3 (septals, small D3)'), ('RCA', 'RCA (RMA, SN, conus)'), ('proxRCA', 'proximal RCA, 30 mm (SN, conus)'),
               ('proxLCx', 'proximal LCx, 20 mm from the LM (SN, 20 %)'), ('LADtree&RCA', 'overlap LAD and RCA bands'), ('union', 'union of all bands')):
    v8 = np.array([r['bands']['8'].get(h, 0.) for r in R]); v15 = np.array([r['bands']['15'].get(h, 0.) for r in R])
    rows.append(f'| {lab} | {np.median(v8):,.0f} [{np.percentile(v8, 10):,.0f}, {np.percentile(v8, 90):,.0f}] | {np.median(v8 / tree):.0f} | '
                f'{np.median(v15):,.0f} [{np.percentile(v15, 10):,.0f}, {np.percentile(v15, 90):,.0f}] | {np.median(v15 / tree):.0f} |')
out['BANDTABLE'] = '\n'.join(rows) + f'\n\nTraced tree: median {np.median(tree):,.0f} mm³ over {n} cases.'
out['BANDMED'] = (f"{np.median(np.array([r['bands']['8']['union'] for r in R]) / tree):.0f}",
                  f"{np.median(np.array([r['bands']['15']['union'] for r in R]) / tree):.0f}")

# ---- toy
def t(d, b, k):
    r = [x for x in TOY if x['dice'] == d and x['band_mm'] == b and x['n_ext'] == k][0]
    return r
rows = ['| Dice term | Band | S Dice at 10 extended reads | 30 | 60 | Parent Dice at 10 |', '|---|---|---|---|---|---|']
for d in ('oracle', 'naive', 'none', 'leaf', 'leaf_batch', 'leaf_skip', 'marginal', 'ignore'):
    for b in (('0',) if d in ('oracle', 'naive') else ('0', '8', '15')):
        a, bb, cc = t(d, b, 10), t(d, b, 30), t(d, b, 60)
        rows.append(f"| {d} | {b} mm | {a['S_dice'][0]:.2f} ± {a['S_dice'][1]:.2f} | {bb['S_dice'][0]:.2f} ± {bb['S_dice'][1]:.2f} | "
                    f"{cc['S_dice'][0]:.2f} ± {cc['S_dice'][1]:.2f} | {a['P_dice'][0]:.3f} |")
out['TOYTABLE'] = '\n'.join(rows)

# ---- twigs and dominance
E = [r for r in R if 'twigs' in r]
rows = ['| Trunk | Cases with a twig ≥ 3 mm | ≥ 5 mm | ≥ 10 mm | Twigs ≥ 5 mm |', '|---|---|---|---|---|']
for tr in ('LAD', 'LCx', 'RCA'):
    k = [sum(any(x >= L for x in r['twigs'].get(tr, [])) for r in E) for L in (3, 5, 10)]
    tt = sum(sum(x >= 5 for x in r['twigs'].get(tr, [])) for r in E)
    rows.append(f'| {tr} | {k[0]} ({100 * k[0] / len(E):.1f} %) | {k[1]} ({100 * k[1] / len(E):.1f} %) | {k[2]} ({100 * k[2] / len(E):.1f} %) | {tt} |')
out['TWIGS'] = '\n'.join(rows) + f"\n\n{len(E)} cases scored; {sum('twigs_error' in r for r in R)} errors."
out['DOM'] = (f"From the labels: any L-PDA or L-PLA **{DOM['any_left']}** of 620 (left only {DOM['left_only']}, with an R-PDA/R-PLA "
              f"too {DOM['both']}); right only {DOM['right_only']}; neither {DOM['neither']}. L-PDA in {DOM['L-PDA']}, L-PLA in {DOM['L-PLA']}.")
mt = {k: sum(r['map'][k] for r in R) for k in R[0]['map']}
out['MAP'] = (f"`to_1f` on the {n}: D3 from \"Other\" in {mt['d3']} cases; later LAD-side pieces to LAD {mt['d4_to_lad']}; "
              f"LCx-side pieces to LCx {mt['other_lcx']}; two-sided pieces to the nearest class {mt['other_nearest']}; "
              f"pieces touching neither side → 255: {mt['ignore']} (in {sum(r['ignore_voxels'] > 0 for r in R)} cases).")
print(json.dumps(out))
