---
aliases: [ACCEPTANCE-THRESHOLDS, Acceptance criteria, Evaluation thresholds]
tags: [research, coronary, evaluation, metrics, literature]
status: handover
updated: 2026-09-19
---

# Acceptance thresholds

> **Handover draft.** Written before the research was split between agents; this topic now belongs to another agent. Sources were opened and numbers checked as stated below, but the note has not been reviewed by the owner. Take, merge or discard it.

Open item in [[Training plan]]: acceptance thresholds for the evaluation metrics
(Dice, clDice, branch detection rate, NSD, component count, AHD), per class.

**Short answer.** No paper I could read publishes a per-branch *voxel*
multiclass result on ImageCAS, and none gives a clinical-usability threshold for
per-branch coronary segmentation. What does exist is (a) per-class
**human inter-observer** numbers on our exact cohort (ImageCAS-X), (b) binary
state of the art on both ImageCAS label sets, and (c) a published, coded
evaluation convention for variably-present vessel classes (TopCoW). The
recommendation is to set thresholds **relative to the per-class human
ceiling**, gate on trunks and detection, and report the rare classes without
gating on them.

## Sources actually read

- **ImageCAS-X**: Bransby KM et al., arXiv:2608.30404 (2026, preprint). Full
  citation in [[Class schema options]].
- **ImageCAS**: Zeng A et al., Comput Med Imaging Graph 2023;109:102287,
  doi:10.1016/j.compmedimag.2023.102287 (arXiv:2211.01607v2, read in full).
- **BCS**: Owusu-Ansah M et al., STACOM 2026, arXiv:2607.28327.
- **Kim 2025**: Kim JN, Song Y, Wu H, et al. *Improving coronary artery
  segmentation with self-supervised learning and automated pericoronary adipose
  tissue segmentation: a multi-institutional study on coronary computed
  tomography angiography images.* J Med Imaging 2025;12(1):016002.
  doi:10.1117/1.JMI.12.1.016002 (PMC11831809).
- **TopCoW**: Yang K, Musio F, Ma Y, et al. *Benchmarking the CoW with the
  TopCoW Challenge: topology-aware anatomical segmentation of the Circle of
  Willis for CTA and MRA.* arXiv:2312.17670v4 (2025). Plus the challenge's
  evaluation code, `CoWBenchmark/TopCoW_Eval_Metrics` on GitHub (read the
  source of the Dice, HD95, Betti-0 and detection metrics).

Not accessed: the **ASOCA challenge** paper (Gharleghi R et al., Comput Med
Imaging Graph 2022;97:102049, doi:10.1016/j.compmedimag.2022.102049). It is
CC-BY, but ScienceDirect returned 403 to a non-browser fetch and the browser
extension was unavailable. Only the abstract was read; it contains no numbers.

## What is published

### Binary lumen, for calibration

| Label set / test set | Method | DSC | Other | Source |
|---|---|---|---|---|
| ImageCAS original masks, official 250-case test fold | ImageCAS baseline (coarse+patch ensemble) | 82.96 % | HD 27.22 mm, AHD 0.818 mm | ImageCAS Table 3/4 |
| ImageCAS original masks, 750/250 split, mean of 3 seeds | STU-Net-L (best baseline) | 0.818 | clDice 0.890, β₀ err 2.9 | BCS Table 2 |
| ImageCAS-X labels, 160-case test | nnU-Net | 89.8 ± 3.2 % | HD95 7.08 mm, Betti err 5.6 | ImageCAS-X |
| ImageCAS-X labels, 160-case test | CAS-Net (best) | 91.2 ± 2.8 % | HD95 2.99 mm, Betti err 1.9 | ImageCAS-X |
| ImageCAS-X labels, 160-case test | **inter-observer** | **92.8 ± 3.1 %** | HD95 2.46 mm, Betti err 0.4, clDice 95.4 % | ImageCAS-X |
| ImageCAS-X labels, 160-case test | ImageCAS method re-run | 87.9 ± 2.9 % | | ImageCAS-X |

The ImageCAS method scores ~5 points higher on the ImageCAS-X labels than on its
own. The re-annotation changed the ground truth enough that **the two label sets
have separate calibration targets.** Our binary run, on the original masks,
should be compared with 82.96 % and ~0.82. The ~0.856 inter-observer figure in
[[Training plan]] does not come from either paper I read; its source should be
traced or the figure dropped.

### Per-class human ceiling on our cohort

ImageCAS-X Table 1 (160 test cases, two analysts) gives per-segment
inter-observer DSC and clDice. The full table is in [[Class schema options]].
In summary: RCA 95.3, LAD 92.3, LM 91.9, LCx 84.8, R-PLA 83.6, D2 82.9,
R-PDA 82.6, Other 81.3, IM 80.6, D1 79.9, OM2 77.7, L-PDA 75.1, OM1 74.1,
L-PLA 70.9 (DSC %, all with SD 14–32 except the trunks).

Two further findings from the same paper (as stated in the text; which method
they refer to was not confirmed): "local DSC score increases with lumen diameter
(ρ = +0.89, p<0.001)"; "no significant differences between left, right and
co-dominance (p=0.40)"; and only a small correlation with image quality
(ρ = +0.13, p = 0.11).

### Per-class automatic results

- On ImageCAS: **none found for a voxel multiclass model.** ImageCAS-X's
  benchmark is binary; its tables report no per-segment numbers for automatic
  methods.
- Elsewhere, 3 classes (LAD, LCX, RCA): Kim 2025 reports Dice
  0.794 ± 0.059 for nnU-Net on an internal test set (26 CCTA, University
  Hospitals Cleveland) and 0.741 ± 0.081 on an external set (73 CCTA, Mackay
  Memorial Hospital), with an SSL-pretrained UNETR at 0.787 / 0.757. Small test
  sets, different scanners and labels; useful mainly for the size of the
  external drop (~5 points for nnU-Net).
- Closest multiclass vessel analogue, TopCoW (13 classes, brain CTA/MRA):
  "top teams had a median class-average Dice of around 90% for both CTA and
  MRA" on internal test sets, with detection F1 above 75 % for most test sets on
  the small communicating arteries. Human agreement there: "Many CoW component
  classes had Dice scores of around 90% or above, while R-Pcom, L-Pcom, Acom,
  and 3rd-A2 had slightly lower Dice at 76-89%" (measured on only 5 patients).

### Clinical usability

Nothing I read states a Dice, clDice or detection threshold for clinical use of
per-branch coronary labels. ImageCAS-X concludes that methods "do not yet
match human-level agreement" without a threshold. The BCS paper offers the one
downstream, decision-level measure: agreement of FFR-CT treat/no-treat
decisions between predicted and reference geometry (75–79 % for baselines,
85–88 % with Skeleton Recall or soft-BCS training on ImageCAS). The authors
note this measures "geometric, not clinical, fidelity."

## How to score absent classes: adopt TopCoW's rules

This is the most concrete, reusable finding. TopCoW's evaluation code
(`topcow24_eval/metrics/seg_metrics/`) does the following for each class in
each case:

- The class average runs over the **union of labels present in the ground
  truth or the prediction.** A class absent from both is skipped, not scored.
- If a class is present in only one of the two, **Dice = 0** and
  **HD95 = 90 mm** (a fixed upper bound, `HD95_UPPER_BOUND = 90`).
- **Detection**: TP if present in the ground truth with IoU ≥ 0.25
  (`IOU_THRESHOLD = 0.25`); FN if present with IoU < 0.25; FP if absent in the
  ground truth but predicted; **TN if absent in both**. F1 is computed over
  cases at aggregation.
- Betti-0 error per class: |b0(pred) − b0(gt)| with 26-connectivity; an empty
  mask has b0 = 0.

For us that resolves the IM problem (present in ~27 % of cases) and the
L-PDA/L-PLA problem cleanly. It also defines "branch detection rate" in a way
someone else has already published.

## Recommended thresholds

These are **my proposal**, anchored on the published human ceiling. They are
not taken from any paper. Test set: the sealed 160-case ImageCAS-X test set (see
[[Fold scheme and splits]]).

| Tier | Classes | Gate | Threshold |
|---|---|---|---|
| Binary sanity | merged lumen, ImageCAS original masks, official fold | DSC | ≥ 82.96 % (else the pipeline is broken) |
| Binary on ImageCAS-X | merged lumen | DSC | ≥ 89.8 % (reproduce their nnU-Net) |
| 1. Trunks | LM, LAD, LCx, RCA | per-class DSC and detection | DSC within 5 points of the human value (≥ 87, 87, 80, 90); detection 100 % for LAD/RCA, ≥ 97 % for LM/LCx |
| 2. Common branches | D1, D2, OM1, R-PDA, R-PLA | detection F1 (IoU ≥ 0.25) | ≥ 0.85; DSC reported, not gated |
| 3. Variably present | IM, OM2, Other | detection F1 including TN | ≥ 0.75; DSC reported |
| 4. Rare | L-PDA, L-PLA | none | report with bootstrap CI; n = 8 and 9 in the test set is too small to gate on |
| Topology | all | β₀ error per class, plus a connectedness measure (BCS) | report; no gate until the baseline sets a reference |

Why this shape:

- **Per class, not global.** Human DSC ranges from 70.9 to 95.3 across classes
  on this cohort. Any single threshold is either trivial for RCA or impossible
  for L-PLA.
- **Detection gates the branches, Dice does not.** For 3–4-voxel tubes, human
  Dice on branches has SDs of 20–30 points, so a Dice gate would pass or fail on
  noise. Detection at IoU ≥ 0.25 is what TopCoW used for its small classes.
- **The human value is a ceiling, not a target** (as [[Training plan]] already
  says). "Within 5 points" is a judgement call; tighten it once the baseline
  shows where it lands.

## What this implies for [[Training plan]]

- Close "Acceptance thresholds" with the tiered table above, marked as
  provisional until the multiclass baseline exists.
- In "Evaluation": adopt TopCoW's absent-class rules verbatim (union of present
  labels; one-sided absence → Dice 0, HD95 90 mm; detection IoU ≥ 0.25 with TN
  for absent–absent). Add β₀ per class and a bifurcation-connectedness measure.
- Replace "inter-observer agreement ≈ 0.856" with the sourced figures:
  92.8 % binary on ImageCAS-X labels, and the per-class table; trace or drop
  0.856.
- These proposals are not in [[Proposed changes]] (class schema only); they are for this topic's owning agent to take or discard.
