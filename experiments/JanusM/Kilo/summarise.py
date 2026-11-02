"""Summarise exp_layers.py output into the tables of the Kilo E1-E3 note.

Usage: python summarise.py RESULT.json [OUT.json]
Medians across cases; per-case values are the mean of the random repetitions.
"""
import json, sys
import numpy as np


def q(x):
    x = np.asarray([v for v in x if v is not None and not np.isnan(v)], float)
    return f"{np.median(x):.3f} [{np.percentile(x, 25):.3f}, {np.percentile(x, 75):.3f}]" if len(x) else "-"


def main(path, out=None):
    R = [r for r in json.load(open(path)) if "skip" not in r]
    S = {"n_cases": len(R), "n_contrast": sum(r["contrast"] for r in R)}
    print(f"cases {len(R)}, contrast {S['n_contrast']}")
    # E1
    for k, f in [("myo_ml", lambda r: r["myo_ml"]), ("wall_p50_mm", lambda r: r["thick_mm_p10_50_90"][1]),
                 ("wall_p10_mm", lambda r: r["thick_mm_p10_50_90"][0]), ("wall_p90_mm", lambda r: r["thick_mm_p10_50_90"][2]),
                 ("vox_across_native", lambda r: r["vox_across_wall_native_median"]),
                 ("vox_across_grid", lambda r: r["vox_across_wall_grid_median"]),
                 ("laplace_vs_distance_same_third", lambda r: r["laplace_vs_distance_same_third"])]:
        S[k] = q([f(r) for r in R]); print("E1", k, S[k])
    segs = {s: q([r["seg_thick_mm"].get(str(s)) for r in R if str(s) in r["seg_thick_mm"]]) for s in range(1, 18)}
    S["seg_thick_mm"] = segs
    # E2
    conds = []
    for r in R:
        for x in r["E2"]:
            if (x["kind"], x["sigma_mm"]) not in conds: conds.append((x["kind"], x["sigma_mm"]))
    S["E2"] = {}
    taus = ["0.15", "0.4", "0.65", "0.9"]
    for c in conds:
        per = []
        for r in R:
            xs = [x for x in r["E2"] if (x["kind"], x["sigma_mm"]) == c]
            per.append({
                "dice_myo": np.mean([x["dice_myo"] for x in xs]),
                "dice_t1": np.mean([x["dice_third"][0] for x in xs]),
                "dice_t2": np.mean([x["dice_third"][1] for x in xs]),
                "dice_t3": np.mean([x["dice_third"][2] for x in xs]),
                "frac_third_changed": np.mean([x["frac_third_changed"] for x in xs]),
                "dice_seg_mean": np.mean([x["dice_seg_mean"] for x in xs]),
                "seg_thick_abs_err_mm": np.mean([x["seg_thick_abs_err_mm"] for x in xs]),
                **{f"bias_pp_{t}": np.mean([x["transm_err_pp_mean"][t] for x in xs]) for t in taus},
                **{f"mae_pp_{t}": np.mean([x["transm_err_pp_mae"][t] for x in xs]) for t in taus},
                **{f"kim_flip_{t}": np.mean([x["kim_bin_changed"][t] for x in xs]) for t in taus},
                "kim_flip_all": np.mean([np.mean([x["kim_bin_changed"][t] for t in taus]) for x in xs]),
            })
        S["E2"][f"{c[0]}_{c[1]}"] = {k: q([p[k] for p in per]) for k in per[0]}
        print("E2", c, {k: v for k, v in S["E2"][f'{c[0]}_{c[1]}'].items()})
    # E3
    C = [r for r in R if r["contrast"]]
    tp = [v for r in C for v in r["E3_tpr"].values()]
    tg = [v for r in C for v in r["E3_tpr_guard"].values()]
    within_sd = [np.std(list(r["E3_tpr"].values())) for r in C if len(r["E3_tpr"]) > 8]
    shift = []
    for r in C:
        for rep in r["E3_tpr_sigma1"]:
            for s, v in rep.items():
                if s in r["E3_tpr"]: shift.append(abs(v - r["E3_tpr"][s]))
    S["E3"] = {"n_cases": len(C), "tpr_all_segments": q(tp), "tpr_guard": q(tg),
               "tpr_within_patient_sd": q(within_sd), "abs_shift_sigma1": q(shift),
               "frac_segments_tpr_below_0.99": float(np.mean(np.array(tp) < 0.99)) if tp else None,
               "frac_segments_shift_gt_0.05": float(np.mean(np.array(shift) > 0.05)) if shift else None}
    print("E3", S["E3"])
    if out: json.dump(S, open(out, "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:])
