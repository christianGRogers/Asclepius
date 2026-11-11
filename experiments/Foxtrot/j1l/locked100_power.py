"""Foxtrot, track 1-L round 1: what a paired decision on the locked 100 can resolve, on measured per-case spread.

The decision compares two fixed models (Janus 0 and a Janus 1-L candidate) on the same 100 cases. Its precision is
set by the SD of the per-case paired difference. Janus 0's own per-case file is on Fir, not here, so the spread comes
from the three real paired runs on val 80 in trillium-results (same scorer family, A1 ostia, pinned tF1):
  F1-F0  two warm fine-tunes from one base (closest to 'two similar models');
  B-run1 two from-scratch runs with different recipes;
  F0-B   a warm fine-tune against its own base (closest to 'Janus 1-L vs Janus 0').
Method: each pair's per-case macro (and per-class) differences are centred, resampled with replacement to n cases,
and shifted by a true gain delta. A simulated decision uses the paired 95 % t-interval (the bootstrap interval agrees
to 3 decimals at these n; checked below). 20 000 simulations per cell. Output: results/locked100_power.json.
"""
import json, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
T = os.path.join(ROOT, 'trillium-results')
FILES = {'run1': f'{T}/round6/atlas2/results/per_case_run1.json', 'B': f'{T}/round6/atlas2/results/per_case_b.json',
         'F0': f'{T}/round7/atlas3/per_case_F0.json', 'F1': f'{T}/round7/atlas3/per_case_F1.json'}
PAIRS = [('F1', 'F0'), ('B', 'run1'), ('F0', 'B')]
CL = {'1': 'LM', '2': 'LAD', '3': 'LCx', '4': 'RCA'}
NSIM = 20000


def load(name):
    out = {}
    for r in json.load(open(FILES[name])):
        fl = {str(x) for x in r.get('flagged_classes', [])}
        out[r['case']] = {c: v for c, v in r['per_class'].items() if v is not None and c not in fl}
    return out


def diffs(a, b):
    cases = sorted(set(a) & set(b))
    per = {CL[c]: np.array([a[k][c] - b[k][c] for k in cases if c in a[k] and c in b[k]]) for c in CL}
    mac = []
    for k in cases:
        cs = [c for c in CL if c in a[k] and c in b[k]]
        if cs:
            mac.append(np.mean([a[k][c] for c in cs]) - np.mean([b[k][c] for c in cs]))
    return np.array(mac), per


def sim_lb(d, n, delta, rng, nsim=NSIM):
    """Simulated lower and upper 95 % bounds of the mean paired difference at n cases and true gain delta."""
    x = d - d.mean()
    s = x[rng.integers(0, len(x), (nsim, n))] + delta
    m = s.mean(1); se = s.std(1, ddof=1) / np.sqrt(n)
    return m - 1.984 * se, m


def main():
    rng = np.random.default_rng(20261111)
    M = {k: load(k) for k in FILES}
    res = {'pairs': {}, 'grid': {}, 'class_guard_false_fail': {}, 'notes': []}
    for a, b in PAIRS:
        mac, per = diffs(M[a], M[b])
        res['pairs'][f'{a}-{b}'] = {'n': len(mac), 'macro_sd': round(float(mac.std(ddof=1)), 4),
                                    'per_class_sd': {c: round(float(v.std(ddof=1)), 4) for c, v in per.items()},
                                    'per_class_n': {c: len(v) for c, v in per.items()}}
        # power of 'lower 95 % bound > 0' (superiority) and of 'lower bound > -0.01' (non-inferiority)
        g = {}
        for n in (80, 100):
            for delta in (0.0, 0.005, 0.0075, 0.01, 0.0125, 0.015, 0.02):
                lb, m = sim_lb(mac, n, delta, rng)
                g[f'n{n}_d{delta}'] = {'p_superior': round(float((lb > 0).mean()), 3),
                                       'p_noninferior_m0.01': round(float((lb > -0.01).mean()), 3)}
        res['grid'][f'{a}-{b}'] = g
        # D45 class guard: P(some class mean delta < -0.02) when the true change is zero in every class.
        # Classes resampled jointly by case would need aligned vectors; independent resampling per class is the
        # conservative (higher false-fail) version when class errors are positively correlated.
        ff = {}
        for thr in (-0.02, -0.03):
            fail = np.zeros(NSIM, bool)
            for c, v in per.items():
                n_c = int(round(len(v) * 100 / 80))
                x = v - v.mean(); s = x[rng.integers(0, len(x), (NSIM, n_c))].mean(1)
                fail |= s < thr
            ff[str(thr)] = round(float(fail.mean()), 3)
        res['class_guard_false_fail'][f'{a}-{b}'] = ff
    # cross-check: t-interval vs percentile bootstrap on one real vector at n = 80
    mac, _ = diffs(M['F0'], M['B'])
    bs = mac[rng.integers(0, len(mac), (10000, len(mac)))].mean(1)
    se = mac.std(ddof=1) / np.sqrt(len(mac))
    res['ci_check_F0-B_n80'] = {'t': [round(float(mac.mean() - 1.99 * se), 4), round(float(mac.mean() + 1.99 * se), 4)],
                                'bootstrap': [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)]}
    # minimum detectable effect, 80 % power, two-sided 0.05, normal approx, per pair SD
    for k, p in res['pairs'].items():
        sd = p['macro_sd']
        p['mde_80pct'] = {n: round(2.80 * sd / np.sqrt(n), 4) for n in (80, 100)}
        # a recipe claim adds the seed term (A37: max(measured, 0.012)) for each of two runs
        p['mde_80pct_recipe_claim_n100_sigma0.012'] = round(2.80 * float(np.sqrt(sd ** 2 / 100 + 2 * 0.012 ** 2)), 4)
    json.dump(res, open(os.path.join(HERE, 'results', 'locked100_power.json'), 'w'), indent=1)
    for k, p in res['pairs'].items():
        print(k, p['macro_sd'], p['mde_80pct'], 'recipe', p['mde_80pct_recipe_claim_n100_sigma0.012'], p['per_class_sd'])
        print('   ', {kk: v for kk, v in res['grid'][k].items() if kk.startswith('n100')})
        print('    class guard false-fail', res['class_guard_false_fail'][k])
    print(res['ci_check_F0-B_n80'])


if __name__ == '__main__':
    main()
