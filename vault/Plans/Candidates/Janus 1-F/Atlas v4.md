---
tags: [plans, candidate, janus-1f, branches, partial-labels, fir, round4, stage2, freeze, D27, D45, D47, D54, D55]
author: Atlas
track: 1-F
round: 4
version: 4
updated: 2026-11-28
issue: christianGRogers/Asclepius#303
---

# Atlas v4 (Janus 1-F): under D54 an extended read is a full label, the J1F-2 freeze is one script, and stage 2's shape and procedure can be ruled converged

## 0. In one paragraph

The plan in force is Delta v3 as amended (F-A1 to F-A36), with D54 and D55. **Stage 1 (J1F-A) is not reopened.**
D54 and D55 change nothing in it (§2). This round is about **stage 2 (J1F-2)**. Code is in
`experiments/Atlas/j1f_r4/`. The write-up is
[[Atlas - Janus 1-F round 4, under D54 an extended read is a full label and the J1F-2 freeze is one script]].

**What I found:**
1. **D54 turns every extended pool read into a full label.** An undrawn branch is absent, so no voxel of an extended
   read is left ambiguous. The parent is a singleton, background is `{bg}`, and the drawn branch is `{branch}`.
   Overlaps follow D47 Q4 and D40 as before.
   - The marginal CE and leaf-Dice are then needed only on ImageCAS-X background in the band, and on four-class pool
     reads.
   - **This closes a loss hole** that the "complete" rule had left open (§3.2). I re-ran Foxtrot's round-2 loss check
     on 10 training cases.
     - Under the old rule, painting S1 at 0.5 over the whole LAD group cost nothing: CE 0.00076, against 0.00069 for a
       correct S1. The LAD group had no Dice term (leaf loss 1.0, no target).
     - **Under D54 the same sprawl costs 3.6× the CE (0.00282), and the LAD group's leaf-Dice comes back (0.45 against
       0.08).**
   - So training now penalises theft on the pool's own reads, not only at the look.
2. **Every rule that depended on complete groups is listed and replaced** (§3.1). There are nine places:
   - F-A11's and F-A21's extended-read rows, and master plan §4;
   - Foxtrot's `dice_terms.py` (re-run under D54) and Crucible's `dice_toy.py`;
   - the export's `completeGroups` (recorded, ignored);
   - the band's "≥ 10 reads per group";
   - the floor's patient set;
   - `labels.py`'s instruction text, whose sha256 the scorer of record pins.
3. **The J1F-2 freeze is one frozen script**, `j1f2_freeze.py` (§5). From a SegQueue14 export, it computes:
   - the band per class group;
   - L1r's run length, L2d's gap and K1r's line, each by a rule written before any read is seen;
   - the read counts per class and source;
   - the inter-read floor, by the scorer of record's definitions;
   - the D35 tiers.
   - **It refuses a sealed-pool patient before it opens any file** (D55 Q-F2-1). It also refuses an
     `--acceptance-scoring` export, a `--four-class` export and the annotator benchmark. It runs on CPU and prints a
     sha256 for the lead to post.
   - **Tested** on a 60-case stand-in export built from ImageCAS-X *training* labels: 120 reads, 55 of them extended
     pairs, with D2, OM2 and PLB standing in for S1, SN and RMA. It also passes 6 of 6 whole-export refusals. A
     "thief" export (10 mm of LAD painted S1) moves K1r's statistic from 0.000 to 0.050–0.095 and its line to STOP
     (§5.3).
4. **D55 is written into the stage-2 plan** (§4):
   - the sealed pool is read in extended mode but never reaches the freeze (Q-F2-1);
   - there is no J1F-B, and the 1.5× near-miss rule is a flag of the script (Q-F2-2);
   - J1F-2's look carries F-A32's T_L logic. J1F-2 always fine-tunes a1's network, and its vessels are chosen by a
     table like F-A32's (P-r4-3).

**Converged?** **Yes for stage 2's shape and procedure** (§7). Every rule is code or a table with an outcome for
every case. Each number that is left (the four band widths, τ₁, τ₂ and the L1r/K1r line) is the output of a pinned
script with a stop rule, run once before J1F-2 is submitted. The rest are build items for `role:swe`: the stage-2
trainer, a stage-2 scorer layer and J1F-2's decode. Their definitions are fixed here.

## 1. Inputs, independence, data

**Binding:**
- D45 to D55; D54 and D55 above all;
- F-A1 to F-A36 ([[Janus 1-F Round 1]], [[Janus 1-F Round 2]], [[Janus 1-F Round 3]]);
- the master plan of the track.

**Independence.** I did not read any other round-4 candidate or any `exp/j1f-r4-*` branch. My own v3 was read.

**Data read:**
- The ImageCAS-X segmentations of **60 of the 620 D45 training cases**, the 60 with the smallest
  sha256(`asclepius-j1f-r4-atlas-standin:` + id). `fetch_subset.py` asserts the 620's pin `1350cb1f…1152` and fetches
  no other member. `make_standins.py` re-asserts that every file is a training case.
- **Names only:** the seal file, the A34 reserve and the Round-10 D35 lists, for the refusal tests. No pool volume or
  read was opened.

**Not read:**
- no locked-100 label (not even counts this round);
- no sealed ImageCAS-X test case, quality-0 case or D60 CT;
- no TotalSegmentator twin;
- no pool read, sealed or not;
- no model output.

Nothing ran on Fir, SciNet or Trillium.

## 2. D54 and D55 against stage 1: nothing changes

| Decision | Does it touch J1F-A? | Why |
|---|---|---|
| D54 (undrawn = absent) | **No** | J1F-A trains on Dataset 719, the 620 ImageCAS-X cases only (F-A29). No pool read enters stage 1, and ImageCAS-X has no extended read |
| D55 Q-F2-1 yes | No | The sealed pool's extended classes are a report in D27's look; J1F-A never sees the pool |
| D55 Q-F2-2 no | No | J1F-B was never in J1F-A |
| D55 Q-F2-3 yes | Already ruled | F-A32 is in force: `collect` applies its table if 1-L is adopted and its maps are on Fir before the ledger opens |
| D55 Q-F3-1 to Q-F3-3 | Already ruled | The 14-day window, a1 and a2 together, the swe build before the purge |

**One stage-1 risk that D54's panel change creates.** The scorer of record pins `src/segqueue14/labels.py` by sha256
(`5f69b5be…0a4b`, F-A28 and F-A36). That file still carries the annotator sentence "Tick a branch group complete when
you have looked for every branch in it" (`EXTENDED_INSTRUCTIONS`), which D54 makes untrue.
- An swe who deletes it for D54 changes the hash.
- `collect` would then refuse at the look.
- The pin is still intact on `dev` today (re-checked: `5f69b5be…0a4b`).
- **Proposed (P-r4-6):** until J1F-A's `collect` has run, no edit to `labels.py`, not even to its text. The panel
  already shows no ticks (D54, `01bf717`), so the stale sentence costs nothing meanwhile. If it must change sooner, a
  ruling re-pins the hash before `collect`, as F-A36 requires, after checking that `collapse_to_four` and
  `assign_contact_branches` are byte-identical.

## 3. D54 in stage 2

### 3.1 Every rule that depended on complete groups

| # | Where | As written | Under D54 |
|---|---|---|---|
| 1 | F-A11, "Label sets by source": "an extended read: drawn classes are singletons; parents depend on Q3's flag" | parent `{parent ∪ children}` unless ticked | **every voxel of an extended read is a singleton** (§3.2) |
| 2 | F-A21, "Extended reads", D47 Q3 line | "a complete group's parent is a singleton; an unmarked group's parent is {parent ∪ children}" | deleted; the D47 Q4 line (child over its own parent is the child; other overlaps ignore) stays |
| 3 | Master plan §4, "Extended reads" bullet | as F-A21 | as row 2 |
| 4 | `experiments/Foxtrot/j1f_r2/dice_terms.py` | its extended sample has no flag: LAD-group voxels `{LAD-group, S1}`, the ImageCAS-X band on background | **re-run under D54**: `dice_terms_d54.py` (§3.2). The round-2 file stays as the record of the old rule |
| 5 | `experiments/Crucible/j1f_r2/dice_toy.py`, "EXT, complete: every voxel singleton" | one of two cases | now the **only** extended case; its "incomplete" variant no longer arises |
| 6 | SegQueue14 export, `read.json` `completeGroups` and the manifest's `complete_groups` (D47 Q3) | "an empty class in a group listed there means absent" | **recorded and ignored.** A tick changes no label. The freeze prints `ticked_reads` only |
| 7 | F-A21's band re-set, "≥ 10 reads per group" | read by some as reads with the group *complete* | **≥ 10 trainable extended reads with a class of the group drawn** |
| 8 | F-A23's floor, "patients with two extended reads" | an absent class in an unmarked group was "not looked for", so no disagreement | **an absent class is a reading.** A branch drawn by one reader and not the other is a miss, through naming: the second reader's parent covers it |
| 9 | `src/segqueue14/labels.py` `EXTENDED_INSTRUCTIONS` ("Tick a branch group complete …") | annotator text | untrue now, but **left as is** until J1F-A's `collect` (P-r4-6, §2) |

No other script in `experiments/*/j1f*` reads `completeGroups` (searched: `grep -ri complete`).

### 3.2 Stage-2 labels and loss

**The stage-2 training label of every voxel (P-r4-1, replacing F-A11's table and F-A21's extended-read line):**

| Source | Voxel | Label set |
|---|---|---|
| ImageCAS-X 620 | traced class (stage-1 converter, F-A28) | `{class}` |
| ImageCAS-X 620 | background inside a host's band | F-A21's table, with the frozen widths (§5): LAD and D1–D3 → `{bg, S1, S2, S3}`; RCA → `{bg, RMA}`; proximal RCA → `{bg, RMA, SN, Conus}`; proximal LCx → `{bg, SN}` |
| ImageCAS-X 620 | background elsewhere | `{bg}` |
| ImageCAS-X 620 | converter's 255 | ignore (13 on disk, F-A29) |
| **Extended pool read (trainable), D54** | a drawn class, alone | `{class}` |
| | a branch over one of its own parents only (D47 Q4) | `{branch}` |
| | any other overlap (D40) | ignore |
| | **any other voxel (undrawn = absent)** | `{bg}`. A parent voxel is `{parent}` |
| | a voxel marked only as a material | `{bg}` (materials dropped first, as D46 Q8) |
| Four-class pool read (trainable), unchanged | a parent's voxel | `{parent ∪ its stage-1 and stage-2 children}` (F-A11) |
| | background inside a host's band | as ImageCAS-X background: a four-class read traces no branch beyond the seed (D47 Q7 asks only extended readers) |
| | background elsewhere | `{bg}` |

The own parents are D47 Q1's:
- D1–D3 and S1–S3 → LAD;
- OM1, OM2 → LCx;
- Ramus → LCx or LM;
- Conus, RMA → RCA;
- SN, PDA, PLB → LCx or RCA, the vessel they leave.

`read_labels` and `training_sets_d54` in `j1f2_freeze.py` are the reference code. The self-test checks that a child
over its parent becomes the child, a three-way overlap becomes ignore, a material is dropped, every extended-read set is
a singleton, and a four-class LAD's set holds S1–S3.

**The loss is unchanged in form:**
- marginal CE plus leaf-Dice per sample, smooth 1e-5, `batch_dice: false` asserted (F-A21);
- on an extended read every set is a singleton, so marginal CE **is** CE and leaf-Dice **is** soft Dice;
- the machinery is needed only where ImageCAS-X or a four-class read leaves a branch untraced.

**Evidence: Foxtrot's loss check re-run under D54** (`dice_terms_d54.py` → `results/dice_terms_d54.{json,txt}`).
- Setup: the first 10 of the 60 training cases; a 64 mm cube on the proximal LAD; a 30 mm synthetic septal of
  r = 0.6 mm.
- Both rules are scored on the same cases, with Foxtrot's own `terms` unchanged.
- Mean over 10 cases; leaf-Dice loss per channel, then CE.

| Scenario on the extended read | Old rule (no flag): LAD-group / S1 leaf, CE | **D54**: LAD-group / S1 leaf, CE |
|---|---|---|
| A, right (tube → S1) | 1.000 / 0.342, 0.00069 | 0.079 / 0.479, 0.00079 |
| B, miss (tube → LAD group) | 1.000 / 0.972, 0.00117 | 0.102 / 0.980, 0.00127 |
| **C, sprawl (S1 at 0.5 on every LAD-group voxel)** | **1.000 / 0.342, 0.00076** (indistinguishable from A) | **0.450 / 0.852, 0.00282** (3.6× A's CE) |
| D, intrude (OM1 at 0.5 on the LAD group) | 1.000 / 0.342, 0.00259 | 0.450 / 0.502, 0.00282 |

- **Under the old rule an extended read could not teach "this is LAD, not a septal".** The LAD group had no Dice
  target (loss 1.0, a constant). Sprawl cost +0.00007 of CE, under 10 % of A's.
- **Under D54 sprawl costs four times A's CE, and both Dice terms see it.**
- A miss (B) costs the same under both rules: the tube is a singleton in both.
- So D54 trains against L1r's failure mode on the pool's own reads, not only at the look.

### 3.3 The band and the read thresholds

**The band (F-A21) is still a device for ImageCAS-X and four-class background.** D54 does not touch ImageCAS-X, so
the band's role, its sets and its clamp are unchanged. Two things change:
- **What it is measured on.** The trainable extended reads with a class of the group drawn (row 7 of §3.1). Under D54
  every extended read *labels* the group, but only reads that draw it tell us how far it reaches.
- **How each read counts.** The width is the 95th percentile of the drawn voxels' distance from the host, **each read
  weighted equally** (its 201-point quantile curve, resampled). That way one large read cannot set a band. It is
  rounded up to 0.5 mm, clamped to [8, 25] mm, and needs ≥ 10 reads, otherwise the provisional 15 mm stays.

**The class groups and their hosts:**

| Group | Classes | Host (distance from) |
|---|---|---|
| LAD | S1, S2, S3 | LAD ∪ D1–D3 |
| RCA | RMA | RCA |
| proximal RCA | Conus, SN off the RCA | RCA |
| proximal LCx | SN off the LCx | LM ∪ LCx |

SN goes to whichever of LCx and RCA it is nearer to (D47 Q1).

**The read thresholds (F-A23), under D54:**
- **Positives still decide.** A class trains only with ≥ 30 trainable patients **with the class drawn** in ≥ 1 extended
  read, from ≥ 3 sources with ≥ 5 such patients each.
  - "Trainable" means not sealed, not in any Round-10 D35 draw, not in the A34 reserve, and nothing else
    `janusm.guard` holds out.
  - D54 adds **negatives for free**: every other trainable extended read is a confirmed absence. The freeze prints
    them (`patients_extended_absent`). They need no threshold of their own.
- **The floor now measures looking as well as tracing.** On trainable patients with two extended reads of one volume
  and the class drawn by at least one reader, the floor pools detection × naming over both directions, by the scorer
  of record's definitions:
  - detection: ≥ 50 % of the centreline within 1.5 mm of the other read's vessel;
  - naming: strict majority of the covered points.
  - It must be ≥ 0.6 on ≥ 10 patients.
  - Under D54 a reader who never draws, say, the conus labels it absent everywhere, and the other reader's conus
    then counts as "named parent". **The floor is D54's safety net.** A class that annotators do not use consistently
    fails it and stays folded.
  - Presence agreement over all double-read patients is printed beside it, as a report. D54 makes absence a reading,
    so it is now meaningful.
- **The 1.5× near-miss rule (Q-F2-2 no; F-A23)** is the freeze's `--raised` flag. A class that failed a J1F-2 look
  with its count within 1.5× of 30 needs 45 patients next time.
- **D35 tiers (F-A22 S)** come from counts, before any D35 prediction exists: D35 patients (A33's list) with the class
  drawn in ≥ 1 extended read. Decide at ≥ 30, report at ≥ 20, otherwise counts only.

**The D54 QC (report only, P-r4-2).** The freeze prints two things:
- `branchless_extended_trainable_reads`: extended reads with no branch drawn at all, for example a read flagged for
  extended mode (D47 Q6) or with plaque painted but no branch separated;
- the share of extended reads that leave out D1, D2, OM1, OM2, PDA or PLB.

Under D54 a branchless read teaches "no diagonal, all LAD". ImageCAS-X has D1 in 97 of the 100 locked cases, so a high
D1-absent share in extended reads is a reader signal, not anatomy. Whether such reads are trained is the lead's
(Q-F4-1). Until the lead answers, D54 is applied as written.

### 3.4 L1r, L2d and K1r under D54

The three gates measure the model on the locked 100 (L1r, L2d) and on the fit-check 20 (K1r). All of these are
ImageCAS-X cases, so **D54 does not change any definition** (F-A30 stands). It changes two things.
1. **The training signal behind them.** Under D54 the model is penalised for painting stage-2 classes over a parent
   (§3.2, scenario C) or into an extended read's background. So L1r and K1r should fire less for a good model. The
   lines stay as guards.
2. **What the re-check measures on reads.** Round 3 (§5 item 2) asks that 3 mm, 30 mm and 0.02 be re-checked on the
   first extended reads. Under D54 a read is a full label, so a read *is* a correct model's output for its own case,
   and each re-check is that read scored as a prediction:
   - **τ₁ (L1r's run length):** for each drawn stage-2 piece, the longest 26-connected run of its parent group's own
     centreline (the group as drawn, whole, D39) inside the piece dilated by one voxel. That is a correct ostium with
     one voxel of bleed.
     - τ₁ = the 99th percentile over pieces, rounded up to 0.5 mm, never below 3 mm.
     - **Above 6 mm: STOP** (the round-3 thief paints 10 mm).
     - With < 30 pieces, 3 mm stays.
   - **τ₂ (L2d's gap):** for each stage-2 26-component (≥ 20 voxels), the distance from its nearest voxel to every
     other drawn coronary voxel. That is the gap a reader left.
     - τ₂ = the smallest of 30, 35, 40, 45 and 50 mm at which ≤ 1 % of reads have a component beyond it.
     - None: **STOP**.
     - With < 30 reads, 30 mm stays.
     - At 1 %, a model that leaves reader-like gaps expects 1 dirty case in 100, far from L2d's 6.
   - **The L1r/K1r line (one statistic, F-A30):** the pooled share of each parent group's centreline inside stage-2
     pieces (one-voxel bleed) in runs > τ₁, with its one-sided 1.25 % upper bound by patient bootstrap. The worst of
     LAD, LCx and RCA is taken.
     - If that bound is ≤ 0.01 (half the line), 0.02 stays.
     - Otherwise the line is 2 × the bound rounded up to 0.005.
     - **Above 0.04: STOP.**
   - Septal length (Round 3 §7, "longer than 40 mm") no longer decides anything. L2d measures a gap, not a length
     (F-A30). The freeze writes each piece's length to `rows.jsonl`.

**Not re-set here:** the proximal windows (30 mm along the RCA, 20 mm from the LM; F-A21). Reads give no ostium
without an aorta. A conus or SN that arises beyond them gets `{bg}` on ImageCAS-X background there, which is the
conservative error. Listed in §9.

### 3.5 The read counts each class needs, in one place

| Need | Line | Source of the count |
|---|---|---|
| Train a class | ≥ 30 trainable patients drawn (45 after a near miss) **and** ≥ 3 sources with ≥ 5 **and** the floor ≥ 0.6 on ≥ 10 double-read patients | freeze `classes.<c>.train` |
| Re-set a band group | ≥ 10 trainable extended reads with the group drawn | `band_detail.<g>.reads` |
| Re-set τ₁ | ≥ 30 drawn stage-2 pieces | `tau_L1_detail.pieces` |
| Re-set τ₂ | ≥ 30 trainable extended reads | `tau_L2_detail.reads` |
| D35 decide / report | ≥ 30 / ≥ 20 D35 patients drawn | `classes.<c>.d35_tier` |
| Ship unfolded | decide tier and L1r, L2d pass on the look | J1F-2 `collect` |

## 4. D55 in stage 2: the plan as it now stands

### 4.1 Order on Fir (Q-F2-2 no)

1. a1, then a2 (report only, D55 Q-F3-2), then J1F-A's `collect` (one look; F-A32's table).
2. **No J1F-B.**
3. **J1F-2 only when the freeze says at least one class trains** (`classes.<c>.train` true). If no class trains,
   J1F-2 is not submitted, and the freeze is re-run on the next export, each time with a new hash.
4. Revisit Job B only if a J1F-2 class fails with its count within 1.5× of its threshold (D55). The freeze's
   `--raised` makes the next count 45.

### 4.2 The sealed pool (Q-F2-1 yes)

- The 150 sealed patients are read in extended mode like any case (D23).
- **Their reads never reach the freeze.** The default export leaves them out. `j1f2_freeze.py` refuses, exit 3,
  before any file is opened, if a sealed name appears, an `__r2` replica of one, or an export with
  `--acceptance-scoring` (§5.3).
- They are scored once, inside D27's single acceptance look, as a report: per class, n, recall, naming and presence
  agreement with CI, by the scorer of record. Under D54 presence agreement is now meaningful there too. No J1F-2
  number, band, threshold or tier uses them.

### 4.3 J1F-2's recipe

- **Start: a1's network**, the 1-F network trained in J1F-A, whatever reading shipped (F, T or T_L).
  - New heads by parent copy: S1–S3 ← LAD; SN, Conus, RMA ← RCA.
  - The 13 stage-1 heads are a1's.
- **Data:**
  - the 620;
  - the trainable extended reads;
  - the trainable four-class reads;
  - every set as in §3.2;
  - only the classes the freeze marks `train`. The others stay folded into their parent in every label (an S2 that
    does not train is LAD in every read).
- **Loss:** §3.2 (F-A21's form).
- **During training: K1r** at each fit check, on the fit-check 20, at the frozen τ₁ and line. Over the line at the
  last check writes `LEAK`, and the PM may cancel.
- **Decode, J1F-2:**
  - F2 is the hierarchical decode over the 19 classes;
  - G2 holds three uint8 name maps, the argmax within each set:
    - {LAD, D1, D2, D3, S1, S2, S3};
    - {LCx, OM1, OM2, Ramus, PDA, PLB, SN};
    - {RCA, PDA, PLB, SN, Conus, RMA}.
  - As F-A31, the chunk's npz is deleted after decode.

### 4.4 J1F-2's look under F-A32 (P-r4-3)

**The problem.** F-A22 compares J1F-2 with "the shipped stage-1 model". After F-A32 that may be:
- **F**: a1's own vessels;
- **T**: Janus 0's vessels with a1's names;
- **T_L**: 1-L's vessels with a1's names.

Whichever it is, J1F-2 is a new a1-network, so its own vessels (F2) are new and must be checked against what shipped.

**The vessel source s** is the source of the shipped stage-1 vessels: a1, Janus 0 or 1-L. It is written in the looks
ledger at J1F-2's submission. **1-L counts** if it is adopted and its 100 maps are on Fir before J1F-2's `collect`
opens the ledger. A later 1-L is a report, as in F-A32.

The readings of J1F-2's one prediction, pre-registered in the ledger:
- **F2**, its own;
- **R2_s = G2 selected by s's territory map** when s ≠ a1 (vessels bit-equal to s, asserted);
- **R2_L = G2 selected by 1-L's map** when 1-L counts and s ≠ 1-L.

| V′ (F2 vs s, one-sided 1.25 %) | V_L′ (F2 vs 1-L, only if 1-L counts and s ≠ 1-L) | J1F-2's vessels | B′ and L1r, L2d, S read on |
|---|---|---|---|
| pass | pass, or not applicable | F2's own | F2 |
| pass | fail | 1-L's | R2_L |
| fail | — | 1-L's if 1-L counts, else s's | R2_L or R2_s |

**Then:**
- **B′** on the chosen reading: every class that shipped unfolded in stage 1 still passes its F-A27 lines. If B′
  fails, **J1F-2 is not adopted** and the stage-1 model stays.
- **L1r, L2d** (frozen τ₁, τ₂, line) and **S** (D35 tiers, from the freeze) on the chosen reading. A failing class
  ships folded.
- When s = a1 and 1-L does not count, the table is F-A22 as ruled, except for one change. **A V′ failure no longer
  discards J1F-2's branches.** They ship on s's vessels (R2_s), exactly as T saved stage 1's branches in F-A19.
  Because R2_s's vessels are bit-equal to what shipped, no vessel can regress.
- **It is one look.** V′ and V_L′ choose among readings named before anything is scored, as in F-A32. The track's
  budget of two looks is unchanged.
- Code: the table is `verdict.py`'s, with F2 and R2 in place of F and T. The swe ports it into J1F-2's `collect`.

### 4.5 The stage-2 build (`role:swe`, after this round's ruling)

1. The stage-2 trainer: the sets of §3.2. Its CPU tests are F-A21's three, plus three for D54:
   - an extended read's sets are all singletons, so marginal CE equals CE and leaf-Dice equals Dice;
   - a `completeGroups` tick changes no label;
   - an empty branch channel in an extended read is a negative.
2. `j1f2_freeze.py`, copied byte-identical, and its output, committed as `configs/janus1/j1f2_freeze.json` with its
   sha256 before submission.
3. A stage-2 scorer layer, pinned, over the scorer of record. It adds values 13–18 and L1r, L2d, S and the reports
   (literal L1, L2, K1; K3). Its definitions are F-A30's with τ₁, τ₂ and the line read from the freeze file, never
   typed. `read_labels`, `geometry` and `pair_agreement` here are its reference.
4. J1F-2's decode (F2, G2) and `collect` (§4.4).

## 5. The freeze procedure

### 5.1 The script

`experiments/Atlas/j1f_r4/j1f2_freeze.py`. Run `python j1f2_freeze.py selftest`; the exact sha256 goes in the PR
description.
- **Pins.** It imports the scorer of record by sha256 (`5221032f…2e5b`), which pins `tf1.py` and `labels.py` itself.
  It loads the D27 seal through `segtrain.pool_seal`, which checks its hash. It reads A33's D35 list by sha256
  (`1a75fe41…66b1`) and `janusm.guard` for the reserve and every Round-10 draw.
- **Order.** It reads the manifest and refuses an acceptance-mode or four-class export. It classifies every read
  directory **by name**:
  - sealed or benchmark → refuse;
  - A33 D35 → tier counts only;
  - held out by the guard → not opened, counted by reason;
  - else trainable.
  - Only then does it open a file.
- **Geometry** (band, τ₁, τ₂, line) leaves out D29's anomalous strata (ImageCHD, ImageALCAPA) and the header-spacing
  sets (ImageALCAPA, HOCMvalvesSeg, CCA200-HF). Their millimetres are not trusted. They still count toward the read
  counts.
- **Outputs:**
  - `j1f2_freeze.json`: numbers and counts only, no case names. Post it with its sha256;
  - `excluded.json`: counts by reason;
  - `rows.jsonl`: per read. It stays with the lead.
- **Exit codes:** 0 FROZEN, 2 STOP (a number out of range: the PM), 3 REFUSED.
- **Every rule is a module constant**, so the script's hash freezes the rules:
  - `BAND_Q`, `BAND_CLAMP`, `TAU1_*`, `TAU2_*`, `LINE1_*`;
  - `TRAIN_PATIENTS`, `RAISE`, `SRC_*`, `FLOOR*`, `TIER_*`;
  - `NBOOT`, `BOOT_SEED`.

### 5.2 The exact commands (the lead's)

**1. On janus (the Girder host):** the default export of each read's own classes, both reads. Sealed reads are left
out by default. Do not pass `--four-class`, `--include-unreviewed` or `--acceptance-scoring`.

```sh
segqueue14-export --out /srv/segqueue14/export-j1f2 --replicas all
rsync -a --exclude 'ct.nii.gz' /srv/segqueue14/export-j1f2/ fir.alliancecan.ca:scratch/j1f2/export/
```

**2. On Fir** (login node, then one CPU job on `def-aso22`, 0 GPU-h):

```sh
module load StdEnv/2023 python/3.11.5
source $HOME/icx14-venv/bin/activate
R=$SCRATCH/asclepius/repo; W=$SCRATCH/j1f2
git -C $R fetch origin dev && git -C $R checkout dev && git -C $R pull --ff-only
python $R/experiments/Atlas/j1f_r4/j1f2_freeze.py selftest          # "j1f2_freeze selftest ok"
sha256sum $R/experiments/Atlas/j1f_r4/j1f2_freeze.py                # must equal the ruled hash
srun --account=def-aso22 --time=3:00:00 --cpus-per-task=16 --mem=64G \
  python $R/experiments/Atlas/j1f_r4/j1f2_freeze.py $W/export $W/freeze --np 16
echo "exit $?"; sha256sum $W/freeze/j1f2_freeze.json
```

- After a J1F-2 near miss, append `--raised <class>[,<class>]` to the `srun` line.
- **Send back on #303:** `j1f2_freeze.json`, its sha256, `excluded.json` and the exit code. **Never send
  `rows.jsonl`**, any mask or any case list.
- Exit 3 means the export held a sealed read: export again with the command above.
- Exit 2 goes to the PM.

**Cost:** CPU only. The stand-in run took 2.6 min per extended read pair on one core here, so a 300-read export on
16 cores should take well under the hour asked.

### 5.3 Tests on stand-ins

**The stand-in export** (`make_standins.py`): 60 ImageCAS-X training cases written in SegQueue14's export layout
(`<case>/segmentations/<class>.nii.gz`, `read.json` with no ticks, `manifest.json`). The first 5 cases are four-class
reads; the other 55 are extended.
- **Stand-ins for the untraced classes:** D2 → S1, OM2 → SN off the LCx, a PLB touching the RCA → RMA.
- **Each child is drawn over its parent** at the junction (D47 Q4).
- **A second read `__r2` per case:** each branch piece is dropped into its parent with p = 0.10 (under D54, a miss),
  and each class grows by one voxel with p = 0.30.
- **Five fake sources.** The names cannot collide with a pool name.

**Results** (`results/freeze_standin_normal.out`, `results/standin_normal_freeze.json`):

FREEZE_NORMAL_TABLE

**What the run shows:**
- **The band clamps at the top.** D2 and the RCA-side PLB reach far from their hosts, so their q95 is above 25 mm.
  The proximal-RCA group has no stand-in, so it keeps 15 mm with "provisional (0 reads)". The script picks the rule
  outcome per group.
- **τ₁** lands just above 3 mm: a one-voxel bleed at the junction of a 0.3–0.4 mm-voxel ImageCAS-X tree gives runs up
  to ≈ 3.5 mm. This is the case Round 3 §7 foresaw (ostia longer than 3 mm), and the rule handles it.
- **The floor** recovers the simulated second reader. Dropping 10 % of pieces into the parent gives detection ≈ 1 and
  naming ≈ 0.9.
- **The counts** fail on purpose. 55 patients spread over 5 fake sources reach ≥ 5 per source in some groups only,
  and the train flags follow exactly.

**The thief** (`results/freeze_standin_thief.out`): 20 cases whose first read also paints the 10 mm of LAD centreline
nearest the S1 stand-in's origin as S1.

FREEZE_THIEF_TABLE

**Refusals** (`test_refusals.py` → `results/test_refusals.out`): **6 of 6 pass**.
1. A sealed volume's name beside a stand-in exits 3, and an `open()` spy shows **0 files of the export opened**.
2. Its `__r2` replica alone exits 3.
3. An acceptance-mode manifest exits 3.
4. A four-class export exits 3.
5. `--no-guard` on a pool name exits 3.
6. The annotator benchmark exits 3.

The sealed directories hold stand-in masks only. Only the seal file's names were used.

## 6. Round 3 §5, item by item

| Item | Answer | Where |
|---|---|---|
| 1. Re-set the band per class group from trainable extended reads, posted with its sha256 | `j1f2_freeze.py` (rule of F-A21; equal weight per read; D54's reading of "≥ 10 reads") | §3.3, §5 |
| 2. Re-check L1r's 3 mm, L2d's 30 mm, K1r's 0.02 | Each re-set by a written rule with a STOP, on reads scored as a correct model's output | §3.4, §5 |
| 3. Read counts and the inter-read floor with the scorer of record | `classes.<c>`: positives, sources, floor (scorer's definitions, both directions), presence agreement, tier | §3.3, §3.5 |
| 4. Apply Q-F2-1's and Q-F2-2's answers | Sealed reads refused by the freeze, scored only in D27's look; no J1F-B; `--raised` | §4.1, §4.2 |
| 5. Re-derive F-A27's lines if a measured second-reader branch study exists | **None exists**, so F-A27 stands. The pool's double reads do not qualify: F-A27 is calibrated to ImageCAS-X's own second analyst under ImageCAS-X's convention (D7). A pool reader's D1 is not that measurement | — |
| D54 in stage 2 | Nine places replaced; labels, loss, band, thresholds, gates, counts | §3 |
| D55 in stage 2 | Plan as it stands, with F-A32 carried into J1F-2's look | §4 |
| The freeze procedure | Script, commands, stand-in tests, refusals | §5 |
| Convergence | Yes, for shape and procedure | §7 |

## 7. Convergence

**Stage 2's shape and procedure can be ruled converged now.**

**What is fixed and needs no further round:**
- the label set of every voxel of every source (§3.2), with reference code and self-tests;
- the loss (F-A21), heads, start (a1's network) and decode (F2, G2);
- the class groups, the band rule and its clamp;
- the definitions of L1r, L2d and K1r (F-A30) and the rule that sets each of their numbers;
- the read-count rule, the floor and its statistic, the 1.5× rule, the D35 tiers;
- the look: one fixed sequence with F-A32's readings (§4.4), at one-sided 1.25 %, as the second of two looks;
- the data rules: the seal refused, D35 counts only, the reserve and other draws excluded, D29 and spacing-suspect sets
  out of geometry;
- the order on Fir (§4.1).

**What is left, and why it needs no round:**
- **Numbers:** the four band widths, τ₁, τ₂ and the L1r/K1r line. Each is the output of `j1f2_freeze.py` (pinned) on the
  export that exists when J1F-2 is about to be submitted. Each has a stop rule. The freeze is a computation, not a
  choice.
- **Build:** §4.5, by `role:swe`, with its definitions fixed here.

**Conditions** (each a check with a stop rule):
1. The judge fixes `j1f2_freeze.py`'s sha256 in the ruling.
2. The freeze exits 0 and its json and sha256 are posted on #303 before J1F-2 is submitted.
3. At least one class is `train`.
4. The stage-2 trainer's six CPU tests pass on Fir.
5. Q-F4-1 is answered, or D54 is applied as written.

**What could still reopen it:** only an observation in §9's table, for example a STOP from the freeze, or the floor
failing for every class.

## 8. Proposed amendments

| # | Proposal | Replaces |
|---|---|---|
| P-r4-1 | Stage 2's label sets as §3.2: every voxel of an extended read a singleton (D54); D47 Q4 and D40 for overlaps; four-class reads as F-A11 with the band on their background | F-A11's and F-A21's extended-read rows; master plan §4's D47 Q3 bullet |
| P-r4-2 | The band, τ₁, τ₂, the L1r/K1r line, the read counts, the floor and the D35 tiers are the outputs of `j1f2_freeze.py` (rules §3.3–§3.4, constants in the file), with its D54 QC lines printed as reports | F-A21's band re-set, F-A23's counts, F-A30's "re-checked before J1F-2" |
| P-r4-3 | J1F-2 starts from a1's network; its look reads F2, R2_s and R2_L under §4.4's table; a V′ failure ships the branches on s's vessels | F-A22's "failing V′ … not adopted" |
| P-r4-4 | The freeze refuses any sealed name, replica, acceptance-mode or four-class export, before opening a file (D55 Q-F2-1) | Round 3 §3.8's "the band and floor scripts refuse a sealed-pool patient" (now code) |
| P-r4-5 | J1F-2 is submitted only when the freeze marks ≥ 1 class `train`; otherwise the freeze is re-run on the next export | F-A23's "when counts allow" |
| P-r4-6 | No edit to `src/segqueue14/labels.py`, text included, until J1F-A's `collect` has run, or a ruling re-pins it | protects F-A28/F-A36's pin |

## 9. Questions for the lead

**Q-F4-1. An extended read with no branch drawn: all branches absent, or a four-class read for stage 2?**
- **The problem:** D54 makes every undrawn branch absent "in every extended read". A read becomes extended when any
  extended class has work (D53), for example only plaque painted, or when its case is flagged extended mode (D47 Q6).
  Such a read then says the patient has no diagonal and no marginal. ImageCAS-X has D1 in 97 of 100 locked cases.
- **Options:**
  - (a) D54 as written;
  - (b) for stage 2's branch labels only, an extended read with **no** branch class drawn is trained as a four-class
    read (parents `{parent ∪ children}`). Its materials and vessels are unchanged.
- **Recommended: (b).** It touches only reads that drew nothing in any branch, the one case where "not drawn" is
  least likely to mean "looked and absent". The freeze prints how many there are (`branchless_extended_trainable_reads`)
  and the D1/OM1/PDA absent shares, so the lead can see the size first. Until the lead answers, (a) applies.

## 10. Cost

0 GPU-h added. The freeze is one CPU job on `def-aso22` (≤ 3 h, 16 cores, 64 G). J1F-2 stays ≈ 15 GPU-h when counts
allow (F-A22). No J1F-B (D55).

## 11. What would change this plan

| Observation | Then |
|---|---|
| The freeze exits 2 on τ₁ > 6 mm | L1r's run filter cannot separate ostia from theft at that bleed; the PM brings a run-free L1 form (Crucible's nearest-label form) to the next ruling |
| The freeze exits 2 on τ₂ (> 1 % of reads leave a > 50 mm gap) | Readers draw disconnected septals; L2d becomes a report until a ruling |
| The freeze exits 2 on the line (> 0.04) | Reads themselves overlap parents too much; the PM checks D47 Q4 drawing before any J1F-2 |
| `branchless_extended_trainable_reads` is more than 10 % of extended reads, or the D1-absent share is above 20 % | Q-F4-1 becomes urgent before J1F-2 |
| No class reaches `train` for two exports in a row | D35's tiers and the read plan go back to the PM; nothing trains |
| A class fails a J1F-2 look with its count within 1.5× of its threshold | `--raised`; revisit Q-F2-2 (D55) |
| `labels.py`'s sha256 changes before J1F-A's `collect` | P-r4-6: re-pin by ruling, or `collect` refuses |
| Conus or SN origins are found beyond the proximal windows in the first reads (reported by the stage-2 scorer layer on reads with an aorta) | The windows are re-set by the next ruling |

## 12. Evidence

| File | What |
|---|---|
| `experiments/Atlas/j1f_r4/fetch_subset.py` | 60 hash-chosen training labels; asserts the 620's pin |
| `j1f2_freeze.py` | The freeze; `selftest` |
| `make_standins.py` | Stand-in export from training labels |
| `dice_terms_d54.py`, `results/dice_terms_d54.{json,txt}` | Foxtrot's loss check, old rule vs D54 |
| `results/freeze_standin_normal.out`, `results/standin_normal_freeze.json` | Freeze on 60 stand-in cases |
| `results/freeze_standin_thief.out`, `results/standin_thief_freeze.json` | Freeze on 20 thief cases |
| `test_refusals.py`, `results/test_refusals.out` | 6 whole-export refusals |
