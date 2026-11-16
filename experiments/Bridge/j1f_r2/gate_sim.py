"""Janus 1-F round 2, item 1: false-fail rate of F-A6's B gates for a human-level model on the locked 100.

A "human-level model" is a second ImageCAS-X analyst: it agrees with the reference as well as ImageCAS-X's second,
blinded analyst agreed with the first (Table 1 of arXiv:2608.30404: per-segment presence agreement, and DSC on cases
where both analysts drew the segment). No image, label or model output is read. CPU only, seconds.

Model of the human reader, per class c (locked count n_c of 100, prevalence pi = n_c / 100):
  presence  : agreement ~ Binomial(100, A_c) / 100                        (A_c from Table 1)
  detection : a reference branch is missed with probability a_c.
              symmetric: discordant cases split evenly between miss and extra call (a = d / 2pi, d = 1 - A_c),
                         capped so extra calls do not exceed the negatives;
              misses-only (pessimistic): every discordant case is a miss (a = d / pi).
  naming    : a detected branch carries the wrong name with probability q_c, the weight at DSC ~ 0 of a two-part
              mixture fitted to Table 1's DSC mean and SD (good part ~ N(mu, 0.08^2), mu free; see fit_q).
Each detected branch is named independently; branches = cases (PDA's second pieces are ignored, which favours the gate).

Usage: python3 gate_sim.py [draws] > gate_sim.json
"""
import json
import sys

import numpy as np
from scipy.optimize import brentq

# ImageCAS-X Table 1: inter-observer presence agreement, DSC mean, DSC SD (160 test cases)
TABLE1 = {'D1': (.969, .799, .287), 'D2': (.894, .829, .243), 'OM1': (.944, .741, .323),
          'OM2': (.875, .777, .291), 'PDA': (.988, .826, .219), 'PLB': (.962, .836, .186)}
# Locked-100 reference counts (Delta v1's census; label counts only, F-A7)
LOCKED = {'D1': 98, 'D2': 64, 'OM1': 84, 'OM2': 40, 'PDA': 96, 'PLB': 96}
# F-A6 as ruled in round 1
RECALL_LINE, PRES_MARGIN, NAMING_LINE, K_OF_6 = 0.80, 0.05, 0.85, 4


def fit_q(m, s, sg=0.08):
    """Share of co-present cases at DSC ~ 0, from mean m and SD s, good part with SD sg."""
    return brentq(lambda q: m * m / (1 - q) + (1 - q) * sg * sg - (s * s + m * m), 1e-6, 0.9)


def miss_rate(A, pi, mode):
    d = 1 - A
    if mode == 'misses_only':
        return min(1.0, d / pi)
    extra = min(d / 2, 1 - pi)
    return (d - extra) / pi


def simulate(draws, rng, mode, lines, q_scale=1.0, miss_scale=1.0):
    passes, per = {}, {}
    for c, (A, m, s) in TABLE1.items():
        n = LOCKED[c]
        q = min(1.0, fit_q(m, s) * q_scale)
        a = min(1.0, miss_rate(A, n / 100, mode) * miss_scale)
        pres = rng.binomial(100, A, draws) / 100
        det = rng.binomial(n, 1 - a, draws)
        rec = det / n
        named = rng.binomial(det, 1 - q) / np.maximum(det, 1)
        rl, pl, nl = lines[c]
        ok_r, ok_p, ok_n = rec >= rl, pres >= pl, named >= nl
        ok = ok_r & ok_p & ok_n
        passes[c] = ok
        per[c] = {'n': n, 'miss_rate': round(a, 4), 'misname_rate_q': round(q, 4),
                  'E_recall': round(1 - a, 3), 'E_naming': round(1 - q, 3), 'E_presence': A,
                  'fail_recall': round(1 - ok_r.mean(), 3), 'fail_presence': round(1 - ok_p.mean(), 3),
                  'fail_naming': round(1 - ok_n.mean(), 3), 'fail_class': round(1 - ok.mean(), 3)}
    npass = sum(passes.values())
    return per, {f'P(<{K_OF_6} of 6 pass)': round(float((npass < K_OF_6).mean()), 4),
                 'P(<5 of 6)': round(float((npass < 5).mean()), 4),
                 'P(<6 of 6)': round(float((npass < 6).mean()), 4),
                 'mean classes passing': round(float(npass.mean()), 3)}


def ruled_lines():
    return {c: (RECALL_LINE, TABLE1[c][0] - PRES_MARGIN, NAMING_LINE) for c in TABLE1}


def proposed_lines():
    """Bridge v2: each line is the human-level expectation minus 1.96 binomial SEs (2.5 % one-sided per component, the track's bound),
    rounded down to 0.01, and never above the ruled line for recall/presence. Naming's line moves to the
    human estimate as well, because 0.85 is above a human's expected naming on OM1."""
    out = {}
    for c, (A, m, s) in TABLE1.items():
        n = LOCKED[c]
        a = miss_rate(A, n / 100, 'symmetric')
        q = fit_q(m, s)
        r = 1 - a
        rl = min(RECALL_LINE, np.floor(100 * (r - 1.96 * np.sqrt(r * (1 - r) / n))) / 100)
        pl = min(A - PRES_MARGIN, np.floor(100 * (A - 1.96 * np.sqrt(A * (1 - A) / 100))) / 100)
        k = n * r
        nl = np.floor(100 * ((1 - q) - 1.96 * np.sqrt(q * (1 - q) / k))) / 100
        out[c] = (float(rl), float(pl), float(nl))
    return out


def main():
    draws = int(sys.argv[1]) if len(sys.argv) > 1 else 200_000
    rng = np.random.default_rng(20261115)
    res = {'draws': draws, 'seed': 20261115, 'q_fit_sensitivity': {}}
    for sg in (0.05, 0.08, 0.12):
        res['q_fit_sensitivity'][str(sg)] = {c: round(fit_q(m, s, sg), 4) for c, (A, m, s) in TABLE1.items()}
    for name, lines in (('ruled', ruled_lines()), ('proposed', proposed_lines())):
        res[name] = {'lines': {c: [round(x, 3) for x in v] for c, v in lines.items()}}
        for mode in ('symmetric', 'misses_only'):
            per, agg = simulate(draws, rng, mode, lines)
            res[name][mode] = {'per_class': per, 'aggregate': agg}
        # power: a deficient model, naming error and misses both 2x a human's (and +0.10 naming error)
        for tag, qs, ms in (('2x_human_errors', 2.0, 2.0), ('3x_human_errors', 3.0, 3.0)):
            per, agg = simulate(draws, rng, 'symmetric', lines, q_scale=qs, miss_scale=ms)
            res[name][tag] = {'per_class': {c: per[c]['fail_class'] for c in per}, 'aggregate': agg}
        # icx14-like: no branch detected as its own class -> naming 0
        per, agg = simulate(draws, rng, 'symmetric', lines, q_scale=1 / 0.03)
        res[name]['naming_collapse'] = {'aggregate': agg}
    json.dump(res, sys.stdout, indent=1)


if __name__ == '__main__':
    main()
