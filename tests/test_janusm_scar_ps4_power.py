"""Round 4 paired-scar §9, power and scoring: PS4-S8 (JA86) and PS4-S9 (JA85).

Ruling: ``vault/JanusM/Judgements/Round 4 - paired-scar.md``. Each test below is one of §9's named
checks, in §9's order. Synthetic data only: simulated studies and hand-built patients, no image,
case or identifier.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from janusm.scar import PASSED
from janusm.scar import power as P
from janusm.scar import registration as R
from janusm.scar import scoring as S

GOLF_SIZE = P.expected_scar_segments(1.0, 3.0)  # 3.99 scarred segments per scar patient
KILO_SIZE = P.kilo_segments_per_scar_patient()  # 3.25


def _seal(**kw):
    base = dict(
        p_fail=0.02,
        segs_per_scar_patient=GOLF_SIZE,
        extent_error=0.25,
        sens_by_bin=P.GOLF_SENS_BY_BIN,
        enrich=0.7,
        tau=P.CLUSTERING["weak"],
    )
    return P.seal_size(**{**base, **kw})


# -------------------------------------------------------------------------------------------------
# PS4-S8 — seal_size: stability, stated power, phase share (JA86)


def test_ps4_s8_defaults_to_2000_sims():
    import inspect

    assert inspect.signature(P.seal_size).parameters["sims"].default == 2000 == P.SEAL_SIMS


def test_ps4_s8_interp_n80_follows_golf_power_r4_table():
    curve = {120: 0.70, 140: 0.90, 160: 0.95}
    assert P.interp_n80(curve) == pytest.approx(130.0)
    assert P.interp_n80({120: 0.85, 140: 0.9}) == 120.0  # at or below the grid's first point
    assert P.interp_n80({120: 0.5, 140: 0.6}) is None
    lo = P.interp_n80(curve, shift=+2, sims=2000)
    hi = P.interp_n80(curve, shift=-2, sims=2000)
    assert lo < 130.0 < hi
    se0, se1 = (math.sqrt(p * (1 - p) / 2000) for p in (0.70, 0.90))
    p0, p1 = 0.70 + 2 * se0, 0.90 + 2 * se1
    assert lo == pytest.approx(120 + (0.80 - p0) / (p1 - p0) * 20)


@pytest.mark.slow
def test_ps4_s8_two_seeds_at_2pct_weak_70_golf_size_agree_within_one_grid_step():
    # 2 % failure, weak clustering, 70 %, Golf's infarct size: Golf R4 E12 has grid N 140
    # (interpolated 128, band 119-137). The grid stops at 180, where power is far above 0.80.
    grid = (100, 120, 140, 160, 180)
    a = _seal(n_grid=grid, seed=101)
    b = _seal(n_grid=grid, seed=7001)
    assert a["sims"] == b["sims"] == 2000
    assert abs(a["seal"] - b["seal"]) <= 20, (a["seal"], b["seal"])
    for s in (a, b):  # 140 expected
        assert abs(s["seal"] - 140) <= 20, s["seal"]
    for s in (a, b):
        lo, hi = s["n80_mc_band"]
        assert lo <= s["n80_interp"] <= hi
        assert 110 <= s["n80_interp"] <= 145, s["n80_interp"]
        assert s["underpowered"] is False and s["power_at_seal"] >= 0.80


@pytest.mark.slow
def test_ps4_s8_2pct_strong_70_caps_at_240_and_is_underpowered():
    # 2 % failure, strong clustering, 70 %: Golf R4 E12 has power at 240 of 0.69 (Golf's infarct
    # size) and 0.64 (Kilo's). Kilo's size sits in the middle of the ruling's 0.63-0.69.
    s = _seal(segs_per_scar_patient=KILO_SIZE, tau=P.CLUSTERING["strong"], n_grid=(220, 240))
    assert s["seal"] == P.SEAL_CAP == 240 and s["capped"] is True
    assert s["underpowered"] is True
    assert s["power_at_seal_source"] == "grid" and s["analysed_at_seal"] == 240
    assert 0.63 <= s["power_at_seal"] <= 0.69, s["power_at_seal"]
    assert s["n80_interp"] is None and s["n80_mc_band"] == [None, None]


def test_ps4_s8_phase_share_01_raises_enrolment_by_1_over_09_capped_at_240():
    kw = dict(p_fail=0.0, n_grid=(120, 160), sims=20, boot=50)
    base = _seal(**kw)
    ph = _seal(phase_share=0.1, **kw)
    # power, the floor and the 270 segments are on analysed patients: unchanged
    assert ph["power_presence"] == base["power_presence"]
    assert ph["seal_analysed"] == base["seal_analysed"] == 120
    assert ph["seal_enrolled"] == ph["seal"] == math.ceil(120 / 0.9) == 134
    assert ph["analysed_at_seal"] >= 120 and ph["capped"] is False
    # a 221-patient segment requirement needs 246 enrolled: the cap binds on enrolment
    seg = 270 / (0.5 * 220.4)
    capped = _seal(enrich=0.5, segs_per_scar_patient=seg, phase_share=0.1, **kw)
    assert capped["n_segments_270"] == capped["seal_analysed"] == 221
    assert capped["seal"] == capped["seal_enrolled"] == 240 and capped["capped"] is True
    assert capped["analysed_at_seal"] == 216  # floor(240 * 0.9): power is stated there
    assert capped["power_at_seal_source"] == "simulated"
    assert 0.0 <= capped["power_at_seal"] <= 1.0
    uncapped = _seal(enrich=0.5, segs_per_scar_patient=seg, **kw)
    assert uncapped["seal"] == 221 and uncapped["capped"] is False
    with pytest.raises(ValueError):
        _seal(phase_share=1.0, **kw)


def test_ps4_s8_phase_share_0_reproduces_the_default():
    kw = dict(p_fail=0.0, n_grid=(120, 160), sims=20, boot=50, seed=3)
    a = _seal(**kw)
    b = _seal(phase_share=0.0, **kw)
    assert a == b
    assert a["seal"] == a["seal_enrolled"] == a["n_required"] == a["seal_analysed"]
    assert a["analysed_at_seal"] == a["seal"]


def test_ps4_s8_seal_grading_allowed_needs_lq40_when_underpowered():
    ok = [PASSED] * 20
    assert R.seal_grading_allowed(ok)
    assert R.seal_grading_allowed(ok, underpowered=False)
    assert not R.seal_grading_allowed(ok, underpowered=True)
    assert R.seal_grading_allowed(ok, underpowered=True, lead_override=True)
    # JA29's > 10 % stop stays the hard floor: no override lifts it
    bad = [PASSED] * 8 + [R.NOT_GRADED] * 2 + [R.NOT_GRADED]
    assert not R.seal_grading_allowed(bad, lead_override=True)
    assert not R.seal_grading_allowed(bad, underpowered=True, lead_override=True)


# -------------------------------------------------------------------------------------------------
# PS4-S9 — the phase-unmatched stratum, and flag-only routing in yield (JA85)

SEG = 16


def _pt(ref, ct, **kw):
    return S.Patient(ref=np.asarray(ref), ct=np.asarray(ct), **kw)


def _study():
    """Forty ordinary patients, half with scar, CT reading LGE exactly, one not graded."""
    out = []
    for i in range(40):
        ref = np.zeros(SEG, int)
        if i % 2:
            ref[i % SEG : i % SEG + 3] = 1 + i % 4
        ct = ref.copy()
        if i == 1:
            ct[ref > 0] = 0  # one miss so sensitivity is not degenerate
        out.append(_pt(ref, ct))
    out.append(_pt(np.zeros(SEG, int), np.full(SEG, S.NOT_GRADED)))
    return out


def _phase(route, graded=True):
    ref = np.zeros(SEG, int)
    ref[:4] = 3
    ct = ref.copy() if graded else np.full(SEG, S.NOT_GRADED)
    return _pt(ref, ct, strata={"phase_unmatched"}, phase_route=route)


def test_ps4_s9_confirmed_and_flag_only_phase_patients():
    base = _study()
    conf, flag = _phase("confirmed"), _phase("flag_only")
    kw = dict(anchor=0.70, n_boot=300, seed=4)
    r0 = S.score(base, **kw)
    r_conf = S.score(base + [conf], **kw)
    r_flag = S.score(base + [flag], **kw)
    r_both = S.score(base + [conf, flag], **kw)

    # both leave primary sensitivity and specificity
    for r in (r_conf, r_flag, r_both):
        for k in ("sens", "spec", "tbin"):
            assert r["primary"][k]["point"] == r0["primary"][k]["point"]
        assert r["primary"]["counts"] == r0["primary"]["counts"]

    # only the flag-only patient moves yield: numerator and denominator
    def y(r):
        return r["yield"]["patients_not_graded"], round(r["yield"]["point"] * 1e6)

    n0 = len(base)
    assert r0["yield"]["point"] == pytest.approx(1 / n0)
    assert y(r_conf) == y(r0)
    assert r_flag["yield"]["patients_not_graded"] == 2
    assert r_flag["yield"]["point"] == pytest.approx(2 / (n0 + 1))
    assert r_both["yield"]["point"] == pytest.approx(2 / (n0 + 1))
    assert r_both["yield"]["patients_flag_only"] == 1

    ph = r_both["phase_unmatched"]
    assert ph["patients"] == 2
    assert ph["routes"] == {"confirmed": 1, "flag_only": 1, "unrouted": 0}
    assert ph["share"]["point"] == pytest.approx(2 / (n0 + 2))
    assert ph["share"]["upper"] >= ph["share"]["point"]
    assert ph["lge_positive_share"]["stratum"] == 1.0
    assert ph["lge_positive_share"]["primary"] == pytest.approx(20 / n0)
    assert ph["accuracy"] is r_both["strata"]["phase_unmatched"]
    assert ph["accuracy"]["sens"]["point"] == 1.0  # its own JA55 accuracy, on its graded reads

    # the put-back treats both as not graded under split accounting
    pb = ph["put_back"]
    assert pb["itd_mode"] == "split"
    c0, cb = r0["primary"]["counts"], pb["primary"]["counts"]
    assert cb["patients"] == c0["patients"] + 2
    assert cb["positive_segments"] == c0["positive_segments"] + 8  # 4 scarred segments each, missed
    assert cb["negative_segments"] == c0["negative_segments"]  # split: out of specificity
    assert cb["scar_on_both"] == c0["scar_on_both"]
    assert pb["primary"]["sens"]["point"] < r_both["primary"]["sens"]["point"]
    assert pb["yield"]["patients_not_graded"] == 3
    assert pb["yield"]["point"] == pytest.approx(3 / (n0 + 2))

    # decide's output is unchanged by the put-back: it reads the primary and yield only
    assert r_both["decision"] == S.decide(r_both["primary"], 0.70, r_both["yield"]["upper"])
    # the routed patients' own reads cannot move the decision either
    swapped = [_phase("confirmed", graded=False), _phase("flag_only", graded=False)]
    r_swapped = S.score(base + swapped, **kw)
    assert r_swapped["decision"] == r_both["decision"]
    assert r_swapped["phase_unmatched"]["put_back"] == pb


def test_ps4_s9_development_flags_for_the_lead():
    base = _study()  # 41 patients
    kw = dict(anchor=0.70, n_boot=100, seed=1)
    one = S.score(base + [_phase("flag_only")], **kw)["phase_unmatched"]["report_to_lead"]
    assert one == {"flag_only_share_over_3pct": False, "phase_share_over_20pct": False}
    two = S.score(base + [_phase("flag_only")] * 2, **kw)["phase_unmatched"]
    assert two["flag_only_share"] == pytest.approx(2 / 43)
    assert two["report_to_lead"]["flag_only_share_over_3pct"] is True
    many = S.score(base + [_phase("confirmed")] * 11, **kw)["phase_unmatched"]
    assert many["share"]["point"] == pytest.approx(11 / 52)
    assert many["report_to_lead"] == {
        "flag_only_share_over_3pct": False,
        "phase_share_over_20pct": True,
    }


def test_ps4_s9_phase_route_needs_the_stratum():
    ref = np.zeros(SEG, int)
    with pytest.raises(ValueError):
        _pt(ref, ref, phase_route="flag_only")
    with pytest.raises(ValueError):
        _pt(ref, ref, strata={"phase_unmatched"}, phase_route="maybe")
    # a stratum patient without a route (as before #260) is treated as confirmed: out of yield
    p = _pt(ref, np.full(SEG, S.NOT_GRADED), strata={"phase_unmatched"})
    r = S.score(_study() + [p], anchor=0.7, n_boot=100, seed=2)
    assert r["yield"]["patients_not_graded"] == 1
    assert r["phase_unmatched"]["routes"]["unrouted"] == 1
