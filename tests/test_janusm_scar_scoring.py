"""The paired-seal scoring harness (JA27, JA32, JA55, JA56; JA35 item 6; PS3-S8, PS3-S9), on
synthetic reads only."""

from __future__ import annotations

import json

import numpy as np
import pytest

from janusm.scar import scoring as S


def _p(ref, ct, **kw):
    return S.Patient(ref=np.array(ref), ct=np.array(ct), **kw)


def test_intention_to_diagnose_counts_not_graded_as_wrong():
    ref = np.array([0, 2, 0, 3])
    ct = np.array([S.NOT_GRADED, S.NOT_GRADED, 0, 3])
    assert S.intention_to_diagnose(ref, ct).tolist() == [1, 0, 0, 3]


def test_endpoints_by_hand():
    # 2 patients x 4 segments. LGE positives: 4; CT detects 3, 2 of them in the right bin.
    ref = np.array([[1, 2, 0, 0], [3, 4, 0, 0]])
    ct = np.array([[1, 3, 0, 1], [0, 4, 0, 0]])
    e = S.endpoints(S.patient_stats(ref, ct).sum(0))
    assert e["sens"] == pytest.approx(3 / 4)
    assert e["spec"] == pytest.approx(3 / 4)
    assert e["tbin"] == pytest.approx(2 / 3)
    assert e["patient_sens"] == pytest.approx(1.0)
    perfect = S.endpoints(S.patient_stats(ref, ref).sum(0))
    assert perfect["kappa_linear"] == pytest.approx(1.0)
    assert perfect["kappa_quadratic"] == pytest.approx(1.0)


def test_kappa_matches_the_textbook_formula():
    rng = np.random.default_rng(0)
    ref = rng.integers(0, 5, (30, 17))
    ct = np.clip(ref + rng.integers(-1, 2, ref.shape), 0, 4)
    m = np.zeros((5, 5))
    np.add.at(m, (ref.ravel(), ct.ravel()), 1)
    p = m / m.sum()
    e = np.outer(p.sum(1), p.sum(0))
    k = np.arange(5)
    for quad, key in ((False, "kappa_linear"), (True, "kappa_quadratic")):
        d = np.abs(np.subtract.outer(k, k)) / 4
        d = d**2 if quad else d
        want = 1 - (d * p).sum() / (d * e).sum()
        got = S.endpoints(S.patient_stats(ref, ct).sum(0))[key]
        assert got == pytest.approx(want)


def test_mask_drops_segments():
    ref = np.array([[2, 0, 3]])
    ct = np.array([[0, 1, 3]])
    st = S.patient_stats(ref, ct, mask=np.array([[False, True, True]]))
    assert st[0, S.POS] == 1 and st[0, S.TP] == 1 and st[0, S.NEG] == 1
    assert st[0, S.CONF0 :].sum() == 2


def test_bootstrap_resamples_patients_not_segments():
    """Clustered errors widen the CI: the same segments in 10 patients vs spread over 160."""
    rng = np.random.default_rng(1)
    ref = np.ones((10, 16), int)
    ct = np.zeros((10, 16), int)
    ct[:8] = 1  # 8 patients all detected, 2 all missed -> sens 0.8, perfectly clustered
    clustered = S.cluster_bootstrap(S.patient_stats(ref, ct), 2000, rng)["sens"]
    spread = S.cluster_bootstrap(
        S.patient_stats(ref.reshape(160, 1), ct.reshape(160, 1)), 2000, rng
    )["sens"]
    assert clustered["point"] == pytest.approx(0.8) == spread["point"]
    assert clustered["upper"] - clustered["lower"] > 3 * (spread["upper"] - spread["lower"])


def test_bars_and_the_reader_anchor():
    assert S.bars(0.75) == {"sens": 0.75, "spec": 0.93, "tbin": pytest.approx(0.65)}
    assert S.bars(0.59)["tbin"] is None
    assert S.bars(None)["tbin"] is None
    r1 = np.array([[0, 1, 2, 3, 4, 2]])
    r2 = np.array([[0, 1, 3, 3, 0, 2]])
    a = S.reader_agreement(r1, r2)
    assert a == {"agreement": pytest.approx(3 / 4), "segments": 4}


def test_decide_needs_every_presence_endpoint():
    ci = {"sens": {"lower": 0.76}, "spec": {"lower": 0.95}, "tbin": {"lower": 0.50}}
    d = S.decide(ci, 0.55, yield_upper=0.05)
    assert d["presence"]["per_endpoint"] == {"sens": True, "spec": True, "yield": True}
    assert d["presence_validated"] is True and d["kim_bin_validated"] is False
    d = S.decide(ci, 0.70, yield_upper=0.05)
    assert d["kim_bin"]["passed_anchor_bar"] is False and d["kim_bin_validated"] is False
    assert S.decide(ci, 0.55, yield_upper=0.11)["presence_validated"] is False
    low = {**ci, "spec": {"lower": 0.92}}
    assert S.decide(low, 0.55, yield_upper=0.0)["presence_validated"] is False


def test_patient_validation():
    with pytest.raises(ValueError):
        _p([0, 5], [0, 0])
    with pytest.raises(ValueError):
        _p([0, 1], [0, -2])
    with pytest.raises(ValueError):
        _p([0, 1], [0, 1], strata={"made_up"})
    with pytest.raises(ValueError):
        _p([0, 1], [0])


def _cohort(rng, n=60, s=17):
    pts = []
    for _ in range(n):
        ref = np.zeros(s, int)
        if rng.random() < 0.6:
            k = rng.integers(2, 6)
            ref[rng.choice(s, k, replace=False)] = rng.integers(1, 5, k)
        ct = np.where(rng.random(s) < 0.9, ref, 0)
        ct = np.where((ref == 0) & (rng.random(s) < 0.02), 1, ct)
        pts.append(
            S.Patient(
                ref=ref,
                ct=ct,
                protocol="A" if rng.random() < 0.5 else "B",
                ref_share=ref / 4.0,
                ct_share=ct / 4.0,
            )
        )
    return pts


def test_score_primary_excludes_strata_and_non_ischaemic_segments():
    rng = np.random.default_rng(2)
    base = _cohort(rng)
    s = 17
    # a perfect primary cohort, plus stratum patients whose CT misses everything
    perfect = [S.Patient(ref=p.ref, ct=p.ref, protocol=p.protocol) for p in base]
    bad_ref = np.array([3] * 4 + [0] * (s - 4))
    bad = [
        S.Patient(ref=bad_ref, ct=np.zeros(s, int), strata={st})
        for st in ("acute", "non_ischaemic", "phase_unmatched")
    ]
    # a primary patient whose missed scar is non-ischaemic: dropped segment by segment
    isch = np.ones(s, bool)
    isch[:4] = False
    mixed = S.Patient(ref=bad_ref, ct=np.zeros(s, int), ischaemic=isch)
    rep = S.score(perfect + bad + [mixed], anchor=0.8, n_boot=300)
    assert rep["primary"]["sens"]["point"] == pytest.approx(1.0)
    assert rep["primary"]["counts"]["patients"] == len(perfect) + 1
    assert set(rep["strata"]) == {"acute", "non_ischaemic", "phase_unmatched"}
    assert rep["strata"]["acute"]["sens"]["point"] == 0.0
    assert rep["decision"]["presence_validated"] is True
    assert rep["decision"]["kim_bin_validated"] is True
    json.dumps(rep)  # JSON-ready, counts and estimates only


def test_prior_cabg_stays_in_for_scar_but_not_territories():
    s = 17
    ref = np.zeros(s, int)
    ref[[0, 2, 4]] = 2  # one LAD, one RCA, one LCx segment
    cabg = S.Patient(ref=ref, ct=np.zeros(s, int), strata={"prior_cabg"})
    ok = S.Patient(ref=ref, ct=ref)
    rep = S.score([cabg, ok], anchor=None, n_boot=200)
    assert rep["primary"]["sens"]["point"] == pytest.approx(0.5)
    for terr in ("LAD", "RCA", "LCx"):
        assert rep["by_territory"][terr]["sens"]["point"] == pytest.approx(1.0)
    assert rep["strata"]["prior_cabg"]["sens"]["point"] == 0.0


def test_score_worst_case_itd_against_graded_only():
    rng = np.random.default_rng(3)
    pts = _cohort(rng)
    s = 17
    failed = S.Patient(ref=np.array([2] * 3 + [0] * (s - 3)), ct=np.full(s, S.NOT_GRADED))
    rep = S.score(pts + [failed], anchor=0.8, n_boot=300, itd_mode="worst")
    rep_ok = S.score(pts, anchor=0.8, n_boot=300)
    # JA29 worst case: the failed patient's scar is missed and its scar-free segments false calls
    assert rep["primary"]["sens"]["point"] < rep_ok["primary"]["sens"]["point"]
    assert rep["primary"]["spec"]["point"] < rep_ok["primary"]["spec"]["point"]
    # it never enters scar-on-both, so transmurality agreement does not move
    assert rep["primary"]["tbin"]["point"] == pytest.approx(rep_ok["primary"]["tbin"]["point"])
    # graded-only drops it
    graded = rep["accountings"]["graded"]
    assert graded["sens"]["point"] == pytest.approx(rep_ok["primary"]["sens"]["point"])
    assert graded["counts"]["patients"] == len(pts)
    assert rep["not_graded"]["patients_not_graded"] == 1
    assert rep["not_graded"]["segment_rate"] == pytest.approx(s / (s * (len(pts) + 1)))


def test_score_reports_everything_ja32_lists():
    rng = np.random.default_rng(4)
    rep = S.score(_cohort(rng), anchor=0.55, n_boot=300)
    assert rep["rule"]["tbin_deciding"] is False
    assert set(rep["decision"]["presence"]["per_endpoint"]) == {"sens", "spec", "yield"}
    assert set(rep["accountings"]) == {"worst", "nocall", "graded"}
    for k in ("kappa_linear", "kappa_quadratic", "patient_sens", "patient_spec"):
        assert (
            0
            <= rep["primary"][k]["lower"]
            <= rep["primary"][k]["point"]
            <= rep["primary"][k]["upper"]
            <= 1
        )
    assert set(rep["by_protocol"]) == {"A", "B"}
    assert set(rep["by_territory"]) == {"LAD", "RCA", "LCx"}
    ba = rep["bland_altman_scar_share"]
    assert ba["loa_lower"] <= ba["bias"] <= ba["loa_upper"]


def test_score_is_deterministic_for_a_seed():
    rng = np.random.default_rng(5)
    pts = _cohort(rng)
    a = S.score(pts, anchor=0.7, n_boot=200, seed=9)
    b = S.score(pts, anchor=0.7, n_boot=200, seed=9)
    assert a == b
