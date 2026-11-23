---
tags: [plans, candidate, janus1-L, track-1L, round3, trillium, four-class, D45, D46, D49, D50, locked100, ensemble, convergence]
author: Delta
track: 1-L
round: 3
version: 3
updated: 2026-11-23
issue: christianGRogers/Asclepius#302
---

# Delta v3 (track 1-L): not converged, for one reason only. Job 0 has not run. Everything else is settled, and the plan is written through as one text (Part B)

## 0. Position and the convergence verdict

**I accept the round-2 ruling.** Delta v2 as amended (L-A13 to L-A25) is the plan, on top of L-A1 to L-A12, D46,
**D49** (the lead's yes to Q-R2-1 to Q-R2-4) and **D50** (Job 0 may run on Fir, with a Trillium identity check
before training). This version contradicts none of them.

**Can round 3 rule the plan converged? No.** [[Janus 1-L Round 2]] §5 makes items 1 and 2 preconditions:

| §5 item | Status | Delta v3's answer | Where |
|---|---|---|---|
| 1. Step T and Job 0 run, outputs on #302 | **Not met.** Step T is done and posted (#302, 2026-11-23): SHA256SUMS with the fingerprint, verified on Trillium; 0 class-weighted-CE lines in all three logs; no `ce_class_weights.json`. **Job 0 has not run**, so L0, `select.json`, the decomposition and the MDE do not exist | The L-A23 table is applied to Step T's rows now (§1). Job 0's rows are mapped outcome by outcome (§1.2) and read by the next round | §1 |
| 2. The lead's answers | **Met** (D49, all four yes) | Written through: E ships (Q-R2-1), Rule T on D60 (Q-R2-2), Q4 with "Dice not shown worse" (Q-R2-3), S allocated (Q-R2-4) | Part B |
| 3. S's form | **Settled: 0.5 mm, whatever Job 0 shows** | S answers the warm-start question. The 0.45 mm grid is a width lever, and it would confound that answer. The full 0.45 mm specification is given anyway, with CPU evidence that t\* and Rule T carry across grids | §2 |
| 4. Calibration | **Settled as a rule** | Rule W is never re-run on calibrated probabilities. A calibration is (exactly, or nearly) a threshold on a warped grid, and Rule W already searches the thresholds (CPU proof and phantom). `calib60.py` is a report on L-A23's triggers. Two pre-registered grid refinements | §3 |
| 5. Class-weighted CE | **Settled by Step T: moot** | 0 of 3 logs show it and the file is absent, so the fine-tune keeps stock DiceCE and L-A2 stands | §4 |
| 6. #306's commands | **Settled except the decomposition reading**, which needs Job 0's numbers | Every script's interface was confirmed by running the chain end to end on fixtures. Four interface defects are fixed (F1–F4). A reference `gate.py` is provided for `collect`. The full command block includes D50's identity check | §5, Part B §5 |
| 7. One consolidated plan | **Settled** | Part B: L-A1 to L-A25, D46, D49, D50 and this version's amendments, written through with no superseded clause | Part B |

**So the next round can rule "converged" on Job 0's posted numbers alone:** it applies §1.2's table row by row, and
reads the decomposition by L-A22. If no row fires a stop or a round-4 item, nothing else in the plan waits on it.

**Independence, stated plainly.**
- I did not open any `* v3.md` of this track, any `exp/j1l-r3-*` branch, or any file under
  `experiments/Atlas/j1l_r3/` or `experiments/Bridge/j1l_r3/`.
- Two things reached me anyway:
  - `git log` on dev showed the Atlas v3 and Bridge v3 commit titles;
  - when I read #302 for Step T's results, which were posted after this round began, the thread also held the
    Atlas v3 and Bridge v3 summary comments.
- My interface findings F1 (the `'%.2f'` line) and F2 (`predict -f 0 1` is not E) were committed before that read
  (`7ac25b0`, 2026-11-23 00:57 UTC; this session read #302 at about 06:30 UTC).
- F3 (`--save_npz`) is from my own read of nnU-Net 2.8.1's `ensemble.py`. The summaries name it too, so it is
  independent agreement, not a new finding.
- Where those summaries reach a conclusion I also reach (S at 0.5 mm, a Platt reading for calibration), my reasons
  and evidence are my own and are given below. Nothing from them is used as evidence here.

**New evidence this round** (CPU; `experiments/Delta/j1l_r3/`). No image, label, sealed case or locked-100 number
was opened. Every volume is synthetic.
- `chain_check.py`: the merged scripts chained end to end (`decide.py select` → the t\* line → `rule_t.dice_bound`
  → `threshold_export.py` on Rule T's grid → `rule_t.run` → `mde_from_job0.py`). It found F1.
- nnU-Net 2.8.1's own code, read from the wheel: F2 and F3. Probabilities are saved on the native grid.
- `calib_equiv.py`: calibration against thresholds (item 4).
- `grid045_phantom.py` and `grid045_finegrid.py`: t\* and Rule T across a 0.45 mm grid (item 3), and Rule T on a
  0.025 grid.
- `calib60.py`: the calibration report tool, self-tested.
- `gate.py`: a reference `collect` decision, with L-A21 test 9's fixtures and more.
- `l0_trillium.sh`: D50's identity check.

Note: [[Delta - Round 3 of Janus 1-L - calibration is a threshold, Rule T crosses grids, and four interface defects in the plan of record]].

## 1. Item 1: what has run, and L-A23 applied

### 1.1 Step T's rows (posted on #302, read now)

| Row (L-A20, L-A23) | Posted | Then |
|---|---|---|
| Fingerprint copied | Yes; in SHA256SUMS (`e41c772f…7e05`), verified OK on Trillium | P places it in the new preprocessed folder (L-A21) |
| Class-weighted CE in Janus 0's logs | **0** in each of the three `training_log_*.txt`; `ce_class_weights.json` absent | **No stop.** Item 5 is moot (§4) |
| `nnUNet_compile` | **Unknown.** Fir's copy of icx4's `job_body.sh` was not found; dev's copy (`f`) postdates Janus 0's training | Not a stop (§5.4): `f` is used everywhere, the D50 identity check runs under it, and the verdict lists it as unverified |
| `batch_dice` (3d_fullres) | `False` | Recorded. The fine-tune uses Janus 0's plans, so it inherits `False` and needs no setting |
| Transfer route | Fir → the lead's machine → Trillium as one tar (`c30cb01e…0b9b2959`); Fir has no key for Trillium | **The plan's `rsync` line is replaced** by this route (Part B §5.1). Trillium's login host is `trillium-gpu.scinet.utoronto.ca` |

### 1.2 Job 0's rows (not run; mapped now, read by the next round)

L-A23's table stands as written. Round 3 adds the D50 split and four rows:

| Job 0 result | Then |
|---|---|
| **Job 0 ran on Fir** (D50) | Its L0 is a determinism check only. **`l0_trillium.sh` runs on Trillium before P** (≈ 1 GPU-h, §5.3), with L0's three thresholds. If it fails, stop (L-A8). Its locked-100 argmax is the decision baseline (§5.3) |
| Job 0 ran on Trillium | Its L0 is the identity check. `l0_trillium.sh` is not run |
| L0 fails (either cluster) | Stop (L-A8). #306 is not built |
| t\* ∈ {0.45, 0.40, 0.35}, Dice-bound | The plan as written |
| t\* = 0.30, Dice-bound, and Dice(0.30) − Dice(0.35) > 0.002 (still rising at the edge) | **Rule W's grid is extended once to 0.25** on the tuning 60 (CPU, from Job 0's saved probabilities; same guards and ties), and `select.json` is re-frozen before #306 (§3.3). Calibration is read as a report (`calib60.py`) |
| t\* = 0.30 not at a rising edge, or FP rising at every t < 0.50 | Rim miscalibration (L-A23). `calib60.py` runs as a report. **Rule W is not re-run** (§3) |
| t\* held by a guard | t_C = t\* (L-A15). The guard is named. `calib60.py` runs as a report. If the guard is FP, no calibration can lift it (§3.1 D). A component-level FP lever goes to a later round |
| t\* = 0.50, Dice peaking at 0.50 | As L-A23: the export lever is empty, and the Q4 branch is the expected verdict. **S stays 0.5 mm** (§2) |
| Dice at t\* > 0.03 below 0.934, volume ratio ≥ 0.95 | As L-A23, but **S stays 0.5 mm** (§2). A 0.45 mm run goes to a later round as a width arm, with its own decision set |
| Dice(t\*) − Dice(0.50) < 0.003 on the 60 | Stated on #302 before training (L-A23) |
| Janus 0's locked-100 per-case SD | `mde_from_job0.py` restates the MDE. No margin moves |
| The decomposition | L-A22, for later rounds only |

**What each missing output would change, in one line each:**
- **L0's blocks:** whether anything proceeds.
- **`select.json`:** t\*, Rule T's scope, and whether §3.3's edge rule fires.
- **The decomposition summaries:** only which arm a later round may cost (L-A22).
- **The MDE printout:** the stated MDE and the "under-powered" clause.
- **F0** (Janus 0 on D60, if the lead runs it early): nothing. It is Rule T's reference, and it can run in `predict`
  instead.

## 2. Item 3: S's form is 0.5 mm, whatever Job 0 shows

### 2.1 Why

- **S has one job.** L-A18 triggers it only on the warm-start signature: H1 fails and both members are below
  Janus 0 at argmax. S answers "was the warm start the problem?" A 0.45 mm S would change the grid, the plans, the
  normalisation's resampling and the view as well. If S then passed, nobody could say whether the from-scratch start
  or the grid did it, and the next round would inherit a confounded result from the track's last look.
- **The grid triggers are a width question, not a warm-start question.** "t\* = 0.50" and "Dice at t\* 0.03 below the
  ceiling" say the 0.5 mm grid limits width. They say nothing about whether the warm start failed. A 0.45 mm run
  answers them, as its own arm, with its own decision set, after the verdict. The look budget (L-A18: two) leaves no
  room for it on the locked 100 in this track. That is a reason to keep it out of S, not to fold it in.
- **The view shrinks.** nnU-Net's 256³ patch at 0.45 mm sees 115.2 mm, against 128 mm at 0.5 mm. My own committed
  survey of the original ImageCAS masks (583 cases, aggregate only;
  [[Delta - The binary masks are two clean trees, and a tight tree ROI is only 2-3x smaller than the volume]])
  puts the tree's x-extent at a median of 110 mm and a p95 of 127 mm. So a material share of trees that fit one
  0.5 mm patch do not fit one 0.45 mm patch. I did not run a view check on ImageCAS-X labels: this container holds
  no labels. The decision does not rest on it.

### 2.2 The 0.45 mm specification, for the record (if a later round or the judge wants it)

- **Plans step:** a new fingerprint and plan on dataset 718, because the 0.5 mm plans cannot be moved to 0.45 mm.
  - `nnUNetv2_extract_fingerprint -d 718`, then `nnUNetv2_plan_experiment -d 718 -pl ResEncUNetPlanner
    -gpu_memory_target 60 -overwrite_target_spacing 0.45 0.45 0.45 -overwrite_plans_name
    nnUNetResEncUNetPlans_60G_iso045`. These are icx4's `prepare.py` flags with the spacing changed.
  - Then patch 256³ and batch 2, as icx4 forces them.
  - The 620 only in training. `refuse_sealed` as for P.
- **View check:** on the 620's ImageCAS-X labels (training cases, D45), the share of trees whose bounding box fits
  inside 115.2 mm on every axis, against 128 mm. It must be pre-registered before it is run. Its rule belongs to the
  round that proposes the arm.
- **t\* and Rule T carry unchanged** (`grid045_phantom.py`):
  - nnU-Net 2.8.1 saves probabilities after resampling them to the CT's native grid (`export_prediction.py`:
    `resampling_fn_probabilities`, then `revert_cropping_on_probabilities`). So a 0.45 mm model's exports, scores
    and Rule T radii live on the same voxels as Janus 0's.
  - The phantom: native grid 0.35 × 0.35 × 0.5 mm, Janus 0 on 0.5 mm, S on 0.45 mm, both interpolated (order 1) to
    native, `rule_t.py`'s own functions.

| S at 0.45 mm | t\* | Rule T (0.05 grid) | Oracle | Dice: frozen / Rule T / oracle |
|---|---|---|---|---|
| Same rim | 0.40 | 0.40 | 0.40 | 0.980 / 0.980 / 0.980 |
| Width gain (b 0.07 → 0.03 mm) | 0.40 | **0.45** | 0.45 | **0.953** / 0.983 / 0.983 |
| Sharper (τ × 0.7) | 0.40 | 0.40 | 0.40 | 0.981 / 0.981 / 0.981 |
| Softer (τ × 1.4) | 0.40 | 0.40 | 0.45 | 0.959 / 0.959 / 0.977 |
| Softer, Rule T on a **0.025** grid | 0.40 | **0.425** | 0.425 | 0.959 / **0.981** / 0.981 |

  - A grid change alone does not move t (row 1).
  - A frozen t\* loses 0.030 Dice when S gains width, and Rule T does not.
  - At the 0.05 grid step, Rule T misses one scenario: the two neighbouring points have |dr| 0.024 and 0.025 mm, and
    the oracle sits between them. A 0.025 step recovers it. This is §3.3's second refinement, and it applies to C
    too.
- **Cost:** ≈ 55–60 GPU-h (L-A25), plus ≈ 1 h of CPU for planning and preprocessing.

## 3. Item 4: calibration is a threshold, so Rule W is never re-run on calibrated probabilities

### 3.1 The evidence (`calib_equiv.py`)

A temperature divides the logits by T. The saved probabilities give the logits up to a per-voxel constant (log p), so
softmax(log p / T) = softmax(z / T) (checked), and a temperature can be fitted to Job 0's npz.

- **A. At argmax, a temperature changes nothing:** argmax(z / T) = argmax(z) for every T (checked on the phantom).
  "Calibrate, then export at argmax" is Janus 0 at argmax. It cannot fix a lumen that is drawn thin at argmax.
- **B. A foreground (binary) temperature is exactly a threshold:** {σ(l / T) ≥ t} = {p_fg ≥ σ(T · logit(t))}
  (checked on 200 000 draws). Rule W on calibrated probabilities with grid G is Rule W on the raw probabilities with
  the warped grid σ(T · logit(G)). For example, T = 1.5 maps {0.50 … 0.30} to {0.50, 0.43, 0.35, 0.28, 0.22}.
- **C. A five-class temperature is nearly a threshold:**
  - The phantom has soft rims, logit noise, and a bifurcation and an ambiguous trunk where LAD and LCx split the mass.
  - Each calibrated mask is reproduced by the best raw threshold to Dice ≥ 0.972 for T ∈ [0.5, 1.5], ≥ 0.943 at
    T = 2, and 0.881–0.932 at T = 3.
  - The disagreeing voxels are where the vessel mass is split (median top-class share 0.64, against 0.999 over the
    mask).
  - That is an artefact of summing four classes after tempering them, not a width correction. So it is not a lever
    to adopt.
- **D. No calibration removes an FP component that the matching threshold keeps.** In 40 of 40 (T, t) pairs, the
  dim blob is present in the calibrated mask exactly when it is present in the matched raw mask.
- **E. Platt scaling of the foreground logit,** σ(a · logit(p_fg) + b), is monotone in p_fg. So it is exactly a
  threshold too (checked). Its "calibrated 0.5" is the raw threshold σ(−b/a). The F1-optimal point of a calibrated
  score is F\*/2 (Lipton et al., *Thresholding classifiers to maximize F1 score*, arXiv:1402.1892), which maps to the
  raw threshold σ((logit(F\*/2) − b)/a). Both are points Rule W's grid already searches.

### 3.2 The rule (pre-registered)

- **Rule W is not re-run on calibrated probabilities**, under any Job 0 result. By §3.1, it would re-search the same
  family of masks on a warped grid. The one new freedom (row C) is an artefact of class-splitting.
- **`calib60.py` runs as a report, on L-A23's calibration triggers only** (t\* = 0.30, FP rising at every t < 0.50,
  or a guard-held t\*).
  - It fits T, and Platt (a, b), on the rim band of the tuning 60. Its inputs are Job 0's npz and the tuning 60's
    ImageCAS-X labels, which are training cases.
  - It prints ECE before and after, t_half = σ(−b/a), and t_F = σ((logit(F\*/2) − b)/a).
  - **Reading:** |t_F − t\*| ≤ 0.05 says t\* is the calibration's own F1 point, a global miscalibration that the
    threshold already fixes. Otherwise the report says Rule W's choice is not explained by a global miscalibration.
    It is local rim shape, which Rule T, not a temperature, carries to C.
  - **It decides nothing.** It refuses every case outside the tuning 60, and any sealed case (self-tested).
- **Rule T is the calibration transfer.** A candidate whose rim is calibrated differently from Janus 0's is exactly
  what Rule T measures, on D60, label-free (L-A15).

### 3.3 Two grid refinements (amendments D3-3, D3-4)

1. **Rule W's edge.** If t\* = 0.30 is Dice-bound and Dice(0.30) − Dice(0.35) > 0.002, Rule W is re-run once with
   0.25 added. This is the floor Rule T's grid already has. Same guards, same ties, on the tuning 60, from Job 0's
   saved probabilities (CPU: `threshold_export.py --t 0.25` and one scorer run). `select.json` is re-frozen and its
   new sha256 posted before #306 is built. It is fixed now, before Job 0, so it cannot be chosen on Job 0's numbers.
   It never reads the locked 100.
2. **Rule T's step is 0.025** (0.600, 0.575, …, 0.250; chosen only ≤ 0.50), not 0.05 (§2.2's softer row). The ties
   rule (0.005 mm, then t\*, then the larger t) is unchanged.
   - **Interface:** `threshold_export.py` names folders `t{t:.2f}`, which rounds 0.425 to `t0.42` (unique on this
     grid, but lossy). #306 passes the grid to both `threshold_export.py` and `rule_t.py` and names folders
     `t{t:.3f}`. `rule_t.py`'s `GRID` and its folder format change together, in one place, with a self-test that the
     15 folders exist.
   - **Cost:** 15 rather than 8 exports per model on D60 (CPU, a few GB).
   - **Exports at t_C off the 0.05 grid:** C's locked-100 export at t_C, and Janus 0 at t_C for the share sentence,
     are made in `collect` from the saved probabilities. That is why `predict` keeps the locked-100 npz until
     `collect` ends (Part B §5.6).

## 4. Item 5: class-weighted CE. Moot

Step T posted 0 "class-weighted CE" lines in each of Janus 0's three training logs, and no `ce_class_weights.json`.
icx4's hook (`icx4_trainers.py` `_build_loss`) logs that line at every chunk start when the file exists. So Janus 0
trained with stock DiceCE in every chunk.

- The fine-tune keeps stock DiceCE.
- L-A21 self-test 6's assertion "CE weight None" is the check.
- L-A2's "no class weights" stands.
- Nothing is added and no recipe change is accepted.

The conditional rule (Round 2 §5 item 5) is closed. For a later reader: had the logs shown weights, the fine-tune
would have taken the weights in force in Janus 0's last chunk, because the warm start sits in that loss's optimum,
and S would have followed Janus 0's per-chunk schedule.

## 5. Item 6: the scripts' interfaces, confirmed, and the defects fixed

### 5.1 Confirmed by running them (`chain_check.py`, fixtures only)

| Script | Interface confirmed | Note |
|---|---|---|
| `Crucible/j1l_r1/decide.py select` | `--scores t0.50=FILE …` → stdout JSON: `per_threshold` keyed `'0.50'`…, `chosen_t` a **string** (`'0.40'`) | Not the gate (L-A17) |
| `Crucible/j1l_r1/threshold_export.py` | `--probs DIR --out DIR --t …` → `OUT/t{t:.2f}/<case>.nii.gz` + `voxels.json`. Reads `probabilities` in nnU-Net's order beside `<case>.nii.gz` | Works on `nnUNetv2_ensemble` output (`probabilities` key, argmax seg) |
| `Delta/j1l_r2/rule_t.py` | `--j0 DIR --cand DIR --select FILE --out FILE --np N`. Reads `j0/t{t*:.2f}` and `cand/t{t:.2f}` for its grid; refuses non-D60 or sealed ids | `dice_bound` reads `per_threshold['0.40']['dice']` (string keys): works |
| `Delta/j1l_r2/mde_from_job0.py` | one positional path → stdout JSON. Reads `rows[].per_class`, `flagged_classes`, `provisional`, `dice.tree` | — |
| `Bridge/j1l_r2/error_decomp.py` | `--pred DIR --icx DIR --aorta DIR --layout FILE --np N --out FILE`. Tuning 60 only; self-test passes | — |
| `Atlas/r9_score_icx4.py` | `--pred --icx --aorta --layout --splits --set val --out [--pair]`; rows as above plus `recall`, `fp_components` | — |
| `Delta/j1l_r3/gate.py` | `--base --cand [--alpha] [--a1 --a2 --l0-pass]` → verdict JSON | Reference for `collect` (§5.5) |

### 5.2 Defects in the plan of record, and their fixes (amendment D3-5)

- **F1. The post-Job-0 t\* line fails.**
  - Master plan §5: `T=$(python -c "…print('%.2f' % json.load(…)['chosen_t'])")` raises `TypeError: must be real
    number, not str`, because `chosen_t` is a string.
  - Then `T` is empty, and `for t in 0.50 $T` runs once. **The decomposition at t\* is skipped silently.**
  - Fix: `float(json.load(…)['chosen_t'])` (checked).
- **F2. `nnUNetv2_predict -f 0 1` is not E.**
  - nnU-Net 2.8.1's `predict_logits_from_preprocessed_data` sums and divides the **logits**.
  - `nnUNetv2_ensemble` averages the saved **probabilities**: E's definition, the mean softmax.
  - L-A14's sentence "`nnUNetv2_ensemble` … equals `nnUNetv2_predict -f 0 1`" is withdrawn. **E is defined as
    `nnUNetv2_ensemble`'s output**, and never substituted.
- **F3. `nnUNetv2_ensemble` writes probabilities only with `--save_npz`** (`save_merged_probabilities`). Without it,
  E has no npz and neither Rule T nor the t_C export can run. `predict` passes `--save_npz`.
- **F4. Rule T's exports are not in any job.** Job 0 exports only Rule W's five thresholds, and Rule T reads its own
  grid. `predict` exports Janus 0 at t\* on D60, and C (and a1, a2 as reports) on Rule T's whole grid on D60 (Part B
  §5.6).

### 5.3 D50: the Trillium identity check, and the baseline

- If Job 0 ran on Fir, `experiments/Delta/j1l_r3/l0_trillium.sh` runs on Trillium before P (≈ 1 GPU-h).
  - Janus 0 re-predicts the locked 100 exactly as Job 0 does, with probabilities.
  - L0 is scored on the val-80 part only, against Fir's own predictions, with L0's three thresholds.
- **The decision baseline is then this Trillium run's argmax export** (pre-registered now). It is Janus 0 at argmax,
  as L-A5 says, on the cluster and software stack the candidate is predicted on. Its probabilities give "Janus 0 at
  t_C" for the share sentence without moving Fir's npz.
- If Job 0 ran on Trillium, Job 0's file is the baseline, as before.
- Either way, `mde_from_job0.py` reads Job 0's locked-100 file. L-A7 allows it: it is not a candidate look.

### 5.4 `nnUNet_compile`

Janus 0's training setting is unknown. That does not block anything:
- It changes the training graph's compilation, not the recipe's settings.
- The fine-tune and every prediction use `nnUNet_compile=f`, as icx4's dev launcher and Job 0 do.
- The D50 identity check is run under `f`, so it shows directly whether Trillium's inference reproduces Fir's.
- The verdict lists "Janus 0's `nnUNet_compile` at training: unverified".

### 5.5 `collect`'s gate: `gate.py`, a reference

`collect` implements L-A5, L-A16, L-A17 and D49 Q-R2-3. `gate.py` states that logic in 150 lines, so #306 can be
tested against it.

- **H1:** macro lower bound > −0.02; class means ≥ −0.03; L3 on `recall` (trimmed mean, or mean with upper bound);
  FP ≤ 1.
- **H2 and H3**, in sequence.
- **The Q4 branch:** lower bound > −0.015 **and** the upper bound of Δ Dice ≥ 0.
- **The S trigger:** H1 fails, both members' point Δ < 0 at argmax, and L0 passed.
- **α** as a parameter: 2.5 % for 1-L.1, 1.25 % for S.
- **Reports:** G5's classes and the excess kurtosis.

Self-tests (L-A21 test 9, plus four more):
- a uniform −0.03 LCx recall loss fires L3, and a heavy-tailed null fired it 0 times in 40;
- lower bound −0.0173 with H2 failing → not adopted; −0.0123 → adopted (Q4);
- the same tF1 with Dice shown worse → not adopted (Q-R2-3);
- FP 1.2 fails H1;
- H1 + H2 → adopted;
- S needs both members below Janus 0;
- the 1.25 % bound is wider.

It is a reference, not the launcher. The wording strings stay L-A16's.

### 5.6 The decomposition reading (L-A22)

No summaries are posted, so no group is read. The reading of record is L-A22's (ceilings ≥ 0.030, 0.015–0.030 with a
no-training test, < 0.015 none; the contrast-line rule for `distal`; LCx first). The next round applies it to the
two posted summaries. It decides nothing for Janus 1-L.1.

## 6. Amendments proposed (round 3)

| # | Change | Replaces |
|---|---|---|
| D3-1 | S is 0.5 mm, whatever Job 0 shows. A 0.45 mm run is a later width arm with its own decision set | L-A18's "round 3 decides its form"; L-A23's two "0.45 mm form of S" cells |
| D3-2 | Rule W is never re-run on calibrated probabilities. `calib60.py` is a report on L-A23's calibration triggers | Round 2 §5 item 4 |
| D3-3 | Rule W's edge: if t\* = 0.30 is Dice-bound and still rising, one re-run with 0.25 added, before #306 | L-A4's grid, in that case only |
| D3-4 | Rule T's step is 0.025 (0.600 … 0.250), with folders `t{t:.3f}` | L-A15's {0.50, 0.45, …, 0.25} |
| D3-5 | F1–F4 fixed in the commands. E is `nnUNetv2_ensemble --save_npz` only. L-A14's "equals `predict -f 0 1`" is withdrawn | Master plan §5; L-A14; L-A21's `predict` |
| D3-6 | D50: `l0_trillium.sh` before P when Job 0 ran on Fir. Its argmax export is the baseline. The Step T transfer is the tar route | L-A5's baseline source; master plan §5's `rsync` |
| D3-7 | Class-weighted CE closed (Step T: none). `nnUNet_compile=f`, listed as unverified for Janus 0's training | Round 2 §5 item 5; L-A20's open line |

## 7. What would change this plan

| Observation | Then |
|---|---|
| Job 0's rows (§1.2) | As §1.2 says. With no stop row and the decomposition read, the next round can rule "converged" |
| `l0_trillium.sh` fails while Fir's L0 passed | Stop (L-A8, D50). The PM diagnoses the Trillium stack (compile, versions, CT layout) before #306 |
| `calib60.py`: \|t_F − t\*\| > 0.05 | Report only. Rule T carries the width. No re-choice |
| Rule T's `rule_t.json` has no minimum inside the grid | t_C at the edge, stated (Delta v2 §10) |
| The judge prefers a 0.45 mm S | §2.2 is the specification. Then the view check's pass rule must be fixed before it is run |

## 8. Questions for the lead

None. D49 and D50 answered everything this plan needs. **Action, not a decision:** run Job 0 (Trillium or Fir, under
D50), then post the outputs Part B §5.2 lists.

---

# Part B. The consolidated plan text (item 7)

*Written through from L-A1 to L-A25, D45, D46, D49, D50 and Delta v3's D3-1 to D3-7. Where this text and an older
clause differ, this text is meant to replace the master plan as a whole.*

## B0. In force

- **Binding decisions:**
  - D45: the split; Trillium; the lead runs every job;
  - D46: Q1–Q8;
  - D49: Q-R2-1 to Q-R2-4;
  - D50: Job 0 may run on Fir, with a Trillium identity check before training;
  - D8 and D25: ImageCAS-X's lumen, four classes by territory;
  - D27 and D32: the seals;
  - D34: naming;
  - D35: pool questions only;
  - D40: overlaps become ignore, for pool reads.
- The main [[Master plan]] still governs the pool-driven work, D35 and the seal. Track 1-F (#303) shares only the
  split.

## B1. In one paragraph

**Janus 1-L is the ensemble E of two warm fine-tunes of Janus 0, a1 and a2, on D45's 620 ImageCAS-X cases.**
- The recipe: A17a, 250 epochs, peak LR 1e-2, Janus 0's plans (moved, equal except `dataset_name` and
  `image_reader_writer`), mirroring off, stock DiceCE.
- **E** is `nnUNetv2_ensemble --save_npz` of the two folds' saved probabilities (mean softmax).
- **Rule W** fixes Janus 0's thin lumen at export with a foreground threshold t\*, chosen on the tuning 60 and frozen
  before training.
- **Rule T** carries the width t\* gives (not the number) to E, by local radius on the shared centreline of D60.
  t_C is frozen before the look.
- **The locked 100 judge E at t_C against Janus 0 at argmax once:** H1 → H2 → H3.
- **Adopted when:**
  - H1 + H2 (better in width, tF1 non-inferior at 0.02); or
  - H1 alone with a lower bound > −0.015 and whole-tree Dice not shown worse (D46 Q4, D49 Q-R2-3).
- **One fallback,** a from-scratch 0.5 mm run S, pre-registered with its own look at 1.25 %.
- **Cost:** ≈ 33–36 Trillium GPU-h (≈ 1 of it only if Job 0 ran on Fir, D50), S only on its trigger.

## B2. Data (L-A1, D45, D49 Q-R2-2)

| Set | Cases | Use |
|---|---|---|
| Train 620 | ImageCAS-X train 560 + dev 44 + c0123 c0195 c0340 c0416 c0430 c0435 c0447 c0617 c0624 c0660 c0726 c0758 c0772 c0877 c0971 c0984 | Training (folds 0 and 1, identical entries) |
| ↳ tuning 60 | dev 44 + those 16; Janus 0 never trained on them | Rule W (Job 0), `calib60.py`, the decomposition. The 10 lowest ids are nnU-Net's fold val (in-sample display only) |
| Locked 100 | val 80 + c0068 c0102 c0251 c0271 c0323 c0327 c0470 c0545 c0592 c0620 c0644 c0805 c0807 c0824 c0827 c0841 c0908 c0946 c0957 c0996 | The one decision; L0 on its val 80. Never trained on, never used to choose anything, never nnU-Net's val |
| D60 | 60 ImageCAS quality-0 CTs (`experiments/Delta/j1l_r2/drift60.json`, pin `916e8a18…004e`) | Rule T only. **CT images only: no label or original ImageCAS mask read, nothing trained on them** (D49). `fetch_cases.py` without `--masks` |
| Sealed | ImageCAS-X test 80 + quality-0 20 | Never read, predicted, scored or trained on |

- **Pins:** sha256 of the sorted ids joined by `\n`:
  - locked 100: `bbd9c687818956e2d5664b06fd8c8bd02ddb031e9b9d08036d59cc0e1a4d5895`;
  - train 620: `1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152`.
- **File of record:** `experiments/Delta/j1l_r1/janus1_split_proposal.json` (`19b832fe…4dd3`), copied to
  `configs/janus1/split-2026-11.json` by #306.
- **Labels:** ImageCAS-X as drawn, `territory.to_four`, exactly as dataset 715.
- **Pool reads:** none in Janus 1-L (B8).

## B3. Recipe (L-A2, L-A14, L-A20, L-A21, D3-7)

| Item | Setting |
|---|---|
| Start | Janus 0 `checkpoint_final.pth` (Dataset715; sha256 `a0fb75de…ca43`), strict full load with heads, bitwise-checked |
| Trainer | `nnUNetTrainer_janus1l`: a thin subclass of `nnUNetTrainer_segtrain_finetune` whose `perform_actual_validation` returns at once |
| Plans | Janus 0's `plans.json` (`b7178bbc…3cc2`) copied to `Dataset715_ICX4/nnUNetResEncUNetPlans_60G_iso05.json` under `$nnUNet_preprocessed`, moved with `nnUNetv2_move_plans_between_datasets`, then `nnUNetv2_preprocess` only. Equal to Janus 0's except `dataset_name` and `image_reader_writer`. Janus 0's `dataset_fingerprint.json` (`e41c772f…7e05`) placed in the new preprocessed folder. **No fingerprint or plan step.** `batch_dice` is inherited (`False`) |
| Window check | `SEGTRAIN_CT_WINDOW=off`; `finetune_load` compares plans and normalisation |
| Schedule | 2500-iteration linear warm-up to 1e-2, then poly per iteration; SGD Nesterov 0.99; 250 × 250 iterations; batch 2; 256³ |
| Loss, augmentation | DiceCE with deep supervision, **no class weights** (Step T: none in Janus 0's logs); nnU-Net default augmentation, mirroring off in training and inference |
| Sampling | Uniform over the 620; oversampling 0.33 |
| Validation | Fold val = the 10 lowest-id tuning cases. Final validation skipped. `checkpoint_best` never read |
| Environment | `SEGTRAIN_FINETUNE_FROM`, `SEGTRAIN_SAVE_EVERY=10`, `SEGTRAIN_SAVE_PROBABILITIES=0`, `SEGTRAIN_MAX_SECONDS` = walltime − 30 min, `nnUNet_compile=f`; `SEGTRAIN_ITERATIONS` and `SEGTRAIN_EPOCHS` unset. segtrain installed editable in the icx14 venv |
| Runs | a1 = fold 0, a2 = fold 1, concurrent, chain-resumable |
| Candidate | **C = E at t_C.** E = `nnUNetv2_ensemble -i <fold0> <fold1> -o <E> --save_npz`. Never `nnUNetv2_predict -f 0 1`, which averages logits. If a2 has not completed 250 epochs within two chained 23:50 jobs, C = a1 at t_C (Rule T on a1). If a1 has not completed, nothing is scored |
| Inference | `checkpoint_final`, `--disable_tta`, `--save_probabilities` (locked 100 and D60) |
| Not in this plan | Skeleton Recall or other topology loss, the 1e-3 arm, class-weighted CE, a new spacing, from-scratch training (except S) |

### B3.1 Rule W (L-A4, D3-3)

- **Data:** Janus 0's probabilities on the tuning 60 (Job 0).
- **Grid:** {0.50, 0.45, 0.40, 0.35, 0.30}. A voxel is vessel where the summed vessel probability is ≥ t; its class is
  the argmax among the four vessels.
- **Choice:** the highest mean whole-tree Dice, subject to:
  - tF1 ≥ tF1(0.50) − 0.005;
  - FP per case ≤ FP(0.50) + 0.10;
  - no class's centreline recall falls.
- **Ties** (Dice within 0.002) go to the larger t. t = 0.50 always qualifies.
- **Code:** `experiments/Crucible/j1l_r1/decide.py select`.
- **Edge (D3-3):** if t\* = 0.30 is Dice-bound and Dice(0.30) − Dice(0.35) > 0.002, re-run once with 0.25 added,
  before #306.
- **Never re-run on calibrated probabilities (D3-2).**
- **Frozen:** `select.json`'s sha256 is posted before any training job.

### B3.2 Rule T (L-A15, D3-4)

- **Reference:** Janus 0 at t\* on D60: its skeleton, and the EDT radius on it (native spacing).
- **Measure:** dr(t) = the 10 %-trimmed mean of C(t)'s radius minus Janus 0's, on the reference points C(t) covers,
  pooled over D60.
- **Grid:** 0.600, 0.575, …, 0.250; chosen only ≤ 0.50. Folders `t{t:.3f}`.
- **Choice:** t_C = the smallest |dr|. Ties within 0.005 mm go to t\*, then to the larger t.
- **Scope:** if t\* was guard-held (Dice at t\* > 0.002 below the grid's best), t_C = t\*.
- **Runs on C's own probabilities** (E's, or a1's under the fallback). a1's and a2's dr are reports. Opposite signs
  are reported as seed noise.
- **Code:** `experiments/Delta/j1l_r2/rule_t.py`, with #306 passing the grid.
- **Frozen:** `rule_t.json`'s sha256 is posted before `collect` scores anything.

## B4. The decision (L-A5 to L-A8, L-A14 to L-A18, D46 Q3/Q4, D49 Q-R2-3, D50)

**L0 first.** Janus 0 re-predicted reproduces Fir's val-80 decisive macro 0.909 ± 0.003, each class within 0.01 of
LM 0.945, LAD 0.903, LCx 0.857 and RCA 0.938, and ≥ 95 % of cases within 0.01 of Fir's own predictions. Otherwise
stop.
- If Job 0 ran on Fir, that L0 is a determinism check, and `l0_trillium.sh`'s L0 must pass on Trillium before P (D50).
- **The baseline** is Janus 0 at argmax: from `l0_trillium.sh` if it ran, else from Job 0.

**The comparison:**
- C = E at t_C (Janus 1-L.1) against the baseline;
- decisive tF1 @ 1.5 mm at A1c `24441cf8…5254`, Janus 0's A1 aortas, A1a/A1b;
- paired by case; bootstrap 10 000, seed 0; one-sided 2.5 % bounds;
- one look per candidate model, and at most two in the track (C, and S if triggered).

| # | Test | Passes when |
|---|---|---|
| H1 | tF1 non-inferior, nothing lost | Lower bound Δ macro tF1 > −0.02; no class mean Δ < −0.03; L3 holds; C's FP components ≤ 1 per case |
| H2 | Width | Lower bound Δ whole-tree Dice > 0 |
| H3 | tF1 superior | Lower bound Δ macro tF1 > 0 |

**L3** is computed on the scorer's per-class `recall`. For no class may either hold:
- the 10 %-trimmed mean Δ < −0.02;
- or the mean < −0.02 with its upper bound < 0.

Its stated false-alarm rate is 3–8 %, up to about 19 % under a broad shift. The report prints each class's excess
kurtosis.

| Outcome | Verdict | Wording of record |
|---|---|---|
| H1 fails | Not adopted; Janus 0 stays; G5 lists five cases for any class with point Δ < −0.05; S if its trigger fires | "Janus 1-L.1 was not shown non-inferior to Janus 0 in tree-F1 (Δ m, 95 % CI [l, u]; margin −0.02) [or: failed the class / L3 / FP guard, named]. Janus 0 remains the model." |
| H1, lower bound in (−0.02, −0.015], H2 fails | Not adopted | "Non-inferior to Janus 0 at 0.02 but not at the 0.015 that D46 Q4 requires for adoption without a width gain; not shown better. Janus 0 remains." |
| H1, lower bound > −0.015, H2 fails, Dice upper bound < 0 | **Not adopted** (D49 Q-R2-3) | "Non-inferior in tree-F1 at 0.015 (Δ m, 95 % CI [l, u]), but its lumen width is shown worse than Janus 0's (whole-tree Dice Δ d, 95 % CI [dl, du]). Janus 0 remains." |
| H1, lower bound > −0.015, H2 fails, Dice upper bound ≥ 0 | **Adopted** (D46 Q4, D49) | "Janus 1-L is non-inferior to Janus 0 in tree-F1 at a pre-specified margin of 0.015 (Δ m, 95 % CI [l, u]), and passed the class, recall and FP guards (smallest class mean Δ: [class, value]). It is not shown better or worse in lumen width (whole-tree Dice Δ d, 95 % CI [dl, du]) or better in tree-F1. Adopted for its larger training set." |
| H1 + H2, H3 fails | **Adopted** (D46 Q3) | "Janus 1-L is better than Janus 0 in lumen width: whole-tree Dice +d (95 % CI [dl, du]). Its tree-F1 is non-inferior at 0.02 (Δ m, lower bound l), with the class, recall and FP guards passed. A tree-F1 gain was not shown. [Share sentence.]" |
| H1 + H2 + H3 | **Adopted** | As above, ending "… and better in tree-F1 (Δ m, lower bound l > 0)." |

**Every adopted wording also states:**
- "a two-network ensemble of fine-tunes of Janus 0, exported at foreground threshold t_C", and whether Rule T moved
  t_C;
- the MDE, and "under-powered" if the tF1 MDE > 0.025;
- L3's false-alarm rate;
- the val-80 and locked-20 parts (A26: a reversal is reported, not acted on);
- "Janus 0's `nnUNet_compile` at training: unverified".

**The share sentence:** s = (Janus 0 at t_C − Janus 0 at argmax) / (C − Janus 0 at argmax), in Dice.
- s ≥ 0.8: "Most of the width gain is the export threshold, which applies to Janus 0 as well; the fine-tune adds
  [1 − s]."
- s ≤ 0.2: "Most of the width gain is the fine-tune."
- Otherwise: "The threshold and the fine-tune each contribute."

**CONSORT form:** every claim prints its two-sided 95 % CI beside the margin. "Not shown better" is never written "no
better".

**What ships is C exactly as tested.** Never an argmax export, never a1 alone after the look.

**Reports, which decide nothing:**
- Janus 0 at t_C;
- a1, a2, a1 at t_C, a1 at argmax, and E − a1 with its CI;
- σ_g = |a1 − a2|/√2, with A37's ≥ 2-runs rule if |a1 − a2| > 0.02;
- C's Dice and volume ratio at every t;
- per class: tF1, Dice, tolerant Dice, volume ratio, centreline recall and precision, FP;
- val 80 and locked 20 apart;
- the 89 never-inspected cases.

### B4.1 S (L-A18, D49 Q-R2-4, D3-1)

- **Trigger:** H1 fails **and** a1 and a2 at argmax both have point Δ macro tF1 < 0 **and** L0 passed. Never on one
  class, L3 or FP alone with a member ≥ 0.
- **Run:** Janus 0's recipe from scratch on the 620, **at 0.5 mm with Janus 0's plans**: `nnUNetTrainerICX4`
  settings, 1000 epochs, one run, final validation skipped, ≈ 53 GPU-h in three chained jobs.
- **The lead runs it on the trigger** without waiting for another round (D49).
- **Look:** Janus 1-L.2 at t_S (Rule T on S), in the same H1 → H2 → H3 and wording, with every bound at one-sided
  1.25 %. Reports: a1 − S and E − S.
- If S fails, Janus 0 stays.

## B5. Commands (the lead runs them)

### B5.1 Step T: done (2026-11-23)

- Janus 0 was copied off Fir, with its fingerprint and logs, and kept in the lead's Fir home space.
- It went Fir → the lead's machine → Trillium as `janus0_out.tar` (`c30cb01e…0b9b2959`), extracted to
  `$SCRATCH/janus0`.
- `sha256sum -c SHA256SUMS` was OK for all four files; 1000 of 1000 CTs are present; the venv and the icx4 trainer
  are installed; both self-tests pass.

### B5.2 Job 0 (≈ 3–4 GPU-h; D46 Q2, D50)

On Trillium (`trillium-gpu.scinet.utoronto.ca`), or on Fir under `def-aso22_gpu` as a one-off (D50; the other queued
job is cancelled):

```sh
cd $SCRATCH/asclepius/repo && git pull --ff-only && cd experiments/Crucible/j1l_r1 && sbatch job0_janus0_probs.sh
```

When it has ended (same cluster; login node, CPU):

```sh
source $HOME/icx14-venv/bin/activate
R=$SCRATCH/asclepius/repo; W=$SCRATCH/j1l_job0; J0=$SCRATCH/janus0
tail -12 $R/experiments/Crucible/j1l_r1/j1l-job0-*.out
python -c "
import json; L = json.load(open('$R/experiments/Crucible/j1l_r1/lists.json'))
json.dump({'val': [c for c in L['locked100'] if c not in L['locked20_of_open36']]}, open('$W/split_val80.json', 'w'))"
python $R/experiments/Atlas/r9_score_icx4.py --pred $W/thr/t0.50 --pair $J0/pred_fir --icx $J0/icx --aorta $J0/aorta \
  --layout $W/layout.json --splits $W/split_val80.json --set val --np 8 --out $W/scores/identity_val80.json
sha256sum $W/select.json
# only if L0 passed:
T=$(python -c "import json;print('%.2f' % float(json.load(open('$W/select.json'))['chosen_t']))")   # F1 fixed
python $R/experiments/Bridge/j1l_r2/error_decomp.py --selftest
for t in 0.50 $T; do
  python $R/experiments/Bridge/j1l_r2/error_decomp.py --pred $W/thr/t$t --icx $J0/icx --aorta $J0/aorta \
    --layout $W/layout.json --np 8 --out $W/scores/error_decomp_tuning60_t$t.json
done
python $R/experiments/Delta/j1l_r2/mde_from_job0.py $W/scores/locked100_janus0_argmax.json
# only on L-A23's calibration triggers (report):
python $R/experiments/Delta/j1l_r3/calib60.py --probs $W/probs --icx $J0/icx --select $W/select.json \
  --out $W/scores/calib60.json --np 8
```

**Post on #302:**
- the `.out` tail;
- the `summary` and `paired` blocks of `identity_val80.json`;
- `select.json` and its sha256;
- the two decomposition `summary` blocks;
- the MDE printout;
- `calib60.json` if it ran.

Never a per-case row, a volume or a sealed file.

**D3-3's edge re-run, only if it fires:**

```sh
python $R/experiments/Crucible/j1l_r1/threshold_export.py --probs $W/probs --out $W/thr --t 0.25 --np 12
python $R/experiments/Atlas/r9_score_icx4.py --pred $W/thr/t0.25 --icx $J0/icx --aorta $J0/aorta --layout $W/layout.json \
  --splits $W/split_tuning60.json --set val --np 8 --out $W/scores/tuning60_t0.25.json > /dev/null
python $R/experiments/Crucible/j1l_r1/decide.py select --scores $(for t in 0.50 0.45 0.40 0.35 0.30 0.25; do \
  printf 't%s=%s ' $t $W/scores/tuning60_t$t.json; done) > $W/select.json && sha256sum $W/select.json
```

### B5.3 D50 identity check on Trillium (only if Job 0 ran on Fir; ≈ 1 GPU-h)

```sh
cd $SCRATCH/asclepius/repo && git pull --ff-only && sbatch experiments/Delta/j1l_r3/l0_trillium.sh
# when it ends: post the printed summary and paired blocks (val 80). If L0 fails there, stop.
```

If Job 0 ran on Fir, Fir's `select.json` (and the posted sha256) is copied to `$SCRATCH/j1l_job0/select.json` on
Trillium by the same tar route as Step T. `sha256sum` must match the posted value.

### B5.4 #306 (`trillium/janus1l`), built after the converged ruling, to L-A21's spec

Modes and what each runs underneath:
- **`check`:** L-A21's self-tests 1–9 (test 9 against `gate.py`'s fixtures), a test that Rule T's 15 folders exist,
  and a dry run.
- **`prepare` (P):**
  - dataset 718 = the 620 + the locked 100, `cNNNN`, `territory.to_four`;
  - Janus 0's plans copied, `nnUNetv2_move_plans_between_datasets -s 715 -t 718 -sp nnUNetResEncUNetPlans_60G_iso05
    -tp nnUNetResEncUNetPlans_60G_iso05`, then `nnUNetv2_preprocess -d 718 -plans_name
    nnUNetResEncUNetPlans_60G_iso05 -c 3d_fullres`;
  - the fingerprint copied in;
  - `splits_final.json`: two identical entries, val = the 10 lowest tuning ids.
- **`train`:** a1 and a2 as B3, concurrent.
- **`predict` (≈ 3 GPU-h):**
  - folds 0 and 1 separately on the locked 100 and D60, `--save_probabilities --disable_tta -chk
    checkpoint_final.pth`;
  - Janus 0 on D60 likewise, unless F0 ran it;
  - `nnUNetv2_ensemble -i fold0 fold1 -o E --save_npz` for both sets (F3);
  - `threshold_export.py` on D60: Janus 0 at t\*; E, a1 and a2 on Rule T's 15-point grid (F4);
  - locked-100 exports of a1, a2 and E on the grid, **not scored**;
  - the locked-100 npz kept until `collect` ends; D60's npz deleted after export.
- **`transfer`:** `rule_t.py --j0 d60_j0 --cand d60_E --select select.json --out rule_t.json` (and a1, a2 as reports).
  It prints the sha256 and stops.
- **`collect`:**
  - refuses without the posted sha256 of `select.json` and `rule_t.json`, and refuses a second run (looks ledger,
    opened before any locked-100 number is computed);
  - exports E at t_C and Janus 0 at t_C from the npz if t_C is not already exported;
  - scores with `r9_score_icx4.py`;
  - applies the gate (`gate.py`'s logic), writes the wording of B4, `results/SUMMARY.md` and `verdict.json`.
- **`status`.**

**Send back on #302:**
- `check`'s printout;
- `status` after the first 20 epochs;
- `rule_t.json` and its sha256;
- `results/` (no weights, no volumes);
- the `.out` of any failed job.

**Keep** both `checkpoint_final.pth` in the lead's purge-safe space.

## B6. Cost (Trillium, 1 × H100, `def-aso22`, 181 s/epoch)

| Job | GPU-h |
|---|---|
| Job 0 (Trillium or Fir) | 3–4 |
| `l0_trillium.sh` (only if Job 0 ran on Fir) | ≈ 1 |
| P | ≈ 1 |
| a1 + a2 (concurrent, no final validation) | ≈ 25–27 |
| predict | ≈ 3 |
| transfer, collect, decomposition, MDE, calib60 | 0 (CPU) |
| **Total** | **≈ 33–36**, ceiling ≈ 60 |
| S, only on its trigger | +≈ 53 |
| E on all 1000, if adopted | ≈ 4–8 |

## B7. Naming (D46 Q7, L-A24)

- Janus 1-L.1 = C (E at t_C, or a1 at t_C under the fallback). Janus 1-L.2 = S, if read.
- Reports take no number.
- The adopted model is **Janus 1-L**.
- D28 is met by a2.

## B8. When pool reads arrive (L-A11, L-A19)

Round 10's A33–A39 apply from the adopted Janus 1-L:
- pool a1′ starts from a1 and pool a2′ from a2; the candidate is E′;
- G1's replicate clause becomes "each member's Δ > 0";
- G2 and L3 compare E′ with E on the locked 100;
- the b arm (1e-3) starts from a1;
- the 620 are the replay set;
- D35 decides;
- D44 reads collapse to four by territory before D40, with PDA and PLB by side;
- material classes follow D46 Q8.

If a1 alone was adopted, L-A11 applies as written. If Janus 0 stays, the pool stage starts from Janus 0.

## B9. What would change this plan

| Observation | Then |
|---|---|
| L0 fails (Fir's, or Trillium's under D50) | Stop (L-A8) |
| Job 0's rows | Delta v3 §1.2 |
| a2 fails twice | C = a1; D28's replicate reported missing |
| \|a1 − a2\| > 0.02 at the look | A37's ≥ 2 runs per arm for later recipe claims; E's look is unaffected |
| S's trigger | B4.1 |
