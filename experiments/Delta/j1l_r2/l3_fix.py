"""Delta, Janus 1-L round 2: L3 (the recall guard, L-A5) as adopted, against L3' = the same trimmed rule with a
significance clause (Yuen's trimmed-mean t bound), under two shapes of the true per-case recall change.

Round 1 measured L3's false alarm (about 4 %) by resampling the warm siblings' real recall differences, which are
mostly zero with a few large flips (excess kurtosis > 10). A parent-to-child difference (a1 - Janus 0) may instead
carry a broad per-case component. This script asks how both rules behave in each case.

  L3  (adopted): fires for a class if trimmed10 mean delta < -0.02, or (mean < -0.02 and 95 % upper bound < 0);
  L3' (proposed): fires if [trimmed10 mean < -0.02 and Yuen upper bound of the trimmed mean < 0],
                  or (mean < -0.02 and 95 % upper bound < 0).
False alarm: true mean change 0 in every class. Power: (i) a uniform -0.03 loss in one class; (ii) 8 of 100 trees
of one class each lose 0.4 of their recall (shortening concentrated in a few trees; mean -0.032).
Noise: real per-class recall differences (atlas3 F1 - F0, recall_icx_traced) as in ensemble_power.py.

Usage: python l3_fix.py  (writes l3_fix.json)
"""
import json
import math
import os

import numpy as np

from ensemble_power import CLS, N, T975, draw_v, measured, trimmed, ub

HERE = os.path.dirname(os.path.abspath(__file__))
G = 0.10


def yuen_ub(x, g=G):
    n = x.shape[-1]
    k = int(round(g * n))
    s = np.sort(x, axis=-1)
    lo, hi = s[..., k:k + 1], s[..., n - k - 1:n - k]
    w = np.clip(x, lo, hi)
    sw = w.std(-1, ddof=1)
    se = sw / ((1 - 2 * g) * math.sqrt(n))           # Yuen's standard error of the g-trimmed mean
    return trimmed(x, g) + 1.987 * se


def fires(x, rule):
    tm = trimmed(x)
    b = (x.mean(-1) < -0.02) & (ub(x) < 0)
    if rule == 'L3':
        return (tm < -0.02) | b
    return ((tm < -0.02) & (yuen_ub(x) < 0)) | b


def run(rng, rec, reps=4000):
    out = []
    for shape, lam in (('heavy', 0.0), ('heavy', 1.0), ('heavy', 3.0), ('gauss', 1.0), ('gauss', 3.0)):
        for scen in ('null', 'uniform_-0.03', 'few_trees_-0.4'):
            hit = {'L3': np.zeros(reps, bool), "L3'": np.zeros(reps, bool)}
            for j, k in enumerate(CLS):
                dk = rec[k]
                sv = float(np.std(dk, ddof=1)) / math.sqrt(2)
                v = draw_v(rng, dk, (reps, N))
                s = (math.sqrt(lam) * draw_v(rng, dk, (reps, N)) if shape == 'heavy'
                     else rng.normal(0, math.sqrt(lam) * sv, (reps, N)))
                x = s + v
                if j == 2 and scen == 'uniform_-0.03':          # LCx
                    x = x - 0.03
                if j == 2 and scen == 'few_trees_-0.4':
                    x = x.copy(); x[:, :8] -= 0.4
                for r in hit:
                    hit[r] |= fires(x, r)
            out.append(dict(s_shape=shape, lam=lam, scenario=scen,
                            L3=round(float(hit['L3'].mean()), 3), L3p=round(float(hit["L3'"].mean()), 3)))
    return out


if __name__ == '__main__':
    rng = np.random.default_rng(7)
    _, rec = measured()
    rows = run(rng, rec)
    json.dump(dict(rule_L3p="trimmed10 < -0.02 and Yuen 95% UB < 0, or mean < -0.02 and 95% UB < 0", rows=rows),
              open(os.path.join(HERE, 'l3_fix.json'), 'w'), indent=1)
    for r in rows:
        print(r)
