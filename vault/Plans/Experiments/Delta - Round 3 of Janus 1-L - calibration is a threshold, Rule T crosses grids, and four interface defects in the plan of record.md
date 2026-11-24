---
tags: [plans, experiment, janus1-L, track-1L, round3, calibration, threshold, transfer, nnunet, interfaces, gate]
author: Delta
round: 3
track: 1-L
updated: 2026-11-23
issue: christianGRogers/Asclepius#302
code: experiments/Delta/j1l_r3/
---

# Round 3 of Janus 1-L: calibration is a threshold, Rule T crosses grids, and four interface defects in the plan of record

All CPU, all synthetic. No image, label, sealed case or locked-100 number was opened. It serves
[[Candidates/Janus 1-L/Delta v3|Delta v3]], items 3, 4 and 6 of [[Janus 1-L Round 2]] §5.

## 1. Does calibrating Janus 0 give Rule W anything a threshold does not? (item 4)

**Question.** L-A23 sends a temperature check on the tuning 60 to round 3 if Job 0 shows rim miscalibration, and asks
whether Rule W should then be re-run on calibrated probabilities.

**Setup.** `calib_equiv.py`:
- a phantom tree, 48 × 48 × 96 voxels at 0.5 mm, with five-class logits;
- an RCA tube, and a left trunk that splits into LAD and LCx, with an ambiguous stretch where the two share the mass;
- soft rims (0.45 mm per logit unit), logit noise (SD 0.35), and one dim blob as an FP component;
- temperatures T ∈ {0.5, 0.7, 0.85, 1.0, 1.25, 1.5, 2, 3} and Rule W's grid {0.50 … 0.30}.

**Results.**

| Claim | Result |
|---|---|
| A. softmax(log p / T) = softmax(z / T): a temperature can be fitted to saved probabilities | True (atol 1e-5) |
| A. argmax is invariant to T | True for all 8 T. "Calibrate, then argmax" is Janus 0 at argmax |
| B. Binary: {σ(l/T) ≥ t} = {p ≥ σ(T · logit t)} | Exact (200 000 draws × 40 pairs). For example, T = 1.5 warps the grid to {0.50, 0.43, 0.35, 0.28, 0.22} |
| C. Five-class T against the best raw threshold (fine search, step 0.0025) | Dice ≥ **0.972** for T ∈ [0.5, 1.5]; ≥ 0.943 at T = 2; 0.881–0.932 at T = 3 |
| C. Where they disagree (T = 2, t = 0.40) | 931 of 11 137 voxels. Median top-vessel share 0.64 there, against 0.999 over the mask: the voxels where vessel classes split the mass |
| D. The FP blob in the calibrated mask ⇔ in the matched raw mask | 40 of 40 pairs agree |
| E. Platt on the foreground logit is exactly a threshold | True: σ(a · logit p + b) ≥ t ⇔ p ≥ σ((logit t − b)/a) |

**Reading.**
- A foreground calibration (temperature or Platt) only re-labels Rule W's grid points. A five-class temperature
  nearly does the same.
- Its one extra freedom is an artefact: summing four tempered classes inflates voxels whose mass is split between
  vessel names.
- No calibration lifts an FP-bound t\*.
- **So Rule W is not re-run on calibrated probabilities.**
- `calib60.py` is a report. It gives T, Platt (a, b), ECE, t_half = σ(−b/a), and t_F = σ((logit(F\*/2) − b)/a), the
  F1-optimal point of a calibrated score (Lipton et al., arXiv:1402.1892). Its self-test recovers a known
  (a, b) = (0.625, 0.8) as (0.626, 0.802), and it refuses a locked-100 id.

## 2. Do t\* and Rule T carry to a 0.45 mm run? (item 3)

**Question.** If S ran at 0.45 mm, could t\* and Rule T still be used?

**Fact (nnU-Net 2.8.1, read from the wheel).**
- `export_prediction.py` resamples the logits and probabilities to the CT's own geometry
  (`resampling_fn_probabilities`, then `revert_cropping_on_probabilities`) before `np.savez_compressed(...,
  probabilities=...)`.
- So any network's saved probabilities, exports and scores share the native grid.

**Setup.** `grid045_phantom.py`:
- `transfer_phantom.py`'s trees (seed 21; 8 tuning, 8 drift, 8 locked), with the native grid 0.35 × 0.35 × 0.5 mm;
- Janus 0's probability on 0.5 mm and S's on 0.45 mm, each interpolated (order 1) to native;
- `rule_t.py`'s own `case_diffs`, `trimmed` and `choose` on the drift trees, unlabelled.

| S at 0.45 mm | t\* | Rule T | Oracle | Locked Dice: frozen / Rule T / oracle |
|---|---|---|---|---|
| Same rim | 0.40 | 0.40 | 0.40 | 0.9801 / 0.9801 / 0.9801 |
| Width gain (b = 0.03 mm) | 0.40 | 0.45 | 0.45 | 0.9531 / 0.9832 / 0.9832 |
| Sharper (τ × 0.7) | 0.40 | 0.40 | 0.40 | 0.9811 / 0.9811 / 0.9811 |
| Softer (τ × 1.4) | 0.40 | 0.40 | 0.45 | 0.9592 / 0.9592 / 0.9766 |
| Softer, 0.025 grid (`grid045_finegrid.py`) | 0.40 | 0.425 | 0.425 | 0.9592 / **0.9813** / 0.9813 |
| Width gain, 0.025 grid | 0.40 | 0.45 | 0.45 | 0.9531 / 0.9832 / 0.9832 |

**Reading.**
- A grid change alone does not move t.
- Rule T recovers the oracle whenever t should move, except at the 0.05 step in the softer case. There its two
  neighbours have |dr| 0.024 and 0.025 mm, with the oracle between them. A 0.025 step recovers it.
- So the carry is not an obstacle to a 0.45 mm S. Delta v3 keeps S at 0.5 mm for a different reason: S answers the
  warm-start question, and a grid change would confound it.
- Delta v3 adopts the 0.025 step for Rule T on C as well (D3-4).

**Limits.**
- One phantom family.
- The rim model is a sigmoid of distance.
- No real network's 0.45 mm probabilities exist.
- The view check (does the tree fit 115.2 mm?) needs labels and was not run here.

## 3. Do the merged scripts chain as the plan's commands assume? (item 6)

**Setup.** `chain_check.py` ran on synthetic fixtures in scorer and nnU-Net formats:
1. `decide.py select`;
2. the master plan's t\* line;
3. `rule_t.dice_bound`;
4. `threshold_export.py` on Rule T's grid;
5. `rule_t.run`;
6. `mde_from_job0.py`.

**Results.**
- Every step runs, and the folders match.
- One defect: `select.json` stores `chosen_t` as a string (`"0.40"`), so the master plan's `'%.2f' % …['chosen_t']`
  raises `TypeError` (returncode 1). `T` is then empty, and the t\* decomposition is silently skipped.
  `float(...)` fixes it.

**Also read in nnU-Net 2.8.1:**
- `nnUNetPredictor.predict_logits_from_preprocessed_data` sums the folds' **logits** and divides. So `nnUNetv2_predict
  -f 0 1` is a logit average, not E's mean softmax.
- `nnUNetv2_ensemble` averages saved probabilities, and writes an npz only with `--save_npz`.
- `move_plans_between_datasets` defaults `-tp` to `-sp`.

## 4. A reference gate for `collect` (item 6)

`gate.py` implements:
- H1 (macro −0.02, class −0.03, L3 on `recall`, FP ≤ 1);
- H2 and H3 in sequence;
- the Q4 branch with D49's "Dice not shown worse";
- the S trigger;
- α as a parameter.

| Fixture | Result |
|---|---|
| Uniform −0.03 LCx recall loss | L3 fires, H1 fails |
| Heavy-tailed (t₂) null, 40 draws | L3 fired 0 times |
| Lower bound −0.0173, H2 failing | Not adopted |
| Lower bound −0.0123, H2 failing | Adopted (Q4) |
| Same tF1, Dice upper bound < 0 | Not adopted (Q-R2-3) |
| FP 1.2 per case | H1 fails |
| Dice gain | H1 + H2, adopted |
| Members −0.01 / −0.005 against −0.01 / +0.005 | S fires / does not |
| α 1.25 % against 2.5 % | Wider bound |

## 5. What it changes

- **Item 4:** Rule W is never re-run on calibrated probabilities (D3-2). Rule W gets a pre-registered edge extension
  to 0.25 (D3-3).
- **Item 3:** S is 0.5 mm (D3-1). Rule T's step becomes 0.025 (D3-4).
- **Item 6:** F1–F4 are fixed in the command block (D3-5). `gate.py` is the reference for `collect`.

## Files

`experiments/Delta/j1l_r3/`:
- `chain_check.py` → `chain_check.json`;
- `calib_equiv.py` → `calib_equiv.json`;
- `calib60.py` (tool, `--selftest`);
- `grid045_phantom.py` → `grid045_phantom.json`;
- `grid045_finegrid.py` → `grid045_finegrid.json`;
- `gate.py` (`--selftest`);
- `l0_trillium.sh` (D50's identity check, for the lead).
