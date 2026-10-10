"""nnU-Net v2 trainers for the Atlas Trillium experiment. Copied by ./atlas into the venv's
nnunetv2/training/nnUNetTrainer/variants/atlas/ so nnUNetv2_train can find them by name.

nnUNetTrainerAtlasBench  - R0 benchmark: master config, mirroring off, ATLAS_BENCH_EPOCHS epochs (default 4), no
                           checkpoints, no final validation. Per iteration it times the wait for the next batch
                           (loader) separately from the CUDA-synchronised train step (GPU), and records peak VRAM.
                           Writes JSON to $ATLAS_BENCH_OUT.
nnUNetTrainerAtlas       - the short real run: mirroring off, ATLAS_EPOCHS epochs (poly LR over that length),
                           checkpoint every 25 epochs, and a hard stop before $ATLAS_DEADLINE (unix time) so the
                           final validation (sliding-window prediction of the val fold) always runs.
"""
import os, json, time
import numpy as np
import torch
from nnunetv2.training.nnUNetTrainer.variants.data_augmentation.nnUNetTrainerNoMirroring import nnUNetTrainerNoMirroring


def _sync():
    if torch.cuda.is_available():
        torch.cuda.synchronize()


def _test_overrides(tr):
    # CPU self-test only: tiny epochs. Never set on Trillium.
    if os.environ.get('ATLAS_TEST_ITERS'):
        tr.num_iterations_per_epoch = int(os.environ['ATLAS_TEST_ITERS']); tr.num_val_iterations_per_epoch = 1


class nnUNetTrainerAtlasBench(nnUNetTrainerNoMirroring):
    def __init__(self, plans, configuration, fold, dataset_json, device=torch.device('cuda')):
        super().__init__(plans, configuration, fold, dataset_json, device)
        self.num_epochs = int(os.environ.get('ATLAS_BENCH_EPOCHS', 4))
        self.disable_checkpointing = True
        _test_overrides(self)

    def save_checkpoint(self, filename):
        pass

    def perform_actual_validation(self, save_probabilities=False):
        pass

    def run_training(self):
        self.on_train_start()
        if torch.cuda.is_available(): torch.cuda.reset_peak_memory_stats()
        rec = dict(epochs=[], n_proc_DA=os.environ.get('nnUNet_n_proc_DA'), patch=list(self.configuration_manager.patch_size),
                   batch_size=self.batch_size, gpu=torch.cuda.get_device_name() if torch.cuda.is_available() else 'cpu', torch=torch.__version__)
        for epoch in range(self.current_epoch, self.num_epochs):
            self.on_epoch_start(); self.on_train_epoch_start()
            t_epoch = time.time(); waits, steps, outs = [], [], []
            for _ in range(self.num_iterations_per_epoch):
                t0 = time.time(); batch = next(self.dataloader_train); t1 = time.time()
                outs.append(self.train_step(batch)); _sync(); t2 = time.time()
                waits.append(t1 - t0); steps.append(t2 - t1)
            self.on_train_epoch_end(outs)
            t_train = time.time() - t_epoch
            with torch.no_grad():
                self.on_validation_epoch_start()
                vo = [self.validation_step(next(self.dataloader_val)) for _ in range(self.num_val_iterations_per_epoch)]
                self.on_validation_epoch_end(vo)
            self.on_epoch_end()
            rec['epochs'].append(dict(epoch=epoch, epoch_s=time.time() - t_epoch, train_s=t_train,
                                      loader_wait_s=float(np.sum(waits)), gpu_step_s=float(np.sum(steps)),
                                      median_wait=float(np.median(waits)), median_step=float(np.median(steps)),
                                      peak_alloc_gib=(torch.cuda.max_memory_allocated() / 2**30) if torch.cuda.is_available() else 0.0,
                                      peak_reserved_gib=(torch.cuda.max_memory_reserved() / 2**30) if torch.cuda.is_available() else 0.0))
            with open(os.environ.get('ATLAS_BENCH_OUT', 'bench.json'), 'w') as f:
                json.dump(rec, f, indent=1)
        self.on_train_end()


class nnUNetTrainerAtlas(nnUNetTrainerNoMirroring):
    def __init__(self, plans, configuration, fold, dataset_json, device=torch.device('cuda')):
        super().__init__(plans, configuration, fold, dataset_json, device)
        self.num_epochs = int(os.environ.get('ATLAS_EPOCHS', 1000))
        self.save_every = 25
        self.deadline = float(os.environ.get('ATLAS_DEADLINE', 0)) or None
        _test_overrides(self)

    def perform_actual_validation(self, save_probabilities=False):
        if os.environ.get('ATLAS_TEST_SKIP_FINAL_VAL'):  # CPU self-test only
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
            if self.deadline and time.time() + 1.5 * float(np.median(times)) > self.deadline:
                self.print_to_log_file(f'ATLAS: stopping at epoch {epoch} of {self.num_epochs} before the deadline')
                break
        self.on_train_end()
