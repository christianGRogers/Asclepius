---
tags: [janus-m, experiment, layers, laplace, AHA17, TPR, totalsegmentator, partial-volume]
author: Hotel
round: 1
updated: 2026-10-30
issue: christianGRogers/Asclepius#130
---

# Layers computed from two borders hold only if the borders are within half a millimetre, and at 1.5 mm the blur swamps the layer HU

## Questions

1. **Construction.** Can the transmural thirds and the AHA 17 segments be computed automatically from a myocardium
   mask and three cavity masks, on real hearts?
2. **Border quality.** How good must the two borders be for the computed layers, segment thicknesses and segment TPRs
   to be stable? This sets the deciding metric.
3. **Existing labels.** Where do TotalSegmentator's borders sit against the image's own edge?
4. **Layer HU.** Does the layer HU at clinical-dataset resolution carry the physiological endo/epi signal (TPR about 1.1),
   or partial volume?

## Data

The TotalSegmentator v1 dataset (Wasserthal et al., *Radiology: AI* 2023; Zenodo 6802614, **CC BY 4.0**).
- **Studies:** the 37 studies typed "ct heart" or "ct coronary arteries" in its `meta.csv`, minus **11 whose s-number is
  a coronary hold-out in the project pool** (5 sealed, 6 reserved; see "Disclosure"). That leaves **26 studies**:
  23 "ct heart" and 3 "ct coronary arteries".
- **Contrast:** 17 have LV blood > 150 HU (contrast); 9 do not, including the 3 "coronary arteries" calcium-score scans.
- **Volumes:** 1.5 mm isotropic, as released. The heart masks are model-made (Supplement S3).
- **Fetch:** `fetch_ts_cardiac.py` pulls only the CT and six masks per study out of the 28 GB zip by HTTP range
  requests, and skips coronary hold-outs.

## Method (`experiments/JanusM/Hotel/layers_from_borders.py`, CPU)

Per study:
- **Crop and resample.** Crop to the heart plus 15 mm, then resample to **0.75 mm**: CT linearly, masks through their
  signed distance. This lets sub-millimetre border errors be represented.
- **Transmural depth u.** Laplace's equation in the LV myocardium, solved by conjugate gradients on the voxel graph:
  - u = 0 next to the LV cavity;
  - u = 1 next to anything else (the epicardium, or the RV cavity across the septum);
  - Neumann conditions elsewhere.
- **Thickness and thirds.** Thickness = distance to the cavity + distance to the outside. The thirds are u < ⅓, ⅓–⅔
  and > ⅔.
- **AHA 17 segments.**
  - Long axis: the LV cavity's principal axis, oriented from the mitral centre (the LV voxels touching the LA) toward
    the apex.
  - Rings: basal, mid and apical thirds of the cavity length, plus an apex cap beyond it.
  - Sectors: angles from the septum (the RV centroid), with the anterior side taken from patient anterior; 6/6/4 sectors.
- **Edge profiles (contrast only).** The median HU is taken in 0.75 mm bins of signed distance from each label border:
  - at the endocardium, across the LV cavity border;
  - at the epicardium, across the free wall only, with the RV, LA and aorta (plus 3 mm) excluded.

  The plateaus are blood (≥ 3 mm deep in the cavity), the myocardial core (≥ 3 mm from both borders) and epicardial
  fat (−250 to −30 HU, 1.5–4.5 mm outside). The **half-maximum crossing** is where the image puts the edge; its
  distance from 0 is the label's offset. The 10–90% crossing distance is the edge's blur width.
- **Layer HU and TPR.** Mean HU per third, with insets of 0, 0.75, 1.5 and 2.25 mm from both borders. Per-segment
  TPR = mean HU of the subendocardial third / mean HU of the subepicardial third, on the 1.5 mm inset core.
- **Border-error propagation.**
  - Both borders are moved by independent smooth random fields (Gaussian, 6 mm correlation length) of RMS 0.5, 1.0
    and 1.5 mm, applied to the signed distances of the cavity and of cavity + myocardium.
  - Thirds, thickness, segments and TPR are re-derived and compared with the unperturbed result.
  - There are 2 draws per level. The RNG seed is 20261030 per worker; the run was split over 4 workers, round-robin
    in case order.

**Outputs:**
- per case: `e1_ts_cardiac_results.json`;
- summary: `e1_summary.json` (`summarise_layers.py`).

## Results

**1. Construction works on every heart.**
- **Coverage:** the AHA 17-segment construction ran on 26/26 studies, and the Laplace solve converged on all.
- **Thickness:** the median wall thickness is 10.7 mm (IQR 9.8–10.8) in the contrast studies. Over all 442 segments,
  the segment thickness has median 9.6 mm (IQR 8.5–11.0).
- **Resolution:** at 0.75 mm, the wall is 13 voxels across (median).

**2. Border error propagates into the layers much faster than into the myocardium** (26 studies, medians):

| Border RMS error | Myocardium Dice | Subendo. third Dice | Mid third Dice | Subepi. third Dice | Segment thickness error | Segment TPR error (relative) |
|---|---|---|---|---|---|---|
| 0.5 mm | 0.992 | 0.975 | 0.978 | 0.982 | 0.10 mm | 3% |
| 1.0 mm | 0.951 | 0.852 | 0.892 | 0.892 | 0.42 mm | 12% |
| 1.5 mm | 0.909 | 0.729 | 0.809 | 0.810 | 0.64 mm | 21% |

The relative TPR error is the absolute error divided by the case's median segment TPR. It is computed on the 17
contrast studies.

**3. TotalSegmentator's endocardium is unbiased; its epicardium sits about 0.9 mm out in the fat** (17 contrast studies):

| | Median | IQR |
|---|---|---|
| Endocardial half-maximum offset (negative = inside the cavity label) | +0.07 mm | −0.34 to +0.49 |
| Epicardial half-maximum offset (positive = inside the myocardium label) | **+0.86 mm** | +0.53 to +1.54 |
| Endocardial 10–90% edge width | **4.7 mm** | 4.6–5.0 (n = 12) |
| Plateaus (blood / myocardial core / epicardial fat) | 449 / 94 / −83 HU | — |

**4. At 1.5 mm, layer HU is partial volume, not perfusion** (17 contrast studies, median of per-case means):

| Inset from both borders | Subendocardial | Mid-wall | Subepicardial | Endo/epi |
|---|---|---|---|---|
| 0 mm | 194 HU | 111 HU | 35 HU | 3.15 |
| 1.5 mm | 176 | 110 | 75 | 2.58 |
| 2.25 mm | 167 | 108 | 86 | 2.15 |

- **Segment TPR:** on the 1.5 mm core, the per-case median TPR is 2.25 (IQR 2.10–2.49), with a within-heart SD across
  segments of 0.78.
- **The physiological value is far lower.** In normal territories TPR is 1.12 ± 0.13 under stress (George 2009, full
  text). At rest the endo/epi ratio is 0.99 in the septum and 1.23 elsewhere (Kühl 2012).
- **Non-contrast labels are worse.** On the 9 non-contrast studies, 15% of "myocardium" voxels are below −30 HU,
  against 6% with contrast.

## What it implies

1. **The layers can be computed, and should be.** Thirds and AHA segments are a deterministic function of four masks.
   The code runs in about a minute per heart on CPU. Nothing about them needs to be learned.
2. **Borders must be within about 0.5 mm for per-segment TPR, and within about 1 mm for thickness.**
   - Myocardium Dice 0.91, the level reported for CT (Zreik 2018: 0.91; Baskaran *JACC CI* 2020: median 0.92),
     corresponds here to about 1.5 mm RMS border error. At that error, the subendocardial third agrees at Dice 0.73
     and segment TPR moves by 21%, nearly twice the whole normal spread (0.13 / 1.12 ≈ 12%).
   - **A myocardium Dice that looks good therefore says little about the layers.** Hotel's deciding metric is border
     distance and segment thickness (Hotel v1 §7.2):
     - adopt at thickness MAE ≤ 0.5 mm and ASSD ≤ 1.0 mm;
     - ship per-segment TPR only at border ASSD ≤ 0.5 mm.
3. **Model-made labels need a written border rule before they seed reads.** TotalSegmentator's epicardium includes
   about 0.9 mm of fat. Seeded reads would inherit that bias, which is the D26 seed-anchoring risk in a new form. The
   half-maximum rule (Hotel v1 §6) names the border, and a script can check every read against it.
4. **Rest TPR at 1.5 mm is not a perfusion measurement.**
   - The endocardial edge is 4.7 mm wide (10–90%). The subendocardial third of a 10 mm wall is 3.3 mm, so it lies
     entirely inside the blur, and an inset does not rescue it: the endo/epi ratio is still 2.15 at 2.25 mm.
   - Rest TPR needs native sub-millimetre CCTA. Whether the blur there is narrow enough is the first thing Job M0
     measures on the pool's 0.5 mm volumes.
   - If it is not, TPR ships per territory only, or after a partial-volume correction (Hotel v1 §9).
5. **TotalSegmentator v1 is fit for pretraining and for testing the pipeline, not as a reference** for layer borders
   or layer HU.

## Limits

- **The volumes are 1.5 mm.** The blur widths and HU gradients are those of resampled data, not of native CCTA. Native
  data is Job M0's job.
- **The perturbation is a model of border error** (smooth, independent, isotropic). Real model errors are correlated
  with anatomy, for example at the base, the apex and the papillary muscles.
- **The AHA construction uses cavity-length thirds and the RV centroid**, not the RV insertion points. It is adequate
  for propagation tests, but a clinical version should find the insertion points.
- **No reader reference exists in this experiment.** "Offset" is against the image's half-maximum, not against a human.

## Disclosure

While the method was being developed, one study, **s0655, was opened before its coronary hold-out status was known.**
In the pool it is `TotalSegmentator-cardiac__s0655`, a sealed patient.
- **What was computed:** the myocardium HU, thirds, edges and segments. No coronary label was read, and no coronary
  model was run.
- **What was done afterwards:**
  - its outputs were deleted;
  - it, and the 10 other held-out studies, are absent from every result above;
  - every Hotel script now refuses held-out volumes through `coronary_holdout.py`.
- The PM is told, and the lead decides whether it matters.
