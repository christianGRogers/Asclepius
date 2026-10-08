---
tags: [plans, experiment, post-processing, bridging, convention, C4]
author: Delta
round: 4
updated: 2026-10-08
---

# Against the thick reference, bridging still joins false positives 6 times in 13

## Question

Round 3 ruling, C4. Delta suspected that the "false-positive" orphans joined by bridging were vessels
the *thin* ImageCAS-X reference never traced. If so, they would be true joins under the decided
*thick* reference, the original ImageCAS mask ([[Human decisions]] D0). Re-read the bridge audit
against the thick mask.

## Method

`experiments/Delta/c4_thick.py`. Same predictions, anchors and 3 mm bridging as
[[Delta - Real bridging on 17 nnU-Net predictions gains little alone, half its 3 mm joins are false positives, and gap-centred re-inference makes it work]]:
- the released ImageCAS-X binary nnU-Net, fold 0, tile step 0.75;
- 18 ImageCAS-X test cases, threshold 0.5, components < 100 voxels removed;
- deployable anchors from the TotalSegmentator aorta or the blood pool.

For each bridge, check whether the orphan touches the thin reference, whether it touches the thick
mask, and what fraction of its voxels lie inside the thick mask. Raw FP components are counted
against both references.

## Result

| | thin reference (ImageCAS-X) | **thick reference (decided)** |
|---|---|---|
| bridges made (3 mm), 18 cases | 13 | 13 |
| orphans touching no reference voxel (FP joins) | 5 | **6** |
| raw FP components per case (before any repair) | 1.11 | **1.22** |

- Of the 5 thin-FP joins, 2 become true under the thick reference: c0362 (88 % of the orphan inside
  the thick mask) and c0407 (92 % inside). The other 3 lie entirely outside the thick mask
  (c0113: 104 voxels; c0264: 690 voxels; c0464: 108 voxels).
- One join that was true against the thin reference touches nothing in the thick mask. ImageCAS-X
  traced a vessel that the original mask lacks.

## What it implies

1. **C4 is answered: the convention explains only part of it.** Under the binding thick reference,
   **6 of 13 joins (46 %) still attach a piece that touches no reference vessel**, about the same
   share as against the thin reference (5 of 13). Bridging's FP problem does not go away with the
   convention.
2. The A2 rules stay as they are: the raw FP gate is read before repair, and every bridge is audited.
   The A2 note that "P1 bridging is not expected to pass" stands on the decided reference.
3. Size does not separate the true joins from the false ones. FP orphans range from 104 to 1052
   voxels. No safe filter exists from this evidence. The Trillium run's audit, on a 4-class
   thick-trained model, is the remaining test.

## Limits

- One released thin-trained binary model, tile step 0.75, 18 cases and 13 bridges. Gap-centred
  re-inference bridges were not re-read here, because those fused probabilities were not saved.
  Trillium audits them against the thick reference directly.
