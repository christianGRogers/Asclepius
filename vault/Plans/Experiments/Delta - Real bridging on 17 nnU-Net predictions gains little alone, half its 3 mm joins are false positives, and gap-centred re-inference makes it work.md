---
tags: [plans, experiment, post-processing, topology, real-predictions, tree-f1]
author: Delta
round: 2
updated: 2026-10-04
---

# Real bridging on 17 nnU-Net predictions gains little alone, half its 3 mm joins are false positives, and gap-centred re-inference makes it work

## Question

The Round 1 ruling: the bridging number in Delta v1 (rooted recall 0.78 → 0.91) was an upper bound
from a gap-tolerant metric, not a measured repair. This note measures an **implemented** bridging step
on real predictions, including the false connections it makes, and tests one new step, **gap-centred
re-inference**.

## Method

- Predictions: ImageCAS-X's released binary nnU-Net (fold 0) on **17 ImageCAS-X test cases** that no
  fold saw. These are the 8 from [[Delta - A released nnU-Net cuts 3 of 8 test trees that Dice scores at 0.84-0.92]]
  plus 9 new ones, from 10 CTs downloaded for this round (c0846 is in E10 only, c0951 in neither — the
  run died). Same inference settings as E8: crop = reference bbox + 10 mm, tile step 0.75, no TTA.
- **4-class names are oracle names**: every predicted voxel takes the nearest reference class. The
  model is binary, so these tests measure connectivity, not naming. Real 4-class predictions do not exist
  yet; R1's validation fold must repeat this.
- Ostium and anchors come from
  [[Delta - Two cheap ostium rules find 116 of 116 true ostia, and their disagreement flags every miss]].
  The TotalSegmentator aorta is used for 4 cases and the blood-pool proxy for the rest. Reference ostia
  for tree-F1 are taken from these structures (pool: thickest endpoint near the pool). **Deployable
  anchors** are the 2 largest predicted components within 3 mm of the structure; no reference is used.
- **Bridging** (`postproc.bridge`): repeatedly join the nearest un-anchored component ≥ 100 voxels to
  the anchored set if the gap is ≤ d mm, using a straight tube of radius 1 voxel that takes the orphan's
  class. d = 1.5, 3 and 5 mm (`bridge_eval.py`).
- Each bridge is audited for three things:
  - **FP joined**: the orphan touches no reference voxel, i.e. a false-positive blob was attached.
  - **Cross-tree**: the orphan and the anchor point are on different trees (left vs right).
  - **Off-reference tube voxels**: tube voxels more than 1 mm outside the reference.
- **Gap-centred re-inference** (`regap.py`): for each un-anchored component ≥ 100 voxels within 15 mm
  of the anchored set, run the same network once more on a single 96 × 160 × 160 window centred on the
  gap midpoint. Then fuse the first-pass probability with the new one (mean, or max) inside that window,
  re-threshold, and optionally apply 3 mm bridging. 16 of the 17 cases (c0846 not reached).
- Scoring: tree-F1 at 0 and 1.5 mm tolerance, Dice, and FP components.

## Result

**Bridging alone (17 cases, first-pass prediction):**

| max gap | bridges | **FP blobs joined** | cross-tree | off-ref tube voxels | tF1@0 | **tF1@1.5** | FP components |
|---|---|---|---|---|---|---|---|
| none | 0 | – | – | 0 | 0.784 | 0.836 | 1.18 |
| 1.5 mm | 4 | 0 | 0 | 0 | 0.799 | 0.836 | 1.18 |
| 3 mm | 12 | **5** | 0 | 80 | 0.809 | 0.846 | 0.88 |
| 5 mm | 23 | **10** | 1 | 375 | 0.821 | 0.862 | 0.59 |

- Bridging at ≤ 1.5 mm does not change tF1@1.5 at all, because the metric already tolerates those gaps.
- Bridging at 3 mm gains +0.010 tF1@1.5. But **5 of its 12 joins attach a false-positive blob** to
  the tree, and that **lowers the FP-component count** from 1.18 to 0.88. Bridging hides FPs from the
  master's FP gate.
- Bridging at 5 mm gains +0.026 but makes 10 FP joins and 1 left-to-right join in 23 bridges.
- The 3 mm FP joins were orphans of 104–1052 voxels; the true joins were 396–3999 voxels. Size alone
  does not separate them.

**Re-inference (16 cases):**

| variant | Dice | tF1@0 | **tF1@1.5** | rooted@1.5 | FP comps (after) |
|---|---|---|---|---|---|
| first pass | 0.890 | 0.774 | 0.829 | 0.801 | 1.19 |
| + bridging 3 mm | 0.890 | 0.800 | 0.839 | 0.816 | 0.88 |
| re-inference (max) | 0.894 | 0.786 | 0.837 | 0.828 | 1.25 |
| **re-inference (max) + bridging 3 mm** | 0.894 | 0.815 | **0.854** | 0.848 | 0.81 |

- Per case, re-inference (max) + bridging 3 mm against the first pass:
  - c0407: 0.756 → **0.938**
  - c0113: 0.523 → **0.700**
  - c0675: 0.829 → 0.867
  - c0250: +0.002
  - c0526: +0.001
  - the other 11 cases changed by at most 0.001. **No case got worse.**
- Mean gain +0.025, bootstrap 95 % CI [0.000, 0.057]. Bridging alone gives c0407 0.783 and c0113 0.659.
  Re-inference narrows gaps into bridgeable range, and the two together do what neither does alone.
- Cost: 0–6 windows per case (mean 1.7), about 4 CPU-minutes per case here. On a GPU this is seconds.
- What is left unrepaired:
  - c0679 (0.236) and c0774 (0.670): long gaps, with correct ostia (verified in the ostium note).
  - c0526 (0.851): a 9 mm LCx gap.
  - These are model failures that no post-processing reaches.

## What it implies

1. The v1 claim is **revised down**. Implemented 3 mm bridging buys about +0.01 tF1@1.5 on real output,
   not +0.13. Half of its joins attach false positives. If FP components are counted after bridging, the
   master's FP gate is gamed.
2. So the **FP gate must be counted before bridging**, and every bridge must be reported. A bridge whose
   orphan has no support in a second look (re-inference) should not be made. This is a recipe change to
   the master's P1.
3. **Gap-centred re-inference is the step that makes repair work**: no case worse, large gains exactly on
   the cut trees. It is cheap and needs no training. It should be a candidate post-processing step,
   judged on R1's val fold by tF1 like P1–P3.
4. The remaining cut trees (3 of 16) are long gaps in thin distal vessels. Fixing them is a training
   problem (context, patch size, thin-vessel sampling), not a post-processing problem.

## Limits

- One released small-patch model (96 × 160 × 160), binary, thin convention, tile step 0.75. Part of the
  re-inference gain may come from the first pass using fewer overlapping windows than nnU-Net's default
  0.5. **The control (first pass at step 0.5 on the cut cases) was started but did not finish.** The
  master's 256³ patch may cut fewer trees and leave less to repair.
- Oracle names; 16–17 cases; the bootstrap CI touches 0.
- The blood-pool proxy anchors 13 of 17 cases, and TotalSegmentator only 4.
