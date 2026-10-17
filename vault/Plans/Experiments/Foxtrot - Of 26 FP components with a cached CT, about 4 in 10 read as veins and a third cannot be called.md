---
tags: [plans, experiment, fp-gate, census, veins, report, round8]
author: Foxtrot
round: 8
updated: 2026-10-11
---

# Of 26 FP components with a cached CT, about 4 in 10 read as veins and a third cannot be called

**Report only (Round 8: not a gate).**

## Question

What are atlas2 run 1's raw FP components? The candidates are cardiac veins, unlabelled arterial
branches, and mask artefacts (vessel the mask failed to cover).

This extends Atlas's reading of 21 components
([[Atlas - Trillium run 2 results, the A1 re-score, the window ablation and what the confident false positives are]]).
Here the criteria are explicit and stated in advance, and I report uncertainty.

## Method

- **Cases.** Every val case with a locally cached CT that has a raw FP component: **12 cases, 26 components**.
  They are c0038, c0225, c0252, c0288, c0368, c0400, c0606, c0613, c0717, c0848, c0950 and c0956.
  - By census category: 22 `confident_other`, 3 `icx_vessel`, 1 `low_confidence`.
  - The other 68 val cases and the 36 open cases have no cached CT. Their 93 components are not classified.
  - The default-window arm B has no local segmentations.
  - Nothing was downloaded.
- **Reference.** The projected proxy, rebuilt with atlas2's `lib/proxy.make_label`. FP components are
  exactly atlas2's set; this reproduction is exact
  ([[Foxtrot - On atlas2's val FPs the heart-and-aorta ROI rule removes nothing, because the FPs sit on the heart]]).
- **Scripts.** `experiments/Foxtrot/fp_triage.py` (features and rules) and `summarise_triage.py` (counts,
  bootstrap, per-component table). The rules sit in the script's docstring and were fixed before the script
  ran on any case.

**Features (per component).**

| Feature | Definition |
|---|---|
| `core_hu` | Median HU of the component eroded by 1 voxel |
| `art_hu` | Median HU of mask voxels ≥ 1 mm inside the mask and within 20 mm of the component |
| `r_art` | `core_hu / art_hu` |
| `r_ao` | `core_hu` / median HU of the 2 mm-eroded TotalSegmentator aorta |
| `ring_hu` | Median HU of a 1–4-voxel shell around the component |
| `diam` | 2 × the p90 of the EDT over the skeleton |
| `len` | Skeleton length |
| `dist_ref` | Distance to the reference mask |
| `along` | Fraction of the skeleton 1–10 mm from the mask |
| `companion` | Class of the nearest reference voxel |

**Classes (first match wins).**

| Class | Rule |
|---|---|
| `calcium_other` | `core_hu` > max(600, 1.5 × `art_hu`) |
| `mask_artefact` | `r_art` ≥ 0.75 and `dist_ref` ≤ 2 mm |
| `artery_branch` | `r_art` ≥ 0.75 and `dist_ref` > 2 mm |
| `vein` | `r_art` < 0.75, `ring_hu` < 0 (epicardial fat), `along` ≥ 0.5 (runs beside the tree) and `diam` ≥ 1 mm |
| `indeterminate` | everything else |

- **Connection to the coronary sinus / great cardiac vein.** This could **not** be tested: no label in the
  project or in TotalSegmentator's free `total` task marks the coronary sinus. Only the companion artery is
  reported (LCx = the GCV's groove).
- **Uncertainty.** A case-level bootstrap (5000 resamples) and the `r_art` threshold re-run at 0.65 and 0.85.

## Result (26 components, 12 cases)

| Class | n | Share | Case-bootstrap 95 % CI | At `r_art` 0.65 / 0.85 |
|---|---|---|---|---|
| **vein** | **10** | 38 % | [25 %, 55 %] | 9 / 10 |
| artery_branch | 4 | 15 % | [4 %, 28 %] | 5 / 3 |
| mask_artefact | 3 | 12 % | [0 %, 21 %] | 4 / 3 |
| calcium_other | 0 | 0 % | — | 0 / 0 |
| **indeterminate** | **9** | 35 % | [21 %, 48 %] | 8 / 10 |

Within the 22 `confident_other` components: vein 8, artery_branch 3, mask_artefact 3, indeterminate 8.

**Enhancement and shape (medians, IQR).**

- `core_hu` 124 [46, 156] against `art_hu` 247 [184, 344], so `r_art` 0.42 [0.20, 0.77].
- Aorta 536 HU, so `r_ao` 0.24.
- `ring_hu` −42, i.e. fat.
- `diam` 2.7 mm, `len` 7 mm, `dist_ref` 4.8 mm.
- Companions: LAD 9, RCA 9, LCx 5, LM 2.
- Veins by companion: LAD 6 (the anterior interventricular vein's course), RCA 3, LCx 1.

**What qualifies these counts.**

1. **"Vein" covers two kinds.** 6 of the 10 veins enhance (core 69–221 HU, `r_art` 0.36–0.72), as veins
   do in an arterial phase. **4 do not**: core 0–32 HU, `r_art` ≤ 0.14. An unenhanced tube in fat may be an
   unopacified vein, or it may be non-vessel tissue in the shape of a vessel. Seven of the 26 components
   have core < 60 HU. The ImageCAS mask itself puts about 47 % of its voxels at 16–38 HU ([[Human decisions]],
   D0). The model has been trained to call low-HU tubes "vessel", so some of these FPs may be the mask's own
   convention, repeated where the mask was not drawn.
2. **Most of the indeterminate components are low-enhancing tubes in fat** that lie more than 6 mm from the
   tree (`along` 0). Five of the nine would be "vein" if the "runs alongside" criterion were dropped. That
   is post hoc and is not adopted, but it puts **an upper range of 15/26** on veins and makes 10/26 the lower
   reading.
3. **Artery-bright components are a minority:** 7/26 (27 %), meaning unlabelled branches plus mask
   artefacts. Their CIs are wide.

## What it implies (report)

1. Atlas's reading (mostly veins, a minority of unlabelled arterial branches) holds on more components with
   explicit criteria. **Vein-like** is the largest single class at 38 % [25, 55], and up to 58 % if the
   course criterion is relaxed. **Artery-like** is about a quarter. About a third cannot be called from HU
   and geometry alone.
2. That supports an FP lever that teaches "low-enhancing tube in fat beside the artery is background" (Atlas's
   FP-aware loss). It also marks a risk. If a large share are unenhanced structures of the same kind the mask
   itself contains (47 % of mask voxels below 38 HU), a loss that suppresses them may also suppress mask
   vessel. **Run 3 should report recall on low-HU reference voxels** alongside the FP count.
3. **A human look at the 9 indeterminate and 4 unenhanced components** would settle most of the uncertainty
   cheaply: 13 components, minutes each.

## Limits

- 26 of 119 components (12 of 80 cases). The 93 others are unclassified.
- Thresholds are heuristic; their only basis is Atlas's 0.75. Sensitivity at 0.65/0.85 moves at most one
  component per class.
- There is no vein or coronary-sinus label, so "vein" is a reading of enhancement, fat and course, not a
  ground truth.
- `art_hu` is undefined for 1 component (c0288, 36 mm from the mask); it falls to `indeterminate`.
