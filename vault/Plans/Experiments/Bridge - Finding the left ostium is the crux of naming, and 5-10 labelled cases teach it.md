---
tags: [plans/experiment, branch-labelling, two-stage, ostium, label-efficiency]
author: Bridge
round: 1
updated: 2026-10-04
---

# Finding the left ostium is the crux of naming a binary tree, and 5–10 labelled cases teach it

## Question

A graph labeller that names LM / LAD / LCx / RCA on a binary lumen mask (see
[[Bridge - A rule-based labeller names LM, LAD, LCx and RCA on our binary masks]]) has to root the
left tree at the ostium: the left main runs from the ostium to the LAD/LCx split. If the root is
wrong, the LM is placed on some distal branch and LAD/LCx are swapped or merged. How reliably can the
ostium be found **from the mask alone**, does a naive **CT** cue help, and how many labelled cases does
a learned picker need?

## Method

- Cases: every case whose skeleton was cached by `experiments/Bridge/extract.py` at the time of the
  run and that has ImageCAS-X labels: **94 cases** (random order over c0000–c0999; mapping
  c = ImageCAS id − 1, verified independently in [[Crucible - ImageCAS-X is real and its 800 cases are our cases c(id-1)]]).
- Skeleton: kimimaro TEASAR on 26-connected components of the binary mask (scale 1.5, const 2 mm,
  anisotropy = voxel spacing). Candidate ostia = skeleton endpoints of the left tree (not touching the
  volume boundary); typically 30–60 per tree.
- Truth: the ImageCAS-X LM-majority skeleton vertex farthest from any LAD/LCx-majority vertex
  (ImageCAS-X labels projected to our voxels, ≤ 2 mm). A pick is correct if it is within 5 mm.
  Cases where no endpoint is within 5 mm of that point are dropped (1 of 95).
- Endpoint features (11): mean radius over the first 3 mm / 6 mm walking inward along the heavier side,
  max radius in 6 mm, relative height in the tree, stub length to first junction, fraction of the tree
  beyond the first step, distance to the right tree, and within-tree ranks of radius/height/distance.
- Pickers: three hand rules; a logistic regression (standardised, class-balanced) — 5-fold CV by case,
  and a label-efficiency curve (train on N random cases, test on a fixed third, 5 repeats).
- CT cue: for the 24–25 cached-CT cases with ImageCAS-X labels, fraction of non-mask voxels within 4 mm
  (and 10 mm) of each endpoint as bright as the local lumen (≥ 0.75 × median lumen HU), on the theory
  that the ostium abuts the contrast-filled aortic root.
- Scripts: `experiments/Bridge/extract.py`, `label.py` (`endpoint_features`), `evaluate.py`,
  `ostium_learn.py`, `ct_ostium.py`.

## Result

| Ostium picker | Top-1 correct (≤ 5 mm), n = 94 |
|---|---|
| widest terminal radius + height (my first rule) | 0.447 |
| mean radius over first 6 mm | 0.755 |
| hand-weighted combo (radius + height − distance to RCA tree) | 0.862 |
| **logistic regression, 5-fold CV** | **0.957** |
| logistic + anatomical-plausibility re-rank inside the full labeller (held-out, see labeller note) | reported there |

Label efficiency (fixed test third, n = 31; mean ± sd over 5 random training draws):

| Training cases | 5 | 10 | 20 | 40 |
|---|---|---|---|---|
| Top-1 ostium | 0.929 ± 0.013 | 0.942 ± 0.032 | 0.935 ± 0.029 | 0.955 ± 0.016 |

Largest standardised coefficients: relative height (+1.9), radius rank (+1.6), fraction of tree
beyond (−1.4), distance-to-RCA-tree rank (−1.0), max radius (+0.9): the ostium is the high, thick end
nearest the right tree whose walk-in leads into the bulk of the tree.

**CT cue: negative.** With the 4 mm sphere the brightest-surroundings endpoint was the ostium in
**1 of 24** cases; with 10 mm, **1 of 13** (stopped early). Distal ends are surrounded by bright
voxels too — the ImageCAS masks stop short of the visible lumen distally, and the cardiac chambers are
as bright as the aorta. A naive intensity threshold is not an ostium detector.

## What it implies

1. The only hard decision in naming a left tree is where it starts; everything downstream is
   topology. It is learnable from **5–10 labelled cases** to ~93–94 % and from ~40 to ~96 %, with an
   11-parameter model. This is the label-efficiency argument for a two-stage design measured, not
   asserted: the naming stage needs tens of cases, not hundreds.
2. A residual ~4 % ostium error remains on mask features alone. The image must supply the rest, and
   not through a naive HU threshold — a learned image cue (a small patch classifier at endpoints, or
   adjacency to an aorta mask) is the next thing to try; it is cheap because candidates are ~50 points
   per case, not a volume.

## Limits

- Truth is ImageCAS-X's ostium projected onto ImageCAS masks (different annotators, lumen 3× thinner);
  a pick 5 mm off can still be "right" in our protocol.
- 94 cases, not 800; the extraction pass was still running on a shared, saturated CPU.
- The logistic weights used inside the labeller were fit on the first 79 dev cases; the held-out
  evaluation in the labeller note uses cases never seen when fitting or when designing rules.
