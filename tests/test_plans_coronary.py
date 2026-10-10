"""The R1 recipe in segtrain.plans and the coronary trainer: fixed CT window, pinned 256^3 / batch
2, explicit
ImageCAS-X splits with sealed refusal (A14), task 712's extras, and the trainer's window check."""

import json

import pytest

from segtrain import plans
from segtrain.config import Config, LabelSet, TaskConfig, load_task


def _plans_file(tmp_path):
    p = tmp_path / "segtrainPlans_coronary4_60G_iso05.json"
    p.write_text(
        json.dumps(
            {
                "foreground_intensity_properties_per_channel": {
                    "0": {
                        "percentile_00_5": -164.0,
                        "percentile_99_5": 640.0,
                        "mean": 105.0,
                        "std": 180.0,
                    }
                },
                "configurations": {
                    "3d_fullres": {
                        "patch_size": [256, 256, 256],
                        "batch_size": 2,
                        "spacing": [0.5, 0.5, 0.5],
                    }
                },
            }
        )
    )
    return p


def test_apply_ct_window_overwrites_the_fingerprint_window(tmp_path):
    p = _plans_file(tmp_path)
    before = plans.apply_ct_window(p, (-300, 1300))
    props = json.loads(p.read_text())["foreground_intensity_properties_per_channel"]["0"]
    assert before["percentile_00_5"] == -164.0
    assert (props["percentile_00_5"], props["percentile_99_5"], props["mean"], props["std"]) == (
        -300,
        1300,
        100,
        400,
    )
    with pytest.raises(ValueError):
        plans.apply_ct_window(p, (1300, -300))


def test_enforce_patch_accepts_the_recipe(tmp_path):
    p = _plans_file(tmp_path)
    before = plans.enforce_patch(p, "3d_fullres", [256, 256, 256], 2, spacing=(0.5, 0.5, 0.5))
    assert before["patch_size"] == [256, 256, 256] and not before["pinned_over_mismatch"]


@pytest.mark.parametrize("field,value", [("patch_size", [192, 256, 256]), ("batch_size", 3),
                                         ("spacing", [0.7, 0.7, 0.7])])
def test_a_replanned_recipe_is_refused_not_pinned(tmp_path, monkeypatch, field, value):
    """A21b: nnU-Net planning on new data may return another patch/batch/spacing; the plan is
    refused (and left untouched), never silently pinned over."""
    monkeypatch.delenv(plans.ALLOW_PIN_ENV, raising=False)
    p = _plans_file(tmp_path)
    d = json.loads(p.read_text())
    d["configurations"]["3d_fullres"][field] = value
    p.write_text(json.dumps(d))
    with pytest.raises(ValueError, match="did not reproduce the recipe"):
        plans.enforce_patch(p, "3d_fullres", [256, 256, 256], 2, spacing=(0.5, 0.5, 0.5))
    assert json.loads(p.read_text()) == d
    task_file = tmp_path / "task.yaml"
    task_file.write_text("ct_window: [-300, 1300]\npatch_size: [256, 256, 256]\nbatch_size: 2\n")
    task = TaskConfig(712, "CoronaryBranches", LabelSet("b", {"x": 1}), (0.5, 0.5, 0.5),
                      source_path=task_file)
    with pytest.raises(ValueError):
        plans.finalize_plans(p, task)
    assert json.loads(p.read_text()) == d             # window not written either


def test_pinning_over_a_mismatch_needs_the_explicit_opt_in(tmp_path, monkeypatch):
    p = _plans_file(tmp_path)
    d = json.loads(p.read_text())
    d["configurations"]["3d_fullres"]["patch_size"] = [192, 256, 256]
    p.write_text(json.dumps(d))
    monkeypatch.setenv(plans.ALLOW_PIN_ENV, "1")
    before = plans.enforce_patch(p, "3d_fullres", [256, 256, 256], 2)
    assert before["pinned_over_mismatch"] and before["patch_size"] == [192, 256, 256]
    assert json.loads(p.read_text())["configurations"]["3d_fullres"]["patch_size"] == [256] * 3


def test_task_712_states_the_master_recipe():
    task = load_task(712)
    ex = plans.task_extras(task)
    assert task.spacing == (0.5, 0.5, 0.5) and task.trainer == "nnUNetTrainer_segtrain_coronary"
    assert task.label_set.names == [
        "left_main",
        "left_anterior_descending",
        "left_circumflex",
        "right_coronary_artery",
    ]
    assert ex["planner"] == "ResEncUNetPlanner" and ex["gpu_memory_target_gb"] == 60
    assert ex["patch_size"] == [256, 256, 256] and ex["batch_size"] == 2
    assert ex["ct_window"] == [-300, 1300] and ex["ignore_label"] is True
    assert ex["sealed_list"] == "trillium/sealed_test.json"


def test_finalize_plans_applies_window_and_patch_and_records_the_planner(tmp_path):
    p = _plans_file(tmp_path)
    task_file = tmp_path / "task.yaml"
    task_file.write_text("ct_window: [-300, 1300]\npatch_size: [256, 256, 256]\nbatch_size: 2\n")
    task = TaskConfig(
        712, "CoronaryBranches", LabelSet("b", {"x": 1}), (0.5, 0.5, 0.5), source_path=task_file
    )
    rec = plans.finalize_plans(p, task)
    assert rec["planned"]["patch_size"] == [256, 256, 256]
    record = json.loads(p.with_suffix(".planner_output.json").read_text())
    assert record["window_before"]["percentile_99_5"] == 640.0
    plans.finalize_plans(p, task)  # idempotent; keeps the first (planner) record
    assert (
        json.loads(p.with_suffix(".planner_output.json").read_text())["window_before"][
            "percentile_99_5"
        ]
        == 640.0
    )


def _cfg(tmp_path):
    return Config(
        zenodo_root=tmp_path,
        nnunet_raw=tmp_path / "raw",
        nnunet_preprocessed=tmp_path / "pre",
        nnunet_results=tmp_path / "res",
        runs_root=tmp_path / "runs",
    )


def test_explicit_splits_refuse_sealed_and_overlap(tmp_path):
    cfg = _cfg(tmp_path)
    task = TaskConfig(712, "CoronaryBranches", LabelSet("b", {"x": 1}), (0.5, 0.5, 0.5))
    out = plans.write_explicit_splits(cfg, task, ["c0001", "c0002"], ["c0003"], sealed={"c0999"})
    assert json.loads(out.read_text()) == [{"train": ["c0001", "c0002"], "val": ["c0003"]}]
    with pytest.raises(ValueError):
        plans.write_explicit_splits(cfg, task, ["c0001"], ["c0001"])
    with pytest.raises(ValueError):
        plans.write_explicit_splits(cfg, task, ["c0001"], ["c0003"], sealed={"c0003"})


def test_trainer_window_check():
    from segtrain.nnunet_ext import ct_window as tr

    good = {
        "foreground_intensity_properties_per_channel": {
            "0": {"percentile_00_5": -300.0, "percentile_99_5": 1300.0}
        }
    }
    bad = {
        "foreground_intensity_properties_per_channel": {
            "0": {"percentile_00_5": -164.0, "percentile_99_5": 640.0}
        }
    }
    tr.check_window(good, tr.CT_WINDOW)
    with pytest.raises(RuntimeError):
        tr.check_window(bad, tr.CT_WINDOW)
    tr.check_window(bad, None)  # SEGTRAIN_CT_WINDOW=off (window ablation)


def test_trainer_window_env(monkeypatch):
    from segtrain.nnunet_ext import ct_window as tr

    monkeypatch.delenv("SEGTRAIN_CT_WINDOW", raising=False)
    assert tr.expected_window() == (-300.0, 1300.0)
    monkeypatch.setenv("SEGTRAIN_CT_WINDOW", "off")
    assert tr.expected_window() is None
    monkeypatch.setenv("SEGTRAIN_CT_WINDOW", "-200,1000")
    assert tr.expected_window() == (-200.0, 1000.0)


def test_trainer_disables_mirroring_and_saves_probabilities(env_has_nnunet):
    """Imports torch + nnU-Net (~40 s), so it runs only with SEGTRAIN_TEST_NNUNET=1, like the repo's
    other
    nnU-Net-dependent tests."""
    if not env_has_nnunet:
        pytest.skip("set SEGTRAIN_TEST_NNUNET=1 to run nnU-Net-dependent tests")
    import unittest.mock as m

    from segtrain.nnunet_ext.nnUNetTrainer_segtrain import nnUNetTrainer_segtrain
    from segtrain.nnunet_ext.nnUNetTrainer_segtrain_coronary import (
        nnUNetTrainer_segtrain_coronary as T,
    )

    seen = {}

    def parent_cfg(self):
        return ("rot", False, [256, 256, 256], (0, 1, 2))

    def parent_val(self, save_probabilities=False):
        seen["save"] = save_probabilities

    f = T.__new__(T)  # no __init__: drive just the two overridden methods
    f._save_probabilities = True
    with (
        m.patch.object(
            nnUNetTrainer_segtrain,
            "configure_rotation_dummyDA_mirroring_and_inital_patch_size",
            parent_cfg,
        ),
        m.patch.object(nnUNetTrainer_segtrain, "perform_actual_validation", parent_val),
    ):
        out = f.configure_rotation_dummyDA_mirroring_and_inital_patch_size()
        assert out[3] is None and f.inference_allowed_mirroring_axes is None
        f.perform_actual_validation()
        assert seen["save"] is True


def test_plan_experiment_uses_the_task_planner_budget_and_finalizes(tmp_path, monkeypatch):
    """plan_experiment passes the task's planner and VRAM budget to nnU-Net, then applies the
    window and the patch."""
    import sys
    import types

    seen = {}
    task_file = tmp_path / "Dataset712_CoronaryBranches.yaml"
    task_file.write_text(
        "planner: ResEncUNetPlanner\ngpu_memory_target_gb: 60\nct_window: [-300, 1300]\n"
        "patch_size: [256, 256, 256]\nbatch_size: 2\n"
    )
    task = TaskConfig(
        712,
        "CoronaryBranches",
        LabelSet("b", {"x": 1}),
        (0.5, 0.5, 0.5),
        plans_name="segtrainPlans_coronary4_60G_iso05",
        source_path=task_file,
    )
    cfg = _cfg(tmp_path)

    def fake_plan(**kw):
        seen.update(kw)
        out = task.preprocessed_dir(cfg) / f"{task.plans_name}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(_plans_file(tmp_path).read_text())

    mod = types.ModuleType("nnunetv2.experiment_planning.plan_and_preprocess_api")
    mod.plan_experiments = fake_plan
    monkeypatch.setitem(sys.modules, "nnunetv2.experiment_planning.plan_and_preprocess_api", mod)
    monkeypatch.setitem(sys.modules, "nnunetv2", types.ModuleType("nnunetv2"))
    monkeypatch.setitem(
        sys.modules,
        "nnunetv2.experiment_planning",
        types.ModuleType("nnunetv2.experiment_planning"),
    )
    pf = plans.plan_experiment(cfg, task)
    assert seen["experiment_planner_class_name"] == "ResEncUNetPlanner"
    assert seen["gpu_memory_target_in_gb"] == 60.0 and seen["overwrite_target_spacing"] == (
        0.5,
        0.5,
        0.5,
    )
    p = json.loads(pf.read_text())
    assert p["configurations"]["3d_fullres"]["patch_size"] == [256, 256, 256]
    assert p["foreground_intensity_properties_per_channel"]["0"]["percentile_99_5"] == 1300
