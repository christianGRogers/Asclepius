"""Round 2 ruling §7 item 1, as code: the pre-registered decisions on Job JM-0 / JM-0R aggregates.

Runs **when the lead posts JM-0R's summary.json** (or the JA23 fallback's). Every rule below was fixed by the
Round 1 and Round 2 rulings before any output exists; this script only applies them and prints each decision with
the number it rests on. A quantity the input does not carry prints "NOT DECIDABLE", never a default.

    python apply_r2_rules.py SUMMARY_JSON [--format jm0r|lima_jm0b] [--detectable E5_JSON]

The quantities it needs are the **JM-0R output schema** that #169 must emit (`QUANTITIES`, named keys, aggregates
only). `--format lima_jm0b` maps Lima's Round 2 `jm0b_readout.py` summary (the JA23 fallback) onto them; it lacks
the edge width and free-wall TPR, so those rules print NOT DECIDABLE until Hotel's fallback script supplies them.
"""
import argparse
import json
import sys

# name: (meaning, unit)
QUANTITIES = {
    "n_cases": ("cases read out", "count"),
    "frame_fail_share": ("share of cases whose AHA frame failed (JA3)", "fraction"),
    "orientation_fail_share": ("share of frame-ok cases failing the orientation checks (JA3)", "fraction"),
    "thickness_median_mm": ("median over cases of the median segment thickness, equal-thickness (JA2)", "mm"),
    "halves_segment_share": ("share of segments 1-16 needing halves (< 4 voxels per third or < 5 mm; JA2)", "fraction"),
    "halfmax_endo_mm": ("median over cases of the median endocardial half-maximum offset, + = mask outward", "mm"),
    "halfmax_epi_mm": ("median over cases of the median epicardial half-maximum offset, + = mask outward", "mm"),
    "edge_endo_10_90_mm": ("median over cases of the endocardial 10-90 % edge width", "mm"),
    "tpr_freewall_guarded_median": ("median guarded (JA17 adaptive band) TPR over free-wall segments "
                                    "(1, 4-7, 10-13, 15-16)", "ratio"),
    "tpr_share_below_0p99": ("share of guarded segments below 0.99 (reported only, JA17)", "fraction"),
    "fat_share_hearts": ("share of hearts with a core cluster, per cut c (HU) and min volume V (mm3)", "{c: {V: fraction}}"),
    "arc_mass_changed_share": ("median share of myocardial mass changing segment, fixed vs arc septal sectors", "fraction"),
    "geodesic_segment_change_share": ("share of segments whose majority artery differs, Euclidean vs geodesic", "fraction"),
    "cv_n": ("shape-corrected SD of segment thickness / patient median (Lima E3/E5)", "fraction"),
    "segment_shape": ("mean segment thickness / patient median, segments 1-16", "list of 16"),
}

FAT_C = ["0", "-30", "-50", "-100"]   # least strict first (JA18)
FAT_V = ["5", "20", "50"]


def from_lima_jm0b(s):
    """Map Lima R2's summarise.summarise() output onto QUANTITIES (the JA23 fallback)."""
    n = s.get("n_cases")
    ok = s.get("n_frame_ok")
    q = {"n_cases": n}
    if n:
        q["frame_fail_share"] = (n - ok) / n
    if ok and "orientation_ok" in s:
        q["orientation_fail_share"] = 1 - s["orientation_ok"]["fixed"] / ok
    if "median_thickness_mm" in s:
        q["thickness_median_mm"] = s["median_thickness_mm"]["p50"]
    if "share_segments_needing_halves" in s:
        q["halves_segment_share"] = s["share_segments_needing_halves"]
    for b in ("endo", "epi"):
        k = f"halfmax_offset_{b}_mm_case_medians"
        if s.get(k, {}).get("n"):
            q[f"halfmax_{b}_mm"] = s[k]["p50"]
    if "share_hearts_with_fat_cluster" in s:
        q["fat_share_hearts"] = s["share_hearts_with_fat_cluster"]
    if "myocardium_relabelled_fixed_vs_arc" in s:
        q["arc_mass_changed_share"] = s["myocardium_relabelled_fixed_vs_arc"]["p50"]
    if "segments_differ_euclid_vs_geodesic" in s:
        q["geodesic_segment_change_share"] = s["segments_differ_euclid_vs_geodesic"]
    if "rel_thickness_shape_corrected_sd" in s:
        q["cv_n"] = s["rel_thickness_shape_corrected_sd"]
    if "rel_thickness_by_segment_mean_sd" in s:
        q["segment_shape"] = [s["rel_thickness_by_segment_mean_sd"][str(k)][0] for k in range(1, 17)]
    return q


def decide(q):
    D = []

    def need(*names):
        miss = [n for n in names if q.get(n) is None]
        return ("NOT DECIDABLE: missing " + ", ".join(miss)) if miss else None

    def add(rule, decision, basis):
        D.append({"rule": rule, "decision": decision, "basis": basis})

    # AHA failures (JA3; Juliet v1 / Lima v1 threshold 10 %)
    m = need("frame_fail_share", "orientation_fail_share")
    if m:
        add("AHA frame (JA3)", m, "")
    else:
        bad = q["frame_fail_share"] > 0.10 or q["orientation_fail_share"] > 0.10
        add("AHA frame (JA3)", "FIX THE FRAME before any table ships" if bad else "frame accepted",
            f"frame fail {q['frame_fail_share']:.3f}, orientation fail {q['orientation_fail_share']:.3f} (limit 0.10)")
    # halves (JA2): applied per segment by the module; the share is reported
    m = need("halves_segment_share")
    add("Halves (JA2)", m or "applied per segment by the geometry module; no plan change",
        "" if m else f"{q['halves_segment_share']:.3f} of segments use halves")
    # thickness-definition check (Hotel v2 §4.4, JA18 F3)
    m = need("thickness_median_mm")
    if m:
        add("Thickness definition (Hotel §4.4)", m, "")
    else:
        t = q["thickness_median_mm"]
        ok = 5.7 - 1.5 <= t <= 6.5 + 1.5
        add("Thickness definition (Hotel §4.4)",
            "definitions agree; F3 holds" if ok else
            "MISMATCH: readers hand-measure thickness on the first 20 decision cases (3 mid-ventricular segments, "
            "short-axis normal) and the module's definition is aligned before the reference population is fitted",
            f"median {t:.2f} mm against 4.2-8.0 mm (5.7-6.5 mm +- 1.5)")
    # seed half-maximum offsets: snap tool (JA17 condition 2; JA21's read-check tolerance 0.5 mm)
    m = need("halfmax_endo_mm", "halfmax_epi_mm")
    if m:
        add("Seed half-maximum offsets / snap tool", m, "")
    else:
        e, p = q["halfmax_endo_mm"], q["halfmax_epi_mm"]
        snap_reads = abs(e) > 0.5 or abs(p) > 0.5
        snap_tpr = abs(e) > 0.25
        add("Seed half-maximum offsets / snap tool",
            ("BUILD THE SNAP TOOL (role:swe) before reads: seeds would fail the 0.5 mm read check"
             if snap_reads else "no snap needed for reads")
            + ("; rest TPR needs snapped endocardium (JA17 cond. 2)" if snap_tpr else ""),
            f"endo {e:+.2f} mm, epi {p:+.2f} mm (read check 0.5; TPR endo 0.25)")
    # rest TPR gate (JA17)
    m = need("edge_endo_10_90_mm", "halfmax_endo_mm", "tpr_freewall_guarded_median")
    if m:
        add("Rest TPR gate (JA17)", m, "")
    else:
        edge, e, t = q["edge_endo_10_90_mm"], q["halfmax_endo_mm"], q["tpr_freewall_guarded_median"]
        if edge > 2.0:
            dec = "NOT COMPUTED (edge > 2 mm)"
        elif edge <= 1.5 and abs(e) <= 0.25 and 0.99 <= t <= 1.15:
            dec = "SHOWN in the table as a patient-relative z (JA18), never against 0.99"
        else:
            dec = "research export only; not in the table"
        add("Rest TPR gate (JA17)", dec,
            f"edge {edge:.2f} mm (<= 1.5), endo offset {e:+.2f} (|.| <= 0.25 or snapped), "
            f"free-wall TPR {t:.3f} (0.99-1.15); share < 0.99 = {q.get('tpr_share_below_0p99')} (reported)")
    # provisional fat cut (JA18)
    m = need("fat_share_hearts")
    if m:
        add("Provisional fat cut (JA18)", m, "")
    else:
        f = q["fat_share_hearts"]
        pick = next(((c, v) for c in FAT_C for v in FAT_V if f.get(c, {}).get(v, 1.0) <= 0.05), None)
        add("Provisional fat cut (JA18)",
            f"c = {pick[0]} HU, V = {pick[1]} mm3 (provisional; refitted once on the reference population)"
            if pick else "NO CANDIDATE: fat is a number only, never a flag, until the reference population",
            "least strict (c, V) with <= 5 % of hearts carrying a cluster; grid " + json.dumps(f))
    # septal-arc column (JA20)
    m = need("arc_mass_changed_share")
    add("Septal-arc column (JA20)", m or ("kept" if q["arc_mass_changed_share"] >= 0.10 else "dropped"),
        "" if m else f"{q['arc_mass_changed_share']:.3f} of mass changes segment (drop if < 0.10)")
    # geodesic territories (JA20)
    m = need("geodesic_segment_change_share")
    add("Geodesic vs Euclidean territories (JA20)",
        m or ("ROUND 4 RULES on geodesic (>= 10 % of segments change)" if q["geodesic_segment_change_share"] >= 0.10
              else "Euclidean stays primary; geodesic not built"),
        "" if m else f"{q['geodesic_segment_change_share']:.3f} of segments change majority")
    # E5 detectable depth (JA18, ruling §7 item 3)
    m = need("cv_n", "segment_shape")
    add("Detectable depth on the page (JA18; Lima E5)",
        m or "re-run e5_ja18.detectable_depth with these cv_n and shape and the decision set's measured "
             "segment-thickness error; print its page line",
        "" if m else f"cv_n {q['cv_n']:.3f}")
    return D


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("summary"); ap.add_argument("--format", choices=("jm0r", "lima_jm0b"), default="jm0r")
    a = ap.parse_args()
    s = json.load(open(a.summary))
    q = s if a.format == "jm0r" else from_lima_jm0b(s)
    unknown = sorted(set(q) - set(QUANTITIES))
    if unknown:
        sys.exit(f"unknown quantities {unknown}: the input is not a JM-0R summary")
    for d in decide(q):
        print(f"- {d['rule']}: {d['decision']}" + (f"  [{d['basis']}]" if d['basis'] else ""))


if __name__ == "__main__":
    main()
