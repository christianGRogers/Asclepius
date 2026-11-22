---
tags: [plans, candidate, track-1F, round-2, janus-1F, fir, partial-labels, D44, D45, D47]
author: Crucible
track: Janus 1-F
round: 2
version: 2
updated: 2026-11-22
issue: christianGRogers/Asclepius#303
---

# Crucible v2 (Janus 1-F): freeze the scorer, the B lines and the launcher spec now. OM2's 0.80 recall line fails a human-level model too often, so recall is set per class from human agreement. Stage 2's Dice term only works in nnU-Net's per-sample form. Arm N and Job B are not run.

**Status of the inputs.**
- Delta v1 as amended (F-A1 to F-A13) is the plan in force. This candidate amends it; it does not replace it.
- D47 has answered every round-1 question with the recommendation. In particular: Q1 (A), name by course and collapse
  by origin; Q3, the "group complete" flag; Q4, a child overlapping its own parent trains as the child; Q6, D35 is
  read in extended mode; Q8, a2 runs if the allocation allows; Q9, Janus 1-F.1 / Janus 1-F.
- **Step T and F0 have not run.** Nothing here rests on their output. §12 says what each result would change.
- **Data used:** the 620 D45 training label files only, fetched by `fetch620.py`, which builds the split from id lists
  first and downloads no other label file. For the locked 100, only Delta's published counts are used (F-A7). No CT,
  no TotalSegmentator twin, no pool read, no model output.
- Code: `experiments/Crucible/j1f_r2/`. Experiments note:
  [[Crucible - Janus 1-F round 2, the B gates, the branch scorer and stage 2's Dice term on the 620]].

## 0. Thesis, and what changes in the plan in force

1. **B's recall line of 0.80 fails a human-level model on OM2 about 4 times in 10 (item 1).**
   - A human-level model disagrees with ImageCAS-X on presence as often as a second reader does (Table 1). Half of
     those disagreements are a whole branch missed. OM2 is in only 40 locked cases, so the expected misses alone put a
     reader's recall near 0.82.
   - Simulated (`sim_gates.py`), OM2 fails F-A6's lines in **41 %** of draws for a typical reader and **82 %** for a
     slightly worse one. D2 fails in 9–28 %. This is over the 20 % line the ruling's §8 set for loosening a gate.
   - **Proposed (amends F-A6 B1, B2):** the recall line is set per class from the same Table 1 agreement, minus 0.10.
     The naming line is 0.80. Presence stays at A − 0.05. Per-class false fails then fall to ≤ 11 % for a typical
     reader. Every bad model in the simulation still fails, except a model with twice the human disagreement, which
     passes the 4-of-6 rule 30 % of the time (15 % under F-A6's lines).
2. **The scorer's definitions are one 250-line module, frozen by hash, tested on the 620 (item 2).**
   `branch_score.py` scores the reference against itself at exactly 1 on every class, and three perturbations at
   exactly the numbers they must give. Presence is ≥ 5 mm. Branch tF1 is A1c, unchanged, with one root per piece.
3. **Arm N is dropped (item 3).** B's lines are anchored on human agreement, not on a comparator, so no gate needs
   Arm N. The rule-ordinal reading (F-A9) already gives the namer's half for free.
4. **Stage 2's Dice term must be computed per sample, as nnU-Net 3d_fullres already does (item 4).**
   - Fidon et al.'s leaf-Dice, as published, pushes every unannotated class to 0 on set-valued voxels (their text,
     re-read). That is ImageCAS-X's septals again, in the Dice term.
   - In nnU-Net's per-sample form (`batch_dice: false`, smooth 1e-5), the term for a class with no target on a patch
     has a gradient of at most 1e-7 per voxel once 10 voxels are predicted. It is inert, not harmful.
   - So F-A11's leaf-Dice stands, **with `batch_dice: false` pinned**. With batch Dice it would be wrong.
   - The band: @@BAND_SUMMARY@@
5. **Job B is not run; F-A11's read thresholds stay, with one change (item 5).**
6. **D35 in extended mode reports a class only if it is visible in ≥ 70 % of patients (item 6).** SN, Conus and RMA
   stay counts-only. A question for the lead: whether the sealed pool reads may also be made in extended mode, for an
   acceptance-time report.
7. **Shi et al. reconciled (item 7).** Both sets of numbers are in the paper. They answer different comparisons.
8. **The `trillium/janus1f` spec is frozen as a diff against L-A21 (item 8).** One correction to F-A2 comes with it:
   nnU-Net's fold validation must not be the locked 100 (L-A21's leak, which applies here too).
9. **The start stays Janus 0 if Janus 1-L is adopted first (item 9).** A fourth reading, T_L, takes 1-L's vessels.
10. **One census of record (item 10):** `census620.py`'s definitions, with their numbers in §10.

## 1. Item 1: the B lines, frozen, with their false-fail rates

### 1.1 The model of "human-level" (`sim_gates.py`)

- **Counts:** the locked-100 cases with each gated class, as Delta counted them (D1 98, D2 64, OM1 84, OM2 40, PDA 96,
  PLB 96). Pieces per present case are resampled from the 620 (`census620.py`, §2.3), so a two-piece PDA counts twice,
  as the scorer counts it.
- **Presence:** ImageCAS-X Table 1's inter-observer agreement A (F-A6's lines + 0.05: D1 .969, D2 .894, OM1 .944,
  OM2 .875, PDA .988, PLB .962). A human-level model disagrees on (1 − A) × 100 cases in expectation:
  - a share f is **false-absent** (every branch of that case missed);
  - the rest is false-present (only presence suffers);
  - f = 0.5 is two equally skilled readers.
- **Partial misses:** in a present case, a branch is still missed (< 50 % covered) with probability m.
- **Naming:** a detected branch is named right with probability r.
- **Correlation:** per case, m and r are Beta draws with intra-case correlation 0.2.
- 2 000 locked sets per scenario; the gates are scored exactly as F-A6 and §2 define them.

- **Why f = 0.5 drives the result.** Expected recall of a typical reader is
  (1 − 50 (1 − A) / n_c)(1 − m). For OM2 that is (1 − 6.25 / 40)(0.97) = **0.82**: at the 0.80 line before any
  sampling noise. For D2 it is 0.89, for the other four 0.94–0.96.
- **What is not known:** human naming accuracy (r) and partial misses (m) have no published number for ImageCAS-X.
  They are a grid, not a claim. CPR-GCN's D/OM F1 on expert centrelines is 0.909–0.914 (Yang et al., Table 3), so
  r = 0.90–0.93 is the range a good model reaches.

### 1.2 Results

Pass rate of each class (all of B1 and B2) and of the read rule, per scenario. **A false fail is 1 − the pass rate
for a human-level row.**

@@SIMTABLE@@

### 1.3 The frozen lines (amends F-A6 B1 and B2)

| Class | n locked | B1 recall ≥ | B1 presence agreement ≥ | B2 naming ≥ |
|---|---|---|---|---|
@@LINES@@

- **Recall line = expected human recall − 0.10**, with f = 0.5 and m = 0.03, rounded to two decimals. It is a
  number now, frozen in this table; the formula is only how it was set.
- **Presence stays at A − 0.05.** It is the only line that catches over-calling, and at n = 100 its false-fail is
  ≤ 7 % for every class.
- **Naming 0.80, not 0.85.** At r = 0.90, 0.85 fails D2 and OM2 10–15 % of the time on naming alone. A model that
  names 3 in 4 right still fails 6 classes in 7 (row "BAD naming 0.75").
- **The 4-of-6 read rule stays.** With R2's lines a typical human-level model reaches ≥ 4 of 6 in ≥ 99 % of draws.
  The rule's job is not the verdict's false fail but **which classes ship unfolded**: under F-A6's lines, OM2 would be
  folded into the LCx in 4 of 10 draws for a model as good as a reader.
- **What R2 gives up.** A model with twice the human disagreement passes ≥ 4 of 6 in 30 % of draws (15 % under F-A6's
  lines). It still fails D2 and OM2 in ≥ 94 % of draws, so the classes it ships unfolded are the common ones.
- **Ramus (24) and D3 (7) stay report-only**, as F-A6 says.

## 2. Item 2: the scorer's definitions, frozen by hash

### 2.1 The module

`experiments/Crucible/j1f_r2/branch_score.py`, sha256 `@@BSHA@@`. It is the spec for `trillium/janus1f`'s branch
scorer: the swe copy must be byte-identical or carry a test that reproduces this file's numbers on §2.2's fixtures.

| Definition | Frozen as |
|---|---|
| Reference branch | One 26-connected component of one branch class in the reference, whose centreline is ≥ 5 mm. The centreline is the **whole tree's** skeleton (A1c's `_skeletonise`) restricted to the piece. A shorter piece is neither detected nor missed |
| Centreline length | Sum of 26-neighbour edge lengths between skeleton voxels, in mm |
| Presence | A class's centreline totals ≥ 5 mm. Reference: as above. Prediction: the skeleton of the predicted foreground, labelled by predicted class |
| Detection | ≥ 50 % of the branch's centreline voxels lie within 1.5 mm (D3) of predicted foreground of **any** class. Recall = Σ detected / Σ branches over cases |
| Naming | Each covered centreline voxel takes the class of its nearest predicted foreground voxel. A detected branch is named right when **strictly more than half** of its covered voxels take its reference class. Accuracy = Σ named right / Σ detected |
| Branch tF1 | A1c's `tree_f1` (sha256 `24441cf8…5254`, unchanged) on class c alone, with **one root per reference piece**: the piece's centreline voxel nearest the rest of the reference tree |
| Four-class collapse (D47 Q1 (A)) | D1–D3 → LAD; OM1, OM2, Ramus → LCx; each 26-connected PDA/PLB component → whichever of LCx or RCA has more voxels in its one-voxel ring (ties, no contact → RCA). `rca_always=True` is Q1 (C), kept for the record only |
| Decoding | Hierarchical (F-A4): territory by summed probability, then class within. Reading T: Janus 0's argmax territory |
| Ignore (255) | Background in every definition |

### 2.2 Tests on the 620 (`census620.py`, first @@NSELF@@ cases for the slow tF1)

@@SELFTEST@@

### 2.3 Presence at 5 mm, not 3 mm

@@PIECES@@

## 3. Item 3: Arm N is dropped

- **No gate needs it.** §1's lines are anchored on ImageCAS-X's human agreement. They need no comparator, so they
  need no per-case spread of a comparator.
- **Its naming half is already in the plan at no cost.** F-A9's rule-ordinal reading renumbers F's own D and OM
  branches by origin order. It is a namer on a tree that is not Janus 0's, but the question it answers ("do the
  network's ordinals beat counting?") is the one Arm N would answer.
- **What Arm N adds alone is a namer on Janus 0's tree.** That is code on Fir (a segment classifier, its training
  and its scorer) for a reading that cannot deliver S1–S3, SN, Conus or RMA. Published naming on automatic trees loses
  much (Hampe et al. 2024: 0.74 vs 0.91, in the round-1 ruling).
- **It stays where the ruling put it:** one of the three options if B fails (F-A6's last verdict row). Built then, it
  is built for a known failure.

## 4. Item 4: stage 2's loss, measured on the 620

### 4.1 The Dice term

**The literature, re-read.**
- Fidon et al. (arXiv:2107.03846 v2, Eq. 4) define leaf-Dice with sums over all voxels. Their text says that for an
  unannotated class "the term ∑ p_{i,c} in the denominator pushes p_{i,c} towards 0 for all the voxels", including
  the set-valued ones, and that leaf-Dice "is not equivalent to just masking out the unannotated voxels".
- **For 1-F that is the background problem again.** On an ImageCAS-X patch, S1–S3, SN, Conus and RMA are never a
  singleton. A Dice term pooled over the batch would push them to 0 on every ImageCAS-X voxel, the band included.
- Table 2 (verbatim): marginal Dice CC 11.1, DGM 37.8, BS 39.4; leaf-Dice 62.0, 71.4, 61.5 (DSC %). Leaf-Dice still won
  there, because each of their classes was annotated somewhere in most batches.

**nnU-Net's form makes the push inert.** Janus 0's plans set `batch_dice: false` for 3d_fullres
(`nnUNetResEncUNetPlans_60G_iso05.json`, re-read in `trillium-results/icx14`), with smooth 1e-5. On a patch where a
class has no target voxel, its Dice is smooth / (Σp + smooth), whose gradient per voxel is smooth / (Σp + smooth)²
(`dice_toy.py grad_check`):

| Predicted mass of the class on the patch (voxels) | 0.01 | 0.1 | 1 | 10 | 100 |
|---|---|---|---|---|---|
| Gradient per voxel, no target | 0.10 | 1e-3 | 1e-5 | 1e-7 | 1e-9 |

- With a 50-voxel target half covered, the gradient per covered voxel is 0.018. So the no-target term is 10⁵ times
  weaker once 10 voxels are predicted. It only holds a class already at zero there.
- **Ruling proposed:** stage 2 keeps leaf-Dice (F-A11), computed **per sample** with smooth 1e-5, and the launcher
  refuses `batch_dice: true`.

**The toy (`dice_toy.py`).** @@TOY@@

### 4.2 The background band

@@BAND@@

### 4.3 Bridge's leakage check, pre-registered as a stage-2 gate

- **L1, on the 20 fit-check training cases at every fit check:** the share of each untraced class's predicted voxels
  that lie inside ImageCAS-X's traced lumen. Reported; above 0.05 at the last check writes `LEAK` (as F-A5's `STALL`).
- **L2, on the locked 100, inside stage 2's own one look:** that share ≤ **0.02** per class, and the traced classes
  lose ≤ 0.005 of their centreline to untraced classes. Failing L2 means the class ships folded into its parent.
- **L3, outside the band:** the share of each untraced class's predicted voxels beyond the band on ImageCAS-X cases.
  Reported only; a high share says the band is too narrow, not that the model is wrong.
- These are measured on ImageCAS-X, where the true answer for the traced lumen is known: an untraced class must take
  no traced voxel. They cannot see a septal painted on a vein; D35's extended reads can (§6).

## 5. Item 5: reads per class: a rule, not Job B

- **Job B answers a different question.** It thins OM and PLB, which are traced, large, ordinal-named classes whose
  parent copy already starts at the right territory. Septals, SN, conus and RMA are thinner (§1 of Crucible v1: the
  thinnest traced branches already sit at 0.61–0.67 mm median radius), unnamed in ImageCAS-X, and learned against a
  set-valued background. How fast OM learns from 20 cases is not how fast S1 does.
- **It costs one J1F-A (≈ 33 GPU-h)** before any extended read exists, for a threshold that stage 2's own counts gate
  anyway.
- **Keep F-A11's thresholds, with one change:** the inter-read floor (detection × naming ≥ 0.6 on ≥ 10 patients with
  two extended reads) is measured **with §2's scorer**, reader against reader, so the floor and the model's score use
  one definition.
- **When the rule would be revisited:** if, at the first wave, a class has 15–29 trainable patients and the PM wants
  to train it early, then a thinning job on that class's own reads (inside the trainable pool, never D35 or the locked
  100) is the experiment. It is costed then.

## 6. Item 6: the scoring set for the six untraced classes

D47 Q6: the D35 patients are read in extended mode. `untraced_yield.py`: patients with the class in ≥ 1 of two reads,
= N × visible prevalence × (1 − (1 − s)²), s = the chance one extended read draws it.

| Set | Visible in 50 % (s 0.6 / 0.9) | 70 % | 90 % | Half-width at 0.8, best case |
|---|---|---|---|---|
| D35 (35 patients) | 15 / 17 | 21 / 24 | 27 / 31 | ± 0.14 |
| 70 patients (hypothetical; a D35 decision) | 29 / 35 | 41 / 49 | 53 / 62 | ± 0.10 |
| D35 + the 150 sealed (acceptance only) | 78 / 92 | 109 / 128 | 140 / 165 | ± 0.06 |

- **D35 reaches F-A11's report line (≥ 20) only for a class visible in ≥ 70 % of patients, and its decide line (≥ 30)
  only at 90 % with good readers.** That is plausibly S1, and not SN, Conus or RMA. None of these prevalences is
  sourced for CCTA visibility: the grid is the claim, not the numbers.
- **So:** S1–S3 are reported from D35 with n and CI when they reach 20; **SN, Conus and RMA are counts only** (D47
  Q6's own wording). No untraced class is decided on D35.
- **Question for the lead (no D-number changes):** may the 150 sealed pool patients' reads be made in extended mode?
  It does not change D27's single look or what it decides. It is the only set that can ever report SN, Conus and RMA,
  at acceptance. Not asked as a recommendation to grow D35 (§5 item 6 of the ruling leaves that to D35).

## 7. Item 7: Shi et al.'s numbers, reconciled

Read at source (arXiv:2007.03868 v1, the only version; PDF text, §4, "The combined effect of data pooling and using
marginal loss" and "The effect of exclusion loss"):
- "It brings a 4.7% increases (.921 vs .874) in average dice coefficient for test images when compared with Ψ^mc_F,
  which is trained on F alone". So **marginal loss, joint training (Ψ^mc_All) 0.921 vs fully labelled only 0.874**.
- "… the mean dice coefficient is increased from .874 to .900" compares **Ψ^mc_F+Pi**, networks trained on F plus
  **one** partial set each, with ordinary losses, against Ψ^mc_F. That is pooling without the marginal loss.
- "it brings a 3.1% increase (.931 vs .900)": **marginal + exclusion, joint (0.931) vs that pooling baseline (0.900)**.
- Table 3, block Ψ^mc_F, row rCE+rDC, column All = .874 is verbatim. The Ψ^mc_All rows (.921, .931) were read in the
  text above, not in the table body, which the PDF text extraction garbles.
- **So both advocates quoted real numbers.** Atlas and Crucible quoted the marginal loss's own effect (0.874 → 0.921;
  + exclusion 0.931). Delta's 0.874 → 0.900 is the effect of pooling without the marginal loss, and its 0.931 vs 0.900
  is marginal + exclusion against that baseline. The method's claim is the first pair; this plan quotes it that way.

## 8. Item 8: the `role:swe` spec for `trillium/janus1f`, frozen as a diff against L-A21

**Shared with #306 / L-A21, unchanged:** the install (editable segtrain, sealed paths printed); Step T's plans copied
first, `move_plans_between_datasets` then `preprocess` only, Janus 0's fingerprint placed, no `plan_experiment` and no
`extract_fingerprint`; the plans check without `dataset_name` and `image_reader_writer` (not sha256 equality); the
split file and its pins (F-A1 = L-A1); `SEGTRAIN_CT_WINDOW=off`, `SEGTRAIN_SAVE_EVERY=10`,
`SEGTRAIN_SAVE_PROBABILITIES=0`, `SEGTRAIN_MAX_SECONDS` = walltime − 30 min, `nnUNet_compile` as Janus 0's;
`SEGTRAIN_ITERATIONS`/`SEGTRAIN_EPOCHS` unset; `checkpoint_best` never read; **`perform_actual_validation` a no-op**;
the modes `check`, `prepare`, `train`, `predict`, `collect`, `status`; the looks ledger; self-tests 1–6 of L-A21.

**Different in 1-F:**

| Item | `janus1l` (L-A21) | `janus1f` |
|---|---|---|
| Cluster header | Trillium | Fir: `--gpus-per-node=h100:1 --cpus-per-task=12 --mem=280G --time=23:50:00 --account=def-aso22` |
| Dataset | 718, `territory.to_four` | **719**, `branch_score.to_1f` (Delta's map, `--left-pda name` per D47 Q1 (A), "Other" touching neither side → 255) and a refusal if collapse4(1-F) ≠ `to_four` on any voxel outside "Other" and 255 |
| `splits_final.json` val | 10 lowest-id cases of the tuning 60 | **the 20 fit-check training cases** (F-A5's sha256 list). Corrects F-A2, which made the locked 100 fold 0's validation: with final validation off and val = 20 training cases, no pseudo-Dice and no automatic prediction ever touches the locked 100 (L-A21's leak) |
| Trainer | `nnUNetTrainer_janus1l` (finetune + no final validation) | `nnUNetTrainer_janus1f`: the same, plus the parent-copy head build (F-A2) and its two identity checks at step 0, and the fit check at epochs 150 and 300 with hierarchical decoding (F-A5) |
| Loss | DiceCE, ignore 255 | the same; **`batch_dice: false` asserted** (§4.1) |
| `predict` | folds 0, 1 + E | fold 0 (a1) and, if run, fold 1 (a2); `--save_probabilities --disable_tta`; **probabilities kept**, because F and T decode from them (F-A4). nnU-Net's own label export is not used |
| Baseline | Trillium J0 | Fir's own Janus 0 locked-100 predictions (F-A8), from Step T's `$KEEP` copy; refused if their sha256 list differs from Step T's posted list |
| `collect` | H1–H3 | V (= H1, with collapse4 by origin) on F; B on the reading that ships (§1.3's lines); F-A9's reports; writes `DECISION.md`. Refuses a second run |
| Readings | E | F, T, and T_L only if §9's condition holds |
| Self-tests added | — | 7. Parent copy: territory sums equal Janus 0's within 1e-5 and the hierarchical decode equals Janus 0's argmax on a random batch; a plain-argmax decode must **fail** this test (Atlas's 2.5 %). 8. `to_1f`: the counts of §10 on a 3-case fixture; Q1 unset refuses. 9. The scorer: §2.2's self-score and perturbation numbers on 3 fixtures. 10. The gate: OM2 recall 0.71 fails, 0.73 passes; a model calling every class present fails D2/OM1/OM2 presence. 11. `batch_dice: true` refuses |
| Refusals added | — | a locked or sealed case in training; plans not equal (as L-A21); Q1 switch unset; an identity error; dataset id in use; the Janus 0 baseline's checksums missing; `batch_dice: true` |
| Re-fetch | — | if `$SCRATCH` was purged: CT and labels re-fetched from Girder/Zenodo by `prepare`, and the checksums of Step T's `$KEEP` used for Janus 0 |

The issue is opened after the round that rules the plan converged (F-A12), not now.

## 9. Item 9: the warm start if Janus 1-L is adopted first

- **The start stays Janus 0.** The 1-L candidate is E, a two-network ensemble (L-A14), with an export threshold t\*
  (L-A15). Neither is one checkpoint that `finetune_load` can load with a strict, bitwise check. Warm-starting from one
  member of E would start 1-F from a network that is not the adopted model.
- **V's comparator stays Janus 0 at argmax.** V asks whether 1-F's own training kept the vessels it started from. That
  is a question about this run, and its answer does not depend on 1-L.
- **If 1-L is adopted before `collect` runs, one reading is added: T_L** = 1-L's shipped four-class voxels (at t\*, as
  it ships), named by 1-F's within-territory argmax. Its vessels are 1-L's by construction.
  - The verdict table gains one rule, fixed now: if V passes and B passes on F, and 1-L is adopted, **T_L ships in
    F's place unless F's collapsed vessels are non-inferior to 1-L's on the locked 100 by V's own rule.** B is re-read
    on T_L. So the project never ships a 1-F whose vessels are worse than its best four-class model.
  - 1-L's locked-100 predictions are Trillium files, scored on Fir as files. That is not a re-prediction, so F-A8's
    objection does not apply.
  - This is a second look at the locked 100 for track 1-F only in the sense that 1-L's files are scored: its numbers
    are already 1-L's own look, and nothing in 1-F's recipe is chosen from them.

## 10. Item 10: the census of record

`census620.py` (and `dominance620.py`) on the 620. Definitions are in the scripts' docstrings; the numbers:

@@CENSUS@@

## 11. Item 11: the consequences of D47

| Answer | What it changes here |
|---|---|
| Q1 (A) | `to_1f` uses `--left-pda name`; collapse4 by origin (§2.1). SegQueue's collapse and instruction change by a `role:swe` issue (not this PR). In stage 2, an SN off the circumflex collapses to LCx |
| Q2 | Step T is the lead's (§12) |
| Q3 | In stage 2, a parent group marked complete is a singleton; unmarked, the parent is {parent ∪ its children} (F-A11) |
| Q4 | In stage 2's extended reads, a branch overlapping its own parent trains as the branch; other overlaps stay 255 |
| Q5 | Nothing now; the revisit is at the first pool wave |
| Q6 | §6 |
| Q7 | Stage 2's extended reads of S1–S3, SN, Conus and RMA may extend beyond the seed, so the band (§4.2) must not be read from the seed |
| Q8 | a2 is fold 1 of the same launcher, concurrent, same recipe, its own fit check. It is reported (between-run spread per branch class, A37) and never read for the verdict: if a1 writes `STALL` and a2 does not, a1 is still the decision and the PM may cancel both |
| Q9 | The reading that ships (F, T or T_L) is **Janus 1-F.1**; once adopted, **Janus 1-F**. a2 and the rule-ordinal reading take no number |

## 12. Step T and F0: what each result would change

| Result | Then |
|---|---|
| **F0's split pins** equal `1350cb1f…` and `bbd9c687…` | Nothing. They are reproduced here from Zenodo's file lists (`fetch620.py`) |
| F0's pins differ | Stop: Fir's ImageCAS-X file lists differ from Zenodo's. Nothing here changes; the launcher waits |
| **F0's label counts** equal Foxtrot's expected line | Nothing. @@F0@@ |
| F0's counts differ | Stop (ruling §8). If only `other_amb` differs, F-A3's 255 rule moves by those pieces; this plan's numbers do not |
| **Step T** posts the three checksum lines and 160 / 160 / 100 | The launcher's baseline refusal (§8) has its reference. Nothing else |
| Step T finds Janus 0 trained with class-weighted CE (L-A20) | Stop, as track 1-L. 1-F's recipe would need the same weights; round 3 decides |
| Step T has not run by early December | As the ruling: J1F-A must re-fetch Janus 0 or wait. §9's T_L does not help: it needs Janus 0 too, for F |
| Step T's `plans.json` shows `batch_dice: true` for 3d_fullres | §4.1's conclusion flips: stage 2 needs leaf-Dice with a per-class skip on patches where the class has no singleton, and the self-test 11 inverts |

## 13. What would change this plan

| Observation | Then |
|---|---|
| A measured human naming accuracy for ImageCAS-X (e.g. from the D35 double reads with §2's scorer) below 0.85 | B2's line moves down with it, before J1F-A's look only |
| The first extended reads show the untraced classes' voxels beyond the band at more than 10 % | The band widens to their 95th percentile (§4.2) before stage 2 trains |
| L1 writes `LEAK` | Stage 2 is cancelled at the PM's call; round N+1 adds Shi's exclusion term against ImageCAS-X's traced lumen |
| 1-L adopted before J1F-A's `collect` | T_L is added (§9) |


