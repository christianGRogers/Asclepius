"""Shared synthetic-LIE benchmark, v3 (Janus-M Round 4, path jm/paired-scar, #251 item 1): the **shipped** JA51
registration stages on every heart x condition, graded by the same benchmark scorer as v2 (menu.grade).

Pre-registered on #251 before any v3 result. One run serves Golf, Kilo and Juliet.

What changes from v2 (run.py)
  - Registration is `janusm.scar.registration` as shipped (SCAR_VERSION 1.1.0): `prepare_first_pass` (Euclidean
    masks, 4 mm metric mask, 10 mm fallback mask), `_metric`, `_rigid`, `_affine_from`, `carry`, `qc` and the phase
    step's `edge_offset`. Nothing in src/ is changed.
  - Two new motions (bench.MOTIONS_V3): `phase_neg` (larger LIE cavity) and `aniso` (3 / 3 / 6 % scale, random sign).
    The v2 motions keep v2's seed string, so their images are identical to v2's.
  - Arms:
      oracle   truth geometry on the LIE grid;
      R0       identity (scanner frame);
      rigid4   shipped rigid, 4 mm Euclidean mask (JA51 step 3);
      affine4  shipped affine from rigid4, same mask (JA51 step 4, before its acceptance rule);
      rigid10  shipped rigid from R0, 10 mm Euclidean mask (JA51 step 5);
      bspline  SimpleITK B-spline from rigid4, 20 mm control spacing, 4 mm Euclidean mask (JA53), on motion
               nonrigid (every blood level and CNR) and on rigid at CNR 5 (its harm check). Narrowed from the #251
               post (nonrigid, rigid, aniso) for run time (~140 s a case), before any result.
    The JA51 chain and the #251 item 2 affine-rule candidates are assembled from these arms in score_v3.py with the
    shipped decision functions.
  - Each registered arm also logs the shipped QC (four values, blood median, remote, contrast), the affine sanity
    numbers (log det, singular values, shear) and the JA52 edge offset (JA44 sign) over the 6 remote segments.

Grading (unchanged from v2): the shipped transform is converted to a SimpleITK affine and the geometry is carried by
menu.carry, so presence and extent are scored by exactly the code the #179 strike rules were written against.

Usage: PYTHONPATH=src python experiments/JanusM/bench_lie/run_v3.py <data_dir> [--hearts a,b] [--out f] [--procs 4]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import warnings
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import SimpleITK as sitk
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))
import bench  # noqa: E402
import menu  # noqa: E402
from fetch import hearts as heart_list  # noqa: E402  (guard runs on the whole list)
from janusm.scar import registration as R  # noqa: E402
from janusm.scar.common import remote, smooth  # noqa: E402

sitk.ProcessObject.SetGlobalDefaultNumberOfThreads(1)    # one thread per worker; the pool gives the parallelism
CONDS = [(b, c, m) for b in bench.BLOOD for c in bench.CNRS for m in bench.MOTIONS_V3]
BSPLINE_CONDS = lambda motion, cnr: motion == "nonrigid" or (motion == "rigid" and cnr == 5)  # noqa: E731
BSPLINE_GRID_MM = 20.0
MAXFEV = 2000
N_SAMPLES = 30_000


def _r(a, n=3):
    return [None if not np.isfinite(x) else round(float(x), n) for x in np.asarray(a, float)]


def _f(x, n=4):
    return None if x is None or not np.isfinite(x) else round(float(x), n)


def _pack(g):
    return {k: _r(g[k]) for k in ("pk_share", "pg_share", "ev", "ed")} | {
        "remote": round(g["remote"], 1), "rsd": round(g["rsd"], 2), "qc": {k: round(v, 4) for k, v in g["qc"].items()}}


def to_sitk(T: R.Transform):
    """Shipped Transform (fixed LIE world -> moving first-pass world) as a SimpleITK affine (same convention)."""
    tx = sitk.AffineTransform(3)
    tx.SetCenter([float(x) for x in T.centre])
    tx.SetMatrix([float(x) for x in np.asarray(T.matrix).ravel()])
    tx.SetTranslation([float(x) for x in T.translation])
    return tx


def shipped_log(lie, fp, T, sm):
    """Shipped QC, affine sanity and the JA52 edge offset of one transform."""
    car = R.carry(fp, T, lie.shape, bench.A_RAS)
    q = R.qc(lie, car)
    rem = remote(sm, car.segments, car.core())
    off = R.edge_offset(sm, car, rem.segments) if rem is not None else float("nan")
    san = R.affine_sanity(T.matrix)
    return {"fatlike": _f(q.fatlike), "bloodlike": _f(q.bloodlike), "brighter_than_blood": _f(q.brighter_than_blood),
            "rim_dark": _f(q.rim_dark), "blood_median": _f(q.blood_median, 2), "remote_median": _f(q.remote_median, 2),
            "remote_sd": _f(q.remote_sd, 3), "contrast": _f(q.contrast, 3), "blood_core": q.blood_core,
            "log_det": _f(san["log_det"], 5), "sv": _r(san["singular_values"], 5), "shear": _r(san["shear"], 5),
            "sane": san["ok"], "edge_offset_mm": _f(off, 3)}


def bspline(lie, fp_img, mask4, init_tx, seed):
    """JA53's B-spline arm: Mattes MI, 20 mm control spacing, moving mask = classes 1-4 + 4 mm (Euclidean)."""
    fixed, moving = menu._img(lie.astype(np.float32)), menu._img(fp_img.astype(np.float32))
    mesh = [max(1, int(round(n / BSPLINE_GRID_MM))) for n in fixed.GetSize()]
    bs = sitk.BSplineTransformInitializer(fixed, mesh, 3)
    r = sitk.ImageRegistrationMethod()
    r.SetMetricAsMattesMutualInformation(numberOfHistogramBins=50)
    r.SetMetricSamplingStrategy(r.RANDOM)
    r.SetMetricSamplingPercentage(0.05, seed)
    r.SetMetricMovingMask(menu._img(mask4.astype(np.uint8)))
    r.SetInterpolator(sitk.sitkLinear)
    r.SetOptimizerAsLBFGSB(gradientConvergenceTolerance=1e-5, numberOfIterations=100, maximumNumberOfCorrections=5,
                           maximumNumberOfFunctionEvaluations=400)
    r.SetShrinkFactorsPerLevel([2, 1])
    r.SetSmoothingSigmasPerLevel([1.0, 0.0])
    r.SetMovingInitialTransform(init_tx)
    r.SetInitialTransform(bs, inPlace=True)
    r.Execute(fixed, moving)
    comp = sitk.CompositeTransform(3)
    comp.AddTransform(init_tx)
    comp.AddTransform(bs)
    return comp


def tre_points(tx, pts, n=4000):
    x, x0 = pts
    k = min(n, len(x))
    est = np.array([tx.TransformPoint([float(v) for v in p]) for p in x[:k]])
    return float(np.linalg.norm(est - x0[:k], axis=1).mean())


def one_heart(args):
    try:
        return _one_heart(args)
    except Exception as e:  # noqa: BLE001  (a heart that cannot be set up is recorded, the pool keeps going)
        return [{"heart": args[0], "skip": f"heart error: {type(e).__name__}: {e}"[:300]}]


def _one_heart(args):
    hid, data_dir, part_dir = args
    part = Path(part_dir) / f"{hid}.jsonl"
    have = set()
    if part.exists():
        for line in open(part):
            r = json.loads(line)
            have.add((r.get("blood"), r.get("cnr"), r.get("motion")))
    todo = [x for x in CONDS if x not in have]
    if not todo:
        return [json.loads(line) for line in open(part)]
    t0 = time.time()
    h = bench.load_heart(hid, data_dir)                  # janusm.guard.refuse inside, before any file is opened
    if "skip" in h:
        return [{"heart": hid, "skip": h["skip"]}]
    rows = []
    geo = menu.fp_geometry(h)
    if geo is None:
        return [{"heart": hid, "skip": "AHA failed on the first-pass labels"}]
    fp = R.prepare_first_pass(h["ct"], h["lab"], bench.A_RAS, mask_mm=R.MASK_DILATION_MM,
                              fallback_mm=R.FALLBACK_MASK_MM, case_id=None if hid == "phantom" else hid)
    mask4 = ndi.distance_transform_edt(h["lab"] == 0) <= R.MASK_DILATION_MM       # Euclidean, full grid (B-spline)

    def keep(row):
        rows.append(row)
        with open(part, "a") as fh:
            fh.write(json.dumps(row) + "\n")

    for blood, cnr, motion in todo:
        try:
            one_case(h, hid, geo, fp, mask4, blood, cnr, motion, keep, t0)
        except Exception as e:  # noqa: BLE001  (recorded per case, never hidden; the pool keeps going)
            keep({"heart": hid, "blood": blood, "cnr": cnr, "motion": motion,
                  "case_error": f"{type(e).__name__}: {e}"[:300]})
    print(hid, "done", round(time.time() - t0), "s", flush=True)
    return [json.loads(line) for line in open(part)]


def one_case(h, hid, geo, fp, mask4, blood, cnr, motion, keep, t0):
    sp = np.ones(3)
    if True:
        seed = int(hashlib.sha256(f"bench-lie-r3:{hid}:{blood}:{cnr}:{motion}".encode()).hexdigest()[:8], 16)
        c = bench.make_case(h, blood, cnr, motion, seed)
        if "skip" in c:
            keep({"heart": hid, "blood": blood, "cnr": cnr, "motion": motion, "skip": c["skip"]})
            return
        lie = c["lie"]
        sm = smooth(lie, sp)
        row = {"heart": hid, "blood": blood, "cnr": cnr, "motion": motion, "seed": seed, "v": 3,
               "truth_vol": _r(c["truth"]["vol"]), "truth_depth": _r(c["truth"]["depth"]),
               "T_nominal": c["truth"]["T_nominal"], "arms": {}}
        mo = c["motion"]
        row["motion_s"] = (np.round(mo["s"], 5).tolist() if np.ndim(mo["s"]) else float(mo["s"]))
        oracle = {"myo": c["lab_t"] == bench.G.MYO, "cav": c["lab_t"] == bench.G.LV, "seg": c["seg_t"],
                  "u": c["u_t"], "phi": c["phi_t"], "s": c["s_t"]}
        start = R.Transform(np.eye(3), np.zeros(3), fp.centre)
        rs = seed % 1000
        ts = time.time()
        met = R._metric(fp, lie, bench.A_RAS, sp, (2.0, 0.0), N_SAMPLES, 48, rs)
        rig = R._rigid(met, fp.centre, start, MAXFEV)
        t_rig = time.time() - ts
        ts = time.time()
        aff = R._affine_from(met, rig, MAXFEV)
        t_aff = time.time() - ts
        ts = time.time()
        met10 = R._metric(fp, lie, bench.A_RAS, sp, (2.0, 0.0), N_SAMPLES, 48, rs, mask=fp.fallback_mask)
        rig10 = R._rigid(met10, fp.centre, start, MAXFEV)
        t_r10 = time.time() - ts
        shipped = {"R0": (start, 0.0), "rigid4": (rig, t_rig), "affine4": (aff, t_aff), "rigid10": (rig10, t_r10)}
        arms = [("oracle", None, oracle, None)]
        for name, (T, secs) in shipped.items():
            arms.append((name, to_sitk(T), None, (T, secs)))
        if BSPLINE_CONDS(motion, cnr):
            ts = time.time()
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    bs = bspline(lie, c["fp"], mask4, to_sitk(rig), rs)
                arms.append(("bspline", bs, None, (None, time.time() - ts)))
            except RuntimeError as e:                    # report, never hide
                row["bspline_error"] = str(e)[:200]
        for name, tx, car, ship in arms:
            ta = time.time()
            if car is None:
                car = menu.carry(geo, tx, lie.shape)
            try:
                g = menu.grade(lie, car)
                fixed = (g["remote"], g["rsd"], g["thr_k"])
                rec = {"scar": _pack(g),
                       "free_own": _pack(menu.grade(c["lie_free"], car)),
                       "noblood": _pack(menu.grade(c["lie_noblood"], car, fixed))}
            except (IndexError, ValueError) as e:      # carried wall too small to grade (gross misregistration)
                rec = {"ungradable": f"{type(e).__name__}: {e}"[:200]}
            if ship is not None:
                T, secs = ship
                rec["reg_sec"] = round(secs, 1)
                if T is not None:
                    rec["tre_mm"] = round(menu.tre(tx, c["tre_pts"]), 3)
                    rec["shipped"] = shipped_log(lie, fp, T, sm)
                else:
                    rec["tre_mm"] = round(tre_points(tx, c["tre_pts"]), 3)
                    # B-spline QC: shipped QC on menu's carried geometry has no column ids; log menu QC only
            rec["sec"] = round(time.time() - ta, 1)
            row["arms"][name] = rec
        keep(row)
        print(hid, blood, cnr, motion, {k: v.get("tre_mm") for k, v in row["arms"].items()},
              round(time.time() - t0), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data_dir")
    ap.add_argument("--hearts")
    ap.add_argument("--motions")
    ap.add_argument("--out", default=str(HERE / "results_v3.jsonl"))
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--parts", default=str(HERE / "results_v3_parts"), help="per-heart files, written per case")
    ap.add_argument("--resume", action="store_true", help="keep hearts already complete in --out; run the rest")
    a = ap.parse_args()
    global CONDS
    if a.motions:
        CONDS = [x for x in CONDS if x[2] in a.motions.split(",")]
    ids = heart_list() + ["phantom"]                       # janusm.guard.refuse runs on the whole list here
    if a.hearts:
        ids = [i for i in a.hearts.split(",") if i in ids]
    done = set()
    if a.resume and Path(a.out).exists():
        rows = [json.loads(line) for line in open(a.out)]
        per = {}
        for r in rows:
            per.setdefault(r["heart"], []).append(r)
        done = {h for h, rr in per.items() if any("skip" in r and "blood" not in r for r in rr) or len(rr) >= len(CONDS)}
        with open(a.out, "w") as f:
            for h in done:
                for r in per[h]:
                    f.write(json.dumps(r) + "\n")
        ids = [i for i in ids if i not in done]
    Path(a.parts).mkdir(parents=True, exist_ok=True)
    print(f"{len(ids)} hearts x {len(CONDS)} conditions ({len(done)} already complete)", flush=True)
    with Pool(a.procs) as p, open(a.out, "a" if a.resume else "w") as f:
        for rows in p.imap_unordered(one_heart, [(i, a.data_dir, a.parts) for i in ids]):
            for r in rows:
                f.write(json.dumps(r) + "\n")
            f.flush()


if __name__ == "__main__":
    main()
