"""``evaluate.score_predictions`` leaves a task's ignore label out of the scoring (D40, #278).

A reference voxel carrying nnU-Net's ignore label belongs to no class, so a prediction there is
neither a hit nor a false positive. Synthetic volumes only.
"""

import sys
from pathlib import Path

import nibabel as nib
import numpy as np

REPO = Path(__file__).resolve().parents[1]
if str(REPO / "src") not in sys.path:
    sys.path.append(str(REPO / "src"))

from segtrain.config import Config, TaskConfig, load_label_set  # noqa: E402
from segtrain.evaluate import score_predictions  # noqa: E402


def _setup(tmp_path, ignore_label):
    task_file = tmp_path / "Dataset799_IgnoreEval.yaml"
    task_file.write_text("ignore_label: true\n" if ignore_label else "folds: [0]\n")
    task = TaskConfig(dataset_id=799, dataset_name="IgnoreEval",
                      label_set=load_label_set("coronary_icx4",
                                               labels_dir=REPO / "configs" / "labels"),
                      spacing=None, configuration="3d_fullres", source_path=task_file)
    cfg = Config(zenodo_root=tmp_path, nnunet_raw=tmp_path / "raw",
                 nnunet_preprocessed=tmp_path / "pre", nnunet_results=tmp_path / "res",
                 runs_root=tmp_path / "runs")
    ref = np.zeros((12, 12, 12), np.uint8)
    ref[2:5, 2:5, 2:5] = 2                      # LAD
    ref[7:10, 7:10, 7:10] = 5                   # shared by two classes in the read: ignore
    pred = np.zeros_like(ref)
    pred[2:5, 2:5, 2:5] = 2
    pred[7:10, 7:10, 7:10] = 3                  # LCx where the reference has no class
    (task.raw_dir(cfg) / "labelsTs").mkdir(parents=True)
    nib.save(nib.Nifti1Image(ref, np.eye(4)), str(task.raw_dir(cfg) / "labelsTs" / "c0001.nii.gz"))
    preds = tmp_path / "preds"
    preds.mkdir()
    nib.save(nib.Nifti1Image(pred, np.eye(4)), str(preds / "c0001.nii.gz"))
    return cfg, task, preds


def _by_name(scores):
    return {s.name: s for s in scores}


def test_ignore_voxels_are_left_out(tmp_path):
    cfg, task, preds = _setup(tmp_path, ignore_label=True)
    scores = _by_name(score_predictions(cfg, task, preds, compute_nsd=False,
                                        pool_seal="exclude")["c0001"])
    assert scores["LAD"].dice == 1.0
    assert scores["LCx"].pred_voxels == 0       # the prediction under ignore is not scored


def test_without_an_ignore_label_nothing_changes(tmp_path):
    cfg, task, preds = _setup(tmp_path, ignore_label=False)
    scores = _by_name(score_predictions(cfg, task, preds, compute_nsd=False,
                                        pool_seal="exclude")["c0001"])
    assert scores["LCx"].pred_voxels == 27      # a false positive, as before
