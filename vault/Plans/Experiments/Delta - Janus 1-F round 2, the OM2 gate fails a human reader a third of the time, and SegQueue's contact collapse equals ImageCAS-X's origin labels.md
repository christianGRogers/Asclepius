---
tags: [experiment, janus1-F, track-1F, round2, gates, simulation, scorer, D47, band, cpu]
author: Delta
updated: 2026-11-15
issue: christianGRogers/Asclepius#303
code: experiments/Delta/j1f_r2/
---

# Delta - Janus 1-F round 2: the OM2 gate fails a human reader a third of the time, and SegQueue's contact collapse equals ImageCAS-X's origin labels

**Questions** ([[Janus 1-F Round 1]] §5, items 1, 2 and 4):
1. How often do F-A6's B gates fail a human-level model on the locked 100?
2. Can the scorer's definitions be frozen as code that passes a self-test?
3. Does D47's contact collapse (SegQueue 0.20.0) reproduce ImageCAS-X's origin labels?
4. How much background does a stage-2 band of w mm release, and how much of a branch-sized structure does it cover?

**Setup.** CPU only, labels only. The 720 non-sealed ImageCAS-X label maps were fetched with round 1's
`fetch_allowed.py`, which skips every sealed case before reading it. No CT and no model output was used. The locked
100's reference labels were counted (F-A7). Every other test ran on training cases, except the label-to-label
collapse check.

## Results

1. **Gates** (`gate_sim.py`).
   - **The simulated reader.** A second reader is simulated from ImageCAS-X Table 1:
     - per-class miss rates, from n and agreement with disagreements split evenly: D1 0.016, D2 0.085, OM1 0.033,
       OM2 0.179, PDA 0.006, PLB 0.020;
     - extras inserted at a random sibling rank;
     - positional names, so a dropped D1 renames D2.
   - **As ruled** (recall 0.80, naming 0.85, agreement Table 1 − 0.05): OM2 fails a human-level reader **36 %** of the
     time (recall 27.5 %, naming 11.8 %). D2 fails 0.8 %, or 15 % at 1.5× human error. The others fail ≤ 0.4 %.
     P(< 4 of 6) is 0.000, or 0.007 at 1.5×.
   - **At recall 0.75 and naming 0.80** (margin unchanged): OM2 11 %, the rest ≤ 0.4 %, and P(< 4 of 6) 0.000
     (0.002 at 1.5×).
   - **Against bad models:**
     - a model that calls every class in every case: not adopted 100 %;
     - names shifted in 25 % of cases: 100 %;
     - 20 % or 35 % of branches missed: ≥ 99.8 %;
     - names shifted in 15 % of cases: 21 %, against 98 % as ruled.
   - **Calibration.** The PDA/PLB swap rate must be ≈ 0.01 to match Table 1's 98.8 % agreement.
2. **Scorer** (`branch_score.py`, sha256 `fb629576…9840`). 31 of 31 self-test checks pass on six training cases:
   - identity → 1;
   - a 1-voxel dilation leaves recall and naming at 1;
   - D1↔D2 and PDA↔PLB swaps → naming 0, recall 1;
   - OM2 → LCx → detected but not named;
   - OM2 erased → recall 0;
   - the collapse equals D25 on every non-"Other" voxel.
3. **Contact collapse** (`label_checks.py`, SegQueue's `collapse_to_four` imported).
   - Inputs: 1-F's PDA = R-PDA ∪ L-PDA and PLB = R-PLA ∪ L-PLA, on all 720 maps.
   - 1 513 components decided, 109 of them to the LCx.
   - **0 fallbacks and 0 voxels on the wrong side.** On ImageCAS-X the contact rule and the origin labels are the same
     partition.
4. **Band** (120 hash-chosen training cases).

   | Band | Released (union of LAD, LCx, RCA) | Share of a 256³ patch | Covers a D/OM-sized branch (median share of its voxels) |
   |---|---|---|---|
   | 8 mm | 90k mm³ | ≈ 4 % | 0.37–0.45 |
   | 15 mm | 298k mm³ | ≈ 14 % | 0.75–0.92 |
   | 25 mm | 803k mm³ | ≈ 38 % | 1.00 |

   - R-PDA and R-PLA run 31–35 mm from the RCA trunk (p90), as long distal vessels do.

## What it changes

All four go into [[Candidates/Janus 1-F/Delta v2|Delta v2]]:
- **Gates:** B1 recall 0.80 → 0.75 and B2 naming 0.85 → 0.80 (§1).
- **Scorer:** `branch_score.py` is the scorer of record, with SegQueue's collapse imported, not re-implemented (§2).
- **Q1 switches:** the (B)/(C) switches are deleted (§2).
- **Band:** 15 mm per host (§4.2).

**Limitation of the simulation.** For D1–OM2 the simulated reader agrees on presence 0.01–0.03 more than Table 1,
because an extra branch usually renames a sibling. The 1.5× rows bracket this.
