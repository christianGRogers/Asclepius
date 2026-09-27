"""The flat layout, which is the one the real data arrives in.

ImageCAS ships two files per case in a single directory rather than a directory
per case. Everything downstream of ``segtrain index`` is indifferent to that --
it reads meta.csv -- so the whole difference lives in the scanner, and so does
the whole risk: a pairing bug here does not crash, it silently indexes an image
against the wrong case's label.
"""

from pathlib import Path

import pytest

from segtrain.index import IndexError_, looks_flat, scan, scan_flat


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")
    return path


def _imagecas(root: Path, ids=("1", "2", "10")) -> Path:
    """The real thing: ``<id>.img.nii.gz`` beside ``<id>.label.nii.gz``."""
    for case_id in ids:
        _touch(root / f"{case_id}.img.nii.gz")
        _touch(root / f"{case_id}.label.nii.gz")
    return root


def test_imagecas_pairs_are_found(tmp_path):
    cases = scan_flat(_imagecas(tmp_path))

    assert [c.case_id for c in cases] == ["1", "10", "2"]  # sorted as strings
    for case in cases:
        assert case.image.name == f"{case.case_id}.img.nii.gz"
        assert case.multilabel is not None
        assert case.multilabel.name == f"{case.case_id}.label.nii.gz"
        assert case.label_form == "multilabel"


def test_every_image_is_paired_with_its_own_label(tmp_path):
    """The failure that does not announce itself.

    Pairing by sorted position rather than by name puts case 10's label on case
    2's image on any dataset whose ids are not zero-padded -- which ImageCAS's
    are not. Nothing raises; the model just trains on mislabelled data.
    """
    cases = scan_flat(_imagecas(tmp_path, ids=[str(n) for n in range(1, 21)]))

    for case in cases:
        stem = case.multilabel.name[: -len(".label.nii.gz")]
        assert stem == case.case_id


@pytest.mark.parametrize(
    "image_name, label_name",
    [
        ("7.img.nii.gz", "7.label.nii.gz"),
        ("7.nii.gz", "7.label.nii.gz"),          # no marker on the image half
        ("7_img.nii.gz", "7_label.nii.gz"),
        ("7.image.nii.gz", "7.segmentation.nii.gz"),
        ("7.ccta.nii.gz", "7.seg.nii.gz"),
        ("7.ct.nii.gz", "7_gt.nii.gz"),
    ],
)
def test_marker_spellings(tmp_path, image_name, label_name):
    _touch(tmp_path / image_name)
    _touch(tmp_path / label_name)

    cases = scan_flat(tmp_path)

    assert len(cases) == 1
    assert cases[0].case_id == "7"
    assert cases[0].image.name == image_name
    assert cases[0].multilabel.name == label_name


def test_segmentation_is_not_read_as_seg(tmp_path):
    """``.segmentation`` ends with neither ``.seg`` nor a case id of its own.

    Checked longest-marker-first. Shortest-first would strip ``.seg`` and leave
    a case called ``7.mentation``.
    """
    _touch(tmp_path / "7.img.nii.gz")
    _touch(tmp_path / "7.segmentation.nii.gz")

    cases = scan_flat(tmp_path)

    assert [c.case_id for c in cases] == ["7"]


def test_an_image_with_no_label_still_indexes(tmp_path):
    """A partially delivered dataset should be reported, not quietly shortened."""
    _touch(tmp_path / "1.img.nii.gz")
    _touch(tmp_path / "1.label.nii.gz")
    _touch(tmp_path / "2.img.nii.gz")

    cases = scan_flat(tmp_path)

    assert [c.case_id for c in cases] == ["1", "2"]
    assert cases[1].has_labels is False


def test_a_label_with_no_image_is_not_a_case(tmp_path):
    _touch(tmp_path / "1.img.nii.gz")
    _touch(tmp_path / "1.label.nii.gz")
    _touch(tmp_path / "99.label.nii.gz")

    assert [c.case_id for c in scan_flat(tmp_path)] == ["1"]


# ------------------------------------------------------------------ detection


def test_auto_detects_flat(tmp_path):
    assert looks_flat(_imagecas(tmp_path)) is True
    assert [c.case_id for c in scan(tmp_path)] == ["1", "10", "2"]


def test_auto_detects_nested(tmp_path):
    _touch(tmp_path / "s0001" / "ct.nii.gz")
    _touch(tmp_path / "s0001" / "labels.nii.gz")

    assert looks_flat(tmp_path) is False
    assert [c.case_id for c in scan(tmp_path)] == ["s0001"]


def test_case_directories_win_over_stray_files(tmp_path):
    """A stray export beside real case directories must not flip the layout."""
    _touch(tmp_path / "s0001" / "ct.nii.gz")
    _touch(tmp_path / "s0001" / "labels.nii.gz")
    _touch(tmp_path / "scratch.nii.gz")

    assert looks_flat(tmp_path) is False
    assert [c.case_id for c in scan(tmp_path)] == ["s0001"]


def test_layout_can_be_forced(tmp_path):
    _imagecas(tmp_path)
    assert scan(tmp_path, layout="nested") == []
    assert len(scan(tmp_path, layout="flat")) == 3


def test_unknown_layout_is_refused(tmp_path):
    with pytest.raises(IndexError_, match="unknown layout"):
        scan(tmp_path, layout="sideways")
