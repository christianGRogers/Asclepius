---
tags: [plans, experiment, metrics, topology, evaluation]
author: Delta
round: 1
updated: 2026-10-04
---

# Dice cannot see the errors that break a coronary tree — and neither can per-class clDice

## Question

Which metric detects which failure? The candidate deciding metrics this round are mean per-class
Dice (Bridge v1) and macro per-class clDice (Atlas v1). If we corrupt real reference trees with the
errors a CNN makes — boundary erosion, breaks, lost distal branches, false-positive blobs, and
branch-label errors at the carina — how does each metric respond, and does a rooted, labelled
centreline metric (tree-F1, defined below) do better?

## Method

`experiments/Delta/perturb_metrics.py` (`treelib.py` helpers; summary `summarise_pert.py`).
Reference = ImageCAS-X lumen of each case with its segment labels mapped to 4 classes (subtree
convention: D→LAD, OM/IM/L-PDA/L-PLA→LCx, R-PDA/R-PLA→RCA). Cases **c0039, c0099, c0162, c0224,
c0291** (spread over ids; CPU-limited). Each perturbation is applied to the reference and the
corrupted copy is scored against the reference. Skeletons: skimage Lee 3D; graph in mm.

Binary corruptions (labels follow the voxels): `erode1` (one-voxel erosion); `dilate1`; `gaps5`
(5 cuts, ball r = 1.5 mm, at random centreline points with centre EDT < 0.75 mm — lumen ≤ ~3 voxels —
≥ 6 mm from any centreline end, so each cut severs); `gaps5_thick` (5 cuts, r = 2.5 mm, at points
with EDT ≥ 1 mm — proximal vessels); `drop_term30` (delete 30 % of terminal branches);
`thin_lost` (delete voxels whose nearest centreline point has EDT < 0.6 mm); `fp5` (5 blobs r = 2 mm,
5–11 mm from the tree). Label corruptions (mask unchanged): `carina5`/`carina10` (first 5/10 mm of
LCx called LAD); `side_swap` (largest side subtree off the LAD main path called LCx); `d1_as_lcx`
(the expert-labelled D1 called LCx); `lm_as_lad`; `islands` (five 3 mm stretches given a
neighbouring class).

Metrics: Dice; NSD@0.5 mm; binary clDice; macro per-class Dice; **macro per-class clDice** (centreline
of class c predicted as c, vs predicted class-c centreline inside reference class c); β₀ error
(26-connected components, |pred − ref|); per-class component excess; segment detection (reference
centreline segments ≥ 3 mm, ≥ 50 % covered); **rooted recall** (fraction of reference centreline lying
in a predicted component that contains a reference ostium — the thickest centreline endpoint, LM
end preferred); centreline label accuracy; and **tree-F1** = macro over classes of the harmonic mean
of *rooted, correctly-labelled* centreline recall and labelled centreline precision.

## Result (mean over cases; label rows over the cases where the structure exists)

| Corruption | Dice | macro Dice | NSD@0.5 | clDice | **per-class clDice** | β₀ err | rooted recall | **tree-F1** |
|---|---|---|---|---|---|---|---|---|
| none | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0 | 1.000 | 1.000 |
| erode 1 voxel | 0.638 | 0.643 | 0.922 | 0.931 | 0.947 | **36.6** | 0.615 | 0.803 |
| dilate 1 voxel | 0.745 | 0.751 | 0.996 | 1.000 | 1.000 | 0 | 1.000 | 1.000 |
| 5 thin breaks | **0.995** | 0.995 | 0.995 | 0.987 | **0.990** | 4.6 | 0.836 | 0.926 |
| 5 proximal breaks | **0.971** | 0.966 | 0.979 | 0.980 | **0.972** | 5.2 | **0.301** | **0.502** |
| 30 % terminal branches lost | 0.824 | 0.833 | 0.836 | 0.839 | 0.836 | 3.2 | 0.596 | 0.732 |
| thin tails lost | 0.970 | 0.974 | 0.972 | 0.907 | 0.929 | 34.0 | 0.576 | 0.778 |
| 5 false-positive blobs | 0.969 | 0.975 | 0.973 | 0.997 | 0.997 | 5.0 | 1.000 | **0.997** |
| carina: 5 mm LCx→LAD | 1.000 | 0.984 | 1.000 | 1.000 | 0.992 | 0 | 1.000 | 0.992 |
| carina: 10 mm LCx→LAD | 1.000 | 0.971 | 1.000 | 1.000 | 0.984 | 0 | 1.000 | 0.984 |
| side subtree → LCx | 1.000 | 0.959 | 1.000 | 1.000 | 0.941 | 0 | 1.000 | 0.941 |
| D1 → LCx (expert D1) | 1.000 | 0.971 | 1.000 | 1.000 | 0.950 | 0 | 1.000 | 0.950 |
| LM → LAD | 1.000 | 0.732 | 1.000 | 1.000 | 0.743 | 0 | 1.000 | 0.743 |
| 5 label islands | 1.000 | 0.982 | 1.000 | 1.000 | 0.983 | 0 | 1.000 | 0.983 |

(Per-class component excess: +1 for every label corruption, +10 for islands — the only number that
"sees" islands as islands.)

## What it implies

1. **Breaks are invisible to overlap metrics.** Five proximal breaks leave Dice at 0.97 and
   per-class clDice at 0.97 while 70 % of the tree is no longer connected to its ostium (rooted
   recall 0.30). On a single case (c0039) it is starker: Dice 0.971, per-class clDice 0.921, rooted
   recall **0.02**, tree-F1 0.16. A deciding metric that cannot tell a whole tree from a tree cut at
   the LM is the wrong deciding metric for a coronary model whose downstream uses (CPR, FFR-CT,
   per-vessel plaque) all walk the tree from the ostium.
2. **β₀ sees breaks but cannot weigh them**: 5 proximal breaks (+5.2) and 5 false-positive blobs
   (+5.0) score the same, and 5 distal breaks (+4.6) nearly so. Rooted recall separates all three
   (0.30 / 1.00 / 0.84).
3. **Label errors are seen equally by macro Dice, per-class clDice and tree-F1** (they are all
   per-class overlap at heart): tree-F1 adds nothing there and loses nothing.
4. **Boundary-only errors** (erode/dilate one voxel) move Dice by 25–36 points but leave centreline
   metrics near 1 *unless* they disconnect: on the thin ImageCAS-X lumen one voxel of erosion creates
   +37 components and tree-F1 falls to 0.80 — correctly, because the tree is now in pieces.
5. **tree-F1's blind spot**: false-positive blobs (0.997). It must be gated by a false-positive-
   component count, which is what the plan does.
6. Conclusion: decide on **tree-F1**, report Dice/NSD/clDice, β₀ against the reference's own count and
   FP components. Mean Dice (Bridge) and per-class clDice (Atlas) would both rank a model that cuts
   trees at the LM above a model that misses 30 % of distal branches (0.97 vs 0.83–0.84); tree-F1
   ranks them the other way (0.50 vs 0.73).

## Limits

- Five cases; the label rows on 3–4 cases (structures absent in some). Corruptions are idealised:
  real breaks are not uniform (see [[Delta - A released nnU-Net breaks coronary trees where vessels are thin, and the signal is still there]]
  for real ones).
- Ostium = thickest centreline endpoint (LM end preferred); the plan replaces this with the aorta
  contact rule. tree-F1 with no gap tolerance treats a 1-voxel gap as a break.
- Done on the thin ImageCAS-X lumen; on our ~2× thicker masks erosion is far less destructive
  (c0000, our mask: erode 1 voxel → 0 extra components).
