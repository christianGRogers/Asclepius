---
tags: [plans, experiment, gpu, trillium, double-reads, noisy-labels, pending]
author: Crucible
round: 3
updated: 2026-10-08
status: pending (prepared; to be run by the project lead on Trillium)
---

# GPU experiment (pending): with two reads per case, which training target makes the best model?

## Question

Decision D2 means every case will be labelled twice. Nobody has measured how to train on the two reads. Six
candidate targets, all expressible as plain nnU-Net datasets with no custom loss:

| Arm | Training target per case |
|---|---|
| **single** | read A only (the single-read baseline) |
| **both** | read A and read B as two separate training samples (same image twice) |
| **agree** | voxels where A and B agree; disagreement → nnU-Net `ignore` label |
| **union** | vessel if either read says vessel; LM/LAD/LCx/RCA conflict → `ignore` |
| **a11** (added round 4) | the judge's A11 default. Each read is a separate sample; voxels both reads call vessel but name differently → `ignore` in both samples; extent differences keep each read's own label |
| **oracle** | the truth the reads were simulated from (upper bound, not available in practice) |

Two secondary questions:

- How far below the truth does scoring against *one* annotator put a model?
- Can a model trained on two reads exceed the inter-read agreement?

## Method

The code is at `trillium/crucible/`, under the README contract: entry point `./crucible`, one job of 1 × H100 for
23 h 55 min, `--account=def-aso22`.

1. **Login node.**
   - Build the venv (`$HOME/.venvs/crucible`; torch from the Alliance wheelhouse, nnunetv2 2.8.1).
   - Install the trainer `nnUNetTrainerCrucible`. It is nnU-Net's no-mirroring trainer with the epoch count taken
     from the environment and a deadline guard that checkpoints and exits for resume.
   - Discover `cases/` (ImageCAS or Girder layout).
   - Fetch the ImageCAS-X labels with one ~13.5 MB HTTP range request.
   - Submit the job.
2. **Job, stage `prep`.** Uses the 200 ImageCAS-X *train* cases and 50 ImageCAS-X *val* cases. ImageCAS-X's
   160-case test list is never touched, because it is the master's sealed-test pool.
   - Truth T is the ImageCAS mask split into four classes by nearest ImageCAS-X name. This is D0 (thick), D1
     (territory) and D1b (ramus → LCx).
   - Two reads per case are simulated. **Round 4: the default read model is now `annot_bias`.** Read A comes from
     annotator X (carina shifted +1.5 ± 1 mm, stops early at r_t ~ U(0.8, 1.1) mm); read B from annotator Y
     (−1.5 ± 1 mm, traces further, U(0.55, 0.8)). Ramus and D1/OM1 slips are as before.
   - This is the one regime where the CPU study found that fusion changes the result, and changes it in a direction
     only real training can settle ([[Crucible - Correlated annotator errors change what fusion does, and A10 scoring cannot see it]]).
     Under independent errors all schemes converge to the same target.
   - The `single` arm alternates annotators across cases, so it is not biased toward one habit.
   - `CRUCIBLE_READS=indep` restores the round-3 model, but the lead runs `./crucible` with nothing else.
   - Crop to the mask bounding box + 15 mm.
3. **Stage `plan` / `preprocess`.**
   - **One plan for all arms.** It is made on the oracle dataset, set to the master's fixed CT window [−300, 1300] HU,
     and copied to the other datasets with `nnUNetv2_move_plans_between_datasets`. Normalisation and patch are
     therefore identical across arms.
   - Default 3d_fullres: patch 96 × 160 × 160 at 0.5 × 0.35 × 0.35 mm on the smoke run. That is not the master's
     256³ ResEnc, which would not fit six arms into 24 h.
4. **Stage `probe`.** Four epochs measure s/epoch. Epochs per arm are then set to
   (remaining time − 1.5 h) / (6 × s/epoch), clamped to 20–300 and identical for every arm.
   - **Fairness:** every arm gets the same number of gradient steps. `both` sees twice the cases in the same steps.
5. **Stage `train`.** Arms run in order: single, both, a11, agree, union, oracle (oracle last, so a deadline cuts the arm that matters least). A deadline stop leaves later arms
   unfinished and records them. Re-running `./crucible` resumes them.
6. **Stage `predict` + `eval`.**
   - Predict the 50 test crops, with no TTA because mirroring is off.
   - Drop components < 100 voxels.
   - Score tF1 @ 1.5 mm (D3), plus Dice, rooted recall and precision, each against T, read A and read B.
   - Compute the inter-read ceiling (B scored against A).
   - Report paired per-case differences against `single`, with a bootstrap 95 % CI.
7. **Output.** `results/SUMMARY.md`, `results.json` and logs, in `$SCRATCH/crucible_2reads/results`. They are copied
   to `experiments/crucible/results/` when writable, otherwise by `./crucible collect`.

**Tested here on CPU** (no GPU available):

- `shellcheck` is clean;
- `./crucible dryrun` on a fake `<root>/cases/` (Girder layout, plus a junk directory) detects the layout, fetches
  the 804 ImageCAS-X files and prints the sbatch command;
- the ImageCAS layout is recognised by `discover.py`;
- full driver smoke run on CPU (`CRUCIBLE_SMOKE=1`: 4 train / 2 test cases, crops capped at 192 × 192 × 128,
  patch 48 × 64 × 64, 1 epoch × 2 iterations) completed end to end: prep → one shared plan → preprocess 5 datasets
  (including the `ignore` label) → 6 arms → predict → eval → `SUMMARY.md` / `results.json`. Its numbers are
  meaningless by design.
- Fixed during smoke testing:
  - `move_plans` does not copy `dataset.json`;
  - nnU-Net's own final validation on fold `all` re-predicts the training set. It is now skipped, saving about
    1 GPU-h per arm;
  - a tree with no root in the crop lost all its vessel in the reads; every tree now gets a root.

## Decision rule (pre-registered)

Let Δ be the paired tF1-vs-truth difference of an arm against `single`, with its 95 % CI.

| Result | Decision for the master plan |
|---|---|
| `a11` vs `both` (paired), **vs truth** | The CPU bracket under `annot_bias` runs from +0.018 (the network fills ignored carina voxels from their neighbours) to −0.075 (it does not). If `a11` ≥ `both`, the master's A11 default stands. If `a11` < `both` with the CI excluding 0, the ignored band is not being filled, and A11's name-conflict `ignore` should be narrowed to cases without systematic annotator habits (detected in A12) |
| any fusion vs `both`, **vs reads** | Expected to be within ±0.002 whatever the truth-side result. If so, this confirms that A10 scoring cannot choose a fusion rule, and the A11 test on real reads (scored vs reads) needs the ImageCAS-X carina anchor as a second criterion |
| `both` has Δ > 0 with the CI excluding 0, and ≥ `agree` and `union` | **Train on both reads as separate samples** (the simplest). Fusion is not needed |
| `agree` or `union` beats `both` (CI of their difference excludes 0) | Use that fusion with nnU-Net's ignore label (`ignore` = 5 in dataset.json) |
| No arm beats `single` | The second read is worth more as an **evaluation and QA** resource (ceiling, arbitration) than as training signal. Train on one read per case, chosen as the one closer to the namer QA |
| Any arm's tF1 *vs reads* < tF1 *vs truth* by > 0.03 | Already decided by A10: score as the mean of tF1 against each read, never against one read and never against a fused reference. Report the gap as evidence of how far single-read scoring understates the truth |

## What would change which decision

- The master (Atlas v3) currently says nothing about how two reads enter training; this experiment fills that gap.
- If `agree`/`union` win, the master needs the ignore label in `src/segtrain` (dataset.json `ignore`) before R1
  consumes team labels.
- If no arm beats `single`, the extra annotation effort of D2 should be costed as evaluation, not training.

## Limits

- **Reads are simulated.** The ranking can only be as true as the error model. The model is calibrated to
  ImageCAS-X's per-class inter-observer Dice (LM is under-agreed: 0.81 vs 0.92). The first ~50 real double-read
  cases must be used to re-fit it (carina-shift SD, truncation radius, slip rates), and the conclusion re-checked
  on the label-level simulation (CPU, minutes).
- Default patch, not the master's 256³ ResEnc; 200 training cases; one seed.
- tF1 is my re-implementation with the thickest-voxel ostium, so it is provisional under A9.

## Status

- **Prepared and smoke-tested; not yet run on Trillium.**
- Expected GPU-time use: about 1.2 h of the 24 h is CPU-bound prep, fingerprinting and preprocessing inside the job;
  the probe takes 4 epochs; the rest is 5 equal-step arms plus about 1.5 h for prediction and evaluation.
- Plan: [[Crucible v4]].
