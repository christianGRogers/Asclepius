"""SLURM job scripts, and the chain that carries a run past the 24-hour cap.

Trillium caps every job at 24 hours. Stage 1 is roughly 24-40 GPU-hours on an
H100 and the 1.5 mm group models are longer, so a run has to survive being
stopped and restarted. Three pieces cooperate:

1. ``SEGTRAIN_MAX_SECONDS`` in ``nnUNetTrainer_segtrain`` stops training at an
   epoch boundary before the wall, writes ``checkpoint_latest.pth``, and exits
   *without* nnU-Net's ``on_train_end`` -- which would delete that checkpoint.
2. A chain of blocks, submitted **once, from a login node**.
3. Each block resumes from ``checkpoint_latest.pth`` with ``--c``.

**Why the chain is submitted up front rather than by the job itself.** The
obvious design is a job that ends by submitting its own successor. On Trillium
that is not merely discouraged, it is blocked: *"Jobs cannot be submitted from
compute nodes (nor datamover nodes)."* A self-resubmitting script fails at the
last line, every time, and the run silently stops after one block. So the whole
chain is created at submit time, in one of two shapes:

``array`` (default)
    ``sbatch --array=1-N%1``. One submission, N blocks, ``%1`` forcing them to
    run one at a time. This is the pattern the Alliance's own machine-learning
    documentation recommends for exactly this problem. Blocks that start after
    the run has finished exit in seconds.

``dependency``
    N separate jobs, each ``--dependency=afterany`` on the one before. Same
    effect, more scheduler bookkeeping. It exists because the Trillium quickstart
    never mentions job arrays, so array behaviour there is undocumented; if
    ``array`` turns out to be restricted, this needs no code change to fall back
    to.

``afterany``, not ``afterok``: a block killed by preemption, node failure or the
walltime exits nonzero, and that is precisely when the next block is most needed.
``afterok`` would cancel the rest of the chain.

The trainer's budget is derived from ``--time``, never configured separately: two
numbers that must agree will eventually disagree, and the failure mode is a job
killed mid-epoch with no checkpoint.
"""

from __future__ import annotations

import re
import shlex
import subprocess
from pathlib import Path
from typing import Optional

from .config import Config, SciNetConfig, TaskConfig

# D-HH:MM:SS, D-HH:MM, D-HH, HH:MM:SS, MM:SS, MM -- SLURM's full --time grammar.
_WALLTIME = re.compile(
    r"^(?:(?P<days>\d+)-)?(?P<a>\d+)(?::(?P<b>\d+))?(?::(?P<c>\d+))?$"
)

CHAIN_MODES = ("array", "dependency")


class SlurmError(RuntimeError):
    pass


def parse_walltime(text: str) -> int:
    """SLURM ``--time`` string to seconds.

    Implemented rather than approximated because the training budget is derived
    from it, and misreading ``24:00`` as 24 hours when SLURM means 24 minutes
    would hand the trainer a budget 60x too long -- the job would then be killed
    mid-epoch every single block, and the run would never advance.
    """
    match = _WALLTIME.match(str(text).strip())
    if not match:
        raise SlurmError(
            f"could not parse walltime {text!r}; expected forms like "
            "'23:50:00', '1-00:00:00', '30:00' or '60'"
        )
    days = int(match.group("days") or 0)
    a, b, c = match.group("a"), match.group("b"), match.group("c")

    if c is not None:
        hours, minutes, seconds = int(a), int(b), int(c)
    elif b is not None:
        # Ambiguous by design in SLURM: with days present "1-12:30" is H:M,
        # without days "12:30" is M:S.
        if days:
            hours, minutes, seconds = int(a), int(b), 0
        else:
            hours, minutes, seconds = 0, int(a), int(b)
    else:
        hours, minutes, seconds = (int(a), 0, 0) if days else (0, int(a), 0)

    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def format_walltime(seconds: int) -> str:
    seconds = max(0, int(seconds))
    days, rest = divmod(seconds, 86400)
    hours, rest = divmod(rest, 3600)
    minutes, secs = divmod(rest, 60)
    if days:
        return f"{days}-{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def train_budget_seconds(sc: SciNetConfig) -> int:
    """Wall-clock seconds to give the trainer inside a job of ``sc.walltime``.

    The margin has to cover everything that is not training: module loading, the
    venv, any staging, nnU-Net unpacking its ``.npz`` archives, then at the far
    end one final epoch (the deadline is only tested at epoch boundaries), a
    ~400 MB checkpoint write, and shutting down the augmentation workers.
    Overshooting the margin wastes a slice of a 24-hour block; undershooting it
    means SIGKILL with the epoch lost.
    """
    total = parse_walltime(sc.walltime)
    budget = total - int(sc.pause_margin_seconds)
    if budget <= 0:
        raise SlurmError(
            f"walltime {sc.walltime} ({total}s) is not longer than "
            f"pause_margin_seconds ({sc.pause_margin_seconds}s); there would be "
            "no time left to train"
        )
    return budget


# --------------------------------------------------------------- script rendering


def sbatch_directives(
    sc: SciNetConfig,
    *,
    job_name: str,
    log_path: str,
    gpu: bool = True,
    array: Optional[str] = None,
) -> list[str]:
    """The ``#SBATCH`` block, as ordered lines.

    Returned rather than printed so tests can assert on it without rendering a
    whole script or touching a cluster.

    Three Trillium rules are enforced here by *omission*, which is why this looks
    thinner than a typical GPU job script:

    * **No ``--partition``.** "Do not specify this partition explicitly; you must
      allow the scheduler to select the appropriate partition for your job."
      ``gpu_partition``/``cpu_partition`` therefore default to empty and exist
      only for other clusters.
    * **No ``--mem``.** "Memory requests are ignored... Do not use ``--mem``."
      A single-GPU job gets a quarter node, about 188 GiB, whichever way you ask.
    * **No ``--cpus-per-task`` by default.** Scheduling is by whole GPU: one GPU
      comes with 24 of the node's 96 cores and none of the Trillium GPU examples
      request cores at all. The job reads what it actually got out of
      ``$SLURM_CPUS_ON_NODE`` instead of asserting a number the scheduler may
      ignore.
    """
    lines = [f"#SBATCH --job-name={job_name}"]
    if sc.account:
        lines.append(f"#SBATCH --account={sc.account}")

    partition = sc.gpu_partition if gpu else sc.cpu_partition
    if partition:
        lines.append(f"#SBATCH --partition={partition}")

    lines.append(f"#SBATCH --nodes={sc.nodes}")

    if gpu and sc.gpus_per_node:
        # --gpus-per-node, not --gres=gpu:N: the Alliance documents --gres as a
        # form that "may not be supported in the future".
        lines.append(f"#SBATCH --gpus-per-node={sc.gpus_per_node}")

    cpus = sc.cpus_per_task if gpu else sc.prepare_cpus
    if cpus:
        lines.append(f"#SBATCH --cpus-per-task={cpus}")
    if sc.mem:
        lines.append(f"#SBATCH --mem={sc.mem}")

    lines.append(f"#SBATCH --time={sc.walltime if gpu else sc.prepare_walltime}")
    if array:
        lines.append(f"#SBATCH --array={array}")
    lines.append(f"#SBATCH --output={log_path}")

    if sc.mail_user:
        lines.append(f"#SBATCH --mail-user={sc.mail_user}")
        lines.append(f"#SBATCH --mail-type={sc.mail_type}")

    lines.extend(sc.sbatch_extra)
    return lines


def _env_exports(env: dict) -> list[str]:
    return [f"export {key}={shlex.quote(str(value))}" for key, value in sorted(env.items())]


def _preamble(sc: SciNetConfig, *, gpu: bool) -> list[str]:
    """Modules, then the venv, then nothing else.

    Order matters twice over. The venv is built against one specific Python
    module, so activating it before loading that module gets you a different
    interpreter and a torch that cannot see the GPU. And ``module purge`` comes
    first because a job inherits the submitting shell's environment by default --
    which is how a module loaded once in a login shell ends up silently shadowing
    the one the venv was built against, weeks later.

    ``gpu_modules`` is separate from ``modules`` for a concrete reason: there is
    no ``cuda`` module on Trillium's CPU nodes, so a shared list containing it
    would make the CPU-only prepare job fail at ``module load`` before it did any
    work.
    """
    modules = list(sc.modules) + (list(sc.gpu_modules) if gpu else [])
    lines: list[str] = []
    if modules:
        lines.append("module purge")
        lines.append(f"module load {' '.join(modules)}")
    if sc.venv:
        lines.append(f"source {shlex.quote(sc.venv)}/bin/activate")
    lines.extend(sc.setup_commands)
    return lines


def _nnunet_env(cfg: Config, sc: SciNetConfig) -> dict:
    return {
        "nnUNet_raw": str(cfg.nnunet_raw),
        "nnUNet_preprocessed": str(cfg.nnunet_preprocessed),
        "nnUNet_results": str(cfg.nnunet_results),
        # Without this nnU-Net cannot find nnUNetTrainer_segtrain and the job dies
        # seconds in with "Could not find requested nnunet trainer" -- cheap, but
        # only if you know to look for it.
        "nnUNet_extTrainer": str(Path(__file__).resolve().parent / "nnunet_ext"),
        # SLURM buffers job output aggressively and may only flush at exit. Every
        # block of this chain is *designed* to end at the wall clock, so without
        # this the tail of every log -- the part saying whether the pause was
        # clean -- is the part you lose.
        "PYTHONUNBUFFERED": "1",
    }


def render_train_script(
    cfg: Config,
    task: TaskConfig,
    fold: int,
    *,
    epochs: Optional[int] = None,
    iterations: Optional[int] = None,
    preview: bool = True,
) -> str:
    """One block of the training chain.

    The same script serves both chain modes. In ``array`` mode SLURM supplies the
    block number in ``$SLURM_ARRAY_TASK_ID``; in ``dependency`` mode the
    submitter passes it as ``$1``. Nothing else differs, so there is no second
    template to keep in sync.
    """
    sc = cfg.scinet
    run_dir = task.run_dir(cfg, fold)
    budget = train_budget_seconds(sc)
    model_dir = (f"{cfg.nnunet_results}/{task.nnunet_name}/"
                 f"{task.trainer}__{task.plans_name}__{task.configuration}/fold_{fold}")

    env = _nnunet_env(cfg, sc)
    env.update({
        "SEGTRAIN_RUN_DIR": str(run_dir),
        "SEGTRAIN_TASK": task.nnunet_name,
        "SEGTRAIN_MAX_SECONDS": str(budget),
        "SEGTRAIN_SAVE_EVERY": str(sc.save_every),
    })
    if epochs:
        env["SEGTRAIN_EPOCHS"] = str(epochs)
    if iterations:
        env["SEGTRAIN_ITERATIONS"] = str(iterations)

    roots = [
        "--zenodo-root", str(cfg.zenodo_root),
        "--nnunet-raw", str(cfg.nnunet_raw),
        "--nnunet-preprocessed", str(cfg.nnunet_preprocessed),
        "--nnunet-results", str(cfg.nnunet_results),
        "--runs-root", str(cfg.runs_root),
    ]
    train_args = ["train", "--task", str(task.dataset_id), "--fold", str(fold),
                  "--device", "cuda", "--foreground", *roots]
    if epochs:
        train_args += ["--epochs", str(epochs)]
    if iterations:
        train_args += ["--iterations", str(iterations)]

    status_args = ["status", "--task", str(task.dataset_id), "--fold", str(fold),
                   "--run-dir", str(run_dir), "--is-complete"]
    preview_args = ["preview", "--task", str(task.dataset_id), "--fold", str(fold),
                    "--watch", "--device", "cuda", "--poll", "60", *roots]

    array = f"1-{sc.chain_max}%1" if sc.chain_mode == "array" else None
    log = f"{run_dir}/slurm-%A_%a.out" if array else f"{run_dir}/slurm-%j.out"

    body = [
        "#!/bin/bash",
        *sbatch_directives(
            sc,
            job_name=f"segtrain-{task.dataset_id}-f{fold}",
            log_path=log,
            gpu=True,
            array=array,
        ),
        "",
        # No -e: a nonzero exit from training must still reach the reporting at
        # the bottom, and -e would skip straight past it.
        "set -uo pipefail",
        "",
        'BLOCK="${SLURM_ARRAY_TASK_ID:-${1:-1}}"',
        f'RUN_DIR={shlex.quote(str(run_dir))}',
        f'MODEL_DIR={shlex.quote(model_dir)}',
        "",
        f'echo "=== segtrain block $BLOCK/{sc.chain_max}  job ${{SLURM_JOB_ID}}  '
        '$(date -Is) ==="',
        'echo "node $(hostname)  gpus ${SLURM_GPUS_ON_NODE:-?}  '
        'cores ${SLURM_CPUS_ON_NODE:-?}"',
        "",
        *_preamble(sc, gpu=True),
        "",
        *_env_exports(env),
        "",
        "# nnU-Net sizes its augmentation pool from the machine's core count",
        "# unless told otherwise. On Trillium a 1-GPU job holds 24 of the node's",
        "# 96 cores, so the default would oversubscribe the allocation 4x and",
        "# spend the run fighting the three jobs sharing the node.",
        'export nnUNet_n_proc_DA="${SLURM_CPUS_PER_TASK:-${SLURM_CPUS_ON_NODE:-24}}"'
        if not sc.dataloader_workers else
        f'export nnUNet_n_proc_DA={sc.dataloader_workers}',
        "",
        'mkdir -p "$RUN_DIR"',
        "",
        "# Blocks 2..N of an array are queued before anyone knows whether they",
        "# are needed. One that starts after the run has finished must not",
        "# restart training -- nnU-Net with no --c would begin again at epoch 0",
        "# and overwrite a finished model.",
        f"if segtrain {' '.join(shlex.quote(a) for a in status_args)}; then",
        '    echo "run already complete; nothing to do in this block"',
        "    exit 0",
        "fi",
        "",
    ]

    if sc.stage_to_tmpdir:
        body += _staging_block(cfg, task)

    body += [
        "",
        "# Resume whenever a checkpoint exists. Deciding here rather than at",
        "# submit time is what makes the chain restartable after a crash: block 1",
        "# may itself be a retry.",
        "CONTINUE=",
        'if [ -f "$MODEL_DIR/checkpoint_latest.pth" ]; then',
        "    CONTINUE=--continue-training",
        '    echo "found checkpoint_latest.pth; resuming"',
        "else",
        '    echo "no checkpoint; starting from epoch 0"',
        "fi",
        "",
    ]

    if preview:
        body += [
            "# The preview daemon shares this job's GPU. A second allocation for a",
            "# few seconds of inference every 25 epochs would double both the cost",
            "# of the run and the queue wait. Separate process, so a preview crash",
            "# cannot take training with it.",
            f"segtrain {' '.join(shlex.quote(a) for a in preview_args)} &",
            "PREVIEW_PID=$!",
            'trap \'kill "$PREVIEW_PID" 2>/dev/null\' EXIT',
            "",
        ]

    body += [
        "# timeout is a backstop, not the mechanism: SEGTRAIN_MAX_SECONDS should",
        "# already have paused cleanly at an epoch boundary well before this. It",
        "# fires only if that failed, and then at least the job ends on its own",
        "# terms with its log flushed rather than being SIGKILLed at the wall.",
        f"timeout {budget + 600} segtrain "
        f"{' '.join(shlex.quote(a) for a in train_args)} $CONTINUE",
        "TRAIN_RC=$?",
        'echo "training exited with $TRAIN_RC at $(date -Is)"',
        "",
        "# The trainer exits 0 for both 'paused at the wall' and 'finished all",
        "# epochs', so the exit code cannot tell them apart. The event stream can.",
        f"if segtrain {' '.join(shlex.quote(a) for a in status_args)}; then",
        '    echo "RUN COMPLETE; remaining blocks will exit immediately"',
        "else",
        '    echo "paused; the next block resumes from checkpoint_latest.pth"',
        "fi",
        "",
        "exit $TRAIN_RC",
    ]
    return "\n".join(body) + "\n"


def _staging_block(cfg: Config, task: TaskConfig) -> list[str]:
    """Copy the preprocessed task into ``$SLURM_TMPDIR`` and train from there.

    Read the size warning before enabling this. **On Trillium there is no
    node-local disk**: the nodes have none, and ``$SLURM_TMPDIR`` is a RAM disk
    whose contents count against the job's memory cgroup. So this trades RAM for
    filesystem I/O, and a 1-GPU job has about 188 GiB of it.

    That makes it a good deal for Stage 1 -- ~10 GB of 3 mm data, unpacked to
    ~14 GB, against 188 GiB -- and a bad one for the 1.5 mm group models, where
    preprocessed data is ~75 GB and nnU-Net's ``.npz`` -> ``.npy`` unpacking
    roughly doubles it. Hence ``stage_to_tmpdir`` defaults to off.

    It is also less necessary here than the usual advice implies. That advice was
    written for Lustre; Trillium's storage is all-NVMe VAST rated at ten million
    read IOPS, which tolerates many small random reads far better.

    ``df`` inside the job reports the RAM disk as the size of physical memory,
    not of your allocation, so it will happily let you fill it and be OOM-killed.
    The guard below checks the dataset size against the cgroup limit instead.
    """
    src = f"{cfg.nnunet_preprocessed}/{task.nnunet_name}"
    return [
        "# Stage preprocessed data into $SLURM_TMPDIR -- which on Trillium is a",
        "# RAM disk, so this spends job memory. See slurm.py for the sizing.",
        f"STAGE_SRC={shlex.quote(src)}",
        'if [ -n "${SLURM_TMPDIR:-}" ] && [ -d "$STAGE_SRC" ]; then',
        '    NEED_KB=$(du -sk "$STAGE_SRC" | cut -f1)',
        "    LIMIT_KB=$(awk '/MemTotal/ {print $2}' /proc/meminfo)",
        "    if [ -r /sys/fs/cgroup/memory.max ]; then",
        "        CG=$(cat /sys/fs/cgroup/memory.max)",
        '        [ "$CG" != "max" ] && LIMIT_KB=$((CG / 1024))',
        "    fi",
        "    # Unpacking .npz to .npy roughly doubles it, and training needs room",
        "    # on top, so require the staged copy to be under a third of the",
        "    # memory this job is actually allowed.",
        '    if [ "$NEED_KB" -lt $((LIMIT_KB / 3)) ]; then',
        '        echo "staging $((NEED_KB / 1024)) MiB into $SLURM_TMPDIR ..."',
        '        mkdir -p "$SLURM_TMPDIR/nnUNet_preprocessed"',
        '        if cp -r "$STAGE_SRC" "$SLURM_TMPDIR/nnUNet_preprocessed/"; then',
        '            export nnUNet_preprocessed="$SLURM_TMPDIR/nnUNet_preprocessed"',
        '            echo "staged; nnUNet_preprocessed=$nnUNet_preprocessed"',
        "        else",
        '            echo "WARNING: staging failed; training from $STAGE_SRC" >&2',
        "        fi",
        "    else",
        '        echo "NOT staging: $((NEED_KB / 1048576)) GiB will not fit in a"\\',
        '             "third of $((LIMIT_KB / 1048576)) GiB of job memory" >&2',
        "    fi",
        "else",
        '    echo "not staging; training from $nnUNet_preprocessed"',
        "fi",
    ]


def render_prepare_script(
    cfg: Config,
    task: TaskConfig,
    *,
    scheme: str = "official",
    convert: bool = False,
    workers: Optional[int] = None,
) -> str:
    """A CPU-only job for convert / plan / preprocess.

    No GPU is requested. Fingerprinting, planning and preprocessing are CPU and
    I/O bound, and a GPU allocation would sit idle for hours while queueing
    behind every other GPU job on the cluster. On Trillium the CPU subcluster is
    also 1224 nodes against the GPU subcluster's 63, so the wait is usually far
    shorter.

    One Trillium wrinkle: the CPU nodes have no ``cuda`` module, so ``modules``
    must not require one for this job to load its environment. Keeping cuda out
    of ``scinet.modules`` and into ``gpu_modules`` is what handles that.
    """
    sc = cfg.scinet
    log_dir = cfg.runs_root / f"{task.nnunet_name}__prepare"
    roots = [
        "--zenodo-root", str(cfg.zenodo_root),
        "--nnunet-raw", str(cfg.nnunet_raw),
        "--nnunet-preprocessed", str(cfg.nnunet_preprocessed),
        "--nnunet-results", str(cfg.nnunet_results),
        "--runs-root", str(cfg.runs_root),
    ]
    steps = []
    if convert:
        steps.append(["convert", "--task", str(task.dataset_id), *roots])
    steps.append(["plan", "--task", str(task.dataset_id), "--scheme", scheme, *roots])
    pre = ["preprocess", "--task", str(task.dataset_id), *roots]
    if workers:
        pre += ["--workers", str(workers)]
    steps.append(pre)

    body = [
        "#!/bin/bash",
        *sbatch_directives(
            sc,
            job_name=f"segtrain-prep-{task.dataset_id}",
            log_path=f"{log_dir}/slurm-%j.out",
            gpu=False,
        ),
        "",
        "set -euo pipefail",
        "",
        f'echo "=== segtrain prepare {task.nnunet_name}  job $SLURM_JOB_ID  '
        '$(date -Is) ==="',
        'echo "node $(hostname)  cores ${SLURM_CPUS_ON_NODE:-?}"',
        "",
        *_preamble(sc, gpu=False),
        "",
        *_env_exports(_nnunet_env(cfg, sc)),
        "",
    ]
    for step in steps:
        body.append(f"segtrain {' '.join(shlex.quote(a) for a in step)}")
    body += ["", 'echo "prepare finished at $(date -Is)"']
    return "\n".join(body) + "\n"


# ------------------------------------------------------------------- sbatch et al


def write_script(path: Path, text: str) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)
    return path


def submit_chain(sc: SciNetConfig, script: Path, cwd: Optional[str] = None) -> list[str]:
    """Create the whole chain, returning its job ids in order.

    In ``array`` mode that is one id; in ``dependency`` mode it is ``chain_max``
    of them, each waiting on its predecessor. Either way this must run on a login
    node -- compute nodes cannot submit.
    """
    if sc.chain_mode == "array":
        # --array is already in the script's directives, so one submission
        # creates all chain_max blocks.
        return [submit(script, cwd=cwd)]

    job_ids: list[str] = []
    previous: Optional[str] = None
    for block in range(1, sc.chain_max + 1):
        dependency = f"afterany:{previous}" if previous else None
        job_id = submit(script, [str(block)], dependency=dependency, cwd=cwd)
        job_ids.append(job_id)
        previous = job_id
    return job_ids


def submit(
    script: Path,
    args: Optional[list[str]] = None,
    *,
    dependency: Optional[str] = None,
    cwd: Optional[str] = None,
    hold: bool = False,
) -> str:
    """``sbatch --parsable``, returning the job id."""
    cmd = ["sbatch", "--parsable"]
    if dependency:
        cmd.append(f"--dependency={dependency}")
    if hold:
        cmd.append("--hold")
    cmd.append(str(script))
    cmd += [str(a) for a in (args or [])]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=cwd)
    except FileNotFoundError as exc:
        raise SlurmError(
            "sbatch is not on PATH. This has to run on a cluster login node -- "
            "and on Trillium, GPU jobs specifically from the GPU login node "
            "(trillium-gpu.alliancecan.ca). Compute and datamover nodes cannot "
            "submit jobs at all."
        ) from exc
    except subprocess.SubprocessError as exc:
        raise SlurmError(f"sbatch failed: {exc}") from exc

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise SlurmError(f"sbatch rejected the job: {detail}")

    # --parsable gives "jobid" or "jobid;cluster".
    return result.stdout.strip().split(";")[0]


def job_state(job_id: str) -> Optional[str]:
    """SLURM state for a job, or None if it cannot be determined.

    squeue first, then sacct: squeue only knows about pending and running jobs,
    and a finished job vanishes from it. Reading only squeue would report a
    completed run as "gone" and an accounting outage as "finished".
    """
    out = _run(["squeue", "--noheader", "--format=%T", "--job", str(job_id)])
    if out and out.strip():
        return out.splitlines()[0].strip() or None

    out = _run(["sacct", "--noheader", "--parsable2", "--format=State",
                "--jobs", str(job_id)])
    if out:
        for line in out.splitlines():
            state = line.strip().split("|")[0].strip()
            if state:
                # "CANCELLED by 12345"
                return state.split()[0]
    return None


def queued_jobs(name_prefix: str = "segtrain") -> list[dict]:
    """This user's queued or running jobs, optionally filtered by name prefix."""
    out = _run(["squeue", "--me", "--noheader", "--format=%i|%j|%T|%M|%L|%R"])
    if not out:
        return []
    jobs = []
    for line in out.splitlines():
        parts = line.strip().split("|")
        if len(parts) < 6:
            continue
        if name_prefix and not parts[1].startswith(name_prefix):
            continue
        jobs.append({
            "job_id": parts[0], "name": parts[1], "state": parts[2],
            "elapsed": parts[3], "left": parts[4], "reason": parts[5],
        })
    return jobs


def cancel(job_id: str) -> bool:
    return _run(["scancel", str(job_id)]) is not None


def _run(cmd: list[str]) -> Optional[str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout
