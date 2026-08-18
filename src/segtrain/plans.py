"""nnU-Net fingerprinting, planning and preprocessing, driven from our task configs.

nnU-Net self-configures everything from the dataset -- patch size, batch size,
network depth, normalization -- which is precisely what the reference paper
relies on ("hyperparameter optimization was not performed"). The only thing we
ever override is the **target spacing**, and the coronary task does not even do
that.

Both choices are deliberate. A task with an explicit ``spacing`` forces it,
which is how the phase 2 regional models pin themselves to 1.5 mm. The coronary
task sets ``spacing: native`` instead and lets nnU-Net's median-spacing rule
decide, because that rule already computes the finest target the data supports --
exactly what a high-resolution vessel model wants. What native cannot protect
against is the median itself moving: a few thick-slice studies in an otherwise
fine CCTA set drag the target coarse and interpolate the thinnest vessels away.
``max_spacing_mm`` and ``spacing_warnings`` below exist for that.

Everything else -- loss (Dice + cross-entropy), deep supervision, SGD with
momentum 0.99, polynomial LR decay from 0.01, 1000 epochs of 250 iterations --
is left at nnU-Net's defaults on purpose.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from .config import Config, TaskConfig
from .splits import SPLIT_TEST, build_splits, read_meta, select, validate_splits, write_splits_final


def configure_nnunet_env(cfg: Config) -> None:
    """Publish our paths into the environment nnU-Net reads.

    Must run before any ``nnunetv2`` import in this process, and is also applied
    to subprocess environments. Keeping this in one place means the user never
    maintains nnU-Net's three environment variables by hand.
    """
    os.environ["nnUNet_raw"] = str(cfg.nnunet_raw)
    os.environ["nnUNet_preprocessed"] = str(cfg.nnunet_preprocessed)
    os.environ["nnUNet_results"] = str(cfg.nnunet_results)
    os.environ.setdefault("nnUNet_extTrainer", str(ext_trainer_dir()))
    for p in (cfg.nnunet_raw, cfg.nnunet_preprocessed, cfg.nnunet_results, cfg.runs_root):
        Path(p).mkdir(parents=True, exist_ok=True)


def ext_trainer_dir() -> Path:
    """Directory holding our custom trainer, for nnU-Net's external-trainer lookup.

    nnU-Net only searches its own package for trainer classes unless
    ``nnUNet_extTrainer`` points elsewhere. It imports modules found there as
    top-level modules, which is why the trainer file uses absolute imports.
    """
    return Path(__file__).resolve().parent / "nnunet_ext"


def extract_fingerprint(
    cfg: Config,
    task: TaskConfig,
    num_processes: Optional[int] = None,
    check_integrity: bool = False,
    clean: bool = True,
) -> None:
    """Scan the raw dataset for shapes, spacings and intensity statistics."""
    configure_nnunet_env(cfg)
    from nnunetv2.experiment_planning.plan_and_preprocess_api import extract_fingerprints

    extract_fingerprints(
        dataset_ids=[task.dataset_id],
        num_processes=num_processes or min(8, cfg.n_workers()),
        # Integrity checking re-reads and re-validates every image/label pair.
        # Worth doing once per dataset; too slow to leave on by default.
        check_dataset_integrity=check_integrity,
        clean=clean,
        verbose=False,
    )


def plan_experiment(
    cfg: Config,
    task: TaskConfig,
    gpu_memory_target_gb: Optional[float] = None,
) -> Path:
    """Generate the plans file, forcing this task's target spacing.

    ``gpu_memory_target_gb`` sets the VRAM budget nnU-Net sizes patches and
    batches against. Leave it unset to use nnU-Net's 8 GB default, which keeps
    plans portable; raise it only if you know the training GPU and want larger
    patches. Note it changes the architecture, so plans made for one budget are
    not interchangeable with checkpoints trained under another.
    """
    configure_nnunet_env(cfg)
    from nnunetv2.experiment_planning.plan_and_preprocess_api import plan_experiments

    kwargs = dict(
        dataset_ids=[task.dataset_id],
        overwrite_plans_name=task.plans_name,
    )
    # spacing None means native: leave nnU-Net's median-spacing rule alone. It
    # already computes the finest target the data supports, which is exactly what
    # a high-resolution task wants -- overriding it with a guess would resample
    # the data for no reason, and resampling a 1.5 mm-wide distal vessel is not
    # a free operation.
    if task.spacing is not None:
        kwargs["overwrite_target_spacing"] = tuple(float(s) for s in task.spacing)
    if gpu_memory_target_gb is not None:
        kwargs["gpu_memory_target_in_gb"] = float(gpu_memory_target_gb)

    plan_experiments(**kwargs)

    plans_file = task.preprocessed_dir(cfg) / f"{task.plans_name}.json"
    if not plans_file.is_file():
        raise RuntimeError(f"planning did not produce {plans_file}")
    return plans_file


def available_cases(cfg: Config, task: TaskConfig) -> set:
    """Case ids actually converted into imagesTr."""
    images = task.raw_dir(cfg) / "imagesTr"
    if not images.is_dir():
        return set()
    return {p.name[: -len("_0000.nii.gz")] for p in images.glob("*_0000.nii.gz")}


def write_splits(
    cfg: Config,
    task: TaskConfig,
    scheme: str = "official",
    n_folds: int = 5,
    seed: int = 12345,
    restrict_to_available: bool = True,
) -> Path:
    """Write splits_final.json so nnU-Net uses our split, not a random one.

    Without this file nnU-Net invents its own 5-fold split over whatever is in
    imagesTr. The 89 test cases are never in imagesTr, so they stay safe either
    way -- but the published train/val boundary would be lost, and the numbers
    would stop being comparable to the paper.

    Splits are intersected with the cases actually converted. A split naming a
    case that is not on disk makes nnU-Net fail partway through the first epoch,
    which is a confusing way to discover you converted a subset -- and running on
    a subset is normal during smoke tests and debugging.
    """
    rows = read_meta(cfg.meta_csv)
    splits = build_splits(rows, scheme=scheme, n_folds=n_folds, seed=seed)
    validate_splits(splits, select(rows, SPLIT_TEST))

    if restrict_to_available:
        present = available_cases(cfg, task)
        if present:
            trimmed = []
            for fold in splits:
                trimmed.append(
                    {
                        "train": [c for c in fold["train"] if c in present],
                        "val": [c for c in fold["val"] if c in present],
                    }
                )
            dropped = sum(
                len(a["train"]) + len(a["val"]) - len(b["train"]) - len(b["val"])
                for a, b in zip(splits, trimmed)
            )
            if dropped:
                print(
                    f"note: {dropped} split entries refer to cases not present in imagesTr "
                    f"and were dropped (subset conversion)"
                )
            empty = [i for i, f in enumerate(trimmed) if not f["val"] or not f["train"]]
            if empty:
                raise RuntimeError(
                    f"after restricting to converted cases, fold(s) {empty} have an empty "
                    "train or val set. Convert more cases, or use --scheme cv5 so the "
                    "validation cases come from the same subset."
                )
            splits = trimmed

    out_dir = task.preprocessed_dir(cfg)
    out_dir.mkdir(parents=True, exist_ok=True)
    return write_splits_final(out_dir / "splits_final.json", splits)


def preprocess(
    cfg: Config,
    task: TaskConfig,
    num_processes: Optional[int] = None,
    verbose: bool = False,
) -> None:
    """Resample, normalize and cache the dataset for training.

    Only the task's own configuration is preprocessed. nnU-Net's default is to
    build 2d, 3d_fullres and 3d_lowres; for this dataset that would triple the
    disk cost -- tens of gigabytes per task -- for two configurations we never
    train.
    """
    configure_nnunet_env(cfg)
    from nnunetv2.experiment_planning.plan_and_preprocess_api import preprocess_dataset

    n = num_processes or max(1, min(8, cfg.n_workers() // 2))
    preprocess_dataset(
        dataset_id=task.dataset_id,
        plans_identifier=task.plans_name,
        configurations=[task.configuration],
        num_processes=[n],
        verbose=verbose,
    )


def describe_plans(cfg: Config, task: TaskConfig) -> str:
    """Human-readable summary of what nnU-Net decided.

    Worth reading before committing GPU-days: patch size and batch size are the
    two numbers that determine whether the run fits in VRAM and how long it takes.
    """
    import json

    plans_file = task.preprocessed_dir(cfg) / f"{task.plans_name}.json"
    if not plans_file.is_file():
        return f"no plans at {plans_file} -- run `segtrain plan` first"

    with open(plans_file, encoding="utf-8") as fh:
        plans = json.load(fh)

    conf = (plans.get("configurations") or {}).get(task.configuration)
    if conf is None:
        return f"plans exist but have no '{task.configuration}' configuration"

    arch = conf.get("architecture", {})
    arch_kwargs = arch.get("arch_kwargs", {})
    lines = [
        f"{task.nnunet_name}  [{task.plans_name} / {task.configuration}]",
        f"  classes          {task.label_set.n_classes} + background",
        f"  target spacing   {conf.get('spacing')}",
        f"  patch size       {conf.get('patch_size')}",
        f"  batch size       {conf.get('batch_size')}",
        f"  stages           {arch_kwargs.get('n_stages')}",
        f"  features         {arch_kwargs.get('features_per_stage')}",
        f"  normalization    {conf.get('normalization_schemes')}",
        f"  preprocessed to  {task.preprocessed_dir(cfg)}",
    ]
    median = plans.get("original_median_spacing_after_transp")
    if median:
        override = "not overridden (native)" if task.spacing is None else (
            f"overridden to {list(task.spacing)}")
        lines.append(f"  source spacing   {median}  ({override})")

    for warning in spacing_warnings(task, conf.get("spacing")):
        lines.append(f"  WARNING          {warning}")
    return "\n".join(lines)


def spacing_warnings(task: TaskConfig, planned) -> list[str]:
    """Flag a planned target spacing too coarse for this task's structures.

    Exists because `spacing: native` delegates the choice to nnU-Net, which picks
    the dataset *median*. That is right for a homogeneous CCTA set and wrong the
    moment a handful of thick-slice studies are mixed in: the median moves, every
    volume is resampled toward it, and the thinnest vessels are interpolated out
    of existence before training ever starts.

    Nothing fails at that point. Preprocessing succeeds, training runs, and the
    model simply never learns the distal branches -- which reads as a modelling
    problem rather than the data problem it is. Hence a warning at plan time,
    when it is still cheap to fix.
    """
    if task.max_spacing_mm is None or not planned:
        return []
    try:
        worst = max(float(s) for s in planned)
    except (TypeError, ValueError):
        return []
    if worst <= task.max_spacing_mm:
        return []
    return [
        f"planned target spacing {list(planned)} is coarser than this task's "
        f"limit of {task.max_spacing_mm} mm.\n"
        "                   nnU-Net picks the median spacing of the dataset, so "
        "this usually means some\n"
        "                   cases are thick-slice. Either drop them, or set an "
        "explicit `spacing:` in\n"
        "                   the task file to stop the median deciding for you."
    ]
