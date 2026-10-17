---
tags: [plans/experiment, ostium, aorta, negative-result, A1]
author: Bridge
round: 4
updated: 2026-10-08
---

# An aorta-preferred ostium changes nothing, because the learned ostium already touches the pool

## Question

The Round 3 ruling (§5, Bridge) asked for the **aorta-preferred ostium** to be implemented. Among the
namer's candidate left ostia, prefer an endpoint that touches the aorta. Does this fix the namer's ostium
errors (90.7 % within 5 mm of ImageCAS-X's start point; known failures c0325, c0800, c0519, c0211)?

## Method

- **Aorta stand-in.** Delta's contrast-pool rule (`experiments/Delta/treelib.py` `blood_pool`,
  re-implemented): CT smoothed at 0.7 mm, > 200 HU, coronary mask dilated 2 voxels and removed, 3 mm
  opening, components ≥ 2 cm³. It is computed on the mask's bounding box + 15 mm. TotalSegmentator needs
  ~5–7 GB of RAM, which this shared machine cannot give. On Trillium the master runs it anyway (A1).
- **Namer variants.** Frozen namer: ramus → LCx, 4 mm naming bridges, learned ostium + plausibility
  re-rank.
  - `rerank_learned`: as frozen.
  - `rerank_learned_pool`: the same, plus a logit bonus of 3 for any candidate endpoint within 3 mm of the
    pool. The bonus is large enough to override the learned order among the top-5 candidates.
- **Cases.** Every cached CT with ImageCAS-X labels and a cached skeleton: **39 cases** (4 outside my
  development set).
- **Truth and scoring.**
  - Ostium truth: ImageCAS-X left-centreline `start_points` (aorta contact).
  - Naming scored as in [[Bridge - Under the binding ramus rule the namer gets 88 percent of unseen thick-mask cases fully right]]
    (D1b).
- Scripts: `experiments/Bridge/pool_ostium.py`, `label.py` (`EP_HOOK`, `learned_pool`; the default path
  is unchanged).

## Result

| Variant (39 cases) | ostium ≤ 5 mm | ≤ 10 mm | all four classes ≥ 0.8 | swaps |
|---|---|---|---|---|
| learned (frozen) | 0.821 | 0.949 | 0.872 | 4 |
| learned + pool preference | 0.821 | 0.949 | 0.872 | 4 |

- **The pool preference changed the chosen ostium in 0 of 39 cases.** In 37 cases at least one candidate
  touches the pool (median 1), and the learned score already picked it.
- **The two large ostium failures (c0325: 51 mm; c0800: 42 mm) have no left-tree endpoint within 8 mm of the
  true start point and none touching the pool.** The thick mask's left tree, as skeletonised, offers no
  correct candidate. No candidate-ranking rule can fix that, aorta-based or not.
- The other failures (c0738, c0951, c0050) have the ostium right (2–8 mm) and fail on the LM end / LAD–LCx
  split.

## What it implies

1. **The aorta-preferred ostium is implemented and is a no-op on this sample.** It should stay in the
   namer as a cross-check, flagging a chosen ostium that touches no pool, but it is not a fix. The ruling's
   request is answered with a negative.
2. **The remaining ostium failures are candidate-generation failures**, not ranking failures. The fix would
   be to add a candidate where the tree meets the aorta (the aorta-contact point itself, as A1 defines it
   for tF1) rather than to re-rank skeleton endpoints. On Trillium, with TotalSegmentator aortas for all
   1000 cases (A1), that candidate is free. It is untested here.
3. **What remains is spread over decisions.** Held-out D1b failures: ramus 3, LM end 2, ostium 2,
   fused trees 1, absent ImageCAS-X LM 1. In this sample, 3 of 5 failures
   are the LM end or the LAD/LCx split. Those are exactly the decisions where the A13 D/R/H comparison will
   show whether the network's softmax (H) beats the rules (R).

## Limits

- 39 cases, of which only 4 are held out: the namer was developed on most of these.
- The pool is a stand-in for the TotalSegmentator aorta. It also contains the cardiac chambers.
