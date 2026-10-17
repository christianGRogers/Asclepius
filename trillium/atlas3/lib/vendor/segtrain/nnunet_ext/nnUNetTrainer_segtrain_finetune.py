"""The wave fine-tune trainer (Round 6, A17a; Atlas v8 §2.7.3).

``nnUNetTrainer_segtrain_coronary`` (fixed CT window checked, no mirroring, val softmax saved,
sealed refusal, event stream, wall-clock pause and chain resume) plus the two things a warm start
of the same 4 + 1 classes needs and stock nnU-Net does not have:

1. **The whole network is loaded, output heads included.** ``-pretrained_weights`` skips every
   ``.seg_layers.`` key, so the deep-supervision heads would restart from random. Here the source
   checkpoint is named by ``SEGTRAIN_FINETUNE_FROM`` and loaded by
   :func:`segtrain.nnunet_ext.finetune_load.load_finetune_source`, which refuses unless plans,
   normalisation, output classes and state-dict keys are identical, loads strictly, and verifies
   every tensor bitwise. **Do not also pass** ``-pretrained_weights``: nnU-Net would then overwrite
   the body (not the heads) from that file after this load.
2. **A linear LR warm-up over a stated number of iterations, then poly decay**
   (:mod:`segtrain.nnunet_ext.finetune_schedule`), stepped every iteration rather than every
   epoch. Peak 1e-2 (A17b primary arm); ``nnUNetTrainer_segtrain_finetune_lr1e3`` is the
   pre-registered 1e-3 fallback arm (Foxtrot F2), a separate class so its results folder never
   collides with the primary arm's. ``SEGTRAIN_WARMUP_ITERS`` (default 2500 = 10 epochs x 250)
   sets the warm-up; ``SEGTRAIN_EPOCHS`` (default 250 here) the length.

Both the load (source path, sha256, epoch, tensor and head counts) and the schedule (peak, warm-up,
total, first/end-of-warm-up/last LR) go to the training log and to ``events.jsonl``; the LR of
every epoch is in the usual epoch events.

A resumed chain block (``--c``) continues from its own ``checkpoint_latest.pth``; the source is
then not needed and, if given, is overwritten by the resume load.
"""

from __future__ import annotations

import os

import torch

from segtrain.nnunet_ext.finetune_load import load_finetune_source
from segtrain.nnunet_ext.finetune_schedule import DEFAULT_WARMUP_ITERS, WarmupPolyScheduler

# Absolute import: nnU-Net imports this file as a top-level module.
from segtrain.nnunet_ext.nnUNetTrainer_segtrain_coronary import nnUNetTrainer_segtrain_coronary

FINETUNE_EPOCHS = 250


class nnUNetTrainer_segtrain_finetune(nnUNetTrainer_segtrain_coronary):
    """Warm fine-tune of the master model: full load (heads kept), warm-up + poly, peak 1e-2."""

    PEAK_LR = 1e-2

    def __init__(self, plans, configuration, fold, dataset_json, device=torch.device("cuda")):  # noqa: B008
        super().__init__(plans, configuration, fold, dataset_json, device)
        if not os.environ.get("SEGTRAIN_EPOCHS"):
            self.num_epochs = FINETUNE_EPOCHS
        self.initial_lr = self.PEAK_LR
        self.warmup_iters = int(os.environ.get("SEGTRAIN_WARMUP_ITERS", DEFAULT_WARMUP_ITERS))
        self.finetune_source = os.environ.get("SEGTRAIN_FINETUNE_FROM") or None
        self._finetune_summary = None
        self._global_iter = 0

    # -- the schedule ------------------------------------------------------------
    def total_iterations(self) -> int:
        return int(self.num_epochs) * int(self.num_iterations_per_epoch)

    def configure_optimizers(self):
        optimizer = torch.optim.SGD(self.network.parameters(), self.initial_lr,
                                    weight_decay=self.weight_decay, momentum=0.99, nesterov=True)
        scheduler = WarmupPolyScheduler(optimizer, self.initial_lr, self.warmup_iters,
                                        self.total_iterations())
        return optimizer, scheduler

    def on_train_epoch_start(self) -> None:
        # nnU-Net's version steps a per-epoch poly schedule; this one is per iteration. The epoch's
        # first-iteration LR is what goes to the log and the epoch event.
        self.network.train()
        self._global_iter = int(self.current_epoch) * int(self.num_iterations_per_epoch)
        lr = self.lr_scheduler.step(self._global_iter)
        self.print_to_log_file("")
        self.print_to_log_file(f"Epoch {self.current_epoch}")
        self.print_to_log_file(f"Current learning rate: {lr:.6g} (iteration {self._global_iter})")
        self.logger.log("lrs", lr, self.current_epoch)

    def train_step(self, batch: dict) -> dict:
        self.lr_scheduler.step(self._global_iter)
        self._global_iter += 1
        return super().train_step(batch)

    # -- the load ----------------------------------------------------------------
    def initialize(self):
        super().initialize()
        if self.finetune_source and self._finetune_summary is None:
            self._finetune_summary = load_finetune_source(
                self.network, self.finetune_source, self.plans_manager.plans,
                self.configuration_name, self.dataset_json, map_location=str(self.device))
            self.print_to_log_file(f"[segtrain] fine-tune source loaded in full: "
                                   f"{self._finetune_summary}")

    def on_train_start(self) -> None:
        resumed = int(self.current_epoch) > 0
        if not resumed and self._finetune_summary is None:
            if not self.was_initialized:
                self.initialize()
            if self._finetune_summary is None:
                raise RuntimeError("nnUNetTrainer_segtrain_finetune needs SEGTRAIN_FINETUNE_FROM "
                                   "(the last accepted model's checkpoint_final.pth); refusing to "
                                   "start a fine-tune from random weights")
        super().on_train_start()
        schedule = self.lr_scheduler.describe()
        self.print_to_log_file(f"[segtrain] LR schedule: {schedule}")
        w = self._writer()
        if w is not None:
            try:
                w.emit("finetune", resumed=resumed, schedule=schedule,
                       source=self._finetune_summary)
            except Exception as exc:
                self.print_to_log_file(f"[segtrain] failed to emit finetune event: {exc}")


class nnUNetTrainer_segtrain_finetune_lr1e3(nnUNetTrainer_segtrain_finetune):
    """The pre-registered fallback arm (A17b / Foxtrot F2): peak 1e-3, otherwise identical."""

    PEAK_LR = 1e-3


class nnUNetTrainer_segtrain_finetune_5epochs(nnUNetTrainer_segtrain_finetune):
    """Five epochs, for a smoke test of the fine-tune path."""

    def __init__(self, plans, configuration, fold, dataset_json, device=torch.device("cuda")):  # noqa: B008
        super().__init__(plans, configuration, fold, dataset_json, device)
        self.num_epochs = int(os.environ.get("SEGTRAIN_EPOCHS", "5"))
