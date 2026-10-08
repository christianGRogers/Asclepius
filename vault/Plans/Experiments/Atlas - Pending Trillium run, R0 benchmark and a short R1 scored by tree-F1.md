---
tags: [plans/experiment, trillium, r0, gpu, pending]
author: Atlas
round: 3
status: pending (prepared, not yet run)
updated: 2026-10-06
---

# Pending Trillium run: R0 benchmark and a short R1, scored by tree-F1

## Question

Two things the master plan cannot settle without a GPU (Round 2 ruling §4, Atlas items 2 and 5):

1. **R0 (amendment A6).** For the master configuration, what are the real peak VRAM, seconds per epoch and loader
   saturation? The configuration is ResEnc 60 GB plans, 0.5 mm isotropic, 256³ patch, batch 2, mirroring off,
   fixed window, on one Trillium H100 with its 24 cores. Do they meet the plan's acceptance (≤ 306 s/epoch, peak
   ≤ 75 GB), and how do they compare with the CPU predictions (≈ 55 GB; 27–85 H100-h per 1000 epochs)?
2. **First real 4-class predictions of the master recipe.** On the ImageCAS-X val fold (80 cases), what are:
   - tree-F1 @ 1.5 mm;
   - the FP-component gate on the raw prediction;
   - branch-swap rate;
   - how many trees are cut?

   Every real-prediction number in the vault so far comes from one small-patch (48 × 56 × 56 mm) binary model
   (ruling C3). This would be the first from a 128 mm, 4-class model.

## Method (what `trillium/atlas/atlas` does)

- **Login node.**
  - Builds a venv in `$HOME`: Alliance torch wheel plus `nnunetv2==2.8.1`, with the two experiment trainers copied
    into nnU-Net.
  - Finds `<root>/cases` and maps it to `c0000…c0999`. Both contract layouts are accepted and the detected one is
    printed.
  - Fetches the ImageCAS-X labels (~14 MB) by HTTP range requests.
  - Submits **one** job: `--account=def-aso22 --nodes=1 --gpus-per-node=1 --time=23:50:00`, no partition, no
    `--mem`, output under `$SCRATCH`.
  - Re-running never submits a second long job; it reports status or collects results.
- **Stage A, CPU in the job.**
  - Projected proxy labels in the binding convention for ImageCAS-X train (560) and val (80): split ImageCAS mask,
    territory rule, ramus → LCx; nearest ImageCAS-X name within 2 mm, then geodesic. The test (160) and quality-0
    (200) cases are not touched.
  - nnU-Net fingerprint, then `ResEncUNetPlanner -gpu_memory_target 60 -overwrite_target_spacing 0.5 0.5 0.5`. The
    planner's own output is recorded before the plan's window [−300, 1300] HU and 256³ / batch 2 are written in.
  - Preprocess with ≤ 10 workers, since one case at 0.5 mm needs ~10 GB RAM.
  - Fold 0 = train 560 / val 80.
- **Stage B, R0.** `nnUNetTrainerAtlasBench`, 4 epochs each at `nnUNet_n_proc_DA` = 12 and 22. Per iteration it
  times the wait for the next batch separately from the CUDA-synchronised step, and records peak allocated and
  reserved VRAM. If no epoch completes at 256³ (OOM), the job switches to the measured fallback 192 × 256 × 256 and
  re-benchmarks.
- **Stage C, short R1.** `nnUNetTrainerAtlas`: as many epochs as fit in what remains of 23:50 after a 1.5 h
  reserve, with the poly-LR schedule set to that length (expected ~250–450 epochs at 160–300 s/epoch). nnU-Net's
  final validation then predicts the 80 val cases with tile step 0.5.
- **Stage D, CPU.** `lib/report.py` scores every val case with `lib/tf1.py`, then writes `results/SUMMARY.md`,
  `results.json`, `per_case_val.json`, logs and the training curve. That is small: no weights, no volumes.
  - `tf1.py` is a self-contained port of Delta's definition (`thick` ostium, so it is provisional under A9).
  - CPU-validated against Delta's `perturb_metrics.score`: identical tF1, per-class clDice and swap rate to 4
    decimals on all 6 pairs tested (c0415, c0753, c0782 at 0.8 and 1.0 mm; e.g. c0782 at 1.0 mm: 0.8552 vs 0.8552).
    Script: `trillium/atlas/lib/validate_tf1.py`.

**Tested here on CPU (2026-10-08):**

- `shellcheck` and `bash -n` clean on `atlas` and `lib/job_body.sh`; every Python module compiles.
- **Dry runs in both contract layouts:**
  - Girder `<case>/ct.nii.gz` + `coronary_arteries.nii.gz`, 79 cases;
  - ImageCAS `<n>.img.nii.gz` + `<n>.label.nii.gz`, 79 cases, ids mapped n → `c{n-1}`.

  Both print the detected layout and the job script with `--account=def-aso22`.
- **Failure paths:** an unrecognised layout and a missing `cases/` fail loudly, listing what was tried.
- **`./atlas selftest`** builds a proxy label for a real val case (c0400: 75 % of mask voxels named within 2 mm,
  25 % geodesic, 0 unreached).
- **Stage A labels + plan** on the 42 ImageCAS-X train/val cases in the fake tree. On these real proxy labels nnU-Net's
  planner returns **256³, batch 2, 0.5 mm**, the master's plan. The fingerprint window it would use is
  **[−165, 658] HU**, matching the prediction of ≈ [−164, 640] in the window note.
- **Trainers, run through `nnUNetv2_train -device cpu`** with a tiny test architecture and 2 iterations per epoch
  (test-only env switches):
  - the benchmark trainer writes its per-epoch JSON (loader wait vs step time);
  - the R1 trainer stops cleanly before `ATLAS_DEADLINE` ("stopping at epoch 2 of 30") and writes
    `checkpoint_final`;
  - `--val` exports the val prediction NIfTI.

  nnU-Net's discovery finds both trainer classes once they are copied into the package, as the launcher does.
- **`report.py`** on mock benchmarks plus two predictions (one with an RCA slab cut out) gives the right table: the
  cut case gets RCA tF1 0.80 against clDice ≈ 0.96 and is flagged as a cut tree. Output 16 kB.

## What result would change which decision

| Result | Decision it changes |
|---|---|
| Peak reserved VRAM ≤ 75 GB and ≤ 306 s/epoch at 256³ | R0 passes; replace the 27–85 h forecast in v3 §2.5 by the measured figure; schedule R1 at full length |
| VRAM over → the job falls back to 192 × 256 × 256 | Adopt batch 1 or activation checkpointing before the fallback patch (v3 §2.5 order), since the fallback shows the LM to only 85 % of LAD-centred patches |
| Loader-wait share > 30 % at 22 workers | Loader-bound: GPU spatial transform or lower spatial-augmentation probabilities becomes part of the recipe (A3 then also a cost decision) |
| Val tF1@1.5 within a few points of per-class clDice, few cut trees | The small-patch cut rate (3/8) does not transfer to the master; P1/P1′ have little to fix |
| Many cut trees (clDice − tF1 > 0.10) | P1′ and Delta's distal-gap arm become live candidates on R1 |
| Swap rate ≥ 5 % or LM/LAD/LCx tF1 well below RCA | Bridge's renaming (R) is likely to win the A7 comparison, and patch context is not sufficient on its own |
| FP components > 1 per case on the raw prediction | Gate fails before any repair; the fixed window and window ablation A2 are the first suspects |

## Limits

- **Short schedule.** About 25–45 % of the plan's 1000 epochs. tF1 is a lower bound on R1's, though the poly-LR
  schedule completes, so the model is not mid-schedule.
- **Reference.** The reference is the projected proxy (the plan's training target), not team labels, which do not
  exist yet.
- **Ostium.** tF1 uses the `thick` ostium (A9: provisional). The FP gate and swap rate do not depend on it.
- **No A4 QA filter.** The Bridge labeller's `ignore` / exclusion was left out to keep the job's dependencies small.
  It affects ~0.3 % of voxels and ~10 % of cases.
- **Not tested on CPU:**
  - full-size network training, which the sandbox's 15 GB cannot hold (the activation estimate is ~55 GB);
  - full preprocessing: 2 of 6 cases completed before the sandbox ran out of memory. On Trillium a 1-GPU job has
    188 GiB and preprocessing uses ≤ 10 workers;
  - module loading and the Alliance pip wheelhouse.
