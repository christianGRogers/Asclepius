"""Delta, Janus 1-L round 2: should the one pre-registered candidate C be a1 or the ensemble E = mean softmax(a1, a2)?

No locked-100 number, no sealed case and no image is read. The noise comes from the only measured pair of warm
siblings on this family: atlas3 F1 and F0 (two warm fine-tunes from one start, same data, val 80, A1c tF1;
trillium-results/round7/atlas3/per_case_F{0,1}.json), resampled with its real heavy tails.

Model (per case i, against Janus 0 = J0, all in macro decisive tF1):
    a_k,i - J0_i = mu + g_k + s_i + v_k,i          k = 1, 2 (a1, a2)
    E_i   - J0_i = mu + e + (g_1 + g_2)/2 + s_i + w_i,   w_i = sqrt(2 phi) (v_1,i + v_2,i) / 2
  * v: a warm child's own per-case noise. v_1 - v_2 is resampled from the measured F1 - F0 per-case differences
    (random sign), so Var(v) = SD(F1 - F0)^2 / 2 and the tails are real;
  * s: the per-case spread of the recipe's true effect, shared by both children, SD = sqrt(lam) * sigma_v.
    lam = 1 reproduces round 1's optimistic SD(a1 - J0) = 0.038; lam = 6.7 its pessimistic 0.075.
    s has the measured heavy tails (resampled like v); 'gauss' rows draw it Gaussian instead, a sensitivity check
    that matters for the trimmed recall guard L3;
  * g: a run-level offset of one child (A37's floor 0.012), drawn once per simulated study;
  * phi: how much of a member's noise E keeps. 0.5 = E behaves like the average of its members' scores;
    1.0 = no reduction at all (the worst case for E: softmax averaging buys nothing per case);
  * e: a mean ensemble bonus. 0 in every primary row (no source gives one for tF1 at M = 2).
Tests on n = 100 (one-sided 2.5 %, t bound; the bootstrap gives the same within 0.005 at n = 100):
    H1 macro part: LB > -0.02;  Q4: LB > -0.015;  H3: LB > 0.
The recall guard L3 (Delta v1 §4, L-A5) is simulated per class from the real per-class recall differences
(recall_icx_traced, F1 - F0), with the same lam / phi structure, under mu = 0 (its false-alarm rate).
Dice (H2): Gaussian, SD(a1 - J0) 0.010 / 0.023 (Crucible v1 §5.2), same structure.

Usage: python ensemble_power.py   (writes ensemble_power.json; about 1 min)
"""
import json
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
CLS = ['1', '2', '3', '4']
N = 100
T975 = 1.984


def load(p):
    return {x['case']: x for x in json.load(open(os.path.join(ROOT, p)))}


def macro(x):
    v = [x['per_class'][k] for k in CLS if k in x['per_class'] and int(k) not in x.get('flagged_classes', [])]
    return float(np.mean(v)) if v else None


def measured():
    a = load('trillium-results/round7/atlas3/per_case_F1.json')
    b = load('trillium-results/round7/atlas3/per_case_F0.json')
    cases = sorted(c for c in set(a) & set(b) if macro(a[c]) is not None and macro(b[c]) is not None)
    d = np.array([macro(a[c]) - macro(b[c]) for c in cases])
    rec = {}
    for k in CLS:
        r = [a[c]['split']['recall_icx_traced'].get(k) - b[c]['split']['recall_icx_traced'].get(k)
             for c in cases if a[c]['split']['recall_icx_traced'].get(k) is not None
             and b[c]['split']['recall_icx_traced'].get(k) is not None]
        rec[k] = np.array(r)
    return d, rec


def draw_v(rng, diffs, size):
    """Two independent children's noise whose difference has the measured distribution: v = +-d/sqrt(2)."""
    pick = diffs[rng.integers(0, len(diffs), size)]
    return pick * rng.choice([-1.0, 1.0], size) / math.sqrt(2.0)


def lb(x):
    return x.mean(-1) - T975 * x.std(-1, ddof=1) / math.sqrt(x.shape[-1])


def ub(x):
    return x.mean(-1) + T975 * x.std(-1, ddof=1) / math.sqrt(x.shape[-1])


def trimmed(x, p=0.10):
    k = int(round(p * x.shape[-1]))
    s = np.sort(x, axis=-1)
    return s[..., k:x.shape[-1] - k].mean(-1)


def tf1_grid(rng, d, reps=4000):
    sv = float(np.std(d, ddof=1)) / math.sqrt(2)
    rows = []
    for lam in (0.0, 1.0, 6.7):
        for sg in (0.0, 0.012):
            for phi in (0.5, 0.75, 1.0):
                for mu in (-0.02, -0.01, 0.0, 0.005, 0.01, 0.02):
                    v1 = draw_v(rng, d, (reps, N)); v2 = draw_v(rng, d, (reps, N))
                    s = math.sqrt(lam) * draw_v(rng, d, (reps, N))          # SD sqrt(lam) * sigma_v, real tails
                    g1, g2 = rng.normal(0, sg, (2, reps, 1))
                    a1 = mu + g1 + s + v1
                    E = mu + (g1 + g2) / 2 + s + math.sqrt(2 * phi) * (v1 + v2) / 2
                    la, le = lb(a1), lb(E)
                    rows.append(dict(lam=lam, sigma_g=sg, phi=phi, mu=mu,
                                     sd_a1=round(float(a1.std(-1, ddof=1).mean()), 4),
                                     sd_E=round(float(E.std(-1, ddof=1).mean()), 4),
                                     H1_a1=round(float((la > -0.02).mean()), 3), H1_E=round(float((le > -0.02).mean()), 3),
                                     Q4_a1=round(float((la > -0.015).mean()), 3), Q4_E=round(float((le > -0.015).mean()), 3),
                                     H3_a1=round(float((la > 0).mean()), 3), H3_E=round(float((le > 0).mean()), 3),
                                     E_fails_H1_a1_passes=round(float(((le <= -0.02) & (la > -0.02)).mean()), 3)))
    return sv, rows


def l3_false_alarm(rng, rec, reps=4000):
    """L3 under mu = 0 (no true recall change): how often it fires, for C = a1 and C = E."""
    out = []
    for shape in ('heavy', 'gauss'):
        for lam in (0.0, 1.0, 3.0):
            if shape == 'gauss' and lam == 0.0:
                continue
            for phi in (0.5, 1.0):
                fa_a1 = np.zeros(reps, bool); fa_E = np.zeros(reps, bool)
                for k in CLS:
                    dk = rec[k]
                    sv = float(np.std(dk, ddof=1)) / math.sqrt(2)
                    v1 = draw_v(rng, dk, (reps, N)); v2 = draw_v(rng, dk, (reps, N))
                    s = (math.sqrt(lam) * draw_v(rng, dk, (reps, N)) if shape == 'heavy'
                         else rng.normal(0, math.sqrt(lam) * sv, (reps, N)))
                    a1 = s + v1
                    E = s + math.sqrt(2 * phi) * (v1 + v2) / 2
                    for x, fa in ((a1, fa_a1), (E, fa_E)):
                        fa |= (trimmed(x) < -0.02) | ((x.mean(-1) < -0.02) & (ub(x) < 0))
                out.append(dict(s_shape=shape, lam=lam, phi=phi, L3_false_alarm_a1=round(float(fa_a1.mean()), 3),
                                L3_false_alarm_E=round(float(fa_E.mean()), 3)))
    return out


def dice_grid(rng, reps=4000):
    rows = []
    for sd in (0.010, 0.023):
        sv = sd / math.sqrt(2)          # lam = 1: SD(a1 - J0) = sd
        for phi in (0.5, 1.0):
            for dd in (0.0, 0.003, 0.005, 0.01):
                v1, v2, s = rng.normal(0, sv, (3, reps, N))
                a1 = dd + s + v1
                E = dd + s + math.sqrt(2 * phi) * (v1 + v2) / 2
                rows.append(dict(sd_a1_minus_J0=sd, phi=phi, dice_effect=dd,
                                 H2_a1=round(float((lb(a1) > 0).mean()), 3), H2_E=round(float((lb(E) > 0).mean()), 3)))
    return rows


def boot_check(rng, d):
    """The t bound against a percentile bootstrap (B = 2000) on a few draws: the two decisions agree."""
    sv = float(np.std(d, ddof=1)) / math.sqrt(2)
    agree = 0
    for _ in range(200):
        x = rng.normal(0, sv, N) + draw_v(rng, d, N)
        bl = np.percentile(x[rng.integers(0, N, (2000, N))].mean(1), 2.5)
        agree += (bl > -0.005) == (lb(x[None])[0] > -0.005)
    return agree / 200


def main():
    rng = np.random.default_rng(302)
    d, rec = measured()
    sv, rows = tf1_grid(rng, d)
    out = dict(source='atlas3 F1 - F0, val 80 (warm siblings), A1c tF1', n_pairs=int(len(d)),
               sd_F1_minus_F0=round(float(np.std(d, ddof=1)), 4), sigma_v=round(sv, 4),
               kurtosis_excess=round(float(((d - d.mean()) ** 4).mean() / d.var() ** 2 - 3), 2),
               t_vs_bootstrap_agreement=boot_check(rng, d),
               tf1=rows, l3=l3_false_alarm(rng, rec), dice=dice_grid(rng))
    json.dump(out, open(os.path.join(HERE, 'ensemble_power.json'), 'w'), indent=1)
    print({k: v for k, v in out.items() if k not in ('tf1', 'l3', 'dice')})
    for r in rows:
        if r['sigma_g'] == 0.012 and r['phi'] in (0.5, 1.0):
            print(r)
    for r in out['l3']:
        print(r)
    for r in out['dice']:
        print(r)


if __name__ == '__main__':
    main()
