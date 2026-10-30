"""Golf R2 E5: LIE-to-CCTA registration, and Kim-bin scar grading inside registered first-pass borders, on real anatomy.

Question (Round 1 ruling section 6 item 8): a late-iodine-enhancement (LIE) scan is a second acquisition, minutes after
the first-pass CCTA, in another breath-hold and often at another heart rate. Golf E3 (R1) showed the scar must be graded
inside the first-pass borders. Which registration carries those borders onto the LIE scan well enough for Kim bins,
and what scar-head rule grades best inside them?

Per case (public TotalSegmentator v2.0.1 gated-like cardiac CT that passes guard_r2; real CT and released labels):
  1. Crop the heart (+25 mm), resample to 1.0 mm. AHA segments and equal-thickness depth u from the labels.
  2. Place a subendocardial scar in one standard territory (LAD / LCx / RCA in turn): each of its segments gets a
     transmural depth drawn from the Kim-bin midpoints (0, 15, 35, 60, 90 %), with a smooth +-5 % jitter. Truth per
     segment = scar volume / myocardial volume, binned 0 | 1-25 | 26-50 | 51-75 | 76-100 %.
  3. Synthesise an LIE scan: remote myocardium 90 HU; scar 90+D; blood (every CT voxel > 200 HU outside the
     myocardium) 90+D, i.e. as bright as scar (the hard case, E3); fat (CT < -30) -80; everything else the real CT
     compressed to 35 %. PSF FWHM 1.0 mm; correlated noise (0.6 mm) with SD = D / CNR.
  4. Misalign the LIE scan by a known transform: rigid (translation t in a random direction, rotation up to r degrees
     per axis) + a scaling of 1+s along a random axis about the LV (a heart-rate / phase difference) + a smooth
     displacement field of RMS n mm (correlation 20 mm).  Levels: none; typical (4 mm, 2 deg, 3 %, 1 mm);
     large (8 mm, 4 deg, 6 %, 2 mm).  These levels are assumptions, stated as such in the note.
  5. Register the real first-pass CT (moving) to the LIE scan (fixed), Mattes mutual information, first-pass heart
     mask dilated 10 mm as the moving mask: identity (scanner coordinates); rigid; rigid+affine; rigid+affine+B-spline
     (30 mm control grid).  The first-pass myocardium, cavity and AHA map are warped onto the LIE grid.
  6. Grade every segment inside the warped borders:
       T  "threshold":       scar voxel = LIE > remote mean + 3 SD (remote = mid-wall of the 4 darkest segments);
                             transmurality = scar / myocardium per segment.
       P  "presence first":  as T, but a segment is scar-present only if, after a 1-voxel opening and leaving out the
                             1 mm next to the warped endocardium, >= 5 % of its voxels are scar; else bin 0.
  Outputs: endo/epi ASSD of the warped borders against the true ones (mm), and per-segment Kim-bin accuracy,
  linear-weighted kappa, scar-presence sensitivity and specificity.

Usage: python lie_reg.py <ts_dir> [--cases N] [--np 4]      writes lie_reg.json (CPU only)
"""
import argparse, json, sys, time
from multiprocessing import Pool
from pathlib import Path

import nibabel as nib
import numpy as np
import SimpleITK as sitk
from scipy import ndimage as ndi

sitk.ProcessObject_SetGlobalDefaultNumberOfThreads(1)   # one thread per worker; parallelism is across cases

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from guard_r2 import refuse  # noqa: E402
from layers_ts import LA, MYO, LV, RV, aha, aha_labels, depth  # noqa: E402

TERR = {"LAD": [1, 2, 7, 8, 13, 14, 17], "RCA": [3, 4, 9, 10, 15], "LCx": [5, 6, 11, 12, 16]}
KIM_MID = [0.0, 0.15, 0.35, 0.60, 0.90]
MIS = {"none": (0, 0, 0, 0), "typical": (4.0, 2.0, 0.03, 1.0), "large": (8.0, 4.0, 0.06, 2.0)}
REGS = ["identity", "rigid", "affine", "bspline"]
CNRS = [3.0, 5.0]
D = 60.0
GRADERS = ["T", "P", "T10", "T15", "T20"]


def kim(f):
    f = np.asarray(f) * 100
    return np.select([f <= 0.5, f <= 25, f <= 50, f <= 75], [0, 1, 2, 3], 4)


def wkappa(a, b, k=5):
    a, b = np.asarray(a), np.asarray(b)
    O = np.zeros((k, k))
    for i, j in zip(a, b):
        O[i, j] += 1
    W = np.abs(np.subtract.outer(np.arange(k), np.arange(k))) / (k - 1)
    E = np.outer(O.sum(1), O.sum(0)) / O.sum()
    return float(1 - (W * O).sum() / max((W * E).sum(), 1e-9))


def load_case(case_dir):
    refuse("TotalSegmentator-cardiac", case_dir.name)          # never opens a held-out case or twin
    ct = nib.load(case_dir / "ct.nii.gz")
    L = np.asanyarray(nib.load(case_dir / "cardiac_label.nii.gz").dataobj) > 0.5
    sp = np.array(ct.header.get_zooms()[:3], float)
    a = np.asanyarray(ct.dataobj).astype(np.float32)
    heart = L[MYO] | L[LV] | L[RV] | L[LA]
    nz = np.argwhere(heart)
    m = np.ceil(25 / sp).astype(int)
    lo, hi = np.maximum(nz.min(0) - m, 0), np.minimum(nz.max(0) + m + 1, heart.shape)
    sl = tuple(slice(x, y) for x, y in zip(lo, hi))
    z = sp / 1.0
    ctr = ndi.zoom(a[sl], z, order=1)
    lab = {}
    for k, c in (("la", LA), ("myo", MYO), ("cav", LV), ("rv", RV)):
        s = L[c][sl]
        f = ndi.distance_transform_edt(~s, sampling=sp) - ndi.distance_transform_edt(s, sampling=sp)
        lab[k] = ndi.zoom(f.astype(np.float32), z, order=1) < 0
    lab["myo"] &= ~lab["cav"]
    R = ct.affine[:3, :3] / np.linalg.norm(ct.affine[:3, :3], axis=0)
    return ctr, lab, R.T @ np.array([0.0, 1.0, 0.0])


def smooth(shape, corr, rng):
    f = ndi.gaussian_filter(rng.standard_normal(shape).astype(np.float32), corr)
    return f / (f.std() + 1e-9)


def make_lie(ct, lab, scar, cnr, rng):
    lie = 40 + 0.35 * (np.clip(ct, -300, 1200) - 40)
    lie[(ct < -30) & ~lab["myo"]] = -80
    lie[(ct > 200) & ~lab["myo"]] = 90 + D
    lie[lab["myo"]] = 90
    lie[scar] = 90 + D
    lie = ndi.gaussian_filter(lie, 1.0 / 2.355)
    return lie + smooth(ct.shape, 0.6 / 2.355 * 2, rng) * (D / cnr)


def misalign_field(shape, level, centre, rng):
    t, r, s, n = MIS[level]
    X = np.stack(np.meshgrid(*[np.arange(k, dtype=np.float32) for k in shape], indexing="ij"), -1)
    if t == 0 and n == 0:
        return X
    ang = np.radians(rng.uniform(-r, r, 3))
    cx, cy, cz = np.cos(ang); sx, sy, sz = np.sin(ang)
    Rm = (np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]) @ np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
          @ np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]))
    ax = rng.standard_normal(3); ax /= np.linalg.norm(ax)
    S = np.eye(3) + s * np.outer(ax, ax)
    tv = rng.standard_normal(3); tv = t * tv / np.linalg.norm(tv)
    A = Rm @ S
    Y = (X - centre) @ A.T + centre + tv
    for k in range(3):
        Y[..., k] += n * smooth(shape, 20.0, rng)
    return Y


def warp(a, Y, order):
    return ndi.map_coordinates(a, [Y[..., k] for k in range(3)], order=order, mode="nearest")


def warp_mask(m, Y):
    f = ndi.distance_transform_edt(~m) - ndi.distance_transform_edt(m)
    return warp(f.astype(np.float32), Y, 1) < 0


def img(a):
    return sitk.GetImageFromArray(np.ascontiguousarray(a.astype(np.float32)))


def register_all(fixed, moving, mmask):
    """identity, rigid, rigid+affine, rigid+affine+B-spline, each started from the previous one."""
    F, M = img(fixed), img(np.clip(moving, -200, 600))
    MM = sitk.Cast(img(mmask.astype(np.float32)), sitk.sitkUInt8)

    def run(tx, opt):
        R = sitk.ImageRegistrationMethod()
        R.SetMetricAsMattesMutualInformation(50)
        R.SetMetricSamplingStrategy(R.RANDOM); R.SetMetricSamplingPercentage(0.1, seed=7)
        R.SetMetricMovingMask(MM)
        R.SetInterpolator(sitk.sitkLinear)
        opt(R)
        R.SetShrinkFactorsPerLevel([4, 2, 1]); R.SetSmoothingSigmasPerLevel([2, 1, 0])
        R.SetInitialTransform(tx, inPlace=False)
        return R.Execute(F, M)

    def gd(R):
        R.SetOptimizerAsRegularStepGradientDescent(2.0, 1e-3, 200, relaxationFactor=0.6)
        R.SetOptimizerScalesFromPhysicalShift()
    init = sitk.CenteredTransformInitializer(F, M, sitk.Euler3DTransform(), sitk.CenteredTransformInitializerFilter.MOMENTS)
    init = sitk.Euler3DTransform(init)
    init.SetTranslation((0, 0, 0))     # start from scanner coordinates; keep only the centre of rotation
    rig = run(init, gd)
    aff0 = sitk.AffineTransform(3)
    rr = sitk.Euler3DTransform(sitk.CompositeTransform(rig).GetNthTransform(0)) if isinstance(rig, sitk.CompositeTransform) else sitk.Euler3DTransform(rig)
    aff0.SetCenter(rr.GetCenter()); aff0.SetMatrix(rr.GetMatrix()); aff0.SetTranslation(rr.GetTranslation())
    aff = run(aff0, gd)
    mesh = [max(int(s / 30), 1) for s in F.GetSize()]
    bs = sitk.BSplineTransformInitializer(F, mesh, order=3)
    comp = sitk.CompositeTransform(3); comp.AddTransform(aff); comp.AddTransform(bs)

    def lb(R):
        R.SetOptimizerAsLBFGSB(gradientConvergenceTolerance=1e-5, numberOfIterations=60, maximumNumberOfCorrections=5)
    R = sitk.ImageRegistrationMethod()
    R.SetMetricAsMattesMutualInformation(50)
    R.SetMetricSamplingStrategy(R.RANDOM); R.SetMetricSamplingPercentage(0.1, seed=7)
    R.SetMetricMovingMask(MM); R.SetInterpolator(sitk.sitkLinear); lb(R)
    R.SetShrinkFactorsPerLevel([2, 1]); R.SetSmoothingSigmasPerLevel([1, 0])
    R.SetMovingInitialTransform(aff)
    R.SetInitialTransform(bs, inPlace=True)
    R.Execute(F, M)
    comp = sitk.CompositeTransform(3); comp.AddTransform(aff); comp.AddTransform(bs)
    return {"identity": sitk.Transform(3, sitk.sitkIdentity), "rigid": rig, "affine": aff, "bspline": comp}


def resample(a, ref, tx, nearest=False):
    out = sitk.Resample(img(a), img(ref), tx, sitk.sitkNearestNeighbor if nearest else sitk.sitkLinear, float(a.min()))
    return sitk.GetArrayFromImage(out)


def surf_dist(a, b):
    sa, sb = a & ~ndi.binary_erosion(a), b & ~ndi.binary_erosion(b)
    da, db = ndi.distance_transform_edt(~sa), ndi.distance_transform_edt(~sb)
    sd = lambda m: (ndi.distance_transform_edt(~m) - 0.5) * ~m - (ndi.distance_transform_edt(m) - 0.5) * m
    # ASSD, and the signed bias of a's surface relative to b (> 0: a lies outside b), 0 for identical masks
    return float((db[sa].mean() + da[sb].mean()) / 2), float(np.mean(sd(b)[sa]) - np.mean(sd(a)[sa]))


def grade(lie, myo, cav, seg):
    u = depth(myo, cav, np.ones(3))
    mid = myo & (u >= 1 / 3) & (u < 2 / 3)
    med = [np.median(lie[mid & (seg == k)]) if (mid & (seg == k)).sum() > 20 else np.inf for k in range(1, 17)]
    rem = np.zeros_like(myo)
    for k in np.argsort(med)[:4]:
        rem |= mid & (seg == k + 1)
    mu, sd = lie[rem].mean(), lie[rem].std()
    sc = myo & (lie > mu + 3 * sd)
    core = ndi.binary_opening(sc) & (ndi.distance_transform_edt(~cav) > 1.0)
    T, P = [], []
    for k in range(1, 18):
        m = myo & (seg == k)
        n = max(m.sum(), 1)
        f = sc[m].sum() / n
        T.append(f)
        P.append(f if core[m].sum() / n >= 0.05 else 0.0)
    T = np.array(T)
    return {"T": T, "P": np.array(P), "T10": np.where(T >= 0.10, T, 0.0), "T15": np.where(T >= 0.15, T, 0.0),
            "T20": np.where(T >= 0.20, T, 0.0)}


def run_case(args):
    case_dir, idx = args
    t0 = time.time()
    rng = np.random.default_rng(20261030 + idx)
    ct, lab, ant = load_case(case_dir)
    myo, cav = lab["myo"], lab["cav"]
    geom, diag = aha(myo, cav, lab["rv"], lab["la"], np.ones(3))
    if geom is None:
        return case_dir.name, {"error": diag}
    seg = aha_labels(myo, geom, ant)
    u = depth(myo, cav, np.ones(3))
    terr = list(TERR)[idx % 3]
    tgt = np.zeros(18)
    for k in TERR[terr]:
        tgt[k] = rng.choice(KIM_MID)
    jit = 0.05 * smooth(myo.shape, 8.0, rng)
    scar = myo & (u < tgt[seg] + jit) & (tgt[seg] > 0)
    truth = np.array([scar[seg == k].sum() / max((seg == k).sum(), 1) for k in range(1, 18)])
    tb = kim(truth)
    heart = myo | cav | lab["rv"] | lab["la"]
    mmask = ndi.binary_dilation(heart, iterations=10)
    centre = np.argwhere(myo | cav).mean(0)
    out = {"territory": terr, "truth_bins": tb.tolist(), "runs": []}
    for level in MIS:
        Y = misalign_field(myo.shape, level, centre, rng)
        myo_t, cav_t = warp_mask(myo, Y), warp_mask(cav, Y)
        epi_t = myo_t | cav_t
        seg_t = warp(seg.astype(np.float32), Y, 0).astype(np.uint8) * myo_t
        scar_t = warp_mask(scar, Y) & myo_t
        for cnr in CNRS:
            lie = make_lie(warp(ct, Y, 1), {"myo": myo_t}, scar_t, cnr, rng)
            # NB the LIE background is the real CT warped by Y; the first-pass CT is the moving image
            txs = register_all(lie, ct, mmask) if level != "none" else {"identity": sitk.Transform(3, sitk.sitkIdentity)}
            for reg, tx in txs.items():
                myo_w = resample(myo.astype(np.float32), lie, tx) > 0.5
                cav_w = resample(cav.astype(np.float32), lie, tx) > 0.5
                seg_w = resample(seg.astype(np.float32), lie, tx, nearest=True).astype(np.uint8)
                myo_w &= ~cav_w
                endo, endo_b = surf_dist(cav_w, cav_t)
                epi, epi_b = surf_dist(myo_w | cav_w, epi_t)
                G = grade(lie, myo_w, cav_w, seg_w * myo_w)
                r = {"mis": level, "cnr": cnr, "reg": reg, "assd_endo": endo, "assd_epi": epi,
                     "bias_endo": endo_b, "bias_epi": epi_b}
                for name, g in G.items():
                    gb = kim(g)
                    r[name] = {"acc": float((gb == tb).mean()), "bins": gb.tolist(), "frac": g.round(4).tolist(),
                               "mae_pp": float(np.abs(g - truth).mean() * 100)}
                out["runs"].append(r)
        print(case_dir.name, level, f"{time.time() - t0:.0f}s", flush=True)
    out["truth_frac"] = truth.round(3).tolist()
    return case_dir.name, out


def summarise(res):
    rows = {}
    for c, o in res.items():
        if "runs" not in o:
            continue
        tb = np.array(o["truth_bins"])
        for r in o["runs"]:
            k = (r["mis"], r["cnr"], r["reg"])
            d = rows.setdefault(k, {"endo": [], "epi": [], "bendo": [], "bepi": [], "tb": [], **{g: [] for g in GRADERS}})
            d["endo"].append(r["assd_endo"]); d["epi"].append(r["assd_epi"])
            d["bendo"].append(r["bias_endo"]); d["bepi"].append(r["bias_epi"])
            d["tb"] += tb.tolist()
            for g in GRADERS:
                d[g] += r[g]["bins"]
    out = []
    for (mis, cnr, reg), d in rows.items():
        tb = np.array(d["tb"])
        row = {"mis": mis, "cnr": cnr, "reg": reg, "n_cases": len(d["endo"]), "n_segments": int(tb.size),
               "assd_endo_median": float(np.median(d["endo"])), "assd_epi_median": float(np.median(d["epi"])),
               "assd_endo_p90": float(np.percentile(d["endo"], 90)), "assd_epi_p90": float(np.percentile(d["epi"], 90)),
               "bias_endo_median": float(np.median(d["bendo"])), "bias_epi_median": float(np.median(d["bepi"]))}
        for g in GRADERS:
            gb = np.array(d[g])
            pos = tb > 0
            row[g] = {"kim_acc": float((gb == tb).mean()), "wkappa": wkappa(tb, gb),
                      "presence_sens": float((gb[pos] > 0).mean()), "presence_spec": float((gb[~pos] == 0).mean()),
                      "scarfree_called_scar": int((gb[~pos] > 0).sum())}
        out.append(row)
    order = {m: i for i, m in enumerate(MIS)}
    return sorted(out, key=lambda r: (order[r["mis"]], r["cnr"], REGS.index(r["reg"])))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("ts_dir", type=Path)
    ap.add_argument("--cases", type=int, default=0)
    ap.add_argument("--np", type=int, default=4)
    a = ap.parse_args()
    ids = sorted(json.loads((HERE / "ts_cases_r2.json").read_text()))
    if a.cases:
        ids = ids[:a.cases]
    jobs = [(a.ts_dir / i, n) for n, i in enumerate(ids)]
    part = HERE / "lie_reg_partial.json"
    res = json.loads(part.read_text()) if part.exists() else {}
    jobs = [j for j in jobs if j[0].name not in res]
    with Pool(a.np) as p:
        for name, o in p.imap_unordered(run_case, jobs, chunksize=1):
            res[name] = o
            part.write_text(json.dumps(res) + "\n")       # resumable: a finished case is never recomputed
    s = summarise(res)
    (HERE / "lie_reg.json").write_text(json.dumps({"summary": s, "cases": res}, indent=1) + "\n")
    for r in s:
        print(r["mis"], r["cnr"], r["reg"], f"endo {r['assd_endo_median']:.2f} epi {r['assd_epi_median']:.2f}",
              {g: {k: round(v, 3) for k, v in r[g].items()} for g in GRADERS})
