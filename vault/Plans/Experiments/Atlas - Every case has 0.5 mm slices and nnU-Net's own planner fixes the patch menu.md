---
tags: [plans/experiment, geometry, nnunet, planner, patch-size]
author: Atlas
round: 1
updated: 2026-10-04
---

# Every case has 0.5 mm slices, and nnU-Net's own planner fixes the patch menu

## Question

1. What is the real voxel geometry of the 1000 cases? The vault says "near-isotropic ~0.35 mm".
2. Given that geometry, what patch size and batch size does **nnU-Net v2's own planner** produce, for the plain
   U-Net and the ResEnc presets, at several VRAM targets, at native spacing and at 0.5 mm isotropic? Does it plan a
   cascade? This replaces the hand arithmetic in [[Training plan]] §2 with the planner's real output.

## Method

- Headers of **all 1000** binary masks (`$SCR/data/masks/c*.nii.gz`; CT and mask share the affine). Shape,
  spacing, orientation. Header-only, no voxel data.
- A synthetic nnU-Net dataset (`Dataset710`) whose `dataset_fingerprint.json` holds the **real 1000 spacings and
  shapes** (the CT is full-FOV, so shape after nonzero-crop = full shape) and 5 labels (bg + LM/LAD/LCx/RCA). The
  planners read only `dataset.json` + the fingerprint, so this is the planner's exact output for this cohort.
  Intensity statistics in the fingerprint are placeholders; they do not affect patch/batch/spacing.
- nnU-Net **v2.8.1** (pip, 2026-10-04). Planners: `ExperimentPlanner` (plain U-Net) at 8 / 24 / 40 / 70 GB;
  `nnUNetPlannerResEncM/L/XL`; `ResEncUNetPlanner` at 60 and 75 GB. Each also with
  `overwrite_target_spacing=[0.5,0.5,0.5]`.
- Scripts: `experiments/Atlas/header_stats.py` (headers → `headers.json`), `experiments/Atlas/planner_sweep.py`.

## Result

**Geometry (all 1000 cases).**

| | value |
|---|---|
| In-plane matrix | 512 × 512 in every case |
| In-plane spacing | 0.289–0.465 mm, median **0.35**, mean 0.353 ± 0.030; 142 cases (14 %) differ from 0.35 by > 10 % |
| **Slice spacing** | **0.500 mm in all 1000 cases** |
| Slices | 166–277; 275 in 621 cases, 206 in 126; 333 cases < 256 slices |
| z extent | 83–138.5 mm, median 137.5 mm |
| In-plane FOV | 148–238 mm, median 179 mm |
| Voxels per case | 43.5–72.6 M, median 72.1 M |
| Anisotropy (z / xy) | median 1.43, max 1.73 — below nnU-Net's anisotropy threshold of 3, so no anisotropic handling fires |

nnU-Net's median-spacing rule gives target spacing **(z, y, x) = (0.5, 0.35, 0.35) mm**. "Native" for this cohort
therefore means 0.35 mm in-plane and 0.5 mm through-plane; it is **not** isotropic, and the in-plane axes of ~14 %
of cases get resampled by more than 10 %.

**Planner output (3d_fullres; patch in voxels z,y,x; mm extent z × y × x).**

| Planner / VRAM target | Spacing | Patch (vox) | Mvox | Extent (mm) | Batch | Patch / median volume |
|---|---|---|---|---|---|---|
| plain, 8 GB (default) | native | 96 × 160 × 160 | 2.5 | 48 × 56 × 56 | 2 | 3.4 % |
| ResEnc M | native | 96 × 160 × 160 | 2.5 | 48 × 56 × 56 | 2 | 3.4 % |
| plain 24 GB = ResEnc L | native | 128 × 256 × 224 | 7.3 | 64 × 90 × 78 | 2 | 10.2 % |
| plain 40 GB | native | 160 × 256 × 256 | 10.5 | 80 × 90 × 90 | 2 | 14.5 % |
| ResEnc XL | native | 160 × 320 × 256 | 13.1 | 80 × 112 × 90 | 2 | 18.2 % |
| ResEnc 60 GB | native | 160 × 320 × 320 | 16.4 | 80 × 112 × 112 | 2 | 22.7 % |
| plain 70 GB | native | 192 × 320 × 320 | 19.7 | 96 × 112 × 112 | 2 | 27.3 % |
| ResEnc 75 GB | native | 224 × 320 × 320 | 22.9 | 112 × 112 × 112 | 2 | 31.8 % |
| ResEnc L | 0.5 iso | 160 × 224 × 192 | 6.9 | 80 × 112 × 96 | 2 | 19.5 % |
| ResEnc XL | 0.5 iso | 192 × 256 × 256 | 12.6 | 96 × 128 × 128 | 2 | 35.7 % |
| ResEnc 60 GB | 0.5 iso | 256 × 256 × 256 | 16.8 | 128 × 128 × 128 | 2 | 47.6 % |
| plain 70 GB / ResEnc 75 GB | 0.5 iso | 256 × 256 × 256 | 16.8 | 128 × 128 × 128 | **3** | 47.6 % |

(Planner VRAM targets are nnU-Net's own estimates; the ResEnc presets M/L/XL are calibrated by the nnU-Net authors to
~9 / ~23 / ~37 GB actual use, Isensee et al. 2024, arXiv:2404.09556, Table 2.)

Two source-code facts checked in v2.8.1 while doing this:

- `3d_lowres` is planned when the fullres patch is < 25 % of the median image (`lowres_creation_threshold = 0.25`)
  **but is then dropped** if the low-res median image is less than 2× smaller than full-res. A cascade only exists
  if one trains `3d_lowres`; no gate on the 25 % figure is needed — simply never train it.
- `nnUNetTrainer` trains a **fixed 1000 epochs × 250 iterations**, saves a checkpoint every 50 epochs, and has **no
  early stopping** (no patience/early-stop code anywhere under `nnunetv2/training`). It also mirrors along all three
  axes and rotates ±30° by default in 3D (`configure_rotation_dummyDA_mirroring_and_inital_patch_size`).

## What it implies

1. The vault's "near-isotropic ~0.35 mm" is wrong for every case: slices are 0.5 mm. ([[Training plan]] "Fixed
   constraints"; [[Patch size is the dominant lever for thin vessels, and the evidence supports the 70 GB budget]].)
   It does not change the conclusion that no anisotropic handling fires (ratio 1.43 < 3).
2. At native spacing the 256³-volume cap in the planner is applied in **mm**, not voxels, so a 70 GB plain U-Net gets
   **192 × 320 × 320 = 19.7 M voxels at batch 2** (27 % of the median case), not "256³ at batch 3". The Training
   plan's statements that 70 GB "returns batch 3 at the same patch" hold only at 0.5 mm iso.
3. The ResEnc presets as shipped (M, L) give patches of 48–64 mm through-plane: too small to hold one coronary tree
   (see [[Atlas - A 128 mm patch at 0.5 mm holds the whole tree and the LM in almost every training patch]]). The recipe must set the VRAM
   target explicitly (`-gpu_memory_target`), not take a preset.
4. The research note [[Training schedule length and early stopping on a 24-hour walltime with job-chain resume]]
   describes loss-based early stopping and "validation every 50 iterations". Neither exists in nnU-Net v2.8.1:
   training is a fixed 1000 epochs, checkpoint every 50 epochs, 50 validation iterations per epoch. Job-chain resume
   (`--c`) is still the right mechanism.

## Limits

- Planner VRAM figures are estimates, not measured on an H100. The planner's estimate is conservative for plain
  U-Nets in practice, but the first GPU job must log real peak memory.
- The fingerprint's intensity numbers are placeholders; they only matter for normalisation, not planning.
