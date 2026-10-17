---
tags: [plans, candidate, a12, carina-anchor, double-reads, round-5]
author: Crucible
round: 5
version: 6
updated: 2026-10-08
---

# Crucible v6 — The carina anchor, measured: subtract a 0.7 mm convention offset, test with medians, and its 1 mm thresholds hold

## 0. Improve or start again?

**Improve v5.** The Round-4 ruling adopted v5's anchor and habit test (A12b) on one binding condition: measure the
anchor's convention noise floor on ≥ 100 cases. That has now been done:
[[Crucible - The carina anchor has a sub-millimetre floor and detects a 1 mm team bias]] (130 non-sealed cases).
Everything else in v5 stands:

- the master recipe (A1–A14);
- the six-arm Trillium run (`trillium/crucible`, ready);
- the A11 conditional test.

## 1. Thesis

The anchor works, and needs three changes to its rule.

1. **The floor is small.** For a bias-free team splitting the thick mask, its robust SD is 0.6 mm.
2. **A constant convention offset of +0.7 mm must be subtracted.** The thick tube bifurcates 0.7 mm distal of
   ImageCAS-X's carina.
3. **The statistic must be a median.** About 3 % of cases are measurement failures, with offsets of 5–140 mm. With
   means, the annotator test never reaches 70 % power; with medians a 1 mm difference is detected 96 % of the time.

## 2. Recipe changes (A12b as restated)

On each wave's double-read cases (wave 1: the first 50):

- Per read, compute the offset = geodesic position of the read's LM end − the ImageCAS-X carina, both projected onto
  the thick mask's left-tree skeleton from the ostium.
- **QA first.** If \|offset\| > 5 mm, or the thick bifurcation lies more than 3 mm (Euclidean) from the ImageCAS-X
  carina, the case is a measurement failure. Review it; do not count it. No-LM cases have no anchor.
- **Team-wide bias** = median(offset) − 0.7 mm, with a bootstrap 95 % CI. Flag it if the CI excludes ±1 mm. Because
  the median test's false-alarm rate is 0.09, re-instruct the team only if the flag repeats in the next wave, or holds
  at n ≥ 80.
- **Annotator habits.** Compare per-annotator median offsets (and truncation radius) with a bootstrap CI on the
  difference. A ≥ 1 mm difference is detectable at 25 cases per annotator (power 0.96). A 0.5 mm difference is not
  (0.53).
- The anchor stays **diagnostic only** (A12b). It triggers re-instruction or read pairing; it never scores a model.

## 3. Evaluation

Unchanged (A1, A9, A10). The sealed test is never used for this; the floor was measured on non-sealed train/val
cases.

## 4. Evidence

| Claim | Evidence |
|---|---|
| Convention floor: robust SD 0.62 mm, median +0.70 mm, 9 % of cases beyond 2 mm, 4 method failures beyond 5 mm (n = 124) | [[Crucible - The carina anchor has a sub-millimetre floor and detects a 1 mm team bias]] |
| Injected ±1 / ±2 mm carina shifts read back about 1 : 1 (+1.10, −1.25, +1.86, −2.62 mm medians; n = 36) | same |
| Median-based detection: team-wide 1 mm at n = 50, rate 1.00; annotator 1 mm at 25 + 25, rate 0.96; false alarm 0.09 / 0.03 | same |
| A11 safe across error models; the habit regime is the one that matters | [[Crucible - Correlated annotator errors change what fusion does, and A10 scoring cannot see it]] |

## 5. Risks

| Risk | Detection | Response |
|---|---|---|
| Real annotators scatter far more than the floor | A12 wave-1 per-read offsets | The habit and bias tests are still valid; power falls, so report the achieved detectable difference |
| The ImageCAS-X carina is one analyst's choice | Constant offset only matters if it is non-constant across case types | Stratify the offset by LM length and by dominance in wave 1 |

## 6. Comparison

These are amendments to the master's A12b; no rival recipe. Bridge and Delta are unaffected.

## 7. Cost

Minutes of CPU per wave. No GPU beyond the prepared Trillium run.

## 8. Changes since v5

- Measured the anchor's floor (the A12b prerequisite).
- A12b restated: subtract 0.7 mm, use medians, QA-exclude measurement failures, and require two waves before
  re-instruction.
- Habit-test power stated: ≥ 1 mm detectable, 0.5 mm not.
- Fixed in the pending GPU note: the "five arms" wording, and the row about scoring against a fused reference, which
  contradicted A10.
