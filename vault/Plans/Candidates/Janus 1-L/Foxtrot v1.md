---
tags: [plans, candidate, janus1-L, D45, trillium, four-class, warm-start, ensemble, locked100]
author: Foxtrot
track: 1-L
round: 1
version: 1
updated: 2026-11-11
issue: christianGRogers/Asclepius#302
---

# Janus 1-L, Foxtrot v1: two warm runs on the 620, ship their ensemble, and make one powered decision on the locked 100

## 0. The plan in one paragraph

Janus 1-L is a **warm fine-tune of Janus 0 on D45's 620 ImageCAS-X cases**: Round 10's A17a trainer, 250 epochs, peak LR 1e-2,
Janus 0's plans byte for byte. There are **two independent runs (s1, s2)**, and what ships is **their softmax ensemble E**. It is
one network pair, not best-of. The pair also measures the seed term that every later recipe claim needs (A37).

**Pool reads do not enter Janus 1-L.** The first pool fine-tune starts from Janus 1-L when Round 10's A39 holds.

**There is one pre-registered decision, E against Janus 0, on the locked 100.**
- Metric: decisive macro tF1, paired by case.
- **Better** = the lower 95 % bound > 0, no class mean Δ < −0.03, and FP ≤ 1 per case.
- On the measured paired spread this detects a gain of about **0.012** (CPU experiment, §4).

**Cost on Trillium: about 30 GPU-h.** Before any training job, a 1 GPU-h check confirms that Janus 0's checkpoint reproduces on Trillium.

**No loss change for lumen width.** That costs Dice, not tF1, and a recipe change cannot be resolved on 100 cases. A width
offset is measured as a cross-fitted report instead.

## 1. What I keep from the Round 10 plan, what I change, and why

The starting point is Delta v10 as amended in Round 10 (A36–A38): a warm fine-tune with replay and the J1 gates.

| Round 10 (Janus 1, pool-driven) | Janus 1-L, Foxtrot v1 | Why |
|---|---|---|
| Warm start from Janus 0, A17a trainer, 250 epochs, warm-up then poly | **Kept** | The cheapest path that keeps Janus 0's features. It is ≈ 13 GPU-h a run against ≈ 50 from scratch on Trillium (§5). Scratch-vs-warm is a recipe claim that the locked 100 cannot resolve below ≈ 0.05 (§4.3). |
| Data: ImageCAS-X 560 + pool reads | **ImageCAS-X 620 only** (D45) | Pool reads: 10 scored pairs, none approved. §6 says what changes when reads come. |
| Runs: a1, a2 (1e-2), b (1e-3) | **s1, s2 (1e-2); no 1e-3 arm** | The 1e-3 arm exists for forgetting under a pool shift (A17b). Here the new data is the same distribution as 90 % of the old, so there is nothing to forget towards. Its 14 GPU-h buy no decision. |
| Ship a1; a2 is the replicate, never shipped | **Ship the ensemble of s1 and s2** | It uses the replicate instead of discarding it, and it removes the seed lottery from the shipped model (§3.3). |
| Decision set for ImageCAS-X: val 80 | **Locked 100** (D45) | Val 80 + 20 open-36, never trained on (§2). |
| Gates G1–G6 | **One decisive comparison** with a class guard and the A15 FP gate (§4). G3 (seed learning) is not needed until pool reads join | G1 was a pool gain; there is no pool here. G3 guards against learning a seed's extent; ImageCAS-X has no seeds. |
| Compute: Fir | **Trillium** (D45) | Commands in §5. Trillium's measured 181 s/epoch for this exact plan (icx14, 256³, batch 2) costs the runs. |

## 2. Data (D45, D8, D25, D27/D32)

### 2.1 The split, computed

The locked 20 are the open-36 ids with the smallest `sha256('asclepius-janus1-locked100:' + id)`
(`experiments/Foxtrot/j1l/locked100.py`; [[Foxtrot - On the measured paired spread the locked 100 resolves a macro tF1 gain of about 0.011-0.013, and a recipe claim only about 0.05|note]] §1):

- **Locked 20:** c0068, c0102, c0251, c0271, c0323, c0327, c0470, c0545, c0592, c0620, c0644, c0805, c0807, c0824, c0827,
  c0841, c0908, c0946, c0957, c0996 (sha256 of the comma-joined list `81b6b526…c7c6f4dc`).
- **Trained 16 of open-36:** c0123, c0195, c0340, c0416, c0430, c0435, c0447, c0617, c0624, c0660, c0726, c0758, c0772,
  c0877, c0971, c0984.
- **Training 620** = ImageCAS-X train 560 + dev-44 + those 16.
- **Locked 100** = ImageCAS-X val 80 + the locked 20. It is nnU-Net's fold-0 val (§3.1).
- **Sealed and never read:** the sealed 80 and quality-0 20. Nothing here touches them.

### 2.2 Labels and data rules

- Labels are ImageCAS-X as drawn (D8), collapsed by `territory.to_four` (D25). This is exactly dataset 715's conversion, applied to 720 cases.
- No TotalSegmentator twin and no pool volume is used.
- D40 (the overlap ignore label) applies only to pool reads, so it does not arise here.

## 3. The recipe

### 3.1 Settings

| Item | Setting |
|---|---|
| Start | Janus 0's `checkpoint_final.pth`, loaded in full (heads included) by `nnUNetTrainer_segtrain_finetune` (A17a). Never `-pretrained_weights` |
| Plans | **Janus 0's plans file, unchanged:** ResEnc 60G, 0.5 mm isotropic, patch 256³, batch 2, `CTNormalization` with Janus 0's own intensity properties (0.5/99.5 % = 61/808 HU on this dataset). Moved to the new dataset with `nnUNetv2_move_plans_between_datasets`, then `nnUNetv2_preprocess`. **The 620 are never re-fingerprinted**: a new fingerprint changes the normalisation constants, and `finetune_load` refuses (correctly) |
| CT-window check | **`SEGTRAIN_CT_WINDOW=61,808`** (Janus 0's window). Without it the A17a trainer refuses: it expects the D0-era fixed window (−300, 1300) (`ct_window.py`). Atlas's window ablation found no difference between the two windows (B − run1 macro −0.003, CI [−0.012, 0.006]), so Janus 0's window is kept, not changed |
| Epochs | 250 × 250 iterations; 2500-iteration linear warm-up to peak 1e-2, then poly (the A17a defaults) |
| Augmentation | nnU-Net's default, **mirroring off** in training and inference (the trainer enforces it; it keeps left and right from swapping) |
| Sampling | Uniform over the 620 |
| Validation | nnU-Net fold 0 = **locked 100**. The pseudo-Dice is a progress display only. **`checkpoint_final.pth` is the model; `checkpoint_best` is never used.** The final validation writes the softmax (`SEGTRAIN_SAVE_PROBABILITIES=1`, the default), which the ensemble needs |
| Runs | **s1 and s2**: two independent launches of the same job. nnU-Net's data order and cuDNN are not seeded, so the runs differ as two seeds do |
| Shipped model | **E = `nnUNetv2_ensemble` of s1 and s2** (mean softmax, argmax). Predicting with E costs 2× inference, about 1 min a case |
| Base for later fine-tunes | **s1**, pre-registered (a warm start needs one network) |

### 3.2 Why warm, and its known risk

- **Cost.** Warm is 13 GPU-h; scratch is 50 GPU-h a run on Trillium (1000 × 181 s).
- **Resolution.** "Warm beats scratch" is a recipe claim. With A37's seed term it has an MDE of ≈ 0.05 on the locked 100 (§4.3), so it cannot be settled here.
- **The known risk.** Warm-started networks can generalise worse than fresh ones trained on the same data (Ash & Adams, *On
  Warm-Starting Neural Network Training*, NeurIPS 2020, arXiv:1910.08475; abstract: warm-starting gives "poorer generalization
  performance than models that have fresh random initializations"; Round 10 found the paper; I have read the abstract, not the tables).
  **The locked-100 decision is exactly the check for this:** a warm model that generalises worse fails the guard or comes out
  NOT ADOPTED, and Janus 0 stays.
- **The full retrain.** A from-scratch run on the 620 remains Round 10's Q7 for the lead, after the pool waves.

### 3.3 Why an ensemble of the two runs, and what it costs

1. **It removes the seed lottery from the shipped model.**
   - A single run's macro tF1 differs from a replicate's by a run-level term of up to σ ≈ 0.012 (A37's floor). With one run
     shipped, that term is drawn once.
   - Averaging two runs halves its variance, if the two runs' errors are independent at the run level. Ensembling probabilities
     is not exactly averaging scores, but it moves in the same direction.
   - This is the variance argument; it holds whether or not the mean improves.
2. **The external evidence is that ensembles do not hurt segmentation and usually help.**
   - Mehrtash et al., *Confidence Calibration and Predictive Uncertainty Estimation for Deep Medical Image Segmentation*,
     IEEE TMI 39(12):3868–3878, 2020, doi:10.1109/TMI.2020.3006437, arXiv:1911.13273.
   - Their Table II, single Dice-loss model against an ensemble of 50:
     - heart (ACDC) RV 0.84 → 0.87, myocardium 0.81 → 0.83, LV 0.92 → 0.93;
     - prostate 0.88 → 0.90;
     - brain tumour 0.45–0.67 → 0.51–0.74.
   - Their Discussion: "the segmentation accuracy in terms of the Dice coefficient and Hausdorff distance was also improved
     through ensembling."
   - **Caveat:** that is M = 50, not 2, and Dice, not tree-F1. I expect a smaller gain at M = 2, and I claim no number for it.
   - Kamnitsas et al., *Ensembles of Multiple Models and Architectures for Robust Brain Tumour Segmentation* (EMMA,
     arXiv:1711.01468), is the BraTS 2017 winner (first of 50+ teams). It is cited for the same direction, not for a size.
   - nnU-Net's own default inference is an ensemble of five folds (Isensee et al., Nat Methods 2021,
     doi:10.1038/s41592-020-01008-z). Janus 0 is a single fold, so E moves it towards nnU-Net's default.
3. **Cost.** No extra training: the second run is the replicate that A37/D28 wanted anyway. Inference doubles (≈ 1 extra GPU-min per case).
4. **What it does not do.** It cannot be the warm-start base. s1 is pre-registered for that, so no later choice is best-of.

### 3.4 What gain to expect (an opinion, labelled as one)

- **60 more training cases is an 11 % increase over 560.** Janus 0's centreline recall is already 0.94–0.97 on val. I expect the
  data alone to move macro tF1 by well under the ≈ 0.012 MDE. I have no measurement of the learning curve.
- **The 250 extra epochs at a re-warmed LR are a second, small lever.** Atlas's curves show thin structures still improving late in
  the schedule ([[Atlas - Validation pseudo-Dice of the four main vessels flattens by epoch 100-200, but thin structures need the full schedule]]).
- **The ensemble is the third lever.**
- **The honest prior is that "BETTER" is a coin flip at best.** §4.2 pre-registers what happens when it is not reached.

### 3.5 Lumen width: no loss change, and a cross-fitted report

**What we know.** Janus 0 draws the boundary about one voxel inside ImageCAS-X's ([[icx4 - Results]]):
- tolerant Dice 0.97 against plain 0.88;
- volume ratio 0.87;
- the missed rim at about 237 HU, inside the window.

**Why no loss change.** A one-voxel rim moves Dice and leaves tF1 nearly unchanged; tF1 decides (A28). A loss change for width is
a recipe change: on 100 cases it is resolvable only at ≈ 0.05 (§4.3), and it risks extent, the thing tF1 measures. So
**Janus 1-L changes no loss and no post-processing that decides**.

**What it does instead, report only, on CPU, from the saved locked-100 softmax.**
- **The rule:** a foreground threshold τ on 1 − p(background), class = argmax over the four vessels where foreground.
- **The grid:** τ ∈ {0.50, 0.45, 0.40, 0.35, 0.30, 0.25}.
- **Cross-fitting:** the locked 100 is split into halves by `sha256('foxtrot-j1l-width:' + id)`. τ is chosen on half A to bring the
  volume ratio closest to 1, then reported on half B (Dice, tolerant Dice, volume ratio, tF1). Then the halves swap.
- **What the lead gets:** a de-biased estimate of what a width offset buys in Dice, and what it costs in tF1. It needs no further
  look at the locked 100 for tuning.
- **When it becomes a decision:** only if a later use needs calibre (stenosis; not in scope), in a later round.
- The script is round 2's work (it needs the softmax files to exist).

## 4. The decision on the locked 100 (pre-registered)

### 4.1 The rule

The rule is implemented and self-tested in `experiments/Foxtrot/j1l/locked100_decide.py`.

**Metric (the scoring rules of record).**
- Decisive tF1 @ 1.5 mm (D3), A1 with TotalSegmentator aortas.
- The A1c-pinned metric (`24441cf8…5254`).
- Flagged trees out (A1b) and provisional cases out (A1a).
- Scored by `experiments/Atlas/r9_score_icx4.py`, unchanged.
- The aortas for all 100 exist on Fir (icx4 made them for val 80 and open-36).

**The comparison.**
- There is **one decisive comparison: E against Janus 0**, both fixed predictions, paired by case.
- Interval: patient bootstrap, 10 000 resamples, 95 %.

| Verdict | Rule |
|---|---|
| **BETTER** | Lower 95 % bound of Δ macro > 0, **and** no class mean Δ < −0.03, **and** E's FP components per case ≤ 1 (A15) |
| **NON-INFERIOR** | Not BETTER; lower bound > −0.01, and the same guard and FP |
| **NOT ADOPTED** | Anything else |

**Reported, never deciding.**
- s1 and s2 each against Janus 0.
- s1 − s2: the **first measured seed term on the master family**, which A37 asked for.
- Δ on the 20 open cases alone.
- Per-class Δ.
- Whole-tree and per-class Dice, tolerant Dice, volume ratio and centreline recall and precision (`r10_dice_check.measure`).
- FP per case.

### 4.2 What each verdict does

| Verdict | Then |
|---|---|
| BETTER | E is **Janus 1-L** and replaces Janus 0 for predictions and prelabels. s1 is the base for the first pool fine-tune (§6) |
| NON-INFERIOR | E is adopted as the base model, **described as "not shown better than Janus 0"**: it has seen 60 more cases at no detectable cost. Adoption here is the **lead's call** (Q1). The default if the lead does not answer is to keep Janus 0 |
| NOT ADOPTED | Janus 0 stays. The class that tripped the guard has its worst 5 locked cases reviewed. The next round decides whether a scratch run on the 620 (≈ 50 GPU-h) is worth it |

### 4.3 Power, on measured spread (CPU experiment)

Source: [[Foxtrot - On the measured paired spread the locked 100 resolves a macro tF1 gain of about 0.011-0.013, and a recipe claim only about 0.05]].
Janus 0's own per-case file is on Fir. So the per-case paired spread comes from the three real paired val-80 runs in
`trillium-results/`: macro SD of the difference 0.038 / 0.041 / 0.046. The last, a warm fine-tune against its own base, is
the closest analogue.

**P(BETTER on the macro) at n = 100:**

| True Δ | 0 | 0.005 | 0.010 | 0.0125 | 0.015 | 0.020 |
|---|---|---|---|---|---|---|
| P(lower bound > 0) | 0.01–0.04 | 0.22–0.25 | 0.60–0.79 | 0.76–0.95 | 0.87–0.99 | 0.98–1.00 |

- **MDE (80 % power):** 0.011–0.013. The 20 added cases lower it by about 0.0015 against val 80 alone.
- **NON-INFERIOR for a neutral model** (Δ = 0): 0.61–0.79. At Δ = 0.005: 0.88–0.99.
- **Class guard false-fail for a neutral model:** 0.3–2.2 % at −0.03, against 3.5–8.8 % at −0.02. LM's 0/1 tF1 drives the −0.02
  failures, which is why the guard is −0.03.
- **A recipe claim** (seed term max(σ, 0.012) per run, A37) has an MDE of **≈ 0.049**. The locked 100 decides checkpoints, not
  recipes.

### 4.4 Looks at the locked 100

- The locked 100 is the only clean ImageCAS-X decision set the track has, so its looks are budgeted.
- **The one decisive look is §4.1.**
- s1, s2, the open-20 view, Dice and the cross-fitted width study are reports.
- nnU-Net's per-epoch pseudo-Dice on fold 0 is displayed during training, as it was for Janus 0 on val 80. It is never used for a
  choice: no checkpoint-best, no early stop, no epoch choice.
- Any later Janus 1-L candidate adds one decisive look, recorded in the ledger. **No rule, threshold or weight is tuned on it.**

## 5. Trillium jobs (the lead runs every one; account `def-aso22`)

### 5.1 Jobs and cost

**Rates.** Trillium measured **181 s/epoch** for this plan (icx14 on Trillium: 256³, batch 2, ResEnc 60G;
`trillium-results/icx14/results/training_log_*`, 446 epochs in 23.24 h). Dataset preparation took 0.68 h for 640 cases.

| # | Job | Waits on | GPU-h |
|---|---|---|---|
| T0 | Janus 0 on Trillium: predict the locked 100. **Identity check:** the Trillium predictions must match Fir's (`$SCRATCH/icx4/predictions`) to per-case tF1 within 0.002 and whole-tree Dice ≥ 0.999 on ≥ 98 of 100. **If it fails, stop.** This catches a broken checkpoint copy, venv or nnU-Net version before 28 GPU-h are spent | the `trillium/janus1l` launcher (role:swe, §8) | ≤ 1 |
| P | Build dataset 7xx (720 cases: 620 + locked 100) with Janus 0's plans; preprocess | T0 PASS | ≈ 0.8 |
| L1 | s1: 250 epochs (12.6 h) + final validation with softmax on the locked 100 (≈ 0.5 h) | P | ≈ 13.1 |
| L2 | s2: the same, launched beside L1 | P | ≈ 13.1 |
| — | Ensemble, scoring and decision (CPU) | L1, L2 | 0 |
| | **Total** | | **≈ 28 (ceiling 1 + 1 + 2 × 23.8 ≈ 50)** |

Each GPU job is 1 × H100 (`--gpus-per-node=1`, with 24 cores and ≈ 188 GiB, icx4's Trillium header), 23:50 walltime,
on `def-aso22`. Every stage resumes and skips finished work (`trillium/README.md`'s contract). **No job reads a sealed case.**
The launcher refuses unless every id it trains on or scores is outside `sealed_test.json`'s sealed lists, and the locked 100 is disjoint from the training list.

### 5.2 Commands (copy-paste)

**On Fir's login node: hand Janus 0 over** (once, about 1 GB):

```sh
cd $SCRATCH/asclepius && git -C repo pull --ff-only
H=$SCRATCH/janus0_handoff; mkdir -p $H/aorta $H/pred_fir
R=$SCRATCH/icx4/nnunet_results/Dataset715_ICX4/nnUNetTrainerICX4__nnUNetResEncUNetPlans_60G_iso05__3d_fullres
cp $R/fold_0/checkpoint_final.pth $R/plans.json $R/dataset.json $SCRATCH/icx4/splits.json $H/
for c in $(python3 -c "import json; s=json.load(open('$H/splits.json')); o=json.load(open('repo/experiments/Foxtrot/j1l/results/locked100.json')); print(' '.join(s['val'] + o['locked20_from_open36']))"); do
  cp $SCRATCH/icx4/aorta/${c}_aorta.nii.gz $H/aorta/ && cp $SCRATCH/icx4/predictions/$c.nii.gz $H/pred_fir/
done
ls $H/aorta | wc -l; ls $H/pred_fir | wc -l          # expect 100 and 100
(cd $H && sha256sum checkpoint_final.pth plans.json splits.json > SHA256)
```

**On Trillium's login node:**

```sh
mkdir -p $SCRATCH/asclepius && cd $SCRATCH/asclepius
git clone -b dev https://github.com/christianGRogers/Asclepius.git repo || git -C repo pull --ff-only
rsync -av fir.alliancecan.ca:'$SCRATCH/janus0_handoff/' $SCRATCH/janus0_handoff/
(cd $SCRATCH/janus0_handoff && sha256sum -c SHA256)
# cases/: the launcher walks up to the first cases/ (icx4's rule). If Trillium's copy is elsewhere: ln -s <that dir> $SCRATCH/asclepius/cases
mkdir -p experiments && rm -rf experiments/janus1l && cp -r repo/trillium/janus1l experiments/janus1l && cd experiments/janus1l
J1L_DRYRUN=1 JANUS0=$SCRATCH/janus0_handoff ./janus1l      # prints 620 / 100 / sealed 0, the window 61,808, the jobs it would submit
JANUS0=$SCRATCH/janus0_handoff ./janus1l t0                 # Job T0; when DONE: ./janus1l status t0  -> "identity PASS" or stop
JANUS0=$SCRATCH/janus0_handoff ./janus1l train              # Jobs P, then L1 and L2 (afterok:P), each 23:50
./janus1l status                                            # after ~2 h: s/epoch for s1 and s2, expect ~180-190
```

**When L1 and L2 are `DONE`** (Trillium, CPU; about 1–2 h at 16 processes, either on the login node within its limits or in a short CPU job):

```sh
cd $SCRATCH/asclepius/experiments/janus1l && ./janus1l ensemble          # nnUNetv2_ensemble s1+s2 softmax -> $SCRATCH/janus1l/pred_ens
V=$HOME/icx14-venv/bin/python; REPO=$SCRATCH/asclepius/repo; W=$SCRATCH/janus1l
for m in janus0 s1 s2 ens; do
  $V $REPO/experiments/Atlas/r9_score_icx4.py --pred $W/pred_$m --icx $W/icx --aorta $SCRATCH/janus0_handoff/aorta \
     --splits $W/splits_locked.json --layout $W/layout.json --set val --out $W/score_$m.json --np 16
done
$V $REPO/experiments/Atlas/r9_score_icx4.py --pred $W/pred_s1 --pair $W/pred_s2 --icx $W/icx --aorta $SCRATCH/janus0_handoff/aorta \
   --splits $W/splits_locked.json --layout $W/layout.json --set val --out $W/seed_term.json --np 16
python3 $REPO/experiments/Foxtrot/j1l/locked100_decide.py --janus0 $W/score_janus0.json --cand $W/score_ens.json --out $W/decision.json
for m in s1 s2; do python3 $REPO/experiments/Foxtrot/j1l/locked100_decide.py --janus0 $W/score_janus0.json --cand $W/score_$m.json --out $W/report_$m.json; done
./janus1l collect                                           # results/ (< 50 MB): decision.json, report_*.json, seed_term.json, logs
```

**Send back:**
- `results/` (via `collect`), or paste `decision.json` and `seed_term.json` on #302;
- T0's identity line;
- the s/epoch.

`splits_locked.json` (val = the locked 100) and `layout.json` are written by the launcher (§8).
`pred_janus0` is T0's Trillium prediction, shown identical to Fir's.

## 6. Pool reads: none now, and what changes when they come

- **Today** there are 10 scored pairs and none approved. Janus 1-L is ImageCAS-X only, and the plan above needs nothing from the pool.
- **When Round 10's A39 holds** (#116 merged, A21's dry run, ≥ 25 D35 and ≥ 40 trainable primary patients double-read), the
  pool fine-tune of Round 10 (A36–A38) runs, with four substitutions:
  1. Its base is **s1 of Janus 1-L** if the verdict was BETTER (or NON-INFERIOR and the lead adopted it); otherwise Janus 0.
  2. Its replay set is the **620**, not the 560.
  3. Its forgetting guards G2 and G3 are scored on the **locked 100**, not val 80 (n = 100 lowers G2's MDE by about 0.0015).
  4. D35 stays its decision set; D40 makes overlapping voxels the ignore label; D35 and the D27/D32 seal are never trained on.
- Nothing about the locked 100 changes. The pool reads never touch it.
- **If the lead wants pool reads inside Janus 1-L itself** (a second 1-L version), that is the same recipe with the trainable reads
  added. Its decision moves to D35, because the locked 100 cannot see a pool gain.

## 7. What would change this plan

| Observation | Change |
|---|---|
| T0 identity fails | Stop; fix the transfer, venv or nnU-Net version; no training until it passes |
| s/epoch on Trillium > 230 (250 epochs > 16 h) | Still one job each; the cost rises to ≈ 35 GPU-h; report it |
| \|s1 − s2\| macro > 0.02 on the locked 100 | A37's rule: later recipe decisions need ≥ 2 runs per arm, and the ensemble's variance argument gets stronger |
| NOT ADOPTED with the guard on one class | That class's worst cases are reviewed; round 2 weighs a scratch run on the 620 (≈ 50 GPU-h) against stopping at Janus 0 |
| The cross-fitted width study shows ≥ 1 Dice point at a tF1 cost < 0.005 | Offered to the lead as an output option for calibre uses; still never decisive |
| Pool reads pass A39 | §6 |
| The lead answers Q1–Q3 | As answered |

## 8. Code that must ship (role:swe, to be filed on the ruling, not now)

**`trillium/janus1l`**: a launcher copied from `trillium/icx4`, which is proven on Trillium and Fir, with these items:

1. **The lists.** It pins the 620 and the locked 100: train 560 and val 80 from `splits.json` (sha256 printed), dev-44 and
   open-36 from `sealed_test.json`, and the locked 20 recomputed from D45's salt and asserted equal to
   `experiments/Foxtrot/j1l/results/locked100.json`. It refuses on any sealed id, or if the locked 100 overlaps the 620. That is a
   `segtrain.pool_seal`-style guard, which issue #302 asks for.
2. **The dataset.** It builds dataset 7xx with labels by `territory.to_four`. It uses `nnUNetv2_move_plans_between_datasets` from
   Janus 0's plans, then `nnUNetv2_preprocess`, never a fingerprint, and writes `splits_final.json` with fold 0 = 620 / locked 100.
   The dataset id is the PM's choice: 715 is Janus 0, 716 the pool task and 717 Janus 1's pool fine-tune.
3. **Training.** It trains with `nnUNetTrainer_segtrain_finetune`, with `SEGTRAIN_FINETUNE_FROM=$JANUS0/checkpoint_final.pth`,
   `SEGTRAIN_CT_WINDOW=61,808` (read from Janus 0's plans, not typed) and `SEGTRAIN_SAVE_PROBABILITIES=1`. segtrain is installed into
   icx4's venv.
4. **The modes.** `t0` (predict the locked 100 with Janus 0; the identity check), `train` (P, then L1 and L2), `ensemble`
   (`nnUNetv2_ensemble`, with `plans.json` and `dataset.json` copied beside the validation folders), `status` and `collect`.
   It also writes `splits_locked.json`, `layout.json`, `icx/` and `pred_<m>/` links.
5. **Self-test.** `J1L_DRYRUN=1` and a CPU self-test with a tiny patch, like icx4's.

## 9. Questions for the lead

**Q1. A NON-INFERIOR verdict.** Adopt E as the base anyway, because it has seen 60 more cases at no detectable cost? Or keep
Janus 0 until a model is shown better? **Recommended:** adopt, with the wording "not shown better". The default, if unanswered, is to keep Janus 0.

**Q2. Shipping an ensemble.** Is an ensemble acceptable as "Janus 1-L"? It is two networks and 2× inference time. The base for
pool fine-tunes stays s1.

**Q3. Naming (D34/D45).** Read order is s1, s2, E. **Recommended:** the decided model E is "Janus 1-L", and s1 and s2 are
reported as its two members, not as separate Janus numbers.

## 10. Evidence index

**CPU experiments (this round):**
- [[Foxtrot - On the measured paired spread the locked 100 resolves a macro tF1 gain of about 0.011-0.013, and a recipe claim only about 0.05]];
- `experiments/Foxtrot/j1l/`: `locked100.py`, `locked100_power.py`, `locked100_decide.py` (self-test passes).

**Repository evidence used:**
- [[icx4 - Results]] (Janus 0: val-80 0.909; the one-voxel width finding);
- `trillium-results/icx14/results/` (Trillium 181 s/epoch; 0.68 h preparation);
- `trillium-results/round6`, `round7` (paired per-case files);
- `src/segtrain/nnunet_ext/ct_window.py` and `finetune_load.py` (the window and normalisation checks that §3.1 must satisfy);
- Round 10 A36–A38.

**External sources (checked 2026-11-11):**

| Citation | Where to find it | What I checked |
|---|---|---|
| Mehrtash et al., IEEE TMI 39(12):3868–3878, 2020 | doi:10.1109/TMI.2020.3006437; arXiv:1911.13273; PMC7704933 | Table II single against 50-model ensemble Dice, as quoted in §3.3, and the Discussion sentence (read on PMC) |
| Kamnitsas et al., EMMA | arXiv:1711.01468 | Abstract: an ensemble of models and architectures, first in BraTS 2017. No number used |
| Ash & Adams, NeurIPS 2020 | arXiv:1910.08475 | Abstract sentence quoted in §3.2. Tables not read (the PDF exceeded the fetch limit), so no number used |
| Isensee et al., nnU-Net, Nat Methods 2021 | doi:10.1038/s41592-020-01008-z | Cited only for the default five-fold ensemble at inference, nnU-Net's documented behaviour. No number used |

**Not used:** Wald et al. (arXiv:2410.23132), which Round 10's A17a cites for the warm-up. Its abstract is about MAE
pre-training and says nothing about fine-tuning schedules, so I do not lean on it.
