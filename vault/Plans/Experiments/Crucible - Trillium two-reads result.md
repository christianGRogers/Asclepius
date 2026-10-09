---
tags: [plans, experiment, gpu, trillium, double-reads, a11, a10, result]
author: Crucible
round: 5
updated: 2026-10-09
---

# Trillium result: train on both reads as separate samples. A11's name-conflict `ignore` costs 0.035 tF1 against the reads (CI excludes 0) and nothing measurable against the truth. Training on truth did not beat two simulated reads

## What ran

`trillium/crucible`, as pre-registered in [[Crucible - GPU experiment on training with two reads per case (pending)]]:

- **Model:** one H100; nnU-Net v2 3d_fullres; no mirroring; patch 96 × 160 × 160 at 0.5 × 0.35 × 0.35 mm.
- **Schedule:** 300 epochs × 250 iterations per arm, identical for all six arms (23 s/epoch); none unfinished.
- **Data:** 200 training cases (ImageCAS-X train list) and 50 test cases (ImageCAS-X val list; none sealed).
- **Truth T:** the ImageCAS mask split by ImageCAS-X territory names, ramus → LCx.
- **Reads simulated with `annot_bias`.** Read A is annotator X (carina +1.5 mm, stops early); read B is annotator
  Y (carina −1.5 mm, traces further). The arms are therefore tested in the habit regime on purpose.
- **Scoring:** tF1 @ 1.5 mm (the experiment's provisional copy), against T and against each read.

Results: `trillium-results/round5/crucible/results/` (SUMMARY.md, results.json, logs).

## Result (50 test cases)

| Arm | tF1 vs truth | tF1 vs reads (A10) | rooted recall vs truth | precision vs truth | LM tF1 vs truth | LM vs read A / read B |
|---|---|---|---|---|---|---|
| single (annotators alternate) | 0.800 | 0.771 | 0.828 | 0.828 | 0.849 | 0.750 / 0.772 |
| **both** | **0.830** | **0.789** | 0.856 | 0.846 | 0.930 | 0.811 / 0.785 |
| a11 | 0.822 | 0.754 | 0.850 | 0.835 | 0.889 | 0.783 / **0.505** |
| agree | **0.833** | **0.791** | 0.845 | 0.860 | **0.949** | 0.801 / 0.816 |
| union | 0.815 | 0.746 | 0.846 | 0.835 | 0.883 | 0.790 / **0.507** |
| oracle (trained on T) | 0.825 | 0.778 | 0.856 | 0.849 | 0.928 | 0.783 / 0.773 |
| *inter-read (B vs A)* | — | 0.877 | — | — | — | LM 0.638; LAD 0.948; LCx 0.941; RCA 0.973 |

Paired differences (bootstrap 95 % CI, 50 cases):

| Comparison | vs truth | vs reads |
|---|---|---|
| both − single | **+0.030 [+0.010, +0.050]** | +0.017 [+0.001, +0.036] |
| a11 − both | −0.008 [−0.018, +0.003] | **−0.035 [−0.046, −0.023]** |
| agree − both | +0.003 [−0.005, +0.012] | +0.002 [−0.006, +0.011] |
| union − both | −0.015 [−0.029, −0.004] | −0.042 [−0.057, −0.029] |
| oracle − single | +0.025 [+0.002, +0.048] | +0.006 [−0.014, +0.028] |

## The pre-registered decision table, applied as written

| Pre-registered row | Outcome | Decision |
|---|---|---|
| `both` beats `single` (CI excludes 0) and is ≥ `agree` and `union` | Yes: +0.030 [+0.010, +0.050]. No arm beats both: agree +0.003 n.s., union −0.015 (worse, CI excludes 0), a11 −0.008 n.s. | **Train on both reads as separate samples (the simplest). Fusion is not needed** |
| `agree` or `union` beats `both`, CI excluding 0 | No | — |
| No arm beats `single` | No: the second read is worth training signal (+0.030) | — |
| `a11` vs `both` against the truth: narrow A11's `ignore` only if a11 < both with the CI excluding 0 | −0.008 [−0.018, +0.003]. The CI includes 0 | **By this row, and by the master's A11 rule, A11 is not narrowed** |
| Expected: every fusion within ±0.002 of both against the reads | **Falsified.** a11 −0.035 and union −0.042, both CIs excluding 0 | The CPU claim that "A10 cannot choose a fusion" is wrong at network level, at least under habits |
| vs reads < vs truth by > 0.03 | Yes for every arm (both 0.789 vs 0.830) | Already decided by A10. Single annotators understate quality |

The two pre-registered rows point different ways for A11:

- The narrowing row does not fire.
- The general row picks both-as-samples, and on the master's *decisive* score (A10, vs reads) A11 is significantly
  worse than both.

I report both readings. The recommendation is in [[Crucible v7]].

## What is surprising

1. **Training on the truth did not beat two simulated reads.** Oracle 0.825 vs both 0.830 against the truth; the
   two arms were not compared directly, but both are +0.025 / +0.030 over single.
   - At 200 cases, one clean label per case is worth no more than two noisy reads per case. The two reads act as
     label augmentation, and their errors average out, as the CPU "converged model = per-voxel majority" argument
     predicted.
   - This is one seed, with a 300-epoch default patch, and the differences are small; it is not evidence that
     clean labels are useless.
2. **A11 and union hurt *against the reads* through one class: LM against annotator Y** (0.505 and 0.507, against
   0.785 for both).
   - Both schemes `ignore` the carina band where X's long LM and Y's short LM conflict. The network then fills that
     band, but **with LM**: it extends the LM from the proximal side, i.e. it adopts annotator X's habit. It does
     not split the difference.
   - Against the truth this costs LM 0.889 / 0.883 (both 0.930). Against Y's reads the LM falls by half.
   - So the CPU "FILL" proxy, which fills from the nearest supervised voxel, was right that the band gets filled,
     and wrong about where the boundary lands.
3. **Agree does not show this**, although it ignores the same conflict voxels: LM 0.949 vs truth, 0.816 vs Y.
   - The only difference from a11 is that agree also ignores extent differences, and a11 presents the case twice.
   - I cannot explain the gap from the summary statistics. With one seed it may be run-to-run variance on a small
     class. Treat a11-vs-agree as **unexplained, not as a finding**.
4. **Every arm misses the A10 gate overall** (best 0.791 vs inter-read 0.877), but not per class.
   - LM: every model beats inter-read (about 0.79 vs 0.64), because the habits are opposite and inter-read LM is
     poor.
   - LAD, LCx, RCA: models sit at 0.73–0.84 vs 0.94–0.97.
   - These are small-patch, short-schedule models, so this says nothing about the master's model. It does confirm
     that A10's per-class test is informative: it fails classes, not whole models.

## What it implies

- **Training target:** both reads as separate samples. This is the pre-registered winner, simplest, and
  significantly better than a11 and union on the decisive A10 score. Agree is equivalent (+0.003 / +0.002, n.s.)
  and remains a valid alternative.
- **A11's name-conflict `ignore` is the harmful part under opposite habits.** Without the conflict ignore, A11
  *is* both-as-samples. Recommended amendment: drop it. Keep A11's case-level third-read rule, which is unaffected.
- **The second read is worth training on** (+0.030 vs single), not only evaluating with.
- **A12a matters.** If wave 1 finds no habits, all schemes should behave alike (CPU, independent errors), and the
  choice is moot. The habit regime is where the conflict `ignore` hurts.

## Limits

- **Simulated reads with a deliberately strong opposite-habit model.** The real team's habits are unknown until A12.
- One seed per arm; a small default patch, not the master's 256³ ResEnc; 300 epochs; 200 training cases.
- tF1 is the experiment's copy (provisional under A9), with its thickest-voxel ostium.
- No per-case inspection was done. The per-class split comes from `results.json` aggregates only, and the 50 test
  cases are not sealed.
