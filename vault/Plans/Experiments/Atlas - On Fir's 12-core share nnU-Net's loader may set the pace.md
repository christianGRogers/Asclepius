---
aliases: [Atlas R9 loader]
tags: [plans, experiment, round9, fir, compute, loader]
author: Atlas
round: 9
status: done (an estimate; job 1 on Fir measures it)
updated: 2026-10-18
issue: christianGRogers/Asclepius#48
---

# On Fir's 12-core share, nnU-Net's loader may set the pace

**Question.** On Trillium, a 1-GPU job has 24 cores, so icx4 runs 22 augmentation workers. It was GPU-bound there:
181 s per epoch, 0.72 s per batch of two 256³ patches, and a 0.02 % loader wait in R0. Fir's bundle is 12 cores per
GPU, so `job_body.sh` runs `nnUNet_n_proc_DA = 12 − 2 = 10` workers. Does the loader become the bottleneck, and
how many GPU-hours should the lead expect?

**Method.** `experiments/Atlas/r9_loader_cost_synthetic.py` is the round-4 `loader_cost.py` with a synthetic
volume, because this sandbox has no CT; the transforms' cost does not depend on the image content. It times
nnU-Net 2.8.1's own training transform pipeline (`nnUNetTrainer.get_training_transforms`, mirroring off, the 7-stage
ResEnc deep-supervision scales, 4 labels) on one sample at a time:

- one thread;
- final patch 256³, padded initial crop 411³ (rotation ±30°, scale 0.85–1.25);
- an Intel Xeon @ 2.80 GHz, on a 4-core VM that was also downloading during the first run.

There were two runs, n = 16 and n = 40 (logs `r9_loader_cost_n16.log`, `r9_loader_cost_n40.log`).

**Result.**

| | n | mean | median | p90 | max |
|---|---|---|---|---|---|
| run 1 (VM busy) | 16 | 7.58 s | 0.58 s | 23.95 s | 57.16 s |
| run 2 | 40 | 5.53 s | 2.49 s | 9.45 s | 72.85 s |
| pooled | 56 | **6.1 s** | 0.9 s | — | — |
| pooled, top 3 removed | 53 | **3.3 s** | — | — | — |

The cost is bimodal: about 0.1–1 s when no spatial transform fires, and 5–13 s when rotation or scaling resamples
the 411³ crop. That happens in 46 % of samples. On top of that there are rare outliers (36–73 s), probably CPU
contention on the VM. Round 4's estimate on the same kind of machine was 5.2 s per sample
([[Atlas - Without a GPU, nnU-Net's own loader and a saved-tensor count bound R0]]).

**What it means for Fir.** One epoch is 250 batches × 2 = 500 samples.

| Per-sample cost c (CPU-s) | Trillium, 22 workers: loader time per epoch | Fir, 10 workers | Fir epoch (max of GPU 181 s, loader) | 1000 epochs |
|---|---|---|---|---|
| 3.3 (trimmed) | 75 s | 165 s | 181 s, GPU-bound | ≈ 50 h |
| 5.2 (round 4) | 118 s | 260 s | 260 s | ≈ 72 h |
| 6.1 (pooled) | 139 s | 305 s | 305 s | ≈ 85 h |
| 7.9 (×1.3 slower Fir core) | 180 s | 395 s | 395 s | ≈ 110 h |

**Consistency check against Trillium.** Trillium would have been loader-bound only if c > 0.72 × 22 / 2 ≈ 7.9 s.
It was not (loader wait 0.02 %), so these costs agree with what was measured there.

**Caveats.**
- Fir's EPYC 9454 (Zen 4, 2.75 GHz) is not this VM's Xeon. Single-thread speed may differ by tens of percent either
  way.
- Reading and cropping the preprocessed data (blosc2) is not timed here, so this underestimates the cost a little.
- The batch-2 overlap between workers is ideal in this arithmetic. In practice the queue smooths the heavy tail
  only partly.

**What it changes** ([[Atlas v11]] §6.2).

- **Expected:** 55–85 GPU-h for 1000 epochs on Fir; worst case ≈ 110 h. That is above the compute inventory's
  50–70 h, which assumed 3 s per sample.
- **CHAIN=5** (≈ 118 h of capacity) instead of 4. Spare jobs exit within a minute.
- **Pre-registered:** if job 1's first ~20 epochs run above **400 s/epoch** (1000 epochs would not fit 5 chained
  jobs), cancel and rerun at 500 epochs (`ICX4_EPOCHS=500`; jobs inherit the environment). The poly schedule then
  completes (A22).
- Asking for 24 cores would halve the loader time but is charged as 2 GPUs of fairshare (Alliance bundle rule). It
  stays a lead option, not the default.
