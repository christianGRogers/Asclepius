"""Delta, Janus 1-L round 2: does t* chosen on Janus 0 transfer to the candidate C, and what label-free rule fixes
it when it does not? Synthetic coronary-like trees on a 0.5 mm grid; no real image, label or score is read.

Each tree: a tapering trunk (radius 2.0 -> 0.8 mm) with two side branches (1.2 -> 0.6 mm), on random smooth paths.
A model's probability of vessel at a voxel x is sigmoid((R(x) - b - d(x)) / tau), with d the distance to the
nearest axis point and R its radius: b is the boundary's inward bias, tau its softness. Janus 0 = (b0, tau0) is set
so that its argmax volume ratio is near the measured 0.867 ([[icx4 - Results]]: 0.867).

Steps, as in the plan:
  1. Rule W (Dice only here): t* = the grid t with the best mean Dice of Janus 0 on 12 tuning trees.
  2. The candidate C differs from Janus 0 in one way (scenarios below). On 12 *drift* trees (no labels used),
     Rule T measures the width difference on the shared centreline: dr(t) = trimmed mean over the skeleton
     points of Janus 0 at t* that C(t) also covers, of EDT_C(t) - EDT_J0(t*) (local radius, mm).
     t_T = the grid t with the smallest |dr|; ties within 0.005 mm go to t*, then the larger t (rule_t.py also
     never chooses t > 0.50; no scenario here chose one, so the results are the same).
  3. On 12 *locked* trees: Dice and volume ratio of C at t*, at t_T, and at the oracle t (best Dice on truth).
Scenarios for C: same as Janus 0; sharper (tau x 0.6); softer (tau x 1.6); the two-member ensemble (members
b0 +- 0.15 mm, per-tree random sign, probabilities averaged); a real width gain (b = 0); extra extent (C also
draws a distal branch that Janus 0 misses, at Janus 0's width).

Usage: python transfer_phantom.py   (writes transfer_phantom.json; about 2-4 min on 4 cores)
"""
import json
import os

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree
from skimage.morphology import skeletonize

HERE = os.path.dirname(os.path.abspath(__file__))
SP = 0.5
SHAPE = (110, 110, 110)
GRID = [0.60, 0.55, 0.50, 0.45, 0.40, 0.35, 0.30, 0.25]
B0, TAU0 = 0.07, 0.22


def path(rng, start, n=60, step=0.9):
    p = [np.asarray(start, float)]
    d = rng.normal(size=3); d /= np.linalg.norm(d)
    for _ in range(n):
        d = d + 0.25 * rng.normal(size=3); d /= np.linalg.norm(d)
        q = p[-1] + step * d
        q = np.clip(q, 6, np.array(SHAPE) * SP - 6)
        p.append(q)
    return np.array(p)


def tree(rng):
    """Axis points (mm), radius (mm), and branch id (0 trunk, 1-2 side, 3 the distal extra branch)."""
    c = np.array(SHAPE) * SP / 2
    trunk = path(rng, c + rng.normal(0, 4, 3), n=55)
    rt = np.linspace(2.0, 0.8, len(trunk))
    pts, rad, bid = [trunk], [rt], [np.zeros(len(trunk))]
    for k, at in ((1, 15), (2, 30)):
        b = path(rng, trunk[at], n=30)
        pts.append(b); rad.append(np.linspace(1.2, 0.6, len(b))); bid.append(np.full(len(b), k))
    e = path(rng, trunk[-1], n=18, step=0.8)
    pts.append(e); rad.append(np.linspace(0.8, 0.55, len(e))); bid.append(np.full(len(e), 3))
    return np.concatenate(pts), np.concatenate(rad), np.concatenate(bid)


GRIDPTS = np.indices(SHAPE).reshape(3, -1).T * SP


def fields(ax, rad, bid):
    kd = cKDTree(ax)
    d, i = kd.query(GRIDPTS, distance_upper_bound=4.0)
    far = ~np.isfinite(d)
    i[far] = 0
    d[far] = 9.0
    return d.reshape(SHAPE), rad[i].reshape(SHAPE), bid[i].reshape(SHAPE)


def prob(d, R, b, tau):
    return 1.0 / (1.0 + np.exp(-(R - b - d) / tau))


def model(f, kind, rng=None):
    d, R, bid = f
    if kind == 'janus0':
        p = prob(d, R, B0, TAU0)
    elif kind == 'same':
        p = prob(d, R, B0, TAU0)
    elif kind == 'sharper':
        p = prob(d, R, B0, TAU0 * 0.6)
    elif kind == 'softer':
        p = prob(d, R, B0, TAU0 * 1.6)
    elif kind == 'ensemble':
        s = rng.choice([-1, 1])
        p = 0.5 * (prob(d, R, B0 + 0.15 * s, TAU0) + prob(d, R, B0 - 0.15 * s, TAU0))
    elif kind == 'width_gain':
        p = prob(d, R, 0.0, TAU0)
    elif kind == 'extent':
        p = prob(d, R, B0, TAU0)
    else:
        raise ValueError(kind)
    if kind != 'extent':
        p = np.where(bid == 3, 0.0, p)          # every model but 'extent' misses the distal extra branch
    return p


def truth(f):
    d, R, _ = f
    return d <= R


def dice(a, b):
    return 2.0 * (a & b).sum() / (a.sum() + b.sum())


def radii_on(skel, mask):
    return ndimage.distance_transform_edt(mask, sampling=SP)[skel]


def trimmed(x, g=0.10):
    x = np.sort(x); k = int(round(g * len(x)))
    return float(x[k:len(x) - k].mean())


def run(seed=11, n=12):
    rng = np.random.default_rng(seed)
    sets = {k: [fields(*tree(rng)) for _ in range(n)] for k in ('tuning', 'drift', 'locked')}
    tun = {t: np.mean([dice(model(f, 'janus0') >= t, truth(f)) for f in sets['tuning']]) for t in GRID}
    vr0 = np.mean([(model(f, 'janus0') >= 0.5).sum() / truth(f).sum() for f in sets['tuning']])
    best = max(tun.values())
    tstar = max(t for t in GRID if tun[t] >= best - 0.002 and 0.30 <= t <= 0.50)
    out = dict(janus0=dict(b_mm=B0, tau_mm=TAU0, vr_argmax=round(float(vr0), 3),
                           tuning_dice={str(t): round(float(v), 4) for t, v in tun.items()}, t_star=tstar),
               scenarios={})
    j0 = []
    for f in sets['drift']:
        m = model(f, 'janus0') >= tstar
        j0.append((skeletonize(m), m))
    for kind in ('same', 'sharper', 'softer', 'ensemble', 'width_gain', 'extent'):
        r2 = np.random.default_rng(seed + 1)
        drift_p = [model(f, kind, r2) for f in sets['drift']]
        dr = {}
        for t in GRID:
            diffs = []
            for (sk, m0), p in zip(j0, drift_p):
                mc = p >= t
                shared = sk & mc
                if shared.sum() < 20:
                    continue
                diffs.append(radii_on(shared, mc) - radii_on(shared, m0))
            dr[t] = trimmed(np.concatenate(diffs))
        dvol = {t: float(np.median([(p >= t).sum() / m0.sum() for (sk, m0), p in zip(j0, drift_p)])) for t in GRID}
        best_abs = min(abs(v) for v in dr.values())
        cands = [t for t in GRID if abs(dr[t]) <= best_abs + 0.005]
        t_T = tstar if tstar in cands else max(cands)
        t_V = min(GRID, key=lambda t: (abs(dvol[t] - 1.0), -t))
        r3 = np.random.default_rng(seed + 2)
        lp = [model(f, kind, r3) for f in sets['locked']]
        tr = [truth(f) for f in sets['locked']]
        dl = {t: float(np.mean([dice(p >= t, g) for p, g in zip(lp, tr)])) for t in GRID}
        vl = {t: float(np.mean([(p >= t).sum() / g.sum() for p, g in zip(lp, tr)])) for t in GRID}
        t_or = max(GRID, key=lambda t: dl[t])
        out['scenarios'][kind] = dict(
            drift_dr_mm={str(t): round(v, 4) for t, v in dr.items()},
            drift_volume_ratio={str(t): round(v, 3) for t, v in dvol.items()},
            t_frozen=tstar, t_rule_T=t_T, t_volume_match=t_V, t_oracle=t_or,
            locked_dice=dict(frozen=round(dl[tstar], 4), rule_T=round(dl[t_T], 4), volume_match=round(dl[t_V], 4),
                             oracle=round(dl[t_or], 4), argmax=round(dl[0.5], 4)),
            locked_volume_ratio=dict(frozen=round(vl[tstar], 3), rule_T=round(vl[t_T], 3),
                                     volume_match=round(vl[t_V], 3), oracle=round(vl[t_or], 3)))
    return out


if __name__ == '__main__':
    o = run()
    json.dump(o, open(os.path.join(HERE, 'transfer_phantom.json'), 'w'), indent=1)
    print(json.dumps(o['janus0']))
    for k, v in o['scenarios'].items():
        print(k, 't*', v['t_frozen'], 'T', v['t_rule_T'], 'V', v['t_volume_match'], 'oracle', v['t_oracle'],
              v['locked_dice'], v['locked_volume_ratio'])
