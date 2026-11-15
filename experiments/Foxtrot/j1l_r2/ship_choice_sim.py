"""Foxtrot, track 1-L round 2: a1 or the two-run ensemble E as the one candidate read in H1 (Foxtrot v2 section 1).

Question. With one look at the locked 100, does reading E = mean softmax(a1, a2) in a1's place change
  (i) how often a neutral or slightly better model is adopted (H1 at -0.02; the D46 Q4 bar at -0.015),
 (ii) how often a model that is truly worse than Janus 0 by >= 0.01 is adopted,
(iii) how far the adopted model's true quality is from the family mean (the seed lottery)?

Data. The only real pair of replicate-like warm runs on this network family is Round 7's atlas3 F0 and F1 (two
200-epoch warm fine-tunes from one base, val 80; F1 adds an FP term at weight 1e-4, so they are near-replicates),
and the only real run against a different base on the same 80 cases is B (Round 6, the window ablation). Paired by
case, with flagged classes out (A1b), as in experiments/Foxtrot/j1l/locked100_power.py:
  a1 - J0  ~  F0 - B                      (a single warm run against a different model)
  a2 - a1  ~  F1 - F0                     (two warm runs of one recipe)
  E  - J0  ~  (F0 + F1)/2 - B             (E's per-case score taken as the mean of its members' scores)
The last line is an approximation: an ensemble's tree-F1 is not the mean of its members' tree-F1. It is neutral on
average (where one member connects a branch and the other cuts it, E may do either) and it gives E no ensemble gain;
any real gain (Mehrtash et al. 2020) is added separately as delta_E.

Simulation. Per draw: 100 cases resampled with replacement from the 80 (jointly, so the a1/a2/J0 structure per case
is kept), every per-case difference centred, then shifted by the true effect delta plus the run-level terms
g1, g2 ~ N(0, sigma_g^2) (E gets (g1 + g2)/2 + delta_E). The decision uses the paired 95 % t-interval's lower bound,
as locked100_power.py does (the bootstrap agrees to 3 decimals at n = 100). Class guards, L3 and FP are not modelled
here; they act the same on both candidates to first order. 20 000 draws per cell.
Output: results/ship_choice_sim.json.  Run: python3 ship_choice_sim.py   (about 1 min)
"""
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
T = os.path.join(ROOT, 'trillium-results')
FILES = {'B': f'{T}/round6/atlas2/results/per_case_b.json',
         'F0': f'{T}/round7/atlas3/per_case_F0.json', 'F1': f'{T}/round7/atlas3/per_case_F1.json'}
NSIM, N = 20000, 100
T975 = 1.984


def load(name):
    out = {}
    for r in json.load(open(FILES[name])):
        fl = {str(x) for x in r.get('flagged_classes', [])}
        out[r['case']] = {c: v for c, v in r['per_class'].items() if v is not None and c not in fl}
    return out


def per_case(M):
    """Per-case macro of each run over the classes all three runs score (so the three differences are coherent)."""
    cases = sorted(set(M['B']) & set(M['F0']) & set(M['F1']))
    rows = []
    for k in cases:
        cs = [c for c in M['B'][k] if c in M['F0'][k] and c in M['F1'][k]]
        if cs:
            rows.append([np.mean([M[r][k][c] for c in cs]) for r in ('B', 'F0', 'F1')])
    return np.array(rows)          # columns: J0 (B), a1 (F0), a2 (F1)


def simulate(X, delta, sigma_g, delta_e, rng):
    j0, a1, a2 = X[:, 0], X[:, 1], X[:, 2]
    d_a1 = a1 - j0
    d_e = (a1 + a2) / 2 - j0
    d_a1, d_e = d_a1 - d_a1.mean(), d_e - d_e.mean()
    idx = rng.integers(0, len(X), (NSIM, N))
    g = rng.normal(0, sigma_g, (NSIM, 2)) if sigma_g > 0 else np.zeros((NSIM, 2))
    out = {}
    for name, d, run_term, extra in (('a1', d_a1, g[:, 0], 0.0), ('E', d_e, g.mean(1), delta_e)):
        true = delta + run_term + extra                    # the candidate's true mean effect vs Janus 0
        s = d[idx] + true[:, None]
        m = s.mean(1)
        lb = m - T975 * s.std(1, ddof=1) / np.sqrt(N)
        h1 = lb > -0.02
        q4 = lb > -0.015
        out[name] = {'P_H1_pass': round(float(h1.mean()), 3),
                     'P_adopt_noninferior_Q4': round(float(q4.mean()), 3),
                     'P_H3_tF1_superior': round(float((lb > 0).mean()), 3),
                     'P_adopted_and_truly_worse_by_0.01': round(float((q4 & (true <= -0.01)).mean()), 4),
                     'P_adopted_and_truly_worse_by_0.005': round(float((q4 & (true <= -0.005)).mean()), 4),
                     'SD_true_effect_of_shipped_model': round(float(true.std()), 4)}
    return out


def main():
    rng = np.random.default_rng(20261115)
    M = {k: load(k) for k in FILES}
    X = per_case(M)
    sd = lambda v: round(float(np.std(v, ddof=1)), 4)  # noqa: E731
    meas = {'n_cases': int(len(X)),
            'sd_a1_minus_J0 (F0-B)': sd(X[:, 1] - X[:, 0]),
            'sd_E_minus_J0 ((F0+F1)/2-B)': sd((X[:, 1] + X[:, 2]) / 2 - X[:, 0]),
            'sd_a2_minus_a1 (F1-F0)': sd(X[:, 2] - X[:, 1]),
            'mean_a2_minus_a1 (F1-F0)': round(float(np.mean(X[:, 2] - X[:, 1])), 4),
            'sigma_g_1df_from_F1_F0': None,
            'share_of_cases_where_runs_differ_by_more_than_0.05': round(float(np.mean(np.abs(X[:, 2] - X[:, 1]) > 0.05)), 3)}
    d = X[:, 2] - X[:, 1]
    se = d.std(ddof=1) / np.sqrt(len(d))
    meas['sigma_g_1df_from_F1_F0'] = round(float(np.sqrt(max(d.mean() ** 2 - se ** 2, 0) / 2)), 4)
    for name, col in (('a1', (X[:, 1] - X[:, 0])), ('E', ((X[:, 1] + X[:, 2]) / 2 - X[:, 0]))):
        meas[f'mde80_n100_{name}'] = round(float((1.96 + 0.8416) * np.std(col, ddof=1) / np.sqrt(N)), 4)
    grid = {}
    for sigma_g in (0.0, 0.005, 0.012):
        for delta_e in (0.0, 0.003):
            for delta in (-0.015, -0.01, -0.005, 0.0, 0.003, 0.005):
                grid[f'sigma_g={sigma_g} delta_E={delta_e} delta={delta}'] = simulate(X, delta, sigma_g, delta_e, rng)
    res = {'measured': meas, 'grid': grid,
           'notes': ['E-J0 per case is approximated by the mean of its members\' scores (no ensemble gain); '
                     'delta_E adds a hypothetical gain.',
                     'Run-level terms are N(0, sigma_g^2); A37 floor 0.012; the F1-F0 one-df estimate is small.']}
    json.dump(res, open(os.path.join(HERE, 'results', 'ship_choice_sim.json'), 'w'), indent=1)
    print(json.dumps(meas, indent=1))
    for k in ('sigma_g=0.0 delta_E=0.0 delta=0.0', 'sigma_g=0.005 delta_E=0.0 delta=0.0',
              'sigma_g=0.012 delta_E=0.0 delta=0.0', 'sigma_g=0.012 delta_E=0.0 delta=-0.01',
              'sigma_g=0.005 delta_E=0.0 delta=-0.01', 'sigma_g=0.005 delta_E=0.003 delta=0.0',
              'sigma_g=0.0 delta_E=0.0 delta=-0.01', 'sigma_g=0.012 delta_E=0.0 delta=0.005'):
        print(k, json.dumps(grid[k]))


if __name__ == '__main__':
    main()
