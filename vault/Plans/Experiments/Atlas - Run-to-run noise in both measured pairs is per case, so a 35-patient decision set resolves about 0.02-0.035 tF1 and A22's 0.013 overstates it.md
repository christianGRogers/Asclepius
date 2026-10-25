---
tags: [plans/experiment, round10, D35, A22, power, seed, fine-tune]
author: Atlas
round: 10
updated: 2026-10-25
issue: christianGRogers/Asclepius#113
code: experiments/Atlas/r10_paired_power.py
---

# Run-to-run noise in both measured pairs is per case, so a 35-patient decision set resolves about 0.02–0.035 tF1, and A22's 0.013 overstates it

**Question.** A wave-1 fine-tune question (A17, A22) is a paired comparison of two models on the D35 decision set,
both scored against the same reads. How small an effect can n decision patients resolve? Does A22's
σ_seed = 0.013 belong outside the paired case CI (a whole-model shift that no number of cases removes) or inside it
(per-case noise that the case CI already sees)?

**Data.** Both pairs are on the same 80 ImageCAS val cases, scored at the A1c-pinned tF1 with TotalSegmentator
aortas. The reference is the thick D0-era one, so only ratios are carried over to Janus 0.

- **Warm replicate.** Atlas run 3, F0 vs F1 (`trillium-results/round7/atlas3`).
  - Both arms warm-start from run 2's B with the A17a trainer: seed 12345, the same data stream, 200 epochs.
  - F1's FP term stayed at 1e-4 of the loss ([[Atlas - Run 3 result, the FP-aware loss was too weak to test]]).
  - So F1 − F0 is, to a good approximation, a replicate of one warm fine-tune, differing by GPU nondeterminism.
- **Scratch pair.** Atlas run 2, run 1 vs B (`trillium-results/round6/atlas2`).
  - Two from-scratch trainings (fixed vs default window, 412 vs 368 epochs), judged a tie in Round 8.
  - An upper bound on the noise between two separately trained models of one recipe.
- **Janus 0's per-case spread** comes from its posted CIs (#43): SD ≈ CI width / 3.92 × √n. Checked on run 1, where
  the per-case file exists: 0.0647 from its bootstrap CI against 0.0645 directly.

## Results

| | Warm replicate F1 − F0 | Scratch pair B − run 1 |
|---|---|---|
| n | 80 | 80 |
| Mean paired Δ macro tF1 | +0.0047 | −0.0027 |
| SD of per-case Δ | **0.038** | **0.041** |
| SE of the mean (case only) | 0.0043 | 0.0046 |
| Per-case correlation of the arms | 0.84 | 0.79 |
| SD(Δ) / SD(per-case tF1) | 0.57 | 0.64 |
| **Model-level term σ_g per arm (1 df: √max(Δ̄² − SE², 0) / 2)** | **0.0013** | **0** |

Per class, SD(Δ) is LM 0.12 / 0.05, LAD 0.043 / 0.047, LCx 0.065 / 0.10 and RCA 0.054 / 0.039 (warm / scratch). The
LM is the noisiest, because a short LM flips between rooted and cut.

**In both pairs the whole difference between the two runs is per-case noise.** The mean differences (0.0047,
−0.0027) are what case sampling alone gives (SE 0.0043–0.0046). The 1-df estimates of a model-level shift are 0.001
and 0. A22's 0.013 was set in Round 8 from a smaller model, as a prior to be replaced "when measured on the master".
If it is model-level, it doubles every minimum detectable effect below. Neither pair shows a model-level term of
that size. Two pairs is 2 df, so this is evidence, not proof. Run-to-run variation from GPU nondeterminism alone is
known to match that from changing the seed (Summers & Dinneen, ICML 2021, arXiv:2103.04514, abstract: "all sources
of nondeterminism have similar effects on measures of model diversity"). Split and
test-sample variance dominate seed variance in published benchmarks (Bouthillier et al. 2021, arXiv:2103.03098, §2:
"Bootstrapping data stands out as the most important source of variance"). That is the per-case part, which a paired
case CI sees.

**Janus 0's per-case spread is larger than run 1's.** Val decisive macro: SD 0.117 against 0.065. Per class, LM
0.121, LAD 0.126, LCx 0.135, RCA 0.079. The ImageCAS-X reference traces further distally, so a few cut trees weigh
more. The per-case SD of a paired difference on the pool is therefore bracketed by:

- **optimistic:** the measured SD(Δ) itself, 0.038–0.041;
- **pessimistic:** ratio × Janus 0's SD × f, i.e. 0.067–0.075 × f (f = pool spread / val spread, A31.1).

## Minimum detectable effect of a paired decision (macro tF1; 80 % power, two-sided 5 %)

MDE = 2.80 × √(SD(Δ)² / n + 2σ_g² / runs per arm). Julious 2004 (Stat Med 23:1921, doi:10.1002/sim.1783, §2.2.2 and
eq. 2.10) gives the paired form.

| Decision patients n | Optimistic, f = 1 (SD(Δ) 0.038–0.041) | Pessimistic, f = 1 (0.067–0.075) | Pessimistic, f = 1.5 (0.10–0.11) | With A22's 0.013 as model-level, one run per arm (pessimistic, f = 1) |
|---|---|---|---|---|
| 26 | 0.021–0.023 | 0.037–0.041 | 0.055–0.062 | 0.063–0.066 |
| **35** | **0.018–0.019** | **0.032–0.036** | 0.048–0.053 | 0.060–0.063 |
| 50 | 0.015–0.016 | 0.027–0.030 | 0.040–0.045 | 0.058–0.059 |
| 61 | 0.014–0.015 | 0.024–0.027 | 0.036–0.041 | 0.057–0.058 |
| 80 (val 80, the forgetting guard) | 0.012–0.013 | 0.021–0.024 | — | 0.056–0.057 |

## What it changes

- **35 patients resolve about 0.02–0.035 tF1 if the pool varies like val**, and 0.05 if it varies 1.5× as much.
  That is enough for the question wave 1 has to answer first: does a fine-tune on pool reads beat Janus 0 on pool
  reads? A model trained on one centre, then shown the team's convention and 26 sources, should move by more than
  that, or the fine-tune is not worth having. It is **not** enough for second-order recipe questions (LR arm, replay
  ratio), whose effects are likely below 0.02. Those are fixed by pre-registered defaults, not tested. Going to 50
  (the second tranche) gains about 15 %.
- **A22 on real numbers.** On these two pairs, the 0.013 prior is per-case noise and is already inside the paired
  case CI. Adding it again as a model-level term costs a factor of about 2 in MDE, and a set of any size cannot
  recover that. Proposed **A22′**:
  - the first Janus 1 decision runs its primary arm twice (two seeds), as D28's fallback already requires;
  - the replicate's 1-df σ̂_g is pooled with these two;
  - if the pooled σ̂_g ≤ 0.005, later warm fine-tune decisions use the paired case CI alone, one run per arm;
  - if it is larger, σ̂_g enters as the model-level term, and an effect under 0.02 needs two runs per arm.
- **Limits.**
  - Both pairs are on ImageCAS val and the thick reference.
  - The warm pair shares a seed (it is a nondeterminism replicate, not a seed replicate).
  - The scratch pair also differs in window and epochs.
  - Janus 0's SDs come from CIs, not the per-case file. `--janus0 $SCRATCH/icx4/r9_tf1_val.json` reruns the table on
    the real file (a CPU minute on the login node).
