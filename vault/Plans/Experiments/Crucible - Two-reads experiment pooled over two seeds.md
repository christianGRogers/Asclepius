---
tags: [plans, experiment, gpu, trillium, double-reads, a11, a10, result, seeds]
author: Crucible
round: 8
updated: 2026-10-11
---

# Two seeds of the two-reads experiment: "two reads beat one" and "union is worst against the reads" hold. The a11-vs-both sign does not. Training-run noise is as large as the effects we decided A11′ on

## What was pooled

There are two complete runs of `trillium/crucible`:

- seed 1, Round 5: `trillium-results/round5/crucible/results/`;
- seed 2: `trillium-results/round6/crucible_seed2/results/`.

The two runs share the following:

- the six arms;
- 300 epochs per arm;
- the 200 training cases and the 50 test cases;
- **identical simulated reads.** The per-case inter-read values agree exactly between the runs; the script asserts this.

Only the training run differs: the seed, plus GPU nondeterminism. So **case and seed are crossed**: every arm has two scores on each of the 50 cases.

Script: `experiments/Crucible/r8_pool_seeds.py`. It is CPU only, uses the committed JSON only, and runs in seconds.

The script reports three things:

- **Pooled, seed as a fixed factor.** The per-case contrast is averaged over the two seeds, then bootstrapped over cases. This is the right CI for "these two runs on these cases".
- **Seed × contrast interaction.** The per-case difference between the seed-2 and seed-1 contrasts, bootstrapped over cases. If its CI excludes 0, run-to-run variance is real beyond case sampling.
- **Seed as a random factor.** The fixed-factor SE plus the between-seed variance of the contrast mean, (c₁ − c₂)²/2, divided by 2 seeds. This is the honest CI for "a new training run". With 2 seeds it is crude and wide; it is a floor on uncertainty, not a precise interval.

## Between-seed SD of every arm

There are two SDs per arm:

- **between-seed SD of the arm mean:** |m₁ − m₂| / √2;
- **per-case SD from seed alone:** SD(x₁ − x₂) / √2 over cases.

| Arm | vs truth s1 / s2 (pooled) | Between-seed SD | Per-case seed SD | vs reads s1 / s2 (pooled) | Between-seed SD | Per-case seed SD |
|---|---|---|---|---|---|---|
| single | 0.800 / 0.805 (0.803) | 0.003 | 0.046 | 0.771 / 0.779 (0.775) | 0.005 | 0.034 |
| both (A11′) | 0.830 / 0.821 (0.825) | 0.007 | 0.025 | 0.789 / 0.778 (0.783) | 0.008 | 0.026 |
| a11 | 0.822 / 0.833 (0.827) | 0.008 | 0.027 | 0.754 / 0.789 (0.771) | **0.025** | 0.029 |
| agree | 0.833 / 0.827 (0.830) | 0.004 | 0.021 | 0.791 / 0.785 (0.788) | 0.004 | 0.020 |
| union | 0.815 / 0.820 (0.817) | 0.003 | 0.035 | 0.746 / 0.755 (0.751) | 0.006 | 0.041 |
| oracle | 0.825 / 0.826 (0.826) | 0.001 | 0.039 | 0.778 / 0.778 (0.778) | 0.001 | 0.035 |

- **Arm means move by 0.001–0.008 between runs.** The exception is a11 against the reads, which moves by 0.025.
- **A single case moves by 0.02–0.05 tF1** from the training run alone. That is comparable to the case-to-case spread of the contrasts.
- **Per class, the RCA is the noisiest.** For example, `both` scores RCA 0.802 vs 0.774 against the truth.

## Contrasts

| Contrast | vs | Seed 1 | Seed 2 | Pooled, fixed seed [95 % CI] | Seed random [95 % CI] | Interaction s2 − s1 [95 % CI] |
|---|---|---|---|---|---|---|
| both − single | truth | +0.030 | +0.016 | **+0.023 [+0.010, +0.038]** | **[+0.003, +0.042]** | −0.014 [−0.037, +0.009] |
| a11 − single | truth | +0.022 | +0.028 | +0.025 [+0.011, +0.042] | [+0.008, +0.041] | +0.006 [−0.014, +0.026] |
| agree − single | truth | +0.033 | +0.022 | +0.028 [+0.014, +0.044] | [+0.009, +0.046] | −0.011 [−0.030, +0.008] |
| union − single | truth | +0.015 | +0.015 | +0.015 [+0.003, +0.027] | [+0.003, +0.026] | +0.000 [−0.023, +0.024] |
| oracle − single | truth | +0.025 | +0.021 | +0.023 [+0.008, +0.038] | [+0.008, +0.038] | −0.004 [−0.030, +0.025] |
| **a11 − both** | **truth (decisive row)** | −0.008 | +0.012 | **+0.002 [−0.006, +0.012]** | **[−0.020, +0.024]** | **+0.020 [+0.006, +0.035]** |
| agree − both | truth | +0.003 | +0.007 | +0.005 [−0.003, +0.014] | [−0.004, +0.014] | +0.003 [−0.009, +0.016] |
| union − both | truth | −0.015 | −0.001 | −0.008 [−0.017, +0.000] | [−0.024, +0.008] | +0.014 [−0.001, +0.031] |
| oracle − both | truth | −0.005 | +0.005 | +0.000 [−0.011, +0.012] | [−0.015, +0.015] | +0.010 [−0.006, +0.028] |
| both − single | reads | +0.017 | −0.001 | +0.008 [−0.004, +0.023] | [−0.014, +0.030] | −0.018 [−0.038, −0.000] |
| **a11 − both** | **reads (A10)** | −0.035 | +0.011 | **−0.012 [−0.021, −0.001]** | **[−0.059, +0.035]** | **+0.046 [+0.031, +0.062]** |
| agree − both | reads | +0.002 | +0.008 | +0.005 [−0.003, +0.014] | [−0.005, +0.015] | +0.006 [−0.006, +0.018] |
| union − both | reads | −0.042 | −0.023 | **−0.032 [−0.042, −0.023]** | **[−0.054, −0.011]** | +0.020 [+0.003, +0.039] |
| oracle − both | reads | −0.011 | +0.001 | −0.005 [−0.016, +0.005] | [−0.021, +0.010] | +0.012 [−0.003, +0.027] |

## What is robust across seeds

1. **Every two-read target beats one read against the truth.** This holds for both, a11, agree and union, in both seeds, with every seed-random CI excluding 0.
   - both − single: +0.023, seed-random CI [+0.003, +0.042].
   - The effect size is not stable: +0.030, then +0.016.
2. **Union is the worst arm against the reads in both seeds:** −0.032 vs both, seed-random CI excluding 0.
   - The mechanism repeats too. Union's LM scored against read B (annotator Y, short LM) is **0.507 / 0.533**, with **22/50 and 21/50 cases** below 0.5, and 12 of those cases are the same in both runs.
   - The network fills union's ignored carina band with LM, which is X's habit. This happens in every run.
3. **Truth labels are no better than two reads.** Oracle − both is +0.000 vs the truth and −0.005 vs the reads; both are near 0 with tight CIs. Two reads match the truth.
4. **Agree ≈ both** in both seeds, against the truth and the reads (+0.005, n.s.).

## What is not robust

1. **a11 − both changes sign.** The interaction CI excludes 0 against the truth (+0.020) and against the reads (+0.046), so **the run-to-run difference is real and is not a case-sampling artefact**. Pooled vs the truth it is +0.002 [−0.020, +0.024] seed-random: no evidence either way.
2. **a11's LM collapse against read B was a run-level event, not a property of the target.**
   - LM vs B: seed 1 **0.505** (22/50 cases < 0.5); seed 2 **0.794** (5/50, the same rate as both's 2–6/50).
   - Only 4 collapsed cases are shared between the runs.
   - So the ignore band makes the LM-fill failure *possible*. union hits it every time; a11 hit it in 1 of 2 runs.
3. **both − single against the reads** (+0.017, then −0.001). The Round 5 claim "two reads beat one against the reads" does not survive pooling: +0.008, seed-random CI [−0.014, +0.030].
4. **"Truth-trained loses 0.011 against the reads"** ([[Crucible v8]] §4) was seed 1 only. Pooled it is −0.005 [−0.016, +0.005]. Withdrawn as a finding; restated as "no difference".
5. **a11 is better than both on the RCA in both seeds** against the truth (+0.016, +0.043). The ignore band is nowhere near the RCA, so this is either noise in the noisiest class or an indirect effect: fewer supervised voxels changes the loss weighting. It is unexplained, and I do not interpret it.

## Does A11′ stand?

**Yes, but on changed grounds.**

- **The pre-registered row** ("narrow A11 only if a11 < both vs truth with the CI excluding 0") never fires: not in seed 1, not in seed 2, not pooled.
- **The Round 5 grounds were** "a11 is significantly worse than both on the A10 score". That was seed-1 evidence. Pooled with a fixed seed it is still −0.012 [−0.021, −0.001], but with seed as a random factor it is [−0.059, +0.035]. **It is no longer decisive.**
- **What remains for A11′:**
  1. It is the simplest target.
  2. It is not worse than a11 on any pooled estimate against the truth.
  3. It removes a demonstrated failure mode. The ignore band let the network adopt one annotator's LM habit in 1/2 a11 runs and 2/2 union runs. The cost was LM against the other annotator, about 0.5 against about 0.8, which is a gated class under D6's per-class margin.
- **The conditional A11 test is moot.** Under D0/D7 the reads are splits of the same mask, so the carina band is the only conflict the ignore would touch. That is exactly where the failure mode lives.

## Method lesson (applies to every GPU arm comparison, not only mine)

- **Training-run variance is not in a 50-case paired CI.** A single-seed contrast below about 0.02 tF1 cannot carry a decision. a11 − both moved by 0.020 against the truth, and by 0.046 against the reads, between two runs on identical data.
- **The same caution applies to Round 8's other single-seed contrast.** Window ablation B: −0.0027 [−0.0118, +0.0062], one run each, and the arms ran for different numbers of epochs (368 vs 412).
- **Proposed rule:** an arm decision with a pooled effect under 0.02 needs ≥ 2 seeds, with seed pre-registered as a factor. Otherwise it is reported as "no difference detected", not as a win.
