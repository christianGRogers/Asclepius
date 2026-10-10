"""The wave fine-tune trainer (Round 6, A17a): the source checkpoint is loaded in full, output
heads included and bitwise identical; plans/classes/keys must match; the LR warms up linearly over
a stated number of iterations, then decays poly; the 1e-3 fallback arm exists; sealed refusal."""

import json

import pytest

from segtrain.nnunet_ext.finetune_schedule import WarmupPolyScheduler, warmup_poly_lr

PEAK, W, T = 1e-2, 2500, 250 * 250


# ------------------------------------------------------------------ schedule (torch-free)
def test_warmup_is_linear_over_the_stated_iterations():
    assert warmup_poly_lr(0, PEAK, W, T) == pytest.approx(PEAK / W)            # iteration 0
    assert warmup_poly_lr(W // 2 - 1, PEAK, W, T) == pytest.approx(PEAK / 2)   # mid-ramp
    assert warmup_poly_lr(W - 1, PEAK, W, T) == pytest.approx(PEAK)            # end of ramp
    ramp = [warmup_poly_lr(i, PEAK, W, T) for i in range(W)]
    assert all(b > a for a, b in zip(ramp, ramp[1:]))


def test_poly_decay_after_the_warmup():
    assert warmup_poly_lr(W, PEAK, W, T) == pytest.approx(PEAK)
    mid = W + (T - W) // 2
    assert warmup_poly_lr(mid, PEAK, W, T) == pytest.approx(PEAK * 0.5 ** 0.9, rel=1e-3)
    assert warmup_poly_lr(T - 1, PEAK, W, T) < 1e-5 * PEAK * 100
    decay = [warmup_poly_lr(i, PEAK, W, T) for i in range(W, T, 997)]
    assert all(b < a for a, b in zip(decay, decay[1:]))


def test_scheduler_sets_every_param_group():
    class Opt:
        param_groups = [{"lr": 0.0}, {"lr": 0.0}]

    s = WarmupPolyScheduler(Opt, PEAK, W, T)
    assert s.step(W - 1) == pytest.approx(PEAK)
    assert all(g["lr"] == pytest.approx(PEAK) for g in Opt.param_groups)
    d = s.describe()
    assert d["warmup_iters"] == W and d["lr_end_of_warmup"] == pytest.approx(PEAK)


# ------------------------------------------------------------------ full load (tiny network, CPU)
torch = pytest.importorskip("torch")


def _net(seed, features=(4, 8, 8)):
    from dynamic_network_architectures.architectures.unet import PlainConvUNet

    torch.manual_seed(seed)
    return PlainConvUNet(1, len(features), list(features), torch.nn.Conv3d, 3, [1, 2, 2], 1, 5, 1,
                         conv_bias=True, norm_op=torch.nn.InstanceNorm3d,
                         norm_op_kwargs={"eps": 1e-5, "affine": True}, nonlin=torch.nn.LeakyReLU,
                         deep_supervision=True)


PLANS = {"configurations": {"3d_fullres": {"spacing": [0.5, 0.5, 0.5], "patch_size": [16, 16, 16],
                                           "architecture": {"n_stages": 3}}},
         "foreground_intensity_properties_per_channel": {"0": {"percentile_00_5": -300.0,
                                                               "percentile_99_5": 1300.0,
                                                               "mean": 100.0, "std": 400.0}},
         "transpose_forward": [0, 1, 2], "transpose_backward": [0, 1, 2]}
DJ = {"labels": {"background": 0, "left_main": 1, "left_anterior_descending": 2,
                 "left_circumflex": 3, "right_coronary_artery": 4, "ignore": 5}}


def _checkpoint(tmp_path, net, plans=PLANS, dataset_json=DJ):
    path = tmp_path / "checkpoint_final.pth"
    torch.save({"network_weights": net.state_dict(), "current_epoch": 412,
                "trainer_name": "nnUNetTrainer_segtrain_coronary",
                "init_args": {"plans": plans, "configuration": "3d_fullres", "fold": 0,
                              "dataset_json": dataset_json}}, str(path))
    return path


def test_full_load_keeps_the_output_heads_bitwise(tmp_path):
    from segtrain.nnunet_ext.finetune_load import load_finetune_source

    source, target = _net(1), _net(2)
    heads = [k for k in source.state_dict() if ".seg_layers." in k]
    assert heads, "the tiny network must have deep-supervision heads"
    assert not torch.equal(source.state_dict()[heads[0]], target.state_dict()[heads[0]])
    summary = load_finetune_source(target, _checkpoint(tmp_path, source), PLANS, "3d_fullres", DJ)
    for k, v in source.state_dict().items():
        assert torch.equal(target.state_dict()[k], v), k
    assert summary["heads_loaded"] and summary["n_head_tensors"] == len(heads)
    assert summary["source_epoch"] == 412 and len(summary["source_sha256"]) == 64


def test_stock_pretrained_weights_would_reinitialise_the_heads(tmp_path):
    """The premise of A17a (Foxtrot F1), on nnU-Net 2.8.1's own loader."""
    lpw = pytest.importorskip("nnunetv2.run.load_pretrained_weights")
    source, target = _net(1), _net(2)
    before = {k: v.clone() for k, v in target.state_dict().items()}
    lpw.load_pretrained_weights(target, str(_checkpoint(tmp_path, source)))
    heads = [k for k in source.state_dict() if ".seg_layers." in k]
    assert all(torch.equal(target.state_dict()[k], before[k]) for k in heads)        # not loaded
    body = [k for k in source.state_dict() if ".seg_layers." not in k]
    assert all(torch.equal(target.state_dict()[k], source.state_dict()[k]) for k in body)


def test_ignore_label_difference_is_allowed(tmp_path):
    from segtrain.nnunet_ext.finetune_load import load_finetune_source

    no_ignore = {"labels": {k: v for k, v in DJ["labels"].items() if k != "ignore"}}
    load_finetune_source(_net(2), _checkpoint(tmp_path, _net(1)), PLANS, "3d_fullres", no_ignore)


@pytest.mark.parametrize("change", ["classes", "spacing", "window", "architecture"])
def test_incompatible_sources_are_refused(tmp_path, change):
    from segtrain.nnunet_ext.finetune_load import load_finetune_source

    plans, dj, target = json.loads(json.dumps(PLANS)), json.loads(json.dumps(DJ)), _net(2)
    if change == "classes":
        dj["labels"]["ramus"] = 6
    elif change == "spacing":
        plans["configurations"]["3d_fullres"]["spacing"] = [0.7, 0.7, 0.7]
    elif change == "window":
        plans["foreground_intensity_properties_per_channel"]["0"]["percentile_99_5"] = 719.0
    else:
        target = _net(2, features=(4, 8, 16))
    with pytest.raises(ValueError, match="refusing"):
        load_finetune_source(target, _checkpoint(tmp_path, _net(1)), plans, "3d_fullres", dj)


def test_missing_source_is_an_error(tmp_path):
    from segtrain.nnunet_ext.finetune_load import load_finetune_source

    with pytest.raises(FileNotFoundError):
        load_finetune_source(_net(2), tmp_path / "nope.pth", PLANS, "3d_fullres", DJ)


# ------------------------------------------------------------------ the trainer class (~8 s import)
def test_trainer_steps_the_lr_every_iteration_and_has_the_fallback_arm():
    pytest.importorskip("nnunetv2")
    import unittest.mock as m

    from segtrain.nnunet_ext.nnUNetTrainer_segtrain_coronary import nnUNetTrainer_segtrain_coronary
    from segtrain.nnunet_ext.nnUNetTrainer_segtrain_finetune import (
        nnUNetTrainer_segtrain_finetune as FT,
    )
    from segtrain.nnunet_ext.nnUNetTrainer_segtrain_finetune import (
        nnUNetTrainer_segtrain_finetune_lr1e3 as FT3,
    )

    assert FT.PEAK_LR == 1e-2 and FT3.PEAK_LR == 1e-3 and issubclass(FT3, FT)
    assert issubclass(FT, nnUNetTrainer_segtrain_coronary)   # window, mirroring, softmax, A14

    class Opt:
        param_groups = [{"lr": 0.0}]

    t = FT.__new__(FT)
    t.num_epochs, t.num_iterations_per_epoch, t.initial_lr, t.warmup_iters = 250, 250, 1e-2, W
    t.lr_scheduler = WarmupPolyScheduler(Opt, 1e-2, W, 250 * 250)
    t.network = m.MagicMock()
    t.logger = m.MagicMock()
    t.print_to_log_file = lambda *a, **k: None
    t.current_epoch = 0
    seen = []
    with m.patch.object(nnUNetTrainer_segtrain_coronary, "train_step",
                        lambda self, batch: seen.append(Opt.param_groups[0]["lr"]) or {}):
        t.on_train_epoch_start()
        for _ in range(3):
            t.train_step({})
        assert seen == pytest.approx([1e-2 / W, 2e-2 / W, 3e-2 / W])
        t.current_epoch = 10            # epoch 10 starts at iteration 2500 = end of warm-up
        t.on_train_epoch_start()
        t.train_step({})
        assert seen[-1] == pytest.approx(1e-2)
    t.logger.log.assert_any_call("lrs", pytest.approx(1e-2 / W), 0)


def test_sealed_guard_maps_every_name():
    from segtrain.nnunet_ext.sealed_guard import refuse_sealed

    assert refuse_sealed(["c0003", "c0003__r2", "imagecas_0004"]) == 3
    with pytest.raises(RuntimeError, match="A14"):
        refuse_sealed(["c0003", "imagecas_0003__r2"])          # = c0002, sealed
    with pytest.raises(RuntimeError, match="A14"):
        refuse_sealed(["patient_7"])


# ------------------------------------------------------------------ the real trainer, tiny network
def _tiny_plans():
    from pathlib import Path

    r = Path(__file__).resolve().parents[1] / "trillium-results" / "round5" / "atlas" / "results"
    plans = json.loads((r / "nnUNetResEncUNetPlans_60G_iso05.json").read_text())
    dj = json.loads((r / "dataset.json").read_text())
    c = plans["configurations"]["3d_fullres"]
    c["patch_size"] = [16, 16, 16]
    c["architecture"] = {
        "network_class_name": "dynamic_network_architectures.architectures.unet.PlainConvUNet",
        "arch_kwargs": {"n_stages": 3, "features_per_stage": [4, 8, 8],
                        "conv_op": "torch.nn.modules.conv.Conv3d", "kernel_sizes": [[3, 3, 3]] * 3,
                        "strides": [[1, 1, 1], [2, 2, 2], [2, 2, 2]], "n_conv_per_stage": [1, 1, 1],
                        "n_conv_per_stage_decoder": [1, 1], "conv_bias": True,
                        "norm_op": "torch.nn.modules.instancenorm.InstanceNorm3d",
                        "norm_op_kwargs": {"eps": 1e-5, "affine": True}, "dropout_op": None,
                        "dropout_op_kwargs": None, "nonlin": "torch.nn.LeakyReLU",
                        "nonlin_kwargs": {"inplace": True}},
        "_kw_requires_import": ["conv_op", "norm_op", "dropout_op", "nonlin"]}
    dj["labels"]["ignore"] = 5
    return plans, dj


def test_real_finetune_trainer_loads_the_master_checkpoint_heads_included(tmp_path, monkeypatch):
    """The actual trainer classes on CPU: a coronary-trainer checkpoint is loaded by the fine-tune
    trainer's initialize() with every tensor identical (heads included), at 250 epochs, peak 1e-2,
    warm-up 2500 iterations; a source with another CT window is refused."""
    pytest.importorskip("nnunetv2")
    from segtrain.nnunet_ext.nnUNetTrainer_segtrain_coronary import nnUNetTrainer_segtrain_coronary
    from segtrain.nnunet_ext.nnUNetTrainer_segtrain_finetune import nnUNetTrainer_segtrain_finetune

    plans, dj = _tiny_plans()
    for k in ("nnUNet_raw", "nnUNet_preprocessed", "nnUNet_results"):
        monkeypatch.setenv(k, str(tmp_path))
    for k in ("SEGTRAIN_EPOCHS", "SEGTRAIN_WARMUP_ITERS", "SEGTRAIN_ITERATIONS"):
        monkeypatch.delenv(k, raising=False)
    ident = plans["configurations"]["3d_fullres"]["data_identifier"]
    data = tmp_path / plans["dataset_name"] / ident
    data.mkdir(parents=True)
    (data / "x.b2nd").write_bytes(b"")
    cpu = torch.device("cpu")

    def build(cls, p):
        p = json.loads(json.dumps(p))
        p["continue_training"] = False
        t = cls(p, "3d_fullres", 0, dj, cpu)
        t.initialize()
        return t

    torch.manual_seed(1)
    master = build(nnUNetTrainer_segtrain_coronary, plans)
    ck = tmp_path / "checkpoint_final.pth"
    torch.save({"network_weights": master.network.state_dict(), "init_args": master.my_init_kwargs,
                "trainer_name": "nnUNetTrainer_segtrain_coronary", "current_epoch": 412}, str(ck))
    monkeypatch.setenv("SEGTRAIN_FINETUNE_FROM", str(ck))
    torch.manual_seed(2)
    ft = build(nnUNetTrainer_segtrain_finetune, plans)
    src, got = master.network.state_dict(), ft.network.state_dict()
    assert any(".seg_layers." in k for k in src)
    assert all(torch.equal(src[k], got[k]) for k in src)
    assert ft._finetune_summary["heads_loaded"] and ft.num_epochs == 250
    d = ft.lr_scheduler.describe()
    assert d["peak_lr"] == 1e-2 and d["warmup_iters"] == 2500 and d["total_iters"] == 250 * 250

    other = json.loads(json.dumps(plans))
    other["foreground_intensity_properties_per_channel"]["0"]["percentile_99_5"] = 719.0
    torch.manual_seed(3)
    with pytest.raises(ValueError, match="refusing"):
        build(nnUNetTrainer_segtrain_finetune, other)
