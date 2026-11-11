"""Bridge, track 1-L round 1: what the locked 100 can decide, and the operating characteristics of the
pre-registered Janus 1-L rule (Bridge v1 §4).

Data (no new scoring; all already in the repository, all on ImageCAS val 80, A1c-pinned tF1, TotalSegmentator aortas):
  * "a new model vs its parent" per-case paired difference: atlas2 B - run 1 (two from-scratch runs, Round 6) and
    atlas3 F1 - F0 (two warm fine-tunes from one checkpoint, Round 7). Both are thick-reference (D0-era) models, so
    they are used for the SHAPE of the per-case difference, centred to mean 0, then shifted by a true effect delta.
  * "replicate noise" a2 - a1: atlas3 F1 - F0 on the same case (the only measured warm replicate).
  * Pessimistic scaling to Janus 0's wider spread: each class column x (Janus 0 per-case SD / run 1 per-case SD),
    Janus 0's SDs recovered from its CIs (Atlas, Round 10): LM 0.121, LAD 0.126, LCx 0.135, RCA 0.079.
Per-case decisive macro = mean of the classes not flagged in either model (A1b).

The rule simulated (Bridge v1 §4.2), on n = 100 locked cases, percentile bootstrap (B = 1000) per simulated study:
  ADOPT  = L1: lower 95 % bound of macro Delta(a1 - J0) > -m
         & L2: no class mean Delta(a1 - J0) < -0.03
         & L4: a2's macro Delta point estimate > -m
  BETTER = ADOPT & lower 95 % bound of macro Delta(a1 - J0) > 0
(L3, the centreline-recall guard, needs recall rows the old files do not all have; it is not simulated.)

    python3 experiments/Bridge/j1l_r1/locked100_power.py      # ~1-2 CPU minutes; writes locked100_power.json
"""
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
TR = os.path.join(REPO, 'trillium-results')
CL = ['1', '2', '3', '4']
NAMES = dict(zip(CL, ['LM', 'LAD', 'LCx', 'RCA']))
J0_SD = {'1': 0.121, '2': 0.126, '3': 0.135, '4': 0.079}


def load(p):
    return {r['case']: r for r in json.load(open(os.path.join(TR, p)))}


def pair(a, b):
    """Per-case per-class paired difference b - a; NaN where flagged in either or missing."""
    cases = sorted(set(a) & set(b))
    D = np.full((len(cases), 4), np.nan)
    for i, c in enumerate(cases):
        fl = set(map(str, a[c].get('flagged_classes') or [])) | set(map(str, b[c].get('flagged_classes') or []))
        for j, k in enumerate(CL):
            x, y = a[c]['per_class'].get(k), b[c]['per_class'].get(k)
            if k not in fl and x is not None and y is not None:
                D[i, j] = y - x
    return cases, D


def class_sd(p):
    rows = load(p)
    out = {}
    for j, k in enumerate(CL):
        v = [r['per_class'].get(k) for r in rows.values()
             if r['per_class'].get(k) is not None and k not in set(map(str, r.get('flagged_classes') or []))]
        out[k] = float(np.std(v, ddof=1))
    return out


run1, b = load('round6/atlas2/results/per_case_run1.json'), load('round6/atlas2/results/per_case_b.json')
f0, f1 = load('round7/atlas3/per_case_F0.json'), load('round7/atlas3/per_case_F1.json')
cs, D_scr = pair(run1, b)
cw, D_warm = pair(f0, f1)
assert cs == cw, 'the two pairs are on the same 80 val cases'
sd1 = class_sd('round6/atlas2/results/per_case_run1.json')
SCALE = np.array([J0_SD[k] / sd1[k] for k in CL])


def macro(D):
    return np.nanmean(D, axis=-1)


def centred(D, passes=50):
    """Zero every class mean AND the per-case macro mean (flagged classes make the two differ)."""
    D = D.copy()
    for _ in range(passes):
        D = D - np.nanmean(D, axis=0)
        D = D - np.nanmean(macro(D))
    return D


rng = np.random.default_rng(20261111)


def simulate(base, rep, delta_vec, n=100, sims=2000, B=1000, margins=(0.01, 0.015, 0.02)):
    """base: per-case a1-J0 shape (centred); rep: per-case a2-a1 (centred); delta_vec: true shift per class."""
    N = base.shape[0]
    res = {f'adopt_m{m}': 0 for m in margins}
    res.update({f'better_m{m}': 0 for m in margins})
    res.update(L2_fail=0, lo_mean=0.0, sd_macro_delta=[])
    for _ in range(sims):
        idx = rng.integers(0, N, n)
        D1 = base[idx] + delta_vec
        D2 = D1 + rep[idx]
        m1 = macro(D1)
        res['sd_macro_delta'].append(np.nanstd(m1, ddof=1))
        boot = rng.integers(0, n, (B, n))
        bm = np.nanmean(m1[boot], axis=1)
        lo = np.percentile(bm, 2.5)
        cls = np.nanmean(D1, axis=0)
        l2 = bool(np.all(cls >= -0.03))
        p2 = float(np.nanmean(macro(D2)))
        res['L2_fail'] += (not l2)
        res['lo_mean'] += lo
        for m in margins:
            ok = (lo > -m) and l2 and (p2 > -m)
            res[f'adopt_m{m}'] += ok
            res[f'better_m{m}'] += ok and lo > 0
    out = {k: round(v / sims, 3) for k, v in res.items() if k != 'sd_macro_delta'}
    out['sd_macro_delta'] = round(float(np.median(res['sd_macro_delta'])), 4)
    return out


scenarios = {
    'optimistic (warm-replicate shape, measured scale)': (centred(D_warm), centred(D_warm)),
    'central (scratch-pair shape, measured scale)': (centred(D_scr), centred(D_warm)),
    'pessimistic (scratch-pair shape x Janus 0 spread)': (centred(D_scr) * SCALE, centred(D_warm) * SCALE),
}
# Atlas's upper pessimistic bound (Round 10): SD of the macro paired difference 0.072
_k = 0.072 / float(np.nanstd(macro(centred(D_scr) * SCALE), ddof=1))
scenarios['harsh (pessimistic, macro SD 0.072, Atlas R10 upper)'] = (centred(D_scr) * SCALE * _k, centred(D_warm) * SCALE * _k)
effects = {
    'uniform -0.03': np.full(4, -0.03), 'uniform -0.02': np.full(4, -0.02), 'uniform -0.01': np.full(4, -0.01),
    'zero': np.zeros(4), 'uniform +0.005 (data scaling, high)': np.full(4, 0.005),
    'uniform +0.01': np.full(4, 0.01), 'uniform +0.02': np.full(4, 0.02),
    'LCx only -0.05 (macro -0.0125)': np.array([0, 0, -0.05, 0]),
}
out = {'n_locked': 100, 'scale_pessimistic': dict(zip([NAMES[k] for k in CL], np.round(SCALE, 3).tolist())),
       'measured_sd_macro_delta': {'scratch pair': round(float(np.nanstd(macro(D_scr), ddof=1)), 4),
                                   'warm replicate': round(float(np.nanstd(macro(D_warm), ddof=1)), 4)},
       'mde_80pct_two_sided': {}, 'grid': {}}
for name, (base, rep) in scenarios.items():
    sd = float(np.nanstd(macro(base), ddof=1))
    out['mde_80pct_two_sided'][name] = {'sd_delta': round(sd, 4), 'mde_n100': round(2.80 * sd / 10, 4)}
    out['grid'][name] = {}
    for ename, dv in effects.items():
        out['grid'][name][ename] = simulate(base, rep, dv)
        print(name, '|', ename, out['grid'][name][ename], flush=True)

# What +60 cases (560 -> 620) buys, if decisive error 1 - tF1 follows a power law in training-set size
# (Hestness et al. 2017, arXiv:1712.00409: exponents between -0.07 and -0.35 across domains; ImageNet top-1 -0.309).
e0 = 1 - 0.909
out['data_scaling_gain'] = {f'beta {bta}': round(e0 - e0 * (620 / 560) ** bta, 4) for bta in (-0.07, -0.128, -0.309, -0.5)}
print(out['mde_80pct_two_sided'], out['data_scaling_gain'])
json.dump(out, open(os.path.join(HERE, 'locked100_power.json'), 'w'), indent=1)
