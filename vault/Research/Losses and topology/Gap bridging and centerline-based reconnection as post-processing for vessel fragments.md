---
tags: [research/loss, post-processing, gap-bridging, centerline, topology]
status: solid
updated: 2026-09-20
aliases: [Gap bridging, Centerline reconnection, DPC-walk, Fragment reconnection]
---

# Gap bridging and centerline-based reconnection as post-processing for vessel fragments

[[Training plan]] §4 explicitly rules out graph-structured *primary* segmenters but explicitly welcomes graph-based *downstream* processing. This note examines gap bridging and centerline-based reconnection as post-processing candidates, with measured results from the literature.

## The problem: vessel fragments and breaks

The voxel segmentation model produces a binary (or multiclass) probability map. After thresholding and connected-component analysis, gaps appear when:
1. A thin distal branch is predicted below threshold in a short segment (partial volume, low contrast).
2. A bifurcation region confuses the model: branches split but the junction is misclassified.
3. A stenosis or calcification causes the network to drop confidence locally.

[[Training plan]] §4 bans largest-component post-processing (which would delete real branches), so fragments remain. Gap bridging aims to **reconnect fragments that are spatially close and topologically plausible**, without hallucinating new vessels.

## Centerline-based reconnection: DPC-Walk framework

The most recent coronary-specific work is the **CorSegRec framework** (Qiu et al., three-stage approach: segmentation, reconnection, reconstruction):

**Stage 1: Voxel segmentation** — standard 3D nnU-Net or ResUNet.

**Stage 2: DPC-Walk reconnection** — Distance-Probability-Cosine walk:
- Extract centerline from the binary segmentation mask via skeletonization.
- For each disconnected fragment, identify its endpoint.
- Initialize a local search around that endpoint using a "DPC" cost function combining:
  - **Distance** to the nearest connected component.
  - **Probability** (confidence from the network's output logits, not just the thresholded mask).
  - **Cosine** similarity of the local direction (the predicted direction matches vessel trajectory).
- Walk iteratively from endpoint toward the nearest fragment, updating the path if the cost improves.

The improved version (Qiu et al. 2025) handles "long-distance reconnection" by expanding the neighborhood and allowing reconnections between distant fragments if topologically plausible.

**Measured results on ASOCA (Atlas Segmentation of Coronary Arteries)**:
- Baseline segmentation (ResUNet): 87.13 % Dice, 5.06 mm HD95.
- After DPC-Walk reconnection: **88.53 % Dice, 1.07 mm HD95** (ASOCA).
- On PDSCA (public dataset): **85.07 % Dice, 1.63 mm HD95**.

The **1.4 percentage point Dice gain and 4–3.4 mm HD95 improvement** is substantial, and the HD95 drop (from 5.06 to 1.07 mm) directly reflects the gap-bridging effect.

**Ablation detail (Table 6 from the paper, reconnection accuracy alone)**:
- DPC approach: **92.22 % reconnection accuracy, 98.20 % reconnection sensitivity, 82.79 % specificity**.
- This means the algorithm successfully reconnects 92 % of truly-disconnected fragments while false-reconnecting only ~17 % of unrelated fragments.

**Caveats:**
- Measured on ASOCA only (80 training, 20 test cases), a single dataset, no cross-dataset generalization shown.
- The framework is three-stage, so the DPC-Walk gain cannot be isolated from the reconstruction stage (Stage 3).
- No direct comparison to other gap-bridging methods; no ablation showing DPC vs simpler greedy distance-based reconnection.

## Other centerline-based approaches (non-coronary)

**Automatic retinal blood vessel gap correction (Amanatiadis et al., 2019)**:
- Skeletonize the segmentation; identify endpoints of disconnected skeletons.
- Use random-walk diffusion on the image to find paths between endpoints, weighted by vessel probability.
- Reconnect if random-walk confidence exceeds threshold.
- Tested on retinal images, not quantified in isolation but claimed to reduce "discontinuities in extracted vessel trees".

**Brain vessel centerline extraction (Zheng et al., 2025)**:
- Extract centerline using thinning; identify disconnected branches.
- Use 3D morphological reconstruction to expand the skeleton and fill small gaps.
- Closing operation (dilation + erosion) to bridge gaps < 5 voxels.
- No direct Dice improvement reported; the method is for centerline extraction, not segmentation improvement.

## What this implies for [[Training plan]]

1. **DPC-Walk is the only coronary-CCTA-measured gap-bridging approach**, and it is a **candidate second-stage post-processing experiment**, not part of the baseline. Do not schedule it ahead of the Skeleton Recall loss experiment (§5); run the baseline model, measure fragmentation (β₀ component count), and decide if gap-bridging is needed.

2. **If the multiclass baseline shows fragmentation (β₀ >> expected anatomical count)**, implement DPC-Walk as a paired post-processing run: same fold, same test cases, apply the CorSegRec three-stage pipeline to the baseline predictions. Measure the impact on Dice, HD95, component count, and per-class connectivity. The ImageCAS cohort differs from ASOCA (0.35 mm vs ASOCA's typical slice thickness, different scanner), so coronary-specific validation is needed.

3. **DPC-Walk requires:**
   - Predicted probability map (which nnU-Net produces: the softmax logits).
   - Segmentation mask (binary threshold, e.g., 0.5).
   - Centerline extraction (scikit-image skeletonization or similar).
   - The authors' code at the CorSegRec repository (check if it is open-source and compatible with ImageCAS preprocessing).

4. **Do not assume gap-bridging will solve all fragments**. The DPC-Walk specificity is 82.79 %, meaning ~17 % of false-reconnections still occur. The method is best for **bridging short gaps** (sub-5-voxel breaks); for long disconnections or ambiguous bifurcations, no post-processing can recover what the voxel model did not find.

## What this implies for [[Proposed changes]]

- Add to §4 "Graph reasoning welcome downstream": "**Centerline-based gap bridging (DPC-Walk framework)** is a candidate post-processing stage if the multiclass baseline exhibits excessive fragmentation (β₀ > 2× expected anatomical branch count). Measured on ASOCA: +1.4 Dice, −4 mm HD95 over baseline. Conditional on fragmentation, not scheduled."

- Add to §5 as a conditional experiment: "If baseline component count exceeds threshold, apply CorSegRec DPC-Walk to best validation checkpoint and evaluate on test fold. Measure Dice, HD95, β₀, and per-class connectivity; accept only if Dice gain >0.5 pp and component count moves toward expected anatomy."

Collected in [[Proposed changes]].
