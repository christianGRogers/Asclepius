---
tags: [plans, experiment, round6, tree-f1, a1c, audit, a21]
author: Delta
round: 6
updated: 2026-10-10
status: report only. `src/segtrain/tf1.py` is frozen (A1c, sha256 3c737cbc…9253); nothing changed
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
