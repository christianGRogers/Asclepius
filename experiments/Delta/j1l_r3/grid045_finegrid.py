"""Delta, Janus 1-L round 3: grid045_phantom.py re-run for the two scenarios where t moves, with Rule T on a 0.025
grid (0.60 ... 0.25) instead of 0.05. Same trees (seed 21), same rule_t.py functions; writes grid045_finegrid.json.
Usage: python grid045_finegrid.py   (about 1-2 min)
"""
import os
import sys, json, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grid045_phantom as g
FINE = [round(x, 3) for x in np.arange(0.60, 0.2499, -0.025)]
g.GRID = FINE
g.rule_t.GRID = tuple(FINE)
rng = np.random.default_rng(21)
from scipy.spatial import cKDTree
sets = {}
for k in ('tuning', 'drift', 'locked'):
    sets[k] = [(lambda a: (cKDTree(a[0]), a[1], a[2]))(g.tp.tree(rng)) for _ in range(8)]
tstar = 0.40
j0 = [g.model_native(t, 'janus0') >= tstar for t in sets['drift']]
lg = [g.truth(t) for t in sets['locked']]
res = {}
for kind in ('softer', 'width_gain'):
    pooled = {t: [] for t in FINE}
    for t_, m0 in zip(sets['drift'], j0):
        p = g.model_native(t_, kind)
        d = g.rule_t.case_diffs(m0, {t: p >= t for t in FINE}, g.NATIVE)
        for t in FINE: pooled[t].append(d[t])
    dr = {t: g.rule_t.trimmed(np.concatenate(pooled[t])) for t in FINE}
    tS = g.rule_t.choose(dr, tstar)
    lp = [g.model_native(t, kind) for t in sets['locked']]
    dl = {t: float(np.mean([g.dice(p >= t, q) for p, q in zip(lp, lg)])) for t in FINE}
    tor = max((t for t in FINE if t <= 0.5), key=lambda t: dl[t])
    res[kind] = dict(t_rule_T_fine=tS, t_oracle_fine=tor, dice_rule_T=round(dl[tS], 4), dice_oracle=round(dl[tor], 4),
                     dice_frozen=round(dl[tstar], 4), dr={f'{t:.3f}': round(v, 4) for t, v in dr.items()})
    print(kind, res[kind]['t_rule_T_fine'], res[kind]['t_oracle_fine'], res[kind]['dice_frozen'], res[kind]['dice_rule_T'], res[kind]['dice_oracle'], flush=True)
json.dump(res, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'grid045_finegrid.json'), 'w'), indent=1)
