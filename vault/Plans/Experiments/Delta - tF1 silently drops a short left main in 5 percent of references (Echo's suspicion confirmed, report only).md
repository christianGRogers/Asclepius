---
tags: [plans, experiment, round6, tree-f1, a1c, audit, a21]
author: Delta
round: 6
updated: 2026-10-11
status: Round 7 ruling applied. Variant 1 (report only) is the default; the variant 3 fallback is opt-in. tf1.py sha256 3c737cbc…9253 → 9bb77e24…0608
---

# tF1 silently drops a short left main in 5 percent of references (Echo's suspicion confirmed, report only)

## The suspicion (Echo, A21)

`tree_f1` scores a class only if the reference **centreline** has voxels of that class. Its loop over classes reads `if not (rlab == c).any(): continue`. So a class that is present in the reference voxels but absent from the skeleton leaves `per_class` and the macro mean with no flag. Echo showed this on synthetic boxes, which `skeletonize` reduces to nothing.

## Does it happen on real references? Yes: 7 of 143 (5 %)

Data: the reference attributes from `experiments/Delta/r6_attrs.py`, i.e. Atlas's proxy for 80 val and 63 open test cases, measured with segtrain's own `_Centreline`.

| Case | Class | Reference voxels | Centreline voxels of that class |
|---|---|---|---|
| c0613 | LM | 724 | 0 |
| c0848 | LM | 1068 | 0 |
| c0772 | LM | 930 | 0 |
| c0805 | LM | 1228 | 0 |
| c0807 | LM | 321 | 0 |
| c0824 | LM | 362 | 0 |
| c0108 | LCx | 309 | 0 |

- **Confirmed in the GPU results.** Atlas's run-1 `per_case_val.json` has no LM entry for c0613 and c0848, although their references contain an LM. c0133 and c0956 genuinely have no LM. So the scored macro for those 2 cases is a 3-class mean, and the model's LM there is never scored.
- **Fragile cases.** 11 more references have an LM centreline shorter than 3 mm (1–9 skeleton voxels): c0068, c0099, c0225, c0252, c0323, c0340, c0400, c0424, c0592, c0624, c0753. Their LM tF1 rests on a handful of voxels.

## Mechanism (c0848, c0613)

- The LM in these references is a short, wide stub: 8–11 mm long, with an inscribed radius up to 1.9–2.4 mm.
- `skeletonize` shortens every vessel end by about its radius. The medial axis that is left starts at the bifurcation, and every skeleton voxel near the LM lies inside the LAD or LCx labels.
- LM voxels are 0.7–0.8 mm from the skeleton at best, about 3 mm at the median. No skeleton voxel carries label 1.

So this is not a box artefact. It is how a short, fat trunk skeletonises.

## What it costs

- The macro becomes a mean over 3 classes instead of 4 in those cases. Paired comparisons are unaffected, because every arm shares the reference.
- A prediction's LM errors in those cases are invisible: for example, an LM named LAD would not be counted.
- The bigger risk is for the two-reads machinery. Whether a read "has an LM" changes which classes are averaged. A per-class aggregate (A10 per vessel) silently loses a few percent of its LM cases. Those are the short-LM cases, where reads disagree most.

## Options for the judge (A1c: evidence note + regression tests; not applied)

1. **Make it visible, change no number** (recommended now):
   - add `classes_without_centreline` to `TreeF1`, filled with every class present in the reference voxels but absent from its centreline, and put it in `as_row()`;
   - aggregates report these cases separately, as A1b does for flagged trees.

   The tests needed are a short-LM-stub fixture (the class is listed and `per_class` is unchanged), plus every existing regression unchanged.
2. **Score the class anyway** (a metric change): give each reference voxel of a centreline-less class its nearest skeleton voxel, and score recall and precision on those skeleton voxels with the class's voxel label. This would change tF1 in 5 % of cases and needs its own validation before any decision table.
3. **Leave as is**, and document that tF1's LM term is undefined for short trunks.

I recommend option 1 before wave 1. Option 2 should be decided only if the first wave's reads show the problem is common in team labels.

## Related (A21)

`src/segtrain/aorta.py` (new, with `tests/test_aorta.py`) is the batch aorta producer that A1a needs outside a Trillium job.

- **Real check:** one real case (c0163, CPU, cropped around the tree): 96 s, peak about 5 GB, Dice 0.96 against the round-5 mask.
- **Limit:** TotalSegmentator must be called under `if __name__ == "__main__":`. Without the guard its spawned workers die. The module then fails that case loudly, as designed.

## Round 7: implemented under A1c (new sha256 `9bb77e24c5b8959d37752e260c78e4e589101687a7fe45f130b188670af90608`)

### What changed

**Variant 1, report only (the default).**
- `TreeF1.classes_without_centreline` is a sorted list of class ids. It is also emitted as `as_row()["classes_without_centreline"]`. This is the field that `segtrain.reads` and the A10 aggregates must carry (Crucible).
- No score changes: a centreline-less class stays out of `per_class` and the macro, exactly as before.

**Variant 3, the fallback (opt-in, off by default).**
- Called as `tree_f1(..., fallback_centreline=True)`. `TreeF1.centreline_fallback` records that it was used.
- A centreline-less class is scored on a fallback centreline: its own skeleton, or its maximal-EDT voxels if that skeleton is empty.
- Those points join the reference centreline with the class's label. They join the predicted centreline wherever the prediction covers them, with the predicted label.
- Rooting uses the same rooted components.
- `find_ostia` is unchanged (diffed against the frozen copy).

The frozen copy is kept as `experiments/Delta/tf1_3c737cbc.py`. The tests compare against it.

### Tests (`tests/test_tf1.py`, 27 tests, about 13 s; full suite 722 passed)

| Ruling test | Result |
|---|---|
| 1. Short-LM-stub fixture | LM voxels beside, not on, the skeleton (the c0848 geometry). LM is listed in the new field. `per_class`, recall, precision and tF1 are **bit-identical to the frozen copy** for the stub, a cut stub, an LM renamed LAD, and the plain fixtures |
| 2. Existing regressions | All unchanged: the Atlas, Bridge and Delta copies, the ostium tests, the gate and the audit |
| 5. Perfect prediction under the fallback | Every class, LM included, scores 1.0 |
| 6. LM renamed LAD under the fallback | LM tF1 is 0; LAD precision falls from 1.0 (default) to 0.67 |
| 7. Fallback where every class has a centreline | Identical to the default on all regression predictions. The fallback branch is not entered |

### Cohort identity check (ruling test 3), on the cached data: `experiments/Delta/r7_cohort_identity.py`

**Inputs.** All 143 proxy references (Atlas val 80, Delta open 63), each with one CPU-built prediction. The prediction applies three errors at once: LM renamed LAD, a 4 mm cut through the LAD 40 % along its axis, and the distal third of the RCA removed. For the 7 listed cases the identity prediction was also run. Run 1's predictions stay on Trillium, so this half of test 3 is pending (see below).

**Result.** The new and frozen code agree bit for bit on `per_class`, recall, precision and tF1 for **143 of 143** degraded predictions and for 7 of 7 identity predictions. The new field lists **exactly the 7 cases** of this note: c0613, c0848, c0772, c0805, c0807 and c0824 (LM), and c0108 (LCx).

**Paired report for the fallback** (an initial look at ruling test 8, on CPU-built predictions). Macro tF1, default → fallback:

| Case | Identity prediction | Degraded prediction |
|---|---|---|
| c0613 | 1.000 → 1.000 | 0.740 → 0.554 |
| c0848 | 1.000 → 1.000 | 0.766 → 0.573 |
| c0772 | 1.000 → 1.000 | 0.517 → 0.384 |
| c0805 | 1.000 → 1.000 | 0.528 → 0.391 |
| c0807 | 1.000 → 1.000 | 0.738 → 0.549 |
| c0824 | 1.000 → 1.000 | 0.754 → 0.564 |
| c0108 | 0.999 → 0.999 | 0.418 → 0.563 |

- In the six LM cases, the fallback LM term of the degraded prediction is 0, as an LM renamed LAD should score.
- In c0108 the missing class is the LCx, which that prediction gets right. The fallback raises its macro instead.
- So the fallback moves these 7 cases by −0.19 to +0.15 when the prediction is wrong there, and by nothing when it is right.

### Still to do before wave 1 (ruling test 8 and the run-1 half of test 3)

Run 1's val predictions must be re-scored under both hashes, for the 7 cases and overall, reporting the macro and the LM. This is a CPU step wherever the segmentations live: atlas2 already pins the old hash, and the miss census will copy them off $SCRATCH. Per Round 7, every atlas2 report should also list its `classes_without_centreline` cases. The default stays report-only until the judge adopts variant 3.
