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

Cost: +56–76 GPU-h. It adds no wall-clock if it runs beside the first run. But Fir's 24 h queue is busy
(309 queued at 06:00 UTC), so seed 2 should be submitted only **after seed 1's first job has started**,
so that it can never delay seed 1.

| Outcome on open 80 (paired, decisive macro) | Action |
|---|---|
| \|seed 2 − seed 1\| ≤ 0.005 per class | Use σ_seed = the measured value; most later single-seed decisions become legitimate |
| 0.005–0.02 | A22 as written, with the measured σ_seed |
| > 0.02 in any class | Every retrained decision needs ≥ 3 seeds; ensembling becomes the default if the ensemble beats the better single model (case CI excludes 0) |

**This is the lead's GPU-budget call, not a requirement.** Round 8 refused a standalone 40 h seed replicate
of a settled forced choice. This one is different: it seeds the base model of every later decision, and
our unused Fir fairshare makes it cheap in wall-clock. If the lead declines, σ_seed is measured, as Round 8 said, on the
first retrained decision (likely the first pool fine-tune).

## 7. Schedule on Fir, and the first job for the lead

**Fir facts.** Read 2026-10-18 from docs.alliancecan.ca, via the compute inventory note (#46/#47):
- 160 nodes × 4 H100 SXM5 80 GB, with about half the nodes MIG-partitioned;
- bundle per GPU: 12 cores / 280 GB;
- jobs up to 7 days;
- compute nodes have internet;
- SCRATCH 20 TB with a 60-day purge;
- `def-aso22` works after the CCDB opt-in.

**Account facts** (the lead's Fir output, #46 comments of 05:55 and 05:57 UTC, PR #52):
- `CC_CLUSTER=fir`, so `./icx4` picks the Fir job shape by itself.
- Slurm accounts `def-aso22_gpu` / `_cpu`, charged automatically from `--account=def-aso22`.
- RawUsage 0 (LevelFS inf), so fairshare priority is at its maximum. No MaxJobs/MaxTRES/GrpTRES limits.
- HOME 48 GiB; SCRATCH 19 TiB (60-day purge); PROJECT unconfirmed.
- GPU partitions by walltime: 3 h, 12 h, 24 h (`gpubase_bygpu_b3`, where the 23:50 jobs land), 3 d, 7 d, and
  `gpubackfill` 24 h.
- StdEnv/2023 + python 3.11.5 + cuda 12.6 load; the wheelhouse has torch 2.14.1 for cp311.
- **The queue is busy:** at about 06:00 UTC, 309 one-GPU jobs were queued and 216 running in the 24 h
  partition, with no idle GPU node. Expect a wait; top fairshare should put us near the front. Keep the 23:50
  chain: the 3 d and 7 d partitions have fewer nodes (60 and 30).

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
#    (source alliancecan#trillium : <root>/cases  ->  destination alliancecan#fir-globus : $SCRATCH/asclepius/cases),
#    or rsync from a Trillium login node to Fir's scratch (on Fir, `echo $SCRATCH` gives the path):
#      rsync -a <root>/cases/ fir.alliancecan.ca:<Fir $SCRATCH>/asclepius/cases/

# 2. On the Fir login node:
ssh fir.alliancecan.ca
mkdir -p $SCRATCH/asclepius/experiments && cd $SCRATCH/asclepius
git clone --branch dev https://github.com/christianGRogers/Asclepius.git repo      # or rsync your Trillium checkout
cp -r repo/trillium/icx4 experiments/icx4
cd experiments/icx4
ICX4_DRYRUN=1 ./icx4                    # must print "cluster: fir" and --gpus-per-node=h100:1, --cpus-per-task=12, --mem=280G, def-aso22
./icx4                                  # builds the venv, fetches labels, submits a chain of 4 x 23:50 jobs
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

All items were checked on 2026-10-18 against Crossref, PubMed, arXiv or the official page. Where a table
could not be read (paywall), the claim is cited to what was read, and the gap is stated.

### 8.1 The model: no published result argues for leaving a configured nnU-Net ResEnc

| Claim | Source |
|---|---|
| nnU-Net self-configures and is the baseline to beat | Isensee et al., *Nature Methods* 18:203–211 (2021), doi 10.1038/s41592-020-01008-z |
| ResEnc presets beat the original nnU-Net. 5-fold mean DSC: KiTS 86.04 → 88.17 (L) / 88.67 (XL); AMOS 88.64 → 89.41 / 89.68 | Isensee et al., *nnU-Net Revisited*, MICCAI 2024, doi 10.1007/978-3-031-72114-4_47, arXiv 2404.09556, **Table 1** |
| No 2024–2026 work beats a configured nnU-Net on multi-class vessel labelling; TopCoW and TopBrain winners are nnU-Net | [[Foxtrot - Nothing published by October 2026 beats a well-configured nnU-Net on per-branch coronary or vessel labelling]] (sources verified there) |

The VRAM targets of the presets (M 9–11 GB, L 24 GB, XL 40 GB) are in the nnU-Net repository
(`documentation/resenc_presets.md`), not the paper. The paper's Table 1 gives measured VRAM: M 9.1, L 22.7,
XL 36.6 GB. Our 60 GB plan is a custom ResEnc plan at a 256³ patch, larger than XL, and was benchmarked here:
R0, 55.6 GiB.

### 8.2 Comparable numbers: there is no published per-branch voxel model to compare with

| What | Number | Comparable to us? |
|---|---|---|
| **Per-branch voxel segmentation by a CNN, LM/LAD/LCx/RCA** | **None found** (two searches; Foxtrot's survey agrees) | — |
| ImageCAS-X inter-observer per-segment DSC, 160 test cases (arXiv 2608.30404, **Table 1**; preprint) | LM 91.9 ± 13.7, LAD 92.3 ± 6.7, **LCx 84.8 ± 19.8**, RCA 95.3 ± 5.0; merged 92.8 ± 3.1 | Same cases and convention (D8), but **human vs human, Dice not tF1**, and 14 segments (LAD/LCx/RCA unsplit, so the four trunk rows are close to ours). The ceiling's *shape* transfers: the LCx is hardest for humans too, as in run 1 (LCx 0.846 tF1, the lowest class) |
| ImageCAS-X binary benchmark, **Table 2** | nnU-Net 89.8 ± 3.2; nnU-Net + clDice 90.0; CAS-Net 91.2; **TotalSegmentator zero-shot 70.5 ± 6.2**; original ImageCAS labels vs ImageCAS-X 41.8 | Binary only. Their nnU-Net is default-configured (Foxtrot). TotalSegmentator's 70.5 is relevant to us because D23's pool seeds *are* TotalSegmentator masks: annotators will be cutting down a seed whose Dice against an expert tree was about 0.70 on ImageCAS (the pool may differ) |
| CPR-GCN (Yang et al., CVPR 2020, doi 10.1109/CVPR42600.2020.00386, arXiv 2003.08560, **Table 3**), 511 subjects, 5-fold | Branch-level F1: LM 0.989, LAD 0.988, LCx 0.976, RCA 0.990 | **Not comparable.** It labels *given centrelines*, a task close to Bridge's namer, not voxel segmentation. The same table re-implements TreeLab-Net (Wu et al., IJCARS 14:271–280, 2019, doi 10.1007/s11548-018-1884-6): LM 0.983, LAD 0.942, LCx 0.924, RCA 0.949. Wu's own per-branch table was not readable (paywall); its abstract gives AUC > 97 % for the four main branches on 436 scans |
| TopoLab (Zhang et al., arXiv 2307.11959) | F1 87.23 on orCaScore (72 CTA), 92.19 in-house (1200), 14 categories | Centreline labelling again; preprint |
| ASOCA (Gharleghi et al., CMIG 97:102049, 2022, doi 10.1016/j.compmedimag.2022.102049). 40 train / 20 test; inter-annotator Dice 85.6 ± 7.7 (Sci Data 10:128, 2023, doi 10.1038/s41597-023-02016-2, Tables 1–2) | Top Dice 0.867 (ranking at asoca.grand-challenge.org/MICCAI_Ranking/) | Binary, another cohort. **Read from the challenge ranking page.** The CMIG table number was not readable |
| CAT08 (Schaap et al., *MedIA* 13:701–714, 2009, doi 10.1016/j.media.2009.06.003). 32 CTA (8 train / 24 test), RCA, LAD, LCx + one side branch | Scores are normalised so that 50 = observer performance | Centrelines. This is the precedent for A10's logic: the unit of measurement is a second human |
| TotalSegmentator (Wasserthal et al., *Radiology: AI* 5:e230024, 2023, doi 10.1148/ryai.230024) | `coronary_arteries` is a separate, licensed task with **one binary class** (`map_to_binary.py`). The README reports no coronary Dice | It cannot name branches, so it is no 4-class baseline. It is our seed and our aorta source |

**Reading.** Our 4-class numbers have no published comparator. What can honestly be compared:
1. **The binary tree, against ImageCAS-X Table 2.** The A23 / #54 report should therefore include the
   whole-tree Dice icx4 already computes, on the open 80, beside nnU-Net's 89.8. That is a different sample
   (their 160 includes our sealed 80), so the comparison is indicative, not paired.
2. **The per-class pattern, against human agreement.** The ImageCAS-X inter-observer table is the only
   per-branch voxel evidence on these exact cases. Their LCx spread (SD 19.8 Dice points, about 3× LAD's) is
   evidence that A10's binding class will be the LCx (§5, and the note's k > 1 scenario).

### 8.3 The evaluation design: the literature says our concern is the field's common failure

| Claim | Source | Used for |
|---|---|---|
| Of 221 MICCAI 2023 segmentation papers, 54.8 % report no variability and 1 paper reports CIs. In 77 papers with imputed CIs, the median 95 % CI width of the winner's mean DSC is 0.03, while the median 1st–2nd gap is 0.01; in 64.9 % the runner-up lies inside the winner's CI | Christodoulou et al., MICCAI 2024, doi 10.1007/978-3-031-72117-5_12, arXiv 2409.17763 (§3, Fig. 3, Fig. 4b) | Every decision table here states its MDE (A19); single-seed wins under 0.02 are "not detected" (A22) |
| Fold-to-fold SD of ResEnc M DSC: 0.57–2.6 % across six datasets. On BTCV the between-method spread is smaller than the fold noise | nnU-Net Revisited, Appendix **Table 3** and §4 | Training noise is the same order as the effects being tested. That is our σ_seed problem |
| nnU-Net trained with 50 seeds: the best seed significantly beat 0–76 % of the other seeds (hold-out) | Åkesson, Töger, Heiberg, *Comput Biol Med* 180:108944 (2024), doi 10.1016/j.compbiomed.2024.108944 (abstract; full-text SDs not read) | A22's seed rule, and the optional seed 2 (§6) |
| Randomise every source of variation (split, init, data order, augmentation), and compare by P(A > B) | Bouthillier et al., MLSys 2021, arXiv 2103.03098, §5 | Seeds as concurrent runs on Fir. nnU-Net does not fix a seed by default, so a second run randomises init, order and augmentation |
| Error bars of about ±10 % at 100 samples; fold SE underestimates them | Varoquaux, *NeuroImage* 180:68–77 (2018), doi 10.1016/j.neuroimage.2017.06.061 | Why A10 is powered on patients, not volumes, and why the 36-case clean set alone cannot decide much (MDE 0.039 with one seed) |
| For tubular structures, use clDice or another centreline metric beside or instead of DSC | Maier-Hein et al., *Metrics Reloaded*, *Nature Methods* 21:195–212 (2024), doi 10.1038/s41592-023-02151-z, Table 1 (FP3.3) | tF1 (a centreline, topology-aware score) is decisive, Dice secondary (#54). clDice: Shit et al., CVPR 2021, doi 10.1109/CVPR46437.2021.01629 |

Not cited, on purpose: Renard et al. (*Sci Rep* 10:13724, 2020) is a literature review with no seed
experiments, so it supports nothing numeric here.

### 8.4 Fir

From docs.alliancecan.ca/wiki/Fir (last edited 21 July 2026; read 2026-10-18):
- 160 GPU nodes × 4 H100 SXM5 80 GB (48 cores, 1125 GB per node). The page's "GPU layout" paragraph says 2
  per node; the table's 4 is taken, as in the inventory.
- Max job 7 days.
- About half the nodes are MIG; a full GPU is requested with `h100:1`.
- Compute nodes have internet.

From *Allocations and compute scheduling* (last edited 25 Sept 2026): a full H100 on Fir is 12.2 RGU, with a
recommended bundle of **12 cores / 280 GB**. That is exactly icx4's Fir profile.

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
