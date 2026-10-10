"""``segtrain`` command line interface.

A phase 1 coronary run, start to finish::

    segtrain index      --root /data/coronary   # scan cases -> meta.csv
    segtrain convert    --task 710
    segtrain plan       --task 710 --gpu-mem 24 # fingerprint + plans + splits
    segtrain preprocess --task 710
    segtrain train      --task 710 --fold 0
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
        layout=args.layout,
    )
    print(report.render())
    return 0 if report.ok else 1


# -------------------------------------------------------------------------- index


def cmd_index(args) -> int:
    """Scan a dataset directory and write the meta.csv the pipeline reads.

    This is the entry point for a labelled dataset. Once meta.csv exists every
    other subcommand works identically, whichever layout the data arrived in.

    Two layouts are understood and auto-detected: one directory per case, and
    the flat two-files-per-case form ImageCAS ships. Pass --layout to force
    one if the guess is wrong.
    """
    from .index import build_rows, read_overrides, scan, summarize, write_meta

    cfg, _ = _load(args)
    root = Path(args.root) if args.root else cfg.zenodo_root

    cases = scan(root, layout=args.layout)
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
    if args.explicit_icx:
        # R1 (task 712): ImageCAS-X train -> train, val -> val, sealed cases refused (A14).
        from .plans import write_explicit_splits
        from .proxy import icx_split, load_sealed

        lists = icx_split(args.explicit_icx)
        path = write_explicit_splits(cfg, task, lists["train"], lists["val"], sealed=load_sealed())
        print(f"train {len(lists['train'])}, val {len(lists['val'])}\nwrote {path}")
        return 0
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
    from .events import env_for_training
    from .plans import configure_nnunet_env

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
    print(f"watch:    segtrain status --task {task.dataset_id} --fold {args.fold} --watch")
    return 0


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


def _transport(cfg, args):
    """Pick the transport, or say what is missing."""
    from .transfer import LocalTransport, RsyncTransport

    remote = getattr(args, "remote", None) or cfg.transfer.remote
    local = getattr(args, "from_path", None) or cfg.transfer.local_path
    if remote and local:
        raise ConfigError(
            "a remote and a local source were both given; they are alternatives"
        )
    if local:
        return LocalTransport(source=str(Path(local).expanduser()))
    if remote:
        return RsyncTransport(
            remote=remote,
            ssh_options=cfg.transfer.ssh_options,
            bandwidth_limit=getattr(args, "bwlimit", None) or cfg.transfer.bandwidth_limit,
        )
    raise ConfigError(
        "no transfer source. Set `transfer.remote` in configs/dataset.local.yaml "
        "to the export directory on the Girder host, as rsync spells it "
        "(transfer.remote: segqueue@girder.example.org:/srv/segqueue/export), or "
        "pass --remote / --from once. `segqueue-export --out <dir>` on the server "
        "is what produces that directory."
    )


def cmd_scinet_fetch(args) -> int:
    """Pull the training export onto the cluster and verify it arrived intact.

    Deliberately not a job: compute nodes have no outbound network, so a transfer
    submitted to the queue waits for its allocation and then fails at the first
    connection.
    """
    from segqueue.manifest import FULL, QUICK

    from .transfer import TransferError, advise_destination, advise_host, pull

    cfg, task = _load(args)
    dest = Path(args.dest) if args.dest else cfg.zenodo_root
    transport = _transport(cfg, args)
    mode = QUICK if (args.quick or cfg.transfer.verify == "quick") else FULL

    print(f"source   {getattr(transport, 'remote', None) or getattr(transport, 'source', '')}")
    print(f"dest     {dest}")
    print(f"verify   {mode}")
    print()
    for note in advise_host() + advise_destination(dest):
        print(f"  !  {note}")
        print()

    if args.dry_run:
        print("[dry-run] fetching the manifest only, to report what would move")
        try:
            from segqueue.manifest import Manifest, needed
            dest.mkdir(parents=True, exist_ok=True)
            transport.fetch_manifest(str(dest))
            manifest = Manifest.read(dest)
        except (TransferError, OSError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        outstanding = needed(dest, manifest)
        totals = manifest.totals
        print(f"manifest {totals['cases']} case(s), {totals['files']} file(s), "
              f"{_human(totals['bytes'])}")
        print(f"would move {len(outstanding)} file(s); "
              f"{totals['files'] - len(outstanding)} already present")
        return 0

    def progress(attempt, remaining):
        label = "attempt" if attempt == 1 else "retry"
        print(f"[{label} {attempt}] {remaining} file(s) outstanding")

    try:
        report = pull(transport, dest, attempts=cfg.transfer.attempts, mode=mode,
                      progress=progress)
    except TransferError as exc:
        print("", file=sys.stderr)
        print(f"error: {exc}", file=sys.stderr)
        return 1

    receipt = report.write(dest)
    totals = report.totals
    print()
    print(f"manifest {totals['cases']} case(s), {totals['files']} file(s), "
          f"{_human(totals['bytes'])}  (exported {report.manifest_created})")
    print(f"moved    {len(report.transferred)} file(s) in {report.attempts} attempt(s), "
          f"{report.seconds:.0f}s")
    print(f"verify   {report.verified.summary()}")
    print(f"receipt  {receipt}")

    if not report.ok:
        print()
        broken = report.verified.broken_cases
        print(f"{len(broken)} case(s) did not arrive intact and must not be trained on:",
              file=sys.stderr)
        for case in broken[:20]:
            print(f"  {case}", file=sys.stderr)
        if len(broken) > 20:
            print(f"  ... and {len(broken) - 20} more", file=sys.stderr)
        print("", file=sys.stderr)
        print("Re-run this command: the work list is recomputed from what is "
              "here, so it will fetch only these.", file=sys.stderr)
        return 1

    print()
    print(f"next: segtrain index --root {dest}")
    return 0


def cmd_verify(args) -> int:
    """Check a local tree against the manifest that travelled with it."""
    from segqueue.manifest import FULL, QUICK, Manifest, ManifestError, verify

    cfg, _task = _load(args)
    root = Path(args.root) if args.root else cfg.zenodo_root
    mode = QUICK if args.quick else FULL

    try:
        manifest = Manifest.read(root)
    except ManifestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    totals = manifest.totals
    print(f"root     {root}")
    print(f"manifest {totals['cases']} case(s), {totals['files']} file(s), "
          f"{_human(totals['bytes'])}  (exported {manifest.created})")
    if manifest.source:
        segments = manifest.source.get("segments")
        if segments:
            print(f"labels   {len(segments)}: {', '.join(str(s) for s in segments)}")
    print()

    state = {"last": -1}

    def progress(path, index, total):
        if mode == FULL and total > 100:
            percent = (index * 100) // total
            if percent >= state["last"] + 10:
                state["last"] = percent
                print(f"  {percent}% ({index}/{total})", flush=True)

    result = verify(root, manifest, mode=mode, progress=progress)
    print(f"result   {result.summary()}")

    for label, paths in (("missing", result.missing), ("corrupt", result.corrupt)):
        for path in paths[:20]:
            print(f"  {label}: {path}")
        if len(paths) > 20:
            print(f"  ... and {len(paths) - 20} more {label}")
    for path, expected, found in result.truncated[:20]:
        print(f"  truncated: {path} ({found} of {expected} bytes)")
    if args.show_extra:
        for path in result.extra[:20]:
            print(f"  extra: {path}")

    if not result.is_clean:
        print()
        broken = result.broken_cases
        print(f"{len(broken)} of {totals['cases']} case(s) are not as promised. "
              "`segtrain fetch` re-fetches exactly these.", file=sys.stderr)
        return 1

    print("")
    print(f"All {totals['cases']} case(s) are byte-for-byte what was exported.")
    return 0


def _human(count: int) -> str:
    size = float(count)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{size:.1f} TiB"


def cmd_scinet_prepare(args) -> int:
    """Submit the CPU-only convert / plan / preprocess job."""
    from .slurm import SlurmError, parse_walltime, render_prepare_script, submit, write_script

    cfg, task = _load(args)
    sc = _scinet_bits(cfg)

    log_dir = cfg.runs_root / f"{task.nnunet_name}__prepare"
    log_dir.mkdir(parents=True, exist_ok=True)
    script_path = log_dir / "prepare.sh"
    text = render_prepare_script(cfg, task, scheme=args.scheme,
                                 convert=args.convert, workers=args.workers,
                                 layout=args.layout)
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
                               iterations=args.iterations)
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

    For working offline or archiving a finished run. To *watch* a run there is
    no need to copy anything: ``segtrain scinet status --watch`` reads
    events.jsonl over ssh, and the login nodes share $SCRATCH with the compute
    nodes, so the file being read is the one the job is writing.
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
    # of events, and pulling ~1 GB of .pth every time would make the
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


# --------------------------------------------------------------------------- coronary tools
#
# Thin wrappers over the four-class pipeline modules (tf1, namer, proxy, reads). Each loads
# NIfTI files with nibabel, calls one library function and prints or writes its result; the
# reasoning lives in the modules and in vault/Plans/.


def _nifti(path: Path):
    import nibabel as nib
    import numpy as np

    img = nib.load(str(path))
    return np.asarray(img.dataobj), img


def _discover_cases(root: Path) -> dict[str, dict]:
    """Cases under ``root`` in either supported layout, as ``{case: {"ct": .., "mask": ..}}``.

    Girder export: ``<root>/c0042/ct.nii.gz`` + ``coronary_arteries.nii.gz``. ImageCAS release:
    ``<root>/43.img.nii.gz`` + ``43.label.nii.gz``, which is tournament case ``c0042``."""
    root = Path(root)
    cases: dict[str, dict] = {}
    for d in sorted(root.iterdir()):
        ct, mask = d / "ct.nii.gz", d / "coronary_arteries.nii.gz"
        if d.is_dir() and ct.is_file() and mask.is_file():
            cases[d.name] = {"ct": ct, "mask": mask}
    for img in sorted(root.glob("*.img.nii.gz")):
        n = img.name.split(".", 1)[0]
        label = root / f"{n}.label.nii.gz"
        if n.isdigit() and label.is_file():
            cases[f"c{int(n) - 1:04d}"] = {"ct": img, "mask": label}
    return cases


def cmd_tf1(args) -> int:
    import json

    from .convert import align_to_reference
    from .tf1 import fp_components, tree_f1

    ref, ref_img = _nifti(args.reference)
    spacing = ref_img.header.get_zooms()[:3]

    # Every volume is put on the reference's voxel grid before anything is compared voxel by
    # voxel: a prediction or aorta stored with an axis reversed (SegQueue / TotalSegmentator
    # outputs) would otherwise score as a near-total miss (Echo D12). A real geometry mismatch
    # is refused.
    def on_ref_grid(path, what):
        _, img = _nifti(path)
        data, problem = align_to_reference(img, ref_img)
        if data is None:
            print(f"refusing: {what} {path} is not on the reference grid ({problem})",
                  file=sys.stderr)
        return data

    pred = on_ref_grid(args.prediction, "prediction")
    aorta = on_ref_grid(args.aorta, "aorta mask") if args.aorta else None
    ct = on_ref_grid(args.ct, "CT") if args.ct else None
    if pred is None or (args.aorta and aorta is None) or (args.ct and ct is None):
        return 2
    aorta = aorta > 0 if aorta is not None else None
    result = tree_f1(ref, pred, spacing, tol_mm=args.tol, aorta=aorta, ct=ct)
    row = result.as_row()
    row["fp_components"] = fp_components(ref, pred)
    print(json.dumps(row, indent=1, default=str))
    return 0


def cmd_name(args) -> int:
    import json

    import nibabel as nib
    import numpy as np

    from .namer import name_tree

    mask, img = _nifti(args.mask)
    result = name_tree(mask > 0, img.affine, ramus=args.ramus)
    nib.save(nib.Nifti1Image(result.labels.astype(np.uint8), img.affine), str(args.out))
    print(f"wrote {args.out}")
    if args.json:
        print(json.dumps(result.decisions.__dict__, indent=1, default=str))
    return 0


def cmd_name_qa(args) -> int:
    import json

    from .namer import disagreement

    label, img = _nifti(args.label)
    mask, _ = _nifti(args.mask)
    d = disagreement(label, mask > 0, img.affine, ramus=args.ramus)
    print(json.dumps({"exclude": bool(d["exclude"]), "ramus_only": bool(d["ramus_only"]),
                      "ignore_voxels": int(d["ignore"].sum()), "flags": d["flags"],
                      "reason": d["reason"]}, indent=1, default=str))
    return 1 if d["exclude"] else 0


def cmd_proxy(args) -> int:
    from .proxy import build_proxy_tree, load_sealed

    cases = _discover_cases(args.cases)
    if not cases:
        print(f"no cases found under {args.cases} (expected c0000/ct.nii.gz or 1.img.nii.gz)",
              file=sys.stderr)
        return 2
    records = build_proxy_tree(cases, args.icx, args.root, load_sealed(args.sealed),
                               subsets=args.subsets, workers=args.workers)
    # Count what was actually written; say what was not, and why (Echo D8).
    written = [r for r in records if r.ok and not r.excluded]
    excluded = [r for r in records if r.ok and r.excluded]
    failed = [r for r in records if not r.ok]
    import json

    report = json.loads((Path(args.root) / "proxy_report.json").read_text(encoding="utf-8"))
    missing = report.get("missing", [])
    print(f"{len(written)} proxy cases written under {args.root} (see proxy_report.json)")
    if excluded:
        print(f"  {len(excluded)} excluded by the A4 namer QA (not written; human review), e.g. "
              f"{', '.join(r.case for r in excluded[:5])}")
    if failed:
        print(f"  FAILED: {len(failed)} case(s), e.g. "
              + "; ".join(f"{r.case}: {r.error}" for r in failed[:3]), file=sys.stderr)
    if missing:
        print(f"  MISSING: {len(missing)} requested ImageCAS-X case(s) are not under {args.cases}, "
              f"e.g. {', '.join(missing[:5])}", file=sys.stderr)
    if written and not report.get("qa_applied"):
        print("  WARNING: the A4 namer QA did not run (segtrain.namer unavailable): the proxies "
              "carry no carina ignore and no wholesale-disagreement exclusion", file=sys.stderr)
    if not written:
        print("no proxy case was written", file=sys.stderr)
        return 1
    return 1 if (failed or missing) else 0


def cmd_aorta(args) -> int:
    from .aorta import AortaBatchError, produce_aortas
    from .proxy import load_sealed

    found = _discover_cases(args.cases)
    if not found:
        print(f"no cases found under {args.cases} (expected c0000/ct.nii.gz or 1.img.nii.gz)",
              file=sys.stderr)
        return 2
    cts = {c: v["ct"] for c, v in found.items()}
    refs = {c: v["mask"] for c, v in found.items()} if args.crop else None
    try:
        report = produce_aortas(cts, args.out, device=args.device, references=refs,
                                sealed=load_sealed(args.sealed), overwrite=args.overwrite)
    except AortaBatchError as e:
        print(f"aorta: {e}", file=sys.stderr)
        return 1
    print(f"aorta masks: {len(report.made)} made, {len(report.kept)} already present, "
          f"in {args.out} (see aorta_report.json)")
    return 0


def cmd_reads_report(args) -> int:
    import json

    from .reads import default_scorer, first_reads_report, load_read_folder, report_markdown

    cases = load_read_folder(args.reads, mask_dir=args.masks, icx_dir=args.icx,
                             aorta_dir=args.aorta_dir)
    # With --aorta-dir each case is scored with its own aorta (the A1 ostium of record);
    # cases without one, or a run without the option, stay provisional (A1a).
    scorer = default_scorer() if args.score else None
    report = first_reads_report(cases, scorer=scorer, previous_bias_flag=args.previous_bias_flag,
                                per_case_tf1=bool(args.aorta_dir) and args.score)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "report.json").write_text(json.dumps(report, indent=1, default=str))
    (args.out / "REPORT.md").write_text(report_markdown(report))
    print(f"{len(cases)} cases; wrote {args.out / 'REPORT.md'} and report.json")
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
                          help="dataset id (710), name (CoronaryLumen), or "
                               "Dataset710_CoronaryLumen")

    fold_opt = argparse.ArgumentParser(add_help=False)
    fold_opt.add_argument("--fold", "-f", type=int, default=0)

    split_opt = argparse.ArgumentParser(add_help=False)
    split_opt.add_argument("--scheme", choices=("official", "cv5"), default="official",
                           help="'official' keeps the split recorded in meta.csv "
                                "(default); 'cv5' builds 5-fold CV over train+val")
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
    s.add_argument("--layout", default="auto", choices=("auto", "nested", "flat"),
                   help="source layout, as for `index`. Auto-detected, and it has "
                        "to match what index saw or meta.csv names cases convert "
                        "cannot find")
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
    s.add_argument("--layout", default="auto", choices=("auto", "nested", "flat"),
                   help="nested: one directory per case. flat: <id>.img.nii.gz "
                        "beside <id>.label.nii.gz, as ImageCAS ships (default: auto)")
    s.add_argument("--overrides",
                   help="CSV of case_id,split to pin specific cases -- this is how "
                        "an official published split is honoured instead of hashing")
    s.add_argument("--force", action="store_true", help="overwrite an existing meta.csv")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(func=cmd_index)

    s = sub.add_parser(
        "verify", parents=[common],
        help="check a data tree against the manifest that came with it",
        description="Answer the question `segtrain index` cannot: not how many "
                    "cases are here, but whether they are the ones that were sent "
                    "and all of them. Reads manifest.json at the root of the tree.")
    s.add_argument("--root", help="tree to check (default: zenodo_root)")
    s.add_argument("--quick", action="store_true",
                   help="compare sizes only. A stat per file instead of reading "
                        "every byte; catches truncation, not corruption")
    s.add_argument("--show-extra", action="store_true",
                   help="also list files present here but not in the manifest")
    s.set_defaults(func=cmd_verify)

    s = sub.add_parser("splits", parents=[common, task_opt, split_opt],
                       help="write splits_final.json from meta.csv")
    s.add_argument("--explicit-icx", type=Path, metavar="ICX_DIR",
                   help="write ImageCAS-X's own train/val split instead (task 712)")
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

    s = sub.add_parser("status", parents=[common, task_opt, fold_opt],
                       help="summarise a run from its event stream")
    s.add_argument("--run-dir", help="read this directory instead of the configured one")
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

    s = scisub.add_parser(
        "fetch", parents=[common, task_opt],
        help="pull the training export here and verify it, on a login node",
        description="Pull an export written by `segqueue-export` and check every "
                    "file against the manifest that travelled with it. Re-running "
                    "fetches only what is missing or wrong, so an interrupted "
                    "transfer costs the remainder rather than the whole thing. Run "
                    "this on a login or datamover node: compute nodes have no "
                    "outbound network.")
    s.add_argument("--dest", help="override zenodo_root as the destination")
    s.add_argument("--remote", help="rsync source, e.g. user@host:/srv/segqueue/export "
                                    "(overrides transfer.remote)")
    s.add_argument("--from", dest="from_path",
                   help="a mounted source directory instead of a remote")
    s.add_argument("--bwlimit", help="rsync --bwlimit value, e.g. 50m")
    s.add_argument("--quick", action="store_true",
                   help="verify sizes only, not contents. Catches a truncated "
                        "transfer but not a corrupted byte")
    s.add_argument("--dry-run", action="store_true",
                   help="fetch the manifest and report what would move")
    s.set_defaults(func=cmd_scinet_fetch)

    s = scisub.add_parser("prepare", parents=[common, task_opt],
                          help="submit the CPU-only convert/plan/preprocess job")
    s.add_argument("--scheme", choices=("official", "cv5"), default="official")
    s.add_argument("--convert", action="store_true",
                   help="also run `convert` in the job, before planning")
    s.add_argument("--layout", default="auto", choices=("auto", "nested", "flat"),
                   help="source layout for the convert step, written into the job "
                        "script so it cannot guess differently hours later")
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

    # Four-class coronary tools (vault/Plans/Master plan.md). No config needed.
    s = sub.add_parser("tf1", help="tree-F1 of a 4-class prediction against a reference (A9)")
    s.add_argument("reference", type=Path, help="4-class reference NIfTI")
    s.add_argument("prediction", type=Path, help="4-class prediction NIfTI, same grid")
    s.add_argument("--aorta", type=Path, help="aorta mask for the A1 ostium (else provisional)")
    s.add_argument("--ct", type=Path, help="CT, for the blood-pool ostium rule")
    s.add_argument("--tol", type=float, default=1.5, help="gap tolerance in mm (decided: 1.5)")
    s.set_defaults(func=cmd_tf1)

    s = sub.add_parser("name", help="name a binary coronary tree into LM/LAD/LCx/RCA")
    s.add_argument("mask", type=Path, help="binary lumen mask NIfTI")
    s.add_argument("out", type=Path, help="output 4-class NIfTI")
    s.add_argument("--ramus", default="LCx", help="ramus intermedius class (decided: LCx)")
    s.add_argument("--json", action="store_true", help="also print the naming decisions")
    s.set_defaults(func=cmd_name)

    s = sub.add_parser("name-qa", help="check a 4-class label against the rule namer (A4); "
                                       "exit 1 if the case should be excluded")
    s.add_argument("label", type=Path, help="4-class label NIfTI")
    s.add_argument("mask", type=Path, help="the binary mask it was split from")
    s.add_argument("--ramus", default="LCx")
    s.set_defaults(func=cmd_name_qa)

    s = sub.add_parser("proxy", help="build the R1 proxy labels (ImageCAS-X names on the "
                                     "ImageCAS mask) for task 712")
    s.add_argument("--cases", type=Path, required=True, help="case directory (either layout)")
    s.add_argument("--icx", type=Path, required=True, help="ImageCAS-X dataset directory")
    s.add_argument("--root", type=Path, required=True, help="output directory")
    s.add_argument("--sealed", type=Path,
                   help="sealed-test JSON (default trillium/sealed_test.json)")
    s.add_argument("--subsets", nargs="+", default=["train", "val"])
    s.add_argument("--workers", type=int, default=1)
    s.set_defaults(func=cmd_proxy)

    s = sub.add_parser("aorta", help="TotalSegmentator aorta masks for the A1 ostium "
                                     "(needs the 'aorta' extra)")
    s.add_argument("--cases", type=Path, required=True, help="case directory (either layout)")
    s.add_argument("--out", type=Path, required=True, help="writes <case>_aorta.nii.gz here")
    s.add_argument("--device", default="cpu", help="cpu, gpu or gpu:N")
    s.add_argument("--no-crop", dest="crop", action="store_false",
                   help="segment the whole CT instead of a crop around the coronary mask")
    s.add_argument("--sealed", type=Path,
                   help="sealed-test JSON (default trillium/sealed_test.json); "
                        "sealed cases are refused")
    s.add_argument("--overwrite", action="store_true")
    s.set_defaults(func=cmd_aorta)

    s = sub.add_parser("reads-report", help="A12 report on double reads: convention, "
                                            "inter-read tF1, carina anchor, habits")
    s.add_argument("reads", type=Path, help="folder of <case>/<annotator>.nii.gz reads")
    s.add_argument("--masks", type=Path, help="ImageCAS masks (either case layout's mask files)")
    s.add_argument("--icx", type=Path, help="ImageCAS-X dataset directory (carina anchor)")
    s.add_argument("--aorta-dir", type=Path,
                   help="per-case aorta masks as written by segtrain.aorta (A1 ostium); "
                        "without it tF1 is provisional")
    s.add_argument("--no-score", dest="score", action="store_false",
                   help="skip tF1 (fast; convention and anchor checks only)")
    s.add_argument("--previous-bias-flag", action="store_true",
                   help="the previous wave raised the carina bias flag (confirms it)")
    s.add_argument("--out", type=Path, required=True, help="output directory")
    s.set_defaults(func=cmd_reads_report)

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
