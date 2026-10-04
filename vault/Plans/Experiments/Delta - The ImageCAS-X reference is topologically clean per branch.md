---
tags: [plans, experiment, topology, labels, imagecas-x, post-processing]
author: Delta
round: 1
updated: 2026-10-04
---

# The ImageCAS-X reference is topologically clean per branch — so "one piece per branch" is a safe rule

## Question

A label-consistency post-processing step ("each branch is one connected piece in its tree;
LAD and LCx attach to LM; RCA never touches the left tree") is only safe if the *reference*
labels obey it. Do they? And how much of each class is side branch (the 4-class convention
question: do diagonals/marginals belong to LAD/LCx or to background)?

## Method

`experiments/Delta/icx_topology.py` (summary: `summarise_icx_topo.py`). ImageCAS-X 14-class
labels (Zenodo 10.5281/zenodo.21887809; case mapping ImageCAS id n → our `c{n-1}`, verified in
[[Crucible - ImageCAS-X is real and its 800 cases are our cases c(id-1)]]), every 4th case of the
800 in id order, stopped at **100 cases** for CPU. Two 4-class mappings:
*subtree* (D1/D2/Other-diagonals → LAD; OM1/OM2/IM/L-PDA/L-PLA → LCx; R-PDA/R-PLA → RCA;
"Other" (14) → nearest labelled voxel) and *trunk* (only LM=1, LAD=2, LCx=3, RCA=9; side branches
dropped). Per class: 26-connected pieces; 26-contact between LAD–LM, LCx–LM, LAD–LCx, RCA–left.
IM (ramus) is put with LCx in *subtree* — a convention choice, not anatomy.

## Result (100 cases)

| | subtree | trunk |
|---|---|---|
| LM present | 97/100 | 97/100 |
| LM one piece | 97/97 | 97/97 |
| LAD one piece | **100/100** | 99/100 (c0083: 5060 + 2853 voxels) |
| LCx one piece | 99/100 (2nd piece = 1 voxel) | 99/100 (1 voxel) |
| RCA one piece | 100/100 | 100/100 |
| LAD touches LM (when LM present) | 97/97 | 97/97 |
| LCx touches LM (when LM present) | 97/97 | 96/97 |
| RCA touches left tree | 0/100 | 0/100 |

- ImageCAS-X lumen: 2 components in 96/100; the 4 others have a real 3rd vessel. **The three
  cases without LM (c0020, c0141, c0196) are exactly the three-component cases with LAD and LCx
  arising separately** — the "LM attached to aorta, LAD/LCx attached to LM" grammar must allow
  this 3 % variant (ImageCAS-X's paper says so too). c0509's 3rd component is 459 voxels.
- **Side branches are a large share of each class under the subtree convention**: median 25 %
  of LAD voxels (IQR 19–30 %), 36 % of LCx (23–47 %), 25 % of RCA (18–30 %).
- Variant classes in this sample: IM 18/100, L-PDA/L-PLA 8/100, "Other" 13/100.

## What it implies

1. **"One piece per class per tree" holds in ≥ 99 % of reference cases** (one 1-voxel speck,
   one trunk-convention LAD split). A post-processing step that enforces it — by relabelling,
   never by deleting — cannot hurt correct labels except in ~1 % of cases. The parent-attachment
   rule holds whenever LM exists; when LM is absent (3 %) LAD and LCx are separate trees.
2. The 4-class convention is not a detail: it moves 25–36 % of each left-tree class's voxels in
   or out of the label. Per-class Dice is therefore dominated by the convention, and the
   project must write it down before the first multiclass run. The team splits a whole seed tree,
   which naturally yields the *subtree* convention; I assume it, and the harness scores both.
3. The ramus intermedius (18 %) has no parent trunk in a 4-class schema: it is the one place a
   "label swap" can be a protocol disagreement rather than a model error (measured in
   [[Delta - Dice cannot see the errors that break a coronary tree]]).

## Limits

- 100 of 800 cases (stride 4); proportions have ±~3 pp sampling error at these rates.
- Contact is voxel 26-adjacency, not anatomical attachment.
- The team's labels (split from the *original* masks, ~3× thicker) may behave differently; this
  must be re-run on the first 50 team-labelled cases.
