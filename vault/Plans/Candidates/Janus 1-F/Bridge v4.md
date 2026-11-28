---
tags: [plans/candidate, bridge, janus-1f, branches, stage2, partial-labels, fir, D45, D47, D54, D55, round4, freeze]
author: Bridge
track: Janus 1-F
round: 4
updated: 2026-11-28
issue: christianGRogers/Asclepius#303
---

# Bridge v4 (Janus 1-F): under D54 every extended read is a full label, and J1F-2's numbers come from one script the lead runs

## 0. Position in one paragraph

Bridge accepts the plan in force ([[Master plan - Janus 1-F]]: Delta v3 as amended by F-A1 to F-A36) and the lead's
answers D54 and D55. **Stage 1 (J1F-A, a2) stays converged.** D54 and D55 change nothing in it (§2). This round is
about stage 2 (J1F-2), and Bridge's answer is:

1. **D54 removes the only partial label that came from the pool.** Every rule that depended on complete groups was
   about one thing: the parent set {parent ∪ children} of an extended read with no tick. That set is gone. In an
   extended read every voxel is now a singleton, or ignore where two unrelated classes overlap (§3). Sets remain only
   on ImageCAS-X (the band) and on 4-class pool reads.
2. **This makes the main stage-2 theft free path disappear, and adds one new risk.** Foxtrot's `dice_terms.py`,
   re-run with D54's labels, shows that a head painting S1 over the whole LAD group used to cost nothing in CE and
   leaf-Dice. Now it costs CE × 3.7 and doubles S1's leaf-Dice loss (§3.1). The new risk is that a reader's omission
   is now a negative label. Two changes handle it:
   - the inter-read floor is pooled in both directions, so an omission counts against it;
   - the freeze reports stage-1 classes drawn far less often than ImageCAS-X draws them.
   One lead question follows (Q-F4-1: reads with no branch drawn at all).
3. **D55 is written into the plan** (§4):
   - the sealed pool is never read by the freeze, which refuses it (exit 3);
   - there is no J1F-B;
   - **J1F-2's look follows F-A32's table**, with readings F2, T2 and T2_L, so T_L can still ship after stage 2.
4. **The freeze is one script**, `experiments/Bridge/j1f_r4/j1f2_freeze.py` (§6). It reads a SegQueue14 export and
   writes one json with a sha256. The json holds:
   - the band per class group;
   - L1r's run length (3 mm), L2d's gap (30 mm) and the theft line used by both L1r and K1r (0.02);
   - each class's read counts and inter-read floor, measured with the scorer of record's own code;
   - the D35 S-tiers.
   Each number has a fixed rule and a STOP condition. **Tests: ⟨TESTS⟩ checks pass**, including two 620-derived
   stand-in exports:
   - with clean readers, 3 mm, 30 mm and 0.02 stay;
   - with long ostia, 38 mm gaps and a 45 % omission rate, they move as the rules say, and the floor fails.
5. **Stage 2's shape and procedure can be ruled converged now** (§8). Only its numbers are left, and the freeze
   computes them mechanically. A STOP sends a number to the PM, not to a new round.

## 1. What this round read, and independence

- **Read:**
  - `.claude/roles/researcher.md`;
  - [[Human decisions]] (D27, D35, D44 to D55);
  - [[Janus 1-F Round 1]], [[Janus 1-F Round 2]] and [[Janus 1-F Round 3]];
  - [[Master plan - Janus 1-F]];
  - Bridge v3;
  - Foxtrot's `j1f_r2/dice_terms.py` and `j1f_r3/stage2_falsefail.py`;
  - the scorer of record;
  - `segtrain.pool_seal`, `janusm.guard`, and SegQueue14's export and labels.
- **Not read:** no other round-4 candidate and no `exp/j1f-r4-*` branch.
- **Data:**
  - the ImageCAS-X segmentations of **40 of the 620 training cases**, chosen by the smallest
    sha256(`asclepius-j1f-r4-bridge-standins:` + id). `fetch_subset.py` asserts the 620's pin `1350cb1f…1152` and
    requests no other member;
  - for the locked 100, nothing;
  - for the 620 prevalence prior, **counts only** from the committed `Delta/j1f_r1/census.json` rows of the 620.
- **Never opened:** any locked, sealed-80, quality-0 or D60 label or CT; any TotalSegmentator twin; any pool read or
  pool CT. The stand-in "reads" are ImageCAS-X training labels plus synthetic tubes, under names (`Standin<A-D>__pNNNN`)
  that are no pool or ImageCAS-X id.
- Nothing ran on Fir, SciNet or Trillium.

## 2. D54 and D55 against stage 1: nothing changes, one pin to protect

- **D54 does not touch J1F-A.**
  - J1F-A trains on ImageCAS-X's 620 only. Its labels come from the scorer's `stage1_labels`; no pool read and no tick
    enters it.
  - Its scorer reads ImageCAS-X references and model maps. Neither has groups.
- **D55 Q-F2-3 and Q-F3-1 to Q-F3-3 are already written into stage 1** (F-A32, F-A36's conditions); D55 only
  answers them. Q-F2-1 and Q-F2-2 are stage-2 questions.
- **One thing to protect: `src/segqueue14/labels.py` is pinned.**
  - The scorer of record asserts its sha256 `5f69b5be…0a4b` at import, and `collect` pins it (F-A36).
  - D54's two SegQueue commits (`c3ad98c`, `01bf717`) left it unchanged; it still hashes to `5f69b5be…0a4b` on dev.
  - But it still holds the now-unused `COMPLETE_GROUPS` and an `EXTENDED_INSTRUCTIONS` text that says "Tick a branch
    group complete". The module no longer shows that text (`test_segqueue14_module.py` asserts it is unused).
  - **A tidy-up of `labels.py` for D54 before J1F-A's and J1F-2's `collect` would stop `collect`**, safely but at
    the cost of a re-spec. **P-r4-8:** any D54 tidy-up of `labels.py` waits until after J1F-2's look, or goes in
    another file.
- **Conclusion: stage 1 is not reopened.**

## 3. D54 in stage 2: what depended on complete groups, and what replaces it

### 3.0 The inventory

| Where | What depended on complete groups | Under D54 |
|---|---|---|
| F-A21, "Extended reads" (D47 Q3) | a complete group's parent is a singleton; an unmarked group's parent is {parent ∪ children} | **every extended read's parent is a singleton.** An undrawn branch is absent: its would-be voxels are whatever the read says (its parent, or background) |
| [[Master plan - Janus 1-F]] §4, "Extended reads" | the same text | replaced (§4 below) |
| `experiments/Foxtrot/j1f_r2/dice_terms.py` | the extended sample is the no-tick case: `S_ext[2, f(grp)] = True` (the LAD group is {LAD-group, S1}) | superseded. `dice_terms_d54.py` re-runs Foxtrot's own `case` with that one line removed (§3.1) |
| `experiments/Crucible/j1f_r2/dice_toy.py` | its EXT sample is already "complete: every voxel singleton" | unchanged: it was D54's case all along |
| F-A21's trainer tests | "leaf-Dice drops a set voxel from c's sums only when c is in the set" | kept, for ImageCAS-X and 4-class reads. Three tests added (§3.1) |
| SegQueue14 export, `read.json` `completeGroups`, manifest `complete_groups` | the signal of absence | **read by nothing that trains.** The freeze counts reads with old ticks and changes no number for them (test C19) |
| D53's "a tick counts as work" | a tick-only read was sent as 21 classes with no branch drawn | such reads now say "all 14 branches absent" (§3.5, Q-F4-1) |
| `labels.py` `COMPLETE_GROUPS`, `group_members` | the tick's groups | unused by 1-F. Not edited until after J1F-2's look (§2) |
| L1r, L2d, K1r, F-A23's counts | **no dependence**: they read ImageCAS-X references, model maps and drawn classes | definitions kept; their numbers are measured from the reads (§3.3) |

No other script in the repository builds a stage-2 label from a tick. `grep -rni complete` over `experiments/*/j1f*`,
`src/segtrain` and `trillium/` finds only the two dice files above and an unrelated resume flag.

### 3.1 Labels and loss

**The label of an extended read (`labels_d54`, the freeze's and the proposed trainer's converter):**

| Voxel is in | Label |
|---|---|
| exactly one of the 18 vessel/branch classes | that class |
| a branch and its own parent vessel, nothing else (D47 Q4; PDA, PLB and SN take RCA or LCx) | the branch |
| any other combination (two branches; a branch on another vessel; LM and LAD) | ignore |
| a material only | background; a vessel voxel that is also plaque stays vessel (D46 Q8's 1-L rule, applied to 1-F) |
| nothing | background |

- An undrawn class needs no rule: nothing is a set.
- Stage-2 values are 0–12 as stage 1, then S1 13, S2 14, S3 15, SN 16, Conus 17 and RMA 18.
- Ignore is 255 in the scorer and **19 on disk**, by F-A29's max + 1 rule for 19 labels.

**What this does to the loss.**
- On an extended read, the marginal CE is CE, and leaf-Dice is plain per-sample Dice.
- Sets remain only on:
  - ImageCAS-X background inside the band (F-A21's table);
  - 4-class pool reads, where the parent is {parent ∪ its children}.
- Leaf-Dice, `batch_dice: false` and the marginal CE are unchanged.

**Evidence: `dice_terms_d54.py`** runs Foxtrot's own `case` on 10 hash-chosen training cases, once as written
(`d47q3`) and once with D54's single change. Output: `dice_terms_d54.json`. Each cell is the loss on the extended-read
sample, mean of the 10 cases:

| Scenario on the extended read | CE, D47 Q3 (no tick) | CE, D54 | S1 leaf-Dice loss, D47 Q3 | S1 leaf-Dice loss, D54 | LAD-group leaf-Dice loss, D47 Q3 / D54 |
|---|---|---|---|---|---|
| A right (tube → S1) | 0.00080 | 0.00088 | 0.319 | 0.419 | 1.000 (no target) / 0.079 |
| B miss (tube → LAD-group) | 0.00138 | 0.00146 | 0.971 | 0.977 | 1.000 / 0.103 |
| **C sprawl (S1 at 0.5 on every LAD-group voxel)** | **0.00088** | **0.00325** | **0.319** | **0.839** | 1.000 / 0.450 |
| D intrude (OM1 at 0.5 on the LAD group) | 0.00302 | 0.00325 | 0.319 | 0.446 | 1.000 / 0.450 |

What the table shows:
- **Before D54, a sprawling S1 head was free on an untick read.** Its CE was within 10 % of the right answer's, and its
  S1 leaf-Dice loss was identical, because every LAD-group voxel's set held S1.
- **Under D54 the same sprawl costs 3.7 × the CE and 2.0 × the S1 loss.** The extended read now also gives the LAD
  group a Dice target: before, the group's leaf-Dice term was 1.0 with no target at all.
- That was the leakage stage 2's gates were built to catch. D54 removes it at the source, on every extended read.

**Trainer CPU tests added to F-A21's three:**
1. the same read with and without ticks gives byte-identical labels;
2. no {parent ∪ children} set is ever built from an extended read;
3. the D47 Q4 table above, cell by cell.

The freeze's self-test runs the same checks on `labels_d54` (§6.2).

### 3.2 The band and the read thresholds

- **The band's role is unchanged.** It exists for ImageCAS-X's background, where S1–S3, SN, Conus and RMA are
  untraced. D54 says nothing about ImageCAS-X.
- **Its measurement gains reads.** F-A21 sets each group's width to the 95th percentile of its drawn voxels'
  distance from the host, over the trainable extended reads (≥ 10 reads per group), clamped to [8, 25] mm. Under D47
  Q3 an argument could be made to measure it only on ticked groups, since an untick read might have stopped early.
  Under D54 every extended read is complete by rule, so **every trainable extended read with the group drawn counts.**
- **The read thresholds keep their positives:** ≥ 30 trainable patients with the class drawn (scorer presence,
  ≥ 5 mm), from ≥ 3 sources with ≥ 5 each (F-A11, F-A23).
- **D54 changes what a negative is.** An extended read without the class now trains the class as absent. So the
  inter-read floor must see omissions:
  - **P-r4-3: the floor is pooled in both directions.** Each read is the reference for the other, and
    named ÷ pieces ≥ 0.6 is taken over both directions' pieces.
  - It is measured on ≥ 10 double-read patients in which **at least one** read drew the class.
  - A reader who drops a class that the other drew loses that piece outright. One direction alone sees this only
    when the omitting reader is the prediction.
  - Presence agreement between the two reads is reported beside it.
  - Test C17: one reader omits the class in every pair, so the floor is 0.5 and the class does not train.
- **4-class pool reads** keep F-A11's {parent ∪ children} parent set. D54 is about extended reads only.
  - **P-r4-7 (independent of D54):** their background inside the band should take ImageCAS-X's band sets. A 4-class
    reader was not asked to trace septals beyond the seed either.

### 3.3 L1r, L2d and K1r

Their definitions do not depend on groups. Each reads ImageCAS-X references or model maps. What D54 changes is
**what a correct stage-2 model learns**, and therefore what these numbers have to tolerate:

- **L1r (3 mm run, 0.02 line).**
  - Under D54, the only stage-2 paint on a parent that training rewards is the readers' own child-over-parent overlap
    (D47 Q4). Before, an untick read rewarded paint anywhere on the parent group.
  - So **the run length must pass the readers' own overlap runs**. The freeze measures them along each read's stage-1
    centreline:
    - the skeleton of the stage-1 channels, in L1r's three parent groups;
    - points inside any stage-2 channel;
    - 26-connected runs, at Foxtrot's length (points × mean voxel side).
  - Rule: **run = max(3 mm, the 99th percentile of the reader runs, rounded up to 0.5 mm)**. STOP above 8 mm, where a
    reader's ostium is as long as the thief F-A30 was built to catch.
  - **The line** is re-checked on the same reads: the readers' own stolen share in runs longer than the run length,
    per group, with a read-bootstrap 97.5 % upper bound. Rule: **0.02 if 2 × the worst upper bound ≤ 0.02; otherwise
    2 × that bound, rounded up to 0.005**. STOP above 0.05, since Foxtrot's thief takes 0.137–0.142.
- **L2d (30 mm).**
  - Under D54, a gap a reader leaves between pieces of a branch traced beyond the seed (D47 Q7) is confirmed
    background, so a correct model reproduces it.
  - The freeze measures L2d's own statistic on the reads: each stage-2 26-component of ≥ 20 voxels, and its nearest
    distance to every other coronary voxel.
  - Rule: **D = the first of 30, 35, …, 60 mm at which ≤ 2 % of reads have any component farther**. At 2 %, a correct
    model fails "≥ 95 of 100" with probability 1.6 % (binomial). STOP if none qualifies.
  - The 95-of-100 point count stays.
- **K1r** is L1r's statistic on the fit-check 20 (F-A30). It takes **the same run length and the same line** from
  the freeze, so training and the look still agree.

**Reports beside them** (never deciding):
- the readers' run maximum;
- each group's farthest drawn voxel (P99, K3's analogue);
- the drawn-length list per stage-2 class. This is §7's "septals longer than 40 mm" trigger, which under L2d is a
  report. L2d measures gaps, not lengths.

### 3.4 The read counts each class needs (as the freeze prints them)

| Per stage-2 class | Needed to train | Source |
|---|---|---|
| trainable patients with the class drawn (presence ≥ 5 mm in any of their extended reads) | **≥ 30**, or **45** after a near miss (F-A23's 1.5 ×, `--raised`) | F-A11, F-A23 |
| sources with ≥ 5 such patients | **≥ 3** | F-A23 |
| double-read patients with the class in either read | **≥ 10** | F-A11 |
| inter-read named ÷ pieces, both directions pooled, by the scorer of record | **≥ 0.6** | F-A23, P-r4-3 |
| D35 patients with the class (counts only, `--d35-tiers`) | decide ≥ 30, report ≥ 20, else counts | F-A22's S, printed before any D35 prediction |

- **"Trainable"** means not sealed, not D35 (any of the five Round-10 draws), not the A34 reserve, not a
  TotalSegmentator twin (`janusm.guard`), not marked defect, and extended.
- **The patient** is `segtrain.pool_seal.ingest_patient`. A replica `__r2` is the same volume read again.

### 3.5 The one new risk, and Q-F4-1

Under D54 an extended read in which **no branch class is drawn at all** says "this heart has no D1, no PDA, no
septal". D1 is present in 98 % of ImageCAS-X's 620 hearts. Such reads arise three ways:
- a case flagged for extended mode that the reader read as four classes. D53 sends 21 classes anyway, and D35 and,
  under D55, the sealed pool are flagged;
- an old read whose only "work" was a tick (D53);
- a reader who used the panel's toggle but drew nothing.

Trained under D54, each teaches every branch as its parent. The freeze counts such reads (`reads_no_branch_drawn`).
For D1, D2, OM1, OM2, PDA, PLB and Ramus it also prints the extended reads' drawn rate against ImageCAS-X's 620 rate,
and flags any class whose 97.5 % upper bound is below 0.8 × that rate (test C18).
- **Q-F4-1** (§10) asks whether reads with no branch drawn may be left out of stage-2 training whole. They would not
  be reinterpreted. Every other extended read follows D54 as written.

## 4. D55 in stage 2: the plan as it now stands

The text below replaces [[Master plan - Janus 1-F]] §4. Unchanged items are kept word for word in substance.

**Stage 2 (J1F-2)**

- **Labels (D54, D47 Q4):**
  - an extended read is a full label: every voxel in one class is that class; a branch over its own parent is the
    branch; other overlaps are ignore; an undrawn branch class is absent;
  - ticks change nothing; materials are dropped as D46 Q8;
  - values are 0–18 (S1 13, S2 14, S3 15, SN 16, Conus 17, RMA 18), with ignore 19 on disk (F-A29's rule) and 255 in
    the scorer.
- **Sets** exist only on:
  - ImageCAS-X background inside the band: LAD and D1–D3 → {bg, S1, S2, S3}; RCA → {bg, RMA}; proximal RCA (30 mm) →
    {bg, RMA, SN, Conus}; proximal LCx (20 mm from the LM) → {bg, SN}; elsewhere {bg}. Traced voxels are never in a
    set;
  - 4-class pool reads, where the parent is {parent ∪ its children} (and, if P-r4-7 is adopted, background in the band
    as ImageCAS-X).
- **Loss:** marginal CE + per-sample leaf-Dice, smooth 1e-5, `batch_dice: false` asserted.
- **Heads:** parent copy from the stage-1 network behind the shipped reading (S1–S3 ← LAD; SN, Conus, RMA ← RCA).
- **Band, run length, gap, theft line, counts, floors:** **from the freeze json** (§6), whose sha256 J1F-2's launcher
  pins together with the trainable-reads list's sha256. J1F-2 trains on exactly the freeze's trainable reads.
- **Train a class** when the freeze prints `trainable: true`:
  - ≥ 30 patients (45 after a near miss);
  - ≥ 3 sources of ≥ 5;
  - ≥ 10 double-read patients;
  - floor ≥ 0.6, both directions.
- **Order on Fir (D55 Q-F2-2): a1, a2, then J1F-2 when the freeze shows at least one stage-2 class trainable.**
  - **No J1F-B.**
  - Revisit Q-F2-2 only if a J1F-2 class fails S or L with its count within 1.5 × of its threshold. That failure also
    raises the class's count to 1.5 × (F-A23).
- **During training, K1r:** L1r's statistic, at the freeze's run length, on the 20 fit-check training cases at each
  fit check. Above the freeze's line at the last check, the job writes `LEAK`, and the PM may cancel.
- **J1F-2's look**, the track's second, with every bound one-sided 1.25 %.
  - **Readings, pre-registered in the ledger before anything is scored. All are readings of J1F-2's single
    prediction:**
    - **F2**, J1F-2's own decode;
    - **T2**, J1F-2's within-territory names selected by the territory map of **the shipped stage-1 reading** (F, T or
      T_L). Its four classes are that map, asserted bit-equal;
    - **T2_L**, the same names selected by Janus 1-L's shipped map. Only if 1-L is adopted and its maps are on Fir
      before J1F-2's `collect` opens the ledger (F-A32's condition, D55 Q-F2-3).
    - `decode` writes G2: three uint8 maps of the argmax within {LAD, D1–D3, S1–S3}, within {LCx, OM1, OM2, Ramus,
      PDA, PLB, SN} and within {RCA, PDA, PLB, SN, Conus, RMA}.
  - **The sequence is F-A32's table**, with:
    - V′ = V's four clauses against the shipped stage-1 reading;
    - V′_L = the same against 1-L, read only after V′ and B′;
    - B′ = every class that shipped unfolded in stage 1 still passes its F-A27 line;
    - then, per new class, L1r (freeze run, freeze line), L2d (freeze gap, ≥ 95 of 100) and S (D35 tiers).

| V′ (F2 vs shipped stage 1) | V′_L (F2 vs 1-L) | B′ | Ships |
|---|---|---|---|
| pass | pass, or 1-L not in time | on F2 | **F2** |
| pass | fail | on T2_L | **T2_L** |
| pass | fail | fails on T2_L, passes on F2 | **F2**, "vessels below Janus 1-L" in `DECISION.md` |
| fail | — | on T2_L (if in time), else on T2 | **T2_L**, else **T2** |
| any | — | fails on every reading | J1F-2 not adopted; the stage-1 model stays shipped |

- **Consequences of the look:**
  - a new class failing L1r, L2d or S ships folded into its parent;
  - T2's and T2_L's vessels equal an already-adopted map by construction, so V′ is met there by identity and only B′,
    L and S decide;
  - it is one look: V′_L chooses whose vessels ship and adopts nothing new.
- **Reports only:** literal L1, L2 and K1; Delta's lumen-core K1; each class's farthest-voxel distance and
  outside-band volume; the freeze's D54 reports.
- **Scoring sets (D55 Q-F2-1).**
  - J1F-2 is decided on the locked 100 (V′, B′, L) and D35 (S). The freeze prints D35's tiers from counts before any
    D35 prediction is scored.
  - **The 150 sealed pool patients are read in extended mode. Their extended classes are scored once, inside D27's
    single acceptance look, as a report with n and CI by the scorer of record.** They are never scored earlier, never
    decide J1F-2, and never set a band, run length, gap, line or count.
  - The freeze refuses any sealed read (exit 3), and so refuses an `--acceptance-scoring` export.

## 5. Round 3 §5, item by item

| §5 item | Answer |
|---|---|
| 1. Re-set the band per class group from the trainable extended reads, post it with its sha256 | `j1f2_freeze.py` computes it per group (LAD, RCA, pRCA, pLCx) by F-A21's rule. The json and its sha256 are posted; J1F-2 pins it (§6). Groups with < 10 reads keep 15 mm and cannot train anyway (< 30 patients) |
| 2. Re-check L1r's 3 mm, L2d's 30 mm and K1r's 0.02 on the same reads | The same run, from the reads' own child-over-parent runs, by the rules of §3.3. Each number has a written rule and a STOP; K1r inherits L1r's run and line |
| 3. Confirm each class's read count and inter-read floor with the scorer of record | Printed per class (§3.4). The floor runs `j1f_scorer.score_case` itself (sha256 `5221032f…2e5b`, checked at import) with its class tables widened to the 14 branches inside a context manager. Nothing else is changed, and the tables are restored (self-test) |
| 4. Apply Q-F2-1's and Q-F2-2's answers | §4: sealed extended classes as a D27 report only, refused by the freeze; no J1F-B, Fir's order a1, a2, J1F-2 |
| 5. Re-derive F-A27's lines if a measured second-reader branch study exists before J1F-A is submitted | **None is on record** (2026-11-28), so F-A27 stands. SegQueue's double reads are not that study: they are different readers on different CTs from ImageCAS-X's second analyst, whose disagreement F-A15 models. The freeze prints their stage-1 inter-read figures as a report |

## 6. The freeze procedure

### 6.1 What the script does, in order

1. **Before any read file is opened:**
   - it checks the scorer of record's sha256 and the D35 list's sha256;
   - it refuses a `--four-class` export (exit 2);
   - **it refuses any read of a sealed pool patient, and an `--acceptance-scoring` export (exit 3).**
   - Every other held-out read is set aside by patient and counted: the D35 draws, the A34 reserve, TotalSegmentator
     twins and ImageCAS-X test/val (`janusm.guard`, fail closed: exit 5 if it cannot load).
2. Per trainable extended read (defect reads skipped), on the read's bounding box:
   - the D54 labels;
   - scorer presence per class;
   - the reader runs per parent group, with the centreline points;
   - the L2d gaps;
   - the drawn-distance histogram per band group. Proximal hosts are geodesic from the LM contact or from the
     vessel's thickest skeleton end, since pool CTs have no aorta mask;
   - SN is assigned to RCA or LCx by face contact, as SegQueue's collapse assigns it.
3. Per double-read patient, the scorer of record in both directions.
4. With `--d35-tiers`, D35 reads are opened for per-class presence only.
5. It writes `freeze.json` and `freeze_rows.jsonl` and prints both sha256 values and the summary.
   - `freeze.json` holds counts, millimetres, rates, source names, library versions and the sha256 of the trainable
     list.
   - `freeze_rows.jsonl` names reads; it stays with the export and only its sha256 is posted.
   - Exit 4 if any STOP fired.

### 6.2 Tests (`test_freeze.py` → `test_freeze.out`): ⟨TESTS⟩

⟨TESTTABLE⟩

### 6.3 The exact command the lead runs

On the machine that serves SegQueue14, with a dev checkout at `$R` and a venv holding numpy, scipy, scikit-image and
nibabel (the versions are printed into the json):

```sh
R=<repo checkout>; X=$HOME/j1f2_freeze/export_$(date +%F); W=$HOME/j1f2_freeze; mkdir -p $W
git -C $R fetch origin dev && git -C $R checkout dev && git -C $R pull --ff-only
segqueue14-export --out $X --replicas all            # no --four-class, no --acceptance-scoring, no --include-unreviewed
PYTHONPATH=$R/src python $R/experiments/Bridge/j1f_r4/j1f2_freeze.py selftest
PYTHONPATH=$R/src python $R/experiments/Bridge/j1f_r4/j1f2_freeze.py \
  --export $X --out $W/j1f2_freeze.json --np 8 --d35-tiers ; echo "exit $?"
sha256sum $W/j1f2_freeze.json $W/j1f2_freeze_rows.jsonl $R/experiments/Bridge/j1f_r4/j1f2_freeze.py
```

- After a near miss, add `--raised <class> …` (F-A23).
- **Post on #303:**
  - the printed summary;
  - `exit N`;
  - the three sha256 lines;
  - `j1f2_freeze.json`. It holds no read name, volume or patient id.
- **Do not post** `j1f2_freeze_rows.jsonl` or the export.
- **Exit codes:**

| Exit | Meaning | Then |
|---|---|---|
| 0 | numbers frozen | the PM copies the json into J1F-2's config, and the launcher pins its sha256 and the trainable-reads sha256 |
| 2 | a four-class export | re-export without `--four-class` |
| 3 | a sealed read is in the export | re-export without `--acceptance-scoring`. Never edit the export by hand |
| 4 | a STOP | the PM reads the STOP line. No J1F-2 is submitted on these numbers |
| 5 | a pin or the guard failed | stop; the PM finds which file moved |

**When it runs:**
- whenever the lead wants a count. It costs CPU only, about 20 s per read on 3 cores here;
- **the run that J1F-2 pins is the last one before J1F-2 is submitted, never one after.** A later export with more
  reads is a new freeze for a later J1F-2 submission, not an edit of this one.

## 7. What the `role:swe` stage-2 spec must carry (when J1F-2 is near)

This is not filed now, because stage 2 waits on reads. It holds:
- `labels_d54` as the one extended-read converter, ported byte-for-byte or imported with the freeze's sha256, and
  tested on the same fixtures;
- the set table, which has no extended-read entry;
- ignore 19 on disk;
- `decode` writing F2, G2 and the marker;
- `collect2` with the readings of §4 and F-A32's table;
- the launcher refusing a missing or different freeze sha256, a trainable list that differs from the freeze's, or a
  sealed name;
- K1r reading the freeze's run and line.

## 8. Convergence

- **Stage 2's shape and procedure can be ruled converged now.** What a round could still choose:
  - the labels: fixed by D54 and D47 Q4;
  - the loss, sets and heads: F-A21, narrowed by D54;
  - the gates: F-A30's definitions;
  - the sequence and readings: F-A22 with F-A32's table (D55);
  - the scoring sets: D55 Q-F2-1;
  - the order: D55 Q-F2-2.
  Each is written. **The numbers are left to the freeze**, which is a script with a sha256, a rule for every number,
  tests at each rule's edge, and an exit code for every outcome.
- **Two things remain, and neither needs a round:**
  - Q-F4-1, with both answers written: yes leaves no-branch reads out; no trains them under D54 as written. The freeze
    numbers barely move either way, because such reads add no drawn voxel, run or gap;
  - the swe spec of §7, which is a build, not a choice.
- **What would reopen stage 2:** a STOP from the freeze; a lead answer that changes D54 or D55; or a J1F-2 failure.
  The last is F-A23's 1.5 × and the Q-F2-2 revisit.

## 9. Proposed amendments

| # | Amendment |
|---|---|
| P-r4-1 | F-A21's "Extended reads" is replaced by §3.1's table (D54). No extended-read set exists. Ticks are ignored. Ignore is 19 on disk for J1F-2's 19 labels |
| P-r4-2 | J1F-2's band, L1r run, L2d gap, theft line (L1r and K1r) and per-class trainability are the outputs of `experiments/Bridge/j1f_r4/j1f2_freeze.py` at the sha256 the lead posts, by the rules in §3.3 and §3.4. J1F-2 pins that json's sha256 and the trainable-reads sha256 |
| P-r4-3 | F-A23's inter-read floor is pooled over both directions, on double-read patients with the class in either read; presence agreement is reported |
| P-r4-4 | J1F-2's look follows F-A32's table with F2, T2 and T2_L (§4); D55 Q-F2-3 holds for stage 2 |
| P-r4-5 | D55 Q-F2-1: the sealed pool's extended classes are a D27 report only. The freeze refuses sealed reads and acceptance exports |
| P-r4-6 | D55 Q-F2-2: no J1F-B. Fir's order is a1, a2, J1F-2 |
| P-r4-7 | 4-class pool reads' background in the band takes ImageCAS-X's band sets (not D54; the same untraced-septal reason) |
| P-r4-8 | `src/segqueue14/labels.py` is not edited until J1F-2's look; any D54 tidy-up goes elsewhere |
| P-r4-9 | Stage 2's shape and procedure are ruled converged; only the freeze's numbers remain |

## 10. Question for the lead

**Q-F4-1. May an extended read in which no branch class is drawn at all be left out of stage-2 training as a whole
read?**
- **The problem:** under D54 such a read teaches all 14 branches as absent. D1 is present in 98 % of hearts. These
  reads come from flagged cases read as four classes, from old tick-only reads, and from readers who drew nothing.
- **Recommended: yes.** The read is left out whole and counted. It is not reinterpreted, and every other extended
  read follows D54 as written. The cost is a few negatives in a pool where negatives are plentiful.
- "No" is also written: such reads train under D54. The freeze's under-drawn report then flags D1 and PDA if they
  are common.

## 11. Evidence and code (`experiments/Bridge/j1f_r4/`)

| File | What |
|---|---|
| `j1f2_freeze.py` | The freeze script (§6), with its `selftest` |
| `test_freeze.py`, `test_freeze.out` | ⟨TESTS⟩ checks: refusals, the rules at their edges, the two stand-in exports against k-d-tree truth |
| `standin_freeze_summary.json` | The freeze json of each stand-in export |
| `make_standins.py` | 620-derived stand-in exports (SegQueue14 layout, synthetic stage-2 branches of known geometry) |
| `fetch_subset.py` | The 40 hash-chosen 620 training segmentations, pinned to the 620 |
| `dice_terms_d54.py`, `dice_terms_d54.json`, `dice_terms_d54.out` | Foxtrot's `dice_terms.case`, D47 Q3 vs D54 |

Experiments note: [[Bridge - Under D54 an extended read is a full label, and one script freezes every J1F-2 number from the reads]].
