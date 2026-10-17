---
tags: [plans, candidate, tree-f1, ostium, qa, round5]
author: Delta
round: 5
version: 6
updated: 2026-10-10
---

# Delta v6: the post-processing thesis is closed; what remains is the metric that decides

## 1. Decision: improve, by narrowing (not restart)

My thesis since v1 has been that the master recipe needs connectivity post-processing, which I tested in three forms:

- gap-centred re-inference (P1′);
- bridging (P1);
- label repair (P2).

On the master model the pre-registered test failed for all three ([[Delta - Trillium P1′ result on the master model]]):

| Step | C2 result (n = 27 clean cases) |
|---|---|
| P1′ | +0.0007 [−0.0061, +0.0059]; 9 cases worse, 3 of them by more than 0.01 |
| P1 bridging alone | +0.0002 |
| P2 label repair | 0 |
| P1′, primary read (`pool_thick` roots, unflagged) | −0.0017 |

By my own rule all three leave the recipe. A restart would mean finding a new candidate step. The evidence says there is none to find in post-processing:

- The master model rarely cuts a correctly rooted tree: about 0.004 tF1 per case on Atlas's val.
- The 1.5 mm tolerance already forgives what short bridges join.

What survives is the part of my work the decisions rest on: the deciding metric. v6 keeps only that.

## 2. Recipe changes

1. **Remove P1, P1′ and P2 from the master's inference.** nnU-Net's default inference (tile step 0.5) stands. No switch is kept: an unused option invites post-hoc use.
2. **Keep the A2 QA in full:**
   - the FP gate on the raw prediction;
   - the bridge-audit record, for any analysis that bridges.
3. **A1, aorta-first per side (as proposed in v5, now validated and implemented).**
   - The tF1 ostium is the reference centreline voxel nearest the TotalSegmentator aorta, per tree component and side, with `thick` and `pool_thick` as the cross-check. Flagged trees go to a human.
   - On 84 thick-reference cases (160 expert ostia) this rule gets 139 right, against 125 for `thick`. It fixes all 11 misplaced RCA roots in Atlas's val. 15 of its 21 misses are flagged; 6 are silent, 4 of those by 5.0–5.3 mm.
   - It is `segtrain.tf1.find_ostia`, with tests.
4. **No decision table is read on an absolute tF1 that lacks aorta masks (A1a).**
   - TotalSegmentator takes about 40 s per CT on CPU. Atlas's val (softmax kept on $SCRATCH) should be re-scored before R1's numbers are compared with any threshold.
   - The 0.846 is a lower bound; the estimate is 0.87–0.90.
5. **Evaluation hygiene (new).**
   - A missing input is a fault, never a smaller test set. My job silently dropped 17 of 80 open cases because the ImageCAS-X fetch had been interrupted; `trillium/delta` now fails instead.
   - Every evaluator should report n against the published split (`trillium/sealed_test.json`) and refuse if they differ. I propose the master adopt this as a rule.

## 3. What I offer next (CPU, no GPU)

| Item | Why | Cost |
|---|---|---|
| Re-score Atlas's R1 val with aorta-rule `segtrain.tf1` | Turns the provisional 0.846 into a number that can decide | TotalSegmentator on 80 CTs (about 1 h) plus scoring, on the cluster where the softmax lives |
| FP census tool in `segtrain.tf1` | Atlas's FP census needs, per FP component: size, distance to the tree, overlap with ImageCAS-X, mean softmax. That is the plain-function extension of `fp_components` | about 1 day; the API is additive |
| A human-review list of flagged ostia per evaluation | A1's flags only help if somebody looks | minutes per run |

## 4. Evidence

| Claim | Evidence |
|---|---|
| P1′ / P1 / P2 fail on the master model | [[Delta - Trillium P1′ result on the master model]] |
| Connectivity headroom of 0.004 per case; 13 of 17 cuts are ostium artefacts; the aorta rule validated | [[Delta - On the thick reference the cheap ostium rules miss 1 in 8 ostia silently, which made 13 of the 17 cut trees]] |
| The one tF1 implementation | `src/segtrain/tf1.py`, `tests/test_tf1.py`; [[Delta - Implementation of tf1]] |

## 5. Risks

| Risk | Response |
|---|---|
| A future model, e.g. one with a smaller patch or after an ablation, cuts trees again | The raw gate and the "cut tree on validated ostia" count will show it. P1′ code stays in `trillium/delta` as an experiment, not in the recipe |
| TotalSegmentator is unavailable at some site | tF1 is reported as provisional and decides nothing (A1a) |

## 6. Changes since v5

- P1′, P1 and P2 are withdrawn, on the pre-registered result.
- A1 is aorta-first per side, now validated on 84 cases and implemented.
- Evaluation-hygiene rule added; the 17-case drop is explained and fixed.
- Next work offered: the aorta re-score of R1 and the FP census tool.
