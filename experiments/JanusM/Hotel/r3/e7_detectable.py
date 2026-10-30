"""Hotel R3 E7: re-run Lima's E3 (JA18 rule C) with a measured cv_n and segment shape, and fix the detectable depth
that the page prints instead of a sensitivity (Round 2 ruling §7 item 3).

A simulation; no case is opened. It imports Lima's own functions unchanged (experiments/JanusM/Lima/calibrate_sim.py:
population, rule_c_scores, calibrate_c, territory_flags) and changes only their inputs and the read-out:

1. **Measured inputs from a JSON with JM-0R's keys** (Lima's jm0b_readout keys, which JA23 carries into JM-0R):
   `rel_thickness_by_segment_mean_sd` (the 16-segment shape), `rel_thickness_shape_corrected_sd` (cv_n) and
   `median_thickness_mm`. Today the only measured values are Lima's self-test on the 23 allowed public hearts
   (1.5 mm model-made labels; experiments/JanusM/Lima/local_check_summary.json, guarded when it was made). When the
   lead posts JM-0R, the same command runs on its summary.
2. **No double count.** cv_n measured on Janus-M 0's own borders already contains Janus-M 0's measurement error.
   The deployed table measures patients with the same model, so the primary run adds no extra error (sig_m = 0).
   Lima's E3 added sig_m on top; that is kept as a sensitivity (sig_m 0.25 and 0.5 mm), which double-counts.
3. **A finer depth grid and replicates:** relative depth 0.10-0.60 in 0.05 steps, 4 independent populations of
   2000 per condition; the detectable depth is the smallest depth whose territory sensitivity is >= 0.80 in the
   mean of the replicates, reported with the replicate range.
4. **Hotel's F1 floor (JA18).** A rule-C territory flag shows only if the territory's shape-corrected mean thinning
   (mm) relative to the patient's remote segments exceeds RC_terr. Swept: 0 (no floor), 0.35, 0.7 and 1.0 mm.
   RC_terr comes from the first 20 decision double reads; E4 (Hotel R2) gives 0.74 mm per segment at 0.25 mm read
   noise, about 0.74 / sqrt(5) = 0.33 mm for a five-segment territory mean if segments were independent.

    python experiments/JanusM/Hotel/r3/e7_detectable.py OUT.json [--inputs JM0R_OR_SELFTEST.json] [--quick]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "experiments/JanusM/Lima"))
import calibrate_sim as C  # noqa: E402

DEFAULT_INPUTS = ROOT / "experiments/JanusM/Lima/local_check_summary.json"
TNAMES = list(C.TERR16)


def read_inputs(path):
    d = json.loads(Path(path).read_text())
    shape = np.array([d["rel_thickness_by_segment_mean_sd"][str(k)][0] for k in range(1, 17)], float)
    med = d["median_thickness_mm"]
    if isinstance(med, (list, tuple)):  # [q25, median, q75] or similar
        med = med[1] if len(med) >= 3 else med[0]
    if isinstance(med, dict):
        med = med.get("median", med.get("p50"))
    return {"shape": shape, "cv_n": float(d["rel_thickness_shape_corrected_sd"]), "median_mm": float(med),
            "source": str(Path(path).relative_to(ROOT)) if str(path).startswith(str(ROOT)) else str(path)}


def f1_deviation(meas, shape):
    """Per patient x territory: shape-corrected mean thinning (mm) of the territory against the patient's remote
    segments (those outside it). Positive = thinner than expected."""
    n = meas.shape[0]
    out = np.zeros((n, 3))
    for j, t in enumerate(TNAMES):
        segs = [s - 1 for s in C.TERR16[t]]
        rem = [s for s in range(16) if s not in segs]
        level = np.median(meas[:, rem] / shape[rem], 1)  # the patient's remote level, shape-corrected
        exp = level[:, None] * shape[segs]
        out[:, j] = (exp - meas[:, segs]).mean(1)
    return out


def one(prev, depth, cv_n, sig_m, mix, rcs, seed):
    rng = np.random.default_rng(seed)
    meas, lesion, sick, terr, ph = C.population(2000, prev, depth, cv_n, sig_m, mix, rng)
    z = C.rule_c_scores(meas)
    cut, k = C.calibrate_c(z, rng=np.random.default_rng(seed + 1))
    tf = C.territory_flags(z < cut)
    dev = f1_deviation(meas, C.SHAPE)
    out = {"k_mad": k}
    sick_idx = np.nonzero(sick)[0]
    for rc in rcs:
        f = tf & (dev > rc)
        hit = np.array([f[i, TNAMES.index(terr[i])] for i in sick_idx])
        out[str(rc)] = {"false_flag": float(f.any(1)[~sick].mean()),
                        "sens": float(hit.mean()) if len(hit) else float("nan")}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--inputs", default=str(DEFAULT_INPUTS))
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    inp = read_inputs(a.inputs)
    C.SHAPE = inp["shape"]  # Lima's population() reads these module globals
    C.ED_MEDIAN_MM = inp["median_mm"] / 1.0  # the measured median replaces the 5.7 mm CT anchor (phase still mixed)
    depths = np.round(np.arange(0.10, 0.601, 0.05), 2) if not a.quick else [0.3, 0.4]
    reps = 4 if not a.quick else 1
    rcs = (0.0, 0.35, 0.7, 1.0)
    mixes = {"mixed": {"ED": 0.4, "MD": 0.4, "SYS": 0.2}, "all_ED": {"ED": 1.0, "MD": 0.0, "SYS": 0.0}}
    scen = [("measured_no_double_count", inp["cv_n"], 0.0),
            ("lima_style_sig0.25", inp["cv_n"], 0.25), ("lima_style_sig0.5", inp["cv_n"], 0.5),
            ("cv0.06", 0.06, 0.0), ("cv0.12", 0.12, 0.0), ("cv0.15", 0.15, 0.0)]
    if a.quick:
        scen = scen[:1]
    grid = []
    seed = 31000
    for sname, cv, sig in scen:
        for mname, mix in mixes.items():
            for prev in (0.1, 0.3):
                for dep in depths:
                    rr = []
                    for _r in range(reps):
                        seed += 2
                        rr.append(one(prev, float(dep), cv, sig, mix, rcs, seed))
                    row = {"scenario": sname, "cv_n": cv, "sig_m": sig, "mix": mname, "prev": prev,
                           "depth": float(dep), "k_mad": [x["k_mad"] for x in rr]}
                    for rc in rcs:
                        row[f"rc{rc}"] = {"false_flag": [round(x[str(rc)]["false_flag"], 4) for x in rr],
                                          "sens": [round(x[str(rc)]["sens"], 4) for x in rr]}
                    grid.append(row)
            print(sname, mname, "done", flush=True)
    # detectable depth: smallest depth with mean sensitivity >= 0.80
    det = {}
    for sname, _cv, _sig in scen:
        for mname in mixes:
            for prev in (0.1, 0.3):
                for rc in rcs:
                    rows = sorted([g for g in grid if g["scenario"] == sname and g["mix"] == mname and
                                   g["prev"] == prev], key=lambda g: g["depth"])
                    hit = [g for g in rows if np.mean(g[f"rc{rc}"]["sens"]) >= 0.80]
                    ff = max(max(g[f"rc{rc}"]["false_flag"]) for g in rows)
                    det[f"{sname}|{mname}|prev{prev}|rc{rc}"] = {
                        "depth80": hit[0]["depth"] if hit else ">0.60",
                        "sens_range_at_depth80": [min(hit[0][f"rc{rc}"]["sens"]), max(hit[0][f"rc{rc}"]["sens"])]
                        if hit else None,
                        "max_false_flag": ff}
    res = {"inputs": {"source": inp["source"], "cv_n": inp["cv_n"], "median_mm": inp["median_mm"],
                      "shape": [round(float(x), 3) for x in inp["shape"]]},
           "design": {"n_per_population": 2000, "reps": reps, "depths": [float(x) for x in depths],
                      "rc_terr_mm": list(rcs)},
           "detectable_depth": det, "grid": grid}
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    for k, v in det.items():
        if "|mixed|prev0.1|" in k:
            print(k, v)


if __name__ == "__main__":
    main()
