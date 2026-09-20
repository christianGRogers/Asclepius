---
tags: [research, handoff]
status: living
updated: 2026-09-19
---

# Handoffs

Things found while researching datasets and benchmarks that belong to another
agent's topic. One line each, no follow-up done here.

- **Annotation-protocol agent:** CARDIAG (arXiv:2607.22139, X-ray angiography,
  2026 preprint) was built explicitly to fix quality problems its authors
  identify in its predecessor ARCADE: missing
  patient identifiers, no leakage-safe split, and "high concern towards the
  quality of the labels." CARDIAG's fix — institution/patient-stratified
  splits, explicit annotator-uncertainty labels, full DICOM metadata — is a
  directly transferable checklist for our own annotation protocol and split
  hygiene, even though the modality differs (X-ray vs CCTA). See [[Public
  coronary CCTA datasets]].
- **Class-schema agent:** confirmed by a dedicated search of the 2023–2026
  dataset landscape (ASOCA, CAT08, orCaScore, ARCADE, CARDIAG, CCA-200,
  PCCTA120 all checked): **no public dataset besides ImageCAS-X ships
  per-branch voxel labels on 3D CCTA.** This corroborates, rather than
  changes, [[Class schema options]]'s recommendation to adopt the ImageCAS-X
  schema — it is not one option among several, it is the only one.
- **Augmentation/preprocessing agent:** Zhang et al. 2025 (J Imaging Inform
  Med, ASOCA→GeoCAD cross-dataset study) found that artery contrast
  enhancement (r=0.408, p<0.001) and edge sharpness (r=0.239, p=0.046) were
  the strongest measured correlates of cross-dataset segmentation
  performance — stronger than calcification burden for the internal/external
  *gap* specifically. These are image-quality metrics computable at
  preprocessing/QA time. See [[External validation and cross-dataset
  generalisation for coronary segmentation]].
- **Class-schema agent:** if plaque analysis is ever a stated downstream goal,
  it needs the outer vessel wall boundary, which a lumen-only schema (ours,
  ImageCAS-X's) cannot supply. This is a schema gap, not a dataset-landscape
  one — flagged in more detail in the Metrics and clinical validation folder's
  own `Handoffs.md`.
