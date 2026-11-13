---
tags: [plans, judgement, track-1-L, round1, janus1-l, D45, trillium, locked100]
track: 1-L
round: 1
updated: 2026-11-11
issue: christianGRogers/Asclepius#302
---

# Janus 1-L, Round 1 ruling

This is the first round of track 1-L (D45, #302): the training plan for **Janus 1-L**, an improved Janus 0 with the same
four classes, run by the lead on Trillium. The five candidates are in `Candidates/Janus 1-L/`:
- [[Candidates/Janus 1-L/Atlas v1|Atlas v1]] (#304);
- [[Candidates/Janus 1-L/Bridge v1|Bridge v1]] (#308);
- [[Candidates/Janus 1-L/Crucible v1|Crucible v1]] (#309);
- [[Candidates/Janus 1-L/Delta v1|Delta v1]] (#307);
- [[Candidates/Janus 1-L/Foxtrot v1|Foxtrot v1]] (#305).

The judge ran no experiment and did no research. The checks below are re-reads of committed files and code.

## 0. Where the five agree

All five keep the starting point's recipe, and nobody needs to argue it again in round 2:
- a **warm fine-tune of Janus 0** with the A17a trainer: full load with heads, 2500-iteration warm-up to 1e-2, then
  poly, 250 epochs;
- **Janus 0's plans unchanged**, with no new fingerprint (a new one would change the CT normalisation the warm network
  expects);
- mirroring off, DiceCE, `checkpoint_final` only, no TTA;
- training on D45's 620 alone. Pool reads join later, through Round 10's path.

They also agree, each from its own CPU experiment, on the fact that shapes the decision:
- the locked 100 can see a paired macro tF1 change of about **0.011–0.021**;
- 60 more training cases should buy about **0.001–0.005**.

**So a tF1 superiority gate on the data alone will almost always say "not shown".** The five answer that fact in three
different ways:
- **Add a measurable lever** (lumen width), and keep tF1 as a non-inferiority guard: Atlas, Crucible.
- **Adopt on non-inferiority**: Bridge (and Foxtrot's NON-INFERIOR verdict, left to the lead).
- **Keep a superiority gate** and add an ensemble to give it a chance: Delta, Foxtrot.

## 1. Ruling: Crucible v1 is track 1-L's plan, as amended (L-A1 to L-A12)

**[[Candidates/Janus 1-L/Crucible v1|Crucible v1]] is the plan in force for track 1-L.** It wins on four points:
1. **It answers the power problem with a lever the locked 100 can see.** Janus 0's one measured, fixable defect is a
   lumen drawn about one voxel inside ImageCAS-X's (Dice 0.880, volume ratio 0.867). D8 makes ImageCAS-X's lumen the
   target, and #302 asks for a width lever. Dice's MDE on the locked 100 is 0.003–0.006, so a width fix can be shown.
2. **It is the only candidate with new evidence on where the width deficit comes from.** It models nnU-Net's own
   resampling path, and finds that even a perfect network at 0.5 mm reaches only whole-tree Dice 0.934 and volume
   ratio 0.974. Janus 0 loses 13.3 % of the volume; the grid explains 2.6 %. So the first lever is the network's
   output, and a finer grid is the next one (§3.2).
3. **Its threshold rule is chosen where it cannot leak, by the right objective.** It is chosen on the 60 cases Janus 0
   never trained on. It maximises Dice subject to guards on tF1, FP and recall, rather than chasing a volume ratio.
4. **It is runnable.**
   - Its Job 0 script exists and is self-tested.
   - It handles the A17a trainer's window check correctly (`SEGTRAIN_CT_WINDOW=off`, see §3.4).
   - It is the cheapest (≈ 19 GPU-h).

**Its weak points, fixed by amendment:**
- one run with no replicate (L-A3);
- G3 as written, which false-alarms on about a third of neutral models (L-A5);
- a Step T command that downloads from a feature branch (L-A9).

**What the others contribute:**
- **Delta v1:**
  - the round's most consequential evidence, the G3 false-alarm rate and its trimmed fix (L-A5);
  - the folds-0/1 design that makes the replicate and the ensemble free (L-A3);
  - the split file and guard of #306 (L-A1, L-A10).
- **Atlas v1:**
  - the canonical list pins (L-A1);
  - the replicate's purpose, measuring σ_g for both tracks (L-A3);
  - the decomposition reports (L-A6);
  - Step T's copy of `plans.json` (L-A9).
- **Bridge v1:**
  - the measured Trillium speed, used for costing (L-A9);
  - the identity check with a per-class clause (L-A8);
  - the non-inferiority operating characteristics and CONSORT wording, used for Q4;
  - the side-aware D44 collapse (L-A11);
  - the 60-case error decomposition, which round 2 must use (§5).
- **Foxtrot v1:**
  - the per-case identity check against Fir's own predictions (L-A8);
  - the ensemble's variance argument, which round 2 must weigh (§5);
  - the catch that Wald et al.'s abstract does not support a fine-tuning schedule.

### Binding amendments (track 1-L, Round 1)

Amendments in this track are numbered **L-A*n*** so they cannot be confused with the main track's A1–A44. They
override the candidate text where they conflict.

**L-A1. The split and its pins (D45).**
- All five split files hold the same lists, checked here:
  - locked 100 = val 80 + c0068, c0102, c0251, c0271, c0323, c0327, c0470, c0545, c0592, c0620, c0644, c0805,
    c0807, c0824, c0827, c0841, c0908, c0946, c0957, c0996;
  - train 620 = train 560 + dev 44 + c0123, c0195, c0340, c0416, c0430, c0435, c0447, c0617, c0624, c0660, c0726,
    c0758, c0772, c0877, c0971, c0984;
  - the two lists are disjoint, and no case in `trillium/sealed_test.json`'s sealed ImageCAS-X 80 or quality-0 20 is
    in either.
- The five quoted hashes differ only in how the ids are joined. **The pins of record** are the sha256 of the sorted
  ids, joined by `\n`, with no trailing newline (Atlas's convention):
  - locked 100: `bbd9c687818956e2d5664b06fd8c8bd02ddb031e9b9d08036d59cc0e1a4d5895`;
  - train 620: `1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152`.
- **The file of record** is Delta's `experiments/Delta/j1l_r1/janus1_split_proposal.json` (file sha256
  `19b832fe…4dd3`), copied to `configs/janus1/split-2026-11.json` by #306 §1. The guard checks both the file hash and
  the two list pins. Track 1-F (#303) uses the same file and guard.

**L-A2. The recipe.**
- **Start:** Janus 0's `checkpoint_final.pth` (Dataset715), loaded by `nnUNetTrainer_segtrain_finetune` (A17a): full
  load, strict, bitwise-checked.
- **Schedule:** 2500-iteration linear warm-up to 1e-2, then poly; 250 epochs × 250 iterations; batch 2.
- **Plans:**
  - Janus 0's `plans.json`, byte-identical, moved to the new dataset with `nnUNetv2_move_plans_between_datasets`, then
    `nnUNetv2_preprocess`;
  - **no fingerprint and no `plan_experiment`**. This corrects Delta v1 §5 and #306's "plan and preprocess dataset
    718".
- **Window check:** `SEGTRAIN_CT_WINDOW=off`. `finetune_load`'s field-by-field comparison of plans and normalisation
  constants is then the guard. It is stricter than the window check it replaces.
- **Also fixed:**
  - mirroring off, in training and inference;
  - nnU-Net's default augmentation otherwise;
  - DiceCE with deep supervision;
  - uniform sampling over the 620;
  - fold val = the locked 100, for display only;
  - `checkpoint_final` only, never `checkpoint_best`;
  - `--disable_tta`.
- **Not in round 1:** Skeleton Recall (Atlas's arm b), the 1e-3 arm, class-weighted CE, a new spacing, a from-scratch
  run.

**L-A3. Runs.**
- **a1** (nnU-Net fold 0) is the pre-registered ship candidate.
- **a2** (fold 1, the same split entry) is its replicate. It is never shipped in a1's place. Its job is to measure σ_g
  on the master family (A37's open question), for this track and for 1-F.
- **E** (`nnUNetv2_predict -f 0 1`, mean softmax) is predicted and **reported only** in round 1. Whether E replaces a1
  as the ship candidate is round 2's question (§5, item 1) and the lead's (Q6).
- a2 runs subject to Q5. The recommended answer is yes.

**L-A4. Lumen width: Crucible's Rule W, frozen before training.**
- **Data:** Janus 0's probabilities on the **tuning 60** (dev 44 + the 16 trained open-36 cases), from Job 0.
- **Grid:** t ∈ {0.50, 0.45, 0.40, 0.35, 0.30}. A voxel is vessel where the summed vessel probability is ≥ t; its class
  is the argmax among the four vessels.
- **Choice:** the t with the highest mean whole-tree Dice, subject to:
  - mean decisive macro tF1 ≥ tF1(0.50) − 0.005;
  - FP components per case ≤ FP(0.50) + 0.10;
  - no class's centreline recall falls.
- **Ties** (Dice within 0.002) go to the larger t. t = 0.50 always qualifies.
- **Frozen:** `select.json`'s sha256 is posted on #302 before any training job is submitted. t* is applied unchanged
  to a1, a2 and E.
- **Not adopted:** Atlas's volume-ratio target, Delta's "closest to 1", Delta's second locked-100 test for adopting W,
  and Bridge's and Foxtrot's choices of t on halves of the locked 100. Any choice made on locked-100 numbers is a look
  (L-A7).

**L-A5. The decision on the locked 100, pre-registered.**
- **Candidate C** = a1 at t\*.
- **Baseline** = Janus 0 at argmax, re-predicted on Trillium in Job 0.
- **Scoring:**
  - `experiments/Atlas/r9_score_icx4.py` at A1c `24441cf8…5254`;
  - Janus 0's A1 aortas, copied from Fir;
  - flagged trees apart (A1b), provisional cases deciding nothing (A1a);
  - paired by case, 10 000 bootstrap resamples, each lower bound being a one-sided 2.5 % bound.
- **Fixed sequence:** each test is read only if the one before passes.

| # | Test | Passes when |
|---|---|---|
| **H1** | tF1 non-inferior, and nothing lost | Lower bound of Δ decisive macro tF1 > **−0.02**; **and** no class's mean Δ < −0.03; **and** the **recall guard L3** holds; **and** C's FP components per case ≤ 1 (A15) |
| **H2** | Width | Lower bound of Δ whole-tree Dice (native grid, `r10_dice_check.measure`) > **0** |
| **H3** | tF1 superior | Lower bound of Δ decisive macro tF1 > **0** |

- **The recall guard L3** (Delta v1 §4) replaces A38's G3 for this track. For no class may either hold:
  - the 10 %-trimmed mean Δ of per-class traced centreline recall (the scorer's `recall_icx_traced`) is < −0.02;
  - **or** its mean is < −0.02 **and** its 95 % upper bound is < 0.
- **Why L3:** G3 as written false-alarms on **31 %** of neutral fine-tunes at n = 100. Delta measured this by
  resampling the real per-case deltas of the warm replicate, which are heavy-tailed because a few trees flip between
  rooted and cut. L3 false-alarms on about 4 % and still catches a uniform 0.03 loss 99.9 % of the time. Atlas's H1,
  Bridge's L3 and Crucible's H1 all used G3 as written. Each would have failed about a third of neutral models.

**Verdicts:**

| Outcome | Verdict |
|---|---|
| H1 fails | **Not adopted.** Janus 0 stays. A class with point Δ < −0.05 has its five worst locked cases listed for the PM (G5). Round N+1 diagnoses from aggregates and the 60-case analysis, never by tuning on the locked 100 |
| H1 passes, H2 fails | **Non-inferior, not shown better.** Janus 0 stays as shipped, unless the lead answers Q4 yes. In that case a1 is adopted as the track's base if H1's lower bound is > −0.015, worded "non-inferior to Janus 0 at 0.015, not shown better" (Bridge's rule and CONSORT wording) |
| H1 and H2 pass | **Adopted: "better than Janus 0 in lumen width (Dice), tF1 non-inferior".** a1 at t\* is Janus 1-L |
| H1, H2 and H3 pass | **Adopted: "… and in tF1".** |

- Atlas's verdict "H1, and H2 or H3" does not fit its own fixed sequence, in which H3 is read only after H2. This
  sequence replaces it.
- **Dice as a co-decider after tF1 non-inferiority** reverses main-track A28 for this track. The judge rules it in,
  because #302 asks for tF1 and Dice and D8 makes ImageCAS-X's lumen the target. It is still put to the lead (Q3).

**L-A6. Reports beside the decision. None of them decides anything.**
- **What the threshold alone does:** Janus 0 at t\* against Janus 0 at argmax.
- **What the data alone does:** a1 at argmax against Janus 0 at argmax.
- **The verdict's wording** names the share of the Dice gain that Janus 0 at t\* already reaches. Janus 0 at t\* is
  **never** a separate ship candidate in round 1, because that would be a second look.
- a2 and E, each against Janus 0.
- **σ_g** = |a1 − a2| / √2, macro and per class. If |a1 − a2| > 0.02 macro, every later recipe claim in the track
  needs ≥ 2 runs per arm (A37).
- **Transfer of t\*:** C's Dice and volume ratio at every t.
- Per class: tF1, Dice, tolerant Dice, volume ratio, centreline recall and precision, FP.
- The val-80 and locked-20 parts separately (A26: a sign reversal is reported, not acted on).
- The 89 cases that were never on an advocate's development list.

**L-A7. One look.**
- Each candidate model's locked-100 numbers are computed once, after both runs are done.
- Nothing on the locked 100 chooses t, an epoch, a checkpoint, a run or a rule.
- Janus 0's baseline score in Job 0 is not a candidate look. Its per-case SD may update the stated MDE, but no margin.

**L-A8. The identity check (L0), before anything is read.**
- Janus 0 re-predicted on Trillium must reproduce Fir's val-80 decisive macro **0.909 within ±0.003**, and each class
  within 0.01.
- Where Fir's predictions were copied in Step T, ≥ 95 % of cases must also agree per case within 0.01.
- **Otherwise stop.** Nothing is decided until the PM has found the cause.

**L-A9. The jobs and their cost.**
- **Costing basis:** Trillium's measured **181 s/epoch** for this network (icx14's log, 446 epochs, mean 181.1 s,
  re-read here), not the older R0 175. That makes 250 epochs ≈ 12.6 h.
- **Order:**
  - **Step T** (now; no GPU): copy from Fir before the 60-day scratch purge, about 2026-12-20. The commands are in
    [[Master plan - Janus 1-L]] §5. Crucible's `curl` from the feature branch becomes `dev`.
  - **Job 0** (≈ 3–4 GPU-h): Crucible's `job0_janus0_probs.sh`, unchanged, plus the val-80 identity score.
  - **P + a1 + a2** (≈ 1 + 2 × 13.5 GPU-h): needs the #306 launcher.
  - **E + collect** (≈ 1 GPU-h).
- **Total:** ≈ **32–34 GPU-h**, with a ceiling of about 60.

**L-A10. #306 is the launcher issue, adopted with these changes.** It is built only after round 2 confirms §5 items 1
and 2.
- §1 (split file + guard): as written, plus the two list pins of L-A1.
- J0 is Crucible's Job 0 (L-A9), not a new J0. The launcher reads its `select.json`.
- No plan step (L-A2). `SEGTRAIN_CT_WINDOW=off` is set by the launcher. segtrain is installed into the icx4/icx14
  venv.
- a1/a2 as folds 0/1, chain-resumable on Trillium. Probabilities are saved for the locked 100. The export is at t\*.
- `collect` implements L-A5 to L-A8. The ladder, rung 1 (E), is not built until round 2 rules on it.

**L-A11. When pool reads arrive.** Round 10's A33–A39 apply, with these substitutions:
- the parent is the adopted Janus 1-L (or Janus 0);
- the replay set is the 620;
- the locked 100 replaces val 80 in G2, and in G3 in L3's form;
- D35 decides (G1) at A39's counts;
- D40 makes vessel-class overlaps the ignore label;
- **D44 reads collapse to four by territory before D40**: D1–D3 and S1–S3 → LAD; OM1, OM2 and the ramus → LCx (D1b);
  SN, conus and RMA → RCA; **PDA and PLB by the side they leave from** (D25, D1). Bridge and Delta agree on this.
- The handling of material classes is Q8.
- None of this changes the first jobs.

**L-A12. Naming.** This is the lead's (Q7). Until answered, no Janus number is assigned.

## 2. Scorecards

Scores are out of 5: (a) reasoning, (b) evidence including spot-checked citations, (c) fit to D45, the other binding
decisions and Trillium, (d) risk and cost.

| Candidate | (a) Reasoning | (b) Evidence | (c) Fit | (d) Risk/cost | Verdict |
|---|---|---|---|---|---|
| **Crucible v1** | 4.5. One pre-registered model and one fixed sequence; the width lever chosen off the decision set, by Dice with tF1, FP and recall guards. Flags its own reversal of A28 (Q3). Weak: no replicate, and G3 as written | 4.5. The resampling model follows nnU-Net 2.8.1's path (labels binarised at 0.5 mm, logits back, argmax). It supersedes Atlas's older round-trip note, which never binarises at 0.5 mm and so reports 0.994. Lipton et al. (arXiv:1402.1892) stated correctly and caveated; Ash & Adams Table 1 (56.2 vs 51.7) matches the other readers; FDA fixed-sequence guidance correctly dated, record id unconfirmed and said so | 4.5. Split exact (`lists.json` = the others' lists). Job 0 refuses sealed ids. Window handled. Step T pulls from a feature branch (fixed, L-A9) | 4.5. ≈ 19 GPU-h, Job 0 runnable today | **Track 1-L's plan**, as amended |
| **Delta v1** | 3.5. Its L1 is a superiority gate that its own numbers say a1 will rarely pass (+0.01: 0.26–0.75), so the likely end is "Janus 0 stays". W's adoption is a second locked-100 decision. The folds-0/1 design and the E − a1 test (MDE about 0.005–0.010) are good | 5. The G3 finding is the round's most consequential: 31 % false alarms, re-read in `power_locked100.json` and the code, which uses the scorer's traced recall. Split file hash verified (`19b832fe…4dd3`). Isensee 2018 §2.4 quote is correct | 3.5. "Plan and preprocess dataset 718" contradicts the warm start: `finetune_load` would refuse new plans. No handling of the window check, so its commands would stop at the trainer. Its checkpoint path assumes Round 10's Job 0 was run | 4. ≈ 33 GPU-h | L3, the folds design and #306's split guard adopted; the ladder deferred to round 2 |
| **Atlas v1** | 4. The same structure as the winner, and the clearest statement of why width is the lever. But arm b goes against the evidence it cites itself (BCS: Skeleton Recall doubles components on ImageCAS; Delta's verified note: "recover branches but do not connect them"). t is targeted at a volume ratio, not Dice. "H2 or H3" does not fit its fixed sequence | 4.5. Canonical pins reproduced exactly. Hestness §1, Summers & Dinneen abstract and Kirchhoff's 8 % / 2 % overhead all match Delta's verification note. It leans on its own older resampling note, which Crucible supersedes | 4. Misses the A17a window refusal. Arm b needs new loss code before the first job | 3.5. ≈ 46 GPU-h and an extra code item | Pins, replicate rationale, decomposition reports and Step T's `plans.json` copy adopted |
| **Bridge v1** | 4. Non-inferiority is the honest framing of what the locked 100 can answer, with the best operating characteristics of the round. But it offers no width lever although #302 asks for one, and its Option W picks t on half the locked 100, which is a look | 4.5. 181–182 s/epoch from icx14's log verified (mean 181.1 over 446 epochs). CONSORT non-inferiority citation (Piaggio et al., JAMA 2012) correct. Wrong that the A17a trainer "cannot be used as is": `SEGTRAIN_CT_WINDOW=off` exists in `ct_window.py` for exactly this | 4. A pre-registered from-scratch fallback. The best D44 → four analysis (PDA/PLB by side, materials before D40) | 4. ≈ 34 GPU-h, ≈ 83 at worst | Costing, L0, the side-aware collapse and the Q4 rule adopted; 60-case error analysis set for round 2 |
| **Foxtrot v1** | 3.5. The ensemble's variance argument is right. But the single E-vs-Janus 0 comparison is, in its own words, "a coin flip at best". Its NON-INFERIOR margin of −0.01 fails 21–39 % of neutral models. Width is left to a cross-fitted study on the locked 100 | 4. Power from the three real paired files. Mehrtash et al. (TMI 2020) cited with the right caveat (M = 50, Dice). States it did not read Ash & Adams' tables. Correctly drops Wald et al. | 4. Per-case identity against Fir's predictions is the best identity check of the round. The window value `61,808` works only if read from the plans, as its §8 says | 4. ≈ 28 GPU-h; ships a 2× inference model | Per-case identity check adopted; ensemble question sent to round 2 and the lead |

### Spot-checks this round

- **The split:** all five lists re-loaded. Locked 100 and train 620 are equal as sets across Atlas, Bridge, Crucible
  and Delta, and the locked 20 match Foxtrot's. 0 overlap, 0 sealed. Atlas's pins reproduce from Delta's lists. Bridge's
  pin is the same list joined by commas.
- **The window check:** `src/segtrain/nnunet_ext/ct_window.py` reads `SEGTRAIN_CT_WINDOW`, with `off` disabling the
  check. Crucible is right and Bridge is wrong. `finetune_load.py` compares plans and normalisation field by field.
- **Trainer equivalence:** `nnUNetTrainerICX4` (Janus 0) and `nnUNetTrainer_segtrain_coronary` (A17a's base) are both
  no-mirroring DiceCE trainers with a deadline stop. The A17a trainer has run on Trillium before (atlas3 F0, Round 8).
  #306's self-test should still diff the two trainers' loss and sampling settings (§5, item 7).
- **Trillium speed:** icx14's `train.log`, 446 epochs, mean 181.1 s.
- **G3:** Delta's script uses `split.recall_icx_traced` per class. The 31 % / 4 % / 0 % rows are in
  `power_locked100.json`.
- **Crucible's Job 0:** read in full. It asserts 160 cases with no sealed id, predicts with `--save_probabilities` and
  `--disable_tta`, and scores t only on the tuning 60. On the locked 100 it scores only Janus 0's argmax.
- **Resampling:** the two notes differ in method, not arithmetic. Atlas's resamples continuous masks there and back.
  Crucible binarises at 0.5 mm, as nnU-Net does to training labels.
- **Citations not re-checked beyond the vault's verification notes:** ImageCAS-X (arXiv:2608.30404) and BCS
  (arXiv:2607.28327), both full-text verified in Delta's topology note. **No citation in the round was found to be
  unfindable or misquoted.**
- **Not opened:** no sealed case, no locked-100 score of any model, no pool read.

## 3. Rulings on the contested points

### 3.1 Non-inferiority, superiority, or a second lever

**What the evidence says.** A superiority gate on the data alone fails a truly +0.005 model 72–85 % of the time
(Bridge, Foxtrot, Delta all measure this). Non-inferiority alone ships a model that is "not worse", which is a weak
claim for something called "improved Janus 0". The width defect is real, measured and seeable on the locked 100.

**The ruling.**
- tF1 stays the guard (H1). A tF1 gain is still claimed only by H3.
- **Dice decides only after tF1 is shown not to be worse** (Q3).
- Non-inferiority alone adopts only if the lead says so (Q4), at Bridge's tighter −0.015.

### 3.2 The width lever

**What is settled.** All five agree:
- the boundary sits about one voxel inside ImageCAS-X's, on a dim rim;
- extent is fine;
- tF1 barely sees width.

**The ruling.**
- **Round 1 lever:** an export threshold, chosen off the decision set, by Dice with guards (L-A4).
- **Next lever, triggered by Job 0 or the gate:** a finer grid (0.45 mm: ceiling 0.956, a 115 mm view, from scratch
  ≈ 55–60 GPU-h). Crucible §7 states its triggers.
- **Not adopted:** a loss change for width. It is a recipe change the locked 100 cannot attribute. Nobody brought
  evidence for one.

### 3.3 Runs: one, two, two + an arm, or an ensemble

| Option | Cost | Why not chosen |
|---|---|---|
| One run (Crucible) | 15 GPU-h | Leaves σ_g unmeasured on the master family, and both tracks need it. D28's fallback is ambiguous for 1-L (Q5) |
| Atlas's arm b | + 15.5 GPU-h | Not justified on current evidence |
| Delta's and Foxtrot's ensemble as the ship candidate | — | Its test design is not settled (§5, item 1), and shipping it is a lead's call (Q6) |

**The ruling:** a1 and a2 as folds 0/1, with E predicted as a report. The two runs are concurrent, so a2 costs no
wall-clock.

### 3.4 The trainer

Use the repository's A17a trainer with `SEGTRAIN_CT_WINDOW=off`. `finetune_load`'s strict plans comparison is the
guard. Bridge's self-contained copy of the trainer is not needed. Foxtrot's `61,808` is equivalent only when read from
the plans file, so `off` is the simpler form.

## 4. The first Trillium jobs

The first jobs are **Step T** (now) and **Job 0** (≈ 3–4 GPU-h, inference only). Their commands are in
[[Master plan - Janus 1-L]] §5.

**Job 0 settles no decision and leaks nothing:**
- it scores t only on the 60 training cases;
- on the locked 100 it scores only the baseline.

Running it before round 2 gives round 2 three things: t\*, the size of the width gain on the 60, and a passed or
failed identity check. That is Q2.

The training jobs (P, a1, a2, E) wait for #306 and for the rounds.

## 5. What round 2 must settle

1. **The ship candidate: a1 or E.**
   - If E, how it is tested without spending a second look: E replaces a1 in the same H1–H3 sequence, and is not tested
     in addition to it.
   - Which network is the base for pool fine-tunes.
   - The E − a1 evidence a pre-registration needs (Delta: MDE about 0.005–0.010). Q6's answer bounds this.
2. **The H1-pass, H2-fail branch**, given the lead's answer to Q4. **The H2-pass, H3-fail wording**, given Q3.
3. **t\* transfer.** With no held-out ImageCAS-X cases left outside the locked 100, say how a calibration shift
   between Janus 0 and a1 would show, and whether t\* stays frozen (the current rule) or a pre-registered alternative
   exists that never uses locked-100 numbers.
4. **If Job 0 has run:**
   - read `select.json`;
   - apply Crucible §7's triggers (t\* = 0.50, t\* = 0.30, Dice still more than 0.03 under 0.934 with the volume ratio
     ≥ 0.95);
   - restate the locked-100 MDE from Janus 0's exact per-case SD (no margin changes, L-A7).
5. **The 60-case error decomposition** (Bridge §7). Split LCx's and the other classes' tF1 loss on the tuning 60 into
   breaks, naming and extent, using Job 0's outputs. Write the CPU script and the lead's command. It decides whether
   any extent or topology arm (e.g. Skeleton Recall) is worth a run in a later round.
6. **The fallback when H1 fails.** Is a from-scratch 620 run (Bridge's S, ≈ 53 GPU-h at 181 s/epoch × 1000) or
   the 0.45 mm scratch run (Crucible) pre-registered now, with its trigger and its own look? Or is it left to the
   round after the result?
7. **#306's spec, frozen.**
   - The exact launcher interface and commands for P, a1, a2, E and `collect`.
   - Self-tests: split pins, sealed refusal, no plan step, strict load, t\* applied.
   - A diff of `nnUNetTrainerICX4` against `nnUNetTrainer_segtrain_coronary` (loss, sampling, oversampling,
     validation), so that "the same recipe" is checked, not assumed.
8. **D28 and naming**, given Q5 and Q7.

**Round 3 is the earliest round that can rule the plan converged** (#302).

## 6. Questions for the lead

None of these changes a D-number unless it says so. Each has a recommendation.

**Q1. Step T now.** Copy Janus 0's checkpoint, `plans.json`, `dataset.json`, its 160 aortas, the 160 ImageCAS-X labels
and Fir's predictions for the locked 100 off Fir's scratch before the 60-day purge (about 2026-12-20). Without
`plans.json` the warm start cannot be reproduced.
- **Recommended: yes, this week** (the commands are in [[Master plan - Janus 1-L]] §5).

**Q2. Run Job 0 before round 2?** It is inference only, ≈ 3–4 GPU-h on Trillium, and needs no new code. It fixes t\* on
the 60 training cases and checks that Janus 0 reproduces on Trillium. On the locked 100 it scores only the baseline.
- **Recommended: yes.** Round 2 then plans on measured numbers rather than predictions.

**Q3. Dice as a co-decider in track 1-L.** Main-track A28 says Dice decides nothing. Here, Dice superiority counts as
"better" **only after** tF1 non-inferiority and the class, recall and FP guards pass. This reverses A28 for this track,
and A28 is a plan rule, not a D-number.
- **Recommended: yes.** #302 asks for tF1 and Dice. D8 makes ImageCAS-X's lumen the target. The width defect is the
  one improvement the locked 100 can see.

**Q4. If a1 is non-inferior but not shown better** (H1 passes, H2 fails), is it adopted as Janus 1-L, the base for
the pool fine-tunes?
- **Recommended: yes, if H1's lower bound is > −0.015**, worded "non-inferior to Janus 0 at 0.015, not shown better".
  - It has seen 60 more cases.
  - A warm continuation on this family moved tF1 by −0.002 [−0.013, +0.007] (Atlas).
  - Bridge's rule adopts a model 0.02 worse at most 0.2 % of the time.
- The alternative (Atlas) keeps Janus 0 for its longer record.

**Q5. D28 on track 1-L.** Does "the first retrained decision adds a second seed" bind Janus 1-L?
- **Recommended: run a2 either way** (+≈ 14 GPU-h, concurrent, no wall-clock). It is a replicate, never shipped, and
  measures σ_g for both 1-L and 1-F.

**Q6. Would you accept a two-network ensemble as Janus 1-L,** if round 2 pre-registers it? It doubles inference
(about 1 extra GPU-minute per case; ≈ 3–4 extra GPU-h to predict all 1000), and the pool fine-tunes would still start
from one network (a1).
- **Recommended: yes in principle.** Round 2 decides whether the evidence earns it.

**Q7. Naming (D34/D45).**
- **Recommended:** only a model the decision reads as a candidate takes a number. a1 is **Janus 1-L.1**; the adopted
  model is called **Janus 1-L**.
- a2, E and Janus 0 at t\* are reports under 1-L.1 and take no number, unless round 2 makes E the candidate, in which
  case E takes 1-L.1 instead.

**Q8. D44 material classes in pool reads** (needed only before the first pool fine-tune of 1-L; reads D40 and D44).
- **Recommended:**
  - (a) material labels are dropped before D40's overlap rule, so a vessel voxel also marked as plaque stays vessel
    (Bridge);
  - (b) a voxel marked only as stent or plaque, with no vessel class, is **background**. The protocol is lumen-only,
    and a reader who saw lumen there would have marked a vessel, since every class is saved whole (D39).
- Delta recommends ignore for (b). The judge disagrees: ignore removes supervision exactly where the model must learn
  not to bleed into calcium. The lead decides.

## 7. What would change this ruling

| Observation | Then |
|---|---|
| Job 0's identity check fails | Stop (L-A8). Round 2 plans around the cause |
| Job 0: t\* = 0.50 | The export lever is empty. H2 tests the network alone, and round 2 weighs the 0.45 mm run (Crucible §7) |
| Job 0: t\* = 0.30, or FP rises at every t < 0.5 | Rim miscalibration. Round 2 looks at calibration on the 60 before any threshold ships |
| The lead answers Q3 no | H2 is a report. Adoption rests on H3, or on non-inferiority (Q4) |
| The lead answers Q6 no | E stays a report for the track |
| Pool reads reach A39's counts before the training jobs run | Unchanged: 1-L runs on ImageCAS-X alone first (L-A11) |
