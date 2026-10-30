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
    return C.detectable_depths(C.LIMA_CV_N, C.LIMA_SHAPE, [0.0, 0.35, 0.7, 1.0])


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


def test_the_single_function_matches_the_sweep(primary):
    r = C.detectable_depth(C.LIMA_CV_N, C.LIMA_SHAPE, 1.0)
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
    seed = C.DEFAULT_SEED + E7_SCENARIO_STRIDE * scenario
    r = C.detectable_depths(cv_n, C.LIMA_SHAPE, list(expect), sig_m=sig_m, seed=seed)
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
        C.detectable_depth(0.088, C.LIMA_SHAPE[:15], 1.0)
    with pytest.raises(ValueError):
        C.detectable_depth(-0.1, C.LIMA_SHAPE, 1.0)
    with pytest.raises(ValueError):
        C.detectable_depth(0.088, C.LIMA_SHAPE, -1.0)
    with pytest.raises(ValueError, match="no normal variation"):
        C.detectable_depth(0.0, C.LIMA_SHAPE, 1.0)  # rule C would have no scale (0 / 0)


def test_page_line_fills_the_depth_and_warns_above_forty_percent(primary):
    line = C.page_line(primary[1.0])
    assert ">= 35 %" in line and "not a sensitivity for scar" in line
    assert "above 40 %" not in line
    assert "above 40 %" not in C.page_line(0.40)
    assert "above 40 %" in C.page_line(0.45)
    assert "up to 60 %" in C.page_line(None)


def test_calibrate_opens_no_case():
    src = inspect.getsource(C)
    for word in ("nibabel", "load_case", "open(", "glob"):
        assert word not in src, word
