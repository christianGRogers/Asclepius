---
tags: [plans, candidate, topology, evaluation]
author: Delta
round: 1
version: 1
updated: 2026-10-04
---

# Delta v1 — Topology first, measured: decide on tree-F1, train for branch recovery, repair connectivity and labels after

## 1. Thesis

The errors that make a per-branch coronary segmentation useless are **breaks** (a tree that is
no longer connected to its ostium) and **wrong names** (an LCx stretch called LAD) — and the
metrics the other plans decide on cannot see them. On our data, a 3 mm cut through a proximal
vessel leaves Dice at 0.97 and per-class clDice at 0.92 while disconnecting 98 % of the tree from
its ostium; relabelling a whole first diagonal as LCx barely moves the binary metrics at all
(§4, E3). Two references of the *same* vessels (our masks vs ImageCAS-X) agree at Dice 0.46 but
on 93 % of centreline (E7), so voxel Dice mostly scores the boundary convention. A released
nnU-Net run on our own CTs shows what real errors look like (E8). So this plan (a) **decides every
choice on a rooted, labelled centreline metric — tree-F1 — validated against simulated and real
failures**; (b) trains one direct 4-class nnU-Net at native resolution with the one topology loss
that has coronary evidence (Skeleton Recall) as a paired arm; (c) puts connectivity and name
consistency where the evidence says they can be fixed — **post-processing that only reconnects
and relabels, never deletes** (hysteresis gap bridging on the probability map; island repair and
one-piece-per-branch absorption), each measured on real or simulated errors. I dropped the
separate localisation network from my opening thesis: a tree ROI with margin is still 38 % of the
volume (E1), so it buys 2–3× for a new failure mode.

DRAFT — sections 2–8 being written.
