"""Summarise Hotel R2 E2 (harness), E3 (rest TPR) and E5 (depth), and derive E4 (the calibration floor).

E4 needs no new simulation. A read is modelled as an independent E2 perturbation of the true borders, so the
difference between two reads of one segment's thickness has SD sqrt(2) * SD(single error). The repeatability
coefficient RC = 1.96 * sqrt(2) * SD is the smallest change in one segment that two reads can tell apart at 95 %.
A Stage A threshold below RC flags noise.

    python experiments/JanusM/Hotel/r2/summarise_r2.py experiments/JanusM/Hotel/r2/summary.json
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def m(x):
    return round(float(np.mean(x)), 3)


def main(out):
    e2 = json.loads((HERE / "e2_harness.json").read_text())
    e3 = json.loads((HERE / "e3_tpr.json").read_text())
    e5 = json.loads((HERE / "e5_depth.json").read_text())
    res = {"E2_A_round1_conventions": {}, "E2_B_harness_0p5mm": {}, "E2_B_bias": [], "E4_floor": {},
           "E3_tpr": {}, "E5_depth": e5}
    allpts = []
    for name, d in e2["A"].items():
        tab = {}
        for sig in sorted({r["sigma_mm"] for r in d["rows"]}):
            rr = [r for r in d["rows"] if r["sigma_mm"] == sig]
            tab[str(sig)] = {"subendo_dice": m([r["dice_third"][0] for r in rr]),
                             "myo_dice": m([r["dice_myo"] for r in rr]),
                             "endo_mean_abs_d_mm": m([r["endo_mean_abs_d_mm"] for r in rr]),
                             "epi_mean_abs_d_mm": m([r["epi_mean_abs_d_mm"] for r in rr]),
                             "seg_thick_abs_err_mm": m([r["seg_thick_abs_err_mm"] for r in rr])}
            allpts += [(0.5 * (r["endo_mean_abs_d_mm"] + r["epi_mean_abs_d_mm"]), r["dice_third"][0], name) for r in rr]
        res["E2_A_round1_conventions"][name] = {"grid_mm": d["grid_mm"], "by_nominal_sigma": tab}
    rows = e2["B"]["rows"]
    for corr in sorted({r["corr_mm"] for r in rows if r["kind"] == "random"}):
        tab = {}
        for sig in sorted({r["sigma_mm"] for r in rows if r["kind"] == "random"}):
            rr = [r for r in rows if r["kind"] == "random" and r["corr_mm"] == corr and r["sigma_mm"] == sig]
            se = np.concatenate([r["seg_thick_err_signed_mm"] for r in rr])
            tab[str(sig)] = {"subendo_dice": m([r["dice_third"][0] for r in rr]),
                             "third_dice": [m([r["dice_third"][k] for r in rr]) for k in range(3)],
                             "myo_dice": m([r["dice_myo"] for r in rr]),
                             "endo_mean_abs_d_mm": m([r["endo_mean_abs_d_mm"] for r in rr]),
                             "seg_thick_abs_err_mm": m([r["seg_thick_abs_err_mm"] for r in rr]),
                             "seg_thick_err_sd_mm": round(float(np.std(se)), 3),
                             "kim_flip_mean": m([np.mean(list(r["kim_bin_flip"].values())) for r in rr])}
            allpts += [(0.5 * (r["endo_mean_abs_d_mm"] + r["epi_mean_abs_d_mm"]), r["dice_third"][0], "harness")
                       for r in rr]
            if corr == 8.0:
                sd = float(np.std(se))
                res["E4_floor"][str(sig)] = {"single_read_seg_thick_sd_mm": round(sd, 3),
                                             "repeatability_coeff_mm": round(1.96 * np.sqrt(2) * sd, 2)}
        res["E2_B_harness_0p5mm"][f"corr_{corr}"] = tab
    for r in rows:
        if r["kind"] == "bias":
            res["E2_B_bias"].append({"border": r["border"], "bias_mm": r["bias_mm"],
                                     "subendo_dice": round(r["dice_third"][0], 3),
                                     "myo_dice": round(r["dice_myo"], 3),
                                     "seg_thick_abs_err_mm": round(r["seg_thick_abs_err_mm"], 3),
                                     "kim_flip": r["kim_bin_flip"]})
    # does achieved displacement explain Dice across conventions? linear fit, residual by source
    x = np.array([p[0] for p in allpts])
    y = np.array([p[1] for p in allpts])
    A = np.vstack([x, np.ones_like(x)]).T
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = y - A @ coef
    res["E2_collapse"] = {"fit_subendo_dice_vs_mean_abs_d": [round(float(c), 3) for c in coef],
                          "r2": round(float(1 - resid.var() / y.var()), 3),
                          "mean_residual_by_source": {s: round(float(resid[[p[2] == s for p in allpts]].mean()), 4)
                                                      for s in sorted({p[2] for p in allpts})}}
    # E3 tables
    def get(**k):
        for r in e3["rows"]:
            if all(r[a] == b for a, b in k.items()):
                return r["tpr_read"]
    for wall in ("free", "septum"):
        t = {}
        for edge in (0.8, 1.2, 1.6, 2.4, 3.2, 4.7):
            t[str(edge)] = {f"v{v}_g{g}": [get(wall=wall, T_mm=10.0, tpr_true=tt, edge1090_mm=edge, voxel_mm=v,
                                               guard_mm=g, d_endo_mm=0, d_epi_mm=0) for tt in (1.10, 1.00, 0.85)]
                            for v in (0.5, 1.5) for g in (0.0, 1.0)}
        res["E3_tpr"][f"{wall}_10mm_[1.10,1.00,0.85]"] = t
    t = {}
    for T in (6.0, 8.0, 10.0, 12.0):
        t[str(T)] = {f"d_endo{de}_d_epi{dp}": get(wall="free", T_mm=T, tpr_true=1.10, edge1090_mm=1.2, voxel_mm=0.5,
                                                   guard_mm=1.0, d_endo_mm=de, d_epi_mm=dp)
                     for de, dp in ((0, 0), (0.5, 0), (-0.5, 0), (0, 0.5), (0, -0.5))}
    res["E3_tpr"]["free_true1.10_edge1.2_v0.5_g1.0_by_wall_and_border_error"] = t
    Path(out).write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps({k: res[k] for k in ("E2_collapse", "E4_floor")}, indent=1))
    for n, d in res["E2_A_round1_conventions"].items():
        print(n, {s: (v["subendo_dice"], v["endo_mean_abs_d_mm"]) for s, v in d["by_nominal_sigma"].items()})
    for c, d in res["E2_B_harness_0p5mm"].items():
        print(c, {s: (v["subendo_dice"], v["endo_mean_abs_d_mm"], v["seg_thick_abs_err_mm"], v["kim_flip_mean"])
                  for s, v in d.items()})
    for b in res["E2_B_bias"]:
        print(b)
    print(json.dumps(res["E3_tpr"]["free_true1.10_edge1.2_v0.5_g1.0_by_wall_and_border_error"]))
    print(json.dumps(res["E3_tpr"]["septum_10mm_[1.10,1.00,0.85]"]["1.2"]))


if __name__ == "__main__":
    main(sys.argv[1])
