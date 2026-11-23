---
tags: [plans, experiment, janus-1-l, round-3, gate, commands, calibration, spacing, cpu]
author: Crucible
track: 1-L
round: 3
updated: 2026-11-23
issue: christianGRogers/Asclepius#302
code: experiments/Crucible/j1l_r3/
---

# Janus 1-L round 3: the collect gate is written and mutation-tested, the 0.45 mm view check runs on the 620, and calibration is a grid question

For [[Candidates/Janus 1-L/Crucible v3|Crucible v3]], answering [[Janus 1-L Round 2]] §5 items 3, 4 and 6 without
Step T or Job 0. CPU only. No locked-100 number, no sealed or quality-0 label, no image. Nothing ran on Fir, SciNet or
Trillium.

## 1. The `collect` gate (`gate.py`, `pipeline_check.py`)

**Question.** L-A17 says `decide.py gate` is not the gate, and L-A21 asks for `collect`'s gate per L-A16 and L-A17,
with self-tests that fail on a broken fixture. D49 Q-R2-3 adds a Dice clause to Q4. Does a gate exist that implements
all of it, and do the merged scripts chain into it?

**Setup.** `gate.py` reads only r9-scorer JSONs and the frozen JSONs. Self-tests on synthetic rows. `pipeline_check.py`
chains synthetic nnU-Net outputs through an emulation of `nnUNetv2_ensemble --save_npz` (read from nnU-Net 2.8.1's
`ensemble.py`), `threshold_export.py`, `decide.py select`, `rule_t.py` and the gate, then runs six broken copies of the
gate against its own self-test.

**Result.**
- 14 self-tests pass, including L-A21 #9's fixtures (uniform −0.03 LCx recall fires L3; heavy-tailed null fires on 4.0 %
  of draws over four classes; −0.017 → not adopted, −0.012 → adopted via Q4; FP 1.2 fails H1) and D49's (Dice shown
  worse → not adopted). Three trees flipping to cut (mean −0.024) does not fire L3, though it fires G3 as written.
- **Mutation test: all six broken gates are killed** (Q-R2-3 removed; Q4 at −0.02; FP out of H1; L3 → G3 as written;
  class guard dropped; S's α = C's).
- **Three seam defects**, each of which would have stopped a job:
  1. `rule_t.py` needs C exported at every t of its grid (0.60 … 0.25); Rule W's list (0.50 … 0.30) makes it stop;
  2. `nnUNetv2_ensemble` writes no `.npz` without `--save_npz`, and `threshold_export.py` then exits;
  3. `nnUNetv2_move_plans_between_datasets` writes into dataset 718's preprocessed folder without creating it
     (batchgenerators' `save_json` is a bare `open`).
- Every script's self-test (threshold_export, decide, rule_t, error_decomp, r9 scorer) passes here.

**Operating characteristics** (`gate_oc.py`, 300 draws per cell, synthetic paired data; per-case SD of Δ tF1 0.038 or
0.055, of Δ Dice 0.012 or 0.020, both assumed):
- with width matched, Q-R2-3 refuses 1–2 % of otherwise-adopted candidates;
- with a true Dice loss of 0.005, it refuses 57–93 %;
- S's 1.25 % look adopts 3–9 points less often than C's.

**What it changes.** The gate of record exists (R3-A1). Rule T's 0.05 grid residual now matters under Q-R2-3, so Crucible
v3 proposes a 0.025 grid (R3-A8). The command block passes the full grid, `--save_npz` and the `mkdir`.

## 2. The 115 mm view check (`s045.py`)

**Question.** If Job 0 sets the grid trigger, S could train at 0.45 mm. A 256³ patch then spans 115.2 mm, not 128 mm.
How much of a coronary tree can one patch hold at each view?

**Setup.** The 620 D45 training labels (public ImageCAS-X release), fetched by name one file at a time. Per case:
cover(v), the largest share of the tree's labelled voxels in one axis-aligned v-mm cube (summed-area table, 2 mm cells).
**Rule fixed before the run:** PASS if the median cover at 115.2 mm is within 0.05 of that at 128 mm, and the 10th
percentile within 0.08.

**Result.**

<!-- VIEW -->

## 3. Calibration is a grid question (`calib_equiv.py`)

**Question.** L-A23 says that if Job 0 shows rim miscalibration, round 3 fits a temperature and maybe re-runs Rule W on
calibrated probabilities. Can a temperature give a mask Rule W could not already give?

**Result.**
- A binary temperature on the summed vessel probability is monotone, so its masks at t equal the raw masks at
  t′ = σ(T·logit(t)): identical on every voxel, T ∈ {0.7, 0.85, 1.2, 1.5}.
- A 5-class temperature on the saved probabilities differs from the best raw threshold on at most 0.4–1.1 % of rim
  voxels (synthetic rim with 20 % branch-point splits).

**What it changes.** No temperature step. If t\* lands at the grid's edge (0.30), extend Rule W's grid on the tuning
60 (and Rule T's with it). FP rising at every t < 0.50 cannot be calibrated away; t\* = 0.50 stands (R3-A5).

## 4. Limits

- The Dice SDs in the operating characteristics are assumed. No paired Δ Dice SD exists outside the locked 100.
- The view check uses label extent, not image context: it measures how much tree one patch can see, not how much
  aorta or myocardium.
- `nnUNetv2_ensemble` was emulated from its source, not run (no GPU stack here).
