"""Delta, Round 10: what the A30 seal (D27) and the D35 decision set buy, on Janus 0's spread.

1. A10 power (D6: per class, all four, margin 0.05) at seal sizes 150 / 200 / 250, with Bridge's simulation
   (experiments/Bridge/wave1/power.py, unchanged) on Janus 0's per-case val distribution.
2. The D35 decision set: the minimum detectable paired effect (80 % power, two-sided 0.05) of a fine-tune
   comparison scored on n decision patients, with A22's seed term, for 1 or 2 seeds per arm.

Janus 0's per-case val tF1 is on Fir ($SCRATCH/icx4/r9_tf1_val.json), not in the repository. Two modes:
  --real r9_tf1_val.json   the lead's file (rows[].per_class by name, rows[].flagged_classes): exact.
  (default) surrogate      run 1's real per-case shape (atlas2 per_case_run1.json, unflagged), mapped per class to
                           Janus 0's decisive mean and to the SD implied by its 95 % bootstrap CI (icx4 - Results.md,
                           Delta SUMMARY on #43): SD = CI width x sqrt(n) / 3.92. Clipped to [0, 1].
CPU only, no image, no sealed case. Usage: python3 power_r10.py [--real FILE] [--out OUT.json]"""
import argparse
import json
import math
import os
import sys

import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'experiments', 'Bridge', 'wave1'))
from power import p_pass  # noqa: E402

CL = ['LM', 'LAD', 'LCx', 'RCA']
NUM = {'1': 'LM', '2': 'LAD', '3': 'LCx', '4': 'RCA'}
# Janus 0, val 80, decisive (A1, TotalSegmentator ostia): means from r9_tf1_val.json's summary (#43).
J0_MEAN = {'LM': 0.9449, 'LAD': 0.9035, 'LCx': 0.8566, 'RCA': 0.9375}
J0_N = {'LM': 78, 'LAD': 80, 'LCx': 80, 'RCA': 75}
# 95 % bootstrap CIs per class from Delta's score_tf1.py on the same predictions (#43, delta_p2/SUMMARY.md). Those
# are under expert ostia (means 0.010-0.011 higher on the left tree, RCA identical); the width is what is used.
J0_CI = {'LM': (0.9235, 0.9774), 'LAD': (0.8836, 0.9389), 'LCx': (0.8347, 0.8939), 'RCA': (0.9174, 0.9532)}
J0_MACRO_CI = (0.8802, 0.9316)      # r9 scorer, decisive macro, n = 80
SIGMA_SEED = 0.013                  # A22 (Round 8), from-scratch training, macro tF1
RUN1_PAIRED_SD = None               # computed below from atlas2 (B - run 1), as Bridge r9


def load_rows(path):
    d = json.load(open(path))
    rows = d['rows'] if isinstance(d, dict) else d
    out = {c: [] for c in CL}
    for r in rows:
        if r.get('error') or r.get('provisional'):
            continue
        pc = {NUM.get(k, k): v for k, v in r['per_class'].items()}
        fl = {NUM.get(str(x), str(x)) for x in r.get('flagged_classes', [])}
        for c in CL:
            v = pc.get(c)
            if v is not None and c not in fl:
                out[c].append(float(v))
    return {c: np.array(v) for c, v in out.items()}


def surrogate():
    base = load_rows(os.path.join(REPO, 'trillium-results/round6/atlas2/results/per_case_run1.json'))
    out, info = {}, {}
    for c in CL:
        x = base[c]
        sd_t = (J0_CI[c][1] - J0_CI[c][0]) * math.sqrt(J0_N[c]) / 3.92
        z = (x - x.mean()) / x.std(ddof=1)
        y = np.clip(J0_MEAN[c] + sd_t * z, 0.0, 1.0)
        out[c] = y
        info[c] = dict(run1_mean=round(float(x.mean()), 4), run1_sd=round(float(x.std(ddof=1)), 4), n_run1=len(x),
                       janus0_sd_from_ci=round(sd_t, 4), surrogate_mean=round(float(y.mean()), 4),
                       surrogate_sd=round(float(y.std(ddof=1)), 4))
    return out, info


def paired_sd_run1():
    R = os.path.join(REPO, 'trillium-results/round6/atlas2/results')
    a = {r['case']: r for r in json.load(open(os.path.join(R, 'per_case_run1.json')))}
    b = {r['case']: r for r in json.load(open(os.path.join(R, 'per_case_b.json')))}
    d = [b[c]['decisive'] - a[c]['decisive'] for c in a
         if c in b and a[c].get('decisive') is not None and b[c].get('decisive') is not None]
    return float(np.std(d, ddof=1)), len(d)


NS = (100, 150, 175, 200, 228, 250)


def p_pass_rho(base, f, k, keep, n, rho, delta=0.0, sims=4000, seed=20261018):
    """Bridge's p_pass with a per-patient correlation rho between model-vs-read and inter-read: the inter-read
    draw reuses the model's case index with probability rho (a mixture copula), else an independent index."""
    rng = np.random.default_rng(seed)
    passes = np.ones(sims, bool)
    per = {}
    for c, x in base.items():
        x = np.asarray(x, float)
        nc = max(5, int(round(n * keep[c])))
        mu = x.mean()
        i1 = rng.integers(0, len(x), (sims, nc))
        i2 = np.where(rng.random((sims, nc)) < rho, i1, rng.integers(0, len(x), (sims, nc)))
        d = (mu + f * (x[i1] - mu)) - (mu + k * f * (x[i2] - mu)) + delta
        lo = d.mean(1) - 1.96 * d.std(1, ddof=1) / math.sqrt(nc)
        ok = lo > -0.05
        per[c] = round(float(ok.mean()), 3)
        passes &= ok
    return round(float(passes.mean()), 3), per


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--real')
    ap.add_argument('--out')
    ap.add_argument('--sims', type=int, default=4000)
    a = ap.parse_args()
    if a.real:
        base, info, mode = load_rows(a.real), {}, 'real'
        info = {c: dict(mean=round(float(v.mean()), 4), sd=round(float(v.std(ddof=1)), 4), n=len(v))
                for c, v in base.items()}
    else:
        (base, info), mode = surrogate(), 'surrogate'
    res = dict(mode=mode, base=info)

    # 1. A10 power on the seal. keep = the scorable share per class: Janus 0's own on val (LM 78/80 present,
    # RCA 75/80 unflagged) and Bridge's 'not reviewed' pool scenario (LM 0.80, RCA 0.70).
    keeps = {'janus0_val': {'LM': 0.975, 'LAD': 1.0, 'LCx': 1.0, 'RCA': 0.94},
             'pool_not_reviewed': {'LM': 0.80, 'LAD': 0.90, 'LCx': 0.90, 'RCA': 0.70}}
    grid = []
    for kname, keep in keeps.items():
        for f in (1.0, 1.2, 1.5):
            for k in (0.75, 1.0, 1.2, 1.5):
                for delta in (0.0, -0.02):
                    for n in NS:
                        p, per = p_pass(base, {c: f for c in CL}, {c: k for c in CL}, keep, n, delta, sims=a.sims)
                        grid.append(dict(keep=kname, f=f, k=k, delta=delta, n=n, p_all4=p, per_class=per))
    res['a10'] = grid
    # 1b. Bridge's model draws model and inter-read for a patient independently (rho = 0). If the patients that are
    # hard for the model are also hard for two readers (rho > 0), the contrast is tighter and A10 has more power.
    rgrid = []
    for rho in (0.0, 0.3, 0.5):
        for f in (1.0, 1.2):
            for n in NS:
                p, per = p_pass_rho(base, f, 1.0, keeps['janus0_val'], n, rho, sims=a.sims)
                rgrid.append(dict(rho=rho, f=f, k=1.0, n=n, p_all4=p, per_class=per))
    res['a10_rho'] = rgrid

    # 2. The decision set: paired MDE for a fine-tune comparison (macro tF1 vs the reads), A22's SE.
    sd_pair, n_pair = paired_sd_run1()
    macro_sd = (J0_MACRO_CI[1] - J0_MACRO_CI[0]) * math.sqrt(80) / 3.92
    res['paired_sd_run1_B'] = [round(sd_pair, 4), n_pair]
    res['janus0_macro_sd_from_ci'] = round(macro_sd, 4)
    mde = []
    for f in (1.0, 1.5):
        for sig, sig_name in ((SIGMA_SEED, 'A22 0.013'), (0.0065, 'half (warm fine-tune, assumed)')):
            for seeds in (1, 2):
                for n in (10, 25, 35, 50, 80, 150):
                    case = (f * sd_pair) ** 2 / n
                    se = math.sqrt(case + sig ** 2 / seeds)
                    se2 = math.sqrt(case + 2 * sig ** 2 / seeds)    # both arms carry seed noise
                    mde.append(dict(f=f, sigma_seed=sig_name, seeds_per_arm=seeds, n=n,
                                    mde_case_only=round(2.8 * math.sqrt(case), 4),
                                    mde_A22=round(2.8 * se, 4), mde_both_arms=round(2.8 * se2, 4)))
    res['decision_set_mde'] = mde
    s = json.dumps(res, indent=1)
    if a.out:
        open(a.out, 'w').write(s)
    # short print
    print('mode', mode, json.dumps(info))
    print('paired SD (run1 vs B, macro decisive):', res['paired_sd_run1_B'], ' Janus 0 macro SD:', res['janus0_macro_sd_from_ci'])
    print('\nA10 P(all four pass), keep=janus0_val, delta 0:')
    for f in (1.0, 1.2, 1.5):
        for k in (0.75, 1.0, 1.2, 1.5):
            row = [g['p_all4'] for g in grid if g['keep'] == 'janus0_val' and g['f'] == f and g['k'] == k and g['delta'] == 0.0]
            print(f'  f={f} k={k}:', dict(zip(NS, row)))
    print('A10 with rho (k=1, keep=janus0_val):')
    for r in (0.0, 0.3, 0.5):
        for f in (1.0, 1.2):
            print(f'  rho={r} f={f}:', {g['n']: g['p_all4'] for g in rgrid if g['rho'] == r and g['f'] == f})
    print('A10, keep=pool_not_reviewed, delta 0:')
    for f in (1.0, 1.2, 1.5):
        for k in (1.0, 1.2):
            row = [g['p_all4'] for g in grid if g['keep'] == 'pool_not_reviewed' and g['f'] == f and g['k'] == k and g['delta'] == 0.0]
            print(f'  f={f} k={k}:', dict(zip(NS, row)))
    print('\nDecision-set MDE (macro), f=1 / f=1.5:')
    for r in mde:
        if r['n'] in (25, 35, 50, 80):
            print(' ', r)


if __name__ == '__main__':
    main()
