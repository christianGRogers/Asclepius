---
tags: [plans/experiment, branch-labelling, two-stage, robustness, topology]
author: Bridge
round: 1
updated: 2026-10-04
---

# Stage-1 gaps are what break naming, and bridging fixes most of it

## Question

The labeller in [[Bridge - A rule-based labeller names LM, LAD, LCx and RCA on our binary masks]] was
scored on reference masks. A stage-1 model will hand it masks with breaks (every ImageCAS-X benchmark
model leaves Betti-0 errors of 1.9–8.0 per case; [[Delta - Topology losses on coronaries are verified, and they recover branches but do not connect them]])
and with missing distal branches. Which of these errors hurts naming, and can the naming stage protect
itself without touching the voxel mask?

## Method

- 50 ImageCAS-X cases from the dev set (`pert_cases.txt`), frozen v3 labeller.
- Perturbations on the cached skeleton graph (`experiments/Bridge/perturb.py`):
  **gaps** — cut G ∈ {1, 3, 6} skeleton positions chosen length-weighted across both trees and delete all
  skeleton within 1 mm of each (a ~2 mm break), splitting the tree into fragments; **prune** — delete every
  terminal branch shorter than 10 / 25 mm (missed distal side branches), never the ostial (LM) end.
  Voxels owned by deleted vertices are dropped from scoring (that loss is stage 1's, not naming's).
- Two labeller variants: as frozen (fragments take the class of the nearest named vertex), and with
  **bridging** — before naming, join any component whose endpoint lies within 4 mm of another component
  (`label.py`, `BRIDGE=4`); the voxel mask itself is never edited.

## Result

| Perturbation | components | no bridging: voxel acc. / all-4 ≥ 0.8 | **4 mm bridging** |
|---|---|---|---|
| none | 2.1 | 0.971 / 0.94 | 0.971 / 0.94 |
| 1 gap | 3.2 | 0.958 / 0.84 | 0.971 / 0.94 |
| 3 gaps | 5.2 | 0.913 / 0.74 | 0.966 / 0.92 |
| 6 gaps | 8.1 | 0.827 / **0.50** | 0.964 / **0.92** |
| prune < 10 mm | 2.1 | 0.971 / 0.94 | 0.971 / 0.94 |
| prune < 25 mm (4.8 % of voxels gone) | 2.1 | 0.971 / 0.94 | 0.971 / 0.94 |

Bridging is neutral on unperturbed masks: on the 96 dev ImageCAS-X cases it gives the identical result
to the frozen labeller (all-4 ≥ 0.8: 0.927 both).

## What it implies

1. **Missed distal branches do not hurt naming at all**; breaks do, badly (half of cases wrong at six
   breaks), because a break near the LM moves the apparent ostium and orphans whole sub-trees.
2. **A 4 mm bridging step removes almost all of that damage** (0.50 → 0.92 fully right at six breaks),
   with no effect on intact trees. It belongs in stage 2; it only connects graph nodes for naming and never
   changes which voxels are vessel, so it cannot violate [[Training plan]] §4's "never lose a vessel".
3. For a direct multiclass model, a break is no different from any other voxel — which is both its
   strength (no cascade of errors) and the reason it has no mechanism for keeping a vessel's name
   consistent across a break.

## Limits

- Simulated breaks are ~2 mm and land uniformly along the tree; real stage-1 breaks cluster at stenoses
  and calcium and may be longer than 4 mm. To be re-measured on fold-0 stage-1 predictions (first GPU run).
- Bridging can, in principle, join the left and right trees where they come within 4 mm; not seen in
  these 50 cases, and the fused-tree QA check (one tree > 800 mm) would flag it.
