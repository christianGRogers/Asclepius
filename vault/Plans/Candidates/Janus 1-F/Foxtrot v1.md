---
tags: [plans, candidate, track-1-F, round1, janus1-f, D44, D45, fir, partial-labels, locked100]
author: Foxtrot
track: 1-F
round: 1
version: 1
updated: 2026-11-12
issue: christianGRogers/Asclepius#303
---

# Foxtrot v1 (Janus 1-F): grow Janus 0's head into the branches ImageCAS-X drew, train with set-valued targets, and add the never-traced branches only when reads draw them

## 1. Thesis

Janus 1-F must segment 18 classes (D44, D45). ImageCAS-X's 14 classes cover only 12 of them. The plan is shaped by
what each class actually has, measured on D45's 620 training cases
([[Foxtrot - ImageCAS-X labels 12 of Janus 1-F's 18 classes, D3 in only 47 of 620 cases, and never traced septals, nodal or acute marginal branches]]):

1. **The six missing classes are not "unlabelled children" of their parents. They are outside ImageCAS-X's lumen.**
   - ImageCAS-X's protocol says: "Septal perforators, acute marginals and nodal arteries were not traced"
     (arXiv:2608.30404, Appendix B).
   - The labels agree. A twig of 3 mm or more hangs off the LAD label in only **6 of 620** cases, and off the RCA in 3.
   - So on ImageCAS-X, S1–S3, SN, RMA (and, as far as can be measured, the conus) are **background**. No
     partial-label loss can learn them from ImageCAS-X: there is no positive voxel anywhere.
   - They need pool reads that draw both the lumen and the name. Until those exist, the network should have no head for
     them.
2. **D3 is nearly absent.** "Other" yields a D3 in **47 of 620** cases, about 8 in the locked 100. It is a large-D3
   class: ImageCAS-X traces a third diagonal only if it is ≥ 1.8 mm or as large as D1/D2.
3. **The left-sided posterior question is small but real.**
   - L-PDA appears in 38 cases and L-PLA in 54 (0.5 % of foreground volume).
   - 46 cases are left-dominant and 13 co-dominant.
4. **The project's own 14-class attempt failed at optimisation, not at data.** icx14 trained from scratch with plain
   DiceCE ([[icx14 - interim check after job 1 (446 epochs), side branches not yet learned]],
   [[icx14 - job 2 restarted from scratch (resume bug), R-PLA appears at epoch 440]]):
   - every side branch had a val pseudo-Dice of exactly 0 for 440 epochs;
   - D1 was in 631 of 640 cases, so data was not the limit;
   - the parent class's cross-entropy majority won;
   - classes unlocked one at a time: R-PLA at about epoch 440, the rest not by epoch 455;
   - the four trunks themselves took 50–200 epochs to appear.
5. **On this project, a network's own names beat structure.** Round 5 compared namers on Janus 0's predecessor
   ([[Bridge - Trillium naming result on the master model]]):
   - rule renaming −0.013 tF1 and grammar decoding −0.013 [−0.022, −0.006] against the network's own names;
   - perfect (oracle) names would add only +0.010.
   - Published graph labellers (CPR-GCN, TreeLab-Net) are strong, but they need a correct centreline tree, and none is
     built here. Bridge found that "stage-1 gaps are what break naming".

**So the plan:**
- **One direct multi-class nnU-Net,** warm-started from Janus 0 by **head surgery**. Each child class copies its
  parent's output weights with bias −log k. At step 0, the four-vessel collapse equals Janus 0 **exactly** (checked to
  1.6e-15). The network never has to re-learn the vessels, only to split them. This removes icx14's first failure (the
  trunks taking 50–200 epochs) and shrinks the second (the parent's majority), because each child starts at its
  parent's probability, not at zero.
- **Set-valued (marginal) cross-entropy.** Every voxel's target is a set of allowed classes. The loss is
  −log Σ p over the set (Shi et al., MedIA 2021):
  - ImageCAS-X's ambiguities (L-PDA, D3 without D2, unexplained "Other") are handled by one rule;
  - pool reads, 4-class or extended (D44), use the same rule;
  - D40's overlaps are ignored.
- **Round 1 trains the 12 classes ImageCAS-X drew, on the 620 alone,** as track 1-L does.
  - The six never-traced classes are added later by the same head surgery, once enough reads draw them (§5).
  - The threshold is set by a measurement this run makes on D3, the rarest class it trains.
- **The locked 100 decides with a pre-registered fixed sequence** (§7):
  - the vessels must be non-inferior to the warm start;
  - each branch class is shipped, shipped provisional, or folded into its parent, on pre-set lines;
  - if the vessels fail, a CPU-only fallback relabels inside the start model's own four-class mask. That makes the
    vessels identical by construction.
- **Fir cost:** about **56 GPU-h** (two warm runs of 500 epochs, a1 and a2, plus inference). A 0 GPU-h identity check
  can run today (§8).

## 2. The 18 classes, what ImageCAS-X gives each, and its tier

Counts are on D45's 620 training cases. Expected locked-100 counts are scaled from the 620; no locked label was opened.

| 1-F class | From ImageCAS-X | Training cases | Expected in locked 100 | Median diameter (mm) | Tier |
|---|---|---|---|---|---|
| LM, LAD, LCx, RCA | as drawn | 611 / 620 / 620 / 620 | ~99–100 | 3.0 / 1.68 / 1.67 / 2.25 | Vessels (V) |
| D1 | D1 | 611 | ~98 | 1.27 | A |
| D2 | D2 | 359 | ~58 | 1.27 | A |
| OM1 | OM1 | 540 | ~87 | 1.35 | A |
| PDA | R-PDA, plus L-PDA as a set (§3) | 572 (+38) | ~92 (+6) | 1.22 | A |
| PLB | R-PLA, plus L-PLA as a set | 565 (+54) | ~91 (+9) | 1.35 | A |
| OM2 | OM2 | 229 | ~37 | 1.35 | B |
| Ramus | IM | 149 | ~24 | 1.21 | B |
| D3 | the diagonal-side "Other" nearest the LM/LAD join | 47 | ~8 | 1.25 | C |
| S1, S2, S3, SN, RMA | **never traced** (background) | 0 | 0 | — | D |
| Conus | not mentioned by ImageCAS-X; no twigs in the RCA label | 0 | 0 | — | D |

**What each tier means:**

| Tier | Meaning |
|---|---|
| A | At or above about 49 present locked cases, the size for a ±0.10 detection CI. **Decided on the locked 100** |
| B | 14–41 present cases give ±0.10 Dice but not detection. **Reported with CIs; shipped only as provisional** |
| C | Too rare to report. **Trained, counted, shipped provisional** |
| D | No ImageCAS-X signal. **No head in round 1**; added by reads (§5) |

The sample sizes are in the experiment note, §6. Dice SDs come from ImageCAS-X's Table 1 inter-observer agreement.

## 3. Data and the partial-label strategy

### 3.1 One rule: every voxel's target is a set of allowed classes

The loss for a voxel with allowed set S is the marginal cross-entropy, −log Σ_{c∈S} p_c:
- a singleton set is ordinary CE;
- the full set is "ignore";
- a parent set (e.g. {LAD, D1, D2, D3}) moves the set as a whole and **never re-ranks its members**.

`head_surgery_check.py` verifies the gradient against finite differences: grad/p is constant inside the set.

Shi et al. call this the marginal loss: "the background label … combines the unlabeled organs with true background"
(arXiv:2007.03868; MedIA 70:101979, 2021). It is the minimal extension of nnU-Net's DiceCE:
- the **CE term** uses the marginal;
- the **Dice term** treats set-valued voxels as ignore for every class (they are 0.5 % of foreground on ImageCAS-X);
- **D40's overlaps** are 255, as now;
- nnU-Net's nearest-neighbour label downsampling for deep supervision keeps the codes intact.

### 3.2 ImageCAS-X → 1-F (`experiments/Foxtrot/j1f/make_labels_1f.py`, run on all 620)

| ImageCAS-X | 1-F target | Cases | Why |
|---|---|---|---|
| LM, LAD, LCx, RCA, D1, D2, OM1, OM2, IM, R-PDA, R-PLA | LM, LAD, LCx, RCA, D1, D2, OM1, OM2, Ramus, PDA, PLB | — | Same vessel, same name |
| L-PDA | set {PDA, LCx} | 38 | The lead's question (Q1); trains without presupposing the answer |
| L-PLA | set {PLB, LCx} | 54 | The same |
| "Other", diagonal side, attached nearest the LM/LAD join, case has D1 and D2 | D3 | 47 | Ordinal: the next diagonal after D2 |
| the same, but the case has no D2 | set {LAD, D3} | 1 | The ordinal is unknown |
| a further diagonal-side "Other" (D4) | LAD | 2 | D44 has no D4; #280 unions it into the LAD |
| "Other", marginal side (OM3, OM4) | LCx | 20 | No OM3 class; #280 unions it into the LCx |
| "Other" touching only the RCA (7) or nothing (1) | ignore (255) | 8 | Unexplained; not guessed |
| background | background | all | See §5.3 for the Tier D change later |

**What the 620 receive:**
- D3 0.26 % of foreground;
- set {PDA, LCx} 0.27 %;
- set {PLB, LCx} 0.25 %;
- ignore < 0.01 %.

The converter writes a NIfTI per case (`write` mode). The launcher (§9) builds the 1-F dataset with it.

### 3.3 Pool reads (when they enter: through Round 10's A36 path, not in round 1)

| Read | Voxel painted as … | 1-F target |
|---|---|---|
| Extended (D44) | a branch class c | c |
| Extended | parent P (LAD, LCx or RCA) | set {P ∪ the children of P that this read left **empty**} |
| Extended | a Tier D class whose head does not exist yet | its parent, side-aware (SN by attachment; S1–S3 → LAD; conus and RMA → RCA) |
| 4-class (protocol 17) | parent P | set {P ∪ every child of P} |
| Any | two or more classes (D39) | 255 (D40) |
| Any | background | background |

A class left empty in an extended read is ambiguous, because D38 allows empty classes. The set rule never teaches
"this branch is its parent" from an annotator who did not label branches.

### 3.4 Not in round 1

Pool reads (none are exported yet, and 1-L also trains on the 620 alone), the D35 set, sealed cases. **D22 stands:**
ImageCAS-X is not re-annotated. Q4 asks one bounded question about it.

## 4. Architecture and recipe

### 4.1 One network, not segment-then-label

| | Direct multi-class (chosen) | Segment-then-label (fallback and comparator) |
|---|---|---|
| Names | The network's own. On this project these beat rules by 0.013 tF1 and are within 0.010 of oracle names (Round 5) | A namer must place every branch point. Gaps move whole sub-trees (Bridge, Round 1–2) |
| Code needed | A head-growing loader and a set-valued loss (§9) | A centreline graph, a learned or rule namer for 12 classes, and voxel re-projection. None exists beyond the 4-class `segtrain.namer` |
| Literature | MultiTalent (Ulrich et al., MICCAI 2023, arXiv:2303.14444): one nnU-Net-family model over datasets with conflicting class definitions | CPR-GCN (Yang et al., CVPR 2020, arXiv:2003.08560): 511 subjects, mean F1 0.955; TreeLab-Net (Wu et al., IJCARS 2019, doi:10.1007/s11548-018-1884-6): 436 CCTA. Both start from a given centreline tree, on private data |
| Vessels | Must be shown non-inferior (V1) | Identical to the start model by construction |

**The hybrid is kept as the fallback, at no GPU cost.** "Relabel within mask" takes the start model's four-class
mask. Inside each territory, each voxel takes 1-F's argmax among that territory's children (PDA and PLB inside the LCx
territory, too). It needs only 1-F's saved probabilities on the locked 100. It is used only if V1 fails (§7, a fixed
sequence, so no second look).

### 4.2 Warm start by head surgery

- **Start:** Janus 0's `checkpoint_final.pth` (Dataset715, D34). If track 1-L has shipped a Janus 1-L under its H1
  before F1 is submitted, start from that instead. It has the same plans and architecture (1-L's L-A2). V1 then
  compares against whichever model was the start.
- **Surgery:** each deep-supervision `seg_layers` 1×1×1 conv grows from 5 to 13 outputs:
  - every class under parent P takes P's weights and the bias b_P − log k_P;
  - k = 4 for LAD (LAD, D1, D2, D3), 4 for LCx (LCx, OM1, OM2, Ramus) and 3 for RCA (RCA, PDA, PLB).
  - Every other tensor is loaded strictly and bitwise, as `finetune_load` does now.
  - Stock nnU-Net re-initialises the heads ([[Foxtrot - Stock nnU-Net warm starts re-initialise the segmentation heads and have no warm-up, and the MAE paper found 1e-3 better than 1e-2]]).
    That would throw away the four-vessel solution, which is what icx14 lost 200 epochs relearning.
- **Exactness:** the four-vessel collapse of the grown network equals Janus 0's softmax to 1.6e-15
  (`head_surgery_check.py`, 10 000 random voxels). At step 0, Janus 1-F *is* Janus 0 under the collapse.
  - Children of one parent start tied, so the argmax picks the first, the parent itself.
  - Training only has to break ties where the labels say so.
- **Plans:** Janus 0's `plans.json`, byte-identical, moved to the 1-F dataset with
  `nnUNetv2_move_plans_between_datasets`:
  - no fingerprint and no `plan_experiment` (as 1-L's L-A2 corrected for 1-L);
  - `SEGTRAIN_CT_WINDOW=off`, with the loader's field-by-field plan check as the guard.
  - The loader's class check is relaxed in one way only: the new label set must be the old one plus children
    declared in a parent map.

### 4.3 Recipe

- **Kept from Janus 0 and 1-L:**
  - 0.5 mm isotropic, 256³ patch, batch 2;
  - **mirroring off** (left and right are names here);
  - nnU-Net's default augmentation otherwise;
  - `checkpoint_final` only, `--disable_tta`;
  - uniform sampling over the 620;
  - fold val = the locked 100, for display only (L-A2): nothing is chosen on it.
- **Schedule:**
  - A17a's 2500-iteration warm-up to 1e-2, then poly;
  - **500 epochs** × 250 iterations, not 1-L's 250.
  - Why 500: from scratch, icx14's first side branch appeared at about epoch 440. Head surgery should shorten that,
    but by an unmeasured amount. The interim fit checks (§4.4) are the evidence a later round uses to shorten it.
- **Loss:** DiceCE with the set-valued CE (§3.1). No class weights at the start.
- **Two runs, a1 and a2:** folds 0 and 1 of an identical split, so they differ only in seed and order, as in 1-L's
  L-A9.
  - a1 decides.
  - a2 must agree in sign (§7).
  - a2 also gives the first between-run spread on branch classes, which every later 1-F decision needs.

### 4.4 Interim fit checks (training cases only; nothing on the locked 100)

At epochs 150 and 300, the job predicts 20 fixed **training** cases with `checkpoint_latest`:
- the first 20 of the 620 by sha256(`asclepius-j1f-fitcheck:` + id);
- it records the per-class Dice against their 1-F labels in `fitcheck.json`.

**Pre-registered rules:**
- **At 150:** any Tier A class with fit Dice below 0.30 (icx14's failure mode) → the remaining chunks use CE weights
  of 4 on the 8 branch classes. icx14 prepared this file but never ran it. The vessel weights stay at 1.
- **At 300:** any Tier A class still below 0.30 → the run continues, and the plan records "direct learning failed for
  class c". The locked-100 read then uses the fallback for that class (relabel within mask), not a new run.
- **D3's fit Dice at epoch 500 sets the Tier D threshold (§5.2).** D3 has 47 training cases, the rarest class trained
  here.

## 5. Staged class addition and how many reads per class

### 5.1 Training thresholds

A Tier D class gets a head (grown from its parent with bias −log k, exactly as in §4.2) when it has trainable reads
in at least **N_train** patients:
- trainable = non-sealed, non-D35, not in the reserve;
- either read counts.

| D3's fit Dice at epoch 500 (a1) | N_train | Reading |
|---|---|---|
| ≥ 0.60 | **50** | About 50 cases suffice for a warm, grown head |
| < 0.60 | **150** | Rarity is the bottleneck; wait for three times the reads |

This makes the threshold a measurement on the project's own data instead of an opinion. It is the only number in the
plan chosen this way. Until a Tier D class passes, its painted voxels go to its parent (§3.3).

### 5.2 Reporting thresholds

- A class is **reported** with a CI on a set when it is present in **≥ 30** scored patients (Dice ±0.10 for most
  classes, experiment note §6).
- It is **decided on** (shipped as a named class) only at **≥ 49** (detection ±0.10).
- Below 30: counts only.
- For Tier D the only scored set is the D35 decision set's extended reads (35 patients, A33). **No Tier D class can be
  decided on before a larger extended-read scoring set exists.** §11 Q3 asks the lead about that.

### 5.3 What changes on ImageCAS-X when a Tier D head is added

Once S1–S3 exist, ImageCAS-X's background next to the LAD is "background or an untraced septal".
- **Proposed:** background voxels within 8 mm of ImageCAS-X's LAD label take the set {bg, S1, S2, S3}. Those within
  8 mm of the RCA's first 40 mm and of the LCx's first 20 mm take {bg, SN, Conus, RMA} as applicable.
- Everything farther stays background, which keeps the false-positive pressure that Shi et al.'s exclusion loss
  otherwise supplies.
- **This distance rule is untested.** Round 2 measures how much background it releases, on CPU.

## 6. Metrics

All metrics are computed on the locked 100 against the 1-F reference built from ImageCAS-X by `make_labels_1f.py`:
- a set-valued voxel counts as correct if the prediction is any member;
- 255 is excluded.
The vessel scorer is unchanged.

| Metric | Defined as | Role |
|---|---|---|
| **Vessel tF1** | Collapse 1-F to four, side-aware: D1–D3 → LAD; OM1, OM2, Ramus → LCx; a PDA or PLB component → the LCx if it touches the LCx territory more than the RCA, else the RCA. Then the A1c decisive tF1 (hash `24441cf8…5254`, TotalSegmentator aortas), unchanged | Decides V1 |
| **Branch detection F1** | Per case and class: present in the reference if its skeleton is ≥ 3 mm; predicted present if class c's skeleton is ≥ 3 mm. F1 over cases. This mirrors ImageCAS-X's presence agreement | Decides B |
| **Branch centreline F1 (cF1)** | Per class: skeleton precision and recall at 1.5 mm (decision D3's tolerance), with no break rule, over cases where the reference has the class. Not A1c; a new, frozen-by-hash scorer (§9) | Decides B |
| **Naming accuracy** | Over reference branch components with any predicted vessel overlap: the share whose overlapping prediction's majority label is right. It separates naming from detection | Report |
| **Dice per class** | Over present cases. Report only (A28's spirit). Read against ImageCAS-X's inter-observer Dice (Table 1: D1 79.9, D2 82.9, OM1 74.1, OM2 77.7, IM 80.6, R-PDA 82.6, R-PLA 83.6, L-PDA 75.1, L-PLA 70.9, Other 81.3) | Report, as a human-level line |
| **FP components** | As A15, per case | Report |
| **Tier D** | Not scored on the locked 100: there is no reference. Scored only on extended pool reads, once §5.2's counts are met | — |

Val 80 and locked 20 are reported apart; a sign reversal is reported, not acted on (A26, as in 1-L).

## 7. The pre-registered decision on the locked 100

The decision is computed once, after a1 and a2 are both done. It is a fixed sequence, so later steps are read only if
earlier ones pass.

| Step | Rule | If it fails |
|---|---|---|
| **V1, vessels** | Paired bootstrap over the 100 (patients resampled), a1 − start: macro vessel tF1 Δ lower 95 % bound **> −0.02**, and no class point Δ **< −0.03**. a2's macro point Δ also > −0.02 | Go to V1-fallback |
| V1-fallback | Recompute B on "relabel within mask" (§4.1). V1 then holds by construction | Branch steps use the fallback output |
| **B, Tier A** (D1, D2, OM1, PDA, PLB) | Per class: detection F1 ≥ **0.80** and cF1 ≥ **0.70** in a1; a2's points also ≥ 0.75 / 0.65 | The class is **folded into its parent** in the exported map |
| **B, Tier B** (OM2, Ramus) | The same lines on point estimates | Folded into the parent; if it passes, it is shipped as **provisional** |
| **Tier C** (D3) | Reported (counts, detections), no line | Shipped **provisional** |
| **Read** | 1-F is read and takes the next Janus number (D34) if V1 or its fallback holds **and ≥ 3 of the 5** Tier A classes pass | "Not adopted": the start model stays the vessel model; round N+1 diagnoses from training-set fit and aggregates only |

**Why these lines:**
- **V1's −0.02** is a non-inferiority margin. Track 1-L's round-1 ruling found that a −0.01 margin fails 21–39 % of
  neutral models on the locked 100. A paired macro MDE of 0.011–0.021 means −0.02 is the tightest margin a neutral
  model passes reliably.
  - Head surgery makes Δ = 0 at step 0. Any loss is what splitting costs the trunks.
  - **What 1-F must hold on the four vessels compared with Janus 0 is therefore the lower 95 % bound of the macro tF1
    change above −0.02, with no vessel class down by more than 0.03.** Janus 0's decisive val-80 tF1 was 0.909
    (LM 0.945, LAD 0.903, LCx 0.857, RCA 0.938).
- **Tier A's lines** have no published model to anchor them (ImageCAS-X benchmarks only binary lumen; experiment note
  and Bransby et al.).
  - 0.80 detection and 0.70 cF1 are working lines, not derived ones. I did not read ImageCAS-X's per-segment presence
    agreement figures, so I do not anchor to them. A later round should tighten both on a2's spread.
- **"Fold into parent"** means a weak class never ships a wrong name. It still ships its lumen, under the parent, so the
  vessels lose nothing.

## 8. Fir jobs, GPU-hours and exact commands (the lead runs them; account `def-aso22`)

| # | Job | Needs | GPU-h |
|---|---|---|---|
| **F0** | Identity check of the label conversion on Fir's own ImageCAS-X copy, 620 cases. CPU only | This PR merged | **0** |
| **F1** | a1 and a2: warm, grown heads, 500 epochs, two chained 23:50 jobs each, concurrent; interim fit checks at 150/300 | §9's code | 2 × ≈ 27 = **≈ 54** |
| **F2** | Predict the locked 100 (probabilities saved, for the fallback) and the 620's fit cases; collect | F1 | **≈ 1–2** |
| **F3** | Score V1 and B on CPU, with the start model's existing locked-100 predictions (`$SCRATCH/icx4/predictions`) | F2 | **0** (16-core CPU job) |
| | **Total** | | **≈ 56**, ceiling ≈ 60 |

**Costing:**
- **Epoch time:** Janus 0 ran at about 192 s/epoch on Fir ([[icx4 - Results]]). The 13-output head adds a negligible
  amount, 8 extra 1×1×1 output channels.
- **Per run:** 500 × 192 s = 26.7 h, so 2 chained jobs.
- **Saving if F1 converges early:** a2 could stop at a1's verdict point. That is not done in round 1, because the
  first 1-F spread is the point of a2.
- **Not costed here:** a from-scratch 1-F. Rejected on icx14's record (§1.4); about 54 GPU-h per seed if a later round
  wants it.

### F0 (runnable as soon as this PR merges; 0 GPU-h)

On `fir.alliancecan.ca`, inside `tmux`:

```sh
module load StdEnv/2023 python/3.11.5
cd $SCRATCH/asclepius && git -C repo fetch origin dev && git -C repo checkout dev && git -C repo pull --ff-only
source $HOME/icx14-venv/bin/activate            # icx4's venv: nibabel, scipy, scikit-image via nnU-Net
J=$SCRATCH/asclepius/repo/experiments/Foxtrot/j1f
mkdir -p $SCRATCH/j1f && cd $SCRATCH/j1f
# the 620 / 100 lists from icx4's own copy of the ImageCAS-X file lists; asserts no sealed id
python $J/split620.py $SCRATCH/icx4/icx $SCRATCH/asclepius/repo/trillium/icx4/sealed_test.json split620.json
python - <<'EOF'
import json, hashlib
d = json.load(open('split620.json'))
for k in ('train620', 'locked100'):
    print(k, hashlib.sha256('\n'.join(sorted(d[k])).encode()).hexdigest())
EOF
# the conversion: reads only the 620 training labels
srun --account=def-aso22 --time=1:00:00 --cpus-per-task=8 --mem=32G \
    python $J/make_labels_1f.py stats $SCRATCH/icx4/icx split620.json labels_1f_stats.json 8
python -c "import json; s=json.load(open('labels_1f_stats.json'))['summary']; print(s['other'], s['cases_with_D3'])"
```

**Send back the three printed lines.**

**Expected:**
- train620 `1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152`;
- locked100 `bbd9c687818956e2d5664b06fd8c8bd02ddb031e9b9d08036d59cc0e1a4d5895`;
- `{'other_diag': 50, 'other_marg': 20, 'other_amb': 8, 'd3_from_other': 47, 'd3_set': 1, 'd4_to_lad': 2} 47`.

Any difference means Fir's label copy or the conversion differs from this PR's. Stop and tell the PM.

### F1–F2 (after §9's code merges; the launcher mirrors icx4's and #306's)

```sh
module load StdEnv/2023 python/3.11.5
cd $SCRATCH/asclepius && git -C repo pull --ff-only
mkdir -p experiments && rm -rf experiments/janus1f && cp -r repo/trillium/janus1f experiments/janus1f
cd experiments/janus1f
ls $SCRATCH/icx4/nnunet_results/Dataset715_ICX4/nnUNetTrainerICX4__nnUNetResEncUNetPlans_60G_iso05__3d_fullres/fold_0/checkpoint_final.pth   # Janus 0 (icx4's job_body.sh: DS, TR, PLANS)
J1F_CLUSTER=fir J1F_START=$SCRATCH/icx4/nnunet_results/Dataset715_ICX4/nnUNetTrainerICX4__nnUNetResEncUNetPlans_60G_iso05__3d_fullres/fold_0/checkpoint_final.pth \
    J1F_FOLDS="0 1" CHAIN=2 ./janus1f
grep SBATCH $SCRATCH/janus1f/job.sh    # --gpus-per-node=h100:1 --cpus-per-task=12 --mem=280G --time=23:50:00 --account=def-aso22
./janus1f status                        # epochs, s/epoch, and fitcheck.json at 150 / 300
./janus1f collect                       # after both folds end: results/ incl. fitcheck.json, locked-100 probabilities index
```

**Notes on F1–F2:**
- The `J1F_START` path is Janus 0's checkpoint as icx4 writes it (`DS=Dataset715_ICX4`, `TR=nnUNetTrainerICX4`,
  `PLANS=nnUNetResEncUNetPlans_60G_iso05` in `trillium/icx4/lib/job_body.sh`); the `ls` line checks it first. The
  launcher records its sha256 in the results, so the start of record is pinned.
- **Check the printout:**
  - `start: Janus 0 (Dataset715), heads grown 5 -> 13, collapse max |Δ| < 1e-6`;
  - `train 620 pin 1350cb1f…`;
  - `locked 100 pin bbd9c687…`;
  - `sealed 0`;
  - four job ids (two per fold).

### F3 (CPU, after F2)

```sh
cd $SCRATCH/asclepius/experiments/janus1f
srun --account=def-aso22 --time=3:00:00 --cpus-per-task=16 --mem=64G ./janus1f score   # V1, fallback if needed, B, report
```

**Send back:** `results/DECISION.md`, written by the scorer verbatim from §7's table.

## 9. `role:swe` work this plan needs (one issue, opened only if the judge adopts the plan)

1. **`finetune_load` grow mode.** It takes a parent map `{child: parent}` and grows each `seg_layers` conv with the
   parent's row and bias b_P − log k_P. It asserts the four-vessel collapse equals the source within 1e-6 on a random
   batch. Self-tested on CPU with a tiny network, like `tests/test_finetune.py`.
2. **Set-valued DiceCE** in a trainer (`nnUNetTrainer_segtrain_j1f`):
   - label values ≥ 20 are sets, read from `dataset.json` (`"sets": {"20": [11, 3], …}`);
   - CE is the marginal;
   - Dice ignores set voxels;
   - 255 is ignore;
   - optional class weights at a chunk boundary (§4.4);
   - the fit check at 150/300.
3. **`trillium/janus1f` launcher:**
   - builds the 1-F dataset from `$SCRATCH/icx4/icx` with `make_labels_1f.py write`;
   - moves Janus 0's plans and preprocesses;
   - uses 1-L's split file and guard (L-A1, `configs/janus1/split-2026-11.json`);
   - chains, resumes (either checkpoint file: icx14's lesson), predicts, collects and scores.
4. **The branch scorer:** detection F1, cF1, naming accuracy and per-class Dice on 1-F references, with set and 255
   handling, frozen by hash before F3. It also does the side-aware collapse and relabel-within-mask.

**Size:** the loader and loss are small (each about 100 lines plus tests). The launcher is a copy-and-edit of icx4's.

## 10. What would change the plan

| Observation | Change |
|---|---|
| Fit Dice of Tier A classes still < 0.30 at epoch 300 with class weights | The direct approach failed for those classes. Round 2 makes segment-then-label primary for them, with a namer trained on the 620's centrelines |
| V1 fails on a1 but passes on a2 (or the reverse) | Seed noise dominates the vessel change. The next round costs a third seed or an ensemble before any 1-F model is read |
| D3 fit Dice ≥ 0.60 | N_train = 50 for Tier D (§5.1) |
| D3 fit Dice < 0.60 | N_train = 150 |
| The lead answers Q1 | The sets {PDA, LCx} and {PLB, LCx} become plain values (PDA/PLB, or LCx) in the next dataset build. No retrain is needed for the vessels: the collapse is side-aware either way |
| Extended pool reads arrive faster than expected (≥ 50 patients with septals) | S1–S3 are added in the first pool fine-tune, with §5.3's distance rule measured first |
| Pool reads show that the TotalSegmentator seed rarely contains septals, conus or SN | Annotators would have to trace beyond the seed (Q3). Without that, Tier D cannot be learned from the pool either |
| 1-L ships a model under H1 before F1 starts | F1 starts from it (§4.2); V1 compares against it |
| A published multi-class coronary-branch model on ImageCAS-X appears | Its per-segment numbers replace §7's working lines for Tier A |

## 11. Questions for the lead (asked, not decided)

**Q1. Left-sided PDA and PLB (D44 lists them under the RCA).** Two options:
- **(a) Anatomical (recommended):**
  - the PDA and PLB classes mean "the posterior descending / posterolateral branch, from either side";
  - the four-vessel collapse is side-aware (left-sided → LCx), which keeps D25;
  - ImageCAS-X itself names L-PDA and L-PLA as their own segments;
  - the SCCT 18-segment reporting model also names segments rather than territories (Leipsic et al. 2014, below).
- **(b) Territorial:** PDA and PLB only when right-sided; a left-sided one stays LCx.

Either way, **#280's current default collapses PDA, PLB and SN to the RCA always.** That contradicts D25 for left
sides. In the 620 it would move 38 L-PDA and 54 L-PLA branches to the wrong vessel in the 4-class scores. Whichever
the lead picks, #280's collapse should follow it. The same question applies to an SN from the LCx.

**Q2. Should the extended-class annotator instructions ask annotators to trace septals, SN, conus and RMA beyond the
TotalSegmentator seed?**
- ImageCAS-X never traced them, so their only possible labels are pool reads.
- A seed that lacks them gives annotators nothing to cut down (D26).
- This costs annotator time, and it is the lead's call.

**Q3. A scoring set for Tier D.** The D35 set (35 patients) cannot reach §5.2's 30 present cases for septals or SN
unless nearly every patient has them labelled. Two options:
- accept "counts only" for Tier D until the pool has enough extended reads (the default);
- or enlarge the decision set, which changes D35's frozen draw and is a D35 question.

**Q4 (D22). Targeted extended reads of ImageCAS-X?** The fastest route to Tier D labels is extended reads of only
S1–S3, SN, conus and RMA on about 60 ImageCAS-X *training* cases. This changes D22.
- **Recommended: not now.** Revisit at the first pool wave if fewer than 50 patients have septal reads.

## 12. External evidence (checked 2026-11-12)

| Source | What it supports | Checked how |
|---|---|---|
| Bransby et al., *ImageCAS-X: a dataset and benchmark for coronary artery segmentation and centerline extraction in CCTA*, arXiv:2608.30404; data Zenodo 10.5281/zenodo.21887809 | Appendix B: "Septal perforators, acute marginals and nodal arteries were not traced"; the < 1 mm distal rule; "Other" = D3/D4/OM3/OM4 only if ≥ 1.8 mm or as large as the first or second branch. Table 1: per-segment inter-observer DSC (quoted in §6), with presence agreement defined as "both analysts either annotate that segment or both omit it". Dominance on 800: 91.1 % right, 5.1 % left, 3.8 % co. Supplementary Table 4: the 14 class ids. **No multi-class benchmark** (binary lumen only) | arXiv HTML read 2026-11-12. The conus branch is not mentioned anywhere |
| Shi, Xiao, Chen, Zhou, *Marginal loss and exclusion loss for partially supervised multi-organ segmentation*, MedIA 70:101979 (2021), doi:10.1016/j.media.2021.101979, arXiv:2007.03868 | The marginal loss (§3.1); the exclusion loss as the reason to keep background elsewhere (§5.3) | Abstract and bibliographic record read. **Tables not read**; no number of theirs is used |
| Ulrich, Isensee, Wald, Zenk, Baumgartner, Maier-Hein, *MultiTalent*, MICCAI 2023, arXiv:2303.14444 | One nnU-Net-family model over datasets with conflicting class definitions | Abstract only. Its loss and heads were not read, so nothing here depends on them |
| Yang, Zhen, Chi, Zhang, Hua, *CPR-GCN*, CVPR 2020, arXiv:2003.08560 | A graph labeller on 511 subjects, mean F1 0.955 (abstract), given a centreline tree | Abstract |
| Wu et al., *Automated anatomical labeling of coronary arteries via bidirectional tree LSTMs* (TreeLab-Net), IJCARS 14:271–280 (2019), doi:10.1007/s11548-018-1884-6 | Tree labelling on 436 CCTA; main-branch AUC > 97 % | Bibliographic record and abstract |
| Leipsic et al., *SCCT guidelines for the interpretation and reporting of coronary CT angiography*, J Cardiovasc Comput Tomogr 8:342–358 (2014), doi:10.1016/j.jcct.2014.07.003 | The 18-segment model behind Q1(a) | Record verified, and its 18-segment model confirmed through Kim et al., Korean J Radiol 25:331 (2024), doi:10.3348/kjr.2024.0112. **I could not open the 2014 text, so its segment numbering is not quoted** |
| Gotkowski, Maier-Hein, Isensee, *Revisiting 3D medical scribble supervision*, arXiv:2403.12834 (MICCAI 2025) | nnU-Net with a partial loss is a strong baseline for partially labelled 3D data | Abstract |

**Project evidence used:**
- icx14's two notes (§1.4);
- [[Bridge - Trillium naming result on the master model]] and [[Bridge - Stage-1 gaps are what break naming, and bridging fixes most of it]];
- [[icx4 - Results]] (Janus 0's numbers and Fir's 192 s/epoch);
- the Janus 1-L round-1 ruling (L-A1 pins, L-A2 recipe, the −0.01 margin finding);
- Foxtrot's warm-start note.

## 13. Risks

| Risk | Mitigation |
|---|---|
| Head surgery's tie leaves children unlearned (argmax always the parent) | The tie breaks wherever CE has a singleton child label (every D1 voxel, for example). The epoch-150 fit check catches a stall, and its pre-registered response is class weights |
| Set-valued targets let the model put a set's rarer member nowhere (L-PDA always predicted LCx) | Only 0.5 % of foreground is set-valued. Q1's answer removes it. Scored as correct either way until then |
| A distribution shift between ImageCAS-X's large-D3 and a pool read's D3 | Tier C status; D3 is never decided on ImageCAS-X alone |
| V1 fails | A CPU fallback, identical vessels by construction (§4.1) |
| 500 epochs is too long or too short | The fit checks record the unlock epoch. a2 duplicates it. Round 2 resizes with that evidence |
| The working lines (0.80, 0.70) are unanchored | Stated as such (§7). a2's spread tightens them in round 2 |
| New code is on the critical path | F0 runs today. The code is two small modules plus a copied launcher (§9) |

## 14. Code and notes in this PR

- `experiments/Foxtrot/j1f/`:
  - `split620.py`, `fetch_620.py`: D45's split and a fetch of only the 620 labels;
  - `census14.py`, `census7.py`, `summarise14.py`: the census;
  - `make_labels_1f.py`: the 14 → 1-F conversion with set codes;
  - `head_surgery_check.py`: the exactness and gradient checks;
  - `results/`: per-case census, summaries, conversion stats, check output;
  - `split620.json`: the lists, matching L-A1's pins.
- [[Foxtrot - ImageCAS-X labels 12 of Janus 1-F's 18 classes, D3 in only 47 of 620 cases, and never traced septals, nodal or acute marginal branches]].
- No sealed, locked-100 or other test label was downloaded or opened. No GPU job was run.
