---
tags: [plans, judgement, track-1-F, round2, janus1-f, D44, D45, D47, fir, locked100, partial-labels, gates, scorer, swe-spec]
track: 1-F
round: 2
updated: 2026-11-23
issue: christianGRogers/Asclepius#303
---

# Janus 1-F, Round 2 ruling

This is the second round of track 1-F (D45, #303): the training plan for **Janus 1-F**, run by the lead on **Fir**.
The five round-2 candidates are in `Candidates/Janus 1-F/`:
- [[Candidates/Janus 1-F/Atlas v2|Atlas v2]];
- [[Candidates/Janus 1-F/Bridge v2|Bridge v2]];
- [[Candidates/Janus 1-F/Crucible v2|Crucible v2]];
- [[Candidates/Janus 1-F/Delta v2|Delta v2]] (the holder);
- [[Candidates/Janus 1-F/Foxtrot v2|Foxtrot v2]].

Each candidate's Experiments note and its code under `experiments/<advocate>/j1f_r2/` were read with it.

**Binding inputs:**
- D45 to D49, D47 above all (the lead accepted every round-1 recommendation: Q1 (A), Q3, Q4, Q6, Q7, Q8, Q9);
- [[Janus 1-F Round 1]] (F-A1 to F-A13) and its §5;
- [[Janus 1-L Round 2]] (L-A13 to L-A25), where the tracks share mechanics.

**What the judge ran.** Every number this ruling leans on was re-run on CPU in this container (§2, spot-checks). One
new script, `experiments/Judge/j1f_r2/cross_gates.py`, scores each advocate's proposed gate lines under two other
advocates' human models.
- **Data read:** the committed census files of the 620 only, and the locked 100's published label **counts**
  (98 / 64 / 84 / 40 / 96 / 96).
- **Not read:** no label volume, no CT, no sealed or quality-0 case, no TotalSegmentator twin, and no model output.
- Nothing ran on Fir, SciNet or Trillium.

**This round does not rule the plan converged.** Round 3 is the earliest round that can (#303).

## 0. Where the five agree

Nobody needs to argue these points again in round 3.

- **The B gates as ruled fail a human-level model on OM2, above the 20 % line of the round-1 ruling's §8.**
  - All five simulated a second ImageCAS-X analyst from Table 1, each with a different model of the human reader.
  - All five find OM2 failing a human reader 18–95 % of the time, depending on the model. So the round-1 trigger fires
    and the gate is loosened before submission.
  - Atlas and Bridge also find OM1 failing about half the time on naming.
  - **"4 of 6" stays** as the read rule. V is not reopened.
- **The scorer's definitions:**
  - presence at **5 mm** of centreline (3 mm and 5 mm differ by at most one or two training cases per class);
  - detection: ≥ 50 % of a reference branch's centreline within 1.5 mm of predicted vessel of any class;
  - naming by majority over the covered centreline, with ties wrong (four of five say so explicitly);
  - one tF1 root per reference piece (R-PDA is in two pieces in 10.7 % of the 620);
  - only D47's answer (A) is built. `JANUS1F_LEFT_PDA` and the (B)/(C) branches are deleted.
- **On ImageCAS-X's own labels the contact collapse equals the origin labels.**
  - SegQueue's `assign_contact_branches` gives ImageCAS-X's own side on all 1,296 PDA/PLB components of the 620, with
    0 fallbacks. Delta and Bridge each found this independently. Atlas, Crucible and Foxtrot found the equivalent
    "0 voxels off D25 outside 'Other'" with their own collapses.
  - So V compares like with like under D47 (A), and no left-dominance list is needed.
- **Arm N is dropped.** All five drop it. It comes back only as a round-N+1 candidate if B fails.
- **Stage 2's Dice term is leaf-Dice.**
  - Atlas withdraws merged mass, and Foxtrot withdraws ignore-for-Dice.
  - Fidon et al. Table 2 is the table behind it.
  - Crucible's and Foxtrot's CPU checks say why: merged mass gives the septal no signal; ignore-for-Dice cannot see an
    intruder.
- **The stage-2 band should be territory-specific, not one ring around the tree.** Four of five say so; Delta proposes
  it per host.
- **Shi et al. are reconciled.**
  - The marginal-loss row of record is **0.921 vs 0.874** (Table 3, "All"); with exclusion it is 0.931.
  - Delta's ".874 → .900" is the paper's F + P_i pairwise-pooling row, not the marginal loss. Delta withdraws it.
- **The warm start stays Janus 0, whatever Janus 1-L does.**
  - 1-L's candidate is the two-network ensemble E (L-A14), exported at t_C, on Trillium. There is no single checkpoint
    to parent-copy from.
  - A 1-L reading is a report only.
- **D35 (35 patients, extended mode) can report S1 at most.** SN, Conus and RMA stay counts only. No untraced class is
  decided on D35.
- **Step T and F0 have not run.** Nothing in round 2 rests on them.

## 1. Ruling: Delta v2 is track 1-F's plan, as amended (F-A14 to F-A26)

**[[Candidates/Janus 1-F/Delta v2|Delta v2]] is the plan in force for track 1-F**, on top of F-A1 to F-A13 and D47.
It wins on three points.
1. **It answers all eleven items with code that runs.**
   - Its scorer imports the two pinned modules (A1c `tf1.py`, SegQueue's `labels.py`) instead of re-implementing them,
     and passes 31 self-tests.
   - Its contact-collapse check ran SegQueue's own function on every non-sealed map.
2. **It is the only candidate that measures the band and the branch-to-trunk distances on the same cases** (§4.2:
   15 mm covers 75–92 % of a D/OM-sized branch in the median case).
3. **Its §9 settles the warm-start question for the right reason:** a parent copy needs one set of weights, and V's
   comparator must not move mid-plan.

**Its weak points, fixed by amendment:**
- **Its gate lines (0.75 / 0.80, flat) still fail a human-level OM2 56–78 %** under Atlas's and Bridge's human models
  (§2; F-A15 adopts Atlas's lines).
- **Its spec keeps the locked 100 as fold 0's validation set.** nnU-Net then computes a pseudo-Dice on the locked
  100 at every epoch. Track 1-L closed this hole in L-A21 (F-A20).
- **Its spec asserts the plans' sha256 equals Janus 0's.** `move_plans_between_datasets` rewrites two fields, so that
  check always fails (L-A21; F-A20).
- **Reading T, as Delta writes it, can never name a left-sided posterior branch.** Under D47 that branch lies in Janus
  0's LCx territory, while PDA/PLB sit in the RCA decode group (Foxtrot; F-A19).
- **Job B as an integration test costs ≈ 22 GPU-h** for a question that transfers weakly to the untraced classes
  (F-A23).

**What the others contribute:**
- **Atlas v2:**
  - **the gate lines of record (F-A15).** They are the only set whose per-class false-fail for a human-level model
    stays ≤ 0.17 under every human model tried. Under its own nine scenarios it is ≤ 0.08. It still rejects a model
    with twice a human's errors 94 % of the time (§2, the cross-check);
  - the scorer definitions with per-piece counting (F-A16);
  - val = the 20 fit-check cases (F-A20);
  - the observation that a one-voxel erosion removes whole D1s and PDAs, which ties 1-F's B1 to track 1-L's width
    finding (F-A22 reports).
- **Bridge v2:**
  - **human misnaming estimated from Table 1's DSC spread** (a co-present DSC near 0 means the analysts named
    different branches). This is the finding that exposed OM1's 0.85 naming line;
  - SegQueue's function as the one collapse (F-A17);
  - the territory-specific label sets (F-A21);
  - Shi et al. row by row, including mCE alone 0.873 and mDC alone 0.876;
  - the honest withdrawal of its v1 claim about Shi's abstract.
- **Crucible v2:**
  - **`batch_dice: false` pinned for stage 2's leaf-Dice**, with the per-voxel gradient bound and the toy (F-A21);
  - the most specific band table (F-A21);
  - K1, a leakage flag on the fit-check training cases at no look cost (F-A24);
  - the inter-read floor measured with the scorer of record (F-A23);
  - **the sealed-pool question (Q-F2-1).**
- **Foxtrot v2:**
  - **reading T's LCx territory must admit PDA and PLB** (F-A19);
  - the per-class text of F-A4 sent 4,879 left-PDA voxels in 5 cases to the RCA. This is fixed by SegQueue's chain
    rule, which the plan now imports (F-A17);
  - the three L-A20/L-A21 corrections carried into 1-F (F-A20);
  - the twig census reconciled: Crucible's higher count is the 9 cases with no left main (F-A25);
  - F0-r2 (F-A26);
  - the band cap at 25 mm (F-A21);
  - the 1.5× read-threshold rule (F-A23).

### Binding amendments (track 1-F, Round 2)

F-A1 to F-A13 stay in force except where these change them. They override the candidate text where they conflict.

**F-A14. The plan in force.** Delta v2 as amended here, on top of F-A1 to F-A13 and D47.

**F-A15. B's lines, frozen (amends F-A6's B1 and B2; settles §5 item 1).**

| Class | B1 recall ≥ | B1 presence agreement ≥ | B2 naming ≥ |
|---|---|---|---|
| D1 | 0.81 | 0.94 | 0.83 |
| D2 | 0.76 | 0.84 | 0.86 |
| OM1 | 0.75 | 0.90 | 0.78 |
| OM2 | 0.60 | 0.81 | 0.78 |
| PDA | 0.89 | 0.97 | 0.90 |
| PLB | 0.89 | 0.94 | 0.92 |

- **How they were set (Atlas's rule):** each line is the 5th percentile of a human-level model's statistic, in the
  worst of nine scenarios for that statistic, rounded down to 0.01. Its source is `experiments/Atlas/j1f_r2/gate_sim.py`,
  `proposed_lines`, re-run byte-identically (§2).
- **"≥ 4 of 6" is unchanged. V is unchanged.**
- **The lines are written into `configs/janus1/j1f_gates.json`** (Bridge's form). The launcher reads that file and
  refuses one whose sha256 differs from the value posted on #303.
- **These lines are stricter than F-A6's for D1, PDA and PLB.** A human leaves room there, and tightening before
  submission is allowed (F-A6).
- **OM2's recall line of 0.60 is low on purpose.**
  - A second analyst omits OM2 in about 18 % of the cases where the first drew it.
  - With n = 40, no line near 0.80 can be passed by a human.
  - OM2 still separates a model 0.20 worse in omission most of the time.
  - A failing OM2 folds into the LCx and is listed.
- **What no line can do at n = 100:** a model with 10 % extra misnaming is rejected only 58 % of the time, under F-A6's
  lines and these alike. That is a limit of the decision set and is written into `DECISION.md`.

**F-A16. The scorer of record (settles §5 item 2).**
- **Definitions:** Atlas's `j1f_scorer.py` (sha256 `2da3cb1a…886c`), as its §2.2 table states them:
  - per-piece recall and naming, over 26-components of ≥ 20 voxels;
  - the centreline is the whole reference tree's skeleton, restricted to the piece;
  - presence at 5 mm;
  - naming by strict majority, with ties wrong;
  - one tF1 root per piece.
- **One change: its collapse is replaced by an import of `segqueue14.labels.assign_contact_branches`** (F-A17).
- **Why Atlas's file and not Delta's.** F-A15's lines were simulated per piece. Delta's scorer counts a branch once per
  case, all pieces together. The scorer and the lines must count the same thing.
- **Delta's 31 checks (`test_branch_score.py`) and Atlas's self-test both become the scorer's tests**, on training
  fixtures only.
- **The amended file's sha256 does not exist yet.** Round 3 posts it (§5, item 1). Until it is posted, `collect`
  cannot run.

**F-A17. One collapse: SegQueue's (amends F-A4).**
- **The four-class collapse of any 1-F map** (prediction or reference) is `collapse_to_four` /
  `assign_contact_branches` from `src/segqueue14/labels.py`:
  - D1–D3 → LAD;
  - OM1, OM2, Ramus → LCx;
  - each PDA/PLB/SN component → the vessel with the most face contact;
  - a component reached only through another component takes that one's vessel (the chain rule);
  - RCA on a tie or no contact, counted.
- **It is pinned by the sha256 of `labels.py`** (`5f69b5be…0a4b` at this ruling's base).
- **F-A4's per-class "touches most" is withdrawn.** Taken per class it sends left PDAs that touch only their PLA to
  the RCA (Foxtrot, §2.4). SegQueue's chain rule does not, and it is the same code pool reads are collapsed with.
- **Atlas's one-voxel ring, Crucible's ring and Foxtrot's `posterior_side` are not used.**
- **`collect` reports the fallback count for F and T.** It is 0 on every reference map.

**F-A18. Labels (amends F-A3).**
- **The converter is Delta's `j1f_labels.py`, with two changes:**
  - D47 (A) hard-wired: L-PDA/L-PLA → PDA/PLB, and the switch removed;
  - F-A3's ignore rule added.
- **Expected counts on the 620:** D3 47, D4 → LAD 2, LCx-side "Other" → LCx 20, nearest 1, ignore 8. Crucible,
  Foxtrot, Atlas and Delta's own v1 counts all give these numbers.
- **The collapse check:** collapse4(1-F) equals `territory.to_four` on every voxel outside "Other" and 255.

**F-A19. Reading T under D47 (amends F-A6's T and F-A4).**
- **T's territory is Janus 0's argmax.** Inside the LCx territory, T's argmax runs over **{LCx, OM1, OM2, Ramus, PDA,
  PLB}**. Inside the RCA territory, it runs over {RCA, PDA, PLB}. Otherwise T could never name a left-sided posterior
  branch (Foxtrot).
- **T's four-class output is Janus 0's map itself**, asserted bit-equal. It is not a collapse of T's names.
- **F keeps F-A4's decode groups unchanged.** The step-0 identity needs PDA/PLB in the RCA group, since they are
  parent-copied from the RCA row. F's vessels are scored after F-A17's collapse.

**F-A20. Track 1-L's round-2 corrections, carried into 1-F (amends F-A2).**
- **Validation:**
  - `splits_final.json` has two identical entries: train = the 620, **val = the 20 fit-check cases** (F-A5's sha256
    list, inside the 620).
  - `perform_actual_validation` is a no-op.
  - **F-A2's "fold-0 validation is the locked 100" is withdrawn.** Under it, nnU-Net computes a per-epoch pseudo-Dice
    on the locked 100, and its final validation writes plain-argmax predictions of them. That breaks F-A7 (Atlas,
    Crucible, Foxtrot; L-A21's leak).
- **Plans:** L-A21's plans check replaces "byte-identical": the plans equal Janus 0's once `dataset_name` and
  `image_reader_writer` are removed. A changed percentile refuses.
- **Fingerprint:** Step T's copy of Janus 0's `dataset_fingerprint.json` goes into Dataset 719's preprocessed folder.
  No `extract_fingerprint`.
- **The rest, as L-A21:**
  - editable segtrain install;
  - `SEGTRAIN_SAVE_EVERY=10`;
  - `SEGTRAIN_MAX_SECONDS` = walltime − 30 min;
  - `nnUNet_compile` as Janus 0's;
  - `SEGTRAIN_ITERATIONS`/`SEGTRAIN_EPOCHS` unset;
  - `checkpoint_best` never read;
  - the looks ledger.
- **L3 reads the scorer's `recall`** (L-A17).
- **Prediction (settles Atlas vs the others):**
  - the locked 100 are predicted in chunks of 10, with `--save_probabilities --disable_tta`;
  - `decode` writes F and T and then **deletes that chunk's npz and nnU-Net's own argmax export** before the next
    chunk;
  - `collect` reads only maps that carry `decode`'s marker.
  - Atlas's in-memory decoding is an acceptable alternative for the swe, if it passes the same decode self-test.

**F-A21. Stage 2's loss and label sets (amends F-A11; settles §5 item 4).**
- **Loss:**
  - marginal CE plus **leaf-Dice per sample** (Delta §4.1's definition);
  - smooth 1e-5;
  - **`batch_dice: false` asserted.** The launcher refuses `true`. If Step T shows Janus 0's 3d_fullres plans with
    `batch_dice: true` (icx14's plans have `false`; re-read), Crucible's `leaf_skip` replaces it.
- **Label sets for ImageCAS-X background** (Crucible's table, per host):

| ImageCAS-X background within the band of… | Label set |
|---|---|
| the LAD and D1–D3 | {bg, S1, S2, S3} |
| the RCA (whole) | {bg, RMA} |
| the proximal RCA (30 mm from its ostium) | {bg, RMA, SN, Conus} |
| the proximal LCx (20 mm from the LM) | {bg, SN} |
| anywhere else | {bg} |

- **Traced-class voxels are never in a set** (Foxtrot).
- **D3 is not in the LAD set** (Crucible proposed it). D3 is a traced stage-1 class, and putting it in ImageCAS-X's
  background set would change what stage 1 already learned.
- **Width:**
  - **15 mm, provisional.**
  - Before J1F-2 is submitted, it is **re-set per class group** to the 95th percentile of the distance from its host of
    the voxels drawn in the trainable extended reads (≥ 10 reads per group), **clamped to [8, 25] mm**.
  - It is computed on CPU and posted with its sha256.
  - 8 mm is not the default. It holds 37–45 % of a D/OM-sized branch in the median case (Delta), and under half of a
    20 mm synthetic septal (Foxtrot).
- **Extended reads:**
  - D47 Q3: a complete group's parent is a singleton; an unmarked group's parent is {parent ∪ children};
  - D47 Q4: a child over its own parent is the child; other overlaps are 255.
- **The stage-2 trainer's CPU tests:**
  - marginal CE equals CE on singleton voxels;
  - the gradient matches finite differences (Foxtrot v1's check);
  - leaf-Dice drops a set voxel from c's sums only when c is in the set.

**F-A22. The track's look budget and stage 2's gate (settles the leakage check of §5 item 4).**
- **At most two candidate looks on the locked 100** (as L-A18).
  - **J1F-A** is the first look. F and T are two readings pre-registered in that one look.
  - **J1F-2** is the second.
  - A third candidate needs another decision set, chosen by a later round.
- **J1F-2's fixed sequence, every bound one-sided 1.25 %:**
  1. **V′:** V's rule against the **shipped stage-1 model**, the one J1F-2 would replace. The same reading against
     Janus 0 is reported.
  2. **B′:** every class that shipped unfolded in stage 1 still passes its F-A15 lines.
  3. **L1, theft:** for each parent group (LAD, LCx, RCA), the share of its **reference** centreline predicted as any
     stage-2 class is ≤ **0.02** (Foxtrot). This stays inside V's −0.03 per class.
  4. **L2, far paint:** in ≥ 95 % of locked cases, no voxel of a stage-2 class lies more than **30 mm** from predicted
     coronary foreground (Delta).
  5. **S:** each new class on D35 is tiered by its count: decide at n ≥ 30, report at ≥ 20, otherwise counts only.
     Each tier is printed before any D35 prediction is scored.
- **Consequences:**
  - failing V′ or B′ means J1F-2 is not adopted;
  - a class failing L1 or L2 ships folded into its parent;
  - a class below its decide tier ships folded.
- **K1 (Crucible):** at each fit check, the share of each stage-2 class's predicted voxels inside ImageCAS-X's traced
  lumen, on the 20 fit-check **training** cases. Above 0.05 at the last check, the job writes `LEAK`, and the PM may
  cancel. This costs no look.
- **Reported only:** each stage-2 class's predicted volume outside its band (K3), and its outside-band share
  (Atlas's L1, Bridge's L2). The band is a training device, not anatomy.
- **Round 3 may change these numbers.** They are frozen before J1F-2 is submitted, never after.

**F-A23. Reads per class: a rule, not Job B (settles §5 item 5; amends F-A11).**
- **F-A11's provisional thresholds stand**, with three changes:
  - "≥ 3 sources" means **≥ 3 sources with ≥ 5 trainable patients each** (Atlas);
  - the inter-read floor (detection × naming ≥ 0.6 on ≥ 10 patients with two extended reads) is **measured with the
    scorer of record**, reader against reader (Crucible);
  - if a J1F-2 class fails S or L with its read count within 1.5× of the threshold, its threshold rises to 1.5×
    before the next try (Foxtrot).
- **Job B (Bridge; Delta's B30/Ball) is not committed.** It thins traced, ordinal, ImageCAS-X classes whose parent
  copy already starts in the right territory. The six stage-2 classes start from ImageCAS-X background, from other
  sources and readers (Atlas, Crucible, Foxtrot).
  - A stage-2 class trained too early costs one J1F-2 run (≈ 15 GPU-h) and is caught by F-A22.
  - Job B would spend ≈ 22 GPU-h to avoid that.
  - It stays available as Q-F2-2.
- **Free evidence:** D3 (47 training cases) and Ramus (149) are reported with n and CI (F-A9). This is a report, never
  a steer.

**F-A24. Warm start and 1-L (settles §5 item 9).**
- **J1F-A starts from Janus 0, and V compares with Janus 0's Fir predictions, whatever 1-L's verdict.**
- **If Janus 1-L is adopted before `collect`, two reports are added. Neither decides:**
  - **V_L:** F collapsed, against 1-L's shipped locked-100 maps, scored on Fir as files;
  - **T_L:** 1-L's shipped territories with 1-F's within-territory names, under F-A19's rule.
- **Crucible's rule (T_L ships in F's place unless F is non-inferior to 1-L) is not adopted this round.** It would
  make 1-F's verdict depend on another track's outcome, and it was pre-registered by one advocate only.
  - Whether a released 1-F should carry 1-L's vessels is a product choice: Q-F2-3.
  - If the lead says yes, round 3 writes the rule.

**F-A25. One census of record (settles §5 item 10).**
- **The file of record is Delta's round-1 `experiments/Delta/j1f_r1/census.json`** with `ordinal.json`.
  - It is the only census with one row per case for all 720 non-sealed cases.
  - It is what the gate simulation reads.
- **Values to quote:**
  - **Locked gate counts:** D1 97, D2 64, OM1 84, OM2 40, PDA 98, PLB 99 under D47 (A) at 5 mm. F-A15's lines were set
    on the round-1 counts (98, 64, 84, 40, 96, 96). The differences are ≤ 3 cases and are within the rounding of the
    lines.
  - **Cases with a left PDA or PLA:** 59 of 620 (all five agree).
  - **Dominance from `Descriptors.xlsx`:** 564 / 21 / 35. It is quoted beside the label count, never instead of it.
  - **LAD trunk twigs ≥ 5 mm:** 4–5 of 620 by Delta's definition (Delta's file 4; Foxtrot's re-run 5).
    - Crucible's 13–15 is reconciled by Foxtrot: 9 of its LAD cases are the 9 cases with no left main, whose ostial
      stubs count as twigs.
    - Atlas's and Crucible's LCx count (21) includes the 20 LCx-side "Other" pieces that F-A3 maps into the LCx: they
      are unnamed marginals by design.
- **The conclusion is unchanged:** ImageCAS-X's trunks hide almost no side branch.

**F-A26. F0-r2 replaces F0** (Foxtrot v2 §13). It prints the two split pins and the D47 converter's counts on Fir's
own copy: `{'d3': 47, 'd4_to_lad': 2, 'other_lcx': 20, 'other_nearest': 1, 'other_ignore': 8}`. The command is in
[[Master plan - Janus 1-F]] §5.

**Settled by D47 and recorded only (§5 item 11):**
- **Q8:** a2 = fold 1, concurrent, its own seed. It is report only and never ensembled. F-A5's stall rule reads a1's
  `fitcheck.json`.
- **Q9:** the reading that ships (F or T) is **Janus 1-F.1**; if adopted, **Janus 1-F**. Stage 2's first read is
  **Janus 1-F.2** (D34).
- **Committed when released:** a1 ≈ 30 GPU-h plus a2 ≈ 29 GPU-h, so ≈ 60 GPU-h. Nothing is released before round 3.

## 2. Scorecards

Scores are out of 5: (a) reasoning, (b) evidence including spot-checks, (c) fit to D44, D45, D47, the other binding
decisions and Fir, and (d) risk and cost.

| Candidate | (a) Reasoning | (b) Evidence | (c) Fit | (d) Risk/cost | Verdict |
|---|---|---|---|---|---|
| **Delta v2** | 4.5. A clear answer to every item. Its Arm N and warm-start arguments are the round's cleanest. Weak: flat 0.75 / 0.80 lines; Job B as an integration test conflates a code test with a threshold experiment | 4.5. Scorer with 31 checks; the contact collapse on 720 maps; the band and the branch distances on the same 120 cases; Shi re-read and its own error withdrawn. Its gate simulation, re-run, is byte-identical. It counts on the locked 100's per-case census rows (permitted as counts, F-A7); Atlas, Bridge, Crucible and Foxtrot used counts alone | 3.5. It keeps the locked 100 as fold-0 validation (a per-epoch look) and a plans sha256 check that always fails, after track 1-L's round 2 showed both. T cannot name a left PDA | 4. ≈ 62 GPU-h + 22 for Job B | **Track 1-F's plan**, as amended |
| **Atlas v2** | 5. The line rule (5th percentile, worst scenario, round down) is principled and per class. It is the only proposal that tightens where a human leaves room | 5. The gate simulation re-ran byte-identically, and its lines hold under Bridge's model too (§ spot-checks). A scorer with synthetic and real-case validation. The band measured with whole-piece and median coverage. It disclosed seeing the title of Delta's note | 4.5. Carried L-A21 correctly (val, no locked-100 validation). Its collapse is its own ring, not SegQueue's | 4.5. 0 extra GPU | **Lines (F-A15) and scorer definitions (F-A16) adopted** |
| **Bridge v2** | 4.5. Human misnaming read from Table 1's DSC spread is the round's key insight, and why OM1 fails. Weak: its own lines still fail OM2 76 % under its own misses-only reading, which it accepts as "4 of 6 absorbs" | 4.5. Gate simulation byte-identical. The contact rule on 1,296 components re-read from its per-case census (0 disagreements, median tree 1,951 mm³). Shi row by row, with its v1 claim withdrawn | 4. SegQueue's function imported; Job B absolute. The spec predates L-A21 and keeps no val fix | 3.5. +22 GPU-h for Job B | **The naming model, SegQueue's collapse and the territory sets adopted**; Job B to the lead (Q-F2-2) |
| **Foxtrot v2** | 4.5. The sharpest defect-finder of the round: T's LCx territory, PDA–PLB chains, and the twig artefact explained. Weak: its lines keep OM1's naming at 0.85 (fails 48–51 % under Atlas's and Bridge's models) | 4.5. Gate simulation byte-identical. Three twig methods on one pass. Synthetic septal tubes give the band a length scale. Quotes no Shi number, which is safe but not an answer | 5. Carried L-A20/L-A21 exactly. F0-r2 is runnable | 4.5. 0 extra GPU | **T's fix, the L-A21 carry-over, the census reconciliation, F0-r2, the band cap and the 1.5× rule adopted** |
| **Crucible v2** | 4.5. The Dice-term analysis is the deepest (Fidon's own text, the per-sample gradient bound, the toy). Its T_L shipping rule goes beyond what one advocate should pre-register | 4. Gate simulation byte-identical, but its lines fail OM1 68 % under Atlas's model. Its band "× tree" multiples (21×, 68×) use a tree volume from a 3 × 3 × 2 max-pooled grid (median 4,012 mm³ against 1,951 mm³ at native spacing in Bridge's census), so they are about half the native ratio. Its RCA twig count is an upper bound, as it says | 4.5. Val fix, `batch_dice` pin, look-free K1 | 4.5. 0 extra GPU | **`batch_dice: false`, the band table, K1, the inter-read floor and the sealed-pool question adopted**; T_L rule to the lead (Q-F2-3) |

### Spot-checks this round

**The five gate simulations, re-run here:**

| Script | Input | Result |
|---|---|---|
| `Atlas/j1f_r2/gate_sim.py` | `census_r2.jsonl` (620) | `gate_sim.json` and stdout **byte-identical** |
| `Bridge/j1f_r2/gate_sim.py` | none | **byte-identical** |
| `Crucible/j1f_r2/sim_gates.py` | `census620.jsonl` | **byte-identical** |
| `Delta/j1f_r2/gate_sim.py` | `j1f_r1/census.json`, `ordinal.json` | `gate_sim.json` and log **byte-identical** |
| `Foxtrot/j1f_r2/gate_sim.py` | `pass1_620.jsonl` | `gate_sim.json` and txt **byte-identical** |

**Each proposal under other advocates' human models** (`experiments/Judge/j1f_r2/cross_gates.py` →
`cross_gates.json`). Per-class false-fail of a human-level model, the worst class shown, and power:

| Lines | Bridge, symmetric | Bridge, misses-only | Atlas, worst of 9 | P(reject), 2× human errors (Bridge) | P(reject), omission +0.10 (Atlas) |
|---|---|---|---|---|---|
| As ruled (F-A6) | OM1 0.51 | OM2 0.95 | OM2 0.82 | 0.98 | 1.00 |
| **Atlas P1 (adopted)** | PLB 0.12 | **OM2 0.16** | **OM1 0.08** | **0.94** | **1.00** |
| Bridge | OM2 0.09 | OM2 0.76 | OM2 0.55 | 0.96 | 1.00 |
| Crucible R2 | OM2 0.15 | OM2 0.68 | OM1 0.68 | 0.66 | 1.00 |
| Delta F2-1 | OM2 0.17 | OM2 0.78 | OM2 0.56 | 0.63 | 1.00 |
| Foxtrot R2 | OM1 0.50 | OM2 0.77 | OM2 0.56 | 0.91 | 1.00 |
| A looser trial set (judge's, rejected) | OM2 0.02 | OM2 0.12 | OM1 0.06 | **0.37** | 0.98 |

- **Of the five proposals, only Atlas's lines keep every class under the ruling's 20 % line in every human model tried** (worst 0.162:
  OM2 under Bridge's misses-only).
- **They keep the verdict's power** against a model with twice a human's errors (0.94).
- The judge's looser trial set shows the other side of the trade: per-class safety bought by giving up most of the
  power (0.37). It is recorded and rejected.
- **The five human models differ in how they split Table 1's disagreement** between misses, extra calls and misnames.
  Table 1 cannot settle this. That is why the lines are chosen by the worst model, not the average.

**Other checks:**
- **SegQueue's collapse.**
  - `assign_contact_branches` (`labels.py` l. 305–) has the chain rule: a component touching only a decided component
    takes its vessel.
  - Bridge's per-case census, re-read: 620 cases, 0 fallbacks, 0 components on the wrong side. Delta's summary: the
    same on the 620 and 0 on the locked 100.
  - Foxtrot's 4,879-voxel finding is against F-A4's per-class text, not against SegQueue's function.
- **Hashes.** `src/segtrain/tf1.py` `24441cf8…5254` (A1c), `src/segqueue14/labels.py` `5f69b5be…0a4b`, Atlas
  `j1f_scorer.py` `2da3cb1a…886c`, Delta `branch_score.py` `fb629576…9840`, Crucible `20a06cb7…f5f4`, Foxtrot
  `902de0ae…598b`, Foxtrot `labels_r2.py` `7d1441e3…bf74`. All match the candidates.
- **`batch_dice`.** icx14's `nnUNetResEncUNetPlans_60G_iso05.json` (`trillium-results/icx14/results/`): 3d_fullres
  `false`, 2d `true`. Janus 0's own plans arrive with Step T (F-A21's fallback).
- **The no-target Dice gradient.** smooth / (Σp + smooth)² at smooth 1e-5 and Σp = 10 is 1e-7 per voxel, as Crucible
  states (checked by hand).
- **Band volumes agree once definitions match.**
  - Whole-tree ring: Atlas 142 / 433 cm³ and Bridge 139 / 428 cm³ at 8 / 15 mm.
  - Host-restricted union: Delta 90k / 298k mm³ and Crucible 87k / 275k mm³.
  - Crucible's "× tree" multiples are about half the native ratio (scorecard).
- **Shi et al.** (arXiv:2007.03868v1, HTML, Table 3, "All"):
  - F alone rCE + rDC .874;
  - F + P_i rCE + rDC .900;
  - All mCE .873, mDC .876, mCE + mDC **.921**, + eCE + eDC **.931**.
  - Both of the text's sentences (".921 vs .874", ".931 vs .900") were found verbatim. Atlas, Bridge, Crucible and
    Delta v2 quote them correctly.
- **Delta's contact check opened the locked 100's label maps** to compare labels with labels. No model was scored,
  and nothing steers a recipe, so it is permitted under F-A7. The 620 result alone settles it. **Later scorer checks
  should use training cases only.**
- **Not checked by re-run:** Crucible's `dice_toy.py` (needs torch), and Foxtrot's `dice_terms.py` and `band.py`
  (need label volumes). Nothing in the ruling rests on a number from them beyond what the advocates agree on and
  Fidon's Table 2.

## 3. Rulings on the contested points

### 3.1 The gate lines (§5 item 1)

| Proposal | What it changes | Ruling |
|---|---|---|
| Atlas P1: per class, 5th percentile of the worst scenario | all 18 lines; stricter on D1/PDA/PLB | **Adopted (F-A15).** Robust under every human model (§2) |
| Bridge: human expectation − 1.96 SE | naming per class; recall only on OM2 | Its naming model is adopted as evidence. Its lines fail OM2 76 % if OM2 disagreement is all misses |
| Crucible: recall = human − 0.10, naming 0.80 | recall per class | Fails OM1 68 % under Atlas's model |
| Delta: flat 0.75 / 0.80 | two numbers | Fails OM2 56–78 % under the other models |
| Foxtrot: ruled, capped at human − 0.10 | three lines | Keeps OM1 naming at 0.85, which fails about half the time under Atlas's and Bridge's models |

### 3.2 The scorer and the collapse (§5 item 2)

- **Four scorers exist.** The one of record must count what the lines were simulated on: pieces (F-A16).
- **The collapse must be the one pool reads use:** SegQueue's (F-A17). Every advocate's own collapse agrees with it on
  the reference. On predictions only one implementation must exist.

### 3.3 Arm N (§5 item 3)

Dropped, unanimously. If F-A6's verdict is "not adopted", round N+1 may build it as a candidate. Foxtrot's narrower
trigger (V passes, B1 passes, B2 fails in ≥ 3 classes) is the case where it is most useful.

### 3.4 Stage 2's loss and band (§5 item 4)

- **Leaf-Dice per sample, `batch_dice: false`** (F-A21).
- **The band is territory-specific, 15 mm until extended reads re-set it within [8, 25] mm.**
  - Bridge's 8 mm default is not adopted. Foxtrot's tubes and Delta's branch distances both show that 8 mm leaves most
    of a 20 mm branch outside it, where 620 ImageCAS-X cases call it background.
  - Bridge's concern (the band releases 70–220× the tree's volume) is real. It is answered by the per-territory sets,
    by the read-based re-set and by F-A22's gate, not by narrowing the band blind.
- **The leakage gate** (F-A22) takes Foxtrot's theft measure (on reference centreline, tied to V's tolerance), Delta's
  far-paint bound, Crucible's look-free K1, and L-A18's look budget.

### 3.5 Reads per class (§5 item 5)

A rule, 3 to 2 (F-A23). Delta's point stands that the label-set trainer needs testing before it trains a real class.
It is met by CPU tests (F-A21), not by a 22 GPU-h run whose answer transfers weakly.

### 3.6 The scoring set for the six untraced classes (§5 item 6)

- **D35 (extended mode) is the scoring set, with Delta's, Atlas's, Bridge's, Crucible's and Foxtrot's yield tables in
  agreement.**
  - **Report** a class at ≥ 20 patients, which needs a drawn share π ≈ 0.6–0.7.
  - **Decide** at ≥ 30, which needs π ≈ 0.9.
  - S1 may reach the report tier. SN, Conus and RMA stay counts only.
- **A larger held-out pool set is a D35 question.** The first extended D35 wave measures π per class, and the PM asks
  then if a class the lead wants shipped falls short.
- **Crucible's sealed-pool question is new and is the lead's: Q-F2-1.**

### 3.7 Shi et al. (§5 item 7)

Settled (§0, §2). Foxtrot's "drop both" is not needed now that the rows are verified.

### 3.8 The swe spec (§5 item 8)

- Delta §8 + Atlas §2.8 + Crucible §8 + Foxtrot §8 agree on the shape: `janus1l` as L-A21 freezes it, imported, with
  1-F's items.
- The ruling takes Delta's interface and modes. It corrects them by F-A16 to F-A20.
- **The issue is opened only after the round that rules the plan converged** (F-A12).

### 3.9 Warm start (§5 item 9)

Janus 0, unanimously (F-A24). Crucible's T_L shipping rule goes to the lead (Q-F2-3).

### 3.10 Census (§5 item 10) and D47 consequences (§5 item 11)

F-A25, and the D47 record in §1.

## 4. The first Fir jobs

**Two jobs can run now. Both are 0 GPU-h, and both are the lead's.**
1. **Step T** (track 1-L's, with L-A20's additions):
   - Janus 0's checkpoint, plans, `dataset_fingerprint.json`, training logs, the 160 labels and aortas, and Fir's
     locked-100 predictions go to `$KEEP`.
   - **Added for 1-F:** post the `batch_dice` value of Janus 0's 3d_fullres plans (F-A21).
   - **The scratch purge is about 2026-12-20.** Without Step T, neither track can warm-start, and 1-F has no V baseline
     and no T.
2. **F0-r2** (F-A26): the split pins and the D47 converter's counts on Fir's own copy.

**J1F-A waits on:**
- the swe issue (F-A12), filed after convergence;
- the split file `configs/janus1/split-2026-11.json` (F-A1);
- the amended scorer's posted hash (F-A16);
- `configs/janus1/j1f_gates.json` (F-A15).

#303 requires at least three rounds before training starts.

## 5. What round 3 must settle

1. **The scorer file of record.**
   - Atlas's `j1f_scorer.py` with its collapse replaced by the SegQueue import (F-A16, F-A17).
   - Delta's 31 checks and Atlas's self-test ported to it, run on training fixtures.
   - Its sha256 posted.
   - Show that the per-piece recall it computes on the 620 matches the piece distribution F-A15 was simulated on.
2. **`configs/janus1/j1f_gates.json`** with F-A15's lines, and a test that a fixture with OM2 recall 0.59 fails while
   0.61 passes.
3. **The full J1F-A command block for the master plan**, from Delta §8.1 as amended. Include the chunked
   predict-and-decode (F-A20) with a disk estimate from one case's npz size.
4. **The converged stage-1 spec, as one diff against `janus1l`**, with every refusal and self-test of Delta §8.3 and
   §8.6, plus:
   - F-A19's T test (a left PDA in Janus 0's LCx territory is named PDA);
   - F-A20's val test (no locked id in `splits_final.json`).
5. **F-A22's stage-2 numbers:** keep or change 0.02, 30 mm, 95 % and K1's 0.05. Report each one's false-fail on
   ImageCAS-X references treated as a prediction, on the 620 (CPU).
6. **The answers to Q-F2-1 to Q-F2-3, and their consequences.** If Q-F2-3 is yes, write T_L's verdict rule and say
   whether it is inside the first look.
7. **Step T and F0-r2's results, if posted.**
   - If Janus 0 trained with class-weighted CE, decide 1-F's loss (as L-A20).
   - If `batch_dice` is true, `leaf_skip` (F-A21).
8. **Whether the plan is converged.**

## 6. Questions for the lead

None of these changes a D-number unless it says so. Each has a recommendation.

**Q-F2-1. May the 150 sealed pool patients be read in extended mode?** (Crucible v2 §6, its question as asked.)
- **The problem:** D35's 35 patients can report S1 at most. SN, Conus and RMA can never reach 20 there. The 150-patient
  pool seal is the only other set outside training. At plausible visibilities it would hold 78–165 patients per class
  with D35 (Crucible's table).
- **It does not open the seal.**
  - D27's single look (A19) stays the only look.
  - Extended reads collapse to the same four classes (D47 Q1), so the four-class acceptance read is unchanged.
  - The extended classes on the seal would be scored **only inside that single acceptance look, as a report**. They
    never decide 1-F's stage 2 and are never read earlier.
- **Cost:** annotator time on sealed cases, under D47 Q7's "trace beyond the seed".
- **Recommended: yes**, on those three conditions: scored only at the seal's single look, as a report, never earlier,
  never deciding. If you prefer to keep the seal's reads exactly as they are, the answer "no" costs only the report on
  SN, Conus and RMA, which then stay counts only until a larger held-out set exists.

**Q-F2-2. Run Job B (J1F-B, ≈ 22 GPU-h on Fir) after J1F-A?** (Bridge v2 B-v2-4, which names it the lead's
allocation call; Delta v2 §5 proposes the same run as B30 + Ball.)
- **What it measures:** how few extended reads a class needs. It thins OM and PLB on a 60-case hold-out of the 620.
- **Against it** (Atlas, Crucible, Foxtrot):
  - it measures traced ImageCAS-X classes, which transfer weakly to the six untraced ones;
  - a class trained too early costs one ≈ 15 GPU-h J1F-2 run and is caught by F-A22's gate.
- **Recommended: no for now.** Priority on Fir stays a1, then a2. Revisit if the first J1F-2 class fails with its count
  within 1.5× of the threshold (F-A23).

**Q-F2-3. If Janus 1-L is adopted, should a released Janus 1-F carry 1-L's vessels?** (Crucible v2 §9's T_L rule;
Bridge v2 §10 names the choice the lead's.)
- **The choice:** F's own vessels must pass V against Janus 0. But 1-L may be better than Janus 0. Crucible would ship
  T_L (1-L's vessels, 1-F's names) unless F's vessels are non-inferior to 1-L's.
- **Recommended: yes in principle, written as a rule by round 3 before J1F-A is submitted.** Until then, T_L and V_L
  are reports only (F-A24).
  - It costs no GPU and no new look: T_L is a third reading inside J1F-A's one look.
  - It keeps the project from releasing a branch model whose vessels are worse than its best vessel model.

## 7. What would change this ruling

| Observation | Then |
|---|---|
| A measured ImageCAS-X or pool second-reader branch study (e.g. D35's double reads, scored with F-A16's scorer) | F-A15's lines are recomputed by Atlas's rule from the measured rates, before J1F-A is submitted, never after |
| Step T shows class-weighted CE in Janus 0's logs | J1F-A's loss is re-decided in round 3 (as L-A20) |
| Step T shows `batch_dice: true` in Janus 0's 3d_fullres plans | Stage 2 uses `leaf_skip` (F-A21) |
| F0-r2's pins or counts differ | Stop. The PM finds which copy differs |
| Step T has not run by early December | The PM escalates. The purge (~2026-12-20) removes the warm start, V's baseline and T |
| The amended scorer's per-piece counts on the 620 differ from the piece distribution the lines were simulated on | Re-run Atlas's `gate_sim.py` with the scorer's counts and re-freeze F-A15 (round 3) |
| The first extended reads put a group's 95th-percentile distance beyond 25 mm | That group's band stays at 25 mm, and its far voxels are reported. Round N+1 considers Shi's exclusion term |
| J1F-A's fit check writes `STALL` | F-A5 as ruled: the PM may cancel, and round N+1 chooses the next design |
| Q-F2-1 answered no | SN, Conus and RMA stay counts only until a larger held-out set exists |
| Q-F2-3 answered yes | Round 3 writes T_L's verdict rule inside J1F-A's look |
