---
tags: [experiment, bridge, janus-1f, track-1-F, round3, scorer, gates, stage2, nnunet]
author: Bridge
updated: 2026-11-23
issue: christianGRogers/Asclepius#303
code: experiments/Bridge/j1f_r3/
---

# Bridge - The 1-F scorer counts what the gates were simulated on, and two stage-2 lines would fail a correct model

Behind [[Candidates/Janus 1-F/Bridge v3|Bridge v3]] (track 1-F, round 3). CPU only. Only the 620 D45 training labels
were read. No locked, sealed, quality-0 or D60 case was opened, no model output exists, and nothing ran on Fir, SciNet
or Trillium.

## Questions

1. Does the scorer of record (Atlas's file with SegQueue's collapse, F-A16/F-A17) count the same pieces the F-A15
   lines were simulated on, over the 620?
2. Does `j1f_gates.json` make OM2 recall 0.59 fail and 0.61 pass?
3. What would block or break J1F-A's commands in nnU-Net 2.8.1, and how much disk does the chunked predict need?
4. Do F-A22's stage-2 numbers (L1 0.02, L2 30 mm in ≥ 95 %, K1 0.05) false-fail a **correct** stage-2 model?

## Setup

| Question | Script | Data |
|---|---|---|
| 1 | `j1f_scorer.py` (selftest), `test_scorer_cases.py`, `run620.py` + `summarise620.py` | the 620 references (D47 (A) labels by Atlas's round-2 converter, the census's own) |
| 2 | `test_gates.py` | none (fixtures) |
| 3 | nnU-Net 2.8.1's wheel source; `npz_size.py`; `decode_ref.py` | two training cases for npz size |
| 4 | `stage2_sim.py` + `summarise_stage2.py` | 120 hash-chosen training references plus synthetic correct stage-2 tubes |

## Results

**1. The scorer.**
- `j1f_scorer.py` (sha256 `7e6875a3…ff78`) is Atlas's file with three changes:
  - SegQueue's `collapse_to_four` replaces the ring collapse, with `labels.py` pinned at import;
  - the converter is removed;
  - the B reading (`load_gates`, `aggregate`, `verdict`) is added.
- Its self-test passes, including the chain rule, a counted fallback, and OM2 23/24/25 of 40.
- On Delta's six training cases, all **34 of 34** checks pass: Delta's (30 apply to these cases) and Atlas's four. The one-voxel erosion
  is a report: recall D1 0.83 and PDA 0.83, from one thin branch each vanishing, as Atlas found.
- On all 620 cases, piece counts, lengths and voxel counts equal Atlas's census in every case and class:
  - PDA has 543 / 62 / 3 cases with 1 / 2 / 3 pieces;
  - PLB has 600 / 10 with 1 / 2.
- The converter totals equal F-A18's line.
- The collapse equals D25 on every voxel outside "Other" and 255, with 0 fallbacks over 1,296 components.
- Four pieces (one each of D2, OM2, PDA and PLB) sit in cases under 5 mm. That is far inside the lines' rounding.

**2. The gates.**
- `j1f_gates.json` (sha256 `16ce8954…1b6b`) equals Atlas's `proposed_lines`.
- OM2 recall 0.59 fails; 0.60 and 0.61 pass.
- Each of the 18 lines holds at its value and fails 0.01 below.
- A changed file is refused.

**3. nnU-Net 2.8.1.**
- **The ignore label must be the largest label + 1** (`label_handling.py` l. 41). With 13 classes it is 13, so F-A3's
  255 would stop training at its first step.
- **Probabilities are saved as float32 at the original CT shape** (`label_handling.py` l. 138,
  `export_prediction.py` l. 101):
  - 3.5–3.75 GB per case uncompressed;
  - compressed, 0.02 GB for an idealised smooth softmax up to 3.0–3.2 GB with logit noise.
  - So a chunk of 10 is budgeted at ≤ 38 GB.
- `move_plans_between_datasets` keeps the plans identifier when `-tp` is omitted.
- The fit-check 20 recomputed from the split: sha256 `3f3b696c…1330`, equal to Foxtrot's file.

**4. Stage 2, on 120 training references with correct synthetic branches** (straight tubes, radius 0.6 mm, length
10–50 mm; painted outside the lumen only, or also over the host's lumen for 2.5 mm, as D47 Q4 trains):

| Number | Correct model's value | False-fail as ruled |
|---|---|---|
| L1 (≤ 0.02 theft) | 0.016–0.017 (junction painting), 0 otherwise | 0 in every scenario |
| L2 (no voxel > 30 mm in ≥ 95 %, 1.25 % bound) | tip distance ≈ branch length | 0.56–0.81 at 30 mm, where only 0.8–1.7 % of cases cross; 1.00 at ≥ 40 mm |
| K1 (≤ 0.05 of voxels in the traced lumen) | 0.11–0.16 at 10 mm, 0.06–0.08 at 20 mm, 0.04–0.06 at 30 mm | ≈ 1.00 at ≤ 20 mm; 0–0.99 by class at 30 mm |
| L2′ (islands > 5 mm, ≥ 95 of 100) | — | 0 |
| K1′ (L1 on the 20 fit-check cases > 0.03) | — | 0 |

- **L2's lower bound at one-sided 1.25 % needs 100 of 100:** at 99 of 100 it is 0.938.
- **A model with islands in 10 % of cases fails L2′ with probability 0.94.**

## What it changes

- **The scorer of record and the gate file can be pinned now:** `j1f_scorer.py` `7e6875a3…ff78`,
  `j1f_gates.json` `16ce8954…1b6b`.
- **Two launcher corrections before J1F-A is built:**
  - the ignore value in Dataset 719 must be **13** (nnU-Net asserts ignore = max label + 1), with `collect`
    mapping 13 → 255;
  - predict's chunk of 10 is budgeted at ≤ 38 GB of float32 npz, and the first chunk's size is posted.
- **For J1F-2's freeze, not before:**
  - replace L2 by an island rule read on the point count;
  - replace K1 by L1's centreline statistic on the fit-check cases;
  - keep L1.
- **Stage 1 is converged in Bridge's view,** given F0-r2's expected lines and a recorded Q-F2-3 answer. Both of
  Q-F2-3's branches are written out in the candidate, §6.
