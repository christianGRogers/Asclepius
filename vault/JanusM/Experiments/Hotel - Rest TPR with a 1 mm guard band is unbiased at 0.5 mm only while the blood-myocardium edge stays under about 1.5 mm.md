---
tags: [janus-m, experiment, TPR, partial-volume, guard-band, rest-ccta, path-rest-ccta]
author: Hotel
round: 2
path: jm/rest-ccta
updated: 2026-10-30
issue: christianGRogers/Asclepius#142
---

# Rest TPR with a 1 mm guard band is unbiased at 0.5 mm only while the blood-myocardium edge stays under about 1.5 mm

Round 1 ruling §2.6 / §6 item 6: rest TPR may be reported per segment only if Round 2 shows, at native 0.5 mm with
Juliet's 1 mm guard band, a normal-heart ratio near the published 1.06–1.12. This note predicts when that can
happen. The measurement itself needs native ImageCAS, which is on Fir, so it is a CPU add-on to Job JM-0
(Hotel v2 §7).

## What was run

Everything is synthetic; no image was opened.

- **The model.** `experiments/JanusM/Hotel/r2/e3_tpr.py` (writes `e3_tpr.json`) is a 1-D wall along its normal:
  - LV blood at 450 HU;
  - myocardium of thickness T (6, 8, 10 or 12 mm), with a linear transmural gradient set so that
    mean(inner third) / mean(outer third) equals the true TPR (1.10, 1.00 or 0.85), and an outer third at 100 HU;
  - then epicardial fat at −80 HU (free wall), or RV blood at 350 HU (septum).
- **The imaging.** The profile is blurred by a Gaussian point spread, set by its **10–90 % edge width** (0–4.7 mm),
  and averaged into 0.5 or 1.5 mm voxels at 16 grid phases.
- **The read.** It follows JA2: equal-thickness thirds between the *estimated* borders. The true borders are moved by
  0 or ±0.5 mm at either border. Each third is trimmed by a guard band of 0, 0.5, 1.0 or 1.5 mm from its own border.
- **Why the edge width.** It can be measured on every scan. Hotel R1 E1 measured 4.7 mm at the endocardium on 1.5 mm
  TotalSegmentator CT. The Fir add-on `r2/fir/halfmax_tpr_m0.py` measures it on native ImageCAS.
- **3-D check.** The add-on was run on a synthetic 0.4 mm heart: uniform myocardium (true TPR 1.00), 1.0 mm FWHM
  blur, 20 HU noise.
  - Unbiased labels gave half-maximum offsets of +0.005 mm (endocardium) and +0.003 mm (epicardium), and a 0.95 mm
    10–90 % edge.
  - Labels grown outward by two voxels read +0.64 mm at the epicardium.
  - TPR read **1.003** with the 1 mm guard and **1.29** without.

    The 1-D model predicts 1.00 and 1.23–1.34 for that blur, so the two agree.
  - A sealed case id (`c0002`) stopped the run before any image was opened.

## Results

**Free wall, T = 10 mm, no border error, 0.5 mm voxels.** Each cell is the read TPR for true TPRs 1.10 / 1.00 /
0.85.

| 10–90 % edge (mm) | No guard | **1 mm guard** |
|---|---|---|
| 0 (ideal) | 1.20 / 1.10 / 0.95 | 1.08 / 1.00 / 0.87 |
| 0.8 | 1.33 / 1.23 / 1.08 | **1.08 / 1.00 / 0.87** |
| 1.2 | 1.44 / 1.34 / 1.19 | **1.09 / 1.01 / 0.88** |
| 1.6 | 1.57 / 1.47 / 1.32 | 1.12 / 1.04 / 0.91 |
| 2.4 | 1.85 / 1.75 / 1.60 | 1.25 / 1.17 / **1.04** |
| 3.2 | 2.18 / 2.09 / 1.95 | 1.47 / 1.39 / 1.27 |
| 4.7 (Hotel R1, 1.5 mm CT) | 2.89 / 2.82 / 2.71 | 2.00 / 1.94 / 1.84 |

- **Without a guard band, rest TPR is partial volume at any realistic blur.** Even an ideal edge reads +0.10, because
  the boundary voxel itself is half blood.
- **With a 1 mm guard band**, the read stays within 0.01 of truth up to a 1.2 mm edge, and within 0.04 at 1.6 mm.
  - The guard-band read of a true 1.10 is 1.08–1.09, because trimming the innermost 1 mm removes the steepest part
    of a linear gradient. A guarded TPR is therefore slightly different from George 2009's untrimmed layers, and its
    normal range must be measured, not borrowed.
- **At a 2.4 mm edge a true defect (0.85) reads 1.04,** above a true normal wall (1.00 reads 1.17, 1.10 reads 1.25).
  At that blur, per-segment TPR would put defects in the normal range.
- **Voxel size matters much less than blur.** At a 1.2 mm edge with a 1 mm guard, 1.5 mm voxels read
  1.11 / 1.03 / 0.90, which is +0.02 over 0.5 mm voxels. The blur (the edge width) is what drives the error. Hotel's
  Round 1 numbers on 1.5 mm CT (2.25) were far off because those resampled images have a 4.7 mm edge, not because of
  the voxel size alone.
- **The septum, with RV blood outside, behaves like the free wall** with the guard: 1.09 / 1.00 / 0.87 at a 1.2 mm
  edge.

**Border error, true TPR 1.10, 1.2 mm edge, 1 mm guard, 0.5 mm voxels:**

| Wall | No error | Endocardium 0.5 mm into wall | Endocardium 0.5 mm into blood | Epicardium 0.5 mm into fat | Epicardium 0.5 mm into wall |
|---|---|---|---|---|---|
| 6 mm | 1.09 | 1.07 | **1.20** | 1.15 | 1.08 |
| 10 mm | 1.09 | 1.08 | 1.15 | 1.12 | 1.08 |
| 12 mm | 1.09 | 1.09 | 1.14 | 1.12 | 1.09 |

- **An endocardium drawn into the blood is the dangerous error.** At 0.5 mm it adds +0.05 to +0.11, about the whole
  published normal SD (George 2009: 1.12 ± 0.13).
- **An epicardium drawn into the fat** adds +0.03 to +0.06. TotalSegmentator v1's +0.86 mm outward epicardium would
  add more.

## What it changes

**The ruling's condition becomes a measurable rule.** Per-segment rest TPR is reported only if all of these hold on
Job JM-0's 40 ImageCAS-X cases:

1. **Edge width.** The median endocardial 10–90 % edge width is ≤ 1.5 mm.
2. **Endocardial bias.** The `heartchambers_highres` endocardial half-maximum offset satisfies |offset| ≤ 0.25 mm,
   or the borders are snapped to half-maximum first (Hotel v2 §5.4).
3. **The ratio itself.** The guarded free-wall TPR median is 1.06–1.12, read off the add-on's output.

Otherwise:
- rest TPR stays per-territory and report-only;
- if the edge exceeds 2 mm, it is dropped from the table.

Nothing here needs a scar reference.
