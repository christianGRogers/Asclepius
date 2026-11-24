"""Foxtrot, Janus 1-L round 3: how finely can Rule T (L-A15) resolve a width shift between Janus 0 and C?

Rule T compares C(t) with Janus 0 at t* through dr(t) = 10 %-trimmed mean, over Janus 0's skeleton points that C(t)
covers, of EDT(C(t)) - EDT(J0(t*)). An EDT value at a centreline point is a *minimum* over directions of the
distance to the nearest background voxel, on the voxel grid. The width change the export threshold makes is
sub-voxel: Rule W's grid moves the wall by soft x logit(t), about 0.05 mm per 0.05 step of t for a rim of
softness 0.25 mm. So the question is whether dr(t) sees shifts of that size, or ties at zero and falls back to t*.

Phantoms (no data): curved tubes of radius 0.8-2.6 mm, analytic distance to the axis (continuous geometry), on a
0.4 mm or 0.5 mm grid. Probability of vessel p = sigmoid((R - dist - w) / soft) + smooth noise, where w is the
model's wall offset (w > 0: drawn thin, as Janus 0). Thresholding at t puts the wall w + soft * logit(t) inside the true wall.

  oracle  t_C* = the grid t <= 0.50 whose wall offset for C is closest to Janus 0's at t* (exact, from w and soft);
  rule T  Delta's rule_t.case_diffs / trimmed / choose, imported unchanged;
  alt     the shared-tube offset: dV / A, where dV = |C(t) & B| - |J0(t*) & B| and A = J0(t*)'s surface area in B,
          B = the voxels within (local radius + 1 mm) of J0(t*)'s skeleton points that C(t) covers. It counts every
          rim voxel (so it averages sub-voxel shifts), and stays near the shared centreline (so extent barely moves
          it: an extra branch only enters B where it leaves the shared vessel).

Scenarios: Janus 0 w0 = 0.20 mm, soft 0.25; t* = 0.35 (Rule W's typical pick for that rim). C differs by its wall
offset (C as wide as J0 at t*, half way, as thin as J0, wider than J0 at t*), its softness, and extent (C draws an
extra branch; C misses a distal piece). 12 cases of 3 tubes each per scenario.

Output: rule_t_resolution.json; one row per scenario and grid with t_oracle, t_ruleT, t_alt and the wall error each
choice leaves (mm). Usage: python rule_t_resolution.py [--quick]
"""
import argparse
import json
import os
import sys

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'experiments', 'Delta', 'j1l_r2'))
import rule_t as RT  # noqa: E402  (Delta's Rule T, unchanged)

GRID = RT.GRID
TSTAR = 0.35


def logit(t):
    return np.log(t / (1 - t))


def tube_field(shape, sp, rng, n_tubes=3, extra_branch=False, cut_distal=False):
    """Signed 'R - dist' field (mm) of n curved tubes, max over tubes; a second field for C if its extent differs."""
    zz, yy, xx = [np.arange(n) * s for n, s in zip(shape, sp)]
    Z, Y, X = np.meshgrid(zz, yy, xx, indexing='ij')
    P = np.stack([Z, Y, X], -1).reshape(-1, 3)
    ext = np.array(shape) * np.array(sp)
    f = np.full(len(P), -np.inf)
    fC = np.full(len(P), -np.inf)
    for k in range(n_tubes):
        a = rng.uniform(0.15, 0.85, 3) * ext
        d = rng.normal(size=3); d /= np.linalg.norm(d)
        bend = rng.normal(size=3) * 0.15
        L = 0.9 * ext.min()
        s = np.linspace(-L / 2, L / 2, 40)
        pts = a + s[:, None] * d + (s[:, None] ** 2 / L) * bend[None, :] * 4
        r = np.linspace(rng.uniform(1.6, 2.6), rng.uniform(0.8, 1.4), len(pts))
        dist = np.full(len(P), np.inf); rr = np.zeros(len(P)); sidx = np.zeros(len(P), int)
        for i in range(len(pts) - 1):
            p0, p1 = pts[i], pts[i + 1]
            v = p1 - p0
            u = np.clip(((P - p0) @ v) / (v @ v), 0, 1)
            q = np.linalg.norm(P - (p0 + u[:, None] * v), axis=1)
            take = q < dist
            dist[take] = q[take]; rr[take] = (r[i] + u * (r[i + 1] - r[i]))[take]; sidx[take] = i
        g = rr - dist
        f = np.maximum(f, g)
        gc = g.copy()
        if cut_distal and k == 0:
            gc[sidx >= int(0.75 * len(pts))] = -np.inf          # C misses the last quarter of tube 0
        fC = np.maximum(fC, gc)
        if extra_branch and k == 0:
            b0 = pts[len(pts) // 2]
            bd = rng.normal(size=3); bd -= (bd @ d) * d; bd /= np.linalg.norm(bd)
            b1 = b0 + bd * 0.35 * L
            v = b1 - b0
            u = np.clip(((P - b0) @ v) / (v @ v), 0, 1)
            q = np.linalg.norm(P - (b0 + u[:, None] * v), axis=1)
            fC = np.maximum(fC, 0.9 - q)                           # a 0.9 mm branch only C draws
    return f.reshape(shape), fC.reshape(shape)


def smooth_noise(shape, rng, sd, sigma_vox=2.0):
    n = ndimage.gaussian_filter(rng.normal(size=shape), sigma_vox)
    return n / (n.std() + 1e-12) * sd


def prob(field, w, soft, noise):
    return 1.0 / (1.0 + np.exp(-(field - w) / soft + noise))


def alt_offset(m0, m, sp):
    """Shared-tube wall offset dV / A (mm); positive when C(t) is wider than Janus 0 at t* near the shared centreline."""
    sk = RT.skeleton(m0) & m
    if not sk.any():
        return np.nan, 0.0, 0.0
    r0 = ndimage.distance_transform_edt(m0, sampling=sp)
    d_sk, idx = ndimage.distance_transform_edt(~sk, sampling=sp, return_indices=True)
    B = d_sk <= r0[tuple(idx)] + 1.0
    vv = float(np.prod(sp))
    dV = (np.count_nonzero(m & B) - np.count_nonzero(m0 & B)) * vv
    surf = m0 & ~ndimage.binary_erosion(m0)
    # face area of the boundary voxels: count exposed faces, weighted by the face area of each axis
    A = 0.0
    for ax, (a1, a2) in enumerate(((1, 2), (0, 2), (0, 1))):
        for sh in (1, -1):
            nb = np.roll(m0, sh, axis=ax)
            A += np.count_nonzero(m0 & ~nb & B) * sp[a1] * sp[a2]
    return dV / A if A > 0 else np.nan, dV, A


def choose_alt(off, tstar):
    finite = {t: v for t, v in off.items() if np.isfinite(v) and t <= 0.50 + 1e-9}
    best = min(abs(v) for v in finite.values())
    cands = [t for t, v in finite.items() if abs(v) <= best + 0.005]
    return tstar if tstar in cands else max(cands)


def scenario(name, sp, n_cases, rng, w0=0.20, s0=0.25, wC=0.20, sC=0.25, extra=False, cut=False, noise_sd=0.3):
    shape = (64, 64, 64) if sp[0] >= 0.5 else (72, 72, 72)
    pooled = {t: [] for t in GRID}
    alt = {t: [0.0, 0.0] for t in GRID}
    for i in range(n_cases):
        f, fC = tube_field(shape, sp, rng, extra_branch=extra, cut_distal=cut)
        nz0, nzC = smooth_noise(shape, rng, noise_sd), smooth_noise(shape, rng, noise_sd)
        m0 = prob(f, w0, s0, nz0) >= TSTAR
        pC = prob(fC, wC, sC, nzC)
        masks = {t: pC >= t for t in GRID}
        dd = RT.case_diffs(m0, masks, np.array(sp))
        for t in GRID:
            pooled[t].append(dd[t])
            _, dV, A = alt_offset(m0, masks[t], np.array(sp))
            alt[t][0] += dV; alt[t][1] += A
    dr = {t: RT.trimmed(np.concatenate(pooled[t])) for t in GRID}
    dr_mean = {t: float(np.concatenate(pooled[t]).mean()) for t in GRID}
    frac0 = {t: float((np.abs(np.concatenate(pooled[t])) < 1e-9).mean()) for t in GRID}
    off = {t: alt[t][0] / alt[t][1] for t in GRID}
    # oracle: wall offsets (mm, positive = inside the true wall) of J0 at t* and C at t
    wall0 = w0 + s0 * logit(TSTAR)
    wallC = {t: wC + sC * logit(t) for t in GRID}
    elig = [t for t in GRID if t <= 0.50 + 1e-9]
    t_or = min(elig, key=lambda t: (abs(wallC[t] - wall0), -t))
    t_rt = RT.choose(dr, TSTAR)
    t_alt = choose_alt(off, TSTAR)
    err = lambda t: round(float(wallC[t] - wall0), 3)  # noqa: E731  (C's wall minus J0's at t*, mm; + = C thinner)
    return dict(scenario=name, spacing_mm=sp[0], n_cases=n_cases, wC=wC, softC=sC, extra_branch=extra,
                cut_distal=cut, t_oracle=t_or, t_ruleT=t_rt, t_alt=t_alt,
                wall_error_mm=dict(oracle=err(t_or), ruleT=err(t_rt), alt=err(t_alt), frozen_tstar=err(TSTAR)),
                dr_trimmed_mm={f'{t:.2f}': round(v, 4) for t, v in dr.items()},
                dr_untrimmed_mm={f'{t:.2f}': round(v, 4) for t, v in dr_mean.items()},
                share_of_points_with_dr_exactly_0={f'{t:.2f}': round(v, 3) for t, v in frac0.items()},
                alt_offset_mm={f'{t:.2f}': round(v, 4) for t, v in off.items()})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--quick', action='store_true')
    a = ap.parse_args()
    n = 4 if a.quick else 12
    w0, s0 = 0.20, 0.25
    wall0 = w0 + s0 * logit(TSTAR)                       # J0 at t* sits wall0 inside the true wall
    S = [  # (name, kwargs): C's wall offset wC chosen so C(0.50) sits where named
        ('C = Janus 0 (no drift)', dict(wC=w0)),
        ('C wider: C(0.50) = J0(t*)', dict(wC=wall0)),
        ('C half way', dict(wC=(w0 + wall0) / 2)),
        ('C wider than J0(t*)', dict(wC=wall0 - 0.10)),
        ('C thinner than J0', dict(wC=w0 + 0.08)),
        ('C softer rim (0.35)', dict(wC=w0, sC=0.35)),
        ('C wider + extra branch', dict(wC=(w0 + wall0) / 2, extra=True)),
        ('C wider + missing distal', dict(wC=(w0 + wall0) / 2, cut=True)),
    ]
    rows = []
    for sp in ((0.5, 0.5, 0.5), (0.4, 0.4, 0.4)):
        for name, kw in S:
            rng = np.random.default_rng(1000 + len(rows))
            r = scenario(name, sp, n, rng, w0=w0, s0=s0, **kw)
            rows.append(r)
            print(f"[res] {sp[0]} mm | {name:28s} oracle {r['t_oracle']:.2f} ruleT {r['t_ruleT']:.2f} "
                  f"alt {r['t_alt']:.2f} | wall err mm: ruleT {r['wall_error_mm']['ruleT']:+.3f} "
                  f"alt {r['wall_error_mm']['alt']:+.3f} frozen {r['wall_error_mm']['frozen_tstar']:+.3f} | "
                  f"dr0 share@0.50 {r['share_of_points_with_dr_exactly_0']['0.50']}", flush=True)
    summ = {}
    for key in ('ruleT', 'alt', 'frozen_tstar'):
        e = [abs(r['wall_error_mm'][key]) for r in rows]
        summ[key] = dict(mean_abs_wall_error_mm=round(float(np.mean(e)), 3), max=round(float(np.max(e)), 3),
                         exact_grid_hits=sum(r['t_' + ('ruleT' if key == 'ruleT' else 'alt')] == r['t_oracle']
                                             for r in rows) if key != 'frozen_tstar' else
                         sum(TSTAR == r['t_oracle'] for r in rows))
    out = dict(note='phantoms only; Rule T imported unchanged from experiments/Delta/j1l_r2/rule_t.py',
               janus0=dict(w0=w0, soft=s0, t_star=TSTAR, wall_at_tstar_mm=round(float(wall0), 3)),
               grid=list(GRID), summary=summ, rows=rows)
    json.dump(out, open(os.path.join(HERE, 'rule_t_resolution.json' if not a.quick else 'rule_t_resolution_quick.json'),
                        'w'), indent=1)
    print(json.dumps(summ, indent=1))


if __name__ == '__main__':
    main()
