"""Aggregate lima_geom read-outs (one JSON object per line) into the numbers the round needs. Aggregates only:
no case id, no image, no per-case value leaves this function.

    python summarise.py ROWS_JSONL [OUT_JSON]
"""
import json
import sys
from collections import Counter

import numpy as np


def q(v, ps=(10, 50, 90)):
    v = [x for x in v if x is not None and np.isfinite(x)]
    return {f"p{p}": round(float(np.percentile(v, p)), 3) for p in ps} | {"n": len(v)} if v else {"n": 0}


def summarise(rows):
    ok = [r for r in rows if r.get("frame") == "ok"]
    s = {"n_cases": len(rows), "n_frame_ok": len(ok),
         "frame_failures": dict(Counter(r.get("frame", r.get("skip", "error")) for r in rows if r not in ok))}
    if not ok:
        return s
    s["median_thickness_mm"] = q([r["median_thickness_mm"] for r in ok])
    seg_vpt = [v for r in ok for k, v in r["vox_per_third"].items() if int(k) <= 16]
    s["vox_per_third_segments"] = q(seg_vpt, (5, 10, 50, 90))
    s["share_segments_needing_halves"] = round(float(np.mean([len(r["segments_needing_halves"]) / 16 for r in ok])), 3)
    s["cases_with_any_halves"] = sum(bool(r["segments_needing_halves"]) for r in ok)
    s["empty_segments_cases"] = sum(bool(r["empty_segments"]) for r in ok)
    s["orientation_ok"] = {"fixed": sum(r["orientation_ok_fixed"] for r in ok),
                           "arc": sum(r["orientation_ok_arc"] for r in ok), "of": len(ok)}
    s["septal_arc_deg"] = q([r["septal_arc_deg"] for r in ok])
    s["myocardium_relabelled_fixed_vs_arc"] = q([r["seg_changed_fixed_vs_arc"] for r in ok])
    for k in ("thirds_agree_et_laplace", "thirds_agree_et_yp"):
        s[k] = q([r[k] for r in ok])
    for k in ("thirds_share_et", "thirds_share_yp", "thirds_share_laplace"):
        s[k] = [round(float(np.median([r[k][i] for r in ok])), 3) for i in range(3)]
    for b in ("endo", "epi"):
        v = [r["halfmax"][b]["median_mm"] for r in ok if r.get("halfmax") and r["halfmax"].get(b)]
        s[f"halfmax_offset_{b}_mm_case_medians"] = q(v)
    s["blood_hu"] = q([r["blood_hu"] for r in ok])
    s["myo_core_hu"] = q([r["myo_hu"] for r in ok])
    s["myo_core_sd_hu"] = q([r["core_hu"]["sd"] for r in ok])
    tg = [v for r in ok for v in r["tpr_guarded"].values()]
    tu = [v for r in ok for v in r["tpr_unguarded"].values()]
    s["tpr_unguarded_segments"] = q(tu, (10, 25, 50, 75, 90))
    s["tpr_guarded_segments"] = q(tg, (10, 25, 50, 75, 90))
    s["tpr_guarded_case_median"] = q([np.median(list(r["tpr_guarded"].values())) for r in ok if r["tpr_guarded"]])
    s["share_guarded_segments_in_0p99_1p25"] = round(float(np.mean([(0.99 <= v <= 1.25) for v in tg])), 3) if tg else None
    s["core_hu_q0p1"] = q([r["core_hu"]["q"]["0.1"] for r in ok])
    s["core_hu_q1"] = q([r["core_hu"]["q"]["1"] for r in ok])
    s["share_hearts_with_fat_cluster"] = {
        cut: {vol: round(float(np.mean([r["fat_clusters"][cut][vol] > 0 for r in ok])), 3) for vol in ("5", "20", "50")}
        for cut in ("0", "-30", "-50", "-100")}
    # Lima E3 calibration inputs
    rel = {k: [r["rel_thickness"][k] for r in ok if k in r["rel_thickness"]] for k in map(str, range(1, 17))}
    s["rel_thickness_by_segment_mean_sd"] = {k: [round(float(np.mean(v)), 3), round(float(np.std(v)), 3)]
                                            for k, v in rel.items() if len(v) > 2}
    s["rel_thickness_within_case_sd"] = q([float(np.std(list(r["rel_thickness"].values()))) for r in ok])
    shape = {k: np.mean(v) for k, v in rel.items() if v}
    resid = [r["rel_thickness"][k] / shape[k] for r in ok for k in r["rel_thickness"] if k in shape]
    s["rel_thickness_shape_corrected_sd"] = round(float(np.std(resid)), 3) if resid else None
    rh = [v for r in ok for v in (r.get("rel_subendo_hu") or {}).values()]
    s["rel_subendo_hu_sd"] = round(float(np.std(rh)), 3) if rh else None
    # territories
    t = [r for r in ok if "terr_euclid" in r]
    if t:
        nseg = sum(len(r["terr_euclid"]) for r in t)
        s["territory_cases"] = len(t)
        s["territory_discordance_euclid"] = round(sum(len(r["terr_discordant_euclid"]) for r in t) / nseg, 3)
        s["territory_discordance_euclid_arc_sectors"] = round(
            sum(len(r["terr_discordant_euclid_arc"]) for r in t) / nseg, 3)
        g = [r for r in t if "terr_geodesic" in r]
        if g:
            ng = sum(len(r["terr_geodesic"]) for r in g)
            s["territory_discordance_geodesic"] = round(sum(len(r["terr_discordant_geodesic"]) for r in g) / ng, 3)
            s["segments_differ_euclid_vs_geodesic"] = round(
                sum(len(r["segments_differ_euclid_geodesic"]) for r in g) / ng, 3)
            s["voxel_agree_euclid_geodesic"] = q([r["voxel_agree_euclid_geodesic"] for r in g])
        s["patients_with_any_discordant_segment_euclid"] = round(
            float(np.mean([bool(r["terr_discordant_euclid"]) for r in t])), 3)
        s["mass_share_euclid_median"] = {v: round(float(np.median([r["mass_share_euclid"][v] for r in t])), 3)
                                         for v in ("LAD", "LCx", "RCA")}
    return s


if __name__ == "__main__":
    rows = [json.loads(x) for x in open(sys.argv[1])]
    out = summarise(rows)
    if len(sys.argv) > 2:
        json.dump(out, open(sys.argv[2], "w"), indent=1)
    print(json.dumps(out, indent=1))
