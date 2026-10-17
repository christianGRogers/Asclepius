---
tags: [plans, candidate, double-reads, noisy-labels, correlated-errors, round-4]
author: Crucible
round: 4
version: 5
updated: 2026-10-08
---

# Crucible v5 — A11 survives correlated errors, but no read-based score can choose a fusion rule: anchor the team's carina to ImageCAS-X and test fusion where annotators have habits

## 0. Improve or start again?

**Improve v4.** Its scoring and acceptance rule is now binding (A10), and its fusion default is binding in part, as
A11. The ruling (§4) asked three things, and all three are done:

| Ruling asked for | Done in |
|---|---|
| A correlated-error test | [[Crucible - Correlated annotator errors change what fusion does, and A10 scoring cannot see it]] |
| Boundary jitter beyond truncation | same note |
| The A11 hybrid as an arm of the GPU run | `trillium/crucible/` (six arms, re-tested) |

The model recipe remains the master's ([[Atlas v3]], A1–A12).

## 1. Thesis

1. **A11 is a safe default.** Under independent errors, a shared stenosis stop, a shared carina ambiguity, a
   team-wide bias and brush jitter, every fusion rule converges to within about 0.01 tF1 of both-as-samples. A11 is
   never worse than −0.001.
2. **The one regime where fusion matters is opposite per-annotator habits.** One reader systematically puts the
   carina distal and stops early; the other does the reverse.
   - There, ignore-based fusions (A11, agree, union) beat both-as-samples by **+0.02–0.03 tF1 against the truth**,
     if the network fills the ignored band from its neighbours.
   - They lose up to 0.07 if it does not.
   - Only training decides which. The GPU run now uses exactly this read model.
3. **Scoring against the reads (A10) cannot see any of these differences.** It stays within ±0.002 everywhere,
   because it measures agreement with the annotators, not truth.
   - With a shared bias, the converged model drifts from the truth (tF1 0.90–0.92). The truth itself then scores
     below the model against the reads.
   - So the master's pre-registered A11 test on real reads, which is judged vs reads, **cannot fail A11, and cannot
     detect a team-wide bias.** It needs an external anchor.
4. **The anchor already exists.** ImageCAS-X labels name 800 of our cases. The *position* of the LM end and of the
   LAD/LCx split along the centreline is largely independent of the lumen-extent convention. The per-case offset
   (team carina − ImageCAS-X carina) measures:
   - a team-wide bias (a nonzero mean);
   - per-annotator habits (offset differences by annotator).
   It costs minutes of CPU.

## 2. Recipe (master + four additions)

The master is unchanged: nnU-Net v2 ResEnc, 0.5 mm iso, 256³ patch, fixed window, no mirroring, tF1 @ 1.5 mm,
A10 scoring, A11 training, A12 wave-1 report.

### 2.1 Add to A12: the carina anchor and the annotator-habit test (CPU)

For each of the first 50 double-read cases, compute along the team reads' own centreline (geodesic mm from the
ostium):

- **LM-end position** (LM → LAD/LCx) for read 1, read 2 and ImageCAS-X (projected names, ramus → LCx);
- **distal end of each main vessel** (truncation) for each read.

Report:

- the mean (team − ImageCAS-X) carina offset, with a 95 % CI. **This is a team-wide bias** if |mean| > 1 mm;
- per-annotator mean offsets and truncation radii. **These are habits** if two annotators' offsets differ by > 1 mm
  (permutation test across their cases);
- the refit noise model, now including habit and correlation terms, and a re-run of `r5_corr.py` with it.

### 2.2 Decision rules, pre-registered

| A12 finds | Then |
|---|---|
| No team bias and no habits | A11 as binding; the A11 test on real reads (vs reads) is sufficient |
| **Habits** (annotators differ by > 1 mm) | Keep A11, which is better than or equal to both-as-samples in simulation in that regime *if the network fills the band*. The GPU result (below) says whether it does. Pair reads across habit groups where scheduling allows, so every case's two reads are not always the same habit pair. Judge the A11 test **also by the carina offset vs ImageCAS-X**, not only vs reads |
| **Team-wide bias** (> 1 mm) | Re-instruct the team with ImageCAS-X carina examples before more labelling. No fusion rule can remove a bias both reads share. Report the sealed test with and without the ImageCAS-X carina check |

### 2.3 The GPU experiment (prepared; the lead runs it)

`trillium/crucible/`, one command, 1 × H100 for ≤ 23 h 55 min, `--account=def-aso22`.

- **Six equal-step arms:** single (annotators alternate), both, **a11**, agree, union, oracle.
- **Reads:** default `annot_bias` (opposite habits).
- **Decisive comparison for this plan:** a11 vs both, **against the truth**:
  - a11 ≥ both: the network fills the ignored band, and A11 stands even under habits;
  - a11 < both (CI excludes 0): narrow A11's name-conflict `ignore` to cases without detected habits.
- **Second check:** all fusions vs reads within ±0.002. That confirms A10 cannot choose a fusion rule.

See [[Crucible - GPU experiment on training with two reads per case (pending)]].

### 2.4 A10 margin check

Under a shared carina ambiguity, a converged model only *ties* the inter-read tF1 (+0.000). So the 0.02
non-inferiority margin is not lenient. If A12 finds a shared ambiguity, confirm the margin with the clinical lead
before sealed-test scoring. The jitter row (−0.020) is a tie artefact of my proxy and is not used.

## 3. Evaluation

As the master (A1, A9, A10). The carina-offset distribution against ImageCAS-X is reported on the sealed test as a
**secondary, convention-independent** check.

## 4. Evidence

| Claim | Evidence |
|---|---|
| Fusion rules within about 0.01 of both-as-samples under indep, corr_trunc, corr_carina, team_bias, jitter; A11 ≥ −0.001 | [[Crucible - Correlated annotator errors change what fusion does, and A10 scoring cannot see it]] (14 cases × 6 scenarios) |
| Under opposite habits, ignore-fusions +0.018 to +0.026 vs truth (CIs exclude 0) with neighbour fill; up to −0.075 without | same |
| Against the reads, every fusion is within ±0.002, even where they differ by 0.02–0.03 vs truth | same |
| A shared bias makes the truth score below the model vs reads (0.905 vs 0.946; 0.897 vs 0.941) | same |
| The GPU run is contract-compliant, with six arms and the habit read model | `trillium/crucible/`; CPU smoke runs; dry runs in both layouts |
| ImageCAS-X names cover our cases `c{id-1}` | [[Crucible - ImageCAS-X is real and its 800 cases are our cases c(id-1)]] |

## 5. Risks

| Risk | Detection | Response |
|---|---|---|
| ImageCAS-X carina positions differ from ours by convention (thin vs thick LM end) | Offset distribution on the first 50 cases: a constant offset with small spread is convention; spread or per-annotator structure is habit | Subtract the constant; use spread and per-annotator differences |
| The GPU run's simulated habits are the wrong size | A12 refit | Re-run the CPU simulation with fitted values; the GPU result is a prior only (as the ruling says) |
| "Converged model = plurality" proxy | GPU run | — |

## 6. Comparison

- **The master.** v5 changes none of its training. It adds:
  - to A12: the ImageCAS-X carina anchor and an annotator-habit test;
  - to the A11 test: an anchor criterion, because judging it vs reads cannot fail;
  - a margin check on A10.
  These are amendments, not a rival recipe.
- **Bridge, Delta:** unaffected.

## 7. Cost

- **CPU:** minutes per wave.
- **GPU:** the one prepared Trillium job (≤ 24 H100-h).
- **Human:** none beyond D2. Pairing reads across habit groups is a scheduling rule for the labelling lead.

## 8. Changes since v4

- New correlated-error, habit and jitter study.
- The GPU run gains the A11 arm and uses the habit read model by default; the single arm alternates annotators.
- New: the ImageCAS-X carina anchor, the habit test, and the pairing rule.
- Withdrawn:
  - the v4 claim that "a converged model clears inter-read by about 0.06". It holds only under independent errors:
    +0.024 in the larger r5 sample, and 0.000 under a shared ambiguity;
  - the hierarchical read-out idea, which was tested and gives only +0.005.
