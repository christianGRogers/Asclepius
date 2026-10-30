---
tags: [janus-m, experiment, depth, laplace, yezzi-prince, layers, path-rest-ccta]
author: Hotel
round: 2
path: jm/rest-ccta
updated: 2026-10-30
issue: christianGRogers/Asclepius#142
---

# Equal-thickness thirds match Yezzi–Prince on 98 percent of a phantom wall, raw Laplace isolines on 86 percent

Round 1 ruling §6 item 3, first part: equal-thickness against Yezzi–Prince depth at 0.5 mm.

## What was run

The test is synthetic: no image was opened. Script: `experiments/JanusM/Hotel/r2/e5_depth.py`, which writes
`e5_depth.json`.

**Two phantoms.** Both use E2's continuous phantom voxelised at 0.5 mm, with the base rim excluded:
- the E2 phantom itself, with walls of about 6–14 mm;
- a thinned variant, in which the cavity is moved 2 mm so that the lateral wall is about 4–5 mm.

**Three depth definitions:**
- **Equal thickness (JA2).** u = d_endo / (d_endo + d_epi), where each distance is Euclidean distance to the nearest
  border.
- **Raw Laplace.** u is the harmonic potential, 0 at the cavity and 1 outside. The thirds are cut at its isolines
  1/3 and 2/3. This is what Hotel v1 and Kilo v1 used.
- **Yezzi–Prince (2003).**
  - L0 and L1 are the lengths of the streamline of ∇u / |∇u| from a voxel to the endocardium and to the epicardium.
  - Depth is L0 / (L0 + L1), and thickness is L0 + L1.
  - The streamlines were traced directly (RK2, 0.1 mm steps) from 20,000 random myocardial voxels per phantom. All
    reached both borders.
  - An upwind fixed-point solver was tried first. It diverged where neighbouring streamlines point at each other, so
    it was replaced by tracing. Tracing is what the Yezzi–Prince PDE computes everywhere.

## Results

| Agreement of thirds (same voxels) | Phantom | Thinned |
|---|---|---|
| Equal thickness vs Yezzi–Prince | **0.985** | **0.981** |
| … in walls < 7 mm | 0.980 | 0.962 |
| … in walls > 12 mm | 0.991 | 0.987 |
| Equal thickness vs raw Laplace | 0.862 | 0.841 |
| Raw Laplace vs Yezzi–Prince | 0.860 | 0.836 |

| Volume share of the inner / mid / outer third | Equal thickness | Yezzi–Prince | Raw Laplace |
|---|---|---|---|
| Phantom | 26 / 35 / 39 % | 27 / 34 / 39 % | 20 / 32 / 47 % |
| Thinned | 25 / 35 / 40 % | 26 / 34 / 40 % | 19 / 31 / 49 % |

Median thickness, equal thickness vs Yezzi–Prince:
- 10.52 vs 10.50 mm overall;
- 6.27 vs 6.10 mm in walls < 7 mm;
- 5.22 vs 5.10 mm in the thinned lateral wall.

What this shows:
- **Equal thickness is Yezzi–Prince to within 2 % of voxels and about 0.1–0.2 mm of thickness.** The thin wall is
  where they part most.
- **Raw Laplace isolines are the outlier.** They shrink the inner third to about 20 % of the wall's volume and swell
  the outer third to about 48 %. A subendocardial third cut on raw Laplace is therefore thinner than the clinical
  "one third of the thickness".
  - Hotel v1 used raw Laplace; JA2 already moved to equal thickness.
  - Golf's and India's Round 1 figure of 88 % agreement with raw Laplace at 1.5 mm is the same effect.

**Limits.** The phantom is smooth: there are no trabeculae (JA1 puts them in the pool) and no papillary insertions.
Real walls may separate the definitions more. `geometry_m0.py` on Fir could report the same agreement on JM-0 cases
if the shared geometry module (#139) gains a Yezzi–Prince option. Hotel does not ask for that now.

## What it changes

- **Equal thickness stays the primary depth (JA2), and Yezzi–Prince adds nothing worth its cost.** The two agree on
  98 % of voxels.
- **Raw Laplace isolines should not be used for thirds in any reported output.** The Laplace potential is still
  useful as the field whose streamlines define Yezzi–Prince, but its isolines are not thirds.
- **§6 item 3's other two parts** need real anatomy and are carried to Job JM-0's output (Hotel v2 §5.3):
  - fixed vs arc-proportional septal sectors;
  - Euclidean vs geodesic territories.
