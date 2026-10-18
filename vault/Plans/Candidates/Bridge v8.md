---
tags: [plans/candidate, bridge, statistics, evaluation, fir, four-class]
author: Bridge
round: 9
updated: 2026-10-18
issue: christianGRogers/Asclepius#48
---

# Bridge v8: run icx4 on Fir unchanged; score it by tF1, and give A10 cases it can actually be scored on

## 0. Position

- **The model is icx4 as built.** That is one 4-class nnU-Net v2 ResEnc on ImageCAS-X collapsed by territory
  (D25), dataset 715. Bridge proposes no recipe change. The architecture has the strongest published
  baseline record (§8), our run 1 scored 0.896 decisive macro tF1 with the same network, and a recipe change
  now could only be judged against a model that has not been scored yet.
- **What is broken is the evaluation, not the model.** As written, the plan for Fir would end with:
  1. a **Dice-only** score, which decides nothing under A1/A1c;
  2. the **A14 sealed test opened**, because icx4 scores all 160 ImageCAS-X test cases (Echo, #49);
  3. an **acceptance rule (A10, D6) with no cases.** No team read will ever touch the frozen sealed test
     (D22, D23), and ImageCAS-X's own second read of its test set was never released (verified on Zenodo).
- v8 fixes all three. It sizes the new A10 set from data
  ([[Bridge - No team read will ever touch the sealed test, so A10 needs a sealed pool set of about 150 patients]]),
  costs every step in Fir GPU-hours and gives the lead the exact first job.

## 1. Model and architecture (unchanged from icx4)

| Item | Setting | Source |
|---|---|---|
| Network | nnU-Net v2.8.1, ResEnc, the 60 GB plan (`nnUNetResEncUNetPlans_60G_iso05`) | `trillium/icx4`; Round 5 R0 benchmark: 55.6 GiB, fits an 80 GB H100 |
| Resolution | 0.5 mm isotropic | [[Atlas - Resampling to 0.5 mm isotropic loses nothing measurable, 0.7-0.8 mm does]] |
| Patch, batch | 256³, batch 2 | [[Atlas - A 128 mm patch at 0.5 mm holds the whole tree and the LM in almost every training patch]] |
| Augmentation | nnU-Net default; mirroring off (left/right is the label) | master plan |
| CT window | nnU-Net's default (Round 8, tie-break) | [[Round 8]] |
| Length | 1000 epochs, poly LR, one fold (fold 0 = ImageCAS-X's val 80) | icx4 |
| Inference | tile step 0.5, no TTA | icx4 `job_body.sh` |

## 2. Labels

ImageCAS-X as drawn (D8), collapsed by `trillium/icx4/lib/territory.py`:
- LM ← LM;
- LAD ← LAD, D1, D2;
- LCx ← LCx, OM1, OM2, IM, L-PDA, L-PLA;
- RCA ← RCA, R-PDA, R-PLA;
- "Other" (D3/D4, OM3/OM4) → the nearest LAD/LCx voxel, in mm.

Echo's audit (#49) found that this table matches D25 value by value in all five copies.

- The **reference for every score is collapsed by the same function** as the training labels (icx4
  `score.py` already does this).
- Echo found that `segtrain.reads.icx_to_territory` measures "Other" distance in voxels, not mm. That is
  harmless for icx4, which never calls it. But any later scorer built on segtrain must use the mm version
  (Echo's swe issue).

## 3. Data and splits

| Set | Cases | Use |
|---|---|---|
| ImageCAS-X train | 560 | Training |
| ImageCAS-X val (fold 0) | 80 | nnU-Net validation; per-epoch pseudo-Dice only |
| ImageCAS-X test, **open clean** | 36 | Interim decisions (decisive tF1). Reported apart from the dev 44 |
| ImageCAS-X test, **open development** | 44 | Interim decisions, reported separately (each was inspected by an advocate) |
| ImageCAS-X test, **sealed** | 80 | **One blind look**, model vs ImageCAS-X, for the final model only. Not scored by icx4 (Echo's fix) |
| Quality-0 sealed | 20 | **Retired** (proposal): no reads (D23) and no ImageCAS-X labels, so nothing can score them |
| **Pool seal (new, proposed)** | 150 primary patients (216 volumes) + 20 ImageCHD patients, report only | **A10** against team double reads. Out of every pool fine-tune |
| Pool, rest | 367 patients | Team reads (D23); later fine-tunes (A17) |

The pool seal is drawn by patient, stratified by source, ranked by a salted sha256:
`experiments/Bridge/r9/seal_pool.py` → `sealed_pool_proposal.json`. It must be published before the first pool
read is exported. Why by patient: the 675 pool volumes are **517 patients**, and one patient has 20 cardiac
phases.

## 4. Recipe and sequence

1. **icx4 on Fir**, unchanged (§7 commands).
2. **Decisive scoring** on the open 80 (issue #54): TotalSegmentator aortas, then `segtrain.tf1` at the
   pinned A1c hash, flagged trees apart (A1b), FP components (A15) and the A23 diagnostic.
3. **Prelabels and pool predictions.** icx4 predicts all 1000 ImageCAS cases. The pool is served from
   TotalSegmentator seeds (D23, D26), so icx4 is not shown to annotators. The pool predictions are made only
   for scoring once reads arrive.
4. **When wave-1 pool reads arrive** (non-sealed only):
   - measure f (the pool/val spread ratio) and k (the inter-read/model spread ratio);
   - extend the seal along its pre-registered order if either is above 1.2 (§5);
   - then fine-tune on the reads under A17 (fine-tune trainer, LR 1e-2 with a 1e-3 arm) and A11′.
5. **Acceptance:** A10 on the pool seal, once. The sealed ImageCAS-X 80 are scored blind in the same sitting.

## 5. Deciding metric and decision rules

- **Decisive:** tF1 @ 1.5 mm (D3), A1 ostium from a TotalSegmentator aorta, A1c hash `24441cf8…`, flagged trees
  apart (A1b).
  - Dice is reported, never decisive.
  - Delta showed Dice cannot see the breaks that cut a tree: [[Delta - Dice cannot see the errors that break a coronary tree]].
  - The published coronary benchmarks score by Dice or overlap, so §8 compares on both.
- **A10 (D6), on the pool seal.** For each class, non-inferior to inter-read tF1 within 0.05: the lower 95 %
  bound of the mean paired difference must be above −0.05. All four classes must pass. Power at n = 150
  patients, for a model exactly as good as a reader:

  | Pool spread relative to ImageCAS val | P(pass) |
  |---|---|
  | Same | **0.97** |
  | 1.5× | 0.58 (about 250 patients are needed for 0.88) |

  The LCx is the binding class.
- **Seal size rule (pre-registered).** Measure f and k on wave-1 *non-sealed* double reads. If the power at
  δ = 0 falls below 0.8, extend the seal along `extension_order` (200, then 250 patients) **before any sealed
  read is scored**.
- **Retrained-network decisions: A22.** σ_seed = 0.013 until it is measured; an effect under 0.02 needs
  ≥ 2 seeds; arms get equal epochs. On the open 80, the MDE for a paired retrained comparison is:

  | Design | MDE |
  |---|---|
  | Cases only | 0.013 |
  | One seed per arm | **0.039** |
  | Two seeds | 0.029 |
  | Three seeds | 0.025 |

  So on Fir, any contested arm runs as concurrent seeds, not as a single run.
- **icx4's own reading (pre-registered; it is a model-vs-expert benchmark, so it has no pass bar).**

  | Result on open 80, decisive tF1 | Reading and action |
  |---|---|
  | Every class ≥ 0.85 and macro ≥ 0.88 | Proceed: icx4 is the base for pool fine-tunes |
  | Any class < 0.85, or LCx < 0.83 (Atlas's Round 8 guard) | Review that class's 10 worst open cases before any fine-tune, then choose the fix |
  | Macro < 0.80 | Stop. Something is wrong with the job, the labels or the scorer, not the recipe. Check the collapse, the resume and the hash first |
  | Flagged trees > 30 % for any class | The A1b review becomes the first task; a decision on that class waits for it |

  The 0.85/0.88 lines are set from run 1 (LCx 0.846, macro 0.896). Run 1 used the D0 thick convention, and the
  two conventions are not comparable in absolute terms ([[Crucible - A perfect segmentation in the wrong lumen convention loses 0.19 tree-F1]]).
  These lines are therefore triggers for a look, not acceptance.

## 6. Seeds on Fir: an optional second icx4 seed

Fir has 640 H100s. A second, independent icx4 run (nnU-Net does not fix its seed, so a second run is a new
seed) needs the `ICX4_WORK` workdir override from #54. It gives three things:
1. **σ_seed on the 4-class model itself.** Every later A22 decision currently borrows Crucible's
   small-model 0.013.
2. **A free check on the run.** icx14's job 2 lost a run to a resume bug.
3. **A 2-model ensemble.** Scoring it is a fixed-prediction decision with case-only CIs.

Cost: +56–76 GPU-h, with no extra wall-clock if it is submitted beside the first run.

| Outcome on open 80 (paired, decisive macro) | Action |
|---|---|
| \|seed 2 − seed 1\| ≤ 0.005 per class | Use σ_seed = the measured value; most later single-seed decisions become legitimate |
| 0.005–0.02 | A22 as written, with the measured σ_seed |
| > 0.02 in any class | Every retrained decision needs ≥ 3 seeds; ensembling becomes the default if the ensemble beats the better single model (case CI excludes 0) |

**This is the lead's GPU-budget call, not a requirement.** Round 8 refused a standalone 40 h seed replicate
of a settled forced choice. This one is different: it seeds the base model of every later decision, and
Fir's capacity makes it wall-clock-free. If the lead declines, σ_seed is measured, as Round 8 said, on the
first retrained decision (likely the first pool fine-tune).

## 7. Schedule on Fir, and the first job for the lead

**Fir facts.** Read 2026-10-18 from docs.alliancecan.ca, via the compute inventory note (#46/#47):
- 160 nodes × 4 H100 SXM5 80 GB, with about half the nodes MIG-partitioned;
- bundle per GPU: 12 cores / 280 GB;
- jobs up to 7 days;
- compute nodes have internet;
- SCRATCH 20 TB with a 60-day purge;
- `def-aso22` works after the CCDB opt-in.

*Assumption:* opportunistic priority on `def-aso22` (the issue's default); #46's account table is still empty.

| Step | Where | GPU-h (Fir) | Note |
|---|---|---|---|
| Labels, venv, preprocess | login node + job 1 (CPU part) | ~1–2 | First run on Fir builds `$HOME/icx14-venv` |
| Training, 1000 epochs | jobs 1–3 (chain of 4 × 23:50) | **52–69** | 187–208 s/epoch on Trillium (icx14). Fir has 10 data workers against 22, so it may be up to ~250 s/epoch (inventory) |
| Predict 1000 cases | last job | 2–4 | |
| Aortas (open 80) + tF1 (#54) | last job | ~1 | CPU tF1 overlaps |
| **Total, icx4** | | **≈ 56–76** | 3–4 chained jobs |
| Optional seed 2 (§6) | concurrent | +56–76 | Needs #54's `ICX4_WORK` |

**The first Fir job (copy-paste).**

```sh
# 0. Once, in a browser: CCDB -> Resources -> Access Systems -> opt in to Fir (takes up to 1 h).

# 1. Data: copy cases/ from Trillium to Fir with Globus
#    (source alliancecan#trillium : <root>/cases  ->  destination alliancecan#fir : $SCRATCH/asclepius/cases),
#    or rsync from a Trillium login node to Fir's scratch (on Fir, `echo $SCRATCH` gives the path):
#      rsync -a <root>/cases/ fir.alliancecan.ca:<Fir $SCRATCH>/asclepius/cases/

# 2. On the Fir login node:
ssh fir.alliancecan.ca
mkdir -p $SCRATCH/asclepius/experiments && cd $SCRATCH/asclepius
git clone --branch dev https://github.com/christianGRogers/Asclepius.git repo      # or rsync your Trillium checkout
cp -r repo/trillium/icx4 experiments/icx4
cd experiments/icx4
ICX4_CLUSTER=fir ICX4_DRYRUN=1 ./icx4   # must print: --gpus-per-node=h100:1, --cpus-per-task=12, --mem=280G, account def-aso22
ICX4_CLUSTER=fir ./icx4                 # builds the venv, fetches labels, submits a chain of 4 x 23:50 jobs
./icx4 status                           # after ~2 h: s/epoch; above ~250 s, all 4 chained jobs will be used

# 3. Before training ends (>= 2 days later), once Echo's sealed-split fix and #54 are merged into dev:
cd $SCRATCH/asclepius/repo && git pull && cp -r trillium/icx4/lib/. $SCRATCH/asclepius/experiments/icx4/lib/
#    (score.py is read when the last job starts, so updating lib/ in place is enough; no resubmission.)

# 4. When `./icx4 status` says DONE:
./icx4 collect                          # then post results/SUMMARY.md on #43
```

- **Account:** `def-aso22` (the launcher's default).
- **Resources per job:** 1 × H100 80 GB, 12 cores, 280 GB, 23:50.
- **Expected:** 56–76 GPU-h over 3–4 jobs.
- **If step 3 cannot happen in time:** let the job finish, but do not open `per_case_test.json` or the test
  table, and tell the PM. The judge then treats the sealed 80 as opened, and the final model-vs-expert look
  moves to the pool seal only.
- **Scratch purge.** Fir purges scratch after 60 days. Copy `results/` and the checkpoint off scratch within
  a month.

## 8. External evidence

*(Filled in below from verified sources.)*

## 9. What would change this plan

| Evidence | Change |
|---|---|
| icx4 open-80 decisive macro < 0.80 | Stop: debug the job, labels or scorer (§5) before any recipe question |
| Any class < 0.85 (LCx < 0.83) on open 80 | Review that class's worst cases; a recipe change for it would need A22 seeds |
| Wave-1 non-sealed reads: f or k > 1.2 | Extend the pool seal to 200–250 patients before sealed scoring |
| Wave-1: model vs reads 0.02–0.03 below inter-read on non-sealed pool cases | A10 will likely fail at any affordable n. Pool fine-tuning (A17) becomes the critical path, decided under A22 |
| Seed 2 run (§6) | σ_seed table in §6 |
| Another advocate's recipe change shown on the open 80 with ≥ 2 seeds and effect ≥ 0.03 | Adopt it; Bridge has no stake in the recipe |
| ImageCAS-X's second-analyst test reads become available (§11 Q4) | A10 also runs on the sealed ImageCAS-X 80, against expert double reads; passing requires both sets |
| The judge keeps the A14 seal as A10's set | Then A10 cannot be scored at all; the lead would have to read ImageCAS cases twice (reversing part of D22/D23), a human decision |

## 10. Risks

| Risk | Response |
|---|---|
| The Echo/#54 fixes are not merged before icx4 scores | §7 step 3; worst case, the sealed 80 count as opened and only the pool seal remains |
| Fir's 12 cores slow training (CPU-bound augmentation) | The 4-job chain covers ~90 h of training; `./icx4 status` shows s/epoch early |
| A MIG slice instead of a full H100 | The Fir profile asks for `h100:1`. The dry run shows the header |
| The pool is far more varied than ImageCAS (26 sources) | That is the f scenario; the seal size rule handles it; ImageCHD is report-only and the spacing-suspect sets are excluded |
| The patient-key heuristic merges or splits patients wrongly | The builder confirms per source. Errors only move a few volumes between sealed and training |
| The seal takes 32 % of primary pool volumes from fine-tuning | The price of a scoreable A10. At 100 patients, P(pass) at f = 1 drops from 0.97 to 0.84 |

## 11. Questions for the lead (decisions, not assumptions)

1. **Quality-0 sealed 20:** retire them (they can never be scored), or keep them for a future read? Bridge
   recommends retiring.
2. **Many phases of one patient in the pool** (60 patients with 2–20 volumes; 675 volumes for 517 patients).
   Under D23 each volume is read twice. Reading 20 phases of one heart costs annotator time and adds little
   independent information. Should the queue serve one volume per patient first? This touches D23, so it is
   the lead's call.
3. **The optional second icx4 seed (§6):** +56–76 GPU-h on Fir.
4. **Ask the ImageCAS-X authors (Bransby et al.) for their second-analyst annotations of the 160 test cases.**
   They exist (arXiv:2608.30404, inter-observer table) but are not in the Zenodo record: verified 2026-10-18,
   one segmentation per case. With them, A10 can also run on the sealed ImageCAS-X 80, against expert double
   reads, at no annotator cost. It would be a second, in-domain A10 beside the pool seal. Contacting authors is
   the lead's call (D19: the lead handles access requests).

## 12. Cost

- **CPU here:** done (two scripts, one note).
- **Fir:** icx4 is 56–76 GPU-h. Optionally +56–76 for seed 2.
- **SWE:** #54 (decisive scoring + `ICX4_WORK`), Echo's sealed-split issue, and later a builder for the pool
  seal list.
