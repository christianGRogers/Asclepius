---
aliases: [LOSS-EVIDENCE, Loss functions, Topology losses]
tags: [research, coronary, loss, topology, literature]
status: handover
updated: 2026-09-19
---

# Loss function evidence

> **Handover draft.** Written before the research was split between agents; this topic now belongs to another agent. Sources were opened and numbers checked as stated below, but the note has not been reviewed by the owner. Take, merge or discard it.

Open item in [[Training plan]]: Dice+CE is the baseline; is a clDice / cbDice /
topology-aware term worth a scheduled second experiment, and which one?

**Short answer.** On coronary CCTA specifically, the two measurements that
exist (both on ImageCAS) show topology losses moving Dice by well under a point
and **not** improving the topology metrics they target; clDice made component
and distance errors worse on our cohort. Where a topology loss clearly helped,
it was on small, variably-present vessel classes in a *multiclass* cerebral
vessel task, which is the situation our rare branches will be in. The
candidate second experiment should be **Skeleton Recall**, not clDice, mainly
because clDice's memory cost fights the patch budget the plan depends on.

## Sources actually read

| Short name | Citation |
|---|---|
| clDice | Shit S, Paetzold JC, Sekuboyina A, Ezhov I, Unger A, Zhylka A, Pluim JPW, Bauer U, Menze BH. *clDice – a novel topology-preserving loss function for tubular structure segmentation.* CVPR 2021. arXiv:2003.07311. (Abstract read.) |
| Skeleton Recall | Kirchhoff Y, Rokuss MR, Roy S, Kovacs B, Ulrich C, Wald T, Zenk M, Vollmuth P, Kleesiek J, Isensee F, Maier-Hein K. *Skeleton Recall Loss for connectivity conserving and resource efficient segmentation of thin tubular structures.* ECCV 2024. arXiv:2404.03010. (Read via arXiv HTML.) |
| cbDice | Shi P, Hu J, Yang Y, Gao Z, Liu W, Ma T. *Centerline Boundary Dice loss for vascular segmentation.* MICCAI 2024. arXiv:2407.01517. (Read via arXiv HTML.) |
| ImageCAS-X | Bransby KM et al. arXiv:2608.30404, 2026 (preprint). See [[Class schema options]]. |
| BCS | Owusu-Ansah M, Lee K, Venugopal V, Jawaid MM, Duan W, Brown J. *Same branches, different trees: a bifurcation connectedness metric for coronary artery segmentation and FFR-CT decision agreement.* STACOM 2026 (MICCAI workshop). arXiv:2607.28327. (Read via arXiv HTML.) |

Found but **not opened**: *A Clinically-Informed Benchmark for Topology-Aware
Coronary Artery Segmentation*, Springer LNCS 2026, doi:10.1007/978-3-032-17734-6_2.
Springer redirected to an authentication page and the browser extension was not
available in this session to go through the UofT proxy. A search-engine summary
says it benchmarks topology-aware losses on ASOCA and finds them similar on
primary segments, with differences in secondary/tertiary segments dominated by
annotation inconsistency. **Unverified; do not cite until read.**

## Evidence on coronary CCTA (our anatomy)

### ImageCAS-X: nnU-Net vs nnU-Net + clDice, binary lumen

Dataset: ImageCAS-X test set, 160 ImageCAS scans, ImageCAS-X re-annotated
labels; single training run per method (1000 epochs × 250 iterations).
Values verbatim from their benchmark table (mean ± SD):

| | DSC % | HD95 mm | Betti err | clDice % | ASSD mm | CL HD95 mm |
|---|---|---|---|---|---|---|
| nnU-Net | 89.8 ± 3.2 | 7.08 ± 12.65 | 5.6 ± 3.5 | 92.3 ± 3.6 | 1.02 ± 0.75 | 10.41 ± 13.41 |
| nnU-Net + clDice | 90.0 ± 3.5 | 9.70 ± 15.36 | 8.0 ± 4.4 | 91.7 ± 3.9 | 1.20 ± 0.99 | 12.95 ± 14.20 |
| Inter-observer | 92.8 ± 3.1 | 2.46 ± 3.62 | 0.4 ± 0.4 | 95.4 ± 3.6 | 0.53 ± 0.33 | 4.58 ± 5.75 |

(The clDice columns here are computed on centerlines as a metric.) Adding
clDice: DSC +0.2, clDice metric −0.6, Betti error 5.6 → 8.0, HD95 +2.6 mm.
On this cohort it made the topology *worse* by their own topology metric. No
significance test reported for this pair. Note also that nnU-Net's Betti error
(5.6) and HD95 are far worse than the best method's (CAS-Net 1.9, 2.99 mm)
despite similar Dice: nnU-Net's weakness here is **spurious components**, not
overlap.

### BCS paper: Dice+CE vs clDice vs Skeleton Recall, binary lumen

Dataset: ImageCAS, "1,000 coronary CTA volumes split 750/250 into training and
test", original ImageCAS masks, test N = 250, **mean over 3 seeds**. Three
pretrained backbones (not nnU-Net). Selected columns:

| Backbone | Loss | Dice | clDice | BCS | β₀ err | FFR agreement % |
|---|---|---|---|---|---|---|
| CT-FM | baseline | 0.809 | 0.875 | 0.728 | 4.3 | 75.4 |
| CT-FM | clDice | 0.809 | 0.878 | 0.728 | 4.2 | 75.3 |
| CT-FM | Skeleton Recall | 0.808 | 0.861 | 0.794 | 8.0 | 85.7 |
| STU-Net-L | baseline | 0.818 | 0.890 | 0.758 | 2.9 | 77.5 |
| STU-Net-L | clDice | 0.814 | 0.888 | 0.750 | 2.6 | 76.6 |
| STU-Net-L | Skeleton Recall | 0.820 | 0.874 | 0.815 | 5.8 | 86.7 |
| SwinUNETR | baseline | 0.799 | 0.874 | 0.744 | 7.9 | 78.5 |
| SwinUNETR | clDice | 0.797 | 0.878 | 0.738 | 5.6 | 75.4 |
| SwinUNETR | Skeleton Recall | 0.798 | 0.850 | 0.780 | 11.9 | 85.1 |

BCS = "the fraction of ground-truth bifurcations whose branches stay
connected". FFR agreement = agreement of treat/no-treat decisions ("minimum
FFR anywhere in the tree is ≤0.80") between a solver run on predicted and on
ground-truth geometry. The authors: "Dice stays within 0.011 of baseline for
every loss" and "no single loss dominates all axes."

Reading: clDice loss is a no-op on every axis here. Skeleton Recall leaves
Dice unchanged, raises bifurcation connectedness and downstream FFR-decision
agreement by ~7–10 points, and roughly doubles the component-count error. It
recovers branches, at the cost of more fragments.

## Evidence on multiclass vessel labelling (closest analogue)

The TopCoW Circle-of-Willis task is the nearest published analogue to ours:
13 vessel classes, several of them small and variably present (communicating
arteries), like IM and L-PDA/L-PLA here.

### Skeleton Recall on TopCoW multiclass

Dataset: TopCoW, 3D, 200 samples, 13 classes; nnU-Net backbone. No fold/seed
averaging or significance test reported.

| | Dice | clDice | β₀ err | β₁ err |
|---|---|---|---|---|
| nnU-Net default | 85.36 | 93.68 | 0.137 | 0.0571 |
| + clDice | Out of memory | | | |
| + Skeleton Recall | 86.59 | 94.35 | 0.151 | 0.056 |

Verbatim: "the inefficiency of clDice Loss rendered it infeasible on all 13
classes as it exceeded the memory capacity of an A100 40GB GPU". Averaged
over the binary tasks, clDice cost "approximately 88% additional training
time and 52% more VRAM"; Skeleton Recall "8% training time and 2% higher VRAM".

### cbDice on TopCoW multiclass

Dataset: TopCoW 2023, 90 MRA cases (72 train / 18 validation+test), nnU-Net v2,
single run per configuration, no significance tests. Loss:
0.5·CE + weighted Dice + weighted X, where α = β = 0 is CE alone. "L" = large
non-communicating arteries, "S" = small communicating arteries (R-Pcom, L-Pcom,
Acom, 3rd-A2).

| Loss (α, β) | Dice(L) | Dice(S) | clDice | NSD(S) |
|---|---|---|---|---|
| CE only (0, 0) | 81.51 | 7.012 | 90.10 | 14.08 |
| CE + Dice (1, 0) | 84.03 | 0 | 88.22 | 0 |
| + clDice (1, 1) | 84.21 | 38.46 | 90.72 | 47.85 |
| + cbDice (1, 1) | 84.11 | 41.55 | 91.34 | 50.42 |
| + cbDice (1, 2) | 84.01 | 43.38 | 91.95 | 54.11 |

A default CE+Dice nnU-Net scoring **zero** on the small, variably-present
classes, rescued to ~40 by any centerline term, is the single most striking
number in this literature for a problem shaped like ours. It is also the least
trustworthy: 18 test cases, one run, no explanation given by the authors, and it
does not match the Skeleton Recall paper's default-nnU-Net TopCoW result of
85.36 mean Dice (different split, data release and aggregation, so the two are
not directly comparable either). Treat it as a warning about rare classes, not
an effect size.

## Where the literature disagrees

- **clDice helps** (clDice paper, five non-coronary datasets; cbDice paper,
  TopCoW small vessels) **vs clDice does nothing or harms** (ImageCAS-X and BCS,
  both on ImageCAS coronaries). The coronary evidence is the more relevant and
  the better controlled (BCS: 3 seeds, 250 test cases).
- **Topology metrics conflict with each other.** Skeleton Recall improves BCS
  and FFR agreement on ImageCAS while worsening β₀ and the clDice metric. The
  BCS authors conclude "recovering branches and keeping them connected are
  separable properties" and recommend reporting a measure of each. This matters
  for [[Acceptance thresholds]]: a single topology number will mislead.

## Recommendation

1. **Baseline: nnU-Net default Dice+CE.** Unchanged. No coronary evidence shows
   any alternative moving Dice by more than ~1 point.
2. **Second experiment: + Skeleton Recall, not clDice.** Why:
   - clDice's memory cost directly shrinks the patch, and the large patch is a
     core decision in [[Training plan]] §2. It ran out of memory at 13 classes on
     40 GB with default patches; we would have 15 classes and patches roughly an
     order of magnitude larger in voxels.
   - On our cohort clDice loss did not improve topology (ImageCAS-X) and did
     nothing across three backbones (BCS).
   - Skeleton Recall is from the nnU-Net group, near-free in compute (+2 % VRAM),
     multiclass-capable, gave +1.2 Dice on 13-class TopCoW and the largest
     branch-recovery gains on ImageCAS.
   - Expected cost: more small fragments (β₀). That interacts with the ban on
     largest-component post-processing in [[Training plan]] §4; plan a
     fragment-aware clean-up that never deletes a component touching a labelled
     vessel.
3. **cbDice as an optional third**, only if the rare classes (IM, L-PDA, L-PLA,
   D2, OM2) come out near zero in the baseline. Its only claimed advantage
   relevant to us is small-vessel class rescue, and that claim rests on 18
   test cases.
4. **Judge the loss experiment on per-class branch detection and per-class
   clDice for the small classes**, not on mean Dice. Every coronary result
   above shows mean Dice moving by less than its seed-to-seed noise.

## What this implies for [[Training plan]]

- Replace "clDice/cbDice term is a candidate second experiment" with
  "**Skeleton Recall** is the scheduled second experiment (fold 0, paired
  against the baseline); cbDice only if rare classes fail". Reason: memory and
  the coronary evidence above.
- Add β₀ (component count) and a bifurcation-connectedness measure to the
  evaluation list, since the losses trade them off against each other.
- These proposals are not in [[Proposed changes]] (class schema only); they are for this topic's owning agent to take or discard.
