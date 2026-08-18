"""``segtrain`` command line interface.

A phase 1 coronary run, start to finish::

    segtrain index      --root /data/coronary   # scan cases -> meta.csv
    segtrain convert    --task 710
    segtrain plan       --task 710 --gpu-mem 24 # fingerprint + plans + splits
    segtrain preprocess --task 710
    segtrain train      --task 710 --fold 0
    segtrain preview    --task 710 --fold 0 --watch   # second terminal
    segtrain evaluate   --task 710

The same run on a SciNet cluster, from a login node::

    segtrain scinet check                              # config, paths, quotas
    segtrain index          --root $SCRATCH/coronary   # login node
    segtrain scinet prepare --task 710 --convert       # CPU job
    segtrain scinet submit  --task 710 --fold 0        # chained GPU job
    segtrain scinet status  --task 710 --fold 0 --watch

Heavy imports (torch, nnU-Net) happen inside the subcommands that need them, so
``convert``, ``splits``, ``status`` and ``evaluate --score-only`` all run on a
machine with neither installed -- including a login node, where importing torch
to print a help message would be antisocial.
"""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import sys
import time
from dataclasses import replace
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
              f"{t.spacing_label:>9}  {t.configuration}")

    print("\ncompute:")
    try:
        import torch

        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                p = torch.cuda.get_device_properties(i)
                print(f"  cuda:{i}  {p.name}  {p.total_memory / 2**30:.1f} GiB")
        else:
            print("  no CUDA device -- training here is not viable; "
                  "use `segtrain scinet submit`")
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


# -------------------------------------------------------------------------- index


def cmd_index(args) -> int:
    """Scan a dataset directory and write the meta.csv the pipeline reads.

    This is the entry point for your own labelled data. TotalSegmentator ships
    its own meta.csv with a published split; anything else needs one written, and
    once it exists every other subcommand works identically.
    """
    from .index import build_rows, read_overrides, scan, summarize, write_meta

    cfg, _ = _load(args)
    root = Path(args.root) if args.root else cfg.zenodo_root

    cases = scan(root)
    if not cases:
        print(f"no cases found under {root}\n"
              "Expected one directory per case, each containing ct.nii.gz "
              "(or image.nii.gz, or <case>.nii.gz).", file=sys.stderr)
        return 1

    overrides = read_overrides(Path(args.overrides)) if args.overrides else None
    rows = build_rows(
        cases,
        val_fraction=args.val_fraction,
        test_fraction=args.test_fraction,
        seed=args.seed,
        study_type=args.study_type,
        overrides=overrides,
    )

    print(f"root     {root}")
    print(summarize(cases, rows, args.val_fraction, args.test_fraction))
    if overrides:
        print(f"  pinned:  {len(overrides)} case(s) placed by {args.overrides}")

    out = Path(args.out) if args.out else root / "meta.csv"
    if args.dry_run:
        print(f"\n[dry-run] would write {out}")
        return 0

    # Refuse to silently rewrite an index that other artefacts already depend on:
    # a converted dataset and a splits_final.json were built against the old one,
    # and reassigning splits underneath them moves test cases into training.
    if out.exists() and not args.force:
        print(f"\n{out} already exists. Re-writing it can move cases between "
              "splits,\nwhich invalidates anything already converted or trained. "
              "Pass --force if that is what you want.", file=sys.stderr)
        return 1

    write_meta(out, rows)
    print(f"\nwrote {out}")
    print(f"next: segtrain convert --task {args.task}" if getattr(args, "task", None)
          else "next: segtrain convert --task 710")
    return 0


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

    print(f"planning at {task.spacing_label} target spacing ...")
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

    if args.backend == "slurm":
        backend = get_backend("slurm", scinet=cfg.scinet)
        print("\nnote: this submits a single job of "
              f"{cfg.scinet.walltime}. A 1000-epoch run does not fit in one; use "
              "`segtrain scinet submit` for the chained version.")
    else:
        backend = get_backend(args.backend)

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

    if getattr(args, "is_complete", False):
        # Silent and exit-code only: this is a shell predicate, not a report.
        # A missing run directory is "not complete", not an error, because the
        # first block of a chain asks before anything has been written.
        if not run_dir.is_dir():
            return 1
        return 0 if read_run(run_dir).status == "completed" else 1

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


# ------------------------------------------------------------------------- scinet


def _scinet_bits(cfg: Config):
    """Validate the cluster config, and fail with something actionable.

    Called before anything is rendered or submitted. Every one of these is a
    mistake that otherwise surfaces as an sbatch rejection or -- much worse -- a
    job that starts, runs for a minute and dies, which on a busy cluster costs a
    queue wait to discover.
    """
    from .slurm import SlurmError, train_budget_seconds

    sc = cfg.scinet
    problems = []
    if not sc.account:
        problems.append(
            "no allocation account. Set scinet.account in configs/dataset.local.yaml, "
            "or export SLURM_ACCOUNT. `sshare -U` lists the accounts you can charge."
        )
    if not sc.modules and not sc.venv:
        problems.append(
            "neither scinet.modules nor scinet.venv is set, so the job would run "
            "against the compute node's bare system Python and fail on `import torch`."
        )
    try:
        train_budget_seconds(sc)
    except SlurmError as exc:
        problems.append(str(exc))

    if problems:
        raise ConfigError("cluster configuration is incomplete:\n  - "
                          + "\n  - ".join(problems))
    return sc


def cmd_scinet_check(args) -> int:
    """Pre-flight the cluster setup without submitting anything.

    Worth running once per session: every check here corresponds to a failure
    that would otherwise be found by a job dying after its queue wait.
    """
    import subprocess

    from .slurm import parse_walltime, queued_jobs

    cfg, _ = _load(args)
    sc = cfg.scinet
    ok = True

    def report(label: str, good: bool, detail: str = "") -> None:
        nonlocal ok
        ok = ok and good
        print(f"  [{'ok' if good else '!!'}] {label:<28} {detail}")

    print(f"cluster  {sc.cluster}")
    print("\nscheduler:")
    have_sbatch = shutil.which("sbatch") is not None
    report("sbatch on PATH", have_sbatch,
           "" if have_sbatch else "not a cluster login node -- submit from one")
    report("account", bool(sc.account), sc.account or "unset (see `sshare -U`)")

    if have_sbatch:
        jobs = queued_jobs()
        print(f"  [--] {'segtrain jobs queued':<28} {len(jobs)}")
        for job in jobs:
            print(f"         {job['job_id']}  {job['name']:<22} {job['state']:<10} "
                  f"{job['reason']}")

    print("\nbudget:")
    total = parse_walltime(sc.walltime)
    budget = sc.budget_seconds()
    report("walltime", True, f"{sc.walltime}  ({total / 3600:.1f} h)")
    report("trainer budget", budget > 0,
           f"{budget}s ({budget / 3600:.1f} h), margin {sc.pause_margin_seconds}s")
    report("chain", sc.chain_max >= 1,
           f"{sc.chain_mode}, {sc.chain_max} block(s) = up to "
           f"{sc.chain_max * total / 3600:.0f} h total")
    # 24 h is the hard cap on both Trillium subclusters; sbatch rejects anything
    # longer outright rather than trimming it.
    if sc.cluster == "trillium" and total > 24 * 3600:
        report("walltime <= 24 h", False,
               f"{sc.walltime} exceeds Trillium's 24 h limit; sbatch will refuse it")

    print("\nenvironment:")
    report("modules", bool(sc.modules), " ".join(sc.modules) or "none set")
    print(f"  [--] {'gpu modules (extra)':<28} {' '.join(sc.gpu_modules) or 'none'}")
    venv_ok = bool(sc.venv) and Path(sc.venv, "bin", "activate").is_file()
    report("venv", venv_ok, sc.venv or "none set")
    if sc.venv and not venv_ok:
        print(f"         no bin/activate under {sc.venv} -- run `segtrain scinet setup`")
    # Trillium's guidance is explicit and the failure is silent-looking: a venv
    # on $SCRATCH "may get partially deleted", which surfaces weeks later as an
    # ImportError in block 7 of a chain.
    scratch = os.environ.get("SCRATCH")
    if sc.venv and scratch and str(sc.venv).startswith(scratch):
        report("venv location", False,
               "on $SCRATCH, which may be partially deleted -- put it in $HOME")

    print("\npaths:")
    home = os.environ.get("HOME", "")
    project = os.environ.get("PROJECT", "")
    for key in ("zenodo_root", "nnunet_raw", "nnunet_preprocessed", "nnunet_results",
                "runs_root"):
        value = Path(getattr(cfg, key))
        exists = value.is_dir()
        # A missing root is only a problem if its *parent* is not writable: the
        # pipeline creates these itself.
        parent_ok = exists or (value.parent.is_dir() and os.access(value.parent, os.W_OK))
        note = "" if exists else "   (will be created)"

        # The one that actually bites on Trillium. $HOME and $PROJECT are mounted
        # read-only on compute nodes, so a job writing there dies on its first
        # output -- after its queue wait, and for a reason the traceback does not
        # make obvious.
        readonly = None
        if key != "zenodo_root":
            if home and str(value).startswith(home) and not (
                    project and str(value).startswith(project)):
                readonly = "$HOME"
            elif project and str(value).startswith(project):
                readonly = "$PROJECT"
        if readonly and sc.cluster == "trillium":
            report(key, False,
                   f"{value}   under {readonly}, which is READ-ONLY on compute "
                   "nodes -- move it to $SCRATCH")
        else:
            report(key, parent_ok, str(value) + note)

    print("\nfilesystem:")
    if shutil.which("diskusage_report"):
        out = subprocess.run(["diskusage_report"], capture_output=True, text=True,
                             timeout=120)
        for line in (out.stdout or "").splitlines():
            print("  " + line)
        print("  $SCRATCH allows 25 TB / 10M files, so this dataset's ~145,000 files")
        print("  are a non-issue; space is the thing to watch.")
    else:
        print("  diskusage_report not found; check your quota by hand")

    print("\ngpu:" if have_sbatch else "\ngpu (this node):")
    try:
        import torch

        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                p = torch.cuda.get_device_properties(i)
                print(f"  cuda:{i}  {p.name}  {p.total_memory / 2**30:.1f} GiB")
        else:
            print("  no CUDA device here, which is normal on a login node -- "
                  "the job script asks for one")
    except ImportError:
        print("  torch not importable here; fine on a login node if the venv is "
              "activated only inside the job")

    print("\n" + ("ready to submit" if ok else "fix the '!!' lines above first"))
    return 0 if ok else 1


def cmd_scinet_setup(args) -> int:
    """Print the commands that build the venv on a login node.

    Printed rather than executed. Building it needs the right module stack loaded
    in the *calling* shell, and a Python subprocess cannot change its parent's
    environment -- so a script that ran these itself would either work by luck or
    build a venv against the wrong interpreter. Handing over an exact block to
    paste is both honest and easier to debug.
    """
    cfg, _ = _load(args)
    sc = cfg.scinet
    venv = sc.venv or "$SCRATCH/segtrain/.venv"
    repo = Path(__file__).resolve().parents[2]

    modules = list(sc.modules) + list(sc.gpu_modules)

    print("# Run these once, on the GPU login node (trillium-gpu.alliancecan.ca).")
    print("# Compute nodes have no outbound internet, so every download happens here.")
    print("#")
    print("# The venv goes in $HOME, not $SCRATCH: compute nodes can read $HOME,")
    print("# $SCRATCH 'may get partially deleted', and $SLURM_TMPDIR is a RAM disk.")
    print()
    if modules:
        print("module purge")
        print(f"module load {' '.join(modules)}\n")
    print(f"virtualenv --no-download {venv}" if not args.venv_module
          else f"python -m venv {venv}")
    print(f"source {venv}/bin/activate")
    print("pip install --no-index --upgrade pip")
    print()
    print("# --no-index installs from the Alliance wheelhouse rather than PyPI.")
    print("# Those wheels are built against this cluster's CUDA, drivers and CPU;")
    print("# PyPI's torch bundles its own CUDA and is the usual cause of a job")
    print("# that imports fine and then cannot see the GPU. H100s need torch>=2.5.1.")
    print("pip install --no-index torch nnunetv2 SimpleITK nibabel")
    print()
    print("# The pipeline itself, without letting pip re-resolve the above.")
    print(f"pip install --no-deps -e {shlex.quote(str(repo))}")
    print()
    print("# Then check it:")
    print("python -c 'import torch, nnunetv2; print(torch.__version__, "
          "torch.version.cuda)'")
    print("segtrain scinet check")
    print()
    print("# Note: `avail_wheels torch nnunetv2` shows what the wheelhouse has.")
    print("# Stay on Python 3.11/3.12 -- there is no SimpleITK wheel for 3.13+.")
    return 0


def cmd_scinet_fetch(args) -> int:
    """Download the dataset onto the cluster from a login node.

    Deliberately not a job: compute nodes have no outbound internet, so a
    download submitted to the queue would wait for hours and then fail at the
    first HTTP request.
    """
    import subprocess

    cfg, task = _load(args)
    dest = Path(args.dest) if args.dest else cfg.zenodo_root
    script = Path(__file__).resolve().parents[2] / "scripts" / "init_dataset.py"

    print(f"dest     {dest}")
    print("source   zenodo.org/records/10047292 -- TotalSegmentator v2.0.1, ~22 GB")
    print("          expands to ~30 GB and about 145,000 files.")
    print()
    print("Two things to check before this runs:")
    print("  * that this is a login or datamover node (tri-dm1.scinet.utoronto.ca).")
    print("    Compute nodes have no outbound internet and cannot reach Zenodo,")
    print("    so this can never be a batch job.")
    print("  * that `dest` is under $SCRATCH. $HOME and $PROJECT are read-only")
    print("    from compute nodes, so a dataset in either is unusable by a job.")
    print()
    print("Space, not inodes, is the constraint here: $SCRATCH allows 25 TB and")
    print("10M files, so 145,000 is not a problem. The download resumes, so an")
    print("interrupted transfer costs only the remainder.")
    print()
    if args.dry_run:
        print("[dry-run] not downloading")
        return 0

    cmd = [sys.executable, str(script), "--dest", str(dest)]
    if args.keep_zip:
        cmd.append("--keep-zip")
    print("+ " + " ".join(cmd))
    code = subprocess.run(cmd).returncode
    if code != 0:
        return code

    print()
    print("Once every task is converted the Zenodo tree is no longer needed --")
    print(f"~30 GB and ~145,000 files back:  rm -rf {dest}")
    print(f"next: segtrain scinet prepare --task {task.dataset_id} --convert")
    return 0


def cmd_scinet_prepare(args) -> int:
    """Submit the CPU-only convert / plan / preprocess job."""
    from .slurm import SlurmError, parse_walltime, render_prepare_script, submit, write_script

    cfg, task = _load(args)
    sc = _scinet_bits(cfg)

    log_dir = cfg.runs_root / f"{task.nnunet_name}__prepare"
    log_dir.mkdir(parents=True, exist_ok=True)
    script_path = log_dir / "prepare.sh"
    text = render_prepare_script(cfg, task, scheme=args.scheme,
                                 convert=args.convert, workers=args.workers)
    write_script(script_path, text)

    print(f"task     {task.nnunet_name}")
    print(f"steps    {'convert, ' if args.convert else ''}plan, preprocess")
    print(f"queue    {sc.cpu_partition or '(site default)'}  "
          f"{sc.prepare_cpus or sc.cpus_per_task} cpus  {sc.prepare_walltime}")
    print(f"script   {script_path}")
    print("  no GPU is requested: this is CPU and I/O work, and the CPU queue is")
    print("  both cheaper against the allocation and usually far shorter.")
    print()
    if args.dry_run:
        print(text)
        return 0

    try:
        job_id = submit(script_path)
    except SlurmError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"submitted job {job_id}")
    print(f"logs     {log_dir}/slurm-{job_id}.out")
    print(f"next     segtrain scinet submit --task {task.dataset_id} "
          f"  (after this finishes; ~{parse_walltime(sc.prepare_walltime) // 3600} h cap)")
    return 0


def cmd_scinet_submit(args) -> int:
    """Submit the whole training chain.

    One command covers the whole run: each block trains to its wall-clock budget,
    checkpoints, and the next resumes from that checkpoint. The chain is created
    here, on the login node, because Trillium forbids a job from submitting
    anything -- see ``segtrain.slurm``.
    """
    from .slurm import SlurmError, parse_walltime, render_train_script, submit_chain, write_script

    cfg, task = _load(args)
    sc = _scinet_bits(cfg)

    overrides = {}
    if args.chain_max:
        overrides["chain_max"] = args.chain_max
    if args.chain_mode:
        overrides["chain_mode"] = args.chain_mode
    if overrides:
        sc = replace(sc, **overrides)
        sc.validate()
        cfg = replace(cfg, scinet=sc)

    run_dir = task.run_dir(cfg, args.fold)
    run_dir.mkdir(parents=True, exist_ok=True)
    script_path = run_dir / "job.sh"

    text = render_train_script(cfg, task, args.fold, epochs=args.epochs,
                               iterations=args.iterations,
                               preview=not args.no_preview)
    write_script(script_path, text)

    block = parse_walltime(sc.walltime)
    budget = sc.budget_seconds()
    epochs = args.epochs or task.epochs
    total_hours = sc.chain_max * block / 3600

    print(f"task     {task.nnunet_name} fold {args.fold}")
    print(f"queue    {sc.gpu_partition or '(scheduler chooses -- correct on Trillium)'}"
          f"  {sc.gpus_per_node} gpu  {sc.walltime}")
    print(f"budget   {budget / 3600:.1f} h of training per block, "
          f"{sc.pause_margin_seconds / 60:.0f} min margin")
    print(f"chain    {sc.chain_mode}, up to {sc.chain_max} block(s) = "
          f"{total_hours:.0f} h of GPU time")
    print(f"epochs   {epochs}")
    print(f"script   {script_path}")
    if sc.stage_to_tmpdir:
        print("staging  preprocessed data into $SLURM_TMPDIR -- which is a RAM disk "
              "on Trillium,")
        print("         and so spends job memory. The script re-checks that it fits.")

    # A 1000-epoch 3d_fullres run is ~24-40 GPU-hours, so a chain that cannot
    # reach the end will stop short and look, from the event stream, exactly like
    # a run still in progress. Say so now rather than in two days.
    if total_hours < 40 and epochs >= 1000:
        print()
        print(f"note: {sc.chain_max} x {sc.walltime} is {total_hours:.0f} h, which "
              f"may not finish {epochs} epochs.")
        print("      Raise scinet.chain_max (or --chain-max). Re-running this "
              "command later also resumes,")
        print("      so stopping short costs a queue wait rather than the run.")
    print()

    if args.dry_run:
        print(text)
        return 0

    try:
        job_ids = submit_chain(sc, script_path)
    except SlurmError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if sc.chain_mode == "array":
        print(f"submitted array job {job_ids[0]}  "
              f"({sc.chain_max} block(s), one at a time)")
        print(f"logs     {run_dir}/slurm-{job_ids[0]}_1.out ...")
    else:
        print(f"submitted {len(job_ids)} chained job(s): {', '.join(job_ids)}")
        print(f"logs     {run_dir}/slurm-<jobid>.out")
    print(f"watch    segtrain scinet status --task {task.dataset_id} "
          f"--fold {args.fold} --watch")
    print(f"stop     segtrain scinet cancel --task {task.dataset_id} "
          f"--fold {args.fold}")
    print(f"slicer   {sc.run_address(str(run_dir))}")
    return 0


def cmd_scinet_status(args) -> int:
    """Training progress from the event stream, plus what SLURM thinks.

    Both halves are needed and neither is sufficient. The event stream is silent
    while a job sits in the queue, and SLURM says RUNNING for a job whose trainer
    crashed twenty minutes ago.
    """
    from .events import read_run
    from .slurm import queued_jobs

    cfg, task = _load(args)
    run_dir = Path(args.run_dir) if args.run_dir else task.run_dir(cfg, args.fold)
    run_name = run_dir.name

    def queue_line() -> str:
        jobs = [j for j in queued_jobs()
                if j["name"] == f"segtrain-{task.dataset_id}-f{args.fold}"]
        if not jobs:
            return "no job queued or running"
        return "  ".join(
            f"{j['job_id']} {j['state']}"
            + (f" ({j['reason']})" if j["state"].upper() == "PENDING" else "")
            + (f" {j['left']} left" if j["state"].upper() == "RUNNING" else "")
            for j in jobs
        )

    while True:
        events = run_dir / "events.jsonl"
        if not events.is_file():
            line = f"{run_name}: no events yet  |  {queue_line()}"
        else:
            state = read_run(run_dir)
            _, dice = state.mean_pseudo_dice()
            eta = state.eta_seconds()
            line = (f"{run_name}  epoch {state.current_epoch}"
                    + (f"/{state.total_epochs}" if state.total_epochs else "")
                    + (f"  pseudo Dice {dice[-1]:.4f}" if dice else "")
                    + (f"  eta {eta / 3600:.1f} h" if eta else "")
                    + f"  [{state.status or 'waiting'}]  |  {queue_line()}")

        if not args.watch:
            print(line)
            if not events.is_file():
                return 1
            return 0

        sys.stdout.write("\r" + line.ljust(140))
        sys.stdout.flush()
        if events.is_file() and read_run(run_dir).status == "completed":
            print()
            return 0
        time.sleep(args.interval)


def cmd_scinet_queue(args) -> int:
    from .slurm import queued_jobs

    jobs = queued_jobs("" if args.all else "segtrain")
    if not jobs:
        print("nothing queued")
        return 0
    print(f"{'job':<12} {'name':<26} {'state':<10} {'elapsed':>9} {'left':>9}  reason")
    for job in jobs:
        print(f"{job['job_id']:<12} {job['name']:<26} {job['state']:<10} "
              f"{job['elapsed']:>9} {job['left']:>9}  {job['reason']}")
    return 0


def cmd_scinet_cancel(args) -> int:
    """Cancel the running block and the queued successor.

    Order matters, and getting it wrong is a trap: the successor depends on this
    job with ``afterany``, so cancelling the running job *first* satisfies that
    dependency and SLURM promptly starts the block you were trying to stop.
    """
    from .slurm import cancel, queued_jobs

    cfg, task = _load(args)
    run_dir = task.run_dir(cfg, args.fold)
    name = f"segtrain-{task.dataset_id}-f{args.fold}"

    jobs = [j for j in queued_jobs() if j["name"] == name]
    if not jobs:
        print(f"no queued or running job named {name}")
        return 0

    # Pending (the successors) before running (the current block).
    jobs.sort(key=lambda j: 0 if j["state"].upper() == "PENDING" else 1)
    for job in jobs:
        good = cancel(job["job_id"])
        print(f"{'cancelled' if good else 'FAILED to cancel'} "
              f"{job['job_id']} ({job['state']})")

    (run_dir / "chain_next.jobid").unlink(missing_ok=True)
    print("\ncheckpoint_latest.pth is untouched, so `segtrain scinet submit` "
          "resumes where this left off.")
    return 0


def cmd_scinet_pull(args) -> int:
    """Copy a run directory, and optionally its checkpoints, to this machine.

    For working offline or archiving a finished run. To *watch* a run, point the
    Slicer monitor straight at ``user@host:/path`` instead -- it reads the live
    file on the shared filesystem and needs no copy at all.
    """
    import subprocess

    cfg, task = _load(args)
    sc = cfg.scinet
    host = args.host or sc.login_host
    if not host:
        print("no login host: pass --host user@trillium.scinet.utoronto.ca or set "
              "scinet.login_host", file=sys.stderr)
        return 2

    remote_runs = args.remote_runs_root or str(cfg.runs_root)
    run_name = f"{task.nnunet_name}__fold{args.fold}"
    dest = Path(args.dest or cfg.runs_root)
    dest.mkdir(parents=True, exist_ok=True)

    base = ["-o", "BatchMode=yes"]
    if args.identity_file:
        base += ["-i", args.identity_file]

    print(f"run directory -> {dest / run_name}")
    # Exclude checkpoints from the default sweep: the run directory is a few MB
    # of events and previews, and pulling ~1 GB of .pth every time would make the
    # common case unusable over a home connection.
    cmd = ["scp", *base, "-r", f"{host}:{remote_runs}/{run_name}", str(dest)]
    print("+ " + " ".join(cmd))
    if subprocess.run(cmd).returncode != 0:
        return 1

    if args.checkpoints:
        model = f"{task.trainer}__{task.plans_name}__{task.configuration}"
        remote_results = args.remote_results_root or str(cfg.nnunet_results)
        local = task.results_dir(cfg) / model / f"fold_{args.fold}"
        local.mkdir(parents=True, exist_ok=True)
        print(f"checkpoints   -> {local}")
        for name in ("checkpoint_best.pth", "checkpoint_final.pth"):
            remote = f"{host}:{remote_results}/{task.nnunet_name}/{model}/fold_{args.fold}/{name}"
            print(f"  {name} (~400 MB) ...")
            subprocess.run(["scp", *base, remote, str(local / name)])
        for name in ("dataset.json", "plans.json"):
            remote = f"{host}:{remote_results}/{task.nnunet_name}/{model}/{name}"
            subprocess.run(["scp", *base, remote, str(local.parent / name)])

    print("\ndone")
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
                          help="dataset id (710), name (Coronary), or Dataset710_Coronary")

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

    s = sub.add_parser("index", parents=[common],
                       help="scan your own dataset directory and write meta.csv")
    s.add_argument("--root", help="dataset root; defaults to the configured data root")
    s.add_argument("--out", help="where to write meta.csv (default: <root>/meta.csv)")
    s.add_argument("--val-fraction", type=float, default=0.15)
    s.add_argument("--test-fraction", type=float, default=0.15)
    s.add_argument("--seed", type=int, default=12345,
                   help="changing this reshuffles every case; do not change it "
                        "once you have trained anything")
    s.add_argument("--study-type", default="ccta",
                   help="recorded per case; used to stratify --scheme cv5 folds")
    s.add_argument("--overrides", help="CSV of case_id,split to pin specific cases")
    s.add_argument("--force", action="store_true", help="overwrite an existing meta.csv")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(func=cmd_index)

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
    s.add_argument("--backend", default="local", choices=("local", "slurm"),
                   help="'slurm' submits one job, one walltime block; for a "
                        "multi-day run use `segtrain scinet submit`")
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
    # Used by the SLURM job script to decide whether to cancel its own queued
    # successor: the trainer exits 0 for both "paused at the wall" and "finished",
    # so only the event stream can tell them apart.
    s.add_argument("--is-complete", action="store_true",
                   help="print nothing; exit 0 only if the run finished all its epochs")
    s.set_defaults(func=cmd_status)

    # -- scinet: the SLURM/GPU workflow
    sci = sub.add_parser(
        "scinet",
        help="run on a SciNet cluster via SLURM (check, setup, fetch, prepare, submit)")
    scisub = sci.add_subparsers(dest="scinet_command", required=True)

    s = scisub.add_parser("check", parents=[common],
                          help="pre-flight the cluster config, paths and quotas")
    s.set_defaults(func=cmd_scinet_check)

    s = scisub.add_parser("setup", parents=[common],
                          help="print the login-node commands that build the venv")
    s.add_argument("--venv-module", action="store_true",
                   help="use `python -m venv` instead of the Alliance `virtualenv "
                        "--no-download` wrapper")
    s.set_defaults(func=cmd_scinet_setup)

    s = scisub.add_parser("fetch", parents=[common, task_opt],
                          help="download the dataset here, on a login node")
    s.add_argument("--dest", help="override zenodo_root for this download")
    s.add_argument("--keep-zip", action="store_true",
                   help="keep the 22 GB archive after extracting")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(func=cmd_scinet_fetch)

    s = scisub.add_parser("prepare", parents=[common, task_opt],
                          help="submit the CPU-only convert/plan/preprocess job")
    s.add_argument("--scheme", choices=("official", "cv5"), default="official")
    s.add_argument("--convert", action="store_true",
                   help="also run `convert` in the job, before planning")
    s.add_argument("--workers", type=int, help="preprocessing worker processes")
    s.add_argument("--dry-run", action="store_true", help="print the script, submit nothing")
    s.set_defaults(func=cmd_scinet_prepare)

    s = scisub.add_parser("submit", parents=[common, task_opt, fold_opt],
                          help="submit the training job chain (crosses the 24 h cap)")
    s.add_argument("--epochs", type=int)
    s.add_argument("--iterations", type=int, help="iterations per epoch (smoke tests)")
    s.add_argument("--chain-max", type=int,
                   help="override scinet.chain_max: how many walltime blocks")
    s.add_argument("--chain-mode", choices=("array", "dependency"),
                   help="one --array=1-N%%1 job (default) or N --dependency jobs")
    s.add_argument("--no-preview", action="store_true",
                   help="do not run the preview daemon alongside training")
    s.add_argument("--dry-run", action="store_true", help="print the script, submit nothing")
    s.set_defaults(func=cmd_scinet_submit)

    s = scisub.add_parser("status", parents=[common, task_opt, fold_opt],
                          help="training progress plus the SLURM queue state")
    s.add_argument("--run-dir", help="read this directory instead of the configured one")
    s.add_argument("--watch", action="store_true")
    s.add_argument("--interval", type=float, default=30.0)
    s.set_defaults(func=cmd_scinet_status)

    s = scisub.add_parser("queue", parents=[common],
                          help="list your queued and running jobs")
    s.add_argument("--all", action="store_true", help="not just segtrain jobs")
    s.set_defaults(func=cmd_scinet_queue)

    s = scisub.add_parser("cancel", parents=[common, task_opt, fold_opt],
                          help="cancel the running block and its queued successor")
    s.set_defaults(func=cmd_scinet_cancel)

    s = scisub.add_parser("pull", parents=[common, task_opt, fold_opt],
                          help="copy a run directory here over scp")
    s.add_argument("--host", help="user@login-node; defaults to scinet.login_host")
    s.add_argument("--identity-file", help="SSH private key")
    s.add_argument("--dest", help="where to put the run directory locally")
    s.add_argument("--remote-runs-root", help="runs_root on the cluster, if it differs")
    s.add_argument("--remote-results-root",
                   help="nnUNet_results on the cluster, if it differs")
    s.add_argument("--checkpoints", action="store_true", help="also fetch .pth files")
    s.set_defaults(func=cmd_scinet_pull)

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
