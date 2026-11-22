---
tags: [plans, candidate, janus-1f, branches, partial-labels, fir, round2, D44, D45, D47]
author: Atlas
track: 1-F
round: 2
version: 2
updated: 2026-11-22
issue: christianGRogers/Asclepius#303
---

# Atlas v2 (Janus 1-F): the ruled lines fail a human reader on OM2 most of the time; freeze per-class lines calibrated to ImageCAS-X's own second analyst, a scorer of record, and a launcher that never validates on the locked 100

## 0. In one paragraph

The plan in force is Delta v1 as amended (F-A1 to F-A13), and D47 has answered Q1–Q9. This candidate does not
reopen it. It answers the ruling's §5 items 1–11 with CPU evidence from the D45 training 620. Four results change
what round 3 should freeze.

1. **B's lines, as ruled, fail a human-level model.** I simulated a model that disagrees with ImageCAS-X's reference
   exactly as ImageCAS-X's own second analyst does (Table 1, read from the paper). At the locked-100 counts:
   - OM2 fails **58 %** of the time (46–81 % across the error mixes I tried);
   - OM1 up to 50 %, D2 6–22 %.
   - The "4 of 6" verdict itself rarely fails (≤ 7 %), so the cost is not a lost model. It is **human-level classes
     folded into their parent and listed as failures**.
   - Per-class lines, each set at a human-level model's 5th percentile in the worst error mix, keep every class's
     false-fail at **≤ 7.1 %** and still fail a model 0.10 worse than human in omission **100 %** of the time (§2.1).
2. **The scorer can be frozen now** (`experiments/Atlas/j1f_r2/j1f_scorer.py`). It implements F-A3's labels, F-A4's
   origin collapse under D47 Q1, and every B measure. The contact collapse reproduces D25 on the 620 except for "Other"
   voxels in 2 cases (§2.2).
3. **The band is a trade, measured.** Only 5.5 % of traced side-branch pieces lie wholly within 8 mm of their parent,
   and 23 % within 15 mm, so no band contains an untraced branch whole. A 15 mm band releases ≈ 433 cm³ of
   background per case. I recommend 15 mm **restricted by territory per class**, with a pre-registered leakage gate
   (§2.4).
4. **The launcher must not validate on the locked 100, and must not save probabilities.** This carries track 1-L's
   round-2 finding (L-A21) to 1-F. Saving 13-channel probabilities would be very large, so prediction must decode
   inside the predictor (§2.8).

Arm N, my round-1 comparator, is **dropped** (§2.3).

## 1. Inputs, and what I did not read

**Binding:**
- D45 (classes, split, Fir);
- D46 (track 1-L's answers);
- **D47** (1-F's Q1–Q9, all as recommended). Q1 (A): left-sided PDA/PLB and a circumflex SN keep their names and
  collapse to the vessel they leave;
- D8, D22, D25, D27/D32, D35, D40 as amended by D47 Q4.
- The ruling's amendments F-A1 to F-A13.

**Read:**
- the ruling;
- the 1-F master plan;
- my v1;
- the round-1 candidates (Delta v1, Bridge v1 and Crucible v1, for specific points);
- track 1-L's round-2 ruling (L-A13 to L-A25), because #306's spec is the base of 1-F's launcher;
- ImageCAS-X (arXiv:2608.30404) Table 1 and Supplementary B, from the PDF;
- Shi et al. (arXiv:2007.03868) Tables 3, 5, 6 and 7.

**Data (all CPU, in this container):**
- ImageCAS-X segmentations of the **620 training cases only** and `Descriptors.xlsx`, fetched by
  `experiments/Atlas/j1f_r2/fetch_620.py`. Before any read it asserts the 620's pin (`1350cb1f…1152`) and that no
  member is a locked-100 case.
- My 620 equals the 620 in `experiments/Delta/j1l_r1/janus1_split_proposal.json` (sha256 `19b832fe…4dd3`, #306).
- No locked-100, sealed-80 or quality-0 label was fetched or opened.
- The locked-100 counts I use are Delta v1's published label counts (F-A7).
- No TotalSegmentator twin was used, and nothing ran on Fir, SciNet or Trillium.

**Independence.** I did not open any round-2 candidate of this track or any `exp/j1f-r2-*` branch.
- One broad `grep` of `vault/Plans/Experiments/` for "Table 1" printed the **title and four lines** of Delta's round-2
  Experiments note: OM2's gate failing a human reader "a third of the time", 36 %, and a PDA/PLB swap-rate calibration.
- I did not open the note. My simulation (§2.1) was designed before that and is my own, and its model differs: I
  calibrate to Table 1's **clDice** mixture, not a swap rate.
- I say so here so that the judge can weigh the agreement accordingly.

## 2. The eleven items

### 2.1 Item 1: B's lines, frozen by a human-level simulation

**The model** (`gate_sim.py`). A "human-level" 1-F disagrees with the reference as ImageCAS-X's second analyst does
on the test 160 (Table 1):

| Segment | n (both drew) | Agreement % | DSC | clDice |
|---|---|---|---|---|
| D1 | 155 | 96.9 | 79.9 ± 28.7 | 85.0 ± 30.2 |
| D2 | 91 | 89.4 | 82.9 ± 24.3 | 88.1 ± 25.3 |
| OM1 | 132 | 94.4 | 74.1 ± 32.3 | 79.8 ± 34.2 |
| OM2 | 46 | 87.5 | 77.7 ± 29.1 | 83.7 ± 30.6 |
| R-PDA | 150 | 98.8 | 82.6 ± 21.9 | 88.4 ± 22.3 |
| R-PLA | 147 | 96.2 | 83.6 ± 18.6 | 89.4 ± 18.4 |

Table 1's own definitions: "Agreement is the percentage of scans in which both analysts either annotate that segment
or both omit it. Remaining metrics were computed over the n scans in which both analysts annotated the segment."

Per reference piece:
1. **Omission.** With probability m_c the reader draws no c in the case, and the piece is missed.
   - Table 1's 160·(1 − A) disagreeing scans split evenly between "reference only" and "reader only", since two
     analysts are exchangeable.
   - So m_c = 1.6 % (D1), 8.5 % (D2), 3.3 % (OM1), **17.9 % (OM2)**, 0.6 % (PDA), 2.0 % (PLB).
2. **Both drew it.** The pair's clDice is fitted as a two-part mixture to Table 1's mean and SD.
   - With probability p0_c the reader's c is elsewhere (coverage ≈ 0): p0 = 0.11, 0.07, **0.15**, 0.11, 0.05, 0.03.
   - Otherwise coverage ~ Beta(h_c ≈ 0.93–0.95, SD σ_h).
   - The low part is either an **ordinal shift**: the piece is detected but misnamed, with share s.
   - Or a **stub**: the piece is missed, with share 1 − s.
3. **Scenarios:** σ_h ∈ {0.05, 0.08, 0.12} and s ∈ {0, 0.5, 1}. clDice has no 1.5 mm tolerance and also carries
   precision, so it understates coverage. The rates below are upper bounds in that respect.

**Inputs:**
- The locked counts are 98, 64, 84, 40, 96, 96 of 100.
- Pieces per case come from the 620 (PDA in two or three pieces in 10.7 % of cases, PLB in two in 1.6 %).
- 2000 replicates per scenario, 8000 for the scenarios that set the lines.

**As ruled** (recall ≥ 0.80, naming ≥ 0.85, presence ≥ A − 0.05). False-fail of a human-level model, central
scenario (σ_h 0.08, s 0.5), with the range over the nine scenarios in brackets:

| | D1 | D2 | OM1 | OM2 | PDA | PLB | verdict (< 4 of 6) |
|---|---|---|---|---|---|---|---|
| fail rate | 0.3 % [0.05–11] | 7.2 % [6–22] | 4.7 % [4.7–50] | **58 %** [46–81] | 0 % [0–0.05] | 0.15 % [0.05–0.15] | 0.25 % [0.25–7.4] |
| driven by | — | recall, presence | naming (s = 1), recall (s = 0) | **recall**: E[recall] = 0.72–0.82 < 0.80 | | | |

- **The ruling's §8 trigger fires.** OM2 fails a human-level model more than 20 % of the time in every scenario, and
  OM1 and D2 do in some. "That gate is loosened before submission."
- **The cause is structural, not noise.** A human omits OM2 in 18 % of the cases where the other analyst drew it, so
  no recall line at 0.80 can be passed by a human on OM2.

**Proposed (P1): per-class lines.** Each line is the 5th percentile of a human-level model's statistic, in the worst
scenario for that statistic, rounded **down** to 0.01:
- recall: s = 0, σ_h 0.12;
- naming: s = 1, σ_h 0.05;
- presence: the binomial.

| Class | recall ≥ | naming ≥ | presence ≥ | false-fail, 9 scenarios |
|---|---|---|---|---|
| D1 | 0.81 | 0.83 | 0.94 | 2.0–6.3 % |
| D2 | 0.76 | 0.86 | 0.84 | 3.1–6.4 % |
| OM1 | 0.75 | 0.78 | 0.90 | 2.1–7.1 % |
| OM2 | 0.60 | 0.78 | 0.81 | 3.7–7.1 % |
| PDA | 0.89 | 0.90 | 0.97 | 1.5–6.0 % |
| PLB | 0.89 | 0.92 | 0.94 | 2.7–4.9 % |
| **verdict (< 4 of 6)** | | | | **≤ 0.25 %** |

**Power** (central scenario): false-pass is what matters. Each row is a model worse than human, with the share of
replicates in which the **verdict** rejects it:

| Model | as ruled | proposed |
|---|---|---|
| omission +0.10 on every class | 99.7 % | 99.9 % |
| omission +0.20 | 100 % | 100 % |
| 10 % extra misnaming | 58 % | 58 % |
| 20 % extra misnaming | 100 % | 99.9 % |
| icx14 (every branch named as its parent) | 100 % | 100 % |

Per class, the proposed lines are **stricter** for D1, PDA and PLB, where a human leaves room, and looser for OM2.
- A 10 %-misnaming model fails PDA 77 % and PLB 87 % of the time under P1, against 20 % and 15 % as ruled.
- It fails OM2 18 % under P1, against 80 % as ruled.

So P1 moves the gate's strictness to where the locked 100 can see it. Naming errors of 10 % stay hard to see at
n = 100 under either set. That is a property of the decision set, not of the lines.

**Also kept:**
- the "4 of 6" rule: under P1 a human fails it ≤ 0.25 % of the time, and a model 0.10 worse in omission 100 %;
- presence as a **per-class line**, not "A − 0.05": the binomial at the locked counts is what sets the noise.

**Not proposed:**
- dropping OM2 from the gated set. At 40 cases its line is low, but it still separates (omission +0.20: 68 %).
- a lower-bound form (CI against a human line). It needs the model's own spread, which does not exist before the look.

### 2.2 Item 2: the scorer of record

`experiments/Atlas/j1f_r2/j1f_scorer.py`, proposed for freezing by its sha256,
**`2da3cb1a2a95a32fd9706bb8019bdc292a71f2bddaed159b76623b747ec0886c`**. It is printed by
`python j1f_scorer.py selftest`, and posted on #303 with the PR. It imports the pinned `tf1.py`
(`24441cf8…5254`) and refuses any other.

| Definition | Frozen value | Why |
|---|---|---|
| Piece | 26-component of one branch class, ≥ 20 voxels | R-PDA in two pieces is two pieces, each with its own root (10.7 % of cases on the 620) |
| Centreline | skeleton of the **whole** reference tree, restricted to the piece; A1c's fallback if empty | a branch's skeleton is the tree's, not its own blob's |
| Root | the piece's centreline point nearest its parent (LAD for D; LCx for OM, Ramus; LCx or RCA for PDA/PLB) | "rooted at the branch's origin" |
| Presence | centreline length of the class ≥ **5 mm** | 3 mm and 5 mm differ by at most one case per class (D2, OM2, PDA, PLB: one each) on the 620 (§3). Delta's 5 mm is kept |
| Detection | ≥ 50 % of the piece's centreline within 1.5 mm (D3) of predicted vessel of **any** class | F-A6 |
| Naming | covered points take the label of their nearest predicted voxel; named right if **strictly more than half** carry the piece's class | F-A6 "mostly the right class", ties fail |
| Branch tF1 | `tree_f1` on (ref == c, pred == c), one ostium per piece at its root, components ≥ 20 voxels | per-piece rooting |
| Collapse | D1–D3 → LAD; OM1, OM2, Ramus → LCx; each PDA ∪ PLB component → the territory (LCx or RCA) with more voxels in its one-voxel ring; tie → nearer | F-A4 under **D47 Q1 (A)**. Only (A) is implemented: Q1 is answered |
| Labels | F-A3 with Q1 (A): L-PDA/L-PLA → PDA/PLB; first LAD-side "Other" → D3, later → LAD; LCx-side → LCx; touching only RCA or nothing → 255; small or tied pieces → nearest LAD/LCx | F-A3 |

**Checks:**
- **The synthetic self-test** covers:
  - identity → all 1;
  - D1/D2 swap → detected, misnamed;
  - D2 dropped → missed, presence disagrees;
  - D2 painted as LAD → detected, misnamed;
  - OM1 truncated to 30 % → missed;
  - D1 cut from its origin → detected but tF1 < 0.5;
  - a left PDA → LCx, a PLB off the RCA → RCA;
  - the label map on a toy ImageCAS-X.
- **On a real 620 case** (`validate_scorer.py`, c0217):
  - identity → 1.0 everywhere;
  - D1/D2 swapped → both detected, misnamed, tF1 0;
  - OM folded into LCx → detected, misnamed, presence lost;
  - PLB dropped → missed;
  - PDA truncated to 40 % → missed (tF1 0.58).
- **A one-voxel erosion of the whole tree** removes D1 and the PDA altogether (tF1 0.31 and 0.20), because those
  branches sit at the grid floor (≈ 1.2–1.4 mm across, 2.5 voxels at 0.5 mm). **A model that is a voxel thin loses
  whole branches.** That is the model's problem, not the scorer's. But it ties 1-F to track 1-L's width finding:
  Janus 0's lumen is thin, and 1-F inherits it. Report each gated class's Dice beside Table 1's (F-A9), so a B1
  failure can be read as width or as naming.
- **On the 620, the contact collapse of the stage-1 labels equals icx4's `territory.to_four`** (D25) in every voxel
  except 40 "Other" voxels in 2 case(s). The collapse needs no left-dominance case list.
- **Cost:** ≈ 110 s per case per reading on one core, so ≈ 6 core-h for F and T on the locked 100: minutes on Fir's
  12 cores.

### 2.3 Item 3: Arm N, dropped

My round-1 Arm N (a CPU namer on Janus 0's tree) is **dropped**, not built.
- **It decides nothing now.** F-A6's gate is a fixed line, not a comparison, and §2.1 calibrates it without any
  model's per-case spread. So the one thing only Arm N could supply, a spread for a comparative gate, is not needed.
- **It does not exist,** and building it is the largest code item I proposed in round 1: segment graph, features,
  classifier and ordinal step.
- **Hampe et al. 2024** (0.74 vs 0.91 on automatic trees) says it would be weak on Janus 0's tree, and it cannot
  deliver the six untraced classes.
- **Its question survives** as the rule-ordinal report (F-A9), which costs nothing, and as one of the three designs
  round N+1 chooses from if the stall check fires or < 4 of 6 pass.

### 2.4 Item 4: stage 2's loss details (measured on the 620)

**The Dice term: leaf-Dice. My merged-mass Dice is withdrawn.**
- Merged mass (v1 §4.3) has no table behind it.
- Leaf-Dice has one: Fidon et al. Table 2, as the round-1 ruling found.
- "Ignore for Dice" (Foxtrot) is leaf-Dice's denominator rule seen from the other side: set-valued voxels leave the
  Dice term. The two differ only in whether background singletons count, and in leaf-Dice they do.
- So the round converges on **marginal CE + leaf-Dice**.

**The band, measured.** `census_r2.py` measures, on the 620:
- background within 4, 8 and 15 mm of the traced tree;
- each traced side branch's distance from its own parent trunk. This is the only proxy ImageCAS-X allows for where an
  untraced side branch (septal, SN, conus, RMA) runs, since D/OM/Ramus/PDA/PLB are side branches of the same calibre.

| Band | background released per case, median [p10–p90] | × tree volume | share nearest LAD / LCx / RCA / LM | traced side-branch pieces wholly inside (max distance ≤ band) | pieces with their centreline median inside |
|---|---|---|---|---|---|
| 4 mm | 43 [36–53] cm³ | 22 | 33 / 26 / 21 / 3 % | 0.3 % | 4.4 % |
| 8 mm | 142 [118–170] cm³ | 72 | 33 / 25 / 22 / 3 % | 5.5 % | 26 % |
| 15 mm | 433 cm³ | 220 | 32 / 24 / 23 / 4 % | 23 % | 60 % |

What this shows:
- **No band holds a side branch whole.** Even at 15 mm, most pieces leave it. A band protects the **proximal**
  course, where an untraced branch's background label would most directly contradict a pool read. Distal voxels
  outside it stay background singletons in ImageCAS-X cases, whatever width is chosen.
- **Width buys proximal coverage at the price of unsupervised volume.** 15 mm releases 220 × the tree's volume per
  case: most of the heart's surroundings, where the new classes get no negative evidence from ImageCAS-X.
- **Territory restriction cuts that price by about three to four.** The released background splits roughly evenly
  between LAD, LCx and RCA (table). A class can only arise where its parent is:
  - S1–S3: within the band of the **LAD** only;
  - Conus and RMA: of the **RCA** only;
  - SN: of the **RCA, the LM and the proximal LCx**, since 20–22 % of SN arteries leave the circumflex (Koşar et al.;
    Vikse et al.).

**Proposed (P2):**
- an ImageCAS-X background voxel within **15 mm** of the traced tree gets the set {bg} ∪ {the stage-2 classes whose
  parent territory is nearest that voxel};
- elsewhere it is {bg};
- 15 rather than 8 mm because a side branch's median point is inside 15 mm for 60 % of pieces but inside 8 mm for
  only 26 %.

**Proposed (P3): the leakage gate, pre-registered for J1F-2** (Bridge v1's check, made a gate). On the locked 100, where
ImageCAS-X carries none of the six classes:
- **L1:** each new class's predicted voxels **outside** its P2 band are ≤ 5 % of that class's predicted voxels, pooled
  over cases. Above that, the class's logit is masked outside its band at export, and the class is reported as
  leaking.
- **L2:** no new class in more than 10 % of locked cases with > 1 cm³ predicted. Above that, the class ships folded
  into its parent.
- V is re-read on the stage-2 model against stage 1's shipped model, with the same margins (a second look, which
  needs its own α. Round 3 sets it: I suggest 1.25 %, as track 1-L's L-A18).
- **D35 precision** against extended reads is a report until a class reaches 20 patients (§2.6).

### 2.5 Item 5: reads per class: a rule, not Job B

**Keep F-A11's provisional thresholds.** Do not run Job B or a learning curve now. Three reasons:
1. **Job B measures the wrong thing.** It thins OM and PLB reads in a network that already segments their parent and
   has ImageCAS-X's 620 positives of the class's siblings. The stage-2 classes start from ImageCAS-X **background**
   (§2.4) with no traced sibling, so the answer does not transfer.
2. **It spends 33–45 GPU-h before any extended read exists,** to set a threshold that D47 Q5 already gives a trigger
   for: revisit if fewer than 30 patients have a septal read at the first pool wave.
3. **The threshold is checked by the outcome anyway.** A class is trained at ≥ 30 patients, and then shipped unfolded
   only if it passes on D35 (§2.6) and P3. A threshold set too low costs one stage-2 run, not a wrong model.

**One tightening:** "≥ 3 sources" counts **patients from ≥ 3 sources with ≥ 5 patients each**, so one large source
cannot carry a class.

### 2.6 Item 6: the scoring set for the six untraced classes (D47 Q6: D35 read in extended mode)

`untraced_yield.py`. D35 has **35 patients**, each read twice (D23). The table gives the expected count and the
probability of reaching each line, at a grid of prevalences π. Here π is "visible and drawn"; no prevalence is
sourced but SN's origin.

| π | patients with the class (reads correlated, P = π): E, P(≥ 20), P(≥ 30) | reads independent: E, P(≥ 20), P(≥ 30) | recall 0.8 ± (95 %) |
|---|---|---|---|
| 0.4 | 14.0, 0.03, 0.00 | 22.4, 0.85, 0.00 | ± 0.21 |
| 0.6 | 21.0, 0.70, 0.00 | 29.4, 1.00, 0.50 | ± 0.17 |
| 0.8 | 28.0, 1.00, 0.27 | 33.6, 1.00, 1.00 | ± 0.15 |
| 0.9 | 31.5, 1.00, 0.87 | 34.6, 1.00, 1.00 | ± 0.14 |

- **Report (≥ 20):** needs π ≥ 0.63 for 80 % assurance with correlated reads.
- **Decide or ship (≥ 30):** needs π ≥ 0.89.
- **So:**
  - **septals** (several per heart, S1 nearly always) can likely be **reported**, and S1 perhaps decided;
  - **SN, Conus and RMA** stay **counts only** on D35 (as D47 Q6 accepted). Any decision on them needs a larger
    held-out set, which is a D35 decision for the lead and is not asked here.
  - At 35 patients a recall of 0.8 is known to ± 0.14–0.21, so D35 can tell a working class from a broken one, not a
    good one from a human-level one.
- **Not proposed:** scoring the six on the A30 pool seal. Its single look is D6's (D27), and it is not 1-F's to spend.

### 2.7 Item 7: Shi et al.'s numbers, reconciled

I read arXiv:2007.03868 v1, its only version (8 Jul 2020), in its HTML rendering. **Both sets of numbers are in Table
3. They answer different comparisons:**

| Row (Table 3, mean Dice, "All") | Value | Who quoted it |
|---|---|---|
| ΨFmc, rCE+rDC: one network on the **fully labelled set only** | .874 | everyone |
| ΨF+P, rCE+rDC: networks on F **plus one partial set**, standard losses | .900 | Delta (".874 → .900") |
| ΨAllmc, **mCE+mDC**: one network on all five sets, marginal loss | **.921** | Atlas v1, Crucible |
| ΨAllmc, mCE+mDC+**eCE+eDC**: marginal + exclusion | .931 | Atlas v1 ("adding the exclusion loss gave 0.931"); Delta (".931 vs .900") |

The paper's own sentences carry both readings: "a 4.7% increase (.921 vs .874)" for the marginal loss, and "a 3.1%
increase (.931 vs .900)" for the full method against F + partial.
- **For 1-F's question** (does a marginal loss over partially labelled data beat training on the fully labelled part
  alone?) the row of record is **.921 vs .874**.
- **Delta's .900** is not a marginal-loss result.
- **Table 6** is unchanged: as fully labelled cases go from 24 to 4, mean Dice falls from .874 to .774.

### 2.8 Item 8: the `role:swe` spec for `trillium/janus1f`, as a diff against #306 + L-A21

**Shared, unchanged from L-A21:**
- editable segtrain install, or the exported sealed-list paths;
- the split file and its guard;
- Step T's plans copied and moved, Janus 0's fingerprint placed, no `plan_experiment`/`extract_fingerprint`;
- the plans check without `dataset_name`/`image_reader_writer`;
- `SEGTRAIN_CT_WINDOW=off`, `SEGTRAIN_SAVE_EVERY=10`, `SEGTRAIN_SAVE_PROBABILITIES=0`, `SEGTRAIN_MAX_SECONDS`;
- `nnUNet_compile` as Janus 0's;
- `checkpoint_best` never read;
- the looks ledger, and `collect` refusing a second run.

**Different in 1-F:**

| Item | `janus1l` (L-A21) | `janus1f` |
|---|---|---|
| Header | Trillium | **Fir**: `--account=def-aso22 --gpus-per-node=h100:1 --cpus-per-task=12 --mem=280G --time=23:50:00` |
| Dataset | 718, `territory.to_four` | **719**, `stage1_labels` from the frozen scorer module (13 values + 255), the same code `collect` uses for the locked-100 references |
| Val in `splits_final.json` | 10 lowest-id of the tuning 60 | **the 20 fit-check cases** (F-A5), inside the 620. **This amends F-A2's "fold-0 validation is the locked 100".** With val = the locked 100, the run's own end-of-training validation predicts and scores the locked 100 at **plain argmax**, which breaks F-A7 twice. Two identical entries: a1 = fold 0, a2 = fold 1 (D47 Q8) |
| Trainer | `nnUNetTrainer_janus1l` (final validation a no-op) | `nnUNetTrainer_janus1f`: the same, plus (i) parent-copy head load for every `seg_layers` output; (ii) the step-0 identity on a random training batch, refusing on error; (iii) the fit check at epochs 150 and 300 on the 20, hierarchical decode, `fitcheck.json`, `STALL` per F-A5 |
| Step-0 identity | — | territory sums equal Janus 0's within 1e-5, **and** the hierarchical territory equals Janus 0's argmax on every voxel. On random logits the 13-output head meets both (error 1.3e-15, agreement 1.000000; `head13_check.out`), while a plain 13-way argmax moves **4.8–42 %** of voxels across territories depending on logit scale. The self-test must show the plain decode failing |
| Predict | `--save_probabilities`, E by `nnUNetv2_ensemble` | **No saved probabilities.** A `nnUNetPredictor` subclass decodes the logits **in memory** and writes two uint8 maps per case: **F** (hierarchical) and **T** (Janus 0's Fir label map as territory, then 1-F's within-territory argmax). A 13-channel softmax per case at 0.5 mm would be very large on scratch for 100 cases, and nothing downstream needs it. `--disable_tta`, mirroring off |
| Collect | H1 → H2 → H3, `rule_t.json` | **V → B** (F-A6), with P1's lines; the frozen scorer's sha256 must equal the one posted on #303, or `collect` refuses; F-A9's reports; one look |
| Threshold | t_C (L-A15) | **none** (F-A6 compares at argmax; ruling §7) |
| Refusals | sealed/locked in training, plans, split | the same, plus: Q1 switch absent (now fixed to (A) by D47, so the switch is asserted, not read); a dataset id in use; an identity error; a scorer hash mismatch |
| Re-fetch | — | if `$SCRATCH` was purged: CTs and labels from Step T's `$KEEP`, else `trillium/fetch_cases.py`; Janus 0's model **only** from `$KEEP` (§3) |

**Self-tests, each failing on a broken fixture first:**
1. L-A21's 1–6, unchanged.
2. Labels: `stage1_labels` on the toy (L-PDA → PDA, D3, 255) and its collapse equals `territory.to_four` on a fixture
   with a left-dominant PDA.
3. Head: the identity passes on parent copy and **fails** on a random head and on plain argmax.
4. Fit check: a fixture network that predicts parents only writes `STALL`.
5. F and T: T's four-class collapse equals Janus 0's map byte for byte.
6. Gate: P1's lines fire on a fixture with OM2 recall 0.55; a model passing V with 3 of 6 classes gives "not adopted";
   V failing with ≥ 4 of 6 on T gives "T".

### 2.9 Item 9: the warm start if Janus 1-L is adopted first: Janus 0, unchanged

- **1-L's candidate is E** (two networks, softmax-averaged, exported at t_C: L-A14, L-A15). There is no single
  checkpoint to grow a head from. a1 alone is not what shipped, and a head grown from E is not defined.
- **V's comparator would move to Trillium.** F-A8 pairs on Fir's own Janus 0 predictions to avoid a cross-cluster
  difference. 1-L's predictions are Trillium's.
- **t_C has no meaning in 1-F,** which decodes at argmax (ruling §7).
- **So:** J1F-A starts from Janus 0 whatever 1-L's outcome. If 1-L is adopted, two reports are added beside V, neither
  deciding: F's four collapsed classes against 1-L's locked-100 predictions, and T's against them. The next 1-F
  round may start from 1-L when a single-network 1-L exists and its predictions are on Fir.

### 2.10 Item 10: one census of record (the 620)

**Proposed (P4):** `experiments/Atlas/j1f_r2/census_r2.jsonl` and `census_r2_summary.json` are the census of record.
Their definitions are in `census_r2.py`'s docstring: labels only, 620 by the pin.

| Quantity | Value on the 620 | Definition |
|---|---|---|
| Cases with D1 / D2 / D3 / OM1 / OM2 / Ramus / PDA / PLB (≥ 5 mm) | 611 / 358 / 47 / 540 / 228 / 149 / 607 / 609 | §2.2's presence |
| PDA in two pieces / PLB in two pieces | 65 (3 of them in three pieces) / 10 cases | §2.2's piece |
| "Other": D3 / D4 → LAD / LCx-side / nearest / ignore (255) | D3 47 cases; D4 → LAD 2 pieces; LCx-side 20; nearest 1; ignore 8 (in 8 cases) | F-A3 as implemented |
| Unnamed trunk twigs (skeleton spurs of the trunk class, beyond its two longest ends), cases with ≥ 1 of ≥ 3 / 5 / 10 mm | LAD 11 / 9 / 7; LCx 21 / 21 / 20; RCA 1 / 1 / 0 | spur = endpoint-to-junction walk on the trunk's own skeleton |
| Cases with a left-sided PDA or PLA (labels, ≥ 20 voxels) | 59 (46 left only, 13 with both sides) | the count that matters for D47 Q1 |
| Dominance (`Descriptors.xlsx`) R / Co / L | 564 / 21 / 35 | ImageCAS-X's own field |
| `Descriptors.xlsx` "R" with a left-sided posterior branch | 5 cases (and 2 co-dominant with none) | why dominance and "left-sided PDA/PLA" must not be used interchangeably |

- **The round-1 disagreement on trunk twigs** (Crucible 13, Delta 4, Foxtrot 6) came from different spur
  definitions. This one is stated and reproducible.
- **For D47 Q1, quote "cases with a left-sided PDA or PLA",** not dominance. Co-dominant and some right-dominant
  hearts carry one.

### 2.11 Item 11: Q8 and Q9's consequences

- **Q8 (a2 runs, report only).**
  - a2 is fold 1 of the same `splits_final.json`, submitted concurrently with a1, ≈ +29 GPU-h. The total committed
    becomes ≈ 60 GPU-h.
  - a2 is predicted on the locked 100 **after** `collect` has written a1's verdict, and its numbers are reports:
    between-run spread per gated class, |a1 − a2|/√2 as track 1-L's σ_g.
  - **a2 never replaces a1,** is never ensembled into what ships, and never moves a line.
  - If a2's verdict differs from a1's, that is reported (A26's rule), not acted on.
- **Q9.** The model read in F-A6 (F or T) is **Janus 1-F.1**, and the adopted one is **Janus 1-F**. a2, the rule
  reading and every report take no number. `collect`'s `DECISION.md` writes the name and which reading it is.

## 3. Step T and F0 have not run: what each would change

| Result | Then |
|---|---|
| **F0** prints both pins and Foxtrot's label counts | Nothing changes. My census uses a different implementation of F-A3 (the frozen scorer's), so F0 and `census_r2` are two independent counts of the same rule. They already agree with F0's **expected** printout: my D3 47 + D4→LAD 2 + 1 small LAD-touching piece sent to the nearest = Foxtrot's `other_diag` 50; my LCx-side 20 = `other_marg` 20; my ignore 8 = `other_amb` 8; D3 47 and D4→LAD 2 equal. So if F0 prints its expected line on Fir, Fir's copy matches this container's 620 too |
| F0's pins differ | Stop (ruling §8). Fir's copy is not the 620 |
| F0's counts differ from Foxtrot's but match mine | The launcher uses the frozen scorer's `stage1_labels` (§2.8), so mine are the ones of record. Report the difference |
| **Step T** copies plans, fingerprint, checkpoint, the 160 labels and aortas, and Fir's locked-100 predictions | J1F-A can be built as §2.8 says |
| Step T shows Janus 0 trained **with** class-weighted CE (L-A20's check) | 1-F's "unweighted DiceCE" (F-A2) is then a recipe change from Janus 0. Round 3 chooses between adding the weights for the vessel classes and accepting the change. V would measure it either way |
| Step T is late and the purge (≈ 2026-12-20) passes | Janus 0's checkpoint and Fir predictions are gone. Without them there is no warm start, no T and no V baseline. The track waits for a re-fetch from Trillium or wherever Janus 0 survives (ruling §8). Nothing in this plan has a substitute |
| Step T's locked-100 predictions are fewer than 100 | T and V cannot be scored on the missing cases. Stop and report. Never re-predict Janus 0 on Fir silently: that changes the baseline |

## 4. Proposed amendments, for round 3

| # | What | Replaces |
|---|---|---|
| **P1** | B's per-class lines (§2.1 table); "4 of 6" kept | F-A6's 0.80 / 0.85 / A − 0.05 |
| **P2** | Stage-2 background band: 15 mm, territory-restricted per class | F-A11's open band |
| **P3** | Stage-2 leakage gate L1/L2 | F-A11 "Bridge's leakage check, kept for stage 2" |
| **P4** | `census_r2` as the census of record | ruling §5 item 10 |
| **P5** | The scorer of record: `j1f_scorer.py` at this PR's head, hash posted on #303 | ruling §5 item 2 |
| **P6** | Val = the 20 fit-check cases; no locked-100 validation in training; predict decodes in memory, no saved probabilities | F-A2's "fold-0 validation is the locked 100" |
| **P7** | Arm N dropped; leaf-Dice adopted; Job B not run; warm start pinned to Janus 0 whatever 1-L does | ruling §5 items 3, 4, 5, 9 |

## 5. Cost

| Job | GPU-h | Change from round 1 |
|---|---|---|
| Step T, F0 | 0 | — |
| J1F-A a1 | ≈ 29–31 (ceiling 47.7) | none |
| a2 (D47 Q8) | ≈ 29 | now committed |
| Scoring (F, T, a2 reports) | 0 (≈ 6 core-h each) | — |
| J1F-2 | ≈ 15, when F-A11's counts are met | — |
| Arm N, Job B | 0 | dropped |

## 6. What would change this plan

| Observation | Then |
|---|---|
| Table 1 turns out not to describe independent reads | The human-level model would be too kind, and P1's lines too loose. The paper says each test case was "re-annotated by a different analyst, selected at random, following the same protocol without review from the lead analyst and blinded to the first set of labels" (§Data Subsets), so this is not expected |
| ImageCAS-X's test 160 differ in difficulty from the locked 100 (Janus 0's val 80 + 20 open) | All 800 were split at random (§Data Subsets), so they should not differ. The locked 100's own label counts already enter the simulation |
| The locked 100's real piece counts differ from the 620's distribution | Re-run `gate_sim.py` with those counts (labels only, F-A7) before freezing P1 |
| F0's "Other" counts differ from `census_r2`'s | §3's rows |
| The first extended pool reads show septals running mostly beyond 15 mm of the tree | P2's band widens for S1–S3 only, or the stage-2 classes get no band and rely on pool reads alone |
| L1 fires for every new class | Shi's exclusion term (Table 3: .921 → .931) is added to stage 2, which v1 declined |

## 7. Evidence

| Claim | Evidence |
|---|---|
| B's lines fail a human-level model on OM2 58 % (46–81 %) | `experiments/Atlas/j1f_r2/gate_sim.py`, `gate_sim.json` |
| Table 1's numbers and definitions | Bransby et al., arXiv:2608.30404v1, Table 1 and its caption; Supplementary B ("Septal perforators, acute marginals and nodal arteries were not traced") |
| The scorer's definitions and checks | `j1f_scorer.py` (self-test), `validate_scorer.py`, `validate_scorer.json` |
| Contact collapse equals D25 on the 620 | `census_r2.jsonl` (`collapse_mismatch_*`), `census_r2_summary.json` |
| Band volumes and side-branch distances | `census_r2.py`, `census_r2_summary.json` |
| D35 yields | `untraced_yield.py`, `untraced_yield.out` |
| 13-output head identity | `head13_check.py`, `head13_check.out` |
| Shi et al.'s rows | arXiv:2007.03868v1, Table 3 (and Tables 5–7), HTML rendering |
| SN from the circumflex in 20–22 % | Koşar et al. (as round 1); Vikse et al., PLoS One 2016, Table 3 (as Crucible v1) |
| Track 1-L's validation leak and spec | [[Janus 1-L Round 2]], L-A20, L-A21 |
| Write-up | [[Atlas - Janus 1-F round 2, the ruled branch gates fail a human reader on OM2, and per-class lines fix it]] |
