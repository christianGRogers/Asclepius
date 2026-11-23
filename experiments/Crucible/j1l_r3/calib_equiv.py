"""Crucible, Janus 1-L round 3, §5 item 4: is "re-run Rule W on temperature-calibrated probabilities" a new rule,
or Rule W on a re-labelled grid? CPU, synthetic probabilities only.

Rule W exports vessel where the summed vessel probability p_v >= t. Two calibrations:
  binary   p_v' = sigmoid(logit(p_v) / T). This is strictly monotone in p_v, so {p_v' >= t} = {p_v >= t'} with
           t' = sigmoid(T logit(t)): exactly the same masks, at re-labelled thresholds.
  5-class  softmax(log p / T) over nnU-Net's saved 5-class probabilities (log p are the logits up to a per-voxel
           constant), then summed over the four vessels. Not exactly monotone in p_v when the vessel mass is split
           between two vessels. This script measures how often the 5-class mask at t differs from the raw mask at the
           best-matching t' (Dirichlet-shaped voxels, realistic split at branch points).

Result -> the plan: a temperature cannot draw a mask Rule W could not draw at some raw threshold (binary: never;
5-class: in the fraction printed). So the calibration item reduces to the grid: if Job 0 lands at t* = 0.30 (the
grid's edge), the remedy is to extend Rule W's grid downward on the tuning 60 (0.25, 0.20), not a second rule; if FP
rises at every t < 0.50, no monotone calibration can remove it (the FP voxels are above the rim voxels in p_v), and
the answer is the guard as written (t* = 0.50).

Usage: python calib_equiv.py   (writes calib_equiv.json)
"""
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
GRID = np.round(np.arange(0.20, 0.501, 0.05), 2)
FINE = np.linspace(0.01, 0.99, 981)


def logit(p):
    p = np.clip(p, 1e-7, 1 - 1e-7)
    return np.log(p / (1 - p))


def sig(x):
    return 1 / (1 + np.exp(-x))


def main():
    rng = np.random.default_rng(0)
    n = 400_000
    # rim voxels: vessel mass ~ Beta, split between a main and a second vessel (branch points: 20 % of voxels split)
    pv = rng.beta(0.6, 0.6, n)
    split = np.where(rng.random(n) < 0.2, rng.uniform(0.2, 0.5, n), rng.uniform(0.0, 0.05, n))
    rest = rng.dirichlet([1, 1], n) * 0.02
    P = np.stack([1 - pv, pv * (1 - split) * 0.98, pv * split * 0.98, pv * 0.01 + rest[:, 0] * pv,
                  pv * 0.01 + rest[:, 1] * pv], 1)
    P /= P.sum(1, keepdims=True)
    raw = P[:, 1:].sum(1)
    out = {}
    for T in (0.7, 0.85, 1.2, 1.5):
        # binary: exact equivalence
        cal = sig(logit(raw) / T)
        tb = {f'{t:.2f}': round(float(sig(T * logit(t))), 4) for t in GRID}
        assert all(((cal >= t) == (raw >= sig(T * logit(t)) - 1e-9)).mean() > 0.9999 for t in GRID)
        # 5-class temperature
        L = np.log(np.clip(P, 1e-12, 1)) / T
        Q = np.exp(L - L.max(1, keepdims=True)); Q /= Q.sum(1, keepdims=True)
        q = Q[:, 1:].sum(1)
        rows = {}
        for t in GRID:
            m = q >= t
            diffs = [(m != (raw >= tt)).mean() for tt in FINE]
            k = int(np.argmin(diffs))
            rows[f'{t:.2f}'] = dict(best_raw_t=round(float(FINE[k]), 3), voxels_differing=round(float(diffs[k]), 5))
        out[f'T={T}'] = dict(binary_equivalent_raw_t=tb, five_class=rows,
                             max_differing=max(v['voxels_differing'] for v in rows.values()))
        print(f'T={T}: binary exact; 5-class worst share of rim voxels differing from the best raw t: '
              f"{out[f'T={T}']['max_differing']:.4%}")
    json.dump(dict(n_voxels=n, note='rim-like voxels only; a whole CT is >99 % certain background, so the share of '
                   'all voxels is far smaller', results=out), open(os.path.join(HERE, 'calib_equiv.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
