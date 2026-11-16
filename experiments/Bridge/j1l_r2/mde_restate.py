"""Bridge, track 1-L round 2 (#302): two small calculations for Bridge v2.

1. **The locked-100 MDE restated from Job 0** (Janus 1-L Round 1 §5 item 4). Job 0 scores Janus 0 at argmax on the
   locked 100. That gives Janus 0's own per-class spread there, which is the one input of round 1's power numbers that
   was recovered from CIs rather than measured. The paired-difference shapes are the two measured pairs Bridge v1 used
   (atlas2 scratch pair, atlas3 warm replicate, val 80, A1c tF1). Each class column is rescaled by
   (Janus 0's locked-100 SD / atlas2 run 1's SD), exactly as round 1's "pessimistic" scenario did. L-A7: this may
   update the stated MDE; it changes no margin.

       python mde_restate.py --janus0 $W/scores/locked100_janus0_argmax.json     # after Job 0 (CPU, seconds)
       python mde_restate.py                                                     # now: Janus 0's SDs recovered from its CIs

2. **What shipping the ensemble E instead of a1 buys in the chance of adoption** (§5 item 1). The macro clause of H1
   (lower bound of Delta > -0.02), Q4's clause (> -0.015) and H3 (> 0) are read at a run-level model:
   a single run's true Delta is N(mu, tau^2) with tau = 0.004 or 0.012 (A37's upper bound for sigma_g); E's is N(mu + g, tau^2 / 2)
   (two independent run errors averaged; g = E's own gain, unmeasured, 0 to 0.005). The case-level standard error is
   SD/10. P(pass) = Phi((mu + m - 1.96 se) / sqrt(se^2 + tau^2)) in closed form (normal approximation).

Writes mde_restate.json next to itself (or --out).
"""
import argparse
import json
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
TR = os.path.join(REPO, 'trillium-results')
CL = ['1', '2', '3', '4']
NAMES = dict(zip(CL, ['LM', 'LAD', 'LCx', 'RCA']))
J0_SD_RECOVERED = {'1': 0.121, '2': 0.126, '3': 0.135, '4': 0.079}   # round 1's input (Atlas, Round 10, from CIs)
#: The run-level SD of a single run's true Delta. 0.012 is the 95 % upper bound that stands as A37's floor (Round 10);
#: the one measured warm pair (atlas3 F1 - F0, val 80: mean +0.0047, case SE 0.0043) gives a 1-df point estimate of
#: about 0.001. 0.004 is used as a central value.
TAUS = (0.004, 0.012)


def phi(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def load(p):
    return {r['case']: r for r in json.load(open(os.path.join(TR, p)))}


def pair(a, b):
    cases = sorted(set(a) & set(b))
    D = np.full((len(cases), 4), np.nan)
    for i, c in enumerate(cases):
        fl = set(map(str, a[c].get('flagged_classes') or [])) | set(map(str, b[c].get('flagged_classes') or []))
        for j, k in enumerate(CL):
            x, y = a[c]['per_class'].get(k), b[c]['per_class'].get(k)
            if k not in fl and x is not None and y is not None:
                D[i, j] = y - x
    return D


def macro(D):
    return np.nanmean(D, axis=-1)


def centred(D, passes=50):
    D = D.copy()
    for _ in range(passes):
        D = D - np.nanmean(D, axis=0)
        D = D - np.nanmean(macro(D))
    return D


def class_sd_rows(rows, key_of):
    out = {}
    for k in CL:
        v = [r['per_class'][key_of(k)] for r in rows if key_of(k) in r['per_class']
             and key_of(k) not in set(map(str, r.get('flagged_classes') or []))]
        out[k] = float(np.std(v, ddof=1))
    return out


def janus0_sd(path):
    """Per-class SD of Janus 0's decisive per-case tF1 on the locked 100 (r9_score_icx4 rows; names LM..RCA)."""
    rows = [r for r in json.load(open(path))['rows'] if 'error' not in r and not r['provisional']]
    sd = class_sd_rows(rows, lambda k: NAMES[k])
    return {k: sd[k] for k in CL}, len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--janus0', help="Job 0's locked100_janus0_argmax.json; default: round 1's recovered SDs")
    ap.add_argument('--out', default=os.path.join(HERE, 'mde_restate.json'))
    a = ap.parse_args()
    run1 = load('round6/atlas2/results/per_case_run1.json')
    D_scr = centred(pair(run1, load('round6/atlas2/results/per_case_b.json')))
    D_warm = centred(pair(load('round7/atlas3/per_case_F0.json'), load('round7/atlas3/per_case_F1.json')))
    sd_run1 = class_sd_rows(list(run1.values()), lambda k: k)
    if a.janus0:
        j0, n = janus0_sd(a.janus0)
        src = f'Job 0, Janus 0 at argmax on the locked 100 ({n} non-provisional cases)'
    else:
        j0, src = J0_SD_RECOVERED, "round 1's Janus 0 SDs recovered from its val-80 CIs (Atlas, Round 10)"
    scale = np.array([j0[k] / sd_run1[k] for k in CL])
    out = {'janus0_sd_source': src, 'janus0_class_sd': {NAMES[k]: round(j0[k], 4) for k in CL},
           'scale_vs_atlas2_run1': {NAMES[k]: round(float(s), 3) for k, s in zip(CL, scale)}, 'scenarios': {}}
    for name, D in (('scratch-pair shape', D_scr), ('warm-replicate shape', D_warm)):
        sd = float(np.nanstd(macro(D * scale), ddof=1))
        se = sd / 10
        out['scenarios'][name] = {
            'sd_macro_delta': round(sd, 4), 'mde_80pct_n100': round(2.80 * se, 4),
            'P_H1_macro_pass_if_true_0': round(phi((0.02 - 1.96 * se) / se), 3),
            'P_H1_macro_pass_if_true_-0.01': round(phi((0.01 - 1.96 * se) / se), 3),
            'P_Q4_pass_if_true_0': round(phi((0.015 - 1.96 * se) / se), 3),
            'P_Q4_pass_if_true_-0.01': round(phi((0.005 - 1.96 * se) / se), 3),
            'P_H3_pass_if_true_+0.005': round(phi((0.005 - 1.96 * se) / se), 3)}
    # 2. E against a1
    ens = {}
    for tau in TAUS:
        for sd in (0.038, 0.051, 0.072):
            se = sd / 10
            for mu in (-0.01, 0.0, 0.005):
                for g in (0.0, 0.003, 0.005):
                    row = {}
                    for lab, m in (('H1_macro', 0.02), ('Q4', 0.015), ('H3', 0.0)):
                        p1 = phi((mu + m - 1.96 * se) / math.sqrt(se ** 2 + tau ** 2))
                        pe = phi((mu + g + m - 1.96 * se) / math.sqrt(se ** 2 + tau ** 2 / 2))
                        row[lab] = {'a1': round(p1, 3), 'E': round(pe, 3), 'E_minus_a1': round(pe - p1, 3)}
                    ens[f'tau {tau} | SD {sd} | mu {mu:+.3f} | g {g:.3f}'] = row
    out['ensemble_vs_a1'] = {'taus': TAUS, 'rows': ens}
    json.dump(out, open(a.out, 'w'), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != 'ensemble_vs_a1'}, indent=1))
    for tau in TAUS:
        for sd in (0.038, 0.051, 0.072):
            for g in (0.0, 0.005):
                k = f'tau {tau} | SD {sd} | mu +0.000 | g {g:.3f}'
                print(k, {lab: (v['a1'], v['E']) for lab, v in ens[k].items()})


if __name__ == '__main__':
    main()
