---
aliases: [Patch sampling, Vessel-anchored sampling, Foreground oversampling, Class-balanced sampling]
tags: [research/architecture, sampling, class-imbalance, nnunet, coronary, evidence]
status: solid
updated: 2026-09-19
---

# Class-balanced and vessel-anchored patch sampling for rare distal branches

Sub-question: [[Training plan]] §5 lists "class-balanced, vessel-anchored patch
sampling" as a standing experiment for the multiclass model, arguing that
"nnU-Net's default picks one random foreground class for a third of patches; with
many classes of wildly different volume — some absent in many patients — rare
branches starve." Is that mechanism correctly described, and what is the fix with
evidence behind it?

## What nnU-Net's default sampler actually does — verified in source

Two levels of randomness are involved, and only one of them is class-balanced.

1. **Case selection.** Before any patch is drawn, nnU-Net must pick which training
   case to sample from. This is driven by the dataloader's case iteration (weighted
   toward finishing an epoch over the case list, not toward any class), so a branch
   class that is anatomically present in only a fraction of the 1000 cases (a ramus
   intermedius, or a hypoplastic distal segment) is proportionally rare *at this
   level* regardless of anything downstream.
2. **Within-case patch placement**, `oversample_foreground_percent` (default 0.333):
   for the oversampled fraction of patches, nnU-Net's v2 `DataLoader3D.get_bbox`
   (`nnunetv2/training/dataloading/data_loader.py`, verified against current source)
   calls `fg_locations.eligible_classes(identifier)` to get the list of foreground
   classes **present in that specific case**, then
   `selected_class = eligible_classes_or_regions[np.random.choice(len(eligible_classes_or_regions))]`
   — **uniform random choice among classes present in the chosen case**, not
   weighted by how rare that class is across the dataset.

Read precisely, the plan's description is half right: within a case where a rare
branch and a common one are both present, nnU-Net already gives them **equal**
sampling weight for that oversampled draw — it does not favour the common vessel.
The actual starvation mechanism is upstream, at case selection: a class present in
only 80 of 1000 cases gets patches centred on it only when one of those 80 cases is
drawn, at the same rate as every other case is drawn, and never gets *extra*
attention to compensate for its rarity across the cohort. This distinction matters
for where a fix should act — reweighting the class-choice line inside an already-rare
case buys little; reweighting *which case gets selected*, or how many patches per
case get centred on the rare class once it is selected, buys more.

## Evidence that instance/class imbalance genuinely starves rare structures

- **BraTS-METS 2025** (Kundu, Kofler, Ivory, et al., *Instance Awareness of
  Multi-class Semantic Segmentation Loss Functions*, arXiv:2604.24276, preprint;
  brain metastases, 260 test cases — **not vascular**, but the mechanism generalises
  directly): a plain voxel-averaged Dice+CE baseline scored 0.59 ± 0.27 foreground
  Dice; extending instance-sensitive losses (blob loss / CC loss) to the multiclass
  setting via one-vs-rest decomposition, so that "uniform averaging over classes
  ensures each class contributes equally regardless of frequency", raised foreground
  Dice to 0.64 ± 0.26 and improved rare-class Dice specifically; inverse-size
  weighting confined to each connected component's own spatial context (rather than
  applied globally, which the authors report destabilises training) pushed rare-class
  Dice to 0.44 ± 0.36. This is a **loss-level**, not a sampling-level, fix to the same
  underlying problem — the authors' framing ("rare classes with few instances receive
  a disproportionately small share of the training signal" under plain voxel
  averaging) is the same starvation mechanism the plan's sampling proposal targets,
  attacked from the objective side instead of the sampler side. Not on coronary or
  even vascular data; recorded as mechanism evidence, not an effect size for our task.
- **TopCoW multiclass, on vascular anatomy directly** (already the central table in
  [[Topology-aware losses on thin tubular structures]]): default nnU-Net Dice+CE
  scored **0** Dice on the small, variably-present classes (β=0 row, small
  communicating arteries) while scoring 84 on the large ones — the sharpest
  documented case of a standard sampler-plus-loss combination failing completely on
  a rare vascular class of exactly the kind this project's distal branches are. The
  rescue there came from a topology loss term (cbDice/clDice), not from resampling,
  because the TopCoW paper (Shi et al., MICCAI 2024, arXiv:2407.01517) does not
  report changing the sampler — so this result shows the failure is real on our
  anatomy-class, but does not by itself show sampling is the fix; it shows a fix is
  needed somewhere.

## Vessel-anchored sampling beyond nnU-Net's per-case class choice

"Vessel-anchored" in the plan's phrasing means going further than nnU-Net's
present-in-this-case uniform choice: deliberately biasing *which case* gets drawn,
or *how many* of a case's oversampled patches centre on its rarest class, by the
class's dataset-wide frequency — the standard remedy in the general class-imbalance
literature (inverse-frequency case weighting, class-balanced episodic sampling).
Search of the coronary-specific literature turned up no published ablation of this
exact mechanism (case-frequency-weighted sampling) against nnU-Net's default on a
coronary dataset; this is a gap, not a settled question, and the two- or three-way
disagreement in the class-imbalance literature generally (undersampling vs
oversampling vs loss reweighting, none dominant across tasks) means the experiment
has to be run on this cohort rather than assumed from elsewhere.

## What this implies for [[Training plan]]

1. **Correct the mechanism in §5.** The starvation nnU-Net's default produces is at
   case-selection frequency, not at the per-case class-choice step, which is already
   uniform. A fix should target *how often a case containing a rare class is drawn*,
   or *how many oversampled slots within that case go to the rare class*, not the
   per-case `np.random.choice` line, which needs no change.
2. **Treat sampling and loss reweighting as two candidate fixes for the same
   documented failure**, not as alternatives already resolved in favour of one: the
   TopCoW zero-Dice result shows the failure on vascular multiclass data; the
   BraTS-METS ablation shows a loss-side fix working on a different anatomy; nothing
   found shows a sampling-side fix measured on any vascular multiclass task. The
   scheduled Skeleton Recall loss experiment ([[Topology-aware losses on thin
   tubular structures]]) and this sampling experiment address related but distinct
   mechanisms (connectivity vs exposure) and should be logged as separate ablation
   arms, not conflated.
3. **Keep some genuinely random background patches**, as the plan already states,
   for look-alike rejection — none of the imbalance evidence above argues for
   removing that; the failure mode it prevents (learning to always predict
   foreground) is a different one from rare-class starvation.
4. **This is a genuinely open experiment, not a literature-settled one.** Record it
   as such rather than importing a numeric expectation from BraTS-METS or TopCoW —
   neither is coronary CTA and neither isolates sampling from loss.

Related: [[Topology-aware losses on thin tubular structures]],
[[Class imbalance in multiclass vessel segmentation]].
Collected in [[Proposed changes]].
