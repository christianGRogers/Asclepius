---
aliases: [Annotator drift, Quality drift detection, Bad annotator detection]
tags: [research, annotation, quality-control, segqueue, literature]
status: draft
updated: 2026-09-19
---

# Detecting a drifting or bad annotator

A team of undergraduate annotators working over a term will not be uniformly
good, and will not stay equally good over time (fatigue, semester workload,
drifting interpretation of an ambiguous rule). SegQueue's gold cases and blind
duplicates (`src/segqueue/policy.py`) exist to catch this, but the code only
implements a per-submission mean-Dice flag; it does not yet track a trend, and
mean Dice is the specific statistic [[Can non-experts label vessels as well as
experts]] already shows hides the failure mode that matters. This note
collects what published evidence exists on *what* to measure and *how* to
watch it over time. Companion notes: [[Can non-experts label vessels as well
as experts]], [[Fusing multiple annotations and learning from noisy labels]],
[[Sizing the overlap set and arbitrating disagreements]].

## The evidence, ranked by how directly it transfers

### 1. A drift-specific finding, but not from imaging: systematic labelling drift is real and distinct from random noise

General crowdsourcing/annotation-quality literature (assembled from search
summaries, not a single paper read in full — **flag accordingly**) draws a
distinction between random inter-annotator disagreement and *drift*: a
consistent change in one annotator's behaviour over time, driven by fatigue or
a shifting internal model of an ambiguous rule, that a single-timepoint
agreement check will not catch because it looks like ordinary noise at any one
instant. The concrete design implication is the same one SegQueue's `policy.py`
docstring already states as its motivation ("reviewing nothing means finding
out in April that one student misunderstood") but does not yet operationalise:
**agreement has to be tracked as a time series per annotator, not only
computed per case.**

### 2. A concrete detector for one specific, quantified error mode: missed structures

**Karimi D, Dou H, Warfield SK, Gholipour A. *Deep learning with noisy labels:
exploring techniques and remedies in medical image analysis.* Med Image Anal
2020;65:101759 (arXiv:1912.02911v4). Read in full.** Full citation detail in
[[Fusing multiple annotations and learning from noisy labels]].

Their brain-lesion experiment (Section V-A) is the most directly transferable
result in this research to "how do you catch an annotator who is
systematically missing things." Setup: 165 MRI scans, TSC lesions, one
experienced annotator. On 12 scans, they had the annotator review the same
scans **twice**, in separate sessions, and compared: "In the 12 scans in the
clean dataset, 306 lesions were detected in the first reading and 68 lesions
in the followup readings" — i.e. **18% of lesions were missed on the first
pass**, purely from single-annotator inconsistency, no second annotator
involved. They then showed the misses were not random: "smaller or fainter
lesions were more likely to be missed... lesions that had been missed in the
first reading were less dark on the T1 image (p<0.001), smaller in size
(p<0.001), and farther away from the closest lesion (p=0.004)."

Their fix, built from this diagnosis: train a **random forest classifier**, on
six features (intensity in each sequence, lesion size, distance to nearest
lesion, and a CNN's own prediction uncertainty), to distinguish true lesions
the annotator missed from the CNN's false positives, and use it *during*
training to add back lesions the CNN found but the human annotation omitted.
Result: lesion-count F1 rose from 0.747 (baseline, trained on the
as-annotated noisy labels) to **0.819** with this iterative label cleaning,
the largest gain of every method they tried on this dataset (Table II).

Translated to coronary branches: **a small, distal, low-contrast branch is the
coronary analogue of a "smaller, fainter lesion,"** and the same systematic-
miss mechanism should be expected — an annotator under time pressure is more
likely to miss a faint distal OM2 than a bright proximal RCA, not at random
but predictably by exactly the features (diameter, contrast, distance from the
trunk) that already predict human disagreement in
[[Class schema options]] and [[How well two annotators agree on per-branch
coronary labels]]. The transferable design, independent of Karimi's exact
random forest: **compare an annotator's first-pass output against the model's
own prediction on the same case, specifically for foreground the model found
that the human omitted** (not the reverse — false additions are a different,
easier-to-catch error), and flag when this happens more than expected for a
given annotator, rather than only flagging low Dice.

### 3. Bias is a distinct signal from disagreement, and shows up more clearly downstream

**Shwartzman O, Gazit H, Shelef I, Riklin-Raviv T. *The Worrisome Impact of an
Inter-rater Bias on Neural Network Training.* arXiv:1906.11872v2, 2020.** Full
detail in [[Fusing multiple annotations and learning from noisy labels]] and
[[Seeding annotation with model predictions and label efficiency]].

Their finding that a rater-classifier network distinguished raters *more*
accurately from trained-network predictions than from the raters' raw
annotations is, read one way, a detection method: **a classifier trained to
predict "which annotator produced this label" from label geometry alone is
picking up exactly the systematic-bias signal that a symmetric agreement
metric (Dice against a partner or a gold case) is not designed to catch**,
because a consistent bias shared with no one else does not reduce Dice against
an independent gold reference the way random error does — it reduces it in a
*specific, reproducible direction*. A cheap version of this for SegQueue: for
each annotator with enough submitted cases, compute the *signed* per-class
volume or boundary-position bias against the gold/duplicate reference (not
just |error|), and flag a persistent one-directional sign, not only a large
magnitude.

### 4. What general crowdsourcing quality-control practice does, for calibration

**Ørting SN, Doyle A, van Hilten A, Hirth M, Inel O, Madan CR, Mavridis P,
Spiers H, Cheplygina V. *A Survey of Crowdsourcing in Medical Image Analysis.*
arXiv:1902.09159v2, 2019 (submitted to Human Computation).** Read in full via
the fetched arXiv PDF.

Directly relevant numbers from their survey of 57 medical-imaging
crowdsourcing papers (their Table 2, Section 4): of studies using multiple
annotators per image, "the number of annotators per image for experiments
using multiple annotators per image ranges from 2 to 5000," but "the majority
(66%) of these experiments use between 5 to 25 annotators per image" — far
more redundancy than SegQueue's design (2 annotators on a duplicate case),
because most of the surveyed work is crowdsourcing to an anonymous, unvetted
public rather than a trained, individually-accountable team; not a number to
copy, but useful context for why SegQueue's lighter-weight, identity-tracked
design (5-case gate, then 20%→10% review) is the correct simplification for
a small trained team rather than a mass-anonymous crowd, where the *only*
lever available is redundancy. Their survey did **not** report a method for
detecting drift specifically (checked directly; not found in the fetched
sections) — it documents gold-standard injection and majority/STAPLE fusion as
the standard tools, both of which SegQueue and [[Fusing multiple annotations
and learning from noisy labels]] already cover, but nothing beyond that on a
*time-series* quality signal. This is a real gap in the published literature,
not a search failure on my part — worth stating plainly rather than papering
over.

## Synthesis: what SegQueue's flag rule should track that it does not yet

Reading `src/segqueue/policy.py`'s `review_needed` and the `gold_dice_flag` /
`duplicate_dice_flag` constants against all four findings above:

1. **Per-class, not per-case-mean.** Already argued in [[How well two
   annotators agree on per-branch coronary labels]] and [[Sizing the overlap
   set and arbitrating disagreements]]; repeated here because it is also the
   specific mechanism by which a drifting annotator's error on one branch
   hides inside a good mean.
2. **Missed-structure rate against the model's own presegmentation**, not only
   Dice against a partner or gold reference — the Karimi mechanism. A branch
   the binary model (or, later, the multiclass model) found with reasonable
   confidence and the annotator's submission does not contain at all is a
   stronger, cheaper-to-compute signal than Dice on the branches both agree
   exist.
3. **A trend, not a snapshot.** Store each annotator's gold/duplicate score
   per class over time (already possible — the scores exist per submission)
   and flag a downward trend across, say, the last 5–10 scored cases, not only
   a single case falling below 0.70. A single bad case is expected noise; a
   run of five declining scores is drift.
4. **Signed bias, not only magnitude**, computed against gold or duplicate
   references, to catch the Shwartzman failure mode — an annotator who is
   consistently generous or consistently conservative on a boundary call in a
   way that never quite drops mean Dice below threshold but is real and
   reproducible.

None of this requires new infrastructure beyond what SegQueue already scores
per submission (`server/girder_segqueue/scoring.py`'s `mean_dice`, per the
citation already in [[Can non-experts label vessels as well as experts]]); it
is a matter of storing per-class and per-annotator time series rather than
consuming a single scalar and discarding it.

## What this implies for [[Training plan]]

- These are concrete, code-adjacent recommendations for whoever owns
  `src/segqueue/policy.py` and `server/girder_segqueue/scoring.py` — not a
  training-method decision, so nothing here edits [[Training plan]] directly.
  Flagged as a handoff-quality finding even though it sits inside this folder's
  scope (annotation protocol), because it is closer to an implementation
  change than a research conclusion.
- The four gaps above (per-class flagging, missed-structure detection against
  the model, trend tracking, signed bias) are the concrete content for
  [[Training plan]]'s "annotation protocol details" item, alongside the
  overlap-set and arbitration proposals in [[Sizing the overlap set and
  arbitrating disagreements]].
- Karimi's 18%-missed-on-first-pass finding (single annotator, no second
  rater involved) is a caution against assuming a single annotator's
  submission is reliable just because it was not flagged by duplicate or gold
  scoring — most cases are neither, and the miss rate was measured precisely
  on cases with no partner to disagree with.
