"""Bridge, Round 10: which rule should decide the seal's last step (200 -> 250) on wave-1 reads?

Rule A (A31.1 as written): extend if f_hat or k_hat > 1.2 in any class.
Rule B (proposed): extend if the re-run power at the current size, with the measured per-class f_hat and k_hat,
         is below 0.8 (the same power model, in its normal form).

f_hat_c = SD(model-vs-read, pool patients) / SD(Janus 0 val per-case tF1, 80);
k_hat_c = SD(inter-read, pool) / SD(model-vs-read, pool).
Per-case scores are normal; the per-class val SDs are Janus 0's (power_r10.py surrogate); classes independent.
For each true (f, k) and wave-1 size, the script reports P(extend) under each rule and the resulting true
P(pass a human-level model), averaged over the decision.

Normal-form power (validated against power_r10.py's resampling within 0.01 in the cases printed):
  P_c = Phi(0.05 / (sd_c f sqrt(1 + k^2) / sqrt(n keep_c)) - 1.96);  P = prod_c P_c.

Usage: python3 experiments/Bridge/r10/extension_rule.py --out experiments/Bridge/r10/extension_rule.json
"""
from __future__ import annotations

import argparse
import os
import json
import math

import numpy as np
from math import erf, sqrt

SD = {'LM': 0.1214, 'LAD': 0.1289, 'LCx': 0.1362, 'RCA': 0.0815}   # power_r10.py surrogate (Janus 0)
KEEP = {'LM': 78 / 80, 'LAD': 1.0, 'LCx': 1.0, 'RCA': 75 / 80}
NVAL = 80


def phi(x):
    return 0.5 * (1 + erf(x / sqrt(2)))


def power(n, f, k, delta=0.0):
    """f, k: dict per class or scalar."""
    p = 1.0
    for c, s in SD.items():
        fc = f[c] if isinstance(f, dict) else f
        kc = k[c] if isinstance(k, dict) else k
        se = s * fc * math.sqrt(1 + kc ** 2) / math.sqrt(max(5, round(n * KEEP[c])))
        p *= phi((0.05 + delta) / se - 1.96)
    return p


def simulate(true_f, true_k, n_wave, size=200, big=250, sims=20000, seed=20261025):
    rng = np.random.default_rng(seed)
    fire_a = np.zeros(sims, bool)
    pw_b = np.ones(sims)
    for c, s in SD.items():
        val = rng.normal(0, s, (sims, NVAL)).std(1, ddof=1)
        mod = rng.normal(0, s * true_f, (sims, n_wave)).std(1, ddof=1)
        inter = rng.normal(0, s * true_f * true_k, (sims, n_wave)).std(1, ddof=1)
        fh, kh = mod / val, inter / mod
        fire_a |= (fh > 1.2) | (kh > 1.2)
        se = s * fh * np.sqrt(1 + kh ** 2) / math.sqrt(max(5, round(size * KEEP[c])))
        pw_b *= np.array([phi(x) for x in (0.05 / se - 1.96)])
    fire_b = pw_b < 0.8
    p_small, p_big = power(size, true_f, true_k), power(big, true_f, true_k)
    res = {}
    for name, fire in (('A_ratio_trigger', fire_a), ('B_repower', fire_b)):
        pe = float(fire.mean())
        res[name] = {'p_extend': round(pe, 3), 'true_power_after': round(pe * p_big + (1 - pe) * p_small, 3)}
    res['true_power_at'] = {str(size): round(p_small, 3), str(big): round(p_big, 3)}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out')
    a = ap.parse_args()
    check = {f'n{n}_f{f}_k{k}': round(power(n, f, k), 3)
             for n, f, k in ((150, 1, 1), (200, 1, 1), (250, 1, 1), (200, 1.2, 1.2), (250, 1.2, 1.2))}
    print('normal-form check (power_r10 resampling: n150 0.762, n200 0.913, n250 0.970, n200 f=k=1.2 0.592, '
          'n250 f=k=1.2 0.751):', check)
    out = {'normal_form_check': check, 'runs': []}
    for n_wave in (35, 61, 100):
        for tf, tk in ((1.0, 1.0), (1.2, 1.0), (1.0, 1.2), (1.2, 1.2), (1.5, 1.0)):
            r = simulate(tf, tk, n_wave)
            r.update(n_wave=n_wave, true_f=tf, true_k=tk)
            out['runs'].append(r)
            print(f"wave n={n_wave:3d} true f={tf} k={tk}: A extends {r['A_ratio_trigger']['p_extend']:.2f} "
                  f"(power {r['A_ratio_trigger']['true_power_after']:.2f}); B extends "
                  f"{r['B_repower']['p_extend']:.2f} (power {r['B_repower']['true_power_after']:.2f}); "
                  f"power at 200/250 {r['true_power_at']}")
    if a.out:
        json.dump(out, open(a.out, 'w'), indent=1)


if __name__ == '__main__' and not os.environ.get('RULE_C'):
    main()


# ---- Rule C: size the seal from the measured s_d = SD(model-vs-read - inter-read) per class -----------------
SIZES = (150, 200, 250)


def power_sd(n, sd_d):
    p = 1.0
    for c in SD:
        p *= phi(0.05 / (sd_d[c] / math.sqrt(max(5, round(n * KEEP[c])))) - 1.96)
    return p


def rule_c(sd_d_hat):
    """The smallest pre-registered seal size whose re-powered P(all four pass) >= 0.8; 250 if none."""
    for n in SIZES:
        if power_sd(n, sd_d_hat) >= 0.8:
            return n
    return SIZES[-1]


def simulate_c(f, k, rho, n_wave, sims=20000, seed=20261025):
    rng = np.random.default_rng(seed)
    true_sd = {c: s * f * math.sqrt(1 + k * k - 2 * rho * k) for c, s in SD.items()}
    est = {c: rng.normal(0, true_sd[c], (sims, n_wave)).std(1, ddof=1) for c in SD}
    chosen = np.array([rule_c({c: est[c][i] for c in SD}) for i in range(sims)])
    true_p = {n: power_sd(n, true_sd) for n in SIZES}
    return {'f': f, 'k': k, 'rho': rho, 'n_wave': n_wave,
            'true_power': {str(n): round(p, 3) for n, p in true_p.items()},
            'share_chosen': {str(n): round(float(np.mean(chosen == n)), 3) for n in SIZES},
            'true_power_after': round(float(np.mean([true_p[n] for n in chosen])), 3),
            'mean_seal_size': round(float(chosen.mean()), 1)}


def main_c(out_path=None):
    runs = []
    for n_wave in (35, 49, 61):
        for f, k, rho in ((1, 1, 0), (1, 1, 0.5), (1.2, 1.2, 0), (1.2, 1.2, 0.5), (1.5, 1, 0), (1, 1.2, 0.3)):
            r = simulate_c(f, k, rho, n_wave, sims=4000)
            runs.append(r)
            print('C', r)
    if out_path:
        d = json.load(open(out_path)) if os.path.exists(out_path) else {}
        d['rule_c'] = runs
        json.dump(d, open(out_path, 'w'), indent=1)


if __name__ == '__main__' and os.environ.get('RULE_C'):
    main_c(os.environ.get('RULE_C_OUT'))
