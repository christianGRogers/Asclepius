"""Indexing a bring-your-own dataset, and converting its two label forms."""

from __future__ import annotations

import nibabel as nib
import numpy as np
import pytest

from segtrain import index
from segtrain.config import LabelSet
from segtrain.convert import convert_case, remap_multilabel
from segtrain.splits import SPLIT_TEST, SPLIT_TRAIN, SPLIT_VAL, read_meta

CORONARY = LabelSet(
    "coronary",
    {"left_main": 1, "left_anterior_descending": 2,
     "left_circumflex": 3, "right_coronary_artery": 4},
)


def _volume(path, array, affine=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    img = nib.Nifti1Image(np.asarray(array), affine if affine is not None else np.eye(4))
    img.set_data_dtype(array.dtype)
    nib.save(img, str(path))


def _case(root, case_id, form="per-structure", image_name="ct.nii.gz"):
    """One case on disk, in whichever label form."""
    case_dir = root / case_id
    _volume(case_dir / image_name, np.zeros((8, 8, 8), dtype=np.int16))

    if form == "per-structure":
        for i, name in enumerate(CORONARY.names, start=1):
            mask = np.zeros((8, 8, 8), dtype=np.uint8)
            mask[i, 0, 0] = 1
            _volume(case_dir / "segmentations" / f"{name}.nii.gz", mask)
    elif form == "multilabel":
        labels = np.zeros((8, 8, 8), dtype=np.uint8)
        for i in range(1, 5):
            labels[i, 0, 0] = i
        _volume(case_dir / "labels.nii.gz", labels)
    return case_dir


# ------------------------------------------------------------------ scanning


def test_scan_finds_both_label_forms(tmp_path):
    _case(tmp_path, "c001", "per-structure")
    _case(tmp_path, "c002", "multilabel")

    cases = {c.case_id: c for c in index.scan(tmp_path)}
    assert cases["c001"].label_form == "per-structure"
    assert cases["c002"].label_form == "multilabel"


def test_segmentations_dir_wins_over_a_multilabel_file(tmp_path):
    """Per-structure masks carry provenance a merged volume has already lost."""
    case_dir = _case(tmp_path, "c001", "per-structure")
    _volume(case_dir / "labels.nii.gz", np.zeros((8, 8, 8), dtype=np.uint8))

    (only,) = index.scan(tmp_path)
    assert only.label_form == "per-structure"


@pytest.mark.parametrize("image_name", ["ct.nii.gz", "image.nii.gz", "ccta.nii.gz"])
def test_several_image_names_are_accepted(tmp_path, image_name):
    _case(tmp_path, "c001", image_name=image_name)
    assert len(index.scan(tmp_path)) == 1


def test_case_named_image_is_found(tmp_path):
    """`<case>/<case>.nii.gz` is how a lot of exports come out."""
    _volume(tmp_path / "c001" / "c001.nii.gz", np.zeros((4, 4, 4), dtype=np.int16))
    (only,) = index.scan(tmp_path)
    assert only.case_id == "c001"


def test_directories_without_an_image_are_skipped(tmp_path):
    _case(tmp_path, "c001")
    (tmp_path / "notes").mkdir()
    assert [c.case_id for c in index.scan(tmp_path)] == ["c001"]


def test_a_case_with_no_labels_is_reported_not_hidden(tmp_path):
    _volume(tmp_path / "c001" / "ct.nii.gz", np.zeros((4, 4, 4), dtype=np.int16))
    cases = index.scan(tmp_path)
    assert not cases[0].has_labels
    assert "no labels" in index.summarize(cases, index.build_rows(cases))


# ------------------------------------------------------------ split assignment


def test_split_assignment_is_stable_as_the_dataset_grows(tmp_path):
    """The property the whole hashing approach exists for.

    Shuffle-and-slice would reassign every case each time a new one arrives,
    quietly moving yesterday's test cases into today's training set. Nothing
    would crash; the model would just score better than it should.
    """
    first = [index.assign_split(f"case{i:04d}", 0.15, 0.15) for i in range(50)]
    later = [index.assign_split(f"case{i:04d}", 0.15, 0.15) for i in range(200)]
    assert later[:50] == first


def test_split_assignment_does_not_depend_on_the_process(tmp_path):
    """Python salts str.__hash__ per process; this must not."""
    assert index.assign_split("c001", 0.2, 0.2, seed=7) == \
        index.assign_split("c001", 0.2, 0.2, seed=7)


def test_split_proportions_are_roughly_as_asked():
    splits = [index.assign_split(f"c{i:05d}", 0.20, 0.10) for i in range(4000)]
    assert 0.17 < splits.count(SPLIT_VAL) / len(splits) < 0.23
    assert 0.07 < splits.count(SPLIT_TEST) / len(splits) < 0.13


def test_seed_changes_the_assignment():
    a = [index.assign_split(f"c{i}", 0.2, 0.2, seed=1) for i in range(100)]
    b = [index.assign_split(f"c{i}", 0.2, 0.2, seed=2) for i in range(100)]
    assert a != b


def test_fractions_that_leave_no_training_data_are_refused(tmp_path):
    _case(tmp_path, "c001")
    cases = index.scan(tmp_path)
    with pytest.raises(index.IndexError_, match="nothing to train on"):
        index.build_rows(cases, val_fraction=0.6, test_fraction=0.5)


def test_overrides_pin_specific_cases(tmp_path):
    for i in range(6):
        _case(tmp_path, f"c{i:03d}")
    cases = index.scan(tmp_path)

    rows = index.build_rows(cases, overrides={"c000": SPLIT_TEST, "c001": SPLIT_TEST})
    placed = {r.case_id: r.split for r in rows}
    assert placed["c000"] == SPLIT_TEST
    assert placed["c001"] == SPLIT_TEST


def test_override_file_accepts_comma_or_semicolon(tmp_path):
    (tmp_path / "a.csv").write_text("case_id,split\nc001,test\nc002,val\n", encoding="utf-8")
    (tmp_path / "b.csv").write_text("c001;test\nc002;val\n", encoding="utf-8")
    expected = {"c001": SPLIT_TEST, "c002": SPLIT_VAL}
    assert index.read_overrides(tmp_path / "a.csv") == expected
    assert index.read_overrides(tmp_path / "b.csv") == expected


def test_override_file_with_no_usable_rows_is_an_error(tmp_path):
    (tmp_path / "bad.csv").write_text("c001,trian\n", encoding="utf-8")
    with pytest.raises(index.IndexError_, match="no usable rows"):
        index.read_overrides(tmp_path / "bad.csv")


# ---------------------------------------------------------------- meta.csv


def test_written_index_round_trips_through_read_meta(tmp_path):
    """One index format in the codebase, not one per data source."""
    for i in range(20):
        _case(tmp_path, f"c{i:03d}")
    cases = index.scan(tmp_path)
    rows = index.build_rows(cases, study_type="ccta")

    path = index.write_meta(tmp_path / "meta.csv", rows)
    reloaded = read_meta(path)

    assert [r.case_id for r in reloaded] == [r.case_id for r in rows]
    assert [r.split for r in reloaded] == [r.split for r in rows]
    assert {r.study_type for r in reloaded} == {"ccta"}


def test_every_case_lands_in_exactly_one_split(tmp_path):
    for i in range(40):
        _case(tmp_path, f"c{i:03d}")
    rows = index.build_rows(index.scan(tmp_path))
    assert {r.split for r in rows} <= {SPLIT_TRAIN, SPLIT_VAL, SPLIT_TEST}
    assert len({r.case_id for r in rows}) == 40


# ------------------------------------------------------- multilabel conversion


def _reference(shape=(8, 8, 8)):
    return nib.Nifti1Image(np.zeros(shape, dtype=np.int16), np.eye(4))


def test_multilabel_passes_through_when_indices_already_match(tmp_path):
    source = np.zeros((8, 8, 8), dtype=np.uint8)
    source[0, 0, 0] = 1
    source[1, 0, 0] = 4
    _volume(tmp_path / "labels.nii.gz", source)

    labels, missing, problems = remap_multilabel(
        tmp_path / "labels.nii.gz", CORONARY, _reference())

    assert problems == []
    assert labels[0, 0, 0] == 1
    assert labels[1, 0, 0] == 4
    assert set(missing) == {"left_anterior_descending", "left_circumflex"}


def test_multilabel_is_remapped_through_source_values(tmp_path):
    """The case that makes hand-labelled data usable at all.

    An exported segmentation numbers its segments in the order they were drawn.
    Reading those positionally would mislabel every vessel while looking
    entirely successful.
    """
    label_set = LabelSet(
        "c",
        {"left_main": 1, "right_coronary_artery": 2},
        source_values={"left_main": 7, "right_coronary_artery": 3},
    )
    source = np.zeros((8, 8, 8), dtype=np.uint8)
    source[0, 0, 0] = 7   # their left_main
    source[1, 0, 0] = 3   # their RCA
    _volume(tmp_path / "labels.nii.gz", source)

    labels, missing, problems = remap_multilabel(
        tmp_path / "labels.nii.gz", label_set, _reference())

    assert problems == []
    assert labels[0, 0, 0] == 1
    assert labels[1, 0, 0] == 2
    assert missing == []


def test_unmapped_values_are_dropped_and_reported(tmp_path):
    """Silently zeroing them would look exactly like a model that never learned."""
    source = np.zeros((8, 8, 8), dtype=np.uint8)
    source[0, 0, 0] = 1
    source[1, 0, 0] = 9
    _volume(tmp_path / "labels.nii.gz", source)

    labels, _, problems = remap_multilabel(
        tmp_path / "labels.nii.gz", CORONARY, _reference())

    assert labels[1, 0, 0] == 0
    assert len(problems) == 1
    assert "9" in problems[0] and "source_values" in problems[0]


def test_multilabel_geometry_disagreement_is_refused(tmp_path):
    source = np.zeros((8, 8, 8), dtype=np.uint8)
    source[0, 0, 0] = 1
    shifted = np.eye(4)
    shifted[0, 3] = 25.0
    _volume(tmp_path / "labels.nii.gz", source, affine=shifted)

    labels, _, problems = remap_multilabel(
        tmp_path / "labels.nii.gz", CORONARY, _reference())

    assert labels.max() == 0
    assert "geometry" in problems[0]


def test_multilabel_shape_disagreement_is_refused(tmp_path):
    _volume(tmp_path / "labels.nii.gz", np.ones((4, 4, 4), dtype=np.uint8))
    labels, _, problems = remap_multilabel(
        tmp_path / "labels.nii.gz", CORONARY, _reference())
    assert labels.max() == 0
    assert "shape" in problems[0]


# -------------------------------------------------------------- convert_case


@pytest.mark.parametrize("form", ["per-structure", "multilabel"])
def test_convert_case_handles_either_form(tmp_path, form):
    root = tmp_path / "data"
    _case(root, "c001", form)
    images, labels = tmp_path / "img", tmp_path / "lbl"
    images.mkdir()
    labels.mkdir()

    result = convert_case("c001", root, images, labels, CORONARY, "copy", False)

    assert result.ok, result.error
    assert (images / "c001_0000.nii.gz").is_file()
    written = np.asanyarray(nib.load(str(labels / "c001.nii.gz")).dataobj)
    assert set(np.unique(written)) == {0, 1, 2, 3, 4}


def test_convert_case_reports_a_case_with_no_labels(tmp_path):
    root = tmp_path / "data"
    _volume(root / "c001" / "ct.nii.gz", np.zeros((4, 4, 4), dtype=np.int16))
    images, labels = tmp_path / "img", tmp_path / "lbl"
    images.mkdir()
    labels.mkdir()

    result = convert_case("c001", root, images, labels, CORONARY, "copy", False)
    assert not result.ok
    assert "no labels" in result.error


def test_convert_case_reports_a_missing_image(tmp_path):
    root = tmp_path / "data"
    (root / "c001").mkdir(parents=True)
    images, labels = tmp_path / "img", tmp_path / "lbl"
    images.mkdir()
    labels.mkdir()

    result = convert_case("c001", root, images, labels, CORONARY, "copy", False)
    assert not result.ok
    assert "no image" in result.error


def test_convert_case_skips_work_already_done(tmp_path):
    root = tmp_path / "data"
    _case(root, "c001")
    images, labels = tmp_path / "img", tmp_path / "lbl"
    images.mkdir()
    labels.mkdir()

    assert convert_case("c001", root, images, labels, CORONARY, "copy", False).ok
    again = convert_case("c001", root, images, labels, CORONARY, "copy", False)
    assert again.skipped


def test_lumpy_small_split_is_explained_not_hidden(tmp_path):
    """Hashing hits the requested ratio only in expectation.

    On a few dozen cases the realised split can look badly off, and the natural
    reaction -- re-roll the seed until it looks right -- is choosing a test set by
    peeking at it. So say it out loud instead.
    """
    for i in range(12):
        _case(tmp_path, f"c{i:03d}")
    cases = index.scan(tmp_path)
    rows = index.build_rows(cases, val_fraction=0.15, test_fraction=0.15)
    text = index.summarize(cases, rows, 0.15, 0.15)

    counts = {s: sum(1 for r in rows if r.split == s) for s in
              (SPLIT_TRAIN, SPLIT_VAL, SPLIT_TEST)}
    lumpy = abs(counts[SPLIT_VAL] - 1.8) > 1.4 or abs(counts[SPLIT_TEST] - 1.8) > 1.4
    if lumpy:
        assert "only in expectation" in text
        assert "--overrides" in text


def test_no_lumpiness_note_on_a_larger_dataset(tmp_path):
    """The note is scoped to small datasets; it must not nag at scale."""
    cases = [index.ScannedCase(f"c{i:03d}", tmp_path / f"c{i:03d}" / "ct.nii.gz",
                               seg_dir=tmp_path / f"c{i:03d}" / "segmentations")
             for i in range(200)]
    rows = index.build_rows(cases, val_fraction=0.15, test_fraction=0.15)
    assert "only in expectation" not in index.summarize(cases, rows, 0.15, 0.15)
