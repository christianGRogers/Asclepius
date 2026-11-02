"""Hotel E1/E2: myocardial layers and AHA segments derived from two borders.

For each TotalSegmentator v1 cardiac study (fetched by fetch_ts_cardiac.py):

1. Label sanity: LV blood-pool HU (contrast or not), myocardium HU, share of myocardium
   voxels below -30 HU (fat or label leak).
2. A Laplace transmural coordinate u in the LV myocardium (u = 0 at the LV cavity, u = 1 at
   the epicardium or the RV cavity), wall thickness (distance to endo + distance to epi), and
   transmural thirds (subendocardial, mid-wall, subepicardial).
3. Border-error propagation: both borders are moved by a smooth random displacement of a
   given RMS (mm); the thirds are re-derived and compared with the unperturbed thirds (Dice).
   This measures how good the two borders must be for the derived layers to be stable.
4. AHA 17 segments from the LV long axis (apex to mitral centre) and the RV direction
   (septum), and per-segment HU of each third plus the transmural perfusion ratio
   TPR = mean HU(subendocardial third) / mean HU(subepicardial third).

CPU only. Usage: python layers_from_borders.py DATA_DIR OUT_JSON [--no-perturb]
(--no-perturb skips step 3, for the Fir pass on sub-millimetre pool volumes.)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
from scipy import ndimage as ndi
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import cg

from coronary_holdout import PoolGuard, held_out_totalseg_ids

RNG_SEED = 20261030
SIGMAS_MM = [0.5, 1.0, 1.5]
SMOOTH_MM = 6.0  # correlation length of the simulated border error
N_DRAWS = 2


def load(case: Path):
    ct = nib.load(case / "ct.nii.gz")
    a = ct.get_fdata(dtype=np.float32)
    sp = np.array(ct.header.get_zooms()[:3], dtype=float)
    seg = {}
    for m in ["heart_myocardium", "heart_ventricle_left", "heart_ventricle_right",
              "heart_atrium_left", "aorta"]:
        seg[m] = np.asarray(nib.load(case / "segmentations" / f"{m}.nii.gz").dataobj) > 0
    return a, sp, ct.affine, seg


def laplace(myo: np.ndarray, endo_src: np.ndarray, epi_src: np.ndarray) -> np.ndarray:
    """Solve Laplace in myo with u=0 next to endo_src, u=1 next to epi_src, Neumann elsewhere."""
    idx = -np.ones(myo.shape, dtype=np.int64)
    pts = np.argwhere(myo)
    idx[tuple(pts.T)] = np.arange(len(pts))
    n = len(pts)
    rows, cols, vals = [], [], []
    diag = np.zeros(n)
    b = np.zeros(n)
    for ax in range(3):
        for step in (-1, 1):
            nb = pts.copy()
            nb[:, ax] += step
            ok = (nb[:, ax] >= 0) & (nb[:, ax] < myo.shape[ax])
            i_ok = np.where(ok)[0]
            nbv = nb[ok]
            nidx = idx[tuple(nbv.T)]
            inside = nidx >= 0
            # myocardium neighbour: coupling
            rows.append(i_ok[inside]); cols.append(nidx[inside]); vals.append(-np.ones(inside.sum()))
            diag[i_ok[inside]] += 1
            # Dirichlet neighbours
            out = ~inside
            o_pts = nbv[out]
            is_endo = endo_src[tuple(o_pts.T)]
            is_epi = epi_src[tuple(o_pts.T)] & ~is_endo
            ii = i_ok[out]
            diag[ii[is_endo]] += 1
            diag[ii[is_epi]] += 1
            np.add.at(b, ii[is_epi], 1.0)
    # isolated components with no Dirichlet contact get a tiny anchor to stay solvable
    diag = np.where(diag == 0, 1.0, diag) + 1e-9
    rows.append(np.arange(n)); cols.append(np.arange(n)); vals.append(diag)
    A = coo_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(n, n)).tocsr()
    u0 = np.full(n, 0.5)
    u, _ = cg(A, b, x0=u0, rtol=1e-6, maxiter=3000)
    out = np.full(myo.shape, np.nan, dtype=np.float32)
    out[tuple(pts.T)] = np.clip(u, 0, 1)
    return out


def derive(lv: np.ndarray, myo: np.ndarray, rv: np.ndarray, sp: np.ndarray):
    """Transmural coordinate, thickness and thirds from an LV cavity and an LV myocardium mask."""
    st = ndi.generate_binary_structure(3, 1)
    lv_d = ndi.binary_dilation(lv, st)
    endo_src = lv
    epi_src = ~(myo | lv)  # everything else, RV cavity included (septum's right side)
    u = laplace(myo, endo_src, epi_src)
    d_endo = ndi.distance_transform_edt(~lv, sampling=sp)
    d_epi = ndi.distance_transform_edt(myo | lv, sampling=sp)
    thick = np.where(myo, d_endo + d_epi, np.nan)
    thirds = np.zeros(myo.shape, dtype=np.uint8)
    thirds[myo & (u < 1 / 3)] = 1
    thirds[myo & (u >= 1 / 3) & (u < 2 / 3)] = 2
    thirds[myo & (u >= 2 / 3)] = 3
    touches_endo = myo & lv_d
    derive.d_endo, derive.d_epi = d_endo, d_epi  # kept for inset sampling
    return u, thick, thirds, touches_endo


def smooth_noise(shape, sp, sigma_mm, rng):
    n = rng.standard_normal(shape).astype(np.float32)
    n = ndi.gaussian_filter(n, SMOOTH_MM / sp)
    n *= sigma_mm / (n.std() + 1e-9)
    return n


def perturb(lv, myo, sp, sigma_mm, rng):
    """Move the endocardial and epicardial borders by independent smooth fields (RMS sigma_mm)."""
    epi_solid = lv | myo

    def sdf(m):
        return ndi.distance_transform_edt(~m, sampling=sp) - ndi.distance_transform_edt(m, sampling=sp)

    lv2 = (sdf(lv) + smooth_noise(lv.shape, sp, sigma_mm, rng)) < 0
    ep2 = (sdf(epi_solid) + smooth_noise(lv.shape, sp, sigma_mm, rng)) < 0
    ep2 |= lv2
    return lv2, ep2 & ~lv2


def dice(a, b):
    s = a.sum() + b.sum()
    return float(2 * (a & b).sum() / s) if s else float("nan")


def aha_segments(lv, myo, la, rv, aff, sp):
    """AHA 17-segment label per myocardium voxel (0 = not assigned)."""
    world = lambda p: (aff[:3, :3] @ p.T).T + aff[:3, 3]
    lv_pts = world(np.argwhere(lv).astype(float))
    # mitral centre: LV voxels that touch the LA
    mitral = lv & ndi.binary_dilation(la, iterations=2)
    if mitral.sum() < 10:
        return None, "no LA-LV contact"
    mc = world(np.argwhere(mitral).astype(float)).mean(0)
    c = lv_pts.mean(0)
    # long axis: principal axis of the LV cavity, oriented from the mitral centre to the apex
    w, v = np.linalg.eigh(np.cov((lv_pts - c).T))
    ax = v[:, -1]
    if np.dot(c - mc, ax) < 0:
        ax = -ax
    myo_ijk = np.argwhere(myo)
    myo_pts = world(myo_ijk.astype(float))
    t_lv = (lv_pts - mc) @ ax
    t_myo = (myo_pts - mc) @ ax
    t_cav_apex = np.percentile(t_lv, 99.5)
    base_t = 0.0
    # basal / mid / apical thirds of the cavity length (Cerqueira 2002), apex cap beyond the cavity
    L = t_cav_apex - base_t
    ring = np.full(len(myo_pts), -1)
    ring[(t_myo >= base_t) & (t_myo < base_t + L / 3)] = 0
    ring[(t_myo >= base_t + L / 3) & (t_myo < base_t + 2 * L / 3)] = 1
    ring[(t_myo >= base_t + 2 * L / 3) & (t_myo <= t_cav_apex)] = 2
    ring[t_myo > t_cav_apex] = 3
    # circumferential angle: zero at the septum (direction to the RV centroid), positive towards anterior
    rv_c = world(np.argwhere(rv).astype(float)).mean(0)
    e_sep = rv_c - c
    e_sep -= np.dot(e_sep, ax) * ax
    e_sep /= np.linalg.norm(e_sep)
    e2 = np.cross(ax, e_sep)
    # world is RAS: anterior = +y
    if np.dot(e2, np.array([0.0, 1.0, 0.0])) < 0:
        e2 = -e2
    r = myo_pts - c
    ang = np.degrees(np.arctan2(r @ e2, r @ e_sep))  # 0 = mid-septum, +90 ~ anterior
    seg = np.zeros(len(myo_pts), dtype=np.uint8)
    # six-sector rings: septum centred on 0 deg, split into anteroseptal (0..60) and inferoseptal (-60..0)
    six = [(0, 60, 2), (60, 120, 1), (120, 180, 6), (-180, -120, 5), (-120, -60, 4), (-60, 0, 3)]
    for lo, hi, s in six:
        sel = (ang >= lo) & (ang < hi)
        seg[sel & (ring == 0)] = s
        seg[sel & (ring == 1)] = s + 6
    # apical ring: four 90-degree sectors: septal (-45..45)=14, anterior (45..135)=13, lateral=16, inferior=15
    four = [(-45, 45, 14), (45, 135, 13), (-135, -45, 15)]
    for lo, hi, s in four:
        seg[((ang >= lo) & (ang < hi)) & (ring == 2)] = s
    seg[(ring == 2) & ((ang >= 135) | (ang < -135))] = 16
    seg[ring == 3] = 17
    out = np.zeros(myo.shape, dtype=np.uint8)
    out[tuple(myo_ijk.T)] = seg
    return out, "ok"


UPSAMPLE = 2  # 1.5 mm -> 0.75 mm (volumes finer than 1 mm are kept as they are), so sub-millimetre border errors are representable


def crop_upsample(a, sp, aff, s):
    """Crop to the heart (+15 mm) and resample: CT linearly, masks through their signed distance."""
    heart = s["heart_myocardium"] | s["heart_ventricle_left"] | s["heart_ventricle_right"] | s["heart_atrium_left"]
    ijk = np.argwhere(heart)
    m = int(np.ceil(15 / sp.min()))
    lo = np.maximum(ijk.min(0) - m, 0)
    hi = np.minimum(ijk.max(0) + m + 1, a.shape)
    sl = tuple(slice(l, h) for l, h in zip(lo, hi))
    f = UPSAMPLE if sp.max() > 1.0 else 1  # only the 1.5 mm public volumes are upsampled
    a2 = ndi.zoom(a[sl], f, order=1)
    out = {}
    for k, v in s.items():
        v = v[sl]
        sd = ndi.distance_transform_edt(~v) - ndi.distance_transform_edt(v)
        out[k] = ndi.zoom(sd.astype(np.float32), f, order=1) < 0
    aff2 = aff.copy()
    aff2[:3, 3] = aff[:3, :3] @ lo + aff[:3, 3]
    aff2[:3, :3] = aff[:3, :3] / f
    return a2, sp / f, aff2, out


INSETS_MM = [0.0, 0.75, 1.5, 2.25]
TPR_INSET_MM = 1.5  # voxels nearer than this to either border are not sampled for HU


def per_segment(a, seg, thirds, thick, contrast):
    core = (derive.d_endo >= TPR_INSET_MM) & (derive.d_epi >= TPR_INSET_MM)
    th, tpr, sub = {}, {}, {}
    for k in range(1, 18):
        mk = seg == k
        if mk.sum() < 50:
            continue
        th[k] = float(np.nanmean(thick[mk]))
        if contrast:
            m1, m3 = mk & (thirds == 1) & core, mk & (thirds == 3) & core
            if m1.sum() >= 20 and m3.sum() >= 20 and a[m3].mean() > 20:
                sub[k] = float(a[m1].mean())
                tpr[k] = float(a[m1].mean() / a[m3].mean())
    return th, tpr, sub


def edge_profiles(a, myo, lv, rv, la, aorta, sp):
    """Median HU against signed distance from the label's endocardial and epicardial borders.

    Positive = inside the myocardium label. The half-maximum crossing between the two plateaus
    is where the image puts the edge; its distance from 0 is the label's border offset (mm).
    """
    bins = np.arange(-4.5, 6.01, 0.75)
    d_in_endo = ndi.distance_transform_edt(~lv, sampling=sp)  # in myo: distance to cavity
    d_out_endo = ndi.distance_transform_edt(~ndi.binary_dilation(lv, iterations=0) | ~lv, sampling=sp)
    d_lv_in = ndi.distance_transform_edt(lv, sampling=sp)  # inside cavity: depth
    near_lv = ndi.distance_transform_edt(~lv, sampling=sp)
    solid = myo | lv
    d_epi_in = ndi.distance_transform_edt(solid, sampling=sp)
    d_epi_out = ndi.distance_transform_edt(~solid, sampling=sp)
    other = ndi.binary_dilation(rv | la | aorta, iterations=4)
    res = {}
    # endocardium: inside cavity -> negative, inside myo (towards epi) -> positive
    sd_endo = np.where(lv, -d_lv_in, np.where(myo, near_lv, np.nan))
    # epicardium (free wall only): inside myo positive, outside negative
    sd_epi = np.where(myo & ~other, d_epi_in, np.where(~solid & ~other & (d_epi_out < 6), -d_epi_out, np.nan))
    for name, sd in (("endo", sd_endo), ("epi", sd_epi)):
        prof = []
        for lo, hi in zip(bins[:-1], bins[1:]):
            m = (sd >= lo) & (sd < hi)
            prof.append(float(np.median(a[m])) if m.sum() > 50 else None)
        res[name] = {"bin_lo_mm": bins[:-1].tolist(), "median_hu": prof}
    # half-maximum crossing
    def crossing(prof, lo_side_val, hi_side_val, frac=0.5):
        half = lo_side_val + frac * (hi_side_val - lo_side_val)
        centres = bins[:-1] + 0.375
        vals = np.array([np.nan if v is None else v for v in prof])
        ok = ~np.isnan(vals)
        c, v = centres[ok], vals[ok]
        for i in range(len(v) - 1):
            if (v[i] - half) * (v[i + 1] - half) <= 0 and v[i] != v[i + 1]:
                return float(c[i] + (half - v[i]) * (c[i + 1] - c[i]) / (v[i + 1] - v[i]))
        return None
    core = myo & (ndi.distance_transform_edt(~lv, sampling=sp) >= 3) & (d_epi_in >= 3)
    myo_core = float(np.median(a[core])) if core.sum() > 50 else float(np.median(a[myo]))
    blood = float(np.median(a[d_lv_in >= 3])) if (d_lv_in >= 3).any() else None
    fat = a[(~solid) & ~other & (d_epi_out > 1.5) & (d_epi_out < 4.5)]
    fat = fat[(fat > -250) & (fat < -30)]  # fat window, so lung is not taken as fat
    fat = float(np.median(fat)) if fat.size > 50 else None
    res["plateaus_blood_myocore_fat"] = [blood, myo_core, fat]
    if blood:
        pe = res["endo"]["median_hu"]
        res["endo_halfmax_mm"] = crossing(pe, blood, myo_core)
        c10, c90 = crossing(pe, blood, myo_core, 0.1), crossing(pe, blood, myo_core, 0.9)
        res["endo_10_90_width_mm"] = (c90 - c10) if (c10 is not None and c90 is not None) else None
    if fat is not None:
        res["epi_halfmax_mm"] = crossing(res["epi"]["median_hu"], fat, myo_core)
    return res


def run_case(case: Path, rng) -> dict:
    a, sp, aff, s = load(case)
    a, sp, aff, s = crop_upsample(a, sp, aff, s)
    myo, lv, rv, la = s["heart_myocardium"], s["heart_ventricle_left"], s["heart_ventricle_right"], s["heart_atrium_left"]
    r: dict = {"case": case.name, "spacing_mm": sp.tolist(), "study_type": (case / "done").read_text()}
    if myo.sum() < 1000 or lv.sum() < 1000:
        r["status"] = "masks missing"
        return r
    r["lv_blood_hu"] = float(np.median(a[ndi.binary_erosion(lv, iterations=2)])) if ndi.binary_erosion(lv, iterations=2).any() else float(np.median(a[lv]))
    r["contrast"] = r["lv_blood_hu"] > 150
    r["myo_hu_median"] = float(np.median(a[myo]))
    r["myo_frac_below_m30"] = float((a[myo] < -30).mean())
    r["myo_ml"] = float(myo.sum() * sp.prod() / 1000)
    # keep the largest myocardium component
    lab, n = ndi.label(myo)
    if n > 1:
        sizes = ndi.sum(myo, lab, range(1, n + 1))
        myo = lab == (1 + int(np.argmax(sizes)))
    u, thick, thirds, touches = derive(lv, myo, rv, sp)
    r["myo_touching_cavity_frac"] = float(touches.sum() / myo.sum())
    r["thickness_mm_median"] = float(np.nanmedian(thick))
    r["thickness_mm_p10_p90"] = [float(np.nanpercentile(thick, 10)), float(np.nanpercentile(thick, 90))]
    r["voxels_across_wall_median"] = r["thickness_mm_median"] / float(sp.mean())
    r["third_ml"] = [float((thirds == k).sum() * sp.prod() / 1000) for k in (1, 2, 3)]
    if r["contrast"]:
        r["edges"] = edge_profiles(a, myo, lv, rv, la, s["aorta"], sp)
        r["third_hu_mean_by_inset_mm"] = {}
        for d in INSETS_MM:
            core = (derive.d_endo >= d) & (derive.d_epi >= d)
            r["third_hu_mean_by_inset_mm"][str(d)] = [
                float(a[(thirds == k) & core].mean()) if ((thirds == k) & core).sum() > 100 else None for k in (1, 2, 3)]

    seg, why = aha_segments(lv, myo, la, rv, aff, sp)
    r["aha_status"] = why
    if seg is None:
        r["status"] = "no AHA"
        return r
    r["aha_ml"] = {int(k): float((seg == k).sum() * sp.prod() / 1000) for k in range(1, 18)}
    th0, tpr0, sub0 = per_segment(a, seg, thirds, thick, r["contrast"])
    r["aha_thickness_mm"], r["aha_tpr"], r["aha_subendo_hu"] = th0, tpr0, sub0
    # border-error propagation: thirds Dice, per-segment thickness and TPR error
    pert = {}
    for sg in ([] if NO_PERTURB else SIGMAS_MM):
        rows = []
        for _ in range(N_DRAWS):
            lv2, myo2 = perturb(lv, myo, sp, sg, rng)
            _, thick2, th2, _ = derive(lv2, myo2, rv, sp)
            seg2, _ = aha_segments(lv2, myo2, la, rv, aff, sp)
            row = {"dice": [dice(myo, myo2)] + [dice(thirds == k, th2 == k) for k in (1, 2, 3)]}
            if seg2 is not None:
                thp, tprp, _ = per_segment(a, seg2, th2, thick2, r["contrast"])
                row["thick_abs_err_mm"] = float(np.mean([abs(thp[k] - th0[k]) for k in th0 if k in thp]))
                if tprp:
                    row["tpr_abs_err"] = float(np.mean([abs(tprp[k] - tpr0[k]) for k in tpr0 if k in tprp]))
            rows.append(row)
        agg = {"dice_myo_endo_mid_epi": np.mean([q["dice"] for q in rows], 0).tolist()}
        for key in ("thick_abs_err_mm", "tpr_abs_err"):
            v = [q[key] for q in rows if key in q]
            if v:
                agg[key] = float(np.mean(v))
        pert[str(sg)] = agg
    if pert:
        r["perturb"] = pert
    r["status"] = "ok"
    return r


def main(data: Path, out: Path) -> None:
    rng = np.random.default_rng(RNG_SEED)
    res = []
    held = held_out_totalseg_ids()
    guard = PoolGuard()
    for case in sorted(p for p in data.iterdir() if (p / "done").exists()):
        if case.name in held or guard.reason(case.name + ".nii.gz"):
            raise SystemExit(f"{case.name} is a coronary hold-out (D27/A34/D35); refusing to read it")
        try:
            r = run_case(case, rng)
        except Exception as e:  # report and continue
            r = {"case": case.name, "status": f"error: {e}"}
        print(json.dumps({k: r.get(k) for k in ("case", "status", "contrast", "lv_blood_hu", "myo_hu_median",
                                                   "thickness_mm_median", "aha_status")}), flush=True)
        res.append(r)
    out.write_text(json.dumps(res, indent=1))


NO_PERTURB = "--no-perturb" in sys.argv

if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
