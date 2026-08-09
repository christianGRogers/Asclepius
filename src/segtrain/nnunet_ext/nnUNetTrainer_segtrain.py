"""nnU-Net trainer that publishes a structured event stream while it trains.

This is a thin instrumentation layer, not a change to the training recipe. Every
hook calls ``super()`` and then reports what happened; the loss, optimizer,
schedule and augmentation are untouched nnU-Net defaults, which is what the
reference paper's method requires.

Why instrument the trainer rather than parse its log file: the log is formatted
for humans and its layout is not a stable interface, whereas ``self.logger``
holds the exact values nnU-Net itself uses. Reading them directly means the
numbers in Slicer are the numbers nnU-Net trained on, not a re-derivation.
(``segtrain.logparse`` still offers a log-scraping fallback for runs launched
outside this pipeline.)

Configured entirely by environment variable, because nnU-Net constructs trainers
with a fixed signature we cannot extend:

``SEGTRAIN_RUN_DIR``
    Where events.jsonl and previews/ go. Defaults to nnU-Net's output folder.
``SEGTRAIN_EPOCHS``
    Override the epoch count. Used for smoke tests; leave unset for real runs.
``SEGTRAIN_ITERATIONS``
    Override iterations per epoch (nnU-Net default 250). Only for smoke tests --
    lowering it changes the effective schedule, since nnU-Net's polynomial LR
    decay is defined over epochs, not steps.
``SEGTRAIN_TASK``
    Task name, recorded in the run_start event for display.
"""

from __future__ import annotations

import os
from typing import Optional

import numpy as np
import torch
from nnunetv2.training.nnUNetTrainer.nnUNetTrainer import nnUNetTrainer

# Absolute import: nnU-Net imports this file as a top-level module.
from segtrain.events import EventWriter


def _safe(logger, key: str, step: int = -1) -> Optional[float]:
    """Read one scalar from nnU-Net's logger without ever raising.

    Monitoring must not be able to kill a multi-day training run, so every read
    that feeds the event stream is defensive: a missing or malformed value
    becomes None and the epoch event is emitted anyway.
    """
    try:
        value = logger.get_value(key, step=step)
    except Exception:
        return None
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_list(logger, key: str, step: int = -1) -> Optional[list]:
    try:
        value = logger.get_value(key, step=step)
    except Exception:
        return None
    if value is None:
        return None
    try:
        return [float(v) for v in np.asarray(value).ravel()]
    except Exception:
        return None


class nnUNetTrainer_segtrain(nnUNetTrainer):
    """Default nnU-Net training, plus an events.jsonl the Slicer monitor reads."""

    def __init__(
        self,
        plans: dict,
        configuration: str,
        fold: int,
        dataset_json: dict,
        # Mirrors nnUNetTrainer's own signature exactly; nnU-Net constructs
        # trainers positionally, so this must not drift from the base class.
        device: torch.device = torch.device("cuda"),  # noqa: B008
    ):
        super().__init__(plans, configuration, fold, dataset_json, device)

        epochs_override = os.environ.get("SEGTRAIN_EPOCHS")
        if epochs_override:
            try:
                self.num_epochs = int(epochs_override)
            except ValueError:
                pass

        iters_override = os.environ.get("SEGTRAIN_ITERATIONS")
        if iters_override:
            try:
                n = int(iters_override)
                self.num_iterations_per_epoch = n
                # Keep at least one validation step so pseudo-Dice is still
                # produced; without it the event stream has no quality signal.
                self.num_val_iterations_per_epoch = max(1, n // 5)
            except ValueError:
                pass

        self._events: Optional[EventWriter] = None
        self._run_dir = os.environ.get("SEGTRAIN_RUN_DIR") or self.output_folder
        self._task_name = os.environ.get("SEGTRAIN_TASK", "")

    @property
    def _is_main(self) -> bool:
        """Only rank 0 writes events; under DDP every rank runs these hooks."""
        return getattr(self, "local_rank", 0) == 0

    def _writer(self) -> Optional[EventWriter]:
        if not self._is_main:
            return None
        if self._events is None:
            try:
                self._events = EventWriter(self._run_dir)
            except Exception as exc:
                self.print_to_log_file(f"[segtrain] could not open event stream: {exc}")
                return None
        return self._events

    def _class_names(self) -> list:
        """Structure names in the order nnU-Net reports pseudo-Dice.

        nnU-Net's per-class Dice array covers foreground classes in label order,
        so dropping background and sorting by index recovers the labels. Sending
        the names once in run_start lets the monitor render a named table instead
        of a column of anonymous numbers.
        """
        labels = self.dataset_json.get("labels", {})
        fg = [(name, idx) for name, idx in labels.items() if idx != 0 and name != "background"]
        fg.sort(key=lambda kv: kv[1] if isinstance(kv[1], int) else 0)
        return [name for name, _ in fg]

    def on_train_start(self) -> None:
        super().on_train_start()
        w = self._writer()
        if w is None:
            return
        conf = self.configuration_manager
        w.run_start(
            task=self._task_name or self.plans_manager.dataset_name,
            dataset=self.plans_manager.dataset_name,
            configuration=self.configuration_name,
            fold=self.fold,
            epochs=int(self.num_epochs),
            device=str(self.device),
            class_names=self._class_names(),
            patch_size=[int(x) for x in conf.patch_size],
            batch_size=int(conf.batch_size),
            spacing=[float(x) for x in conf.spacing],
            output_folder=str(self.output_folder),
            trainer=type(self).__name__,
        )

    def on_epoch_end(self) -> None:
        # nnU-Net increments current_epoch inside on_epoch_end, so the epoch this
        # data belongs to must be captured before delegating.
        epoch = int(self.current_epoch)
        super().on_epoch_end()

        w = self._writer()
        if w is None:
            return
        try:
            start = _safe(self.logger, "epoch_start_timestamps")
            end = _safe(self.logger, "epoch_end_timestamps")
            w.epoch(
                epoch=epoch,
                train_loss=_safe(self.logger, "train_losses"),
                val_loss=_safe(self.logger, "val_losses"),
                pseudo_dice=_safe_list(self.logger, "dice_per_class_or_region"),
                lr=_safe(self.logger, "lrs"),
                epoch_seconds=(end - start) if (start and end) else None,
                mean_fg_dice=_safe(self.logger, "mean_fg_dice"),
                ema_fg_dice=_safe(self.logger, "ema_fg_dice"),
            )
        except Exception as exc:
            self.print_to_log_file(f"[segtrain] failed to emit epoch event: {exc}")

    def save_checkpoint(self, filename: str) -> None:
        super().save_checkpoint(filename)
        w = self._writer()
        if w is None:
            return
        try:
            name = os.path.basename(str(filename))
            # 'best' vs 'latest' matters downstream: the preview daemon follows
            # 'latest' so the picture tracks training, while packaging uses 'best'.
            kind = "best" if "best" in name else ("final" if "final" in name else "latest")
            w.checkpoint(epoch=int(self.current_epoch), path=str(filename), kind=kind)
        except Exception as exc:
            self.print_to_log_file(f"[segtrain] failed to emit checkpoint event: {exc}")

    def on_train_end(self) -> None:
        super().on_train_end()
        w = self._writer()
        if w is None:
            return
        try:
            w.run_end(status="completed", epochs_completed=int(self.current_epoch))
        finally:
            w.close()
            self._events = None


class nnUNetTrainer_segtrain_5epochs(nnUNetTrainer_segtrain):
    """Five epochs, for proving the pipeline end to end without burning GPU-days.

    Used by the CPU smoke test: it exercises conversion, planning, preprocessing,
    the event stream, the preview daemon and the Slicer monitor in a few minutes.
    """

    def __init__(self, plans, configuration, fold, dataset_json,
                 device=torch.device("cuda")):  # noqa: B008
        super().__init__(plans, configuration, fold, dataset_json, device)
        self.num_epochs = int(os.environ.get("SEGTRAIN_EPOCHS", "5"))
