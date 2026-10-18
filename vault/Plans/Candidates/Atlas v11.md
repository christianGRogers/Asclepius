---
tags: [plans, candidate, master, nnunet, multiclass, fir, round9, four-class]
author: Atlas
round: 9
version: 11
updated: 2026-10-18
issue: christianGRogers/Asclepius#48
---

# Atlas v11: icx4 on Fir as the master's model, scored by tF1 against ImageCAS-X, sealed test kept sealed, a second seed for σ_seed

> **Why v11, not v10.** The Round 9 brief (#48) asks for "v9 → v10", but `Atlas v10.md` already exists: it was
> written on 2026-10-11 as Atlas's response to the Round 8 ruling (run 3 under A24), never judged, and overtaken the
> same day by the D8–D10 restructure. Candidates are "never edited after the round [they were] submitted in"
> ([[README|Plans README]]), and nothing is discarded, so this Round 9 candidate is **v11**. v10 stays as the record.
> It is missing from [[Plan ledger]]; the ledger is the judge's to update.

## 0. The plan in one paragraph

Train **one four-class nnU-Net v2 ResEnc model (LM, LAD, LCx, RCA; D25)** on **ImageCAS-X as drawn (D8), collapsed by
territory** (`trillium/icx4/lib/territory.py`, verified against D25 by Echo, #49). Use the recipe the master has run
three times on Trillium: 0.5 mm isotropic, 256³ patch, batch 2, mirroring off, nnU-Net's default CT window, DiceCE
with deep supervision, **1000 epochs**, ImageCAS-X's split (560 train / 80 val). The code is **`trillium/icx4`
with PR #66** (the `role:swe` fix for #54/#55: a sealed-case filter, in-job tF1 with TotalSegmentator aortas on the
80 open test cases, and `ICX4_WORK` for a second run). The model and recipe are unchanged. It runs on **Fir with
`def-aso22`**: a full H100 80 GB, 12 cores / 280 GB, a 5-job chain sized for the measured loader risk.

Two things are added on CPU:

- **The decisive score on the 80 val cases.** It uses the frozen tF1 (A1c hash `24441cf8…5254`) against
  ImageCAS-X, with run 2's aortas, and pairs the two seeds (`experiments/Atlas/r9_score_icx4.py`, self-tested).
  #66 scores only the open test cases.
- **A zero-code seal** (`r9_seal_icx_test.py`), to be used **only if #66 has not merged** when the lead starts.

A **second seed** (Job B), concurrent if the lead agrees, measures σ_seed on the master as A22 requires and gives a
two-member ensemble. Team reads from the 675-volume pool (D23) arrive later and enter through the A17 fine-tune
recipe. **Acceptance under D6 needs paired human reads on sealed cases.** Two routes are proposed to the lead (§9):
ask ImageCAS-X's authors for the test re-annotations they already made, or seal a hashed pool subset before any
read is seen.

## 1. Thesis: why this plan, now

1. **The cheapest plan that answers the open question is the right first Fir job.** Nothing about the 4-class
   model on ImageCAS-X has been measured yet:
   - icx14 was cancelled at epoch ~455, with no scores;
   - run 1's 0.896 was on the thick ImageCAS mask, which D8 retired.

   `trillium/icx4` already exists and the lead wrote it for D25. Echo's audit (#49) found the label table correct.
   The compute inventory (#46/#47) made it Fir-ready. Any new recipe element would be decided single-seed, which
   A22 forbids for effects under 0.02. So **run what is built, measure it properly, and buy the seed variance that
   every later decision needs.**
2. **The recipe is still the best-evidenced one.**
   - No published model beats a well-configured nnU-Net on per-branch or multi-class vessel labelling. TopCoW and
     TopBrain were both won by nnU-Net teams.
   - ResEnc is the one upgrade nnU-Net Revisited supports.
   - **No published model segments LM/LAD/LCx/RCA voxels on ImageCAS(-X) at all** (searched 2026-10-18).

   Sources: [[Foxtrot - Nothing published by October 2026 beats a well-configured nnU-Net on per-branch coronary or vessel labelling]];
   [[Atlas - The external evidence for a 4-class nnU-Net on ImageCAS-X, checked against the source texts]].
3. **On the same cohort the model is already near a second human.** icx14's main-segment val pseudo-Dice at epoch
   ~450 against ImageCAS-X's inter-observer DSC (arXiv:2608.30404, Table 1):

   | | LM | LAD | LCx | RCA |
   |---|---|---|---|---|
   | icx14 val pseudo-Dice, epoch ~450 | 0.90–0.91 | 0.90–0.91 | 0.83–0.85 | 0.92–0.93 |
   | ImageCAS-X inter-observer DSC | 91.9 | 92.3 | 84.8 | 95.3 |

   The two are not the same measurement (§7.4). But they say the remaining headroom is small, and that the LCx is
   hard for humans too. The work now is to **measure on the decisive metric** (tF1, which Dice cannot replace:
   [[Delta - Dice cannot see the errors that break a coronary tree]]), not to change the model.
4. **Four classes are easier than fourteen, not harder.** icx14's ten side-branch classes stayed at Dice 0 for
   ~440 epochs because a side branch is locally indistinguishable from its parent
   ([[icx14 - interim check after job 1 (446 epochs), side branches not yet learned]]). D25 merges each side
   branch into its parent's class, which removes that failure mode by construction. What remains is what the master
   has always had to learn: four territories and their boundaries at the carina.

## 2. What carries over from rounds 1–8, and what D8–D26 retire

| Amendment | Status under D8/D22/D23/D25 | In this plan |
|---|---|---|
| **A1/A1a/A1b** aorta ostium; provisional and flagged cases apart | Kept | Open 80: aortas computed in the job (#66). Val 80: run 2's TotalSegmentator aortas (`$SCRATCH/atlas2/aorta`, copied to Fir). Cases without one are provisional |
| **A1c** frozen metric, fallback centreline | Kept; hash `24441cf8…5254` | The scorer refuses any other `tf1.py` |
| **A2/A15** FP gate on the raw prediction, ≤ 1/case at acceptance | Kept | Reported per run; the human question of Round 8 §6.1 stays open |
| **A2 window** (default) | Kept | icx4 uses nnU-Net's window (`prepare.py`) |
| **A3** convention monitor (thin vs thick) | **Retired** by D8 (ImageCAS-X lumen) and D12 (free redrawing) | A per-read thickness ratio against ImageCAS-X-style lumen is report-only on the pool (§5.3) |
| **A4** proxy QA, **A17c** proxy admission | **Retired**: no projected proxy; ImageCAS-X is the label | — |
| **A7** rule renaming as a competitor; softmax at val/test | Kept as a competitor; softmax is not saved by icx4 | Job B's ensemble step saves softmax for val/open (§6.3) |
| **A8/D1b** ramus → LCx | Fixed by D25 | `territory.py` |
| **A9** one tF1 implementation | Kept | `src/segtrain/tf1.py` only |
| **A10/D6** per-class non-inferiority to inter-read tF1, margin 0.05 | Kept, but **no sealed case has two reads yet** | §9 Q2 |
| **A11′** both reads as samples | Kept for pool reads | §5.3 |
| **A12** first-50 report | Kept, on the first 50 pool double reads | — |
| **A14** sealed test | Kept. icx4 as written would score the 80 sealed cases (Echo #49) | #66's filter. Fallback without #66: `r9_seal_icx_test.py` (§4.2) |
| **A17a/b** fine-tune trainer, LR 1e-2 with 1e-3 fallback | Kept | §5.3 |
| **A19** one decisive sealed look; MDE in every table | Kept | §7 |
| **A21** aorta producer before decisive tF1 outside a job | Kept | #66 computes the open-80 aortas in the job; run 2's cover val |
| **A22** seed rule (σ_seed = 0.013 prior; < 0.02 needs ≥ 2 seeds) | Kept | **Job B measures σ_seed on the master** |
| **A23** contrast-supported extent tF1 (report only) | Kept, report only | Not in the first scorer (it needs CT HU); added when the pool reads arrive |
| **A24** run 3 | Done: not adopted. The term was < 0.1 % of the loss, so the idea itself was never tested ([[Atlas - Run 3 result, the FP-aware loss was too weak to test]]) | A properly weighted FP term is a candidate lever after σ_seed (§8) |

## 3. Model and architecture

nnU-Net v2.8.1, `ResEncUNetPlanner` with a 60 GB target, overridden to 0.5 mm isotropic spacing, a **256³ patch** and
**batch 2**: a 7-stage residual encoder U-Net, features 32→320, InstanceNorm, LeakyReLU. Mirroring is off (a mirror
turns an LAD into an RCA-side vessel). Plans name: `nnUNetResEncUNetPlans_60G_iso05`; dataset 715; trainer
`nnUNetTrainerICX4`. Everything is as built in `trillium/icx4`.

| Choice | Evidence |
|---|---|
| ResEnc over plain U-Net / transformers / Mamba | nnU-Net Revisited (MICCAI 2024, arXiv:2404.09556), Table 1: CNN U-Nets best; the Mamba layers "have no effect" |
| 0.5 mm isotropic | [[Atlas - Resampling to 0.5 mm isotropic loses nothing measurable, 0.7-0.8 mm does]]; ImageCAS-X trains at 0.5 mm iso too |
| 256³ patch (a 128 mm field) | It holds the whole tree and the LM in almost every training patch ([[Atlas - A 128 mm patch at 0.5 mm holds the whole tree and the LM in almost every training patch]]). ImageCAS-X's released nnU-Net used a 48 × 56 × 56 mm field |
| 55.6 GiB at batch 2 on H100 | Measured, R0 ([[Atlas - Trillium R0 and short R1 results]]); Fir has the same H100 SXM5 80 GB |
| Default CT window | Round 8 A2 (tie-break) |
| 1000 epochs, poly 0.9 | nnU-Net default (Isensee et al. 2021, arXiv:1904.08128 p. 16–17). Thin tubes lose most from short schedules (nnFoundation, arXiv:2609.26924, Table F30: hepatic vessel 0.638 vs 0.669 and inferior alveolar canal 0.560 vs 0.713 at 150 vs 1000 epochs). Our own curves flatten early, but pseudo-Dice does not see tips ([[Atlas - Validation pseudo-Dice of the four main vessels flattens by epoch 100-200, but thin structures need the full schedule]]) |
| Single fold, not 5 | The only large ablation found: fold 0 vs a 5-fold ensemble, 0.8310 vs 0.8315 (BraTS-GoAT, arXiv:2609.15524). A second **seed** is worth more: it gives σ_seed and an ensemble member (§6.3) |

**Not in the first job, and why.**
- **Skeleton Recall** gave +1.2 Dice on 13-class TopCoW (ECCV 2024, Table 2). The expected effect is below A22's
  0.02 threshold, so a single-seed arm could not decide it.
- **The FP-aware loss at a working weight:** the same reason.
- **Two-stage binary → names:** the named model's own names beat rule renaming in round 5 (A7).
- **Pretrained encoders:** no vessel evidence, and they cannot be loaded into this network
  ([[Foxtrot - Large-scale CT pretraining gains about one Dice point on organs, has no vessel evidence, and cannot be loaded into the master's network]]).

Each of these becomes a two-seed comparison once σ_seed is measured (§8).

## 4. Labels, data and splits

### 4.1 Labels (D25, D8)

ImageCAS-X segmentations as drawn, 14 → 4 by `territory.py`:

| Class (value) | ImageCAS-X classes |
|---|---|
| LM (1) | LM |
| LAD (2) | LAD, D1, D2 |
| LCx (3) | LCx, OM1, OM2, IM (ramus, D1b), L-PDA, L-PLA |
| RCA (4) | RCA, R-PDA, R-PLA |
| — | Other (D3/D4, OM3/OM4) → class of the nearest LAD/LCx voxel, in mm |

Echo (#49) verified all five copies of this table against D25 (120 tests pass). Echo also found that
`segtrain.reads.icx_to_territory` measures "nearest" in voxel indices rather than mm. That matters only for the
pool-read pipeline (`role:swe` #56).

**Census of the four classes on the 720 non-sealed cases**
([[Atlas - The four-class ImageCAS-X labels, census and connectivity]]):

- Every class is one connected piece in ≥ 99 % of cases. The exceptions are 6 detached rami (reached through the
  LM, which tF1 still roots) and 2 LAD cases with a tiny second piece. No label repair is needed.
- LM is absent in 11 cases (1.5 %) and is the smallest class (median 99 mm³).
- "Other" is in 85 cases, 3.7 % of their tree.
- **Side branches are 24–25 % of the LAD and RCA classes and 35 % of the LCx (p90 57 %).** So the 4-class LCx is the
  most composite class. Neither icx14's LCx trunk pseudo-Dice nor ImageCAS-X's LCx inter-observer DSC (both trunk
  only) predicts it.

### 4.2 Splits and the sealed test (A14)

| Set | Cases | Use |
|---|---|---|
| ImageCAS-X train | 560 | training |
| ImageCAS-X val | 80 | **every decision** (fold 0 val). Run 2's aortas exist for exactly these 80: run 1's val set is ImageCAS-X's val split, checked case by case against `per_case_run1.json` |
| ImageCAS-X test, open and clean | 36 | decisive tF1 in the job (#66): the out-of-sample check of the val decision |
| ImageCAS-X test, open development | 44 | tF1 and Dice in the job (#66), reported apart: inspected by advocates before, so biased |
| **ImageCAS-X test, sealed** | **80** | **never scored by this plan's jobs.** Predicted only, as part of "all 1000" for the hand-off. Scored once, at the milestone, under A19 |
| ImageCAS, not in ImageCAS-X | 200 (20 sealed quality-0) | predicted only; never read under D23 (§9 Q3) |
| CCTA pool (D23) | 675 volumes, 26 sources | predicted after training (§5.2); team reads → fine-tune and acceptance |

As built on `dev` today, icx4's `score.py` scores every case in ImageCAS-X's `test.txt`: all 160, including the
80 sealed (Echo, #49).

- **PR #66** (open, `role:swe`, for #55) routes every scoring stage through one filter (`lib/sealed.py`) and
  refuses to start without the sealed list. **This plan assumes #66.**
- **If the lead starts before #66 merges,** `experiments/Atlas/r9_seal_icx_test.py` removes the 80 sealed IDs from
  `test.txt` before submission, with no change to icx4. `score.py` then scores only the 80 open cases, and
  `prepare.py`'s overlap check still holds.

**Never combine the two:** #66's launcher refuses a test split that is not exactly 80 + 36 + 44, so it would
(correctly) refuse a sealed-trimmed `test.txt`. Restore it with `mv test.full.txt test.txt`.

## 5. Recipe and phases

### 5.1 Phase F1: the master on Fir (now)

| Job | What | GPU-h on Fir (estimate) |
|---|---|---|
| **A** | icx4 (with #66), seed 1, 1000 epochs. Then it predicts all 1000 cases, computes aortas for the open 80, and scores the open 80 by tF1 (decisive on open-36; dev-44 apart) and Dice | 55–85 expected, ≤ 110 (§6.2), +0.5 for aortas |
| **B** (lead's choice, recommended) | the same, second seed, **concurrent**: `ICX4_WORK=$SCRATCH/icx4-seed2` (#66) | 55–85, ≤ 110 |
| CPU, login node | `r9_score_icx4.py`: tF1, FP and Dice on the **val 80**, both runs, paired → σ̂_seed | ~2 core-h |
| **E** (after A and B) | ensemble predictions of the val 80 (decision R5) and open 36 (check) with both checkpoints (nnU-Net averages the two models' softmax); softmax saved (A7) | ≈ 1 |

### 5.2 Phase F2: the pool as a domain-shift check (after Job A; no reads needed)

The 675 pool volumes come from 26 sources. Among them are ImageCHD (83, congenital disease), ImageALCAPA (30,
**anomalous origin of the left coronary from the pulmonary artery**) and Taiwan AI CUP (100); 414 are QC "limited".
The model has seen one centre. Before any read exists:

- predict the 675 pool volumes with Job A's checkpoint (≈ 3–4 GPU-h);
- score the **binary** agreement (Dice, clDice) of the collapsed prediction with each volume's TotalSegmentator seed
  (D23), **per source**.

TotalSegmentator is itself only 70.5 Dice against ImageCAS-X (arXiv:2608.30404, Table 2), so the absolute level
means little. What matters is **a source whose median agreement falls well below the pool's**: a domain-shift flag
for that source, reported to the lead before the reads start. ALCAPA cases break the aorta-ostium rule (A1) by
anatomy: their left tree arises from the pulmonary artery. They are reported as their own stratum, and §9 Q4 asks
whether they belong in acceptance.

### 5.3 Phase F3: team reads (when they arrive)

As the master's §2.7 recipe (Round 6, A17), with the D8/D23 changes:

- Reads are pool volumes, two reads each (D23), drawn from the TotalSegmentator seed and redrawn freely to the
  contrast lumen (D12). They are therefore in the ImageCAS-X convention, and **no convention monitor halts a wave**
  (A3 retired). The per-read ratio of read volume to the model's predicted volume is reported, for information.
- Each read is a separate sample (A11′). The third-read trigger stays.
- Fine-tune from Job A's checkpoint with the A17a trainer (warm start, heads kept, warm-up). LR 1e-2 with the
  1e-3 fallback arm (A17b). Training set: ImageCAS-X train (560) plus the reads received.
  - **Every fine-tune decision is a retrained decision** under A22, using the σ_seed from Job B.
- Before wave 1 this needs a segtrain task for the 4-class ImageCAS-X + pool data (Echo's "one gap"). It becomes a
  `role:swe` issue if this plan wins; it is not needed for Phase F1.

## 6. Fir: the exact commands, resources and hours

Fir facts (docs.alliancecan.ca, read 2026-10-18; details and quotes in
[[Atlas - The external evidence for a 4-class nnU-Net on ImageCAS-X, checked against the source texts]] §B):

- 160 GPU nodes, each with 4 × H100 SXM5 80 GB and 1 × EPYC 9454 (48 cores).
- About half the nodes are MIG-split, so a full `h100:1` must be requested.
- The bundle is **12 cores / 288 GB per GPU** (recommended ≤ 280 GB). Over-bundle requests are charged as the
  maximum over GPU, cores and memory.
- Walltime partitions: 3 h / 12 h / 24 h / 72 h / 7 d.
- SCRATCH is 20 TB with a **60-day purge**. Compute nodes have internet. Jobs inherit the submitting shell's
  environment.

icx4's Fir profile already asks for `--gpus-per-node=h100:1 --cpus-per-task=12 --mem=280G`, 23:50 per job
(the 24 h partition, which gets more scheduling chances than the 72 h one).

### 6.1 Job A, the first Fir job (copy-paste; the lead runs it)

```sh
# 0. One-off (≤ 1 h): CCDB → Resources → Access Systems → opt in to Fir for def-aso22 (compute inventory, #46).

# 1. Data, Trillium → Fir (Globus: alliancecan#trillium → alliancecan#fir):
#      Trillium <root>/cases/           → Fir $SCRATCH/asclepius/cases/   (the 1000 ImageCAS cases icx4 walks up to)
#      Trillium $SCRATCH/atlas2/aorta/  → Fir $SCRATCH/atlas2/aorta/      (run 2's A1 aortas, 80 val + 36 open: val scoring)
#    ImageCAS-X labels: icx4 fetches them from Zenodo on the login node (Fir login and compute nodes have internet).

# 2. Code, on the login node. Use dev with PR #66 merged; check it is there:
cd $SCRATCH/asclepius && git clone -b dev https://github.com/christianGRogers/Asclepius.git repo
test -f repo/trillium/icx4/lib/sealed.py && echo "#66 present" || echo "#66 NOT merged: do step 3b"
mkdir -p experiments && cp -r repo/trillium/icx4 experiments/icx4

# 3b. ONLY if #66 is not merged: keep the 80 sealed cases out of icx4's scorer (A14), before icx4 reads the list.
#     (Never with #66: its launcher refuses a trimmed test list.)
#   module load StdEnv/2023 python/3.11.5
#   python repo/experiments/Atlas/r9_seal_icx_test.py $SCRATCH/icx4/icx repo/trillium/sealed_test.json --fetch
#   → "test.txt: 160 -> 80 cases (80 sealed removed)"; exits 2 on any mismatch.

# 4. Submit (login node). CHAIN=5 covers ≤ ~118 h of training + prediction; spare jobs exit within a minute.
cd $SCRATCH/asclepius/experiments/icx4
ICX4_CLUSTER=fir CHAIN=5 ./icx4
#   check the printout: "[icx4] cluster: fir", the sealed filter's group counts (open-36 36, dev-44 44), five job ids;
#   and in $SCRATCH/icx4/job.sh: --gpus-per-node=h100:1, --cpus-per-task=12, --mem=280G, --account=def-aso22

# 5. After ~3 h (job 1 preprocesses for ~1–2 h, then trains):
./icx4 status        # the epoch line; s/epoch = time between epoch lines. Apply §6.2's rule.
```

**Expected:** 55–85 GPU-h for Job A, ≤ 110 h worst case (§6.2), plus ~2 h of preprocessing in job 1, and ~2–4 h of prediction and
~0.5 h of aortas in the last job. Each hour is charged as one GPU bundle (12.2 RGU).

**Send back** (as for Trillium): `./icx4 collect` → `results/` (SUMMARY.md with the decisive open-36 tF1,
results.json, logs). The checkpoint stays on Fir. Copy it out of the 60-day purge zone at the end:
`cp -r $SCRATCH/icx4/nnunet_results $PROJECT/icx4_nnunet_results`.

### 6.2 Hours, and the one pre-registered schedule rule

| Measure | Value | Source |
|---|---|---|
| Trillium, 22 loader workers | 175–182 s/epoch, GPU-bound (loader wait 0.02 %) | R0; icx14 logs |
| GPU step | ≈ 0.72 s per batch of 2 | 181 s / 250 iterations |
| Fir loader workers | 10 (`nnUNet_n_proc_DA = cores − 2`) | `job_body.sh` |
| Augmentation cost per 256³ sample, 1 thread | **3.3–6.1 CPU-s** (n = 56; trimmed / pooled mean), bimodal: ~0.1–1 s without a spatial transform, 5–13 s with one (46 % of samples), rare 36–73 s outliers | [[Atlas - On Fir's 12-core share nnU-Net's loader may set the pace]] |
| Consistency with Trillium | Trillium is loader-bound only if c > 7.9 s; R0 measured a 0.02 % loader wait | ✓ |
| ⇒ Fir epoch | max(181 s GPU, 500 × c / 10) = **181–305 s** (395 s if a Fir core is 1.3× slower) | arithmetic |
| ⇒ 1000 epochs | **≈ 55–85 h expected**, ≈ 110 h worst case | — |

The per-sample cost was measured on a 4-core VM's Xeon, not a Fir EPYC core, and it leaves out reading the
preprocessed data, so job 1 measures it for real.

**Rule (fixed now).** Read s/epoch from the first ~20 training epochs of job 1:

- **≤ 400 s/epoch:** let the chain run (1000 epochs ≤ 111 h, plus ~6 h of preprocessing, prediction and aortas, fits CHAIN=5: 5 × 23.6 h = 118 h).
- **> 400 s/epoch:** cancel and resubmit at 500 epochs. The preprocessing is kept; only the started training is
  discarded (< 3 h):
  ```sh
  scancel $(cat $SCRATCH/icx4/submitted_jobs)
  rm -rf $SCRATCH/icx4/nnunet_results/Dataset715_ICX4/nnUNetTrainerICX4__nnUNetResEncUNetPlans_60G_iso05__3d_fullres
  mv $SCRATCH/icx4/submitted_jobs $SCRATCH/icx4/submitted_jobs.cancelled
  ICX4_CLUSTER=fir ICX4_EPOCHS=500 CHAIN=4 ./icx4      # the trainer reads ICX4_EPOCHS; jobs inherit the environment
  ```
  The poly schedule completes at 500 (A22: the epoch count is set from the time available). The run is labelled
  "500-epoch" in every report.

A 24-core request would halve the loader time but is charged as 2 GPUs for fairshare. It is not the default; the
lead may prefer it to the 500-epoch fallback (it needs a one-line change to the Fir profile).

### 6.3 Job B (second seed) and the ensemble

**Why.** A22 needs σ_seed on the master before any retrained decision under 0.02. The two icx14 chunks already
differ by up to 0.014 pseudo-Dice over the same epochs. Every lever left (a weighted FP term, Skeleton Recall, warm
vs scratch fine-tunes) is a < 0.02 effect. Without σ_seed, none of them can be decided.

**How (with #66).** Submit B at the same time as A, from the same folder:

```sh
cd $SCRATCH/asclepius/experiments/icx4
ICX4_WORK=$SCRATCH/icx4-seed2 ICX4_CLUSTER=fir CHAIN=5 ./icx4   # jobs "icx4-icx4-seed2"; nnU-Net draws a fresh seed
ICX4_WORK=$SCRATCH/icx4-seed2 ./icx4 status                     # same s/epoch rule as A (§6.2), applied to both
```

If the 500-epoch fallback fires, it fires for **both** runs: equal epochs (A22).

**Scoring, σ_seed and the ensemble (CPU + ≈ 1 GPU-h).**

```sh
# login node, after both runs finish. Python: icx4's venv ($HOME/icx14-venv) + `pip install scikit-image`
python repo/experiments/Atlas/r9_score_icx4.py --pred $SCRATCH/icx4/predictions --pair $SCRATCH/icx4-seed2/predictions \
  --icx $SCRATCH/icx4/icx --aorta $SCRATCH/atlas2/aorta --splits $SCRATCH/icx4/splits.json --set val \
  --out $SCRATCH/icx4/r9_tf1_val_AB.json --np 10
#  → decisive val macro tF1 for A and B, paired difference, case and seed-inclusive CIs, sigma_seed_estimate_1df
# ensemble E: B's fold_0 goes in as "fold_1" of A's model folder; nnU-Net then averages both models' softmax
R=nnunet_results/Dataset715_ICX4/nnUNetTrainerICX4__nnUNetResEncUNetPlans_60G_iso05__3d_fullres
cp -r $SCRATCH/icx4-seed2/$R/fold_0 $SCRATCH/icx4/$R/fold_1
# then one 1-GPU job (≈ 1 h): nnUNetv2_predict -d 715 -c 3d_fullres -f 0 1 -tr nnUNetTrainerICX4
#   -p nnUNetResEncUNetPlans_60G_iso05 -chk checkpoint_final.pth --save_probabilities, on the val 80 + open 36 CTs only;
#   score its output with r9_score_icx4.py --pred <ensemble dir> --pair $SCRATCH/icx4/predictions (rule R5).
```

The ensemble job script (input folder of the 116 CT links, sbatch header as icx4's Fir profile, 3 h) is written
when B has finished; it decides nothing beyond R5.

## 7. The deciding metric and the decisions

### 7.1 Metric

**Macro tF1 at 1.5 mm (D3)**, from `src/segtrain/tf1.py` at the A1c hash `24441cf8…5254`, against **ImageCAS-X
collapsed to four classes** (D8, D25), with the A1 aorta ostium. Provisional and flagged trees are kept out of
decisive aggregates (A1a/b). It is reported with:

- the FP gate (A2/A15);
- per-class tF1;
- **per-class Dice**, for the literature (§7.4);
- on the open test cases, #66's in-job tF1 and Dice (`SUMMARY.md`; open-36 decisive, dev-44 apart).

`experiments/Atlas/r9_score_icx4.py` does all of this on CPU. It refuses sealed cases and any other metric hash.
Its self-test passes: a perfect tree scores 1.0, a 3 mm LAD cut drops the LAD to 0.4, an LCx named LAD scores 0, an
off-tree blob counts 1 FP, a case without an aorta is provisional, and pairing and the sealed refusal both work
([[Atlas - A CPU scorer for icx4 at the pinned tF1 hash]]).

**No change to the metric is proposed.** One thing differs from rounds 5–8: the reference is now ImageCAS-X (D8),
so absolute tF1 is not comparable with run 1's 0.896 on the thick mask (convention cost ≈ 0.19 tF1 between
conventions). Every absolute number from this round starts a new series.

### 7.2 Pre-registered decisions (fixed before any Fir result)

All decisions are on the **80 val cases**. The open 36 are reported beside them as an out-of-sample check, and the
sealed cases are never used.

| # | Question | Rule | MDE / note |
|---|---|---|---|
| R1 | Schedule | §6.2: ≤ 400 s/epoch → 1000 epochs; > 400 → 500 | Forced choice |
| R2 | **Does the recipe stand?** | Job A decisive macro tF1 ≥ **0.85** → yes. < 0.85 → the recipe reopens, starting with the per-class split and the flagged-tree review | A guard, not a forecast: run 1's 0.896 (thick) minus D6's 0.05 margin. The thin ImageCAS-X reference traces more distal vessel than the thick mask, so recall may be harder; 0.05 of slack allows for that |
| R3 | LCx guard (Round 8) | LCx decisive tF1 < **0.80** → review calcified LCx cases before Phase F3; the window question reopens | ImageCAS-X's human LCx DSC is 84.8 ± 19.8, so a low LCx alone is not a model failure |
| R4 | **σ_seed** (Job B) | σ̂_seed = √(max(d² − SE²_case, 0)/2) from the paired val difference d. **≤ 0.013:** A22's prior stands. **0.013–0.025:** A22's SE uses σ̂. **> 0.025:** every retrained decision needs ≥ 3 seeds per arm | One pair is a 1-df estimate. Phase F3's fine-tunes add pairs, and the estimate is pooled as they accrue |
| R5 | Ship A or the ensemble E | Ship E if (E − A) macro tF1 on val > 0 with the case CI excluding 0, **and** FP/case not higher (case CI). Else ship A (half the inference) | A decision on fixed predictions, so a case-only CI (A22). MDE about 0.010 |
| R6 | FP gate | Reported. If Job A's FP/case > 1 (expected: no measured model has met it), the Round 8 §6.1 human question is put again, with icx4's census | — |
| R7 | Pool domain shift (§5.2) | A source whose median binary agreement with its TotalSegmentator seed is < 0.75 × the pool median is flagged to the lead before reads start | Report only |

### 7.3 Acceptance (unchanged in substance: A10/D6, A15, swaps)

Per class, on the sealed reads: model mean-against-reads tF1 non-inferior to inter-read tF1 at margin **0.05**
(paired bootstrap lower bound > −0.05). Also FP ≤ 1/case raw, and swap rate < 5 %. Under D22/D23 **no sealed case has
two reads**, so the lead must choose where they come from (§9 Q2).

### 7.4 External yardsticks: what is comparable and what is not

| Ours | Published | Comparable? |
|---|---|---|
| Per-class Dice on the open test (ImageCAS-X, 4-class territories) | ImageCAS-X inter-observer DSC per **main segment**: LM 91.9, LAD 92.3, LCx 84.8, RCA 95.3 (Table 1) | Same cohort and lumen. **Not the same classes**: ours include the side branches, which are 24–25 % (LAD, RCA) and 35 % (LCx) of the class volume (census). Report-only, never "human-level" |
| Whole-tree Dice on the open test (icx4's `tree_dice`) | ImageCAS-X Table 2, binary, 160 test cases: nnU-Net 89.8, CAS-Net 91.2, inter-observer 92.8, TotalSegmentator 70.5 | **Close**: same lumen and same kind of number. But our 80 open cases are a subset, and the paper's nnU-Net is the auto-planned 3d_fullres (a 48 × 56 × 56 mm field) |
| Decisive per-class tF1 | Hampe 2024 (J Med Imaging 11:034001), automatic tree + naming, segment F1: LM 0.70, LAD 0.86, LCx 0.74, RCA 0.90 (25 cases) **[WF; re-read before quoting]** | Same task (detect + name). **Different** matching rule, 10 AHA classes, other data |
| — | CPR-GCN (CVPR 2020), labelling of *reference* centrelines: F1 0.976–0.990 | Upper bound on naming only; not comparable with tF1 |
| Run 1 tF1 0.896 (thick) | — | Not comparable with any ImageCAS-X number (convention) |

## 8. What would change the plan

| Result | Change |
|---|---|
| R1: > 400 s/epoch | 500-epoch schedule (already pre-registered) |
| R2 fails (macro tF1 < 0.85) | The recipe reopens. First look: flagged/provisional share, the per-class split, the cut census on ImageCAS-X. Candidate levers: Skeleton Recall, a weighted FP term (λ set so the term is 5–20 % of the loss), patch/context. Each is two seeds per arm |
| R4: σ̂_seed > 0.025 | ≥ 3 seeds per arm for every retrained decision. Phase F3's wave decisions get more expensive; the wave plan is re-costed |
| R4: σ̂_seed ≤ 0.013 and R2 passes | The next GPU work is the first two-seed lever comparison (FP term at a working weight, or Skeleton Recall), chosen by Job A's FP census |
| R7: a source flags | Its volumes go to the lead as a stratum; reads from it are reported separately in every wave |
| #66 is not merged when the lead starts | Step 3b (the zero-code seal); B runs after A unless `ICX4_WORK` exists |
| The lead declines Job B | A22's prior stays; the first Phase F3 retrained decision must add the second seed to its control (Round 8's fallback) |
| The ImageCAS-X authors share the test re-annotations (§9 Q2a) | The 80 sealed ImageCAS-X cases become the D6 acceptance set, on the training cohort |
| D25/D8 change again | Re-plan. Nothing here assumes more than the label table and the lumen |

## 9. Decisions for the lead

1. **Job B (second seed): yes or no.** It doubles Phase F1's GPU (≈ 55–85 h more). Atlas recommends yes, run
   concurrently with A (`ICX4_WORK`, #66): Fir has 640 H100s, and σ_seed blocks every later decision.
2. **Where D6's paired reads on sealed cases come from.** D22 means the 80 sealed ImageCAS-X cases will never be read
   by the team, and D23 means the 20 sealed quality-0 cases will not be either. Options:
   - **(a)** Ask ImageCAS-X's authors (Bransby et al.) for the test-set re-annotations their paper describes ("each
     test case was additionally re-annotated by a different analyst"; arXiv:2608.30404, §Data Subsets). They are
     not in the Zenodo release (checked 2026-10-18: 800 segmentations, 1600 centrelines, 800 surfaces, no second
     reads). If shared, A10 runs on the 80 sealed ImageCAS-X cases with ImageCAS-X as read 1 and the re-annotation
     as read 2. **Recommended:** it is the training cohort and needs no annotator time.
   - **(b)** Seal pool **patients** (not volumes: the 675 volumes are only ~517 patients), hash-ranked within source,
     **before any pool read is seen**. They are scored at the milestone against their two team reads. Bridge v8
     sizes this at ~150 patients from run 1's per-case spread (97 % power if the pool varies like ImageCAS val, 58 %
     if 1.5× more), with the LCx binding. Atlas adopts Bridge's sizing and draw rather than duplicating it. This
     measures the deployment distribution; (a) does not.
   - Atlas recommends **both**: (a) for the model on its own cohort, at no annotator cost; (b) for the pool. Under
     (b) alone, acceptance waits for ~300 sealed reads.
3. **The 20 sealed quality-0 cases.** Under D23 they will never be read. Retire them from A14 as historical
   (recommended), or route them to SegQueue14 last.
4. **Anomalous anatomy in acceptance.** ImageALCAPA (30 volumes) has a left tree arising from the pulmonary artery,
   and ImageCHD (83) is congenital. D25's territory rule and A1's aorta ostium assume normal anatomy. Atlas
   recommends reporting them as a separate stratum, outside the D6 acceptance aggregate.
5. **Carried over:** the FP gate's achievability (Round 8 §6.1), now to be asked on icx4's numbers.

## 10. Risks and early signals

| Risk | Early signal | Response |
|---|---|---|
| Fir lands the job on a MIG slice or with 1 core | `nvidia-smi` line in `slurm-*.out` (80 GB?); `cores 12` in the job banner | The Fir profile requests both; `scancel` and check `ICX4_CLUSTER=fir` |
| Loader-bound epochs | s/epoch in `./icx4 status` | §6.2 rule |
| The sealed test leaks | The launcher printout lacks the sealed filter's counts; `SUMMARY.md` lists more than open-36 + dev-44 | #66's filter refuses to start without the list; fallback step 3b; `r9_score_icx4.py` refuses sealed IDs |
| Resume bug (icx14 lost 23 h) | "training from scratch" in a later job's log | Fixed in icx4 (resume from either checkpoint) |
| 60-day scratch purge | — | Copy results and checkpoint to `$PROJECT` at the end (§6.1) |
| Long queue waits (`def-` opportunistic priority) | Job pending > 24 h | The 24 h partition is already the shortest the run fits; Nibi takes the same command (`ICX4_CLUSTER=nibi`) |
| Domain shift to the pool | §5.2 per-source agreement | Strata; per-source reporting; the reads fix it through Phase F3 |
| 4-class boundaries at the carina | The LM per-class tF1 and the 5 % short-LM fallback cases (A1c) | Reported per class; a known, small term |

## 11. Cost

- **GPU (Fir):**
  - Job A: 55–85 h expected, ≤ 110 h.
  - Job B: the same (if approved).
  - Ensemble: ≈ 1 h.
  - Pool prediction: ≈ 3–4 h.

  Phase F1 + F2 total: **≈ 60–90 h with A only** (≤ 115 h), **≈ 115–175 h with B** (≤ 225 h). Phase F3 is as v10 §2.7.5
  (≈ 170 H100-h to the final model), re-costed after R4.
- **CPU:** login-node scoring, ≈ 2 core-h per run.
- **Lead time:**
  - the Globus copies (cases ≈ tens of GB; pool CTs 54 GB for Phase F2);
  - the CCDB opt-in;
  - one `./icx4 status` look after ~3 h;
  - `collect` at the end.
- **Engineering:**
  - PR #66 (`role:swe` #54/#55: sealed filter, in-job tF1, `ICX4_WORK`), already open. Without it, step 3b
    keeps the seal and B runs after A;
  - a segtrain task for 4-class team reads (before wave 1, only if this plan wins).

## 12. Evidence index (new this round)

| Claim | Evidence |
|---|---|
| Main-vessel pseudo-Dice flattens by epoch 100–200; run 1's LR tail added 0.005–0.016 | [[Atlas - Validation pseudo-Dice of the four main vessels flattens by epoch 100-200, but thin structures need the full schedule]] |
| Short schedules hurt thin tubes most (150 vs 1000 epochs) | nnFoundation arXiv:2609.26924, Table F30 (checked by eye) |
| Fir hardware, bundle, partitions, charging, environment inheritance | [[Atlas - The external evidence for a 4-class nnU-Net on ImageCAS-X, checked against the source texts]] §B |
| Loader may be the bottleneck at 10 workers | [[Atlas - On Fir's 12-core share nnU-Net's loader may set the pace]] |
| 4-class label census, side-branch share, connectivity | [[Atlas - The four-class ImageCAS-X labels, census and connectivity]] |
| ImageCAS-X inter-observer per segment; no published per-branch model on ImageCAS(-X) | arXiv:2608.30404 Table 1 (checked by eye); search list in the literature note |
| The test re-annotations are not in the Zenodo release | Zenodo 10.5281/zenodo.21887809 zip listing, 2026-10-18 (§9 Q2) |
| The collapse matches D25; icx4 would score the sealed 80 | Echo, #49 (first audit summary) |
| tF1 scorer at the pinned hash, self-tested | [[Atlas - A CPU scorer for icx4 at the pinned tF1 hash]] |

## 13. Changes since v10 (and v9, the last judged version)

- **Restructured for D8–D26.** The thick-mask apparatus is retired (A3, A4, A17c, the proxy). The label is ImageCAS-X
  collapsed by D25, and the reference is ImageCAS-X.
- **Compute: Fir**, through icx4's existing profile, with a pre-registered schedule rule for the loader risk.
- **Sealed test protected** by #66, with a zero-code fallback (step 3b). A decisive val-80 scorer with seed pairing added.
- **Job B, a second seed**, proposed to measure σ_seed on the master (A22's open item).
- **Acceptance under D22/D23:** two sources of sealed paired reads proposed (§9 Q2).
- **Run 3 closed:** not adopted. The idea is not refuted: the term was too weak to test.
- **v10's D7 correction** is moot under D12 (free redrawing), and is kept as the record.
