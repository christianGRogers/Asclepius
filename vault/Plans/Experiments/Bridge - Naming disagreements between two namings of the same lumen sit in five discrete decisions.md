---
tags: [plans/experiment, double-reads, naming, label-fusion, D2]
author: Bridge
round: 3
updated: 2026-10-05
---

# Naming disagreements between two namings of the same lumen sit in five discrete decisions

## Question

D2 says every case gets two reads. Both reads split the same ImageCAS mask (D4), so the reads should
mostly differ in **names**, not in lumen. Two ways to fuse them:

- **Voxel level** (vault default, [[Fusing multiple annotations and learning from noisy labels]]):
  disagreeing voxels become soft or `ignore`.
- **Decision level** ([[Bridge v3]] §2.2): find which naming decisions differ and adjudicate those.

The decision-level route only works if name disagreement is not diffuse, i.e. if it lives in a few
decisions plus a thin carina band. No double reads exist yet (D5: nothing labelled). Can the claim be
tested now on the closest stand-in we have?

## Method

- **Stand-in for two reads:** two independent namings of the **same** thick lumen for every cached case
  with ImageCAS-X labels (**170 cases**; 75 outside my development set).
  - "Read A" = ImageCAS-X names projected onto our mask (territory, ramus → LCx: D1, D1b).
  - "Read B" = the frozen rule namer (ramus → LCx, 4 mm naming bridges).
  - Both are per skeleton vertex, from `extract.py` caches. "Near" voxels only (≤ 2 mm of an ImageCAS-X
    vessel, ~85 %).
- **Decisions extracted identically from each labelled skeleton:**
  - ostium = LM vertex farthest from LAD/LCx;
  - LM end = LM vertex nearest LAD/LCx;
  - LAD/LCx swap (> 50 % of one read's LAD named LCx by the other);
  - tree identity (> 50 % of one read's RCA named as a left-tree class);
  - ramus (> 50 % of ImageCAS-X IM voxels not LCx).
  - A decision disagrees at > 5 mm or > 50 %.
- **Every disagreeing voxel is attributed to one of:**
  - **band** — within 3 mm of either LM end;
  - **decision** — in a case where some decision disagrees;
  - **diffuse** — otherwise.
- Script: `experiments/Bridge/decisions.py`.
- **Disclosure:** the first version of the script extracted only three decisions (ostium, LM end,
  LAD/LCx). Tree identity and the ramus, both on [[Bridge v3]]'s own list, were missing and added after
  the first run. Both results are reported.

## Result

| | all 170 cases | held-out 75 |
|---|---|---|
| Disagreeing near voxels (pooled) | 2.05 % | — |
| Share in the **carina band** | 9.8 % | 10.0 % |
| Share in **decision-disagreeing cases** (5 decisions) | 77.5 % | 89.7 % |
| Share **diffuse** | **12.7 %** | **0.3 %** |
| Diffuse, if only the first 3 decisions are extracted | 68.7 % | — |
| Cases with any decision disagreement | 35 (21 %) | 15 (20 %) |
| — ramus / ostium > 5 mm / LM end > 5 mm / tree identity / LAD↔LCx | 19 / 9 / 7 / 2 / 0 | — |
| Median per-case diffuse fraction (agreeing cases) | 0.0 | — |

- The 68.7 % "diffuse" under three decisions is almost all two fused-tree cases (c0502, c0484: one namer
  calls the right tree left) and ramus cases. Both are decisions, and the 5-decision extractor
  reclassifies them.
- What remains diffuse sits in a handful of cases (c0152, c0050: 13–15 % of their voxels; then < 5 %).

## What it implies

1. **The pre-registered expectation in [[Bridge v3]] §3 holds on the stand-in.** With five decisions,
   87 % of naming disagreement (99.7 % on held-out cases) is in the carina band or in a case with a
   disagreeing decision. Name disagreement between two namings of the same lumen is not diffuse noise.
2. **Voxel-level fusion would spend `ignore` where it is wrong.** On a decision-disagreeing case it
   masks only part of a wrongly named subtree, and the rest of that subtree trains on whichever read was
   kept. Adjudicating the decision fixes the whole subtree at once.
3. **Adjudication load on the stand-in is 21 % of cases**, more than half of them the ramus. Under D1b
   the ramus is a rule, so human reads should disagree on it far less than my namer does against
   ImageCAS-X (19 of 35). The real rate is the wave-1 measurement in [[Bridge v3]] §3.

## Limits

- **A stand-in, not two human reads.** One "read" is a rule namer whose errors are structured by
  construction: rules fail as decisions. Human readers can also make diffuse errors (a mis-clicked
  side branch), which this cannot measure. That is what the wave-1 check is for.
- Projected ImageCAS-X names come from a different lumen convention (thin), with nearest-voxel transfer.
- Thresholds (5 mm, 50 %, 3 mm band) were set before the run, not tuned.
