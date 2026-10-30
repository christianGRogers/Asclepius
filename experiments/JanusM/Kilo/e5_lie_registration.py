"""E5 (Kilo v2): registering first-pass borders to a late-enhancement CT, and grading scar inside them.

Path B grades late iodine enhancement (LIE) inside the first-pass (CCTA) borders, registered to the LIE scan (JA11;
Golf E3: an LIE-only reader scores 0.20 Kim-bin accuracy). This asks, on real anatomy:
  1. how far each registration method leaves the borders from their true position on the LIE scan, and
  2. what that costs the per-segment scar call and its Kim bin (0; 1-25; 26-50; 51-75; 76-100 %).

Data: the open public TotalSegmentator v1 cardiac CTs (Zenodo 6802614, CC BY 4.0; model-made heart masks at 1.5 mm).
Every case passes heldout.check_public (held-out pool patients and JA12 twins refused) before any file is opened.

Per case:
  * first pass = the real CT and its masks. Scars are placed in 5 segments of 1-16 (depth tau in 0.15, 0.40, 0.65,
    0.90 and one random), subendocardial: wall voxels of that segment with distance depth < tau. Reference bin =
    the scar's volume share of its segment (the LGE analogue). The other segments are scar-free;
  * a synthetic LIE scan in the same patient: the CT warped by a known motion (rigid, rotation N(0, 3 deg) and
    translation N(0, 4 mm) per axis, for a second breath-hold; plus a smooth non-rigid field, RMS 1.5 mm, 20 mm
    correlation, for a different R-R phase), with LIE contrast: blood 110 HU, remote myocardium 85 HU, scar 150 HU,
    other soft tissue compressed toward 40 HU, lung and air unchanged; blurred (0.6 voxel) and noise 18 HU;
  * registration of the CT (moving) to the LIE scan (fixed), Mattes mutual information, heart crop:
      R0 none (scanner coordinates); R1 rigid; R2 rigid + affine; R3 rigid with the metric restricted to the
      first-pass heart (chambers + wall dilated 10 mm); R4 R3 + a coarse B-spline (about 50 mm control spacing);
    and the oracle (the true warp) to isolate grading error from registration error;
  * grading inside the warped wall, per segment, after 1-voxel Gaussian smoothing:
      G2 / G3 / G5: voxel > remote median + n robust SD (remote = core voxels, >= 1 voxel inside both borders, of the
      6 segments with the lowest core median);
      GF: FWHM, voxel > remote + half of (99th percentile of the brightest segment's core - remote);
    a segment is "scar" when >= 5 % of its voxels pass ("presence first", Juliet E3), then binned by the share.
Outputs: endocardial and epicardial ASSD (mm) per method, segment sensitivity / specificity, Kim-bin agreement and
the SD of transmurality error among true-scar segments (E6's sd_s).

Usage: python e5_lie_registration.py DATA_DIR OUT_JSON [--jobs 4] [--reps 1]
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

BLOOD = ("heart_ventricle_left", "heart_ventricle_right", "heart_atrium_left", "heart_atrium_right", "aorta")
KIM = np.array([0.0, 0.25, 0.50, 0.75])
TAUS = (0.15, 0.40, 0.65, 0.90)
METHODS = ("oracle", "R0_none", "R1_rigid", "R2_affine", "R3_rigid_heartmask", "R4_heartmask_bspline")
GRADERS = {"G2": 2.0, "G3": 3.0, "G5": 5.0, "GF": None}
META = None


def kim_bin(frac, present):
    return np.where(present, np.digitize(np.clip(frac, 1e-9, 1), KIM[1:]) + 1, 0)


def surface(m):
    return m & ~ndi.binary_erosion(m)


def assd(a, b, sp):
    """Symmetric mean surface distance (mm) between two masks' surfaces."""
    sa, sb = surface(a), surface(b)
    if not sa.any() or not sb.any():
        return float("nan")
    da = ndi.distance_transform_edt(~sb, sampling=sp)[sa]
    db = ndi.distance_transform_edt(~sa, sampling=sp)[sb]
    return float((da.sum() + db.sum()) / (len(da) + len(db)))


def endo_surface(myo, cav):
    return myo & ndi.binary_dilation(cav)


def surf_dist(sa, sb, sp):
    if not sa.any() or not sb.any():
        return float("nan")
    da = ndi.distance_transform_edt(~sb, sampling=sp)[sa]
    db = ndi.distance_transform_edt(~sa, sampling=sp)[sb]
    return float((da.sum() + db.sum()) / (len(da) + len(db)))


def to_sitk(a, sp, dtype=sitk.sitkFloat32):
    im = sitk.GetImageFromArray(np.ascontiguousarray(np.transpose(a, (2, 1, 0))))   # numpy x,y,z -> sitk
    im.SetSpacing([float(s) for s in sp])
    return sitk.Cast(im, dtype)


def from_sitk(im):
    return np.transpose(sitk.GetArrayFromImage(im), (2, 1, 0))


def motion_field(shape, sp, rng):
    """Displacement (voxels) = rigid (breath-hold) + smooth non-rigid (phase)."""
    c = (np.array(shape) - 1) / 2
    ang = np.radians(rng.normal(0, 3, 3))
    cx, cy, cz = np.cos(ang); sx, sy, sz = np.sin(ang)
    R = (np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]) @ np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
         @ np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]))
    tr = rng.normal(0, 4, 3)                                                     # mm
    g = np.stack(np.meshgrid(*[np.arange(n) for n in shape], indexing="ij"), -1).astype(np.float32)
    p_mm = (g - c) * sp
    rigid = (p_mm @ R.T - p_mm + tr) / sp
    nr = np.stack([ndi.gaussian_filter(rng.standard_normal(shape).astype(np.float32), 20 / sp[i] / 2)
                   for i in range(3)], -1)
    nr = nr / np.sqrt((nr ** 2).sum(-1).mean()) * 1.5 / sp
    return (rigid + nr).astype(np.float32)


def warp(a, D, order):
    g = np.stack(np.meshgrid(*[np.arange(n) for n in a.shape], indexing="ij"), 0).astype(np.float32)
    return ndi.map_coordinates(a, g + np.moveaxis(D, -1, 0), order=order, mode="nearest")


def register(fixed, moving, kind, heart_mask=None):
    """Moving = first-pass CT, fixed = LIE. heart_mask (moving space) restricts the metric for R3 / R4."""
    if kind == "R0_none":
        return sitk.Transform(3, sitk.sitkIdentity)
    masked = kind in ("R3_rigid_heartmask", "R4_heartmask_bspline")
    def method(levels=(4, 2, 1), sig=(2, 1, 0)):
        r = sitk.ImageRegistrationMethod()
        r.SetMetricAsMattesMutualInformation(48)
        r.SetMetricSamplingStrategy(r.RANDOM); r.SetMetricSamplingPercentage(0.15, seed=7)
        r.SetInterpolator(sitk.sitkLinear)
        r.SetShrinkFactorsPerLevel(list(levels)); r.SetSmoothingSigmasPerLevel(list(sig))
        if masked:
            r.SetMetricMovingMask(heart_mask)
        return r
    rig = sitk.CenteredTransformInitializer(fixed, moving, sitk.Euler3DTransform(),
                                            sitk.CenteredTransformInitializerFilter.GEOMETRY)
    r = method(); r.SetOptimizerAsRegularStepGradientDescent(2.0, 1e-3, 200, relaxationFactor=0.6)
    r.SetOptimizerScalesFromPhysicalShift(); r.SetInitialTransform(rig, inPlace=False)
    rig = r.Execute(fixed, moving)
    if kind in ("R1_rigid", "R3_rigid_heartmask"):
        return rig
    if kind == "R2_affine":
        aff = sitk.AffineTransform(3)
        r = method(); r.SetOptimizerAsRegularStepGradientDescent(1.0, 1e-3, 200, relaxationFactor=0.6)
        r.SetOptimizerScalesFromPhysicalShift(); r.SetMovingInitialTransform(rig)
        r.SetInitialTransform(aff, inPlace=False)
        aff = r.Execute(fixed, moving)
        return sitk.CompositeTransform([rig, aff])
    # R4: coarse B-spline (about 50 mm control spacing) on top of the masked rigid, two levels, 40 iterations
    mesh = [max(2, int(round(sz * sp / 50))) for sz, sp in zip(fixed.GetSize(), fixed.GetSpacing())]
    bs = sitk.BSplineTransformInitializer(fixed, mesh)
    r = method((2, 1), (1, 0))
    r.SetOptimizerAsGradientDescentLineSearch(1.0, 40, convergenceMinimumValue=1e-5, convergenceWindowSize=5)
    r.SetOptimizerScalesFromPhysicalShift()
    r.SetMovingInitialTransform(rig); r.SetInitialTransform(bs, inPlace=True)
    r.Execute(fixed, moving)
    return sitk.CompositeTransform([rig, bs])


def grade(lie_s, wall_seg, n_sd):
    """Per-segment scar share in [0, 1] and presence, from the LIE image inside a (warped) segment map.
    Remote statistics come from core wall voxels (>= 1 voxel from either border), so partial volume with blood, fat
    or lung does not inflate them; SD is robust (1.4826 MAD). The threshold is applied to every wall voxel."""
    wall = wall_seg > 0
    core = ndi.binary_erosion(wall)
    med = {s: np.median(lie_s[core & (wall_seg == s)]) for s in range(1, 17) if (core & (wall_seg == s)).sum() > 20}
    if len(med) < 8:
        return np.full(16, np.nan), np.zeros(16, bool)
    remote_segs = sorted(med, key=med.get)[:6]
    rem = lie_s[core & np.isin(wall_seg, remote_segs)]
    mu = np.median(rem); sd = 1.4826 * np.median(np.abs(rem - mu))
    if n_sd is None:      # FWHM: half way between remote and the brightest segment's core maximum (99th pct)
        top = max(med, key=med.get)
        thr = mu + 0.5 * (np.percentile(lie_s[core & (wall_seg == top)], 99) - mu)
    else:
        thr = mu + n_sd * sd
    frac = np.full(16, np.nan)
    for s in range(1, 17):
        m = wall_seg == s
        if m.sum() > 20:
            frac[s - 1] = (lie_s[m] > thr).mean()
    return frac, frac >= 0.05


def run_case(args):
    case, reps = args
    from heldout import check_public
    check_public(pathlib.Path(case).name, META_TEXT)          # refuse before any file of the case is opened
    case = pathlib.Path(case)
    rng = np.random.default_rng(int(case.name[1:]) + 5)
    rd = lambda k: np.asanyarray(nib.load(case / f"segmentations/{k}.nii.gz").dataobj) > 0
    myo, cav = rd("heart_myocardium"), rd("heart_ventricle_left")
    if myo.sum() < 1000 or cav.sum() < 1000:
        return {"case": case.name, "skip": "no LV myocardium / cavity in mask"}
    ctn = nib.load(case / "ct.nii.gz"); ct = np.asanyarray(ctn.dataobj).astype(np.float32)
    sp = np.array(ctn.header.get_zooms()[:3], float)
    blood = {k: rd(k) for k in BLOOD}
    la = blood["heart_atrium_left"]; rv = blood["heart_ventricle_right"]
    if float(np.median(ct[cav])) < 150:
        return {"case": case.name, "skip": "no contrast in the LV blood pool"}
    # heart crop with a 30 mm margin
    box = myo | cav
    m = np.ceil(30 / sp).astype(int)
    lo = np.maximum(np.argwhere(box).min(0) - m, 0); hi = np.minimum(np.argwhere(box).max(0) + m + 1, box.shape)
    sl = tuple(slice(a, b) for a, b in zip(lo, hi))
    ct, myo, cav, la, rv = ct[sl], myo[sl], cav[sl], la[sl], rv[sl]
    allblood = np.zeros_like(myo)
    for k in BLOOD:
        allblood |= blood[k][sl]
    allblood &= ~myo
    aff = ctn.affine.copy(); aff[:3, 3] = aff[:3, :3] @ lo + aff[:3, 3]
    nf = la | blood["aorta"][sl]
    t, thick = distance_depth(myo, cav, nf, sp)
    seg, _ = aha17(myo, cav, rv, la, aff)
    out = {"case": case.name, "spacing": sp.tolist(), "wall_mm_median": float(np.nanmedian(thick[myo])), "reps": []}
    for rep in range(reps):
        # scars
        segs = rng.choice(np.arange(1, 17), 5, replace=False)
        taus = list(TAUS) + [float(rng.uniform(0.05, 1.0))]
        scar = np.zeros_like(myo)
        for s, tau in zip(segs, taus):
            scar |= myo & (seg == s) & (t < tau)
        ref_frac = np.array([(scar & (seg == s)).sum() / max((seg == s).sum(), 1) for s in range(1, 17)])
        ref_bin = kim_bin(ref_frac, ref_frac > 0)
        # synthetic LIE in first-pass space, then moved
        lie = np.where(ct < -200, ct, 40 + 0.45 * (ct - 40))
        lie[allblood] = 110; lie[myo] = 85; lie[scar] = 150
        D = motion_field(myo.shape, sp, rng)
        lie_w = warp(ndi.gaussian_filter(lie, 0.6), D, 1) + rng.normal(0, 18, myo.shape).astype(np.float32)
        lie_s = ndi.gaussian_filter(lie_w, 1.0)
        true_seg = warp(seg, D, 0); true_cav = warp(cav.astype(np.uint8), D, 0) > 0
        true_myo = true_seg > 0
        fixed = to_sitk(lie_w, sp); moving = to_sitk(np.clip(ct, -300, 800), sp)
        segm = to_sitk(seg, sp, sitk.sitkUInt8); cavm = to_sitk(cav.astype(np.uint8), sp, sitk.sitkUInt8)
        heart = ndi.binary_dilation(myo | cav | allblood, iterations=int(np.ceil(10 / sp.mean())))
        hmask = to_sitk(heart.astype(np.uint8), sp, sitk.sitkUInt8)
        r = {"scar_segments": [int(s) for s in segs], "ref_frac": ref_frac.round(3).tolist(), "methods": {}}
        for meth in METHODS:
            if meth == "oracle":
                wseg, wcav = true_seg, true_cav
            else:
                t0 = time.time()
                T = register(fixed, moving, meth, hmask)
                secs = time.time() - t0
                wseg = from_sitk(sitk.Resample(segm, fixed, T, sitk.sitkNearestNeighbor, 0))
                wcav = from_sitk(sitk.Resample(cavm, fixed, T, sitk.sitkNearestNeighbor, 0)) > 0
            wmyo = wseg > 0
            e = {"seconds": 0.0 if meth == "oracle" else round(secs, 1),
                 "endo_assd_mm": surf_dist(endo_surface(wmyo, wcav), endo_surface(true_myo, true_cav), sp),
                 "myo_assd_mm": assd(wmyo, true_myo, sp),
                 "myo_dice": float(2 * (wmyo & true_myo).sum() / (wmyo.sum() + true_myo.sum())),
                 "wall_blood_share": float((wmyo & warp(allblood.astype(np.uint8), D, 0).astype(bool)).sum() / wmyo.sum())}
            for g, n_sd in GRADERS.items():
                frac, pres = grade(lie_s, wseg, n_sd)
                b = kim_bin(np.nan_to_num(frac), pres)
                e[g] = {"bin": b.tolist(), "frac": np.round(frac, 3).tolist()}
            r["methods"][meth] = e
        out["reps"].append(r)
    return out


def summarise(rows):
    S = {}
    for meth in METHODS:
        geo = {k: [] for k in ("seconds", "endo_assd_mm", "myo_assd_mm", "myo_dice", "wall_blood_share")}
        gr = {g: {"tp": 0, "fn": 0, "tn": 0, "fp": 0, "agree": 0, "n": 0, "err": [], "agree_scar": 0, "n_scar": 0}
              for g in GRADERS}
        for row in rows:
            for r in row.get("reps", []):
                e = r["methods"][meth]
                for k in geo:
                    geo[k].append(e[k])
                ref_frac = np.array(r["ref_frac"]); ref_bin = kim_bin(ref_frac, ref_frac > 0)
                for g in GRADERS:
                    b = np.array(e[g]["bin"]); f = np.array(e[g]["frac"], float)
                    ok = ~np.isnan(f); pos = ref_bin > 0
                    G = gr[g]
                    G["tp"] += int((pos & (b > 0) & ok).sum()); G["fn"] += int((pos & (b == 0) & ok).sum())
                    G["tn"] += int((~pos & (b == 0) & ok).sum()); G["fp"] += int((~pos & (b > 0) & ok).sum())
                    G["agree"] += int(((b == ref_bin) & ok).sum()); G["n"] += int(ok.sum())
                    both = pos & (b > 0) & ok
                    G["agree_scar"] += int((b[both] == ref_bin[both]).sum()); G["n_scar"] += int(both.sum())
                    G["err"] += (f[both] - ref_frac[both]).tolist()
        S[meth] = {k: {"median": float(np.nanmedian(v)), "p90": float(np.nanpercentile(v, 90))} for k, v in geo.items()}
        for g, G in gr.items():
            S[meth][g] = {"sens": G["tp"] / max(G["tp"] + G["fn"], 1), "spec": G["tn"] / max(G["tn"] + G["fp"], 1),
                          "kim_bin_agreement_all": G["agree"] / max(G["n"], 1),
                          "kim_bin_agreement_scar_on_both": G["agree_scar"] / max(G["n_scar"], 1),
                          "transmurality_error_sd": float(np.std(G["err"])) if G["err"] else None,
                          "transmurality_error_mean": float(np.mean(G["err"])) if G["err"] else None,
                          "n_segments": G["n"], "n_scar_segments": G["tp"] + G["fn"]}
    return S


def init(meta_text):
    global META_TEXT
    META_TEXT = meta_text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data"); ap.add_argument("out"); ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--reps", type=int, default=1); ap.add_argument("--meta", required=True)
    a = ap.parse_args()
    meta = open(a.meta).read()
    from heldout import refused_with_twins
    direct, twins = refused_with_twins(meta)
    cases = sorted(p for p in pathlib.Path(a.data).glob("s[0-9][0-9][0-9][0-9]") if p.is_dir())
    bad = [c.name for c in cases if c.name in direct | twins]
    if bad:
        raise SystemExit(f"refusing the whole run: held-out or twin cases present on disk: {bad}")
    sitk.ProcessObject.SetGlobalDefaultNumberOfThreads(1)
    with ProcessPoolExecutor(a.jobs, initializer=init, initargs=(meta,)) as ex:
        rows = []
        for row in ex.map(run_case, [(str(c), a.reps) for c in cases]):
            print(row["case"], row.get("skip", "ok"), flush=True); rows.append(row)
    json.dump({"cases": rows, "summary": summarise(rows), "n_cases": sum("reps" in r for r in rows),
               "refused_direct": len(direct), "refused_twins": len(twins)}, open(a.out, "w"), indent=1)
    print(json.dumps(summarise(rows), indent=1))


if __name__ == "__main__":
    main()
