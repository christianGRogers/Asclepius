---
tags: [plans/candidate, bridge, janus-1f, branches, partial-labels, fir, D44, D45, D47, round2]
author: Bridge
track: Janus 1-F
round: 2
updated: 2026-11-16
issue: christianGRogers/Asclepius#303
---

# Bridge v2 (Janus 1-F): anchor every branch gate to a second ImageCAS-X analyst, collapse with SegQueue's own code, drop Arm N, and make the reads-per-class experiment cheaper and absolute

## 0. Position in one paragraph

Bridge accepts the plan in force ([[Master plan - Janus 1-F]], Delta v1 as amended by F-A1 to F-A13, and D47). This
round answers the eleven items of [[Janus 1-F Round 1]] §5 with CPU work in `experiments/Bridge/j1f_r2/`. The four
answers that change the plan:

1. **B's gate lines fail a human reader too often** (item 1). Simulated from ImageCAS-X Table 1, a second analyst
   fails the **OM1** gate **50 %** of the time and **OM2** 42–95 %; the "4 of 6" rule fails it 4–21 %. The cause is
   B2's 0.85 naming line: Table 1's DSC spread implies a human names OM1 right only about 0.85 of the time. Bridge
   proposes **per-class lines at a human's expectation minus 1.96 binomial SEs**. Under them a human fails "4 of 6"
   0.15–3 % of the time, and a model with twice a human's errors still fails 96 %.
2. **The four-class collapse for predictions is SegQueue 0.20.0's own function**, imported, not re-written (item 2).
   On the 620, `assign_contact_branches` gives ImageCAS-X's own side for **all 1,296** posterior-branch
   components (1,296 of 1,296, no fallback used). Scoring by contact and scoring by side therefore give the same
   answer on the reference.
3. **Arm N is dropped** (item 3). The T reading is already segment-then-label on Janus 0's tree, and the gate no
   longer needs a branch-tF1 spread.
4. **Reads per class: Job B, smaller and absolute** (item 5). Two runs, not three (≈ 22 GPU-h, not 33). k\* is read
   against item 1's human-level lines on a 60-case hold-out of the 620, not against a full-label run. It runs after
   J1F-A's verdict and before any extended read trains. Until it has run, F-A11's 30-patient rule stands.

The other items are measured or specified below:
- Stage 2's band (item 4): an 8 mm band releases about 71× the traced tree's volume of background per case, and
  15 mm about 218×.
- The scoring set for the six untraced classes (item 6).
- Shi et al.'s numbers, reconciled row by row (item 7). One of Bridge v1's own claims is retracted.
- The frozen `role:swe` spec as a diff against #306 (item 8).
- The warm start stays Janus 0 (item 9).
- One census of record (item 10).
- D47's consequences (item 11).

## 1. What this round read, and independence

- **Read:**
  - [[Janus 1-F Round 1]] (all of it, §5 above all);
  - [[Master plan - Janus 1-F]];
  - D45, D46 and **D47** in [[Human decisions]];
  - Bridge v1, and the four other round-1 candidates (Atlas, Crucible, Delta v1, Foxtrot), for their positions on
    the §5 items;
  - #306 (the `janus1l` launcher spec);
  - PR #326 (SegQueue 0.20.0, D47), and `src/segqueue14/labels.py` on `dev`;
  - [[Master plan - Janus 1-L]]'s header.
- **Not read:**
  - no round-2 candidate of this track (no `v2` file other than this one, and no other `exp/j1f-r2-*` branch);
  - `experiments/Delta/j1f_r2/` and Delta's round-2 experiment note are on `dev`. Bridge saw their file names in a
    directory listing and opened neither.
- **Data:**
  - ImageCAS-X segmentations of the **620 training cases only** (`fetch_seg620.py`; Zenodo 10.5281/zenodo.21887809,
    CC BY 4.0);
  - `Descriptors.xlsx`, of which only the 620 training rows were used.
- **Not opened:** no locked-100 label, no sealed case, no model output, no pool read. The locked-100 counts used in
  §2 are Delta v1's label counts, as the ruling adopted them (F-A7).

## 2. Item 1: the gate numbers, and their false-fail rate for a human-level model

### 2.1 How a human reader is modelled (`gate_sim.py`, 200 000 draws, seed 20261115)

A "human-level model" is a second ImageCAS-X analyst. It agrees with the reference as ImageCAS-X's blinded second
analyst agreed with the first (Table 1, 160 test cases). For each gated class c, with n_c locked cases holding the
class (D1 98, D2 64, OM1 84, OM2 40, PDA 96, PLB 96):

| Component | Model | Source |
|---|---|---|
| **Presence agreement** | Binomial(100, A_c) / 100 | Table 1's agreement A_c |
| **Detection (a reference branch missed)** | rate a_c; **symmetric:** discordant cases split evenly between a miss and an extra call (a = (1 − A)/2π, capped by the negatives available); **misses-only, pessimistic:** every discordant case is a miss (a = (1 − A)/π) | Table 1's agreement, with π the locked prevalence |
| **Naming (a detected branch misnamed)** | rate q_c, the weight at DSC ≈ 0 of a two-part mixture (point mass at 0, plus N(μ, 0.08²) with μ free) fitted to Table 1's DSC mean and SD on co-present cases | Table 1's DSC. A co-present DSC near 0 means that the two analysts called different branches by that name |

**The naming estimate is the new step.** Table 1's DSC has a mean of 0.74–0.84 with SDs of 0.19–0.32. That spread is
only possible with a mass near 0, since no unimodal distribution on [0, 1] with mean 0.80 has SD 0.29.

| Class | A (Table 1) | DSC mean ± SD | **q, human misnaming** (SD of good part 0.05 / 0.08 / 0.12) | Human naming 1 − q | Miss rate a, symmetric / misses-only |
|---|---|---|---|---|---|
| D1 | 0.969 | 0.799 ± 0.287 | 0.112 / **0.107** / 0.098 | 0.893 | 0.016 / 0.032 |
| D2 | 0.894 | 0.829 ± 0.243 | 0.076 / **0.072** / 0.062 | 0.928 | 0.083 / 0.166 |
| OM1 | 0.944 | 0.741 ± 0.323 | 0.157 / **0.153** / 0.144 | **0.847** | 0.033 / 0.067 |
| OM2 | 0.875 | 0.777 ± 0.291 | 0.120 / **0.116** / 0.106 | 0.884 | 0.156 / **0.313** |
| PDA | 0.988 | 0.826 ± 0.219 | 0.063 / **0.058** / 0.048 | 0.942 | 0.006 / 0.013 |
| PLB | 0.962 | 0.836 ± 0.186 | 0.044 / **0.039** / 0.029 | 0.961 | 0.020 / 0.040 |

The fit is insensitive to the assumed SD of the good part: q moves by at most 0.015.

### 2.2 The ruled lines (F-A6) fail a human reader

Each value is the probability that a second analyst fails the gate on the locked 100.

| Class | Recall ≥ 0.80 | Presence ≥ A − 0.05 | Naming ≥ 0.85 | **Class fails**, symmetric | **Class fails**, misses-only |
|---|---|---|---|---|---|
| D1 | 0.000 | 0.004 | 0.091 | 0.094 | 0.094 |
| D2 | 0.002 | 0.062 | 0.017 | 0.080 | 0.315 |
| OM1 | 0.000 | 0.025 | **0.492** | **0.504** | **0.517** |
| OM2 | 0.162 | 0.070 | 0.256 | **0.420** | **0.947** |
| PDA | 0.000 | 0.000 | 0.000 | 0.001 | 0.001 |
| PLB | 0.000 | 0.014 | 0.000 | 0.014 | 0.014 |
| **"< 4 of 6 pass"** (not adopted) | | | | **0.043** | **0.207** |
| "< 6 of 6" (some class folds) | | | | 0.765 | 0.984 |

- **OM1's naming line sits above a human's expectation** (0.85 against 0.847), so a human fails it half the time.
- **OM2 fails on all three components.** It has only 40 locked cases, and its Table 1 agreement (0.875) is the
  lowest of the six.
- **Under the pessimistic reading, "4 of 6" fails a human-level model 21 % of the time.** That is above the
  ruling's 20 % line for loosening (§8).
- **Even under the symmetric reading, a human-level F ships with 1–2 classes folded 77 % of the time.** Those
  classes would be folded for noise, not for a defect.

### 2.3 Proposed lines (frozen by `gate_sim.py`'s `proposed_lines()`)

**The rule:** each line is the human-level expectation minus **1.96 binomial SEs** at the locked count. That is a
one-sided 2.5 % per component, the track's bound (L-A5). Each line is rounded down to 0.01. Recall and presence
lines are never raised above the ruled ones.

| Class | B1 recall ≥ | B1 presence ≥ | B2 naming ≥ | Change from F-A6 |
|---|---|---|---|---|
| D1 | 0.80 | 0.919 | **0.83** | naming −0.02 |
| D2 | 0.80 | **0.83** | **0.86** | presence −0.014, naming +0.01 |
| OM1 | 0.80 | **0.89** | **0.76** | presence −0.004, naming −0.09 |
| OM2 | **0.73** | **0.81** | **0.77** | recall −0.07, presence −0.015, naming −0.08 |
| PDA | 0.80 | 0.938 | **0.89** | naming +0.04 |
| PLB | 0.80 | 0.912 | **0.92** | naming +0.07 |

| Model on the locked 100 | P(< 4 of 6 pass), ruled | **P(< 4 of 6 pass), proposed** | Mean classes passing, proposed |
|---|---|---|---|
| Human-level, symmetric | 0.043 | **0.0015** | 5.73 |
| Human-level, misses-only | 0.207 | **0.031** | 4.81 |
| Twice a human's miss and misname rates | 0.977 | **0.956** | 1.73 |
| Three times | 1.000 | **1.000** | 0.21 |
| Naming collapsed (icx14's failure) | 1.000 | **1.000** | 0 |

**What this buys:**
- A human-level model is no longer folded for noise. The per-class false-fail is 2–8.5 % (symmetric).
- A model twice as error-prone as a human still fails "4 of 6" 96 % of the time.
- PDA's and PLB's naming lines **rise**, because humans name them better than 0.85. Raising a line is allowed
  before submission (F-A6), and it keeps the gate from passing a model clearly worse than a human on the two easiest
  classes.

**What stays:**
- **"4 of 6"** stays as the read rule. Under the proposed lines, P(< 5 of 6) for a human is 2.6 % (symmetric) to
  30 % (misses-only, almost all of it OM2's recall). "5 of 6" would therefore fail a human almost a third of the time
  under the pessimistic reading. "4 of 6" fails one 3 % of the time.
- **V** is not reopened.

**Its limits:**
- **The misses-only reading of OM2 is the one case the model cannot settle.** Table 1 does not say whether OM2
  discordance is a missed branch or a renamed one. If it is all misses, a human recalls 0.69 of OM2s and fails even
  0.73 most of the time.
  - "4 of 6" absorbs this: OM2 alone cannot sink the verdict.
  - The fold rule handles OM2 if it fails: it ships folded into the LCx, and that is reported.
- **Classes are drawn independently.** Errors of one model are positively correlated across classes. That widens the
  spread of "classes passing" but leaves the per-class rates unchanged.
- **Branches are counted as cases.** PDA's second pieces (10 %) would add trials, which makes the gate more stable,
  not less.

**Proposed amendment, B-v2-1:** replace F-A6's B1/B2 numbers by the table above. Freeze them, with
`gate_sim.py`'s sha256, in `configs/janus1/j1f_gates.json`, which the launcher reads (§9). Everything else in F-A6
is unchanged.

## 3. Item 2: the scorer's definitions, frozen by hash

`trillium/janus1f/lib/branch_score.py`, CPU, beside `tf1_score.py`. A1c (`24441cf8…5254`) is unchanged. Every
definition runs on the reference and the prediction alike, at the case's native spacing.

| Term | Definition |
|---|---|
| **Piece** | A 26-connected component of one class with ≥ 20 voxels |
| **Centreline** | `skimage.morphology.skeletonize` of the piece. Length = skeleton voxels × mean spacing (Bridge v1's `census.py`) |
| **Present** | A class is present in a case if the summed centreline length of its pieces is **≥ 5 mm**. On the 620, 3 mm instead of 5 mm changes presence in ≤ 5 cases for each gated class (D1 1, D2 2, OM1 2, OM2 1, R-PDA 2, R-PLA 5), and in 6 of 54 for L-PLA. The 5 mm line is kept: it also stops a 3–5 mm skeleton spur on a prediction from counting as a branch |
| **Presence agreement** | The share of the 100 cases where reference and prediction both have the class, or both lack it |
| **Detected** | A reference piece is detected if ≥ 50 % of its centreline points lie within 1.5 mm (D3) of predicted foreground of **any** class |
| **Named** | A detected reference piece is named right if, among its centreline points within 1.5 mm of predicted foreground, the **majority** have their nearest predicted foreground voxel labelled with the reference's class. A tie counts as wrong |
| **Branch tF1** (report) | A1c's tF1 on one class, **one root per piece**: the piece's skeleton point nearest a voxel of its parent. The parent is the reference's own for the reference, and the predicted one for the prediction. R-PDA is in two pieces in 63 of 620 training cases (Bridge v1), so the per-piece root matters |
| **Collapse, prediction** | D1–D3 → LAD; OM1, OM2, Ramus → LCx. PDA and PLB go to RCA or LCx by `segqueue14.labels.assign_contact_branches`, imported from `src/segqueue14/labels.py`, with parents RCA = {RCA} and LCx = {LCx, OM1, OM2, Ramus}. It is the same call SegQueue 0.20.0 makes (`collapse_to_four`). Its fallbacks (unattached or tie → RCA) are counted and reported |
| **Collapse, reference** | ImageCAS-X's own side: R-PDA/R-PLA → RCA, L-PDA/L-PLA → LCx. This is `territory.py`, which Janus 0 trained on |
| **Untraced classes on ImageCAS-X** | None exist in stage 1. In stage 2 they are excluded from every ImageCAS-X metric (Delta v1 §6.3) |

**D47 settles Q1 as (A).** The (B) and (C) branches of F-A3 and F-A4 are therefore removed from the spec:
- no `JANUS1F_LEFT_PDA` switch;
- the label map is pinned by hash instead.

**The contact rule on ImageCAS-X's own labels** (`census_r2.py`, 620 cases):
| Class | ImageCAS-X side | Contact rule says | Components |
|---|---|---|---|
| PDA | R | RCA | 638 |
| PDA | L | LCx | 38 |
| PLB | R | RCA | 565 |
| PLB | L | LCx | 55 |
| **All** | | **agree: 1,296 of 1,296** | cases with any disagreement: **0**; fallbacks (unattached or tie): **0** |

- 59 of the 620 cases have a left-sided component. Two cases have no PDA or PLB at all.

**What this means:** on the reference, the side label and the contact rule agree **on every component in every case**. The rule's fallback was never needed, because every
ImageCAS-X posterior piece touches its own parent and only that parent. So scoring the
prediction by contact against the reference by side compares like with like, to within the disagreements listed.
SegQueue and the 1-F scorer then give one answer for the same voxels, because they run one function.

**Hashes frozen at the swe PR's merge** (the launcher prints and checks them):
- `branch_score.py`;
- `src/segqueue14/labels.py`;
- `configs/janus1/j1f_gates.json`;
- `tf1.py` (A1c).

**Proposed amendment, B-v2-2:** the definitions above become F-A6's scoring, for D47's answer (A) only.

## 4. Item 3: Arm N, dropped

**Bridge recommends not building Arm N.** Four reasons:

1. **Its comparator role is taken.** T is Janus 0's tree named by a 1-F network, so segment-then-label is already
   read on the locked 100 at no GPU cost. Arm N would add a third naming of the same tree, by a weaker namer:
   - its classifier would be trained on reference trees and applied to predicted ones;
   - published naming drops from 0.91 to 0.74 on automatic trees (Hampe et al. 2024; [[Janus 1-F Round 1]] §3.2).
2. **Its gate role is no longer needed.** Item 1's gates are binomial in detection and naming, so their power
   follows from the counts (§2). Branch tF1 is a report.
3. **Measuring its spread would cost a look.** The per-case branch-tF1 spread Arm N was to supply could only come
   from scoring a model on the locked 100 before J1F-A ends. That is a model score that steers a gate, which F-A7
   forbids. On the 620 it would be optimistic, because Janus 0 trained on them.
4. **It would cost a `role:swe` item** (a segment classifier) on the critical path, for a report.

**When it comes back:** if B's verdict is "< 4 of 6" on both F and T, round N+1 chooses among class weights, F3 and
a graph namer (F-A6). Arm N is that graph namer, and it can be built then.

The **rule-ordinal reading** (F-A9) needs no Arm N. It is Bridge v1's namer step 4 (origin order along the parent),
applied to F's own predicted types.

## 5. Item 4: stage 2's loss, measured on the 620

### 5.1 The Dice term: leaf-Dice

- **Leaf-Dice and "ignore for Dice" are the same rule.** For class c, the Dice sums run over voxels whose label set
  is {c}, or a set that excludes c. A voxel whose set holds c and other classes is left out of c's Dice. Delta v1
  §11.4 and Foxtrot's "ignore set voxels for Dice" both state this. The round has two choices, not three.
- **Merged-mass Dice** sums the set's channels and scores the sum as one class. Fidon et al. Table 2 (marginal Dice,
  which is merged mass) put it at 11.1 vs leaf-Dice's 62.0 on the corpus callosum, their scarcest structure. Our six
  classes are scarcer still.
- **Shi et al. used merged mass and it worked** (Table 3: mCE + mDC 0.921), but **their merged label was the
  background** of large organs. Under merged-mass Dice the background's Dice is barely moved by an organ, while a
  septal's Dice is all septal.
- **Bridge agrees with F-A11: leaf-Dice.** Atlas's merged mass is not adopted.

### 5.2 The band: what each width releases (`census_r2.py`, 620 cases)

The band is the region of ImageCAS-X background that stage 2 labels as a set ({bg, untraced classes}) rather than
{bg}. Measured per case, as medians over the 620:

| Band width d | Background released, mm³ (p10–p90) | × traced tree | Host-restricted, mm³ | Host share | Share by nearest side: LAD / LCx / RCA / LM |
|---|---|---|---|---|---|
| 4 mm | 42,400 (34,700–51,600) | 21× | 32,200 | 0.78 | 0.33 / 0.26 / 0.38 / 0.03 |
| 8 mm | 138,700 (115,200–166,200) | 71× | 107,400 | 0.79 | 0.33 / 0.26 / 0.39 / 0.03 |
| 15 mm | 427,500 (360,800–502,800) | 218× | 338,200 | 0.80 | 0.32 / 0.25 / 0.40 / 0.04 |

The traced tree's median volume is 1,951 mm³. All values are medians over the 620; the source is `census_r2_summary.json`.

**Reading it:**
- **The band is two orders of magnitude larger than what it is meant to catch.**
  - The traced tree has a median volume of 1,951 mm³. A traced side branch has a median of 70–115 mm³ (Bridge v1
    census).
  - So at 8 mm, about 138,700 mm³ of background per case loses its full background pressure for each untraced class,
    to make room for perhaps 50–150 mm³ of untraced vessel.
  - Under a marginal CE, the network pays nothing for putting an untraced class's probability anywhere in that
    volume, as long as bg + that class is high.
- **Restricting the band to the host vessels** (the LAD side for S1–S3, the RCA side and the first 30 mm of the LCx
  for SN, Conus and RMA) releases 79 % of it at 8 mm. It does not change the order of magnitude.
- **The LAD-side and RCA-side zones barely overlap** (at 8 mm they overlap in 4 of the 620 cases, at most 0.3 % of the host band; at 15 mm in 122 cases, at
  most 2.3 %). That makes a better restriction possible.

**Bridge's proposal for stage 2 (B-v2-3):**
1. **Territory-specific sets, not one set:**
   - background within d of the LAD side → {bg, S1, S2, S3};
   - within d of the RCA side → {bg, SN, Conus, RMA};
   - within d of the first 30 mm of the LCx → {bg, SN};
   - elsewhere → {bg}.

   A septal is then never cheap near the RCA, and an RMA never near the LAD. Softmax keeps that exclusion without
   Shi's exclusion term.
2. **d is set from the first extended reads, not chosen now.** Before J1F-2 is submitted, a CPU script measures the
   distance from the traced trunk of every voxel drawn as S1–S3, SN, Conus or RMA in exported extended reads. d is
   the **95th percentile per group** (septal; RCA group), rounded up to 1 mm.
   - That needs reads, which exist before J1F-2 by definition (F-A11's counts).
   - **Until then, d = 8 mm** (Foxtrot) is the provisional value, not Crucible's 15. At 15 mm the band releases about
     three times the background of 8 mm (427,500 vs 138,700 mm³) for distal septal segments that a 4-class pool read
     already supervises as part of the LAD set.
3. **The leakage gate, pre-registered for stage 2** (Bridge v1 §9, now a gate). On the locked 100, reading the
   stage-2 model (one look, as F-A7):
   - **L1:** median share of ImageCAS-X **traced** voxels predicted as an untraced class ≤ **0.5 %**, and no case
     above 5 %. Those voxels are a traced branch or trunk, so any untraced call on them is wrong.
   - **L2:** median predicted volume of each untraced class **outside** the band ≤ 10 % of its volume inside. A
     class that lives outside its band is leaking into veins or myocardium.
   - **L3:** stage-1's V and B, re-run on the stage-2 model against the shipped stage-1 model (the forgetting
     guard).
   - **Failing L1 or L2:** that class is not shipped. Shi's exclusion term (0.921 → 0.931 in their Table 3) is the
     next round's remedy.

## 6. Item 5: reads per class, Job B, smaller and absolute

Bridge keeps the experiment, because no rule in the round is anchored. F-A11's 30 patients is the five candidates'
common ground, not a measurement. Three changes from v1:

1. **Two arms, not three.** The full-label reference arm is dropped. **k\* is read against item 1's human-level
   lines** on the hold-out, not against a full-label run. That saves ≈ 11 GPU-h, and the reference becomes the
   standard a shipped class must meet anyway.
2. **The two regimes stage 2 will face are simulated separately:**
   - **OM (OM1 + OM2) thinned into its parent:** in the 500 − k hidden cases, OM voxels become the set {LCx, OM1,
     OM2}. This is a 4-class pool read.
   - **PLB thinned into the background:** in the hidden cases, PLB voxels become the set {bg, PLB}, within the PLB's
     own 8 mm band. This is ImageCAS-X's untraced background, exactly.

   Both are thinned in the same run, in different territories.
3. **Timing.** It runs after J1F-A's verdict and before any extended read trains. It needs stage 2's label-set
   trainer, which F-A11 builds before J1F-2, so it adds no new code on stage 1's path.

| Item | Setting |
|---|---|
| Hold-out | The 60 training cases with the smallest sha256(`asclepius-j1f-r2-budget:` + id). Never the locked 100. They are excluded from both arms' training |
| Training | The other 560. OM and PLB exact in k ∈ {**20, 60**} cases (the k smallest sha256(`asclepius-j1f-r2-k:` + id) among those holding the class) and set-labelled elsewhere |
| Recipe | J1F-A's, at **200 epochs**, warm from Janus 0 by parent copy, marginal CE + leaf-Dice |
| Read | Each arm's OM1, OM2 and PLB on the 60, with item 1's metrics and lines scaled to the hold-out counts by the same rule (`gate_sim.py`) |
| k\* | **20** if k = 20 passes for OM1 and PLB; **60** if only k = 60 does; **"more than 60"** otherwise |
| Cost | 2 × ≈ 11 GPU-h = **≈ 22 GPU-h** (200 × 192–210 s), one 23:50 link each, concurrent |

**What it cannot show:**
- ImageCAS-X is one source with clean labels. k\* from it is a **lower bound** for pool reads from ≥ 3 sources with
  reader noise.
- So F-A11's "≥ 3 sources" and its inter-read floor stay as they are. Job B moves only the patient count, and only
  upward from 20.

**If the lead does not run it,** F-A11's 30 stands, and the reason is recorded: it is the five candidates' common
ground and was not measured.

**Proposed amendment, B-v2-4:** Job B as above becomes J1F-B, after J1F-A, at ≈ 22 GPU-h. It is the lead's call
for Fir's allocation, since it competes with a2 (Q8).

## 7. Item 6: the scoring set for the six untraced classes (D47 Q6: D35 in extended mode)

D35 has 35 patients. Let p be the share of them in whom a reader draws the class (`untraced_yield.py`, exact
binomial):

| p | Expected cases | P(≥ 20): report | P(≥ 30): decide or ship unfolded | Wilson 95 % half-width of a 0.85 rate at the expected n |
|---|---|---|---|---|
| 0.3 | 10.5 | 0.001 | 0 | ±0.21 |
| 0.5 | 17.5 | 0.25 | 0 | ±0.16 |
| 0.7 | 24.5 | 0.96 | 0.03 | ±0.14 |
| 0.8 | 28 | 1.00 | 0.27 | ±0.13 |
| 0.9 | 31.5 | 1.00 | 0.87 | ±0.12 |
| 0.95 | 33.2 | 1.00 | 0.99 | ±0.12 |

- **This round found no CT figure for how often a reader can see each class**, so p is a range, not an estimate.
- **The anatomy bounds it from above:**
  - S1 exists in essentially every heart, and S2–S3 in most;
  - the SN artery exists in every heart, but is thin;
  - a conus artery exists in nearly every heart, a separate ostium in 22 % (Koşar et al.);
  - acute marginals exist in most right-dominant hearts.
- **Only a class that readers draw in ≥ 86 % of patients reaches 30 on D35 more often than not.** S1 might; SN,
  Conus and RMA probably cannot; S2–S3 are uncertain.

**Bridge's recommendation:**
- On D35, **report** each untraced class with n and CI once ≥ 20 patients have it (F-A11). It decides nothing below
  30.
- Ship a class unfolded only at ≥ 30 decision patients.
- A larger held-out pool set is a D35 decision. It is not asked now: the first extended-mode D35 wave gives the real
  p per class at no cost. If p < 0.86 for a class the lead wants shipped, that wave is the time to ask.

## 8. Item 7: Shi et al.'s numbers, reconciled

The PDF was re-read: arXiv:2007.03868v1, Table 3 and the text of §4.3. **Both sets of numbers are in the paper. They
answer different questions.**

| Number | Table 3 row and column ("All" = mean Dice) | What it compares | Who quoted it |
|---|---|---|---|
| **0.921 vs 0.874** | Ψᵐᶜ_All, **mCE + mDC** (marginal loss, five datasets pooled) vs Ψᵐᶜ_F, rCE + rDC (one network, the fully labelled set only) | **The marginal loss with pooling, against the fully labelled set alone.** This is the number for "label sets let you use partial data" | Atlas, Crucible: **correct** |
| **.874 → .900** | Ψᵐᶜ_F rCE + rDC (0.874) vs Ψᵇ_F+Pi rCE + rDC (0.900): **separate binary networks**, one per organ, each on F plus its partial set | Pooling **without** a marginal loss. Not the marginal loss's effect | Delta v1. The numbers are right but attributed to the wrong comparison |
| **.931 vs .900** | Ψᵐᶜ_All mCE + mDC + eCE + eDC (0.931) vs the binary networks (0.900) | Marginal + exclusion in one network, against per-organ binary networks | Delta v1. The numbers are right, but the comparator is the binary-network row |
| **0.921 → 0.931** | mCE + mDC vs mCE + mDC + eCE + eDC, both Ψᵐᶜ_All | **The exclusion term's own effect: +0.010** ("an average of 1.0 %", §4.3) | Nobody. This is the number for "is Shi's exclusion term worth it", which B-v2-3 cites |
| **0.873 / 0.876** | Ψᵐᶜ_All with mCE alone / mDC alone | **Marginal CE alone, or marginal Dice alone, does not beat F alone (0.874).** Only the pair does | Nobody. It is a warning for stage 2: its CE term is marginal, and its Dice term (leaf-Dice) is not Shi's |

- **Bridge v1 §3.2 claimed** that Shi's "abstract" says the exclusion loss alone added little on kidney and
  pancreas. **The abstract says no such thing. That claim is withdrawn.**
  - The nearest supported statement is Table 5's 0:1 row (exclusion loss only, 0.897, against marginal only, 0.921).
  - Bridge v1 quoted no number from Shi, so nothing else changes.
- **Table 6** (fewer fully labelled cases, more partial: 0.874 → 0.774 as full : partial goes from 24 : 0 to
  4 : 20) is the only evidence in the paper about **how little** full labelling suffices. It is on organs, not
  branches. That is why item 5 measures rather than cites.

## 9. Item 8: the `role:swe` spec for `trillium/janus1f`, frozen as a diff against #306

**Taken from #306 unchanged:**
- §1 entirely: `configs/janus1/split-2026-11.json`, its pin, the `segtrain.janus1_split.refuse` guard and its
  tests;
- A17a's `nnUNetTrainer_segtrain_finetune`, its warm-up and poly schedule, and the sha256 log of the start;
- the chain-resumable job logic;
- `status`, `collect` and the dry run (named `JANUS1F_DRYRUN=1`);
- `splits_final.json` with two identical entries, so that a1 = fold 0 and a2 = fold 1;
- no change to `tf1.py` (A1c).

**Changed or added for 1-F:**

| # | Item | Spec |
|---|---|---|
| 1 | Header | Fir: `--account=def-aso22 --gpus-per-node=h100:1 --cpus-per-task=12 --mem=280G --time=23:50:00` (icx4's) |
| 2 | Dataset | **719**, from the 620 + the locked 100. Refuses an id already in use |
| 3 | Labels | `j1f_labels.py` (Delta v1, `experiments/Delta/j1f_r1/`), with D47's (A) fixed: L-PDA/L-PLA → PDA/PLB; "Other" touching only the RCA or nothing → 255 (F-A3). Its four-class identity check against `territory.py` runs on every case. Its sha256 is pinned. No left-PDA switch |
| 4 | Plans | Janus 0's `plans.json` byte-identical (`nnUNetv2_move_plans_between_datasets`, then `nnUNetv2_preprocess`). No fingerprint, no `plan_experiment`. `SEGTRAIN_CT_WINDOW=off`. Mirroring off |
| 5 | Loader | `finetune_load` gains the parent-copy option (Delta v1 §11.1; parent map `configs/janus1/j1f_parents.json`). Before epoch 0 it refuses unless, on one random batch: (a) territory sums equal Janus 0's within 1e-5; (b) the hierarchical decode equals Janus 0's argmax on every voxel |
| 6 | Fit check (F-A5) | A trainer hook at the ends of epochs 150 and 300. It predicts the 20 training cases with the smallest sha256(`asclepius-j1f-fitcheck:` + id) with the current weights, decodes as item 8, and writes per-class Dice to `fitcheck.json`. At 150 it writes `STALL` if any of D1, OM1, PDA or PLB is below 0.10 |
| 7 | Baseline (no J0) | Janus 0's Fir predictions of the locked 100 and icx4's aortas, from `$KEEP` (Step T) or else `$SCRATCH/icx4`. The **identity check** (F-A8): `branch_score`'s vessel path re-scores Janus 0's val-80 predictions to decisive macro 0.909 ± 0.003, each class within 0.01. Otherwise it refuses. No t\* (#306's rule W does not apply, §7 of the ruling) |
| 8 | Prediction and decode | `nnUNetv2_predict --save_probabilities --disable_tta` on the locked 100, a1's and a2's folds. **F:** hierarchical decode (F-A4). **T:** Janus 0's argmax territory, then 1-F's within-territory argmax. Both written as label maps. Probabilities are deleted after both are written (disk) |
| 9 | Scorer | `lib/branch_score.py` (§3). It imports `segqueue14.labels.assign_contact_branches` and uses A1c for vessels and branch tF1 |
| 10 | Decision | `DECISION.md`: V (H1's form, L3 included), then B with `j1f_gates.json` (B-v2-1), then the verdict table of F-A6. The fixed sequence is printed with each line's number and pass/fail. F-A9's reports go in `REPORTS.md` beside it (rule-ordinal reading, sibling confusion, val 80 / locked 20 apart, Ramus/D3, `fitcheck.json`) |
| 11 | Replicate | `JANUS1F_RUN=b` trains fold 1 with a different seed, report only (D47 Q8). `DECISION.md` is written from a1 only. A line in `REPORTS.md` says whether b's verdict would have been the same |
| 12 | Re-fetch | If `$SCRATCH/icx4` was purged: Janus 0's files from `$KEEP`; CT by `trillium/fetch_cases.py`; ImageCAS-X labels for the 720 non-sealed cases by a range-request fetch (as `experiments/Bridge/j1f_r2/fetch_seg620.py`, widened to the locked 100 for scoring only) |
| 13 | Refusals | A sealed or locked case in training; a split-hash mismatch; plans not byte-identical; a Janus 0 checkpoint whose sha256 differs from Step T's; either identity check failing; a used dataset id; a pinned hash (§3) that differs |

**Tests (CPU):**
- the parent-copy identity on a tiny network, both checks;
- hierarchical decode against a hand-built 13-channel volume, where plain argmax and the hierarchical decode
  differ;
- `branch_score` on a synthetic tree: one D1 missed, one misnamed, a PDA off the LCx (collapses to LCx), and a
  two-piece PDA (two roots);
- the gate file read and the "4 of 6" verdict table, for each row;
- the dry run printing the split pins, the label counts of F0, the hashes and the refusals.

**Not in this issue:** stage 2's label-set trainer and Job B's budget options. They come in a second issue before
J1F-B or J1F-2, so that stage 1 is not held for them.

## 10. Item 9: the warm start if Janus 1-L is adopted first

**J1F-A starts from Janus 0, and V compares against Janus 0, whatever 1-L's verdict.** Four reasons:

1. **The question stage 1 answers is "does growing branches cost the vessels".** It is answered cleanly only
   against the parent the branches were grown from. The step-0 identity (F-A2) makes that comparison exact.
2. **Janus 1-L is Janus 0 fine-tuned on the same 620 cases**, at 250 epochs ([[Master plan - Janus 1-L]]). It brings
   no new data to 1-F. Its expected change is small: D46 Q4 adopts it if non-inferior.
3. **Its export threshold t\* is a width fix outside the network.** 1-F decodes by argmax. Comparing 1-F's argmax
   with 1-L at t\* would mix a decoding change with a training change.
4. **1-L's checkpoint lives on Trillium.** Moving it to Fir and re-predicting adds the cross-cluster difference
   F-A8 was written to avoid.

**If 1-L is adopted before J1F-A is read, two reports are added, deciding nothing:**
- **V′:** F against 1-L's locked-100 predictions (copied from Trillium, at 1-L's own export). Δ macro tF1 with its
  CI.
- **T′:** 1-L's territories with 1-F's within-territory names.
- The release note then says which vessel model a shipped 1-F carries. Pairing 1-F's names with 1-L's vessels is a
  product choice for the lead, made on V′ and T′.

**Stage 2** starts from the shipped stage-1 model, as F-A11 says. Its forgetting guard (L3, §5.2) is against that
model.

## 11. Item 10: one census of record

| Quantity | Of record | Value on the 620 | Why this one |
|---|---|---|---|
| **Label counts that feed training** (D3 from "Other", ignored pieces, L-PDA/L-PLA) | `j1f_labels.py`'s own summary, reproduced on Fir by F0 | D3 47; "Other" diag 50 / marg 20 / ambiguous 8 (the F0 line in the master plan) | It is the converter that makes the training labels, so its count is the one the model sees. Bridge v1's 48 is withdrawn: it counted by a looser origin rule |
| **Dominance** | ImageCAS-X's `Descriptors.xlsx` (its own definition), 620 rows | **Right 564, left 35, co-dominant 21** | The dataset's field, not an inference |
| **Cases with a left-sided PDA or PLA** | Labels | **59** (35 left-dominant, 19 co-dominant, 5 right-dominant by the descriptor) | The number that matters for D47's collapse |
| **Unnamed trunk twigs** | `census_r2.py`: the skeleton of each trunk class, minus its longest path; each remaining skeleton component is a twig of length (voxels × mean spacing) | Cases with a twig ≥ 3 mm / ≥ 5 mm: **LAD 6 / 3, LCx 1 / 1, RCA 2 / 1**. At most one twig per case. Totals: **9 / 5** twigs in 620 cases | One method, two cut-offs, code in the repository |
| **Per-class geometry** (volume, length, diameter, origins) | Bridge v1 `census_620.jsonl` | Bridge v1 §2.4 | The only per-branch table with origins |

- **Atlas's dominance (34 left, 21 co-dominant of 613) agrees with this to within its seven fewer cases.**
- **Bridge v1's and Foxtrot's "46 left" were label inferences.** They are replaced by the descriptor.
- **On twigs:** Crucible's 13, Delta's 4 and Foxtrot's 6 used three methods. The census above replaces all three
  for quotation. **ImageCAS-X almost never leaves an unnamed side twig on a trunk**: 9 twigs of at least 3 mm in 620 cases,
  each in a different case.
  - This is closest to Delta's 4 and Foxtrot's 6. Crucible's 13 is not reproduced.
  - No twig rule is needed in the converter or the scorer: at most 1.5 % of cases would be touched.

## 12. Item 11: D47's and Q8/Q9's consequences

| Answer | Consequence in this plan |
|---|---|
| **Q1 (A)** | Labels: L-PDA/L-PLA → PDA/PLB, fixed (§9 item 3). Collapse: SegQueue's function (§3). F-A3's and F-A4's (B)/(C) clauses lapse. V's Janus 0 reference is not relabelled (that was (C) only) |
| **Q2 Step T** | The baseline and the re-fetch read from `$KEEP` first (§9 items 7, 12). **Step T has not run.** Until it has, the scratch purge (about 2026-12-20) can remove Janus 0's checkpoint, plans and predictions. J1F-A cannot start without them |
| **Q3 complete flag** (#326: `completeGroups`) | Stage 2's label sets for an extended read: a parent group ticked complete is a **singleton** (its unseen children are absent). Unticked, the parent stays {parent ∪ children}. `null` (older modules) is treated as unticked |
| **Q4 child-in-parent** | Stage 2: an extended-read voxel in both a branch and its own parent trains as the branch. Unrelated overlaps stay 255 |
| **Q5** | Unchanged. Revisit at the first pool wave if fewer than 30 patients have a septal read. Job B's k\* says whether 30 is the right count |
| **Q6 D35 extended** | §7. The D35 wave measures p per class |
| **Q7 trace beyond seed** | Makes §5.2's band-from-reads measurement possible: drawn septals are no longer cut off at the seed |
| **Q8 a2: yes if the allocation allows** | a2 runs **concurrently** with a1 (fold 1, §9 item 11), ≈ 29 GPU-h, report only. It gives the first between-run spread of branch presence, naming and tF1, which J1F-B and any later recipe claim need (A37). **Priority if Fir is short:** a1, then a2, then J1F-B |
| **Q9** | The model read in F-A6 (F or T) is **Janus 1-F.1**. If adopted, it is Janus 1-F. a2, J1F-B, V′ and T′ take no number |

## 13. Proposed amendments (round 2, Bridge)

| # | Amends | Change |
|---|---|---|
| **B-v2-1** | F-A6 (B's numbers) | Per-class lines of §2.3, frozen in `j1f_gates.json` with `gate_sim.py`'s hash. "4 of 6" kept |
| **B-v2-2** | F-A4, F-A6 (scoring) | §3's definitions. Prediction collapse by `assign_contact_branches`, imported. Presence at 5 mm. (B)/(C) removed per D47 |
| **B-v2-3** | F-A11 (stage 2) | Leaf-Dice. Territory-specific label sets. Band d from the 95th percentile of drawn distances in extended reads, provisionally 8 mm. Leakage gate L1–L3 |
| **B-v2-4** | F-A10, F-A11 | J1F-B: two arms, k ∈ {20, 60}, absolute read against B-v2-1's lines on a 60-case hold-out, ≈ 22 GPU-h, after J1F-A |
| **B-v2-5** | §5 item 3 | Arm N not built. Revisit only on a "< 4 of 6" verdict |
| **B-v2-6** | F-A2 (§5 item 9) | Start and V's comparator stay Janus 0. V′ and T′ are reported if 1-L is adopted first |
| **B-v2-7** | F-A12 | The swe issue of §9, opened after this round's ruling. Stage-2 code goes in a second issue |

## 14. What Step T and F0 would change (neither has run)

| Job | If it matches | If it does not |
|---|---|---|
| **F0**: split pins, label counts on Fir | §11's label counts become Fir-verified. Nothing else moves | **Stop.** Fir's ImageCAS-X copy or the converter differs. Every count in §2 and §11 that came from the converter is re-read from Fir's output before the swe issue is opened. The gate lines of §2.3 do not move: they depend only on the locked counts and Table 1 |
| **Step T**: `$KEEP` copy, three `SHA256SUMS`, counts 160 / 160 / 100 | The launcher's baseline and refusal on the checkpoint hash (§9 items 7, 13) point at `$KEEP` | If the counts differ (for example, fewer than 100 locked-100 predictions), V cannot be paired. The missing cases are re-predicted from Janus 0's checkpoint on Fir (≈ 1 GPU-h) before J1F-A is read. Without the checkpoint, the track waits (ruling §8) |
| **Step T not run by early December** | — | The PM escalates. Bridge has nothing to add to the ruling's §8 row |

## 15. What would change this plan

| Observation | Then |
|---|---|
| A second-reader study on the pool (D2's two reads) measures branch naming agreement directly | It replaces §2.1's mixture estimate of q. The lines are recomputed by the same rule before J1F-A is submitted, never after |
| OM2's locked count were below 30 | OM2 leaves the gated set and "4 of 6" becomes "4 of 5". It is 40 (Delta), so no change |
| Extended reads show the 95th-percentile septal distance from the LAD above 15 mm | The septal band is that wide, but the leakage gate L2 is then tightened to 5 % |
| J1F-B's k = 20 passes | Stage 2 may train a class at 20 patients from ≥ 3 sources, with F-A11's inter-read floor |
| J1F-B's k = 60 fails | The untraced classes need more than 60 reads each. The lead is told what that costs before a targeted extended-read campaign is proposed |
| `assign_contact_branches` changes in SegQueue | The scorer's pinned hash refuses. The swe PM decides whether 1-F follows (it should: one rule) |

## 16. Evidence

| Claim | Source | Used for |
|---|---|---|
| Per-segment inter-observer presence agreement and DSC (mean ± SD), 160 test cases, second analyst blinded | Bransby et al., *ImageCAS-X*, arXiv:2608.30404, Table 1 (as in Bridge v1 §5.2 and the ruling) | §2 |
| Septal perforators, acute marginals and nodal arteries not traced | same, Suppl. B | §5, §7 |
| Marginal loss: Table 3 rows (0.874, 0.900, 0.921, 0.931, 0.873, 0.876); Table 5's 0:1 row (0.897); Table 6 (0.874 → 0.774) | Shi, Xiao, Chen, Zhou, *Med Image Anal* 70:101979 (2021), arXiv:2007.03868v1, re-read from the PDF 2026-11-15 | §8, §5 |
| Leaf-Dice vs marginal Dice on scarce structures (CC 62.0 vs 11.1) | Fidon et al., MICCAI 2021, arXiv:2107.03846, Table 2 (as verified in [[Janus 1-F Round 1]]) | §5.1 |
| Conus with a separate ostium in 22 %; SN from the RCA 79 %, Cx 20 % | Koşar et al., *Diagn Interv Radiol* 15:275 (2009), Table 2 (Bridge v1) | §7 |
| Naming on automatic trees 0.74 vs reference trees 0.91 | Hampe et al. 2024 (vault-verified; [[Janus 1-F Round 1]] §3.2) | §4 |
| SegQueue's D47 contact rule | `src/segqueue14/labels.py`, `assign_contact_branches` (PR #326) | §3 |

## 17. Code and cost

`experiments/Bridge/j1f_r2/`:

| File | What | Runtime |
|---|---|---|
| `gate_sim.py` → `gate_sim.json` | §2: human-level false-fail of the ruled and proposed gates, plus power | seconds |
| `fetch_seg620.py` | The 620's segmentations and `Descriptors.xlsx`, by range requests | ≈ 5 min |
| `census_r2.py` → `census_r2.jsonl` | §3 contact rule, §5 bands, §11 twigs, per case | ≈ 5 h on 2–4 cores |
| `summarise_r2.py` → `census_r2_summary.json` | The tables of §3, §5 and §11 | seconds |
| `untraced_yield.py` → `untraced_yield.json` | §7 | seconds |
| `test_j1f_r2.py` | Self-tests: the q fit recovers a planted mixture; the twig measure on a synthetic trunk with one known twig | seconds |

**Cost:**
- **GPU:** J1F-A ≈ 30, a2 ≈ 29 (D47 Q8), J1F-B ≈ 22 (new), J1F-2 ≈ 15 when reads exist.
- **Before round 3:** 0 GPU-h.
