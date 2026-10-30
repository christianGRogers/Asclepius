"""Janus-M JM-0R decision procedure (JA43; issue #193): the one pre-registered decision script.

Moved from ``experiments/JanusM/Hotel/r3/jm0r_decide.py`` (jm/rest-ccta) and extended as
``vault/JanusM/Judgements/Round 3 - rest-ccta.md`` JA43 rules. Lima's ``apply_r2_rules.py`` and
India's ``jm0r_rules.py`` are retired; their fallback mappers are ported below
(:func:`from_lima_jm0b`, :func:`merge_fallback`), and their dry runs stay as records.

It runs when the lead posts JM-0R's ``summary.json``, and not before. It reads **aggregate
JSON only** (no case id, no image, no path), so it needs no guard call: every number it reads was
produced by a guarded Fir job. Nobody runs it on Fir.

Inputs (JA43):

* ``--jm0r F``: JM-0R's ``summary.json``; its flat ``decision_inputs`` block (JA44) is read as is;
* or the JA23 fallback, through the ported mappers: ``--lima`` (Lima R2 ``jm0b_readout``
  summary), ``--india`` (India ``jm0_addon`` summary), ``--hotel`` (Hotel R2
  ``halfmax_tpr_m0`` aggregate), ``--juliet`` (Job JM-0's ``geometry_m0`` summary).

**Sign (JA44, canonical):** + = the region bounded by that border (the LV pool for the endocardium,
pool + myocardium for the epicardium) extends beyond the image half-maximum. JM-0R v2, Lima and
India report it this way; Hotel R2's add-on reports the endocardium the other way round, so its
endocardial value is negated by the fallback mapper.

**Missing inputs.** A missing input prints ``NOT DECIDABLE: <key>`` and the rule takes its
conservative branch, fixed below. No default value is ever substituted (Lima).

**R9** calls S3's ``janusm.calibrate.detectable_depth`` (JA40). Until S3 is merged the import fails,
and R9 prints ``NOT DECIDABLE: janusm.calibrate.detectable_depth (S3)`` with the provisional page
figure.

Output: one line per rule (its number and its source in the rulings), the ``NOT DECIDABLE`` lines,
and ``decisions.json`` (aggregates and decisions only)::

    python experiments/JanusM/fir/jm0r_decide.py --jm0r summary.json --out decisions.json
    python experiments/JanusM/fir/jm0r_decide.py --lima L.json --india I.json --hotel H.json \\
        --juliet J.json --out decisions.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

DECIDE_VERSION = "1"

# The JA44 contract: every key of JM-0R's ``decision_inputs``.
KEYS = (
    "n_cases", "n_usable",
    "aha_frame_fail_share", "aha_orientation_fail_share",
    "thickness_median_mm", "halves_segment_share",
    "endo_halfmax_offset_mm_median", "epi_halfmax_offset_mm_median",
    "endo_edge_10_90_mm_median",
    "tpr_guard1_freewall_median", "tpr_guard_adaptive_freewall_median",
    "tpr_guard_adaptive_freewall_patient_median", "tpr_guard_adaptive_share_below_0p99",
    "fat_grid", "fat_patient_rule_share",
    "septal_arc_mass_changed_median", "geodesic_segments_changed_share",
    "et_laplace_third_agreement_median",
    "cv_n", "cv_n_robust_log", "segment_shape", "rel_subendo_hu_sd",
    "script_version",
)

# ---- pre-registered thresholds (JA43's table; JA2, JA3, JA17, JA18, JA20, JA40) -------------
MIN_USABLE = 36                 # R0: of the 40 JM-0 cases
AHA_FAIL = 0.10                 # R1
HALVES_NOTE = 0.25              # R2
THICK_WINDOW = (4.2, 8.0)       # R3: 5.7-6.5 mm (Chen 2025) +- 1.5 mm (Hotel v2 §4.4)
SNAP_READS = 0.5                # R4: either |offset| above this -> snap seeds before any read
SNAP_TPR = 0.25                 # R4/R5: |endo| above this -> rest TPR needs snapped borders
BIAS_GUARD = 0.3                # R4: printed only (India): seed expected to fail the JA37 guard
EDGE_GATE = 1.5                 # R5: mm, 10-90 %
EDGE_DROP = 2.0                 # R5: not computed above this
EDGE_TO_FWHM = 1.09             # R5: FWHM = 10-90 % width / 1.09 (JA17)
TPR_WINDOW = (0.99, 1.15)       # R5
FAT_C = (0, -30, -50, -100)     # R6: HU, least strict first
FAT_V = (5, 20, 50)             # R6: mm3, least strict first within each c
FAT_NULL = 0.05                 # R6: share of hearts
ARC_DROP = 0.10                 # R7
GEO_SHARED = 0.10               # R8
DEPTH_WARN = 0.40               # R9: the page says so above this (Hotel; JA40)
F1_FLOOR_MM = 1.0               # R9: JA40's F1 floor until the reads exist (then JA42's RC)
DEPTH_SEED = 20261030           # R9: fixed
PROVISIONAL_DEPTH = 0.35        # R9: JA40's provisional print (cv_n 0.088, F1 1.0 mm; Hotel E7)

ND = "NOT DECIDABLE"


# --------------------------------------------------------------------------------------- helpers
def load(path):
    return json.loads(Path(path).read_text()) if path else None


def _get(d, *path):
    for k in path:
        if d is None:
            return None
        if isinstance(d, dict):
            d = d.get(k)
        elif isinstance(d, list) and isinstance(k, int) and -len(d) <= k < len(d):
            d = d[k]
        else:
            return None
    return d


def _med(v):
    """The median from the shapes the Round 2 scripts print: a number, {"p50"|"median": x},
    [q25, q50, q75, n] (Hotel) or [median, p10, p90] (India; take index 0 explicitly there)."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, dict):
        for k in ("p50", "median"):
            if v.get(k) is not None:
                return float(v[k])
    if isinstance(v, list) and len(v) >= 3 and v[1] is not None:
        return float(v[1])
    return None


def _neg(x):
    return None if x is None else -float(x)


# --------------------------------------------------------------------------------------- mappers
def from_jm0r(summary: dict) -> dict:
    """JM-0R v2's ``summary.json`` (or its bare ``decision_inputs`` block) -> the JA44 keys."""
    block = summary.get("decision_inputs", summary)
    return {k: block.get(k) for k in KEYS}


def from_lima_jm0b(s: dict) -> dict:
    """Lima R2's ``jm0b_readout`` summary (via ``summarise.py``) -> JA44 keys. Ported from
    ``Lima/r3/apply_r2_rules.py``. Lima's offsets are already canonical. Lima counts a load
    failure as a frame failure, as its script did."""
    s = s or {}
    n, ok = s.get("n_cases"), s.get("n_frame_ok")
    x = {"n_cases": n}
    if n and ok is not None:
        x["aha_frame_fail_share"] = (n - ok) / n
    if ok and _get(s, "orientation_ok", "fixed") is not None:
        x["aha_orientation_fail_share"] = 1 - s["orientation_ok"]["fixed"] / ok
    x["thickness_median_mm"] = _med(s.get("median_thickness_mm"))
    x["halves_segment_share"] = s.get("share_segments_needing_halves")
    for b in ("endo", "epi"):
        v = s.get(f"halfmax_offset_{b}_mm_case_medians")
        if isinstance(v, dict) and v.get("n"):
            x[f"{b}_halfmax_offset_mm_median"] = _med(v)
    fat = s.get("share_hearts_with_fat_cluster")
    if fat:
        x["fat_grid"] = {f"{c},{v}": share for c, d in fat.items() for v, share in d.items()}
    x["septal_arc_mass_changed_median"] = _med(s.get("myocardium_relabelled_fixed_vs_arc"))
    x["geodesic_segments_changed_share"] = s.get("segments_differ_euclid_vs_geodesic")
    x["et_laplace_third_agreement_median"] = _med(s.get("thirds_agree_et_laplace"))
    x["cv_n"] = s.get("rel_thickness_shape_corrected_sd")
    rel = s.get("rel_thickness_by_segment_mean_sd")
    if rel and all(str(k) in rel for k in range(1, 17)):
        x["segment_shape"] = [rel[str(k)][0] for k in range(1, 17)]
    return {k: v for k, v in x.items() if v is not None}


def from_india_addon(s: dict) -> dict:
    """India's ``jm0_addon`` summary -> JA44 keys (India's part of ``merge_fallback``). India's
    offsets are already canonical."""
    s = s or {}
    x = {"n_cases": s.get("n_cases"), "n_usable": s.get("n_ok"),
         "endo_halfmax_offset_mm_median": _get(s, "A_endo_offset_mm_median_p10_p90", 0),
         "epi_halfmax_offset_mm_median": _get(s, "A_epi_offset_mm_median_p10_p90", 0),
         "septal_arc_mass_changed_median": s.get("C_seg_changed_prop_median"),
         "et_laplace_third_agreement_median": s.get("B_third_agree_et_laplace_median")}
    return {k: v for k, v in x.items() if v is not None}


def from_hotel_r2(s: dict) -> dict:
    """Hotel R2's ``halfmax_tpr_m0`` aggregate -> JA44 keys. **Its endocardial offset is negated**
    (Hotel R2: + = the label's endocardium in the blood; JA43, JA44). Its TPR is the fixed 1 mm
    guard, which maps to ``tpr_guard1_freewall_median`` only: R5 uses it in place of the adaptive
    band only where the two are the same band (FWHM <= 1 mm)."""
    s = (s or {}).get("aggregate", s or {})
    x = {"n_cases": s.get("n_cases"), "n_usable": s.get("n_usable"),
         "endo_halfmax_offset_mm_median": _neg(_med(s.get("endo_halfmax_offset_mm_q25_50_75_n"))),
         "epi_halfmax_offset_mm_median": _med(s.get("epi_halfmax_offset_mm_q25_50_75_n")),
         "endo_edge_10_90_mm_median": _med(s.get("endo_10_90_mm_q")),
         "tpr_guard1_freewall_median": _med(_get(s, "tpr_guard1.0", "free_wall_segments_q"))}
    return {k: v for k, v in x.items() if v is not None}


def from_juliet(s: dict) -> dict:
    """Job JM-0's ``geometry_m0`` summary -> JA44 keys (Hotel's own fallback)."""
    s = (s or {}).get("summary", s or {})
    x = {"n_cases": s.get("n_cases"), "n_usable": s.get("n_usable"),
         "thickness_median_mm": s.get("median_thick_mm")}
    return {k: v for k, v in x.items() if v is not None}


# JA23's fallback order. Each later source fills only what is missing, except the half-maximum
# offsets and the edge, which Hotel measures on the free wall and which it supplies (India).
_HOTEL_WINS = ("endo_halfmax_offset_mm_median", "epi_halfmax_offset_mm_median",
               "endo_edge_10_90_mm_median")


def merge_fallback(lima=None, india=None, hotel=None, juliet=None) -> dict:
    """The JA23 fallback: Juliet, then Lima, India and Hotel mapped onto the JA44 keys (India's
    ``merge_fallback``, ported, with Hotel's own Juliet source).

    Returns (inputs, source per key)."""
    x, src = {}, {}
    for name, part in (("juliet", from_juliet(juliet)), ("lima", from_lima_jm0b(lima)),
                       ("india", from_india_addon(india)), ("hotel", from_hotel_r2(hotel))):
        for k, v in part.items():
            if k not in x or (name == "hotel" and k in _HOTEL_WINS):
                x[k], src[k] = v, name
    return {k: x.get(k) for k in KEYS}, src


# --------------------------------------------------------------------------------------- rules
def _detectable_depth():
    """S3's function, or None while S3 is not merged."""
    try:
        from janusm.calibrate import detectable_depth
    except Exception:  # noqa: BLE001 -- not merged yet (or broken): R9 is NOT DECIDABLE
        return None
    return detectable_depth


def decide(x: dict, *, rc_terr_mm: float = F1_FLOOR_MM, sig_m: float = 0.0, depth_fn=None):
    """Apply R0-R10 (JA43) to the JA44 inputs ``x``. Returns a list of rule records."""
    out = []

    def rule(rid, basis, keys, outcome, missing=(), **extra):
        out.append({"rule": rid, "basis": basis, "inputs": {k: x.get(k) for k in keys},
                    "missing": list(missing), "outcome": outcome, **extra})

    def miss(*keys):
        return [k for k in keys if x.get(k) is None]

    # R0 -- usable cases
    m = miss("n_usable")
    n = x.get("n_usable")
    proceed = not m and n >= MIN_USABLE
    rule("R0", "JA43 R0; Hotel v3 §5.1", ["n_cases", "n_usable"],
         "proceed" if proceed else
         f"STOP: fewer than {MIN_USABLE} usable cases; no rule is applied", m)

    # R1 -- AHA frame (JA3)
    m = miss("aha_frame_fail_share", "aha_orientation_fail_share")
    ok_shares = [x[k] for k in ("aha_frame_fail_share", "aha_orientation_fail_share")
                 if x.get(k) is not None]
    fix = bool(m) or any(v > AHA_FAIL for v in ok_shares)
    rule("R1", "JA43 R1; JA3", ["aha_frame_fail_share", "aha_orientation_fail_share"],
         "failing cases show 'AHA frame failed' and no segment table"
         + ("; a role:swe frame fix before decision-set scoring, the reference population and any"
            " table (reads proceed)" if fix else ""), m, frame_fix=fix)

    # R2 -- halves (JA2)
    m = miss("halves_segment_share")
    note = bool(m) or x["halves_segment_share"] > HALVES_NOTE
    rule("R2", "JA43 R2; JA2", ["halves_segment_share"],
         "JA2 per segment, as the module computes"
         + ("; Table A's header states the layer count per segment" if note else
            "; Table A's header unchanged") + " (never halves everywhere)", m, header_note=note)

    # R3 -- thickness definition (Hotel v2 §4.4)
    m = miss("thickness_median_mm")
    agree = not m and THICK_WINDOW[0] <= x["thickness_median_mm"] <= THICK_WINDOW[1]
    rule("R3", "JA43 R3; Hotel v2 §4.4, F3", ["thickness_median_mm"],
         "definitions agree; F3 holds" if agree else
         "readers hand-measure 3 mid-ventricular segments on the first 20 decision cases; the "
         "definition is aligned before the reference population; no thinning flag ships before "
         "that", m, f3_holds=agree)

    # R4 -- seed half-maximum offsets (canonical sign)
    m = miss("endo_halfmax_offset_mm_median", "epi_halfmax_offset_mm_median")
    e, p = x.get("endo_halfmax_offset_mm_median"), x.get("epi_halfmax_offset_mm_median")
    if m:
        snap_reads, snap_tpr, fail_guard = None, True, None
        o4 = ("no snap decision until both offsets are measured; rest TPR treated as needing "
              "snapped borders")
    else:
        snap_reads = abs(e) > SNAP_READS or abs(p) > SNAP_READS
        snap_tpr = abs(e) > SNAP_TPR
        fail_guard = max(abs(e), abs(p)) > BIAS_GUARD
        o4 = ("the snap tool (S8) runs on the seeds before any read" if snap_reads else
              "no snap before reads")
        o4 += ("; rest TPR needs snapped borders" if snap_tpr else "; rest TPR needs no snap")
        o4 += (f"; printed, not acted on: the seed is {'' if fail_guard else 'not '}expected to "
               f"fail the {BIAS_GUARD} mm guard")
    rule("R4", "JA43 R4; JA17, JA44", ["endo_halfmax_offset_mm_median",
                                       "epi_halfmax_offset_mm_median"], o4, m,
         snap_before_reads=snap_reads, snap_for_tpr=snap_tpr,
         seed_expected_to_fail_bias_guard=fail_guard)

    # R5 -- rest TPR (JA17)
    edge = x.get("endo_edge_10_90_mm_median")
    tpr, tpr_key = x.get("tpr_guard_adaptive_freewall_median"), "tpr_guard_adaptive_freewall_median"
    if tpr is None and edge is not None and edge / EDGE_TO_FWHM <= 1.0 \
            and x.get("tpr_guard1_freewall_median") is not None:
        # max(1 mm, FWHM) is 1 mm here: the 1 mm guard is the adaptive band, not a substitute.
        tpr, tpr_key = x["tpr_guard1_freewall_median"], "tpr_guard1_freewall_median"
    m = []
    if edge is None:
        m, o5 = ["endo_edge_10_90_mm_median"], "not shown"
    elif edge > EDGE_DROP:
        o5 = "not computed (edge > 2 mm)"
    elif tpr is None:
        m, o5 = ["tpr_guard_adaptive_freewall_median"], "not shown"
    elif edge <= EDGE_GATE and TPR_WINDOW[0] <= tpr <= TPR_WINDOW[1]:
        if e is None:
            m, o5 = ["endo_halfmax_offset_mm_median"], "not shown"
        elif abs(e) <= SNAP_TPR:
            o5 = "shown per segment as a patient-relative z-score (JA17, JA18)"
        else:
            o5 = "shown after snapping (S8); research export until then"
    else:
        o5 = "research export only; not in the table"
    rule("R5", "JA43 R5; JA17", ["endo_edge_10_90_mm_median", "endo_halfmax_offset_mm_median",
                                 "tpr_guard_adaptive_freewall_median",
                                 "tpr_guard1_freewall_median",
                                 "tpr_guard_adaptive_freewall_patient_median",
                                 "tpr_guard_adaptive_share_below_0p99"], o5, m, tpr_from=tpr_key)

    # R6 -- fat cut (JA18)
    grid, m, pick = x.get("fat_grid"), [], None
    if not grid:
        m = ["fat_grid"]
    else:
        for c in FAT_C:
            for v in FAT_V:
                share = grid.get(f"{c},{v}")
                if share is None:
                    m = [f"fat_grid[{c},{v}]"]
                    break
                if share <= FAT_NULL:
                    pick = {"c_hu": c, "v_mm3": v, "share": share}
                    break
            if m or pick:
                break
    if m:
        o6 = "fat is a number only"
    elif pick:
        o6 = (f"provisional cut c = {pick['c_hu']} HU, V = {pick['v_mm3']} mm3 "
              f"(share {pick['share']})")
    else:
        m = miss("fat_patient_rule_share")
        if not m and x["fat_patient_rule_share"] <= FAT_NULL:
            pick = {"rule": "hotel_patient", "share": x["fat_patient_rule_share"]}
            o6 = f"no grid cell passes; Hotel's patient rule (share {pick['share']})"
        else:
            o6 = "no grid cell or patient rule passes: fat is a number only"
    rule("R6", "JA43 R6; JA18", ["fat_grid", "fat_patient_rule_share"],
         o6 + ". Provisional; fixed on the reference population", m, cut=pick)

    # R7 -- septal-arc column (JA20)
    m = miss("septal_arc_mass_changed_median")
    keep = bool(m) or x["septal_arc_mass_changed_median"] >= ARC_DROP
    rule("R7", "JA43 R7; JA20", ["septal_arc_mass_changed_median"],
         "column kept (a sensitivity column)" if keep else
         "column dropped (< 10 % of mass changes segment)", m, column_kept=keep)

    # R8 -- geodesic (JA20), ruled now
    m = miss("geodesic_segments_changed_share")
    shared = not m and x["geodesic_segments_changed_share"] >= GEO_SHARED
    rule("R8", "JA43 R8; JA20, JA24", ["geodesic_segments_changed_share"],
         "Euclidean is primary"
         + ("; segments whose majority changes are marked 'shared' in Table A/B and geodesic mass "
            "goes to the research export" if shared else "; no segment marked 'shared'"),
         m, shared_marking=shared)

    # R9 -- detectable depth (JA40, S3)
    m = miss("cv_n", "segment_shape")
    fn = depth_fn if depth_fn is not None else _detectable_depth()
    depth = None
    if fn is None:
        m = m + ["janusm.calibrate.detectable_depth (S3)"]
    if m:
        o9 = (f"the page prints the provisional {int(round(100 * PROVISIONAL_DEPTH))} % (JA40) "
              "until it can be computed")
    else:
        try:
            res = fn(x["cv_n"], x["segment_shape"], rc_terr_mm, sig_m=sig_m, seed=DEPTH_SEED)
        except ValueError as e:  # inputs S3 cannot simulate (e.g. cv_n 0: no normal variation)
            res = {"error": str(e)}
        depth = res.get("depth")
        if "error" in res:
            o9 = (f"the page prints the provisional {int(round(100 * PROVISIONAL_DEPTH))} % "
                  f"(JA40): the detectable depth cannot be computed from these inputs "
                  f"({res['error']})")
        elif depth is None:
            o9 = "the page prints: thinning detection not demonstrated at this measurement error"
        else:
            o9 = (f"the page prints a detectable depth of {int(round(100 * depth))} % "
                  f"(cv_n {x['cv_n']}, F1 {rc_terr_mm} mm)")
            if depth > DEPTH_WARN:
                o9 += f"; above {DEPTH_WARN:.2f}: the page says so, and nothing is loosened"
    rule("R9", "JA43 R9; JA40", ["cv_n", "cv_n_robust_log", "segment_shape"], o9, m,
         depth=depth, rc_terr_mm=rc_terr_mm, sig_m=sig_m)

    # R10 -- equal thickness vs Laplace, reported only
    m = miss("et_laplace_third_agreement_median")
    rule("R10", "JA43 R10", ["et_laplace_third_agreement_median"], "reported only", m)

    if not proceed:
        for r in out[1:]:
            r["outcome"] = "NOT APPLIED (R0 stopped); would be: " + r["outcome"]
            r["applied"] = False
    for r in out:
        r.setdefault("applied", True)
    return out


def lines(decisions) -> list:
    """One line per rule (its number, its source in the rulings and where its inputs came from),
    then its NOT DECIDABLE lines."""
    text = []
    for r in decisions:
        vals = ", ".join(f"{k}={_fmt(v)}" for k, v in r["inputs"].items() if v is not None)
        frm = "/".join(r.get("from") or ()) or "-"
        text.append(f"{r['rule']} [{r['basis']}] from {frm}: {vals or '-'} -> {r['outcome']}")
        text.extend(f"    {ND}: {k}" for k in r["missing"])
    return text


def _fmt(v):
    if isinstance(v, float):
        return f"{v:.4g}"
    if isinstance(v, list) and len(v) > 4:
        return f"[{len(v)} values]"
    if isinstance(v, dict):
        return f"{{{len(v)} cells}}"
    return str(v)


# --------------------------------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    for k in ("jm0r", "lima", "india", "hotel", "juliet", "out"):
        ap.add_argument("--" + k)
    ap.add_argument("--rc-mm", type=float, default=F1_FLOOR_MM,
                    help="F1's RC per territory (mm); JA40's floor until the reads exist")
    ap.add_argument("--sig-m", type=float, default=0.0,
                    help="added segment error (mm); 0 when cv_n comes from the table's model")
    a = ap.parse_args(argv)
    if a.jm0r:
        x = from_jm0r(load(a.jm0r))
        src = {k: "jm0r" for k, v in x.items() if v is not None}
    elif any((a.lima, a.india, a.hotel, a.juliet)):
        x, src = merge_fallback(load(a.lima), load(a.india), load(a.hotel), load(a.juliet))
    else:
        print("no input: this procedure runs when the lead posts JM-0R's summary.json",
              file=sys.stderr)
        return 2
    res = decide(x, rc_terr_mm=a.rc_mm, sig_m=a.sig_m)
    for r in res:
        r["from"] = sorted({src[k] for k, v in r["inputs"].items() if v is not None and k in src})
    for line in lines(res):
        print(line)
    if a.out:
        doc = {"decide_version": DECIDE_VERSION, "input_script_version": x.get("script_version"),
               "sources": src, "decisions": res}
        Path(a.out).write_text(json.dumps(doc, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
