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

RESULT_NOTE

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
