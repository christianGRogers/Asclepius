"""Judge, Janus 1-F round 2: every advocate's proposed B lines, evaluated under two advocates' human models
(Bridge's DSC-mixture model, both modes, and Atlas's clDice-mixture model, nine scenarios), plus power rows.
Locked counts only (98/64/84/40/96/96). CPU, no data read except Atlas's committed 620 piece census."""
import json, sys, importlib.util
import numpy as np
R = sys.argv[1]
def load(name, path):
    s = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
B = load('bgs', f'{R}/experiments/Bridge/j1f_r2/gate_sim.py')
A = load('ags', f'{R}/experiments/Atlas/j1f_r2/gate_sim.py')
T1A = {c: v[0] for c, v in B.TABLE1.items()}
C = ['D1', 'D2', 'OM1', 'OM2', 'PDA', 'PLB']
def flat(rec, nam, marg):  # (recall, presence, naming)
    return {c: (rec[c] if isinstance(rec, dict) else rec, T1A[c] - marg, nam[c] if isinstance(nam, dict) else nam) for c in C}
SETS = {
 'ruled': flat(.80, .85, .05),
 'Atlas P1': {'D1': (.81, .94, .83), 'D2': (.76, .84, .86), 'OM1': (.75, .90, .78), 'OM2': (.60, .81, .78), 'PDA': (.89, .97, .90), 'PLB': (.89, .94, .92)},
 'Bridge': {'D1': (.80, .919, .83), 'D2': (.80, .83, .86), 'OM1': (.80, .89, .76), 'OM2': (.73, .81, .77), 'PDA': (.80, .938, .89), 'PLB': (.80, .912, .92)},
 'Crucible R2': flat({'D1': .85, 'D2': .79, 'OM1': .84, 'OM2': .72, 'PDA': .86, 'PLB': .85}, .80, .05),
 'Delta F2-1': flat(.75, .80, .05),
 'Foxtrot R2': flat({'D1': .80, 'D2': .80, 'OM1': .80, 'OM2': .744, 'PDA': .80, 'PLB': .80}, {'D1': .85, 'D2': .817, 'OM1': .85, 'OM2': .744, 'PDA': .85, 'PLB': .85}, .05),
 'Judge J2': {'D1': (.80, .919, .80), 'D2': (.75, .83, .80), 'OM1': (.75, .89, .75), 'OM2': (.60, .80, .75), 'PDA': (.80, .938, .85), 'PLB': (.80, .912, .85)},
}
out = {}
rng = np.random.default_rng(20261123)
pdist = A.pieces_dist(f'{R}/experiments/Atlas/j1f_r2/census_r2.jsonl')
for name, L in SETS.items():
    row = {}
    for mode in ('symmetric', 'misses_only'):
        per, agg = B.simulate(40000, rng, mode, L)
        row[f'Bridge {mode}'] = {'per_class_fail': {c: per[c]['fail_class'] for c in C}, 'verdict_fail': agg['P(<4 of 6 pass)']}
    per, agg = B.simulate(40000, rng, 'symmetric', L, q_scale=2, miss_scale=2)
    row['Bridge 2x errors (power)'] = {'per_class_fail': {c: per[c]['fail_class'] for c in C}, 'verdict_fail': agg['P(<4 of 6 pass)']}
    prop = {c: {'recall': L[c][0], 'presence': L[c][1], 'naming': L[c][2]} for c in C}
    worst = {c: 0.0 for c in C}; vworst = 0.0
    for sh in (0.05, 0.08, 0.12):
        for s in (0.0, 0.5, 1.0):
            r = A.simulate_lines(A.params(sh), pdist, prop, s, sh, reps=1000, seed=1)
            for c in C: worst[c] = max(worst[c], r[c]['fail_rate'])
            vworst = max(vworst, r['verdict_fail_rate'])
    row['Atlas worst of 9 scenarios'] = {'per_class_fail': worst, 'verdict_fail': vworst}
    for lab, sh in (('omission +0.10', {'dm': .10}), ('misnaming 0.10', {'dn': .10}), ('misnaming 0.20', {'dn': .20})):
        r = A.simulate_lines(A.params(.08), pdist, prop, .5, .08, reps=1000, seed=2, shift=sh)
        row[f'Atlas power {lab}'] = {'per_class_fail': {c: r[c]['fail_rate'] for c in C}, 'verdict_fail': r['verdict_fail_rate']}
    out[name] = row
    print(name)
    for k, v in row.items():
        print(f'  {k:32s}', ' '.join(f'{c}={v["per_class_fail"][c]:.3f}' for c in C), f'| <4of6={v["verdict_fail"]:.3f}')
json.dump({'sets': SETS, 'results': out}, open(sys.argv[2], 'w'), indent=1)
