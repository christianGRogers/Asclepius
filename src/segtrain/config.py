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
class RemoteConfig:
    """The rented GPU instance: how to reach it and where things live on it."""

    host: str = ""
    identity_file: Optional[str] = None
    root: str = "/home/ubuntu/segtrain"
    python: str = "python3"
    # Lambda images ship a conda env with torch already matched to the driver;
    # creating a fresh venv would mean re-downloading a CUDA torch build on the
    # clock. `--system-site-packages` keeps that and layers our deps on top.
    venv: str = "/home/ubuntu/segtrain/.venv"
    ssh_options: list[str] = field(default_factory=list)

    @property
    def configured(self) -> bool:
        return bool(self.host)

    @property
    def data_root(self) -> str:
        return f"{self.root}/data"

    @property
    def nnunet_raw(self) -> str:
        return f"{self.data_root}/nnUNet_raw"

    @property
    def nnunet_preprocessed(self) -> str:
        return f"{self.data_root}/nnUNet_preprocessed"

    @property
    def nnunet_results(self) -> str:
        return f"{self.data_root}/nnUNet_results"

    @property
    def runs_root(self) -> str:
        return f"{self.root}/runs"

    @property
    def repo(self) -> str:
        return f"{self.root}/segmentator-train"

    def ssh_args(self) -> list[str]:
        """Base ssh/scp arguments: identity, batch mode, keepalives.

        ServerAliveInterval matters here -- a training run is monitored for days
        over a home connection, and without keepalives an idle control channel
        gets dropped by NAT long before anything interesting happens.
        """
        args = ["-o", "BatchMode=yes", "-o", "ServerAliveInterval=30",
                "-o", "ServerAliveCountMax=6"]
        if self.identity_file:
            # IdentitiesOnly stops ssh offering every key in the agent first and
            # tripping the server's MaxAuthTries before reaching this one.
            args += ["-i", str(self.identity_file), "-o", "IdentitiesOnly=yes"]
        args += list(self.ssh_options)
        return args


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
    remote: RemoteConfig = field(default_factory=RemoteConfig)

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

    remote_raw = base.get("remote") or {}
    remote = RemoteConfig(
        host=str(remote_raw.get("host") or ""),
        identity_file=(str(remote_raw["identity_file"])
                       if remote_raw.get("identity_file") else None),
        root=str(remote_raw.get("root") or "/home/ubuntu/segtrain"),
        python=str(remote_raw.get("python") or "python3"),
        venv=str(remote_raw.get("venv")
                 or f"{remote_raw.get('root') or '/home/ubuntu/segtrain'}/.venv"),
        ssh_options=list(remote_raw.get("ssh_options") or []),
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
        remote=remote,
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
