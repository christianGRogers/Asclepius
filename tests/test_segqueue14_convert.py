"""SegQueue14 export -> ``segtrain convert`` with ``coronary_icx4``, end to end.

A read in the project's four classes (D25) goes out of SegQueue14 as one binary mask per class
(``segmentations/<name>.nii.gz``) and must come back from ``segtrain convert`` as
the same integers on the same voxels. Run both ways a training set can arrive:
per-class masks (the export) and a single label volume (an ImageCAS-X file or a
prelabel, whose values are already ours).

The exporter is loaded from its file, as ``experiments/Echo/segqueue_dry_run.py``
loads the live one: its package ``__init__`` needs Girder, the functions used here
do not.
"""

import importlib.util
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
_SRC = REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.append(str(_SRC))

from segqueue14 import labels  # noqa: E402
from segtrain.config import Config, TaskConfig, load_label_set  # noqa: E402
from segtrain.convert import convert_dataset  # noqa: E402
from segtrain.index import build_rows, scan, write_meta  # noqa: E402
from segtrain.splits import read_meta  # noqa: E402


def _exporter():
    pytest.importorskip("SimpleITK")
    spec = importlib.util.spec_from_file_location(
        "sq14_export", REPO / "server" / "girder_segqueue14" / "export.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _label_set():
    return load_label_set(labels.LABEL_SET_NAME, labels_dir=REPO / "configs" / "labels")


def _read(seed=0, shape=(24, 20, 18)):
    """A volume with every project class present and a few touching."""
    rng = np.random.default_rng(seed)
    vol = np.zeros(shape, dtype=np.uint8)
    for k in range(1, labels.N_CLASSES + 1):
        z = rng.integers(0, shape[0] - 3)
        y = rng.integers(0, shape[1] - 3)
        x = rng.integers(0, shape[2] - 3)
        vol[z:z + 3, y:y + 3, x:x + 2] = k
    return vol


def _config(tmp_path, root):
    return Config(zenodo_root=root, nnunet_raw=tmp_path / "raw",
                  nnunet_preprocessed=tmp_path / "pre", nnunet_results=tmp_path / "res",
                  runs_root=tmp_path / "runs", link_mode="copy", convert_workers=1)


def _task():
    return TaskConfig(dataset_id=799, dataset_name="SegQueue14RoundTrip",
                      label_set=_label_set(), spacing=None, configuration="3d_fullres")


def _convert(tmp_path, root):
    rows = build_rows(scan(root), val_fraction=0.0, test_fraction=0.0, seed=1)
    write_meta(root / "meta.csv", rows)
    cfg, task = _config(tmp_path, root), _task()
    report = convert_dataset(cfg, task, read_meta(root / "meta.csv"))
    return report, task.raw_dir(cfg)


def test_the_export_writes_one_mask_per_class_and_convert_restores_the_labels(tmp_path):
    sitk = pytest.importorskip("SimpleITK")
    ex = _exporter()
    segments = labels.segment_specs()
    root = tmp_path / "export"
    affine = np.diag([0.5, 0.5, 0.6, 1.0])

    truths = {}
    for i, case in enumerate(("imagecas_0002", "imagecas_0005", "asoca_7")):
        truth = _read(seed=i)
        truths[case] = truth
        folder = root / case
        (folder / "segmentations").mkdir(parents=True)
        ct = nib.Nifti1Image(np.full(truth.shape, 300, dtype=np.int16), affine)
        nib.save(ct, str(folder / "ct.nii.gz"))
        # The exporter's own path: an integer volume on the CT grid, split by value
        # and written against the label image's geometry.
        stored = sitk.ReadImage(str(folder / "ct.nii.gz"))
        array = np.ascontiguousarray(truth.transpose(2, 1, 0))     # sitk is z,y,x
        label_image = sitk.GetImageFromArray(array)
        label_image.CopyInformation(stored)
        masks = ex.splitLabels(sitk.GetArrayFromImage(label_image), segments)
        assert sorted(masks) == sorted(labels.NAMES)
        for name, mask in masks.items():
            ex._writeMask(mask, label_image, str(folder / "segmentations" / f"{name}.nii.gz"))

    report, raw = _convert(tmp_path, root)
    assert report.ok, report.render()
    assert report.n_train == 3
    for case, truth in truths.items():
        got = np.asarray(nib.load(str(raw / "labelsTr" / f"{case}.nii.gz")).dataobj)
        assert np.array_equal(got, truth), case
    dataset = (raw / "dataset.json").read_text()
    for name in labels.NAMES:
        assert f'"{name}"' in dataset


def test_an_integer_volume_in_the_project_values_converts_unchanged(tmp_path):
    root = tmp_path / "icx"
    truth = _read(seed=5)
    folder = root / "imagecas_0010"
    folder.mkdir(parents=True)
    affine = np.diag([0.4, 0.4, 0.5, 1.0])
    nib.save(nib.Nifti1Image(np.zeros(truth.shape, dtype=np.int16), affine),
             str(folder / "ct.nii.gz"))
    nib.save(nib.Nifti1Image(truth, affine), str(folder / "labels.nii.gz"))

    report, raw = _convert(tmp_path, root)
    assert report.ok, report.render()
    got = np.asarray(nib.load(str(raw / "labelsTr" / "imagecas_0010.nii.gz")).dataobj)
    assert np.array_equal(got, truth)
    assert set(np.unique(got)) == set(range(labels.N_CLASSES + 1))


def test_absent_optional_classes_are_reported_missing_not_dropped(tmp_path):
    """A case with no LM (separate LAD and LCx ostia) still converts; LM is absent, not lost."""
    root = tmp_path / "icx"
    truth = _read(seed=3)
    truth[truth == labels.LABEL_VALUES["LM"]] = 0
    folder = root / "imagecas_0011"
    folder.mkdir(parents=True)
    nib.save(nib.Nifti1Image(np.zeros(truth.shape, dtype=np.int16), np.eye(4)),
             str(folder / "ct.nii.gz"))
    nib.save(nib.Nifti1Image(truth, np.eye(4)), str(folder / "labels.nii.gz"))
    report, raw = _convert(tmp_path, root)
    assert report.ok, report.render()
    got = np.asarray(nib.load(str(raw / "labelsTr" / "imagecas_0011.nii.gz")).dataobj)
    assert np.array_equal(got, truth)


# ------------------------------------------------- D39 (#275): class-stack submissions


def _write_stack_case(sitk, ex, folder, classes, affine):
    """Write a CT and its class-stack submission, then export the stack as the server does."""
    from segqueue14 import labelfile

    (folder / "segmentations").mkdir(parents=True)
    shape = next(iter(classes.values())).shape
    nib.save(nib.Nifti1Image(np.full(shape, 300, dtype=np.int16), affine),
             str(folder / "ct.nii.gz"))
    ct = sitk.ReadImage(str(folder / "ct.nii.gz"))
    d, sp, o = ct.GetDirection(), ct.GetSpacing(), ct.GetOrigin()
    ijk = [[d[3 * r + c] * sp[c] for c in range(3)] + [o[r]] for r in range(3)]
    stack = folder.parent / f"{folder.name}.seg.nrrd"
    labelfile.write_class_stack(
        str(stack), [np.ascontiguousarray(classes[n].transpose(2, 1, 0)) for n in labels.NAMES],
        labels.NAMES, ijk)
    for name, (mask, grid) in ex.splitClassStack(str(stack), labels.segment_specs()).items():
        ex._writeMask(mask, grid, str(folder / "segmentations" / f"{name}.nii.gz"))
    stack.unlink()


def test_a_class_stack_without_overlaps_exports_and_converts_unchanged(tmp_path):
    sitk = pytest.importorskip("SimpleITK")
    ex = _exporter()
    root = tmp_path / "export"
    truth = _read(seed=7)
    classes = {name: (truth == labels.LABEL_VALUES[name]).astype(np.uint8)
               for name in labels.NAMES}
    _write_stack_case(sitk, ex, root / "imagecas_0003", classes, np.diag([0.5, 0.5, 0.6, 1.0]))
    report, raw = _convert(tmp_path, root)
    assert report.ok, report.render()
    got = np.asarray(nib.load(str(raw / "labelsTr" / "imagecas_0003.nii.gz")).dataobj)
    assert np.array_equal(got, truth)


def test_overlapping_classes_are_exported_whole_and_refused_by_convert(tmp_path):
    """#275: the export keeps every class whole; convert under 'refuse' (task 716) picks no
    class for a shared voxel -- the case is reported, named, and not converted."""
    sitk = pytest.importorskip("SimpleITK")
    ex = _exporter()
    root = tmp_path / "export"
    tree = (_read(seed=2) > 0).astype(np.uint8)
    classes = {name: tree.copy() for name in labels.NAMES}          # untouched seeded case
    _write_stack_case(sitk, ex, root / "imagecas_0004", classes, np.diag([0.5, 0.5, 0.6, 1.0]))
    for name in labels.NAMES:
        mask = np.asarray(nib.load(str(root / "imagecas_0004" / "segmentations"
                                       / f"{name}.nii.gz")).dataobj)
        assert np.array_equal(mask > 0, tree > 0), name

    rows = build_rows(scan(root), val_fraction=0.0, test_fraction=0.0, seed=1)
    write_meta(root / "meta.csv", rows)
    cfg, task = _config(tmp_path, root), _task()
    cfg.overlap_policy = "refuse"
    report = convert_dataset(cfg, task, read_meta(root / "meta.csv"))
    assert not report.ok
    [failure] = report.failures
    assert "classes overlap" in failure.error and "LM/LAD" in failure.error
    assert "#275" in failure.error
    assert not (task.raw_dir(cfg) / "labelsTr" / "imagecas_0004.nii.gz").exists()


def test_task_716_trains_shared_voxels_as_ignore():
    """D40 (#278): task 716 writes shared voxels as nnU-Net's ignore label."""
    from segtrain.config import load_task
    from segtrain.plans import task_extras

    task = load_task(716, tasks_dir=REPO / "configs" / "tasks",
                     labels_dir=REPO / "configs" / "labels")
    extras = task_extras(task)
    assert extras["overlap_policy"] == "ignore"
    assert extras["ignore_label"] is True


# ------------------------------------------------- D40 (#278): shared voxels -> ignore

IGNORE = labels.N_CLASSES + 1


def _ignore_task(tmp_path, policy="ignore", ignore_label=True):
    """A task like 716 on the round-trip label set: ``overlap_policy`` and ``ignore_label``."""
    task_file = tmp_path / "Dataset799_SegQueue14RoundTrip.yaml"
    task_file.write_text(f"overlap_policy: {policy}\n"
                         + ("ignore_label: true\n" if ignore_label else ""))
    return TaskConfig(dataset_id=799, dataset_name="SegQueue14RoundTrip",
                      label_set=_label_set(), spacing=None, configuration="3d_fullres",
                      source_path=task_file)


def _write_masks(folder, classes):
    """A SegQueue14 export folder: ct.nii.gz + segmentations/<class>.nii.gz, classes whole."""
    affine = np.diag([0.5, 0.5, 0.6, 1.0])
    (folder / "segmentations").mkdir(parents=True)
    shape = next(iter(classes.values())).shape
    nib.save(nib.Nifti1Image(np.full(shape, 300, dtype=np.int16), affine),
             str(folder / "ct.nii.gz"))
    for name, mask in classes.items():
        nib.save(nib.Nifti1Image(mask.astype(np.uint8), affine),
                 str(folder / "segmentations" / f"{name}.nii.gz"))


def _convert_with(tmp_path, root, task):
    rows = build_rows(scan(root), val_fraction=0.0, test_fraction=0.0, seed=1)
    write_meta(root / "meta.csv", rows)
    cfg = _config(tmp_path, root)
    report = convert_dataset(cfg, task, read_meta(root / "meta.csv"))
    return report, task.raw_dir(cfg)


def _label(raw, case):
    return np.asarray(nib.load(str(raw / "labelsTr" / f"{case}.nii.gz")).dataobj)


def test_an_untouched_seeded_read_converts_to_ignore_on_the_tree(tmp_path):
    """Four identical full masks (an untouched seeded case): all ignore on the tree, 0 elsewhere."""
    sitk = pytest.importorskip("SimpleITK")
    ex = _exporter()
    root = tmp_path / "export"
    tree = _read(seed=2) > 0
    classes = {name: tree.astype(np.uint8) for name in labels.NAMES}
    _write_stack_case(sitk, ex, root / "imagecas_0004", classes, np.diag([0.5, 0.5, 0.6, 1.0]))

    report, raw = _convert_with(tmp_path, root, _ignore_task(tmp_path))
    assert report.ok, report.render()
    got = _label(raw, "imagecas_0004")
    assert np.array_equal(got, np.where(tree, IGNORE, 0))
    [case] = report.with_overlaps
    assert case.ignored == int(tree.sum())
    text = report.render()
    assert f"imagecas_0004: {int(tree.sum())} ignored voxels" in text
    assert "LM/LAD" in text and "D40" in text


def test_a_partly_trimmed_read_keeps_single_class_voxels_and_ignores_only_shared(tmp_path):
    root = tmp_path / "export"
    truth = _read(seed=7)
    classes = {name: truth == labels.LABEL_VALUES[name] for name in labels.NAMES}
    lcx = classes["LCx"]
    # The annotator trimmed LM, LCx and RCA to their own vessels but left LAD over LCx too.
    classes["LAD"] = classes["LAD"] | lcx
    _write_masks(root / "imagecas_0003", classes)

    report, raw = _convert_with(tmp_path, root, _ignore_task(tmp_path))
    assert report.ok, report.render()
    got = _label(raw, "imagecas_0003")
    want = truth.copy()
    want[lcx] = IGNORE
    assert np.array_equal(got, want)
    [case] = report.with_overlaps
    assert case.ignored == int(lcx.sum())
    assert case.overlap_pairs == [("LAD", "LCx", int(lcx.sum()))]
    assert f"imagecas_0003: {int(lcx.sum())} ignored voxels (LAD/LCx {int(lcx.sum())})" \
        in report.render()


def test_three_classes_on_one_voxel_count_it_once(tmp_path):
    root = tmp_path / "export"
    truth = _read(seed=4)
    classes = {name: truth == labels.LABEL_VALUES[name] for name in labels.NAMES}
    rca = classes["RCA"]
    classes["LM"] = classes["LM"] | rca
    classes["LAD"] = classes["LAD"] | rca
    _write_masks(root / "imagecas_0006", classes)

    report, raw = _convert_with(tmp_path, root, _ignore_task(tmp_path))
    assert report.ok, report.render()
    got = _label(raw, "imagecas_0006")
    want = truth.copy()
    want[rca] = IGNORE
    assert np.array_equal(got, want)
    assert report.with_overlaps[0].ignored == int(rca.sum())


def test_an_overlap_free_read_converts_exactly_as_before(tmp_path):
    root = tmp_path / "export"
    truth = _read(seed=9)
    _write_masks(root / "imagecas_0007",
                 {name: truth == labels.LABEL_VALUES[name] for name in labels.NAMES})
    report, raw = _convert_with(tmp_path, root, _ignore_task(tmp_path))
    assert report.ok, report.render()
    assert np.array_equal(_label(raw, "imagecas_0007"), truth)
    assert not report.with_overlaps
    assert "ignore" not in report.render()


def test_an_old_single_label_read_converts_as_before(tmp_path):
    root = tmp_path / "icx"
    truth = _read(seed=5)
    folder = root / "imagecas_0010"
    folder.mkdir(parents=True)
    affine = np.diag([0.4, 0.4, 0.5, 1.0])
    nib.save(nib.Nifti1Image(np.zeros(truth.shape, dtype=np.int16), affine),
             str(folder / "ct.nii.gz"))
    nib.save(nib.Nifti1Image(truth, affine), str(folder / "labels.nii.gz"))
    report, raw = _convert_with(tmp_path, root, _ignore_task(tmp_path))
    assert report.ok, report.render()
    assert np.array_equal(_label(raw, "imagecas_0010"), truth)


def test_the_dataset_json_declares_ignore_as_the_highest_label(tmp_path):
    import json

    root = tmp_path / "export"
    truth = _read(seed=1)
    _write_masks(root / "imagecas_0008",
                 {name: truth > 0 for name in labels.NAMES})
    report, raw = _convert_with(tmp_path, root, _ignore_task(tmp_path))
    assert report.ok, report.render()
    dj = json.loads((raw / "dataset.json").read_text())
    assert dj["labels"] == {"background": 0, **dict(labels.LABEL_VALUES), "ignore": IGNORE}
    assert dj["labels"]["ignore"] == max(dj["labels"].values())


def test_ignore_without_an_ignore_label_is_refused(tmp_path):
    root = tmp_path / "export"
    truth = _read(seed=1)
    _write_masks(root / "imagecas_0008", {name: truth > 0 for name in labels.NAMES})
    with pytest.raises(ValueError, match="ignore_label: true"):
        _convert_with(tmp_path, root, _ignore_task(tmp_path, ignore_label=False))


@pytest.mark.parametrize("policy", ["smaller_wins", "label_order"])
def test_the_other_policies_still_pick_a_class(tmp_path, policy):
    root = tmp_path / "export"
    tree = _read(seed=2) > 0
    _write_masks(root / "imagecas_0004", {name: tree for name in labels.NAMES})
    report, raw = _convert_with(tmp_path, root, _ignore_task(tmp_path, policy=policy))
    assert report.ok, report.render()
    got = _label(raw, "imagecas_0004")
    assert set(np.unique(got[tree])) <= set(labels.LABEL_VALUES.values())
    assert (got[~tree] == 0).all()
