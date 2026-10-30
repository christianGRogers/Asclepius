"""Kilo's layer geometry: everything except the myocardium mask is computed, not learned.

From an LV myocardium mask, an LV cavity mask and an RV cavity mask this gives, per voxel:
  - transmural depth t in [0, 1] (0 = endocardium, 1 = epicardium) from Laplace's equation
    (Jones et al. 2000), and from the distance ratio d_endo / (d_endo + d_epi) as a check;
  - wall thickness in mm (d_endo + d_epi, Euclidean);
  - the transmural third (1 subendocardial, 2 mid-wall, 3 subepicardial);
  - the AHA 17-segment label (Cerqueira et al. 2002) and its standard coronary territory.

Boundary conditions for Laplace: t = 0 on myocardium voxels face-adjacent to the LV cavity,
t = 1 on voxels face-adjacent to anything that is neither cavity nor myocardium except the
atria and aorta (the basal opening), which are no-flux. Solved as a sparse linear system.
"""
from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import cg

FACE = ndi.generate_binary_structure(3, 1)
AHA_TERRITORY = {**{s: "LAD" for s in (1, 2, 7, 8, 13, 14, 17)},
                 **{s: "RCA" for s in (3, 4, 9, 10, 15)},
                 **{s: "LCx" for s in (5, 6, 11, 12, 16)}}


def laplace_depth(myo, cav, noflux=None, tol=1e-6, maxiter=4000):
    """Transmural depth by Laplace's equation on the myocardium voxels."""
    myo = myo.astype(bool); cav = cav.astype(bool) & ~myo
    noflux = np.zeros_like(myo) if noflux is None else (noflux.astype(bool) & ~myo & ~cav)
    idx = -np.ones(myo.shape, np.int64)
    pts = np.argwhere(myo); n = len(pts); idx[tuple(pts.T)] = np.arange(n)
    rows, cols, vals = [], [], []
    diag = np.zeros(n); rhs = np.zeros(n)
    shape = np.array(myo.shape)
    for ax in range(3):
        for s in (-1, 1):
            nb = pts.copy(); nb[:, ax] += s
            ok = (nb[:, ax] >= 0) & (nb[:, ax] < shape[ax])
            j = np.full(n, -1, np.int64); j[ok] = idx[tuple(nb[ok].T)]
            inside = j >= 0
            # neighbour in myocardium: unknown
            rows.append(np.nonzero(inside)[0]); cols.append(j[inside]); vals.append(-np.ones(inside.sum()))
            diag[inside] += 1
            out = ~inside
            nbo = nb.copy(); nbo[~ok] = 0
            is_cav = np.zeros(n, bool); is_cav[ok] = cav[tuple(nb[ok].T)]
            is_nf = np.zeros(n, bool); is_nf[ok] = noflux[tuple(nb[ok].T)]
            endo = out & is_cav
            epi = out & ~is_cav & ~is_nf
            diag[endo] += 1  # t = 0 there
            diag[epi] += 1; rhs[epi] += 1  # t = 1 there
    A = coo_matrix((np.concatenate(vals + [diag]),
                    (np.concatenate(rows + [np.arange(n)]), np.concatenate(cols + [np.arange(n)]))),
                   shape=(n, n)).tocsr()
    x0 = np.full(n, 0.5)
    x, info = cg(A, rhs, x0=x0, rtol=tol, maxiter=maxiter)
    t = np.full(myo.shape, np.nan, np.float32); t[tuple(pts.T)] = np.clip(x, 0, 1)
    return t, info


def distance_depth(myo, cav, noflux, spacing):
    """Distance-ratio depth and thickness (mm)."""
    myo = myo.astype(bool); cav = cav.astype(bool) & ~myo
    epi_side = ~myo & ~cav & ~(noflux.astype(bool) if noflux is not None else False)
    d_endo = ndi.distance_transform_edt(~cav, sampling=spacing)
    d_epi = ndi.distance_transform_edt(~epi_side, sampling=spacing)
    # d_endo and d_epi run from a wall voxel's centre to the nearest outside voxel's centre, so
    # their sum overstates the wall by one voxel; take off one (mean) spacing.
    s = float(np.mean(spacing))
    thick = np.where(myo, d_endo + d_epi - s, np.nan)
    t = np.where(myo, np.clip((d_endo - s / 2) / np.maximum(d_endo + d_epi - s, 1e-6), 0, 1), np.nan)
    return t.astype(np.float32), thick.astype(np.float32)


def thirds(t):
    out = np.zeros(t.shape, np.uint8)
    ok = ~np.isnan(t)
    out[ok] = 1 + np.minimum((t[ok] * 3).astype(int), 2)
    return out


def aha17(myo, cav, rv, la, affine):
    """AHA 17 segments from the LV long axis and the RV direction.

    Long axis: first principal axis of LV cavity + myocardium, pointing from apex to base
    (base = side nearer the left atrium). Basal / mid / apical thirds split the cavity's extent
    along the axis; myocardium beyond the cavity's apical end is the apex (17). Circumferential
    zero = direction of the RV cavity centroid (the septum), turning towards anterior.
    """
    vox = np.argwhere(myo | cav).astype(float)
    world = lambda v: (affine[:3, :3] @ v.T).T + affine[:3, 3]
    P = world(vox); c = P.mean(0)
    w, V = np.linalg.eigh(np.cov((P - c).T)); ax = V[:, -1]
    la_c = world(np.argwhere(la).astype(float)).mean(0) if la.any() else c + ax
    if np.dot(la_c - c, ax) < 0: ax = -ax  # ax points apex -> base
    M = world(np.argwhere(myo).astype(float)); h = (M - c) @ ax
    Cv = world(np.argwhere(cav).astype(float)); hc = (Cv - c) @ ax
    lo, hi = hc.min(), hc.max()
    rv_c = world(np.argwhere(rv).astype(float)).mean(0)
    def perp(v):
        return v - np.outer(v @ ax, ax) if v.ndim == 2 else v - (v @ ax) * ax
    e1 = perp(rv_c - c); e1 /= np.linalg.norm(e1)
    e2 = np.cross(ax, e1)
    # orient e2 towards anterior (RAS: +y anterior; NIfTI affines are RAS)
    if e2[1] < 0: e2 = -e2
    q = perp(M - c)
    ang = np.degrees(np.arctan2(q @ e2, q @ e1))  # 0 = septum centre, + towards anterior
    seg = np.zeros(len(M), np.uint8)
    f = (h - lo) / (hi - lo)  # 0 apex end of cavity, 1 base
    level = np.where(h < lo, 3, np.where(f < 1 / 3, 2, np.where(f < 2 / 3, 1, 0)))  # 0 basal 1 mid 2 apical 3 apex
    # six sectors for basal/mid, starting at septum centre: [0,60)->2, [60,120)->1, [120,180)->6,
    # [-180,-120)->5, [-120,-60)->4, [-60,0)->3
    six = np.select([(ang >= 0) & (ang < 60), (ang >= 60) & (ang < 120), ang >= 120,
                     ang < -120, (ang >= -120) & (ang < -60)], [2, 1, 6, 5, 4], 3)
    four = np.select([(ang >= -45) & (ang < 45), (ang >= 45) & (ang < 135),
                      (ang >= -135) & (ang < -45)], [14, 13, 15], 16)
    seg = np.where(level == 0, six, np.where(level == 1, six + 6, np.where(level == 2, four, 17)))
    out = np.zeros(myo.shape, np.uint8); out[tuple(np.argwhere(myo).T)] = seg
    return out, {"axis": ax.tolist(), "cavity_length_mm": float(hi - lo)}
