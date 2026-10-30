"""The one JA32 power script (JA28, JA32; JA35 item 4): reproduction of Round 2 and the seal-size
logic.

The reproduction check re-runs every cell of :data:`janusm.scar.power.ROUND2_RECORD` through the
merged engine and requires it within 3.5 Monte-Carlo standard errors of what Round 2 committed. The
recorded values are themselves checked against the committed JSON, so the record cannot drift from
the files."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from janusm.scar import power as P
from janusm.scar import scoring as S

REPO = Path(__file__).resolve().parents[1]
EXP = REPO / "experiments" / "JanusM"


def _golf_json():
    return json.loads((EXP / "Golf" / "cohort_power.json").read_text())["grid"]


def _kilo_json():
    return json.loads((EXP / "Kilo" / "results_e6_power.json").read_text())


def _juliet_json():
    return json.loads((EXP / "Juliet" / "e5_cohort_power.json").read_text())["rows"]


def test_record_matches_the_committed_round2_json():
    golf, kilo, juliet = _golf_json(), _kilo_json(), _juliet_json()
    for cell in P.ROUND2_RECORD:
        p, n = cell["params"], cell["n"]
        if cell["script"] == "golf":
            row = next(
                r
                for r in golf
                if r["N"] == n and all(r[k] == p[k] for k in ("enrich", "lam", "tau", "q"))
            )
            assert row["power_all"] == pytest.approx(cell["power"])
        elif cell["script"] == "kilo":
            row = next(r for r in kilo["grid"] if r["n_patients"] == n and r["sd_s"] == p["sd_s"])
            assert row["power_sens_lb_gt_0.75"] == pytest.approx(cell["power"])
            assert kilo["settings"]["q"] == p["q"]
        else:
            scen = "published" if p["sens"] == 0.86 else "weak"
            row = next(
                r
                for r in juliet
                if r["scenario"] == scen and r["f_mi"] == p["f_mi"] and r["n_patients"] == n
            )
            assert row["pass_rate"] == pytest.approx(cell["power"])
    for sd_s, tb in P.KILO_TBIN_RECORD.items():
        assert kilo["calibration"][str(sd_s)]["tbin_agreement_scarred"] == pytest.approx(tb)


def test_reproduces_round2_within_monte_carlo_error():
    for r in P.reproduce(sims=200, boot=200):
        assert abs(r["z"]) <= 3.5, r


@pytest.mark.parametrize("sd_s", sorted(P.KILO_TBIN_RECORD))
def test_reproduces_kilo_transmurality_agreement(sd_s):
    rng = np.random.default_rng(int(sd_s * 100))
    ref, ct = P.kilo_cohort(rng, 20000, q=0.7, sd_s=sd_s)
    e = S.endpoints(S.patient_stats(ref, ct).sum(0))
    assert e["tbin"] == pytest.approx(P.KILO_TBIN_RECORD[sd_s], abs=0.015)
    assert e["sens"] == pytest.approx(0.845, abs=0.01)
    assert e["spec"] == pytest.approx(0.982, abs=0.005)


def test_golf_cohort_shape_and_failure():
    rng = np.random.default_rng(0)
    ref, ct = P.golf_cohort(rng, 500, p_fail=0.2)
    assert ref.shape == ct.shape == (500, 16)
    failed = (ct == S.NOT_GRADED).all(1)
    assert 0.12 < failed.mean() < 0.28
    assert not (ct[~failed] == S.NOT_GRADED).any()
    ref0, ct0 = P.golf_cohort(np.random.default_rng(0), 500)
    assert (ct0 >= 0).all()


def test_bin_tau_moves_grading_with_the_patient_effect():
    def tbin(bin_tau):
        rng = np.random.default_rng(1)
        ref, ct = P.golf_cohort(rng, 4000, tau=1.2, bin_tau=bin_tau)
        st = S.patient_stats(ref, ct)
        # agreement per patient varies more when bin errors cluster
        with np.errstate(invalid="ignore"):
            per = st[:, S.AGREE] / st[:, S.BOTH]
        return np.nanstd(per[st[:, S.BOTH] >= 3])

    assert tbin(1.0) > tbin(0.0)


def test_expected_scar_segments_and_the_270_rule():
    e = P.expected_scar_segments(0.5, 3.0)
    rng = np.random.default_rng(2)
    ref, _ = P.golf_cohort(rng, 20000, enrich=0.5, lam=3.0)
    assert (ref > 0).sum(1).mean() == pytest.approx(e, rel=0.02)
    assert P.patients_for_segments(270, 0.5, 3.0) in (135, 136)  # JA28: "about 135" at 50 %
    assert P.patients_for_segments(270, 0.7, 3.0) in (96, 97)


def test_seal_size_takes_the_largest_requirement():
    curve = {60: 0.5, 80: 0.81, 100: 0.79, 120: 0.85, 140: 0.9}
    s = P.seal_size(curve, enrich=0.5, lam=3.0)
    assert s["n_power"] == 120  # 80 does not stay above 0.80
    assert s["seal"] == max(120, s["n_segments_270"])
    s = P.seal_size({60: 0.9, 80: 0.95}, enrich=0.7, lam=3.0)
    assert s["n_power"] == 60 and s["seal"] == 120
    assert P.seal_size({60: 0.1, 80: 0.2}, enrich=0.5, lam=3.0)["seal"] is None


def test_power_from_ignores_reported_only_endpoints():
    st = {
        "lower": {
            "sens": np.array([0.8, 0.7]),
            "spec": np.array([0.95, 0.95]),
            "tbin": np.array([0.1, np.nan]),
        }
    }
    pw = P.power_from(st, S.bars(0.5))
    assert pw["power"] == {"sens": 0.5, "spec": 1.0}
    assert pw["power_all"] == 0.5
    pw = P.power_from(st, S.bars(0.7))
    assert pw["power_all"] == 0.0


def test_ja32_study_runs_end_to_end_small():
    res = P.ja32_study(sims=4, boot=20, n_grid=(60, 120), anchors=(0.7,))
    json.dumps(res)
    combos = len(P.CLUSTERING) * len(P.ENRICH) * len(P.P_FAIL)
    assert len(res["seal_size"]) == combos * 2  # one anchor + reported-only
    assert len(res["grid"]) == combos * 2 * 2
    assert res["patients_for_270_segments"]["0.5"] in (135, 136)
