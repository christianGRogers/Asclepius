---
tags: [plans, candidate, two-stage, branch-labelling]
author: Bridge
round: 1
status: candidate
updated: 2026-10-04
---

# Bridge v1 — segment the tree, then name it

## 1. Thesis

The 4-class target is the binary lumen **partitioned** into LM / LAD / LCx / RCA — SegQueue literally
asks annotators to "split an existing tree into LM / LAD / LCx / RCA" (`docs/SERVER-SETUP.md`). So
the task factorises into *is this voxel vessel* (hard, needs native resolution, and we have **1000
labels for it today**) and *which vessel is it* (a few discrete decisions per case: which tree is
left, where the left ostium is, where the LM ends, which child is the LAD). Train stage 1 — a native
-resolution binary nnU-Net — now, on all 1000 masks. Build stage 2 — a graph labeller on the
stage-1 skeleton that propagates names through connectivity — now, with no GPU, and learn only its
few hard decisions from the per-branch labels as they arrive. Measured on this cohort, a frozen
version of that labeller names our binary masks with **98.9 % pooled voxel agreement** with the
independent ImageCAS-X expert labels and gets all four classes ≥ 0.8 Dice in **94.9 %** of 59 cases it
had never seen (ostium right in 98.3 %), and its one learned part needs **5–10 labelled cases**. That decoupling makes the plan label-efficient,
topologically consistent by construction (every class is a connected sub-tree), and useful on day 1
as the pre-segmentation that turns annotation into a check. The plan keeps a **direct multiclass
nnU-Net as a paired comparator arm** and says in advance what result would make me abandon the
thesis (§3).

## 2. Recipe

### 2.0 Data preparation (now, CPU)

- **Grid:** 512×512, in-plane 0.29–0.47 mm (median 0.35), **z = 0.5 mm in every case** (Atlas, Crucible,
  Delta and my own 155-case pass agree). Native target spacing (0.5, 0.35, 0.35).
- **ImageCAS-X** (Bransby et al., arXiv:2608.30404; Zenodo 10.5281/zenodo.21887809, CC BY 4.0): 800
  per-segment label maps on our exact grid, case `c{id−1}` ([[Crucible - ImageCAS-X is real and its 800 cases are our cases c(id-1)]];
  I reproduced the mapping independently, 800/800 header-identical). Fetched by HTTP range read, 13 MB.
  14→4 mapping: LM=1; LAD=LAD+D1+D2; LCx=LCx+OM1+OM2+L-PDA+L-PLA; RCA=RCA+R-PDA+R-PLA; IM and "Other"
  decided by the parent they hang from.
- **Names on our masks, not theirs.** ImageCAS-X's lumen is ~3.3× thinner than ours (binary Dice 0.43;
  93 % of their voxels lie inside our mask; 86 % of our voxels are within 2 mm of one of their vessels):
  [[Bridge - ImageCAS-X names transfer onto our binary masks, which are three times fatter]]. Their
  *names* transfer onto our lumen by nearest-voxel projection; the 14 % of our voxels on branches they did
  not trace are named by the stage-2 graph (they inherit from their parent).
- **Splits (fixed now, before any training):** locked test = the **first 150 cases the labelling team
  completes**, drawn from ImageCAS-X's own 160-case test list where possible (so the test set also carries
  an independent second reading), stratified by dominance; 40 of them double-annotated by our team for an
  inter-rater ceiling. The 200 ImageCAS-X-excluded (non-diagnostic) scans stay in stage-1 training (their
  binary masks exist) and are reported as a separate stratum, never in the main test.

### 2.1 Stage 1 — binary lumen (train now; 1000 labels exist)

Adopt [[Training plan]] §1–3 for the configuration rather than re-argue it: nnU-Net v2 `3d_fullres`,
native spacing, no cascade, no heart crop, no largest-component post-processing, components < 100 voxels
removed (ImageCAS-X's rule; Delta shows it deletes no real vessel). Planner at 70 GB (patch 192×320×320 ≈
96×112×112 mm, batch 2 — Atlas's sweep). Loss Dice+CE (+ Skeleton Recall as the one topology variant
worth a paired run; Delta's note). Two things the two-stage design changes:

- **Mirroring and rotation stay on** (nnU-Net defaults). Binary has no chirality; the [[Training plan]]
  §4 ban on mirroring exists only because a multiclass net would swap left and right. Stage 1 keeps the
  full augmentation nnU-Net's ablations support.
- **Training data:** all 850 non-test cases' ImageCAS binary masks now; as team labels arrive, their
  union (LM∪LAD∪LCx∪RCA) **replaces** the ImageCAS mask for that case, so stage 1 converges to our
  protocol's lumen without waiting for it.
- Schedule: 1000 epochs × 250 it, checkpoint every 50 epochs, job-chain resume; 5 folds over the 850
  (fold 0 first, as the pipeline smoke test).

### 2.2 Stage 2 — naming (CPU; built today, improved as labels arrive)

Input: a binary mask (stage-1 prediction, or a reference mask when used as an annotation aid) and its
affine. Steps (code: `experiments/Bridge/extract.py` + `label.py`, ~15 s per case):

1. 26-connected components; TEASAR skeleton per component (kimimaro, scale 1.5, const 2 mm, physical
   anisotropy); every mask voxel owned by its nearest skeleton vertex in the same component.
2. **Gap bridging:** a component whose endpoint lies within 4 mm of another component is joined to it
   (CorSegRec-style reconnection, but only as a *naming* aid — the voxel mask is never edited).
3. Trees = components with ≥ 30 mm of skeleton. **Left tree = the one of the two largest with the more
   negative RAS x centroid** (RCA Dice 1.000 in every scored case with two separate trees). One tree > 800 mm of skeleton →
   flagged "fused", sent to a human (2 of 195; Delta ~2 %).
4. **Left ostium = learned:** logistic regression on 11 endpoint features (radius walking inward, height,
   distance to the right tree, ranks), then the top 5 candidates re-ranked by anatomical plausibility
   (LM 1.5–30 mm, LAD subtree anterior, LCx subtree posterior, ostium not below the bifurcation).
5. **LM/LAD/LCx split:** along the heavy path from the ostium (≤ 40 mm), the junction maximising
   (second-child subtree length) + (one child anterior, one posterior) − distance; the child whose
   subtree centroid is more anterior is LAD; any further major child (ramus) joins the class it points
   towards; every side branch inherits its parent's class.
6. Right tree → RCA; remaining fragments → class of the nearest named voxel.
7. Output per voxel; every class is a connected sub-tree by construction; plus a per-case QA record
   (LM length, tree lengths, ostium score margin, fused/single-tree flags) so the cases most likely wrong
   are reviewed first.

**As labels arrive:** refit the ostium model (it reaches ~93 % from 5 cases and ~96 % from 40) and
replace the hand-scored bifurcation choice with a learned candidate ranker of the same form (≤ 30
candidate junctions per case). Add one image feature per candidate (a small CT patch descriptor at each
endpoint/junction, e.g. a 32³ patch CNN or the aorta mask from TotalSegmentator) because my naive HU cue
failed. A generic per-vertex learner is **not** the plan: measured, it is worse than the structured
rules at 5–40 cases ([[Bridge - A generic learned vertex labeller is worse than structured rules at 5-40 training cases]]).

**Escalation, only if stage 2 misses its gate (§3) on the first 300 team labels:** a CNN namer at
1.0 mm with inputs (CT, stage-1 probability), 5-class output, loss on mask voxels only, whose softmax
becomes the unary term of the same tree decoding (TopCoW team NIC-VICOROB: image + binary mask input
"improved the segmentation results for both the CTA and MRA multiclass tasks", arXiv:2312.17670).
One 24 h job.

### 2.3 How arriving labels are used

| Labels in hand | Stage 1 | Stage 2 | Annotation |
|---|---|---|---|
| 0 (now) | train on 850 ImageCAS masks, fold 0 then 1–4 | rules + ostium model fit on ImageCAS-X projected names | SegQueue serves each case with the stage-2 named tree; annotators correct names and lumen instead of splitting |
| first 150 | — | — | **locked test set** (and 40 double reads); stage 2 never trained on them |
| 150–300 | swap these cases' masks for the team's union lumen; fine-tune | refit ostium + bifurcation rankers; gate check | prioritise cases the QA record flags |
| 300–1000 | retrain 5 folds on team lumen where available | refit every +100; escalate only on gate failure | — |
| all | final 5-fold ensemble | final rankers | — |

Because stage 2 needs tens of labelled cases, the plan can spend the **first** 150 team labels on a
locked test set rather than training — the direct-multiclass route cannot afford that.

### 2.4 Final model and inference

5-fold stage-1 ensemble (softmax average, threshold 0.5, drop < 100-voxel components) → skeleton →
stage-2 naming → 4-class map at native resolution. CPU stage 2 adds ~15 s per case.

## 3. Evaluation

- **Deciding metric:** on the locked 150-case test, **mean over the four classes of per-case Dice
  against our team's 4-class labels**, absent classes handled per [[Per-class Dice aggregation and handling of absent classes]].
  Secondary: per-class clDice, **swap rate** (cases with any class Dice < 0.5 — the clinically fatal error),
  connected-components-per-class (should be 1), HD95.
- **Error decomposition (the two-stage design gives it for free):** (a) stage-2 naming of the
  **reference** binary mask vs reference names — the naming ceiling; (b) stage-1 binary Dice; (c) end
  to end. If (a) is ~0.98 and (c) is poor, the work goes to stage 1, and vice versa.
- **Comparator arm (paired):** a direct 5-class nnU-Net, same planner, same folds, trained on the same
  labels available at each milestone (300 team labels; all labels), mirroring off. Paired Wilcoxon on
  per-case mean Dice and McNemar on swap rate, on the same 150 test cases.
- **Gate for stage 2** (checked at 300 team labels): naming of reference masks with all four classes
  Dice ≥ 0.8 in ≥ 95 % of test cases and swap rate ≤ 2 %. Today, against ImageCAS-X names on unseen
  cases, the frozen labeller is at 94.9 % and 3.4 % (2/59) — just short on swaps, both from one known
  cause (LM end placed at a later junction), which the learned junction ranker targets. Miss → escalate
  to the CNN namer (§2.2).
- **What would make me abandon the thesis:** the direct arm beating the two-stage end-to-end mean Dice by
  > 1 point with a lower swap rate at the all-labels milestone. Then the final model is the direct arm and
  stage 2 survives only as the annotation pre-segmentation and as post-hoc consistency check.

## 4. Evidence

Experiments (this round, all on our data):

1. [[Bridge - A rule-based labeller names LM, LAD, LCx and RCA on our binary masks]] — frozen labeller
   vs ImageCAS-X names: held-out 59 cases, 98.9 % pooled voxel accuracy, 94.9 % all four classes
   ≥ 0.8, swap 3.4 %; failures are discrete and flaggable.
2. [[Bridge - Finding the left ostium is the crux of naming, and 5-10 labelled cases teach it]] —
   ostium 0.957 CV; 0.93 from 5 cases; naive CT cue fails (1/24).
3. [[Bridge - A generic learned vertex labeller is worse than structured rules at 5-40 training cases]]
   — honest negative on "learn everything".
4. [[Bridge - Naming is one decision per tree, and half of a patch's LAD voxels cannot see it]] —
   2.1 % of voxels within 3 mm of the only class boundary; P(patch sees the bifurcation) ≈ 0.47.
5. [[Bridge - ImageCAS-X names transfer onto our binary masks, which are three times fatter]].
6. [[Bridge - Stage-1 gaps are what break naming, and bridging fixes most of it]] — 6 simulated
   breaks drop fully-right cases 0.94 → 0.50; 4 mm graph bridging restores 0.92; pruning distal
   branches costs nothing.
7. Others' notes relied on: Atlas (grid, planner), Crucible (ImageCAS-X mapping), Delta (topology).

Literature (identifiers checked this session; abstract or full text read as stated):

| Work | Checked | Main-branch result |
|---|---|---|
| Cao et al., Int J Cardiovasc Imaging 2017, doi:10.1007/s10554-017-1169-0 | Crossref + abstract | "In all cases, the proximal parts of main branches including LM were labeled correctly" (83 CCTA, centerline model matching) |
| Wu et al. (TreeLab-Net), IJCARS 14(2):271–280, 2019, doi:10.1007/s11548-018-1884-6 | Crossref + abstract (PMID 30484116) | AUC > 97 % for LM, LAD, LCX, RCA (436 CCTA) |
| Yang et al. (CPR-GCN), CVPR 2020, arXiv:2003.08560 | full PDF, Table 3 | F1 LM 0.989, LAD 0.988, LCX 0.976, RCA 0.990 (511 CCTA, 5-fold); in the same table TreeLab-Net 0.983/0.942/0.924/0.949, Cao 0.987/0.920/0.821/0.922 |
| Hampe et al., J Med Imaging 11(3):034001, 2024, doi:10.1117/1.JMI.11.3.034001 | full text (PMC11095121) | On reference trees (ensemble): LM 0.85, LAD 0.95, LCX 0.85, RCA 0.95; on automatically extracted trees: 0.70 / 0.86 / 0.74 / 0.90 — extraction errors, not the labeller, dominate |
| Ren et al., BMC Med Inform Decis Mak 2023, doi:10.1186/s12911-023-02332-y | abstract | rule/distance-transform labelling on centerlines: 5.4 % of 2180 labels needed correction; experts agree 95.0 % |
| TopCoW, arXiv:2312.17670 | full text | two-stage image+binary-mask input helped one team; **winners were single-stage multiclass nnU-Nets** (counter-evidence, see §6) |

Every published labeller names main branches at 0.92–0.99 F1 **on correct trees** and degrades when the
tree is wrong (Hampe: mean 0.91 → 0.74). That is the decomposition this plan exploits: put the
1000-label effort into the tree, and name it with something that needs few labels. Correction for the
vault: [[Downstream graph labelling of coronary branches is a second stage, never the segmenter]] says
Hampe's labeller reaches "F1 0.95" on reference trees; 0.95 is the *undivided-segments* single network,
the ensemble is 0.91 (their labelling table).

## 5. Risks and early detection

| Risk | Detected by | Response |
|---|---|---|
| Stage-1 breaks fragment the tree and names jump at the gap | experiment 6; per-case component count of stage-1 output vs reference on fold 0 validation | bridging (4 mm) already in; Skeleton Recall paired run; fragments flagged in QA |
| Our team's lumen protocol differs from ImageCAS's (ImageCAS-X disagrees with ImageCAS at Dice 0.42) | binary Dice of team union vs ImageCAS mask on the first 50 labels | stage 1 switches to team lumen case by case (§2.3); stage 2 is lumen-agnostic |
| Ostium / bifurcation wrong (~5 % now) | QA margin of the ostium score; LM length outside 2–30 mm | learned rankers + CT patch feature; QA-flagged cases reviewed first |
| Fused left+right trees (~2 %) | single tree > 800 mm | flag; split at the aortic root by the two ostium candidates (to build) or human |
| Ramus intermedius / protocol for IM | per-case IM flag (trifurcation within 5 mm) | follow whichever rule the protocol fixes; one parameter |
| Direct multiclass is simply better once all labels exist | the comparator arm at the all-labels milestone | switch (pre-registered in §3) |

## 6. Comparison

**Against the current plan of record ([[Training plan]] §3: binary first, then a direct multiclass
nnU-Net once labels flow).** Stage 1 is identical, so nothing is lost. What changes:
(i) the multiclass output exists on day 1 instead of after hundreds of labels; (ii) it is topologically
consistent by construction — a direct voxel model has no mechanism stopping an LAD island inside the
LCx, and for ~half of its LAD/LCx training voxels the deciding bifurcation is outside the patch;
(iii) stage 1 keeps mirroring; (iv) the first 150 team labels can be a locked test set; (v) annotators
receive a named tree, and the measured naming accuracy says most cases need no change to the main split.
The Training plan's own §4 already welcomes graph naming "downstream"; this plan makes it the route to
the deliverable and keeps the direct model as the falsification arm.

**Against "train the multiclass model on ImageCAS-X now"** ([[Proposed changes to the training plan]] §0,
option 1, likely to be argued by others): ImageCAS-X's lumen is a different protocol from our masks
(Dice 0.42–0.43, 3.3× fewer voxels), so a model trained on it predicts their lumen, not ours. Their
*names* are the transferable part — and this plan uses them exactly that way (to fit and validate
stage 2 on our lumen), with no GPU and no protocol mismatch.

**Against TopCoW's evidence for single-stage:** on the Circle of Willis the winners were single-stage
multiclass nnU-Nets. Two differences: CoW segments are short and dense around one ring, so every patch
sees the context; coronary branches run 100–250 mm from one bifurcation. And my plan pays for the
comparator arm rather than assuming the answer.

**Against other candidates this round:** none were filed when this was written; I will answer them in v2.

## 7. Cost

- **GPU (H100-hours; estimates, not measured — nnU-Net's fixed 1000 × 250 iterations at an assumed
  3–4 min/epoch for a ~20 Mvox patch):** stage 1, 5 folds × ~3 chained 24 h jobs ≈ **360 h** (shared with any plan that
  trains a binary model); comparator arm, 1 fold at 300 labels + 5 folds at all labels ≈ **430 h**;
  CNN namer escalation, if triggered, ≈ 24 h. Stage 2 itself: **0 GPU** (≈ 4 CPU-hours per 1000 cases).
- **Human:** annotators correct a pre-named tree instead of splitting one; 40 double reads; one
  person-day to wire stage 2 into SegQueue's pre-segmentation (output is a label map on the case grid).

## 8. Changes since previous version

First version.
