---
tags: [plans, experiment, metrics, topology, imagecas-x, calibre]
author: Delta
round: 1
updated: 2026-10-04
---

# Two references of the same vessels agree on centrelines, not on voxels

## Question

1. **Calibre.** How much of the coronary tree is thin — what fraction of centreline length runs
   through lumens < 4 voxels across — in our masks and in the ImageCAS-X lumen?
2. **Metric robustness.** Our project's binary masks (original ImageCAS labels, which the team
   will split into 4 classes) and ImageCAS-X's expert lumen describe the *same* vessels with
   different boundary conventions. Which metrics register that they are the same tree, and which
   only measure the convention? A decisive metric should not be dominated by a convention choice
   the project has not even made yet.

## Method

`experiments/Delta/convention_metrics.py` (summary `summarise_conv.py`; area check
`area_diam.py`). 15 cases with both references (c0000 + every 33rd ImageCAS-X case from c0006;
list in the script call: c0000 c0006 c0050 c0093 c0131 c0172 c0212 c0263 c0306 c0345 c0388 c0434
c0473 c0516 c0556; run stopped at 15 of 25 for CPU). On a common crop: Lee skeleton of each
reference (skimage), EDT at centreline voxels; local diameter = 2·EDT − in-plane spacing (EDT to
the nearest background voxel centre overshoots the boundary by half a voxel); centreline length
from the 26-graph in mm. Agreement: Dice, NSD at 0.5 and 1.0 mm, clDice (our mask as "prediction",
ImageCAS-X as reference), centreline-in-other-lumen each way, centreline within 1 mm of the other
lumen, and skeleton-segment (≥ 3 mm) detection each way. Area check: 2·√(V/πL).

## Result

**Calibre** (median over 15 cases [IQR]):

| | our masks (orig) | ImageCAS-X |
|---|---|---|
| centreline length | 866 mm [634–1086] | 707 mm [613–742] |
| median local diameter (EDT) | 2.64 mm | 1.32 mm |
| area-equivalent mean diameter (mean of 15) | 3.39 mm | 2.04 mm |
| length in lumen < 3 in-plane voxels | 2.5 % | 32 % |
| length in lumen **< 4 voxels** | **3.6 %** [1.7–9.7] | **65 %** [57–66] |
| length in lumen < 6 voxels | 25 % | 87 % |
| length in lumen < 2 mm | 15 % | 83 % |
| skeleton segments ≥ 3 mm | 24 | 14 |

(EDT-based diameters are biased low relative to area-equivalent ones; the ranking and the ~0.6×
ratio are robust to the choice.)

**Agreement between the two references** (median [IQR], min):

| Metric | value |
|---|---|
| Dice | **0.42** [0.37–0.47], min 0.25 |
| NSD @ 0.5 mm | 0.17 |
| NSD @ 1.0 mm | 0.70 |
| clDice | **0.80** [0.78–0.83] |
| ImageCAS-X centreline inside our mask | **0.90** [0.86–0.93] |
| ImageCAS-X centreline within 1 mm of our mask | 0.92 |
| ImageCAS-X segments found in our mask | 0.92 |
| our centreline inside ImageCAS-X lumen | 0.74 |
| our segments found in ImageCAS-X | 0.66 |
| centreline length ratio ours / theirs | 1.21 |

## What it implies

1. **On ImageCAS-X's convention, two thirds of the tree is a thin-structure problem**: 65 % of
   centreline length runs through lumens under 4 voxels across, which is exactly where one voxel
   of under-segmentation disconnects a vessel (erosion by one voxel gives +50 components on c0039:
   [[Delta - Dice cannot see the errors that break a coronary tree]]). On our own masks' convention
   it is 4 %. Topology risk is therefore mainly a property of the **label convention**, and it must
   be re-measured on the team's labels before deciding how much topology machinery to keep.
2. **Voxel metrics score the convention, centreline metrics score the tree.** The two references
   agree at Dice 0.42 (NSD@0.5 mm 0.17) while 90 % of ImageCAS-X's centreline lies inside our
   mask and 92 % of its segments are found. A model judged by Dice against one convention and
   trained on the other would look broken while finding every vessel. The deciding metric must be
   centreline-based; Dice/NSD are reported, not decided on.
3. **Our masks contain ~21 % more centreline and ~35 % of their segments are not in ImageCAS-X**
   (extra distal/side branches, plus skeleton spurs of a fatter mask). "Branch detection" measured
   against ImageCAS-X would penalise a model for vessels our team will label; the evaluation
   reference must be the team's labels once they exist, with ImageCAS-X as the interim reference.

## Limits

- 15 cases. The skeleton segment counts include spurs, which fatter masks produce more of.
- clDice here is the binary version; class-wise centreline metrics are analysed in the perturbation note.
- Diameter estimates at 0.35 × 0.35 × 0.5 mm are coarse for sub-2 mm vessels (one voxel ≈ 25 %).
