"""`index` and `convert` against both layouts, end to end.

This is the seam where phase 1 was broken. `index` learned the flat form ImageCAS
ships -- `<id>.img.nii.gz` beside `<id>.label.nii.gz` in one directory -- and
`convert` did not: it rebuilt each path as `root / case_id` and called the nested
helpers, so on the layout the real data arrives in, `index` reported 1000 cases
found and `convert` failed all 1000. Nothing in either module's own tests noticed,
because each was right about its own half.

So these tests run the two together. A unit test of either one passes while the
pipeline does not work.
"""

import nibabel as nib
import numpy as np
import pytest

from segtrain.config import Config, LabelSet, TaskConfig
from segtrain.convert import convert_dataset, iter_case_ids
from segtrain.index import build_rows, scan, write_meta
from segtrain.splits import read_meta

LUMEN = LabelSet("coronary_lumen", {"coronary_lumen": 1})


def _volume(path, array, affine=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    image = nib.Nifti1Image(array, affine if affine is not None else np.eye(4))
    nib.save(image, str(path))
    return path


def _flat(root, ids=("1", "2", "10")):
    """ImageCAS: two files per case, one directory, ids not zero-padded."""
    root.mkdir(parents=True, exist_ok=True)
    for case_id in ids:
        _volume(root / f"{case_id}.img.nii.gz",
                np.full((6, 6, 6), 100, dtype=np.int16))
        mask = np.zeros((6, 6, 6), dtype=np.uint8)
        mask[2:4, 2:4, 2:4] = 1
        _volume(root / f"{case_id}.label.nii.gz", mask)
    return root


def _nested(root, ids=("c001", "c002")):
    """The annotation export: a directory per case."""
    for case_id in ids:
        _volume(root / case_id / "ct.nii.gz", np.full((6, 6, 6), 100, dtype=np.int16))
        mask = np.zeros((6, 6, 6), dtype=np.uint8)
        mask[2:4, 2:4, 2:4] = 1
        _volume(root / case_id / "segmentations" / "coronary_lumen.nii.gz", mask)
    return root


def _config(tmp_path, root):
    return Config(
        zenodo_root=root,
        nnunet_raw=tmp_path / "raw",
        nnunet_preprocessed=tmp_path / "pre",
        nnunet_results=tmp_path / "res",
        runs_root=tmp_path / "runs",
        link_mode="copy",
        convert_workers=1,
    )


def _task():
    return TaskConfig(
        dataset_id=710,
        dataset_name="CoronaryLumen",
        label_set=LUMEN,
        spacing=None,
        configuration="3d_fullres",
    )


def _index_then_convert(tmp_path, root, layout="auto"):
    cases = scan(root, layout=layout)
    rows = build_rows(cases, val_fraction=0.0, test_fraction=0.0, seed=1)
    write_meta(root / "meta.csv", rows)

    cfg, task = _config(tmp_path, root), _task()
    report = convert_dataset(cfg, task, read_meta(root / "meta.csv"), layout=layout)
    return cases, report, task.raw_dir(cfg)


# -- the bug ---------------------------------------------------------------


def test_the_flat_layout_converts(tmp_path):
    """The case phase 1 could not run: index found them, convert failed them all."""
    root = _flat(tmp_path / "imagecas")

    cases, report, raw = _index_then_convert(tmp_path, root)

    assert len(cases) == 3
    assert report.ok, report.render()
    assert report.n_train == 3
    for case_id in ("1", "2", "10"):
        assert (raw / "imagesTr" / f"{case_id}_0000.nii.gz").is_file()
        assert (raw / "labelsTr" / f"{case_id}.nii.gz").is_file()


def test_the_nested_layout_still_converts(tmp_path):
    root = _nested(tmp_path / "export")

    cases, report, raw = _index_then_convert(tmp_path, root)

    assert len(cases) == 2
    assert report.ok, report.render()
    assert (raw / "imagesTr" / "c001_0000.nii.gz").is_file()


@pytest.mark.parametrize("layout", ["auto", "flat"])
def test_a_forced_and_an_auto_layout_agree_on_a_flat_tree(tmp_path, layout):
    root = _flat(tmp_path / f"imagecas-{layout}")

    _cases, report, _raw = _index_then_convert(tmp_path, root, layout=layout)

    assert report.ok, report.render()
    assert report.n_train == 3


def test_labels_survive_the_flat_path_with_their_values(tmp_path):
    """Finding the files is not enough; the right label must reach the right case."""
    root = _flat(tmp_path / "imagecas", ids=("1",))

    _cases, report, raw = _index_then_convert(tmp_path, root)

    assert report.ok, report.render()
    written = np.asanyarray(nib.load(str(raw / "labelsTr" / "1.nii.gz")).dataobj)
    assert set(np.unique(written)) == {0, 1}
    assert int(written.sum()) == 8, "the 2x2x2 block, neither lost nor grown"


def test_each_case_keeps_its_own_label_through_the_flat_path(tmp_path):
    """The failure that would not announce itself.

    A missing file raises. A label paired with the wrong case's image trains
    quietly and produces a model that is merely bad. So each case here gets a
    mask of a distinct, known size, and each converted label has to still have
    its own.
    """
    root = tmp_path / "imagecas"
    root.mkdir(parents=True)
    # Ids chosen so string and numeric order disagree, which is what makes a
    # position-based pairing wrong: sorted() gives 1, 10, 137, 2.
    sizes = {"1": 1, "2": 2, "10": 3, "137": 4}
    for case_id, side in sizes.items():
        _volume(root / f"{case_id}.img.nii.gz", np.full((8, 8, 8), 120, dtype=np.int16))
        mask = np.zeros((8, 8, 8), dtype=np.uint8)
        mask[:side, :side, :side] = 1
        _volume(root / f"{case_id}.label.nii.gz", mask)

    _cases, report, raw = _index_then_convert(tmp_path, root)
    assert report.ok, report.render()

    for case_id, side in sizes.items():
        written = np.asanyarray(nib.load(str(raw / "labelsTr" / f"{case_id}.nii.gz")).dataobj)
        assert int(written.sum()) == side ** 3, (
            f"case {case_id} came out with {int(written.sum())} labelled voxels, "
            f"not its own {side ** 3} -- its label was paired with another case")


# -- the class of bug it belonged to ---------------------------------------


def test_a_case_in_meta_but_not_on_disk_is_reported_once(tmp_path):
    """An incomplete transfer, or a stale index. Either way, name it and go on."""
    root = _flat(tmp_path / "imagecas")
    cases = scan(root)
    rows = build_rows(cases, val_fraction=0.0, test_fraction=0.0, seed=1)
    write_meta(root / "meta.csv", rows)
    (root / "2.img.nii.gz").unlink()
    (root / "2.label.nii.gz").unlink()

    cfg, task = _config(tmp_path, root), _task()
    report = convert_dataset(cfg, task, read_meta(root / "meta.csv"))

    assert not report.ok
    assert report.n_train == 2, "the other two still convert"
    failures = [f for f in report.failures if f.case_id == "2"]
    assert len(failures) == 1, "reported once, not once per worker"
    assert "not found under" in failures[0].error
    assert (task.raw_dir(cfg) / "imagesTr" / "1_0000.nii.gz").is_file()


def test_iter_case_ids_sees_a_flat_tree(tmp_path):
    """It looked for `<case>/ct.nii.gz`, so on a flat tree it saw nothing at all."""
    root = _flat(tmp_path / "imagecas")

    assert sorted(iter_case_ids(root)) == ["1", "10", "2"]


def test_dataset_json_counts_only_what_converted(tmp_path):
    import json

    root = _flat(tmp_path / "imagecas")
    cases = scan(root)
    rows = build_rows(cases, val_fraction=0.0, test_fraction=0.0, seed=1)
    write_meta(root / "meta.csv", rows)
    (root / "10.img.nii.gz").unlink()

    cfg, task = _config(tmp_path, root), _task()
    convert_dataset(cfg, task, read_meta(root / "meta.csv"))

    payload = json.loads((task.raw_dir(cfg) / "dataset.json").read_text())
    assert payload["numTraining"] == 2, "a case that failed is not a training case"
