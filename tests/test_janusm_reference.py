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

from janusm import calibrate as C
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
    rc_t = ag["thinning"]["rc"]
    e = R.population_expected(cfg["thinning"])
    rc = max(R.rc_floor_mm(rc_t, t, e[t]) for t in R.TERRITORIES)
    want = C.detectable_depth(cfg["thinning"]["cv_n"], np.asarray(cfg["thinning"]["shape"]), rc,
                              seed=77, **R.s3_wall_kwargs("thinning", cfg["thinning"]))
    assert g["depth"] == want["depth"] and g["sens_range"] == want["sens_range"]
    assert g["s3_wall_input"] == {"measured_median_mm": cfg["thinning"]["median_level"]}
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


def _exact(rng, n, sd, offset=0.0):
    """Two reads whose differences have SD ``sd`` and mean exactly ``offset``."""
    base = rng.normal(1.0, 0.5, n)
    e = rng.normal(0, 1, n)
    e = (e - e.mean()) / e.std(ddof=1) * sd
    return list(base + e + offset), list(base)


def test_chi2_factor_at_20_patients():
    from scipy.stats import chi2

    assert chi2.ppf(0.025, 19) == pytest.approx(8.907, abs=1e-3)
    assert R._chi2_factor(20) == pytest.approx(1.4606, abs=1e-4)


def test_rc_is_the_upper_95_bound_pooled_by_default():
    """R4-S7 (JA63): 20 patients x 3 territories is n = 20, not 60: factor 1.4606."""
    rng = np.random.default_rng(0)
    d1, d2 = {}, {}
    for t in R.TERRITORIES:
        d1[t], d2[t] = _exact(rng, 20, 0.3)
    rc = R.repeatability(d1, d2)
    diffs = np.concatenate([np.subtract(d1[t], d2[t]) for t in R.TERRITORIES])
    sd = np.std(diffs, ddof=1)
    assert rc["n_patients"] == 20 and rc["n_values"] == 60
    assert rc["pooled"]["n_patients"] == 20 and rc["pooled"]["n_values"] == 60
    for t in R.TERRITORIES:
        r = rc["territory"][t]
        assert r["source"] == "pooled" and r["n"] == 20 and "added" not in r["decision"]
        assert r["rc"] == pytest.approx(1.96 * sd * 1.4606, abs=1e-3)
        assert r["rc_point"] == pytest.approx(1.96 * sd, abs=1e-3)
    assert rc["scale"] == "difference"


def test_rc_counts_patients_by_the_case_index():
    """The case index travels with each pair: two positions of one case are one patient."""
    rng = np.random.default_rng(4)
    d1, d2 = {}, {}
    for t in R.TERRITORIES:
        d1[t], d2[t] = _exact(rng, 6, 0.3)
    rc = R.repeatability(d1, d2, cases=[0, 0, 1, 1, 2, 2])
    assert rc["n_patients"] == 3 and rc["n_values"] == 18
    assert rc["territory"]["LAD"]["n_territory"] == 3


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


@pytest.mark.parametrize("n_lad,source", [(14, "pooled"), (15, "territory")])
def test_rc_own_sd_needs_15_patients(n_lad, source):
    """R4-S7: the 14-vs-15 boundary of JA42 step 3, in patients."""
    rng = np.random.default_rng(5)
    d1, d2 = {}, {}
    d1["LAD"], d2["LAD"] = _exact(rng, n_lad, 2.0)
    for t in ("LCx", "RCA"):
        d1[t], d2[t] = _exact(rng, 20, 0.2)
    r = R.repeatability(d1, d2)["territory"]["LAD"]
    assert r["n_territory"] == n_lad and r["source"] == source


def test_rc_adds_a_systematic_reader_offset():
    rng = np.random.default_rng(3)
    d1, d2 = {}, {}
    for t in R.TERRITORIES:
        d1[t], d2[t] = _d(rng, 20, 0.2, offset=0.5)
    rc = R.repeatability(d1, d2)["territory"]["LAD"]
    assert "added" in rc["decision"]
    assert rc["rc"] > 1.96 * rc["sd"] + 0.4


def test_rc_adds_each_territorys_own_offset():
    """R4-S7 (JA63 step 4a): +0.4 on LAD and -0.4 on LCx cancel in the pooled mean; each is
    added to its own territory, and RCA gets nothing."""
    rng = np.random.default_rng(6)
    d1, d2 = {}, {}
    for t, off in (("LAD", 0.4), ("LCx", -0.4), ("RCA", 0.0)):
        d1[t], d2[t] = _exact(rng, 20, 0.2, offset=off)
    rc = R.repeatability(d1, d2)
    assert abs(rc["pooled"]["mean_diff"]) < 1e-6
    t = rc["territory"]
    for name, off in (("LAD", 0.4), ("LCx", -0.4)):
        assert t[name]["mean_diff"] == pytest.approx(off, abs=1e-6)
        assert "added" in t[name]["decision"]
        assert t[name]["rc"] == pytest.approx(1.96 * t[name]["sd"] * 1.4606 + 0.4, abs=1e-3)
    assert "added" not in t["RCA"]["decision"]
    assert t["RCA"]["rc"] == pytest.approx(1.96 * t["RCA"]["sd"] * 1.4606, abs=1e-3)


def _proportional(rng, n=20, cv=0.08):
    """Signed D around 0 whose read noise grows with E (proportional thinning noise)."""
    d1, d2, e1, e2 = {}, {}, {}, {}
    for t in R.TERRITORIES:
        e = np.exp(rng.uniform(np.log(0.3), np.log(30.0), n))
        d = rng.normal(0, 0.2, n)
        d1[t] = list(d + e * rng.normal(0, cv, n))
        d2[t] = list(d + e * rng.normal(0, cv, n))
        e1[t] = list(e * (1 + rng.normal(0, 0.01, n)))
        e2[t] = list(e * (1 + rng.normal(0, 0.01, n)))
    return d1, d2, e1, e2


def test_rc_switches_to_relative_when_error_grows_with_e():
    """R4-S8 (JA64): proportional noise switches to "relative"; the floor at E is RC_rel x E."""
    d1, d2, e1, e2 = _proportional(np.random.default_rng(2))
    rc = R.repeatability(d1, d2, e1, e2)
    assert rc["scale"] == "relative" and rc["spearman_rho"] > R.SPEARMAN_LOG
    assert "Δ / Ē" in rc["decisions"][0]
    v = rc["territory"]["LAD"]["rc"]
    for e in (3.0, 7.5):
        assert R.rc_floor_mm(rc, "LAD", e) == pytest.approx(v * e)
    assert R.rc_floor_mm(rc, "LAD", 0.0) is None and R.rc_floor_mm(rc, "LAD", None) is None


def test_rc_stays_on_differences_when_e_is_not_positive():
    """R4-S8: signed D with rho > 0.4 but some E <= 0 stays on differences, decision recorded."""
    d1, d2, e1, e2 = _proportional(np.random.default_rng(2))
    e1["RCA"][3] = -0.5
    rc = R.repeatability(d1, d2, e1, e2)
    assert rc["scale"] == "difference" and rc["spearman_rho"] > R.SPEARMAN_LOG
    assert "E_T <= 0" in rc["decisions"][0]
    assert R.rc_floor_mm(rc, "LAD", 5.0) == rc["territory"]["LAD"]["rc"]


def test_fat_multiplicative_noise_stays_on_differences():
    """R4-S8 (JA64): fat's RC is always on differences, in mm³, however its noise scales."""
    rng = np.random.default_rng(2)
    d1, d2 = {}, {}
    for t in R.TERRITORIES:
        lvl = rng.uniform(5, 200, 20)
        d1[t] = list(lvl * np.exp(rng.normal(0, 0.2, 20)))
        d2[t] = list(lvl * np.exp(rng.normal(0, 0.2, 20)))
    rc = R.repeatability(d1, d2)
    assert rc["scale"] == "difference" and "mm³" in rc["decisions"][0]
    assert R.rc_floor_mm(rc, "LAD", 50.0) == rc["territory"]["LAD"]["rc"]
    pop = Y.population(60, seed=1, fat_share=0.5)
    ag = R.read_agreement(Y.reads(pop), R.pooled(pop))
    assert ag["fat"]["rc"]["scale"] == "difference"
    assert ag["fat"]["rc"]["spearman_rho"] is None


def test_spearman_exactly_04_stays_on_differences(monkeypatch):
    """R4-S15: the switch is rho > 0.4; exactly 0.4 stays on differences."""
    monkeypatch.setattr(R, "_spearman", lambda x, y: 0.4)
    d1, d2, e1, e2 = _proportional(np.random.default_rng(2))
    rc = R.repeatability(d1, d2, e1, e2)
    assert rc["scale"] == "difference" and rc["spearman_rho"] == 0.4
    assert "<= 0.4" in rc["decisions"][0]


def test_no_log_branch_and_no_level_one_remain():
    """R4-S8: the (e^RC - 1) conversion and the level of 1.0 are deleted."""
    import inspect

    from janusm import report as P

    assert not hasattr(R, "rc_abs")
    for mod in (R, P):
        src = inspect.getsource(mod)
        assert "math.exp" not in src and "level = 1.0" not in src
        assert '"level", 1.0' not in src


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
                       "--halves-note", "no", "--geodesic-shared", "no"])
    assert rc == 3
    err = capsys.readouterr().err
    assert "REFUSED: HeldOutError" in err and "Nothing was opened" in err
    assert not (tmp_path / "out.json").exists()


# ------------------------------------------------------------------------------------ R4-S9
def test_a_fat_segment_that_changes_territory_moves_d():
    """R4-S9 (JA63 step 1): fat's D is per patient-map territory; rule C's fat flag stays AHA."""
    from janusm import features as F

    seg = np.zeros((6, 6, 6), np.int16)
    seg[1:5, 1:5, 1:5] = 1                    # segment 1: LAD on the AHA map
    core = seg > 0
    ct = np.full(seg.shape, 60.0, np.float32)
    ct[2:4, 2:4, 2:4] = -60.0                 # one 8-voxel fat cluster
    aha, _ = F.fat_cluster_volumes(ct, core, seg, 1.0, 0)
    lad, _ = F.fat_cluster_volumes(ct, core, seg, 1.0, 0, {1: "LAD"})
    lcx, _ = F.fat_cluster_volumes(ct, core, seg, 1.0, 0, {1: "LCx"})
    assert aha["LAD"] == lad["LAD"] == [8.0] and lcx["LCx"] == [8.0] and lcx["LAD"] == []

    pop = Y.population(60, seed=1)
    cfg = R.pooled(pop)
    cfg["fat"].update(c_hu=0, v_mm3=5)
    rec = dict(pop[0])
    rec["fat_clusters_mm3"] = {"0": {"LAD": [30.0], "LCx": [], "RCA": [], "none": []}}
    rec["fat_clusters_mm3_patient"] = {"0": {"LAD": [], "LCx": [30.0], "RCA": [], "none": []}}
    st = R.case_state(rec, cfg)
    assert st["fat"]["D"] == {"LAD": 0.0, "LCx": 30.0, "RCA": 0.0}
    assert st["fat"]["territory_rule_c"] == {"LAD": True, "LCx": False, "RCA": False}
    assert st["fat"]["map"] == "patient" and st["map"] == "patient"


def test_a_forced_fallback_is_counted():
    """R4-S9 (JA63): no patient map -> "aha_fallback", counted in rc["decisions"]."""
    pop = Y.population(60, seed=1)
    cfg = R.pooled(pop)
    reads = Y.reads(pop)
    for r in reads[:3]:
        r["read_1"].pop("segment_territory")
        r["read_1"].pop("fat_clusters_mm3_patient")
    st = R.case_state(reads[0]["read_1"], cfg)
    assert st["map"] == "aha_fallback" and st["thinning"]["map"] == "aha_fallback"
    assert st["fat"]["map"] == "aha_fallback"
    ag = R.read_agreement(reads, cfg)
    for s in R.SIGNS:
        assert ag[s]["rc"]["aha_fallback_reads"] == 3
        assert "3 of 40 reads fell back to the AHA default map (JA63)" in ag[s]["rc"]["decisions"]
    assert R.case_state(reads[5]["read_1"], cfg)["map"] == "patient"


def test_d_is_on_the_patient_map_not_aha():
    """R4-S15: D uses the patient map; segment 1 moved to LCx changes LAD's and LCx's D."""
    pop = Y.population(60, seed=1)
    cfg = R.pooled(pop)
    rec = dict(pop[3])
    rec["segment_territory"] = {**rec["segment_territory"], 1: "LCx", 7: "LCx"}
    st = R.case_state(rec, cfg)
    v = R.sign_values(rec, "thinning")
    shape = np.asarray(cfg["thinning"]["shape"])
    want = R.territory_deviation(v, shape, R.F.territory_segments(rec, "patient"))
    aha = R.territory_deviation(v, shape, R.F.territory_segments(rec, "aha"))
    assert st["thinning"]["D"] == want and want["LAD"] != aha["LAD"]


# ------------------------------------------------------------------------------------ R4-S10
@pytest.mark.parametrize("sign", ["thinning", "hypoattenuation"])
def test_gate_gives_s3_the_measured_wall(monkeypatch, sign):
    """R4-S10 (JA60): a recording S3 sees measured_median_mm (= median_level) and, for
    hypoattenuation, the ED-only phase mix."""
    seen = {}

    def s3(cv_n, shape, rc, *, sig_m=0.0, seed, measured_median_mm=None, median_mm=None,
           phase_mix=None):
        seen.update(measured_median_mm=measured_median_mm, median_mm=median_mm,
                    phase_mix=phase_mix)
        return {"depth": 0.3, "sens_range": [0.8, 0.9], "false_flag": 0.01}

    monkeypatch.setattr(C, "detectable_depth", s3)
    cfg = {sign: {"cut": -2.0, "cv_n": 0.1, "shape": list(C.LIMA_SHAPE), "median_level": 5.9}}
    rc = {"status": "computed", "scale": "difference",
          "territory": {t: {"rc": 0.5} for t in R.TERRITORIES}}
    g = R.gate(sign, cfg, {sign: {"rc": rc}}, seed=3)
    assert seen["measured_median_mm"] == 5.9 and seen["median_mm"] is None
    assert seen["phase_mix"] == ({"ED": 1.0, "MD": 0.0, "SYS": 0.0} if sign == "hypoattenuation"
                                 else None)
    assert g["s3_wall_input"]["measured_median_mm"] == 5.9 and g["pass"]


# ------------------------------------------------------------------------------------ R4-S15
def _gate_with_depth(monkeypatch, depth):
    monkeypatch.setattr(C, "detectable_depth", lambda *a, **k: {
        "depth": depth, "sens_range": [0.8, 0.8], "false_flag": 0.0})
    cfg = {"thinning": {"cut": -2.0, "cv_n": 0.1, "shape": list(C.LIMA_SHAPE),
                        "median_level": 6.0}}
    rc = {"status": "computed", "scale": "difference",
          "territory": {t: {"rc": 0.5} for t in R.TERRITORIES}}
    return R.gate("thinning", cfg, {"thinning": {"rc": rc, "kappa": None}})


def test_depth_050_passes_and_055_fails(monkeypatch):
    assert _gate_with_depth(monkeypatch, 0.50)["pass"] is True
    assert _gate_with_depth(monkeypatch, 0.55)["pass"] is False
    assert _gate_with_depth(monkeypatch, None)["pass"] is False


def test_a_pass_with_kappa_none(monkeypatch):
    g = _gate_with_depth(monkeypatch, 0.35)
    assert g["kappa"] is None and g["pass"] is True


def test_kappa_with_4_and_5_flagged_units():
    four = [True] * 4 + [False] * 56
    five = [True] * 5 + [False] * 55
    k, st = R.kappa_status(four, five)
    assert k is None and "not estimable" in st and "(4, 5)" in st
    k, st = R.kappa_status(five, five)
    assert k == pytest.approx(1.0) and st == "estimated"


def test_kappa_not_estimable_when_chance_agreement_is_one():
    k, st = R.kappa_status([True] * 60, [True] * 60)
    assert k is None and st == "not estimable: chance agreement pe = 1"


@pytest.mark.parametrize("has_rc", [True, False])
def test_fat_gate_with_and_without_an_rc(has_rc):
    rc = ({"status": "computed", "scale": "difference",
           "territory": {t: {"rc": 3.0} for t in R.TERRITORIES}} if has_rc
          else {"status": "not_computed"})
    cfg = {"fat": {"rule": "grid", "c_hu": -30, "v_mm3": 20}}
    g = R.gate("fat", cfg, {"fat": {"rc": rc, "kappa": None}})
    assert g["pass"] is has_rc and g["depth"] is None
    assert ("no RC" in g["why"]) is (not has_rc)


# ------------------------------------------------------------------------------------ R4-S11
SYNTH_GOLDEN = Path(__file__).parent / "fixtures/janusm/reference_synth.json"
REGEN = __import__("os").environ.get("JANUSM_REGEN_GOLDEN") == "1"


def test_config_records_versions(built):
    cfg = json.loads(built[0])
    assert cfg["calibrate_version"] == C.CALIBRATE_VERSION
    assert cfg["features_version"] == R.F.FEATURES_VERSION
    assert set(cfg["percentiles"]["septal_arc"]) == {"wall_mm", "rel_subendo_hu"}


def test_golden_config_is_byte_identical(built):
    """R4-S11: the 300-heart synthetic population (seed 11). Regenerate with
    ``JANUSM_REGEN_GOLDEN=1 pytest tests/test_janusm_reference.py`` and review the diff."""
    if REGEN:
        SYNTH_GOLDEN.write_bytes(built[0].encode("utf-8"))
    assert built[0].encode("utf-8") == SYNTH_GOLDEN.read_bytes()


def test_config_sha_matches_under_the_c_locale(built, tmp_path):
    """R4-S11: the file is UTF-8 bytes and its sha is of the bytes written, whatever the locale
    (the config carries non-ASCII: ≥, Δ, mm³)."""
    import os
    import subprocess

    src = tmp_path / "cfg.json"
    src.write_bytes(built[0].encode("utf-8"))
    out = tmp_path / "out.json"
    code = ("import importlib.util, json, sys\n"
            f"spec = importlib.util.spec_from_file_location('b', {str(TOOL)!r})\n"
            "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)\n"
            f"cfg = json.loads(open({str(src)!r}, encoding='utf-8').read())\n"
            f"print(m.write_config({str(out)!r}, cfg))\n")
    env = {k: v for k, v in os.environ.items() if not k.startswith(("LC_", "LANG", "PYTHONUTF8",
                                                                     "PYTHONIOENCODING"))}
    env.update(LC_ALL="C", LANG="C", PYTHONUTF8="0", PYTHONCOERCECLOCALE="0",
               PYTHONPATH=str(REPO / "src"))
    r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    data = out.read_bytes()
    assert any(b > 127 for b in data)
    assert data == built[0].encode("utf-8")
    assert r.stdout.strip() == hashlib.sha256(data).hexdigest()


# ------------------------------------------------------------------------------------ R4-S12
def test_cli_run_without_geodesic_shared_is_refused(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("SLURM_JOB_ID", "0")
    x = str(tmp_path / "x")
    with pytest.raises(SystemExit) as e:
        _tool().main(["--run", "--cases", x, "--hc", x, "--layout", x, "--icx", x,
                      "--splits", x, "--reads", x, "--out", x, "--rest-tpr-gate", "fail",
                      "--septal-arc-column", "drop", "--halves-note", "no"])
    assert e.value.code == 2
    assert "--geodesic-shared" in capsys.readouterr().err
    assert "--geodesic-shared <R8: yes|no>" in _tool().FIR_COMMAND
