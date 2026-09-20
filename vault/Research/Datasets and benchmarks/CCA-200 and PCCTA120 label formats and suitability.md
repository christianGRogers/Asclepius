---
tags: [research, coronary, dataset, benchmark, ccta, literature]
status: evidence-collected
updated: 2026-09-20
aliases: [CCA-200, PCCTA120, Secondary datasets]
---

# CCA-200 and PCCTA120 label formats and suitability

Two 2024–2026 CCTA datasets mentioned in [[Public coronary CCTA datasets]] as "found but not independently opened." Both are flagged as requiring direct verification before any use. This note records what is known from secondary sources and what remains unverified.

**Short answer.** **CCA-200** ships as internal-diameter annotations (a series of radius measurements along a centerline), not a voxel lumen mask—fundamentally different from our task. **PCCTA120** appears to offer artery *and* plaque masks, but whether the artery labeling is per-branch or binary lumen, and whether it is usable as a multiclass training source, could not be verified from available abstracts. Both datasets remain unsuitable for direct use without primary-source confirmation.

## CCA-200

### What is known from secondary sources

Mentioned in a 2025 IEEE TMI paper (not independently opened in this session; cited in [[Public coronary CCTA datasets]] §"Other 2024–2026 releases"):

- **200 CCTA cases** with **internal diameter annotation** (not full lumen voxel mask)
- Ground truth is described as a "geometry-based" diameter series
- One method (geometry-based coronary vectorisation) reported: **0.778 Dice on CCA-200**, 0.895 on ASOCA
- The same method on ASOCA (standard binary lumen benchmark) scored **0.895 Dice**

### Why this is not usable

The core issue: **internal diameter annotation is not a voxel lumen segmentation**. It is a 1D diameter series along a centerline, more similar to CAT08's centerline-labeling task than to ImageCAS's per-voxel binary or per-branch lumen labeling.

Implications:
- Cannot be used as training data for a voxel semantic segmenter
- The reported Dice numbers (0.778) are comparing a voxel prediction to a diameter-series ground truth via some conversion rule—the conversion rule is not stated in the secondary source and could dramatically affect interpretability
- If CCA-200 is ever needed (e.g. for centerline extraction validation), it would require either (a) voxel-level re-annotation, or (b) a separate centerline-extraction evaluation pipeline

### Recommendation

Mark CCA-200 as **not suitable for voxel segmentation training**. If downstream centerline-extraction evaluation becomes a priority, CCA-200 is a candidate external benchmark, but its label format must be verified first from the primary source.

## PCCTA120

### What is known from secondary sources

Found in a 2026 paper on joint artery + plaque segmentation (cited in [[Public coronary CCTA datasets]]); abstract only read:

- **120 CCTA volumes** with **manual artery and atherosclerotic plaque masks**
- Described as a **binary** artery labeling (not per-branch/multiclass) in the secondary description
- Described as having both lumen and plaque annotations, suggesting a two-class voxel mask

No other details located (case composition, disease burden, acquisition protocol, license, availability, fold scheme).

### Why verification is needed

The critical unknown: **is the artery label binary (lumen only) or does it include plaques?** If binary lumen + binary plaque, then:
- It is a two-class problem (lumen, plaque), not a voxel semantic segmentation of the type we need
- It could be converted to binary-lumen-only by merging classes, making it a single-class dataset
- Its value as a multiclass training source is zero

If the description "artery masks" means a binary-lumen-only label and "plaque" is a separate, overlapping segmentation:
- It could be used for plaque-aware preprocessing or segmentation-aware denoising
- It is not a per-branch source
- Its value for our binary or multiclass task is limited unless per-branch labels are available

### Recommendation

Mark PCCTA120 as **not verified for use without primary-source inspection**. The 2026 paper's full text should be fetched and read to confirm: (a) whether artery labels are truly binary lumen or something else, (b) whether they are per-branch or binary, and (c) whether plaque presence affects lumen annotation quality. This is a 30-minute task but essential before treating PCCTA120 as a candidate multiclass source.

## General lesson: secondary data in the literature

Both examples show a common pattern: papers cite "dataset X" in passing without clearly stating the label format, and the format is often different from what one would expect. For this project:

- **CCA-200** illustrates the diameter-vs-voxel ambiguity: a method paper citing a dataset may not be precise about the format-conversion step
- **PCCTA120** illustrates the binary-vs-multiclass ambiguity: a plaque-segmentation paper's "artery masks" may not be the lumen-only binary our project needs

The takeaway is the inverse of [[Fold schemes and split ratios]]'s lesson: just as ID lists must be verified by intersection before claiming leakage is avoided, dataset formats must be verified from the primary source before claiming suitability for a downstream task.

## What this implies for [[Training plan]]

1. **CCA-200 is not a candidate training source** for voxel-multiclass segmentation. If centerline extraction becomes a downstream evaluation task, consider CCA-200 as an external benchmark dataset only, after primary-source verification of the diameter-series format and its conversion to voxel predictions.

2. **PCCTA120 requires primary-source verification** before any use. The 2026 paper's full text must be read to determine whether it is (a) a plaque dataset with a binary-lumen sidecar, (b) a two-class lumen-plus-plaque dataset, or (c) something else entirely. Current evidence is too sparse to guide a decision.

3. **No additional per-branch CCTA datasets besides ImageCAS-X were found** in a 2023–2026 search ([[Public coronary CCTA datasets]], "Still unverified" and general search): CCA-200 and PCCTA120 do not fill that gap, and ASOCA/CAT08/orCaScore remain the only other options (ASOCA for binary lumen, CAT08 for centerlines, orCaScore for calcium only).

See [[Public coronary CCTA datasets]], [[Fold schemes and split ratios]], [[External validation and cross-dataset generalisation for coronary segmentation]], and [[Proposed changes]].
