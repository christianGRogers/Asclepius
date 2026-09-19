---
aliases: [Research context, RESEARCH-CONTEXT]
tags: [research, coronary, nnunet, dataset, benchmark, literature]
status: draft
updated: 2026-09-19
---

# Research context

The two papers [[Training plan]] leans on, condensed: **ImageCAS** (the data and
the 82.96 % benchmark) and **nnU-Net** (the method and its configuration rules).
Everything below was read from the sources named; nothing is from memory.

- **ImageCAS** — Zeng A, Wu C, Lin G, Xie W, Hong J, Huang M, Zhuang J, Bi S,
  Pan D, Ullah N, Khan KN, Wang T, Shi Y, Li X, Xu X. *ImageCAS: A large-scale
  dataset and benchmark for coronary artery segmentation based on computed
  tomography angiography images.* Computerized Medical Imaging and Graphics
  2023;109:102287. doi:10.1016/j.compmedimag.2023.102287. Author list and
  journal reference verified against Crossref; full text read from the author
  preprint arXiv:2211.01607v2 (17 Oct 2023). The ScienceDirect version is
  paywalled and was not opened, so page-level quotes below are from v2.
- **nnU-Net** — Isensee F, Jaeger PF, Kohl SAA, Petersen J, Maier-Hein KH.
  *nnU-Net: a self-configuring method for deep learning-based biomedical image
  segmentation.* Nature Methods 2021;18(2):203–211. doi:10.1038/s41592-020-01008-z
  (online 7 Dec 2020). Title, volume, pages and DOI read from the Nature
  article page; the full text there is paywalled (institutional log-in was not
  available in this session), so the method detail below is from the authors'
  preprint **arXiv:1904.08128v2**, "Automated Design of Deep Learning Methods
  for Biomedical Image Segmentation", read in full. Where the two differ, see
  "Preprint vs published" at the end.

## ImageCAS

### The cohort

| Property | Value (from §3) |
|---|---|
| Scans | 1000 3D CCTA volumes, one per patient |
| Scanner | Siemens 128-slice dual-source, single vendor |
| Centre | Guangdong Provincial People's Hospital, April 2012 – December 2018 |
| Reconstruction phase | 30–40 % or 60–70 %, whichever gives the best coronary images |
| Image size | 512 × 512 × (206–275) voxels |
| In-plane resolution | 0.29–0.43 mm²; spacing 0.25–0.45 mm |
| Sex / age | 414 female (mean 59.98 y), 586 male (mean 57.68 y) |
| Inclusion | age > 18 with documented ischaemic stroke, TIA and/or peripheral artery disease; for known CAD patients, early revascularisation (within 90 days) included |
| Exclusion | index cardiac CTA, or low image quality assessed by a level III radiologist |

The paper's own stated limitations: single centre, single scanner model, and
"no detailed labels is provided" — the coronary subclasses (LM, LAD, …) are
**not separated** in the released masks. That last sentence is the reason this
project exists.

### The labels

"The left and right coronary arteries in each image are independently labeled
by two radiologists, and their results are cross-validated. In case of
discrepancy, a third radiologist will perform the annotation and the final
result is determined by consensus." The text then lists which vessels are
*included* in the labelled region — LM, LAD, LCx, RCA, D1–D3, OM1–OM3, ramus
intermedius, PDA, acute marginal 1 and "other blood vessels", per the AHA
17-segment convention — but the released mask is a single merged binary lumen
label. Figure 1's caption is explicit: "subclasses of coronary arteries are not
further individually labeled."

No inter-observer agreement number is reported anywhere in the paper. Any
"inter-observer ≈ 0.856" figure does **not** come from ImageCAS; see
[[State of the art on ImageCAS]] for the inter-observer number that does exist
for this cohort (ImageCAS-X, 92.8 % DSC).

### Split and training budget

- "Experiments were evaluated using a 4-fold cross-validation approach, with a
  training set of 750 cases (50 cases are used for validation) and a test set of
  250 cases." The official split ships as `imageCAS_data_split.xlsx`; its exact
  structure is decoded in [[Fold schemes and split ratios]].
- All networks: 30 epochs ≈ **21,000 iterations**, Adam, lr 0.002, one RTX 3090
  (24 GB). Dice loss (graph method excepted). Batch size 8 / 2 / 1 for input
  128³ / 256×256×128 / 512×512×256.

### Results that the plan uses

- Benchmark table (Table 4, Dice %): direct segmentation (3D FCN, 512×512×256
  input) **80.58**, HD 28.67 mm, AHD 0.8503 mm; patch segmentation (3D U-Net,
  64³) 72.01; tree-based (3D TreeConvGRU) 68.78; graph-based (GCN) 70.61;
  their baseline (coarse + multi-scale patch ensemble, with dilation)
  **82.96**, HD 27.2169 mm, AHD 0.8180 mm.
- **Input resolution dominates.** 512×512×256 beats 256×256×128 by **7.38 %**
  (p < 0.0001) and 128³ by **12.32 %** (p < 0.0001) Dice. (The plan quotes
  −12.3 %; the paper's figure is 12.32 %.)
- **Augmentation.** Rotation (0/90/180/270°) + horizontal flip at probability
  0.2 and 0.5 *hurt*: no augmentation was better by **2.63 %** (p < 0.0001) and
  **2.73 %** (p < 0.0001) respectively. Their explanation: coronary arteries
  have their own orientation relative to surrounding anatomy, so rotated and
  flipped samples are unrealistic. Note the confound — rotation and flipping
  were varied *together* under one probability, on 16³–64³ patches, at 21 k
  iterations. This is the ablation the plan disagrees with nnU-Net about.
- **Attention gate** +1.34 % (p < 0.0001); 12 channels vs 4 channels +2.13 %
  (p < 0.0001); Frangi input channel +0.01 % (n.s.).
- **Connected-component post-processing** removes vessel-like false positives
  "for most of the predicted images", but Fig. 8(b) shows a failure where the
  pre-segmentation keeps bone tissue and real coronary is partly removed.
- **Tree/graph methods fail structurally**: they depend on a centreline derived
  from a pre-segmentation, and "some coronary arteries are missing in
  pre-segmentation … these coronary arteries are missing in the rest of the
  processing". This is the evidence behind the plan's §4 exclusion.
- Baseline ablation (Table 3), Dice %: patch 16³/32³/64³ without dilation
  79.56 / 81.22 / 82.34; with dilation 77.80 / 82.27 / 82.70; patch ensemble
  81.11; coarse + patch ensemble **82.96**.

### Access

Kaggle (`xiaoweixumedicalai/imagecas`) or by e-mail to the corresponding
author. **No licence statement** is given in the GitHub repository (checked
2026-09-19) — the code repo carries no LICENSE file and the README states no
terms. The README also warns that folders ending in "(1)" are duplicated cases,
since removed; anyone using an older copy should re-download. Licence and
provenance detail: [[Public coronary CCTA datasets]].

## nnU-Net

nnU-Net is not an architecture but a **configuration procedure**: a fixed
blueprint, a set of rules that read a "data fingerprint", and a small number of
empirical choices made from cross-validation.

### Blueprint (data-independent)

- Plain U-Net template, deliberately *without* residual/dense connections,
  attention, squeeze-excitation or dilated convolutions: "a well-configured
  plain U-Net is still hard to beat".
- Instance normalisation (batch size is 2, so batch norm is out), leaky ReLU
  (slope 0.01), two conv blocks per resolution, strided-conv downsampling,
  transposed-conv upsampling, 32 initial feature maps doubling per stage,
  capped at 320 (3D). **Deep supervision** at all but the two lowest
  resolutions, loss weights halving per resolution and normalised to 1.
- Training: **1000 epochs × 250 minibatches** (= 250 k iterations), SGD with
  Nesterov momentum 0.99, initial lr 0.01, `poly` decay (1 − e/e_max)^0.9.
- Loss: **sum of cross-entropy and Dice**.
- Sampling: 66.7 % of patches from random locations, **33.3 % guaranteed to
  contain one randomly chosen foreground class** (forced minimum 1 per batch).
  This is exactly the rule the plan flags as starving rare branches.
- Augmentation: rotation and scaling (each p = 0.2; isotropic 3D patches rotate
  by U(−30°, 30°) per axis; scale U(0.7, 1.4)), Gaussian noise (p = 0.15),
  Gaussian blur (p = 0.2), brightness, contrast, **simulated low resolution**
  (p = 0.25), gamma (p = 0.15, plus an inverted-intensity variant), and
  **mirroring along all axes with p = 0.5**.
- Inference: sliding window with 50 % overlap, Gaussian importance weighting
  toward patch centres, **test-time augmentation by mirroring along all axes**.
  (Both the mirroring augmentation and the mirroring TTA have to be switched
  off for a left/right-distinguishing multiclass task — see [[Training plan]] §4.)

### Rule-based (from the fingerprint)

- **Fingerprint**: image sizes before/after cropping to the non-zero region,
  spacings, modalities, class counts, and foreground intensity mean, s.d.,
  0.5/99.5 percentiles.
- **CT normalisation**: global clip to the foreground 0.5/99.5 percentiles, then
  global mean/s.d. — not per-image z-scoring.
- **Target spacing**: median spacing per axis over training cases. The 10th
  percentile is used for the lowest-resolution axis only when both voxel and
  spacing anisotropy exceed 3 — which, at ImageCAS's near-isotropic spacings,
  never fires.
- **Patch size**: initialised to the median image shape after resampling, then
  reduced along the largest axis until the architecture fits the GPU memory
  budget; topology (number of downsamplings per axis) is recomputed at each
  step; downsampling stops when a feature-map axis would fall below 4 voxels or
  spacings become anisotropic. Memory is *estimated from feature-map sizes*, so
  planning needs no GPU.
- **Batch size**: 2 whenever the patch was reduced; otherwise grown to fill the
  GPU, capped so a minibatch is ≤ 5 % of the total training voxels.
- **Cascade trigger**: the 3D cascade is configured **only when the `3d_fullres`
  patch covers less than 12.5 % of the median image shape**; the low-resolution
  spacing is then increased in 1 % steps until the patch covers 25 %. This is the
  threshold the plan's §2 gate is written against.

### Empirical

- Cross-validate every applicable configuration (2D, `3d_fullres`, `3d_lowres`,
  cascade) in **5-fold CV** over the training data, then pick the best single
  configuration or the best ensemble of two by mean foreground Dice.
- **Post-processing**: test whether keeping only the largest connected component
  (first over all foreground as one, then per class) improves cross-validation
  Dice; adopt only if it does not reduce any class's Dice. It is a *measured*
  choice, not an unconditional rule — worth knowing when the plan rules it out
  for coronaries.

### Evidence value

- Applied to **10 international challenges, 19 datasets, 49 tasks** (preprint
  v2), trained from scratch on challenge data only; "nnU-Net sets a new state of
  the art in 29 out of 49 target structures".
- Figure 6: nine blueprint variations (CE loss, TopK10, residual encoder,
  three convs per stage, lower momentum, Adam, batch norm, **omission of data
  augmentation**) ranked on ten Decathlon datasets with bootstrapped rankings.
  No variant improves consistently, and the **original configuration ranks first
  on aggregate**. This is the correct reading of the nnU-Net side of the
  rotation dispute: augmentation removal loses *on aggregate across ten
  non-coronary datasets*, which is weaker than "rotation helps on coronaries"
  and is why [[Training plan]] §5 schedules the ablation instead of assuming.
- The KiTS 2019 leaderboard analysis: all top-15 entries are U-Net offspring,
  and identical architectures span the whole leaderboard — configuration beats
  architecture. This is the argument for running the plain U-Net baseline before
  the ResEnc variant.

### Preprint vs published

The published Nature Methods abstract says nnU-Net "surpasses most existing
approaches, including highly specialized solutions on **23 public datasets**
used in international biomedical segmentation competitions", whereas preprint v2
describes 19 datasets / 49 tasks. The dataset count grew between versions; the
method description is otherwise the one quoted above. Numbers cited from v2 are
labelled as such throughout this vault.

## What this implies for [[Training plan]]

1. The plan's ImageCAS numbers check out, with one correction: the
   low-resolution penalty is **12.32 %** (128³ vs 512×512×256, p < 0.0001), not
   −12.3 % from "512²×256 to 128³" in the other direction — same fact, worth
   stating as the paper does.
2. The plan's "inter-observer agreement ≈ 0.856" is **not** an ImageCAS number.
   Replace it with the ImageCAS-X inter-observer figure (92.8 ± 3.1 % DSC on
   their test set, their labels) or drop it — see
   [[State of the art on ImageCAS]].
3. §2's 12.5 % gate is exactly nnU-Net's cascade trigger, correctly stated, and
   the planner needs no GPU to report it — so the gate is checkable before any
   submission.
4. Add **mirroring test-time augmentation** to the list of things to disable for
   the multiclass model. The plan disables mirroring augmentation but not the
   TTA, and nnU-Net applies both by default.
5. The ImageCAS rotation result is confounded (rotation and flip varied
   together, small patches, 21 k iterations). The plan's decision to ablate
   rotation *separately* from mirroring is the right call and should say why.
6. nnU-Net's largest-component post-processing is a measured, conditional step
   in the original method. The plan rules it out for coronaries on ImageCAS's
   Fig. 8(b) evidence, which is sound, but the wording should acknowledge that
   nnU-Net only adopts it when cross-validation says so.

See [[Proposed changes]] for the concrete edits.
