---
tags: [plans, candidate, lumen-convention, imagecas-x, round-3]
author: Crucible
round: 3
version: 3
updated: 2026-10-05
---

# Crucible v3 — finishing the D0 price list: the convention mismatch costs 0.19 one way and 0.25 the other, and it manufactures cuts

## 0. Improve or start again?

**I am improving v2. This is an evidence round, not a new recipe.**

I considered a materially different recipe and rejected it. The only candidate I could evidence was the v1
14-class head, and the paired CPU arm below is the only test of it I can run without a GPU. It cannot justify
replacing the master. My job this round is the one the ruling (§4) set:

1. finish the reverse-direction scoring;
2. finish the paired thin / thick / 14-class training run with valid inference, reported as cut and recall
   differences only;
3. re-score with the ported tF1 once it exists. That needs `src/segtrain` tF1 with the A1 ostium, which no one has
   ported on this CPU, so it **remains pending**.

## 1. Thesis

Unchanged from v2. The training target, the SegQueue seed and the team reference must be one convention, decided
at D0. The master's A3 procedures, which came from v2, enforce that. v3 completes the evidence D0 is given. Read
**both** directions of the price list, and note that a convention mismatch shows up partly as *cuts* that do not
exist.

## 2. Recipe

**The master ([[Atlas v2]] amended A1–A9) unchanged.** v3 adds nothing to the model, data, schedule or
post-processing.

It adds one rule to the A3 procedures:

- **(new) Cut counts and rooted recall are only compared within one convention.** Under a mismatched or mixed
  reference, the ostium rule can place the reference ostium on tissue the prediction legitimately does not cover.
  Measured: 3 of 10 RCAs were scored as fully cut by a perfect model.
- Any cut-rate argument (the A1 native-spacing ablation, P1′ bridging, Skeleton Recall) must therefore be scored
  on cases that pass the convention monitor. Its ostia must also pass the A1 cross-check against **that** reference.

## 3. Evaluation

As the master (A1, A9). v3 adds the rule above.

## 4. Evidence

### 4.1 D0 price list, both directions (10 ICX-test cases, re-implemented tF1, `thick` ostium; provisional under A9)

| Team draws… | Model trained on… | tF1@1.5 of a *perfect* model | Where the loss is |
|---|---|---|---|
| expert lumen (A) | expert lumen | 1.000 | — |
| expert lumen (A) | Girder proxy (B) | **0.806** | precision 0.76: branches the expert did not trace. LAD 0.74, LCx 0.79, RCA 0.74 |
| Girder seed (B) | expert lumen (A) | **0.746** | rooted recall 0.71. **RCA 0.50, with 3/10 RCAs scored 0 (artefactual cuts)**: the thin RCA never reaches the thick reference's ostium |
| Girder seed (B) | Girder proxy | 1.000 | — |

Source: [[Crucible - A perfect segmentation in the wrong lumen convention loses 0.19 tree-F1]] (updated with the
reverse direction).

So a mixed state costs about **0.19–0.25 tF1 per affected case**, now measured in both directions rather than
extrapolated. Part of it looks like topology failure, though it is not.

### 4.2 Paired CPU training: thin vs thick vs 14-class target (**pending, running**)

Setup:

- three identical tiny 3D U-Nets (8–64 channels, 80 × 80 × 56 patch ≈ 28 mm, 1200 iterations, seed 0);
- trained on 39 ICX-train cases and tested on the same 10 cases;
- scored against **both** references;
- code: `experiments/Crucible/r2_train.py`, `r2_eval.py`, `r2_summ.py`.

Inference uses training-patch tiles. The v2 bug was 160³-class tiles, which changed InstanceNorm statistics and
emptied the predictions.

Status: thin4 and thin14 are trained and predicted (10/10 and 7/10); thick4 re-inference is running. Results will
be added here and in an experiment note when scored. Until then nothing from this run may be cited.

Pre-registered reading:

- Only the paired differences in rooted recall, unrooted recall and cut count are interpretable, each judged
  against the reference of the arm's *own* convention and against the other.
- Naming at a 28 mm patch is expected to be poor for every arm.
- thin14 vs thin4 is a test of "no worse". It is not a reason to adopt the 14-class head, which stays withdrawn
  unless D0 leaves the side-branch rule open.

### 4.3 Carried over

- The Girder masks are 3.6× the lumen and 47 % non-contrast tissue
  ([[Crucible - Original binary masks disagree with ImageCAS-X]]).
- ICX maps to our cases as `c{id-1}` ([[Crucible - ImageCAS-X is real and its 800 cases are our cases c(id-1)]]).

## 5. Risks

As v2, plus one: **cut-rate conclusions drawn on mixed-convention references.** This is detected by the new §2
rule, and the response is to re-score on single-convention cases only.

## 6. Comparison

This is not a rival plan. It is an evidence supplement to the master's D0 and A3. If the judge folds §2's rule into
A3/A9, Crucible has no separate claim.

## 7. Cost

No GPU. CPU only, for the monitor (about 1 min per case per wave).

## 8. Changes since v2

- Reverse-direction scoring is done: 0.746, with artefactual RCA cuts.
- The price list is complete in both directions.
- New rule: cut and rooted comparisons are made only within one convention.
- The paired CPU run is re-launched with valid inference (pending).
- The ported-tF1 re-score is pending.
