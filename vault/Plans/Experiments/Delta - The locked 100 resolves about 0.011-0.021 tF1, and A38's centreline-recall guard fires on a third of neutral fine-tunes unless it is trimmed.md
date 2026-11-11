---
tags: [plans, experiment, janus1-L, power, locked100, A38, G3, ensemble]
author: Delta
round: 1
track: 1-L
updated: 2026-11-11
issue: christianGRogers/Asclepius#302
code: experiments/Delta/j1l_r1/power_locked100.py
---

# The locked 100 resolves about 0.011–0.021 tF1, and A38's centreline-recall guard fires on a third of neutral fine-tunes unless it is trimmed

**Question.**
1. How small a Janus 1-L gain over Janus 0 can the locked 100 detect?
2. How often do the Round 10 gates (A38) misfire on a fine-tune that changes nothing?
3. How sensitive is a test of ensemble(a1, a2) against a1?

**Data.** Everything is in the repo. Both pairs are on ImageCAS-X val 80 (the same 80 cases that make up 80 % of the
locked 100), scored at A1c `24441cf8…5254` with A1 aortas.
- **The warm replicate:** atlas3 F1 − F0. These are two warm fine-tunes from one start, with the same data and 200
  epochs. The FP term did nothing, so this is a replicate.
- **The scratch pair:** atlas2 B − run 1. These are two from-scratch trainings that Round 8 judged a tie.
- **Janus 0's per-case SD** (macro 0.117; LM 0.121, LAD 0.126, LCx 0.135, RCA 0.079) comes from its posted CI, as in
  Atlas's Round 10 note.

The references are D0-era (the thick ImageCAS-X reference for atlas2 and atlas3), so the ratios carry over and the
absolute values are bracketed. No locked-100 score of any Janus model was read, and no sealed case.

**Method.**
- The per-case decisive macro is the mean of the unflagged classes (icx4's `decisive_case_score`). This reproduces
  Atlas's SD(Δ) to four places: 0.0382 and 0.0411.
- MDE uses two-sided α = 0.05 at power 0.80 (2.80 × SD / √n).
- The gates are simulated with per-case run noise. Janus 0's noise is shared by a1 − J0 and a2 − J0.
- The recall guard is also checked **empirically**. I resample the measured per-case recall deltas, symmetrised (x and
  −x) so that a neutral model has their real tails.

## Results (`experiments/Delta/j1l_r1/power_locked100.json`)

**MDE for a model decision** (paired macro tF1, fixed checkpoints, no seed term; A37):

| SD of per-case Δ | n = 80 | **n = 100** | ensemble − a1, n = 100 |
|---|---|---|---|
| 0.038 (warm replicate, measured) | 0.012 | **0.011** | 0.005 |
| 0.041 (scratch pair, measured) | 0.013 | **0.012** | 0.006 |
| 0.075 (Janus 0's case SD × 0.64, pessimistic) | 0.023 | **0.021** | 0.010 |

D45's 20 extra locked cases cut the MDE by 11 % (√(80/100)).

**The adoption rule L1** requires a1 − J0 to have a lower 95 % bound > 0 **and** a2 − J0 to have a mean > 0.

| True gain | P(L1 passes), optimistic | P(L1 passes), pessimistic |
|---|---|---|
| 0 | 0.021 | 0.033 |
| +0.01 | 0.75 | 0.26 |
| +0.02 | 1.00 | 0.74 |

**The class floor** (A38 G2's "no class mean Δ < −0.03") false-alarms on a neutral model ≤ 1 % of the time at n = 100.
It is fine as written.

**The centreline-recall guard** (A38 G3: no class's recall falls by more than 0.02, point estimate):

| Rule, neutral model, empirical resampling | n = 80 | n = 100 | Detects a uniform LCx recall loss of 0.03 / 0.02 (n = 100) |
|---|---|---|---|
| **As written** (any class mean < −0.02) | **0.36** | **0.31** | — |
| Mean < −0.02 **and** its 95 % upper bound < 0 | 0.039 | 0.041 | — |
| 10 %-trimmed mean < −0.02 | 0.000 | 0.000 | 0.999 / 0.51 |

**Why G3 misfires.** The per-case recall deltas are heavy-tailed:
- per class, a median |Δ| of 0.000–0.007, but an SD of 0.07–0.17;
- the SD comes from 2–3 cases per class whose whole tree flips between rooted and cut (|Δ| > 0.3).

So a class mean moves by about 0.02 whenever one more tree flips one way than the other. That is noise G3 was not
meant to see. G3 exists to catch a model that **stops vessels earlier** everywhere (Crucible's seed-learning case).
That is a shift of the bulk, which a trimmed mean sees and a flip does not.

## What it changes (proposed in Delta v1, track 1-L)

- **Decide Janus 1-L with L1 at n = 100.** It resolves about 0.011 tF1 if a warm fine-tune moves cases as little as
  atlas3's replicate did, and 0.021 if it moves them as much as Janus 0's case spread suggests. Below that, the locked 100
  cannot see a gain, and the plan says "no gain detected", not "no gain".
- **Replace G3** by "10 %-trimmed class recall Δ < −0.02, **or** mean < −0.02 with its 95 % upper bound < 0". The
  combined false-alarm rate is about 4 %, against 31 %. A uniform 0.03 recall loss is still caught.
- **The second run is cheap power.** Ensemble(a1, a2) against a1 has half a1 − J0's per-case noise. The test resolves
  about 0.005–0.010, so a gain from ensembling is visible where a single-run gain is not.
- **Limits.** This rests on two measured pairs (2 df) from D0-era models, and Janus 0's SD is CI-derived. Job J0 in
  Delta v1 re-scores Janus 0 on the locked 100 per case. The MDE row is then recomputed from the exact SD before any
  Janus 1-L number is read.
