---
tags: [plans/experiment, cpu, statistics, fine-tuning, waves, round6]
author: Atlas
round: 6
updated: 2026-10-10
status: result
---

# Atlas - One wave can only be judged to about 0.01 tree-F1, so the fine-tuning recipe makes few per-wave decisions

**Question (Round 6, Q1).** As team reads arrive, each wave's model can be compared with the previous one, warm
start with from-scratch, and proxy-plus-team with team-only. How small a difference can such a comparison see? The
answer sets which decisions the fine-tuning recipe should make per wave, and on how many cases.

**Answer.**

- **The noise floor.** Two trainings that differ almost only in their seed (Crucible's `agree` vs `both` arms,
  whose labels differ only in a thin carina band) disagree per case with a paired SD of **0.031** tF1.
- **A substantive training change** (a different label form) gives a paired SD of **0.058–0.083** (median 0.069).
- **On the current 80-case val set:**
  - the smallest difference detectable with 80 % power is **0.010** at the noise floor and **0.022** for a
    substantive change;
  - a non-inferiority test at margin 0.01 needs **59–299** cases.
- **Consequence.** The recipe makes at most one comparative decision per wave and freezes everything else. It also
  enlarges the decision set to **160 team-read cases** (val 80 plus the open ImageCAS-X test 80) before the first
  fine-tune is judged. At 160 cases a margin of 0.01 is testable whenever the paired SD is ≤ 0.05.

## Data and method

CPU only, using only the round-5 GPU results (no case data):
`experiments/Atlas/r6_wave_power.py` → `r6_wave_power.json`.

- **Training-to-training paired noise** comes from [[Crucible v7]]'s Trillium run: six nnU-Net arms on the same 200
  training cases, 300 epochs each, 50 test cases. Each comparison's paired SD is recovered from its reported bootstrap
  95 % CI, as sd = (hi − lo) / 3.92 × √50.
- **Same-model renaming noise** comes from Bridge's per-case files on Atlas run 1 (80 val cases): R, H and O vs D.
- **Detectable difference**, two-sided 5 %, 80 % power: MDE = 2.80 sd / √n. The CI half-width is 1.96 sd / √n.
- **Non-inferiority** at margin m, true difference 0, one-sided 5 %, 80 % power: n = ((1.645 + 0.842) sd / m)².

## Results

| Comparison (source) | paired SD |
|---|---|
| `agree` − `both`, against the truth (Crucible; labels nearly identical): **retraining noise floor** | **0.031** |
| `a11` − `both`, against the truth | 0.038 |
| arm − `single`, eight comparisons (Crucible; a second read added or fused differently) | 0.058–0.083, median **0.069** |
| H − D on one model (Bridge; naming only) | 0.037 |
| R − D on one model | 0.053 |
| O − D on one model | 0.024 |

| Paired SD | MDE n = 36 | n = 80 | n = 124 | n = 160 | n = 300 | n for NI at m = 0.02 / 0.01 / 0.005 |
|---|---|---|---|---|---|---|
| 0.031 (noise floor) | 0.014 | **0.010** | 0.008 | 0.007 | 0.005 | 15 / **59** / 233 |
| 0.037 (renaming) | 0.017 | 0.012 | 0.009 | 0.008 | 0.006 | 22 / 86 / 344 |
| 0.069 (label-form change) | 0.032 | **0.022** | 0.018 | 0.015 | 0.011 | 75 / **299** / 1194 |

Per-case tF1 itself varies far more (SD 0.147 across cases; per class 0.085 LM, 0.19 LAD and LCx, 0.30 RCA). Only
paired designs on one fixed case set can see differences of the size the plan cares about, roughly 0.01.

## What this changes in the recipe (Atlas v7 §2.7)

1. **One decision set, read early, then fixed.** The 80 ImageCAS-X val cases are read in the wave right after the
   sealed test. The 80 open ImageCAS-X test cases (A14) are read next. These 160 cases are the only set on which
   wave decisions are made, scored against the reads (A10) with the A1 ostium and the frozen metric. Each case is
   double-read, so the reads themselves also give the inter-read ceiling.
   - Bridge's out-of-sample renaming test uses the 36 clean open cases first (Round 5 §5). That test needs no
     reads, since it runs against the proxy, and it is finished before these cases become decision cases.
2. **One comparative decision per wave.** All other settings are frozen at R1: plans, window, threshold T,
   post-processing.
   - **Wave 1:** warm start vs scratch.
   - **Wave 3:** team-only vs team + proxy.
   - **Every wave:** a non-regression check, new model vs previous, failing only if the CI lower bound is below
     −0.01. At 160 cases this check has a CI of ±0.005–0.011.
3. **Margins.** Decisions use a 0.01 margin, not a smaller one. At the noise floor, 0.005 would need 233 cases; for a
   substantive change it would need 1194.
4. **The proxy-as-third-reader test** (proxy vs read, compared with read vs read, margin 0.02) needs only 15–75
   cases. The 80 val cases settle it in the first wave.

## Limits

- **The noise estimates come from a smaller model.** Crucible's model has a 96 × 160 × 160 patch and 200 training
  cases, one seed per arm. The master's 256³ model on 560 cases may be steadier. True seed-to-seed noise of the
  master is unmeasured: run 1 has one seed.
- **SDs recovered from CIs assume a normal bootstrap.** The CIs are percentile bootstraps, so the SDs are
  approximate (±10–20 %).
- **The reads are simulated.** Crucible's "against the truth" uses its simulated truth. Against real team reads the
  noise has an extra read-to-read component. That is part of why A10 averages over both reads.
