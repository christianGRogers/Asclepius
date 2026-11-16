---
tags: [experiment, track-1-L, round-2, janus1-l, ensemble, locked-100, power, D46]
author: Crucible
track: 1-L
round: 2
updated: 2026-11-13
issue: christianGRogers/Asclepius#302
code: experiments/Crucible/j1l_r2/ensemble_oc.py
---

# Testing the two-run ensemble in a1's place raises a neutral model's non-inferiority pass rate and cuts the chance of shipping an unlucky draw, with no second look

## Question

[[Janus 1-L Round 1]] §5 item 1 asks whether the ship candidate should be a1 or E (the mean softmax of a1 and a2), and,
if E, how it is tested without a second look. D46 Q6 accepts an ensemble in principle if round 2 pre-registers it.

If E **replaces** a1 in the same H1 → H2 → H3 sequence, the locked 100 are still looked at once. What does the swap do
to the tF1 tests?

## Setup

CPU simulation, `experiments/Crucible/j1l_r2/ensemble_oc.py` → `ensemble_oc.json` (20 000 studies per row, n = 100).
No image, label, read, locked-100 score or sealed case is opened.

**The model** of the per-case paired difference against Janus 0:

> D_X(c) = δ + g_X + d(c) + r_X(c)

| Term | Meaning | Value |
|---|---|---|
| δ | the recipe's true effect, shared by a1, a2 and E | −0.02 … +0.01 |
| d(c) | the per-case part of that effect that every run shares | variance S² − σ_r² |
| r_X(c) | a run's own per-case part | σ_r = 0.027, from the warm pair atlas3 F0 − F1 (SD 0.038 over 80 val cases; heavy-tailed shape resampled) |
| g_X | a run's own mean offset (A37's "seed lottery") | σ_g ∈ {0.004, 0.008, 0.012}. The F0 − F1 mean gives a 1-df 0.001; A37's floor is 0.012 |
| S | total paired SD of (candidate − Janus 0) | 0.038, 0.055, 0.074 (round 1's range) |

**The ensemble.** Averaging two networks' softmax is not averaging their scores. So E's run-specific variance (in r and
in g) is written as κ × a single run's:
- κ = 0.5: E behaves like the mean of its two members' scores (the most it can gain);
- κ = 0.75: half that gain;
- κ = 1: no gain (equal to a1 by construction, not tabulated).

An ensemble *mean* bonus β is 0 (nothing claimed) or +0.003 (sensitivity only).

**The tests** (one-sided 2.5 %, t-bound, as round 1's power scripts):
- H1's macro clause: lower bound > −0.02. The class, L3 and FP clauses are not modelled.
- D46 Q4's adoption: lower bound > −0.015.
- H3: lower bound > 0.

Also computed: P(the shipped model is truly worse than Janus 0 by more than 0.01), i.e. δ + g (+ β) < −0.01.

## Result

**A neutral recipe (δ = 0, β = 0):**

| S | σ_g | κ | P(H1) a1 → E | P(Q4 adopt) a1 → E | P(shipped model truly < −0.01) a1 → E |
|---|---|---|---|---|---|
| 0.038 | 0.004 | 0.5 | 0.981 → 0.997 | 0.896 → 0.964 | 0.007 → 0.000 |
| 0.038 | 0.008 | 0.5 | 0.917 → 0.977 | 0.800 → 0.897 | 0.102 → 0.040 |
| 0.038 | 0.012 | 0.5 | 0.839 → 0.929 | 0.725 → 0.825 | 0.203 → 0.119 |
| 0.055 | 0.004 | 0.5 | 0.887 → 0.922 | 0.722 → 0.774 | 0.007 → 0.000 |
| 0.055 | 0.008 | 0.5 | 0.821 → 0.886 | 0.672 → 0.737 | 0.107 → 0.038 |
| 0.055 | 0.008 | 0.75 | 0.819 → 0.852 | 0.669 → 0.701 | 0.107 → 0.075 |
| 0.055 | 0.012 | 0.5 | 0.749 → 0.826 | 0.628 → 0.683 | 0.209 → 0.122 |
| 0.055 | 0.012 | 0.75 | 0.751 → 0.787 | 0.626 → 0.651 | 0.206 → 0.170 |
| 0.074 | 0.008 | 0.5 | 0.689 → 0.731 | 0.533 → 0.558 | 0.106 → 0.038 |
| 0.074 | 0.012 | 0.5 | 0.658 → 0.704 | 0.534 → 0.555 | 0.199 → 0.116 |

**H3 (tF1 superiority) at δ = +0.005, S = 0.055, κ = 0.5:**

| σ_g | β = 0: a1 → E | β = +0.003: a1 → E |
|---|---|---|
| 0.004 | 0.236 → 0.245 | 0.236 → 0.402 |
| 0.008 | 0.300 → 0.283 | 0.295 → 0.412 |
| 0.012 | 0.341 → 0.325 | 0.342 → 0.431 |

**What the tables show:**
1. **On every non-inferiority row E passes at least as often as a1**, by 1–10 points. Two things drive this: the
   per-case paired SD falls (0.054 → 0.050 at S = 0.055), and the run offset g shrinks.
2. **E cuts the chance that the shipped model is an unlucky draw** (truly worse than Janus 0 by more than 0.01 with a
   neutral recipe) by about 30–65 % wherever σ_g ≥ 0.008.
3. **E does not raise H3's power unless it has a real mean bonus.** With β = 0 and a large σ_g it is 1–2 points lower.
   Part of a1's H3 "power" is lucky run offsets, which E averages away. That is the variance argument working as
   intended, not a cost.
4. **At σ_g = 0.004 (closest to the one measured pair) the swap matters little**, either way. It never hurts.

## Limits

- **E's κ is not measured.** Two warm runs from one parent are highly correlated, so κ is likely nearer 0.75–1 than
  0.5. The table brackets it. At κ = 1, E is a1's equal.
- **The one warm pair has an FP-term difference** (F1's FP-aware loss, Round 8). It changed nothing detectable, and
  Delta used the same pair as a replicate.
- **The class guard, L3 and FP are not modelled.** E's per-class run noise also falls, so L3's false-alarm rate can
  only fall. FP: an averaged softmax can create or remove small blobs. A15 still binds at the gate.
- **Dice (H2) is not modelled.** Run noise in whole-tree Dice is much smaller than in tF1 (the width deficit is
  systematic). The swap should matter little there.

## What it changes

Crucible v2 §1 makes **E the one pre-registered candidate**, tested in a1's place in the same sequence. a1 drops to a
report. The swap costs one extra inference pass (about 1 GPU-min per case) and no extra look.
