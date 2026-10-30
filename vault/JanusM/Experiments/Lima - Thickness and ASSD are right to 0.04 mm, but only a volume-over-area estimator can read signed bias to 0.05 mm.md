---
tags: [janus-m, experiment, round3, rest-ccta, harness, assd, bias, ja15, ja16]
author: Lima
round: 3
path: jm/rest-ccta
updated: 2026-10-30
issue: christianGRogers/Asclepius#167
---

# Lima E4: thickness and ASSD are right to 0.04 mm, but only a volume-over-area estimator can read signed bias to 0.05 mm

**Question (Round 2 ruling §7 item 2).** Do the JA15 harness's ASSD, signed-bias and thickness implementations measure
what they claim? Does a signed-bias estimator meet JA16's test, "recover a known 0.5 mm shift, in each direction, to
within ±0.05 mm"? The answer decides whether the bias guard is 0.3 or 0.5 mm.

**Setup** (`experiments/JanusM/Lima/r3/e4_estimators.py`, results in `e4.json`).
- **A. Analytic shells: exact truth.**
  - Spheres of radius 12 and 20 mm, with 6 and 9 mm walls, on a 0.5 mm grid. The centre is jittered by a random
    sub-voxel offset (6 draws per size).
  - The perturbed border is the **exact** sphere of radius R + d, for d ∈ ±{0.1, 0.3, 0.5, 1.0} mm, endocardium and
    epicardium: 192 configurations.
  - Truth: signed bias = d; thickness change = −d (endocardium outward) or +d (epicardium outward).
- **B. Real walls, shifted the JA15 way.** The 23 guard-allowed public walls (`janusm.guard.refuse` called on the list
  and on each case). Each border is moved by the harness's rule, S_ref − d < 0 on the half-voxel-corrected signed
  distance, for d ∈ ±{0.3, 0.5} mm.
- **Implementations tested:**
  - ASSD: `segtrain.metrics.surface_distances`, the read queue's `janusm_reads.anchoring.assd`, which is also the
    harness's definition;
  - thickness: the harness's equal-thickness median;
  - five signed-bias estimators (+ = outward):
    - `inner_boundary` (Lima R2): mean reference signed distance at the perturbed mask's inner-boundary voxels, + h/2;
    - `face_midpoint`: mean reference signed distance at every inside/outside face of the perturbed mask;
    - `volume_area`: ΔV ÷ marching-cubes area of the binary reference mask;
    - `two_way`: half the difference of the mean signed surface distances in each direction;
    - `volume_midarea` (Lima R3): ΔV ÷ the mean of the two borders' areas, each measured by marching cubes
      (Lorensen & Cline 1987) on the signed distance smoothed by 0.5 mm.

**Result 1: thickness is exact; ASSD reads slightly high on exact shifts** (analytic, 12 shells per row):

| True shift | ASSD (median) | Thickness change (true) |
|---|---|---|
| ±0.1 mm | 0.12 | ±0.10 (within 0.006) |
| ±0.3 mm | 0.36 | ±0.30 (within 0.002) |
| ±0.5 mm | 0.54 | ±0.50 (within 0.006) |
| ±1.0 mm | 0.96 | ±1.00 (within 0.014) |

The voxel-surface ASSD is +0.02 to +0.06 mm off below 1 mm and −0.04 mm at 1 mm. This is the voxel-centre surface
definition, so it is a property of the unit, not a bug. In JA8's d = model-vs-read − read-vs-read, it largely cancels.

**Result 2: signed-bias error (estimate − truth), median and worst over 12 shells** (analytic, both borders alike):

| True shift | inner_boundary | face_midpoint | volume_area | two_way | **volume_midarea** |
|---|---|---|---|---|---|
| −0.5 mm | +0.13 / 0.13 | +0.06 / 0.06 | +0.05 / 0.06 | −0.04 / 0.04 | **−0.001 / 0.003** |
| −0.3 mm | +0.11 / 0.12 | +0.02 / 0.02 | +0.03 / 0.03 | −0.06 / 0.06 | **0.000 / 0.003** |
| +0.3 mm | +0.06 / 0.07 | −0.01 / 0.01 | −0.02 / 0.02 | +0.06 / 0.06 | **0.000 / 0.005** |
| +0.5 mm | +0.04 / 0.05 | −0.05 / 0.05 | −0.03 / 0.03 | +0.04 / 0.04 | **−0.001 / 0.004** |
| ±1.0 mm | up to +0.15 | up to −0.10 | up to +0.14 | ±0.04 | **≤ 0.004** |

- **Lima R2's estimator fails JA16:** it is +0.13 mm on a 0.5 mm inward shift, and it is the one used in Round 2's E2.
- **`volume_midarea` is exact to ±0.005 mm** at every shift and both borders.
- `two_way` passes at ±0.5 mm but not at ±0.3 mm (±0.06).
- The binary-mask area has to be smoothed first. Marching cubes on a voxel mask, or on its unsmoothed signed
  distance, reads the area of an exact sphere 8.8 % high (the staircase). Smoothing the signed distance by 0.5 mm
  brings it within 0.3 %.

**Result 3: the JA15 harness's "known" shift is not the shift it makes.** On exact spheres, the harness's rule
S_ref − d < 0 realises:

| Nominal shift | Realised (`volume_midarea`, exact on spheres) | Voxel ASSD |
|---|---|---|
| 0.3 mm | **0.41–0.42 mm** | 0.50 |
| 0.5 mm | **0.64–0.65 mm** | 0.61 |

On the 23 real walls the same rule realises 0.40–0.42 and 0.64–0.65 mm (`volume_midarea`), within 0.017 mm of the
spheres. Thickness changes by 0.37–0.39 and 0.58–0.62 mm. The cause is that the corrected signed distance takes
coarse values near the border:
- an outside face neighbour sits at 0.25 mm;
- an outside diagonal neighbour sits at 0.46 mm.

So "< 0.5" also takes in every diagonal neighbour.
- **Every estimator therefore "fails" on the real walls against the nominal d**, including the exact one, by
  +0.08 to +0.20 mm. That is a property of the test, not of the estimators.
- **This also explains Round 2's numbers.** The judge found that Lima's "0.5 mm" bias rows realised 0.54–0.63 mm
  ASSD, with about 1 mm of thickness error per mm of realised bias. That is consistent: the rows realised about
  0.64 mm.

**What it changes.**
1. **The estimator for JA16's guard is `volume_midarea`.** It recovers exact 0.3, 0.5 and 1.0 mm shifts, in both
   directions and on both borders, to ±0.005 mm, which is 10 times inside ±0.05 mm. On the real walls it agrees with
   the shift the harness rule realises on spheres to within 0.017 mm. **JA16's condition is met, so the bias guard is
   0.3 mm.** For a whole border it is a mean normal displacement, which is what a bias guard means. Regional bias
   stays the job of the read check's octants and of ASSD.
2. **JA16's test should be stated against an exact shift.** The JA15 fixture (#170) must generate known shifts
   analytically, or report the realised shift, never S − d with d taken as the truth. The nominal-to-realised ratio
   of the SDF rule (≈ 1.3 at 0.5 mm on a 0.5 mm grid) is recorded so that later harness results can be read.
3. **The fixture's tolerances**, measured here on exact spheres (radius 12–20 mm, 0.5 mm grid):
   - thickness change within ±0.02 mm of truth up to |d| = 1 mm;
   - voxel ASSD 0.54 ± 0.01 mm at |d| = 0.5 and 0.36 ± 0.01 mm at |d| = 0.3;
   - signed bias (`volume_midarea`) within ±0.01 mm of d up to |d| = 1 mm.

**Limits.**
- Spheres are convex and uniformly curved. The real walls test only agreement with the sphere-realised shift, not an
  independent truth.
- The estimator measures a whole-border mean. Equal and opposite regional biases cancel in it.
