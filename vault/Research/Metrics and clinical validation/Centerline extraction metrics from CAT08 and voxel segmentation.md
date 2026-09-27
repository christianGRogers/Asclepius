---
tags: [research, evaluation, metrics, coronary, centerline, cat08, literature]
status: evidence-collected
updated: 2026-09-20
aliases: [CAT08, Centerline metrics, Overlap accuracy, OTF, Accuracy Inside]
---

# Centerline extraction metrics from CAT08 and voxel segmentation

Whether centerline extraction accuracy metrics from the CAT08 2008 challenge—overlap, overlap-until-first-error, accuracy-inside—are applicable to voxel segmentation projects, or whether they are task-orthogonal.

**Short answer.** CAT08 (Schaap et al. 2009, Med Image Anal) defined three metrics for **1D centerline path tracking**, not voxel segmentation: **overlap accuracy** (what fraction of the reference centerline is within a distance tolerance of the prediction), **overlap-until-first-error** (OTF, at what point along the vessel does tracking fail), and **accuracy-inside** (average distance within the region the tracking claims). These metrics answer "did you find the path correctly" and are fundamentally different from voxel overlap metrics (Dice/IoU), which answer "did you get the boundary right." Applying CAT08 metrics to voxel predictions requires (a) extracting a centerline from the voxel prediction via skeletonization, (b) point-sampling and distance-to-reference computation, and (c) a re-interpretation of distance tolerances for voxel data. CAT08 itself is likely **undownloadable** as of 2026 (original host unreachable per secondary sources), making it an impractical direct benchmark. **clDice** (centerline Dice) is the modern analogue for voxel segmentation; it measures centerline overlap without requiring explicit path tracking.

## CAT08 challenge metrics

From Schaap et al. 2009 (Med Image Anal 13(5):701–714), the Rotterdam Coronary Artery Algorithm Evaluation Framework defined three metrics for **manually-extracted reference centerlines** (1D polylines with radius at each point) and **algorithm-produced centerlines**:

### 1. Overlap accuracy

- **Definition**: What fraction of the reference centerline lies within a distance tolerance (e.g., 2 mm) of the closest point on the prediction centerline?
- **Formula**: Overlap(τ) = (number of reference points within τ of prediction) / (total reference points)
- **Result**: Reported as % at multiple tolerances (e.g., overlap at 1 mm, 2 mm, 3 mm, 5 mm)
- **Interpretation**: Measures whether the algorithm "found the path" rather than whether it got the exact boundary

### 2. Overlap-until-first-error (OTF)

- **Definition**: Following the reference centerline from the ostium distally, at what distance along the reference path does the prediction fail to stay within the tolerance?
- **Formula**: OTF(τ) = (distance along reference from start to first out-of-tolerance point) / (total reference path length)
- **Result**: Reported as % path length; higher = the algorithm tracked further before failing
- **Interpretation**: Sensitivity to distal-tracking failure; a prediction that finds the proximal vessel but misses the distal third will have low OTF

### 3. Accuracy-inside (AI)

- **Definition**: For points on the reference centerline that are within tolerance of the prediction, what is the average distance to the prediction centerline?
- **Formula**: AI(τ) = mean distance of in-tolerance reference points to prediction
- **Result**: Reported in mm; lower = more accurate centerline placement
- **Interpretation**: When the algorithm "found" the path (within tolerance), how precisely did it track?

CAT08's test set was small: **8 training CCTA scans with 32 reference centerlines, 24 test scans with 96 centerlines** (128 total), each with 4 manually-labeled vessel centerlines (RCA, LAD, LCx, one large side branch).

## Why CAT08 metrics do not directly apply to voxel segmentation

1. **Different measurement object**: CAT08 measures a 1D path (polyline with radius); voxel segmentation produces a 3D binary mask. Comparing them requires a conversion step (skeletonization → centerline extraction), which introduces an additional source of error.

2. **Distance tolerance is ambiguous for voxels**: CAT08's 2 mm tolerance is a distance from the reference centerline to the prediction centerline (1D-to-1D). For voxel segmentation, "within 2 mm" is ambiguous:
   - Distance from reference boundary to prediction boundary (voxel surface distance)?
   - Distance from reference centerline (if extracted via skeletonization) to prediction centerline?
   - The two can differ substantially for a tube of varying radius.

3. **OTF detection requires explicit path tracking**: OTF measures the point where tracking "fails," which requires a directed traversal from ostium to distal. A voxel prediction that has the right volume but a discontinuous or bifurcated shape does not fail "at" a particular point; it fails everywhere simultaneously. OTF is not defined for a binary mask.

4. **Loss of intermediate structure**: Voxel-to-centerline conversion via skeletonization can introduce artifacts (centerline branching where the reference centerline is continuous, or vice versa). CAT08's tolerance-based scoring would penalize these skeleton artifacts, not the underlying voxel prediction quality.

## The modern analogue for voxel segmentation: clDice

**Centerline Dice (clDice)** (Moccia et al. 2018, "Towards Automatic Coronary Calcium Scoring in a Screening Study with Low-Dose Chest CT," IEEE TMI; further developed in 2020s vessel-segmentation literature) directly measures centerline overlap **on voxel predictions**:

1. Extract the centerline from both reference and prediction voxel masks via skeletonization (Euler characteristic = number of connected components = number of "skeleton trees")
2. Compute Dice on the centerline skeletons: clDice = 2 × (overlap of skeletons) / (reference skeleton + prediction skeleton voxels)
3. Interpret as: "did you find the path?" independent of boundary accuracy

clDice is recommended by Metrics Reloaded ([[Which metrics to report for thin tubular multiclass segmentation]]) for tubular structures, and [[Training plan]] already includes it in the evaluation section.

### Why clDice is better than CAT08 for this project

- Operates on voxel predictions directly; no conversion needed
- Well-defined distance tolerance (implicit in skeletonization neighborhood)
- Reported on the same objects (voxel masks) as Dice/NSD/HD, making it easy to compare
- Modern implementations are standardized (skimage `skeletonize_3d`, harmonic mean of forward/backward overlap)

### CAT08-style stratification on clDice

The *idea* behind OTF—"at what point along the vessel does the model fail?"—can be adapted to clDice:

- Extract centerlines from both reference and prediction
- Traverse from ostium distally along the reference centerline
- At each point, check whether the prediction's skeleton is within a distance threshold
- Report the % path length where prediction and reference overlap

This is a **directed-overlap metric**, distinct from clDice (which treats overlap symmetrically). It has been used in recent vessel-segmentation literature (e.g., TopCoW's "centerline overlap" in [[How to measure branch detection and score absent branches]]), but is not standard.

## CAT08 availability and relevance

From [[Public coronary CCTA datasets]], the original CAT08 host (coronary.bigr.nl/centerlines) is reported as **unreachable** in a 2023-era paper. The dataset is effectively **retired for new work** as of 2026:

- No direct benchmark available for download
- Papers citing CAT08 are 2008–2015 vintage (mostly centerline-extraction papers)
- Any contemporary project aiming to reproduce CAT08 results would need to either (a) contact the original authors for archival data or (b) find an intermediate source (a paper that republished the data)

**Not recommended** as a direct benchmark for this project.

## What this implies for [[Training plan]]

1. **Do not cite CAT08 as a benchmark for voxel segmentation metrics.** CAT08's overlap/OTF/AI metrics are for centerline evaluation, not voxel evaluation. If centerline-extraction evaluation becomes a goal, use **directed-overlap** or **clDice** instead.

2. **clDice is the voxel-segmentation analogue**: use clDice as the centerline-overlap metric per-branch, reported alongside Dice. It is already included in [[Training plan]]'s evaluation section.

3. **For CAT08-style "path failure" detection**: if the model is expected to track the entire vessel from ostium to distal, a directed-overlap metric can measure "what % of the reference path does the prediction overlap within a tolerance." This is distinct from clDice and answers a different question ("was the path continuous?"). Consider reporting it per-branch if branch connectivity matters downstream (see [[Topology and connectivity metrics for coronary trees]]).

4. **Centerline extraction as a downstream task** (if branch naming or FFR-CT input generation needs extracted centerlines): a separate centerline-extraction step is needed after voxel segmentation, not substituted by CAT08 metrics on the voxels themselves. Document this as a separate evaluation.

See [[Which metrics to report for thin tubular multiclass segmentation]], [[Topology and connectivity metrics for coronary trees]], [[How to measure branch detection and score absent branches]], [[Public coronary CCTA datasets]], and [[Proposed changes]].
