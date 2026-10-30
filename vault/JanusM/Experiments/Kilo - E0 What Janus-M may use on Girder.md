---
aliases: [Kilo E0]
tags: [janus-m, experiment, data, seal, kilo]
status: done
round: 1
updated: 2026-10-30
---

# Kilo E0: what Janus-M may use on Girder

**Question.** Janus-M must never read, score or train on a coronary sealed patient or a D35 patient (D37).
After that rule, which of the volumes in `SegQueue/cases` can Janus-M actually use, and how many of them are
adult, ECG-gated CCTA with a trustworthy grid?

**Method.** `experiments/JanusM/Kilo/allowed_volumes.py` (standard library; run on CPU here, 2026-10-30). It walks
the 904 volumes of the 2026-10 QC report (`QC volume reports.csv`; names and Girder item ids only, no image read)
and refuses, **by patient** through `segtrain.pool_seal` (the hash-pinned D27/D32 guard, D33 aliases):

1. the pool seal, primary and report-only (seal sha256 `e71141b4…0690`);
2. the seal's whole extension order (A34's reserve: "untrained, unprelabelled and uninspected" until A35 sizes
   the seal);
3. every patient of **all four** Round 10 D35 draws (Delta's adopted one, and Atlas's, Bridge's and Crucible's),
   because A33 freezes every candidate draw until the lead answers Q1;
4. PLOS-Peng2016 (burned-in patient text; QC report);
5. volumes without the whole heart in view, or without contrast.

Kept volumes are flagged when their source has a suspect spacing header (ImageALCAPA, HOCMvalvesSeg, CCA200-HF)
or is paediatric congenital (ImageCHD, ImageALCAPA, Slicer). Output: `experiments/JanusM/Kilo/allowed_volumes.json`.

**Result.**

| | Volumes |
|---|---|
| In the QC report | 904 |
| Refused: sealed (by patient) | 369 |
| Refused: reserve (extension order) | 156 |
| Refused: in any D35 draw | 48 |
| Refused: heart not fully in view / no contrast / burned-in text | 20 / 2 / 17 |
| **Kept** | **292** (292 patients) |
| of which flagged paediatric or spacing-suspect | 166 (ImageCHD 88, ImageALCAPA 30, HOCMvalvesSeg 27, CCA200-HF 20, Slicer 1) |
| **of which adult, trustworthy grid** | **126**: TotalSegmentator-cardiac 97, Taiwan-AICUP 20, Figshare-EpicardialFat 6, Zenodo-STOPSTORM 3 |

Of those 126, the TotalSegmentator volumes are resampled to 1.5 mm and mostly routine (QC: 0 of 130 "good", 113
"poor"). EpicardialFat has 2.5 mm slices; STOPSTORM is "poor". **Only the 20 Taiwan-AICUP patients are adult,
gated, sub-millimetre CCTA of good quality (16 "good", 4 "fair").**

A breakdown that releases later (counted with the same rule, before the field-of-view filter): 109 volumes are
refused only for the reserve, and 29 only for a non-adopted D35 draw. Most of the reserve comes back when A35
sizes the seal at wave 1, and the 29 when the lead answers Round 10's Q1.

**What it changes.**

- **The coronary pool cannot be Janus-M's main training source now.** The seal, reserve and D35 have taken almost
  every good adult CCTA patient (Taiwan 43 sealed, 12 reserve, 25 in draws; Mendeley-SDN, RIDER, Kaggle-CAD, VMR,
  HeartSR: none free). Janus-M trains first on public data with myocardium labels (Kilo v1 §4).
- **The 20 free Taiwan patients are the only adult CCTA a Janus-M seal can come from today.** Kilo v1 seals all 20
  for Janus-M before anything is read (§6), and adds released reserve patients to Janus-M's training, never to
  its seal, when A35 releases them.
- **Coronary annotatability does not matter for the myocardium**: 135 of the 292 kept volumes are outside the
  coronary pool list (TotalSegmentator-cardiac 97, ImageCHD 25, EpicardialFat 6, HOCM 3, STOPSTORM 3, Slicer 1;
  mostly QC "not annotatable" for coronaries) and are still usable here.
- No sealed, reserved or D35 name is in the output (the script asserts it again before writing).
