---
tags: [janus-m, experiment, scar, LIE, registration, transmurality, kim-bins, round2, paired-scar]
author: Golf
round: 2
path: jm/paired-scar
updated: 2026-10-30
issue: christianGRogers/Asclepius#143
code: experiments/JanusM/Golf/lie_reg.py, experiments/JanusM/Golf/lie_calib.py
data: experiments/JanusM/Golf/lie_reg.json, experiments/JanusM/Golf/lie_calib.json
---

# LIE registration leaves about 0.6 mm of border error, and that error, not the threshold, limits the scar grade

## Question

Round 1 ruling §6 item 8 asks for the LIE-to-CCTA registration method and the scar-head design. Golf R1 E3 showed,
in 1-D, that on a late-iodine-enhancement (LIE) scan with bright blood the scar must be graded inside borders from
the first-pass scan. On real heart anatomy:

1. Which registration carries those borders onto a separately acquired LIE scan?
2. How much error is left?
3. What grading rule survives that error?

## Method

`lie_reg.py`, CPU; `lie_calib.py` for the half-split.

**Data.**
- **12 public TotalSegmentator v2.0.1 gated-like cardiac CTs.** Each passes `guard_r2` and the shared guard (no
  held-out subject or twin), and was used with its real CT and released labels: s0032, s0230, s0391, s0403, s0414,
  s0435, s0452, s0488, s0653, s0702, s0832, s0877.
- The first version of this note (PR #174) reported 11; s0832 finished after that merge. The tables below are all
  12, and no conclusion changed.
- Each heart is cropped and resampled to 1.0 mm.

**Scar.**
- Truth: a subendocardial scar in one standard territory per heart (LAD / RCA / LCx in turn). Each territory
  segment's depth is drawn from the Kim-bin midpoints, with a smooth ±5 % jitter.
- Truth per segment is the scar volume fraction, binned in Kim bins.
- 204 segments in total: 151 scar-free and 53 scarred (bins 1–4: 18 / 6 / 14 / 15).

**Synthetic LIE scan:**

| Tissue | Value |
|---|---|
| Remote myocardium | 90 HU |
| Scar | 150 HU |
| Blood (every CT voxel > 200 HU outside the wall) | 150 HU, **as bright as scar** |
| Fat | −80 HU |
| Elsewhere | the real CT at 35 % contrast |

PSF FWHM 1.0 mm, correlated noise, CNR 3 or 5.

**Misalignment** of the LIE scan by a known transform:

| Level | Translation | Rotation | Scale along a random axis | Smooth non-rigid field |
|---|---|---|---|---|
| none | | | | |
| typical | 4 mm | ≤ 2° per axis | 3 % | RMS 1 mm |
| large | 8 mm | ≤ 4° | 6 % | RMS 2 mm |

These levels are **assumptions**. Golf found no primary source for heart position between breath-holds that it could
open.

**Registration:** first-pass CT (moving) to LIE (fixed), Mattes mutual information, the first-pass heart dilated
10 mm as moving mask. Four methods, each chained from the last: identity (scanner coordinates); rigid; affine;
B-spline (30 mm grid). Borders are carried through signed distances; the AHA map by nearest neighbour.

**Graders** (per segment, on the LIE grid, inside the carried borders):
- **T:** fraction of wall voxels above remote mean + 3 SD; remote = mid-wall of the 4 darkest segments.
- **P ("core presence"):** as T, but the segment is called present only if ≥ 5 % of its voxels are scar after a
  1-voxel opening and outside the 1 mm next to the carried endocardium. Its extent is still the full T.
- **T ≥ τ:** presence by a threshold on T. τ is chosen by weighted kappa on 6 "development" hearts and scored once
  on the other 6 "test" hearts.

## Result

### 1. Registration (median over 12 hearts, CNR 5; ASSD and signed bias in mm, + = outward)

| Misalignment | Method | Endo ASSD | Epi ASSD | Endo ASSD p90 | Endo / epi bias |
|---|---|---|---|---|---|
| typical | identity | 2.01 | 1.97 | 2.06 | +0.57 / +0.60 |
| typical | rigid | 0.77 | 0.79 | 0.99 | +0.43 / +0.46 |
| typical | **affine** | **0.63** | **0.64** | **0.75** | **+0.19 / +0.16** |
| typical | B-spline | 0.70 | 0.68 | 1.05 | +0.26 / +0.39 |
| large | identity | 3.93 | 3.95 | 4.70 | +1.25 / +0.96 |
| large | rigid | 1.28 | 1.30 | 1.64 | +0.45 / +0.46 |
| large | affine | 1.04 | 1.09 | 1.58 | +0.16 / −0.04 |
| large | **B-spline** | **0.96** | **0.78** | **1.15** | +0.24 / +0.38 |

### 2. Scar grade, all 12 hearts, CNR 5 (Kim accuracy / weighted kappa / presence sensitivity / specificity)

| Borders | T (plain fraction) | **P (core presence)** |
|---|---|---|
| exact (no misalignment) | 0.97 / **0.97** / 1.00 / 1.00 | 0.90 / 0.88 / 0.70 / 1.00 |
| typical, identity | 0.56 / 0.11 / 0.34 / 0.75 | 0.74 / 0.17 / 0.15 / 1.00 |
| typical, rigid | 0.50 / 0.53 / 0.94 / **0.48** | 0.83 / 0.77 / 0.70 / 0.99 |
| typical, **affine** | 0.52 / 0.58 / 0.96 / **0.45** | **0.87 / 0.85 / 0.75 / 0.99** |
| typical, B-spline | 0.52 / 0.44 / 0.79 / 0.56 | 0.78 / 0.61 / 0.53 / 0.97 |
| large, affine | 0.53 / 0.45 / 0.85 / 0.53 | 0.78 / 0.57 / 0.47 / 0.95 |
| large, B-spline | 0.50 / 0.42 / 0.74 / 0.52 | 0.76 / 0.60 / 0.51 / 0.95 |

At CNR 3, every condition is worse. With exact borders T gives kappa 0.68; after typical affine, P gives 0.34.

### 3. A presence threshold τ chosen on 6 hearts, scored once on the other 6 (CNR 5)

| Borders | τ chosen | Test: accuracy / kappa / sensitivity / specificity | Same test hearts at τ = 0 |
|---|---|---|---|
| typical, rigid | 0.10 | 0.81 / 0.75 / 0.66 / 0.99 | 0.54 / 0.57 / 0.97 / 0.51 |
| typical, affine | 0.15 | 0.85 / 0.85 / **0.66** / 1.00 | 0.54 / 0.62 / 0.97 / 0.44 |
| large, affine | 0.10 | 0.72 / 0.53 / 0.48 / 0.88 | 0.54 / 0.48 / 0.90 / 0.53 |

## What it implies

1. **Scanner coordinates are not enough.** Identity leaves 2 mm at the typical level, and the grade collapses
   (kappa 0.12). Registration is required.
2. **Affine is the default; B-spline is a fallback.**
   - At the typical level affine has the smallest error (0.63 mm), the shortest tail (p90 0.75 mm) and the smallest
     bias.
   - B-spline adds a tail (p90 1.05 mm) and outward epicardial bias, and helps only at the large level.
   - So B-spline runs only for patients whose affine result fails the development gate.
3. **The residual ≈ 0.6 mm, not the noise and not the threshold, limits the grade.**
   - With exact borders, the plain fraction grades almost perfectly (kappa 0.97).
   - After affine registration the same rule calls **55 % of scar-free segments scar** (specificity 0.45): the carried wall now
     includes bright blood.
   - This is Juliet R1 E3's "scar-free walls read 4–12 %", reproduced on real anatomy and traced to its cause.
4. **Presence must come before the bin, and the robust presence rule ignores the innermost millimetre.**
   - P (core presence) holds specificity at 0.99 after any registration, and reaches kappa 0.85 and sensitivity 0.75
     after affine at CNR 5.
   - A single τ on T, calibrated on half the hearts, gives the same specificity but a lower sensitivity (0.66),
     because it also removes small bin-1 scars.
   - **Scar-0 therefore uses P for presence and the full T for the bin.** The development set may pick τ instead
     only if it beats P there.
5. **Even the best rule is at the edge of E6's sensitivity bound** (0.75 against a lower-bound target of 0.75), and
   CNR 3 is far below it.
   - So the paired cohort's LIE must be **reconstructed for CNR ≥ 5** (Golf R1 E3; dual-energy or photon-counting
     preferred).
   - **Scar-1** (a segment-profile grader trained on development LGE) is planned, not hoped for.
   - Same-phase, same-breath-hold acquisition is listed as a data requirement. It is the cheapest way to shrink the
     residual.

**Limits.**
- The LIE scan is synthetic, so registration is easier here than on real LIE, whose contrast differs from the
  first-pass scan in more ways. The registration numbers are therefore a best case.
- Blood is exactly as bright as scar, which is the hard case for grading.
- The model-made labels are interpolated to 1 mm.
- One territory per heart; 12 hearts and 204 segments; the half-split has 6 test hearts, so its numbers are noisy.
