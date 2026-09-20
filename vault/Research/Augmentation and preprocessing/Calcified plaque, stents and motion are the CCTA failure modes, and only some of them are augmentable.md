---
aliases: [CCTA confounders, Blooming artifact, Motion artifact, Heart rate, Stents, Calcium blooming]
tags: [research/preprocessing, coronary, ccta, artifact, calcium, motion, evidence]
status: solid
updated: 2026-09-19
---

# Calcified plaque, stents and motion are the CCTA failure modes, and only some of them are augmentable

Already referenced from [[CT normalisation on a lumen-only foreground is the
preprocessing risk nobody has checked]] as the note carrying the CCTA-specific
confounder evidence. This note surveys the documented CCTA image-quality failure
modes — calcified plaque/blooming, stents, motion, heart rate and phase, low-dose
protocols — and asks which are plausibly fixed by augmentation and which are not.

## Calcified plaque and blooming: the dominant, physically-characterised confounder

Blooming is the apparent enlargement of a bright structure (calcium, metal) beyond
its true extent, and its root cause is well established, not disputed:

- Pack, Xu, Wang, Baskaran, Min, De Man, *Cardiac CT blooming artifacts: clinical
  significance, root causes and potential solutions*, Vis Comput Ind Biomed Art
  5:29, 2022, DOI
  [10.1186/s42492-022-00125-0](https://doi.org/10.1186/s42492-022-00125-0). Primary
  cause is **partial-volume averaging with the system point-spread function**
  (detector cell size ~1 mm, focal spot size, azimuthal blur, reconstruction
  algorithm), with motion and beam hardening as secondary, correctable
  contributors — the authors directly compare motion correction against
  multi-material beam-hardening correction and find motion correction has "much
  bigger impact." Clinically: calcification "independently increased the odds for
  overall misdiagnosis (odds ratio: 2.49)" and false-positive stenosis diagnosis
  (odds ratio: 10.16), with specificity dropping from 84% to 42% at high calcium
  burden (CACS ≥ 400). This is a diagnosis-level number, not a segmentation-Dice
  number, but the mechanism — calcium obscuring the true lumen boundary — is
  exactly what a lumen segmenter has to resolve.
- **The physics is now simulatable and quantified**, which matters for whether
  augmentation can target it. Wang, Li, Suo, et al., *Simulation of calcium
  blooming artifacts in coronary CT angiography from digital phantoms*, Cardiovasc
  Diagn Ther 16(4):65, 2026, DOI
  [10.21037/cdt-2026-0156](https://doi.org/10.21037/cdt-2026-0156). Built 20 digital
  vascular phantoms (varying plaque geometry and stenosis severity), simulated
  acquisition with GATE/SPEKTR/TIGRE at 80/100/120 kV and four reconstruction
  kernels (one sharp, three progressively softer), and validated against physical
  3D-printed phantoms scanned on three vendors' scanners (SSIM 0.94 ± 0.04 between
  simulated and acquired images; measured calcified area matched design to
  0.99 ± 0.05 of nominal, p = 0.54). Their key quantitative findings on what drives
  blooming magnitude: **normalised calcified area was 1.12 ± 0.13 at 80 kV, falling
  to 0.99 ± 0.11 at 120 kV (p < 0.001)** — lower tube voltage inflates apparent
  calcium size — and **0.93 ± 0.04 with a sharp kernel vs 1.07 ± 0.16 with a soft
  kernel** — sharper reconstruction reduces blooming. The authors explicitly propose
  the framework as a source of "large-scale and diverse training datasets with known
  ground truth" to "improve the generalizability of deep learning-based artifact
  reduction algorithms", but **do not themselves train or test a segmentation
  model** — the augmentation application is a stated future direction, not a result.
- **Blooming is measurably worse for small structures specifically**, corroborating
  the small-object HU-bias evidence already in [[CT normalisation on a lumen-only
  foreground is the preprocessing risk nobody has checked]] (Calicchio et al.: a
  2 mm iodine insert deviated −90 to −124 HU depending on kernel, a 22 mm object
  0 to −3 HU). Blooming and the small-object HU bias are two faces of the same
  partial-volume mechanism, one for hyperdense (calcium/metal) structures and one
  for the lumen itself — both worst exactly where a distal branch lives.

## Stents: a distinct, more severe version of the same partial-volume problem

- The blooming review above and search of the stent-imaging literature converge on
  one number: **stent struts and lumens under ~3 mm diameter are the ones blooming
  degrades most severely**, because the strut metal's blooming can occupy a large
  fraction of an already-small lumen cross-section — search summaries describing
  this as limiting in-stent restenosis assessment specifically for small-caliber
  stents; the primary AJR editorial making this point directly could not be fetched
  this session (403, no authenticated browser) and is **flagged for hand fetch**.
  ImageCAS, this project's cohort, is a lumen-segmentation dataset and its
  documentation does not describe systematic stent inclusion/exclusion; whether
  stented segments are present in meaningful numbers in our training data is
  **unverified and worth checking directly against the cohort**, since a stent is a
  qualitatively different signal (metal, not calcium) that neither the resampling
  nor the normalisation pipeline was designed around.
- No augmentation is known to simulate a stent from an unstented volume — unlike
  calcium blooming, which the digital-phantom paper shows is simulatable from
  physics, a stent's metal artifact is a foreign-object insertion problem, not a
  parameter one can dial on existing anatomy. If stented cases are rare in
  ImageCAS, the honest position is that the model will not have learned this
  failure mode, and no augmentation fixes that — it is a data-coverage gap, not a
  preprocessing one.

## Motion and heart rate: quantified, segment-specific, and only partially augmentable

- Vecsey-Nagy, Jermendy, Kolossváry, et al., *Heart Rate-Dependent Degree of Motion
  Artifacts in Coronary CT Angiography Acquired by a Novel Purpose-Built Cardiac CT
  Scanner*, J Clin Med 11(15):4336, 2022. 160 patients (80 dedicated cardiac CT
  matched to 80 conventional multidetector CT), 2,328 coronary segments scored
  across four heart-rate bands. Image-quality score (higher = better) fell
  monotonically with heart rate on both scanner types, and the gap between
  scanner types widened as heart rate rose: **<60 bpm no significant difference;
  60–65 bpm 3.9 vs 3.7 (p = 0.008); 66–70 bpm 3.5 vs 3.2 (p = 0.048); >70 bpm 3.5 vs
  2.7 (p < 0.001)**. Critically, they name which segments suffer most: **"the mid
  RCA, mid LAD and distal LAD, in particular, are susceptible to motion artifacts at
  high HRs."** This is a directly actionable fact for a per-branch model: the
  branches most exposed to motion artifact are not uniformly distributed across the
  tree, they cluster on specific mid/distal segments of the two longest, most mobile
  vessels.
- Whether motion blur is well modelled by nnU-Net's existing intensity augmentations
  is doubtful. "Simulate low resolution" (already catalogued in the sibling
  normalisation note) approximates a smoother reconstruction kernel or thicker
  slice, not the directional, phase-dependent smearing motion produces — motion
  blur has a preferred direction (along the vessel's motion path during the
  acquisition window) and nnU-Net's low-res simulation is isotropic. No coronary
  paper found tests a directional-blur augmentation against nnU-Net's isotropic
  default; this is an identified gap, not a resolved one.
- Deep-learning motion correction is an active pre-processing field (TW-MoCoNet and
  related work, read only as search summaries this session, not opened in full —
  reported an 80.2% reduction in segments with moderate artifacts after correction,
  **unverified, flagged for hand fetch**) but that is a preprocessing correction
  applied to the *input* image before our pipeline ever sees it, not something this
  project's augmentation choices can substitute for.

## Low-dose protocols: primarily a denoising problem, evidence is indirect for segmentation

Multiple deep-learning CCTA denoising papers (search only, not opened in full this
session) report noise reduction from low-dose acquisition (one reports 35.1 ± 7.8 HU
down to 21.0 ± 4.7 HU after CNN denoising) and describe joint denoising-plus-
segmentation architectures explicitly motivated by preserving "subtle coronary
branches" during denoising — i.e. the field already recognises that generic
denoising can blur away exactly the distal-branch detail this project needs, and
proposes segmentation-aware denoising as the fix. No paper found measures
segmentation Dice as a function of dose or noise level directly on coronary CTA
with a plain (non-segmentation-aware) denoiser; the risk is named in this
literature but not quantified for our purposes. **Flagged as a gap.**

## Which of these an augmentation strategy can plausibly target

| Confounder | Physically simulatable? | Existing nnU-Net augmentation that approximates it | Gap |
|---|---|---|---|
| Calcium blooming | Yes — kV and kernel effects now quantified (Wang et al.) | None directly; gamma/contrast augmentation changes brightness, not partial-volume geometry | No published segmentation-training use yet |
| Kernel/reconstruction shift | Yes, same phantom framework | "Simulate low resolution" partially (softer kernel ≈ more blur) | Sharp-kernel direction (less blur, more noise) not modelled at all |
| Motion blur | Partially — directional, phase-dependent | Not modelled (isotropic blur only) | No directional-blur augmentation tested on coronary data |
| Heart rate / cardiac phase | No — a physiological state, not an image transform | Not applicable | Segment-specific risk (mid RCA, mid/distal LAD) should inform *evaluation* stratification even if not augmentation |
| Stents | No — foreign-object insertion | Not applicable | Data-coverage question: is ImageCAS's stent prevalence known? |
| Low-dose noise | Yes, trivially | Gaussian noise augmentation (variance 0–0.1, p = 0.1) already present | Untested whether current noise range spans real low-dose regimes on this cohort |

## What this implies for [[Training plan]]

1. **Calcium blooming is the best-evidenced, most physically-characterised
   confounder, and the least represented in current augmentation.** nnU-Net's
   gamma/contrast/brightness transforms change global intensity statistics, not
   the partial-volume geometry that produces blooming. Simulating blooming
   directly is not yet a published training technique, only a validated physics
   simulator (Wang et al.) — this is a candidate research direction, not yet an
   evidenced fix, and should be recorded as such rather than adopted.
2. **Stratify evaluation by motion-exposed segments.** Vecsey-Nagy et al.'s named
   segments (mid RCA, mid LAD, distal LAD) give a concrete, literature-grounded set
   to check separately in the AHA-segment confusion matrix [[Training plan]]
   already specifies — if those segments underperform disproportionately, it
   corroborates a real, external, heart-rate-linked effect rather than a modelling
   artefact.
3. **Check ImageCAS's stent prevalence before assuming coverage.** No augmentation
   substitutes for missing stented examples in training data; this is a
   data-question to raise with the datasets/benchmarks owner (see `Handoffs.md`).
4. **Flag for hand fetch:** the AJR stent-imaging editorial (403 this session) and
   the TW-MoCoNet motion-correction paper (search-summary only) — both would
   sharpen the stent and motion sections above from mechanism-level to
   quantified.

Related: [[CT normalisation on a lumen-only foreground is the preprocessing risk nobody has checked]],
[[Generalising across scanners and sites is the unmeasured risk in a single-centre cohort]].
Collected in [[Proposed changes]].
