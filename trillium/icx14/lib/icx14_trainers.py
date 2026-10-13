"""nnU-Net v2 trainer for the icx14 run. Copied by ./icx14 into the venv's
nnunetv2/training/nnUNetTrainer/variants/icx14/ so nnUNetv2_train can find it by name.

nnUNetTrainerICX14 - the full 1000-epoch run, split across chained 23:50 jobs:
  * mirroring off (left/right swaps would teach the model that an LAD can be an RCA);
  * poly LR over the full 1000 epochs, whatever chunk it is in (nnU-Net resumes the epoch counter with --c);
  * checkpoint every 10 epochs (~30 min), so a hard kill loses little;
  * stops cleanly before $ICX14_DEADLINE (unix time) and skips the final validation when it stopped early,
    so a chunk spends its time training, not validating;
  * writes $ICX14_COMPLETE_MARKER when all epochs are done.
"""
import os, time
import numpy as np
import torch
from nnunetv2.training.nnUNetTrainer.variants.data_augmentation.nnUNetTrainerNoMirroring import nnUNetTrainerNoMirroring


class nnUNetTrainerICX14(nnUNetTrainerNoMirroring):
    def __init__(self, plans, configuration, fold, dataset_json, device=torch.device('cuda')):
        super().__init__(plans, configuration, fold, dataset_json, device)
        self.num_epochs = int(os.environ.get('ICX14_EPOCHS', 1000))
        self.save_every = 10
        self.deadline = float(os.environ.get('ICX14_DEADLINE', 0)) or None
        self.stopped_early = False
        if os.environ.get('ICX14_TEST_ITERS'):  # CPU self-test only; never set on Trillium
            self.num_iterations_per_epoch = int(os.environ['ICX14_TEST_ITERS']); self.num_val_iterations_per_epoch = 1

    def _build_loss(self):
        """Optional class-weighted cross-entropy, switched on mid-run by a file, so a later chunk of the chain
        can push the side branches (which a first 446-epoch chunk never predicted) without restarting.
        $W/ce_class_weights.json: a list of 15 weights (background + 14 classes). Absent -> stock nnU-Net loss."""
        loss = super()._build_loss()
        path = os.path.join(os.environ.get('W', ''), 'ce_class_weights.json')
        if os.environ.get('W') and os.path.isfile(path):
            import json
            w = torch.tensor(json.load(open(path)), dtype=torch.float32, device=self.device)
            inner = loss.loss if hasattr(loss, 'loss') else loss       # DeepSupervisionWrapper -> DC_and_CE_loss
            inner.ce.weight = w
            self.print_to_log_file(f'ICX14: class-weighted CE from {path}: {w.tolist()}')
        return loss

    def perform_actual_validation(self, save_probabilities=False):
        if self.stopped_early or os.environ.get('ICX14_SKIP_FINAL_VAL'):
            self.print_to_log_file('ICX14: final validation skipped (training not finished in this chunk)')
            return
        super().perform_actual_validation(save_probabilities)

    def run_training(self):
        self.on_train_start()
        times = []
        for epoch in range(self.current_epoch, self.num_epochs):
            t0 = time.time()
            self.on_epoch_start(); self.on_train_epoch_start()
            outs = [self.train_step(next(self.dataloader_train)) for _ in range(self.num_iterations_per_epoch)]
            self.on_train_epoch_end(outs)
            with torch.no_grad():
                self.on_validation_epoch_start()
                vo = [self.validation_step(next(self.dataloader_val)) for _ in range(self.num_val_iterations_per_epoch)]
                self.on_validation_epoch_end(vo)
            self.on_epoch_end()
            times.append(time.time() - t0)
            if epoch + 1 < self.num_epochs and self.deadline and \
                    time.time() + 2.0 * float(np.median(times[-20:])) > self.deadline:
                self.print_to_log_file(f'ICX14: stopping after epoch {epoch} of {self.num_epochs} before the deadline')
                self.stopped_early = True
                break
        self.on_train_end()   # saves checkpoint_final.pth (holds the epoch counter, so --c resumes from it)
        if not self.stopped_early and self.current_epoch >= self.num_epochs:
            marker = os.environ.get('ICX14_COMPLETE_MARKER')
            if marker:
                open(marker, 'w').write(str(self.current_epoch))
