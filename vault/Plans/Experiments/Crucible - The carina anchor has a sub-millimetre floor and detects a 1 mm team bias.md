---
tags: [plans, experiment, a12, carina-anchor, imagecas-x, noise-floor]
author: Crucible
round: 5
updated: 2026-10-08
---

# The ImageCAS-X carina anchor has a sub-millimetre convention floor (robust SD 0.6 mm): with medians it detects a 1 mm team-wide bias in 50 cases, and a 1 mm annotator difference in 25 + 25

## Question

A12b uses ImageCAS-X's carina (its LM end) as an external anchor for a team-wide carina bias. The Round-4 ruling
(§4) made one prerequisite binding: measure the anchor's **convention noise floor** on ≥ 100 cases.

That floor is the offset the anchor reports when the team has no bias at all but draws on the thick mask (D0).
If its spread exceeds about 1 mm, the 1 mm thresholds are unfounded.

## Method

`experiments/Crucible/r6_anchor_floor.py`, summary `r6_summ.py`.

**Cases.** 130 ImageCAS-X train/val cases, taken in order of a fixed hash. **None is sealed**: the script asserts
it against `trillium/sealed_test.json`.

**Per case:**

- **Thick mask.** The Girder/ImageCAS mask (the D0 convention). Its left tree is skeletonised. The geodesic distance
  *d* along that skeleton runs from the ostium, defined as the ImageCAS-X LM voxel farthest from LAD/LCx, projected
  to the skeleton.
- **ImageCAS-X carina.** The centroid of ImageCAS-X LM voxels touching LAD/LCx, projected to the nearest skeleton
  point. This is *d*_ICX. ImageCAS-X's analysts partition names at their own centreline bifurcations, so this is
  their bifurcation.
- **Floor A, `thick-bif − ICX`.** This is a team with no bias that places the carina where the *thick* tube
  bifurcates. The thick bifurcation is found topologically, without reference to the ImageCAS-X carina position: it
  is the lowest common ancestor, on the shortest-path tree from the ostium, of the farthest LAD point and the
  farthest LCx point. This is the floor A12b asked for.
- **Floor B, `proxy − ICX`.** This is a team that reproduces ImageCAS-X's naming exactly: the projected proxy. It
  measures pure measurement and projection noise.
- **Injected-bias recovery** (40 further cases, 36 scored). The proxy's carina is moved by ±1 and ±2 mm with the
  same operation the simulated reads use. The anchor's reading is recorded.

**Detection power.** I resampled the measured floor distribution, with no normal assumption. A bias is called
detected when the 95 % bootstrap CI of the median (or mean) offset excludes the floor's median:

- a **team-wide bias**: n = 50 cases (A12's wave-1 size);
- an **annotator-habit** difference: 25 cases per annotator, two annotators.

## Result

**130 cases; 125 scored, 124 for floor A.** Five were skipped: four ImageCAS-X cases with no LM (separate ostia,
including c0196), and one skeleton without a reachable LAD.

| Offset along the centreline (mm) | n | median | mean | robust SD (1.4826·MAD) | SD | p5 / p95 | share with \|x\| > 2 mm |
|---|---|---|---|---|---|---|---|
| **A: thick bifurcation − ImageCAS-X carina** | 124 | **+0.70** | +2.03 | **0.62** | 13.26 | −0.80 / +2.05 | 9 % |
| B: projected proxy − ImageCAS-X carina | 125 | 0.00 | −0.15 | 0.00 | 0.58 | −0.98 / 0.00 | 2 % |
| (ImageCAS-X LM length, for scale) | 125 | 7.33 | 8.33 | 4.82 | 5.39 | 0.75 / 17.15 | — |

The SD of 13 mm comes from **4 method failures** with \|x\| > 5 mm (143.0, 38.5, 5.0 and −5.3 mm):

- In c0901 and c0058, the "farthest LAD" path runs through the wrong subtree of a looped or fused thick skeleton.
- c0024 and c0350 are 4–5 mm Euclidean misses.

These are detectable per case (\|offset\| > 5 mm, or a bifurcation farther than 3 mm from the ImageCAS-X carina).
They belong in QA flags, not in the bias estimate.

**Injected bias is read back roughly 1 : 1** (36 cases; median reading minus the case's own floor reading):

| Injected | −2 mm | −1 mm | +1 mm | +2 mm |
|---|---|---|---|---|
| Anchor reads (median; robust SD) | −2.62 (0.46) | −1.25 (0.50) | +1.10 (0.47) | +1.86 (0.57) |

**Detection rate** (resampling the measured floor A):

| True bias | team-wide, n = 50, **median** | annotator difference, 25 vs 25, **median** | team-wide, n = 50, mean | annotator difference, mean |
|---|---|---|---|---|
| 0 mm (false alarm) | 0.09 | 0.03 | 0.12 | 0.11 |
| 0.5 mm | 0.94 | 0.53 | 0.75 | 0.38 |
| **1.0 mm** | **1.00** | **0.96** | 1.00 | 0.63 |
| 1.5 mm | 1.00 | 1.00 | 1.00 | 0.69 |
| 2.0 mm | 1.00 | 1.00 | 1.00 | 0.63 |

## What it implies

1. **The prerequisite is met.** Under a no-bias team on the thick mask, the convention floor has robust SD 0.6 mm,
   below the 1 mm the ruling set as the limit.
   - There is a **constant convention offset of +0.7 mm**: the thick tube bifurcates 0.7 mm distal of ImageCAS-X's
     carina. A12b must subtract this before testing.
   - Restated A12b rule: team-wide bias = median (team − ImageCAS-X) − 0.7 mm, with a bootstrap CI. Flag it if the
     CI excludes ±1 mm.
2. **Use medians, never means.** About 3 % of cases are method failures with offsets of 5–140 mm. With means, the
   25 + 25 annotator test never reaches 70 % power at any bias, because the outliers dominate. With medians it
   detects a 1 mm annotator difference 96 % of the time.
3. **A12a's habit test is powered** at 25 cases per annotator for differences of ≥ 1 mm, but not for 0.5 mm (53 %).
   The 1 mm habit threshold in v5 §2.1 is therefore the right size. Smaller habits need more cases per annotator.
4. **False alarms run slightly above nominal** (0.09 for the team-wide median test against 0.05). Require two
   consecutive waves, or n ≥ 80, before re-instructing the whole team.
5. **QA flag:** any case with an anchor offset > 5 mm, or a thick bifurcation > 3 mm from the ImageCAS-X carina, is
   a measurement failure. It is reviewed, not counted.

## Limits

- Floor A assumes an unbiased team puts the carina at the thick tube's topological bifurcation. Real annotators add
  their own scatter. That scatter is what A12 measures, and it does not change the floor.
- 130 cases. The ImageCAS-X carina is one analyst's per case (its double reads are not in the release).
- The four cases with no LM have no anchor. The anchor does not exist for separate ostia.
- Bootstrap CIs of a median on 50 discrete-ish offsets are slightly anti-conservative (point 4).
