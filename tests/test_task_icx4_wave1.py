"""Task 716, the wave-1 fine-tune of icx4 on SegQueue14 reads (Round 9 A32, #85).

Pins the task against what it must agree with: the coronary_icx4 label set and SegQueue14's
labels (D25), icx4's own recipe as trillium/icx4 runs it (dataset 715, plans name, 0.5 mm, ResEnc
60 GB, 256^3 / batch 2, mirroring off), the A17 trainer and its LR arms, the A14 sealed list and
the D27 pool-seal hook (#84). Nothing here needs nnU-Net or torch: trainer files and icx4's
scripts are read as source.
"""

import ast
import hashlib
import json
import re
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
import pytest
import yaml

from segtrain import pool_seal, slurm
from segtrain.config import Config, SciNetConfig, list_tasks, load_label_set, load_task
from segtrain.convert import convert_dataset
from segtrain.index import assign_split
from segtrain.plans import (
    adopt_plans,
    adopted_window,
    check_adoptable,
    plan_experiment,
    sealed_pool_file,
    sealed_pool_notice,
    task_extras,
    trainer_for_arm,
)
from segtrain.pool_seal import SealedPoolError, ingest_patient, load_pool_seal
from segtrain.proxy import load_sealed, pool_name, sealed_reason
from segtrain.splits import SPLIT_TRAIN, CaseMeta

REPO = Path(__file__).resolve().parents[1]
_SRC = REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.append(str(_SRC))

from segqueue14 import labels as sq14_labels  # noqa: E402
from segqueue14.plan import pool_case_name  # noqa: E402

TASK_FILE = REPO / "configs" / "tasks" / "Dataset716_CoronaryICX4Wave1.yaml"
ICX4_PREPARE = REPO / "trillium" / "icx4" / "lib" / "prepare.py"
ICX4_TRAINERS = REPO / "trillium" / "icx4" / "lib" / "icx4_trainers.py"
FINETUNE = REPO / "src" / "segtrain" / "nnunet_ext" / "nnUNetTrainer_segtrain_finetune.py"
CORONARY = REPO / "src" / "segtrain" / "nnunet_ext" / "nnUNetTrainer_segtrain_coronary.py"


@pytest.fixture
def task():
    return load_task(716)


@pytest.fixture
def cfg(tmp_path) -> Config:
    return Config(zenodo_root=tmp_path / "export", nnunet_raw=tmp_path / "raw",
                  nnunet_preprocessed=tmp_path / "pre", nnunet_results=tmp_path / "res",
                  runs_root=tmp_path / "runs",
                  scinet=SciNetConfig(account="def-example", venv="/home/x/venv"))


def _icx4_constants() -> dict:
    """DS_ID, DS and PLANS as icx4's prepare.py assigns them, without running it."""
    out = {}
    for node in ast.walk(ast.parse(ICX4_PREPARE.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Assign):
            names = [t for t in node.targets if isinstance(t, (ast.Name, ast.Tuple))]
            for t in names:
                elts = t.elts if isinstance(t, ast.Tuple) else [t]
                vals = node.value.elts if isinstance(node.value, ast.Tuple) else [node.value]
                for n, v in zip(elts, vals):
                    if isinstance(n, ast.Name) and isinstance(v, ast.Constant):
                        out[n.id] = v.value
    return out


def _classes(path: Path) -> dict:
    """{class name: (base names, {class attr: constant})} of a trainer file."""
    out = {}
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.ClassDef):
            attrs = {t.id: s.value.value for s in node.body if isinstance(s, ast.Assign)
                     for t in s.targets if isinstance(t, ast.Name)
                     and isinstance(s.value, ast.Constant)}
            out[node.name] = ([b.id for b in node.bases if isinstance(b, ast.Name)], attrs)
    return out


def _icx4_plans(**conf_overrides) -> dict:
    """A plans dict shaped like icx4's nnUNetResEncUNetPlans_60G_iso05.json."""
    conf = {"data_identifier": "nnUNetResEncUNetPlans_60G_iso05_3d_fullres",
            "spacing": [0.5, 0.5, 0.5], "patch_size": [256, 256, 256], "batch_size": 2,
            "normalization_schemes": ["CTNormalization"],
            "architecture": {"network_class_name":
                             "dynamic_network_architectures.architectures.unet.ResidualEncoderUNet",
                             "arch_kwargs": {"n_stages": 6}}}
    conf.update(conf_overrides)
    return {"dataset_name": "Dataset715_ICX4", "plans_name": "nnUNetResEncUNetPlans_60G_iso05",
            "configurations": {"3d_fullres": conf},
            "foreground_intensity_properties_per_channel":
                {"0": {"percentile_00_5": -169.0, "percentile_99_5": 719.0,
                       "mean": 280.0, "std": 160.0}},
            "transpose_forward": [0, 1, 2], "transpose_backward": [0, 1, 2]}


# ----------------------------------------------------------------- the config loads


def test_the_task_loads_by_id_and_name(task):
    assert TASK_FILE.stem in list_tasks()
    assert task.nnunet_name == "Dataset716_CoronaryICX4Wave1"
    assert load_task("CoronaryICX4Wave1").dataset_id == 716


def test_the_dataset_id_clashes_with_nothing_710_to_715():
    assert load_task(716).dataset_id not in range(710, 716)
    assert _icx4_constants()["DS_ID"] == 715
    ids = [load_task(n).dataset_id for n in list_tasks()]
    assert len(ids) == len(set(ids))


# ----------------------------------------------------------------- the labels (D25)


def test_labels_match_coronary_icx4_yaml(task):
    raw = yaml.safe_load((REPO / "configs" / "labels" / "coronary_icx4.yaml").read_text())
    assert task.label_set.name == "coronary_icx4"
    assert task.label_set.labels == raw["labels"] == {"LM": 1, "LAD": 2, "LCx": 3, "RCA": 4}
    assert task.label_set.labels == load_label_set("coronary_icx4").labels


def test_labels_match_segqueue14(task):
    assert sq14_labels.LABEL_SET_NAME == task.label_set.name
    assert task.label_set.names == list(sq14_labels.NAMES)
    assert task.label_set.labels == dict(sq14_labels.LABEL_VALUES)
    assert task.label_set.n_classes == sq14_labels.N_CLASSES


def test_no_ignore_label_and_no_fixed_window(task):
    # A11' read samples carry no ignore value; icx4 trained on nnU-Net's own window.
    extras = task_extras(task)
    assert not extras.get("ignore_label")
    assert "ct_window" not in extras


# ----------------------------------------------------------------- icx4's plan


def test_the_recipe_is_icx4s(task):
    icx4 = _icx4_constants()
    prepare = ICX4_PREPARE.read_text(encoding="utf-8")
    extras = task_extras(task)
    assert task.plans_name == icx4["PLANS"] == "nnUNetResEncUNetPlans_60G_iso05"
    assert extras["plans_from"] == {"dataset": icx4["DS"], "plans_name": icx4["PLANS"],
                                    "trainer": "nnUNetTrainerICX4"}
    assert task.configuration == "3d_fullres"
    assert task.spacing == (0.5, 0.5, 0.5) and task.max_spacing_mm == 0.5
    assert "'-overwrite_target_spacing', '0.5', '0.5', '0.5'" in prepare
    assert extras["planner"] == "ResEncUNetPlanner" and "'ResEncUNetPlanner'" in prepare
    assert extras["gpu_memory_target_gb"] == 60 and "'-gpu_memory_target', '60'" in prepare
    assert extras["patch_size"] == [256, 256, 256] and extras["batch_size"] == 2
    assert "c3['patch_size'] = [256, 256, 256]; c3['batch_size'] = 2" in prepare


def test_mirroring_is_off_in_icx4_and_in_the_fine_tune():
    assert "nnUNetTrainerNoMirroring" in ICX4_TRAINERS.read_text(encoding="utf-8")
    coronary = CORONARY.read_text(encoding="utf-8")
    assert "self.inference_allowed_mirroring_axes = None" in coronary
    bases = _classes(FINETUNE)["nnUNetTrainer_segtrain_finetune"][0]
    assert "nnUNetTrainer_segtrain_coronary" in bases


def test_an_icx4_shaped_plans_file_is_adoptable(task):
    assert check_adoptable(_icx4_plans(), task) == []


@pytest.mark.parametrize("override, word", [
    ({"patch_size": [192, 192, 192]}, "patch"),
    ({"batch_size": 1}, "batch"),
    ({"spacing": [0.7, 0.7, 0.7]}, "spacing"),
    ({"architecture": {"network_class_name": "PlainConvUNet"}}, "ResEnc"),
])
def test_a_plans_file_off_the_recipe_is_refused(task, cfg, tmp_path, override, word):
    src = tmp_path / "plans.json"
    src.write_text(json.dumps(_icx4_plans(**override)))
    assert any(word in p for p in check_adoptable(_icx4_plans(**override), task))
    with pytest.raises(ValueError, match=word):
        adopt_plans(cfg, task, src)


def test_adopt_copies_icx4s_plans_verbatim_but_the_dataset_name(task, cfg, tmp_path):
    src = tmp_path / "nnUNetResEncUNetPlans_60G_iso05.json"
    src.write_text(json.dumps(_icx4_plans(), indent=1))
    raw = task.raw_dir(cfg)
    raw.mkdir(parents=True)
    (raw / "dataset.json").write_text('{"labels": {"background": 0}}')

    out = adopt_plans(cfg, task, src)

    assert out == task.preprocessed_dir(cfg) / "nnUNetResEncUNetPlans_60G_iso05.json"
    got, want = json.loads(out.read_text()), _icx4_plans()
    assert got.pop("dataset_name") == "Dataset716_CoronaryICX4Wave1"
    want.pop("dataset_name")
    assert got == want
    record = json.loads(out.with_name(out.stem + ".adopted_from.json").read_text())
    assert record["source_sha256"] == hashlib.sha256(src.read_bytes()).hexdigest()
    assert record["source_dataset"] == "Dataset715_ICX4"
    assert (task.preprocessed_dir(cfg) / "dataset.json").is_file()
    # the trainer's window check follows the adopted window, not the fixed one
    assert adopted_window(cfg, task) == (-169.0, 719.0)


def test_adopt_refuses_another_datasets_plans(task, cfg, tmp_path):
    plans = _icx4_plans()
    plans["dataset_name"] = "Dataset712_CoronaryBranches"
    src = tmp_path / "p.json"
    src.write_text(json.dumps(plans))
    with pytest.raises(ValueError, match="Dataset712"):
        adopt_plans(cfg, task, src)


def test_the_task_is_never_replanned(task, cfg):
    with pytest.raises(RuntimeError, match="--plans-from"):
        plan_experiment(cfg, task)


def test_tasks_without_plans_from_cannot_adopt(cfg, tmp_path):
    src = tmp_path / "p.json"
    src.write_text(json.dumps(_icx4_plans()))
    with pytest.raises(ValueError, match="plans_from"):
        adopt_plans(cfg, load_task(712), src)


# ----------------------------------------------------------------- the A17 trainer and arms


def test_the_trainer_is_the_a17_fine_tune_with_both_lr_arms(task):
    classes = _classes(FINETUNE)
    arms = task_extras(task)["lr_arms"]
    assert task.trainer == arms["primary"] == "nnUNetTrainer_segtrain_finetune"
    assert classes[arms["primary"]][1]["PEAK_LR"] == 1e-2
    assert classes[arms["lr1e3"]][1]["PEAK_LR"] == 1e-3
    assert arms["lr1e3"] == "nnUNetTrainer_segtrain_finetune_lr1e3"
    m = re.search(r"^FINETUNE_EPOCHS = (\d+)$", FINETUNE.read_text(encoding="utf-8"), re.M)
    assert task.epochs == int(m.group(1))


def test_trainer_for_arm(task):
    assert trainer_for_arm(task) == trainer_for_arm(task, "primary") == task.trainer
    assert trainer_for_arm(task, "lr1e3") == "nnUNetTrainer_segtrain_finetune_lr1e3"
    with pytest.raises(ValueError, match="lr1e3"):
        trainer_for_arm(task, "lr5e3")
    assert trainer_for_arm(load_task(712)) == "nnUNetTrainer_segtrain_coronary"


# ----------------------------------------------------------------- A14 and the D27 pool seal


def test_the_imagecas_seal_is_in_force(task):
    assert task_extras(task)["sealed_list"] == "trillium/sealed_test.json"
    sealed = load_sealed(REPO / "trillium" / "sealed_test.json")
    some = sorted(sealed)[0]
    assert sealed_reason(some, sealed) is not None
    assert sealed_reason(f"{some}__r2", sealed) is not None


# A non-sealed pool volume, a sealed one, and an UNLISTED volume of a sealed patient.
def _pool_names():
    seal = load_pool_seal()
    listed = [n.split("#", 1)[0].strip() for n in
              (REPO / "configs" / "segqueue14" / "pool-2026-10.txt").read_text().splitlines()]
    open_stem = next(pool_case_name(n) for n in listed
                     if n and pool_name(pool_case_name(n)) and not seal.is_sealed(n))
    sealed_stem = sorted(v for v in seal.volumes if pool_name(v))[0]
    unlisted = next(f"{p}_tp9" for p in sorted(seal.patients - seal.report_only_patients)
                    if pool_name(p) and f"{p}_tp9" not in seal.volumes)
    return open_stem, sealed_stem, unlisted


def test_the_task_is_held_to_the_pinned_pool_seal(task):
    assert task_extras(task)["sealed_pool_list"] == pool_seal.SEAL_RELPATH
    assert sealed_pool_file(task) == REPO / pool_seal.SEAL_RELPATH
    assert task_extras(task)["pool_reads"] is True
    assert "HOOK" not in TASK_FILE.read_text(encoding="utf-8")
    note = sealed_pool_notice(task)
    assert pool_seal.SEAL_SHA256[:12] in note and "enforced" in note
    assert sealed_pool_file(load_task(712)) is None


def test_the_guard_refuses_by_patient():
    seal = load_pool_seal()
    open_stem, sealed_stem, unlisted = _pool_names()
    assert seal.reason(open_stem) is None
    assert seal.reason(sealed_stem) and seal.reason(f"{sealed_stem}__r2")
    assert unlisted not in seal.volumes and seal.reason(unlisted)


def test_a14_judges_imagecas_names_and_leaves_pool_names_to_d27():
    sealed = load_sealed(REPO / "trillium" / "sealed_test.json")
    open_stem, _, _ = _pool_names()
    assert sealed_reason(open_stem, sealed, allow_pool=True) is None
    assert sealed_reason(f"{open_stem}__r2", sealed, allow_pool=True) is None
    assert sealed_reason(open_stem, sealed) is not None            # every other task, as before
    for name in ("ImageCAS__0003", "asoca_7", sorted(sealed)[0]):
        assert sealed_reason(name, sealed, allow_pool=True) is not None, name


def _export(root, names, shape=(12, 10, 8)):
    """A tiny SegQueue14-export-shaped tree: <case>/ct.nii.gz + <case>/labels.nii.gz."""
    for i, name in enumerate(names):
        folder = root / name
        folder.mkdir(parents=True)
        lab = np.zeros(shape, dtype=np.uint8)
        lab[2:5, 2:5, 2:4] = 1 + i % 4
        nib.save(nib.Nifti1Image(np.zeros(shape, dtype=np.int16), np.eye(4)),
                 str(folder / "ct.nii.gz"))
        nib.save(nib.Nifti1Image(lab, np.eye(4)), str(folder / "labels.nii.gz"))


def _convert_716(tmp_path, names, **kw):
    root = tmp_path / "export"
    _export(root, names)
    rows = [CaseMeta(case_id=n, split=SPLIT_TRAIN, study_type="ccta") for n in names]
    cfg = Config(zenodo_root=root, nnunet_raw=tmp_path / "raw",
                 nnunet_preprocessed=tmp_path / "pre", nnunet_results=tmp_path / "res",
                 runs_root=tmp_path / "runs", link_mode="copy", convert_workers=1)
    task = load_task(716)
    return convert_dataset(cfg, task, rows, **kw), task.raw_dir(cfg)


def test_convert_takes_an_open_pool_read_and_both_its_reads(tmp_path):
    open_stem, _, _ = _pool_names()
    names = [open_stem, f"{open_stem}__r2", "imagecas_0010"]
    report, raw = _convert_716(tmp_path, names)
    assert report.ok, report.render()
    assert report.n_train == 3 and report.n_excluded == 0 and report.n_pool_sealed == 0
    for n in names:
        assert (raw / "labelsTr" / f"{n}.nii.gz").is_file(), n


@pytest.mark.parametrize("which", ["sealed", "unlisted"])
def test_convert_refuses_a_sealed_pool_read(tmp_path, which):
    open_stem, sealed_stem, unlisted = _pool_names()
    bad = {"sealed": f"{sealed_stem}__r2", "unlisted": unlisted}[which]
    with pytest.raises(SealedPoolError):
        _convert_716(tmp_path, [open_stem, bad])
    assert not (tmp_path / "raw").exists()


def test_convert_exclude_mode_drops_and_counts_them(tmp_path):
    open_stem, sealed_stem, unlisted = _pool_names()
    report, raw = _convert_716(tmp_path, [open_stem, sealed_stem, unlisted],
                               pool_seal="exclude")
    assert report.n_train == 1 and report.n_pool_sealed == 2
    assert [p.name for p in (raw / "labelsTr").iterdir()] == [f"{open_stem}.nii.gz"]


def test_the_trainer_guard_takes_open_pool_reads_and_refuses_sealed_ones(monkeypatch):
    from segtrain.nnunet_ext.sealed_guard import POOL_READS_ENV, refuse_sealed

    open_stem, sealed_stem, unlisted = _pool_names()
    monkeypatch.setenv(POOL_READS_ENV, "1")
    assert refuse_sealed([open_stem, f"{open_stem}__r2", "c0010"]) == 3
    for bad in (sealed_stem, unlisted):
        with pytest.raises(SealedPoolError):
            refuse_sealed([open_stem, bad])
    monkeypatch.delenv(POOL_READS_ENV)
    with pytest.raises(RuntimeError, match="A14"):        # without the task's flag, as before
        refuse_sealed([open_stem])


def test_a_patients_volumes_share_a_split():
    seal = load_pool_seal()
    multi = sorted(seal.volumes)
    by_patient = {}
    for v in multi:
        by_patient.setdefault(ingest_patient(v), []).append(v)
    vols = next(vs for vs in by_patient.values() if len(vs) > 1)
    for seed in range(20):
        assert len({assign_split(v, 0.3, 0.3, seed) for v in vols}) == 1, vols


# ----------------------------------------------------------------- the CLI


def _roots(tmp_path):
    return ["--zenodo-root", str(tmp_path / "export"), "--nnunet-raw", str(tmp_path / "raw"),
            "--nnunet-preprocessed", str(tmp_path / "pre"),
            "--nnunet-results", str(tmp_path / "res"), "--runs-root", str(tmp_path / "runs")]


def test_train_refuses_a_fresh_fine_tune_without_its_source(tmp_path, capsys):
    from segtrain.cli import main

    assert main(["train", "--task", "716", "--dry-run", *_roots(tmp_path)]) == 2
    assert "--finetune-from" in capsys.readouterr().err


def test_train_sets_the_source_the_arm_and_the_adopted_window(tmp_path, capsys, monkeypatch):
    from segtrain.cli import main

    monkeypatch.delenv("SEGTRAIN_CT_WINDOW", raising=False)
    monkeypatch.delenv("SEGTRAIN_POOL_SEAL", raising=False)
    pre = tmp_path / "pre" / "Dataset716_CoronaryICX4Wave1"
    pre.mkdir(parents=True)
    (pre / "nnUNetResEncUNetPlans_60G_iso05.json").write_text(json.dumps(_icx4_plans()))
    ckpt = tmp_path / "checkpoint_final.pth"
    ckpt.write_bytes(b"x")

    rc = main(["train", "--task", "716", "--arm", "lr1e3", "--finetune-from", str(ckpt),
               "--dry-run", *_roots(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "-tr nnUNetTrainer_segtrain_finetune_lr1e3" in out
    assert "-p nnUNetResEncUNetPlans_60G_iso05" in out
    assert f"SEGTRAIN_FINETUNE_FROM={ckpt}" in out
    assert "SEGTRAIN_CT_WINDOW=-169,719" in out
    assert "D27 pool seal: sealed-pool-2026-10.json" in out and "enforced" in out
    assert f"SEGTRAIN_POOL_SEAL={REPO / pool_seal.SEAL_RELPATH}" in out
    assert "SEGTRAIN_POOL_READS=1" in out


def test_plan_without_plans_from_is_refused_for_716(tmp_path, capsys):
    from segtrain.cli import main

    export = tmp_path / "export"
    export.mkdir()
    (export / "meta.csv").write_text("image_id,split\n")
    assert main(["plan", "--task", "716", *_roots(tmp_path)]) == 2
    assert "--plans-from" in capsys.readouterr().err


def test_the_chain_script_carries_the_arm_and_the_source(task, cfg):
    script = slurm.render_train_script(
        cfg, task, 0, trainer=trainer_for_arm(task, "lr1e3"),
        train_extra=["--arm", "lr1e3", "--finetune-from", "/s/icx4/checkpoint_final.pth"])
    assert "--arm lr1e3 --finetune-from /s/icx4/checkpoint_final.pth" in script
    assert "nnUNetTrainer_segtrain_finetune_lr1e3__nnUNetResEncUNetPlans_60G_iso05" in script
