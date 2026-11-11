---
aliases: [Janus 1-L Atlas v1]
tags: [plans, candidate, janus1-l, D45, trillium, four-class, round1]
author: Atlas
track: 1-L
round: 1
updated: 2026-11-11
issue: christianGRogers/Asclepius#302
---

# Atlas v1 (track 1-L): Janus 0 continued on the 620, with its lumen width fixed, judged on the locked 100 by tF1 first

## In one paragraph

**Janus 1-L is a warm continuation of Janus 0 on the 620 D45 training cases.** It uses Janus 0's plans field by
field, the A17a trainer at peak LR 1e-2 and 250 epochs. Two seeds (a1, a2) of this primary arm run, plus one arm
(b) that adds Skeleton Recall loss (w = 1.0).

**The output rule changes, the network does not.** At inference, a voxel is vessel when its background probability
is below a threshold t. That t is fitted once, before any Janus 1-L training, on Janus 0's own predictions of the 60
training cases Janus 0 never saw (dev 44 + open 16).

**The decision on the locked 100 is pre-registered, and tF1 comes first:**
- H1: tF1 non-inferiority at −0.02, with per-class and centreline-recall guards;
- then H2: whole-tree Dice superiority;
- then H3: tF1 superiority.

**"Better than Janus 0" means H1, and H2 or H3.**

**Why this design:**
- **Sixty extra cases should add only 0.001–0.005 tF1**, and the locked 100 resolves 0.011–0.021, so the split alone
  will not be shown better.
- **Janus 0's one known, measured defect** is a lumen drawn about one voxel inside ImageCAS-X's (D8 makes ImageCAS-X's
  lumen the target). It costs about 9 Dice points and almost no tF1. That defect can be fixed, and then seen.

**Pool reads are not needed.** Ten scored pairs and none approved today. When they arrive, they enter through Round
10's A36–A38 path, starting from whichever model this decision adopts.

**Cost:** about 47 GPU-h on Trillium, in four jobs: one ≤ 2 h inference job and three concurrent 23:50 jobs.

## 0. What I keep, change and replace from the Master plan's Janus 1 (Delta v10, Round 10)

| Round 10 (A36–A38) | Here | Why |
|---|---|---|
| Warm fine-tune from Janus 0, A17a trainer, 250 epochs, peak 1e-2 | **Kept** | A warm continuation of this family on in-distribution data moved val-80 tF1 by −0.002 [−0.013, +0.007] (B → F0, §6.2). It is safe and costs about 15 GPU-h, against 55–60 from scratch. There is no domain shift for the 1e-3 arm to protect against |
| Replay ImageCAS-X 560 + pool reads; D35 decides | **Replaced for 1-L:** 620 ImageCAS-X; the **locked 100** decides | D45. Pool reads are 10 scored pairs, none approved. The plan must stand on ImageCAS-X alone (§1.2) |
| fold-0 val = val 80 | fold-0 val = **locked 100** (logged pseudo-Dice only; `checkpoint_final` is used, never "best") | D45: the locked 100 is never trained on. Nothing is selected on it during training |
| a1, a2 at 1e-2 + b at 1e-3 | a1, a2 at 1e-2 + **b = a1's recipe + Skeleton Recall** | A 1e-3 arm answers a domain-shift question this track does not have. The open question here is whether anything beats the split's 0.005. A tF1-targeted loss is the cheapest arm with a plausible effect of that size (§2.4) |
| G1 on D35; G2/G3 on val 80 | **H1–H3 on the locked 100** (§3) | One decision set, one look per candidate |
| No post-processing | **Width threshold t**, fitted on Janus 0's 60 unseen cases | The issue asks for a lumen-width lever. The evidence that width is the whole Dice gap is Janus 0's own (§2.3) |

## 1. Data

### 1.1 ImageCAS-X (D45, D8, D25)

- **Train 620 = ImageCAS-X train 560 + dev 44 + the 16 open-36 cases not locked.**
- **Locked 100 = val 80 + the 20 open-36 cases with the smallest `sha256('asclepius-janus1-locked100:' + id)`.**
- Rebuilt here from the repo's own lists
  ([[Atlas - Janus 1-L, the D45 split rebuilt from the repo's lists, 620 and 100 with no sealed case]]): 620 / 100,
  disjoint, no sealed ImageCAS-X case and no quality-0 case, and together with the sealed 80 exactly ImageCAS-X's 800.
  - Locked 20: c0068, c0102, c0251, c0271, c0323, c0327, c0470, c0545, c0592, c0620, c0644, c0805, c0807, c0824,
    c0827, c0841, c0908, c0946, c0957, c0996.
  - **Pins** (sha256 of the sorted ids, `\n`-joined):
    - locked 100: `bbd9c687818956e2d5664b06fd8c8bd02ddb031e9b9d08036d59cc0e1a4d5895`;
    - train 620: `1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152`.
  - The launcher refuses on any mismatch (§8, swe item 1).
- **Labels:** ImageCAS-X as drawn (D8), collapsed by territory with `trillium/icx4/lib/territory.py` (D25, D1, D1b;
  "Other" → the nearest LAD/LCx). This is dataset 715's exact label code, so Janus 0 and Janus 1-L learn the same target.
- **Never read, scored, predicted or trained on:** the 80 sealed ImageCAS-X test cases and the 20 sealed quality-0
  cases (D27, A14). The launcher stages only the 720 cases above. It does not even predict a sealed case, which icx4
  did for the SegQueue hand-off that 1-L does not need.
- **The 60 Janus-0-unseen training cases (dev 44 + open 16)** have one extra use before training. Janus 0's predictions
  on them are honest held-out predictions, the only ImageCAS-X cases outside the locked 100 where Janus 0's output can be
  calibrated. Job W fits the width threshold on them (§2.3). Dev 44 were inspected in development (A14), which is
  exactly the use they were set aside for.

### 1.2 Pool reads

**Today: none join.** Ten scored pairs and no approved read. 1-L trains and is decided on ImageCAS-X alone. Nothing in
§2–§4 waits for a read.

**When reads arrive**, nothing in 1-L's first decision changes. The pool enters as the next model of the track, by
Round 10's path:
- **Start:** a warm fine-tune from whichever model §3 adopts (Janus 1-L, or Janus 0 if H1 fails).
- **Replay:** the 620 replace A36's 560 as the ImageCAS-X replay set. The locked 100 replace val 80 as the forgetting
  guard (G2/G3), at the same margins (−0.02 macro, −0.03 per class, −0.02 centreline recall).
- **Which reads are trainable:** A36's rule, approved and not sealed (D27/D32), not D35 (D35), not reserved (A34), not
  spacing-suspect. Each read is a sample (A11′).
- **Overlaps:** voxels shared by two or more classes become nnU-Net's ignore label (D40).
- **Extended reads (D44):** collapsed to four by territory (`ICX14_TO_4` or its D44 equivalent) before D40's rule.
  This is a role:swe item for the D44 classes once #280 lands.
- **Decision:** G1 on D35 (A38), starting at A39's counts (≥ 25 D35 and ≥ 40 trainable primary patients double-read).
- **Seed anchoring:** Job S / A40 still applies to the pool model, not to 1-L.

**What changes in this plan when reads arrive:** only the start model of that later fine-tune, and its replay and guard
sets. If reads arrive before 1-L's jobs run, 1-L still runs on ImageCAS-X alone first. Mixing the two would confound the
split's effect with the pool's and leave the locked-100 decision without a clean control.

## 2. The recipe

### 2.1 Start, trainer, schedule

- **Warm start from Janus 0's `checkpoint_final.pth`**, using the A17a trainer (`nnUNetTrainer_segtrain_finetune`):
  - a full load, heads included;
  - a 2500-iteration linear warm-up, then poly decay;
  - **peak LR 1e-2, 250 epochs** (250 iterations of batch 2 each), SGD with Nesterov momentum 0.99, nnU-Net's defaults.
- **Janus 0's plans field by field** (`nnUNetResEncUNetPlans_60G_iso05`), moved to the new dataset with
  `nnUNetv2_move_plans_between_datasets`, which carries the CT normalisation statistics. Re-planning on 620 cases would
  shift the foreground intensity percentiles, and the warm start would see differently normalised input.
  - 0.5 mm isotropic;
  - 256³ patch, batch 2;
  - ResEnc;
  - nnU-Net's own CT window (Round 8's tie-break).
- **Augmentation:** Janus 0's, **mirroring off** (`nnUNetTrainerNoMirroring` behaviour). A left-right mirror swaps the
  LCA and RCA territories that the classes encode. Inference has no TTA, as Janus 0 had none (`--disable_tta`).
- **Loss:** DiceCE as in Janus 0 (a1, a2). Arm b adds Skeleton Recall (§2.4).
- **Why warm and not from scratch:**
  - **No harm, no help:** the measured warm continuation on this family moved tF1 by −0.002 [−0.013, +0.007] (§6.2).
  - **Cost:** about 15 GPU-h against 55–60.
  - **What a scratch run would test:** "Janus 0's recipe on 620", whose expected effect (0.001–0.005) no single pair of
    runs can see.
  - **Ash & Adams' warm-start gap** (arXiv:1910.08475, Table 1: warm-started ResNets generalise worse after their first
    training on part of the data) is the reason to watch, and H1 is the watch.
  - **Exposure:** here the first training saw 90 % of the final data (560 of 620), not their 50 %.
  - **From scratch** stays for the final retrain, once the pool has grown (Round 10's Q7).

### 2.2 Seeds and runs

| Run | Recipe | Seed | Role |
|---|---|---|---|
| **a1** | §2.1, DiceCE | 1 | **The pre-registered ship candidate** |
| a2 | §2.1, DiceCE | 2 | Replicate. Measures σ_g on the master family (A37's open a1 − a2 question). Never shipped in a1's place |
| b | §2.1 + Skeleton Recall, w = 1.0 | 1 | The one recipe arm (§2.4) |

- **The seed** sets torch, numpy and the nnU-Net data-loader seeds (`J1L_SEED`).
- **What a2 − a1 measures:** cuDNN nondeterminism is not removed. Summers & Dinneen (arXiv:2103.04514, abstract: "all
  sources of nondeterminism have similar effects on measures of model diversity") make that the same thing as a seed
  change.
- **Why the replicate:** the Round 10 question "a1 − a2 > 0.02 → recipe decisions need ≥ 2 runs per arm" has never been
  answered on the ImageCAS-X reference, and both tracks (1-L and 1-F) inherit the answer. It costs 15 GPU-h and no
  wall-clock, because the runs are concurrent.

### 2.3 Lumen width: the background threshold t (post-processing, fitted before training)

**The defect** ([[icx4 - Results]], the A27 Dice check on 160 cases):
- 1-voxel-tolerant Dice is 0.97 against plain Dice 0.88;
- predicted volume is 0.87 of ImageCAS-X's;
- centreline recall and precision are 0.94–0.95.

So Janus 0 finds the vessels and draws the boundary about one voxel inside. The missed rim is dim (about 237 HU against
372 HU in the overlap). It is not clipped by the window, and resampling does not cause it: a 0.5 mm round trip keeps
0.994–0.997 Dice ([[Atlas - Resampling to 0.5 mm isotropic loses nothing measurable, 0.7-0.8 mm does]]). Under D8,
ImageCAS-X's lumen is the target, so a model drawing it one voxel thin is wrong by the project's own definition. tF1 is
almost blind to it, which is why it survived Round 9.

**The lever is an output rule, not a new loss.**
- **Rule:** a voxel is vessel if P(background) < t, and its class is the argmax over LM, LAD, LCx and RCA. With t = 0.5
  this is "foreground probability > 0.5", which is almost Janus 0's argmax.
- **Where t comes from:** Janus 0's softmax on the 60 unseen training cases, saved by Job W
  (`nnUNetv2_predict --save_probabilities`).
- **Grid:** t ∈ {0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.95}.
- **Pick:** the smallest t whose median volume ratio (prediction ÷ ImageCAS-X) is ≥ 0.97, among the t that meet both of
  these against t = 0.5 on the same 60:
  - binary centreline precision falls by no more than 0.01;
  - FP components per case rise by no more than 0.2.

  If no t meets all three, t = 0.5: the lever is dropped and H2 tests the network alone.
- **Fitted once, on Janus 0, and frozen** in a JSON beside the job, with its sha256 printed. It is applied unchanged
  to a1, a2 and b.
- **Transfer:** the warm runs start from Janus 0 and continue the same loss, so their calibration should stay close.
  §3's H2 is the test that it did.
- **Why not a loss change:**
  - a boundary-weighted or volume-matching loss would need its own run and arm, and could move tF1 either way;
  - a threshold costs one inference job and can be undone by changing one number.
- **Why not plain dilation:** it would also thicken false positives and the thin distal ends where the model is
  already right.

**Locked-100 decomposition** (report only, not a decision):
- Janus 0 at t against Janus 0 at 0.5 shows what the threshold alone does;
- a1 at 0.5 against Janus 0 at 0.5 shows what the data alone does.

### 2.4 Arm b: Skeleton Recall (tF1's failure mode is cut trees)

- **The loss:** Kirchhoff et al. (ECCV 2024, arXiv:2404.03010), added to DiceCE as L = L_DiceCE + w · L_SkelRecall (§4,
  Eq. 2).
  - **w = 1.0**, the larger of the paper's two settings (w ∈ {0.1, 1.0}). The effect must clear an MDE of 0.011–0.021,
    and §3's guards catch its cost.
  - **What it rewards:** recall of the per-class reference skeleton, dilated (diamond kernel r = 2, as Delta's
    verification records).
  - **Cost:** about 8 % more training time and 2 % more VRAM in the paper. This is the arm's whole extra cost beyond a
    run.
- **Why it is the arm:**
  - **tF1 loses on cut trees.** Janus 0's per-class SD (0.08–0.14) comes from a few trees cut proximally or stopped
    early, and LCx (0.857) is the weakest class.
  - **Skeleton Recall targets missed centreline directly**, and it is the one topology loss that fits a 256³ multi-class
    3D patch. clDice ran out of memory on TopCoW's 13 classes in the paper; Skeleton Recall gained +1.2 Dice there
    (Table 2, as verified in
    [[Delta - Topology losses on coronaries are verified, and they recover branches but do not connect them]]).
- **The known risk, stated up front:**
  - **BCS (arXiv:2607.28327, Table 2, §2.3, as verified by Delta):** on ImageCAS, Skeleton Recall roughly doubles
    disconnected components (β₀ 4.3 → 8.0), with the summary "recovering branches and keeping them connected are
    separable properties".
  - **ImageCAS-X Table 2 (arXiv:2608.30404):** clDice raises Betti error (5.6 → 8.0).
  - **What the guards do:** tF1 forgives gaps ≤ 1.5 mm (D3) and scores longer gaps as breaks. A gain from recovered
    branches can therefore be eaten by new breaks. H1's per-class guard and the FP report see that; the centreline guard
    sees only recall.
- **b is a recipe claim with one seed.** It is adopted over a1 only by §3's rule, never by a best-of.

### 2.5 Not proposed, and why

| Idea | Why not now |
|---|---|
| From-scratch on 620 | Same expected effect as the warm run (≤ 0.005), 4× the cost, unseeable in one pair (§6.2). It is the final retrain (Q7), after the pool |
| A larger network or preset (ResEnc XL) | Janus 0's planner already targets 60 GB at a 256³ patch, beyond nnU-Net's XL memory target. Capacity is not the measured defect |
| Class-weighted CE for LCx | The hook exists (`ce_class_weights.json`), but a weight that moves LCx moves the other classes' boundaries, and LCx's deficit is extent, which b targets |
| Mirroring on | Swaps LCA/RCA territory (D25 classes are sided) |
| Component removal < 100 voxels (ImageCAS-X's rule) | Janus 0's FP is 0.36 per case (A15 met). It is reported, not shipped |
| clDice | Out of memory on multi-class 3D in the Skeleton Recall paper; worse Betti error on ImageCAS-X (Table 2) |

## 3. The decision on the locked 100 (pre-registered)

**Scoring.**
- **Metric:** decisive tF1 @ 1.5 mm (D3) at the A1c hash `24441cf8…5254`, with TotalSegmentator aortas (A1).
  Provisional cases and flagged trees are left out (A1a/A1b), with the same aortas for every model.
- **The aortas are Janus 0's own, copied from Fir.** icx4 made them for exactly val 80 + open-36 + dev-44, which is the
  locked 100 plus the 60.
- **Pairing:** per case against Janus 0, with Janus 0 re-predicted on Trillium in Job W (same software as the
  candidates).
- **Identity check first (A26's spirit):** Trillium Janus 0 at t = 0.5 must reproduce Fir's val-80 decisive macro
  0.909 within ±0.002 (per-case table reported). If it does not, nothing is decided until the PM has found why.
- **CI:** case bootstrap, 10 000 resamples. "Lower bound" means the lower end of the two-sided 95 % CI (one-sided 2.5 %).
- **Dice:** whole-tree (binary union) and per class, on the native grid, as in the A27 Dice check
  (`r10_dice_check.measure`), next to the 1-voxel-tolerant Dice and the volume ratio.

**Who is tested.**
- **a1 is the ship candidate.** a2 is its replicate.
- **b is the only alternative.** For H3, a1 and b each use the 97.5 % CI (Bonferroni over two candidates).
- **Every candidate is scored at the frozen t** (§2.3); Janus 0 is scored at t = 0.5, as it was read.

**The tests, in fixed sequence** (each tested only if the one before passes; this keeps the family-wise error at 5 %):

| # | Test | Rule (candidate − Janus 0, locked 100) | Power on Janus 0's spread (§6.2) |
|---|---|---|---|
| **H1** | tF1 non-inferiority + guards | Lower bound of Δ macro tF1 > **−0.02**, **and** no class mean Δ < −0.03, **and** no class's centreline recall against ImageCAS-X falls by more than 0.02 (G3), **and** FP per case ≤ 1 (A15) | 0.76–1.00 for a neutral model |
| **H2** | Width (Dice superiority) | Lower bound of Δ whole-tree Dice > 0, **and** no class's mean Dice Δ < 0 (point estimate) | Per-case Dice SD 0.023 (val p10–p90); a 0.01 gain is resolved at power > 0.9 if the per-case correlation is ≥ 0.8 |
| **H3** | tF1 superiority | Lower bound of Δ macro tF1 > 0 (97.5 % CI for two candidates), **and** a2's Δ > 0 (for a1) | 0.10–0.26 at a 0.005 gain; 0.76–1.00 at 0.02 |

**Verdicts.**

| Outcome for a1 | Verdict | Then |
|---|---|---|
| H1 fails | **Not adopted.** Janus 0 stays the base | Round 2 diagnoses which guard failed, on locked-100 aggregates only (no per-case tuning on it) |
| H1 passes, H2 fails | **Non-inferior, not shown better.** Janus 0 stays the base | The data alone did not show. Round 2 decides whether the pool fine-tune starts from a1 anyway (the lead's Q3) |
| H1 and H2 pass, H3 fails | **Better than Janus 0 in lumen width, tF1 non-inferior: adopted as Janus 1-L** | It is the base for the pool fine-tune. Its tF1 gain is reported as "not shown" |
| H1, H2 and H3 pass | **Better than Janus 0 in width and tF1: adopted as Janus 1-L** | As above |

**Arm b** goes through the same H1–H3. b replaces a1 as the ship candidate only if:
- b passes H1 and H3;
- a1 fails H3;
- b's point Δ macro tF1 over a1 is > 0.

b against a1 is never a superiority test by itself. Its MDE with one seed is about 0.02–0.03, and ties go to a1. If
both pass H3, a1 ships (pre-registered, not best-of).

**Recipe readings** (report only; these decide later rounds, not this one):
- **σ_g = |Δ(a1 − a2)| / √2** on the locked 100, macro and per class. If |a1 − a2| > 0.02 in macro on the locked 100,
  every later recipe claim in this track needs ≥ 2 runs per arm (Round 10's rule).
- **The two decompositions in §2.3.**
- **Val 80 and locked 20, apart:** the sign only. A reversal is reported, not acted on (A26).
- **Per class:** tF1, Dice, tolerant Dice, volume ratio, centreline recall and precision, FP per case (A15, A23
  extent).

**One look.** Each candidate's locked-100 numbers are computed once, by `./janus1l collect`, after all three runs are
done, and posted whole. Nothing on the locked 100 is used to pick t, an epoch, a checkpoint or a run.

## 4. Trillium jobs (the lead runs them; account `def-aso22`)

All four jobs use the launcher `trillium/janus1l` (§8, swe item 1). It is icx4's launcher (Trillium is its default
cluster) with the D45 split, a warm start and Job W.

**Measured speed on Trillium:** 175 s/epoch at this patch and batch, on the 24-core 1-GPU bundle (R0, Round 5; atlas3
F0, the same warm trainer: `s_epoch_b` 175.85).

**Job shape:** 1 GPU, 24 cores, about 188 GiB (Trillium's 1-GPU bundle), 23:50, `--account=def-aso22`, no
`--partition` and no `--mem` (Trillium's documentation).

| Job | What | Waits on | GPU-h (expected; range) |
|---|---|---|---|
| **0** | Copy Janus 0 (checkpoint, plans, dataset.json) and its 160 aortas off Fir before Fir's 60-day scratch purge (plans.json lives only in `$SCRATCH` there); fetch CTs on Trillium | now | 0 |
| **W** | Janus 0 on the locked 100 + the 60 unseen training cases, with probabilities; identity check; fit t on the 60 | Job 0, swe item 1 | **1.5** (1–2.5) |
| **a1, a2, b** | Three concurrent warm runs: preprocess 620 + 100, 250 epochs, predict the locked 100 at t, tF1 + Dice | W's `t.json` (the launcher refuses without it) | **14.5 / 14.5 / 15.5** (13–18 each) |
| | **Total** | | **≈ 46** (42–56); hard ceiling 2.5 + 3 × 23.8 = 74 |

**Where the hours go in each run:**
- training: 250 × 175 s = 12.2 h (b +8 %);
- preprocessing 720 cases in-job: about 1.5 h, the icx4 measurement scaled;
- prediction of 100 cases: about 0.4 h;
- tF1 on 100 cases: about 0.3 h, CPU in-job.

### Job 0: now (Fir login node, then Trillium login node)

```sh
# --- On Fir (login node): keep Janus 0's run files past the scratch purge, and its aortas for the 160 cases ---
R=$SCRATCH/icx4/nnunet_results/Dataset715_ICX4/nnUNetTrainerICX4__nnUNetResEncUNetPlans_60G_iso05__3d_fullres
KEEP=~/projects/def-aso22/$USER/janus0; [ -d ~/projects/def-aso22 ] || KEEP=$HOME/janus0-keep
mkdir -p $KEEP/aorta
cp $R/plans.json $R/dataset.json $R/fold_0/checkpoint_final.pth $KEEP/
cp $SCRATCH/icx4/aorta/*_aorta.nii.gz $KEEP/aorta/       # val 80 + open-36 + dev-44 only: icx4 made no others
ls $KEEP/aorta | wc -l                                     # expect 160
sha256sum $KEEP/checkpoint_final.pth $KEEP/plans.json      # post both lines on #302
```

```sh
# --- On Trillium (login node), inside tmux ---
mkdir -p $SCRATCH/asclepius && cd $SCRATCH/asclepius
git clone -b dev https://github.com/christianGRogers/Asclepius.git repo || git -C repo pull --ff-only
mkdir -p $SCRATCH/janus0 && scp -r 'croger@fir.alliancecan.ca:~/projects/def-aso22/croger/janus0/*' $SCRATCH/janus0/
#   (if KEEP was $HOME/janus0-keep on Fir, use that path instead)
sha256sum $SCRATCH/janus0/checkpoint_final.pth $SCRATCH/janus0/plans.json   # must equal the Fir lines
python3 repo/trillium/fetch_cases.py cases    # ~91 GB, resumable; asks for the Girder login once. Sealed CTs are fetched
                                              # by this script but the launcher never stages, predicts or scores them
```

### Job W (≈ 1.5 GPU-h)

```sh
cd $SCRATCH/asclepius && git -C repo pull --ff-only
mkdir -p experiments && rm -rf experiments/janus1l && cp -r repo/trillium/janus1l experiments/janus1l
cd experiments/janus1l
J1L_ARM=W JANUS0=$SCRATCH/janus0 ./janus1l
```

**Check the printout:**
- `split: train 620 sha256 1350cb1f…1152 OK; locked 100 sha256 bbd9c687…5895 OK; sealed 0`;
- `janus0: checkpoint sha256 <the Fir line>`;
- `aortas: 160 of 160`;
- the A1c hash line;
- one job id.

**When it is `DONE`:**

```sh
./janus1l status W     # identity: Trillium Janus 0 val-80 macro vs 0.909 (must be within 0.002); t = <value>
./janus1l collect W    # results-W/: identity.json, width_grid.json (all t on the 60), t.json (+ its sha256)
```

If the identity check fails, stop and post `results-W/` on #302. The three runs refuse to start without a passing
`identity.json`.

### Runs a1, a2, b (≈ 44.5 GPU-h, three concurrent 23:50 jobs)

```sh
cd $SCRATCH/asclepius/experiments/janus1l
J1L_ARM=a1 J1L_SEED=1 JANUS0=$SCRATCH/janus0 ./janus1l
J1L_ARM=a2 J1L_SEED=2 JANUS0=$SCRATCH/janus0 ./janus1l
J1L_ARM=b  J1L_SEED=1 JANUS0=$SCRATCH/janus0 ./janus1l      # + Skeleton Recall, w = 1.0
grep SBATCH $SCRATCH/janus1l_a1/job.sh   # --gpus-per-node=1 --time=23:50:00 --account=def-aso22 (no --mem, no --partition)
squeue -u $USER --name janus1l-a1,janus1l-a2,janus1l-b
```

**Check each printout:**
- the split pins, `sealed 0`;
- `warm start: Janus 0 sha256 <…>, heads loaded`;
- `plans = Janus 0's (moved to Dataset720_J1L)`;
- `t = <value> (t.json sha256 …)`;
- `fold-0 val: locked 100 (never trained; checkpoint_final only)`;
- `epochs 250, peak LR 1e-2, warm-up 2500`;
- for b: `skeleton recall w=1.0`.

**After about 2 h:** `./janus1l status a1`. Expect about 175 s/epoch.
- **Up to 300 s/epoch:** let it run.
- **Above 300:** let it run. The chain resumes if a job ends early: `CHAIN=2` is the default, and the spare job exits in
  a minute.

**When all three say `DONE`:**

```sh
./janus1l collect          # scores a1, a2, b and Janus 0 on the locked 100 once, applies §3, writes results/
```

**Send back on #302:**
- `results-W/` and `results/`: `SUMMARY.md` with the H1–H3 table and verdict, `results.json`, per-case tF1 and Dice,
  logs;
- the `slurm-*.out` of any failed job.

No weights, no volumes. No sealed case is staged, so none can be sent.

## 5. External evidence

| Claim | Source | Where | Checked |
|---|---|---|---|
| Data scaling exponents for generalisation error are about −0.07 to −0.35 | Hestness et al. 2017, "Deep Learning Scaling is Predictable, Empirically", arXiv:1712.00409 | §1 ("β_g usually settles between −0.07 and −0.35") | Full text read this round |
| Warm-started models can generalise worse than fresh ones | Ash & Adams 2020, "On Warm-Starting Neural Network Training", arXiv:1910.08475 | Table 1, Fig. 2 | Text read this round |
| Nondeterminism alone varies a model as much as a seed change | Summers & Dinneen 2021, arXiv:2103.04514 | abstract | Title and abstract read this round |
| Skeleton Recall: L = L_generic + w·L_SR, w ∈ {0.1, 1.0}; +1.2 Dice on TopCoW multi-class; about 8 % time, 2 % VRAM; clDice out of memory there | Kirchhoff et al., ECCV 2024, arXiv:2404.03010 | §4 Eq. 2 and the weight sentence (read this round); Table 2 and overhead (Delta, Round 1) | Read, and Delta's verification |
| Skeleton Recall roughly doubles disconnected components on ImageCAS | Owusu-Ansah et al. 2026 (BCS), arXiv:2607.28327 | Table 2, §2.3 | Delta's verification (Round 1) |
| nnU-Net on ImageCAS-X: DSC 89.8, inter-observer 92.8; clDice raises Betti error 5.6 → 8.0 | Bransby et al. 2026 (ImageCAS-X), arXiv:2608.30404 | Table 2 | Title read this round; table by Delta (Round 1) |
| Paired sample size and MDE | Julious 2004, Stat Med 23:1921, doi:10.1002/sim.1783 | §2.2.2, eq. 2.10 | Cited in Round 10, not re-read |

**Reading against ImageCAS-X's own benchmark.** Their nnU-Net reaches 89.8 DSC on their test 160, and Janus 0 reaches
87.9 whole-tree Dice on our open 80. The sets differ (theirs includes our sealed 80), so this is indicative only. But
the 1.9-point gap is the same order as the width deficit §2.3 measures. The lever aims at closing a gap that a standard
nnU-Net on the same labels does not have.

## 6. CPU experiments this round

### 6.1 The split
[[Atlas - Janus 1-L, the D45 split rebuilt from the repo's lists, 620 and 100 with no sealed case]]
(`experiments/Atlas/j1l/split_check.py`). The result is §1.1's counts, pins and lists.

### 6.2 Power on the locked 100, the expected data gain, and a warm continuation
[[Atlas - Janus 1-L, the locked 100 resolves 0.011-0.021 tF1, more than 60 extra cases can be expected to buy]]
(`experiments/Atlas/j1l/power_locked100.py`).

- **MDE at n = 100:** 0.011 (optimistic) to 0.021 (pessimistic, Janus 0's spread).
- **A neutral model** passes a −0.02 non-inferiority margin 0.76–1.00 of the time, and −0.01 only 0.26–0.75.
- **60 extra cases** should add 0.0006–0.0045 tF1.
- **Warm continuation on the same data** (B → F0): −0.002 [−0.013, +0.007].

## 7. What would change the plan

| Result | Then |
|---|---|
| Job W's identity check fails (> 0.002 from 0.909) | Stop. Cross-cluster software or aorta drift is found first; nothing is decided on Trillium until it reproduces |
| No t meets §2.3's conditions on the 60 (precision or FP cost too high) | t = 0.5. H2 tests the network alone, and "better than Janus 0" rests on H3. Round 2 considers a boundary-aware loss arm |
| Width grid shows the volume ratio at t = 0.95 still < 0.95 | The dim rim is not in the probabilities. The width lever needs training (a loss or label change), and Round 2 costs it |
| a1 − a2 > 0.02 macro on the locked 100 | Every later recipe claim in the track needs ≥ 2 runs per arm (Round 10's rule); b's reading is downgraded to "uninformative" |
| b passes H1 and H3 and a1 does not | b ships (§3). Skeleton Recall becomes the track's default for the pool fine-tune |
| b fails H1 through a class drop or FP rise | Skeleton Recall is closed for 1-L. Its component cost (BCS) is confirmed on coronaries |
| Approved pool reads exist before Job W runs | Unchanged: 1-L runs on ImageCAS-X alone first (§1.2) |
| Trillium measures > 300 s/epoch | Each run takes two jobs (`CHAIN=2` already submitted); GPU-h rises to about 20 per run, ≈ 62 in all |
| The lead wants a model with more expected tF1 than 0.005 from 1-L itself | A from-scratch 620 run with Skeleton Recall and two seeds (≈ 120 GPU-h) is the next option. It is not proposed on current evidence |

## 8. role:swe items (to open on the judge's ruling, linked to #302)

1. **`trillium/janus1l`**, built from `trillium/icx4`:
   - **The split:** the D45 split built in code from `sealed_test.json` and ImageCAS-X's filelists, refusing unless the
     two sha256 pins in §1.1 match. A guard like `segtrain.pool_seal` refuses any locked-100 id in training, and any
     sealed id anywhere.
   - **The warm start:** Dataset720_J1L with Janus 0's plans moved by `nnUNetv2_move_plans_between_datasets`; the A17a
     warm-start trainer with `J1L_SEED`, on icx4's no-mirroring trainer base.
   - **Job W:** Janus 0 prediction with `--save_probabilities` on the 160 cases; the identity check; the t grid on the
     60; `t.json`.
   - **The runs:** per-arm workdirs `$SCRATCH/janus1l_<arm>`, prediction of the locked 100 only, the t rule applied in
     collect, tF1 at the frozen hash, Dice from `r10_dice_check.measure`.
   - **`collect`:** applies §3 and writes the H1–H3 table.
   - **Self-tests:** the split pins, the sealed refusal, and the t rule on synthetic arrays.
2. **Skeleton Recall loss** in the warm trainer, a port of Kirchhoff et al.'s per-class skeleton recall with w from the
   environment, with a CPU unit test on a synthetic tube. If it is not ready when W finishes, a1 and a2 run alone and b
   follows (§7 does not change).
3. **The locked-100 list in code** (`configs/janus1/locked100-2026-11.json`, sha256-pinned), shared with track 1-F
   (#303), so both tracks refuse the same 100.

## 9. Questions for the lead (none changes a D-number)

- **Q1. Naming (D34/D45).** Runs read in this track are named in read order. Proposed: a1, a2, b are read as Janus
  1-L.1, 1-L.2, 1-L.3. The adopted one is "Janus 1-L", and the pool fine-tune that follows is 1-L.4.
- **Q2. Job 0 now.** Copy Janus 0's `plans.json`, `dataset.json` and the 160 aortas off Fir `$SCRATCH` now. Fir's
  scratch purge would otherwise take `plans.json`, and without it the warm start cannot be reproduced.
- **Q3. If a1 is non-inferior but not shown better** (H1 passes, H2 fails), should the pool fine-tune still start from
  it rather than Janus 0? Recommended: no. Janus 0 stays the base, and the plan says so in advance. A model that is not
  shown better should not replace one with a longer record.
