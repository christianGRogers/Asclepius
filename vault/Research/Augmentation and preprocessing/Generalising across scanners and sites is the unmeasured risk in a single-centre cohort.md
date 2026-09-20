---
aliases: [Domain generalisation, Scanner shift, Vendor shift, Kernel shift, Cross-site generalization]
tags: [research/preprocessing, coronary, domain-generalization, scanner, evidence]
status: solid
updated: 2026-09-19
---

# Generalising across scanners and sites is the unmeasured risk in a single-centre cohort

Already referenced from [[CT normalisation on a lumen-only foreground is the
preprocessing risk nobody has checked]]: "anything trained on ImageCAS inherits one
contrast protocol... this is a deployment decision the plan has not yet had to make,
but the annotation seeds it produces will be used on whatever data SegQueue ingests
next." This note gathers the direct evidence for that risk and what mitigates it.

## The risk, measured directly on coronary CTA cross-site transfer

Zhang, Gharleghi, Singh, et al., *Optimising Generalisable Deep Learning Models for
CT Coronary Segmentation: A Multifactorial Evaluation*, J Imaging Inform Med
39(3):2680–2694, 2025, DOI
[10.1007/s10278-025-01677-2](https://doi.org/10.1007/s10278-025-01677-2). Trained
nnU-Net, Swin-UNETR and EfficientNet-LinkNet on ASOCA (40 cases: 20 normal, 20
diseased; single centre, GE Lightspeed 64, fixed protocol), 5-fold CV, then tested
cross-site on GeoCAD (70 cases, private, more disease severity, prospective ECG
gating, implicitly different scanner/protocol mix). This is the cleanest available
measurement of exactly the transfer this project's binary/multiclass models would
face if deployed beyond ImageCAS:

- **Calcification-stratified Dice drop, ASOCA → GeoCAD**: statistically significant
  drops appeared *only* in the no-calcification group (**0.90 → 0.82, p = 0.001**)
  and low-calcification group (**0.86 → 0.79, p = 0.006**); moderate/high
  calcification groups were **not** significantly different across sites. Read
  carefully, this says the cross-site gap is **not** primarily a calcium-blooming
  story (see the sibling note) — it is worst on the *cleanest* vessels, which
  implicates something else about GeoCAD's acquisition (contrast, sharpness, noise)
  rather than plaque burden as the dominant driver of this particular gap.
- **What correlated with the cross-site Dice on GeoCAD**: artery contrast
  enhancement (r = 0.408, p < 0.001), edge sharpness (r = 0.239, p = 0.046),
  contrast-to-noise ratio (r = 0.201, p = 0.095, not significant). Already recorded
  in the sibling normalisation note; repeated here because it is the same evidence
  answering a different question — not "does image quality predict Dice" in
  general, but "what, specifically, differs enough between a source and a target
  site to move Dice." Enhancement and sharpness are acquisition/reconstruction
  choices, exactly the kind of thing that varies by scanner vendor and protocol,
  not by patient.
- **The authors' own recommended mitigations**: optimise pre-segmentation imaging
  (adequate contrast enhancement and edge sharpness at acquisition), adapt image
  characteristics between source and target with techniques like adaptive
  histogram equalisation, prefer motion-compensated acquisition and
  edge-enhancing reconstruction kernels, and develop calcification-specific
  handling especially for **low**-level calcification — the opposite emphasis from
  where most CCTA robustness work focuses (heavy calcification), consistent with
  their own stratified finding above.
- Caveat: ASOCA (40 cases) and GeoCAD (70 cases) are both far smaller than
  ImageCAS (1000 cases); per [[nnU-Net still beats transformer and Mamba
  architectures, and ResEnc is the only upgrade worth paying for]]'s benchmark-
  hygiene point, small cohorts produce noisier between-condition comparisons, so
  treat the specific correlation coefficients as directionally right rather than
  precisely calibrated.

## Kernel and vendor shift, as a general CT segmentation phenomenon

- Domain-shift-from-reconstruction-kernel is documented outside coronary imaging
  specifically for segmentation networks: models trained on one kernel family
  (e.g. smooth) lose accuracy when tested on another (sharp), and the general
  finding (lung/COVID segmentation literature, searched but not opened to primary
  source this session — **flagged, treat as directional**) is that **training on a
  mixture of kernels generalises better than training on either alone**. The
  physics behind why kernel choice matters specifically for coronary calcium is
  now quantified directly (see the sibling confounders note): Wang et al.'s digital
  phantom work measured normalised blooming area at 0.93 (sharp kernel) vs 1.07
  (soft kernel) — kernel does not just shift overall sharpness, it changes how much
  calcium visually encroaches on the lumen, which is a segmentation-relevant, not
  merely cosmetic, effect.
- ImageCAS's own documentation (per [[Training plan]]'s fixed constraints and the
  papers already read for other notes) does not report multi-vendor or multi-kernel
  acquisition — it is describable as effectively a single-protocol cohort at the
  level this project's decisions operate, which is exactly the condition under
  which kernel/vendor shift risk goes unmeasured until deployment.

## A directly transferable engineering pattern: appearance augmentation for cross-site nnU-Net

Mudaliar, Li, Lin, Vo, Liao, Wang, Hu, *Improving cross-site whole-heart
segmentation*, arXiv:2608.25109, 2026 (preprint; not coronary-specific — whole-heart
CT/MRI segmentation — but the closest published engineering recipe for exactly this
project's risk, built on the same framework). A TotalSegmentator-initialised
nnU-Netv2 pipeline with **site-characterised, label-preserving appearance
augmentation**: a bias-field augmentation (smooth multiplicative spatial intensity
perturbation) and a Bezier-curve nonlinear intensity remapping (cubic Bezier control
points reshaping the intensity-to-intensity mapping while preserving label
correctness), plus connected-component cleanup. Held-out cross-site validation:

| Modality | Dice before | Dice after | HD95 after |
|---|---|---|---|
| CT | 0.8350 | **0.9135** | 5.22 mm |
| MRI | 0.7695 | 0.7830 | 19.30 mm |

+7.85 Dice points on CT from appearance augmentation alone, on a held-out site the
model never trained on (site G, 20 CT cases). This is a **preprint**, on cardiac
chambers, not coronary lumen — the effect size should not be imported directly —
but the mechanism (bias-field and nonlinear intensity remapping as label-preserving
appearance augmentation, layered on top of an existing nnU-Net pipeline) is a
concrete, cheap, directly-portable recipe if this project is ever evaluated or
deployed beyond ImageCAS.

## What this implies for [[Training plan]]

1. **The plan currently has no position on cross-site generalisation, and the
   evidence says it should not need one yet — but should know the size of the gap
   it is deferring.** ImageCAS-trained models are validated on ImageCAS; the
   0.90→0.82 / 0.86→0.79 Dice drops above are the closest available estimate of
   what a naive cross-site deployment would cost, on a *different*, smaller
   coronary cohort pair, not on ImageCAS→elsewhere specifically.
2. **If cross-site or cross-vendor evaluation is ever added** (candidate targets:
   ASOCA and TotalSegmentator's coronary cohort, both already logged as
   external-validation candidates in `Handoffs.md`), the two cheapest mitigations
   with direct or closely analogous evidence are (a) widening the existing
   brightness/contrast/gamma augmentation ranges — already flagged as narrower
   than real cross-protocol HU spread in the sibling normalisation note — and (b)
   Mudaliar et al.'s bias-field plus Bezier intensity remapping, a two-transform
   addition to an existing nnU-Net pipeline with a measured +7.85 Dice cross-site
   gain on a structurally similar (cardiac CT) task.
3. **Do not conflate the calcification and cross-site questions.** Zhang et al.'s
   own stratified result shows the ASOCA→GeoCAD gap concentrated in
   *low*-calcification cases, not high — a useful correction to the intuitive
   assumption that "harder" (heavily calcified) cases are where cross-site risk
   concentrates.
4. **This remains explicitly deferred, not decided** — [[Training plan]]'s cohort
   is ImageCAS end to end for the binary and multiclass stages; this note exists so
   the deferral is a recorded decision with its cost estimated, not a silent gap.

Related: [[Calcified plaque, stents and motion are the CCTA failure modes, and only some of them are augmentable]],
[[CT normalisation on a lumen-only foreground is the preprocessing risk nobody has checked]].
Collected in [[Proposed changes]].
