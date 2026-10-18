---
tags: [plans, experiment, compute, fir, icx4, throughput, round9]
author: Foxtrot
round: 9
updated: 2026-10-18
issue: christianGRogers/Asclepius#48
code: experiments/Foxtrot/fir_da_throughput.py
---

# On Fir's 12 cores per H100 the icx4 loader may set the pace, so budget four chained jobs

## Question

icx4 trains a 256³ patch, batch 2, with nnU-Net's full augmentation. On Trillium a job gets 24 cores per H100
(22 augmentation workers). On Fir it gets **12** (10 workers, since `job_body.sh` uses `NPROC − 2`). Does
Fir's loader keep the H100 busy, and what does the run cost in GPU-hours?

The compute inventory estimated 50–70 h from Atlas's "≈ 6 CPU-s per batch", which was uncertain by about 2×
([[Compute inventory - Nibi or Fir run icx4 unchanged on def-aso22, the AI clusters need an aip- allocation]]).
This note measures it with nnU-Net's own loader.

## Facts used

- **Fir GPU nodes:** 160 nodes, each with 1 × AMD EPYC 9454 (Zen 4, 48 cores, 2.75 GHz), 1125 GB and
  4 × H100 SXM5 80 GB. Max job 7 days. Compute nodes have internet. (docs.alliancecan.ca/wiki/Fir, "last
  edited on 21 July 2026", read 2026-10-18.)
- **Bundle:** H100-80gb = 12.2 RGU, 12 cores and 288 GB per GPU (280 GB recommended); 0.98 cores per RGU.
  (docs.alliancecan.ca/wiki/Allocations_and_compute_scheduling#Ratios_in_bundles, "last edited on
  25 September 2026".)
- **GPU pace on Trillium (icx14, same plan and GPU):** 456 epochs at **182.0 s** median (p10 181.9, p90 182.2;
  `trillium-results/icx14/job2/results/training_log_2026_10_13_18_46_59.txt`), with 24 cores. The spread is
  almost zero, so Trillium is GPU-bound. With 250 training and 50 validation iterations per epoch, and a
  validation step at about a third of a training step, one training step takes **≈ 0.69 s**. The GPU therefore
  needs ≈ 1.46 training batches per second.

## Method

`experiments/Foxtrot/fir_da_throughput.py` (nnU-Net 2.8.1, torch 2.14 CPU):

- Synthetic preprocessed cases at the icx4 median shape (275 × 358 × 358 at 0.5 mm), saved with nnU-Net's own
  blosc2 writer and the chunk/block sizes its preprocessor computes for a 256³ patch. A four-class tube tree
  gives foreground oversampling something to hit.
- `nnUNetDataLoader` with `nnUNetTrainer.get_training_transforms`: rotation ±30°, scaling, noise, blur,
  brightness, contrast, low-resolution, gamma, deep-supervision targets; no mirroring, as in
  `nnUNetTrainerICX4`. The initial patch is 411³, with 33 % foreground oversampling and batch 2.
- One thread per process (`torch.set_num_threads(1)`, as nnU-Net's augmentation workers run), timing
  `generate_train_batch()`.
- The machine is a 4-vCPU KVM guest on a 5th-generation Xeon (Emerald Rapids, CPU model 207, 2.1 GHz base).

Runs:
- (a) 80 batches, alone;
- (b) 3 processes × 25 batches at once, to see contention;
- (c) a first 60-batch run that overlapped a network download, reported for completeness.

## Result

| Run | Batches | CPU-s per batch, mean (95 % bootstrap CI) | Median | Notes |
|---|---|---|---|---|
| (a) alone | 80 | **7.9 (6.6–9.2)** | 8.0 | bimodal: 27 of 80 under 3 s (no rotation or scaling drawn, p = 0.2 each); the rest ~10–12 s; max 24 s |
| (b) 3 at once | 75 | **9.4 (7.8–11.4)** | | ≈ 1.2× slower than alone: memory-bandwidth contention |
| (c) alone, during a download | 60 | 9.7 | 9.4 | |

The cost is dominated by the spatial transform: rotating and scaling a 411³ crop down to 256³, for two
channels and the segmentation.

### Translating to Fir

Fir's Zen 4 cores are probably about as fast per core as these Emerald Rapids vCPUs, or somewhat faster. I
assume a factor **f = 1.0–1.3** (Fir faster); I did not measure it. With 10 workers, which share 12
cores with 5 validation workers and the main process, use the loaded cost (b).

| Assumption | CPU-s per batch on Fir | Batches/s from 10 workers | GPU needs | Epoch (250 × max(0.69, X/10) + ~10 s) | 1000 epochs |
|---|---|---|---|---|---|
| f = 1.3, loaded | 7.2 | 1.39 | 1.46 | ≈ 190 s | ≈ 53 h |
| f = 1.0, unloaded (a) | 7.9 | 1.27 | 1.46 | ≈ 207 s | ≈ 58 h |
| f = 1.0, loaded (b) | 9.4 | 1.06 | 1.46 | ≈ 245 s | ≈ 68 h |
| Trillium (22 workers, measured) | — | ≥ 2.3 | 1.46 | 182 s | 50.6 h |

**Fir is likely loader-bound by 5–35 %. One thousand epochs take ≈ 53–68 h, against 51 h on Trillium.**
Adding about 1 h of preparation and 3–4 h for predicting 1000 cases plus aortas and tF1 on the open test (#54),
**the run costs ≈ 57–73 H100-hours**. That is 3 chained 23:50 jobs at the fast end and 4 at the slow end.

## What it changes

1. **Keep icx4's Fir profile as is** (`h100:1`, 12 cores, 280 GB, `def-aso22`) and submit **CHAIN=4**: 95 h of
   walltime covers the slow end. The model, epoch count and schedule do not change, so the result stays
   comparable with any Trillium run.
2. **Check after job 1.** `./icx4 status` prints s/epoch:
   - 180–250 s, as predicted: nothing to do;
   - above ~300 s, the 4 jobs no longer cover 1000 epochs plus prediction, and the lead adds a fifth
     (`CHAIN=1 ./icx4` after the chain, which resumes).
3. **Do not ask for 24 cores.** Fir charges 24 cores as ≈ 24.5 RGU against the H100's 12.2, which roughly
   doubles the fairshare used, while the wall-time gain is at most ~25 %. On `def-aso22` at opportunistic
   priority, fairshare matters more than a day of wall time. **Nibi** gives 14 cores per H100 under the same
   account and profile (`ICX4_CLUSTER=nibi`). It is the better alternative if Fir's queue is long.
4. **No code change is needed.** A change that would help (letting `nnUNet_n_proc_DA` use all 12 cores) is
   small, but it is untested under oversubscription, and the chain absorbs the cost anyway.

## Limits

- Synthetic images and trees, not CT. The augmentation cost depends on the array shape and the transforms,
  not the content. The foreground sampling cost differs slightly.
- The Zen 4 / Emerald Rapids speed factor is assumed, not measured. The first Fir job measures the truth
  in its first hour.
- 4 vCPUs cannot reproduce 16 processes on 12 cores. The 1.2× contention factor at 3 processes may be
  larger at 16.
- The validation-step cost (a third of a training step) is an assumption. It shifts the GPU pace by a few
  percent.
