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

import json
import os
from pathlib import Path
from typing import Optional

from .config import Config, TaskConfig, _read_yaml
from .splits import SPLIT_TEST, build_splits, read_meta, select, validate_splits, write_splits_final

# Keys a task YAML may carry beyond what TaskConfig models. Read here, by the module that acts on
# them, so the 4-class R1 task (Dataset712_CoronaryBranches) can state its recipe in one file:
#   planner               nnU-Net experiment planner class (e.g. ResEncUNetPlanner)
#   gpu_memory_target_gb  VRAM budget the planner sizes against (60 for the 256^3 patch)
#   ct_window             [low, high] HU written over the fingerprint percentiles (fixed window)
#   ct_norm               [mean, std] used with ct_window (z-scoring only rescales)
#   patch_size            enforced after planning, [z, y, x]
#   batch_size            enforced after planning
#   ignore_label          true -> labels may carry n_classes+1 = nnU-Net "ignore" (A4 / A11)
#   sealed_list           repo-relative path of the A14 sealed-test JSON; never converted
TASK_EXTRA_KEYS = (
    "planner", "gpu_memory_target_gb", "ct_window", "ct_norm", "patch_size", "batch_size",
    "ignore_label", "sealed_list", "explicit_split", "save_test_probabilities",
)

#: Sidecar beside splits_final.json recording that the split came from explicit lists (ImageCAS-X
#: train/val), so a later ``segtrain plan`` never silently replaces it with the hash split (D13).
EXPLICIT_SPLIT_RECORD = "splits_final.source.json"
#: Where an explicit-split task finds the ImageCAS-X filelists when no directory is passed.
ICX_DIR_ENV = "SEGTRAIN_ICX_DIR"


def task_extras(task: TaskConfig) -> dict:
    """The task file's extra recipe keys (see TASK_EXTRA_KEYS); empty for tasks that set none."""
    if task.source_path is None or not Path(task.source_path).is_file():
        return {}
    data = _read_yaml(Path(task.source_path))
    return {k: data[k] for k in TASK_EXTRA_KEYS if data.get(k) is not None}


def apply_ct_window(plans_file: Path, window, norm=(100.0, 400.0)) -> dict:
    """Write a fixed CT window over nnU-Net's fingerprint-derived one, in a plans file.

    nnU-Net's ``CTNormalization`` clips to the 0.5/99.5 percentiles of *labelled* voxels. With
    coronary labels that is ~[65, 688] HU on an expert lumen and ~[-164, 640] HU on the ImageCAS
    masks: it flattens epicardial fat and maps calcified plaque onto the intensity of bright lumen
    (vault: "Atlas - nnU-Net's automatic CT window on lumen labels flattens 38 percent of the heart
    box"). The master plan fixes [-300, 1300] HU. Returns the previous values so the caller can
    log what was replaced. Must run before preprocessing."""
    import json

    plans_file = Path(plans_file)
    plans = json.loads(plans_file.read_text(encoding="utf-8"))
    props = plans["foreground_intensity_properties_per_channel"]["0"]
    before = {k: props.get(k) for k in ("percentile_00_5", "percentile_99_5", "mean", "std")}
    lo, hi = (float(window[0]), float(window[1]))
    if not lo < hi:
        raise ValueError(f"ct_window must be [low, high] with low < high, got {window}")
    props.update(percentile_00_5=lo, percentile_99_5=hi, mean=float(norm[0]), std=float(norm[1]))
    plans_file.write_text(json.dumps(plans, indent=1), encoding="utf-8")
    return before


#: Opt-in for smoke tests on a case subset, whose planner output may differ from the cohort's.
ALLOW_PIN_ENV = "SEGTRAIN_ALLOW_PATCH_PIN"


def enforce_patch(plans_file: Path, configuration: str, patch_size=None, batch_size=None,
                  spacing=None, allow_pin: Optional[bool] = None) -> dict:
    """Check that the planner produced the recipe's patch, batch and spacing; refuse otherwise.

    The architecture nnU-Net plans (stages, strides, pooling) is derived from the patch it chose.
    Overwriting only ``patch_size`` would silently train a network planned for another patch, and
    a re-plan on new data (another median shape, another fingerprint) could change all three
    without anyone noticing (Round 6, A21b). So a mismatch **raises**, naming what the planner
    returned. ``allow_pin=True`` (or ``SEGTRAIN_ALLOW_PATCH_PIN=1``) pins instead, for smoke tests
    on a subset only, and the record says so. Returns the planner's own values."""
    import json

    plans_file = Path(plans_file)
    plans = json.loads(plans_file.read_text(encoding="utf-8"))
    conf = plans["configurations"][configuration]
    before = {"patch_size": conf.get("patch_size"), "batch_size": conf.get("batch_size"),
              "spacing": conf.get("spacing")}
    wrong = []
    planned_patch = list(conf.get("patch_size") or [])
    if patch_size is not None and planned_patch != [int(x) for x in patch_size]:
        wrong.append(f"patch {conf.get('patch_size')} (recipe {list(patch_size)})")
    if batch_size is not None and conf.get("batch_size") != int(batch_size):
        wrong.append(f"batch {conf.get('batch_size')} (recipe {batch_size})")
    if spacing is not None and [float(x) for x in conf.get("spacing") or []] != \
            [float(x) for x in spacing]:
        wrong.append(f"spacing {conf.get('spacing')} (recipe {list(spacing)})")
    if allow_pin is None:
        allow_pin = os.environ.get(ALLOW_PIN_ENV) == "1"
    if wrong and not allow_pin:
        raise ValueError(f"the planner did not reproduce the recipe for {configuration}: "
                         + "; ".join(wrong) + f". Refusing to pin over it ({plans_file}); the "
                         f"architecture was planned for these values. Set {ALLOW_PIN_ENV}=1 only "
                         "for a smoke test on a case subset.")
    before["pinned_over_mismatch"] = bool(wrong)
    if patch_size is not None:
        conf["patch_size"] = [int(x) for x in patch_size]
    if batch_size is not None:
        conf["batch_size"] = int(batch_size)
    plans_file.write_text(json.dumps(plans, indent=1), encoding="utf-8")
    return before


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
    planner: Optional[str] = None,
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

    extras = task_extras(task)
    kwargs = dict(
        dataset_ids=[task.dataset_id],
        overwrite_plans_name=task.plans_name,
    )
    planner = planner or extras.get("planner")
    if planner:
        kwargs["experiment_planner_class_name"] = str(planner)
    if gpu_memory_target_gb is None and extras.get("gpu_memory_target_gb") is not None:
        gpu_memory_target_gb = float(extras["gpu_memory_target_gb"])
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
    finalize_plans(plans_file, task)
    return plans_file


def finalize_plans(plans_file: Path, task: TaskConfig) -> dict:
    """Apply the task's post-planning recipe keys (fixed CT window, pinned patch/batch).

    Records what the planner itself chose in ``<plans>.planner_output.json`` beside the plans file.
    Idempotent."""
    import json

    extras = task_extras(task)
    record: dict = {}
    # The planner check comes first: a refused plan is left exactly as nnU-Net wrote it (A21b).
    if extras.get("patch_size") is not None or extras.get("batch_size") is not None:
        record["planned"] = enforce_patch(plans_file, task.configuration, extras.get("patch_size"),
                                          extras.get("batch_size"), spacing=task.spacing)
        record["enforced"] = {"patch_size": extras.get("patch_size"),
                              "batch_size": extras.get("batch_size")}
    if extras.get("ct_window") is not None:
        record["window_before"] = apply_ct_window(plans_file, extras["ct_window"],
                                                  extras.get("ct_norm", (100.0, 400.0)))
        record["window_after"] = list(extras["ct_window"])
    if record:
        out = Path(plans_file).with_suffix(".planner_output.json")
        # keep the first record: re-finalizing must not overwrite the planner's own values
        if not out.exists():
            out.write_text(json.dumps(record, indent=1), encoding="utf-8")
    return record


def write_explicit_splits(cfg: Config, task: TaskConfig, train: list, val: list,
                          sealed: Optional[set] = None) -> Path:
    """Write a one-fold splits_final.json from explicit case lists.

    R1 uses ImageCAS-X train -> train and ImageCAS-X val -> val. Refuses any sealed case (A14) and
    any overlap between train and val."""
    from .proxy import canonical_case, sealed_reason

    train = [canonical_case(c) or c for c in train]
    val = [canonical_case(c) or c for c in val]
    overlap = sorted(set(train) & set(val))
    if overlap:
        raise ValueError(f"{len(overlap)} case(s) in both train and val, e.g. {overlap[:3]}")
    if sealed:
        leaked = sorted((set(train) | set(val)) & set(sealed))
        if leaked:
            raise ValueError(f"{len(leaked)} sealed case(s) in the split, e.g. {leaked[:3]}; "
                             "refusing (A14)")
    # Every converted identifier joins the split of the case behind it, so both reads of a case
    # (<case>__r2, A11') and SegQueue names (imagecas_NNNN) are trained, and kept together (D2).
    present = available_cases(cfg, task)
    by_case: dict = {}
    for ident in present:
        by_case.setdefault(canonical_case(ident) or ident, []).append(ident)
    if sealed:
        bad = sorted(i for i in present if sealed_reason(i, set(sealed)))
        if bad:
            raise ValueError(f"{len(bad)} converted identifier(s) are sealed or unmappable, e.g. "
                             f"{bad[:3]}; refusing (A14)")
    in_test = available_cases(cfg, task, "imagesTs")
    if present or in_test:
        wrong = sorted(c for c in train + val if c not in by_case and c in
                       {canonical_case(i) or i for i in in_test})
        if wrong:
            raise RuntimeError(
                f"{len(wrong)} listed case(s) were converted into imagesTs, not imagesTr, e.g. "
                f"{wrong[:3]}: the index gave them split 'test'. Re-index with --val-fraction 0 "
                "--test-fraction 0 (or set explicit_split in the task file) and re-convert (D1)")
        absent = sorted(c for c in train + val if c not in by_case)
        if absent:
            print(f"note: {len(absent)} listed case(s) are not converted and are left out, e.g. "
                  f"{absent[:5]} (A4-excluded proxies are expected here: see proxy_report.json)")
        train = [i for c in train for i in sorted(by_case.get(c, []))]
        val = [i for c in val for i in sorted(by_case.get(c, []))]
    if not train or not val:
        raise RuntimeError("explicit split has an empty train or val set after restricting to "
                           "converted cases")
    out_dir = task.preprocessed_dir(cfg)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = write_splits_final(out_dir / "splits_final.json",
                              [{"train": sorted(train), "val": sorted(val)}])
    (out_dir / EXPLICIT_SPLIT_RECORD).write_text(
        json.dumps({"source": "explicit", "n_train": len(train), "n_val": len(val)}, indent=1),
        encoding="utf-8")
    return path


def available_cases(cfg: Config, task: TaskConfig, folder: str = "imagesTr") -> set:
    """Case ids actually converted into ``folder`` (imagesTr by default)."""
    images = task.raw_dir(cfg) / folder
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
    # An explicit-split task (R1: ImageCAS-X train/val) never gets the hash split over its explicit
    # one (D13): re-planning keeps an existing explicit split, or writes it from $SEGTRAIN_ICX_DIR.
    if task_extras(task).get("explicit_split"):
        out_dir = task.preprocessed_dir(cfg)
        recorded = (out_dir / EXPLICIT_SPLIT_RECORD).is_file()
        if recorded and (out_dir / "splits_final.json").is_file():
            print(f"note: keeping the explicit split in {out_dir / 'splits_final.json'} "
                  f"({task.nnunet_name} uses explicit splits)")
            return out_dir / "splits_final.json"
        icx_dir = os.environ.get(ICX_DIR_ENV)
        if icx_dir:
            from .proxy import icx_split, load_sealed

            lists = icx_split(Path(icx_dir))
            return write_explicit_splits(cfg, task, lists["train"], lists["val"],
                                         sealed=load_sealed())
        raise RuntimeError(
            f"{task.nnunet_name} uses an explicit ImageCAS-X split: run `segtrain splits --task "
            f"{task.dataset_id} --explicit-icx <ImageCAS-X dir>` (or set {ICX_DIR_ENV}); "
            "refusing to write the hash split")
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


def _window_text(plans: dict) -> str:
    p = (plans.get("foreground_intensity_properties_per_channel") or {}).get("0") or {}
    if "percentile_00_5" not in p:
        return "n/a"
    return (f"[{p['percentile_00_5']:g}, {p['percentile_99_5']:g}] HU, "
            f"mean {p.get('mean', float('nan')):g}, sd {p.get('std', float('nan')):g}")


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
        f"  CT window        {_window_text(plans)}",
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
