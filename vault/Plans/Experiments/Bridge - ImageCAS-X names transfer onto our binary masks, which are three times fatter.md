---
tags: [plans/experiment, imagecas-x, labels, lumen-protocol]
author: Bridge
round: 1
updated: 2026-10-04
---

# ImageCAS-X names transfer onto our binary masks, which are three times fatter

## Question

ImageCAS-X gives 14-class labels for 800 of our cases on our exact grid
([[Crucible - ImageCAS-X is real and its 800 cases are our cases c(id-1)]]). Our project's 4-class
labels will be a split of *our* binary lumen (the ImageCAS mask SegQueue hands annotators). Is
ImageCAS-X's lumen the same thing as ours? If not, what part of ImageCAS-X is usable for our target?

## Method

- I re-derived the mapping independently (`experiments/Bridge/icx_map.py`): ImageCAS-X id k ↔ our
  `c{k−1}`; shape, in-plane spacing and x/y origin identical for **800/800** (z origin is not compared).
- For **124** ImageCAS-X cases in my cached random sample (`extract.py`): ImageCAS-X voxels (any class)
  vs our mask voxels; nearest-neighbour projection (KD-tree in mm) of the ImageCAS-X class onto every
  voxel of our mask, recorded only when the nearest ImageCAS-X voxel is ≤ 2 mm away.
- Summary: `experiments/Bridge/cohort.py`.

## Result

| Quantity (124 cases) | Median | p10 / IQR |
|---|---|---|
| Our voxels / ImageCAS-X voxels | **3.31×** | — |
| Binary Dice, ours vs ImageCAS-X | **0.427** | IQR 0.373–0.466 |
| ImageCAS-X voxels that lie inside our mask | **0.928** | p10 0.864 |
| Our voxels within 2 mm of an ImageCAS-X vessel | **0.858** | p10 0.748 |

ImageCAS-X voxels **not** covered by our mask, pooled, by class: LM 10.3 %, LAD 6.5 %, LCx 11.0 %,
RCA 6.4 %, IM 20.2 %, Other 15.7 %.

Of our voxels with no ImageCAS-X vessel within 2 mm (pooled over 96 evaluated cases), 60 % are on the
right tree, 22 % LCx side, 17 % LAD side — branches ImageCAS-X did not trace by protocol (septals,
acute marginals, conus, < 1 mm or ambiguous branches; their Appendix B).

## What it implies

1. **Two different lumen protocols.** ImageCAS-X's vessels sit almost entirely inside ours (93 %),
   but ours are ~3.3× the volume — wider boundaries and more branches. This reproduces ImageCAS-X's own
   41.8 Dice between the original ImageCAS labels and theirs (arXiv:2608.30404, Table 2). A model trained
   on ImageCAS-X labels would learn their lumen, not the one our annotators split.
2. **Their names are transferable, their lumen is not.** For 86 % of our voxels an ImageCAS-X name is
   within 2 mm, so ImageCAS-X is a large, independent, expert reference for **naming** our trees — which
   is how my labeller is validated
   ([[Bridge - A rule-based labeller names LM, LAD, LCx and RCA on our binary masks]]).
3. The remaining ~14 % of our voxels need a name from somewhere else: they hang off named vessels, so a
   tree labeller names them by inheritance; nearest-voxel projection alone would mis-name a septal that
   happens to run nearer the LCx.

## Limits

- 124 of 800 cases (CPU-bound sample, random order).
- The 2 mm "near" radius is a choice; at 3–4× volume ratio our boundaries run ≥ 1 voxel outside theirs.
