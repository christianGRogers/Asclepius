"""``segtrain`` command line interface.

A normal Stage 1 run, start to finish::

    segtrain convert    --task 701
    segtrain plan       --task 701          # fingerprint + plans + splits
    segtrain preprocess --task 701
    segtrain train      --task 701 --fold 0
    segtrain preview    --task 701 --fold 0 --watch   # second terminal
    segtrain evaluate   --task 701

Heavy imports (torch, nnU-Net) happen inside the subcommands that need them, so
``convert``, ``splits``, ``status`` and ``evaluate --score-only`` all run on a
machine with neither installed.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

from . import __version__
from .config import Config, ConfigError, TaskConfig, list_tasks, load_config, load_task


def _progress(done: int, total: int, label: str = "") -> None:
    width = 32
    filled = int(width * done / total) if total else width
    bar = "#" * filled + "-" * (width - filled)
    sys.stderr.write(f"\r  [{bar}] {done}/{total} {label}")
    if done >= total:
        sys.stderr.write("\n")
    sys.stderr.flush()


def _load(args) -> tuple[Config, Optional[TaskConfig]]:
    overrides = {
        k: getattr(args, k, None)
        for k in ("zenodo_root", "nnunet_raw", "nnunet_preprocessed", "nnunet_results",
                  "runs_root", "link_mode")
    }
    cfg = load_config(getattr(args, "config", None), overrides)
    task = load_task(args.task) if getattr(args, "task", None) else None
    return cfg, task


# --------------------------------------------------------------------------- info


def cmd_info(args) -> int:
    cfg, _ = _load(args)
    print(f"segtrain {__version__}")
    print("\npaths:")
    for key in ("zenodo_root", "nnunet_raw", "nnunet_preprocessed", "nnunet_results", "runs_root"):
        value = getattr(cfg, key)
        mark = "" if Path(value).exists() else "   (does not exist yet)"
        print(f"  {key:<22} {value}{mark}")
    print(f"  link_mode              {cfg.link_mode}")
    print(f"  workers                {cfg.n_workers()}")

    print("\ntasks:")
    for name in list_tasks():
        t = load_task(name)
        print(f"  {t.nnunet_name:<24} {t.label_set.n_classes:>3} classes  "
              f"{t.spacing[0]:>4} mm  {t.configuration}")

    print("\ncompute:")
    try:
        import torch

        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                p = torch.cuda.get_device_properties(i)
                print(f"  cuda:{i}  {p.name}  {p.total_memory / 2**30:.1f} GiB")
        else:
            print("  no CUDA device -- training here is not viable; use --backend ssh/slurm")
    except ImportError:
        print("  torch not installed (fine for convert/splits/status)")

    if cfg.meta_csv.is_file():
        from .splits import check_expected_counts, read_meta

        rows = read_meta(cfg.meta_csv)
        counts = check_expected_counts(rows)
        print(f"\ndataset: {sum(counts.values())} cases "
              f"({counts.get('train', 0)} train / {counts.get('val', 0)} val / "
              f"{counts.get('test', 0)} test)")
    return 0


# ------------------------------------------------------------------------ convert


def cmd_convert(args) -> int:
    from .convert import convert_dataset
    from .splits import read_meta

    cfg, task = _load(args)
    cfg.validate(require_data=True)
    rows = read_meta(cfg.meta_csv)

    print(f"converting {task.nnunet_name} ({task.label_set.n_classes} structures) "
          f"-> {task.raw_dir(cfg)}")
    report = convert_dataset(
        cfg,
        task,
        rows,
        limit=args.limit,
        overwrite=args.overwrite,
        include_test=not args.no_test,
        dry_run=args.dry_run,
        progress=None if args.dry_run else _progress,
    )
    print(report.render())
    return 0 if report.ok else 1


# ------------------------------------------------------------------------- splits


def cmd_splits(args) -> int:
    from .plans import write_splits
    from .splits import load_splits, read_meta, summarize

    cfg, task = _load(args)
    cfg.validate(require_data=True)
    rows = read_meta(cfg.meta_csv)
    path = write_splits(cfg, task, scheme=args.scheme, n_folds=args.folds, seed=args.seed)
    # Summarise the file that was actually written. Reporting the unrestricted
    # split here would claim 1082 training cases when a subset conversion may
    # have left far fewer on disk.
    print(summarize(rows, load_splits(path)))
    print(f"\nwrote {path}")
    return 0


# --------------------------------------------------------------------------- plan


def cmd_plan(args) -> int:
    from .plans import describe_plans, extract_fingerprint, plan_experiment, write_splits

    cfg, task = _load(args)
    cfg.validate(require_data=True)

    if not args.skip_fingerprint:
        print(f"extracting fingerprint for {task.nnunet_name} ...")
        extract_fingerprint(cfg, task, check_integrity=args.verify_integrity)

    print(f"planning at {task.spacing[0]} mm ...")
    plan_experiment(cfg, task, gpu_memory_target_gb=args.gpu_mem)

    path = write_splits(cfg, task, scheme=args.scheme, n_folds=args.folds, seed=args.seed)
    print(f"wrote {path}")
    print()
    print(describe_plans(cfg, task))
    return 0


def cmd_preprocess(args) -> int:
    from .plans import describe_plans, preprocess

    cfg, task = _load(args)
    print(f"preprocessing {task.nnunet_name} [{task.configuration}] ...")
    print("  (this writes float32 arrays -- see README for disk sizing)")
    preprocess(cfg, task, num_processes=args.workers, verbose=args.verbose)
    print(describe_plans(cfg, task))
    return 0


# -------------------------------------------------------------------------- train


def _train_command(cfg: Config, task: TaskConfig, args) -> list[str]:
    """Build the nnU-Net training command line."""
    exe = shutil.which("nnUNetv2_train")
    base = [exe] if exe else [sys.executable, "-m", "nnunetv2.run.run_training"]
    cmd = [
        *base,
        str(task.dataset_id),
        task.configuration,
        str(args.fold),
        "-tr",
        args.trainer or task.trainer,
        "-p",
        task.plans_name,
        "-device",
        args.device,
    ]
    if args.continue_training:
        cmd.append("--c")
    if args.npz:
        # Off by default: float16 softmax per class per voxel is hundreds of GB
        # across a group model's validation set, and is only needed to build a
        # cross-fold ensemble.
        cmd.append("--npz")
    return cmd


def cmd_train(args) -> int:
    from .backends import get_backend
    from .plans import configure_nnunet_env
    from .preview import env_for_training

    cfg, task = _load(args)
    configure_nnunet_env(cfg)

    run_dir = task.run_dir(cfg, args.fold)
    run_dir.mkdir(parents=True, exist_ok=True)

    cmd = _train_command(cfg, task, args)
    env = env_for_training(run_dir, task.nnunet_name, epochs=args.epochs)
    env.update(cfg.export_nnunet_env())
    if args.iterations:
        env["SEGTRAIN_ITERATIONS"] = str(args.iterations)

    print(f"task     {task.nnunet_name} fold {args.fold}")
    print(f"run dir  {run_dir}")
    print(f"command  {' '.join(cmd)}")

    if args.dry_run:
        print("\n[dry-run] not launching")
        return 0

    if args.device == "cpu" and not args.i_know_cpu_is_slow:
        print(
            "\nrefusing to start: nnU-Net on CPU is roughly 100x slower than on a GPU, so a "
            "1000-epoch run would take months.\nFor a deliberate short smoke test, pass "
            "--epochs 5 --i-know-cpu-is-slow.",
            file=sys.stderr,
        )
        return 2

    if args.foreground:
        # Smoke tests and debugging want the traceback on screen, not buried in
        # train.log after the process has already detached.
        import subprocess

        return subprocess.run(cmd, env=env).returncode

    backend_kwargs = {}
    if args.backend == "ssh":
        backend_kwargs["host"] = args.host
    backend = get_backend(args.backend, **backend_kwargs)

    job = backend.submit(cmd, str(run_dir), env=env, cwd=str(Path.cwd()))
    print(f"\nlaunched: {job.describe()}")
    print(f"logs:     {run_dir / 'train.log'}")
    print(f"monitor:  segtrain status --task {task.dataset_id} --fold {args.fold}")
    print("          or point the Slicer SegmentatorTrainMonitor module at the run dir")
    return 0


# ------------------------------------------------------------------------ preview


def cmd_preview(args) -> int:
    from .preview import preview_once, watch

    cfg, task = _load(args)
    from .plans import configure_nnunet_env

    configure_nnunet_env(cfg)

    cases = args.cases.split(",") if args.cases else None
    if args.watch:
        print(f"watching {task.nnunet_name} fold {args.fold}; Ctrl-C to stop")
        watch(cfg, task, args.fold, cases=cases, device=args.device,
              poll_seconds=args.poll, compute_nsd=args.nsd)
        return 0

    n = preview_once(cfg, task, args.fold, cases=cases, device=args.device,
                     checkpoint_name=args.checkpoint, compute_nsd=args.nsd)
    print(f"rendered {n} preview(s) into {task.run_dir(cfg, args.fold) / 'previews'}")
    return 0 if n else 1


# ------------------------------------------------------------------------- status


def cmd_status(args) -> int:
    from .events import read_run

    cfg, task = _load(args)
    run_dir = Path(args.run_dir) if args.run_dir else task.run_dir(cfg, args.fold)
    if not run_dir.is_dir():
        print(f"no run directory at {run_dir}", file=sys.stderr)
        return 1

    state = read_run(run_dir)
    if not state.epochs and not state.meta:
        print(f"{run_dir}: no events yet")
        return 0

    print(f"run      {run_dir}")
    print(f"task     {state.meta.get('task', '?')}  fold {state.meta.get('fold', '?')}")
    print(f"status   {state.status or 'unknown'}")
    if state.meta.get("patch_size"):
        print(f"patch    {state.meta['patch_size']}  batch {state.meta.get('batch_size')}")
    total = state.total_epochs
    print(f"epoch    {state.current_epoch}" + (f" / {total}" if total else ""))

    eta = state.eta_seconds()
    if eta:
        print(f"eta      {eta / 3600:.1f} h")

    xs, ys = state.mean_pseudo_dice()
    if ys:
        print(f"pseudo Dice  latest {ys[-1]:.4f}  best {max(ys):.4f}")

    if state.previews:
        p = state.previews[-1]
        dice = p.get("dice") or {}
        mean = sum(dice.values()) / len(dice) if dice else float("nan")
        print(f"preview  epoch {p.get('epoch')} case {p.get('case')} "
              f"mean Dice {mean:.4f} over {len(dice)} structures")

    if args.worst and state.previews:
        dice = state.previews[-1].get("dice") or {}
        print(f"\nweakest {args.worst} structures in the latest preview:")
        for name, value in sorted(dice.items(), key=lambda kv: kv[1])[: args.worst]:
            print(f"  {name:<32} {value:.4f}")

    for m in state.messages[-5:]:
        print(f"  [{m.get('level')}] {m.get('message')}")
    return 0


# ----------------------------------------------------------------------- evaluate


def cmd_evaluate(args) -> int:
    from .evaluate import predict_test_set, score_predictions, summarize, write_reports

    cfg, task = _load(args)
    from .plans import configure_nnunet_env

    configure_nnunet_env(cfg)

    out_dir = task.run_dir(cfg, args.fold)
    if args.predictions:
        pred_dir = Path(args.predictions)
    else:
        print(f"running inference on the held-out test set ({args.checkpoint}) ...")
        pred_dir = predict_test_set(
            cfg, task, fold=args.fold, checkpoint_name=args.checkpoint,
            device=args.device, limit=args.limit,
        )
    print(f"scoring predictions in {pred_dir} ...")
    per_case = score_predictions(
        cfg, task, pred_dir, tolerance_mm=args.nsd_tolerance,
        compute_nsd=not args.no_nsd, limit=args.limit, progress=_progress,
    )
    if not per_case:
        print("no predictions could be matched to ground truth", file=sys.stderr)
        return 1

    a, b = write_reports(per_case, out_dir, prefix=args.prefix)
    print()
    print(summarize(per_case))
    print(f"\nwrote {a}\n      {b}")
    return 0


# --------------------------------------------------------------------------- main


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="segtrain",
        description="Training pipeline for whole-body CT anatomical segmentation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--version", action="version", version=f"segtrain {__version__}")

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", type=Path, help="path to a dataset config YAML")
    for key in ("zenodo-root", "nnunet-raw", "nnunet-preprocessed", "nnunet-results",
                "runs-root"):
        common.add_argument(f"--{key}", dest=key.replace("-", "_"),
                            help=f"override {key.replace('-', '_')}")
    common.add_argument("--link-mode", choices=("hardlink", "symlink", "copy"),
                        help="how to materialise images into imagesTr")

    task_opt = argparse.ArgumentParser(add_help=False)
    task_opt.add_argument("--task", "-t", required=True,
                          help="dataset id (701), name (Organs), or Dataset701_Total3mm")

    fold_opt = argparse.ArgumentParser(add_help=False)
    fold_opt.add_argument("--fold", "-f", type=int, default=0)

    split_opt = argparse.ArgumentParser(add_help=False)
    split_opt.add_argument("--scheme", choices=("official", "cv5"), default="official",
                           help="'official' keeps the published 1082/57 split (default)")
    split_opt.add_argument("--folds", type=int, default=5, help="folds when scheme=cv5")
    split_opt.add_argument("--seed", type=int, default=12345)

    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("info", parents=[common], help="show resolved paths, tasks and hardware")
    s.set_defaults(func=cmd_info)

    s = sub.add_parser("convert", parents=[common, task_opt],
                       help="build an nnU-Net raw dataset from the Zenodo layout")
    s.add_argument("--limit", type=int, help="convert only the first N training cases")
    s.add_argument("--overwrite", action="store_true", help="redo cases that already exist")
    s.add_argument("--no-test", action="store_true", help="skip the held-out test cases")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(func=cmd_convert)

    s = sub.add_parser("splits", parents=[common, task_opt, split_opt],
                       help="write splits_final.json from meta.csv")
    s.set_defaults(func=cmd_splits)

    s = sub.add_parser("plan", parents=[common, task_opt, split_opt],
                       help="fingerprint, plan at the task's spacing, and write splits")
    s.add_argument("--gpu-mem", type=float,
                   help="VRAM budget in GB for patch/batch sizing (nnU-Net default 8)")
    s.add_argument("--skip-fingerprint", action="store_true")
    s.add_argument("--verify-integrity", action="store_true",
                   help="re-read every image/label pair; slow, worth it once")
    s.set_defaults(func=cmd_plan)

    s = sub.add_parser("preprocess", parents=[common, task_opt],
                       help="resample and cache the dataset for training")
    s.add_argument("--workers", type=int)
    s.add_argument("--verbose", action="store_true")
    s.set_defaults(func=cmd_preprocess)

    s = sub.add_parser("train", parents=[common, task_opt, fold_opt], help="launch training")
    s.add_argument("--device", default="cuda", choices=("cuda", "cpu", "mps"))
    s.add_argument("--backend", default="local", choices=("local", "ssh", "slurm"))
    s.add_argument("--host", help="user@host for --backend ssh")
    s.add_argument("--trainer", help="override the task's trainer class")
    s.add_argument("--epochs", type=int, help="override epoch count (smoke tests)")
    s.add_argument("--iterations", type=int,
                   help="override iterations per epoch, default 250 (smoke tests only)")
    s.add_argument("--foreground", action="store_true",
                   help="run in this terminal instead of detaching")
    s.add_argument("--continue-training", "--c", action="store_true", dest="continue_training")
    s.add_argument("--npz", action="store_true",
                   help="save validation softmax; huge, only for cross-fold ensembling")
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--i-know-cpu-is-slow", action="store_true",
                   help=argparse.SUPPRESS)
    s.set_defaults(func=cmd_train)

    s = sub.add_parser("preview", parents=[common, task_opt, fold_opt],
                       help="render held-out cases from the current checkpoint")
    s.add_argument("--watch", action="store_true", help="follow the run until it ends")
    s.add_argument("--cases", help="comma-separated case ids (default: config)")
    s.add_argument("--device", default="cuda", choices=("cuda", "cpu", "mps"))
    s.add_argument("--checkpoint", default="checkpoint_latest.pth")
    s.add_argument("--poll", type=float, default=30.0, help="seconds between checks")
    s.add_argument("--nsd", action="store_true", help="also compute NSD (slow)")
    s.set_defaults(func=cmd_preview)

    s = sub.add_parser("status", parents=[common, task_opt, fold_opt],
                       help="summarise a run from its event stream")
    s.add_argument("--run-dir", help="read this directory instead of the configured one")
    s.add_argument("--worst", type=int, default=0, help="list the N weakest structures")
    s.set_defaults(func=cmd_status)

    s = sub.add_parser("evaluate", parents=[common, task_opt, fold_opt],
                       help="score the held-out test set with Dice and NSD")
    s.add_argument("--checkpoint", default="checkpoint_best.pth")
    s.add_argument("--device", default="cuda", choices=("cuda", "cpu", "mps"))
    s.add_argument("--predictions", help="score an existing prediction folder")
    s.add_argument("--limit", type=int)
    s.add_argument("--no-nsd", action="store_true", help="Dice only; much faster")
    s.add_argument("--nsd-tolerance", type=float, default=1.5)
    s.add_argument("--prefix", default="test")
    s.set_defaults(func=cmd_evaluate)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ConfigError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        if os.environ.get("SEGTRAIN_DEBUG"):
            raise
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
