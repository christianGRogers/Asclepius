---
tags: [plans, experiment, pseudo-labels, label-noise, binary-masks]
author: Crucible
round: 1
updated: 2026-10-04
---

# A half-maximum HU rule inside the Girder mask nearly doubles its agreement with ImageCAS-X (0.40 → 0.78 Dice)

## Question

The Girder masks are ~3.6× the true lumen
([[Crucible - Original binary masks disagree with ImageCAS-X]]). For the 200
cases with no ImageCAS-X label, can a tight lumen be manufactured from what we
already have (Girder mask + CT) with no learning?

## Method

32 cached CTs that have ICX labels (c0000, c0050, …; every 25th case minus the
8 ICX-excluded). `experiments/Crucible/pseudo_lumen.py`:
`pseudo = girder_mask & (HU > T)`, with fixed T ∈ {150, 200, 250, 300} HU or
adaptive `T = f × p95(HU inside the Girder mask)`, f ∈ {0.4, 0.5, 0.6}
(a per-scan half-maximum rule; mean p95 = 472 HU). Optional: keep only the two
largest components. Dice vs ICX merged lumen.

## Result (32 cases)

| Rule | Dice mean | median | p10 | sensitivity | precision |
|---|---|---|---|---|---|
| Girder mask as is | 0.399 | 0.391 | 0.317 | ~0.92 (200-case note) | ~0.27 (200-case note) |
| HU > 150 | 0.719 | 0.716 | 0.616 | | |
| HU > 200 | 0.762 | 0.762 | 0.680 | | |
| HU > 250 | 0.757 | 0.772 | 0.695 | | |
| HU > 300 | 0.704 | 0.716 | 0.567 | | |
| HU > 0.4·p95 | 0.761 | 0.762 | 0.696 | 0.824 | 0.713 |
| **HU > 0.5·p95** | **0.779** | **0.784** | **0.713** | 0.753 | 0.814 |
| HU > 0.6·p95 | 0.756 | 0.765 | 0.674 | 0.664 | 0.885 |
| 0.5·p95 + 2 largest comps | 0.767 | 0.780 | 0.672 | | |

## What it implies

- A no-learning rule turns the Girder mask into a lumen at Dice ~0.78 vs
  ICX — far better than the raw mask (0.40), still well below what learning
  achieves on ICX (published nnU-Net 89.8, CAS-Net 91.2; human 92.8,
  arXiv:2608.30404 Table 2). So for the 200 non-ICX cases this is a **fallback
  pseudo-label / annotator seed**, not the plan of record: the plan of record
  is the ICX-trained model's prediction (expected ~0.90 on diagnostic scans),
  optionally constrained to the Girder mask region, which the HU result shows
  contains 92 % of the true lumen.
- Thresholding alone loses ~25 % of lumen (distal, low-contrast, partial-
  volume) — exactly where the rule-based namer and the team most need it.

## Limits

- The 32 cases are ICX-*included* (diagnostic) scans; the 200 non-ICX cases
  are non-diagnostic (motion/step artefacts), where both the HU rule and any
  model will do worse. Not measured: we have no reference lumen there.
- No calcium handling: calcified plaque (> threshold, inside the Girder mask)
  is counted as lumen by this rule.
