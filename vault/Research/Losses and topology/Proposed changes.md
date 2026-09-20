---
aliases: [Proposed changes, Loss and topology proposals]
tags: [research/loss, proposal, decision-record]
status: living
updated: 2026-09-19
---

# Proposed changes to the training plan

Concrete edits to [[Training plan]] proposed by the losses-and-topology research
thread, each with the note that carries the evidence. Nothing here has been
applied; this folder does not edit the plan.

## 1. Resolve the "Loss" line in "Still open" to a specific, scheduled experiment

**Where:** "Still open" bullet "Loss: defaults (Dice+CE) for the baseline;
clDice/cbDice term is a candidate second experiment, not yet scheduled."
**Proposed:** "Baseline Dice+CE unchanged. **Skeleton Recall** is the scheduled
second experiment (`-tr nnUNetTrainerSkeletonRecall`, pinned commit from
`MIC-DKFZ/Skeleton-Recall`), same fold/data/harness as the multiclass baseline.
cbDice is a conditional third run, triggered only if rare branch classes score
near zero in the baseline. clDice is ruled out: it OOM'd at 13 classes on 40 GB at
default nnU-Net patch size, and the two coronary-CTA measurements that exist
(ImageCAS-X, BCS) both show it as a no-op or a regression on topology metrics."
**Evidence:** [[Topology-aware losses on thin tubular structures]].

## 2. Move the loss experiment out of "Still open" and into §5 "Standing experiments"

**Where:** §5.
**Proposed:** add the Skeleton Recall run as a standing experiment, with its
acceptance criterion stated as "per-class branch detection rate and per-class
centerline overlap for the smallest classes improve, not mean Dice" — every
coronary-CTA measurement found moved mean Dice by less than seed-to-seed noise.
**Evidence:** [[Topology-aware losses on thin tubular structures]].

## 3. Add component count and a fragment-purity check to the evaluation list

**Where:** Evaluation section.
**Proposed:** add two metrics beyond the existing Dice/NSD/HD95/AHA-confusion list:
(a) connected-component count per case against the expected anatomical count
(β₀), because the plan bans largest-component post-processing and needs a metric
that actually detects fragmentation instead of hiding it; (b) a per-component
class-purity check (what fraction of each connected component's voxels carry its
majority class), because a model can pass a component-count check while still
mislabelling pieces of a correctly-detected branch — a distinct failure the
component count does not catch.
**Evidence:** [[Largest-component post-processing is wrong for coronaries]],
[[Enforcing per-branch connectivity so fragments are not assigned to the wrong branch]].

## 4. Name the post-processing ban's mechanism and extend it explicitly to per-label

**Where:** §4, "nnU-Net's largest-component post-processing."
**Proposed:** "The mechanism is `nnUNetv2_find_best_configuration`'s automatic
post-processing search, which keeps a change only if mean Dice does not drop for
any single class — a criterion expressed entirely in Dice, which barely moves when
a 3–4-voxel branch disappears. The ban explicitly includes the **per-label**
variant (`nnUNetv2_determine_postprocessing` run once per class), which is the more
dangerous form for the multiclass model: it keeps only the largest blob *of each
branch class separately*, deleting a correctly-segmented distal piece across a
calcified stenosis on every branch, every case."
**Evidence:** [[Largest-component post-processing is wrong for coronaries]].

## 5. Record centerline reconnection and per-branch graph correction as downstream candidates, not pipeline dependencies

**Where:** §4, after the graph-reasoning carve-out sentence.
**Proposed:** "Two downstream graph-based candidates are recorded, both consistent
with the rule that graph reasoning must never gate what the voxel model found:
(a) centerline reconnection / gap bridging for fragments the voxel model detected
but did not connect (Qiu et al.'s DPC-walk framework: +1.40 Dice, HD95 5.06→1.07 mm
on ASOCA, ResUNet baseline, nnU-Net not compared); (b) a topology-graph relabelling
pass for fragments the voxel model detected and connected but mislabelled across a
bifurcation (VTG-Net's retinal A/V analogue: +3.5–4.2 accuracy points from adding
graph-based correction on top of an unchanged per-pixel classifier). Neither is
scheduled; both are candidates gated on the multiclass baseline showing the
specific failure each addresses."
**Evidence:** [[Largest-component post-processing is wrong for coronaries]],
[[Enforcing per-branch connectivity so fragments are not assigned to the wrong branch]].

## 6. Flag two coronary-specific papers for hand fetch (paywalled this session)

**Where:** n/a — a note for whoever next has UofT-proxy or Chrome access.
**Proposed:** fetch and verify (a) *A Clinically-Informed Benchmark for
Topology-Aware Coronary Artery Segmentation* (Springer LNCS 2026, DOI
10.1007/978-3-032-17734-6_2) — claimed to benchmark topology losses on ASOCA and
find them similar on primary segments; (b) *Transformer Based Coronary Artery
Segmentation Using Tversky Loss Function on 3D CCTA Images* (SN Computer Science,
DOI 10.1007/s42979-025-04619-5) — the one paper found squarely on Tversky loss for
multiclass-adjacent coronary imbalance. Neither claim above is currently cited as
evidence; both are unverified pending access.
**Evidence:** [[Topology-aware losses on thin tubular structures]],
[[Class imbalance in multiclass vessel segmentation]].
