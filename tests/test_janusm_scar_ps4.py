"""Janus-M path B, PS4-S2 and PS4-S4 to PS4-S7: phase grading and routing, the phase check before
the fallback, registered provisional cuts, and the affine optimiser variant
(``vault/JanusM/Judgements/Round 4 - paired-scar.md`` §9, JA81-JA85). PS4-S3's tests are the
PS3-S3 tests in ``test_janusm_scar_registration.py``, amended as §9 says.

Each item's test is the one §9 names. Phantoms only (``tests/janusm_synth.py``), and for PS4-S6 the
committed ``bench_lie/results_v3.jsonl.gz`` rows of the benchmark's own phantom heart (no download,
no real heart). Every QC cut here is a test parameter unless it is read from the committed
benchmark file.
"""

from __future__ import annotations

import gzip
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest

from janusm import geometry as G
from janusm import scar as SC
from janusm.scar import registration as R
from janusm.scar import scar0 as S

sys.path.insert(0, str(Path(__file__).parent))
import janusm_synth as Y  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
BENCH = REPO / "experiments" / "JanusM" / "bench_lie"
FAST = dict(n_samples=10_000, maxfev=600)


@pytest.fixture(scope="module")
def chest():
    ph = Y.StaticChest(gap_mm=5.0)
    geo = G.analyse(ph.labels, affine=ph.affine)
    assert geo.aha.segments is not None and not geo.aha.flagged
    ph.first = R.prepare_first_pass(ph.first_pass, ph.labels, ph.affine, geometry=geo)
    ph.r0 = R.carry(ph.first, R.Transform(np.eye(3), np.zeros(3), ph.first.centre),
                    ph.first_pass.shape, ph.affine)
    ph.aligned = ph.lie()
    ph.aligned_qc = R.qc(ph.aligned, ph.r0)
    return ph


@pytest.fixture(scope="module")
def tight(chest):
    """Cuts just above the aligned phantom's own values: any misregistration fails them."""
    return R.QCCuts(*np.maximum(chest.aligned_qc.values() * 1.2, 0.003))


@pytest.fixture(scope="module")
def phase_cuts(chest):
    """Loose QC (R0 passes); rim_dark's phase cut a little above the aligned phantom's."""
    return R.QCCuts(1.0, 1.0, 1.0, 1.0, max_rim_dark_phase=chest.aligned_qc.rim_dark + 0.1)


def _tre(ph, stage, motion):
    p = ph.first.myo_world
    truth = ph.true_lie_points(motion, p)
    return float(np.linalg.norm(stage.transform.inverse(p) - truth, axis=1).mean())


def _stage(reg, name):
    (s,) = [s for s in reg.stages if s.name == name]
    return s


# ------------------------------------------------------------------------------ PS4-S2
def _synthetic_registration(chest, *, phase_source, flag):
    """A registration whose final stage is ``rigid10`` (carried 6 mm off) after a 4 mm ``rigid``
    stage that lies on the heart."""
    good = chest.r0
    off = R.Transform(np.eye(3), np.array([6.0, 0.0, 0.0]), chest.first.centre)
    bad = R.carry(chest.first, off, chest.first_pass.shape, chest.affine)
    eye = R.Transform(np.eye(3), np.zeros(3), chest.first.centre)
    q = chest.aligned_qc
    st_r0 = R.Stage(R.STAGE_R0, eye, q, False, 0.0, 0.0)
    st_rig = R.Stage(R.STAGE_RIGID, eye, q, False, 0.0, 0.0)
    st_fb = R.Stage(R.STAGE_FALLBACK, off, q, False, 0.0, 0.0)
    phase = R.PhaseCheck(True, 8.0, 0.1, 0.2, 1.0 if flag else 0.0, 0.6, 0.1, None, 0.0,
                         routing_flags=["edge_offset"] if flag else [])
    return R.Registration(
        stages=[st_r0, st_rig, st_fb], final=st_fb, carried=bad, cuts=R.QCCuts(1, 1, 1, 1),
        attempt=1, shift_mm=np.zeros(3), initial_shift_mm=None, phase=phase,
        stage_4mm=st_rig, carried_4mm=good, phase_source=phase_source,
    ), good, bad


def test_ps4_s2_phase_suspect_rigid10_registration_is_graded_on_its_rigid_stage(chest):
    """PS4-S2: a synthetic registration whose final stage is ``rigid10`` but which is
    ``phase_suspect`` is graded on its rigid stage; ``for_scoring`` carries the stratum and the
    route."""
    assert SC.PHASE_SUSPECT in SC.FINAL_STATUSES
    lie = chest.aligned
    for source, flag, route in ((R.PHASE_DICOM_UNMATCHED, False, "confirmed"),
                                (R.PHASE_INFERRED, True, "flag_only")):
        reg, good, bad = _synthetic_registration(chest, phase_source=source, flag=flag)
        assert reg.final.name == "rigid10"
        assert reg.status == SC.PHASE_SUSPECT and reg.phase_route == route
        assert reg.graded_stage.name == "rigid" and reg.graded_carried is good
        out = S.scar0_registered(lie, reg, tau=0.05)
        ref = S.scar0(lie, good, status=SC.PHASE_SUSPECT, phase_route=route, tau=0.05)
        wrong = S.scar0(lie, bad, status=SC.PHASE_SUSPECT, phase_route=route, tau=0.05)
        assert out.segments == ref.segments and out.remote == ref.remote
        assert out.segments != wrong.segments  # the fallback's geometry is not the one graded
        got = out.for_scoring("P-J", "E-D")
        assert got.strata >= {"phase_unmatched"} and got.phase_route == route
        bins, shares = got  # still unpacks as before
        assert np.array_equal(bins, ref.for_scoring("P-J", "E-D").kim_bin)
        table = out.table("P-J", "E-D")
        assert table["phase_route"] == route and table["strata"] == ["phase_unmatched"]
    # an ordinary patient is graded on its final stage, with no stratum and no route
    reg, _, bad = _synthetic_registration(chest, phase_source=R.PHASE_DICOM_MATCHED, flag=True)
    reg.record_reader_check(True)
    assert reg.status == SC.PASSED and reg.phase_route is None
    assert reg.graded_stage is reg.final and reg.graded_carried is bad
    got = S.scar0_registered(lie, reg, tau=0.05).for_scoring("P-J", "E-D")
    assert got.strata == frozenset() and got.phase_route is None
    # a phase-suspect patient needs its route; only it may carry one
    with pytest.raises(ValueError, match="route"):
        S.scar0(lie, chest.r0, status=SC.PHASE_SUSPECT)
    with pytest.raises(ValueError, match="route"):
        S.scar0(lie, chest.r0, status=SC.PASSED, phase_route="confirmed")


# ------------------------------------------------------------------------------ PS4-S4
def test_ps4_s4_one_case_per_ja85_row():
    """PS4-S4: one synthetic case per JA85 row."""
    f = R.status_from_checks
    um, ma, inf = R.PHASE_DICOM_UNMATCHED, R.PHASE_DICOM_MATCHED, R.PHASE_INFERRED
    # 1. DICOM phases differ: stratum, confirmed, whatever the flag, mark or check
    for flag in (False, True):
        for checks in ([], [True], [False]):
            st = f(checks, phase_flag=flag, phase_source=um)
            assert (st, st.route) == (SC.PHASE_SUSPECT, R.ROUTE_CONFIRMED)
    # 2. DICOM-matched or inferred, the reader marks phase: stratum, confirmed
    for src in (ma, inf):
        for flag in (False, True):
            st = f([True], phase_flag=flag, phase_source=src, reader_phase_mark=True)
            assert (st, st.route) == (SC.PHASE_SUSPECT, R.ROUTE_CONFIRMED)
    # 3. inferred, edge flag, no mark: stratum on the flag alone (charged to yield)
    for checks in ([], [True], [False]):
        st = f(checks, phase_flag=True, phase_source=inf)
        assert (st, st.route) == (SC.PHASE_SUSPECT, R.ROUTE_FLAG_ONLY)
    # 4. DICOM-matched, edge flag, no mark: an ordinary patient, the reader check decides
    for checks, want in (([], SC.AWAITING), ([True], SC.PASSED), ([False], SC.AWAITING),
                         ([False, True], SC.REREGISTERED), ([False, False], SC.NOT_GRADED)):
        st = f(checks, phase_flag=True, phase_source=ma)
        assert (st, st.route) == (want, None)
    # 5. no flag, no mark: ordinary
    for src in (ma, inf, None):
        st = f([True], phase_flag=False, phase_source=src)
        assert (st, st.route) == (SC.PASSED, None)
    # a flag with no phase source recorded cannot be routed: it fails closed (not scoreable)
    assert f([True], phase_flag=True) == SC.AWAITING
    with pytest.raises(ValueError, match="phase_source"):
        f([True], phase_source="dicom")
    # failure_rate and phase_suspect_share keep ignoring / counting phase_suspect as before
    st = [SC.PASSED] * 9 + [SC.NOT_GRADED] + [f([], phase_source=um)] * 5
    assert R.failure_rate(st) == pytest.approx(0.1)
    assert R.phase_suspect_share(st) == pytest.approx(5 / 15)


def test_ps4_s4_limbo_case_ends_passed(chest, phase_cuts):
    """PS4-S4: the limbo case (DICOM-matched, edge flag, no reader mark, check passes) ends
    ``passed``, and is scored as an ordinary patient."""
    lie = chest.lie(e=-0.05)  # LIE cavity 5 % larger: the edge offset flags
    reg = R.register_lie(chest.first, lie, chest.affine, phase_cuts, n_samples=2000,
                         phase_source=R.PHASE_DICOM_MATCHED)
    assert reg.phase_flag and reg.phase.routing_flags == ["edge_offset"]
    assert reg.status == SC.AWAITING and not reg.phase_suspect
    assert reg.record_reader_check(True) == SC.PASSED and reg.phase_route is None
    log = json.loads(json.dumps(reg.log()))
    assert log["status"] == SC.PASSED and log["phase"]["phase_flag"]  # the flag is logged
    assert log["phase_source"] == R.PHASE_DICOM_MATCHED and log["phase_route"] is None
    out = S.scar0_registered(lie, reg, tau=0.05).for_scoring("P-G", "E-V")
    assert out.strata == frozenset()
    # the same patient, the reader marking phase: confirmed stratum
    reg2 = R.register_lie(chest.first, lie, chest.affine, phase_cuts, n_samples=2000,
                          phase_source=R.PHASE_DICOM_MATCHED)
    assert reg2.record_reader_check(True, phase_mark=True) == SC.PHASE_SUSPECT
    assert reg2.phase_route == R.ROUTE_CONFIRMED and not reg2.reregistration_allowed


def test_ps4_s4_rim_dark_only_flag_never_yields_phase_suspect(chest, phase_cuts):
    """PS4-S4: a ``rim_dark``-only flag never yields ``phase_suspect``."""
    shrunk = chest.lie(e=0.05)
    # the edge-offset cut out of reach: only rim_dark can fire
    cuts = R.QCCuts(1.0, 1.0, 1.0, 1.0, max_rim_dark_phase=phase_cuts.rim_dark_phase,
                    max_edge_offset_mm=50.0)
    p = R.phase_step(shrunk, chest.r0, cuts)
    assert p.advisory_flags == ["rim_dark"] and p.routing_flags == [] and not p.suspect
    for src in (R.PHASE_DICOM_MATCHED, R.PHASE_INFERRED, None):
        reg = R.register_lie(chest.first, shrunk, chest.affine, cuts, n_samples=2000,
                             phase_source=src)
        assert reg.phase.advisory_flags == ["rim_dark"] and not reg.phase_flag
        for checks in ([], [True], [False]):
            st = R.status_from_checks(checks, phase_flag=reg.phase_flag, phase_source=src)
            assert st != SC.PHASE_SUSPECT and st.route is None
        assert reg.record_reader_check(True) == SC.PASSED
        assert json.loads(json.dumps(reg.log()))["phase"]["advisory_flags"] == ["rim_dark"]


# ------------------------------------------------------------------------------ PS4-S5
def test_ps4_s5_smaller_cavity_with_a_4mm_shift_ends_on_the_4mm_stage(chest, tight):
    """PS4-S5: a static-chest phantom with a 5 % smaller LIE cavity and a 4 mm shift ends on the
    4 mm stage, with no ``rigid10`` in ``stages`` (JA82's skip, on). With the skip off -- the
    default, since the acceptance replay missed -- step 5 runs as shipped, and the 4 mm check is
    logged either way."""
    motion = chest.shift(4.0, seed=11)
    lie = chest.lie(motion, e=0.05, seed=22)
    reg = R.register_lie(chest.first, lie, chest.affine, tight, phase_check_before_fallback=True,
                         phase_source=R.PHASE_INFERRED, **FAST)
    names = [s.name for s in reg.stages]
    assert "rigid10" not in names and names[:2] == ["R0", "rigid"], names
    assert reg.final.name in ("rigid", "affine") and reg.step5_skipped
    assert reg.phase_4mm is reg.phase and reg.phase.routing_flags == ["edge_offset"]
    assert reg.status == SC.PHASE_SUSPECT and reg.graded_stage is reg.final
    assert _tre(chest, reg.final, motion) < 1.0
    log = json.loads(json.dumps(reg.log()))
    assert log["step5_skipped"] and log["graded_stage"] == reg.final.name
    assert log["phase_4mm"]["phase_flag"] and log["phase_route"] == R.ROUTE_FLAG_ONLY
    # the default: step 5 as shipped (JA51), the 4 mm check logged; the stratum patient is still
    # graded on its 4 mm stage, never on the fallback (JA85)
    off = R.register_lie(chest.first, lie, chest.affine, tight, phase_source=R.PHASE_INFERRED,
                         **FAST)
    assert [s.name for s in off.stages][-1] == "rigid10" and not off.step5_skipped
    assert off.phase_4mm is not None and off.phase_4mm.suspect
    if off.phase_suspect:
        assert off.graded_stage.name in ("rigid", "affine")


# ------------------------------------------------------------------------------ PS4-S6
def _bench_score():
    spec = importlib.util.spec_from_file_location("bench_lie_score", BENCH / "score.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_ps4_s6_v2_scores_json_is_refused():
    """PS4-S6: loading v2's ``scores.json`` raises; v3's declares the shipped QC definitions."""
    with pytest.raises(ValueError, match="qc_definitions"):
        R.load_provisional_qc_cuts(BENCH / "scores.json", blood="equal", cnr=5)
    assert R.BENCH_SCORES.name == "scores_v3.json"
    d = json.loads(R.BENCH_SCORES.read_text())
    assert d["qc_definitions"] == R.QC_DEFINITIONS == "janusm.scar.registration 1.1.0"
    p = R.load_provisional_qc_cuts(blood="equal", cnr=5, half=0)
    reg = d["qc_cuts_registered"]["0|equal|5"]
    assert (p.max_fatlike, p.max_bloodlike, p.max_brighter_than_blood, p.max_rim_dark) == (
        reg["fatlike"], reg["bloodlike"], reg["brighter_than_blood"], reg["rim_dark"])
    assert p.rim_dark_phase == d["rim_dark_phase_cuts_ja53"]["0|equal|5"]
    assert p.max_edge_offset_mm == R.EDGE_OFFSET_FLAG_MM
    both = R.load_provisional_qc_cuts(blood="equal", cnr=5)
    assert both.max_fatlike >= p.max_fatlike
    with pytest.raises(KeyError):
        R.load_provisional_qc_cuts(blood="none", cnr=5)


def test_ps4_s6_benchmark_phantom_rigid_case_passes_at_rigid4_and_fails_at_r0():
    """PS4-S6: on the committed v3 rows, the benchmark phantom's ``rigid`` case at CNR 5 passes the
    loaded cuts at its rigid4 stage and fails them at R0, at every blood level."""
    score = _bench_score()
    with gzip.open(BENCH / "results_v3.jsonl.gz", "rt") as fh:
        rows = [json.loads(line) for line in fh]
    rows = [r for r in rows if r.get("heart") == "phantom" and r.get("motion") == "rigid"
            and r.get("cnr") == 5 and "arms" in r]
    assert sorted(r["blood"] for r in rows) == ["above", "below", "equal"]

    def q(arm):
        s = arm["shipped"]
        return R.QC(*[np.nan if s.get(n) is None else float(s[n]) for n in R.QC_NAMES],
                    blood_median=float(s["blood_median"]),
                    remote_median=float(s["remote_median"]), n_wall=1,
                    remote_sd=float(s["remote_sd"]))

    for r in rows:
        cuts = R.load_provisional_qc_cuts(blood=r["blood"], cnr=5, half=score.half("phantom"))
        assert q(r["arms"]["rigid4"]).passes(cuts), r["blood"]
        assert not q(r["arms"]["R0"]).passes(cuts), r["blood"]
        assert r["arms"]["rigid4"]["tre_mm"] < 0.25


# ------------------------------------------------------------------------------ PS4-S7
@pytest.fixture(scope="module")
def variant_runs(chest):
    """Each phantom through every stage (no cut passes), shipped optimiser and the variant."""
    nothing = R.QCCuts(0.0, 0.0, 0.0, 0.0)
    out = {}
    for name, motion in (("aligned", chest.identity), ("shift4", chest.shift(4.0, seed=11)),
                         ("scale3", chest.scale(1.03))):
        lie = chest.lie(motion, seed=22)
        out[name] = (motion, {
            v: R.register_lie(chest.first, lie, chest.affine, nothing, affine_variant=v, **FAST)
            for v in (None, "scaled")
        })
    return out


def test_ps4_s7_variant_affine_tre_no_worse_than_rigid_on_aligned_and_shifted(chest,
                                                                              variant_runs):
    """PS4-S7: on the aligned and the 4 mm-shift phantoms, the variant's affine TRE is <= rigid's
    + 0.1 mm."""
    tre_aff, tre_rig = [], []
    for name in ("aligned", "shift4"):
        motion, runs = variant_runs[name]
        reg = runs["scaled"]
        assert _stage(reg, "affine").info["optimiser_variant"] == "scaled"
        tre_aff.append(_tre(chest, _stage(reg, "affine"), motion))
        tre_rig.append(_tre(chest, _stage(reg, "rigid"), motion))
    assert np.median(tre_aff) <= np.median(tre_rig) + 0.1, (tre_aff, tre_rig)
    for a, r in zip(tre_aff, tre_rig):
        assert a <= r + 0.1, (tre_aff, tre_rig)


def test_ps4_s7_variant_keeps_the_sanity_bound_and_lowers_tre_on_a_3_percent_scale(chest,
                                                                                  variant_runs):
    """PS4-S7: on the 3 % scale phantom the variant keeps the sanity bound and lowers TRE."""
    motion, runs = variant_runs["scale3"]
    aff, rig = _stage(runs["scaled"], "affine"), _stage(runs["scaled"], "rigid")
    assert aff.info["sanity"]["ok"], aff.info["sanity"]
    assert _tre(chest, aff, motion) < _tre(chest, rig, motion)
    assert aff.info["sanity"]["log_det"] < -0.03  # the enlargement, with JA81's sign


def test_ps4_s7_default_path_is_unchanged(chest, variant_runs, monkeypatch):
    """PS4-S7: the default path does not touch the variant, and its affine stage is the shipped
    optimiser's result exactly."""
    motion, runs = variant_runs["shift4"]
    reg = runs[None]
    assert "optimiser_variant" not in _stage(reg, "affine").info

    def boom(*a, **k):
        raise AssertionError("the variant ran on the default path")

    monkeypatch.setattr(R, "_affine_scaled", boom)
    lie = chest.lie(motion, seed=22)
    again = R.register_lie(chest.first, lie, chest.affine, R.QCCuts(0.0, 0.0, 0.0, 0.0), **FAST)
    for a, b in zip(reg.stages, again.stages):
        assert a.name == b.name
        assert np.array_equal(a.transform.matrix, b.transform.matrix)
        assert np.array_equal(a.transform.translation, b.transform.translation)
    with pytest.raises(ValueError, match="affine_variant"):
        R.register_lie(chest.first, lie, chest.affine, R.QCCuts(1, 1, 1, 1), affine_variant="x")
