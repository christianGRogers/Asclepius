"""nnU-Net v2 trainer for Delta's Trillium experiment.

= nnUNetTrainerNoMirroring (mirroring swaps left and right coronary trees) with
  * DELTA_EPOCHS epochs (default 250; the master plan's ablation length),
  * a wall-clock deadline (DELTA_TRAIN_DEADLINE, unix seconds): after 3 epochs the epoch budget is
    shrunk so that training -- including its poly learning-rate decay -- ends before the deadline,
    and the loop also stops before starting an epoch that would overrun it,
  * checkpoint every 10 epochs (resume with --c after a pre-emption),
  * DELTA_SMOKE=1: 2 + 1 iterations per epoch (CPU smoke test only).
Installed by ./delta into the venv's nnunetv2/training/nnUNetTrainer/variants/ directory.
"""
import os
import time

import numpy as np
import torch

from nnunetv2.training.nnUNetTrainer.variants.data_augmentation.nnUNetTrainerNoMirroring import \
    nnUNetTrainerNoMirroring


class nnUNetTrainerDelta(nnUNetTrainerNoMirroring):
    def __init__(self, plans: dict, configuration: str, fold: int, dataset_json: dict,
                 device: torch.device = torch.device('cuda')):
        super().__init__(plans, configuration, fold, dataset_json, device)
        self.num_epochs = int(os.environ.get('DELTA_EPOCHS', '250'))
        self.save_every = 10
        if os.environ.get('DELTA_SMOKE') == '1':
            self.num_iterations_per_epoch = 2
            self.num_val_iterations_per_epoch = 1

    def run_training(self):
        deadline = float(os.environ.get('DELTA_TRAIN_DEADLINE', '0')) or None
        self.on_train_start()
        times = []
        epoch = self.current_epoch
        while epoch < self.num_epochs:
            if deadline and times and time.time() + 1.2 * np.mean(times[-5:]) > deadline:
                self.print_to_log_file(f'DELTA: deadline reached before epoch {epoch}; stopping.')
                break
            t0 = time.time()
            self.on_epoch_start()
            self.on_train_epoch_start()
            train_outputs = [self.train_step(next(self.dataloader_train))
                             for _ in range(self.num_iterations_per_epoch)]
            self.on_train_epoch_end(train_outputs)
            with torch.no_grad():
                self.on_validation_epoch_start()
                val_outputs = [self.validation_step(next(self.dataloader_val))
                               for _ in range(self.num_val_iterations_per_epoch)]
                self.on_validation_epoch_end(val_outputs)
            self.on_epoch_end()
            times.append(time.time() - t0)
            epoch = self.current_epoch
            if deadline and len(times) == 3:
                fit = epoch + int((deadline - time.time()) / (1.15 * np.mean(times)))
                if fit < self.num_epochs:
                    self.print_to_log_file(f'DELTA: epoch budget {self.num_epochs} -> {max(fit, epoch + 1)} '
                                           f'(mean epoch {np.mean(times):.0f} s)')
                    self.num_epochs = max(fit, epoch + 1)
                    self.lr_scheduler.max_steps = self.num_epochs
        self.on_train_end()
