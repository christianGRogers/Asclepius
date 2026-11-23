---
aliases: [Foxtrot j1l round 3 dry run and Rule T resolution]
tags: [plans, experiment, janus1-L, D45, D49, D50, rule-T, identity-check, calibration, cpu, phantom]
status: done (CPU, 2026-11-23)
issue: christianGRogers/Asclepius#302
track: 1-L
---

# The plan's own commands run end to end on phantoms, and Rule T resolves sub-voxel width shifts that a frozen t-star misses

**Question.** [[Janus 1-L Round 2]] §5 asks round 3 for three things:
- item 6: #306's commands, final, with each script's interface confirmed;
- item 4: what to do on a rim-miscalibration signal;
- D50 (2026-11-23): the exact commands of Trillium's identity check.

None of these needs Job 0's numbers. This note asks four questions:
1. Do the plan's command lines, as written, run end to end, and where do they break?
2. Does Rule T resolve the sub-voxel width shifts that the export threshold makes?
3. Can a calibration step reach a mask that Rule W cannot?
4. Does L0 as posted cover its third clause?

**Code.** Everything is in `experiments/Foxtrot/j1l_r3/`, CPU only:

| Script | Writes | Time |
|---|---|---|
| `chain_dryrun.py` | `chain_dryrun.json` | ≈ 3 min, 4 cores |
| `rule_t_resolution.py` | `rule_t_resolution.json` | ≈ 25 min |
| `calib_equivalence.py` | `calib_equivalence.json` | 13 s |
| `l0_check.py --selftest` | — | — |
| `j0t_trillium.sh` | the D50 job; dry-run tested inside `chain_dryrun.py` | — |

**Data.** No image, label or score of any real case is read. Every volume is a synthetic phantom. The case ids are the
plan's own, only because the scripts of record refuse every other id. None is sealed: `chain_dryrun.py` asserts this
against `trillium/sealed_test.json`.

## 1. The plan's command chain, run as written

**Setup.**
- 220 phantom cases (tuning 60, locked 100, D60) in Step T's layout: `$J0/icx`, `$J0/aorta`, `$J0/pred_fir` and
  `cases/<c>/ct.nii.gz`.
- Janus 0's "probabilities" are in nnU-Net 2.8.1's on-disk form: `<case>.npz` with `probabilities` in SimpleITK axis
  order, beside the argmax `<case>.nii.gz`.
- Fir's "predictions" are the same argmax, with 20 rim voxels flipped in two cases.

The script runs the lines of `job0_janus0_probs.sh` (steps 2–4) and the master plan's §5 blocks **verbatim**, as
subprocesses with the plan's variables. It then runs Rule T's exports, `rule_t.py` and the D50 job
`j0t_trillium.sh` with `DRYRUN=1`.

**Result: 24 of 24 steps behave as specified.**

| Step | Result |
|---|---|
| Job 0 tail: export, 5 tuning-60 scorings, `decide.py select`, the locked-100 baseline, the print block | all run |
| Identity: `split_val80.json`, r9 scorer `--pair` | runs. The `paired` block holds `case_ci`, `fp_diff`, `mean_diff_run2_minus_run1`, `n`, `seed_inclusive_ci` and `sigma_seed_estimate_1df`, **but not the share of cases within 0.01** (L0's third clause) |
| `l0_check.py --mode fir-determinism` | computes all three clauses. On phantoms, clauses 1–2 must fail (they are not Janus 0) and it exits 3. Clause 3: 80/80 within 0.01; the jittered case moved 0.0066 |
| The master plan's post-Job-0 line `T=$(python -c "...'%.2f' % ...['chosen_t']")` | **`TypeError: must be real number, not str`**. `decide.py` writes `chosen_t` as a string (`'0.35'`). With `float(...)` it works |
| `error_decomp.py` at 0.50 and at t\*; `mde_from_job0.py` | run. The decomposition iterates over the tuning 60 from `lists.json`, not over the 160-case folder |
| Rule T exports (Janus 0 at t\*, C at 8 t) and `rule_t.py` | run |
| J0T: a failing L0-T stops the job before Rule T's reference is written; a wrong `SELECT_SHA256` refuses; step 3 then `rule_t.py` gives the same t_C as above | all three as specified |

**Read from nnU-Net 2.8.1's wheel** (downloaded to the scratchpad, read, not installed):
- **`nnUNetv2_predict -f 0 1` averages logits.** `predict_logits_from_preprocessed_data` sums each fold's
  `predict_sliding_window_return_logits` and divides by the number of folds (l. 524–530). E in L-A14 is the mean
  softmax.
- **`nnUNetv2_ensemble` averages the saved `probabilities`** (`ensemble.py` l. 18–30). It writes the `.npz` only with
  `--save_npz` (l. 45–46, 122). It also takes `plans.json` and `dataset.json` from the first input folder, and asserts
  that every folder holds the same `.npz` set (l. 92–95).
- So E must come from `nnUNetv2_ensemble --save_npz` on folds predicted separately with `--save_probabilities`.
  L-A14's "equals `nnUNetv2_predict -f 0 1`" is wrong.

**A degenerate case of Rule T, found on these phantoms.**
- The dry-run phantoms are voxel-aligned tubes, and their wall moves in whole shells. On them, Rule T's 10 %-trimmed dr
  was **exactly 0 at every t ≤ 0.50**. It returned t\* (0.35) by its tie rule, where the oracle was 0.50.
- The reason: each centreline EDT is a minimum over directions, so a partial rim change moves only a few points
  (here 3–10 %), and the 10 % trim removes them.
- §2 shows that this does not happen on continuous geometry. It is still worth a report line, so that a degenerate D60
  result is named and not mistaken for "no drift".

## 2. Rule T's resolution on continuous geometry

**Setup.**
- **Phantoms:**
  - curved tubes (radius 2.6 → 0.8 mm) with an analytic distance to the axis, three per case, 12 cases per scenario;
  - 0.5 mm and 0.4 mm grids;
  - smooth logit noise (SD 0.3, σ = 2 voxels).
- **Probability:** p = sigmoid((R − dist − w)/soft). Thresholding at t puts the wall w + soft·logit(t) inside the true
  wall.
- **Janus 0:** w0 = 0.20 mm, soft 0.25 mm, t\* = 0.35. Its wall then sits 0.045 mm inside.
- **The oracle t** is exact: C's wall closest to Janus 0's at t\*, over t ≤ 0.50.
- **Rule T** is Delta's `case_diffs`, `trimmed` and `choose`, imported unchanged.
- **An alternative, built only to test Rule T against:** the shared-tube volume offset dV/A, which counts every rim
  voxel within (r + 1 mm) of the shared skeleton.

**Result.**

| Grid | Scenario | t oracle | t Rule T | t alt | Wall error (mm): Rule T | alt | frozen t\* |
|---|---|---|---|---|---|---|---|
| 0.5 mm | C = Janus 0 (no drift) | 0.35 | 0.35 | 0.35 | +0.000 | +0.000 | +0.000 |
| 0.5 mm | C wider: C(0.50) = J0(t*) | 0.50 | 0.50 | 0.50 | +0.000 | +0.000 | -0.155 |
| 0.5 mm | C half way | 0.40 | 0.40 | 0.45 | -0.024 | +0.027 | -0.077 |
| 0.5 mm | C wider than J0(t*) | 0.50 | 0.50 | 0.50 | -0.100 | -0.100 | -0.255 |
| 0.5 mm | C thinner than J0 | 0.30 | 0.25 | 0.30 | -0.040 | +0.023 | +0.080 |
| 0.5 mm | C softer rim (0.35) | 0.40 | 0.40 | 0.40 | +0.013 | +0.013 | -0.062 |
| 0.5 mm | C wider + extra branch | 0.40 | 0.40 | 0.40 | -0.024 | -0.024 | -0.077 |
| 0.5 mm | C wider + missing distal | 0.40 | 0.40 | 0.45 | -0.024 | +0.027 | -0.077 |
| 0.4 mm | C = Janus 0 (no drift) | 0.35 | 0.35 | 0.35 | +0.000 | +0.000 | +0.000 |
| 0.4 mm | C wider: C(0.50) = J0(t*) | 0.50 | 0.50 | 0.50 | +0.000 | +0.000 | -0.155 |
| 0.4 mm | C half way | 0.40 | 0.40 | 0.45 | -0.024 | +0.027 | -0.077 |
| 0.4 mm | C wider than J0(t*) | 0.50 | 0.50 | 0.50 | -0.100 | -0.100 | -0.255 |
| 0.4 mm | C thinner than J0 | 0.30 | 0.25 | 0.30 | -0.040 | +0.023 | +0.080 |
| 0.4 mm | C softer rim (0.35) | 0.40 | 0.35 | 0.40 | -0.062 | +0.013 | -0.062 |
| 0.4 mm | C wider + extra branch | 0.40 | 0.40 | 0.45 | -0.024 | +0.027 | -0.077 |
| 0.4 mm | C wider + missing distal | 0.40 | 0.40 | 0.40 | -0.024 | -0.024 | -0.077 |

Summary over the 16 rows: Rule T mean \|error\| 0.031 mm (worst 0.1, exact hits 13/16); alternative 0.027 mm (worst 0.1, 12/16); frozen t\* 0.098 mm (worst 0.255, 2/16).

**Reading.**
- **Rule T recovers the oracle t to within one grid step in every scenario,** including an extra branch drawn only by
  C and a distal piece C misses. Its wall error stays a few hundredths of a millimetre.
- **A frozen t\* leaves errors up to 0.255 mm** whenever C's width differs from Janus 0's.
- **The alternative is about the same** (0.027 against 0.031 mm mean, one fewer exact hit). So nothing in Rule T needs to change.
- In the "C wider than Janus 0 at t\*" scenario, no t ≤ 0.50 can thin C, and every rule keeps the −0.100 mm that is
  left. That is the "export lever only widens" scope, as written.
- **The share of shared points with dr exactly 0** is 3–46 % at t = 0.50 on continuous geometry, below the level
  (> 90 % on one side) at which the trim blinds the rule. On the voxel-aligned phantoms of §1 it passed that level. The
  report line asked for in Foxtrot v3 (F5) prints it.

## 3. Calibration cannot reach a mask Rule W cannot

**Setup.** 400 000 synthetic rim voxels with 5-class logits:
- the dominant vessel's logit spans the wall;
- three minor vessels sit 2.5–8 logits below it;
- 5 % are junction voxels, where two vessels compete.

**Platt or isotonic calibration of p_fg** is increasing in p_fg, so each calibrated mask is exactly a raw-threshold
mask, {g(p) ≥ t} = {p ≥ g⁻¹(t)}.

**Temperature scaling** (T = 0.7 to 2.0, t = 0.45 to 0.25):
- argmax is unchanged at every T (asserted), so the 0.50 export cannot move;
- the calibrated mask differs from the nearest raw-threshold mask by **at most 2.06 %** of its voxels, typically
  0.4 %. The differences are junction voxels.

**What this changes:** a calibration step before Rule W adds at most a different grid. Foxtrot v3 therefore settles
§5 item 4 on the raw grid:
- extend Rule W to 0.25 and 0.20 if t\* = 0.30;
- otherwise no step.

## 4. L0's three clauses, and D50's two uses of L0

- **`l0_check.py` reads the r9 scorer's `--pair` file and prints all three clauses** with one verdict. Its self-test:
  - identical runs pass;
  - **5 of 80 cases off by 0.05 fail clause 3 while clause 1 passes** (the macro moves only 0.003). So the third clause
    catches what the posted `summary` cannot;
  - 4 of 80 pass;
  - a 0.012 shift fails;
  - an error row fails;
  - a locked-20 row or a file without `rows_pair` is refused.
- **`--mode`** names D50's two uses:
  - `fir-determinism`: Job 0 on Fir; Fir reproduces Fir;
  - `trillium-identity`: J0T, or Job 0 run on Trillium.
- **It exits 3 on FAIL,** so a `&&` chain stops.
- **`j0t_trillium.sh`** is D50's Trillium identity check. It also writes Rule T's reference (Janus 0 at t\* on D60),
  which no job of the plan of record produces, and the Trillium baseline's probabilities.

## 5. What this changes

In [[Candidates/Janus 1-L/Foxtrot v3|Foxtrot v3]]:
- §7 F1–F6: the interface fixes;
- §3: J0T and the single-cluster baseline;
- §5: no calibration step;
- §8: keep Rule T, with a report line for the degenerate case;
- Appendix A: the commands as tested.

**What it does not show:**
- that the scripts behave the same on real CT, where only Job 0 can tell;
- anything about Janus 0's real rim, t\* or the decomposition.

The phantoms check plumbing and resolution, not accuracy on patients.
