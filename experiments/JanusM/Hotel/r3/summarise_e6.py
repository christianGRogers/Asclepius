"""Summarise Hotel R3 E6: error of each signed-bias and ASSD estimator against the known truth.

The pass rule is fixed here, before the full run was read: an estimator meets JA16 if, for a constant shift of
+0.5 mm and of -0.5 mm, on every border, grid, orientation and wall (smooth and rough), |estimate - truth| <= 0.05 mm.
Reported beside it: the worst error over all shifts (0.1-1.0 mm), the error under JA15 random fields, and the
ASSD error.

    python experiments/JanusM/Hotel/r3/summarise_e6.py experiments/JanusM/Hotel/r3/e6_summary.json
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
BIAS = ("india_bias", "lima_bias", "sym_bias", "pp_bias", "vol_bias")
ASSD = ("voxel_assd", "sdf_assd", "pp_assd")


def main(out):
    rows = json.loads((HERE / "e6_estimators.json").read_text())["rows"]
    sh = [r for r in rows if r["kind"] == "shift"]
    fd = [r for r in rows if r["kind"] == "field"]
    res = {"n_rows": len(rows), "bias": {}, "assd": {}, "thickness": {}}
    for e in BIAS:
        d = {}
        for sgn in (+0.5, -0.5):
            err = np.array([r[e] - r["true_bias"] for r in sh if r["amt"] == sgn])
            d[f"shift{sgn:+.1f}"] = {"mean_err": round(float(err.mean()), 4),
                                     "max_abs_err": round(float(np.abs(err).max()), 4), "n": int(len(err))}
        alls = np.array([r[e] - r["true_bias"] for r in sh])
        rel = np.array([(r[e] - r["true_bias"]) / r["true_bias"] for r in sh if abs(r["true_bias"]) > 0.05])
        fe = np.array([r[e] - r["true_bias"] for r in fd])
        d["all_shifts_max_abs_err"] = round(float(np.abs(alls).max()), 4)
        d["all_shifts_mean_rel_err"] = round(float(rel.mean()), 4)
        d["fields_mean_err"] = round(float(fe.mean()), 4)
        d["fields_max_abs_err"] = round(float(np.abs(fe).max()), 4)
        d["by_grid_shift0.5_max_abs_err"] = {
            str(g): round(float(max(abs(r[e] - r["true_bias"]) for r in sh if abs(r["amt"]) == 0.5 and
                                    r["sp"] == list(g))), 4)
            for g in sorted({tuple(r["sp"]) for r in sh})}
        d["meets_JA16"] = bool(all(v["max_abs_err"] <= 0.05 for k, v in d.items() if k.startswith("shift")))
        res["bias"][e] = d
    for e in ASSD:
        err = np.array([r[e] - r["true_assd"] for r in rows])
        es = np.array([r[e] - r["true_assd"] for r in sh])
        ef = np.array([r[e] - r["true_assd"] for r in fd])
        res["assd"][e] = {"shifts_mean_err": round(float(es.mean()), 4), "shifts_max_abs_err":
                          round(float(np.abs(es).max()), 4), "fields_mean_err": round(float(ef.mean()), 4),
                          "fields_max_abs_err": round(float(np.abs(ef).max()), 4),
                          "all_mean_err": round(float(err.mean()), 4)}
    th = [r for r in sh if "thick_change_median_mm" in r]
    for amt in sorted({r["amt"] for r in th}):
        v = np.array([r["thick_change_median_mm"] for r in th if r["amt"] == amt])
        res["thickness"][f"endo_shift{amt:+.2f}"] = {"true": -amt, "mean": round(float(v.mean()), 4),
                                                     "max_abs_err": round(float(np.abs(v + amt).max()), 4),
                                                     "n": int(len(v))}
    Path(out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
