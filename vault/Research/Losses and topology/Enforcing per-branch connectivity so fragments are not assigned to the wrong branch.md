---
aliases: [Per-branch connectivity, Intra-segment misclassification, Branch-class fragmentation, VTG-Net]
tags: [research, post-processing, topology, coronary, multiclass, evidence]
status: solid
updated: 2026-09-19
---

# Enforcing per-branch connectivity so fragments are not assigned to the wrong branch

[[Largest-component post-processing is wrong for coronaries]] covers the general
ban on keep-the-largest-component post-processing and surveys reconnection/gap-
bridging as an alternative. This note is about a distinct, multiclass-specific
failure that general topic did not cover: even when a fragment is *correctly*
detected as coronary lumen, in a per-branch multiclass model it can be **assigned to
the wrong branch class** — a piece of LAD labelled as a diagonal, or a fragment near
a bifurcation flipped between LCx and an obtuse marginal. This is a labelling error
along an existing connected component, not a missing-component error, and needs a
different fix.

## The failure mode is documented, at scale, in the nearest analogous multiclass vessel task

Retinal artery/vein (A/V) classification is the vascular multiclass problem with the
largest published literature on exactly this failure, because it has the same
structure: one connected vessel tree, voxel/pixel-wise per-class labelling, and two
or more classes that must not be assigned within the same physical vessel. The
literature's own name for it is *intra-segment misclassification* — the same anatomic
vessel receiving multiple class labels along its length.

- Mishra, Wang, Wei, Chen, Hu, *VTG-Net: A CNN Based Vessel Topology Graph Network
  for Retinal Artery/Vein Classification*, Front Med (Lausanne) 8:750396, 2021.
  States the failure directly, illustrated in their Fig. 1: CNN output shows
  **"multiple class assignment of a single vessel segment."** Their fix builds a
  topology-preserving graph from the CNN's features, runs a GCN over it, and fuses
  CNN and GCN predictions by an agreement-based voting scheme. Measured effect,
  classification accuracy:

  | Dataset | CNN only | + topology graph fusion |
  |---|---|---|
  | AV-DRIVE | 94.60 % | **98.11 %** |
  | Tongren | 93.81 % | **97.98 %** |

  +3.5 and +4.2 points from adding topology-aware correction on top of an otherwise
  unchanged per-pixel classifier — the largest single-mechanism gain found in this
  session's search on any vessel-labelling sub-question.
- Corroborating design pattern, not independently quantified this session: AV-casNet
  (found via search, not opened in full) uses the same two-stage shape — CNN
  segmentation first, a cascaded GNN to "refine vessel connectivity" second — echoing
  Hampe et al.'s coronary tree-labelling pipeline (see [[Downstream graph labelling
  of coronary branches is a second stage, never the segmenter]]) and the general
  backflow-tracing / topology-graph family surveyed under "Handling Bifurcation
  Points" in the retinal A/V literature: skeletonise, isolate vessel segments between
  bifurcation/crossing points, then classify or correct each segment as a whole
  rather than voxel-by-voxel, so that a segment cannot be split-labelled internally
  by construction.

Why this transfers to coronaries and not just conceptually: the mechanism producing
intra-segment misclassification in retina is the same one that will produce it in
our multiclass model — a per-voxel classifier has no explicit constraint that
"voxels connected along a single vessel share a label", so near a bifurcation, a
region of low contrast, or a calcified segment, the network's confidence can flip
class within what is anatomically one continuous branch. Coronary bifurcations
(LM→LAD/LCx, RCA→PDA/PLV) are exactly the geometry where this is most likely, because
that is where two branch classes are physically closest and most visually similar in
a small neighbourhood.

## Distinguishing this from the largest-component problem

The two failures are opposite in a precise sense and need different audits:

| | Largest-component problem | Intra-segment misclassification |
|---|---|---|
| What is wrong | A whole, correctly-labelled fragment is deleted | A correctly-detected fragment is mislabelled |
| Where it shows up | Binary or per-label post-processing that keeps one component | Anywhere two branch classes meet, especially bifurcations |
| Evidence for us | β₀ = 2.9–11.9 components on ImageCAS, no post-processing (BCS paper) | VTG-Net's +3.5–4.2 pt accuracy gain on retinal A/V |
| Fix family | Never delete; reconnect or keep and report | Topology graph correction over the labelled output |

A component-count metric (β₀, already proposed to the metrics owner via
`Handoffs.md`) will not catch intra-segment misclassification, because the fragment
is still there and still connected — it is simply the wrong colour. A dedicated
per-branch confusion check is needed: for each connected component of the raw
multiclass prediction, what fraction of its voxels carry each class label. A
component that is >90% one class with a small contaminating patch of a neighbouring
class at one end is the VTG-Net failure signature, and the [[Training plan]]'s
existing AHA-segment confusion matrix (evaluation section) is the right place to
surface it in aggregate, but only if it is computed per-component rather than
per-voxel-pooled, which pools the contamination away.

## What the fix would look like for this project, and what is unproven

1. **Do nothing beyond the segmenter's own class prediction, and measure whether it
   is a real problem here first.** No coronary-specific measurement of intra-segment
   misclassification rate exists in the sources opened this session — the VTG-Net
   evidence is retinal, not coronary, so the size of the effect on our task is
   **unverified by extrapolation**, not by direct measurement.
2. **If the multiclass baseline shows the failure** (visible directly in the
   per-component class-purity check above, or in AHA-segment confusion concentrated
   at anatomically adjacent branch pairs rather than spread uniformly), the
   evidenced fix is a downstream topology-graph correction stage — skeletonise the
   per-branch prediction, segment it into pieces between bifurcation/endpoints, and
   relabel each piece by majority vote or a small GNN over the piece's own geometry
   and image features, exactly Hampe et al.'s and VTG-Net's shared design. This is
   the same "downstream graph reasoning, never gating the voxel model's presence/
   absence calls" pattern [[Training plan]] §4 already sanctions and [[Downstream
   graph labelling of coronary branches is a second stage, never the segmenter]]
   documents — the correction stage only relabels voxels the segmenter already
   found, it never deletes or adds them.
3. **A cheaper first check**, worth doing before building any graph-correction
   stage: whether nnU-Net's own bifurcation-adjacent errors are dominated by
   intra-segment misclassification or by ordinary boundary noise. If the latter, a
   graph-correction stage is solving a problem that is not actually present at our
   resolution and label count, and the effort is better spent on the class-imbalance
   and sampling experiments in the sibling notes instead.

## What this implies for [[Training plan]]

1. **Add a per-component class-purity check to the evaluation plan**, alongside the
   AHA-segment confusion matrix already specified — this is the metric that would
   actually detect the failure this note describes, and nothing currently listed
   does. Flag to the metrics/evaluation owner via `Handoffs.md`-equivalent in this
   folder (see below) since `src/segtrain/metrics.py` does not yet compute
   component-level class purity any more than it computes β₀.
2. **Do not schedule a topology-graph correction stage before the multiclass
   baseline exists and the per-component check has run on it.** The evidence for the
   fix (VTG-Net, +3.5–4.2 accuracy points) is strong but off-anatomy; building the
   fix before confirming the failure is present would be solving an unmeasured
   problem.
3. **Keep this failure conceptually separate from the largest-component ban** when
   writing acceptance criteria — a model can pass a component-count check and still
   have this problem, and a fix for one does not fix the other.

Related: [[Largest-component post-processing is wrong for coronaries]],
[[Downstream graph labelling of coronary branches is a second stage, never the segmenter]],
[[Class imbalance in multiclass vessel segmentation]].
Collected in [[Proposed changes]].
