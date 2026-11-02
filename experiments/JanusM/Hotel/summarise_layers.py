"""Summarise layers_from_borders.py output (one or more JSON files) into the tables of the E1 note.

Usage: python summarise_layers.py OUT_JSON IN_JSON [IN_JSON ...]
"""
import json
import sys

import numpy as np


def q(v):
    v = np.asarray([x for x in v if x is not None], float)
    if v.size == 0:
        return None
    return {"n": int(v.size), "median": round(float(np.median(v)), 3),
            "p25": round(float(np.percentile(v, 25)), 3), "p75": round(float(np.percentile(v, 75)), 3)}


def main(out, ins):
    rows = [r for f in ins for r in json.load(open(f))]
    ok = [r for r in rows if r.get("status") == "ok"]
    con = [r for r in ok if r["contrast"]]
    s = {"n_cases": len(rows), "n_ok": len(ok), "n_contrast": len(con),
         "not_ok": {r["case"]: r.get("status") for r in rows if r.get("status") != "ok"},
         "cases": sorted(r["case"] for r in rows)}
    for name, grp in (("contrast", con), ("non_contrast", [r for r in ok if not r["contrast"]])):
        s[name] = {
            "lv_blood_hu": q([r["lv_blood_hu"] for r in grp]),
            "myo_hu_median": q([r["myo_hu_median"] for r in grp]),
            "myo_frac_below_m30": q([r["myo_frac_below_m30"] for r in grp]),
            "thickness_mm_median": q([r["thickness_mm_median"] for r in grp]),
            "myo_ml": q([r["myo_ml"] for r in grp]),
        }
    # edges (contrast only)
    e = [r["edges"] for r in con if "edges" in r]
    s["edges"] = {
        "endo_halfmax_mm (negative = edge inside the cavity label)": q([x.get("endo_halfmax_mm") for x in e]),
        "endo_10_90_width_mm": q([x.get("endo_10_90_width_mm") for x in e]),
        "epi_halfmax_mm (positive = edge inside the myocardium label)": q([x.get("epi_halfmax_mm") for x in e]),
        "plateau_blood": q([x["plateaus_blood_myocore_fat"][0] for x in e]),
        "plateau_myocardium_core": q([x["plateaus_blood_myocore_fat"][1] for x in e]),
        "plateau_epicardial_fat": q([x["plateaus_blood_myocore_fat"][2] for x in e]),
    }
    # third HU by inset
    ins_tab = {}
    for d in ("0.0", "0.75", "1.5", "2.25"):
        vals = [r["third_hu_mean_by_inset_mm"][d] for r in con if "third_hu_mean_by_inset_mm" in r]
        ins_tab[d] = {lab: q([v[i] for v in vals]) for i, lab in enumerate(("endo", "mid", "epi"))}
        ins_tab[d]["endo_over_epi_per_case"] = q([v[0] / v[2] if (v[0] is not None and v[2] not in (None, 0) and v[2] > 20) else None for v in vals])
    s["third_hu_by_inset_mm"] = ins_tab
    # TPR per segment (inset 1.5 mm)
    tpr_case_median = [np.median(list(r["aha_tpr"].values())) if r.get("aha_tpr") else None for r in con]
    tpr_case_sd = [np.std(list(r["aha_tpr"].values())) if r.get("aha_tpr") and len(r["aha_tpr"]) > 3 else None for r in con]
    s["tpr_inset1.5"] = {"per_case_median": q(tpr_case_median), "within_case_sd_across_segments": q(tpr_case_sd),
                          "segments_with_tpr_per_case": q([len(r.get("aha_tpr", {})) for r in con])}
    s["aha_ok"] = sum(r.get("aha_status") == "ok" for r in ok)
    s["aha_thickness_mm_all_segments"] = q([v for r in ok for v in r.get("aha_thickness_mm", {}).values()])
    # perturbation
    pt = {}
    for sg in ("0.5", "1.0", "1.5"):
        P = [r["perturb"][sg] for r in ok if "perturb" in r]
        if not P:
            continue
        dd = np.array([p["dice_myo_endo_mid_epi"] for p in P])
        pt[sg] = {"dice_myo": q(dd[:, 0]), "dice_endo_third": q(dd[:, 1]), "dice_mid_third": q(dd[:, 2]),
                  "dice_epi_third": q(dd[:, 3]),
                  "segment_thickness_abs_err_mm": q([p.get("thick_abs_err_mm") for p in P]),
                  "segment_tpr_abs_err_contrast": q([r["perturb"][sg].get("tpr_abs_err") for r in con if "perturb" in r])}
    s["perturb_by_border_rms_mm"] = pt
    json.dump(s, open(out, "w"), indent=1)
    print(json.dumps(s, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
