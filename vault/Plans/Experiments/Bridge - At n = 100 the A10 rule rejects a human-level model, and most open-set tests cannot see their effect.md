---
tags: [plans/experiment, statistics, evaluation, A10, A14, power, multiplicity]
author: Bridge
round: 6
updated: 2026-10-10
---

# At n = 100 the A10 rule rejects a human-level model, and most open-set tests cannot see their effect

## Question (Round 6, Q3)

Using the real per-case results in `trillium-results/round5/`, four questions:

1. What paired effects can the sealed 80 + 20 test, the val 80 and the open 36 detect, per class and for macro tF1?
2. What does A10 (per-class non-inferiority to inter-read tF1, margin 0.02, paired bootstrap lower bound) mean at n = 100?
3. How many decisions does the plan make, and does it need a multiplicity correction?
4. Are the open sets large enough for the decisions assigned to them?

## Data and method

- **Per-case tF1 distributions.**
  - The master on Atlas val: 80 cases, `bridge/results/cases`, arm D.
  - The master on the open ImageCAS-X test: 63 cases, `delta/results/per_case.jsonl`.
- **Paired per-case differences of four kinds:**
  - renaming on the same lumen: R/H/O − D;
  - inference: tile step 0.75 vs 0.5;
  - post-processing: P1′ vs raw;
  - *retrained networks*: Crucible's both/single/agree/a11 arms, 50 cases.
- **The A10 contrast itself:** Crucible's per-case (model-vs-reads − inter-read) per class. These are
  simulated reads in a strong-habit regime, from a small-patch model. They are the only per-case
  inter-read data that exist.
- **MDE:** minimum detectable effect, paired t, two-sided α = 0.05, power 0.8.
- **A10 pass probabilities:** simulated with the implemented rule (`segtrain.reads.acceptance`,
  percentile bootstrap). Whole cases are resampled, so correlations between classes are kept, and the
  contrast vectors are re-centred on a chosen true difference δ.
- Scripts: scratch `stats/power.py`, `stats/power2.py`. CPU only; no sealed case was read.

## 1. Spread of the per-case scores

| Master tF1 per case | LM | LAD | LCx | RCA | macro |
|---|---|---|---|---|---|
| SD, Atlas val (n = 80) | 0.135 | 0.160 | 0.171 | **0.321** | 0.147 |
| SD, open test (n = 63) | 0.223 | 0.209 | 0.217 | **0.324** | 0.174 |
| Cases < 0.5, open test | 5 % | 5 % | 6 % | **14 %** | 6 % |

- The scores are heavy-tailed. The RCA's spread comes from whole-tree zeros: ostium artefacts and real
  cuts.
- Removing tails, as the A1b flagged-tree review will partly do, changes every power figure below by a
  factor of about 2.

## 2. What paired comparisons can detect

SD is the per-case paired difference; MDE is the minimum detectable effect at each n.

| Contrast type (example) | SD, macro | MDE n = 100 (sealed) | n = 80 (val) | n = 36 (clean open) | n = 27 (Delta's clean) | Worst class, MDE at n = 80 |
|---|---|---|---|---|---|---|
| Same lumen, renaming (O − D) | 0.024 | 0.007 | 0.008 | 0.011 | 0.013 | LM 0.025 |
| Same lumen, renaming (R − D) | 0.053 | 0.015 | 0.017 | 0.026 | 0.030 | LM 0.033 |
| Inference (tile step) | 0.025 | 0.007 | 0.008 | 0.012 | 0.014 | LM 0.034 |
| Post-processing (P1′) | 0.034 | 0.010 | 0.011 | 0.016 | 0.019 | RCA 0.036 |
| **Retrained network** (both vs single) | **0.070** | **0.020** | **0.022** | **0.034** | **0.039** | LM 0.065, RCA 0.052 |
| Retrained network (agree vs both) | 0.032 | 0.009 | 0.010 | 0.015 | 0.018 | LCx 0.023 |

**Reading.**

- A paired comparison between two *trained models* (window ablation, A3/A4 ablations, the A11 test,
  team-only vs team + proxy, 5-fold vs single) detects about **0.02 macro** at n = 80–100. Per class it
  detects 0.03–0.06 for LM and RCA. Smaller true effects end as ties.
- Comparisons on the *same predictions* (post-processing, inference settings, naming) detect about
  0.007–0.015 macro at n = 80–100.

## 3. A10 at n = 100: the rule as written is a superiority test

The A10 contrast has a per-case SD of **0.14 (macro) to 0.19 (LCx, RCA)**. Its two parts are nearly
uncorrelated (ρ = 0.03–0.09; LM 0.57): a case hard for the model is not hard for the readers. Pairing
therefore buys almost nothing.

Probability that a model **passes** A10 on the 100 sealed cases, by true mean difference δ
(model-vs-reads minus inter-read):

| δ | LM | LAD | LCx | RCA | macro | **All four classes** (the rule) |
|---|---|---|---|---|---|---|
| −0.02 (at the margin) | 0.04 | 0.07 | 0.05 | 0.03 | 0.07 | 0.00 |
| **0 (exactly human-level)** | 0.28 | 0.30 | 0.23 | 0.20 | 0.32 | **0.00** |
| +0.02 | 0.80 | 0.68 | 0.59 | 0.57 | 0.78 | 0.24 |
| +0.04 | 0.97 | 0.92 | 0.88 | 0.82 | 0.95 | 0.70 |
| 0, tails trimmed (A1b-like) | 0.64 | 0.56 | 0.34 | 0.56 | 0.81 | 0.06 |

- **A model exactly as good as a second annotator fails A10 almost surely.** It needs to *beat* the
  inter-read agreement by about 0.04 in every class to pass with 70 % probability.
- The sample size that would give 80 % power at δ = 0 is 380–680 cases per class.
- At n = 100, the margin giving 80 % power at δ = 0 is **0.04 macro and 0.045–0.05 per class**.
- The type-I side is fine: a model 0.02 worse than readers passes with probability ≤ 0.07 per class,
  and essentially never on all four.

Caveat: the SD comes from simulated reads. The master's own per-case SD (§1) is at least as large, so
the real figures are unlikely to be better. If real inter-read tF1 is near 1 with little spread,
σ_d ≈ σ_model, which is about the same.

## 4. Other acceptance and decision rules

- **FP gate (≤ 1 per case, A15).** Per-case SD is 1.31. Read as a point estimate at n = 100, a model
  with a true rate of 1.1 still passes 16 % of the time, and one at 0.9 fails 10 %. The rule does not
  say whether it reads the point estimate or a bound.
- **Epoch rule** ("R1 vs 412 epochs differ by < 0.01 on val"; SE ≈ 0.008 at n = 80). The probability
  that it reports "< 0.01" is:
  - 0.80 if the true gain is 0;
  - 0.49 if the true gain is 0.01;
  - 0.10 if the true gain is 0.02.

  That is acceptable for a compute decision, but it is a coin flip at exactly the threshold.
- **Window ablation (A16 Phase B, val 80, retrained).** MDE is 0.022 macro. Most plausible window
  effects will be ties, so the decision will in practice be made by the FP tie-break.

## 5. Decisions on the open sets

| Decision | Set | Effect the test needs to see | MDE there | Verdict |
|---|---|---|---|---|
| P1′ (Delta) | 27–36 clean open | ≤ 0.004 (Round 5 bound) | 0.016–0.019 | **Cannot detect.** The headroom is a quarter of the MDE. |
| Gated subtree renaming (Bridge v5 §2.3) | 36 clean open | ≤ ~0.005 (part of O − D = 0.010) | 0.011–0.026 | **Cannot detect.** Withdrawn in v6. |
| A1 flag rate (A1b budget) | 36 / 80 | a rate around 0.2 | ±0.13 / ±0.09 (95 % CI half-width) | Enough for budgeting, not for comparing rules |
| Threshold T (A15), P2 | val 80 | not stated | 0.008–0.011 (same predictions) | Adequate if the pre-registered gain is ≥ 0.01 |

## 6. How many decisions, and is a correction needed?

**Adoption decisions** that can add something to the final recipe, each "adopt if the paired CI
excludes 0". There are about 11:

1. P1′
2. P2
3. threshold T
4. window
5. A1 native spacing
6. A3 rotation
7. A4 Skeleton Recall
8. the A11 test
9. 5-fold vs single
10. team-only vs team + proxy
11. gated renaming

If every one were truly null, the chance of at least one false adoption (one-sided 2.5 % each) is
**24 %**. Most of them reuse the same val 80, and the components are stacked into one final model that
is never itself compared with the baseline.

The other decision kinds need little or no correction:

- **Forced choices**, where one option must be taken anyway (window, A11 form, 5-fold vs single), need
  no correction. A wrong pick with a tiny true difference costs little.
- **A10** is an intersection-union test: all four classes must pass. That needs no correction for
  type I; its problem is power (§3).
- **Per-class results** in every table are reported, not decided on. They need no correction provided
  no adoption ever rests on a single class, which should be stated.
- **Repeated looks at the sealed test.** [[Sealed test]] says it is scored "at milestones" without
  saying how many. Every look that informs a later choice spends the set.

## Proposed changes

1. **A10, the human decision on the margin (the ruling's §6 item 3).** Give the clinical lead this
   table, not just "0.02". At n = 100, a 0.02 margin per class means "must beat a second reader by
   about 0.04". Options, all pre-registered before the reads exist:
   - **(a)** a margin of 0.05 per class, with macro as the primary at 0.04; or
   - **(b)** keep 0.02 but on **macro only** as the primary. Per class becomes descriptive, with a
     safety floor: no class point estimate below −0.05.

   Either way, run the **A1b review before sealed scoring.** The tails it removes roughly double the
   power.
2. **One decisive look at the sealed test** (the final model), plus at most one pre-declared interim
   look that cannot change any recipe decision. Every other evaluation uses val or open sets.
3. **Every pre-registered decision table states its MDE at its n.** If the expected effect is below
   the MDE, the test is reported-only and the default stays.
   - On this basis, P1′ (Delta) and my gated renaming are closed now, saving the open-36 GPU
     predictions for other uses.
4. **Adoption family:** a final confirmatory paired test of the stacked recipe on the sealed test,
   final vs the R1 baseline, at the end. This is one test, and it protects against accumulated false
   adoptions without Holm-correcting eleven small decisions.
   - If extra protection is wanted, require adoptions that change the *training* recipe (the retrained
     contrasts) to replicate on the open 36 with the same sign.
5. **FP gate:** state that it reads the point estimate on the 100 sealed cases, with the CI reported.
6. **Epoch rule:** keep it, adding that it needs the upper CI of the gain to be < 0.02. Otherwise
   there is a 49 % chance of a wrong "no gain" call at a true 0.01.

## Caveats

- The A10 contrast SD comes from simulated reads and a small model. Wave 1 (A12) should re-estimate it
  on real reads before the margin is frozen. That costs no GPU: score the R1 model against wave-1 reads.
- The MDEs assume normal paired differences. These differences are heavy-tailed, and percentile
  bootstrap CIs at n = 27–36 under-cover slightly. That raises the false-adoption risk a little; it
  does not rescue the power verdicts.
