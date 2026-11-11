---
tags: [plans/experiment, janus1-l, D45, power, locked100, warm-start]
author: Atlas
track: 1-L
round: 1
updated: 2026-11-11
issue: christianGRogers/Asclepius#302
code: experiments/Atlas/j1l/power_locked100.py
---

# Janus 1-L: the locked 100 resolves 0.011–0.021 tF1, more than 60 extra cases can be expected to buy

**Question.** Janus 1-L is judged against Janus 0 on the 100 locked cases (D45), paired per case. (1) How small a
macro-tF1 difference can 100 cases resolve, and how often does a neutral model pass a non-inferiority margin? (2) How
much should 60 more training cases (560 → 620, +10.7 %) be expected to add? (3) What did a warm continuation on the same
data do last time it was measured on this model family?

**Data and method.** `experiments/Atlas/j1l/power_locked100.py` (CPU, seconds). Output:
`experiments/Atlas/j1l/power_locked100.json`.
- **Paired SD of per-case Δ macro tF1:** the two measured pairs from Round 10
  ([[Atlas - Run-to-run noise in both measured pairs is per case, so a 35-patient decision set resolves about 0.02-0.035 tF1 and A22's 0.013 overstates it]]).
  - Optimistic: their measured SD(Δ), 0.038 and 0.041.
  - Pessimistic: their SD(Δ)/SD(case) ratios (0.57, 0.64) × Janus 0's per-case SD from #43 (0.117): 0.067 and 0.075.
    Janus 0's per-case spread is larger than the old thick-reference models', so this bracket is the realistic one
    for the ImageCAS-X reference.
- MDE = (1.96 + 0.84) × SD/√n (paired, two-sided 5 %, 80 % power; Julious 2004, doi:10.1002/sim.1783, §2.2.2).
  P(pass) uses the normal approximation to the case bootstrap.
- **Expected data gain:** Janus 0's error 1 − 0.909 scaled by (560/620)^α. Hestness et al. 2017
  (arXiv:1712.00409, §1: "β_g usually settles between −0.07 and −0.35") is the range for α; 0.5 is added as a
  generous upper case.
- **Warm continuation:** run 2's B (`trillium-results/round6/atlas2`) against the same model after 200 more epochs on
  the same data with the A17a warm-start trainer, peak LR 1e-2, 2500-iteration warm-up (atlas3 F0,
  `trillium-results/round7/atlas3`), paired on val 80. Thick D0-era reference: a sign and a size, not a transfer.

## Results

**Locked 100, Janus 1-L candidate vs Janus 0, macro tF1:**

| SD(Δ) | MDE (80 %) | P(NI at −0.01 passes), neutral model | P(NI at −0.02 passes), neutral model | P(superiority), true gain 0.005 | 0.01 | 0.02 |
|---|---|---|---|---|---|---|
| 0.038 (optimistic) | **0.011** | 0.75 | 1.00 | 0.26 | 0.75 | 1.00 |
| 0.041 (optimistic) | 0.012 | 0.68 | 1.00 | 0.23 | 0.68 | 1.00 |
| 0.067 (pessimistic) | 0.019 | 0.32 | 0.85 | 0.11 | 0.32 | 0.85 |
| 0.075 (pessimistic) | **0.021** | 0.26 | 0.76 | 0.10 | 0.26 | 0.76 |

At n = 80 (val 80 alone) the MDE is 0.012–0.024; at 120 it would be 0.010–0.019. The 20 locked open-36 cases buy about
10 % of resolution.

**Expected gain from 60 more cases (macro tF1):** α = 0.07: 0.0006; 0.2: 0.0018; 0.35: 0.0032; 0.5: 0.0045.

**Warm continuation on the same data (B → F0, n = 80):** Δ macro tF1 **−0.002, 95 % CI [−0.013, +0.007]**, SD(Δ)
0.046. Per class: LM −0.018, LAD −0.003, LCx +0.014, RCA −0.008. FP components per case +0.01.

## Reading

1. **More data alone will not be shown better.** The 60 cases should add about 0.001–0.005 tF1. The locked 100
   resolves 0.011–0.021. A data-only Janus 1-L passes a tF1 superiority test 10–26 % of the time even if its gain is
   real. A plan that defines "better than Janus 0" as tF1 superiority from the split alone is mostly a coin that lands
   on "no".
2. **A −0.02 non-inferiority margin is the workable one.** A neutral model passes it 76–100 % of the time. At −0.01 it
   passes 26–75 %, so a −0.01 margin would reject neutral fine-tunes about half the time. This matches Round 10's G2
   (−0.02) on the same reasoning.
3. **A warm continuation on in-distribution data neither helps nor harms**, within ±0.01. The cheap warm start is safe.
   It is not a lever by itself.
4. **So the lever has to be something with an expected effect of at least about 0.015 tF1, or an endpoint that
   resolves better than tF1.** Two candidates:
   - whole-tree Dice, where Janus 0's known one-voxel width shortfall ([[icx4 - Results]]: 1-voxel-tolerant Dice
     0.97 against plain 0.88, volume ratio 0.87) is a several-point effect, and the per-case SD is small (val p10–p90
     0.846–0.904);
   - an extent/connectivity loss aimed at tF1's failure mode (cut trees), which can plausibly move tF1 by more than the
     data does.

   [[Janus 1-L Atlas v1]] builds its decision on both.

**Limits.** Both paired SDs come from the D0-era thick reference and are scaled, not measured, for Janus 0. The first
real number is the a1 − a2 pair under [[Janus 1-L Atlas v1]]. The power law is a prior from other domains,
not a measurement on coronaries. B → F0 is a continuation after a truncated schedule, and it ran on the old labels.
