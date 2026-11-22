---
tags: [plans, candidate, track-1-F, round2, janus1-f, D44, D45, D47, fir, locked100, partial-labels]
author: Foxtrot
track: 1-F
round: 2
version: 2
updated: 2026-11-22
issue: christianGRogers/Asclepius#303
---

# Foxtrot v2 (Janus 1-F): freeze the scorer and the gates on a human-level simulation, keep F-A11's read rule, take leaf-Dice and a measured band, and carry track 1-L's round-2 mechanics into the launcher

**What this is.** Round 2's answers to [[Janus 1-F Round 1]] §5, items 1–11, on top of the plan in force (Delta v1 as
amended by F-A1 to F-A13) and the lead's answers in **D47**. It does not re-argue §0 of the ruling.

**Evidence.** CPU only, on D45's 620 training labels and nothing else:
[[Foxtrot - On the 620, human-level branches false-fail OM2's round-1 gate up to 45 percent of the time, leaf-Dice is the only Dice term that both learns a drawn septal and stops an intruder, and the origin collapse needs PDA and PLB grouped]].
Code: `experiments/Foxtrot/j1f_r2/`.

**Data rules kept.** Only the 620 training labels were fetched (`../j1f/fetch_620.py`, which refuses anything else) and
every script asserts the 620's L-A1 pin. No locked-100, sealed, quality-0 or TotalSegmentator-twin label was opened.
The locked-100 counts used below are the ones the round-1 ruling already states (F-A7). Nothing ran on Fir, SciNet or
Trillium. **Step T and F0 have not run**; §13 says what each would change.

## 0. The answers in one table

| §5 item | Answer | Evidence |
|---|---|---|
| 1. Gate numbers | **Keep V, B1's 0.80 recall, the "inter-observer − 0.05" presence line, B2's 0.85 and "4 of 6"**, except where they fail a human-level model: **D2's naming line 0.817; OM2's recall and naming lines 0.744** (each "the ruled line, capped at the human-level value − 0.10"). Human-level false-fail is then ≤ 0.09 per class and < 0.001 for the read | `gate_sim.py`, §1 |
| 2. Scorer | Frozen as `branch_score.py` (sha256 in §2) on top of A1c's `tree_f1`, with **PDA and PLB grouped** before the origin collapse | `pass1.py`, `recheck_collapse.py`, §2 |
| 3. Arm N | **Dropped** | §3 |
| 4. Stage 2's loss | **Leaf-Dice** (not merged mass, not ignore). **Band by parent segment, 15 mm by default, widened by a pre-registered rule from the first reads.** Bridge's leakage check becomes stage 2's gate L | `dice_terms.py`, `band.py`, §4 |
| 5. Reads per class | **A rule: F-A11's thresholds kept**, no Job B, no learning curve | §5 |
| 6. Untraced classes' scoring set | D35 (35 patients, extended mode, D47 Q6) reaches the report line (20) for a class drawn in ≥ 70 % of patients, and the decide line (30) only at ≥ 90 %. **Septals: report. SN, conus, RMA: counts only** | `d35_yield.py`, §6 |
| 7. Shi et al. | None quoted; drop both sets | §7 |
| 8. `role:swe` spec | A patch on `janus1l` as L-A21 froze it, with **three round-1 corrections** that track 1-L's round 2 found (plans check, fingerprint, validation set) and **T's LCx territory admitting PDA/PLB** (D47) | §8 |
| 9. Warm start | **Janus 0 either way**; 1-L's adoption adds two reports | §9 |
| 10. Census of record | Delta's method (class-mask longest path) on the 620, at 5 mm; Crucible's higher count is the **9 cases without a left main**, whose ostial stubs it counts as twigs | `pass1.py`, §10 |
| 11. Q8, Q9 | a2 = fold 1, report only, no ensemble; F or T is Janus 1-F.1 | §11 |

## 1. Item 1: the gate numbers, frozen

### 1.1 The simulation

`gate_sim.py`, 20 000 trials per class and setting.
- **Locked counts:** the ruling's (D1 98, D2 64, OM1 84, OM2 40, PDA 96, PLB 96). No locked label was opened here.
- **Pieces per present case:** drawn from the 620 (`pass1.py`). PDA has two or more pieces in 10.7 % of cases, PLB in
  1.6 %, D1 in 1.3 %, the rest in under 1 %.
- **A human-level model** disagrees with the reference about a class's presence as often as ImageCAS-X's two observers
  (Table 1: D1 0.969, D2 0.894, OM1 0.944, OM2 0.875, PDA 0.988, PLB 0.962). Half the disagreements are false adds on
  absent cases (at most half of them), the rest are misses on present cases. That gives a per-present-case miss rate
  m of D1 0.021, D2 0.083, OM1 0.033, **OM2 0.156**, PDA 0.006, PLB 0.020.
- **Table 1 does not say whether a miss is a lumen not drawn or a lumen drawn under another name.** So three
  attributions are run: all detection misses (B1), half and half, and all naming errors (B2).
- **Below human level:** m × 1.5, × 2, × 3, and independent per-piece slips (a piece undetected and a piece misnamed,
  2 % or 5 % each). These measure power.

### 1.2 Results (false-fail rate of each class's B, and of the read)

| Lines | Model | D1 | D2 | OM1 | OM2 | PDA | PLB | Read fails (< 4 of 6) |
|---|---|---|---|---|---|---|---|---|
| **R0, as ruled** (0.80 / a − 0.05 / 0.85) | human, misses = detection | 0.00 | 0.06 | 0.02 | 0.18 | 0.00 | 0.01 | 0.000 |
| | human, half and half | 0.00 | 0.06 | 0.02 | 0.14 | 0.00 | 0.01 | 0.000 |
| | human, misses = naming | 0.00 | 0.08 | 0.02 | **0.45** | 0.00 | 0.01 | 0.001 |
| **R2, proposed** (R0 capped at human − 0.10) | human, worst attribution | 0.00 | 0.07 | 0.02 | **0.09** | 0.00 | 0.01 | 0.000 |
| | m × 2, worst attribution | 0.07 | 0.57 | 0.22 | 0.80 | 0.00 | 0.11 | 0.14–0.18 |
| | m × 3, worst attribution | 0.31 | 0.95 | 0.58 | 1.00 | 0.01 | 0.35 | 0.76–0.78 |
| | human + 2 % slips per piece, half and half | 0.24 | 0.22 | 0.26 | 0.14 | 0.17 | 0.32 | — |
| | always calls the class present | 0.01 | 1.00 | 1.00 | 1.00 | 0.02 | 0.04 | — |

R1 (a flat 0.75 / a − 0.07 / 0.80 for every class) is in `results/gate_sim.txt`. It fixes OM2's false-fail (0.17 at
worst) but gives up power everywhere else: at m × 2 the read fails only 2–4 % of the time.

### 1.3 What it shows

1. **OM2's naming line fails a human-level model up to 45 % of the time.** ImageCAS-X's own observers disagree on OM2
   in 12.5 % of cases. With 40 OM2 cases, that is 0.156 of them. If those disagreements are naming errors, a
   human-level model's OM2 naming is 0.844, just under 0.85. The ruling's §8 says a gate that fails a human-level
   model more than 20 % of the time is loosened before submission. OM2's is. Its recall line is close too (0.18).
2. **D2 is at 6–8 %, the rest at ≤ 2 %.** Keep them.
3. **The presence line is the binding one, and it is the right one.** A model that is human-level except for 2 %
   independent slips per piece fails B in 14–32 % of trials, almost all through presence. In the high-prevalence
   classes (D1, PDA, PLB: 96–98 cases) a single-piece branch that is missed or misnamed is a presence disagreement,
   and the human budget is only 1–4 cases. That is power against a sub-human model, not a false alarm. Keep −0.05.
4. **"4 of 6" almost never fails a human-level model** (< 0.001) and fails a model with twice the human error 14–18 %
   of the time and three times 76–78 %. Keep it.
5. **The always-present caller** passes D1, PDA and PLB, which are present in 96–98 % of cases anyway, and fails D2,
   OM1 and OM2 every time. That is what the ruling wanted from presence agreement.

### 1.4 The lines to freeze

| Class | B1 recall ≥ | B1 presence agreement ≥ | B2 naming ≥ |
|---|---|---|---|
| D1 | 0.80 | 0.919 | 0.85 |
| D2 | 0.80 | 0.844 | **0.817** |
| OM1 | 0.80 | 0.894 | 0.85 |
| OM2 | **0.744** | 0.825 | **0.744** |
| PDA | 0.80 | 0.938 | 0.85 |
| PLB | 0.80 | 0.912 | 0.85 |

- **Rule:** each line = min(the ruled line, 1 − m_human − 0.10), m_human as §1.1. It changes only D2's naming and OM2's
  two lines.
- **Read rule:** ≥ 4 of 6, unchanged. V unchanged (not reopened).
- **Caveats, stated in `DECISION.md`:**
  - Table 1's agreement is itself a sample of unknown size. If it is small, the human level is uncertain by a few
    points and OM2's lines could still be tight.
  - Locked counts are "any voxel" counts. Presence is scored at 5 mm. On the 620 the two differ by ≤ 1 % of cases
    for every gated class except PLB (610 vs 601).
  - Classes are simulated independently. A model's errors are likely correlated across classes, which makes "4 of 6"
    less forgiving than shown, not more.

## 2. Item 2: the scorer's definitions, frozen by hash

### 2.1 Definitions (`experiments/Foxtrot/j1f_r2/branch_score.py`, sha256 `902de0ae5d87a29ef68f0baee11c46de33ea51f77e8aa140359ac61de08d598b`)

| Quantity | Definition |
|---|---|
| Centreline | the skeleton of the whole reference tree (255 included, so the tree stays connected), restricted to the class. A piece with no skeleton voxel uses its maximal-EDT voxel |
| Reference branch | a 26-connected piece of the class. R-PDA is two pieces in 10.7 % of the 620 |
| **Detected** (B1) | ≥ 50 % of the piece's centreline lies within 1.5 mm (D3) of predicted vessel of **any** class |
| **Named** (B2) | among a detected piece's covered centreline points, the class of the nearest predicted voxel; right iff the true class is the **strict** plurality (a tie is wrong) |
| **Presence** | reference: class centreline ≥ **5.0 mm** (Delta's line, not v1's 3 mm); prediction: the class's share of the predicted skeleton ≥ 5.0 mm. Skeleton voxels × mean voxel side |
| Recall, naming | pooled over pieces across cases; presence agreement over the 100 cases |
| **Branch tF1** (report) | `segtrain.tf1.tree_f1` at the A1c hash `24441cf8…`, on {class → 1, other vessel → 2}, with **one ostium per reference piece**: the piece's centreline point nearest its parent. tF1 = `per_class[1]` |
| Parent | D1–D3 → LAD; OM1, OM2, Ramus → LCx; PDA, PLB → their side by `posterior_side` (§2.4) |
| **Origin collapse** for V | `labels_r2.collapse4`: D1–D3 → LAD; OM1, OM2, Ramus → LCx; PDA and PLB by `posterior_side` |

**Only D47's answer is frozen.** Q1 is (A): a left PDA/PLB is named PDA/PLB and collapses to the LCx. Options (B) and
(C) are moot, and their collapses are not built.

### 2.2 Self-tests on the 620

**Identity** (each reference scored against itself, all 620): recall, naming and presence agreement are 1.000 for all
eight branch classes (621 D1, 359 D2, 47 D3, 541 OM1, 230 OM2, 154 Ramus, 676 PDA and 620 PLB pieces). Branch tF1 is 1.000 on the 20 fit-check cases.

**Perturbations** (the 20 fit-check cases; recall / naming / presence agreement / tF1):

| Perturbation | D1 | D2 | OM2 | Ramus | PDA | PLB |
|---|---|---|---|---|---|---|
| swap D1 ↔ D2 | 1 / **0** / 0.50 / **0** | 1 / **0** / 0.50 / **0** | 1 / 1 / 1 / 1 | 1 / 1 / 1 / 1 | 1 / 1 / 1 / 1 | 1 / 1 / 1 / 1 |
| delete OM2 | 1 / 1 / 1 | 1 / 1 / 1 | **0** / – / 0.30 | 1 / 1 / 1 | 1 / 1 / 1 | 1 / 1 / 1 |
| every branch → its parent | 1 / **0** / 0.00 | 1 / **0** / 0.50 | 1 / **0** / 0.30 | 1 / **0** / 0.95 | 1 / 1 / 1 | 1 / 1 / 1 |
| thin every branch to skeleton + 1 voxel | 1 / 1 / 1 | 1 / 1 / 1 | 1 / 1 / 1 | 1 / 1 / 1 | 1 / 1 / 1 | 1 / 1 / 1 |

(D3 and OM1 behave as D2 and D1; full table in `results/summary.md`. In "every branch → its parent", PDA and PLB keep
their names because they have no parent relabel in that perturbation.)

- **Swapping D1 and D2** keeps detection at 1 and drops naming and tF1 to 0 for both. Presence agreement falls only
  in cases that have a D1 and no D2.
- **Deleting OM2** drops its recall to 0 and its presence agreement to the share of cases without OM2.
- **Relabelling every branch as its parent** (a types-free network) keeps detection, and naming goes to 0. This is
  why B1 and B2 are separate.
- **Thinning every branch to its skeleton plus one voxel** keeps detection and naming at 1. The 50 % / 1.5 mm rule
  does not punish a thin but correct branch.

### 2.3 The collapse, checked against D25

`collapse4(map13(label))` against icx4's `territory.to_four(label)` on every case flagged or with a left posterior
branch (61): **40 mismatched voxels in 2 cases, all of them "Other"** (the same 40 Delta v1 found). There are none on
left PDA/PLB voxels.

### 2.4 Why PDA and PLB are grouped before the collapse

F-A4 says "a PDA or PLB connected component goes to the vessel it touches most". Applied per class, that **sent 4 879
voxels of left PDA in 5 of the 620 cases to the RCA**. In those cases the left PDA touches only the left PLA, not the
LCx, so its count is 0 vs 0 and the tie went to the RCA. **Grouping PDA with PLB first** (each 26-component of the
two together, by touch, and by EDT distance if it touches neither) gives 0 mismatches. The collapse decides V, so the
per-class reading would have moved LCx voxels into the RCA in every such case of the locked 100 as well.

**The same fact matters for reading T.** Under D47 a left PDA is named PDA, but it lies in Janus 0's LCx territory. T
must admit PDA and PLB inside the LCx territory too (§8, item 5), or T can never name a left-sided posterior branch.

## 3. Item 3: Arm N, dropped

**Recommendation: do not build Arm N in this track's first model, as a gate or as a report.**
- **Its question is already answered twice at zero GPU.**
  - "Does counting beat the network's ordinals?" is F-A9's rule-ordinal reading, from F's own types.
  - "Can 1-F's names sit on Janus 0's vessels?" is reading T, which the plan already scores and can ship.
  - Arm N adds only "a classifier on Janus 0's skeleton instead of the network's head". Published evidence says that
    is the weaker route on automatic trees (Hampe et al. 2024: 0.74 vs 0.91, quoted in the ruling §3.2).
- **It is code on the critical path:** a centreline graph on predicted trees, a segment classifier trained on the
  620's centrelines, and re-projection to voxels. None of it exists beyond the four-class `segtrain.namer`.
- **As a gate it would need a branch-tF1 spread it alone supplies.** §1 replaces that need: the B lines are calibrated
  on a human-level simulation, not on a comparator.
- **When it comes back:** if F-A6's verdict is "not adopted" with V passing and B failing on naming (B2) in ≥ 3
  classes while B1 passes. Then a namer is the targeted repair, and round N+1 builds it with F's failures in hand.

## 4. Item 4: stage 2's loss details, measured on the 620

### 4.1 The Dice term: leaf-Dice (F-A11 confirmed)

`dice_terms.py` puts scripted predictions on real 620 geometry: a 64 mm cube around each case's proximal LAD, with a
30 mm synthetic septal tube. It builds two samples per case:
- **an ImageCAS-X sample:** the band's background is the set {bg, S}; there is no S singleton anywhere;
- **an extended-read sample without D47 Q3's "complete" flag:** the tube is a singleton S1, and the LAD group's voxels
  are the set {LAD-group, S1}.

It scores nnU-Net's soft Dice (per sample, `batch_dice: False` in Janus 0's 3d_fullres plans, `do_bg` off, smooth
1e-5) in three forms.

Mean Dice loss over 10 of the 620 (`results/dice_terms.json`), S1 and OM1 columns:

| Sample, scenario | leaf S1 | ignore S1 | merged S1 | leaf OM1 | ignore OM1 | merged OM1 | marginal CE |
|---|---|---|---|---|---|---|---|
| Extended read, A: tube predicted S1 | 0.391 | 0.391 | 0.0007 | 0.673 | 0.601 | 0.673 | 0.00075 |
| Extended read, B: tube predicted LAD | **0.975** | **0.975** | 0.0008 | 0.673 | 0.601 | 0.673 | 0.00117 |
| Extended read, C: S1 at 0.5 over the LAD group | 0.391 | 0.391 | 0.0008 | 0.685 | 0.601 | 0.685 | 0.00083 |
| Extended read, D: OM1 at 0.5 over the LAD group | 0.391 | 0.391 | 0.0029 | **0.882** | 0.601 | **0.882** | 0.00291 |
| ImageCAS-X, true septal predicted S1 | 1.000 | 1.000 | 0.0004 | 0.673 | 0.655 | 0.673 | 0.00086 |
| ImageCAS-X, septal not predicted | 1.000 | 1.000 | 0.0004 | 0.671 | 0.655 | 0.671 | 0.00081 |

**What it shows:**
- **Merged mass learns nothing about the septal.** S1's loss is the same whether the tube is predicted S1 (A) or LAD
  (B). Every LAD-group voxel counts as an S1 positive whose merged mass is already 1. This is the failure Fidon et
  al.'s Table 2 reports for the marginal Dice.
- **Ignore-for-Dice (Foxtrot v1's) learns the septal but cannot see an intruder.** OM1 predicted on the LAD group's
  set voxels (D) leaves OM1's Dice unchanged, because every set voxel is dropped for every class. Leaf-Dice keeps
  those voxels as OM1 negatives and penalises it.
- **Leaf-Dice does both.** It is the only one of the three that separates A from B and D from A. I withdraw v1's
  ignore-for-Dice.
- **No Dice term stops S1 spreading over its parent (C)** in a read without the complete flag, and the marginal CE does
  not either. Only a read whose LAD group is flagged complete (D47 Q3) makes those voxels singletons. **So stage 2's
  septal precision comes from flagged reads and from ImageCAS-X's background outside the band, not from the loss.**
  Stage 2's gate (§4.4) measures it.
- **On ImageCAS-X samples the Dice term is inert for the six classes.** With no singleton, a class's per-sample Dice
  is flat; its gradient per voxel is about 8 × 10⁻⁵ of the CE's. The band, through the CE alone, decides what
  ImageCAS-X teaches about untraced branches.

### 4.2 The band: by parent segment, 15 mm, widened by a rule

`band.py` on 27 of the 620 (ids divisible by 20).
- **Regions:**
  - **S:** around the LAD trunk;
  - **N:** around the RCA's first 30 mm and the LCx's first 20 mm (SN, conus);
  - **R:** around the RCA from 20 mm to 80 % of its arc (right marginals).
- Medians over cases:

| w (mm) | S band cm³ | N band cm³ | R band cm³ | union cm³ | union / 256³ patch | union / background within 25 mm | traced branch volume within w of the LAD |
|---|---|---|---|---|---|---|---|
| 4 | 11.1 | 4.6 | 6.3 | 20.0 | 0.009 | 0.019 | 0.064 |
| 8 | 38.8 | 18.2 | 22.6 | 69.1 | 0.033 | 0.065 | 0.129 |
| 15 | 129.7 | 72.1 | 78.6 | 231.3 | 0.110 | 0.213 | 0.243 |
| 25 | 362.1 | 238.0 | 232.7 | 634.6 | 0.303 | 0.586 | 0.299 |

The traced tree is a median 1.96 cm³, so even the 8 mm band releases 35 times the tree's own volume. The S band lies
evenly along the LAD (proximal / mid / distal thirds 0.37 / 0.28 / 0.35 at 15 mm), not only where septals leave.

- **Synthetic septals:** straight 1 mm tubes from the LAD at 15, 30 and 45 % of its arc, aimed at the nearest PDA
  voxel. The septum spans the two interventricular grooves. The column is the share of the tube inside the band,
  where the CE term does not penalise it:

| Septal length | w = 4 | w = 8 | w = 15 | w = 25 |
|---|---|---|---|---|
| 10 mm | 0.47 | 0.88 | 1.00 | 1.00 |
| 20 mm | 0.24 | 0.45 | 0.83 | 1.00 |
| 30 mm | 0.16 | 0.30 | 0.56 | 0.92 |
| 40 mm | 0.12 | 0.23 | 0.42 | 0.70 |
| 60 mm | 0.08 | 0.15 | 0.28 | 0.47 |

81 tubes on 27 cases; under 1 % of any tube's centreline runs through a traced vessel.

**What it shows:**
- **8 mm (Foxtrot v1) is too narrow.** Any septal longer than about 10 mm is mostly outside it. Outside the band,
  ImageCAS-X's singleton background penalises every predicted septal voxel, in 620 cases against a few dozen extended
  reads. A network trained that way learns septals that stop at the band's edge.
- **15 mm (Crucible) covers a 20 mm septal almost wholly and a 30 mm one by half.** It releases 21 % of the
  background within 25 mm of the tree, about 11 % of a 256³ patch.
- **25 mm covers 30 mm septals, but releases most of the background near the tree (59 %).** That gives up most of
  the false-positive pressure that keeps S1 off the myocardium and the fat.
- **The septal length is not known from this data.** ImageCAS-X traced none, and I found no CT series that states it
  in mm. The sweep is a sweep, not a measurement.

**Proposed (pre-registered before J1F-2):**
1. **The band is per region (S, N, R), not one ring around the whole tree.** SN and conus sets apply only near the
   proximal RCA and LCx, and septal sets only near the LAD.
2. **Default w = 15 mm.**
3. **Widened by the first reads, by rule:** before J1F-2, for each class, take the 95th percentile of the distance of
   its drawn centreline from its region in the trainable extended reads. If that is above 15 mm, the class's band is
   that percentile, capped at 25 mm. It is computed on CPU and posted with its sha256 before J1F-2 starts.
4. **Traced-class voxels are never in a set**, whatever the band. Within 15 mm of the LAD lie 24 % of the traced
   branch volume (D1–D3 and others). They stay singletons, so an S head can never take a diagonal's voxels from
   ImageCAS-X. §4.4 checks the same thing on predictions.

### 4.3 What the band does not fix

- **Conus from its own aortic ostium** is outside N whenever it does not leave the RCA. Its voxels on ImageCAS-X are
  singleton background more than 15 mm from the RCA. That is a reason to report the conus, not decide on it, until
  pool reads show where it lies (§6 puts it at counts only anyway).
- **An SN off the circumflex** (D47 Q1) is covered by N's LCx part.

### 4.4 Stage 2's gate (Bridge's leakage check), pre-registered

J1F-2 is read on the locked 100 once, after training, in a fixed sequence:

| # | Test | Passes when |
|---|---|---|
| V′ | the vessels hold against the **shipped stage-1 model** | V's rule (−0.02 bound, −0.03 per class, L3, FP) |
| B′ | every class that shipped in stage 1 still passes | its §1.4 lines |
| L | **leakage:** the share of each traced parent group's reference centreline (LAD group, LCx group, RCA group) that J1F-2 predicts as any stage-2 class | ≤ **0.02** for each group |
| S | each new class on D35 | §6's tier: decide (n ≥ 30), report (n ≥ 20), else counts only |

- **Why 0.02:** a leakage of 0.02 moves at most 0.02 of a traced class's centreline out of its name. That is within
  V's −0.03 per-class tolerance, so a model that passes L cannot fail V through leakage alone.
- **Baseline:** stage 1 has no stage-2 head, so its leakage is 0 by construction. L needs no comparator.
- **A class that fails S ships folded into its parent.** Failing V′, B′ or L means J1F-2 is not adopted, and the
  stage-1 model stays.

## 5. Item 5: reads per class, a rule (F-A11's thresholds kept)

**Recommendation: keep F-A11's provisional thresholds as the rule. Run neither Job B nor the learning curve.**

| | Job B (Bridge) | Learning curve (Delta) | Rule (F-A11) |
|---|---|---|---|
| Cost | ≈ 33 GPU-h | ≈ 45 GPU-h | 0 |
| What it measures | how a warm, grown head learns a **traced** ImageCAS-X class from k ∈ {20, 60} cases | the same, at more k | — |
| What stage 2 needs | how a head learns an **untraced** class from **pool** reads (other scanners, other annotators, the six classes ImageCAS-X never drew) | | |
| Worst case if wrong | — | — | one J1F-2 run (≈ 15 GPU-h) trained too early, caught by stage 2's gate (§4.4), and re-run when reads grow |

- **Why not the experiment.**
  - Its transfer is weak: OM and PLB thinned inside ImageCAS-X keep ImageCAS-X's protocol, scanner mix and full-tree
    context. Septals, SN, conus and RMA come from a different source with different annotators.
  - It costs more than the error it protects against. Both designs cost 2–3 J1F-2 runs to avoid at most one.
  - Its hold-out inside the 620 takes cases from J1F-A's training or needs its own run, and it must wait for J1F-A
    anyway.
- **What makes the rule safe.**
  - Training a class waits on counts, never dates (F-A11).
  - Stage 2 is gated (§4.4): a class trained too early fails its report line on D35 or leaks into traced classes.
    Both are caught before anything ships.
  - The first evidence on "how few reads" comes free: D3 (47 training cases) and Ramus (149) are trained in J1F-A and
    reported with n and CI (F-A9). That is a report, never a steer (F-A7).
- **What would change this:** if the first J1F-2 fails its gate with the class's read count within 1.5× of the
  threshold, round N+1 raises the threshold to 1.5× before the next try. That rule costs nothing now.

## 6. Item 6: the scoring set for the six untraced classes (D47 Q6: D35 in extended mode)

`d35_yield.py`: exact binomial over D35's 35 patients (A33). π is the share of patients whose extended read draws the
class, which is visibility × the annotator tracing it (D47 Q7). Two reads per patient do not add patients.

| π | E[n] | P(n ≥ 20), the report line | P(n ≥ 30), the decide line | ± on a recall of 0.8 at E[n] |
|---|---|---|---|---|
| 0.3 | 10.5 | 0.001 | 0.000 | 0.23 |
| 0.5 | 17.5 | 0.25 | 0.000 | 0.18 |
| 0.6 | 21.0 | 0.70 | 0.001 | 0.16 |
| 0.7 | 24.5 | 0.96 | 0.03 | 0.15 |
| 0.8 | 28.0 | 1.00 | 0.27 | 0.14 |
| 0.9 | 31.5 | 1.00 | 0.87 | 0.14 |

**Patients needed for P(n ≥ 30) ≥ 0.8:** 35 at π = 0.9, 46 at 0.7, 66 at 0.5, 113 at 0.3.

**What this means (no prevalence is assumed as fact: ImageCAS-X traced none of these, so the project has no number):**
- **S1** is the only class likely to be drawn in ≥ 70 % of patients once annotators trace beyond the seed (D47 Q7).
  D35 can then **report** it (n ≥ 20, ± 0.15) but probably not decide on it.
- **S2, S3, SN, conus, RMA:** counts only on D35, as the ruling recommended. A class at π ≈ 0.5 reaches the report
  line in a quarter of draws.
- **No untraced class ships unfolded on D35 alone.** The decide line needs π ≥ 0.9.
- **The first measurement that settles this is free.** D35's first extended reads give each class's π. If S1's π is
  ≥ 0.9, D35 decides it. If not, the next round asks the lead for a larger held-out pool set (a D35 question, ruling
  Q6), sized from the table above.
- **Pre-registered:** stage 2's `DECISION.md` prints each class's n on D35 and its tier (counts / report / decide)
  before any stage-2 prediction of D35 is scored.

## 7. Item 7: Shi et al.'s numbers, none quoted

Foxtrot v1 and v2 quote no number from Shi et al. (arXiv:2007.03868; MedIA 70:101979). The method (the marginal CE)
is not in doubt, and nothing in this plan depends on a table value. **Recommendation:** the judge drops both sets of
numbers from the record unless the advocates who cite them give the table and the row.

## 8. Item 8: the `role:swe` spec for `trillium/janus1f`, frozen (F-A12)

**Base.** `trillium/janus1l` as **L-A21** freezes it (track 1-L round 2), not #306's round-1 text. Shared parts stay
shared: `janus1f` imports `janus1l`'s split guard, sealed refusals, plans check, chain/resume, looks ledger and
`status`, and only the items below are 1-F's own. The diff is written as a patch on `janus1l` so a later change to the
shared part reaches both.

**Three round-1 amendments that L-A20/L-A21 have since shown to be wrong in form, corrected here:**

| F-A text | What L-A20/L-A21 found | 1-F spec |
|---|---|---|
| F-A2 "Janus 0's `plans.json`, byte-identical" | `move_plans_between_datasets` rewrites `dataset_name` and `image_reader_writer`, so a sha256 equality always fails | L-A21's plans check: equal to Janus 0's once those two fields are removed; a changed percentile refuses |
| F-A2 (silent) | `on_train_start` copies `dataset_fingerprint.json` from the preprocessed folder; without it the run dies at step 1 | Step T's copy of Janus 0's fingerprint is placed in Dataset 719's preprocessed folder; no `extract_fingerprint` |
| F-A2 "fold-0 validation is the locked 100, for display only" | nnU-Net's final validation would predict and write the locked 100 (1-L round 2 §3.4, the final-validation leak) | `splits_final.json`: two identical entries, train = the 620, **val = the 20 fit-check cases** (inside the 620; `results/fitcheck20.json`, pin `3f3b696c…1330`). `perform_actual_validation` returns at once. Nothing in training ever touches the locked 100 |

**1-F's own items:**

1. **Labels.** `prepare` writes Dataset 719 from `$KEEP`'s (or `$SCRATCH/icx4/icx`'s) 620 ImageCAS-X labels with
   `experiments/Foxtrot/j1f_r2/labels_r2.py`'s `map13` (Delta's map, D47 Q1 = A, F-A3's ignore), moved into
   `src/segtrain/j1f_labels.py`. `JANUS1F_LEFT_PDA` is gone: D47 fixed it. The launcher asserts F0-r2's counts (§13).
   `dataset.json` declares 13 labels and `ignore: 255`.
2. **Loader.** `finetune_load.load_finetune_source(..., parent_map={5:2, 6:2, 7:2, 8:3, 9:3, 10:3, 11:4, 12:4})`:
   every non-head tensor strict and bitwise; every `seg_layers` 1×1×1 conv (deep supervision included) grows from 5 to
   13 rows, child = parent's row, territory biases −log k (k = 4, 4, 3; LM and bg unchanged). Two refusals on a
   random batch: territory sums equal Janus 0's within 1e-5, **and** the hierarchical decode equals Janus 0's argmax on
   every voxel (F-A2). PDA and PLB copy the RCA's row (D44's parent). A left-sided PDA/PLB therefore starts in the
   RCA territory's sum and must win its voxels from the LCx side by training; F's origin collapse puts them back in the
   LCx for V (§2.4).
3. **Trainer** `nnUNetTrainer_janus1f`: `janus1l`'s trainer with 500 epochs × 250 iterations (A17a warm-up 2500
   iterations to 1e-2, then poly), DiceCE unweighted, ignore 255, mirroring off, `SEGTRAIN_SAVE_EVERY=10`, and a
   **fit-check hook**: at the end of epochs 150 and 300 it predicts the 20 fit-check cases (sliding window, no TTA,
   logits), decodes hierarchically, scores per-class Dice against their 1-F labels, writes `fitcheck.json`, and at 150
   writes `STALL` if any of D1, OM1, PDA, PLB is below 0.10 (F-A5). Cost ≈ 20 × 30 s ≈ 10 min of GPU per check. A
   chain boundary falling between epoch 140 and 150 does not skip it: the hook keys on `current_epoch`, and
   `fitcheck.json` lists the epochs it holds.
4. **Predict.** The locked 100 with `--save_probabilities --disable_tta`, so decoding is from probabilities, never
   from nnU-Net's argmax export (F-A4). a2's prediction, if a2 ran, in the same pass.
5. **Decode** (`janus1f decode`, CPU): reading F (hierarchical) and reading T (Janus 0's argmax territory from
   `$KEEP/predictions`, then 1-F's within-territory argmax). **Under D47, T's LCx territory admits PDA and PLB as well
   as LCx, OM1, OM2 and Ramus** (§2.4): without it, T could never name a left-sided posterior branch. T's four-class
   output is Janus 0's territory map itself, not a collapse of T's names; `decode` asserts it is bit-equal to Janus 0's
   prediction.
6. **Score** (`janus1f collect`, CPU): V on F's origin collapse (`labels_r2.collapse4`, PDA and PLB grouped) with the
   A1c scorer and Janus 0's in-job aortas; B with `branch_score.py` moved into `src/segtrain/branch_score.py`
   **unchanged in its logic**, frozen by the sha256 of the moved file, posted on #303 before `collect` runs; F-A6's
   fixed sequence with §1's lines; F-A9's reports; `DECISION.md`; the looks ledger refuses a second `collect`.
7. **Refusals** (each with a failing fixture in `check`): a sealed or locked id in training; the split file's hash
   (`19b832fe…4dd3`) or either list pin; the plans check; the fingerprint missing; an identity error at step 0; a
   dataset id in use; a `collect` without the posted scorer hash; F0-r2's counts not matching.
8. **Fir specifics.** `#SBATCH --account=def-aso22 --gpus-per-node=h100:1 --cpus-per-task=12 --mem=280G
   --time=23:50:00`; `$KEEP` first, `$SCRATCH/icx4` second; if both lack the CTs, `fetch` re-downloads the 620 + 100
   CTs from Zenodo by range requests (never a sealed id), and the labels the same way (the 620 only, plus the locked
   100's labels inside `collect`'s scorer only).
9. **Self-tests in `check`**, beyond L-A21's nine: the loader's two identity checks on a toy network; the hierarchical
   decode against a plain argmax on a parent-copied head (the plain argmax must differ, Atlas's 2.5 %); the scorer's
   identity and perturbation table (§2) reproduced on two committed 620 fixtures; the collapse on a left-dominant
   fixture whose PDA touches only its PLB.

## 9. Item 9: the warm-start source, Janus 0 either way

**Recommendation: J1F-A starts from Janus 0, and V compares against Janus 0, even if Janus 1-L is adopted before
J1F-A is submitted.**
- **The baseline must be on Fir and must exist before training.** Janus 0's locked-100 predictions and aortas are on
  Fir (F-A8) and in Step T's `$KEEP`. Janus 1-L's are on Trillium. Re-predicting 1-L on Fir adds a cross-cluster step
  that F-A8 rejected for the same reason.
- **1-L's adoption rule is about lumen width at a threshold t_C (L-A14, L-A15).** 1-F's vessel guard is at argmax
  (§7 of the ruling). Starting 1-F from an ensemble exported at t_C would make the start and the guard disagree on
  what "the vessels" are.
- **1-L is an ensemble of two fine-tunes** (L-A14). A parent copy of an ensemble is not defined. Picking one member
  gives up what made 1-L better.
- **What 1-L's adoption changes instead (reports only):**
  - **T_L:** 1-F's within-territory names on 1-L's exported territories (on Trillium, CPU after 1-F's probabilities
    are copied). It shows whether 1-F's names transfer to the vessel model of record.
  - **Δ vs 1-L:** F's collapsed vessels against 1-L's locked-100 predictions, beside V. Never a gate.
- **When to revisit:** the first pool fine-tune of 1-F (A36's path), when the vessel model of record will be 1-L's.

## 10. Item 10: one census of record for the 620

**Run:** all three round-1 twig methods on the same 620 labels in one pass (`pass1.py`; Delta's `side_branches`,
Foxtrot's `twigs`, Crucible's skan rule re-implemented with its "minus the longest").

| Method | LAD cases ≥ 3 / 5 / 10 mm | LCx ≥ 5 mm | RCA ≥ 3 / 5 mm |
|---|---|---|---|
| Delta (class-mask skeleton, off the longest path) | 7 / 5 / 3 | 1 | 3 / 2 |
| Foxtrot (the same idea, own graph code) | 6 / 4 / 3 | 1 | 3 / 2 |
| Crucible (whole-tree skeleton, pure end branches) | 15 / 13 / 11 | 9 | 3 / 3 |

**Why Crucible's is higher:** 9 of its 13 LAD cases and all 9 of its LCx cases are the **9 training cases with no left
main** (separate LAD and LCx ostia). On the whole-tree skeleton, the stub from each ostium to the first junction is a
pure LAD (or LCx) end branch, and the rule counts it as a twig. Without those, Crucible's LAD count is 4, the same as
the others. The methods agree; the ruling's "lower cut-off finding fewer" was this artefact.

**Of record (proposed):**
- **Trunk twigs:** Delta's method at **5 mm**. The LAD carries an unnamed side branch in **5 of 620** cases (7 at
  3 mm, 3 at 10 mm), the LCx in 1, the RCA in 2. This is what "ImageCAS-X traced no septal, SN, conus or RMA" rests on.
- **Dominance, from labels by the PDA:** right 570, left 36, both PDAs 2, no PDA 12 (10 of them with a left PLA only).
  **59 cases have a left PDA or PLA**, the number that matters for D47 Q1. `Descriptors.xlsx` is ImageCAS-X's own
  variable and is quoted only beside it, never mixed with it.
- **Stage-1 labels** (`labels_r2.map13`, D47 Q1 = A, F-A3): D3 in **47** cases; D4 → LAD in 2; LCx-side "Other" → LCx
  in 20; **8 "Other" pieces → ignore** (467 voxels, 0.002 % of the tree); 1 small two-sided piece → nearest.
- **Presence at 5 mm vs any voxel** (gated classes): D1 610/611, D2 358/359, OM1 540/540, OM2 227/229, PDA 606/608,
  PLB 601/610.

## 11. Item 11: the consequences of D47 Q8 and Q9

**Q8 (a2 runs if the allocation allows, report only).**
- a2 = fold 1 of the same `splits_final.json` (two identical entries), concurrent with a1, its own seed. +≈ 29 GPU-h.
- It is **never** read for V, B, a stop or a checkpoint. F-A5's stall check reads **a1's** `fitcheck.json` only;
  a2's is printed beside it.
- Its reports: a2's V and B numbers, |a1 − a2| per class, and σ_g = |a1 − a2|/√2 (as L-A24), so the next 1-F recipe
  claim has its first between-run spread on branch classes (A37).
- **No ensemble.** Unlike 1-L's L-A14, D47 Q8 says report only. If a later round wants a two-network 1-F, it
  pre-registers it then.
- **If allocation is short,** a1 alone runs and nothing else changes.

**Q9 (naming).**
- The reading that F-A6 ships (F or T) is **Janus 1-F.1**; the adopted model is **Janus 1-F**.
- a2, T_L, the rule-ordinal reading and every argmax or report export take no number.
- `DECISION.md` writes the number only on an "adopted" verdict.
- Stage 2's first shipped model is the next read in this track: **Janus 1-F.2** if read, as D34 numbers runs within
  a track.

## 12. Corrections to round-1 text that this round finds

| Where | Round-1 text | Correction | Why |
|---|---|---|---|
| F-A2 | plans "byte-identical" | L-A21's plans check | `move_plans_between_datasets` rewrites two fields (L-A21) |
| F-A2 | (silent on the fingerprint) | copy Janus 0's `dataset_fingerprint.json` (L-A20) | nnU-Net 2.8.1 dies at step 1 without it |
| F-A2 | fold-0 val = the locked 100, display only | val = the 20 fit-check cases, final validation a no-op | the final-validation leak (1-L round 2 §3.4) |
| F-A4 | "a PDA or PLB connected component goes to the vessel it touches most" | **PDA and PLB grouped first**, then by touch, else by distance (`labels_r2.posterior_side`) | taken per class, it sent 4 879 voxels of left PDA in 5 cases to the RCA: those left PDAs touch only their left PLA (§2.4) |
| F-A6, T | "Janus 0's argmax territories, with J1F-A's within-territory argmax" | T's LCx territory also admits PDA and PLB | under D47 Q1 a left PDA is named PDA but lies in Janus 0's LCx territory |
| F-A6, V | L3 | L3 reads the scorer's `recall` (L-A17) | the same correction as track 1-L |
| Master plan §5, F0 | expected `make_labels_1f.py` v1 printout | F0-r2 below | v1's converter used set codes that D47 and F-A3 have removed |

## 13. Step T and F0 have not run: what each would change

**Step T** (D46 Q1, D47 Q2; the lead runs it; Fir).
- **Until it runs, nothing here changes, but J1F-A cannot be launched**: Janus 0's checkpoint, plans, fingerprint,
  aortas and locked-100 predictions exist only on Fir scratch, which purges about 2026-12-20.
- **If it shows Janus 0's logs with class-weighted CE** (L-A20's check), J1F-A's DiceCE "unweighted" no longer matches
  Janus 0's recipe. Round 3 decides, as for 1-L.
- **If the purge comes first,** the baseline predictions are gone. V would then need Janus 0 re-predicted on Fir
  (≈ 1 GPU-h). That is the cross-cluster-free version of F-A8 and changes no margin. The checkpoint itself can only
  come back from wherever else it survives (ruling §8).

**F0-r2** (replaces the master plan's F0; Fir login node, CPU, 0 GPU-h; the lead runs it). It checks that Fir's
ImageCAS-X copy gives the same 620 and the same stage-1 labels as this PR.

```sh
module load StdEnv/2023 python/3.11.5
cd $SCRATCH/asclepius && git -C repo fetch origin dev && git -C repo checkout dev && git -C repo pull --ff-only
source $HOME/icx14-venv/bin/activate
J=$SCRATCH/asclepius/repo/experiments/Foxtrot
mkdir -p $SCRATCH/j1f && cd $SCRATCH/j1f
python $J/j1f/split620.py $SCRATCH/icx4/icx $SCRATCH/asclepius/repo/trillium/icx4/sealed_test.json split620.json
python - <<'EOF'
import json, hashlib
d = json.load(open('split620.json'))
for k in ('train620', 'locked100'):
    print(k, hashlib.sha256('\n'.join(sorted(d[k])).encode()).hexdigest())
EOF
srun --account=def-aso22 --time=2:00:00 --cpus-per-task=8 --mem=32G python - <<'EOF'
import json, os, sys, numpy as np, nibabel as nb
sys.path[:0] = [os.path.expandvars('$SCRATCH/asclepius/repo/experiments/Foxtrot/j1f_r2')]
import labels_r2 as L
ids = json.load(open('split620.json'))['train620']
tot = {'d3': 0, 'd4_to_lad': 0, 'other_lcx': 0, 'other_nearest': 0, 'other_ignore': 0}
for c in ids:
    im = nb.load(os.path.expandvars(f'$SCRATCH/icx4/icx/{int(c[1:]) + 1}.coronary.nii.gz'))
    raw = np.asarray(im.dataobj).astype(np.uint8); raw = raw[L.crop(raw, 4)]
    _, info = L.map13(raw, np.array(im.header.get_zooms()[:3], float))
    for k in tot: tot[k] += info[k]
print(tot)
EOF
```

**Expected** (this PR, on Zenodo's copy of the 620):
- `train620 1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152`;
- `locked100 bbd9c687818956e2d5664b06fd8c8bd02ddb031e9b9d08036d59cc0e1a4d5895`;
- `{'d3': 47, 'd4_to_lad': 2, 'other_lcx': 20, 'other_nearest': 1, 'other_ignore': 8}`.

The label path is the one round 1's F0 already uses (`make_labels_1f.py` lists `$SCRATCH/icx4/icx` directly).
**Any difference in the three lines: stop, tell the PM.** A difference in
the counts with matching pins means Fir's label copy differs from Zenodo's.

## 14. Cost

Unchanged from F-A10: J1F-A ≈ 29–31 GPU-h (ceiling 47.7), a2 + ≈ 29 (D47 Q8). This round adds **two fit checks of
≈ 10 GPU-min each** inside J1F-A, and **removes** the 33–45 GPU-h that Job B or a learning curve would have cost.
Nothing here needs a GPU now. **No training job starts before round 3** (#303).

## 15. What would change this plan

| Observation | Change |
|---|---|
| F0-r2's counts differ | Stop; the PM finds which copy differs |
| Step T shows class-weighted CE in Janus 0's logs | J1F-A's loss is re-decided in round 3 (as 1-L) |
| D35's first extended reads give S1 π ≥ 0.9 | S1 can be decided on D35 (§6) |
| The first extended reads put the 95th percentile of drawn septal distance beyond 15 mm | The band widens by §4.2's rule, before J1F-2 |
| A J1F-2 class fails its gate with its count within 1.5× of the threshold | Its training threshold rises to 1.5× (§5) |
| V passes, B fails on naming in ≥ 3 classes with B1 passing | Round N+1 builds a namer (Arm N's idea) for those classes (§3) |
| ImageCAS-X's Table 1 sample size is found to be small | §1's lines are re-simulated with its sampling error before J1F-A is submitted |

## 16. Code and results in this PR

- `experiments/Foxtrot/j1f_r2/`:
  - `labels_r2.py` (sha256 `7d1441e3…f74`): the stage-1 map (D47 Q1 = A, F-A3), `posterior_side` and `collapse4`;
  - `branch_score.py` (sha256 `902de0ae…598b`): the scorer to freeze;
  - `pass1.py`, `recheck_collapse.py`, `gate_sim.py`, `band.py`, `dice_terms.py`, `d35_yield.py`, `summarise.py`;
  - `results/`: `summary.md` / `summary.json` (every table here), `gate_sim.json` / `.txt`, `pass1_620.jsonl`
    (per-case label statistics, no voxels), `selftest_fitcheck20.jsonl`, `band27.jsonl`, `recheck_collapse.json`,
    `dice_terms.json` / `.txt`, `d35_yield.json`, `fitcheck20.json`.
- Note: [[Foxtrot - On the 620, human-level branches false-fail OM2's round-1 gate up to 45 percent of the time, leaf-Dice is the only Dice term that both learns a drawn septal and stops an intruder, and the origin collapse needs PDA and PLB grouped]].
- Labels fetched: the 620 training labels only. Nothing else was downloaded or opened. No GPU or cluster job was run.

