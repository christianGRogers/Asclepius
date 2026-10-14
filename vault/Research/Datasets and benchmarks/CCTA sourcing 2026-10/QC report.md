---
aliases: [QC report]
tags: [dataset, ccta, qc]
status: done
updated: 2026-10-14
---

# QC of the 904 volumes added to SegQueue/cases

Ten agents rendered every volume with `scripts/qc_render.py` (3 axial, coronal, sagittal, coronal MIP), looked at each picture and wrote one report line. Nothing was deleted or changed. Per-volume lines: `QC volume reports.csv` (name, Girder item id, anatomy, contrast, coronary visibility, resolution, quality, artefacts, orientation, annotatable, note).

**Totals:** quality good 195 / fair 480 / poor 229; annotatable yes 262 / limited 430 / no 212; orientation ok 895, unclear 7, rotated 2.

| Source | Volumes | Good | Fair | Poor | Annotatable yes | limited | no | Coronaries most / proximal / barely / no |
|---|---|---|---|---|---|---|---|---|
| TotalSegmentator-cardiac | 130 | 0 | 17 | 113 | 0 | 16 | 114 | 0 / 8 / 26 / 96 |
| ImageCHD | 110 | 8 | 92 | 10 | 1 | 82 | 27 | 0 / 2 / 69 / 39 |
| Taiwan-AICUP-CardiacCT | 100 | 78 | 22 | 0 | 90 | 10 | 0 | 19 / 77 / 4 / 0 |
| IDC-rider_lung_pet_ct | 90 | 1 | 58 | 31 | 3 | 66 | 21 | 0 / 19 / 58 / 13 |
| Mendeley-SDN-cy54ttk3fj | 80 | 45 | 34 | 1 | 70 | 10 | 0 | 22 / 52 / 6 / 0 |
| Mendeley-SDN-spb25zt2c4 | 47 | 2 | 24 | 21 | 4 | 30 | 13 | 2 / 12 / 22 / 11 |
| Figshare-EpicardialFat-CE | 40 | 0 | 26 | 14 | 0 | 34 | 6 | 0 / 12 / 28 / 0 |
| VMR-Coronary | 33 | 6 | 23 | 4 | 14 | 16 | 3 | 0 / 24 / 7 / 2 |
| Slicer-SampleData | 32 | 0 | 17 | 15 | 0 | 16 | 16 | 0 / 2 / 29 / 1 |
| ImageALCAPA | 30 | 0 | 29 | 1 | 0 | 30 | 0 | 0 / 0 / 30 / 0 |
| Kaggle-CAD-RandomSamples | 28 | 15 | 12 | 1 | 23 | 5 | 0 | 5 / 19 / 4 / 0 |
| HOCMvalvesSeg | 27 | 0 | 19 | 8 | 1 | 23 | 3 | 0 / 1 / 25 / 1 |
| Mendeley-SDN-4643nn2z44 | 24 | 0 | 23 | 1 | 3 | 20 | 1 | 0 / 6 / 17 / 1 |
| Mendeley-SDN-7x9kb53262 | 23 | 1 | 22 | 0 | 1 | 22 | 0 | 0 / 18 / 5 / 0 |
| CCA200-HF | 20 | 13 | 7 | 0 | 18 | 2 | 0 | 5 / 15 / 0 / 0 |
| PLOS-Peng2016-CCTA-JPEG | 17 | 0 | 17 | 0 | 1 | 16 | 0 | 0 / 15 / 2 / 0 |
| Figshare-CardiacCT15 | 15 | 8 | 7 | 0 | 10 | 5 | 0 | 1 / 13 / 1 / 0 |
| Mendeley-SDN-37nnfyh3x9 | 12 | 3 | 9 | 0 | 4 | 8 | 0 | 0 / 5 / 7 / 0 |
| IDC-varepop_apollo | 12 | 0 | 8 | 4 | 0 | 9 | 3 | 0 / 5 / 7 / 0 |
| Kaggle-HeartSR | 10 | 7 | 3 | 0 | 8 | 2 | 0 | 5 / 5 / 0 / 0 |
| SLAWT2016-CT | 9 | 4 | 5 | 0 | 6 | 3 | 0 | 1 / 8 / 0 / 0 |
| IDC-nsclc_radiogenomics | 4 | 0 | 3 | 1 | 0 | 3 | 1 | 0 / 0 / 4 / 0 |
| Zenodo-STOPSTORM | 3 | 0 | 0 | 3 | 0 | 0 | 3 | 0 / 0 / 0 / 3 |
| Mendeley-9wv3fkxstx | 2 | 0 | 2 | 0 | 1 | 1 | 0 | 0 / 1 / 1 / 0 |
| BMC-BEO2017-SerialStenosis-CCTA | 2 | 0 | 1 | 1 | 0 | 1 | 1 | 0 / 1 / 0 / 1 |
| Figshare-23057000 | 2 | 2 | 0 | 0 | 2 | 0 | 0 | 0 / 2 / 0 / 0 |
| Zenodo-21855641-AtrialFibre | 1 | 1 | 0 | 0 | 1 | 0 | 0 | 0 / 1 / 0 / 0 |
| Figshare-DCM3-Pulmonary35 | 1 | 1 | 0 | 0 | 1 | 0 | 0 | 0 / 1 / 0 / 0 |

## Systematic findings

- **Best for annotation:** Taiwan-AICUP (90 of 100 annotatable), Mendeley-SDN-cy54ttk3fj (70/80), Kaggle-CAD (23/28), CCA200 (18/20), HeartSR, SLAWT, Figshare-CardiacCT15, VMR (14/33).
- **TotalSegmentator-cardiac is mostly unusable for coronaries:** 114 of 130 "no" — 1.5 mm resampled, and many are routine chest/abdomen/neck CT despite the cardiac study type (several have no heart or only part of it).
- **Paediatric congenital sets (ImageCHD, ImageALCAPA, Slicer TruncalValve/PDA):** the heart is clear but infant coronaries are mostly too small to trace — "limited".
- **Spacing headers look wrong:** ImageALCAPA (all, 1.0 mm placeholder — known), HOCMvalvesSeg (1.0 mm placeholder), CCA200-HF (header FOV ~416 mm vs ~200 mm cardiac crop — spacing likely ~2x too large; check against the source), ImageCHD 1126/1129 (stretched in z).
- **Intensities:** HOCMvalvesSeg approximate HU, clipped at the top (420–840); PLOS-Peng2016 is 8-bit from JPEG; Figshare-EpicardialFat has 2.5 mm slices.
- **Multi-phase near-duplicates:** many RIDER, Mendeley-SDN and Slicer volumes are other phases of the same patient (stored separately as decided); a few look like true duplicates (RIDER-1563443119 ×3; some Mendeley-SDN series pairs).
- **Metal/hardware:** sternotomy wires/clips (several RIDER, VMR), prosthetic valve (Mendeley-SDN-spb25zt2c4 s018), pacemaker leads (EpicardialFat CE020), aortic stent graft (TotalSeg s1201).

## Volumes that need attention

- **Corrupt (no image):** VMR-Coronary__0157_H_CORO_SVGD_1 and _2 (constant values).
- **Rotated 180° in the axial plane:** VMR-Coronary__0148_H_CORO_SVGD and __0157_H_CORO_SVGD_0 (VMR conversion issue for this case family).
- **Orientation unclear (review):** ImageCHD__1022 (heart on the right: dextrocardia or flip), ImageCHD__1030 (ambiguous situs), Mendeley-SDN-7x9kb53262 s010_p15/p90 (dilated aorta), Mendeley-SDN-spb25zt2c4 s018_p0 (noise).
- **Non-diagnostic noise:** Mendeley-SDN-spb25zt2c4 s018_p0/p5/p10/p90/p95.
- **No contrast:** ImageCHD__1063; VMR 0178 (KD) looks non-contrast.
- **Privacy:** PLOS-Peng2016 volumes carry burned-in screen text; P04 shows patient name, ID, birth date, hospital and exam date (confirmed by eye). Most of the 17 show corner text. Not served to anyone (no live SegQueue records; SegQueue14 not deployed). Decision for the project lead.
