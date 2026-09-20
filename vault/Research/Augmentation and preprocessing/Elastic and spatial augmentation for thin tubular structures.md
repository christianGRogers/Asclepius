---
tags: [research/augmentation, elastic-deformation, spatial, thin-vessels, nnunet]
status: solid
updated: 2026-09-20
aliases: [Elastic deformation, Spatial augmentation, Augmentation for vessels]
---

# Elastic and spatial augmentation for thin tubular structures

[[Training plan]] §5 preserves the intensity augmentations (gamma, low-resolution simulation, brightness, contrast) that are "not in dispute". This note examines elastic deformation and spatial transforms (rotation, scaling, mirroring) for thin tubular structures: do they help or do they blur the 1–2 mm branches we depend on?

## Elastic deformation: mechanism and application

Elastic deformation applies a random displacement field to the image and label, simulating deformations like anatomical variation or acquisition-induced warping:

1. Generate a random displacement grid (e.g., 4×4×4 nodes in 3D).
2. Initialize displacement at each node: `δ ~ Uniform(-α, α)` where α is a control parameter (typically 5–20 voxels).
3. Interpolate displacement at every voxel using cubic B-spline.
4. Warp the image and label: `x' = x + interpolate(δ)`.

**Interpolation choice matters**: cubic B-spline (smooth) preserves fine structure better than nearest-neighbor, which would destroy thin branches. nnU-Net uses cubic B-spline by default.

## What the literature reports on elastic deformation

### Vessel segmentation (non-coronary)

**DS6 paper (Deformation-aware Semi-supervised Learning, small vessel segmentation with noisy training data, Chlebus et al., PMC9605070)**:
- Task: segment small brain vessels from 7T MRA.
- Uses elastic deformation as part of data augmentation.
- Reported: elastic deformation is effective for small-vessel robustness; no direct ablation of elastic vs non-elastic is given, but the combined augmentation pipeline improves small-vessel detection.
- **Status**: elastic deformation is treated as standard practice, not questioned.

**Convolutional Neural Networks for vessel detection (large-vessel occlusion, Asadi et al., Springer, 2021)**:
- Task: detect large vessels in CT.
- Augmentation: "elastic deformations applied to augment training data".
- **Isolated measurement**: training with elastic deformation on 100 datasets raised ROC AUC from 0.56 (no augmentation) to **0.85 (with elastic deformation)**.
- **Caveat**: this is on large-vessel detection (classification), not fine segmentation; vessels are 10–20 mm, not 1–2 mm.

### nnU-Net's default behavior

nnU-Net v2 applies elastic deformation with `alpha = (0, 900)` (voxel units) and `sigma = (9, 13)` (smoothness of the displacement field):
- On a typical 256³ patch at 1 mm spacing, α=900 means displacements up to 900 mm — clearly way too large for real data.
- nnU-Net's planner automatically scales these to match the patch and spacing; effective α becomes order ~20–50 voxels.
- Elastic deformation is applied with probability ~0.2 (20 % of patches).

**For 0.35 mm spacing (coronary resolution)**:
- α=20 voxels = 20 × 0.35 = 7 mm maximum displacement.
- A 1.5 mm vessel at that displacement could move almost entirely across the image.
- But probability 0.2 means 80 % of training patches see zero elastic deformation.

## Elastic deformation on thin structures: potential risks

1. **Distal branches can disappear from a patch**. If a 1.5 mm distal branch is 2 mm from the patch boundary and is displaced outward by 7 mm, it leaves the patch entirely during training. The model never sees it.

2. **Elastic deformation is affine + nonlinear**. After deformation, the vessel may still be in the patch, but its position is randomized. For a 1 mm vessel, this is 3× its diameter—a significant perturbation. Rotation (affine) adds to this.

3. **Label-image correspondence**: both image and label are deformed by the same field, so topological breaks do not occur. However, if the deformation creates a very sharp bend (curvature ~1 mm), the thin-vessel segmentation network must learn that the bent version is still a valid vessel. This may slow convergence.

## What the evidence shows: help vs harm

**No direct coronary measurement exists** comparing "with elastic deformation" vs "without" on thin vessels. The literature is mixed:

- **Implicit evidence (positive)**: DS6 and Asadi papers apply elastic deformation as standard and report good results; no ablation removes it. This suggests practitioners consider it helpful, at least for robustness.

- **ImageCAS ablation (neutral)**: Zeng et al. (CMIG 2023, the ImageCAS binary lumen paper) report ablations for rotation/flip, architecture, loss, but **do not explicitly ablate elastic deformation**. nnU-Net's default pipeline includes elastic deformation, and their model achieves 82.96 % Dice; stopping the ablation there does not prove or disprove elastic deformation's contribution.

- **Theoretical concern (negative)**: rotating a 1.5 mm vessel by 45° in-plane, then elastically deforming it, creates anatomically implausible geometries. The network must learn that these deformed versions are still valid training examples. Coronary anatomy has preferred orientations; aggressive deformation throws that away.

## Spatial transforms: rotation, scaling, mirroring

Orthogonal to elastic deformation:

### Rotation

**[[Training plan]] §5 and [[Rotation augmentation is disputed, but the two papers are not measuring the same operation]]: this is already resolved.**
- ImageCAS measured rotation+flip hurting Dice by ~2.7 % (p < 0.0001).
- nnU-Net defaults to always rotating and found removal a clear loss on other datasets.
- Plan: ablate rotation separately from mirroring; intensity augmentations stay.

### Scaling (random re-scaling)

No isolated measurement on coronary. Scaling a 1.5 mm vessel by ±10% changes its diameter to 1.35–1.65 mm. This is plausible anatomical variation (vessels do vary in diameter), but it is not the same as elastic deformation (which is non-uniform). nnU-Net applies random scaling with factor ∈ [0.7, 1.3] (70–130 %) by default. No ablation on coronary exists.

### Mirroring

[[Training plan]] §4 and [[Mirroring is ruled out for multiclass, and it is a chirality problem, not only a left-right one]] already rule this out explicitly for multiclass.

## Risk: blur of thin vessels vs robustness

The core tension: aggressive spatial augmentation (elastic + rotation + scaling) can help generalization and robustness to anatomical variation, but on 1–2 mm structures, it risks:
- Moving branches out of patches.
- Creating implausible geometries that confuse the network.
- Slowing convergence because the effective training set becomes very large (every patch is unique).

On a 24-hour walltime with early-stopping-by-validation-loss, slower convergence is costly.

## What this implies for [[Training plan]]

1. **Keep elastic deformation in the baseline** — it is nnU-Net's default, removal would be a change, and there is no coronary evidence that it harms. Any gain from removing it would be small (maybe 0.5–1 Dice pp) and hard to detect.

2. **Do not schedule an elastic-deformation ablation as a standing experiment**. The evidence is insufficient to justify it, and the walltime cost of a paired run is high.

3. **If the multiclass baseline shows poor distal-branch Dice (<20 %) and slow convergence (early-stopped before 100 epochs), run a one-off diagnostic**: disable elastic deformation (set `p_elastic = 0` in nnUNetTrainerDefault), continue training on the same checkpoint for another 24 h, and measure final Dice. If distal-branch Dice improves and convergence speed increases, this is evidence that elastic deformation is harmful on this cohort. Otherwise, the poor performance is a separate issue.

4. **Scaling (0.7–1.3) is probably fine** — it models anatomical diameter variation, not just resolution artifacts. No action needed.

5. **Rotation remains ablated** (per existing decision). No change.

## What this implies for [[Proposed changes]]

- Add to §5 (standing experiments) **conditional diagnostic**: "If the multiclass baseline converges slowly (<100 epochs to early-stop) or distal-class Dice remains below 20 % despite per-class weighting, measure the effect of disabling elastic deformation (p_elastic = 0). Elastic deformation is preserved in the baseline; if its ablation improves distal-class metrics, it becomes an optimization lever. Otherwise, poor performance is attributed to class imbalance or model capacity, not augmentation strategy."

- Note in the evaluation section: "Convergence epoch and per-class Dice trajectory logged to identify whether augmentation choices affect different-scale branches differently."

Collected in [[Proposed changes]].
