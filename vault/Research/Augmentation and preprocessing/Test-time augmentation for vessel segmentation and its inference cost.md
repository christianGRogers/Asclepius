---
tags: [research/augmentation, test-time-augmentation, tta, inference, cost-benefit]
status: solid
updated: 2026-09-20
aliases: [TTA, Test-time augmentation, Inference cost]
---

# Test-time augmentation for vessel segmentation and its inference cost

At inference, test-time augmentation (TTA) applies multiple transformations to each test image (e.g., original + flipped + rotated + scaled), runs inference on each variant independently, and averages the predictions before final thresholding. This note examines whether TTA is worth the computational cost for coronary vessel segmentation.

## Mechanism and cost

**How TTA works:**
1. Original image passes through the network: `ŷ_0 = model(x)`.
2. Flipped horizontally: `ŷ_1 = model(flip_h(x))`, then flip predictions back.
3. Flipped vertically: `ŷ_2 = model(flip_v(x))`, then flip predictions back.
4. Other augmentations (rotations, scaling): `ŷ_k = model(augment_k(x))`.
5. Average predictions: `ŷ_final = mean([ŷ_0, ŷ_1, ŷ_2, ..., ŷ_K])`.
6. Threshold and return binary/multiclass map.

**Inference time cost:**
- Baseline (single forward pass): 1× inference time.
- TTA with N variants (N=3 for typical H/V flip + original): **~3× inference time**.
- TTA with 8–12 augmentations (rotations + scales): **~10× inference time**.

For coronary CCTA at 0.35 mm (no crop, full 512×512×250 volume), sliding-window inference is already expensive:
- Single forward pass: ~5–10 seconds per volume on H100.
- With 50 % patch overlap (order ~100–150 patches per volume): already 50–150 seconds.
- **TTA 3×: 150–450 seconds per volume = 2.5–7.5 minutes per case.**

On a dataset of 1000 cases, this is 40–125 GPU-hours for inference-only, which is substantial.

## Evidence from vessel segmentation literature

### Positive (TTA helps)

**Cardiac segmentation (PULSE: multi-task cardiac architecture, Datta et al., arXiv:2512.03848, 2025, recent preprint)**:
- Task: cardiac chamber and vessel segmentation from multi-modal cardiac imaging.
- TTA used: three-view augmentation (original, horizontal flip, vertical flip).
- Effect: "TTA stabilizes inference and reduces structural fragmentation and boundary uncertainty".
- Quantitative result: **not explicitly stated** in the abstract; full paper access needed. **Status: abstract-only, unverified.**

### Neutral (TTA does not consistently help)

**Coronary artery segmentation comparison (search result found but full details not accessed)**: 
- Tri-axial fusion (architectural choice: U-Net with feature fusion across three orthogonal views) **outperformed single-axis approaches combined with TTA** when evaluated on multiple metrics.
- **Implication**: architectural design (tri-axial features) is a better lever than inference-time augmentation for coronary segmentation. One source says "TTA may not be the most efficient choice for vessel segmentation when good architecture is available."

### General TTA overhead

**Albumentations documentation (standard practice)**: TTA typically incurs **2–3× inference time** for 2–3 augmentations, cost rises linearly with augmentation count.

**Better Aggregation in Test-Time Augmentation (Shankar & Wilber, arXiv:2011.11156, 2020)**:
- Shows that naive averaging of TTA predictions can be suboptimal; learned weighting or more sophisticated aggregation can improve results.
- Does not address coronary segmentation; general computer vision paper.
- **Key insight**: the aggregation strategy matters; simple averaging may lose information.

## Coronary-specific considerations

1. **Mirroring is ruled out for multiclass** (see [[Training plan]] §4 and [[Mirroring is ruled out for multiclass, and it is a chirality problem, not only a left-right one]]). This eliminates the cheapest TTA variant (horizontal/vertical flips), which would otherwise be trivial.

2. **Rotation is already disputed** (see [[Rotation augmentation is disputed, but the two papers are not measuring the same operation]]). ImageCAS measured rotation+flip hurting Dice; applying rotation at test-time reverses that decision, creating an internal contradiction.

3. **Sliding-window inference already provides aggregation**. Overlapping patches are averaged with Gaussian weighting, which is similar to TTA's averaging. Raising patch overlap from 50% to 90% provides the smoothing benefit of TTA at a cost only slightly higher than TTA (more GPU memory, same VRAM), with the advantage of guaranteed consistency (same model, no need to re-reverse augmentations).

4. **No published comparison on coronary CCTA** exists between:
   - Baseline + 90 % overlap inference, vs.
   - Baseline + 50 % overlap + TTA (3–5 augmentations).

## The core question: overlap or TTA?

Both strategies aim to reduce inference edge artifacts. The trade-off:

- **Higher patch overlap (90 %)**:
  - Cost: ~1.5–2× single-pass time (each voxel appears in more patches).
  - Benefit: consistent predictions (same model, deterministic).
  - Drawback: must re-run from checkpoint; cannot be applied post-hoc.

- **TTA**:
  - Cost: ~3× single-pass time (typically 3 augmentations; more with rotations).
  - Benefit: can be applied to any existing checkpoint; no retraining.
  - Drawback: relies on augmentations that may not apply (rotation ruled out, mirroring ruled out for multiclass).

On coronary, with mirroring and rotation ruled out, effective TTA is reduced to maybe original + 1–2 other augmentations (scaling, elastic deformation), which is still ~2–3× cost but with less clear benefit.

## What this implies for [[Training plan]]

1. **TTA is not scheduled as a baseline or standing experiment**. The inference cost is 2–3× for a gain that is unquantified on coronary CCTA and may not exist given architectural constraints (rotation/mirroring ruled out).

2. **If final validation Dice is below acceptance threshold** (<80 % for the mean, <60 % for rare classes), measure the effect of TTA **post-hoc on the best checkpoint**:
   - Apply TTA with 3 augmentations: original, 10% scaling up, 10% scaling down.
   - Do NOT apply rotation or mirroring (ruled out).
   - Measure Dice and inference time.
   - Accept TTA only if Dice gain is >1 pp and inference time budget permits it.

3. **Alternatively: increase patch overlap to 90 %** (from default 50 %) and retrain from the best-validation checkpoint. This provides smoothing without augmentation-reversal overhead. Measure Dice and wall-time; compare to TTA.

4. **Do not apply TTA to per-class rare-branch metrics**. If a rare class Dice remains low despite TTA, the issue is not inference smoothing; it is a training problem (undersampling, class weighting, etc.).

## What this implies for [[Proposed changes]]

- Add to evaluation section: "**Inference strategy tuning** is deferred to post-baseline. If validation Dice gap between multiclass baseline and acceptance threshold is >1 pp, measure: (a) Increasing sliding-window overlap to 90 % with retraining from best checkpoint, vs. (b) Test-time augmentation (scaling variants only, no rotation/mirroring) applied post-hoc. Accept either if Dice gain exceeds 1 pp and inference time is acceptable; if both achieve gains, choose the lower inference cost."

- Note: "TTA on coronary CCTA is untested; the cardiac-imaging positive result (Datta et al. 2025) is abstract-only and unverified. The architectural constraints (rotation ruled out per §5 ablation, mirroring ruled out per §4) limit TTA to non-affine augmentations; the benefit is unclear."

Collected in [[Proposed changes]].
