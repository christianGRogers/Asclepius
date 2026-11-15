---
tags: [plans, candidate, janus1-F, track-1F, round2, fir, D44, D45, D47, locked100, partial-labels, label-sets, gates, scorer, swe-spec]
author: Delta
track: 1-F
round: 2
version: 2
updated: 2026-11-15
issue: christianGRogers/Asclepius#303
---

# Delta v2 (Janus 1-F): loosen the two branch lines that fail a human-level reader, freeze the branch scorer as code, keep the band at 15 mm, and test the read threshold with the stage-2 trainer itself

## 0. Position

**I hold the track's plan** ([[Master plan - Janus 1-F]], Delta v1 as amended by F-A1 to F-A13). This version answers
every item of [[Janus 1-F Round 1]] §5. It changes nothing the ruling settled except where a measurement below says
so, and each change is listed as a proposed amendment in §13.

**What is new since round 1:**
- **D47.** The lead accepted every round-1 recommendation. For this plan the ones that bite are Q1 (a left-sided
  PDA/PLB is named PDA/PLB and collapses to the vessel it leaves), Q3 (per-group "complete" flags), Q4 (a child drawn
  over its parent trains as the child), Q6 (D35 read in extended mode), Q7 (trace beyond the seed) and Q8/Q9 (a2,
  naming). SegQueue 0.20.0 (#326) already implements Q1's collapse **by face contact, per component, RCA on a tie**.
- **Step T and F0 have not run.** The lead runs them on Fir. §12 says what each result would change. Nothing below
  waits on them except J1F-A itself.

**New evidence this round** (CPU, labels only, code in `experiments/Delta/j1f_r2/`; the 720 non-sealed ImageCAS-X
label files re-fetched with round 1's `fetch_allowed.py`, which skips every sealed case before any byte is read; note: [[Delta - Janus 1-F round 2, the OM2 gate fails a human reader a third of the time, and SegQueue's contact collapse equals ImageCAS-X's origin labels]]):
1. **A simulation of the B gates against a human-level reader** on the locked 100's own reference branches
   (`gate_sim.py`, §1). As ruled, **OM2 fails a human-level reader 36 % of the time.** The other five classes stay
   under 1 %.
2. **The branch scorer as code, with a self-test** (`branch_score.py`, `test_branch_score.py`, §2): 31 of 31 checks
   pass on six training cases.
3. **SegQueue 0.20.0's own contact collapse, run on all 720 ImageCAS-X label maps** (`label_checks.py`, §2.3).
   It reproduces ImageCAS-X's own L-/R- side labels on every voxel: 0 mismatched voxels and 0 fallbacks, over 1 513 PDA/PLB components, 109 of which go to the LCx.
4. **The stage-2 band, measured** on 120 hash-chosen training cases (§4.2).
5. **Shi et al.'s Table 3, re-read** (§7). My round-1 numbers were the wrong rows for the claim I made.

**Independence.** I did not read the other round-2 candidates of this track. I re-read the round-1 candidates
(Atlas, Bridge, Crucible, Foxtrot v1), as the brief asks.

## 1. The gate numbers (item 1)

### 1.1 What the simulation does

`gate_sim.py` draws a second reader **B** against the reference **A** (ImageCAS-X) on the locked 100, 4 000 times:
- **Misses.** Each reference branch of class c is dropped with probability m_c.
- **Extras.** Extra branches are inserted on the LAD and LCx sides at a Poisson rate, at a random rank among the
  siblings.
- **Names are positional on the LAD and LCx sides**, as ImageCAS-X numbers them (round 1, finding 2): B's k-th
  LAD-side branch is D1, D2, D3, then LAD; B's k-th LCx-side branch is OM1, OM2, then LCx. So a dropped D1 renames
  B's D2 as D1, and naming errors arise from detection errors, as they do for humans.
- **PDA and PLB** are not ordinal: dropped with m_c, swapped with each other with probability ε.
- **m_c and the extra rates come from ImageCAS-X Table 1** (re-read this round from the arXiv HTML: n scans with both
  analysts' segment, and agreement over 160 scans). Disagreements are split evenly between misses and extras:
  d_c = 160 (1 − a_c), m_c = (d_c / 2) / (n_c + d_c / 2).

| Class | Table 1 n, agreement | m_c (human) | Locked references (≥ 5 mm, D47 (A)) |
|---|---|---|---|
| D1 | 155, 96.9 % | 0.016 | 97 |
| D2 | 91, 89.4 % | 0.085 | 64 |
| OM1 | 132, 94.4 % | 0.033 | 84 |
| OM2 | 46, 87.5 % | 0.179 | 40 |
| PDA | 150, 98.8 % (R-PDA) | 0.006 | 98 |
| PLB | 147, 96.2 % (R-PLA) | 0.020 | 99 |

The locked counts moved slightly from round 1 (98, 64, 84, 40, 96, 96). Under D47 (A) a left PDA or PLA is a PDA or
PLB, which adds 2 and 3. One D1 has a centreline of 3–5 mm.

**Two calibration notes.**
- **The PDA/PLB swap rate must be small to match Table 1.** At ε = 0.05 the simulated human's PDA agreement is 0.945,
  against Table 1's 0.988. Only ε ≈ 0.01 is consistent. So the human-level runs use ε = 0.01, with 0.02 as a check.
- **The model is slightly optimistic on presence and pessimistic on naming for D1–OM2.** Emergent agreement is 0.01–0.03
  above Table 1, because an extra branch usually renames a sibling rather than adding a class. A reader with 1.5× the
  human miss and extra rates brackets this: its D2 agreement (0.891) matches Table 1's (0.894). Both are reported.

### 1.2 Results

Probability of failing, per class (B1 or B2), and of the verdict "< 4 of 6", for the lines as ruled and as proposed.
All rows: 4 000 draws, seed 0 (`gate_sim.log`).

| Reader | Lines | D1 | D2 | OM1 | OM2 | PDA | PLB | P(< 4 of 6) |
|---|---|---|---|---|---|---|---|---|
| human, ε 0.01 | **as ruled** (R 0.80, N 0.85, margin 0.05) | 0.000 | 0.008 | 0.000 | **0.364** | 0.003 | 0.004 | 0.000 |
| human × 1.5 | as ruled | 0.000 | 0.152 | 0.000 | **0.864** | 0.004 | 0.028 | 0.007 |
| human, ε 0.01 | **proposed** (R 0.75, N 0.80, margin 0.05) | 0.000 | 0.003 | 0.000 | **0.113** | 0.003 | 0.004 | 0.000 |
| human × 1.5 | proposed | 0.000 | 0.086 | 0.000 | 0.617 | 0.004 | 0.028 | 0.002 |
| human, ε 0.01 | looser (R 0.75, N 0.80, margin 0.07) | 0.000 | 0.000 | 0.000 | 0.104 | 0.000 | 0.001 | 0.000 |

As ruled, OM2's failures come from recall (0.275: a human finds 82 % of 40 reference OM2s, and 0.80 sits inside the
noise) and from naming (0.118). D2 is safe at human level and fails 15 % of the time at 1.5× human error.

**Power against bad models** (P(not adopted), i.e. < 4 of 6):

| Bad model | As ruled | Proposed |
|---|---|---|
| Calls every class present in every case | 1.000 | 1.000 |
| Ordinal shift (names off by one) in 25 % of cases | 1.000 | 1.000 |
| Ordinal shift in 15 % of cases (naming ≈ 0.79) | 0.978 | 0.209 |
| Misses 35 % of every branch | 1.000 | 1.000 |
| Misses 20 % of every branch | 1.000 | 0.998 |

- **"Every class everywhere"** passes D1, PDA and PLB (98–99 of 100 locked cases have them) and fails the other three
  on agreement. The 4-of-6 rule is what stops it, as F-A6 intended.
- **The one model the proposal lets through** more often is a model that misnames about 1 branch in 5 on the LAD and
  LCx sides. Expert-to-expert agreement on left-dominant trees is 87.6 % of segments (Cao et al. 2017). I accept
  that: a gate that fails a human 36 % of the time on OM2 is the larger error.

### 1.3 Frozen numbers

- **B1:** detection recall **≥ 0.75**, and presence agreement **≥ Table 1 − 0.05** (D6's margin, unchanged): D1 0.919,
  D2 0.844, OM1 0.894, OM2 0.825, PDA 0.938, PLB 0.912.
- **B2:** naming accuracy **≥ 0.80**.
- **Read rule:** ≥ 4 of the 6 gated classes pass, unchanged.
- **The margin stays 0.05.** Going to 0.07 buys 0.009 on OM2 at human level and costs power against the 20 %-miss
  model (0.984).
- **OM2 is still the weakest gate** (11 % at human level, n = 40). A human-level OM2 that fails is folded into the
  LCx and listed. That is the cost of a fold, not of the verdict.
- **Presence stays at 5 mm, not 3 mm.** On the locked references only three branches have a centreline of 3–5 mm (one
  D1, one R-PDA, one L-PLA; `gate_sim_3mm.log`), so the cut barely moves the reference. On the prediction side, 5 mm
  stops a 3–5 mm fragment from counting as "present".

These numbers are frozen when J1F-A is submitted (F-A6). They are constants in `branch_score.py` (§2), so they are
pinned by its sha256.

## 2. The scorer, frozen by hash (item 2)

### 2.1 The file of record

**`experiments/Delta/j1f_r2/branch_score.py`**, to be copied byte-identical into `trillium/janus1f/lib/`. The
launcher refuses if its sha256 differs from the value posted with the swe issue. The version in this PR has sha256
`fb6295767dcc726899e951daa8a0aa1c733291a4c0821b915c9f702610729840`.

It imports two pinned modules and re-implements neither:
- `segtrain.tf1` (A1c, sha256 `24441cf8…5254`), for the report-only branch tF1;
- `segqueue14.labels.collapse_to_four` (SegQueue 0.20.0, `src/segqueue14/labels.py` sha256 `5f69b5be…0a4b`), for the
  four-class collapse.

### 2.2 The definitions

Per locked case and branch class c. A "branch" is class c in one case, all its pieces together, because ImageCAS-X
names one D1, one D2, … per case.

| Term | Definition |
|---|---|
| Centreline | `skimage` 3-D `skeletonize` of the class mask. Length = skeleton voxels × the geometric-mean voxel side |
| Present | centreline ≥ **5 mm**; the same rule for reference and prediction |
| Detected | a present reference branch with ≥ **50 %** of its centreline voxels within **1.5 mm** (D3) of predicted foreground of **any** class |
| Named | a detected branch whose covered centreline voxels take, **by majority**, the label c from their nearest predicted foreground voxel (Euclidean, true spacing) |
| Recall_c (B1) | detected / present reference branches |
| Agreement_c (B1) | share of the 100 cases where reference and prediction are both present or both absent (Table 1's own measure) |
| Naming_c (B2) | named / detected |
| Branch tF1_c (report) | `tf1.tree_f1` on class c alone, binary, tol 1.5 mm, **one ostium per reference piece** at its centreline voxel nearest the parent: LAD for D1–D3; LCx for OM1, OM2, Ramus; for PDA and PLB, the collapsed vessel the piece touches most. R-PDA is in two pieces in 10 % of cases, and each piece gets its own root |
| Four-class collapse | `collapse_to_four`: D1–D3 → LAD; OM1, OM2, Ramus → LCx; **each PDA/PLB component → the vessel with the most face contact** (a component reached only through another takes that one's vessel), RCA on a tie or no contact. One implementation for pool reads and for 1-F. The vessel scorer (V) reads its output |
| Ignore (255) | reference only (F-A3's eight unexplained "Other" pieces): excluded from every class |

**Q1's other answers are gone.** D47 chose (A), so the launcher no longer needs `JANUS1F_LEFT_PDA`. It hard-codes
D47 (A): L-PDA/L-PLA → PDA/PLB in the labels, and the contact collapse in scoring. The (B) and (C) branches of F-A3
and F-A4 are deleted rather than kept as dead switches.

**The self-test** (`test_branch_score.py`, six training cases chosen by hash, never a locked one; 31 of 31 pass,
`test_branch_score.log`):
- **identity:** recall, agreement and naming = 1 and branch tF1 = 1, for every gated class present;
- **a 1-voxel dilation of the prediction:** recall and naming stay 1;
- **D1 ↔ D2 swapped:** recall 1, naming 0;
- **PDA ↔ PLB swapped:** recall 1, naming 0;
- **OM2 relabelled LCx:** detected (recall 1), not named (naming 0), and agreement falls;
- **OM2 erased:** recall 0;
- **the collapse:** the 1-F reference collapsed by SegQueue's function equals ImageCAS-X's D25 territories on every
  non-"Other" voxel, in all six cases.

### 2.3 The contact collapse against ImageCAS-X's origin labels

D47 replaced the ruling's "the vessel it touches most" with SegQueue's exact rule. So I ran SegQueue's function on all
720 label maps:
- 1-F's PDA = R-PDA ∪ L-PDA and PLB = R-PLA ∪ L-PLA;
- OM1, OM2, IM and LCx-side "Other" in the LCx;
- the result compared with ImageCAS-X's own side labels (D25: L-* → LCx, R-* → RCA).

| Set | PDA/PLB components | → LCx | Fallbacks (tie / no contact) | Left-branch voxels | Voxels on the wrong side |
|---|---|---|---|---|---|
| Train 620 | 1 296 | 93 | 0 (0 / 0) | 112 379 | **0** |
| Locked 100 | 217 | 16 | 0 (0 / 0) | 19 797 | **0** |

(`label_checks_summary.md`.)

**What this settles.** On ImageCAS-X the contact rule and the origin labels are the same partition. So:
- the 1-F reference collapsed by SegQueue's function **is** Janus 0's D25 reference, and V compares like with like
  under D47 (A);
- pool reads and 1-F are collapsed by the same code;
- no per-case origin rule is needed in the scorer, which was round 1's worry about option (A).

The check is on reference labels. On a prediction the rule can fall back to the RCA, for a PDA piece that touches
nothing. `collect` reports the fallback count, as SegQueue does.

## 3. Arm N: dropped (item 3)

**Do not build Arm N this round.** Reasons:
- **What Arm N was for is already covered.** Its value was a namer whose vessels are Janus 0's by construction. Reading
  T is exactly that, with 1-F as the namer, at no extra code.
- **The B gates are absolute, anchored on human agreement (§1), not relative.** A comparator gate ("beat Arm N") needs
  Arm N's per-case branch-tF1 spread on the locked 100. That number would be a second look at the locked 100 before
  J1F-A, for a gate whose power is unknown.
- **Its cost is real.** It needs a graph extractor on predicted trees, a segment classifier, its tests, and a decision
  about what to do with breaks and touching branches. On automatic trees, published namers lose most of their margin
  (Hampe et al. 2024: label F1 0.74 against 0.91 on reference trees).
- **It cannot deliver stage 2's classes** (Atlas v1 §5.1 says so too).

**The rule-ordinal report (F-A9) stays.** It measures "network ordinals vs counting" on F's own segmentation, which is
the part of Arm N that informs the next design.

**Trigger to build it.** If J1F-A's verdict is "not adopted" (< 4 of 6), F-A6 already names a graph namer on Janus 0's
tree as one of round N+1's options. Arm N is then that option, built as a candidate and not as a comparator.

## 4. Stage 2's loss details (item 4)

### 4.1 The Dice term: leaf-Dice, defined exactly

For each class c, the Dice term counts only voxels where c is **decided**:
- the target is 1 where the voxel's label set is {c};
- the target is 0 where c is not in the set;
- a voxel whose set contains c **and** another class is left out of c's Dice, numerator and denominator.

The CE term is the marginal over the set (F-A11, unchanged).

**Against the two alternatives:**
- **Merged mass** (Atlas: Dice on Σ_{c∈S} p_c). On ImageCAS-X the six untraced classes only ever appear inside the
  set {bg, S1–S3, SN, Conus, RMA}. Merged-mass Dice on that set rewards "bg or any of the six" equally, so it gives the
  six classes almost no signal. Fidon et al.'s Table 2 shows marginal Dice collapsing on scarce classes (corpus
  callosum 11.1 % vs leaf-Dice 62.0 %), and our six are the scarcest we have.
- **Ignore for Dice** (Foxtrot): drops a set voxel for **every** class. An ImageCAS-X background-set voxel next to the
  LAD then stops being a Dice negative for the LAD, D1 and the rest. Leaf-Dice keeps it as a negative for every class
  outside the set. Leaf-Dice is Foxtrot's rule with that fixed.
- **Why the choice matters at all.** In Shi et al.'s own ablation (Table 3, §7) the marginal CE alone gave 0.873 mean
  Dice, no better than the fully labelled set alone (0.874). Marginal CE plus a Dice term gave 0.921. The Dice term
  carried the gain there, on large organs. On scarce classes the leaf form is the one that does not collapse.

### 4.2 The background band, measured

The band decides where ImageCAS-X background becomes the set {bg, untraced classes} rather than {bg}.

`label_checks.py` measured, on 120 training cases chosen by sha256(`asclepius-j1f-r2-band:` + id):
- **(a)** the background volume a band of w mm around each host trunk would release;
- **(b)** a proxy for how much of an untraced branch a band of w covers: the share of each **traced** side branch's
  voxels lying within w of its own trunk.

Septals do not exist in ImageCAS-X, so (b) uses D1, D2, OM1, OM2, R-PDA and R-PLA, which are of the same calibre
(round 1: median radius 0.61–0.67 mm).

**(a) Background released**, median [p10, p90] per case, in mm³ and as a multiple of the case's tree volume. A 256³
patch at 0.5 mm is 2 097k mm³.

| Host trunk | 4 mm | 8 mm | 15 mm | 25 mm |
|---|---|---|---|---|
| LAD | 10k [8k, 12k]; ×5 | 37k [28k, 43k]; ×18 | 123k [95k, 143k]; ×60 | 341k [266k, 395k]; ×168 |
| LCx | 7k [4k, 10k]; ×4 | 26k [14k, 34k]; ×12 | 89k [54k, 114k]; ×43 | 258k [163k, 325k]; ×128 |
| RCA | 10k [8k, 12k]; ×5 | 33k [27k, 40k]; ×16 | 109k [91k, 129k]; ×54 | 310k [265k, 359k]; ×152 |
| Union | 27k [22k, 32k]; ×13 | 90k [75k, 106k]; ×46 | **298k [253k, 341k]; ×151** | 803k [684k, 934k]; ×410 |

**(b) Share of a traced side branch's voxels within w of its own trunk**, median [p10] over cases, and the median of
each case's 90th-percentile and maximum distance:

| Branch (trunk) | 4 mm | 8 mm | 15 mm | 25 mm | p90 mm | max mm | cases |
|---|---|---|---|---|---|---|---|
| D1 (LAD) | 0.21 [0.11] | 0.45 [0.27] | **0.80 [0.52]** | 1.00 [0.80] | 17.6 | 21.1 | 117 |
| D2 (LAD) | 0.17 [0.10] | 0.38 [0.24] | **0.77 [0.50]** | 1.00 [0.74] | 20.1 | 24.3 | 61 |
| OM1 (LCx) | 0.17 [0.08] | 0.38 [0.19] | **0.75 [0.41]** | 1.00 [0.65] | 17.9 | 20.7 | 100 |
| OM2 (LCx) | 0.16 [0.07] | 0.37 [0.19] | **0.92 [0.38]** | 1.00 [0.57] | 14.8 | 17.6 | 40 |
| R-PDA (RCA) | 0.13 [0.08] | 0.23 [0.16] | 0.41 [0.28] | 0.67 [0.47] | 34.7 | 38.3 | 115 |
| R-PLA (RCA) | 0.12 [0.07] | 0.23 [0.14] | 0.42 [0.26] | 0.73 [0.44] | 31.2 | 35.1 | 114 |

**Proposed: 15 mm (Crucible's), per host.**
- **The bands:**
  - S1–S3 within 15 mm of the LAD trunk;
  - Conus and RMA within 15 mm of the RCA trunk;
  - SN within 15 mm of the RCA trunk and of the LCx's first 20 mm, which is Foxtrot's proximal rule (opinion; not
    measured here).
- **Everything else in ImageCAS-X stays {bg}.**
- **What a band releases where it is wrong, and what it leaves out where it is right.** Inside the band the six heads
  feel no background pressure from ImageCAS-X. Outside it, ImageCAS-X calls any untraced branch background, so a
  septal's far end is trained toward background.
  - **No band** removes ImageCAS-X's background pressure on the six heads everywhere: all 620 cases.
  - **8 mm (Foxtrot)** covers only 37–45 % of a branch the size of a diagonal or marginal (median). Most of a septal's
    length would then be trained toward background from 620 cases, against a few dozen extended reads saying
    otherwise.
  - **15 mm** covers 75–92 % of a D/OM-sized branch in the median case. It releases about 300k mm³ per case, about
    14 % of a 256³ patch.
  - **25 mm** covers the whole of a D/OM-sized branch, but releases 2.7× as much (about 38 % of a patch). By then it
    is close to "no band" near the heart.
- **The remaining truncation at the band's edge** is met by the extended reads themselves. Under D47 Q7, septals, SN,
  conus and RMA are traced beyond the seed. Under Q3, a complete group makes their full length a singleton, which
  leaf-Dice and the CE both see.
- **The R-PDA and R-PLA rows are not a model for the six.** They run far from the RCA trunk (p90 31–35 mm) because they
  are long distal vessels. Septals and the conus are short and leave the trunk directly. The D/OM rows are the
  better proxy, and they are a proxy only.
- **The band is a config value** (`band_mm`). Stage 2's first look (§4.3) reports the six classes' predicted volume
  beyond it. If extended reads show septals routinely longer than 15 mm from the LAD, the next stage-2 candidate
  widens it. That is not decided on the locked 100.

### 4.3 The leakage check, pre-registered as a stage-2 gate

Stage 2 (J1F-2) is a new candidate model. It gets one look at the locked 100, under these gates, in order:
1. **No regression on stage 1's decision.** V and B (§1.3) re-run on J1F-2's output, with the six new classes folded
   into their parents (S1–S3 → LAD; SN, Conus, RMA by contact as SegQueue does). Both must still pass. The vessels are
   compared with **Janus 0**, as in stage 1.
2. **No theft from traced classes (Bridge's leakage check, made quantitative).** On the locked 100, voxels predicted
   as one of the six classes that ImageCAS-X labels as a **traced** class must be ≤ **1 %** of ImageCAS-X's traced
   foreground, pooled. ImageCAS-X's traced labels are singletons, so a septal painted on the LAD trunk is an error
   even though ImageCAS-X has no septals.
3. **No painting far from the tree.** In ≥ 95 % of locked cases, no voxel of the six classes lies more than **30 mm**
   from predicted coronary foreground of any stage-1 class. Every traced D and OM branch lies within 18–24 mm of its
   trunk in the median case (§4.2, max distance). 30 mm leaves room for a septal leaving a diagonal-free LAD
   segment. The number is an opinion bounded by those measurements.
4. **Reports** (never a gate until §6's counts): each six-class detection, naming and precision against D35's
   extended reads.

If gate 2 or 3 fails, the next step is Shi et al.'s exclusion term against ImageCAS-X's traced foreground (Bridge's
and Crucible's remedy), not a narrower band.

## 5. Reads per class: one experiment, run as the stage-2 trainer's first test (item 5)

**Run Job B in a reduced form, as the label-set trainer's integration test, after J1F-A and before the first stage-2
class is trained.** Keep F-A11's provisional lines until it reports.

**Why this, and not Bridge's three runs or my round-1 learning curve:**
- **Thinning a traced class honestly needs the label-set trainer.** A case whose OM2 is "not drawn" must carry the
  4-class pool set {LCx, OM1, OM2, Ramus} on those voxels. That is exactly what a 4-class pool read gives stage 2.
  Relabelling the thinned OM2 as LCx would teach the wrong answer.
- **So Job B is the faithful dress rehearsal of stage 2:** few extended reads among many 4-class reads, with a known
  answer on held-out cases. It tests the trainer and measures the threshold in one run.
- **It costs no stage-1 time.** It runs after J1F-A's verdict.

**The design (≈ 22 GPU-h):**

| Item | Setting |
|---|---|
| Hold-out | 60 of the 620, smallest sha256(`asclepius-j1f-r2-budget:` + id); never trained; never the locked 100 |
| Thinned classes | **OM2 and PLB** (229 and 565 training cases): the scarce ordinal case and the common non-ordinal one |
| Runs | **B30:** OM2 and PLB singletons in exactly 30 of the 560 training cases (hash-chosen); in every other case their voxels carry the 4-class parent set. **Ball:** the same 560 with every class as a singleton (control) |
| Recipe | J1F-A's: warm from Janus 0, parent-copied heads, Janus 0's plans; **200 epochs**, label-set trainer (marginal CE + leaf-Dice) for both runs, so the only difference is the thinning |
| Score | §2's scorer on the 60 hold-out cases (recall, agreement, naming for OM2 and PLB) |

**Pre-registered rule:**
- If B30 is within **0.05** of Ball on recall, agreement and naming for both thinned classes, F-A11's train line stays
  **30**.
- If B30 falls short by more than 0.05 on any of the three, in either class, the train line becomes **60**, and a
  B60 run (≈ 11 GPU-h) runs before any stage-2 class is trained.
- The stage-2 trainer must also pass its CPU tests: marginal CE equals ordinary CE on singleton voxels, and its
  gradient matches finite differences (Foxtrot's check).

**Caveat.** Janus 0 saw the hold-out's 4-class labels in its own training, so the hold-out's territories are not new
to the network. Its branch split is new, and the branch split is what Job B measures.

## 6. The scoring set for the six untraced classes (item 6)

D47 Q6 put the D35 decision patients in extended mode. What a held-out set of n patients yields, for a class drawn in a
share p of them (`d35_yield.py`; binomial; no data):

| n patients | p | E[count] | P(≥ 20): report | P(≥ 30): decide | ± on a detection rate of 0.85 |
|---|---|---|---|---|---|
| 35 (D35) | 0.4 | 14 | 0.03 | 0.00 | 0.18 |
| 35 | 0.6 | 21 | 0.70 | 0.00 | 0.15 |
| 35 | 0.8 | 28 | 1.00 | 0.27 | 0.13 |
| 35 | 0.9 | 32 | 1.00 | 0.87 | 0.12 |
| 60 | 0.4 | 24 | 0.88 | 0.07 | 0.15 |
| 60 | 0.6 | 36 | 1.00 | 0.96 | 0.11 |
| 100 | 0.4 | 40 | 1.00 | 0.99 | 0.11 |
| 100 | 0.2 | 20 | 0.54 | 0.01 | 0.15 |

**Reading.** I do not know how often each untraced class is visible and drawn on CCTA. Nothing in this repository
measures it, and the first extended reads will. So the plan is written for the range:
- **D35 alone can report a class only if it is drawn in about 60 % or more of patients.** It can decide (ship
  unfolded) only at about 90 %. That plausibly covers S1 at most.
- **SN, Conus and RMA stay folded into their parents** in everything that leaves the project, until a larger held-out
  set exists.
- **No new question to the lead now.** Once D35's extended reads are in, the counts per class are known. If any class
  that has reached F-A11's train line has fewer than 20 D35 patients, the PM asks the lead whether to read a further
  held-out pool set in extended mode. About 60 patients covers p ≥ 0.4 for reporting and p ≥ 0.6 for deciding. That
  is D35's to decide, not this plan's.

## 7. Shi et al.'s numbers, reconciled (item 7)

Re-read from arXiv:2007.03868v1 (MedIA 70:101979), Table 3, column "All" (mean Dice over the ten organ–dataset
columns):

| Network | Data | Loss | All |
|---|---|---|---|
| Ψ_F^mc | fully labelled F only | rCE + rDC | **0.874** |
| Ψ^mc_{F+Pi} | F plus **one** partial set at a time | rCE + rDC | **0.900** |
| Ψ_All^mc | F + all four partial sets | marginal CE only | 0.873 |
| Ψ_All^mc | F + all four partial sets | marginal CE + marginal Dice | **0.921** |
| Ψ_All^mc | F + all four partial sets | + exclusion CE + exclusion Dice | **0.931** |

**Atlas and Crucible quoted it correctly:** joint training on all five sets with the marginal loss, 0.921 against
0.874 on F alone, and 0.931 with exclusion.

**My round-1 quote was wrong for the claim it supported.**
- ".874 → .900" is the paper's text comparing F alone with the **pairwise** F + P_i models. It is not the pooled
  marginal model.
- ".931 vs .900" is the paper's own sentence comparing the full model with those pairwise models. The table's
  exclusion gain over marginal alone is 0.931 against 0.921.

I withdraw both and use the table's rows above. The method is unchanged.

## 8. The `role:swe` spec for `trillium/janus1f`, frozen (item 8)

**Filed only after the round that rules the plan converged** (F-A12; round 3 at the earliest). It is #306's
`janus1l` as frozen in [[Candidates/Janus 1-L/Delta v2|Delta v2 (1-L)]] §7, with the differences below. Shared
parts stay shared: the split guard, the sealed guard, the plans-identity check, the chain logic and `status` are
**imported from `trillium/janus1l/lib/`**, not copied.

### 8.1 Interface: `trillium/janus1f/janus1f <mode>`

**Environment:**
- `JANUS0=$SCRATCH/janus0` (Step T's folder; `$KEEP` copy as fallback);
- `J1F_WORK=$SCRATCH/janus1f`;
- `J1F_RUN=a1|a2`;
- `JANUS1F_DRYRUN=1` (prints, submits nothing).

| Mode | Does | Job | GPU-h |
|---|---|---|---|
| `check` | All self-tests (§8.3), then a dry run: split pins, Janus 0 sha256, plans sha256 (must equal Janus 0's), `branch_score.py` sha256, the label-count line (§8.2), every SBATCH header | login | 0 |
| `prep` | Dataset **719**: the 620 + the locked 100, named `cNNNN`, labels by `j1f_labels.py` with D47 (A) and F-A3's ignore rule. Janus 0's `plans.json` by `nnUNetv2_move_plans_between_datasets`; `nnUNetv2_preprocess` only; no fingerprint, no `plan_experiment`. Refuses a dataset id already in use | CPU job | ≈ 1 |
| `train` | J1F-A: `nnUNetTrainer_janus1f` (§8.4), `SEGTRAIN_FINETUNE_FROM=$JANUS0/…/checkpoint_final.pth` with `SEGTRAIN_FINETUNE_HEADS=parent_copy:configs/janus1/j1f_parents.json`, `SEGTRAIN_CT_WINDOW=off`, 500 epochs, chained (2 links). a2 (D47 Q8) is the same with fold 1 and its own seed, concurrent | 2 × 23:50 per run | ≈ 29–31 per run |
| `predict` | `afterok`. The locked 100 with `--save_probabilities --disable_tta -chk checkpoint_final.pth`. Writes **F** (hierarchical decode, §8.5) and **T** (Janus 0's argmax territories from Step T's copy of Fir's predictions, then 1-F's argmax inside each territory), then deletes the npz | 3 h | ≈ 1 |
| `collect` | Vessels: collapse F by `branch_score.collapse4`, score with the A1c scorer and icx4's in-job aortas, paired with Janus 0's Fir predictions (F-A6, F-A8). Branches: `branch_score.score_case` + `aggregate` for F and T. Applies V, then B (§1.3), then the verdict table. Writes `results/DECISION.md`, `results/verdict.json`, and F-A9's reports, including the rule-ordinal reading. a2, when present, is report-only | login | 0 |
| `status` | s/epoch, epochs done, chain state, and `fitcheck.json` when present | login | 0 |

**The lead's commands** (the same shape as #306's; written out when the issue is filed):

```sh
cd $SCRATCH/asclepius && git -C repo pull --ff-only && source $HOME/icx14-venv/bin/activate
pip install --no-deps -e repo
rm -rf experiments/janus1f && cp -r repo/trillium/janus1f experiments/janus1f && cd experiments/janus1f
JANUS0=$SCRATCH/janus0 ./janus1f check        # post the printout on #303
JANUS0=$SCRATCH/janus0 ./janus1f prep         # then, when it ends:
JANUS0=$SCRATCH/janus0 J1F_RUN=a1 ./janus1f train
JANUS0=$SCRATCH/janus0 J1F_RUN=a2 ./janus1f train   # D47 Q8, if the allocation allows
./janus1f status                              # expect ~192-210 s/epoch; fitcheck at epochs 150 and 300
./janus1f collect                             # post results/DECISION.md and verdict.json
```

**Send back on #303:**
- `check`'s printout;
- `status` after 20 epochs and after epoch 150, with `fitcheck.json`;
- `results/` (no weights, no volumes);
- the `.out` of any failed job.

### 8.2 Labels

- **The converter is `j1f_labels.py`**, sha-pinned. Round 1 ran it with `--left-pda lcx`. It changes in two ways:
  - **D47 (A) is hard-wired.** L-PDA/L-PLA → PDA/PLB, and the `--left-pda` switch is removed.
  - **F-A3's ignore rule is added:** "Other" pieces touching only the RCA, or nothing, become 255.
- **`check` prints its summary counts.** The expected line is computed by the swe on the 720 non-sealed label files
  and written into the issue. `prep` refuses on any difference.
- **F0 is the independent cross-check.** It runs Foxtrot's converter on Fir's own copy (§12).

### 8.3 Self-tests (`./janus1f check`; each must fail on a broken input)

#306's tests 1–4 and 7 apply unchanged: split pins, seals, no plan step, strict load, ensemble. Test 5 (t\*) does not
apply: 1-F reads at argmax. Test 6 (L3) applies to V. Added:
1. **Parent copy.**
   - On a random batch, the territory sums of the 13-channel softmax equal Janus 0's 5-channel softmax within 1e-5.
   - The hierarchical decode equals Janus 0's argmax on every voxel.
   - For every deep-supervision output.
   - Fixture: one head row not copied.
2. **Hierarchical decode.**
   - On random logits, decode territories equal the argmax of the summed probabilities.
   - Plain argmax differs on > 1 % of voxels (Atlas's 2.5 % check, kept as a tripwire).
   - Fixture: a decode that takes a plain argmax.
3. **The branch scorer.** `test_branch_score.py`'s 31 checks, on the six training cases it names.
4. **Labels.** Every 719 training label collapses (`collapse4`) to `territory.py`'s four classes, except the 255
   voxels and round 1's 40 "Other" voxels in 2 cases. Fixture: one L-PDA voxel written as RCA.
5. **The locked 100 is never scored before `collect`.** The trainer's final validation is skipped (§8.4), and no
   `summary.json` exists for fold 0 after `train`.

### 8.4 The trainer diff, against #306's `nnUNetTrainer_janus1l`

| Setting | `janus1l` | `janus1f` |
|---|---|---|
| Output head | 5 classes, loaded strict | **13 classes**: non-head tensors strict and bitwise; every `seg_layers` head (deep supervision included) by parent copy from `configs/janus1/j1f_parents.json` (round 1's `parent_copy.py` rule) |
| Final validation | skipped (no locked-100 number before `collect`) | skipped, the same |
| Fit check | none | **F-A5:** at epochs 150 and 300, predict the 20 training cases with the smallest sha256(`asclepius-j1f-fitcheck:` + id), decode as in §8.5, and write per-class Dice to `fitcheck.json`; at 150, D1, OM1, PDA or PLB < 0.10 writes `STALL` |
| Loss, sampling, schedule, augmentation | A17a's, L-A2 | the same, with 13 classes; ignore label 255 |
| Class-weight file | must be absent (Step T checks) | the same; if Step T finds Janus 0 ran with `ce_class_weights.json`, `prep` refuses and the PM brings it back to the round |
| Epochs | 250 | **500** |

### 8.5 Decoding

- **F:**
  1. Territory = argmax of the summed probabilities over {bg}, {LM}, {LAD, D1, D2, D3}, {LCx, OM1, OM2, Ramus},
     {RCA, PDA, PLB}.
  2. Class = argmax within that territory.
  - Computed from nnU-Net's saved probabilities, which sum exactly.
- **T:** the territory comes from Janus 0's Fir prediction of the same case (argmax). Step 2 is the same. T's four
  classes therefore equal Janus 0's **before** the contact collapse.
- **One subtlety under D47.** PDA and PLB sit in the RCA decode group. A left-sided PDA that the network names PDA is
  collapsed to the **LCx** by contact. So T's collapsed vessels can differ from Janus 0's wherever Janus 0 called a
  left PDA "RCA". `collect` reports that voxel count. It is expected to be zero or near it, because Janus 0's labels
  put left PDAs in the LCx.

### 8.6 Refusals

The launcher refuses:
- a sealed or locked case in training;
- plans that are not byte-identical to Janus 0's;
- a parent-copy identity error above 1e-5;
- a used dataset id;
- a `branch_score.py` or `j1f_labels.py` sha256 mismatch;
- a missing Janus 0 baseline prediction for any locked case;
- a CT or label set that is incomplete. If `$SCRATCH` was purged, it prints icx4's own idempotent fetch steps
  (`trillium/icx4/lib/fetch_icx.py` for labels, `layout.py check` for CTs) and stops. The lead re-runs them, then
  `prep`.

### 8.7 Cost

| Job | GPU-h |
|---|---|
| prep | ≈ 1 (CPU job) |
| J1F-A a1 (incl. fit checks ≈ 0.3) | ≈ 29–31 (ceiling 47.7) |
| a2 (D47 Q8) | ≈ 29–31 |
| predict | ≈ 1 per run |
| Job B (B30 + Ball, after the verdict) | ≈ 22 |
| **Stage 1 committed** | **≈ 31 (a1) + 31 (a2) = 62** |

## 9. The warm-start source if Janus 1-L is adopted first (item 9)

**Janus 0, regardless.** Reasons:
- **Janus 1-L may not be one network.** My 1-L round-2 plan makes the a1 + a2 ensemble the ship candidate, and D46 Q6
  accepts an ensemble in principle. A parent-copy warm start needs one set of weights.
- **The comparator would move mid-plan.** V compares with Janus 0's Fir predictions, which exist and are paired by
  case. A 1-L start would need V to compare with 1-L, whose locked-100 predictions are on Trillium, with a
  cross-cluster difference in the pair (F-A8's reason).
- **What 1-L buys 1-F is available without retraining.** Reading T can take its territories from any 4-class model.
  If 1-L is adopted before `collect`, `collect` also writes **T(1-L)**: 1-L's territories with 1-F's branches. This is
  a report, decided on nothing in this round. It can become the shipped composite in a later round at zero GPU-h.
- **V's comparator stays Janus 0** in every case.

## 10. One census of record (item 10)

**The census of record for the 620 and the locked 100 is round 1's `experiments/Delta/j1f_r1/census.json`** (sha256
`e2216d1b…cb6a`), with `ordinal.json` (`5b4006a3…0bd6`). It is the only census with one row per case for all 720
non-sealed cases, which is what the gate simulation and the locked counts read.

| Quantity | Value of record | Definition |
|---|---|---|
| Trunk twigs | LAD 4, LCx 1, RCA 2 cases of 620 (locked 100: 0) | unnamed skeleton branches ≥ 5 mm leaving the class's main path |
| Left-sided posterior branches | 59 of 620 (L-PDA 38, L-PLA 54); 12 of 100 (L-PDA 4, L-PLA 12) | any voxel of ImageCAS-X's L-PDA or L-PLA |
| Dominance | reported from `Descriptors.xlsx` beside the label count, never instead of it | — |
| Locked gate counts (D47 (A), ≥ 5 mm) | D1 97, D2 64, OM1 84, OM2 40, PDA 98, PLB 99; Ramus 24, D3 7 | §2.2's presence rule |

**Why the twig counts differ** (Crucible 13, Foxtrot 6, Delta 4): the three censuses count different things. Mine
counts a skeleton branch only once it has left the main path for ≥ 5 mm. Counts that include short spurs at
bifurcations, or at a 3 mm cut, are higher. None of the three changes the conclusion (0.5–2 % of cases), so the
plan quotes one number from one file.

## 11. D47's other consequences, and Q8/Q9 (item 11)

| Answer | Consequence in this plan |
|---|---|
| Q1 (A) | Labels: L-PDA/L-PLA → PDA/PLB (§8.2). Collapse: SegQueue's contact rule, imported (§2). `JANUS1F_LEFT_PDA` removed. Locked PDA 98, PLB 99 |
| Q3 complete flags | Stage-2 label sets (F-A11): in an extended read, a parent whose group is marked complete is a **singleton**; an unmarked group's parent is {parent ∪ its children}; an empty child class in a complete group is a true negative |
| Q4 child over parent | Stage-2 label sets: an overlap of a branch with its own parent is the **branch** (singleton); unrelated overlaps stay D40's full-set ignore |
| Q5 | Unchanged. Revisit at the first pool wave if fewer than 30 patients have a septal read (§6) |
| Q6 D35 extended | §6's table. D35 is the six classes' only scoring set for now |
| Q7 trace beyond the seed | Makes extended reads of the six classes non-empty. Stage 2 still waits for F-A11's counts |
| Q8 a2 | Runs concurrently with a1 on fold 1 with its own seed (§8.1). Report-only: σ per branch class = \|a1 − a2\| / √2, and A37's rule if a class's tF1 differs by > 0.02. Never shipped, never a gate |
| Q9 naming | `DECISION.md` names the read model (F or T) **Janus 1-F.1**. If adopted, it is **Janus 1-F**. a2, T(1-L) and the rule-ordinal reading take no number |

## 12. Step T and F0 have not run: what each result changes

| Result | Changes |
|---|---|
| **Step T posts its three `SHA256SUMS` lines and counts 160 / 160 / 100** | Nothing. `JANUS0=$SCRATCH/janus0` is the warm start and the baseline source |
| Step T finds `ce_class_weights.json` in Janus 0's run | `prep` refuses (§8.4). The round decides whether 1-F copies the 4-class weights to the children (parent copy of weights) or both tracks re-derive |
| Step T has not run by early December | Scratch purge (~2026-12-20) risk. J1F-A cannot start without Janus 0's checkpoint, plans and locked-100 predictions. The PM escalates; nothing in this plan can replace them |
| Step T's locked-100 prediction count is < 100 | `collect` would lack pairs. J1F-A's `predict` re-predicts Janus 0 on the missing cases on Fir (≈ 0.1 GPU-h per 10 cases) with the same checkpoint, and reports it |
| **F0's split pins match** (`1350cb1f…`, `bbd9c687…`) | Nothing |
| F0's pins differ | Stop. Fir's ImageCAS-X copy differs from Zenodo's. Every count in this plan is from Zenodo's |
| F0's label counts match Foxtrot's PR (`other_diag 50, other_marg 20, other_amb 8, d3_from_other 47, …`) | Nothing. Two converters agree on Fir's copy |
| F0's label counts differ | Stop before `prep`. Either the copy or Foxtrot's converter differs. `check` then runs `j1f_labels.py` on the same files, which says which |

## 13. Proposed amendments to the ruling

| # | Amends | Change |
|---|---|---|
| F2-1 | F-A6 B1, B2 | Recall line 0.80 → **0.75**; naming line 0.85 → **0.80**; margin 0.05 and "4 of 6" unchanged (§1) |
| F2-2 | F-A6, F-A9 | The definitions of record are `branch_score.py` (§2), pinned by sha256 |
| F2-3 | F-A3, F-A4 | D47 (A) hard-wired; the four-class collapse is SegQueue 0.20.0's `collapse_to_four`, imported; `JANUS1F_LEFT_PDA` and the (B)/(C) branches deleted |
| F2-4 | F-A11 | Leaf-Dice as defined in §4.1; the band as in §4.2; the stage-2 gates of §4.3 |
| F2-5 | F-A11 | Job B as B30 + Ball after J1F-A, with §5's rule. Train line 30 until it reports |
| F2-6 | §5 item 3 | Arm N dropped; built only as a candidate if B fails (§3) |
| F2-7 | F-A2 | The warm start stays Janus 0 if 1-L is adopted first. T(1-L) is a report (§9) |
| F2-8 | F-A12 | The swe spec is §8 |
| F2-9 | Delta v1 §13 item 2 | Shi et al.'s numbers as §7's table |

## 14. What would change this plan

| If… | Then |
|---|---|
| The lead rejects the looser lines (F2-1) | Keep 0.80 / 0.85 and accept that OM2 folds about a third of the time at human level. Nothing else changes |
| Step T or F0 report anything but the expected lines | §12's row for it |
| The B30 run falls more than 0.05 short of Ball | Train line 60 and a B60 run (§5) |
| The stage-2 leakage gates fail | Shi's exclusion term against ImageCAS-X's traced foreground (§4.3), then a new stage-2 candidate |
| D35's extended reads show a class drawn in < 40 % of patients | That class stays folded; the PM asks the lead about a larger extended held-out set (§6) |
| J1F-A's fit check writes `STALL` | F-A5 as ruled: the PM may cancel. Round N+1 chooses among class weights, a two-network design and the graph namer (Arm N, §3) |

## 15. Evidence and code (`experiments/Delta/j1f_r2/`)

| File | What |
|---|---|
| `gate_sim.py`, `gate_sim.json`, `gate_sim.log`, `gate_sim_3mm.log` | §1: the human-level and bad-model simulation; 5 mm and 3 mm presence |
| `branch_score.py` | §2: the scorer of record |
| `test_branch_score.py`, `test_branch_score.log` | §2: its self-test (31/31 PASS) |
| `label_checks.py`, `label_checks_summary.md` | §2.3 the contact collapse on 720 maps; §4.2 the band on 120 training cases |
| `summarise_checks.py` | builds `label_checks_summary.md` |
| `d35_yield.py`, `d35_yield.txt` | §6 |

**Sources re-read this round:**
- ImageCAS-X Table 1 (arXiv:2608.30404, HTML v1): per-segment n and agreement, quoted in §1.1.
- Shi et al., arXiv:2007.03868v1, Table 3 and §4.4: §7.

Citations carried from v1 and the ruling (Fidon Table 2, Cao 2017, Hampe 2024) are used only as they were verified
there.

**Not opened:** no sealed case, no CT, no model's locked-100 score. The locked 100's **reference labels** were counted
for §1's eligibility and simulation, as F-A7 permits. The scorer's self-test and the band ran on training cases only.
The contact-collapse check (§2.3) ran on all 720 non-sealed label maps, comparing labels with labels.
