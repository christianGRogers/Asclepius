---
tags: [plans/experiment, patch-size, sampling, context, imagecas-x]
author: Atlas
round: 1
updated: 2026-10-04
---

# A 128 mm patch at 0.5 mm holds the whole tree, and the LM, in almost every training patch

## Question

A direct 4-class model must decide LAD vs LCx vs LM from what is inside one patch. Bridge argues that for half of a
patch's LAD voxels the deciding evidence (the LM bifurcation) is out of view
([[Bridge - Naming is one decision per tree, and half of a patch's LAD voxels cannot see it]]). For the patch sizes
nnU-Net's planner actually produces on this cohort
([[Atlas - Every case has 0.5 mm slices and nnU-Net's own planner fixes the patch menu]]):

1. In what fraction of cases does one patch hold each branch, each tree, the whole tree?
2. How often does a training patch contain each class — at random positions, and when nnU-Net centres a
   foreground patch on a voxel of a given class (does an LAD-centred patch see the LM?)
3. Is class-balanced sampling needed?

## Method

- **153 ImageCAS-X cases** (ids 1–125 and 934–998, two workers walking from both ends of the id
  list; stopped for CPU; duplicate rows from a restart removed), labels mapped to the 4 project classes (trunk mapping: LM = 1, LAD = 2, LCx = 3, RCA = 9). Left tree = all
  left-sided ImageCAS-X classes; right = RCA, R-PDA, R-PLA.
- Each class's presence max-pooled to a 2 mm grid. Patch geometries (x, y, z mm) from the planner sweep:
  ResEnc L native 78 × 90 × 64; plain 70 GB native 112 × 112 × 96; ResEnc 75 GB native 112 × 112 × 112; **0.5 mm iso
  256³ = 128 × 128 × 128** (ResEnc 60 GB or plain 70 GB at 0.5 mm). A patch larger than the image along an axis is
  clamped (nnU-Net pads).
- "Fits": some patch position contains every cell of the structure. "Random": fraction of in-image patch positions
  containing ≥ 1 cell of the class (nnU-Net's non-forced patches; it adds a small rotation pad, ignored here).
  "Centred on A, contains B": nnU-Net's forced-foreground rule (`data_loader.get_bbox`: patch centred on a random
  voxel of the chosen class, lower bound clamped, upper side may overhang into padding), averaged over A's cells.
- Script `experiments/Atlas/extent_sampling.py`, summary `summarise_extent.py`.

## Result

Extents (mm, x / y / z, median; p90): whole tree 107 / 90 / 85 (119 / 99 / 94; max 135 / 111 / 109); left tree
66 / 89 / 80; LAD 40 / 56 / 78 (59 / 68 / 91). Delta measured our (fatter, more distal) binary trees at a median
110 × 94 × 88 mm, p95 127 × 110 × 104
([[Delta - The binary masks are two clean trees, and a tight tree ROI is only 2-3x smaller than the volume]]).
Class shares of 4-class foreground: LM 6.8 %, LAD 29.6 %, LCx 18.5 %, RCA 45.1 %; foreground = 0.035 % of the
volume; LM present in 98.7 % of cases (absent = separate ostia).

**Fraction of cases where one patch holds the structure**

| Patch | LAD | left tree | right tree | whole tree |
|---|---|---|---|---|
| ResEnc L preset, native (78 × 90 × 64) | 0.25 | **0.07** | 0.31 | 0.00 |
| plain 70 GB, native (112 × 112 × 96) | 0.94 | 0.94 | 0.99 | 0.60 |
| ResEnc 75 GB, native (112³) | 1.00 | 1.00 | 0.99 | 0.65 |
| **0.5 mm iso, 128³** | 1.00 | 1.00 | 0.99 | **0.98** |

**Forced-foreground patch centred on a voxel of the row class: P(patch contains the column class)**

| Patch | LAD → LM | LAD → LCx | LCx → LM | RCA → LM |
|---|---|---|---|---|
| ResEnc L preset, native | 0.61 | 0.64 | 0.79 | 0.38 |
| plain 70 GB, native | 0.80 | 0.87 | 0.92 | 0.71 |
| ResEnc 75 GB, native | 0.89 | 0.92 | 0.98 | 0.95 |
| **0.5 mm iso, 128³** | **0.97** | **0.99** | **0.99** | **0.98** |

**Random (non-forced) patch contains the class**: 0.5 mm iso 128³ — LM 0.985, LAD 1.00, LCx 0.999, RCA 0.992;
ResEnc L native — LM 0.35, LAD 0.60, LCx 0.64, RCA 0.57.

## What it implies

1. **Patch size decides whether a direct model can see the evidence for a branch name**, and the presets do not
   provide it: the ResEnc L preset at native spacing holds the left tree in 7 % of cases and shows the LM to 61 % of
   LAD-centred patches — Bridge's concern is real for that configuration.
2. **At 0.5 mm with a 256³ patch it disappears**: the left tree fits in every case, the whole tree in 98 %, and
   97 % of LAD-centred patches contain the LM (99 % contain the LCx, i.e. the bifurcation's other child). At
   inference, a 256-slice window spans ≥ 93 % of the height of every case (max 277 slices), so every window sees the
   ostia. Bridge's 0.47–0.56 used patches placed uniformly among all positions containing a voxel, ignoring that the
   image itself is barely taller than the patch; with nnU-Net's actual placement the figure is 0.97.
3. Because 0.5 mm is lossless here ([[Atlas - Resampling to 0.5 mm isotropic loses nothing measurable, 0.7-0.8 mm does]]),
   the 128 mm patch costs nothing in resolution and fits in less VRAM than the native 112³ patch (16.8 vs 22.9 Mvox).
4. **No class-balanced sampler is needed**: every class is in ≥ 98.5 % of random 128³ patches. nnU-Net's default
   sampling suffices; the special sampler in [[Training plan]] §5 is moot at this patch size.

## Limits

- 153 of 800 cases, from the two ends of the id range (not random); extents were stable between the first 31 and
  the full 153 (whole-tree fit 0.97 → 0.98).
- ImageCAS-X trees are thinner and shorter than our masks; our masks' p95 extent (Delta) is 127 × 110 × 104 mm,
  still inside 128³ for the large majority. Recompute on the final team labels.
- 2 mm presence grid: containment is approximate to ±1 mm at patch edges.
- Containing the LM is necessary, not sufficient, for correct naming; the network still has to use it.
