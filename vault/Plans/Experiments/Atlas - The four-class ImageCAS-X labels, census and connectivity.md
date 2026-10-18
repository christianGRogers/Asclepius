---
aliases: [Atlas R9 census]
tags: [plans, experiment, round9, labels, d25, imagecas-x]
author: Atlas
round: 9
status: done
updated: 2026-10-18
issue: christianGRogers/Asclepius#48
---

# The four-class ImageCAS-X labels: census and connectivity

**Question.** What exactly does icx4 learn and get scored on, once ImageCAS-X's 14 classes are collapsed by D25?
In particular:

- how much of each class is side branch (which is what icx14's "trunk" pseudo-Dice left out);
- whether each class is still one connected piece (tF1 traces classes from an ostium);
- how often LM is absent, and how much "Other" there is.

**Method.** `experiments/Atlas/r9_icx4_census.py` runs on the ImageCAS-X segmentations (Zenodo
10.5281/zenodo.21887809, fetched 2026-10-18 by icx4's own `fetch_icx.py`). Each one is collapsed with
**`trillium/icx4/lib/territory.py` itself**, so "Other" goes to the nearest LAD/LCx in mm, exactly as icx4 trains.
Components are 26-connected. Labels only; no CT is needed.

- **The 80 sealed test cases are left out (A14):** 720 cases are reported: 560 train, 80 val, and the 80 open test
  cases. A first pass read all 800 label files. Its output was replaced before anything was committed, and no
  sealed case's numbers appear here or in the JSON.
- Per-case output: `experiments/Atlas/r9_icx4_census.json`.
- Tables: `r9_icx4_census_summary.py`.

**Result** (720 cases: 560 train, 80 val, 80 open test):

| Class | cases with it | median volume (mm³) | side-branch share of the class (median; p90) | cases where the class has > 1 piece ≥ 20 voxels | voxels outside the largest piece (mean) |
|---|---|---|---|---|---|
| LM | 709 / 720 | 99 | 0; 0 | 0 | 0 % |
| LAD | 720 / 720 | 573 | **0.24**; 0.37 | 2 | 0.01 % |
| LCx | 720 / 720 | 424 | **0.35**; 0.57 | 6 | 0.15 % |
| RCA | 720 / 720 | 805 | **0.25**; 0.35 | 0 | 0 % |

- Mean class share of tree voxels: LM 5.2 %, LAD 29.8 %, LCx 23.3 %, RCA 41.8 %.
- Whole tree: 2 components in 707 cases (left + right), 3 in 13.
- **No LM in 11 cases (1.5 %)**: separate LAD and LCx ostia. D13 makes LM optional, and tF1's per-component ostia
  (A1, Round 3) handle these cases.
- **"Other" (D3/D4, OM3/OM4)** is in 85 cases (12 %), 3.7 % of the tree where present. Echo counted 76 of 640 in
  train + val (#49).
- **Ramus (IM → LCx, D1b)** is in 173 cases. In 6 of them it is not 26-connected to the LCx main vessel, so the LCx
  class is in two pieces joined only through the LM. Those 6 are exactly the 6 multi-piece LCx cases above (checked
  case by case).
- The 2 two-piece LAD cases have pieces of ≥ 20 voxels that hold 0.01 % of LAD voxels on average.

**What it means.**

1. **The LCx is the most composite class.** About a third of its volume (more than half in 1 case in 10) is OM,
   ramus or left PDA/PLA: the small, distal, variable vessels. icx14's LCx "trunk" pseudo-Dice (0.83–0.85) and
   ImageCAS-X's LCx inter-observer DSC (84.8 ± 19.8) both leave those branches out. **The 4-class LCx can come out
   either above or below them**, so neither predicts the 4-class LCx. This is the class the LCx guard (R3) and
   Bridge's power analysis are both about.
2. **D25's collapse produces clean classes.** Every class is one piece in ≥ 99 % of cases. The exceptions are 6
   detached-ramus LCx cases and 2 LAD cases with a tiny second piece. A ramus reached through the LM is still rooted
   for tF1, because the left component's ostium reaches it. No label-repair step is needed before training.
3. **The LM is small (median 99 mm³) and absent in 1.5 % of cases.** A missed LM costs that case 0.25 of macro tF1
   (one class in four), on the fewest voxels. A1c's fallback centreline for short LM stubs (≈ 5 % of references) stays
   relevant.
4. **Side branches are 24–35 % of the LAD/LCx/RCA classes.** The icx14 failure mode (side-branch classes at Dice 0
   for 440 epochs) cannot recur: those voxels now carry the parent's label. What remains is the distal tips'
   **extent**, which tF1 recall measures and Dice barely sees.
