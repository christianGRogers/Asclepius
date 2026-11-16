---
tags: [plans, candidate, janus1-L, D45, D46, trillium, four-class, warm-start, ensemble, locked100, round2]
author: Foxtrot
track: 1-L
round: 2
version: 2
updated: 2026-11-15
issue: christianGRogers/Asclepius#302
---

# Janus 1-L, Foxtrot v2: read the two-run ensemble in a1's place, carry the width rather than the threshold, and pre-register one fallback look

## 0. Position

**The plan in force is kept:** Crucible v1 as amended by L-A1 to L-A12 ([[Master plan - Janus 1-L]]), with D46's
answers. Nothing in §0 of [[Janus 1-L Round 1]] is reopened. v2 answers the eight items of its §5 and changes
four things:

| # | Change | Why (evidence) |
|---|---|---|
| 1 | **The candidate read on the locked 100 is E**, the mean softmax of a1 and a2, **in a1's place**, in the same H1 → H2 → H3 sequence and with one look. a1 and a2 become reports | On the only replicate pair of this family, E's paired SD against a baseline is **0.034 against 0.046** for one run. The MDE falls from 0.013 to 0.0095, and a neutral model passes D46's Q4 bar 0.95–0.99 of the time instead of 0.80–0.87, with no ensemble gain assumed (§1) |
| 2 | **What transfers from Janus 0 is the width Rule W chose, not the number t\*.** A label-free, pre-registered switch moves the export threshold when the candidate draws a different volume than Janus 0 at t\* | No labelled case is left outside the locked 100. Images no model trained on still show a calibration shift, without a label (§3) |
| 3 | **One fallback run and its look are pre-registered now**, with a trigger. Its form (0.5 mm or 0.45 mm) is set by Job 0 | Freezing it before any 1-L number exists keeps it from being tuned on a1's result (§6) |
| 4 | **#306 skips nnU-Net's automatic final validation.** It predicts the locked 100 only after the export threshold is frozen | nnU-Net's final validation would compute a1's and a2's whole-case Dice on the locked 100 at argmax before anything is frozen. That is H2's metric, outside the one look (§7) |

**Not changed:**
- the recipe (L-A2);
- the split and pins (L-A1);
- Rule W on the tuning 60 (L-A4);
- H1 to H3 with their margins and L3 (L-A5);
- the identity check (L-A8);
- the reports (L-A6);
- D46's answers.

**Step T and Job 0 have not run.** Every place that needs their numbers says what each outcome would change (§4).

**Independence.** I read the round-1 candidates, the judgement, the master plan and D46. I did not read Bridge v2,
Crucible v2, Delta v2, their branches, or any other round-2 note. A directory listing showed me the title of one
Crucible round-2 experiment note on the ensemble. I did not open it.

**New evidence this round** (CPU; `experiments/Foxtrot/j1l_r2/`; no image, label, locked-100 score or sealed case
read):
- [[Foxtrot - On real replicate runs the two-run ensemble cuts the paired spread against the baseline by a quarter, so reading it in a1's place sharpens the one look]]
  (`ship_choice_sim.py`);
- [[Foxtrot - A tuning-60 error decomposition and a label-free check that t-star transfers, both self-tested and waiting on Job 0]]
  (`error_decomp.py`, `t_transfer.py`, `calib_cases.py`, `job0b_calib_volumes.sh`; all self-tests pass).

## 1. Item 1: the ship candidate is E, read in a1's place

### 1.1 The evidence

From [[Foxtrot - On real replicate runs the two-run ensemble cuts the paired spread against the baseline by a quarter, so reading it in a1's place sharpens the one look|the ship-choice note]].
The data are Round 7's F0 and F1, two warm fine-tunes from one base, against Round 6's B, on the same val 80:

| | One run (a1) | Two-run mean (E) |
|---|---|---|
| SD of the per-case paired Δ against the baseline | 0.0455 | **0.0339** |
| MDE on the locked 100 (80 % power) | 0.0128 | **0.0095** |
| P(H1) for a neutral model, σ_g = 0.005 | 0.93 | **1.00** |
| P(Q4 adopt, lower bound > −0.015) for a neutral model, σ_g = 0.005 | 0.80 | **0.95** |
| P(Q4 adopt) for a model truly at −0.015 | 0.04 | **0.02** |
| SD of the shipped model's true effect, σ_g = 0.005 | 0.005 | **0.0035** |

**The ground has moved since v1.**
- **The run-level term σ_g looks small.** The replicates' means differ by 0.005, inside case noise. The one-df
  estimate is 0.0013. The "seed lottery on the mean" that v1 argued from is therefore weak.
- **What the data show instead is per-case instability.** The two replicates differ per case with SD 0.038, and on
  11 % of cases by more than 0.05 macro tF1.
- **A single run ships that noise into every patient's prelabel. E halves its variance,** and the same halving makes
  E's comparison with Janus 0 sharper.
- **No ensemble gain is assumed.** E's per-case score is modelled as the mean of its members'. Any real gain only
  adds to E's pass rates, and raises H3's chance at a +0.005 effect from 0.30 to 0.61 if δ_E = 0.003.

### 1.2 How E is tested without a second look

- **Candidate C = E at t_E**, where t_E is t\* or the switched value of §3, frozen before C's locked-100 numbers are
  computed.
- **E replaces a1 in H1 → H2 → H3,** with every margin, guard and α unchanged (L-A5). There is one look. a1 is not
  tested beside E, and no rule ever chooses between them after the look.
- **a1, a2 and E − a1 are reports** (L-A6), computed in the same `collect` run after the verdict, from the same
  predictions.
- **E is built from the two folds' saved probabilities** (`nnUNetv2_ensemble --save_npz`), so a1's and a2's own
  predictions and E's come from one inference pass per network (§7).

### 1.3 The E − a1 evidence a pre-registration needs: none from the locked 100

- **A pre-registered single candidate needs a reason chosen before the data, not a test.** E's reason is the measured
  per-case stability and the sharper decision (§1.1), plus the direction of the external evidence:
  - Mehrtash et al., IEEE TMI 39(12):3868–3878, 2020, Table II (M = 50, Dice);
  - nnU-Net's default five-fold ensemble (Isensee et al., Nat Methods 2021).
- **Testing E − a1 on the locked 100 would be the ladder,** which spends two looks. Delta's MDE of 0.005–0.010 for
  that test is reported, not used.
- **E − a1 is reported** with its CI and Delta's MDE beside it. If it is negative beyond its CI, the report says so.
  E stays the verdict's model, because swapping after the look is a second look. The finding goes to 1-F and to the
  next 1-L round.
- **What would have made E the wrong pre-registration:** a measured σ_g so large that E's members disagree on the
  mean (|a1 − a2| > 0.02 is A37's rule; reported). It cannot hurt E's own test, which already carries both members.

### 1.4 The base for pool fine-tunes

**Recommended (a proposal for the round that runs the pool stage, L-A11): member-wise.**
- A37/A38 already run two pool fine-tunes at 1e-2 (a1, a2) from the parent. Start pool **a1′ from E's member a1 and
  a2′ from a2**. The pool candidate is E′ = ensemble(a1′, a2′).
- G1's "a2 in the same sign" becomes "each child in the same sign".
- b (1e-3), if it runs, starts from a1.
- **Extra cost: none.** These are the two runs A37 budgets anyway.

**If one network must be the base** (the judge's framing in Q6), it is a1. But then every pool child is a single
network judged against an ensemble parent in G2, with the ensemble's per-case stability counted against it. I do not
recommend it.

### 1.5 D46's answers that bear on this

- **Q6:** an ensemble is acceptable in principle if pre-registered. This section does that.
- **Q7:** "unless round 2 makes E the candidate, in which case E takes 1-L.1". So D46 itself anticipates E as the
  candidate.
- **Q5:** a2 is "report only, never shipped". I read it as *never shipped alone or in a1's place*, since Q6 and Q7
  of the same decision admit an ensemble that contains a2. If the lead reads Q5 as excluding a2 from any shipped
  model, then **a1 is the candidate**, E stays a report, and everything else in v2 stands. This is QF1 (§12).

## 2. Item 2: the two middle branches, given D46 Q3 and Q4

**C** is E at t_E. Every claim cites its own interval (Piaggio et al., JAMA 2012, CONSORT non-inferiority).

| Outcome | Verdict | Wording of record |
|---|---|---|
| H1 fails | **Not adopted.** Janus 0 stays. G5's listing, then §6 | "Janus 1-L.1 was not adopted: [the clause that failed], Δ macro tF1 x [lb, ub]." |
| H1 passes with lb ∈ (−0.020, −0.015]; H2 fails | **Not adopted.** Janus 0 stays | "Non-inferior to Janus 0 at 0.02 but not at the 0.015 that D46 requires for adoption without a width gain; not shown better." |
| **H1 passes with lb > −0.015; H2 fails** (D46 Q4) | **Adopted as Janus 1-L**, exported at t_E as tested | "Janus 1-L is non-inferior to Janus 0 in tree-F1 at a margin of 0.015 (Δ x, 95 % CI [lb, ub]) on 100 locked ImageCAS-X cases. It is not shown better in lumen width (Δ whole-tree Dice y [lb, ub]) or in tree-F1. It is adopted because it is trained on 620 cases rather than 560, at no detected cost." |
| **H1 and H2 pass; H3 fails** (D46 Q3) | **Adopted as Janus 1-L** | "Janus 1-L is better than Janus 0 in lumen width: whole-tree Dice +y (95 % CI [lb > 0, ub]) on 100 locked ImageCAS-X cases. Its tree-F1 is non-inferior at a margin of 0.02 (Δ x [lb, ub]), with no class lost and centreline recall guarded (L3). A tree-F1 gain is not shown. Janus 0 at the same threshold reaches z % of the Dice gain." |
| H1, H2 and H3 pass | Adopted | As above, ending "…and better in tree-F1 (Δ x [lb > 0, ub])." |

**Three rules for these rows:**
- **Under H2, the tF1 margin is 0.02, not 0.015.** A width gain shown at one-sided 2.5 % carries the looser H1
  margin, as L-A5 has it. The wording says "0.02". The Q4 margin of 0.015 applies only when there is no width
  gain to justify adoption.
- **The adopted export is the one tested** (t_E), never argmax. Argmax is a different export that the look did not
  test. C at argmax is a report (L-A6).
- **z %** is L-A6's share: (Dice of Janus 0 at t_E − Dice of Janus 0 at argmax) / (Dice of C − Dice of Janus 0 at
  argmax). If z ≥ 80 %, the wording adds: "most of the width gain comes from the export threshold, not from the
  new training".

## 3. Item 3: the transfer of t\*

### 3.1 How a calibration shift would show

| Where | What | When | Decides |
|---|---|---|---|
| **60 label-free images** (open ImageCAS quality-0; `calib60.json`) | shift s = median V_C(t\*) / V_J0(t\*), and the volume-matched t_C (`t_transfer.py`) | after training, **before** the look | the switch (§3.2) |
| The tuning 60 | the candidate's volume at t\* against Janus 0's | after training | nothing: in-sample for a1 and a2, so biased towards labels |
| The locked 100 | C's Dice and volume ratio at every t (L-A6) | after the look | nothing: a report that feeds 1-F and later rounds |

- s < 1 means the candidate draws less than Janus 0 at t\*: it is sharper, or thinner. s > 1 means it draws more.
- Janus 0's own argmax-to-t\* volume ratio on the same images is printed beside s for scale.

### 3.2 The rule: frozen t\* unless the label-free switch fires

- **Default:** t_E = t\* (L-A4 unchanged).
- **The switch:** t_E = t_C if |t_C − t\*| ≥ 0.10 (two steps of Rule W's grid). t_C is the grid value whose
  median V_C(t) / V_J0(t\*) is closest to 1, so it reproduces the width that Rule W found Dice-best on 60 labelled
  cases.
- **Frozen before the look:** `transfer.json` (computed on E's own probabilities) is posted on #302 with its
  sha256. `collect` refuses to export at any other t.
- **It never uses a locked-100 number,** image or label, and never a label of the 60 images.
- **Why a switch and not always t_C:** Rule W's choice should stand unless the evidence of a shift is clear. Two
  grid steps is outside the plateaus a coarse grid produces (see the self-test in the tools note).
- **Caveat:** quality-0 images are poorer than ImageCAS-X's. s is a ratio of two networks on the same images,
  which cancels much of that. If the lead declines their use (QF2), the default (frozen t\*) applies and §3.1's
  locked-100 report remains.

**Cost:** Job 0b (Janus 0, ≈ 1 GPU-h) and 2 × 60 cases inside the predict job (≈ 1 GPU-h).

## 4. Item 4: Job 0 has not run. What each result would change

| Job 0 (and 0b) result | Then |
|---|---|
| L0 identity fails (val-80 macro ≠ 0.909 ± 0.003, or a class beyond 0.01, or < 95 % of cases within 0.01 of Fir) | **Stop** (L-A8). Nothing below is read. Round 3 plans around the cause |
| t\* ∈ {0.45, 0.40, 0.35}, Dice up 0.01–0.03 on the 60 (Crucible's prediction) | The plan as written |
| **t\* = 0.50** | The export lever is empty. H2 tests the network alone. The transfer switch still runs: with t\* = 0.5 its target is Janus 0's argmax width. The **grid trigger** of §6 is set |
| **t\* = 0.30, or FP rises at every t < 0.5** | Rim miscalibration. Round 3 reads the error decomposition (§5) and the calibration on the 60 before t\* ships. The switch stays clamped to [0.30, 0.50] |
| **Dice at t\* still > 0.03 under 0.934, volume ratio ≥ 0.95** (Crucible §7) | The grid binds. The **grid trigger** of §6 is set: a fallback run, if triggered, is at 0.45 mm. The 0.45 mm run is also a candidate for the round after an adopted Janus 1-L |
| Janus 0's per-case locked-100 SD | The stated MDEs are restated before any 1-L number: 2.80 × SD_Δ / 10, with SD_Δ taken as the larger of the measured paired proxy (0.034 for E; 0.046 for one run) and the value derived from Janus 0's SD. No margin moves (L-A7) |
| Job 0b: Janus 0's volumes on calib60 | The switch's target table. Nothing is decided until the candidate exists |

## 5. Item 5: the 60-case error decomposition

**Script:** `experiments/Foxtrot/j1l_r2/error_decomp.py`, self-tested; the method is in
[[Foxtrot - A tuning-60 error decomposition and a label-free check that t-star transfers, both self-tested and waiting on Job 0|the tools note]].
- It splits every class's recall loss on the tuning 60 into **cut, gap** (breaks), **misnamed** (naming) and
  **extent**, and its precision loss into **misnamed** and **outside**.
- The bins equal the frozen metric's recall and precision, asserted on every tree.
- For each kind of error, it reports the tF1 gain if only that error were removed.
- It refuses any case outside the tuning 60.

**The lead's command** (Trillium login node, after Job 0; CPU, ≈ 30–60 min):

```sh
source $HOME/icx14-venv/bin/activate; R=$SCRATCH/asclepius/repo; W=$SCRATCH/j1l_job0; J0=$SCRATCH/janus0
git -C $R pull --ff-only && python $R/experiments/Foxtrot/j1l_r2/error_decomp.py --selftest
T=$(python -c "import json;print('%.2f' % json.load(open('$W/select.json'))['chosen_t'])")
python $R/experiments/Foxtrot/j1l_r2/error_decomp.py --pred $W/thr/t0.50 --pred2 $W/thr/t$T \
   --icx $J0/icx --aorta $J0/aorta --layout $W/layout.json --np 16 --out $W/scores/decomp_tuning60.json
```

**Post on #302:** the printed `summary` and `summary2` blocks.

**The reading, fixed now:**

| Result (macro or LCx, mean tF1 gain on decisive trees) | Then (a later round, never Janus 1-L.1) |
|---|---|
| Breaks-fixed ≥ 0.02 and the largest | A connectivity arm earns a run (Skeleton Recall, guarded for disconnected components: BCS, arXiv:2607.28327) |
| Naming-fixed ≥ 0.02 and the largest | A naming arm (the namer, or class-weighted CE for the weak class) |
| Extent-fixed the largest | The threshold already acts on it. Compare the argmax and t\* rows |
| Every gain < 0.01 | No arm is worth a run on this evidence |

It decides nothing about Janus 1-L.1, whose recipe is frozen.

## 6. Item 6: one fallback run, pre-registered now

| | Pre-registered |
|---|---|
| **Trigger S** (warm-start failure) | H1 fails, **and** a1's and a2's point Δ macro against Janus 0 are both < 0 (the reports). That is Ash & Adams's warm-start signature, seen in both members |
| **Not a trigger** | H1 fails on one class's guard or on L3 alone, with a member's Δ ≥ 0. Then G5's listing and the round after decide, because a scratch run does not target a class |
| **The run** | From scratch on the 620, Janus 0's recipe (`nnUNetTrainerICX4`, 1000 epochs, one run, chained). **Form:** 0.5 mm with Janus 0's plans (≈ 53 GPU-h at 181 s/epoch), **unless Job 0 set the grid trigger (§4), in which case 0.45 mm** with its own fingerprint (Crucible's ≈ 55–60 GPU-h). One run answers both questions at the price of one |
| **Its export threshold** | The candidate trained on the tuning 60, so Rule W cannot be rerun. t\* applies with §3.2's switch, computed on its own calib60 volumes |
| **Its look** | **Janus 1-L.2**, against Janus 0 (not against E), with the same H1 → H2 → H3, margins and guards. One look |
| **The look budget** | Track 1-L spends **at most two candidate looks** on the locked 100. 1-L.2 is read only if 1-L.1 made no claim. A false "better" claim across the track therefore stays ≤ 2 × 2.5 % = 5 %. A third candidate needs a decision set other than the locked 100, chosen by a later round |
| **If 1-L.2 fails** | Janus 0 stays as track 1-L's model. The recipe reopens from §5's decomposition |
| **Cost** | Only if triggered: ≈ 53–60 GPU-h, plus ≈ 1 to predict |

**Why pre-register now:** the trigger, the run and the look are frozen before any Janus 1-L number exists, so none
of them can be shaped by a1's result. It costs nothing until it fires.

**Why not run it now:** at ≈ 55 GPU-h it would double the track for a question the warm runs may never raise.

## 7. Item 7: #306's specification, frozen

### 7.1 The interface (`trillium/janus1l/janus1l`, built from `trillium/icx4`)

**Inputs:**
- `JANUS0=$SCRATCH/janus0` (Step T);
- `J1L_JOB0=$SCRATCH/j1l_job0` (`select.json`);
- `J1L_JOB0B=$SCRATCH/j1l_job0b` (`vol_janus0.json`);
- `J1L_WORK=$SCRATCH/janus1l`.

**Dataset 718** (the PM pins the id; 715 is Janus 0, 716 the pool task, 717 A36's).

| Mode | What it does | Waits on | GPU-h |
|---|---|---|---|
| `J1L_DRYRUN=1 ./janus1l` | Prints every self-test line of §7.2; submits nothing | — | 0 |
| `./janus1l prepare` (**P**) | Dataset 718: the 620 + the locked 100, labels by `territory.to_four`. `nnUNetv2_move_plans_between_datasets` from 715, then `nnUNetv2_preprocess` only. A two-entry `splits_final.json` (both entries: train 620, val locked 100) | `select.json`'s sha256 on #302 | ≈ 1 |
| `./janus1l train` (**a1, a2**) | Folds 0 and 1, concurrent, `nnUNetTrainer_segtrain_finetune`, chain-resumable (`SEGTRAIN_MAX_SECONDS`, `--c`), `SEGTRAIN_SAVE_EVERY=10`, **`SEGTRAIN_SKIP_FINAL_VAL=1`** | P | ≈ 13 each |
| `./janus1l predict` | Each fold predicts the locked 100 + calib60 with `--save_probabilities --disable_tta`. Predictions only, nothing scored | a1, a2 | ≈ 2.5 |
| `./janus1l transfer` (CPU) | E = `nnUNetv2_ensemble -i fold_0 fold_1 --save_npz` for both sets; `t_transfer.py volumes` for E, a1 and a2 on calib60, then `decide` against `vol_janus0.json` at t\*. Writes `transfer.json` and prints its sha256. Deletes calib60's probabilities | predict | 0 |
| `./janus1l collect` (CPU) | **Only with `J1L_TRANSFER_SHA` equal to the posted sha256.** Exports C = E at `export_t`; the reports at t\* and argmax; scores (A1c scorer, Janus 0's aortas); H1 → H2 → H3 (L-A5, L3); the reports (L-A6); `looks.json` ledger | transfer | 0 |
| `./janus1l status` | s/epoch, stage, last log line | — | 0 |

### 7.2 Self-tests (`./janus1l selftest`, CPU; every line also printed by the dry run)

1. **Split:** the file sha256 is `19b832fe…4dd3`; the list pins are `bbd9c687…5895` and `1350cb1f…1152`;
   620/100 are disjoint, with 0 sealed; calib60 shares nothing with the 620, the locked 100 or the sealed lists.
2. **Sealed refusal:** an injected sealed id in any list makes the launcher refuse. The trainer's `refuse_sealed`
   also raises on it.
3. **No plan step:**
   - a mocked `PATH` makes `nnUNetv2_extract_fingerprint`, `nnUNetv2_plan_experiment` and
     `nnUNetv2_plan_and_preprocess` fail if called;
   - the moved plans may differ from Janus 0's only in `dataset_name` (a JSON diff), else stop.
   - This corrects L-A2's "byte-identical": `move_plans_between_datasets` rewrites the dataset name. The
     field-by-field identity that `finetune_load` checks is the real guard.
4. **Strict load:** `finetune_load` on a toy network loads strictly, heads included, bitwise. A perturbed plans or
   normalisation field makes it refuse.
5. **Janus 0's loss:** Janus 0's training log must hold no `class-weighted CE` line (icx4's optional
   `ce_class_weights.json` hook). If it does, stop: the fine-tune trainer has no class weights, so "the same recipe"
   would be false.
6. **Window:** `SEGTRAIN_CT_WINDOW=off` is exported, and `finetune_load`'s normalisation comparison is active.
7. **t\* applied:**
   - `prepare` refuses unless `select.json`'s sha256 equals `J1L_SELECT_SHA`;
   - `collect` refuses unless `transfer.json`'s equals `J1L_TRANSFER_SHA`;
   - every export carries the t it was made at, and collect asserts it.
8. **One look:**
   - final validation is skipped;
   - `predict` writes no score;
   - `collect` refuses a second run for a candidate already in `looks.json`;
   - no locked-100 label is opened before `collect`.
9. **Trainer settings:** both trainers are instantiated on a toy dataset, and every row of §7.3 marked "same" is
   asserted equal from the live objects, not from this table.

**One trainer change** (a few lines, in `nnUNetTrainer_segtrain_coronary.perform_actual_validation`, as icx4's
`ICX4_SKIP_FINAL_VAL` does): `SEGTRAIN_SKIP_FINAL_VAL=1` returns without validating.
- **Why:** nnU-Net's final validation predicts fold val (the locked 100) at argmax and writes its Dice to
  `validation/summary.json` and the log, for a1 and a2, the moment training ends. That is H2's metric, computed
  before `transfer.json` is frozen and outside the look.
- The per-epoch pseudo-Dice on random patches stays a display (L-A2).

### 7.3 `nnUNetTrainerICX4` (Janus 0) against `nnUNetTrainer_segtrain_finetune` (Janus 1-L), read from the code

| Setting | ICX4 (`trillium/icx4/lib/icx4_trainers.py`) | Fine-tune (`src/segtrain/nnunet_ext/…`) | Same? |
|---|---|---|---|
| Parent | `nnUNetTrainerNoMirroring` | `…_coronary` → `…_segtrain` → `nnUNetTrainer` | — |
| Mirroring, training and inference | off | off (`mirror_axes = None`, `inference_allowed_mirroring_axes = None`) | **same** |
| Loss | nnU-Net DiceCE with deep supervision; CE class weights **only if** `$W/ce_class_weights.json` existed | nnU-Net DiceCE with deep supervision, no hook | **same iff** self-test 5 passes |
| Optimizer | nnU-Net default: SGD, momentum 0.99, Nesterov, its weight decay | SGD, momentum 0.99, Nesterov, `self.weight_decay` | **same** |
| LR | nnU-Net poly per epoch from 1e-2 over 1000 epochs | 2500-iteration linear warm-up to 1e-2, then poly per iteration over 250 epochs | **intended** (A17a) |
| Epochs × iterations | 1000 × 250 | 250 × 250 | intended |
| Batch, patch, foreground oversampling, sampling, augmentation | nnU-Net defaults from the plans | not overridden | **same** (asserted, 7.2-9) |
| Validation per epoch | nnU-Net default iterations, pseudo-Dice | same | **same** |
| Final validation | runs unless stopped early; probabilities only with `--npz` | runs and saves probabilities by default | **differs**: skipped (7.2) |
| Checkpoint period | 10 epochs | nnU-Net default; `SEGTRAIN_SAVE_EVERY=10` | set equal |
| Time limit | `ICX4_DEADLINE`, a predictive stop | `SEGTRAIN_MAX_SECONDS`, a pause that keeps `checkpoint_latest` | equivalent |
| Sealed guard | in the launcher | also in the trainer (`refuse_sealed`; c-ids map) | stricter |
| Window/normalisation | none | window check off; `finetune_load` compares normalisation | stricter |

**Conclusion:** the recipes differ only where A17a intends (schedule, length) and where #306 now intends (final
validation), provided Janus 0 never used class weights.

## 8. Item 8: D28 and naming, given D46 Q5 and Q7

- **D28** ("the first retrained decision adds a second seed"): a2 runs (D46 Q5), so it is met. a2's mean against
  Janus 0 and |a1 − a2| are reported, and σ_g goes to 1-F (L-A6).
- **D46 Q5 and E:** §1.5. Under my reading, a2 is shipped only as a member of E, never alone. Under the other
  reading, a1 is the candidate.
- **Naming (D46 Q7):**

| Model | Name |
|---|---|
| E at t_E (the one candidate read) | **Janus 1-L.1** |
| The fallback of §6, if read | **Janus 1-L.2** |
| a1, a2, Janus 0 at t_E, any argmax export | Reports under 1-L.1; no number |
| The adopted model | **Janus 1-L** |

## 9. Cost (Trillium, 1 × H100, `def-aso22`; 181 s/epoch)

| Job | GPU-h | When |
|---|---|---|
| Step T | 0 | Now (before ~2026-12-20) |
| Job 0 (Crucible's, unchanged) | 3–4 | Now (D46 Q2) |
| **Job 0b** (Janus 0 on calib60, volumes only) | ≈ 1 | Now, beside Job 0 |
| P | ≈ 1 | After round 3 and #306 |
| a1, a2 (no final validation) | ≈ 13 each | P |
| predict (2 networks × 160 cases) | ≈ 2.5 | a1, a2 |
| transfer, collect | 0 (CPU) | predict |
| **Total** | **≈ 33–35** (ceiling ≈ 60) | |
| Fallback (§6), only if triggered | ≈ 53–60 | After the verdict |
| Predict all 1000 with E, if adopted | ≈ 4–8 | After adoption |

## 10. Commands for now (the lead runs them)

**Job 0b**, after this PR merges (Trillium GPU login node; it needs Step T only):

```sh
cd $SCRATCH/asclepius && git -C repo pull --ff-only
python repo/experiments/Foxtrot/j1l_r2/t_transfer.py --selftest
cd repo/experiments/Foxtrot/j1l_r2 && sbatch job0b_calib_volumes.sh
squeue -u $USER --name j1l-job0b
# when it has ended:
tail -3 j1l-job0b-*.out          # "volumes of 60 of 60 calib60 cases", and the sha256 line
```

**Post on #302:** the two lines of the `.out` tail. No image, label or probability file leaves Trillium.

**After Job 0:** the decomposition command of §5.

**Later:** the training jobs, through #306 (§7), after round 3.

## 11. What would change this plan

| Observation | Then |
|---|---|
| The lead reads D46 Q5 as excluding a2 from any shipped model (QF1) | a1 is the candidate; E is a report; §1.4 is moot |
| The lead declines the label-free use of calib60 (QF2) | t\* stays frozen (L-A4); §3.1's locked-100 report remains; Job 0b is dropped |
| Job 0's outcomes | §4 |
| \|a1 − a2\| > 0.02 macro | A37's ≥ 2 runs per arm for every later recipe claim. E's test is unaffected |
| `transfer.json` switches t | Recorded and posted. The verdict's wording names t_E and says it was switched by the label-free rule |
| The reported E − a1 is below 0 beyond its CI | The verdict stands. 1-F and the next 1-L round do not assume an ensemble gain |
| Self-test 5 finds class weights in Janus 0's log | Stop before P. A round decides between adding the weights to the fine-tune and accepting a recipe change |

## 12. Questions for the lead

**QF1. D46 Q5 and the ensemble.** Q5 says a2 is "report only, never shipped". Q6 and Q7 of the same decision accept
an ensemble containing a2 as 1-L.1. May a2 be shipped as a member of E, never alone?
- **Recommended: yes.** E is the sharper and more stable candidate (§1.1). If no, a1 is the candidate and nothing
  else changes.

**QF2. Label-free use of 60 open quality-0 images.** Their CT images only, no labels, never trained on. They are not
in D45's 620 or 100, and none of D45's sealed quality-0 20 is among them. They serve only to check whether t\*
transfers (§3).
- **Recommended: yes.** No D-number restricts them, but it is a new use of project data, so it is put to you.

**For the judge, not the lead:**
- §1.4, member-wise pool bases, is a proposal for the pool round (L-A11).
- §7.2's skipped final validation is an L-A7 point.
- §7.2-3 corrects L-A2's wording ("byte-identical" becomes "identical but for `dataset_name`").

## 13. Evidence index

**This round (CPU, `experiments/Foxtrot/j1l_r2/`):**

| File | What | Check |
|---|---|---|
| `ship_choice_sim.py` → `results/ship_choice_sim.json` (`33f6fe2a…c2c`) | §1's measured SDs and the simulated pass rates | Reads only `trillium-results/round6`, `round7` per-case files |
| `error_decomp.py` | §5 | `--selftest` passes; bins equal the frozen recall and precision |
| `t_transfer.py` | §3 | `--selftest` passes |
| `calib_cases.py` → `results/calib60.json` (ids sha256 `415c62ce…8345`) | §3's images | Asserts quality-0 = 200, sealed 20 and dev 24 inside it, no overlap with 620, 100 or sealed |
| `job0b_calib_volumes.sh` | §10 | `bash -n`; refuses sealed, locked or training ids |

**Repository evidence re-read:** `trillium/icx4/lib/icx4_trainers.py`;
`src/segtrain/nnunet_ext/{nnUNetTrainer_segtrain, _coronary, _finetune, finetune_load, ct_window, sealed_guard}.py`;
`src/segtrain/tf1.py`; `trillium/icx4/lib/tf1_score.py`; `experiments/Atlas/r9_score_icx4.py`;
`experiments/Crucible/j1l_r1/{job0_janus0_probs.sh, threshold_export.py, lists.json}`;
`trillium/make_sealed_test.py`; [[Sealed test]]; `trillium-results/round7/atlas3/SUMMARY.md`.

**External sources** (as cited in v1 and checked then; no new source this round):
- Mehrtash et al., IEEE TMI 39(12):3868–3878, 2020, doi:10.1109/TMI.2020.3006437 (Table II, Discussion);
- Isensee et al., Nat Methods 2021, doi:10.1038/s41592-020-01008-z (five-fold ensemble at inference);
- Ash & Adams, NeurIPS 2020, arXiv:1910.08475 (abstract);
- Piaggio et al., JAMA 2012, doi:10.1001/jama.2012.87802 (CONSORT non-inferiority);
- BCS, arXiv:2607.28327 (as verified in Delta's topology note).
