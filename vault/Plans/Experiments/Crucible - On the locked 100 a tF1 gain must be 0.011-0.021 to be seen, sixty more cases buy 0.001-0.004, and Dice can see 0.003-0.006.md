---
tags: [plans, experiment, janus-1-l, power, locked-100, cpu]
author: Crucible
track: 1-L
round: 1
updated: 2026-11-11
issue: christianGRogers/Asclepius#302
code: experiments/Crucible/j1l_r1/locked100_power.py, experiments/Crucible/j1l_r1/make_lists.py
---

# On the locked 100 a tF1 gain must be 0.011–0.021 to be seen, sixty more cases buy 0.001–0.004, and Dice can see 0.003–0.006

**Question.** D45 fixes 100 locked validation cases and 620 training cases. What paired difference against Janus 0
can the locked 100 detect, on tF1 and on Dice? And what can the 60 extra training cases be expected to buy?

**Method** (CPU, seconds; no image, label or sealed case opened).
- **The locked 20 of open-36** by D45's rule (`make_lists.py`; `lists.json`, sha256 `7ecc464b…fd56`):
  c0068, c0102, c0251, c0271, c0323, c0327, c0470, c0545, c0592, c0620, c0644, c0805, c0807, c0824, c0827, c0841,
  c0908, c0946, c0957, c0996.
  - The other 16 go to training: c0123, c0195, c0340, c0416, c0430, c0435, c0447, c0617, c0624, c0660, c0726, c0758,
    c0772, c0877, c0971, c0984.
  - Checked: 100 locked and 620 training cases, disjoint, none sealed.
- **tF1 paired spread.** Two measured pairs on val 80, at the decisive per-case macro (flagged trees out, A1b):
  - atlas2 run 1 − B, two from-scratch runs: SD 0.0411;
  - atlas3 F0 − F1, two warm fine-tunes: SD 0.0382.

  These reproduce Atlas's Round 10 values. The raw `tf1` field keeps flagged trees and gives 0.085–0.109, so it must
  not be used. Each pair is centred, resampled to n = 100 (4 000 draws) and shifted by a true effect, at scale 1 and
  at scale 1.8 (Janus 0's per-case macro SD from its CI is 0.117, against run 1's 0.065).
- **Dice:** no paired per-case Dice exists. A normal model is used, on Janus 0's val-80 per-case SD (0.023, from
  p10/p90 0.846/0.904) and a between-model correlation ρ of 0.5–0.9.
- **Data:** a log-linear learning curve. Each doubling of the cases removes a fraction g of the remaining tF1 error
  (1 − 0.909); 560 → 620 is 0.147 doublings.

## Result

**tF1, n = 100** (P of each rule passing; lower 95 % bound of the mean paired Δ):

| Pair, scale | SD of Δ | MDE (80 %) | True Δ = 0: P(LB > −0.02) | P(LB > −0.01) | True Δ = +0.005: P(LB > 0) | True Δ = +0.01: P(LB > 0) |
|---|---|---|---|---|---|---|
| warm F0−F1, ×1 | 0.038 | 0.011 | 0.995 | 0.72 | 0.33 | 0.72 |
| scratch run1−B, ×1 | 0.041 | 0.012 | 0.997 | 0.69 | 0.23 | 0.70 |
| warm F0−F1, ×1.8 | 0.069 | 0.019 | 0.80 | 0.37 | 0.18 | 0.39 |
| scratch run1−B, ×1.8 | 0.074 | 0.021 | 0.78 | 0.28 | 0.10 | 0.27 |

**Dice, n = 100:** SD of Δ 0.010–0.023 (ρ 0.9–0.5); MDE (80 %) **0.003–0.006**. A true +0.01 is seen with P ≥ 0.99.

**Sixty more cases:** expected tF1 gain **0.0007–0.0038** (g = 5–25 % per doubling).

## Reading

1. **"Better than Janus 0 on tF1" is not a fair primary claim for 1-L on ImageCAS-X alone.** The data effect is a
   fifth to a third of the smallest MDE. A superiority test on tF1 would pass 3–20 % of the time on a real but small
   gain. Running it as the primary test means a near-certain "no gain", or a temptation to try more arms.
2. **tF1 should be guarded, not chased.** A −0.02 non-inferiority bound passes a neutral model 78–100 % of the time.
   −0.01 passes it 28–72 % of the time (too tight; Round 10 reached the same verdict at n = 80, A38 G2).
3. **Dice is where 1-L can show a gain the locked 100 can see.** Its MDE is 3–6 thousandths, and Janus 0 sits
   0.054 below the 0.5-mm ceiling for a reason it can fix
   ([[Crucible - At 0.5 mm even a perfect network scores whole-tree Dice 0.934, so most of Janus 0's thin lumen is the network, not the resampling]]).
4. **There is no confirmation set left.** D45 moves open-36 and dev-44 into training or the locked 100. So the
   locked 100 must carry a single pre-registered sequence of tests, and every arm choice must be made off it
   (Crucible v1 §5).

**Caveats.**
- The paired spreads come from D0/early-D8-era runs (the master family, same 80 cases). Janus 0's own pair is
  unmeasured; the ×1.8 rows bracket it.
- The Dice SD of Δ is a model, not a measurement; Job 0 measures it (Janus 0 argmax vs thresholded, on the 60).
