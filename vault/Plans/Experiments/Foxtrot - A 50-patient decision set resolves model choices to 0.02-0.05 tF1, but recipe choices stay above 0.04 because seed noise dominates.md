---
tags: [plans/experiment, round10, D35, A22, A17, power, fine-tune]
author: Foxtrot
round: 10
updated: 2026-10-25
issue: christianGRogers/Asclepius#113
---

# A 50-patient decision set resolves model choices to 0.02–0.05 tF1, but recipe choices stay above 0.04 because seed noise dominates

**Question (D35).** What precision does a pool decision set of n patients buy for the paired fine-tune comparisons it
exists to decide? Does the answer depend more on n or on the number of training seeds (A22)?

**Method.**
1. **The case term, measured.** `experiments/Foxtrot/r10/paired_noise.py` takes the SD of the per-case paired
   difference in decisive tF1 from the three real paired runs on val 80 (A1 ostia, pinned tF1, flagged trees out;
   `trillium-results/`):
   - **atlas3 F1 − F0:** two 200-epoch warm fine-tunes from one base (A17a trainer), same seed and data stream, with a
     near-zero loss term (0.0001). This is the closest thing we have to two fine-tunes that differ only by run noise.
   - **atlas2 B − run 1:** two from-scratch trainings that differ by recipe (window), 412 epochs each.
   - **atlas3 F0 − B:** a warm fine-tune against its own base.
2. **Precision.** `experiments/Foxtrot/r10/repower.py`: SE² = (r · f · s_d)² / n + σ_seed² (1/k_A + 1/k_B), with
   MDE = 2.80 × SE (two-sided 5 %, 80 % power).
   - s_d is the largest measured SD of the three pairs.
   - r is Janus 0's spread over run 1's (1.82 for macro, from the CI; [[Foxtrot - On Janus 0's spread the 150-patient seal passes a human-level model 78 percent of the time, so it should grow to 200 now]]). It is reported both scaled and unscaled (r = 1).
   - f is the pool spread over val's: 1 and 1.5.
   - σ_seed = 0.013 (A22), and k is the number of seeds per arm.
   - A comparison between **two fixed checkpoints** has no seed term. One example is "is this Janus 1 checkpoint
     better than Janus 0 on the pool?", where the checkpoint itself is what ships. A **recipe** comparison does,
     because it claims that one way of training beats another.

## Result: the measured paired noise

| Pair (val 80) | Macro: mean Δ (CI), SD of Δ | LAD SD of Δ | LCx SD of Δ | RCA SD of Δ | LM SD of Δ (share of Δ = 0) |
|---|---|---|---|---|---|
| F1 − F0 (warm FT replicate) | +0.0047 (−0.003, 0.014), **0.038** | 0.043 | 0.065 | 0.054 | 0.124 (54 %) |
| B − run 1 (scratch, different recipe) | −0.0027 (−0.012, 0.006), **0.041** | 0.047 | 0.103 | 0.039 | 0.050 (39 %) |
| F0 − B (warm FT vs its base) | −0.0024 (−0.013, 0.007), **0.046** | 0.049 | 0.083 | 0.056 | 0.124 (44 %) |

- The per-case correlation between paired models is 0.67–0.88 per class (LM 0.5, which is all-or-nothing).
- **Two near-identical fine-tunes still differ per case by an SD of about 0.04 macro.** That is the floor any D35
  comparison works against.
- Fine-tuning for 200 epochs moved the mean by less than its CI (F0 − B).

## Result: minimum detectable effect, macro tF1, f = 1 (pool like val)

| Design | n = 30 | n = 50 | n = 61 | n = 100 |
|---|---|---|---|---|
| Two fixed checkpoints, measured noise (r = 1) | 0.023 | **0.018** | 0.016 | 0.013 |
| Two fixed checkpoints, Janus 0-scaled (r = 1.82) | 0.042 | **0.033** | 0.030 | 0.023 |
| Recipe, 1 seed vs fixed Janus 0, or 2 seeds per arm (r = 1) | 0.043 | 0.041 | 0.040 | 0.039 |
| Recipe, same, Janus 0-scaled | 0.056 | **0.049** | 0.047 | 0.043 |
| Recipe, 1 seed per arm, Janus 0-scaled | 0.067 | 0.061 | 0.059 | 0.057 |

- At f = 1.5 (pool 1.5× more varied), the fixed-checkpoint MDE at n = 50 is 0.027 (r = 1) and 0.049 (scaled).
  The 2-seed recipe MDE is 0.045 and 0.061.
- **Per class:**
  - LCx is the hardest: at n = 50, f = 1, its fixed-checkpoint MDE is 0.041–0.049, and its recipe MDE 0.054–0.061;
  - LAD sits between: 0.019–0.031 for fixed checkpoints;
  - LM's distribution is all-or-nothing, so no class-level LM decision should be taken at n ≈ 50.
- All rows are in `experiments/Foxtrot/r10/results/repower.json`.

## What it means

1. **The seed term caps recipe decisions.**
   - With two seeds per arm, the seed SE alone is 0.013, so no recipe difference below about 0.037 is detectable at
     any n.
   - Going from 50 to 100 decision patients improves a recipe MDE by 0.002–0.006 and costs 50 patients that the seal
     or training needs.
   - **So D35's size is not the lever for recipe questions. Seeds are,** and each fine-tune seed costs about
     15 Fir GPU-h (Foxtrot v6 §6).
2. **The case term caps model decisions, and 50 patients is enough for them.**
   - "Does this fine-tuned checkpoint beat Janus 0 on pool reads?" is resolvable to 0.02–0.05 at 50 patients.
   - That is the size of gain fine-tuning is expected to give on a shifted domain. The published cross-centre
     drops for coronary segmentation are 5–8 Dice points
     ([[Foxtrot v5]] §8: Kim et al. JMI 2025; Zhang et al. JIIM 2025).
   - Thirty patients would give 0.023–0.042, and 100 would give 0.013–0.023.
3. **What D35 should and should not decide.**
   - **Should:** whether a fine-tuned checkpoint replaces the current one (Janus 1 vs Janus 0), with the seed term
     reported beside the result.
   - **Should not:** small recipe A/B questions (LR arms, mixing ratios, warm vs scratch, loss terms). Their likely
     effects (< 0.02, A22) are below what any feasible D35 can see. Fix them by default and by the literature, and
     test them only if a model decision fails.
4. **The A22 rule stands for recipe claims.** A model decision is a different kind of claim: this checkpoint versus
   that checkpoint, on these patients. The candidate asks the judge to state that distinction in A22's wording, so
   that the first pool decision is not blocked on a second seed of a 60 GPU-h control (D28's fallback).

## Limits

- The paired runs are on ImageCAS val with the retired thick reference (atlas2/atlas3), not on pool reads. The
  r-scaling is an assumption: it treats Janus 0's wider tail as if it widened paired differences in proportion.
  Correlated failures (a tree broken in both arms) would not, and that is why the unscaled row is given too.
- Pool reads come two per volume, which averages read noise, and some patients have several volumes. Both narrow the
  case term somewhat. Neither is modelled.
- σ_seed = 0.013 is A22's borrowed value. A warm fine-tune's seed variance is probably smaller than a from-scratch
  training's (shared base), but there is no measurement. Janus 1's two seeds give the first one (Foxtrot v6 §5).
