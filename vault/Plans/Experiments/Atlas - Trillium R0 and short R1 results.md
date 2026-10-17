---
tags: [plans/experiment, trillium, r0, r1, tf1, fp-gate, ostium]
author: Atlas
round: 5
updated: 2026-10-09
status: result
---

# Atlas - Trillium R0 and short R1 results

**R0 passes.** The master recipe trains at 175 s per epoch and peaks at 55.6 GiB. A 1000-epoch R1 therefore takes
48.6 h.

**The short R1 (412 epochs) names well.**

- macro tF1@1.5 is 0.846 as scored. Corrected for the reference ostium, it lies in 0.87–0.90.
- Swaps are 0.9 %.
- Rule renaming (R) and grammar decoding (H) lose to the model's own names (Bridge).

**Two of the headline failures are not what they look like.**

- **The 17 "cut trees" are mostly a fault of the provisional ostium, not of the model.**
  - 11 of the 17 are whole-tree zeros, where the vessel is found (clDice 0.77–0.98) but tF1 is exactly 0.
    - Six flip to a rooted, full score under Bridge's near-identical provisional ostium rule. Bridge's rule in turn
      zeroes seven trees that mine scores fully.
    - Against ImageCAS-X start points, the `thick` rule puts the RCA ostium **30–64 mm from the true one in 5 of 13**
      RCAs that have a truth point. The left ostium is more than 5 mm off in 6 of 80.
  - About **6 of 80 cases are real failures**: four partial mid-tree cuts (three on the LCx) and two RCAs that look
    proximally missed.
  - On the decision table this is "few cuts" for the LAD and LCx (gap 0.017 and 0.021 once the ostium artefact is
    removed). The RCA sits in the middle band (0.07), so P1′ is judged on its merits.
- **The FP gate fails for real, and diffusely.**
  - 1.49 components per case (95 % CI 1.21–1.78); median 1; 38 of 80 cases have ≥ 2. It is not a few outliers.
  - The only prior measurement on the same reference, a released nnU-Net, scored 1.22.
  - FP counts rise weakly with how much vessel ImageCAS-X traces beyond the ImageCAS mask (ρ = 0.27, p = 0.02).
    That suggests part of the FP count is real vessel the reference omits. It is not proof, because the predictions
    are on `$SCRATCH` and no component has been inspected.
  - My pre-registered response names the window first (ablation A2). A census of the FP components is needed before
    any other lever.

## R0 (A6)

| `n_proc_DA` | s / epoch | loader-wait share | GPU step (median) | peak allocated | peak reserved |
|---|---|---|---|---|---|
| 12 | **174.9** | 0.02 % | 0.65 s | 42.5 GiB | **55.6 GiB** |
| 22 | 175.3 | 0.02 % | 0.65 s | 42.5 GiB | 55.7 GiB |

- **GPU-bound, not loader-bound.** 12 workers are enough. None of the loader levers (GPU spatial transform, lower
  augmentation probabilities) is needed.
- **VRAM.** My saved-tensor model predicted ≈ 54 GB of activations; the measurement is 42.5 GiB allocated and
  55.6 GiB reserved. Batch 1, checkpointing and the fallback patch are all retired.
- **1000 epochs: 48.6 h** on one H100, inside the plan's 27–85 h band (central 45 h). That is three 23:50 chained
  jobs, or about 49 H100-h.

## Short R1: what ran

- **Data.** 560 ImageCAS-X train cases → 80 ImageCAS-X val cases.
- **Labels.** The projected proxy (D0/D1/D1b). A4 QA was not applied in the job.
- **Recipe.** ResEnc, 0.5 mm iso, 256³ patch, batch 2, mirroring off, fixed window [−300, 1300].
- **Schedule.** 412 epochs, full poly-LR schedule; 21.8 h wall time in total.
- **The window was applied as intended.** The planner's own fingerprint window on the full data is
  [−169, 719] HU. My 6-case estimate was [−164, 640]. The job overwrote it, and the plans file used for training
  carries `percentile_00_5 = −300`, `percentile_99_5 = 1300`, mean 100, sd 400 (in the plans file and in
  `train.log`). The planner's own value is recorded deliberately in `planner_output.json`.
  - The full-data value shows the default window would clip everything above 719 HU, which includes calcium. That
    is the A2 ablation's question, not a defect of this run.
- **Training curve.** The EMA pseudo-Dice passes 0.80 by about epoch 70 and plateaus from about epoch 150
  (0.834–0.836). The last-epoch per-class pseudo-Dice is 0.905, 0.840, 0.776 and 0.828. This hints that 1000 epochs
  will add little, which matters for the 48.6 h cost (see v5 §2.5).

## Val (80 cases, reference = projected proxy, provisional `thick` ostium)

| | LM | LAD | LCx | RCA | macro |
|---|---|---|---|---|---|
| tF1 @1.5, as scored | 0.964 | 0.869 | 0.812 | 0.771 | **0.846** |
| tF1, better of the two provisional ostium rules (Atlas / Bridge) | 0.964 | 0.890 | 0.830 | 0.814 | **0.871** |
| per-class clDice (tF1's upper bound if every tree is rooted) | 0.964 | 0.907 | 0.851 | 0.884 | 0.900 |
| clDice − tF1, as scored | 0.000 | 0.039 | 0.039 | **0.114** | |
| clDice − tF1, better rule | 0.000 | 0.017 | 0.021 | 0.070 | |
| Dice | 0.904 | 0.844 | 0.771 | 0.840 | 0.838 |

- **Swap rate:** 0.9 % of detected centreline (gate < 5 %).
- **Raw FP components:** 1.49 per case (gate ≤ 1).
- **Bridge's arms on this model** ([[Bridge v4]]'s experiment):
  - D (the model's own names) 0.847;
  - R −0.013 [−0.025, −0.002];
  - H −0.013 [−0.022, −0.006];
  - O (oracle names) +0.010 [+0.005, +0.015].
- The direct model leaves 0.01 of naming headroom, and neither competitor captures it. A7: R and H stay QA only.

## The 17 cut trees, case by case

Flag: per-class clDice − tF1 > 0.10 (the Round 4 table). Below, "Atlas" and "Bridge" are the two provisional
ostium implementations. Both use a reference-derived "thickest endpoint" (Bridge's left rule takes the LM end
farthest from the LAD/LCx). Both score the same predictions.

| Kind | Cases | Evidence |
|---|---|---|
| **Ostium artefact, other rule roots it fully** | c0038 RCA, c0133 LAD+LCx, c0252 RCA, c0288 RCA, c0848 RCA, c0956 LAD+LCx (6) | Bridge tF1 0.71–0.97 ≈ clDice. Where the left truth exists, my left root is 17.6 mm (c0133) and 30.3 mm (c0956) from the ImageCAS-X start point |
| **Ostium artefact under both rules (likely)** | c0163 RCA, c0368 RCA, c0606 RCA, c0613 LAD+LCx, c0744 RCA (5) | c0163: the shared root is **60.5 mm** from the ImageCAS-X RCA start point. c0613: the left root is **116.7 mm** from the left start point. c0368, c0606 and c0744: the shared root is 42–57 mm from the RCA endpoint nearest the left ostium. clDice 0.88–0.98 |
| **Real: partial mid-tree cut** | c0095 LAD (0.80 vs clDice 0.93), c0186 LCx (0.56 vs 0.66), c0826 LCx (0.73 vs 0.84), c0878 LCx (0.68 vs 0.94) (4) | Same value under both rules; left ostium within 2.6 mm of truth |
| **Real (probably): RCA proximally missed** | c0717 RCA (0 vs 0.77), c0560 RCA (0.09 vs 0.83) (2) | Root at, or 13 mm from, the RCA endpoint nearest the left ostium. No RCA truth point in these cases |

**Why the `thick` rule fails here.**
- On 13 val RCAs with an ImageCAS-X start point, my rule is within 4 mm of truth in 7, 6 mm off in one, and **32–64 mm
  off in 5**. Bridge's rule is identical on 12 of the 13 and 40 mm off in the thirteenth (c0186).
- ImageCAS annotations often end bluntly in a mid-calibre distal RCA, so a distal endpoint can be the "thickest".
- The tF1 then zeroes the tree whenever the prediction stops short of that distal end (an artefact) and is
  unaffected when it doesn't, which is why the zeros flip between two near-identical rules.
- The rule of record (A1: aorta contact, cross-checked by `thick` / `pool_thick`, disagreement > 5 mm flagged) is
  designed for exactly this. Round 4 measured it with 0 silent errors in 130.
- Consequence: **every val number in this round is provisional (A9) and biased low on the RCA**, mine and Bridge's
  alike. Bridge's paired differences are unaffected, because every arm shares the reference ostia.

**Reading under the pre-registered table** (Round 4: ≤ 0.03 few cuts, > 0.10 many, between: P1′ on its merits):

- **LAD and LCx: few cuts** (0.017 and 0.021 under the better rule). The small-patch model's 3-in-8 cut rate does
  not transfer. About 4 in 80 cases have a real partial cut, three of them on the LCx.
- **RCA: middle band** (0.070). At least four of its five remaining zeros have roots demonstrably or very likely in
  the wrong place, so the RCA gap is probably ≤ 0.03 under the A1 ostium. That stays unproven until it is re-scored
  with the aorta rule.
- **P1′** stays a candidate. It is decided by Delta's C2 comparison on this model, as Round 4 ruled. There is no
  case for promoting it.

## The FP gate

| | value |
|---|---|
| mean FP components per case (≥ 100 voxels, touching no reference voxel) | **1.49** (bootstrap 95 % CI 1.21–1.78) |
| cases with 0 / 1 / 2 / 3 / 4 / 5 | 23 / 19 / 23 / 8 / 5 / 2 |
| cases passing ≤ 1 | 42 / 80 |
| share of all FP components in the 15 worst cases | 45 % |
| predicted components touching the reference, per case | 2.9 (reference: 2.1) |
| Spearman with case tF1 / Dice | −0.16 (p 0.16) / −0.19 (p 0.08) |
| Spearman with ImageCAS-X voxels outside the ImageCAS mask (count of ≥ 100-voxel pieces) | **+0.27 (p 0.017)** |
| prior: released nnU-Net, same thick reference ([[Delta - Against the thick reference, bridging still joins false positives 6 times in 13]]) | 1.22 |

What this shows:

1. **The failure is real and broad.** Even trimming the worst 10 % of cases leaves 1.19 per case. It does not come
   from bad cases: FP count barely tracks tF1.
2. **No model measured so far passes ≤ 1 against the ImageCAS mask.** The gate was set without a baseline (A2). I
   do not ask for it to move. I record that its threshold is untested against any achievable model.
3. **Part of the FP count may be vessel the reference omits.**
   - Every ImageCAS-X piece touches the ImageCAS mask: no case has a detached ImageCAS-X vessel. Yet ImageCAS-X
     traces a median of 3.9 pieces of ≥ 100 voxels beyond the mask (5.8 % of its vessel voxels).
   - FP counts are higher where it does so more.
   - Under D0 such vessel is still a false positive, because the mask is the reference. So this would change the
     *lever*, not the verdict. Training cannot unlearn real vessel the labels sometimes include and sometimes omit,
     and the gate would then have to be met by a calibrated threshold or the window, not by more epochs.
4. **The window is the pre-registered first suspect.** The default window ([−169, 719]) is what the A2 ablation
   tests. The fixed window shows the model more of the fat/vessel contrast and calcium. That may help or hurt FP;
   only the paired run can say.

The FP components themselves (size, softmax confidence, HU, distance to the tree, overlap with ImageCAS-X,
location) need the predictions, which are on `$SCRATCH`. That census is the cheapest decisive step, and it is the
first phase of the proposed run.

## What the results change

| Pre-registered row | Result | Decision |
|---|---|---|
| R0 ≤ 306 s / epoch, ≤ 75 GB | 175 s, 55.6 GiB | R0 passes; R1 = 48.6 h; batch 1 / checkpointing / fallback patch retired |
| Loader-wait > 30 % | 0.02 % | No loader levers; A3 (rotation) is a pure accuracy question |
| Few cut trees | LAD/LCx yes; RCA middle band under the provisional ostium | P1/P1′ have little to fix on the left; P1′ decided by Delta's C2, not promoted |
| Swap ≥ 5 % or left classes well below RCA | 0.9 %; R/H lose | A7: ship the model's own names; R and H stay QA |
| FP > 1 per case | 1.49 | Gate fails; window ablation A2 first, after an FP census |

## Proposed next Trillium run (`trillium/atlas`, same contract: one command, no arguments, 1 H100 ≤ 23:50, `def-aso22`, never writes to Girder)

**Phase A: diagnosis of run 1** (≤ 1.5 h, no training).
1. Copy the 80 val predicted segmentations (uint8, ≈ 25 MB in total) into `results/` so CPU work can continue in
   the repo. The softmax and weights stay on `$SCRATCH`.
2. **FP census**, one row per FP component:
   - voxels and mm³;
   - predicted class;
   - mean and max softmax (from the saved npz);
   - mean HU;
   - distance to the reference tree;
   - fraction inside ImageCAS-X labels (dilated 1 mm);
   - distance to the blood pool;
   - centroid.
3. **Re-score** with the `src/segtrain.tf1` port (A9) using `pool_thick` from the CT, and with ImageCAS-X
   start-point ostia (left and right centreline files fetched on the login node, ≈ 160 small VTKs).

This settles both open questions above: how many trees are really cut, and what the FPs are.

**Phase B: window ablation A2** (≈ 21 h).
- **Change.** Identical to run 1 except the default fingerprint window [−169, 719]. That means re-preprocessing
  (39 min); 412 epochs on the same split.
- **Scoring.** Same predict and score, plus the Phase A census on its predictions.
- **Decision.**
  - Paired on the 80 val cases: FP difference and tF1 difference (rule-of-record ostium, bootstrap CI).
  - The window is chosen by tF1 under the ablation rule (CI excludes 0). If tF1 ties, the window with fewer FP
    components wins.
  - If neither window passes the gate, the census decides the next lever:
    - mostly low-confidence blobs → a calibrated foreground threshold (raw = argmax at a threshold chosen on val,
      which is still "raw" under A2);
    - mostly inside ImageCAS-X / real vessel → the gate's reference question goes to the judge.

**Why this run, rather than starting the 1000-epoch R1.**
- R1 at full length costs 48.6 h, and the plateau from epoch ~150 suggests it buys little.
- Its window has to be settled first anyway (A2 is in the plan's ablation list).
- The census needs no training.

R1 full length runs next, as three chained jobs, with the window that wins.

Scripts and per-case data for this note: `experiments/Atlas/r5_reference_geometry.py` (proxy, three ostium rules,
ImageCAS-X start points, ImageCAS-X-outside-mask pieces) → `r5_reference_geometry.jsonl`; `r5_analyse.py`. The raw
results are in `trillium-results/round5/atlas/results/`.

## Limits

- **The reference is the projected proxy, not team reads.** A4 QA was not applied. The model was trained and
  scored on the same convention.
- **Every tF1 here is provisional (A9).** The "better of two rules" row is an optimistic estimate, not a measurement
  with the rule of record.
- **The RCA ostium check covers 13 cases.** They are the only val cases with a right-centreline file. The "endpoint
  nearest the left ostium" heuristic is itself right (≤ 5 mm) in only 8 of those 13, so it supports, but does not
  prove, the both-rules-wrong group.
- **The FP analysis is reference-side only.** No FP component was looked at.
