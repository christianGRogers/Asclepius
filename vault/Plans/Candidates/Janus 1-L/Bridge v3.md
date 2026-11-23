---
tags: [plans/candidate, bridge, janus1-l, D45, D46, D49, trillium, locked100, round3]
author: Bridge
track: 1-L
round: 3
version: 3
updated: 2026-11-23
issue: christianGRogers/Asclepius#302
---

# Bridge v3 (Janus 1-L): not converged, because Step T and Job 0 have not run. S is 0.5 mm whatever Job 0 shows, because a 115 mm view fails a pre-registered check. The temperature check cannot see an inward rim. The command block is final, with five interface defects fixed

## 0. Position

Bridge v3 works inside the plan in force: [[Master plan - Janus 1-L]] (Delta v2 as amended by L-A1 to L-A25), with
D45, D46 and **D49** (the lead said yes to Q-R2-1 to Q-R2-4). It answers the seven items of [[Janus 1-L Round 2]] §5.

**Step T, Job 0 and F0 have not run.** No number in this plan comes from them. Where an item needs one, I give the
rule and what each outcome would change (§1). F0 belongs to track 1-F (#303). Track 1-L shares only the split with it
(L-A1), so F0's outputs change nothing here.

**Independence.** I read no other round-3 candidate of this track and no `exp/j1l-r3-*` branch. The `dev` log does
show the title of a merged Atlas round-3 commit, because `git log` prints it. I did not open its files, and nothing
below rests on it.

### 0.1 Converged or not: item by item

**Round 3 cannot rule the plan converged.** The ruling's own condition (§5: "only if items 1 and 2 are met") fails on
item 1.

| §5 item | Status | Why |
|---|---|---|
| 1. Step T and Job 0 outputs on #302 | **Not met. This blocks convergence** | Neither has run. L-A23's table cannot be applied to numbers that do not exist (§1) |
| 2. The lead's answers to Q-R2-1 to Q-R2-4 | **Met** (D49, all four yes) | Written through in §2 and in Part B |
| 3. S's form | **Settled, whatever Job 0 shows: 0.5 mm** | nnU-Net's own planner keeps 256³ at 0.45 mm, so the view is 115.2 mm. That fails a check whose rule was fixed before the run, on the 620 (§3) |
| 4. Calibration | **The rule is settled. Whether it runs is not**: it needs Job 0's t\* | Finding: a temperature cannot move the 0.5 crossing, so the check the ruling names cannot detect an inward rim. I add a Platt bias, which can (§4) |
| 5. Class-weighted CE in Janus 0's run | **The rule is settled. Whether it applies is not**: it needs Step T's `grep` | §5 |
| 6. #306's commands | **Final**, against the merged scripts, with five interface defects found and fixed. **The decomposition reading on posted numbers is not settled**: none are posted | §6 |
| 7. One consolidated plan text | **Written** (Part B). It becomes the plan of record once item 1 is met | Part B |

**What round 4 then needs:** only item 1's outputs, and L-A23's table applied to them. If Step T and Job 0 post
clean results (L0 passes, no class weights, t\* Dice-bound), nothing in Part B changes, except the decomposition
reading and the posted sha256 values. Round 4 could then rule converged on reading alone.

**New CPU evidence** (all in `experiments/Bridge/j1l_r3/`):

| What | Script → output | Item |
|---|---|---|
| nnU-Net 2.8.1's own planner, run at 0.5 mm and 0.45 mm on a fingerprint built from the 620's headers | `plan045.py` → `plan045.json` | 3 |
| The 115 mm view check on the 620's labels, with its rule written before the run | `view_check.py` → `view_check.json` | 3 |
| A temperature fit and a Platt fit on Janus 0's rim, with a self-test that shows why they differ | `calib60.py` (runs after Job 0) | 4 |
| A reference gate for `collect`: L-A5, L-A16, L-A17, D49 Q-R2-3, S's 1.25 %, and the looks ledger, with L-A21 self-test 9's fixtures | `gate.py` | 6 |
| `nnUNetv2_ensemble` → `threshold_export.py` → Rule T's directory layout, on nnU-Net 2.8.1 | `ensemble_chain.py` → `ensemble_chain.json` | 6 |
| Every merged script's self-test, re-run on `dev` | §6.1 | 6 |
| The label fetch, restricted to the 620 | `fetch620.py` | 3 |

## 1. Step T and Job 0 (§5 item 1): not run. What each output would change

L-A23's table stands as written. Here it is again, with what each row changes **in this plan's own items**. It is
read by round 4 on the posted numbers, and by no one before.

| Output | Result | Changes |
|---|---|---|
| Step T `SHA256SUMS` (now 4 lines) | Present, and `sha256sum -c` passes on Trillium | Nothing. Missing fingerprint line: P cannot run (L-A20). Re-copy before the Fir purge, about 2026-12-20 |
| Step T `grep -c "class-weighted CE"` | 0 in every log | §5's rule does not apply. The trainer self-test 6 asserts CE weight None |
| | > 0 in any log | **Stop before P.** §5's rule applies. It needs the weight list and which logs carry it |
| Step T `nnUNet_compile` line | `f` (expected) or another value | `train` and S export that value. The 181 s/epoch costing holds only for `f` |
| L0 `summary` / `paired` | Pass | Everything below is read |
| | Fail | Stop (L-A8). Nothing below is read. #306 is not built |
| `select.json` | t\* ∈ {0.45, 0.40, 0.35}, Dice-bound | The plan as written. Rule T applies |
| | t\* = 0.50, Dice peaking at 0.50 | The export lever is empty, and the Q4 branch is the expected verdict. **S stays 0.5 mm** (§3: the 0.45 mm form is closed) |
| | t\* = 0.30, or FP rising at every t < 0.50 | `calib60.py` runs before #306 freezes t (§4). Rule W's grid may extend to {0.25, 0.20} on the 60 (§4.3) |
| | t\* held by a guard | t_C = t\* (L-A15 scope). The binding guard is named on #302. If it is FP, `calib60.py` runs |
| | Dice(t\*) more than 0.03 below 0.934, volume ratio ≥ 0.95 | The grid binds. **S stays 0.5 mm** (§3). A finer grid goes to a round with its own decision set |
| | Dice(t\*) − Dice(0.50) < 0.003 | "H2 will likely fail on the threshold alone" is posted on #302 before training |
| `du -sh $W/probs` (**new**, §6.4) | The 160 cases' saved probabilities | Sizes `predict`'s disk. If 160 cases take more than about 0.4 TB, `predict` exports and deletes each model's `.npz` as it goes |
| Decomposition summaries | Posted | L-A22's reading, for later rounds (§6.5). Never for Janus 1-L.1 |
| MDE restatement | Posted | The verdict's stated MDE, and "under-powered" if the tF1 MDE > 0.025. No margin moves |

**One defect in the posted after-Job-0 command.** [[Master plan - Janus 1-L]] §5 sets
`T=$(python -c "...print('%.2f' % json.load(open('$W/select.json'))['chosen_t'])")`. But `decide.py select` writes
`chosen_t` as a **string** (`f'{chosen:.2f}'`), and `'%.2f' % '0.45'` raises
`TypeError: must be real number, not str` (checked here). The decomposition loop would then run only at t = 0.50, and
`$T` would be empty. **Fix:** `float(...)`, as in Part B §5.

## 2. The lead's answers (§5 item 2): met, written through

D49, 2026-11-22. Each answer replaces the "subject to" clause it settles:

| Answer | What it fixes in the plan |
|---|---|
| Q-R2-1 yes | **C = E at t_C** (L-A14). a2 ships only as one of E's two members. a1 at t_C is C only under the a2-failure fallback, decided from logs. L-A19's member-wise pool fine-tunes apply |
| Q-R2-2 yes | **Rule T runs on D60** (L-A15). `predict` covers D60 for folds 0 and 1 and for Janus 0. No label or ImageCAS mask of a D60 case is read. `fetch_cases.py` without `--masks` fetches none |
| Q-R2-3 yes | **The Q4 row gains "and whole-tree Dice not shown worse"**: the one-sided upper bound of Δ Dice ≥ 0. `gate.py` implements it, and its self-test 3 refuses a model with tF1 lower bound −0.012 and Dice shown worse |
| Q-R2-4 yes | **S runs on its trigger without another round**: 0.5 mm (§3), ≈ 53 GPU-h, look at 1.25 % |

These leave no open question for the lead in this track's first look.

## 3. S's form (§5 item 3): 0.5 mm in every Job 0 outcome

### 3.1 What the 0.45 mm grid would actually give

`plan045.py` runs nnU-Net 2.8.1's own `ResEncUNetPlanner` with `gpu_memory_target_in_gb=60`, as Janus 0 was planned
(`trillium/icx4/lib/prepare.py`). It runs on CPU, on a fingerprint built from the 620's label headers. The labels
share their CT's grid, and cropping to nonzero leaves a full-field-of-view CT unchanged. Intensity properties do not
enter the patch or batch choice. The 620's median spacing is 0.5 × 0.35 × 0.35 mm (z, y, x), and the median shape is
275 × 512 × 512.

| Target | Patch | Batch | View | Median image (voxels) | Network |
|---|---|---|---|---|---|
| 0.5 mm | 256³ | 2 | **128.0 mm** | 275 × 358 × 358 | 7 stages, 32 → 320 |
| 0.45 mm | 256³ | 2 | **115.2 mm** | 306 × 398 × 398 | the same |

- **The 0.5 mm row reproduces Janus 0's recorded planner output** (`trillium-results/icx14/results/planner_output.json`:
  256³, batch 2). So the stand-in fingerprint gives what the real one gave.
- **At 0.45 mm the memory target binds, not the image size.** The planner keeps 256³ and batch 2, and the view
  shrinks to 115.2 mm. The "115 mm view" of Round 1 is what nnU-Net itself would choose, not an assumption.
- **The cost is lower than costed.** With the same patch, batch and 250 iterations per epoch, an epoch costs the
  same 181 s. Only preprocessing and inference grow, by (0.5/0.45)³ = 1.37×. So S at 0.45 mm would be ≈ 53–55 GPU-h,
  not 55–60. This is moot after §3.2.

### 3.2 The view check, with its rule fixed before the run

`view_check.py` reads the 620's ImageCAS-X labels only. It collapses them by `territory.to_four` and refuses any id
outside the 620. It reads no CT, and no aorta (those are TotalSegmentator outputs). **The rule was written in the
script's docstring and committed before the first run** (commit `Bridge v3 … view check (WIP)`):
- **V1:** the share of cases whose whole tree fits in one cube may fall by at most 10 percentage points against
  128 mm;
- **V2:** in every class, the share of voxels whose tree root lies inside a cube centred on them may fall by at most
  5 points. This is the best-placed sliding window's context: can the network see where a vessel comes from when it
  labels a voxel? The left root is the LM centroid. The RCA root is the RCA voxel nearest it.

**Result (620 cases):**

| | 128 mm (0.5 mm) | 115.2 mm (0.45 mm) | 102.4 mm (0.4 mm, report) |
|---|---|---|---|
| Whole tree fits | 97.3 % | **78.2 %** (−19.0 pp) | 28.2 % |
| Left tree fits | 100 % | 99.7 % | 87.1 % |
| RCA fits | 99.8 % | 99.4 % | 97.6 % |
| Best cube's share of the tree, p10 | 1.000 | 0.992 | 0.930 |
| Root in view, LM | 100 % | 100 % | 100 % |
| Root in view, LAD | 89.7 % | 83.8 % (**−5.8**) | 76.1 % |
| Root in view, LCx | 95.1 % | 90.2 % (−4.9) | 83.5 % |
| Root in view, RCA | 94.4 % | 86.2 % (**−8.2**) | 73.7 % |

The tree's extent is 107 × 90 × 86 mm at the median, and 120 × 102 × 99 mm at p90. The long axis is the one a
115 mm cube cuts.

**Verdict: FAIL** on V1 and on V2 (LAD, RCA). A 128 mm cube holds the whole tree in 97 % of cases. A 115 mm cube holds
it in 78 %, and it loses the RCA's root from view at 8 % more of the RCA.

**Caveats, stated:**
- The roots are proxies.
- The check measures context, not accuracy. Whether a 115 mm view actually costs tF1 was not measured, and cannot be
  without a run.
- The thresholds (10 and 5 points) are mine. I fixed them before the run, and the result is not near them on V1.

### 3.3 The ruling on S's form

- **S is 0.5 mm, in every Job 0 outcome.** It is Janus 0's plans moved to dataset 718 exactly as for P, so it has no
  plans step and needs no view check. Its warm-start question is the only thing it tests (L-A18).
- **The 0.45 mm form is closed for track 1-L.** It would change the spacing and cut the view. A failure could then
  not be attributed, and a success would carry a context loss that tF1 has not been asked about.
- **A 288³ patch at 0.45 mm (129.6 mm) is not proposed.** It is 1.42× the memory the planner targeted. It would need
  batch 1 or a new memory target, so the batch would change as well as the spacing: a third change.
- **A finer grid goes to a later round with its own decision set** (L-A18's look budget), if Job 0 sets the grid
  trigger. Its first CPU step is this check, re-run at its patch.

**How t\* and Rule T carry to S** (needed in any form):
- Rule T works on exported masks on each case's own grid, so it is indifferent to the network's spacing.
- t_S is Rule T run on S's D60 probabilities against Janus 0 at t\*, with L-A15's scope clause (a guard-held t\*
  gives t_S = t\*).
- No "t = 0.50" export is needed for S.

**S's commands** are in Part B §5.6. Its cost is ≈ 53 GPU-h: three chained 23:50 jobs at 181 s/epoch, plus predict
≈ 1.5 GPU-h.

## 4. Calibration (§5 item 4): a temperature cannot see an inward rim

### 4.1 The finding

The ruling names "a temperature fit on Janus 0's probabilities" as the calibration check (L-A23). **A single
temperature cannot move the export boundary.**
- p_T = softmax(log p / T) rescales every log-odds about 0. For vessel against background, p_T ≥ 0.5 exactly where
  p ≥ 0.5. With five classes this holds up to the split of probability among the four vessels.
- So a temperature fit says whether Janus 0 is over- or under-confident. It says nothing about **where** its 0.5
  crossing sits. And where it sits is Janus 0's measured defect: the boundary is one voxel inside ImageCAS-X's, on a
  dim rim ([[Janus 1-L Round 1]] §3.2).

**`calib60.py --selftest` shows it.** The fixture is a tube whose true boundary is at r = 4 voxels, while the
network's 0.5 crossing is at r = 3.

| Fit | Fitted | Raw threshold its export equals | Rim ECE |
|---|---|---|---|
| None | — | 0.50 | 0.300 |
| Temperature | T = 1.04 | **0.498** (mask Dice 1.000 with argmax) | 0.300 |
| **Platt**, a·logit(p_fg) + b | a, b | **0.125** (the truth: 0.119) | **0.015** |

### 4.2 The check, as run after Job 0 (only on L-A23's triggers)

`calib60.py` reads Job 0's saved probabilities and the ImageCAS-X labels of the **tuning 60 only**. It refuses every
other case: the locked 100, D60 and the sealed cases. It fits on voxels in each tree's bounding box plus 10 voxels,
and reports:
- **T** (as the ruling asks), and the raw threshold the temperature export equals (expected ≈ 0.50);
- **Platt's a and b**, and **t_eq = sigmoid(−b/a)**: the raw foreground probability at which Janus 0's calibrated
  vessel probability is 0.5;
- the rim ECE: raw, under the temperature, and under Platt;
- far FP: the mean raw foreground probability of predicted voxels more than 1.5 mm from the reference.

**Cost:** CPU, the login node, ≈ 20–40 min with `--np 8`. Its command is in Part B §5.2.

### 4.3 The reading, fixed now

- **Rule W is not re-run on calibrated probabilities.** Platt's map is monotone, so "calibrated ≥ 0.5" is exactly
  "raw ≥ t_eq". Rule W's grid already offers that export, if t_eq is in range. t_eq is the NLL answer to Rule W's
  Dice question. It is a cross-check, not a second rule.
- **|t_eq − t\*| ≤ 0.05:** calibration agrees with Rule W. Nothing changes.
- **t\* = 0.30 (the grid's edge) and t_eq < 0.275:** Rule W's grid extends by {0.25, 0.20} on the same 60, with the
  same guards. `decide.py select` takes any keys, so it is one more scorer run per t. This is a choice on the tuning
  60 only, made before #306 freezes t. Rule T's grid already reaches 0.25.
- **FP rising at every t < 0.50, with far-FP mean probability ≥ 0.35:** the FP is confident, not a rim effect. t\*
  stays as Rule W chose it, since its FP guard already bounds it. The next round reads the decomposition's `stray`
  share.
- **Anything else:** report only.

## 5. Class-weighted CE in Janus 0's run (§5 item 5)

**What would be found.** icx4's `_build_loss` reads `$W/ce_class_weights.json` when a chunk of the chain starts. It
then logs `ICX4: class-weighted CE from <path>: [w0, …, w4]` in that chunk's `training_log_*.txt`. Each chained job
writes its own log. So Step T's `grep -c` per file says **which chunks** trained with weights, and the log line says
**which weights**.

**The rule (decided from the logs, before P, with no locked-100 number):**

| Logs show | Then |
|---|---|
| 0 in every file | Stock DiceCE. Self-test 6 asserts CE weight None |
| Weights w in the **last** chunk (Janus 0 ended under w) | **Add w to the fine-tune**, for all 250 epochs. `nnUNetTrainer_janus1l._build_loss` sets `inner.ce.weight = w` (icx4's own two lines) from a frozen `ce_weights.json` posted on #302 with its sha256. Self-test 6 asserts CE weight == w. S, if it runs, replays Janus 0's chunk schedule: w from the epoch at which the first weighted log starts |
| Weights only in **earlier** chunks | Janus 0 ended under the stock loss. The fine-tune stays stock. The report names the history |
| Different weights in different chunks | Use the last chunk's, as above |

**Why add rather than accept a recipe change.** A fine-tune continues the loss its checkpoint converged under. If it
drops the weights, Δ mixes "620 cases instead of 560" with "weights removed". H1 could then not tell which moved LCx,
the class weights usually push. "The same recipe" (L-A2) is what makes Δ attributable.

**What it costs:** nothing, either way. The verdict states "fine-tuned with Janus 0's class weights [w]" when they
apply.

## 6. #306's commands, final (§5 item 6)

### 6.1 The merged scripts, re-read and re-tested on `dev`

Every self-test was re-run here on `dev` at `db02b25`:

| Script | Interface (read from source) | Self-test |
|---|---|---|
| `Crucible/j1l_r1/threshold_export.py` | `--probs DIR` (`<case>.npz` with `probabilities` + `<case>.nii.gz`), `--out DIR`, `--t …` (default 0.5 to 0.3), `--np`. Writes `<out>/t%.2f/<case>.nii.gz` and `voxels.json`. Refuses sealed ids | passed |
| `Crucible/j1l_r1/decide.py select` | `--scores t0.50=F …`. Writes `chosen_t` **as a string** and `per_threshold[t]` with `tf1`, `dice`, `fp`, `recall`, `qualifies` | passed |
| `Delta/j1l_r2/rule_t.py` | `--j0 DIR --cand DIR --select select.json --out F --np`. Reads `j0/t{t*}` and `cand/t{t}` for **t ∈ {0.60, 0.55, …, 0.25}**, D60 only. Prints the JSON and `sha256 <hex>` | passed |
| `Atlas/r9_score_icx4.py` | `--pred --icx --aorta --layout --splits --set val --out --np`. Scores `splits['val']`, refuses sealed ids | passed |
| `Bridge/j1l_r2/error_decomp.py` | `--pred --icx --aorta --layout --np --out`. Takes its cases from `lists.json` `tuning60` only | passed |
| `Delta/j1l_r2/mde_from_job0.py` | one positional argument: `locked100_janus0_argmax.json` | (no self-test; reads `per_class`, `flagged_classes`, `dice.tree`, which r9 writes) |
| `Bridge/j1l_r3/gate.py` (**new**) | `--base --cand [--j0tc] --model --alpha --ledger`. Refuses any id outside the locked 100 (pin checked) | passed (9 fixtures) |
| `Bridge/j1l_r3/calib60.py` (**new**) | `--probs --icx --select [--fp-rises] --out --np`. Tuning 60 only | passed |

### 6.2 Five interface defects, fixed in the command block

1. **`nnUNetv2_ensemble` writes no probabilities unless `--save_npz`.** nnU-Net 2.8.1 `ensemble.py` l. 45–46 and 122.
   Without it E has only an argmax `.nii.gz`. `threshold_export.py` then finds no `.npz` and exits, so neither Rule T
   nor the export at t_C can run. `ensemble_chain.py` checks this on nnU-Net 2.8.1 itself:
   - no `--save_npz` means no `.npz`;
   - with it, E's `.npz` is the exact mean of the two folds;
   - `threshold_export` at 0.50 reproduces the ensemble's own segmentation;
   - two copies of one fold reproduce that fold (L-A21 self-test 8).

   **All four checks passed.**
2. **Rule T needs eight exports, and Job 0's default makes five.** `rule_t.py` opens `t0.60 … t0.25`. Every
   candidate export on D60 must pass `--t 0.6 0.55 0.5 0.45 0.4 0.35 0.3 0.25`. Janus 0 on D60 needs only t\*.
3. **Janus 0 at t_C may not exist.** Job 0 exports the locked 100 at {0.50, …, 0.30}. Rule T can choose t_C = 0.25. So
   `collect` exports Janus 0 at t_C from Job 0's saved probabilities whenever `$W0/thr/t$TC` is missing.
4. **`'%.2f' % chosen_t` fails**, because the value is a string (§1). Every block below uses `float()`.
5. **`move_plans_between_datasets` rewrites a third field, `plans_name`, and with a different `-tp` a fourth,
   `data_identifier`** (l. 34–43, 56–57). The L-A21 plans check ("equal except `dataset_name` and
   `image_reader_writer`") holds only if `-tp` equals `-sp`. The block passes the same name, and the check also
   asserts `plans_name` and `data_identifier` unchanged.

Two smaller ones:
- `SEGTRAIN_MAX_SECONDS` = 23:50 − 30 min = **84 000 s**. Bridge v2's 84 600 was 30 min − 10 min short.
- The val-80 identity split is built from `lists.json` `locked20_of_open36`, which exists. `janus1_split_proposal.json`
  names it `locked20_from_open36`. Both lists hold the same 20, and the block reads `lists.json` only.

### 6.3 `collect`'s gate

`gate.py` is the reference implementation for #306. #306 may import it, or must reproduce its nine fixtures:
1. tF1 lower bound −0.017 with H2 failing gives **not adopted**.
2. Lower bound −0.012 gives **adopted (D46 Q4)**.
3. The same with Dice shown worse gives **not adopted (Q-R2-3)**.
4. FP of 1.2 per case fails H1.
5. A uniform −0.03 LCx recall loss fires L3.
6. A heavy-tailed null (t₃, SD 0.05) fired L3 in **0 of 100** draws. That is consistent with L-A17's 3–8 %, which was
   measured on the real sibling differences, not on this null.
7. H1 + H2 + H3 with s ≥ 0.8 prints the threshold share sentence.
8. A lower bound that clears −0.02 at 2.5 % by 0.0005 fails at S's 1.25 %.
9. A non-locked id is refused.

**One reading to confirm.** L-A18 says "every bound at one-sided 1.25 %" for S. `gate.py` applies α to the decision
bounds: H1's macro bound, Q4's bound, Q-R2-3's Dice bound, H2 and H3. **L3's 95 % upper bound stays as L-A17 fixes
it**, because L3 is a guard that protects a class, not a claim. Tightening it would make the guard fire less often.
If the judge reads "every bound" to include L3, the change is one argument.

### 6.4 Disk

Each saved probability file is (5, z, y, x) float32 at the original resolution. That is ≈ 1.4 GB per case
uncompressed, and an unmeasured size compressed.
- `predict` writes 160 cases × 3 models (a1, a2, Janus 0 on D60 only) plus E.
- Job 0 writes 160 such files first, so its `du -sh $W/probs` (§1) is the measurement.
- **The block exports each model's grid as soon as its predictions finish.** It keeps only E's and a1's locked-100
  `.npz` (for t_C), and deletes the rest after their `voxels.json` is written. Rule T reads only exports.

### 6.5 The decomposition reading on the posted numbers

**Not possible: none are posted.** The reading is L-A22's, applied by round 4 to the two `summary` blocks:
- each group's macro ceiling: ≥ 0.030 an arm may be costed, 0.015–0.030 only after a no-training test on the 60,
  < 0.015 no arm;
- extent is ruled out if more than half its `distal` points lie below A23's contrast line;
- extent → Skeleton Recall, breaks → a connectivity lever with its own evidence, naming → the namer or CE weights,
  width → the threshold;
- LCx is read first.

It decides nothing for Janus 1-L.1.

### 6.6 The block

It is in Part B §5, written for the lead.
- The `./janus1l` modes are L-A21's.
- Under each mode are the exact calls it must make. #306's dry run prints them, so the launcher can be checked line
  by line against this text.
- No line runs a script that is not on `dev` today, except `trillium/janus1l` itself and `nnUNetTrainer_janus1l`.

## 7. One consolidated plan text (§5 item 7)

Part B below is [[Master plan - Janus 1-L]] with L-A1 to L-A25, D49 and this candidate's round-3 amendments written
through. No clause is superseded or left "subject to". The judge can adopt it as the master plan's text with the
round number changed.

**Round-3 amendments proposed (B-A1 to B-A6):**
- **B-A1. S is 0.5 mm** (§3). L-A18's "round 3 decides its form" becomes "0.5 mm".
- **B-A2. The calibration check adds a Platt fit** (§4). L-A23's calibration rows read t_eq, not T alone, by §4.3's
  rule.
- **B-A3. The class-weight rule** (§5).
- **B-A4. The five interface fixes** (§6.2) and the disk rule (§6.4).
- **B-A5. `gate.py`'s nine fixtures are self-test 9**, with α applied as §6.3 states.
- **B-A6. Job 0's post adds `du -sh $W/probs`** (§1).

## 8. Cost

Unchanged from L-A25, except S.

| Job | GPU-h |
|---|---|
| Job 0 | 3–4 |
| P | ≈ 1 |
| a1 + a2 (concurrent, no final validation) | ≈ 25–27 |
| predict (2 folds × the locked 100 and D60; Janus 0 × D60) | ≈ 3 |
| transfer, collect, decomposition, MDE, calibration | 0 (CPU) |
| **Total** | **≈ 33–35**, ceiling ≈ 60 |
| S (0.5 mm), only on its trigger (D49 Q-R2-4) | +≈ 53 |

## 9. Questions for the lead

None. D49 answered every open question for this look. §5's class-weight rule and §4's grid extension are decided by
logs and by the tuning 60, before any locked-100 number. They follow rules fixed here, and need no new decision.

**Action, not a decision:** Step T before the Fir purge, about 2026-12-20. Its commands are unchanged (Part B §5.1).

## 10. What would change this plan

| Observation | Then |
|---|---|
| Step T or Job 0 posts its outputs | Round 4 applies §1's table. If L0 passes, there are no class weights and t\* is Dice-bound, Part B stands as written |
| L0 fails | Stop. Round 4 plans around the cause |
| Class weights found | §5's rule. `ce_weights.json` is posted before P |
| `calib60.py` gives t_eq ≤ 0.275 with t\* = 0.30 | Rule W's grid extends (§4.3) before #306 freezes t |
| The judge rejects V1/V2's thresholds | S's form reverts to "0.45 mm on Job 0's grid trigger". Part B §5.6 then needs a plans step, which this plan does not write |
| `du -sh` shows > 0.4 TB for 160 cases | `predict` deletes as §6.4 says. No other change |

## 11. Evidence index

| Claim | Source |
|---|---|
| The planner keeps 256³ / batch 2 at 0.45 mm (115.2 mm), and reproduces Janus 0's 0.5 mm plan | `experiments/Bridge/j1l_r3/plan045.py`, `plan045.json` (nnU-Net 2.8.1 `ResEncUNetPlanner`, 60 GB); `trillium-results/icx14/results/planner_output.json` |
| The view check fails V1 (−19.0 pp) and V2 (LAD −5.8, RCA −8.2) | `view_check.py`, `view_check.json` (620 labels; rule committed before the run) |
| A temperature cannot move the 0.5 crossing; Platt's bias can | `calib60.py --selftest` |
| Without `--save_npz` there are no E probabilities; with it the chain works | nnU-Net 2.8.1 `ensembling/ensemble.py` l. 45–46, 122; `ensemble_chain.py`, `ensemble_chain.json` |
| `move_plans` rewrites `plans_name`, and `data_identifier` when `-tp` differs | nnU-Net 2.8.1 `move_plans_between_datasets.py` l. 32–43, 54–57 (wheel read 2026-11-23) |
| `chosen_t` is a string; `'%.2f' %` on it fails | `experiments/Crucible/j1l_r1/decide.py` l. 81 (`select`); checked in Python 3.13 |
| The gate implements L-A5, L-A16, L-A17, Q-R2-3 and S's α | `gate.py --selftest` (9 fixtures) |
| icx4's class-weight hook and its log line | `trillium/icx4/lib/icx4_trainers.py` l. 29–39 |
| The merged scripts' interfaces | §6.1, read at `dev` `db02b25` |

**Data:**
- Read: the 620 D45 training labels only, by `fetch620.py` (ImageCAS-X, Zenodo, range reads). Their headers were used
  for the planner, and their voxels for the view check.
- Committed: only the summary. No per-case row.
- Not read or opened: no locked-100 label, no sealed or quality-0 label, no TotalSegmentator file, no CT, no pool read.
- No GPU job was run, and nothing ran on Fir, SciNet or Trillium.

---

# Part B. The consolidated plan text (for the master plan)

*Track 1-L's plan as it would stand once round 4 reads Step T's and Job 0's outputs and finds them clean: L-A1 to
L-A25, D45, D46, D49 and B-A1 to B-A6, written through. Brackets are filled from the posted outputs.*

## B0. In one paragraph

**Janus 1-L is Janus 0 fine-tuned warm on D45's 620 ImageCAS-X cases, twice, and shipped as the ensemble of the two.**
- The repository's A17a trainer (`nnUNetTrainer_janus1l`, a thin subclass with final validation skipped).
- 250 epochs, peak LR 1e-2.
- Janus 0's plans, moved to dataset 718 (identical except `dataset_name` and `image_reader_writer`).
- Mirroring off.
- [Janus 0's class weights w, only if Step T found them (B-A3).]
- **a1** and **a2** are folds 0 and 1 of one split entry. **C = E**, the mean softmax of a1 and a2, exported at
  **t_C** (D49 Q-R2-1).

**Width.**
- **Rule W** chooses t\* on Janus 0's probabilities for the tuning 60, by Dice with tF1, FP and recall guards.
- **Rule T** carries the width t\* gives to E. It does this by matching local radius on the shared centreline of 60
  unlabelled quality-0 CTs (D60, D49 Q-R2-2).
- Both are frozen before the look.

**The decision.** The locked 100 judge E at t_C against Janus 0 at argmax, once:
- **H1:** tF1 non-inferior at −0.02, with class, recall (L3) and FP guards;
- **H2:** whole-tree Dice superior;
- **H3:** tF1 superior.

A non-inferior, not-better E is adopted only if H1's lower bound is above −0.015 **and its whole-tree Dice is not shown
worse** (D46 Q4, D49 Q-R2-3).

**Fallback.** One fallback is pre-registered: **S**, Janus 0's recipe from scratch on the 620 at 0.5 mm, with its own
look at 1.25 %. The lead runs it on its trigger (D49 Q-R2-4).

**Cost:** ≈ 33–35 Trillium GPU-h; S +≈ 53.

## B1. Data (L-A1, L-A15, D49 Q-R2-2)

| Set | Cases | Use |
|---|---|---|
| **Train 620** | ImageCAS-X train 560 + dev 44 + c0123 c0195 c0340 c0416 c0430 c0435 c0447 c0617 c0624 c0660 c0726 c0758 c0772 c0877 c0971 c0984 | Training (folds 0 and 1, identical) |
| ↳ **tuning 60** | dev 44 + those 16; never trained on by Janus 0 | Rule W (Job 0); calibration if triggered. The 10 lowest ids are nnU-Net's fold val (in-sample display only) |
| **Locked 100** | val 80 + c0068 c0102 c0251 c0271 c0323 c0327 c0470 c0545 c0592 c0620 c0644 c0805 c0807 c0824 c0827 c0841 c0908 c0946 c0957 c0996 | The decision. Never trained on, never used to choose anything, never nnU-Net's val |
| **D60** | 60 unlabelled ImageCAS quality-0 CTs (`experiments/Delta/j1l_r2/drift60.json`, pin `916e8a18…004e`) | Rule T only. CT images only; no label or ImageCAS mask read; nothing trained on them; only Janus 0's and the candidate's predictions compared (D49) |
| Sealed | ImageCAS-X test 80 + quality-0 20 | **Never read, predicted, scored or trained on** |

- **Pins:** sha256 of the sorted ids joined by `\n`:
  - locked 100: `bbd9c687818956e2d5664b06fd8c8bd02ddb031e9b9d08036d59cc0e1a4d5895`;
  - train 620: `1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152`.
- **File of record:** `experiments/Delta/j1l_r1/janus1_split_proposal.json` (sha256 `19b832fe…4dd3`), which becomes
  `configs/janus1/split-2026-11.json` under #306.
- **Labels:** ImageCAS-X as drawn (D8), collapsed by `trillium/icx4/lib/territory.py` (D25, D1, D1b).
- **Pool reads:** none in Janus 1-L. When A39's counts are met, the pool fine-tunes run **member-wise** (L-A19):
  - pool a1′ from a1 and pool a2′ from a2, and the candidate is E′;
  - G1's replicate clause becomes "each member's Δ > 0", and G2 and L3 compare E′ with E on the locked 100;
  - the 620 are the replay set, and D35 decides;
  - D44 reads collapse to four by territory before D40, with PDA and PLB by side; D46 Q8 for material classes.

## B2. Recipe (L-A2, L-A3, L-A14, L-A20, L-A21, B-A3)

| Item | Setting |
|---|---|
| Start | Janus 0 `checkpoint_final.pth` (Dataset715). Full strict load with heads, bitwise-checked, sha256 logged (`SEGTRAIN_FINETUNE_FROM`) |
| Trainer | `nnUNetTrainer_janus1l` = `nnUNetTrainer_segtrain_finetune` (A17a) whose `perform_actual_validation` returns at once. [If B-A3 applies: its `_build_loss` sets CE weight = w from the posted `ce_weights.json`] |
| Plans | Janus 0's `plans.json`, copied to `$nnUNet_preprocessed/Dataset715_ICX4/nnUNetResEncUNetPlans_60G_iso05.json`, then `nnUNetv2_move_plans_between_datasets -s 715 -t 718 -sp P -tp P` (same name), then `nnUNetv2_preprocess` only. **No fingerprint step, no plan step.** Janus 0's `dataset_fingerprint.json` is placed in the new preprocessed folder. **Check:** the moved plans equal Janus 0's once `dataset_name` and `image_reader_writer` are removed. `plans_name` and `data_identifier` are unchanged. `finetune_load.check_compatible` passes |
| Schedule | 2500-iteration linear warm-up to 1e-2, then poly; SGD, Nesterov 0.99; 250 epochs × 250 iterations |
| Loss, augmentation | DiceCE with deep supervision. Class weights only by B-A3. nnU-Net default augmentation, **mirroring off** in training and inference |
| Split | `splits_final.json`: two identical entries. Train = the 620; **val = the 10 lowest-id cases of the tuning 60** |
| Environment | `SEGTRAIN_CT_WINDOW=off`, `SEGTRAIN_SAVE_EVERY=10`, `SEGTRAIN_SAVE_PROBABILITIES=0`, `SEGTRAIN_MAX_SECONDS=84000`, `nnUNet_compile` = Janus 0's (Step T). `SEGTRAIN_EPOCHS` and `SEGTRAIN_ITERATIONS` unset. segtrain installed editable, or `SEGTRAIN_SEALED_LIST` and `SEGTRAIN_POOL_SEAL` exported |
| Checkpoint, inference | `checkpoint_final` only, never `checkpoint_best`. `--disable_tta --save_probabilities` |
| Runs | **a1** = fold 0, **a2** = fold 1, concurrent. **C = E** = `nnUNetv2_ensemble --save_npz` of the two folds' probabilities |
| Fallbacks, from logs | a2 not at 250 epochs within two chained jobs: C = a1 at t_C (Rule T on a1). a1 not finished: nothing is scored; the PM reports |
| Not in this plan | Skeleton Recall or another topology loss, the 1e-3 arm, a new spacing (S is 0.5 mm, B-A1), from-scratch training except S |

### B2.1 Rule W: the export threshold (L-A4)

- **Data:** Janus 0's probabilities on the tuning 60 (Job 0).
- **Grid:** t ∈ {0.50, 0.45, 0.40, 0.35, 0.30}, extended to {0.25, 0.20} only by B2.3's rule. A voxel is vessel where
  the summed vessel probability is ≥ t, and its class is the argmax among the four vessels.
- **Choice:** the highest mean whole-tree Dice, subject to:
  - tF1 ≥ tF1(0.50) − 0.005;
  - FP per case ≤ FP(0.50) + 0.10;
  - no class's centreline recall falls.
- **Ties** (Dice within 0.002) go to the larger t.
- **Code:** `experiments/Crucible/j1l_r1/decide.py select`.
- **Frozen:** `select.json` is posted on #302 with its sha256: **t\* = [ ]**, sha256 [ ].

### B2.2 Rule T: carrying the width to E (L-A15)

- **Reference:** Janus 0 at t\* on D60: its skeleton, and the local radius (EDT) on it.
- **Measure:** dr(t), the 10 %-trimmed mean of E(t)'s radius minus Janus 0's, on the reference centreline points E(t)
  covers, pooled over D60.
- **Choice:** t_C = the t ≤ 0.50 on {0.50, …, 0.25} with the smallest |dr|. Ties within 0.005 mm go to t\*, then to
  the larger t.
- **Scope:** if t\* was held back by a guard (Dice at t\* more than 0.002 below the grid's best), t_C = t\*.
- **Reports:** a1's and a2's dr(t). If they shift in opposite directions, the report says it is seed noise.
- **Code:** `experiments/Delta/j1l_r2/rule_t.py`.
- **Frozen:** `rule_t.json` and its sha256 are posted on #302 before `collect`. `collect` refuses without them.

### B2.3 Calibration (L-A23 rows; B-A2): only if t\* = 0.30, FP rises at every t < 0.50, or t\* is guard-held

`experiments/Bridge/j1l_r3/calib60.py` runs on the tuning 60. It reports T, Platt's (a, b) and
t_eq = sigmoid(−b/a).
- **|t_eq − t\*| ≤ 0.05:** nothing changes.
- **t\* = 0.30 and t_eq < 0.275:** Rule W re-runs with {0.25, 0.20} added, the same guards, on the same 60, before
  `select.json` is frozen.
- **Confident far FP (mean p ≥ 0.35) with FP rising:** t\* stays.
- Rule W is never re-run on calibrated probabilities.

## B3. The decision on the locked 100 (L-A5 to L-A8, L-A14 to L-A18, D49)

**L0, the identity check, comes first.**
- Janus 0 re-predicted on Trillium reproduces Fir's val-80 decisive macro **0.909 ± 0.003**.
- Each class is within 0.01 of LM 0.945, LAD 0.903, LCx 0.857 and RCA 0.938.
- ≥ 95 % of cases agree within 0.01 against Fir's own predictions.
- **Otherwise stop.**

**The comparison.**
- C = E at t_C (**Janus 1-L.1**), against Janus 0 at argmax (Job 0).
- Decisive tF1 @ 1.5 mm at A1c `24441cf8…5254`, with Janus 0's A1 aortas and the A1a/A1b exclusions.
- Paired by case; bootstrap 10 000, seed 0; one-sided 2.5 %.
- **One look per model; at most two in the track** (C, and S if triggered). A looks ledger refuses a third.

| # | Test | Passes when |
|---|---|---|
| **H1** | tF1 non-inferior, nothing lost | Lower bound Δ macro tF1 > −0.02; no class mean Δ < −0.03; **L3** holds; E's FP components ≤ 1 per case |
| **H2** | Width | Lower bound Δ whole-tree Dice > 0 |
| **H3** | tF1 superior | Lower bound Δ macro tF1 > 0 |

**L3** works on the scorer's per-class `recall`. For no class may either hold:
- the 10 %-trimmed mean Δ < −0.02;
- or the mean Δ < −0.02 with a 95 % upper bound < 0.

Its stated false-alarm rate is 3–8 %, and up to about 19 % under a broad shift. Each class's excess kurtosis is
printed.

| Outcome | Verdict | Wording of record (brackets filled by `collect`) |
|---|---|---|
| H1 fails | **Not adopted.** Janus 0 stays. G5 lists five cases for any class with point Δ < −0.05. S runs if its trigger fires | "Janus 1-L.1 was not shown non-inferior to Janus 0 in tree-F1 (Δ m, 95 % CI [l, u]; margin −0.02) [or: failed the class / L3 / FP guard, named]. Janus 0 remains the model." |
| H1 passes, lower bound in (−0.02, −0.015], H2 fails | **Not adopted** | "Non-inferior to Janus 0 at 0.02 but not at the 0.015 that D46 Q4 requires for adoption without a width gain; not shown better. Janus 0 remains." |
| H1 passes, lower bound > −0.015, H2 fails, Dice shown worse (upper bound < 0) | **Not adopted** (D49 Q-R2-3) | "Non-inferior to Janus 0 in tree-F1 at 0.015 (Δ m, 95 % CI [l, u]), but its whole-tree Dice is shown worse (Δ d, 95 % CI [dl, du]). Janus 0 remains." |
| H1 passes, lower bound > −0.015, H2 fails, Dice not shown worse | **Adopted** (D46 Q4) | "Janus 1-L is non-inferior to Janus 0 in tree-F1 at a pre-specified margin of 0.015 (Δ m, 95 % CI [l, u]), and passed the class, recall and FP guards (smallest class mean Δ: [class, value]). It is not shown better in lumen width (whole-tree Dice Δ d, 95 % CI [dl, du]) or in tree-F1. Adopted for its larger training set." |
| H1 and H2 pass, H3 fails | **Adopted** | "Janus 1-L is better than Janus 0 in lumen width: whole-tree Dice +d (95 % CI [dl, du]). Its tree-F1 is non-inferior at 0.02 (Δ m, lower bound l), with the class, recall and FP guards passed. A tree-F1 gain was not shown. [Share sentence.]" |
| H1, H2 and H3 pass | **Adopted** | As above, ending "… and better in tree-F1 (Δ m, lower bound l > 0)." |

**Every adopted wording also states:**
- "a two-network ensemble of fine-tunes of Janus 0, exported at foreground threshold t_C", and whether Rule T moved
  t_C from t\*;
- [the class weights, if B-A3 applied];
- the MDE, and "under-powered" if the tF1 MDE > 0.025;
- L3's false-alarm rate;
- the val-80 and locked-20 parts, with any sign reversal reported and not acted on (A26).

**The share sentence.** s = (Janus 0 at t_C − Janus 0 at argmax) / (E − Janus 0 at argmax), in whole-tree Dice:
- s ≥ 0.8: "Most of the width gain is the export threshold, which applies to Janus 0 as well; the fine-tune adds
  [1 − s]";
- s ≤ 0.2: "Most of the width gain is the fine-tune";
- otherwise: "The threshold and the fine-tune each contribute".

**CONSORT form:** every claim prints its two-sided 95 % CI beside the margin. "Not shown better" is never written "no
better".

- **What ships is E at t_C as tested.** Never an argmax export, never a1 or a2 alone after the look.
- **Reports, which decide nothing:**
  - Janus 0 at t_C;
  - a1, a2, a1 at t_C, a1 at argmax, and E − a1 with its CI;
  - σ_g = |a1 − a2|/√2, with A37's ≥ 2-runs rule if |a1 − a2| > 0.02;
  - E's Dice and volume ratio at every t;
  - per-class tF1, Dice, tolerant Dice, volume ratio, recall, precision and FP;
  - val 80 and locked 20 apart; the 89 never-inspected cases.
- **Code:** `experiments/Bridge/j1l_r3/gate.py` (or #306's equivalent, passing its nine fixtures).
  `experiments/Crucible/j1l_r1/decide.py gate` is **not** the gate.

### B3.1 The fallback S (L-A18, D49 Q-R2-4, B-A1)

- **Trigger (all of these):**
  - H1 fails;
  - a1 at argmax **and** a2 at argmax both have a point Δ macro tF1 < 0 against Janus 0;
  - L0 passed.

  It is never triggered by one class, by L3 or by FP alone with a member ≥ 0.
- **Run:** Janus 0's recipe from scratch on the 620, **at 0.5 mm with Janus 0's plans** (dataset 718, the same
  splits).
  - `nnUNetTrainerICX4`, 1000 epochs, one run, `ICX4_SKIP_FINAL_VAL=1`;
  - class weights only as B-A3 replays them;
  - ≈ 53 GPU-h, in three chained 23:50 jobs.
- **Allocation:** the lead runs it without another round.
- **Threshold:** t_S by Rule T on S's D60 probabilities.
- **Look:** **Janus 1-L.2**, against Janus 0, in the same H1 → H2 → H3 and wording, with every decision bound at
  one-sided **1.25 %**. L3 stays as defined. A false adoption over the track is then ≤ 2.5 % + 1.25 %.
- **If S fails,** Janus 0 stays as track 1-L's model.

## B4. Naming (L-A24)

- **Janus 1-L.1** = E at t_C, or a1 at t_C under the a2 fallback.
- **Janus 1-L.2** = S, if read.
- a1, a2, Janus 0 at t_C and every argmax export are reports and take no number.
- The adopted model is **Janus 1-L**.
- D28 is met by a2 (σ_g reported).

## B5. Commands (the lead runs them)

### B5.1 Step T (Fir, then Trillium): unchanged from [[Master plan - Janus 1-L]] §5

Post on #302:
- the four `SHA256SUMS` lines;
- the three counts;
- the `grep -c` count per log, and, if any is > 0, **the logged weight line of each such log**;
- the `ls` line;
- the `nnUNet_compile` line.

### B5.2 Job 0, and the CPU steps after it

`sbatch job0_janus0_probs.sh` and the identity score are as in [[Master plan - Janus 1-L]] §5. Then, on the login
node:

```sh
source $HOME/icx14-venv/bin/activate
R=$SCRATCH/asclepius/repo; W=$SCRATCH/j1l_job0; J0=$SCRATCH/janus0
git -C $R pull --ff-only
du -sh $W/probs                                                       # post this (B-A6)
T=$(python -c "import json;print('%.2f' % float(json.load(open('$W/select.json'))['chosen_t']))")
python $R/experiments/Bridge/j1l_r2/error_decomp.py --selftest
for t in 0.50 $T; do
  python $R/experiments/Bridge/j1l_r2/error_decomp.py --pred $W/thr/t$t --icx $J0/icx --aorta $J0/aorta \
    --layout $W/layout.json --np 8 --out $W/scores/error_decomp_tuning60_t$t.json
done
python $R/experiments/Delta/j1l_r2/mde_from_job0.py $W/scores/locked100_janus0_argmax.json
# only if t* = 0.30, FP rose at every t < 0.50, or t* was guard-held (B2.3):
python $R/experiments/Bridge/j1l_r3/calib60.py --selftest
python $R/experiments/Bridge/j1l_r3/calib60.py --probs $W/probs --icx $J0/icx --select $W/select.json \
  --np 8 --out $W/scores/calib60.json          # add --fp-rises if FP rose at every t < 0.50
```

Post on #302:
- `du -sh`;
- the two decomposition `summary` blocks;
- the MDE printout;
- `calib60.json`, if run.

### B5.3 #306: `check` and `prepare` (P)

```sh
cd $SCRATCH/asclepius && git -C repo pull --ff-only
source $HOME/icx14-venv/bin/activate && pip install --no-deps -e repo        # segtrain editable (L-A21)
export R=$SCRATCH/asclepius/repo J0=$SCRATCH/janus0 W0=$SCRATCH/j1l_job0 W=$SCRATCH/j1l
export J1L_SELECT_SHA256=<select.json sha256 posted on #302>
export J1L_NNUNET_COMPILE=<Janus 0's value from Step T>
cd $R/trillium/janus1l
./janus1l check            # self-tests 1-9 (L-A21, with B-A5's gate fixtures), one OK line each; submits nothing
./janus1l prepare          # sbatch P
```

`prepare` must run, and `check` must print:

```sh
export nnUNet_raw=$W/raw nnUNet_preprocessed=$W/pre nnUNet_results=$W/res
M=$J0/nnunet_results/Dataset715_ICX4/nnUNetTrainerICX4__nnUNetResEncUNetPlans_60G_iso05__3d_fullres
P=nnUNetResEncUNetPlans_60G_iso05
# raw Dataset718_J1L: imagesTr/cNNNN_0000.nii.gz -> cases/cNNNN/ct.nii.gz; labelsTr by territory.to_four; dataset.json
mkdir -p $nnUNet_preprocessed/Dataset715_ICX4 && cp $M/plans.json $nnUNet_preprocessed/Dataset715_ICX4/$P.json
nnUNetv2_move_plans_between_datasets -s 715 -t 718 -sp $P -tp $P
cp $M/dataset_fingerprint.json $nnUNet_preprocessed/Dataset718_J1L/
python -m janus1l.plans_check $M/plans.json $nnUNet_preprocessed/Dataset718_J1L/$P.json   # B2 check; refuses on any other difference
nnUNetv2_preprocess -d 718 -plans_name $P -c 3d_fullres -np 10
# splits_final.json: [{train: 620, val: 10 lowest tuning-60 ids}] x 2
```

### B5.4 `train` (a1 and a2, concurrent; chain-resumable)

```sh
./janus1l train            # sbatch a1 and a2 (afterok:P); each resubmits itself with --c until 250 epochs
./janus1l status           # after ~2 h: expect ~181 s/epoch (if nnUNet_compile is Janus 0's)
```

Each job runs:

```sh
export SEGTRAIN_FINETUNE_FROM=$M/fold_0/checkpoint_final.pth SEGTRAIN_CT_WINDOW=off SEGTRAIN_SAVE_EVERY=10 \
  SEGTRAIN_SAVE_PROBABILITIES=0 SEGTRAIN_MAX_SECONDS=84000 nnUNet_compile=$J1L_NNUNET_COMPILE
unset SEGTRAIN_EPOCHS SEGTRAIN_ITERATIONS
nnUNetv2_train 718 3d_fullres $FOLD -tr nnUNetTrainer_janus1l -p $P [--c]        # FOLD = 0 (a1) or 1 (a2)
```

### B5.5 `predict`, `transfer` and `collect`

```sh
./janus1l predict          # sbatch (afterok a1:a2); scores nothing
./janus1l transfer         # CPU; prints rule_t.json and its sha256 -> post on #302
export J1L_RULE_T_SHA256=<posted>
./janus1l collect          # CPU; refuses without both posted sha256, refuses a second run (looks ledger)
```

`predict` runs:

```sh
Q="-d 718 -c 3d_fullres -tr nnUNetTrainer_janus1l -p $P -chk checkpoint_final.pth --disable_tta --save_probabilities"
for f in 0 1; do for s in locked d60; do
  nnUNetv2_predict -i $W/in_$s -o $W/pf$f/$s -f $f $Q; done; done
nnUNetv2_predict -i $W/in_d60 -o $W/pj0/d60 -d 715 -c 3d_fullres -f 0 -tr nnUNetTrainerICX4 -p $P \
  -chk checkpoint_final.pth --disable_tta --save_probabilities          # with nnUNet_results=$J0/nnunet_results
for s in locked d60; do nnUNetv2_ensemble -i $W/pf0/$s $W/pf1/$s -o $W/pE/$s --save_npz -np 8; done   # --save_npz: B-A4
X="python $R/experiments/Crucible/j1l_r1/threshold_export.py --np 8"
G="0.6 0.55 0.5 0.45 0.4 0.35 0.3 0.25"
for m in E f0 f1; do d=$([ $m = E ] && echo pE || echo p$m); $X --probs $W/$d/d60 --out $W/d60_$m --t $G; done
$X --probs $W/pj0/d60 --out $W/d60_j0 --t $(python -c "import json;print(float(json.load(open('$W0/select.json'))['chosen_t']))")
# then delete the d60 .npz (B-A4: Rule T reads exports only)
```

`transfer` runs:

```sh
python $R/experiments/Delta/j1l_r2/rule_t.py --selftest
python $R/experiments/Delta/j1l_r2/rule_t.py --j0 $W/d60_j0 --cand $W/d60_E --select $W0/select.json --out $W/rule_t.json --np 8
for m in f0 f1; do python $R/experiments/Delta/j1l_r2/rule_t.py --j0 $W/d60_j0 --cand $W/d60_$m \
  --select $W0/select.json --out $W/rule_t_$m.json --np 8; done                       # reports only
```

(Under the a2 fallback, `--cand $W/d60_f0` gives `rule_t.json`.)

`collect` runs:

```sh
TC=$(python -c "import json;print('%.2f' % float(json.load(open('$W/rule_t.json'))['t_C']))")
for m in E f0 f1; do d=$([ $m = E ] && echo pE || echo p$m); $X --probs $W/$d/locked --out $W/lk_$m --t 0.5 $TC; done
[ -d $W0/thr/t$TC ] && J0TC=$W0/thr/t$TC || { $X --probs $W0/probs --out $W/j0tc --t $TC; J0TC=$W/j0tc/t$TC; }   # B-A4
SC="python $R/experiments/Atlas/r9_score_icx4.py --icx $J0/icx --aorta $J0/aorta --layout $W0/layout.json \
    --splits $W0/split_locked100.json --set val --np 20"
$SC --pred $W/lk_E/t$TC --out $W/scores/E_tC.json
$SC --pred $J0TC --out $W/scores/J0_tC.json
for m in E f0 f1; do for t in 0.50 $TC; do [ $m$t = E$TC ] || $SC --pred $W/lk_$m/t$t --out $W/scores/${m}_t$t.json; done; done
python $R/experiments/Bridge/j1l_r3/gate.py --base $W0/scores/locked100_janus0_argmax.json --cand $W/scores/E_tC.json \
  --j0tc $W/scores/J0_tC.json --model "Janus 1-L.1" --alpha 0.025 --ledger $W/looks.json > $W/gate.json
```

**Send back:** `gate.json` and `collect`'s `SUMMARY.md`: the reports above, σ_g, and the per-class tables. They hold no
volumes, no weights and no sealed case.

### B5.6 S, only on its trigger (D49 Q-R2-4)

```sh
./janus1l s-train          # Dataset 718 as prepared; nnUNetTrainerICX4, fold 0, 1000 epochs, chained 23:50 jobs
```

It runs:

```sh
export ICX4_EPOCHS=1000 ICX4_SKIP_FINAL_VAL=1 ICX4_DEADLINE=<job end - 30 min, unix time> nnUNet_compile=$J1L_NNUNET_COMPILE
export W=$SCRATCH/j1l_s && test ! -e $W/ce_class_weights.json        # unless B-A3 replays Janus 0's schedule
nnUNetv2_train 718 3d_fullres 0 -tr nnUNetTrainerICX4 -p $P [--c]    # results to a separate nnUNet_results=$W/res
```

Then `predict`, `transfer` and `collect` as above, for the single model S. `collect` runs:

```sh
gate.py --base $W0/scores/locked100_janus0_argmax.json --cand $W/scores/S_tS.json \
  --j0tc $W/scores/J0_tS.json --model "Janus 1-L.2" --alpha 0.0125 --ledger $W/looks.json
```

## B6. Cost (L-A25, B-A1)

| Job | What | Waits on | GPU-h |
|---|---|---|---|
| T | Copy Janus 0 off Fir; set up on Trillium | **now** (before ~2026-12-20) | 0 |
| 0 | Janus 0 on the 160 with probabilities; Rule W; baseline and identity scores | T | 3–4 (ceiling 6) |
| 0-CPU | Decomposition, MDE, calibration if triggered | 0 | 0 |
| P | Dataset 718 with Janus 0's plans; preprocess | #306 | ≈ 1 |
| a1, a2 | 250 epochs × 181 s, concurrent | P | ≈ 25–27 |
| predict | 2 folds × (locked 100 + D60); Janus 0 × D60; ensembles | a1, a2 | ≈ 3 |
| transfer, collect | Rule T; the one look and the reports | predict | 0 |
| | **Total** | | **≈ 33–35** (ceiling ≈ 60) |
| S | 0.5 mm, from scratch, only on its trigger | the verdict | +≈ 53 |

## B7. What would change this plan

| Observation | Then |
|---|---|
| L0 fails | Stop (L-A8) |
| Class weights in Janus 0's last chunk | B-A3: the fine-tune uses them; posted before P |
| t\* = 0.50 or the grid binds | The Q4 branch is the expected verdict. S stays 0.5 mm. A finer grid goes to a later round with its own decision set |
| a2 fails twice | C = a1 at t_C |
| \|a1 − a2\| > 0.02 | A37's ≥ 2 runs per arm for later recipe claims. E's look is unaffected |
| H1 fails with both members' argmax Δ < 0 | S runs (B3.1) |
