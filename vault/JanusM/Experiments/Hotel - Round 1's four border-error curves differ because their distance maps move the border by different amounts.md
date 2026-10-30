---
tags: [janus-m, experiment, perturbation, harness, layers, STA, calibration, path-rest-ccta]
author: Hotel
round: 2
path: jm/rest-ccta
updated: 2026-10-30
issue: christianGRogers/Asclepius#142
---

# Round 1's four border-error curves differ because their distance maps move the border by different amounts

Round 1 ruling §6 item 2 asks for one shared perturbation harness that explains why the four simulations
disagree. At a nominal "0.5 mm" border error, the subendocardial-third Dice was:
- 0.909 (Golf);
- 0.927 (India);
- 0.939 (Kilo);
- 0.975 (Hotel).

This note also derives **E4**, the repeatability floor that Path A uses to calibrate its signs (Hotel v2 §4).

## What was run

All of it is synthetic. **No image of any kind was opened.** Script:
`experiments/JanusM/Hotel/r2/e2_harness.py`, which writes `e2_harness.json`; summaries are in `summary.json`.

- **The phantom.**
  - The LV is two truncated prolate ellipsoids: outer surface 34 × 34 × 60 mm, cavity 24 × 24 × 52 mm. The cavity
    is shifted 4 mm, so the wall runs from about 6 to 14 mm (median 10.5 mm).
  - Segments: 18 pseudo-segments (six 60° sectors × three levels). The open base rim, within 6 mm of the cut plane,
    is left out of every statistic.
- **The shared recipe**, found in all four Round 1 codes (code read by a helper agent and re-checked here):
  1. make a white-noise field, smooth it with a Gaussian, and rescale it to a nominal SD σ;
  2. add independent fields to the endocardial and epicardial signed distance maps (SDFs);
  3. threshold the result, and recompute the thirds.
- **Part A** replays the four SDF conventions on the same 1.5 mm masks:

  | Advocate | SDF convention |
  |---|---|
  | Golf | half-voxel offset at 1.5 mm, then linear zoom to 0.5 mm |
  | India | mask resampled to 0.5 mm, quarter-voxel offset |
  | Kilo | plain SDF at 1.5 mm, then zoom to 0.5 mm |
  | Hotel | mask resampled to 0.75 mm, plain SDF at 0.75 mm |

  Settings: σ 0.25 / 0.5 / 1.0 mm, 8 mm smoothing, 3 draws each. Every draw records the border movement it actually
  produced, mean |d| = changed volume ÷ border area.
- **Part B is the proposed harness.**
  - The phantom's *continuous* SDF (Sampson distance) on a native 0.5 mm grid, so sub-voxel shifts can be
    represented.
  - Independent endocardial and epicardial fields: σ 0.1–1.0 mm, smoothing 4 / 8 / 16 mm, 3 draws each.
  - Constant biases: ±0.25, ±0.5 and ±1.0 mm at the endocardium; ±0.25, ±0.5 and −0.86 mm at the epicardium (−0.86
    is TotalSegmentator v1's measured outward epicardial bias).
  - Thirds use equal-thickness depth (JA2).
  - STA: Kilo's idea, a fixed subendocardial scar of transmurality τ (0.15, 0.40, 0.65 or 0.90), placed on the true
    borders and re-read inside the perturbed wall; the result is the rate of Kim-bin flips.

## Results

### Part A: the four Round 1 conventions on one phantom (mean of 3 draws)

| Convention | σ 0.25: Dice / mean \|d\| (mm) | σ 0.5: Dice / mean \|d\| | σ 1.0: Dice / mean \|d\| |
|---|---|---|---|
| Golf | 0.950 / 0.126 | **0.900** / 0.287 | 0.802 / 0.560 |
| India | 0.991 / 0.029 | 0.916 / 0.191 | 0.805 / 0.512 |
| Kilo | 0.967 / 0.077 | 0.935 / 0.168 | 0.899 / 0.280 |
| Hotel | 1.000 / 0.000 | 0.990 / 0.030 | 0.900 / 0.264 |

- **"0.5 mm" moves the border by 0.03–0.29 mm, depending only on the convention.** The ordering of Round 1's
  Dice values is reproduced (Golf < India < Kilo < Hotel).
- **Golf's convention is the unbiased one.**
  - Its "0.5 mm" gives 0.900 here and 0.909 in Round 1.
  - Kilo's plain SDF zoomed from 1.5 mm has slope 2 near the border, so it halves every shift.
  - Hotel's plain SDF at 0.75 mm moves nothing until |noise| > 0.75 mm. **Hotel's Round 1 curve was the softest
    because Hotel's error model barely moved the border.** That retracts Hotel v1's "≤ 0.5 mm" bar, as the ruling
    already ruled.

### One line explains all of them

Across every Part A and Part B draw (4 conventions plus the harness), the fit is:

**subendocardial-third Dice ≈ 0.998 − 0.379 × mean |d| (mm)**, with R² = 0.95.

| Source | Mean residual |
|---|---|
| Golf | +0.009 |
| India | −0.008 |
| Kilo | −0.001 |
| Hotel | +0.006 |
| Harness | −0.001 |

**The disagreement is entirely in the x-axis**: what each model called "0.5 mm". So JA8's choice of ASSD, which is
the achieved displacement, rather than any curve's nominal σ, is the right one. Any future simulation should report
achieved displacement, never nominal σ.

### Part B: the harness at native 0.5 mm (8 mm smoothing, mean of 3 draws)

| σ (mm) | Achieved mean \|d\| endo | Subendo / mid / subepi Dice | Myo Dice | Segment-thickness \|error\| | SD of signed thickness error | Kim flips |
|---|---|---|---|---|---|---|
| 0.1 | 0.035 | 0.982 / 0.985 / 0.983 | 0.994 | 0.074 | 0.094 | 0.000 |
| 0.25 | 0.111 | 0.952 / 0.962 / 0.951 | 0.981 | 0.211 | 0.266 | 0.005 |
| 0.5 | 0.247 | 0.909 / 0.923 / 0.896 | 0.962 | 0.451 | 0.576 | 0.019 |
| 0.75 | 0.356 | 0.853 / 0.877 / 0.844 | 0.942 | 0.607 | 0.718 | 0.074 |
| 1.0 | 0.506 | 0.812 / 0.838 / 0.803 | 0.928 | 0.676 | 0.813 | 0.069 |

The 4 and 16 mm smoothing lengths are in `summary.json → E2_B_harness_0p5mm`.

**Smoothing length matters little.** At σ 0.5, subendocardial Dice is 0.896 / 0.909 / 0.914 at 4 / 8 / 16 mm.

**Constant biases:**

| Bias | Subendo Dice | Myo Dice | Segment-thickness \|error\| | Kim flips (τ 0.15 / 0.40 / 0.65 / 0.90) |
|---|---|---|---|---|
| Endocardium +0.25 mm (inward) | 0.931 | 0.990 | 0.239 | 0 / 0 / 0 / 0 |
| Endocardium −0.25 mm | 0.932 | 0.990 | 0.251 | 0 / 0 / 0 / 0 |
| Endocardium ±0.5 mm | 0.858–0.867 | 0.979–0.981 | 0.48–0.49 | ≤ 0.11 |
| Epicardium ±0.5 mm | 0.967–0.969 | 0.965 | 0.48–0.49 | ≤ 0.11 |
| **Epicardium −0.86 mm (TotalSegmentator v1)** | **0.948** | 0.942 | **0.858** | 0 / 0.11 / 0.22 / 0.22 |

- **Subendocardial Dice is nearly blind to epicardial bias.** An outward 0.86 mm epicardium still scores 0.948, but
  it puts every segment's thickness 0.86 mm too thick and flips up to 22 % of Kim bins. This is why JA8's signed-bias
  guards and thickness co-primary are needed.
- **The STA (Kim-flip) rate is coarse here.** There are only 9 evaluable pseudo-segments, so one flip is 0.11. Treat
  it as a direction, not a size.

## E4: the repeatability floor for Path A thresholds

Model a read as an independent perturbation of the true borders. Then:
- the difference between two reads of one segment's thickness has SD √2 × the single-read SD;
- the repeatability coefficient is RC = 1.96 × √2 × SD.

| Read-vs-read border noise σ | Single-read SD of segment thickness | **Repeatability coefficient** |
|---|---|---|
| 0.1 mm | 0.094 mm | 0.26 mm |
| 0.25 mm | 0.266 mm | **0.74 mm** |
| 0.5 mm | 0.576 mm | **1.60 mm** |
| 1.0 mm | 0.813 mm | 2.25 mm |

- **A thinning flag set closer to normal than RC flags noise.**
  - At σ 0.25, a 7 mm wall must read ≤ 6.26 mm before the change is real.
  - At σ 0.5, it must read ≤ 5.4 mm, which is at the CMR 5.5 mm cut.
- **The floor is a model figure until the first 20 decision double reads** (JA8) give the measured read-vs-read SD.
  Then RC is recomputed from them by the same formula, and every Path A threshold is checked against it (Hotel v2 §4).

## What it changes

1. **§6 item 2 is settled:** the four curves differ because the four distance maps move the border by 0.03–0.29 mm
   under the same "0.5 mm". One unbiased harness (Part B) replaces them. It reports achieved displacement, and STA is
   computed inside it.
2. **Hotel v1's "≤ 0.5 mm" bar is withdrawn.** Hotel's own error model was the softest. On the unbiased harness, an
   achieved 0.25 mm mean displacement already costs subendocardial Dice 0.91 and 0.45 mm of segment thickness.
3. **Path A's thresholds are bounded below by read noise** (E4). This is the core of the calibration plan without a
   scar reference.
