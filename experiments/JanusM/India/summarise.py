"""Pool the per-subject JSON of exp_layers.py into results/summary.json and print the tables for the note.

    python summarise.py OUT_DIR
"""
import json, os, sys, glob
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def q(xs, ps=(10, 50, 90)):
    xs = [x for x in xs if x is not None and np.isfinite(x)]
    return [round(float(np.percentile(xs, p)), 3) for p in ps] if xs else None


def main(out):
    rows = [json.load(open(f)) for f in sorted(glob.glob(os.path.join(out, "s*.json")))]
    ok = [r for r in rows if r.get("ok") and "E2" in r]
    why = defaultdict(int)
    for r in rows:
        if not (r.get("ok") and "E2" in r):
            why[r.get("why", "qc")] += 1
    S = dict(n_subjects=len(rows), n_used=len(ok), excluded=dict(why), subjects_used=[r["sid"] for r in ok])

    # E1
    S["E1"] = dict(
        thick_mid_mm_p10_50_90_of_subject_medians=q([r["E1"]["thick_mm_p10_50_90"][1] for r in ok]),
        thick_native_mm=q([r["E1"]["thick_native_mm_p50"] for r in ok]),
        vox_across_wall_1p5mm=q([r["E1"]["vox_across_1p5"] for r in ok]),
        vox_per_third_1p5mm=q([r["E1"]["vox_across_1p5"] / 3 for r in ok]),
        vox_per_third_0p5mm=q([r["E1"]["vox_across_0p5"] / 3 for r in ok]),
        frac_midwall_thinner_4p5mm=q([r["E1"]["frac_mid_thinner_than_4p5mm"] for r in ok]),
        thick_by_seg_mm={s: q([r["E1"]["thick_by_seg_mm"].get(str(s)) for r in ok]) for s in range(1, 18)},
    )
    # E2
    S["E2"] = dict(agree_dist_laplace=q([r["E2"]["agree_dist_laplace"] for r in ok]),
                   median_abs_t_diff=q([r["E2"]["median_abs_t_diff"] for r in ok]))
    pert = defaultdict(lambda: defaultdict(list))
    for r in ok:
        for p in r["E2"]["perturb"]:
            key = p["kind"] if p["kind"] != "rand" else f"rand_sigma{p['sigma']}"
            pert[key]["dice_myo"].append(p["dice_myo"])
            for k in ("1", "2", "3"):
                pert[key][f"dice_layer{k}"].append(p["dice_layer"][k])
            pert[key]["scar_bin_agree"].append(p["scar_bin_agree"])
            pert[key]["scar_abs_err_pct"].append(p["scar_abs_err_pct"])
            pert[key]["scar_abs_err_pct_p90"].append(p.get("scar_abs_err_pct_p90"))
    S["E2"]["perturb"] = {k: {m: q(v) for m, v in d.items()} for k, d in pert.items()}
    # E3
    S["E3"] = dict(septal_arc_deg=q([r["E3"]["septal_arc_deg"] for r in ok], (5, 10, 50, 90, 95)),
                   frame_change_seg={k: q([r["E3"]["frame_change_seg_terr"][k][0] for r in ok])
                                     for k in ("tilt5", "tilt10", "ref10", "ref20", "base5")},
                   frame_change_territory={k: q([r["E3"]["frame_change_seg_terr"][k][1] for r in ok])
                                           for k in ("tilt5", "tilt10", "ref10", "ref20", "base5")},
                   seg_ml={s: q([r["E3"]["seg_ml"].get(str(s)) for r in ok]) for s in range(1, 18)})
    # E4
    S["E4"] = dict(hu_lv=q([r["qc"]["hu_lv"] for r in ok]), hu_myo=q([r["qc"]["hu_myo"] for r in ok]),
                   median_hu_layer={k: q([r["E4"]["median_layer"][k] for r in ok]) for k in ("1", "2", "3")},
                   tpr_median=q([r["E4"]["tpr_median"] for r in ok]),
                   tpr_mean=q([r["E4"]["tpr"] for r in ok]),
                   blood_like_subendo=q([r["E4"]["blood_like_subendo"] for r in ok]),
                   frac_tpr_median_below_0p99=float(np.mean([r["E4"]["tpr_median"] < 0.99 for r in ok])) if ok else None)
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    json.dump(S, open(os.path.join(HERE, "results", "summary.json"), "w"), indent=1)
    print(json.dumps(S, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
