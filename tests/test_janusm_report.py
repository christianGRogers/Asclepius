"""S7 (issue #196): the table writer, on synthetic phantoms only (JA48, Hotel v3 §4.3, Lima v2
§3 item 4c). Golden outputs live in ``tests/fixtures/janusm/report_*``; regenerate them with
``JANUSM_REGEN_GOLDEN=1 pytest tests/test_janusm_report.py`` and review the diff.
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import numpy as np
import pytest

from janusm import features as F
from janusm import guard, sealed_r1
from janusm import reference as R
from janusm import report as P

sys.path.insert(0, str(Path(__file__).parent))
import janusm_synth as Y  # noqa: E402

GOLDEN = Path(__file__).parent / "fixtures/janusm"
REGEN = os.environ.get("JANUSM_REGEN_GOLDEN") == "1"


def _config(**table):
    """A reference config built from a synthetic population around the normal phantom (with
    the phantom's septal-arc values, so the column has percentiles)."""
    lab, ct, aff, cor = Y.heart()
    f0 = F.case_features(lab, ct, aff, cor)
    shape = np.array([f0["rel_thickness"][k] for k in range(1, 17)])
    pop = Y.population(400, shape=shape, median_mm=f0["median_wall_mm"], cv=0.04)
    rng = np.random.default_rng(12)
    for f in pop:
        f["septal_arc"] = {q: {k: float(f0["septal_arc"][q][k] * np.exp(rng.normal(0, 0.05)))
                               for k in F.ARC_SEPTAL} for q in ("wall_mm", "rel_subendo_hu")}
    kw = dict(septal_arc_column=True, halves_note=True, geodesic_shared=False)
    kw.update(table)
    return R.dumps(R.build_config(pop, Y.reads(pop), cases_sha="0" * 64, n_cases=400,
                                  rest_tpr_gate="fail", model="synthetic phantom population",
                                  guard_mm=1.0, **kw))


def _pin(path, text, mp):
    path.write_bytes(text.encode("utf-8"))
    mp.setattr(guard, "REFERENCE_SHA256", hashlib.sha256(text.encode("utf-8")).hexdigest())
    return path


@pytest.fixture(scope="module")
def ref_text():
    return _config()


@pytest.fixture(scope="module")
def ref(tmp_path_factory, ref_text):
    """The config pinned for the module (septal-arc column kept, R8 off)."""
    mp = pytest.MonkeyPatch()
    yield _pin(tmp_path_factory.mktemp("ref") / "reference-r1.json", ref_text, mp)
    mp.undo()


@pytest.fixture(scope="module")
def ref_geodesic():
    """R8 on, septal-arc column dropped."""
    return _config(geodesic_shared=True, septal_arc_column=False)


CASES = {
    "normal": ({}, {"LAD": "1", "LCx": "0", "RCA": "2"}),
    "thinned": ({"thin": 0.4}, {"LAD": "3", "LCx": "0"}),
    "thinned-hypo": ({"thin": 0.4, "subendo_hu": 60.0}, {"LAD": "4A", "RCA": "N"}),
}


@pytest.fixture(scope="module")
def reports(ref):
    out = {}
    for name, (kw, grades) in CASES.items():
        lab, ct, aff, cor = Y.heart(**kw)
        out[name] = P.build(f"Synthetic__{name}", lab, ct, aff, cor, ref, grades,
                            purpose="any", header={"phase": None, "endo_edge_10_90_mm": 1.2,
                                                   "endo_halfmax_offset_mm": 0.1,
                                                   "epi_halfmax_offset_mm": -0.05})
    return out


def _lad(rep):
    return next(r for r in rep["table_b"] if r["territory"] == "LAD")


# ------------------------------------------------------------------------------------ golden
@pytest.mark.parametrize("name", list(CASES))
@pytest.mark.parametrize("fmt", ["md", "html"])
def test_golden_output(reports, name, fmt):
    rep = reports[name]
    text = P.render_markdown(rep) if fmt == "md" else P.render_html(rep)
    path = GOLDEN / f"report_{name}.{fmt}"
    if REGEN:
        path.write_text(text, encoding="utf-8")
    assert text == path.read_text(encoding="utf-8")


def test_byte_identical_reruns(ref, reports):
    lab, ct, aff, cor = Y.heart(**CASES["thinned"][0])
    again = P.build("Synthetic__thinned", lab, ct, aff, cor, ref, CASES["thinned"][1],
                    purpose="any", header={"phase": None, "endo_edge_10_90_mm": 1.2,
                                           "endo_halfmax_offset_mm": 0.1,
                                           "epi_halfmax_offset_mm": -0.05})
    assert P.dumps(again) == P.dumps(reports["thinned"])
    assert P.render_markdown(again) == P.render_markdown(reports["thinned"])
    assert P.render_html(again) == P.render_html(reports["thinned"])


# ------------------------------------------------------------------------------------ flags
def test_null_phantom_has_no_flag(reports):
    for r in reports["normal"]["table_b"]:
        assert not any(s["flag"] for s in r["signs"].values())
        assert r["phrase"] == P.PHRASES["none"]


def test_thinned_lad_is_flagged_only_in_its_territory(reports):
    rep = reports["thinned"]
    assert _lad(rep)["signs"]["thinning"]["flag"]
    for r in rep["table_b"]:
        if r["territory"] != "LAD":
            assert not any(s["flag"] for s in r["signs"].values())


def test_table_a_never_carries_a_flag(reports):
    for rep in reports.values():
        assert len(rep["table_a"]) == 17
        for row in rep["table_a"]:
            assert not any("flag" in k for k in row)
    md = P.render_markdown(reports["thinned-hypo"])
    table_a = md.split("## Table A")[1].split("## Table B")[0]
    assert "FLAG" not in table_a


def test_rest_tpr_blank_with_reason_when_the_gate_fails(reports):
    row = reports["normal"]["table_a"][0]
    assert row["rest_tpr_z"] is None and row["rest_tpr_note"] == "not shown: rest TPR gate fail"


def test_header_fields(reports):
    h = reports["normal"]["header"]
    assert h["phase"] == "phase unrecorded" and "phase-uncertain" in h["thickness_note"]
    for k in ("harness_version", "geometry_version", "reference_sha256", "guard_version",
              "endo_halfmax_offset_mm", "epi_halfmax_offset_mm", "endo_edge_10_90_mm",
              "aha_orientation", "septal_arc_deg", "territory_source", "spacing_mm"):
        assert h[k] is not None, k
    assert "JA44" in h["offset_sign"]
    assert h["halves_note"] is True  # R4-S15
    assert h["layers"]["thirds"] + h["layers"]["halves"] == 17
    assert h["territory_map"] == "patient"
    assert "Layers per segment" in P.render_markdown(reports["normal"])


# ------------------------------------------------------------------------------------ phrases
@pytest.mark.parametrize("pattern,any_flag,grade,want", [
    (True, True, "3", "pattern_significant"),
    (True, True, "4B", "pattern_significant"),
    (True, True, "2", "pattern_other"),
    (True, True, None, "pattern_other"),
    (True, True, "N", "pattern_other"),
    (False, True, "5", "flags"),
    (False, True, None, "flags"),
    (False, False, "4A", "none"),
    (False, False, None, "none"),
])
def test_phrase_table(pattern, any_flag, grade, want):
    assert P.phrase(pattern, any_flag, grade) == P.PHRASES[want]


def test_one_phrase_per_territory_end_to_end(reports):
    assert _lad(reports["thinned-hypo"])["composite"]
    assert _lad(reports["thinned-hypo"])["phrase"] == P.PHRASES["pattern_significant"]
    assert _lad(reports["thinned"])["phrase"] == P.PHRASES["flags"]
    assert _lad(reports["normal"])["phrase"] == P.PHRASES["none"]
    for rep in reports.values():
        for r in rep["table_b"]:
            assert r["phrase"] in P.PHRASES.values()


def test_pattern_without_a_significant_grade(ref):
    lab, ct, aff, cor = Y.heart(thin=0.4, subendo_hu=60.0)
    rep = P.build("Synthetic__x", lab, ct, aff, cor, ref, {"LAD": "2"}, purpose="any")
    assert _lad(rep)["phrase"] == P.PHRASES["pattern_other"]


def test_missing_grade_prints_not_graded(reports):
    rep = reports["thinned-hypo"]
    by = {r["territory"]: r for r in rep["table_b"]}
    assert by["LCx"]["grade"] == "not graded"
    assert by["RCA"]["grade"] == "N" and by["RCA"]["grade_class"] == "not_graded"
    assert by["LAD"]["phrase"] == P.PHRASES["pattern_significant"]


# ------------------------------------------------------------------------------------ words
def test_no_forbidden_word_outside_the_footer(reports):
    for rep in reports.values():
        for text in (P.render_markdown(rep), P.render_html(rep), P.dumps(rep)):
            assert P.forbidden_hits(text, rep["footer"]) == []
    assert P.forbidden_hits("a scar here", []) and P.forbidden_hits("cut 0.99", [])


def test_footer(reports):
    f = reports["normal"]["footer"]
    assert f[0] == "Research output, not validated: no scar or perfusion reference."
    assert f[-1] == "Population: this population, phase-uncertain."
    assert f[1].startswith("Thinning: a territory is flagged only when")


# ------------------------------------------------------------------------------------ refusals
def test_changed_reference_config_is_refused(ref, tmp_path):
    bad = tmp_path / "reference-r1.json"
    bad.write_text(ref.read_text().replace('"n_cases": 400', '"n_cases": 401'))
    lab, ct, aff, cor = Y.heart()
    with pytest.raises(R.ReferenceError, match="pinned"):
        P.build("Synthetic__normal", lab, ct, aff, cor, bad, purpose="any")


def test_unpinned_reference_is_refused(ref, monkeypatch):
    monkeypatch.setattr(guard, "REFERENCE_SHA256", None)
    with pytest.raises(R.ReferenceError, match="not pinned"):
        P.build("Synthetic__normal", None, None, None, None, ref, purpose="any")


@pytest.mark.parametrize("purpose", ["any", "decision_scoring"])
def test_guard_hit_refuses_before_any_read(tmp_path, purpose):
    """A Janus-M seal case outside seal scoring: refused before the reference or any array is
    touched (both are invalid here, so any later step would raise something else)."""
    seal = sorted(sealed_r1.load().seal)[0]
    with pytest.raises(guard.HeldOutError):
        P.build(f"ImageCAS-X__{seal}", None, None, None, None, tmp_path / "nope.json",
                purpose=purpose)


# ------------------------------------------------------------------------------------ R4-S8
def test_the_gate_and_the_report_produce_the_same_floor_for_the_same_e(monkeypatch):
    """One floor function (JA64): gate() at the population's E and the report at the patient's
    E call ``rc_floor_mm`` and agree when the two E are equal."""
    calls = []
    real = R.rc_floor_mm

    def spy(rc, t, e):
        calls.append((t, e))
        return real(rc, t, e)

    monkeypatch.setattr(R, "rc_floor_mm", spy)
    monkeypatch.setattr(R.calibrate, "detectable_depth", lambda *a, **k: {
        "depth": 0.3, "sens_range": [0.8, 0.8], "false_flag": 0.0})
    rc = {"status": "computed", "scale": "relative",
          "territory": {t: {"rc": 0.12} for t in R.TERRITORIES}}
    blk = {"cut": -2.0, "cv_n": 0.1, "shape": [1.0] * 16, "median_level": 4.2, "status": "flag"}
    g = R.gate("thinning", {"thinning": blk}, {"thinning": {"rc": rc}})
    state = {"D": {t: 0.4 for t in R.TERRITORIES}, "E": {t: 4.2 for t in R.TERRITORIES},
             "territory_rule_c": {t: True for t in R.TERRITORIES}, "map": "patient"}
    cell = P.sign_decision("thinning", state, "LAD", {"rc": {"thinning": rc}, "thinning": blk})
    assert g["floor_mm"]["LAD"] == pytest.approx(cell["floor"]) == pytest.approx(0.12 * 4.2)
    assert ("LAD", 4.2) in calls and len([c for c in calls if c == ("LAD", 4.2)]) >= 2
    assert cell["flag"] is False  # 0.4 <= 0.504


# ------------------------------------------------------------------------------------ R4-S15
def test_rule_c_and_gate_pass_with_d_at_most_rc_is_a_number():
    rc = {"status": "computed", "scale": "difference",
          "territory": {t: {"rc": 0.8} for t in R.TERRITORIES}}
    cfg = {"rc": {"thinning": rc}, "thinning": {"status": "flag"}}
    for d, flag in ((0.8, False), (0.81, True)):
        state = {"D": {"LAD": d}, "E": {"LAD": 5.0}, "territory_rule_c": {"LAD": True}}
        cell = P.sign_decision("thinning", state, "LAD", cfg)
        assert cell["flag"] is flag and cell["shown"] == ("flag" if flag else "number")
        assert cell["value"] == d


# ------------------------------------------------------------------------------------ R4-S11
@pytest.mark.parametrize("attr,mod", [("GEOMETRY_VERSION", "G"), ("FEATURES_VERSION", "F")])
def test_a_version_mismatch_is_refused(ref, monkeypatch, attr, mod):
    from janusm import geometry as G

    monkeypatch.setattr({"G": G, "F": F}[mod], attr, "9.9.9")
    lab, ct, aff, cor = Y.heart()
    with pytest.raises(P.ReportError, match="running"):
        P.build("Synthetic__normal", lab, ct, aff, cor, ref, purpose="any")


# ------------------------------------------------------------------------------------ R4-S12
def test_one_segment_is_shared_only_with_r8_on(ref_text, ref_geodesic, tmp_path, monkeypatch):
    """A phantom whose segment 1 has a different geodesic majority: "shared" only when the
    config's R8 verdict is on."""
    real = F.case_features

    def moved(*a, **k):
        f = real(*a, **k)
        f["segment_territory_geodesic"] = {**f["segment_territory_geodesic"], 1: "LCx"}
        return f

    monkeypatch.setattr(F, "case_features", moved)
    lab, ct, aff, cor = Y.heart()
    out = {}
    for name, text in (("off", ref_text), ("on", ref_geodesic)):
        path = _pin(tmp_path / f"{name}.json", text, monkeypatch)
        out[name] = P.build("Synthetic__normal", lab, ct, aff, cor, path, purpose="any")
    shared = {n: {r["segment"] for r in out[n]["table_a"] if r["shared"]} for n in out}
    assert shared["on"] - shared["off"] == {1}  # only the moved segment changes
    for name, want in (("off", False), ("on", True)):
        rep = out[name]
        assert rep["table_a"][0]["shared"] is want
        assert (1 in _lad(rep)["shared_segments"]) is want
        assert (1 in _lad(rep)["segments"]) is not want
    assert "geodesic" in out["on"]["header"]["shared_rule"]


# ------------------------------------------------------------------------------------ R4-S13
def test_lm_feeds_lad_and_lcx():
    g = {"LM": "4B", "LAD": "0", "LCx": "0", "RCA": "0"}
    assert P.territory_grade(g, "LAD") == ("4B", "LM 4B")
    assert P.territory_grade(g, "LCx") == ("4B", "LM 4B")
    assert P.territory_grade(g, "RCA") == ("0", None)
    assert [P.grade_class(P.territory_grade(g, t)[0]) for t in ("LAD", "LCx", "RCA")] == \
        ["significant", "significant", "not_significant"]
    assert P.territory_grade({"LM": "2", "LAD": "3"}, "LAD") == ("3", None)
    assert P.territory_grade({"LM": "1", "LAD": "N"}, "LAD") == ("1", "LM 1")
    assert P.territory_grade({"LM": "N", "LAD": "N"}, "LAD") == ("N", None)
    assert P.territory_grade({"LM": "N"}, "LAD") == ("N", "LM N")
    assert P.territory_grade({}, "LAD") == (None, None)


def test_lm_grade_in_the_table(ref):
    lab, ct, aff, cor = Y.heart()
    rep = P.build("Synthetic__normal", lab, ct, aff, cor, ref,
                  {"LM": "4B", "LAD": "0", "LCx": "0", "RCA": "0"}, purpose="any")
    by = {r["territory"]: r for r in rep["table_b"]}
    assert by["LAD"]["grade"] == by["LCx"]["grade"] == "4B"
    assert by["LAD"]["grade_source"] == "LM 4B" and by["RCA"]["grade_source"] is None
    assert by["LAD"]["grade_class"] == by["LCx"]["grade_class"] == "significant"
    assert by["RCA"]["grade_class"] == "not_significant"
    assert "| 4B (LM 4B) |" in P.render_markdown(rep)


def test_grades_round_trip_from_an_export_record(ref):
    """A read form as the client submits it and the export writes it, into Table B."""
    from janusm_reads.protocol import ReadSubmission

    sub = ReadSubmission(checksum="0" * 64, size_bytes=1,
                         cadrads={"LM": "2", "LAD": "3", "LCx": "0", "RCA": "N"},
                         lesion_points={"LAD": [1.0, 2.0, 3.0]})
    wire = ReadSubmission.from_dict(sub.to_dict())
    rec = {"reader": "r", "seeded": True, "blank": False, "third": False,  # export.readRecord
           "cadrads": dict(wire.cadrads), "lesionPoints": dict(wire.lesion_points),
           "border_protocol": 1}
    grades = P.grades_from_read_record(rec)
    assert grades == {"LM": "2", "LAD": "3", "LCx": "0", "RCA": "N",
                      "lesion_point": {"LAD": [1.0, 2.0, 3.0]}}
    lab, ct, aff, cor = Y.heart()
    rep = P.build("Synthetic__normal", lab, ct, aff, cor, ref, grades, purpose="any")
    by = {r["territory"]: r for r in rep["table_b"]}
    assert (by["LAD"]["grade"], by["LCx"]["grade"], by["RCA"]["grade"]) == ("3", "2", "N")
    assert by["LCx"]["grade_source"] == "LM 2"
    assert by["LAD"]["mass_distal_note"] == P.DISTAL_NOTE
    assert by["LCx"]["mass_distal_note"] is None and by["RCA"]["mass_distal_note"] is None


def test_distal_mass_label(ref):
    lab, ct, aff, cor = Y.heart()
    rep = P.build("Synthetic__normal", lab, ct, aff, cor, ref,
                  {"LM": "4B", "lesion_point": {"LM": [0.0, 0.0, 0.0]}}, purpose="any")
    by = {r["territory"]: r for r in rep["table_b"]}
    assert by["LAD"]["mass_distal_note"] == by["LCx"]["mass_distal_note"] == \
        "distal mass: not computed (report v1)"
    assert by["RCA"]["mass_distal_note"] is None and by["LAD"]["mass_distal_g"] is None
    assert P.render_markdown(rep).count("distal mass: not computed (report v1)") == 2


# ------------------------------------------------------------------------------------ R4-S14
def test_septal_arc_column_filled_on_2_3_8_9(reports):
    for rep in reports.values():
        for row in rep["table_a"]:
            v = row["septal_arc_value"]
            if row["segment"] in (2, 3, 8, 9):
                assert v["thickness_mm"] is not None and v["thickness_pctl"] is not None
                assert v["rel_subendo_hu"] is not None
            else:
                assert v is None
    md = P.render_markdown(reports["normal"])
    assert "Septal arc: thickness mm; rel. subendo HU" in md
    row1 = next(x for x in md.splitlines() if x.startswith("| 1 "))
    assert row1.rstrip(" |").endswith("—")


def test_septal_arc_column_omitted_when_r7_drops_it(ref_geodesic, tmp_path, monkeypatch):
    path = _pin(tmp_path / "drop.json", ref_geodesic, monkeypatch)
    lab, ct, aff, cor = Y.heart()
    rep = P.build("Synthetic__normal", lab, ct, aff, cor, path, purpose="any")
    assert all("septal_arc_value" not in r for r in rep["table_a"])
    assert "Septal arc:" not in P.render_markdown(rep)


# ------------------------------------------------------------------------------------ R5-S5
def test_r5s5_a_report_without_segment_territory_falls_back_and_says_so(ref, monkeypatch):
    """R5-S5 (JA75, JA63): ``segment_territory`` dropped -> ``territory_map == "aha_fallback"``,
    and the fall-back note is in the header and the markdown. With the map, neither."""
    lab, ct, aff, cor = Y.heart()
    kept = P.build("Synthetic__normal", lab, ct, aff, cor, ref, purpose="any")
    real = F.case_features

    def dropped(*a, **k):
        f = real(*a, **k)
        f.pop("segment_territory")
        return f

    monkeypatch.setattr(F, "case_features", dropped)
    rep = P.build("Synthetic__normal", lab, ct, aff, cor, ref, purpose="any")
    h = rep["header"]
    note = "D on the AHA default map: no patient-specific map (fall-back, JA63)"
    assert h["territory_map"] == "aha_fallback" and h["territory_map_note"] == note
    assert f"- **Territory map:** {note}" in P.render_markdown(rep)
    assert note in P.render_html(rep)
    for row in rep["table_b"]:
        for sign in ("thinning", "hypoattenuation"):
            assert row["signs"][sign]["map"] == "aha_fallback"
    assert kept["header"]["territory_map"] == "patient"
    assert "territory_map_note" not in kept["header"]
    assert "- **Territory map:** patient-specific" in P.render_markdown(kept)
    assert note not in P.render_markdown(kept)


# ------------------------------------------------------------------------ R5-S6: halves_note
def test_r5s6_halves_note_false(tmp_path, monkeypatch):
    """R5-S6: ``halves_note`` tested False as well as True (``test_header_fields``): False
    leaves the "Layers per segment" line out."""
    path = _pin(tmp_path / "nohalves.json", _config(halves_note=False), monkeypatch)
    lab, ct, aff, cor = Y.heart()
    rep = P.build("Synthetic__normal", lab, ct, aff, cor, path, purpose="any")
    assert rep["header"]["halves_note"] is False
    md = P.render_markdown(rep)
    assert "Layers per segment" not in md and "Layers per segment" not in P.render_html(rep)
    assert "Territory map" in md  # the rest of the header is printed


# ------------------------------------------------------------------------------- R5-S6: S12
def test_r5s6_s12_a_real_geodesic_majority_differs_on_one_segment_shared_only_with_r8_on(
        ref_text, ref_geodesic, tmp_path, monkeypatch):
    """S12: ``janusm_synth.heart_r8``'s real ``geometry.territories(method="geodesic")``
    majority differs from the Euclidean one on segment 1 only (no monkeypatch); segment 1 is
    "shared" only with R8 on."""
    lab, ct, aff, cor = Y.heart_r8()
    f = F.case_features(lab, ct, aff, cor)
    e, g = f["segment_territory"], f["segment_territory_geodesic"]
    assert {k for k in e if e[k] != g[k]} == {1}
    assert (e[1], g[1]) == ("LCx", "LAD")
    assert f["segment_territory_share"][1] >= F.SHARED_BELOW  # not "shared" by its share
    plain = F.case_features(*Y.heart_r8(branch=False))         # the branch is what moves it
    assert all(plain["segment_territory"][k] == plain["segment_territory_geodesic"][k]
               for k in plain["segment_territory"])
    out = {}
    for name, text in (("off", ref_text), ("on", ref_geodesic)):
        path = _pin(tmp_path / f"{name}.json", text, monkeypatch)
        out[name] = P.build("Synthetic__r8", lab, ct, aff, cor, path, purpose="any")
    shared = {n: {r["segment"] for r in out[n]["table_a"] if r["shared"]} for n in out}
    assert shared["on"] - shared["off"] == {1}
    assert out["off"]["table_a"][0]["shared"] is False
    assert out["on"]["table_a"][0]["shared"] is True
    lcx = {n: next(r for r in out[n]["table_b"] if r["territory"] == "LCx") for n in out}
    assert 1 in lcx["off"]["segments"] and 1 in lcx["on"]["shared_segments"]


# ------------------------------------------------------------------------------- R5-S6: S13
def test_r5s6_s13_grades_round_trip_through_the_export_mapping(ref):
    """S13: a read stored as ``rest.submit`` stores it, written by the export's own mapping
    (``janusm_reads.readform.read_form``, which ``export.readRecord`` calls), into Table B."""
    from janusm_reads import readform
    from janusm_reads.protocol import ReadSubmission

    sub = ReadSubmission.from_dict(ReadSubmission(
        checksum="0" * 64, size_bytes=1, cadrads={"LM": "2", "LAD": "3", "LCx": "0", "RCA": "N"},
        lesion_points={"LAD": [1.0, 2.0, 3.0]}).to_dict())
    stored = {"userId": "u", "seeded": True, "border_protocol": 1,       # rest.submit's fields
              "cadrads": dict(sub.cadrads), "lesionPoints": dict(sub.lesion_points)}
    rec = {"reader": "u", **readform.read_form(stored)}                 # export.readRecord
    grades = P.grades_from_read_record(rec)
    assert grades == {"LM": "2", "LAD": "3", "LCx": "0", "RCA": "N",
                      "lesion_point": {"LAD": [1.0, 2.0, 3.0]}}
    assert grades == readform.reader_grades(stored)
    lab, ct, aff, cor = Y.heart()
    rep = P.build("Synthetic__normal", lab, ct, aff, cor, ref, grades, purpose="any")
    by = {r["territory"]: r for r in rep["table_b"]}
    assert (by["LAD"]["grade"], by["LCx"]["grade"], by["RCA"]["grade"]) == ("3", "2", "N")
    assert by["LCx"]["grade_source"] == "LM 2"
    assert by["LAD"]["mass_distal_note"] == P.DISTAL_NOTE


def test_r5s6_s13_the_export_writes_the_form_with_readform():
    """S13: ``export.readRecord`` takes its form fields from ``readform.read_form`` and writes
    no ``cadrads`` / ``lesionPoints`` of its own (read from the source: the export needs
    girder, which this job does not install)."""
    import ast

    src = (Path(__file__).parents[1] / "server/girder_janusm/export.py").read_text("utf-8")
    fn = next(n for n in ast.walk(ast.parse(src))
              if isinstance(n, ast.FunctionDef) and n.name == "readRecord")
    ret = next(n for n in ast.walk(fn) if isinstance(n, ast.Return))
    assert isinstance(ret.value, ast.Dict)
    keys = {k.value for k in ret.value.keys if isinstance(k, ast.Constant)}
    assert not keys & {"cadrads", "lesionPoints"}
    spread = [v for k, v in zip(ret.value.keys, ret.value.values) if k is None]
    assert [ast.unparse(v) for v in spread] == ["readform.read_form(read)"]
