"""Round 3 paired-scar §9, power and scoring: PS3-S8 (JA55), PS3-S9 (JA56), PS3-S10 (JA57).

Ruling: ``vault/JanusM/Judgements/Round 3 - paired-scar.md``. Each test below is one of §9's named
checks. The reproductions re-run committed Round 3 cells (Juliet E9, Kilo E9, Golf E10, #187)
through ``janusm.scar.power`` and require each within 3.5 Monte-Carlo standard errors of what was
recorded; the recorded values are read from the committed JSON, never retyped. Synthetic data only.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from janusm.scar import power as P
from janusm.scar import scoring as S

EXP = Path(__file__).resolve().parents[1] / "experiments" / "JanusM"
Z_MAX = 3.5
SIMS, BOOT = 400, 200


def _z(recorded: float, rec_sims: int, now: float, sims: int) -> float:
    var = max(recorded * (1 - recorded), 0.25 / sims)  # floor keeps z finite at 0 or 1
    return (now - recorded) / math.sqrt(var * (1 / rec_sims + 1 / sims))


# -------------------------------------------------------------------------------------------------
# PS3-S8 — JA55 accounting and the yield endpoint


def _juliet_e9():
    return json.loads((EXP / "Juliet" / "r3" / "e9_itd_power.json").read_text())


def _kilo_e9():
    return json.loads((EXP / "Kilo" / "results_e9_engine_ja32.json").read_text())


# Juliet E9's split cells the ruling names: N 200 at 50 %, 160 at 70 %, 2 % failure, weak clustering
JULIET_SPLIT_CELLS = [(0.5, 200), (0.7, 160)]


@pytest.mark.parametrize("enrich,n", JULIET_SPLIT_CELLS)
def test_ps3_s8_reproduces_juliet_e9_split_cells(enrich, n):
    rec = _juliet_e9()
    row = next(
        r
        for r in rec["rows"]
        if r["clustering"] == "weak" and r["enrich"] == enrich and r["n"] == n
        and r["p_fail"] == 0.02
    )  # fmt: skip
    assert row["power_split"] >= 0.80  # the cells that size JA57's planning figures
    params = {**P.JA32_BASE, "tau": P.CLUSTERING["weak"], "enrich": enrich, "p_fail": 0.02}
    st = P.simulate_studies(P.golf_cohort, n, SIMS, BOOT, 5500 + n, itd_mode="split", **params)
    # Juliet's joint pass = sens, spec, tbin at anchor 0.70 and yield: JA56's claim 2 power
    now = P.claim_power(st, rec["anchor"])["kim_bin"]
    assert abs(_z(row["power_split"], rec["sims"], now, SIMS)) <= Z_MAX, (row, now)


KILO_CELLS = [(m, n) for m in ("worst", "nocall", "graded") for n in (120, 160, 240)]
# the ruling's §1.4 table, as re-read by the judge
KILO_RULING = {
    "worst": (0.39, 0.503, 0.61),
    "nocall": (0.65, 0.78, 0.913),
    "graded": (0.88, 0.947, 0.993),
}


@pytest.mark.parametrize("mode,n", KILO_CELLS)
def test_ps3_s8_reproduces_kilo_e9_worst_nocall_graded_cells(mode, n):
    rec = _kilo_e9()
    row = next(
        r for r in rec["B_failures"] if r["enrich"] == 0.5 and r["p_fail"] == 0.02 and r["n"] == n
    )
    # nocall is scored with its yield bar (Kilo's proposal); worst and graded as Kilo ran them
    recorded = row[mode]["joint_nocall_yield" if mode == "nocall" else "joint_fixed"]
    assert recorded == pytest.approx(KILO_RULING[mode][(120, 160, 240).index(n)], abs=0.011)
    params = {**rec["settings"]["base"], "q": 0.25, "p_fail": 0.02}
    st = P.simulate_studies(P.golf_cohort, n, SIMS, BOOT, 9900 + n, itd_mode=mode, **params)
    bars = S.bars(rec["settings"]["anchor"])
    now = P.power_from(st, bars, S.YIELD_BAR if mode == "nocall" else None)["power_all"]
    assert abs(_z(recorded, rec["settings"]["sims"], now, SIMS)) <= Z_MAX, (mode, n, now)


def _hand_study():
    """20 patients, 17 segments: 10 with 4 scarred segments, CT perfect; 10 scar-free, CT clean."""
    pts = []
    for i in range(20):
        ref = np.zeros(17, int)
        if i < 10:
            ref[[0, 1, 6, 7]] = [1, 2, 3, 4]
        pts.append(S.Patient(ref=ref, ct=ref.copy()))
    return pts


def test_ps3_s8_one_failed_scarred_patient_lowers_sensitivity_leaves_specificity_under_split():
    pts = _hand_study()
    ok = S.score(pts, anchor=0.8, n_boot=200)
    failed_ref = pts[0].ref
    failed = S.Patient(ref=failed_ref, ct=np.full(17, S.NOT_GRADED))
    rep = S.score(pts[1:] + [failed], anchor=0.8, n_boot=200)
    assert rep["rule"]["itd_mode"] == "split"  # the default
    assert ok["primary"]["sens"]["point"] == 1.0
    assert rep["primary"]["sens"]["point"] == pytest.approx(36 / 40)
    assert rep["primary"]["spec"]["point"] == ok["primary"]["spec"]["point"] == 1.0
    # its 13 scar-free segments left the specificity denominator; worst case counts them wrong
    c, c_ok = rep["primary"]["counts"], ok["primary"]["counts"]
    assert c["negative_segments"] == c_ok["negative_segments"] - 13
    assert rep["accountings"]["worst"]["spec"]["point"] < 1.0
    assert rep["accountings"]["nocall"]["spec"]["point"] == 1.0
    assert rep["yield"]["point"] == pytest.approx(1 / 20)
    assert rep["yield"]["patients_not_graded"] == 1


def test_ps3_s8_resolve_modes_by_hand():
    ref = np.array([[2, 0, 0], [3, 0, 1]])
    ct = np.array([[S.NOT_GRADED] * 3, [3, 0, S.NOT_GRADED]])
    c, m, k = S.resolve(ref, ct, mode="split")
    assert c.tolist() == [[0, 0, 0], [3, 0, 0]]
    assert m.tolist() == [[True, False, False], [True, True, True]] and k.all()
    c, m, k = S.resolve(ref, ct, mode="worst")
    assert c.tolist() == [[0, 1, 1], [3, 0, 0]] and m.all()
    c, m, k = S.resolve(ref, ct, mode="nocall")
    assert c.tolist() == [[0, 0, 0], [3, 0, 0]] and m.all()
    c, m, k = S.resolve(ref, ct, mode="graded")
    assert m.tolist() == [[False] * 3, [True, True, False]] and k.tolist() == [False, True]
    with pytest.raises(ValueError):
        S.resolve(ref, ct, mode="lenient")


def test_ps3_s8_yield_bar_is_inside_decide():
    ng = np.r_[np.ones(30, bool), np.zeros(170, bool)]  # 15 % not graded
    y = S.yield_upper_bound(ng, n_boot=500, rng=np.random.default_rng(0))
    assert y["point"] == pytest.approx(0.15) and y["upper"] > 0.15
    ci = {"sens": {"lower": 0.9}, "spec": {"lower": 0.97}, "tbin": {"lower": 0.9}}
    d = S.decide(ci, 0.8, y["upper"])
    assert d["presence"]["per_endpoint"]["yield"] is False
    assert d["presence_validated"] is False and d["kim_bin_validated"] is False
    y = S.yield_upper_bound(np.zeros(200, bool), n_boot=500, rng=np.random.default_rng(0))
    assert y["upper"] == 0.0
    assert S.decide(ci, 0.8, y["upper"])["presence_validated"] is True


# -------------------------------------------------------------------------------------------------
# PS3-S9 — Two claims (JA56)


def _reads(agree: int, total: int = 20):
    """Two unadjudicated reads with ``agree`` of ``total`` scar-on-both segments in the same bin."""
    r1 = np.full((1, total), 2)
    r2 = np.r_[np.full(agree, 2), np.full(total - agree, 3)][None, :]
    return r1, r2


def test_ps3_s9_presence_fails():
    pts = _hand_study()
    # CT misses half the scar in every scarred patient: sensitivity 0.5; the bins it calls are exact
    missed = []
    for p in pts:
        ct = p.ct.copy()
        ct[[0, 1]] = 0
        missed.append(S.Patient(ref=p.ref, ct=ct))
    rep = S.score(missed, double_reads=_reads(16), n_boot=300)
    d = rep["decision"]
    assert d["presence"]["per_endpoint"]["sens"] is False
    assert d["presence_validated"] is False
    # the Kim bin would clear its bar, but it is not evaluated when presence fails
    assert rep["primary"]["tbin"]["lower"] == 1.0
    assert d["kim_bin"]["evaluated"] is False and d["kim_bin_validated"] is False


def test_ps3_s9_presence_passes_and_the_bin_passes():
    pts = _hand_study() * 3
    rep = S.score(pts, double_reads=_reads(16), n_boot=300)
    d = rep["decision"]
    assert rep["rule"]["anchor"]["agreement"] == pytest.approx(0.80)
    assert d["presence_validated"] is True
    assert d["kim_bin"]["evaluated"] is True
    assert d["kim_bin"]["bar_lower95"] == pytest.approx(0.70)
    assert d["kim_bin_validated"] is True


def test_ps3_s9_the_anchor_is_055():
    pts = _hand_study() * 3
    rep = S.score(pts, double_reads=_reads(11), n_boot=300)
    d = rep["decision"]
    assert rep["rule"]["anchor"]["agreement"] == pytest.approx(0.55)
    assert d["presence_validated"] is True
    # an anchor < 0.60 cannot validate the Kim bin, however well CT grades ...
    assert d["kim_bin_validated"] is False and d["kim_bin"]["anchor_deciding"] is False
    # ... and the 0.50-bar result is reported beside it
    assert d["kim_bin"]["fixed_bar_lower95"] == 0.50
    assert d["kim_bin"]["passed_fixed_bar"] is True


def test_ps3_s9_anchor_is_over_every_double_read_patient_unadjudicated():
    # development (40) + seal (60) double reads; the seal scored has 60 patients, and the anchor
    # uses all 100 from the two raw reads, not the adjudicated reference
    rng = np.random.default_rng(56)
    r1 = rng.integers(0, 5, (100, 17))
    r2 = np.where(rng.random((100, 17)) < 0.7, r1, rng.integers(0, 5, (100, 17)))
    expect = S.reader_agreement(r1, r2)
    seal = _hand_study() * 3
    rep = S.score(seal, double_reads=(r1, r2), n_boot=100)
    assert rep["rule"]["anchor"]["agreement"] == pytest.approx(expect["agreement"])
    assert rep["rule"]["anchor"]["segments"] == expect["segments"] > 17 * 60 * 0.5
    seal_only = S.reader_agreement(r1[40:], r2[40:])["agreement"]
    assert seal_only != pytest.approx(expect["agreement"], abs=1e-12)
    with pytest.raises(ValueError):
        S.score(seal, anchor=0.7, double_reads=(r1, r2))
    with pytest.raises(ValueError):
        S.reader_agreement(r1, r2[:50])


# -------------------------------------------------------------------------------------------------
# PS3-S10 — seal_size per JA57


def _golf_e10():
    return json.loads((EXP / "Golf" / "power_ja32.json").read_text())["segments_needed"]


def _draw_kilo_k(rng):
    names = list(P.KILO_TERR)
    terr = P.KILO_TERR[names[rng.choice(3, p=[P.KILO_TERR_P[k] for k in names])]]
    return 1 + rng.binomial(len(terr) - 1, 0.45)


def _draw_golf_k(rng):
    return min(1 + rng.poisson(3.0), 17)


@pytest.mark.parametrize("enrich", [0.5, 0.7])
def test_ps3_s10_reproduces_golf_e10_segments_needed(enrich):
    rec = _golf_e10()
    # the ruling's figures: 167 / 119 with Kilo's infarct size
    assert rec["kilo"][str(enrich)]["median"] == {0.5: 167, 0.7: 119}[enrich]
    m = P.kilo_segments_per_scar_patient()
    assert m == pytest.approx(3.25)
    assert P.patients_for_scarred_segments(270, enrich, m) == rec["kilo"][str(enrich)]["median"]
    # seal_size's 270-segment term takes the same input
    s = P.seal_size(0.02, m, 0.25, P.GOLF_SENS_BY_BIN, enrich, n_grid=(240,), sims=5, boot=20)
    assert s["n_segments_270"] == rec["kilo"][str(enrich)]["median"]
    # and Golf's own Monte-Carlo count (median, p90) reproduces for both infarct sizes
    for size, draw in (("kilo", _draw_kilo_k), ("golf", _draw_golf_k)):
        mc = P.segments_needed_mc(np.random.default_rng(10), draw, enrich, sims=1500)
        assert abs(mc["median"] - rec[size][str(enrich)]["median"]) <= 2, (size, mc)
        assert abs(mc["p90"] - rec[size][str(enrich)]["p90"]) <= 4, (size, mc)


def test_ps3_s10_reproduces_187_patients_for_270_segments():
    rec = json.loads((EXP / "Scar" / "ja32_power_r2.json").read_text())
    assert rec["patients_for_270_segments"] == {"0.5": 136, "0.7": 97}
    m = P.expected_scar_segments(1.0, 3.0)  # #187's cohort: 1 + Poisson(3), 16 segments
    for enrich in (0.5, 0.7):
        s = P.seal_size(0.02, m, 0.25, P.GOLF_SENS_BY_BIN, enrich, n_grid=(240,), sims=5, boot=20)
        assert s["n_segments_270"] == rec["patients_for_270_segments"][str(enrich)]


def test_ps3_s10_cap_binds_under_strong_clustering_at_50():
    s = P.seal_size(
        p_fail=0.02,
        segs_per_scar_patient=P.expected_scar_segments(1.0, 3.0),
        extent_error=0.25,
        sens_by_bin=P.GOLF_SENS_BY_BIN,
        enrich=0.5,
        tau=P.CLUSTERING["strong"],
        n_grid=(160, 200, 240),
        sims=200,
        boot=200,
    )
    assert s["capped"] is True and s["seal"] == P.SEAL_CAP == 240
    assert max(s["power_presence"].values()) < 0.80
    json.dumps(s)


def test_ps3_s10_claim2_enters_the_target_only_if_the_gap_is_at_least_minus_003():
    kw = dict(
        p_fail=0.02,
        segs_per_scar_patient=4.0,
        extent_error=(0.25, 0.25, 0.25, 0.25),  # per bin
        sens_by_bin=P.GOLF_SENS_BY_BIN,
        enrich=0.7,
        n_grid=(120, 240),
        sims=20,
        boot=50,
    )
    inside = P.seal_size(dev_ct_agreement=0.67, dev_anchor=0.70, **kw)
    assert inside["claim2_gap"] == pytest.approx(-0.03)
    assert inside["claim2_powered"] is True and inside["scar1_triggered"] is False
    assert set(inside["power_kim_bin"]) == {"120", "240"}
    below = P.seal_size(dev_ct_agreement=0.66, dev_anchor=0.70, **kw)
    assert below["claim2_powered"] is False and below["scar1_triggered"] is True
    assert below["power_kim_bin"] == {} and below["n_power_kim_bin"] is None
    # an anchor < 0.60 cannot validate the bin, so it is never powered
    low = P.seal_size(dev_ct_agreement=0.58, dev_anchor=0.55, **kw)
    assert low["claim2_powered"] is False
    # presence-only sizing ignores claim 2 entirely
    none = P.seal_size(**kw)
    assert none["claim2_powered"] is False and none["claim2_gap"] is None


def test_ps3_s10_seal_only_grows_and_respects_the_floor():
    kw = dict(
        p_fail=0.0,
        segs_per_scar_patient=4.0,
        extent_error=0.25,
        sens_by_bin=P.GOLF_SENS_BY_BIN,
        enrich=0.7,
        n_grid=(120, 160),
        sims=40,
        boot=100,
    )
    s = P.seal_size(**kw)
    assert s["seal"] >= P.SEAL_FLOOR
    grown = P.seal_size(previous=200, **kw)
    assert grown["seal"] >= 200
    assert P.seal_size(previous=300, **kw)["seal"] == P.SEAL_CAP


def test_ps3_s10_extent_error_per_bin_moves_only_that_bin():
    def agree(q):
        rng = np.random.default_rng(3)
        ref, ct = P.golf_cohort(rng, 4000, q=q, bin_tau=1.0)
        both = (ref > 0) & (ct > 0)
        return [float((ct[both & (ref == b)] == b).mean()) for b in (1, 2, 3, 4)]

    flat = agree(0.25)
    per = agree((0.25, 0.25, 0.60, 0.25))
    assert per[2] < flat[2] - 0.2
    for b in (0, 1, 3):
        assert per[b] == pytest.approx(flat[b], abs=0.03)
    # the scalar and the constant per-bin vector are the same cohort
    assert agree((0.25,) * 4) == pytest.approx(flat)
