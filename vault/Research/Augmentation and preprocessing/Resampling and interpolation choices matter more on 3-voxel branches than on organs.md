---
aliases: [Resampling, Interpolation, Label resampling, Spline order]
tags: [research/preprocessing, nnunet, coronary, resampling, interpolation, evidence]
status: solid
updated: 2026-09-19
---

# Resampling and interpolation choices matter more on 3-voxel branches than on organs

[[Training plan]] §1 fixes target spacing to native (~0.35 mm, nnU-Net's
median-spacing rule) but does not discuss *how* voxels get there — the
interpolation kernel used when resampling both the CT volume and the label mask
from acquisition spacing to target spacing. For a liver or kidney this choice is
nearly invisible; for a structure that is 4–6 voxels wide it is not.

## What nnU-Net v2 actually does — verified in source

Read from `nnunetv2/preprocessing/resampling/default_resampling.py` (current
master):

- **Image data** (`is_seg=False`): resampled with scikit-image `resize`, **cubic
  spline, order 3 by default**, edge-mode padding, anti-aliasing off.
- **Segmentation labels** (`is_seg=True`): routed through `resize_segmentation`,
  which does **not** interpolate the integer label map directly (which would invent
  fractional label values with no meaning) — for the isotropic case it interpolates
  a per-class binary indicator and thresholds, effectively a one-vs-rest soft
  interpolation followed by a decision rule, rather than a plain nearest-neighbour
  or linear resample of the label integers.
- **Anisotropic volumes** (in-plane spacing much finer than through-plane, or vice
  versa — triggered by nnU-Net's own anisotropy heuristic): resampling is done
  **separately per axis**. In-plane keeps the order-3 (image) / per-class (label)
  scheme; the through-plane (z) axis uses **`order_z=0`, i.e. nearest-neighbour**,
  explicitly to avoid inventing anatomy between widely-spaced acquisition slices.
- **Our cohort is near-isotropic** (~0.29–0.45 mm, [[Training plan]]'s fixed
  constraints), so the anisotropy branch should not fire and both axes get the
  smoother, order-3 / per-class treatment — worth confirming once against
  Dataset710's actual planner output rather than assumed, the same discipline
  [[Cascade and low-resolution stages cost more than they buy on 0.35 mm vessels]]
  already applies to the cascade-trigger gate.

## Why this is the right default for thin vessels, not an accident to override

A plain nearest-neighbour resample of a label mask is the interpolation choice most
likely to damage a thin tube: it can only ever pick an existing voxel's label, so a
vessel that is 1–2 voxels across at some cross-section can lose a whole ring of
label around its true (sub-voxel) centreline whenever the resampling grid does not
land on the voxel that already carries the label — a discretisation error that gets
proportionally larger as the structure gets thinner. nnU-Net's per-class
soft-interpolate-then-threshold approach is a **partial-volume-aware** compromise:
it lets a voxel's revised label be decided by how much of each class's original
extent falls into it, rather than by which single old voxel happens to be nearest.
This is the same reasoning that makes bilinear/spline resampling standard practice
for image intensities generally; nnU-Net having applied an analogous idea to labels,
by default, is a genuine (if undocumented in the paper) piece of engineering that
this project inherits for free. No paper found runs a controlled ablation of
nnU-Net's label-resampling scheme against plain nearest-neighbour specifically on
coronary or other thin-vessel data — **this is asserted from the mechanism, not
measured on our anatomy**, and is worth flagging precisely because it is the kind of
"self-configuring" decision that is easy to trust without checking.

## Resampling order also interacts with the image/label resampling sequence itself

`CT normalisation on a lumen-only foreground` (sibling note) already establishes
that nnU-Net normalises intensities **before** resampling. The resampling step
itself then runs on already-normalised images, so any resampling-induced blurring
of intensity near a vessel boundary happens after the foreground-only percentile
clip — meaning a resampling artefact that pulls a boundary voxel's intensity toward
background is not subsequently re-clipped or re-centred, it simply propagates. This
is a second-order interaction, not a documented failure, but it is one more reason
the fingerprint-window check that note already proposes (read
`dataset_fingerprint.json` after first preprocessing) is worth doing before trusting
the pipeline blind on this cohort.

## What CCTA-specific interpolation literature exists

Search for coronary- or thin-vessel-specific interpolation ablations (order 1 vs 3,
sinc, or label nearest-neighbour vs soft-threshold) turned up general remote-sensing
and vessel-profile-extraction usage notes (nearest-neighbour for binary vessel
profiles, linear for grayscale) but **no controlled ablation on coronary CTA
segmentation accuracy specifically**. This is a real gap in the published evidence,
not a settled question resolved elsewhere — the case above is made from first
principles and from nnU-Net's own documented default, not from a coronary-specific
measurement.

## What this implies for [[Training plan]]

1. **No change needed to §1.** nnU-Net's default resampling scheme (order-3 image,
   per-class-threshold labels, isotropic branch expected to fire on this cohort) is
   already the partial-volume-aware choice appropriate for thin vessels, and
   overriding it toward plain nearest-neighbour would very likely make distal
   branches *worse*, not better.
2. **Add a confirmation, not a change, to the pre-submission gates.** Alongside the
   patch-fraction, spacing and normalisation-window gates already proposed
   ([[Cascade and low-resolution stages cost more than they buy on 0.35 mm vessels]],
   [[CT normalisation on a lumen-only foreground is the preprocessing risk nobody
   has checked]]), confirm from the planner printout that the anisotropy branch
   does **not** fire for Dataset710 — if it does, the through-plane axis silently
   drops to nearest-neighbour, which is the one interpolation mode this note argues
   against for thin structures.
3. **This is a genuine literature gap, worth naming rather than silently assuming
   settled.** If a future ablation budget exists, a resampling-scheme comparison
   (nnU-Net default vs plain nearest-neighbour labels) on the binary model would be
   the cheapest way to turn this note's mechanism argument into a measurement.

Related: [[CT normalisation on a lumen-only foreground is the preprocessing risk nobody has checked]],
[[Cascade and low-resolution stages cost more than they buy on 0.35 mm vessels]].
Collected in [[Proposed changes]].
