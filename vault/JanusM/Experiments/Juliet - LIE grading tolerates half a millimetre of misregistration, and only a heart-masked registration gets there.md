---
tags: [janus-m, experiment, scar, lie, registration, phantom, path-b]
author: Juliet
round: 2
path: jm/paired-scar
updated: 2026-10-30
issue: christianGRogers/Asclepius#143
code: experiments/JanusM/Juliet/register_lie.py
---

# E6: LIE grading tolerates half a millimetre of misregistration, and only a heart-masked registration gets there

## Question

JA11 grades late iodine enhancement (LIE) inside the first-pass (CCTA) borders, carried onto the late scan. The two
scans are minutes apart in one session. The heart can sit elsewhere on the second breath-hold, while the spine,
chest wall and lungs move less. This experiment asks:

1. How much misregistration can segment-level Kim-bin grading tolerate?
2. Which registration method gets under that tolerance?
3. Can a check that needs no ground truth tell a bad registration from a good one?

## Method

**Synthetic 3-D phantom.** No case is opened; `guard_r2.gate()` runs first. Output: `e6_registration.json`
(68 runs, 68 min on 4 CPUs).

**Geometry.** 1 mm grid, 144 mm field, each voxel the mean of 2 × 2 × 2 sub-samples.
- **Static:** soft tissue, two lungs, the spine, the descending aorta.
- **The heart (moves between scans):**
  - LV cavity a = 25 mm, b = 45 mm, with a 10 mm wall and 3 mm of epicardial fat;
  - an RV crescent against the septum, and the LA;
  - 18 wall segments;
  - a contiguous patch of 2–6 segments with subendocardial scar, its transmurality drawn from 0.15 / 0.35 / 0.60 /
    0.90 (one per Kim bin).

**Intensities (HU).** Both scans have a Gaussian PSF with FWHM 1 mm.

| Tissue | CCTA (first pass) | LIE (about 7 min) |
|---|---|---|
| LV blood | 450 | 130 |
| RV blood | 350 | 130 |
| Myocardium | 110 | 90 |
| Scar | 70 | 90 + C, with C = 60 (or 40) |
| Fat | −90 | −90 |
| Lung | −800 | −800 |
| Bone | 500 | 500 |
| Noise SD | 30 | 15 (or 20) |

**Motion between scans.** The heart is translated by d mm (mostly cranio-caudal) and rotated by up to 0.4 d degrees,
with d ∈ {0, 0.5, 1, 1.5, 2, 3, 4, 6, 8, 10}.

**Cardiac-phase case.** One extra condition changes the LV cavity by 5 % (e = 0.05) between the scans. This change
is non-rigid.

**Registration.** All methods are rigid with 6 parameters. The LIE is moved onto the CCTA grid by mutual information
(Maes 1997, [10.1109/42.563664](https://doi.org/10.1109/42.563664)): 48 bins, Powell, two levels, 150k sampled points.
- **R0:** none (scanner coordinates).
- **R1:** MI over the whole field.
- **R2:** MI inside a heart mask: the CCTA labels (LV wall, LV, RV, LA) dilated by 10 mm.

**Grading.** This is the rule head of §8.3.
1. Smooth the registered LIE (FWHM 1.5 mm).
2. Take the remote reference from the darkest segment.
3. Threshold half-way to the myocardial 99th percentile.
4. Per segment, measure the **depth-binned transmural extent**: the share of 10 depth bins called scar, averaged
   over 3° × 2 mm columns.
5. Call the segment scar-present at T ≥ 0.10, then assign its Kim bin.

Truth is the same measure on the exact scar mask.

**Truth-free QC.** Two shares of CCTA myocardium voxels:
- "fat-like": the registered, smoothed LIE value is < 0 HU;
- "blood-like": the value lies near the blood level.

## Result

Means over 4 seeds. Bin accuracy is over all 18 segments, with the scarred segments alone in brackets. TRE is the
mean residual over the myocardium, in mm.

| d (mm) | R0 TRE | R0 bin acc. | R1 TRE (max) | R1 bin acc. | **R2 TRE (max)** | **R2 bin acc.** |
|---|---|---|---|---|---|---|
| 0 | 0.00 | 0.99 (0.94) | 0.42 (0.43) | 1.00 (1.00) | 0.51 (0.53) | 1.00 (1.00) |
| 0.5 | 0.51 | 0.99 (0.94) | — | — | — | — |
| 1 | 1.03 | 0.89 (0.69) | — | — | — | — |
| 1.5 | 1.54 | 0.82 (0.69) | — | — | — | — |
| 2 | 2.05 | 0.60 (0.54) | 0.81 (1.19) | 0.97 (0.88) | **0.33 (0.36)** | **0.99 (0.94)** |
| 3 | 3.08 | 0.26 (0.46) | — | — | — | — |
| 4 | 4.10 | 0.24 (0.40) | 1.70 (2.74) | 0.79 (0.81) | **0.31 (0.38)** | **1.00 (1.00)** |
| 6 | 6.16 | 0.15 (0.23) | 2.83 (4.66) | 0.46 (0.71) | **0.26 (0.38)** | **0.99 (0.94)** |
| 8 | 8.21 | 0.11 (0.19) | 4.00 (6.33) | 0.36 (0.56) | **0.28 (0.31)** | **1.00 (1.00)** |
| 10 | 10.27 | 0.10 (0.13) | 5.19 (8.18) | 0.17 (0.23) | **0.31 (0.64)** | **0.99 (0.94)** |

**Harder LIE (C = 40 HU, noise 20 HU).** R2 holds TRE 0.37 / 0.47 mm at d = 4 / 8, with bin accuracy 0.99 / 0.99.
R1 falls to 0.36 / 0.07.

**Truth-free QC (C = 60 HU), fat-like share by d (mm), with no registration:**

| d | 0 | 0.5 | 1 | 1.5 | 2 | 3 | 4 | 6 | 8 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| fat-like | 0.019 | 0.022 | 0.032 | 0.044 | 0.056 | 0.080 | 0.097 | 0.115 | 0.123 | 0.125 |

After R2, the fat-like share is 0.015–0.021 in every run. The blood-like share rises the same way (0.08 → 0.32).

**A 5 % cardiac-phase change** (e = 0.05) is not rigid, and no method fixes it:

| Condition | Bin accuracy on scarred segments | Sensitivity |
|---|---|---|
| no motion, no registration | 0.52 | 0.79 |
| R2 at d = 4 | 0.40 | 0.67 |

The CCTA endocardium lies inside the LIE scar, so scar is under-read. The fat and blood QC do not see it: 0.015–0.019
fat-like, which is in the normal range.

## What it shows

1. **The tolerance is about 0.5 mm.** At 0.5 mm grading is unchanged (0.99). At 1 mm, bin accuracy on scarred
   segments falls from 0.94 to 0.69. At 2 mm, specificity is 0.63: the moved blood pool and fat read as scar or as
   a gap.
2. **Whole-field MI is pulled to the static chest.** Its residual grows with d (5.2 mm at d = 10) because the spine,
   lungs and chest wall dominate the histogram and did not move.
3. **Heart-masked MI (R2) lands at 0.26–0.56 mm mean residual at every d from 0 to 10 mm, and grading is
   0.98–1.00 at every d > 0.** That makes it the method.
   - The one weaker cell is d = 0 with the harder LIE (C = 40, noise 20). There R2 moved a well-aligned scan by
     0.56 mm and specificity fell to 0.86 at τ = 0.10, with bin accuracy 0.88. E7's calibrated τ recovers most of it
     (0.88 / 0.95 at τ = 0.15).
   - Its floor of about 0.3–0.5 mm (0.51–0.56 at d = 0) is above zero. Noise and the 1 mm grid set it. Grading is
     unaffected.
   - Without motion, though, R0 is better. So the pipeline keeps R0 when R0 already passes QC.
4. **The fat-like share is a usable truth-free gate.** It separates ≤ 0.5 mm (≤ 0.022) from ≥ 1 mm (≥ 0.032).
   Real values differ by scanner and patient, so the cut is set on the cohort's calibration third, not taken from
   here.
5. **A cardiac-phase mismatch is not a registration problem; it is a data requirement.** The LIE must be
   reconstructed at the CCTA's phase, or the borders must come from a CCTA phase reconstructed to match the LIE.
   Neither QC number detects it.

## What it changes

- **Registration method (Juliet v2 §8.2):**
  1. Start from scanner coordinates (one DICOM frame of reference).
  2. If the fat-like QC fails, run rigid MI inside the CCTA heart mask dilated by 10 mm.
  3. Accept only if QC passes after registration. Otherwise the patient is excluded from scoring and counted as a
     registration failure. Failures are reported, never hidden.
- **Cohort data requirement:** the LIE and CCTA gating phases are recorded and matched (§8.1).
- **Limits.**
  - Rigid heart, homogeneous tissue, a 1 mm grid, and no microvascular obstruction.
  - The breath-hold displacement range is an assumption (no heart-specific source found).
  - 4 seeds per cell.
  - Real LIE has lower CNR and beam-hardening, and the first-pass RV is denser than here.
  - The calibration third is the first real test.
