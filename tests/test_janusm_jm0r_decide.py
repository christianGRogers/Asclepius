"""The JA43 decision script (issue #193) on synthetic aggregate inputs only.

Every input here is a made-up aggregate (no case id, no image). Each R0-R10 branch is driven from
one passing baseline by changing the keys its rule reads.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "experiments/JanusM/fir/jm0r_decide.py"


@pytest.fixture(scope="module")
def dec():
    spec = importlib.util.spec_from_file_location("jm0r_decide", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["jm0r_decide"] = mod
    spec.loader.exec_module(mod)
    return mod


SHAPE = [1.0 + 0.01 * k for k in range(16)]


def base():
    """Every JA44 key, with values on which every rule takes its plain branch."""
    grid = {f"{c},{v}": 0.2 for c in (0, -30, -50, -100) for v in (5, 20, 50)}
    grid["-100,50"] = 0.02
    return {"n_cases": 40, "n_usable": 40,
            "aha_frame_fail_share": 0.025, "aha_orientation_fail_share": 0.0,
            "thickness_median_mm": 6.1, "halves_segment_share": 0.05,
            "endo_halfmax_offset_mm_median": 0.1, "epi_halfmax_offset_mm_median": -0.1,
            "endo_edge_10_90_mm_median": 1.2,
            "tpr_guard1_freewall_median": 1.04, "tpr_guard_adaptive_freewall_median": 1.03,
            "tpr_guard_adaptive_freewall_patient_median": 1.03,
            "tpr_guard_adaptive_share_below_0p99": 0.2,
            "fat_grid": grid, "fat_patient_rule_share": 0.03,
            "septal_arc_mass_changed_median": 0.04, "geodesic_segments_changed_share": 0.05,
            "et_laplace_third_agreement_median": 0.92,
            "cv_n": 0.088, "cv_n_robust_log": 0.07, "segment_shape": SHAPE,
            "rel_subendo_hu_sd": 0.05, "script_version": "2"}


def fake_depth(value):
    calls = []

    def fn(cv_n, shape, rc_terr_mm, *, sig_m, seed, measured_median_mm):
        calls.append((cv_n, len(shape), rc_terr_mm, sig_m, seed, measured_median_mm))
        return {"depth": value, "sens_range": None, "false_flag": None}

    fn.calls = calls
    return fn


def run(dec, depth=0.35, **changes):
    x = base()
    for k, v in changes.items():
        if v is _DROP:
            x.pop(k)
        else:
            x[k] = v
    return {r["rule"]: r for r in dec.decide(x, depth_fn=fake_depth(depth))}


_DROP = object()


def test_the_base_case_is_fully_decidable(dec):
    res = dec.decide(base(), depth_fn=fake_depth(0.35))
    assert [r["rule"] for r in res] == [f"R{i}" for i in range(11)]
    assert all(not r["missing"] and r["applied"] for r in res)
    assert not [ln for ln in dec.lines(res) if "NOT DECIDABLE" in ln]
    assert set(base()) == set(dec.KEYS)


# ------------------------------------------------------------------------------- R0
@pytest.mark.parametrize("n, proceeds", [(40, True), (36, True), (35, False), (23, False)])
def test_r0_usable_cases(dec, n, proceeds):
    res = run(dec, n_usable=n)
    assert (res["R0"]["outcome"] == "proceed") is proceeds
    later = [res[f"R{i}"] for i in range(1, 11)]
    assert all(r["applied"] is proceeds for r in later)
    if not proceeds:
        assert res["R0"]["outcome"].startswith("STOP")
        assert all(r["outcome"].startswith("NOT APPLIED (R0 stopped)") for r in later)


def test_r0_stops_on_23_cases_and_prints_it(dec):
    lines = dec.lines(dec.decide({**base(), "n_usable": 23}, depth_fn=fake_depth(0.3)))
    assert lines[0].startswith("R0 [JA43 R0") and "STOP" in lines[0]
    assert all("NOT APPLIED" in ln for ln in lines[1:] if ln.startswith("R"))


def test_r0_missing_stops(dec):
    res = run(dec, n_usable=_DROP)
    assert res["R0"]["missing"] == ["n_usable"] and res["R0"]["outcome"].startswith("STOP")


# ------------------------------------------------------------------------------- R1
@pytest.mark.parametrize("frame, orient, fix", [(0.025, 0.0, False), (0.10, 0.10, False),
                                                (0.15, 0.0, True), (0.0, 0.125, True)])
def test_r1_aha_frame(dec, frame, orient, fix):
    r = run(dec, aha_frame_fail_share=frame, aha_orientation_fail_share=orient)["R1"]
    assert r["frame_fix"] is fix
    assert "'AHA frame failed'" in r["outcome"]
    assert ("role:swe frame fix" in r["outcome"]) is fix
    if fix:
        assert "reads proceed" in r["outcome"]


def test_r1_missing_takes_the_fix(dec):
    r = run(dec, aha_orientation_fail_share=_DROP)["R1"]
    assert r["missing"] == ["aha_orientation_fail_share"] and r["frame_fix"] is True


# ------------------------------------------------------------------------------- R2
@pytest.mark.parametrize("share, note", [(0.05, False), (0.25, False), (0.3, True)])
def test_r2_halves(dec, share, note):
    r = run(dec, halves_segment_share=share)["R2"]
    assert r["header_note"] is note
    assert "never halves everywhere" in r["outcome"]


def test_r2_missing_states_the_layer_count(dec):
    r = run(dec, halves_segment_share=_DROP)["R2"]
    assert r["missing"] and r["header_note"] is True


# ------------------------------------------------------------------------------- R3
@pytest.mark.parametrize("t, holds", [(6.1, True), (4.2, True), (8.0, True), (4.1, False),
                                      (9.0, False)])
def test_r3_thickness_definition(dec, t, holds):
    r = run(dec, thickness_median_mm=t)["R3"]
    assert r["f3_holds"] is holds
    assert ("no thinning flag ships" in r["outcome"]) is (not holds)


def test_r3_missing_takes_the_hand_measurement(dec):
    r = run(dec, thickness_median_mm=_DROP)["R3"]
    assert r["missing"] and r["f3_holds"] is False


# ------------------------------------------------------------------------------- R4
@pytest.mark.parametrize("endo, epi, reads, tpr, guard", [
    (0.1, -0.1, False, False, False),
    (0.35, 0.0, False, True, True),       # |endo| > 0.25 and > 0.3: TPR snap; guard printed
    (0.25, 0.5, False, False, True),      # thresholds are strict
    (0.6, 0.0, True, True, True),
    (0.0, -0.6, True, False, True),       # either border, either sign
])
def test_r4_seed_offsets(dec, endo, epi, reads, tpr, guard):
    r = run(dec, endo_halfmax_offset_mm_median=endo, epi_halfmax_offset_mm_median=epi)["R4"]
    assert r["snap_before_reads"] is reads
    assert r["snap_for_tpr"] is tpr
    assert r["seed_expected_to_fail_bias_guard"] is guard
    assert ("snap tool (S8) runs on the seeds" in r["outcome"]) is reads
    assert "printed, not acted on" in r["outcome"]


def test_r4_missing(dec):
    r = run(dec, epi_halfmax_offset_mm_median=_DROP)["R4"]
    assert r["missing"] == ["epi_halfmax_offset_mm_median"]
    assert r["snap_before_reads"] is None and r["snap_for_tpr"] is True


# ------------------------------------------------------------------------------- R5
@pytest.mark.parametrize("changes, expect", [
    ({}, "shown per segment as a patient-relative z-score"),
    ({"endo_edge_10_90_mm_median": 2.5}, "not computed (edge > 2 mm)"),
    ({"endo_edge_10_90_mm_median": 1.8}, "research export only"),
    ({"tpr_guard_adaptive_freewall_median": 1.2}, "research export only"),
    ({"tpr_guard_adaptive_freewall_median": 0.98}, "research export only"),
    ({"endo_halfmax_offset_mm_median": -0.4}, "shown after snapping"),
])
def test_r5_rest_tpr(dec, changes, expect):
    r = run(dec, **changes)["R5"]
    assert r["outcome"].startswith(expect) and not r["missing"]


def test_r5_missing_tpr_is_not_shown(dec):
    r = run(dec, tpr_guard_adaptive_freewall_median=_DROP, endo_edge_10_90_mm_median=1.4)["R5"]
    assert r["outcome"] == "not shown"
    assert r["missing"] == ["tpr_guard_adaptive_freewall_median"]


def test_r5_missing_edge_is_not_shown(dec):
    r = run(dec, endo_edge_10_90_mm_median=_DROP)["R5"]
    assert r["outcome"] == "not shown" and r["missing"] == ["endo_edge_10_90_mm_median"]


def test_r5_missing_offset_is_not_shown(dec):
    r = run(dec, endo_halfmax_offset_mm_median=_DROP)["R5"]
    assert r["outcome"] == "not shown" and r["missing"] == ["endo_halfmax_offset_mm_median"]


def test_r5_the_1mm_guard_stands_in_only_where_it_is_the_adaptive_band(dec):
    # edge 1.0 mm: FWHM 0.92 mm, so max(1 mm, FWHM) = 1 mm
    r = run(dec, tpr_guard_adaptive_freewall_median=_DROP, endo_edge_10_90_mm_median=1.0)["R5"]
    assert r["tpr_from"] == "tpr_guard1_freewall_median" and r["outcome"].startswith("shown")
    # edge 1.4 mm: FWHM 1.28 mm, a wider band than 1 mm: no stand-in
    r = run(dec, tpr_guard_adaptive_freewall_median=_DROP, endo_edge_10_90_mm_median=1.4)["R5"]
    assert r["outcome"] == "not shown"


# ------------------------------------------------------------------------------- R6
def _grid(passing=(), share=0.2):
    g = {f"{c},{v}": share for c in (0, -30, -50, -100) for v in (5, 20, 50)}
    for k in passing:
        g[k] = 0.01
    return g


@pytest.mark.parametrize("passing, cut", [
    (("0,5", "-100,50"), (0, 5)),
    (("-50,20", "-50,5", "-100,5"), (-50, 5)),   # least strict c first, then V within it
    (("-30,50", "-50,5"), (-30, 50)),
])
def test_r6_the_least_strict_grid_cell(dec, passing, cut):
    r = run(dec, fat_grid=_grid(passing))["R6"]
    assert (r["cut"]["c_hu"], r["cut"]["v_mm3"]) == cut
    assert "Provisional" in r["outcome"]


def test_r6_patient_rule_then_number_only(dec):
    r = run(dec, fat_grid=_grid(), fat_patient_rule_share=0.04)["R6"]
    assert r["cut"]["rule"] == "hotel_patient"
    r = run(dec, fat_grid=_grid(), fat_patient_rule_share=0.08)["R6"]
    assert r["cut"] is None and "number only" in r["outcome"] and not r["missing"]
    r = run(dec, fat_grid=_grid(), fat_patient_rule_share=_DROP)["R6"]
    assert r["cut"] is None and r["missing"] == ["fat_patient_rule_share"]


def test_r6_missing_grid_or_cell_is_never_defaulted(dec):
    r = run(dec, fat_grid=_DROP)["R6"]
    assert r["missing"] == ["fat_grid"] and r["cut"] is None and "number only" in r["outcome"]
    g = _grid(("-50,5",))
    del g["-30,20"]  # an earlier, less strict cell is unknown: no pick
    r = run(dec, fat_grid=g)["R6"]
    assert r["missing"] == ["fat_grid[-30,20]"] and r["cut"] is None


# ------------------------------------------------------------------------------- R7, R8
@pytest.mark.parametrize("share, kept", [(0.04, False), (0.10, True), (0.2, True)])
def test_r7_septal_arc_column(dec, share, kept):
    assert run(dec, septal_arc_mass_changed_median=share)["R7"]["column_kept"] is kept


def test_r7_missing_keeps_the_column(dec):
    r = run(dec, septal_arc_mass_changed_median=_DROP)["R7"]
    assert r["missing"] and r["column_kept"] is True


@pytest.mark.parametrize("share, shared", [(0.05, False), (0.10, True), (0.3, True)])
def test_r8_geodesic(dec, share, shared):
    r = run(dec, geodesic_segments_changed_share=share)["R8"]
    assert r["shared_marking"] is shared
    assert r["outcome"].startswith("Euclidean is primary")


def test_r8_missing(dec):
    r = run(dec, geodesic_segments_changed_share=_DROP)["R8"]
    assert r["missing"] and r["shared_marking"] is False


# ------------------------------------------------------------------------------- R9, R10
def test_r9_calls_detectable_depth_with_cv_n_shape_the_f1_floor_and_the_measured_wall(dec):
    """R4-S2 (JA60): a recording depth_fn receives JM-0R's thickness_median_mm as the measured
    wall."""
    fn = fake_depth(0.35)
    r = {x["rule"]: x for x in dec.decide(base(), depth_fn=fn)}["R9"]
    assert fn.calls == [(0.088, 16, 1.0, 0.0, dec.DEPTH_SEED, 6.1)]
    assert r["depth"] == 0.35 and "35 %" in r["outcome"] and "wall 6.1 mm" in r["outcome"]
    assert "nothing is loosened" not in r["outcome"]
    assert r["inputs"]["cv_n_robust_log"] == 0.07  # reported beside it, never used
    assert r["inputs"]["thickness_median_mm"] == 6.1
    assert r["numbers_only"] is False and r["footer"] is None
    assert dec.R3_NOTE not in r["outcome"]
    fn = fake_depth(0.4)
    dec.decide({**base(), "thickness_median_mm": 5.2}, depth_fn=fn)
    assert fn.calls[0][-1] == 5.2


def test_r9_default_is_the_shipped_s3(dec):
    from janusm.calibrate import detectable_depth

    assert dec.detectable_depth is detectable_depth
    assert dec.DECIDE_VERSION == "2"


def test_r9_above_0p40_says_so_and_none_is_not_demonstrated(dec):
    assert "nothing is loosened" in run(dec, depth=0.45)["R9"]["outcome"]
    r = run(dec, depth=None)["R9"]
    assert "not demonstrated" in r["outcome"] and r["numbers_only"] is True


def test_r9_provisional_print_reads_45_percent(dec):
    """R4-S2 (JA60): the provisional print is 45 %, labelled as the placeholder."""
    assert dec.PROVISIONAL_DEPTH == 0.45
    r = run(dec, segment_shape=_DROP)["R9"]
    assert "provisional 45 %" in r["outcome"] and "35 %" not in r["outcome"]
    assert dec.PROVISIONAL_FOOTER in r["outcome"]
    assert r["footer"] == "provisional (JA40), not computed on this population"
    assert r["provisional_depth"] == 0.45


def test_r9_missing_median_is_not_decidable(dec):
    """R4-S2 (JA60): no thickness_median_mm -> NOT DECIDABLE, S3 is not called, and the page
    prints the provisional 45 %."""
    fn = fake_depth(0.35)
    x = base()
    del x["thickness_median_mm"]
    res = dec.decide(x, depth_fn=fn)
    r = {y["rule"]: y for y in res}["R9"]
    assert fn.calls == []
    assert r["missing"] == ["thickness_median_mm"] and r["depth"] is None
    assert "provisional 45 %" in r["outcome"] and r["numbers_only"] is True
    assert "    NOT DECIDABLE: thickness_median_mm" in dec.lines(res)


def test_r9_s3_refusal_prints_not_decidable(dec):
    """R4-S2 (JA60): cv_n = 0 (S3 refuses) prints ``NOT DECIDABLE: cv_n (S3 refused: ...)``; the
    thinning sign shows numbers only and the footer is labelled provisional."""
    res = dec.decide({**base(), "cv_n": 0.0})  # the shipped S3 refuses: no normal variation
    r = {y["rule"]: y for y in res}["R9"]
    assert len(r["missing"]) == 1
    assert r["missing"][0].startswith("cv_n (S3 refused: ") and "no normal variation" in \
        r["missing"][0]
    nd = [ln for ln in dec.lines(res) if "NOT DECIDABLE" in ln]
    assert nd == [f"    NOT DECIDABLE: {r['missing'][0]}"]
    assert r["depth"] is None and r["numbers_only"] is True
    assert r["footer"] == dec.PROVISIONAL_FOOTER and "provisional 45 %" in r["outcome"]
    assert "numbers only until JM-0R is rerun" in r["outcome"]


def test_r9_r3_failure_adds_the_note(dec):
    """R4-S2 (JA60): R3 fails -> R9 still computes, and its line says the definition is
    unaligned."""
    for t in (9.668, 3.9):
        fn = fake_depth(0.35)
        res = {y["rule"]: y for y in dec.decide({**base(), "thickness_median_mm": t},
                                                depth_fn=fn)}
        assert res["R3"]["f3_holds"] is False
        assert fn.calls and fn.calls[0][-1] == t
        assert res["R9"]["depth"] == 0.35 and not res["R9"]["missing"]
        assert res["R9"]["outcome"].endswith(dec.R3_NOTE)
        assert "unaligned thickness definition" in res["R9"]["outcome"]


def test_r9_missing_inputs(dec):
    r = run(dec, segment_shape=_DROP)["R9"]
    assert r["missing"] == ["segment_shape"] and r["depth"] is None


def test_r10_reported_only(dec):
    assert run(dec)["R10"]["outcome"] == "reported only"
    assert run(dec, et_laplace_third_agreement_median=_DROP)["R10"]["missing"]


# ------------------------------------------------------------------------------- mappers
def test_from_jm0r_reads_the_block_or_the_bare_block(dec):
    x = base()
    assert dec.from_jm0r({"provenance": {}, "decision_inputs": x}) == x
    assert dec.from_jm0r(x) == x
    assert dec.from_jm0r({"decision_inputs": {"n_usable": 40}})["cv_n"] is None


def test_hotel_fallback_negates_the_endocardium(dec):
    h = {"aggregate": {"n_cases": 40, "n_usable": 39,
                       "endo_halfmax_offset_mm_q25_50_75_n": [0.1, 0.3, 0.5, 39],
                       "epi_halfmax_offset_mm_q25_50_75_n": [0.0, 0.2, 0.4, 39],
                       "endo_10_90_mm_q": [1.0, 1.3, 1.6, 39],
                       "tpr_guard1.0": {"free_wall_segments_q": [0.9, 1.02, 1.1, 300]}}}
    x = dec.from_hotel_r2(h)
    assert x["endo_halfmax_offset_mm_median"] == -0.3
    assert x["epi_halfmax_offset_mm_median"] == 0.2
    assert x["endo_edge_10_90_mm_median"] == 1.3
    assert x["tpr_guard1_freewall_median"] == 1.02
    assert "tpr_guard_adaptive_freewall_median" not in x


def test_lima_fallback(dec):
    s = {"n_cases": 40, "n_frame_ok": 38, "orientation_ok": {"fixed": 37},
         "median_thickness_mm": {"p50": 6.0}, "share_segments_needing_halves": 0.1,
         "halfmax_offset_endo_mm_case_medians": {"p50": 0.2, "n": 38},
         "halfmax_offset_epi_mm_case_medians": {"n": 0},
         "share_hearts_with_fat_cluster": {"0": {"5": 0.3}, "-30": {"5": 0.04}},
         "myocardium_relabelled_fixed_vs_arc": {"p50": 0.06},
         "segments_differ_euclid_vs_geodesic": 0.08,
         "rel_thickness_shape_corrected_sd": 0.09,
         "rel_thickness_by_segment_mean_sd": {str(k): [1.0, 0.1] for k in range(1, 17)}}
    x = dec.from_lima_jm0b(s)
    assert x["aha_frame_fail_share"] == pytest.approx(0.05)
    assert x["aha_orientation_fail_share"] == pytest.approx(1 / 38)
    assert x["endo_halfmax_offset_mm_median"] == 0.2  # canonical already
    assert "epi_halfmax_offset_mm_median" not in x     # n = 0: not measured
    assert x["fat_grid"] == {"0,5": 0.3, "-30,5": 0.04}
    assert x["segment_shape"] == [1.0] * 16 and x["cv_n"] == 0.09


def test_merge_fallback_order_and_sources(dec):
    lima = {"n_cases": 40, "n_frame_ok": 40, "halfmax_offset_endo_mm_case_medians":
            {"p50": 0.2, "n": 40}, "myocardium_relabelled_fixed_vs_arc": {"p50": 0.06}}
    india = {"n_cases": 40, "n_ok": 39, "A_endo_offset_mm_median_p10_p90": [0.15, 0.0, 0.3],
             "A_epi_offset_mm_median_p10_p90": [0.05, -0.1, 0.2],
             "C_seg_changed_prop_median": 0.5, "B_third_agree_et_laplace_median": 0.9}
    hotel = {"endo_halfmax_offset_mm_q25_50_75_n": [0.1, 0.4, 0.5, 39]}
    juliet = {"summary": {"n_cases": 40, "n_usable": 38, "median_thick_mm": 6.2}}
    x, src = dec.merge_fallback(lima, india, hotel, juliet)
    assert set(x) == set(dec.KEYS)
    assert x["n_usable"] == 38 and src["n_usable"] == "juliet"
    assert x["septal_arc_mass_changed_median"] == 0.06       # India only fills gaps
    assert src["septal_arc_mass_changed_median"] == "lima"
    assert x["epi_halfmax_offset_mm_median"] == 0.05
    assert src["epi_halfmax_offset_mm_median"] == "india"
    assert x["endo_halfmax_offset_mm_median"] == -0.4       # Hotel wins, negated
    assert src["endo_halfmax_offset_mm_median"] == "hotel"
    assert x["cv_n"] is None                                # never defaulted


# ------------------------------------------------------------------------------- main
def test_main_prints_one_line_per_rule_and_writes_decisions_json(dec, tmp_path, capsys,
                                                                 monkeypatch):
    monkeypatch.setattr(dec, "detectable_depth", fake_depth(0.35))
    summ = tmp_path / "summary.json"
    summ.write_text(json.dumps({"provenance": {}, "decision_inputs": base()}))
    out = tmp_path / "decisions.json"
    assert dec.main(["--jm0r", str(summ), "--out", str(out)]) == 0
    printed = capsys.readouterr().out.splitlines()
    assert [ln.split(" ")[0] for ln in printed] == [f"R{i}" for i in range(11)]
    assert all("[JA43 R" in ln and "from jm0r" in ln for ln in printed)
    doc = json.loads(out.read_text())
    assert doc["input_script_version"] == "2" and len(doc["decisions"]) == 11
    assert not re.search(r"c\d{4}|s\d{4}|nii", out.read_text())


def test_main_fallback_and_no_input(dec, tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(dec, "detectable_depth", fake_depth(0.35))
    lima = tmp_path / "lima.json"
    lima.write_text(json.dumps({"n_cases": 40, "n_frame_ok": 40}))
    assert dec.main(["--lima", str(lima)]) == 0
    text = capsys.readouterr().out
    assert "NOT DECIDABLE: n_usable" in text and "STOP" in text
    assert dec.main([]) == 2
