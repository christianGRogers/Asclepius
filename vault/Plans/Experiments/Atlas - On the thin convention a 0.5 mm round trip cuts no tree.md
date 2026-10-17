---
tags: [plans/experiment, resampling, spacing, topology, tree-f1, amendment-a5]
author: Atlas
round: 2
updated: 2026-10-04
---

# On the thin convention, a 0.5 mm round trip cuts no tree

## Question

Ruling §4.4 and amendment A5: if the humans choose the expert lumen (option A), the labels are thin; 65 % of
ImageCAS-X centreline sits in lumen < 4 voxels across. Does training and predicting at 0.5 mm isotropic then cost
**connectivity**, i.e. cut trees in a way tree-F1 sees? The network-level answer needs a GPU (ablation A1). The
target-level answer does not: if resampling the reference itself to 0.5 mm and back cuts the tree, no 0.5 mm model
can do better.

## Method

- Cases: the **10 ImageCAS-X cases with the finest in-plane spacing** (0.289–0.318 mm), i.e. those that 0.5 mm
  resamples most, chosen from the header table before looking at any result. A further 12 random cases were queued;
  this note reports what had finished.
- Reference: Delta's loader, `perturb_metrics.GT(case, 'icx')`. That is the ImageCAS-X lumen with the 4-class subtree
  mapping, the thin option-A target, cropped with a 12 mm margin.
- Round trip: one-hot of the 5 labels (incl. background) → linear resample to T mm isotropic → linear back to the
  native grid → argmax. This is nnU-Net's own path for resampling segmentations and predicted probabilities. T = 0.5
  and 0.8 mm (reference).
- Scored with Delta's `perturb_metrics.score` against the original: **tree-F1 at zero gap tolerance**, which is
  stricter than the 1.5 mm decisive version; also rooted recall, β₀ error, per-class component excess, per-class
  clDice, macro Dice, swap rate.
- Delta's code imported read-only. Script `experiments/Atlas/thin_roundtrip_tf1.py`, summary `summarise_thin.py`.

## Result

| | 0.5 mm: mean | 0.5 mm: worst case | 0.8 mm: mean | 0.8 mm: worst case |
|---|---|---|---|---|
| **tree-F1 (0 mm tolerance)** | **0.999** | **0.995** | 0.980 | 0.935 |
| tF1 recall (named + rooted) | 0.999 | 0.994 | 0.966 | 0.895 |
| rooted recall | 0.999 | 0.992 | 0.961 | 0.863 |
| per-class clDice | 0.999 | 0.995 | 0.990 | 0.980 |
| macro Dice | 0.994 | 0.988 | 0.901 | 0.879 |
| β₀ error | 0.1 | 1 | 2.0 | 7 |
| cases with tF1 < 0.99 | 0 / 10 | | 5 / 10 | |

## What it implies

1. **At 0.5 mm the thin tree survives intact**, even in the cases resampled most (0.29 mm pixels): no case loses
   more than 0.5 % of rooted, correctly named centreline, and at most one extra component appears. The decisive
   metric has essentially no target-level resolution penalty at the master's spacing.
2. **At 0.8 mm half the cases are cut** (β₀ up to +7, rooted recall down to 0.86) while per-class clDice stays at
   0.98–0.99. This is the failure tF1 exists to see, and it reproduces at target level the ImageCAS finding that
   coarse inputs cost accuracy.
3. Under option A the spacing ablation A1 is still mandatory (A5), because the network may use sub-0.5 mm detail
   the target does not need. This note removes the strongest a-priori reason to expect 0.5 mm to lose: the target
   itself does not lose.

## Limits

- 10 cases, chosen as the hardest for 0.5 mm, not representative. Random cases resample less, so they should do
  better.
- Target level only. A network at 0.5 mm sees an image with no signal above 1 cycle/mm
  ([[Atlas - Resampling to 0.5 mm isotropic loses nothing measurable, 0.7-0.8 mm does]]), but whether it *segments*
  thin distal trunks as well as a native-spacing network is A1's question.
- Delta's ostium definition (thickest endpoint) is used here. Since the round trip barely moves the LM ends, it does
  not matter for this comparison.
