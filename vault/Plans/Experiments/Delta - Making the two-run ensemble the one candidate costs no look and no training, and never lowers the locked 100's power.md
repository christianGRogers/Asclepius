---
tags: [plans, experiment, janus1-L, power, locked100, ensemble, L3, D46]
author: Delta
round: 2
track: 1-L
updated: 2026-11-13
issue: christianGRogers/Asclepius#302
code: experiments/Delta/j1l_r2/ensemble_power.py, experiments/Delta/j1l_r2/l3_fix.py
---

# Making the two-run ensemble the one candidate costs no look and no training, and never lowers the locked 100's power

**Question** (Janus 1-L Round 1 ruling §5, item 1). Should the one pre-registered candidate C in the H1–H3 sequence be
a1, or the ensemble E = mean softmax(a1, a2)? The ruling bars testing both: that would be two looks (L-A7). So the
choice has to be made now, on what is known before any locked-100 number exists.

**Data.** Nothing new is read: no locked-100 number, no sealed case, no image. The noise comes from the one measured pair
of warm siblings on this family: atlas3 F1 and F0, two warm fine-tunes from one start on the same data, val 80, A1c
tF1 (`trillium-results/round7/atlas3/per_case_F{0,1}.json`).
- SD of the per-case macro difference: 0.0382.
- Excess kurtosis: 12.8. Most cases do not move; a few trees flip between rooted and cut.

**Model.** Per case, a1 − J0 = μ + g₁ + sᵢ + v₁ᵢ, and E − J0 = μ + (g₁ + g₂)/2 + sᵢ + wᵢ.
- v is a child's own per-case noise. v₁ − v₂ is resampled from the real F1 − F0 differences, so the tails are real.
- s is the per-case spread of the recipe's true effect, which both children share. Its SD is √λ·σ_v:
  - λ = 1 reproduces round 1's optimistic SD(a1 − J0) of 0.038;
  - λ = 6.7 reproduces the pessimistic 0.075.
- g is a run-level offset, A37's floor σ_g = 0.012, or 0.
- w = √(2φ)·(v₁ + v₂)/2:
  - φ = 0.5: E behaves like the average of its members' scores;
  - φ = 1: no per-case gain at all (the worst case for E).
- **No mean ensemble bonus is assumed** (e = 0 in every row). No source gives one for tree-F1 at M = 2.

Rules are the ruling's, at n = 100, with one-sided 2.5 % t bounds. Against a percentile bootstrap they give the same
decision in 97 % of draws.
- **H1:** lower bound > −0.02.
- **Q4 (D46):** lower bound > −0.015.
- **H3:** lower bound > 0.

## Result

**tF1: P(pass), C = a1 against C = E** (4 000 simulated studies per cell; the full grid is in `ensemble_power.json`)

| λ, σ_g, φ | True μ | H1: a1 → E | Q4 adopt: a1 → E | H3: a1 → E | E fails H1 where a1 passes |
|---|---|---|---|---|---|
| 1, 0.012, 0.5 | −0.02 | 0.29 → **0.24** | 0.16 → **0.10** | 0.015 → 0.002 | 0.12 |
| | 0 | 0.84 → **0.93** | 0.73 → **0.82** | 0.28 → 0.24 | 0.02 |
| | +0.005 | 0.91 → **0.98** | 0.84 → **0.93** | 0.42 → 0.44 | 0.01 |
| | +0.01 | 0.96 → **0.996** | 0.92 → **0.98** | 0.58 → **0.64** | 0.001 |
| 1, 0.012, 1.0 (E no better per case) | 0 | 0.84 → 0.91 | 0.74 → 0.80 | 0.28 → 0.21 | 0.03 |
| | +0.01 | 0.97 → 0.99 | 0.92 → 0.97 | 0.59 → 0.61 | 0.003 |
| 1, 0, 0.5 (no run offset) | 0 | 0.998 → 1.00 | 0.96 → 0.99 | 0.03 → 0.02 | 0.000 |
| | +0.01 | 1.00 → 1.00 | 1.00 → 1.00 | 0.74 → **0.83** | 0.000 |
| 1, 0, 1.0 (the worst case) | any | **identical** | identical | identical | ≤ 0.07 (at μ = −0.01) |
| 6.7, 0.012, 0.5 (pessimistic) | 0 | 0.63 → 0.69 | 0.50 → 0.52 | 0.14 → 0.09 | 0.07 |
| | +0.01 | 0.86 → 0.92 | 0.76 → 0.84 | 0.38 → 0.37 | 0.02 |

H3 at μ = 0 is not a size error when σ_g > 0. A model decision judges the checkpoint, and a checkpoint with g > 0 really
is better than Janus 0. With σ_g = 0, H3's size is 0.02–0.03, as it should be.

**What the table shows.**
1. **E is never worse at the decision.** In the worst case (φ = 1, σ_g = 0), the two candidates behave identically.
2. **Wherever there is something to average, E is better in both directions.**
   - It adopts a neutral or better model more often: H1 0.84 → 0.93 and Q4 0.73 → 0.82 at μ = 0.
   - It adopts a −0.02 model less often: Q4 0.16 → 0.10.
   - The gain comes from two sources. The run lottery (σ_g) is halved. And if φ < 1, the per-case noise shrinks
     (SD(E − J0) / SD(a1 − J0) = 0.87 at λ = 1; 0.71 at λ = 0).
3. **The regret is small.** "E fails H1 where a1 would have passed" happens in ≤ 3 % of studies for any μ ≥ 0 at
   λ ≤ 1 (≤ 7 % pessimistic). It is mostly large only where adopting a1 would itself be wrong (μ = −0.02: 12 %).
4. **Dice (H2):** E's power is the same or higher. With SD(a1 − J0) = 0.023 and a Dice gain of 0.005, H2 passes
   0.58 → 0.71 at φ = 0.5, and 0.57 → 0.57 at φ = 1.

**The recall guard L3** (L-A5), false-alarm rate under no true change:

| Shape of the true per-case recall change s | λ | L3, C = a1 | L3, C = E |
|---|---|---|---|
| Heavy-tailed, as measured (most trees unchanged, a few flip) | 0 | 0.034 | 0.021–0.056 |
| | 1 | 0.062–0.069 | 0.064–0.066 |
| | 3 | 0.075–0.079 | 0.069–0.075 |
| Gaussian (every tree moves a little) | 1 | 0.17–0.19 | 0.19–0.21 |
| | 3 | 0.46–0.47 | 0.45–0.47 |

**A correction to my round-1 number.** Round 1 said L3 false-alarms about 4 %. That is right when the parent-to-child
differences look like the sibling differences we measured, which are heavy-tailed. With a broad, Gaussian per-case
shift it is 17–47 %.
- A variant with a significance clause (`l3_fix.py`, L3′: trimmed mean < −0.02 **and** Yuen's 95 % upper bound < 0)
  caps the Gaussian false alarm at 10–12 %. But it costs power against real shortening: a uniform −0.03 LCx loss is
  caught 0.65 instead of 0.80 at λ = 1, and 0.36 instead of 0.79 at λ = 3.
- The only parent-to-child evidence on this family (warm children of one start) is heavy-tailed. So **L3 stays as
  adopted**, and its false-alarm rate is stated as **3–8 %, or up to 19 % if the shift is broad**. The report prints each
  class's excess kurtosis of the recall Δ, so the reader can see which regime the result came from. It does not change
  the rule.
- E does not change L3's behaviour either way.

## What it changes

- **C = E is pre-registered** (Delta v2 §1). It costs no training, because a2 runs anyway (D46 Q5). It costs no look,
  because a1 is never tested.
- **The E − a1 test of my round 1 (MDE 0.005–0.010) is withdrawn.** It is no longer needed: E is not chosen over a1 on
  the locked 100. E − a1 is a report.
- **L3's stated false-alarm rate** is 3–8 % (heavy tails, as measured), and up to about 19 % under a broad shift.

**Limits.**
- One sibling pair, scored on val 80 (n = 80), stands in for the parent-to-child noise.
- φ is unknown for tree-F1. The table brackets it, and the decision holds at φ = 1.
- Probability averaging is not score averaging. A thin segment that one member keeps and the other drops can fall
  under the threshold in E. That is why φ = 1 is in the table, and why H1's class, recall and FP guards apply to E
  unchanged.
