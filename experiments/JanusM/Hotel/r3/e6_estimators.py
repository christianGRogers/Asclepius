"""Hotel R3 E6: validate the JA15 measurement implementations against a known truth (Round 2 ruling §7 item 2).

Question: which ASSD, signed-bias and thickness implementations can be the geometry module's single shared fixture
(JA15), and does any signed-bias estimator recover a known +-0.5 mm shift to within +-0.05 mm in each direction,
which decides JA16's 0.3 mm vs 0.5 mm guard?

Synthetic only: no case is opened, so no guard call is needed; the phantom is analytic.

Truth. The LV phantom (Hotel R2 E2) is given by continuous signed distances F_endo, F_solid (Sampson distance to
two truncated ellipsoids), optionally roughened by a smooth 3 mm field (so the walls are not ideal quadrics), and
rotated by a random rotation (so the walls are oblique to the grid). A border is perturbed by
    mask = F - s(x) < 0
where s is a constant shift (+ = the region grows: cavity into the wall, or solid into the fat) or a JA15 random
field (8 mm Gaussian-smoothed). The true normal displacement at a reference-surface point is s(x) / |grad F|, so
the true signed bias is its mean over the reference surface and the true ASSD is close to its mean absolute value
(exact for a constant shift; first-order for a smooth field). The base rim (within 6 mm of the cut plane) is
excluded from surfaces and truth alike, because the cut plane is a valve plane, not a border.

Estimators of the signed bias of mask A (perturbed) relative to B (reference), + = A larger:
  india   India R2 harness_r2.border_stats (imported unchanged)
  lima    Lima R2 harness.assd_and_bias (imported unchanged)
  sym     Hotel: 1/2 [ mean SDF_B over A's inner-surface voxels - mean SDF_A over B's inner-surface voxels ],
          with half-voxel-corrected SDFs. The half-voxel offset of each one-sided term cancels, and so does the
          oblique-surface error, because it enters both terms with the same sign.
ASSD estimators:
  voxel   segtrain.metrics.surface_distances (what janusm_reads.anchoring.assd ships), surface-voxel to
          surface-voxel distances
  sdf     Hotel: mean of |SDF_B + h/2| over A's inner-surface voxels and |SDF_A + h/2| over B's, pooled
Thickness: janusm.geometry.depth (equal thickness) on the label map, median over 16 pseudo-segments of each
segment's median thickness; the true change for an endocardial shift s is -s.

    python experiments/JanusM/Hotel/r3/e6_estimators.py OUT.json [--quick]
"""
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments/JanusM/India"))
sys.path.insert(0, str(ROOT / "experiments/JanusM/Lima"))
import harness as lima  # noqa: E402
import harness_r2 as india  # noqa: E402
from janusm import geometry as G  # noqa: E402
from segtrain.metrics import _surface, surface_distances  # noqa: E402

BOX = np.array([84.0, 84.0, 76.0])
FACE = ndi.generate_binary_structure(3, 1)


# ------------------------------------------------------------------ phantom ------------------------------------
def phantom(sp, rot_seed, rough):
    """Continuous SDFs (mm, + outside) of cavity and solid on a grid of spacing sp, plus base-rim ROI mask."""
    sp = np.asarray(sp, float)
    n = np.ceil(BOX / sp).astype(int)
    X = [(np.arange(k) + 0.5) * s - b / 2 for k, s, b in zip(n, sp, BOX)]
    x, y, z = np.meshgrid(*X, indexing="ij")
    P = np.stack([x, y, z], -1).reshape(-1, 3)
    R = Rotation.random(random_state=rot_seed).as_matrix() if rot_seed is not None else np.eye(3)
    Q = P @ R  # body coordinates
    qx, qy, qz = Q[:, 0], Q[:, 1], Q[:, 2]
    zz = 30.0 - qz  # base plane at body z = 30 mm; apex toward -z

    def ell(x0, a, c):
        q = ((qx - x0) / a) ** 2 + (qy / a) ** 2 + (zz / c) ** 2
        g = 2 * np.sqrt(((qx - x0) / a ** 2) ** 2 + (qy / a ** 2) ** 2 + (zz / c ** 2) ** 2)
        return (q - 1) / np.maximum(g, 1e-9)

    Fs = ell(0.0, 32.0, 56.0).reshape(n)
    Fc = ell(4.0, 22.0, 48.0).reshape(n)
    if rough:
        rng = np.random.default_rng(1000 + (rot_seed or 0))
        for F in (Fs, Fc):
            f = ndi.gaussian_filter(rng.standard_normal(n), 3.0 / sp)
            F += (0.6 * f / f.std()).astype(F.dtype)  # 0.6 mm SD bumps, 3 mm correlation
    base = (-zz).reshape(n)
    roi = base < -6.0  # more than 6 mm below the base plane
    return Fc.astype(np.float32), Fs.astype(np.float32), base.astype(np.float32), roi


def gradmag(F, sp):
    g = np.gradient(F, *sp)
    return np.sqrt(sum(x * x for x in g))


def field(shape, sp, sigma, corr, rng):
    f = ndi.gaussian_filter(rng.standard_normal(shape).astype(np.float32), corr / np.asarray(sp))
    return (f * (sigma / f.std())).astype(np.float32)


# ------------------------------------------------------------------ estimators ---------------------------------
def inner(m):
    return m & ~ndi.binary_erosion(m, FACE, border_value=1)


def sdfc(m, sp):
    h = float(np.mean(sp)) / 2
    return np.where(m, h - ndi.distance_transform_edt(m, sampling=sp),
                    ndi.distance_transform_edt(~m, sampling=sp) - h).astype(np.float32)


def est_sym(A, B, sp, roi):
    sA, sB = inner(A) & roi, inner(B) & roi
    SA, SB = sdfc(A, sp), sdfc(B, sp)
    h = float(np.mean(sp)) / 2
    bias = 0.5 * (float(SB[sA].mean()) - float(SA[sB].mean()))
    assd = float((np.abs(SB[sA] + h).sum() + np.abs(SA[sB] + h).sum()) / (sA.sum() + sB.sum()))
    return bias, assd


def surface_points(m, sp, roi, sigma_vox=0.7):
    """Sub-voxel surface of a binary mask: zero crossings of phi = G_sigma * m - 0.5 along each grid axis,
    linearly interpolated; outward unit normal from grad phi; each crossing kept only on its dominant axis and
    weighted by the area it stands for (product of the other two spacings / |n_axis|)."""
    sp = np.asarray(sp, float)
    phi = ndi.gaussian_filter(m.astype(np.float32), sigma_vox) - 0.5
    gr = np.gradient(phi, *sp)
    P, N, W = [], [], []
    for a in range(3):
        sl0 = [slice(None)] * 3
        sl1 = [slice(None)] * 3
        sl0[a], sl1[a] = slice(0, -1), slice(1, None)
        p0, p1 = phi[tuple(sl0)], phi[tuple(sl1)]
        cross = (p0 > 0) != (p1 > 0)
        cross &= roi[tuple(sl0)]
        idx = np.argwhere(cross)
        v0, v1 = p0[cross], p1[cross]
        t = v0 / (v0 - v1)
        g0 = np.stack([g[tuple(sl0)][cross] for g in gr], 1)
        g1 = np.stack([g[tuple(sl1)][cross] for g in gr], 1)
        g = g0 + t[:, None] * (g1 - g0)
        n = -g / np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-9)  # outward (phi > 0 inside)
        dom = np.argmax(np.abs(n), 1) == a
        pos = (idx + 0.5).astype(float)
        pos[:, a] += t
        pos = pos * sp
        o = [k for k in range(3) if k != a]
        P.append(pos[dom])
        N.append(n[dom])
        W.append(sp[o[0]] * sp[o[1]] / np.abs(n[dom, a]))
    return np.concatenate(P), np.concatenate(N), np.concatenate(W)


def est_pp(A, B, sp, roi):
    """Point-to-plane, symmetric: bias (+ = A larger) and ASSD, on sub-voxel surfaces."""
    from scipy.spatial import cKDTree
    pa, na, wa = surface_points(A, sp, roi)
    pb, nb, wb = surface_points(B, sp, roi)
    _, ib = cKDTree(pb).query(pa)
    dab = np.einsum("ij,ij->i", pa - pb[ib], nb[ib])  # + : A's surface outside B
    _, ia = cKDTree(pa).query(pb)
    dba = np.einsum("ij,ij->i", pb - pa[ia], na[ia])  # + : B's surface outside A
    bias = 0.5 * (np.average(dab, weights=wa) - np.average(dba, weights=wb))
    assd = float((np.sum(wa * np.abs(dab)) + np.sum(wb * np.abs(dba))) / (wa.sum() + wb.sum()))
    return float(bias), assd


def est_vol(A, B, sp, roi):
    """Volume over area: (|A| - |B|) / mean area, both inside the ROI; area = integral of |grad (G * mask)|."""
    sp = np.asarray(sp, float)
    vv = float(np.prod(sp))

    def area(m):
        g = np.gradient(ndi.gaussian_filter(m.astype(np.float32), 0.7), *sp)
        return float(np.sqrt(sum(x * x for x in g))[roi].sum() * vv)

    dv = (float((A & roi).sum()) - float((B & roi).sum())) * vv
    return dv / (0.5 * (area(A) + area(B)))


def est_voxel_assd(A, B, sp, roi):
    # segtrain.metrics on the ROI-cropped masks: the base plane is cut away by masking both masks to the ROI
    # band, and only surface voxels inside the ROI are kept, as surface_distances returns all of them
    dab, dba = surface_distances(A, B, sp)
    keepA, keepB = roi[_surface(A)], roi[_surface(B)]  # the same surface voxels segtrain uses, in order
    return float((dab[keepA].sum() + dba[keepB].sum()) / (keepA.sum() + keepB.sum()))


def est_india(A, B, sp, roi):
    # border_stats(cav_r, solid_r, cav_p, solid_p, myo_r, sp): call with the same mask as cavity and solid
    # pair, and read the matching entry. It restricts to a band around myo_r; give it the ROI band of B.
    myo = ndi.binary_dilation(inner(B), FACE, iterations=2) & roi
    out = india.border_stats(B, B, A, A, myo, np.asarray(sp, float))
    return out["endo"]["bias"] if out["endo"] else float("nan")


def est_lima(A, B, sp, roi):
    ref = lima.sdf(B, np.asarray(sp, float), "corrected")
    sa = lima.surface(A) & roi  # Lima's surface voxels, restricted to the ROI band
    h = float(np.mean(sp)) / 2
    return float(np.mean(ref[sa]) + h)


# ------------------------------------------------------------------ one condition ------------------------------
def truth(F, s, sp, roi):
    band = (np.abs(F) < 0.5 * float(np.min(sp))) & roi
    gm = gradmag(F, sp)[band]
    d = (s[band] if np.ndim(s) else np.full(gm.shape, s)) / np.maximum(gm, 1e-6)
    return float(d.mean()), float(np.abs(d).mean())


def thickness_median(cav, sol, sp, roi, seg):
    lab = np.zeros(cav.shape, np.uint8)
    lab[sol & ~cav] = G.MYO
    lab[cav] = G.LV
    d = G.depth(lab, spacing=sp)
    th = d.thickness
    vals = []
    for k in range(16):
        m = (seg == k) & roi & (lab == G.MYO)
        if m.sum() > 50:
            vals.append(float(np.nanmedian(th[m])))
    return np.array(vals)


def run(cfg):
    sp, rot, rough, kind, border, amt, rep = (cfg[k] for k in ("sp", "rot", "rough", "kind", "border", "amt", "rep"))
    sp = np.asarray(sp, float)
    Fc, Fs, base, roi = phantom(sp, rot, rough)
    Fb = Fc if border == "endo" else Fs
    if kind == "shift":
        s = np.float32(amt)
        S = np.full(Fb.shape, s, np.float32)
    else:
        S = field(Fb.shape, sp, amt, 8.0, np.random.default_rng(7000 + rep + 100 * (rot or 0)))
    # truth uses the region's own SDF; the cut plane is applied as an intersection with base < 0
    B = (Fb < 0) & (base < 0)
    A = ((Fb - S) < 0) & (base < 0)
    tb, ta = truth(Fb, S, sp, roi)
    r = {**{k: cfg[k] for k in ("rot", "rough", "kind", "border", "amt", "rep")}, "sp": list(map(float, sp)),
         "true_bias": tb, "true_assd": ta}
    r["sym_bias"], r["sdf_assd"] = est_sym(A, B, sp, roi)
    r["india_bias"] = est_india(A, B, sp, roi)
    r["lima_bias"] = est_lima(A, B, sp, roi)
    r["voxel_assd"] = est_voxel_assd(A, B, sp, roi)
    r["pp_bias"], r["pp_assd"] = est_pp(A, B, sp, roi)
    r["vol_bias"] = est_vol(A, B, sp, roi)
    if kind == "shift" and border == "endo" and abs(amt) in (0.25, 0.5):
        # thickness: median over pseudo-segments, perturbed minus reference (true: -amt for the endocardium)
        sol = (Fs < 0) & (base < 0)
        n = Fb.shape
        X = [(np.arange(k) + 0.5) * s_ - b / 2 for k, s_, b in zip(n, sp, BOX)]
        x, y, z = np.meshgrid(*X, indexing="ij")
        Rm = Rotation.random(random_state=rot).as_matrix() if rot is not None else np.eye(3)
        Q = np.stack([x, y, z], -1) @ Rm
        ang = (np.degrees(np.arctan2(Q[..., 1], Q[..., 0])) + 360) % 360
        lev = np.digitize(30.0 - Q[..., 2], [16.0, 34.0])
        seg = ((ang // 90).astype(int) * 4 + lev).astype(np.int16)  # 4 sectors x up to 4 levels
        t0 = thickness_median(B & sol, sol, sp, roi, seg)
        t1 = thickness_median(A & sol, sol, sp, roi, seg)
        if len(t0) == len(t1) and len(t0):
            r["thick_change_median_mm"] = float(np.median(t1 - t0))
    return r


def main(out, quick=False):
    t0 = time.time()
    grids = [(0.5, 0.5, 0.5), (0.4, 0.4, 0.5)]
    rots = [None, 11, 23] if not quick else [11]
    shifts = [-1.0, -0.5, -0.3, -0.25, -0.1, 0.1, 0.25, 0.3, 0.5, 1.0] if not quick else [-0.5, 0.5]
    cfgs = []
    for sp in grids if not quick else grids[:1]:
        for rot in rots:
            for rough in (False, True):
                for border in ("endo", "epi"):
                    for a in shifts:
                        cfgs.append(dict(sp=sp, rot=rot, rough=rough, kind="shift", border=border, amt=a, rep=0))
                    for sig in ((0.25, 0.5) if not quick else (0.5,)):
                        for rep in range(2 if not quick else 1):
                            cfgs.append(dict(sp=sp, rot=rot, rough=rough, kind="field", border=border, amt=sig,
                                             rep=rep))
    with Pool(3) as p:
        rows = p.map(run, cfgs, chunksize=1)
    res = {"n": len(rows), "seconds": round(time.time() - t0), "rows": rows}
    Path(out).write_text(json.dumps(res, indent=1) + "\n")
    print("done", len(rows), res["seconds"], "s")


if __name__ == "__main__":
    main(sys.argv[1], "--quick" in sys.argv)
