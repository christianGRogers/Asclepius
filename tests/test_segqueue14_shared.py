"""SegQueue14's shared package: the 14 classes, the protocol, the plan, the NIfTI
header reader and the per-class scoring rule. No Girder, no Slicer.

``segqueue14`` lives in this repository's ``src/``. The suite may be running
against an installed copy of ``segtrain`` from another checkout that predates it,
so ``src/`` is appended to the path -- appended, not prepended, so every module
the rest of the suite already resolves keeps resolving to the same file.
"""

import gzip
import struct
import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.append(str(_SRC))

from segqueue import protocol as live_protocol  # noqa: E402
from segqueue14 import (  # noqa: E402
    PROTOCOL_VERSION,
    labels,
    nifti,
    protocol,  # noqa: E402
)
from segqueue14 import plan as sqplan  # noqa: E402
from segqueue14 import scoring as sq  # noqa: E402

# ------------------------------------------------------------------ classes


def test_fourteen_classes_with_imagecas_x_values_in_order():
    assert labels.NAMES == ["LM", "LAD", "LCx", "D1", "D2", "OM1", "OM2", "IM", "RCA",
                            "R-PDA", "R-PLA", "L-PDA", "L-PLA", "Other"]
    assert [labels.LABEL_VALUES[n] for n in labels.NAMES] == list(range(1, 15))


def test_only_lad_lcx_and_rca_are_required():
    # D13.
    assert labels.REQUIRED == ["LAD", "LCx", "RCA"]
    required = [s["name"] for s in labels.segment_dicts() if s["required"]]
    assert required == ["LAD", "LCx", "RCA"]


def test_colours_are_distinct_and_every_segment_has_a_one_line_hint():
    colours = [tuple(s["color"]) for s in labels.segment_dicts()]
    assert len(set(colours)) == 14
    for spec in labels.segment_dicts():
        assert spec["hint"] and "\n" not in spec["hint"] and len(spec["hint"]) < 80
        assert all(0.0 <= c <= 1.0 for c in spec["color"])


def test_segments_round_trip_through_the_live_segment_spec():
    specs = labels.segment_specs()
    assert [s.to_dict() for s in specs] == labels.segment_dicts()


def test_label_config_matches_the_segment_table():
    from segtrain.config import load_label_set

    labels_dir = Path(__file__).resolve().parents[1] / "configs" / "labels"
    label_set = load_label_set(labels.LABEL_SET_NAME, labels_dir=labels_dir)
    assert label_set.names == labels.NAMES
    assert label_set.labels == labels.LABEL_VALUES
    assert not label_set.source_values, "ImageCAS-X values are our values"


def test_the_instructions_are_the_project_leads_text():
    text = labels.INSTRUCTIONS
    assert text.startswith("You are given a prediction of the coronary tree in 14 classes.")
    for phrase in ("contrast-filled lumen", "(D3/D4, OM3/OM4) go in Other",
                   "A ramus intermedius is IM", "(R- or L-)", "Note anything unusual."):
        assert phrase in text


@pytest.mark.parametrize("counts, missing", [
    ({"LAD": 5, "LCx": 3, "RCA": 9}, []),
    ({"LAD": 5, "LCx": 0, "RCA": 9}, ["LCx"]),
    ({"LAD": 5}, ["LCx", "RCA"]),
    ({}, ["LAD", "LCx", "RCA"]),
    ({"LAD": "7", "LCx": None, "RCA": "x"}, ["LCx", "RCA"]),
    ({"LAD": 1, "LCx": 1, "RCA": 1, "LM": 0, "Other": 0}, []),
])
def test_missing_required(counts, missing):
    assert labels.missing_required(counts) == missing


def test_missing_required_message_names_the_classes():
    assert labels.missing_required_message([]) == ""
    one = labels.missing_required_message(["RCA"])
    assert one.startswith("RCA is empty")
    two = labels.missing_required_message(["LCx", "RCA"])
    assert two.startswith("LCx and RCA are empty")


# ----------------------------------------------------------------- protocol


def test_routes_live_under_their_own_prefix():
    assert protocol.path(protocol.NEXT) == "segqueue14/next"
    assert protocol.path(protocol.CASE_ASSET, case_id="c", kind="prelabel") == \
        "segqueue14/case/c/asset/prelabel"
    assert protocol.API_PREFIX != live_protocol.API_PREFIX
    assert protocol.PROTOCOL_HEADER != live_protocol.PROTOCOL_HEADER


def test_the_seed_is_not_an_asset_and_the_reference_is_reviewer_only():
    assert "seed" not in protocol.ASSET_KINDS
    assert protocol.ASSET_PRELABEL in protocol.ASSET_KINDS
    assert protocol.ASSET_REFERENCE not in protocol.ASSET_KINDS
    assert protocol.ASSET_REFERENCE in protocol.REVIEW_ASSET_KINDS


def test_the_current_client_is_accepted():
    protocol.check_client_protocol(PROTOCOL_VERSION)
    protocol.check_client_protocol(str(PROTOCOL_VERSION))


@pytest.mark.parametrize("sent", [None, "", 0, 1, PROTOCOL_VERSION - 1, "garbage"])
def test_an_old_or_foreign_client_is_told_to_update_the_segqueue14_module(sent):
    with pytest.raises(protocol.ProtocolError) as info:
        protocol.check_client_protocol(sent)
    assert info.value.code == protocol.ERR_CLIENT_TOO_OLD
    assert "Update the SegQueue14 module" in str(info.value)
    assert info.value.detail["minProtocol"] == PROTOCOL_VERSION


def test_the_live_client_protocol_is_refused():
    # A live SegQueue module pointed at /segqueue14 would send protocol 1.
    from segqueue import PROTOCOL_VERSION as LIVE

    with pytest.raises(protocol.ProtocolError):
        protocol.check_client_protocol(LIVE)


def test_assignment_info_carries_the_prelabel_and_round_trips():
    info = protocol.AssignmentInfo14(assignment_id="a", case_id="c", case_name="imagecas_0002",
                                     has_region=True, has_prelabel=True,
                                     prelabel_version="icx14-v1")
    data = info.to_dict()
    assert data["hasPrelabel"] is True and data["prelabelVersion"] == "icx14-v1"
    assert data["hasSeed"] is False
    assert "kind" not in data, "blind means blind"
    assert protocol.AssignmentInfo14.from_dict(data) == info
    # An older reader still understands the shape.
    assert live_protocol.AssignmentInfo.from_dict(data).case_name == "imagecas_0002"


# --------------------------------------------------------------------- plan


@pytest.mark.parametrize("name, n", [
    ("imagecas_0002", 2), ("imagecas_1000", 1000), ("imagecas_0000", None),
    ("imagecas_1001", None), ("c0001", None), ("asoca_1", None)])
def test_imagecas_ids(name, n):
    assert sqplan.imagecas_id(name) == n


@pytest.mark.parametrize("filename, case", [
    ("c0001.nii.gz", "imagecas_0002"),        # the model's own naming, id - 1
    ("c0999.nii.gz", "imagecas_1000"),
    ("imagecas_0002.nii.gz", "imagecas_0002"),
    ("imagecas_0002.prelabel.nii.gz", "imagecas_0002"),
    ("asoca_17.nii.gz", "asoca_17"),
    ("/x/y/c0000.nii", "imagecas_0001"),
])
def test_prediction_files_map_to_cases(filename, case):
    assert sqplan.case_name_for_prediction(filename) == case


def test_reference_items_map_by_metadata_first():
    assert sqplan.case_name_for_reference("2.coronary.nii.gz") == "imagecas_0002"
    assert sqplan.case_name_for_reference(
        "2.coronary.nii.gz", {"segqueue_case": "imagecas_0002"}) == "imagecas_0002"
    assert sqplan.case_name_for_reference(
        "weird.nii.gz", {"segqueue_case": "imagecas_0042"}) == "imagecas_0042"
    assert sqplan.case_name_for_reference("readme.txt") is None


def test_split_lists_parse_in_every_spelling_and_refuse_overlap():
    splits = sqplan.splits_from_lists({
        "train": "1 2 3\n4,5", "val": "imagecas_0006 c0006", "test": "8.coronary.nii.gz",
        "exclude": "9", "readme": "10"})
    assert splits == {1: "train", 2: "train", 3: "train", 4: "train", 5: "train",
                      6: "val", 7: "val", 8: "test", 9: "exclude"}
    with pytest.raises(ValueError, match="both"):
        sqplan.splits_from_lists({"train": "1 2", "test": "2"})


@pytest.mark.parametrize("filename, split", [
    ("train.txt", "train"), ("val.txt", "val"), ("test_list.txt", "test"),
    ("exclude.txt", "exclude"), ("validation.csv", "val"), ("notes.txt", None),
    ("train.nii.gz", None)])
def test_split_list_names(filename, split):
    assert sqplan.split_list_name(filename) == split


def _icx_population(n_train=560, n_val=80, n_test=160, n_unlabelled=200):
    """A stand-in for ImageCAS: ids 1..1000 with ImageCAS-X's split sizes."""
    ids = list(range(1, n_train + n_val + n_test + n_unlabelled + 1))
    splits, refs = {}, []
    for i, n in enumerate(ids):
        split = ("train" if i < n_train else "val" if i < n_train + n_val
                 else "test" if i < n_train + n_val + n_test else "exclude")
        splits[n] = split
        if split != "exclude":
            refs.append(sqplan.case_name_for_imagecas_id(n))
    names = [sqplan.case_name_for_imagecas_id(n) for n in ids]
    return names, splits, refs


def test_the_plan_orders_trainval_then_unlabelled_then_test():
    names, splits, refs = _icx_population()
    plans, problems = sqplan.plan_imagecas_cases(names, splits, refs)
    assert not problems
    tiers = [p.tier for p in plans]
    # Serve order is the plan order: a block per tier, in D14/D16's order.
    blocks = [t for i, t in enumerate(tiers) if i == 0 or tiers[i - 1] != t]
    assert blocks == [sqplan.TIER_ICX_TRAINVAL, sqplan.TIER_UNLABELLED, sqplan.TIER_ICX_TEST]
    assert tiers.count(sqplan.TIER_ICX_TRAINVAL) == 640
    assert tiers.count(sqplan.TIER_UNLABELLED) == 200
    assert tiers.count(sqplan.TIER_ICX_TEST) == 160
    priorities = [p.priority for p in plans]
    assert priorities == sorted(priorities, reverse=True)


def test_reads_are_one_per_imagecas_x_case_two_per_unlabelled_plus_ten_percent():
    names, splits, refs = _icx_population()
    plans, _ = sqplan.plan_imagecas_cases(names, splits, refs)
    by = {p.name: p for p in plans}
    unlabelled = [p for p in plans if p.tier == sqplan.TIER_UNLABELLED]
    assert all(p.replicas == 2 and not p.blind_duplicate and not p.has_reference
               for p in unlabelled)
    icx = [p for p in plans if p.has_reference]
    dups = [p for p in icx if p.blind_duplicate]
    assert all(p.replicas == (2 if p.blind_duplicate else 1) for p in icx)
    # 10 % of each split: 56 + 8 + 16.
    assert len([p for p in dups if p.split == "train"]) == 56
    assert len([p for p in dups if p.split == "val"]) == 8
    assert len([p for p in dups if p.split == "test"]) == 16
    assert by["imagecas_0001"].kind == sqplan.KIND_REFERENCE
    assert unlabelled[0].kind == sqplan.KIND_PAIRED


def test_the_duplicate_choice_is_stable_and_configurable():
    names, splits, refs = _icx_population()
    a, _ = sqplan.plan_imagecas_cases(names, splits, refs)
    b, _ = sqplan.plan_imagecas_cases(list(reversed(names)), splits, refs)
    assert {p.name for p in a if p.blind_duplicate} == {p.name for p in b if p.blind_duplicate}
    none, _ = sqplan.plan_imagecas_cases(names, splits, refs, duplicate_fraction=0.0)
    assert not any(p.blind_duplicate for p in none)
    quarter, _ = sqplan.plan_imagecas_cases(names, splits, refs, duplicate_fraction=0.25)
    assert sum(p.blind_duplicate for p in quarter) == 140 + 20 + 40
    with pytest.raises(ValueError):
        sqplan.choose_duplicates({"x": ["a"]}, fraction=1.5)


def test_priorities_are_data_and_can_be_changed():
    names, splits, refs = _icx_population(10, 2, 3, 4)
    plans, _ = sqplan.plan_imagecas_cases(
        names, splits, refs, priorities={sqplan.TIER_ICX_TEST: 999})
    assert plans[0].tier == sqplan.TIER_ICX_TEST and plans[0].priority == 999


def test_a_case_whose_place_in_the_queue_is_unknown_is_a_problem_not_a_guess():
    plans, problems = sqplan.plan_imagecas_cases(
        ["imagecas_0001", "imagecas_0002", "imagecas_0003", "scan_x"],
        {1: "test", 2: "train"}, ["imagecas_0001", "imagecas_0003"])
    assert [p.name for p in plans] == ["imagecas_0001"]
    text = "\n".join(problems)
    assert "imagecas_0002" in text and "no reference" in text
    assert "imagecas_0003" in text and "no train/val/test split" in text
    assert "scan_x" in text


def test_new_dataset_cases_want_two_reads_and_a_tag():
    plan = sqplan.plan_new_dataset_case("asoca_7", "asoca")
    assert plan.replicas == 2 and plan.dataset == "asoca"
    assert plan.tier == sqplan.TIER_NEW_DATASET
    assert sqplan.DEFAULT_PRIORITIES[sqplan.TIER_UNLABELLED] > plan.priority > \
        sqplan.DEFAULT_PRIORITIES[sqplan.TIER_ICX_TEST]
    assert plan.kind == sqplan.KIND_PAIRED
    assert sqplan.new_case_name("asoca", "Case 07.nii.gz") == "asoca_Case_07"
    assert sqplan.new_case_name("asoca", "asoca_3.nrrd") == "asoca_3"
    with pytest.raises(ValueError):
        sqplan.plan_new_dataset_case("x", "bad tag!")


# ---------------------------------------------------------- prelabel rules


def _case(version="", tier=sqplan.TIER_ICX_TRAINVAL):
    return {"prelabelFileId": "f" if version else None, "prelabelVersion": version,
            "tier": tier}


def test_prelabel_attach_skip_and_refresh():
    d = sqplan.prelabel_decision
    assert d(_case(), "v1").action == sqplan.ATTACH
    assert d(_case("v1"), "v1").action == sqplan.SKIP
    assert d(_case("v1"), "v2").action == sqplan.REFRESH


def test_no_refresh_once_anybody_has_submitted_or_is_working():
    # D15: only on cases with no submissions yet.
    d = sqplan.prelabel_decision
    assert d(_case("v1"), "v2", submissions=1).action == sqplan.SKIP
    assert d(_case("v1"), "v2", working_assignments=1).action == sqplan.SKIP


def test_no_refresh_of_the_held_out_test_cases_unless_asked():
    # D16.
    d = sqplan.prelabel_decision
    case = _case("v1", tier=sqplan.TIER_ICX_TEST)
    assert d(case, "v2").action == sqplan.SKIP
    assert "D16" in d(case, "v2").reason
    assert d(case, "v2", include_test=True).action == sqplan.REFRESH
    # A first prelabel is still attached to a test case: it is not a refresh.
    assert d(_case(tier=sqplan.TIER_ICX_TEST), "v1").action == sqplan.ATTACH


@pytest.mark.parametrize("version", ["", " ", "a/b", "..", "x" * 65, "v 1"])
def test_bad_model_versions_are_refused(version):
    with pytest.raises(ValueError):
        sqplan.validate_model_version(version)


def test_good_model_versions():
    assert sqplan.validate_model_version(" icx14-v1 ") == "icx14-v1"
    assert sqplan.validate_model_version("icx14_ft300+2026.10") == "icx14_ft300+2026.10"


# -------------------------------------------------------------------- NIfTI


def _nifti_bytes(shape=(4, 5, 6), datatype=2, bitpix=8, spacing=(0.5, 0.5, 0.6),
                 order="<"):
    header = bytearray(348)
    struct.pack_into(order + "i", header, 0, 348)
    dims = [len(shape)] + list(shape) + [1] * (7 - len(shape))
    struct.pack_into(order + "8h", header, 40, *dims)
    struct.pack_into(order + "hh", header, 70, datatype, bitpix)
    struct.pack_into(order + "8f", header, 76, 1.0, *spacing, 0, 0, 0, 0)
    struct.pack_into(order + "f", header, 108, 352.0)
    header[344:348] = b"n+1\x00"
    n = 1
    for d in shape:
        n *= d
    return bytes(header) + b"\x00" * 4 + b"\x00" * n


def test_a_nifti_header_is_read_from_a_gzipped_stream_in_small_chunks():
    raw = gzip.compress(_nifti_bytes())
    chunks = [raw[i:i + 7] for i in range(0, len(raw), 7)]
    header = nifti.header_from_chunks(iter(chunks))
    assert header.shape3 == (4, 5, 6)
    assert header.spacing3 == pytest.approx((0.5, 0.5, 0.6))
    assert header.dtype_name == "uint8"
    assert nifti.check_prelabel_header(header) is None


def test_a_large_mostly_empty_label_volume_is_not_inflated_to_read_its_header():
    raw = gzip.compress(_nifti_bytes(shape=(512, 512, 200)))
    header = nifti.header_from_chunks(iter([raw]))
    assert header.shape3 == (512, 512, 200)


def test_big_endian_and_uncompressed_headers():
    header = nifti.header_from_chunks([_nifti_bytes(order=">")])
    assert header.shape3 == (4, 5, 6) and not header.little_endian


def test_prelabel_header_problems():
    assert "uint8" in nifti.check_prelabel_header(
        nifti.parse_header(_nifti_bytes(datatype=4, bitpix=16)))
    assert "3D" in nifti.check_prelabel_header(
        nifti.parse_header(_nifti_bytes(shape=(4, 5))))
    with pytest.raises(nifti.NiftiError):
        nifti.parse_header(b"\x00" * 348)


def test_same_grid():
    a = nifti.parse_header(_nifti_bytes())
    assert nifti.same_grid(a, nifti.parse_header(_nifti_bytes())) is None
    assert "shape" in nifti.same_grid(a, nifti.parse_header(_nifti_bytes(shape=(4, 5, 7))))
    assert "spacing" in nifti.same_grid(
        a, nifti.parse_header(_nifti_bytes(spacing=(0.5, 0.5, 0.8))))


def test_a_real_nibabel_file_reads_the_same(tmp_path):
    nib = pytest.importorskip("nibabel")
    np = pytest.importorskip("numpy")
    image = nib.Nifti1Image(np.zeros((7, 8, 9), dtype=np.uint8), np.diag([0.4, 0.4, 0.5, 1]))
    path = tmp_path / "p.nii.gz"
    nib.save(image, str(path))
    header = nifti.header_from_path(str(path))
    assert header.shape3 == (7, 8, 9)
    assert header.spacing3 == pytest.approx((0.4, 0.4, 0.5))
    assert nifti.check_prelabel_header(header) is None


# ------------------------------------------------------------------ scoring


def _tree(np):
    """A small 14-class volume: a block per class, side by side."""
    vol = np.zeros((40, 20, 20), dtype=np.uint8)
    for k in range(1, 15):
        vol[2 * k:2 * k + 2, 5:12, 5:12] = k
    return vol


def test_a_perfect_read_scores_one_everywhere_and_raises_no_flag():
    np = pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    ref = _tree(np)
    result = sq.score_labels(ref.copy(), ref, (0.5, 0.5, 0.5))
    assert result["mean_dice"] == 1.0
    assert result["presence_agreement"] == 1.0
    assert result["required_min_dice"] == 1.0
    for name in labels.NAMES:
        entry = result["per_structure"][name]
        assert entry["dice"] == 1.0 and entry["present_read"] and entry["present_ref"]
    assert sq.reference_flags(result, {"mean_dice_flag": 0.6,
                                       "required_dice_flag": 0.7}) == []


def test_a_wrongly_named_vessel_is_flagged_by_class_and_presence():
    np = pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    ref = _tree(np)
    read = ref.copy()
    read[read == 3] = 6          # the LCx labelled OM1
    read[read == 12] = 0         # the L-PDA missed
    result = sq.score_labels(read, ref, (0.5, 0.5, 0.5))
    assert result["per_structure"]["LCx"]["dice"] == 0.0
    assert result["per_structure"]["L-PDA"]["present_read"] is False
    assert result["per_structure"]["L-PDA"]["presence_agrees"] is False
    assert result["presence_agreement"] == pytest.approx(12 / 14, abs=1e-4)
    assert result["required_min_dice"] == 0.0
    reasons = sq.reference_flags(result, {"mean_dice_flag": 0.6, "required_dice_flag": 0.7})
    assert any("LCx Dice 0.00" in r for r in reasons)
    assert sq.reference_flags(result, {"class_dice_flags": {"OM1": 0.9}})[0].startswith("OM1")


def test_cropping_changes_no_number():
    np = pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    from segtrain.metrics import agreement

    ref = np.zeros((60, 50, 50), dtype=np.uint8)
    ref[10:30, 10:20, 30:40] = 2
    ref[12:15, 22:30, 31:33] = 9
    read = np.roll(ref, 1, axis=0)
    full = agreement(read, ref, labels.NAMES, (0.5, 0.4, 0.4))
    cropped = sq.score_labels(read, ref, (0.5, 0.4, 0.4))
    for name in ("LAD", "RCA"):
        assert cropped["per_structure"][name]["dice"] == full["per_structure"][name]["dice"]
        assert cropped["per_structure"][name]["hd95"] == full["per_structure"][name]["hd95"]
    assert cropped["mean_dice"] == full["mean_dice"]


def test_empty_volumes_score_as_nothing_rather_than_nan():
    np = pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    empty = np.zeros((5, 5, 5), dtype=np.uint8)
    result = sq.score_labels(empty, empty, (1, 1, 1))
    assert result["mean_dice"] is None and result["required_min_dice"] is None
    assert sq.reference_flags(result, {"mean_dice_flag": 0.6}) == []


def test_voxel_counts_and_headline():
    np = pytest.importorskip("numpy")
    counts = sq.voxel_counts(_tree(np))
    assert counts["LM"] == 2 * 7 * 7 and counts["Other"] == 2 * 7 * 7
    assert set(counts) == set(labels.NAMES)
    assert sq.headline_dice({"reference": {"mean_dice": 0.8},
                             "duplicate": {"mean_dice": 0.5}}) == 0.8
    assert sq.headline_dice({"duplicate": {"mean_dice": 0.5}}) == 0.5
    assert sq.headline_dice(None) is None


def test_duplicate_and_error_flags():
    assert sq.duplicate_flags({"mean_dice": 0.4}, {"duplicate_mean_dice_flag": 0.6})
    assert not sq.duplicate_flags({"mean_dice": 0.7}, {"duplicate_mean_dice_flag": 0.6})
    assert "geometry" in sq.reference_flags({"error": "geometry_mismatch"}, {})[0]
    assert sq.reference_flags({"mean_dice": float("nan")}, {"mean_dice_flag": 0.6}) == []
