---
tags: [plans, candidate, janus-1f, branches, partial-labels, fir, round1, D44, D45]
author: Atlas
track: 1-F
round: 1
version: 1
updated: 2026-11-11
issue: christianGRogers/Asclepius#303
---

# Atlas v1 (Janus 1-F): learn branch types, not ordinals; start the new outputs exactly at Janus 0; beat a zero-GPU namer on the locked 100

## 0. The plan in one paragraph

Janus 1-F has to name 14 branches, and ImageCAS-X labels only part of them. This plan rests on four measured facts.

1. **The project's own 14-class run never learned a branch.** It was the cancelled `icx14`. After 455 of 1000 epochs
   (two 23 h jobs), 9 of its 10 branch classes had a validation pseudo-Dice of exactly 0 in every epoch. The tenth,
   R-PLA, first rose above 0 at epoch 424. Its trunks learned normally (LM 0.90, LAD 0.90, LCx 0.84, RCA 0.93) (§2).
2. **ImageCAS-X's ordinals follow a rule.** On the 613 training cases, ⟨ORD⟩ (§3.3).
3. **ImageCAS-X draws only the branches it names.** The LAD and RCA labels carry ⟨EP⟩ unnamed side twigs. Septals, SN,
   conus and RMA are therefore **background** in ImageCAS-X, not unlabelled LAD/RCA (§3.2).
4. **An exact warm start exists.** New branch outputs can be initialised from Janus 0's head so that, with hierarchical
   decoding, the first epoch reproduces Janus 0 voxel for voxel (§5.2, checked numerically).

So:

- **The network learns branch *types*.** These are D (diagonal), OM, Ramus, PDA, PLB, and later S, SN, Conus and
  RMA. **Ordinals** (D1–D3, S1–S3, OM1–OM2) are assigned afterwards from origin order along the parent.
- **It warm-starts from Janus 0 with a parent-copy head** (*Arm T*, one Fir run, ≈ 28 GPU-h).
- **It must beat a zero-GPU baseline** (*Arm N*: a branch namer that names Janus 0's own predicted tree). The decision
  is pre-registered on the locked 100 (§7). Arm N holds the four vessels by construction. Arm T must hold them within
  −0.02 macro tF1 of Janus 0.
- **Classes with no ImageCAS-X label (S, SN, Conus, RMA) are not emitted in phase 1.** They enter in phase 2, from
  extended pool reads, under a marginal (set-valued) loss. Three conditions apply: the read marks the branch group
  complete, ≥ 30 trainable patients carry the class, and a class is emitted only after it clears a per-class floor on
  ≥ 40 evaluation patients (§4.4).
- **Three questions go to the lead (§10).** The main one is PDA/PLB: name them by position, but collapse to four
  classes by origin, which is D25's own rule.

## 1. What binds this plan

| Decision | What it fixes here |
|---|---|
| D45 | Classes: LM, LAD, LCx, RCA + D1–D3, S1–S3, OM1, OM2, Ramus, SN, Conus, RMA, PDA, PLB (18 + background). Fir. **620 training / locked 100**, seal intact. Materials (1-M) not here |
| D44 | SegQueue's extended classes are optional per read; 4-class reads keep coming |
| D8 | ImageCAS-X's lumen as drawn |
| D22 | The 800 ImageCAS-X cases are not re-annotated (so no new ImageCAS-X labels for S/SN/Conus/RMA/D3, ever, unless the lead changes D22) |
| D25, D1, D1b | The four-class collapse is **by territory = by origin** (a branch takes its parent's class; ramus → LCx; a left-sided PDA/PLA → LCx) |
| D27/D32, D35 | Pool seal and D35 decision set: never trained on; D35 decides pool questions |
| D40 | Voxels claimed by two classes in a pool read → ignore |
| D3, A1c | tF1 @ 1.5 mm with the pinned `tf1.py` (sha256 `24441cf8…5254`) |
| D34 | 1-F runs are numbered as they are read |
| D9/D10 → D25 | The 14-class attempt is history; its lesson is §2 |

**The locked 100 is the sister track's.** All five 1-L round-1 advocates hash the project case id
(`sha256('asclepius-janus1-locked100:c0068')`). That gives locked-100 sha256 `bbd9c687…d5895`
(`experiments/Atlas/j1l/split_j1l.json`). `experiments/Atlas/j1f/split.py` reproduces the same 20 cases. Hashing
ImageCAS-X's own file number instead ("69") picks 7 different cases (13 of 20 shared), so the string should be pinned
in the launcher (Q3). This round's experiments use only the **613 cases that are training under both readings**:
no locked, sealed or quality-0 label was downloaded.

## 2. Lessons from the 14-class attempt (D9/D10 → D25, `trillium/icx14`)

`trillium-results/icx14/job2/results/` holds the training log of the cancelled run:
- ImageCAS-X's 14 classes as drawn;
- nnU-Net ResEnc 60 GB plan, 0.5 mm, 256³, batch 2, no mirroring, poly LR over 1000 epochs;
- train 560 + val 80 (640 in the census).

I parsed every pseudo-Dice line (898 lines; epochs 0–455; the two log files overlap):

| Class | Cases with the class (of 640) | Epochs with pseudo-Dice > 0 | Max | Mean of last 50 logged |
|---|---|---|---|---|
| LM | 630 | 596 (from epoch 130) | 0.921 | 0.904 |
| LAD | 640 | 850 (from 27) | 0.919 | 0.904 |
| LCx | 640 | 843 (from 34) | 0.886 | 0.837 |
| RCA | 640 | 779 (from 61) | 0.938 | 0.925 |
| D1 | 631 | **0** | 0 | 0 |
| D2 | 380 | **0** | 0 | 0 |
| OM1 | 558 | **0** | 0 | 0 |
| OM2 | 243 | **0** | 0 | 0 |
| IM | 147 | **0** | 0 | 0 |
| R-PDA | 594 | **0** | 0 | 0 |
| R-PLA | 589 | 32 (from **424**) | 0.779 | 0.442 |
| L-PDA | 38 | **0** | 0 | 0 |
| L-PLA | 59 | **0** | 0 | 0 |
| Other | 76 | **0** | 0 | 0 |

What this does and does not show:

- **It is not a frequency problem.**
  - D1 is in 631 of 640 cases and R-PDA in 594, and neither ever scored a true positive.
  - R-PLA, which is as common, began at epoch 424.
  - The network kept every branch voxel in the parent class: the trunks' Dice is normal.
- **It is not a compute or memory problem.** 15 outputs ran at 182 s/epoch on Trillium, the same as Janus 0's
  192 s/epoch on Fir with 5. One H100 holds batch 2 at 256³ with 15 channels.
- **It is not proof that branches cannot be learned.**
  - The run stopped at epoch 455 with the LR still at 0.0058.
  - R-PLA's late take-off says the branch classes may come in late, one by one. My Round-9 note showed that thin
    structures need the full schedule ([[Atlas - Validation pseudo-Dice of the four main vessels flattens by epoch
    100-200, but thin structures need the full schedule]]).
  - nnU-Net's per-sample soft Dice with `batch_dice: False` pushes any class that is absent from a patch to predict
    nothing. Whether this is the cause is a hypothesis, not a measurement.
- **What it does show: a from-scratch, 15-class, ordinal-label network is a ≥ 46 GPU-h bet with no partial result.**
  Half a schedule produced no usable branch at all.

**Lessons adopted:**
1. Start the branch outputs from a model that already segments the tree (§5.2), not from nothing.
2. Merge confusable ordinal siblings into one type, so a class's positives are not split three ways (§3.3).
3. Keep a no-GPU baseline that cannot be worse than Janus 0 on the vessels (Arm N).
4. Score at a fixed epoch budget, with an early read at epoch 250 that is report-only (§7).

## 3. What ImageCAS-X gives a 1-F model (CPU, 613 training cases)

Code: `experiments/Atlas/j1f/` (`split.py`, `fetch_620.py`, `census.py`, `summarise.py`, `ordinal_rule.py`). Full
numbers: [[Atlas - J1F - ImageCAS-X gives branch types cleanly, and ordinals follow origin order]]. Labels only; no CT.

### 3.1 Frequency, size and calibre

⟨TABLE31⟩

- **Calibre.** Diameter is 2 × the whole-tree distance transform, sampled on each class's skeleton. ImageCAS-X's
  labelled branches are ⟨CAL⟩ mm across at the median, which is about ⟨CALV⟩ voxels at 0.5 mm.
  - The 10th percentile sits at the grid floor (1.0 mm), so the smallest branches are at the resolution limit already.
  - Septals, SN and conus are not labelled anywhere in ImageCAS-X, so their calibre cannot be measured here. It is
    measured on the first extended reads (§4.4, trigger E1).
  - I found no findable published table of septal, SN or conus calibre to cite instead. Dodge et al. 1992
    (doi:10.1161/01.CIR.86.1.232) reports segment diameters, but I could not check its branch table, so I do not use it.
- **Imbalance.** Each branch class holds ⟨IMB⟩ of the tree's voxels. The tree is about 0.05 % of the volume.

### 3.2 ImageCAS-X draws only what it names

⟨EP31⟩

**Consequence for partial labels:** in an ImageCAS-X case, a septal, SN, conus or RMA voxel is labelled **background**.
- It is not "LAD, branch unknown". The correct training target for an ImageCAS-X background voxel is the **set**
  {background, S, SN, Conus, RMA}.
- A plain one-hot background teaches the network that septals are background. Pool extended reads would then be
  fighting 620 cases of contrary evidence.
- In phase 1 these four classes are not in the head, so the problem does not arise. In phase 2 the marginal loss
  handles it (§4.3).

### 3.3 Ordinals follow origin order, so a network can learn types

⟨ORD33⟩

### 3.4 "Other" and D3

⟨OTH34⟩

### 3.5 Dominance and the PDA/PLB question

⟨DOM35⟩

## 4. Data and the partial-label strategy

### 4.1 Classes: what the network outputs, and what 1-F reports

| Reported class (D45) | Network output | How the reported class is made |
|---|---|---|
| LM, LAD, LCx, RCA | same | direct |
| D1, D2, D3 | **D** | D components ordered by origin along the LAD → D1, D2, D3; a 4th and later → LAD (Q2) |
| S1, S2, S3 | **S** (phase 2) | the same rule along the LAD; S4+ → LAD (Q2) |
| OM1, OM2 | **OM** | the same rule along the LCx; OM3+ → LCx (Q2) |
| Ramus | **Ramus** | direct (ImageCAS-X IM) |
| PDA | **PDA** | direct, R- and L- alike (Q1) |
| PLB | **PLB** | direct, R- and L- alike (Q1) |
| SN, Conus, RMA | **SN, Conus, RMA** (phase 2) | direct |

The network has 10 outputs in phase 1 (background, 4 vessels, D, OM, Ramus, PDA, PLB) and 14 in phase 2. The ordinal
step is a small CPU post-process on the predicted label map:
- components of each type, at least 20 voxels;
- origin = the geodesic distance from the LM (left) or the RCA ostium (right) along the predicted tree;
- the components are then ordered by origin.

§3.3 measures what this rule costs against ImageCAS-X's own ordinals.

**Why types and not ordinals:**
- the network never has to tell D1 from D2 by local appearance;
- the positives of D1 + D2 + D3 train one class (the D type is in ⟨DTYPE⟩ of cases, against D2's ⟨D2SHARE⟩);
- the rule cannot produce the ordinal errors a network makes, such as two D1s or a D2 without a D1;
- it reuses `src/segtrain/namer.py`'s skeleton and geodesic machinery.

### 4.2 Training targets by source

Each training voxel gets a **set** of allowed classes. A singleton set is an ordinary label.

| Source | Phase | Vessel voxels | Background voxels |
|---|---|---|---|
| **ImageCAS-X 620** | 1, 2 | LM, LAD, LCx, RCA; D1/D2/LAD-side Other → **D**; OM1/OM2/LCx-side Other → **OM**; IM → Ramus; R-/L-PDA → PDA; R-/L-PLA → PLB. All singletons. "Other" touching both sides or neither → ignore | phase 1: {bg}; phase 2: **{bg, S, SN, Conus, RMA}** |
| **Pool read, 4-class** (D25 reads) | 2 | LAD → {LAD, D, S}; LCx → {LCx, OM, Ramus, PDA, PLB, SN}; RCA → {RCA, PDA, PLB, SN, Conus, RMA}; LM → {LM} | **{bg, S, SN, Conus, RMA}**: a reader cutting a TotalSegmentator seed down to four vessels may leave small branches out, exactly as ImageCAS-X does |
| **Pool read, extended**, branch group marked complete | 2 | singletons for the classes drawn; the parent's remaining voxels → {parent} | {bg} plus the classes of any group *not* marked complete |
| **Pool read, extended**, group not marked complete | 2 | drawn classes are singletons (a drawn branch is evidence); the parent's remaining voxels keep the 4-class set for that group | as above |
| Any pool read | 2 | D40: voxels in ≥ 2 classes → ignore | — |

An extended read's ordinals are merged into types for training (D1–D3 → D, S1–S3 → S, OM1–OM2 → OM). They are used
only for scoring, where they also measure how often readers' ordinals agree with the §4.1 rule.

Two points about this table:
- **The "complete" flag is the crux.** D38 means an empty S1 is accepted, so an empty class is ambiguous: "no septal
  here" and "I didn't draw septals" look the same. Without a per-group "this group is complete" flag, an extended read
  can only ever supervise the classes it drew positively. This is Q4, a small change to #280's build.
- **The 4-class read sets follow D25 by origin.** An LCx-origin PDA is LCx territory, and an SN arising from the LCx is
  LCx territory.

### 4.3 The loss

- **Phase 1 needs no new loss.** Every ImageCAS-X target is a singleton or ignore, so the stock nnU-Net CE + Dice with
  the ignore label applies. The only new code is the derived labels, the head surgery (§5.2) and hierarchical decoding.
- **Phase 2: the marginal loss of Shi et al.** The CE term is −log Σ_{c∈S(v)} p_c(v), summed over a voxel's allowed
  set. The Dice term is computed per sample, only on the classes that sample supervises, with the set members' mass
  merged into the parent or background channel.
  - Source: Shi, Xiao, Chen, Zhou, *Marginal loss and exclusion loss for partially supervised multi-organ
    segmentation*, arXiv:2007.03868 (Medical Image Analysis).
  - **Table 3:** on a union of one fully and four partially labelled abdominal CT sets, marginal CE + marginal Dice
    reached mean Dice **0.921**, against **0.874** for the same network trained on the fully labelled set only
    (rCE + rDC). Adding the exclusion loss gave **0.931**.
  - **Table 6:** the gain grows as fully labelled data shrinks. That is our case: no case has every class.
  - The exclusion loss is not adopted in phase 2. Coronary classes touch at every bifurcation, so "no overlap" is weak
    information there, and D39/D40 already handle overlaps in reads.
- **Alternatives, not adopted for phase 2:**
  - **DoDNet** (Zhang, Xie, Xia, Shen, arXiv:2011.10217): a dynamic head conditioned on the task. It needs a task
    per dataset, and our partial labels vary per read, not per dataset.
  - **Staged class addition without set-valued targets**, i.e. fine-tuning on extended reads only. It forgets the
    620 unless ImageCAS-X is replayed, and replaying ImageCAS-X with one-hot background re-teaches "septal =
    background" (§3.2).

### 4.4 How many reads before a class is trained, emitted or reported

Three thresholds, per class, counted in **patients**:

| Threshold | Rule | Why |
|---|---|---|
| **Train** (phase 2 includes the class's positives) | ≥ 30 trainable patients (not sealed, not D35, not reserved) with an extended read that marks the class's group complete | The phase-2 run is ≈ 15 GPU-h. Below about 30 patients a learned class is in the regime where the project's own learned namer lost to rules at 5–40 training cases ([[Bridge - A generic learned vertex labeller is worse than structured rules at 5-40 training cases]]). This is an opinion, anchored there, and the judge may move it |
| **Report** (a per-class number appears in results) | ≥ 40 evaluation patients carrying the class in the reference | At a detection rate near 0.8, n = 40 gives a 95 % binomial half-width of 1.96·√(0.16/40) = **0.12**. Below 40, the class is pooled into "rare branches" with its count |
| **Emit** (1-F outputs the class; annotators may see it as a prelabel) | Reported, **and** class tF1 ≥ 0.70 **and** branch detection recall ≥ 0.75 on the evaluation set | 0.70 is D18's review trigger for LAD/LCx/RCA. Below the floor, the class's voxels go back to its parent in the output, so 1-F is never worse than a four-class answer on that branch |

For S, SN, Conus and RMA, the evaluation set can only be **pool extended reads**: ImageCAS-X never labels them, by D22.
They are scored on extended reads of the **D35 decision set** (never trained on). So:
- **if D35 reads are made in extended mode, phase 2 can be decided on them;**
- otherwise, those classes cannot be reported before a separate held-out set exists.

This is Q4(b) for the lead.

## 5. Architecture and recipe

### 5.1 Two arms in phase 1, decided on the locked 100

| | **Arm N: namer on Janus 0's tree** | **Arm T: type network** |
|---|---|---|
| Vessel voxels | Janus 0's own prediction (fixed; already on Fir in `$SCRATCH/icx4/predictions`) | A new network, warm-started from Janus 0 |
| Branch types | A CPU segment classifier on the predicted tree's skeleton graph, trained on the 620's ImageCAS-X labels | The network's 5 type outputs, decoded hierarchically |
| Ordinals | §4.1 rule | §4.1 rule |
| Four vessels vs Janus 0 | **Identical by construction.** The namer only subdivides a territory, never moves a voxel between territories | Must pass the guard (§7) |
| GPU | **0** | ≈ 28 GPU-h |
| Code | extend `src/segtrain/namer.py` | derived labels + head surgery + hierarchical decoding |

Arm N exists because the issue's "segment-then-label" option is cheap here. It gives 1-F a result even if Arm T repeats
icx14. External evidence that graph labelling of a given tree is strong:
- **CPR-GCN** (Yang, Zhen, Chi, Zhang, Hua, CVPR 2020, arXiv:2003.08560), **Table 3:** on 511 CCTA trees (five-fold
  CV), segment-labelling F1 0.909 (D), 0.914 (OM), 0.909 (RI = ramus), 0.964 (S), 0.938 (R-PDA), 0.945 (R-PLB);
  mean 0.955. The same table gives TreeLab-Net 0.871 mean and a registration method 0.857.
- **TreeLab-Net** (Wu et al., Int J CARS 14:271–280, 2019, doi:10.1007/s11548-018-1884-6): bidirectional tree-LSTM
  on centreline features. The abstract reports side-branch AUC > 0.90 (D, OM, R-PLB).

Caveats:
- Both label **groups** (D, OM, S), not ordinals (D1/D2). This supports §4.1's types-then-ordinals split.
- Both label a **given** tree. A branch the segmentation missed cannot be named, and Janus 0 never segments septals,
  SN or conus (§3.2). **Arm N therefore cannot deliver phase 2's classes.** That is why Arm T is not optional in the
  long run, only in the first decision.

The Arm N classifier is a gradient-boosted classifier on per-segment features: parent class, origin distance, length,
mean calibre, direction relative to the parent, and side of the parent relative to the heart's long axis. It is
trained on the 620's labels and runs on CPU. Bridge's evidence ("structured rules beat a generic learned labeller at
5–40 cases") does not bind at 620 cases.

### 5.2 Arm T's recipe

| Item | Setting | Source |
|---|---|---|
| Start | **Janus 0's `checkpoint_final.pth`**, all layers, **head expanded 5 → 10 by parent copy**: each new type copies its parent's weights and bias, and every member of a decode group gets bias − log k (k = the group's size: LAD with D → 2; LCx with OM, Ramus → 3; RCA with PDA, PLB → 3). The same is done for every deep-supervision output. Every group's summed probability then equals Janus 0's (max error 2·10⁻¹⁵) | `experiments/Atlas/j1f/head_init_check.py`, output in `head_init_check.out` |
| Decoding | **Hierarchical:** decode group = argmax of summed group probabilities; then type = argmax within the group | same check, on random logits: a plain argmax over the 10 outputs moves 2.5 % of voxels to another group at init (3.7 % with phase 2's 14); hierarchical decoding moves 0. On real, confident voxels the plain-argmax error would sit at boundaries; its size there is not measured, and it does not matter, since 1-F never decodes that way |
| Decode groups vs the collapse | The decode groups are an initialisation device: PDA and PLB start in the RCA group, so an LCx-origin PDA is decoded as PDA once its mass wins. The **four-class collapse used for scoring is by origin** (D25), on the decoded label map | §6 |
| Plans | Janus 0's plans moved to the new dataset (`nnUNetv2_move_plans_between_datasets`), field for field: ResEnc 60 GB, 0.5 mm, 256³, batch 2, mirroring off | Janus 0 (#43) |
| Data | ImageCAS-X **620** (D45), derived type labels (§4.2), dataset 730; fold-0 val = the **locked 100**, never trained on | D45 |
| Trainer | the A17a fine-tune trainer (full load; the head loaded with the surgery above; 2500-iteration warm-up then poly), peak LR 1e-2 | Round 10 A36 |
| Epochs | **500**, with checkpoints at 250 and 500. Decided at 500; 250 is report-only | §2: icx14's only learned branch appeared at epoch 424; thin structures need the full schedule |
| Seeds | **one.** The phase-1 decision compares fixed outputs (a model decision, A37's clarification), so it needs no seed term | A37 |
| Why not warm from Janus 1-L | 1-L does not exist yet. If 1-L is adopted before Arm T starts, Arm T starts from 1-L instead, with no other change. The head surgery is identical | D45 |
| Why not from scratch | icx14 (§2); from scratch costs ≈ 55–60 GPU-h against ≈ 28 | #43 timings |

**Why parent-copy matters.** In icx14 the branch outputs started random and stayed at zero. Here every branch output
starts as its parent, at exactly Janus 0's probability for that territory. The first gradient step only has to move
mass *within* a territory, from the parent to a type, where the labels say so. The four-vessel answer is Janus 0's on
the first iteration and drifts only as far as training pushes it. That drift is what §7's guard measures.

### 5.3 Phase 2 (after the triggers in §4.4)

- **Arm T2:** warm from the phase-1 winner, if that is T; from T's checkpoint if N won. The head expands 10 → 14 by the
  same parent copy: S from LAD; SN, Conus and RMA from RCA.
- Data: ImageCAS-X 620 + every trainable pool read, 4-class and extended, under §4.2's sets and §4.3's marginal loss.
- 250 epochs, ≈ 15 GPU-h.
- Decided on D35 (pool) and the locked 100 (guard), as in §7.

## 6. Metrics

All scoring uses the pinned `tf1.py`, unchanged. A wrapper sets its module-level `CLASSES` to the reported classes
(1–18). `ordinal_rule.py` shows the mechanism on 613 cases. A file hash check refuses any other `tf1.py`.

| Metric | Definition | Role |
|---|---|---|
| **Four-vessel tF1** | 1-F's output collapsed **by origin** (D25) to LM/LAD/LCx/RCA; tF1 @ 1.5 mm against ImageCAS-X collapsed by `territory.to_four`, ostia from the in-job TotalSegmentator aortas | guard vs Janus 0 (§7) |
| **Per-class tF1** | the same tF1, per reported class (D1, D2, D3, OM1, OM2, Ramus, PDA, PLB on ImageCAS-X) | primary branch metric |
| **Branch macro tF1** | per case, the mean over the branch classes present in the reference; then the mean over cases | primary endpoint |
| **Branch detection** | a reference branch (a class's connected component ≥ 20 voxels) is detected if ≥ 50 % of its centreline is covered by predicted vessel of **any** class within 1.5 mm; recall over reference branches, precision over predicted branch components | separates "missed" from "misnamed" |
| **Naming accuracy** | among detected reference branches, the share whose covered centreline carries the right class (majority vote); plus the sibling confusion matrix (D1/D2/D3, OM1/OM2, PDA/PLB) | what Arm N vs T is really about |
| **Dice** | per class | report only (A28) |

**Classes without ImageCAS-X labels** (S1–S3, SN, Conus, RMA, and D3 apart from §3.4's derivation):
- They are never scored on the locked 100 for absolute numbers.
- On the locked 100 they are reported only as **false-positive burden**: the predicted volume and component count of
  each, since every such voxel is ImageCAS-X background. That number has no meaning for accuracy, so it is reported
  only.
- They are scored on extended reads of D35 against both reads, with the same metrics, once §4.4's report threshold
  holds.

## 7. Pre-registered decision on the locked 100 (phase 1)

Scored on the locked 100 (val 80 + the 20 locked open-36), with the in-job TotalSegmentator aortas. Provisional cases
and flagged trees are excluded (A1a/A1b). Both arms and Janus 0 are fixed predictions, with a paired patient bootstrap
(10 000 resamples, 95 %).

| # | Check | Rule |
|---|---|---|
| **V1** | Four vessels hold (Arm T only; Arm N holds by construction, and the scorer asserts Δ = 0 for N) | Δ macro four-vessel tF1 (T − Janus 0): **lower 95 % bound > −0.02**, **and** no class (LM, LAD, LCx, RCA) mean Δ < −0.03. These are A38 G2's numbers, the agreed forgetting margin, kept so that 1-L and 1-F are held to the same line |
| **V2** | Not shortening vessels | No class's four-vessel **centreline recall** falls by more than 0.02 against Janus 0 (A38 G3) |
| **B1** | Choose T over N | T passes V1–V2, **and** Δ branch macro tF1 (T − N) has its **lower 95 % bound > 0**. Otherwise **N** is phase 1's 1-F. Ties go to N: it is cheaper and holds the vessels exactly |
| **B2** | Which classes 1-F emits | Per class, on the chosen arm: §4.4's emit rule (reported with ≥ 40 locked patients, tF1 ≥ 0.70, detection recall ≥ 0.75). Classes below the floor are folded back into their parent in the output, and listed |
| **B3** | Epoch 250 (T only) | Reported, never decides. If epoch 250 already passes B1, that is noted for phase 2's epoch budget |
| **B4** | Open-36 vs val 80 | The 20 locked open-36 are reported apart. A sign reversal of B1's Δ between val 80 and the 20 is reported, not acted on (A26's rule) |
| **R** | The read | D34: the chosen arm is read as the next Janus number in this track. The other arm is never shipped in its place |

**Outcomes that change the plan:**
- **T fails V1 only.** Rerun T once with ImageCAS-X's four-vessel classes weighted 2:1 in the Dice term. If that fails
  too, N stands.
- **N's branch macro tF1 < 0.60 and T fails B1.** Neither arm is a usable 1-F. Phase 1 is reported as negative, and
  Round 2 reopens the architecture. Training an ordinal network directly is *not* the default fallback (§2).
- **T's branch classes are all zero at epoch 250** (icx14 repeated). Report it. Epoch 500 still runs, since it is the
  same job. Round 2 is then told that parent-copy did not cure it.

**Power.** I do not claim a minimum detectable effect for B1 this round. Branch tF1's per-case spread is unknown until
Arm N runs (CPU), and it should be measured before the judge fixes B1's margin. Round 2 can do this from Arm N's
output alone.

## 8. Fir jobs (account `def-aso22`, the lead runs every job)

They need a launcher `trillium/janus1f`, copied from `trillium/icx4` (the same Fir profile, sealed-case filter and A1c
guard). It should be built as a `role:swe` issue if this plan is adopted (§9). The commands below assume it.

### Job F0: login node, CPU, minutes

```sh
module load StdEnv/2023 python/3.11.5
cd $SCRATCH/asclepius && git -C repo pull --ff-only
mkdir -p experiments && rm -rf experiments/janus1f && cp -r repo/trillium/janus1f experiments/janus1f
cd experiments/janus1f && JANUS1F_DRYRUN=1 ICX4_CLUSTER=fir ./janus1f
```

The printout must show:
- `locked100 sha256 bbd9c687…d5895 (= track 1-L)`;
- `train 620, locked 100, sealed 0, quality-0 0`;
- `types: D <n>, OM <n>, Ramus <n>, PDA <n>, PLB <n>; Other ignored <n> components`;
- `Janus 0 checkpoint found`, `Janus 0 predictions: locked 100 of 100`;
- `aortas: locked 100 of 100`;
- `= frozen hash (A1c)`.

### Job N: Arm N, CPU only (≈ 2–3 h on 16 cores, 0 GPU-h)

```sh
ARM=namer ICX4_CLUSTER=fir JANUS0=$SCRATCH/icx4 JANUS1F_WORK=$SCRATCH/janus1f_n ./janus1f
# sbatch header it writes: --account=def-aso22 --cpus-per-task=16 --mem=64G --time=04:00:00 (no GPU)
```

What it does:
1. Trains the segment classifier on the 620's ImageCAS-X labels, on CPU.
2. Names Janus 0's locked-100 predictions.
3. Scores §6 for Arm N and Janus 0.

### Job T: Arm T, GPU (≈ 28 GPU-h; ceiling 2 × 23:50 = 47.7)

```sh
ARM=types SEED=1 EPOCHS=500 CHAIN=2 ICX4_CLUSTER=fir JANUS0=$SCRATCH/icx4 JANUS1F_WORK=$SCRATCH/janus1f_t ./janus1f
grep SBATCH $SCRATCH/janus1f_t/job.sh   # --gpus-per-node=h100:1 --cpus-per-task=12 --mem=280G --time=23:50:00 --account=def-aso22
./janus1f status $SCRATCH/janus1f_t     # after ~2 h: s/epoch, expect 185-200 (Janus 0: 192 on Fir; icx14's 15 outputs: 182 on Trillium)
```

**Costing:**

| Step | Time |
|---|---|
| Preprocessing (CPU in job 1) | ≈ 0.7 h (icx14: 0.68) |
| 500 epochs at ≈ 192 s | 26.7 h |
| Prediction on the locked 100 | ≈ 1 h |
| **Total** | **≈ 28 GPU-h** |

Both jobs can run at once: N needs no GPU.

**When both are `DONE`:**

```sh
./janus1f collect $SCRATCH/janus1f_n && ./janus1f collect $SCRATCH/janus1f_t
./janus1f decide $SCRATCH/janus1f_n $SCRATCH/janus1f_t   # applies §7 V1-V2, B1-B4; writes decision.json and DECISION.md
```

**Send back on #303:** both `results/` folders and `decision.json`. No volume leaves Fir.

**Phase 2 (Job T2, ≈ 15 GPU-h):** only after §4.4's train trigger holds for at least one of S, SN, Conus, RMA, and Q4
is answered. Its commands are written in the round that adopts it.

**Total committed now:** ≈ 28 GPU-h (ceiling 48) and about 3 CPU-hours.

## 9. Code that must ship (`role:swe`, to open if adopted; not opened by this candidate)

1. **`trillium/janus1f` launcher** (from `icx4`):
   - dataset 730 derived labels (§4.2, phase 1);
   - head surgery (§5.2) applied when the A17a trainer loads Janus 0, including the deep-supervision heads;
   - hierarchical decoding in prediction;
   - Arm N's segment classifier (an extension of `src/segtrain/namer.py`);
   - the §4.1 ordinal step;
   - the §6 scorers (the `tf1.py` class wrapper, branch detection, naming accuracy);
   - `decide`.
   - Self-tests on synthetic trees; never a sealed case.
2. **Phase 2 only:** the marginal CE + masked Dice loss (§4.3) as an nnU-Net trainer. A per-read "branch group
   complete" flag in SegQueue14's extended reads (#280 follow-up, Q4) and in `segqueue14-export`.

## 10. Questions for the lead

- **Q1. PDA and PLB in a left-dominant heart.** ImageCAS-X labels L-PDA/L-PLA in ⟨LPDA⟩ of the 613 training cases.
  - D44 lists PDA and PLB under the RCA, and #280's default collapse sends them to the RCA always.
  - D25 (and Janus 0's training labels) send a left-sided PDA/PLA to the **LCx**.
  - **Recommendation: name by position, collapse by origin.** A PDA is "PDA" whether it arises from the RCA or the
    LCx. In the four-class collapse it takes its parent's class, as D1/D25 already say for every branch. This keeps
    1-F's four-vessel output comparable with Janus 0 and 1-L. The alternative makes an LCx-origin PDA count as RCA,
    which moves voxels across territories against every four-class label the project has.
  - The same applies to an SN arising from the LCx.
  - If the lead prefers "always RCA", 1-F still names the same branches. Only the collapse and the V1 guard's reference
    change, and V1 would then compare against Janus 0 relabelled the same way.
- **Q2. D4+, S4+ and OM3+.** D44 has no class for them. This plan returns them to the parent (LAD, LCx). The
  annotator instructions in #280 should say the same, or reads and 1-F will disagree on every 4th diagonal.
- **Q3. Pin the locked-100 string** as `'asclepius-janus1-locked100:' + 'cNNNN'`, the reading all 1-L advocates used
  (sha256 `bbd9c687…d5895`). The other reading ("69") changes 7 of the 20.
- **Q4.** (a) Add a per-group "complete" flag to extended reads (§4.2). Without it, phase 2 can learn only from the
  branches drawn positively. (b) Ask D35 patients' reads to use the extended classes. Otherwise S, SN, Conus and RMA
  have no evaluation set outside the seal (§4.4).

## 11. What would change this plan

| Observation | Change |
|---|---|
| Arm N's branch tF1 already clears B2's floor on most ImageCAS-X classes, and T fails B1 | 1-F phase 1 is N; GPU goes to phase 2 only |
| T's branches are still zero at epoch 250 | Parent-copy is not enough: Round 2 tests a type-only head (5 types, no vessels) or class-balanced patch sampling |
| §3.3's rule disagrees with ImageCAS-X's ordinals on more than 5 % of branches | Ordinals become a learned step (on the graph, in Arm N's classifier), not a rule |
| Extended reads never mark groups complete (Q4a declined) | Phase 2 uses positive-only supervision for S/SN/Conus/RMA (set {class, parent, bg} on unmarked voxels), and the emit floor rises to tF1 ≥ 0.80 |
| The lead answers Q1 "always RCA" | Only the collapse and V1's reference change |
| 1-L is adopted before Job T starts | Job T warm-starts from 1-L |

## 12. Evidence used

| Claim | Evidence |
|---|---|
| icx14 never learned 9 of 10 branches in 455 epochs | `trillium-results/icx14/job2/results/training_log_*.txt`, parsed in §2 |
| ImageCAS-X's class frequencies, calibre, ordinals, "Other" and dominance on the 613 | `experiments/Atlas/j1f/` + [[Atlas - J1F - ImageCAS-X gives branch types cleanly, and ordinals follow origin order]] |
| Parent-copy head + hierarchical decoding reproduces Janus 0 exactly at init | `experiments/Atlas/j1f/head_init_check.py` (output `head_init_check.out`) |
| Marginal loss beats training on the fully labelled set alone | Shi et al., arXiv:2007.03868, Tables 3 and 6 |
| Graph labelling of a given coronary tree: F1 ≈ 0.91–0.96 for D/OM/RI/S/PDA/PLB groups | Yang et al., CVPR 2020, arXiv:2003.08560, Table 3; Wu et al. 2019, doi:10.1007/s11548-018-1884-6 |
| ImageCAS-X: 800 cases, segment labels, centrelines, dominance | Bransby et al., arXiv:2608.30404; Zenodo 10.5281/zenodo.21887809 (`Descriptors.xlsx`: dominance per scan) |
| PDA/PLB are named by position in the standard segment model (L-PDA and L-PLB are segments of their own) | SCCT guidelines, Leipsic et al., J Cardiovasc Comput Tomogr 8:342–358, 2014, doi:10.1016/j.jcct.2014.07.003, 18-segment model (segment 15 L-PDA, 18 L-PLB, 17 ramus; checked through a reproduction, PMC11395889 Fig. 1) |
| nnU-Net ResEnc presets | Isensee et al., *nnU-Net Revisited*, MICCAI 2024, arXiv:2404.09556 |
