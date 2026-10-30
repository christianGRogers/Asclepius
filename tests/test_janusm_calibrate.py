"""Janus-M detectable depth (JA40) on simulated populations only; no case is opened.

The default seed is Hotel E7's, so E7's rows (``experiments/JanusM/Hotel/r3/e7_detectable.json`` on
``jm/rest-ccta``; mixed phase, prevalence 0.1) come back exactly, not just to the 0.05 step.
"""

from __future__ import annotations

import inspect

import numpy as np
import pytest

from janusm import calibrate as C

# E7's seeds advance by 352 per scenario (2 mixes x 2 prevalences x 11 depths x 4 replicates x 2)
E7_SCENARIO_STRIDE = 352


@pytest.fixture(scope="module")
def primary():
    """E7's primary rows: cv_n 0.088, Lima's shape and median, no added error, F1 swept."""
    return C.detectable_depths(
        0.088, C.LIMA_SHAPE, [0.0, 0.35, 0.7, 1.0], seed=31000, median_mm=9.668
    )


def test_e7_primary_rows_reproduce(primary):
    """JA40: 0.30 at RC 0 and 0.35 at RC 1.0, with E7's sensitivity range and false flags."""
    r0, r1 = primary[0.0], primary[1.0]
    assert r0["depth"] == 0.30
    assert [round(x, 4) for x in r0["sens_range"]] == [0.8592, 0.9113]
    assert round(r0["false_flag"], 4) == 0.0188
    assert r1["depth"] == 0.35
    assert [round(x, 4) for x in r1["sens_range"]] == [0.8856, 0.9073]
    assert round(r1["false_flag"], 4) == 0.0061
    assert primary[0.35]["depth"] == 0.30 and primary[0.7]["depth"] == 0.30


def test_e7_every_replicate_reproduces(primary):
    """Two E7 grid rows, replicate by replicate (rounded to E7's four places)."""
    by = {t["depth"]: t for t in primary[1.0]["table"]}
    assert [round(x, 4) for x in by[0.30]["sens"]] == [0.7978, 0.7833, 0.7718, 0.8075]
    assert [round(x, 4) for x in by[0.30]["false_flag"]] == [0.0033, 0.0045, 0.0033, 0.0044]
    by0 = {t["depth"]: t for t in primary[0.0]["table"]}
    assert [round(x, 4) for x in by0[0.25]["sens"]] == [0.7302, 0.6612, 0.7212, 0.657]


def test_inputs_are_explicit_and_the_median_matters():
    """The ruling's signature: ``seed`` has no default. The F1 floor is in mm, so the wall moves
    the result: E7's 0.35 at RC 1.0 needs the 9.668 mm anchor; the 5.7 mm anchor gives 0.45."""
    with pytest.raises(TypeError):
        C.detectable_depth(0.088, C.LIMA_SHAPE, 1.0)
    assert C.LIMA_MEDIAN_MM == 9.668 and C.E7_SEED == 31000
    thin = C.detectable_depth(0.088, C.LIMA_SHAPE, 1.0, seed=31000, median_mm=5.7)
    assert thin["depth"] == 0.45


# ------------------------------------------------------------------------- JA60 (R4-S1)
def test_ja60_default_anchor_is_the_ed_median_and_gives_the_provisional_45():
    """R4-S1: with no wall the anchor is ED_MEDIAN_MM (5.7 mm), not 9.668 mm; JA40's procedure
    there (cv_n 0.088, F1 1.0 mm, seed 31000) is JA60's provisional 45 %."""
    r = C.detectable_depth(0.088, C.LIMA_SHAPE, 1.0, seed=31000)
    assert r["depth"] == 0.45
    assert r["inputs"]["anchor_mm"] == C.ED_MEDIAN_MM == 5.7
    assert r["inputs"]["anchor_source"] == "ed_default"
    assert r["inputs"]["measured_median_mm"] is None and r["inputs"]["median_mm"] is None
    assert r["calibrate_version"] == C.CALIBRATE_VERSION == "1.1.0"
    assert "above 40 %" in C.page_line(r)  # JA40's warning sentence


def test_ja60_population_factor_at_limas_inputs():
    """R4-S1: deterministic (200 000 hearts, seed 7); Lima G1: 1.1087."""
    f = C.population_factor(C.PHASE_MIX, C.LIMA_SHAPE, C.LIMA_CV_N)
    assert f == pytest.approx(1.109, abs=0.002)
    assert C.population_factor(C.PHASE_MIX, C.LIMA_SHAPE, C.LIMA_CV_N) == f
    assert (C.FACTOR_HEARTS, C.FACTOR_SEED) == (200000, 7)
    # phase does not scale an ED-only population: its factor is the patient-scale median only
    assert C.population_factor({"ED": 1.0}, C.LIMA_SHAPE, C.LIMA_CV_N) == pytest.approx(
        1.0, abs=0.01
    )


def test_ja60_measured_median_is_the_simulated_median():
    """R4-S1: at measured_median_mm=6.3 the simulated population's median wall is 6.3 +- 1 %
    (an independent seed, not the factor's own)."""
    anchor = C.anchor_mm(6.3, C.PHASE_MIX, C.LIMA_SHAPE, C.LIMA_CV_N)
    meas, *_ = C.population(
        200000,
        0.0,
        0.0,
        C.LIMA_CV_N,
        0.0,
        C.PHASE_MIX,
        np.random.default_rng(12345),
        shape=C.LIMA_SHAPE,
        median_mm=anchor,
    )
    assert float(np.median(np.median(meas, 1))) == pytest.approx(6.3, rel=0.01)


def test_ja60_detectable_depth_simulates_on_the_anchor_of_the_measured_wall(monkeypatch):
    """R4-S1: every population is simulated at measured / factor, in the phase mix passed, and
    ``inputs`` records the measured wall, the anchor and the factor."""
    seen = []

    def rec(depth, cv_n, shape, rcs, seed, *, sig_m, median_mm, phase_mix):
        seen.append((median_mm, dict(phase_mix)))
        return {"k_mad": 3.0, **{rc: {"false_flag": 0.0, "sens": 1.0} for rc in rcs}}

    monkeypatch.setattr(C, "simulate", rec)
    r = C.detectable_depth(0.088, C.LIMA_SHAPE, 1.0, seed=1, measured_median_mm=6.3)
    f = C.population_factor(C.PHASE_MIX, C.LIMA_SHAPE, 0.088)
    assert len(seen) == 44 and all(m == pytest.approx(6.3 / f) for m, _ in seen)
    assert r["inputs"]["measured_median_mm"] == 6.3
    assert r["inputs"]["anchor_mm"] == pytest.approx(6.3 / f)
    assert r["inputs"]["population_factor"] == f
    assert r["inputs"]["anchor_source"] == "measured"
    seen.clear()
    r = C.detectable_depth(
        0.088, C.LIMA_SHAPE, 1.0, seed=1, measured_median_mm=6.3, phase_mix={"ED": 1.0}
    )
    f_ed = C.population_factor({"ED": 1.0}, C.LIMA_SHAPE, 0.088)
    full = {"ED": 1.0, "MD": 0.0, "SYS": 0.0}  # JA73: the partial mix is passed on in full
    assert seen[0] == (pytest.approx(6.3 / f_ed), full)
    assert r["design"]["phase_mix"] == full and r["inputs"]["phase_mix"] == full


def test_r5_s1_partial_phase_mix_equals_the_three_key_call():
    """R5-S1 (JA73), unstubbed: ``{"ED": 1.0}`` reaches ``population()`` (no ``KeyError: 'MD'``)
    and gives the same depth, table and record as the three-key mix for the same seed."""
    kw = dict(seed=31000, measured_median_mm=6.3)
    part = C.detectable_depth(0.088, C.LIMA_SHAPE, 1.0, phase_mix={"ED": 1.0}, **kw)
    full = C.detectable_depth(
        0.088, C.LIMA_SHAPE, 1.0, phase_mix={"ED": 1, "MD": 0, "SYS": 0}, **kw
    )
    assert part == full
    assert part["inputs"]["phase_mix"] == {"ED": 1.0, "MD": 0.0, "SYS": 0.0}
    assert part["calibrate_version"] == C.CALIBRATE_VERSION == "1.1.1"


@pytest.mark.parametrize(
    "bad",
    [{"ED": 0.5}, {"XX": 1.0}, {"ED": -0.5, "MD": 1.5}, {"ED": float("nan")}, {"ED": "a"}, None],
)
def test_r5_s1_bad_phase_mix_raises_value_error_never_key_error(bad):
    """R5-S1 (JA73): a bad mix is a ``ValueError`` at every entry point, never a ``KeyError``."""
    calls = [
        lambda: C.detectable_depth(0.088, C.LIMA_SHAPE, 1.0, seed=1, phase_mix=bad),
        lambda: C.detectable_depths(0.088, C.LIMA_SHAPE, [1.0], seed=1, phase_mix=bad),
        lambda: C.simulate(0.3, 0.088, C.LIMA_SHAPE, [0.0], 5, phase_mix=bad, n=50),
        lambda: C.population(50, 0.1, 0.3, 0.088, 0.0, bad, np.random.default_rng(0)),
        lambda: C.population_factor(bad),
        lambda: C.anchor_mm(6.3, bad),
    ]
    for call in calls:
        with pytest.raises(ValueError):
            call()


def test_r5_s1_partial_mix_at_every_entry_point():
    """R5-S1 (JA73): ``population``, ``simulate`` and ``population_factor`` take a partial mix,
    with the same draws as the full one."""
    full = {"ED": 0.6, "MD": 0.4, "SYS": 0.0}
    part = {"ED": 0.6, "MD": 0.4}
    a = C.population(50, 0.1, 0.3, 0.088, 0.0, part, np.random.default_rng(0))
    b = C.population(50, 0.1, 0.3, 0.088, 0.0, full, np.random.default_rng(0))
    assert all(np.array_equal(x, y) for x, y in zip(a, b))
    assert C.simulate(0.3, 0.088, C.LIMA_SHAPE, [0.0], 5, phase_mix=part, n=200) == C.simulate(
        0.3, 0.088, C.LIMA_SHAPE, [0.0], 5, phase_mix=full, n=200
    )
    assert C.population_factor({"ED": 1.0}) == C.population_factor({"ED": 1, "MD": 0, "SYS": 0})


def test_ja60_both_walls_raise():
    """R4-S1: measured_median_mm and median_mm together are an error, as is a bad wall."""
    with pytest.raises(ValueError, match="not both"):
        C.detectable_depth(0.088, C.LIMA_SHAPE, 1.0, seed=1, measured_median_mm=6.3, median_mm=5.7)
    with pytest.raises(ValueError, match="not both"):
        C.detectable_depths(
            0.088, C.LIMA_SHAPE, [1.0], seed=1, measured_median_mm=6.3, median_mm=5.7
        )
    for bad in (0.0, -1.0, float("nan")):
        with pytest.raises(ValueError):
            C.detectable_depth(0.088, C.LIMA_SHAPE, 1.0, seed=1, measured_median_mm=bad)
    with pytest.raises(ValueError, match="phase"):
        C.detectable_depth(0.088, C.LIMA_SHAPE, 1.0, seed=1, phase_mix={"ED": 0.5})


def test_no_depth_names_the_largest_tried():
    r = C.detectable_depth(0.30, C.LIMA_SHAPE, 1.0, seed=3, median_mm=9.668)
    assert r["depth"] is None and r["exceeds"] == 0.60 and r["sens_range"] is None
    assert "numbers only" in C.page_line(r)


def test_the_single_function_matches_the_sweep(primary):
    r = C.detectable_depth(0.088, C.LIMA_SHAPE, 1.0, seed=31000, median_mm=9.668)
    assert r["depth"] == primary[1.0]["depth"] and r["sens_range"] == primary[1.0]["sens_range"]
    assert r["false_flag"] == primary[1.0]["false_flag"]
    assert r["inputs"]["rc_terr_mm"] == 1.0 and r["inputs"]["sig_m"] == 0.0
    assert r["design"]["replicates"] == 4 and r["design"]["n_per_population"] == 2000
    assert r["design"]["phase_mix"] == {"ED": 0.4, "MD": 0.4, "SYS": 0.2}
    assert r["design"]["prevalence"] == 0.1


@pytest.mark.parametrize(
    "scenario, cv_n, sig_m, expect",
    [
        (2, 0.088, 0.5, {0.0: 0.35, 1.0: 0.35}),  # Lima-style row: error added on top
        (3, 0.06, 0.0, {0.0: 0.20, 1.0: 0.30}),
        (4, 0.12, 0.0, {0.0: 0.40, 1.0: 0.40}),
        (5, 0.15, 0.0, {0.0: 0.45, 1.0: 0.45}),
    ],
)
def test_e7_lookup_rows_reproduce(scenario, cv_n, sig_m, expect):
    """E7's lookup on cv_n and its Lima-style sensitivity row, at E7's seeds."""
    seed = 31000 + E7_SCENARIO_STRIDE * scenario
    r = C.detectable_depths(
        cv_n, C.LIMA_SHAPE, list(expect), sig_m=sig_m, seed=seed, median_mm=9.668
    )
    assert {rc: r[rc]["depth"] for rc in expect} == expect


def test_false_flags_stay_under_the_calibration_target(primary):
    for r in primary.values():
        assert r["false_flag"] <= C.FALSE_FLAG_TARGET


def test_the_depth_is_on_the_grid_and_rounded_up(primary):
    for r in primary.values():
        assert r["depth"] in C.DEPTHS
        means = [np.mean(t["sens"]) for t in r["table"]]
        i = C.DEPTHS.index(r["depth"])
        assert means[i] >= 0.80 and all(m < 0.80 for m in means[:i])


def test_a_seed_is_reproducible_and_another_seed_differs():
    a = C.simulate(0.3, 0.088, C.LIMA_SHAPE, [0.0], 5)
    assert a == C.simulate(0.3, 0.088, C.LIMA_SHAPE, [0.0], 5)
    assert a != C.simulate(0.3, 0.088, C.LIMA_SHAPE, [0.0], 7)


def test_territory_flags_need_two_contiguous_segments():
    f = np.zeros((3, 16), bool)
    f[0, [0, 1]] = True  # segments 1, 2: LAD, adjacent
    f[1, [0, 13]] = True  # segments 1, 14: LAD, not adjacent
    f[2, [2, 8]] = True  # segments 3, 9: RCA, adjacent
    t = C.territory_flags(f)
    assert t[0].tolist() == [True, False, False]
    assert not t[1].any()
    assert t[2].tolist() == [False, True, False]


def test_f1_deviation_reads_a_known_thinning():
    shape = np.asarray(C.LIMA_SHAPE)
    meas = 10.0 * shape[None, :].repeat(2, 0)
    lad = [s - 1 for s in C.TERR16["LAD"]]
    meas[1, lad] *= 0.7
    d = C.f1_deviation(meas, shape)
    assert np.allclose(d[0], 0.0)
    assert d[1, 0] == pytest.approx(0.3 * 10.0 * shape[lad].mean())
    # the thinned LAD is most of the other territories' remote, so they read thicker, never thinner
    assert (d[1, 1:] < 0).all()


def test_inputs_are_checked():
    with pytest.raises(ValueError):
        C.detectable_depth(0.088, C.LIMA_SHAPE[:15], 1.0, seed=1)
    with pytest.raises(ValueError):
        C.detectable_depth(-0.1, C.LIMA_SHAPE, 1.0, seed=1)
    with pytest.raises(ValueError):
        C.detectable_depth(0.088, C.LIMA_SHAPE, -1.0, seed=1)
    with pytest.raises(ValueError, match="no normal variation"):
        C.detectable_depth(0.0, C.LIMA_SHAPE, 1.0, seed=1)  # rule C would have no scale (0 / 0)


def test_page_line_fills_the_depth_and_warns_above_forty_percent(primary):
    line = C.page_line(primary[1.0])
    assert "≥ 35 %" in line and "not a sensitivity for scar" in line
    assert "above 40 %" not in line
    assert "above 40 %" not in C.page_line(0.40)
    assert "above 40 %" in C.page_line(0.45)
    assert "up to 60 %" in C.page_line(None)
    hypo = C.page_line(0.30, "hypoattenuation")
    assert hypo.startswith("Hypoattenuation:") and "≥ 30 %" in hypo


def test_calibrate_opens_no_case():
    src = inspect.getsource(C)
    for word in ("nibabel", "load_case", "open(", "glob"):
        assert word not in src, word
