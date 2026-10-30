"""E8 (Round 4, #205 item 2): why Lima E5 prints 45 % and Hotel E7 prints 35 %, on one seed.

Simulation only: no case, no image, no Girder read. ``janusm.guard.refuse([])`` is called first so
the script follows the Janus-M entry-point rule, but it names nothing.

Both numbers come from the same population (``janusm.calibrate.population``, Lima's) and the same
rule C (``rule_c_scores`` + ``calibrate_c``). They differ in four inputs:

==============  ===========================  ==============================================
input           Hotel E7 (shipped as S3)     Lima E5 (``Lima/r3/e5_ja18.py``)
==============  ===========================  ==============================================
median_mm       9.668 (Lima's self-test)     5.7 (Chen 2025 ED anchor; ``ED_MEDIAN_MM``)
F1 deviation    shape-corrected vs remote    raw territory mean - remote median
F1 floor        rc = 1.0 mm (JA40)           RC = 1.96 * sqrt(2) * sig_m / sqrt(k)
added error     sig_m = 0                    sig_m = 0.5 mm
==============  ===========================  ==============================================

(E5's design is also 1 population of 4000 per depth from 0.15, one sequential rng; S3 uses 4 x 2000
from 0.10. That is run separately at the end.)

Every row below uses S3's design and seeds (``detectable_depths``' scheme from ``E7_SEED``), and every
F1 variant is read on the **same** simulated hearts, so a change between rows is the input alone.

    python experiments/JanusM/Hotel/r4/e8_e5_vs_e7.py OUT_JSON [--seeds 5]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))

from janusm import calibrate as C  # noqa: E402
from janusm.guard import refuse  # noqa: E402

TERR = C.TERRITORIES


def lima_f1(meas, sig_r):
    """Lima E5's F1 (copied from ``e5_ja18.f1_pass``): raw territory mean below the remote median
    by more than 1.96 * sqrt(2) * sig_r / sqrt(k)."""
    out = np.zeros((meas.shape[0], 3), bool)
    for j, t in enumerate(TERR):
        idx = [s - 1 for s in C.TERR16[t]]
        rest = [i for i in range(16) if i not in idx]
        dev = meas[:, idx].mean(1) - np.median(meas[:, rest], 1)
        out[:, j] = dev < -1.96 * np.sqrt(2) * sig_r / np.sqrt(len(idx))
    return out


def one(depth, seed, *, median_mm, sig_m, shape, cv_n):
    """One population; territory sensitivity and false flags for each F1 variant."""
    rng = np.random.default_rng(seed)
    meas, _, sick, terr, _ = C.population(
        C.N_PER_POPULATION, C.PREVALENCE, depth, cv_n, sig_m, C.PHASE_MIX, rng,
        shape=shape, median_mm=median_mm)
    z = C.rule_c_scores(meas)
    cut, _ = C.calibrate_c(z, rng=np.random.default_rng(seed + 1))
    tf = C.territory_flags(z < cut)
    dev = C.f1_deviation(meas, shape)
    variants = {
        "rule_c_only": tf,
        "hotel_f1_rc1.0": tf & (dev > 1.0),
        "hotel_f1_rc1.0_scaled": tf & (dev > 1.0 * median_mm / C.LIMA_MEDIAN_MM),
        "lima_f1_sig0.5": tf & lima_f1(meas, 0.5),
    }
    si = np.nonzero(sick)[0]
    res = {}
    for k, f in variants.items():
        hit = np.array([f[i, TERR.index(terr[i])] for i in si])
        res[k] = (float(hit.mean()), float(f.any(1)[~sick].mean()))
    res["pop_median_mm"] = float(np.median(np.median(meas[~sick], 1)))
    return res


def depth_rows(seed0, **kw):
    """S3's design: depths 0.10..0.60, 4 replicates, seed sequence seed0 + 2, + 4, ..."""
    s, table = seed0, []
    for depth in C.DEPTHS:
        reps = []
        for _ in range(C.REPLICATES):
            s += 2
            reps.append(one(depth, s, **kw))
        table.append((depth, reps))
    out = {}
    for v in ("rule_c_only", "hotel_f1_rc1.0", "hotel_f1_rc1.0_scaled", "lima_f1_sig0.5"):
        d80 = next((d for d, reps in table
                    if np.mean([r[v][0] for r in reps]) >= C.SENSITIVITY_TARGET), None)
        out[v] = {"depth80": d80,
                  "sens_by_depth": {f"{d:.2f}": round(float(np.mean([r[v][0] for r in reps])), 3)
                                    for d, reps in table},
                  "max_false_flag": round(max(r[v][1] for _, reps in table for r in reps), 4)}
    out["pop_median_mm"] = round(float(np.median([r["pop_median_mm"] for _, reps in table
                                                   for r in reps])), 3)
    return out


def lima_original(seed):
    """E5's own ``detectable_depth`` design (4000 per depth from 0.15, one rng), Lima F1, sig 0.5,
    median 5.7, at a fresh seed: how much the printed step moves between seeds."""
    rng = np.random.default_rng(seed)
    for depth in np.arange(0.15, 0.651, 0.05):
        meas, _, sick, terr, _ = C.population(4000, 0.1, depth, C.LIMA_CV_N, 0.5, C.PHASE_MIX, rng,
                                              shape=C.LIMA_SHAPE, median_mm=C.ED_MEDIAN_MM)
        cut, _ = C.calibrate_c(C.rule_c_scores(meas))
        tf = C.territory_flags(C.rule_c_scores(meas) < cut) & lima_f1(meas, 0.5)
        if np.mean([tf[i, TERR.index(terr[i])] for i in np.nonzero(sick)[0]]) >= 0.8:
            return round(float(depth), 2)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--seeds", type=int, default=5)
    a = ap.parse_args()
    refuse([], what="E8 (simulation; no case)")
    shape, cv = np.array(C.LIMA_SHAPE), C.LIMA_CV_N
    grid = {}
    for median in (C.ED_MEDIAN_MM, C.LIMA_MEDIAN_MM):
        for sig in (0.0, 0.5):
            key = f"median{median}|sig{sig}"
            grid[key] = depth_rows(C.E7_SEED, median_mm=median, sig_m=sig, shape=shape, cv_n=cv)
            print(key, {k: v["depth80"] if isinstance(v, dict) else v
                        for k, v in grid[key].items()}, flush=True)
    # The F1 floor in mm against the wall: depth depends on rc / median only when sig_m = 0.
    sweep = {}
    for median in (4.5, 5.0, 5.7, 6.5, 7.0, 8.0, 9.0, 9.668):
        r = depth_rows(C.E7_SEED, median_mm=median, sig_m=0.0, shape=shape, cv_n=cv)
        sweep[str(median)] = {"depth80_rc1.0": r["hotel_f1_rc1.0"]["depth80"],
                              "pop_median_mm": r["pop_median_mm"],
                              "rc_over_pop_median": round(1.0 / r["pop_median_mm"], 4)}
        print("sweep", median, sweep[str(median)], flush=True)
    seeds = {}
    for k in range(a.seeds):
        s0 = C.E7_SEED + 1000 * (k + 1)
        seeds[str(s0)] = {
            m: depth_rows(s0, median_mm=m, sig_m=0.0, shape=shape, cv_n=cv)["hotel_f1_rc1.0"][
                "depth80"] for m in (C.ED_MEDIAN_MM, C.LIMA_MEDIAN_MM)}
        print("seed", s0, seeds[str(s0)], flush=True)
    lima_seeds = {str(s): lima_original(s) for s in (20261030, 1, 2, 3, 4)}
    print("lima original design", lima_seeds, flush=True)
    out = {"inputs": {"cv_n": cv, "shape": list(C.LIMA_SHAPE), "seed": C.E7_SEED,
                      "calibrate_version": C.CALIBRATE_VERSION},
           "grid": grid, "median_sweep": sweep, "other_seeds_rc1.0_sig0": seeds,
           "lima_e5_design_by_seed": lima_seeds}
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
