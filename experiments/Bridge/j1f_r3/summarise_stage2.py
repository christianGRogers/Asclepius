"""Summarise stage2_sim.jsonl into false-fail rates of F-A22's numbers for a CORRECT stage-2 model (and the
proposed replacements). Decision rules as F-A22 words them, each at one-sided 1.25 %:
  L1  per parent group, the bootstrap 98.75 % upper bound of the pooled stolen share over 100 cases <= 0.02;
  L2  the Clopper-Pearson 98.75 % lower bound of the share of cases with no stage-2 voxel > 30 mm from stage-1
      foreground >= 0.95 (so it needs 100 of 100: 99 of 100 gives 0.938);
  L2' (proposed) the same count rule on islands: a stage-2 26-component whose nearest voxel is > 5 mm from stage-1
      foreground; read on the POINT share (>= 95 of 100), not a bound;
  K1  on 20 cases, each class's pooled share of predicted voxels inside the traced lumen <= 0.05;
  K1' (proposed) on 20 cases, L1's stolen-centreline share <= 0.03 in each parent group.
Locked-size samples (100 cases; 20 for K1) are drawn with replacement from the simulated training cases.
Usage: python3 summarise_stage2.py stage2_sim.jsonl > stage2_summary.json"""
import json, sys
import numpy as np
from scipy.stats import beta

rows = [json.loads(l) for l in open(sys.argv[1])]
rng = np.random.default_rng(20261123)
B, NB = 400, 1000
a = 0.0125
out = {'cases_simulated': len(rows), 'runs': {}}
for run in sorted(rows[0]['runs']):
    rr = [r['runs'][run] for r in rows if run in r['runs']]
    n = len(rr)
    res = {'n': n}
    # per-case values
    for g in ('LAD', 'RCA', 'LCx'):
        st = np.array([x['L1'].get(g, [0, 0])[0] for x in rr], float)
        tot = np.array([x['L1'].get(g, [0, 0])[1] for x in rr], float)
        res[f'L1_{g}_share'] = round(st.sum() / max(tot.sum(), 1), 4)
        if st.sum() == 0:
            res[f'L1_{g}_falsefail'] = 0.0
            continue
        fails = 0
        for _ in range(B):
            idx = rng.integers(0, n, 100)
            s, t = st[idx], tot[idx]
            bs = []
            for _ in range(NB // 4):
                j = rng.integers(0, 100, 100)
                bs.append(s[j].sum() / t[j].sum())
            fails += np.quantile(bs, 1 - a) > 0.02
        res[f'L1_{g}_falsefail'] = round(fails / B, 3)
    far = np.array([x['L2_max_mm'] > 30 for x in rr])
    isl = np.array([x['L2_island_mm'] > 5 for x in rr])
    res['L2_cases_beyond_30mm'] = round(float(far.mean()), 3)
    res['L2_max_mm_median'] = float(np.median([x['L2_max_mm'] for x in rr]))
    f_l2 = f_l2p = 0
    for _ in range(2000):
        idx = rng.integers(0, n, 100)
        k = 100 - int(far[idx].sum())
        lo = beta.ppf(a, k, 100 - k + 1) if k > 0 else 0.0
        f_l2 += lo < 0.95
        f_l2p += (100 - int(isl[idx].sum())) < 95
    res['L2_falsefail'] = round(f_l2 / 2000, 3)
    res['L2prime_falsefail'] = round(f_l2p / 2000, 3)
    # K1
    k1 = {}
    for c in ('S1', 'S2', 'S3', 'SN', 'Conus', 'RMA'):
        ins = np.array([x['K1'][c][0] for x in rr if c in x['K1']], float)
        tot = np.array([x['K1'][c][1] for x in rr if c in x['K1']], float)
        if not len(tot):
            continue
        ff = 0
        for _ in range(2000):
            idx = rng.integers(0, len(tot), 20)
            ff += ins[idx].sum() / max(tot[idx].sum(), 1) > 0.05
        k1[c] = {'share': round(ins.sum() / tot.sum(), 4), 'falsefail_LEAK': round(ff / 2000, 3), 'n': int(len(tot))}
    res['K1'] = k1
    # K1' (proposed): L1's centreline statistic on the 20 fit-check training cases, LEAK above 0.03 in any group
    st = np.array([[x['L1'].get(g, [0, 0])[0] for g in ('LAD', 'LCx', 'RCA')] for x in rr], float)
    tot = np.array([[x['L1'].get(g, [0, 0])[1] for g in ('LAD', 'LCx', 'RCA')] for x in rr], float)
    ff = 0
    for _ in range(2000):
        idx = rng.integers(0, n, 20)
        ff += (st[idx].sum(0) / np.maximum(tot[idx].sum(0), 1) > 0.03).any()
    res['K1prime_falsefail_LEAK'] = round(ff / 2000, 3)
    out['runs'][run] = res
print(json.dumps(out, indent=1))
