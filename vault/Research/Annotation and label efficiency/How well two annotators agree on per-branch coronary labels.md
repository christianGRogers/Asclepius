---
aliases: [Inter-rater agreement per-branch, Annotation ceiling]
tags: [research, annotation, inter-rater, coronary, segqueue, evidence]
status: draft
updated: 2026-09-19
---

# How well two annotators agree on per-branch coronary labels

The question: what is the realistic ceiling for agreement between two people
labelling the *same* coronary tree per branch, and therefore what a multiclass
model can be asked to reach. [[Training plan]] §Evaluation currently says
"inter-observer agreement ≈ 0.856 — the ceiling, not a target" and expects the
per-branch ceiling to come from our own overlap set. The per-branch number
already exists, measured on 160 of our own 1000 cases.

## The one directly applicable measurement

**Bransby KM, Øksnebjerg E, Kjær K, Kirkeby J, El Youssef Y, Jiménez A,
Pedersson PR, de Knegt MC, Kofoed KF, Paulsen RR. *ImageCAS-X: a dataset and
benchmark for coronary artery segmentation and centerline extraction in coronary
CT angiography*. arXiv:2608.30404 (August 2026). Preprint — not peer reviewed.**
Read in full as HTML on arXiv; data on Zenodo record 21887809, CC BY 4.0.

They re-annotated their whole 160-case test set with a second analyst and report
per-segment agreement. Same scanner cohort, same 1000 ImageCAS volumes, same
18-segment vocabulary. This is as close to our task as published evidence gets.

Inter-observer agreement, ImageCAS-X test set (n = 160 scans; `nn` = scans in
which the segment was present; "Agreement" = percentage of scans in which both
analysts either annotated the segment or both omitted it):

| Segment | nn | Agreement % | DSC | clDice | ASSD (mm) | HD95 (mm) |
|---|---|---|---|---|---|---|
| LM | 155 | 96.9 | 91.9 ± 13.7 | 95.6 ± 17.6 | 0.40 ± 1.52 | 1.41 ± 5.58 |
| LAD | 160 | 100.0 | 92.3 ± 6.7 | 96.4 ± 7.9 | 0.48 ± 1.29 | 3.39 ± 9.07 |
| LCx | 159 | 99.4 | 84.8 ± 19.8 | 87.3 ± 23.0 | 1.85 ± 3.86 | 8.59 ± 15.30 |
| RCA | 160 | 100.0 | 95.3 ± 5.0 | 98.2 ± 6.0 | 0.32 ± 1.13 | 2.18 ± 6.81 |
| D1 | 155 | 96.9 | 79.9 ± 28.7 | 85.0 ± 30.2 | 2.53 ± 6.80 | 6.66 ± 12.30 |
| D2 | 91 | 89.4 | 82.9 ± 24.3 | 88.1 ± 25.3 | 1.36 ± 3.97 | 3.96 ± 6.92 |
| OM1 | 132 | 94.4 | 74.1 ± 32.3 | 79.8 ± 34.2 | 3.47 ± 8.27 | 8.93 ± 15.70 |
| OM2 | 46 | 87.5 | 77.7 ± 29.1 | 83.7 ± 30.6 | 2.33 ± 6.04 | 5.38 ± 9.16 |
| IM | 43 | 89.4 | 80.6 ± 24.5 | 89.2 ± 25.2 | 1.28 ± 3.98 | 5.32 ± 12.70 |
| R-PDA | 150 | 98.8 | 82.6 ± 21.9 | 88.4 ± 22.3 | 1.35 ± 4.52 | 5.00 ± 9.10 |
| R-PLA | 147 | 96.2 | 83.6 ± 18.6 | 89.4 ± 18.4 | 1.02 ± 2.35 | 5.92 ± 9.27 |
| L-PDA | 8 | 100.0 | 75.1 ± 29.0 | 81.6 ± 31.8 | 2.82 ± 6.76 | 8.72 ± 18.10 |
| L-PLA | 9 | 96.9 | 70.9 ± 27.2 | 77.7 ± 30.3 | 2.50 ± 5.02 | 8.32 ± 12.50 |
| Other | 14 | 88.8 | 81.3 ± 17.0 | 86.7 ± 16.2 | 2.10 ± 3.65 | 10.14 ± 15.80 |
| **All segments merged** | 160 | 95.3 | **92.8 ± 3.1** | 95.4 ± 3.6 | 0.53 ± 0.33 | 2.46 ± 3.62 |

Four things to take from this table.

1. **The ceiling is not one number, it is a per-class curve.** Merged (i.e. the
   binary lumen task) two analysts agree at DSC 92.8. Per branch the same two
   people agree at 95 on the RCA and 71–80 on OM1, D1, L-PLA. A multiclass model
   that scores 75 on OM1 is at the human ceiling; the same score on the RCA is a
   failure. Any single acceptance threshold across classes encodes a
   misunderstanding.
2. **The standard deviations are larger than the gaps.** OM1 is 74.1 ± 32.3:
   that distribution is bimodal in practice — most cases near-perfect, a tail of
   cases where the two analysts named a different vessel OM1 and the DSC
   collapses toward 0. Reporting a mean per class hides the failure mode our QA
   actually needs to catch. Report the *fraction of cases below X* alongside the
   mean.
3. **Presence disagreement is separate from boundary disagreement.** Agreement
   on whether a segment exists at all runs 87.5–100 %, worst for D2 (89.4),
   OM2 (87.5), IM (89.4) and "Other" (88.8) — exactly the variably-present
   branches. This is a categorical error mode that Dice cannot express, and it
   needs its own measurement (see [[Sizing the overlap set and arbitrating disagreements]]).
4. **Rare classes cannot be estimated.** L-PDA has nn = 8 and L-PLA nn = 9 in a
   160-case overlap set. Their DSCs (75.1, 70.9) are single-digit-sample
   numbers. No overlap set we can afford will stabilise them.

## What the number is actually measuring, and why it is an optimistic bound

The ImageCAS-X workflow was: automated centerline extraction → analyst trims,
removes spurious segments and draws missing vessels → a 3D U-Net (trained on 100
manually annotated cMPR vessel volumes) predicts the lumen → analyst corrects it
slice by slice → lead analyst reviews every case. The inter-observer study says:
"each test case was additionally re-annotated by a different analyst, selected at
random, following the same protocol without review from the lead analyst and
blinded to the first set of labels."

"Following the same protocol" means the second analyst also started from the
same machine pre-labels. The paper does not say this explicitly — **this is my
inference, not a stated fact** — but it follows from "the same protocol", and it
matters: two annotators who both edit the same automatic seed share its errors,
so their measured agreement is an upper bound on what independent from-scratch
annotation would give. It is nonetheless the right bound for us, because
[[Training plan]] §3 has our binary model seeding presegmentations, so our
annotators will share a seed in exactly the same way.

Two further caveats:

- Agreement was measured on the *uncorrected* second annotation vs the
  lead-reviewed first annotation, so part of the gap is the review step, not raw
  human disagreement. (ImageCAS-X states the second set had no lead review; it
  does not state whether the first set in the comparison was pre- or
  post-review. **Unverified.**)
- The analysts' credentials and training are **not stated anywhere in the
  paper**. "Four trained analysts" is all we know. So this is not a
  radiologist-vs-radiologist ceiling; it is a trained-non-physician ceiling,
  which is the right comparison for an undergraduate team but should not be
  described as expert agreement.

## The binary-lumen comparison points

- **Merged lumen, same cohort:** DSC 92.8 ± 3.1 between two ImageCAS-X analysts.
- **Centerlines, CAT08/Rotterdam:** Schaap M, Metz CT, van Walsum T, et al.
  *Standardized evaluation methodology and reference database for evaluating
  coronary artery centerline extraction algorithms.* Med Image Anal
  2009;13(5):701–714. doi:10.1016/j.media.2009.06.003 (read the NIH author
  manuscript PDF in full). Three trained observers independently annotated 4
  vessels in each of 32 CTA datasets. They report no single agreement scalar;
  instead the challenge *normalises* every method score so that **50 points =
  observer performance**, which is the cleanest published statement of the idea
  that human agreement is the unit of measurement. Accuracy: most methods that
  tracked the vessel correctly were within one voxel (AI < 0.4 mm); the best
  method reached 0.23 mm, and its overlap score of 84 (> 50) means it exceeded
  inter-observer agreement on overlap while still being below it on accuracy
  (score 47.9).
- **The plan's 0.856 figure is currently unsourced.** It is not in the ImageCAS
  paper (Zeng A, et al. Comput Med Imaging Graph 2023;109:102287,
  doi:10.1016/j.compmedimag.2023.102287 — I read the arXiv version 2211.01607
  in full and searched it; the only agreement-shaped statements are the
  annotation procedure, below, and the 82.96 % benchmark Dice). Treat 0.856 as
  **unverified** until its source is found, and prefer ImageCAS-X's 92.8 for the
  merged task, which was measured on this exact cohort.

For context on how the ImageCAS binary masks themselves were made (Zeng 2023,
verbatim): "the left and right coronary arteries in each image are independently
labeled by two radiologists, and their results are cross-validated. In case of
discrepancy, a third radiologist will perform the annotation and the final
result is determined by consensus." No agreement statistic, no per-case time,
and no radiologist experience level is reported. Notably the *labelling* was
done "according to the AHA naming convention (17 paragraphs)" — the per-segment
identity existed at annotation time and was not released.

## Intra-rater agreement

**No usable published measurement found for per-branch coronary labelling.**
ImageCAS-X reports no intra-observer study; CAT08 reports none; ImageCAS reports
none. This is a real gap: without it we cannot separate "this annotator is
inconsistent" from "these two annotators disagree", which is the difference
between retraining one person and rewriting the guideline. We can measure it
ourselves almost for free — see the repeat-assignment proposal in
[[Proposed changes]].

## What this implies for [[Training plan]]

- Replace "inter-observer agreement ≈ 0.856" with the ImageCAS-X numbers, which
  were measured on this cohort: **92.8 DSC for the merged lumen**, and a
  per-class ceiling of **~95 (RCA), ~92 (LAD), ~85 (LCx), 74–84 (named side
  branches), ~71–81 (left-dominant PDA/PLA, tiny n)**. Mark them as a preprint.
- Acceptance thresholds must be **per class**, pegged to this curve, not a
  single number. (Thresholds themselves belong to the metrics agent; this note
  supplies the ceiling they should be pegged to.)
- Our own overlap set is still worth running, but its job changes: not to
  discover the ceiling — that exists — but to show our undergraduates reach it.
  That is a calibration target we can state in advance.
- Report **presence/absence agreement per class** as a first-class metric
  alongside Dice, because 9–12 % of the disagreement on variably-present
  branches is categorical.
- The evaluation of a multiclass model should quote, per class, the fraction of
  cases below the human agreement value, not only the mean.
