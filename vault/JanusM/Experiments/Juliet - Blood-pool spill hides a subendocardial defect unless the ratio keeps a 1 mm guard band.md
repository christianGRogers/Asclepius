---
tags: [janus-m, experiment, perfusion, ctp, tpr, phantom]
author: Juliet
round: 1
updated: 2026-10-30
---

# Blood-pool spill hides a subendocardial defect unless the ratio keeps a 1 mm guard band

## Question

Ischaemia on CT perfusion is read layer-wise. George 2009 defines the transmural perfusion ratio (TPR) as
subendocardial over subepicardial attenuation. Normal TPR is 1.12 ± 0.13, abnormal is < 0.99, and territories behind
70–100 % stenoses read 0.91 ± 0.10 ([10.1161/CIRCIMAGING.108.813766](https://doi.org/10.1161/CIRCIMAGING.108.813766);
Results, Fig. 3, Discussion). The < 0.99 cut-off was derived on the same 40 patients, as the authors note.

If Janus-M computes a TPR from its own borders, how much do the scanner's blur and partial volume bias it? The bias
comes from the bright blood pool on one side and epicardial fat on the other. Does a guard band fix it?

## Method

Synthetic only. `experiments/JanusM/Juliet/phantom.py` (E2), `results.json` → `E2`.

- **Image.** Same phantom as [[Juliet - Computed transmural thirds are only as good as the borders, at any CT voxel size]].
  Static stress-perfusion-like values:
  - blood pool 400 HU;
  - myocardium 110 HU;
  - a 3 mm epicardial fat ring at −90 HU;
  - 30 HU outside;
  - an **ischaemic sector** (normal 10 mm wall, 120–180°) whose inner half is 80 HU, so its true TPR is
    80/110 = 0.727.
- **Blur and noise.** Gaussian point-spread function, FWHM f ∈ {0, 0.6, 0.8, 1.0, 1.5} mm, on an 8× supersampled
  grid, then block-averaged to 0.5 mm voxels. White noise SD 25 HU, 20 seeds.
- **Borders.** Exact, to isolate the spill. Border error adds to it; see the E1 note.
- **TPR.** Mean of the sub-endo third over the sub-epi third, per sector, after removing a guard band g ∈
  {0, 0.5, 1.0} mm from the endocardial edge of the sub-endo third and the epicardial edge of the sub-epi third.
  Sectors: normal 10 mm wall (240–300°), ischaemic (130–170°), normal thinned 5 mm wall (15–45°).
- **Which f is realistic.** Atlas measured no image signal above about 1 cycle/mm in ImageCAS CT
  ([[Atlas - Resampling to 0.5 mm isotropic loses nothing measurable, 0.7-0.8 mm does]], in `vault/Plans/Experiments/`).
  A Gaussian PSF whose MTF falls to 2–10 % at 1 cycle/mm has FWHM 0.8–1.05 mm (my arithmetic from that measurement,
  not a published value). I found no citable PSF for the smooth cardiac kernels. Rajendran 2022 gives only
  sharp-kernel limiting values, 0.21–0.28 mm ([10.1148/radiol.212579](https://doi.org/10.1148/radiol.212579)).

## Result

TPR, mean ± SD over 20 noise seeds; true values 1.000 (normal) and 0.727 (ischaemic).

| PSF FWHM | Guard | Normal 10 mm | Ischaemic | Normal thinned 5 mm |
|---|---|---|---|---|
| 0 | 0 | 1.07 ± 0.02 | 0.79 ± 0.02 | 1.15 ± 0.02 |
| 0.8 mm | 0 | **1.20** ± 0.02 | **0.91** ± 0.02 | **1.46** ± 0.03 |
| 1.0 mm | 0 | **1.25** ± 0.02 | **0.96** ± 0.02 | **1.59** ± 0.03 |
| 1.5 mm | 0 | 1.39 | 1.09 | 1.98 |
| 0.8 mm | 0.5 mm | 1.02 | 0.75 | 1.06 |
| 1.0 mm | 0.5 mm | 1.05 | 0.77 | 1.13 |
| 0.8 mm | **1.0 mm** | **1.00** ± 0.02 | **0.73** ± 0.02 | **1.03** ± 0.05 |
| 1.0 mm | **1.0 mm** | **1.01** ± 0.02 | **0.73** ± 0.02 | **1.04** ± 0.05 |
| 1.5 mm | 1.0 mm | 1.04 | 0.76 | 1.15 ± 0.05 |

Without a guard, the normal-minus-ischaemic difference survives (0.28–0.30). Its **absolute level drifts up by
0.2–0.4**, and **twice as much in a thinned wall**. At f = 1.0 mm a true TPR of 0.73 reads 0.96, just under George's
0.99 cut-off. A normal thinned wall reads 1.59. With a 1 mm guard the bias falls to ≤ 0.04 at f ≤ 1.0 mm. The cost is
voxels: the thinned-wall sub-endo sample drops from 87 to 35 per sector-slice, and the SD rises from 0.03 to 0.05.

## What it changes

1. **A layer-wise perfusion output needs the guard band in its definition.** Janus-M's TPR is computed on the
   computed thirds minus 1 mm on the blood-pool and fat sides. The guard is pre-registered, not tuned on outcome data.
2. **Published TPR cut-offs do not transfer to a different border definition.** Part of George's normal TPR of 1.12
   may itself be spill, though subendocardial physiology also plays a part, and this experiment cannot separate
   them. Thresholds for Janus-M's own TPR must be re-derived on its own outputs against a reference (SPECT, CMR
   perfusion or invasive FFR). No public CT perfusion dataset with such a reference exists (Juliet v1 §4).
3. **Thinned walls are where spill is worst and samples are fewest.** Report TPR only where the wall is ≥ 3 mm
   thicker than the two guards (≥ 5 mm). Below that, report thinning and LIE instead.
4. **Limits.** 2-D phantom, static image, no beam-hardening. Beam hardening is a separate, known artefact in CT
   perfusion; correction moved a canine MBF correlation from 0.60 to 0.74, Kitagawa 2010,
   [10.1148/radiol.10091399](https://doi.org/10.1148/radiol.10091399), abstract. The PSF value is inferred, not
   measured. Round 2 can measure an edge-spread function across the septum on ImageCAS cases (Job M0's cases) to
   replace the inference.
