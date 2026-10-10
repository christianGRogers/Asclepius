"""Tests for segtrain.reads: A3 convention monitor, A10 scoring, A11 targets, A12 report.

All fixtures are tiny synthetic coronary trees (a Y-shaped left tree plus a separate
RCA), so the suite needs no case data and no tree-F1 implementation: functions that
score take a ``scorer`` and the tests pass a simple stand-in.
"""

from __future__ import annotations

import numpy as np
import pytest

from segtrain import reads as R

SP = (0.5, 0.5, 0.5)


def _segment_dist(shape, p0, p1):
    g = np.stack(np.meshgrid(*[np.arange(n) for n in shape], indexing="ij"), -1).astype(float)
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    v = p1 - p0
    t = np.clip(((g - p0) @ v) / (v @ v), 0, 1)
    return np.linalg.norm(g - (p0 + t[..., None] * v), axis=-1), t


def make_tree(shape=(48, 48, 48), radius=2.5, lm_len=8):
    """4-class tree: LM from the ostium down to the carina, LAD and LCx diverging, RCA apart."""
    ost = np.array([24.0, 20.0, 44.0])
    car = ost - [0, 0, lm_len]
    segs = {
        R.LM: (ost, car),
        R.LAD: (car, car + [12, 0, -26]),
        R.LCX: (car, car + [-12, 0, -26]),
        R.RCA: ([40.0, 40.0, 44.0], [40.0, 40.0, 6.0]),
    }
    dist = np.stack([_segment_dist(shape, a, b)[0] for a, b in segs.values()])
    lab = np.zeros(shape, np.uint8)
    inside = dist.min(0) <= radius
    lab[inside] = np.array(list(segs))[dist.argmin(0)][inside]
    return lab


def shift_carina(lab, mm, sp=SP):
    """Move the LM/LAD-LCx boundary distally (mm > 0) or proximally (mm < 0)."""
    from scipy import ndimage

    out = lab.copy()
    if mm > 0:
        d = ndimage.distance_transform_edt(lab != R.LM, sampling=sp)
        out[np.isin(lab, (R.LAD, R.LCX)) & (d <= mm)] = R.LM
    else:
        d = ndimage.distance_transform_edt(~np.isin(lab, (R.LAD, R.LCX)), sampling=sp)
        sel = (lab == R.LM) & (d <= -mm)
        _, ind = ndimage.distance_transform_edt(~np.isin(lab, (R.LAD, R.LCX)), return_indices=True)
        out[sel] = lab[tuple(ind)][sel]
    return out


def dice_scorer(ref, pred, spacing):
    """Stand-in for segtrain.tf1: per-class Dice over classes present in the reference."""
    out = {}
    for c in R.CLASSES:
        r, p = ref == c, pred == c
        if r.any():
            out[c] = 2 * (r & p).sum() / (r.sum() + p.sum())
    return out


@pytest.fixture(scope="module")
def tree():
    return make_tree()


# ----------------------------------------------------------------------------- A11
def test_a11_prime_keeps_each_reads_own_labels():
    a = np.array([0, 1, 2, 2, 3, 0, 4])
    b = np.array([0, 1, 3, 0, 3, 2, 4])
    ta, tb = R.a11_targets(a, b)
    assert ta.tolist() == a.tolist() and tb.tolist() == b.tolist()
    assert R.name_conflict(a, b).tolist() == [False, False, True, False, False, False, False]


def test_retired_a11_rule_only_on_request():
    a = np.array([0, 1, 2, 2, 3, 0, 4])
    b = np.array([0, 1, 3, 0, 3, 2, 4])
    ta, tb = R.a11_targets(a, b, conflict_ignore=True)
    assert ta.tolist() == [0, 1, R.IGNORE, 2, 3, 0, 4]
    assert tb.tolist() == [0, 1, R.IGNORE, 0, 3, 2, 4]


def test_a11_rejects_shape_mismatch():
    with pytest.raises(ValueError):
        R.a11_targets(np.zeros(3), np.zeros(4))


# ----------------------------------------------------------------------------- A3
def test_calibre_thin_tree_is_mostly_thin(tree):
    thick = R.calibre_fraction(tree > 0, SP)
    thin = R.calibre_fraction(make_tree(radius=1.0) > 0, SP)
    assert thin > thick
    assert thin > 0.8


def test_convention_check_passes_a_split_and_flags_a_thin_read(tree):
    ok = R.convention_check(tree, tree > 0, SP)
    assert not ok.thin and ok.union_dice_vs_mask == pytest.approx(1.0)
    thin_read = make_tree(radius=1.0)
    bad = R.convention_check(thin_read, tree > 0, SP, icx_lumen=thin_read > 0)
    assert bad.thin and len(bad.reasons) == 2


def test_wave_halts_above_ten_percent(tree):
    ok = R.convention_check(tree, tree > 0, SP)
    thin = R.convention_check(make_tree(radius=1.0), tree > 0, SP)
    assert not R.wave_halts([ok] * 10)
    assert not R.wave_halts([thin] + [ok] * 9)  # exactly 10 %
    assert R.wave_halts([thin, thin] + [ok] * 9)


# ----------------------------------------------------------------------------- A11 third read
def test_third_read_not_needed_for_small_carina_shift(tree):
    tr = R.third_read_triggers(tree, shift_carina(tree, 1.0), SP, scorer=dice_scorer)
    assert not tr.needed
    assert tr.lm_end_mm is not None and tr.lm_end_mm < 2.0


def test_third_read_on_lad_lcx_swap(tree):
    b = tree.copy()
    b[tree == R.LAD], b[tree == R.LCX] = R.LCX, R.LAD
    tr = R.third_read_triggers(tree, b, SP)
    assert tr.needed and tr.lad_lcx_swap > 0.9


def test_third_read_ramus_only_swap_is_exempt(tree):
    b = tree.copy()
    ramus = np.zeros(tree.shape, bool)
    ramus[:, :, 10:20] = tree[:, :, 10:20] == R.LAD  # pretend the distal LAD piece is a ramus
    b[ramus] = R.LCX
    tr = R.third_read_triggers(tree, b, SP, ramus_mask=ramus)
    assert tr.ramus_only and not tr.needed


def test_third_read_on_large_lm_disagreement(tree):
    tr = R.third_read_triggers(tree, shift_carina(tree, 7.0), SP)
    assert tr.needed and tr.lm_end_mm > 5


# ----------------------------------------------------------------------------- A10
def test_score_vs_reads_averages_over_reads(tree):
    other = shift_carina(tree, 1.5)
    res = R.score_vs_reads(tree, [tree, other], SP, scorer=dice_scorer)
    assert res["per_class"][R.RCA] == pytest.approx(1.0)
    assert res["per_class"][R.LM] < 1.0
    assert res["macro"] == pytest.approx(np.mean(list(res["per_class"].values())))


def test_inter_read_is_symmetric(tree):
    b = shift_carina(tree, 1.5)
    assert R.inter_read_tf1(tree, b, SP, dice_scorer) == R.inter_read_tf1(b, tree, SP, dice_scorer)


def test_acceptance_noninferiority():
    rng = np.random.default_rng(1)
    inter = [{c: 0.9 for c in R.CLASSES} for _ in range(100)]
    good = [{c: 0.9 + rng.normal(0, 0.02) for c in R.CLASSES} for _ in range(100)]
    bad = [{c: 0.85 + rng.normal(0, 0.02) for c in R.CLASSES} for _ in range(100)]
    assert R.acceptance(good, inter)["accepted"]
    res = R.acceptance(bad, inter)
    assert not res["accepted"] and all(not v["pass"] for v in res["per_class"].values())


def test_acceptance_skips_absent_classes():
    model = [{R.LM: 0.95}, {R.LM: 0.95, R.RCA: 0.9}]
    inter = [{R.LM: 0.9}, {R.LM: 0.9, R.RCA: 0.9}]
    res = R.acceptance(model, inter, n_boot=200)
    assert res["per_class"][R.LM]["n"] == 2 and res["per_class"][R.RCA]["n"] == 1
    assert R.LAD not in res["per_class"]
    assert not res["decisive"]  # provisional by default (A1a)


def test_acceptance_excludes_flagged_cases_and_reports_decisive():
    model = [{R.LM: 0.95}, {R.LM: 0.10}]
    inter = [{R.LM: 0.9}, {R.LM: 0.9}]
    res = R.acceptance(model, inter, n_boot=200, provisional=[False, False], flagged=[False, True])
    assert res["per_class"][R.LM]["n"] == 1 and res["n_flagged_excluded"] == 1
    assert res["decisive"] and res["accepted"]


# ----------------------------------------------------------------------------- A12b anchor
def test_carina_offset_reads_an_injected_shift(tree):
    mask = tree > 0
    zero = R.carina_offset(tree, tree, mask, SP)
    assert not zero.review and abs(zero.offset_mm) < 0.6
    distal = R.carina_offset(shift_carina(tree, 2.0), tree, mask, SP)
    proximal = R.carina_offset(shift_carina(tree, -2.0), tree, mask, SP)
    assert 1.0 < distal.offset_mm < 3.5
    assert -3.5 < proximal.offset_mm < -1.0


def test_carina_offset_reviews_missing_lm(tree):
    no_lm = tree.copy()
    no_lm[tree == R.LM] = R.LAD
    assert R.carina_offset(no_lm, tree, tree > 0, SP).review
    assert R.carina_offset(tree, no_lm, tree > 0, SP).review


def test_team_bias_subtracts_convention_and_uses_medians():
    rng = np.random.default_rng(0)
    floor = list(0.7 + rng.normal(0, 0.6, 50))
    res = R.team_bias(floor + [140.0, 38.0])  # two measurement failures do not move a median
    assert abs(res["bias_mm"]) < 0.4 and not res["flagged"]
    biased = list(0.7 + 2.0 + rng.normal(0, 0.6, 50))
    res = R.team_bias(biased)
    assert res["detected"] and res["flagged"] and not res["reinstruct"]
    assert R.team_bias(biased, previous_flag=True)["reinstruct"]


def test_team_bias_empty():
    assert R.team_bias([None, float("nan")])["n"] == 0


def test_habit_test_finds_opposite_habits():
    rng = np.random.default_rng(0)
    res = R.habit_test(
        {
            "x": list(1.5 + rng.normal(0, 0.6, 25)),
            "y": list(-1.5 + rng.normal(0, 0.6, 25)),
            "z": list(1.5 + rng.normal(0, 0.6, 25)),
        },
        n_perm=500,
    )
    flags = {(p["a"], p["b"]): p["habit"] for p in res["pairs"]}
    assert flags[("x", "y")] and flags[("y", "z")] and not flags[("x", "z")]
    assert res["habits"]


def test_habit_test_ignores_small_groups():
    res = R.habit_test({"x": [1.0, 2.0], "y": [0.0] * 10}, n_perm=100)
    assert res["pairs"] == [] and not res["habits"]


def test_truncation_radius(tree):
    mask = tree > 0
    assert R.truncation_radius(tree, mask, SP) is None
    trunc = tree.copy()
    trunc[:, :, :14] = 0
    r = R.truncation_radius(trunc, mask, SP)
    assert r is not None and 0.5 < r < 2.0


def test_icx_to_territory():
    icx = np.array([0, 1, 2, 4, 5, 3, 6, 7, 8, 12, 13, 9, 10, 11])
    assert R.icx_to_territory(icx).tolist() == [0, 1, 2, 2, 2, 3, 3, 3, 3, 3, 3, 4, 4, 4]


# ----------------------------------------------------------------------------- A12 report
def test_first_reads_report_on_a_folder(tmp_path, tree):
    nib = pytest.importorskip("nibabel")
    aff = np.diag(list(SP) + [1.0])
    masks = tmp_path / "masks"
    masks.mkdir()
    icx = tmp_path / "icx"
    icx.mkdir()
    reads = tmp_path / "reads"
    for k, (case, sa, sb) in enumerate(
        [("c0000", 1.0, -1.0), ("c0001", 1.5, -0.5), ("c0002", 0.5, -1.5)]
    ):
        (reads / case).mkdir(parents=True)
        nib.save(nib.Nifti1Image(shift_carina(tree, sa), aff), str(reads / case / "annX.nii.gz"))
        nib.save(nib.Nifti1Image(shift_carina(tree, sb), aff), str(reads / case / "annY.nii.gz"))
        nib.save(nib.Nifti1Image((tree > 0).astype(np.uint8), aff), str(masks / f"{case}.nii.gz"))
        icx14 = np.select(
            [tree == R.LM, tree == R.LAD, tree == R.LCX, tree == R.RCA], [1, 2, 3, 9], 0
        ).astype(np.uint8)
        nib.save(nib.Nifti1Image(icx14, aff), str(icx / f"{k + 1}.coronary.nii.gz"))
    cases = R.load_read_folder(str(reads), mask_dir=str(masks), icx_dir=str(icx))
    assert [c.case for c in cases] == ["c0000", "c0001", "c0002"]
    rep = R.first_reads_report(cases, scorer=dice_scorer)
    assert "naming_attribution" in rep["cases"][0]
    w = rep["wave"]
    assert w["n_cases"] == 3 and w["a3_reads_checked"] == 6 and not w["a3_halt"]
    assert w["adjudication_rate"] == 0.0
    assert set(w["inter_read_tf1"]) == set(R.CLASS_NAMES.values())
    assert w["a12b_team_bias"]["n"] == 6
    offs = {n: v["offset_mm"] for n, v in rep["cases"][0]["anchor"].items()}
    assert offs["annX"] > offs["annY"]
    md = R.report_markdown(rep)
    assert "A12b" in md and "Inter-read tF1" in md


def test_default_scorer_uses_segtrain_tf1():
    pytest.importorskip("segtrain.tf1")
    tree = make_tree(radius=3.0)  # tf1 places an ostium only on trees of >= 1000 voxels
    sp = (1.0, 1.0, 1.0)
    scorer = R.default_scorer()
    res = scorer(tree, tree, sp)
    per = res["per_class"]
    assert set(per) == set(R.CLASSES) and all(v == pytest.approx(1.0) for v in per.values())
    assert res["provisional"]  # no aorta mask: A1a
    cut = tree.copy()
    cut[:, :30, 30:33] = 0  # cut LAD and LCx below the carina (the RCA, at y = 40, is untouched)
    res = R.score_vs_reads(cut, [tree, tree], sp)
    assert res["provisional"]
    assert res["per_class"][R.LAD] < 0.9 and res["per_class"][R.RCA] == pytest.approx(1.0)


# ----------------------------------------------------------------------------- A12 attribution
def test_naming_attribution_carina_shift_is_a_decision(tree):
    pytest.importorskip("segtrain.namer")
    att = R.naming_attribution(tree, shift_carina(tree, 2.0), SP, use_namer=False)
    assert att["n_conflict_voxels"] > 0
    assert att["decision_share"] == pytest.approx(1.0)
    assert not att["wholesale"]


def test_naming_attribution_flags_a_swap(tree):
    pytest.importorskip("segtrain.namer")
    b = tree.copy()
    b[tree == R.LAD], b[tree == R.LCX] = R.LCX, R.LAD
    att = R.naming_attribution(tree, b, SP, use_namer=False)
    assert att["wholesale"] and "swap" in att["flags"]
    assert att["decision_share"] > 0.9


def test_naming_attribution_scattered_jitter_is_diffuse(tree):
    pytest.importorskip("segtrain.namer")
    rng = np.random.default_rng(0)
    b = tree.copy()
    far = (tree == R.LAD) & (np.arange(tree.shape[2])[None, None, :] < 16)
    idx = np.argwhere(far)
    pick = idx[rng.choice(len(idx), 15, replace=False)]
    b[tuple(pick.T)] = R.LCX  # isolated single-voxel name flips, far from the carina
    att = R.naming_attribution(tree, b, SP, use_namer=False)
    assert att["decision_share"] < 0.2


def test_imagecas_names_map_to_case_ids():
    assert R.case_id("imagecas_0002") == "c0001"
    assert R.case_id("imagecas_0003__r2") == "c0002"
    assert R.case_id("c0100") == "c0100"


def test_read_folder_merges_export_replicas(tmp_path, tree):
    nib = pytest.importorskip("nibabel")
    aff = np.diag(list(SP) + [1.0])
    for folder, lab in (("imagecas_0101", tree), ("imagecas_0101__r2", shift_carina(tree, 1.0))):
        d = tmp_path / folder / "segmentations"
        d.mkdir(parents=True)
        nib.save(
            nib.Nifti1Image(np.zeros(tree.shape, np.int16), aff),
            str(tmp_path / folder / "ct.nii.gz"),
        )
        for name, c in R.EXPORT_SEGMENTS.items():
            nib.save(nib.Nifti1Image((lab == c).astype(np.uint8), aff), str(d / f"{name}.nii.gz"))
    (case,) = R.load_read_folder(str(tmp_path))
    assert case.case == "c0100" and sorted(case.reads) == ["r1", "r2"]
    assert np.array_equal(case.reads["r1"], tree)


def test_lm_in_one_read_only_triggers_a_third_read(tree):
    no_lm = tree.copy()
    no_lm[tree == R.LM] = R.LAD
    tr = R.third_read_triggers(tree, no_lm, SP)
    assert tr.needed and "LM present in one read only" in tr.reasons  # Round 6 A21
    both_absent = R.third_read_triggers(no_lm, no_lm.copy(), SP)
    assert not both_absent.needed  # A4 absent-LM guard: agreed separate ostia


def test_report_scores_per_case_with_its_aorta(tmp_path, tree, monkeypatch):
    nib = pytest.importorskip("nibabel")
    aff = np.diag(list(SP) + [1.0])
    for case in ("c0000", "c0001"):
        d = tmp_path / "reads" / case
        d.mkdir(parents=True)
        nib.save(nib.Nifti1Image(tree, aff), str(d / "annX.nii.gz"))
        nib.save(nib.Nifti1Image(tree, aff), str(d / "annY.nii.gz"))
    (tmp_path / "aorta").mkdir()
    ao = np.zeros(tree.shape, np.uint8)
    ao[20:28, 16:24, 44:48] = 1
    nib.save(nib.Nifti1Image(ao, aff), str(tmp_path / "aorta" / "c0000_aorta.nii.gz"))
    cases = R.load_read_folder(str(tmp_path / "reads"), aorta_dir=str(tmp_path / "aorta"))
    assert cases[0].aorta is not None and cases[1].aorta is None
    seen = []

    def fake_default_scorer(**kw):
        seen.append(kw.get("aorta") is not None)
        return lambda ref, pred, sp: {
            "per_class": dice_scorer(ref, pred, sp),
            "provisional": "aorta" not in kw,
            "flagged": False,
        }

    monkeypatch.setattr(R, "default_scorer", fake_default_scorer)
    rep = R.first_reads_report(cases, per_case_tf1=True, use_namer=False)
    assert seen == [True, False]
    assert not rep["cases"][0]["inter_read_tf1"]["provisional"]
    assert rep["cases"][1]["inter_read_tf1"]["provisional"] and rep["wave"]["tf1_provisional"]
