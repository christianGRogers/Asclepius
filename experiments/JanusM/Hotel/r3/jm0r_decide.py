"""Hotel R3: the pre-registered decision procedure for Job JM-0 / JM-0R outputs (Round 2 ruling §7 item 1).

It runs when the lead posts the outputs on #142, and not before. It reads **aggregate JSON only** (no case id, no
image), so it needs no guard call; every number it reads was produced by a guarded Fir job.

Inputs, any of (JA23: JM-0R, or its fallback of the three committed add-ons plus Job JM-0's own summary):
  --jm0r     JM-0R's aggregate JSON (its schema: Hotel v3 §6.3, which reuses the keys below)
  --juliet   Job JM-0's printed summary (experiments/JanusM/Juliet/fir/geometry_m0.py)
  --lima     Lima's jm0b summary.json (experiments/JanusM/Lima/fir/jm0b_readout.py, via summarise.py)
  --india    India's jm0_addon summary (experiments/JanusM/India/fir/jm0_addon.py)
  --hotel    Hotel's add-on aggregate (experiments/JanusM/Hotel/r2/fir/halfmax_tpr_m0.py)
When JM-0R is given, it wins for every quantity it carries. Otherwise each quantity is taken from the first source
in a fixed order (listed per rule below); a quantity no source carries is "not evaluable", and its rule takes the
conservative branch stated in advance.

**Sign convention for half-maximum offsets (canonical):** + = the labelled region (the LV pool for the
endocardium; pool plus myocardium for the epicardium) reaches beyond the image half-maximum. Lima and India report
it this way. Hotel R2's add-on reports the endocardium the other way round (+ = the label's endocardium sits in
the blood), so its endocardial value is negated here.

Every rule, its threshold and its branch are fixed in this file before any output exists (Hotel v3 §5).

    python experiments/JanusM/Hotel/r3/jm0r_decide.py [--jm0r F] [--juliet F] [--lima F] [--india F] [--hotel F] \
        [--out decisions.json]
"""
import argparse
import json
import sys
from pathlib import Path

# ---- pre-registered thresholds (Round 2 ruling JA2, JA17, JA18, JA20; Hotel v2 §4.4, §9) -----------------------
MIN_USABLE = 36                 # of 40 JM-0 cases; fewer: stop and look before applying any rule
HALVES_WARN = 0.25              # share of segments needing halves above which Table A defaults to halves
THICK_REF = (5.7, 6.5)          # CT end-diastole / mid-diastole means (Chen 2025)
THICK_TOL = 1.5                 # mm (Hotel v2 §4.4)
OFFSET_GATE = 0.25              # mm, JA17 condition 2
OFFSET_SNAP_READS = 0.5         # mm, Hotel v2 §9: snap seeds before reads
EDGE_GATE = 1.5                 # mm 10-90 %, JA17 condition 1
EDGE_DROP = 2.0                 # mm, JA17: not computed above this
FWHM_PER_1090 = 1 / 1.09        # Gaussian edge: FWHM = 10-90 % width / 1.09 (JA17)
TPR_WINDOW = (0.99, 1.15)       # JA17 condition 3, median guarded free-wall TPR
FAT_C = (0, -30, -50, -100)     # HU, least strict first (JA18)
FAT_V = (5, 20, 50)             # mm^3, least strict first
FAT_NULL = 0.05                 # share of hearts with a cluster
ARC_DROP = 0.10                 # JA20: septal-arc column dropped below this median share of mass changing segment
GEO_RULE = 0.10                 # JA20: geodesic vs Euclidean majority change, share of segments
AHA_FAIL = 0.10                 # share of cases failing the AHA frame


def load(p):
    return json.loads(Path(p).read_text()) if p else None


def get(d, *path):
    for k in path:
        if d is None:
            return None
        d = d.get(k) if isinstance(d, dict) else (d[k] if isinstance(d, list) and isinstance(k, int)
                                                  and k < len(d) else None)
    return d


def p50(v):
    """Median from the shapes the scripts use: dict with p50/median, [median, p10, p90], [q25, q50, q75, n]."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, dict):
        for k in ("p50", "median"):
            if k in v:
                return float(v[k])
        return None
    return None


def first(*cands):
    for src, val in cands:
        if val is not None:
            return src, val
    return None, None


def decide(S):
    out = []

    def rule(rid, question, src, value, outcome, basis):
        out.append({"rule": rid, "question": question, "source": src, "value": value, "outcome": outcome,
                    "basis": basis})

    J, L, I, H, R = S.get("juliet"), S.get("lima"), S.get("india"), S.get("hotel"), S.get("jm0r")
    # --- 0. enough cases
    src, n = first(("jm0r", get(R, "n_usable")), ("juliet", get(J, "summary", "n_usable") or get(J, "n_usable")),
                   ("lima", get(L, "n_frame_ok")), ("india", get(I, "n_ok")), ("hotel", get(H, "n_usable")))
    rule("R0", "Are >= 36 of the 40 JM-0 cases usable?", src, n,
         "proceed" if n is not None and n >= MIN_USABLE else "STOP: post the failure reasons; no rule is applied",
         "Hotel v3 §5.1")
    # --- 1. AHA failures
    src, nf = first(("jm0r", get(R, "aha_failures")), ("lima", len(get(L, "frame_failures") or {}) if L else None))
    rate = None if nf is None or not n else nf / max(n, 1)
    rule("R1", "AHA frame failures (JA3)", src, rate,
         "not evaluable: carried to JM-0R" if rate is None else
         ("ok: failing cases flagged and left out of F2" if rate <= AHA_FAIL else
          "geometry module fix (role:swe) before the reference population is computed"), "JA3; Hotel v3 §5.1")
    # --- 2. halves
    src, h = first(("jm0r", get(R, "share_segments_needing_halves")), ("lima", get(L, "share_segments_needing_halves")))
    rule("R2", "Share of segments needing halves (JA2)", src, h,
         "not evaluable: JA2 still applies per segment" if h is None else
         ("JA2 per segment; Table A unchanged" if h <= HALVES_WARN else
          "Table A shows halves for every segment (thirds only in the research export)"), "JA2; Hotel v3 §5.1")
    # --- 3. thickness definition
    src, t = first(("jm0r", p50(get(R, "median_thickness_mm"))), ("juliet", get(J, "summary", "median_thick_mm")),
                   ("lima", p50(get(L, "median_thickness_mm"))))
    lo, hi = THICK_REF[0] - THICK_TOL, THICK_REF[1] + THICK_TOL
    rule("R3", f"Median wall thickness within {THICK_TOL} mm of 5.7-6.5 mm? (Hotel v2 §4.4)", src, t,
         "not evaluable" if t is None else
         ("definitions agree; F3 anchor holds" if lo <= t <= hi else
          "readers measure thickness by hand on the first 20 decision cases; Janus-M's definition is aligned "
          "before the reference population (F2) is computed; no thinning flag ships until then"),
         "Hotel v2 §4.4; JA18")
    # --- 4. half-maximum offsets (canonical sign)
    h_endo = get(H, "endo_halfmax_offset_mm_q25_50_75_n")
    h_epi = get(H, "epi_halfmax_offset_mm_q25_50_75_n")
    src_e, endo = first(("jm0r", get(R, "endo_offset_mm_median")),
                        ("lima", p50(get(L, "halfmax_offset_endo_mm_case_medians"))),
                        ("india", get(I, "A_endo_offset_mm_median_p10_p90", 0)),
                        ("hotel(negated)", -h_endo[1] if h_endo else None))
    src_p, epi = first(("jm0r", get(R, "epi_offset_mm_median")),
                       ("lima", p50(get(L, "halfmax_offset_epi_mm_case_medians"))),
                       ("india", get(I, "A_epi_offset_mm_median_p10_p90", 0)),
                       ("hotel", h_epi[1] if h_epi else None))
    if endo is None or epi is None:
        o4 = "not evaluable: no snap decision; rest TPR stays out (JA17 condition 2 unmet)"
    elif abs(epi) >= OFFSET_SNAP_READS or abs(endo) >= OFFSET_SNAP_READS:
        o4 = "half-maximum snap tool (role:swe) runs on the seeds before any read; thickness check R3 uses snapped borders"
    elif abs(endo) > OFFSET_GATE or abs(epi) > OFFSET_GATE:
        o4 = "snap tool needed for rest TPR only (JA17 condition 2); reads use the seeds as they are"
    else:
        o4 = "no snap: seed borders sit at the half-maximum within 0.25 mm"
    rule("R4", "Seed half-maximum offsets, endo / epi (mm, + = region beyond the edge)", f"{src_e} / {src_p}",
         [endo, epi], o4, "JA7, JA17; Hotel v2 §9")
    # --- 5. rest TPR gate (JA17)
    src_g, edge = first(("jm0r", get(R, "endo_10_90_mm_median")), ("hotel", get(H, "endo_10_90_mm_q", 1)))
    fwhm = None if edge is None else edge * FWHM_PER_1090
    adaptive = get(R, "tpr_guard_adaptive_free_patient_median")
    one_mm = first(("jm0r", get(R, "tpr_guard1_free_patient_median")),
                   ("hotel", get(H, "tpr_guard1.0", "patient_median_free_q", 1)),
                   ("lima", p50(get(L, "tpr_guarded_case_median"))))
    if edge is None:
        o5, val = "rest TPR not shown (edge width not measured)", None
    elif edge > EDGE_DROP:
        o5, val = "rest TPR not computed (edge > 2 mm)", None
    elif edge > EDGE_GATE:
        o5, val = "rest TPR not shown (edge > 1.5 mm); research export only", None
    else:
        guard = max(1.0, fwhm)
        if guard > 1.0 and adaptive is None:
            o5, val = (f"not evaluable: the adaptive guard ({guard:.2f} mm) needs JM-0R; rest TPR not shown "
                       "until then"), None
        else:
            val = adaptive if adaptive is not None else one_mm[1]
            off_ok = endo is not None and abs(endo) <= OFFSET_GATE
            if val is None:
                o5 = "not evaluable: no guarded TPR"
            elif not off_ok:
                o5 = "rest TPR not shown until borders are snapped (condition 2)"
            elif TPR_WINDOW[0] <= val <= TPR_WINDOW[1]:
                o5 = "rest TPR shown per segment as a patient-relative z-score (JA17, JA18)"
            else:
                o5 = "rest TPR not shown (median outside 0.99-1.15); research export only"
    rule("R5", "Rest TPR gate (JA17): edge <= 1.5 mm, |endo offset| <= 0.25 mm, guarded median 0.99-1.15",
         src_g, {"edge_1090_mm": edge, "fwhm_mm": fwhm, "guarded_median": val}, o5, "JA17")
    # --- 6. provisional fat cut (JA18)
    grid = get(R, "share_hearts_with_fat_cluster") or get(L, "share_hearts_with_fat_cluster")
    gsrc = "jm0r" if get(R, "share_hearts_with_fat_cluster") else ("lima" if grid else None)
    pick = None
    if grid:
        for c in FAT_C:
            for v in FAT_V:
                s = get(grid, str(c), str(v))
                if s is not None and s <= FAT_NULL:
                    pick = (c, v, s)
                    break
            if pick:
                break
    patient_rule = get(R, "share_hearts_with_fat_cluster_patient_rule")
    o6 = ("not evaluable: fat shown as a number only" if not grid else
          (f"provisional cut c = {pick[0]} HU, V = {pick[1]} mm3 (share {pick[2]})" if pick else
           "no (c, V) reaches <= 5 % of hearts: fat is a number only, never a flag"))
    if patient_rule is not None:
        o6 += f"; Hotel's patient noise-aware rule: share {patient_rule}" + (
            " (adopted if it is the less strict of the two passing rules)" if patient_rule <= FAT_NULL else "")
    rule("R6", "Provisional fat cut (JA18): least strict (c, V) with <= 5 % of hearts carrying a cluster", gsrc,
         pick, o6, "JA18; fixed again on the reference population before any seal read")
    # --- 7. septal-arc column (JA20)
    src, arc = first(("jm0r", get(R, "seg_changed_fixed_vs_arc_median")),
                     ("lima", p50(get(L, "myocardium_relabelled_fixed_vs_arc"))),
                     ("india", get(I, "C_seg_changed_prop_median")))
    rule("R7", "Septal-arc sensitivity column (JA20)", src, arc,
         "not evaluable: column kept" if arc is None else
         ("column dropped (< 10 % of mass changes segment)" if arc < ARC_DROP else "column kept"), "JA20")
    # --- 8. geodesic vs Euclidean (JA20)
    src, geo = first(("jm0r", get(R, "segments_differ_euclid_vs_geodesic")),
                     ("lima", get(L, "segments_differ_euclid_vs_geodesic")))
    rule("R8", "Geodesic vs Euclidean majority change (JA20)", src, geo,
         "not evaluable: Euclidean stays" if geo is None else
         ("Euclidean stays; no further ruling needed" if geo < GEO_RULE else
          "Hotel's pre-registered position for the ruling: Euclidean stays primary (it is the Voronoi rule "
          "Kurata 2015 and Ide 2017 validate, JA24); segments whose majority differs are shown as 'shared'"),
         "JA20, JA24")
    if not str(out[0]["outcome"]).startswith("proceed"):
        for r in out[1:]:
            r["outcome"] = "NOT APPLIED (R0 failed); would be: " + r["outcome"]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    for k in ("jm0r", "juliet", "lima", "india", "hotel", "out"):
        ap.add_argument("--" + k)
    a = ap.parse_args(argv)
    S = {k: load(getattr(a, k)) for k in ("jm0r", "juliet", "lima", "india", "hotel")}
    if not any(S.values()):
        sys.exit("no input: this procedure runs when the lead posts JM-0 / JM-0R outputs")
    res = decide(S)
    for r in res:
        print(f"{r['rule']}  {r['question']}\n    source {r['source']}: {r['value']}\n    -> {r['outcome']}")
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    return res


if __name__ == "__main__":
    main()
