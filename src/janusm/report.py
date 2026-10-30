"""The Janus-M table writer (S7, issue #196; Round 3 rest-ccta JA48, Hotel v3 §4.3).

``build(...)`` turns one case's borders, CT, coronary tree, the pinned reference config and the
reader's grades into Tables A and B; ``render_markdown`` / ``render_html`` print them. The same
inputs always give the same bytes.

Order of work: the JA12 guard on the case (``purpose`` as the caller declares; seal cases only
under ``seal_scoring``) before anything else; then the reference config, which must match its pin
(:func:`janusm.reference.load`); only then the arrays.

As amended by JA48:

* **Header:** phase (or "phase unrecorded", and every thickness is phase-uncertain), spacing, the
  endocardial 10-90 % edge and both half-maximum offsets in the canonical sign (JA44: + = the
  region bounded by the border extends beyond the image half-maximum; supplied by the caller from
  the read checker or JM-0R v2), AHA orientation and septal arc, territory source, the halves note
  (R2), ``HARNESS_VERSION``, ``GEOMETRY_VERSION``, the config sha256 and ``guard_version``.
* **Table A (segments 1-17):** numbers with population percentiles, never a flag (JA18).
* **Table B (LAD, LCx, RCA):** the reader's CAD-RADS 2.0 grade copied ("not graded" if absent);
  masses; segments ("shared" apart); per sign a flag only if rule C's territory flag (AHA default
  map, as calibrated) and F1 (D > RC_T) and the sign's gate passed (JA41), else the number; the
  composite; exactly one concordance phrase from Lima v2 §3 item 4c's table.
* **Footer:** the research-output sentence, each depth sign's page line (S3's ``page_line``,
  filled from the config), and the population label.

As amended by Round 4 (``jm/rest-ccta`` JA63, JA64, JA67, JA69; R4-S8 to R4-S14):

* the config's ``geometry_version`` and ``features_version`` must equal the running ones
  (:class:`ReportError` otherwise);
* F1's floor is :func:`janusm.reference.rc_floor_mm` at the patient's own E_T, the one function
  the gate also uses; no level of 1.0 remains;
* a fall-back to the AHA default map is printed in the header, never silent;
* "shared" also marks a segment whose Euclidean and geodesic majorities differ, when the config's
  R8 verdict says so;
* Table B's grade: LAD and LCx take the worse of their own and LM's (:func:`territory_grade`),
  noted "LM <grade>"; :func:`grades_from_read_record` maps an exported read form; a row with a
  lesion point prints "distal mass: not computed (report v1)";
* the septal-arc column (R7 kept) holds the arc-proportional values of segments 2, 3, 8 and 9.

Never printed outside the fixed footer sentences: a sensitivity, scar, ischaemia, 5.5 mm,
-10 HU, or 0.99 as a cut (:data:`FORBIDDEN`).
"""

from __future__ import annotations

import html
import json
import re
from typing import Dict, Optional

from janusm import calibrate
from janusm import features as F
from janusm import geometry as G
from janusm import reference as R

REPORT_VERSION = "1.1.0"
TERRITORIES = F.TERRITORIES
SIGNIFICANT = ("3", "4A", "4B", "5")           # CAD-RADS 2.0, >= 50 %
NOT_SIGNIFICANT = ("0", "1", "2")
NOT_GRADED = "not graded"
#: CAD-RADS 2.0 order for "the worse of" (JA67); N and absent rank below every grade.
GRADE_ORDER = ("0", "1", "2", "3", "4A", "4B", "5")
LM_FEEDS = ("LAD", "LCx")
DISTAL_NOTE = "distal mass: not computed (report v1)"
#: Hotel v2 §3.3, exact; chosen by Lima v2 §3 item 4c's table.
PHRASES = {
    "pattern_significant": "Territory shows chronic-infarct-like geometry",
    "pattern_other": "Geometric sign without graded stenosis",
    "flags": "Isolated measurements outside range",
    "none": "No geometric sign in territory",
}
FOOTER_RESEARCH = "Research output, not validated: no scar or perfusion reference."
FOOTER_POPULATION = "Population: this population, phase-uncertain."
FORBIDDEN = (r"sensitivit", r"scar", r"isch(a)?emi", r"5\.5\s*mm", r"[-−]10\s*HU")
UNITS = {"thinning": "mm", "hypoattenuation": "rel.", "fat": "mm³"}


class ReportError(RuntimeError):
    """The table cannot be made for this input."""


def _r(x, nd=2):
    return None if x is None else round(float(x), nd)


def _get(d, k):
    if not d:
        return None
    return d.get(k, d.get(str(k)))


def grade_class(grade) -> str:
    """"significant" (CAD-RADS 3-5), "not_significant" (0-2) or "not_graded" (absent, N)."""
    g = None if grade is None else str(grade).strip().upper()
    if g in SIGNIFICANT:
        return "significant"
    if g in NOT_SIGNIFICANT:
        return "not_significant"
    return "not_graded"


def _norm_grade(g) -> Optional[str]:
    if g is None:
        return None
    g = str(g).strip().upper()
    return g or None


def territory_grade(grades: dict, territory: str):
    """JA67: (grade, ``grade_source`` note) for a Table B row. LAD and LCx take the worse of
    their own grade and LM's (0 < 1 < 2 < 3 < 4A < 4B < 5); the note reads "LM <grade>" when LM
    is the source. N only if both are N or absent. RCA is its own."""
    grades = grades or {}
    own = _norm_grade(grades.get(territory))
    if territory not in LM_FEEDS:
        return own, None
    lm = _norm_grade(grades.get("LM"))
    rank = {g: i for i, g in enumerate(GRADE_ORDER)}
    ro, rl = rank.get(own), rank.get(lm)
    if rl is not None and (ro is None or rl > ro):
        return lm, f"LM {lm}"
    if ro is None and rl is None and own is None and lm == "N":
        return lm, "LM N"
    return own, None


def grades_from_read_record(rec: dict) -> dict:
    """An exported read record's form (``cadrads``, ``lesionPoints``; JA46 (d)) as
    :func:`build`'s ``reader_grades``: ``{"LM": "4B", "LAD": "0", ..., "lesion_point":
    {vessel: [x, y, z]}}``. The mapping is :mod:`janusm_reads.readform`'s, the one the export
    writes the record with (R5-S6 S13)."""
    from janusm_reads import readform

    return readform.reader_grades(readform.read_form(rec))


def sign_decision(sign: str, s: Optional[dict], territory: str, cfg: dict) -> dict:
    """One Table B sign cell (JA41): a flag only if rule C's territory flag (AHA default map),
    F1 (D > the floor of :func:`janusm.reference.rc_floor_mm` at the patient's E_T) and the
    sign's gate passed; else the number."""
    if s is None:
        return {"shown": "number", "value": None, "flag": False, "note": "not measured"}
    d = s["D"][territory]
    e = (s.get("E") or {}).get(territory)
    ok_c = bool(s["territory_rule_c"][territory])
    rc = cfg["rc"][sign]
    floor = None
    if rc.get("status") == "computed":
        floor = R.rc_floor_mm(rc, territory, e)
    ok_f1 = d is not None and floor is not None and d > floor
    ok_gate = cfg[sign].get("status") == "flag"
    flag = bool(ok_c and ok_f1 and ok_gate)
    return {"shown": "flag" if flag else "number", "flag": flag,
            "value": _r(d, 2 if sign != "fat" else 1), "units": UNITS[sign],
            "floor": _r(floor, 3), "expected": _r(e, 3), "map": s.get("map")}


def phrase(pattern: bool, any_flag: bool, grade) -> str:
    """Lima v2 §3 item 4c: exactly one phrase per territory."""
    if pattern:
        return PHRASES["pattern_significant" if grade_class(grade) == "significant"
                       else "pattern_other"]
    return PHRASES["flags" if any_flag else "none"]


def _arc_value(feat: dict, pct: dict, k: int) -> Optional[dict]:
    """JA69 (a): segment ``k``'s arc-proportional wall and relative subendocardial HU with their
    population percentiles; None outside segments 2, 3, 8 and 9 or below the frame guard."""
    if k not in F.ARC_SEPTAL:
        return None
    arc = feat.get("septal_arc") or {}
    w, h = _get(arc.get("wall_mm"), k), _get(arc.get("rel_subendo_hu"), k)
    if w is None and h is None:
        return None
    tab = pct.get("septal_arc") or {}
    return {"thickness_mm": _r(w), "rel_subendo_hu": _r(h),
            "thickness_pctl": R.percentile_of(w, _get(tab.get("wall_mm"), k)),
            "rel_subendo_pctl": R.percentile_of(h, _get(tab.get("rel_subendo_hu"), k))}


def _contiguous_pair(segs) -> bool:
    s = set(int(x) for x in segs)
    return any(n in s for x in s if x <= 16 for n in calibrate.RING[x])


def build(case_id, labels, ct, affine, coronary, reference=None, reader_grades=None, *,
          purpose, header: Optional[dict] = None,
          coronary_source: str = "ImageCAS-X reference tree", root=None) -> dict:
    """Tables A and B for one case. ``reference``: the config path (default: the repository's,
    which must match ``janusm.guard.REFERENCE_SHA256``). ``reader_grades``: ``{"LAD": "3",
    ...}`` (CAD-RADS 2.0 worst lesion per vessel; missing or "N" -> not graded) and optionally
    ``"lesion_point": {vessel: [x, y, z]}``. ``header``: ``phase``, ``endo_edge_10_90_mm``,
    ``endo_halfmax_offset_mm``, ``epi_halfmax_offset_mm`` (canonical sign, JA44)."""
    from janusm import guard, harness

    guard.refuse([case_id], what="Janus-M report (S7)", purpose=purpose, root=root)  # first
    ref = R.load(reference, root=root)
    cfg = ref.data
    for key, running in (("geometry_version", G.GEOMETRY_VERSION),
                         ("features_version", F.FEATURES_VERSION)):
        if cfg.get(key) != running:
            raise ReportError(f"the reference config's {key} {cfg.get(key)!r} is not the running "
                              f"{running!r}: the population and the page would measure a case "
                              "differently (JA48)")
    header = dict(header or {})
    grades = dict(reader_grades or {})
    feat = F.case_features(labels, ct, affine, coronary, guard_mm=float(cfg["guard_mm"]))
    if feat.get("frame") != "ok":
        raise ReportError("AHA frame failed: no segment table (JA43 R1)")
    pct = cfg["percentiles"]
    st = R.case_state(feat, cfg, "patient")
    geo_shared = bool(cfg["table"].get("geodesic_shared"))
    terr_e = feat.get("segment_territory") or {}
    terr_g = feat.get("segment_territory_geodesic") or {}

    def shared(k) -> bool:
        sh = _get(feat.get("segment_territory_share"), k)
        if sh is not None and sh < F.SHARED_BELOW:
            return True
        if geo_shared:  # JA43 R8: the two majorities differ
            a, b = _get(terr_e, k), _get(terr_g, k)
            return a is not None and b is not None and a != b
        return False

    # ---------------------------------------------------------------- header
    phase = header.get("phase")
    halves = feat.get("halves_segments", [])
    hd = {
        "case": str(case_id),
        "phase": phase if phase else "phase unrecorded",
        "thickness_note": None if phase else "every thickness is phase-uncertain",
        "spacing_mm": feat["spacing_mm"],
        "endo_edge_10_90_mm": _r(header.get("endo_edge_10_90_mm")),
        "endo_halfmax_offset_mm": _r(header.get("endo_halfmax_offset_mm")),
        "epi_halfmax_offset_mm": _r(header.get("epi_halfmax_offset_mm")),
        "offset_sign": "+ = the region bounded by the border extends beyond the image "
                       "half-maximum (JA44)",
        "aha_orientation": "pass" if feat.get("orientation_ok") and not feat["aha_flagged"]
                           else "fail",
        "septal_arc_deg": feat.get("septal_arc_deg"),
        "territory_source": coronary_source if coronary is not None else "AHA default map only",
        "territory_map": st["map"],
        "shared_rule": ("majority share < 0.6, or Euclidean and geodesic majorities differ (R8)"
                        if geo_shared else "majority share < 0.6"),
        "layers": {"thirds": 17 - len(halves), "halves": len(halves)},
        "halves_note": bool(cfg["table"]["halves_note"]),
        "harness_version": harness.HARNESS_VERSION,
        "geometry_version": G.GEOMETRY_VERSION,
        "features_version": F.FEATURES_VERSION,
        "report_version": REPORT_VERSION,
        "reference_sha256": ref.sha256,
        "guard_version": guard.GUARD_VERSION,
        "guard_purpose": purpose,
    }

    # ---------------------------------------------------------------- Table A
    tpr = cfg["rest_tpr"]
    fat_c, fat_v = cfg["fat"].get("c_hu"), cfg["fat"].get("v_mm3")
    fat_seg = (feat.get("fat_segment_mm3") or {}).get(str(fat_c), {}).get(str(fat_v), {}) \
        if fat_c is not None else None
    terr = feat.get("segment_territory") or {}
    share = feat.get("segment_territory_share") or {}
    rows = []
    for k in range(1, 18):
        w = _get(feat["wall_mm"], k)
        sub = _get(feat.get("rel_subendo_hu"), k) if k <= 16 else None
        t = _get(terr, k)
        sh = _get(share, k)
        row = {
            "segment": k, "name": G.SEGMENT_NAMES[k],
            "layers": _get(feat["layer_scheme"], k),
            "thickness_mm": _r(w),
            "thickness_pctl": R.percentile_of(w, _get(pct["thickness_mm"], k)),
            "rel_thickness": _r(_get(feat.get("rel_thickness"), k)) if k <= 16 else None,
            "rel_subendo_hu": _r(sub),
            "rel_subendo_pctl": R.percentile_of(sub, _get(pct["rel_subendo_hu"], k)),
            "core_fat_mm3": (_r(_get(fat_seg, k) or 0.0, 1) if fat_seg is not None else None),
            "territory": t, "territory_share": _r(sh),
            "shared": shared(k),
            "aha_territory": G.AHA_STANDARD[k],
        }
        x = _get(feat.get("tpr"), k)
        if tpr["gate"] == "pass" and x is not None and tpr.get("z_scale"):
            row["rest_tpr_z"], row["rest_tpr_note"] = _r((x - tpr["median"]) / tpr["z_scale"]), None
        else:
            row["rest_tpr_z"] = None
            row["rest_tpr_note"] = (f"not shown: rest TPR gate {tpr['gate']}"
                                    if tpr["gate"] != "pass" else "not measured")
        if cfg["table"]["septal_arc_column"]:
            row["septal_arc_value"] = _arc_value(feat, pct, k)
        rows.append(row)

    # ---------------------------------------------------------------- Table B
    tmap = F.territory_segments(feat, "patient")
    tb = []
    for t in TERRITORIES:
        signs: Dict[str, dict] = {sign: sign_decision(sign, st.get(sign), t, cfg)
                                  for sign in R.SIGNS}
        th, hy = st.get("thinning"), st.get("hypoattenuation")
        sub_flag = signs["hypoattenuation"]["flag"] or signs["fat"]["flag"]
        composite = signs["thinning"]["flag"] and sub_flag
        if composite and cfg["composite"]["needs_two_contiguous"]:
            tsegs = [k for k in calibrate.TERR16[t] if th["seg_flag"][k - 1]
                     and ((hy is not None and hy["seg_flag"][k - 1])
                          or (fat_seg is not None and (_get(fat_seg, k) or 0) > 0))]
            composite = _contiguous_pair(tsegs)
        any_flag = any(v["flag"] for v in signs.values())
        g, g_src = territory_grade(grades, t)
        points = grades.get("lesion_point") or {}
        has_point = bool(points.get(t) or (t in LM_FEEDS and points.get("LM")))
        segs = tmap.get(t, [])
        tb.append({
            "territory": t,
            "grade": str(g) if g not in (None, "") else NOT_GRADED,
            "grade_class": grade_class(g), "grade_source": g_src,
            "mass_g": _r(_get(feat.get("mass_g"), t), 1),
            "mass_share": _r(_get(feat.get("mass_share"), t), 3),
            "aha_mass_g": _r(feat["mass_g_aha"][t], 1),
            "segments": [k for k in segs if not shared(k)],
            "shared_segments": [k for k in segs if shared(k)],
            "signs": signs, "composite": bool(composite),
            "phrase": phrase(bool(composite), any_flag, g),
            "mass_distal_g": None,
            "mass_distal_note": DISTAL_NOTE if has_point else None,
        })

    footer = [FOOTER_RESEARCH] + [cfg["page_line"][s] for s in R.DEPTH_SIGNS
                                  if s in cfg.get("page_line", {})] + [FOOTER_POPULATION]
    if st["map"] == "aha_fallback":
        hd["territory_map_note"] = ("D on the AHA default map: no patient-specific map "
                                    "(fall-back, JA63)")
    return {"report_version": REPORT_VERSION, "header": hd, "table_a": rows, "table_b": tb,
            "statuses": {s: cfg[s].get("status") for s in R.SIGNS}, "footer": footer}


# -------------------------------------------------------------------------------------- render
def dumps(rep: dict) -> str:
    return json.dumps(rep, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def _fmt(x, nd=2):
    if x is None:
        return "—"
    if isinstance(x, bool):
        return "yes" if x else "no"
    if isinstance(x, float):
        t = f"{x:.{nd}f}"
        return t[1:] if t.startswith("-") and float(t) == 0 else t
    return str(x)


def _pct(x):
    return "" if x is None else f" (p{x})"


def _header_lines(h: dict) -> list:
    off = lambda k: _fmt(h[k]) + " mm" if h[k] is not None else "not measured"  # noqa: E731
    lines = [
        ("Phase", h["phase"] + (f"; {h['thickness_note']}" if h["thickness_note"] else "")),
        ("Spacing", " × ".join(_fmt(x, 2) for x in h["spacing_mm"]) + " mm"),
        ("Endocardial 10–90 % edge", off("endo_edge_10_90_mm")),
        ("Half-maximum offsets", f"endocardium {off('endo_halfmax_offset_mm')}, "
                                 f"epicardium {off('epi_halfmax_offset_mm')} ({h['offset_sign']})"),
        ("AHA orientation", f"{h['aha_orientation']}; septal arc "
                            f"{_fmt(h['septal_arc_deg'], 1)}°"),
        ("Territory source", h["territory_source"]),
        ("Territory map", "patient-specific" if h.get("territory_map") == "patient" else
         h.get("territory_map_note") or str(h.get("territory_map"))),
        ("Shared segments", h.get("shared_rule", "majority share < 0.6")),
    ]
    if h["halves_note"]:
        lines.append(("Layers per segment", f"{h['layers']['thirds']} in thirds, "
                                            f"{h['layers']['halves']} in halves"))
    lines.append(("Versions", f"harness {h['harness_version']}, geometry "
                              f"{h['geometry_version']}, features {h['features_version']}, "
                              f"report {h['report_version']}, guard {h['guard_version']}"))
    lines.append(("Reference config sha256", h["reference_sha256"]))
    return lines


def _table_a(rows) -> tuple:
    cols = ["Segment", "Layers", "Thickness mm", "Rel. thickness", "Rel. subendo HU",
            "Core fat mm³", "Rest TPR z", "Territory (share)", "AHA default"]
    if rows and "septal_arc_value" in rows[0]:
        cols.append("Septal arc: thickness mm; rel. subendo HU")
    body = []
    for r in rows:
        terr = "—" if r["territory"] is None else (
            f"{r['territory']} ({_fmt(r['territory_share'])})"
            + (" shared" if r["shared"] else ""))
        cells = [f"{r['segment']} {r['name']}", _fmt(r["layers"]),
                 _fmt(r["thickness_mm"]) + _pct(r["thickness_pctl"]),
                 _fmt(r["rel_thickness"]),
                 _fmt(r["rel_subendo_hu"]) + _pct(r["rel_subendo_pctl"]),
                 _fmt(r["core_fat_mm3"], 1),
                 _fmt(r["rest_tpr_z"]) if r["rest_tpr_z"] is not None else r["rest_tpr_note"],
                 terr, r["aha_territory"]]
        if "septal_arc_value" in r:
            a = r["septal_arc_value"]
            cells.append("—" if a is None else
                         f"{_fmt(a['thickness_mm'])}{_pct(a['thickness_pctl'])}; "
                         f"{_fmt(a['rel_subendo_hu'])}{_pct(a['rel_subendo_pctl'])}")
        body.append(cells)
    return cols, body


def _sign_cell(s: dict) -> str:
    if s["value"] is None:
        return s.get("note", "—")
    v = f"{_fmt(s['value'], 1 if s.get('units') == 'mm³' else 2)} {s['units']}"
    return f"FLAG ({v})" if s["flag"] else v


def _table_b(rows) -> tuple:
    cols = ["Territory", "Reader grade (CAD-RADS 2.0)", "Mass g (share)", "AHA default mass g",
            "Segments", "Shared segments", "Thinning", "Hypoattenuation", "Fat", "Composite",
            "Mass distal to marked lesion (unvalidated)", "Concordance"]
    body = []
    for r in rows:
        grade = r["grade"] + (f" ({r['grade_source']})" if r.get("grade_source") else "")
        body.append([r["territory"], grade,
                     f"{_fmt(r['mass_g'], 1)} ({_fmt(r['mass_share'], 3)})",
                     _fmt(r["aha_mass_g"], 1),
                     ", ".join(map(str, r["segments"])) or "—",
                     ", ".join(map(str, r["shared_segments"])) or "—",
                     _sign_cell(r["signs"]["thinning"]),
                     _sign_cell(r["signs"]["hypoattenuation"]),
                     _sign_cell(r["signs"]["fat"]), _fmt(r["composite"]),
                     r["mass_distal_note"] or "—", r["phrase"]])
    return cols, body


def render_markdown(rep: dict) -> str:
    h = rep["header"]
    out = [f"# Janus-M table: {h['case']}", ""]
    out += [f"- **{k}:** {v}" for k, v in _header_lines(h)]
    for title, (cols, body) in (("Table A: segments (numbers, never flags)", _table_a(
            rep["table_a"])), ("Table B: territories", _table_b(rep["table_b"]))):
        out += ["", f"## {title}", "", "| " + " | ".join(cols) + " |",
                "|" + "---|" * len(cols)]
        out += ["| " + " | ".join(c.replace("|", "/") for c in row) + " |" for row in body]
    out += ["", "---", ""] + [f"{x}  " for x in rep["footer"]]
    return "\n".join(out).rstrip() + "\n"


def render_html(rep: dict) -> str:
    e = html.escape
    h = rep["header"]
    out = ["<!doctype html>", '<html lang="en"><head><meta charset="utf-8">',
           f"<title>Janus-M table: {e(h['case'])}</title>",
           "<style>body{font-family:system-ui,sans-serif;margin:16px}table{border-collapse:"
           "collapse;margin:8px 0}td,th{border:1px solid #999;padding:2px 6px;font-size:13px;"
           "text-align:left}footer{margin-top:12px;font-size:13px}</style></head><body>",
           f"<h1>Janus-M table: {e(h['case'])}</h1>", "<dl>"]
    out += [f"<dt>{e(k)}</dt><dd>{e(str(v))}</dd>" for k, v in _header_lines(h)]
    out.append("</dl>")
    for title, (cols, body) in (("Table A: segments (numbers, never flags)", _table_a(
            rep["table_a"])), ("Table B: territories", _table_b(rep["table_b"]))):
        out += [f"<h2>{e(title)}</h2>", "<table><thead><tr>"
                + "".join(f"<th>{e(c)}</th>" for c in cols) + "</tr></thead><tbody>"]
        out += ["<tr>" + "".join(f"<td>{e(c)}</td>" for c in row) + "</tr>" for row in body]
        out.append("</tbody></table>")
    out += ["<footer>"] + [f"<p>{e(x)}</p>" for x in rep["footer"]] + ["</footer>",
                                                                        "</body></html>"]
    return "\n".join(out) + "\n"


def forbidden_hits(text: str, footer) -> list:
    """Forbidden words in ``text`` outside the fixed footer sentences (and 0.99 as a cut)."""
    for line in footer:
        text = text.replace(line, "").replace(html.escape(line), "")
    hits = [p for p in FORBIDDEN if re.search(p, text, re.I)]
    if re.search(r"cut[^\n|]{0,20}0\.99|0\.99[^\n|]{0,20}cut", text, re.I):
        hits.append("0.99 as a cut")
    return hits


__all__ = ["build", "render_markdown", "render_html", "dumps", "phrase", "grade_class",
           "PHRASES", "FORBIDDEN", "forbidden_hits", "ReportError", "territory_grade",
           "grades_from_read_record", "sign_decision"]
