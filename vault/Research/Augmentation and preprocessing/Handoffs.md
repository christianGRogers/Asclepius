---
tags: [research/augmentation, handoff]
status: living
updated: 2026-09-19
---

# Handoffs

Findings that fell outside "augmentation, preprocessing and CCTA image quality"
and belong to another topic owner. One line each, no follow-up done here.

- **Loss / topology owner:** TotalSegmentator's current coronary model
  (`map_tasks_config.py`, task 509,
  `Dataset509_coronary_arteries_cm_nativ_400subj_SKELETON`) trains with
  `nnUNetTrainerSkeletonRecall`, i.e. a skeleton-recall loss, having previously
  used a plain DA-variant trainer for task 507 — a live example of a
  topology-aware loss chosen for coronaries in a shipped product.
- **Datasets / benchmarks owner:** TotalSegmentator's coronary model is trained
  on 400 subjects with a heart crop and 0.7 mm resampling; ASOCA (Gharleghi et
  al., Comput Med Imaging Graph 2022) is a second public CCTA lumen dataset,
  60 cases, 30 normal / 30 diseased, with a held-out test set — both are
  candidate external-validation sets for a cross-dataset check.
- **Metrics / clinical validation owner:** the ImageCAS benchmark reports Dice,
  HD and AHD only; its own failure analysis (Fig. 7, 8, 10) is qualitative.
- **Architecture / patch sampling owner:** ImageCAS measured patch size as the
  dominant factor in their patch pipeline — 79.56 / 81.22 / 82.34 % Dice for
  16³ / 32³ / 64³ (p < 0.0001, p < 0.001 pairwise), on ImageCAS.
