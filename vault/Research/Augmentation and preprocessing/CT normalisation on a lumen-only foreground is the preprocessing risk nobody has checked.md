---
tags: [research/preprocessing, nnunet, coronary, normalisation, intensity]
status: solid
updated: 2026-09-19
aliases: [CT normalisation, Windowing, Intensity normalisation]
---

# CT normalisation on a lumen-only foreground is the preprocessing risk nobody has checked

[[Training plan]] settles spacing and patch size but says nothing about
intensity. nnU-Net decides that automatically, and for this task the automatic
decision has a property worth looking at before the first 24-hour block is
spent.

## What nnU-Net will actually do to our Hounsfield units

Verified in source (`nnUNetv2`, master, commit `ded2aa3`, 2026-09-14):

1. `src/segtrain/convert.py:395` writes `"channel_names": {"0": "CT"}`, so
   `get_normalization_scheme` selects **`CTNormalization`**.
2. The fingerprint extractor
   (`nnunetv2/experiment_planning/dataset_fingerprint/fingerprint_extractor.py`)
   collects intensity statistics **only over foreground voxels** —
   `foreground_mask = segmentation[0] > 0` — sampling up to 10⁸ voxels across the
   dataset, and stores `mean`, `std`, `percentile_00_5`, `median`,
   `percentile_99_5`.
3. `CTNormalization.run` then does, for every voxel of every image:
   `np.clip(image, percentile_00_5, percentile_99_5)`, then subtract the
   foreground `mean` and divide by the foreground `std`.
4. Normalisation happens **before** resampling
   (`default_preprocessor.py`: "normalization MUST happen before resampling").

For a liver or pancreas dataset the foreground is a large soft-tissue organ and
those percentiles bracket a sensible CT window. **Our foreground is the coronary
lumen**: a few thousand voxels per case of iodinated blood, typically several
hundred HU, with partial-volume edges below that. So the 0.5–99.5 percentile
window is computed over contrast-filled lumen only, which has two consequences
for the rest of the image:

- Everything **below** the lower bound — epicardial fat (≈ −100 HU), myocardium
  (≈ 40–100 HU), lung, air — is clipped to a single value. Vessel-versus-
  background contrast survives (the lumen is above the bound), but the *context*
  that distinguishes a coronary from a cardiac vein, a pulmonary vessel, or a
  bone edge is partly flattened. That context is exactly what [[Training plan]]
  §2 says whole volumes are kept for ("learn to reject coronary look-alikes").
- Everything **above** the upper bound — calcified plaque, stents, bone, and the
  bright tail of the aortic root — saturates to one value. Calcium is then
  indistinguishable from the brightest lumen by intensity alone, which is the
  wrong compression for a cohort where calcified plaque is the documented
  failure mode (see
  [[Calcified plaque, stents and motion are the CCTA failure modes, and only some of them are augmentable]]).

**This is a mechanism, not a measurement.** I have not seen the fingerprint for
Dataset710 — it does not exist yet — so the actual numbers are unknown and the
severity is unverified. The check is free: after `segtrain` preprocessing, read
`percentile_00_5` / `percentile_99_5` / `mean` / `std` from
`nnUNet_preprocessed/Dataset710_Coronary/dataset_fingerprint.json` and compare the
window to the HU ranges below. If the window turns out to be, say, 150–700 HU, it
is worth an experiment; if it comes out wide, there is nothing to fix.

## Why absolute HU cannot be trusted anyway: contrast-phase and protocol variability

Calicchio, Epstein, Boussoussou et al., *Impact of technical, patient-related and
measurement variables on serial Hounsfield unit-based quantitative coronary
plaque analysis in computed tomography: time for a new chapter*, European Heart
Journal – Imaging Methods and Practice 3(1):qyaf014, 2025, DOI
[10.1093/ehjimp/qyaf014](https://doi.org/10.1093/ehjimp/qyaf014):

- Dropping tube voltage from 140 to 100 kVp raised mean ascending-aortic
  attenuation from **520 HU to 653 HU**, and that shift systematically changed
  HU-threshold-based plaque measurements (non-calcified plaque down, calcified
  plaque up; r = −0.61 and r = 0.59, P < 0.01).
- The reference standard the whole low-attenuation-plaque literature rests on
  (Motoyama et al.) was acquired at **135 kVp with 258 HU** lumen attenuation —
  i.e. published coronary lumens span roughly **250–650 HU** across ordinary
  protocols, a factor of ~2.5.
- Small objects are measured wrong: a 2 mm iodine insert of nominal 147 HU
  deviated by **−90 to −124 HU** depending on reconstruction kernel, while a
  22 mm object deviated by 0 to −3 HU. Vessels below 4 mm were accurate only
  with photon-counting detector CT.
- Their recommendation for serial imaging is rigid protocol matching — which is
  precisely what a segmentation model deployed across sites cannot assume.

The last point matters twice: a **distal** coronary is a small object, so its
apparent HU is not just noisier than a proximal one, it is *biased low*, and the
bias depends on the reconstruction kernel. Any preprocessing that assumes a
single, scanner-independent HU meaning for "lumen" is assuming something the
physics does not deliver, and it is worst exactly where this project's value lies.

Independently, image-quality factors measured on real CCTA correlate with
segmentation accuracy. Zhang, Gharleghi, Singh et al., *Optimising Generalisable
Deep Learning Models for CT Coronary Segmentation: A Multifactorial Evaluation*,
Journal of Imaging Informatics in Medicine 39(3):2680–2694, 2025, DOI
[10.1007/s10278-025-01677-2](https://doi.org/10.1007/s10278-025-01677-2), trained
nnU-Net, Swin-UNETR and EfficientNet-LinkNet on ASOCA (40 cases, GE Lightspeed 64,
0.625 mm slices) and tested on GeoCAD (70 cases, GE and Siemens, prospective ECG
gating):

- **artery contrast enhancement vs Dice: r = 0.408, p < 0.001**
- **edge sharpness vs Dice: r = 0.239, p = 0.046**
- contrast-to-noise ratio vs Dice: r = 0.201, p = 0.095 (not significant)

So how bright and how sharp the artery is predicts how well it gets segmented,
on the test cohort. Note the ordering: *enhancement* matters more than *noise*.

## The intensity augmentations we keep, and what range they actually cover

[[Training plan]] §5 says intensity augmentations "are not in dispute and stay".
For the record, what that means concretely in nnU-Net v2 (`nnUNetTrainer.py`,
`get_training_transforms`), applied to already z-scored data:

| Transform | Range | Probability |
|---|---|---|
| Gaussian noise | variance 0–0.1 | 0.1 |
| Gaussian blur | σ 0.5–1.0 | 0.2 (per channel 0.5) |
| Multiplicative brightness | ×0.75–1.25 | 0.15 |
| Contrast | ×0.75–1.25, range preserved | 0.15 |
| Simulate low resolution | downsample factor 0.5–1 | 0.25 (per channel 0.5) |
| Gamma, inverted image | γ 0.7–1.5, stats retained | 0.1 |
| Gamma | γ 0.7–1.5, stats retained | 0.3 |

Two observations. First, **"simulate low resolution"** is the transform that
matches this project's stated risk profile best: it blurs and re-upsamples, which
is a reasonable model of a thicker-slice or smoother-kernel acquisition, and of
the partial-volume behaviour of a distal vessel. Keeping it is well motivated,
not just conventional. Second, the brightness/contrast range of ±25 % is
**narrower than the real protocol spread** documented above (258 → 653 HU is
+153 %). Within-cohort that is irrelevant — ImageCAS is one scanner at one centre
— but it bounds how much cross-scanner robustness the defaults can buy. See
[[Generalising across scanners and sites is the unmeasured risk in a single-centre cohort]].

## What this implies for [[Training plan]]

1. **Add a fourth pre-submission gate.** Alongside patch fraction, target
   spacing and batch size, print and record the CT normalisation window
   (`percentile_00_5`, `percentile_99_5`, `mean`, `std`) from
   `dataset_fingerprint.json`. It costs nothing and it is the one preprocessing
   decision currently made silently.
2. **If the window is narrow, run a paired normalisation experiment** on the
   binary model: nnU-Net default against `intensityproperties` overridden in
   `plans.json` with percentiles computed over whole volumes (or a fixed
   CCTA-motivated window). One variable, one fold, same harness. Do not change it
   blind — nnU-Net's default is well tested and the failure is hypothetical until
   the fingerprint says otherwise.
3. **Record intensity augmentation as a decision with a reason**, not as "not in
   dispute": low-resolution simulation and gamma are the transforms that model
   kernel, slice-thickness and enhancement variation, which is the documented
   source of CCTA variability.
4. **Anything trained on ImageCAS inherits one contrast protocol.** If the model
   is ever to run on outside data, widen brightness/contrast/gamma ranges
   deliberately rather than relying on defaults, and validate on a second cohort.
   This is a deployment decision the plan has not yet had to make, but the
   annotation seeds it produces will be used on whatever data SegQueue ingests
   next.
