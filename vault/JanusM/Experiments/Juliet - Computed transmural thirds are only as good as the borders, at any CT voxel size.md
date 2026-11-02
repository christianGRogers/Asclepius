---
tags: [janus-m, experiment, layers, phantom, transmural]
author: Juliet
round: 1
updated: 2026-10-30
---

# Computed transmural thirds are only as good as the borders, at any CT voxel size

## Question

Juliet v1 proposes that Janus-M learns **borders** (LV cavity, LV myocardium, RV cavity, LA) and **computes** the
layers (subendocardial, mid-wall, subepicardial thirds) from them, rather than learning layer classes. If so:
1. Is the CT voxel size a limit on computed thirds, in normal (10 mm) and thinned (5 mm) walls?
2. How fast does a border error degrade them?
3. Does the depth definition matter (Laplace potential vs equal-thickness distance ratio)?

## Method

Synthetic only; no patient data. `experiments/JanusM/Juliet/phantom.py` (E1), results in `results.json` → `E1`.

- **Phantom.** 2-D short-axis LV: endocardial radius 25 mm, wall 10 mm, a 60° sector thinned to 5 mm (15° cosine
  taper; the infarct-thinning cut-off is ≤ 5.5 mm, Shah 2013,
  [10.1001/jama.2013.1381](https://doi.org/10.1001/jama.2013.1381), abstract).
- **Masks.** Each border is perturbed by a smooth random radial error, RMS ε ∈ {0, 0.25, 0.5, 1.0} mm, with a
  correlation length of about 10°. The error is drawn independently for endo and epi. Masks are voxelised by area
  fraction ≥ 0.5 on an 8× supersampled grid, at voxel v ∈ {0.25, 0.4, 0.75, 1.5} mm. Each condition uses 12 seeds.
- **Computed layers.** Depth = d_endo / (d_endo + d_epi), the Euclidean distance to the cavity over the distance to
  the outside. Thirds are depth cuts at 1/3 and 2/3. For comparison, the Laplace potential u (0 at the cavity, 1
  outside; Jones 2000,
  [10.1002/1097-0193(200009)11:1<12::AID-HBM20>3.0.CO;2-K](https://doi.org/10.1002/1097-0193(200009)11:1%3C12::AID-HBM20%3E3.0.CO;2-K))
  is cut the same way.
- **Truth.** Thirds of the true radial depth at each voxel centre.
- **Metrics.** Dice per third in the thinned sector (15–45°) and in a normal sector (120–300°); myocardium Dice;
  median thickness error at mid-wall.

## Result

Dice of computed thirds (mean of 12 seeds; SDs ≤ 0.03 except where noted). Voxel size barely matters; border error
dominates.

| Voxel | Border RMS | Myo Dice | Sub-endo thin / normal | Mid thin / normal | Sub-epi thin / normal | Thickness error thin / normal (mm) |
|---|---|---|---|---|---|---|
| 0.4 mm | 0 | 0.998 | 0.97 / 0.99 | 0.95 / 0.99 | 0.98 / 0.99 | −0.19 / −0.25 |
| 0.4 mm | 0.25 mm | 0.977 | 0.89 / 0.95 | 0.90 / 0.95 | 0.89 / 0.95 | −0.15 / −0.28 |
| 0.4 mm | **0.5 mm** | 0.955 | **0.76 / 0.90** | 0.79 / 0.91 | 0.80 / 0.90 | −0.09 / −0.17 |
| 0.4 mm | 1.0 mm | 0.911 | 0.51 / 0.80 | 0.64 / 0.81 | 0.69 / 0.77 | −0.19 / −0.36 |
| 0.25 / 0.75 / 1.5 mm | 0.5 mm | 0.956 / 0.955 / 0.955 | 0.77 / 0.75 / 0.78 (thin) | 0.80 / 0.78 / 0.79 | 0.80 / 0.78 / 0.79 | 0.00 / −0.17 / −0.28 (thin) |
| 1.5 mm | 0 | 0.999 | 1.00 / 0.99 | 0.95 / 0.97 | 0.95 / 0.97 | −0.50 / −0.68 |

**Laplace vs distance ratio.** The plain Laplace potential is not an equal-thickness depth. In an annulus it is
logarithmic, so its 1/3 cut sits 0.36 mm closer to the endocardium than the true third. With perfect borders its
sub-endo Dice is 0.93 and its mid Dice 0.89 (normal wall, 0.4 mm), against 0.99 for the distance ratio. Streamline
length normalisation fixes this (Yezzi & Prince 2003, [10.1109/TMI.2003.817775](https://doi.org/10.1109/TMI.2003.817775)).
A simple potential does not.

## What it changes

1. **Thirds are a geometry problem, not a learning problem.** With exact borders, computed thirds have Dice ≥ 0.95
   at every voxel size from 0.25 to 1.5 mm, in a 5 mm wall too. A network adds nothing a border cannot give, and no
   reader could supply a reference for a "mid-wall" class anyway.
2. **The deciding metric is the border error.** A myocardium Dice of 0.955, which looks excellent, corresponds to
   0.5 mm border RMS. That gives sub-endocardial thirds of 0.90 in a normal wall but **0.76 in a thinned wall**.
   Juliet v1 therefore decides on **endo- and epicardial surface distance (mm)** and **per-segment thickness error**,
   not on Dice. Zreik 2018 reports 0.7 mm mean absolute surface distance for an LV myocardium CNN on CCTA (Dice 0.91;
   [10.1016/j.media.2017.11.008](https://doi.org/10.1016/j.media.2017.11.008), abstract). At that level the
   thinned-wall sub-endo third falls between this table's 0.5 mm row (0.76) and its 1.0 mm row (0.51).
3. **Use a streamline-length depth (Yezzi–Prince) or the distance ratio, never a raw Laplace potential.** The
   computed-layer code pins one definition, versioned.
4. **Thickness from a distance transform is biased low by about one third of a voxel** (−0.17 to −0.25 mm at
   0.4 mm; −0.5 to −0.7 mm at 1.5 mm). At native CCTA resolution this is small against the 5.5 mm thinning cut-off.
   At 1.5 mm it is not. Thinning flags must be computed on the native or 0.5 mm grid.
5. **Limits.** 2-D, concentric, smooth errors; no trabeculae or papillary muscles. Real borders fail in other ways:
   at the base, where trabeculae meet the blood pool, and at the apex. Job M0 (Juliet v1 §8) measures the real
   thickness distribution at native resolution.
