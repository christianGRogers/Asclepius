---
tags: [plans/experiment, janus1-l, track-1-L, round3, spacing, field-of-view, calibration, interfaces, cpu]
author: Bridge
track: 1-L
round: 3
updated: 2026-11-23
issue: christianGRogers/Asclepius#302
code: experiments/Bridge/j1l_r3/
---

# At 0.45 mm nnU-Net keeps a 256 cube, and its 115 mm view holds the whole coronary tree in 78 percent of cases against 97 percent

These are the CPU experiments behind [[Candidates/Janus 1-L/Bridge v3|Bridge v3]]. They answer three of
[[Janus 1-L Round 2]] §5's items without Step T or Job 0. No GPU job was run. The only data read were the 620 D45
training labels.

## 1. What view would S get at 0.45 mm? (§5 item 3)

**Question.** Round 1 costed a 0.45 mm run with "a 115 mm view". Is that what nnU-Net would really plan? And does a
115 mm view lose context that a 128 mm one keeps?

### Setup

- **`fetch620.py`** fetches the ImageCAS-X labels of the train 620 only, by range reads from the Zenodo record. It
  refuses any locked-100, sealed or quality-0 id.
- **`plan045.py`** runs nnU-Net 2.8.1's `ResEncUNetPlanner` with a 60 GB target, as Janus 0 was planned. It runs on
  CPU, on a fingerprint built from the 620's label headers. The labels share their CT's grid, and the intensity
  properties do not enter the patch choice.
- **`view_check.py`** measures each tree, after the D25 collapse, against cubes of 128, 115.2 and 102.4 mm:
  - whether the whole tree, the left tree and the RCA fit;
  - the best cube's share of the tree;
  - "root in view": the share of a class's voxels whose tree root lies inside a cube centred on them. The root is a
    proxy: the left root is the LM centroid, and the RCA root is the RCA voxel nearest it.
- **The pass rule was committed before the run:**
  - V1: the whole-tree fit may fall by ≤ 10 points;
  - V2: root in view may fall by ≤ 5 points in every class.

### Result

nnU-Net's own plan:

| Target | Patch | Batch | View |
|---|---|---|---|
| 0.5 mm | 256³ | 2 | 128.0 mm (**reproduces Janus 0's recorded `planner_output.json`**) |
| 0.45 mm | 256³ | 2 | **115.2 mm**, the same 7-stage network |

The view check, on the 620:

| | 128 mm | 115.2 mm | 102.4 mm |
|---|---|---|---|
| Whole tree fits | 97.3 % | **78.2 %** | 28.2 % |
| Left tree fits | 100 % | 99.7 % | 87.1 % |
| RCA fits | 99.8 % | 99.4 % | 97.6 % |
| Root in view, LAD / LCx / RCA | 89.7 / 95.1 / 94.4 % | **83.8 / 90.2 / 86.2 %** | 76.1 / 83.5 / 73.7 % |

The tree's median extent is 107 × 90 × 86 mm, and its p90 is 120 × 102 × 99 mm.

**Verdict: the 0.45 mm form FAILS** on V1 (−19.0 points) and on V2 (LAD −5.8, RCA −8.2).

### What it changes

- **S is 0.5 mm in every Job 0 outcome.** A finer grid would bring a context loss with it, and a 288³ patch would
  also change the batch.
- **The cost estimate was high.** With a fixed patch, an epoch at 0.45 mm costs the same 181 s.

**Caveats:**
- The check measures context, not accuracy.
- The roots are proxies.
- The thresholds are pre-registered but mine.

## 2. Can a temperature fit see Janus 0's inward rim? (§5 item 4)

**Question.** L-A23 names a temperature fit as the calibration check for a rim miscalibration. Does it answer that
question?

**Setup.** `calib60.py` fits a temperature on the five-class softmax and a Platt fit on the foreground log-odds. It
runs on the tuning 60 only, after Job 0. Its self-test uses a tube whose true boundary is at r = 4 voxels, while the
network crosses 0.5 at r = 3.

**Result.**

| Fit | Export equals raw threshold | Rim ECE |
|---|---|---|
| Raw | 0.50 | 0.300 |
| Temperature (T = 1.04) | **0.498** | 0.300 |
| Platt | **0.125** (the truth: 0.119) | 0.015 |

**What it changes.**
- A temperature rescales log-odds about 0, so it **cannot move the 0.5 crossing**. It is blind to the defect it was
  named for.
- The check reports Platt's t_eq = sigmoid(−b/a) as well. That is an NLL cross-check of Rule W's t\*.
- Rule W is not re-run on calibrated probabilities. The map is monotone, so the grid already holds the same export.

## 3. Do the merged scripts fit together? (§5 item 6)

**Setup.**
- Every merged script's self-test was re-run on `dev`.
- `ensemble_chain.py` writes two toy folds as `nnUNetv2_predict --save_probabilities` would, ensembles them with
  nnU-Net 2.8.1's own `ensemble_folders`, and exports them with `threshold_export.py`.
- `gate.py` is a reference gate (L-A5, L-A16, L-A17, D49 Q-R2-3, S's 1.25 %), with nine fixtures.

**Result.**
- All self-tests pass.
- Five interface defects were found:
  1. **Without `--save_npz` the ensemble writes no probabilities**, so neither Rule T nor the export at t_C can run.
     With it, E's `.npz` is the exact mean, t = 0.50 reproduces the ensemble's segmentation, and two copies of one
     fold reproduce it.
  2. Rule T needs eight threshold exports, and Job 0's default makes five.
  3. Janus 0 at t_C = 0.25 is not among Job 0's exports.
  4. `select.json`'s `chosen_t` is a string, so the master plan's `'%.2f' %` fails with a TypeError.
  5. `move_plans_between_datasets` also rewrites `plans_name`, and `data_identifier` if `-tp` differs.
- The gate's heavy-tailed null fired L3 in 0 of 100 draws. A uniform −0.03 LCx loss fired it. The Q4 and Q-R2-3
  branches came out as the wording table says.

**What it changes.** Bridge v3 Part B §5's command block carries all five fixes.

## Data and refusals

| Data | Handling |
|---|---|
| The 620 training labels | Read: headers and voxels. Only aggregate summaries are committed; per-case rows are not |
| Locked-100, sealed and quality-0 labels | Not read |
| CTs and TotalSegmentator outputs | Not read |
| Pool | Not read |
