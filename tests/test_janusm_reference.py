"""S6 (issue #196): the reference-population builder, on synthetic populations only.

JA41 (gate), JA42 (RC), JA48 (config, pin, refusal). No case is opened; the only case ids used
are the repository's own frozen lists, to check that the builder refuses them.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

from janusm import calibrate_s3_stub as C
from janusm import guard, sealed_r1
from janusm import reference as R

sys.path.insert(0, str(Path(__file__).parent))
import janusm_synth as Y  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
TOOL = REPO / "tools/janusm/build_reference.py"


# ------------------------------------------------------------------------------------ cases
def test_config_path_is_the_guards():
    assert R.CONFIG_RELPATH == guard.REFERENCE_RELPATH
    assert guard.REFERENCE_SHA256 is None  # pinned only by the PR that commits the lead's run


def test_derived_population_excludes_every_janusm_list():
    cases = R.derive_cases()
    s = sealed_r1.load()
    train = set(json.loads((REPO / guard.SPLITS_RELPATH).read_text())["train"])
    assert len(cases) == 360 == len(set(cases))
    assert set(cases) <= train
    for lst in (s.seal, s.decision, s.jm0, s.seal_extension):
        assert not set(cases) & set(lst)
    assert R.refuse_cases(cases) == cases


@pytest.mark.parametrize("which", ["seal", "decision", "jm0", "seal_extension"])
def test_refuses_any_seal_decision_or_jm0_case(which):
    cases = R.derive_cases()
    intruder = sorted(getattr(sealed_r1.load(), which))[0]
    with pytest.raises(guard.HeldOutError):
        R.refuse_cases(cases[1:] + [intruder])


def test_refuses_a_list_that_is_not_the_derived_one():
    cases = R.derive_cases()
    with pytest.raises(R.ReferenceError, match="missing"):
        R.refuse_cases(cases[:-1])
    with pytest.raises(R.ReferenceError, match="duplicate"):
        R.refuse_cases(cases + cases[:1])


def test_refuses_a_splits_file_that_is_not_pinned(tmp_path):
    p = tmp_path / "splits.json"
    p.write_text("{}")
    with pytest.raises(R.ReferenceError, match="pinned"):
        R.refuse_cases(R.derive_cases(), splits_path=p)


def test_inputs_and_outputs_carry_no_case_id():
    R.assert_anonymous({"wall_mm": {"1": 7.0}, "fat_clusters_mm3": {"-30": {"LAD": []}}})
    for bad in ({"id": "c0002"}, ["s0655"], {"x": "ImageCAS-X__c0002"}):
        with pytest.raises(R.ReferenceError):
            R.assert_anonymous(bad)


# ------------------------------------------------------------------------------------ rule C
GOLDEN_LIMA = [  # from experiments/JanusM/Lima/calibrate_sim.py on jm/rest-ccta, unchanged
    (7, (0.1, 0.4, 0.088, 0.0), 1.75),
    (3, (0.3, 0.3, 0.15, 0.5), 1.80),
    (21, (0.1, 0.2, 0.06, 0.25), 1.70),
]


@pytest.mark.parametrize("seed,args,k", GOLDEN_LIMA)
def test_rule_c_fit_reproduces_calibrate_c(seed, args, k):
    prev, dep, cv, sig = args
    meas = C.population(2000, prev, dep, cv, sig, C.MIXED, np.random.default_rng(seed))[0]
    fit = R.rule_c_fit(meas, seed + 1)
    cut, k_direct = C.calibrate_c(C.rule_c_scores(meas), rng=np.random.default_rng(seed + 1))
    assert np.allclose(fit["_z"], C.rule_c_scores(meas))
    assert fit["k"] == pytest.approx(k_direct) == pytest.approx(k)
    assert fit["cut"] == pytest.approx(cut, abs=1e-4)
    assert fit["null_rate"] <= R.NULL_TARGET
    assert len(fit["shape"]) == len(fit["scale"]) == 16


def test_rule_c_z_matches_the_pooled_scores():
    meas = C.population(500, 0.0, 0.0, 0.08, 0.0, C.MIXED, np.random.default_rng(2))[0]
    fit = R.rule_c_fit(meas, 1)
    assert np.allclose(R.rule_c_z(meas[17], fit), fit["_z"][17], atol=5e-3)  # config stores 4 dp


# ------------------------------------------------------------------------------------ depth
def test_detectable_depth_reproduces_hotel_e7_primary_rows():
    """cv_n 0.088, Lima's shape, the measured 9.668 mm median: 0.30 at RC 0, 0.35 at RC 1.0."""
    for rc, want in ((0.0, 0.30), (1.0, 0.35)):
        d = C.detectable_depth(0.088, C.LIMA_SHAPE, rc, seed=31000, median_mm=9.668)
        assert d["depth"] == want
        assert d["false_flag"] <= 0.02


def test_gate_equals_s3_detectable_depth_at_the_same_seed():
    pop = Y.population(300, seed=4)
    cfg = R.pooled(pop)
    ag = R.read_agreement(Y.reads(pop), cfg)
    g = R.gate("thinning", cfg, ag, seed=77)
    rc = max(ag["thinning"]["rc"]["territory"][t]["rc"] for t in R.TERRITORIES)
    want = C.detectable_depth(cfg["thinning"]["cv_n"], np.asarray(cfg["thinning"]["shape"]), rc,
                              seed=77, median_mm=cfg["thinning"]["median_level"])
    assert g["depth"] == want["depth"] and g["sens_range"] == want["sens_range"]
    assert g["pass"] == (want["depth"] is not None and want["depth"] <= R.DEPTH_GATE)


def test_gate_fails_without_rc_or_above_half():
    cfg = {"thinning": {"cut": -2.0, "cv_n": 0.25, "shape": list(C.LIMA_SHAPE),
                        "median_level": 6.0}}
    assert R.gate("thinning", cfg, {"thinning": {"rc": {"status": "not_computed"}}})["pass"] \
        is False
    rc = {"status": "computed", "scale": "difference",
          "territory": {t: {"rc": 1.0} for t in R.TERRITORIES}}
    g = R.gate("thinning", cfg, {"thinning": {"rc": rc}}, seed=3)
    assert g["pass"] is False and (g["depth"] is None or g["depth"] > R.DEPTH_GATE)


# ------------------------------------------------------------------------------------ RC
def _d(rng, n, sd, offset=0.0):
    base = rng.normal(1.0, 0.5, n)
    e1, e2 = rng.normal(0, sd / math.sqrt(2), (2, n))
    return list(base + e1 + offset), list(base + e2)


def test_rc_is_the_upper_95_bound_pooled_by_default():
    rng = np.random.default_rng(0)
    d1, d2 = {}, {}
    for t in R.TERRITORIES:
        d1[t], d2[t] = _d(rng, 20, 0.3)
    rc = R.repeatability(d1, d2)
    from scipy.stats import chi2

    diffs = np.concatenate([np.subtract(d1[t], d2[t]) for t in R.TERRITORIES])
    sd = np.std(diffs, ddof=1)
    n = len(diffs)
    want = 1.96 * sd * math.sqrt((n - 1) / chi2.ppf(0.025, n - 1))
    for t in R.TERRITORIES:
        assert rc["territory"][t]["source"] == "pooled"
        assert rc["territory"][t]["rc"] == pytest.approx(want, abs=1e-3)
        assert rc["territory"][t]["rc_point"] == pytest.approx(1.96 * sd, abs=1e-3)
    assert rc["scale"] == "difference"


def test_rc_uses_a_noisy_territorys_own_sd():
    rng = np.random.default_rng(1)
    d1, d2 = {}, {}
    d1["LAD"], d2["LAD"] = _d(rng, 20, 1.5)
    d1["LCx"], d2["LCx"] = _d(rng, 20, 0.2)
    d1["RCA"], d2["RCA"] = _d(rng, 10, 0.2)
    rc = R.repeatability(d1, d2)["territory"]
    assert rc["LAD"]["source"] == "territory"
    assert rc["LCx"]["source"] == "pooled"
    assert "n_T 10" in rc["RCA"]["decision"] and rc["RCA"]["source"] == "pooled"


def test_rc_adds_a_systematic_reader_offset():
    rng = np.random.default_rng(3)
    d1, d2 = {}, {}
    for t in R.TERRITORIES:
        d1[t], d2[t] = _d(rng, 20, 0.2, offset=0.5)
    rc = R.repeatability(d1, d2)["territory"]["LAD"]
    assert "added" in rc["decision"]
    assert rc["rc"] > 1.96 * rc["sd"] + 0.4


def test_rc_switches_to_log_ratios_when_error_grows_with_the_level():
    rng = np.random.default_rng(2)
    d1, d2 = {}, {}
    for t in R.TERRITORIES:
        lvl = rng.uniform(5, 200, 20)
        d1[t] = list(lvl * np.exp(rng.normal(0, 0.2, 20)))
        d2[t] = list(lvl * np.exp(rng.normal(0, 0.2, 20)))
    rc = R.repeatability(d1, d2)
    assert rc["scale"] == "log"
    assert R.rc_abs(rc, "LAD", 10.0) == pytest.approx(
        (math.exp(rc["territory"]["LAD"]["rc"]) - 1) * 10.0)


def test_kappa_not_estimable_below_five_and_icc_agrees():
    assert R.cohen_kappa([1, 1, 0, 0], [1, 1, 0, 0]) == pytest.approx(1.0)
    assert R.icc_2_1([1, 2, 3, 4], [1, 2, 3, 4]) == pytest.approx(1.0)
    pop = Y.population(60, seed=1)
    cfg = R.pooled(pop)
    ag = R.read_agreement(Y.reads(pop), cfg)
    assert ag["thinning"]["n_units"] == 120
    assert ag["fat"]["kappa"] is None and "not estimable" in ag["fat"]["kappa_status"]


# ------------------------------------------------------------------------------------ fat
def test_fat_cut_takes_the_least_strict_cell_under_five_percent():
    grid = {f"{c}_{v}": 0.2 for c in (0, -30, -50, -100) for v in (5, 20, 50)}
    grid["-30_20"] = 0.04
    grid["-50_5"] = 0.01
    assert R.fat_choice(grid, 0.0)["c_hu"] == -30 and R.fat_choice(grid, 0.0)["v_mm3"] == 20
    none = {k: 0.5 for k in grid}
    assert R.fat_choice(none, 0.03)["rule"] == "patient_noise"
    assert R.fat_choice(none, 0.3)["rule"] == "none"


# ------------------------------------------------------------------------------------ config
@pytest.fixture(scope="module")
def built():
    pop = Y.population(300, seed=11)
    kw = dict(cases_sha="0" * 64, n_cases=300, rest_tpr_gate="pass", septal_arc_column=False,
              halves_note=True, model="synthetic", guard_mm=1.0)
    a = R.dumps(R.build_config(pop, Y.reads(pop), **kw))
    b = R.dumps(R.build_config(pop, Y.reads(pop), **kw))
    return a, b


def test_config_is_byte_identical_on_rerun_and_carries_no_id(built):
    a, b = built
    assert a == b
    cfg = json.loads(a)
    R.assert_anonymous(cfg)
    for k in ("version", "geometry_version", "guard_version", "cases_sha256", "n_cases",
              "label", "thinning", "hypoattenuation", "fat", "gate", "rc", "rest_tpr",
              "composite", "detectable_depth", "construct_checks", "page_line", "percentiles"):
        assert k in cfg, k
    assert cfg["label"] == "this population, phase-uncertain"
    for s in R.SIGNS:
        assert set(cfg["gate"][s]) >= {"depth", "pass", "kappa", "icc"}
        assert cfg[s]["status"] in ("flag", "number_only")
    assert cfg["thinning"]["null"]["patients"] == 20000


def test_load_refuses_unpinned_changed_and_accepts_pinned(built, tmp_path, monkeypatch):
    p = tmp_path / "reference-r1.json"
    p.write_text(built[0])
    with pytest.raises(R.ReferenceError, match="not pinned"):
        R.load(p)
    monkeypatch.setattr(guard, "REFERENCE_SHA256", hashlib.sha256(built[0].encode()).hexdigest())
    assert R.load(p).data["version"] == R.REFERENCE_VERSION
    p.write_text(built[0].replace('"n_cases": 300', '"n_cases": 301'))
    with pytest.raises(R.ReferenceError, match="pinned"):
        R.load(p)


# ------------------------------------------------------------------------------------ CLI
def _tool():
    import importlib.util

    spec = importlib.util.spec_from_file_location("build_reference", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_cli_prints_the_fir_command_and_runs_nothing(capsys):
    assert _tool().main([]) == 0
    out = capsys.readouterr().out
    assert "sbatch --account=def-aso22" in out and "--run" in out and "must print 360" in out


def test_cli_run_refuses_outside_slurm(monkeypatch, capsys):
    monkeypatch.delenv("SLURM_JOB_ID", raising=False)
    assert _tool().main(["--run"]) == 3
    assert "REFUSED" in capsys.readouterr().err


def test_cli_run_refuses_a_held_out_case_before_opening_anything(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("SLURM_JOB_ID", "0")
    cases = tmp_path / "cases.txt"
    cases.write_text("\n".join(R.derive_cases()[1:] + [sorted(sealed_r1.load().seal)[0]]))
    missing = str(tmp_path / "does-not-exist")
    rc = _tool().main(["--run", "--cases", str(cases), "--hc", missing, "--layout", missing,
                       "--icx", missing, "--splits", str(REPO / guard.SPLITS_RELPATH),
                       "--reads", missing, "--out", str(tmp_path / "out.json"),
                       "--rest-tpr-gate", "fail", "--septal-arc-column", "drop",
                       "--halves-note", "no"])
    assert rc == 3
    err = capsys.readouterr().err
    assert "REFUSED: HeldOutError" in err and "Nothing was opened" in err
    assert not (tmp_path / "out.json").exists()
