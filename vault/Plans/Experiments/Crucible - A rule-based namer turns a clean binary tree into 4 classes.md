---
tags: [plans, experiment, pseudo-labels, branch-naming, imagecas-x]
author: Crucible
round: 1
updated: 2026-10-04
---

# A 100-line rule-based namer turns a *clean* binary tree into LM/LAD/LCx/RCA at ~0.98 voxel accuracy — and fails on our Girder masks

## Question

How good are 4-class labels manufactured automatically from a binary coronary
mask, with no CT, no learning and no new annotation? Two inputs, to separate
the naming step from mask quality:

- **A**: the ImageCAS-X merged lumen (clean, tight lumen);
- **B**: our Girder binary mask (the original ImageCAS label; see
  [[Crucible - Original binary masks disagree with ImageCAS-X]]).

## Method

Script `experiments/Crucible/rule_naming.py` (62 ICX cases: every 13th ICX id).

Rules: the two largest 26-connected components are the left and right trees
(left = higher voxel-x index; our headers' x axis is negative in all 1000
cases); the right tree is RCA. Left tree: 3-D skeleton (scikit-image); root =
skeleton endpoint with the largest lumen radius (the ostium is a blunt cut);
LM = path from root to the first junction with ≥ 2 child subtrees each
≥ 20 mm long; of those children the most anterior (header +y) is LAD, the most
posterior LCx, any middle one (ramus) is ignored. Each voxel takes the label of
its nearest skeleton voxel; stray fragments take the nearest labelled voxel.

Reference: ICX labels mapped to 4 classes two ways —
**territory** (D1, D2 → LAD; OM1, OM2, L-PDA, L-PLA → LCx; R-PDA, R-PLA → RCA;
IM and Other → ignore) and **main-only** (only LM, LAD, LCx, RCA voxels scored).
For B, scoring is restricted to voxels both masks call vessel.

## Result (62 cases)

| Input / mapping | voxel acc. mean (median, p10) | LM Dice mean (median) | LAD | LCx | RCA | cases with LM < 0.8 |
|---|---|---|---|---|---|---|
| A, territory | 0.979 (0.997, 0.987) | 0.905 (0.979) | 0.959 (0.997) | 0.980 (0.996) | 0.990 (1.000) | 4 / 62 |
| A, main-only | 0.978 (0.997, 0.984) | 0.905 (0.979) | 0.958 (0.997) | 0.980 (0.994) | 0.991 (1.000) | 4 / 62 |
| **B (Girder mask), territory** | 0.910 (0.993, **0.740**) | **0.611** (0.950) | 0.867 (0.995) | 0.833 (0.988) | 0.984 (1.000) | **23 / 61** |

Failures on clean input are anatomical, not random: case 197 has **no left
main** (separate LAD and LCx ostia → three components; the rule assumes two
trees), voxel accuracy 0.37; cases 991 (0.70) and 565 (0.85) mis-place the
ostium. On our Girder masks the same rules fail in more than a third of cases
for LM, and in a quarter for LAD/LCx, because the extra structures and the
thick tissue layer (3.7 components, 3.6× volume) move the root and the first
large bifurcation.

## What it implies

1. **Given a clean lumen, branch naming into 4 classes is nearly solved by
   geometry** (median voxel accuracy 0.997). The hard part of this project is
   the lumen and the LM/bifurcation boundary, not "which vessel is which".
   Manufactured 4-class pseudo-labels are therefore as good as the lumen they
   are made from.
2. **Do not manufacture 4-class labels from the Girder masks directly** (B). If
   pseudo-labels are needed for the 200 non-ICX cases, make the lumen first
   (an ICX-trained model's prediction, or at minimum the HU rule in
   [[Crucible - A half-maximum HU rule recovers a tight lumen from the Girder masks]])
   and name it second — or better, let the 4-class model trained on ICX label them.
3. The namer is a free **QA check** on every team label and every prediction:
   disagreement between a submitted 4-class label and the rule's naming of
   that same label's union flags swapped LAD/LCx, a mis-placed carina, or a
   missing LM, for human review. It needs no GPU.
4. Territory vs main-only mapping barely changes the score here, because the
   namer gives side branches their parent's label and main-only scoring simply
   ignores them. The *training* convention still matters (27 % of voxels).

## Limits

- Scored against ICX's own naming, which assigns voxels to the nearest
  centerline point — the same nearest-skeleton logic the rule uses, which
  flatters boundary agreement at the LM bifurcation.
- 62 cases; rare anatomies (absent LM, left dominance: 5 %) are
  under-sampled. The absent-LM failure is structural and needs an explicit
  rule (≥ 3 large components → two left trees).
- RCA scores are trivially high because the right tree is one component in
  almost all cases.
