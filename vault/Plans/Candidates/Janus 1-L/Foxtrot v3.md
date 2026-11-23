---
tags: [plans, candidate, janus1-L, D45, D46, D49, D50, trillium, fir, four-class, warm-start, ensemble, locked100, round3]
author: Foxtrot
track: 1-L
round: 3
version: 3
updated: 2026-11-23
issue: christianGRogers/Asclepius#302
---

# Janus 1-L, Foxtrot v3: not yet converged (Job 0 is the only gap), with D50's Trillium identity check written, the plan's commands run end to end on phantoms, and items 3–5 settled

## 0. Position

**The plan in force stays:** Delta v2 as amended by L-A1 to L-A25 ([[Master plan - Janus 1-L]],
[[Janus 1-L Round 2]]), under D45, D46, D49 and D50. v3 reopens nothing of [[Janus 1-L Round 2]] §0 or §1. It answers
the seven items of §5 and adds what D50 asks the converged round to write.

**Convergence: not converged, for one reason.** §5 item 1 needs Job 0's outputs on #302, and Job 0 has not run (it is
queued). Every other item can be settled now, and v3 settles them. If the judge accepts v3, round 4 needs only to apply
L-A23's table to the posted numbers and fill one sentence of item 6.

| §5 item | State after v3 | Why |
|---|---|---|
| 1. Step T and Job 0 outputs on #302 | **Half met.** Step T: met (both clusters, #302). Job 0: **not met** | L0, `select.json`, the decomposition and the MDE restatement do not exist yet |
| 2. The lead's answers to Q-R2-1 to Q-R2-4 | **Met** (D49: yes to all four) | §2 |
| 3. S's form | **Settled: 0.5 mm, whatever Job 0 shows** | §4. S tests the warm start. A new grid is a second change in the same run |
| 4. Calibration | **Settled: no calibration step.** On Job 0's edge trigger, Rule W's grid extends to 0.25 and 0.20 | §5. Every calibrated mask is a raw-threshold mask (exactly for Platt/isotonic; within 2 % of rim voxels for a temperature) |
| 5. Class-weighted CE | **Settled: none.** No log shows it and `ce_class_weights.json` is absent | §6. Step T, #302 |
| 6. #306's commands, final | **Settled except one sentence:** the decomposition's reading needs Job 0's numbers | §7. Every command run end to end on phantoms (24 steps, all pass). Six interface fixes |
| 7. One consolidated plan text | **Written:** Appendix A, as replacement text for the master plan | Appendix A |

**New in v3** (CPU; `experiments/Foxtrot/j1l_r3/`; no image, label or score of a real case read):
- [[Foxtrot - The plan's own commands run end to end on phantoms, and Rule T resolves sub-voxel width shifts that a frozen t-star misses]]
  (`chain_dryrun.py`, `rule_t_resolution.py`, `calib_equivalence.py`, `l0_check.py`, `j0t_trillium.sh`).

**Independence.** I read D45 to D50, the round-2 ruling, the master plan, my own v2, the round-2 scripts of record
(Crucible's `decide.py`, `threshold_export.py` and `job0_janus0_probs.sh`; Delta's `rule_t.py` and `mde_from_job0.py`;
Bridge's round-2 `error_decomp.py`; Atlas's r9 scorer) and nnU-Net 2.8.1's wheel. **I did not open Atlas v3, Bridge v3,
their notes, their branches or anything under `experiments/*/j1l_r3/` but my own.** I did read #302, which the brief sends
me to for Step T's results. The same thread holds Atlas's and Bridge's round-3 summary comments, so I saw their headlines.
Where my findings coincide with one of theirs (the `T=` TypeError, the logit-averaging `-f 0 1`, L0's third clause
missing from the posted blocks, S at 0.5 mm), I say so, and the evidence here is my own run.

## 1. Item 1: Step T has run, Job 0 has not

### 1.1 What Step T's posted outputs settle (#302, 2026-11-23)

| Output | Value | Consequence |
|---|---|---|
| Counts | icx 160, aorta 160, Fir predictions 100 | As expected. L0's third clause and J0T have Fir's own locked-100 predictions to compare with |
| `grep -c "class-weighted CE"` | 0 in each of Janus 0's three logs | **Item 5 settled** (§6) |
| `ce_class_weights.json` | absent | The same |
| `SHA256SUMS` | checkpoint `a0fb75de…a43`, plans `b7178bbc…3cc2`, fingerprint `e41c772f…7e05`, lists `7ecc464b…6fd56`. All four verified OK on Trillium | **These are now pins.** #306's `check` refuses a checkpoint, `plans.json` or fingerprint with a different sha256 (A-1, Appendix A) |
| `batch_dice` | `False` | Nothing changes. It is part of the plans that are copied as they are |
| `nnUNet_compile` | **unknown**: Fir's `job_body.sh` was not found | §1.2 |
| Transfer route | Fir → the lead's machine → Trillium (one tar, `c30cb01e…0b9b2959`). Trillium's host is `trillium-gpu.scinet.utoronto.ca` | Appendix A §5 records the route as run. The `rsync` line is withdrawn |
| Purge-safe copy | the lead's Fir home space | Done before the purge (≈ 2026-12-20) |

### 1.2 `nnUNet_compile`, if Fir's copy never turns up

- **The rule: run the fine-tune with `nnUNet_compile=f`, and say in the verdict that Janus 0's setting is unknown.**
- **Why that is safe.** The flag only decides whether `torch.compile` fuses the network's kernels. The loss, optimiser,
  data, augmentation and architecture are the same either way. The checkpoint loads either way:
  `finetune_load` strips a `_orig_mod.` prefix and unwraps a compiled module
  (`src/segtrain/nnunet_ext/finetune_load.py` l. 25, 40, 93). So the flag is a speed setting with float-rounding effects, not a
  recipe term.
- **Why `f`:** Job 0 already predicts with `f`. Compile on H100 adds minutes of start-up to every chained job, and it
  risks a recompile on resume.
- **Amendment to L-A21:** the trainer-diff self-test (item 6) asserts `nnUNet_compile=f`, not "as Janus 0's".

### 1.3 Job 0: not run. What each output would change

L-A23's table stands, row for row. v3 adds three things to the way it is read:
- **The L0 to apply is all three clauses, and the third is in no posted block.** The r9 scorer's `summary` gives
  clauses 1 and 2. Its `paired` block gives a mean difference and CIs (the dry run lists its keys), but not the share
  of cases within 0.01. `l0_check.py` computes all three from the same scorer file, prints a verdict line, and **exits
  3 on FAIL**, so a `&&` chain stops (§7, F2).
- **Under D50, Job 0's L0 means one of two things,** and `l0_check.py --mode` says which:
  - Job 0 on **Fir**: `fir-determinism` (Fir reproduces Fir). Then J0T's L0-T (§3) is required before a1 and a2 train;
  - Job 0 on **Trillium**: `trillium-identity`. That is the L0 of the plan as written, and J0T's step 2 repeats it.
- **The post-Job-0 `T=` line fails as written** (F1, §7): `chosen_t` is a string, and `'%.2f' % str` raises
  `TypeError`. The dry run reproduces it. Appendix A uses `float(...)`.

| Job 0 result (posted) | Then (v3's additions in **bold**) |
|---|---|
| L0 fails (`l0_check` exits 3) | Stop (L-A8). **If Job 0 ran on Fir, a determinism failure on Fir is still a stop: Janus 0 cannot be reproduced on its own cluster** |
| L0 passes on Fir | **J0T runs on Trillium before #306's `train`. If L0-T fails, stop and post `l0_trillium.json`** |
| t\* ∈ {0.45, 0.40, 0.35}, Dice-bound | The plan as written |
| t\* = 0.30 (grid edge) | **Rule W re-runs on the tuning 60 with the grid extended to {0.50, …, 0.20}, same guards, before #306 is built. Rule T's grid extends to 0.20 to match.** No calibration step (§5) |
| FP rises at every t < 0.50, or t\* held by a guard | t_C = t\* (L-A15's scope). **No calibration step: a calibrated mask is a raw mask, so its FP rises too** (§5). The guard that bound is named on #302 |
| t\* = 0.50 with Dice peaking at 0.50 | As L-A23: the export lever is empty, and the Q4 branch is the expected verdict. **S stays 0.5 mm** (§4) |
| Dice at t\* > 0.03 below 0.934 with volume ratio ≥ 0.95 | **S stays 0.5 mm** (§4). The finding is posted as evidence for a later round's width arm, on another decision set |
| Dice(t\*) − Dice(0.50) on the 60 < 0.003 | As L-A23: posted on #302 before training |
| Janus 0's locked-100 per-case SD | `mde_from_job0.py` restates the MDE. No margin moves (L-A7) |
| The decomposition | L-A22's reading, applied mechanically (§7.4). For later rounds only |

## 2. Item 2: met by D49

The lead said yes to Q-R2-1 to Q-R2-4 (D49, 2026-11-22). Written through in Appendix A:
- **Q-R2-1:** C = E at t_C. a2 ships only as one of E's two members.
- **Q-R2-2:** Rule T runs on D60, label-free.
- **Q-R2-3:** L-A16's Q4 row reads "adopted if H1 passes with lower bound > −0.015, H2 fails, **and the 95 % upper
  bound of Δ whole-tree Dice ≥ 0**". If the upper bound is < 0, the verdict is **not adopted**, and the wording is
  "non-inferior in tree-F1 at 0.015 but its lumen width is shown worse than Janus 0's (Δ Dice d, 95 % CI [dl, du]);
  Janus 0 remains".
- **Q-R2-4:** S runs on its trigger without another round.

## 3. D50: the Trillium identity check (J0T), and one baseline platform

D50 lets Job 0 run on Fir and leaves "its exact commands" for Trillium's identity check to the converged round. They are
in `experiments/Foxtrot/j1l_r3/j0t_trillium.sh`, dry-run tested (§7.3).

### 3.1 What J0T does (≈ 1.5 GPU-h, Trillium, after Job 0, before #306's `train`)

1. **Janus 0 re-predicts the locked 100 and D60 on Trillium.** Same model, flags and inference as Job 0: no TTA,
   probabilities saved, `nnUNet_compile=f`.
2. **L0-T:**
   - the argmax export of the val 80, scored with the r9 scorer `--pair $J0/pred_fir`;
   - `l0_check.py --mode trillium-identity`, with L0's thresholds unchanged.
   - It exits 3 on FAIL, and step 3 does not run.
3. **Rule T's reference:** Janus 0 on D60 at t\*, for `rule_t.py --j0`.
   - t\* is read from Job 0's `select.json`, which the job first checks against the sha256 posted on #302
     (`SELECT_SHA256=…`). A wrong hash refuses.

**It never scores:**
- a locked-20 case;
- any locked-100 export other than the val-80 argmax;
- anything on D60.

**It writes no label of any case.** Its outputs to post are the `.out` tail, `l0_trillium.json` with its sha256 line,
and `du -sh` of the two probability folders, which size `predict`'s disk.

### 3.2 The baseline of record is Janus 0 as predicted on Trillium (pre-registered now)

- **The rule.** The locked-100 baseline in H1 → H2 → H3 is Janus 0 at argmax **from J0T's probabilities**, scored in
  `collect`. The candidate is predicted on Trillium too.
- **If Job 0 ran on Trillium,** J0T's predictions and Job 0's are the same in kind. Job 0's file stays the baseline,
  and J0T's step 1 adds only D60.
- **Why.** L0-T admits up to 5 % of val-80 cases differing by more than 0.01 between clusters. A Fir baseline against a
  Trillium candidate would carry that platform noise into every paired Δ, and into H1's lower bound. One cluster
  removes it at no extra look:
  - Janus 0 is not a candidate, and its argmax on the locked 100 is already computed by Job 0;
  - re-scoring it reveals nothing about any candidate.
- **The MDE restatement** may use Job 0's Fir file. It reads only Janus 0's own per-case SD.
- **Reports, which decide nothing:**
  - Fir-baseline − Trillium-baseline on the locked 100, macro and per class;
  - Janus 0 at t_C, also from J0T's probabilities.
  - They replace a copy of Job 0's probabilities from Fir to Trillium, which would be several tens of GB.
- **Cost:** J0T moves Janus 0 × D60 out of `predict` (≈ 0.5 GPU-h) and adds the locked 100 (≈ 1 GPU-h). Net ≈ +1 GPU-h.

### 3.3 What a Fir Job 0 must post (the D50 branch)

The same as the master plan's §5 Job 0 list:
- the `.out` tail;
- `identity_val80.json`'s `summary` and `paired`;
- `select.json` with its sha256;

and also **`l0.json` from `l0_check.py --mode fir-determinism`**, for the third clause.

The Fir job reads CTs from wherever Fir holds them. That changes nothing in the outputs, which are scored by the same
CPU scripts.

## 4. Item 3: S is 0.5 mm, whatever Job 0 shows

**Settled now, without Job 0.** L-A18 defines S by its trigger, *both warm members worse than Janus 0 at argmax*: the
warm-start signature (Ash & Adams, arXiv:1910.08475). S is the test of that one hypothesis, so it keeps Janus 0's recipe
and changes one thing, the initialisation.

**Why not 0.45 mm, even if Job 0 says the grid binds:**
1. **Two changes in one run cannot be read.** A 0.45 mm S that passed would not tell whether warm-starting or the grid
   was the trouble. One that failed would not clear either. Track 1-L has two looks (L-A18), and S's look is the last.
2. **The grid row of L-A23 is a width finding,** and width already has its lever in the plan: the export threshold,
   carried by Rule T. A grid change is a recipe arm. L-A22 sends recipe arms to a later round on another decision set,
   because the locked 100's two looks are spent.
3. **It costs more and needs a new plans step.** A 0.45 mm plan needs `plan_experiment` (or a hand-edited plan), a new
   preprocess, and a view-size check. L-A21 forbids planning, so a 0.45 mm S would also break #306's frozen spec.
   ≈ 55–60 GPU-h against ≈ 53.
4. **Others measured the view.** #302's summaries say two round-3 advocates measured the 620's labels, and both found
   the 0.45 mm view (115 mm with a 256³ patch) fails a pre-registered containment check. I did not read or repeat
   their work. My ruling stands on 1–3 alone.

**What a grid-binding Job 0 does instead:** it is posted as evidence for a later round's width arm. That arm needs its
own decision set (L-A18's third-look rule).

## 5. Item 4: no calibration step

**The question in L-A23** was whether, on a rim-miscalibration signal, a temperature fit on Janus 0's tuning-60
probabilities should be followed by re-running Rule W on calibrated probabilities. **It should not, because it cannot
reach a mask that Rule W cannot reach.**

`calib_equivalence.py` (synthetic 5-class rim logits, 400 000 voxels, 5 % at junctions):
- **Platt or isotonic calibration of p_fg** is increasing in p_fg, so {g(p_fg) ≥ t} = {p_fg ≥ g⁻¹(t)}. Every
  calibrated mask is exactly a raw-threshold mask. Calibration only re-grids Rule W.
- **Temperature scaling of the logits:**
  - leaves argmax unchanged at every T, so t = 0.50 cannot move (asserted at every T tried);
  - is not a function of p_fg alone, but its masks at t ∈ {0.45, …, 0.25}, T ∈ {0.7, …, 2.0} equal the nearest
    raw-threshold mask up to **at most 2.1 % of the calibrated mask's voxels** (`worst_disagreement_share` 0.0206;
    typically 0.4 %). Those voxels are rim voxels at bifurcations, where the vessel mass splits between two classes.

**So the triggers are handled on the raw grid:**

| Trigger | Action |
|---|---|
| t\* = 0.30 (Dice still rising at the grid edge) | Extend Rule W's grid to 0.25 and 0.20 on the tuning 60, same guards and tie rule, before #306. Rule T's grid extends to 0.20 |
| FP rises at every t < 0.50 | t\* = 0.50. A calibrated mask is a raw mask up to ≤ 2 % of rim voxels, so its FP rises too. Rule T does not apply (scope), and t_C = t\* |
| t\* held by a guard | t_C = t\* (L-A15's scope) |

## 6. Item 5: Janus 0 trained without class weights

Step T found `class-weighted CE` 0 times in each of Janus 0's three training logs, and no `ce_class_weights.json`.
So the fine-tune's loss is plain DiceCE, which is Janus 0's. L-A21's trainer-diff self-test asserts "CE weight None",
as written. Nothing else changes.

## 7. Item 6: #306's commands, final, and the interfaces they rest on

### 7.1 How I checked the interfaces

`chain_dryrun.py` builds 220 synthetic phantom cases in Step T's own layout:
- 60 tuning, 100 locked and 60 D60;
- probabilities in nnU-Net 2.8.1's on-disk form;
- Fir "predictions" with two cases jittered.

It then runs the plan's **command lines as written**, as subprocesses with the plan's variables:
- Job 0's tail (export, 5 scorings, `decide.py select`, the baseline scoring, the print block);
- the master plan's identity commands, then `l0_check.py`;
- the post-Job-0 `T=` line, as written and as corrected;
- `error_decomp.py` at 0.50 and at t\*, and `mde_from_job0.py`;
- Rule T's exports and `rule_t.py`;
- J0T (`DRYRUN=1`): it must stop at a failing L0, refuse a wrong `select.json` hash, and give the same t_C as the Rule T
  step.

**24 of 24 steps behave as specified** (`chain_dryrun.json`). On phantoms, the expected failures fail with the expected
exit codes: L0, the `T=` line, and a wrong select hash.

### 7.2 Interface findings (F1–F6)

| # | Finding | Fix (in Appendix A) |
|---|---|---|
| F1 | The post-Job-0 line `'%.2f' % json.load(...)['chosen_t']` raises `TypeError` (`chosen_t` is `'0.35'`, a string, from `decide.py select`). Also on #302 from two other advocates | `'%.2f' % float(...)` |
| F2 | L0's third clause (≥ 95 % of cases within 0.01) is in neither posted block. `paired` has `case_ci`, `fp_diff`, `mean_diff_run2_minus_run1`, `n`, `seed_inclusive_ci`, `sigma_seed_estimate_1df`. Also on #302 from Atlas | `l0_check.py`, all three clauses, exit 3 on FAIL |
| F3 | **`nnUNetv2_predict -f 0 1` is not E.** nnU-Net 2.8.1 sums the folds' *logits* and divides (`predict_logits_from_preprocessed_data`, l. 524–530), while E is the mean *softmax* (L-A14). `nnUNetv2_ensemble` averages the saved `probabilities` (`ensemble.py` l. 18–30), and writes the `.npz` only with `--save_npz` (l. 45–46, 122). Without it, `threshold_export.py` finds no `.npz` and stops. It also needs `plans.json` and `dataset.json` in the first input folder, which `nnUNetv2_predict` copies there, and the same `.npz` set in every folder (l. 92–95). Also on #302 from Atlas and Bridge | L-A14's "equals `nnUNetv2_predict -f 0 1`" is struck. `predict` runs fold 0 and fold 1 **separately** with `--save_probabilities`, then `nnUNetv2_ensemble -i f0 f1 -o E --save_npz` |
| F4 | `rule_t.py` needs Janus 0 at t\* on D60 under `--j0 <dir>/t<t*>`. No job of the plan of record writes it. The predict job lists Janus 0 × D60 probabilities, but not the export | J0T step 3 writes it (`$V/d60_j0/t$T`) |
| F5 | On voxel-aligned phantoms (straight tubes on the grid), Rule T's 10 %-trimmed dr is exactly 0 at every t ≤ 0.50. Each centreline EDT is a minimum over directions, so a partial rim change moves fewer than 10 % of the points, and trimming removes them. Rule T then returns t\* by its tie rule, while the oracle was 0.50. On continuous geometry this does not happen (§8) | Report only: `transfer` prints the share of shared points with dr = 0 at each t. If the trimmed dr is 0 at every t ≤ 0.50, the verdict says "Rule T could not resolve a width difference; t_C = t\* by its tie rule" |
| F6 | `l0_check.py` exits 3 on FAIL. The other scripts print a verdict and exit 0 | The command blocks chain with `&&` where a FAIL must stop |

**Checked and found consistent (no fix needed):**
- `threshold_export.py` writes `t<t:.2f>` folders, which Job 0's loops, `decide.py select`'s `t0.50=` keys,
  `rule_t.py`'s `t{t:.2f}` and `error_decomp.py --pred` all read.
- `t = 0.50` is argmax, and every `t < 0.50` is a superset of it: if a vessel class beats background, p_bg < 0.5.
- `rule_t.py` reads `chosen_t` with `float()`.
- `error_decomp.py` iterates over the tuning 60 from `lists.json`, not over the folder, so the 160-case `thr/t0.50` is
  safe.
- `mde_from_job0.py` reads the scorer's `rows` and `dice.tree`.
- `rule_t.py` refuses any non-D60 case.
- The r9 scorer refuses sealed cases.
- The self-tests of the five scripts of record (`threshold_export.py`, `decide.py`, `rule_t.py`, `error_decomp.py`,
  the r9 scorer) pass here, and so does `l0_check.py`'s.

### 7.3 The command blocks

The commands are in Appendix A §5, one block per job, in the order the lead runs them:
1. Job 0 (as queued; on Fir or Trillium, D50);
2. the post-Job-0 CPU block;
3. J0T;
4. #306's modes.

`check`, `prepare` and `train` live in `trillium/janus1l` (#306, not yet built), so their lines name the mode and what it
must run inside. `predict`, `transfer` and the export half of `collect` are written against the merged scripts and were
dry-run tested in that form.

### 7.4 The decomposition reading, on the posted numbers

No numbers are posted, so this is the one sentence round 4 fills. The reading is mechanical (L-A22):
- for each group's macro ceiling: ≥ 0.030 an arm may be costed; 0.015–0.030 needs a no-training test first; < 0.015 no
  arm;
- extent is vetoed if more than half of the `distal` points are below A23's contrast line;
- LCx is read first.

It decides only what a later round may propose.

## 8. Rule T holds up at sub-voxel shifts (evidence for keeping it)

`rule_t_resolution.py` imports Delta's `rule_t` functions unchanged and runs them on continuous-geometry phantoms:
- curved tubes of radius 0.8–2.6 mm with an analytic distance to the axis;
- grids of 0.5 mm and 0.4 mm;
- smooth logit noise;
- Janus 0 drawn 0.20 mm thin with a 0.25 mm rim, so t\* = 0.35 puts its wall 0.045 mm inside.

Eight scenarios per grid, 12 cases each, compared with the exact oracle t:

| | Mean \|wall error\| (mm) | Worst (mm) | Exact grid hits (of 16) |
|---|---|---|---|
| **Rule T (as merged)** | 0.031 | 0.1 | 13 |
| Shared-tube volume offset (an alternative I built to test it) | 0.027 | 0.1 | 12 |
| Frozen t\* | 0.098 | 0.255 | 2 |

- **Rule T resolves the sub-voxel shifts the export threshold makes** (0.05–0.15 mm). It is not moved by an extra branch
  or a missing distal piece.
- Its largest miss is the one no t ≤ 0.50 can fix: C already wider than Janus 0 at t\*.
- **Rule T is within one grid step of the oracle in all 16 rows.** The alternative is about the same (0.027 against
  0.031 mm), **so I propose no change to Rule T.** F5's degenerate case belongs to voxel-aligned
  tubes, which real coronaries are not. F5's report line is there so that a degenerate D60 result is named, not hidden.

## 9. Cost (Trillium, 1 × H100)

| Job | GPU-h | Change from L-A25 |
|---|---|---|
| Job 0 (Fir or Trillium, D50) | 3–4 | — |
| **J0T** (Janus 0 on the locked 100 and D60; L0-T; Rule T's reference) | **≈ 1.5** | new (D50) |
| P | ≈ 1 | — |
| a1 + a2 | ≈ 25–27 | — |
| predict (folds 0 and 1 on the locked 100 and D60; ensemble on CPU) | ≈ 2.5 | Janus 0 × D60 moved to J0T |
| transfer, collect, decomposition, MDE | 0 | — |
| **Total** | **≈ 33–36** (ceiling ≈ 60) | ≈ +1 |
| S, on its trigger (D49 Q-R2-4) | +≈ 53 (0.5 mm only) | the 0.45 mm form is dropped |

## 10. Questions for the lead

**None.** D50 asked the converged round for J0T's commands, and they are written. The `nnUNet_compile` rule (§1.2) and
the baseline platform (§3.2) are technical choices for the judge.

## 11. What would change this plan

| Observation | Then |
|---|---|
| Job 0 posted, L0 passes | Round 4 applies L-A23 (as read in §1.3) and §7.4, and can rule converged |
| Fir's `job_body.sh` turns up with `nnUNet_compile=t` | Stated in the verdict. The fine-tune still runs `f` (§1.2) |
| L0-T fails on Trillium | Stop. The lead decides whether Janus 1-L trains on Fir (a D45/D50 question, not a plan question) |
| Rule T's dr is 0 at every t ≤ 0.50 on D60 | t_C = t\* by the tie rule, and the verdict says Rule T could not resolve (F5) |
| t\* = 0.30 | Rule W's grid extends to 0.20 before #306 (§5) |
| Job 0's grid row fires | Posted as width evidence for a later round. S unchanged (§4) |

---

## Appendix A. The consolidated plan text (item 7)

*This is written as replacement text for [[Master plan - Janus 1-L]]. Every clause of L-A1 to L-A25, D49 and D50 is
written through, together with the v3 changes above (each marked "v3" so the judge can strike it), and no superseded
clause is kept. Citations point at the amendment of record.*

### A.0 Status and binding decisions

- **In force:** Delta v2 as amended by L-A1 to L-A25 (and round 3's amendments).
- **Binding:**
  - D45: split, Trillium, the lead runs every job;
  - D46: the round-1 answers;
  - D49: Q-R2-1 to Q-R2-4, all yes;
  - D50: Job 0 may run on Fir, and Trillium's identity check runs before training;
  - D25 and D8: four classes by territory, on ImageCAS-X's lumen;
  - D27/D32: the seals;
  - D34: naming;
  - D35: pool questions only;
  - D40: overlaps to ignore, for pool reads.
- **Done:** Step T, on both clusters (#302, 2026-11-23).
- **Next:**
  1. Job 0 (queued);
  2. the post-Job-0 CPU block;
  3. J0T;
  4. #306, built only after the round that rules converged;
  5. P, a1 and a2, predict, transfer, collect.

### A.1 In one paragraph

**Janus 1-L is Janus 0 fine-tuned warm on D45's 620 ImageCAS-X cases, twice (a1, a2).**
- **Recipe:** the A17a trainer through the subclass `nnUNetTrainer_janus1l`, 250 epochs, peak LR 1e-2, Janus 0's plans
  moved without re-planning, mirroring off, no class weights.
- **The candidate C is their ensemble E** (mean softmax, by `nnUNetv2_ensemble`), exported at a foreground threshold
  t_C:
  - **Rule W** chooses t\* on Janus 0's probabilities for the 60 training cases it never saw;
  - **Rule T** carries the width t\* gives to E, by matching local radius on the shared centreline of 60 unlabelled
    quality-0 CTs.
- **The locked 100 judge C against Janus 0 once:**
  - H1: tF1 non-inferior at −0.02, with class, recall and FP guards;
  - H2: whole-tree Dice superior;
  - H3: tF1 superior.
- **Adoption:** H1 + H2 is "better". A non-inferior, not-better C is adopted if H1's lower bound is above −0.015 and its
  Dice is not shown worse (D46 Q4, D49 Q-R2-3).
- **Fallback:** one pre-registered from-scratch run S (0.5 mm), with its own look at 1.25 %.

### A.2 Data (L-A1, L-A15)

| Set | Cases | Use |
|---|---|---|
| Train 620 | ImageCAS-X train 560 + dev 44 + c0123 c0195 c0340 c0416 c0430 c0435 c0447 c0617 c0624 c0660 c0726 c0758 c0772 c0877 c0971 c0984 | Training (folds 0 and 1: the same split entry) |
| ↳ tuning 60 | dev 44 + those 16 | Rule W on Janus 0's probabilities (Job 0), before any training. The 10 lowest ids are nnU-Net's fold val (display only, L-A21) |
| Locked 100 | val 80 + c0068 c0102 c0251 c0271 c0323 c0327 c0470 c0545 c0592 c0620 c0644 c0805 c0807 c0824 c0827 c0841 c0908 c0946 c0957 c0996 | The one decision. Never trained on, never used to choose anything, never nnU-Net's val |
| D60 | `experiments/Delta/j1l_r2/drift60.json` (pin `916e8a18…004e`) | Rule T only. CT images; Janus 0's and the candidate's predictions compared; no label or mask read; nothing trained (D49 Q-R2-2) |
| Sealed | ImageCAS-X test 80 + quality-0 20 | Never read, predicted, scored or trained on |

- **Pins:**
  - locked 100: `bbd9c687818956e2d5664b06fd8c8bd02ddb031e9b9d08036d59cc0e1a4d5895`;
  - train 620: `1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152`;
  - split file `19b832fe…4dd3` → `configs/janus1/split-2026-11.json`.
- **Janus 0 pins (v3, from Step T):**
  - checkpoint `a0fb75de766445f2cbc81b9201a290414e0b9b19ab57320753afa26d20a9ca43`;
  - `plans.json` `b7178bbc6d86e658e449b72cef7621f06de222c107083a2622792d346bd93cc2`;
  - `dataset_fingerprint.json` `e41c772faf5e58a31d44cfc948031354dde6d0070a900a1ebfdb14691f937e05`.
- **Labels:** ImageCAS-X as drawn (D8), collapsed by `territory.to_four` (D25, D1, D1b), as dataset 715.
- **Pool reads:** none in Janus 1-L. The pool fine-tune later runs member-wise:
  - pool a1′ from a1 and a2′ from a2, and the candidate is E′ (L-A19);
  - D44 reads collapse by territory before D40, with materials dropped (D46 Q8).

### A.3 Recipe (L-A2, L-A3, L-A20, L-A21)

| Item | Setting |
|---|---|
| Start | Janus 0 `checkpoint_final.pth` (pinned), full strict load with heads, bitwise-checked |
| Plans | Janus 0's `plans.json` (pinned) is copied to `Dataset715_ICX4/nnUNetResEncUNetPlans_60G_iso05.json`, then moved with `nnUNetv2_move_plans_between_datasets` to dataset 718. It must equal Janus 0's except `dataset_name` and `image_reader_writer`. Then `nnUNetv2_preprocess` only. Janus 0's fingerprint is placed in the preprocessed folder. **No planning, no fingerprinting** |
| Schedule | 2500-iteration linear warm-up to 1e-2, then poly. SGD, Nesterov 0.99. 250 epochs × 250 iterations |
| Loss, augmentation | DiceCE with deep supervision, **no class weights** (Step T: none in Janus 0's logs). nnU-Net default augmentation, **mirroring off** in training and inference |
| Validation | Fold val = the 10 lowest tuning-60 ids. Final validation skipped (`perform_actual_validation` returns). `checkpoint_best` never read |
| Environment | `SEGTRAIN_FINETUNE_FROM`, `SEGTRAIN_CT_WINDOW=off`, `SEGTRAIN_SAVE_EVERY=10`, `SEGTRAIN_SAVE_PROBABILITIES=0`, `SEGTRAIN_MAX_SECONDS` = walltime − 30 min; `SEGTRAIN_ITERATIONS` and `SEGTRAIN_EPOCHS` unset. **`nnUNet_compile=f`** (v3: Janus 0's setting is unknown, and the flag is not a recipe term). segtrain installed editable, or with `SEGTRAIN_SEALED_LIST` and `SEGTRAIN_POOL_SEAL` set |
| Runs | a1 = fold 0, a2 = fold 1, concurrent, chain-resumable |
| C | **E = `nnUNetv2_ensemble --save_npz` of the two folds' saved probabilities** (v3 F3: never `nnUNetv2_predict -f 0 1`, which averages logits). If a2 has not completed 250 epochs within two chained 23:50 jobs, C = a1 at t_C. If a1 has not completed, nothing is scored |
| Export | t_C (A.3.2), applied to C, with every report at t_C too. What ships is C exactly as tested |

**A.3.1 Rule W (L-A4).**
- **Grid:** t ∈ {0.50, 0.45, 0.40, 0.35, 0.30} on Janus 0's tuning-60 probabilities. Vessel where Σ p_vessel ≥ t
  (t = 0.50 is argmax); the class is the argmax among the four vessels.
- **Choice:** the highest mean whole-tree Dice, subject to:
  - tF1 ≥ tF1(0.50) − 0.005;
  - FP ≤ FP(0.50) + 0.10;
  - no class's centreline recall falls.
- **Ties** (Dice within 0.002) go to the larger t.
- **v3, the edge rule:** if t\* = 0.30, the grid extends to 0.25 and 0.20 on the same 60, with the same guards, before
  #306 is built. No calibration step.
- **Code:** `decide.py select`. `select.json` and its sha256 are posted on #302 before any training job.

**A.3.2 Rule T (L-A15, D49 Q-R2-2).**
- **Reference:** Janus 0 at t\* on D60, as predicted on Trillium by J0T: its skeleton and its EDT radius.
- **Measure:** dr(t), the 10 %-trimmed mean, over reference skeleton points C(t) covers and pooled over D60, of
  EDT(C(t)) − EDT(J0(t\*)).
- **Choice:** t_C = the t ≤ 0.50 on {0.50, …, 0.25} (to 0.20 under the edge rule) with the smallest |dr|. Ties within
  0.005 mm go to t\*, then to the larger t.
- **Scope:** if t\* is more than 0.002 Dice below the grid's best (guard-held), t_C = t\*.
- **Runs on C's probabilities.** a1's and a2's dr are reports. If they shift in opposite directions, the report calls it
  seed noise.
- **v3 report (F5):** the share of shared points with dr = 0 at each t. If the trimmed dr is 0 at every t ≤ 0.50, the
  verdict states that Rule T could not resolve.
- **Code:** `rule_t.py`. `rule_t.json` and its sha256 are posted on #302 before `collect`, and `collect` refuses
  without it.

### A.4 The decision on the locked 100

**L0, the identity check (L-A8; D50; v3 `l0_check.py`).** Janus 0 re-predicted:
- reproduces Fir's val-80 decisive macro 0.909 ± 0.003;
- has each class within 0.01 of LM 0.945, LAD 0.903, LCx 0.857 and RCA 0.938;
- has ≥ 95 % of cases within 0.01 of Fir's own predictions.

Otherwise stop. If Job 0 ran on Fir, this is a determinism check, and **L0-T** (J0T, the same three clauses on Trillium
against Fir's predictions) must pass before #306's `train`.

**The comparison.**
- **C** = E at t_C (Janus 1-L.1).
- **Baseline** = Janus 0 at argmax **as predicted on Trillium** (v3: from J0T, or Job 0 if it ran on Trillium).
- Decisive tF1 @ 1.5 mm at A1c `24441cf8…5254`, with Janus 0's A1 aortas and A1a/A1b exclusions.
- Paired by case; bootstrap 10 000; one-sided 2.5 % bounds.
- One look per candidate. At most two in the track (C, and S if triggered).

| # | Test | Passes when |
|---|---|---|
| H1 | tF1 non-inferior, nothing lost | Lower bound Δ macro tF1 > −0.02; no class mean Δ < −0.03; L3 holds; C's FP ≤ 1 per case |
| H2 | Width | Lower bound Δ whole-tree Dice > 0 |
| H3 | tF1 superior | Lower bound Δ macro tF1 > 0 |

**L3 (L-A17),** on the scorer's per-class `recall`. For no class may either hold:
- its 10 %-trimmed mean Δ < −0.02;
- or its mean < −0.02 with a 95 % upper bound < 0.

Stated false-alarm rate 3–8 %, up to ≈ 19 % under a broad shift. Each class's excess kurtosis of the recall Δ is
printed.

**Verdicts (L-A16 with D49 Q-R2-3), wording of record:**

| Outcome | Verdict | Wording |
|---|---|---|
| H1 fails | Not adopted; S if its trigger fires | "Janus 1-L.1 was not shown non-inferior to Janus 0 in tree-F1 (Δ m, 95 % CI [l, u]; margin −0.02) [or: failed the class / L3 / FP guard, named]. Janus 0 remains the model." G5 lists five cases for any class with point Δ < −0.05 |
| H1, lb ∈ (−0.02, −0.015], H2 fails | Not adopted | "Non-inferior to Janus 0 at 0.02 but not at the 0.015 that D46 Q4 requires for adoption without a width gain; not shown better. Janus 0 remains." |
| H1, lb > −0.015, H2 fails, **Dice upper bound < 0** | **Not adopted** (D49 Q-R2-3) | "Non-inferior in tree-F1 at 0.015 (Δ m, 95 % CI [l, u]), but its lumen width is shown worse than Janus 0's (whole-tree Dice Δ d, 95 % CI [dl, du]). Janus 0 remains." |
| H1, lb > −0.015, H2 fails, Dice upper bound ≥ 0 | **Adopted** (D46 Q4) | "Janus 1-L is non-inferior to Janus 0 in tree-F1 at a pre-specified margin of 0.015 (Δ m, 95 % CI [l, u]), and passed the class, recall and FP guards (smallest class mean Δ: [class, value]). It is not shown better in lumen width (whole-tree Dice Δ d, 95 % CI [dl, du]) or in tree-F1. Adopted for its larger training set." |
| H1 + H2, H3 fails | **Adopted** (D46 Q3) | "Janus 1-L is better than Janus 0 in lumen width: whole-tree Dice +d (95 % CI [dl, du]). Its tree-F1 is non-inferior at 0.02 (Δ m, lower bound l), with the class, recall and FP guards passed. A tree-F1 gain was not shown. [Share sentence.]" |
| H1 + H2 + H3 | **Adopted** | As above, ending "… and better in tree-F1 (Δ m, lower bound l > 0)." |

**Every adopted wording also states:**
- "a two-network ensemble of fine-tunes of Janus 0, exported at foreground threshold t_C", and whether Rule T moved t_C;
- the MDE, with "under-powered" if the tF1 MDE > 0.025;
- L3's false-alarm rate;
- the val-80 and locked-20 parts (any sign reversal reported, not acted on);
- that Janus 0's `nnUNet_compile` setting is unknown, if it still is.

**The share sentence:** s = (J0 at t_C − J0 at argmax) / (C − J0 at argmax), in Dice:
- s ≥ 0.8: "most of the width gain is the export threshold, which applies to Janus 0 as well; the fine-tune adds
  [1 − s]";
- s ≤ 0.2: "most of the width gain is the fine-tune";
- otherwise: "the threshold and the fine-tune each contribute".

CONSORT form: every claim prints its two-sided 95 % CI beside the margin. "Not shown better" is never written "no
better".

**Reports, which decide nothing:**
- J0 at t_C;
- a1, a2, a1 at t_C, every argmax export, E − a1 with CI;
- σ_g = |a1 − a2|/√2 (A37's ≥ 2-runs rule if |a1 − a2| > 0.02);
- C's Dice and volume ratio at every t;
- per-class tF1, Dice, tolerant Dice, volume ratio, recall, precision and FP;
- val 80 and locked 20 apart;
- the 89 never-inspected cases;
- v3: Fir-baseline − Trillium-baseline.

**S (L-A18, D49 Q-R2-4).**
- **Trigger:** H1 fails, and a1 at argmax and a2 at argmax both have point Δ macro tF1 < 0, and L0 passed. Never on one
  class, L3 or FP alone with a member ≥ 0.
- **Run:** Janus 0's recipe from scratch on the 620, **0.5 mm, Janus 0's plans** (v3: settled), 1000 epochs, one run,
  final validation skipped, ≈ 53 GPU-h. The lead runs it on the trigger.
- **Look:** Janus 1-L.2 at t\* with Rule T on S, in the same sequence and wording, every bound at one-sided 1.25 %.
- If S fails, Janus 0 stays.

**Naming (L-A24):** Janus 1-L.1 = C; Janus 1-L.2 = S if read; the adopted model is Janus 1-L. D28 is met by a2.

### A.5 Commands (the lead runs them)

**Step T: done** (2026-11-23). Route as run: Fir packs `janus0_out.tar` → the lead's machine → Trillium,
`$SCRATCH/janus0`, `sha256sum -c SHA256SUMS` OK.

**Job 0 (as queued, Fir or Trillium, D50).** `experiments/Crucible/j1l_r1/job0_janus0_probs.sh`. Then, on the same
cluster:

```sh
source $HOME/icx14-venv/bin/activate
R=$SCRATCH/asclepius/repo; W=$SCRATCH/j1l_job0; J0=$SCRATCH/janus0     # Fir: the paths the queued job used
git -C $R pull --ff-only
python -c "
import json; L = json.load(open('$R/experiments/Crucible/j1l_r1/lists.json'))
json.dump({'val': [c for c in L['locked100'] if c not in L['locked20_of_open36']]}, open('$W/split_val80.json', 'w'))"
python $R/experiments/Atlas/r9_score_icx4.py --pred $W/thr/t0.50 --pair $J0/pred_fir --icx $J0/icx --aorta $J0/aorta \
  --layout $W/layout.json --splits $W/split_val80.json --set val --np 8 --out $W/scores/identity_val80.json
MODE=fir-determinism    # or trillium-identity if Job 0 ran on Trillium
python $R/experiments/Foxtrot/j1l_r3/l0_check.py --scores $W/scores/identity_val80.json --mode $MODE --out $W/l0.json \
  && sha256sum $W/select.json
```

Post: the `.out` tail, `l0.json` with its sha256 line, and `select.json` with its sha256.

**After Job 0 (CPU, only if L0 passed).**

```sh
T=$(python -c "import json;print('%.2f' % float(json.load(open('$W/select.json'))['chosen_t']))")
python $R/experiments/Bridge/j1l_r2/error_decomp.py --selftest
for t in $(printf '%s\n' 0.50 $T | sort -u); do
  python $R/experiments/Bridge/j1l_r2/error_decomp.py --pred $W/thr/t$t --icx $J0/icx --aorta $J0/aorta \
    --layout $W/layout.json --np 8 --out $W/scores/error_decomp_tuning60_t$t.json
done
python $R/experiments/Delta/j1l_r2/mde_from_job0.py $W/scores/locked100_janus0_argmax.json
```

Post the two `summary` blocks and the MDE printout. If Job 0 ran on Fir, copy `select.json` to Trillium's
`$SCRATCH/j1l_job0/` (one small file; its posted sha256 is checked by J0T).

**J0T (Trillium, ≈ 1.5 GPU-h, before #306's `train`).**

```sh
cd $SCRATCH/asclepius/repo && git pull --ff-only
SELECT_SHA256=<select.json's sha256 from #302> sbatch experiments/Foxtrot/j1l_r3/j0t_trillium.sh
```

Post: the `.out` tail, `l0_trillium.json` with its sha256, and the `du -sh` lines. If L0-T fails, stop.

**#306 (`trillium/janus1l/janus1l`, built to L-A21 after the converged round).**

```sh
cd $SCRATCH/asclepius/repo && git pull --ff-only && source $HOME/icx14-venv/bin/activate
J=trillium/janus1l/janus1l
R=$SCRATCH/asclepius/repo; E=$R/experiments/Crucible/j1l_r1; JOB0=$SCRATCH/j1l_job0
V=$SCRATCH/j1l_j0t; Q=$SCRATCH/j1l_pred      # J0T's folder (inputs in_l100, in_d60; d60_j0) and predict's
$J check                    # self-tests 1-9 (L-A21) + the Step T pins + l0_trillium.json says PASS; dry run prints paths
$J prepare                  # P: copy + move plans, preprocess, fingerprint; dataset 718; ≈ 1 GPU-h
$J train                    # a1 (fold 0), a2 (fold 1), concurrent, chained 23:50 jobs; $J status between
$J predict                  # below; ≈ 2.5 GPU-h
$J transfer                 # below; CPU; prints rule_t.json's sha256 -> post on #302
$J collect --select-sha256 <posted> --rule-t-sha256 <posted>    # the one look; refuses a second run
```

`predict` must run (v3 F3):

```sh
P="-d 718 -c 3d_fullres -tr nnUNetTrainer_janus1l -p nnUNetResEncUNetPlans_60G_iso05 -chk checkpoint_final.pth \
   --disable_tta --save_probabilities -npp 6 -nps 6 -device cuda"
for f in 0 1; do for s in l100 d60; do nnUNetv2_predict -i $V/in_$s -o $Q/f${f}_$s -f $f $P; done; done
for s in l100 d60; do nnUNetv2_ensemble -i $Q/f0_$s $Q/f1_$s -o $Q/E_$s --save_npz -np 8; done
```

`transfer` must run (Rule T, with a1's and a2's as reports):

```sh
G="0.60 0.55 0.50 0.45 0.40 0.35 0.30 0.25"                  # 0.20 appended under the edge rule
for m in E f0 f1; do
  python $E/threshold_export.py --probs $Q/${m}_d60 --out $Q/d60_$m --t $G --np 12
  python $R/experiments/Delta/j1l_r2/rule_t.py --j0 $V/d60_j0 --cand $Q/d60_$m --select $JOB0/select.json \
    --out $Q/rule_t_$m.json --np 12
done
sha256sum $Q/rule_t_E.json          # rule_t.json of record = rule_t_E.json (or rule_t_f0.json under the a1 fallback)
```

`collect`:
- exports E, f0, f1 and Janus 0 (from J0T's `$V/probs_l100`) on the locked 100 at t_C and at 0.50;
- scores each with the r9 scorer;
- applies the gate of A.4 (L-A16, L-A17, D49 Q-R2-3), writing the looks ledger before it scores C;
- prints the verdict, its wording and the reports.

Its gate is #306's to build. Two round-3 reference gates exist on dev, and I have not read them.

### A.6 Cost

See §9: ≈ 33–36 GPU-h with Job 0 and J0T. S +≈ 53 on its trigger.

### A.7 What is still open

- **Job 0's outputs:** round 4 applies L-A23 as read in §1.3.
- **The decomposition reading** (§7.4).
- **#306** is built after the converged round.
