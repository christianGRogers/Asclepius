---
tags: [plans, experiment, post-processing, labels, topology, honest-negative]
author: Delta
round: 1
updated: 2026-10-04
---

# Label repair fixes islands but cannot fix a wrong carina — and a naive version makes things worse

## Question

A direct 4-class voxel model has no mechanism keeping one vessel one name (the failure the retinal
A/V literature calls intra-segment misclassification; see [[Enforcing per-branch connectivity so fragments are not assigned to the wrong branch]]).
Can a CPU post-processing step that only *relabels* voxels the model found repair that — and what
does it do to correct labels and to the other label errors (carina, whole-branch swaps)?

## Method

`experiments/Delta/postproc.py::relabel` (final version):
1. skeletonise the binary prediction; split into segments at junctions; each voxel is owned by its
   nearest centreline voxel;
2. **island repair along segments**: repeatedly take the shortest run of class L on a segment's
   centreline that is bounded on both sides by the same class M *and is shorter than both*; relabel
   it (and the L-voxels it owns) to M;
3. **small-piece absorption**: repeatedly take the smallest class piece that is not its class's largest
   piece in its tree and is ≤ 25 mm³; give it the class it touches most.
Nothing is added or deleted.

Evaluation: `postproc_eval.py` (all label corruptions from
[[Delta - Dice cannot see the errors that break a coronary tree]] on the ImageCAS-X 4-class reference,
cases c0039, c0099, c0162, c0224) and `islands_seeds.py` (5 random 3 mm label islands, 6 seeds × the same 3
cases = 18 trials). Wrong voxels = voxels whose label differs from the reference.

Two earlier versions were measured and rejected — reported because they are the obvious designs:
- **v0, unbounded absorption** (any non-largest class piece takes its neighbour's label): carina5 on
  c0039 went from 543 to **1365** wrong voxels — the mislabelled carina stretch orphans the correct
  OM/side branches beyond it, and absorption then renames them too.
- **v1, run rule without "shorter than both neighbours"**: on random islands, 8 trials went from
  6086 to **17 398** wrong voxels and 5 of 8 got worse — when two islands sit on one trunk, the trunk
  stretch between them is itself "bounded by the same class" and was renamed (c0162: 1068 → 7944,
  all RCA → LAD).

## Result (final version)

| Corruption (4 cases; side subtree 3) | wrong voxels before → after | tree-F1 before → after | per-class piece excess before → after |
|---|---|---|---|
| none (correct labels) | 0 → **0** | 1.000 → 1.000 | 0 → 0 |
| 5 random islands (1 seed per case) | 2576 → **0** | 0.984 → 1.000 | 9.75 → 0 |
| 5 random islands, 18 trials (6 seeds × c0039/c0099/c0162) | 13 383 → **204** (16/18 fully repaired, 0 worse) | — | — |
| carina, first 5 mm of LCx → LAD | 2123 → 2215 | 0.993 → 0.993 | 1.0 → 0.25 |
| carina, first 10 mm | 3715 → 3807 | 0.986 → 0.986 | 1.25 → 0.50 |
| largest LAD side subtree → LCx | 8527 → 8527 | 0.920 → 0.920 | 1 → 1 |
| expert D1 → LCx | 8411 → 8411 | 0.935 → 0.935 | 1 → 1 |
| LM → LAD | 8252 → 8259 | 0.743 → 0.743 | 1.25 → 0 |

## What it implies

1. **Islands — the voxel-noise label error a direct model is prone to — are repaired almost
   completely** (98.5 % of wrong voxels over 18 trials, never worse), and correct labels are never
   touched. This gives a direct 4-class model the "one vessel, one name" property that Bridge v1 gets
   from graph naming, without a second model.
2. **Boundary errors at the carina and whole-branch swaps are untouched** (≤ 92 voxels worse). That is
   correct behaviour — from labels alone there is no evidence which side is right — and it means
   those errors must be prevented by the model (context: the patch must see the carina) and *measured*
   (tree-F1 and macro Dice see them equally). Post-processing is not a substitute.
3. The per-class piece count falls to 0 excess in most corruptions even when the error remains
   (carina, LM→LAD): **a "one piece per class" check is not evidence that labels are right**, so it
   is a QA flag, not an acceptance criterion.
4. The two rejected versions show this step can do real harm if designed naively; it must ship with
   its regression test (identity unchanged; islands repaired; carina not made worse) and be judged on
   the validation fold by tree-F1, switchable off.

## Limits

- Corruptions are simulated on the reference; a real 4-class model's islands may be shaped
  differently (thicker, at bifurcations). Re-measure on the first multiclass validation predictions.
- 4 cases; the absorption cap (25 mm³) was chosen from one failure (c0039 carina) and not tuned.
  Carina rows get ~90 voxels worse (tiny LCx remnants absorbed) — negligible, but not zero.
