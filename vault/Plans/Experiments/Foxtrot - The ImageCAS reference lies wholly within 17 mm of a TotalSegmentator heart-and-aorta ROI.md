---
tags: [plans, experiment, fp-gate, post-processing, totalsegmentator, roi, round6]
author: Foxtrot
round: 6
updated: 2026-10-10 (extended to 92 cases after the Round 6 ruling, A20)
---

# The ImageCAS reference lies wholly within 17 mm of a TotalSegmentator heart-and-aorta ROI

## Question

A15 allows a component-level deletion filter as an FP lever only "with census evidence that it removes no
reference vessel". The literature's standard FP lever for vessel labelling is ROI localisation:

- TopCoW 2024 two-stage pipelines;
- ADE-HTL's TotalSegmentator heart masks;
- TotalSegmentator's own heart-cropped coronary model.

See [[Foxtrot - Nothing published by October 2026 beats a well-configured nnU-Net on per-branch coronary or vessel labelling]].

How far from a TotalSegmentator heart ∪ aorta mask does the ImageCAS (Girder) reference coronary mask
reach? Is there a distance d beyond which deleting predicted components can never delete reference
vessel?

## Method

- **Cases.** The first 40 non-sealed cases with a cached CT, in case-id order: c0000, c0020, c0025, c0038,
  c0041, c0050, c0073, c0075, c0100, c0111, c0113, c0125, c0133, c0141, c0150, c0163, c0172, c0175, c0196,
  c0200, c0217, c0225, c0250, c0252, c0264, c0270, c0275, c0288, c0300, c0325, c0341, c0350, c0362, c0368,
  c0375, c0400, c0405, c0407, c0425, c0434.
  - None is in [[Sealed test]]; checked against its lists.
  - Only the reference masks and CTs were read, no predictions.
  - The run was stopped at 40 of the 92 planned cases to free the shared CPU.
- **Script.** `experiments/Foxtrot/heart_roi_ref.py`; summary `experiments/Foxtrot/summarise_roi.py`. Raw
  output is in `$SCR/work/Foxtrot/roi.jsonl`.
- **Procedure.**
  1. Resample the CT to 3 mm, trilinear. That is the fast model's own spacing, and it keeps RSS under 1.5 GB.
  2. Run TotalSegmentator 2.18 `fast=True, roi_subset=['heart', 'aorta']` on CPU, giving ROI = heart (51)
     ∪ aorta (52).
  3. Upsample the ROI to 1 mm and take the Euclidean distance transform.
  4. For every reference voxel, read its distance to the ROI (nearest 1 mm cell). For every 26-connected
     reference component, record its minimum and maximum distance.
- Median 65 s per case on one thread.

## Result (40 cases)

| Quantity | Value |
|---|---|
| Reference voxels outside the heart ∪ aorta mask itself (d > 0) | 90.4 % pooled; the tree is epicardial, so the ROI must be dilated |
| Reference voxels > 5 mm from the ROI | 27.6 % pooled (max 63 % in one case) |
| > 10 mm | 0.93 % pooled; 32 of 40 cases have some |
| > 15 mm | 0.010 % pooled; 2 of 40 cases (c0073: 292 voxels; c0252: 133) |
| **> 20 mm** | **0 voxels in 40 of 40 cases** |
| Farthest reference voxel per case | median 11.2 mm, p90 14.2, **max 16.5 mm** (c0073), 16.4 (c0252) |
| Reference components deleted by the rule "delete a component whose every voxel is > d from the ROI" | d = 5 mm: 4 components (1–2 voxels each) in 3 cases; **d ≥ 10 mm: none** |
| TotalSegmentator heart mask sanity | smallest 11,818 3-mm voxels (median 19,300); no failure |

## What it implies

1. **A component rule at d = 25 mm cannot delete reference vessel on these 40 cases, with a margin of
   8.5 mm.** Every reference voxel is within 16.5 mm of the ROI. Any predicted component that overlaps the
   reference therefore has a minimum ROI distance ≤ 16.5 mm and is kept. Only components with zero
   reference overlap can be removed. As a result, per case:
   - the FP-component count can only fall;
   - tF1 recall is unchanged;
   - tF1 precision can only rise.

   d = 20 mm would also hold, with a 3.5 mm margin. I propose 25 mm because 40 cases are a small sample of
   the extreme.
2. **Whether the rule helps depends on where the FPs are**, which only the census can say. It helps only
   with FPs ≥ 25 mm from heart and aorta, e.g. pulmonary or chest-wall vessels, the kinds ImageCAS-X's
   supplement attributes to the original labels. It does nothing for FPs on the epicardium (veins, side
   branches outside the mask). The census's "distance to blood pool" and "centroid" columns do not answer
   this; a heart ∪ aorta distance column does.
3. **The ROI comes free with A1.** The A1 ostium already runs TotalSegmentator on every scored CT (aorta).
   Adding `heart` to `roi_subset` is the same model call.

## Extension to all 92 cached non-sealed cases (Round 6 ruling, A20 condition 1)

Same script and settings, resumed after the ruling. It covers every non-sealed case whose CT is cached in
`$SCR/data/ct`: 92 cases, the 40 above plus c0450, c0464, c0475, c0500, c0507, c0525, c0526, c0550, c0553,
c0560, c0575, c0579, c0586, c0600, c0606, c0613, c0615, c0625, c0650, c0675, c0679, c0695, c0700, c0717,
c0725, c0738, c0744, c0750, c0771, c0774, c0775, c0789, c0800, c0802, c0825, c0846, c0848, c0850, c0875,
c0900, c0904, c0906, c0907, c0919, c0925, c0927, c0950, c0951, c0956, c0959, c0974, c0975. None is sealed.
No CT was downloaded, and no TotalSegmentator output was kept.

| Quantity (92 cases) | Value |
|---|---|
| Farthest reference voxel per case | mean 11.4 mm, s.d. 2.0; median 11.1; p90 14.1; **max 16.5 (c0073)** |
| Tail (cases whose farthest voxel exceeds …) | 15 mm: **4** (c0073 16.5, c0252 16.4, c0575 16.2, c0606 15.8); 18 mm: 0; **20 mm: 0** |
| Next five | c0950 15.0, c0825 14.8, c0113 14.7, c0150 14.5, c0375 14.2 |
| Pooled reference voxels > 10 / > 15 / > 20 mm | 1.0 % / 0.006 % / 0 |
| Reference components the d = 25 mm rule would delete | **0** (at d = 5 mm: 11 components of 1–7 voxels in 9 cases; from d = 10 mm: 0) |
| Heart mask < 5000 3-mm voxels (rule disabled) | 0 cases (smallest 11,818) |
| Run time | median 51 s per case, 1 thread |

**A20 condition 1 holds on 92 of 1000 cases.** Requirement: maximum ≤ d − 5 = 20 mm in every non-sealed
case. The worst case here is 3.5 mm inside that bound. A normal extrapolation from mean 11.4 / s.d. 2.0 puts
the expected maximum over 900 non-sealed cases at about 18 mm. That is a heuristic, since the tail may be
heavier than normal. The remaining 908 cases (808 non-sealed + 100 sealed pass/fail) are proposed as a
job in [[Foxtrot v2]].

## Limits

- 92 cases (40 in the first pass), all with cached CTs. Extremes on 1000 cases may exceed 16.5 mm. The rule must be re-checked on
  each wave's read cases, and on the val/test reads before adoption.
- The distance is quantised at 1 mm and derived from a 3 mm mask; the error is about ±2 mm. That is a further
  reason for the 25 mm margin.
- Reference side only. No prediction was examined, so no FP reduction is claimed here.
- Under A15 this is a non-raw deletion filter. Whether its FP count may stand in for the raw count is the
  judge's decision.
