---
tags: [plans/experiment, round-10, D35, D27, A10, A22, A31, power, Janus-0]
author: Crucible
round: 10
updated: 2026-10-25
issue: christianGRogers/Asclepius#113
---

# On Janus 0's spread 150 sealed patients are enough only if reader and model errors correlate, and D35 beyond 35 patients buys almost nothing

**Questions.**
1. A31.1: re-power the A10 seal on Janus 0's own per-case val spread. Is 150 enough?
2. What does a D35 decision set of n patients resolve in a paired fine-tune comparison, once A22's seed term is
   included?
3. Which rule should size the seal from wave-1 reads?

**Method.** `experiments/Crucible/r10/r10_power.py` → `r10_power.json`, and `r10_seal_rule.py` →
`r10_seal_rule.json`. CPU only. Every input is a repository file. No sealed case and no read is opened.

## 1. Janus 0's per-case spread is wider than run 1's

Janus 0's per-case tF1 is not in the repository. Its spread follows from the bootstrap CIs on #43
(SD ≈ CI width / 3.92 × √n):

| | LM | LAD | LCx | RCA | Macro |
|---|---|---|---|---|---|
| Run 1 per-case SD (atlas2, val 80) | 0.081 | 0.078 | 0.111 | 0.079 | 0.064 |
| Janus 0 per-case SD (from the CIs) | 0.121 | 0.126 | 0.135 | 0.079 | 0.117 |
| Ratio | 1.49 | 1.61 | 1.22 | 1.00 | 1.82 |

Janus 0's macro CI is asymmetric (−0.029 / +0.022), so a few bad cases make its tail heavier. Sources:
- per-class CIs come from Delta's summary (expert ostium), the only per-class CIs published;
- the macro CI comes from the r9 scorer.

Bridge's Round 9 power table used run 1's spread. **Re-run on Janus 0's spread, 150 sealed patients pass a
human-level model less often than Round 9 assumed.**

## 2. A10 power at 150 / 200 / 250 on Janus 0's spread

**Model.** Bridge's `experiments/Bridge/wave1/power.py`, unchanged:
- run 1's empirical shape, rescaled to Janus 0's per-class mean and SD;
- scorable shares 0.85 / 0.95 / 0.95 / 0.95;
- inter-read drawn independently (ρ = 0).

The ρ = 0.5 column lets a patient's model-vs-read and inter-read deviations share a case-difficulty term.

P(all four classes pass), model exactly as good as a reader (δ = 0):

| f (pool spread / val) | k | n = 150 | n = 200 | n = 250 | n = 150, ρ = 0.5 |
|---|---|---|---|---|---|
| 1.0 | 1.0 | **0.76** | 0.90 | 0.96 | 0.995 |
| 1.0 | 1.2 | 0.65 | 0.84 | 0.93 | 0.99 |
| 1.2 | 1.0 | 0.51 | 0.71 | 0.85 | 0.96 |
| 1.5 | 1.0 | 0.23 | 0.39 | 0.55 | 0.75 |

- At δ = −0.02 (a model 0.02 worse than a reader), n = 150 and f = k = 1: 0.13 (0.59 at ρ = 0.5).
- A model 0.05 worse than a reader never passes at n = 150 (0.000).
- Bridge's run-1 figure for the first cell was 0.966.

**Reading.**
- With independent errors, Janus 0's spread puts 150 patients below 0.8. 200 is needed at f = k = 1, and 250 at
  f = 1.2.
- With a shared case-difficulty term (ρ = 0.5), 150 is ample even at f = 1.2.
- ρ has never been measured. For comparison, two networks scored on the same 80 val cases correlate at
  ρ = 0.67–0.88 per class (run 1 vs B, §3).
- **So the seal's size turns on a number only paired reads can give**, and D35's reads give it (§4).

## 3. Paired noise: what a fine-tune comparison on D35 resolves

The per-case SD of the **difference** between two trained networks on the same 80 val cases (atlas2/atlas3
results, thick-convention era, A1 ostium, flagged trees out):

| Pair | What | Macro SD(diff) | ρ | LCx SD(diff) |
|---|---|---|---|---|
| run 1 vs B | two from-scratch trainings (Round 6) | 0.041 | 0.79 | 0.103 |
| F0 vs F1 | two warm fine-tunes from B, same seed and data (Round 7) | 0.038 | 0.84 | 0.065 |
| B vs F1 | a base and its warm fine-tune | 0.031 | 0.88 | 0.078 |

**MDE.** Two-sided α 0.05, power 0.8, so MDE = 2.80 · √( (f·SD)²/n + σ_seed²/s ):
- σ_seed = 0.013 (A22), added as `r9_score_icx4.paired()` adds it;
- s = seeds per arm;
- SD scaled by Janus 0's/run 1's macro ratio (1.82), except in the "as measured" row.

| Contrast | f | Seeds/arm | n = 30 | n = 35 | n = 50 | n = 60 |
|---|---|---|---|---|---|---|
| Macro, warm vs warm, as measured | 1.0 | 1 | 0.042 | 0.041 | 0.039 | 0.039 |
| Macro, warm vs warm, × Janus 0 ratio | 1.0 | 1 | 0.051 | **0.049** | 0.046 | 0.044 |
| Same | 1.0 | 2 | 0.044 | 0.042 | 0.038 | 0.036 |
| Same | 1.25 | 1 | 0.058 | 0.055 | 0.050 | 0.048 |
| Macro, scratch vs scratch, × ratio | 1.0 | 1 | 0.053 | 0.051 | 0.047 | 0.045 |
| LCx, scratch vs scratch, × ratio | 1.0 | 1 | 0.074 | 0.070 | 0.062 | 0.058 |

**Reading.**
- Seed noise is about half the variance at n = 35. **Going from 35 to 50 patients improves the MDE by
  0.003–0.004**, and costs 15 patients of pool training data.
- D35 resolves **about 0.04–0.05 macro** at any affordable size. That is enough to see a domain-adaptation gain of
  that size (Janus 1 against Janus 0 on pool reads).
- It is **not** enough to see a warm-vs-scratch difference, which ImageCAS-era pairs put well under 0.02.
- So **warm vs scratch cannot be decided on D35** and must be decided by cost (Crucible v11 §4).

## 4. Sizing the seal: the measured contrast (rule D) against f/k > 1.2 (rule F/K)

**Rule F/K** (A31.1 as implemented in `report_wave1.py`):
- extend to 200 if any f or k > 1.2;
- extend to the maximum if Bridge's re-run power at 200 is < 0.8.

**Rule D** (proposed):
- on the D35 patients, take each patient's A10 contrast d = Janus 0-vs-reads − inter-read per class, as measured,
  so f, k and ρ enter together;
- centre it at 0;
- choose the smallest seal in {150, 200, 227} whose bootstrap P(all four pass) ≥ 0.8.

**Simulation.** 400 wave-1 samples of 30 patients per world (Janus 0-shaped spread, k = 1). True P(pass) is at the
size each rule picks:

| World (f, ρ) | True P at 150 / 200 / 227 | Rule D: mean size, expected P | Rule F/K: mean size, expected P |
|---|---|---|---|
| 1.0, 0 | 0.77 / 0.91 / 0.95 | 182, 0.86 | 202, 0.91 |
| 1.0, 0.5 | 0.995 / 1.0 / 1.0 | **150, 0.995** | 201, 1.0 |
| 1.2, 0 | 0.51 / 0.71 / 0.79 | 217, 0.76 | 220, 0.77 |
| 1.2, 0.5 | 0.96 / 0.99 / 1.0 | **155, 0.96** | 219, 1.0 |
| 1.5, 0 | 0.23 / 0.39 / 0.48 | 227, 0.48 | 227, 0.48 |
| 1.5, 0.5 | 0.75 / 0.91 / 0.94 | 193, 0.87 | 227, 0.94 |

**Reading.**
- When reader and model errors share case difficulty, rule D keeps the seal at about 150, still above 0.95 power.
  That releases 50–77 reserve patients to training.
- Rule F/K extends anyway, because at 30 patients its eight SD ratios exceed 1.2 by chance (71 %, Bridge's own
  `trigger_false_alarm.py`).
- When errors are independent, rule D is slightly less conservative than F/K (0.86 vs 0.91 expected power at
  f = 1), but still above its 0.8 target.
- In the hard worlds both rules hit the cap equally.
- **Rule D answers the question the seal asks, with the quantity that decides it.**

## What it changes

- **The acceptance set:** 150 is not enough on Janus 0's spread if errors are independent. It is enough if they
  correlate. Decide on D35's measured contrast (rule D), with **200 as the default** if D35 is not read in time.
  The cap is 227 once D35 is skipped from the extension order.
- **D35 size:** 35 patients. Larger buys almost nothing, because A22's seed term dominates.
- **Warm vs scratch** is below D35's resolution, so it is decided by cost.

## Limits

- Janus 0's SDs come from CIs, not per-case data. The run-1 shape stands in for Janus 0's.
- The paired SDs come from the thick-convention era and are scaled.
- ρ is a scenario until D35 is read.
- Rule D uses Janus 0 as the model. The final model's contrast may differ, and the rule says so in its report.
