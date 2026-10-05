---
tags: [plans, candidate, master, nnunet, multiclass]
author: Atlas
round: 3
version: 3
updated: 2026-10-04
---

# Atlas v3 — one direct 4-class nnU-Net, one label convention, judged by tree-F1 on the raw prediction

## 1. Thesis

Train **one** nnU-Net v2 ResEnc model end to end on 4-class labels (LM, LAD, LCx, RCA):

- 0.5 mm isotropic, 256³ (128 mm) patch;
- fixed CT window, no mirroring;
- nnU-Net default loss, sampling and inference overlap.

**What the humans decide.** The convention is chosen at D0: expert lumen (A) or Girder seed (B), plus the
side-branch and ramus rules. The procedures of A3 then keep every label, every wave and the sealed test in that one
convention.

**What the evidence decides.** Everything after the network is a set of switchable, pre-registered competitors,
scored on R1's val fold by one implementation of tree-F1 (A1 ostium, A9):

- post-processing P1, P1′ and P2;
- rule renaming R and hybrid decoding H;
- an FP gate computed on the raw prediction, so no repair can game it.

The direct model keeps whatever the evidence lets it keep.

What v3 adds:

- the round-2 amendments, integrated;
- the fallback configuration's extents, now measured in a note;
- the nearest thing to R0 a CPU allows: a measured nnU-Net data-loader throughput and a measured activation-memory
  model for the planned network.

## 2. Recipe

### 2.0 Week-0 order of work

| Step | When | Blocks | Who / cost |
|---|---|---|---|
| **D0: human decision meeting** | this week | R1 (waits ≤ 1 week, then defaults to B) | Clinical lead and labelling lead decide, in writing: (1) lumen convention, A or B; (2) side-branch convention, territory or trunk; (3) **ramus rule**: LAD, LCx or background, which sets namer switch A8; (4) tF1 tolerance (1.5 mm unless changed now); (5) labelling order (sealed test first, plus 20 double reads); (6) whether 4-class seeds are shown, with Crucible's randomised 20/20 trial recommended; (7) if A, whether labels already made from Girder seeds are redone |
| **R0** | first GPU job, 1-GPU `debugjob` ≤ 2 h | every other GPU job | 2 H100-h. Forecast and acceptance in §2.5 |
| CPU prep | now | R1 | Proxy factory (all variants); A4 QA over 800 cases; **trunk-mode A4** if D0 picks trunk; TotalSegmentator aorta on all 1000; port tF1 to `src/segtrain/metrics.py` with the A1 ostium (~1 day); bridge audit wrapper (Delta's); P3/H wrappers (~0.5 day) |

### 2.1 Labels: one convention, enforced

Splits are unchanged:

| Set | Cases | Role |
|---|---|---|
| ImageCAS-X train / val | 560 / 80 | proxy until team-labelled |
| ImageCAS-X test | 160 | 80 sealed; 80 enter training only with team labels |
| quality-0 | 200 | 20 sealed; rest only with team labels |

**Option A (expert lumen).** The ImageCAS-X lumen and names, read out to 4 classes by D0's side-branch and ramus
rule. SegQueue is re-seeded with the ImageCAS-X lumen.

**Option B (Girder seed; the default).** ImageCAS-X names projected onto our mask (nearest within 2 mm, geodesic
for the rest), read out the same way.

**A4 QA, as revised.**

- **Option B, voxel rule:** `ignore` only on near voxels where proxy ≠ Bridge's frozen labeller (median 0.26 %,
  all within 10 mm of the carina).
- **Option B, case rule:** the case is **excluded from training until reviewed** if the ostium is off by > 5 mm,
  the LM Dice is < 0.5, or LAD↔LCx swaps exceed 5 % (10.5 % of cases)
  ([[Atlas - The rule labeller disagrees with the projected proxy on 0.3 percent of voxels, all at the carina]]).
- **Option A:** case flags only.
- **Trunk mode (if D0 picks trunk).** The measurement above used territory counts. Trunk mode compares only voxels
  that both namers call trunk. It needs a per-voxel projection rather than Bridge's per-vertex territory counts. It
  is implemented and re-measured on the same 172 cases **before** R1 reads trunk labels: a CPU half-day.

**A3 convention-keeping procedures (binding, CPU and human cost only).**

1. **Seed tagging.** Every case carries `seed=girder` or `seed=icx`.
2. **Per-case convention monitor on every wave.** Report:
   - Dice of the team label's union against the ImageCAS-X lumen and against the Girder mask;
   - Delta's calibre fraction (centreline in lumen < 4 voxels across).

   A case is "in convention" when its union is closer to the chosen convention's lumen. If **more than 10 % of a
   wave** is out of convention, the wave **halts** for re-instruction. Out-of-convention cases are excluded from
   training and from the sealed test until redone.
3. **Single-convention sealed test.** Every sealed case passes the monitor before it is frozen.
4. **First-20 check (pre-registered).** Run on the first 20 team labels, measured by the A9 tF1:
   - macro tF1, branch-swap rate, and carina-vs-elsewhere error of each proxy variant;
   - calibre (the A5 trigger);
   - convention monitor.

   Rules unchanged from v2: switch variant if beaten by CI; drop proxies if best < 0.80; if the labels are thin, A1
   is mandatory and decisive.

### 2.2 Preprocessing

Unchanged from v2:

- nnU-Net v2.8.1 `3d_fullres`;
- **0.5 mm isotropic**: lossless for image and labels
  ([[Atlas - Resampling to 0.5 mm isotropic loses nothing measurable, 0.7-0.8 mm does]]); on the thin convention a
  0.5 mm round trip leaves tF1@0 ≥ 0.995 in the 10 hardest cases
  ([[Atlas - On the thin convention a 0.5 mm round trip cuts no tree]]);
- **fixed window [−300, 1300] HU**
  ([[Atlas - nnU-Net's automatic CT window on lumen labels flattens 38 percent of the heart box]]);
- no crop.

### 2.3 Model

- ResEnc U-Net from `ResEncUNetPlanner -gpu_memory_target 60 -overwrite_target_spacing 0.5 0.5 0.5`:
  - **256³ patch, batch 2, 7 stages, 142 M parameters, 69 TFLOP per training step**;
  - the tree fits one patch in 98 % of cases, and 97 % of LAD-centred patches contain the LM.
- **Fallback if R0 fails: the ResEnc XL preset at 0.5 mm, 192 × 256 × 256 (96 × 128 × 128 mm).** Its extents are
  now measured (FALLBACK_RESULT) ([[Atlas - The fallback 192 × 256 × 256 patch at 0.5 mm, measured]]).
- Deep supervision on. Under option B, `ignore` = label 5.

### 2.4 Loss, sampling, augmentation

All unchanged:

- Dice + CE;
- default sampling;
- defaults with mirroring off;
- rotation is ablation A3, and also a loader-cost lever.

Skeleton Recall is ablation A4, judged after post-processing.

### 2.5 R0 and the compute model (A6)

**What a CPU can measure before R0**
([[Atlas - Without a GPU, nnU-Net's own loader delivers LOADER_RESULT and the activation memory model predicts MEMORY_RESULT]]):

- LOADER_SUMMARY
- MEMORY_SUMMARY

**Compute forecast (unchanged).** 17.2 EFLOP per 1000 epochs. That is 27 H100-h at the A100's measured utilisation
fraction and 85 h at its absolute rate; central 45 h
([[Atlas - A 256³ training step costs 69 TFLOP, and the CPU loader may set the pace]]).

**R0 protocol** (1-GPU `debugjob`, ≤ 120 min, 24 cores, 188 GiB):

1. `nnUNetTrainerBenchmark_5epochs`: peak VRAM and s/epoch.
2. One epoch each at `nnUNet_n_proc_DA` = 12, 20 and 22: GPU utilisation and iterations/s.
3. Compare both with this note's predictions. Every GPU-hour figure in the plan is then replaced by R0's.

**R0 acceptance:** ≤ 306 s/epoch and peak VRAM ≤ 75 GB. On failure, in order: fallback config (VRAM or s/epoch);
more workers, then a GPU spatial transform, then halved spatial-augmentation probabilities (loader-bound).

**Runs.** Same table as v2:

| Run | Epochs | H100-h |
|---|---|---|
| R0 | — | 2 |
| R1 | 1000 | ~45 |
| A0 (control) | 250 | ~11 |
| A1 native spacing (mandatory if A5) | 250 | ~11 |
| A2 default window | 250 | ~11 |
| A3 no rotation | 250 | ~11 |
| A4 Skeleton Recall | 250 | ~12 |

Ablation rule: paired tF1 CI excludes 0.

**Inference:**

- nnU-Net default **tile step 0.5**, Gaussian weighting, no TTA;
- **`--save_probabilities` on every val and test prediction** (A7), so H, P1′ and any decoding change can be scored
  without re-running the GPU.

### 2.6 Post-processing (A2 revised, A7, A8): competitors, not defaults

**Always on:**

- threshold, then drop components < 100 voxels;
- never delete a component ≥ 100 voxels;
- never force left and right apart;
- no largest-component logic.

**FP gate** = predicted components touching no reference vessel, computed on this **raw** prediction, before any
step below (binding).

**Candidates, each off until it wins on R1 val by the A9 tF1 (paired CI excludes 0):**

| Step | What | Prior evidence | Adoption rule |
|---|---|---|---|
| P1 | 3 mm geometric bridging (Delta) | +0.010 tF1 on 17 real predictions; 5 of 12 joins attached FP blobs ([[Delta - Real bridging on 17 nnU-Net predictions gains little alone, half its 3 mm joins are false positives, and gap-centred re-inference makes it work]]) | CI, **and** the bridge audit shows no FP-blob joins beyond reference-supported ones; not expected to pass |
| P1′ | Gap-centred re-inference + support-gated bridging (Delta) | Unproven: CI touches 0, confounded by tile step 0.75 | **Judged only against the tile-step-0.5 baseline** that R1 uses. If default overlap already closes the gaps, P1′ is dropped |
| P2 | Label repair (Delta `postproc.py`, regression-tested) | Fixes islands, not carina | CI |
| P3 = R | Rule renaming of the model's vessel mask (Bridge's frozen labeller, naming bridges only, ramus switch set by D0, A8) | Within 0.007 (ramus excluded) to 0.037 (all classes) tF1 of oracle naming on a small-patch binary model | Ship only if CI excludes 0 in its favour **and** its swap rate is no higher (A7) |
| P3b = H | Bridge's hybrid decoding from saved softmax | Unmeasured; no prior weight | Same as R |

**Bridge audit (Delta's, binding; it replaces v2's off-reference tube count).** Per case:

- bridges made;
- orphans with no reference support;
- cross-tree joins;
- FP components before and after.

The audit covers P1, P1′ and any naming joins R makes. Order when several pass: P1/P1′ → P2 → R/H. The QA flags
are always computed.

### 2.7 How labels arriving over time are used

| Team labels | Action |
|---|---|
| 0 | D0; R0; CPU prep; R1 + A0–A4; P1–H judged on R1 val |
| first 20 | First-20 check (§2.1.4): switch / drop / A1-mandatory, as pre-registered |
| every wave | Convention monitor; halt at > 10 % out of convention; seed tags |
| 100 sealed + 20 double reads | Monitor-passed, frozen; inter-rater tF1 ceiling |
| +150 / +300 / +600 | 250-epoch fine-tune on team ∪ proxy (team overrides); reviewed flagged cases re-enter |
| ≥ 600 | Paired run, team-only vs team + proxy |
| all 900 | Final from scratch, 1000 epochs; 5-fold only if the CV ensemble beats single by tF1 |

## 3. Evaluation (A1 revised, A9)

**Decisive metric: macro tF1 @ 1.5 mm.** From R1 on, only the ported `src/segtrain` implementation decides (A9). It
is regression-tested on Delta's E3 perturbations. Every number in the vault before it, including this plan's, is
provisional.

**Ostium (A1 revised).** For each tree:

- primary: the endpoint within 5 mm of the TotalSegmentator aorta (run on Trillium for all 1000);
- cross-check: Delta's `thick` and `pool_thick` rules;
- a tree where the rules disagree by > 5 mm is flagged to a human, not scored silently;
- validated on 30 val cases against ImageCAS-X `start_points` before any sealed-test scoring.

**No comparison mixes ostium definitions** (A9).

**FP gate** on the raw prediction, ≤ 1 component per case on average.

**Reported alongside:**

- per-class clDice, Dice, HD95;
- β₀ vs the reference's own count;
- swap rate, LM length error, detection;
- the bridge audit.

Results are stratified by dominance, disease and image quality.

**Acceptance:** within 5 tF1 points of team inter-rater per class; FP ≤ 1; swap < 5 %.

## 4. Evidence

All v2 evidence rows stand. New this round:

| Claim | Evidence |
|---|---|
| Fallback 192 × 256 × 256 at 0.5 mm: extents and LM visibility | [[Atlas - The fallback 192 × 256 × 256 patch at 0.5 mm, measured]] |
| CPU loader throughput and memory model for the 256³ config | [[Atlas - Without a GPU, nnU-Net's own loader delivers LOADER_RESULT and the activation memory model predicts MEMORY_RESULT]] |
| Bridging alone +0.01; half its joins are FP; re-inference unproven | [[Delta - Real bridging on 17 nnU-Net predictions gains little alone, half its 3 mm joins are false positives, and gap-centred re-inference makes it work]] |
| Cross-checked ostium finds 116/116 | [[Delta - Two cheap ostium rules find 116 of 116 true ostia, and their disagreement flags every miss]] |
| Rule naming of a predicted tree is within 0.007–0.037 of oracle naming | [[Bridge - On real stage-1 output, the two-stage namer is within 0.01-0.03 tree-F1 of perfect naming]] |
| A perfect model in the wrong convention loses 0.19 tF1 (one direction) | [[Crucible - A perfect segmentation in the wrong lumen convention loses 0.19 tree-F1]] |

## 5. Risks and early detection

The v2 table stands, with these changes:

| Risk | Early signal | Response |
|---|---|---|
| Mixed conventions (largest measured lever, 0.19 tF1 one way) | Per-wave convention monitor | Halt the wave at > 10 %; exclude and redo |
| Repair hides FPs | FP gate on the raw prediction; bridge audit | Repair adopted only with a clean audit |
| P1′ gain is just overlap | Its baseline is tile step 0.5 | Drop P1′ |
| Loader-bound at 256³ | This round's loader note; R0 | Workers → GPU spatial transform → lower augmentation probabilities |
| Every real-prediction number shares one small-patch model (ruling C3) | — | Nothing about cut rates is assumed until R1 val |

## 6. Comparison

All three challengers now run on the master's model, data, schedule and metric. Their contributions are in this
plan as competitors with pre-registered adoption rules:

- Crucible's convention procedures (A3);
- Delta's ostium, gate order and audit (A1, A2);
- Bridge's renaming and ramus switch (A7, A8).

Accepting them costs no GPU time and none of the recipe's evidenced choices. The decisive fact still open is R1 val:
D vs R vs H, and P1/P1′, under one metric.

## 7. Cost

As in v2: **≈ 220–470 H100-h**, ~105 h before any team label. Added this round:

- engineering: audit wrapper and trunk-mode A4, ~1 day if trunk is chosen;
- human: per-wave convention monitor review (minutes per wave); possible redo of Girder-seeded labels if A is
  chosen (D0 item 7).

## 8. Changes since v2

1. **A1 revised:** aorta-contact ostium cross-checked against `thick`/`pool_thick`, disagreement flagged;
   validated against ImageCAS-X `start_points`.
2. **A2 revised:**
   - FP gate on the raw prediction;
   - Delta's audit replaces my tube count;
   - P1 demoted;
   - P1′ added, judged against tile step 0.5;
   - inference fixed at step 0.5.
3. **A3 strengthened:** seed tags, per-wave monitor with a 10 % halt, single-convention sealed test.
4. **A4 revised:** measured form adopted; trunk mode required before R1 if trunk is chosen.
5. **A7:** R with Bridge's adoption rule; `--save_probabilities`; H as P3b.
6. **A8:** ramus is a namer switch set at D0.
7. **A9:** only the ported tF1 decides from R1 on.
8. **Fallback extents** moved into a measured note.
9. **R0 pre-measurements:** loader throughput and memory model.
10. **D0 item 7:** redo of Girder-seeded labels.
