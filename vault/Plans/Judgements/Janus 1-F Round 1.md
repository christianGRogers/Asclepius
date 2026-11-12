---
tags: [plans, judgement, track-1-F, round1, janus1-f, D44, D45, fir, locked100, partial-labels]
track: 1-F
round: 1
updated: 2026-11-12
issue: christianGRogers/Asclepius#303
---

# Janus 1-F, Round 1 ruling

This is the first round of track 1-F (D45, #303): the training plan for **Janus 1-F**, which segments the four vessels
plus D44's 14 branch classes, run by the lead on **Fir**. The five candidates are in `Candidates/Janus 1-F/`:
- [[Candidates/Janus 1-F/Atlas v1|Atlas v1]] (#318);
- [[Candidates/Janus 1-F/Bridge v1|Bridge v1]] (#312);
- [[Candidates/Janus 1-F/Crucible v1|Crucible v1]] (#313);
- [[Candidates/Janus 1-F/Delta v1|Delta v1]] (#320);
- [[Candidates/Janus 1-F/Foxtrot v1|Foxtrot v1]] (#319).

The judge ran no experiment and did no research. Every check below is a re-read of committed files and code.
[[Janus 1-L Round 1]] is context only. Where the two tracks share something, this ruling follows it and says so (§7).

## 0. Where the five agree

The five reached the same plan from five independent censuses. Nobody needs to argue these points again in round 2.

**The facts:**
- **ImageCAS-X never traced six of 1-F's classes.**
  - Its protocol says that septal perforators, acute marginals and nodal arteries were not traced (arXiv:2608.30404,
    Suppl. B, quoted the same way by all five).
  - The labels agree. Unnamed side branches hang off the trunk classes in 0.5–2 % of cases, depending on the cut-off.
  - So S1–S3, SN, Conus and RMA are **background** in ImageCAS-X, not unlabelled children of their parent. No
    partial-label loss can learn them from the 620 alone.
- **ImageCAS-X numbers its branches by origin order.**
  - D1 before D2 in 349–359 of 349–359 cases with both, depending on the advocate's origin rule.
  - OM1 before OM2 in 222–228 of 222–228.
  - The first LAD-side "Other" piece comes after D2 in 45–47 of 45–47.
  - So **D3 is the first LAD-side "Other" piece**, in 47 training cases. It is a large-D3 class only.
- **icx14 never learned a branch.**
  - It trained from scratch. Nine of its ten branch classes had pseudo-Dice 0 for about 450 epochs, although D1 was
    in 631 of 640 cases. R-PLA appeared at about epoch 424–440.
  - It was cancelled at about 45 % of its schedule, so it shows a long delay, not impossibility.
- **About 9.5 % of the 620 have a left-sided PDA or PLA** (58–59 cases).

**The design** (one network, two stages):
- **One nnU-Net, warm-started from Janus 0 by parent copy.**
  - Every new branch output copies its parent's output row, and the biases of each territory drop by log of the
    territory's size.
  - At step 0 the territory probabilities equal Janus 0's, to about 1e-15. Atlas, Bridge, Crucible, Delta and
    Foxtrot each checked this.
- **Stage 1 trains only what ImageCAS-X traced**, on the 620, with Janus 0's plans, 500 epochs and mirroring off.
- **Stage 2 adds S1–S3, SN, Conus and RMA later**, from extended pool reads, through a label-set (marginal) loss.
- **The vessels are guarded on the locked 100** at Round 10's forgetting margin: the lower bound of Δ macro tF1 must
  be above −0.02, and no class may fall by more than 0.03.
- **If the vessels fail, a fallback ships:** Janus 0's four-class voxels, named by 1-F inside each territory. It has
  four names in this round (Bridge's composite, Crucible's hybrid, Delta's reading T, Foxtrot's relabel-within-mask)
  and is one design.
- **Nobody proposes re-annotating ImageCAS-X** (D22 stands).

## 1. Ruling: Delta v1 is track 1-F's plan, as amended (F-A1 to F-A13)

**[[Candidates/Janus 1-F/Delta v1|Delta v1]] is the plan in force for track 1-F.** It wins on four points.

1. **It is the most runnable.** It is the only candidate that carries track 1-L's settled mechanics over correctly:
   - L-A1's split file and pins;
   - Janus 0's plans byte-identical, with no fingerprint and no `plan_experiment`;
   - `SEGTRAIN_CT_WINDOW=off`;
   - A17a's loader extended by one option.
   The launcher refuses to start until the left-PDA switch is set.
2. **Its labels collapse exactly to D25.** `j1f_labels.py` checks every training label against `territory.py`'s four
   classes, so the vessel guard compares like with like. On the 620 the only mismatch is 40 "Other" voxels in 2 cases.
3. **It is the only candidate whose gate eligibility is measured rather than scaled.**
   - It counted the locked 100's reference labels (D1 98, D2 64, OM1 84, OM2 40, PDA 96, PLB 96; Ramus 24, D3 7).
   - These are label counts, not a model score, so they are not a look. They fix which classes are gated before
     any model exists (§2, spot-checks).
4. **It keeps both answers to "segment-then-label or one network".** The free reading F and the territory-constrained
   reading T come from the same run, and T's vessels are Janus 0's by construction.

**Its weak points, fixed by amendment:**
- Decoding by plain argmax over 13 channels (F-A4, from Atlas).
- No recall guard, so a vessel could shorten unseen (F-A6, L3 from track 1-L).
- A presence-agreement gate that a model calling D1 in every case would pass (F-A6).
- Pairing against track 1-L's Trillium J0, when Fir already holds Janus 0's predictions and aortas (F-A8).
- A stall check read from the locked 100's pseudo-Dice (F-A5).
- A Q1 recommendation that the other four advocates and track 1-L's L-A11 disagree with (§6, Q1).

**What the others contribute:**
- **Atlas v1:**
  - hierarchical decoding (F-A4), with the round's most consequential check: a plain argmax over the grown head moves
    **2.5 %** of voxels to another territory at step 0 (`head_init_check.out`, re-read);
  - the rule-ordinal reading as a report (F-A9);
  - the "group complete" flag (Q3);
  - the zero-GPU namer Arm N, sent to round 2 (§5).
- **Bridge v1:**
  - the only empirical design for "how many reads per class", Job B, sent to round 2 (§5);
  - the child-in-parent overlap question (Q4);
  - the SN origin evidence (Koşar et al.);
  - the dormant-type leakage check, kept for stage 2.
- **Crucible v1:**
  - leaf-Dice for stage 2's Dice term, the only Dice-term choice backed by a table (Fidon et al. Table 2);
  - the territory band and the inter-read agreement floor for training a class (F-A11);
  - L2 (unlisted branches go to their parent);
  - the cross-track septal note for #302 (§7).
- **Foxtrot v1:**
  - the stall check on fixed **training** cases (F-A5), which needs no look at the locked 100;
  - F0, runnable today (F-A8);
  - ignore for the unexplained "Other" pieces (F-A3);
  - the replicate's case (Q8).

### Binding amendments (track 1-F, Round 1)

Amendments in this track are numbered **F-A*n***, so they cannot be confused with the main track's A1–A44 or track 1-L's
L-A*n*. They override the candidate text where they conflict.

**F-A1. The split is track 1-L's (L-A1), unchanged.**
- **File of record:** `configs/janus1/split-2026-11.json` (from Delta's 1-L file, #306 §1). It does not exist on `dev`
  yet, so both launchers wait on it.
- **Pins:**
  - locked 100 `bbd9c687818956e2d5664b06fd8c8bd02ddb031e9b9d08036d59cc0e1a4d5895`;
  - train 620 `1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152`.
- **The locked 20 are hashed on the `cNNNN` id form**, as L-A1 already pins. Atlas's Q3 and Crucible's L5 are settled
  by L-A1 and do not go to the lead again.

**F-A2. Stage 1's recipe (J1F-A).**
- **Start:** Janus 0's `checkpoint_final.pth` (Dataset715).
  - Loaded by A17a's `finetune_load`: every non-head tensor strict and bitwise.
  - Each `seg_layers` head, deep supervision included, is built by parent copy (Delta's `parent_copy.py` rule).
  - The loader refuses unless, on a random batch, the territory sums equal Janus 0's within 1e-5 **and** the
    hierarchical decode equals Janus 0's argmax on every voxel.
- **The start is pinned to Janus 0 for round 1.** Atlas and Foxtrot would switch to Janus 1-L if it is adopted first.
  This ruling does not: it would move the comparator mid-plan, and Janus 1-L runs on Trillium. Round 2 may revisit
  (§5, item 9).
- **Plans:**
  - Janus 0's `plans.json`, byte-identical, moved with `nnUNetv2_move_plans_between_datasets`, then
    `nnUNetv2_preprocess`;
  - no fingerprint and no `plan_experiment`;
  - `SEGTRAIN_CT_WINDOW=off`;
  - **Dataset 719**. The launcher refuses an id already in use.
- **Schedule:** 500 epochs × 250 iterations, batch 2, 2500-iteration linear warm-up to 1e-2, then poly. This is
  A17a's shape. Bridge's poly from 1e-2 with no warm-up is not adopted: a grown head should not take a full-LR first
  step.
- **Loss:** nnU-Net's DiceCE, unweighted, with deep supervision and the stock ignore label (255) only.
  - Stage 1 needs no new loss. Foxtrot's set-valued CE for L-PDA/L-PLA is not needed once Q1 fixes their label
    (F-A3).
  - Bridge's dormant heads would put the marginal loss on stage 1's critical path. They are not adopted.
- **Fixed:**
  - mirroring off, in training and inference;
  - nnU-Net's default augmentation otherwise;
  - uniform sampling over the 620;
  - `checkpoint_final` only;
  - `--disable_tta`.
- **Fold-0 validation is the locked 100, for nnU-Net's display only.** Its pseudo-Dice is never read for a decision,
  a stop or a checkpoint (F-A5, F-A7).
- **One run in round 1 (a1).** A replicate a2 is the lead's call (Q8).

**F-A3. Stage 1's classes and labels (13 outputs).**
- **Outputs:** bg, LM, LAD, LCx, RCA, D1, D2, D3, OM1, OM2, Ramus, PDA, PLB.
- **Labels:** Delta's `j1f_labels.py` map, with two changes.
  - **L-PDA / L-PLA follow the lead's answer to Q1.**
    - Under the recommended (A), they become PDA / PLB.
    - Under (B), they become LCx, which is Delta's `--left-pda lcx`.
    - Under (C), they become PDA / PLB, and only the collapse differs (F-A4).
    - The launcher refuses until `JANUS1F_LEFT_PDA` is set.
  - **"Other" pieces that touch only the RCA or nothing** (8 on the 620) become **255, ignore** (Foxtrot), not guessed.
- **Unchanged from Delta:**
  - the first LAD-side "Other" piece → D3;
  - later LAD-side pieces → LAD;
  - LCx-side pieces → LCx;
  - IM → Ramus;
  - R-PDA/R-PLA → PDA/PLB.
- **D4+, S4+, OM3+** stay in the parent, as SegQueue 0.18.0's own instructions already say. So do unlisted branches
  (AV-nodal, atrial, other unnamed branches), per Crucible's L2. This is not a new decision, and it is listed in
  Q1's note only for completeness.

**F-A4. Decoding: hierarchical, and the four-class collapse by origin.**
- **Hierarchical decoding (Atlas):**
  1. The territory is the argmax of the summed probabilities over {bg}, {LM}, {LAD, D1, D2, D3}, {LCx, OM1, OM2,
     Ramus} and {RCA, PDA, PLB}.
  2. The class is the argmax within that territory.
- **Why:** with parent copy, a plain argmax compares single channels of territories of different sizes (k = 4, 4, 3).
  At step 0 it moves 2.5 % of voxels to another territory (3.7 % with stage 2's head). Delta's and Foxtrot's
  self-tests check the territory **sums**, which is correct but is not what nnU-Net's argmax export does.
- **Consequence:** prediction must export from logits or probabilities, not from nnU-Net's own label export. This is
  the launcher's job (§5, item 8). Reading T is the same decode, with step 1 replaced by Janus 0's argmax.
- **The four-class collapse used for every vessel score is by origin (D25, D1):**
  - D1–D3 → LAD; OM1, OM2, Ramus → LCx (D1b).
  - A PDA or PLB connected component goes to the vessel it touches most (LCx or RCA). Under Q1 (B) none touches the
    LCx, because those voxels are LCx already.
  - Under Q1 (C), the collapse is "PDA/PLB → RCA always". V1's Janus 0 reference is then relabelled the same way,
    from ImageCAS-X's L-/R- labels (Atlas §10).

**F-A5. The stall check reads training cases only (Foxtrot §4.4, simplified).**
- **Fixed cases:** the 20 cases of the 620 with the smallest sha256(`asclepius-j1f-fitcheck:` + id).
- **At epochs 150 and 300,** the job predicts them with the then-current weights, decoded as in F-A4, and writes
  per-class Dice to `fitcheck.json`.
- **Stall rule (pre-registered):** at epoch 150, if any of D1, OM1, PDA or PLB has fit Dice < 0.10, the job writes
  `STALL`. That is icx14's failure: exactly 0.
  - The PM may then cancel the run, saving about 18 GPU-h.
  - Round N+1 chooses between class weights, a two-network design and a graph namer.
- **Foxtrot's mid-run switch to class weights is not adopted.**
  - The read model would mix two recipes.
  - The chain's first chunk boundary falls near epoch 440, not 150.
- **Delta's "pseudo-Dice still 0 at epoch 250" read from `status`** uses the locked 100. It is replaced by this rule.

**F-A6. The decision on the locked 100, pre-registered.**

| Item | Definition |
|---|---|
| **Candidate F** | J1F-A at `checkpoint_final`, decoded as in F-A4 |
| **Candidate T** | Janus 0's argmax territories, with J1F-A's within-territory argmax |
| **Baseline** | Janus 0's existing Fir predictions of the locked 100 (`$SCRATCH/icx4/predictions`, or Step T's copy), at argmax |
| **Scoring** | Janus 0's A1c scorer (`24441cf8…5254`) with its in-job aortas (all 100 locked cases have one: icx4 made aortas for the 160 non-sealed val and open cases, re-read in [[icx4 - Results]]). A1a/A1b exclusions. Paired by case, 10 000 bootstrap resamples, each lower bound a **one-sided 2.5 %** bound, as in L-A5 |

A **fixed sequence**: each step is read only if the one before it passes.

| # | Test | Passes when |
|---|---|---|
| **V** | F's vessels hold | Lower bound of Δ decisive macro tF1 (F collapsed − Janus 0) > **−0.02**; **and** no class's mean Δ < −0.03; **and** track 1-L's recall guard **L3** holds; **and** F's FP components per case ≤ 1 (A15) |
| **B** | Each **gated** class (D1, D2, OM1, OM2, PDA, PLB: ≥ 30 locked cases with the class, counted by Delta) passes, on the reading that ships | **B1, detection:** branch-level detection recall ≥ **0.80** (a reference branch is detected if ≥ 50 % of its centreline lies within 1.5 mm of predicted vessel of any class), **and** presence agreement ≥ ImageCAS-X Table 1's inter-observer agreement − 0.05 (D1 ≥ 0.919, D2 ≥ 0.844, OM1 ≥ 0.894, OM2 ≥ 0.825, PDA ≥ 0.938, PLB ≥ 0.912). **B2, naming:** among detected reference branches, the share whose covered centreline is mostly the right class is ≥ **0.85** |

- **Why two detection measures.** Presence agreement alone is passed by a model that calls D1, PDA and PLB present in
  every case: 98–96 of 100 locked cases have them. Branch-level recall alone does not punish over-calling in D2 or
  OM2 (36 and 60 locked negatives). Together they do both.
- **The recall guard L3** (Delta's, from track 1-L) replaces A38's G3, which false-alarms on about a third of neutral
  models at n = 100. Atlas's and Bridge's V2 used G3 as written. Crucible, Delta and Foxtrot had no recall guard.
- **Crucible's "one-sided 95 %" bound** is looser than track 1-L's. Both tracks use the one-sided 2.5 % bound.

**Verdicts:**

| V | B | Ships |
|---|---|---|
| pass | ≥ 4 of 6 gated classes pass | **F** is read as the next Janus number (Q9). Gated classes that fail, and Ramus and D3, ship **folded into their parent** in the exported map and are listed. Ramus and D3 are reported with n and CI |
| fail | ≥ 4 of 6 pass on **T** | **T** is read in F's place. Its four classes equal Janus 0's by construction. The vessel loss of F is reported and round N+1 diagnoses it |
| either | < 4 of 6 pass on the reading that would ship | **Not adopted.** Nothing ships. Round N+1 chooses among class weights, Delta's F3 (from scratch, 1000 epochs, ≈ 58 GPU-h) and a graph namer on Janus 0's tree. No GPU run follows automatically |

- **Thresholds may be tightened or loosened by round 2, before J1F-A is submitted, and never after** (§5, item 1).
- Atlas's B1 (beat Arm N with a lower bound > 0) is not a gate this round. Its power is unknown and Arm N does not
  exist yet (§5, item 3).

**F-A7. One look.**
- F's and T's locked-100 numbers are computed once, after J1F-A ends.
- Nothing on the locked 100 chooses an epoch, a checkpoint, a threshold, a reading, a class weight or a stop.
- **Locked-100 *labels* may be counted** (presence, piece counts) to fix eligibility before any model exists, as Delta
  did. No other locked-label analysis may steer a recipe choice.

**F-A8. Before anything is read.**
- **F0 (Foxtrot), login node, 0 GPU-h, runnable now.** It reproduces the split pins and the label-conversion counts
  on Fir's own ImageCAS-X copy (§ commands in [[Master plan - Janus 1-F]]).
- **The identity check (L-A8's form, on Fir):**
  - the 1-F scorer re-scores Janus 0's existing val-80 predictions to decisive macro **0.909 ± 0.003**, each class
    within 0.01;
  - J1F-A's loader passes its step-0 identity (F-A2).
  - Otherwise stop: nothing is read until the PM has found the cause.
- **Delta's reuse of track 1-L's Trillium J0 is not adopted.**
  - The baseline is Fir's own Janus 0 predictions, the files Janus 0's results were scored from.
  - Re-predicting Janus 0 on another cluster would add a cross-cluster difference to the comparison.

**F-A9. Reports beside the decision. None of them decides anything.**
- **The rule-ordinal reading (Atlas, Bridge):**
  - collapse F's D1–D3 to one type and OM1–OM2 to another;
  - re-number them by origin order along the parent;
  - score them against the same references.
  - This measures whether the network's own ordinals beat counting, at no extra GPU. A later model may switch naming
    on this evidence; this one may not.
- **Per class:** branch tF1 (A1c rooted where the branch meets its parent), Dice beside ImageCAS-X Table 1's
  inter-observer DSC, centreline recall and precision, and the sibling confusion matrix.
- **Readings and subsets:**
  - T's vessels (Δ = 0, asserted) and branches;
  - F's branches inside T's territories;
  - val 80 and locked 20 apart (A26: a sign reversal is reported, not acted on).
- **Ramus, D3, L-PDA and L-PLA:** n, CI and confusion.
- **`fitcheck.json`** at 150 and 300.

**F-A10. The jobs and their cost (Fir, `def-aso22`, 1 × H100, 12 cores, 280 G, 23:50).**

| Job | What | Waits on | GPU-h |
|---|---|---|---|
| **Step T** | Track 1-L's Step T copies Janus 0's checkpoint, plans, the 160 labels and aortas, and Fir's locked-100 predictions to `$KEEP` in project space. It is 1-F's insurance against the 60-day scratch purge (about 2026-12-20) too | now (Q2) | 0 |
| **F0** | Split pins and label counts on Fir (CPU) | now | 0 |
| **J1F-A** | Stage 1: 500 epochs at ≈ 192–210 s, so 2 chained jobs; preprocessing in the first; stall check at 150/300; predict the locked 100 with logits; F and T; score; `DECISION.md` | the launcher (§5, item 8), the split file (F-A1), Q1 | ≈ **29–31** (ceiling 47.7; × 1.5 if the 12-core loader sets the pace) |
| a2 | Replicate, report only | Q8 | + ≈ 29 |
| J1F-2 | Stage 2 | F-A11's counts | ≈ 15, costed when reads exist |

- **Committed by this ruling: ≈ 30 GPU-h, not yet released.** No training job starts before round 3 (#303).

**F-A11. Stage 2, adopted in principle; its details are round 2's.**
- **Loss:**
  - The CE term is the marginal over each voxel's label set (Shi et al.).
  - The Dice term counts only singleton voxels (leaf-Dice, Fidon et al. Table 2). This is Crucible's, and Delta's §11
    item 4 is the same rule. Atlas's merged-mass Dice and Foxtrot's ignore-for-Dice are round 2's to argue against
    it.
- **Label sets by source** (Delta §3's table):
  - ImageCAS-X background → {bg, S1–S3, SN, Conus, RMA}, **within a band** around the traced tree. How wide, or
    whether there is a band at all, is round 2's (§5, item 4).
  - A 4-class read's parent → {parent ∪ its children}.
  - An extended read: drawn classes are singletons; parents depend on Q3's flag.
  - Overlaps → D40's ignore, or Q4's child rule if the lead says so.
- **Heads:** new heads by parent copy from the shipped stage-1 model (S1–S3 ← LAD; SN, Conus, RMA ← RCA).
- **Provisional read thresholds.** These are the five candidates' common ground. Round 2 may replace them with
  measurements.
  - **Train a class:** ≥ 30 trainable patients (not sealed, not D35, not reserve) with the class drawn in an
    extended read, from ≥ 3 sources, **and** inter-read agreement (detection × naming) ≥ 0.6 on ≥ 10 patients with
    two extended reads (Crucible's floor).
  - **Report a class:** ≥ 20 decision patients with the class in at least one read, with n and CI.
  - **Decide on or ship a class unfolded:** ≥ 30 decision or locked cases with the class.
  - **D35 has 35 patients, so SN, Conus and RMA may never reach 30 there** (Q6).

**F-A12. One `role:swe` issue, opened after round 2 freezes its spec** (as track 1-L's #306). Not opened now, so that
round 2's changes are not built twice. Its content is §5, item 8.

**F-A13. Naming** follows the lead's answer to Q9. Until then, no Janus number is assigned.

## 2. Scorecards

Scores are out of 5: (a) reasoning, (b) evidence including spot-checked citations, (c) fit to D44, D45, the other
binding decisions and Fir, and (d) risk and cost.

| Candidate | (a) Reasoning | (b) Evidence | (c) Fit | (d) Risk/cost | Verdict |
|---|---|---|---|---|---|
| **Delta v1** | 4.5. One run, two readings (F, T) from the same weights, a clear fixed table, and F3 kept conditional. It states its independence from Crucible's identical finding. Weak: plain-argmax decode; presence agreement as the only detection gate; no recall guard; its Q1 recommendation (left PDA = LCx, no D44 name) gives up a class ImageCAS-X itself names | 4.5. Census, ordinal (359/359, 228/228, 47/47) and the label-collapse check re-read in `summary.md` and `parent_copy_selftest.log` (argmax agreement 1.0000 on **collapsed** probabilities). Locked-100 label counts measured. MiB Eq. 8–9 and Cao 2017 (PMC) correctly used. Its Shi et al. numbers (.874 → .900; .931 with exclusion) **conflict** with Atlas's and Crucible's (0.921 marginal). Unresolved; §5 item 7 | 4.5. L-A1 and L-A2 carried over exactly (no plan step, window off). Launcher refuses until Q1 is set. Pairing on Trillium's J0 is a cross-cluster detour (fixed, F-A8) | 4.5. ≈ 31 GPU-h; no new loss on the critical path | **Track 1-F's plan**, as amended |
| **Atlas v1** | 4.5. Types-then-ordinals is principled, since ImageCAS-X's ordinals are positional. Arm N is the cheapest honest baseline in the round. Weak: V2 is G3 as written; B1 against Arm N has unknown power and needs a classifier that does not exist | 5. **The hierarchical-decoding finding** (2.5 % / 3.7 % of voxels change territory under plain argmax; `head_init_check.out` re-read) is the round's most consequential check. icx14 log parsed per class. Ordinal rule scored with the pinned `tf1.py` (0.995). Says plainly it could not check Dodge 1992 and drops it | 4. Works on the 613 cases that are training under both hash readings, which is the careful choice. Dataset 730 and its own launcher are fine. G3 conflicts with track 1-L's L3 | 4. ≈ 28 GPU-h + CPU; Arm N adds a code item | Hierarchical decoding, the rule-ordinal report, the complete-flag question adopted; Arm N to round 2 |
| **Crucible v1** | 4.5. The clearest statement of why the partial labelling is in the background. Stage A with no custom loss; stage B gated on counts, never dates. The band is the right idea, stated as an opinion. Weak: a separate pilot job, where a training-case check in the main run does the same for free; no recall guard | 4.5. Fidon et al. Table 2 (leaf-Dice 62.0 vs marginal 11.1 on corpus callosum) is the only table-backed choice of Dice term. Vikse et al. and CONFIRM correctly scoped. Reads-per-class CI table reproducible from `reads_per_class.py`. Its "20 cases without an aorta" is wrong: icx4 made aortas for all 160 non-sealed val and open cases | 4. Its R1 bound is one-sided 95 %, looser than track 1-L's 2.5 %. Otherwise exact: split, `checkpoint_final` only, the L1 switch | 4. ≈ 42 GPU-h now (pilot + J1) | Leaf-Dice, the band, the agreement floor, L2 and the cross-track septal note adopted |
| **Foxtrot v1** | 4. Head surgery plus set-valued CE is a coherent single rule. The tiers are clear, and the stall check on training cases is the right instrument. Weak: the N_train threshold read from D3's **training-fit** Dice does not measure how few reads generalise; the a2-must-agree gate adds false failures | 4. Gradient check of the marginal CE against finite differences (`head_surgery_check.txt`, re-read). Honest that it read Shi's and MultiTalent's abstracts only, and that its 0.80/0.70 lines are unanchored. F0's expected printout matches the committed pins | 4.5. L-A1/L-A2 respected. F0 runs today. A set-valued loss on stage 1's critical path for 0.5 % of foreground | 3.5. ≈ 56 GPU-h (two runs) | The stall check, F0, ignore for unexplained "Other" adopted; a2 to the lead (Q8) |
| **Bridge v1** | 4. The only candidate to turn "how many reads" into an experiment (Job B). Types + namer with the parent recorded makes Q1 a lookup, not a retrain. Weak: dormant heads in stage A put the marginal loss on the critical path for classes that cannot fire; no warm-up after head growth; V2 is G3 | 4.5. Suppl. B quoted in full. Koşar et al. Table 2 (SN from RCA 79 %, Cx 20 %) used for the namer's unattached branches. Ordinal agreement 0.998 / 0.999 re-read in its census | 4. Composite well specified. Job B runs before any read exists | 3. ≈ 61 GPU-h, of which 33 for Job B | Job B and Arm N-style namer to round 2; Q4 adopted; SN evidence used |

### Spot-checks this round

- **The split.** Bridge's, Delta's and Foxtrot's split files reproduce L-A1's two pins exactly (`1350cb1f…`,
  `bbd9c687…`). Each is disjoint and holds no sealed ImageCAS-X test or quality-0 case (`trillium/sealed_test.json`).
  Atlas's 613 are a subset of the 620 with no sealed case. Crucible's locked 20 (listed in its §1) equal Delta's
  `locked_open20`. **The two tracks lock the same 100.**
- **Parent copy.**
  - Delta's self-test checks the argmax of the **collapsed** probabilities, which is hierarchical decoding in effect.
    Its launcher text and Foxtrot's ("ties pick the parent") export by plain argmax.
  - Atlas's check shows that plain argmax moves 2.5 % of voxels across territories at step 0. Hence F-A4.
- **SegQueue 0.18.0's collapse.**
  - `src/segqueue14/labels.py` l. 102 says "PDA, PLB and SN always RCA". PDA and PLB have parent `"RCA"` in the
    extended table.
  - `EXTENDED_INSTRUCTIONS` tell annotators to move "SN, conus, RMA, PDA and PLB out of RCA".
  - The same file's own four-class hints (l. 52–54) put "a left-sided PDA/PLA" in the LCx.
  - **So the module contradicts itself and D25 for left-dominant hearts.** This is Q1.
- **Aortas and baseline predictions on Fir.** [[icx4 - Results]]: Janus 0 predicted all 1000 cases and made aortas
  for the 160 non-sealed val and open cases. That covers the whole locked 100.
- **Locked-100 labels.** Delta's census opened the locked 100's reference labels, for counts only (`summary.md`'s
  second table). No model was scored. Permitted under F-A7, and noted.
- **Disagreements between censuses** (none changes the plan):
  - **Unnamed trunk branches.** Crucible counts 13 LAD cases at ≥ 5 mm. Delta counts 4 at ≥ 5 mm. Foxtrot counts 6
    at ≥ 3 mm. The lower cut-off finding fewer means the methods differ, not the data. Round 2 names one census of
    record (§5, item 10).
  - **Dominance.** Atlas reads `Descriptors.xlsx` (34 left, 21 co-dominant of 613). Bridge and Foxtrot infer it from
    the labels (46 left). The count that matters, cases with a left PDA or PLA, agrees: 58 of 613, 59 of 620.
- **Citations.**
  - Shi et al. (arXiv:2007.03868) gives **two different sets of numbers in the round** (§5, item 7). Foxtrot avoids
    the problem by quoting none.
  - The others agree across advocates and with the vault's verification notes:
    - ImageCAS-X Suppl. B and Table 1;
    - Fidon et al. Table 2;
    - MiB Eq. 8–9;
    - CPR-GCN Table 3 (vault-verified);
    - Hampe et al. 2024 (vault-verified);
    - Koşar et al.; Vikse et al.; Cao et al. 2017;
    - SCCT 2014 (record only; everyone says so).
  - **No citation was found to be unfindable.** Atlas (Dodge 1992) and Crucible (Hampe 2021, the conus figure) dropped
    what they could not open, which is the right practice.
- **Not opened:** no sealed case, no model's locked-100 score, no pool read.

## 3. Rulings on the contested points

### 3.1 Types-then-ordinals, or ordinal outputs

- **For types (Atlas, Bridge):**
  - ImageCAS-X's ordinals are positional by protocol and in fact (rule ceiling 0.995 tF1);
  - pooling D1 + D2 + D3 gives one class with positives in 98.5 % of cases;
  - a rule cannot output two D1s.
- **For ordinal outputs (Crucible, Delta, Foxtrot):**
  - on this project the network's own names beat rule renaming by 0.013 tF1 (Round 5, on four vessels);
  - a 256³ patch at 0.5 mm holds the whole tree in almost every patch (Atlas's own note), so position is visible.

**The ruling: ordinal outputs, with the rule reading reported (F-A9).** An ordinal network can be read both ways
from one run. A type network cannot be read with network ordinals. So this choice keeps the question measurable at no
GPU cost, and the next model can switch on evidence.

### 3.2 Segment-then-label, or one network

- **One network** (all five), **with the territory-constrained reading T as the pre-registered fallback** (F-A6). T
  is segment-then-label with the network as labeller, and its vessels cannot be worse than Janus 0's.
- **A graph namer on Janus 0's tree** (Atlas's Arm N) is cheap. But:
  - published naming loses much on automatic trees (Hampe et al. 2024: 0.74 vs 0.91);
  - it cannot deliver the six untraced classes.
- It goes to round 2 as a comparator to build or drop (§5, item 3), not as the plan.

### 3.3 One run, a pilot, or a replicate

| Option | Cost | Ruling |
|---|---|---|
| Crucible's pilot P1 | ≈ 10 GPU-h | Not adopted. The stall check on training cases inside J1F-A (F-A5) answers the same question ("do branches unlock?") for free, by epoch 150 |
| Foxtrot's a2 | ≈ 29 GPU-h | The lead's call (Q8). Report only, never a gate. Foxtrot's "a2 must agree" clause adds false failures to a model decision |
| Bridge's Job B | ≈ 33 GPU-h | Round 2 (§5, item 5). It answers a stage-2 question while no stage-2 read exists |

### 3.4 Left-sided PDA/PLB and the SN

This is the lead's (Q1). The judge's recommendation is the four advocates' (A), not Delta's (B).
- **(A) costs nothing in stage 1 and keeps a class ImageCAS-X names.**
- **It matches track 1-L's L-A11**, which already collapses D44 reads by side.
- **Delta's argument for (B) is weak where it counts.** "The vessel gate compares like with like" is met by F-A4's
  origin collapse. Human disagreement on left-dominant trees (Cao 2017) is a reason to report those cases, not to
  drop their name.

## 4. The first Fir jobs

Two jobs can run now: **Step T** (track 1-L's, which also covers 1-F) and **F0**. Both are 0 GPU-h. Their commands
are in [[Master plan - Janus 1-F]] §5.

J1F-A waits on:
- the launcher (F-A12);
- the split file (F-A1);
- the lead's answer to Q1.

#303 also requires at least three rounds before training jobs start.

## 5. What round 2 must settle

1. **Freeze the gate numbers before J1F-A is submitted.**
   - Keep or replace B1's 0.80 recall, its inter-observer − 0.05 line, B2's 0.85 and the "4 of 6" read rule.
   - Give each one's false-fail rate for a human-level model at the measured locked counts, by simulation from
     ImageCAS-X Table 1's agreement and the 620's piece counts (CPU).
   - V is fixed (track 1-L's H1) and is not reopened.
2. **The scorer's definitions, frozen by hash:**
   - branch-level detection;
   - naming by majority over covered centreline;
   - presence (≥ 5 mm centreline, as Delta; Foxtrot used 3 mm);
   - branch tF1 rooted at the branch's origin, one root per piece (R-PDA is in two pieces in 10 % of cases);
   - the origin collapse of F-A4 for each answer to Q1.
3. **Arm N: build it or drop it.** Atlas's segment classifier on Janus 0's tree costs CPU and code. If built, say
   whether it is a report or a gate. A gate needs the per-case branch-tF1 spread, which Arm N alone can supply on CPU.
4. **Stage 2's loss details, measured on CPU on the 620:**
   - the Dice term (leaf-Dice vs merged mass vs ignore);
   - the background band (none, 8 mm as Foxtrot, 15 mm as Crucible), with how much background each releases and
     where;
   - Bridge's leakage check as a pre-registered stage-2 gate.
5. **Reads per class: an experiment or a rule.**
   - Bridge's Job B (OM and PLB thinned to k ∈ {20, 60}, ≈ 33 GPU-h) or Delta's learning curve (≈ 45 GPU-h), its
     hold-out (inside the 620, never the locked 100), and when it runs: after J1F-A, before any extended read.
   - Or keep F-A11's provisional thresholds and say why.
6. **The scoring set for the six untraced classes,** given the lead's answer to Q6: counts only, D35 in extended mode,
   or a larger held-out pool set. What each yields at plausible prevalences.
7. **Shi et al.'s numbers.** Atlas and Crucible quote Table 3 as marginal 0.921 vs 0.874. Delta quotes .874 → .900,
   and .931 with exclusion vs .900. The advocates who cite them must reconcile them with the table and row, or drop
   the numbers. The method is not in doubt.
8. **The `role:swe` spec for `trillium/janus1f`, frozen (F-A12).**
   - It is a copy of #306's `janus1l` with:
     - the parent-copy loader option and its two identity checks (F-A2);
     - hierarchical decoding from logits (F-A4);
     - `j1f_labels.py` with the Q1 switch (F-A3);
     - the fit check (F-A5);
     - readings F and T;
     - the branch scorer (item 2);
     - `DECISION.md` (F-A6).
   - Refusals: sealed or locked case in training, plans not byte-identical, Q1 unset, an identity error, a dataset id
     in use.
   - A diff against #306 so that shared parts stay shared.
   - Fir CT and label re-fetch if `$SCRATCH` was purged.
9. **The warm-start source** if Janus 1-L is adopted before J1F-A is submitted: Janus 0 (this ruling) or 1-L, and what
   V's comparator becomes.
10. **One census of record** for the 620 (trunk twigs, dominance), so later rounds quote one number.
11. **Q8 and Q9's consequences**, once answered.

**Round 3 is the earliest round that can rule the plan converged** (#303).

## 6. Questions for the lead

None of these changes a D-number unless it says so. Each has a recommendation.

**Q1. Left-dominant PDA/PLB, and an SN from the circumflex: which D44 class, and which of the four vessels?**

ImageCAS-X names posterior branches by course and side: R-PDA, R-PLA, L-PDA, L-PLA. 58–59 of the 620 training cases
(9.5 %) have a left-sided one, where it is a median 12 % of the LCx territory (Crucible). The SN artery leaves the
circumflex in about 20 % of hearts (Koşar et al.; Vikse et al.: 22 %).

D44 lists PDA, PLB and SN under the RCA. SegQueue 0.18.0 scores PDA, PLB and SN as **"always RCA"** and tells
annotators to move them "out of RCA". D25, Janus 0's training labels and the same module's own four-class hints put
a left-sided PDA/PLA in the **LCx**. Track 1-L's L-A11 already collapses PDA/PLB **by side**.

| Option | D44 name for a left-sided PDA/PLB (and a circumflex SN) | Four-class collapse | Who recommends |
|---|---|---|---|
| **(A) Name by course, collapse by origin** | PDA / PLB (SN) | to the vessel it leaves: LCx | Atlas, Bridge, Crucible, Foxtrot; the judge |
| (B) PDA/PLB are right-sided only | none: it stays LCx | LCx | Delta |
| (C) As SegQueue 0.18.0 now | PDA / PLB (SN) | RCA always | nobody |

- **Recommended: (A).**
  - It keeps D25, D1 and track 1-L's L-A11.
  - It keeps a class ImageCAS-X and the SCCT segment model both name.
  - 1-F's four-vessel output stays comparable with Janus 0 and 1-L.
- **Under (A), SegQueue needs a small change (a `role:swe` issue after your answer):**
  - the scoring collapse of PDA, PLB and SN goes by the vessel the branch leaves, not "always RCA";
  - the extended instructions say "out of whichever vessel it leaves".
- **(C) moves LCx voxels into the RCA in every left-dominant read**, against every four-class label the project has.
- **The trained network is the same under (A) and (C); only the collapse differs.** Under (B) the training labels
  change: L-PDA/L-PLA become LCx. Stage 1 waits on this answer, because its launcher refuses until the switch is set.
- **For completeness:** branches beyond D3, S3 and OM2, and unlisted branches (AV-nodal, atrial), stay in their
  parent, as SegQueue's instructions already say (Crucible's L2).

**Q2. Run track 1-L's Step T this week, if it has not run.** Its `$KEEP` copy in Fir project space is also 1-F's
only protection against the scratch purge, about 2026-12-20. It holds:
- Janus 0's checkpoint, `plans.json` and `dataset.json`;
- the 160 labels and aortas;
- Fir's locked-100 predictions.

Without `plans.json` neither track can warm-start. **Recommended: yes.** F0 can run at the same session (0 GPU-h).

**Q3. A "this branch group is complete" flag on extended reads** (a #280 follow-up; no D-number).
- **The problem:** D38 accepts an empty class, so an empty S1 means either "no septal" or "did not look".
- **Without the flag:** an extended read can supervise only the branches drawn, and its parent stays a set.
- **With it:** a parent marked complete is a singleton.
- **Recommended: yes**, per parent group (LAD, LCx, RCA branches). Atlas, Bridge and Delta ask for this in three forms.

**Q4. D40 for a branch overlapping its own parent in an extended read.**
- **The problem:** D26 starts every class as a copy of the seed. A branch painted as S1 but not erased from the LAD
  is a child–parent overlap, which D40 turns into ignore.
- **Recommended: train it as the child,** and keep unrelated overlaps as ignore. This amends D40 for extended reads
  only (Bridge, Crucible).
- Until answered, D40 applies literally.

**Q5. Not re-annotating ImageCAS-X (D22).** Foxtrot notes that extended reads of S1–S3, SN, Conus and RMA on about
60 ImageCAS-X training cases would be the fastest route to stage 2.
- **Recommended: not now.** Revisit at the first pool wave if fewer than 30 patients have a septal read.
- Stage 1 needs nothing from it.

**Q6. Read the D35 decision patients in extended mode, with the six untraced classes traced where visible?**
- **The problem:** the six untraced classes can be scored only on extended pool reads outside training, and D35 is
  the only such set.
  - At 35 patients, septals may reach the reporting line.
  - SN, Conus and RMA probably cannot reach 30 cases.
- **Recommended: yes for D35.** Accept "counts only" for SN, Conus and RMA until more reads exist. Any growth of a
  held-out pool set is a D35 decision, and is not asked now.

**Q7. Trace septals, SN, conus and RMA beyond the TotalSegmentator seed** when an annotator uses those classes?
- **The problem:** D26's seed may not contain them. With nothing to cut down, extended reads of these classes stay
  empty.
- **Recommended: yes, as an instruction for extended reads only.** It costs annotator time only where the annotator
  chose the extended classes. This is the lead's call.

**Q8. A replicate a2 of J1F-A on Fir** (≈ 29 GPU-h, concurrent, report only, never shipped). It gives the first
between-run spread on branch classes, which any later 1-F recipe claim needs (A37).
- **Recommended: yes if Fir's allocation allows.** It is not required for the round-1 decision, which is a model
  decision.

**Q9. Naming (D34/D45).**
- **Recommended:** the model read in F-A6 (F or T) is **Janus 1-F.1**, and the adopted model is called **Janus 1-F**.
  Reports (a2, the rule reading) take no number.
- This mirrors track 1-L's Q7.

## 7. Consistency with track 1-L, and conflicts flagged

| Shared item | 1-L | 1-F | Status |
|---|---|---|---|
| Locked-100 and train-620 lists, pins, `cNNNN` hash form | L-A1 | F-A1 | **Same**, verified on three 1-F split files |
| Split file of record | `configs/janus1/split-2026-11.json` (#306) | same | Not on `dev` yet; both launchers wait on it |
| Janus 0's warm start | full strict load, plans byte-identical, window off, A17a warm-up | the same, plus parent copy of the heads | Consistent |
| Vessel guard | H1: −0.02 lower bound, −0.03 per class, L3, FP ≤ 1, one-sided 2.5 % | V: identical | Consistent. Crucible's 95 % bound and Atlas's and Bridge's G3 corrected |
| Janus 0 baseline | re-predicted on Trillium (J0) | Fir's own predictions | **Different by design.** Each track pairs on its own cluster. 1-L's identity check (L-A8) compares the two; if it fails, both tracks hear of it |
| Export threshold t\* (L-A4) | applied to 1-L | **not applied** | 1-F's vessels are compared at argmax. If 1-L ships at t\*, the composite T is Janus 0 at argmax, not 1-L at t\*. Round 2 notes it if 1-L is adopted first |
| D44 → 4 collapse of pool reads | L-A11: PDA/PLB by side | F-A4: by origin | Consistent with each other; **both conflict with SegQueue 0.18.0's "always RCA"** (Q1) |
| Septals in pool LAD reads | SegQueue's four-class instruction puts septals in the LAD; ImageCAS-X drew none | stage 2's label sets treat a 4-class LAD as {LAD, D1–D3, S1–S3} | **For #302 (Crucible's note):** a model trained on ImageCAS-X will look short in the LAD against pool reads, by the septals' length. That is an extent effect, not an error. Round 2 of 1-L should know it before pool fine-tunes |
| Dataset ids | 718 (Delta's 1-L reading) | 719 | Launchers refuse a used id |

## 8. What would change this ruling

| Observation | Then |
|---|---|
| The lead answers Q1 (B) | F-A3 relabels L-PDA/L-PLA as LCx. Nothing else changes |
| The lead answers Q1 (C) | The collapse becomes "always RCA" and V's Janus 0 reference is relabelled the same way (F-A4) |
| F0's counts differ from the PR's | Stop. Fir's copy or the converter differs; the PM finds out which |
| Step T has not run by early December | J1F-A must re-fetch Janus 0 from wherever it survives, or the track waits; the PM escalates |
| Round 2's simulation shows that a gate fails a human-level model more than 20 % of the time | That gate is loosened before submission (§5, item 1) |
| The stall check fires at epoch 150 | J1F-A may be cancelled. Round N+1 chooses among class weights, a two-network design and a graph namer |
| Janus 1-L is adopted before J1F-A is submitted | Round 2 decides the start (§5, item 9) |
