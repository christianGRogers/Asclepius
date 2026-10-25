---
tags: [plans, candidate, round10, fir, four-class, janus, D35, D27, seal, fine-tune, power]
author: Foxtrot
round: 10
version: 6
updated: 2026-10-25
issue: christianGRogers/Asclepius#113
---

# Foxtrot v6: spend the 161 open pool patients on purpose. Seal 200 now, decide on the seal's own reserve tail, warm-fine-tune Janus 1 with ImageCAS-X rehearsal

## 1. Thesis

Janus 0 is good (val-80 decisive tF1 0.909; [[icx4 - Results]]). The recipe question is settled. What Round 10 must
settle is how a fixed, small set of pool patients is split between three uses:
- **acceptance** (the seal, D27);
- **decisions** (D35);
- **training** (A17).

Each use's power depends on the size of the others. Counted on real patients (D32), that set is far smaller than the
figure D35 was decided on:

1. **There are 161 non-sealed primary patients, not about 347, and 100 of them are the seal's extension reserve.**
   Only **61** are open, and 43 of those are one source (Taiwan AI CUP). "About 347" is the retired name-heuristic count.
   ([[Foxtrot - After the seal and its reserve only 61 primary pool patients are open, so the D35 set must come from the extension order]])
2. **On Janus 0's own spread, the 150-patient seal is under-powered even in the best case.** A model as good as a second
   reader passes A10 with P = 0.78 if the pool is like val, 0.51 at the A31 trigger line, and 0.23 if the pool is
   1.5× more varied. At 200 patients: 0.91 / 0.74 / 0.42.
   ([[Foxtrot - On Janus 0's spread the 150-patient seal passes a human-level model 78 percent of the time, so it should grow to 200 now]])
3. **About 50 decision patients is the right size, and only for model decisions.** Fifty patients resolve "does this
   checkpoint beat Janus 0 on pool reads" to 0.02–0.05 macro tF1. Recipe A/B questions stay above about 0.04 at any
   size, because the seed term (A22) dominates.
   ([[Foxtrot - A 50-patient decision set resolves model choices to 0.02-0.05 tF1, but recipe choices stay above 0.04 because seed noise dominates]])
4. **The literature says:**
   - warm-start each wave cheaply, and keep the old domain in the mix, or nnU-Net forgets it;
   - retrain from scratch once at the end;
   - expect seed-started reads to agree more with each other and less with the truth.
   ([[Foxtrot - Fine-tuning catches up with less compute, forgets without rehearsal, and team reads started from a seed agree more and are less accurate]])

**So the plan:**
- **Seal → 200 now**, along its pre-registered order (positions 1–50), before any read exists.
- **D35 = extension positions 51–100** (50 patients, 72 volumes, 8 sources). This is a draw already salted, ranked
  within source and frozen since D32, so no new salt is chosen.
- **Janus 1 = a warm fine-tune of Janus 0 on ImageCAS-X train 560 + the open pool reads**, two seeds (≈ 30 Fir GPU-h).
  It is decided on D35 as a model decision, with a val-80 forgetting guard.
- **Two measurements before any pool read (Job 1, ≈ 5 GPU-h):**
  - how a fully seed-anchored read would sit against ImageCAS-X's convention, measured on val 80;
  - Janus 0's per-source domain check.
- **The from-scratch retrain** (Crucible P4) is costed and kept for the final model, where D35 decides it against the
  best warm model once.

The 250-patient seal and a D35 drawn from the open patients are kept as the lead's alternative (§11, Q1), with their
numbers.

## 2. Model and recipe (unchanged; settled)

Janus 0 is `trillium/icx4`: nnU-Net v2.8.1 ResEnc (`nnUNetResEncUNetPlans_60G_iso05`), 0.5 mm iso, 256³, batch 2,
mirroring off, default window, DiceCE, 1000 epochs, ImageCAS-X 560/80 collapsed by D25 (`territory.py`), on Fir
(`def-aso22`). It is the base model (#113, "settled").
- **No architecture change.** nnU-Net Revisited (Isensee et al., MICCAI 2024, arXiv:2404.09556, **Table 1**): CNN
  U-Nets (ResEnc, MedNeXt) match or beat the Transformer and Mamba models tested. This corrects my v5 wording,
  "beat every".
- **Lumen width (the A27 Dice row) is a convention, not an error.** Janus 0 draws the boundary about one voxel inside
  ImageCAS-X's: tolerant Dice 0.97 against 0.88, volume ratio 0.87, centreline recall 0.94. That costs Dice, not tF1.
  **My v5 F7.1 premise ("loses tree") was wrong**, and Atlas's check showed it.

## 3. The D35 decision set

### 3.1 What it is drawn from: the counts, reconciled

| Primary stratum (real patients, D32) | Patients | Volumes |
|---|---|---|
| Sealed (D27/D32) | 150 | 305 |
| Extension positions 1–50 (seal → 200) | 50 | 72 |
| Extension positions 51–100 (seal → 250) | 50 | 72 |
| Extension position 101 | 1 | 1 |
| Open | 61 | 69 |
| **Non-sealed primary, total** | **161** | 214 |

Beside these: ImageCHD 63 open (report-only stratum, D29) and 74 suspect-spacing patients (outside A10 until
re-gridded).
- **"About 50 of about 347" (#43, D35)** is 517 − 150 − 20, where 517 is the name-heuristic count that D32 retired.
- **"198 open" (wave-1 note)** = 61 + 63 + 74.
- **D35's 15 % and its 50 disagree.** 50 is 31 % of the 161 non-sealed primary patients. This plan keeps the count
  the lead saw (50) and flags the percentage (§11, Q2).

### 3.2 The draw (proposed)

| Item | Value |
|---|---|
| Set | `primary.extension_order[50:100]` of `configs/segqueue14/sealed-pool-2026-10.json` (sha256 pinned, D32) |
| Salt | The seal's own: `asclepius-sealed-round9-pool:`. **No new salt**, so nothing can be salt-shopped |
| Draw | Patient level (real patients, `segtrain.pool_seal.ingest_patient`); salted sha256 rank **within source**, round-robin across sources (Bridge's draw, `experiments/Bridge/r9/seal_pool.py`, rebuilt on real patients by `reseal_d32.py`) |
| Size | **50 patients, 72 volumes** |
| Sources | Kaggle-CAD 9, SDN-cy54ttk3fj 9, Taiwan 9, EpicardialFat 8, VMR 8, TotalSegmentator-cardiac 3, CardiacCT15 2, IDC-RIDER 2 |
| Strata | Primary only: no ImageCHD, ALCAPA or suspect-spacing patient (D29) |
| Frozen | Already. The list is a deterministic function of the pinned seal. `experiments/Foxtrot/r10/d35_proposal.py` writes it, with its hash, to `experiments/Foxtrot/r10/d35_proposal.json`. No read of these patients has been opened: the wave-1 tools refuse them as reserved |
| Never trained on | Enforced by #114 (`role:swe`, opened this round). Today task 716 refuses only the seal, **not the reserve** |
| Scored | Every volume of a D35 patient, both reads, averaged per patient (the patient is the unit of n). Decisive tF1 @ 1.5 mm, A1 (TotalSegmentator aortas), A1c `24441cf8…5254`, flagged trees apart (A1b) |
| Its reads may | decide model questions (§5.4); feed A31's f and k and the seed flag (it is not sealed, so looking is allowed); be reported per source |
| Its reads may not | be trained on, prelabelled, or used to set a threshold that is then validated on them |

**Why this draw rather than a fresh one.** A fresh within-source draw from the 61 open patients would be 70 %
Taiwan. At 50 patients it would leave 11 primary patients to train on. At 15 % (9 patients) it would decide nothing.
Positions 51–100 are better balanced (8 sources) than anything the open set can give. They are already a
pre-registered random draw, so this choice adds no freedom.

### 3.3 The power it buys

From the measured paired noise of two warm fine-tunes from one base (atlas3 F1 − F0: SD of the per-case Δ 0.038
macro), MDE at 80 % power, f = 1 → 1.5:

| D35 question | n = 50 | Reading |
|---|---|---|
| Model decision: checkpoint vs checkpoint (no seed term) | **0.018–0.027** (measured noise) / **0.033–0.049** (scaled to Janus 0's spread) | Resolves the gains fine-tuning should give on a shifted domain (cross-centre drops are 5–8 Dice points in the literature; [[Foxtrot v5]] §8) |
| Recipe decision, 2 seeds per arm (A22) | 0.041–0.061 | Cannot see the < 0.02 recipe effects A22 is about. Do not run such A/Bs on D35 in wave 1 |
| LCx, model decision | 0.041–0.074 | LCx decisions at n = 50 are coarse. They are reported, and do not decide alone |

Doubling D35 to 100 would improve the model-decision MDE by about 30 % and the recipe MDE by under 10 %. It would cost
50 patients that the seal or training needs. **50 is the size.**

### 3.4 Interaction with A30's extension order

- Positions 1–50 → **sealed now** (§4). Positions 51–100 → **D35**. Position 101 → training.
- **The seal can no longer reach 250 by rule.** If wave 1's f/k re-power says 200 is short, that is reported to the
  lead, as Bridge's rule already does at 250. It does not reach into D35, because D35's reads will have been looked
  at by then.

## 4. The acceptance set: extend the seal to 200 now

- **Re-powered on Janus 0's spread** (A31.1). Janus 0's per-class val SDs are recovered from the posted CIs: LM 0.121,
  LAD 0.126, LCx 0.135, RCA 0.079. That is 1.0–1.6× run 1's spread, which Round 9's sizing used.
- P(a human-level model passes A10, all four classes), with LCx binding in every row:

  | | 150 | 200 | 250 |
  |---|---|---|---|
  | f = 1, k = 1 | 0.78 | **0.91** | 0.97 |
  | f = 1, k = 1.2 | 0.66 | 0.85 | 0.93 |
  | f = 1.2, k = 1 | 0.51 | 0.74 | 0.86 |
  | f = 1.5, k = 1 | 0.23 | 0.42 | 0.56 |

- **Recommendation: seal 200 now** (positions 1–50 of the order, 72 volumes), as one explicit PR to the seal file.
  Under D27 this is the lead's (Q1).
  - **Why now:**
    - Bridge's own sizing rule ("200, or 250 if power at 200 < 0.8") already gives 200 at f = k = 1, before any read;
    - extending before reads exist means the extension never depends on seen data;
    - it removes the f/k trigger's 54–71 % false-alarm rate at wave-1 sizes from this step.
  - **Nothing changes for annotators:** these volumes are already in the D23 queue, and the tools already refuse
    them.
- **What 250 would buy:** +0.06 to +0.14 in P(pass). It costs the only well-balanced decision set. If the lead prefers
  250, D35 becomes a 30-patient draw from the open 61 (fresh salt `asclepius-d35-round10:`, already written to
  `d35_proposal.json` as the alternative: 21 of its 30 are Taiwan), and only 31 primary patients remain to train on.
- Wave 1 still measures f and k (A31.1), on the open + D35 patients (n ≈ 111), where Bridge's false-alarm rate is
  about 29 % rather than 54 %. If f or k > 1.2, the power table is re-run and reported to the lead.
- **One file settles the spread.** The real per-case file `$SCRATCH/icx4/r9_tf1_val.json` replaces the CI-derived
  SDs (`repower.py` takes it). Send-back item, §10.

## 5. The pool fine-tune recipe: Janus 1

### 5.1 Warm or scratch: costed in Fir GPU-hours

Fir cost is measured on Janus 0: 192 s/epoch, prediction of 1000 cases 0.8 h, 160 aortas 1.2 h (#43).

| Route | Per seed | Under A22 (2 seeds) | What it can resolve on D35 at n = 50 |
|---|---|---|---|
| **Warm fine-tune from Janus 0** (A17a trainer, 250 epochs = task 716's default) | 13.3 h training + ~1.5 h preprocess/predict/score ≈ **15 GPU-h** | **≈ 30 GPU-h** | vs Janus 0: 0.02–0.05 (model decision) |
| From scratch on ImageCAS-X + pool (Crucible P4), 1000 epochs | 53 h + 2 h preprocess + ~4 h predict/aortas ≈ **60 GPU-h** | ≈ 120 GPU-h | — |
| A warm-vs-scratch recipe A/B, done properly | — | ≈ 150 GPU-h | only differences ≥ 0.04–0.06 |

**Choice: warm for every wave model; scratch once, for the final model.**
- **He, Girshick, Dollár** (ICCV 2019, arXiv:1811.08883, **Fig. 1, Table 1**): random init catches up with
  fine-tuning only at about 5–6× the schedule (R50 40.7 vs 40.9 AP at 5×). With little data it falls far behind
  (1k images: 3.5 vs 9.9 AP, **Figs. 7–8**). Our pool share is little data.
- **Ash & Adams** (NeurIPS 2020, arXiv:1910.08475, **Table 1**): when data grows, warm-started models generalise
  1–7 points worse than fresh ones (classification only). That is the one documented cost of warm-starting, and why
  the **final** model is a fresh retrain, compared once on D35.
- A warm-vs-scratch A/B in wave 1 would cost about 150 GPU-h to resolve only effects ≥ 0.04. Not worth it.

### 5.2 Janus 1's recipe

| Item | Setting | Why |
|---|---|---|
| Start | Janus 0 `checkpoint_final.pth`, full load including heads, 2500-iteration warm-up, then poly (A17a, `nnUNetTrainer_segtrain_finetune`) | A17a; stock nnU-Net re-initialises the heads |
| Plans | Janus 0's, adopted (`segtrain plan --plans-from`), as task 716 does | The warm start is only valid on identical plans |
| Peak LR | 1e-2, the primary arm (A17b). The 1e-3 arm runs **only if** the val-80 forgetting guard fails (§5.4) | Avoids a recipe A/B that D35 cannot resolve (§3.3) |
| Epochs | 250 (task 716's default) | atlas3's 200-epoch fine-tunes on Trillium took 10 h each. 250 fits one 23:50 Fir job |
| **Data** | **ImageCAS-X train 560 (rehearsal) + every trainable pool read**, each read a sample (A11′), sampled uniformly. The pool share is then about 20–30 % of samples | **Lifelong nnU-Net** (González et al., Sci Rep 13:9381, 2023, doi:10.1038/s41598-023-34484-2, **Tables 1–2**): sequential fine-tuning forgets (hippocampus 90.5 → 20.2 Dice), and rehearsal prevents most of it (88.2). That is MRI, not CT, but the mechanism is the same network. **Task 716 trains on pool reads only, so it must gain the ImageCAS-X 560** (role:swe, §9) |
| Pool reads in training | Open primary (61 patients + 1) + open ImageCHD (63), approved double reads. Suspect-spacing volumes only after re-gridding (Q6). **Never** sealed, extension 1–50, or D35 | D27, D35, #114 |
| Seeds | **2** (A and B), concurrent | The first measured σ_seed for a fine-tune; A22's 0.013 is borrowed from from-scratch runs |
| Names (D34) | Seed A is read first → **Janus 1**. Seed B → **Janus 2** | D34: numbered in the order read |

### 5.3 Does task 716 fit?

Partly. It already does the right things:
- adopted plans;
- the A17a trainer with both LR arms;
- the seal by patient;
- reads as samples;
- the split keyed by patient.

Three gaps:
1. **No rehearsal.** ImageCAS-X 560 is not in task 716 (§5.2).
2. **No held-out guard** for the reserve and D35 (#114).
3. **Its SLURM path is Trillium-shaped.** `segtrain scinet submit` has no Fir profile, and `gpus_per_node` is an
   integer, so it cannot express `h100:1`.

The proven Fir path is the icx4 launcher. So the plan asks for a **`trillium/janus` launcher** built on `icx4`'s Fir
profile, which runs task 716's trainer and data (role:swe, §9).

### 5.4 How Janus 1 is decided (pre-registered)

All scores are decisive tF1, A1/A1c, flagged trees apart. Δ = Janus 1 − Janus 0, paired per patient (D35) or per case
(val 80).

| Check | Set | Rule | If it fails |
|---|---|---|---|
| **Forgetting guard** | val 80 | Lower 95 % bound of Δ macro ≥ −0.02, and no class mean Δ < −0.03 | Run the 1e-3 arm (A17b; same data, 2 seeds) and apply the same rules to it. If that fails too, Janus 0 stays, and the rehearsal ratio goes to Round 11 |
| **Pool gain** (model decision) | D35, ≥ 40 of 50 patients double-read | Δ macro > 0 with its 95 % CI excluding 0. Seed term included: σ̂ from Janus 1 vs Janus 2 on D35, floor 0.013 | "Not shown better": Janus 0 stays the working model; the next wave adds reads and repeats |
| Confirmation | open-36 | Same sign (A26) | A reversed sign is reported, not adopted |
| FP gate | D35 + val 80 | FP components per case ≤ 1, raw (A15) | Reported; A15 binds only on the final model |
| Report only | D35 | per class (LCx decides nothing alone at n = 50); per source; **seen vs unseen sources** (M&Ms, Campello et al., IEEE TMI 2021, doi:10.1109/TMI.2021.3090082, Table IX and Fig. 8: models degrade most on centres absent from training) | — |

- **Which seed ships:** Janus 1 (seed A), pre-registered. It is never "the better of A and B on D35", because picking
  the winner on D35 biases its D35 score upward.
- **A22 and D28.** This is a model decision (this checkpoint vs that one, on D35), so the seed term is reported but
  does not require a second Janus 0. A22 binds recipe claims, and §3.3 shows those cannot be resolved here anyway.
  **The judge is asked to state this distinction in A22.** Otherwise, D28's fallback ("the first retrained decision
  adds a second seed to its control") would make the first pool decision wait on a 60 GPU-h retrain of Janus 0.

## 6. What team reads measure: seed anchoring, convention, domain

### 6.1 The convention of seed-started reads

- **Width does not matter to A10.** tF1 is centreline-based. Janus 0's one-voxel-thin boundary costs 9 Dice points
  and almost no tF1. Wherever reads keep TotalSegmentator's outline (D26), their width convention is TotalSegmentator's.
  Wherever annotators redraw (D12), it is closer to ImageCAS-X's. Neither moves tF1 much.
- **Extent and topology do matter.** These are where a read stops distally, which side branches it keeps, and the
  gaps the seed leaves. A read that only trims the seed inherits the seed's extent.
- **The literature expects exactly this:**
  - **Guberina et al. 2026** (doi:10.1016/j.tipsro.2026.100401, **Table 1, Fig. 2**): physicians correcting algorithm
    contours removed only about 30 % of the algorithm's error on average. The worse algorithm still gave the worse
    final contour in 151 of 169 comparisons.
  - **Arjmandi et al. 2025** (doi:10.1002/acm2.70425, **Tables 2–4**): AI-started contours raised inter-observer Dice
    from 0.78 to 0.89, while agreement with the expert fell from 0.85 to 0.81.
  - For A10, that means inter-read tF1 rises (the bar rises), and model-vs-read measures agreement with the seed's
    extent.
- **New pre-read measurement (M1, in Job 1, report-only, pre-registered).** Run TotalSegmentator `coronary_arteries`
  (the seed's exact settings, `tools/ccta/totalseg_cpu.py`) on **val 80 + open-36** (never a sealed case). Then:
  1. Name the binary seed with ImageCAS-X's classes (Bridge's seed naming: nearest reference voxel in mm; components
     not touching the reference are dropped, as an annotator deletes a vein). This is a **fully anchored read**.
  2. Score that read against collapsed ImageCAS-X: decisive tF1 per class, plus `r10_dice_check.measure()` (tolerant
     Dice, volume ratio, centreline recall and precision).
  3. Score Janus 0 against the anchored read and against ImageCAS-X on the same cases. **The difference is the shift
     A10's left side would see if reads were fully anchored.**

  | M1 result (val 80, macro) | Reading | What it changes |
  |---|---|---|
  | Anchored read vs ImageCAS-X ≥ 0.90, and \|Janus 0 shift\| ≤ 0.02 | The seed's extent is close to ImageCAS-X's; anchoring changes little of what A10 means | L5 can be answered "A10 on the pool stands" |
  | 0.80–0.90, or the shift is 0.02–0.05 | Partly a different convention | A31.2's seed flag decides per class, and the A23 contrast-supported diagnostic is reported first beside A10 |
  | < 0.80, or the shift is > 0.05 | Fully anchored reads would test the model against TotalSegmentator's extent | Q3 to the lead before wave-1 acceptance work: add the sealed ImageCAS-X 80 milestone as a binding co-criterion (§11) |

  It costs about 1 GPU-h of TotalSegmentator plus about 15 CPU-min, and it answers before any read exists how much
  L5 can matter.
- **Wave 1 then measures the real thing (A31.2, unchanged):** seed-vs-read against inter-read per class, plus the edit
  sizes. It runs on open + D35 reads, n ≈ 111.

### 6.2 Per-source domain shift (A31.3, A31.4)

- **A31.4, the pre-read domain check** (Atlas F2): Janus 0's prediction against each pool volume's seed, per source.
  It runs on the Job 1 predictions (CPU), on non-sealed, non-extension volumes only. As Atlas added, it reports
  **plain Dice, 1-voxel-tolerant Dice and volume ratio** side by side, so that a uniform width difference is not read
  as domain shift. Report-only.
- **A31.3, model-vs-read per source:** reported with patient-bootstrap CIs, decides nothing at n ≈ 30. It splits into
  seen sources (the five in Janus 1's training set) and unseen ones.

## 7. The left-tree ostium residual (report only; P2 closed)

- P2's 0.0079 sits in a few val left trees: 4.3 % of ostia are more than 2 mm from the expert start, and the open-36
  gap is 0.
- **On the pool, it partly cancels.** A10 is a contrast, model-vs-read minus inter-read, and both sides use the same
  aorta-derived ostium from the same read. A common ostium error moves both terms. It does not cancel when the model's
  root differs from the reads' root.
- **Report (CPU, Fir login node, no GPU).** From Delta's per-case P2 output (`$SCRATCH/icx4/delta_p2/`), list the val
  trees with ostium distance > 2 mm: case, side, distance, per-class tF1 under each ostium, and whether the
  TotalSegmentator aorta touches the left sinus. This is a list for a human look. Nothing changes A1.

## 8. What would change the plan

| Observation | Threshold | Change |
|---|---|---|
| Janus 0's real per-case val SD (`r9_tf1_val.json`) | P(pass) at 200, f = k = 1 < 0.8 | Report to the lead before the seal PR; 250 (Q1 alternative) becomes the recommendation |
| M1 (§6.1) | anchored read < 0.80, or Janus 0 shift > 0.05 | Q3 is asked again before wave-1 acceptance; the sealed ImageCAS-X milestone becomes a binding co-criterion if the lead agrees |
| Wave-1 f or k (open + D35) | > 1.2 in any class | Re-run §4's table, report to the lead (the seal cannot grow into D35) |
| Janus 1 forgetting guard | fails | The 1e-3 arm; then Janus 0 stays and rehearsal goes to Round 11 |
| Janus 1 pool gain | CI excludes 0 | Janus 1 is the working model; the next wave fine-tunes from Janus 1 under the same rules |
| Janus 1 pool gain | not shown | Janus 0 stays; next wave with more reads |
| σ̂_seed (Janus 1 vs Janus 2) | > 0.02 | Every later D35 decision needs two seeds per arm; quoted in A22 |
| Seen − unseen source gap on D35 | > 0.05 macro | Domain generalisation, not fine-tuning, is the issue. Report per source and look at what the unseen sources share (scanner, contrast) |

## 9. `role:swe` work this plan needs

| Item | Status |
|---|---|
| **#114**: refuse the reserve (and later D35) in `convert` and the trainer, by real patient, from a pinned held-out file | **Opened this round**, because it is a hazard under the current plan whatever the ruling |
| `trillium/janus` launcher on the icx4 Fir path: mode `pool-predict` (Job 1) and mode `finetune` (Job 2: task 716's trainer, ImageCAS-X 560 + pool reads, the held-out guard, prediction and scoring of D35, val 80 and open-36) | To be opened after the ruling |
| The seal extension to 200 as one explicit PR to `configs/segqueue14/sealed-pool-2026-10.json` (D27: seal changes are explicit) | After the lead's Q1 |
| Re-gridding the 74 suspect-spacing volumes (QC) | After Q6 |

## 10. Exact Fir jobs for the lead

Account `def-aso22` (charged to `def-aso22_gpu`); 1 × H100 80 GB (`h100:1`), 12 cores, 280 G; partition chosen by
walltime. Every job reads only non-sealed, non-extension volumes. The launcher refuses anything else, like `icx4`'s
`lib/sealed.py`.

**Job 1 (now; no reads needed; needs the `trillium/janus` launcher): Janus 0 on the pool + M1, about 5 GPU-h, one job.**

```sh
module load StdEnv/2023 python/3.11.5
cd $SCRATCH/asclepius/repo && git pull --ff-only          # a dev with the janus launcher and #114 merged
mkdir -p $SCRATCH/asclepius/experiments && rm -rf $SCRATCH/asclepius/experiments/janus
cp -r trillium/janus $SCRATCH/asclepius/experiments/janus && cd $SCRATCH/asclepius/experiments/janus
JANUS_CLUSTER=fir JANUS_MODE=pool-predict \
  JANUS_BASE=$SCRATCH/icx4/nnunet_results/Dataset715_ICX4/nnUNetTrainerICX4__nnUNetResEncUNetPlans_60G_iso05__3d_fullres/fold_0/checkpoint_final.pth \
  JANUS_VOLUMES=$SCRATCH/asclepius/repo/experiments/Foxtrot/r10/d35_proposal.json ./janus
grep SBATCH $SCRATCH/janus/pool-predict/job.sh          # h100:1, cpus-per-task=12, mem=280G, time=06:00:00, account=def-aso22
```

- **What it does:**
  - fetches the 278 volumes in `janus0_may_predict_now` from Girder `SegQueue/cases` (D22);
  - predicts them with Janus 0;
  - makes TotalSegmentator aortas for them (A1);
  - runs TotalSegmentator `coronary_arteries` on val 80 + open-36 for M1.
- **Cost:** ≈ 0.3 h prediction + 2–3 h aortas + 1 h coronary seeds ≈ **4–5 GPU-h**, walltime 6 h.
- **Then on the login node (CPU, about 30 min):** M1 and the A31.4 domain check
  (`python experiments/Foxtrot/r10/m1_report.py`, written with the launcher).
- **Send back on #113:**
  - `$SCRATCH/janus/pool-predict/SUMMARY.md` and `m1.json`;
  - **`$SCRATCH/icx4/r9_tf1_val.json`** (Janus 0's per-case val scores; settles §4);
  - the §7 list.

**Job 2 (Janus 1 and Janus 2): start when ≥ 40 of the 62 trainable primary patients have both reads approved.** About
140 reads incl. ImageCHD; #114 and the launcher merged. Two concurrent jobs, about 15 GPU-h each, **≈ 30 GPU-h in all**.

```sh
segqueue14-export --out /srv/segqueue14/export-wave1 --replicas all     # Girder host; sealed reads left out
# move the export to $SCRATCH/wave1 on Fir, then:
cd $SCRATCH/asclepius/experiments/janus
for SEED in A B; do
  JANUS_CLUSTER=fir JANUS_MODE=finetune JANUS_SEED=$SEED JANUS_WORK=$SCRATCH/janus/ft-$SEED \
    JANUS_BASE=$SCRATCH/icx4/nnunet_results/Dataset715_ICX4/nnUNetTrainerICX4__nnUNetResEncUNetPlans_60G_iso05__3d_fullres/fold_0/checkpoint_final.pth \
    JANUS_READS=$SCRATCH/wave1 JANUS_REHEARSAL=$SCRATCH/icx4 JANUS_EPOCHS=250 JANUS_ARM=primary ./janus
done
grep SBATCH $SCRATCH/janus/ft-A/job.sh                   # h100:1, cpus-per-task=12, mem=280G, time=23:50:00, account=def-aso22
./janus status $SCRATCH/janus/ft-A                       # after ~2 h: s/epoch (expect ~190-200)
```

- **The launcher refuses to start if:**
  - any read is sealed, in extension 1–50, or in D35 (#114);
  - the plans differ from Janus 0's;
  - fewer than 40 trainable primary patients are double-read.
- **Per seed:** 250 epochs ≈ 13.3 h, plus preprocessing of the pool part (≈ 0.5 h; ImageCAS-X's preprocessed data
  is reused from `$SCRATCH/icx4`) and prediction of D35, val 80 and open-36 (≈ 0.3 h). One job, walltime 23:50.
- **D35 scoring (CPU, login node):** when ≥ 40 of the 50 D35 patients have both reads approved,
  `./janus score-d35 $SCRATCH/janus/ft-A $SCRATCH/janus/ft-B`. It applies §5.4's rules and writes the verdict.
- **Send back on #113:** both `SUMMARY.md` files, `d35_verdict.json`, `val80_guard.json`.

**Later (the final model; costed, not now): from scratch** on ImageCAS-X train + val + open (720) + every trainable
pool read, 1000 epochs, ≈ 60 GPU-h. It is compared once on D35 against the best warm Janus (Q5). Then come the one
look at the 200-patient seal (A10, D6) and the one look at the sealed ImageCAS-X 80 (A26).

**Wave-1 GPU budget: ≈ 35 GPU-h** (Job 1 + Job 2), against about 150 for a warm-vs-scratch A/B.

## 11. Questions for the lead (asked, not decided)

| # | Question | Recommendation | Trade |
|---|---|---|---|
| Q1 | Extend the seal to 200 now (positions 1–50) and make D35 positions 51–100? | **Yes** | P(pass at human level) 0.91 instead of 0.78 (f = k = 1). 250 becomes unreachable (it would buy +0.06 to +0.14). Alternative: seal 250 later if needed, with D35 = 30 open patients (70 % Taiwan) and 31 left to train on |
| Q2 | D35 says "about 15 %" and "about 50", which are 31 % of the real non-sealed primary patients. Which holds? | **Keep 50** | 15 % (24 of 161) gives a model-decision MDE of about 0.03–0.07 |
| Q3 (L5) | If reads are seed-anchored, is A10 on the pool still acceptance? | Decide **after M1**, before wave-1 reads are scored. If M1 shows a shift > 0.05, make the sealed ImageCAS-X 80 milestone (model vs ImageCAS-X, at most 0.03 below open-36) a binding co-criterion | — |
| Q4 (L6) | ASOCA? | **Not now.** The pool's 22 sealed sources are the external test | — |
| Q5 | The final retrain on train + val + open? | **Yes, at the end, from scratch**, decided on D35 against the best warm Janus. D35 is what makes this decidable without val 80 | Spends val 80 and open-36 as decision sets; after it, ImageCAS-X has only the sealed 80's one look |
| Q6 | Re-grid the 74 suspect-spacing volumes? | **Yes** (QC) | +74 trainable patients. Today they are neither trainable nor scorable |

## 12. External evidence (checked 2026-10-25; full table in the literature note)

| Claim | Source | Where |
|---|---|---|
| Scratch catches up only with about 5–6× compute; it fails with little data | He, Girshick, Dollár, ICCV 2019, doi:10.1109/ICCV.2019.00502 | Fig. 1, Table 1, Figs. 7–8 |
| Warm-starting on grown data can generalise worse (classification) | Ash & Adams, NeurIPS 2020, arXiv:1910.08475 | Table 1, Fig. 7 |
| nnU-Net fine-tuning forgets; rehearsal prevents it (MRI) | González et al., Sci Rep 13:9381 (2023), doi:10.1038/s41598-023-34484-2 | Tables 1–2 |
| Fine-tuning ≥ scratch in medical imaging (not shown for small-data segmentation) | Tajbakhsh et al., IEEE TMI 35:1299 (2016), doi:10.1109/TMI.2016.2535302 | abstract; Figs. 2b, 4b, 6b, 9 |
| Degradation on centres absent from training | Campello et al., IEEE TMI 40:3543 (2021), doi:10.1109/TMI.2021.3090082 | Table IX, Figs. 2 and 8 |
| Corrected auto-contours keep about 70 % of the algorithm's error | Guberina et al., tipsRO 38:100401 (2026), doi:10.1016/j.tipsro.2026.100401 | Table 1, Fig. 2 |
| AI-started contours: inter-observer agreement up, accuracy down | Arjmandi et al., JACMP 27:e70425 (2025), doi:10.1002/acm2.70425 | Tables 2–4 |
| Automation bias is strongest in inexperienced readers (scripted "AI") | Dratsch et al., Radiology 307:e222176 (2023), doi:10.1148/radiol.222176 | abstract |
| Data sampling dominates variance; init is less than half of it; use several runs | Bouthillier et al., MLSys 2021, arXiv:2103.03098 | Fig. 1, Sec. 5 |
| CIs are rarely reported, and runner-ups lie inside the winner's CI | Christodoulou et al., MICCAI 2024, arXiv:2409.17763 | Sec. 3, Fig. 4b (64.9 % of 77) |
| CNN U-Nets match or beat Transformers and Mamba | Isensee et al., MICCAI 2024, arXiv:2404.09556 | Table 1 |

## 13. Risks

| Risk | Likelihood | Effect | Mitigation |
|---|---|---|---|
| The CI-derived Janus 0 spread is wrong | medium | §4's numbers move | One send-back file (`r9_tf1_val.json`); §8 row 1 |
| Too few trainable pool patients to gain on D35 | medium | "Not shown better" | Rehearsal keeps ImageCAS-X; the next wave adds reads; Q6 adds 74 patients |
| Fine-tune on 5 sources does not transfer to the seal's 22 | medium | A10 fails on unseen sources | The seen/unseen split on D35 (§5.4) warns early; the final retrain uses every source available |
| Seed anchoring makes A10 test TotalSegmentator's extent | likely, unmeasured | A10's meaning | M1 before any read; A31.2 on reads; Q3 |
| D35 at 50 cannot see LCx-only effects | certain | Coarse per-class decisions | LCx reported, never decisive alone |
| The launcher is new code | certain | A failed Fir job | Built on the icx4 Fir path; dry-run header check; Job 1 is small (5 GPU-h) |

## 14. Comparison with the master and other positions

- **Kept from the master** ([[Atlas v11]] + A25–A32): Janus 0 and its recipe, A1/A1c, A11′, A15, A17a/b, A19, A22
  (with the model/recipe distinction asked for in §5.4), A23, A26, A28, A31.
- **Atlas F3 (warm fine-tune):** agreed, and I add rehearsal, the forgetting guard and two seeds. **Crucible P3/P4:**
  P4's from-scratch final model is adopted (Q5). P3's "≥ 300 open pool reads" trigger is out of reach on real
  patients (about 140 primary reads in total), and its 2:1 mixing A/B is below D35's resolution.
- **Bridge's wave-1 tools:** used unchanged. f, k and the seed flag gain the D35 reads (n ≈ 111).

## 15. Changes since v5

1. A complete plan for after Janus 0 (D34, D35), replacing v5's plan for the first job.
2. **New CPU evidence:**
   - the real-patient D35 frame (161 / 100 / 61);
   - Janus 0's seal re-power;
   - measured paired noise from three real pairs;
   - D35 MDEs;
   - a frozen, reproducible D35 candidate with tests (`experiments/Foxtrot/r10/`, `pytest experiments/Foxtrot/r10`, 4 pass).
3. **#114** opened (the reserve is not refused in training).
4. **Corrected:** F7.1's "lost tree" premise (it was lumen width); "beat every" → "match or beat" (nnU-Net Revisited
   Table 1).
5. Retired: F5 (done; Janus 0's 192 s/epoch confirmed the budget), F7 (read), and F8's n = 30 table (replaced by D35).
