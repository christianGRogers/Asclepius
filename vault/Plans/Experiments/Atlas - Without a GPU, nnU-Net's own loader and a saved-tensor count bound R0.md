---
tags: [plans/experiment, r0, compute, memory, loader]
author: Atlas
round: 3
updated: 2026-10-08
---

# Without a GPU, nnU-Net's own loader and a saved-tensor count bound R0

## Question

The Round 2 ruling (§4, Atlas item 2) asks the master to get as close to R0 as possible without a GPU. How much
VRAM will the master configuration need? How many CPU-seconds does nnU-Net's real training data pipeline spend per
batch? The configuration is ResEnc 60 GB plans, 0.5 mm, 256³, batch 2, mirroring off.

## Method

1. **Activation memory.** Each planned architecture is built from its plans file on PyTorch's `meta` device. One
   training forward pass is run at the planned patch × batch, and the bytes of every tensor autograd saves for
   backward are summed (`torch.autograd.graph.saved_tensors_hooks`), counted both per save and per unique tensor
   object. Parameters, gradients and SGD momentum are added.
   - Everything is fp32 (meta has no autocast), so the result is calibrated rather than read off.
   - Calibration: the ResEnc L preset targets 24 GB, and the nnU-Net authors measured **22.7 GB** for it
     (nnU-Net Revisited Table 1, verified in
     [[Atlas - The recipe's external numbers checked against the source texts]]). Its 0.5 mm analogue in our sweep
     is the yardstick.
   - `experiments/Atlas/activation_memory.py`.
2. **Loader.** A real nnU-Net dataset was built from 6 CT-cached cases:
   - ImageCAS-X labels read out to 4 classes;
   - planned by `ResEncUNetPlanner -gpu_memory_target 60 -overwrite_target_spacing 0.5 0.5 0.5` (planner output on
     these real cases: **256³, batch 2, 0.5 mm**);
   - fixed window;
   - preprocessed by nnU-Net (`experiments/Atlas/r0cpu_setup.py`).

   Then `nnUNetTrainerNoMirroring.get_dataloaders()`, nnU-Net's own loader and augmentation, timed over 10 batches
   with `nnUNet_n_proc_DA=0` (single process) on this sandbox (`experiments/Atlas/loader_benchmark.py`).

## Result

**Memory.**

| Config | Saved for backward, fp32 (unique / all saves) | + params, grads, momentum | Predicted peak with AMP (× 22.7 / 28.2) |
|---|---|---|---|
| ResEnc L preset analogue, 0.5 mm (160 × 224 × 192) | 27.1 / 40.6 GiB | 1.1 GiB | 22.7 GB (calibration point) |
| ResEnc XL fallback, 0.5 mm (192 × 256 × 256) | 49.4 / 74.1 GiB | 1.6 GiB | **≈ 41 GB** |
| **Master, ResEnc 60 GB, 0.5 mm (256³)** | **65.7 / 98.6 GiB** | 1.6 GiB | **≈ 54 GB (≈ 50–62)** |
| A1 native, ResEnc 60 GB (160 × 320 × 320) | 64.2 / 96.3 GiB | 1.6 GiB | ≈ 53 GB |
| plain U-Net 70 GB, native (192 × 320 × 320) | 62.7 / 89.2 GiB | 0.5 GiB | not calibrated (different family) |

**Loader** (single process, 2 real cases at 0.5 mm):

- start-up 42 s;
- **10.3 CPU-seconds per batch of two 256³ patches** (17.9 s wall per batch on a VM whose load average was 7.4
  from other agents);
- main-process RSS 0.9 GiB.

The multi-worker run (3 workers) failed: its workers were killed by the sandbox's memory limit while other agents'
jobs held 11 of 15 GB. Per-worker memory is therefore **not measured** here.

Preprocessing memory: nnU-Net's `nnUNetv2_preprocess` of one case at 0.5 mm was OOM-killed at `-np 2` and at
`-np 1` (15 GB VM, other jobs present); 2 of 6 cases finished. Budget ~10 GB per preprocessing worker.

## What it implies

1. **The master fits the card.** The predicted peak is ~54 GB against the 75 GB R0 acceptance and the 80 GB H100, so
   the ResEnc XL-sized fallback should not be needed for memory. If R0 still shows > 75 GB, the next step is batch 1
   or activation checkpointing; both keep the 128 mm context that the fallback loses
   ([[Atlas - The fallback 192 × 256 × 256 patch at 0.5 mm, measured]]). The native A1 arm needs the same memory.
2. **The loader is the likely bottleneck, and the margin is thin.**
   - Supply: at 10.3 CPU-s per batch, 22 workers deliver one batch every ≈ 0.47 s on this VM's cores.
   - Demand: the GPU needs 69 TFLOP per step, i.e. 0.4 s at the A100's utilisation fraction and 1.2 s at its
     absolute rate ([[Atlas - A 256³ training step costs 69 TFLOP, and the CPU loader may set the pace]]).
   - So the job is either just GPU-bound or just loader-bound. This is why the Trillium run benchmarks at 12 and 22
     workers and times loader wait separately from step time
     ([[Atlas - Pending Trillium run, R0 benchmark and a short R1 scored by tree-F1]]).
3. **Preprocessing must be capped at ~10 workers** in a 188 GiB job; the Trillium job does that.

## Limits

- The memory figure is calibrated on one published measurement and assumes the master's AMP-to-fp32 ratio equals
  the ResEnc L preset's. cuDNN workspaces scale with patch and could add a few GB. R0 measures the real figure.
- The loader figure is single-process on a contended VM with 2 cases. Genoa cores at 2.4 GHz and the absence of
  contention may move it either way.
