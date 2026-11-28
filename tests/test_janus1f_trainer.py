"""nnUNetTrainer_janus1f and its parent-copy load (#392; F-A2, F-A5, F-A20, F-A29): the step-0
identity, the val test on the keys nnU-Net reads, the fit check's decode and STALL rule, and the
real trainer on CPU."""

from __future__ import annotations

import json

import numpy as np
import pytest

from segtrain.nnunet_ext import janus1f_rules as T

J0_LABELS = {"background": 0, "LM": 1, "LAD": 2, "LCx": 3, "RCA": 4}
J1F_LABELS = {n: i for i, n in enumerate(T.NAMES)} | {"ignore": 13}
PARENTS = T._REPO + "/configs/janus1/j1f_parents.json"


# ------------------------------------------------------------------ torch-free parts
def test_val_test_on_the_keys_nnunet_reads():
    sp = T.load_split()
    tr, val = sp["train620"], T.fitcheck_ids(sp["train620"])
    T.check_keys(tr, val, sp)
    with pytest.raises(RuntimeError, match="locked"):
        T.check_keys(tr, val[:-1] + [sp["locked100"][0]], sp)
    with pytest.raises(RuntimeError, match="locked"):
        T.check_keys(tr + [sp["locked100"][1]], val, sp)
    with pytest.raises(RuntimeError, match="fit-check"):
        T.check_keys(tr, sorted(tr)[:20], sp)


def test_heads_rule():
    assert T.heads_rule("parent_copy:/x.json") == "/x.json"
    with pytest.raises(RuntimeError):
        T.heads_rule("")


def test_fit_check_decode_dice_and_stall():
    rng = np.random.default_rng(0)
    z = rng.normal(size=(13, 6, 6, 6))
    p = np.exp(z) / np.exp(z).sum(0)
    f = T.decode_f(p)
    terr = np.argmax(np.stack([p[list(g)].sum(0) for g in T.F_GROUPS]), 0)
    back = np.zeros_like(terr)
    for t, g in enumerate(T.F_GROUPS):
        back[np.isin(f, g)] = t
    assert np.array_equal(back, terr)
    ref = f.copy()
    ref[0, 0, 0] = 13
    d = T.dice_per_class(f, ref)
    assert all(v is None or v == 1.0 for v in d.values())
    assert T.stall({"D1": 0.09, "OM1": 0.5, "PDA": 0.2, "PLB": 0.3}, 150) == ["D1"]
    assert T.stall({"D1": 0.09}, 300) == []


# ------------------------------------------------------------------ the parent-copy load, tiny
# network
torch = pytest.importorskip("torch")
from segtrain.nnunet_ext import parent_copy as PC  # noqa: E402


class _Dec(torch.nn.Module):
    def __init__(self, c):
        super().__init__()
        self.seg_layers = torch.nn.ModuleList([torch.nn.Conv3d(8, c, 1), torch.nn.Conv3d(4, c, 1)])


class _Net(torch.nn.Module):
    def __init__(self, c):
        super().__init__()
        self.enc = torch.nn.Conv3d(1, 8, 3, padding=1)
        self.up = torch.nn.Conv3d(8, 4, 3, padding=1)
        self.decoder = _Dec(c)

    def forward(self, x):
        a = torch.relu(self.enc(x))
        b = torch.relu(self.up(a))
        return [self.decoder.seg_layers[1](b), self.decoder.seg_layers[0](a)]


def _ckpt(tmp_path, labels=J0_LABELS):
    torch.manual_seed(0)
    src = _Net(5)
    plans = {
        "configurations": {"3d_fullres": {"patch_size": [8, 8, 8]}},
        "foreground_intensity_properties_per_channel": {"0": {"mean": 1.0}},
        "transpose_forward": [0, 1, 2],
        "transpose_backward": [0, 1, 2],
    }
    p = tmp_path / "checkpoint_final.pth"
    torch.save(
        {
            "network_weights": src.state_dict(),
            "current_epoch": 1000,
            "init_args": {
                "plans": plans,
                "configuration": "3d_fullres",
                "dataset_json": {"labels": dict(labels, ignore=5)},
            },
        },
        str(p),
    )
    return p, plans, src


def test_parent_copy_load_and_step0_identity(tmp_path):
    ck, plans, src = _ckpt(tmp_path)
    net = _Net(13)
    s = PC.load_parent_copy(net, ck, PARENTS, plans, "3d_fullres", {"labels": J1F_LABELS})
    heads = s.pop("_source_heads")
    assert s["n_head_tensors"] == 4 and s["n_body_bitwise"] == 4
    for k, v in src.state_dict().items():
        if ".seg_layers." not in k:
            assert torch.equal(net.state_dict()[k], v)
    x = torch.randn(2, 1, 8, 8, 8)
    r = PC.step0_identity(net, x, heads)
    assert r["max_abs_territory_error"] < 1e-5 and r["territory_argmax_agreement"] == 1.0
    assert r["head"] == "decoder.seg_layers.1"
    with torch.no_grad():  # OM2's row left at random init
        net.decoder.seg_layers[1].weight[9].normal_()
        net.decoder.seg_layers[1].bias[9] = 0.0
    with pytest.raises(RuntimeError, match="step-0 identity"):
        PC.step0_identity(net, x, heads)


def test_parent_copy_refuses_wrong_classes_or_plans(tmp_path):
    ck, plans, _ = _ckpt(tmp_path)
    with pytest.raises(ValueError, match="ignore"):
        PC.load_parent_copy(
            _Net(13), ck, PARENTS, plans, "3d_fullres", {"labels": dict(J1F_LABELS, ignore=255)}
        )
    with pytest.raises(ValueError, match="target classes"):
        PC.load_parent_copy(_Net(13), ck, PARENTS, plans, "3d_fullres", {"labels": J0_LABELS})
    other = json.loads(json.dumps(plans))
    other["configurations"]["3d_fullres"]["patch_size"] = [16, 16, 16]
    with pytest.raises(ValueError, match="refusing"):
        PC.load_parent_copy(_Net(13), ck, PARENTS, other, "3d_fullres", {"labels": J1F_LABELS})
    with pytest.raises(FileNotFoundError):
        PC.load_parent_copy(
            _Net(13), tmp_path / "none.pth", PARENTS, plans, "3d_fullres", {"labels": J1F_LABELS}
        )


# ------------------------------------------------------------------ the real trainer, tiny network
def test_real_janus1f_trainer_grows_janus0_by_parent_copy(tmp_path, monkeypatch):
    pytest.importorskip("nnunetv2")
    from test_finetune import _tiny_plans

    from segtrain.nnunet_ext import nnUNetTrainer_janus1f as TR
    from segtrain.nnunet_ext.nnUNetTrainer_segtrain_coronary import nnUNetTrainer_segtrain_coronary

    plans, _ = _tiny_plans()
    dj0 = {
        "channel_names": {"0": "CT"},
        "labels": dict(J0_LABELS, ignore=5),
        "file_ending": ".nii.gz",
    }
    dj1 = dict(dj0, labels=J1F_LABELS)
    for k in ("nnUNet_raw", "nnUNet_preprocessed", "nnUNet_results"):
        monkeypatch.setenv(k, str(tmp_path))
    for k in ("SEGTRAIN_EPOCHS", "SEGTRAIN_WARMUP_ITERS", "SEGTRAIN_ITERATIONS"):
        monkeypatch.delenv(k, raising=False)
    ident = plans["configurations"]["3d_fullres"]["data_identifier"]
    (tmp_path / plans["dataset_name"] / ident).mkdir(parents=True)
    (tmp_path / plans["dataset_name"] / ident / "x.b2nd").write_bytes(b"")
    cpu = torch.device("cpu")

    def build(cls, dj):
        p = json.loads(json.dumps(plans))
        p["continue_training"] = False
        t = cls(p, "3d_fullres", 0, dj, cpu)
        t.initialize()
        return t

    torch.manual_seed(1)
    j0 = build(nnUNetTrainer_segtrain_coronary, dj0)
    ck = tmp_path / "checkpoint_final.pth"
    torch.save(
        {
            "network_weights": j0.network.state_dict(),
            "init_args": j0.my_init_kwargs,
            "trainer_name": "nnUNetTrainerICX4",
            "current_epoch": 1000,
        },
        str(ck),
    )
    monkeypatch.setenv("SEGTRAIN_FINETUNE_FROM", str(ck))
    monkeypatch.setenv("SEGTRAIN_FINETUNE_HEADS", "parent_copy:" + PARENTS)
    monkeypatch.setenv("SEGTRAIN_EPOCHS", "250")
    with pytest.raises(RuntimeError, match="unset"):
        build(TR.nnUNetTrainer_janus1f, dj1)
    monkeypatch.delenv("SEGTRAIN_EPOCHS")
    with pytest.raises(RuntimeError, match="ignore 13"):
        build(TR.nnUNetTrainer_janus1f, dict(dj0, labels=dict(J1F_LABELS, ignore=255)))
    torch.manual_seed(2)
    t = build(TR.nnUNetTrainer_janus1f, dj1)
    assert t.num_epochs == 500 and t._finetune_summary["n_head_tensors"] > 0
    src, got = j0.network.state_dict(), t.network.state_dict()
    for k, v in src.items():
        if ".seg_layers." in k:
            assert got[k].shape[0] == 13
        else:
            assert torch.equal(got[k], v)
    x = torch.randn(1, 1, 16, 16, 16)
    r = PC.step0_identity(t.network, x, t._source_heads)
    assert r["max_abs_territory_error"] < 1e-5
    assert t.perform_actual_validation() is None
    assert not (tmp_path / "validation").exists()


def test_fit_check_writes_fitcheck_json_and_stall(tmp_path, monkeypatch):
    """fit_check with nnU-Net's predictor and dataset replaced by fakes: a model that never names D1
    STALLs."""
    pytest.importorskip("nnunetv2")
    import types

    import nnunetv2.inference.predict_from_raw_data as P

    from segtrain.nnunet_ext import nnUNetTrainer_janus1f as TR

    seg = np.zeros((1, 4, 4, 4), np.int16)
    seg[0, 0] = 5  # D1 in the reference
    seg[0, 1] = 2

    class FakePred:
        def __init__(self, **kw):
            pass

        def manual_initialization(self, *a):
            pass

        def predict_sliding_window_return_logits(self, data):
            z = torch.full((13, 4, 4, 4), -5.0)
            z[2] = 5.0  # LAD everywhere: D1 never named
            return z

    class FakeDS:
        def __init__(self, folder, keys, folder_with_segs_from_previous_stage=None):
            self.identifiers = list(keys)

        def load_case(self, k):
            return np.zeros((1, 4, 4, 4), np.float32), seg, None, {}

    monkeypatch.setattr(P, "nnUNetPredictor", FakePred)
    t = types.SimpleNamespace(
        output_folder=str(tmp_path),
        device=torch.device("cpu"),
        network=_Net(13),
        enable_deep_supervision=True,
        dataset_class=FakeDS,
        preprocessed_dataset_folder="",
        folder_with_segs_from_previous_stage=None,
        plans_manager=None,
        configuration_manager=None,
        dataset_json={},
        do_split=lambda: (["a"], ["c0001", "c0002"]),
        set_deep_supervision_enabled=lambda e: None,
        print_to_log_file=lambda *a: None,
    )
    t._write_json = types.MethodType(TR.nnUNetTrainer_janus1f._write_json, t)
    out = TR.nnUNetTrainer_janus1f.fit_check(t, 150)
    assert out["stall_classes"] == ["D1"] and out["mean_dice"]["D1"] == 0.0
    assert json.loads((tmp_path / "fitcheck.json").read_text())["150"]["cases"] == [
        "c0001",
        "c0002",
    ]
    assert "D1" in (tmp_path / "STALL").read_text()
    (tmp_path / "STALL").unlink()
    TR.nnUNetTrainer_janus1f.fit_check(t, 300)
    assert not (tmp_path / "STALL").exists()
    assert sorted(json.loads((tmp_path / "fitcheck.json").read_text())) == ["150", "300"]
