---
tags: [plans/experiment, statistics, evaluation, A1, A10, A16, seeds, power]
author: Bridge
round: 8
updated: 2026-10-11
---

# With A1 scoring the sealed test detects about 0.012 tF1, but seed noise doubles every training comparison

## Question (Round 8)

1. Redo the Round 6 power and MDE table with the real A1-scored per-case tF1, flagged trees excluded
   (A1b).
2. Can the window ablation (paired n = 80, B at 368 epochs vs run 1 at 412) support a decision, and
   what was its MDE?
3. What is the seed-to-seed SD of a paired arm difference (Crucible seeds 1 and 2), and what does it
   imply for the plan's single-seed decisions?

## Data

- `trillium-results/round6/atlas2/results/per_case_run1.json` and `per_case_b.json`: 80 val cases,
  `segtrain.tf1` at the frozen hash, aorta ostia, per-class flags.
- `round5/crucible` and `round6/crucible_seed2`: the same 50 test cases and the same 6 arms, two seeds.
- `training_log` files for the epoch question.
- Scripts: scratch `stats/power3.py`. CPU only; no sealed case was touched.

## 1. With A1 the per-case spread falls 2–4×, so Round 6's numbers were too pessimistic

| Run 1, val 80 | LM | LAD | LCx | RCA | decisive macro |
|---|---|---|---|---|---|
| n unflagged | 72 | 72 | 72 | **56** | 80 |
| Mean | 0.966 | 0.901 | 0.846 | 0.883 | 0.896 |
| SD, unflagged (Round 6, provisional ostia) | 0.081 (0.135) | 0.078 (0.160) | 0.111 (0.171) | 0.079 (**0.321**) | 0.064 (0.147) |
| SD, flagged trees included | 0.085 | 0.076 | 0.109 | 0.207 | 0.068 |

- The heavy tails of Round 6 (RCA zeros) were ostium artefacts. A1 removes most of them; the 24
  flagged RCA trees carry the rest.
- **The cost is the RCA n.** 30 % of RCA trees are flagged, so until the A1b review clears them the
  sealed test has about 70 scorable RCAs, not 100.

**Minimum detectable effects (80 % power, two-sided 0.05), using the paired SDs of a real retrained
contrast (B − run 1).** The first three columns ignore seed noise; the last includes it.

| | LM | LAD | LCx | RCA | decisive | decisive incl. flagged |
|---|---|---|---|---|---|---|
| Paired SD | 0.050 | 0.047 | 0.103 | 0.039 | **0.041** | 0.085 |
| MDE, n = 100 (sealed) | 0.014 | 0.013 | 0.029 | 0.011 | **0.012** | 0.024 |
| MDE, n = 80 (val) | 0.016 | 0.015 | 0.033 | 0.012 | **0.013** | 0.027 |
| MDE, n = 36 (clean open) | 0.024 | 0.022 | 0.049 | 0.018 | **0.020** | 0.040 |
| **MDE, single seed per arm, seed SD included (§3)** | | | | | **≈ 0.038** | |

Excluding flagged trees halves every MDE. A1b is a power decision as well as a correctness one.

## 2. A10 redone with the real model spread

The inter-read spread is still only simulated, so three scenarios are shown. ρ ≈ 0 between the model's
and the readers' per-case scores (Crucible).

| Scenario for inter-read SD | P(pass) at δ = 0, macro | P(pass), all four classes | Margin for 80 % power at δ = 0 (macro / worst class) |
|---|---|---|---|
| As simulated (LM 0.165, others 0.05–0.08) | 0.49 | 0.01 | 0.029 / LM 0.054 |
| = model SD | 0.60 | 0.01 | 0.025 / LCx 0.046 |
| = half the model SD | 0.80 | 0.05 | 0.020 / LCx 0.037 |

- Round 6's conclusion holds, more weakly. **Per-class, all four classes at 0.02 still rejects a
  human-level model 95–99 % of the time.**
- **Macro-only at 0.02 is now about a coin flip to near-adequate.** Round 6 put it at 0.32.
- E1 of Bridge v6 is therefore revised (Bridge v7):
  - macro primary at 0.02–0.03;
  - per class reported, with a floor.
- The real inter-read SD from wave 1 decides between those values.

## 3. Seed noise: training comparisons are about 1.8× noisier than their CIs say

The same 15 arm contrasts were scored against the truth and against the reads, giving 30 contrasts in
each of two seeds on identical test cases:

- **The seed-to-seed SD of a paired arm difference is 0.013.** It is 0.008 against the truth and 0.016
  against the reads.
- The case-bootstrap SE of the same contrasts is 0.007, so a single-seed CI is too narrow by a factor
  of about **1.8**. It covers the seed-averaged effect about **66 %** of the time, not 95 %.
- **Sign flips:** 4 of 15 contrasts against the truth and 7 of 15 against the reads change sign.
  Significance changes in 5 of 15 for each reference.
- **The decisive Round 5 contrast is one of the flips.** a11 − both against the reads was −0.035
  [−0.046, −0.023] in seed 1 and +0.011 in seed 2. A11′ was adopted on seed 1. It is still the simpler
  rule, but the evidence that a11 is *worse* is gone.
- **What replicates:** both > single against the truth (+0.030, +0.016), and union worst against the
  reads.
- Seed noise does not shrink with more test cases. For training-recipe decisions, the limiting
  resource is **seeds, not cases**.
- Caveat: this is a small model (96 × 160 × 160, 300 epochs, 200 cases). The master's seed SD is
  unmeasured and could be smaller.

## 4. The window decision (A16 Phase B)

| B − run 1, n = 80 | Mean | 95 % CI | MDE (cases only) | MDE incl. seed SD |
|---|---|---|---|---|
| Decisive tF1 | −0.003 | [−0.012, +0.006] | 0.013 | ≈ 0.038 |
| LCx (worst class) | −0.019 | [−0.043, +0.006] | 0.033 | — |
| Incl. flagged trees | −0.013 | [−0.032, +0.006] | 0.027 | — |
| FP components per case | −0.19 | [−0.48, +0.10] | **0.42** | — |

**Can it support a decision?**

- **As equivalence on tF1, partly.** The case CI excludes a gain or loss larger than about 0.012.
  Allowing for seed noise, it excludes only about ±0.03.
- **As "default wins on FP", no.** The FP tie-break used a point estimate whose CI spans 0. The MDE for
  FP at n = 80 is 0.42 per case, more than twice the observed difference. The rule as written was
  applied correctly, but the FP tie-break here is close to a coin flip.
- **The epoch mismatch is probably not what decided it, but this is untested in tF1.**
  - B stopped at its deadline at epoch 368 with the LR schedule planned for 412: LR 0.0014, never
    annealed to 4 × 10⁻⁵.
  - In run 1, the last 44 epochs changed mean pseudo-Dice by under 0.001 (0.8402 at epochs 348–367 vs
    0.8401 at 392–411).
  - So the truncation bias in voxel terms is far below the MDE. Its effect on tF1 and FP (the LCx
    −0.019) is not identifiable from these runs.
- **Reading.** The two windows are indistinguishable at the resolution this design has. Choosing the
  default is harmless, but it is a choice, not a finding. The FP census (79 % `confident_other`) says
  the window is not the FP lever, whichever window is chosen.

## 5. What this means for each single-seed decision

| Decision (round) | Contrast type | Seed noise enters? | Status after §3 |
|---|---|---|---|
| A7: R/H vs D (5) | Naming on fixed predictions | Weakly (through D's errors) | Stands; the effect sizes are 2× the case CI and the swaps are structural |
| A2: P1′, bridging, tile step (5) | Post-processing and inference on fixed predictions | Weakly | Stands (null, or closed by the MDE) |
| A11′ vs a11, against the reads (5) | Retrained networks | **Fully** | **Not supported.** It reversed in seed 2; A11′ stands only as the simpler rule |
| both > single (5) | Retrained | Fully | Replicated in 2 seeds |
| Window B vs run 1 (8) | Retrained, 1 seed, unequal epochs | Fully | Equivalence at ±0.03; not decisive |
| Future: A3/A4 ablations, A11 test, team-only vs team + proxy, 5-fold vs single | Retrained | Fully | Need ≥ 2 seeds per arm, or a seed-inflated CI |

## Caveats

- The seed SD is from one small-model setup with two seeds. It is the only measurement available.
- The inter-read SD is simulated. Wave 1 replaces it.
- The MDEs assume roughly normal paired differences. After A1 they are much less heavy-tailed than in
  Round 6.
