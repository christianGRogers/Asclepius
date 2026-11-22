"""Atlas, Janus 1-L round 3: L3's false-alarm rate when its upper bound is the bootstrap that L-A5 prescribes.

L-A5 makes every bound of the look a 10 000-resample percentile bootstrap. Delta's L3 figures (3-8 %, `l3_fix.json`)
used a t bound (mean + 1.984 SD / sqrt(n)). On the measured, heavy-tailed sibling differences the two can differ,
because a percentile bootstrap of a mean is narrower than the t interval when a few cases carry the spread.

Noise: the real per-class recall differences of the warm siblings (atlas3 F1 - F0, val 80, as Delta's
`ensemble_power.measured`), drawn as two independent children (+-d / sqrt 2, `draw_v`), plus a broad component of
lam x the sibling variance (lam 0, 1, 3; heavy = resampled from the same differences, gauss = normal). True change 0
in every class. L3 fires if any class fires. Also: the power for a uniform -0.03 LCx loss.

Usage: python l3_null.py [reps] [B]   (writes l3_null.json)
"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'experiments', 'Delta', 'j1l_r2'))
from ensemble_power import CLS, N, draw_v, measured, trimmed, ub  # noqa: E402


def boot_ub(x, b, rng, alpha=0.025):
    out = np.empty(x.shape[0])
    for s in range(0, x.shape[0], 100):
        idx = rng.integers(0, x.shape[-1], (b, x.shape[-1]))
        out[s:s + 100] = np.percentile(x[s:s + 100][:, idx].mean(-1), 100 * (1 - alpha), axis=-1)
    return out


def fires(x, bound):
    tm = trimmed(x)
    return (tm < -0.02) | ((x.mean(-1) < -0.02) & (bound < 0))


def main(reps=2000, b=2000):
    rng = np.random.default_rng(303)
    _, rec = measured()
    rows = []
    for shape, lam in (('heavy', 0.0), ('heavy', 1.0), ('heavy', 3.0), ('gauss', 1.0)):
        for scen in ('null', 'uniform_-0.03_LCx'):
            hit_t, hit_b, hit_tm = (np.zeros(reps, bool) for _ in range(3))
            for j, k in enumerate(CLS):
                dk = rec[k]
                sv = float(np.std(dk, ddof=1)) / math.sqrt(2)
                x = draw_v(rng, dk, (reps, N))
                if lam:
                    x = x + (math.sqrt(lam) * draw_v(rng, dk, (reps, N)) if shape == 'heavy'
                             else rng.normal(0, math.sqrt(lam) * sv, (reps, N)))
                if j == 2 and scen != 'null':
                    x = x - 0.03
                hit_t |= fires(x, ub(x))
                hit_b |= fires(x, boot_ub(x, b, rng))
                hit_tm |= trimmed(x) < -0.02
            rows.append(dict(shape=shape, lam=lam, scenario=scen, L3_t_bound=round(float(hit_t.mean()), 3),
                             L3_bootstrap=round(float(hit_b.mean()), 3),
                             trimmed_clause_alone=round(float(hit_tm.mean()), 3)))
            print(rows[-1], flush=True)
    json.dump(dict(reps=reps, B=b, rows=rows), open(os.path.join(HERE, 'l3_null.json'), 'w'), indent=1)


if __name__ == '__main__':
    a = sys.argv[1:]
    main(*(int(x) for x in a)) if a else main()
