"""The annotator benchmark (D43, #286) without a server: its name, which ImageCAS-X
cases may be drawn, the draw, and that no training reader takes its reads.

The server side (serving, scoring, review, export) is
``test_segqueue_server14_benchmark.py``, against a real Girder and MongoDB.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
_SRC = REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.append(str(_SRC))

from segqueue14 import benchmark as b  # noqa: E402
from segqueue14 import labels  # noqa: E402

# ------------------------------------------------------------------ names


def test_the_name_is_the_imagecas_id_zero_padded():
    assert b.case_name(123) == "annotator_benchmark_0123"
    assert b.case_name(855) == "annotator_benchmark_0855"
    assert b.case_name(1000) == "annotator_benchmark_1000"
    with pytest.raises(ValueError):
        b.case_name(0)
    assert b.imagecas_id_of("annotator_benchmark_0123") == 123
    assert b.icx_case(123) == "c0122" and b.imagecas_id("c0122") == 123


@pytest.mark.parametrize("name", [
    "annotator_benchmark_0123", "annotator_benchmark_0123__r2", "annotator_benchmark_0123_rA",
    "/export/annotator_benchmark_0123", "annotator_benchmark_0123/"])
def test_a_benchmark_read_is_recognised_under_every_spelling(name):
    assert b.is_benchmark_name(name)


@pytest.mark.parametrize("name", [
    "imagecas_0123", "c0122", "ImageCAS__0123", "SetA__annotator_benchmark_0123",
    "annotator_benchmark_", "annotator_benchmark_x"])
def test_other_names_are_not_benchmarks(name):
    assert not b.is_benchmark_name(name)


# ------------------------------------------------------------- eligibility

SPLITS = {
    "train": [f"c{i:04d}" for i in range(0, 20)] + ["c0099"],
    "val": ["c0020", "c0021"],
    "test": ["c0030", "c0031", "c0099"],          # c0099 is in train and test: test wins
}
SEALED_TEST = {
    "rule": "not a list",
    "sealed_icx_test": ["c0030"],
    "open_icx_test": ["c0031"],
    "sealed_quality0": ["c0003"],
    "excluded_dev_cases_in_quality0": ["c0004"],
    "excluded_dev_cases_in_test": ["c0005"],
    "declared_dev_cases": {"Atlas": ["c0006"]},    # development cases are not held out
}


def _guard(c):
    if c in ("c0020", "c0021"):
        return f"{c}: ImageCAS-X {c} is in the ImageCAS-X val 80"
    if c == "c0007":
        return f"{c}: ImageCAS-X {c} is a Janus-M seal case (seal; JA6)"
    return None


def test_eligibility_excludes_test_sealed_excluded_guarded_and_twin_cases():
    e = b.eligibility(SPLITS, SEALED_TEST, _guard, twins=["c0008"])
    assert "test" in e.excluded["c0099"]
    for c, key in (("c0003", "sealed_quality0"), ("c0004", "excluded_dev_cases_in_quality0"),
                   ("c0005", "excluded_dev_cases_in_test")):
        assert key in e.excluded[c]
    assert "val 80" in e.excluded["c0020"] and "Janus-M seal" in e.excluded["c0007"]
    assert "twin" in e.excluded["c0008"]
    assert "c0006" in e.eligible, "a declared development case is not held out"
    for c in ("c0030", "c0031"):
        assert c not in e.eligible and c not in e.excluded, "test-only cases are no candidates"
    assert set(e.eligible) == {f"c{i:04d}" for i in range(20)} - {
        "c0003", "c0004", "c0005", "c0007", "c0008"}
    assert e.twins.startswith("1 listed")


def test_without_a_twin_list_it_says_so():
    e = b.eligibility(SPLITS, SEALED_TEST, _guard)
    assert e.twins == b.NO_TWIN_LIST and "c0008" in e.eligible


def test_the_draw_is_deterministic_and_independent_of_input_order():
    one = b.draw(b.eligibility(SPLITS, SEALED_TEST, _guard), SPLITS)
    shuffled = {k: list(reversed(v)) for k, v in SPLITS.items()}
    two = b.draw(b.eligibility(shuffled, SEALED_TEST, _guard), shuffled)
    assert one == two
    assert one.icx == min(b.eligibility(SPLITS, SEALED_TEST, _guard).eligible,
                          key=lambda c: b.rank(c))
    assert one.name == b.case_name(one.imagecas_id) and one.split == "train"
    assert one.position == 0 and str(one.eligible) in one.why
    # Another salt is another draw (and the salt is recorded on the pick).
    salted = b.draw(b.eligibility(SPLITS, SEALED_TEST, _guard, salt="other:"), SPLITS)
    assert salted.salt == "other:"


def test_an_unusable_case_is_skipped_with_its_reason_and_the_next_is_taken():
    e = b.eligibility(SPLITS, SEALED_TEST, _guard)
    first = e.eligible[0]
    skipped = []
    pick = b.draw(e, SPLITS, usable=lambda c: "no CT" if c == first else None, skipped=skipped)
    assert pick.icx == e.eligible[1] and pick.position == 1
    assert skipped == [f"{first}: no CT"]
    with pytest.raises(ValueError):
        b.draw(e, SPLITS, usable=lambda c: "no CT")


def test_the_real_draw_is_an_open_train_case_and_stable():
    """The project's own lists, through the JA12 guard (which checks every pin).

    The case on the server is stored and never redrawn, so this changing does not
    change the benchmark. It is pinned so that a change to the lists is noticed.
    """
    from janusm import guard

    g = guard.load_guard(REPO)
    splits = json.loads((REPO / "trillium-results/icx14/results/splits.json").read_text())
    sealed = json.loads((REPO / "trillium/sealed_test.json").read_text())
    e = b.eligibility(splits, sealed, lambda c: g.reason(c, source="ImageCAS-X"))
    pick = b.draw(e, splits)
    assert pick.split == "train" and pick.icx in splits["train"]
    assert g.reason(pick.icx, source="ImageCAS-X") is None
    assert g.reason(str(pick.imagecas_id), source="ImageCAS") is None
    held = {c for k, v in sealed.items() if isinstance(v, list) for c in v}
    assert pick.icx not in held and pick.icx not in splits["test"]
    assert not set(e.eligible) & (set(splits["val"]) | set(splits["test"]) | held)
    assert pick.name == "annotator_benchmark_0855", pick.why


# ------------------------------------------------------------ training readers


def test_segtrain_refuses_a_benchmark_read_by_name_whatever_allow_pool_says():
    from segtrain.proxy import benchmark_name, sealed_reason

    for name in ("annotator_benchmark_0855", "annotator_benchmark_0855__r2"):
        assert benchmark_name(name)
        for allow_pool in (False, True):
            why = sealed_reason(name, {"c0000"}, allow_pool=allow_pool)
            assert why and "annotator benchmark (D43)" in why
    assert sealed_reason("imagecas_0002", {"c0000"}) is None


def test_the_trainer_guard_refuses_a_benchmark_identifier():
    from segtrain.nnunet_ext.sealed_guard import refuse_sealed

    with pytest.raises(RuntimeError, match="sealed or unmappable"):
        refuse_sealed(["imagecas_0002", "annotator_benchmark_0855"], sealed=set(),
                      allow_pool=True)


def _mask_tree(root, case, shape=(12, 10, 8)):
    import nibabel as nib

    folder = root / case
    (folder / "segmentations").mkdir(parents=True)
    affine = np.diag([0.5, 0.5, 0.5, 1.0])
    nib.save(nib.Nifti1Image(np.full(shape, 300, np.int16), affine), str(folder / "ct.nii.gz"))
    for k, name in enumerate(labels.NAMES, start=1):
        mask = np.zeros(shape, np.uint8)
        mask[k:k + 2, 2:5, 2:5] = 1
        nib.save(nib.Nifti1Image(mask, affine), str(folder / "segmentations" / f"{name}.nii.gz"))


def test_convert_skips_benchmark_reads_and_says_how_many(tmp_path):
    pytest.importorskip("nibabel")
    from segtrain.config import Config, TaskConfig, load_label_set
    from segtrain.convert import convert_dataset
    from segtrain.index import build_rows, scan, write_meta
    from segtrain.splits import read_meta

    root = tmp_path / "export"
    for case in ("imagecas_0002", "annotator_benchmark_0855", "annotator_benchmark_0855__r2"):
        _mask_tree(root, case)
    rows = build_rows(scan(root), val_fraction=0.0, test_fraction=0.0, seed=1)
    write_meta(root / "meta.csv", rows)
    cfg = Config(zenodo_root=root, nnunet_raw=tmp_path / "raw",
                 nnunet_preprocessed=tmp_path / "pre", nnunet_results=tmp_path / "res",
                 runs_root=tmp_path / "runs", link_mode="copy", convert_workers=1)
    task = TaskConfig(dataset_id=799, dataset_name="BenchmarkSkip",
                      label_set=load_label_set(labels.LABEL_SET_NAME,
                                               labels_dir=REPO / "configs" / "labels"),
                      spacing=None, configuration="3d_fullres")
    report = convert_dataset(cfg, task, read_meta(root / "meta.csv"))
    assert report.ok, report.render()
    assert report.n_train == 1 and report.n_benchmark == 2
    assert "2 annotator benchmark read(s) skipped (D43)" in report.render()
    written = sorted(p.name for p in (task.raw_dir(cfg) / "labelsTr").iterdir())
    assert written == ["imagecas_0002.nii.gz"]
