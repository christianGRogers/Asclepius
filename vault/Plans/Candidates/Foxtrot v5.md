---
tags: [plans, candidate, round9, fir, four-class, icx4, external-validation, literature]
author: Foxtrot
round: 9
version: 5
updated: 2026-10-18
issue: christianGRogers/Asclepius#48
---

# Foxtrot v5: run icx4 on Fir as built, decide on tF1 over the open test, read the result against the literature, and test it on other centres

> **File name.** The Round 9 brief names my next candidate `Foxtrot v4.md`, but that file is my Round 8
> candidate, and candidates are never edited after their round ([[README]]). This is therefore v5.

## 1. Thesis

**Decision: adopt icx4 as the model, unchanged. Add the four things it lacks to be a plan:**

1. a measured Fir job shape and GPU-hour budget (F5);
2. a decisive score (F6), which is Bridge's #54 and Echo's #55, endorsed here, not duplicated;
3. two outside reads of the first result, pre-registered, at no GPU cost (F7);
4. an external test on other centres' scans, pre-registered, as team reads arrive (F8).

Why not change the model. The literature still offers nothing that beats a well-configured nnU-Net on
multi-class vessel labelling. The evidence:

- [[Foxtrot - Nothing published by October 2026 beats a well-configured nnU-Net on per-branch coronary or vessel labelling]] (Round 6);
- TopCoW and TopBrain were won by nnU-Net teams;
- nnU-Net Revisited (Isensee et al., MICCAI 2024, arXiv:2404.09556, Table 1): ResEnc M/L/XL match or beat
  every transformer and Mamba model tested;
- re-checked today: [[Foxtrot - No published model labels LM, LAD, LCx and RCA on ImageCAS-X, so icx4 is judged against binary benchmarks and the human ceiling]].

icx4 *is* that configuration: nnU-Net v2.8.1, ResEnc encoder, a 60 GB plan with a 256³ patch at 0.5 mm (a
128 mm field), default window (Round 8), mirroring off, 1000 epochs. The one coronary benchmark where
nnU-Net lost (ImageCAS-X: CAS-Net 91.2 vs nnU-Net 89.8 DSC, binary) used a default-planned nnU-Net with a
~50 mm field. icx4 departs from that default on exactly that point.

What the literature does *not* give us is a per-territory benchmark. No published model reports
LM/LAD/LCx/RCA accuracy on ImageCAS-X, and no per-branch coronary model has been tested on another centre.
So this plan's robustness case rests on three things:

- a binary benchmark on the same test cohort (ImageCAS-X Table 2);
- a four-class human ceiling derived from ImageCAS-X's inter-observer table (§7.2);
- an external test this project must run itself (F8).

## 2. Model and architecture

As built in `trillium/icx4` (D25; #43):

| Item | Setting | Evidence |
|---|---|---|
| Framework | nnU-Net v2.8.1, `3d_fullres`, `nnUNetTrainerICX4` (no mirroring, poly LR over 1000 epochs, deadline-safe chunks) | Isensee et al., Nat Methods 2021, doi:10.1038/s41592-020-01008-z; Revisited Table 1 |
| Network | `ResidualEncoderUNet`, 7 stages, features 32–320, blocks 1-3-4-6-6-6-6 (plan `nnUNetResEncUNetPlans_60G_iso05`) | read from `trillium-results/icx14/results/nnUNetResEncUNetPlans_60G_iso05.json`, the same plan icx4 uses |
| Patch, batch | 256³ at 0.5 mm, batch 2 | [[Atlas - A 128 mm patch at 0.5 mm holds the whole tree and the LM in almost every training patch]]; MedNeXt-v2's larger-patch gain (Round 6 note) |
| Window | nnU-Net default CT normalisation | [[Round 8]] (tie-break) |
| Loss | Dice + CE, no class weights | The four classes are large (§3); class weights were an icx14 side-branch fix only |
| Topology loss | none | Skeleton Recall has no coronary result; on multi-class TopCoW it gained +1.2 Dice at +8 % time (Kirchhoff et al., ECCV 2024, arXiv:2404.03010, Table 2). It is a candidate for a later, paired run, not the first job |

## 3. Labels

ImageCAS-X's lumen as drawn (D8), collapsed to four classes by territory (D25, D1, D1b) with
`trillium/icx4/lib/territory.py`. Echo verified it against D25 value by value, with Other assigned to the
nearest LAD/LCx voxel in mm (#49, PR #59).

Census of the 640 train+val label maps (the test split was not opened), from
[[Foxtrot - On ImageCAS-X the four-class human agreement is at least about 92 LM, 89 LAD, 82 LCx and 92 RCA Dice]]:

| Class | Present (of 640) | Median volume mm³ (p10–p90) | Share of tree |
|---|---|---|---|
| LM | 630 | 99 (48–189) | 5 % |
| LAD (+ D1, D2, Other→LAD) | 640 | 573 (391–886) | 29 % |
| LCx (+ OM1, OM2, IM, L-PDA, L-PLA, Other→LCx) | 640 | 428 (212–794) | 23 % |
| RCA (+ R-PDA, R-PLA) | 640 | 808 (427–1521) | 43 % |

- No class is rare enough to need class weights.
- LM is absent in 1.6 % of cases, and it is the smallest class, so its Dice will be the noisiest.
- Other is 0.3 % of tree volume, in 76 cases.

## 4. Data and splits

- **Train 560 / val 80 (fold 0) / test 160**: ImageCAS-X's own split, as icx4 does it.
- **The sealed test stays sealed.** Of the 160 test cases, only **open-36** and **dev-44** are scored, each
  reported separately (#55). The 80 cases sealed under A14 are predicted, because prelabels need every
  case, but they are never scored, summarised or copied into `results/`.
- Predictions for all 1000 ImageCAS volumes are kept (≈ 2–4 GPU-h), as icx4 does.
- Pooled volumes (D23): not used for training in this plan. They are the external test (F8).

## 5. Recipe and schedule on Fir

### F5. Job shape and budget, from a measured loader cost

Fir GPU nodes have 1 × AMD EPYC 9454 (Zen 4, 48 cores, 2.75 GHz), 1125 GB and 4 × H100 SXM5 80 GB. That is
**12 cores per H100**; Trillium gives 24 (docs.alliancecan.ca/wiki/Fir, last edited 21 Jul 2026, read
2026-10-18). Fir's bundle is 12 cores and 288 GB per H100, 12.2 RGU per GPU and 0.98 cores per RGU
(docs.alliancecan.ca/wiki/Allocations_and_compute_scheduling#Ratios_in_bundles, last edited 25 Sep 2026).

The question is whether 10 augmentation workers (icx4's `NPROC − 2`) keep an H100 fed with 256³ batches.
Measured here: [[Foxtrot - On Fir's 12 cores per H100 the icx4 loader may set the pace, so budget four chained jobs]].

- **Measured:** nnU-Net 2.8.1's own loader and augmentation, run on the icx4 plan (256³ patch, batch 2,
  411³ pre-rotation crop) on one CPU thread, costs **7.9 CPU-s per batch** alone (95 % CI 6.6–9.2) and
  **9.4** with three workers contending.
- **The GPU's pace** on Trillium (icx14, same plan): 182.0 s per epoch with no spread, i.e. ≈ 0.69 s per
  training step. To keep up, the loader must supply ≈ 1.46 batches/s.
- **On Fir**, 10 workers supply ≈ 1.06–1.39 batches/s. This assumes Zen 4 is 1.0–1.3× this sandbox's
  Emerald Rapids per core, which I did not measure. The expected epoch is **≈ 190–245 s**, i.e. 5–35 %
  slower than Trillium, and 1000 epochs take ≈ 53–68 h.

**Plan:**
- Keep icx4's Fir profile as is: `--gpus-per-node=h100:1 --cpus-per-task=12 --mem=280G`, `def-aso22`,
  23:50 walltime, `CHAIN=4`.
- Keep the 1000 epochs. The poly schedule must complete (A22), and the chain resumes across jobs.
- **Budget: ≈ 57–73 H100-hours (training 53–68 h, preparation ≈ 1 h, predicting 1000 cases plus aortas and tF1 ≈ 3–4 h), in 3 chained jobs at the fast end and 4 at the slow end.** Four chained jobs give 95 h of walltime, which covers the slow end. Fir allows
  7-day jobs, but the 24 h chain is the tested path (the icx14 resume bug cost 23 GPU-h), so keep it.
- **Not proposed:** asking for 24 cores. At 0.98 cores per RGU, 24 cores cost about 24.5 RGU, twice the
  H100's 12.2. That roughly doubles the fairshare charged for a gain of at most ~25 % in wall time, and
  `def-aso22` runs at opportunistic priority. It is a fallback only (§9).

## 6. Deciding metric

### F6. Decisive tF1 on the open test (#54, #55), endorsed

- **Decisive:** tree-F1 at 1.5 mm (D3), with the A1 ostium from TotalSegmentator aortas, at the A1c hash
  `24441cf8df0f000bd956c7dd9d8ae1daac866cfb14df1d174441d00e54f05254`. I checked this is still
  `src/segtrain/tf1.py` on `dev` today. Flagged trees are reported apart (A1b). Reported per class and
  macro, separately on open-36 and dev-44.
- **Secondary, decides nothing:** Dice per class and whole-tree Dice (icx4's current `score.py`); raw FP
  components per case (A15).
- **Acceptance (A10, D6)** stays as ruled: per class, non-inferior to inter-read tF1 within 0.05, against
  team reads. On ImageCAS-X there are no team reads, so A10 is first applied on pooled volumes (F8).
- **What is not a baseline:** run 1's 0.896. It was trained and scored on the original ImageCAS mask, and
  that agrees with ImageCAS-X at only 41.8 DSC (ImageCAS-X Table 2). icx14's trunk Dice is not one
  either (Echo, #49). icx4's first decisive tF1 *is* the baseline for every later comparison.

## 7. Two outside reads of the first result (F7, pre-registered, zero GPU)

### 7.1 Whole-tree Dice against the published binary benchmark

ImageCAS-X Table 2 (Bransby et al., arXiv:2608.30404, preprint) scores binary-lumen models on the same 160
test scans, against the same reference:

| Model | DSC % |
|---|---|
| TotalSegmentator (zero-shot) | 70.5 |
| nnU-Net (default planner) | 89.8 |
| CAS-Net (best) | 91.2 |
| Two human analysts | 92.8 |

icx4 reports whole-tree Dice on open-36 + dev-44 (80 of those 160). The 95 % CI half-width is about
**±0.7** points (per-case SD 3.2).

| icx4 whole-tree Dice (open-80) | Reading | Action |
|---|---|---|
| ≥ 91.2 | at or above the best published model | none |
| 88.3 – 91.2 | in the published nnU-Net range | none |
| < 88.3 (1.5 below default nnU-Net) | the 4-class model or the recipe loses tree that a default binary nnU-Net finds | check the collapse, window and preprocessing before predictions are used; report to the judge |

### 7.2 Per-class Dice against the four-class human ceiling

The four-class ceiling can be estimated from ImageCAS-X's per-segment inter-observer table. Collapsing
segments to territories can only raise agreement, so the estimate is a floor on the ceiling:
[[Foxtrot - On ImageCAS-X the four-class human agreement is at least about 92 LM, 89 LAD, 82 LCx and 92 RCA Dice]].

| Class | Trunk-only human DSC (ImageCAS-X Table 1) | Four-class floor estimate | Read icx4's Dice as human level if ≥ | Read as failed if < |
|---|---|---|---|---|
| LM | 91.9 | 91.9 | 89 | 84 |
| LAD | 92.3 | 89.4 | 86 | 81 |
| LCx | 84.8 | 81.6 | 79 | 74 |
| RCA | 95.3 | 92.2 | 89 | 84 |

Reading: a per-class Dice within ~3 points of the estimate is at human level for that class. A class more
than 8 points below it is reported as a failure of that class, and the class is examined first in the
miss census. These rules decide nothing about acceptance (A10 decides that). They tell the lead on day 3
whether the predictions are usable.

## 8. External validation (F8, pre-registered)

The open test is one scanner at one hospital, and 91 % of its cases are right-dominant. Across centres,
published segmentation models lose **5–8 Dice points** (binary):

- ImageCAS → ASOCA: 0.831 → 0.767 (Seg2RefineNet, Sci Rep 2025, doi:10.1038/s41598-025-24953-1, Table 3);
- Cleveland → Taipei: 0.794 → 0.741 (Kim et al., JMI 2025, doi:10.1117/1.JMI.12.1.016002, Table 1;
  overall Dice);
- ASOCA → GeoCAD: ≈ 0.86–0.90 → 0.79–0.82 (Zhang et al., JIIM 2025, doi:10.1007/s10278-025-01677-2, Table 4).

Trunk *naming* did not drop across centres (LWT-ARTERY-LABEL, arXiv:2508.06874, Table 2). No per-branch
segmentation model has been tested externally.

**E1. The pooled volumes with team reads are this project's external per-branch test.** SegQueue14 serves
675 pooled volumes from other scanners and centres, each read twice in four classes (D23, D25, D26).

- When the **first 30 double-read pooled cases** are approved, run icx4 inference on them. That is one short
  GPU job, ≈ 0.5 GPU-h (§10, job 2).
- Score decisive tF1 per class against each read (A10's scoring), beside inter-read tF1. Aortas come from
  A21's producer, outside the job.
- Pre-registered: the expected macro tF1 drop from open-80 to pooled is **unknown, prior 0.05–0.10**, by
  analogy with the Dice drops above.
- The minimum detectable effect at n = 30 is to be quoted with the result (A19); on A1-scored per-case
  SD 0.064 (Bridge, Round 8) it is about 0.033.

| Result on the first 30 pooled cases | What it means | What changes |
|---|---|---|
| Passes A10 (every class within 0.05 of inter-read) | the model transfers | nothing; continue to wave fine-tunes (A17) |
| Fails A10, open-80 at human level, drop concentrated in low-contrast or non-Siemens cases | domain shift, as published | the D15-style fine-tune on pooled reads is the lever, not the architecture; report contrast and edge sharpness per case (Zhang et al.) |
| Fails A10 and open-80 also below human level | the model, not the shift | back to the recipe (§9) |

**E2. Binary, public: ASOCA (40 labelled, CC BY 4.0).** This is a lead decision: registration at the UK Data
Service needs ethics evidence. If the lead obtains it:

- score whole-tree Dice and raw FP per case for icx4's prediction, using the binary reference, any class
  counts as vessel (≈ 0.1 GPU-h);
- **pre-registered: Dice ≥ 0.77** (the published ImageCAS-trained zero-shot result) is in line; below 0.70
  is a generalisation failure worth a note to the lead.

ASOCA cannot test naming (binary labels).

**Not proposed:** orCaScore with TopoLab's centreline names (72 CCTA). It would be a per-branch external
test, but the image registration closed in August 2025 and the labels need a Baidu-hosted password. I
list it so the lead knows it exists.

## 9. What results would change the plan

| Observation | Threshold | Change |
|---|---|---|
| s/epoch in the first Fir job | > 300 s after epoch 20 (4 jobs no longer cover 1000 epochs plus prediction) | the lead submits one more job after the chain (`CHAIN=1 ./icx4`; it resumes). No recipe change; the schedule stays at 1000 epochs. If Fir's queue is long, Nibi (14 cores) instead |
| Whole-tree Dice, open-80 | < 88.3 | §7.1: check collapse, window and preprocessing before predictions are used |
| Any class's Dice vs the four-class ceiling | > 8 points below | that class goes first in a miss census (CPU) |
| LCx decisive tF1 | lowest class, as every source predicts | expected; not an alarm by itself |
| FP components per case (raw) | > 1 (A15) | expected (run 1: 1.49). The A24 lesson stands: a fair FP-loss test needs the term at 5–20 % of the loss, paired, two seeds (A22) |
| External E1 | see §8 | fine-tune on pooled reads, or back to the recipe |
| A paired change to the recipe (Skeleton Recall, FP loss, 5 folds) | any | needs two seeds at σ_seed 0.013 if the effect is under 0.02 (A22); never decided on one Fir run |

## 10. Exact first Fir job (for the lead)

**Preconditions.**
- CCDB → Resources → Access Systems → Fir is enabled for your account (≤ 1 h after opting in).
- `dev` contains #55 (sealed filter) and, ideally, #54 (tF1).
- If #55 is not merged yet, start anyway. The scorer runs only after epoch 1000, about three days later,
  and every chained job re-reads `lib/` from the experiment folder. **Before the last job starts, re-copy
  `trillium/icx4/lib/` from a `dev` that contains #55.** Without #55, icx4 would score the sealed 80.

**Job 1: train, predict, score (the whole icx4 chain).** On a Fir login node (`ssh <user>@fir.alliancecan.ca`), in `tmux`:

```sh
export ROOT=$SCRATCH/asclepius
# 1. the repository (or rsync your Trillium checkout)
git clone -b dev https://github.com/christianGRogers/Asclepius.git ~/Asclepius || git -C ~/Asclepius pull --ff-only
# 2. the cases: Globus from Trillium (recommended; ~91 GB):
#    source  alliancecan#trillium  <Trillium $SCRATCH>/asclepius/cases/
#    dest    alliancecan#fir       $ROOT/cases/
#    (no Girder fallback: fetch_cases.py reads SegQueue/cases, which D22 changed; it may no longer hold the 1000 ImageCAS CTs)
mkdir -p $ROOT/cases $ROOT/experiments
ls $ROOT/cases | wc -l                       # expect 1000
# 3. the experiment
rm -rf $ROOT/experiments/icx4 && cp -r ~/Asclepius/trillium/icx4 $ROOT/experiments/icx4
cd $ROOT/experiments/icx4
ICX4_CLUSTER=fir CHAIN=4 ./icx4             # builds the venv, fetches ImageCAS-X labels, submits 4 chained jobs
grep SBATCH $SCRATCH/icx4/job.sh            # expect h100:1, cpus-per-task=12, mem=280G, account=def-aso22
squeue -u $USER --name icx4                 # 4 jobs, the later ones (Dependency)
./icx4 status                               # after ~2 h: the first epochs and s/epoch
```

- **Resources:** 1 × H100 80 GB, 12 cores, 280 GB, 23:50 per job, account `def-aso22`, 4 jobs chained
  (`afterany`).
- **Expected GPU-hours:** ≈ 57–73 H100-hours over 3–4 jobs (training 53–68 h; Trillium would be ≈ 55 h).
- **Send back:**
  - `./icx4 status` after the first job: the s/epoch line;
  - `./icx4 collect` at the end, then `results/` (SUMMARY.md, results.json, logs; < 50 MB).

**Job 2 (later, ≈ 0.5 GPU-h): external test E1.** Once 30 pooled cases have two approved reads. It needs
a small inference-only launcher (`role:swe`, to be opened after this round's ruling): predict the listed
pooled volumes with `checkpoint_final.pth`; aortas and tF1 run outside the job.

## 11. Risks

| Risk | Likelihood | Effect | Mitigation |
|---|---|---|---|
| Fir's loader is slower than estimated | medium | longer wall time, not a worse model | 4-job chain; s/epoch check after job 1 |
| Opportunistic priority means long queue waits | unknown (#46 has no `sshare` output yet) | days of delay | Nibi has the same profile (`ICX4_CLUSTER=nibi`, 14 cores) |
| Fir scratch purge (60 days) | certain over time | loses predictions and checkpoint | `./icx4 collect` at the end; copy `checkpoint_final.pth` to PROJECT (1 TB) |
| Sealed test opened by the old `score.py` | low if §10 is followed | A14 broken | #55 before the last job |
| One seed | certain | no seed CI on the baseline | A22: the first paired decision adds a second seed to its control |
| The ceiling estimate is approximate | certain | §7.2 thresholds are soft | they decide nothing; A10 decides |

## 12. Comparison with the master and other candidates

The master ([[Atlas v9]], with the [[Round 8]] amendments) is a four-class plan on the D0 thick mask.
D8 and D25 replaced that mask. icx4 already implements the D8/D25 recipe, so I keep the master's
amendments where they still apply:

- A1 / A1c tF1;
- A10 at D6's 0.05;
- A11′ two-read samples for team reads;
- A15 FP gate;
- A17 fine-tune trainer;
- A19 MDE statements;
- A22 seed rule.

The proxy-specific amendments (A3's thick-convention monitor, A4's proxy QA, A17c's proxy admission) lapse
with D8. My plan differs from icx4-as-built only by adding F5–F8. It is compatible with any other
candidate that keeps icx4 as the first job.

## 13. Changes since v4

1. A full four-class plan for Fir (D25), replacing v4's amendments to the D0 master.
2. F5: Fir job shape and budget from a measured loader cost.
3. F6: endorses #54 and #55 as the decisive score; run 1's numbers are not a baseline.
4. F7: two pre-registered outside reads of the first result (binary benchmark; four-class ceiling).
5. F8: an external test on pooled team reads, plus ASOCA if the lead registers.
6. Literature updated and three vault citations corrected (Kim et al. is an overall Dice; Zhang et al.
   trains on ASOCA; TreeLab-Net is Wu et al. 2019).
7. v4's items: the low-HU recall column applied to atlas3's FP loss, which ran and was not adopted, so it
   is moot. The human look at 13 FP components stays open, but it concerns the D0 mask and is no longer
   on this plan's path.
