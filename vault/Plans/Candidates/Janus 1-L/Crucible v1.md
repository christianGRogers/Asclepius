---
tags: [plans, candidate, track-1-L, round-1, trillium, four-class, D45, janus, lumen-width, locked-100]
author: Crucible
track: 1-L
round: 1
version: 1
updated: 2026-11-11
issue: christianGRogers/Asclepius#302
---

# Crucible v1 (Janus 1-L): guard tF1, fix the thin lumen, and let the locked 100 judge one pre-registered model

## 0. Keep, improve or replace the starting point?

**The starting point** is the Master plan's Janus 1 ([[Delta v10]] as amended in [[Round 10]], A36–A38). It is a warm
fine-tune of Janus 0, for 250 epochs, on ImageCAS-X train 560 plus the trainable pool reads. It is decided on the
D35 pool set (G1) and guarded on val 80 (G2–G5).

**Crucible keeps its recipe and replaces its decision.**
- **Kept:** the warm fine-tune. That means A17a's full load with heads, a 2500-iteration warm-up then poly, peak LR
  1e-2, 250 epochs, Janus 0's plans, and uniform sampling.
- **Changed, because D45 changed the data:**
  - the training set is the 620 ImageCAS-X cases, not 560 plus pool reads;
  - the decision set is the locked 100, not D35;
  - the open-36 confirmation step (G4) is gone, because D45 spends open-36.
- **Replaced: what "better than Janus 0" means.** G1 asked for a gain in pool tF1. On ImageCAS-X alone, a tF1 gain
  is not a fair primary claim. Sixty more cases are expected to buy 0.001–0.004. The locked 100 can only see
  0.011–0.021 (§5.2).

**Added: a width fix.** Janus 0's one measurable, fixable defect is the lumen width. It sits about one voxel inside
ImageCAS-X: Dice 0.880, volume ratio 0.867. The locked 100 can see a Dice change of 3–6 thousandths.

**This round's evidence** (CPU; code in `experiments/Crucible/j1l_r1/`):
- [[Crucible - At 0.5 mm even a perfect network scores whole-tree Dice 0.934, so most of Janus 0's thin lumen is the network, not the resampling]]
- [[Crucible - On the locked 100 a tF1 gain must be 0.011-0.021 to be seen, sixty more cases buy 0.001-0.004, and Dice can see 0.003-0.006]]
- Three tested scripts that Job 0 and the gate run unchanged:
  - `threshold_export.py`;
  - `decide.py`;
  - `job0_janus0_probs.sh`.
- `lists.json`, the D45 lists derived from ids only (sha256 `7ecc464b…fd56`).
- External sources, each read at source on 2026-11-11 (§9).

## 1. Thesis

1. **Janus 1-L can be made measurably better than Janus 0 on ImageCAS-X, but not on tF1.** It can be better in
   lumen width, at no tF1 cost.
   - On tF1, the locked 100's MDE is 0.011–0.021 and the data effect is 0.001–0.004.
   - On Dice, the MDE is 0.003–0.006. Janus 0 sits 0.054 below what a perfect network can reach at 0.5 mm (0.934).
2. **Most of the thin lumen is the network, not the grid.** Run through nnU-Net's resampling, a perfect network loses
   2.6 % of the volume; Janus 0 loses 13.3 %.
   - The cause is an inward boundary on a dim rim. The cheapest direct fix is the export: a foreground threshold
     below 0.5.
   - The theory predicts this. For calibrated probabilities, the F1-optimal threshold is half the optimal F1 (§9,
     E1), and Dice is F1. At Dice ≈ 0.88–0.93 that puts the best threshold near 0.44–0.47, not 0.5.
3. **The threshold must be chosen where it cannot leak.** The 60 cases that D45 moves into training (dev-44 plus 16
   of open-36) were never trained on by Janus 0.
   - Janus 0's probabilities on them choose t (Job 0).
   - The locked 100 never sees a candidate threshold before the gate.
4. **With no confirmation set left, the locked 100 carries one pre-registered model and one fixed sequence of
   tests.** Every other number is a report.

## 2. Data

| Set | Cases | Use |
|---|---|---|
| **Train 620** (D45) | ImageCAS-X train 560 + dev-44 + 16 of open-36 | Janus 1-L training |
| ↳ **tuning 60** | dev-44 + those 16 | Before training, Janus 0's out-of-sample probabilities on them choose the export threshold (Job 0) |
| **Locked 100** (D45) | val 80 + the other 20 of open-36 (salted hash; `lists.json`) | The gate (§5), one look. Never trained on, never used to choose t |
| Sealed ImageCAS-X 80, quality-0 20 | — | **Never read, scored or trained on** (D27, A14). Every script refuses them |

- **Labels:** ImageCAS-X as drawn (D8), collapsed by `territory.to_four` (D25, D1, D1b; "Other" → the nearest
  LAD/LCx).
- **The locked 20 of open-36:** c0068, c0102, c0251, c0271, c0323, c0327, c0470, c0545, c0592, c0620, c0644, c0805,
  c0807, c0824, c0827, c0841, c0908, c0946, c0957, c0996.

### 2.1 Pool reads

The plan works on ImageCAS-X alone. Today there are 10 scored pairs and no approved read, so no pool read enters
the first job. When reads arrive:
- **They enter a later 1-L fine-tune** (Janus 1-L as the start), on the Master plan's terms:
  - each read is a sample (A11′);
  - shared voxels become the ignore label (D40);
  - 14-class reads are collapsed by territory first (D41/D44);
  - never a sealed, D35, reserve or spacing-suspect volume (D27, D35, A34).
- **Start condition:** A39's, at least 40 trainable primary patients double-read.
- **Decision:** D35 decides the pool question (D35's purpose). The locked 100 is the forgetting guard: the H1 bound
  of §5 against the then-current 1-L.
- **Width:** reads may redraw the outline (D12). So t* is re-checked on D35 as a report: model-vs-read Dice and
  volume ratio at t* and at 0.5. A team convention wider or narrower than ImageCAS-X's shows there first.

## 3. The recipe

| Item | Setting | Why |
|---|---|---|
| Start | **Warm from Janus 0's `checkpoint_final.pth`**: full load including heads, strict, bitwise-checked (A17a `finetune_load`) | Data adds 0.001–0.004 either way. Scratch costs about 55 GPU-h against about 15, for a difference the locked 100 cannot see (§5.2). Ash & Adams (E2) is the risk: warm starts can generalise worse when the new data is a superset. Hence H1's guard, and §7's trigger for a from-scratch run |
| Plans | **Janus 0's `plans.json`, byte-identical** (`nnUNetResEncUNetPlans_60G_iso05`: ResEnc, 0.5 mm, 256³, batch 2, nnU-Net's default CT normalisation) | `finetune_load` refuses any plans or normalisation difference. Re-planning on 720 cases would change the foreground percentiles. ResEnc at a 60-GB target is already beyond the XL preset's 40 GB (E3) |
| Trainer | A17a's warm-up and poly schedule (peak 1e-2, 2500-iteration warm-up), no mirroring, DiceCE, **with `SEGTRAIN_CT_WINDOW=off`** | `nnUNetTrainer_segtrain_coronary` refuses plans without the fixed window, and Janus 0 uses nnU-Net's default window (Round 8's tie-break). The check must be switched off explicitly, not by re-planning (#306 comment) |
| Epochs | **250** | A36 |
| Data, mix | Train 620, uniform per case | A36's mix. There is no pool yet |
| nnU-Net val | Fold-0 val = locked 100. `checkpoint_final` only; the in-training pseudo-Dice is never read | nnU-Net needs a val set. Checkpoint selection on it would leak |
| Augmentation | nnU-Net default minus mirroring | No evidence to move it |
| Loss, width | **No loss change in round 1.** Width is fixed at export (§3.1) | §1.2: the bias is the network's boundary on a dim rim. A loss change needs a GPU run to test; the threshold needs only inference |
| Seeds | **One run (seed 0)**; optional replicate a2 (§10, Q2) | A37's distinction: shipping a fixed checkpoint is a model decision, which needs no seed term. No recipe claim is made |
| Export | Foreground threshold **t\*** from Job 0. Vessel where the summed vessel probability is ≥ t\*; class by argmax among the vessels | §3.1 |

### 3.1 The width fix: an export threshold chosen off the locked 100

**Rule W** (`decide.py select`, pre-registered):
- **Candidates:** t ∈ {0.50, 0.45, 0.40, 0.35, 0.30}, on Janus 0's probabilities for the tuning 60.
- **Choose** the t with the highest mean whole-tree Dice, subject to:
  - (i) mean decisive macro tF1 ≥ tF1(0.50) − 0.005;
  - (ii) mean FP components per case ≤ FP(0.50) + 0.10;
  - (iii) no class's centreline recall falls.
- **Ties** (Dice within 0.002) go to the larger t. t = 0.50 always qualifies, so "no change" is a possible answer.

**Prediction, written before Job 0:**
- t\* ∈ {0.45, 0.40} (E1's half-F1 rule at Dice about 0.9);
- Dice on the tuning 60 rises by 0.01–0.03;
- the volume ratio rises toward 0.95.

If t\* = 0.30, Janus 0's rim probabilities are miscalibrated, not just under 0.5. That is a finding for round 2
(§7).

**t\* is chosen on Janus 0 and applied to Janus 1-L.** That transfer is an assumption: the fine-tune starts from the
same weights and data and runs for 250 epochs. It is checked as a report (§5.3), not tuned on the locked 100.

**Not chosen for round 1:**
- **A finer target spacing.** 0.4 mm raises the 0.5-mm Dice ceiling from 0.934 to 0.975. But it cannot warm-start,
  because the plans differ. It shrinks a 256³ patch's view from 128 to 102 mm, and it costs about 55–60 GPU-h from
  scratch. It is triggered in §7.
- **Boundary or topology losses** (boundary loss, clDice). They have no CPU evidence here, and they target different
  failures: clDice targets connectivity, which tF1 already shows is fine.

## 4. Other choices

- **Inference:** as icx4: no TTA (`--disable_tta`), `checkpoint_final.pth`, probabilities saved for the locked 100.
- **Post-processing:** none beyond the threshold. Bridging and ROI rules are closed (A2, A20).
- **FP:** A15 (≤ 1 component per case) binds the shipped model on the locked 100. A lower threshold can add dim
  components beside the tree, so Rule W's (ii) and §5's safety line both check it.

## 5. The decision on the locked 100 (pre-registered)

### 5.1 The comparison
- **Candidate C** = Janus 1-L at t\*.
- **Baseline** = Janus 0 at argmax, from Job 0's locked-100 predictions: the model as shipped.
- Both are fixed predictions, scored with `experiments/Atlas/r9_score_icx4.py` at A1c `24441cf8…5254`, with A1
  aortas (Janus 0's own) and flagged trees apart (A1b).
- Paired by case; bootstrap with 10 000 resamples, seed 0 (`decide.py gate`).
- **One look.** No other candidate is scored against the locked 100 before C is.

### 5.2 Power (Janus 0's spread; [[Crucible - On the locked 100 a tF1 gain must be 0.011-0.021 to be seen, sixty more cases buy 0.001-0.004, and Dice can see 0.003-0.006]])

| | SD of paired Δ | MDE (80 %, n = 100) | P(pass) for a neutral model |
|---|---|---|---|
| tF1, superiority | 0.038–0.074 | 0.011–0.021 | 0.03–0.06 |
| tF1, non-inferior at −0.02 | same | — | 0.78–1.00 |
| tF1, non-inferior at −0.01 | same | — | 0.28–0.72 (too tight) |
| Whole-tree Dice, superiority | 0.010–0.023 | 0.003–0.006 | 0.025 |

### 5.3 The sequence (fixed; stop at the first failure; each at a one-sided 2.5 %)

| # | Hypothesis | Passes when |
|---|---|---|
| **H1** | tF1 non-inferior | Lower 95 % bound of mean Δ decisive macro tF1 > **−0.02**; **and** no class's mean Δ < −0.03; **and** no class's centreline-recall mean Δ < −0.02 (A38's G2/G3 at n = 100) |
| **H2** | Dice superior | Lower 95 % bound of mean Δ whole-tree Dice > **0** |
| **H3** | tF1 superior | Lower 95 % bound of mean Δ decisive macro tF1 > **0** |
| Safety | A15 | C's FP components per case ≤ 1 on the locked 100 |

**Verdicts:**
- **"Janus 1-L is better than Janus 0":** H1 + H2 + safety. Janus 1-L replaces Janus 0 as the 1-L base and takes
  the next Janus number (D34). If H3 also passes, the claim says "and in tF1".
- **H1 fails:** Janus 0 stays. A class drop beyond 0.05 triggers a review of that class's worst five cases (G5), and
  the cause goes to round N+1.
- **H1 passes but H2 fails:** Janus 0 stays as shipped. The fine-tune is reported as "no worse, no wider". Round N+1
  takes up §7's spacing trigger.

**Reports (decide nothing; written after the verdict):**
- Janus 0 at t\*, which isolates the threshold;
- C at argmax, which isolates the fine-tune;
- C's Dice at every t (the transfer check of §3.1);
- per class;
- the val-80 and locked-20 parts separately;
- the volume ratio and tolerant Dice;
- FP.

**Why fixed-sequence:** with no confirmation set, a second ship candidate, or a choice of t on the locked 100, would
spend the set's α twice. A fixed sequence keeps the family-wise error at 5 % without splitting α, as long as nothing
after a failure is claimed (E4).

**Note on val 80:** it informed earlier recipe choices (the window, P2) and was Janus 0's nnU-Net val fold
(`checkpoint_final`, no selection). The bias this leaves favours Janus 0, not C.

## 6. The Trillium jobs (the lead runs them; account `def-aso22`)

Every GPU job uses 1 × H100 80 GB (`--gpus-per-node=1`; 24 cores and about 188 GiB come with it) and is submitted
from the GPU login node (`trillium-gpu.alliancecan.ca`). **No job reads, scores or trains on a sealed case.**

| # | Job | Waits on | GPU-h (ceiling) |
|---|---|---|---|
| T | Copy Janus 0, its aortas and the 160 labels Fir → Trillium; clone; fetch CTs | this PR | 0 |
| 0 | Janus 0 probabilities on 160 cases; Rule W; the baseline score | T | **3–4** (6) |
| 1 | Janus 1-L: warm fine-tune, 250 epochs; predict the locked 100 with probabilities; export at t\* | Job 0's t\*; #306's launcher (with the two points in my comment there) | **≈ 15** (23.8) |
| G | The gate (`decide.py gate`), CPU | Job 1 | 0 |

**Total ≈ 19 GPU-h** (ceiling about 34). Optional replicate a2 (Q2): +15.

**Step T** (Fir login node, then Trillium; MFA prompts are the lead's; < 3 GB):

```sh
# on Fir (Janus 0's workdir is purged ~60 days after 2026-10-21: before about 2026-12-20)
cd $SCRATCH/icx4
L=$SCRATCH/janus0_out; mkdir -p $L/icx $L/aorta
M=nnunet_results/Dataset715_ICX4/nnUNetTrainerICX4__nnUNetResEncUNetPlans_60G_iso05__3d_fullres
mkdir -p $L/$M/fold_0 && cp $M/plans.json $M/dataset.json $L/$M/ && cp $M/fold_0/checkpoint_final.pth $L/$M/fold_0/
curl -sSL https://raw.githubusercontent.com/christianGRogers/Asclepius/exp/j1l-r1-crucible/experiments/Crucible/j1l_r1/lists.json -o $L/lists.json
for c in $(python3 -c "import json;print(' '.join(json.load(open('$L/lists.json'))['job0']))"); do
  n=$((10#${c:1} + 1)); cp icx/$n.coronary.nii.gz $L/icx/; cp aorta/${c}_aorta.nii.gz $L/aorta/; done
ls $L/icx | wc -l; ls $L/aorta | wc -l          # 160 and 160
rsync -av $L/ $USER@trillium-gpu.alliancecan.ca:/scratch/$USER/janus0/
```

```sh
# on Trillium (trillium-gpu.alliancecan.ca), inside tmux
module load StdEnv/2023 python/3.11.5
mkdir -p $SCRATCH/asclepius && cd $SCRATCH/asclepius
git clone -b dev https://github.com/christianGRogers/Asclepius.git repo || git -C repo pull --ff-only
python3 repo/trillium/fetch_cases.py cases      # ~91 GB, resumable; asks for the Girder login once
# the icx4 venv (as trillium/icx4's setup_venv), once
virtualenv --no-download $HOME/icx14-venv && source $HOME/icx14-venv/bin/activate
pip install --no-index --upgrade pip && pip install --no-index torch && pip install nnunetv2==2.8.1 remotezip nibabel scipy scikit-image
T=$(python -c 'import nnunetv2,os;print(os.path.join(os.path.dirname(nnunetv2.__file__),"training","nnUNetTrainer","variants","icx4"))')
mkdir -p $T && touch $T/__init__.py && cp repo/trillium/icx4/lib/icx4_trainers.py $T/
python repo/experiments/Crucible/j1l_r1/threshold_export.py --selftest && python repo/experiments/Crucible/j1l_r1/decide.py --selftest
```

**Job 0** (after this PR merges; `experiments/Crucible/j1l_r1/job0_janus0_probs.sh`):

```sh
cd $SCRATCH/asclepius/repo/experiments/Crucible/j1l_r1 && sbatch job0_janus0_probs.sh
# after it ends (about 2-4 h):
cat $SCRATCH/j1l_job0/select.json | head -40; tail -8 j1l-job0-*.out
```

**What Job 0 does:**
- predicts the 160 cases with `--save_probabilities`;
- writes thresholded exports;
- scores the tuning 60 at five thresholds;
- applies Rule W;
- scores Janus 0 at argmax on the locked 100.

**Check:** the locked-100 file's val-80 cases must reproduce Janus 0's 0.909 (A26-style identity). The thresholded
locked-100 exports are written but not scored.

**Job 1** (after #306's launcher lands, with t\* from Job 0):

```sh
cd $SCRATCH/asclepius && git -C repo pull --ff-only
mkdir -p experiments && rm -rf experiments/janus1l && cp -r repo/trillium/janus1l experiments/janus1l
cd experiments/janus1l && JANUS1L_DRYRUN=1 ./janus1l      # prints: train 620, val (locked) 100, sealed 0, split hash, Janus 0 sha256, plans identical
JANUS0=$SCRATCH/janus0 JANUS1L_T=$(python3 -c "import json;print(json.load(open('$SCRATCH/j1l_job0/select.json'))['chosen_t'])") \
  SEGTRAIN_CT_WINDOW=off ./janus1l                        # one 23:50 job: preprocess 620+100 with Janus 0's plans, 250 epochs, predict locked 100 (probs), export at t*
./janus1l status                                          # s/epoch; expect ~175 (Trillium R0) -> ~12.2 h of training
```

**Gate** (Trillium login node, CPU, about 1 h):

```sh
R=$SCRATCH/asclepius/repo; W=$SCRATCH/j1l_job0
python $R/experiments/Atlas/r9_score_icx4.py --pred $SCRATCH/janus1l/export_tstar --icx $SCRATCH/janus0/icx \
  --aorta $SCRATCH/janus0/aorta --layout $W/layout.json --splits $W/split_locked100.json --set val --np 20 \
  --out $SCRATCH/janus1l/locked100_cand.json
python $R/experiments/Crucible/j1l_r1/decide.py gate --base $W/scores/locked100_janus0_argmax.json \
  --cand $SCRATCH/janus1l/locked100_cand.json | tee $SCRATCH/janus1l/gate.json
```

**Send back on #302:**
- `select.json`;
- Job 0's `.out` tail;
- `gate.json`;
- both locked-100 score files' `summary` blocks;
- `./janus1l status`'s s/epoch line;
- the `.out` of any failed job.

Never send a file of a sealed case; no job writes one.

## 7. What would change the plan

| Observation | Then |
|---|---|
| Job 0: t\* = 0.50 (no threshold helps on the tuning 60) | The width lever is not the export. Round 2 weighs a finer spacing (from scratch, about 55–60 GPU-h at 0.45 mm, ceiling 0.956, 115-mm view) against "Janus 1-L = Janus 0 + 60 cases", and the gate drops H2 |
| Job 0: Dice at t\* still more than 0.03 below 0.934 on the tuning 60, with the volume ratio ≥ 0.95 | The bias is removed and the grid now binds: propose the 0.45-mm from-scratch run in round 2 |
| Job 0: t\* = 0.30, or FP rises at every t < 0.5 | Rim miscalibration, or dim veins beside the tree. Round 2 looks at calibration (temperature on the tuning 60) before any threshold ships |
| Job 0: Janus 0 does not reproduce 0.909 on val 80 | Stop: the transfer or the scorer differs. Nothing is decided until it does |
| Job 1: training s/epoch > 250 on Trillium | The 250 epochs still fit (17.4 h); let it run |
| Gate: H1 fails | Janus 0 stays. Round N+1 reads the class reports; warm vs scratch (E2) becomes the open question |
| Pool reads: ≥ 40 trainable primary patients double-read | §2.1's fine-tune joins the plan, decided on D35 |
| The lead rules D28's "second seed" binds 1-L (Q2) | a2 runs beside Job 1 (+15 GPU-h). The gate is unchanged (a2 is never shipped in C's place) |

## 8. Risks

- **The transfer of t\*.** Janus 1-L's calibration may differ from Janus 0's. It is reported (C's Dice at every t),
  and H1 still guards tF1. A miss costs Dice, never the seal.
- **Thresholds and FP.** Guarded twice: Rule W (ii) and A15 at the gate.
- **Job 0 depends on Fir's scratch.** Janus 0's workdir is purged about 60 days after 2026-10-21. Step T should run
  before about 2026-12-20, or the aortas must be recomputed (about 1 GPU-h, TotalSegmentator).
- **The resampling model** is skimage's `resize` called as nnU-Net calls it, not nnU-Net's own run. A
  real-preprocessing check is a one-line addition to Job 0 if the judge wants it.
- **The paired-SD inputs** are from older runs of the same family. Job 0 measures Janus 0's own threshold-pair SD
  on the 60 as a report.

## 9. External evidence (each read at source, 2026-11-11)

- **E1. Lipton, Elkan & Narayanaswamy, "Thresholding Classifiers to Maximize F1 Score",** arXiv:1402.1892 (stat.ML,
  v2 May 2014). Abstract: for well-calibrated conditional probabilities, the optimal threshold is half the optimal
  F1 score.
  - Applied here: whole-tree Dice is the voxel F1, so a calibrated model's Dice-optimal threshold sits below 0.5.
  - The paper's setting is binary classification with calibrated scores, not a segmentation network. That is why
    t\* is chosen empirically (Rule W) and not set to F1/2.
- **E2. Ash & Adams, "On Warm-Starting Neural Network Training",** NeurIPS 2020, arXiv:1910.08475.
  - Fig. 1: ResNets on CIFAR-10, warm-started on 50 % then trained on 100 %. The caption says they produce
    "similar training performance but differing test performance".
  - Table 1 (ResNet-18, SGD) as read in the HTML version: about 56.2 % from random init against 51.7 % warm.
  - §4 ("Shrink, Perturb, Repeat") is their remedy.
  - Applied here: our 560 → 620 is that setting at a much smaller step. It is the reason H1 guards tF1, and the
    reason a from-scratch run is the named fallback (§7).
- **E3. nnU-Net ResEnc presets** (MIC-DKFZ/nnUNet `documentation/resenc_presets.md`; Isensee et al., "nnU-Net
  Revisited", MICCAI 2024, arXiv:2404.09556). The preset table gives M 9–11 GB, L 24 GB and XL 40 GB of VRAM, and
  `-gpu_memory_target` with `-overwrite_plans_name` to scale beyond them.
  - Janus 0's 60-GB ResEnc plans are beyond XL already. No preset change is proposed, because the warm start needs
    identical plans.
- **E4. Fixed-sequence testing.** Testing pre-ordered hypotheses each at the full α, and stopping at the first
  failure, controls the family-wise error rate. This is the standard "fixed-sequence" method (FDA, *Multiple
  Endpoints in Clinical Trials: Guidance for Industry*, final, October 2022, its "Fixed-Sequence Method" section; the copy at the NLM digital collections, nlm:nlmuid-9918504488206676. The section number was not confirmed, so none is cited).
- **Code read at source:** nnU-Net v2.8.1 `preprocessing/resampling/default_resampling.py` (`resize_segmentation`,
  order 1 with a 0.5 cut; the logits resized at export). `resample_roundtrip.py` reproduces this.

## 10. Questions for the lead (none assumed in the plan)

- **Q1. Fir for Step T.** Janus 0, its aortas and labels live on Fir. Step T copies about 3 GB to Trillium.
  - Alternative: Job 0 runs on Fir, where everything already is; it is inference only, about 3 GPU-h. Job 1 stays
    on Trillium (D45) either way.
  - Recommended: Step T to Trillium, so that the gate's baseline and the candidate are scored in one place.
- **Q2. D28 on track 1-L.** Does "the first retrained decision adds a second seed to its control" bind Janus 1-L?
  - Crucible's reading: no, because shipping a fixed checkpoint is a model decision (A37).
  - If yes: a2 runs beside Job 1 for +15 GPU-h, as a replicate that is never shipped.
- **Q3. Dice as a co-decider.** Main-track A28 says Dice decides nothing. #302 asks for tF1 and Dice. This plan uses
  Dice only after tF1 non-inferiority (H1 → H2). That is a judge's call, not a D-number. It is flagged because it
  reverses A28 for this track.

## 11. Cost

| Item | GPU-h |
|---|---|
| Job 0: 160 cases with probabilities, plus scoring in the job | 3–4 |
| Job 1: preprocess 720 (about 2 h) + 250 epochs × about 175 s (12.2 h) + locked-100 prediction (about 1 h) | about 15 |
| **First jobs** | **about 19** (ceiling 34) |
| Optional a2 (Q2) | +15 |
| Round-2 contingency: 0.45-mm from scratch (§7) | about 55–60, only if triggered |

## 12. Code that must ship

Crucible adds two points to **#306** (Janus 1 split guard + `trillium/janus1l`, proposed by Delta) in a comment
rather than opening a duplicate:
1. **Janus 0's plans reused byte-identically.** No `plan_experiment` for 718.
2. **`SEGTRAIN_CT_WINDOW=off`.** Without it, the A17a trainer refuses Janus 0's default-window plans.

Two more points:
- the launcher saves the locked-100 probabilities and exports at `JANUS1L_T`;
- the split pin should be checked against `lists.json` here (same ids; Crucible's file is not the pin).
