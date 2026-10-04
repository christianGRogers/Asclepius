---
tags: [plans/experiment, compute, r0, nnunet, trillium]
author: Atlas
round: 2
updated: 2026-10-04
---

# A 256³ training step costs 69 TFLOP, and the CPU loader may set the pace

## Question

Amendment A6 requires R0 (measured VRAM, s/epoch, loader saturation) before any other GPU job, because every
GPU-hour figure in the vault is extrapolated. Without a GPU, how far can the extrapolation be replaced by
arithmetic on the real network, and what should R0 expect? Two parts: (1) compute per training step of the exact
planned architectures; (2) CPU cost of nnU-Net's augmentation per sample, against the 24 cores a single-GPU
Trillium job gets.

## Method

1. **FLOPs.** Each plans file from the planner sweep
   ([[Atlas - Every case has 0.5 mm slices and nnU-Net's own planner fixes the patch menu]]) instantiated with
   `get_network_from_plans` on PyTorch's `meta` device (exact layers, no memory), one forward pass at the planned
   patch × batch, conv and transposed-conv MACs counted by hooks. Training step ≈ 3 × forward. Calibration: nnU-Net
   Revisited measured ResEnc L on KiTS fold 0 at **35.28 A100-40GB GPU-hours** for 1000 epochs
   ([[Atlas - The recipe's external numbers checked against the source texts]]). Our ResEnc L-sized config costs
   7.1 EFLOP per 1000 epochs, so the A100 sustained ≈ 56 TFLOP/s ≈ 18 % of its 312 TFLOP/s bf16 peak.
   `experiments/Atlas/flops_estimate.py`.
2. **Loader.** nnU-Net v2.8.1's own `get_training_transforms` (rotation ±30°, scaling 0.7–1.4, intensity
   transforms, mirroring off, 6 deep-supervision scales, labels 1–4) applied to 40 samples. The input is the
   rotation-padded crop nnU-Net's loader takes (411³ for a 256³ patch), cut from a real CT (c0050) resampled to
   0.5 mm. One thread per sample, on this tournament machine (4 cores, load average ≈ 7–8 from other agents, so
   wall times are inflated by roughly 2×). `experiments/Atlas/loader_cost.py`.
3. Trillium single-GPU allocation: "a quarter node, with 24 cores and about 188 GiB of RAM"; 1-GPU `debugjob`
   up to 120 min (docs.alliancecan.ca/wiki/Trillium_Quickstart, read 2026-10-04).

## Result

**Compute per configuration** (patch z,y,x; batch 2):

| Config | Params | Train step | 1000 epochs | H100-h if H100 sustains 18 % of peak (178 TFLOP/s) | if it only matches the A100 (56 TFLOP/s) |
|---|---|---|---|---|---|
| ResEnc L, 0.5 mm (160 × 224 × 192) | 102 M | 28 TFLOP | 7.1 EFLOP | 11 | 35 |
| ResEnc XL, 0.5 mm (192 × 256 × 256) | 142 M | 52 TFLOP | 12.9 EFLOP | 20 | 64 |
| **ResEnc 60 GB, 0.5 mm (256³) — master** | 142 M | **69 TFLOP** | **17.2 EFLOP** | **27** | **85** |
| ResEnc 60 GB, native (160 × 320 × 320) — ablation A1 | 142 M | 67 TFLOP | 16.8 EFLOP | 26 | 83 |
| ResEnc 75 GB, native (224 × 320 × 320) | 142 M | 94 TFLOP | 23.6 EFLOP | 37 | 117 |
| plain 70 GB, native (192 × 320 × 320) | 45 M | 54 TFLOP | 13.4 EFLOP | 21 | 66 |

**Loader, per 256³ sample** (n = 40): bimodal. 24 of 40 samples took 0.1–1.4 s (no rotation or scaling drawn:
crop + intensity transforms only); 16 took 4.5–60 s (rotation or scaling drawn, p = 0.2 each: full 256³
resampling of image, label and 6 deep-supervision targets). Mean **6.5 s**, median 1.1 s, p90 14.3 s.

## What it implies

1. **The master config's 1000-epoch run should take 27–85 H100-h of GPU compute; the central guess (~45 h, two
   links) matches the plan's 40–60 h extrapolation.** The A1 native arm costs the same compute (16.8 vs 17.2
   EFLOP), so A1 is a fair comparison at equal cost.
2. **The data loader can be the bottleneck.** A batch of 2 needs ≈ 13 CPU-s here (perhaps 6 CPU-s on an
   uncontended Genoa core). The GPU needs 0.4 s (at 178 TFLOP/s) to 1.2 s (at 56 TFLOP/s) per step. Keeping it fed
   takes 5–30 workers, against 24 cores per GPU. **R0 must report GPU utilisation and iterations/s with
   `nnUNet_n_proc_DA` = 20.** If it is loader-bound:
   - preprocess once more with smaller margins;
   - lower `p_rotation` / `p_scaling` (the rotation ablation A3 is then also a cost lever);
   - or run the spatial transform on the GPU (batchgeneratorsv2 transforms are torch ops).
   Any of these must be recorded as a recipe change.
3. **R0 can run in a 1-GPU `debugjob` (≤ 120 min):**
   - `nnUNetTrainerBenchmark_5epochs` for s/epoch and peak VRAM;
   - one epoch with `nnUNet_n_proc_DA` ∈ {12, 20} for loader saturation.
   Acceptance band from this note: 1000 epochs in ≤ 85 h, i.e. ≤ 306 s/epoch. Above that, use the fallback
   (ResEnc XL-sized 192 × 256 × 256 at 0.5 mm, 12.9 EFLOP).

## Limits

- MAC counting covers convolutions only. Norms, activations and the loss add memory traffic, not FLOPs. That
  overhead is inside the A100 calibration, which was measured end to end.
- The A100 calibration is from KiTS, whose patch differs from ours. Utilisation on an H100 is unknown; that is why
  a range is given.
- The loader timings come from a contended 4-core VM and a single CT. They give the order of magnitude, not the
  figure to plan on; R0 gives that.
