---
tags: [experiment, janus-1f, round4, stage2, freeze, partial-labels, D27, D45, D47, D54, D55]
author: Atlas
updated: 2026-11-28
issue: christianGRogers/Asclepius#303
code: experiments/Atlas/j1f_r4/
---

# Atlas - Janus 1-F round 4, under D54 an extended read is a full label and the J1F-2 freeze is one script

For [[Candidates/Janus 1-F/Atlas v4|Atlas v4]].

**Data:**
- CPU work on **60 of the D45 training 620**, labels only, chosen by the smallest
  sha256(`asclepius-j1f-r4-atlas-standin:` + id). `fetch_subset.py` asserts the 620's pin.
- Seal, reserve and D35 lists: names only.

**Not read:**
- no locked-100 label;
- no sealed, quality-0 or D60 case;
- no pool read;
- no TotalSegmentator twin;
- no model output.

**Where it ran:** nothing on Fir, SciNet or Trillium.

## Questions

1. Under D54 (an undrawn branch in an extended read is absent), what does stage 2's loss see on an extended read,
   compared with round 2's rule without the "complete" flag?
2. Can the J1F-2 freeze be one script that runs on a SegQueue14 export and computes every stage-2 number? It must
   produce the band per group, L1r's run length, L2d's gap, the L1r/K1r line, the read counts and the inter-read floor.
   It must refuse a sealed-pool patient.
3. Do its rules behave on stand-ins? A correct export should pass, and an export with a thief should stop.

## Setup

- **`dice_terms_d54.py`:** Foxtrot's `dice_terms.py` (round 2), with its `terms` unchanged, on 10 training cases.
  - Each case: a 64 mm cube on the proximal LAD, with a 30 mm synthetic septal of r = 0.6 mm.
  - The extended-read sample is built twice:
    - the old rule: LAD-group `{LAD-group, S1}`, the band on background;
    - D54: every voxel a singleton.
- **`make_standins.py`:** a SegQueue14-layout export from the 60 training cases.
  - The first 5 cases are four-class reads and the other 55 extended, so 110 extended reads and 10 four-class.
  - Stand-ins: D2 → S1, OM2 → SN off the LCx, a PLB touching the RCA → RMA.
  - Each child is drawn over its parent at the junction (D47 Q4).
  - Each case has a second read `__r2`: each branch piece is dropped into its parent with p = 0.10, and each class
    grows by one voxel with p = 0.30.
  - There are five fake sources. In the `thief` mode (20 cases), each first read also paints the 10 mm of LAD
    centreline nearest the S1 origin as S1.
- **`j1f2_freeze.py`:** the freeze (rules in its docstring, constants at module level). Its `selftest` checks the
  label rules, D54's sets, run lengths, refusals and rounding.
- **`test_refusals.py`:** six whole-export refusals, one of them with an `open()` spy.

## Results

**1. Loss under D54** (`results/dice_terms_d54.txt`; mean of 10; leaf-Dice loss LAD-group / S1, then CE):

| Extended-read scenario | Old rule | D54 |
|---|---|---|
| A, right | 1.000 / 0.342, 0.00069 | 0.079 / 0.479, 0.00079 |
| B, miss | 1.000 / 0.972, 0.00117 | 0.102 / 0.980, 0.00127 |
| C, S1 sprawled over the LAD group | 1.000 / 0.342, **0.00076** | 0.450 / 0.852, **0.00282** |
| D, OM1 intruding on the LAD group | 1.000 / 0.342, 0.00259 | 0.450 / 0.502, 0.00282 |

Under the old rule, C was free: +0.00007 CE over A, and no LAD-group Dice target at all. Under D54 it costs 3.6× A's
CE, and both Dice terms see it.

**2–3. The freeze on stand-ins:**

`j1f2_freeze.py` sha256 `d0715f78…8f72`; `results/freeze_standin_{normal,thief}.out` and
`results/standin_{normal,thief}_freeze.json`. The normal run took 13 min on 4 cores.

| Output | Correct stand-ins (60 cases, 120 reads) | Thief (20 cases, 40 reads) |
|---|---|---|
| status, exit | FROZEN, 0 | **STOP, 2** |
| band LAD / RCA / pLCx / pRCA | 21.5 / 25 (clamped from 46.8) / 25 (clamped from 36.5) / 15 (provisional, 0 reads) mm | 23.5 / 25 / 25 / 15 mm |
| τ₁; worst bound at 3 mm | 3.0 mm; 0.0063 | 6.0 mm; 0.041 |
| per-piece longest run q99 / max | 5.8 / 6.6 mm | 14.0 / 14.2 mm |
| L1r/K1r line | 0.02 | 0.075 (> 0.04: STOP) |
| τ₂; reads with a gap > 30 mm | 30 mm; 0 % | 30 mm |
| S1 patients / sources ≥ 5 / floor | 34 / 4 / 0.954 → train | 14 / 1 / 0.923 |
| SN | 23 / 3 / 0.905 → not (23 < 30) | 10 / 0 / 0.824 |
| RMA | 52 / 5 / 0.960 → train | 20 / 1 / 0.974 |
| `j1f2_freeze.json` sha256 | `e7b1dcbf…4aed` | `ef8390b3…3117` |

**Refusals** (`results/test_refusals.out`): 6 of 6 exit 3:
- a sealed volume's name, with 0 files of the export opened;
- its `__r2` replica;
- an acceptance-mode manifest;
- a four-class export;
- `--no-guard` on a pool name;
- the annotator benchmark.

## What it changes

- **Stage 2's labels.** Every voxel of an extended read is a singleton (P-r4-1). The marginal CE and leaf-Dice are
  needed only on ImageCAS-X and four-class background. Training now penalises theft on the pool's own reads.
- **The freeze is a computation, not a round.** The lead runs one CPU job on an export and posts a json and its
  sha256. Out-of-range numbers stop at the PM.
- **L1r's run length and its line are one rule.** It takes the smallest run length at which reads, scored as a correct
  model with one voxel of bleed, stay at half the line. A per-piece percentile rule would have moved τ₁ to 6 mm on
  these stand-ins (99th percentile of the longest run 5.8 mm, 17 of 65 S1 pieces over 3 mm) for no gain: the pooled
  share at 3 mm is ≤ 0.004.
- **Not settled here:** the stand-ins are ImageCAS-X branches renamed. Real septals, SN, conus and RMA, and real
  readers, set the numbers when the lead runs the freeze.
