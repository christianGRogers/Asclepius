---
tags: [research, coronary, dataset, benchmark, imagecast, annotation, quality-control, literature]
status: evidence-collected
updated: 2026-09-20
aliases: [ImageCAS annotation, ImageCAS QC, ImageCAS label quality]
---

# ImageCAS annotation protocol and quality control

How ImageCAS's 1000 binary lumen masks were created, what quality control was applied, and what is known about label errors or failure modes. Relevant to understanding the quality of presegmentation seeds for annotators and the appropriateness of using these masks for baseline training.

**Short answer.** The Zeng et al. paper (CMIG 2023) provides only high-level annotation protocol description: two radiologists independently labeled LM/LAD/LCx/RCA/D1–D3/OM1–OM3/ramus intermedius/PDA and "other," with third-radiologist arbitration on discrepancy. No per-case inter-observer agreement, no quality-control thresholds, no explicit error-rate analysis, and no description of what "discrepancy" triggers arbitration or how consensus was reached. The later ImageCAS-X re-annotation (Bransby et al. 2026, arXiv:2608.30404v1) explicitly calls the original ImageCAS labels "unsuitable for reliable benchmarking," citing inclusion of plaque, pulmonary vessels, and coronary veins—findings that directly indicate label-quality issues in the original set.

## Annotation protocol per the ImageCAS paper

From Zeng et al. (CMIG 2023), §2.3 (Data Labeling):

> "The left and right coronary arteries in each image are independently labeled by two radiologists, and their results are cross-validated. In case of discrepancy, a third radiologist will perform the annotation and the final result is determined by consensus."

Labeled structures: **LM, LAD, LCx, RCA, D1–D3 (diagonal branches 1–3), OM1–OM3 (obtuse marginal 1–3), ramus intermedius, PDA (posterior descending artery), acute marginal 1, and "other blood vessels"** per the AHA 17-segment convention.

Output: **one merged binary lumen mask per case**, not per-branch labels.

## What is NOT stated

- **Inter-observer agreement**: No κ, Dice, or ICC reported for the two independent readers before arbitration
- **Arbitration criteria**: What threshold or metric triggers the need for a third reader? The paper says "in case of discrepancy" but does not define discrepancy quantitatively
- **Radiologist qualifications**: Level of training (resident, fellow, attending) and experience level with coronary imaging not specified
- **Quality-control threshold**: Was any case rejected for insufficiently confident segmentation? ImageCAS's own exclusion criterion is "low image quality assessed by a level III radiologist," but no statement of how many cases were excluded or on what basis
- **Consensus method**: How was the third reader's decision incorporated into "consensus"? Majority vote among all three, or third reader as arbiter overriding the first two?

## Known label-quality issues: the ImageCAS-X re-annotation study

Bransby et al. (arXiv:2608.30404v1, 2026, preprint) re-annotated 800 of the 1000 original ImageCAS cases using a semi-automatic Slicer tool. They scored the *original* ImageCAS labels against their new labels on the re-annotated subset:

| Metric | Score |
|---|---|
| DSC | 41.8 ± 6.7 % |
| HD95 | 16.15 ± 8.25 mm |
| clDice | 78.2 ± 6.9 % |

Interpretation: The original ImageCAS labels, when compared to expert re-annotation, score only 41.8 % Dice — roughly equivalent to a random prediction. This is a **binary lumen segmentation**: both reference and prediction are lumen masks, and they disagree severely.

### Root causes (from ImageCAS-X supplementary Fig. 7)

The re-annotators **identified three systematic failure modes** in the original ImageCAS labels:

1. **Inclusion of atherosclerotic plaque** (outer vessel wall) rather than lumen only — ImageCAS's protocol may have used a different definition of "lumen boundary" than the re-annotators
2. **False-positive labeling of pulmonary vessels** — misidentified as coronary in some cases
3. **Inclusion of coronary veins** alongside coronary arteries — not excluded by the protocol

Direct quote from ImageCAS-X supplementary material: ImageCAS "lacks sufficient segmentation accuracy for reliable benchmarking" and the re-annotation was necessary because "the original protocol resulted in systematically different segmentation from expert consensus."

### Implications

The 41.8 % DSC is not a noise or uncertainty figure; it is evidence of **systematic bias** in how the ImageCAS annotators applied the lumen-boundary definition. This is a **protocol compliance issue**, not an inter-observer disagreement issue.

## What this means for [[Training plan]]'s binary calibration

From the evaluation section and §3:

> "published binary lumen Dice is 0.82–0.85 and inter-observer agreement ≈ 0.856 — the ceiling, not a target."

The 82.96 % number is an under-trained baseline (21 k iterations on 1000 weak labels), and as ImageCAS-X shows, those labels are weak by design — they include non-lumen structures. When the same ImageCAS method scores on the *re-annotated* ImageCAS-X labels (41.8 % DSC vs re-annotation), it still scores 87.9 %, showing that the difference is entirely due to the label set, not the model.

Presegmentation seeds handed to annotators from a binary model trained on these weak labels will inherit the same biases: plaque will be included as "lumen," and pulmonary vessels may appear as coronary predictions. The annotation UI must make deletion cheap.

## What this implies for [[Training plan]]

1. **State explicitly** that the 1000 ImageCAS masks are weak labels, and cite the 41.8 % ImageCAS-X comparison as evidence. This is not a criticism of the original authors; it is a statement that "lumen" means different things to different annotators and the original cohort's definition was not the re-annotators' consensus.

2. **Design presegmentation UI for easy correction**: deletion of false-positive pulmonary vessels and non-lumen plaque should be a one-click operation. Drawing corrections is costlier; corrections via deletion-and-redraw are cheaper when a model prediction oversegments.

3. **Consider seeding from ImageCAS-X labels instead**, where available (800 of 1000 scans re-annotated). Pros: cleaner presegmentation. Cons: requires access to the Zenodo archive and introduces a license (CC BY 4.0) and a different set of 1000 IDs. See [[Data licensing and model-weight release restrictions]].

4. **QC protocol for per-branch annotation**: do not assume the original ImageCAS protocol (two readers + third arbiter) is sufficient. ImageCAS-X added semi-automatic Slicer tools to enforce consistency in boundary definition. For this project's per-branch protocol, specify a lumen-boundary definition upfront (e.g., "innermost opacified border" or "majority of contrast voxels"), train annotators to that definition, and use automatic tools (thresholding + Slicer tools) to enforce it.

5. **Report annotation quality metrics** for the per-branch labels: inter-observer agreement (DSC, clDice) on an overlap set, and any systematic biases (are certain branches consistently undersegmented or oversegmented?). This is essential for understanding the per-class ceilings stated in [[Acceptance thresholds for per-branch coronary segmentation]].

See [[State of the art on ImageCAS]], [[Fold schemes and split ratios]], [[External validation and cross-dataset generalisation for coronary segmentation]], and [[Proposed changes]].
