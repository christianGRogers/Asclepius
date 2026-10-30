"""Summarise E2 (harness.py): per model and nominal sigma, and against the realised border error.

    python summarise_e2.py E2_JSONL OUT_JSON
"""
import json
import sys
from collections import defaultdict

import numpy as np


def med(v):
    v = [x for x in v if x is not None and np.isfinite(x)]
    return round(float(np.median(v)), 3) if v else None


def main(src, out):
    cases = [json.loads(x) for x in open(src)]
    ok = [c for c in cases if "rows" in c]
    res = {"n_cases": len(cases), "n_used": len(ok), "skipped": [c.get("skip") for c in cases if "rows" not in c],
           "wall_mm_0p5": med([c["wall_mm_median_0p5"] for c in ok]),
           "voxels_per_third_0p5": med([c["voxels_per_third_0p5"] for c in ok])}
    by = defaultdict(list)
    for c in ok:
        for r in c["rows"]:
            by[(r["model"], r["sigma_nominal"])].append(r)
    table = []
    for (m, s), rs in sorted(by.items()):
        table.append({"model": m, "sigma_nominal": s, "n": len(rs),
                      "dice_myo": med([r["dice_myo"] for r in rs]),
                      "dice_subendo": med([r["dice_thirds"][0] for r in rs]),
                      "dice_mid": med([r["dice_thirds"][1] for r in rs]),
                      "dice_subepi": med([r["dice_thirds"][2] for r in rs]),
                      "assd_endo": med([r["assd_endo"] for r in rs]), "assd_epi": med([r["assd_epi"] for r in rs]),
                      "bias_endo": med([r["bias_endo"] for r in rs]), "bias_epi": med([r["bias_epi"] for r in rs]),
                      "seg_thick_err_mm": med([r["seg_thick_err_mm"] for r in rs]),
                      "sta": med([r["sta"] for r in rs])})
    res["table"] = table
    # collapse: subendocardial Dice against the realised mean border ASSD, random-field rows of the four models
    pts = [(0.5 * (r["assd_endo"] + r["assd_epi"]), r["dice_thirds"][0], r["model"], r["sta"], r["seg_thick_err_mm"])
           for c in ok for r in c["rows"] if r["model"] in ("golf", "india", "kilo", "hotel", "lima_c8")
           and r["sigma_nominal"] > 0 and np.isfinite(r["assd_endo"]) and np.isfinite(r["assd_epi"])]
    x = np.array([p[0] for p in pts]); y = np.array([p[1] for p in pts]); mdl = np.array([p[2] for p in pts])
    nominal_spread = {s: [t["dice_subendo"] for t in table if t["sigma_nominal"] == s
                          and t["model"] in ("golf", "india", "kilo", "hotel")] for s in (0.25, 0.5, 1.0)}
    res["nominal_spread_subendo_dice"] = {str(s): [min(v), max(v)] for s, v in nominal_spread.items() if v}
    coef = np.polyfit(x, y, 2)
    resid = y - np.polyval(coef, x)
    res["fit_subendo_dice_vs_realised_assd"] = {"quadratic": [round(float(c), 4) for c in coef],
                                                "residual_sd": round(float(resid.std()), 4),
                                                "total_sd": round(float(y.std()), 4)}
    res["mean_residual_by_model"] = {m: round(float(resid[mdl == m].mean()), 4) for m in np.unique(mdl)}
    bins = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.7, 1.0, 1.5]
    res["by_realised_assd_bin"] = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        sel = (x >= lo) & (x < hi)
        if sel.sum() < 3:
            continue
        row = {"assd_mm": f"{lo}-{hi}", "n": int(sel.sum()), "dice_subendo": med(y[sel])}
        for m in ("golf", "india", "kilo", "hotel", "lima_c8"):
            s2 = sel & (mdl == m)
            if s2.sum() >= 3:
                row[m] = med(y[s2])
        row["sta"] = med([pts[i][3] for i in np.nonzero(sel)[0]])
        row["seg_thick_err_mm"] = med([pts[i][4] for i in np.nonzero(sel)[0]])
        res["by_realised_assd_bin"].append(row)
    # realised / nominal ratio ("gain") per model, at sigma 0.5 and 1.0
    res["gain_realised_over_nominal"] = {
        m: {str(s): med([0.5 * (r["assd_endo"] + r["assd_epi"]) / s for r in by[(m, s)]]) for s in (0.5, 1.0)}
        for m in ("golf", "india", "kilo", "hotel", "lima_c8")}
    json.dump(res, open(out, "w"), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != "table"}, indent=1))
    for t in table:
        print(t)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
