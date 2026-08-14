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
import sys
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "init_dataset", REPO / "scripts" / "init_dataset.py")
    module = importlib.util.module_from_spec(spec)
    # Registered before exec: @dataclass resolves annotations through
    # sys.modules[cls.__module__], which is None for an unregistered module.
    sys.modules[spec.name] = module
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


# -- IDC catalogue and queries -----------------------------------------------


def test_catalogue_entries_are_internally_consistent():
    for ds in init_dataset.IDC_CATALOGUE:
        assert ds.truth in ("expert", "model", "mixed"), ds.id
        assert ds.label_modality in ("SEG", "RTSTRUCT"), ds.id
        # Exactly one selection mechanism: a collection holds its own CT, an
        # analysis result only references CT held elsewhere.
        assert bool(ds.collection) != bool(ds.analysis_result), ds.id
        assert ds.cases > 0, ds.id
        assert ds.labels, ds.id


def test_catalogue_ids_are_unique():
    ids = [d.id for d in init_dataset.IDC_CATALOGUE]
    assert len(ids) == len(set(ids))
    assert set(ids) == set(init_dataset.IDC_BY_ID)


def test_expert_group_excludes_model_output_and_noncommercial():
    expert = init_dataset.idc_group("expert")
    assert expert, "the expert group should not be empty"
    assert all(d.truth == "expert" for d in expert)
    # nsclc_radiomics is CC BY-NC: a model trained on it inherits the restriction.
    assert all("NC" not in d.license for d in expert)
    assert "nsclc_radiomics" not in {d.id for d in expert}
    assert "totalsegmentator_ct_segmentations" not in {d.id for d in expert}


def test_all_group_includes_everything():
    assert len(init_dataset.idc_group("all")) == len(init_dataset.IDC_CATALOGUE)


def test_idc_group_rejects_an_unknown_name():
    with pytest.raises(KeyError):
        init_dataset.idc_group("no_such_dataset")


def test_selection_sql_for_a_collection_asks_for_images_and_labels():
    ds = init_dataset.IDC_BY_ID["lctsc"]
    sql = init_dataset.idc_selection_sql(ds)
    assert "collection_id = 'lctsc'" in sql
    assert "Modality IN ('CT', 'RTSTRUCT')" in sql
    assert "LIMIT" not in sql

    limited = init_dataset.idc_selection_sql(ds, limit_cases=5)
    assert "LIMIT 5" in limited


def test_selection_sql_for_an_analysis_result_joins_back_to_source_ct():
    ds = init_dataset.IDC_BY_ID["totalsegmentator_ct_segmentations"]
    sql = init_dataset.idc_selection_sql(ds)
    # The derived collection holds no CT of its own; it has to be reached
    # through seg_index.segmented_SeriesInstanceUID.
    assert "analysis_result_id = 'totalsegmentator_ct_segmentations'" in sql
    assert "seg_index" in sql
    assert "segmented_SeriesInstanceUID" in sql
    assert "UNION ALL" in sql


# -- S3 listing --------------------------------------------------------------


LISTING = """<?xml version="1.0" encoding="UTF-8"?>
<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
  <Name>idc-open-data</Name>
  <IsTruncated>{truncated}</IsTruncated>
  <NextContinuationToken>{token}</NextContinuationToken>
  <Contents><Key>uuid/a.dcm</Key><Size>1024</Size></Contents>
  <Contents><Key>uuid/b.dcm</Key><Size>2048</Size></Contents>
  <Contents><Key>uuid/</Key><Size>0</Size></Contents>
</ListBucketResult>"""


def test_parse_s3_listing_returns_objects_and_no_token_when_complete():
    objects, token = init_dataset.parse_s3_listing(
        LISTING.format(truncated="false", token=""))
    assert objects == [("uuid/a.dcm", 1024), ("uuid/b.dcm", 2048)]
    assert token == ""


def test_parse_s3_listing_ignores_directory_placeholders():
    objects, _ = init_dataset.parse_s3_listing(
        LISTING.format(truncated="false", token=""))
    assert all(not key.endswith("/") for key, _ in objects)


def test_parse_s3_listing_returns_the_continuation_token_when_truncated():
    _, token = init_dataset.parse_s3_listing(
        LISTING.format(truncated="true", token="abc/123+="))
    assert token == "abc/123+="


def test_parse_s3_listing_drops_a_stale_token_when_not_truncated():
    # S3 can echo a token on the final page; following it would loop forever.
    _, token = init_dataset.parse_s3_listing(
        LISTING.format(truncated="false", token="abc123"))
    assert token == ""


# -- object fetching ---------------------------------------------------------


def test_fetch_object_skips_a_file_already_at_the_right_size(tmp_path):
    target = tmp_path / "a.dcm"
    target.write_bytes(b"x" * 10)
    size, fetched = init_dataset._fetch_object("key", target, 10)
    assert (size, fetched) == (10, False)


@pytest.mark.needs_network
def test_catalogue_matches_the_live_idc_index():
    """The catalogue's numbers are claims about IDC. Check them against IDC.

    IDC ships a new version a few times a year and collections grow, so this
    guards against the catalogue quietly going stale -- not against small drift.
    """
    collections = {d.collection: d for d in init_dataset.IDC_CATALOGUE if d.collection}
    quoted = ", ".join(f"'{c}'" for c in collections)
    try:
        rows = init_dataset.idc_sql(
            f"SELECT collection_id, Modality, COUNT(DISTINCT PatientID) pts, "
            f"string_agg(DISTINCT license_short_name, '|') lic FROM index "
            f"WHERE collection_id IN ({quoted}) GROUP BY 1, 2",
            timeout=120)
    except Exception as exc:  # network, DNS, API change
        pytest.skip(f"IDC API unreachable: {exc}")

    labels, images = {}, {}
    for row in rows:
        ds = collections[row["collection_id"]]
        if row["Modality"] == ds.label_modality:
            labels[ds.id] = (row["pts"], row["lic"])
        elif row["Modality"] == "CT":
            images[ds.id] = row["lic"]

    assert set(labels) == {d.id for d in collections.values()}, "a collection disappeared"
    for ds_id, (patients, label_license) in labels.items():
        ds = init_dataset.IDC_BY_ID[ds_id]
        assert abs(patients - ds.cases) <= max(5, ds.cases * 0.1), (
            f"{ds_id}: catalogue says {ds.cases} cases, IDC says {patients}")
        assert ds.license in images[ds_id], (
            f"{ds_id}: catalogue says images are {ds.license}, IDC says {images[ds_id]}")
        assert (ds.label_license or ds.license) in label_license, (
            f"{ds_id}: catalogue says labels are {ds.label_license or ds.license}, "
            f"IDC says {label_license}")


def test_published_archive_constants_are_intact():
    """The record's own values. If Zenodo reissues the file, these must change."""
    assert init_dataset.ZIP_BYTES == 23_581_218_285
    assert init_dataset.ZIP_MD5 == "fe250e5718e0a3b5df4c4ea9d58a62fe"
    assert "10047292" in init_dataset.ZENODO_URL
    assert init_dataset.EXPECTED_CASES == 1228
