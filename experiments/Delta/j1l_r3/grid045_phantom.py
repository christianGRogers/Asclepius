"""Delta, Janus 1-L round 3 (#302, Round 2 ruling §5 item 3): do t* and Rule T carry to a run on a 0.45 mm grid?

nnU-Net 2.8.1 resamples a network's probabilities back to the CT's own grid before it saves them
(`export_prediction.py`: `resampling_fn_probabilities`, then `revert_cropping_on_probabilities`), and every export,
score and Rule T measurement in the plan is made on that native grid. So a 0.45 mm run S and Janus 0 (0.5 mm) meet
on the same voxels. What can differ is the rim: each network's probability is sampled on its own grid and
interpolated (order 1, nnU-Net's default for probabilities) to the native one.

Phantom (synthetic trees from ../j1l_r2/transfer_phantom.py, 55 mm box; native grid 0.35 x 0.35 x 0.5 mm, the
median ImageCAS spacing):
  Janus 0   p = sigmoid((R - b0 - d) / tau0) sampled on 0.5 mm, interpolated to native;
  S         the same form on 0.45 mm, in four scenarios: same rim; a width gain (b = 0.03 mm); sharper (tau x 0.7);
            softer (tau x 1.4).
  Rule W    t* = best mean Dice of Janus 0 on 8 tuning trees (native grid).
  Rule T    rule_t.py's own case_diffs / trimmed / choose on 8 drift trees, unlabelled, native spacing.
  locked    8 more trees: Dice of S at the frozen t*, at Rule T's t_S, and at the oracle t.
Writes grid045_phantom.json. About 3-6 min on 4 cores.
"""
import json
import os
import sys

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'j1l_r2'))
import transfer_phantom as tp  # noqa: E402  (tree generator, B0, TAU0)
import rule_t  # noqa: E402

BOX = np.array(tp.SHAPE) * tp.SP          # 55 mm
NATIVE = np.array([0.35, 0.35, 0.5])
GRID = list(rule_t.GRID)


def grid_pts(sp):
    n = np.floor(BOX / sp).astype(int)
    return n, (np.indices(n).reshape(3, -1).T * sp)


def field(kd, rad, bid, sp):
    n, pts = grid_pts(sp)
    d, i = kd.query(pts, distance_upper_bound=4.0)
    far = ~np.isfinite(d); i[far] = 0; d[far] = 9.0
    return d.reshape(n), rad[i].reshape(n), bid[i].reshape(n)


def to_native(p, sp):
    n, _ = grid_pts(NATIVE)
    coords = np.indices(n).reshape(3, -1) * NATIVE[:, None] / sp
    return ndimage.map_coordinates(p, coords, order=1, mode='nearest').reshape(n)


def model_native(t, kind):
    kd, rad, bid = t
    if kind == 'janus0':
        sp, b, tau = 0.5, tp.B0, tp.TAU0
    else:
        sp = 0.45
        b, tau = {'same': (tp.B0, tp.TAU0), 'width_gain': (0.03, tp.TAU0), 'sharper': (tp.B0, tp.TAU0 * 0.7),
                  'softer': (tp.B0, tp.TAU0 * 1.4)}[kind]
    d, R, bb = field(kd, rad, bid, sp)
    p = tp.prob(d, R, b, tau)
    p = np.where(bb == 3, 0.0, p)
    return to_native(p.astype(np.float32), sp)


def truth(t):
    kd, rad, bid = t
    d, R, bb = field(kd, rad, bid, NATIVE)
    return (d <= R) & (bb != 3)


def dice(a, b):
    return 2.0 * (a & b).sum() / (a.sum() + b.sum())


def run(seed=21, n=8):
    rng = np.random.default_rng(seed)
    sets = {}
    for k in ('tuning', 'drift', 'locked'):
        sets[k] = []
        for _ in range(n):
            ax, rad, bid = tp.tree(rng)
            sets[k].append((cKDTree(ax), rad, bid))
    tun_p = [model_native(t, 'janus0') for t in sets['tuning']]
    tun_g = [truth(t) for t in sets['tuning']]
    tun = {t: float(np.mean([dice(p >= t, g) for p, g in zip(tun_p, tun_g)])) for t in GRID}
    best = max(tun[t] for t in GRID if 0.30 <= t <= 0.50)
    tstar = max(t for t in GRID if 0.30 <= t <= 0.50 and tun[t] >= best - 0.002)
    out = dict(native_mm=NATIVE.tolist(), janus0=dict(grid_mm=0.5, t_star=tstar,
                                                      tuning_dice={f'{t:.2f}': round(v, 4) for t, v in tun.items()}),
               scenarios={})
    j0_drift = [model_native(t, 'janus0') >= tstar for t in sets['drift']]
    lock_g = [truth(t) for t in sets['locked']]
    for kind in ('same', 'width_gain', 'sharper', 'softer'):
        pooled = {t: [] for t in GRID}
        for t_, m0 in zip(sets['drift'], j0_drift):
            p = model_native(t_, kind)
            d = rule_t.case_diffs(m0, {t: p >= t for t in GRID}, NATIVE)
            for t in GRID:
                pooled[t].append(d[t])
        dr = {t: rule_t.trimmed(np.concatenate(pooled[t])) for t in GRID}
        t_S = rule_t.choose(dr, tstar)
        lp = [model_native(t, kind) for t in sets['locked']]
        dl = {t: float(np.mean([dice(p >= t, g) for p, g in zip(lp, lock_g)])) for t in GRID}
        t_or = max((t for t in GRID if t <= 0.50), key=lambda t: dl[t])
        out['scenarios'][kind] = dict(dr_mm={f'{t:.2f}': round(v, 4) for t, v in dr.items()},
                                      t_frozen=tstar, t_rule_T=t_S, t_oracle=t_or,
                                      locked_dice=dict(frozen=round(dl[tstar], 4), rule_T=round(dl[t_S], 4),
                                                       oracle=round(dl[t_or], 4), argmax=round(dl[0.50], 4)),
                                      loss_vs_oracle=dict(frozen=round(dl[t_or] - dl[tstar], 4),
                                                          rule_T=round(dl[t_or] - dl[t_S], 4)))
        print(kind, out['scenarios'][kind]['t_frozen'], t_S, t_or, out['scenarios'][kind]['locked_dice'], flush=True)
    j0_lock = [model_native(t, 'janus0') for t in sets['locked']]
    out['janus0']['locked_dice_at_t_star'] = round(float(np.mean([dice(p >= tstar, g)
                                                                  for p, g in zip(j0_lock, lock_g)])), 4)
    return out


if __name__ == '__main__':
    o = run()
    json.dump(o, open(os.path.join(HERE, 'grid045_phantom.json'), 'w'), indent=1)
    print(json.dumps(o['janus0']))
