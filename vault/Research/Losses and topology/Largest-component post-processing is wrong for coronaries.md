---
aliases: [Largest connected component, LCC post-processing, Post-processing policy, Gap bridging]
tags: [research, post-processing, topology, coronary, nnunet]
status: draft
updated: 2026-09-19
---

# Largest-component post-processing is wrong for coronaries

[[Training plan]] §4 already rules out nnU-Net's largest-component
post-processing. This note supplies the evidence for that ban, states precisely
what nnU-Net's rule does (so the ban can be implemented rather than remembered),
and surveys what to do instead with the fragments that remain.

Related: [[Topology-aware losses on thin tubular structures]] — the loss we are
most likely to adopt (Skeleton Recall) *increases* fragment count, which makes
the post-processing policy part of that experiment rather than a later tidy-up.

## What nnU-Net's rule actually is

From nnU-Net's own documentation (`MIC-DKFZ/nnUNet`,
`documentation/how_to_use_nnunet.md`), verbatim:

> "Postprocessing in nnU-Net only considers the removal of all but the largest
> component in the prediction (once for foreground vs background and once for
> each label/region)."

and

> "nnUNetv2_find_best_configuration will also automatically determine the
> postprocessing that should be used."

The acceptance criterion lives in
`nnunetv2/postprocessing/remove_connected_components.py`: a candidate
post-processing step is kept only if the **foreground mean Dice** improves, and
is rejected if **any single class's mean Dice** drops — the code's own comment
is *"if a single class got worse as a result we won't do this"*. That guard is
better than nothing, but it is a guard expressed entirely in Dice.

Two consequences for us:

1. **The decision metric is the wrong metric.** Dice on a 3–4-voxel-wide tube
   barely moves when an entire distal branch disappears, so "Dice did not get
   worse" is not evidence that no vessel was deleted. This is the same
   argument made for the evaluation set in
   [[Why Dice misreads a three-voxel coronary branch]]; here it decides whether
   voxels are thrown away, which is worse.
2. **The per-label variant is the dangerous one for the multiclass model.**
   "Once for each label" means: for every branch class, keep only that class's
   largest blob. A correct segmentation of a branch that the network happens to
   predict in two pieces across a calcified stenosis loses the distal piece —
   precisely the piece that matters clinically.

## Why it is wrong for this anatomy specifically

- **The ground truth is not one component.** The coronary tree arises from two
  separate ostia; a normal heart yields at least two disconnected trees in any
  voxel mask (three when a conus branch or a separate ostium is labelled). Any
  rule that keeps one component deletes an entire coronary territory by
  construction. This is not a subtle statistical effect, it is anatomy. The
  best-performing coronary reconnection work in the literature encodes the same
  assumption from the other direction: Qiu et al.'s framework seeds its
  reconnection from *"the two largest connected components"* and treats
  everything else as candidate branches to be reattached, not deleted.
- **Predictions are far more fragmented than the anatomy.** On ImageCAS with no
  post-processing, the BCS paper counts β₀ = 2.9 to 7.9 26-connected components
  per case for the three baselines it trains, rising to 5.8–11.9 with Skeleton
  Recall (Owusu-Ansah et al., STACOM 2026 workshop preprint, arXiv:2607.28327;
  250 test cases, mean over 3 seeds). Against an expected 2, a
  keep-the-largest rule would discard between one and ten real or partly real
  objects per case.
- **Component count and clinical usefulness are not aligned.** In that same
  table, the configuration with the *worst* β₀ (Skeleton Recall, 8.0 on CT-FM)
  had the *best* downstream FFR treat/no-treat agreement (85.7 % vs 75.4 %
  baseline). Deleting components to make β₀ look like the ground truth's would
  have thrown away exactly the branches that improved the clinical decision.

The claim in [[Training plan]] §4 that ImageCAS "shows it removing real coronary
while keeping bone" could **not be re-verified in this session** — the ImageCAS
PDF would not extract text and no HTML version was available. Treat that
specific sentence as unverified provenance; the ban itself stands on the three
points above, which were verified.

## Is removing *small* components safe?

This is a different rule from keep-the-largest and the literature is split on
it:

- ImageCAS-X (Bransby et al., arXiv:2608.30404, 2026 preprint) post-processes
  every model with *"threshold at 0.5, followed by removal of connected
  components smaller than 100 voxels"*. At their 0.5 mm isotropic resampling,
  100 voxels is 12.5 mm³ — a 1.5 mm-diameter branch segment about 7 mm long.
  So even this "safe" rule can delete a short distal stub.
- The BCS paper applies **no connected-component post-processing at all** and
  reports β₀ as a metric instead.

At our native ~0.35 mm spacing, 100 voxels is ~4.3 mm³ — a thinner slice of
vessel than at 0.5 mm, so a voxel-count threshold transplanted from another
paper means something different here. Any threshold must be expressed in mm³
(or better, in centerline length), never in voxels, and must be chosen by
looking at what it deletes, not by Dice.

## The alternatives, and what evidence supports them

### Centerline reconnection / gap bridging

The strongest coronary-specific evidence is Qiu et al.'s three-stage framework
(*A topology-preserving three-stage framework for fully-connected coronary
artery extraction*, arXiv:2504.01597, 2025; a journal version appears in
Medical Image Analysis, PMID 40239457, which I could not open — ScienceDirect
returned HTTP 403). Its predecessor is peer-reviewed: Qiu Y, Li Z, Wang Y,
Dong P, Wu D, Yang X, Hong Q, Shen D. *CorSegRec: a topology-preserving scheme
for extracting fully-connected coronary arteries from CT angiography.*
MICCAI 2023, doi:10.1007/978-3-031-43898-1_64.

Structure: (1) segmentation with an NSDT soft-clDice loss (clDice reweighted by
a normalised skeleton distance transform); (2) **centerline reconnection** — a
"DPC walk" that scores candidate steps by distance to the target endpoint, a
learned centerline probability, and directional cosine similarity, with
Dijkstra search for the connecting path; (3) missing-vessel reconstruction by
level-set / implicit modelling.

The ablation that matters to us (their Table 9, ASOCA) isolates stages 2+3:

| Configuration | Dice | HD95 |
|---|---|---|
| Stage 1 only | 87.13 % | 5.06 mm |
| Stages 1+2+3 | 88.53 % | 1.07 mm |

+1.40 Dice, and HD95 from 5.06 mm to 1.07 mm. PDSCA (100 private CTAs, Peking
Union) shows +1.7 Dice from the same stages. Headline numbers: 88.53 ± 1.81 %
Dice / 1.07 ± 0.60 mm HD95 on ASOCA (40 training cases, 20 test, five-fold CV),
85.07 ± 0.79 % / 1.63 ± 0.55 mm on PDSCA.

**Read the HD95 improvement, not the Dice improvement.** A reconnection step
that adds a thin bridge cannot move Dice much; collapsing HD95 by 4 mm is the
signature of "a far-away piece stopped being an orphan". That is the effect we
would be buying.

Caveats, recorded honestly: the comparison baseline is ResUNet (82.03 % Dice on
ASOCA), **nnU-Net is not in their tables at all**, so "+6 points over the
baseline" says little about what it would add on top of a properly configured
nnU-Net. The MICCAI reviewers' published concerns were that evaluation
*"only looks at typical distance and overlap metrics, but does not consider
stenosis or diseased areas"*, that there is no ablation of the loss itself, and
that the method shows *"much higher standard deviation compared to other
methods"* in one table. And stage 3 (implicit reconstruction of vessels the
network never saw) invents geometry — it is exactly the kind of step that must
never be allowed to fabricate a branch in a clinical read.

A relevant safety property of their design, which we should copy: reconnections
that fail an evaluation check are *"removed from the prediction mask"* — the
reconnection is proposed, scored, and only then accepted.

### Keep the fragments and report them

The BCS paper's position — no component post-processing, report β₀ and a
bifurcation-connectedness score instead — is the cheapest defensible policy and
is what `segtrain evaluate` already does by scoring raw predictions
(`src/segtrain/evaluate.py` deliberately does no post-processing). Note that
`src/segtrain/metrics.py` currently computes Dice, NSD and HD95 only; it has no
component count, so "we do not post-process, we measure instead" is not yet
true in code. Component counting is a metrics-side change and is flagged to the
metrics agent in `Handoffs.md`.

### Topology repair as a separate, auditable stage

Nothing in the coronary literature I could open supports applying a repair step
silently inside the inference command. Both Qiu et al. designs are explicit
multi-stage pipelines with their own evaluation. The pattern to adopt is:
raw prediction is the artefact of record, repair is a separate artefact, and
both are scored.

## Proposed policy

1. **Never run `nnUNetv2_determine_postprocessing`/`find_best_configuration`
   post-processing as part of the pipeline.** If it is ever run by hand, print
   what it selected per class and audit deletions in mm³ before believing it.
   The plan says this; it is worth making it a CI-checkable fact rather than a
   convention, since nnU-Net applies it automatically inside
   `find_best_configuration`.
2. **No largest-component rule, foreground or per-label.** The per-label form is
   the more dangerous and is the one a multiclass run would silently invoke.
3. **Small-component removal only with an mm³ threshold, justified by an
   audit**, and only ever *after* the raw prediction has been scored. Default:
   off.
4. **A fragment must be reconnected or kept, never deleted, if it plausibly
   belongs to a labelled vessel.** Deletion is the one irreversible option.
5. **Centerline reconnection is a downstream experiment, not part of the
   segmenter**, consistent with [[Training plan]] §4's position that graph
   reasoning is welcome downstream but must never be able to lose a vessel the
   voxel model found. Judge it on HD95/AHD and branch detection, not Dice.

## What this implies for [[Training plan]]

- §4's ban should name the mechanism (`nnUNetv2_find_best_configuration`
  applies this automatically; the criterion is mean Dice) so the ban is
  actionable.
- Add: per-label largest-component is explicitly included in the ban, because
  the multiclass run is where it does the most harm.
- Add a one-line post-processing policy: raw prediction is the artefact of
  record; any cleanup is a separate, separately-scored stage; deletion
  thresholds are in mm³.
- Record centerline reconnection (DPC-walk style) as a **downstream candidate**
  with the ASOCA ablation as its supporting evidence, and with the caveat that
  it has never been measured against an nnU-Net baseline.

Collected in [[Proposed changes]].
