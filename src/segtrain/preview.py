"""Live-preview daemon: turn the newest checkpoint into something you can look at.

Loss curves tell you a run is converging. They do not tell you that the model has
swapped T11 for T12, or that it segments a beautiful liver and has never once
found the gallbladder. Seeing the segmentation is what catches those, which is
the whole reason for wanting training visible inside Slicer.

This runs as a separate process **on the training machine**, beside the trainer:

    1. watch for a new ``checkpoint_latest.pth``
    2. run inference on a few fixed validation cases
    3. score each structure against ground truth
    4. write the segmentation into ``<run_dir>/previews/`` and emit a preview event

Slicer then only has to download a ~0.3 MB label volume. Keeping inference next
to the GPU is what makes the monitor usable over a slow link, and what lets it
work at all when the GPU is a rented box on the other side of the country.

Running as a separate process rather than inside a trainer hook is deliberate:
inference on a whole volume takes real GPU time, and a crash in preview code --
or a preview that simply takes too long -- must never be able to interrupt a
multi-day training run.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

import nibabel as nib
import numpy as np

from .config import Config, TaskConfig
from .events import EventWriter
from .metrics import dice_dict, score_case

# How long to wait between checks for a new checkpoint. Checkpoints appear every
# `save_every` epochs (nnU-Net default 50), which is minutes at best, so polling
# faster than this buys nothing.
POLL_SECONDS = 30.0


@dataclass
class PreviewTarget:
    """One case to render, resolved to concrete files."""

    case_id: str
    image: Path
    label: Path


def resolve_targets(cfg: Config, task: TaskConfig, cases: Sequence[str]) -> list[PreviewTarget]:
    """Locate the image/label pair for each preview case in the raw dataset."""
    raw = task.raw_dir(cfg)
    targets = []
    for case_id in cases:
        image = raw / "imagesTr" / f"{case_id}_0000.nii.gz"
        label = raw / "labelsTr" / f"{case_id}.nii.gz"
        if not image.is_file():
            # Preview cases are validation cases, so they live in imagesTr. If one
            # is missing, the conversion was subsetted -- skip rather than crash.
            continue
        targets.append(PreviewTarget(case_id, image, label))
    return targets


def checkpoint_mtime(path: Path) -> Optional[float]:
    try:
        return path.stat().st_mtime
    except OSError:
        return None


class PreviewRunner:
    """Loads a checkpoint and renders preview segmentations for a set of cases."""

    def __init__(
        self,
        cfg: Config,
        task: TaskConfig,
        fold: int,
        run_dir: Path,
        device: str = "cuda",
        compute_nsd: bool = False,
    ):
        self.cfg = cfg
        self.task = task
        self.fold = fold
        self.run_dir = Path(run_dir)
        self.device = device
        # NSD needs two distance transforms per structure over the whole volume.
        # For a live preview that is minutes of CPU for information you would not
        # act on differently, so Dice only by default; evaluate.py computes both.
        self.compute_nsd = compute_nsd
        self._predictor = None

    def model_folder(self) -> Path:
        """nnU-Net's output folder base for this task/trainer/plans/configuration."""
        return (
            self.task.results_dir(self.cfg)
            / f"{self.task.trainer}__{self.task.plans_name}__{self.task.configuration}"
        )

    def checkpoint_path(self, name: str = "checkpoint_latest.pth") -> Path:
        return self.model_folder() / f"fold_{self.fold}" / name

    def _load(self, checkpoint_name: str):
        import torch
        from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor

        predictor = nnUNetPredictor(
            tile_step_size=0.5,
            use_gaussian=True,
            # Test-time mirroring costs 8x the inference for a small accuracy gain.
            # Wrong trade for a preview that must not steal GPU time from training.
            use_mirroring=False,
            perform_everything_on_device=(self.device != "cpu"),
            device=torch.device(self.device),
            verbose=False,
            verbose_preprocessing=False,
            allow_tqdm=False,
        )
        predictor.initialize_from_trained_model_folder(
            str(self.model_folder()),
            use_folds=(self.fold,),
            checkpoint_name=checkpoint_name,
        )
        return predictor

    def render(
        self,
        targets: Sequence[PreviewTarget],
        epoch: int,
        writer: EventWriter,
        checkpoint_name: str = "checkpoint_latest.pth",
    ) -> int:
        """Predict, score and emit one preview per target. Returns how many succeeded."""
        predictor = self._load(checkpoint_name)
        previews_dir = self.run_dir / "previews"
        previews_dir.mkdir(parents=True, exist_ok=True)
        names = self.task.label_set.names
        n_ok = 0

        for target in targets:
            try:
                out_stem = previews_dir / f"ep{epoch:04d}_{target.case_id}"
                predictor.predict_from_files(
                    [[str(target.image)]],
                    [str(out_stem)],
                    save_probabilities=False,
                    overwrite=True,
                    num_processes_preprocessing=1,
                    num_processes_segmentation_export=1,
                )
                seg_path = Path(str(out_stem) + ".nii.gz")
                if not seg_path.is_file():
                    writer.log(
                        f"preview for {target.case_id} produced no output", level="warning"
                    )
                    continue

                dice = {}
                if target.label.is_file():
                    pred_img = nib.load(str(seg_path))
                    ref_img = nib.load(str(target.label))
                    spacing = [float(z) for z in ref_img.header.get_zooms()[:3]]
                    scores = score_case(
                        np.asanyarray(pred_img.dataobj).astype(np.uint8),
                        np.asanyarray(ref_img.dataobj).astype(np.uint8),
                        names,
                        spacing,
                        compute_nsd=self.compute_nsd,
                    )
                    dice = dice_dict(scores)

                writer.preview(
                    epoch=epoch,
                    case=target.case_id,
                    # Relative so the monitor can resolve it against whatever path
                    # the run directory has locally or over SSH.
                    seg=str(seg_path.relative_to(self.run_dir)).replace("\\", "/"),
                    dice=dice,
                    reference_image=str(target.image),
                    checkpoint=checkpoint_name,
                )
                n_ok += 1
            except Exception as exc:
                writer.log(
                    f"preview failed for {target.case_id}: {type(exc).__name__}: {exc}",
                    level="error",
                )
        return n_ok


def watch(
    cfg: Config,
    task: TaskConfig,
    fold: int,
    cases: Optional[Sequence[str]] = None,
    device: str = "cuda",
    poll_seconds: float = POLL_SECONDS,
    max_iterations: Optional[int] = None,
    compute_nsd: bool = False,
) -> None:
    """Follow a training run, rendering a preview each time the checkpoint changes.

    Exits when the run emits a terminal event, or after ``max_iterations`` polls
    (used by tests so this never blocks a suite forever).
    """
    run_dir = task.run_dir(cfg, fold)
    run_dir.mkdir(parents=True, exist_ok=True)

    runner = PreviewRunner(cfg, task, fold, run_dir, device=device, compute_nsd=compute_nsd)
    targets = resolve_targets(cfg, task, cases or cfg.preview.cases)

    writer = EventWriter(run_dir)
    if not targets:
        writer.log("preview daemon: no preview cases resolved; exiting", level="warning")
        writer.close()
        return

    writer.log(
        f"preview daemon watching {runner.checkpoint_path()} "
        f"for cases {', '.join(t.case_id for t in targets)}"
    )

    last_seen: Optional[float] = None
    iterations = 0
    try:
        while True:
            if max_iterations is not None and iterations >= max_iterations:
                break
            iterations += 1

            ckpt = runner.checkpoint_path()
            mtime = checkpoint_mtime(ckpt)
            if mtime is not None and mtime != last_seen:
                # A checkpoint being written is not a checkpoint finished being
                # written. Wait for the size to settle before torch.load sees a
                # truncated file.
                if _settled(ckpt):
                    last_seen = mtime
                    epoch = _epoch_from_events(run_dir)
                    runner.render(targets, epoch, writer)
            if _run_finished(run_dir):
                break
            time.sleep(poll_seconds)
    except KeyboardInterrupt:
        writer.log("preview daemon interrupted", level="warning")
    finally:
        writer.close()


def _settled(path: Path, checks: int = 3, delay: float = 1.0) -> bool:
    """True once the file's size stops changing across consecutive checks."""
    try:
        last = path.stat().st_size
    except OSError:
        return False
    for _ in range(checks):
        time.sleep(delay)
        try:
            size = path.stat().st_size
        except OSError:
            return False
        if size != last:
            last = size
            continue
        return True
    return False


def _epoch_from_events(run_dir: Path) -> int:
    """Best-known current epoch, read from the trainer's own event stream."""
    from .events import read_run

    try:
        state = read_run(run_dir)
        return int(state.current_epoch or 0)
    except Exception:
        return 0


def _run_finished(run_dir: Path) -> bool:
    from .events import read_run

    try:
        return read_run(run_dir).finished
    except Exception:
        return False


def preview_once(
    cfg: Config,
    task: TaskConfig,
    fold: int,
    cases: Optional[Sequence[str]] = None,
    device: str = "cuda",
    checkpoint_name: str = "checkpoint_latest.pth",
    compute_nsd: bool = False,
) -> int:
    """Render a single round of previews from the current checkpoint and return."""
    run_dir = task.run_dir(cfg, fold)
    runner = PreviewRunner(cfg, task, fold, run_dir, device=device, compute_nsd=compute_nsd)
    targets = resolve_targets(cfg, task, cases or cfg.preview.cases)
    if not targets:
        raise RuntimeError("no preview cases could be resolved in the converted dataset")
    ckpt = runner.checkpoint_path(checkpoint_name)
    if not ckpt.is_file():
        raise FileNotFoundError(f"no checkpoint at {ckpt}")

    with EventWriter(run_dir) as writer:
        return runner.render(targets, _epoch_from_events(run_dir), writer, checkpoint_name)


def env_for_training(run_dir: Path, task_name: str, epochs: Optional[int] = None) -> dict:
    """Environment the trainer needs to find its run directory."""
    env = {"SEGTRAIN_RUN_DIR": str(run_dir), "SEGTRAIN_TASK": task_name}
    if epochs is not None:
        env["SEGTRAIN_EPOCHS"] = str(int(epochs))
    return {**os.environ, **env}
