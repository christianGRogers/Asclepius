"""SegQueue14 export -> ``segtrain convert`` with ``coronary_icx14``, end to end.

A 14-class read goes out of SegQueue14 as one binary mask per class
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
    """A 14-class volume with every class present and a few touching."""
    rng = np.random.default_rng(seed)
    vol = np.zeros(shape, dtype=np.uint8)
    for k in range(1, 15):
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


def test_an_integer_volume_with_imagecas_x_values_converts_unchanged(tmp_path):
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
    assert set(np.unique(got)) == set(range(15))


def test_absent_optional_classes_are_reported_missing_not_dropped(tmp_path):
    """A case with no IM or L-PDA (common) still converts; those are absent, not lost."""
    root = tmp_path / "icx"
    truth = _read(seed=3)
    truth[truth == labels.LABEL_VALUES["IM"]] = 0
    truth[truth == labels.LABEL_VALUES["L-PDA"]] = 0
    folder = root / "imagecas_0011"
    folder.mkdir(parents=True)
    nib.save(nib.Nifti1Image(np.zeros(truth.shape, dtype=np.int16), np.eye(4)),
             str(folder / "ct.nii.gz"))
    nib.save(nib.Nifti1Image(truth, np.eye(4)), str(folder / "labels.nii.gz"))
    report, raw = _convert(tmp_path, root)
    assert report.ok, report.render()
    got = np.asarray(nib.load(str(raw / "labelsTr" / "imagecas_0011.nii.gz")).dataobj)
    assert np.array_equal(got, truth)
