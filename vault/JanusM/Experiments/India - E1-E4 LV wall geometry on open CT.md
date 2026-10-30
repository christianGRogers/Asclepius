---
aliases: [India - E1-E4 LV wall geometry on open CT]
tags: [janus-m, experiment, india, round-1, myocardium, layers, aha17]
status: done
round: 1
advocate: India
updated: 2026-10-30
---

# India E1–E4: LV wall geometry, layers and AHA segments on open CT

**Question.** Should Janus-M learn myocardial layers and segments as classes, or learn the borders and compute
them? How does a border error carry into layers, AHA segments and scar transmurality? And what does rest
attenuation by layer look like on open labels?

Used by [[India v1]]. Code: `experiments/JanusM/India/` (`lvgeom.py`, `exp_layers.py`, `summarise.py`,
`fetch_ts_cardiac.py`). Pooled numbers: `experiments/JanusM/India/results/summary.json`.

## Data

**Source:** TotalSegmentator v1 (Zenodo 6802614, CC BY 4.0; Wasserthal et al., *Radiol Artif Intell* 2023,
doi:10.1148/ryai.230024). Every study whose `meta.csv` type is a cardiac protocol: `ct heart`,
`ct heart-thorakale aorta`, `ct aortic valve`, `ct coronary arteries`, `ct left artrium`. That gives 130 subjects.

**Exclusion (the coronary seal), enforced in code:**
- All **16 TotalSegmentator subjects in the SegQueue14 pool** are excluded before download, and deleted if already
  present (`pool_subjects()` in `fetch_ts_cardiac.py`).
- Several of them are in the D27 seal and two are in Delta's D35 draw.
- The ids come from the pool list, the seal file and every Round 10 decision-set proposal
  (`pool_subjects()`). The loader refuses them before reading.
- **s-numbers name the same patient in v1 and the pool's v2.0.1.** Over the 1204 shared ids, sex and study type agree
  for 1203, ages differ by at most 4 years, and institute letters are relabelled consistently. This was checked on
  the two `meta.csv` files only.
- No sealed, D35 or pool volume was opened. The first, unguarded fetch stopped at s0111, below the first held-out id.
- 115 subjects were fetched (CT plus 6 masks each, by HTTP range requests). Images stay in the session's scratch
  space and are never committed.

**Labels:**
- Grid: 1.5 mm isotropic.
- Origin: model-assisted, all manually reviewed.
- The v2 release notes say v1's heart chambers had "systemic errors… (e.g. myocardium always slightly
  misaligned)" (`resources/improvements_in_v2.md` in the TotalSegmentator repository).

These are therefore **realistic LV shapes, not a border reference**.

**QC (per subject):**
- contrast: LV blood pool median > 200 HU and > 100 HU above the myocardium;
- cavity enclosed: ≥ 85 % of the cavity's shell is myocardium, LA or aorta;
- crop does not touch the volume edge;
- the long-axis frame is found.

**Used:** **64** of 115. Excluded: 50 failed QC (mostly non-contrast or weak contrast; some crops touching the edge or cavities not enclosed), 1 had no LV label. Subject list: `results/summary.json`.

## Method

1. The masks are resampled to 0.5 mm (trilinear on each mask, threshold 0.5). This is a CCTA-like grid.
2. **Depth.** Two transmural coordinates are computed:
   - distance-based, t = d_endo / (d_endo + d_epi);
   - Laplace, u = 0 on the endocardial shell and u = 1 on the epicardial shell, solved with CG.

   Thirds are taken at 1/3 and 2/3. Thickness is d_endo + d_epi at mid-wall (0.4 < t < 0.6).
3. **AHA frame.**
   - Base: the centroid of the LV cavity next to the LA.
   - Apex: the farthest myocardium point from the base.
   - Septal arc: the RV-contact myocardium in the mid ventricle.
   - Anterior insertion: the arc end with the larger anterior component.
   - Segments: 6/6/4 + apex cap (Cerqueira 2002).
4. **E2, perturbation.**
   - The endocardial and epicardial surfaces each move along their normals by an independent smooth Gaussian
     field. SD is 0.25, 0.5, 1.0 or 1.5 mm, correlation length 8 mm, applied to the signed distance.
   - There are also two pure biases: the epicardium 0.5 mm outward, and the endocardium 0.5 mm inward.
   - Layers are recomputed on the perturbed wall and compared with the reference layers.
   - **Synthetic scar:** in the LAD segments (1, 2, 7, 8, 13, 14, 17), all wall with reference depth t < x, for
     x = 10, 20, …, 90 %. It is fixed in space.
   - Transmurality per segment = scar volume / wall volume. It is read on the reference and on the perturbed wall
     (segments recomputed on the perturbed wall in the same frame) and binned 0 / 1–25 / 26–50 / 51–75 / 76–100 %.
5. **E3, frame robustness.** The share of myocardium whose segment changes, and whose AHA-default territory
   changes, under four frame changes:
   - the long axis tilted 5° or 10° (4 random directions);
   - the RV-insertion reference rotated ±10° or ±20°;
   - the base plane moved ±5 mm.
6. **E4, rest attenuation by layer** on the native 1.5 mm grid:
   - median HU of each third;
   - the subendocardial/subepicardial ratio (a rest analogue of George 2009's TPR);
   - the share of subendocardial voxels brighter than half-way between myocardium and blood pool.

Per-subject values are pooled as the 10th / 50th / 90th percentile over subjects.

## Results

All values: p10 / median / p90 over the 64 subjects.

### E1: wall geometry

| Quantity | p10 | median | p90 |
|---|---|---|---|
| Mid-wall thickness, 0.5 mm grid (subject median, mm) | 8.5 | 9.5 | 10.5 |
| Same on the native 1.5 mm grid (mm) | 8.4 | 9.2 | 10.2 |
| Voxels across the wall at 1.5 mm | 5.7 | 6.3 | 7.0 |
| **Voxels per third at 1.5 mm** | 1.9 | **2.1** | 2.3 |
| Voxels per third at 0.5 mm | 5.7 | 6.3 | 7.0 |
| Share of mid-wall thinner than 4.5 mm | 1.8 % | 2.6 % | 5.6 % |

By segment (median of subject medians, mm):

| Segment | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Thickness | 9.7 | 12.5 | 11.0 | 9.5 | 9.8 | 10.8 | 8.5 | 11.7 | 12.8 | 9.9 | 9.1 | 10.2 | 7.6 | 8.1 | 7.4 | 7.9 | 5.8 |

The thicknesses are well above CMR normals (5.3/6.3 mm mid-cavity, Kawel 2012). This is consistent with v1's label
offset, trabeculae counted as wall, and systolic reconstructions. The septal segments (2, 3, 8, 9) are thickest,
which is the expected pattern, and the apex is thinnest.

### E2: coordinate choice, and border error into layers and scar

- **Laplace vs distance thirds:** they agree on 88 % of wall voxels (87–89 %). The median |Δt| is 0.044.

**Border perturbation** (0.5 mm grid, correlation length 8 mm):

| Perturbation | Dice myocardium | Dice subendo third | Dice mid | Dice subepi | Scar transmurality \|error\|, median (pts) | p90 (pts) | Same 25-pt bin |
|---|---|---|---|---|---|---|---|
| random, SD 0.25 mm | 0.996 | 0.989 | 0.988 | 0.988 | 0.1 | 0.8 | 98 % |
| random, SD 0.5 mm | 0.976 | 0.927 | 0.936 | 0.934 | 1.0 | 3.2 | 94 % |
| random, SD 1.0 mm | 0.934 | 0.823 | 0.846 | 0.827 | 2.6 | 7.3 | 85 % |
| random, SD 1.5 mm | 0.891 | 0.716 | 0.759 | 0.721 | 4.0 | 10.5 | 79 % |
| epicardium +0.5 mm (bias) | 0.970 | 0.968 | 0.917 | 0.886 | 2.3 | 4.9 | 84 % |
| endocardium −0.5 mm into the cavity (bias) | 0.980 | **0.877** | 0.926 | 0.980 | 1.6 | 3.4 | 91 % |

The scar columns pool, per subject, the 7 LAD segments × 9 scar depths (10–90 %). The table gives the median over
subjects of each subject's median and p90.

### E3: AHA frame

- **Septal (RV-contact) arc, mid-ventricle:** p5 117°, p10 122°, **median 137°**, p90 151°, p95 154°. Fixed 60°
  sectors assume 120°.

**Myocardium reassigned to another segment / another AHA-default territory:**

| Frame change | Segment | Territory |
|---|---|---|
| long axis tilted 5° | 11.9 % | 5.1 % |
| long axis tilted 10° | 23.8 % | 10.3 % |
| RV-insertion reference ±10° | 15.2 % | 7.8 % |
| RV-insertion reference ±20° | 30.3 % | 15.7 % |
| base plane ±5 mm | 9.1 % | 2.5 % |

- **Segment volumes** (median, mL): 6.7–12.0 for segments 1–16, and 2.1 for the apex cap (17). The rule gives
  balanced segments.

### E4: rest attenuation by layer (native 1.5 mm, open labels)

| Quantity | p10 | median | p90 |
|---|---|---|---|
| LV blood pool median HU | 237 | 339 | 509 |
| Myocardium median HU | 73 | 95 | 142 |
| Subendocardial third, median HU | 103 | 143 | 238 |
| Mid-wall third, median HU | 72 | 98 | 141 |
| Subepicardial third, median HU | 37 | 66 | 108 |
| Subendo/subepi ratio (medians) | 1.52 | 2.13 | 3.78 |
| Subendocardial voxels brighter than half-way to blood | 9 % | 27 % | 50 % |

No subject has a ratio below 0.99. The ratio is not perfusion: the inner third is lifted by blood-pool partial
volume, and the outer third is lowered by epicardial fat.

## What it implies (for [[India v1]])

1. **Do not learn layers as classes.** On the only large open CT label grid, a third is about 2 voxels (E1).
   Two reasonable coordinate definitions agree on 88 % of voxels (E2), so a learned third would mostly learn
   label noise.
2. **Gate on the borders in mm, not on myocardium Dice.**
   - A 0.5 mm inward endocardial bias costs the myocardium 2 Dice points and the inner third 12 points.
   - A smooth error matching published myocardium Dice (0.88–0.94, i.e. about 1.0–1.5 mm SD here) leaves the inner
     third at 0.72–0.82 Dice. It puts 15–21 % of segments in the wrong scar-transmurality bin.
   - An error of SD ≤ 0.25 mm keeps every layer Dice ≥ 0.98 and the scar error p90 below 1 point. That is the
     basis of India v1's 0.25 mm gate on (model − inter-read) border ASSD.
3. **Report transmurality, not third-by-third Dice.** The clinically used number, segment scar extent, degrades
   more slowly than the layer masks: a 2.6-point median error at SD 1.0 mm.
4. **Compute AHA segments, and fix the septal rule in Round 2.** The frame is sensitive: a 10° error in the RV
   reference moves 15 % of the mass. The measured septal arc (median 137°) is wider than the 120° that fixed sectors
   assume. Territory assignment is less sensitive than segment assignment (about half), which favours
   patient-specific territories from Janus over the AHA default.
5. **Rest layer attenuation needs real 0.5 mm borders with trabeculae in the cavity.** On the open labels the
   subendo/subepi ratio is 2.1, so it measures partial volume, not tissue. India v1 keeps it report-only and makes
   the border convention a question for the lead (Q3).
6. **Do not borrow a CMR thinning threshold.** CT label thickness here is about 9.5 mm against CMR normals of
   5–6 mm.

## Limits

- **The shapes come from 1.5 mm labels upsampled to 0.5 mm.** They are smoother than a true 0.5 mm read, with no
  trabeculae. The perturbation results are about geometry and hold for any wall of this thickness. The absolute
  thickness and E4 numbers inherit v1's label offset. They are **not normal values**: the clinical status of these
  subjects is unknown.
- **The border-error model is smooth, isotropic and independent per surface.** Real model errors are likely
  correlated with trabeculae and the basal plane.
- **The AHA frame is a simple rule.** E3 measures how sensitive any such rule is; it does not validate this one.
- **Synthetic scar is a depth-defined shell.** Real scar is patchy. Transmurality here is a volume fraction per
  segment, which averages small errors away.
