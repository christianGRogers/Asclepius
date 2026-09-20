---
aliases: [Binary-init fine-tuning, Multi-task learning, Centerline auxiliary head, Warm-start]
tags: [research/architecture, fine-tuning, multi-task, transfer-learning, coronary, evidence]
status: solid
updated: 2026-09-19
---

# Binary-init fine-tuning and multi-task auxiliary heads for the multiclass model

Sub-question: [[Training plan]] §3.2 and §5 name "binary-init fine-tuning vs
from-scratch" for the multiclass model as a cheap standing experiment, plan-of-record
still "retrain from scratch". Separately, Topic 1 asks about multi-task setups
(lumen head plus branch-label head, centerline heads). Both are versions of the same
question — what auxiliary signal, beyond the multiclass labels themselves, is worth
carrying into training — so they are treated together here.

## Binary-init fine-tuning: no coronary-specific measurement exists, but the closest analogue is positive

No paper found initialises a *multiclass* coronary segmenter from a *binary* lumen
checkpoint and measures it against training the multiclass model from scratch — this
exact experiment is **unmeasured in the literature** and stays a genuinely open
question, which is why [[Training plan]] correctly keeps it a "cheap experiment, not
the plan of record" rather than a decision.

The closest measured analogue is in-domain self-supervised pretraining on the same
cohort, covered in full in [[Foundation and promptable models do not yet beat a
configured nnU-Net for coronaries]]: Kim, Song, Wu, et al. (J Med Imaging
12(1):016002, 2025, DOI 10.1117/1.JMI.12.1.016002) pretrained a UNETR
self-supervised on up to 800 unlabelled ImageCAS volumes, then fine-tuned on a
labelled cohort, and measured **+4.8 Dice** (internal) and **+4.1 Dice** (external)
over training the same architecture from scratch, with the gain largest exactly when
fine-tuning data is scarcest (0.56 vs 0.38 Dice at a 79:1 pretrain:fine-tune ratio).
Binary-init fine-tuning is a *stronger* form of this idea than SSL pretraining —
the binary checkpoint already encodes supervised knowledge of "this voxel is
coronary lumen", which is a strict subset of every multiclass label, rather than a
task-agnostic contrastive representation. If unsupervised in-domain pretraining
buys 4–5 Dice points on this exact cohort, a supervised binary-lumen warm start is at
least as plausible a source of transferable signal, and the annotator pipeline
described in [[Training plan]] §3.1 already produces the binary checkpoint for free
(it exists before any multiclass label does) — making this one of the cheapest
experiments in the whole plan to try, at the cost of one paired fine-tuning run once
per-branch labels exist.

The general transfer-learning literature (searched broadly; nothing coronary- or
vessel-specific beyond the above) gives one relevant qualitative pattern worth
recording, from the segmentation transfer-learning survey (Kandel & Castelli-class
findings, general medical imaging, not vessel-specific): reusing pretrained weights
for lower encoder layers and randomly (re)initialising task-specific layers is
reported as the sub-variant with the largest effect on convergence speed. Applied to
binary-to-multiclass fine-tuning, this suggests the useful signal is likely to be in
the shared encoder (edge and vesselness-like low-level features common to both
tasks), while the final classification layer — which must grow from 2 classes to
~15 — has no pretrained weights to inherit and should not be expected to transfer.
This is a plausible mechanism, not a measured coronary result, and is flagged as such.

## Multi-task setups: centerline auxiliary heads have a direct, positive coronary result

Unlike binary-init fine-tuning, auxiliary centerline supervision **has** been
measured directly on coronary and coronary-adjacent vascular imaging, though not on
CCTA volumetric segmentation specifically — the existing evidence base is 2D/X-ray
coronary angiography:

- Centerline-supervision multi-task learning (ScienceDirect,
  DOI-indexed but full text not opened this session — **flagged for hand fetch**):
  reported title claim is that adding a centerline-supervision auxiliary branch,
  with centerline labels obtained by skeletonising the segmentation mask,
  "improve[s] the accuracy and connectivity of segmentation results" on X-ray
  coronary angiography. Only the abstract-level claim was accessible; the
  quantitative Dice/connectivity numbers are **unverified**.
- Joint direction- and centerline-aware learning (JLNet; Yang, Xie, Cheng et al.,
  read via the ACM DL summary) joins direction prediction and centerline prediction
  with the segmentation mask in one loss, motivated explicitly by the claim that this
  "enforces the network to learn the geometric features of vessel connectivity" — the
  same structural argument as Skeleton Recall (see [[Topology-aware losses on thin
  tubular structures]]), but implemented as an auxiliary prediction head rather than
  a loss term on the segmentation head itself. Again, only summary-level claims were
  accessible this session; quantitative comparison **unverified, flagged for hand
  fetch**.

Mechanistically, an auxiliary centerline (or branch-label) head is a *softer* version
of what [[Training plan]] §4 already rules the tree/graph *segmenter* approach out
for: the auxiliary head's prediction never gates or replaces the voxel segmentation,
it only adds gradient signal during training, so it does not reintroduce the failure
mode ("any vessel the pre-segmentation misses never becomes a node") that disqualified
graph-structured *primary* segmenters. This is the same distinction the plan already
draws for downstream GNN branch labelling — see the sibling note.

## What multi-task with a lumen head plus a branch-label head would mean concretely

The plan's multiclass task is already, in effect, "segment the branch identity",
which subsumes "segment the lumen" (the union of all branch classes is the lumen).
A genuinely separate lumen head is therefore mostly useful as an easier auxiliary
target during early training or as a consistency signal (branch-class predictions
summed should equal the lumen prediction), not as new information — no coronary
paper located tests this specific auxiliary-lumen-head design, and it is not
distinguishable in the literature from the binary-init fine-tuning question above:
both are ways of giving the network an easier version of the task first. The
segment-level coronary calcium scoring literature (PMC11484984, "Automated
segment-level coronary artery calcium scoring") uses a related multi-task design
(joint calcium detection and AHA segment classification) but on calcium scoring, not
lumen segmentation, and is out of scope for a lumen/branch task — recorded here only
to note the pattern (auxiliary anatomical-location head) exists elsewhere in the
coronary CT literature.

## What this implies for [[Training plan]]

1. **Binary-init fine-tuning stays a scheduled cheap experiment, and the case for it
   strengthens**, by analogy with the +4–5 Dice SSL-pretraining result on the same
   cohort (Kim et al.) rather than by any direct measurement. Run it paired against
   from-scratch, same fold, same harness, the moment the first batch of per-branch
   labels exists — it costs nothing extra since the binary checkpoint is already a
   plan deliverable (§3.1).
2. **A centerline (or direction) auxiliary head is a second, distinct candidate
   experiment**, mechanistically safe against the plan's ban on graph *segmenters*
   (it never gates the output), but its coronary evidence is currently
   abstract-level only. Do not schedule it ahead of Skeleton Recall — the loss-level
   version of the same idea already has a stronger, better-controlled coronary CCTA
   result (BCS paper, three seeds, 250 test cases; see [[Topology-aware losses on
   thin tubular structures]]) — but note it as a follow-on if Skeleton Recall
   under-delivers.
3. **Flag for hand fetch:** the centerline-supervision multi-task paper and JLNet,
   both currently abstract/summary-only, would need full-text access before their
   claimed connectivity gains can be cited as evidence rather than as a lead.

Related: [[Foundation and promptable models do not yet beat a configured nnU-Net for coronaries]],
[[Topology-aware losses on thin tubular structures]],
[[Downstream graph labelling of coronary branches is a second stage, never the segmenter]].
Collected in [[Proposed changes]].
