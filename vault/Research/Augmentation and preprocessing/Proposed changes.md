---
aliases: [Proposed changes, Augmentation proposals]
tags: [research/preprocessing, proposal, decision-record]
status: living
updated: 2026-09-19
---

# Proposed changes to the training plan

Concrete edits to [[Training plan]] proposed by the augmentation-and-preprocessing
research thread, each with the note that carries the evidence. Nothing here has
been applied; this folder does not edit the plan.

## 1. Add a normalisation-window pre-submission gate

**Where:** §2, alongside the existing patch-fraction/spacing/batch-size gates.
**Proposed:** "(d) CT normalisation window — read `percentile_00_5`,
`percentile_99_5`, `mean`, `std` from `nnUNet_preprocessed/Dataset710_Coronary/
dataset_fingerprint.json` after first preprocessing and record them. If the window
is narrow (order 150–700 HU), it is worth a paired normalisation experiment against
whole-volume percentiles; if wide, no action needed."
**Evidence:** [[CT normalisation on a lumen-only foreground is the preprocessing risk nobody has checked]].

## 2. Add an anisotropy-branch confirmation to the same gate set

**Where:** §2.
**Proposed:** "(e) confirm from the planner printout that nnU-Net's anisotropy
branch does **not** fire for Dataset710. If it does, the through-plane resampling
axis silently drops to nearest-neighbour interpolation for both image and label —
the one interpolation mode most likely to damage a 1–2-voxel-wide vessel
cross-section."
**Evidence:** [[Resampling and interpolation choices matter more on 3-voxel branches than on organs]].

## 3. Record the intensity-augmentation rationale with a physical grounding, not "not in dispute"

**Where:** §5.
**Proposed:** replace the bare "intensity augmentations are not in dispute and stay"
with a one-line justification: "gamma and low-resolution-simulation transforms are
the ones that model reconstruction-kernel and contrast-phase variation, which
Calicchio et al. (2025) and Zhang et al. (2025) both show measurably affects
segmentation accuracy on CCTA; the current ±25% brightness/contrast range is
narrower than the documented cross-protocol lumen-attenuation spread (258–653 HU,
~+153%), which bounds cross-scanner robustness without affecting within-ImageCAS
training."
**Evidence:** [[CT normalisation on a lumen-only foreground is the preprocessing risk nobody has checked]],
[[Generalising across scanners and sites is the unmeasured risk in a single-centre cohort]].

## 4. Name calcium blooming and stents as known, currently-unaddressed confounders

**Where:** new bullet under "Still open" or §5.
**Proposed:** "Calcified plaque (blooming) is the best-characterised CCTA
confounder in the literature (odds ratio 2.49 for misdiagnosis, 10.16 for
false-positive stenosis at CACS ≥ 400 — Pack et al. 2022) and is not targeted by any
current augmentation; a validated digital-phantom blooming simulator exists (Wang
et al. 2026) but has not yet been used to train a segmentation model anywhere in
the literature. Stent prevalence in ImageCAS is unverified and worth checking
directly — no augmentation can substitute for missing stented training examples."
**Evidence:** [[Calcified plaque, stents and motion are the CCTA failure modes, and only some of them are augmentable]].

## 5. Add motion-exposed segments to the evaluation stratification

**Where:** Evaluation section, alongside the AHA-segment confusion matrix.
**Proposed:** "Stratify per-segment metrics to check mid RCA, mid LAD and distal LAD
separately — Vecsey-Nagy et al. (2022) name these as the segments most susceptible
to heart-rate-dependent motion artifact (image-quality score gap between scanner
types widening from non-significant at <60 bpm to 3.5 vs 2.7, p < 0.001, at
>70 bpm). Underperformance concentrated in these segments would corroborate a real
external effect rather than a modelling artefact."
**Evidence:** [[Calcified plaque, stents and motion are the CCTA failure modes, and only some of them are augmentable]].

## 6. Record cross-site generalisation as deferred-with-a-cost-estimate, not deferred-silently

**Where:** "Still open."
**Proposed:** "Cross-site/cross-vendor generalisation is out of scope while training
and evaluating on ImageCAS only, but the closest measured analogue (ASOCA→GeoCAD,
Zhang et al. 2025) shows 4–8 Dice-point drops concentrated in low-calcification
cases specifically. If cross-site evaluation is ever added, the cheapest evidenced
mitigation is appearance augmentation (bias-field + Bezier intensity remapping;
Mudaliar et al. 2026 measured +7.85 Dice cross-site on a structurally similar
cardiac-CT task) layered on the existing nnU-Net pipeline."
**Evidence:** [[Generalising across scanners and sites is the unmeasured risk in a single-centre cohort]].

## 7. Flag papers for hand fetch (paywalled or summary-only this session)

**Proposed:** note for whoever next has UofT-proxy or Chrome access —
(a) the AJR editorial on coronary stent imaging readiness (403 this session);
(b) TW-MoCoNet motion-correction paper (search-summary only, claimed 80.2%
reduction in moderate-artifact segments, unverified); (c) the CNN-based CCTA
denoising papers cited only via search summary (35.1→21.0 HU noise reduction
figure, unverified primary source). None of these numbers are currently cited as
evidence in the folder's notes; all are flagged as leads only.
**Evidence:** [[Calcified plaque, stents and motion are the CCTA failure modes, and only some of them are augmentable]].
