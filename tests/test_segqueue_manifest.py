"""What the manifest has to catch, tested against what actually goes wrong.

Every failure mode here is one a transfer really produces: a case that never
arrived, a volume cut off mid-write, a byte that flipped, a tree that looks
complete because the file count is right. None of them raise on their own, which
is the whole reason this module exists, so the tests assert on the *report*
rather than on an exception.
"""

import json

import pytest

from segqueue.manifest import (
    FULL,
    MANIFEST_NAME,
    QUICK,
    Manifest,
    ManifestError,
    build,
    diff,
    needed,
    verify,
)


def _case(root, name, ct=b"ct-bytes", masks=(("left_main", b"lm"),)):
    """One case in the layout `segtrain convert` reads."""
    directory = root / name
    (directory / "segmentations").mkdir(parents=True, exist_ok=True)
    (directory / "ct.nii.gz").write_bytes(ct)
    for structure, payload in masks:
        (directory / "segmentations" / f"{structure}.nii.gz").write_bytes(payload)
    return directory


def _tree(root, names=("1", "2", "10")):
    for name in names:
        _case(root, name)
    return root


# -- building -------------------------------------------------------------


def test_build_groups_files_under_their_case(tmp_path):
    manifest = build(_tree(tmp_path))

    assert [c.case for c in manifest.cases] == ["1", "10", "2"]  # sorted as strings
    assert manifest.totals == {"cases": 3, "files": 6, "bytes": 3 * (8 + 2)}
    paths = [entry.path for entry in manifest.files()]
    assert "1/ct.nii.gz" in paths
    assert "1/segmentations/left_main.nii.gz" in paths


def test_paths_are_posix_even_on_windows(tmp_path):
    manifest = build(_tree(tmp_path, ("1",)))

    for entry in manifest.files():
        assert "\\" not in entry.path, "a manifest crosses Windows, Linux and a cluster"


def test_build_is_deterministic(tmp_path):
    """Two manifests of one tree must be byte-identical, so they can be diffed."""
    first = build(_tree(tmp_path), now="2026-01-01T00:00:00+00:00")
    second = build(tmp_path, now="2026-01-01T00:00:00+00:00")

    assert first.to_json() == second.to_json()


def test_files_at_the_root_are_not_adopted_into_a_case(tmp_path):
    _tree(tmp_path, ("1",))
    (tmp_path / "NOTES.txt").write_bytes(b"not training data")

    manifest = build(tmp_path)

    assert [entry.path for entry in manifest.files()] == [
        "1/ct.nii.gz", "1/segmentations/left_main.nii.gz"]


def test_build_can_be_restricted_to_named_cases(tmp_path):
    _tree(tmp_path, ("1", "2"))

    manifest = build(tmp_path, cases=["2"])

    assert [c.case for c in manifest.cases] == ["2"]


def test_build_on_a_missing_case_says_which(tmp_path):
    _tree(tmp_path, ("1",))

    with pytest.raises(ManifestError, match="no such case directory"):
        build(tmp_path, cases=["1", "nope"])


# -- round trip -----------------------------------------------------------


def test_write_read_round_trip(tmp_path):
    original = build(_tree(tmp_path), source={"kind": "segqueue-export"})
    original.write(tmp_path)

    loaded = Manifest.read(tmp_path)

    assert loaded.to_json() == original.to_json()
    assert loaded.source == {"kind": "segqueue-export"}


def test_a_tree_with_no_manifest_says_so_rather_than_guessing(tmp_path):
    with pytest.raises(ManifestError, match="no manifest.json"):
        Manifest.read(tmp_path)


def test_a_manifest_from_the_future_refuses_to_be_read_partially(tmp_path):
    (tmp_path / MANIFEST_NAME).write_text(
        json.dumps({"manifest_version": 99, "cases": []}), encoding="utf-8")

    with pytest.raises(ManifestError, match="newer than this code understands"):
        Manifest.read(tmp_path)


def test_an_interrupted_write_leaves_the_previous_manifest_intact(tmp_path):
    build(_tree(tmp_path, ("1",))).write(tmp_path)
    before = (tmp_path / MANIFEST_NAME).read_text(encoding="utf-8")

    # The partial file is what a killed write leaves behind; it must not be read.
    (tmp_path / (MANIFEST_NAME + ".partial")).write_text("{tru", encoding="utf-8")

    assert (tmp_path / MANIFEST_NAME).read_text(encoding="utf-8") == before
    assert Manifest.read(tmp_path).totals["cases"] == 1


def test_unparseable_json_is_an_error_not_an_empty_manifest(tmp_path):
    (tmp_path / MANIFEST_NAME).write_text("{not json", encoding="utf-8")

    with pytest.raises(ManifestError, match="not valid JSON"):
        Manifest.read(tmp_path)


# -- verifying ------------------------------------------------------------


def test_a_clean_tree_verifies(tmp_path):
    manifest = build(_tree(tmp_path))

    result = verify(tmp_path, manifest)

    assert result.is_clean
    assert len(result.ok) == 6
    assert result.broken_cases == []


def test_a_missing_case_is_reported_as_a_broken_case(tmp_path):
    manifest = build(_tree(tmp_path))
    for path in (tmp_path / "2").rglob("*"):
        if path.is_file():
            path.unlink()

    result = verify(tmp_path, manifest)

    assert not result.is_clean
    assert sorted(result.missing) == ["2/ct.nii.gz", "2/segmentations/left_main.nii.gz"]
    assert result.broken_cases == ["2"], "the unit that is unusable is the case"


def test_a_truncated_file_is_caught_by_size_alone(tmp_path):
    """An interrupted transfer produces a short file, and QUICK must catch it."""
    manifest = build(_tree(tmp_path))
    (tmp_path / "1" / "ct.nii.gz").write_bytes(b"ct-by")  # 5 of 8 bytes

    result = verify(tmp_path, manifest, mode=QUICK)

    assert result.truncated == [("1/ct.nii.gz", 8, 5)]
    assert result.broken_cases == ["1"]


def test_a_flipped_byte_needs_the_digest_and_is_missed_by_size(tmp_path):
    manifest = build(_tree(tmp_path))
    (tmp_path / "1" / "ct.nii.gz").write_bytes(b"CT-BYTES")  # same length

    assert verify(tmp_path, manifest, mode=QUICK).is_clean, "size cannot see this"

    full = verify(tmp_path, manifest, mode=FULL)
    assert full.corrupt == ["1/ct.nii.gz"]
    assert not full.is_clean


def test_extra_files_are_reported_but_do_not_fail_the_check(tmp_path):
    manifest = build(_tree(tmp_path, ("1",)))
    (tmp_path / "leftover.nii.gz").write_bytes(b"from a previous export")

    result = verify(tmp_path, manifest)

    assert result.extra == ["leftover.nii.gz"]
    assert result.is_clean, "nobody asked about this file; it is not a reason to stop"


def test_the_manifest_itself_is_not_an_extra_file(tmp_path):
    manifest = build(_tree(tmp_path, ("1",)))
    manifest.write(tmp_path)
    (tmp_path / "transfer-receipt.json").write_text("{}", encoding="utf-8")

    assert verify(tmp_path, manifest).extra == []


def test_verify_reports_everything_rather_than_stopping_at_the_first_fault(tmp_path):
    """"Which cases did not arrive" is the answer needed, not "at least one"."""
    manifest = build(_tree(tmp_path))
    (tmp_path / "1" / "ct.nii.gz").unlink()
    (tmp_path / "2" / "ct.nii.gz").write_bytes(b"short")
    (tmp_path / "10" / "ct.nii.gz").write_bytes(b"CT-BYTES")

    result = verify(tmp_path, manifest, mode=FULL)

    assert result.missing == ["1/ct.nii.gz"]
    assert [p for p, _, _ in result.truncated] == ["2/ct.nii.gz"]
    assert result.corrupt == ["10/ct.nii.gz"]
    assert result.broken_cases == ["1", "10", "2"]


def test_quick_mode_says_it_only_checked_sizes(tmp_path):
    manifest = build(_tree(tmp_path, ("1",)))

    assert "sizes only" in verify(tmp_path, manifest, mode=QUICK).summary()
    assert "sizes only" not in verify(tmp_path, manifest, mode=FULL).summary()


def test_an_unknown_mode_is_rejected(tmp_path):
    manifest = build(_tree(tmp_path, ("1",)))

    with pytest.raises(ValueError, match="mode must be"):
        verify(tmp_path, manifest, mode="sort-of")


# -- planning a transfer --------------------------------------------------


def test_needed_is_empty_for_a_complete_tree(tmp_path):
    manifest = build(_tree(tmp_path))

    assert needed(tmp_path, manifest) == []


def test_needed_lists_exactly_the_paths_to_re_fetch(tmp_path):
    manifest = build(_tree(tmp_path))
    (tmp_path / "1" / "ct.nii.gz").unlink()
    (tmp_path / "2" / "segmentations" / "left_main.nii.gz").write_bytes(b"")

    assert needed(tmp_path, manifest) == [
        "1/ct.nii.gz", "2/segmentations/left_main.nii.gz"]


def test_needed_on_an_empty_destination_asks_for_everything(tmp_path):
    manifest = build(_tree(tmp_path))
    destination = tmp_path.parent / "elsewhere"
    destination.mkdir()

    assert len(needed(destination, manifest)) == 6


def test_needed_and_verify_agree_by_construction(tmp_path):
    """Planning and checking must be the same rule, or they disagree eventually."""
    manifest = build(_tree(tmp_path))
    (tmp_path / "1" / "ct.nii.gz").write_bytes(b"short")

    assert needed(tmp_path, manifest, mode=FULL) == verify(tmp_path, manifest, FULL).bad


# -- comparing the two ends ----------------------------------------------


def test_diff_finds_a_case_the_receiver_never_heard_about(tmp_path):
    sender = build(_tree(tmp_path, ("1", "2")))
    receiver = build(_tree(tmp_path.parent / "rx", ("1",)))

    report = diff(sender, receiver)

    assert report["only_in_left"] == ["2/ct.nii.gz", "2/segmentations/left_main.nii.gz"]
    assert report["only_in_right"] == []
    assert report["changed"] == []


def test_diff_finds_the_same_path_with_different_contents(tmp_path):
    sender = build(_tree(tmp_path, ("1",)))
    other = _tree(tmp_path.parent / "rx", ())
    _case(other, "1", ct=b"different")
    receiver = build(other)

    assert diff(sender, receiver)["changed"] == ["1/ct.nii.gz"]
