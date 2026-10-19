"""A10 power under D6 (per class, all four, margin 0.05), the algorithm of experiments/Bridge/r9/a10_pool_power.py
as a function: model per-case tF1 resampled from a real per-case distribution (icx4's own val, A31.1), spread
scaled by f on the pool; inter-read an independent draw with k x that spread; pass a class when the lower 95 %
bound of mean(model - inter + delta) > -0.05."""
from __future__ import annotations

import math

import numpy as np

MARGIN = 0.05


def p_pass(base: dict, f: dict, k: dict, keep: dict, n: int, delta: float = 0.0, sims: int = 4000,
           seed: int = 20261018) -> tuple[float, dict]:
    """base: class -> 1-D array of per-case tF1 (unflagged). f, k, keep: class -> float. Returns
    (P(all four pass), {class: P(pass)})."""
    rng = np.random.default_rng(seed)
    passes = np.ones(sims, bool)
    per = {}
    for c, x in base.items():
        x = np.asarray(x, float)
        nc = max(5, int(round(n * keep[c])))
        mu = x.mean()
        model = mu + f[c] * (x[rng.integers(0, len(x), (sims, nc))] - mu)
        inter = mu + k[c] * f[c] * (x[rng.integers(0, len(x), (sims, nc))] - mu)
        d = model - inter + delta
        lo = d.mean(1) - 1.96 * d.std(1, ddof=1) / math.sqrt(nc)
        p = lo > -MARGIN
        per[c] = round(float(p.mean()), 3)
        passes &= p
    return round(float(passes.mean()), 3), per
