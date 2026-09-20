---
tags: [research, coronary, dataset, benchmark, imagecast, stents, calcification, literature]
status: evidence-collected
updated: 2026-09-20
aliases: [ImageCAS disease burden, ImageCAS stents, ImageCAS calcification]
---

# ImageCAS disease burden and calcification status

Whether and in what proportion ImageCAS contains stents, calcified plaques, and the patient-level disease characteristics—flagged as unverified in [[Calcified plaque, stents and motion are the CCTA failure modes, and only some of them are augmentable]] and relevant to both [[Training plan]]'s evaluation strategy and the annotation protocol.

**Short answer.** The ImageCAS paper (Zeng et al., CMIG 2023, arXiv:2211.01607v2) states the cohort composition (age, sex, diagnoses, inclusion/exclusion) but does not report stent prevalence, calcification burden (Agatston score or similar), or any quantitative disease stratification beyond the inclusion criterion "known CAD patients, early revascularisation (within 90 days) included." No supplementary data sheet providing per-case disease staging, stent status, or calcification scores has been located. This remains an unverified gap.

## What the ImageCAS paper states

From §3 (Cohort Description):
- **414 female** (mean 59.98 y), **586 male** (mean 57.68 y): total n = 1000
- **Inclusion criteria**: age > 18 with documented ischaemic stroke, TIA and/or peripheral artery disease; for **known CAD patients, early revascularisation (within 90 days) included**
- **Exclusion**: index cardiac CTA, or low image quality assessed by a level III radiologist

Interpretation: The "known CAD patients, early revascularisation" language indicates a population enriched for significant disease (revascularisation-requiring), but the paper does not quantify what fraction are revascularised vs asymptomatic, diseased vs disease-free, or what the distribution of lesion severity/calcification is.

The paper explicitly states two cohort limitations: **"single centre, single scanner model, and no detailed labels is provided"** (the last referring to per-class branches, not to missing disease descriptors). No acknowledgment that stent or calcification data are missing or unavailable.

## Why this matters for this project

From [[Calcified plaque, stents and motion are the CCTA failure modes, and only some of them are augmentable]]:

- **Calcium blooming** (partial-volume artifact, worst in <2 mm structures): "blooming is measurably worse for small structures specifically… both worst exactly where a distal branch lives." The Wang et al. 2026 simulator confirms blooming magnitude depends on tube voltage and reconstruction kernel.
  
- **Stents** (metal artifact on already-small lumens): "stent struts and lumens under ~3 mm diameter are the ones blooming degrades most severely." Stent prevalence in the cohort is unknown; if significant, the model will train on a signal type (metal artifact) it will also encounter at test time.

- **Calcification status**: affects whether a lesion is calcified (calcium + stenosis, high specificity but variable sensitivity for hemodynamic significance) or non-calcified (softer plaque, higher risk for rupture and acute events). CAD-RADS v2.0 and clinical interpretation depend on calcification status. Neither the ImageCAS paper nor the released dataset documentation states Agatston score or per-case calcification category.

## What would be needed to close this gap

Three questions, in order of importance:

1. **Stent prevalence**: Of the 1000 cases, how many contain at least one stent? In how many branches do stents occur, and what are the stent types/materials (if documented)?
   
2. **Calcification burden**: Per-case Agatston score, or if unavailable, a binning into CAD-RADS calcification categories (minimal/mild/moderate/extensive)?
   
3. **Disease severity**: Per-case CAD-RADS stenosis category (1/2/3/4) or quantitative stenosis grades, and the distribution across the cohort.

These could appear in: (a) the supplementary material of Zeng et al. (if hosted online); (b) the Girder server copy of the dataset in this project (if annotators added disease metadata); (c) a follow-up paper from the ImageCAS team; or (d) not at all, in which case it is a dataset-documentation gap.

## What this implies for [[Training plan]]

1. **Before any claim about robustness to calcification or stents**, confirm the prevalence in the 1000 cases. If stents are rare (<5%), the model's learned features for stented segments may not generalize; this is a data-coverage gap, not an augmentation problem ([[Calcified plaque, stents and motion...]]).

2. **Stratify external-validation performance by calcification burden** if the binary model is scored on ASOCA: ASOCA does not report per-case Agatston scores in the published descriptor (Gharleghi et al., Sci Data 2023), but that might be available from the UK Data Service upon request. A calcification-stratified Dice drop would be direct evidence of whether blooming/calcium is a learned or un-learned failure mode.

3. **Evaluation stratification**: if ImageCAS composition includes a mix of diseased (revascularised) and non-diseased patients with high-risk stroke history, that difference in disease prevalence between training and test cohorts (if our annotators are labeling a different distribution) should be recorded as a potential source of performance variation.

4. **Annotation protocol decision**: if our annotators will see stented cases and we have not measured model behavior on them, either (a) version-gate the annotation interface so stented segments are annotated separately and performance is reported by stent status, or (b) accept that stented segments are a known gap and report accordingly in any manuscript.

See [[Public coronary CCTA datasets]], [[Fold schemes and split ratios]], [[External validation and cross-dataset generalisation for coronary segmentation]], and [[Proposed changes]].
