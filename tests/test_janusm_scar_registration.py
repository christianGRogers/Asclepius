"""Janus-M path B, PS3-S1 to PS3-S5: the JA51 registration chain, the JA52 phase step and the JA53
QC cuts (``vault/JanusM/Judgements/Round 3 - paired-scar.md`` §9, ``registration.py``).

Each item's test is the one §9 names. Phantoms only (``tests/janusm_synth.py``): the static-chest
phantom (Juliet E6's heart in a chest whose lung hugs it), a 1 mm-grid bright-wall cavity, and
synthetic development records. No real, public or held-out case is opened; every QC cut here is a
test parameter, not a development value.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

from janusm import geometry as G
from janusm import scar as SC
from janusm.scar import registration as R
from janusm.scar.common import CarriedGeometry

sys.path.insert(0, str(Path(__file__).parent))
import janusm_synth as Y  # noqa: E402

HELD_OUT = "TotalSegmentator-cardiac__s0655"  # the guard's own positive control
FAST = dict(n_samples=10_000, maxfev=600)


# ------------------------------------------------------------------------------ fixtures
@pytest.fixture(scope="module")
def chest():
    ph = Y.StaticChest(gap_mm=5.0)
    geo = G.analyse(ph.labels, affine=ph.affine)
    assert geo.aha.segments is not None and not geo.aha.flagged
    ph.geo = geo
    ph.first = R.prepare_first_pass(ph.first_pass, ph.labels, ph.affine, geometry=geo)
    ph.r0 = R.carry(ph.first, R.Transform(np.eye(3), np.zeros(3), ph.first.centre),
                    ph.first_pass.shape, ph.affine)
    ph.aligned = ph.lie()
    ph.aligned_qc = R.qc(ph.aligned, ph.r0)
    return ph


@pytest.fixture(scope="module")
def tight(chest):
    """Cuts just above the aligned phantom's own values: any misregistration fails them."""
    v = np.maximum(chest.aligned_qc.values() * 1.2, 0.003)
    return R.QCCuts(*v)


def _tre(ph, stage, motion):
    p = ph.first.myo_world
    truth = ph.true_lie_points(motion, p)
    return float(np.linalg.norm(stage.transform.inverse(p) - truth, axis=1).mean())


@pytest.fixture(scope="module")
def shifted(chest, tight):
    """The static-chest phantom, heart shifted 4 mm (rigid motion only), through the whole chain."""
    motion = chest.shift(4.0, seed=11)
    lie = chest.lie(motion, seed=22)
    reg = R.register_lie(chest.first, lie, chest.affine, tight, **FAST)
    return motion, lie, reg


def _stage(reg, name):
    (s,) = [s for s in reg.stages if s.name == name]
    return s


# ------------------------------------------------------------------------------ PS3-S1
def test_ps3_s1_4mm_rigid_recovers_the_heart_10mm_rigid_does_not(chest, shifted):
    """PS3-S1: the static-chest phantom, heart shifted 4 mm: 4 mm rigid TRE < 0.5 mm, and 10 mm
    rigid TRE > 1.0 mm on the same case."""
    motion, _, reg = shifted
    assert reg.mask_mm == 4.0 and reg.fallback_mm == 10.0
    assert chest.first.mask_mm == R.MASK_DILATION_MM == 4.0
    names = [s.name for s in reg.stages]
    assert names == ["R0", "rigid", "affine", "rigid10"], names
    assert _tre(chest, reg.stages[0], motion) > 3.0
    tre4 = _tre(chest, _stage(reg, "rigid"), motion)
    tre10 = _tre(chest, _stage(reg, "rigid10"), motion)
    assert tre4 < 0.5, tre4
    assert tre10 > 1.0, tre10
    # the fallback is logged as its own stage, and did not replace the better 4 mm result
    log = json.loads(json.dumps(reg.log()))
    fb = [s for s in log["stages"] if s["name"] == "rigid10"][0]
    assert fb["mask_mm"] == 10.0 and not fb["kept"]
    assert reg.final.name in ("rigid", "affine")


def test_ps3_s1_mask_is_euclidean_and_a_parameter(chest):
    """The margin is a parameter, default 4.0 mm Euclidean (``edt <= margin``)."""
    from scipy import ndimage as ndi

    fp = chest.first
    # the same crop with a 0 mm margin is classes 1-4 themselves
    f0 = R.prepare_first_pass(chest.first_pass, chest.labels, chest.affine, geometry=chest.geo,
                              mask_mm=0.0, fallback_mm=None)
    heart = f0.mask
    assert f0.fallback_mask is None
    d = ndi.distance_transform_edt(~heart, sampling=fp.spacing)
    assert np.array_equal(fp.mask, d <= 4.0)
    assert np.array_equal(fp.fallback_mask, d <= 10.0)
    with pytest.raises(ValueError, match="margin"):
        R.prepare_first_pass(chest.first_pass, chest.labels, chest.affine, geometry=chest.geo,
                             mask_mm=40.0)


class _MockQC:
    """Mocked QC: hands out the next QC in ``seq`` on every call to ``R.qc``."""

    def __init__(self, seq):
        self.seq, self.calls = list(seq), 0

    def __call__(self, lie, carried, defs=R.DEFAULT_QC_DEFINITIONS):
        q = self.seq[min(self.calls, len(self.seq) - 1)]
        self.calls += 1
        return q


def _q(v):
    return R.QC(*v, blood_median=130.0, remote_median=90.0, n_wall=100, remote_sd=5.0)


CUTS = R.QCCuts(0.05, 0.05, 0.05, 0.2)
OK, BAD, WORSE = _q((0.01, 0.01, 0.01, 0.1)), _q((0.2, 0.1, 0.1, 0.3)), _q((0.4, 0.1, 0.1, 0.3))


@pytest.fixture
def mocked(chest, monkeypatch):
    """No optimiser: rigid and affine return identity, and every metric's mask is recorded."""
    masks = []
    real_metric = R._metric

    def metric(fp, *a, mask=None, **k):
        masks.append("10mm" if mask is fp.fallback_mask and mask is not None else "4mm")
        return real_metric(fp, *a, mask=mask, **k)

    monkeypatch.setattr(R, "_metric", metric)
    monkeypatch.setattr(R, "_rigid", lambda m, c, start, f: R.Transform(np.eye(3),
                                                                        start.translation, c))
    monkeypatch.setattr(R, "_affine_from", lambda m, rig, f: R.Transform(np.eye(3),
                                                                         rig.translation,
                                                                         rig.centre))

    def run(seq, **kw):
        mq = _MockQC(seq)
        monkeypatch.setattr(R, "qc", mq)
        reg = R.register_lie(chest.first, chest.aligned, chest.affine, CUTS, n_samples=2000, **kw)
        return reg, list(masks)

    return run


def test_ps3_s1_fallback_runs_only_when_the_4mm_stage_fails_qc(mocked):
    """PS3-S1: the fallback runs only when the 4 mm stage's QC fails (a mocked QC)."""
    reg, masks = mocked([OK])  # R0 passes
    assert [s.name for s in reg.stages] == ["R0"] and masks == ["4mm"]
    reg, masks = mocked([BAD, OK])  # 4 mm rigid passes: no affine, no fallback
    assert [s.name for s in reg.stages] == ["R0", "rigid"] and masks == ["4mm", "4mm"]
    # every 4 mm stage fails: one 10 mm rigid run, which passes and replaces the result
    reg, masks = mocked([BAD, BAD, BAD, OK])
    assert [s.name for s in reg.stages] == ["R0", "rigid", "affine", "rigid10"]
    assert masks[-1] == "10mm" and masks.count("10mm") == 1
    assert reg.final.name == "rigid10" and reg.qc_passed
    # the fallback fails QC and raises the normalised maximum: logged, not kept
    reg, _ = mocked([BAD, BAD, BAD, WORSE])
    assert reg.stages[-1].name == "rigid10" and not reg.stages[-1].kept
    assert reg.final.name == "rigid"
    # the fallback fails QC but lowers the normalised maximum: kept
    reg, _ = mocked([WORSE, WORSE, WORSE, BAD])
    assert reg.stages[-1].kept and reg.final.name == "rigid10" and not reg.qc_passed
    # PS4-S5: a mocked whole-image-motion case (no routing flag on the 4 mm stage) still runs the
    # fallback with JA82's skip on; the 4 mm phase check is logged either way
    for on in (False, True):
        reg, masks = mocked([BAD, BAD, BAD, OK], phase_check_before_fallback=on)
        assert [s.name for s in reg.stages] == ["R0", "rigid", "affine", "rigid10"]
        assert masks[-2:] == ["4mm", "10mm"] and reg.final.name == "rigid10"
        assert reg.phase_4mm is not None and not reg.phase_4mm.suspect and not reg.step5_skipped
        assert reg.stage_4mm.name == "rigid" and reg.graded_stage is reg.final
    # no fallback reached: no 4 mm check is logged
    reg, _ = mocked([BAD, OK])
    assert reg.phase_4mm is None and reg.stage_4mm is None


# ------------------------------------------------------------------------------ PS3-S2
def test_ps3_s2_rim_dark_rises_when_the_lie_cavity_shrinks(chest):
    """PS3-S2: a phantom with the LIE cavity shrunk 5 % has ``rim_dark`` above the aligned
    phantom's by >= 0.2."""
    shrunk = R.qc(chest.lie(e=0.05), chest.r0)
    aligned = chest.aligned_qc
    assert np.isfinite(aligned.rim_dark) and np.isfinite(shrunk.rim_dark)
    assert shrunk.rim_dark - aligned.rim_dark >= 0.2, (shrunk.rim_dark, aligned.rim_dark)
    assert aligned.blood_core == ">=2mm"


def test_ps3_s2_blood_median_is_2mm_inside_free_of_wall_partial_volume():
    """PS3-S2: a 1 mm-grid phantom with a bright wall shows the 2 mm blood median free of wall
    partial volume (equal to the true blood level within 1 %)."""
    img, cav, wall = Y.bright_wall_cavity(blood=130.0, wall=400.0)
    sp = np.ones(3)
    car = CarriedGeometry(myo=wall, cavity=cav, segments=np.zeros(cav.shape, np.int16),
                          u=np.full(cav.shape, np.nan), column=np.full(cav.shape, -1),
                          spacing=sp, affine=np.eye(4))
    q = R.qc(img, car)
    assert q.blood_core == ">=2mm" and q.n_blood >= R.MIN_BLOOD_CORE_VOXELS
    assert abs(q.blood_median - 130.0) <= 0.01 * 130.0, q.blood_median
    # the old one-voxel core is not free of the wall
    from janusm.scar.common import core_mask, smooth

    sm = smooth(img, sp)
    assert np.median(sm[core_mask(cav)]) > q.blood_median


def test_ps3_s2_small_cavity_falls_back_to_one_voxel_and_nan_fails_closed():
    img, cav, wall = Y.bright_wall_cavity(radius_mm=3.0, n=24)
    car = CarriedGeometry(myo=wall, cavity=cav, segments=np.zeros(cav.shape, np.int16),
                          u=np.full(cav.shape, np.nan), column=np.full(cav.shape, -1),
                          spacing=np.ones(3), affine=np.eye(4))
    core, depth = R.blood_core(cav, np.ones(3))
    assert depth == "1 voxel" and core.sum() > 0
    q = R.qc(img, car)
    assert not np.isfinite(q.rim_dark)  # no remote on this cavity
    assert not q.passes(R.QCCuts(1.0, 1.0, 1.0, 1.0))
    with pytest.raises(TypeError):
        R.QCCuts(0.1, 0.1, 0.1)  # max_rim_dark is required


# ------------------------------------------------------------------------------ PS3-S3
def test_ps3_s3_affine_rule_units():
    """PS3-S3 unit cases, amended by PS4-S3 for JA81 (rule (g)): sanity bound violated; then one
    case per clause (the normalised maximum rises; flat but fails QC with log det 0.01; flat with
    log det 0.03; fails QC on rigid but passes after affine with log det 0)."""
    cuts = R.QCCuts(0.01, 0.5, 0.5, 0.5)
    rig = _q((0.02, 0.3, 0.1, 0.1))  # normalised (2.0, 0.6, 0.2, 0.2): fails QC
    assert not rig.passes(cuts)
    passing = _q((0.005, 0.2, 0.1, 0.1))  # normalised max 0.5: passes QC
    flat = _q((0.02, 0.2, 0.1, 0.1))  # normalised max 2.0, as rigid's: fails QC
    eye = np.eye(3)

    def scaled(log_det):
        return np.eye(3) * np.exp(log_det / 3.0)

    assert R.AFFINE_SCALE_LOG_DET == 0.02
    # sanity bound violated, with a QC that would pass
    for m in (np.diag([1.2, 1.0, 1.0]),  # a scale beyond 15 %
              np.diag([1.1, 1.1, 1.1]),  # |log det| = 0.29 > 0.15, every scale within 15 %
              np.array([[1.0, 0.2, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])):  # shear 0.2
        assert not R.affine_sanity(m)["ok"], m
        assert not R.affine_accepted(m, passing, rig, cuts)
    # rotation is not penalised: the bound reads scale and shear only
    rot = R._rot([10.0, -5.0, 20.0])
    assert R.affine_sanity(rot @ np.diag([1.05, 0.97, 1.0]))["ok"]
    # (b') the maximum rises -> reject, even with a scale found
    assert not R.affine_accepted(scaled(0.03), _q((0.03, 0.2, 0.1, 0.1)), rig, cuts)
    # (c') the maximum is flat, fails QC and log det 0.01 -> reject
    assert not R.affine_accepted(scaled(0.01), flat, rig, cuts)
    # (c') the maximum is flat and log det 0.03 -> keep; the sign does not matter
    assert R.affine_accepted(scaled(0.03), flat, rig, cuts)
    assert R.affine_accepted(scaled(-0.03), flat, rig, cuts)
    # fails QC on rigid but passes after affine, log det 0 -> keep
    assert R.affine_accepted(eye, passing, rig, cuts)
    # (g) keeps by design what JA51 4(b) rejected: one normalised value rises, the maximum falls,
    # affine passes QC
    one_rises = _q((0.005, 0.2, 0.1, 0.11))
    assert not R.qc_rule_accepts(one_rises, rig, cuts)
    assert R.affine_accepted(eye, one_rises, rig, cuts)
    # the clauses are logged one by one
    r = R.affine_rule(scaled(0.01), flat, rig, cuts)
    assert r["sanity"] and r["max_not_raised"] and not r["passes_or_scaled"] and not r["kept"]
    # NaN rejects
    assert not R.affine_accepted(eye, _q((np.nan, 0.2, 0.1, 0.1)), rig, cuts)
    assert not R.affine_accepted(scaled(0.03), flat, _q((np.nan, 0.3, 0.1, 0.1)), cuts)


def test_ps3_s3_a_3_percent_scale_keeps_affine(chest, tight):
    """PS3-S3: a phantom with a 3 % scale keeps affine. PS4-S3: no longer a strict xfail (#243):
    JA81's rule (g) keeps it, and the last line asserts the sign the convention implies
    (``Transform`` maps the fixed LIE to the moving first pass, so a 3 % larger LIE heart reads
    log det ~ -3 log 1.03 = -0.089)."""
    motion = chest.scale(1.03)
    lie = chest.lie(motion, seed=23)
    reg = R.register_lie(chest.first, lie, chest.affine, tight, **FAST)
    aff = _stage(reg, "affine")
    assert aff.kept, aff.info
    assert aff.info["sanity"]["ok"] and aff.info["normalised_qc_rule"]
    assert reg.final.name in ("affine", "rigid10")
    assert _tre(chest, aff, motion) < _tre(chest, _stage(reg, "rigid"), motion)
    assert aff.info["sanity"]["log_det"] < -0.03  # the 3 % enlargement, with its correct sign


def test_ps3_s3_affine_that_increases_tre_is_rejected(chest, shifted):
    """PS3-S3: a rigid-only 4 mm shift phantom where affine increases TRE rejects it."""
    motion, _, reg = shifted
    rig, aff = _stage(reg, "rigid"), _stage(reg, "affine")
    assert _tre(chest, aff, motion) > _tre(chest, rig, motion)
    assert not aff.kept and reg.final is rig


# ------------------------------------------------------------------------------ PS3-S4
@pytest.fixture(scope="module")
def phase_cuts(chest):
    """rim_dark's phase cut a little above the aligned phantom's."""
    return R.QCCuts(1.0, 1.0, 1.0, 1.0, max_rim_dark_phase=chest.aligned_qc.rim_dark + 0.1)


def test_ps3_s4_phase_mismatch_is_flagged(chest, phase_cuts):
    """PS3-S4: phantoms at +5 % and -5 % cavity change are flagged (``rim_dark`` for +5 %, the edge
    offset for -5 %); the aligned phantom is not."""
    aligned = R.phase_step(chest.aligned, chest.r0, phase_cuts)
    assert aligned.evaluable and not aligned.suspect, aligned.summary()
    assert abs(aligned.edge_offset_mm) < R.EDGE_OFFSET_FLAG_MM
    shrunk = R.phase_step(chest.lie(e=0.05), chest.r0, phase_cuts)  # LIE cavity 5 % smaller
    assert "rim_dark" in shrunk.flags and "rim_dark" in shrunk.advisory_flags  # JA84: advisory
    larger = R.phase_step(chest.lie(e=-0.05), chest.r0, phase_cuts)  # LIE cavity 5 % larger
    assert larger.routing_flags == ["edge_offset"] and larger.suspect  # JA84: routing
    assert "rim_dark" not in larger.flags  # rim_dark cannot see a larger LIE cavity
    # JA44's canonical sign: the larger LIE cavity reads negative, the smaller one positive
    assert larger.edge_offset_mm < -R.EDGE_OFFSET_FLAG_MM
    assert shrunk.edge_offset_mm > aligned.edge_offset_mm
    for p in (aligned, shrunk, larger):
        s = json.loads(json.dumps(p.summary()))
        assert {"edge_offset_iqr_mm", "log_det_affine", "log_det_final"} <= set(s)


def test_ps3_s4_not_evaluable_without_blood_contrast(chest, phase_cuts):
    """JA52: not evaluable when blood - remote < 2 robust SD; no flag then."""
    tab = dict(chest.jr.LIE)
    for k in (2, 3, 4, 12):
        tab[k] = tab[1]  # blood at the myocardium's level
    flat = chest.lie(e=0.05, tab=tab)
    p = R.phase_step(flat, chest.r0, phase_cuts)
    assert not p.evaluable and not p.suspect and p.contrast < R.MIN_PHASE_CONTRAST_SD


def test_ps3_s4_failure_rate_ignores_phase_suspect():
    """PS3-S4: ``failure_rate`` ignores ``phase_suspect``."""
    st = [SC.PASSED] * 9 + [SC.NOT_GRADED]
    assert R.failure_rate(st + [SC.PHASE_SUSPECT] * 5) == pytest.approx(0.1)
    assert R.seal_grading_allowed(st + [SC.PHASE_SUSPECT] * 50)
    # a routed patient is phase suspect whatever the check says (JA85; PS4-S4 has every row)
    for checks in ([], [False], [True]):
        assert R.status_from_checks(checks, phase_flag=True,
                                    phase_source=R.PHASE_INFERRED) == SC.PHASE_SUSPECT
    # JA52 stop rule: a phase-suspect share above 20 % goes to the lead
    assert not R.phase_suspect_needs_report([SC.PASSED] * 8 + [SC.PHASE_SUSPECT] * 2)
    assert R.phase_suspect_needs_report([SC.PASSED] * 7 + [SC.PHASE_SUSPECT] * 3)
    with pytest.raises(ValueError):
        R.failure_rate([SC.PHASE_SUSPECT])


def test_ps3_s4_phase_suspect_stops_further_registration(chest, phase_cuts, monkeypatch):
    lie = chest.lie(e=-0.05)  # PS4-S4: the edge offset routes (rim_dark is advisory)
    cuts = R.QCCuts(1.0, 1.0, 1.0, 1.0, max_rim_dark_phase=phase_cuts.rim_dark_phase)
    reg = R.register_lie(chest.first, lie, chest.affine, cuts, n_samples=2000,
                         phase_source=R.PHASE_INFERRED)
    assert [s.name for s in reg.stages] == ["R0"]  # QC passes these loose cuts
    assert reg.phase_suspect and reg.status == SC.PHASE_SUSPECT
    assert reg.phase_route == R.ROUTE_FLAG_ONLY
    assert reg.record_reader_check(False) == SC.PHASE_SUSPECT
    assert not reg.reregistration_allowed
    with pytest.raises(ValueError, match="phase"):
        R.register_lie(chest.first, lie, chest.affine, cuts, attempt=2, initial_shift_mm=[1, 0, 0],
                       previous_checks=[False], previous_phase_suspect=True)
    log = json.loads(json.dumps(reg.log()))
    assert log["status"] == SC.PHASE_SUSPECT and log["phase"]["phase_flag"]
    assert log["phase"]["log_det_final"] == 0.0 and log["phase"]["log_det_affine"] is None


# ------------------------------------------------------------------------------ PS3-S5
def _records(n=900, seed=0, fails=0):
    """Synthetic development records with known quantiles (case ids are made-up phantom ids).

    Reader-passed: fat-like ~ U(0, 0.04) (p95 0.038, flat); blood-like ~ U(0, 0.02 c) (p95
    0.019 c, rising with contrast c ~ U(2, 10)); brighter ~ U(0, 0.2 / c) (p95 0.19 / c,
    falling); rim_dark ~ U(0, 0.1) when phase-matched (80 %), U(0, 0.5) otherwise. Protocols: A
    (600), B (290), C (10, below 15: pooled). Reader fails: the three shares far above their cuts,
    rim_dark drawn as for matched passes (uncorrelated with the fail).
    """
    rng = np.random.default_rng(seed)
    out = []
    keys = ["A"] * 600 + ["B"] * 290 + ["C"] * 10
    for i in range(n):
        c = rng.uniform(2, 10)
        matched = rng.random() < 0.8
        qc = {
            "fatlike": rng.uniform(0, 0.04),
            "bloodlike": rng.uniform(0, 0.02 * c),
            "brighter_than_blood": rng.uniform(0, 0.2 / c),
            "rim_dark": rng.uniform(0, 0.1 if matched else 0.5),
        }
        out.append({"case_id": f"phantom-{i}", "qc": qc, "reader_pass": True,
                    "protocol": keys[i % len(keys)], "contrast": c, "phase_matched": matched})
    for j in range(fails):
        c = rng.uniform(2, 10)
        qc = {"fatlike": 0.2, "bloodlike": 0.5, "brighter_than_blood": 0.5,
              "rim_dark": rng.uniform(0, 0.1)}
        out.append({"case_id": f"phantom-f{j}", "qc": qc, "reader_pass": False,
                    "protocol": "A", "contrast": c, "phase_matched": True})
    return out


def test_ps3_s5_known_quantiles_reproduce_the_cuts():
    """PS3-S5: synthetic records with known quantiles reproduce the cuts."""
    recs = _records()
    f = R.fit_qc_cuts(recs)
    assert set(f.protocols) == {R.POOLED, "A", "B"}  # C has fewer than 15: pooled
    assert f.protocol_cuts("C") is f.protocols[R.POOLED]
    assert f.gate == (True,) * 4 and f.n_reader_failed == 0  # no fail: drop rule cannot run
    for key in ("A", "B", R.POOLED):
        p = f.protocols[key]
        for c in (4.0, 6.0, 8.0):
            assert p.fatlike.at(c) == pytest.approx(0.038, rel=0.12)
            assert p.bloodlike.at(c) == pytest.approx(0.019 * c, rel=0.15)
            assert p.brighter_than_blood.at(c) == pytest.approx(0.19 / c, rel=0.2)
        # the bands are monotone
        assert np.all(np.diff(p.bloodlike.cut) >= 0)
        assert np.all(np.diff(p.brighter_than_blood.cut) <= 0)
        # rim_dark: p95 over all reader-passed (a 0.8 / 0.2 mixture: 0.375); phase cut over
        # phase-matched only (0.095)
        assert p.rim_dark == pytest.approx(0.375, rel=0.12)
        assert p.rim_dark_phase == pytest.approx(0.095, rel=0.06)
    cuts = f.cuts_for("A", 6.0)
    assert cuts.max_bloodlike == pytest.approx(f.protocols["A"].bloodlike.at(6.0))
    assert cuts.rim_dark_phase == f.protocols["A"].rim_dark_phase
    assert np.isnan(f.cuts_for("A", np.nan).max_fatlike)  # no contrast: the shares fail


def test_ps3_s5_value_uncorrelated_with_reader_fails_is_dropped():
    """PS3-S5: a value uncorrelated with reader fails is dropped."""
    f = R.fit_qc_cuts(_records(fails=100))
    assert f.gate == (True, True, True, False), f.catch_rate
    assert f.catch_rate[3] < R.MIN_CATCH_RATE <= min(f.catch_rate[:3])
    cuts = f.cuts_for("A", 5.0)
    assert cuts.gate == (True, True, True, False)
    # a dropped value no longer stops R0, but stays logged
    q = _q((0.0, 0.0, 0.0, 0.99))
    assert q.passes(cuts) and q.rim_dark == 0.99


def test_ps3_s5_a_non_guarded_id_raises():
    """PS3-S5: a non-guarded id raises (the JA12 guard first; fails closed)."""
    from janusm.guard import HeldOutError

    recs = _records(n=60)
    recs[5]["case_id"] = HELD_OUT
    with pytest.raises(HeldOutError):
        R.fit_qc_cuts(recs)
    recs[5]["case_id"] = None
    with pytest.raises(ValueError, match="case_id"):
        R.fit_qc_cuts(recs)


def test_ps3_s5_frozen_json_and_provisional_cuts(tmp_path):
    """PS3-S5 output: a frozen JSON for ``configs/janusm/paired-r2.json``; provisional cuts from
    ``bench_lie/scores_v3.json`` (PS4-S6; v2's ``scores.json`` is refused)."""
    f = R.fit_qc_cuts(_records(fails=100))
    path = R.save_qc_cuts(f, tmp_path / "paired-r2.json")
    text = path.read_text()
    assert "phantom-" not in text  # counts only, no case id
    d = json.loads(text)
    assert d["frozen"] and d["gate"]["rim_dark"] is False
    with pytest.raises(FileExistsError):
        R.save_qc_cuts(f, path)  # frozen cuts are never moved
    g = R.load_qc_cuts(path)
    for key, c in (("A", 3.3), ("B", 7.1), ("C", 5.0)):
        assert g.cuts_for(key, c) == f.cuts_for(key, c)
    # provisional (PS4-S6, JA83): the v3 benchmark's registered-case cuts at the matching blood
    bench = json.loads(R.BENCH_SCORES.read_text())["qc_cuts_registered"]["0|equal|5"]
    p = R.load_provisional_qc_cuts(blood="equal", cnr=5, half=0)
    assert (p.max_fatlike, p.max_bloodlike, p.max_brighter_than_blood, p.max_rim_dark) == (
        bench["fatlike"], bench["bloodlike"], bench["brighter_than_blood"], bench["rim_dark"])
    both = R.load_provisional_qc_cuts(blood="equal", cnr=5)
    assert both.max_fatlike >= p.max_fatlike
    with pytest.raises(KeyError):
        R.load_provisional_qc_cuts(blood="none", cnr=5)


def test_fitted_cuts_drive_the_chain(chest):
    """register_lie takes the fitted cuts, read at the patient's own contrast."""
    f = R.fit_qc_cuts(_records())
    reg = R.register_lie(chest.first, chest.aligned, chest.affine, f, protocol="A",
                         n_samples=2000)
    c = chest.aligned_qc.contrast
    assert reg.cuts == f.cuts_for("A", c)
    assert reg.log()["protocol"] == "A"
