---
tags: [plans/experiment, patch-size, fallback, r0]
author: Atlas
round: 3
updated: 2026-10-05
---

# The fallback 192 × 256 × 256 patch at 0.5 mm, measured

## Question

The Round 2 ruling (§2, Atlas (b) i) found that the master's R0 fallback claim, "holds the left tree in 93 % and the
whole tree in 92 % of 153 cases", appears in no experiment note. What does the fallback patch actually contain? The
fallback is the ResEnc XL preset at 0.5 mm: 192 × 256 × 256, i.e. 96 × 128 × 128 mm (z, y, x).

## Method

Exactly the method of
[[Atlas - A 128 mm patch at 0.5 mm holds the whole tree and the LM in almost every training patch]]:

- the same 153 ImageCAS-X cases (id list frozen in `$SCR/work/Atlas/es_ids.txt`);
- trunk 4-class mapping, 2 mm presence grid;
- nnU-Net-faithful centred foreground patches.

The fallback geometry was added as a fifth patch (`'iso05_XL_12.6M': (128, 128, 96)` mm x, y, z), and all five
patches were re-run in one pass (`experiments/Atlas/extent_sampling.py es_v3.jsonl @es_ids.txt`; summary
`summarise_extent.py`). The four original patches reproduce the earlier note's numbers exactly.

## Result

| | Master 256³ (128 mm cube) | **Fallback 192 × 256 × 256 (96 × 128 × 128 mm)** |
|---|---|---|
| One patch holds the LAD | 1.00 | 0.94 |
| … the left tree | 1.00 | **0.935** |
| … the right tree | 0.99 | 0.99 |
| … the whole tree | 0.98 | **0.915** |
| Best patch captures (fraction of whole tree) | 1.000 | 0.998 |
| Random patch contains LM | 0.985 | 0.82 |
| LAD-centred patch contains LM | **0.97** | **0.85** |
| LCx-centred patch contains LM | 0.985 | 0.925 |
| RCA-centred patch contains LM | 0.98 | 0.715 |

## What it implies

1. **The v2 extent figures are confirmed:** 93.5 % for the left tree and 91.5 % for the whole tree, against the
   93 % / 92 % stated.
2. **The fallback loses context where it matters.** The LM is in view of 85 % of LAD-centred patches instead of
   97 %. The loss comes from the shorter z extent (96 mm against LAD z extents up to 109 mm). The fallback is a real
   step down, not free.
3. **Order of fallbacks, if R0 fails.** First try what keeps the 128 mm cube:
   - more loader workers;
   - the GPU spatial transform;
   - lower spatial-augmentation probability;
   - for VRAM only, activation checkpointing or batch 1, as in
     [[Atlas - Without a GPU, nnU-Net's own loader and a saved-tensor count bound R0]].

   Only then drop to 192 × 256 × 256. If the fallback is used, branch-swap rate on val is the metric to watch.

## Limits

Same as the parent note: 153 cases from both ends of the id range; ImageCAS-X trunk trees, which are thinner than our
masks; 2 mm grid.
