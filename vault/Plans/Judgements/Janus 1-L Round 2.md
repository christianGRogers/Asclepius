---
tags: [plans, judgement, track-1-L, round2, janus1-l, D45, D46, trillium, locked100, ensemble]
track: 1-L
round: 2
updated: 2026-11-15
issue: christianGRogers/Asclepius#302
---

# Janus 1-L, Round 2 ruling

This is round 2 of track 1-L (D45, #302). The five candidates are in `Candidates/Janus 1-L/`:
- [[Candidates/Janus 1-L/Crucible v2|Crucible v2]] (#323, the holder);
- [[Candidates/Janus 1-L/Bridge v2|Bridge v2]] (#324);
- [[Candidates/Janus 1-L/Delta v2|Delta v2]] (#325);
- [[Candidates/Janus 1-L/Atlas v2|Atlas v2]] (#328);
- [[Candidates/Janus 1-L/Foxtrot v2|Foxtrot v2]] (#329).

Round 2 had to settle the eight items of [[Janus 1-L Round 1]] §5, under D46 (the lead accepted every round-1
recommendation). **Step T and Job 0 have not run**, so nothing here rests on t\*, the identity check or Janus 0's
locked-100 spread. Every result they can give is mapped to an outcome now (L-A23).

The judge ran no experiment and did no research. The checks in §2 are re-reads of committed files and code, plus a
read of nnU-Net 2.8.1's own wheel to check the citations Bridge made to it.

## 0. Where the five agree

Nobody needs to argue these again:
- **The recipe, the split, Rule W on the tuning 60, H1 → H2 → H3 with L3, the identity check and the reports stand**
  (L-A1 to L-A8).
- **What ships is the candidate as tested.** No branch ships an argmax export or any other variant of C after the look.
- **A fallback is fixed before the look.** It is a from-scratch run S on the 620, triggered only when both warm runs
  are worse than Janus 0 at argmax (the warm-start signature, Ash & Adams, arXiv:1910.08475). It is never triggered by
  one class, by L3 or by FP alone. The 0.45 mm run is not an H1 fallback: its trigger is Job 0's.
- **The 60-case decomposition** decides only what a later round may propose, never Janus 1-L.1. All five wrote one,
  and each asserts it reproduces the frozen `tree_f1` per case.
- **nnU-Net's final validation must not run on the locked 100.** All five found the same leak: with fold val = the
  locked 100, `nnUNetTrainer_segtrain_coronary` predicts and scores them at argmax when each run ends, before t\* is
  applied and outside `collect`. That breaks L-A7.
- **#306 must set** `SEGTRAIN_SAVE_EVERY=10` and check that Janus 0 trained **without** icx4's `ce_class_weights.json`
  hook. Otherwise "the same recipe" is assumed, not checked.

## 1. Ruling: Delta v2 is track 1-L's plan, as amended (L-A13 to L-A25)

**[[Candidates/Janus 1-L/Delta v2|Delta v2]] is the plan in force for track 1-L.** Crucible v2 and Delta v2 now share
the same structure: E in a1's place, a pre-registered S, and a label-free transfer check. Delta v2 wins on three points:
1. **Its transfer rule measures what Rule W chose.** Rule W picks a lumen width. Delta's Rule T matches **width on the
   shared centreline**, so a candidate that draws more distal branches is not thinned to match a volume. It is the
   only rule tested on a phantom across six scenarios:
   - it recovers the oracle threshold in five;
   - it keeps t\* when nothing changed;
   - it shows how a plain volume match goes wrong when extent changes (Crucible's and Foxtrot's rules are volume
     matches).
2. **It found two defects in the decision code that would have decided the look wrongly** (both re-checked, §2):
   - the decision scorer writes `recall`, not L-A5's `recall_icx_traced`;
   - Crucible's `decide.py gate` implements A38's G3 as written (a plain mean ≥ −0.02), keeps FP outside H1, and has no
     −0.015 branch, so `collect` cannot reuse it.
3. **It corrects its own round-1 number.** L3's false-alarm rate is 3–8 % on the measured, heavy-tailed sibling
   differences, and up to about 19 % if the shift is broad (`l3_fix.json`). That is the kind of evidence the tournament
   rewards.

**Its weak points, fixed by amendment:**
- Its plans self-test ("`plans.json` sha256 equals Janus 0's") would fail every time, because
  `move_plans_between_datasets` rewrites two fields (Bridge; L-A21).
- It misses the `dataset_fingerprint.json` crash at training start (Bridge; L-A20).
- It counts S at 2.5 % one-sided, which makes a false adoption over the track up to 5 % (L-A18).

**What the others contribute:**
- **Crucible v2:**
  - the cleanest statement of E in a1's place, its a2-failure fallback, and the wording table (L-A14, L-A16);
  - S's α split at 1.25 % (L-A18);
  - the trainer diff and the final-validation skip as a thin subclass (L-A21).
- **Bridge v2:**
  - **four defects in the plan of record, read from nnU-Net 2.8.1's own code. All four are confirmed (§2), and three of
    them would have stopped or leaked the first training job** (L-A20, L-A21);
  - the 60-case decomposition of record, with its A23 extent rule (L-A22);
  - Q-B1, which closes a real gap in D46 Q4 (Q-R2-3).
- **Foxtrot v2:**
  - the measured per-case stability argument for E. On the only replicate pair, one case in nine moves by more than
    0.05 between siblings, and E's paired SD against a baseline falls by a quarter (L-A14);
  - the track's look budget: at most two candidate looks on the locked 100 (L-A18);
  - QF1 and QF2, merged into Q-R2-1 and Q-R2-2.
- **Atlas v2:**
  - the explicit "what ships is what was tested" rule and the guard-naming in the Q4 wording (L-A16);
  - Step T's training-log check (L-A20);
  - the observation that a1 and a2 shifting in opposite directions on the drift set means seed noise (L-A15 report).

### Binding amendments (track 1-L, Round 2)

L-A1 to L-A12 stay in force, except where the amendments below change them.

**L-A13. The plan in force.** Delta v2 as amended here, on top of L-A1 to L-A12 and D46.

**L-A14. The candidate is E, tested in a1's place (amends L-A3, L-A5's C, L-A12).**
- **C = E at t_C.**
  - E is the mean softmax of a1 and a2. `nnUNetv2_ensemble` of the two folds' saved probabilities equals
    `nnUNetv2_predict -f 0 1`, and lets a1, a2 and E come from one inference pass per network.
  - t_C comes from L-A15.
- **E replaces a1 in H1 → H2 → H3.** Every margin, guard and α is unchanged. One look. a1, a2, a1 at t_C, a1 at argmax
  and E − a1 are reports (L-A6).
- **Fallbacks, decided from logs before any locked-100 number exists:**
  - if a2 has not completed 250 epochs within two chained 23:50 jobs, C = **a1 at t_C**, with L-A15 run on a1;
  - if a1 has not completed, nothing is scored, and the PM reports it.
- **Subject to Q-R2-1.** If the lead reads D46 Q5 as barring a2 from any shipped model, C = a1 at t_C, and everything
  else here stands. The answer must be on record before Job P.

**L-A15. Rule T: t\* carried by width on unlabelled CTs (amends L-A4's "applied unchanged").**
- **D60:** Delta's `drift60.json`, pin `916e8a18…004e`.
  - These are 60 of ImageCAS's 200 quality-0 cases, after removing the 20 sealed (A14) and the 24 declared development
    cases, ranked by `sha256('asclepius-janus1l-drift60:' + id)`.
  - None is in the 620, the locked 100, the sealed lists, the SegQueue14 pool or Janus-M's `sealed-r1.json` (re-checked).
  - `fetch_cases.py` already brings their CTs to Trillium.
  - **No label or original ImageCAS mask of a D60 case is ever read.**
- **The rule (`experiments/Delta/j1l_r2/rule_t.py`, as Delta v2 §3):**
  - the reference is Janus 0 at t\* on D60: its skeleton, and the local radius (EDT) on it;
  - dr(t) is the 10 %-trimmed mean of C(t)'s radius minus Janus 0's, on the reference centreline points C(t) covers,
    pooled over D60;
  - t_C is the t ≤ 0.50 on the grid {0.50, 0.45, …, 0.25} with the smallest |dr|. Ties within 0.005 mm go to t\*, then
    to the larger t.
- **Scope:** if t\* was held back by a guard (Dice at t\* more than 0.002 below the best Dice on the grid), t_C = t\*.
- **It runs on C's own probabilities** (E's, or a1's under the fallback). a1's and a2's dr(t) are printed as reports.
  If they shift in opposite directions, the report says the shift is seed noise. It changes nothing.
- **Frozen:** `rule_t.json` and its sha256 are posted on #302 before `collect` computes any locked-100 number of C.
  `collect` refuses without the posted sha256.
- **Subject to Q-R2-2.** If the lead declines this use of quality-0 CTs, t_C = t\* (L-A4 unchanged), and Rule T's
  absence is stated in the verdict.

**L-A16. The verdicts and their wording (settles §5 item 2 under D46 Q3, Q4).**

| Outcome | Verdict | Wording of record (brackets filled by `collect`) |
|---|---|---|
| H1 fails | **Not adopted.** Janus 0 stays. G5 lists five cases for any class with point Δ < −0.05. L-A18 says whether S runs | "Janus 1-L.1 was not shown non-inferior to Janus 0 in tree-F1 (Δ m, 95 % CI [l, u]; margin −0.02) [or: failed the class / L3 / FP guard, named]. Janus 0 remains the model." |
| H1 passes, lower bound in (−0.02, −0.015], H2 fails | **Not adopted** | "Non-inferior to Janus 0 at 0.02 but not at the 0.015 that D46 Q4 requires for adoption without a width gain; not shown better. Janus 0 remains." |
| H1 passes, lower bound > −0.015, H2 fails | **Adopted** (D46 Q4), as tested at t_C. Subject to Q-R2-3 | "Janus 1-L is non-inferior to Janus 0 in tree-F1 at a pre-specified margin of 0.015 (Δ m, 95 % CI [l, u]), and passed the class, recall and FP guards (smallest class mean Δ: [class, value]). It is not shown better in lumen width (whole-tree Dice Δ d, 95 % CI [dl, du]) or in tree-F1. Adopted for its larger training set." |
| H1 and H2 pass, H3 fails | **Adopted** (D46 Q3) | "Janus 1-L is better than Janus 0 in lumen width: whole-tree Dice +d (95 % CI [dl, du]). Its tree-F1 is non-inferior at 0.02 (Δ m, lower bound l), with the class, recall and FP guards passed. A tree-F1 gain was not shown. [Share sentence.]" |
| H1, H2 and H3 pass | **Adopted** | As above, ending "… and better in tree-F1 (Δ m, lower bound l > 0)." |

- **Every adopted wording also states:**
  - "a two-network ensemble of fine-tunes of Janus 0, exported at foreground threshold t_C", and whether Rule T moved
    t_C from t\*;
  - the MDE stated under L-A23, and "under-powered" if the tF1 MDE is above 0.025;
  - L3's stated false-alarm rate (L-A17);
  - the val-80 and locked-20 parts, with any sign reversal reported and not acted on (A26).
- **The share sentence** is s = (Janus 0 at t_C − Janus 0 at argmax) / (C − Janus 0 at argmax), in whole-tree Dice,
  from the L-A6 reports:
  - s ≥ 0.8: "Most of the width gain is the export threshold, which applies to Janus 0 as well; the fine-tune adds
    [1 − s]."
  - s ≤ 0.2: "Most of the width gain is the fine-tune."
  - otherwise: "The threshold and the fine-tune each contribute."
- **Margins:** the −0.015 bound applies only in the branch with no width gain. With H2 passing, H1's −0.02 is enough.
- **CONSORT form** (Piaggio et al., JAMA 2012): every claim prints its two-sided 95 % CI beside the margin.
  "Not shown better" is never written "no better".

**L-A17. L3 reads the scorer's `recall` (corrects L-A5).**
- The decision scorer (`r9_score_icx4.py` → icx4's `tf1_score`) writes per-class tree-F1 `recall` against
  ImageCAS-X. It has no `recall_icx_traced`, which came from atlas3's scorer. With ImageCAS-X as the reference, the
  two are the same quantity. L3 is computed on `recall`.
- **L3's stated false-alarm rate is 3–8 %** (heavy-tailed shift, as measured), **and up to about 19 % under a broad
  shift** (Delta's `l3_fix.json`). The rule does not change.
- The report prints each class's excess kurtosis of the recall Δ, so a reader can see which regime the result came
  from.
- **`experiments/Crucible/j1l_r1/decide.py gate` is not the gate.** It applies G3 as written, keeps FP outside H1,
  and has no −0.015 branch. `collect` implements L-A5, L-A16 and L-A17, with self-tests (L-A21).

**L-A18. The fallback S and the track's look budget (settles §5 item 6).**
- **The track spends at most two candidate looks on the locked 100.** A third candidate needs a different decision set,
  chosen by a later round. Atlas v2 §6.2 (a 0.45 mm run with its own look after a1's) would be a third look, so it is
  refused.
- **Trigger (all of these):**
  - H1 fails;
  - a1 at argmax and a2 at argmax both have a point Δ macro tF1 < 0 against Janus 0 (the reports). This is read at
    argmax, so the signature is the training's, not the threshold's;
  - L0 passed.
- **Not a trigger:** H1 failing on one class, L3 or FP with either member's point Δ ≥ 0. Then G5's listing and the
  60-case decomposition go to the next round.
- **The run:** Janus 0's own recipe from scratch on the 620 (`nnUNetTrainerICX4`-equivalent settings, Janus 0's
  plans, 1000 epochs, one run, final validation skipped), ≈ 53 GPU-h in three chained jobs. Round 3 decides from Job 0
  whether its form is 0.45 mm instead (§5, item 3).
- **Its threshold:** t\* with Rule T run on S.
- **Its look:** Janus 1-L.2, against Janus 0, in the same H1 → H2 → H3 sequence and wording, with **every bound at
  one-sided 1.25 %**. So a false adoption over the track's two looks is at most 2.5 % + 1.25 %.
- **Allocation:** S runs only with the lead's allocation (Q-R2-4).
- **If S fails,** Janus 0 stays as track 1-L's model.

**L-A19. The base for pool fine-tunes, when E is adopted (amends L-A11).**
- A37 already runs two primary pool runs. **Pool a1′ starts from a1, and pool a2′ from a2.** The pool candidate is
  E′ = ensemble(a1′, a2′).
  - G1's replicate clause becomes "each member's Δ > 0".
  - G2 and L3 compare E′ with the adopted E on the locked 100.
  - The b arm (1e-3), if it runs, starts from a1.
- **This is cost-neutral against Round 10's A37.** Bridge's and Atlas's "+14–15 GPU-h per wave" does not hold for the
  first pool stage, which already budgets both runs.
- If a1 alone is adopted (the L-A14 fallback, or Q-R2-1 answered no), L-A11 applies as written.
- The pool round may revisit this with σ_g and E − a1 in hand.

**L-A20. Step T additions** (it has not run, so they cost nothing now; after the Fir purge, about 2026-12-20, they
cannot be recovered).
- **Copy `dataset_fingerprint.json`** from Janus 0's model folder. nnU-Net 2.8.1's `on_train_start` copies it from the
  preprocessed folder (`nnUNetTrainer.py` l. 972–973), so a1 and a2 would die at their first step without it. Do not
  re-fingerprint.
- **Copy Janus 0's `training_log_*.txt`** and post `grep -c "class-weighted CE"` for each (expected 0), and whether
  `$SCRATCH/icx4/ce_class_weights.json` exists (expected: no).
  - **If any log shows class-weighted CE, stop.** Round 3 decides between adding the weights to the fine-tune and
    accepting a recipe change.
- **Post Janus 0's `nnUNet_compile` setting** from icx4's `job_body.sh` on Fir.

The commands are in [[Master plan - Janus 1-L]] §5.

**L-A21. #306's spec, frozen (settles §5 item 7; amends L-A2, L-A10).**
- **Install:** segtrain goes into the icx14 venv **editable** (`pip install --no-deps -e repo`), or with
  `SEGTRAIN_SEALED_LIST` and `SEGTRAIN_POOL_SEAL` exported. A non-editable install looks for
  `trillium/sealed_test.json` beside the installed package (`proxy.load_sealed`, `Path(__file__).parents[2]`), finds
  nothing, and refuses to train. The dry run prints both paths.
- **P (dataset 718):**
  - the 620 + the locked 100, ids `cNNNN`, labels by `territory.to_four`;
  - Step T's `plans.json` copied first to `$nnUNet_preprocessed/Dataset715_ICX4/nnUNetResEncUNetPlans_60G_iso05.json`,
    which `move_plans_between_datasets` asserts exists;
  - then `nnUNetv2_move_plans_between_datasets`, then `nnUNetv2_preprocess` only;
  - Janus 0's fingerprint placed in the new preprocessed folder;
  - **no `plan_experiment`, no `extract_fingerprint`.**
- **The plans check replaces "byte-identical":** the moved plans equal Janus 0's once `dataset_name` and
  `image_reader_writer` are removed. `move_plans_between_datasets` rewrites both (l. 32, 56).
  `finetune_load.check_compatible` compares the configuration, intensity properties and transposes, not those two
  fields, so it still passes. A sha256 equality test (Atlas v2, Delta v2) would always fail.
- **`splits_final.json`:** two identical entries. Train = the 620. **Val = the 10 lowest-id cases of the tuning 60**
  (Bridge). nnU-Net 2.8.1 only warns when val is inside train (l. 651). So no per-epoch pseudo-Dice and no checkpoint
  selection ever touches the locked 100.
- **The trainer:** `nnUNetTrainer_janus1l`, a thin subclass of `nnUNetTrainer_segtrain_finetune` whose
  `perform_actual_validation` returns at once.
  - It is run with `SEGTRAIN_FINETUNE_FROM`, `SEGTRAIN_CT_WINDOW=off`, `SEGTRAIN_SAVE_EVERY=10`,
    `SEGTRAIN_SAVE_PROBABILITIES=0`, `SEGTRAIN_MAX_SECONDS` = walltime − 30 min, and `nnUNet_compile` as Janus 0's;
  - `SEGTRAIN_ITERATIONS` and `SEGTRAIN_EPOCHS` must be unset;
  - `checkpoint_best` is never read.
- **Modes:** `check` (self-tests and dry run), `prepare`, `train` (a1, a2 concurrent, chain-resumable), `predict`,
  `transfer`, `collect` and `status`.
  - `predict` covers folds 0 and 1 on the locked 100 and D60, and Janus 0 on D60, with `--save_probabilities
    --disable_tta`. E comes from `nnUNetv2_ensemble`. `predict` scores nothing.
  - `transfer` runs Rule T and stops after printing `rule_t.json`'s sha256.
  - `collect` refuses without `select.json`'s and `rule_t.json`'s posted sha256, and refuses a second run (a looks
    ledger).
- **Self-tests:** each must fail on a broken fixture before any submission.
  1. Split: the file hash `19b832fe…4dd3` and both list pins; a sealed or locked id in training refuses; val ⊂ tuning
     60.
  2. Sealed refusal at index, prepare, trainer, predict, transfer and decomposition.
  3. No plan step: a mocked `PATH` fails any fingerprint or planning call. The plans check above passes, and a changed
     percentile refuses.
  4. Strict load: `finetune_load` bitwise, heads included.
  5. The fingerprint is present, and the sealed list resolves.
  6. The trainer diff, asserted from live objects on a toy dataset: loss class and CE weight None; oversampling 0.33
     and not probabilistic; 250/50 iterations; batch and patch; deep-supervision scales; SGD momentum, Nesterov and
     weight decay; no mirror axes in training or inference; `save_every` 10; final validation a no-op; the LR at the
     first step, at warm-up end and at the last step.
  7. t applied: exports at t_C are byte-equal to `threshold_export.py`'s, and every file carries its t.
  8. Ensemble: `nnUNetv2_ensemble` of two copies of one fold reproduces that fold.
  9. **The gate:**
     - a uniform −0.03 LCx recall loss fires L3, and a heavy-tailed null mostly does not;
     - a lower bound of −0.017 with H2 failing gives "not adopted", and −0.012 gives "adopted (Q4)";
     - FP of 1.2 per case fails H1.
- **Built only after the round that rules the plan converged**, with the commands that round fixes.

**L-A22. The 60-case decomposition (settles §5 item 5).**
- **Script of record:** Bridge's `experiments/Bridge/j1l_r2/error_decomp.py`, run at t = 0.50 and at t\*. It has the
  finest categories (gap, root, fragment, distal with A23's contrast share, edge, stray). It refuses every case outside
  the tuning 60, and every case whose recall or precision differs from the frozen `tree_f1` by more than 1e-9.
- **The reading, applied by the next round to each group's macro ceiling** (a perfect fix's tF1 gain):
  - ≥ 0.030: an arm of that kind may be costed. A real arm recovers part of its ceiling, and half of 0.030 is about
    the locked 100's MDE;
  - 0.015–0.030: only after a no-training test on the 60 recovers half of it;
  - < 0.015: no arm.
  - If more than half of the `distal` points lie below A23's contrast line, no extent arm is proposed, whatever its
    ceiling.
- **Which lever fits which group.** The evidence on record (BCS, arXiv:2607.28327, as verified in Delta's topology
  note) is that Skeleton Recall recovers branches without connecting them.
  - **Extent** → Skeleton Recall.
  - **Breaks** → a connectivity lever that needs its own evidence, **not** Skeleton Recall. This corrects Bridge's and
    Foxtrot's mapping.
  - **Naming** → the namer or class-weighted CE.
  - **Width** → the threshold, already in the plan.
- LCx is read first.

**L-A23. Job 0's results, read by a table fixed now (settles §5 item 4).**

| Job 0 result | Then |
|---|---|
| L0 fails | Stop (L-A8). Nothing below is read, and #306 is not built until it passes |
| t\* ∈ {0.45, 0.40, 0.35}, Dice-bound | The plan as written |
| t\* = 0.50 with Dice peaking at 0.50 | The export lever is empty. Rule T still carries Janus 0's argmax width to C. The Q4 branch becomes the expected verdict, and the 0.45 mm form of S goes to round 3 |
| t\* held by a guard | t_C = t\* (L-A15 scope). The guard that bound is named on #302. If it is FP, round 3 looks at calibration on the 60 |
| t\* = 0.30, or FP rises at every t < 0.50 | Rim miscalibration. Round 3 reads calibration on the 60 (a temperature fit on Janus 0's probabilities, CPU) before #306 freezes t |
| Dice at t\* more than 0.03 below 0.934, with volume ratio ≥ 0.95 | The grid binds. The 0.45 mm form of S goes to round 3 |
| Dice(t\*) − Dice(0.50) on the 60 < 0.003 | H2 will likely fail on the threshold alone. Stated on #302 before training |
| Janus 0's locked-100 per-case SD | `experiments/Delta/j1l_r2/mde_from_job0.py` restates the MDE for a1 and E, in tF1 and Dice. No margin moves (L-A7) |
| The decomposition | L-A22, for later rounds only |

**L-A24. D28 and naming (settles §5 item 8).**
- D28 is met by a2 (D46 Q5). σ_g = |a1 − a2|/√2 is reported, with A37's rule if |a1 − a2| > 0.02.
- **Janus 1-L.1** = C (E at t_C, or a1 at t_C under the fallback). **Janus 1-L.2** = S, if read.
- a1, a2, Janus 0 at t_C and every argmax export are reports under 1-L.1 and take no number.
- The adopted model is **Janus 1-L**.

**L-A25. Cost** (Trillium, 1 × H100, 181 s/epoch).

| Job | GPU-h |
|---|---|
| Job 0 | 3–4 |
| P | ≈ 1 |
| a1 + a2 (concurrent, no final validation) | ≈ 25–27 |
| predict (2 folds × the locked 100 and D60; Janus 0 × D60) | ≈ 3 |
| transfer, collect, decomposition, MDE | 0 (CPU) |
| **Total** | **≈ 33–35**, ceiling ≈ 60 |
| S, only on its trigger and the lead's allocation | +≈ 53 (0.5 mm) or ≈ 55–60 (0.45 mm) |
| Predicting all 1000 with E, if adopted | ≈ 4–8 |

## 2. Scorecards

Scores are out of 5: (a) reasoning, (b) evidence, including spot-checked citations, (c) fit to D45/D46, the other
binding decisions and Trillium, (d) risk and cost.

| Candidate | (a) Reasoning | (b) Evidence | (c) Fit | (d) Risk/cost | Verdict |
|---|---|---|---|---|---|
| **Delta v2** | 4.5. E in a1's place with no assumed gain; withdraws its own ladder. The transfer rule measures width on the shared centreline, so extent cannot move it. Reads D46 Q5/Q6 openly and puts the reading to the lead | 5. Two notes: the ensemble simulation with the real heavy-tailed sibling noise, including the worst case (φ = 1: identical); and a six-scenario phantom for Rule T. It corrects its own round-1 L3 figure. `drift60.json` re-derived: pin matches, 0 sealed, 0 locked, 0 Janus-M. The L3 field and `decide.py` findings re-read and confirmed | 4. The plans sha256 self-test would always fail, and it misses the fingerprint crash. Otherwise exact: D60 is on Trillium already, and the final-validation skip is in place | 4.5. ≈ 33–35 GPU-h; S at 2.5 % (amended to 1.25 %) | **Track 1-L's plan**, as amended |
| **Bridge v2** | 4. Honest about E: its own table shows E never worse on H1 or Q4, and better at A37's τ. But its case for a1 rests on a pool cost that A37 already pays, and on "freezing t\* can only cost power". Its own Q-B1 is a counter-example: an over-widening t\* can lead to adopting a model with worse Dice through Q4 | 5. **The round's most practical evidence.** Four defects read from nnU-Net 2.8.1. Re-read in the wheel here: `on_train_start` copies `dataset_fingerprint.json` (l. 972–973); `move_plans` asserts the source preprocessed folder and rewrites `dataset_name` (l. 32) and `image_reader_writer` (l. 56); val ⊂ train only warns (l. 651). The `proxy.load_sealed` default path confirmed in `src/segtrain/proxy.py`. τ ≈ 0.001 from atlas3 F1 − F0 matches Foxtrot's 0.0013 | 4.5. The val = 10 tuning cases fix is the cleanest guard for L-A7 | 4. ≈ 32–33 GPU-h | Defects 1–4, the decomposition of record and Q-B1 adopted; a1 as candidate not adopted |
| **Crucible v2** | 4.5. The clearest pre-registration of E, with its a2 fallback and the wording table. The α split for S is the right accounting of a second look. Its Rule T is a volume match, which thins a candidate that draws more branches | 4. `ensemble_oc.json` agrees with Delta's and Foxtrot's directions. No phantom or test of its own drift rule beyond its self-test. Citations reused from round 1, as checked then | 4. Final-validation leak caught. Plans "except `dataset_name`" misses `image_reader_writer`. Misses the fingerprint. Proposes reusing `decide.py`, whose gate is G3 as written | 4.5. ≈ 33–36 GPU-h | E's pre-registration, the fallback rule and S's 1.25 % adopted; it loses the holder's seat to Delta v2's transfer rule and code catches |
| **Foxtrot v2** | 4. Moves its ground honestly from the mean seed lottery to per-case stability. The look budget of two is right. Its transfer switch is a volume match that fires only at two grid steps, which is coarse | 4.5. Re-read: SD 0.0455 → 0.0339 and 9 of 80 cases > 0.05 come from the committed atlas3 and atlas2 files. Note that E's score as the mean of its members' scores is an approximation it states. The 25 % cut is an upper estimate for a softmax ensemble. `calib60.json` pin matches, 0 sealed, 0 locked. It did not read the other round-2 plans, and says so | 4. `SEGTRAIN_SKIP_FINAL_VAL` does not exist yet, so it needs code. It ties S's form to Job 0 now | 4. ≈ 33–35 GPU-h | Per-case argument, look budget, QF1/QF2 adopted (merged) |
| **Atlas v2** | 3.5. Its argument against E (lineage, unmeasured gain) is answered by member-wise pool runs at no extra cost (A37). Its 0.45 mm arm after a1's look would be a third look. Its Rule T (inflation ratio) cancels extent better than a volume match, but has no phantom | 4. `u40.json` pin matches; 0 sealed, 0 locked (it keeps the 24 declared development cases, which is harmless for a label-free check). The trainer diff is right. Citations as in round 1 | 3.5. The plans sha256 self-test would always fail. Misses the fingerprint and the sealed-path defect | 4. ≈ 34–36 GPU-h | "Ships what was tested", the guard-naming wording and the training-log check adopted |

### Spot-checks this round

- **nnU-Net 2.8.1** (the wheel, downloaded to the scratchpad and read, not installed or run):
  - `nnUNetTrainer.py` l. 971–973: `shutil.copyfile(<preprocessed>/dataset_fingerprint.json, …)` in `on_train_start`;
  - l. 651–652: val inside train is only a warning;
  - `move_plans_between_datasets.py`: asserts the source preprocessed folder (l. 23–24) and rewrites `dataset_name`
    (l. 32) and `image_reader_writer` (l. 56);
  - the preprocessing API needs no fingerprint for `nnUNetv2_preprocess`.
- **`finetune_load.check_compatible`** compares the configuration block, the intensity properties and the transposes,
  not `dataset_name` or the reader. So the moved plans pass it.
- **`src/segtrain/proxy.py` `load_sealed`:** the default is `Path(__file__).resolve().parents[2] / "trillium" /
  "sealed_test.json"`, and a missing file raises. `sealed_guard.py` honours `SEGTRAIN_SEALED_LIST`.
- **`trillium/icx4/lib/icx4_trainers.py`:** the `ce_class_weights.json` hook (l. 29–39) and `ICX4_SKIP_FINAL_VAL`
  (l. 43) exist.
- **`trillium/icx4/lib/tf1_score.py` l. 96** writes `recall=` and `precision=`. `recall_icx_traced` exists only in
  `trillium/atlas3/lib/score.py`.
- **`experiments/Crucible/j1l_r1/decide.py gate`** (l. 92–110): the recall clause is a plain mean ≥ −0.02, FP sits
  outside H1, and there is no −0.015 branch.
- **Drift sets**, re-derived from the committed lists:
  - D60 (Delta): 200 → 180 → 156 → 60, pin reproduced;
  - U40 (Atlas): from 180, pin reproduced;
  - calib60 (Foxtrot): from 156, pin reproduced;
  - none holds a sealed id (`trillium/sealed_test.json`), a locked-100 id or a Janus-M id (`configs/janusm/sealed-r1.json`);
  - `fetch_cases.py` fetches the 200 unlabelled cases from `SegQueue/cases`.
- **Round 10's A37** runs a1 and a2 as primary runs plus b. So member-wise pool runs add no training.
- **Job 0's script** writes `scores/locked100_janus0_argmax.json`, the input `mde_from_job0.py` expects.
- **Citations:** no new external source this round. Isensee et al., Mehrtash et al., Ash & Adams, Piaggio et al. and
  BCS are as checked in round 1. **No citation was found unfindable or misquoted.**
- **Not opened:** no sealed case, no locked-100 number of any model, no pool read, no image or label.

## 3. Rulings on the contested points

### 3.1 a1 or E

**What the evidence says.** Three independent simulations (Crucible, Delta, Foxtrot) and Bridge's own table agree.
With no ensemble gain assumed, E in a1's place:
- passes H1 and the Q4 bar at least as often for a neutral or better model;
- passes Q4 less often for a model at −0.015 or −0.02;
- is identical to a1 in Delta's worst case (φ = 1, σ_g = 0).

The regret, "E fails H1 where a1 would have passed", is ≤ 3 % for any true Δ ≥ 0 (7 % pessimistic). E's lower H3 rate
at μ = 0 is fewer superiority claims for a neutral recipe, which is a feature.

**What the a1 side argued:**
1. **Lineage and cost.** Answered by L-A19. A37 already runs two primary pool runs.
2. **t\* on one network.** Answered by Rule T, run on E's own probabilities. In the phantom's ensemble scenario, a
   frozen t\* and Rule T both cost 0.005 Dice against the oracle.
3. **Double inference.** About 4–8 GPU-h per 1000-case pass. Small.

**The ruling:** E (L-A14), subject to the lead's reading of D46 Q5 (Q-R2-1). The ruling's own L-A3 said a2 is "never
shipped in a1's place", and D46 accepted Q7's note that E takes 1-L.1 if round 2 makes it the candidate. So the judge
reads Q5 as "never alone". A D-number is the lead's to read, though, so the reading goes to the lead.

**Evidence base, stated plainly:** all three simulations rest on one sibling pair (atlas3 F0/F1, val 80, Round 7's
recipe). a2 − a1 at the look is the first real measurement. It is reported, and it changes nothing at this look.

### 3.2 The t\* transfer

| Rule | Measures | Fault |
|---|---|---|
| Frozen (Bridge) | — | Over-widens a softer or self-widened candidate (phantom: −0.053 and −0.066 Dice). Through Q4, it can lead to adopting a model with worse lumen width (Bridge's own Q-B1) |
| Volume ratio, ±3 % band (Crucible) | Volume against Janus 0 at t\* | Extent moves it (phantom: 0.977 against 0.984) |
| Volume ratio, switch at two grid steps (Foxtrot) | The same | The same, and it is coarse |
| Inflation ratio (Atlas) | vol(t)/vol(0.5) against Janus 0's | Partly cancels extent. Untested beyond its self-test |
| **Width on the shared centreline (Delta)** | **What Rule W chose** | Domain caveat (quality-0 images), stated in the verdict |

**The ruling:** Delta's Rule T (L-A15). Every non-frozen rule needs unlabelled CTs. That is a new use of project data,
so it goes to the lead (Q-R2-2).

### 3.3 S, the 0.45 mm run, and the look budget

- **All five agree on the trigger.** The judge fixes it at argmax for both members, so a threshold that failed cannot
  pass for a warm-start failure.
- **α.** Two looks at 2.5 % each make a false adoption over the track up to 5 %. Crucible's 1.25 % for S keeps it at
  3.75 %, for about a 10 % wider MDE on S's look. S is already the second try, so this is the right trade.
- **0.45 mm.** Bridge and Foxtrot would switch S to 0.45 mm on Job 0's grid trigger. Crucible and Delta leave it to
  round 3. That decision needs Job 0's numbers and none exist, so round 3 decides (§5, item 3). It does so before any
  training job, which keeps it off locked-100 information.

### 3.4 The final-validation leak and fold val

All five closed the leak by skipping the final validation. Bridge's fix goes further: with val = 10 tuning cases, the
per-epoch pseudo-Dice and the logs never touch the locked 100 either. Both are adopted (L-A21). L-A2's "fold val = the
locked 100, display only" is withdrawn.

## 4. The first Trillium jobs

Unchanged: **Step T** (now, with L-A20's additions) and **Job 0** (≈ 3–4 GPU-h). After Job 0, two CPU commands run on
the login node: the decomposition (L-A22) and the MDE restatement (L-A23). Their commands are in
[[Master plan - Janus 1-L]] §5.

**Step T is urgent.** The Fir scratch purge is about 2026-12-20. L-A20's fingerprint cannot be recovered after it.

The training jobs wait for #306, built to L-A21 after the round that rules the plan converged.

## 5. What round 3 must settle

Round 3 is the earliest round that can rule the plan converged. **It can do so only if items 1 and 2 below are met.**
Otherwise it rules "not converged", says why, and round 4 follows.

1. **Step T and Job 0 have run, and their outputs are on #302:**
   - the `SHA256SUMS`, now including the fingerprint;
   - the class-weight check (L-A20);
   - L0's `summary` and `paired` blocks;
   - `select.json` and its sha256;
   - the decomposition summaries at t = 0.50 and at t\*;
   - the MDE restatement.

   Round 3 then applies L-A23's table, row by row, to the posted numbers. It reads no other number.
2. **The lead's answers to Q-R2-1 to Q-R2-4 are on record** (or are explicitly deferred by the lead, with the plan's
   default in force).
3. **S's form:** 0.5 mm (Janus 0's plans, its warm-start question only), or 0.45 mm if Job 0 set the grid trigger
   (L-A23). If 0.45 mm, round 3 gives:
   - its plans step and its 115 mm view check;
   - how t\* and Rule T carry to a new grid, or a stated "t = 0.50" export for it;
   - its cost.
4. **Calibration**, only if Job 0 gives t\* = 0.30, FP rising at every t < 0.50, or a guard-held t\*:
   - the temperature check on the 60;
   - whether Rule W is re-run on calibrated probabilities before training.
5. **If Step T found class-weighted CE in Janus 0's run:** add the weights to the fine-tune, or accept and name a
   recipe change.
6. **#306's commands, final.** L-A21 freezes the spec. Round 3 writes the lead's exact command block for `check`,
   `prepare`, `train`, `predict`, `transfer` and `collect` against the merged scripts:
   - Rule T's `rule_t.py` on E;
   - `collect`'s gate per L-A16 and L-A17, with Q-R2-3's clause if the lead says yes;
   - `mde_from_job0.py`;
   - Bridge's `error_decomp.py`.

   It confirms each script's interface (arguments, input files, outputs) by reading it. It also states the decomposition
   reading (L-A22) on the posted numbers: which group, if any, earns a later arm.
7. **One consolidated plan text.** The master plan with L-A1 to L-A25 (and any round-3 amendments) written through, so
   the converged plan reads as one document with no superseded clause.

## 6. Questions for the lead

None of these changes a D-number unless it says so. Each has a recommendation. Duplicates from the advocates are
merged, and the sources are named.

**Q-R2-1. D46 Q5 and the ensemble** (Foxtrot QF1 = Delta Q-L1). D46 Q5 says a2 is "report only, never shipped". Q6
accepts a two-network ensemble if pre-registered, and Q7 names E 1-L.1 if round 2 makes it the candidate. May a2 be
shipped as one of E's two members, never alone and never in a1's place?
- **Recommended: yes.** E passes a neutral or better model at least as often as a1, and a worse one less often, with no
  ensemble gain assumed (§3.1). Pool fine-tunes then run member-wise at no extra training (L-A19).
- If no, C = a1 at t_C, and everything else stands.

**Q-R2-2. Label-free use of 60 quality-0 CTs (D60) for the t\* transfer check** (Foxtrot QF2; Delta's, Crucible's and
Atlas's rules need the same).
- Only the CT images are used: no label and no original ImageCAS mask is read, and nothing is trained on them.
- They are outside the 620, the locked 100, the sealed 20, the pool and Janus-M's sets.
- Janus 0 and the candidate predict them, and only the two predictions are compared.
- **Recommended: yes.** No D-number restricts them, but it is a new use of project data.
- If no, t\* stays frozen (L-A4), and the verdict says the transfer was not checked.

**Q-R2-3. Should D46 Q4 exclude a model whose lumen width is shown worse?** (Bridge Q-B1; amends D46 Q4.) Under Q4, a
candidate that is non-inferior in tF1 but has whole-tree Dice shown **worse** than Janus 0's (the 95 % upper bound of
Δ Dice < 0) would still be adopted.
- **Recommended: yes, exclude it.** Add "and whole-tree Dice not shown worse" to Q4. D8 makes ImageCAS-X's lumen the
  target, and adopting on non-inferiority should not knowingly ship a thinner or fatter lumen.
- If no, the verdict adopts it and states "lumen width worse than Janus 0".

**Q-R2-4. S's allocation** (Delta Q-L2). If S's trigger fires (L-A18), will you run S (≈ 53 GPU-h; ≈ 55–60 at 0.45 mm)
on Trillium without waiting for another round?
- **Recommended: yes.** The trigger, the run and its look are fixed now, before any 1-L number exists. Waiting would let
  the result shape the fallback.
- If no, S goes to the round after the verdict like any other proposal, and needs a decision set other than the locked
  100 if it would be a third look.

**Actions, not decisions** (Bridge Q-B2; Crucible §12; Atlas §7.2; Delta §11): add L-A20's three items to Step T
before the Fir purge, about 2026-12-20. The commands are in [[Master plan - Janus 1-L]] §5.

## 7. What would change this ruling

| Observation | Then |
|---|---|
| The lead answers Q-R2-1 no | C = a1 at t_C (L-A14). L-A19 is moot |
| The lead answers Q-R2-2 no | t_C = t\* (L-A4). The predict job drops D60 |
| The lead answers Q-R2-3 yes | L-A16's Q4 row gains "and the upper bound of Δ whole-tree Dice ≥ 0" |
| Step T finds class-weighted CE in Janus 0's logs | Stop before P. Round 3 decides (§5, item 5) |
| Job 0's identity check fails | Stop (L-A8). Round 3 cannot rule converged |
| Job 0 sets the grid trigger | Round 3 decides S's form (§5, item 3) |
| Job 0 shows rim miscalibration | Round 3's calibration item (§5, item 4) |
| a2 fails twice | C = a1 (L-A14). D28's replicate is reported missing |
| \|a1 − a2\| > 0.02 at the look | A37's ≥ 2 runs per arm for later recipe claims. E's look is unaffected |
