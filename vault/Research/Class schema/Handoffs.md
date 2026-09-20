---
tags: [research, handoff]
status: living
updated: 2026-09-19
---

# Handoffs

Things found while researching class schema and coronary anatomical labelling
that belong to another agent's topic. One line each, no follow-up done here.

- **Architecture agent:** Kim et al. 2025 (J Med Imaging 12(1):016002,
  doi:10.1117/1.JMI.12.1.016002) compared UNETR (transformer), U-Net,
  Attention-U-Net and nnU-Net on a 3-class (LAD/LCx/RCA) CCTA task at patch
  sizes 96³ and 128³; nnU-Net scored highest at the internal site (Dice
  0.794) but generalised worse externally than their self-supervised-
  pretrained UNETR (0.757 external vs presumably lower for plain nnU-Net,
  exact external nnU-Net figure not extracted). Detail in [[How many classes
  remain learnable given roughly 1000 cases]].
- **Metrics/acceptance-thresholds agent:** Föllmer et al. 2024 (Insights
  Imaging 15:250, doi:10.1186/s13244-024-01827-0) score coronary segment
  identity with a weighted Cohen's kappa that discounts adjacent-segment
  confusion (weight 0.5) versus distant confusion (weight 1.0), reaching
  weighted kappa 0.808 against a human-observer 0.809. Detail in
  [[Bifurcation ownership and carina voxel assignment]].
- **Datasets/benchmarks agent:** ARCADE (Popov et al., Sci Data 2024,
  doi:10.1038/s41597-023-02871-z) is a 2D X-ray angiography dataset, 1200+1200
  images, SYNTAX-derived ~25-class vessel-region schema plus a separate
  stenosis-region task; baseline YOLOv8 Dice 0.49, inter-rater Dice 0.73–0.90.
  Not CCTA and not importable as CT voxel labels, but the only public dataset
  built on the SYNTAX segment model. Detail in [[SYNTAX segmentation and the
  ARCADE dataset]].
