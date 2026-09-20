---
aliases: [GNN branch labelling, CPR-GCN, Anatomical labelling, Downstream graph reasoning]
tags: [research/architecture, gnn, graph, downstream, coronary, evidence]
status: solid
updated: 2026-09-19
---

# Downstream graph labelling of coronary branches is a second stage, never the segmenter

[[Training plan]] §4 rules out tree/graph-structured models as the *primary*
segmenter, but explicitly welcomes graph reasoning downstream — "branch naming on an
extracted centerline, reconnection post-processing" — provided it "must never be
able to lose a vessel the voxel model found." This note supplies the coronary
evidence for that downstream role, and shows precisely how the disqualifying failure
mode manifests when it is measured directly.

## The clean measurement: labelling accuracy tracks extraction accuracy, not the other way round

Hampe, van Velzen, Wolterink, et al., *Graph neural networks for automatic extraction
and labeling of the coronary artery tree in CT angiography*, J Med Imaging
(Bellingham) 11(3):034001, 2024, DOI
[10.1117/1.JMI.11.3.034001](https://doi.org/10.1117/1.JMI.11.3.034001). 104 CCTA
scans (two centres, Aalst and Amsterdam), 79 train / 25 test. Three-stage pipeline:
CNN-based centerline tracking initialises a graph, a graph-attention-network (GAT)
ensemble prunes false-positive segments (tree refinement), and a second GAT ensemble
assigns 10 AHA segment labels to the refined graph.

Tree extraction (centerline tracking, not full lumen segmentation) scored **recall
0.84, precision 0.87, F1 0.85** against reference centerlines. Anatomical labelling,
measured on the network's *own automatically extracted* trees, scored mean **F1 0.74**
across the 10 AHA segments (RCA 0.90, LAD 0.86, down to septal branches 0.54). The
paper then reports the number that matters most for this project's decision: **on
manually extracted (reference) trees, the identical labelling network reaches F1
0.95** — a 21-point gap attributable entirely to upstream extraction error. The
authors state directly that labelling is degraded specifically because septal
branches "are frequently missed during extraction" and because tracking occasionally
leaks past the ostium into the aorta, causing whole branches to be discarded by the
refinement stage. This is [[Training plan]] §4's disqualifying mechanism for
tree/graph *segmenters*, measured rather than argued: **a vessel the extraction stage
misses is never available to the labelling stage, and the labelling stage cannot
recover it no matter how good the graph network is.** The paper's own authors draw
the same conclusion — "improving tree extraction would improve performance of
anatomical labeling."

Two structural properties of this result matter for how the plan should use it:

1. **It validates using graph reasoning as a labelling layer on top of a strong
   upstream segmenter.** The labelling network's F1 on *correct* input (0.95) is
   high; the ceiling on the whole pipeline is set by what reaches the graph, not by
   the graph network's own capacity.
2. **It validates the plan's specific caution about never letting graph reasoning
   gate the voxel model's output.** Hampe et al.'s tree-refinement stage does
   exactly the disqualified thing at small scale — it discards graph nodes it judges
   spurious — and that is the step responsible for losing real branches (the septal
   and ostium-leak failures), not the labelling stage itself. If this project's
   downstream branch-labelling stage is ever built, the analogous refinement/pruning
   step is where a real vessel could be silently deleted, and it is the step to
   audit hardest.

## Corroborating design pattern: CPR-GCN and related methods condition labelling on both geometry and image evidence

Yang, Fu, Zhang, et al., *CPR-GCN: Conditional Partial-Residual Graph Convolutional
Network in Automated Anatomical Labeling of Coronary Arteries*, read as
arXiv:2003.08560 (a CVPR 2020 paper; full text did not extract cleanly this session
— **citation and design pattern only, quantitative numbers unverified pending a
clean re-fetch**). The stated design is to feed the labelling GCN both the
extracted centerline geometry (position, branch topology) and CT image features
along each segment ("branch size and spanning direction"), rather than geometry
alone, precisely because geometry-only labelling cannot resolve anatomically
ambiguous cases (e.g. a short, atypically-routed diagonal that geometry alone would
mislabel). This reinforces that any downstream labelling stage for this project
should have access to the original image, not just the segmentation mask — a
detail worth deciding before building one.

## What this implies for [[Training plan]]

1. **§4's downstream carve-out is well supported and the exact mechanism is now on
   record**: a 21-F1-point gap between labelling on reference vs. automatically
   extracted trees, on CCTA, is direct evidence that voxel-segmentation quality is
   the ceiling for any downstream graph-labelling stage, not the other way round.
   The practical reading for the plan's own sequencing (binary → multiclass → ResEnc,
   §3) is unchanged, but it sharpens the case for **not** building a graph-labelling
   stage before the voxel segmenter is solid: doing so earlier only measures how bad
   the pipeline's own extraction step is.
2. **If a downstream labelling/reconnection stage is ever built** (this project
   already needs per-branch class identity from the voxel model directly, so a
   separate labelling stage is not required for the core deliverable, but could be a
   QA or reconciliation layer), the failure to avoid is any pruning step that deletes
   a graph node/branch the voxel model found — same principle as the ban on
   largest-component post-processing in [[Largest-component post-processing is wrong
   for coronaries]], applied to the graph domain instead of the voxel domain.
3. **Feed image features, not just geometry, to any future labelling stage** — the
   CPR-GCN design pattern, corroborated qualitatively by the difficulty AHA-segment
   labelling has with anatomically ambiguous branches in Hampe et al.'s own lower-F1
   classes (septal, OM).
4. **This remains explicitly out of scope for the current multiclass task**: the
   plan already gets per-branch labels directly from the voxel model's classes, so
   graph labelling is a QA/analysis tool, not a pipeline dependency, consistent with
   §4's "welcome downstream" framing.

Related: [[Largest-component post-processing is wrong for coronaries]],
[[Binary-init fine-tuning and multi-task auxiliary heads for the multiclass model]].
Collected in [[Proposed changes]].
