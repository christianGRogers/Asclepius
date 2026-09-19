---
tags: [research, handoff]
status: living
updated: 2026-09-19
---

# Handoffs

Things found while researching annotation protocol and label efficiency that
belong to another agent's topic. One line each, no follow-up done here.

- **Datasets/benchmarks agent:** ImageCAS-X (arXiv:2608.30404, preprint, Aug
  2026) re-annotated 800 of the 1000 ImageCAS cases and reports that against
  their own labels the *original ImageCAS* lumen masks score **DSC 41.8, HD95
  16.15 mm, Betti error 7.0** (p < 0.001), attributing the gap to inclusion of
  atherosclerotic plaque, false-positive pulmonary vessels and false-positive
  coronary veins. That is the mask our binary model is being trained on.
- **Datasets/benchmarks agent:** ImageCAS-X excluded 200 of the 1000 scans —
  motion (114), step artifact (76), poor contrast mixing (7), static noise (1),
  wrong FOV (1), file corruption (1) — and splits 560/80/160. Quality
  distribution of the kept 800: 55 poor, 140 adequate, 168 good, 437 excellent.
- **Class schema agent:** the original ImageCAS annotation was done "according to
  the AHA naming convention (17 paragraphs)" with per-branch names listed in the
  paper, but only a merged binary mask was released. Per-branch labels may exist
  upstream and be obtainable by asking the authors.
- **Metrics/clinical validation agent:** CAT08 (Schaap, Med Image Anal 2009,
  doi:10.1016/j.media.2009.06.003) normalises every score so that **50 points =
  inter-observer performance**. That is a ready-made design for expressing our
  metrics relative to the human ceiling rather than in absolute Dice.
- **Metrics agent:** ImageCAS-X reports Betti error and clDice per segment
  alongside DSC and ASSD; their inter-observer Betti error is 0.0–0.25 per
  segment, i.e. humans essentially never disagree on topology per branch, while
  their best model CAS-Net has aggregate Betti error 1.9 ± 1.5 against an
  inter-observer 0.2 ± 0.4.
