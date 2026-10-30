"""Kilo R4 replication of the shared benchmark v3 (Janus-M Round 4, path jm/paired-scar, #251 item 1): the SHIPPED
registration chain (``janusm.scar.registration``, SCAR_VERSION 1.1.0, JA51-JA53) through the benchmark.

Pre-registered on #251 (Kilo, 2026-10-30 18:56 and ~19:04 UTC) before any result existed. Our three claims to run the
one benchmark crossed; by agreement on #251 Golf's run (bench_lie/run_v3.py) is the canonical v3, and this run is
Kilo's replication: same seeds and module, Kilo's motions (bench_kilo_r4.py = bench_lie/bench.py at 93c9380 plus
phase_m5, aniso3, aniso6, exactly as run), output kept here, never in bench_lie/.

Per case (same generator and seed formula as run.py, so every none / rigid / scale / phase / nonrigid case is the v2
case byte for byte):
  - ``register_lie`` exactly as shipped (Euclidean 4 mm mask, its own Mattes MI and Powell search, 10 mm fallback),
    with QC cuts forced to fail, so every stage exists: R0 -> rigid (4 mm) -> affine (4 mm) -> rigid10 (10 mm, from
    R0). Each stage's shipped QC values, affine sanity terms, MI, TRE and the JA52 edge offset are logged, and every
    stage is graded by ``menu.grade`` (as v2). score_shipped.py (same folder) replays the chain offline at any cuts and under any
    affine acceptance rule (#251 item 2): the forced stages are the stages the chain would compute, because each
    stage starts from R0 or from rigid, never from a QC decision.
  - ``oracle``: the truth geometry (the rule's own error), with the shipped QC and edge offset on it (JA53's
    "aligned" reference for self-fitted cuts).
  - ``bspline`` (JA53's arm; motions nonrigid and rigid only; reported, never in the chain): SimpleITK B-spline,
    control spacing 20 mm, from the as-shipped chain's final transform (provisional cuts at this blood level), the
    moving mask = classes 1-4 dilated 4 mm (Euclidean), Mattes MI, LBFGSB, two levels.
  - On (equal, 5, rigid) per heart, one UN-forced ``register_lie`` at the provisional cuts: score_shipped.py checks
    the replay picks the same final stage.

The JA12 guard runs on the whole heart list (fetch.hearts) and again per heart (bench.load_heart) before any file
is opened. Writes results_kilo_r4.jsonl (one JSON line per case); no image is written.

Usage: PYTHONPATH=src python experiments/JanusM/Kilo/r4/run_shipped.py <data_dir> [--hearts a,b] [--procs 4]
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

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments/JanusM/bench_lie"))
sys.path.insert(0, str(HERE))
import bench_kilo_r4 as bench  # noqa: E402
sys.modules["bench"] = bench                      # menu, fetch and module_parity share this generator
import menu  # noqa: E402
import SimpleITK as sitk  # noqa: E402
from fetch import hearts as heart_list  # noqa: E402
from janusm.scar import SCAR_VERSION  # noqa: E402
from janusm.scar import registration as REG  # noqa: E402
from module_parity import oracle_geometry  # noqa: E402

CNR = 5
MOTIONS = ("none", "rigid", "scale", "aniso3", "aniso6", "phase", "phase_m5", "nonrigid")
CONDS = [(b, CNR, m) for m in MOTIONS for b in bench.BLOOD]
BSPLINE_MOTIONS = ("nonrigid", "rigid")
FORCE = REG.QCCuts(max_fatlike=-1.0, max_bloodlike=-1.0, max_brighter_than_blood=-1.0, max_rim_dark=-1.0)
BSPLINE_MM = 20.0


def seed_of(hid, blood, cnr, motion):
    return int(hashlib.sha256(f"bench-lie-r3:{hid}:{blood}:{cnr}:{motion}".encode()).hexdigest()[:8], 16)


def _r(a, n=3):
    return [None if not np.isfinite(x) else round(float(x), n) for x in np.asarray(a, float)]


def _pack(g):
    return {k: _r(g[k]) for k in ("pk_share", "pg_share", "ev", "ed")} | {
        "remote": round(g["remote"], 1), "rsd": round(g["rsd"], 2)}


def to_sitk(T: REG.Transform):
    tx = sitk.AffineTransform(3)
    tx.SetCenter([float(x) for x in T.centre])
    tx.SetMatrix([float(x) for x in np.asarray(T.matrix).ravel()])
    tx.SetTranslation([float(x) for x in T.translation])
    return tx


def tre_T(T: REG.Transform, pts):
    x, x0 = pts
    return float(np.linalg.norm(T.forward(x) - x0, axis=1).mean())


def tre_sitk(tx, pts):
    x, x0 = pts
    est = np.array([tx.TransformPoint([float(a) for a in p]) for p in x])
    return float(np.linalg.norm(est - x0, axis=1).mean())


def grade_all(c, car):
    g = menu.grade(c["lie"], car)
    fixed = (g["remote"], g["rsd"], g["thr_k"])
    return {"scar": _pack(g), "free_own": _pack(menu.grade(c["lie_free"], car)),
            "free_fixed": _pack(menu.grade(c["lie_free"], car, fixed)),
            "noblood": _pack(menu.grade(c["lie_noblood"], car, fixed))}


def qc_dict(q: REG.QC):
    return {k: (None if not np.isfinite(v) else round(float(v), 5)) for k, v in
            (("fatlike", q.fatlike), ("bloodlike", q.bloodlike), ("brighter_than_blood", q.brighter_than_blood),
             ("rim_dark", q.rim_dark), ("blood_median", q.blood_median), ("remote_median", q.remote_median),
             ("remote_sd", q.remote_sd), ("contrast", q.contrast))} | {"blood_core": q.blood_core}


def edge_off(lie, carried):
    """JA52's secondary flag value on one carried geometry (JA44 sign: a larger LIE cavity reads negative)."""
    sm = REG.smooth(lie, carried.spacing, REG.DEFAULT_QC_DEFINITIONS.smooth_fwhm_mm)
    rem = REG.remote(sm, carried.segments, carried.core())
    return float(REG.edge_offset(sm, carried, rem.segments)) if rem is not None else float("nan")


def replay_shipped(stages: dict, cuts: REG.QCCuts):
    """JA51 as shipped, on forced stages: the final stage's name."""
    passes = {k: REG.QC(**{f: (np.nan if v[f] is None else v[f]) for f in REG.QC_NAMES},
                        blood_median=0, remote_median=0, n_wall=1).passes(cuts) for k, v in
              ((k, s["qc"]) for k, s in stages.items())}
    if passes["R0"]:
        return "R0"
    final = "rigid"
    if not passes["rigid"]:
        a = stages["affine"]
        qa = REG.QC(**{f: (np.nan if a["qc"][f] is None else a["qc"][f]) for f in REG.QC_NAMES},
                    blood_median=0, remote_median=0, n_wall=1)
        qr = REG.QC(**{f: (np.nan if stages["rigid"]["qc"][f] is None else stages["rigid"]["qc"][f])
                       for f in REG.QC_NAMES}, blood_median=0, remote_median=0, n_wall=1)
        if a["sanity"]["ok"] and REG.qc_rule_accepts(qa, qr, cuts):
            final = "affine"
    if not passes[final]:
        f = stages["rigid10"]
        qf = REG.QC(**{k: (np.nan if f["qc"][k] is None else f["qc"][k]) for k in REG.QC_NAMES},
                    blood_median=0, remote_median=0, n_wall=1)
        qo = REG.QC(**{k: (np.nan if stages[final]["qc"][k] is None else stages[final]["qc"][k])
                       for k in REG.QC_NAMES}, blood_median=0, remote_median=0, n_wall=1)
        mn, mo = REG.normalised_max(qf, cuts), REG.normalised_max(qo, cuts)
        if passes["rigid10"] or (np.isfinite(mn) and np.isfinite(mo) and mn < mo):
            final = "rigid10"
    return final


def bspline(c, fp_heart_lab, init_tx, seed):
    """JA53's B-spline arm: from the chain's final affine, 20 mm control spacing, 4 mm Euclidean moving mask."""
    from scipy import ndimage as ndi
    fixed, moving = menu._img(c["lie"].astype(np.float32)), menu._img(c["fp"].astype(np.float32))
    mask = (ndi.distance_transform_edt(~(fp_heart_lab > 0)) <= 4.0).astype(np.uint8)
    mesh = [max(1, int(round(s / BSPLINE_MM))) for s in fixed.GetSize()]
    bs = sitk.BSplineTransformInitializer(fixed, mesh, 3)
    comp = sitk.CompositeTransform([init_tx, bs])
    r = sitk.ImageRegistrationMethod()
    r.SetMetricAsMattesMutualInformation(numberOfHistogramBins=48)
    r.SetMetricSamplingStrategy(r.RANDOM)
    r.SetMetricSamplingPercentage(0.05, seed)
    r.SetMetricMovingMask(menu._img(mask))
    r.SetInterpolator(sitk.sitkLinear)
    r.SetOptimizerAsLBFGSB(gradientConvergenceTolerance=1e-5, numberOfIterations=100, maximumNumberOfCorrections=5)
    r.SetShrinkFactorsPerLevel([2, 1])
    r.SetSmoothingSigmasPerLevel([1.0, 0.0])
    r.SetInitialTransform(comp, inPlace=True)
    r.Execute(fixed, moving)
    return comp


def one_heart(args):
    hid, data_dir, motions = args
    sitk.ProcessObject.SetGlobalDefaultNumberOfThreads(1)
    t0 = time.time()
    h = bench.load_heart(hid, data_dir)                  # guard first (bench.load_heart -> janusm.guard.refuse)
    if "skip" in h:
        return [{"heart": hid, "skip": h["skip"]}]
    geo = menu.fp_geometry(h)
    if geo is None:
        return [{"heart": hid, "skip": "AHA failed on the first-pass labels"}]
    fp = REG.prepare_first_pass(h["ct"], h["lab"], bench.A_RAS)   # 4 mm mask, 10 mm fallback (shipped defaults)
    rows = []
    for blood, cnr, motion in [x for x in CONDS if x[2] in motions]:
        seed = seed_of(hid, blood, cnr, motion)
        c = bench.make_case(h, blood, cnr, motion, seed)
        if "skip" in c:
            rows.append({"heart": hid, "blood": blood, "cnr": cnr, "motion": motion, "skip": c["skip"]})
            continue
        row = {"heart": hid, "blood": blood, "cnr": cnr, "motion": motion, "seed": seed,
               "truth_vol": _r(c["truth"]["vol"]), "truth_depth": _r(c["truth"]["depth"]),
               "T_nominal": c["truth"]["T_nominal"], "arms": {}, "stages": {}}
        # oracle: grading, plus the shipped QC and edge offset on the truth geometry
        ta = time.time()
        ocar = oracle_geometry(c)
        oracle = {"myo": ocar.myo, "cav": ocar.cavity, "seg": c["seg_t"], "u": c["u_t"], "phi": c["phi_t"],
                  "s": c["s_t"]}
        row["arms"]["oracle"] = grade_all(c, oracle)
        row["oracle_qc"] = qc_dict(REG.qc(c["lie"], ocar)) | {"edge_offset_mm": round(edge_off(c["lie"], ocar), 4)}
        # the shipped chain, every stage forced
        reg = REG.register_lie(fp, c["lie"], bench.A_RAS, FORCE, seed=seed % 1000)
        for st in reg.stages:
            car = REG.carry(fp, st.transform, c["lie"].shape, bench.A_RAS)
            rec = {"qc": qc_dict(st.qc), "tre_mm": round(tre_T(st.transform, c["tre_pts"]), 3),
                   "mi": round(float(st.mi), 5), "sec": round(st.seconds, 1),
                   "edge_offset_mm": round(edge_off(c["lie"], car), 4),
                   "log_det": round(REG._log_det(st.transform.matrix), 5),
                   "matrix": np.round(st.transform.matrix, 6).tolist(),
                   "translation": np.round(st.transform.translation, 4).tolist(),
                   "centre": np.round(st.transform.centre, 4).tolist()}
            if st.name == REG.STAGE_AFFINE:
                rec["sanity"] = st.info["sanity"]
            row["stages"][st.name] = rec
            row["arms"][st.name] = grade_all(c, menu.carry(geo, to_sitk(st.transform), c["lie"].shape))
        # B-spline arm from the as-shipped final transform at the provisional cuts
        if motion in BSPLINE_MOTIONS:
            tb = time.time()
            cuts = REG.load_provisional_qc_cuts(blood=blood, cnr=cnr)
            fin = replay_shipped(row["stages"], cuts)
            st = {s.name: s for s in reg.stages}[fin]
            try:
                comp = bspline(c, h["lab"], to_sitk(st.transform), seed % 1000)
                row["arms"]["bspline"] = grade_all(c, menu.carry(geo, comp, c["lie"].shape))
                row["bspline"] = {"from": fin, "tre_mm": round(tre_sitk(comp, c["tre_pts"]), 3),
                                  "sec": round(time.time() - tb, 1)}
            except Exception as ex:  # noqa: BLE001
                row["bspline"] = {"from": fin, "error": str(ex)[:200]}
        # one un-forced call per heart, to check the offline replay
        if (blood, cnr, motion) == ("equal", 5, "rigid"):
            cuts = REG.load_provisional_qc_cuts(blood=blood, cnr=cnr)
            live = REG.register_lie(fp, c["lie"], bench.A_RAS, cuts, seed=seed % 1000)
            row["live_check"] = {"final": live.final.name, "stages": [s.name for s in live.stages],
                                 "tre_mm": round(tre_T(live.final.transform, c["tre_pts"]), 3),
                                 "phase": live.phase.summary()}
        row["sec"] = round(time.time() - ta, 1)
        rows.append(row)
        print(hid, blood, cnr, motion, {k: v["tre_mm"] for k, v in row["stages"].items()},
              row.get("bspline", {}).get("tre_mm"), row["sec"], flush=True)
    print(hid, motions, "done", round(time.time() - t0), "s", flush=True)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data_dir")
    ap.add_argument("--hearts")
    ap.add_argument("--out", default=str(HERE / "results_kilo_r4.jsonl"))
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--motions", help="comma-separated subset of MOTIONS (for a smoke test)")
    a = ap.parse_args()
    global CONDS
    if a.motions:
        CONDS = [x for x in CONDS if x[2] in a.motions.split(",")]
    ids = heart_list() + ["phantom"]                       # janusm.guard.refuse on the whole list, first
    if a.hearts:
        ids = [i for i in a.hearts.split(",") if i in ids]
    done = set()
    if Path(a.out).exists():                               # resume: (heart, motion) tasks already written
        for line in open(a.out):
            r = json.loads(line)
            done.add((r["heart"], r.get("motion")))
    ms = sorted({m for _, _, m in CONDS}, key=MOTIONS.index)
    tasks = [(i, a.data_dir, (m,)) for m in ms for i in ids if (i, m) not in done and (i, None) not in done]
    print(f"SCAR_VERSION {SCAR_VERSION}; {len(ids)} hearts x {len(CONDS)} conditions; {len(tasks)} tasks to run",
          flush=True)
    with Pool(a.procs, maxtasksperchild=1) as p, open(a.out, "a") as f:
        for rows in p.imap_unordered(one_heart, tasks):
            for r in rows:
                f.write(json.dumps(r) + "\n")
            f.flush()


if __name__ == "__main__":
    main()
