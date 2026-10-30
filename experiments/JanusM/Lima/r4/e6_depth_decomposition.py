"""Lima R4 E6: why Lima E5 printed 45 % and Hotel E7 35 % (issue #205 item 2), on one seed.

A simulation of 16 segment thicknesses per heart; no case or image is opened. The guard is still
called first, on an empty list, so the script fails closed if the guard's pins are broken.

Everything runs on the shipped ``janusm.calibrate`` (S3): its ``population``, ``rule_c_scores``,
``calibrate_c`` and ``territory_flags``, with E7's design (4 populations of 2000 per depth, depths
0.10-0.60, seed sequence from ``E7_SEED``). Only four things are switched, one at a time and in
all 16 combinations, so every combination sees the same random draws (median only rescales them;
sig_m 0 still draws its zero-SD noise, so the draw order is identical):

1. ``median``: 9.668 mm (E7: Lima's mixed-phase self-test median, used as the end-diastolic anchor)
   or 5.7 mm (E5: Chen 2025's end-diastolic CT mean, the anchor ``population`` was written for);
2. ``sig_m``: 0 (E7, JA40) or 0.5 mm (E5);
3. ``floor``: F1's floor, 1.0 mm (E7, JA40) or E5's 1.96 * sqrt(2) * sig_m / sqrt(k) per territory
   (0.57 / 0.62 / 0.62 mm for LAD / RCA / LCx at sig_m 0.5; 0 at sig_m 0);
4. ``dev``: F1's deviation, Hotel's shape-corrected one (``calibrate.f1_deviation``, JA42) or
   E5's raw one (patient's remote median minus the territory's mean, no shape correction).

Then E5's own ``detectable_depth`` (one population of 4000 per depth, depths from 0.15, one
generator for the whole sweep) is run on 20 seeds, to show its step-to-step spread.

Then the shipped ``detectable_depth`` (JA40's settings: sig_m 0, F1 1.0 mm, Hotel's deviation) at
four medians (9.668 and 5.7 mm as anchors, and the anchors that reproduce 9.668 and 5.7 mm as the
population's measured median) on five seeds, including E7's and ``jm0r_decide``'s ``DEPTH_SEED``.

Also reported: the end-diastolic anchor that makes the simulated population's median wall equal a
measured median (the phase mix multiplies the anchor by about 1.1), for 9.668 mm and 5.7 mm.

    python experiments/JanusM/Lima/r4/e6_depth_decomposition.py OUT.json
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(HERE.parent / "r3"))

from janusm import calibrate as C  # noqa: E402
from janusm import guard  # noqa: E402

RC_FACTOR = 1.96 * np.sqrt(2)  # E5's floor: RC of a k-segment mean from a single-read SD
K = np.array([len(C.TERR16[t]) for t in C.TERRITORIES])


def f1_raw(meas):
    """E5's F1 deviation (mm, + = thinner): remote median minus territory mean, no shape."""
    out = np.zeros((meas.shape[0], 3))
    for j, t in enumerate(C.TERRITORIES):
        idx = [s - 1 for s in C.TERR16[t]]
        rest = [i for i in range(16) if i not in idx]
        out[:, j] = np.median(meas[:, rest], 1) - meas[:, idx].mean(1)
    return out


def one(depth, seed, median, sig_m):
    """One population: per (floor, dev) the sensitivity and false-flag share."""
    shape = np.asarray(C.LIMA_SHAPE)
    rng = np.random.default_rng(seed)
    meas, _, sick, terr, _ = C.population(C.N_PER_POPULATION, C.PREVALENCE, depth, C.LIMA_CV_N,
                                          sig_m, C.PHASE_MIX, rng, shape=shape, median_mm=median)
    z = C.rule_c_scores(meas)
    cut, _ = C.calibrate_c(z, rng=np.random.default_rng(seed + 1))
    tf = C.territory_flags(z < cut)
    devs = {"hotel": C.f1_deviation(meas, shape), "lima_raw": f1_raw(meas)}
    floors = {"1.0mm": np.full(3, 1.0), "e5_sigma": RC_FACTOR * sig_m / np.sqrt(K)}
    sick_i = np.nonzero(sick)[0]
    ti = np.array([C.TERRITORIES.index(terr[i]) for i in sick_i])
    out = {"rule_c_only_sens": float(tf[sick_i, ti].mean())}
    for (dn, d), (fn, f) in itertools.product(devs.items(), floors.items()):
        shown = tf & (d > f[None, :])
        out[f"{dn}|{fn}"] = (float(shown[sick_i, ti].mean()), float(shown.any(1)[~sick].mean()))
    return out


def sweep(median, sig_m, seed=C.E7_SEED):
    rows, s = [], seed
    for depth in C.DEPTHS:
        reps = []
        for _ in range(C.REPLICATES):
            s += 2  # E7's sequence, as calibrate.detectable_depths
            reps.append(one(depth, s, median, sig_m))
        rows.append((depth, reps))
    res = {}
    for key in [k for k in rows[0][1][0] if "|" in k] + ["rule_c_only_sens"]:
        curve = []
        for depth, reps in rows:
            sens = [r[key][0] if key != "rule_c_only_sens" else r[key] for r in reps]
            curve.append({"depth": depth, "sens_mean": round(float(np.mean(sens)), 4),
                          "sens_range": [round(min(sens), 4), round(max(sens), 4)]})
        hit = [c for c in curve if c["sens_mean"] >= C.SENSITIVITY_TARGET]
        res[key] = {"depth": hit[0]["depth"] if hit else None, "curve": curve}
        if key != "rule_c_only_sens":
            res[key]["false_flag_max"] = round(max(r[key][1] for _, rr in rows for r in rr), 4)
    return res


def anchor_for(measured_median, seed=7, n=200000):
    """The ED anchor whose simulated population (phase mix, patient scale) has this median wall."""
    rng = np.random.default_rng(seed)
    meas, *_ = C.population(n, 0.0, 0.0, C.LIMA_CV_N, 0.0, C.PHASE_MIX, rng,
                            shape=C.LIMA_SHAPE, median_mm=1.0)
    factor = float(np.median(np.median(meas, 1)))
    return {"measured_median_mm": measured_median, "population_factor": round(factor, 4),
            "ed_anchor_mm": round(measured_median / factor, 3)}


def e5_seed_spread(seeds=range(20)):
    import e5_ja18 as E5  # Lima R3 E5, unchanged
    E5.C.SHAPE = np.asarray(C.LIMA_SHAPE)
    out = []
    for sd in seeds:
        out.append(E5.detectable_depth(C.LIMA_CV_N, np.asarray(C.LIMA_SHAPE), 0.5,
                                       np.random.default_rng(sd)))
    vals, counts = np.unique([v if v is not None else -1 for v in out], return_counts=True)
    return {"seeds": list(seeds), "depths": out,
            "histogram": {str(v): int(c) for v, c in zip(vals, counts)}}


def median_by_seed(medians, seeds=(C.E7_SEED, 20261030, 1, 2, 3)):
    rows = []
    for med in medians:
        for sd in seeds:
            r = C.detectable_depth(C.LIMA_CV_N, C.LIMA_SHAPE, 1.0, seed=sd, median_mm=med)
            rows.append({"median_mm": med, "seed": sd, "depth": r["depth"],
                         "sens_range": [round(x, 4) for x in r["sens_range"]] if r["sens_range"]
                         else None, "false_flag": round(r["false_flag"], 4)})
            print("median", med, "seed", sd, r["depth"], flush=True)
    return rows


def main(out_path):
    guard.refuse([], what="Lima R4 E6 (simulation; no case is opened)")
    factorial = []
    for median, sig_m in itertools.product((9.668, 5.7), (0.0, 0.5)):
        res = sweep(median, sig_m)
        for key, r in res.items():
            dev, floor = key.split("|") if "|" in key else ("none", "none")
            factorial.append({"median_mm": median, "sig_m": sig_m, "dev": dev, "floor": floor,
                              "depth": r["depth"], "false_flag_max": r.get("false_flag_max"),
                              "curve": r["curve"]})
            print(median, sig_m, key, r["depth"], r.get("false_flag_max"), flush=True)
    doc = {"experiment": "Lima R4 E6", "calibrate_version": C.CALIBRATE_VERSION,
           "seed": C.E7_SEED, "cv_n": C.LIMA_CV_N, "shape": list(C.LIMA_SHAPE),
           "design": {"n": C.N_PER_POPULATION, "replicates": C.REPLICATES,
                      "depths": list(C.DEPTHS), "prevalence": C.PREVALENCE,
                      "phase_mix": C.PHASE_MIX},
           "e5_floor_mm_at_sig0.5": dict(zip(C.TERRITORIES,
                                             np.round(RC_FACTOR * 0.5 / np.sqrt(K), 3).tolist())),
           "factorial": factorial,
           "anchors": [anchor_for(9.668), anchor_for(5.7)],
           "e5_own_function_20_seeds": e5_seed_spread()}
    doc["ja40_by_median_and_seed"] = median_by_seed(
        [9.668, doc["anchors"][0]["ed_anchor_mm"], 5.7, doc["anchors"][1]["ed_anchor_mm"]])
    Path(out_path).write_text(json.dumps(doc, indent=1) + "\n")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(HERE / "e6_depth_decomposition.json"))
