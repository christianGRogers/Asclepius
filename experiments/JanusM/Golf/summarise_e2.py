"""Summarise layers_ts.json (E2) into the numbers quoted in Golf v1 and its experiment note.
Usage: python summarise_e2.py   (prints a markdown block; writes layers_ts_summary.json)"""
import json
from pathlib import Path

import numpy as np

here = Path(__file__).parent
d = json.loads((here / "layers_ts.json").read_text())
C = {k: v for k, v in d["cases"].items() if "error" not in v}
err = {k: v["error"] for k, v in d["cases"].items() if "error" in v}
q = lambda xs: (float(np.median(xs)), float(np.percentile(xs, 25)), float(np.percentile(xs, 75)))
S = {"n_cases": len(d["cases"]), "n_ok": len(C), "errors": err}
S["hu_lv_blood"] = q([c["hu_lv_blood"] for c in C.values()])
S["hu_myo"] = q([c["hu_myo"] for c in C.values()])
S["sd_myo"] = q([c["sd_myo"] for c in C.values()])
S["blood_myo_cnr"] = q([(c["hu_lv_blood"] - c["hu_myo"]) / c["sd_myo"] for c in C.values()])
# d_endo + d_epi from two voxel-centre distance transforms counts one voxel too many (a wall of n voxels gives
# (n + 1) * h), so the absolute thickness is corrected by one voxel here; differences between two masks on the
# same grid (the sensitivity rows) are unaffected.
wall = {k: c["wall_mm_median"] - float(np.mean(c["spacing_mm"])) for k, c in C.items()}
S["wall_mm"] = q(list(wall.values()))
S["wall_mm_range"] = [min(wall.values()), max(wall.values())]
S["voxels_per_third_1p5"] = q([wall[k] / 3 / float(np.mean(C[k]["spacing_mm"])) for k in C])
S["wall_mm_fine_ref"] = q([c["fine"]["wall_mm_ref"] - 0.5 for c in C.values()])
S["third_share_eq"] = np.mean([c["third_share_equal_thickness"] for c in C.values()], 0).round(3).tolist()
S["third_share_lap"] = np.mean([c["third_share_laplace_potential"] for c in C.values()], 0).round(3).tolist()
S["agree_lap_eq"] = q([c["agree_laplace_vs_thickness_thirds"] for c in C.values()])
A = {k: c for k, c in C.items() if "aha_share" in c}
S["aha_ok"] = len(A)
S["aha_fail"] = {k: c.get("fail") for k, c in C.items() if "aha_share" not in c}
S["aha_all17"] = sum(c["aha_empty_segments"] == 0 for c in A.values())
S["aha_orient_ok"] = sum(c["aha_checks"]["ok"] for c in A.values())
S["aha_orient_fail"] = [k for k, c in A.items() if not c["aha_checks"]["ok"]]
S["septal_arc"] = q([c["septal_arc_deg"] for c in A.values()])
S["aha_share_mean"] = np.mean([c["aha_share"] for c in A.values()], 0).round(3).tolist()
S["aha_cv"] = q([c["aha_cv_1_16"] for c in A.values()])
rows = {}
for c in C.values():
    for r in c["fine"]["runs"]:
        key = r.get("bias") or f"sigma {r['sigma_mm']}"
        rows.setdefault(key, []).append(r)
S["sensitivity"] = {}
for key, rs in rows.items():
    S["sensitivity"][key] = {
        "n": len(rs),
        "dice_myo": q([r["dice_myo"] for r in rs]),
        "dice_thirds": [q([r["dice_thirds"][i] for r in rs]) for i in range(3)],
        "wall_err_mm": q([r["wall_err_mm"] for r in rs]),
        "abs_wall_err_mm": q([abs(r["wall_err_mm"]) for r in rs]),
        "dice_aha_mean": q([r["dice_aha_mean"] for r in rs if "dice_aha_mean" in r]) if any("dice_aha_mean" in r for r in rs) else None,
    }
(here / "layers_ts_summary.json").write_text(json.dumps(S, indent=1))
f = lambda t: f"{t[0]:.3f} [{t[1]:.3f}, {t[2]:.3f}]"
g = lambda t: f"{t[0]:.1f} [{t[1]:.1f}, {t[2]:.1f}]"
print(f"cases {S['n_ok']}/{S['n_cases']} ok; errors {err}")
print("LV blood HU", g(S["hu_lv_blood"]), "| myo HU", g(S["hu_myo"]), "| myo SD", g(S["sd_myo"]), "| blood-myo CNR", g(S["blood_myo_cnr"]))
print("wall mm (1.5 mm grid, corrected)", g(S["wall_mm"]), "| 0.5 mm grid", g(S["wall_mm_fine_ref"]), "range", [round(x, 1) for x in S["wall_mm_range"]], "| voxels/third @1.5", g(S["voxels_per_third_1p5"]))
print("third shares eq", S["third_share_eq"], "lap", S["third_share_lap"], "agree", f(S["agree_lap_eq"]))
print("AHA ok", S["aha_ok"], "all17", S["aha_all17"], "orient ok", S["aha_orient_ok"], S["aha_orient_fail"], "fails", S["aha_fail"])
print("septal arc", g(S["septal_arc"]), "| seg share mean", S["aha_share_mean"], "| CV", f(S["aha_cv"]))
print("| condition | n | myo Dice | subendo | mid | subepi | thickness error mm | |error| | AHA Dice |")
for key, r in S["sensitivity"].items():
    print(f"| {key} | {r['n']} | {f(r['dice_myo'])} | {f(r['dice_thirds'][0])} | {f(r['dice_thirds'][1])} | "
          f"{f(r['dice_thirds'][2])} | {f(r['wall_err_mm'])} | {f(r['abs_wall_err_mm'])} | "
          f"{f(r['dice_aha_mean']) if r['dice_aha_mean'] else '-'} |")
