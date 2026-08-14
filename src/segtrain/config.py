"""Configuration loading: dataset paths, task definitions, label sets.

Resolution order for every path setting, highest priority first:

    1. explicit CLI flag
    2. environment variable (nnU-Net's own names: nnUNet_raw, nnUNet_preprocessed,
       nnUNet_results -- so a box already set up for nnU-Net needs no config file)
    3. configs/dataset.local.yaml   (gitignored, per-machine)
    4. configs/dataset.yaml         (tracked template)

This is what lets the identical repo drive a laptop, a rented GPU box, and a
cluster without editing tracked files.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

# Repo root, found relative to this file: src/segtrain/config.py -> repo/
REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "configs"
LABELS_DIR = CONFIG_DIR / "labels"
TASKS_DIR = CONFIG_DIR / "tasks"

# nnU-Net reads these from the environment. We set them from our config so the
# user never has to keep two sources of truth in sync.
ENV_BY_KEY = {
    "nnunet_raw": "nnUNet_raw",
    "nnunet_preprocessed": "nnUNet_preprocessed",
    "nnunet_results": "nnUNet_results",
}

VALID_LINK_MODES = ("hardlink", "symlink", "copy")
VALID_OVERLAP_POLICIES = ("smaller_wins", "label_order")


class ConfigError(RuntimeError):
    """Raised for a malformed or inconsistent configuration."""


def _read_yaml(path: Path) -> dict:
    # utf-8-sig: the dataset's own meta.csv ships with a BOM, and hand-edited
    # config files on Windows frequently pick one up too. Tolerate it.
    with open(path, encoding="utf-8-sig") as fh:
        data = yaml.safe_load(fh)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: expected a YAML mapping, got {type(data).__name__}")
    return data


@dataclass
class PreviewConfig:
    """Which cases the live-preview daemon renders, and how often."""

    cases: list[str] = field(default_factory=list)
    every_n_epochs: int = 25
    skip_if_busy: bool = True


@dataclass
class SciNetConfig:
    """How a run is submitted to SLURM on a SciNet cluster.

    Everything a job script needs, and nothing about *where* data lives -- the
    nnU-Net roots are ordinary ``Config`` paths, because on a cluster they are
    ordinary paths on a shared filesystem. That is the substantive difference
    from a serverless backend: there is no volume to mount and no container
    boundary, so the same ``segtrain`` commands run on the login node and on the
    compute node against the same paths.

    ``account`` is the only field with no sensible default. SLURM on the Alliance
    clusters rejects a job with no ``--account`` when the user belongs to more
    than one allocation, which every user with a RAC does.
    """

    cluster: str = "trillium"
    account: str = ""
    # Both default to empty, and on Trillium they must stay that way: "Do not
    # specify this partition explicitly; you must allow the scheduler to select
    # the appropriate partition for your job."
    gpu_partition: str = ""
    cpu_partition: str = ""

    # -- the GPU training job
    nodes: int = 1
    # Trillium schedules whole GPUs: 1 (a quarter node, 24 cores, ~188 GiB) or a
    # multiple of 4. 2 and 3 are rejected, and MIG is unavailable. nnU-Net's
    # default plan targets 8 GB of VRAM, so one 80 GB H100 is already far more
    # than this workload can use -- asking for four would idle three of them.
    gpus_per_node: int = 1
    # 0 means "do not emit --cpus-per-task". None of the Trillium GPU examples
    # request cores, because the cores come with the GPU; the job reads
    # $SLURM_CPUS_ON_NODE instead of asserting a number.
    cpus_per_task: int = 0
    # Ignored on Trillium -- "Memory requests are ignored... Do not use --mem".
    # Kept for other clusters.
    mem: str = ""
    # The cap is 24 h. Ten minutes under it leaves room for the job to be placed
    # and to shut down without SLURM's own kill landing first.
    walltime: str = "23:50:00"
    # Subtracted from walltime to get the trainer's budget. Must cover module
    # load, venv, staging, nnU-Net's unpacking, one final epoch (the deadline is
    # only tested at epoch boundaries) and a ~400 MB checkpoint write.
    pause_margin_seconds: int = 30 * 60
    # nnU-Net checkpoints every 50 epochs by default; at ~2 min/epoch an unclean
    # kill -- preemption, node failure -- would cost ~100 minutes. 25 halves that
    # for negligible I/O.
    save_every: int = 25
    # How the chain is built. "array" is one `sbatch --array=1-N%1`; "dependency"
    # is N jobs each waiting on the last. Both are submitted from a login node,
    # because Trillium forbids a job from submitting anything. See segtrain.slurm.
    chain_mode: str = "array"
    # How many walltime blocks the chain may use. Also the ceiling: a run that
    # never reports completion stops here rather than queueing forever. Trillium
    # allows 500 submitted jobs, so this is our limit, not the scheduler's.
    chain_max: int = 3
    # nnU-Net sizes its augmentation pool from the machine's core count unless
    # told otherwise, which on a shared node oversubscribes the allocation 4x.
    # 0 means "read $SLURM_CPUS_ON_NODE at run time", which is what you want.
    dataloader_workers: int = 0
    # Copy the preprocessed task into $SLURM_TMPDIR and train from there.
    # Off by default, and read segtrain.slurm before turning it on: Trillium
    # nodes have no local disk, so $SLURM_TMPDIR is a RAM disk that spends the
    # job's own memory. Reasonable for Stage 1 at 3 mm (~10 GB of ~188 GiB);
    # not for the 1.5 mm groups (~75 GB, roughly doubled by unpacking).
    stage_to_tmpdir: bool = False

    # -- the CPU-only plan/preprocess job
    prepare_walltime: str = "12:00:00"
    prepare_cpus: int = 0

    # -- environment
    # Loaded by every job. Keep cuda out of this list: Trillium's CPU nodes have
    # no cuda module, and the prepare job would fail at `module load`.
    modules: list[str] = field(default_factory=list)
    # Loaded by GPU jobs only, on top of `modules`.
    gpu_modules: list[str] = field(default_factory=list)
    # Trillium-specific: build this in $HOME, which compute nodes can read.
    # $SCRATCH "may get partially deleted", and $SLURM_TMPDIR is RAM.
    venv: str = ""
    setup_commands: list[str] = field(default_factory=list)
    sbatch_extra: list[str] = field(default_factory=list)

    mail_user: str = ""
    mail_type: str = "FAIL,TIME_LIMIT"

    # Only used to print a paste-ready address for the Slicer monitor.
    login_host: str = ""

    def validate(self) -> None:
        from .slurm import CHAIN_MODES

        if self.chain_mode not in CHAIN_MODES:
            raise ConfigError(
                f"scinet.chain_mode must be one of {CHAIN_MODES}, "
                f"got {self.chain_mode!r}"
            )
        if self.chain_max < 1:
            raise ConfigError(f"scinet.chain_max must be at least 1, got {self.chain_max}")
        # Trillium rejects 2 or 3 GPUs outright, and the error comes back from
        # sbatch as a generic configuration message that takes a while to place.
        if self.cluster == "trillium" and self.gpus_per_node not in (1, 4, 8, 12, 16):
            raise ConfigError(
                f"scinet.gpus_per_node={self.gpus_per_node} is invalid on Trillium: "
                "GPUs are scheduled whole, so ask for 1 (a quarter node) or a "
                "multiple of 4. 2 and 3 are rejected."
            )

    def budget_seconds(self) -> int:
        from .slurm import train_budget_seconds

        return train_budget_seconds(self)

    def run_address(self, run_dir: str) -> str:
        """``user@host:/path`` for the Slicer monitor, or the bare path."""
        return f"{self.login_host}:{run_dir}" if self.login_host else str(run_dir)


@dataclass
class Config:
    """Resolved paths and settings for one invocation."""

    zenodo_root: Path
    nnunet_raw: Path
    nnunet_preprocessed: Path
    nnunet_results: Path
    runs_root: Path
    link_mode: str = "hardlink"
    convert_workers: int = 0
    overlap_policy: str = "smaller_wins"
    reader_writer: str = "NibabelIOWithReorient"
    preview: PreviewConfig = field(default_factory=PreviewConfig)
    scinet: SciNetConfig = field(default_factory=SciNetConfig)

    @property
    def meta_csv(self) -> Path:
        return self.zenodo_root / "meta.csv"

    def subject_dir(self, case_id: str) -> Path:
        return self.zenodo_root / case_id

    def n_workers(self) -> int:
        return self.convert_workers or (os.cpu_count() or 4)

    def export_nnunet_env(self) -> dict[str, str]:
        """Environment for a child nnU-Net process.

        nnU-Net resolves its roots from the environment at import time, so this
        must be applied to the subprocess env, not merely to os.environ after
        nnU-Net has already been imported.
        """
        env = dict(os.environ)
        for key, var in ENV_BY_KEY.items():
            env[var] = str(getattr(self, key))
        return env

    def validate(self, *, require_data: bool = False) -> None:
        if self.link_mode not in VALID_LINK_MODES:
            raise ConfigError(
                f"link_mode must be one of {VALID_LINK_MODES}, got {self.link_mode!r}"
            )
        if self.overlap_policy not in VALID_OVERLAP_POLICIES:
            raise ConfigError(
                f"overlap_policy must be one of {VALID_OVERLAP_POLICIES}, "
                f"got {self.overlap_policy!r}"
            )
        self.scinet.validate()
        if require_data:
            if not self.zenodo_root.is_dir():
                raise ConfigError(f"zenodo_root does not exist: {self.zenodo_root}")
            if not self.meta_csv.is_file():
                raise ConfigError(
                    f"meta.csv not found at {self.meta_csv} -- is zenodo_root correct?"
                )


def load_config(
    config_path: Optional[Path] = None,
    overrides: Optional[dict[str, Any]] = None,
) -> Config:
    """Build a Config from file, environment, and explicit overrides."""
    if config_path is not None:
        base = _read_yaml(Path(config_path))
    else:
        local = CONFIG_DIR / "dataset.local.yaml"
        tracked = CONFIG_DIR / "dataset.yaml"
        chosen = local if local.is_file() else tracked
        if not chosen.is_file():
            raise ConfigError(f"no configuration found at {local} or {tracked}")
        base = _read_yaml(chosen)

    # Environment beats the file for the three nnU-Net roots.
    for key, var in ENV_BY_KEY.items():
        if os.environ.get(var):
            base[key] = os.environ[var]

    # CLI flags beat everything. Ignore None so unset flags don't clobber.
    for key, value in (overrides or {}).items():
        if value is not None:
            base[key] = value

    preview_raw = base.get("preview") or {}
    preview = PreviewConfig(
        cases=list(preview_raw.get("cases") or []),
        every_n_epochs=int(preview_raw.get("every_n_epochs", 25)),
        skip_if_busy=bool(preview_raw.get("skip_if_busy", True)),
    )

    scinet_raw = base.get("scinet") or {}
    defaults = SciNetConfig()
    scinet_cfg = SciNetConfig(
        cluster=str(scinet_raw.get("cluster") or defaults.cluster),
        # SLURM_ACCOUNT is the variable sbatch itself reads, so honouring it here
        # means `export SLURM_ACCOUNT=...` in a login profile is enough and the
        # account never has to be written into a config file at all.
        account=str(scinet_raw.get("account")
                    or os.environ.get("SLURM_ACCOUNT", "")),
        gpu_partition=str(scinet_raw.get("gpu_partition") or ""),
        cpu_partition=str(scinet_raw.get("cpu_partition") or ""),
        nodes=int(scinet_raw.get("nodes", defaults.nodes)),
        gpus_per_node=int(scinet_raw.get("gpus_per_node", defaults.gpus_per_node)),
        cpus_per_task=int(scinet_raw.get("cpus_per_task", defaults.cpus_per_task)),
        mem=str(scinet_raw.get("mem") or ""),
        walltime=str(scinet_raw.get("walltime") or defaults.walltime),
        pause_margin_seconds=int(scinet_raw.get("pause_margin_seconds",
                                               defaults.pause_margin_seconds)),
        save_every=int(scinet_raw.get("save_every", defaults.save_every)),
        chain_mode=str(scinet_raw.get("chain_mode") or defaults.chain_mode),
        chain_max=int(scinet_raw.get("chain_max", defaults.chain_max)),
        dataloader_workers=int(scinet_raw.get("dataloader_workers",
                                              defaults.dataloader_workers)),
        stage_to_tmpdir=bool(scinet_raw.get("stage_to_tmpdir",
                                            defaults.stage_to_tmpdir)),
        prepare_walltime=str(scinet_raw.get("prepare_walltime")
                             or defaults.prepare_walltime),
        prepare_cpus=int(scinet_raw.get("prepare_cpus", defaults.prepare_cpus)),
        modules=[str(m) for m in (scinet_raw.get("modules") or [])],
        gpu_modules=[str(m) for m in (scinet_raw.get("gpu_modules") or [])],
        venv=str(scinet_raw.get("venv") or ""),
        setup_commands=[str(c) for c in (scinet_raw.get("setup_commands") or [])],
        sbatch_extra=[str(c) for c in (scinet_raw.get("sbatch_extra") or [])],
        mail_user=str(scinet_raw.get("mail_user") or ""),
        mail_type=str(scinet_raw.get("mail_type") or defaults.mail_type),
        login_host=str(scinet_raw.get("login_host") or ""),
    )

    required = ["zenodo_root", "nnunet_raw", "nnunet_preprocessed", "nnunet_results", "runs_root"]
    missing = [k for k in required if not base.get(k)]
    if missing:
        raise ConfigError(f"missing required config keys: {', '.join(missing)}")

    cfg = Config(
        zenodo_root=Path(base["zenodo_root"]).expanduser(),
        nnunet_raw=Path(base["nnunet_raw"]).expanduser(),
        nnunet_preprocessed=Path(base["nnunet_preprocessed"]).expanduser(),
        nnunet_results=Path(base["nnunet_results"]).expanduser(),
        runs_root=Path(base["runs_root"]).expanduser(),
        link_mode=str(base.get("link_mode", "hardlink")),
        convert_workers=int(base.get("convert_workers", 0)),
        overlap_policy=str(base.get("overlap_policy", "smaller_wins")),
        reader_writer=str(base.get("reader_writer", "NibabelIOWithReorient")),
        preview=preview,
        scinet=scinet_cfg,
    )
    cfg.validate()
    return cfg


@dataclass
class LabelSet:
    """An ordered, 1-based mapping of structure name to label index.

    The order is a trained model's output-channel order. Once a model exists it
    is frozen: reordering silently remaps every prediction.
    """

    name: str
    labels: dict[str, int]

    @property
    def names(self) -> list[str]:
        """Structure names in label-index order."""
        return [n for n, _ in sorted(self.labels.items(), key=lambda kv: kv[1])]

    @property
    def n_classes(self) -> int:
        """Foreground classes, excluding background."""
        return len(self.labels)

    def index_of(self, name: str) -> int:
        return self.labels[name]

    def name_of(self, index: int) -> str:
        for n, i in self.labels.items():
            if i == index:
                return n
        raise KeyError(f"no structure with label index {index} in set {self.name!r}")

    def to_nnunet_labels(self) -> dict[str, int]:
        """dataset.json 'labels' block: background plus each structure."""
        out: dict[str, int] = {"background": 0}
        for n in self.names:
            out[n] = self.labels[n]
        return out


def load_label_set(name: str, labels_dir: Optional[Path] = None) -> LabelSet:
    path = (labels_dir or LABELS_DIR) / f"{name}.yaml"
    if not path.is_file():
        available = sorted(p.stem for p in (labels_dir or LABELS_DIR).glob("*.yaml"))
        raise ConfigError(
            f"unknown label set {name!r}; available: {', '.join(available) or 'none'}"
        )

    data = _read_yaml(path)
    labels = data.get("labels")
    if not isinstance(labels, dict) or not labels:
        raise ConfigError(f"{path}: 'labels' must be a non-empty mapping")

    labels = {str(k): int(v) for k, v in labels.items()}

    # These invariants are what convert.py and the trained model both rely on.
    # Catching a break here is far cheaper than discovering it after a 2-day run.
    indices = sorted(labels.values())
    expected = list(range(1, len(labels) + 1))
    if indices != expected:
        raise ConfigError(
            f"{path}: label indices must be contiguous 1..{len(labels)}; "
            f"got {indices[:5]}{'...' if len(indices) > 5 else ''}"
        )
    declared = data.get("count")
    if declared is not None and int(declared) != len(labels):
        raise ConfigError(f"{path}: declared count {declared} != {len(labels)} labels")

    return LabelSet(name=data.get("name", name), labels=labels)


@dataclass
class TaskConfig:
    """One nnU-Net Dataset: which structures, at what resolution, trained how."""

    dataset_id: int
    dataset_name: str
    label_set: LabelSet
    spacing: tuple[float, float, float]
    configuration: str = "3d_fullres"
    trainer: str = "nnUNetTrainer_segtrain"
    plans_name: str = "nnUNetPlans"
    epochs: int = 1000
    folds: list[int] = field(default_factory=lambda: [0])
    source_path: Optional[Path] = None

    @property
    def nnunet_name(self) -> str:
        """nnU-Net's directory name, e.g. 'Dataset701_Total3mm'."""
        return f"Dataset{self.dataset_id:03d}_{self.dataset_name}"

    def raw_dir(self, cfg: Config) -> Path:
        return cfg.nnunet_raw / self.nnunet_name

    def preprocessed_dir(self, cfg: Config) -> Path:
        return cfg.nnunet_preprocessed / self.nnunet_name

    def results_dir(self, cfg: Config) -> Path:
        return cfg.nnunet_results / self.nnunet_name

    def run_dir(self, cfg: Config, fold: int) -> Path:
        """Where events.jsonl and previews/ live for one fold of this task."""
        return cfg.runs_root / f"{self.nnunet_name}__fold{fold}"


def _task_files(tasks_dir: Optional[Path] = None) -> list[Path]:
    return sorted((tasks_dir or TASKS_DIR).glob("Dataset*.yaml"))


def load_task(
    ref: str | int,
    tasks_dir: Optional[Path] = None,
    labels_dir: Optional[Path] = None,
) -> TaskConfig:
    """Load a task by dataset id (701), name (Organs), or full nnU-Net name."""
    ref_s = str(ref)
    candidates = _task_files(tasks_dir)
    if not candidates:
        raise ConfigError(f"no task configs found in {tasks_dir or TASKS_DIR}")

    match: Optional[Path] = None
    for path in candidates:
        # Filename is Dataset<id>_<name>.yaml -- match on either part so
        # `--task 701`, `--task Organs` and `--task Dataset702_Organs` all work.
        m = re.match(r"Dataset(\d+)_(.+)", path.stem)
        if not m:
            continue
        ds_id, ds_name = m.group(1), m.group(2)
        if ref_s == path.stem or ref_s == ds_id or ref_s.lstrip("0") == ds_id.lstrip("0"):
            match = path
            break
        if ref_s.lower() == ds_name.lower():
            match = path
            break
    if match is None:
        known = ", ".join(p.stem for p in candidates)
        raise ConfigError(f"unknown task {ref!r}; available: {known}")

    data = _read_yaml(match)
    for key in ("dataset_id", "dataset_name", "label_set", "spacing"):
        if key not in data:
            raise ConfigError(f"{match}: missing required key {key!r}")

    spacing = data["spacing"]
    if not isinstance(spacing, (list, tuple)) or len(spacing) != 3:
        raise ConfigError(f"{match}: spacing must be a list of 3 numbers, got {spacing!r}")

    return TaskConfig(
        dataset_id=int(data["dataset_id"]),
        dataset_name=str(data["dataset_name"]),
        label_set=load_label_set(str(data["label_set"]), labels_dir=labels_dir),
        spacing=(float(spacing[0]), float(spacing[1]), float(spacing[2])),
        configuration=str(data.get("configuration", "3d_fullres")),
        trainer=str(data.get("trainer", "nnUNetTrainer_segtrain")),
        plans_name=str(data.get("plans_name", "nnUNetPlans")),
        epochs=int(data.get("epochs", 1000)),
        folds=[int(f) for f in (data.get("folds") or [0])],
        source_path=match,
    )


def list_tasks(tasks_dir: Optional[Path] = None) -> list[str]:
    return [p.stem for p in _task_files(tasks_dir)]
