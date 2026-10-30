"""Shared synthetic-LIE benchmark: reference implementations of the JA29-JA30 menu, for scoring only.

These are benchmark implementations written from the ruling's text. The shipped modules are the role:swe issues
(JA35 items 1-2); they should reproduce these numbers on the benchmark, and this file is their test reference.

JA29 registration: the first-pass CT is moving, the LIE is fixed; grading is on the LIE grid. Mattes MI, the metric
masked (moving side) to JA1 classes 1-4 dilated 10 mm; rigid (Euler, centred on the heart), then affine from rigid.
A variant arm masks to classes 1-4 dilated 4 mm (rigid only), to test how much static chest the 10 mm margin admits.
Myocardium and cavity are carried by signed distance (linear), segments, depth u and column coordinates by nearest
neighbour.

QC on the smoothed LIE (Gaussian FWHM 1.5 mm), over the carried wall:
  fat_like     share < 0 HU (Juliet);
  blood_like   share > remote + 0.8 (blood - remote), blood = median of the carried cavity eroded 2 mm (Juliet);
  above_blood  share > blood median (Kilo);
  rim_dark     share of the carried cavity's 2 mm inner rim below (remote + blood) / 2: a candidate phase check.

JA30 Scar-0, common steps: smooth (FWHM 1.5 mm); core = carried wall eroded 1 voxel; remote = core voxels of the 6
lowest-median segments, median and robust SD 1.4826 MAD.
  P-K  >= 5 % of the segment's voxels above remote + 1/2 (p99 of the brightest segment's core - remote)
  P-J  E-D extent T >= tau (tau supplied by the caller: fitted on the other half of the hearts)
  P-G  >= 5 % above remote + 3 SD after a 1-voxel opening, ignoring 1 mm at the carried endocardium
  E-V  share of the segment's voxels above remote + 3 SD
  E-D  depth-binned extent of the same remote + 3 SD call (bench.depth_extent)
A present segment reads at least Kim bin 1.
"""
from __future__ import annotations

import numpy as np
import SimpleITK as sitk
from scipy import ndimage as ndi

from bench import A_RAS, G, _columns, depth_extent, volume_share

SM = 1.5 / 2.355


def fp_geometry(heart):
    """Geometry of the first-pass labels, computed once per heart (what registration carries)."""
    if "geo" not in heart:
        lab = heart["lab"]
        aha = G.aha17(lab, affine=A_RAS)
        if aha.segments is None:
            heart["geo"] = None
            return None
        phi, s = _columns(lab, aha)
        cav, mc = lab == G.LV, np.isin(lab, (G.MYO, G.LV))
        heart["geo"] = {
            "sd_cav": (ndi.distance_transform_edt(~cav) - ndi.distance_transform_edt(cav)).astype(np.float32),
            "sd_mc": (ndi.distance_transform_edt(~mc) - ndi.distance_transform_edt(mc)).astype(np.float32),
            "seg": np.nan_to_num(aha.segments).astype(np.float32),
            "u": np.nan_to_num(G.depth(lab, affine=A_RAS).u, nan=-1).astype(np.float32),
            "phi": phi, "s": s,
            "mask": ndi.binary_dilation(lab > 0, iterations=10).astype(np.uint8),     # JA29: classes 1-4 + 10 mm
            "mask4": ndi.binary_dilation(lab > 0, iterations=4).astype(np.uint8),     # variant: + 4 mm
            "centre": np.argwhere(lab > 0).mean(0)}
    return heart["geo"]


def _img(a):
    return sitk.GetImageFromArray(np.ascontiguousarray(np.asarray(a).transpose(2, 1, 0)))


def _arr(im):
    return sitk.GetArrayFromImage(im).transpose(2, 1, 0)


def register(lie, fp, geo, kind, init=None, seed=0, mask="mask"):
    fixed, moving = _img(lie.astype(np.float32)), _img(fp.astype(np.float32))
    r = sitk.ImageRegistrationMethod()
    r.SetMetricAsMattesMutualInformation(numberOfHistogramBins=50)
    r.SetMetricSamplingStrategy(r.RANDOM)
    r.SetMetricSamplingPercentage(0.05, seed)
    r.SetMetricMovingMask(_img(geo[mask]))
    r.SetInterpolator(sitk.sitkLinear)
    r.SetOptimizerAsRegularStepGradientDescent(learningRate=1.0, minStep=1e-3, numberOfIterations=300,
                                               relaxationFactor=0.5)
    r.SetOptimizerScalesFromPhysicalShift()
    r.SetShrinkFactorsPerLevel([2, 1])
    r.SetSmoothingSigmasPerLevel([1.0, 0.0])
    c = [float(x) for x in geo["centre"]]
    if kind == "rigid":
        tx = sitk.Euler3DTransform()
        tx.SetCenter(c)
    else:
        tx = sitk.AffineTransform(3)
        tx.SetCenter(c)
        if init is not None:
            A, c0, t0 = matrix_of(init)
            tx.SetCenter([float(x) for x in c0])
            tx.SetMatrix([float(x) for x in A.ravel()])
            tx.SetTranslation([float(x) for x in t0])
    r.SetInitialTransform(tx, inPlace=False)
    return r.Execute(fixed, moving)


def identity(geo):
    tx = sitk.Euler3DTransform()
    tx.SetCenter([float(x) for x in geo["centre"]])
    return tx


def matrix_of(tx):
    """T(x) = A (x - c) + c + t for Euler / affine (and their composite wrappers)."""
    t = tx
    while True:
        try:
            comp = sitk.CompositeTransform(t)
            if comp.GetNumberOfTransforms() == 1 and comp.GetNthTransform(0).GetName() != t.GetName():
                t = comp.GetNthTransform(0)
                continue
        except Exception:  # noqa: BLE001
            pass
        break
    for cast in (sitk.Euler3DTransform, sitk.AffineTransform):
        try:
            t = cast(t)
            break
        except Exception:  # noqa: BLE001
            continue
    A = np.array(t.GetMatrix()).reshape(3, 3)
    return A, np.array(t.GetCenter()), np.array(t.GetTranslation())


def carry(geo, tx, shape):
    ref = sitk.Image([int(x) for x in shape], sitk.sitkFloat32)

    def rs(a, interp, default):
        return _arr(sitk.Resample(_img(a), ref, tx, interp, default, sitk.sitkFloat32))
    cav = rs(geo["sd_cav"], sitk.sitkLinear, 99.0) < 0
    mc = rs(geo["sd_mc"], sitk.sitkLinear, 99.0) < 0
    myo = mc & ~cav
    seg = rs(geo["seg"], sitk.sitkNearestNeighbor, 0.0).astype(np.int16)
    u = rs(geo["u"], sitk.sitkNearestNeighbor, -1.0)
    u[~myo | (u < 0)] = np.nan
    seg[~myo] = 0
    return {"myo": myo, "cav": cav, "seg": seg, "u": u,
            "phi": rs(geo["phi"], sitk.sitkNearestNeighbor, 0.0), "s": rs(geo["s"], sitk.sitkNearestNeighbor, 0.0)}


def tre(tx, pts):
    """Mean distance (mm) between the estimated and the true LIE -> first-pass map, over (LIE point, true point)
    pairs sampled on the truth wall (bench.make_case's `tre_pts`)."""
    A, c, t = matrix_of(tx)
    x, x0 = pts
    est = (x - c) @ A.T + c + t
    return float(np.linalg.norm(est - x0, axis=1).mean())


def _remote(sm, core, seg):
    meds = []
    for k in range(1, 18):
        v = sm[core & (seg == k)]
        if v.size >= 10:
            meds.append((float(np.median(v)), k))
    meds.sort()
    low = [k for _, k in meds[:6]]
    rv = sm[core & np.isin(seg, low)]
    med = float(np.median(rv))
    rsd = float(1.4826 * np.median(np.abs(rv - med)))
    bright = meds[-1][1]
    return med, rsd, bright


def qc(sm, car, remote):
    wall = car["myo"]
    cav_core = ndi.binary_erosion(car["cav"], iterations=2)
    blood = float(np.median(sm[cav_core])) if cav_core.sum() > 50 else float("nan")
    w = sm[wall]
    out = {"fat_like": float((w < 0).mean()), "above_blood": float((w > blood).mean()), "blood_med": blood}
    out["blood_like"] = float((w > remote + 0.8 * (blood - remote)).mean()) if blood > remote + 5 else float("nan")
    # candidate phase check: the 2 mm inner rim of the carried cavity reading myocardium-dark
    rim = car["cav"] & ~ndi.binary_erosion(car["cav"], iterations=2)
    out["rim_dark"] = float((sm[rim] < (remote + blood) / 2).mean()) if rim.sum() > 50 else float("nan")
    return out


def grade(lie, car, fixed=None):
    """All menu values per segment 1-17 on one LIE image with carried geometry.

    fixed: the (remote, robust SD, P-K threshold) of another image. The scar-free twin is graded with the scarred
    image's constants, so the twin differs from the scarred image only by the scar signal: a twin call is then a call
    made by blood spill or noise, not by a re-fitted threshold (the spill share).
    """
    sm = ndi.gaussian_filter(lie, SM)
    myo, seg = car["myo"], car["seg"]
    core = ndi.binary_erosion(myo)
    if fixed is None:
        med, rsd, bright = _remote(sm, core, seg)
        thr_k = med + 0.5 * (np.percentile(sm[core & (seg == bright)], 99) - med)
    else:
        med, rsd, thr_k = fixed
    hi3 = (sm > med + 3 * rsd) & myo
    d_endo = ndi.distance_transform_edt(~car["cav"])
    g_call = ndi.binary_opening(hi3) & (d_endo >= 1.0)
    g_den = myo & (d_endo >= 1.0)
    pk, pg = np.full(17, np.nan), np.full(17, np.nan)
    for k in range(1, 18):
        m = myo & (seg == k)
        if m.sum() >= 20:
            pk[k - 1] = (sm[m] > thr_k).mean()
            d = g_den & (seg == k)
            pg[k - 1] = g_call[d].mean() if d.sum() >= 10 else np.nan
    return {"pk_share": pk, "pg_share": pg,
            "ev": volume_share(hi3, myo, seg),
            "ed": depth_extent(hi3, myo, seg, car["u"], car["phi"], car["s"]),
            "remote": med, "rsd": rsd, "thr_k": float(thr_k), "qc": qc(sm, car, med)}


def kim(x):
    x = np.nan_to_num(np.asarray(x, float))
    return np.select([x <= 0.005, x <= 0.25, x <= 0.50, x <= 0.75], [0, 1, 2, 3], 4)


def presence(g, tau):
    return {"P-K": g["pk_share"] >= 0.05, "P-J": np.nan_to_num(g["ed"]) >= tau, "P-G": g["pg_share"] >= 0.05}


def final_bin(present, extent):
    return np.where(present, np.maximum(kim(extent), 1), 0)
