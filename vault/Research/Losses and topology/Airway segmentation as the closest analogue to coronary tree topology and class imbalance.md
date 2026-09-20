---
tags: [research/topology, airway, analogue, tubular-structures, imbalance]
status: solid
updated: 2026-09-20
aliases: [Airway analogue, Tubular topology, Branch segmentation]
---

# Airway segmentation as the closest analogue to coronary tree topology and class imbalance

The coronary artery tree and the airway tree (bronchial tree) are the two largest branching vascular/tubular structures in medical imaging. This note examines what the airway literature has learned about topology preservation and class imbalance that transfers to coronary multiclass segmentation.

## Why airway is the right analogue

Both trees share:
- **Branching structure**: trachea → bronchi → bronchioles (airways); aortic root → LAD/LCx/RCA → distal branches (coronary).
- **Scale imbalance**: trachea/proximal bronchi are 5–20 mm diameter; bronchioles are 1–2 mm. Proximal coronaries are 3–5 mm; distal branches are 1.5–2 mm. **Same scale ratio (~10×).**
- **Per-case volume imbalance**: large trachea dominates; small bronchioles are rare and variable. Same as proximal-vs-distal coronary.
- **Topology priority**: a segmentation model that loses a bronchiole or misses a small bronchus branch is a failure, just as losing a distal coronary branch is. Dice can be high while topology is broken.
- **Absence and variability**: not all bronchioles are present in every scan (anatomical variation); not all ramus intermedius or secondary diagonals exist (coronary variation).

**Scale difference**: airways are imaged at finer resolution (HRCT, ~0.5–1 mm isotropic), while coronaries are 0.29–0.45 mm in ImageCAS (finer still). Proportionally, they are comparable.

**Coronary-specific differences**:
- Airways are in air-filled lungs (high contrast); coronaries are in cardiac muscle with iodine enhancement (lower contrast, more noise).
- Airways are relatively static; coronaries have motion artifact and calcification blooming.

## What the airway literature has solved

### 1. Topology-aware losses

**Airway Segmentation Based on Topological Structure Enhancement Using Multi-task Learning (MICCAI 2024, Kingma et al.)**:
- Problem: "standard 3D-UNet segmentation results typically exhibit airway topology breakage".
- Solution: multi-task learning combining segmentation + centerline auxiliary head.
- **Mechanism**: centerline supervision forces the network to learn connectivity; centerline is extracted from the label by skeletonization, then dilated to a tubular prior.
- **Result**: on an airway dataset (not quantified in the abstract; full paper access needed), centerline-supervised multi-task learning "improved accuracy and connectivity of segmentation results".
- **Status**: this is the approach mentioned as JLNet-adjacent in [[Binary-init fine-tuning and multi-task auxiliary heads for the multiclass model]], already flagged for hand fetch.

**Skeleton Recall Loss (Kirchhoff et al., ECCV 2024)**:
- Specifically designed for tubular structures; tested on airway datasets as well as coronary (TopCoW, ASOCA).
- Directly covered in [[Topology-aware losses on thin tubular structures]].
- **Key insight for airways**: the loss is CPU-precomputed, so scaling to many branches (airway has ~20 visible levels in CT) does not blow up memory. Skeleton Recall scaled to 13-class TopCoW without OOM, where clDice did OOM.

### 2. Class imbalance and per-class loss weighting

**Interpolation-Split: A Data-Centric Deep Learning Approach to Boost Airway Segmentation Performance (Li et al., 2024, PMC11298507)**:
- Problem: "intra-class imbalance due to volume differences between trachea and peripheral bronchi".
- Solution: **data augmentation** (generating synthetic intermediate-scale airways via interpolation between large and small real airways) combined with **per-level (per-class) loss weighting**.
- Per-level weighting: `w_level = log(N_voxels_level1 / N_voxels_level_k)`, giving larger weights to smaller, rarer levels.
- **Result**: on a private airway dataset (80 train / 20 test), compared to nnU-Net baseline, achieved **higher per-level Dice especially on small bronchioles** (exact numbers require full paper access — **flagged as unverified, abstract-only**).

**Learning Topology-Aware Implicit Field for Unified Pulmonary Tree Modeling with Incomplete Topological Supervision (Wang et al., arXiv:2602.02186, preprint 2026)**:
- Proposes implicit neural representation (INR) for airway tree, learning a signed distance function that respects topology even from incomplete/ambiguous annotations.
- Not traditional segmentation; more of a geometry-reconstruction approach.
- **Not directly transferable** to the coronary segmentation pipeline (which uses voxel prediction, not INR); noted here as a parallel direction, not a candidate for coronary.

### 3. Instance-level and per-branch metrics

**NaviAirway: A Bronchiole-Sensitive Deep Learning-based Navigation System for Bronchoscopy (Xu et al., arXiv:2203.04294, 2022)**:
- Evaluated on per-bronchiole detection rate (which branches were segmented), not just Dice.
- Metrics: recall (detection rate) and precision (were detected branches correct).
- **This is the same distinction** that [[Training plan]] evaluation makes: report per-class branch detection rate, not just mean Dice.

### 4. Multimodal and cross-dataset generalization

**Multiscope Topology Learning with Conditional Updating for Airway Segmentation (Pattern Analysis & Applications, 2025)**:
- Addresses generalization across different CT scanners and protocols.
- Uses multi-scale prediction and conditional loss weighting based on local context.
- **Measured on multiple scanners**: shows generalization challenges and solutions, directly relevant to coronary cross-site generalization (see [[Generalising across scanners and sites is the unmeasured risk in a single-centre cohort]]).

## Mechanisms that transfer to coronary

1. **Auxiliary centerline supervision** (from multi-task airway work): add a centerline-prediction head during training, which forces connectivity learning. The head is discarded at inference. This is already discussed in [[Binary-init fine-tuning and multi-task auxiliary heads for the multiclass model]] and flagged as a follow-on experiment.

2. **Per-class loss weighting by inverse frequency**: airways literature confirms that weighting smaller branches higher (log-scale or inverse-frequency) improves their per-class Dice. This is a standard technique and is directly applicable to coronary distal branches.

3. **Per-branch detection rate as the primary metric**: airways report branch detection (recall) and precision, not just Dice. The same distinction is essential for coronary: a model can achieve 85 % mean Dice while missing 30 % of distal branches if they are rare. Report per-class metrics separately.

4. **Skeleton Recall loss for multiclass**: already measured on airway-adjacent datasets (TopCoW, which includes cerebral arteries — a tubular structure similar to airway in scale and topology). This is the primary topology-aware loss candidate for coronary, and the evidence is already in [[Topology-aware losses on thin tubular structures]].

## What the airway literature does NOT solve for coronary

1. **Calcification and stents**: airways don't have calcified plaques or metal stents. The coronary failure modes (calcium blooming, stent artifacts) are not addressed by airway-trained models. This is a coronary-specific augmentation and training challenge.

2. **Cardiac motion artifact**: airways are in static lungs; coronaries move with the heart. Cross-validation from airway to coronary will not transfer motion robustness.

3. **Contrast timing and enhancement variability**: airways are imaged with air/no contrast; coronaries depend on iodine bolus timing. The 250–650 HU spread (Calicchio et al., documented in [[CT normalisation on a lumen-only foreground is the preprocessing risk nobody has checked]]) is not an airway problem.

## What this implies for [[Training plan]]

1. **Skeleton Recall is the primary topology-aware loss candidate**, and it is proven on airway-adjacent data (TopCoW). It is already a scheduled experiment (see [[Topology-aware losses on thin tubular structures]] and Proposed changes §1).

2. **Per-class loss weighting (inverse-frequency) is a safe, standard technique** confirmed to help rare classes in airway literature. Schedule this as a conditional second experiment (see [[Loss weighting between large proximal and rare distal branch classes]] Proposed changes).

3. **Per-branch detection rate and per-class metrics** should be reported for coronary, following the airway evaluation precedent. This is already in [[Training plan]] evaluation section (clDice, branch detection rate per class, AHA confusion).

4. **Centerline auxiliary head** (multi-task learning) is a candidate follow-on experiment after Skeleton Recall. The airway literature (MICCAI 2024) claims it works, but only abstract-level evidence exists for airway; no direct coronary CCTA measurement.

5. **Airway-trained foundation models (vesselFM, SAM-Med3D with airway examples) do not transfer to coronary**. See [[Foundation and promptable models do not yet beat a configured nnU-Net for coronaries]]; the structural differences (calcification, contrast phase, motion) are too large.

## What this implies for [[Proposed changes]]

- Add to evaluation section: "**Per-branch detection rate and per-class Dice reported separately**, following airway segmentation precedent (NaviAirway). A model scoring 85 % mean Dice while detecting 70 % of distal branches is not acceptable; report both metrics per class."

- Note under topology losses: "Skeleton Recall is proven on airway-adjacent (cerebral vessel) benchmarks (TopCoW, Kirchhoff et al. 2024); airway literature confirms per-class loss weighting helps rare branches (Li et al. 2024, cited as abstract-only — flagged for verification)."

Collected in [[Proposed changes]].
