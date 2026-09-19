---
aliases: [Topology losses, clDice, cbDice, Skeleton Recall, Topology-aware loss evidence]
tags: [research, loss, topology, coronary, literature]
status: draft
updated: 2026-09-19
---

# Topology-aware losses on thin tubular structures

Open item in [[Training plan]]: the baseline loss is nnU-Net's default Dice+CE,
and "clDice/cbDice term is a candidate second experiment, not yet scheduled".
This note asks what a topology-aware loss actually buys on thin tubular
structures, what it costs, and which one is worth one paired run.

This note supersedes the pre-division draft at
`vault/Research/Class schema/Handover/Loss function evidence.md`. Every number
below was re-read from the source by this agent; where the handover and the
source differ, the source wins and the difference is flagged.

## Papers opened for this note

| Short name | Citation | How read |
|---|---|---|
| clDice | Shit S, Paetzold JC, Sekuboyina A, Ezhov I, Unger A, Zhylka A, Pluim JPW, Bauer U, Menze BH. *clDice — a novel topology-preserving loss function for tubular structure segmentation.* CVPR 2021, doi:10.1109/CVPR46437.2021.01629 | arXiv HTML (arXiv:2003.07311), abstract + results tables |
| Skeleton Recall | Kirchhoff Y, Rokuss MR, Roy S, Kovacs B, Ulrich C, Wald T, Zenk M, Vollmuth P, Kleesiek J, Isensee F, Maier-Hein KH. *Skeleton Recall Loss for connectivity conserving and resource efficient segmentation of thin tubular structures.* ECCV 2024, LNCS 15135, pp. 218–234, doi:10.1007/978-3-031-72980-5_13 | arXiv HTML (arXiv:2404.03010v2) + the authors' GitHub `MIC-DKFZ/Skeleton-Recall` |
| cbDice | Shi P, Hu J, Yang Y, Gao Z, Liu W, Ma T. *Centerline Boundary Dice loss for vascular segmentation.* MICCAI 2024, LNCS 15008, doi:10.1007/978-3-031-72111-3_5 | arXiv HTML (arXiv:2407.01517v1) |
| ImageCAS-X | Bransby KM et al. *ImageCAS-X: a dataset and benchmark for coronary artery segmentation and centerline extraction in coronary CT angiography.* arXiv:2608.30404, 2026. **Preprint.** | arXiv HTML |
| BCS | Owusu-Ansah M, Lee K, Venugopal V, Jawaid MM, Duan W, Brown J. *Same branches, different trees: a bifurcation connectedness metric for coronary artery segmentation and FFR-CT decision agreement.* STACOM 2026 (MICCAI workshop); arXiv:2607.28327, submitted 30 July 2026. **Workshop preprint.** | arXiv HTML |

Wanted and **not accessible**: *A Clinically-Informed Benchmark for
Topology-Aware Coronary Artery Segmentation*, Springer LNCS 2026,
doi:10.1007/978-3-032-17734-6_2. link.springer.com returned HTTP 303 to
`idp.springer.com/authorize`, and the `claude-in-chrome` skill was not offered
in this session, so the UofT proxy route was unavailable. A search-engine
snippet claims it benchmarks topology-aware methods on ASOCA and finds them
**similar on primary segments**, with secondary/tertiary differences dominated
by annotation inconsistency rather than method choice. That is directly on
point for us and **unverified — do not cite it until someone opens it.**

## What each loss does

- **clDice** (Shit et al.): soft-skeletonises *both* prediction and label with
  iterated min/max-pool erosion, then takes the harmonic mean of "how much of
  the predicted skeleton lies in the true mask" and "how much of the true
  skeleton lies in the predicted mask". Differentiable, computed on the GPU,
  inside the training graph. The authors are explicit that the skeleton is an
  approximation: *"Although our proposed soft-skeleton approximation works well
  in practice, a better differentiable skeletonization can only improve
  performance."*
- **Skeleton Recall** (Kirchhoff et al.): skeletonises **only the label**, on
  the **CPU, during data loading**, with scikit-image, then dilates that
  skeleton with a diamond kernel of radius 2 to make it tubular. The loss is a
  plain recall of the predicted foreground on that tube:
  `L_SkelRecall = -(1/|C|) Σ_c Σ_i (Y_skel,i,c · Ŷ_i,c) / Σ_i Y_skel,i,c`,
  added as `L = L_generic + w · L_connectivity` with `w ∈ {0.1, 1.0}`. For
  multiclass it "assign[s] parts of the skeleton to their respective classes".
  Because nothing is skeletonised on the GPU, cost is near-zero and, critically,
  **near-constant in the number of classes**.
- **cbDice** (Shi et al.): clDice plus distance-transform weighting. It takes
  the skeleton radius `R` from the mask distance map and uses normalised radius
  `R_N = R/R_max` and inverse `I_N = I/I_min` so that a break in a thin branch
  and a break in a thick one count comparably. The stated motivation is exactly
  our problem: clDice+Dice still exhibits *"diameter imbalance, favoring larger
  vessels"*. The paper also proves its precursor is sensitive to translations
  within the vessel radius, which clDice is not.

## Effect sizes, by dataset

### clDice's own datasets (no coronaries)

Vessap, 3D multi-channel microscopy of brain vessels, soft-Dice vs
`L_c` (soft-Dice + soft-clDice), verbatim from the paper:

| Network | Loss | Dice | clDice | β₀ err | β₁ err |
|---|---|---|---|---|---|
| FCN 1-ch | soft-dice | 85.21 | 90.88 | 3.385 | 4.458 |
| FCN 1-ch | L_c, α=0.5 | 85.44 | 91.32 | 2.292 | 3.677 |
| FCN 2-ch | soft-dice | 85.31 | 90.10 | 2.833 | 4.771 |
| FCN 2-ch | L_c, α=0.2 | 86.45 | 91.22 | 2.656 | 4.385 |
| U-Net 1-ch | soft-dice | 87.46 | 91.18 | 3.094 | 5.042 |
| U-Net 1-ch | L_c, α=0.5 | 87.82 | 93.03 | 2.656 | 4.615 |
| U-Net 2-ch | soft-dice | 87.98 | 90.16 | 2.344 | 4.323 |
| U-Net 2-ch | L_c, α=0.4 | 88.57 | 93.25 | 2.281 | 4.302 |

Read: Dice +0.2 to +1.1, clDice metric +0.4 to +3.1, β₀ error down in all four
rows. Consistent but small, and on 3D microscopy, not CT. No significance test
reported, single run per cell.

### Skeleton Recall's benchmark (nnU-Net backbone, five datasets)

Verbatim; "Default" is nnU-Net's own Dice+CE:

| Dataset | Config | Dice | clDice | β₀ err | β₁ err |
|---|---|---|---|---|---|
| Roads (2D) | Default | 78.99 | 88.79 | 5.769 | 84.62 |
| | +clDice | 79.15 | 89.00 | 6.539 | 82.00 |
| | +SkelRecall | 79.25 | 89.06 | 4.846 | 83.69 |
| DRIVE (2D) | Default | 80.87 | 80.26 | 57.00 | 22.80 |
| | +clDice | 81.05 | 80.68 | 44.50 | 23.35 |
| | +SkelRecall | 80.99 | 80.83 | 38.75 | 21.50 |
| Cracks (2D) | Default | 94.59 | 95.76 | 0.147 | 0.0033 |
| | +clDice | 94.80 | 95.96 | 0.142 | 0.0033 |
| | +SkelRecall | 94.88 | 96.04 | 0.148 | 0.0035 |
| ToothFairy (3D) | Default | 71.80 | 89.16 | 0.900 | 0.0200 |
| | +clDice | 72.36 | 89.67 | 0.620 | 0.0200 |
| | +SkelRecall | 74.42 | 92.05 | 0.540 | 0.0200 |
| TopCoW binary (3D) | Default | 93.55 | 98.25 | 0.743 | 1.800 |
| | +clDice | 93.64 | 98.35 | 0.514 | 1.986 |
| | +SkelRecall | 93.72 | 98.48 | 0.500 | 1.586 |
| TopCoW 13-class | Default | 85.36 | 93.68 | 0.137 | 0.0571 |
| | +clDice | **out of memory** | | | |
| | +SkelRecall | 86.59 | 94.35 | 0.151 | 0.0560 |

Results are on held-out test sets (Roads, ToothFairy, TopCoW) or 5-fold CV
(DRIVE, Cracks); the paper does not state that multiple seeds were run. The
largest 3D gain is ToothFairy (+2.6 Dice, +2.9 clDice over default), a single
thick-ish tubular structure. On the two TopCoW rows — the vascular ones, and the
ones shaped like our task — the gain is +0.2 and +1.2 Dice.

**Cost, which is the decisive number for us:** Skeleton Recall costs
*"only an additional 8% training time and 2% higher VRAM consumption"*; clDice
costs *"approximately 88% additional training time and 52% more VRAM
consumption"* averaged over the five datasets. Scaling to many classes,
Skeleton Recall keeps *"near-constant additional overhead"* while clDice grows
*"approximately linear"* — which is why the 13-class cell above is an OOM on an
A100 40 GB at nnU-Net's default patch size.

### cbDice's benchmark

DRIVE (2D retina, 20 test images, 20 epochs, nnU-Net) — differences are in the
noise: CE+Dice 82.4 Dice / 82.3 clDice; +clDice 82.3 / 82.2; +cbDice(β=0.5)
82.5 / 82.4.

PARSE 2022 (100 CT pulmonary artery scans, 80 train / 20 val+test, 50 epochs,
nnU-Net): CE+Dice 85.05 Dice, 80.11 clDice, 277.7 β-err; +clDice 85.30 / 80.23 /
263.4; +cbDice(β=2) 84.91 / 80.02 / 275.8. On this 3D CT vascular dataset
**cbDice did not beat plain CE+Dice** on any of the three columns.

TopCoW 2023 (90 MRA cases, 72 train / 18 val+test, 100 epochs, nnU-Net v2),
"L" = large non-communicating arteries, "S" = small communicating arteries:

| Loss | Dice(L) | Dice(S) | clDice | NSD(L) | NSD(S) |
|---|---|---|---|---|---|
| CE+Dice (β=0) | 84.03 | **0** | 88.22 | 91.90 | 0 |
| +clDice (β=1) | 84.21 | 38.46 | 90.72 | 92.45 | 47.85 |
| +cbDice (β=2) | 84.01 | 43.38 | 91.95 | 91.99 | 54.11 |
| NexToU +cbDice (β=3) | 84.21 | 48.43 | 90.89 | 92.30 | 58.91 |

A default nnU-Net scoring **exactly zero** on the small, variably-present
classes while scoring 84 on the large ones, and being rescued to ~40 by any
centerline term, is the most striking result in this literature for a problem
shaped like ours — and the least trustworthy: 18 cases in val+test, one run per
cell, no significance test, and no explanation offered by the authors for the
zero. It also contradicts the Skeleton Recall paper's default-nnU-Net TopCoW
number (85.36 mean Dice over 13 classes, which cannot coexist with several
classes at zero unless the class sets or aggregation differ). Different data
release, split and aggregation, so they are not strictly comparable — but the
disagreement is real and is recorded here as a disagreement. See
[[Class imbalance in multiclass vessel segmentation]].

### Coronary CCTA — the only evidence on our anatomy

**ImageCAS-X** (preprint). 160-scan ImageCAS test set with re-annotated labels,
**0.5 mm isotropic** resampling, one run per method, post-processing = threshold
0.5 then remove components < 100 voxels:

| | DSC % | HD95 mm | Betti err | clDice % | ASSD mm |
|---|---|---|---|---|---|
| nnU-Net | 89.8 ± 3.2 | 7.08 ± 12.65 | 5.6 ± 3.5 | 92.3 ± 3.6 | 1.02 ± 0.75 |
| nnU-Net + clDice | 90.0 ± 3.5 | 9.70 ± 15.36 | 8.0 ± 4.4 | 91.7 ± 3.9 | 1.20 ± 0.99 |

Adding clDice: DSC +0.2, clDice metric −0.6, Betti error 5.6 → 8.0, HD95
+2.6 mm, ASSD +0.18 mm. On coronaries it made topology **worse** by the paper's
own topology metric. No significance test for this pair, single run. The paper
does not state the clDice weight it used, which limits how much weight to put
on the result. The authors' own summary is that *"topological errors such as
vessel breaks are present in all model predictions despite high DSC and
clDice"*.

**BCS** (workshop preprint). ImageCAS, 750/250 split, 250 test cases,
**mean over three seeds**, resampled to 1.0 mm isotropic, HU clipped to
[−200, 600], **no connected-component post-processing**, β₀ = number of
26-connected components:

| Backbone | Loss | Dice | HD95 | clDice | BCS | β₀ | FFR agree |
|---|---|---|---|---|---|---|---|
| CT-FM | baseline | 0.809 | 6.00 | 0.875 | 0.728 | 4.3 | 75.4 % |
| CT-FM | clDice | 0.809 | 5.91 | 0.878 | 0.728 | 4.2 | 75.3 % |
| CT-FM | soft-BCS | 0.807 | 5.63 | 0.872 | 0.757 | 4.6 | 85.5 % |
| CT-FM | SkelRecall | 0.808 | 6.44 | 0.861 | 0.794 | 8.0 | 85.7 % |
| STU-Net-L | baseline | 0.818 | 5.19 | 0.890 | 0.758 | 2.9 | 77.5 % |
| STU-Net-L | clDice | 0.814 | 5.49 | 0.888 | 0.750 | 2.6 | 76.6 % |
| STU-Net-L | soft-BCS | 0.813 | 7.03 | 0.879 | 0.765 | 4.0 | 86.8 % |
| STU-Net-L | SkelRecall | 0.820 | 5.71 | 0.874 | 0.815 | 5.8 | 86.7 % |
| SwinUNETR | baseline | 0.799 | 6.02 | 0.874 | 0.744 | 7.9 | 78.5 % |
| SwinUNETR | clDice | 0.797 | 5.99 | 0.878 | 0.738 | 5.6 | 75.4 % |
| SwinUNETR | soft-BCS | 0.788 | 8.95 | 0.859 | 0.742 | 8.3 | 88.0 % |
| SwinUNETR | SkelRecall | 0.798 | 11.52 | 0.850 | 0.780 | 11.9 | 85.1 % |

Seed-level SDs are reported as ≤0.018 for rates, ≤2.0 for HD95, ≤1.1 for β₀,
≤4.5 pp for FFR agreement. Loss weights: the baseline uses
λ_d = 0.35, λ_CE = 0.15, λ_v = 0.35, α = 0; every topology configuration uses
λ_d = λ_CE = 0.5, λ_v = 0, α = 0.05.

Two caveats the handover did not record and that matter to us: **(a)** the
baseline is not a plain Dice+CE — it carries a third volumetric term λ_v that
the topology rows drop, so "baseline vs topology" also changes the volumetric
objective; **(b)** the volumes are resampled to **1.0 mm isotropic**, roughly
three times our native 0.35 mm. At 1 mm a 1.5 mm distal branch is one voxel
across, so this experiment is run in a regime where breaks are far more likely
than in ours, which should if anything *inflate* the benefit of a connectivity
term. It still found clDice to be a no-op.

Reading across the three seeds and three backbones: clDice moves nothing
(|ΔDice| ≤ 0.004, ΔBCS ≤ 0.008 in either direction). Skeleton Recall leaves
Dice unchanged (−0.001 to +0.002), raises bifurcation connectedness by
+0.036 to +0.066 and FFR treat/no-treat agreement by +6.6 to +10.3 points, and
**roughly doubles β₀** (4.3→8.0, 2.9→5.8, 7.9→11.9). Soft-BCS buys most of the
FFR agreement with a much smaller β₀ penalty, but is the authors' own new loss,
measured only by them.

## Losses I could not find coronary evidence for

- **Persistent-homology / Betti losses** (Hu et al., Clough et al., Betti
  matching). Not opened in this session; no coronary CCTA result located. The
  general objection is cost: PH losses are computed per patch on the CPU and
  scale badly with volume and class count — the same failure mode that put
  clDice out of memory at 13 classes. Treat as out of scope for a first
  experiment and record as **unverified**.
- **Centerline-weighted CE / distance-weighted losses.** cbDice is the
  best-documented member of this family and is covered above.
- **Connectivity-aware losses** other than soft-BCS: nothing coronary found.

## Where the literature disagrees

1. **clDice helps** (clDice paper on Vessap/DRIVE-class data; cbDice paper on
   TopCoW small vessels) **vs clDice does nothing or harms** (ImageCAS-X and
   BCS, both on ImageCAS coronaries). The coronary evidence is more relevant to
   us and, in the BCS case, better controlled (3 seeds × 3 backbones,
   250 test cases). Both coronary sources are 2026 preprints.
2. **Topology metrics disagree with each other.** Skeleton Recall improves BCS
   and FFR agreement on ImageCAS while *worsening* β₀ and the clDice metric.
   The BCS authors' own conclusion is that *"recovering branches and keeping
   them connected are separable properties"*. A single topology number will
   mislead.
3. **cbDice on 3D CT vasculature**: the paper's own PARSE result has cbDice
   slightly *behind* CE+Dice, while its TopCoW result is its headline. The
   difference between those two is multiclass small-vessel rescue, not 3D CT.

## Recommendation

1. **Keep nnU-Net's default Dice+CE as the baseline.** No coronary result
   anywhere above moves Dice by more than ~1 point in any direction; the loss
   is not where the binary model is won or lost.
2. **Schedule exactly one paired loss experiment, and make it Skeleton Recall**,
   not clDice:
   - Memory. The large patch is a core decision in [[Training plan]] §2.
     clDice costs ~52 % more VRAM and ~88 % more time, grows linearly in class
     count, and already OOM'd at 13 classes on 40 GB at *default* patch size.
     Our patches are an order of magnitude larger in voxels and we expect a
     similar class count. Skeleton Recall costs ~2 % VRAM, ~8 % time, and is
     near-constant in class count because the skeleton is precomputed on the
     CPU in the data loader.
   - Evidence. On our own cohort clDice did nothing across three backbones
     and three seeds (BCS) and worsened topology in the one nnU-Net comparison
     that exists (ImageCAS-X). Skeleton Recall gave the largest
     branch-recovery gains on ImageCAS and +1.2 Dice on 13-class TopCoW.
   - Provenance. Skeleton Recall is from the nnU-Net group and ships an
     `nnUNetTrainerSkeletonRecall` for nnU-Net v2
     (`MIC-DKFZ/Skeleton-Recall`), so the experiment is a trainer swap, not a
     fork of the loss stack. Note it is a *patched fork*, not upstream
     nnU-Net — the repository says upstream integration is "under discussion",
     so pin the commit.
   - Expected cost: **more fragments** (β₀ roughly doubled on ImageCAS). See
     [[Largest-component post-processing is wrong for coronaries]].
3. **cbDice only as a conditional third run**, triggered by evidence rather
   than scheduled: if rare branch classes come out at or near zero Dice in the
   multiclass baseline, the TopCoW 0 → 43 result is the only thing in the
   literature that addresses that failure. Its claim rests on 18 cases and one
   run, and its own 3D-CT dataset (PARSE) showed no gain, so it is a rescue
   measure, not an upgrade.
4. **Judge the loss experiment on per-class branch detection and per-class
   centerline overlap for the small classes, plus a component count** — never
   on mean Dice, which in every coronary experiment above moved less than its
   seed-to-seed noise.

## What this implies for [[Training plan]]

- The "Still open → Loss" bullet should resolve to: baseline Dice+CE unchanged;
  **Skeleton Recall** is the one scheduled paired loss experiment (same fold,
  same data, same harness, `-tr nnUNetTrainerSkeletonRecall`); cbDice is
  conditional on rare-class failure; clDice is **ruled out** on memory grounds
  and on coronary evidence.
- Add the loss experiment to §5 "Standing experiments" rather than leaving it
  in "Still open", and state its acceptance criterion in terms of per-class
  branch detection, not Dice.
- The evaluation list should carry a component count (β₀) *and* a
  connectedness measure, because the candidate loss is expected to improve one
  while worsening the other.
- §4's ban on largest-component post-processing becomes *more* load-bearing if
  Skeleton Recall is adopted, since it produces more fragments. The
  fragment-handling policy has to be decided in the same experiment, not after.

Collected in [[Proposed changes]].
