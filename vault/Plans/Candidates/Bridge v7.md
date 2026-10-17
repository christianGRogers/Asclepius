---
tags: [plans/candidate, bridge, statistics]
author: Bridge
round: 8
updated: 2026-10-11
---

# Bridge v7: decide on A1-scored variance, and count seeds for training decisions

## 0. Position

- The model is unchanged: Bridge proposes nothing to the recipe.
- The namer stays QA only (v5).
- v7 revises v6's statistics with the real A1-scored data and adds a seed rule. Evidence:
  [[Bridge - With A1 scoring the sealed test detects about 0.012 tF1, but seed noise doubles every training comparison]].

## 1. What changed since v6

1. **The variance is smaller than v6 assumed.** With A1 ostia and flagged trees out, the per-case SD
   falls from 0.15 to **0.064** (decisive macro), and RCA from 0.32 to 0.08. The sealed test detects
   **≈ 0.012** macro for a paired training comparison (from case sampling alone), and val ≈ 0.013.
2. **A10 is less hopeless than v6 said, but per class it still fails.** At δ = 0 and margin 0.02:
   - macro passes 49–80 % of the time;
   - all four classes pass 1–5 % of the time.
3. **Seed noise is the binding limit for training decisions.**
   - The seed-to-seed SD of a paired arm contrast is 0.013, against a case SE of 0.007.
   - A single-seed CI covers the seed-averaged effect about 66 % of the time.
   - The Round 5 a11-vs-both result against the reads reversed sign in seed 2.
4. **The window comparison supports equivalence, not a winner.**
   - tF1 −0.003 [−0.012, +0.006]: ±0.03 once seed noise is included.
   - FP −0.19 [−0.48, +0.10], with an MDE of 0.42.
   - The 368-vs-412 confound is small in pseudo-Dice (< 0.001 over the last 44 epochs), but untested in
     tF1.

## 2. Amendments proposed (replacing v6 E1, E5 and E6 where they conflict)

| # | Change | Cost |
|---|---|---|
| S1 | **A10 primary = decisive macro, margin 0.02, after the A1b review.** Per class: reported, with a floor (no class point estimate < −0.05). If wave 1's real inter-read SD exceeds 0.08 (macro), the clinical lead is offered 0.025–0.03 with the power table. | none |
| S2 | **The A1b review is a power requirement.** Flagged trees cut the RCA n by 30 %, and including them doubles the MDE. Review flagged sealed trees before scoring, not after. | reviewer time already budgeted |
| S3 | **Seed rule for every retrained-network decision** (ablations, A11 test, team-only vs team + proxy, 5-fold vs single): ≥ 2 seeds per arm, or a CI widened by the seed SD, SE = √(SE²_case + σ²_seed) with σ_seed = 0.013 until measured on the master. Fixed-prediction decisions (post-processing, naming, inference settings) keep case-only CIs. | 2× training per contested arm |
| S4 | **Equal epochs are a precondition of any paired training comparison.** A run stopped at its deadline is compared against the control's checkpoint at the same epoch, or the comparison is reported, not decided. | none: run 1 has per-epoch logs, but checkpoints would need `save_every` |
| S5 | **Window:** record "default" as chosen by tie-break (harmless), not as better. The FP lever is reopened by the census (79 % `confident_other`), not by the window. | none |
| S6 | **A11′** stays the default only as the simpler rule. The Round 5 evidence that a11 is worse against the reads is withdrawn. The conditional A11 test on real reads is decided under S3. | none |

## 3. One proposed Trillium experiment (costed; not built; awaiting the judge)

**Seed replicate of the window ablation on the master.**

- **Runs:**
  - run 1 configuration, seed 2, 412 epochs;
  - B configuration (default window), seed 2, 412 epochs.
- **Analysis:**
  - the two windows compared on equal epochs in 2 seeds;
  - two direct estimates of the master's seed SD (run 1 s1 vs s2, and B s2 vs B s1@368).
- **Cost:** 2 × 412 × 176 s ≈ **40 H100-h**, plus about 1 h of scoring. Inference and A1 scoring reuse
  atlas2's aortas.

**Pre-registered decision table:**

| Outcome | Action |
|---|---|
| Master seed SD of the decisive macro (paired, per run) ≤ 0.005 | Seed noise is negligible on the master: S3 drops to case-only CIs; single-seed decisions stand |
| 0.005 < seed SD ≤ 0.015 | S3 as written (σ_seed measured) |
| > 0.015 | Every retrained decision needs ≥ 3 seeds; ablations are re-prioritised by cost |
| Window, mean of 2 seeds, CI with the seed term excluding 0 | That window wins; otherwise the default stays (tie-break) |

**Priority.** This is below the FP-recipe work that the census reopened. It is worth running only if
the plan has more than about 3 retrained-network decisions left. It does (A3, A11 test, team-only vs
team + proxy, 5-fold), and each of those would otherwise be decided on one seed.

## 4. Risks

| Risk | Response |
|---|---|
| The Crucible seed SD (small model) overstates the master's | §3 measures it; until then S3 is conservative, not wrong |
| S3 doubles training cost for ablations | Only contested arms need a second seed; forced choices with tiny stakes can stay single-seed and be labelled as such |
| The inter-read SD is unknown until wave 1 | S1's margin is fixed after wave 1 and before the sealed reads are scored |

## 5. Cost

- **Without the experiment:** no GPU; CPU only.
- **With the experiment:** ≈ 41 H100-h, if the judge approves §3.
