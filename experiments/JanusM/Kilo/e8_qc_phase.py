"""E8 (Kilo v3): registration QC cuts, and a truth-free check that sees a cardiac-phase mismatch.

Round 2 ruling, section 7 item 5: how the JA29 QC cuts are set on development, and whether any truth-free number
catches a phase mismatch (Juliet E6: a 5 % cavity change halves bin accuracy on scarred segments, and neither the
fat-like nor the blood-like share sees it). Also (Kilo's objection 1b on #179): is P-K specific on a heart with no scar?

Data: the 13 enhanced public TotalSegmentator v1 cardiac CTs that the shared JA12 guard allows (the whole list and
each case pass `janusm.guard.refuse` before any file is opened). Images stay outside the repository.

Per heart and repetition (seeded by heart and rep):
  * scars as E5: 5 segments of 1-16, subendocardial, depth tau in 0.15 / 0.40 / 0.65 / 0.90 / random; plus a
    scar-free version of the same heart with the same noise (the LGE-negative case);
  * cardiac phase between the scans, e in {-0.05, 0, +0.05}: the LIE's endocardium moves by e x R_eq (R_eq = the
    LV cavity's equivalent-sphere radius) with the epicardium fixed. e > 0: the LIE cavity is smaller and its wall
    thicker (Juliet E6's case); e < 0: the reverse. Scar follows the wall (subendocardial scar grows inward with it);
  * LIE contrast: remote myocardium 85 HU, scar 85 + D (D = 60), blood 85 + {0.5, 1.0, 1.5} D (below, equal to and
    above scar), fat -80, other soft tissue compressed toward 40, lung and air unchanged; PSF 0.6 voxel; noise SD
    D / CNR, CNR in {3, 5};
  * motion of the LIE against the first pass: none; or E5's (whole-image rigid, rot N(0, 3 deg), trans N(0, 4 mm),
    plus smooth non-rigid RMS 1.5 mm, 20 mm correlation);
  * JA29 stages: R0 (scanner coordinates, i.e. no correction) and heart-masked rigid Mattes MI (R3 of E5); the
    first-pass CT is moving and the LIE fixed; classes and segments carried by nearest neighbour.

Per carried result:
  * truth: the mean signed and absolute distance of the carried endocardium from the LIE's true endocardium
    (+ = the carried border lies inside the true wall, so it misses subendocardium);
  * QC (all on the LIE smoothed to FWHM 1.5 mm, JA30; remote = core voxels of the 6 lowest-median segments; blood =
    the carried cavity eroded by 2 mm):
      q_fat    share of the carried wall < 0 HU (Juliet);
      q_blood  share of the carried wall > remote + 0.8 (blood - remote) (Juliet);
      q_bright share of the carried wall > the blood median (Kilo);
  * **edge offset** (new, truth-free): the signed distance from the carried endocardium at which the LIE crosses
    half-way between blood and remote wall, from the mean intensity profile over the 6 remote segments (0.5 mm bins,
    -6 to +4 mm). Positive = the LIE's edge lies outside (in the wall of) the carried border, i.e. the LIE cavity is
    larger. Per-segment offsets are also kept, and their spread (IQR over segments 1-16) is the translation signal;
  * grading (JA30 constants): P-K, P-G presence; E-V extent; per segment against the truth (volume share in the
    LIE's true wall), and on the scar-free version for specificity on an LGE-negative heart.

Usage: python e8_qc_phase.py DATA_DIR OUT_JSON [--jobs 4] [--reps 2]
"""
from __future__ import annotations

import argparse, json, pathlib, sys, time
from concurrent.futures import ProcessPoolExecutor

import nibabel as nib
import numpy as np
import SimpleITK as sitk
from scipy import ndimage as ndi

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from layers import distance_depth, aha17  # noqa: E402
from e5_lie_registration import BLOOD, TAUS, motion_field, warp, register, to_sitk, from_sitk  # noqa: E402

D = 60.0
REMOTE = 85.0
BLOOD_LEVELS = {"below": 0.5, "equal": 1.0, "above": 1.5}
CNRS = (3.0, 5.0)
PHASES = (-0.05, 0.0, 0.05)
MOTIONS = ("none", "e5")
KIM = np.array([0.25, 0.50, 0.75])


def kbin(frac, present):
    return np.where(present, np.digitize(np.clip(frac, 1e-9, 1), KIM) + 1, 0)


def corrected_sdf(cav, sp):
    """Signed distance (mm) from the cavity surface, half-voxel corrected (Golf's convention, JA15): negative inside
    the cavity, positive outside; boundary voxels sit at -h/2 and +h/2 instead of -h and +h."""
    h = float(np.mean(sp))
    return np.where(cav, -(ndi.distance_transform_edt(cav, sampling=sp) - h / 2),
                    ndi.distance_transform_edt(~cav, sampling=sp) - h / 2).astype(np.float32)


def phase_fields(myo, cav, scar, seg, s0, delta_mm, sp):
    """Sub-voxel phase change: the LIE's endocardium sits at s0 = -delta_mm (> 0: the cavity shrinks, the wall
    thickens inward), the epicardium is fixed. Returns, on the first-pass grid: blood fraction in the LV (fb), the
    scar source of each LV voxel (a cavity voxel takes its nearest wall voxel's scar), and the per-segment truth
    (scar volume share of the LIE's wall, partial volumes counted)."""
    h = float(np.mean(sp))
    lv = myo | cav
    fb = np.where(lv, np.clip(0.5 - (s0 + delta_mm) / h, 0, 1), 0).astype(np.float32)
    _, ind = ndi.distance_transform_edt(~myo, sampling=sp, return_indices=True)
    scar_src = np.where(myo, scar, scar[tuple(ind)]) & lv
    seg_lv = np.where(myo, seg, seg[tuple(ind)]) * lv
    ww = (1 - fb) * lv
    truth = np.array([float((ww * scar_src)[seg_lv == k].sum() / max(ww[seg_lv == k].sum(), 1e-6)) for k in range(1, 17)])
    return fb, scar_src, truth


def remote_stats(img, wall_seg):
    wall = wall_seg > 0
    core = ndi.binary_erosion(wall)
    med = {s: float(np.median(img[core & (wall_seg == s)])) for s in range(1, 17) if (core & (wall_seg == s)).sum() > 20}
    if len(med) < 8:
        return None
    rs = sorted(med, key=med.get)[:6]
    rem = img[core & np.isin(wall_seg, rs)]
    mu = float(np.median(rem)); sd = float(1.4826 * np.median(np.abs(rem - mu)))
    return mu, sd, rs, med, core


def grade(img, wall_seg, sdist):
    """JA30 menu items P-K, P-G (presence) and E-V (extent), per segment 1-16."""
    r = remote_stats(img, wall_seg)
    if r is None:
        return None
    mu, sd, rs, med, core = r
    top = max(med, key=med.get)
    thr_k = mu + 0.5 * (np.percentile(img[core & (wall_seg == top)], 99) - mu)
    thr_3 = mu + 3 * sd
    above3 = (img > thr_3) & (wall_seg > 0)
    opened = ndi.binary_opening(above3)
    out = {"pk": np.zeros(16, bool), "pg": np.zeros(16, bool), "ev": np.full(16, np.nan), "pk_share": np.full(16, np.nan)}
    for s in range(1, 17):
        m = wall_seg == s
        if m.sum() <= 20:
            continue
        out["pk_share"][s - 1] = (img[m] > thr_k).mean()
        out["pk"][s - 1] = out["pk_share"][s - 1] >= 0.05
        deep = m & (sdist > 1.0)
        out["pg"][s - 1] = deep.sum() > 0 and opened[deep].mean() >= 0.05
        out["ev"][s - 1] = above3[m].mean()
    out["thr_k_minus_remote_sd"] = float((thr_k - mu) / max(sd, 1e-6))
    return out


def signed_endo_distance(cav, sp):
    """mm from the carried endocardium: negative in the cavity, positive outside it (half-voxel corrected)."""
    return corrected_sdf(cav, sp)


def nearest_segment(wall_seg, sp):
    """Each voxel's nearest carried-wall segment."""
    _, ind = ndi.distance_transform_edt(wall_seg == 0, sampling=sp, return_indices=True)
    return wall_seg[tuple(ind)]


def edge_offset(img, cav, wall_seg, sdist, segs, near):
    """Half-way crossing of the mean LIE profile across the carried endocardium, over the given segments."""
    region = (sdist >= -6) & (sdist <= 4) & (cav | (wall_seg > 0)) & np.isin(near, segs)
    if region.sum() < 200:
        return np.nan
    d, v = sdist[region], img[region]
    edges = np.arange(-6, 4.01, 0.5)
    k = np.digitize(d, edges) - 1
    prof = np.array([v[k == i].mean() if (k == i).sum() > 5 else np.nan for i in range(len(edges) - 1)])
    mid = (edges[:-1] + edges[1:]) / 2
    b = np.nanmedian(prof[(mid >= -6) & (mid <= -3)]); w = np.nanmedian(prof[(mid >= 1.5) & (mid <= 3.5)])
    if not np.isfinite(b) or not np.isfinite(w) or abs(b - w) < 1e-3:
        return np.nan
    h = (b + w) / 2
    ok = np.isfinite(prof)
    f, mid = (prof[ok] - h) * np.sign(b - w), mid[ok]     # f > 0 on the blood side; empty bins skipped
    for i in range(len(f) - 1):
        if f[i] > 0 >= f[i + 1]:
            return float(mid[i] + (mid[i + 1] - mid[i]) * f[i] / (f[i] - f[i + 1]))
    return np.nan


def qc(img, wall_seg, cav):
    r = remote_stats(img, wall_seg)
    if r is None:
        return None
    mu = r[0]
    inner = ndi.binary_erosion(cav, iterations=2)
    bl = float(np.median(img[inner])) if inner.sum() > 50 else float(np.median(img[cav]))
    w = img[wall_seg > 0]
    return {"q_fat": float((w < 0).mean()), "q_blood": float((w > mu + 0.8 * (bl - mu)).mean()),
            "q_bright": float((w > bl).mean()), "remote_hu": mu, "blood_hu": bl, "rs": r[2]}


def run_case(args):
    case, reps = args
    from janusm.guard import refuse
    case = pathlib.Path(case)
    refuse([case.name], what="Kilo E8 case", source="TotalSegmentator")      # JA12 guard first, before any file
    sitk.ProcessObject.SetGlobalDefaultNumberOfThreads(1)
    rng = np.random.default_rng(int(case.name[1:]) + 8)
    rd = lambda k: np.asanyarray(nib.load(case / f"segmentations/{k}.nii.gz").dataobj) > 0  # noqa: E731
    myo, cav = rd("heart_myocardium"), rd("heart_ventricle_left")
    ctn = nib.load(case / "ct.nii.gz"); ct = np.asanyarray(ctn.dataobj).astype(np.float32)
    sp = np.array(ctn.header.get_zooms()[:3], float)
    if myo.sum() < 1000 or cav.sum() < 1000 or float(np.median(ct[cav])) < 150:
        return {"case": case.name, "skip": "no LV contrast or masks"}
    blood = {k: rd(k) for k in BLOOD}
    box = myo | cav
    m = np.ceil(30 / sp).astype(int)
    lo = np.maximum(np.argwhere(box).min(0) - m, 0); hi = np.minimum(np.argwhere(box).max(0) + m + 1, box.shape)
    sl = tuple(slice(a, b) for a, b in zip(lo, hi))
    ct, myo, cav = ct[sl], myo[sl], cav[sl]
    la, rv = blood["heart_atrium_left"][sl], blood["heart_ventricle_right"][sl]
    allblood = np.zeros_like(myo)
    for k in BLOOD:
        allblood |= blood[k][sl]
    allblood &= ~myo
    aff = ctn.affine.copy(); aff[:3, 3] = aff[:3, :3] @ lo + aff[:3, 3]
    t, _ = distance_depth(myo, cav, la | blood["aorta"][sl], sp)
    seg, _ = aha17(myo, cav, rv, la, aff)
    seg = np.where(seg > 16, 0, seg).astype(np.uint8)                        # segments 1-16 (17 left out, as E5)
    r_eq = float((3 * cav.sum() * sp.prod() / (4 * np.pi)) ** (1 / 3))
    moving = to_sitk(np.clip(ct, -300, 800), sp)
    segm = to_sitk(seg, sp, sitk.sitkUInt8); cavm = to_sitk(cav.astype(np.uint8), sp, sitk.sitkUInt8)
    heart = ndi.binary_dilation(myo | cav | allblood, iterations=int(np.ceil(10 / sp.mean())))
    hmask = to_sitk(heart.astype(np.uint8), sp, sitk.sitkUInt8)
    sig = (1.5 / 2.3548) / sp
    out = {"case": case.name, "spacing": sp.tolist(), "r_eq_mm": r_eq, "rows": []}
    for rep in range(reps):
        segs = rng.choice(np.arange(1, 17), 5, replace=False)
        taus = list(TAUS) + [float(rng.uniform(0.05, 1.0))]
        scar = np.zeros_like(myo)
        for s, tau in zip(segs, taus):
            scar |= myo & (seg == s) & (t < tau)
        motions = {"none": None, "e5": motion_field(myo.shape, sp, rng)}
        noise = rng.normal(0, 1, myo.shape).astype(np.float32)
        s0 = corrected_sdf(cav, sp)
        h = float(np.mean(sp))
        for e in PHASES:
            delta = e * r_eq
            fb, scar_src, truth_frac = phase_fields(myo, cav, scar, seg, s0, delta, sp)
            lv = myo | cav
            for mot, Dm in motions.items():
                tw = (lambda a, o: a) if Dm is None else (lambda a, o, Dm=Dm: warp(a, Dm, o))  # noqa: E731
                s_true = tw(s0, 1) + delta                   # the LIE's true endocardium is s_true = 0
                cache = {}
                for bname, bk in BLOOD_LEVELS.items():
                    for cnr in CNRS:
                        for scarred in (True, False):
                            base = np.where(ct < -200, ct, np.where(ct < -30, -80.0, 40 + 0.45 * (ct - 40))).astype(np.float32)
                            base[allblood & ~lv] = REMOTE + bk * D
                            wallv = np.where(scar_src & scarred, REMOTE + D, REMOTE).astype(np.float32)
                            lie = np.where(lv, fb * (REMOTE + bk * D) + (1 - fb) * wallv, base).astype(np.float32)
                            lie = tw(ndi.gaussian_filter(lie, 0.6), 1) + noise * (D / cnr)
                            img = ndi.gaussian_filter(lie, sig)
                            regs = ["R0"] if mot == "none" and e == 0 else ["R0", "R3"]
                            for reg in regs:
                                key = (bname, cnr, reg)
                                if scarred or key not in cache:
                                    if reg == "R0":
                                        wseg, wcav = seg, cav
                                    else:
                                        fixed = to_sitk(lie, sp)
                                        T = register(fixed, moving, "R3_rigid_heartmask", hmask)
                                        wseg = from_sitk(sitk.Resample(segm, fixed, T, sitk.sitkNearestNeighbor, 0))
                                        wcav = from_sitk(sitk.Resample(cavm, fixed, T, sitk.sitkNearestNeighbor, 0)) > 0
                                    cache[key] = (wseg, wcav)
                                wseg, wcav = cache[key]
                                sd_ = signed_endo_distance(wcav, sp)
                                row = {"rep": rep, "phase": e, "delta_mm": round(delta, 3), "motion": mot, "blood": bname,
                                       "cnr": cnr, "scarred": scarred, "reg": reg}
                                shell = np.abs(sd_) <= h / 2 + 1e-3
                                shell &= ndi.binary_dilation(wseg > 0, iterations=1)
                                # + = the carried endocardium lies inside the LIE's true wall (it misses subendocardium)
                                row["endo_signed_mm"] = float(np.mean(s_true[shell]))
                                row["endo_abs_mm"] = float(np.mean(np.abs(s_true[shell])))
                                q = qc(img, wseg, wcav)
                                g = grade(img, wseg, sd_)
                                if q is None or g is None:
                                    row["fail"] = True; out["rows"].append(row); continue
                                row.update({k: v for k, v in q.items() if k != "rs"})
                                near = nearest_segment(wseg, sp)
                                row["edge_offset_remote"] = edge_offset(img, wcav, wseg, sd_, q["rs"], near)
                                per = [edge_offset(img, wcav, wseg, sd_, [k], near) for k in range(1, 17)]
                                row["edge_offset_seg"] = [None if not np.isfinite(x) else round(x, 2) for x in per]
                                tf = truth_frac if scarred else np.zeros(16)
                                row["truth_frac"] = np.round(tf, 3).tolist()
                                row["pk"] = g["pk"].astype(int).tolist(); row["pg"] = g["pg"].astype(int).tolist()
                                row["ev"] = np.round(g["ev"], 3).tolist()
                                row["thr_k_sd"] = round(g["thr_k_minus_remote_sd"], 2)
                                out["rows"].append(row)
        print(case.name, "rep", rep, "done", flush=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data"); ap.add_argument("out"); ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--reps", type=int, default=2); ap.add_argument("--cases", nargs="*")
    a = ap.parse_args()
    cases = sorted(p for p in pathlib.Path(a.data).glob("s[0-9][0-9][0-9][0-9]") if p.is_dir())
    if a.cases:
        cases = [c for c in cases if c.name in a.cases]
    from janusm.guard import refuse
    refuse([c.name for c in cases], what="Kilo E8 run", source="TotalSegmentator")   # whole run refused on any hit
    t0 = time.time()
    with ProcessPoolExecutor(a.jobs) as ex:
        rows = list(ex.map(run_case, [(str(c), a.reps) for c in cases]))
    json.dump({"cases": rows, "seconds": round(time.time() - t0)}, open(a.out, "w"))
    print("done", round(time.time() - t0), "s")


if __name__ == "__main__":
    main()
