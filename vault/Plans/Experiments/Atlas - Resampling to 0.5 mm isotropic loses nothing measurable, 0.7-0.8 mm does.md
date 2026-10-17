---
tags: [plans/experiment, resampling, spacing, resolution, imagecas-x]
author: Atlas
round: 1
updated: 2026-10-04
---

# Resampling to 0.5 mm isotropic loses nothing measurable; 0.7–0.8 mm does

## Question

Slices are 0.5 mm in every case and pixels 0.29–0.47 mm (median 0.35)
([[Atlas - Every case has 0.5 mm slices and nnU-Net's own planner fixes the patch menu]]). Training at 0.5 mm
isotropic halves the voxel count (median 275 × 358 × 358 instead of 275 × 512 × 512), which buys a patch that holds
the whole tree. The vault's position is that any resampling "destroys exactly the structures this project exists to
label" ([[Training plan]] §1). What does going from native in-plane spacing to 0.5 mm (and, for reference, to
0.7–0.8 mm, the regime of ImageCAS's measured −7.4 Dice) actually remove — from the image and from the labels?

## Method

Three independent measurements.

1. **Image spectrum (12 CT cases** with ImageCAS-X labels, `c0000`–`c0375` every 25th minus excluded): per case, a
   96 × 96 mm in-plane crop centred on the coronary tree, every axial slice through the tree, Hann-windowed 2D FFT,
   radial power profile. Power above the Nyquist frequency of a 0.5 mm grid (1.0 cycle/mm) and of a 0.7 mm grid
   (0.714 cycle/mm), as a fraction of total, and minus the noise floor (mean power density of the outermost ring of
   the native spectrum). `experiments/Atlas/ct_spectrum.py`.
2. **Centreline contrast (8 CT cases)**: CT cropped around the tree, resampled with a cubic spline and no
   anti-aliasing (what nnU-Net does to images) to 0.5 and 0.7 mm isotropic and back; at skeleton points of the four
   trunk classes, contrast = centre HU − local background (mean HU in a 1.0–2.5 mm shell outside the lumen, 6 mm
   neighbourhood), binned by centreline EDT; noise = robust SD of the high-pass residual in the shell.
   `experiments/Atlas/ct_contrast.py`, summary `summarise_ctc.py`.
3. **Label round trip (17 cases** of ImageCAS-X, every 6th id, ongoing): ImageCAS-X 14-class labels mapped to the
   project's 4 classes (LM = 1, LAD = 2, LCx = 3, RCA = 9; side branches → background). Each class's mask, in its
   own bounding box, linearly resampled to 0.5 / 0.8 mm isotropic and back, thresholded at 0.5, Dice against the
   original. This is the damage done to the *training target* (and, symmetrically, the resolution limit on the
   *output*, since nnU-Net resamples predicted probabilities back to the native grid). Also: lumen EDT (mm, ≈ radius
   + half a voxel) at centreline points per class. `experiments/Atlas/branch_geometry.py`, `summarise_bg.py`.
   ImageCAS-X lumen is ~3× thinner than our binary masks
   ([[Bridge - ImageCAS-X names transfer onto our binary masks, which are three times fatter]]), so this is the
   conservative (harder) case.

## Result

**1. There is no image signal above 1 cycle/mm.** The radial power spectrum falls steadily and flattens onto a
noise floor at ≈ 0.9–1.0 cycle/mm in every case (e.g. c0050, log₁₀ power: 0.68 cyc/mm 8.58 → 0.89 7.60 → 1.00
7.42 → 1.42 7.10). Power above the 0.5 mm Nyquist: **0.015–0.022 % of total, and 0.000–0.006 % after subtracting
the noise floor** (12/12 cases). Above the 0.7 mm Nyquist: 0.04–0.07 % of total, **0.025–0.042 % after noise** —
~10× more real signal, i.e. a 0.7 mm grid cuts real image content that a 0.5 mm grid keeps.

**2. Centreline contrast is unchanged at 0.5 mm.**

| Centreline EDT bin | points | native contrast | retained after 0.5 mm | after 0.7 mm |
|---|---|---|---|---|
| < 0.6 mm | 407 | 272 HU | 1.005 (min 1.002) | 1.002 (min 0.982) |
| 0.6–0.9 mm | 2214 | 336 HU | 1.002 | 1.030 |
| 0.9–1.3 mm | 1901 | 490 HU | 1.000 | 1.006 |
| > 1.3 mm | 1121 | 520 HU | 1.000 | 0.992 |

Noise ratio after/before: 0.997 (0.5 mm), 0.970 (0.7 mm). (Retention > 1 at 0.7 mm is spline overshoot; this
measure cannot see aliasing, which is why measurement 1 is the decisive one.)

**3. The 4-class target survives 0.5 mm; it does not survive 0.8 mm.**

| Class | Round-trip Dice at 0.5 mm: mean / p5 / min | at 0.8 mm: mean / p5 / min |
|---|---|---|
| LM | 0.996 / 0.992 / 0.992 | 0.938 / 0.893 / 0.830 |
| LAD | 0.994 / 0.991 / 0.990 | 0.911 / 0.886 / 0.874 |
| LCx | 0.994 / 0.991 / 0.990 | 0.907 / 0.871 / 0.855 |
| RCA | 0.997 / 0.993 / 0.985 | 0.940 / 0.906 / 0.828 |

The 0.5 mm loss grows with in-plane resolution (r = 0.72 with spacing) but is still ≥ 0.991 for the finest cases
(0.318 mm).

Calibre of the trunk classes (centreline EDT, ImageCAS-X lumen): LM median 1.50 mm, RCA 1.23, LAD 0.86, LCx 0.87;
LAD/LCx p10 0.50–0.60 mm. 31 % of LAD and LCx centreline points have EDT < 0.75 mm (these are the distal ends);
side branches (not our classes) median 0.66 mm. At 0.5 mm spacing the thinnest trunk segments are ~2–3 voxels across.

## What it implies

1. **0.5 mm isotropic is lossless at the resolution this CT actually has.** The scanner's reconstruction already
   band-limits the image below 1 cycle/mm; the 0.29–0.47 mm pixels oversample it. Resampling in-plane to 0.5 mm
   (z is already 0.5 mm, so nothing is resampled through-plane) removes only noise. Training at 0.5 mm iso is
   therefore *native resolution in information terms* while costing half the voxels.
2. The vault's warning is right for the regime it was measured in: ImageCAS's −7.4 / −12.3 Dice was 512² → 256²
   (≈ 0.7 mm) and 128³; at 0.7–0.8 mm this note measures real image signal lost and 6–9 Dice points of target
   damage. The cascade's low-res stage and anything at ≥ 0.7 mm stay ruled out. 0.5 mm is not in that regime.
3. ImageCAS-X trained every benchmarked method at 0.5 mm isotropic (arXiv:2608.30404, §Methods and App. E.1) and
   nnU-Net reached 89.8 binary Dice against a 92.8 inter-observer ceiling there — consistent with 0.5 mm not being
   the bottleneck.
4. This is a measured claim and still deserves one paired GPU run (0.5 mm iso vs native at equal VRAM) — it is
   ablation A1 in [[Atlas v1]].

## Limits

- 8–17 cases per measurement (CPU-bound, shared machine); the spectrum result was uniform across all 12 cases.
- The spectrum is in-plane and averaged over a 96 mm crop; local edge content of a single vessel is a small part of
  total power, which is why the noise-subtracted figure, not the raw fraction, carries the argument.
- Label round trip uses ImageCAS-X's thin lumen; the project's labels (partitions of our ~3× fatter binary masks)
  will lose less.
- None of this measures the network: a CNN might exploit sub-noise structure. A1 measures that directly.
