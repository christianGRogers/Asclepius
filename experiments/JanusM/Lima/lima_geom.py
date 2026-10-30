"""Lima's geometry read-out for one heart (Janus-M R2, path jm/rest-ccta).

One function, `analyse`, takes four border masks (JA1: LV myocardium, LV blood pool, RV blood pool, LA blood
pool), the CT, and optionally Janus's four coronary classes, all on one isotropic grid. It returns numbers only:

- **item 1** wall thickness, voxels per third, segments that need halves (JA2), AHA orientation checks (JA3);
- **item 1, Hotel's question** the mask border's offset from the image half-maximum, per border (JA7's rule);
- **item 3** equal-thickness vs Laplace vs Yezzi-Prince depth (thirds agreement); fixed 60/90-degree sectors from
  the anterior RV insertion vs arc-proportional septal sectors; Euclidean vs geodesic territories;
- **item 6** rest TPR per segment with and without Juliet's 1 mm guard band; core-sample HU quantiles and fat
  clusters at candidate cut-offs;
- **item 9 (Lima E3)** the calibration inputs: each segment's thickness relative to the patient's own median, and
  the guarded subendocardial HU relative to the patient's own median.

Run on Fir by `fir/jm0b_readout.py` (ImageCAS-X JM-0 cases) and locally by `local_check.py` (public
TotalSegmentator cases after the guard).
"""
from collections import Counter

import numpy as np
from scipy import ndimage as ndi
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra
from scipy.sparse.linalg import cg
from scipy.spatial import cKDTree

FACE = ndi.generate_binary_structure(3, 1)
AHA_DEFAULT = {**{k: "LAD" for k in (1, 2, 7, 8, 13, 14, 17)}, **{k: "RCA" for k in (3, 4, 9, 10, 15)},
               **{k: "LCx" for k in (5, 6, 11, 12, 16)}}
VESSEL = {2: "LAD", 3: "LCx", 4: "RCA"}


# ------------------------------------------------------------------ resampling
def sdf(m, sp):
    """Signed distance, mm, negative inside, half-voxel corrected (slope 1 across the border)."""
    m = m.astype(bool)
    h = float(np.mean(sp)) / 2
    return np.where(m, h - ndi.distance_transform_edt(m, sampling=sp),
                    ndi.distance_transform_edt(~m, sampling=sp) - h).astype(np.float32)


def to_grid(masks, ct, cor, sp0, aff0, grid=0.5, margin_mm=15.0):
    """Crop to the heart and resample to `grid` mm isotropic: masks through signed distances, CT linearly,
    coronary classes by nearest neighbour. Returns dict of arrays, spacing, affine."""
    box = masks["myo"] | masks["lv"]
    m = np.ceil(margin_mm / sp0).astype(int)
    lo = np.maximum(np.argwhere(box).min(0) - m, 0)
    hi = np.minimum(np.argwhere(box).max(0) + m + 1, box.shape)
    sl = tuple(slice(a, b) for a, b in zip(lo, hi))
    f = sp0 / grid
    out = {k: ndi.zoom(sdf(v[sl], sp0), f, order=1) < 0 for k, v in masks.items()}
    out["ct"] = ndi.zoom(ct[sl].astype(np.float32), f, order=1)
    if cor is not None:
        out["cor"] = ndi.zoom(cor[sl].astype(np.uint8), f, order=0)
    shape = min((v.shape for v in out.values()), key=lambda s: np.prod(s))
    out = {k: v[:shape[0], :shape[1], :shape[2]] for k, v in out.items()}
    sol = out["myo"] | out["lv"]
    out["lv"] = out["lv"] & sol
    out["myo"] = sol & ~out["lv"]
    for k in ("rv", "la"):
        out[k] = out[k] & ~sol
    aff = aff0.copy()
    aff[:3, 3] = aff0[:3, :3] @ lo + aff0[:3, 3]
    aff[:3, :3] = aff0[:3, :3] / f
    return out, np.full(3, grid), aff


# ------------------------------------------------------------------ depth
def et_depth(myo, lv, sp):
    """JA2 equal-thickness depth u = d_endo / (d_endo + d_epi), voxel-centre corrected; thickness (mm)."""
    s = float(np.mean(sp))
    de = ndi.distance_transform_edt(~lv, sampling=sp)
    dp = ndi.distance_transform_edt(myo | lv, sampling=sp)
    th = de + dp - s
    u = np.clip((de - s / 2) / np.maximum(th, 1e-6), 0, 1)
    return np.where(myo, u, np.nan).astype(np.float32), np.where(myo, th, np.nan).astype(np.float32), de, dp


def laplace(myo, lv, noflux, tol=1e-6, maxiter=3000):
    """Laplace potential on the wall: 0 at the endocardium, 1 at the epicardium, no-flux at the base (LA, aorta)."""
    pts = np.argwhere(myo)
    n = len(pts)
    idx = -np.ones(myo.shape, np.int64)
    idx[tuple(pts.T)] = np.arange(n)
    rows, cols, diag, rhs = [], [], np.zeros(n), np.zeros(n)
    shp = np.array(myo.shape)
    for ax in range(3):
        for s in (-1, 1):
            nb = pts.copy()
            nb[:, ax] += s
            ok = (nb[:, ax] >= 0) & (nb[:, ax] < shp[ax])
            j = np.full(n, -1, np.int64)
            j[ok] = idx[tuple(nb[ok].T)]
            ins = j >= 0
            rows.append(np.nonzero(ins)[0]); cols.append(j[ins]); diag[ins] += 1
            is_lv = np.zeros(n, bool); is_lv[ok] = lv[tuple(nb[ok].T)]
            is_nf = np.zeros(n, bool); is_nf[ok] = noflux[tuple(nb[ok].T)]
            endo = ~ins & is_lv
            epi = ~ins & ~is_lv & ~is_nf
            diag[endo] += 1
            diag[epi] += 1
            rhs[epi] += 1
    A = coo_matrix((np.concatenate([-np.ones(len(np.concatenate(rows))), diag]),
                    (np.concatenate(rows + [np.arange(n)]), np.concatenate(cols + [np.arange(n)]))),
                   shape=(n, n)).tocsr()
    x, _ = cg(A, rhs, x0=np.full(n, 0.5), rtol=tol, maxiter=maxiter)
    phi = np.full(myo.shape, np.nan, np.float32)
    phi[tuple(pts.T)] = np.clip(x, 0, 1)
    return phi


def yezzi_prince(phi, myo, lv, sp, iters=400, tol=1e-3):
    """Yezzi & Prince (2003) thickness: L0 (from the endocardium) and L1 (from the epicardium) solve
    T . grad L = 1 along the Laplace tangent field T, by upwind Jacobi sweeps. Depth = L0 / (L0 + L1)."""
    f = np.where(myo, phi, np.where(lv, 0.0, 1.0)).astype(np.float32)
    g = np.stack(np.gradient(f, *sp))
    nrm = np.sqrt((g ** 2).sum(0)) + 1e-9
    T = g / nrm
    pts = np.argwhere(myo)
    Tp = T[(slice(None),) + tuple(pts.T)].T  # n x 3
    shp = np.array(myo.shape)
    idx = -np.ones(myo.shape, np.int64)
    idx[tuple(pts.T)] = np.arange(len(pts))

    half = float(np.mean(sp)) / 2  # the border lies half a voxel beyond a boundary neighbour's centre

    def solve(sign, zero_mask):
        """L along the field sign*T, zero at zero_mask's border; the upwind neighbour lies behind, -sign(T)."""
        Ts = sign * Tp
        w = np.abs(Ts) / sp  # per axis
        nb_idx, nb_zero = [], []
        for ax in range(3):
            step = -np.sign(Ts[:, ax]).astype(int)  # upwind neighbour
            nb = pts.copy()
            nb[:, ax] += step
            nb[:, ax] = np.clip(nb[:, ax], 0, shp[ax] - 1)
            nb_idx.append(idx[tuple(nb.T)])
            nb_zero.append(zero_mask[tuple(nb.T)])
        L = np.zeros(len(pts), np.float32)
        den = w.sum(1) + 1e-9
        for _ in range(iters):
            acc = np.ones(len(pts), np.float32)
            for ax in range(3):
                j = nb_idx[ax]
                v = np.where(j >= 0, L[np.maximum(j, 0)], np.where(nb_zero[ax], -half, L))
                acc += w[:, ax] * v
            Ln = acc / den
            if np.max(np.abs(Ln - L)) < tol:
                L = Ln
                break
            L = Ln
        return L

    L0 = solve(+1.0, lv)            # length from the endocardium, marching with T (endo -> epi)
    L1 = solve(-1.0, ~(myo | lv))   # length from the epicardium, marching against T
    u = np.full(myo.shape, np.nan, np.float32)
    u[tuple(pts.T)] = L0 / np.maximum(L0 + L1, 1e-6)
    return u


def thirds(u):
    out = np.zeros(u.shape, np.uint8)
    ok = ~np.isnan(u)
    out[ok] = 1 + np.minimum((u[ok] * 3).astype(int), 2)
    return out


# ------------------------------------------------------------------ AHA frame (JA3)
def world(aff, v):
    return v @ aff[:3, :3].T + aff[:3, 3]


def frame(m, aff):
    """Long axis from the mitral-plane centre to the apex; levels; RV contact arc and insertions."""
    myo, lv, rv, la = m["myo"], m["lv"], m["rv"], m["la"]
    mitral = lv & ndi.binary_dilation(la, iterations=2)
    if mitral.sum() < 20 or rv.sum() < 1000:
        return None, "no mitral plane or no RV"
    mc = world(aff, np.argwhere(mitral).mean(0))
    P = world(aff, np.argwhere(lv).astype(float))
    apex = P[np.argmax(np.linalg.norm(P - mc, axis=1))]
    ax = (apex - mc) / np.linalg.norm(apex - mc)  # base -> apex
    M = world(aff, np.argwhere(myo).astype(float))
    h = (M - mc) @ ax
    hc = (P - mc) @ ax
    L = hc.max()
    level = np.where(h > L, 3, np.where(h < L / 3, 0, np.where(h < 2 * L / 3, 1, 2)))  # basal, mid, apical, cap
    e_ant = np.array([0.0, 1.0, 1.0]) / np.sqrt(2)  # rule B: anterior-superior (Golf aha_check)
    perp = lambda v: v - np.outer(v @ ax, ax) if v.ndim == 2 else v - (v @ ax) * ax
    rvc = world(aff, np.argwhere(rv).mean(0))
    e1 = perp(rvc - mc); e1 /= np.linalg.norm(e1)
    e2 = np.cross(ax, e1)
    q = perp(M - mc)
    ang = np.degrees(np.arctan2(q @ e2, q @ e1)) % 360  # 0 = towards the RV centroid
    # RV contact arc on basal + mid levels: myocardium within 2 mm of the RV cavity
    sp = float(np.abs(np.linalg.det(aff[:3, :3])) ** (1 / 3))
    near_rv = ndi.distance_transform_edt(~rv, sampling=sp)[tuple(np.argwhere(myo).T)] <= 2.0
    sel = near_rv & (level <= 1)
    if sel.sum() < 50:
        return None, "no RV contact"
    bins = np.zeros(180, bool)
    bins[(ang[sel] // 2).astype(int)] = True
    bins = ndi.binary_closing(np.r_[bins, bins, bins], iterations=3)[180:360]  # bridge gaps <= 6 degrees
    if bins.all():
        return None, "RV contact all round"
    # longest circular run of contact bins
    b2 = np.r_[bins, bins]
    best, run, end = 0, 0, 0
    for i, v in enumerate(b2):
        run = run + 1 if v else 0
        if run > best and run <= 180:
            best, end = run, i
    start = (end - best + 1) % 180
    a0, a1 = start * 2.0, ((end % 180) + 1) * 2.0  # arc from a0 to a1, counter-clockwise, in degrees
    arc = best * 2.0

    def direction(a):
        r = np.radians(a)
        return np.cos(r) * e1 + np.sin(r) * e2

    # the anterior insertion is the arc end pointing more anterior-superior
    if direction(a0) @ e_ant >= direction(a1) @ e_ant:
        ant, sgn = a0, +1.0   # the septum lies counter-clockwise from the anterior insertion
    else:
        ant, sgn = a1, -1.0
    phi = (sgn * (ang - ant)) % 360  # 0 at the anterior insertion, increasing into the septum
    return dict(ax=ax, mc=mc, level=level, phi=phi, arc=arc, M=M, e_ant=e_ant,
                sgn=sgn, ant=ant, e1=e1, e2=e2), "ok"


def segments(fr, rule):
    """AHA 17 labels for the myocardium voxels, by `fixed` 60/90-degree sectors from the anterior insertion
    (JA3) or `arc` (septal sectors proportional to the measured RV contact arc)."""
    phi, level = fr["phi"], fr["level"]
    A = 120.0 if rule == "fixed" else fr["arc"]
    rest = (360.0 - A) / 4
    edges = [0, A / 2, A, A + rest, A + 2 * rest, A + 3 * rest, 360.0]
    six = np.select([phi < edges[1], phi < edges[2], phi < edges[3], phi < edges[4], phi < edges[5]],
                    [2, 3, 4, 5, 6], 1)
    centre = A / 2  # septal centre
    p4 = (phi - centre + 45) % 360
    four = np.select([p4 < 90, p4 < 180, p4 < 270], [14, 15, 16], 13)
    return np.where(level == 0, six, np.where(level == 1, six + 6, np.where(level == 2, four, 17))).astype(np.uint8)


def orientation_ok(fr, seg):
    M, mc = fr["M"], fr["mc"]
    c = lambda ks: M[np.isin(seg, ks)].mean(0) if np.isin(seg, ks).any() else mc
    ant1 = (c([1, 7]) - mc) @ fr["e_ant"] > (c([4, 10]) - mc) @ fr["e_ant"]
    sept = (c([2, 3, 8, 9]) - mc) @ fr["e1"] > (c([5, 6, 11, 12]) - mc) @ fr["e1"]
    return bool(ant1 and sept)


# ------------------------------------------------------------------ half-maximum offsets (JA7 rule)
def halfmax_offsets(ct, m, sp, th, n_pts=3000, rng=None):
    """Signed offset (mm) of each mask border from the image half-maximum along the border normal.
    + = the mask border lies outward of the half-maximum (towards the epicardium for the endocardial border,
    into the fat for the epicardial border). Points where a plateau is not clean are skipped."""
    rng = rng or np.random.default_rng(0)
    myo, lv = m["myo"], m["lv"]
    sol = myo | lv
    others = m["rv"] | m["la"] | m.get("other", np.zeros_like(myo))
    near_other = ndi.distance_transform_edt(~others, sampling=sp) < 4.0
    res = {}
    for name, inner in (("endo", lv), ("epi", sol)):
        S = sdf(inner, sp)
        G = np.stack(np.gradient(S, *sp))
        if name == "endo":
            cand = myo & ndi.binary_dilation(lv, FACE)
        else:
            cand = myo & ~ndi.binary_erosion(sol, FACE) & ~near_other
        pts = np.argwhere(cand)
        if len(pts) == 0:
            res[name] = None
            continue
        pts = pts[rng.choice(len(pts), min(n_pts, len(pts)), replace=False)]
        nvec = G[(slice(None),) + tuple(pts.T)].T
        nvec /= np.linalg.norm(nvec, axis=1, keepdims=True) + 1e-9
        s_border = -S[tuple(pts.T)]  # border position along the normal, relative to the voxel centre (mm)
        tloc = th[tuple(pts.T)]
        ss = np.arange(-4.0, 4.01, 0.1)
        coords = pts[:, None, :] + ss[None, :, None] * nvec[:, None, :] / sp
        prof = ndi.map_coordinates(ct, coords.reshape(-1, 3).T, order=1, mode="nearest").reshape(len(pts), len(ss))
        offs = []
        for i in range(len(pts)):
            t = tloc[i]
            if not np.isfinite(t) or t < 3.0:
                continue
            if name == "endo":
                a = np.median(prof[i, (ss >= -3) & (ss <= -1.5)])                  # blood plateau
                b = np.median(prof[i, np.abs(ss - (t / 2 + s_border[i])) <= 0.5])  # mid-wall plateau
                if a - b < 100:
                    continue
                rng_s = (ss >= -1.5) & (ss <= t / 2 + s_border[i])
            else:
                a = np.median(prof[i, np.abs(ss + (t / 2 - s_border[i])) <= 0.5])  # mid-wall plateau
                b = np.median(prof[i, (ss >= 1.5) & (ss <= 3)])                    # outside plateau
                if not (-250 <= b <= 30) or a - b < 60:
                    continue
                rng_s = (ss >= -(t / 2 - s_border[i])) & (ss <= 1.5)
            half = (a + b) / 2
            p, sv = prof[i, rng_s], ss[rng_s]
            cross = np.nonzero((p[:-1] >= half) & (p[1:] < half))[0]
            if len(cross) == 0:
                continue
            k = cross[np.argmin(np.abs(sv[cross] - s_border[i]))]
            s_half = sv[k] + (p[k] - half) / (p[k] - p[k + 1] + 1e-9) * (sv[k + 1] - sv[k])
            offs.append(s_border[i] - s_half)
        offs = np.array(offs)
        res[name] = None if len(offs) < 30 else {
            "n": int(len(offs)), "median_mm": float(np.median(offs)),
            "iqr_mm": [float(np.percentile(offs, 25)), float(np.percentile(offs, 75))]}
    return res


# ------------------------------------------------------------------ territories (JA4)
def territories(m, cor, sp, myo_pts):
    """Per myocardium voxel: nearest LAD/LCx/RCA voxel (Euclidean, JA4) and geodesic on the epicardial
    surface (each surface voxel takes the class whose projected vessel seeds are nearest along the surface;
    the wall takes its nearest surface voxel's class)."""
    vp = np.argwhere(np.isin(cor, (2, 3, 4)))
    if len(vp) < 50:
        return None, None
    vcls = cor[tuple(vp.T)]
    _, nn = cKDTree(vp * sp).query(myo_pts * sp)
    eu = vcls[nn]
    myo, sol = m["myo"], m["myo"] | m["lv"]
    epi = myo & ~ndi.binary_erosion(sol, FACE)
    E = np.argwhere(epi)
    tE = cKDTree(E * sp)
    d, j = tE.query(vp * sp)
    near = d <= 6.0
    if near.sum() < 30:
        return eu, None
    # 26-connected surface graph
    idx = -np.ones(myo.shape, np.int64)
    idx[tuple(E.T)] = np.arange(len(E))
    r, c, w = [], [], []
    for off in np.argwhere(np.ones((3, 3, 3))) - 1:
        if not off.any():
            continue
        nb = E + off
        ok = np.all((nb >= 0) & (nb < np.array(myo.shape)), 1)
        jj = np.full(len(E), -1, np.int64)
        jj[ok] = idx[tuple(nb[ok].T)]
        k = jj >= 0
        r.append(np.nonzero(k)[0]); c.append(jj[k]); w.append(np.full(k.sum(), float(np.linalg.norm(off * sp))))
    G = coo_matrix((np.concatenate(w), (np.concatenate(r), np.concatenate(c))), shape=(len(E), len(E))).tocsr()
    D = np.full((3, len(E)), np.inf)
    for ci, k in enumerate((2, 3, 4)):
        seeds = np.unique(j[near & (vcls == k)])
        if len(seeds):
            D[ci] = dijkstra(G, indices=seeds, min_only=True)
    lab_E = np.array([2, 3, 4])[np.argmin(D, 0)]
    lab_E[~np.isfinite(D.min(0))] = 0
    _, nm = tE.query(myo_pts * sp)
    geo = lab_E[nm]
    return eu, geo


def seg_majority(seg, lab):
    out = {}
    for k in range(1, 18):
        sel = seg == k
        if sel.sum() < 20:
            continue
        cnt = Counter(lab[sel].tolist())
        cnt.pop(0, None)
        if cnt:
            out[k] = VESSEL[cnt.most_common(1)[0][0]]
    return out


# ------------------------------------------------------------------ the read-out
def analyse(m, sp, aff, cor=None, rng=None):
    rng = rng or np.random.default_rng(0)
    myo, lv = m["myo"], m["lv"]
    ct = m["ct"]
    out = {}
    u_et, th, de, dp = et_depth(myo, lv, sp)
    pts = np.argwhere(myo)
    s = float(np.mean(sp))
    out["blood_hu"] = float(np.median(ct[ndi.binary_erosion(lv, iterations=3)]))
    out["myo_hu"] = float(np.median(ct[myo & (de >= 1.0 + s / 2) & (dp >= 1.0 + s / 2)]))
    # ---- item 1: geometry and frame
    fr, why = frame(m, aff)
    out["frame"] = why
    if fr is None:
        return out
    seg = segments(fr, "fixed")
    seg_arc = segments(fr, "arc")
    out["septal_arc_deg"] = fr["arc"]
    out["orientation_ok_fixed"] = orientation_ok(fr, seg)
    out["orientation_ok_arc"] = orientation_ok(fr, seg_arc)
    thv = th[tuple(pts.T)]
    seg_th = {k: float(np.median(thv[seg == k])) for k in range(1, 18) if (seg == k).sum() > 50}
    out["seg_thickness_mm"] = seg_th
    out["empty_segments"] = [k for k in range(1, 18) if (seg == k).sum() <= 50]
    out["median_thickness_mm"] = float(np.median([v for k, v in seg_th.items() if k <= 16]))
    out["vox_per_third"] = {k: v / 3 / s for k, v in seg_th.items()}
    out["segments_needing_halves"] = [k for k, v in seg_th.items() if k <= 16 and (v / 3 / s < 4 or v < 5.0)]
    out["seg_changed_fixed_vs_arc"] = float((seg != seg_arc).mean())
    # ---- item 3: depth definitions
    noflux = (m["la"] | m.get("ao", np.zeros_like(myo))) & ~myo & ~lv
    phi = laplace(myo, lv, noflux)
    u_yp = yezzi_prince(phi, myo, lv, sp)
    T_et, T_lp, T_yp = (thirds(x)[tuple(pts.T)] for x in (u_et, phi, u_yp))
    out["thirds_agree_et_laplace"] = float((T_et == T_lp).mean())
    out["thirds_agree_et_yp"] = float((T_et == T_yp).mean())
    out["thirds_share_et"] = [float((T_et == k).mean()) for k in (1, 2, 3)]
    out["thirds_share_yp"] = [float((T_yp == k).mean()) for k in (1, 2, 3)]
    out["thirds_share_laplace"] = [float((T_lp == k).mean()) for k in (1, 2, 3)]
    # ---- item 1 (Hotel): half-maximum offsets
    out["halfmax"] = halfmax_offsets(ct, m, sp, th, rng=rng)
    # ---- item 6: rest TPR with and without the 1 mm guard band; fat
    hu = ct[tuple(pts.T)]
    g_endo = de[tuple(pts.T)] >= 1.0 + s / 2
    g_epi = dp[tuple(pts.T)] >= 1.0 + s / 2
    tpr, tpr_g, sub_g = {}, {}, {}
    for k in range(1, 17):
        sel = seg == k
        a, b = sel & (T_et == 1), sel & (T_et == 3)
        if a.sum() > 20 and b.sum() > 20:
            tpr[k] = float(hu[a].mean() / hu[b].mean())
        ag, bg = a & g_endo, b & g_epi
        if ag.sum() > 20 and bg.sum() > 20:
            tpr_g[k] = float(hu[ag].mean() / hu[bg].mean())
            sub_g[k] = float(hu[ag].mean())
    out["tpr_unguarded"] = tpr
    out["tpr_guarded"] = tpr_g
    core = g_endo & g_epi
    ch = hu[core]
    out["core_hu"] = {"n": int(core.sum()), "mean": float(ch.mean()), "sd": float(ch.std()),
                      "q": {str(q): float(np.percentile(ch, q)) for q in (0.1, 1, 5, 50)}}
    vox_mm3 = float(np.prod(sp))
    corevol = np.zeros(myo.shape, bool)
    corevol[tuple(pts[core].T)] = True
    fat = {}
    for cut in (0, -30, -50, -100):
        lab, n = ndi.label(corevol & (ct < cut), structure=np.ones((3, 3, 3)))
        sizes = np.bincount(lab.ravel())[1:] * vox_mm3 if n else np.zeros(0)
        fat[str(cut)] = {str(v): int((sizes >= v).sum()) for v in (5, 20, 50)}
    out["fat_clusters"] = fat
    # ---- Lima E3 calibration inputs: patient-relative signs
    med = np.median([v for k, v in seg_th.items() if k <= 16])
    out["rel_thickness"] = {k: v / med for k, v in seg_th.items() if k <= 16}
    if sub_g:
        ms = np.median(list(sub_g.values()))
        out["rel_subendo_hu"] = {k: v / ms for k, v in sub_g.items()}
    # ---- item 3: territories
    if cor is not None:
        eu, geo = territories(m, cor, sp, pts)
        if eu is not None:
            maj_eu = seg_majority(seg, eu)
            out["terr_euclid"] = maj_eu
            out["terr_discordant_euclid"] = [k for k, v in maj_eu.items() if v != AHA_DEFAULT[k]]
            out["mass_share_euclid"] = {VESSEL[k]: float((eu == k).mean()) for k in (2, 3, 4)}
            maj_arc = seg_majority(seg_arc, eu)
            out["terr_discordant_euclid_arc"] = [k for k, v in maj_arc.items() if v != AHA_DEFAULT[k]]
            if geo is not None:
                maj_geo = seg_majority(seg, geo)
                out["terr_geodesic"] = maj_geo
                out["terr_discordant_geodesic"] = [k for k, v in maj_geo.items() if v != AHA_DEFAULT[k]]
                both = geo > 0
                out["voxel_agree_euclid_geodesic"] = float((eu[both] == geo[both]).mean()) if both.any() else None
                out["segments_differ_euclid_geodesic"] = [k for k in maj_eu if maj_geo.get(k) != maj_eu[k]]
    return out
