---
tags: [plans, candidate, janus1-F, track-1F, round1, fir, D44, D45, locked100, partial-labels, label-sets, warm-start, parent-copy, branches]
author: Delta
track: 1-F
round: 1
version: 1
updated: 2026-11-12
issue: christianGRogers/Asclepius#303
---

# Delta v1 (Janus 1-F): grow 1-F out of Janus 0 by copying each parent's head to its branches, train the 12 classes ImageCAS-X traced, and add the six it never traced through label sets once extended reads exist

## 0. Position, and what is new

**Start from scratch** (this is round 1 of a new track), but on settled ground: Janus 0's recipe, A1c's tF1, D45's split
and 1-L's Round 1 ruling (L-A1 split file, L-A2 warm-start mechanics), which this plan reuses wherever 1-F does not
have to differ.

**New evidence this round** (CPU, code in `experiments/Delta/j1f_r1/`, no sealed case downloaded or opened):
[[Delta - Janus 1-F, ImageCAS-X traced 12 of 1-F's 18 classes, numbers its branches in strict order, and leaves the other six as background]].

**Independence.** I did not read Bridge v1 or Crucible v1 of this track (merged on `dev` before this PR). One note's
*file name* showed in a directory listing after my finding 1 was in: Crucible reports the same fact (ImageCAS-X traced
no septal, nodal or acute-marginal branch). I did not open it. Two independent arrivals at it are worth the judge's
notice, since everything below depends on it.

## 1. The findings that shape the plan

1. **ImageCAS-X never traced six of 1-F's classes, and their voxels are background there, not hidden in a parent.**
   ImageCAS-X's protocol: "Septal perforators, acute marginals and nodal arteries were not traced" (arXiv:2608.30404,
   Suppl. B). Measured: of 620 training cases, the LAD class has an unnamed side branch ≥ 5 mm in **4** and the RCA class
   in **2**; none ≥ 10 mm in the RCA (so the conus was not traced either). ImageCAS-X's LAD and RCA are clean; its
   **background** is the merged label {bg, S1, S2, S3, SN, Conus, RMA}.
2. **ImageCAS-X numbers branches in strict order along the parent, so D3 comes out of "Other" by rule.** D1 attaches
   before D2 in **359 of 359** cases; OM1 before OM2 in **228 of 228**; every LAD-side "Other" piece after D2 in
   **47 of 47**. The first LAD-side "Other" piece is D3 (47 training cases, 7 locked); a second is D4 → LAD; LCx-side
   pieces are OM3/OM4 → LCx. D3 is still partial: ImageCAS-X traced it only when ≥ 1.8 mm or as large as D1/D2.
3. **What can be trained and gated now.** Training cases: D1 611, D2 359, OM1 540, OM2 229, Ramus 149, PDA 572,
   PLB 565, D3 47; left PDA 38 and left PLA 54 (Q1). Locked-100 cases with ≥ 30 references: **D1 98, D2 64, OM1 84,
   OM2 40, PDA 96, PLB 96**. Ramus (24), D3 (7) and the left PDA/PLA (4, 12) fall below. Traced branches have median
   radius 0.61–0.67 mm (≈ 2.5 voxels across at 0.5 mm), at ImageCAS-X's 1 mm tracing floor.
4. **A 13-class head can start as Janus 0.** Copying each parent's output row to its branches and lowering the
   territory's biases by log(size) (MiB, Eq. 8–9) makes the collapsed 13-class softmax equal Janus 0's to 1.6e-15,
   with children tied to the parent (`parent_copy.py`, self-test PASS). The stage-1 labels collapse to D25's four
   classes on every voxel but 40 "Other" voxels in 2 of 620 training cases (of 20.9 M tree voxels), and exactly on the
   locked 100 (the note's result 4).
5. **The project's 14-class run failed in the way parent copy prevents.** icx14, from scratch: all ten side-branch
   classes at pseudo-Dice 0 for 446 epochs while D1 was in 631 of 640 cases; one (R-PLA) appeared at ≈ epoch 440 in the
   rerun; cancelled at ≈ 455 (D25). The record's diagnosis: the parent wins the cross-entropy early because a branch is
   locally the same as its parent.

## 2. The plan in one paragraph

**Stage 1 (now, ImageCAS-X only, ≈ 31 Fir GPU-h):** train **J1F-A**, a 13-class nnU-Net (bg, LM, LAD, LCx, RCA, D1, D2,
D3, OM1, OM2, Ramus, PDA, PLB) on the D45 620, **warm from Janus 0 with parent-copied output heads**, Janus 0's plans,
500 epochs. Read it on the locked 100 two ways: **F** (its own output) and **T** (Janus 0's foreground and four
territories, with 1-F choosing only the branch inside each territory: a segment-then-label system whose labeller is
1-F). Ship F if its four vessels, collapsed, are non-inferior to Janus 0 (Δ macro tF1 lower bound > −0.02, no class
< −0.03, FP ≤ 1) and the six gated branch classes pass detection (presence agreement ≥ ImageCAS-X's inter-observer
− 0.05) and naming (≥ 0.85); else ship T, whose vessels are Janus 0's by construction. **Stage 2 (when reads allow):**
add S1–S3, SN, Conus and RMA by parent copy from the shipped model and train on ImageCAS-X + pool reads with a
**label-set (marginal) loss**: every voxel's label is the set of classes it may be, so ImageCAS-X's background is
{bg + the six}, a 4-class pool LAD is {LAD + its branches}, and D40's overlap ignore is the full set. No read is
thrown away.

### The classes, their sources and their stage

| 1-F class | ImageCAS-X source | Training cases (620) | Stage | Scored on |
|---|---|---|---|---|
| LM, LAD, LCx, RCA | same | 611–620 | 1 | locked 100 (A1c tF1, collapsed) |
| D1, D2, OM1, OM2 | same | 611 / 359 / 540 / 229 | 1 | locked 100, gated |
| PDA, PLB | R-PDA, R-PLA (+ L-PDA/L-PLA if Q1 = b) | 572 / 565 | 1 | locked 100, gated |
| Ramus | IM | 149 | 1 | locked 100, report (24 cases) |
| D3 | first LAD-side "Other" | 47 | 1 | locked 100, report (7 cases) |
| S1, S2, S3, SN, Conus, RMA | **none (not traced)** | 0 | 2 | pool extended reads (D35), §6.3 |


## 3. Partial labels: one softmax, one loss, a label set per source

**Every voxel of every training read carries a *set* of classes it may be, and the loss sums the softmax over that
set** (marginal / label-set loss: Shi et al. 2021 §3.2; Fidon et al. 2021). A singleton set is an ordinary label;
the full set is D40's ignore. This one mechanism covers all three label sources 1-F will see, each with its own,
documented semantics:

| Source | A voxel labelled… | …means the set |
|---|---|---|
| ImageCAS-X (620) | LM, LAD, LCx, RCA, D1, D2, OM1, OM2, IM, R-PDA, R-PLA | that class alone (mapped as §2) |
| | L-PDA / L-PLA | {LCx} (Q1 default a) or {PDA} / {PLB} (option b) |
| | Other, LAD side, first along the LAD | {D3} |
| | Other, LAD side, later | {LAD} (D44 has no D4) |
| | Other, LCx side | {LCx} |
| | background | **stage 1:** {bg}. **Stage 2:** {bg, S1, S2, S3, SN, Conus, RMA}: ImageCAS-X did not trace them, so its background is a merged label (§1 finding 1) |
| Pool, 4-class read (D44 toggle off) | LAD | {LAD, D1, D2, D3, S1, S2, S3} |
| | LCx | {LCx, OM1, OM2, Ramus} (+ {PDA, PLB} under Q1 option b, where a left PDA is PDA) |
| | RCA | {RCA, SN, Conus, RMA, PDA, PLB} |
| | LM, background | itself |
| Pool, extended read (toggle on) | any one class | that class |
| | a parent class | the parent alone (the annotator moved the branches out) |
| any read | two or more classes (D39 overlap) | **the full set** (= D40's ignore; D40 stands) |

Two things follow and are the reason for this choice over the alternatives:

- **No read is thrown away.** A 4-class pool read still teaches the territory boundary and the extent of every branch
  (the set excludes the other three territories and background), while D40-style ignore would discard the whole
  vessel. This matters because D44 makes extended classes optional and most early reads will be 4-class.
- **Stage 1 needs none of it.** ImageCAS-X's 12 traced classes are singletons, so J1F-A is a plain nnU-Net loss on 13
  classes. The label-set trainer is needed only for stage 2 (F4), and is built and CPU-tested before it (§11).

**Why not the alternatives:**
- *nnU-Net's ignore label for ImageCAS-X's background* (Gotkowski et al.) would throw away the background
  everywhere in 620 cases. The set {bg, S1–S3, SN, Conus, RMA} keeps the bg-vs-vessel signal for every other class.
- *Per-class sigmoid heads with per-dataset loss masks* (MultiTalent §2.2) handle missing classes but not a coarser
  class (a 4-class LAD that contains D1). They would also drop the softmax's mutual exclusion, which D40 assumes. Kept
  as the fallback in §12.
- *Exclusion loss* (Shi §3.3) is implicit in a softmax.

## 4. Segment-then-label, or one network? One network, born from Janus 0, read inside Janus 0's territories

**The choice: one 13-class nnU-Net (later 19), warm-started from Janus 0 with parent-copied heads (§5), so that a
segment-then-label system is its starting point rather than its rival.** At step 0, J1F-A collapsed to four classes
*is* Janus 0 (self-test, §1 finding 4); training only has to learn which part of each territory is which branch.

**What the project's 14-class attempt teaches** (icx14, D9/D10, reversed by D25):
1. **From scratch, side branches stay at zero for hundreds of epochs.** All ten side-branch classes had pseudo-Dice
   exactly 0 in every one of 446 epochs, although D1 was in 631 of 640 training cases; the main vessels unlocked by
   epoch 50–200 ([[icx14 - interim check after job 1 (446 epochs), side branches not yet learned]]). The restarted
   run reached R-PLA 0.73 from about epoch 440, with the other nine still at 0 at epoch 455 ([[icx14 - job 2
   restarted from scratch (resume bug), R-PLA appears at epoch 440]]). The cause recorded there: a side branch is
   locally the same as its parent, and the parent wins the cross-entropy early. **Parent-copy attacks exactly
   this**: children start tied with the parent, so the gradient's only job is to break the tie.
2. **It was never finished.** icx14 was cancelled at about 455 epochs (D25), so "14 classes do not work" is not
   shown. Its planned fallbacks (class weights × 4, then a two-stage prelabel) were never run. J1F-S (F3) is that
   run, finished, and is only needed if J1F-A fails.
3. **Resume must accept either checkpoint file** (the icx14 bug cost 23 GPU-h). `trillium/j1f` inherits icx4's
   `job_body.sh` fix.
4. **Trunk Dice is not territory Dice.** icx14's LM/LAD/LCx/RCA numbers exclude side branches. 1-F's vessel guard
   must collapse 1-F to four classes before comparing with Janus 0 (§7 V1), not compare trunks.

**Why not a graph namer on Janus 0's tree, as the primary:**
- Naming on *automatic* trees loses much of what naming on *reference* trees achieves: Hampe et al. 2024, mean label F1
  0.74 vs 0.91 (Tables 3, 8). CPR-GCN's 0.955 is on reference centrelines. Cao 2017's rule model: 89.2 % / 83.6 % of
  segments (right / left dominant), against expert agreement of 97.6 / 87.6 %.
- D44's classes are voxel classes, read by Dice and tF1 per class. A centreline namer still needs a voxel-painting
  step, which is where gaps and crossings break it ([[Bridge - Stage-1 gaps are what break naming, and bridging fixes most of it]]).
- D3 and the septals are defined by **order along the parent and by direction** (septals dive into the septum,
  diagonals run on the epicardium). Finding 2 shows that the order is how ImageCAS-X numbers, and an image network
  sees direction; a graph rule needs both hand-coded.

**But keep its guarantee.** §6.2's **territory-constrained reading (T)** takes Janus 0's foreground and four
classes as given and lets 1-F choose only *within* each territory (LAD territory → argmax over {LAD, D1, D2, D3};
LCx → {LCx, OM1, OM2, Ramus}; RCA → {RCA, PDA, PLB}). T is a segment-then-label system whose labeller is 1-F.
Its four vessels are Janus 0's **by construction** (Δ = 0), so a better 4-class model (Janus 1-L) can later be
swapped in under the same 1-F labeller, with no new 1-F training. The free reading (F) is 1-F's own output. Both are
scored; §7 decides which ships.

## 5. Architecture and recipe (stage 1, J1F-A)

- **nnU-Net v2, Janus 0's exact plans** (`nnUNetResEncUNetPlans_60G_iso05`: ResEnc, 0.5 mm isotropic, patch 256³,
  batch 2, mirroring off, nnU-Net's CT normalisation). **Dataset 719** (718 is 1-L's). Plans moved byte-identical from
  715 with `nnUNetv2_move_plans_between_datasets`, then `nnUNetv2_preprocess`; no fingerprint, no `plan_experiment`
  (1-L's L-A2, which corrected exactly this).
- **The split:** the file of record `configs/janus1/split-2026-11.json` and its guard (#306 §1, L-A1); my own
  recomputation (`split_d45.py`) matches both list pins.
- **Labels:** 13 classes by `j1f_labels.py` (§2), `--left-pda lcx` until Q1.
- **Warm start:** Janus 0's `checkpoint_final.pth` (#43) through A17a's loader (`src/segtrain/nnunet_ext/
  finetune_load.py`), extended with one option: every non-head tensor strict and bitwise as now; the 13-channel
  `seg_layers` (all deep-supervision outputs) by parent copy (`parent_copy.py`: copy the parent's row; lower each
  territory's biases by log of its size; MiB Eq. 8–9), then the collapse identity checked on a random batch before
  epoch 0. `SEGTRAIN_CT_WINDOW=off`, as 1-L (L-A2).
- **Schedule:** 500 epochs × 250 iterations, SGD, 2500-iteration linear warm-up to **1e-2**, then poly (1-L's L-A2
  schedule, so the two tracks differ only in what they must). 500, not 250: the branches are new targets on thin structures, which Atlas
  found need the full schedule ([[Atlas - Validation pseudo-Dice of the four main vessels flattens by epoch 100-200,
  but thin structures need the full schedule]]); not 1000, because the territories are inherited.
- **Loss:** nnU-Net's CE + Dice, unweighted. Class weights are F3's lever, not J1F-A's: parent-copy is the
  hypothesis under test, and stacking a second change would hide which one worked.
- **Fold 0 validation = the locked 100**, so nnU-Net's per-class pseudo-Dice is logged on them during training;
  nothing about the run is chosen from those curves (one checkpoint: final).
- **Train = 620.** No pool reads in stage 1 (none are extended yet, and the 4-class ones need the label-set trainer).

## 6. Metrics

### 6.1 The four vessels (decisive for V1–V3)
1-F's output collapsed to four (D25: D1–D3 → LAD; OM1, OM2, Ramus → LCx; PDA, PLB → RCA; under Q1's default (a) a
left PDA/PLB is LCx-labelled, so it collapses to LCx as in Janus 0), scored with Janus 0's own A1c scorer
(`trillium/icx4/lib/tf1_score.py`, decisive tF1 at 1.5 mm, TotalSegmentator aortas; A1a/A1b exclusions) on the locked
100, **paired with Janus 0's prediction of the same case**: 1-L's Job J0 re-predicts Janus 0 on the locked 100 and makes
their aortas (#306 §2); 1-F reuses both, so neither is paid twice. FP components per case (A15) reported.

### 6.2 Branches (the 12 traced classes; both readings T and F)
For each branch class c and each locked case, with the reference "present" if its centreline is ≥ 5 mm:
- **Presence agreement** (ImageCAS-X Table 1's own measure): the share of cases where reference and prediction
  both have c or both lack it, plus sensitivity and precision of "c present". This is the **detection** metric.
- **Naming accuracy:** of the reference centreline points of c that the prediction *found* (any predicted tree voxel
  within 1.5 mm), the share whose nearest predicted voxel is labelled c. Reported with the **confusion among
  siblings** (D1/D2/D3/LAD, OM1/OM2/Ramus/LCx, PDA/PLB/RCA). Detection and naming are kept apart so a missed branch
  and a misnamed branch are never the same number.
- **Branch tF1 at 1.5 mm:** A1c's tF1 on class c alone, rooted where the reference branch meets its parent (needs the
  per-class root option, §11).
- **Dice per class:** report only (A28's rule carries), beside ImageCAS-X Table 1's inter-observer DSC.

### 6.3 Classes ImageCAS-X never traced (S1–S3, SN, Conus, RMA)
- **Never scored on ImageCAS-X**: their absence there is untraced, not absent (§1 finding 1). A prediction of them
  on an ImageCAS-X case is neither TP nor FP; it is excluded from the background in every ImageCAS-X metric.
- **Scored only against extended pool reads**, on the D35 decision set (A33), against the inter-read agreement of
  the same metric (D6's form): presence agreement, naming accuracy and branch tF1, per class, with n and a CI.
- **Reported, deciding nothing, below 30 cases** with the class in at least one read; until then the class is
  folded into its parent in anything that leaves the project (§8).

## 7. The pre-registered decision on the locked 100 (stage 1)

Fixed before J1F-A starts. Janus 0 is the comparator (its locked-100 predictions come from 1-L's J0). The locked 100 is
never trained on, and no hyperparameter is chosen on it.

**Vessel gate (reading F; T passes it by construction):**
- **V1:** Δ macro decisive tF1 (F collapsed − Janus 0), case-bootstrap 95 % CI lower bound **> −0.02**.
- **V2:** no class's Δ below **−0.03** (point estimate).
- **V3:** FP components per case ≤ 1 (A15).

These mirror A38's G2 for Janus 1 (Round 10). Power: Janus 0's paired per-case SD(Δ) between two runs was 0.038–0.041
on val 80, pessimistically 0.067–0.075 ([[Atlas - Run-to-run noise in both measured pairs is per case, so a
35-patient decision set resolves about 0.02-0.035 tF1 and A22's 0.013 overstates it]]); on 100 cases the CI half-width
is 0.008–0.015 (Foxtrot's 1-L note puts the smallest gain the same 100 resolves at 0.011–0.013), so a model as good as
Janus 0 clears −0.02, and one 0.03 worse fails.

**Branch gate (on whichever reading ships):** for each branch class with **≥ 30 locked cases** where the reference
has it (§2's table lists them):
- **B1, detection:** presence agreement ≥ ImageCAS-X's inter-observer agreement for that segment **− 0.05** (D6's
  margin). From Table 1: **D1 ≥ 0.919, D2 ≥ 0.844, OM1 ≥ 0.894, OM2 ≥ 0.825, PDA ≥ 0.938 (R-PDA), PLB ≥ 0.912 (R-PLA)**.
  Table 1 is on ImageCAS-X's test 160 (our sealed 80 among them) and between two of its analysts, so it is a reference
  level, not a paired comparison.
- **B2, naming:** naming accuracy ≥ **0.85**. (Opinion, anchored on Cao 2017's 83.6–89.2 % segment agreement for a
  rule namer and 87.6–97.6 % between experts.)
- **B3:** report branch tF1 and Dice beside Table 1; no threshold in stage 1.
Classes with < 30 locked cases (measured: Ramus 24, D3 7, left PDA 4, left PLA 12; §1 finding 3) are reported with
their n and CI and decide nothing.

**Reading:**
| Outcome | Then |
|---|---|
| V1–V3 pass and B1–B2 pass for every gated class, in F | **Ship F** as the 1-F stage-1 model (the next Janus number, D34) |
| F fails V1–V3, T passes B1–B2 | **Ship T** (Janus 0's vessels, 1-F's names). Report F's vessel loss; round 2 asks why |
| B1 or B2 fails in a class, in both T and F | That class is folded into its parent in the shipped model; if ≥ half the gated classes fail, run **F3 (J1F-S)** and repeat this table with it |
| B fails broadly and F3 also fails | Segment-then-label with a graph namer becomes round 2's primary (§12) |

D35 / pool reads play no part in stage 1 (no extended reads exist). The seal (D27) is not read.

## 8. Reads per class before a class is trained or reported

| Use | Threshold | Basis |
|---|---|---|
| A stage-2 class enters **training** | ≥ **40 trainable pool patients** with the class drawn in ≥ 1 extended read, from ≥ 3 sources (D35 set, seal and reserve excluded) | Opinion. The smallest ImageCAS-X classes J1F-A trains are D3 (47 training cases) and Ramus (149) (§1 finding 3); F2 will show how they fare, which is the first data on this question. A learning-curve job (thin a traced class, e.g. OM2, to 20 / 40 / 80 training cases and re-run stage 1's fine-tune) is costed for round 2 at ≈ 3 × 15 GPU-h, not proposed now |
| A class is **reported** | ≥ 10 decision-set cases with the class in ≥ 1 read, with n and CI | Below 10 a presence rate's 95 % CI is ± 0.19 (p = 0.9) to ± 0.31 (p = 0.5) |
| A class **decides** anything or leaves the project un-folded | ≥ 30 decision-set (or locked) cases | Presence at p = 0.9 on 30 cases: 95 % CI ± 0.11; at n = 30 the per-class tF1 CI is about ± 0.04 at Janus 0's spread |

D35 has 35 patients, so for SN, Conus and RMA (present in a fraction of hearts) the 30-case line may never be reached
on D35 alone. Round 2 must settle whether locked pool cases beyond D35 are needed for the branch classes; that touches
D35's size and is for the lead (Q4).

## 9. Fir jobs (the lead runs them; `def-aso22`; 1 × H100 80 GB, 12 cores, 280 G, charged to `def-aso22_gpu`)

**Costs** come from Janus 0 on Fir: about 192 s per epoch at 256³, batch 2 (23.2 + 23.3 + 7.7 h for 1000 epochs;
[[icx4 - Results]]). A 13-channel head adds softmax and Dice over 8 more channels at the outputs only; I budget
**+10 %** (≈ 210 s per epoch). An estimate, not a measurement: J1F-A's first chunk logs the real figure, and the chain
length follows it (the chain stops itself when training is done, so a spare link costs a minute).

| # | Job | Waits on | GPU-h |
|---|---|---|---|
| F0 | Login node: Dataset 719 from the 620 + locked 100 (labels by `j1f_labels.py`, `--left-pda lcx` until Q1); the split guard; Janus 0's plans moved in; check that every 719 label collapses to `territory.py`'s four classes (§1 finding 4) | `trillium/janus1f` (§11) and #306 (split file, guard) | 0 |
| — | **Reused, not run again:** 1-L's **J0** (#306 §2): Janus 0 re-predicted on the locked 100, their TotalSegmentator aortas, the identity check | 1-L's J0 | 0 here |
| F1 | **J1F-A**: stage 1 (§5): warm from Janus 0 with parent-copied heads, 500 epochs, fold 0 val = locked 100. Preprocessing in the first link | F0, J0 | ≈ 30 (2 links of 23:50) |
| F2 | Last link of F1: predict the locked 100 (free reading F; and T, constrained by J0's Janus 0 prediction), score (§6) and print §7's table | F1 | ≈ 1 |
| F3 | *Conditional* — **J1F-S**: icx14's plan finished: from scratch, 1000 epochs, 13 classes, CE weight 4 on the 8 branch classes | §7 row 3 (≥ half the gated classes fail B1/B2 in T and F) | ≈ 58 |
| F4 | *Later* — **J1F-2**: stage 2: warm from the shipped stage-1 model, six heads parent-copied, label-set loss on ImageCAS-X + pool reads, 250 epochs | §8's read thresholds | ≈ 15 |

**Stage 1 costs about 31 GPU-h** (F1 + F2); 89 if F3 fires. Nothing else is new: Janus 0's locked-100 predictions and
aortas come from 1-L's J0.

**Commands** (exact once `trillium/janus1f` exists; it is #306's `trillium/janus1l` with the changes in §11, so its
shape is the same; Fir's job header is icx4's, `--gpus-per-node=h100:1 --cpus-per-task=12 --mem=280G`):

```sh
# F0 + F1 + F2 (login node, in tmux)
module load StdEnv/2023 python/3.11.5
cd $SCRATCH/asclepius && git -C repo pull --ff-only
rm -rf experiments/janus1f && cp -r repo/trillium/janus1f experiments/janus1f
cd experiments/janus1f
JANUS1F_CLUSTER=fir JANUS1F_RUN=a CHAIN=2 JANUS1F_EPOCHS=500 JANUS1F_LEFT_PDA=lcx \
  JANUS1F_INIT=$SCRATCH/icx4/nnunet_results/Dataset715_ICX4/nnUNetTrainerICX4__nnUNetResEncUNetPlans_60G_iso05__3d_fullres/fold_0/checkpoint_final.pth \
  JANUS1F_J0=$SCRATCH/janus1l/j0 \
  ./janus1f
./janus1f status        # epoch, s/epoch, per-class pseudo-Dice of the 13 classes
./janus1f collect       # small results -> ./results/

# Dry run first (no GPU; checks split, plans, labels, the parent-copy identity on one batch):
JANUS1F_DRYRUN=1 JANUS1F_CLUSTER=fir JANUS1F_RUN=a JANUS1F_LEFT_PDA=lcx JANUS1F_INIT=... JANUS1F_J0=... ./janus1f

# F3, only if §7 row 3 says so:
JANUS1F_CLUSTER=fir JANUS1F_RUN=s CHAIN=3 JANUS1F_EPOCHS=1000 JANUS1F_INIT=none JANUS1F_CE_WEIGHTS=branches4 \
  JANUS1F_LEFT_PDA=lcx JANUS1F_J0=$SCRATCH/janus1l/j0 ./janus1f
```

`$SCRATCH/janus1l/j0` stands for wherever #306's launcher writes J0's outputs; the launcher refuses if J0's identity
check did not pass. **The launcher also refuses:**
- a sealed case (80 test, 20 quality-0) or a locked-100 case in training (the #306 guard, file and list pins);
- a Janus 0 checkpoint whose sha256 differs from the one J0 logged;
- a plans file that is not byte-identical to 715's;
- `JANUS1F_LEFT_PDA` unset (Q1);
- a parent-copy identity error above 1e-5 on the first batch (the trainer checks it before epoch 0).

**What to send back** (post on #303): `results/SUMMARY.md` (§7's table filled in), `results/score_locked100.json`,
`timings.json`, the last 30 lines of `train.log`, and the dry run's output.

## 10. Questions for the lead

- **Q1 (D44 / D25): where does a left-sided PDA or PLB go?** ImageCAS-X splits them by origin (R-PDA/L-PDA,
  R-PLA/L-PLA), as do SCCT's 18-segment model and Cao 2017's left-dominant model (Table 1: LPDA and LPLB are LCx side
  branches). D44 lists one PDA and one PLB, under the RCA; #280's collapse sends PDA → RCA always, which contradicts
  D25 (left PDA → LCx) in left-dominant hearts.
  - **(a) Recommended:** 1-F's PDA and PLB mean **RCA-origin** branches; a left PDA/PLB is **LCx** (D25, D1). Then 1-F's
    four-class collapse equals Janus 0's labels exactly, the vessel gate compares like with like, and #280's PDA → RCA
    collapse is correct by definition. Annotators are told to leave a left PDA/PLB in LCx. Cost: 1-F never names a left
    PDA (38 training cases, 4 locked: it could not be gated anyway).
  - **(b)** PDA/PLB by **groove**, any origin: L-PDA → PDA, L-PLA → PLB. Then #280's collapse must look at origin, and
    the vessel comparison with Janus 0 needs a per-case origin rule. Human agreement is worst exactly here (Cao 2017:
    87.6 % between experts on left-dominant trees vs 97.6 % right).
  - The launcher refuses until `JANUS1F_LEFT_PDA` is set; F0 is the only job that changes with the answer.
- **Q2 (D22, read only): 1-F does not need ImageCAS-X re-annotated.** Stage 2 learns the six untraced classes from
  pool reads through label sets. Re-annotating the 620 for septals would be faster but is D22's to change; I do not
  ask for it.
- **Q3 (#280): extended reads must say which classes the annotator considered.** A pool read with the toggle on but
  no septal drawn could mean "no septal" or "did not look". Stage 2's label sets need to know which. The cheapest form:
  the toggle state (on/off) recorded per read, which #280's server already stores as the class stack. Confirm that a
  toggled-on read means "every extended class was considered"; otherwise each extended class needs a per-read
  "checked" flag.
- **Q4 (D35): the branch classes need more decision cases than D35's 35.** SN, Conus and RMA are present in only part
  of hearts, so a 30-case line may never be met on D35 (§8). Round 2 will size this; any growth of a held-out pool set
  is the lead's.

## 11. What must ship (role:swe; filed only if the judge adopts it, so that five advocates do not file five)

1. **`finetune_load` parent-copy option** (`src/segtrain/nnunet_ext/finetune_load.py`): when the target's output
   classes extend the source's by a pinned parent map (`configs/janus1/j1f_parents.json`), load every non-head tensor
   strictly and bitwise as now, build each `seg_layers` head by `parent_copy.py`'s rule, and refuse unless the
   collapse identity holds on a random batch (< 1e-5). CPU test with a tiny network, as the existing tests.
2. **`trillium/janus1f/janus1f`**, from #306's `janus1l` with: Fir's header; Dataset 719 with `j1f_labels.py`'s map and
   its four-class identity check; `JANUS1F_LEFT_PDA`; J0's outputs reused, not recomputed; the T reading (Janus 0's
   argmax territory, 1-F's argmax among that territory's channels; needs 1-F's logits in the prediction step, not
   saved probabilities); `status`, `collect`, `JANUS1F_DRYRUN`.
3. **Branch scoring** (CPU, beside `tf1_score.py`, A1c unchanged): presence agreement, naming accuracy with sibling
   confusion, branch tF1 rooted where the reference branch meets its parent (one root per piece: the R-PDA is in two
   pieces in 10 % of cases), Dice report-only; the six untraced classes excluded from every ImageCAS-X metric.
4. **Stage 2 only: a label-set trainer**: label maps carry set ids above the class values (a pinned table of sets, per
   source); CE on log Σ_{c∈set} p_c; Dice positives from singleton voxels only, set voxels ignored for Dice. Built and
   CPU-tested before F4, not before F1.

## 12. What would change the plan

| If… | Then |
|---|---|
| F's vessel gate fails but T's branches pass | ship T (§7); round 2 asks whether 500 epochs or the 1e-2 peak moved the territories |
| ≥ half the gated branch classes fail B1/B2 in both readings | F3 (from scratch, weighted CE). If that also fails: a **graph namer on Janus 0's tree** becomes the primary (finding 2 says ordinal naming is trivial on a perfect tree; the hard part is which branches qualify) |
| J1F-A's pseudo-Dice for a branch class is still 0 at epoch 250 (`status`) | parent copy did not break the tie; report it on #303. The run continues (pre-registered), but round 2 starts F3's design early |
| Q1 = b | F0 relabels with `--left-pda name`; the vessel gate's collapse then sends a PDA/PLB piece that touches the LCx to LCx (an origin rule, CPU, in §11 item 3), so it still compares with Janus 0's D25 labels |
| The first extended reads show septals/SN/conus mostly < 2 voxels across at 0.5 mm (measure on exported reads, CPU) | stage 2 at 0.5 mm may not resolve them; round 2 weighs a finer spacing for those classes against Atlas's 0.5 mm evidence |
| The label-set loss lets a stage-2 class drift (predicted where no read supports it) | MultiTalent-style per-class sigmoid heads with per-source loss masks (arXiv:2303.14444 §2.2) as the alternative |
| Pool extended reads arrive slowly | stage 1's model ships and stage 2 waits; nothing in stage 1 depends on pool reads |


## 13. Citations (each opened at source this round unless marked; location given)

| # | Work | ID | What is used, and where |
|---|---|---|---|
| 1 | Bransby KM et al. ImageCAS-X: a dataset and benchmark for coronary artery segmentation and centerline extraction in CCTA. Preprint | arXiv:2608.30404 | **Suppl. B:** "Septal perforators, acute marginals and nodal arteries were not traced"; side branches not traced where the distal diameter < 1 mm; D3/D4/OM3/OM4 labelled "Other" only if "at least as large as the first or second branches or > 1.8 mm in diameter at the most proximal end". **Table 1** (inter-observer, test 160, n = scans where both analysts drew the segment): presence agreement and DSC per segment, e.g. D1 96.9 % / 79.9, D2 89.4 / 82.9, OM1 94.4 / 74.1, OM2 87.5 / 77.7, IM 89.4 / 80.6, R-PDA 98.8 / 82.6, R-PLA 96.2 / 83.6, L-PDA 100.0 / 75.1 (n 8), L-PLA 96.9 / 70.9 (n 9), Other 88.8 / 81.3 (n 14). **Coronary dominance** (§Data): 729 right (91.1 %), 41 left (5.1 %), 30 co-dominant (3.8 %) of 800 |
| 2 | Shi G, Xiao L, Chen Y, Zhou SK. Marginal loss and exclusion loss for partially supervised multi-organ segmentation. *Med Image Anal* 70:101979 (2021) | arXiv:2007.03868 | §3.2: a partially labelled image's background is a "merged" label, trained by summing the probabilities of the merged classes (marginal loss). §4 text with Tables 3–4: pooling the fully and partially labelled sets with marginal loss raised mean Dice from .874 to .900 over the fully labelled set alone; with exclusion loss, .931 vs .900 |
| 3 | Fidon L et al. Label-set loss functions for partial supervision: application to fetal brain 3D MRI parcellation. MICCAI 2021 | arXiv:2107.03846 | The label-set formulation used in §3: each voxel's annotation is a set of possible classes, and the loss marginalises over the set. Abstract and title checked; tables **not** re-read this round |
| 4 | Ulrich C, Isensee F et al. MultiTalent: a multi-dataset approach to medical image segmentation. MICCAI 2023 | arXiv:2303.14444 | §2.2: per-class sigmoid heads and a loss computed "only for classes that were annotated in the corresponding partially labeled dataset". Table 1: BTCV test Dice 88.82 (single model) vs nnU-Net 88.10. The alternative to §3's softmax label sets (§12) |
| 5 | Cermelli F, Mancini M, Rota Bulò S, Ricci E, Caputo B. Modeling the background for incremental learning in semantic segmentation (MiB). CVPR 2020 | arXiv:2002.00718 | §3.3, **Eq. 8–9**: each new class's classifier copies the background's weights, and the biases of the background and the new classes become β_b − log\|C_t\|, so the background's probability is split evenly, not re-learned. **Table 3** (Pascal-VOC overlapped): adding this initialisation raised the new classes' mIoU from 11.9 to 22.1 (19-1) and 4.5 to 13.5 (15-1). §5 applies it from the parent vessel instead of the background |
| 6 | Gotkowski K, … Isensee F. Revisiting 3D medical scribble supervision (first version: "Embarrassingly simple scribble supervision for 3D medical segmentation") | arXiv:2403.12834; nnU-Net `documentation/ignore_label.md` | nnU-Net's ignore label: "losses that are only computed on annotated pixels". It removes a voxel; it cannot say "LAD or S1", which is why §3 needs label sets, and why D40's ignore stays as one of them (the full set) |
| 7 | Leipsic J, Abbara S, Achenbach S et al. SCCT guidelines for the interpretation and reporting of coronary CT angiography. *J Cardiovasc Comput Tomogr* 8(5):342–358 (2014) | 10.1016/j.jcct.2014.07.003 | The 18-segment model ImageCAS-X follows (its §Centerline Extraction cites it as "[1]"). Title, journal, pages checked on Crossref; the figure itself **not** opened (paywalled). Used only as the source of ImageCAS-X's R-/L- split |
| 8 | Cao Q, Broersen A, de Graaf MA et al. Automatic identification of coronary tree anatomy in CCTA. *Int J Cardiovasc Imaging* 33:1809–1819 (2017) | 10.1007/s10554-017-1169-0; PMC5677991 | **Table 1**: separate right- and left-dominant models; in the left-dominant model the LPDA and LPLB are side branches **of the LCx**. Abstract: segments labelled in agreement 89.2 % (right-dominant) / 83.6 % (left-dominant) against expert–expert 97.6 / 87.6 %: naming is hardest, for humans too, exactly where Q1 sits |
| 9 | Yang H, Zhen X, Chi Y et al. CPR-GCN. CVPR 2020 | arXiv:2003.08560 | Table 3 (vault-verified, [[Atlas - The external evidence for a 4-class nnU-Net on ImageCAS-X, checked against the source texts]] 8a): labelling **reference** centrelines, mean F1 0.955; an upper bound for naming without extraction error |
| 10 | Hampe N et al. Graph neural networks for automatic extraction and labeling of the coronary artery tree in CTA. *J Med Imaging* 11(3):034001 (2024) | 10.1117/1.JMI.11.3.034001 | Vault-verified (same note, 8d): labelling F1 on **automatic** trees mean 0.74 vs 0.91 on reference trees (Tables 3, 8). A graph namer inherits every extraction error; the evidence for §4's choice |
| 11 | Isensee F et al. nnU-Net. *Nat Methods* 18:203–211 (2021); nnU-Net Revisited, MICCAI 2024 | 10.1038/s41592-020-01008-z; arXiv:2404.09556 | The recipe Janus 0 runs; `load_pretrained_weights` skips `.seg_layers.`, which §5's parent copy replaces |
| 12 | Zeng A et al. ImageCAS. *Comput Med Imaging Graph* 109:102287 (2023) | arXiv:2211.01607 | Voxel size (0.29–0.43 mm in-plane); vault-verified |

Every arXiv id above was resolved on export.arxiv.org on 2026-11-12 and its title matched. Items 1, 2, 4, 6 and 8
were read in full text for the quoted lines.
