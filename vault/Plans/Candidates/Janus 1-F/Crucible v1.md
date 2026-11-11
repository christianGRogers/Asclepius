---
tags: [plans, candidate, track-1F, round-1, janus-1F, fir, partial-labels, D44, D45]
author: Crucible
track: Janus 1-F
round: 1
version: 1
updated: 2026-11-11
issue: christianGRogers/Asclepius#303
---

# Crucible v1 (Janus 1-F): ImageCAS-X never traced six of 1-F's classes, so 1-F learns the eight it did trace first, adds the rest only from extended reads through a label-set loss, and keeps Janus 0's vessels by construction

## 0. Thesis

1. **ImageCAS-X's partial labelling is in its background, not only in its names.**
   - Its protocol says: "Septal perforators, acute marginals and nodal arteries were not traced". Side branches stop
     where the distal diameter is under 1 mm. "Other" holds a D3/D4/OM3/OM4 only if it is "at least as large as the
     first or second branches or >1.8 mm" (Bransby et al., arXiv:2608.30404, §2 and Table 1).
   - On the 620 training cases, the trunk classes carry almost no unnamed branch: {TWIG_LINE}
     ([[Crucible - ImageCAS-X traced no septal, nodal or acute marginal branch, so its background is not a negative for six of 1-F's classes]]).
   - So a voxel of a septal, the SN, the conus or the RMA is **background** in ImageCAS-X. So is a small D3. Train 1-F on
     ImageCAS-X as drawn and it learns to *not* segment S1–S3, SN, Conus and RMA. Their only positive labels will be
     extended pool reads, which start at zero.
   - Ignore-masking the unknown names does not fix this, because the problem is the background. The fix is a
     **label-set (marginal) loss**: every voxel carries the set of 1-F classes it may belong to, and background near the
     traced tree may be any untraced class (§3). This is what Shi et al. (MedIA 2021) and Fidon et al. (MICCAI 2021)
     built for "background merges unlabelled classes".
2. **Two stages, gated on counts, not dates.**
   - **Stage A (now, ImageCAS-X only): Janus 1-F₀**, 12 classes plus background: the four vessels and the eight
     branch classes ImageCAS-X traced (D1, D2, D3, OM1, OM2, Ramus, PDA, PLB).
     - Plain nnU-Net with a remapped label. No class without a positive label gets an output.
   - **Stage B (when extended reads reach the per-class counts in §7): Janus 1-F₁**, all 18 classes.
     - The six untraced classes get heads.
     - Training switches to the label-set loss over ImageCAS-X + pool reads.
   - A class with no positive label is not trained and not reported.
3. **One network, warm-started from Janus 0 by head inheritance.**
   - Every new branch output starts as a copy of its parent's output layer, with the bias lowered by log(k). At step 0,
     1-F₀ therefore predicts exactly Janus 0's territories, split evenly among a parent and its k−1 children.
   - Training only has to learn the split. icx14 failed differently: from scratch, the side-branch Dice sat at 0 for
     440 epochs while CE's majority class (the parent) won (§8).
   - A 150-epoch pilot (about 10 GPU-h) tests that the branches unlock before the full run is paid for.
4. **Janus 0's vessel line is guaranteed, not hoped for.**
   - On the locked 100, 1-F₀ collapsed to four must be non-inferior to Janus 0 (margin 0.02, the margin Round 10
     adopted on val 80).
   - If it is not, the delivered 1-F is the **hybrid**: Janus 0's (later 1-L's) vessel voxels, named by 1-F₀ within
     each territory. Its four-class output is identical to Janus 0's by construction. It costs CPU only.
   - So 1-F can never make the vessels worse. The lead gets branches either way.
5. **The L-PDA/L-PLA question has a measured price.**
   - Recommended to the lead: name by anatomy (L-PDA → PDA, L-PLA → PLB); collapse to four by origin.
   - #280/#310's default collapse sends PDA/PLB always to RCA. That contradicts D25 for left-sided PDA/PLB, in
     {LDOM_CASES} of the 620. There they are a median {LDOM_SHARE} of the LCx territory (§2.2).

## 1. What ImageCAS-X gives 1-F (CPU, 620 D45 training cases)

`experiments/Crucible/j1f_r1/`:
- `split.py` builds D45's split from id lists only. No label file of the locked 100, the sealed 80 or the sealed
  quality-0 20 is opened. The 20 locked open-36 cases, by sha256(`asclepius-janus1-locked100:` + `c0000`-style id),
  are c0068, c0102, c0251, c0271, c0323, c0327, c0470, c0545, c0592, c0620, c0644, c0805, c0807, c0824, c0827, c0841,
  c0908, c0946, c0957 and c0996. The id form (`cNNNN`, as in `sealed_test.json`) is my reading of D45. **The lead
  or #302's launcher must confirm the same 20** before any 1-F or 1-L job (§9).
- `census.py` and `summarise.py`: labels only, no CT.

{CENSUS_TABLE}

Reading it:
- **Eight 1-F branch classes have ImageCAS-X labels**, with these case counts: D1 {N_D1}, D2 {N_D2}, OM1 {N_OM1},
  OM2 {N_OM2}, Ramus (IM) {N_IM}, PDA (R + L) {N_PDA}, PLB (R + L) {N_PLB}, and D3 (inside Other, below) {N_D3}.
- **D3 exists only as a large "Other" piece.**
  - D-family Other pieces (those touching LAD/D1/D2 only) appear in {N_D3} cases ({P_D3}). Per case: {DCOUNT}.
  - Every one touches the LAD trunk itself, so it is a diagonal off the LAD.
  - A case with one such piece gives a D3 label. With two or more, the proximal-most piece is D3 and the rest are
    LAD (D4+, parent class).
  - A small D3 is untraced, so ImageCAS-X has **no D3-absent label**. A case without Other may still have a D3 in its
    background. That is why D3 is in the untraced set of the background (§3).
- **Calibre.** The thinnest traced branches have median skeleton radius {RAD_BRANCH} mm. In about a quarter of the
  cases with a given branch, the branch's 10th-percentile radius is below 0.5 mm.
  - At nnU-Net's 0.5 mm isotropic grid, a vessel at ImageCAS-X's 1 mm stopping diameter is 2 voxels across.
  - Septals, SN, conus and RMA are untraced, so their calibre cannot be measured here.
  - Septals and nodal arteries are expected to be at or below that floor for most of their length. Expect their
    extended reads to be short and to disagree; that is why §7 gates them on inter-read agreement.

## 2. The label map, 1-F ← ImageCAS-X

### 2.1 Table

| ImageCAS-X | Stage A (1-F₀) target | Stage B (1-F₁) label set |
|---|---|---|
| background | background | {background, S1, S2, S3, SN, Conus, RMA, D3} within the band (§3.2); {background} outside it |
| LM (1) | LM | {LM} |
| LAD (2) | LAD | {LAD} (an untraced septal is background, not LAD: §1) |
| LCx (3) | LCx | {LCx} |
| D1 (4), D2 (5) | D1, D2 | {D1}, {D2} |
| OM1 (6), OM2 (7) | OM1, OM2 | {OM1}, {OM2} |
| IM (8) | Ramus | {Ramus} |
| RCA (9) | RCA | {RCA} |
| R-PDA (10), R-PLA (11) | PDA, PLB | {PDA}, {PLB} |
| L-PDA (12), L-PLA (13) | **PDA, PLB** (L1 default; else LCx) | {PDA}, {PLB} |
| Other (14), D-family, proximal-most piece | D3 | {D3} |
| Other (14), D-family, later pieces | LAD (D4+, D1 territory) | {LAD, D3} |
| Other (14), OM-family | LCx (OM3+, no OM3 class) | {LCx} |

- **Unlisted branches take their parent's class** (D1 territory, as the #280 collapse already does): D4+, OM3+,
  S4+, AV-nodal and atrial branches, and any unnamed RCA branch.
  - Under D44 this is the only reading that keeps every voxel in exactly one class.
  - It is written here as an assumption (L2), because D44 does not say it.
- **ImageCAS-X's LAD is LAD only.** Septals were not traced, so the LAD label is not "LAD or septal". The census
  confirms it (§1): no unnamed branch hangs off the LAD class in {LAD_TWIG_PCT} of cases.

### 2.2 The PDA/PLB question (for the lead, L1)

| Reading | 1-F label for L-PDA / L-PLA | Four-class collapse | Effect |
|---|---|---|---|
| **(a) By anatomy (recommended)** | PDA / PLB | **By origin**: a PDA/PLB connected to the LCx goes to LCx (D25) | One PDA class whatever the dominance; D25's four classes unchanged |
| (b) By origin only | LCx (as in D25) | PDA/PLB → RCA always (as #310 does today) | No left-dominant PDA is ever "PDA"; 1-F's PDA is a right-only class |
| (c) As #310 now | annotators' choice (wording) | PDA/PLB → RCA always | A left-dominant read's PDA voxels move from LCx to RCA in the four-class score |

- **Why (a).** "Posterior descending" names a vessel by its course in the posterior interventricular groove. The
  ImageCAS-X authors named it the same way (L-PDA is a PDA, from the left), as did Li et al. (arXiv:2212.00386:
  L-PDA and L-PLB are classes).
- **The price of (c).**
  - In the 620, {LDOM_CASES} have L-PDA or L-PLA. There they are a median {LDOM_SHARE} (p90 {LDOM_P90}) of the D25
    LCx territory.
  - In those cases the four-class pair score of an extended read against a 4-class read moves that much LCx into RCA.
  - Population left dominance is 9 % on CCTA (Gebhard et al., CONFIRM, EHJ-CVI 2015, 6382 patients, Results).
  - **#310's collapse should go by origin in left-dominant hearts. It is a one-line swe change if the lead picks
    (a).** This is reported to the lead; this plan changes nothing in SegQueue.
- **SN** is likewise one class whatever its origin. It comes from the RCA in 68 % and from the LCx in 22 % (Vikse et
  al., PLoS One 2016, Table 3). The four-class collapse of an SN goes by origin for the same reason.

## 3. The partial-label strategy

### 3.1 Stage A: no custom loss

- 1-F₀ trains only the 12 traced classes, so ImageCAS-X's labels are complete for 1-F₀'s own class list, apart from
  small D3s (§2.1).
- One caveat: an untraced septal is background for 1-F₀. That is correct, because 1-F₀ has no septal class.
- Stock nnU-Net v2 losses (CE + Dice) on the remapped labels.
- **No ignore label in stage A.** ImageCAS-X has no overlaps (D40 does not arise), and D4+ is defined as LAD.

### 3.2 Stage B: label-set loss

**Loss**, per voxel with label set g:
- **CE term:** marginal CE, −log Σ_{c∈g} p_c (Shi et al., MedIA 2021, "marginal loss").
- **Dice term:** leaf-Dice (Fidon et al., MICCAI 2021). A class's Dice counts only voxels whose label set is that
  single class, plus that class's predicted mass.
- Fidon et al. Table 2 is why the Dice term matters:
  - marginal Dice **collapsed on scarce classes** (corpus callosum 11.1 % Dice; deep grey matter 37.8 %);
  - leaf-Dice reached 62.0 % and 71.4 % on the same classes.
  - Our six untraced classes are the scarcest we have. Marginal CE plus leaf-Dice is the combination their axioms
    allow.

**Where the background is a set.**
- ImageCAS-X background within a **band** around the traced tree is {bg, S1–S3, SN, Conus, RMA, D3}. Outside it,
  background is {bg}.
- The band is the traced tree dilated by 15 mm, in the territories that can host the classes:
  - septals and D3 near the LAD;
  - SN, conus and RMA near the RCA;
  - SN near the proximal LCx too (22 %).
- 15 mm is an opinion. It is set to reach a proximal septal or the conus from its parent. It is a config value,
  tested in the stage-B pilot (§9, P2: share of untraced-class predictions outside the band = 0 by construction;
  inside it, reported).

**Pool reads** (D23's 675-volume queue, via D44's extended classes):
- An **extended read** (toggle on, #310) is complete for the classes it draws.
  - A voxel left in a parent after the annotator moved a branch out is the parent, as drawn.
  - A branch the annotator did not separate is still inside the parent. So the parent's label set is
    {parent, its listed branches} for the parent classes whose branches were not used in that read. "Not used" means
    no voxel of any child class in that read.
- A **4-class read** gives each territory the set {parent, all its children} (the #280 collapse, inverted).
- **Overlaps.** A voxel in a parent and one of its own children is {that child}: the D26 copy was simply not
  trimmed. Any other overlap is D40's ignore label.
  - **The parent–child rule extends D40 and goes to the lead (L3).** D40 as written makes every overlap ignore.
  - The default, until the lead answers, is D40 literally: ignore.
- ImageCAS-X replay keeps every ImageCAS-X case in stage B (sequential fine-tuning forgets; Gonzalez et al.,
  arXiv:2010.11008, Table II, cited in Crucible v11).

**Why not the alternatives.**
- **Ignore the unknown classes** (MultiTalent: per-class sigmoid heads, loss only on annotated classes; Ulrich et al.,
  MICCAI 2023, arXiv:2303.14444, §2.2):
  - MultiTalent's datasets annotate an organ either fully or not at all. Ours annotate a septal nowhere in ImageCAS-X
    while drawing its neighbour LAD.
  - With per-class sigmoids and the septal head masked on ImageCAS-X, nothing stops the septal head firing on the
    LAD. The exclusion that softmax gives for free must then be re-added (Shi et al.'s exclusion loss).
  - Softmax with label sets keeps exclusion and needs no new head type. That is the smaller change to nnU-Net.
- **Treat untraced as background**: the default failure (§0.1).
- **Re-annotate ImageCAS-X's septals** (lifts D22): not proposed. The question is the lead's, and §7 shows the pool
  can supply the counts if annotators use the extended classes.

## 4. Architecture and recipe

### 4.1 One network, not segment-then-label

- **For one network.**
  - The pieces exist: Janus 0's nnU-Net ResEnc on ImageCAS-X (val-80 macro tF1 0.909) and nnU-Net's training loop.
  - A second-stage labeller needs centrelines and a trained graph model. The published ones train on hundreds of fully
    labelled trees: CPR-GCN on 511 subjects, two experts, mean F1 0.955 (Yang et al., CVPR 2020, arXiv:2003.08560,
    Table 3), with S at 0.964 and D/OM/RI the weakest (0.909–0.914). The six untraced classes have no tree labelled
    with them, so a graph labeller is just as starved.
  - Li et al. (arXiv:2212.00386, Table 1) report low performance on L-PDA (39 branches) and R, attributed to few
    samples.
- **Against.** icx14 is the project's direct-multiclass failure. §8 is why head inheritance and a pilot answer it.
- **The two-stage idea is kept where it is cheap.** The hybrid (§0.4) is segment-then-label with 1-F₀ as the labeller
  and Janus 0 as the segmenter. It is pre-registered as the fallback (§6) and costs CPU only.

### 4.2 Recipe, Janus 1-F₀ (stage A)

- **Data:**
  - 620 training cases (D45);
  - nnU-Net fold-0 validation = the locked 100, used only for nnU-Net's pseudo-Dice log;
  - `checkpoint_final` only. `checkpoint_best` is never used, because it would select on the locked 100.
- **Network:** Janus 0's plans (Dataset715, ResEnc 60 GB, 0.5 mm, 256³, batch 2, mirroring off). 13 output channels.
- **Warm start by head inheritance.**
  - Load all of Janus 0's weights.
  - Each new channel's 1×1×1 output conv (every deep-supervision head) = a copy of its parent's, bias − log k, with
    k = 1 + the number of children of that parent:
    - LAD → D1, D2, D3 (k = 4);
    - LCx → OM1, OM2, Ramus (k = 4);
    - RCA → PDA, PLB (k = 3).
  - The parent's own bias is also − log k. Σ softmax over a territory then equals Janus 0's territory probability at
    step 0.
  - Stock `-pretrained_weights` re-initialises the heads (Foxtrot's R10 note), so this is a custom trainer
    `nnUNetTrainerJ1F` (swe item, §9).
- **Schedule:** 500 epochs, poly LR from 1e-2 with a 10-epoch linear warm-up (the A17a trainer's shape).
  - 500 epochs, not 250, because branches unlocked late in icx14.
  - Not 1000, because the trunks are already learned. The pilot decides whether 500 is needed (§9).
- **Class-weighted CE:** off by default. It switches on (weight 4 on branch classes, icx14's file
  `ce_class_weights.json`) only if the pilot fails gate P1-b.
- **No seed replication** (D28's spirit). The decision is on a model, not a recipe (§6).

### 4.3 Recipe, Janus 1-F₁ (stage B, later)

- Warm from 1-F₀, with new heads for S1, S2, S3, SN, Conus and RMA inherited from LAD (S1–S3), RCA (SN, Conus, RMA).
- Trainer `nnUNetTrainerJ1FLabelSet`: marginal CE + leaf-Dice; label sets from §3.2 (written per voxel as a set
  bitmask in a second label channel).
- 250 epochs over ImageCAS-X 620 + every trainable pool read (D35, seal and reserve refused by the guard Round 10 set,
  #116), each read a sample (A11′).

## 5. Metrics

| What | Classes | Set | How | Decides? |
|---|---|---|---|---|
| **Vessel tF1** (A1c, decisive, 1.5 mm) | LM, LAD, LCx, RCA after the four-class collapse | locked 100 | Collapse: children to parent, **PDA/PLB/SN by origin** (connected-component touch, the D25 rule). Untraced classes (S, SN, Conus, RMA) **dropped to background**, because ImageCAS-X never traced them, so they cannot count as FP or TP against it | **Yes** (§6 R1) |
| **Branch detection** | each traced branch class | locked 100 | A reference branch = one connected component of that ImageCAS-X class. It is detected if ≥ 50 % of its skeleton lies within 1.5 mm (D3) of predicted vessel of any class | **Yes** (R2) |
| **Branch naming accuracy** | same | locked 100 | Of detected branches, the share whose skeleton is ≥ 50 % covered by the **same** class (Bridge's swap rule) | **Yes** (R2) |
| Branch F1 | same | locked 100 | Precision = predicted components of a class that match a reference branch of that class | Report |
| Per-class Dice | 12 | locked 100 | Against ImageCAS-X's inter-observer DSC (Table 1: D1 79.9, D2 82.9, OM1 74.1, OM2 77.7, IM 80.6, R-PDA 82.6, R-PLA 83.6, L-PDA 75.1, L-PLA 70.9, Other 81.3) | Report (A28) |
| Per-class centreline recall/precision @ 1.5 mm | 12 | locked 100 | Recall shows extent; precision shows naming spill | Report |
| **Untraced classes on ImageCAS-X** | S1–S3, SN, Conus, RMA (1-F₁) | locked 100 | (i) share of their predicted voxels inside ImageCAS-X's traced lumen (should be ≈ 0; a high share means they steal a traced vessel); (ii) predicted volume per case | (i) gates 1-F₁ (§6 R4) |
| **Untraced classes on pool reads** | S1–S3, SN, Conus, RMA, and D3 again | D35 patients with extended reads | Detection and naming against each read, and the same between the two reads (the human line); D6-style contrast | Report until §7's counts are met |

**Scoring classes with no ImageCAS-X labels.** Only against extended pool reads, only on D35 patients (never trained
on), and only once §7's count is met. Before that, they are reported as "not scorable". The one thing ImageCAS-X can
check is that they do not eat traced vessels (row (i)).

## 6. The pre-registered decision on the locked 100

Written before any 1-F model exists. Janus 0's predictions of all 1000 cases already exist (#43). The in-job scorer
scores Janus 0 and 1-F₀ on the same 100 with the same aortas.

**R1. Vessels (must hold Janus 0's line).**
- 1-F₀'s four-class collapse (§5) is **non-inferior to Janus 0 on locked-100 decisive macro tF1 at margin 0.02**:
  one-sided 95 % patient-bootstrap lower bound of (1-F₀ − Janus 0) > −0.02.
- **And** no class's point difference is below −0.03.
- No seed term. This decides on a checkpoint, not a recipe (A22's model/recipe split).
- Power: with Janus 0's paired SD (≈ 0.069; Crucible v11 §2.3, Atlas's measured trained-network pairs scaled to Janus
  0's spread), an equal model passes about 0.89 of the time at n = 100.
- 0.02 is Round 10's val-80 margin (§3.3 there).

**R2. Branches (is 1-F₀ a branch model at all?).**
- Over the eight traced branch classes, the macro of (detection × naming accuracy) is ≥ 0.70.
- Each class with ≥ 20 reference branches in the locked 100 has naming accuracy ≥ 0.70.
- **These thresholds are set from human agreement, not from a measured model:**
  - ImageCAS-X's side-branch inter-observer DSC is 71–83 (Table 1);
  - CPR-GCN's side-branch F1 is 0.91 on expert centrelines.
  - 0.70 is a floor below both, chosen so that a model at the human level passes.
- Expected counts in the locked 100 (scaled from the 620): {EXPECTED_LOCKED}. L-PDA/L-PLA alone are too rare to
  decide anything; they are pooled into PDA and PLB.

**R3. Outcome.**

| R1 | R2 | Delivered |
|---|---|---|
| pass | pass | **1-F₀ is Janus 1-F** (D34 numbers it when read) |
| fail | pass | **The hybrid** (Janus 0's voxels, 1-F₀'s names within each territory). Its R1 is identical to Janus 0 by construction; R2 is re-scored on the hybrid and reported |
| either | fail | No branch model. Report per class. Next: the class-weighted arm (§10). The hybrid is not delivered |

The open-36 check of A26 has no analogue: the 20 open cases are inside the locked 100. Dev-44 and the 16 open cases
are training cases now (D45). The sealed 80 stay untouched.

**R4 (1-F₁, later).** Re-run R1–R2 against 1-F₀ and Janus 0. In addition:
- (i) the share of untraced-class voxels inside ImageCAS-X's traced lumen is ≤ 0.02 per class on the locked 100;
- (ii) per §7, on D35 extended reads, model-vs-read detection × naming for each untraced class is within 0.10 of
  inter-read, reported with its CI.

## 7. How many reads per class

**Detection-rate CIs** (`reads_per_class.py`, Wilson 95 %):

| True rate | Patients with the class for ±0.15 | ±0.10 | ±0.05 |
|---|---|---|---|
| 0.7 | 33 | 78 | 320 |
| 0.8 | 26 | 60 | 245 |
| 0.9 | 17 | 37 | 141 |

**Rules (pre-registered):**

| | Count needed |
|---|---|
| **Train** a class (give it a head in 1-F₁) | ≥ **30 extended reads** in which the class is drawn, from ≥ 15 trainable (non-D35, non-sealed, non-reserved) patients, **and** inter-read agreement for that class (both reads extended) ≥ 0.6 detection × naming on ≥ 10 patients |
| **Report** a class (in R4 ii) | ≥ **26 D35 patients** with the class in both reads (±0.15 at 0.8) |
| **Decide** anything on a class | ≥ 60 patients with the class (±0.10). D35 has 35 patients, so no untraced-class decision is possible on D35 alone; the seal (150) could supply it at acceptance |

Notes:
- The training count is an opinion. Li et al.'s 39 L-PDA branches were too few for a GNN, and CPR-GCN's weakest classes
  were the least frequent.
- The agreement floor stops training on a class the readers cannot draw consistently, which is the expected failure
  for septals and SN at the 1 mm floor (§1).
- **D35 alone cannot report a rarer class.** At prevalence 0.5 (for example, a conus that arises from the RCA rather
  than its own ostium; reported at 30–50 % separate, not sourced here), D35 yields 18 patients, ±0.18. Such a class is
  trained but reported only from the seal at acceptance, or not at all.
- These counts depend on how many annotators turn the extended toggle on (#310, off by default). **That rate is
  unknown, so stage B is gated on counts, never on a date.** The extended-read count per class goes on the wave-1
  dashboard (swe item).

## 8. Lessons from icx14 (D9/D10, reversed by D25)

| icx14 | Cause | This plan |
|---|---|---|
| All ten side-branch classes at pseudo-Dice 0 for 446 epochs; D1 present in 631 / 640 cases | From scratch, CE's majority (the parent) wins early; a branch is told apart only by its place in the tree | Head inheritance from Janus 0: the territory is already right at step 0. The pilot (P1) checks the unlock at 150 epochs before 500 are paid |
| R-PLA unlocked at epoch ~440 in job 2; nothing else had unlocked by 455 | Classes unlock one at a time and late | 500 epochs, not 250; class weights (4×) ready as the fallback arm |
| Job 2 restarted from scratch (resume test needed both checkpoints), 23 GPU-h lost | `checkpoint_latest` deleted at `on_train_end` | icx4's fixed `job_body.sh` is reused; the swe item adds a 2-chunk CPU self-test that exercises a resume |
| Trunk Dice was not comparable to territory Dice | Side branches split out | §5 scores vessels after the collapse, which is the only comparison with Janus 0 |
| 14 classes chosen before any data said they were learnable | — | Stage A trains only the eight traced classes. A class is added only at §7's counts |

## 9. Fir jobs (for the lead; account `def-aso22`)

All jobs: `h100:1`, 12 cores, 280 G, 23:50 (`ICX4_CLUSTER=fir` header). They are costed at Janus 0's measured
192 s/epoch (13 output channels add < 1 % to the step).

**Preconditions:**
1. **The swe item merged into `dev`: `trillium/janus1f`.** It contains:
   - the remap of §2.1 (with the D3 proximal-most rule and the L1 switch `LPDA=anatomy|lcx`);
   - `nnUNetTrainerJ1F` (head inheritance, warm-up, poly);
   - D45's split by `split.py`, refusing unless the 20 locked ids equal #302's;
   - in-job scoring of §5 on the locked 100 for 1-F₀ **and** Janus 0's existing predictions (A1c, aortas in-job for
     the 20 cases without one);
   - the hybrid (CPU);
   - a 2-chunk resume self-test.

   This plan does not open the issue. It is opened with `role:swe`, linked to #303, when a ruling adopts the recipe,
   so that five round-1 candidates do not leave five issues.
2. The lead's answer to L1 (or the default, anatomy).

### Job P1: pilot, 150 epochs. About 10 GPU-h (8.0 training + 1.5 preprocessing + 0.5 scoring)

- Trains on 580 of the 620, with an **internal val of 40** (the 40 smallest sha256(`asclepius-j1f-pilot:` + id)
  of the 620).
- **The locked 100 is not opened.**

```sh
# Fir login node, inside tmux
module load StdEnv/2023 python/3.11.5
cd $SCRATCH/asclepius && git -C repo pull --ff-only
mkdir -p experiments && rm -rf experiments/janus1f && cp -r repo/trillium/janus1f experiments/janus1f && cd experiments/janus1f
ICX4_CLUSTER=fir STAGE=pilot EPOCHS=150 LPDA=anatomy JANUS0=$SCRATCH/icx4/nnunet_results/Dataset715_ICX4 JANUS1F_WORK=$SCRATCH/janus1f_pilot CHAIN=1 ./janus1f
grep SBATCH $SCRATCH/janus1f_pilot/job.sh   # --gpus-per-node=h100:1 --cpus-per-task=12 --mem=280G --time=23:50:00 --account=def-aso22
./janus1f status $SCRATCH/janus1f_pilot     # s/epoch, expect ~190-200
```

**Check the printout:**
- `split: train 580 / pilot-val 40 / locked 100 not opened / sealed 0`;
- `classes: 12 + background`;
- `head inheritance: LAD->D1,D2,D3 (k=4) LCx->OM1,OM2,Ramus (k=4) RCA->PDA,PLB (k=3)`;
- `step-0 check: territory probability = Janus 0 (max abs diff < 1e-4)`.

**Send back:** `results/` (`progress.png`, the pseudo-Dice log per class, and the 40-case pilot-val branch metrics).

**Gates** (read by anyone, from the log):
- **P1-a.** By epoch 100, every one of the eight branch classes has pseudo-Dice > 0 on the pilot val. **Fail →** the
  inheritance does not unlock the branches. Stop. Round 2 decides between class weights and segment-then-label.
- **P1-b.** At epoch 150, D1, OM1, PDA and PLB (each present in > 90 % of cases) have pseudo-Dice ≥ 0.5, and the
  four vessels' collapsed pseudo-Dice is within 0.02 of epoch 0's. **Fail on branches only →** J1 runs with class
  weights (4×). **Fail on vessels →** J1 runs at LR 1e-3 (A17b).

### Job J1: Janus 1-F₀, 500 epochs on the 620. About 32 GPU-h in two chained 23:50 jobs (26.7 training + 1.5 preprocessing + 3–4 predicting all 1000 and scoring)

```sh
cd $SCRATCH/asclepius/experiments/janus1f
ICX4_CLUSTER=fir STAGE=a EPOCHS=500 LPDA=anatomy JANUS0=$SCRATCH/icx4/nnunet_results/Dataset715_ICX4 JANUS1F_WORK=$SCRATCH/janus1f_a CHAIN=2 ./janus1f
# add CE_WEIGHTS=branch4 if P1-b failed on branches; add LR=1e-3 if it failed on vessels
./janus1f status $SCRATCH/janus1f_a
# when DONE:
./janus1f collect $SCRATCH/janus1f_a        # results/: R1 (paired vs Janus 0), R2 per class, hybrid R2, Dice and centreline rows
```

**Check the printout:**
- `split: train 620 / fold-0 val locked 100 / sealed 0`;
- `checkpoint: final (best is never used)`;
- the A1c hash line;
- `locked 100 = val 80 + 20 open-36 [c0068 ... c0996]`.

**Send back on #303:** `results/` (SUMMARY.md, results.json, per-case JSON). The reader applies §6 verbatim.

**Cost.**

| Job | GPU-h |
|---|---|
| P1 | about 10 |
| J1 | about 32 |
| Stage-B pilot P2 (100 epochs) | about 7, when §7's counts are met |
| J2 (1-F₁, 250 epochs) | about 15, when §7's counts are met |
| **Now** | **about 42** |
| **Total** | **about 64** |

Ceiling if every chunk runs long (12-core loader; Foxtrot's R10 note): 1.5×.

## 10. What would change the plan

| Result | Then |
|---|---|
| P1-a fails | Head inheritance does not unlock branches. Round 2 chooses between (i) class-weighted CE from the inherited start and (ii) segment-then-label: a graph labeller on Janus 0's skeleton, trained on the 620's names (CPU-trainable) |
| R1 fails, R2 passes | The hybrid is delivered. Round 2 asks why the vessels moved (expect LCx: a third of it is side branch) |
| R2 fails on one class only (for example OM2, 39 % prevalence) | That class is merged into its parent for 1-F₀ and re-tried at 1-F₁ with more data |
| D3 naming < 0.5 while D1/D2 pass | The proximal-most Other rule is wrong too often (a traced Other is a D4 behind an untraced D3). D3 moves to the untraced set (pool reads only) |
| Extended reads stay rare (toggle off) | Stage B never starts. 1-F stays at 12 classes. Report the six as "no data" to the lead; options are the lead's: turn the toggle on by default, or a targeted extended pass (changes D23's use of annotator time) |
| An untraced class's inter-read agreement < 0.6 | That class is not trained (§7). Report: the class is not reliably readable at CCTA resolution |
| Lead picks L1 (b) | One config switch (`LPDA=lcx`). PDA/PLB are right-only. R2's PDA count drops by about the left-dominant share |
| 1-L's recipe beats Janus 0 | The hybrid's segmenter becomes 1-L, and R1's comparator becomes 1-L. Nothing else changes |

## 11. External evidence (each opened at source, 2026-11-11)

| Source | What it says (table/figure) | Use here |
|---|---|---|
| Bransby et al., ImageCAS-X, arXiv:2608.30404 (HTML v1) | Annotation protocol: "Septal perforators, acute marginals and nodal arteries were not traced"; side branches not traced where distal diameter < 1 mm; "Other" = D3/D4/OM3/OM4 if as large as the first/second branch or > 1.8 mm proximally. Table 1 inter-observer DSC per segment (D1 79.9 … L-PLA 70.9) | §0.1, §1, §2, §5. The central fact of this plan |
| Shi, Xiao, Chen, Zhou, Med Image Anal 70:101979 (2021), DOI 10.1016/j.media.2021.101979, arXiv:2007.03868 | Marginal loss: the background of a partially labelled image merges unlabelled organs, so its probability is the marginal sum. Table 3: joint training on 5 partially labelled sets with marginal CE+Dice 0.921 vs 0.874 on the fully labelled set alone; + exclusion loss 0.931 | §3.2 CE term |
| Fidon et al., MICCAI 2021, arXiv:2107.03846, DOI 10.1007/978-3-030-87196-3_60 | Axiomatic label-set losses; Table 2: leaf-Dice vs marginal Dice on scarce tissues: CC 62.0 vs 11.1, DGM 71.4 vs 37.8, BS 61.5 vs 39.4 | §3.2 Dice term; why marginal Dice alone is unsafe for scarce classes |
| Ulrich et al., MultiTalent, MICCAI 2023, arXiv:2303.14444, §2.2 | Per-class sigmoid heads; loss computed only for classes annotated in each dataset; summed over classes | §3.2, the alternative not chosen, and why |
| Yang et al., CPR-GCN, CVPR 2020, arXiv:2003.08560, Table 3 | 511 subjects, two experts, 11 classes including S; mean F1 0.955; S 0.964; D 0.909, OM 0.914, RI 0.909; centrelines from an automatic tracker | §4.1, §6 R2 reference point |
| Li et al., arXiv:2212.00386, Table 1 and §4 | 141 CCTA, 13 classes including L-PDA, L-PLB; weighted F1 0.805; low performance on R, L-PDA, R-PDA, attributed to few samples (L-PDA 39 branches) | §2.2 (left-sided classes exist as names), §7 |
| Gebhard et al., CONFIRM, Eur Heart J Cardiovasc Imaging 16(8):853–862 (2015), DOI 10.1093/ehjci/jeu314 | 6382 CCTA patients: right dominance 91 %, left 9 % (Results; Table 2) | §2.2, the size of the L1 question |
| Vikse et al., PLoS One 11(2):e0148331 (2016), DOI 10.1371/journal.pone.0148331, Table 3 | SA nodal artery origin, pooled: RCA 68.0 %, LCx 22.1 %, both 2.0 % | §2.2, SN by anatomy; §3.2 band includes the proximal LCx |
| Gonzalez, Sakas, Mukhopadhyay, arXiv:2010.11008, Table II | Joint vs sequential training, prostate: 0.77 vs 0.60 Dice | §3.2 replay in stage B |

Not used:
- Hampe et al. (SPIE MI 2021, GAT segment labelling). I could not open a DOI or full text.
- The conus "separate ostium in 30–50 %" figure. Textbook and wiki sources only; stated as unsourced (§7).

## 12. Questions for the lead (not assumed)

- **L1. Left-sided PDA/PLB (#303's question).**
  - Recommended: (a), by anatomy. L-PDA → PDA, L-PLA → PLB, and SN is SN whatever its origin.
  - The **four-class collapse goes by origin** (D25 unchanged). That means a one-line change to #310's collapse, which
    today sends PDA/PLB/SN always to RCA.
  - Default until answered: (a) for 1-F; #310 untouched.
- **L2. Unlisted branches** (D4+, OM3+, S4+, AV-nodal, atrial, other RCA branches): parent's class.
  - This matches #280's collapse; D44 does not say it.
  - The SegQueue instructions should say it too.
- **L3. Parent–child overlaps in an extended read** (a branch drawn as S1 but left in the LAD's D26 copy): train as the
  child. This extends D40 for 1-F only. Default until answered: D40 literally (ignore).
- **L4. The extended-class toggle default** (#310: off). Stage B's start depends only on how many reads use it (§7).
  - Not a recommendation to change it. A statement that 1-F's six untraced classes wait on it.
- **L5. Confirm the locked-20 id form** (`cNNNN` in the hash), so 1-L and 1-F lock the same 100.

## 13. Risks

| Risk | Detection | Response |
|---|---|---|
| The band (15 mm) lets the model paint untraced classes on veins near the LAD/RCA | R4 (i) cannot see veins; pool reads can. Model-vs-read precision for each untraced class on D35 | Shrink the band; add Shi's exclusion term against the read's background |
| The D3 rule mislabels a D4 as D3 | D3 naming in R2 vs D1/D2 | §10 row 4 |
| Extended reads draw septals into the LAD (toggle on, branch not moved out) | Reads with S-classes empty but LAD centreline > ImageCAS-X's typical length | Label sets (§3.2) treat such a LAD as {LAD, S1–S3}; nothing is lost |
| **Cross-track effect, for 1-L (reported, not decided here):** 4-class pool reads include septals in the LAD (the SegQueue instruction says "every diagonal and septal"); ImageCAS-X does not | 1-L's model-vs-read LAD precision/recall on D35 | For #302: a model trained on ImageCAS-X will look short in the LAD against pool reads, by the septals' length. This is the same extent effect as v11's seed-anchoring note, in the other direction |
| Locked-100 ids differ between tracks | `split.py` vs #302's launcher | L5; the launcher refuses on mismatch |
