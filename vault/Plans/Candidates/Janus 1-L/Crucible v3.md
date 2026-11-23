---
tags: [plans, candidate, track-1-L, round-3, trillium, four-class, D45, D46, D49, janus, locked-100, ensemble, commands]
author: Crucible
track: 1-L
round: 3
version: 3
updated: 2026-11-23
issue: christianGRogers/Asclepius#302
---

# Crucible v3 (Janus 1-L): not converged, because Step T and Job 0 have not run; everything that does not need their numbers is settled here, so round 4 can be a reading round

## 0. The answer in one table

The plan in force is [[Candidates/Janus 1-L/Delta v2|Delta v2]] as amended by L-A1 to L-A25 ([[Janus 1-L Round 2]]),
with D49 (the lead's yes to Q-R2-1 to Q-R2-4). Crucible v3 keeps all of it. It answers the seven items of the ruling's
§5.

| §5 item | Status in round 3 | What Crucible v3 does | § |
|---|---|---|---|
| 1. Step T and Job 0 outputs on #302 | **Not met.** Nothing has run | Says what each output would change, row by row (L-A23), and adds F0 | §1 |
| 2. The lead's answers | **Met** (D49, 2026-11-22) | Writes D49 through L-A14, L-A15, L-A16 and L-A18 | §2 |
| 3. S's form | **Settled as a rule; not yet decidable** | S is 0.5 mm unless Job 0 sets the grid trigger. For 0.45 mm: the plans step (a derived configuration, no re-plan), the 115 mm view check, **run here on the 620**, how t\* and Rule T carry, and the cost | §3 |
| 4. Calibration | **Settled as a rule** | A temperature cannot draw a mask Rule W could not draw at another raw threshold, so "re-run Rule W on calibrated probabilities" is a grid question. Pre-registered remedy per Job 0 result | §4 |
| 5. Class-weighted CE | **Settled as a rule** | If Janus 0 trained with the weights, the fine-tune uses the same file. Step T must copy it now, or it is lost in the purge | §5 |
| 6. #306's commands | **Settled, except the values Job 0 fills in** | The lead's exact block for `check`, `prepare`, `train`, `predict`, `transfer` and `collect`; every script interface read and run; **`collect`'s gate written** (`gate.py`, L-A16, L-A17, Q-R2-3) with mutation-tested self-tests; three seam defects found | §6 |
| 7. One consolidated plan text | **Done** | Part B: the master plan with L-A1 to L-A25, D49 and the round-3 amendments written through | Part B |

**Is the plan converged?** **No.** §5 says round 3 can rule convergence only if items 1 and 2 are met. Item 2 is met;
item 1 is not. Nothing in this candidate rests on a number that Step T or Job 0 will produce. **What is left for
round 4 is reading, not design:** apply L-A23's table, §3.3, §4.2 and §5 below to the posted outputs, fill t\* into
the command block, and rule. No new rule needs to be invented after Job 0 unless the identity check fails.

**This round's evidence** (CPU; code in `experiments/Crucible/j1l_r3/`; note:
[[Crucible - Janus 1-L round 3, the collect gate is written and mutation-tested, the 0.45 mm view check runs on the 620, and calibration is a grid question]]):
- `gate.py`: `collect`'s decision function. 14 self-tests, including L-A21 #9's three fixtures and D49's clause;
- `pipeline_check.py`: the seams between `nnUNetv2_ensemble`, `threshold_export.py`, `decide.py`, `rule_t.py` and
  `gate.py` on synthetic data, and a **mutation test**: six broken versions of the gate, each killed by the
  self-test (L-A21: "each must fail on a broken fixture");
- `gate_oc.py`: the gate's operating characteristics with Q-R2-3, and S's 1.25 % look;
- `s045.py`: the 0.45 mm plans derivation and the 115 mm view check, **run on the 620 training labels**;
- `calib_equiv.py`: what a temperature can and cannot change in Rule W;
- reads of nnU-Net 2.8.1's `ensemble.py`, `export_prediction.py`, `predict_from_raw_data.py`,
  `move_plans_between_datasets.py` and `plans_handler.py`, and of batchgenerators' `save_json`.

**Data used:** the 620 D45 training labels (public ImageCAS-X release, Zenodo record 21887809), fetched one file at a
time by name, so no other label's bytes were downloaded. No locked-100 number, no sealed label, no quality-0 label, no
TotalSegmentator twin, no image. Nothing ran on Fir, SciNet or Trillium.

**Disclosure.** While branching I saw the subject line of a merged commit of another round-3 candidate in `git log`
("115 mm view check fails on the 620; S is 0.5 mm"). I did not open that candidate, its note or its code. My view check
(§3.2) was written to a rule fixed before it ran, on my own definition, and its result is reported as it came out.

---

# Part A: the seven items

## 1. Item 1: Step T, Job 0 and F0 have not run. What each would change

None of these is a design input for this candidate. Each changes only a value or a branch already fixed.

### 1.1 Step T (Fir → Trillium; urgent: the purge is about 2026-12-20)

| Output | Expected | If not |
|---|---|---|
| `SHA256SUMS` (checkpoint, plans, fingerprint, lists) and `sha256sum -c` on Trillium | four lines, all OK | Stop. Copy again before the purge |
| counts 160 / 160 / 100 | as stated | A missing label or aorta: the case leaves Job 0, and L0's 95 % agreement is read on what remains. A missing Fir prediction: L0's per-case agreement is read on fewer cases |
| `grep -c "class-weighted CE"` | 0 in every log | **Stop before P.** §5: the fine-tune uses the same weights file, which Step T must also copy (§5.2, new line in the command) |
| `ce_class_weights.json` | absent | As above |
| `nnUNet_compile` line | `f` | The launcher copies whatever it is (L-A21) |

### 1.2 Job 0 (≈ 3–4 GPU-h)

L-A23's table applies unchanged. What each row means for the **commands** of §6:

| Job 0 result | §6 changes |
|---|---|
| L0 fails | Nothing below is run. #306 is not built |
| t\* ∈ {0.45, 0.40, 0.35}, Dice-bound | `TSTAR` is filled in. Nothing else |
| t\* = 0.50, Dice peaking at 0.50 | `TSTAR=0.50`. Rule T still runs (it carries Janus 0's argmax width). The 0.45 mm question opens: run §3.2's view check (already run here: §3.2) and §3.3's rule |
| t\* held by a guard | `rule_t.py` sets t_C = t\* itself (`t_star_dice_bound` false). If the guard was FP: §4.2 |
| t\* = 0.30, or FP rising at every t < 0.50 | §4.2: extend Rule W's grid on the tuning 60 (CPU, Job 0's saved probabilities), and Rule T's grid with it |
| Dice(t\*) more than 0.03 under 0.934, volume ratio ≥ 0.95 | §3.3 |
| Dice(t\*) − Dice(0.50) < 0.003 | Stated on #302 before training. Nothing in the commands changes |
| Janus 0's locked-100 per-case SD | `mde_from_job0.py`'s output is the `--mde` input of `gate.py`, which writes the MDE sentence and the "under-powered" flag |
| The decomposition summaries | §6.6: the reading. They decide later rounds only |

### 1.3 F0 (track 1-F's login-node check on Fir)

F0 recomputes the split pins on Fir's own ImageCAS-X copy. The split is shared by both tracks (L-A1). **If F0's pins
differ from `bbd9c687…5895` and `1350cb1f…1152`, track 1-L stops too**, because then Step T's labels and the 620 may
not be the files the plan names. If they match, nothing changes for 1-L.

## 2. Item 2: D49, written through

| D49 | Amendment it closes | Written through as |
|---|---|---|
| Q-R2-1 yes | L-A14's "subject to Q-R2-1" | C = E at t_C. a2 ships only as one of E's two members, never alone. L-A19 (member-wise pool runs) is in force |
| Q-R2-2 yes | L-A15's "subject to Q-R2-2" | Rule T runs on D60. The predict job keeps D60 |
| Q-R2-3 yes | L-A16's Q4 row | Adoption through D46 Q4 also needs **the upper 95 % bound of Δ whole-tree Dice ≥ 0**. A new verdict row: "not adopted: lumen width shown worse" (`gate.py`, branch `Q4 refused`) |
| Q-R2-4 yes | L-A18's "Allocation" bullet | If S's trigger fires, the lead runs S without another round |

**What Q-R2-3 costs** (`gate_oc.json`; synthetic paired data with the measured SDs, 300 draws per cell, gate.py
unchanged):

| Per-case SD of Δ (tF1, Dice) | True Δ tF1 | True Δ Dice | P(adopt), D49 | P(adopt), D46 Q4 as first written | Refused by Q-R2-3 | P(adopt), S's 1.25 % look |
|---|---|---|---|---|---|---|
| 0.038, 0.012 | 0 | −0.010 | 0.00 | 0.93 | 0.93 | 0.00 |
| 0.038, 0.012 | 0 | −0.005 | 0.02 | 0.93 | 0.91 | 0.02 |
| 0.038, 0.012 | 0 | 0 | 0.91 | 0.93 | 0.02 | 0.88 |
| 0.038, 0.012 | 0 | +0.005 | 0.94 | 0.94 | 0 | 0.93 |
| 0.038, 0.020 | 0 | −0.005 | 0.31 | 0.88 | 0.57 | 0.30 |
| 0.038, 0.020 | 0 | 0 | 0.91 | 0.92 | 0.02 | 0.89 |
| 0.038, 0.012 | −0.01 | 0 | 0.23 | 0.23 | 0 | 0.14 |
| 0.038, 0.012 | −0.01 | +0.005 | 0.70 | 0.70 | 0 | 0.60 |
| 0.055, 0.012 | 0 | 0 | 0.73 | 0.73 | 0.01 | 0.65 |
| 0.055, 0.012 | 0 | −0.005 | 0.03 | 0.76 | 0.73 | 0.03 |

(All 40 cells are in `gate_oc.json`. The Dice SDs are assumptions: no paired Δ Dice SD is on record outside the
locked 100, and this round reads no locked-100 number.)

**What it says:**
- **With the width truly matched (Δ Dice = 0), Q-R2-3 costs 1–2 points of adoption,** as a 2.5 % guard should.
- **It bites hard on a small real width loss.** The locked 100 resolve whole-tree Dice to about ±0.002–0.004, so a
  true −0.005 is refused 57–93 % of the time. The clause does what D49 asked; the consequence is that **Rule T's
  residual mismatch now matters**. Rule T picks t_C on a 0.05 grid. If half a grid step leaves C's width a few
  thousandths of Dice off Janus 0's optimum, an otherwise adoptable candidate can be refused. R3-A8 (§7) halves the
  step at no GPU cost.
- **S's 1.25 % look** costs 3–9 points of adoption against C's look, as L-A18 intended.

**One reading for the judge (§6.4): which bounds move to 1.25 % at S's look.** L-A18 says "every bound at one-sided
1.25 %". Read literally, it also widens the two **guards** that deny adoption: L3's 95 % upper bound and Q-R2-3's
Dice upper bound. A wider interval makes a guard fire less, so S's look would be *more* lenient on recall and width
than C's, which is the opposite of what the 1.25 % is for. **`gate.py` applies 1.25 % to the bounds that grant a
claim** (H1's, H2's and H3's lower bounds and Q4's −0.015) **and keeps the guards at C's level.** This is a reading of
L-A18, not a change of a D-number; it is flagged as R3-A3.

## 3. Item 3: S's form

### 3.1 The rule

- **S is 0.5 mm** (Janus 0's plans, the warm-start question only) **unless Job 0 sets the grid trigger** (L-A23:
  t\* = 0.50 with Dice peaking at 0.50, or Dice at t\* more than 0.03 under 0.934 with volume ratio ≥ 0.95).
- If the trigger fires, **S is 0.45 mm only if the view check passes** (§3.2). Otherwise S stays 0.5 mm, and the
  0.45 mm question goes to the round after the verdict as an explicit two-change proposal (grid and view), with its
  own decision set (a third look is barred, L-A18).

### 3.2 The 115 mm view check, run on the 620

At 0.45 mm, Janus 0's 256³ patch spans 115.2 mm instead of 128 mm. A tree larger than the patch is normal at both
spacings (sliding-window inference tiles it). What changes is how much of the tree, and how much ostium-to-branch
context, one training patch can hold.

**The measure** (`s045.py view`, rule fixed in the script before it ran): per case, cover(v) is the largest share of
the tree's labelled voxels that one axis-aligned v-mm cube can hold (summed-area table on a 2 mm grid).
**PASS** if the median cover at 115.2 mm is within 0.05 of the median at 128 mm, and the 10th percentile within 0.08.

**Result on the 620 training labels:**

<!-- VIEW_TABLE -->

### 3.3 If S is 0.45 mm: the plans step, the threshold and the cost

- **Plans step** (`s045.py plans`, self-tested): Janus 0's plans gain one configuration, `3d_fullres_045`, that
  `inherits_from` `3d_fullres` (nnU-Net 2.8.1 `plans_handler` l. 237) and changes only `spacing` → 0.45 mm,
  `data_identifier` (so preprocessing cannot overwrite the 0.5 mm folder) and the informational median size. Patch,
  batch, network and normalisation are inherited. No `plan_experiment`, no fingerprint step. The self-test refuses a
  derived file that changes anything else.

  ```sh
  python $R/experiments/Crucible/j1l_r3/s045.py plans --in $nnUNet_preprocessed/Dataset718_Janus1L/nnUNetResEncUNetPlans_60G_iso05.json \
      --out $nnUNet_preprocessed/Dataset718_Janus1L/nnUNetResEncUNetPlans_60G_iso05.json
  nnUNetv2_preprocess -d 718 -plans_name nnUNetResEncUNetPlans_60G_iso05 -c 3d_fullres_045 -np 8
  nnUNetv2_train 718 3d_fullres_045 0 -tr nnUNetTrainerICX4 -p nnUNetResEncUNetPlans_60G_iso05   # + ICX4_SKIP_FINAL_VAL=1, chained
  ```
- **t\* and Rule T carry unchanged.** nnU-Net exports probabilities resampled to each CT's own grid
  (`export_prediction.py`: `resampling_fn_probabilities`, then `revert_cropping_on_probabilities`), so
  `threshold_export.py`, `rule_t.py` (radii in mm from the NIfTI header) and the scorer never see the training grid.
  S's t_C is Rule T run on S, as L-A18 says. No "t = 0.50" export is needed.
- **Cost:** an iteration's cost depends on the patch and batch, not the spacing, so 1000 epochs stay ≈ 50 h. The
  volumes hold (0.5/0.45)³ = 1.37× the voxels, so preprocessing and sliding-window inference grow by about that.
  **≈ 55 GPU-h** in three chained jobs, inside L-A25's 55–60.

## 4. Item 4: calibration

### 4.1 What a temperature can change (`calib_equiv.py`)

Rule W exports vessel where the summed vessel probability p_v ≥ t.
- **A binary temperature** (p_v′ = σ(logit(p_v)/T)) is strictly monotone in p_v. So {p_v′ ≥ t} = {p_v ≥ t′} with
  t′ = σ(T·logit(t)): **exactly the same masks**, at re-labelled thresholds. Checked numerically: identical on every
  voxel for T ∈ {0.7, 0.85, 1.2, 1.5}.
- **A 5-class temperature** (softmax(log p / T) over nnU-Net's saved probabilities) is not exactly monotone in p_v
  where the vessel mass is split between two vessels. On rim-like voxels with a 20 % branch-point split, the
  calibrated mask at t differs from the best raw threshold's mask on **at most 0.4–1.1 % of rim voxels**
  (T = 0.85 … 1.5).

**So "re-run Rule W on calibrated probabilities" is Rule W on a different grid,** up to about 1 % of the rim. It cannot
remove FP that sits above the rim in p_v, and it cannot find a width no raw threshold gives.

### 4.2 The pre-registered remedy, by Job 0 result

| Job 0 shows | Then (before #306 freezes `TSTAR`) |
|---|---|
| t\* = 0.30, Dice still rising at 0.30 (the grid's edge binds) | Extend Rule W's grid on the tuning 60 to {0.25, 0.20}: `threshold_export.py` on Job 0's saved probabilities, the scorer, `decide.py select` over all seven (CPU, ≈ 1 h). **Extend `rule_t.py`'s `GRID` to hold the new t\*** (it stops at 0.25, so t\* = 0.20 could never be matched). No temperature |
| FP rising at every t < 0.50 | t\* = 0.50 by the guard as written. A monotone calibration cannot help (§4.1). Nothing else |
| t\* held by the FP guard at 0.45–0.35 | t_C = t\* (L-A15 scope). The FP excess is named on #302. No calibration |
| Otherwise | No calibration step |

The temperature fit L-A23 names is therefore dropped: it would add a rule and a parameter, and change at most about
1 % of rim voxels against a grid extension that the existing scripts already run.

## 5. Item 5: class-weighted CE in Janus 0's run

### 5.1 The rule

**If Step T finds class-weighted CE in any of Janus 0's training logs, the fine-tune uses the same weights file.**
- a1, a2 then differ from Janus 0's recipe only in what L-A2 already lists (data, schedule, warm start). Dropping the
  weights would be a second recipe change at the same look, confounded with the 60 extra cases.
- `nnUNetTrainer_janus1l` gains the hook from `trillium/icx4/lib/icx4_trainers.py` l. 29–39 (read the file, log
  `class-weighted CE` with the weights). The trainer-diff self-test (L-A21 #6) then asserts CE weight = Janus 0's,
  not None.
- S, if it runs, uses `nnUNetTrainerICX4` itself, so it picks the file up the same way.

### 5.2 Step T must copy the file if it exists

The Step T block checks for `$SCRATCH/icx4/ce_class_weights.json` but does not copy it. **If it exists, it must be
copied before the purge,** or the rule above cannot be applied. One line, added after the `ls` (Part B §5):

```sh
[ -f $SCRATCH/icx4/ce_class_weights.json ] && cp $SCRATCH/icx4/ce_class_weights.json $L/ && sha256sum $L/ce_class_weights.json
```

## 6. Item 6: #306's commands, final

### 6.1 Every script's interface, read and run

| Script | Called by | Inputs | Outputs | Self-test here |
|---|---|---|---|---|
| `experiments/Crucible/j1l_r1/threshold_export.py` | predict, transfer, collect | `--probs` dir of `<case>.npz` (key `probabilities`, SimpleITK order) + `<case>.nii.gz`; `--t …`; `--np` | `<out>/t<t.2f>/<case>.nii.gz`, `voxels.json`. Refuses sealed ids | pass |
| `experiments/Crucible/j1l_r1/decide.py select` | Job 0 | `--scores t0.50=… t0.45=…` (scorer JSONs) | `select.json`: `chosen_t` (string), `per_threshold` keyed `'0.50'`… | pass |
| `experiments/Delta/j1l_r2/rule_t.py` | transfer | `--j0` (Janus 0's D60 export, needs `t<t*>`), `--cand` (C's D60 export, **needs every t of its grid 0.60…0.25**), `--select`, `--out`, `--np`. Reads all 60 D60 ids; refuses others and sealed | `rule_t.json`; prints its sha256 (= the file's) | pass |
| `experiments/Atlas/r9_score_icx4.py` | Job 0, collect | `--pred`, `--icx`, `--aorta`, `--layout`, `--splits` + `--set val`, `--pair` (L0), `--out` | rows per case (`per_class`, `flagged_classes`, `provisional`, `recall`, `fp_components`, `dice.tree`), `summary`, `paired`, `rows_pair` | pass |
| `experiments/Delta/j1l_r2/mde_from_job0.py` | after Job 0 | Job 0's `locked100_janus0_argmax.json` (positional) | JSON on stdout (`mde['tf1, warm siblings']['E']`…) | — (no self-test; read) |
| `experiments/Bridge/j1l_r2/error_decomp.py` | after Job 0 | `--pred`, `--icx`, `--aorta`, `--layout`, `--np`, `--out`; tuning 60 only | `summary` on stdout, rows in `--out` | pass |
| **`experiments/Crucible/j1l_r3/gate.py`** (new) | collect | the scorer JSONs of Janus 0 (baseline) and C; `--select`/`--rule_t` with their posted sha256; `--identity`; `--mde`; `--report` a1/a2 at argmax and t_C, Janus 0 at t_C; `--ledger` | `gate_<look>.json`: branch, verdict, every bound, L3 per class with excess kurtosis, G5 lists, the wording of record, S's trigger, val-80/locked-20 parts, E − a1, σ_g | pass, mutation-tested |

### 6.2 Three seam defects found (each would have stopped or mis-scored a job)

1. **`rule_t.py` needs C exported on its whole grid (0.60 … 0.25), not Rule W's.** Job 0 exports Janus 0 at 0.50 …
   0.30 only. If `predict`/`transfer` copy that `--t` list for C, `rule_t.py` stops at the first missing `t0.60`
   (`pipeline_check.py` S2). The command below passes `--t 0.6 0.55 0.5 0.45 0.4 0.35 0.3 0.25`.
2. **`nnUNetv2_ensemble` writes no `.npz` without `--save_npz`** (`ensemble.py`, `merge_files`), and
   `threshold_export.py` exits with "no .npz". With the flag, the mean is saved under the same key, `probabilities`,
   and `threshold_export.py`'s argmax/orientation guard holds on it (S1). It loads both members' full-resolution
   probabilities per case (~1.6 GB each in float32 at 512 × 512 × 300), so `-np 4` in the job, never on the login node.
3. **`nnUNetv2_move_plans_between_datasets` writes into the target's preprocessed folder without creating it**
   (`save_json(…, join(nnUNet_preprocessed, target, …))`; batchgenerators' `save_json` is a bare `open(…, 'w')`).
   `prepare` must `mkdir -p $nnUNet_preprocessed/Dataset718_Janus1L` before the move, or P dies on its first command.

And one ordering rule: **`collect` checks the two posted sha256 and the looks ledger before it scores C**, not only
inside the gate. Otherwise the scorer computes C's locked-100 numbers before the refusal (L-A21). The block below does
this with `sha256sum -c` first.

### 6.3 The lead's command block

Variables: `R=$SCRATCH/asclepius/repo`, `J0=$SCRATCH/janus0`, `W0=$SCRATCH/j1l_job0` (Job 0), `W=$SCRATCH/j1l`
(Janus 1-L). `TSTAR` is `select.json`'s `chosen_t`. `SEL` and `RTS` are the sha256 values posted on #302. The
`./janus1l` launcher is #306's (L-A21); each mode's body is spelled out under it, so #306 is a thin wrapper and the
lead can run any step by hand.

```sh
# ---- once, on the Trillium login node -----------------------------------------------------------------------------
source $HOME/icx14-venv/bin/activate
git -C $R pull --ff-only && pip install --no-deps -e $R          # editable: load_sealed finds trillium/sealed_test.json
cd $R/trillium/janus1l

# ---- check: self-tests 1-9 (L-A21) and the dry run; submits nothing ------------------------------------------------
./janus1l check
python $R/experiments/Crucible/j1l_r3/gate.py --selftest
python $R/experiments/Crucible/j1l_r3/pipeline_check.py         # S1-S5 PASS
#  prints: split pins, train 620 / val 10 (tuning) / locked-in-train 0 / sealed 0, Janus 0 sha = SHA256SUMS,
#  plans diff = {dataset_name, image_reader_writer}, select.json sha = SEL, trainer diff OK, both sealed-list paths

# ---- prepare (P, about 1 h, CPU-bound; ./janus1l prepare submits it) ------------------------------------------------
#  body:
#   build $nnUNet_raw/Dataset718_Janus1L (620 + locked 100, ids cNNNN, labels by territory.to_four)
mkdir -p $nnUNet_preprocessed/Dataset715_ICX4 $nnUNet_preprocessed/Dataset718_Janus1L
cp $J0/nnunet_results/Dataset715_ICX4/nnUNetTrainerICX4__nnUNetResEncUNetPlans_60G_iso05__3d_fullres/plans.json \
   $nnUNet_preprocessed/Dataset715_ICX4/nnUNetResEncUNetPlans_60G_iso05.json
nnUNetv2_move_plans_between_datasets -s 715 -t 718 -sp nnUNetResEncUNetPlans_60G_iso05 -tp nnUNetResEncUNetPlans_60G_iso05
nnUNetv2_preprocess -d 718 -plans_name nnUNetResEncUNetPlans_60G_iso05 -c 3d_fullres -np 8
cp $J0/nnunet_results/Dataset715_ICX4/nnUNetTrainerICX4__nnUNetResEncUNetPlans_60G_iso05__3d_fullres/dataset_fingerprint.json \
   $nnUNet_preprocessed/Dataset718_Janus1L/
#   write splits_final.json: two identical entries, train = the 620, val = the 10 lowest-id tuning cases
#   plans check: the moved plans equal Janus 0's once dataset_name and image_reader_writer are removed

# ---- train: a1 and a2, two jobs at once, each chain-resumable (at most two 23:50 jobs) -----------------------------
./janus1l train a1 ; ./janus1l train a2 ; ./janus1l status
#  body of one block (fold 0 = a1, fold 1 = a2):
#   export SEGTRAIN_FINETUNE_FROM=$J0/nnunet_results/Dataset715_ICX4/nnUNetTrainerICX4__nnUNetResEncUNetPlans_60G_iso05__3d_fullres/fold_0/checkpoint_final.pth
#   export SEGTRAIN_CT_WINDOW=off SEGTRAIN_SAVE_EVERY=10 SEGTRAIN_SAVE_PROBABILITIES=0 SEGTRAIN_MAX_SECONDS=84000
#   export SEGTRAIN_SEALED_LIST=$R/trillium/sealed_test.json nnUNet_compile=<Janus 0's, from Step T>
#   unset SEGTRAIN_ITERATIONS SEGTRAIN_EPOCHS
#   nnUNetv2_train 718 3d_fullres <fold> -tr nnUNetTrainer_janus1l -p nnUNetResEncUNetPlans_60G_iso05 [--c if checkpoint_latest exists]
#   (+ ce_class_weights.json in the hook's place only if Step T found it, Part A §5)

# ---- predict (about 3 GPU-h; after both 'completed' markers, or a1's alone under L-A14's fallback) ------------------
./janus1l predict
#  body:
P="-c 3d_fullres -p nnUNetResEncUNetPlans_60G_iso05 -chk checkpoint_final.pth --disable_tta --save_probabilities -device cuda"
for f in 0 1; do for s in locked100 d60; do
  nnUNetv2_predict -i $W/in/$s -o $W/p/f$f/$s -d 718 -f $f -tr nnUNetTrainer_janus1l $P; done; done
nnUNet_results=$J0/nnunet_results nnUNetv2_predict -i $W/in/d60 -o $W/p/j0/d60 -d 715 -f 0 -tr nnUNetTrainerICX4 $P
for s in locked100 d60; do nnUNetv2_ensemble -i $W/p/f0/$s $W/p/f1/$s -o $W/p/E/$s --save_npz -np 4; done
#  predict scores nothing

# ---- transfer (CPU job; Rule T) -----------------------------------------------------------------------------------
./janus1l transfer
#  body:
TE=$R/experiments/Crucible/j1l_r1/threshold_export.py; RT=$R/experiments/Delta/j1l_r2/rule_t.py
G="0.6 0.55 0.5 0.45 0.4 0.35 0.3 0.25"      # must equal rule_t.py's GRID; under R3-A8 add 0.575 0.525 ... 0.275
for m in E f0 f1; do python $TE --probs $W/p/$m/d60 --out $W/thr/$m/d60 --t $G --np 4; done
python $TE --probs $W/p/j0/d60 --out $W/thr/j0/d60 --t $TSTAR 0.5 --np 4
python $RT --j0 $W/thr/j0/d60 --cand $W/thr/E/d60 --select $W0/select.json --out $W/rule_t.json --np 4
for m in f0 f1; do python $RT --j0 $W/thr/j0/d60 --cand $W/thr/$m/d60 --select $W0/select.json --out $W/rule_t_$m.json --np 4; done
sha256sum $W/rule_t.json        # POST on #302 with rule_t.json; the f0/f1 files are reports
#  (under L-A14's fallback, --cand $W/thr/f0/d60 writes rule_t.json)

# ---- collect (CPU; the one look) ----------------------------------------------------------------------------------
JANUS1L_SELECT_SHA=$SEL JANUS1L_RULE_T_SHA=$RTS ./janus1l collect
#  body, in this order:
echo "$SEL  $W0/select.json" | sha256sum -c && echo "$RTS  $W/rule_t.json" | sha256sum -c || exit 1
[ -e $W/looks/C.done ] && { echo "look already taken"; exit 1; }; mkdir -p $W/looks $W/scores $W/results
TC=$(python -c "import json;print('%.2f' % json.load(open('$W/rule_t.json'))['t_C'])")
for m in E f0 f1; do python $TE --probs $W/p/$m/locked100 --out $W/thr/$m/locked100 --t $TC 0.5 --np 4; done
python $TE --probs $W0/probs --out $W/thr/j0all --t $TC --np 4
SC="python $R/experiments/Atlas/r9_score_icx4.py --icx $J0/icx --aorta $J0/aorta --layout $W0/layout.json --splits $W0/split_locked100.json --set val --np 8"
$SC --pred $W/thr/E/locked100/t$TC  --out $W/scores/C.json
$SC --pred $W/thr/f0/locked100/t$TC --out $W/scores/a1_tC.json
$SC --pred $W/thr/f1/locked100/t$TC --out $W/scores/a2_tC.json
$SC --pred $W/thr/f0/locked100/t0.50 --out $W/scores/a1_argmax.json
$SC --pred $W/thr/f1/locked100/t0.50 --out $W/scores/a2_argmax.json
$SC --pred $W/thr/j0all/t$TC        --out $W/scores/j0_tC.json
python $R/experiments/Delta/j1l_r2/mde_from_job0.py $W0/scores/locked100_janus0_argmax.json > $W/mde.json
python $R/experiments/Crucible/j1l_r3/gate.py --look C \
  --base $W0/scores/locked100_janus0_argmax.json --cand $W/scores/C.json \
  --select $W0/select.json --select_sha $SEL --rule_t $W/rule_t.json --rule_t_sha $RTS \
  --identity $W0/scores/identity_val80.json --mde $W/mde.json \
  --report a1_argmax=$W/scores/a1_argmax.json a2_argmax=$W/scores/a2_argmax.json \
           a1_tC=$W/scores/a1_tC.json a2_tC=$W/scores/a2_tC.json j0_tC=$W/scores/j0_tC.json \
  --ledger $W/looks/C.done --out $W/results/gate_C.json
#  POST on #302: the printed block (branch, verdict, bounds, S_trigger, wording). No per-case row.
```

**Under L-A14's fallback** (a2 did not finish): `--cand $W/scores/a1_tC.json`, drop the a2 reports, and `rule_t.json`
comes from f0. **S's look** (L-A18, only on the trigger): the same `collect` body with S's scores, `--look S` and
`--ledger $W/looks/S.done`.

### 6.4 `gate.py`, against L-A16 and L-A17

- **H1:** bootstrap lower bound of Δ decisive macro tF1 > −0.02; no class mean Δ < −0.03; L3 on `recall` (L-A17:
  10 %-trimmed mean < −0.02, or mean < −0.02 with its 95 % t upper bound < 0, exactly Delta's measured rule); C's FP
  components per case ≤ 1.
- **H2, H3** in sequence. **Q4:** lower bound > −0.015 **and** Dice upper bound ≥ 0 (D49 Q-R2-3).
- **Pairing:** a case decides tF1 only if non-provisional in both rows; a class counts only if unflagged in both. The
  flags come from the reference, so the two rows should agree; the mismatch count is printed (R3-A2).
- **Refusals:** a locked-100 case missing or errored in any input; any case outside the locked 100; a sealed id; a
  wrong sha256; a second look; L0 failed.
- **Wording:** every row of L-A16, with the brackets filled, plus "a two-network ensemble … at t_C", whether Rule T
  moved t_C, the MDE sentence and "under-powered" above 0.025, L3's stated false-alarm rate, and the share sentence.
- **S's trigger** (L-A18) from a1 and a2 at argmax; σ_g with A37's flag; E − a1; val 80 and locked 20 apart.

**Self-tests (14), all passing**, among them L-A21 #9's three fixtures:
- a uniform −0.03 LCx recall loss fires L3; a heavy-tailed null fires on 4.0 % of draws (any of four classes);
- three trees of 100 flipping from rooted to cut (mean −0.024) does **not** fire L3, though it fires G3 as written;
- a lower bound of −0.017 with H2 failing gives "not adopted", and −0.012 gives "adopted (Q4)";
- the same −0.012 with Dice shown worse gives "not adopted (Q-R2-3)";
- FP of 1.2 per case fails H1.

**Mutation test** (`pipeline_check.py` S5): six broken gates (Q-R2-3 removed; Q4 at −0.02; FP out of H1; L3 replaced
by G3 as written; the class guard dropped; S's α equal to C's). **The self-test kills all six.**

### 6.5 The trainer subclass #306 adds

```python
# src/segtrain/nnunet_ext/nnUNetTrainer_janus1l.py
from segtrain.nnunet_ext.nnUNetTrainer_segtrain_finetune import nnUNetTrainer_segtrain_finetune

class nnUNetTrainer_janus1l(nnUNetTrainer_segtrain_finetune):
    """Janus 1-L (L-A21): A17a's fine-tune with nnU-Net's final validation skipped, so no locked-100 or tuning
    prediction is written when a run ends; the locked 100 come only from `predict`."""
    def perform_actual_validation(self, save_probabilities: bool = False):
        self.print_to_log_file("[janus1l] final validation skipped (L-A21)")
```

Installed by a two-line shim in nnU-Net's `variants/` folder, as `trillium/atlas3/atlas3` does for its trainers.

### 6.6 The decomposition reading (L-A22), on the posted numbers

No summary is posted, so no group can be named yet. The reading, applied mechanically once the two summaries are on
#302, per class with LCx first:
1. take each group's macro ceiling at t = 0.50;
2. ≥ 0.030: an arm of that kind may be costed in a later round; 0.015–0.030: only after a no-training test on the 60
   recovers half; < 0.015: no arm;
3. if more than half of the `distal` points lie below A23's contrast line, no extent arm, whatever its ceiling;
4. extent → Skeleton Recall; breaks → a connectivity lever with its own evidence; naming → the namer or class-weighted
   CE; width → the threshold (already in the plan);
5. the t\* summary is read only to check that the threshold did not trade naming for width (naming ceiling up by more
   than 0.005).

None of this changes Janus 1-L.1.

## 7. Round-3 amendments proposed (R3-A1 to R3-A8)

- **R3-A1. The gate of record** is `experiments/Crucible/j1l_r3/gate.py`; `collect` calls it after `sha256sum -c` of
  `select.json` and `rule_t.json` and after the ledger check.
- **R3-A2. Pairing:** a class flagged in either row is out of both; a case provisional in either row decides no tF1.
  The mismatch count is printed.
- **R3-A3. α at S's look:** 1.25 % on the bounds that grant a claim; the guards (L3's upper bound, Q-R2-3's Dice
  upper bound) keep C's level.
- **R3-A4. Seams:** Rule T's grid for C's D60 export; `--save_npz`; `mkdir -p` of dataset 718's preprocessed folder.
- **R3-A5. Calibration** is the grid (§4): no temperature step; Rule W's and Rule T's grids extend together if t\* is
  at the edge.
- **R3-A6. Step T copies `ce_class_weights.json` if it exists;** if Janus 0 used it, the fine-tune does too (§5).
- **R3-A7. S's form:** 0.5 mm unless Job 0 sets the grid trigger **and** the view check passes (§3).
- **R3-A8. Rule T on a 0.025 grid** (0.600, 0.575, … 0.250): `rule_t.py`'s `GRID` and the D60 export's `--t` list
  gain the half steps. CPU and disk only (about twice the D60 export files). Reason: under Q-R2-3 a Dice loss of
  0.005 is refused most of the time (§2), so the residual of a 0.05 step is no longer negligible. Rule W's grid on the
  tuning 60 stays 0.05 (it is frozen with `select.json`). If the judge prefers no code change to a frozen script, the
  0.05 grid stands and this risk is stated in the verdict.

## 8. Cost

Unchanged from L-A25: **≈ 33–35 GPU-h** (Job 0 included), ceiling ≈ 60. S, only on its trigger: +≈ 53 (0.5 mm) or
≈ 55 (0.45 mm, §3.3). This round's CPU work: about 1 h.

## 9. Questions for the lead

None. D49 answered round 2's. R3-A3 is a reading of L-A18 for the judge, not a D-number question.

**Action, not a decision:** Step T is still urgent (purge about 2026-12-20), now with §5.2's one extra line.

---

# Part B: the consolidated plan (L-A1 to L-A25, D49 and R3-A1 to R3-A7 written through)

This is the text the master plan would read if the judge adopts Part A. Every clause of L-A1 to L-A25 that is still in
force is written in place; superseded clauses (L-A2's "fold val = the locked 100", L-A3's "a1 is the candidate",
L-A4's "applied unchanged", L-A5's `recall_icx_traced`, the "subject to Q-R2-n" clauses) are gone. The source of each
clause is in brackets.

## B0. Binding decisions

D45 (the split, Trillium, the lead runs every job); D46 (Q1–Q8); **D49** (Q-R2-1 to Q-R2-4: E may ship with a2 as a
member; D60 label-free; Q4 needs Dice not shown worse; S runs on its trigger); D25 and D8 (four classes by territory,
ImageCAS-X's lumen); D27/D32 (the seals); D35 (pool questions only); D34 (naming); D40 (overlaps become ignore, pool
reads); D31 (no message to anyone outside the project). The main [[Master plan]] still governs pool work and the seal.
Track 1-F shares only the split.

## B1. In one paragraph

**Janus 1-L is Janus 0 fine-tuned warm on D45's 620 ImageCAS-X cases, twice (a1, a2), shipped as their ensemble E at
an export threshold t_C** [L-A3, L-A14, D49]. Rule W picks t\* on Janus 0's own probabilities for the tuning 60
[L-A4]; Rule T carries the width t\* gives, not the number, to E, by local radius on the shared centreline of 60
unlabelled quality-0 CTs [L-A15, D49]. The locked 100 judge E at t_C against Janus 0 at argmax once: H1 (tF1
non-inferior at −0.02 with class, recall and FP guards), then H2 (Dice superior), then H3 (tF1 superior) [L-A5]. A
non-inferior, not-better E is adopted if H1's lower bound is above −0.015 and its Dice is not shown worse [D46 Q4,
D49]. One fallback, a from-scratch run S, is fixed now with its own look at 1.25 % [L-A18]. **Cost ≈ 33–35 GPU-h,
Job 0 included; S only on its trigger, +≈ 53** [L-A25].

## B2. Data [L-A1, L-A15, D45, D49]

| Set | Cases | Use |
|---|---|---|
| Train 620 | ImageCAS-X train 560 + dev 44 + c0123 c0195 c0340 c0416 c0430 c0435 c0447 c0617 c0624 c0660 c0726 c0758 c0772 c0877 c0971 c0984 | Training, folds 0 and 1 identical |
| ↳ tuning 60 | dev 44 + those 16; never trained on by Janus 0 | Rule W (Job 0). The 10 lowest ids are nnU-Net's fold val, in-sample display only |
| Locked 100 | val 80 + c0068 c0102 c0251 c0271 c0323 c0327 c0470 c0545 c0592 c0620 c0644 c0805 c0807 c0824 c0827 c0841 c0908 c0946 c0957 c0996 | The decision. Never trained on, never used to choose anything, never nnU-Net's val |
| D60 | `experiments/Delta/j1l_r2/drift60.json`, pin `916e8a18…004e` | Rule T only: Janus 0's and the candidates' predictions compared. No label or mask read; nothing trained on them |
| Sealed | ImageCAS-X test 80 + quality-0 20 | Never read, predicted, scored or trained on |

Pins: locked 100 `bbd9c687818956e2d5664b06fd8c8bd02ddb031e9b9d08036d59cc0e1a4d5895`; train 620
`1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152`; file of record
`experiments/Delta/j1l_r1/janus1_split_proposal.json` (`19b832fe…4dd3`) → `configs/janus1/split-2026-11.json` under
#306. Labels: ImageCAS-X as drawn, collapsed by `trillium/icx4/lib/territory.py`, as dataset 715. F0's pins on Fir must
match these [§1.3].

## B3. Recipe [L-A2, L-A3, L-A14, L-A20, L-A21, R3-A4, R3-A6]

| Item | Setting |
|---|---|
| Start | Janus 0 `checkpoint_final.pth` (Dataset715), full strict load with heads, bitwise-checked, sha256 logged |
| Trainer | `nnUNetTrainer_janus1l`, a thin subclass of `nnUNetTrainer_segtrain_finetune` whose `perform_actual_validation` returns at once |
| Plans | Janus 0's `plans.json` placed as `$nnUNet_preprocessed/Dataset715_ICX4/nnUNetResEncUNetPlans_60G_iso05.json`; `mkdir -p` of dataset 718's preprocessed folder; `nnUNetv2_move_plans_between_datasets`; `nnUNetv2_preprocess` only. Janus 0's `dataset_fingerprint.json` placed in the new folder. **Check:** equal to Janus 0's once `dataset_name` and `image_reader_writer` are removed. No fingerprint step, no plan step |
| Schedule | 2500-iteration linear warm-up to 1e-2, then poly; SGD, Nesterov 0.99; 250 epochs × 250 iterations |
| Loss | DiceCE with deep supervision. **No class weights, unless Janus 0's logs show them, in which case the same `ce_class_weights.json`** (copied in Step T) |
| Augmentation, sampling | nnU-Net default, mirroring off in training and inference; uniform over the 620 |
| Validation | Fold val = the 10 lowest-id tuning cases. Final validation skipped. `checkpoint_best` never read |
| Environment | `SEGTRAIN_FINETUNE_FROM`, `SEGTRAIN_CT_WINDOW=off`, `SEGTRAIN_SAVE_EVERY=10`, `SEGTRAIN_SAVE_PROBABILITIES=0`, `SEGTRAIN_MAX_SECONDS` = walltime − 30 min, `SEGTRAIN_SEALED_LIST`, `nnUNet_compile` as Janus 0's; `SEGTRAIN_ITERATIONS` and `SEGTRAIN_EPOCHS` unset; segtrain installed editable |
| Runs | a1 = fold 0, a2 = fold 1 of the same split entry, two concurrent jobs, each chain-resumable within two 23:50 jobs |
| Candidate | **C = E at t_C**, E = `nnUNetv2_ensemble --save_npz` of the two folds' probabilities. If a2 has not completed within two chained jobs, C = a1 at t_C (Rule T run on a1). If a1 has not completed, nothing is scored |
| Inference | `checkpoint_final`, `--disable_tta`, `--save_probabilities`, on the locked 100 and D60 |
| Not in this plan | Skeleton Recall or another topology loss, the 1e-3 arm, a new spacing (except as S's form), from-scratch training (except S) |

### B3.1 Rule W [L-A4, R3-A5]

On Janus 0's tuning-60 probabilities (Job 0), grid t ∈ {0.50, 0.45, 0.40, 0.35, 0.30}: vessel where the summed vessel
probability ≥ t, class = argmax among the four vessels. Choose the highest mean whole-tree Dice subject to tF1 ≥
tF1(0.50) − 0.005, FP ≤ FP(0.50) + 0.10 per case, and no class's recall falling; ties within 0.002 to the larger t.
Code: `experiments/Crucible/j1l_r1/decide.py select`. **If t\* = 0.30 with Dice still rising, the grid extends to
0.25 and 0.20 on the same data before #306 freezes t\*, and Rule T's grid extends with it.** No temperature step.
`select.json` and its sha256 are posted before any training job.

### B3.2 Rule T [L-A15, D49, R3-A8]

Reference: Janus 0 at t\* on D60, its skeleton and its local radius. dr(t) = the 10 %-trimmed mean of C(t)'s radius
minus Janus 0's on the reference centreline points C(t) covers, pooled over D60. t_C = the t ≤ 0.50 on the grid with
the smallest |dr|; ties within 0.005 mm to t\*, then the larger t. **Grid: 0.600 … 0.250 in steps of 0.025** (R3-A8; or
0.05 if the judge declines it). If t\* was held back by a guard (Dice at t\* more than 0.002 under the best), t_C = t\*.
Run on C's own probabilities; a1's and a2's dr are reports (opposite signs = seed noise). Code:
`experiments/Delta/j1l_r2/rule_t.py`. `rule_t.json`'s sha256 is posted before `collect` computes any locked-100 number.

## B4. The decision [L-A5 to L-A8, L-A14 to L-A18, D46 Q3/Q4, D49, R3-A1 to R3-A3]

**L0 first:** Janus 0 re-predicted on Trillium reproduces Fir's val-80 decisive macro 0.909 ± 0.003, each class within
0.01 of LM 0.945, LAD 0.903, LCx 0.857, RCA 0.938, and ≥ 95 % of cases within 0.01 of Fir's own predictions.
Otherwise stop.

**The comparison:** C against Janus 0 at argmax (Job 0), decisive tF1 @ 1.5 mm at A1c `24441cf8…5254` with Janus 0's
A1 aortas, A1a/A1b applied to both rows of a pair, paired by case, bootstrap 10 000, one-sided 2.5 % bounds. **One look
per candidate; at most two in the track.** Gate of record: `experiments/Crucible/j1l_r3/gate.py`, run by `collect`
after the posted sha256 and the looks ledger are checked.

| # | Test | Passes when |
|---|---|---|
| H1 | tF1 non-inferior, nothing lost | Lower bound Δ macro tF1 > −0.02; no class mean Δ < −0.03; L3 holds; C's FP components ≤ 1 per case |
| H2 | Width | Lower bound Δ whole-tree Dice > 0 |
| H3 | tF1 superior | Lower bound Δ macro tF1 > 0 |

**L3** on the scorer's per-class `recall`: for no class is the 10 %-trimmed mean Δ < −0.02, or the mean < −0.02 with its
95 % upper bound < 0. Stated false-alarm rate 3–8 %, up to about 19 % under a broad shift; each class's excess kurtosis
is printed.

| Outcome | Verdict |
|---|---|
| H1 fails | Not adopted. Janus 0 stays. G5 lists five cases for any class with point Δ < −0.05. S if its trigger fires |
| H1 passes, lower bound in (−0.02, −0.015], H2 fails | Not adopted |
| H1 passes, lower bound > −0.015, H2 fails, Dice upper bound ≥ 0 | **Adopted** (D46 Q4, D49) |
| H1 passes, lower bound > −0.015, H2 fails, Dice upper bound < 0 | Not adopted: lumen width shown worse (D49) |
| H1 + H2 | **Adopted**, with the share sentence |
| H1 + H2 + H3 | **Adopted**, "and better in tF1" |

Wording of record: L-A16's table, with the D49 row above, every claim with its two-sided 95 % CI beside the margin, and
every adopted wording stating the ensemble and t_C, whether Rule T moved it, the MDE (and "under-powered" above
0.025), L3's false-alarm rate, and the val-80 and locked-20 parts. "Not shown better" is never "no better". **What ships
is C exactly as tested.**

**Reports, deciding nothing:** Janus 0 at t_C; a1, a2 at t_C and at argmax; E − a1; σ_g = |a1 − a2|/√2 with A37's rule
above 0.02; C's Dice and volume ratio at every t; per-class tF1, Dice, tolerant Dice, volume ratio, recall, precision,
FP; the 89 never-inspected cases.

### B4.1 S [L-A18, D49 Q-R2-4, R3-A3, R3-A7]

- **Trigger:** H1 fails, a1 and a2 at argmax both have point Δ macro tF1 < 0, and L0 passed. Never one class, L3 or FP
  alone with a member ≥ 0.
- **Run:** Janus 0's recipe (`nnUNetTrainerICX4`, its plans, final validation skipped) from scratch on the 620, 1000
  epochs, one run, ≈ 53 GPU-h. **0.45 mm only if Job 0 set the grid trigger and the view check passes;** then the
  derived `3d_fullres_045` configuration, ≈ 55 GPU-h.
- **Threshold:** t\* with Rule T run on S.
- **Look:** Janus 1-L.2 against Janus 0, the same sequence and wording; the bounds that grant a claim at one-sided
  1.25 %, the guards at C's level. The lead runs it without another round (D49). If it fails, Janus 0 stays.

## B5. Pool fine-tunes after adoption [L-A11, L-A19]

Pool a1′ from a1 and pool a2′ from a2; the pool candidate is E′; G1's replicate clause is "each member's Δ > 0"; G2
and L3 compare E′ with the adopted E on the locked 100; the b arm starts from a1. If a1 alone is adopted, L-A11 as
written.

## B6. Naming [L-A24, D46 Q7]

Janus 1-L.1 = C; Janus 1-L.2 = S, if read; the adopted model is Janus 1-L; everything else is a report under 1-L.1.

## B7. Jobs and cost [L-A25]

| Job | Waits on | GPU-h |
|---|---|---|
| Step T (Fir → Trillium; with the fingerprint, the logs, the compile line and `ce_class_weights.json` if present) | now, before about 2026-12-20 | 0 |
| Job 0 | Step T | 3–4 |
| Decomposition, MDE (login node) | Job 0, L0 passed | 0 |
| P | #306, the converged round | ≈ 1 |
| a1, a2 | P | ≈ 25–27 |
| predict | a1, a2 | ≈ 3 |
| transfer, collect | predict | 0 |
| **Total** | | **≈ 33–35** (ceiling ≈ 60) |
| S | its trigger | +≈ 53 (0.45 mm ≈ 55) |

Commands: Step T, Job 0 and the post-Job-0 CPU steps as in [[Master plan - Janus 1-L]] §5, with §5.2's extra line;
the training-phase block as Part A §6.3. Open: only the values Job 0 posts (t\*, the L-A23 row, the MDE) and the
round that reads them.
