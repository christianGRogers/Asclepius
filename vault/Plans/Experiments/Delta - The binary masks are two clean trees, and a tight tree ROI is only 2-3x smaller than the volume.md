---
tags: [plans, experiment, data, topology, roi, connectivity]
author: Delta
round: 1
updated: 2026-10-04
---

# The binary masks are two clean trees, and a tight tree ROI is only 2–3× smaller than the volume

## Question

1. Are the ground-truth binary trees connected? How many components, how many fragments —
   i.e. can "each tree = one component" be used as a rule and as a metric reference?
2. How big is the region a coronary model actually needs (tree bounding box + margin), as a
   fraction of the CT volume and in 256³ patches — i.e. what would a localise-then-segment
   design buy?
3. Grid facts (spacing, orientation) cohort-wide.

## Method

`experiments/Delta/survey_masks.py`, summarised by `summarise_survey.py`. For each binary mask
(`coronary_arteries.nii.gz`, threshold 0.5): shape, spacing, axis codes, foreground voxels,
26-connected components (cc3d) with sizes/bboxes, whole-tree bounding box, and that box grown
by 0/10/20 mm (clipped to the volume). **583 of the 1000 masks** (every other case, c0000–c0999,
in two interleaved shards; stopped at 583 because the shared CPU was saturated — the sample is
spread over the whole id range).

## Result

**Grid.** All 583: 512×512 in-plane, in-plane spacing 0.295–0.465 mm (median 0.350), **z
spacing 0.5 mm in every case**, 187–275 slices (median 275), axis codes LAS for all, masks stored
float64 {0,1}. (Agrees with Crucible's header scan of all 1000.) The cohort is anisotropic
(z/xy ≈ 1.43), not "near-isotropic ~0.35 mm".

**Connectivity of the reference trees.**

| Components (26-conn) | Cases | % |
|---|---|---|
| 1 | 8 | 1.4 |
| 2 | 437 | 75.0 |
| 3 | 110 | 18.9 |
| 4 | 20 | 3.4 |
| 5–7 | 8 | 1.4 |

- Third and later components are almost all specks: median size of the 3rd component **3
  voxels**; 123 of 138 are < 100 voxels. Only **8/583 (1.4 %)** carry a 3rd component ≥ 1000
  voxels (separately-arising vessel or a broken reference; e.g. c0492: 43.0k / 42.9k / 39.8k).
- **Fused left+right trees: ~2 %.** The 8 one-component cases (c0116, c0234, c0242, c0315,
  c0398, c0502, c0578, c0588) and cases like c0038, c0484, c0726 (2nd component ≤ 10 voxels)
  have left and right trees joined into one component (MIP of c0116/c0038 inspected: both
  trees present, touching where distal branches cross). With labels ~3× thicker than the
  ImageCAS-X lumen (see Crucible's comparison), crossing vessels touch.
- The 2nd component (normally the RCA tree) is < 10 % of the 1st in 11/583 cases
  (left-dominant or truncated RCA, e.g. c0025: 77.9k vs 5.3k voxels).

**ROI size.** Tree extent (x, y, z) median 110 × 94 × 88 mm, p95 127 × 110 × 104 mm.

| Box | Fraction of volume (median / p95 / max) | Mvox median / p95 | 256³ patches to tile, median |
|---|---|---|---|
| Tight tree bbox | 0.215 / 0.316 / 0.432 | 14.6 / 19.7 | 0.87 |
| + 10 mm | 0.376 / 0.522 / 0.701 | 25.4 / 33.0 | 1.52 |
| + 20 mm | 0.579 / 0.740 / 0.902 | 38.7 / 48.6 | 2.31 |
| Full volume | 1 | 72.1 | 4.3 (256³ = 23 % of a volume) |

Foreground is 0.16 % of the volume (median; 0.05–0.36 %). The tree bbox touches a volume face in
8/583 (7 at the top, superior, face — the field of view clips the proximal vessels there).

## What it implies

1. **Topology rule, with exceptions measured:** "≥ 2 trees, each one component" holds for ~97 %
   of references after dropping components < 100 voxels. Post-processing may *reconnect* and
   *relabel*, but must never *delete* a large component (1.4 % have a real 3rd vessel) or force
   left and right apart (~2 % are fused in the reference itself). A component-count metric must
   be computed against the reference's own count, not against "2".
2. **Speck removal at < 100 voxels is safe on the reference** (ImageCAS-X's rule): 123/138 extra
   components are < 100 voxels; it would delete none of the ≥ 1000-voxel ones.
3. **Localise-then-segment buys 2–3×, not 10×.** A tree ROI with a 10 mm margin is 38 % of the
   volume (52 % at p95). This is a modest inference saving and a modest training-sampling gain —
   the same gain vessel-anchored patch sampling gives with no extra model. I therefore **drop the
   separate localisation network from my opening thesis**: it adds a failure mode (a clipped RCA,
   the master plan's own objection) for a 2.6× saving. What does matter: **one 256³ patch at
   native spacing (≈ 90 × 90 × 128 mm) covers ~87 % of the tight tree box** — nearly the whole
   tree, both ostia and the LM carina are in one field of view, which is the context that
   separates LAD from LCx.
4. The reference has its own topological defects (fused trees, a few broken pieces). Any
   topology metric must be scored against the reference's actual topology, and fused/broken
   references should be flagged in the evaluation set, not silently averaged.

## Limits

- 583/1000 cases; the remainder was not surveyed for CPU reasons (the sample is interleaved
  over all ids).
- Component counts are on the **original ImageCAS** masks; the ImageCAS-X lumen is different
  and is measured separately ([[Delta - The ImageCAS-X reference is topologically clean per branch]]).
- "Fused" was inspected visually on 2 cases only; the mechanism (crossing contact) is inferred.
