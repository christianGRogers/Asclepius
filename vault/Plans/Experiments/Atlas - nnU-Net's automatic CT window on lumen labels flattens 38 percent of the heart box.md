---
tags: [plans/experiment, preprocessing, normalisation, nnunet, imagecas-x]
author: Atlas
round: 1
updated: 2026-10-04
---

# nnU-Net's automatic CT window on lumen labels flattens 38 % of the heart box

## Question

nnU-Net's `CTNormalization` clips every CT to the [0.5, 99.5] percentiles of **foreground** (labelled-voxel)
intensities pooled over the training set, then z-scores with the foreground mean/std (mechanism verified in
[[CT normalisation on a lumen-only foreground is the preprocessing risk nobody has checked]]). With lumen-only
coronary labels, what window does that produce on this cohort, and what does it erase? And what window would the
original binary masks produce?

## Method

- Cases: the 32 CT-cached cases (`c0000, c0050, …, c0975`, every 25th, minus 8 that ImageCAS-X excludes) that have
  an ImageCAS-X label. ImageCAS-X (Bransby et al., arXiv:2608.30404; Zenodo 10.5281/zenodo.21887809, CC BY 4.0) is an
  expert lumen re-annotation of 800 of these 1000 scans; its file `N.coronary.nii.gz` is our case `c{N-1:04d}`
  (verified: header shape + affine matched uniquely for all 800, `experiments/Atlas/match_icx.py`).
- Lumen HU: up to 10 000 random voxels per case of (a) ImageCAS-X lumen (labels > 0), (b) our binary mask. Pooled
  0.5/99.5 percentiles = the window nnU-Net would pick.
- "Heart box": the bounding box of the ImageCAS-X tree in each case, 200 000 random voxels per case, pooled.
- Script: `experiments/Atlas/ct_norm_window.py`.

## Result

| Foreground used for the fingerprint | Clip low (HU) | Clip high (HU) | Median fg HU | Heart-box voxels below clip | above clip |
|---|---|---|---|---|---|
| **ImageCAS-X lumen** (a lumen-only protocol, like ours) | **65** | **688** | 347 | **37.8 %** | 0.3 % |
| Our original binary masks (ImageCAS) | −164 | 640 | 105 | 11.1 % | 1.0 % |

Heart-box HU percentiles (1/5/25/50/75/95/99): −873 / −771 / −28 / 102 / 245 / 545 / 642. 14 % of the box is
epicardial-fat range (−200…−30 HU).

Per case, the ImageCAS-X lumen's own 0.5th percentile ranges 15–108 HU and its 99.5th 462–820 HU. Our binary mask's
per-case 0.5th percentile ranges −622 to −104 HU and its median 44–161 HU: half of the "vessel" voxels in the
original masks are at soft-tissue or fat attenuation, i.e. not contrast-filled lumen.

## What it implies

0. **Which row applies depends on the label convention.** SegQueue confines annotator edits to the existing
   coronary mask (`docs/SEGQUEUE.md`, "Masking that makes fast painting safe"), so the team's 4-class labels will be
   partitions of *our* binary masks, and the fingerprint window will be close to the second row
   (≈ −164…640 HU; a trunk-only partition would sit a little higher). A model trained on ImageCAS-X-convention
   labels gets the first row. Both rows clip calcium to the intensity of bright lumen; the first also erases fat.

1. With the default pipeline and a lumen-only label set, **everything below 65 HU becomes one value**: epicardial
   fat (the tissue the coronaries run in and that defines the interventricular and AV grooves), lung, air, and the
   low-attenuation end of non-calcified plaque. **Everything above 688 HU also becomes one value**, so calcified
   plaque (typically > 700 HU with blooming) is mapped to exactly the intensity of bright lumen. For a model whose
   job is to tell LAD from LCx by anatomical context and to keep calcium out of the lumen, that is the wrong
   default. This is a preprocessing bug any nnU-Net-based plan inherits unless it is overridden.
2. **Fix (cheap, one plans edit):** overwrite `foreground_intensity_properties_per_channel` in
   `nnUNetPlans.json` with a fixed window, **clip [−300, 1300] HU**, and mean/std computed over that window inside the
   heart box (or simply mean 0, std 500 — z-scoring only rescales). No custom code; preprocessing must be re-run.
   This is in the Atlas recipe and is cheap enough for any plan.
3. The binary masks' intensity profile (median 105 HU, tail to −600 HU) is further evidence that they are not lumen
   masks — see [[Bridge - ImageCAS-X names transfer onto our binary masks, which are three times fatter]] (my own 15-case check agrees: volume ratio 2.4–4.0×, Dice 0.33–0.57).

## Limits

- 32 cases; percentiles are pooled the way nnU-Net pools them, but nnU-Net samples up to 10⁸ voxels over all cases.
  With 32 × 10 000 lumen samples the 0.5/99.5 percentiles are stable to a few HU.
- That the clipping *hurts accuracy* is inferred from what is erased, not measured; measuring it needs a paired
  GPU run (proposed in the Atlas plan as part of run R1, costed there). The fix has no plausible downside.
