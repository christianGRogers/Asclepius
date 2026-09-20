---
tags: [research/loss, class-imbalance, weight-balancing, vessel, multiclass]
status: solid
updated: 2026-09-20
aliases: [Class weighting, Weighted loss, Vessel imbalance]
---

# Loss weighting between large proximal and rare distal branch classes

[[Training plan]] names the multiclass task as "segment the branch identity" where some branches are large (proximal LAD, LCx, RCA trunks; ~500–1000 voxels in a full 512×512×250 volume) and others are rare (distal branches, diagonal branches; sometimes <50 voxels or absent in many patients). This note examines what loss-weighting or loss-balancing strategies work for this extreme imbalance.

## The imbalance problem in vessel segmentation

Standard Dice+CE loss treats all classes equally:
```
L = α · L_dice + (1-α) · L_ce
```

For class *c*:
```
Dice_c = 2·TP_c / (2·TP_c + FP_c + FN_c)
CE_c = -Σ y·log(ŷ)
```

When class *c* is rare (e.g. 30 voxels in a 70M-voxel patch), its loss is dominated by background FP's and false negatives; the common classes (proximal) dominate the gradient. The rare class receives vanishing gradient signal and may converge to zero Dice.

Coronary-specific evidence comes from two sources:

**TopCoW 2023 benchmark (13-class brain vessels, small communicating arteries class)**:
- CE+Dice baseline: **0 Dice on the small-artery class** (84.03 Dice on large arteries, 0 on small).
- Adding clDice term: small artery Dice → 38.46 (with β=1, +clDice weighting).
- Adding cbDice term: small artery Dice → 43.38 (with β=2).
- **Disagreement noted**: NexToU+cbDice reached 48.43 on small arteries, but mean Dice stayed at 84.21, suggesting class weighting redistributed loss away from large arteries.

This is the most striking result in the literature for multiclass vessel segmentation with extreme class imbalance; the 0→43 span is transformative but comes with a caveat: only 18 cases in test set, one run per cell, no seed-level variation reported.

## Strategies that have been tried

### 1. Weighted cross-entropy (inverse class frequency)
```
CE_weighted = -Σ_c w_c · Σ y_c · log(ŷ_c)
```
where `w_c = N_total / N_c` (or normalized). Standard practice in many papers.

**Coronary evidence**: HTC-SGA Former (coronary DSA X-ray segmentation, boundary-aware loss) uses weighted focal loss + weighted Dice, balancing between vessel and background; achieves 92.8 % Dice on that task. No direct comparison of weighting strategies reported.

### 2. Focal loss (Lin et al. 2017)
```
CE_focal = -α_t · (1-p)^γ · log(p)
```
where γ emphasizes hard examples (misclassified voxels). Rarely used directly for medical-image multiclass (it's from object detection), but Dice loss inherently downweights easy negatives.

**Comparison to Dice**: DPN (retinal vessel segmentation) reports *"Dice loss consistently outperforms Focal loss on class imbalance in vessel segmentation because Dice directly optimizes the IoU metric which naturally accounts for extreme foreground-background imbalance."* No coronary comparison found.

### 3. Distance-transform weighting (cbDice / centerline-boundary Dice)
Already covered in [[Topology-aware losses on thin tubular structures]]. The key insight: if a small class has a very thin instance, a boundary error costs more in scaled Dice than in unweighted Dice. Shi et al. (cbDice paper) show that inverse radius `R_N = R/R_max` rebalances large and small vessels so a 1-voxel break in either is equally costly.

**Coronary result**: BCS paper benchmark at 1.0 mm isotropic (three seeds, three backbones, 250 test cases) found **clDice did nothing** on Dice (-0.004 to +0.001) and **cbDice did nothing on Dice** (+0.006 in one case, −0.013 in another), though both moved the clDice metric slightly. The rare-class rescue shown in TopCoW (0→43) did not replicate.

### 4. TubeLoss and dynamic per-voxel weighting
**vesselFM-CT** (Huang et al., 2026, foundation model for vessel segmentation) describes *extrinsic* and *intrinsic* class imbalance:
- **Extrinsic**: different organ classes (aorta vs pulmonary artery) have very different volumes in the training set.
- **Intrinsic**: within a single vessel instance, diameter varies along the spine (thick proximal, thin distal), creating imbalance within a single class.

TubeLoss dynamically adjusts per-voxel weights during training:
```
w_voxel = α · (presence of rare class) + β · (radius inverse weighting)
L = Σ w_voxel · L_base
```

**Measured results**: on multi-vessel CT (aorta, pulmonary, hepatic, renal), TubeLoss reportedly improves Dice on small-vessel classes, but **no quantitative comparison to cbDice or Focal loss is reported in published results** (the comparison is absent or flagged as future work). This is a preprint/recent work and is unverified.

## Why weighting alone may not solve coronary distal branches

1. **Geometric imbalance is extreme**: a distal branch might be 20 voxels in a 70 M-voxel patch (1 in 3.5 M). Even with `w_rare = N_total / N_rare ≈ 3.5M`, the rare-class gradient is still small in absolute terms. Weighting helps but is not magic.

2. **Absence in many cases**: if a distal branch is absent in 70 % of training cases (missing ramus intermedius, PDA absent in dominant RCA, etc.), then on those cases `w_rare` is multiplied by zero. The model only sees the distal branch in 30 % of cases, and only then in ~20 voxels. This is a **data problem, not a weighting problem**.

3. **[[Training plan]] §5 already has a solution**: class-balanced and vessel-anchored patch sampling ensures that cases containing each rare class are oversampled, and patches are drawn preferentially from regions containing that class. This is **sampling-level re-balancing**, which is more direct than per-voxel loss weighting.

## What this implies for [[Training plan]]

1. **Keep nnU-Net's default Dice+CE (α=0.5) as the baseline** — no special weighting for the baseline run. The vessel-anchored sampling (§5 standing experiment) is the primary lever for rare-class recovery.

2. **If the multiclass baseline shows a rare class at ≤20 % Dice** (not zero, but still far behind proximal branches at 80–90 %), run a paired weighted-loss experiment: nnU-Net default loss but with per-class weights `w_c = f(N_c)` set **before training**, not dynamically. Use inverse-frequency weighting as the simplest variant: `w_c = 1.0 / (N_c / N_max)`, normalized so `Σ w_c = num_classes`. This is a cheap change to the trainer.

3. **Do not schedule dynamic weighting (TubeLoss) as a first experiment**: it adds hyperparameters (α, β, schedule) and no coronary evidence exists. Reserve it as a second-tier rescue if inverse-frequency weighting doesn't move the rare classes.

4. **Do not interpret a rare-class Dice of 30–40 % as "failure" if clDice (per-class branch detection) is high**. See [[Topology-aware losses on thin tubular structures]] — the TopCoW 0→43 gain is impressive in Dice but on only 18 test cases, and the real question is whether the branches are found (clDice) and connected (BCS), not their boundary Dice.

## What this implies for [[Proposed changes]]

- Add to §5 (standing experiments): "**Per-class weighting (inverse-frequency) paired experiment** on the multiclass baseline. If any class scores <20 % Dice despite appearing in >20 % of training cases, run one paired trainer with per-class loss weights `w_c = 1.0 / (N_c / N_max)`. Measure per-class Dice, clDice, and component count separately; accept the weighted variant only if rare-class Dice improves by >10 pp without proximal-class Dice dropping by >2 pp."

- Add to evaluation: "Report Dice, clDice, and branch detection rate **per class**, not only mean Dice. Rare classes are the project's value; do not hide them in a mean."

Collected in [[Proposed changes]].
