"""Hotel R2 E2: one shared border-perturbation harness (Round 1 ruling §6 items 2 and 3).

Synthetic only: an analytic LV phantom (truncated prolate ellipsoids with an off-centre cavity, so the wall runs
from about 6 to 14 mm). No CT, no public or pool case is opened.

Part A replays the four Round 1 error models on one phantom, to test why "0.5 mm" gave subendocardial-third Dice
0.909 (Golf), 0.927 (India), 0.939 (Kilo) and 0.975 (Hotel). The four share one recipe: a Gaussian-smoothed noise
field, rescaled to a nominal std sigma, added to each border's signed distance field (SDF), then thresholded. They
differ in the SDF convention and the grid:
  golf   SDF with the half-voxel offset on the 1.5 mm source grid, linearly zoomed to 0.5 mm (unbiased);
  india  mask trilinearly resampled to 0.5 mm, SDF offset by a quarter voxel instead of a half;
  kilo   plain SDF (no offset) on the 1.5 mm grid, linearly zoomed to 0.5 mm;
  hotel  mask resampled to 0.75 mm, plain SDF on the 0.75 mm grid.
For each, the harness measures the achieved border displacement (mean |d| = changed volume / border area) as well
as Dice, so the four can be put on one axis.

Part B is the harness Hotel proposes: native 0.5 mm grid, the phantom's continuous (Sampson) SDF so that sub-voxel
shifts are representable, independent endo and epi fields, a sweep of
sigma and correlation length, plus constant biases. It reports subendocardial-third Dice, segment-thickness error,
Kim-bin flips for synthetic subendocardial scars (Kilo's STA idea), and the agreement of equal-thickness and Laplace
thirds on the unperturbed phantom.

    python experiments/JanusM/Hotel/r2/e2_harness.py OUT.json [--quick]
"""
import json
import sys
import time

import numpy as np
from scipy import ndimage as ndi
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import cg

RNG = np.random.default_rng(20261030)
KIM = np.array([0.0, 0.25, 0.50, 0.75, 1.0001])
TAUS = (0.15, 0.40, 0.65, 0.90)


# ---------------------------------------------------------------- phantom ---------------------------------------
def phantom(g, box=(84.0, 84.0, 72.0)):
    """Boolean (cavity, solid) on a grid of spacing g mm. solid = cavity + myocardium. Base cut at z = 0."""
    n = [int(round(b / g)) for b in box]
    x, y, z = np.meshgrid(*[(np.arange(k) + 0.5) * g for k in n], indexing="ij")
    cx, cy, ztop = box[0] / 2, box[1] / 2, box[2] - 6.0
    zz = ztop - z  # distance below the base plane
    outer = ((x - cx) / 34.0) ** 2 + ((y - cy) / 34.0) ** 2 + (zz / 60.0) ** 2 <= 1
    # cavity shifted +4 mm in x: wall about 6 mm on +x, 14 mm on -x, 9-10 mm elsewhere; apex about 8 mm
    inner = ((x - cx - 4.0) / 24.0) ** 2 + ((y - cy) / 24.0) ** 2 + (zz / 52.0) ** 2 <= 1
    keep = (zz >= 0)
    solid = outer & keep
    cav = inner & keep & solid
    return cav, solid


def phantom_sdf(g, box=(84.0, 84.0, 72.0)):
    """Continuous signed distances (mm, positive outside) of the same phantom: Sampson distance (q - 1) / |grad q|
    to each ellipsoid, intersected with the base half-space. Sub-voxel shifts are then representable."""
    n = [int(round(b / g)) for b in box]
    x, y, z = np.meshgrid(*[(np.arange(k) + 0.5) * g for k in n], indexing="ij")
    cx, cy, ztop = box[0] / 2, box[1] / 2, box[2] - 6.0
    zz = ztop - z

    def ell(x0, a, c):
        q = ((x - x0) / a) ** 2 + ((y - cy) / a) ** 2 + (zz / c) ** 2
        gr = 2 * np.sqrt(((x - x0) / a ** 2) ** 2 + ((y - cy) / a ** 2) ** 2 + (zz / c ** 2) ** 2)
        return (q - 1) / np.maximum(gr, 1e-6)

    base = -zz  # positive above the base plane (outside)
    Ss = np.maximum(ell(cx, 34.0, 60.0), base).astype(np.float32)
    Sc = np.maximum(ell(cx + 4.0, 24.0, 52.0), base).astype(np.float32)
    return Sc, Ss


def sectors(shape, g, cx, cy):
    n = shape
    x, y = np.meshgrid((np.arange(n[0]) + 0.5) * g - cx, (np.arange(n[1]) + 0.5) * g - cy, indexing="ij")
    ang = (np.degrees(np.arctan2(y, x)) + 360) % 360
    sec2d = (ang // 60).astype(np.int8)  # six 60-degree sectors
    z = (np.arange(n[2]) + 0.5) * g
    lev = np.digitize(z, [24.0, 46.0]).astype(np.int8)  # apical / mid / basal by height (phantom frame)
    seg = (sec2d[:, :, None] * 3 + lev[None, None, :]).astype(np.int8)  # 18 pseudo-segments
    seg[:, :, z > 60.0] = -1  # the open base rim (within 6 mm of the cut plane) is left out of every statistic
    return seg


# ---------------------------------------------------------------- SDFs -------------------------------------------
def sdf(m, g, offset_vox):
    """Signed distance (mm), positive outside. offset_vox: 0.5 for the unbiased convention, 0 for plain."""
    out = ndi.distance_transform_edt(~m)
    ins = ndi.distance_transform_edt(m)
    return np.where(m, -(ins - offset_vox), out - offset_vox) * g


def zoom_to(a, f, order=1):
    return ndi.zoom(a.astype(np.float32), f, order=order)


def field(shape, g, sigma, corr_mm):
    if sigma == 0:
        return np.zeros(shape, np.float32)
    n = ndi.gaussian_filter(RNG.standard_normal(shape).astype(np.float32), corr_mm / g)
    return (n / n.std() * sigma).astype(np.float32)


def pipeline(name, cav15, sol15):
    """Return (grid mm, SDF_cav, SDF_solid) as each Round 1 advocate built them from 1.5 mm masks."""
    if name == "golf":
        return 0.5, zoom_to(sdf(cav15, 1.5, 0.5), 3), zoom_to(sdf(sol15, 1.5, 0.5), 3)
    if name == "kilo":
        return 0.5, zoom_to(sdf(cav15, 1.5, 0.0), 3), zoom_to(sdf(sol15, 1.5, 0.0), 3)
    if name == "india":
        c = zoom_to(cav15, 3) >= 0.5
        s = zoom_to(sol15, 3) >= 0.5
        return 0.5, sdf(c, 0.5, 0.25), sdf(s, 0.5, 0.25)
    if name == "hotel":
        f = 1.5 / 0.75
        c = zoom_to(sdf(cav15, 1.0, 0.0), f) < 0
        s = zoom_to(sdf(sol15, 1.0, 0.0), f) < 0
        return 0.75, sdf(c, 0.75, 0.0), sdf(s, 0.75, 0.0)
    raise ValueError(name)


# ---------------------------------------------------------------- geometry ---------------------------------------
def depth_equal(cav, myo, g):
    """u = d_endo / (d_endo + d_epi): d_endo to the cavity, d_epi to the outside of the solid (cavity + myo)."""
    de = ndi.distance_transform_edt(~cav) * g
    dp = ndi.distance_transform_edt(myo | cav) * g
    u = de / np.maximum(de + dp, 1e-6)
    return u, de + dp


def depth_laplace(cav, solid, g, tol=1e-6):
    """Laplace u = 0 on the cavity, 1 outside the solid, zero-flux elsewhere is implicit (6-neighbour graph)."""
    myo = solid & ~cav
    idx = -np.ones(myo.shape, np.int64)
    pts = np.argwhere(myo)
    idx[tuple(pts.T)] = np.arange(len(pts))
    rows, cols = [], []
    b = np.zeros(len(pts))
    diag = np.zeros(len(pts))
    for ax in range(3):
        for s in (-1, 1):
            nb = pts.copy()
            nb[:, ax] += s
            ok = (nb[:, ax] >= 0) & (nb[:, ax] < myo.shape[ax])
            i = np.flatnonzero(ok)
            q = tuple(nb[i].T)
            j = idx[q]
            inmyo = j >= 0
            rows += [i[inmyo]]
            cols += [j[inmyo]]
            diag[i[inmyo]] += 1
            # Dirichlet neighbours
            isc = cav[q] & ~inmyo
            iso = ~solid[q] & ~inmyo
            diag[i[isc]] += 1
            diag[i[iso]] += 1
            b[i[iso]] += 1.0
    r = np.concatenate(rows)
    c = np.concatenate(cols)
    A = coo_matrix((np.concatenate([-np.ones(len(r)), diag]),
                    (np.concatenate([r, np.arange(len(pts))]), np.concatenate([c, np.arange(len(pts))]))),
                   shape=(len(pts), len(pts))).tocsr()
    u, _ = cg(A, b, rtol=tol, maxiter=5000)
    out = np.zeros(myo.shape, np.float32)
    out[tuple(pts.T)] = u
    return out


def thirds(u, myo):
    t = np.zeros(u.shape, np.int8)
    t[myo] = 1 + (u[myo] >= 1 / 3) + (u[myo] >= 2 / 3)
    return t


def dice(a, b):
    s = a.sum() + b.sum()
    return float(2 * (a & b).sum() / s) if s else float("nan")


def area(m, g):
    """Surface area (mm^2) by counting exposed faces."""
    a = 0
    for ax in range(3):
        a += np.count_nonzero(np.diff(m.astype(np.int8), axis=ax))
    return a * g * g


def displacement(ref_sdf, m_ref, m_new, g):
    """Achieved border movement, mean |d| (mm) = changed volume / border area."""
    ch = m_ref ^ m_new
    mean_abs = float(ch.sum() * g ** 3 / max(area(m_ref, g), 1e-6))
    return mean_abs


def transm(scar, myo, seg, s):
    sel = myo & (seg == s)
    n = sel.sum()
    return float((scar & sel).sum() / n) if n > 50 else float("nan")


def evaluate(g, Sc, Ss, cav_r, sol_r, u_r, th_r, seg, nc, ns, laplace=False):
    cp = Sc + nc < 0
    sp_ = Ss + ns < 0
    cp &= sp_
    roi = seg >= 0
    myo_p = sp_ & ~cp
    myo_r = sol_r & ~cav_r
    if laplace:
        u_p = depth_laplace(cp, sp_, g)
        th_p = depth_equal(cp, myo_p, g)[1]
    else:
        u_p, th_p = depth_equal(cp, myo_p, g)
    tr_r, tr_p = thirds(u_r, myo_r), thirds(u_p, myo_p)
    row = {
        "endo_mean_abs_d_mm": displacement(Sc, cav_r, cp, g),
        "epi_mean_abs_d_mm": displacement(Ss, sol_r, sp_, g),
        "dice_myo": dice(myo_r & roi, myo_p & roi),
        "dice_third": [dice((tr_r == k) & roi, (tr_p == k) & roi) for k in (1, 2, 3)],
    }
    errs = []
    for s in np.unique(seg[myo_r & roi]):
        a, b = myo_r & (seg == s), myo_p & (seg == s)
        if a.sum() > 50 and b.sum() > 50:
            errs.append(float(np.median(th_p[b]) - np.median(th_r[a])))
    row["seg_thick_abs_err_mm"] = float(np.mean(np.abs(errs)))
    row["seg_thick_err_signed_mm"] = [round(e, 3) for e in errs]
    flips = {}
    for tau in TAUS:
        f = []
        scar = myo_r & (u_r < tau)  # a fixed subendocardial scar, placed once on the reference borders
        for s in np.unique(seg[myo_r & roi]):
            ref = transm(scar, myo_r, seg, s)
            est = transm(scar, myo_p, seg, s)  # read inside the perturbed wall, as a model's borders would
            if not (np.isnan(ref) or np.isnan(est)):
                f.append(int(np.digitize(ref, KIM) != np.digitize(est, KIM)))
        flips[str(tau)] = float(np.mean(f))
    row["kim_bin_flip"] = flips
    return row


# ---------------------------------------------------------------- parts ------------------------------------------
def part_a(reps, sigmas):
    cav15, sol15 = phantom(1.5)
    out = {}
    for name in ("golf", "india", "kilo", "hotel"):
        g, Sc, Ss = pipeline(name, cav15, sol15)
        cav_r, sol_r = Sc < 0, Ss < 0
        cav_r &= sol_r
        myo_r = sol_r & ~cav_r
        u_r, th_r = depth_equal(cav_r, myo_r, g)
        seg = sectors(Sc.shape, g, 42.0, 42.0)
        res = []
        for sig in sigmas:
            for r in range(reps):
                nc = field(Sc.shape, g, sig, 8.0)
                ns = field(Sc.shape, g, sig, 8.0)
                row = evaluate(g, Sc, Ss, cav_r, sol_r, u_r, th_r, seg, nc, ns)
                row.update(sigma_mm=sig, rep=r)
                res.append(row)
        out[name] = {"grid_mm": g, "wall_median_mm": float(np.median(th_r[myo_r])), "rows": res}
        print("A", name, [(r["sigma_mm"], round(r["dice_third"][0], 3), round(r["endo_mean_abs_d_mm"], 3))
                          for r in res], flush=True)
    return out


def part_b(reps, sigmas, corrs, biases):
    g = 0.5
    Sc, Ss = phantom_sdf(g)
    sol = Ss < 0
    cav = (Sc < 0) & sol
    myo = sol & ~cav
    u_e, th = depth_equal(cav, myo, g)
    t0 = time.time()
    u_l = depth_laplace(cav, sol, g)
    seg = sectors(Sc.shape, g, 42.0, 42.0)
    te, tl = thirds(u_e, myo), thirds(u_l, myo)
    myo = myo & (seg >= 0)
    vox_per_third = th[myo] / 3 / g
    depth = {
        "laplace_seconds": round(time.time() - t0, 1),
        "agreement_equal_vs_laplace": float((te[myo] == tl[myo]).mean()),
        "third_volume_share_equal": [float((te[myo] == k).mean()) for k in (1, 2, 3)],
        "third_volume_share_laplace": [float((tl[myo] == k).mean()) for k in (1, 2, 3)],
        "wall_mm_p5_p50_p95": [float(np.percentile(th[myo], q)) for q in (5, 50, 95)],
        "vox_per_third_p5_p50": [float(np.percentile(vox_per_third, q)) for q in (5, 50)],
        "share_vox_lt4_per_third": float((vox_per_third < 4).mean()),
    }
    # agreement in the thin (< 8 mm) vs thick (> 12 mm) wall
    for lab, sel in (("thin_lt8mm", th < 8), ("thick_gt12mm", th > 12)):
        m = myo & sel
        depth[f"agreement_{lab}"] = float((te[m] == tl[m]).mean()) if m.any() else None
    print("B depth", depth, flush=True)
    rows = []
    for corr in corrs:
        for sig in sigmas:
            for r in range(reps):
                row = evaluate(g, Sc, Ss, cav, sol, u_e, th, seg, field(Sc.shape, g, sig, corr),
                               field(Sc.shape, g, sig, corr))
                row.update(kind="random", sigma_mm=sig, corr_mm=corr, rep=r)
                rows.append(row)
                print("B", corr, sig, r, round(row["dice_third"][0], 3), round(row["endo_mean_abs_d_mm"], 3),
                      round(row["seg_thick_abs_err_mm"], 3), flush=True)
    for border, b in biases:
        z = np.zeros(Sc.shape, np.float32)
        nc = z + (b if border == "endo" else 0)  # positive b shrinks the cavity: endocardium moves inward
        ns = z + (b if border == "epi" else 0)  # positive b shrinks the solid: epicardium moves inward
        row = evaluate(g, Sc, Ss, cav, sol, u_e, th, seg, nc, ns)
        row.update(kind="bias", border=border, bias_mm=b)
        rows.append(row)
        print("B bias", border, b, round(row["dice_third"][0], 3), round(row["seg_thick_abs_err_mm"], 3),
              row["kim_bin_flip"], flush=True)
    return {"grid_mm": g, "depth": depth, "rows": rows}


def main(out, quick=False):
    reps = 1 if quick else 3
    res = {"seed": 20261030,
           "phantom": "truncated prolate ellipsoids, outer 34x34x60 mm, cavity 24x24x52 mm shifted 4 mm; base at z=66",
           "A": part_a(reps, [0.25, 0.5, 1.0]),
           "B": part_b(reps, [0.1, 0.25, 0.5, 0.75, 1.0], [4.0, 8.0, 16.0] if not quick else [8.0],
                       [("endo", 0.25), ("endo", -0.25), ("endo", 0.5), ("endo", -0.5),
                        ("epi", 0.5), ("epi", -0.5), ("epi", -0.86)])}
    with open(out, "w") as fh:
        json.dump(res, fh, indent=1)


if __name__ == "__main__":
    main(sys.argv[1], "--quick" in sys.argv)
