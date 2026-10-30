"""Pool E5 (harness), E6 (depth / sectors) and E7 (TPR phantom) per-case JSON into results/summary_r2.json.

    python summarise_r2.py E5_DIR E6_DIR E7_DIR
"""
import glob, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def load(d):
    return [json.load(open(f)) for f in sorted(glob.glob(os.path.join(d, "s*.json")))]


def q(v, ps=(50, 10, 90)):
    v = [x for x in v if x is not None and not (isinstance(x, float) and np.isnan(x))]
    return [round(float(np.percentile(v, p)), 4) for p in ps] + [len(v)] if v else None


def e5(rows):
    ok = [r for r in rows if r.get("ok")]
    out = {"n_cases": len(ok), "excluded": {}, "models": {}, "U": {}}
    for r in rows:
        if not r.get("ok"):
            out["excluded"][r["why"][:40]] = out["excluded"].get(r["why"][:40], 0) + 1
    for m in ("golf", "india", "kilo", "hotel"):
        res = {}
        for sig in (0.5, 1.0):
            rr = [x for r in ok for x in r["models"][m]["runs"] if x["sigma"] == sig]
            res[f"sigma{sig}"] = dict(
                dice_myo=q([x["dice_myo"] for x in rr]),
                dice_subendo=q([x["dice_thirds"][0] for x in rr]),
                realised_endo_assd=q([x["border"]["endo"]["assd"] for x in rr if x["border"]["endo"]]),
                realised_epi_assd=q([x["border"]["epi"]["assd"] for x in rr if x["border"]["epi"]]))
        res["uniform_0.5mm_endo_shift_realised"] = q([r["models"][m]["uniform_0p5_endo"]["assd"] for r in ok
                                                      if r["models"][m]["uniform_0p5_endo"]])
        out["models"][m] = res
    keys = sorted({(x["kind"], x["sigma"], x["corr"]) for r in ok for x in r["U"]})
    for k in keys:
        rr = [x for r in ok for x in r["U"] if (x["kind"], x["sigma"], x["corr"]) == k]
        out["U"][f"{k[0]} s{k[1]} c{k[2]}"] = dict(
            dice_myo=q([x["dice_myo"] for x in rr]), dice_subendo=q([x["dice_thirds"][0] for x in rr]),
            endo_assd=q([x["border"]["endo"]["assd"] for x in rr if x["border"]["endo"]]),
            epi_assd=q([x["border"]["epi"]["assd"] for x in rr if x["border"]["epi"]]),
            endo_bias=q([x["border"]["endo"]["bias"] for x in rr if x["border"]["endo"]]),
            epi_bias=q([x["border"]["epi"]["bias"] for x in rr if x["border"]["epi"]]),
            sta=q([x["sta"] for x in rr]), thick_err=q([x["thick_err_median"] for x in rr]),
            thick_bias=q([x["thick_bias_median"] for x in rr]))
    out["septal_arc_deg"] = q([r.get("septal_arc_deg") for r in ok])
    return out


def e6(rows):
    ok = [r for r in rows if r.get("ok")]
    runs = [x for r in ok for x in r["runs"]]
    return dict(n_cases=len(ok),
                third_agree_et_yp=q([r["third_agree_et_yp"] for r in ok]),
                median_abs_dt_et_yp=q([r["median_abs_dt_et_yp"] for r in ok]),
                third_share_et=[q([r["third_share_et"][k] for r in ok]) for k in range(3)],
                third_share_yp=[q([r["third_share_yp"][k] for r in ok]) for k in range(3)],
                septal_arc_deg=q([r["septal_arc_deg"] for r in ok]),
                seg_changed_fixed_vs_prop=q([r["seg_changed_fixed_vs_prop"] for r in ok]),
                terr_changed_fixed_vs_prop=q([r["terr_changed_fixed_vs_prop"] for r in ok]),
                under_U_sigma0p5={k: q([x[k] if not isinstance(x[k], list) else x[k][0] for x in runs])
                                  for k in ("dice_thirds_et", "dice_thirds_yp", "sta_et", "sta_yp",
                                            "seg_dice_fixed", "seg_dice_prop", "arc_p")},
                arc_abs_change_under_U=q([abs(x["arc_p"] - r["septal_arc_deg"]) for r in ok for x in r["runs"]]))


def e7(rows):
    ok = [r for r in rows if r.get("ok")]
    out = {"n_cases": len(ok)}
    for R in (1.0, 1.08):
        truth = {}
        for r in ok:
            t = [x for x in r["rows"] if x["R"] == R and x["fwhm"] == 0.0][0]["tpr"]
            truth[r["sid"]] = t
        out[f"R{R}_truth_clean"] = q([v for t in truth.values() for v in t.values()])
        for fwhm in (0.6, 1.5):
            for b in ("true", "rand0.5", "endo_in0.5", "endo_out0.5"):
                for g in (0.0, 0.5, 1.0, 1.5):
                    err, val = [], []
                    for r in ok:
                        x = [y for y in r["rows"] if y["R"] == R and y["fwhm"] == fwhm and y["borders"] == b
                             and y["guard"] == g][0]["tpr"]
                        for s, v in x.items():
                            val.append(v)
                            if s in truth[r["sid"]]:
                                err.append(v - truth[r["sid"]][s])
                    out[f"R{R} fwhm{fwhm} {b} guard{g}"] = dict(
                        tpr=q(val), err=q(err, (50, 25, 75, 10, 90)),
                        share_below_0p99=round(float(np.mean(np.array(val) < 0.99)), 4) if val else None)
    return out


if __name__ == "__main__":
    res = {"E5": e5(load(sys.argv[1]))}
    if len(sys.argv) > 2:
        res["E6"] = e6(load(sys.argv[2]))
    if len(sys.argv) > 3:
        res["E7"] = e7(load(sys.argv[3]))
    json.dump(res, open(os.path.join(HERE, "results", "summary_r2.json"), "w"), indent=1)
    print(json.dumps(res, indent=1))
