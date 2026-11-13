"""Crucible, Janus 1-L Round 2: what changes if the ensemble E = mean softmax of (a1, a2) replaces a1 as the one
candidate in the locked-100 sequence (Janus 1-L Round 1, section 5 item 1; D46 Q6).

Question. E is tested *instead of* a1, in the same H1 -> H2 -> H3 sequence, so the locked 100 is still looked at once.
What does that swap buy or cost on the tF1 tests, under the noise we have measured?

Model of the paired per-case difference against Janus 0 (n = 100):

    D_X(c) = delta + g_X + d(c) + r_X(c)

  delta  the recipe's true effect (60 more cases, 250 more epochs), shared by a1, a2 and E;
  d(c)   the per-case part of the recipe's effect that every run of it shares;
  r_X(c) the run-specific per-case part; g_X the run-specific mean offset (the "seed lottery", A37).

Inputs, all measured, none from the locked 100 or a sealed case:
  * the warm pair atlas3 F0 / F1 (Round 8: two 200-epoch warm runs from one parent, the same data stream; F1 adds an
    FP term that changed nothing detectable). Their per-case decisive-macro difference is r_F0 - r_F1, so its spread
    gives sigma_r = SD(F0 - F1) / sqrt(2) and its *shape* (heavy tails) is resampled for r and d;
  * the total paired SD S of (candidate - Janus 0), the round-1 range 0.038-0.074 (Crucible/Delta/Bridge v1);
  * sigma_g in {0.004, 0.008, 0.012}: the F0 - F1 mean gives a 1-df 0.003; A37's floor is 0.012.

The ensemble. Averaging two runs' softmax is not averaging their scores. The model writes the ensemble's
run-specific variance as kappa * (a single run's), for both r and g: kappa = 0.5 is "E behaves like the mean of its two
members' scores" (the most E can gain from variance), kappa = 1 is "E is no less noisy than a1" (no gain). An
ensemble *mean* bonus beta (E better than its members on average) is set to 0 (claimed nothing) or +0.003.

Tests (one-sided 2.5 %, normal-t bound on the mean, as round 1's power scripts):
  H1 macro  lower bound > -0.02 (L-A5's macro clause; the class, L3 and FP clauses are not modelled here);
  Q4        lower bound > -0.015 (D46 Q4: adoption on non-inferiority alone);
  H3        lower bound > 0.
Also: P(the shipped model is truly worse than Janus 0 by more than 0.01), i.e. delta + g (+ beta) < -0.01, and the
same jointly with passing H1: the chance of adopting an unlucky draw.

CPU, about a minute. Opens no image, no label, no read, no locked-100 or sealed case.
Usage: python3 ensemble_oc.py > ensemble_oc.json
"""
from __future__ import annotations

import json
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
TR = os.path.join(REPO, 'trillium-results', 'round7', 'atlas3')
RNG = np.random.default_rng(20261113)
N = 100
N_SIM = 20000
Z = 1.96


def decisive_macro(row):
    fl = set(row.get('flagged_classes') or [])
    v = [x for k, x in (row.get('per_class') or {}).items() if x is not None and int(k) not in fl]
    return float(np.mean(v)) if v else None


def warm_pair():
    a = {r['case']: decisive_macro(r) for r in json.load(open(os.path.join(TR, 'per_case_F0.json')))}
    b = {r['case']: decisive_macro(r) for r in json.load(open(os.path.join(TR, 'per_case_F1.json')))}
    common = sorted(c for c in set(a) & set(b) if a[c] is not None and b[c] is not None)
    return np.array([a[c] - b[c] for c in common])


def simulate(shape, S, sigma_g, kappa, beta, delta):
    """One scenario. `shape` is the centred, unit-SD empirical shape of a per-case difference."""
    sigma_r = SHAPE_SD_R
    var_d = max(S * S - sigma_r * sigma_r, 0.0)
    idx = lambda: RNG.integers(0, len(shape), size=(N_SIM, N))  # noqa: E731
    d = shape[idx()] * math.sqrt(var_d)
    r1 = shape[idx()] * sigma_r
    r2 = shape[idx()] * sigma_r
    g1 = RNG.normal(0, sigma_g, N_SIM)
    g2 = RNG.normal(0, sigma_g, N_SIM)
    # a1
    da1 = delta + g1[:, None] + d + r1
    # E: run-specific parts shrink to kappa x a single run's variance (kappa = 0.5: the mean of the two members)
    s = math.sqrt(2.0 * kappa)
    rE = (r1 + r2) / 2.0 * s
    gE = (g1 + g2) / 2.0 * s
    dE = delta + beta + gE[:, None] + d + rE
    out = {}
    for name, D, truth in (('a1', da1, delta + g1), ('E', dE, delta + beta + gE)):
        m = D.mean(1)
        lb = m - Z * D.std(1, ddof=1) / math.sqrt(N)
        h1 = lb > -0.02
        bad = truth < -0.01
        out[name] = dict(p_H1_macro=round(float(h1.mean()), 3), p_Q4=round(float((lb > -0.015).mean()), 3),
                         p_H3=round(float((lb > 0).mean()), 3), p_truly_worse_0p01=round(float(bad.mean()), 3),
                         p_pass_H1_and_truly_worse=round(float((h1 & bad).mean()), 4),
                         paired_sd=round(float(D.std(1, ddof=1).mean()), 4))
    return out


if __name__ == '__main__':
    diff = warm_pair()
    sd_pair = float(diff.std(ddof=1))
    SHAPE = (diff - diff.mean()) / sd_pair            # unit-SD empirical shape, heavy tails kept
    SHAPE_SD_R = sd_pair / math.sqrt(2.0)             # sigma_r: one run's run-specific per-case SD
    res = dict(inputs=dict(pair='atlas3 F0 - F1 (Round 8), decisive macro, val 80', n=int(len(diff)),
                           mean=round(float(diff.mean()), 4), sd=round(sd_pair, 4),
                           sigma_r=round(SHAPE_SD_R, 4),
                           sigma_g_1df=round(float(math.sqrt(max(diff.mean() ** 2 - sd_pair ** 2 / len(diff), 0)
                                                             / 2.0)), 4),
                           n_sim=N_SIM, n_locked=N), scenarios=[])
    for S in (0.038, 0.055, 0.074):
        for sigma_g in (0.004, 0.008, 0.012):
            for kappa in (0.5, 0.75, 1.0):
                for beta in (0.0, 0.003):
                    if kappa == 1.0 and beta:
                        continue
                    for delta in (-0.02, -0.01, 0.0, 0.005, 0.01):
                        res['scenarios'].append(dict(S=S, sigma_g=sigma_g, kappa=kappa, beta=beta, delta=delta,
                                                     **simulate(SHAPE, S, sigma_g, kappa, beta, delta)))
    print(json.dumps(res, indent=1))
