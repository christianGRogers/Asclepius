"""Job-script rendering and the walltime chain.

None of this needs a cluster, which is the point: every mistake these tests
catch is otherwise found by a job that queues for hours and then dies, or worse,
by one that runs for a day and quietly makes no progress.
"""

from __future__ import annotations

import stat
from dataclasses import replace

import pytest

from segtrain import slurm
from segtrain.backends import BackendError, get_backend
from segtrain.config import Config, ConfigError, PreviewConfig, SciNetConfig, load_task


@pytest.fixture
def cfg(tmp_path) -> Config:
    """A config rooted in tmp_path, with a plausible cluster section."""
    return Config(
        zenodo_root=tmp_path / "ts",
        nnunet_raw=tmp_path / "raw",
        nnunet_preprocessed=tmp_path / "pre",
        nnunet_results=tmp_path / "res",
        runs_root=tmp_path / "runs",
        preview=PreviewConfig(),
        scinet=SciNetConfig(
            account="rrg-example",
            modules=["StdEnv/2023", "python/3.11.5"],
            gpu_modules=["cuda/12.6"],
            venv="/home/g/grp/you/segtrain-env",
        ),
    )


@pytest.fixture
def task():
    return load_task("710")


# ----------------------------------------------------------------- walltime


@pytest.mark.parametrize(
    "text,seconds",
    [
        ("23:50:00", 23 * 3600 + 50 * 60),
        ("24:00:00", 86400),
        ("1-00:00:00", 86400),
        ("1-12:00:00", 129600),
        ("0-01:30:00", 5400),
        # SLURM's genuinely ambiguous forms: without a day part "12:30" is
        # minutes:seconds, with one it is hours:minutes. Getting this backwards
        # is a 60x error in the trainer's budget.
        ("12:30", 750),
        ("1-12:30", 86400 + 12 * 3600 + 30 * 60),
        ("60", 3600),
        ("1-6", 86400 + 6 * 3600),
    ],
)
def test_parse_walltime(text, seconds):
    assert slurm.parse_walltime(text) == seconds


@pytest.mark.parametrize("bad", ["", "abc", "1:2:3:4", "24h", "-5", "1--00:00"])
def test_parse_walltime_rejects_garbage(bad):
    with pytest.raises(slurm.SlurmError):
        slurm.parse_walltime(bad)


@pytest.mark.parametrize("seconds", [0, 59, 3600, 86399, 86400, 129600])
def test_walltime_round_trips(seconds):
    assert slurm.parse_walltime(slurm.format_walltime(seconds)) == seconds


def test_budget_is_walltime_minus_margin():
    sc = SciNetConfig(walltime="23:50:00", pause_margin_seconds=1800)
    assert slurm.train_budget_seconds(sc) == 23 * 3600 + 50 * 60 - 1800


def test_budget_refuses_a_margin_larger_than_the_job():
    """A margin over the walltime would give the trainer a negative budget.

    The trainer would then believe it was already out of time, pause at epoch
    zero, and every block in the chain would do the same -- a run that burns its
    whole allocation without training a single epoch.
    """
    sc = SciNetConfig(walltime="00:20:00", pause_margin_seconds=1800)
    with pytest.raises(slurm.SlurmError, match="no time left to train"):
        slurm.train_budget_seconds(sc)


# --------------------------------------------------------------- directives


def test_directives_carry_account_gpus_and_time(cfg):
    lines = slurm.sbatch_directives(cfg.scinet, job_name="j", log_path="/l/%j.out")
    assert "#SBATCH --account=rrg-example" in lines
    assert "#SBATCH --gpus-per-node=1" in lines
    assert "#SBATCH --time=23:50:00" in lines
    assert "#SBATCH --output=/l/%j.out" in lines


def test_trillium_forbidden_directives_are_omitted(cfg):
    """Trillium rejects or ignores --partition, --mem and per-core requests.

    Emitting them is not harmless: an explicit --partition is documented as
    something the scheduler must be left to choose, and a job that asks wrongly
    is rejected rather than corrected.
    """
    lines = slurm.sbatch_directives(cfg.scinet, job_name="j", log_path="/l")
    joined = "\n".join(lines)
    assert "--partition" not in joined
    assert "--mem" not in joined
    assert "--cpus-per-task" not in joined


def test_partition_and_mem_appear_when_explicitly_configured(cfg):
    """The fields still work for a cluster that is not Trillium."""
    sc = replace(cfg.scinet, cluster="other", gpu_partition="gpubase",
                 mem="180G", cpus_per_task=16)
    lines = slurm.sbatch_directives(sc, job_name="j", log_path="/l")
    assert "#SBATCH --partition=gpubase" in lines
    assert "#SBATCH --mem=180G" in lines
    assert "#SBATCH --cpus-per-task=16" in lines


def test_cpu_job_uses_the_prepare_walltime(cfg):
    sc = replace(cfg.scinet, walltime="23:50:00", prepare_walltime="04:00:00")
    lines = slurm.sbatch_directives(sc, job_name="j", log_path="/l", gpu=False)
    assert "#SBATCH --time=04:00:00" in lines
    assert not any("--gpus-per-node" in ln for ln in lines)


def test_sbatch_extra_is_appended_verbatim(cfg):
    sc = replace(cfg.scinet, sbatch_extra=["#SBATCH --export=NONE"])
    lines = slurm.sbatch_directives(sc, job_name="j", log_path="/l")
    assert lines[-1] == "#SBATCH --export=NONE"


# ------------------------------------------------------------ train script


def test_array_mode_renders_one_serialised_array(cfg, task):
    sc = replace(cfg.scinet, chain_mode="array", chain_max=3)
    script = slurm.render_train_script(replace(cfg, scinet=sc), task, 0)
    # %1 is the whole point: without it all three blocks run at once, from the
    # same checkpoint, and overwrite each other's results.
    assert "#SBATCH --array=1-3%1" in script
    assert "slurm-%A_%a.out" in script


def test_dependency_mode_renders_no_array_directive(cfg, task):
    sc = replace(cfg.scinet, chain_mode="dependency", chain_max=3)
    script = slurm.render_train_script(replace(cfg, scinet=sc), task, 0)
    assert "--array" not in script
    assert "slurm-%j.out" in script


def test_block_number_comes_from_the_array_id_or_the_argument(cfg, task):
    """One script serves both chain modes."""
    script = slurm.render_train_script(cfg, task, 0)
    assert 'BLOCK="${SLURM_ARRAY_TASK_ID:-${1:-1}}"' in script


def test_script_never_submits_another_job(cfg, task):
    """Trillium blocks job submission from compute nodes.

    A self-resubmitting script is the natural design for this problem and it is
    the one thing that cannot work here: the sbatch at the end fails every time,
    so the chain silently stops after one block.
    """
    script = slurm.render_train_script(cfg, task, 0)
    body = "\n".join(ln for ln in script.splitlines() if not ln.lstrip().startswith("#"))
    assert "sbatch" not in body
    assert "scancel" not in body


def test_a_late_block_exits_instead_of_restarting_training(cfg, task):
    """Blocks queued behind a run that finishes early must not train.

    Without the guard, nnU-Net launched with no --c on a completed run starts
    again at epoch 0 and overwrites a finished model.
    """
    script = slurm.render_train_script(cfg, task, 0)
    guard = script.index("--is-complete")
    train = script.index("segtrain train")
    assert guard < train, "the completion check must precede training"
    assert "exit 0" in script[guard:train]


def test_resume_is_decided_at_run_time_from_the_checkpoint(cfg, task):
    """Not at submit time: block 1 may itself be a retry after a crash."""
    script = slurm.render_train_script(cfg, task, 0)
    assert 'if [ -f "$MODEL_DIR/checkpoint_latest.pth" ]; then' in script
    assert "CONTINUE=--continue-training" in script
    assert "$CONTINUE" in script


def test_model_dir_matches_the_task_layout(cfg, task):
    script = slurm.render_train_script(cfg, task, 2)
    expected = (f"{cfg.nnunet_results}/{task.nnunet_name}/"
                f"{task.trainer}__{task.plans_name}__{task.configuration}/fold_2")
    assert expected in script


def test_budget_is_exported_and_matches_the_walltime(cfg, task):
    script = slurm.render_train_script(cfg, task, 0)
    budget = slurm.train_budget_seconds(cfg.scinet)
    assert f"export SEGTRAIN_MAX_SECONDS={budget}" in script
    # The timeout backstop must sit *after* the trainer's own deadline, or it
    # kills a healthy run mid-epoch before the clean pause can happen.
    assert f"timeout {budget + 600} segtrain train" in script


def test_output_is_unbuffered(cfg, task):
    """Every block is designed to end at the wall clock.

    SLURM may only flush job output at exit, so without this the tail of every
    log -- the part that says whether the pause was clean -- is what you lose.
    """
    script = slurm.render_train_script(cfg, task, 0)
    assert "export PYTHONUNBUFFERED=1" in script


def test_gpu_job_loads_cuda_but_the_cpu_job_does_not(cfg, task):
    """Trillium's CPU nodes have no cuda module; loading it there fails the job."""
    gpu = slurm.render_train_script(cfg, task, 0)
    cpu = slurm.render_prepare_script(cfg, task)
    assert "module load StdEnv/2023 python/3.11.5 cuda/12.6" in gpu
    # Compare the module lines, not the whole script: tmp_path leaks the test's
    # own name into every path in it.
    assert "module load StdEnv/2023 python/3.11.5\n" in cpu


def test_modules_load_before_the_venv_is_activated(cfg, task):
    """The venv is built against one interpreter; activating first gets another."""
    script = slurm.render_train_script(cfg, task, 0)
    assert script.index("module load") < script.index("source /home/g/grp/you")


def test_dataloader_workers_default_to_the_allocation(cfg, task):
    script = slurm.render_train_script(cfg, task, 0)
    assert 'export nnUNet_n_proc_DA="${SLURM_CPUS_PER_TASK:-${SLURM_CPUS_ON_NODE:-24}}"' \
        in script


def test_dataloader_workers_can_be_pinned(cfg, task):
    sc = replace(cfg.scinet, dataloader_workers=8)
    script = slurm.render_train_script(replace(cfg, scinet=sc), task, 0)
    assert "export nnUNet_n_proc_DA=8" in script


def test_preview_daemon_is_optional(cfg, task):
    with_preview = slurm.render_train_script(cfg, task, 0, preview=True)
    without = slurm.render_train_script(cfg, task, 0, preview=False)
    assert "segtrain preview" in with_preview
    assert "PREVIEW_PID" in with_preview
    assert "segtrain preview" not in without


def test_staging_is_off_by_default_and_guards_the_ram_disk(cfg, task):
    """$SLURM_TMPDIR is RAM on Trillium, so staging spends the job's memory."""
    assert "SLURM_TMPDIR" not in slurm.render_train_script(cfg, task, 0)

    sc = replace(cfg.scinet, stage_to_tmpdir=True)
    staged = slurm.render_train_script(replace(cfg, scinet=sc), task, 0)
    assert "$SLURM_TMPDIR" in staged
    # It must measure the dataset against the cgroup limit rather than trusting
    # df, which reports the RAM disk as the size of physical memory.
    assert "memory.max" in staged
    assert "LIMIT_KB / 3" in staged


def test_epoch_and_iteration_overrides_reach_both_the_env_and_the_cli(cfg, task):
    script = slurm.render_train_script(cfg, task, 0, epochs=5, iterations=3)
    assert "export SEGTRAIN_EPOCHS=5" in script
    assert "export SEGTRAIN_ITERATIONS=3" in script
    assert "--epochs 5" in script
    assert "--iterations 3" in script


def test_prepare_script_optionally_converts_first(cfg, task):
    without = slurm.render_prepare_script(cfg, task)
    with_convert = slurm.render_prepare_script(cfg, task, convert=True)
    assert "segtrain convert" not in without
    assert with_convert.index("segtrain convert") < with_convert.index("segtrain plan")
    assert with_convert.index("segtrain plan") < with_convert.index("segtrain preprocess")


# ------------------------------------------------------------------ config


def test_chain_mode_is_validated():
    with pytest.raises(ConfigError, match="chain_mode"):
        SciNetConfig(chain_mode="magic").validate()


def test_chain_max_must_be_at_least_one():
    with pytest.raises(ConfigError, match="chain_max"):
        SciNetConfig(chain_max=0).validate()


@pytest.mark.parametrize("gpus", [2, 3, 5])
def test_trillium_rejects_partial_gpu_groups(gpus):
    """Trillium schedules whole GPUs: 1, or a multiple of 4. 2 and 3 are refused."""
    with pytest.raises(ConfigError, match="gpus_per_node"):
        SciNetConfig(cluster="trillium", gpus_per_node=gpus).validate()


@pytest.mark.parametrize("gpus", [1, 4, 8])
def test_trillium_accepts_valid_gpu_counts(gpus):
    SciNetConfig(cluster="trillium", gpus_per_node=gpus).validate()


def test_other_clusters_are_not_held_to_trillium_gpu_rules():
    SciNetConfig(cluster="killarney", gpus_per_node=2).validate()


def test_account_is_read_from_the_slurm_environment(monkeypatch, tmp_path):
    """`export SLURM_ACCOUNT=...` in a login profile should be enough."""
    from segtrain.config import load_config

    monkeypatch.setenv("SLURM_ACCOUNT", "rrg-fromenv")
    cfg = load_config(None, {
        "zenodo_root": str(tmp_path), "nnunet_raw": str(tmp_path),
        "nnunet_preprocessed": str(tmp_path), "nnunet_results": str(tmp_path),
        "runs_root": str(tmp_path),
    })
    assert cfg.scinet.account == "rrg-fromenv"


# ----------------------------------------------------------------- submission


def test_submit_chain_makes_one_submission_in_array_mode(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(slurm, "submit",
                        lambda *a, **kw: calls.append((a, kw)) or "1001")

    sc = SciNetConfig(chain_mode="array", chain_max=4)
    assert slurm.submit_chain(sc, tmp_path / "job.sh") == ["1001"]
    assert len(calls) == 1, "the --array directive already creates every block"


def test_submit_chain_links_each_job_to_the_last_in_dependency_mode(monkeypatch, tmp_path):
    calls = []

    def fake_submit(script, args=None, *, dependency=None, cwd=None, hold=False):
        calls.append({"args": args, "dependency": dependency})
        return f"200{len(calls)}"

    monkeypatch.setattr(slurm, "submit", fake_submit)
    sc = SciNetConfig(chain_mode="dependency", chain_max=3)
    ids = slurm.submit_chain(sc, tmp_path / "job.sh")

    assert ids == ["2001", "2002", "2003"]
    assert [c["args"] for c in calls] == [["1"], ["2"], ["3"]]
    # afterany, not afterok: a block killed at the walltime exits nonzero, and
    # that is exactly when the successor is needed. afterok would cancel it.
    assert [c["dependency"] for c in calls] == [None, "afterany:2001", "afterany:2002"]


def test_submit_reports_the_login_node_requirement(monkeypatch, tmp_path):
    def no_sbatch(*a, **kw):
        raise FileNotFoundError("sbatch")

    monkeypatch.setattr(slurm.subprocess, "run", no_sbatch)
    with pytest.raises(slurm.SlurmError, match="login node"):
        slurm.submit(tmp_path / "job.sh")


def test_write_script_is_executable(tmp_path):
    path = slurm.write_script(tmp_path / "sub" / "job.sh", "#!/bin/bash\ntrue\n")
    assert path.is_file()
    assert path.stat().st_mode & stat.S_IXUSR


# -------------------------------------------------------------------- backend


def test_slurm_backend_records_the_job_id(monkeypatch, tmp_path, cfg):
    monkeypatch.setattr(slurm, "submit", lambda *a, **kw: "4242")

    backend = get_backend("slurm", scinet=cfg.scinet)
    job = backend.submit(["echo", "hi"], str(tmp_path / "run"),
                         env={"SEGTRAIN_TASK": "x", "PATH": "/leaked"})

    assert job.job_id == "4242"
    assert job.backend == "slurm"

    script = (tmp_path / "run" / "job.sh").read_text()
    assert "export SEGTRAIN_TASK=x" in script
    # Replaying the caller's whole environment onto the compute node is what
    # `module purge` exists to prevent; only our own variables are exported.
    assert "/leaked" not in script


def test_slurm_backend_needs_the_cluster_config(tmp_path):
    backend = get_backend("slurm")
    with pytest.raises(BackendError, match="scinet"):
        backend.submit(["echo"], str(tmp_path / "run"))


def test_cancel_kills_the_successor_before_the_running_block(monkeypatch, tmp_path, cfg):
    """Order matters: the successor depends on this job with afterany.

    Cancelling the running block first satisfies that dependency and SLURM
    promptly starts the very block the user asked to stop.
    """
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "chain_next.jobid").write_text("9002\n")

    cancelled = []
    monkeypatch.setattr(slurm, "cancel", lambda jid: cancelled.append(jid) or True)

    from segtrain.backends.base import Job

    backend = get_backend("slurm", scinet=cfg.scinet)
    backend.cancel(Job(backend="slurm", command=[], run_dir=str(run_dir), job_id="9001"))

    assert cancelled == ["9002", "9001"]


def test_unknown_backend_names_are_rejected():
    with pytest.raises(BackendError, match="unknown backend"):
        get_backend("modal")
