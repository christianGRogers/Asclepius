---
tags: [plans, candidate, imagecas-x, pseudo-labels, label-efficiency, nnunet]
author: Crucible
round: 1
version: 1
updated: 2026-10-04
---

# Crucible v1 — The labels are already here: train on ImageCAS-X's expert lumen now, fix the seed before the team inherits the wrong one, and let team labels refine

## 1. Thesis

My opening thesis was "don't wait for labels — manufacture them, then refine".
The experiments changed what that means. **800 of our 1000 cases already carry
expert per-segment labels** (ImageCAS-X, CC BY 4.0, case `c{id-1}`, 800/800
header-identical), so there is nothing to wait for and little to manufacture.
What the measurements found instead is that the **Girder binary masks — which
SegQueue hands annotators as the tree to "split", and which the master plan
trains its first model on — are not lumen**: they are 3.6× the expert lumen,
Dice 0.41 against it, and 47 % of their voxels sit > 1.5 voxels outside it at
median 16–38 HU (fat, wall, myocardium; contrast lumen is ~370 HU). So the plan
is: (a) **train a multiclass nnU-Net now on ImageCAS-X's own lumen and names**
(14 classes, read out as 4 under whichever side-branch convention the team
writes down — that choice decides 27 % of vessel voxels and has not been made);
(b) **replace the SegQueue seed** with ImageCAS-X-derived labels (800 cases) and
model predictions (200) before the team inherits the thick convention, so team
labels and training labels share one definition of lumen; (c) **self-train only
where no expert label exists** (the 200 non-diagnostic scans) and fold team
labels in as they arrive through a loss that accepts 4-class labels on a
14-class model. Generic semi-supervised machinery (mean teacher, CPS) is
dropped: its documented gains are at tens of labels, not 640.

## 2. Recipe

### 2.0 What exists today (measured)

| Fact | Evidence |
|---|---|
| ImageCAS-X: 800 cases, 14 classes, on our grid; case `c{id-1}`; split 560/80/160; 160 test cases double-read; 200 excluded = image quality 0 | [[Crucible - ImageCAS-X is real and its 800 cases are our cases c(id-1)]] (independently reproduced by Bridge and Atlas) |
| Girder masks = original ImageCAS labels: Dice 0.412 vs ICX lumen, 3.58× volume, cover 92 % of it; 47 % of their voxels > 1.5 vox outside at median 16–38 HU | [[Crucible - Original binary masks disagree with ImageCAS-X]] |
| Side branches = 26.6 % of ICX lumen voxels; main four = 73.4 % | same note |
| SegQueue starts every branch as a full copy of the seed and the annotator cuts it back; edits are confined to the seed | `slicer/SegQueue/SegQueue.py` `_startBranchesFromSeed`, `docs/SEGQUEUE.md` |
| The repo already intends ICX-quality seeds (task 711: "Seeding an annotator with a mask that confidently outlines a pulmonary vein costs more than seeding them with nothing") | `configs/tasks/Dataset711_CoronaryLumenX.yaml` |
| Given a clean lumen, naming 4 classes is geometry: rule namer median voxel acc. 0.997; on Girder masks LM fails (< 0.8) in 23/61 | [[Crucible - A rule-based namer turns a clean binary tree into 4 classes]]; Bridge's better labeller gets 95 % of held-out cases fully right on Girder masks ([[Bridge - A rule-based labeller names LM, LAD, LCx and RCA on our binary masks]]) |
| z = 0.5 mm in all 1000; 0.5 mm iso is lossless; a 256³ patch at 0.5 mm holds the tree | [[Atlas - Resampling to 0.5 mm isotropic loses nothing measurable, 0.7-0.8 mm does]], [[Atlas - A 128 mm patch at 0.5 mm holds the whole tree and the LM in almost every training patch]] |

### 2.1 Decision required this week (human, not GPU): the lumen convention and the seed

The team's labels are the evaluation reference, and today they will be
partitions of the Girder mask. Two coherent options; the plan recommends A.

- **A (recommended): expert lumen.** Re-seed SegQueue before more labelling:
  for the 800 ICX cases ship the **ICX merged lumen** as `coronary_arteries`
  (no code change — it is a binary mask); optionally (≈1 engineer-day) let
  `_startBranchesFromSeed` start each branch from the ICX-derived 4-class map
  instead of four copies of the tree, turning splitting into *verification*.
  For the 200 non-ICX cases ship the M1 prediction (§2.3). Why: the excess
  in the Girder mask is not lumen by HU; downstream lumen uses (stenosis,
  plaque, FFR — [[What downstream coronary tasks need from a segmentation]])
  need the lumen; it removes a 2.6:1 tissue:lumen bias from every label; and the
  same 800 labels become a perfect-convention training set on day one.
- **B: keep the Girder seed.** Then team labels are thick, and the training
  target must be thick too: use Atlas's proxy (ICX names projected onto the
  Girder mask). This plan then reduces to Atlas v1 §2.1 plus §2.5 below. I
  include B as the fallback so the plan never trains to one convention and is
  scored on another.

Whatever is chosen, the **side-branch convention** must be written into the
SegQueue instructions now: are D1/D2 part of LAD, OM/L-PDA/L-PLA part of LCx,
R-PDA/R-PLA part of RCA ("territory"), or background ("trunk")? Ramus (IM) →
which class? It is 27 % of voxels, and the hints ("follow the anterior
interventricular groove") do not answer it.

### 2.2 Data preparation (CPU, now — scripts exist)

- Fetch ICX labels by HTTP range read, 13 MB, CRC-checked
  (`experiments/Crucible/fetch_icx.py`); map `id → c{id-1}`.
- Label sets per ICX case: **L14** (ICX native, 0–14); collapse tables to
  4-class **territory** and **trunk** are applied at read-out, not baked in.
- Splits, fixed now: ICX train 560 (training), ICX val 80 (monitoring),
  **ICX test 160 sealed** — never used for training, initialisation or
  model selection (the leakage constraint task 711 already states). The 200
  non-ICX cases: 20 go to the sealed test once team-labelled; 180 are the
  self-training pool.
- Preprocessing per Atlas's measurements: nnU-Net v2 `3d_fullres`, target
  spacing 0.5 mm isotropic, fixed CT window [−300, 1300] HU
  ([[Atlas - nnU-Net's automatic CT window on lumen labels flattens 38 percent of the heart box]]);
  note the default window is computed from *labelled* voxels, and with the
  tight ICX lumen it would clip even harder than with the Girder masks.

### 2.3 Model M1 — trained now on ICX (GPU, week 1)

- **nnU-Net v2 ResEnc**, `-gpu_memory_target 60` at 0.5 mm iso (planner:
  patch 256³, batch 2 — Atlas's sweep). Deep supervision on.
- **15 output channels (bg + 14 ICX classes).** Read-out to 4 classes by
  **summing softmax probabilities** within each 4-class group (territory:
  LAD = LAD+D1+D2, LCx = LCx+OM1+OM2+L-PDA+L-PLA, RCA = RCA+R-PDA+R-PLA;
  trunk: side-branch groups summed into background), then argmax. IM and
  "Other" go to whichever group the written convention names. Why 14 and not
  4: the convention is undecided and touches 27 % of voxels; the 14-class model
  serves both answers without retraining, and the anatomical names are free
  supervision. Paired check (A1 below) that it costs nothing on the 4-class
  read-out.
- **Loss: Dice + CE** (default). Rare-class Dice terms (L-PDA in 5 % of cases)
  are averaged by nnU-Net over present classes in the batch; if they
  destabilise training (A1 shows it), fall back to CE on the 14 classes plus
  Dice on the 4-class groups.
- **Sampling: nnU-Net default**; at a 128 mm patch every main class is in
  ≥ 98.5 % of patches (Atlas). **Augmentation:** defaults with **mirroring
  off on all axes** (chirality; [[Mirroring is ruled out for multiclass, and it is a chirality problem, not only a left-right one]]).
- **Schedule:** 1000 epochs × 250 it, no early stopping in v2; checkpoint
  every 50 epochs, chain-resume at 23 h. Estimated 40–60 H100-h (Atlas's
  extrapolation from nnU-Net Revisited; R0 measures it).
- **Post-processing:** per-class removal of components < 100 voxels; never
  largest-component ([[Largest-component post-processing is wrong for coronaries]]).
- **Sanity anchor on day 7:** merged-lumen Dice of M1 on the sealed ICX test
  should land near ICX's own nnU-Net (89.8 ± 3.2) and below inter-observer
  92.8 (arXiv:2608.30404, Table 2); per-class Dice vs their double-read
  per-class ceilings (LM 91.9, LAD 92.3, LCx 84.8, RCA 95.3; Table 1). This is
  the only external calibration that exists for these labels.

### 2.4 Manufactured labels for the 200 non-ICX cases (self-training, week 2)

- M1 (+ no-mirror TTA) predicts all 200 non-diagnostic scans → 14-class
  pseudo-labels. QA per case, no GPU: (i) rule-namer consistency (name the
  union with the rule namer; disagreement in LM/LAD/LCx flags the case);
  (ii) prediction volume outside the Girder mask (the Girder mask holds 92 % of
  true lumen, so > 15 % of predicted voxels outside it flags a hallucination);
  (iii) softmax entropy on the centreline.
- These pseudo-labels are **annotator seeds first** (option A) and training
  data second: M2 = M1 fine-tuned 250 epochs on ICX ∪ {pseudo-labels passing QA,
  loss weight 0.5}. Adopt M2 only if it beats M1 on the 20 sealed quality-0
  cases once they are team-labelled (paired bootstrap, §3). This is the one
  place pseudo-labelling can help: those scans are a distribution (motion,
  step artefacts) no expert label covers. If the HU fallback is ever needed
  (no model yet), `girder_mask ∧ HU > 0.5·p95` gives Dice 0.78 vs ICX
  ([[Crucible - A half-maximum HU rule recovers a tight lumen from the Girder masks]]).

### 2.5 How team labels are used as they arrive

| Team labels in hand | Action | GPU |
|---|---|---|
| 0 | M1 trained; seeds replaced (option A); M1 predictions seed the 200 | ~55 h |
| first 20 (ICX cases) | **Convention check, pre-registered:** per-class Dice and clDice of team labels vs ICX territory and trunk read-outs, and vs the Girder-projected proxy. Highest macro clDice fixes the read-out; if the team's merged lumen has Dice < 0.75 vs ICX lumen (i.e. they drew thick), switch to option B targets | 0 |
| sealed test: 80 ICX-test + 20 quality-0 (labelled **first**), 30 of them double-read | becomes the decisive test; never trained on | 0 |
| every +100 training labels | Fine-tune 250 epochs. Team 4-class labels supervise the 14-class model through the **marginal loss** (CE/Dice on the summed group probabilities; Shi et al., MedIA 2021, arXiv:2007.03868): a team "LAD" voxel only says "LAD ∪ D1 ∪ D2", and the model keeps ICX's finer split where it has it. Where a case has both, team labels win for the 4-class groups | ~13 h each |
| ≥ 400 | One paired run: team-only vs team + ICX (marginal) for the final recipe | ~26 h |
| all | **Final:** from scratch, 1000 epochs, 5 folds over the ~900 non-test cases (ICX + team + QA-passed pseudo), ensemble; or the single `all` model if the ensemble gain's CI includes 0 | 50–250 h |

### 2.6 Ablations (paired, 250 epochs each, val fold; adopt only if bootstrap 95 % CI of the per-case difference in the decisive metric excludes 0)

- **A1**: 14-class + summed read-out vs direct 4-class (territory) training.
- **A2**: tight ICX lumen vs Girder-projected proxy (Atlas's labels) as
  training target, both scored against ICX test *and* against the first team
  labels — this measures directly what the seed decision costs.
- **A3**: rotation off (the disputed augmentation).
- **A4**: Skeleton Recall loss (Kirchhoff et al., arXiv:2404.03010) — Delta's topic; one arm only.

## 3. Evaluation

- **Sealed test (decisive):** 100 team-labelled cases — 80 from ICX test +
  20 quality-0 — reported as two strata, never pooled silently. Interim, before
  team labels: the 160 ICX test cases with ICX labels (both read-outs).
- **Decisive metric: macro mean over LM, LAD, LCx, RCA of per-class clDice**,
  case-averaged; class absent in both → dropped for that case, present in one →
  0. Chosen because the two lumen conventions agree on centrelines (clDice 0.80,
  centreline-in-other 0.90) but not on voxels (Dice 0.42)
  ([[Delta - Two references of the same vessels agree on centrelines, not on voxels]]):
  a voxel metric would mostly score which convention the reference used. This
  is the same metric Atlas names; agreeing on the yardstick lets the judge
  compare plans on their merits.
- **Reported with it:** per-class Dice, HD95, branch-swap rate, branch
  detection, components vs reference, LM length error; merged-lumen Dice on ICX
  test for the external anchor; strata by dominance, disease, image quality.
- **Ceiling:** 30 double-read team cases → per-class inter-rater clDice/Dice;
  ICX Table 1 for the expert-lumen convention.
- **Statistics:** per-case paired differences, bootstrap 95 % CI, Wilcoxon
  signed-rank ([[Deciding whether a paired experiment found a real difference]]).

## 4. Evidence

| Load-bearing claim | Evidence |
|---|---|
| ICX exists, CC BY 4.0, 14 classes, maps to our cases `c{id-1}` | [[Crucible - ImageCAS-X is real and its 800 cases are our cases c(id-1)]]; Zenodo 10.5281/zenodo.21887809; arXiv:2608.30404 (read in full) |
| Girder masks are the original ImageCAS labels and are mostly non-lumen tissue | [[Crucible - Original binary masks disagree with ImageCAS-X]] (Dice 0.412 reproduces the paper's 41.8; HU table); paper Suppl. Fig. 7 (plaque, pulmonary vessels, veins in the originals); Delta's calibre (median diameter 2.64 vs 1.32 mm) |
| The side-branch convention moves 27 % of voxels | same note |
| SegQueue makes team labels partitions of the seed | `slicer/SegQueue/SegQueue.py` (`_startBranchesFromSeed`; edits masked to the seed) |
| Naming from a clean lumen is easy; from the thick mask it is fragile for simple rules | [[Crucible - A rule-based namer turns a clean binary tree into 4 classes]]; Bridge's held-out 95 % shows careful rules recover most of it |
| HU rule gives a usable fallback lumen (0.78) | [[Crucible - A half-maximum HU rule recovers a tight lumen from the Girder masks]] |
| A model trained on ICX-quality labels reaches ~89.8–91.2 merged Dice; humans 92.8 | arXiv:2608.30404 Table 2 |
| Semi-supervised gains are a small-label phenomenon: UA-MT on LA, 16 labelled + 64 unlabelled 88.88 vs 86.03 labelled-only vs 91.14 all-80-labelled | Yu et al., MICCAI 2019, arXiv:1907.07034, Table 1 (read); also Tarvainen & Valpola arXiv:1703.01780; Chen et al. (CPS) arXiv:2106.01226; Oliver et al. arXiv:1804.09170 on how SSL gains shrink under realistic baselines; Isensee et al. arXiv:2404.09556 on unvalidated claimed improvements |
| A large noisy set can beat a small clean one | Karimi et al., summarised in [[Fusing multiple annotations and learning from noisy labels]] |
| Pre-annotation anchors annotators to the seed's errors | Shwartzman et al. arXiv:1906.11872, in [[Seeding annotation with model predictions and label efficiency]] |
| Partial / coarser labels can supervise a finer softmax | Shi et al., marginal and exclusion loss, arXiv:2007.03868 (MedIA 2021); nnU-Net ignore label (Gotkowski et al. arXiv:2403.12834; `documentation/ignore_label.md`) as the simpler alternative |
| Spacing, window, patch, no early stopping | Atlas's notes cited in §2 |

## 5. Risks and early detection

| Risk | Detected by | Response |
|---|---|---|
| Project keeps the Girder seed; team draws thick | Convention check on first 20 team labels (team-vs-ICX lumen Dice < 0.75) | Option B: Atlas's projected proxy as training target; decisive metric (clDice) is convention-robust anyway |
| Team's side-branch convention is neither territory nor trunk (e.g. D1 partly LAD) | Convention check: neither read-out reaches 0.80 macro clDice | Train on team labels with ICX as marginal-loss auxiliary only; rewrite the protocol hint |
| 14-class training costs accuracy on the 4 classes | A1 | Switch to direct 4-class territory/trunk |
| ICX labels are tight, team labels from ICX seeds drift (annotators paint outward) | Team union vs ICX lumen per wave | Feed back to the labelling lead; HU-confined painting (150–1000 HU) already in SegQueue |
| Pseudo-labels on quality-0 scans teach artefacts | 20 sealed quality-0 cases; QA flags | M2 adopted only on a paired win; otherwise pseudo-labels remain seeds only |
| Leakage of ICX test into training through init or seeds | Split file fixed now; checksum the split in the run config | M1 never sees the 160; seeds for test cases are ICX labels, which is fine for annotation but those cases never enter training |
| Absent LM / separate ostia (case c0196) and left dominance (5 %) | Rule-namer QA flag (3 large components); stratified metrics | Explicit protocol note: LM class empty is legal |
| GPU time above estimate | R0 benchmark | ResEnc 40 GB preset (Atlas) |

## 6. Comparison

**Master plan / [[Training plan]].** Its step 1 trains a binary model on the
1000 Girder masks and uses its predictions as annotator seeds. Measured, that
model would learn a target that is 3.6× the lumen and 47 % non-contrast
tissue, and the seeds would anchor every team label to it. The repo's own
task 711 already concedes the point for seeds; this plan acts on it. The
plan's "per-branch labels are an open question" is answered: the multiclass
model can start now. Kept from it: nnU-Net 3d_fullres, no cascade, no LCC,
no mirroring, ResEnc, the metrics family.

**Atlas v1.** Same start (day-0 4-class nnU-Net on ICX names, same split,
same decisive metric, same preprocessing — I adopt Atlas's measurements).
The difference is the target: Atlas projects ICX names onto the Girder mask
because team labels will be partitions of it. That makes the model learn the
thick convention on purpose, for all 1000 cases, forever — when the cheaper
fix is to change the seed before the team has labelled much. If the seed
cannot be changed, my fallback *is* Atlas's proxy, so this plan weakly
dominates: identical in world B, better labels in world A. It also keeps the
side-branch decision open (14 → 4 read-out) instead of committing to territory
before the team writes its rule, and it has an explicit plan for the 200
non-diagnostic scans (pseudo-label → seed → paired adoption) where Atlas waits
for team labels.

**Bridge v1.** Bridge's naming is strong (95 % of held-out cases fully right
on the thick masks) and my own rule-namer shows naming is the easy half on a
clean lumen. But Bridge's stage 1 trains on the 1000 Girder masks — the
same thick target as the master plan — and its seeds would carry it to the
team. Its namer is valuable here as QA, not as the segmenter's second stage.

**Delta v1 (draft at time of writing).** Topology-first evaluation and
reconnection post-processing are complementary; this plan uses Delta's
convention-robustness result to choose clDice and would adopt its
post-processing on a paired win.

## 7. Cost

- **GPU (H100-h):** R0 1; M1 ~50; A1–A4 ~55; pseudo-label inference ~3;
  M2 ~13; wave fine-tunes ~6 × 13 = 78; team-vs-mixed 26; final 50–250.
  **Total ≈ 280–480 H100-h**; ~110 before any team label exists.
- **CPU:** label fetch 1 min; split + collapse tables trivial; preprocessed
  data at 0.5 mm ≈ 180 GB (Atlas's estimate).
- **Human:** the convention decision (1 meeting); re-seeding Girder
  (re-upload 1000 `coronary_arteries` items, ~1 engineer-day including the
  optional 4-class-seed extension change); annotator time is expected to
  fall (verifying ICX-seeded names vs splitting a thick tree) but is not
  measured — SegQueue logs time per case, so measure it on the first 40
  (20 ICX-seeded vs 20 Girder-seeded, randomised) before claiming it.

## 8. Changes since previous version

First version. The opening thesis (pseudo-label pretraining + semi-supervised
learning) was **narrowed** after the experiments: ImageCAS-X makes
pretraining-on-manufactured-labels unnecessary for 800 cases, and the evidence
on semi-supervised learning says its gains live at tens of labels. What remains
of the thesis is: start now on the best labels available, manufacture labels
only for the 200 cases nobody has labelled, and stop the worst labels (the
Girder masks) from becoming the team's convention.
