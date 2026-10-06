"""nnU-Net v2 trainer for the Crucible two-reads experiment.

Copied by ./crucible into the venv's nnunetv2/training/nnUNetTrainer/ so nnU-Net can find it by name.
- No mirroring (left/right chirality; master plan rule).
- Epochs and iterations from the environment, identical for every arm (fairness = same number of gradient steps).
- Deadline guard: if CRUCIBLE_DEADLINE (unix time) would be passed by another epoch, save checkpoint_latest.pth
  and exit with code 75 so the driver records the arm as unfinished and a re-run resumes it with --c.
"""
import os
import sys
import time
from os.path import join

import torch

from nnunetv2.training.nnUNetTrainer.variants.data_augmentation.nnUNetTrainerNoMirroring import \
    nnUNetTrainerNoMirroring


class nnUNetTrainerCrucible(nnUNetTrainerNoMirroring):
    def __init__(self, plans, configuration, fold, dataset_json, device=torch.device('cuda')):
        super().__init__(plans, configuration, fold, dataset_json, device)
        self.num_epochs = int(os.environ.get('CRUCIBLE_EPOCHS', '1000'))
        self.num_iterations_per_epoch = int(os.environ.get('CRUCIBLE_ITERS', '250'))
        self.num_val_iterations_per_epoch = int(os.environ.get('CRUCIBLE_VAL_ITERS', '50'))
        self.save_every = 10

    def run_training(self):
        deadline = float(os.environ.get('CRUCIBLE_DEADLINE', '1e18'))
        self.on_train_start()
        t_last = None
        for epoch in range(self.current_epoch, self.num_epochs):
            t0 = time.time()
            self.on_epoch_start()
            self.on_train_epoch_start()
            outs = [self.train_step(next(self.dataloader_train)) for _ in range(self.num_iterations_per_epoch)]
            self.on_train_epoch_end(outs)
            with torch.no_grad():
                self.on_validation_epoch_start()
                vouts = [self.validation_step(next(self.dataloader_val)) for _ in range(self.num_val_iterations_per_epoch)]
                self.on_validation_epoch_end(vouts)
            self.on_epoch_end()
            t_last = time.time() - t0
            with open(join(self.output_folder, 'epoch_times.txt'), 'a') as f:
                f.write(f'{epoch} {t_last:.1f}\n')
            if self.current_epoch < self.num_epochs and time.time() + 1.5 * t_last > deadline:
                self.save_checkpoint(join(self.output_folder, 'checkpoint_latest.pth'))
                self.print_to_log_file('CRUCIBLE: deadline reached, checkpoint saved, exiting for resume')
                sys.exit(75)
        self.on_train_end()
