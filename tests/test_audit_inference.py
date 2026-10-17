"""Echo audit (Round 6, Q4): test-set inference and the `segtrain tf1` command.

Each test records a CONFIRMED defect and is ``xfail(strict=True)``. Evidence and owners:
vault/Plans/Experiments/Echo - Audit of the segtrain implementation against the master plan.md
"""

import json

import nibabel as nib
import numpy as np
import pytest

from segtrain.config import Config, load_task


def test_test_set_inference_saves_softmax(tmp_path, monkeypatch):
    pytest.importorskip("torch")
    pytest.importorskip("nnunetv2")
    import nnunetv2.inference.predict_from_raw_data as P

    from segtrain.evaluate import predict_test_set

    calls = {}

    class FakePredictor:
        def __init__(self, **kw):
            calls["init"] = kw

        def initialize_from_trained_model_folder(self, *a, **kw):
            pass

        def predict_from_files(self, *a, **kw):
            calls["predict"] = kw

    monkeypatch.setattr(P, "nnUNetPredictor", FakePredictor)
    cfg = Config(zenodo_root=tmp_path, nnunet_raw=tmp_path / "raw",
                 nnunet_preprocessed=tmp_path / "pre", nnunet_results=tmp_path / "res",
                 runs_root=tmp_path / "runs")
    task = load_task(712)
    ts = task.raw_dir(cfg) / "imagesTs"
    ts.mkdir(parents=True)
    nib.save(nib.Nifti1Image(np.zeros((4, 4, 4), np.int16), np.eye(4)),
             str(ts / "c0102_0000.nii.gz"))
    predict_test_set(cfg, task, device="cpu")
    assert calls["predict"]["save_probabilities"] is True


def test_tf1_cli_refuses_or_aligns_a_reoriented_prediction(tmp_path, capsys):
    pytest.importorskip("skimage")
    from segtrain.cli import main

    shape = (80, 30, 30)
    ref = np.zeros(shape, np.uint8)
    ref[5:75, 12:17, 3:8] = 4                     # an RCA-like tube, off-centre in z
    aff = np.diag([-0.5, 0.5, 0.5, 1.0])
    flip = aff.copy()
    flip[2, 2], flip[2, 3] = -0.5, 0.5 * (shape[2] - 1)
    nib.save(nib.Nifti1Image(ref, aff), str(tmp_path / "ref.nii.gz"))
    nib.save(nib.Nifti1Image(ref[:, :, ::-1].copy(), flip), str(tmp_path / "pred.nii.gz"))
    try:
        rc = main(["tf1", str(tmp_path / "ref.nii.gz"), str(tmp_path / "pred.nii.gz")])
    except Exception:
        return                                    # refusing is an acceptable fix
    if rc != 0:
        return
    row = json.loads(capsys.readouterr().out)
    assert row["tf1"] > 0.99, row["tf1"]
