"""Janus-M border reads (JA7): labels, protocol, read set, hold-out adapter, the read
checker, the anchoring report and the seeds. No network, no database, no CT: the
checker runs on a synthetic heart (``janusm_reads.phantom``)."""

import ast
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from janusm_reads import (  # noqa: E402
    BORDER_PROTOCOL,
    PROTOCOL_NAME,
    PROTOCOL_VERSION,
    anchoring,
    checker,
    holdout,
    phantom,
    protocol,
    readset,
    seeds,
)
from janusm_reads import labels as L  # noqa: E402

SPLITS = json.loads((REPO / "trillium-results/icx14/results/splits.json").read_text())


def juliet_draw():
    """JA6's draw (Juliet's draw_m0.py, as committed): seal 60, decision 40 from train."""
    left = sorted(SPLITS["train"])
    out = {}
    for name, salt, n in (("seal", "asclepius-janusm-seal-r1:", 60),
                          ("decision", "asclepius-janusm-decision-r1:", 40)):
        pick = sorted(left, key=lambda c: hashlib.sha256((salt + c).encode()).hexdigest())[:n]
        out[name] = pick
        left = [c for c in left if c not in set(pick)]
    return out


# ------------------------------------------------------------------- labels


def test_ja1_labels():
    assert L.CLASSES == {1: "LV myocardium", 2: "LV blood pool", 3: "RV blood pool",
                         4: "LA blood pool"}
    assert L.missing_required({"1": 5, "2": 3, "3": 0}) == [3, 4]
    assert L.missing_required({1: 1, 2: 1, 3: 1, 4: 1}) == []
    assert L.invalid_values([0, 1, 4, 5, 9]) == [5, 9]
    assert "papillary" in L.CONVENTIONS[L.LV_POOL]


def test_protocol_v1_conventions_are_written_down():
    """S5 point 7: the label text carries protocol v1 (Hotel v3 section 5.1, JA46)."""
    assert "outer edge of the blood-filled recesses" in L.CONVENTIONS[L.LV_POOL]
    assert "aortic valve plane" in L.CONVENTIONS[L.LV_POOL]
    assert "mitral gap is 0 or 1" in L.CONVENTIONS[L.LV_POOL]
    assert "above the mitral annulus is not labelled" in L.CONVENTIONS[L.LV_MYO]
    assert "tricuspid annulus to the pulmonary valve" in L.CONVENTIONS[L.RV_POOL]
    assert "appendage" in L.CONVENTIONS[L.LA_POOL]
    assert "pulmonary veins" in L.CONVENTIONS[L.LA_POOL]
    doc = (REPO / "docs" / "JANUSM-READ-PROTOCOL.md").read_text(encoding="utf-8")
    assert "protocol v1 (JA21, JA46)" in doc
    section2 = doc.split("## 2.", 1)[1].split("\n## 3.", 1)[0]
    for phrase in ("outer edge of the blood-filled recesses", "appendage", "pulmonary veins",
                   "ostia", "aortic valve plane", "tricuspid annulus", "pulmonary valve",
                   "above the mitral annulus is not labelled", "mitral gap"):
        assert phrase in section2, phrase
    assert "[Round 2]" not in doc
    section9 = doc.split("## 9.", 1)[1]
    assert "Round 1 value" not in section9 and "border_protocol" in section9


# ----------------------------------------------------------------- protocol


def test_protocol_is_not_segqueue14s():
    from segqueue14 import PROTOCOL_VERSION as SQ14
    from segqueue14 import protocol as sq14

    assert PROTOCOL_VERSION == 1 and PROTOCOL_NAME == "janusm-read"
    assert protocol.API_PREFIX == "janusm" != sq14.API_PREFIX
    assert protocol.PROTOCOL_HEADER != sq14.PROTOCOL_HEADER
    assert SQ14 != PROTOCOL_VERSION
    assert protocol.path(protocol.SUBMIT, read_id="x") == "janusm/read/x/submit"


def test_border_protocol_is_its_own_number():
    """S5 point 9: border_protocol 1, apart from the wire PROTOCOL_VERSION."""
    import janusm_reads

    assert BORDER_PROTOCOL == 1 and "BORDER_PROTOCOL" in janusm_reads.__all__
    src = (REPO / "src" / "janusm_reads" / "__init__.py").read_text()
    assert "PROTOCOL_VERSION = 1" in src and "BORDER_PROTOCOL = 1" in src

@pytest.mark.parametrize("sent", [None, "", "zero", 0, 2, 14, 16])  # 14, 16: SegQueue14
def test_protocol_refuses_missing_or_old_client(sent):
    with pytest.raises(protocol.ProtocolError) as err:
        protocol.check_client_protocol(sent)
    assert err.value.code == protocol.ERR_CLIENT_TOO_OLD


def test_protocol_accepts_current_and_roundtrips():
    protocol.check_client_protocol(PROTOCOL_VERSION)
    info = protocol.ReadInfo(read_id="r", case_name="c0001", state=protocol.ASSIGNED,
                             has_seed=True, checksum="ab", size_bytes=3)
    assert protocol.ReadInfo.from_dict(info.to_dict()) == info
    sub = protocol.ReadSubmission.from_dict({"checksum": "AB", "sizeBytes": 3,
                                             "voxelCounts": {"1": 2}, "future": 1})
    assert sub.checksum == "ab" and sub.voxel_counts == {"1": 2}
    assert protocol.ReadSubmission.from_dict(sub.to_dict()) == sub
    info.flagged, info.check_profile = True, {"endocardial": {"s_mm": [0.0], "hu": [1.0]}}
    assert protocol.ReadInfo.from_dict(info.to_dict()) == info
    assert protocol.can_move(protocol.ASSIGNED, protocol.SUBMITTED)
    assert protocol.can_move(protocol.SUBMITTED, protocol.RETURNED)
    assert not protocol.can_move(protocol.ACCEPTED, protocol.SUBMITTED)
    assert not protocol.can_move(protocol.RELEASED, protocol.ASSIGNED)


FORM = {"LM": "0", "LAD": "3", "LCx": "1", "RCA": "N"}


def test_read_form_is_per_vessel_cadrads_2_with_an_optional_lesion_point():
    """S5 point 6 (JA46 (d))."""
    assert protocol.VESSELS == ("LM", "LAD", "LCx", "RCA")
    assert protocol.CADRADS_GRADES == ("0", "1", "2", "3", "4A", "4B", "5", "N")
    assert protocol.read_form_problems(FORM) == []
    assert protocol.read_form_problems(FORM, {"LAD": [1.0, -2.5, 30.0]}) == []
    assert "LM, LAD, LCx, RCA not graded" in protocol.read_form_problems({})[0]
    assert "RCA not graded" in protocol.read_form_problems({**FORM, "RCA": ""})[0]
    assert "not a CAD-RADS 2.0 grade" in protocol.read_form_problems({**FORM, "LM": "6"})[0]
    assert "not a graded vessel" in protocol.read_form_problems({**FORM, "OM1": "2"})[0]
    assert "three numbers" in protocol.read_form_problems(FORM, {"LAD": [1.0, 2.0]})[0]
    # No lesion point on a vessel graded 0 or N.
    assert "names a lesion" in protocol.read_form_problems(FORM, {"LM": [0, 0, 0]})[0]
    sub = protocol.ReadSubmission.from_dict({"cadrads": {"LM": "4a", "LAD": "0", "LCx": "0",
                                                         "RCA": "0"},
                                             "lesionPoints": {"LM": [1, 2, 3]}})
    assert sub.cadrads["LM"] == "4A" and sub.lesion_points == {"LM": [1.0, 2.0, 3.0]}
    assert sub.form_problems() == []
    assert protocol.ReadSubmission.from_dict({}).form_problems()


def test_return_once_then_accept_and_flag_is_on_the_wire():
    """S5 point 3: one return, then accept with flagged and reasons."""
    assert protocol.MAX_RETURNS == 1
    check = {"config": {"tolerance_mm": 0.5}, "borders": {
        "endocardial": {"offset_mm": 0.8, "threshold_hu": 270.0, "plateaus_hu": [420, 120],
                        "profile": {"s_mm": [-1.0, 0.0, 1.0], "hu": [420.0, 270.0, 120.0]}},
        "epicardial": {"offset_mm": 0.1, "profile": {"s_mm": [0.0], "hu": [0.0]}},
        "septal_rv": {"offset_mm": None, "profile": {}}}}
    prof = protocol.profile_for_reader(check)
    assert set(prof) == {"endocardial", "epicardial"}
    assert prof["endocardial"]["failed"] and not prof["epicardial"]["failed"]
    assert prof["endocardial"]["thresholdHU"] == 270.0
    assert prof["endocardial"]["plateausHU"] == [420, 120]
    assert protocol.profile_for_reader(None) == {}


# ------------------------------------------------------------------ read set


def test_freeze_parsing_and_refusals():
    draw = juliet_draw()
    sets = readset.parse_freeze({"seal": {"cases": draw["seal"]}, "decision": draw["decision"]})
    assert len(sets["seal"]) == 60 and len(sets["decision"]) == 40
    with pytest.raises(readset.ReadSetError):
        readset.parse_freeze({"seal": draw["seal"]})
    with pytest.raises(readset.ReadSetError):
        readset.parse_freeze({"seal": draw["seal"][:59], "decision": draw["decision"]})
    with pytest.raises(readset.ReadSetError):
        readset.parse_freeze({"seal": draw["seal"],
                              "decision": draw["decision"][:39] + draw["seal"][:1]})
    with pytest.raises(readset.ReadSetError):
        readset.parse_freeze({"seal": draw["seal"][:59] + ["imagecas_0001"],
                              "decision": draw["decision"]})


def test_missing_freeze_file_serves_nothing(tmp_path):
    with pytest.raises(readset.ReadSetError, match="missing"):
        readset.load_freeze(tmp_path / "sealed-r1.json")


def test_blank_pick_is_ten_seal_cases_and_stable():
    draw = juliet_draw()
    blank = readset.blank_cases(draw["seal"])
    assert len(blank) == 10 and set(blank) <= set(draw["seal"])
    assert readset.blank_cases(list(reversed(draw["seal"]))) == blank
    # Growing the seal (JA6's extension) never changes which cases are blank.
    grown = draw["seal"] + [c for c in sorted(SPLITS["train"]) if c not in draw["seal"]][:60]
    assert readset.blank_cases(grown) == blank


def test_plan_serves_decision_first_two_reads_each():
    draw = juliet_draw()
    plan = readset.plan(draw)
    assert len(plan) == 100 and all(p.reads == 2 for p in plan)
    assert [p.read_set for p in plan[:40]] == ["decision"] * 40
    assert all(p.priority > q.priority for p in plan[:40] for q in plan[40:])
    assert sum(p.blank for p in plan) == 10
    assert not any(p.blank for p in plan if p.read_set == "decision")
    assert readset.imagecas_number("c0001") == 2


# ------------------------------------------------------------------- holdout

A14 = json.loads((REPO / "trillium/icx4/sealed_test.json").read_text())
POOL_SEAL = json.loads((REPO / "configs/segqueue14/sealed-pool-2026-10.json").read_text())


def test_the_committed_freeze_is_the_juliet_draw_and_passes_the_guard():
    sets = readset.load_freeze()
    draw = juliet_draw()
    assert {k: set(v) for k, v in sets.items()} == {k: set(v) for k, v in draw.items()}
    purposes = holdout.refuse_read_cases(sets["seal"] + sets["decision"], sets, what="test")
    assert {purposes[c] for c in sets["seal"]} == {holdout.SEAL_SCORING}
    assert {purposes[c] for c in sets["decision"]} == {holdout.DECISION_SCORING}


def test_a_changed_freeze_file_is_refused(tmp_path):
    draw = juliet_draw()
    draw["decision"].reverse()
    (tmp_path / "sealed-r1.json").write_text(json.dumps(draw))
    with pytest.raises(readset.ReadSetError, match="pinned"):
        readset.load_freeze(tmp_path / "sealed-r1.json")


def test_janusm_seal_and_decision_roles_come_from_the_guard():
    sets = readset.load_freeze()
    seal, decision = sets["seal"][0], sets["decision"][0]
    holdout.refuse([seal], purpose=holdout.SEAL_SCORING)
    holdout.refuse([decision], purpose=holdout.DECISION_SCORING)
    for name, purpose in ((seal, holdout.ANY), (seal, holdout.DECISION_SCORING),
                          (decision, holdout.ANY), (decision, holdout.SEAL_SCORING)):
        with pytest.raises(holdout.HoldoutError, match="Janus-M"):
            holdout.refuse([name], purpose=purpose)


@pytest.mark.parametrize("name,source,why", [
    ("c0002", None, "A14 sealed 100"),
    (SPLITS["val"][0], None, "val 80"),
    (A14["open_icx_test"][0], None, "test split"),
    ("TotalSegmentator-cardiac__s0655", None, "pool seal"),
    (POOL_SEAL["primary"]["extension_order"][0], None, "reserve"),   # A34 reserve patient
    ("s0356", "TotalSegmentator", "reserve"),
    ("s0019", "TotalSegmentator", "twin"),                           # Round 1 §4 twin
])
def test_coronary_holdouts_are_refused_through_the_guard(name, source, why):
    with pytest.raises(holdout.HoldoutError, match=why):
        holdout.refuse([name], what="test", source=source)


def test_cases_outside_the_freeze_are_refused():
    sets = readset.load_freeze()
    stranger = next(c for c in sorted(SPLITS["train"])
                    if c not in sets["seal"] and c not in sets["decision"])
    holdout.refuse([stranger])            # the guard alone would let it through
    with pytest.raises(holdout.HoldoutError, match="not in the frozen"):
        holdout.refuse_read_cases([stranger], sets)


def test_no_guard_means_no_read(monkeypatch):
    import janusm

    monkeypatch.delattr(janusm, "guard", raising=False)
    monkeypatch.setitem(sys.modules, "janusm.guard", None)   # import fails
    with pytest.raises(holdout.HoldoutError, match="cannot be imported"):
        holdout.refuse(["c0000"])


# ------------------------------------------------------------------- checker


@pytest.fixture(scope="module")
def heart():
    truth, spacing = phantom.heart()
    ct = phantom.ct_from(truth, spacing, noise_hu=15.0)
    return truth, ct, spacing


def test_true_labels_pass_the_half_maximum_rule(heart):
    truth, ct, spacing = heart
    report = checker.check_read(truth, ct, spacing)
    assert report.passed, report.errors
    for border in ("endocardial", "epicardial", "septal_rv"):
        assert abs(report.borders[border].offset_mm) < 0.3
    assert report.plateaus_hu["lv_blood"] == pytest.approx(420, abs=10)
    assert report.plateaus_hu["epicardial_fat"] == pytest.approx(-100, abs=10)
    out = json.loads(report.to_json())
    assert out["border_protocol"] == BORDER_PROTOCOL == 1
    assert out["offsetSign"].startswith("canonical")


def test_the_tolerance_is_half_a_millimetre_and_octants_only_warn():
    """S5 point 2 (JA21, JA46 (c))."""
    cfg = checker.CheckConfig()
    assert cfg.tolerance_mm == 0.5 and cfg.octant_warning_mm == 1.0


# Canonical sign (JA44): + = the region bounded by the border extends beyond the edge.
# move_border(+mm) grows the region past the edge, so its offset is +mm.
@pytest.mark.parametrize("border,mm", [("endocardial", 2.0), ("endocardial", -2.0),
                                       ("epicardial", 2.0), ("epicardial", -1.5),
                                       ("endocardial", 1.0), ("epicardial", -0.75)])
def test_a_border_off_by_more_than_half_a_millimetre_fails_in_the_canonical_sign(heart,
                                                                                  border, mm):
    """S5 points 2 and 8: the whole-border median decides; offsets are canonical."""
    truth, ct, spacing = heart
    report = checker.check_read(phantom.move_border(truth, spacing, border, mm), ct, spacing)
    assert not report.passed
    assert report.borders[border].offset_mm == pytest.approx(mm, abs=0.4)
    assert report.offsets()[border] == report.borders[border].offset_mm
    message = next(e for e in report.errors if border in e)
    assert ("past" if mm > 0 else "short of") in message and "median" in message


def test_a_moved_endocardium_reads_plus_one_millimetre():
    """JA44's own example, on the read checker: the LV pool grown 1 mm past the edge."""
    truth, spacing = phantom.heart()
    ct = phantom.ct_from(truth, spacing)
    report = checker.check_read(phantom.move_border(truth, spacing, "endocardial", 1.0), ct,
                                spacing)
    assert report.borders["endocardial"].offset_mm == pytest.approx(1.0, abs=0.25)


def test_a_border_within_half_a_millimetre_passes(heart):
    truth, ct, spacing = heart
    report = checker.check_read(phantom.move_border(truth, spacing, "epicardial", 0.25), ct,
                                spacing)
    assert report.passed, report.errors
    tight = checker.check_read(phantom.move_border(truth, spacing, "epicardial", 0.25), ct,
                               spacing, checker.CheckConfig(tolerance_mm=0.1))
    assert not tight.passed


def test_a_local_border_error_is_a_warning_not_a_failure(heart):
    """S5 point 2 (JA46 (c)): an octant beyond 1.0 mm warns; the whole border decides."""
    truth, ct, spacing = heart
    read = phantom.move_border(truth, spacing, "epicardial", 2.5, octant=3)
    report = checker.check_read(read, ct, spacing)
    whole = report.borders["epicardial"].offset_mm
    assert abs(whole) <= 0.5 and report.passed, (whole, report.errors)
    assert any("Part of the epicardial border (octant3)" in w for w in report.warnings)
    assert not any("octant" in e for e in report.errors)


def test_every_border_keeps_its_profile_for_the_reader(heart):
    """S5 point 3: the profile (HU against signed distance, both plateaus, the half
    level) goes back with a returned read."""
    truth, ct, spacing = heart
    report = checker.check_read(phantom.move_border(truth, spacing, "endocardial", 2.0), ct,
                                spacing)
    endo = report.to_dict()["borders"]["endocardial"]
    prof = endo["profile"]
    assert len(prof["s_mm"]) == len(prof["hu"]) > 10
    lo, hi = endo["plateaus_hu"]
    assert endo["threshold_hu"] == pytest.approx((lo + hi) / 2)
    # The image edge is at s = -offset: the profile crosses the half level there.
    s, hu = np.array(prof["s_mm"]), np.array(prof["hu"])
    at = np.interp(-endo["offset_mm"], s, hu)
    assert at == pytest.approx(endo["threshold_hu"], abs=40)
    reader = protocol.profile_for_reader(report.to_dict())
    assert reader["endocardial"]["failed"] and not reader["epicardial"]["failed"]


def test_label_conventions(heart):
    truth, ct, spacing = heart
    no_septum = truth.copy()
    no_septum[(truth == L.LV_MYO) & (np.indices(truth.shape)[2] * spacing[2] > 18.0)] = L.RV_POOL
    report = checker.check_read(no_septum, ct, spacing)
    assert any("septum" in e for e in report.errors)

    pap, sp = phantom.heart(papillary=True)
    errors, _ = checker.check_conventions(pap, sp)
    assert any("papillary" in e for e in errors)

    missing = truth.copy()
    missing[missing == L.LA_POOL] = 0
    assert not checker.check_read(missing, ct, spacing).passed

    bad = truth.copy()
    bad[0, 0, 0] = 7
    report = checker.check_read(bad, ct, spacing)
    assert any("not Janus-M classes" in e for e in report.errors)


def test_lv_rv_contact_stays_at_half_a_percent(heart):
    """S5 point 4 (JA46 (b)): a little LV-RV contact (the membranous septum) passes."""
    truth, ct, spacing = heart
    assert checker.CheckConfig().max_pool_contact_share == 0.005
    errors, _ = checker.check_conventions(truth, spacing)
    assert not any("septum" in e for e in errors)


@pytest.fixture(scope="module")
def gap_heart():
    truth, spacing = phantom.heart(mitral_gap_mm=2.0)
    return truth, phantom.ct_from(truth, spacing, noise_hu=10.0), spacing


def test_the_mitral_gap_phantom_passes_and_its_plane_is_fitted(gap_heart):
    truth, ct, spacing = gap_heart
    report = checker.check_read(truth, ct, spacing, seed=truth)
    assert report.passed, report.errors
    assert not any("mitral plane" in w for w in report.warnings)
    centre, normal, radius, source = checker.mitral_plane(truth, spacing, seed=truth)
    assert source == "seed" and abs(normal[0]) > 0.99 and normal[0] < 0  # towards the LA
    assert checker.mitral_plane(truth, spacing)[3] == "read"             # a blank case
    assert checker.pool_above_mitral_mm(truth, spacing, (centre, normal, radius, source)) < 3
    # Without a gap anywhere and no hinge points: a warning, not a failure.
    plain, sp = phantom.heart()
    errors, warnings = checker.check_conventions(plain, sp)
    assert not errors and any("mitral plane could not be fitted" in w for w in warnings)
    # Hinge points fit it when nothing else can.
    hinges = [(10.0, 0.0, 0.0), (10.0, 5.0, 0.0), (10.0, 0.0, 5.0), (10.0, 5.0, 5.0)]
    assert checker.mitral_plane(plain, sp, hinge_points_mm=hinges)[3] == "hinge points"


def test_labels_2_and_4_never_share_a_face(gap_heart):
    """S5 point 4: a hard check (JA46 (a))."""
    truth, ct, spacing = gap_heart
    read = truth.copy()
    pool = truth == L.LV_POOL
    from scipy import ndimage

    grown = ndimage.binary_dilation(pool, iterations=6) & (truth == L.LV_MYO)
    read[grown & (np.indices(truth.shape)[0] * spacing[0] < 24.0)] = L.LV_POOL  # through the gap
    report = checker.check_read(read, ct, spacing, seed=truth)
    assert any("LV and LA blood pools share a face" in e for e in report.errors)


def test_the_lv_pool_reaches_at_most_3_mm_above_the_seeds_mitral_plane(gap_heart):
    """S5 point 4: label 2 <= 3 mm above the JA46 (a) plane, fitted to the seed."""
    from scipy import ndimage

    truth, ct, spacing = gap_heart
    pool, la = truth == L.LV_POOL, truth == L.LA_POOL
    centre, normal, radius, _ = checker.mitral_plane(truth, spacing, seed=truth)
    pts = np.indices(truth.shape).reshape(3, -1).T * np.asarray(spacing)
    rel = pts - centre
    height = (rel @ normal).reshape(truth.shape)
    inplane = np.sqrt(np.maximum(0, (rel ** 2).sum(1) - (rel @ normal) ** 2)).reshape(
        truth.shape)
    # Push the pool 5 mm into the LA over the mitral footprint, then keep a gap of
    # myocardium so no 2-4 face is made: only the plane check can see it.
    extra = (height > 0) & (height <= 5.0) & (inplane <= radius) & ~pool
    read = truth.copy()
    read[extra] = L.LV_POOL
    rim = ndimage.binary_dilation(read == L.LV_POOL) & (read == L.LA_POOL)
    read[rim] = L.LV_MYO
    errors, _ = checker.check_conventions(read, spacing, seed=truth)
    assert not any("share a face" in e for e in errors)
    assert any("above the mitral plane (fitted to the seed" in e for e in errors), errors
    assert la.any()


def test_check_files_refuses_another_grid(tmp_path, heart):
    import nibabel as nib

    truth, ct, spacing = heart
    nib.save(nib.Nifti1Image(truth, np.diag([0.5, 0.5, 0.5, 1])), str(tmp_path / "r.nii.gz"))
    nib.save(nib.Nifti1Image(ct, np.diag([0.5, 0.5, 0.5, 1])), str(tmp_path / "ct.nii.gz"))
    assert checker.check_files(tmp_path / "r.nii.gz", tmp_path / "ct.nii.gz").passed
    assert checker.check_files(tmp_path / "r.nii.gz", tmp_path / "ct.nii.gz",
                               seed_path=tmp_path / "r.nii.gz").passed
    nib.save(nib.Nifti1Image(ct, np.diag([0.6, 0.5, 0.5, 1])), str(tmp_path / "ct2.nii.gz"))
    with pytest.raises(ValueError):
        checker.check_files(tmp_path / "r.nii.gz", tmp_path / "ct2.nii.gz")


# --------------------------------------------------------------------- seeds


def test_seed_maps_coarsens_and_keeps_every_class(heart):
    truth, _, spacing = heart
    ts = np.zeros(truth.shape, dtype=np.int16)
    names = {v: k for k, v in seeds.TS_FALLBACK_IDS.items()}
    for name, value in seeds.TS_TO_JA1.items():
        ts[truth == value] = names[name]
    ts[:2] = names["aorta"]                    # not a JA1 class: background in the seed
    assert set(np.unique(seeds.map_to_ja1(ts, seeds.TS_FALLBACK_IDS))) <= {0, 1, 2, 3, 4}
    seed = seeds.make_seed(ts, spacing, seeds.TS_FALLBACK_IDS)
    assert seed.dtype == np.uint8 and seed.shape == truth.shape
    assert set(np.unique(seed)) == {0, 1, 2, 3, 4}
    assert not seed[:2].any()
    for value in L.REQUIRED:
        a, b = seed == value, truth == value
        dice = 2 * (a & b).sum() / (a.sum() + b.sum())
        assert 0.7 < dice < 1.0, (value, dice)   # rough, as it should be


# ----------------------------------------------------------------- anchoring


def test_anchoring_numbers(heart):
    truth, ct, spacing = heart
    seed = seeds.coarsen(truth, spacing)
    a = phantom.move_border(truth, spacing, "epicardial", 0.5)
    row = anchoring.case_anchoring("c0001", seed, [truth, a], spacing, blank=False)
    assert row.inter_read["endocardial"] == pytest.approx(0.0, abs=1e-6)
    assert 0.2 < row.inter_read["epicardial"] < 1.0
    assert all(0 < c < 0.5 for c in row.changed)


def test_rule1_is_a_two_sample_bootstrap_with_a_0p2_mm_margin():
    """S5 point 5 (JA47 rule 1)."""
    assert anchoring.RULE1_MARGIN_MM == 0.2 and anchoring.BOOTSTRAP_DRAWS == 2000
    # gap 0.5 - inter 0.2 = 0.3 > 0.2, with no spread: exceeds.
    r = anchoring.rule1_bound([1.0] * 4, [0.5] * 6, [0.2] * 6)
    assert r["statistic"] == pytest.approx(0.3) and r["upper95"] == pytest.approx(0.3)
    assert r["exceeds"] and (r["blankCases"], r["seededCases"]) == (4, 6)
    # gap 0.3 - inter 0.2 = 0.1: within the margin.
    assert not anchoring.rule1_bound([0.8] * 3, [0.5] * 5, [0.2] * 5)["exceeds"]
    # The bound is the upper one, so spread can push an in-margin mean over it.
    rng = np.random.default_rng(1)
    blank = list(0.75 + rng.normal(0, 0.3, 10))
    seeded = list(0.5 + rng.normal(0, 0.3, 40))
    wide = anchoring.rule1_bound(blank, seeded, [0.2] * 40)
    assert wide["upper95"] > wide["statistic"]
    # Fixed seed: the same inputs give the same bound.
    assert anchoring.rule1_bound(blank, seeded, [0.2] * 40) == wide
    # Two samples of different sizes; no case is paired across them.
    assert anchoring.rule1_bound([1.0], [0.5, 0.6], [0.1, 0.1]) is not None
    assert anchoring.rule1_bound([], [0.5], [0.1]) is None
    assert anchoring.rule1_bound([0.5], [None], [0.1]) is None


def test_rule1_on_a_wave(heart):
    truth, ct, spacing = heart
    seed = seeds.coarsen(truth, spacing)
    a = phantom.move_border(truth, spacing, "epicardial", 0.5)
    # Seeded reads that copy the seed, blank reads that do not: anchored.
    rows = [anchoring.case_anchoring(f"c{i:04d}", seed, [seed, seed], spacing, False)
            for i in range(3)]
    rows += [anchoring.case_anchoring(f"c{i:04d}", seed, [truth, a], spacing, True)
             for i in range(3, 5)]
    report = anchoring.wave_report("1", rows)
    assert report["borders"]["epicardial"]["rule1"]["exceeds"] is True
    assert report["seededReadsMayAcceptModel"] is False
    assert report["border_protocol"] == 1

    # Seeded and blank reads equally far from the seed: not anchored.
    fine = [anchoring.case_anchoring(f"c{i:04d}", seed, [truth, a], spacing, i >= 3)
            for i in range(5)]
    report = anchoring.wave_report("1", fine)
    assert report["borders"]["endocardial"]["rule1"]["exceeds"] is False
    assert report["rule2"]["flagged"] is False
    assert report["seededReadsMayAcceptModel"] is True
    assert anchoring.wave_report("1", fine[:3])["seededReadsMayAcceptModel"] is None


def test_rule2_flags_a_wave_that_follows_the_seed_and_draws_five_third_reads(heart):
    """S5 point 5 (JA47 rule 2)."""
    truth, ct, spacing = heart
    seed = seeds.coarsen(truth, spacing)
    a = phantom.move_border(truth, spacing, "epicardial", 0.5)
    names = [f"c{i:04d}" for i in range(10)]
    # 8 seeded cases whose reads leave the seed as it is, 2 blank cases.
    rows = [anchoring.case_anchoring(n, seed, [seed, seed], spacing, False) for n in names[:8]]
    rows += [anchoring.case_anchoring(n, seed, [truth, a], spacing, True) for n in names[8:]]
    report = anchoring.wave_report("2", rows)
    rule2 = report["rule2"]
    assert rule2["flagged"] and rule2["readsChangingUnder5pct"] == 16
    drawn = rule2["thirdReadCases"]
    assert len(drawn) == 5 and set(drawn) <= set(names[:8])           # seeded cases only
    assert drawn == anchoring.third_read_cases("2", list(reversed(names[:8])))
    assert drawn != anchoring.third_read_cases("3", names[:8])         # salted per wave
    assert rule2["thirdReadsDone"] == 0 and rule2["rule1OnThirdReads"] is None
    assert report["seededReadsMayAcceptModel"] is False                # rule 1 fails anyway

    # Third reads from blank on the drawn cases, as far from the seed as a blank read:
    # rule 1 on them fails too.
    with_third = [anchoring.case_anchoring(n, seed, [seed, seed], spacing, False,
                                           third=truth if n in drawn else None)
                  for n in names[:8]] + rows[8:]
    report = anchoring.wave_report("2", with_third)
    on_third = report["rule2"]["rule1OnThirdReads"]
    assert report["rule2"]["thirdReadsDone"] == 5
    assert on_third["endocardial"]["blankCases"] == 5 and on_third["endocardial"]["exceeds"]
    assert report["seededReadsMayAcceptModel"] is False
    row = next(r for r in report["rows"] if r["case"] == drawn[0])
    assert set(row["thirdReadVsSeed"]) == {"endocardial", "epicardial"}


def test_rule2_pending_third_reads_leave_the_verdict_open(heart):
    truth, ct, spacing = heart
    seed = seeds.coarsen(truth, spacing)
    # Seeded reads that leave the seed as it is, and blank reads as close to it: rule 1
    # passes, rule 2 flags, and the wave waits for its third reads.
    rows = [anchoring.case_anchoring(f"c{i:04d}", seed, [seed, seed], spacing, False)
            for i in range(6)]
    rows += [anchoring.case_anchoring(f"c{i:04d}", seed, [seed, seed], spacing, True)
             for i in range(6, 8)]
    report = anchoring.wave_report("4", rows)
    assert report["rule2"]["flagged"]
    assert all(not b["rule1"]["exceeds"] for b in report["borders"].values())
    assert report["seededReadsMayAcceptModel"] is None


def test_seed_and_read_half_maximum_offsets_go_into_the_report(heart):
    """S5 point 5: the seed's and the reads' half-maximum offsets (canonical)."""

    truth, ct, spacing = heart
    grown = phantom.move_border(truth, spacing, "endocardial", 1.0)
    offsets = anchoring.halfmax_offsets(grown, ct, spacing)
    assert offsets["endocardial"] == pytest.approx(1.0, abs=0.3)
    row = anchoring.case_anchoring("c0001", grown, [truth, truth], spacing, False,
                                   halfmax={"seed": offsets, "reads": [
                                       anchoring.halfmax_offsets(truth, ct, spacing)] * 2})
    report = anchoring.wave_report("1", [row])
    assert report["halfMaxOffsets"]["endocardial"]["seedMedian"] == pytest.approx(
        offsets["endocardial"])
    assert abs(report["halfMaxOffsets"]["endocardial"]["readMedian"]) < 0.3
    assert report["rows"][0]["halfMaxOffsets"]["seed"] == offsets


@pytest.mark.parametrize("case", ["c0002", "c0000"])   # A14 sealed; train but not frozen
def test_anchoring_manifest_refuses_a_holdout(tmp_path, case):
    (tmp_path / "m.json").write_text(json.dumps(
        {"wave": "1", "cases": [{"case": case, "seed": "s", "reads": ["a", "b"]}]}))
    with pytest.raises(holdout.HoldoutError):
        anchoring.report_from_manifest(tmp_path / "m.json")


# ------------------------------------------------------------- the seed job


def test_seed_job_refuses_a_holdout_before_touching_anything(tmp_path, monkeypatch):
    sys.path.insert(0, str(REPO / "tools" / "janusm"))
    import make_seeds

    draw = juliet_draw()
    draw["decision"][0] = "c0002"   # an A14 sealed case
    monkeypatch.setattr(make_seeds.readset, "load_freeze", lambda path=None: draw)
    out = tmp_path / "seeds"
    with pytest.raises(holdout.HoldoutError, match="A14"):
        make_seeds.main(["--freeze", "unused", "--layout", str(tmp_path / "none.json"),
                         "--totalseg-dir", str(tmp_path / "hc"), "--out", str(out)])
    assert not out.exists() and not (tmp_path / "hc").exists()


# ---------------------------------------------------------------- portability

STDLIB_ONLY = ("__init__", "labels", "protocol", "readset", "holdout")


@pytest.mark.parametrize("module", STDLIB_ONLY)
def test_client_side_modules_are_stdlib_only_and_py39(module):
    path = REPO / "src" / "janusm_reads" / f"{module}.py"
    tree = ast.parse(path.read_text(), feature_version=(3, 9))
    allowed = set(sys.stdlib_module_names) | {"janusm_reads", "janusm"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots = [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            roots = [] if node.level else [(node.module or "").split(".")[0]]
        else:
            continue
        for root in roots:
            assert root in allowed, f"{module}.py imports {root}"


# -------------------------------------------------------------------- client


class _Response:
    def __init__(self, status=200, body=None, content=b""):
        self.status_code, self._body, self._content = status, body, content

    def json(self):
        if self._body is None:
            raise ValueError("no JSON")
        return self._body

    def iter_content(self, chunk_size=1):
        for i in range(0, len(self._content), chunk_size):
            yield self._content[i:i + chunk_size]


class _Session:
    """Answers like the janusm plugin, and records every request."""

    def __init__(self, ct=b"CT bytes", queue_empty=False):
        self.calls, self.ct, self.queue_empty, self.chunks = [], ct, queue_empty, []

    def request(self, method, url, headers=None, stream=False, **kw):
        path = url.split("/api/v1/", 1)[1]
        self.calls.append((method, path, headers, kw))
        if path == "janusm/project":
            return _Response(body={"uploadFolderId": "F1", "protocolVersion": 1})
        if path == "janusm/next":
            if self.queue_empty:
                return _Response(404, {"message": "x", "extra": {
                    "code": protocol.ERR_QUEUE_EMPTY, "message": "none"}})
            return _Response(body={"readId": "R1", "caseName": "c0001", "state": "assigned",
                                   "hasSeed": False,
                                   "checksum": hashlib.sha256(self.ct).hexdigest()})
        if path == "janusm/read/R1/ct":
            return _Response(content=self.ct)
        if path == "file":
            return _Response(body={"_id": "U1"})
        if path == "file/chunk":
            self.chunks.append(kw["data"])
            return _Response(body={"_id": "FILE1"})
        if path == "janusm/read/R1/submit":
            meta = json.loads(kw["params"]["meta"])
            assert kw["params"]["fileId"] == "FILE1"
            return _Response(body={"readId": "R1", "caseName": "c0001", "state": "submitted",
                                   "hasSeed": False, "checkSummary": str(meta["sizeBytes"])})
        if path == "janusm/read/R1/release":
            return _Response(body={"readId": "R1", "state": "released", "hasSeed": False})
        return _Response(426, {"message": "too old", "extra": {
            "code": protocol.ERR_CLIENT_TOO_OLD, "message": "too old"}})


def test_client_reads_a_case_end_to_end(tmp_path):
    from janusm_reads.client import JanusMClient

    session = _Session()
    c = JanusMClient("https://janus.example/", session=session, token="T")
    read = c.next_read()
    assert read.case_name == "c0001" and not read.has_seed
    assert c.download_seed(read, str(tmp_path / "seed.nii.gz")) is None   # blank case
    c.download_ct(read, str(tmp_path / "ct.nii.gz"))
    assert (tmp_path / "ct.nii.gz").read_bytes() == session.ct
    label = tmp_path / "read.nii.gz"
    label.write_bytes(b"label" * 10)
    done = c.submit(read, str(label), {1: 5, 2: 5, 3: 5, 4: 5})
    assert done.state == "submitted" and done.check_summary == "50"
    assert b"".join(session.chunks) == label.read_bytes()
    assert c.release(read).state == "released"
    for _, _, headers, _ in session.calls:
        assert headers[protocol.PROTOCOL_HEADER] == "1" and headers["Girder-Token"] == "T"


def test_client_refuses_a_bad_download_and_reports_codes(tmp_path):
    from janusm_reads.client import JanusMClient, JanusMError

    session = _Session()
    c = JanusMClient("https://janus.example/api/v1", session=session)
    read = c.next_read()
    session.ct = b"something else"
    with pytest.raises(JanusMError) as err:
        c.download_ct(read, str(tmp_path / "ct.nii.gz"))
    assert err.value.code == protocol.ERR_CHECKSUM and not (tmp_path / "ct.nii.gz").exists()
    assert JanusMClient("h", session=_Session(queue_empty=True)).next_read() is None
    with pytest.raises(JanusMError) as err:
        c._json("GET", "janusm/unknown")
    assert err.value.status == 426 and err.value.code == protocol.ERR_CLIENT_TOO_OLD
