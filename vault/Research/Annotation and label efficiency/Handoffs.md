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
- **Loss function agent:** Karimi et al. 2020 (Med Image Anal 65:101759,
  arXiv:1912.02911) ran a direct, controlled comparison of majority vote,
  STAPLE, STAPLE+iMAE loss, minimum-loss-label, and learned annotator-confusion
  estimation on a multi-rater medical classification task; annotator-confusion
  estimation won on both accuracy and catastrophic-error rate. Detail in
  [[Fusing multiple annotations and learning from noisy labels]].
- **Metrics/acceptance-thresholds agent:** Föllmer et al. 2024 (Insights
  Imaging 15:250, doi:10.1186/s13244-024-01827-0) score coronary segment
  identity with a **weighted Cohen's kappa** that gives adjacent-segment
  confusion (e.g. proximal vs mid RCA) half the penalty of a distant
  misclassification — a ready-made way to score bifurcation-boundary
  disagreement without treating a 1-voxel carina call as equal to a wrong
  branch name. Detail in [[Sizing the overlap set and arbitrating
  disagreements]].
- **Datasets/pretraining agent:** Kim et al. 2025 (J Med Imaging 12(1):016002,
  doi:10.1117/1.JMI.12.1.016002) ran a self-supervised-pretraining data-scaling
  ablation on ImageCAS (1000 volumes) and found performance gains from
  pretraining "plateaued beyond 600 volumes." Not the same as labelled
  fine-tuning set size, but relevant if SSL pretraining on our full cohort is
  ever considered before the multiclass fine-tune.
