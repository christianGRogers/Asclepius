"""Juliet R4 E12 (Janus-M Round 4, path jm/paired-scar, #251 item 1): the *shipped* JA51 chain on the shared benchmark.

A replication of the canonical v3 run (Golf's, in bench_lie/; agreed on #251): same hearts, seeds and generator for
the v2 motions, so its rows can be compared case by case. Its own outputs stay in this folder.

v1-v2 (run.py) registered with a SimpleITK reference of JA29. v3 runs every case through the shipped module
(`janusm.scar.registration`, SCAR_VERSION 1.1.0) instead, stage by stage, with the module's own code:

  R0       scanner coordinates (identity);
  rigid    the module's Mattes MI rigid, metric mask = classes 1-4 dilated 4 mm (Euclidean), from R0;
  affine   the module's affine from rigid, same mask; `affine_sanity` logged;
  rigid10  the module's rigid from R0 with the 10 mm Euclidean fallback mask;
  bspline  (motion 'nonrigid' only; JA53's Round 4 arm) SimpleITK B-spline, control spacing 20 mm, 4 mm mask,
           Mattes MI, LBFGSB, started from the module's rigid. The module has no B-spline stage (JA53).
  oracle   the truth geometry on the LIE grid.

Every stage is computed on every case, so score_v3.py can replay `register_lie`'s control flow under any QC
cuts and any affine-acceptance rule (#251 item 2) on the same rows. Per stage it logs: the module's `carry` and
`qc` (four values, blood median, remote, contrast), `edge_offset` over the 6 remote segments (JA52, JA44 sign),
TRE over the truth wall, and every menu value from `menu.grade` on the module's carried geometry (scarred image;
the scar-free twin with its own constants; the twin with the scarred image's constants; blood set to remote).

Conditions: CNR 5; blood below / equal / above; motions none, rigid, scale, phase, nonrigid (v2's, same seeds, so
the same cases) and aniso3, aniso6, phase_neg (Round 4). Pre-registered on #251 before any v3 result.

Held-out handling: `fetch.hearts()` runs janusm.guard.refuse on the whole list, and `bench.load_heart` again per
heart, before any file is opened. The module is called with case_id=None because the guard has already run.

Usage: OMP_NUM_THREADS=1 PYTHONPATH=src python experiments/JanusM/Juliet/r4/run_v3_juliet.py <data_dir> [--procs 4]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BENCH = ROOT / "experiments/JanusM/bench_lie"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(BENCH))
sys.path.insert(0, str(HERE))
import bench_r4 as bench  # noqa: E402  (bench.py plus the Round 4 motions; see bench_r4.py)
import menu  # noqa: E402
from fetch import hearts as heart_list  # noqa: E402  (guard on the whole list)
from janusm.scar import registration as REG  # noqa: E402
from janusm.scar.common import CarriedGeometry  # noqa: E402

MOTIONS = bench.MOTIONS + bench.MOTIONS_R4
CONDS = [(b, 5, m) for b in bench.BLOOD for m in MOTIONS]
LEVELS, NS, BINS, MAXFEV = (2.0, 0.0), 30_000, 48, 2000         # register_lie's defaults
BSPLINE_MM = 20.0


def _r(a, n=3):
    return [None if not np.isfinite(x) else round(float(x), n) for x in np.asarray(a, float)]


def _pack(g):
    return {k: _r(g[k]) for k in ("pk_share", "pg_share", "ev", "ed")} | {
        "remote": round(g["remote"], 1), "rsd": round(g["rsd"], 2)}


def _f(x, n=5):
    return None if x is None or not np.isfinite(x) else round(float(x), n)


def car_dict(cg: CarriedGeometry, geo, fwd):
    """menu.grade's geometry from the module's carried geometry; E-D column coordinates (phi, s) are carried by
    nearest neighbour through the same transform (fwd: LIE voxel -> first-pass voxel, both 1 mm, origin 0)."""
    phi = np.zeros(cg.myo.shape, np.float32)
    s = np.zeros(cg.myo.shape, np.float32)
    p = np.argwhere(cg.myo).astype(float)
    if len(p):
        q = fwd(p).T
        phi[cg.myo] = ndi.map_coordinates(geo["phi"], q, order=0, mode="nearest")
        s[cg.myo] = ndi.map_coordinates(geo["s"], q, order=0, mode="nearest")
    return {"myo": cg.myo, "cav": cg.cavity, "seg": cg.segments.astype(np.int16), "u": cg.u, "phi": phi, "s": s}


def stage_record(c, cg: CarriedGeometry, car, tre):
    q = REG.qc(c["lie"], cg)
    sm = REG.smooth(c["lie"], cg.spacing, REG.DEFAULT_QC_DEFINITIONS.smooth_fwhm_mm)
    rem = REG.remote(sm, cg.segments, cg.core())
    off = REG.edge_offset(sm, cg, rem.segments) if rem is not None else float("nan")
    g = menu.grade(c["lie"], car)
    fixed = (g["remote"], g["rsd"], g["thr_k"])
    return {"scar": _pack(g), "free_own": _pack(menu.grade(c["lie_free"], car)),
            "free_fixed": _pack(menu.grade(c["lie_free"], car, fixed)),
            "noblood": _pack(menu.grade(c["lie_noblood"], car, fixed)),
            "qc": {n: _f(v) for n, v in zip(REG.QC_NAMES, q.values())},
            "blood_median": _f(q.blood_median, 2), "remote_median": _f(q.remote_median, 2),
            "contrast": _f(q.contrast, 3), "edge_offset_mm": _f(off, 3),
            "tre_mm": None if tre is None else round(float(tre), 3)}


def bspline(c, h, rig: REG.Transform, seed):
    import SimpleITK as sitk
    sitk.ProcessObject_SetGlobalDefaultNumberOfThreads(1)
    fixed, moving = menu._img(c["lie"].astype(np.float32)), menu._img(c["fp"].astype(np.float32))
    init = sitk.AffineTransform(3)
    init.SetCenter([float(x) for x in rig.centre])
    init.SetMatrix([float(x) for x in rig.matrix.ravel()])
    init.SetTranslation([float(x) for x in rig.translation])
    mesh = [max(1, int(round(n / BSPLINE_MM))) for n in fixed.GetSize()]
    bs = sitk.BSplineTransformInitializer(fixed, mesh, 3)
    m4 = (ndi.distance_transform_edt(~(h["lab"] > 0)) <= REG.MASK_DILATION_MM).astype(np.uint8)
    r = sitk.ImageRegistrationMethod()
    r.SetMetricAsMattesMutualInformation(numberOfHistogramBins=BINS)
    r.SetMetricSamplingStrategy(r.RANDOM)
    r.SetMetricSamplingPercentage(0.05, seed)
    r.SetMetricMovingMask(menu._img(m4))
    r.SetInterpolator(sitk.sitkLinear)
    r.SetOptimizerAsLBFGSB(gradientConvergenceTolerance=1e-5, numberOfIterations=100)
    r.SetShrinkFactorsPerLevel([2, 1])
    r.SetSmoothingSigmasPerLevel([1.0, 0.0])
    r.SetMovingInitialTransform(init)
    r.SetInitialTransform(bs, inPlace=True)
    r.Execute(fixed, moving)
    comp = sitk.CompositeTransform(init)
    comp.AddTransform(bs)                       # applied first: x -> init(bs(x))
    return comp


def one_heart(args):
    hid, data_dir = args
    t0 = time.time()
    h = bench.load_heart(hid, data_dir)        # janusm.guard.refuse first
    if "skip" in h:
        return [{"heart": hid, "skip": h["skip"]}]
    geo = menu.fp_geometry(h)
    if geo is None:
        return [{"heart": hid, "skip": "AHA failed on the first-pass labels"}]
    fp = REG.prepare_first_pass(h["ct"], h["lab"], bench.A_RAS)
    assert np.allclose(fp.affine[:3, :3], np.eye(3))    # 1 mm grid; the crop keeps full-grid world coordinates
    rows = []
    for blood, cnr, motion in CONDS:
        seed = int(hashlib.sha256(f"bench-lie-r3:{hid}:{blood}:{cnr}:{motion}".encode()).hexdigest()[:8], 16)
        c = bench.make_case(h, blood, cnr, motion, seed)
        if "skip" in c:
            rows.append({"heart": hid, "blood": blood, "cnr": cnr, "motion": motion, "skip": c["skip"]})
            continue
        x, x0 = c["tre_pts"]
        lie = c["lie"]
        row = {"heart": hid, "blood": blood, "cnr": cnr, "motion": motion, "seed": seed,
               "truth_vol": _r(c["truth"]["vol"]), "truth_depth": _r(c["truth"]["depth"]),
               "T_nominal": c["truth"]["T_nominal"], "arms": {}, "sec": {}}
        oracle = {"myo": c["lab_t"] == bench.G.MYO, "cav": c["lab_t"] == bench.G.LV, "seg": c["seg_t"],
                  "u": c["u_t"], "phi": c["phi_t"], "s": c["s_t"]}
        ocg = CarriedGeometry(myo=oracle["myo"], cavity=oracle["cav"], segments=np.where(oracle["myo"], c["seg_t"], 0)
                              .astype(np.int16), u=np.where(oracle["myo"], c["u_t"], np.nan).astype(np.float32),
                              column=np.full(lie.shape, -1, np.int64), spacing=np.ones(3), affine=bench.A_RAS)
        row["arms"]["oracle"] = stage_record(c, ocg, oracle, None)
        rs = seed % 1000
        metric = REG._metric(fp, lie, bench.A_RAS, np.ones(3), LEVELS, NS, BINS, rs)
        start = REG.Transform(np.eye(3), np.zeros(3), fp.centre)
        T = {"R0": start}
        ta = time.time()
        T["rigid"] = REG._rigid(metric, fp.centre, start, MAXFEV)
        row["sec"]["rigid"] = round(time.time() - ta, 1)
        ta = time.time()
        T["affine"] = REG._affine_from(metric, T["rigid"], MAXFEV)
        row["sec"]["affine"] = round(time.time() - ta, 1)
        met10 = REG._metric(fp, lie, bench.A_RAS, np.ones(3), LEVELS, NS, BINS, rs, mask=fp.fallback_mask)
        ta = time.time()
        T["rigid10"] = REG._rigid(met10, fp.centre, start, MAXFEV)
        row["sec"]["rigid10"] = round(time.time() - ta, 1)
        for name, tx in T.items():
            cg = REG.carry(fp, tx, lie.shape, bench.A_RAS)
            # world == voxel on both full grids; the module's transform maps LIE world -> first-pass world
            car = car_dict(cg, geo, tx.forward)
            rec = stage_record(c, cg, car, np.linalg.norm(tx.forward(x) - x0, axis=1).mean())
            rec["matrix"] = np.round(tx.matrix, 6).tolist()
            if name == "affine":
                rec["sanity"] = REG.affine_sanity(tx.matrix)
            row["arms"][name] = rec
        if motion == "nonrigid":
            ta = time.time()
            comp = bspline(c, h, T["rigid"], rs)
            row["sec"]["bspline"] = round(time.time() - ta, 1)
            car = menu.carry(geo, comp, lie.shape)
            cg = CarriedGeometry(myo=car["myo"], cavity=car["cav"], segments=car["seg"], u=car["u"],
                                 column=np.full(lie.shape, -1, np.int64), spacing=np.ones(3), affine=bench.A_RAS)
            est = np.array([comp.TransformPoint([float(v) for v in p]) for p in x])
            row["arms"]["bspline"] = stage_record(c, cg, car, np.linalg.norm(est - x0, axis=1).mean())
        rows.append(row)
        print(hid, blood, motion, {k: v.get("tre_mm") for k, v in row["arms"].items()}, row["sec"], flush=True)
    print(hid, "done", round(time.time() - t0), "s", flush=True)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data_dir")
    ap.add_argument("--hearts")
    ap.add_argument("--out", default=str(HERE / "results_v3_juliet.jsonl"))
    ap.add_argument("--procs", type=int, default=4)
    a = ap.parse_args()
    ids = heart_list() + ["phantom"]                       # janusm.guard.refuse on the whole list
    if a.hearts:
        ids = [i for i in a.hearts.split(",") if i in ids]
    done = set()
    if Path(a.out).exists():                               # resume: keep complete hearts
        per = {}
        for line in open(a.out):
            r = json.loads(line)
            per.setdefault(r["heart"], []).append(r)
        done = {k for k, rr in per.items() if any("blood" not in r for r in rr) or len(rr) >= len(CONDS)}
        with open(a.out, "w") as f:
            for k in sorted(done):
                for r in per[k]:
                    f.write(json.dumps(r) + "\n")
        ids = [i for i in ids if i not in done]
    print(f"{len(ids)} hearts x {len(CONDS)} conditions ({len(done)} already complete)", flush=True)
    with Pool(a.procs, maxtasksperchild=1) as p, open(a.out, "a") as f:
        for rows in p.imap_unordered(one_heart, [(i, a.data_dir) for i in ids]):
            for r in rows:
                f.write(json.dumps(r) + "\n")
            f.flush()


if __name__ == "__main__":
    main()
