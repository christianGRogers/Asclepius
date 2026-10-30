---
tags: [janus-m, experiment, thinning, calibration, detectable-depth, f1, path-rest-ccta]
author: Hotel
round: 4
path: jm/rest-ccta
updated: 2026-10-30
issue: christianGRogers/Asclepius#205
---

# Lima's 45 percent and Hotel's 35 percent differ by the wall the F1 floor is measured against, and R9 never passes the measured wall

Round 3 ruling §8 item 2 and #205 item 2: explain Lima E5's 45 % against Hotel E7's 35 % on one seed with
`janusm.calibrate` (S3), and say which median wall JA40 should use.

## What was run

Simulations only. **No case was opened**; each script calls `janusm.guard.refuse([])` first by rule, naming nothing.

- **E8** `experiments/JanusM/Hotel/r4/e8_e5_vs_e7.py` → `e8_e5_vs_e7.json`.
  - S3's population, rule C and design (4 × 2000 per depth, depths 0.10–0.60, E7's seed sequence from 31000).
  - Every F1 variant is read on the **same simulated hearts**, so a change between columns is the F1 alone, and a
    change between rows is the input alone.
  - Inputs: cv_n 0.088 and Lima's 16-segment shape (as E5 and E7).
  - Also: Lima's own E5 design (one population of 4000 per depth from 0.15) at five seeds.
- **E9** `experiments/JanusM/Hotel/r4/e9_r9_median.py` → `e9_r9_median.json`. What `jm0r_decide.py`'s R9 prints for
  a JM-0R wall median M, as shipped and with M passed to S3.

## The four differences between E5 and E7

| Input | Hotel E7 (= S3) | Lima E5 |
|---|---|---|
| `median_mm` | 9.668 (Lima's self-test, 1.5 mm model-made labels) | 5.7 (Chen 2025 CT end-diastole) |
| F1 deviation | shape-corrected, against the remote level | raw territory mean − remote median |
| F1 floor | 1.0 mm (JA40) | 1.96 · √2 · 0.5 / √k = 0.57 mm (LAD, k 6), 0.62 mm (k 5) |
| added error σ_m | 0 | 0.5 mm |

## Result: E8, one seed (31000), detectable depth at ≥ 80 % mean territory sensitivity

| median_mm | σ_m | Rule C alone | Hotel F1 1.0 mm | Hotel F1, floor scaled to the wall ¹ | Lima F1 |
|---|---|---|---|---|---|
| 9.668 | 0 | 0.30 | **0.35** (E7) | 0.35 | 0.30 |
| **5.7** | 0 | 0.30 | **0.45** | 0.35 | 0.35 |
| 9.668 | 0.5 | 0.35 | 0.35 | 0.35 | 0.35 |
| 5.7 | 0.5 | 0.40 | 0.50 | 0.40 | **0.40** (Lima's inputs) |

¹ 1.0 mm × median_mm / 9.668: the same floor as a share of the wall.

Maximum false flags over all depths stay ≤ 0.039 in every cell (rule C alone, σ 0.5); with any F1 floor ≤ 0.026.

**Other seeds.** At seeds 32000, 33000 and 34000, Hotel F1 1.0 mm with σ 0 gives 0.45 at 5.7 mm and 0.35 at
9.668 mm every time. Lima's own E5 design gives **0.40 at four of five seeds and 0.45 at one**.

**The wall sweep** (σ 0, Hotel F1 1.0 mm, seed 31000). The simulated hearts' median wall is in brackets:

| median_mm | 4.5 (5.0) | 5.0 (5.5) | 5.7 (6.3) | 6.5 (7.2) | 7.0–9.668 (7.8–10.7) |
|---|---|---|---|---|---|
| depth | 0.55 | 0.50 | 0.45 | 0.40 | 0.35 |

## What explains 45 against 35

1. **The F1 floor is in millimetres, and rule C is scale-free.** With σ 0, a population with a thinner wall
   reaches the same rule C depth (0.30 in both rows), but 1.0 mm of shape-corrected thinning is 9 % of a 10.7 mm
   wall and 16 % of a 6.3 mm wall. Scaling the floor with the wall returns 0.35 at 5.7 mm. **The median alone
   moves E7 from 35 % to 45 %**, at every seed tried.
2. **Lima's configuration, run in S3's design, gives 40 %, not 45 %.** Its σ 0.5 mm lifts rule C itself from 0.30
   to 0.40. Its lighter F1 (0.57–0.62 mm on the raw deviation) then costs nothing more (rule C alone and Lima F1
   both 0.40).
3. **E5's printed 45 % is the upper of two seed steps.** Lima's own design gives 0.40 at four of five seeds. E5 drew
   its depth search after the whole κ grid on one generator, and landed on 0.45.

So E5's 45 % = (σ 0.5 added to a cv_n that JA40 says already holds the model's error) + a seed step. E7's 35 % =
a 9.668 mm wall. **Neither F1 implementation is in error.** Under JA40's own rules (σ 0, Hotel's F1, 1.0 mm) the
answer is set by the wall.

## Which median is right for JA40

**The wall of the population the table is computed on**, measured with the same thickness definition as the F1
floor. That is JM-0R's `thickness_median_mm`, and later the reference population's. Until JM-0R reports,
**5.7 mm**, for three reasons:

1. **9.668 mm fails the plan's own R3.** JA43 R3 holds a thickness definition only if the median lies within
   4.2–8.0 mm. Otherwise no thinning flag ships. A table that ever shows a thinning flag therefore has a wall
   ≤ 8.0 mm, where the depth is ≥ 0.35–0.40 (E9 below), never the 9.668 mm case.
2. **JA40 asks for conservative inputs until JM-0R.** 5.7 mm gives the larger depth.
3. **`median_mm` is not the measured median.** `population()` multiplies it by the phase factor (1.00 / 1.14 /
   1.40, mixed 40 / 40 / 20) and the shape. The simulated hearts' median wall is **K = 1.109 ×** `median_mm`
   (E9). E7's "9.668 mm" population had a 10.7 mm median wall. A measured M must enter as `median_mm = M / K`.

**So JA40's provisional print should be 45 %, not 35 %.** That is above 0.40, so the page's warning sentence
applies. It is still within JA41's 0.50 gate.

## Result: E9, R9 against the measured wall (cv_n 0.088, F1 1.0 mm, R9's seed 20261030)

| JM-0R `thickness_median_mm` | 4.2 | 5.0 | 6.0 | 7.0 | 8.0 | 9.668 |
|---|---|---|---|---|---|---|
| R3 holds? | yes | yes | yes | yes | yes | **no** |
| R9 as shipped | 0.35 | 0.35 | 0.35 | 0.35 | 0.35 | 0.35 |
| R9 with M / K passed | **0.60** | **0.60** | 0.45 | 0.40 | 0.40 | 0.35 |

**As shipped, R9 prints 35 % whatever the wall.** `decide()` calls `detectable_depth` without
`thickness_median_mm`, so S3 falls back to 9.668 mm. On a 4.2–5.0 mm wall the true depth is 0.60. That fails JA41's
0.50 gate (thinning should be a number only), but the shipped script would print 35 % and pass it.

## What it changes

- **A `role:swe` fix (Hotel v4, H4-S3):**
  - R9 passes JM-0R's `thickness_median_mm` to S3, which converts it by K;
  - S3's default median becomes the ED anchor;
  - the provisional print becomes 45 %.
- **Round 3's record:** JA49's "45 % vs 35 % unexplained" is explained, with neither implementation in error.
- **Unchanged:** cv_n (still the dominant input), the procedure and the 0.50 gate.
