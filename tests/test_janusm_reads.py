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


# ----------------------------------------------------------------- protocol


def test_protocol_is_not_segqueue14s():
    from segqueue14 import PROTOCOL_VERSION as SQ14
    from segqueue14 import protocol as sq14

    assert PROTOCOL_VERSION == 1 and PROTOCOL_NAME == "janusm-read"
    assert protocol.API_PREFIX == "janusm" != sq14.API_PREFIX
    assert protocol.PROTOCOL_HEADER != sq14.PROTOCOL_HEADER
    assert SQ14 != PROTOCOL_VERSION
    assert protocol.path(protocol.SUBMIT, read_id="x") == "janusm/read/x/submit"


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
    assert protocol.can_move(protocol.ASSIGNED, protocol.SUBMITTED)
    assert protocol.can_move(protocol.SUBMITTED, protocol.RETURNED)
    assert not protocol.can_move(protocol.ACCEPTED, protocol.SUBMITTED)
    assert not protocol.can_move(protocol.RELEASED, protocol.ASSIGNED)


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
    json.loads(report.to_json())


@pytest.mark.parametrize("border,mm,sign", [("endocardial", 2.0, -1), ("endocardial", -2.0, 1),
                                            ("epicardial", 2.0, -1), ("epicardial", -1.5, 1)])
def test_a_border_off_by_more_than_the_tolerance_fails(heart, border, mm, sign):
    truth, ct, spacing = heart
    report = checker.check_read(phantom.move_border(truth, spacing, border, mm), ct, spacing)
    assert not report.passed
    offset = report.borders[border].offset_mm
    assert sign * offset == pytest.approx(abs(mm), abs=0.4)
    assert any(border in e for e in report.errors)


def test_a_border_within_the_tolerance_passes(heart):
    truth, ct, spacing = heart
    report = checker.check_read(phantom.move_border(truth, spacing, "epicardial", 0.5), ct,
                                spacing)
    assert report.passed, report.errors
    tight = checker.check_read(phantom.move_border(truth, spacing, "epicardial", 0.5), ct,
                               spacing, checker.CheckConfig(tolerance_mm=0.25))
    assert not tight.passed


def test_a_local_border_error_is_caught_by_its_sector(heart):
    truth, ct, spacing = heart
    read = phantom.move_border(truth, spacing, "epicardial", 2.5, octant=3)
    report = checker.check_read(read, ct, spacing)
    assert not report.passed
    assert abs(report.borders["epicardial"].offset_mm) < 1.0   # the whole border hides it
    assert any("Part of the epicardial border" in e for e in report.errors)


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


def test_check_files_refuses_another_grid(tmp_path, heart):
    import nibabel as nib

    truth, ct, spacing = heart
    nib.save(nib.Nifti1Image(truth, np.diag([0.5, 0.5, 0.5, 1])), str(tmp_path / "r.nii.gz"))
    nib.save(nib.Nifti1Image(ct, np.diag([0.5, 0.5, 0.5, 1])), str(tmp_path / "ct.nii.gz"))
    assert checker.check_files(tmp_path / "r.nii.gz", tmp_path / "ct.nii.gz").passed
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


def test_anchoring_numbers_and_flag(heart):
    truth, _, spacing = heart
    seed = seeds.coarsen(truth, spacing)
    a = phantom.move_border(truth, spacing, "epicardial", 0.5)
    row = anchoring.case_anchoring("c0001", seed, [truth, a], spacing, blank=False)
    assert row.inter_read["endocardial"] == pytest.approx(0.0, abs=1e-6)
    assert 0.2 < row.inter_read["epicardial"] < 1.0
    assert all(0 < c < 0.5 for c in row.changed)

    # Seeded reads that copy the seed, blank reads that do not: anchored.
    anchored = [anchoring.case_anchoring(f"c{i:04d}", seed, [seed, seed], spacing, False)
                for i in range(3)]
    anchored += [anchoring.case_anchoring(f"c{i:04d}", seed, [truth, a], spacing, True)
                 for i in range(3, 5)]
    report = anchoring.wave_report("1", anchored)
    assert report["borders"]["epicardial"]["anchored"] is True
    assert report["seededReadsMayAcceptModel"] is False

    # Seeded and blank reads equally far from the seed: not anchored.
    fine = [anchoring.case_anchoring(f"c{i:04d}", seed, [truth, a], spacing, i >= 3)
            for i in range(5)]
    report = anchoring.wave_report("1", fine)
    assert report["borders"]["endocardial"]["anchored"] is False
    assert report["seededReadsMayAcceptModel"] is True
    assert anchoring.wave_report("1", fine[:3])["seededReadsMayAcceptModel"] is None


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
