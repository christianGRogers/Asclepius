"""nnU-Net trainer for the Bridge Trillium experiment: the master's settings that touch this experiment
(no mirroring, Atlas v3 §2.4), plus a wall-clock deadline so a single 24 h job always reaches the
validation-set prediction (with softmax) that the experiment exists for.

Installed by `./bridge` into nnunetv2/training/nnUNetTrainer/variants/ (nnU-Net finds trainers by
scanning its own package).

Env:
  BRIDGE_TRAIN_DEADLINE  absolute unix time; training stops at the first epoch boundary after it
  BRIDGE_SAVE_EVERY      checkpoint_latest interval in epochs (default 5) so a killed job can resume
"""
import os
import time

import torch
from nnunetv2.training.nnUNetTrainer.nnUNetTrainer import nnUNetTrainer


class nnUNetTrainer_bridge(nnUNetTrainer):
    def __init__(self, plans, configuration, fold, dataset_json, device=torch.device('cuda')):  # noqa: B008
        super().__init__(plans, configuration, fold, dataset_json, device)
        self.save_every = int(os.environ.get('BRIDGE_SAVE_EVERY', '5'))
        dl = os.environ.get('BRIDGE_TRAIN_DEADLINE')
        self._deadline = float(dl) if dl else None
        n = os.environ.get('BRIDGE_EPOCHS')
        if n:
            self.num_epochs = int(n)
        it = os.environ.get('BRIDGE_ITERATIONS')
        if it:
            self.num_iterations_per_epoch = int(it)
            self.num_val_iterations_per_epoch = max(1, int(it) // 5)

    def configure_rotation_dummyDA_mirroring_and_inital_patch_size(self):
        rotation_for_DA, do_dummy_2d_data_aug, initial_patch_size, mirror_axes = \
            super().configure_rotation_dummyDA_mirroring_and_inital_patch_size()
        self.inference_allowed_mirroring_axes = None
        return rotation_for_DA, do_dummy_2d_data_aug, initial_patch_size, None

    def run_training(self):
        """nnU-Net 2.8.1's loop, verbatim, plus the deadline check at each epoch boundary."""
        self.on_train_start()
        for epoch in range(self.current_epoch, self.num_epochs):
            if self._deadline is not None and time.time() > self._deadline:
                self.print_to_log_file(f'BRIDGE: deadline reached before epoch {epoch}; finishing training')
                break
            self.on_epoch_start()
            self.on_train_epoch_start()
            train_outputs = []
            for batch_id in range(self.num_iterations_per_epoch):
                train_outputs.append(self.train_step(next(self.dataloader_train)))
            self.on_train_epoch_end(train_outputs)
            with torch.no_grad():
                self.on_validation_epoch_start()
                val_outputs = []
                for batch_id in range(self.num_val_iterations_per_epoch):
                    val_outputs.append(self.validation_step(next(self.dataloader_val)))
                self.on_validation_epoch_end(val_outputs)
            self.on_epoch_end()
        self.on_train_end()
