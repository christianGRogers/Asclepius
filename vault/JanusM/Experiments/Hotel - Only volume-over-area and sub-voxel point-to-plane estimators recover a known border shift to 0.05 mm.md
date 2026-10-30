---
tags: [janus-m, experiment, measurement, ASSD, signed-bias, JA15, JA16, fixture, path-rest-ccta]
author: Hotel
round: 3
path: jm/rest-ccta
updated: 2026-10-30
issue: christianGRogers/Asclepius#167
---

# Only volume-over-area and sub-voxel point-to-plane estimators recover a known border shift to 0.05 mm

Round 2 ruling §7 item 2 (JA15, JA16) asks two things:
- validate the ASSD, signed-bias and thickness implementations that become the geometry module's single fixture
  (#170);
- decide whether a bias estimator recovers a known ±0.5 mm shift to within ±0.05 mm, which sets the JA16 guard at
  0.3 mm rather than 0.5 mm.

## What was run

The test is synthetic: **no case was opened**. Script: `experiments/JanusM/Hotel/r3/e6_estimators.py`. Results:
`e6_estimators.json` (336 conditions, 69 CPU-min). Summary: `summarise_e6.py` → `e6_summary.json`.

**The phantom and the conditions:**
- **Phantom:** an analytic LV with known continuous signed distances: two truncated ellipsoids, with the cavity
  off-centre so the wall runs about 6–14 mm. Statistics leave out everything within 6 mm of the valve (cut) plane,
  which is not a border.
- **Grids:** native 0.5 mm isotropic, and ImageCAS-like 0.4 × 0.4 × 0.5 mm.
- **Orientations:** axis-aligned, plus two random rotations, so the walls are oblique to the grid.
- **Walls:** smooth, or rough (0.6 mm-SD bumps at 3 mm correlation added to both signed distances).
- **Perturbations, per border:**
  - constant shifts of ±0.1, ±0.25, ±0.3, ±0.5 and ±1.0 mm;
  - JA15 random fields (8 mm correlation, σ 0.25 and 0.5 mm, 2 draws each).

**Truth.** The true normal displacement is s(x) ÷ |∇F| at each reference-surface point. It is exact for a constant
shift and first-order for a smooth field. Its mean over the surface is the true signed bias, and its mean absolute
value the true ASSD.

**Estimators** (+ = the perturbed region is larger):

| Name | What | Origin |
|---|---|---|
| india | `experiments/JanusM/India/harness_r2.border_stats`, **imported unchanged** | India R2 |
| lima | `experiments/JanusM/Lima/harness.assd_and_bias`, **imported unchanged** | Lima R2 |
| sym | ½ [mean SDF_B over A's surface voxels − mean SDF_A over B's], with half-voxel-corrected SDFs | Hotel |
| **pp** | Sub-voxel point-to-plane, both ways. Each mask is lightly smoothed (Gaussian 0.7 voxel). Its 0.5 crossings along each grid axis are interpolated and kept on their dominant axis, each weighted by the area it stands for. Each point of one surface is matched to the nearest point of the other, and the distance is measured along that point's normal. Bias is the signed mean, averaged over both directions; ASSD is the area-weighted mean of the absolute values | Hotel |
| **vol** | (Volume of A − volume of B) ÷ mean border area, both inside the ROI. Area = ∫ \|∇(G₀.₇ * mask)\| | Hotel |
| voxel ASSD | `segtrain.metrics.surface_distances`, which is what `janusm_reads.anchoring.assd` ships | shipping code |
| sdf ASSD | Mean of \|SDF_other + h/2\| over each surface's voxels | Hotel |
| thickness | `janusm.geometry.depth` (equal thickness) on the label map; median over 16 pseudo-segments of each segment's median thickness; the true change for an endocardial shift s is −s | shipping code |

**The pass rule was fixed in `summarise_e6.py` before the full run was read:** |error| ≤ 0.05 mm for +0.5 and for
−0.5 mm, on both borders, both grids, all orientations and both wall types (24 conditions per direction).

## Results

**Signed bias.** Errors are estimate − truth, in mm.

| Estimator | +0.5 mm: mean / worst | −0.5 mm: mean / worst | Worst over 0.1–1.0 mm | Random fields: mean / worst | **Meets JA16?** |
|---|---|---|---|---|---|
| india | −0.116 / 0.129 | −0.014 / 0.045 | 0.150 | −0.052 / 0.106 | **no** |
| lima | +0.017 / 0.050 | +0.123 / 0.137 | 0.196 | +0.054 / 0.106 | **no** |
| sym | −0.048 / 0.067 | +0.055 / 0.079 | 0.141 | +0.002 / 0.034 | **no** |
| **pp** | −0.016 / 0.025 | +0.025 / 0.032 | 0.067 | +0.003 / 0.032 | **yes** |
| **vol** | −0.004 / 0.012 | +0.013 / **0.019** | 0.054 (at 1.0 mm) | +0.004 / 0.033 | **yes** |

**What the failures show:**
- **India's estimator under-reads outward shifts** by 0.12 mm, as the Round 2 judge found and India disclosed.
- **Lima's under-reads inward shifts** by the same amount. They are mirror images: each samples one mask's surface
  voxels in the other's distance map, with a half-voxel correction that holds only on axis-aligned walls.
- **Averaging the two directions (sym)** removes the asymmetry, but leaves a 10 % shrinkage that grows on the
  anisotropic grid (worst 0.079).
- **Only the two sub-voxel estimators pass.** vol is the more accurate (worst 0.019 at ±0.5). Rough walls cost it
  0.007 mm (0.012 → 0.019); pp goes from 0.025 to 0.032.

**ASSD.** Errors by true displacement, mean / worst:

| True displacement (mm) | 0.1 | 0.25 | 0.3 | 0.5 | 1.0 |
|---|---|---|---|---|---|
| voxel (shipping) | +0.014 / 0.023 | **+0.038 / 0.057** | **+0.045 / 0.065** | +0.014 / 0.049 | −0.057 / 0.099 |
| **pp** | −0.003 / 0.006 | −0.010 / 0.016 | −0.012 / 0.019 | −0.020 / 0.032 | −0.029 / 0.067 |
| sdf | | | | | mean −0.041, worst 0.139 overall |

- **The shipping voxel ASSD over-reads by about 0.04 mm right where JA8's margin sits** (0.25–0.3 mm), and
  under-reads at 1 mm. Its error is non-monotone, because surface-voxel to surface-voxel distances come in steps.
- In JA8's d = (model-vs-read) − (read-vs-read), a *constant* offset would cancel. An offset that depends on the
  displacement does not, so d is distorted by up to 0.04 mm against a 0.25 mm margin.
- **pp ASSD is within 0.02 mm up to 0.5 mm.**

**Thickness** (`janusm.geometry.depth`, median over segments): it reads a 0.25 mm endocardial shift as 0.235–0.237
(worst error 0.032), and 0.5 mm as 0.468–0.474 (worst 0.057). So it shrinks changes by about 6 %.
- That is acceptable for JA8's co-primary (thickness error ≤ read-vs-read + 0.5 mm), and for Table A.
- It is the reason the signed-bias guard should not be read off a thickness difference.

## What it changes

1. **JA16's guard becomes |signed bias| ≤ 0.3 mm**, measured with **vol** (worst 0.019 mm at ±0.5 mm across every
   condition). pp is kept as an independent check: if vol and pp disagree by more than 0.05 mm on a case, the case
   is listed for inspection.
2. **#170's fixture exposes one implementation of each:**
   - **signed bias = vol**;
   - **ASSD = pp**, for JA8 scoring, both terms of d;
   - **thickness = `janusm.geometry.depth`**, median over segments 1–16.

   The fixture's tests are E6's conditions, with tolerances: 0.05 mm for bias at ±0.5 mm; 0.03 mm for ASSD up to
   0.5 mm; 0.06 mm for the thickness change at 0.5 mm.
3. **The read queue's anchoring may keep the voxel ASSD.** It compares reads with reads, where a common offset
   matters less, and its 0.2 mm anchoring margin is far above the offset. **JA8 scoring must not mix
   implementations.**
4. **The ROI must come from the reference alone.** On real cases, vol and pp are taken inside a band around the
   reference read's border, minus the valve band (≤ 3 mm from LA or aorta, as in the geometry module). Basal-limit
   disagreements are then never counted as border bias. The read protocol's mitral-plane check (Hotel v3 §5) keeps
   that band small.

**Limits.**
- An analytic phantom is not a reader's mask. Real read pairs carry staircase roughness and topology differences
  (papillary muscles attached or not) that this phantom does not.
- **The first real check uses the first 20 decision double reads.** On each read pair, and on each seed-vs-read
  pair, vol and pp are computed side by side. The two estimators are independent, and they agree to within 0.03 mm
  on the phantom.
  - If their median absolute disagreement on real pairs exceeds **0.05 mm**, the phantom validation does not
    transfer, and the guard returns to 0.5 mm (Hotel v3 §10).
  - Read-to-read bias itself is not expected to be zero: readers differ.
