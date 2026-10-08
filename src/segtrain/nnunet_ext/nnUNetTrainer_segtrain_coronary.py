"""The R1 trainer for the 4-class coronary task (Dataset712_CoronaryBranches; master plan = Atlas v4).

Everything ``nnUNetTrainer_segtrain`` does (event stream, wall-clock pause, chain resume), plus three recipe rules:

**No mirroring, in training or at inference.** Mirroring swaps the left and right coronary trees while keeping
their labels; the task is to tell them apart. TopCoW's organisers attribute a winning team's L/R swaps to exactly
this (arXiv:2312.17670, Section 5.1). Same override as nnU-Net's own ``nnUNetTrainerNoMirroring``.

**The val softmax is always saved** (amendments A7/A13). The final validation writes ``<case>.npz`` next to each
predicted segmentation, so the naming competitors (rule renaming R, hybrid decoding H) and post-processing
candidates (P1') can be scored on this model without re-running the GPU. ``SEGTRAIN_SAVE_PROBABILITIES=0`` turns it
off (it costs disk: up to ~1 GB per case before compression gains).

**The fixed CT window is checked, not assumed.** The window is applied to the plans file at planning time
(``segtrain.plans.apply_ct_window``); a plans file planned without it would silently train on nnU-Net's
labelled-voxel window, which flattens fat and maps calcium onto lumen. ``on_train_start`` therefore refuses to train
unless the plans' CT clip range equals ``CT_WINDOW``. ``SEGTRAIN_CT_WINDOW=lo,hi`` changes the expected window;
``SEGTRAIN_CT_WINDOW=off`` disables the check (the window ablation, A2 in the plan's ablation table).
"""

from __future__ import annotations

import os

import torch

# Absolute import: nnU-Net imports this file as a top-level module.
from segtrain.nnunet_ext.nnUNetTrainer_segtrain import nnUNetTrainer_segtrain

from segtrain.nnunet_ext.ct_window import CT_WINDOW, check_window, expected_window  # noqa: F401


class nnUNetTrainer_segtrain_coronary(nnUNetTrainer_segtrain):
    """nnUNetTrainer_segtrain + no mirroring + saved val softmax + fixed-window check."""

    def __init__(self, plans, configuration, fold, dataset_json,
                 device=torch.device("cuda")):  # noqa: B008
        super().__init__(plans, configuration, fold, dataset_json, device)
        self._expected_window = expected_window()
        self._save_probabilities = os.environ.get("SEGTRAIN_SAVE_PROBABILITIES", "1") != "0"

    def configure_rotation_dummyDA_mirroring_and_inital_patch_size(self):
        rotation_for_DA, do_dummy_2d_data_aug, initial_patch_size, _mirror_axes = \
            super().configure_rotation_dummyDA_mirroring_and_inital_patch_size()
        self.inference_allowed_mirroring_axes = None
        return rotation_for_DA, do_dummy_2d_data_aug, initial_patch_size, None

    def on_train_start(self) -> None:
        check_window(self.plans_manager.plans, self._expected_window)
        super().on_train_start()

    def perform_actual_validation(self, save_probabilities: bool = False):
        return super().perform_actual_validation(save_probabilities or self._save_probabilities)


class nnUNetTrainer_segtrain_coronary_5epochs(nnUNetTrainer_segtrain_coronary):
    """Five epochs, for the CPU smoke test of the R1 path."""

    def __init__(self, plans, configuration, fold, dataset_json,
                 device=torch.device("cuda")):  # noqa: B008
        super().__init__(plans, configuration, fold, dataset_json, device)
        self.num_epochs = int(os.environ.get("SEGTRAIN_EPOCHS", "5"))
