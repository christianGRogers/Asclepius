---
aliases: [CLAIM checklist, TRIPOD+AI, Reporting guidelines, Publication checklists]
tags: [research, evaluation, publication, coronary, literature]
status: evidence-collected
updated: 2026-09-19
---

# CLAIM and TRIPOD+AI checklists for a coronary segmentation manuscript

What two consensus publication checklists — CLAIM (radiology/medical-imaging
AI) and TRIPOD+AI (clinical prediction models generally) — ask a validation
write-up to disclose, read against what [[Training plan]]'s evaluation
section and `src/segtrain/evaluate.py` currently produce. Both checklists
target classification/prediction papers primarily, not segmentation
benchmarks specifically, so this note keeps only the parts that transfer.

**Short answer.** Both checklists converge on four disclosures this project
does not yet commit to making: (1) an explicit, sourced definition of the
reference standard and how its inter-/intra-rater variability was measured —
[[Class schema options]] and the annotation-protocol agent's work cover the
"how," but [[Training plan]] does not yet say this will be written up; (2)
uncertainty on every performance number (CI or SD), which [[Deciding whether
a paired experiment found a real difference]] already argues for on
statistical grounds and these checklists argue for independently on
disclosure grounds; (3) a stated, justified reason when evaluation data comes
from the same source as training data, which is exactly our situation for the
binary calibration run (see [[Fold schemes and split ratios]]) and needs a
sentence, not a fix; (4) worked failure examples, which nothing in the
current evaluation pipeline produces automatically.

## Sources actually read

- **CLAIM** — Mongan J, Moy L, Kahn CE Jr. *Checklist for Artificial
  Intelligence in Medical Imaging (CLAIM): A Guide for Authors and
  Reviewers.* Radiology: Artificial Intelligence 2020;2(2):e200029.
  doi:10.1148/ryai.2020200029. Read in full on PMC (PMC8017414).
- **TRIPOD+AI** — Collins GS, Moons KGM, Dhiman P, et al. *TRIPOD+AI
  statement: updated guidance for reporting clinical prediction models that
  use regression or machine learning methods.* BMJ 2024;385:e078378.
  doi:10.1136/bmj-2023-078378. Read in full on PMC (PMC11019967).

Both are general checklists (CLAIM: any medical-imaging AI task; TRIPOD+AI:
any clinical prediction model, "regression or machine learning"). Neither is
segmentation-specific, and TRIPOD+AI's fit is looser still — it is written for
models that predict an outcome (a diagnosis, a risk), and a voxel segmentation
is only a "prediction model" in the loosest sense. What follows keeps the
items that transfer; items about outcome time-horizons, calibration plots and
risk-score thresholds (a large fraction of TRIPOD+AI) do not apply to a
segmentation task and are left out.

## CLAIM, item by item, mapped onto what exists here today

- **Item 14** — "detailed, specific definitions of the ground truth
  annotations." Written in [[Class schema options]] (ImageCAS-X policies)
  once adopted; not yet folded into [[Training plan]] itself.
- **Item 16** — number and qualifications of annotators, instructions/training
  given. Belongs to the annotation-protocol agent; flagged in `Handoffs.md`.
- **Item 18** — "methods to measure inter- and intrarater variability, and any
  steps taken to reduce or mitigate." Partially planned (the annotation
  overlap set, see [[NSD tolerance selection for sub-millimetre coronary
  vessels]]) but not yet a written commitment in the plan.
- **Items 20–21** — training/validation/test partitions disjoint "at the
  patient level or higher." Satisfied by design: [[Fold schemes and split
  ratios]] already reasons at the patient/case level, and both ImageCAS's own
  IDs and ImageCAS-X's reuse of them make patient-level disjointness a
  checkable fact rather than an assumption.
- **Item 28** — metrics used, and comparison "to previously published
  models." [[Which metrics to report for thin tubular multiclass
  segmentation]] and [[State of the art on ImageCAS]] already do this inside
  the vault; it needs to reach the plan or manuscript itself.
- **Item 29** — "uncertainty of the performance metrics' values, such as with
  standard deviation and/or confidence intervals." **Not currently produced**:
  `evaluate.summarize()` prints point means only. See [[Proposed changes]] E7.
- **Item 32** — "When [evaluation] data are not drawn from a different data
  source than the training data, note and justify this limitation."
  **Directly applicable and currently unmet.** The binary calibration run's
  ImageCAS official-split test set is drawn from the *same* single-centre,
  single-scanner cohort as training (see [[Research context]]); CLAIM would
  require this named as a limitation, not silently presented as if it were an
  independent test.
- **Item 37** — "presenting examples of incorrectly classified cases to help
  readers better understand the strengths and limitations." **Not currently
  produced.** Nothing in `src/segtrain/evaluate.py` selects or exports
  worst-case examples.

## What TRIPOD+AI adds beyond CLAIM

TRIPOD+AI targets a broader prediction-model audience, and several of its
additions are new relative to the 2015 TRIPOD checklist for reasons that
matter to a segmentation project specifically:

- **Items 16 / 20c — distributional shift between development and evaluation
  data.** TRIPOD+AI asks authors to "identify any differences between the
  development and evaluation data in healthcare setting, eligibility
  criteria, outcome, and predictors" and to "show a comparison … of the
  distribution of important predictors." This is CLAIM item 32's concern
  again, arrived at from a different checklist, and it is exactly what
  [[External validation and cross-dataset generalisation for coronary
  segmentation]] argues for doing with ASOCA: a stated, quantified comparison
  of the two cohorts (scanner, acquisition protocol), not just a second Dice
  number.
- **Items 8a–8c — the reference standard, its rationale, blinding, and
  assessor qualifications.** Close to CLAIM 14/16/18 but explicit about
  **blinding** ("report any actions to blind assessment of the outcome") —
  something neither the vault's current annotation notes nor [[Training
  plan]] addresses either way for our own annotators. Worth a line: do
  annotators see the binary presegmentation before drawing per-branch labels
  (almost certainly yes, since [[Training plan]] §3 describes the binary
  model's predictions as presegmentation seeds)? If so, that is a deliberate,
  reasoned departure from blinding, not an oversight — but it should be
  written down, because a reviewer applying TRIPOD+AI would ask.
- **Item 13 — methods for handling class imbalance**, listed as new relative
  to 2015 specifically because AI/ML methods need it where regression
  checklists did not. This is precisely [[Training plan]] §5's
  "class-balanced, vessel-anchored patch sampling" experiment — already
  planned, just not yet tied to a disclosure requirement that would make its
  omission conspicuous if skipped.
- **Item 22 — full model details "to allow predictions in new individuals"**
  (formula, code, API). Satisfied by design: this is a code-and-vault
  project, and `configs/tasks/*.yaml` plus the plan's documented decisions are
  already most of that artifact, provided they are kept current.
- **Item 23a — subgroup performance with confidence intervals**, naming
  sociodemographic subgroups as the default example but not limited to them.
  For us the natural subgroup axis is anatomical rather than demographic:
  coronary dominance (right/left/co-dominant) and disease status, which
  [[Fold schemes and split ratios]] already recommends stratifying folds on.
  TRIPOD+AI gives a disclosure-standard reason to report per-dominance
  performance, not only to stratify sampling by it.
- **Item 18 (open science) — protocol registration, data/code sharing.** This
  vault, kept alongside the code, is most of this requirement already; the
  gap is a pre-registered analysis plan for the paired experiments (see
  [[Deciding whether a paired experiment found a real difference]]), which
  that note argues for on purely statistical grounds independently (decide
  the test before seeing the result).

## What neither checklist covers, because neither is built for segmentation

Both checklists are silent on the metric-selection questions [[Which metrics
to report for thin tubular multiclass segmentation]] answers from Metrics
Reloaded instead (Dice vs clDice vs NSD, aggregation level, NaN policy) and on
topology (Betti error). Worth stating plainly in any manuscript: CLAIM and
TRIPOD+AI are the *structural* checklist (what sections and disclosures a
paper needs), Metrics Reloaded is the *metric-selection* standard (which
numbers to compute and why). A segmentation paper here needs both; neither
substitutes for the other.

## What this implies for [[Training plan]]

1. **Name the CLAIM item-32 / TRIPOD+AI item-16 limitation explicitly**: the
   binary calibration run's test set is drawn from the same single-centre
   cohort as training. Already implicit in [[Fold schemes and split ratios]]
   and [[Research context]] but should be a named limitation in the plan's
   evaluation section, not left to be inferred.
2. **Add confidence intervals / SD to every reported metric** — already argued
   for statistically in [[Deciding whether a paired experiment found a real
   difference]]; now also a named item in both checklists (CLAIM 29,
   TRIPOD+AI 23a).
3. **Add a worst-case-examples step to the evaluation pipeline** (CLAIM 37) —
   currently nothing in `src/segtrain/evaluate.py` selects or exports the
   worst-scoring cases per class; `summarize()`'s "weakest structures" table
   is close but names structures, not specific case IDs to inspect.
4. **Write down the annotation-blinding decision** (TRIPOD+AI 8c) — flag to
   the annotation-protocol agent in `Handoffs.md`, since the presegmentation
   workflow is their design, but disclosing it is this topic's concern.
5. **Report per-dominance and per-disease-status subgroup performance**
   (TRIPOD+AI 23a), using the same stratification [[Fold schemes and split
   ratios]] already recommends for fold construction — one dataset split
   serving two purposes.

See [[Proposed changes]], [[Deciding whether a paired experiment found a real
difference]] and [[External validation and cross-dataset generalisation for
coronary segmentation]].
