---
tags: [plans, experiment, fine-tuning, proxy-labels, double-reads, round-6]
author: Crucible
round: 6
updated: 2026-10-10
---

# The expert proxy is a different teacher than the team: team-read targets beat it on the A10 score in every regime (+0.013 to +0.028), Atlas's absolute 0.80 proxy-drop threshold can never fire, and calibrating the proxy with the team's measured habits is not a reliable fix

## Question (Round 6, Q1: fine-tuning as team reads arrive)

Atlas's schedule trains on the projected proxy (ImageCAS-X names on the ImageCAS mask) and replaces it case by case
with team reads. It drops proxies only when proxy-vs-reads tF1 falls below 0.80, or after a paired team-only vs
team + proxy run at ≥ 600 cases. Three questions:

1. How far from the team is the proxy, scored the way A10 scores (mean tF1 against each read)?
2. Would the 0.80 drop rule ever fire?
3. Can the wave-1 report's measured habits (median carina offset, median truncation radius) **calibrate** the
   proxy into the team's convention, so that it keeps helping?

## Method

`experiments/Crucible/r7_proxy_calib.py`, summary `r7_summ.py`.

- **Cases:** 14 non-sealed cases (the script asserts against `trillium/sealed_test.json`).
- **Truth T** = the proxy (the ImageCAS mask split by ImageCAS-X names, ramus → LCx).
- **The team** is simulated with the read generator of `r5_corr.py` in three regimes:
  - `indep`: carina N(0, 2) mm, truncation radius U(0.6, 1.05) mm;
  - `team_bias`: everyone shifts the carina +1.5 mm and stops early;
  - `annot_bias`: two annotators with opposite habits.
  Each case has 2 "real" reads plus 8 more.
- **Pass 1** measures the wave's habits the way `segtrain.reads` does: median geodesic carina offset against the
  proxy's carina (`carina_offset`), and median truncation radius (`truncation_radius`), pooled over the 28 real
  reads.
- **Pass 2** builds the **calibrated proxy**: T with that carina shift and that truncation radius applied.
- **Three label sources**, each scored with tF1 @ 1.5 mm against the two real reads (A10) and against T:
  - the raw proxy;
  - the calibrated proxy;
  - the read-mode, the per-voxel plurality of 8 team reads: what a model trained on team reads converges to,
    i.e. the idealised team-read target.
- **Inter-read** tF1 is the mean of the two directions.
- The comparisons are paired, with a bootstrap 95 % CI over cases.

## Result (14 cases per regime; tF1)

| Regime (estimated habits) | inter-read | proxy vs reads | read-mode vs reads | **read-mode − proxy** (vs reads) | calibrated − proxy (vs reads) | proxy vs reads − inter-read |
|---|---|---|---|---|---|---|
| indep (shift 0.0 mm, r_t 0.92 mm) | 0.923 | 0.932 | 0.946 | **+0.013 [+0.001, +0.029]** | +0.015 [+0.002, +0.030] | +0.009 |
| team_bias (+1.47 mm, 1.07 mm) | 0.927 | 0.912 | 0.940 | **+0.028 [+0.011, +0.045]** | −0.009 [−0.052, +0.025] | **−0.015** |
| annot_bias (0.0 mm, 0.97 mm) | 0.913 | 0.928 | 0.943 | **+0.014 [+0.001, +0.029]** | +0.005 [−0.008, +0.020] | +0.015 |

Against the truth, both the read-mode and the calibrated proxy lose 0.04–0.15. That is expected: they are the
team's convention, not ImageCAS-X's.

## What it implies

1. **Team reads are the better teacher on the score that decides (A10), in every regime.** The gap is +0.013 to
   +0.028 tF1, with every CI excluding 0.
   - This agrees with the GPU run. There the oracle arm, trained on the proxy-like truth, scored 0.778 against the
     reads, against 0.789 for both-as-samples ([[Crucible - Trillium two-reads result]]).
   - So every proxy that stays in training while team reads exist pulls the model toward a convention the
     reference does not use.
2. **The absolute rule "drop proxies when proxy vs reads < 0.80" cannot fire.** The proxy scores 0.91–0.93 against
   the reads in all three regimes, including the one where it costs the most (team_bias, −0.028).
   - The informative quantity is **relative**: proxy-vs-reads compared with inter-read on the same cases. Under a
     team-wide bias the proxy sits 0.015 below a second team reader; without one it sits 0.009–0.015 above.
3. **Calibrating the proxy with two wave-level medians is not a reliable fix.**
   - It matches the read-mode when habits are random (indep: +0.015).
   - It does nothing useful under opposite habits (+0.005, n.s.) and fails under a team-wide bias (−0.009, CI
     spanning ±0.05). A single global truncation radius over-trims some trees, and the team's habit is not one
     number.
   - I do **not** propose proxy calibration. This is an honest negative for my own idea.
4. **The relative test can be run on real data at every wave, without a GPU.** It is A10's own non-inferiority
   construction applied to a label source:
   - keep proxies in training only while proxy-vs-reads is non-inferior to inter-read within 0.02 (the lower bound
     of the paired CI > −0.02);
   - otherwise drop the remaining proxies at the next fine-tune.

## Limits

- The team is simulated. The plurality "read-mode" is the converged-target idealisation that a trained network did
  not follow exactly in Round 5.
- 14 cases; tF1 is the experiment copy, with the thickest-voxel ostium (not A1).
- No training: the experiment measures the targets the two sources teach, not the finite-data value of keeping
  proxies for cases that have no team read yet. That value is exactly what a paired GPU run decides
  ([[Crucible v8]]).
