"""Janus-M border-error harness (JA15, JA16) on synthetic phantoms only.

The phantom's borders are exact signed-distance level sets, so a shifted phantom is a known,
exact offset of each closed surface: the truth the ASSD, signed-bias and thickness measures are
checked against. No case is opened.
"""

from __future__ import annotations

import inspect

import numpy as np
import pytest
from scipy import ndimage as ndi

from janusm import geometry as G
from janusm import harness as H

SP = np.full(3, H.GRID_MM)


@pytest.fixture(scope="module")
def ref():
    return H.phantom()


@pytest.fixture(scope="module")
def ja16():
    """JA16's check, as Round 3 will run it."""
    return H.validate_bias_estimator()


# ------------------------------------------------------------------------------- error model
def test_corrected_sdf_puts_the_border_between_voxel_centres():
    m = np.zeros((9, 9, 9), bool)
    m[:4] = True  # border between i = 3 and i = 4
    s = H.corrected_sdf(m, SP)
    assert s[3, 4, 4] == pytest.approx(-SP[0] / 2)
    assert s[4, 4, 4] == pytest.approx(SP[0] / 2)
    assert s[1, 4, 4] == pytest.approx(-2.5 * SP[0])


def test_smooth_field_is_zero_mean_scaled_and_seeded():
    shape = (40, 40, 40)
    f = H.smooth_field(shape, SP, 0.5, 4.0, np.random.default_rng(3))
    assert f.mean() == pytest.approx(0.0, abs=1e-5)
    assert f.std() == pytest.approx(0.5, rel=1e-4)
    g = H.smooth_field(shape, SP, 0.5, 4.0, np.random.default_rng(3))
    assert np.array_equal(f, g)
    assert not H.smooth_field(shape, SP, 0.0, 4.0, np.random.default_rng(3)).any()

    def lag1(x):
        return np.corrcoef(x[:-1].ravel(), x[1:].ravel())[0, 1]

    rough = H.smooth_field(shape, SP, 0.5, 1.0, np.random.default_rng(3))
    assert lag1(f) > lag1(rough)


def test_perturb_without_error_is_the_identity(ref):
    lab, _ = ref
    assert np.array_equal(H.perturb(lab, SP, rng=np.random.default_rng(0)), lab)


def test_perturb_moves_the_borders_independently(ref):
    lab, _ = ref
    cav, sol = H.borders(lab)
    inward = H.perturb(lab, SP, bias_endo=-0.5)
    c2, s2 = H.borders(inward)
    assert np.array_equal(s2, sol) and c2.sum() < cav.sum()
    out = H.perturb(lab, SP, bias_epi=0.5)
    c3, s3 = H.borders(out)
    assert np.array_equal(c3, cav) and s3.sum() > sol.sum()
    # RV and LA keep what the wall does not take
    assert ((out == G.RV) <= (lab == G.RV)).all() and ((out == G.LA) <= (lab == G.LA)).all()


def test_perturb_refuses_a_map_without_an_lv():
    with pytest.raises(ValueError):
        H.perturb(np.zeros((8, 8, 8), np.int16), SP)


# ------------------------------------------------------------------------------- ASSD
def test_assd_is_zero_on_itself_symmetric_and_reads_a_known_shift(ref):
    lab, _ = ref
    _, sol = H.borders(lab)
    _, sol5 = H.borders(H.phantom(epi_shift_mm=0.5)[0])
    assert H.surface_assd(sol, sol, SP) == 0.0
    a, b = H.surface_assd(sol, sol5, SP), H.surface_assd(sol5, sol, SP)
    assert a == pytest.approx(b)
    assert a == pytest.approx(0.5, abs=0.1)
    assert np.isnan(H.surface_assd(sol, np.zeros_like(sol), SP))


# ------------------------------------------------------------------------------- signed bias
def test_signed_bias_is_signed_outward_and_antisymmetric(ref):
    lab, _ = ref
    cav, _ = H.borders(lab)
    cav5, _ = H.borders(H.phantom(endo_shift_mm=0.5)[0])
    assert H.signed_bias(cav, cav, SP) == 0.0
    out = H.signed_bias(cav, cav5, SP)
    assert out > 0
    assert H.signed_bias(cav5, cav, SP) == pytest.approx(-out)


def test_surface_area_matches_the_analytic_capsule():
    cav, outer, *_ = H._phantom_parts(SP, 0, 0, (0.11, 0.23, 0.07), 0, H.PHANTOM_RC, H.PHANTOM_WALL)
    for m, r in ((cav, H.PHANTOM_RC), (outer, H.PHANTOM_RC + H.PHANTOM_WALL)):
        true = np.pi * r**2 + 2 * np.pi * r * H.PHANTOM_CYL + 2 * np.pi * r**2
        assert H.surface_area(m, SP) == pytest.approx(true, rel=0.02)


def test_ja16_the_estimator_recovers_a_known_half_millimetre_shift(ja16):
    """JA16: a known 0.5 mm shift, each direction, each border, within +-0.05 mm."""
    assert ja16["shift_mm"] == 0.5 and ja16["tolerance_mm"] == 0.05
    rows = ja16["rows"]
    assert {(r["border"], np.sign(r["true_mm"])) for r in rows} == {
        ("endo", 1),
        ("endo", -1),
        ("epi", 1),
        ("epi", -1),
    }
    assert any(r["tilt_deg"] for r in rows) and any(r["cavity_shift_mm"] for r in rows)
    assert ja16["worst_abs_error_mm"] <= 0.05
    assert ja16["passed"] and ja16["bias_guard_mm"] == H.BIAS_GUARD_VALIDATED_MM == 0.3


def test_ja16_guard_falls_back_when_the_check_fails():
    r = H.validate_bias_estimator(tolerance_mm=1e-6, n_offsets=1, shapes=((0.0, 0.0),))
    assert not r["passed"] and r["bias_guard_mm"] == H.BIAS_GUARD_FALLBACK_MM == 0.5


def _round2_india_bias(ref_mask, test_mask, sp):
    """India R2's estimator (experiments/JanusM/India/harness_r2.py border_stats), for contrast."""
    surf = ref_mask & ~ndi.binary_erosion(ref_mask, ndi.generate_binary_structure(3, 1))
    return -(float(np.mean(H.corrected_sdf(test_mask, sp)[surf])) + float(np.mean(sp)) / 2)


def test_the_round2_estimator_under_reads_where_this_one_does_not():
    """Round 2 judgement section 1.3: India's estimator read about +0.35 for a +0.5 mm shift."""
    off = (0.13, 0.31, 0.22)
    cav, *_ = H._phantom_parts(SP, 0, 0, off, 0, H.PHANTOM_RC, H.PHANTOM_WALL)
    cav5, *_ = H._phantom_parts(SP, 0.5, 0, off, 0, H.PHANTOM_RC, H.PHANTOM_WALL)
    assert _round2_india_bias(cav, cav5, SP) < 0.45
    assert H.signed_bias(cav, cav5, SP) == pytest.approx(0.5, abs=0.05)


# ------------------------------------------------------------------------------- thickness
def test_thickness_error_is_the_median_over_segments_1_to_16():
    ref = {k: 8.0 for k in range(1, 18)}
    test = {**ref, 1: 9.0, 2: 9.0, 3: 12.0, 17: 30.0}
    th = H.thickness_error(ref, test)
    assert th["n_segments"] == 16  # 17 is not a wall segment for JA8
    assert th["median_abs_mm"] == 0.0 and th["median_signed_mm"] == 0.0
    test = {k: 8.0 + (1.0 if k <= 9 else 0.0) for k in range(1, 17)}
    assert H.thickness_error(ref, test)["median_abs_mm"] == 1.0
    assert H.thickness_error({}, test)["n_segments"] == 0


def test_compare_on_itself_is_all_zero(ref):
    lab, aff = ref
    r = H.compare(lab, lab, affine=aff)
    for k in ("assd_endo", "assd_epi", "bias_endo", "bias_epi", "thick_err_median_mm"):
        assert r[k] == 0.0, k
    assert r["sta"] == 1.0 and r["dice_myo"] == 1.0 and r["n_segments"] == 16
    assert r["harness_version"] == H.HARNESS_VERSION
    assert r["geometry_version"] == G.GEOMETRY_VERSION


# ------------------------------------------------------------------------------- JA15 model rows
def test_rows_are_indexed_by_what_was_realised(ref):
    lab, aff = ref
    rows = [
        H.run(lab, aff, sigma=s, rng=np.random.default_rng(11), with_sta=False)
        for s in (0.25, 0.5, 1.0)
    ]
    assd = [r["assd_endo"] for r in rows]
    assert assd[0] < assd[1] < assd[2]
    for r in rows:
        assert r["corr_mm"] == H.CORR_MM and "sigma_nominal" in r
        assert r["assd_endo"] != r["sigma_nominal"]
        # a zero-mean field leaves a small realised bias, well under the shift itself
        assert abs(r["bias_endo"]) < r["assd_endo"]
    again = H.run(lab, aff, sigma=0.5, rng=np.random.default_rng(11), with_sta=False)
    assert {k: v for k, v in again.items() if k != "sta"} == {
        k: v for k, v in rows[1].items() if k != "sta"
    }


def test_a_constant_model_bias_costs_about_its_own_size_in_thickness(ref):
    """Section 1.3 / JA16: about 1 mm of thickness error per mm of realised bias. The model's
    nominal 0.5 mm on the voxel signed distance realises more than 0.5 mm, hence realised units."""
    lab, aff = ref
    r = H.run(lab, aff, bias_epi=0.5, with_sta=False)
    assert 0.5 < r["bias_epi"] < 0.7
    assert r["thick_bias_median_mm"] == pytest.approx(r["bias_epi"], abs=0.1)
    assert r["assd_endo"] == 0.0


def test_the_harness_opens_no_case():
    src = inspect.getsource(H)
    for word in ("nibabel", "load_case", "open(", "glob"):
        assert word not in src, word
