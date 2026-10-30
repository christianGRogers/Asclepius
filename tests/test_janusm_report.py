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


@pytest.fixture(scope="module")
def ref(tmp_path_factory):
    """A reference config built from a synthetic population around the normal phantom, pinned
    for the module."""
    lab, ct, aff, cor = Y.heart()
    f0 = F.case_features(lab, ct, aff, cor)
    shape = np.array([f0["rel_thickness"][k] for k in range(1, 17)])
    pop = Y.population(400, shape=shape, median_mm=f0["median_wall_mm"], cv=0.04)
    cfg = R.build_config(pop, Y.reads(pop), cases_sha="0" * 64, n_cases=400,
                         rest_tpr_gate="fail", septal_arc_column=False, halves_note=True,
                         model="synthetic phantom population", guard_mm=1.0)
    text = R.dumps(cfg)
    p = tmp_path_factory.mktemp("ref") / "reference-r1.json"
    p.write_text(text)
    mp = pytest.MonkeyPatch()
    mp.setattr(guard, "REFERENCE_SHA256", hashlib.sha256(text.encode()).hexdigest())
    yield p
    mp.undo()


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
