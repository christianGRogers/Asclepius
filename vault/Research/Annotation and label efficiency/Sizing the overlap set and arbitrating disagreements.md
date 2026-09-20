---
aliases: [Overlap set sizing, Arbitration procedure, Gold case rate, Duplicate rate]
tags: [research, annotation, quality-control, segqueue, literature]
status: draft
updated: 2026-09-19
---

# Sizing the overlap set and arbitrating disagreements

[[Training plan]]'s open item "annotation protocol details: overlap-set size,
arbitration, gold cases" against what SegQueue already implements, and against
the published evidence for how big an overlap set needs to be and what happens
when two annotators disagree. Companion notes: [[How well two annotators agree
on per-branch coronary labels]] (the target the overlap set measures against),
[[Fusing multiple annotations and learning from noisy labels]], [[Detecting a
drifting or bad annotator]].

## What SegQueue already does

Read directly from `src/segqueue/policy.py` (not edited; this folder does not
own that code, cited here as the current implementation to evaluate against):

- **5-case training gate**: every annotator's first 5 submissions are reviewed
  by a human (`training_gate_size`, referenced in the module docstring).
- **5% gold cases, 5% blind duplicates** of served work (`gold_rate = 0.05`,
  `duplicate_rate = 0.05`), with every annotator's first case forced to be
  gold (`gold_first_case = True`).
- **20% sampled review, dropping to 10%** once an annotator is "trusted"
  (`base_review_rate = 0.20`, `trusted_review_rate = 0.10`), rising back to
  full review for a fixed run of submissions after any rejection.
- **Automatic flag at mean Dice < 0.70** against the gold reference or the
  duplicate partner (`gold_dice_flag = 0.70`, `duplicate_dice_flag = 0.70`),
  which forces human review regardless of the sampling roll.

This is a sensible, already-implemented skeleton. What follows is evidence for
whether the specific numbers (5%, 5%, 20%/10%, 0.70) are well-chosen, and what
the arbitration step after a flagged disagreement should look like — which the
code does not yet decide.

## The one published per-branch coronary protocol's numbers

Already established in `Handover/Annotation protocol evidence.md` (a draft by
another agent — read as a starting point per instructions, not edited, and
checked against the primary source below): **ImageCAS-X re-annotated 160 of
800 cases (20%) blind**, by a different analyst, without lead review, entirely
for the purpose of measuring agreement — not as an ongoing per-batch QA
mechanism the way SegQueue's duplicate rate is. That is a one-time study
overlap fraction, not a sustained-operation QA rate, and the two numbers are
not directly comparable: ImageCAS-X spent 20% of *total* effort once, to
characterise their whole workforce's ceiling; SegQueue spends 5% of *every*
case, continuously, to catch drift in an ongoing team. The right comparison
for SegQueue's `duplicate_rate` is not "did ImageCAS-X use 5% or 20%" but
"what rate keeps the *cumulative* number of paired cases large enough to
estimate agreement per class" — worked below.

## Sizing an overlap set against class prevalence, not against a single global rate

The instructive number is how many blind-duplicate pairs are needed before a
**rare class** produces enough co-occurrences to say anything. From
[[Variant and absent branches]]: L-PDA and L-PLA occur in ~5% of cases, IM in
~25–27%. If SegQueue's duplicate rate stays at 5% of served cases, and the
project ultimately annotates on the order of a few hundred to ~1000 cases
in-house (on top of any imported ImageCAS-X labels), the arithmetic is
unforgiving for the rare classes:

| Duplicate rate | Cases annotated | Duplicate pairs | Expected L-PDA co-occurrences (~5%) | Expected IM co-occurrences (~26%) |
|---|---|---|---|---|
| 5% (current) | 500 | 25 | ~1.25 | ~6.5 |
| 5% (current) | 1000 | 50 | ~2.5 | ~13 |
| 10% | 1000 | 100 | ~5 | ~26 |

Even doubling the duplicate rate to 10% barely produces enough L-PDA
co-occurrences to compute anything more than a point estimate — consistent
with [[How well two annotators agree on per-branch coronary labels]]'s finding
that ImageCAS-X's own 160-case, 800-total overlap set gave only 8–9
occurrences of L-PDA/L-PLA and reported DSC with a standard deviation nearly
as large as the mean (75.1 ± 29.0). **No affordable duplicate rate will give a
stable per-class agreement number for the rarest classes**; the honest design
response is to report them pooled across the whole project's runtime rather
than per-batch, and not to gate an individual annotator's trust level on their
single-digit sample of a rare class.

### What Sim & Wright would answer, and why I could not retrieve it

**Sim J, Wright CC. *The kappa statistic in reliability studies: use,
interpretation, and sample size requirements.* Phys Ther 2005;85(3):257–268.
doi:10.1093/ptj/85.3.257.** This is the standard reference for sizing a
reliability study around a *categorical* judgement (e.g. "is IM present," "is
this heart right- or left-dominant") using Cohen's kappa, which is the right
tool for the presence/absence disagreement [[How well two annotators agree on
per-branch coronary labels]] identifies as a distinct, Dice-invisible error
mode (87.5–100% agreement per class in ImageCAS-X, worst for the
variably-present branches). **I could not access it**: it is paywalled at
Oxford Academic, the institutional proxy route specified for this session
(`login.myaccess.library.utoronto.ca`) was not reachable via the tools
available to me this session (no working browser-automation skill was
available — see the final report), and no open mirror had the actual sample-
size tables, only the abstract. Retrieve this by hand before finalising a
categorical-agreement overlap size; every secondary source confirms the paper
*contains* the needed tables, none reproduces the numbers.

### A categorical-agreement analogue that is accessible

**TopCoW** (Yang K, Musio F, Ma Y, et al., arXiv:2312.17670v4, 2025 — full
citation and detail already in `Handover/Annotation protocol evidence.md`,
verified there against the arXiv text) measured exactly this kind of
categorical judgement — classifying an anatomical variant (anterior/posterior
circle-of-Willis variant) — on only **5 patients**, two raters: "balanced
accuracies between the raters were 88% for AV and 78% for PV. Cohen's Kappa
scores were 83% for AV and 72% for PV." A kappa in the 0.7–0.8 range from a
5-patient reliability check is a real, if imprecise, result — categorical
agreement studies can produce a usable number from surprisingly few cases
compared with continuous Dice, because each case contributes one full
observation to the kappa rather than a noisy continuous score. This is
indirect support for running our dominance/presence agreement check as its own
small, deliberately-sized study rather than only reading it off the general
5%/10% duplicate stream — a 30–50-case blind-paired mini-study on
presence/dominance alone, sized once Sim & Wright is in hand, would likely
answer the categorical question better than years of 5% duplicates would.

### A different published categorical-agreement design: weighted kappa that discounts adjacent-segment confusion

**Föllmer B, Tsogias S, Biavati F, et al. *Automated segment-level coronary
artery calcium scoring on non-contrast CT: a multi-task deep-learning
approach.* Insights Imaging 2024;15:250. doi:10.1186/s13244-024-01827-0.**
Read via a fetched summary of the PMC/Insights Imaging text (not the full PDF
— **flagged as a secondary extraction, verify before quoting numbers
elsewhere**).

For their 13-segment (SCCT-derived) calcium-scoring task, they score
segment-assignment agreement with a **weighted Cohen's kappa that gives a
misclassification between adjoining segments a weight of 0.5 and any other
misclassification a weight of 1.0** — i.e. calling a lesion "proximal RCA"
when it is "mid RCA" costs half what calling it "LAD" would. Reported
model-vs-reference weighted kappa 0.808 (95% CI 0.790–0.824), against a
human-observer weighted kappa of 0.809 — the model matched inter-observer
agreement almost exactly. Per-segment sensitivity ranged from 0.95 (proximal
RCA) to 0.00 (side-branch RCA) and 0.40 (distal LAD), the same
easy-trunk/hard-branch ordering as everywhere else in this research
(see [[Class schema options]]).

This is directly useful **if our schema keeps any proximal/mid/distal split**
(it currently does not — see [[Class schema options]] — but the merged view
proposed there could resurrect it at evaluation time). A weighted-agreement
statistic that discounts neighbour confusion is the correct way to measure
disagreement at a bifurcation boundary without pretending a 1-voxel-off carina
call is as bad as a wrong branch name, which is the exact question
[[Class schema options]] raises about carina/bifurcation ownership.

## Arbitration: what happens after a flag

`Handover/Annotation protocol evidence.md` proposes: an automatic flag on
dominance disagreement, presence disagreement on any class, or a trunk Dice
drop of more than ~10 points from the human ceiling, routed to a single senior
reviewer whose decision is final — modelled on ImageCAS-X's "review by the
lead analyst" and on ImageCAS's own three-radiologist-adjudication design
(a third radiologist annotates and "the final result is determined by
consensus" on disagreement, per Zeng et al. 2023, already read in full and
cited in [[How well two annotators agree on per-branch coronary labels]]).

I did not find a published protocol that does anything more sophisticated than
"expert breaks the tie" for per-branch vessel disagreement specifically —
every source in this research (ImageCAS, ImageCAS-X, FIVES) resolves
disagreement the same way, with a senior person. The one methodological
variation worth flagging: **FIVES's fusion rule was intersection, not a tie-
break** (see [[Can non-experts label vessels as well as experts]]) — "the
pixels annotated by the 2 annotators in common were included as the final
ground truth," then senior review corrected errors and discussed genuine
disagreements. Intersection trades recall for precision automatically, without
consuming any senior reviewer time on the vast majority of cases where the two
annotations mostly agree; disagreement only needs adjudication where the
non-overlapping region is large enough to matter. This is a cheaper first
filter than "flag everything and send to a human," worth adopting as a
pre-filter ahead of the senior-reviewer step: **auto-accept the intersection
as the training label on any case where the two annotations' pairwise Dice per
class already clears the human ceiling from [[How well two annotators agree on
per-branch coronary labels]]; only route the rest to a reviewer.**

## What this implies for [[Training plan]]

- SegQueue's existing 5%/5%/20%→10%/0.70 numbers are a reasonable
  implemented default and none of the evidence here contradicts them outright,
  but two gaps are worth closing: (1) the 0.70 flag threshold is a single
  global number applied per case-mean, which [[How well two annotators agree
  on per-branch coronary labels]] already flags as hiding exactly the
  catastrophic single-class failure QA most needs to catch — a per-class flag
  (or a "any class present in one annotation and absent in the other" flag)
  is a small code change with direct evidence behind it; (2) no categorical
  (presence/dominance) agreement statistic is currently computed at all.
- **Retrieve Sim & Wright by hand** before finalising any specific overlap-set
  size for the categorical (presence/dominance) question; nothing else found
  gives the sample-size arithmetic directly.
- **Rare classes (L-PDA, L-PLA) cannot be stabilised by any affordable
  duplicate rate.** Report them pooled across the project's full runtime, not
  per-batch, and do not gate annotator trust on them individually.
- **Adopt an intersection auto-accept, human-only-on-the-remainder rule** for
  blind duplicates, modelled on FIVES, ahead of full senior review — cheaper
  than routing every flagged case to a human, and it only consumes reviewer
  time where the two annotations actually diverge by more than chance.
- These are proposals for whoever owns the annotation-protocol code and QA
  thresholds to accept or reject; nothing here edits `src/segqueue/policy.py`
  or [[Training plan]] directly.
