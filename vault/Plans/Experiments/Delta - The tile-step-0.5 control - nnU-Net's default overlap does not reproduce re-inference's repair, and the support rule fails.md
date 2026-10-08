---
tags: [plans, experiment, control, post-processing, topology, real-predictions]
author: Delta
round: 3
updated: 2026-10-08
---

# The tile-step-0.5 control: nnU-Net's default overlap does not reproduce re-inference's repair, and the support rule fails

## Question

Round 2 ruling, C1. The gain from gap-centred re-inference (P1′) was measured on first passes at
tile step 0.75, which is cheaper than nnU-Net's default of 0.5. Is that gain just what the default
overlap recovers anyway? A second question is whether the support rule — bridge only orphans that
the second look predicts again — blocks the false-positive joins.

## Method

- **Model and setup.** Same model, crop and scoring as in
  [[Delta - Real bridging on 17 nnU-Net predictions gains little alone, half its 3 mm joins are false positives, and gap-centred re-inference makes it work]]:
  the released ImageCAS-X binary nnU-Net, fold 0, oracle names, thin ImageCAS-X reference, and
  blood-pool or TotalSegmentator anchors.
- **Cases.** The 4 test cases whose trees were cut and repaired: c0407, c0113, c0675 and c0526.
- **First pass.** Re-run at tile step **0.5** (`nnunet_infer.py`, output `nnpred05/`).
- **Same repair as before.** `regap.py`: gap-centred windows, max fusion, then 3 mm bridging. The
  support-gated variant is added, with a per-bridge audit of whether the orphan touches the reference.
- **Re-runs.** The step-0.75 cases were re-run with the audit included (`regap_v3.jsonl`).
- **Compute notes.** About 17–26 CPU-minutes per case at step 0.5. Several runs were killed by
  out-of-memory events on the shared machine and repeated.

## Result

tF1 @ 1.5 mm:

| case | 0.75 first | **0.5 first** (default) | 0.75 + P1′ + bridge | **0.5 + P1′ + bridge** | 0.5 + P1′ + support-gated bridge |
|---|---|---|---|---|---|
| c0407 | 0.756 | 0.761 | 0.938 | **0.938** | 0.806 |
| c0113 | 0.523 | 0.521 | 0.700 | **0.698** | 0.698 |
| c0675 | 0.829 | 0.834 | 0.867 | **0.902** | 0.902 |
| c0526 | 0.850 | 0.858 | 0.851 | **0.850** | 0.850 |
| mean | 0.740 | 0.744 | 0.839 | **0.847** | 0.814 |

- **Default overlap alone:** +0.003 on average (−0.002 to +0.008). It repairs nothing.
- **P1′ + bridging on the default first pass:** +0.103 on average. The four cases gave +0.177,
  +0.177, +0.068 and **−0.008** (c0526 got slightly worse).
- **Support rule, step-0.75 audit, 6 cases:**
  - It kept all 4 FP joins: each orphan that touched no reference voxel had been predicted again by
    the second look.
  - It blocked 2 true joins: c0407's 3200-voxel orphan, and one 396-voxel orphan in c0675.
  - On the step-0.5 pass it again cost c0407 0.938 → 0.806.

## What it implies

1. **The C1 confound is answered for these cases.** P1′'s repair is not an overlap artefact: the
   default overlap recovers +0.003, while P1′ on top of it recovers +0.10 on the cut trees. It is not
   free: one case got 0.008 worse, so "never worse" is withdrawn.
2. **The support rule is dropped.** It is the wrong filter: it keeps FP joins and blocks true ones.
   The FP orphans are confidently re-predicted, so they are probably real vessels absent from the
   *thin* reference. Under the decided thick reference they may count as true joins. That can only
   be settled on a thick-convention model, which is the pending Trillium run.
3. **This remains n = 4 cut cases** from one small-patch binary model on the thin convention. Whether
   P1′ matters on the master's model and convention is the Trillium question
   ([[Delta - PENDING Trillium run - does gap-centred re-inference beat nnU-Net's default inference on a thick-convention 4-class model]]).

## Limits

- Only the 4 cut cases were controlled. The 12 uncut cases were unchanged by P1′ at step 0.75, and
  were not re-run at step 0.5.
- Oracle names, binary model, thin reference, crop to the reference box + 10 mm.
