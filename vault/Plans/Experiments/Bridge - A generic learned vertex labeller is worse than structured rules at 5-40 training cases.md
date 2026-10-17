---
tags: [plans/experiment, branch-labelling, two-stage, label-efficiency, negative-result]
author: Bridge
round: 1
updated: 2026-10-04
---

# A generic learned vertex labeller is worse than the structured rules at 5–40 training cases

## Question

My thesis says stage 2 (naming LM/LAD/LCx/RCA on a binary tree) needs far fewer per-branch labels than
a direct multiclass net. Two ways to learn stage 2 exist: (a) keep the anatomical structure as rules
and learn only the few hard decisions (the ostium —
[[Bridge - Finding the left ostium is the crux of naming, and 5-10 labelled cases teach it]]), or
(b) a generic per-skeleton-vertex classifier plus a tree-structured decoder. How good is (b) as a
function of the number of labelled cases, against (a) on the same test cases?

## Method

- Cases: the 120 cached cases of the development set (`devset3`), of which **93 have ImageCAS-X
  labels and two main trees**; random split: test = 31 cases, pool = 62.
- Vertex features (root-independent): RAS position relative to the left-tree centroid and to the
  right-tree centroid (raw and normalised by their distance), smoothed radius, degree, sign-free
  tangent. Target: majority ImageCAS-X class (LM/LAD/LCx) of the mask voxels owned by the vertex.
- Classifier: `HistGradientBoostingClassifier` (200 iterations). Decoder: exact tree MAP under the
  grammar *LM is a single path from the root; below it each subtree is wholly LAD or wholly LCx*, root
  chosen jointly among the 8 best learned-ostium candidates as the root of minimum cost. Right tree = RCA.
- Training sizes N = 5, 10, 20, 40 (3 random draws each for N ≤ 40).
- Comparator: the frozen structured rule labeller (v3: learned ostium + plausibility re-rank +
  anterior/posterior split rule) on the **same 31 test cases**.
- Score: voxel-wise per-class Dice vs ImageCAS-X labels projected onto our mask (voxels within 2 mm of
  an ImageCAS-X vessel, IM/"Other" excluded), and the fraction of cases where all four classes reach
  Dice ≥ 0.8. Script: `experiments/Bridge/learn.py`. (An earlier variant whose decoder let the LM label
  spread into side branches scored 0.963 / 0.972 / 0.976 accuracy at N = 5 / 10 / 20; log kept.)
- Leakage note: the ostium logistic weights used by both arms were fit on 79 of these dev cases, so the
  absolute numbers are mildly optimistic for both; the comparison is paired.

## Result

| Labeller | N train | LM | LAD | LCx | RCA | voxel acc. | cases all ≥ 0.8 |
|---|---|---|---|---|---|---|---|
| vertex GBM + grammar | 5 | 0.725 | 0.969 | 0.948 | 1.000 | 0.971 | 0.51 |
| vertex GBM + grammar | 10 | 0.798 | 0.977 | 0.957 | 1.000 | 0.978 | 0.59 |
| vertex GBM + grammar | 20 | 0.816 | 0.979 | 0.956 | 1.000 | 0.979 | 0.65 |
| vertex GBM + grammar | 40 | 0.829 | 0.981 | 0.953 | 1.000 | 0.981 | 0.68 |
| **structured rules v3** | (ostium model only) | **0.915** | **0.987** | **0.950** | **1.000** | **0.987** | **0.94** |

## What it implies

1. **Honest negative for the generic learner.** A per-vertex classifier gets the big vessels right
   (LAD/LCx ≈ 0.95–0.98 from 5 cases) but places the LM/bifurcation boundary poorly, and the
   all-classes-correct rate is 0.51–0.68 against 0.94 for the rules. Its curve flattens after ~20 cases,
   so more labels are not the fix; structure is.
2. **The cheap stage 2 is "rules + learn the few decisions"**, not "learn everything". With labels arriving,
   what should be learned is the ostium score (already learned) and the bifurcation choice (currently a
   hand score; next to replace with a learned candidate ranker trained the same way as the ostium one).
3. Either way, the right tree is trivial (RCA Dice 1.000 whenever the two trees are separate
   components); all naming difficulty is in the left tree.

## Limits

- 31 test cases; ImageCAS-X labels on a 3× thinner lumen are the truth, not our protocol's.
- Features are geometric only; CPR-GCN's result (Yang et al., CVPR 2020, arXiv:2003.08560, Table 3) says
  image features along segments help a learned labeller — not tested here.
