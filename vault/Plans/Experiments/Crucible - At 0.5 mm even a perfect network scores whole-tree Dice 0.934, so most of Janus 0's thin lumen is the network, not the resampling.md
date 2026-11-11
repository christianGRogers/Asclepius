---
tags: [plans, experiment, janus-1-l, lumen-width, resampling, cpu]
author: Crucible
track: 1-L
round: 1
updated: 2026-11-11
issue: christianGRogers/Asclepius#302
code: experiments/Crucible/j1l_r1/resample_roundtrip.py
---

# At 0.5 mm even a perfect network scores whole-tree Dice 0.934, so most of Janus 0's thin lumen is the network, not the resampling

**Question.** Janus 0 draws the lumen about one voxel inside ImageCAS-X's. On val 80 its whole-tree Dice is 0.880, its
1-voxel-tolerant Dice 0.971 and its volume ratio 0.867 ([[icx4 - Results]]). It trains at 0.5 mm isotropic, but
ImageCAS-X is drawn at about 0.35 mm in-plane. How much of the shortfall would a *perfect* network still show, only
because nnU-Net resamples the labels to 0.5 mm and the prediction back? The answer decides whether Janus 1-L's
width lever is the export (the network) or the target spacing (the plans).

**Method** (CPU, `experiments/Crucible/j1l_r1/resample_roundtrip.py`).
- **Cases:** 140 ImageCAS-X **train** cases, evenly spaced over `filelist/train.txt`. No val, test, locked or sealed
  case was opened. Labels only, no CT.
- **Labels:** collapsed to four classes with icx4's own `territory.to_four` (D25).
- **The round trip, as in nnU-Net v2.8.1:**
  1. each class resized to the target spacing (order 1, kept where ≥ 0.5: `resize_segmentation`);
  2. a perfect network outputs that label as one-hot logits;
  3. the logits are resized back (order 1) and argmaxed (`convert_predicted_logits_to_segmentation_with_correct_shape`).
- **Variants:** target spacing 0.5 mm (Janus 0), 0.45 mm and 0.4 mm. Export by argmax (t = 0.5), or vessel wherever
  the summed vessel probability is ≥ 0.4 or ≥ 0.3.
- **Metrics:** whole-tree Dice, the 1-voxel-tolerant Dice and the volume ratio, as `r10_dice_check.measure()`
  defines them; per-class Dice.
- **Spacing of the 140:** in-plane 0.295–0.447 mm (mean 0.353), slices 0.5 mm.

## Result (140 cases; mean, p10–p90 in brackets)

| Target | Export | Whole-tree Dice | Volume ratio | Tolerant Dice | LM / LAD / LCx / RCA Dice |
|---|---|---|---|---|---|
| **0.5 mm (Janus 0)** | argmax | **0.934** (0.916–0.952) | **0.974** (0.963–0.984) | 1.000 | 0.953 / 0.926 / 0.923 / 0.938 |
| 0.5 mm | t = 0.4 | 0.937 | 1.081 | 1.000 | 0.954 / 0.931 / 0.927 / 0.940 |
| 0.5 mm | t = 0.3 | 0.922 | 1.160 | 1.000 | |
| 0.45 mm | argmax | 0.956 (0.939–0.970) | 0.953 | 1.000 | 0.969 / 0.951 / 0.948 / 0.959 |
| 0.4 mm | argmax | 0.975 (0.960–0.988) | 0.969 | 1.000 | 0.983 / 0.971 / 0.970 / 0.977 |
| *Janus 0, val 80 (measured)* | argmax | *0.880* | *0.867* | *0.971* | |

The 8-case pilot gave the same row for 0.5 mm (0.933 / 0.977), so the estimate is stable.

## Reading

1. **The 0.5-mm grid caps whole-tree Dice at about 0.934.** That is the ceiling even for a perfect network, and it
   costs about the same in every class (LCx and LAD most, as the thinnest).
2. **But the grid explains little of the *bias*.** A perfect network loses 2.6 % of the volume; Janus 0 loses 13.3 %.
   About **11 points of volume, and about 0.054 of Dice (0.934 → 0.880), are the network's own**: it puts the
   boundary inside the dim rim ([[icx4 - Results]]: missed voxels ≈ 237 HU against ≈ 372 HU in the overlap).
3. **So the first lever is the network's export, not the plans.**
   - For a perfect network, lowering the threshold adds almost nothing (+0.003 at t = 0.4) and overshoots the volume.
   - For Janus 0, whose probabilities on the rim are below 0.5, a lower threshold is the direct fix of an inward
     bias. How far it goes needs Janus 0's probabilities, which no file in the repository has: that is Job 0
     (Crucible v1 §6).
4. **A finer grid raises the ceiling** to 0.956 (0.45 mm) or 0.975 (0.4 mm). It would be the next lever once the
   network's bias is removed. It cannot warm-start from Janus 0: the A17a loader refuses a checkpoint whose plans
   differ (`finetune_load`). And at a 256³ patch it shrinks the field of view from 128 to 115 or 102 mm.
5. **tF1 is untouched by any of this:** the tolerant Dice is 1.000 in every variant, so the round trip moves no
   centreline beyond a voxel.

## What it changes

- Janus 1-L's width fix in round 1 is an **export threshold chosen on cases Janus 0 never trained on**, not a new
  spacing or loss (Crucible v1 §3).
- A finer-spacing, from-scratch run is costed and kept for a later round. It is triggered only when Job 0 shows the
  network's bias removed and Dice still more than 0.03 under the 0.934 ceiling (Crucible v1 §7).
- **Caveat.** This is a model of nnU-Net's resampling, run with skimage's `resize` exactly as nnU-Net calls it. It is
  not nnU-Net's own run on these cases. Crops (the tree's bounding box + 8 voxels) change rounding by at most one
  voxel per axis.
