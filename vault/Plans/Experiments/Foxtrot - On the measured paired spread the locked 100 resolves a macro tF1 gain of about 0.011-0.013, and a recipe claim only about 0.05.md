---
aliases: [Foxtrot locked-100 power]
tags: [plans, experiment, janus1-L, D45, power, cpu]
status: done (CPU, 2026-11-11)
issue: christianGRogers/Asclepius#302
track: 1-L
---

# On the measured paired spread, the locked 100 resolves a macro tF1 gain of about 0.011–0.013, and a recipe claim only about 0.05

**Question.** D45 fixes 100 locked validation cases for Janus 1-L: Janus 0's val 80 plus 20 of open-36. Issue #302
asks each plan for a pre-registered decision on them, "with power on Janus 0's per-case spread". Three things follow:
- which 20 open-36 cases are locked;
- how small a gain over Janus 0 a paired test on 100 cases can detect;
- how often a class guard fails a model that changed nothing.

**Code.** `experiments/Foxtrot/j1l/`:
- `locked100.py` pins the list;
- `locked100_power.py` runs the simulation;
- `locked100_decide.py` applies the pre-registered rule of [[Candidates/Janus 1-L/Foxtrot v1|Janus 1-L Foxtrot v1]] §4 to two scorer outputs. Its self-test passes.

Outputs are in `results/`. All of it runs on CPU in seconds. No image, label or sealed case is read.

## 1. The locked 20 (D45's rule, computed)

The rule ranks open-36 by `sha256('asclepius-janus1-locked100:' + id)`, with ids as in [[Sealed test]], and takes the 20 smallest:

> **Locked 20:** c0068, c0102, c0251, c0271, c0323, c0327, c0470, c0545, c0592, c0620, c0644, c0805, c0807, c0824, c0827, c0841, c0908, c0946, c0957, c0996
>
> **Trained 16:** c0123, c0195, c0340, c0416, c0430, c0435, c0447, c0617, c0624, c0660, c0726, c0758, c0772, c0877, c0971, c0984

- sha256 of the comma-joined locked-20 list: `81b6b526…c7c6f4dc` (full value in `results/locked100.json`).
- None of the 36 + 44 cases is sealed. The script asserts this.
- Val 80 and train 560 are ImageCAS-X's own split. That split is not in the repository; it is `$SCRATCH/icx4/splits.json` on Fir. So the
  launcher must pin those lists from that file (§ role:swe in the plan).

## 2. Power of a paired decision at n = 100

**Spread used.** Janus 0's per-case file (`r9_tf1_val.json`) is on Fir, not here. The best measured stand-in is the
per-case paired difference of the three real paired runs on val 80 in `trillium-results/`. They use the same A1 scorer family
and the pinned tF1:

| Pair | What it is | Macro SD of the per-case difference | MDE (80 % power, two-sided 0.05), n = 80 / 100 |
|---|---|---|---|
| F1 − F0 (atlas3) | two warm fine-tunes from one base | 0.038 | 0.012 / 0.011 |
| B − run1 (atlas2) | two from-scratch recipes | 0.041 | 0.013 / 0.012 |
| F0 − B (atlas3 vs atlas2) | a warm fine-tune against its own base: **the closest analogue of Janus 1-L vs Janus 0** | 0.046 | 0.014 / 0.013 |

**Method.** Each pair's per-case macro differences are centred, resampled to n cases, shifted by a true gain Δ and
tested with the paired 95 % interval. There are 20 000 simulations per cell. On the real F0 − B vector, the t-interval and the percentile bootstrap
agree: [−0.0125, 0.0078] against [−0.0128, 0.0072].

**P(lower 95 % bound > 0)**, i.e. "shown better", at n = 100 (n = 80 in brackets):

| True Δ macro tF1 | F1 − F0 spread | B − run1 spread | F0 − B spread |
|---|---|---|---|
| 0 | 0.01 (0.01) | 0.03 (0.03) | 0.04 (0.04) |
| 0.005 | 0.22 (0.18) | 0.25 (0.21) | 0.24 (0.21) |
| 0.010 | 0.79 (0.70) | 0.68 (0.58) | 0.60 (0.53) |
| 0.0125 | 0.95 (0.89) | 0.85 (0.77) | 0.76 (0.68) |
| 0.015 | 0.99 (0.97) | 0.95 (0.89) | 0.87 (0.81) |
| 0.020 | 1.00 | 1.00 | 0.98 (0.94) |

**P(lower bound > −0.01)** ("non-inferior") for a model that changes nothing (Δ = 0) is 0.79 / 0.68 / 0.61 across the three spreads.
At Δ = 0.005 it is 0.88–0.99.

**What the 20 added cases buy.** At the same power, going from n = 80 to n = 100 lowers the MDE by about 0.0015. At Δ = 0.0125
it raises power by 6–9 points.

## 3. A recipe claim is about four times coarser

A37 says a claim that one *recipe* beats another includes the seed term, max(measured σ, 0.012) per run. With that
term, the MDE at n = 100 is **0.049** for every spread above, because the seed term dominates. So the locked 100 can tell
"this checkpoint beats Janus 0" at about 0.012. It cannot tell "warm start beats from scratch" or "loss X beats loss Y" unless
the gap is about 0.05.

## 4. How often a class guard fails a neutral model

This is the probability that some class's mean Δ falls below the guard when nothing changed. Classes are resampled independently;
that is the conservative case, since class errors correlate positively.

| Guard | F1 − F0 | B − run1 | F0 − B |
|---|---|---|---|
| any class < −0.02 | 0.040 | 0.035 | 0.088 |
| any class < −0.03 | 0.003 | 0.004 | 0.022 |

LM drives the −0.02 failures: its per-case paired SD is 0.12 in two pairs, because LM tF1 often sits at 0 or 1. **−0.03 is the
guard to use** (it is also A38's G2 class line).

## Limits

- The spreads come from D0-era and atlas-family models on val 80, not from Janus 0. Janus 0's own paired spread
  against a fine-tune of itself is unknown until Janus 1-L exists. Janus 0's per-class model SDs, derived from its CIs (LM 0.121, LAD 0.126,
  LCx 0.135, RCA 0.079; Round 10 §2), are similar to these models' (paired_noise.json `model_sd`: 0.06–0.14). So the
  MDE above is the right order, not an exact value.
- The 20 open-36 cases are slightly easier than val 80 (Janus 0: 0.919 against 0.909 on all of open-36). That changes the mean,
  not the paired SD.

## What it changes

- **The locked-100 decision can only call Janus 1-L "better" if its gain is about ≥ 0.012 macro tF1.** A gain from 60
  extra cases alone is unlikely to be that large (Foxtrot v1 §3.4). So the plan's levers must be chosen for size: an
  ensemble of the two runs, not a recipe tweak.
- Recipe questions (warm against scratch, loss changes, LR) cannot be settled on the locked 100. They should not be
  asked of it.
- The class guard is −0.03. A non-inferiority margin of −0.01 passes a neutral model 61–79 % of the time.
