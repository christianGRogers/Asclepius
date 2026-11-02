---
tags: [janus-m, experiment, data, seal, pool]
author: Juliet
round: 1
updated: 2026-10-30
---

# Only 149 of 675 pool volumes are open to Janus-M today, and none is a normal adult CCTA

## Question

Janus-M must never read, score or train on a coronary sealed patient or a D35 decision-set patient ([[Janus-M]],
D37, M1). How much of the SegQueue14 pool (`configs/segqueue14/pool-2026-10.txt`, 675 volumes) is left for it, now and
after the coronary line's pending decisions?

## Method

`experiments/JanusM/Juliet/exclusion.py` (output `pool_free.json`) excludes, by patient key (a volume is excluded if
it belongs to an excluded patient; D33's merged RIDER pair is treated as one):

| Mode | Excluded |
|---|---|
| **strict** (today) | the 150-patient pool seal (D27/D32/D33); its extension order, the reserve (A34); the 20 ImageCHD report-only sealed patients; **every** Round 10 D35 candidate draw (Delta, Atlas, Bridge, Crucible, Foxtrot), because A33 freezes the union of the candidate draws until the lead answers Round 10 Q1 |
| **after_q1** | as strict, but only Delta's adopted draw (A33) instead of the union; the reserve still held |
| **after_a35** | as after_q1, and A35 keeps the seal at 150 and releases the reserve |

## Result

| Mode | Excluded patient keys | Free volumes | Free by source |
|---|---|---|---|
| strict | 320 | **149** | ImageCHD 63, ImageALCAPA 30, HOCMvalvesSeg 24, CCA200-HF 20, Taiwan AI-CUP 12 |
| after_q1 | 284 | 193 | + Taiwan 22, cy54ttk3fj 16, EpicardialFat 4, Kaggle-CAD 1, VMR 1 |
| after_a35 | 206 | 299 | + RIDER 23, cy54ttk3fj 34 in all, Taiwan 46 in all, VMR 13, Kaggle-CAD 12, EpicardialFat 15, … |

Today every free volume is congenital (ImageCHD, ImageALCAPA), hypertrophic (HOCM), on a suspect grid (ImageALCAPA,
HOCM and CCA-200 are the 74 header-spacing-suspect volumes, D29), or one of 12 Taiwan AI-CUP volumes.

## What it changes

- **The pool cannot be Janus-M's main image source or hold its seal.** A Janus-M seal drawn from the pool today
  would be drawn from abnormal anatomy and suspect spacing.
- **ImageCAS is.** It is adult CCTA from patients with suspected CAD (1000 cases; Zeng 2023,
  [10.1016/j.compmedimag.2023.102287](https://doi.org/10.1016/j.compmedimag.2023.102287)), already on Girder and on
  Fir (`$SCRATCH/icx4`). Juliet v1 uses only the **560 ImageCAS-X training cases** and the **180 non-sealed
  quality-0 cases**. It never touches the A14 sealed 100, val 80 or the ImageCAS-X test split. So no coronary decision
  set is read.
- **The pool's normal rest-perfusion volumes (Mendeley cy54ttk3fj, IRCCS SDN, CC BY 4.0, DICOM only, no labels) become
  usable only after the coronary decisions: 16 volumes after Q1, 34 after A35.** The dataset most likely belongs to
  Forte 2020 ([10.1111/cpf.12598](https://doi.org/10.1111/cpf.12598); matched by title, institution and n = 40, since
  the record links no paper).
  Juliet uses them, when free, as a report-only external domain check, never for a decision.
- **The guard is code.** Any Janus-M fetch of pool volumes calls `exclusion.py` (strict mode until the lead answers
  Q1, then the answered mode). This becomes part of the `role:swe` issue for the Janus-M data path.
