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
    cav, outer, _ = H.exact_shift_phantom(SP, origin_offset_mm=(0.11, 0.23, 0.07))
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
    assert ja16["passed"] and ja16["bias_guard_mm"] == H.BIAS_GUARD_TIGHT_MM == 0.3


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
    cav, *_ = H.exact_shift_phantom(SP, origin_offset_mm=off)
    cav5, *_ = H.exact_shift_phantom(SP, endo_shift_mm=0.5, origin_offset_mm=off)
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
    for k in (
        "assd_voxel_endo",
        "assd_voxel_epi",
        "assd_pp_endo",
        "assd_pp_epi",
        "bias_endo",
        "bias_epi",
        "bias_pp_endo",
        "bias_pp_epi",
        "thick_err_median_mm",
    ):
        assert r[k] == 0.0, k
    assert "assd_endo" not in r  # JA39: an unqualified ASSD would be ambiguous
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
    assd = [r["assd_pp_endo"] for r in rows]
    assert assd[0] < assd[1] < assd[2]
    for r in rows:
        assert r["corr_mm"] == H.CORR_MM and "sigma_nominal" in r
        assert r["assd_pp_endo"] != r["sigma_nominal"]
        assert r["assd_voxel_endo"] > 0
        # a zero-mean field leaves a small realised bias, well under the shift itself
        assert abs(r["bias_endo"]) < r["assd_pp_endo"]
        assert abs(r["bias_pp_endo"]) < r["assd_pp_endo"]
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
    assert r["assd_voxel_endo"] == 0.0 and r["assd_pp_endo"] == 0.0
    # JA38: the nominal and the realised bias side by side
    assert r["bias_epi_nominal"] == 0.5 and r["bias_epi_realised"] == r["bias_epi"]
    assert r["bias_endo_nominal"] == 0.0 and r["bias_endo_realised"] == 0.0
    assert r["bias_pp_epi"] == pytest.approx(r["bias_epi"], abs=0.05)


# ------------------------------------------------------------------------------- JA45 API
def test_harness_version_is_1_3():
    """R5-S3: JA70's band moves reported numbers."""
    assert H.HARNESS_VERSION == "1.3.0"


def test_exact_shift_phantom_moves_the_closed_surface_by_the_shift():
    off = (0.17, 0.05, 0.29)
    cav, sol, aff = H.exact_shift_phantom(SP, origin_offset_mm=off)
    cav5, sol5, aff5 = H.exact_shift_phantom(SP, endo_shift_mm=0.5, origin_offset_mm=off)
    assert np.array_equal(aff, aff5) and cav.shape == cav5.shape
    assert np.array_equal(sol, sol5) and (cav <= cav5).all()
    assert not (cav & ~sol).any()  # the cavity sits inside the outer capsule (flat tops coplanar)
    # the exact volume change of the capsule grown by d (its signed-distance level set): the
    # cylinder and hemisphere widen, and the flat top gains a disc with a rounded rim
    r, d, L = H.PHANTOM_RC, 0.5, H.PHANTOM_CYL
    dv = np.pi * ((r + d) ** 2 - r**2) * L + 2 / 3 * np.pi * ((r + d) ** 3 - r**3)
    dv += np.pi * r**2 * d + 2 * np.pi * (r + 4 * d / (3 * np.pi)) * np.pi * d**2 / 4
    assert (cav5.sum() - cav.sum()) * np.prod(SP) == pytest.approx(dv, rel=0.03)


def test_pp_is_zero_on_itself_antisymmetric_and_nan_when_empty():
    cav, _, _ = H.exact_shift_phantom(SP, origin_offset_mm=(0.1, 0.2, 0.3))
    cav5, _, _ = H.exact_shift_phantom(SP, endo_shift_mm=0.5, origin_offset_mm=(0.1, 0.2, 0.3))
    assert H.signed_bias_pp(cav, cav, SP) == 0.0 and H.assd_pp(cav, cav, SP) == 0.0
    b = H.signed_bias_pp(cav, cav5, SP)
    assert b == pytest.approx(0.5, abs=0.03)
    assert H.signed_bias_pp(cav5, cav, SP) == pytest.approx(-b)
    assert H.assd_pp(cav, cav5, SP) == pytest.approx(H.assd_pp(cav5, cav, SP))
    assert np.isnan(H.assd_pp(cav, np.zeros_like(cav), SP))
    assert np.isnan(H.signed_bias_pp(np.zeros_like(cav), cav, SP))


def test_pp_does_not_depend_on_the_padding_around_the_heart():
    cav, _, _ = H.exact_shift_phantom(SP, origin_offset_mm=(0.1, 0.2, 0.3))
    cav5, _, _ = H.exact_shift_phantom(SP, endo_shift_mm=0.5, origin_offset_mm=(0.1, 0.2, 0.3))
    a = H._pp(cav, cav5, SP)
    big = [np.pad(m, ((5, 17), (0, 9), (11, 0))) for m in (cav, cav5)]
    assert H._pp(*big, SP) == pytest.approx(a, abs=1e-6)


# E4 (Lima R3): exact spheres, sub-voxel centre jitter; JA45: signed_bias within +-0.01 mm to 1 mm
@pytest.mark.slow
@pytest.mark.parametrize("radius", [12.0, 21.0])
def test_e4_exact_shells_signed_bias_within_a_hundredth(radius):
    rng = np.random.default_rng(int(radius))
    n = int(2 * (radius + 4) / H.GRID_MM)
    ax = (np.arange(n) - n / 2) * H.GRID_MM
    X, Y, Z = np.meshgrid(ax, ax, ax, indexing="ij", sparse=True)
    for _ in range(2):
        c = rng.uniform(-H.GRID_MM / 2, H.GRID_MM / 2, 3)
        R = np.sqrt((X - c[0]) ** 2 + (Y - c[1]) ** 2 + (Z - c[2]) ** 2)
        ref = R < radius
        for d in (-1.0, -0.5, -0.3, -0.1, 0.1, 0.3, 0.5, 1.0):
            assert H.signed_bias(ref, R < radius + d, SP) == pytest.approx(d, abs=0.01), d


# E6 (Hotel R3): Hotel's ellipsoid LV, two grids, axis-aligned or oblique, smooth or rough walls.
# The phantom is JA71's phantom A and lives in the harness (``H.e6_open_phantom``).
E6_BOX = H.E6_BOX_MM


def _e6_phantom(sp, rot_seed, rough):
    """(cavity F, solid F, base-plane coordinate, ROI); the ROI leaves out 6 mm at the base."""
    Fc, Fs, base = H.e6_open_phantom(sp, rot_seed, rough)
    return Fc, Fs, base, base < -6.0


def _e6_truth(F, s, sp, roi):
    """True mean signed and absolute normal displacement of the level-set shift F - s < 0."""
    return H.e6_truth(F, s, sp, roi)


def _ja39_tolerance(shift):
    return min(t for d, t in H.PP_ASSD_TOLERANCE_MM.items() if abs(shift) <= d)


def test_ja65_tolerances_are_0035_and_007():
    assert H.PP_ASSD_TOLERANCE_MM == {0.5: 0.035, 1.0: 0.07}
    assert _ja39_tolerance(0.5) == 0.035 and _ja39_tolerance(-1.0) == 0.07


@pytest.mark.slow
@pytest.mark.parametrize("sp", [(0.5, 0.5, 0.5), (0.4, 0.4, 0.5)])
@pytest.mark.parametrize("rot, rough", [(None, False), (23, False), (11, True)])
def test_e6_pp_within_ja39_tolerances(sp, rot, rough):
    """JA39 as JA65 restates it: pp ASSD within 0.035 mm of the truth up to 0.5 mm and 0.07 mm at
    1.0 mm, both grids, oblique and rough walls; the pp bias to the same bounds. Compared
    unrounded (E6's worst at 0.5 mm is 0.032, Lima E7's 0.0322)."""
    Fc, Fs, base, roi = _e6_phantom(sp, rot, rough)
    for F in (Fc, Fs):
        ref = (F < 0) & (base < 0)
        for shift in (-1.0, -0.5, -0.25, 0.25, 0.5, 1.0):
            test = ((F - shift) < 0) & (base < 0)
            tb, ta = _e6_truth(F, shift, sp, roi)
            bias = H.signed_bias_pp(ref, test, sp, roi)
            assd = H.assd_pp(ref, test, sp, roi)
            tol = _ja39_tolerance(shift)
            assert abs(assd - ta) <= tol, (shift, assd, ta)
            assert abs(bias - tb) <= tol, (shift, bias, tb)


@pytest.mark.slow
def test_e6_pp_on_a_smooth_random_field():
    """E6's JA15 field rows: an 8 mm field of 0.5 mm SD on the oblique rough wall."""
    sp = (0.5, 0.5, 0.5)
    Fc, _, base, roi = _e6_phantom(sp, 11, True)
    S = H.smooth_field(Fc.shape, sp, 0.5, 8.0, np.random.default_rng(7))
    ref, test = (Fc < 0) & (base < 0), ((Fc - S) < 0) & (base < 0)
    tb, ta = _e6_truth(Fc, S[(np.abs(Fc) < 0.25) & roi], sp, roi)
    assert H.assd_pp(ref, test, sp, roi) == pytest.approx(ta, abs=0.03)
    assert H.signed_bias_pp(ref, test, sp, roi) == pytest.approx(tb, abs=0.03)


def test_compare_restricts_pp_and_the_guard_to_the_roi():
    """JA61: an ROI restricts ``signed_bias`` as well as pp; the voxel measures stay whole."""
    lab, aff = H.phantom()
    test = H.phantom(endo_shift_mm=0.5)[0]
    roi = np.zeros(lab.shape, bool)
    full = H.compare(lab, test, affine=aff, with_sta=False)
    none = H.compare(lab, test, affine=aff, with_sta=False, roi=roi)
    assert full["bias_pp_endo"] > 0.3 and np.isnan(none["bias_pp_endo"])
    assert full["bias_endo"] > 0.3 and np.isnan(none["bias_endo"])
    assert none["assd_voxel_endo"] == full["assd_voxel_endo"]
    assert full["roi"] == "none" and none["roi"] == "array"
    with pytest.raises(ValueError):
        H.compare(lab, test, affine=aff, with_sta=False, roi="band")


def test_compare_ja37_builds_the_band_per_border():
    lab, aff = H.phantom()
    test = H.phantom(endo_shift_mm=0.5)[0]
    r = H.compare(lab, test, affine=aff, with_sta=False, roi="ja37")
    assert r["roi"] == "ja37"
    cav, _ = H.borders(lab)
    cav_t, _ = H.borders(test)
    band = H.ja37_band(lab, SP, "endo")
    assert r["bias_endo"] == H.signed_bias(cav, cav_t, SP, roi=band)
    assert r["bias_pp_endo"] == H.signed_bias_pp(cav, cav_t, SP, band)
    assert r["assd_pp_endo"] == H.assd_pp(cav, cav_t, SP, band)
    assert r["assd_voxel_endo"] == H.surface_assd(cav, cav_t, SP)  # voxel ASSD on whole masks
    # the shift is exact on the wall; the band leaves out the LA plane, which does not move
    assert r["bias_endo"] == pytest.approx(0.5, abs=0.05)
    assert r["bias_epi"] == 0.0 and r["bias_pp_epi"] == 0.0


def test_the_harness_opens_no_case():
    src = inspect.getsource(H)
    for word in ("nibabel", "load_case", "open(", "glob"):
        assert word not in src, word


# ------------------------------------------------------------------------------- JA65 voxel ASSD
def test_surface_assd_is_segtrains():
    """R4-S6: one voxel ASSD, ``segtrain.metrics.surface_distances``, on the phantom."""
    from segtrain.metrics import surface_distances

    lab, _ = H.phantom()
    cav, _ = H.borders(lab)
    cav5, _ = H.borders(H.phantom(endo_shift_mm=0.5)[0])
    da, db = surface_distances(cav, cav5, SP)
    want = (da.sum() + db.sum()) / (da.size + db.size)
    assert H.surface_assd(cav, cav5, SP) == want
    assert want == pytest.approx(0.47283, abs=5e-6)
    assert "surface_distances" in inspect.getsource(H.surface_assd)


# ------------------------------------------------------------------------------- JA61 band
def _open_pool_face_centres(lab):
    """Centres (mm) of every LV-pool face adjoining label 0 or the array's edge, by brute force."""
    cav = lab == G.LV
    out = []
    for p in np.argwhere(cav):
        for a in range(3):
            for st in (-1, 1):
                q = p.copy()
                q[a] += st
                if (q < 0).any() or (q >= lab.shape).any() or lab[tuple(q)] == 0:
                    c = p.astype(float)
                    c[a] += 0.5 * st
                    out.append(c)
    return np.array(out) * SP


def _small_open_lv():
    """A small LV: a pool in a 4 mm myocardium, with LA over half the base and the other half of
    the base open to label 0 (the outflow)."""
    n = 56
    ax = (np.arange(n) - n / 2 + 0.5) * H.GRID_MM
    X, Y, Z = np.meshgrid(ax, ax, ax, indexing="ij")
    r = np.hypot(X, Y)
    lab = np.zeros((n, n, n), np.int16)
    lab[(r < 9) & (Z < 4) & (Z > -10)] = G.MYO
    lab[(r < 5) & (Z < 4) & (Z > -6)] = G.LV
    lab[(r < 9) & (Z >= 4) & (Z < 8) & (X < 0)] = G.LA
    return lab


def test_ja37_band_excludes_label_4_and_open_pool_faces():
    """R4-S4: JA61's band holds no voxel within 3 mm of label 4 or of an open LV-pool face, and
    keeps the rest of +-3 mm about the border. JA70's band is JA61's less 3 mm about cap faces."""
    from scipy.spatial import cKDTree

    lab = _small_open_lv()
    faces = _open_pool_face_centres(lab)
    assert len(faces)  # the outflow half of the base is open
    la = np.argwhere(lab == G.LA) * SP
    cap, _ = H.cut_cap_faces(lab, SP)
    assert len(cap)
    for border in ("endo", "epi"):
        b70 = H.ja37_band(lab, SP, border)
        band = H.ja37_band(lab, SP, border, cut_cap=False)
        assert not (b70 & ~band).any()
        gone = np.argwhere(band & ~b70) * SP
        assert cKDTree(cap).query(gone)[0].max() <= 3.0 + 1e-9
        pts = np.argwhere(band) * SP
        assert len(pts)
        assert cKDTree(la).query(pts)[0].min() > 3.0
        assert cKDTree(faces).query(pts)[0].min() > 3.0
        # what is left out is only for those reasons, or because it is > 3 mm off the border
        cav, sol = H.borders(lab)
        m = cav if border == "endo" else sol
        near = np.abs(H.corrected_sdf(m, SP)) <= 3.0
        cand = np.argwhere(near & ~band) * SP
        why = np.minimum(cKDTree(la).query(cand)[0], cKDTree(faces).query(cand)[0])
        assert (why <= 3.0 + 1e-9).all()
        assert not (band & ~near).any()
    with pytest.raises(ValueError):
        H.ja37_band(lab, SP, "both")


def test_a_change_within_3mm_of_label_4_moves_the_banded_bias_by_nothing():
    """R4-S4: grow the pool only within 3 mm of the LA; the bias in the band is 0 +- 0.01."""
    lab, _ = H.phantom()
    la = lab == G.LA
    near_la = ndi.distance_transform_edt(~la, sampling=SP) <= 3.0
    cav, sol = H.borders(lab)
    grown = cav | (ndi.binary_dilation(cav, iterations=2) & near_la & sol)
    assert (grown & ~cav).sum() > 100  # a change was made
    band = H.ja37_band(lab, SP, "endo")
    assert H.signed_bias(cav, grown, SP, roi=band) == pytest.approx(0.0, abs=0.01)
    assert H.signed_bias(cav, grown, SP) > 0.01  # the whole-mask estimator sees it


def test_signed_bias_roi_restricts_volume_and_area():
    cav, *_ = H.exact_shift_phantom(SP, origin_offset_mm=(0.1, 0.2, 0.3))
    cav5, *_ = H.exact_shift_phantom(SP, endo_shift_mm=0.5, origin_offset_mm=(0.1, 0.2, 0.3))
    every = np.ones(cav.shape, bool)
    assert H.signed_bias(cav, cav5, SP, roi=every) == pytest.approx(H.signed_bias(cav, cav5, SP))
    assert H.surface_area(cav, SP, roi=every) == pytest.approx(H.surface_area(cav, SP))
    lower = np.zeros(cav.shape, bool)
    lower[:, :, : cav.shape[2] // 2] = True
    a_lo = H.surface_area(cav, SP, roi=lower)
    assert 0 < a_lo < H.surface_area(cav, SP)
    assert a_lo + H.surface_area(cav, SP, roi=~lower) == pytest.approx(H.surface_area(cav, SP))
    with pytest.raises(ValueError):
        H.signed_bias(cav, cav5, SP, roi=lower[:-1])


@pytest.mark.slow
@pytest.mark.parametrize("radius", [12.0, 21.0])
@pytest.mark.parametrize("jitter_seed", [0, 1])
def test_e4_closed_shells_stay_within_a_hundredth_in_the_band(radius, jitter_seed):
    """R4-S4, R5-S4 (JA79): E4's exact shells (a pool in a myocardial shell, nothing open) within
    +-0.01 mm in the band, on both borders, at two sub-voxel centre jitters."""
    lab, R = H.e4_shell(radius, int(radius) + 1 + 100 * jitter_seed)
    for border, r0 in (("endo", radius), ("epi", radius + 5.0)):
        band = H.ja37_band(lab, SP, border)
        assert band.any()
        assert np.array_equal(band, H.ja37_band(lab, SP, border, cut_cap=False))
        ref = R < r0
        for d in (-0.5, -0.3, 0.3, 0.5):
            est = H.signed_bias(ref, R < r0 + d, SP, roi=band)
            assert est == pytest.approx(d, abs=0.01), (border, d)


def _e6_labels(Fc, Fs, base):
    return H.e6_labels(Fc, Fs, base)


@pytest.fixture(scope="module")
def india_open_base():
    """R4-S4 / JA61: India's open-base phantom (E6's, cut at the base plane, pool open to label 0):
    two grids, three walls, both borders, +-0.3 / +-0.5 mm; ``signed_bias`` in JA61's band and in
    JA70's, against the true mean normal displacement in each band."""
    rows = []
    for sp in [(0.5, 0.5, 0.5), (0.4, 0.4, 0.5)]:
        for rot, rough in [(None, False), (23, False), (11, True)]:
            Fc, Fs, base, _ = _e6_phantom(sp, rot, rough)
            lab = _e6_labels(Fc, Fs, base)
            for border, F in (("endo", Fc), ("epi", Fs)):
                bands = {
                    "ja61": H.ja37_band(lab, sp, border, cut_cap=False),
                    "ja70": H.ja37_band(lab, sp, border),
                }
                ref = (F < 0) & (base < 0)
                for shift in (-0.5, -0.3, 0.3, 0.5):
                    test = ((F - shift) < 0) & (base < 0)
                    whole = H.signed_bias(ref, test, sp) - _e6_truth(F, shift, sp, base < 0)[0]
                    row = dict(border=border, shift=shift, whole=whole)
                    for k, band in bands.items():
                        tb, _ = _e6_truth(F, shift, sp, band)
                        row[k] = H.signed_bias(ref, test, sp, roi=band) - tb
                    rows.append(row)
    return rows


@pytest.mark.slow
def test_open_base_india_phantom_with_the_band(india_open_base):
    """R4-S4's open-base check, and R5-S4's pins as R5-S3 replaces them. JA61's band fails: its
    epicardial +-0.5 mm rows all lie in (0.05, 0.075], worst 0.068 +- 0.003 mm (the cut cap stays
    in the band). JA70's band brings every row within 0.05 mm (phantom A of JA71)."""
    rows = india_open_base
    assert len(rows) == 2 * 3 * 2 * 4
    for r in rows:
        assert abs(r["ja61"]) < abs(r["whole"]), r
        if r["border"] == "endo" or abs(r["shift"]) == 0.3:
            assert abs(r["ja61"]) <= 0.05, r
        else:
            assert 0.05 < abs(r["ja61"]) <= 0.075, r
    assert max(abs(r["ja61"]) for r in rows) == pytest.approx(0.068, abs=0.003)
    worst70 = max(abs(r["ja70"]) for r in rows)
    assert worst70 <= H.BIAS_CHECK_TOLERANCE_MM
    assert worst70 == pytest.approx(JA71_WORST_MM["A"], abs=0.005)


# ------------------------------------------------------------------------------- JA70 / JA71
#: JA71's worst |error| per phantom at the validator's defaults (R5-S3's run), pinned +-0.005 mm.
JA71_WORST_MM = {"A": 0.0155, "B": 0.0238, "C": 0.0115, "E": 0.0224}


@pytest.fixture(scope="module")
def ja71():
    """JA71's pre-registered check, at its defaults, as R5-S3 ran it once."""
    return H.validate_bias_estimator(open_base=True)


@pytest.mark.slow
def test_ja71_rows_a_to_f_and_the_verdict(ja71):
    """R5-S3: JA71's rows A-F; the verdict; the worst error per phantom to +-0.005 mm."""
    r = ja71
    assert r["open_base"] and r["band"] == "ja70" and r["tolerance_mm"] == 0.05
    assert r["phantoms"] == ["A", "B", "C", "D", "E", "F"]
    assert r["shifts_mm"] == [0.3, 0.5]
    count = {p: sum(x["phantom"] == p for x in r["rows"]) for p in "ABCDEF"}
    assert count == {"A": 48, "B": 144, "C": 16, "D": 0, "E": 32, "F": 0}
    for p in "ABCE":
        sel = [x for x in r["rows"] if x["phantom"] == p]
        assert {(x["border"], x["true_mm"]) for x in sel} == {
            (b, s) for b in ("endo", "epi") for s in (-0.5, -0.3, 0.3, 0.5)
        }
        assert all(np.isfinite(x["error_mm"]) for x in sel)
        worst = max(abs(x["error_mm"]) for x in sel)
        assert worst == r["by_phantom"][p]["worst_abs_error_mm"]
        assert worst == pytest.approx(JA71_WORST_MM[p], abs=0.005), p
        assert worst <= 0.05
    assert {tuple(x["grid_mm"]) for x in r["rows"] if x["phantom"] in "ABE"} == {
        (0.5, 0.5, 0.5),
        (0.4, 0.4, 0.5),
    }
    assert {x["variant"] for x in r["rows"] if x["phantom"] == "C"} == {"0.0", "23.0"}
    assert {x["variant"] for x in r["rows"] if x["phantom"] == "E"} == {"False", "True"}
    # D and F: JA70's band is JA61's, bit for bit, on every map and border
    assert r["by_phantom"]["D"]["unchanged"] and r["by_phantom"]["F"]["unchanged"]
    assert len([u for u in r["unchanged"] if u["phantom"] == "D"]) == 3 * 2
    assert len([u for u in r["unchanged"] if u["phantom"] == "F"]) == 2 * 2
    for p in "ABCDEF":
        assert r["by_phantom"][p]["min_epi_kept_share"] >= 0.5, p
    assert "normal" in r["by_phantom"]["E"]["forms"]
    assert r["checks"] == {
        "errors_within_tolerance": True,
        "D_unchanged": True,
        "F_unchanged": True,
        "epi_share_at_least_half": True,
        "nonplanar_branch_on_E": True,
    }
    # the verdict: JA71 passes
    assert r["passed"] is True and r["bias_guard_mm"] == 0.3


@pytest.mark.slow
def test_bias_guard_constant_follows_the_ja71_verdict(ja71):
    """R5-S3 / JA79: the constant is set from the verdict computed here at the default settings."""
    verdict = ja71["passed"]
    assert H.BIAS_GUARD_VALIDATED_MM == (0.3 if verdict else 0.5)


@pytest.mark.slow
def test_validate_bias_estimator_open_base(ja71):
    """R5-S4 (JA79): the capsule test runs at the default 3 offsets and asserts the verdict that
    sets the constant; B's worst is pinned (it was 0.0504 mm on JA61's band, R5-S3 replaces it)."""
    rows = [x for x in ja71["rows"] if x["phantom"] == "B"]
    assert len(rows) == 2 * 3 * 3 * 2 * 4  # grids x shapes x 3 offsets x borders x shifts
    assert len({tuple(x["origin_offset_mm"]) for x in rows}) == 2 * 3
    assert {(x["cavity_shift_mm"], x["tilt_deg"]) for x in rows} == {
        (0.0, 0.0),
        (2.3, 0.0),
        (2.3, 23.0),
    }
    worst = max(abs(x["error_mm"]) for x in rows)
    assert worst == pytest.approx(JA71_WORST_MM["B"], abs=0.005)
    assert ja71["passed"] is True
    assert H.BIAS_GUARD_VALIDATED_MM == (0.3 if ja71["passed"] else 0.5) == 0.3


def test_validate_bias_estimator_refuses_unknown_phantoms():
    with pytest.raises(ValueError):
        H.validate_bias_estimator(open_base=True, phantoms=("G",))
    with pytest.raises(ValueError):
        H.validate_bias_estimator(phantoms=("A",))


def test_d_band_is_bit_identical_to_ja61():
    """R5-S3 (JA70 step 5): the LA-capped heart has no opening, so the band is JA61's."""
    for cs, tilt in ((0.0, 0.0), (2.3, 0.0), (2.3, 23.0)):
        lab, aff = H.phantom(cavity_shift_mm=cs, tilt_deg=tilt)
        for border in ("endo", "epi"):
            band, rec = H.ja37_band(lab, SP, border, return_record=True)
            assert np.array_equal(band, H.ja37_band(lab, SP, border, cut_cap=False))
            assert rec["openings"] == [] and rec["kept_share"] == 1.0


@pytest.fixture(scope="module")
def phantom_e_curved():
    return H.outflow_phantom(curved=True)[0]


def test_on_e_an_opening_takes_the_normal_form(phantom_e_curved):
    """R5-S3: E's curved outflow is not planar, so JA70's 45 degree / 20 mm rule runs."""
    _, rec = H.ja37_band(phantom_e_curved, SP, "epi", return_record=True)
    assert [o["form"] for o in rec["openings"]] == ["normal"]
    assert rec["openings"][0]["rms_mm"] > H.CAP_PLANE_RMS_MM
    assert rec["openings"][0]["n_cap_faces"] > 0
    flat = H.outflow_phantom(curved=False)[0]
    _, rec = H.ja37_band(flat, SP, "epi", return_record=True)
    assert [o["form"] for o in rec["openings"]] == ["plane"]
    assert 0.5 <= rec["kept_share"] < 1.0


def test_ja70_parameters_are_the_ruling():
    assert (H.CAP_PLANE_RMS_MM, H.CAP_PLANE_MM, H.CAP_REACH_MM, H.CAP_ANGLE_DEG) == (
        1.0,
        1.0,
        20.0,
        45.0,
    )


@pytest.mark.parametrize("which", ["E-curved", "E-flat", "C"])
def test_a_lateral_epicardial_face_far_from_any_opening_is_never_removed(which, phantom_e_curved):
    """R5-S3: an epicardial face on label 0 more than 20 mm from every opening is no cap face, so
    no band voxel more than 20 + 3 mm from every open pool face is removed."""
    from scipy.spatial import cKDTree

    if which == "E-curved":
        lab = phantom_e_curved
    elif which == "E-flat":
        lab = H.outflow_phantom()[0]
    else:
        lab = H.phantom(cavity_shift_mm=2.3, la_gap_deg=H.JA71_C_LA_GAP_DEG)[0]
    cav, sol = H.borders(lab)
    pool = cKDTree(H._faces_to_zero(cav, lab)[0] * SP)
    cap, _ = H.cut_cap_faces(lab, SP)
    assert len(cap) and pool.query(cap)[0].max() <= H.CAP_REACH_MM + 1e-9
    # lateral epicardial faces on label 0 far from every opening exist here
    sf = H._faces_to_zero(sol, lab)[0] * SP
    assert (pool.query(sf)[0] > H.CAP_REACH_MM).sum() > 1000
    b61 = H.ja37_band(lab, SP, "epi", cut_cap=False)
    b70 = H.ja37_band(lab, SP, "epi")
    far = np.zeros(lab.shape, bool)
    idx = np.argwhere(b61)
    far[tuple(idx[pool.query(idx * SP)[0] > H.CAP_REACH_MM + H.JA37_BAND_MM].T)] = True
    assert far.sum() > 1000
    assert np.array_equal(b70[far], b61[far])


def _literal_band(lab, sp, border):
    """#219's remedy as worded (rejected by JA70): JA61's band less 3 mm about every solid face
    adjoining label 0."""
    sp = np.asarray(sp, float)
    _, sol = H.borders(lab)
    faces, _ = H._faces_to_zero(sol, lab)
    band = H.ja37_band(lab, sp, border, cut_cap=False)
    return H._drop_near(band, faces * sp, sp, H.JA37_BAND_MM)


@pytest.mark.slow
def test_the_literal_remedy_empties_the_epicardial_band():
    """R5-S3 (JA70): why the remedy as worded was not taken. With no aorta, pericardium or fat
    label the free epicardium adjoins label 0 everywhere, and no epicardial surface is left in
    the band on phantom A (every grid and wall): the estimate is undefined. JA70's keeps it."""
    for sp in H.OPEN_BASE_GRIDS:
        for rot, rough in H.E6_WALLS:
            Fc, Fs, base = H.e6_open_phantom(sp, rot, rough)
            lab = H.e6_labels(Fc, Fs, base)
            ref, test = (Fs < 0) & (base < 0), ((Fs - 0.5) < 0) & (base < 0)
            lit = _literal_band(lab, sp, "epi")
            assert H.surface_area(ref, sp, roi=lit) == 0.0
            assert np.isnan(H.signed_bias(ref, test, sp, roi=lit))
            assert H.surface_area(ref, sp, roi=H.ja37_band(lab, sp, "epi")) > 0


def test_compare_ja37_records_the_kept_share_and_the_forms():
    """JA70's record: the share of JA61's band kept and the form per opening, per border."""
    lab, aff = H.phantom()
    r = H.compare(lab, lab, affine=aff, with_sta=False, roi="ja37")
    assert r["band_kept_share_endo"] == 1.0 and r["band_forms_epi"] == ""
    lab = H.phantom(cavity_shift_mm=2.3, la_gap_deg=H.JA71_C_LA_GAP_DEG)[0]
    r = H.compare(lab, lab, affine=aff, with_sta=False, roi="ja37")
    assert r["band_forms_endo"] == r["band_forms_epi"] == "plane"
    assert 0.5 < r["band_kept_share_epi"] < 1.0
    assert "band_kept_share_epi" not in H.compare(lab, lab, affine=aff, with_sta=False)


# ------------------------------------------------------------------------------- JA79 docstrings
def test_signed_bias_docstring_carries_ja37s_disclosure():
    """R5-S4 (JA79)."""
    assert "0.09" in H.signed_bias.__doc__
    doc = " ".join(H.signed_bias.__doc__.split())
    assert "up to 0.05 mm low outward and 0.09 mm high inward near 0.3 mm (India E9)" in doc
    assert "is not known" not in doc.split("India E9")[0]


def test_module_states_the_0035_tolerance():
    """R5-S4 (JA65, JA79): the module says 0.035 mm, not 0.03 mm."""
    doc = " ".join(H.__doc__.split())
    assert "0.035 mm" in doc and "0.03 mm" not in doc


# ------------------------------------------------------------------------------- JA37 transfer
def _transfer_rows(diff, n=20, extra=()):
    rows = [
        {"bias_endo": 0.1 + diff, "bias_pp_endo": 0.1, "bias_epi": -0.2, "bias_pp_epi": -0.2 - diff}
        for _ in range(n)
    ]
    return rows + list(extra)


def test_transfer_check_median_under_the_limit_keeps_0_3():
    t = H.transfer_check(_transfer_rows(0.04))
    assert t["median_abs_diff_mm"]["endo"] == pytest.approx(0.04)
    assert t["median_abs_diff_mm"]["epi"] == pytest.approx(0.04)
    assert t["passed"] and t["bias_guard_mm"] == 0.3 and t["n_over_limit"] == 0
    # JA71 passed, so the open-base check no longer raises the guard
    assert t["bias_guard_applied_mm"] == H.BIAS_GUARD_VALIDATED_MM == 0.3


def test_transfer_check_median_over_the_limit_gives_0_5():
    t = H.transfer_check(_transfer_rows(0.06))
    assert not t["passed"] and t["bias_guard_mm"] == 0.5 and t["n_over_limit"] == 20
    rows = _transfer_rows(0.01)
    for r in rows[:8]:
        r["bias_endo"] += 0.2
    t = H.transfer_check(rows)
    assert t["passed"] and t["n_over_limit"] == 8  # the median holds; the count is reported


def test_transfer_check_refuses_fewer_than_20_rows():
    with pytest.raises(ValueError):
        H.transfer_check(_transfer_rows(0.01, n=19))
    bad = _transfer_rows(0.01)
    bad[3]["bias_pp_epi"] = float("nan")
    with pytest.raises(ValueError):
        H.transfer_check(bad)
    del bad[3]["bias_pp_epi"]
    with pytest.raises(ValueError):
        H.transfer_check(bad)


def test_transfer_check_ignores_row_21():
    far = {"bias_endo": 9.0, "bias_pp_endo": 0.0, "bias_epi": 9.0, "bias_pp_epi": 0.0}
    base = H.transfer_check(_transfer_rows(0.04))
    t = H.transfer_check(_transfer_rows(0.04, extra=[far] * 30))
    assert t == base
    nanrow = {"bias_endo": float("nan")}
    assert H.transfer_check(_transfer_rows(0.04, extra=[nanrow])) == base


def test_transfer_check_mixed_borders_fail_to_half_mm():
    """R5-S4 (JA79): endocardium within the limit, epicardium over it: the check fails."""
    rows = [
        {"bias_endo": 0.04, "bias_pp_endo": 0.0, "bias_epi": 0.06, "bias_pp_epi": 0.0}
        for _ in range(20)
    ]
    t = H.transfer_check(rows)
    assert t["median_abs_diff_mm"] == {"endo": pytest.approx(0.04), "epi": pytest.approx(0.06)}
    assert not t["passed"] and t["bias_guard_mm"] == 0.5 and t["bias_guard_applied_mm"] == 0.5


def test_transfer_check_median_of_exactly_the_limit_passes():
    """R5-S4 (JA79): a median of exactly 0.05 mm passes (<=)."""
    rows = [
        {"bias_endo": 0.05, "bias_pp_endo": 0.0, "bias_epi": -0.05, "bias_pp_epi": 0.0}
        for _ in range(20)
    ]
    t = H.transfer_check(rows)
    assert t["median_abs_diff_mm"] == {"endo": 0.05, "epi": 0.05}
    assert t["passed"] and t["bias_guard_mm"] == 0.3 and t["n_over_limit"] == 0
