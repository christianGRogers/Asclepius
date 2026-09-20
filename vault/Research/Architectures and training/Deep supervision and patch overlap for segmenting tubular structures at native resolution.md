---
tags: [research/architecture, deep-supervision, patch-overlap, thin-vessels, nnunet]
status: solid
updated: 2026-09-20
aliases: [Deep supervision, Patch overlap, Intermediate supervision]
---

# Deep supervision and patch overlap for segmenting tubular structures at native resolution

[[Training plan]] commits to native 0.35 mm spacing with no cascade and large patches (256³–288×288×224). This note examines what deep supervision and patch-overlap strategies are known to work for thin structures at this scale.

## Deep supervision: mechanism and application

Deep supervision, also called intermediate or auxiliary supervision, adds loss terms at hidden layers of the network to improve gradient flow during training. Rather than computing loss only at the final output, intermediate supervision forces features learned at K-th layer to already be predictive of the target (Li et al., *A Comprehensive Review on Deep Supervision: Theories and Applications*, arXiv:2207.02376, 2022):

- **Hidden Layer Deep Supervision (HLDS)**: loss at K-th layer only.
- **Different Branches Deep Supervision (DBDS)**: loss at multiple branches of encoder and decoder; features from different branches are integrated for the final output.
- **Deep Supervision Post Encoding (DSPE)**: deep supervision at K-th layer, then that feature is encoded back into the main network.

The gradient update rule becomes:
```
θᵢ⁺ = θᵢ - η × (∂L_L/∂θᵢ + ∂L_K/∂θᵢ)
```
meaning weights from layer K to 1 are updated using gradients from both the final loss and the intermediate loss, reducing the vanishing gradient problem in very deep networks.

## Evidence on segmentation tasks

On medical imaging with U-Net backbones:
- Bui et al. (CT segmentation, deep supervision on last four layers of 3DUNet) reported improved gradient flow and convergence speed compared to final-layer-only loss.
- Wang et al. (2009) showed adding shallow and deep layer outputs from different encoder/decoder branches improved final prediction performance by learning both low-level and high-level features discriminatively.

The review (Li et al.) notes that **results are task-specific**: deep supervision reliably helps when the network is very deep (pushing against gradient vanishing), but adding supervision at too many layers or with poorly tuned α weights can cause overfitting or conflicting gradient signals at intermediate layers.

## Patch overlap and inference quality

At inference, nnU-Net applies sliding-window inference by default: patches are sampled at regular intervals with overlap (typically 25–50%), predictions from overlapping patches are aggregated using a discretized Gaussian weighting kernel to minimize edge artifacts. The trade-off is direct:

- **50% overlap**: fast, acceptable quality.
- **90% overlap**: highest quality, ~2–3× slower inference.

On vessel segmentation (NeuroVascU-Net, brain vessels in 3D T1 MRI, mean DSC 0.8609 and Jaccard Index 0.7582), sliding-window inference was used for validation ensuring unbiased evaluation; no direct ablation of overlap percentage is reported.

### Coronary-specific issue: what happens at patch edges?

The large patch is a core decision (patch-fraction gate §2 of [[Training plan]]), and inference will use sliding-window aggregation. For a 1.5–2 mm distal branch crossing a patch boundary:

- At **50% overlap**, the branch's cross-section spans two patches with only half redundancy.
- At **90% overlap**, nearly all voxels appear in multiple patch windows, giving the aggregator more samples to weight together.

No published measurement exists on coronary CCTA for this specific scenario. However, the principle is sound: thin structures are most sensitive to boundary artifacts because a 1–3-voxel-wide tube has few voxels left to average. The ImageCAS papers (Zeng et al.) do not report patch-overlap ablations for the binary model; they report the final model's performance but not inference strategy details.

## What this implies for [[Training plan]]

1. **Deep supervision is a candidate standing experiment, not a baseline change**. Add intermediate supervision losses (DBDS variant, deep supervision on encoder/decoder features that feed the final output) to one paired run of the multiclass model once labels exist. Use a default α (weighting intermediate loss) in the range 0.1–0.4 (Li et al. review notes equal weighting α=1 is typical but often leads to overfitting; dynamic adjustment by validation loss is also reported). Judge the experiment on convergence speed and final validation Dice, not on training loss smoothness alone.

2. **Confirm patch-overlap percentage before submission**. In `segtrain config` or `nnUNetv2_find_best_configuration`, the default overlap is 50%. For a 256³ patch at 0.35 mm spacing in a ~90 mm volume, this means 128 voxels of overlap. Because coronary branches are 1.5–2 mm (~4–6 voxels), confirm this before the first 24 h job. If the model shows fragmentation (see [[Largest-component post-processing is wrong for coronaries]]), a rerun with 90% overlap on the same checkpoint is cheap validation.

3. **Record intermediate supervision α and which layers** in the final notes if the experiment is run, so the choice is not silent.

## What this implies for [[Proposed changes]]

- Add a standing experiment: binary model baseline + deep supervision (DBDS, α hyperparameter tuned by validation loss, same fold/harness), once per-branch labels exist. Measure convergence epoch and final Dice.
- Note patch-overlap as a tuning knob if fragmentation appears in multiclass baseline results, not a pre-decision.

Collected in [[Proposed changes]].
