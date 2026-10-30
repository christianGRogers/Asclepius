"""Left-ventricular wall geometry from a myocardium + LV-cavity mask: transmural depth, layers, AHA segments.

Everything here is derived from two borders (endocardium, epicardium) plus landmarks (mitral plane, apex,
RV insertion points). That is India's claim for the Janus-M schema: a model segments the myocardium and the
cavity; layers and segments are computed, not learned as classes. The experiments (`exp_*.py`) test how
well that holds and how border errors propagate.

Conventions
- Arrays are indexed in the NIfTI voxel order, with the RAS affine kept, so "anterior" is +A in world space.
- Transmural depth t in [0, 1]: 0 at the endocardium, 1 at the epicardium. Layers are thirds of t:
  1 subendocardial, 2 mid-wall, 3 subepicardial.
- AHA 17 segments (Cerqueira et al. 2002): 1-6 basal, 7-12 mid, 13-16 apical, 17 apex.
"""
from __future__ import annotations

import numpy as np
import nibabel as nib
from scipy import ndimage as ndi
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import cg

STRUCT = ndi.generate_binary_structure(3, 1)  # 6-connectivity

MASKS = dict(myo="heart_myocardium", lv="heart_ventricle_left", rv="heart_ventricle_right",
             la="heart_atrium_left", ao="aorta")


def load_subject(d, margin_mm=12.0):
    """Load CT + masks of one TotalSegmentator subject folder, cropped to the LV (cavity + myocardium)."""
    ct = nib.load(f"{d}/ct.nii.gz")
    sp = np.array(ct.header.get_zooms()[:3], float)
    m = {k: np.asanyarray(nib.load(f"{d}/segmentations/{v}.nii.gz").dataobj) > 0 for k, v in MASKS.items()}
    lvs = m["myo"] | m["lv"]
    if lvs.sum() == 0:
        return None
    idx = np.argwhere(lvs)
    mg = np.ceil(margin_mm / sp).astype(int)
    lo = np.maximum(idx.min(0) - mg, 0)
    hi = np.minimum(idx.max(0) + mg + 1, lvs.shape)
    sl = tuple(slice(a, b) for a, b in zip(lo, hi))
    aff = ct.affine.copy()
    aff[:3, 3] = aff[:3, :3] @ lo + aff[:3, 3]
    out = dict(ct=np.asanyarray(ct.dataobj)[sl].astype(np.float32), spacing=sp, affine=aff,
               touches_edge=bool((lo == 0).any() or (hi == np.array(lvs.shape)).any()))
    for k in m:
        out[k] = m[k][sl]
    return out


def resample_masks(sub, target=0.5):
    """Resample the masks to an isotropic `target` mm grid by trilinear interpolation of each mask
    (threshold 0.5), resolving overlaps in the order cavity > myocardium > others."""
    f = sub["spacing"] / target
    out = dict(spacing=np.array([target] * 3), affine=sub["affine"].copy())
    out["affine"][:3, :3] = sub["affine"][:3, :3] / f
    for k in ("lv", "myo", "rv", "la", "ao"):
        out[k] = ndi.zoom(sub[k].astype(np.float32), f, order=1) > 0.5
    out["myo"] &= ~out["lv"]
    for k in ("rv", "la", "ao"):
        out[k] &= ~(out["lv"] | out["myo"])
    out["ct"] = ndi.zoom(sub["ct"], f, order=1)
    return out


def keep_largest(m):
    lab, n = ndi.label(m)
    if n <= 1:
        return m
    sizes = ndi.sum(m, lab, range(1, n + 1))
    return lab == (1 + int(np.argmax(sizes)))


# ----------------------------------------------------------------------------------------------- depth

def boundaries(myo, lv):
    """Endocardial and epicardial boundary shells (non-myocardium voxels touching the myocardium).
    Endo = LV cavity voxels touching myocardium; epi = every other non-myocardium voxel touching it,
    except those in the mitral/aortic opening (cavity side), which are not boundaries of the wall."""
    ring = ndi.binary_dilation(myo, STRUCT) & ~myo
    endo = ring & lv
    epi = ring & ~lv
    return endo, epi


def depth_distance(myo, lv, spacing):
    """t = d_endo / (d_endo + d_epi), with Euclidean distances (mm) to the two boundary shells.
    Also returns the local thickness proxy d_endo + d_epi (mm)."""
    endo, epi = boundaries(myo, lv)
    de = ndi.distance_transform_edt(~endo, sampling=spacing)
    dp = ndi.distance_transform_edt(~epi, sampling=spacing)
    t = np.zeros(myo.shape, np.float32)
    s = de + dp
    t[myo] = (de[myo] / np.maximum(s[myo], 1e-6)).astype(np.float32)
    thick = np.zeros(myo.shape, np.float32)
    thick[myo] = s[myo] - spacing.mean()  # shells sit half a voxel outside the wall on each side
    return t, thick


def depth_laplace(myo, lv, tol=1e-6, maxiter=4000):
    """Solve Laplace's equation in the wall with u=0 on the endocardial shell and u=1 on the epicardial
    shell (Jones et al. 2000 for cortex; the standard transmural coordinate in cardiac models)."""
    endo, epi = boundaries(myo, lv)
    idx = -np.ones(myo.shape, np.int64)
    pts = np.argwhere(myo)
    idx[tuple(pts.T)] = np.arange(len(pts))
    n = len(pts)
    rows, cols, vals = [], [], []
    diag = np.zeros(n)
    b = np.zeros(n)
    for ax in range(3):
        for sgn in (-1, 1):
            nb = pts.copy()
            nb[:, ax] += sgn
            ok = (nb[:, ax] >= 0) & (nb[:, ax] < myo.shape[ax])
            i = np.nonzero(ok)[0]
            nbt = tuple(nb[i].T)
            j = idx[nbt]
            inside = j >= 0
            # interior neighbour
            rows.append(i[inside]); cols.append(j[inside]); vals.append(-np.ones(inside.sum()))
            diag[i[inside]] += 1
            # Dirichlet neighbours
            e = endo[nbt] & ~inside
            p = epi[nbt] & ~inside
            diag[i[e]] += 1
            diag[i[p]] += 1
            b[i[p]] += 1.0
    rows.append(np.arange(n)); cols.append(np.arange(n)); vals.append(diag)
    A = coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr()
    dg = np.maximum(diag, 1e-9)
    from scipy.sparse.linalg import LinearOperator
    M = LinearOperator((n, n), matvec=lambda x: x / dg)
    u, info = cg(A, b, rtol=tol, maxiter=maxiter, M=M)
    t = np.zeros(myo.shape, np.float32)
    t[tuple(pts.T)] = np.clip(u, 0, 1)
    return t


def layers(t, myo, k=3):
    """Transmural layers 1..k (1 = subendocardial) from depth t."""
    L = np.zeros(myo.shape, np.uint8)
    L[myo] = np.minimum((t[myo] * k).astype(int), k - 1) + 1
    return L


# ----------------------------------------------------------------------------------------------- AHA

def world(points, affine):
    return points @ affine[:3, :3].T + affine[:3, 3]


def lv_frame(g):
    """Long axis from the mitral-plane centroid (LV cavity voxels touching the LA) to the farthest
    epicardial myocardium point (apex); anterior RV insertion point from the RV-contact arc of the septum.
    Returns dict(base, apex, axis, ref, sign, septal_arc_deg) in world mm."""
    myo, lv, rv, la, aff = g["myo"], g["lv"], g["rv"], g["la"], g["affine"]
    mv = lv & ndi.binary_dilation(la, STRUCT, iterations=2)
    if mv.sum() < 10:
        return None
    base = world(np.argwhere(mv), aff).mean(0)
    mp = world(np.argwhere(myo), aff)
    apex = mp[np.argmax(np.linalg.norm(mp - base, axis=1))]
    axis = (apex - base) / np.linalg.norm(apex - base)
    # RV contact of the myocardium (the septal arc)
    sc = myo & ndi.binary_dilation(rv, STRUCT, iterations=2)
    if sc.sum() < 10:
        return None
    sp = world(np.argwhere(sc), aff)
    # restrict to the mid-ventricle (middle third of the base-apex length) to get the arc
    L = np.linalg.norm(apex - base)
    s = (sp - base) @ axis
    sp = sp[(s > 0.25 * L) & (s < 0.65 * L)]
    if len(sp) < 10:
        return None
    # orthonormal basis in the short-axis plane; e1 = toward patient anterior (+A) projected
    a = np.array([0.0, 1.0, 0.0])
    e1 = a - (a @ axis) * axis
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(axis, e1)
    ang = np.degrees(np.arctan2((sp - base) @ e2, (sp - base) @ e1)) % 360
    # circular arc covering the septal-contact angles: largest gap complement
    h = np.sort(ang)
    gaps = np.diff(np.concatenate([h, h[:1] + 360]))
    gi = int(np.argmax(gaps))
    start = h[(gi + 1) % len(h)]  # arc runs from start (ccw) to end
    end = h[gi]
    arc = (end - start) % 360
    # which end is anterior? the one whose direction has the larger anterior (+A) world component
    def dirv(deg):
        r = np.radians(deg)
        return np.cos(r) * e1 + np.sin(r) * e2
    if dirv(start)[1] >= dirv(end)[1]:
        ref, sign = start, +1   # going +angle from the anterior insertion enters the septum
    else:
        ref, sign = end, -1
    return dict(base=base, apex=apex, axis=axis, e1=e1, e2=e2, ref=ref, sign=sign, septal_arc_deg=arc)


def aha17(g, fr, axis_tilt=None, ref_shift_deg=0.0, base_shift_mm=0.0):
    """AHA 17-segment label per myocardium voxel. Optional perturbations of the frame: tilt the long axis by
    a rotation (3x3 matrix), rotate the RV-insertion reference by ref_shift_deg, move the base plane."""
    myo, lv, aff = g["myo"], g["lv"], g["affine"]
    axis, e1 = fr["axis"], fr["e1"]
    if axis_tilt is not None:
        axis = axis_tilt @ axis
        e1 = axis_tilt @ e1
    e2 = np.cross(axis, e1)
    base = fr["base"] + base_shift_mm * axis
    P = np.argwhere(myo)
    w = world(P, aff) - base
    s = w @ axis
    cav = world(np.argwhere(lv), aff) - base
    s_cav = (cav @ axis).max()        # cavity tip: beyond it is the apical cap (segment 17)
    ang = np.degrees(np.arctan2(w @ e2, w @ e1)) % 360
    phi = (fr["sign"] * (ang - fr["ref"] - ref_shift_deg)) % 360   # 0 at anterior insertion, + into septum
    seg = np.zeros(len(P), np.uint8)
    level = np.clip((s / max(s_cav, 1e-6) * 3).astype(int), 0, 2)   # 0 basal, 1 mid, 2 apical
    # basal/mid: from anterior insertion into septum: anteroseptal, inferoseptal, inferior, inferolateral,
    # anterolateral, anterior (AHA numbers 2,3,4,5,6,1 / 8,9,10,11,12,7)
    six = np.array([2, 3, 4, 5, 6, 1])
    k6 = (phi // 60).astype(int) % 6
    seg[level == 0] = six[k6[level == 0]]
    seg[level == 1] = six[k6[level == 1]] + 6
    # apical: septal 14 centred on mid-septum (phi 60), inferior 15, lateral 16, anterior 13
    four = np.array([14, 15, 16, 13])
    k4 = (((phi - 15) % 360) // 90).astype(int) % 4
    seg[level == 2] = four[k4[level == 2]]
    seg[s > s_cav] = 17
    seg[s < 0] = 0   # above the mitral plane centroid: not part of the 17 (basal ring overshoot)
    out = np.zeros(myo.shape, np.uint8)
    out[tuple(P.T)] = seg
    return out


# Default coronary territory of each AHA segment (Cerqueira et al. 2002, Fig. 4)
AHA_TERRITORY = {**{s: "LAD" for s in (1, 2, 7, 8, 13, 14, 17)},
                 **{s: "RCA" for s in (3, 4, 9, 10, 15)},
                 **{s: "LCx" for s in (5, 6, 11, 12, 16)}}


def rotation(axis, deg):
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    th = np.radians(deg)
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(th) * K + (1 - np.cos(th)) * K @ K


# ----------------------------------------------------------------------------------------------- perturb

def smooth_noise(shape, spacing, sigma_mm, corr_mm, rng):
    """Zero-mean Gaussian random field, std sigma_mm, correlation length corr_mm."""
    f = 4  # draw on a 4x coarser grid, smooth, then upsample: same field statistics, ~60x faster
    cs = tuple(int(np.ceil(s / f)) for s in shape)
    n = rng.standard_normal(cs).astype(np.float32)
    n = ndi.gaussian_filter(n, corr_mm / (spacing * f))
    n = ndi.zoom(n, [s / c for s, c in zip(shape, cs)], order=1)[:shape[0], :shape[1], :shape[2]]
    n *= sigma_mm / max(n.std(), 1e-9)
    return n


def perturb_borders(myo, lv, spacing, sigma_mm, corr_mm, rng, bias_endo=0.0, bias_epi=0.0):
    """Move the endocardial and epicardial surfaces independently by a smooth random normal displacement
    (std sigma_mm) plus an optional bias (mm, positive = outward). Returns (myo', lv')."""
    solid = myo | lv
    h = 0.5 * float(np.mean(spacing))
    def sdf(m):
        # signed distance with the surface half-way between voxel centres: -h/2 inside, +h/2 outside at the
        # boundary, so a displacement of d mm moves the surface by about d mm on the grid
        return np.where(m, h / 2 - ndi.distance_transform_edt(m, sampling=spacing),
                        ndi.distance_transform_edt(~m, sampling=spacing) - h / 2)
    sc, ss = sdf(lv), sdf(solid)
    nc = smooth_noise(myo.shape, spacing, sigma_mm, corr_mm, rng) if sigma_mm > 0 else 0
    ns = smooth_noise(myo.shape, spacing, sigma_mm, corr_mm, rng) if sigma_mm > 0 else 0
    lv2 = (sc - nc - bias_endo) < 0
    solid2 = (ss - ns - bias_epi) < 0
    lv2 &= solid2
    myo2 = solid2 & ~lv2
    return myo2, lv2


def dice(a, b):
    s = a.sum() + b.sum()
    return 2.0 * (a & b).sum() / s if s else np.nan
