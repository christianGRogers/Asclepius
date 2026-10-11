"""Run 3's FP-aware loss and its two trainer arms (Round 8, A24): the term acts only on confident
predictions farther than 1.5 mm from any label; the arms differ only in the loss; and the data and
augmentation stream is deterministic, so F0 and F1 see identical batches (A24.1)."""

import json
import os
import subprocess
import sys

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from segtrain.nnunet_ext.fp_aware_loss import (  # noqa: E402
    FPAwareLoss,
    band_voxels,
    far_background,
    fp_term,
)


def _target(shape=(1, 1, 24, 24, 24)):
    t = torch.zeros(shape, dtype=torch.long)
    t[:, :, 10:14, 10:14, 4:20] = 2                    # a short vessel
    return t


def test_band_is_1p5_mm_at_half_millimetre_spacing():
    assert band_voxels(1.5, (0.5, 0.5, 0.5)) == [3, 3, 3]
    far = far_background(_target(), [3, 3, 3])
    assert not far[0, 12, 12, 10]                      # labelled
    assert not far[0, 12, 16, 10]                      # 3 voxels (1.5 mm) from the label: in the band
    assert far[0, 12, 18, 10]                          # 5 voxels away: far background
    t = _target()
    t[0, 0, 2, 2, 2] = 5                               # an ignore voxel also protects its band
    assert not far_background(t, [3, 3, 3])[0, 4, 4, 4]


def _logits(fp_at, conf):
    """Background everywhere (confident), plus a vessel-class prediction at the given voxels."""
    lg = torch.full((1, 5, 24, 24, 24), -10.0)
    lg[:, 0] = 6.0
    for (x, y, z) in fp_at:
        lg[0, 0, x, y, z] = 0.0
        lg[0, 2, x, y, z] = conf
    return lg.requires_grad_(True)


def test_term_punishes_confident_far_predictions_only():
    t, r = _target(), [3, 3, 3]
    clean = fp_term(_logits([], 0.0), t, r)
    far_conf = fp_term(_logits([(12, 20, 10)], 8.0), t, r)
    far_weak = fp_term(_logits([(12, 20, 10)], -1.0), t, r)   # p_fg ~ 0.27
    near_conf = fp_term(_logits([(12, 16, 10)], 8.0), t, r)      # inside the 1.5 mm band
    assert far_conf - clean > 20 * (far_weak - clean) > 0     # focal: confidence dominates
    assert near_conf.item() == pytest.approx(clean.item(), rel=1e-6)
    lg = _logits([(12, 20, 10), (12, 16, 10)], 8.0)
    fp_term(lg, t, r).backward()
    g = lg.grad
    assert g[0, :, 12, 20, 10].abs().sum() > 0                     # far FP: pushed down
    assert g[0, :, 12, 16, 10].abs().sum() == 0                    # band: left to DiceCE
    assert g[0, :, 12, 12, 10].abs().sum() == 0                    # labelled vessel: untouched


def test_loss_wraps_deep_supervision_and_lambda_zero_is_the_base():
    class Base(torch.nn.Module):
        def forward(self, out, tgt):
            return sum(o.float().mean() for o in out)

    out = [_logits([(12, 20, 10)], 8.0), torch.zeros(1, 5, 12, 12, 12)]
    tgt = [_target(), torch.zeros(1, 1, 12, 12, 12, dtype=torch.long)]
    base = Base()(out, tgt)
    assert FPAwareLoss(Base(), (0.5, 0.5, 0.5), lam=0.0)(out, tgt).item() == pytest.approx(base.item())
    f = FPAwareLoss(Base(), (0.5, 0.5, 0.5), lam=1.0, gamma=2.0)
    total = f(out, tgt)
    assert total.item() == pytest.approx(base.item() + f.last_term) and f.last_term > 0
    assert f.describe() == {"lambda": 1.0, "gamma": 2.0, "band_mm": 1.5, "band_voxels": [3, 3, 3]}
    with torch.no_grad():
        f(out, tgt)
    assert len(f.terms) == 1                                       # validation is not recorded


# ------------------------------------------------------------------ the arms (real nnU-Net, CPU)
def _tiny_dataset(tmp_path):
    """Two tiny cases preprocessed by nnU-Net itself, with run 1's plans shrunk to a 16^3 patch."""
    import nibabel as nib

    sys.path.insert(0, os.path.dirname(__file__))
    from test_finetune import _tiny_plans

    plans, dj = _tiny_plans()
    name = plans["dataset_name"]
    raw = tmp_path / "raw" / name
    for d in ("imagesTr", "labelsTr"):
        (raw / d).mkdir(parents=True)
    rng = np.random.default_rng(0)
    aff = np.diag([0.5, 0.5, 0.5, 1.0])
    for c in ("c0001", "c0003"):
        img = rng.normal(0, 100, (40, 40, 40)).astype(np.int16)
        lab = np.zeros((40, 40, 40), np.uint8)
        lab[15:25, 18:22, 5:35] = 2
        img[lab > 0] = 400
        nib.save(nib.Nifti1Image(img, aff), str(raw / "imagesTr" / f"{c}_0000.nii.gz"))
        nib.save(nib.Nifti1Image(lab, aff), str(raw / "labelsTr" / f"{c}.nii.gz"))
    dj = dict(dj, numTraining=2, file_ending=".nii.gz", channel_names={"0": "CT"})
    (raw / "dataset.json").write_text(json.dumps(dj))
    pre = tmp_path / "pre" / name
    pre.mkdir(parents=True)
    plans["configurations"]["3d_fullres"]["spacing"] = [0.5, 0.5, 0.5]
    plans["configurations"]["3d_fullres"]["batch_size"] = 2
    (pre / f"{plans['plans_name']}.json").write_text(json.dumps(plans))
    (pre / "dataset.json").write_text(json.dumps(dj))
    (pre / "splits_final.json").write_text(json.dumps([{"train": ["c0001"], "val": ["c0003"]}]))
    env = dict(os.environ, nnUNet_raw=str(tmp_path / "raw"), nnUNet_preprocessed=str(tmp_path / "pre"),
               nnUNet_results=str(tmp_path / "res"), OMP_NUM_THREADS="1")
    did = int(name[7:10])
    r = subprocess.run(["nnUNetv2_preprocess", "-d", str(did), "-plans_name", plans["plans_name"],
                        "-c", "3d_fullres", "-np", "1"], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    return plans, dj, env


def test_the_two_arms_see_the_same_batches_and_differ_only_in_the_loss(tmp_path, monkeypatch):
    pytest.importorskip("nnunetv2")
    if not __import__("shutil").which("nnUNetv2_preprocess"):
        pytest.skip("nnUNetv2_preprocess not on PATH")
    plans, dj, env = _tiny_dataset(tmp_path)
    for k in ("nnUNet_raw", "nnUNet_preprocessed", "nnUNet_results"):
        monkeypatch.setenv(k, env[k])
    monkeypatch.setenv("nnUNet_n_proc_DA", "2")
    monkeypatch.setenv("SEGTRAIN_SEED", "7")
    from segtrain.nnunet_ext.nnUNetTrainer_segtrain_fppilot import (
        nnUNetTrainer_segtrain_fppilot_F0 as F0,
        nnUNetTrainer_segtrain_fppilot_F1 as F1,
    )

    def batches(cls, k=3):
        p = json.loads(json.dumps(plans))
        p["continue_training"] = False
        t = cls(p, "3d_fullres", 0, dj, torch.device("cpu"))
        t.initialize()
        tr, val = t.get_dataloaders()
        out = [next(tr) for _ in range(k)]
        for g in (tr, val):
            g._finish()
        return t, [(b["data"].numpy().copy(), b["target"][0].numpy().copy()) for b in out]

    t0, b0 = batches(F0)
    t0b, b0b = batches(F0)
    t1, b1 = batches(F1)
    for (x, y), (x2, y2), (x3, y3) in zip(b0, b0b, b1):
        assert np.array_equal(x, x2) and np.array_equal(y, y2)    # deterministic
        assert np.array_equal(x, x3) and np.array_equal(y, y3)    # F1 sees F0's stream
    assert isinstance(t1.loss, FPAwareLoss) and not isinstance(t0.loss, FPAwareLoss)
    assert t1.loss.radius == [3, 3, 3]
