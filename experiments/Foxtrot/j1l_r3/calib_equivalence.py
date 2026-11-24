"""Foxtrot, Janus 1-L round 3 (Round 2 section 5 item 4): can a calibration step change what Rule W can choose?

Rule W picks a mask {p_fg >= t} from a threshold grid on Janus 0's raw probabilities, p_fg = 1 - p_bg. A calibration
step (L-A23's rim-miscalibration row) would refit the probabilities and re-run Rule W on them. If the calibrated
foreground probability is a strictly increasing function g of the raw p_fg, then {g(p_fg) >= t} = {p_fg >= g^-1(t)}:
every calibrated mask is a raw-threshold mask, so calibration adds nothing but a different grid.

  * Platt / isotonic on p_fg (or on logit p_fg): increasing in p_fg by construction. Exact equivalence.
  * Temperature T on the 5-class logits: p_fg(T) = 1 - softmax(z / T)_bg. It is not a function of p_fg alone (it
    depends on how the vessel mass splits between classes), and argmax is unchanged by any T. This script measures
    how far {p_fg(T) >= t} can be from the nearest raw-threshold mask {p_fg >= t'}, on synthetic 5-class logits with
    the rim structure of a coronary prediction (one dominant vessel class near the wall, others small).

Output: calib_equivalence.json. No data is read.
"""
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def softmax(z, T=1.0):
    z = z / T
    z = z - z.max(0, keepdims=True)
    e = np.exp(z)
    return e / e.sum(0, keepdims=True)


def main():
    rng = np.random.default_rng(4)
    n = 400_000
    # rim voxels: background logit 0, the dominant vessel logit spans the wall, the 3 others well below
    z = np.zeros((5, n))
    z[1] = rng.uniform(-6, 6, n)                                   # dominant vessel, across the wall
    for k in (2, 3, 4):
        z[k] = z[1] - rng.uniform(2.5, 8.0, n)                     # minor vessels (class split varies per voxel)
    # junction voxels (two vessels compete, as at a bifurcation): 5 % of the rim
    j = rng.random(n) < 0.05
    z[2, j] = z[1, j] - rng.uniform(0, 1.5, j.sum())
    pfg = 1 - softmax(z)[0]
    rows = []
    for T in (0.7, 0.85, 1.25, 1.5, 2.0):
        pT = 1 - softmax(z, T)[0]
        assert (softmax(z, T).argmax(0) == softmax(z).argmax(0)).all()   # argmax is invariant to T
        for t in (0.45, 0.40, 0.35, 0.30, 0.25):
            m = pT >= t
            # the raw threshold t' whose mask is closest (by voxel disagreement) to the calibrated mask
            cand = np.quantile(pfg, np.linspace(0.0, 1.0, 2001))
            dis = [np.count_nonzero(m != (pfg >= c)) for c in cand]
            k = int(np.argmin(dis))
            rows.append(dict(T=T, t=t, nearest_raw_t=round(float(cand[k]), 4),
                             disagree_share_of_calibrated_mask=round(dis[k] / max(1, m.sum()), 5)))
    worst = max(r['disagree_share_of_calibrated_mask'] for r in rows)
    out = dict(note='synthetic 5-class rim logits; no data read', n_voxels=n, junction_share=0.05,
               argmax_invariant_to_T=True, worst_disagreement_share=worst, rows=rows,
               reading=('Platt or isotonic calibration of p_fg is exactly a re-gridding of Rule W. Temperature '
                        'scaling leaves argmax unchanged and, at the rim, its masks equal a raw-threshold mask up to '
                        'the share printed: a calibration step can only move t*, not add a mask Rule W cannot reach '
                        'on a finer or wider grid.'))
    json.dump(out, open(os.path.join(HERE, 'calib_equivalence.json'), 'w'), indent=1)
    print(json.dumps(dict(worst=worst, sample=rows[:5]), indent=1))


if __name__ == '__main__':
    main()
