"""India R4 E11: why Lima E5 printed 45 % and Hotel E7 35 % for nominally the same inputs (#205 item 2).

CPU simulation only (no case, no image). Every row uses the shipped ``janusm.calibrate`` population,
rule C and mirror-null calibration, on the same seed sequence (E7's, first seed 31000), and changes
one factor at a time between Hotel E7 (as shipped in S3) and Lima E5 (``Lima/r3/e5_ja18.py``):

- ``median_mm``: the population's median wall (Hotel E7 9.668 mm, Lima E5 5.7 mm);
- F1's deviation: Hotel's shape-corrected one (``calibrate.f1_deviation``) or Lima's raw one
  (territory mean minus the remote median, no shape correction);
- F1's floor: Hotel's fixed 1.0 mm, or Lima's RC = 1.96 * sqrt(2) * sig_m / sqrt(k) (k segments in
  the territory, about 0.26-0.31 mm at sig_m 0.5);
- ``sig_m``: 0 (Hotel) or 0.5 mm added on top of cv_n (Lima).

Read-out exactly as JA40 / S3: 4 replicates of 2000, depths 0.10-0.60, smallest depth with mean
territory sensitivity >= 0.80.

    python experiments/JanusM/India/r4/e11_f1_reconcile.py experiments/JanusM/India/r4/e11_f1_reconcile.json
"""

from __future__ import annotations

import json
import sys

import numpy as np

from janusm import calibrate as C
from janusm import guard

TERR = C.TERRITORIES
RC_FACTOR = 1.96 * np.sqrt(2)


def lima_dev(meas):
    """Lima E5's F1 quantity, sign flipped so + = thinner: remote median minus territory mean (mm)."""
    out = np.zeros((meas.shape[0], 3))
    for j, t in enumerate(TERR):
        idx = [s - 1 for s in C.TERR16[t]]
        rest = [i for i in range(16) if i not in idx]
        out[:, j] = np.median(meas[:, rest], 1) - meas[:, idx].mean(1)
    return out


def floors(kind, sig_m):
    if kind == "hotel_1mm":
        return np.array([1.0, 1.0, 1.0])
    if kind == "lima_rc":
        return np.array([RC_FACTOR * sig_m / np.sqrt(len(C.TERR16[t])) for t in TERR])
    if kind == "none":
        return np.array([-np.inf] * 3)
    raise ValueError(kind)


def one(depth, cv_n, sig_m, median_mm, dev_kind, floor_kind, seed):
    rng = np.random.default_rng(seed)
    meas, _, sick, terr, _ = C.population(
        C.N_PER_POPULATION, C.PREVALENCE, depth, cv_n, sig_m, C.PHASE_MIX, rng,
        shape=C.LIMA_SHAPE, median_mm=median_mm,
    )
    z = C.rule_c_scores(meas)
    cut, _ = C.calibrate_c(z, rng=np.random.default_rng(seed + 1))
    tf = C.territory_flags(z < cut)
    dev = C.f1_deviation(meas, C.LIMA_SHAPE) if dev_kind == "hotel" else lima_dev(meas)
    f = tf & (dev > floors(floor_kind, sig_m)[None, :])
    si = np.nonzero(sick)[0]
    hit = np.array([f[i, TERR.index(terr[i])] for i in si])
    return float(hit.mean()), float(f.any(1)[~sick].mean()), float(np.median(meas))


def depth_of(cv_n, sig_m, median_mm, dev_kind, floor_kind, seed=C.E7_SEED):
    s = seed
    table, medians = [], []
    for depth in C.DEPTHS:
        reps = []
        for _ in range(C.REPLICATES):
            s += 2  # E7's seed sequence, as calibrate.detectable_depths
            reps.append(one(depth, cv_n, sig_m, median_mm, dev_kind, floor_kind, s))
        table.append({"depth": depth, "sens": [round(r[0], 4) for r in reps],
                      "false_flag": [round(r[1], 4) for r in reps]})
        medians += [r[2] for r in reps]
    hit = [t for t in table if np.mean(t["sens"]) >= C.SENSITIVITY_TARGET]
    return {
        "depth": hit[0]["depth"] if hit else None,
        "sens_at_depth": hit[0]["sens"] if hit else None,
        "max_false_flag": max(max(t["false_flag"]) for t in table),
        "simulated_population_median_mm": round(float(np.median(medians)), 3),
        "table": table,
    }


ROWS = [
    # name, sig_m, median, F1 deviation, F1 floor
    ("A Hotel E7 as shipped (S3 test)", 0.0, 9.668, "hotel", "hotel_1mm"),
    ("B = A, median 5.7", 0.0, 5.7, "hotel", "hotel_1mm"),
    ("C = A, sig_m 0.5", 0.5, 9.668, "hotel", "hotel_1mm"),
    ("D = B, sig_m 0.5 (Hotel F1, Lima's median and error)", 0.5, 5.7, "hotel", "hotel_1mm"),
    ("E = D, Lima's RC floor", 0.5, 5.7, "hotel", "lima_rc"),
    ("F Lima E5 procedure (raw dev, Lima RC, 5.7, sig_m 0.5)", 0.5, 5.7, "lima", "lima_rc"),
    ("G = F, Hotel's 1.0 mm floor", 0.5, 5.7, "lima", "hotel_1mm"),
    ("H = F, median 9.668", 0.5, 9.668, "lima", "lima_rc"),
    ("I rule C alone, 5.7, sig_m 0.5", 0.5, 5.7, "hotel", "none"),
    ("J rule C alone, 9.668, sig_m 0", 0.0, 9.668, "hotel", "none"),
    ("K = B, median 5.122 (population median 5.7 after the phase mix)", 0.0, 5.122, "hotel", "hotel_1mm"),
    ("L = A, median 4.2 (R3 window, low end)", 0.0, 4.2, "hotel", "hotel_1mm"),
    ("M = A, median 6.5", 0.0, 6.5, "hotel", "hotel_1mm"),
    ("N = A, median 8.0 (R3 window, high end)", 0.0, 8.0, "hotel", "hotel_1mm"),
    ("O = A, median 8.688 (population median 9.668 after the phase mix)", 0.0, 8.688, "hotel", "hotel_1mm"),
]


def lima_single_population(seed):
    """Lima E5's own read-out: one population of 4000 per depth (0.15-0.65), one shared stream,
    no replicates; Lima's F1 (raw deviation, RC from sig_m 0.5), median 5.7."""
    rng = np.random.default_rng(seed)
    for depth in np.arange(0.15, 0.651, 0.05):
        meas, _, sick, terr, _ = C.population(4000, 0.1, depth, C.LIMA_CV_N, 0.5, C.PHASE_MIX, rng,
                                              shape=C.LIMA_SHAPE, median_mm=5.7)
        z = C.rule_c_scores(meas)
        cut, _ = C.calibrate_c(z)
        f = C.territory_flags(z < cut) & (lima_dev(meas) > floors("lima_rc", 0.5)[None, :])
        hit = np.mean([f[i, TERR.index(terr[i])] for i in np.nonzero(sick)[0]])
        if hit >= 0.8:
            return round(float(depth), 2)
    return None


def main(out):
    guard.refuse([], what="India R4 E11 (simulation; no case opened)")  # nothing to open; recorded
    rows = []
    for name, sig_m, med, dev, fl in ROWS:
        r = depth_of(C.LIMA_CV_N, sig_m, med, dev, fl)
        r.update(name=name, cv_n=C.LIMA_CV_N, sig_m=sig_m, median_mm=med, f1_deviation=dev,
                 f1_floor=fl, f1_floor_mm=[round(float(x), 3) for x in floors(fl, sig_m)])
        print(f"{name:62s} depth {r['depth']}  pop median {r['simulated_population_median_mm']}"
              f"  maxFF {r['max_false_flag']:.3f}", flush=True)
        rows.append(r)
    # check: the shipped function gives row A and B exactly
    ship = {m: C.detectable_depth(C.LIMA_CV_N, C.LIMA_SHAPE, 1.0, seed=C.E7_SEED, median_mm=m)["depth"]
            for m in (9.668, 5.7)}
    # phase-mix factor: simulated population median / median_mm (cv_n 0.088, no thinning)
    rng = np.random.default_rng(7)
    m1 = C.population(200000, 0.0, 0.0, C.LIMA_CV_N, 0.0, C.PHASE_MIX, rng, median_mm=1.0)[0]
    factor = float(np.median(m1))
    lima_seeds = {str(sd): lima_single_population(sd) for sd in [20261030] + list(range(1, 21))}
    print("Lima single-population read-out by seed:", lima_seeds)
    json.dump({"calibrate_version": C.CALIBRATE_VERSION, "seed": C.E7_SEED, "rows": rows,
               "lima_single_population_by_seed": lima_seeds,
               "shipped_detectable_depth": {str(k): v for k, v in ship.items()},
               "phase_mix_median_factor": round(factor, 4)}, open(out, "w"), indent=1)
    print("shipped:", ship, "phase factor", round(factor, 4))


if __name__ == "__main__":
    main(sys.argv[1])
