---
aliases: [Non-expert annotators, Undergraduate annotators, Crowd annotation]
tags: [research, annotation, non-experts, quality-control, segqueue, evidence]
status: draft
updated: 2026-09-19
---

# Can non-experts label vessels as well as experts

The project's labelling workforce is a class of undergraduates
(`docs/SEGQUEUE.md`). The question is not "are they as good as a radiologist"
but **what makes a non-expert's labels good enough, and how do we see when they
are not**.

## The short answer

Three independent lines of evidence say the same thing: **training depth and
instruction quality decide non-expert label quality, not credentials — and the
failure mode is not a slightly worse boundary, it is a small number of
catastrophically wrong objects.** A protocol that detects and removes the
catastrophic cases gets most of the way to expert quality; one that only reports
mean Dice will not see them.

## Evidence

### 1. Instructions with pictures, not more words

**Rädsch T, Reinke A, Weru V, Tizabi MD, Schreck N, Kavur AE, Pekdemir B, Roß T,
Kopp-Schneider A, Maier-Hein L. *Labelling instructions matter in biomedical
image analysis*. Nature Machine Intelligence 2023;5:273–283.
doi:10.1038/s42256-023-00625-5.** Read in full via the author preprint
(arXiv:2207.09899); the peer-reviewed version is the citation of record.

14,040 images annotated by 156 annotators from four professional annotation
companies and 708 Amazon Mechanical Turk crowdworkers, under three instruction
conditions: minimal text, extended text, extended text + exemplary pictures.

- **Extended text alone did nothing.** vs minimal text: severe annotation
  errors median +0.4 % (max +14.8 %, min −31.7 %), no impact on median DSC, IQR
  median +1.8 %. "no statistically significant difference for the extended text
  labeling instructions compared to minimal text".
- **Adding exemplary pictures worked, for every provider.** vs extended text:
  severe errors median **−33.9 %** (max −13.6 %, min −52.3 %), median DSC
  **+2.2 %**, IQR median **−58.3 %**. Odds of a severe error with
  text+pictures were **0.37× (CI 0.28–0.50)** those with minimal text.
- **The gain is entirely in not making catastrophic errors.** They define a
  severe annotation error as "an annotation with a metric score equal to zero",
  and report that once an object was correctly identified there was "no
  significant difference in the DSC score". The mechanism is: pictures stop you
  labelling the wrong thing; they do not make your boundary tidier.
- **Professionals beat the crowd by a wide margin.** With minimal text,
  companies median DSC **0.93** vs MTurk **0.67**; severe errors 307 vs 549;
  IQR 0.36 vs 0.67. Odds of a severe error for a professional were **0.09×
  (CI 0.06–0.12)** those of a crowdworker.
- Context: "76% of the recent MICCAI competitions do not report any labeling
  instructions", and in their survey of 298 professional annotators, poor
  labelling instructions were the **primary** self-reported cause of problems,
  ahead of concentration issues (50 %) and poor input data (45 %).

Caveat the authors state: one dataset (endoscopic instruments), so the absolute
numbers do not transfer to CCTA. The *direction* — pictures over prose, severe
errors as the target — is what transfers.

### 2. A vessel dataset built by juniors with a two-tier review

**Jin K, Huang X, Zhou J, Li Y, Yan Y, Sun Y, Zhang Q, Wang Y, Ye J. *FIVES: A
Fundus Image Dataset for Artificial Intelligence based Vessel Segmentation*.
Scientific Data 2022;9:475. doi:10.1038/s41597-022-01564-3.** Read via PMC
(PMC9352679).

800 fundus images, pixelwise vessel labels. Their workforce shape is almost
exactly ours: **3 ophthalmic practitioners as senior annotators and 24 medical
staff "knowledgeable regarding retinal anatomy" as junior annotators.**

- **Onboarding is a pass/fail test, not a tutorial.** "A detailed annotation
  guideline was made by 3 ophthalmic practitioners… For each annotator, having
  learned the annotation guidelines, 5 test images… were assigned and retrieved
  after their initial annotation." Annotators who failed did not proceed.
- **Every image annotated twice, fused by intersection**: "Each image was
  annotated by 2 annotators. The pixels annotated by the 2 annotators in common
  were included as the final ground truth." Then senior review corrected errors,
  with internal discussion for genuine disagreements.
- **Agreement numbers (their own measurements):** intra-annotator mean Dice
  **0.9679** (range 0.9602–0.9810) on 40 re-annotated images; junior–junior
  inter-annotator **0.9241** (0.8792–0.9823); senior–junior **0.9608**
  (0.9564–0.9676).
- **Cost:** "Annotating one image would take approximately 3–5 hours."
- They explicitly rejected model pre-annotation because the best published
  algorithm reached only ~0.82 Dice, which they judged too weak to seed ground
  truth. Our situation differs (see
  [[Seeding annotation with model predictions and label efficiency]]), but the reasoning — seed
  quality sets the bias floor — is the same one we have to answer.

Two things to take: the **intra > senior–junior > junior–junior ordering**
(0.968 > 0.961 > 0.924) is the pattern to expect in our own QA numbers, and
**intersection fusion** is a deliberate choice to trade recall for precision
that we should decide consciously rather than by accident (see
[[Fusing multiple annotations and learning from noisy labels]]).

### 3. Training depth beats credentials

**Skandarani Y, Jodoin P-M, Lalande A. *Deep learning based cardiac MRI
segmentation: do we need experts?* Algorithms 2021;14(7):212.
doi:10.3390/a14070212.** Read in full via arXiv:2107.11447.

Two non-experts each labelled 1902 cardiac cine-MR images (ACDC). "The
Non-Expert 1 is a technician in biotechnology who received a 30 minute training
by a medical expert"; Non-Expert 2 is "a computer scientist with 4 years of
active research in cardiac cine-MRI" whose "training span several months" and
who was given "fine delineation guidelines". Three networks were trained on each
annotator's labels and tested against expert labels.

- On the **LV cavity** (the easy structure) the non-expert-trained networks were
  "statistically indistinguishable" from the expert-trained ones.
- On the **myocardium and RV** (the hard structures) the briefly-trained
  Non-Expert 1 lost ground while the extensively-trained Non-Expert 2 stayed
  "very close (if not better)". The paper states "there is a Dice score drop of
  12% on the myocardium" for Non-Expert 1 with CE+Dice. From the myocardium
  table (U-Net, ACDC test): expert 0.88 ± 0.03, Non-Expert 1 0.82 ± 0.03,
  Non-Expert 2 0.87 ± 0.03. *The published table extracts as interleaved columns
  from the PDF; I read these three values carefully but they should be checked
  against the typeset table before being quoted elsewhere.*
- Errors concentrated **at the extremes of the structure** — "the performance
  gap is more pronounced on the apex". Our analogue is the distal third of every
  branch, which is exactly where ImageCAS-X's analysts also disagree most.
- Conclusion verbatim: "training a deep neural network… with data labeled by a
  well-trained non-expert achieves comparable performance than on expert data."

Limits: one person per training level, so "training depth" and "this individual"
are confounded; different modality; no quality control was applied to the
non-expert labels, which is the opposite of our design.

### 4. Trained non-physicians outperformed the radiologist labels on our own cohort

ImageCAS-X (arXiv:2608.30404, preprint; see
[[How well two annotators agree on per-branch coronary labels]]) was annotated by
"four trained analysts" — credentials not stated, but not described as
physicians — with a lead analyst reviewing every case. The original ImageCAS
masks were made by two radiologists with a third adjudicating discrepancies.
Measured against the ImageCAS-X labels, the **radiologist-made ImageCAS masks
score DSC 41.8, HD95 16.15 mm, Betti error 7.0**, which the authors attribute to
inclusion of atherosclerotic plaque, false-positive pulmonary vessels and
false-positive coronary veins.

This is not proof that non-physicians beat radiologists: the comparison is
against ImageCAS-X's own labels (so it is not neutral), the protocols differ,
and the two teams may have been answering different questions about what "lumen"
means. What it does show, and what matters for us, is that **a careful protocol
with machine seeding and 100 % lead review produced labels that differ
enormously from an expert-made dataset built without one.** Protocol beats
credential.

## Error types to expect, and how to detect them

From the above, plus the ImageCAS-X per-segment spread:

| Error type | Signature | What catches it |
|---|---|---|
| Wrong vessel named (LCx labelled OM1, D1 vs D2 swap) | per-class DSC ≈ 0 while the merged lumen is fine | per-class duplicate/gold scoring, *not* mean Dice |
| Branch omitted entirely | presence disagreement; recall collapse on one class | presence agreement per class |
| Branch invented (labelled a vein or a pulmonary vessel) | foreground outside the binary seed; extra connected component | component count vs expected; seed-mask containment |
| Boundary sloppiness | small uniform DSC deficit, no zeros | mean per-class DSC vs the human ceiling |
| Ownership of the bifurcation/carina | localised disagreement at branch points only | distance metrics restricted to a radius around junctions (unbuilt) |
| Drift over time / fatigue | per-annotator score trend | time-ordered QA scores per annotator |
| Silent drop-out mid-case | lease expiry | already handled: `src/segqueue/policy.py` lease + stale heartbeat |

**The single most important change this evidence implies for SegQueue:** today's
gold and duplicate scoring flags on **mean Dice < 0.70** across structures
(`src/segqueue/policy.py`, `gold_dice_flag`, `duplicate_dice_flag`, and
`server/girder_segqueue/scoring.py`, which returns `mean_dice`). A mean over
classes is precisely the statistic that hides a severe error: get every trunk
right and one small branch catastrophically wrong, and the mean barely moves.
Rädsch's result says the severe-error count is the quantity that separates good
annotation work from bad. See [[Proposed changes]].

## What this implies for [[Training plan]]

- Undergraduate annotators are viable for this task **conditional on** a written
  guideline that is mostly annotated pictures, a pass/fail onboarding test, and
  QA that looks for catastrophic per-class errors rather than mean Dice.
- Budget the guideline as a deliverable in its own right: exemplary images per
  class, including rare and ambiguous cases, are the intervention with the
  largest measured effect (odds of a severe error 0.37×). Prose alone is
  measurably worthless.
- Expect the hard cases to be the distal branches and the ostia/bifurcations,
  and expect a trained annotator's *own* repeat to be better than their
  agreement with a colleague — so a disagreement is evidence about the
  guideline, not only about the annotator.
- The annotation effort figures worth planning against are ImageCAS-X's
  ~15 min/case centerline correction + ~20 min/case lumen correction *with*
  machine seeding, against FIVES's 3–5 h/image *without* it. Seeding is the
  difference between a term's work and an impossible one.
