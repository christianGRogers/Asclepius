---
tags: [plans, candidate, fine-tuning, proxy-labels, double-reads, round-6]
author: Crucible
round: 6
version: 8
updated: 2026-10-10
---

# Crucible v8 — Fine-tuning as team reads arrive: admit proxies by the same non-inferiority test as models, decide team-only at 300 rather than 600, and compare recipes from identical initialisations

## 0. Improve or start again?

**Improve v7.** A11′ is binding (Round 5). This version answers Round 6 Q1, the fine-tuning recipe, as a challenge
to [[Atlas v6]] §2.7. Model, data, schedule lengths and evaluation stay the master's.

## 1. Thesis

Under the decided reference (D0: team reads; A10: score against each read), the projected expert proxy is a
**different teacher** from the team. Three findings support this:

- **CPU:** team-read targets beat the proxy against the reads by +0.013 to +0.028 tF1 in every simulated regime,
  every CI excluding 0 ([[Crucible - The expert proxy is a different teacher than the team, and calibrating it does not fix that]]).
- **GPU:** the truth-trained arm lost 0.011 against the reads to two simulated reads
  ([[Crucible - Trillium two-reads result]]).
- **The proxy-drop rule:** Atlas's absolute rule (proxy vs reads < 0.80) cannot fire. Proxies score 0.91–0.93
  against the reads even where they cost the most.

So proxies should leave training **as soon as the team's own labels can carry the model, decided by measurement**,
and the test that decides it should be the same non-inferiority construction A10 uses for models.

I also tried to keep proxies useful by calibrating them with the wave-1 habits. It does not work reliably (−0.009
under a team-wide bias), and I do not propose it.

## 2. Recipe changes to §2.7 (amendment A17, proposed)

| Team reads in hand | Atlas v6 | **v8** |
|---|---|---|
| 0 | R1 on proxy | unchanged |
| first 50 double-read cases | Wave-1 report (A12) | Wave-1 report **plus a frozen team validation fold**: these 50 cases (non-sealed) become the val fold for every later wave model and are never trained on, so waves are comparable |
| every wave | monitor, A11′ samples, adjudication | plus the **proxy admission test** (CPU): on the val fold, proxy vs reads must be non-inferior to inter-read within 0.02 (lower bound of the paired CI > −0.02). If it fails, the remaining proxies leave at the next fine-tune. This replaces "< 0.80 → drop" |
| ≥ 150 double-read training cases | fine-tune 250 epochs on team ∪ proxy | unchanged (warm start from R1 is fine for an interim model) |
| **≥ 300** | fine-tune 250 epochs | **paired team-only vs team + proxy**, both arms warm-started from the same checkpoint with the same epochs, scored by A10 on the val fold. The winner's data rule is used from then on. Atlas runs this at ≥ 600; 300 double-read cases is 600 samples |
| ≥ 600 | team-only vs team + proxy | not needed if decided at 300; otherwise run it here |
| all 900 | final from scratch | unchanged, from scratch (see 2.2) |

### 2.1 Mixing rule while proxies remain

- Unchanged from Atlas, which is already right: a case with team reads contributes its two reads (A11′, two
  samples); a case without team reads contributes its proxy (one sample).
- No extra down-weighting is proposed. The 2 : 1 sample ratio already shifts the mix toward team labels as waves
  grow, and I have no evidence for a specific weight.

### 2.2 Initialisation rule

- **Interim models** (fine-tunes per wave) may warm-start: they are cheap and serve QA and the reports.
- **Every recipe comparison** (team-only vs team + proxy; the conditional A11 test) uses **identical
  initialisation in both arms**. Otherwise a warm-start advantage is credited to a data rule.
- **The final model is trained from scratch.** Warm-started networks can generalise worse than fresh ones trained on
  the same final data (Ash & Adams, arXiv:1910.08475), and nnU-Net's own fine-tuning path restarts the full LR
  schedule anyway (`documentation/pretraining_and_finetuning.md`).

### 2.3 Not proposed

| Idea | Why not |
|---|---|
| Proxy calibration with measured habits | Tested; unreliable (above) |
| Per-sample loss reweighting (Ren et al., arXiv:1803.09050) | Needs a clean meta-set and custom training code. Our "clean" set is the team's reads, so the admission test gets the same benefit at no cost |
| Noisy-label machinery for the team reads (co-teaching and similar; surveys: Song et al., arXiv:2007.08199; Karimi et al., arXiv:1912.02911) | The GPU run found two noisy reads ≥ truth labels at this scale. There is nothing left to clean |

## 3. Evaluation

Unchanged (A1, A9, A10). New: the frozen team val fold of 50 non-sealed cases is the only basis for wave-to-wave
comparisons; the sealed test stays untouched until milestones.

## 4. Evidence

| Claim | Evidence |
|---|---|
| Team-read target − proxy vs reads: +0.013 [+0.001, +0.029] (indep), +0.028 [+0.011, +0.045] (team_bias), +0.014 [+0.001, +0.029] (annot_bias) | [[Crucible - The expert proxy is a different teacher than the team, and calibrating it does not fix that]] |
| Proxy vs reads 0.912–0.932: the 0.80 rule never fires; relative to inter-read −0.015 to +0.015 | same |
| Calibrated proxy: +0.015 / −0.009 / +0.005 (not reliable) | same |
| GPU: oracle (truth-trained) 0.778 vs both 0.789 against reads; two reads ≥ truth labels against the truth | [[Crucible - Trillium two-reads result]] |
| Warm-starting can hurt generalisation | Ash & Adams, *On Warm-Starting Neural Network Training*, NeurIPS 2020, arXiv:1910.08475 |
| A large noisy set can beat a small clean one; most noisy-label remedies matter only at high noise | Karimi et al., MedIA 2020, arXiv:1912.02911; [[Fusing multiple annotations and learning from noisy labels]] |

## 5. Risks

| Risk | Detection | Response |
|---|---|---|
| Dropping proxies too early loses data for cases without team reads | The ≥ 300 paired run decides it; the admission test only removes proxies that are worse than a second reader | Re-admit if the paired run favours team + proxy |
| The val fold of 50 is too small for per-class decisions | Bootstrap CIs; LM reported, not gated (Round 3) | Grow the fold to 80 at wave 2 if CIs are too wide |
| Simulation-only evidence for the proxy gap | The admission test measures it on real reads at every wave | — |

## 6. Comparison with Atlas v6 §2.7

Same skeleton: proxy first, then team reads, fine-tunes per wave, final from scratch. v8 changes three things, each
cheap:

1. A relative, A10-consistent proxy admission test replaces an absolute threshold that cannot fire.
2. The team-only decision moves to 300, with identical-initialisation arms.
3. A frozen team val fold makes waves comparable.

## 7. Cost

- **CPU:** minutes per wave (the admission test).
- **GPU:** the paired run at 300 is 2 × 250 epochs × 175 s ≈ 24 H100-h. Atlas's plan already spends this at 600,
  so v8 moves the cost, it does not add it.
- **Human:** none.

## 8. Changes since v7

- Round 6 Q1 answered: the admission test, team-only at 300, the initialisation rule, and the frozen val fold.
- The proxy-calibration idea was tested and withdrawn.
- `segtrain.reads` was fixed after Echo's audit (D4, D5, D6, D7, D10); see
  [[Crucible - Implementation of segtrain.reads]].
