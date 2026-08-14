"""Tests for scripts/init_dataset.py.

Nothing here touches the network. What is worth testing is the part that decides
*where bytes land*: archive-root detection, the traversal guard, and the resume
logic. Those are the failure modes that are silent -- a dataset nested one level
too deep, or an extraction that "succeeded" over a truncated file.

The script is loaded by path rather than imported, because scripts/ is
deliberately not a package: the file has to run on a machine where nothing is
installed.
"""

import importlib.util
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "init_dataset", REPO / "scripts" / "init_dataset.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


init_dataset = _load_script()


def make_zip(path, members):
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return path


# -- archive layout ----------------------------------------------------------


def test_archive_root_detects_a_wrapping_directory():
    names = ["Totalsegmentator_dataset_v201/meta.csv",
             "Totalsegmentator_dataset_v201/s0000/ct.nii.gz"]
    assert init_dataset.archive_root(names) == "Totalsegmentator_dataset_v201"


def test_archive_root_empty_for_a_flat_archive():
    names = ["meta.csv", "s0000/ct.nii.gz", "s0001/ct.nii.gz"]
    assert init_dataset.archive_root(names) == ""


def test_archive_root_follows_meta_csv_not_the_directory_count():
    # A wrapped archive whose members happen to be listed with the subject
    # directories first: meta.csv still settles it.
    names = ["wrapper/s0000/ct.nii.gz", "wrapper/meta.csv"]
    assert init_dataset.archive_root(names) == "wrapper"


def test_archive_root_ignores_a_shared_prefix_that_is_not_a_directory():
    # "s0000" and "s0000x" share a prefix but not a parent directory.
    names = ["s0000/ct.nii.gz", "s0000x/ct.nii.gz"]
    assert init_dataset.archive_root(names) == ""


def test_archive_root_never_strips_a_subject_directory():
    # An archive of one case has no wrapper -- stripping s0000 would flatten the
    # case away and leave a dataset with no subjects.
    assert init_dataset.archive_root(["s0000/ct.nii.gz",
                                      "s0000/segmentations/liver.nii.gz"]) == ""


def test_extract_strips_the_wrapping_directory(tmp_path):
    src = make_zip(tmp_path / "a.zip", {
        "wrapper/meta.csv": "image_id\n",
        "wrapper/s0000/ct.nii.gz": "ct",
        "wrapper/s0000/segmentations/liver.nii.gz": "mask",
    })
    dest = tmp_path / "dataset"
    init_dataset.extract(src, dest)

    assert (dest / "meta.csv").is_file()
    assert (dest / "s0000" / "segmentations" / "liver.nii.gz").read_text() == "mask"
    assert not (dest / "wrapper").exists()


def test_extract_keeps_a_flat_archive_flat(tmp_path):
    src = make_zip(tmp_path / "a.zip", {"meta.csv": "x\n", "s0000/ct.nii.gz": "ct"})
    dest = tmp_path / "dataset"
    init_dataset.extract(src, dest)

    assert (dest / "meta.csv").is_file()
    assert (dest / "s0000" / "ct.nii.gz").is_file()


# -- resume and safety -------------------------------------------------------


def test_extract_skips_files_already_at_the_right_size(tmp_path):
    src = make_zip(tmp_path / "a.zip", {"meta.csv": "x\n", "s0000/ct.nii.gz": "ct"})
    dest = tmp_path / "dataset"

    assert init_dataset.extract(src, dest) == 2
    # Second pass is a no-op: everything is present at the expected size.
    assert init_dataset.extract(src, dest) == 0


def test_extract_redoes_a_truncated_file(tmp_path):
    src = make_zip(tmp_path / "a.zip", {"s0000/ct.nii.gz": "full contents"})
    dest = tmp_path / "dataset"
    init_dataset.extract(src, dest)

    # Simulate an interrupted write: right name, wrong length.
    target = dest / "s0000" / "ct.nii.gz"
    target.write_text("full")

    assert init_dataset.extract(src, dest) == 1
    assert target.read_text() == "full contents"


def test_extract_refuses_a_member_that_escapes_the_destination(tmp_path):
    src = tmp_path / "evil.zip"
    with zipfile.ZipFile(src, "w") as zf:
        # Two members, so archive_root() finds no common wrapper to strip.
        zf.writestr("s0000/ct.nii.gz", "ok")
        zf.writestr("../escaped.txt", "pwned")

    with pytest.raises(RuntimeError, match="escapes the destination"):
        init_dataset.extract(src, tmp_path / "dataset")

    assert not (tmp_path / "escaped.txt").exists()


# -- completeness ------------------------------------------------------------


def _fake_dataset(root, n_cases, n_masks=117):
    root.mkdir(parents=True, exist_ok=True)
    (root / "meta.csv").write_text("image_id;split\n")
    for i in range(n_cases):
        case = root / f"s{i:04d}"
        (case / "segmentations").mkdir(parents=True)
        (case / "ct.nii.gz").write_text("ct")
        for m in range(n_masks):
            (case / "segmentations" / f"structure_{m}.nii.gz").write_text("m")
    return root


def test_looks_complete_requires_meta_and_enough_cases(tmp_path):
    root = _fake_dataset(tmp_path / "ds", n_cases=3, n_masks=1)
    assert init_dataset.looks_complete(root, expect_cases=3)
    assert not init_dataset.looks_complete(root, expect_cases=4)

    (root / "meta.csv").unlink()
    assert not init_dataset.looks_complete(root, expect_cases=3)


def test_looks_complete_false_for_a_missing_root(tmp_path):
    assert not init_dataset.looks_complete(tmp_path / "nope")


def test_case_dirs_ignores_non_subject_directories(tmp_path):
    root = _fake_dataset(tmp_path / "ds", n_cases=2, n_masks=1)
    (root / "scratch").mkdir()
    (root / "s_notanumber").mkdir()
    assert [p.name for p in init_dataset.case_dirs(root)] == ["s0000", "s0001"]


def test_validate_reports_short_case_count_and_missing_masks(tmp_path):
    root = _fake_dataset(tmp_path / "ds", n_cases=2, n_masks=3)
    problems = init_dataset.validate(root, expect_cases=5, expect_structures=3)
    assert any("expected 5" in p for p in problems)

    for mask in (root / "s0000" / "segmentations").glob("*.nii.gz"):
        mask.unlink()
    problems = init_dataset.validate(root, expect_cases=2, expect_structures=3)
    assert any("s0000" in p and "0 masks" in p for p in problems)


def test_validate_clean_dataset_has_no_problems(tmp_path):
    root = _fake_dataset(tmp_path / "ds", n_cases=3, n_masks=2)
    assert init_dataset.validate(root, expect_cases=3, expect_structures=2) == []


# -- formatting --------------------------------------------------------------


@pytest.mark.parametrize(("value", "expected"), [
    (512, "512 B"),
    (2 * 1024, "2.0 KB"),
    (23_581_218_285, "22.0 GB"),
])
def test_human_readable_sizes(value, expected):
    assert init_dataset.human(value) == expected


@pytest.mark.parametrize(("value", "expected"), [
    (45, "45s"),
    (125, "2m05s"),
    (7200, "2h00m"),
])
def test_duration_formatting(value, expected):
    assert init_dataset.duration(value) == expected


def test_published_archive_constants_are_intact():
    """The record's own values. If Zenodo reissues the file, these must change."""
    assert init_dataset.ZIP_BYTES == 23_581_218_285
    assert init_dataset.ZIP_MD5 == "fe250e5718e0a3b5df4c4ea9d58a62fe"
    assert "10047292" in init_dataset.ZENODO_URL
    assert init_dataset.EXPECTED_CASES == 1228
