---
aliases: [ANNOTATION-PROTOCOL, Annotation protocol, Labelling protocol]
tags: [research, coronary, annotation, segqueue, literature]
status: handover
updated: 2026-09-19
---

# Annotation protocol evidence

> **Handover draft.** Written before the research was split between agents; this topic now belongs to another agent. Sources were opened and numbers checked as stated below, but the note has not been reviewed by the owner. Take, merge or discard it.

Open item in [[Training plan]]: annotation protocol details, meaning overlap-set
size, arbitration and gold cases, for per-branch coronary labelling by a team of
undergraduate annotators in the SegQueue Slicer app.

**Short answer.** The one published per-branch protocol on our cohort
(ImageCAS-X) used: machine pre-labels → trained non-physician analysts correct
**centerlines and segment names**, not voxels → a lead analyst reviews every
case → **20 % of cases re-annotated blind** by a second analyst for agreement.
Voxel labels were derived from the named centerline. That design suits an
undergraduate team and should be copied. Because ImageCAS-X labels exist for 800
of our cases, they also give us something no protocol normally has: a ready
**reference set to certify annotators against**.

## Sources actually read

- **ImageCAS-X**: Bransby KM et al., arXiv:2608.30404 (2026, preprint). Full
  citation in [[Class schema options]].
- **ImageCAS**: Zeng A et al., Comput Med Imaging Graph 2023;109:102287,
  doi:10.1016/j.compmedimag.2023.102287.
- **Hampe 2024**: J Med Imaging 2024;11(3):034001, doi:10.1117/1.JMI.11.3.034001.
- **TopCoW**: Yang K, Musio F, Ma Y, et al., arXiv:2312.17670v4 (2025).
- **Skandarani 2021**: Skandarani Y, Jodoin P-M, Lalande A. *Deep learning based
  cardiac MRI segmentation: do we need experts?* Algorithms 2021;14(7):212.
  doi:10.3390/a14070212 (read from arXiv:2107.11447).

Not accessed: Sim J, Wright CC. *The kappa statistic in reliability studies:
use, interpretation, and sample size requirements.* Phys Ther 2005;85(3):257–268,
doi:10.1093/ptj/85.3.257. It is paywalled at OUP and the browser/UofT proxy was
unavailable. Its sample-size tables would be the right basis for sizing the
overlap set for *categorical* agreement (branch presence, dominance). Retrieve
before finalising the overlap-set size.

## What published protocols did

| | ImageCAS (binary) | ImageCAS-X (per-branch) | Hampe 2024 (per-branch centerlines) | TopCoW (13 vessel classes) |
|---|---|---|---|---|
| Who | radiologists | "four trained analysts" + a lead analyst (qualifications not stated) | not stated | two annotators |
| Pre-labelling | not stated | automated centerlines ("a previously validated automated method"); lumen from a 3D U-Net trained on "100 randomly selected cMPR vessel volumes" manually annotated | CNN-based centerline extraction, then correction | not stated in what I read (VR annotation tool) |
| What humans edit | lumen masks | **centerlines + segment names**, then lumen correction | centerlines; "All centerline points … manually assigned an anatomical label" per AHA | voxel labels |
| Review | two independent + third radiologist on discrepancy, "determined by consensus" | "All cases were reviewed by the lead analyst and any errors were corrected" | not reported | not stated |
| Overlap / agreement set | not reported | 160 of 800 (20 %), "re-annotated by a different analyst, selected at random, … without review from the lead analyst and blinded to the first set of labels" | none reported | 5 patients (voxel Dice); variant classification also measured |
| Effort | not reported | 200 h centerline correction + 270 h lumen correction for 800 cases (≈ 15 + 20 min per case; my arithmetic) | not reported | not reported |

Agreement results:

- ImageCAS-X, per class: see the table in [[Class schema options]]. Trunks
  85–95 DSC, branches 71–84, with presence agreement of 87.5–100 % per class.
- TopCoW: voxel Dice "around 90% or above" for most classes, "76-89%" for the
  small communicating arteries (5 patients). For the categorical task of
  classifying anatomical variants: "Balanced accuracies between the raters were
  88% for AV and 78% for PV. Cohen's Kappa scores were 83% for AV and 72% for
  PV" (AV/PV = anterior/posterior variant). This is the nearest published
  analogue to agreeing on **coronary dominance** and **presence of IM**, which
  are also categorical judgements about variable anatomy.

## Evidence on non-expert annotators

Skandarani 2021 (cardiac cine-MRI, ACDC, 100 training / 50 test exams, plus
M&Ms for external test; three networks, 3 training runs each). Two non-experts:
"Non-Expert 1 is a technician in biotechnology who received a 30 minute
training"; "Non-Expert 2 is a computer scientist with 4 years of active research
in cardiac cine-MRI with several months of training … In addition, fine
delineation guidelines were provided." "No further quality control was done to
validate the non-expert annotations."

Networks trained on each person's labels, tested against expert labels on
ACDC (U-Net, CE+Dice):

| Structure | Expert labels | Non-Expert 1 (30 min) | Non-Expert 2 (months + guidelines) |
|---|---|---|---|
| LV cavity DSC | 0.92 ± 0.08 | 0.92 ± 0.08 | 0.93 ± 0.09 |
| Myocardium DSC | 0.88 ± 0.03 | 0.82 ± 0.03 | 0.87 ± 0.03 |
| RV cavity DSC | 0.90 ± 0.06 | 0.78 ± 0.11 | 0.86 ± 0.07 |

The lesson transfers, with care (different modality, one person per arm):
**brief training is enough for the easy structure and not for the hard ones;
guidelines and extended training close the gap.** For us the "easy structures"
are the trunks and the "hard" ones are the branches, where ImageCAS-X's trained
analysts already disagree by 10–20 DSC points.

## Recommendations

1. **Annotate centerlines, not voxels, for the per-branch step.** Copy the
   ImageCAS-X construction: the annotator names centerline segments; voxel
   labels come from nearest-centerline assignment. Why: it removes the least
   reproducible act (painting a boundary at a carina), it is faster
   (≈ 15 min per case for centerline correction in ImageCAS-X), and it keeps our
   labels compatible with theirs. SegQueue should present a named-centerline
   editor on top of the binary lumen.

2. **Certify each annotator against ImageCAS-X labels before they label
   anything new.** Give each new annotator ~10 ImageCAS-X *training-split* cases
   (never test-split) with the labels hidden, score them with the evaluation
   harness from [[Acceptance thresholds]], and release them to real work when
   their per-class agreement is within a stated margin of ImageCAS-X's own
   inter-observer values. Why: Skandarani shows that training depth, not
   credentials, decides quality on hard structures, and this measures depth
   directly. Caveat: ImageCAS-X labels are analyst labels, a reference and not
   ground truth.

3. **Written guideline = SCCT Appendix 1 definitions + ImageCAS-X policies.**
   The policy list is in [[Class schema options]] (dominance derived, not
   declared; main branch by direction and course; no branch < 1 mm distal;
   "Other" rule; IM only on a trifurcation).

4. **Overlap set: 20 % of whatever we annotate, blind, randomly paired, not
   reviewed before scoring.** That is the ImageCAS-X design. Measure agreement
   on the *raw* double annotations, then send both through review. Size it so
   each variably-present class appears enough times to be estimated. For IM, at
   ~27 % prevalence in ImageCAS-X's test set, 100 overlap cases give ~27
   occurrences. For L-PDA/L-PLA (~5 %), no feasible overlap set gives a stable
   estimate, so report them pooled. Confirm the categorical part (presence,
   dominance) against Sim & Wright's tables once retrieved.

5. **Arbitration: an automatic disagreement flag, then one senior reviewer.**
   Flag a case when the two annotators disagree on dominance, on presence of any
   class, or when any trunk's DSC falls below its human value by more than
   ~10 points. Flagged cases go to a single senior reviewer (a clinician if one
   is available; the ImageCAS precedent is a third radiologist) whose decision
   is final. Un-flagged overlap cases take either annotation. Why: ImageCAS-X
   reviewed *everything* through one lead analyst, which does not scale to a
   rotating undergraduate team. The flag rule concentrates expert time where
   agreement actually failed.

6. **Where the team's effort goes, if ImageCAS-X imports cleanly:**
   (a) QA of the imported labels (spot-check 20, then targeted review of cases
   the baseline model disagrees with); (b) an independent protocol-matched
   overlap set to measure *our* team's agreement; (c) optionally a subset of the
   200 image-quality-excluded scans as a separate hard test set (see
   [[Fold scheme and splits]]).

## Still open

- Overlap-set size for categorical agreement: needs Sim & Wright (paywalled).
- Whether a clinician is available as senior reviewer; the protocol degrades to
  "lead annotator" otherwise, as in ImageCAS-X.
- ImageCAS-X analysts' qualifications and training are not stated in the paper.

## What this implies for [[Training plan]]

- Close "Annotation protocol details" with: centerline-first labelling with
  nearest-centerline voxel assignment; annotator certification against
  ImageCAS-X training-split labels; 20 % blind overlap; automatic disagreement
  flag → single senior reviewer.
- The per-branch inter-rater ceiling that §Evaluation says will come "from the
  annotation overlap set" already exists for this cohort (ImageCAS-X Table 1);
  our own overlap set then measures *our* team against it.
- These proposals are not in [[Proposed changes]] (class schema only); they are for this topic's owning agent to take or discard.
