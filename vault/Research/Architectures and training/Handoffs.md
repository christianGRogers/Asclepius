---
tags: [research/architecture, handoff]
status: living
updated: 2026-09-19
---

# Handoffs

Findings that fell outside "architectures and training strategy" and belong to
another topic owner. One line each, no follow-up done here.

- **Class schema owner:** Hampe et al. (J Med Imaging 2024) report per-AHA-segment
  labelling F1 on CCTA-derived coronary graphs: RCA 0.90, LAD 0.86 down to septal
  branches 0.54 — septal and small side-branches are the hardest class to identify
  correctly even from *manually verified* geometry, which is a relevant prior for
  how much annotator disagreement to expect on whichever classes the schema ends up
  treating as separate. See [[Downstream graph labelling of coronary branches is a second stage, never the segmenter]].
- **Datasets / benchmarks owner:** Kim et al. (J Med Imaging 2025, DOI
  10.1117/1.JMI.12.1.016002) is a second multi-institutional CCTA cohort (Cleveland
  + Taiwan sites, 91/23/26 + 73 cases) used for self-supervised pretraining
  evaluation on ImageCAS; a candidate external-validation source additional to
  ASOCA and TotalSegmentator, though not publicly released (privacy agreement).
