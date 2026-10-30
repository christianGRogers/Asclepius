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

**Exclusion (the coronary seal):**
- All **16 TotalSegmentator subjects in the SegQueue14 pool** are excluded before download, and deleted if already
  present (`pool_subjects()` in `fetch_ts_cardiac.py`).
- Several of them are in the D27 seal and two are in Delta's D35 draw.
- No sealed, D35 or pool volume was read. 115 subjects were fetched (CT plus 6 masks each, by HTTP range
  requests). Images stay in the session's scratch space and are never committed.

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

**Used:** {N_USED} of {N_SUBJ}. Excluded: {EXCL}.

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

{RESULTS}

## What it implies (for [[India v1]])

{IMPLIES}

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
