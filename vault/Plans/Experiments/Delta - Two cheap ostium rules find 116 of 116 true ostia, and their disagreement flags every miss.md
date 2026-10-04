---
tags: [plans, experiment, metrics, ostium, tree-f1, validation]
author: Delta
round: 2
updated: 2026-10-04
---

# Two cheap ostium rules find 116 of 116 true ostia, and their disagreement flags every miss

## Question

Tree-F1 (master plan A1) only credits centreline connected to an **ostium**. The Round 1 ruling
requires the ostium to be defined by contact with the TotalSegmentator aorta and validated on ≥ 30
cases. How accurate are the candidate ostium rules, measured against independent ground truth?

## Method

`experiments/Delta/ostium_eval.py` (summary `summarise_ost.py`; aortas `aorta_ts.py`).
- **Truth:** ImageCAS-X centreline `start_points` (VTK attribute; ImageCAS-X defines them as
  degree-1 centreline vertices within 5 mm of a TotalSegmentator aorta, reviewed by their lead
  analyst). Fetched for every case with a cached CT by HTTP range read from the Zenodo zip
  (116 VTK files, 3 MB); LPS world → our voxel grid (checked: 100 % of points fall inside the lumen).
- **Cases:** all **61** ImageCAS-X cases with a cached CT; 58 have both a left and a right
  centreline file (116 trees, 116 true start points; no case in this sample has separate LAD/LCx ostia).
- **Rules, applied to the reference lumen's own skeleton** (the ostium tree-F1 uses):
  *thick* — per tree the endpoint with the largest median radius over ~20 centreline voxels, LM end
  preferred (v1 rule); *pool_thick* — contrast blood pools from the CT (`treelib.blood_pool`: smooth
  0.7 mm, > 200 HU, coronary mask excluded, 3 mm opening, components ≥ 2 cm³), then among endpoints
  within 3 mm of the endpoint nearest a pool, the thickest; *aorta* — endpoints within 5 mm of the
  TotalSegmentator aorta (`--fast`, `roi_subset=aorta`).
- **TotalSegmentator ran on only 5 cases**: on this shared CPU machine it used 4.6 + 2.7 GB RSS and
  was OOM-killed twice (and took a neighbour's job with it); it is cheap on Trillium.

## Result

Distance from each true start point to the rule's ostium:

| Rule | trees | ≤ 2 mm | ≤ 5 mm | median | max |
|---|---|---|---|---|---|
| thick, left | 58 | 96.6 % | **100 %** | 0.59 mm | 2.3 mm |
| thick, right | 58 | 94.8 % | 98.3 % | 0.49 mm | 41.3 mm (c0526) |
| pool_thick, left | 58 | 94.8 % | 98.3 % | 0.60 mm | 7.0 mm (c0073) |
| pool_thick, right | 58 | 96.6 % | **100 %** | 0.43 mm | 2.1 mm |
| TS aorta ≤ 5 mm, left | 5 | 100 % | 100 % | 0.0 mm | 0.9 mm |
| TS aorta ≤ 5 mm, right | 5 | 80 % | 100 % | 0.5 mm | 2.0 mm |

The two cheap rules **never fail on the same tree**: the only misses are thick on c0526-right and
pool_thick on c0073-left, and in both trees the other rule is within 0.0 mm. On the other 114 trees
both rules are within 2.5 mm of the truth.

## What it implies

1. The deployable ostium for tree-F1 can be: **TotalSegmentator aorta contact (≤ 5 mm) where it
   runs, cross-checked by the two cheap rules**; a case where the rules disagree by > 5 mm is
   flagged for a human (2 of 116 trees here, 1.7 %) instead of being scored silently. In this sample
   that procedure gets all 116 ostia right.
2. The v1 "thickest endpoint" heuristic the judge was wary of is right in 115/116 trees; its one miss
   would have zeroed RCA tree-F1 in c0526. The cross-check is what makes it safe.
3. The same rules give the *deployable* anchor for gap bridging (largest predicted components within
   3 mm of the aorta / pools) without any reference — see
   [[Delta - Gap-centred re-inference plus 3 mm bridging repairs the cut trees and never made a case worse]].

## Limits

- Truth is ImageCAS-X's own aorta-contact rule (reviewed), so the aorta rule agreeing with it is
  partly by construction; the cheap rules are the independent test.
- TotalSegmentator validated on 5 cases only (memory); on Trillium it should be run on all 1000.
- No case here has an absent LM (separate ostia, ~3 % of the cohort, E6); multiple start points per
  tree are supported by the code but untested.
