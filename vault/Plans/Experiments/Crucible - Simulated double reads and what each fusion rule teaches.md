---
tags: [plans, experiment, double-reads, noisy-labels, evaluation, tree-f1]
author: Crucible
round: 3
updated: 2026-10-08
---

# Simulated double reads: the fusion rule barely changes what a model can learn, but scoring against one read misranks models and the inter-read "ceiling" is not a ceiling

## Question

D2 means every case is read twice, and D0/D1/D1b fix the target as the ImageCAS mask split into four classes,
territory rule, ramus → LCx. Three questions:

1. How should the two reads enter **training**: one read, both reads as separate samples, agreement-only with
   `ignore`, or union-with-conflict-`ignore`?
2. What should the **reference** be?
3. What does the inter-read agreement bound?

There are no real double reads yet, so this note simulates them from a truth and measures what each choice implies.

## Method

**Truth T.** For 49 cases with CT (all with ImageCAS-X labels), T is the Girder/ImageCAS mask, each voxel given the
territory class of the nearest ImageCAS-X voxel. Crops come from `experiments/Crucible/r2_prep.py`.

**Annotator model** (`experiments/Crucible/r4_reads.py`). Each read is independent. Annotators can only split or trim
the seed, as SegQueue enforces.

- carina shift ~ N(0, 2 mm) of the LM / bifurcation boundary;
- **distal truncation**, "stop where the lumen is no longer confident". Each voxel's vessel radius is taken at its
  nearest centreline voxel. Everything thinner than r_t ~ U(0.6, 1.05) mm is dropped, together with everything
  beyond it that loses its connection to the ostium;
- ramus labelled LAD instead of LCx, p = 0.3 (a protocol slip);
- D1 or OM1 given to the other left class, p = 0.15.

**Calibration** (49 cases, inter-read per-class Dice):

| | LM | LAD | LCx | RCA |
|---|---|---|---|---|
| Simulated | 0.81 | 0.93 | 0.90 | 0.96 |
| ImageCAS-X inter-observer (arXiv:2608.30404, Table 1; different convention) | 0.92 | 0.92 | 0.85 | 0.95 |

The LM is under-agreed: 2 mm is too large a carina SD for a short LM.

**Fusion** (`experiments/Crucible/r4_fusion.py`, 24 cases, K = 10 extra reads per case). For each training scheme, the
label a well-trained model converges to is taken as the per-voxel **mode of that scheme's target over many draws**.
That is the population optimum of cross-entropy:

- single and both share one optimum (both only doubles the samples);
- union and agree are each the mode over read pairs fused that way.

**Scoring.** tF1 @ 1.5 mm (D3; `r2_eval.score`, provisional under A9), with the ostium on T, against:

- the truth T;
- each actual read A and B (mean of the two);
- the inter-read ceiling, B scored against A.

## Result (24 cases)

| Predictor | tF1 vs truth | tF1 vs one read (mean of A, B) | foreground / truth |
|---|---|---|---|
| truth T itself | 1.000 | **0.922** (median 0.938, min 0.746) | 1.000 |
| optimum of single / both | **0.957** (median 0.964) | 0.933 | 0.990 |
| optimum of union | 0.956 | 0.929 | 0.992 |
| optimum of agree | 0.953 | 0.929 | 0.990 |
| one read (B) scored against the other (A) | — | **0.900** (median 0.937, min 0.616) | 0.990 |

- The single/both optimum beats the inter-read figure by +0.057 tF1 on average, and in 20 of 24 cases.
- Scored against one read, the **truth** gets 0.922. That is 0.011 *lower* than the single-read optimum (0.933),
  which is "the median annotator".

## What it implies

1. **The fusion rule hardly changes the target a model converges to** (0.953–0.957 vs truth, a spread of 0.004).
   Under symmetric, independent annotator errors, every scheme's optimum is about the per-voxel majority. So any
   difference between schemes is a **finite-data and variance** effect: noise in gradients, wasted supervision under
   `ignore`, doubled samples under `both`. Only training can measure it.
   - The prepared GPU run [[Crucible - GPU experiment on training with two reads per case (pending)]] measures exactly
     this.
   - On this evidence, the default should be **both reads as separate samples**. It is the simplest, it is equal at
     the optimum, it has twice the samples, and it needs no ignore-label support.
2. **Do not score against a single read.**
   - A perfect model (the truth) scores 0.92 against one read, while a model that imitates the median annotator
     scores 0.93. Single-read scoring therefore *prefers the median annotator to the truth*, and its noise (min 0.75)
     is as large as most recipe effects in the vault.
   - The sealed-test reference must use **both** reads: score each case against both and average, or score only
     where the reads agree.
3. **The inter-read figure is not a ceiling for model-vs-read scores.**
   - A model trained on many reads can score above B-vs-A (+0.057 here), because it averages out each annotator's
     idiosyncrasies.
   - The master's acceptance rule ("within 5 tF1 points of team inter-rater per class") is therefore too lenient as
     stated: a model at the ceiling could still be 0.06 below the median annotator.
   - Restate it as: the model's mean tF1 against the two reads must be **≥ the inter-read tF1**, per class, with a
     paired CI.
4. Truncation (one-sided) is the only asymmetric error. Union-style fusion protects distal length (foreground 0.992
   vs 0.990), but the effect is tiny at these truncation rates. Real reads may truncate more, and the first real
   double reads should be checked for this.

## Limits

- **Everything rests on a hand-built error model.** The ranking conclusion holds only while errors are roughly
  symmetric and independent between annotators. Correlated errors would break it, for example two annotators
  trained alike who both stop at the same stenosis.
  - Re-fit the model on the first ~50 real double reads (carina SD, truncation radius, slip rates) and re-run this
    script (CPU, about an hour).
- "Converged model = mode of targets" is the infinite-data idealisation; capacity limits and finite data are not
  modelled.
- tF1 is my re-implementation with the thickest-voxel ostium on T; it is provisional under A9.
