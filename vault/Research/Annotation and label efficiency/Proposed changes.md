---
aliases: [Annotation proposed changes]
tags: [research, annotation, decision-record, proposal]
status: proposal
updated: 2026-09-19
---

# Proposed changes (annotation and label efficiency)

Edits to [[Training plan]], and to the SegQueue implementation, proposed by
the annotation-protocol and label-efficiency research in this folder. Nothing
here is decided; the plan changes only when someone accepts an item. Anything
the plan loses as a result belongs in [[Plan status]].

Scope: annotation protocol, label quality, and label efficiency only. The
early draft in `Class schema/Handover/Annotation protocol evidence.md` covers
overlapping ground and is superseded by the notes in this folder, in
particular [[Sizing the overlap set and arbitrating disagreements]].

## 1. Close "Annotation protocol details"

Evidence: [[Sizing the overlap set and arbitrating disagreements]],
[[Detecting a drifting or bad annotator]], [[Fusing multiple annotations and
learning from noisy labels]], [[How well two annotators agree on per-branch
coronary labels]].

Proposed text for a new decided section of the plan:

> **Annotation protocol.** Centerline-first labelling with nearest-centerline
> voxel assignment (matching the ImageCAS-X construction, see [[Class schema
> options]]). New annotators certify against ImageCAS-X training-split
> reference cases before live work. SegQueue's existing 5% gold / 5% blind
> duplicate / 20%→10% sampled review / 5-case training gate stand as the
> operating design; the QA statistic changes from a single per-case mean Dice
> flag to: (a) per-class flagging, not a case mean; (b) a missed-structure
> check against the model's own presegmentation, not only Dice against a
> human partner; (c) a trend across an annotator's last 5–10 scored cases, not
> only a single-case threshold; (d) signed, not only absolute, per-class bias
> against gold/duplicate references. Rare classes (L-PDA, L-PLA, ~5%
> prevalence) are reported pooled across the project's full runtime, not
> per-batch, and are not used to gate individual annotator trust.

## 2. Rare-class overlap cannot be solved by raising the duplicate rate

Evidence: [[Sizing the overlap set and arbitrating disagreements]] §"Sizing an
overlap set against class prevalence".

Even doubling `duplicate_rate` from 5% to 10% gives only ~5 L-PDA
co-occurrences per 1000 cases annotated. No affordable rate fixes this.
Proposal: run a **separate, deliberately-sized categorical mini-study**
(30–50 blind-paired cases, stratified toward known or predicted left-dominant/
co-dominant hearts) for the presence/dominance judgement specifically, once
[[Sizing the overlap set and arbitrating disagreements]]'s open item (Sim &
Wright's sample-size tables, currently inaccessible) is retrieved to size it
properly.

## 3. Intersection auto-accept for blind duplicates

Evidence: [[Sizing the overlap set and arbitrating disagreements]] §
"Arbitration", citing FIVES (Jin et al., Sci Data 2022).

Where two blind annotations of the same case already agree per class at or
above the human ceiling from [[How well two annotators agree on per-branch
coronary labels]], auto-accept the voxel intersection as the training label
and skip senior review. Only route cases where the two annotations diverge
more than the human ceiling predicts. Reduces reviewer load without touching
the cases that actually need a human decision.

## 4. Schedule a partial-annotation self-training experiment

Evidence: [[Seeding annotation with model predictions and label efficiency]],
citing Zhang et al., MICCAI 2023 (arXiv:2307.04472) — 24.29% of branches
manually labelled reached parity with full per-branch annotation on clinical
CCTA data via self-training and prototype learning.

Proposal: before committing the full annotation team to fully labelling every
case, run a scheduled experiment: label a deliberately small fraction of
branches (or fully label a fraction of cases) and measure whether a
self-training pass on the rest reaches acceptable per-class agreement. If it
does, this is the single largest lever available on annotator hours; if it
does not on our anatomy, that is worth knowing early rather than after the
team has spent a term on full manual correction everywhere.

## 5. Stratify which cases get annotated first by likely dominance

Evidence: [[Seeding annotation with model predictions and label efficiency]]
§"How many fully-labelled cases".

Random case order under-samples left-dominant and co-dominant hearts
(~5–8% and ~2–4% of cohorts respectively, see [[Variant and absent
branches]]). If the binary lumen model or a cheap heuristic can flag likely
left/co-dominance before a case is served, prioritise those cases toward
annotation early rather than relying on random draw to eventually cover them.

## 6. Noise-robust loss as a cheap standing experiment

Evidence: [[Fusing multiple annotations and learning from noisy labels]] §
"The taxonomy of methods for training on noisy labels".

Not decided here (loss function is another agent's topic — see [[Handoffs]])
but flagged because the evidence is annotation-specific: Karimi et al. 2020's
own experiments found MAE/iMAE-family losses and, more strongly, joint
annotator-confusion estimation outperformed both a single rater's labels and
plain majority vote on a directly comparable multi-rater medical classification
task. Worth the loss-function owner's attention alongside the existing
clDice/cbDice candidate.
