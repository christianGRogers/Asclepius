"""The two arms of run 3, the FP-aware loss pilot (Round 8, A24).

Both arms are the A17a warm fine-tune (full load of the source checkpoint, heads included;
LR warm-up then poly; coronary invariants: window check, no mirroring, val softmax, A14 refusal).
The pairing condition (A24.1) is that **the loss is the only difference**, so both arms also run
the same data and augmentation stream:

* the training and validation augmenters are batchgenerators' deterministic
  ``MultiThreadedAugmenter`` (round-robin order) with fixed per-worker seeds, instead of nnU-Net's
  non-deterministic one;
* the parent process seeds numpy and torch, and the case-sampling RandomState of each data loader,
  before the workers fork;
* ``SEGTRAIN_SEED`` (default 12345) sets all of these.

GPU kernels (cuDNN) stay non-deterministic; that is the residual difference between two runs of
one arm, and it is far below the seed-to-seed variation A22 accounts for.

``nnUNetTrainer_segtrain_fppilot_F0``  plain loss (nnU-Net DiceCE with deep supervision).
``nnUNetTrainer_segtrain_fppilot_F1``  plus the FP-aware term (:mod:`fp_aware_loss`): lambda
    ``SEGTRAIN_FP_LAMBDA`` (1), gamma ``SEGTRAIN_FP_GAMMA`` (2),
    band ``SEGTRAIN_FP_BAND_MM`` (1.5 mm).
Separate classes, so the two result folders never collide.
"""

from __future__ import annotations

import os
import random

import numpy as np
import torch

from segtrain.nnunet_ext.fp_aware_loss import FPAwareLoss

# Absolute import: nnU-Net imports this file as a top-level module.
from segtrain.nnunet_ext.nnUNetTrainer_segtrain_finetune import nnUNetTrainer_segtrain_finetune

DEFAULT_SEED = 12345


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


class nnUNetTrainer_segtrain_fppilot_F0(nnUNetTrainer_segtrain_finetune):
    """Run 3, arm F0: the A17a fine-tune with a seeded, deterministic data stream."""

    def __init__(self, plans, configuration, fold, dataset_json, device=torch.device("cuda")):  # noqa: B008
        super().__init__(plans, configuration, fold, dataset_json, device)
        self.stream_seed = int(os.environ.get("SEGTRAIN_SEED", DEFAULT_SEED))

    def get_dataloaders(self):
        from batchgenerators.dataloading.multi_threaded_augmenter import MultiThreadedAugmenter
        from batchgenerators.dataloading.single_threaded_augmenter import SingleThreadedAugmenter
        from nnunetv2.utilities.default_n_proc_DA import get_allowed_n_proc_DA

        seed = self.stream_seed
        seed_everything(seed)
        dl_tr, dl_val = self._build_data_loaders()
        dl_tr.rs = np.random.RandomState(seed)
        dl_val.rs = np.random.RandomState(seed + 1)
        n = get_allowed_n_proc_DA()
        if n == 0:
            tr, val = SingleThreadedAugmenter(dl_tr, None), SingleThreadedAugmenter(dl_val, None)
        else:
            n_val = max(1, n // 2)
            tr = MultiThreadedAugmenter(dl_tr, None, n, num_cached_per_queue=2,
                                        seeds=[seed + 100 + i for i in range(n)],
                                        pin_memory=self.device.type == "cuda", wait_time=0.002)
            val = MultiThreadedAugmenter(dl_val, None, n_val, num_cached_per_queue=2,
                                         seeds=[seed + 1000 + i for i in range(n_val)],
                                         pin_memory=self.device.type == "cuda", wait_time=0.002)
        _ = next(tr)
        _ = next(val)
        self.print_to_log_file(f"[segtrain] deterministic data stream: seed {seed}, {n} workers")
        return tr, val

    def _build_data_loaders(self):
        """nnU-Net 2.8.1's get_dataloaders up to (not including) the augmenters."""
        from nnunetv2.training.dataloading.data_loader import nnUNetDataLoader
        from nnunetv2.training.dataloading.nnunet_dataset import infer_dataset_class

        if self.dataset_class is None:
            self.dataset_class = infer_dataset_class(self.preprocessed_dataset_folder)
        patch_size = self.configuration_manager.patch_size
        ds_scales = self._get_deep_supervision_scales()
        rot, dummy2d, initial_patch, mirror = \
            self.configure_rotation_dummyDA_mirroring_and_inital_patch_size()
        lm = self.label_manager
        tr_t = self.get_training_transforms(
            patch_size, rot, ds_scales, mirror, dummy2d,
            use_mask_for_norm=self.configuration_manager.use_mask_for_norm,
            is_cascaded=self.is_cascaded, foreground_labels=lm.foreground_labels,
            regions=lm.foreground_regions if lm.has_regions else None, ignore_label=lm.ignore_label)
        val_t = self.get_validation_transforms(
            ds_scales, is_cascaded=self.is_cascaded, foreground_labels=lm.foreground_labels,
            regions=lm.foreground_regions if lm.has_regions else None, ignore_label=lm.ignore_label)
        d_tr, d_val = self.get_tr_and_val_datasets()
        kw = dict(oversample_foreground_percent=self.oversample_foreground_percent,
                  sampling_probabilities=None, pad_sides=None,
                  probabilistic_oversampling=self.probabilistic_oversampling)
        dl_tr = nnUNetDataLoader(d_tr, self.batch_size, initial_patch, patch_size, lm,
                                 transforms=tr_t, **kw)
        dl_val = nnUNetDataLoader(d_val, self.batch_size, patch_size, patch_size, lm,
                                  transforms=val_t, **kw)
        return dl_tr, dl_val


class nnUNetTrainer_segtrain_fppilot_F1(nnUNetTrainer_segtrain_fppilot_F0):
    """Run 3, arm F1: F0 plus the FP-aware term."""

    def _build_loss(self):
        base = super()._build_loss()
        spacing = self.configuration_manager.spacing
        loss = FPAwareLoss(base, spacing,
                           lam=float(os.environ.get("SEGTRAIN_FP_LAMBDA", 1.0)),
                           gamma=float(os.environ.get("SEGTRAIN_FP_GAMMA", 2.0)),
                           band_mm=float(os.environ.get("SEGTRAIN_FP_BAND_MM", 1.5)))
        self.print_to_log_file(f"[segtrain] FP-aware loss: {loss.describe()}")
        return loss

    def on_train_epoch_end(self, train_outputs):
        super().on_train_epoch_end(train_outputs)
        if isinstance(self.loss, FPAwareLoss) and self.loss.terms:
            value = float(np.mean(self.loss.terms))
            self.print_to_log_file(f"[segtrain] FP term (epoch mean): {value:.5f}")
            w = self._writer()
            if w is not None:
                try:
                    w.emit("fp_term", epoch=int(self.current_epoch), value=value)
                except Exception:
                    pass
            self.loss.terms = []
