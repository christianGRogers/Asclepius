"""Golf R3 E8 + E9: every JA30 Scar-0 candidate and the JA29 chain on real hearts, the spill share of P-G, and a
truth-free phase-mismatch check.

Round 2 ruling (paired-scar) section 7 items 1 and 5. This is Golf's run on its own 22 hearts; the shared benchmark
(`experiments/JanusM/bench_lie/`, built by Juliet, #179) is the common ground, and this script is ported onto it
when it lands.

Per heart (public TotalSegmentator v2.0.1 gated-like CT, released labels; janusm.guard.refuse runs on the whole
list and again on each id before its first byte is read):
  1. Crop the heart (+25 mm), 1.0 mm grid; AHA segments, equal-thickness depth u, long-axis position s and angle
     from the labels (Golf R2 layers_ts.py).
  2. A subendocardial-to-transmural scar in one territory (LAD / RCA / LCx in turn); each segment's depth drawn from
     the Kim-bin midpoints (0, 15, 35, 60, 90 %) with a smooth +-5 % jitter. Truth per segment, both ways:
       vol   = scar voxels / segment voxels (Kilo, Golf);
       depth = Juliet's chord measure: per 3 deg x 2 mm column, 10 bins of u, the share of bins > half scar,
               averaged over columns with >= 6 bins.
  3. LIE: remote myocardium 90 HU, scar 150 (D = 60), blood (CT > 200 HU outside the myocardium) at
       below 120 | equal 150 | above 180; fat -80; the rest the real CT compressed to 35 %. PSF FWHM 1 mm;
       correlated noise SD D / CNR, CNR 3 | 5.
     Each LIE is also made, with the same noise, (i) without scar (a scar-free heart) and (ii) with blood set to
     remote (90 HU, the spill counterfactual), and (iii) both.
  4. Motion of the LIE against the first pass (stated assumptions):
       chest  : the whole image moves: 4 mm, 2 deg, 3 % scale along a random axis, 1 mm smooth field (Golf R2);
       static : the same motion applied to the heart only (weight 1 within 5 mm of the heart, 0 beyond 25 mm),
                chest, spine and lungs static (Juliet E6);
       phase5 : chest motion plus a 5 % cardiac-phase change: in the short-axis plane the endocardial radius
                shrinks by 5 % and the wall keeps its area (incompressible), which no rigid or affine map undoes.
  5. JA29 chain, first-pass CT moving, LIE fixed, Mattes MI with the metric masked to classes 1-4 dilated 10 mm:
       R0 (scanner coordinates, i.e. identity on the shared grid); rigid; affine (from rigid).  For `static` also an
       unmasked rigid, to show what the mask is for.  Myocardium and cavity carried through signed distances;
       segments, u, s and angle by nearest neighbour.  Also `exact`: the true moved borders (no registration error).
  6. Scar-0, JA30 constants exactly: LIE smoothed FWHM 1.5 mm; remote = core voxels (>= 1 voxel inside both carried
     borders) of the 6 lowest-median segments, median and 1.4826 MAD.  Per segment it stores:
       pk  = share of voxels > remote + 1/2 (p99 of the brightest segment's core - remote)       (P-K)
       pg  = share of voxels, after a 1-voxel opening of (> remote + 3 SD), more than 1 mm from the carried
             endocardium                                                                           (P-G)
       ev  = share of voxels > remote + 3 SD                                                       (E-V)
       ed  = Juliet's chord extent with the P-K half-way voxel threshold                           (E-D, P-J's T)
       ed3 = the same chord extent with the remote + 3 SD voxel threshold                          (E-D variant)
     Presence and bins are decided in lie_menu_summary.py (P-J's tau from the other half of the hearts).
  7. QC with no truth, per carried geometry: fat-like share of the wall (smoothed LIE < 0 HU, Juliet); the share of
     the wall brighter than the LIE blood median (Kilo); blood-like share (> remote + 0.8 (blood - remote), Juliet);
     and E9's edge offsets: per segment the signed distance from the carried endocardium (epicardium) to the LIE's
     half-maximum edge, median over segments, and the wall-thickness mismatch dthick = epi offset - endo offset.
     Truth (never used by a rule): endocardial / epicardial ASSD of the carried borders against the moved ones.

Usage: PYTHONPATH=<repo>/src python lie_menu.py <ts_dir> [--cases N] [--np 4]
Writes lie_menu_partial.json (per case, resumable; not committed). CPU only.
"""
import argparse, json, sys, time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import SimpleITK as sitk
from scipy import ndimage as ndi

from janusm.guard import GUARD_VERSION, refuse as jrefuse

sitk.ProcessObject_SetGlobalDefaultNumberOfThreads(1)
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from layers_ts import aha, aha_labels, depth  # noqa: E402
from lie_reg import KIM_MID, MIS, TERR, img, load_case, smooth  # noqa: E402

REMOTE, D = 90.0, 60.0
BLOOD = {"below": REMOTE + 0.5 * D, "equal": REMOTE + D, "above": REMOTE + 1.5 * D}
CNRS = (3.0, 5.0)
MOTIONS = ("chest", "static", "phase5")
VARIANTS = ("scar", "noscar", "scar_nb", "noscar_nb")      # nb = blood set to remote (spill counterfactual)
FIELDS = ("pk", "pg", "ev", "ed", "ed3")


def guarded_ids():
    ids = sorted(json.loads((HERE / "ts_cases_r2.json").read_text()))
    jrefuse([f"TotalSegmentator-cardiac__{i}" for i in ids], what="Golf R3 E8 case list")
    return ids


# ---------------------------------------------------------------------------------------------- motion
def rigid_scale(shape, centre, rng):
    t, r, s, n = MIS["typical"]
    X = np.stack(np.meshgrid(*[np.arange(k, dtype=np.float32) for k in shape], indexing="ij"), -1)
    ang = np.radians(rng.uniform(-r, r, 3))
    cx, cy, cz = np.cos(ang); sx, sy, sz = np.sin(ang)
    Rm = (np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]) @ np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
          @ np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]))
    ax = rng.standard_normal(3); ax /= np.linalg.norm(ax)
    A = Rm @ (np.eye(3) + s * np.outer(ax, ax))
    tv = rng.standard_normal(3); tv = t * tv / np.linalg.norm(tv)
    Y = (X - centre) @ A.T + centre + tv
    for k in range(3):
        Y[..., k] += n * smooth(shape, 20.0, rng)
    return X, Y


def phase_field(X, myo, cav, k=0.95):
    """Map LIE-grid points to first-pass points for a cavity whose short-axis radius is k x the first pass's, with
    the wall area kept (r_fp^2 = r^2 + (1 - k^2) Re^2 outside the cavity, r_fp = r / k inside)."""
    P = np.argwhere(myo | cav).astype(np.float32)
    c = P.mean(0)
    _, _, vt = np.linalg.svd(P - c, full_matrices=False)
    ax = vt[0]
    surf = np.argwhere(cav & ~ndi.binary_erosion(cav)).astype(np.float32) - c
    Re = float(np.median(np.linalg.norm(surf - np.outer(surf @ ax, ax), axis=1)))
    V = X - c
    along = V @ ax
    perp = V - along[..., None] * ax
    r = np.linalg.norm(perp, axis=-1) + 1e-6
    rfp = np.where(r < k * Re, r / k, np.sqrt(r ** 2 + (1 - k ** 2) * Re ** 2))
    return c + along[..., None] * ax + perp * (rfp / r)[..., None], Re


def warp(a, Y, order):
    return ndi.map_coordinates(a, [Y[..., k] for k in range(3)], order=order, mode="nearest")


def hsd(m):
    """Half-voxel signed distance, + outside the mask: +-0.5 mm on the voxels either side of the border."""
    return np.where(m, 0.5 - ndi.distance_transform_edt(m), ndi.distance_transform_edt(~m) - 0.5).astype(np.float32)


def sdist(m):
    return (ndi.distance_transform_edt(~m) - ndi.distance_transform_edt(m)).astype(np.float32)


# ---------------------------------------------------------------------------------------------- registration
def register(fixed, moving, mmask):
    F, M = img(fixed), img(np.clip(moving, -200, 600))
    MM = sitk.Cast(img(mmask.astype(np.float32)), sitk.sitkUInt8) if mmask is not None else None

    def run(tx):
        R = sitk.ImageRegistrationMethod()
        R.SetMetricAsMattesMutualInformation(50)
        R.SetMetricSamplingStrategy(R.RANDOM); R.SetMetricSamplingPercentage(0.1, seed=7)
        if MM is not None:
            R.SetMetricMovingMask(MM)
        R.SetInterpolator(sitk.sitkLinear)
        R.SetOptimizerAsRegularStepGradientDescent(2.0, 1e-3, 200, relaxationFactor=0.6)
        R.SetOptimizerScalesFromPhysicalShift()
        R.SetShrinkFactorsPerLevel([4, 2, 1]); R.SetSmoothingSigmasPerLevel([2, 1, 0])
        R.SetInitialTransform(tx, inPlace=False)
        return R.Execute(F, M)

    init = sitk.Euler3DTransform(sitk.CenteredTransformInitializer(
        F, M, sitk.Euler3DTransform(), sitk.CenteredTransformInitializerFilter.MOMENTS))
    init.SetTranslation((0, 0, 0))            # scanner coordinates; only the centre of rotation from moments
    rig = run(init)
    if mmask is None:
        return {"rigid_nomask": rig}
    rr = sitk.Euler3DTransform(rig.GetNthTransform(0) if isinstance(rig, sitk.CompositeTransform) else rig)
    a0 = sitk.AffineTransform(3)
    a0.SetCenter(rr.GetCenter()); a0.SetMatrix(rr.GetMatrix()); a0.SetTranslation(rr.GetTranslation())
    aff = run(a0)
    return {"rigid": rig, "affine": aff}


def tx_info(tx):
    """Truth-free summary of a transform: translation norm and log-determinant (scale) of its matrix."""
    t = tx.GetNthTransform(0) if isinstance(tx, sitk.CompositeTransform) else tx
    try:
        Mx = np.array(t.GetMatrix()).reshape(3, 3); tr = np.array(t.GetTranslation())
    except AttributeError:
        return {}
    return {"shift_mm": float(np.linalg.norm(tr)), "logdet": float(np.log(abs(np.linalg.det(Mx))))}


def carry_sitk(maps, ref, tx):
    out = {}
    R = img(ref)
    for k, (a, nearest) in maps.items():
        o = sitk.Resample(img(a), R, tx, sitk.sitkNearestNeighbor if nearest else sitk.sitkLinear,
                          float(a.max()) if not nearest else 0.0)
        out[k] = sitk.GetArrayFromImage(o)
    return out


def carry_warp(maps, Y):
    return {k: warp(a, Y, 0 if nearest else 1) for k, (a, nearest) in maps.items()}


def geometry(car):
    cav = car["sd_cav"] < 0
    myo = (car["sd_epi"] < 0) & ~cav
    seg = car["seg"].astype(np.uint8) * myo
    return {"myo": myo, "cav": cav, "seg": seg, "u": car["u"], "s": car["s"], "ang": car["ang"]}


# ---------------------------------------------------------------------------------------------- grading
def columns(g, m):
    return ((np.floor(g["ang"][m] / 3).astype(np.int64) * 1000 + np.floor(g["s"][m] / 2).astype(np.int64) + 500) * 10
            + np.clip(np.floor(np.nan_to_num(g["u"][m]) * 10), 0, 9).astype(np.int64))


def chord_index(col):
    """Precomputed column structure for Juliet's chord measure (3 deg x 2 mm columns, 10 depth bins)."""
    uc, inv, cnt = np.unique(col, return_inverse=True, return_counts=True)
    uq, cinv, ccnt = np.unique(uc // 10, return_inverse=True, return_counts=True)
    return inv, cnt, cinv, ccnt, ccnt >= 6


def chord_extent(ci, call):
    inv, cnt, cinv, ccnt, ok = ci
    if not ok.any():
        return 0.0
    db = (np.bincount(inv, weights=call, minlength=len(cnt)) / cnt) > 0.5
    return float((np.bincount(cinv, weights=db, minlength=len(ccnt)) / ccnt)[ok].mean())


def prepare(g):
    """Everything about one carried geometry that does not depend on the LIE values."""
    myo, cav, seg = g["myo"], g["cav"], g["seg"]
    P = {"myo": myo, "cav": cav, "core": ndi.binary_erosion(myo), "far1": ndi.distance_transform_edt(~cav) > 1.0}
    P["segs"] = {}
    for k in range(1, 18):
        m = myo & (seg == k)
        if m.sum() >= 10:
            P["segs"][k] = (m, chord_index(columns(g, m)), P["core"] & m)
    epi = myo | cav
    s_endo = hsd(cav)
    s_epi = hsd(epi)
    _, idx = ndi.distance_transform_edt(~myo, return_indices=True)
    near = seg[tuple(idx)]
    bins = np.arange(-5, 5.01, 0.5)
    P["cav3"] = ndi.binary_erosion(cav, iterations=3) if cav.sum() > 500 else None
    P["prof_endo"], P["prof_epi"] = {}, {}
    for k in range(1, 17):
        for key, sd, region in (("prof_endo", s_endo, cav | myo), ("prof_epi", -s_epi, ~cav)):
            m = region & (near == k) & (np.abs(sd) <= 5)
            if m.sum() >= 200:
                P[key][k] = (m, np.digitize(sd[m], bins))
    P["bins"] = bins
    return P


def grade(lie_s, P):
    """JA30 Scar-0 quantities per segment 1..17 on a smoothed LIE inside one prepared geometry."""
    myo = P["myo"]
    med = np.full(17, np.inf)
    for k, (m, ci, cm) in P["segs"].items():
        v = lie_s[cm]
        if v.size >= 20:
            med[k - 1] = np.median(v)
    order = np.argsort(med)[:6] + 1
    rv = np.concatenate([lie_s[P["segs"][k][2]] for k in order if k in P["segs"]])
    mu = float(np.median(rv)); sd = float(1.4826 * np.median(np.abs(rv - mu)))
    bright = int(np.argmax(np.where(np.isfinite(med), med, -np.inf))) + 1
    p99 = float(np.percentile(lie_s[P["segs"][bright][2]], 99))
    thr_k = mu + 0.5 * (p99 - mu)
    thr_3 = mu + 3 * sd
    above3 = myo & (lie_s > thr_3)
    abovek = myo & (lie_s > thr_k)
    pgm = ndi.binary_opening(above3) & P["far1"]
    out = {f: np.zeros(17) for f in FIELDS}
    for k, (m, ci, cm) in P["segs"].items():
        n = m.sum()
        out["pk"][k - 1] = abovek[m].sum() / n
        out["pg"][k - 1] = pgm[m].sum() / n
        out["ev"][k - 1] = above3[m].sum() / n
        out["ed"][k - 1] = chord_extent(ci, abovek[m])
        out["ed3"][k - 1] = chord_extent(ci, above3[m])
    return {f: v.round(4).tolist() for f, v in out.items()}, {"remote": mu, "sd": sd, "thr_k": thr_k}


def edge_offsets(lie_s, P, remote):
    """E9: per segment, signed distance (mm, + = outward) from the carried border to the LIE half-maximum edge;
    medians over segments of the endocardial and epicardial offsets, and dthick = epi - endo (LIE wall minus
    carried wall)."""
    blood = float(np.median(lie_s[P["cav3"]])) if P["cav3"] is not None else np.nan
    bins = P["bins"]
    x0 = (bins[:-1] + bins[1:]) / 2

    def crossing(profs, level_fn):
        offs = []
        for k, (m, b) in profs.items():
            v = lie_s[m]
            prof = np.array([np.median(v[b == i]) if (b == i).sum() >= 5 else np.nan for i in range(1, len(bins))])
            ok = np.isfinite(prof)
            if ok.sum() < 10:
                continue
            x, pr = x0[ok], prof[ok]
            lev = level_fn(np.median(pr[x < -3]), np.median(pr[x > 3]))
            if lev is None:
                continue
            sg = np.sign(pr - lev)
            ch = np.flatnonzero(sg[:-1] * sg[1:] < 0)
            if not len(ch):
                continue
            j = ch[np.argmin(np.abs(x[ch]))]
            offs.append(float(x[j] + (lev - pr[j]) * (x[j + 1] - x[j]) / (pr[j + 1] - pr[j])))
        return offs

    endo = crossing(P["prof_endo"], lambda i, o: (blood + remote) / 2 if abs(blood - remote) > 15 else None)
    epi = [-x for x in crossing(P["prof_epi"], lambda i, o: (i + o) / 2 if abs(i - o) >= 30 else None)]
    e1 = float(np.median(endo)) if endo else np.nan
    e2 = float(np.median(epi)) if epi else np.nan
    return {"off_endo": e1, "off_epi": e2, "dthick": e2 - e1, "n_endo": len(endo), "n_epi": len(epi),
            "blood_med": blood}


def qc(lie_s, P, remote, blood):
    w = lie_s[P["myo"]]
    return {"qc_fat": float((w < 0).mean()),
            "qc_brighter_than_blood": float((w > blood).mean()) if np.isfinite(blood) else np.nan,
            "qc_bloodlike": float((w > remote + 0.8 * (blood - remote)).mean()) if blood > remote + 15 else np.nan}


def assd(a, b):
    sa, sb = a & ~ndi.binary_erosion(a), b & ~ndi.binary_erosion(b)
    if not sa.any() or not sb.any():
        return np.nan
    return float((ndi.distance_transform_edt(~sb)[sa].mean() + ndi.distance_transform_edt(~sa)[sb].mean()) / 2)


# ---------------------------------------------------------------------------------------------- per case
def run_case(args):
    case_dir, idx, out_dir = args
    jrefuse([f"TotalSegmentator-cardiac__{case_dir.name}"], what="Golf R3 E8 loader")
    t0 = time.time()
    rng = np.random.default_rng(20261031 + idx)
    ct, lab, ant = load_case(case_dir)
    myo, cav = lab["myo"], lab["cav"]
    geom, diag = aha(myo, cav, lab["rv"], lab["la"], np.ones(3))
    if geom is None:
        return case_dir.name, {"error": diag}
    seg = aha_labels(myo, geom, ant)
    u = depth(myo, cav, np.ones(3))
    s_map = np.zeros(myo.shape, np.float32); a_map = np.zeros(myo.shape, np.float32)
    s_map[tuple(geom[7].T)] = geom[0]; a_map[tuple(geom[7].T)] = geom[1]
    terr = list(TERR)[idx % 3]
    tgt = np.zeros(18)
    for k in TERR[terr]:
        tgt[k] = rng.choice(KIM_MID)
    jit = 0.05 * smooth(myo.shape, 8.0, rng)
    scar = myo & (u < tgt[seg] + jit) & (tgt[seg] > 0)
    heart = myo | cav | lab["rv"] | lab["la"]
    mmask = ndi.binary_dilation(heart, iterations=10)
    dheart = ndi.distance_transform_edt(~heart)
    wstat = np.clip((25 - dheart) / 20, 0, 1).astype(np.float32)        # 1 within 5 mm, 0 beyond 25 mm
    centre = np.argwhere(myo | cav).mean(0)
    maps = {"sd_cav": (sdist(cav), False), "sd_epi": (sdist(myo | cav), False), "seg": (seg.astype(np.float32), True),
            "u": (np.nan_to_num(u, nan=0).astype(np.float32), True), "s": (s_map, True), "ang": (a_map, True)}
    fp_geom = {"myo": myo, "cav": cav, "seg": seg, "u": u, "s": s_map, "ang": a_map}
    out = {"territory": terr, "guard_version": GUARD_VERSION, "runs": []}
    for motion in MOTIONS:
        X, Y = rigid_scale(myo.shape, centre, rng)
        if motion == "static":
            Y = X + wstat[..., None] * (Y - X)
        if motion == "phase5":
            Pf, Re = phase_field(X, myo, cav)        # first-pass-frame point -> first-pass point at the LIE's phase
            Y = np.stack([warp(Pf[..., k], Y, 1) for k in range(3)], -1)   # x -> Y(x) -> Pf(Y(x))
        Yh = Y
        ex = geometry(carry_warp(maps, Yh))           # the true moved borders on the LIE grid
        scar_t = (warp(sdist(scar), Yh, 1) < 0) & ex["myo"]
        # truth per segment, on the moved anatomy
        tv, td = np.zeros(17), np.zeros(17)
        for k in range(1, 18):
            m = ex["myo"] & (ex["seg"] == k)
            if m.sum() >= 10:
                tv[k - 1] = scar_t[m].mean()
                td[k - 1] = chord_extent(chord_index(columns(ex, m)), scar_t[m])
        ctw = warp(ct, Yh, 1)
        myo_t = ex["myo"]
        tissue = 40 + 0.35 * (np.clip(ctw, -300, 1200) - 40)
        tissue[(ctw < -30) & ~myo_t] = -80
        bl = (ctw > 200) & ~myo_t
        for blood_name, blood_hu in BLOOD.items():
            for cnr in CNRS:
                noise = smooth(myo.shape, 0.6 / 2.355 * 2, rng) * (D / cnr)

                def make(with_scar, with_blood):
                    a = tissue.copy()
                    a[bl] = blood_hu if with_blood else REMOTE
                    a[myo_t] = REMOTE
                    if with_scar:
                        a[scar_t] = REMOTE + D
                    return ndi.gaussian_filter(a, 1.0 / 2.355) + noise
                lies = {"scar": make(True, True), "noscar": make(False, True),
                        "scar_nb": make(True, False), "noscar_nb": make(False, False)}
                sm = {k: ndi.gaussian_filter(v, 1.5 / 2.355) for k, v in lies.items()}
                txs = register(lies["scar"], ct, mmask)
                if motion == "static":
                    txs.update(register(lies["scar"], ct, None))
                geoms = {"exact": (ex, {}), "R0": (fp_geom, {"shift_mm": 0.0, "logdet": 0.0})}
                for name, tx in txs.items():
                    geoms[name] = (geometry(carry_sitk(maps, lies["scar"], tx)), tx_info(tx))
                for gname, (g, tinfo) in geoms.items():
                    P = prepare(g)
                    r = {"motion": motion, "blood": blood_name, "cnr": cnr, "geom": gname, **tinfo,
                         "assd_endo": assd(g["cav"], ex["cav"]), "assd_epi": assd(g["myo"] | g["cav"], ex["myo"] | ex["cav"])}
                    for v in VARIANTS:
                        G, rem = grade(sm[v], P)
                        r[v] = G
                        if v in ("scar", "noscar"):
                            eo = edge_offsets(sm[v], P, rem["remote"])
                            r[v + "_qc"] = {**qc(sm[v], P, rem["remote"], eo["blood_med"]), **eo, **rem}
                    out["runs"].append(r)
        out.setdefault("truth", {})[motion] = {"vol": tv.round(4).tolist(), "depth": td.round(4).tolist()}
        print(case_dir.name, motion, f"{time.time() - t0:.0f}s", flush=True)
    (out_dir / f"{case_dir.name}.json").write_text(json.dumps(out) + "\n")
    return case_dir.name, "ok"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("ts_dir", type=Path)
    ap.add_argument("--cases", type=int, default=0)
    ap.add_argument("--np", type=int, default=4)
    ap.add_argument("--out", type=Path, default=Path("/home/user/golf_e8"))
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    ids = guarded_ids()
    print(f"guard v{GUARD_VERSION}: {len(ids)} ids pass", flush=True)
    if a.cases:
        ids = ids[:a.cases]
    jobs = [(a.ts_dir / i, n, a.out) for n, i in enumerate(ids) if not (a.out / f"{i}.json").exists()]
    with Pool(a.np) as p:
        for name, o in p.imap_unordered(run_case, jobs, chunksize=1):
            print("done", name, o, flush=True)
