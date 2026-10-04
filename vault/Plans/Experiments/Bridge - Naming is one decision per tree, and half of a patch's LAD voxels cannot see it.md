---
tags: [plans/experiment, branch-labelling, two-stage, topology, patch-context]
author: Bridge
round: 1
updated: 2026-10-04
---

# Naming is one decision per tree, and for half of a patch's LAD voxels that decision is out of view

## Question

If the 4-class labels are the binary lumen partitioned into LM / LAD / LCx / RCA (which is what
SegQueue asks annotators to do — "split an existing tree into LM / LAD / LCx / RCA", `docs/SERVER-SETUP.md`),
where in a case does the class decision actually live?

1. How separable are the left and right trees (connected components)?
2. What fraction of lumen voxels is near the LM bifurcation — the only place where a class boundary
   inside the left tree sits when every side branch inherits its parent's name?
3. For a patch-based direct multiclass net: how often does a training patch that contains an LAD or LCx
   voxel also contain that LM bifurcation, i.e. the evidence that decides the voxel's class?

## Method

- Cases: **155** random cases (c0000–c0999, shuffled with seed 0, as many as the shared CPU allowed);
  binary masks thresholded at 0.5.
- Components: cc3d, 26-connectivity; "tree" = component with ≥ 30 mm of TEASAR skeleton (kimimaro).
- LM bifurcation: from the frozen rule labeller
  ([[Bridge - A rule-based labeller names LM, LAD, LCx and RCA on our binary masks]]).
- Near-bifurcation fraction: mask voxels (via the skeleton vertex that owns them) within 3 mm / 5 mm of
  the bifurcation point.
- Patch context: for every LAD (LCx) voxel at offset Δ from the bifurcation, the probability that an
  axis-aligned cubic patch of side W placed uniformly at random among patches containing the voxel
  also contains the bifurcation = Π_axes max(0, 1 − |Δ_i|/W); averaged over voxels. W = 64, 96, 128 mm
  (Atlas's planner sweep puts nnU-Net's native-spacing patch at 48–112 mm per axis:
  [[Atlas - Every case has 0.5 mm slices and nnU-Net's own planner fixes the patch menu]]).
- Scripts: `experiments/Bridge/extract.py`, `evaluate.py`, `cohort.py`.

## Result

| Quantity (155 cases) | Value |
|---|---|
| Components ≥ 100 voxels: exactly 2 | 149 (96 %); 1 component (left+right fused): 2; 3+: 4 |
| Two largest components hold ≥ 99 % of mask voxels | 98.1 % of cases (≥ 95 %: 99.4 %) |
| Trees (≥ 30 mm skeleton): 2 / 1 / 3 | 116 / 2 / 2 of the 120 evaluated |
| Left vs right by tree centroid x | RCA Dice 1.000 in every case with two separate trees (n = 96 ImageCAS-X cases) |
| Voxels within 3 mm of the LM bifurcation | median **2.1 %** (p10 1.5 %, p90 2.9 %) |
| Voxels within 5 mm | median **3.6 %** (p10 2.6 %, p90 5.2 %) |
| LM length (ostium → chosen bifurcation, skeleton) | median 14.0 mm (p10 9.3, p90 20.8) |

Probability that a random patch containing an LAD / LCx voxel also contains the LM bifurcation:

| Patch side | 64 mm | 96 mm | 128 mm |
|---|---|---|---|
| LAD voxels | 0.33 | 0.47 | 0.56 |
| LCx voxels | 0.37 | 0.52 | 0.61 |
| LAD voxels farther than W from the bifurcation on some axis (never co-visible) | 10.1 % | 0.6 % | 0 % |

Delta's survey of 583 masks agrees on topology (75 % two components, ~2 % fused left+right, extra
components almost all specks): [[Delta - The binary masks are two clean trees, and a tight tree ROI is only 2-3x smaller than the volume]].

## What it implies

1. **The 4-class problem, given the binary tree, is a handful of discrete decisions per case**: which
   component is left (trivial: centroid x, never wrong when trees are separate), where the left ostium
   is, where the LM ends, and which child is LAD. Only ~2–4 % of voxels sit within 3–5 mm of the one
   internal class boundary. Everything else inherits its name through connectivity.
2. **A patch-based direct multiclass model has to name about half of its LAD/LCx training voxels
   without the deciding bifurcation in view** (0.47–0.52 at a 96 mm patch). It can still learn them
   from local anatomy (AV groove vs interventricular groove), so this is a risk, not a proof — but it is
   a structural reason to expect class swaps along long vessels, and a structural reason why a stage
   that sees the whole tree (graph) does not have that problem.
3. The two fused cases (left and right trees touching in the reference) are the main topological
   failure for a naming stage that assumes two trees; they must be detected (one tree carrying > 600 mm
   of skeleton) and split, or handed to a human.

## Limits

- 155 of 1000 cases. Bifurcation position comes from my labeller, which is right in ~93–95 % of
  cases (see the labeller note); wrong cases move the point.
- The patch model is idealised (uniform placement, axis-aligned, cubic). nnU-Net oversamples foreground
  (33 %) and uses anisotropic patches; the order of magnitude is the point.
