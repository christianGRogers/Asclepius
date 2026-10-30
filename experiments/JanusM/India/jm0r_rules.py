"""India v3: the pre-registered decision procedure for Job JM-0 / JM-0R outputs (ruling R2 §7 item 1).

Fixed before any output exists. When the lead posts JM-0R's aggregate JSON (JA23; or the three fallback scripts'
JSONs, merged by `--fallback`), this script applies every rule the rulings pre-register and prints the decisions,
with the number each one used. Nothing here is tuned after the numbers arrive; a rule whose input is missing returns
"undecided (input missing)" and the plan stays as ruled.

Input keys (the JM-0R output contract, proposed for #169; aggregates over the 40 JM-0 cases, no case id):

    n_ok                                  int, cases with a usable frame
    thickness_median_mm                   median over cases of the median segment thickness (equal thickness, JA2)
    halves_segment_share                  share of segments 1-16 that JA2 gives halves
    aha_frame_fail_share                  share of cases with no frame or a failed orientation check (JA3)
    endo_halfmax_offset_mm_median         seed's endocardial half-maximum offset (+ = label outward), median
    epi_halfmax_offset_mm_median          seed's free-wall epicardial offset, median
    endo_edge_10_90_mm_median             endocardial 10-90 % edge width, median
    tpr_guard_adaptive_freewall_median    guarded (JA17 band) free-wall rest TPR, median over segments
    tpr_guard_adaptive_share_below_0p99   reported only
    fat_grid                              {"c,V": share of hearts with >= 1 core cluster}, c in {0,-30,-50,-100} HU,
                                          V in {5,20,50} mm3; plus "patient_noise,3vox" for Hotel's candidate
    septal_arc_mass_changed_median        share of myocardium changing segment, fixed vs arc-proportional
    geodesic_segments_changed_share       share of (case, segment) whose majority territory differs
    et_laplace_third_agreement_median     reported only
    cv_n, segment_shape                   rule C's inputs (Lima E3; JA18): robust SD of log relative thickness,
                                          and the 16 median relative segment thicknesses

    python jm0r_rules.py JM0R.json [--fallback LIMA.json INDIA.json HOTEL.json] [--sig-m 0.24] [--out OUT.json]
"""
from __future__ import annotations

import argparse
import json
import sys

UNDECIDED = "undecided (input missing)"


def _get(x, k):
    v = x.get(k)
    return None if v is None else v


def rules(x, sig_m=None):
    d = {}

    # R1, halves (JA2): applied per segment by the geometry module; reported.
    h = _get(x, "halves_segment_share")
    d["R1_halves"] = UNDECIDED if h is None else dict(
        value=h, decision="halves per segment as JA2 computes them"
        + ("; > 25 % of segments in halves: Table A states the layer count per segment in its header" if h > 0.25
           else ""))

    # R2, thickness-definition check (Hotel v2 §4.4, JA19 header): median within 1.5 mm of 5.7-6.5 mm.
    t = _get(x, "thickness_median_mm")
    if t is None:
        d["R2_thickness_definition"] = UNDECIDED
    else:
        ok = 5.7 - 1.5 <= t <= 6.5 + 1.5
        d["R2_thickness_definition"] = dict(value=t, window=[4.2, 8.0], passed=ok, decision=(
            "definitions agree; F3 holds" if ok else
            "thinning flags do not ship until readers hand-measure thickness on the first 20 decision cases and "
            "the module's definition is aligned (Hotel v2 §4.4)"))

    # R3, seed half-maximum offsets: JA17 condition 2 (snap tool) and the bias guard expectation (JA16).
    eo, po = _get(x, "endo_halfmax_offset_mm_median"), _get(x, "epi_halfmax_offset_mm_median")
    if eo is None or po is None:
        d["R3_seed_offsets"] = UNDECIDED
    else:
        d["R3_seed_offsets"] = dict(endo=eo, epi=po,
                                    snap_tool_needed_for_tpr=abs(eo) > 0.25,
                                    seed_expected_to_fail_bias_guard_0p3=max(abs(eo), abs(po)) > 0.3,
                                    seed_expected_to_fail_bias_guard_0p5=max(abs(eo), abs(po)) > 0.5,
                                    decision=("request the ~100 training reads at the first decision-set look"
                                              if max(abs(eo), abs(po)) > 0.5 else "no change"))

    # R4, rest TPR gate (JA17).
    e, tp = _get(x, "endo_edge_10_90_mm_median"), _get(x, "tpr_guard_adaptive_freewall_median")
    if e is None or tp is None or eo is None:
        d["R4_rest_tpr"] = UNDECIDED
    else:
        c1, c2, c3 = e <= 1.5, abs(eo) <= 0.25, 0.99 <= tp <= 1.15
        if e > 2.0:
            dec = "not computed (edge > 2 mm)"
        elif c1 and c3 and c2:
            dec = "shown per segment as a patient-relative z-score (JA17, JA18)"
        elif c1 and c3 and not c2:
            dec = "shown only after the half-maximum snap tool ships (JA17 condition 2); research export until then"
        else:
            dec = "research export only; not in the table"
        d["R4_rest_tpr"] = dict(edge=e, endo_offset=eo, tpr_median=tp, conditions=[c1, c2, c3], decision=dec,
                                share_below_0p99_reported=_get(x, "tpr_guard_adaptive_share_below_0p99"))

    # R5, provisional fat cut (JA18): the least strict (c, V) with <= 5 % of hearts carrying a cluster.
    fg = _get(x, "fat_grid")
    if not fg:
        d["R5_fat_cut"] = UNDECIDED
    else:
        order = [f"{c},{v}" for c in (0, -30, -50, -100) for v in (5, 20, 50)]   # least strict first
        order += ["patient_noise,3vox"]
        pick = next((k for k in order if k in fg and fg[k] <= 0.05), None)
        d["R5_fat_cut"] = dict(grid=fg, provisional=pick or "none passes: no fat output (research export only)",
                               note="provisional on JM-0's 40 (a CAD-referral population); fixed once on the "
                                    "reference population before any seal read (JA18)")

    # R6, septal-arc sensitivity column (JA20).
    a = _get(x, "septal_arc_mass_changed_median")
    d["R6_septal_arc_column"] = UNDECIDED if a is None else dict(
        value=a, decision="kept" if a >= 0.10 else "dropped (< 10 % of mass changes segment)")

    # R7, geodesic territories (JA20): >= 10 % of segments change majority -> second territory column + lead.
    gs = _get(x, "geodesic_segments_changed_share")
    d["R7_geodesic"] = UNDECIDED if gs is None else dict(
        value=gs, decision=("Table B shows the geodesic territory mass beside the Euclidean one; Euclidean stays "
                            "primary until the lead rules (LQ13)") if gs >= 0.10 else
        "geodesic dropped from the table; Euclidean only (JA4, JA20)")

    # R8, AHA failures (JA3).
    f = _get(x, "aha_frame_fail_share")
    d["R8_aha_failures"] = UNDECIDED if f is None else dict(
        value=f, decision=("failing cases carry 'AHA frame failed' and no segment table; > 10 %: a role:swe fix "
                           "of the frame before any read") if f > 0.10 else
        "failing cases carry 'AHA frame failed' and no segment table")

    # R9, detectable depth printed on the page (JA18; E10 with JM-0R's cv_n and shape).
    cv, shp = _get(x, "cv_n"), _get(x, "segment_shape")
    if cv is None or shp is None or sig_m is None:
        d["R9_detectable_depth"] = UNDECIDED + " (needs cv_n, segment_shape and sig_m)"
    else:
        from e10_detectable_depth import detectable_depth
        r = detectable_depth(shp, cv, sig_m)
        d["R9_detectable_depth"] = dict(cv_n=cv, sig_m=sig_m, depth_80=r["depth_80"], decision=(
            f"page prints: 'finds about 80 % of territories thinned by >= {int(100 * r['depth_80'])} % "
            "in simulation; not a sensitivity'") if r["depth_80"] else
            "page prints: 'thinning detection not demonstrated at this measurement error'")

    # R10, reported only.
    d["R10_et_vs_laplace"] = dict(value=_get(x, "et_laplace_third_agreement_median"), decision="reported only")
    return d


def merge_fallback(lima, india, hotel):
    """Map the three committed add-ons' printed aggregates onto the JM-0R keys (JA23 fallback: one job, in the order
    Lima, India, Hotel). Sign convention here: + = the label border lies outward of the image edge (endocardium:
    into the wall; epicardium: into the fat), as Lima and India print it; Hotel's endocardial offset is + into the
    blood, so it is negated. Where two scripts give one quantity, the later one in JA23's order fills only what is
    missing, except the half-maximum offsets and edges, which Hotel measures on the free wall and are taken from it.
    The fallback TPR is Hotel's fixed 1 mm guard, not JA17's adaptive band; R4 then reads it with that caveat."""
    lima, india, hotel = lima or {}, india or {}, hotel or {}
    hotel = hotel.get("aggregate", hotel)
    med = lambda v: (v.get("p50") if isinstance(v, dict) else v[1] if isinstance(v, list) and len(v) > 2 else v)
    x = {}
    # Lima
    x["thickness_median_mm"] = med(lima.get("median_thickness_mm"))
    x["halves_segment_share"] = lima.get("share_segments_needing_halves")
    if lima.get("n_cases"):
        ori = lima.get("orientation_ok", {})
        ok = min(lima.get("n_frame_ok", 0), ori.get("fixed", lima.get("n_frame_ok", 0)))
        x["aha_frame_fail_share"] = round(1 - ok / lima["n_cases"], 3)
    x["septal_arc_mass_changed_median"] = med(lima.get("myocardium_relabelled_fixed_vs_arc"))
    x["geodesic_segments_changed_share"] = lima.get("segments_differ_euclid_vs_geodesic")
    x["et_laplace_third_agreement_median"] = med(lima.get("thirds_agree_et_laplace"))
    fat = lima.get("share_hearts_with_fat_cluster")
    if fat:
        x["fat_grid"] = {f"{c},{v}": share for c, d in fat.items() for v, share in d.items()}
    x["cv_n"] = lima.get("rel_thickness_shape_corrected_sd")
    rel = lima.get("rel_thickness_by_segment_mean_sd")
    if rel and all(str(k) in rel for k in range(1, 17)):
        x["segment_shape"] = [rel[str(k)][0] for k in range(1, 17)]
    for k, ik in (("endo_halfmax_offset_mm_median", "halfmax_offset_endo_mm_case_medians"),
                  ("epi_halfmax_offset_mm_median", "halfmax_offset_epi_mm_case_medians")):
        x[k] = med(lima.get(ik))
    # India (fills what is missing)
    for k, ik in (("endo_halfmax_offset_mm_median", "A_endo_offset_mm_median_p10_p90"),
                  ("epi_halfmax_offset_mm_median", "A_epi_offset_mm_median_p10_p90")):
        if x.get(k) is None and india.get(ik):
            x[k] = india[ik][0]
    if x.get("septal_arc_mass_changed_median") is None:
        x["septal_arc_mass_changed_median"] = india.get("C_seg_changed_prop_median")
    if x.get("et_laplace_third_agreement_median") is None:
        x["et_laplace_third_agreement_median"] = india.get("B_third_agree_et_laplace_median")
    # Hotel (free-wall half-maximum offsets and edges; 1 mm guarded TPR)
    if hotel.get("endo_halfmax_offset_mm_q25_50_75_n"):
        x["endo_halfmax_offset_mm_median"] = -hotel["endo_halfmax_offset_mm_q25_50_75_n"][1]
    if hotel.get("epi_halfmax_offset_mm_q25_50_75_n"):
        x["epi_halfmax_offset_mm_median"] = hotel["epi_halfmax_offset_mm_q25_50_75_n"][1]
    if hotel.get("endo_10_90_mm_q"):
        x["endo_edge_10_90_mm_median"] = hotel["endo_10_90_mm_q"][1]
    tg = hotel.get("tpr_guard1.0") or {}
    if tg.get("patient_median_free_q"):
        x["tpr_guard_adaptive_freewall_median"] = tg["patient_median_free_q"][1]
        x["tpr_guard_adaptive_share_below_0p99"] = tg.get("share_free_segments_lt_0p99")
        x["tpr_note"] = "fallback: Hotel's fixed 1 mm guard, not JA17's adaptive band"
    return {k: v for k, v in x.items() if v is not None}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("jm0r", nargs="?")
    ap.add_argument("--fallback", nargs=3, metavar=("LIMA", "INDIA", "HOTEL"))
    ap.add_argument("--sig-m", type=float, default=None,
                    help="segment-thickness measurement SD (mm) of the model at JA8's edge; E10 gives it")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    if a.fallback:
        lo = [json.load(open(p)) if p != "-" else {} for p in a.fallback]
        x = merge_fallback(*lo)
    else:
        x = json.load(open(a.jm0r))
    d = rules(x, a.sig_m)
    s = json.dumps(d, indent=1)
    if a.out:
        open(a.out, "w").write(s)
    print(s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
