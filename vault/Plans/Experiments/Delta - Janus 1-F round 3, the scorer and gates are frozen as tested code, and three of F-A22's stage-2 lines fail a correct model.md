---
tags: [experiment, janus1-F, track-1F, round3, scorer, gates, stage2, leakage, nnunet, cpu]
author: Delta
updated: 2026-11-23
issue: christianGRogers/Asclepius#303
code: experiments/Delta/j1f_r3/
---

# Delta - Janus 1-F round 3: the scorer and gates are frozen as tested code, and three of F-A22's stage-2 lines fail a correct model

**Questions** ([[Janus 1-F Round 2]] §5, items 1–5):
1. Can the scorer of record (Atlas's definitions, SegQueue's collapse) be frozen with a hash and pass the round-2
   checks on training fixtures? Does it count the same pieces F-A15's lines were simulated on?
2. Does the gate file apply F-A15's lines exactly (OM2 recall 0.59 fails, 0.61 passes)?
3. How big is one locked case's `--save_probabilities` npz, so that the chunked predict-and-decode can be sized?
4. What does nnU-Net 2.8.1 require of the stage-1 dataset that the v2 spec did not do?
5. How often do F-A22's stage-2 lines (L1 0.02, L2 30 mm / 95 %, K1 0.05) fail a stage-2 model that is correct or
   nearly so?

**Setup.**
- **Compute:** CPU only.
- **Data:** the labels of the D45 620 training cases, fetched with Atlas's `fetch_620.py`, which checks every member
  name against the 620 before reading it.
- **Not used:** no locked-100 label, no sealed or quality-0 case, no CT, no model output.
- **Sources read:** nnU-Net 2.8.1's wheel, from PyPI.
- **Item 5's design.** ImageCAS-X has no stage-2 class, so its own traced side branches stand in for them:
  - D1–D3 on the LAD;
  - OM1, OM2 and Ramus on the LCx;
  - PDA and PLB on the RCA.

  Each stand-in is optionally bled k = 1 or 2 voxels into the traced vessel it touches: an ostium painted too wide.

## Results

1. **The scorer of record** (`j1f_scorer.py`, sha256 `d615c7e7…d808`).
   - **What it is:** Atlas's round-2 file with its collapse replaced by SegQueue's `collapse_to_four`, pinned by
     `labels.py`'s sha256. Its converter is removed (F-A18 names one converter). Everything from geometry to scoring
     is byte-identical to Atlas's.
   - **Tests:** **37 of 37** checks pass on six training cases, after the scorer's, converter's and gate file's
     self-tests.
   - **Pieces:** they equal `census_r2.jsonl`'s in **all 620 cases** (0 differ).
   - **Atlas's `gate_sim.py`** re-run on this census is **byte-identical** to the run F-A15's lines came from. F-A15
     stands.
2. **The converter of record** (`j1f_labels.py`) on the 620:
   - counts `{'d3': 47, 'd4_to_lad': 2, 'other_lcx': 20, 'other_nearest': 1, 'other_ignore': 8}`, F-A18's line
     exactly;
   - the collapse equals D25 on every voxel outside "Other" and 255;
   - 1 296 PDA/PLB components, 93 to the LCx, 0 fallbacks.
3. **The gate file** (`j1f_gates.json`, sha256 `09ddb06f…fc5f`). OM2 recall 0.59 fails; 0.60 and 0.61 pass (inclusive,
   exact fractions); 24/41 fails and 25/41 passes; 4 of 6 passes and 3 of 6 does not.
4. **The npz.** nnU-Net 2.8.1 saves 13 float32 channels at native shape, so 3.75 GB raw for a 275-slice ImageCAS-X
   case. A synthetic estimate deflates to 1.13 GB for a 206-slice case (ratio 2.5). A chunk of 10 needs ≤ 40 GB.
5. **nnU-Net 2.8.1's rules.**
   - The ignore label must be `max(labels) + 1`, so 13 on disk, not 255.
   - `move_plans_between_datasets` with `-tp` = `-sp` rewrites only `dataset_name` and `image_reader_writer`, so
     L-A21's check is exact.
6. **F-A22's stage-2 lines.** A correct or nearly correct stage-2 model was represented by stand-ins: ImageCAS-X's
   traced side branches, with an ostium bleed of k voxels.

| Gate | k = 0 | k = 1 | k = 2 |
|---|---|---|---|
| L1 (0.02, upper bound), literal | pass | LCx P(fail) 0.98 | P(fail) 1.00 (LAD, LCx) |
| L1′ (runs ≥ 3 mm only) | pass | pass (longest run 2.8 mm) | pass (pooled ≤ 0.007) |
| L2 literal (> 30 mm from stage-1 voxels) | **9 % of cases pass** (median case max 41 mm) | same | same |
| L2′ (islands > 30 mm, ≥ 95 of 100 clean) | pass | pass | pass |
| K1 (0.05, 20 cases), literal | pass | P(> 0.05) 0.21 | 1.00 |
| K1′ (lumen core, 0.10) | pass | p95 0.018 | p95 0.061, P 0 |

Also on L2: a one-sided 1.25 % bound on "≥ 95 % of cases" fails a model with 1 % stray islands 26 % of the time.
The point count fails it 0.05 % of the time.

## What it changes

- **§5 items 1 and 2 are settled.** The scorer and gate file have hashes and tests, and F-A15 needs no re-freeze.
- **The stage-1 spec gains two fixes:**
  - the ignore label is 13 on disk;
  - Dataset 719 holds the 620 only.
- **Predict-and-decode is sized:** 40 GB free per chunk of 10.
- **F-A22 keeps its numbers but changes three measures** (Delta v3 F3-4):
  - L1 counts runs ≥ 3 mm;
  - L2 counts islands, as a point count;
  - K1 counts the lumen core, at 0.10.

  As ruled, L2 would fold every correct stage-2 class. L1 and K1 would fire on a one-voxel ostium error.
- **Limits:**
  - the stand-ins are D/OM/PDA/PLB-sized, not septal-sized;
  - the npz size is a synthetic estimate, which the first predict chunk's `du` replaces.

Plan: [[Candidates/Janus 1-F/Delta v3|Delta v3]].
