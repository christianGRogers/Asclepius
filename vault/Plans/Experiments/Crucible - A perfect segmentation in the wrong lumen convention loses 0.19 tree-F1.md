---
tags: [plans, experiment, metrics, tree-f1, lumen-convention, imagecas-x]
author: Crucible
round: 2
updated: 2026-10-04
---

# A perfect segmentation drawn in the other lumen convention scores only 0.81 tree-F1

## Question

The master plan decides everything on macro tree-F1 @ 1.5 mm (tF1, amendment A1). It trains on either the expert
lumen (option A) or the Girder-seed proxy (option B), depending on a human decision (A3). What does tF1 charge for
a *convention mismatch alone*? In other words: if a model reproduced the Girder proxy perfectly, how would it score
against an expert-lumen reference? This sets the scale against which every model difference must be read, and it
says how costly it is to train in one convention and be judged in the other.

## Method

- 10 ImageCAS-X *test* cases with cached CTs (c0041, c0111, c0113, c0150, c0250, c0264, c0362, c0407, c0464, c0526),
  on crops of bbox(Girder ∪ ICX) + margin (`experiments/Crucible/r2_prep.py`, `r2_pack.py`).
- **Reference**: ICX lumen, territory 4-class. Ramus and "Other" go to the nearest LAD/LCx voxel.
- **"Predictions"**:
  - the reference itself (sanity check);
  - the **thick proxy**: the Girder mask, each voxel named by its nearest ICX voxel. This is Atlas's option-B
    proxy without the geodesic step.
- Metric: `experiments/Crucible/r2_eval.py`, a re-implementation of Delta's tF1 on these crops:
  - per class, recall = reference centreline predicted as that class *and* in a predicted component that touches
    the ostium (within 1.5 mm);
  - precision = predicted centreline of that class lying in reference voxels of that class;
  - gap tolerance 0 and 1.5 mm.
  - Ostium: the thickest LM / RCA skeleton endpoint (Delta's heuristic, not the aorta-contact rule).
- Summary: `r2_summ.py`.

## Result

| "Prediction" vs ICX-lumen reference | tF1@0 | tF1@1.5 | rooted recall | precision | per-class clDice | binary Dice | volume ratio |
|---|---|---|---|---|---|---|---|
| ICX lumen itself | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.00 |
| **Girder proxy (perfect option-B model)** | **0.806** | **0.806** | 0.883 | **0.764** | 0.806 | 0.397 | 3.52 |

Per class (tF1@1.5): LM 0.955, **LAD 0.740**, LCx 0.794, RCA 0.735. There are no cuts and no false-positive
components: the loss is all precision (centreline the expert did not trace, i.e. septals, conus, acute marginals,
veins; cf. [[Bridge - ImageCAS-X names transfer onto our binary masks, which are three times fatter]]) plus about
12 % of expert centreline that the thick mask's naming misses.

The reverse direction was **pending at the time of writing**: a perfect thin model scored against a thick team
reference. It is queued as `REF=thick r2_eval.py`.

## What it implies

1. **Under tF1, the lumen convention is worth about 0.19 points before any model is trained.** That is larger than
   any architecture, loss or spacing effect in the vault. A model trained in convention B and scored against a team
   that drew convention A (or the reverse) is penalised by roughly this much for doing exactly what it was taught.
2. So A3 is not a detail: **the training target, the seed and the reference must be one convention**, and it must be
   fixed before R1. Any mixing (for example, team labels drawn partly thin from ICX seeds and partly thick from
   Girder seeds) puts a ~0.2 tF1 noise floor under every comparison.
3. The thick convention's tF1 loss is almost all *precision on untraced branches*. If option B is chosen, the
   reference itself contains those branches, so they stop being errors. The number is a mismatch cost, not a
   quality verdict on either convention.

## Limits

- 10 cases. The ostium is a heuristic. The tF1 here is my re-implementation on crops (Delta's code expects its own
  loader), not the ported `src/segtrain` metric.
- The proxy omits Atlas's geodesic-growth and ignore-label steps; those change naming at the carina (0.3 % of
  voxels, per Atlas), not the untraced-branch precision that dominates here.
