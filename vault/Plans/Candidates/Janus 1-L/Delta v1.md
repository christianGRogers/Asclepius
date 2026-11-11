---
tags: [plans, candidate, janus1-L, track-1L, round1, trillium, four-class, D45, locked100, warm-start, ensemble]
author: Delta
track: 1-L
round: 1
version: 1
updated: 2026-11-11
issue: christianGRogers/Asclepius#302
---

# Delta v1 (track 1-L): warm-start Janus 0 on the 620 twice, read the two runs and their ensemble against Janus 0 on the locked 100 under a pre-registered order, and fix the lumen width with a threshold, not a loss

## 0. Keep, improve or replace the Master plan's Janus 1?

**Keep the recipe, and change the decision and the run design.** The Master plan's Janus 1 (Delta v10, Round 10:
A36–A38) is a warm fine-tune of Janus 0 with ImageCAS-X replay, decided on D35's pool reads. D45 and #302 change three
of its premises:

| Round 10 premise | Now (D45, #302) | Consequence |
|---|---|---|
| Decide on D35's pool reads (G1); val 80 is only a guard | 0 approved reads today; 100 **locked** ImageCAS-X cases, never trained on | **The locked 100 decides.** D35 decides only the later pool stage (§6) |
| Train on 560 + pool reads | Train on **620** (+44 dev, +16 open-36) | 60 cases Janus 0 has never seen: 10.7 % more data, and a clean tuning set for the width rule (§3.4) |
| Three runs: a1, a2 at 1e-2 and b at 1e-3 | Replay is now 100 % of the data | **The b arm loses its purpose.** It existed to protect against forgetting ImageCAS-X while learning pool reads. Its slot goes to the **ensemble of a1 and a2**, which costs no training |

**New evidence this round** (CPU; code in `experiments/Delta/j1l_r1/`; no sealed case, image or locked-100 score
opened):
- [[Delta - D45's locked 100 and training 620, computed from ids, with no sealed case in either]]: the exact 20 + 16
  split of open-36. Pinned file sha256 `19b832fe…4dd3`.
- [[Delta - The locked 100 resolves about 0.011-0.021 tF1, and A38's centreline-recall guard fires on a third of neutral fine-tunes unless it is trimmed]]:
  - the decision's power;
  - a defect in A38's G3 (31 % false alarms at n = 100) and its fix (about 4 %);
  - the ensemble test's sensitivity (about 0.005–0.010).

## 1. The plan in one paragraph

**Janus 1-L is a warm fine-tune of Janus 0.**
- **Data:** the 620 ImageCAS-X training cases, collapsed by D25 exactly as dataset 715.
- **Trainer:** the A17a trainer: full load, 2500-iteration warm-up, poly from peak 1e-2.
- **Length:** 250 epochs.
- **Fixed:** Janus 0's plans and patch, mirroring off, the default window.

**Two runs, a1 and a2,** train as nnU-Net folds 0 and 1 of one dataset, with identical splits. Their ensemble **E** is
then nnU-Net's own two-fold prediction.
- **Order:** a1, a2 and E are read against Janus 0 on the **locked 100** in a pre-registered order (§4).
- **What ships:** the first that passes is shipped. Janus 0 stays if none does.

**Lumen width.** Janus 0 draws the lumen about one voxel inside ImageCAS-X's. This is fixed by a **foreground
threshold** chosen before any locked-100 number is read, on Janus 0's own probabilities for the 60 cases it never trained
on. It is adopted only if tF1 is non-inferior on the locked 100. No loss changes.

**Cost:** about **33 Trillium GPU-h** in four jobs: J0, a1, a2 and E (§5). The plan works on ImageCAS-X alone. Pool
reads join later as a second stage, decided on D35, with the locked 100 as the forgetting guard (§6).

## 2. Data

| Set | Cases | Use |
|---|---|---|
| **Training 620** | ImageCAS-X train 560 + dev 44 + 16 of open-36 (c0123 c0195 c0340 c0416 c0430 c0435 c0447 c0617 c0624 c0660 c0726 c0758 c0772 c0877 c0971 c0984) | nnU-Net training, folds 0 and 1 |
| **Locked 100** | Janus 0's val 80 + 20 of open-36 (c0068 c0102 c0251 c0271 c0323 c0327 c0470 c0545 c0592 c0620 c0644 c0805 c0807 c0824 c0827 c0841 c0908 c0946 c0957 c0996) | nnU-Net's fold val (monitoring only, never trained on), and the decision (§4) |
| **Width-tuning 60** | dev 44 + the 16 above: in training for Janus 1-L, **never seen by Janus 0** | Janus 0's probabilities on them choose the width threshold (§3.4), before any Janus 1-L model exists |
| Sealed | 80 ImageCAS-X test + 20 quality-0 | **Never** read, predicted for scoring, scored or trained on |

- **The split file:** `experiments/Delta/j1l_r1/janus1_split_proposal.json` (sha256
  `19b832fee023986e1dc64b724fbf218fce71942b7f3908f5ae110388ca1b4dd3`), from ids only.
- **The guard:** the `role:swe` issue (§10) copies the file to `configs/janus1/split-2026-11.json` and pins its sha256.
  It adds a guard beside `segtrain.pool_seal` that refuses any locked or sealed id in a training list.
- **The guard's scope:** the split is the same for 1-F (D45), so the guard is shared.
- **Labels:** D25's collapse (`trillium/icx4/lib/territory.py`, dataset 715's labels) on D8's lumen. There are no
  overlaps on ImageCAS-X, so D40 does not arise until pool reads arrive.
- **TotalSegmentator twins:** the project has no list of ImageCAS cases that may be in TotalSegmentator's training data
  (`src/segqueue14/benchmark.py`, `NO_TWIN_LIST`), so nothing is excluded for that reason. TotalSegmentator is used only
  to make aortas for the A1 ostium, never as a label.
- **Pool reads:** none today (10 scored pairs, none approved). §6 says what changes when they arrive.

**The 11 locked cases on an advocate's development list** (c0039 c0152 c0224 c0225 c0400 c0514 c0564 c0566 c0591 c0606
c0950, all val 80) stay in the locked 100.
- **Why they stay:** D45 names val 80 whole, and the comparison is paired, so their inspection biases neither side.
- **What is reported:** L1 on the 89 clean cases, as a sensitivity check. It decides nothing.

## 3. The recipe

### 3.1 Warm start, not from scratch

| | Warm (A17a) | From scratch |
|---|---|---|
| GPU-h per run | ≈ 14 (250 epochs at Trillium's measured 175 s/epoch, R0 in [[Round 5]], plus prediction) | ≈ 52–55 (1000 epochs) |
| Leakage | None: Janus 0 never saw any locked case (D45) | None |
| What it can show at n = 100 | A gain of 0.011–0.021, with a replicate (§4) | The same MDE, for four times the cost |
| Risk | Warm-started nets can generalise worse than fresh ones when data grows: Ash & Adams, *On Warm-Starting Neural Network Training*, NeurIPS 2020, arXiv:1910.08475, abstract ("this warm-starting seems to yield poorer generalization performance than models that have fresh random initializations") | None new |

**Why warm still wins for the first job:**
- **The data grows only 10.7 %** (60 cases).
- **The A17a schedule re-warms to peak 1e-2 for 250 epochs** (25 % of Janus 0's schedule). That is a partial restart,
  not a low-LR polish. MultiTalent's nnU-Net fine-tune uses the same warm-up shape (Ulrich et al., MICCAI 2023,
  arXiv:2303.14444, Methods).
- **The cost is four times lower.**

Ash & Adams's risk is real, and the plan tests it rather than assuming it away. L1 compares the warm model with Janus 0
directly. If it fails, the from-scratch 620 run is the first thing §8 reopens.

### 3.2 Trainer, plans, augmentation, epochs

**Fixed, from Janus 0 (a warm start needs the same network):**
- `nnUNetResEncUNetPlans_60G_iso05`, 3d_fullres;
- 0.5 mm isotropic, 256³ patch, batch 2;
- nnU-Net's default CT normalisation (A27's window check: nothing is clipped);
- **mirroring off** (left/right swaps would teach that an LAD can be an RCA);
- DiceCE with deep supervision.

The ResEnc presets are nnU-Net's own recommendation over the original U-Net (Isensee et al., *nnU-Net Revisited*,
MICCAI 2024, arXiv:2404.09556, Table 1). Changing the preset would break the warm start, and no other preset is
proposed.

**The trainer:** `nnUNetTrainer_segtrain_finetune` (A17a). It does a full load (heads kept) from Janus 0's
`checkpoint_final.pth`, with its sha256 logged, then a 2500-iteration warm-up and poly decay from 1e-2 over 250 epochs.
**250 epochs** is Atlas's measurement: the four vessels' validation pseudo-Dice flattens by epoch 100–200, while thin
structures need the full schedule ([[Atlas - Validation pseudo-Dice of the four main vessels flattens by epoch 100-200, but thin structures need the full schedule]]).

**Augmentation:** nnU-Net's default, minus mirroring, as in Janus 0. No change is proposed, because no evidence here
says one would move tF1 by ≥ 0.011.

### 3.3 Seeds and the ensemble: a1 and a2 as folds 0 and 1

- **The split file** for dataset 718 holds **two identical entries**: train = the 620, val = the locked 100.
- **The runs:** a1 trains fold 0 and a2 trains fold 1, concurrently. nnU-Net fixes no seed, so the two differ in data
  order, augmentation draws and GPU nondeterminism. That is the replicate D28 asked for on the first retrained decision.
- **The ensemble E** is `nnUNetv2_predict … -f 0 1`, nnU-Net's own softmax average. No probability files are stored and
  no new code is needed. nnU-Net ensembles fold models at test time by design: Isensee et al., arXiv:1809.10486, §2.4:
  "we use the five networks obtained from our training set cross-validation as an ensemble to further increase the
  robustness of our models".
- **No measured gain is claimed for E.** It is read in a pre-registered order (§4) and earns nothing it does not show.
- **Its cost:** two forward passes per case at inference (≈ 2× Janus 0's prediction time), and no training.

**Why E and not the 1e-3 arm.**
- **The 1e-3 arm (A17b)** guarded against forgetting ImageCAS-X while learning pool reads (Wald et al., CVPR 2025,
  arXiv:2410.23132, Table 3, brain MRI). With 100 % ImageCAS-X replay there is nothing to forget, so the arm tests a
  question this stage does not have.
- **E is the cheapest lever** with a plausible gain, and its test against a1 resolves about 0.005–0.010, half a single
  run's noise ([[Delta - The locked 100 resolves about 0.011-0.021 tF1, and A38's centreline-recall guard fires on a third of neutral fine-tunes unless it is trimmed]]).

### 3.4 Lumen width and extent: a threshold, chosen before the locked 100 is read

**What Janus 0 does** ([[icx4 - Results]], A27 Dice-row check):
- plain whole-tree Dice 0.880, against a 1-voxel-tolerant Dice of 0.971;
- a volume ratio of 0.867;
- missed voxels at about 237 HU, against 373 HU in the overlap.

Janus 0 places the boundary about one voxel inside ImageCAS-X's, on the dim partial-volume rim. Extent is fine:
centreline recall and precision are 0.94–0.95. **tF1 barely sees width.** Width matters for prelabels (annotators
widen rims by hand, D12) and for any later calibre use.

**The lever: a lower foreground threshold**, not a new loss. Under rule W, a voxel is vessel if 1 − p(background) ≥ t,
and its class is the argmax over the four vessels.

**Pre-registered rule W:**
1. **Job J0** saves Janus 0's probabilities on the **width-tuning 60**. Janus 0 never trained on these cases, and they
   are not locked.
2. **Choose t** from {0.50, 0.45, 0.40, 0.35, 0.30} as the value whose **median volume ratio** (prediction / ImageCAS-X,
   binary) is closest to 1.00. Ties go to the larger t. This is a CPU step on the login node, and it is fixed and
   recorded before Jobs a1/a2 finish.
3. **Apply t to the shipped model** (§4) on the locked 100. **W is adopted** as the shipped post-processing if all three
   hold:
   - paired macro tF1 Δ(W − argmax) has a lower 95 % bound ≥ −0.005;
   - FP components per case rise by ≤ 0.10;
   - the locked-100 median volume ratio moves toward 1.00.
4. **Otherwise** the model ships with plain argmax, and W is reported.

**Why not a loss change.**
- **It would make Janus 1-L differ from Janus 0 in two ways at once,** and the locked 100 cannot attribute a gain of
  0.011 to either.
- **A threshold costs no GPU.** ImageCAS-X's own baselines post-process with a fixed 0.5 threshold (ImageCAS-X,
  arXiv:2608.30404, Table 2 note; [[Delta - Topology losses on coronaries are verified, and they recover branches but do not connect them]]).
- **Topology losses are not proposed either.** On ImageCAS-X, clDice raised the Betti error (8.0 against 5.6; Table 2),
  and Skeleton Recall roughly doubled disconnected components on ImageCAS (BCS, arXiv:2607.28327, Table 2). tF1 counts
  a disconnected recovered branch as missed.

**Residual risk.** t is tuned on Janus 0 and applied to a fine-tune of it. If Janus 1-L's calibration differs, step 3's
volume-ratio clause shows it. In that case t is not re-tuned on the locked 100 (no locked-100 tuning); it is re-tuned in
round 2 on a fresh rule.

## 4. The decision on the locked 100 (pre-registered)

**Scoring.**
- **Metric:** decisive tF1 @ 1.5 mm (D3) at A1c `24441cf8…5254`, with the A1 ostium from TotalSegmentator aortas made
  in Job J0 for all 100 locked cases.
- **Exclusions:** flagged trees apart (A1b); provisional cases decide nothing (A1a).
- **Pairing:** every number is paired per case against **Janus 0 re-predicted on Trillium** in Job J0, on the same
  aortas.
- **Identity check before anything is read:** the re-prediction's val-80 macro must equal Janus 0's Fir value (0.909)
  within ±0.003. In addition, ≥ 95 % of val cases must agree within 0.01. If it fails, the PM is told, and nothing is
  decided.
- **The bootstrap:** by case, with 10 000 resamples.

**The ladder, read in this order; the first rung that passes ships:**

| Rung | Candidate | Ships if |
|---|---|---|
| 1 | **E** = ensemble(a1, a2) | E passes L1–L4 against Janus 0, **and** E − a1 has a lower 95 % bound > 0 |
| 2 | **a1** | a1 passes L1–L4 against Janus 0 |
| 3 | **Janus 0** stays | — ("no gain detected at MDE 0.011–0.021", not "no gain") |

a2 is the replicate. It is never shipped in a1's place (no best-of; A37).

**The checks** (all on the locked 100, against Janus 0; X is E or a1):

| # | Check | Rule | Measured behaviour (n = 100) |
|---|---|---|---|
| L1 | Gain | Macro Δ(X − J0) has a **lower 95 % bound > 0**, **and** a2's mean Δ(a2 − J0) > 0. For X = E, the a2 clause is read on a1 − J0 instead | Size 0.02–0.03. Power at +0.01: 0.26–0.75. At +0.02: 0.74–1.00 |
| L2 | No class lost | No class mean Δ < −0.03 | False alarm ≤ 1 % |
| L3 | Not shortening vessels | For no class: (a) the **10 %-trimmed** mean Δ of centreline recall (ImageCAS-X-traced) < −0.02; or (b) the mean < −0.02 **with** its 95 % upper bound < 0 | False alarm about 4 % (A38's G3 as written: 31 %). It catches a uniform 0.03 loss 99.9 % of the time |
| L4 | Sign on open-20 | Δ(X − J0) on the 20 locked open-36 cases has the same sign as on all 100. A reversal is reported, and the decision stands (A26's rule) | — |
| L5 | Class review (report) | Any class with point Δ < −0.05: list its worst cases for the PM before shipping | — |
| L6 | FP (report; A15 binds only at acceptance) | FP components per case, Δ and CI | — |

**Dice is reported, never decisive** (A28): plain Dice, 1-voxel-tolerant Dice and volume ratio, per class, for J0, a1,
a2, E and W. #302 asks for Dice and tF1, and Dice decides nothing here. That is Round 9's ruling, and this plan does not
reopen it.

**Model decision, not recipe claim** (A37).
- **Model decisions:** L1 compares fixed checkpoints, so it uses the case CI only.
- **Recipe claims:** a claim such as "the warm recipe beats Janus 0's recipe" also needs the seed term, max(σ from
  a1 − a2, 0.012). This plan makes no such claim.
- **Seed-noise check:** if |mean(a1 − J0) − mean(a2 − J0)| > 0.02, the replicate disagrees beyond seed noise. This is
  reported, and later recipe decisions use ≥ 2 runs per arm.

**What counts as "better than Janus 0":** passing rung 1 or 2. The smallest gain this can show is about 0.011 (warm
replicate noise) to 0.021 (Janus 0's case spread). Job J0's exact per-case SD fixes the stated MDE before any Janus 1-L
number is read.

## 5. Trillium jobs (the lead runs them; account `def-aso22`)

| Job | What | Waits on | Walltime asked | GPU-h expected |
|---|---|---|---|---|
| **J0** | Janus 0 re-predicted on the locked 100 (identity check) and on the width-tuning 60 with `--save_probabilities`; TotalSegmentator aortas for the locked 100; tF1; **plan and preprocess dataset 718** (720 cases, CPU on the GPU node) | the `role:swe` launcher (§10); Janus 0's checkpoint copied from Fir | 6 h | 3–4 |
| **a1** | Warm fine-tune, fold 0, 250 epochs; predict the locked 100; tF1 | J0 (`afterok`) | 23:50 | 13–15 |
| **a2** | The same, fold 1 (concurrent with a1) | J0 (`afterok`) | 23:50 | 13–15 |
| **E** | `-f 0 1` ensemble on the locked 100; tF1; probabilities of the ladder's candidate model for W; the ladder's report | a1 and a2 (`afterok`) | 4 h | 1–2 |
| | **Total** | | | **≈ 33 (range 30–40; hard ceiling 2 × 23.8 + 10 = 58)** |

**Timing basis:**
- Trillium R0 measured 175 s/epoch at this patch and batch ([[Round 5]]); Janus 0 ran at 192 s/epoch on Fir.
- 250 epochs is 12.2–13.3 h.
- Janus 0 predicted 1000 cases in 2–4 h, so 100–160 cases take 0.3–0.6 h.
- If an epoch exceeds 330 s, a1/a2 do not finish in one job. The launcher then resumes them in a chained job (icx4's
  `CHAIN` mechanism), at most one more each.

**Every job:**
- 1 × H100 on Trillium (`--gpus-per-node=1`; 24 cores and about 188 GiB come with it);
- `--account=def-aso22`;
- the job **refuses to start** if any sealed id or locked id is in the training list, or if the split file's sha256
  differs from the pinned one.

### The commands (copy-paste, on a Trillium login node, in `tmux`)

**1. Copy Janus 0's checkpoint from Fir** (where Round 9 kept it). Use either Fir path. Globus works too.

```sh
mkdir -p $SCRATCH/janus0
scp fir.alliancecan.ca:projects/def-aso22/$USER/icx4/checkpoint_final.pth $SCRATCH/janus0/ \
  || scp fir.alliancecan.ca:icx4-keep/checkpoint_final.pth $SCRATCH/janus0/
sha256sum $SCRATCH/janus0/checkpoint_final.pth        # send this line back on #302
```

**2. Code and cases, then submit.**

```sh
cd $SCRATCH && mkdir -p asclepius && cd asclepius
git clone -b dev https://github.com/christianGRogers/Asclepius.git repo || git -C repo pull --ff-only
python3 repo/trillium/fetch_cases.py cases              # resumable; skips CTs already present; ends "1000 of 1000 CTs complete"
mkdir -p experiments && rm -rf experiments/janus1l && cp -r repo/trillium/janus1l experiments/janus1l
cd experiments/janus1l
JANUS0=$SCRATCH/janus0/checkpoint_final.pth JANUS1L_DRYRUN=1 ./janus1l    # prints the checks below, submits nothing
JANUS0=$SCRATCH/janus0/checkpoint_final.pth ./janus1l                     # submits J0, a1, a2, E
```

**Check the printout:**
- `layout: girder-ct`, `cases found: 1000`;
- `split: train 620, locked 100, sealed 0, sha256 19b832fe…4dd3 = pinned`;
- `warm start: Janus 0 sha256 <the line from step 1>`;
- `width-tuning 60: 60, none locked, none sealed`;
- `metric hash = frozen (A1c 24441cf8…5254)`;
- four job ids (a1 and a2 depend on J0; E depends on a1 and a2).

```sh
grep SBATCH $SCRATCH/janus1l/job_*.sh                  # --gpus-per-node=1  --account=def-aso22  --time as in the table
squeue -u $USER --name janus1l                         # 4 jobs
```

If a header line is wrong: `scancel $(cat $SCRATCH/janus1l/submitted_jobs)` and tell the PM.

**3. After J0 ends (about 4 h):**

```sh
./janus1l status        # J0: identity check PASS/FAIL, width threshold t chosen and recorded, s/epoch of a1/a2 once training starts
```

If the identity check says FAIL, cancel a1/a2/E (`scancel $(cat $SCRATCH/janus1l/submitted_jobs)`) and post the status
output on #302.

**4. When `./janus1l status` says `DONE` (about 1 day after J0):**

```sh
./janus1l collect       # -> experiments/janus1l/results/: SUMMARY.md (the ladder's verdict), results.json, tf1_per_case_{j0,a1,a2,E,W}.json, width.json, logs
DEST=~/projects/def-aso22/$USER/janus1l; [ -d ~/projects/def-aso22 ] || DEST=$HOME/janus1l-keep; mkdir -p $DEST
cp -r results $DEST/
for f in 0 1; do cp $SCRATCH/janus1l/nnunet_results/Dataset718_*/*/fold_$f/checkpoint_final.pth $DEST/fold_$f.pth; done
```

**Send back on #302:**
- `results/` (small: no weights, no volumes);
- the `./janus1l status` output after J0;
- the `slurm-*.out` of any failed job.

No sealed case is predicted or scored by any of these jobs.

## 6. When pool reads arrive

D35 and the Round 10 machinery stay in force for pool questions. Only the ImageCAS-X side changes: the locked 100
replaces val 80.

| Item | Setting |
|---|---|
| **Base** | Whatever §4 shipped: E's two folds (each fine-tuned, then re-ensembled), a1, or Janus 0 |
| **Stage 2 recipe** | A36 as written, with 620 in place of 560: warm, 250 epochs, ImageCAS-X 620 replay + every trainable pool read, each read a sample (A11′), uniform per sample. Trainable = approved, not sealed, not D35, not reserved, not spacing-suspect (A33–A36) |
| **Overlaps** | D40: voxels claimed by two or more classes become nnU-Net's ignore label |
| **Extended reads (D44)** | Collapsed to four by territory before D40 (D1, D1b, D25). D1–D3 and S1–S3 go to LAD; OM1, OM2 and the ramus go to LCx; SN, conus and RMA go to RCA; PDA and PLB go to the vessel they leave (right → RCA, left → LCx). The **materials** classes: Q1 |
| **Start** | A39's counts: ≥ 25 D35 patients and ≥ 40 trainable primary patients double-read and approved |
| **Decision** | A38's G1 on D35 (pool gain, a2 sign), with **the locked 100 replacing val 80** in G2 (Δ lower bound > −0.02, no class < −0.03) and in G3 **as amended by L3** (trimmed). G4 (open-20 sign), G5 and G6 as written |
| **Below the start counts** | Nothing trains on pool reads, and the Stage-1 model is the base. With 10 scored pairs and none approved, the measurement is a1/a2's ImageCAS-X numbers alone |

## 7. External evidence (each checked at source this round or in the round named)

| Claim | Source | Where | Checked |
|---|---|---|---|
| Warm-starting can generalise worse than fresh initialisation | Ash & Adams, NeurIPS 2020, arXiv:1910.08475 | Abstract (quoted in §3.1) | This round, arXiv abstract page |
| nnU-Net ensembles cross-validation fold models at test time | Isensee et al., arXiv:1809.10486 | §2.4 (quoted in §3.3) | This round, full text |
| ResEnc presets are nnU-Net's recommended baseline | Isensee et al., MICCAI 2024, arXiv:2404.09556 | Table 1 | Rounds 1–9 (vault) |
| Warm-up then full fine-tune in nnU-Net | Ulrich et al., MICCAI 2023, arXiv:2303.14444 | Methods | Round 10 (`experiments/Delta/r10/citations.md` #12) |
| The 1e-3 fine-tune LR (the arm dropped here) | Wald et al., CVPR 2025, arXiv:2410.23132 | Table 3 | Round 10 (#13) |
| nnU-Net on ImageCAS-X: DSC 89.8; clDice raises the Betti error; threshold 0.5 | Bransby et al., ImageCAS-X, arXiv:2608.30404 | Table 2 | Round 1 (Delta), Round 9 |
| Skeleton Recall doubles disconnected components on ImageCAS | Owusu-Ansah et al., BCS, arXiv:2607.28327 | Table 2, §2.3 | Round 1 (Delta) |
| Variance across runs is the size of claimed gains | Bouthillier et al., MLSys 2021, arXiv:2103.03098 | Fig. 3 | Round 10 (#6) |
| CI widths dwarf typical gaps | Christodoulou et al., MICCAI 2024, arXiv:2409.17763 | Abstract, §3 | Round 10 (#11) |

**Not claimed.** No source says that a two-run ensemble raises coronary tF1. E earns its place only through L1 and the
E − a1 test.

## 8. What would change the plan

| Observation | Then |
|---|---|
| J0's identity check fails (val-80 macro ≠ 0.909 ± 0.003) | Stop. The Trillium scorer or prediction path differs from Fir's. Debug before any decision |
| J0's exact per-case SD gives a locked-100 MDE > 0.025 | The ladder stands, but "no gain detected" is expected. Round 2 weighs a larger lever (from scratch, below) against waiting for pool reads |
| a1 and a2 disagree by > 0.02 macro | Seed noise is model-level on this family. Every later recipe question needs ≥ 2 runs per arm (A37) |
| Neither E nor a1 passes L1, and both point Δs are ≤ 0 | The warm recipe adds nothing on 620. **Round 2 costs a from-scratch 620 run** (≈ 52–55 GPU-h, Ash & Adams's case), and the lead's Q7 (final retrain) becomes the vehicle |
| L3 fires (real shortening) | The fine-tune learned to stop early. Check the 60 new cases' label extent against the 560 (CPU, the census) before any rerun |
| W's chosen t lowers tF1 (step 3 fails) | Ship argmax. Width stays a report until a calibre use exists |
| The epoch time on Trillium is > 330 s | One more chained job per run (+≈ 6 GPU-h each). The schedule is never shortened (A25's spirit) |
| Pool reads reach A39's counts | Stage 2 (§6) |
| The lead answers Q1 | The collapse table of §6 is fixed accordingly |

## 9. Questions for the lead

These are lead's calls; none is assumed in the plan:
- **Q1 (D44 → 1-L):** in a pool read, a voxel labelled only as stent, calcified plaque or non-calcified plaque, with no
  vessel class: is it background for Janus 1-L, or ignore?
  - **Recommended: ignore.** Plaque and stent sit in or on the vessel. Calling them background would teach the model
    that a stented or calcified lumen is not vessel. Ignore teaches nothing either way, as D40 does for overlaps.
- **Q2 (D34 within the track, D45):** the models read in this track, in the order E, a1, a2. Recommended names: **Janus
  1-L.1, 1-L.2, 1-L.3**, with the shipped one called **Janus 1-L**.

**For the judge, not the lead:**
- L3 amends A38's G3 for this track. It is a plan rule, not a human decision.
- Dropping the b arm amends A37 for this track. The A17b trainer stays available for Stage 2.

## 10. Implementation (`role:swe`)

One issue, linked from #302 (opened with this PR; to be built only once the round-1 ruling adopts it):
1. **The pinned split:** `configs/janus1/split-2026-11.json`, byte-copied from
   `experiments/Delta/j1l_r1/janus1_split_proposal.json`, with its sha256 pinned in code. The guard
   `segtrain.janus1_split.refuse(ids)` refuses any locked or sealed id, and is called by `segtrain index`/`convert`,
   the trainer and the launcher. Tests: re-derive the 20 from the salt; 0 sealed; 620/100.
2. **`trillium/janus1l/janus1l`**, built from `trillium/icx4`:
   - Trillium's header;
   - dataset 718 from the 620 and the locked 100;
   - a two-entry `splits_final.json`;
   - the A17a trainer installed in the venv, with `SEGTRAIN_FINETUNE_FROM=$JANUS0`;
   - jobs J0/a1/a2/E with the dependencies of §5;
   - the identity check, the W threshold chooser and the ladder report;
   - `status`/`collect`;
   - `JANUS1L_DRYRUN=1`.
3. **No change** to `src/segtrain/tf1.py` (A1c stays `24441cf8…5254`).

## 11. Differences from the Master plan's Janus 1, in one table

| | Master (Delta v10, A36–A38) | Delta v1, track 1-L |
|---|---|---|
| Training data | 560 + pool reads | **620**; pool reads in Stage 2 |
| Deciding set | D35 (G1), val 80 guard | **Locked 100**; D35 only for Stage 2 |
| Runs | a1, a2 at 1e-2; b at 1e-3; ≈ 45 GPU-h on Fir | a1, a2 at 1e-2 as folds 0/1, plus **E** (no training); **≈ 33 GPU-h on Trillium** |
| What ships | a1, or b on a forgetting failure | **E, else a1, else Janus 0**, pre-registered |
| G3 | Point recall Δ < −0.02 (31 % false alarms) | **L3: trimmed, or CI-backed** (about 4 %) |
| Width | Report only | **Rule W:** a threshold tuned on 60 cases Janus 0 never saw; adopted only if tF1 is non-inferior |
