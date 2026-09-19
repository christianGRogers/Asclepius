---
tags: [research/augmentation, nnunet, imagecas, coronary, rotation]
status: solid
updated: 2026-09-19
aliases: [Rotation debate, Rotation ablation evidence]
---

# Rotation augmentation is disputed, but the two papers are not measuring the same operation

[[Training plan]] §5 records the disagreement as a standing experiment: nnU-Net
always rotates and found removing augmentation a loss across ten datasets, while
ImageCAS measured rotation + flip *hurting* by ~2.7 % (p < 0.0001) on this exact
cohort. Reading both sources at the primitive level, **the two results are not in
contradiction, because the word "rotation" means a different operation in each.**

## What ImageCAS actually measured

Zeng et al., *ImageCAS: A large-scale dataset and benchmark for coronary artery
segmentation based on computed tomography angiography images*, Computerized
Medical Imaging and Graphics 2023, DOI
[10.1016/j.compmedimag.2023.102287](https://doi.org/10.1016/j.compmedimag.2023.102287)
(read via the arXiv version, arXiv:2211.01607v2, which carries the same benchmark
sections).

Verbatim, from the patch-based segmentation experiments:

> "For data augmentation, the probability of rotation (randomly 0, 90, 180, 270
> degrees) and horizontal flipping are discussed. For ease of discussion, the two
> probabilities are set to the same value, and three values including 0, 0.2, and
> 0.5 are discussed."

> "For data augmentation, we find that flipping and rotation probabilities of 0/0
> (no flipping and rotation) obtains an improvement of 2.63 % (p < 0.0001) and
> 2.73 % (p < 0.0001) in Dice scores than that of 0.2/0.2 and 0.5/0.5. This
> interesting phenomenon may due to the fact that coronary arteries have its own
> directions with corresponding surround anatomies, and rotation and flipping
> operation may produce unrealistic augmented samples which may harm the training
> process."

Five properties of that experiment matter, and each weakens it as evidence
against nnU-Net's rotation:

1. **The rotations are 90°/180°/270°, not small angles.** These are gross
   reorientations of the anatomy — a heart on its side — not the plausible
   variation in patient positioning and cardiac axis that a ±30° rotation models.
2. **Rotation and flipping were never separated.** Both probabilities were tied
   to one value, so the ~2.7 % is the joint effect of rotation *and* mirroring.
   Mirroring is independently suspect here (see
   [[Mirroring is ruled out for multiclass, and it is a chirality problem, not only a left-right one]]).
3. **The measurement is on a small-patch pipeline, not nnU-Net.** It is the
   patch-based baseline of Fig. 2(b): a 3D U-Net over patches cropped at
   skeleton points, patch sizes 16³/32³/64³, with a 1:1 labelled/unlabelled crop
   ratio. In the same figure set the authors show patch size dominates
   (79.56 % → 81.22 % → 82.34 % Dice for 16³ → 32³ → 64³, all pairwise
   p < 0.0001 or p < 0.001, ImageCAS, 4-fold CV, 750 train / 250 test). A 16–64
   voxel patch of a rotated volume carries almost no anatomical context, so
   "the anatomy has its own orientation" is a claim the pipeline cannot actually
   exploit at that scale — and, symmetrically, a claim whose violation it may be
   unusually sensitive to.
4. **The axis of rotation is not stated** in the text I read. "Horizontal
   flipping" and 90° steps suggest in-plane (axial) operations, but this is
   **unverified**.
5. **The evaluation is Dice only**, on a merged binary lumen mask. Nothing in
   this ablation tells us what rotation does to distal-branch detection or to a
   *per-branch* task, which is the task [[Training plan]] actually targets.

## What nnU-Net actually does

Isensee, Jaeger, Kohl, Petersen and Maier-Hein, *nnU-Net: a self-configuring
method for deep learning-based biomedical image segmentation*, Nature Methods 18,
203–211 (2021), DOI
[10.1038/s41592-020-01008-z](https://doi.org/10.1038/s41592-020-01008-z); method
details read from the authors' preprint (arXiv:1904.08128, Supplementary D) and
cross-checked against the current v2 source.

From the paper's augmentation appendix:

> "Scaling and rotation are applied with a probability of 0.2 each (resulting in
> probabilities of 0.16 for only scaling, 0.16 for only rotation and 0.08 for
> both being triggered). If processing isotropic 3D patches, the angles of
> rotation (in degrees) x, y and z are each drawn from U(-30, 30)."

> "Mirroring. All patches are mirrored with a probability of 0.5 along all axes."

The v2 code (`nnunetv2/training/nnUNetTrainer/nnUNetTrainer.py`, master as of
commit `ded2aa3`, 2026-09-14) matches: in
`configure_rotation_dummyDA_mirroring_and_inital_patch_size`, a 3D configuration
whose patch is not anisotropic (`max(patch)/patch[0] <= 3`, the `ANISO_THRESHOLD`)
gets `rotation_for_DA = (-30°, +30°)` on every axis and `mirror_axes = (0, 1, 2)`;
`get_training_transforms` passes these to `SpatialTransform(..., p_rotation=0.2,
p_scaling=0.2, scaling=(0.7, 1.4))` and appends `MirrorTransform`. Our
configuration (near-isotropic ~0.35 mm, a roughly cubic ~256³ patch) will take
exactly this branch — so "rotation" in our run means **±30° about each axis,
triggered on about 20 % of samples**, which is roughly two orders of magnitude
gentler than what ImageCAS penalised.

The nnU-Net evidence for augmentation is also weaker than the plan's wording
suggests. What the paper tested was the **omission of the whole augmentation
pipeline** (one of nine blueprint variants, ranked across datasets D1–D10 of the
Medical Segmentation Decathlon with bootstrapped ranking); the default
configuration "shows the best generalization and ranks first when aggregating
results of all datasets", and the paper's own message is that "most performance
changes are not consistent over datasets". So:

- It is an all-augmentation ablation, **not a rotation ablation**. No per-axis or
  per-transform numbers exist in that figure.
- **None of the ten datasets is coronary CTA.** D1–D10 are the MSD tasks; the
  only cardiac one is left atrium MRI and the nearest vascular one is hepatic
  vessel CT. Generality across ten tasks is exactly the kind of claim the same
  paper warns not to extrapolate to an eleventh with different properties.
- I could not extract per-dataset Dice deltas for the no-augmentation variant
  from the preprint text; the figure is a ranking plot. **Unverified** as a
  number; verified as a direction.

## The honest summary of the disagreement

| | ImageCAS | nnU-Net |
|---|---|---|
| Operation | 90/180/270° rotation **and** horizontal flip, coupled | ±30° rotation per axis, p = 0.2; mirroring separate |
| Pipeline | 3D U-Net on 16³–64³ skeleton-centred patches | full pipeline, ~large isotropic patches |
| Cohort | ImageCAS, 1000 CCTA, one scanner, one centre | 10 MSD tasks, none coronary CTA |
| Result | no-aug better by 2.63 %/2.73 % Dice (p < 0.0001) | full-aug config ranks first on aggregate |

Both can be true. The defensible reading is: **gross reorientation plus mirroring
hurts coronary CTA segmentation; nothing in either paper tells us what a ±30°
rotation alone does on this cohort.** That is precisely the gap the plan's
standing ablation exists to close, and it is worth running because the answer is
genuinely unknown, not because the literature is split.

A physical argument for keeping some rotation: CCTA volumes are acquired supine
and reconstructed in patient coordinates, so the *scanner* frame is nearly
constant — but the *heart* is not aligned to it. Cardiac axis orientation varies
between patients, and rotation of ±30° is a cheap model of that variation plus
posture and table-angle differences. I have not yet found a peer-reviewed
measurement of cardiac-axis angular spread in CCTA to size that range; treat the
±30° default as unjustified-but-plausible rather than as calibrated.

## What this implies for [[Training plan]]

1. **Re-scope the standing rotation ablation.** The comparison worth running is
   nnU-Net default (±30°, p = 0.2, mirroring off) against rotation off
   (`p_rotation = 0`), mirroring off in both arms. Do *not* run 90° rotations —
   no result about them transfers to our configuration, and ImageCAS already
   measured them as harmful here.
2. **Fix the plan's citation of the ImageCAS number.** The ~2.7 % is
   rotation *and* flipping together, at 90° steps, on a 16³–64³ patch pipeline.
   Recorded as such above; the plan currently reads as if it were a rotation
   result comparable to nnU-Net's.
3. **Weaken the nnU-Net side of the claim too.** "Removing augmentation was a
   clear loss across ten datasets" should read "the full-augmentation
   configuration ranked first on aggregate across ten non-coronary datasets"; the
   paper offers no rotation-specific number.
4. **Cheap ordering.** Run the ablation on the *binary* model, where 1000 labelled
   cases already exist and mirroring is not yet ruled out by the task. The result
   transfers to the multiclass stage as a prior, and costs nothing that the binary
   stage is not already spending. If a third arm is affordable, add ±15° to see
   whether the effect is monotone in angle.
