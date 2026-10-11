---
tags: [plans, experiment, round8, tree-f1, rca, lcx, miss-census, a1c, falsifier]
author: Delta
round: 8
updated: 2026-10-11
---

# Phase A confirms the RCA was an ostium artefact, and the remaining loss is mask vessel without contrast

Inputs:

- **Scores:** atlas2 Phase A (`trillium-results/round6/atlas2/results/per_case_run1.json`: run 1's 80 val cases, re-scored with the A1 aorta ostium, old hash 3c737cbc).
- **Volumes:** run 1's 80 val and 36 open segmentations, and atlas2's 116 TotalSegmentator aortas ($SCR/round6, read-only).
- **References:** Atlas's proxy, rebuilt with its own `make_label`. It reproduces atlas2's per-class scores exactly; see §3.
- **Metric:** `segtrain.tf1` at sha 9bb77e24.

Scripts: `experiments/Delta/r8_miss_census.py`, `summarise_r8_census.py`, `r8_hu_lost.py`, `r8_open36_identity.py`. Outputs are in `work/Delta/r6/`.

## 1. The pre-registered falsifier, scored exactly as written: **it passes. The Q2 taxonomy survived**

| Criterion (Round 6, as written) | Result | Verdict |
|---|---|---|
| Unflagged RCA A1-tF1 ≥ 0.85 | **0.883** (n = 56) | pass |
| Order LM > LAD ≈ RCA > LCx | 0.966 > 0.901 ≈ 0.883 > 0.846. Paired on cases where both are unflagged: LAD − RCA +0.006 [−0.027, +0.038] (n = 48); RCA − LCx +0.026 [−0.002, +0.056] (n = 48) | pass. LAD ≈ RCA holds; RCA > LCx holds on the means, but its paired CI touches 0 |
| RCA gain over 0.771 ≥ 0.07 | 0.883 − 0.771 = **0.112** | pass |

The RCA is no longer the weakest class; the LCx is. My main term, the provisional ostium, was right.

Two honest qualifications:

1. **The gain clause is generous as written.** It compares unflagged trees now with all trees before. Like for like, the gain is smaller:

   | Comparison | RCA gain |
   |---|---|
   | Same unflagged cases, paired | +0.067 [+0.016, +0.135] |
   | All trees (0.771 → 0.835) | +0.065 |

   Both sit just under 0.07. I estimated the artefact at 0.111 from clDice; the realised correction is about 0.065 on all trees, because some trees moved into the flagged set rather than being fixed.

2. **Counting flagged trees, the RCA is still last** (0.835 vs LCx 0.840), because 24 of 80 RCA trees are flagged and they average 0.723.
   - Four of them score 0. Their A1 ostium is 8–20 mm from the ImageCAS-X start point (c0378, c0581, c0708, c0826), so these are metric artefacts, and the flag caught every one.
   - The 17 flagged RCAs whose A1 ostium is within 5 mm average 0.865.
   - A1b is doing its job. Flagged RCAs need the human ostium review, not a model fix.

## 2. Miss census: where the remaining LCx and LAD loss lives (80 val, unflagged classes)

Every lost reference centreline voxel is classified with the module's own recall and precision (the replication is asserted equal per case and class). Losses are a fraction of the class centreline, as a mean per case. "Mask-only" means centreline more than 1 mm from any ImageCAS-X vessel voxel: vessel the experts did not trace.

| | LAD (n 72) | LCx (n 72) | RCA (n 56) | LM (n 72) |
|---|---|---|---|---|
| recall / precision | 0.898 / 0.918 | **0.837 / 0.877** | 0.898 / 0.887 | 0.977 / 0.964 |
| recall loss: absent (no prediction) | 0.081 | **0.135** | 0.097 | 0.007 |
| recall loss: misnamed | 0.012 | 0.013 | 0.001 | 0.016 |
| recall loss: disconnected | 0.009 | 0.016 | 0.005 | 0 |
| mask-only share of the reference centreline | 0.109 | 0.154 | 0.282 | 0.011 |
| recall loss on mask-only centreline | **0.060** | **0.103** | **0.079** | 0.007 |
| → fraction of mask-only centreline lost | **55 %** | **67 %** | **28 %** | — |
| recall loss on ImageCAS-X-traced centreline | 0.042 | 0.060 | 0.023 | 0.016 |
| → fraction of traced centreline lost | 4.7 % | 7.0 % | 3.2 % | 1.6 % |
| precision loss: predicted outside the mask (not ImageCAS-X) | 0.033 | **0.066** | **0.079** | 0.011 |
| precision loss: predicted in ImageCAS-X vessel the mask lacks | 0.041 | 0.040 | 0.032 | 0 |
| precision loss: other class | 0.009 | 0.017 | 0.002 | 0.024 |

What the census shows:

- **On expert-traced vessel the model is close to complete.** It recalls 93–97 % of ImageCAS-X-traced centreline, LCx included.
- **Most of the recall loss is mask-only vessel the model does not predict at all:** 0.060 of 0.102 for the LAD and 0.103 of 0.163 for the LCx. These misses are not small:
  - by radius, about 85 % of lost LCx centreline has a reference radius of at least 1 mm;
  - they are spread from 20 mm to beyond 100 mm from the ostium;
  - the lost centreline lies a median 1.1–2.4 mm from the nearest prediction.
- **The lost mask-only vessel has almost no contrast.** On the 17 val cases with a CT on disk, after smoothing (0.7 mm Gaussian), these are the per-case median HU values at centreline voxels:

  | Class | Mask-only, lost | Mask-only, recalled | Traced, lost | Traced, recalled | Aorta |
  |---|---|---|---|---|---|
  | LAD | 39 | 93 | 108 | 164 | 472 |
  | LCx | 91 | 141 | 76 | 181 | 472 |
  | RCA | 41 | 63 | 56 | 267 | 472 |

  Lost mask-only centreline sits at 7–19 % of aortic HU, which is soft tissue, not contrast lumen. The model is declining to segment reference voxels that the image does not support. Whether those voxels are mask over-segmentation (veins, fat, leakage) or vessels too small and partial-volumed to see cannot be told from HU alone.
- **The precision side has the same shape.**
  - 0.07–0.11 of predicted centreline lies outside the mask.
  - 30–55 % of that, depending on the class, is ImageCAS-X vessel the mask lacks: the reverse extent mismatch.
  - The rest is predicted vessel neither reference contains. This matches the FP census's `confident_other` majority (79 %) on the attached side.
- **Naming and connectivity together cost ≤ 0.03 per class.**

**Answer to Q2's second half.** The remaining LCx and LAD loss lives in reference extent. Specifically, it is vessel in the ImageCAS mask that ImageCAS-X does not trace and that has no contrast, plus vessel the model predicts outside the mask. It is not in distal calibre, connectivity or naming. Window, loss or epoch changes have little to work on. A written extent rule for team reads does.

## 3. The two pending A1c checks (Round 7 tests 3 and 8) on run 1's predictions

**Test 3 (cohort identity on the 116 run-1 predictions).**

| Set | Comparison | Bit-identical |
|---|---|---|
| 80 val | new hash vs atlas2's old-hash `per_class` | 80 / 80 |
| 36 open | new hash vs the frozen copy | 36 / 36 |

- `classes_without_centreline` lists exactly six cases: c0613 and c0848 (val), and c0772, c0805, c0807 and c0824 (open, all LM).
- These are 6 of my 7. The seventh, c0108 (LCx), is a development case with no run-1 prediction.
- **The test passes.**

**Test 8 (paired, both hashes).** Default (= old hash) vs fallback, on run 1's predictions:

| Case | Macro, default → fallback | LM under the fallback |
|---|---|---|
| c0613 | 0.916 → 0.893 | 0.824 |
| c0848 | 0.893 → 0.909 | 0.957 |
| c0772 | 0.802 → **0.669** | **0.286** |
| c0805 | 0.885 → 0.900 | 0.945 |
| c0807 | 0.821 → **0.681** | **0.291** |
| c0824 | 0.926 → 0.932 | 0.947 |

- **Val overall (80):** macro 0.8837 → 0.8837; LM n 76 → 78, mean 0.964 → 0.962.
- **The decisive aggregate is unchanged.** All six cases carry a flagged left ostium, so A1b already keeps their left classes out.
- **The fallback exposes 2 real LM errors** (c0772, c0807: LM tF1 about 0.29) that the default drops silently. On the other 4 it gives LM 0.82–0.96.

## Limits

- The census is single-model (run 1) and correlates with one expert tracing (ImageCAS-X).
- "Mask-only" is defined at 1 mm. The HU check covers 17 of 80 cases, the ones with a CT on disk. It is median-of-medians on smoothed HU, and it is biased toward the round-5 artefact cases.
- Flagged trees are excluded from the census, as from the decisive aggregate.
