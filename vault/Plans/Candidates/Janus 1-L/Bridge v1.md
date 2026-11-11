---
tags: [plans/candidate, bridge, janus1-l, D45, trillium, locked100, non-inferiority]
author: Bridge
round: 1 (track 1-L)
updated: 2026-11-11
issue: christianGRogers/Asclepius#302
---

# Bridge v1 (Janus 1-L): a warm fine-tune on 620, two seeds, adopted on a non-inferiority test the locked 100 can actually answer

## 0. Position in one paragraph

Janus 1-L keeps Round 10's recipe (A36: a warm fine-tune of Janus 0), with three changes:
- it trains on D45's 620 ImageCAS-X cases, with no pool reads yet;
- it runs **two seeds** on Trillium (≈ 30 GPU-h);
- it is **adopted on non-inferiority**, not superiority, against Janus 0 on the locked 100.

The reason is a number:
- the locked 100 resolves a paired difference of **0.011–0.020** macro tF1;
- 60 more training cases should buy **0.001–0.005**.

Under a superiority gate, a Janus 1-L that is genuinely better would usually be judged "not better" and Janus 0 would
be kept. The plan therefore asks the 100 the question they can answer: *is Janus 1-L detectably worse?* It says
"better" only when the data show it.

No training change targets lumen width. tF1 does not see width, and a free post-processing option is measured
instead. If the warm start itself turns out to hurt (Ash & Adams 2020), one from-scratch run (≈ 53 GPU-h) is the
pre-registered fallback.

| | Bridge v1 |
|---|---|
| Data | ImageCAS-X train 620 (560 + dev-44 + 16 of open-36); fold-0 val = the locked 100; pool reads join later (§6) |
| Start | Janus 0's `checkpoint_final.pth`, full load including heads; Janus 0's plans field by field, including its CT normalisation |
| Recipe | A17a: 250 epochs, 2500-iteration warm-up to 1e-2, then poly; nnU-Net default augmentation with mirroring off; ResEnc 60G plan at 0.5 mm, patch 256³, batch 2 (= Janus 0) |
| Runs | a1 (seed 1, primary, the one that ships) and a2 (seed 2, replicate); concurrent; one 23:50 job each |
| Decision | Locked 100, paired against Janus 0 re-predicted in the same job: non-inferiority at 0.015 macro, no class below −0.03, centreline recall, replicate and FP guards (§4) |
| GPU-h | ≈ 30 (2 × ≈ 15). Plus ≈ 4 to predict everything if adopted. Fallback +≈ 53 |

## 1. What Janus 0 tells this plan (read from #43 and [[icx4 - Results]])

| Fact | Value | Consequence |
|---|---|---|
| Decisive val-80 tF1 | 0.909 [0.880, 0.932]; LM 0.945, LAD 0.903, LCx 0.857, RCA 0.938 | LCx is the weak class. A Janus 1-L that trades LCx for macro must be caught: per-class guard L2 |
| Open-36 / dev-44 | 0.919 / 0.906 | Janus 0 never trained on dev-44 or open-36, so its errors on the 60 cases that now join training are held-out errors (§7) |
| FP per case | 0.36 (A15 met) | FP is a guard (L5), not a lever |
| Width | Tolerant Dice 0.97 against plain 0.88; volume ratio 0.87; missed voxels ≈ 237 HU, on the partial-volume rim | The boundary sits about one voxel inside ImageCAS-X's. Centreline recall and precision are 0.94–0.95, so extent is not the problem (§3.4) |
| Speed | Fir 192 s/epoch on 12 cores. **Trillium 181–182 s/epoch** for the same network on 24 cores (icx14's two Trillium jobs, 446 and 456 epochs, p10–p90 180.9–182.2 s; `trillium-results/icx14`) | 250 epochs ≈ 12.6 h; 1000 epochs ≈ 50.4 h |

## 2. Data

### 2.1 ImageCAS-X (D45; computed and checked)

[[Bridge - The D45 split is 620 and 100 as stated, and 11 of the locked 100 were once declared development cases]]
(`experiments/Bridge/j1l_r1/split620.json`):

- **Locked 20 of open-36:** c0068, c0102, c0251, c0271, c0323, c0327, c0470, c0545, c0592, c0620, c0644, c0805,
  c0807, c0824, c0827, c0841, c0908, c0946, c0957, c0996.
- **The other 16 train.** Lists sha256: locked 100 `0090cf9b…876c7`, train 620 `fcd8aaa0…77ef8`.
- **Checks:** 620 and 100 distinct and disjoint; no sealed ImageCAS-X or quality-0 case in either; every non-sealed
  ImageCAS-X case is in exactly one list.
- **11 of the locked 100** (all from val 80) were declared development cases in Rounds 1–4. Janus 0 and Janus 1-L
  share that history, so the paired decision is unaffected. Absolute numbers carry a small optimism, as val 80
  always has.
- **Labels:** dataset 715's collapse (`territory.to_four`, D25/D1/D1b), ImageCAS-X's lumen as drawn (D8).
- **Never read, scored or trained on:** the sealed 80, the sealed quality-0 20 (D45, D27, [[Sealed test]]).

### 2.2 Pool reads

There are none to use today: 10 scored pairs, none approved. **The plan does not wait for them.** What changes when
they arrive is in §6.

### 2.3 Sampling

Uniform per case. That is nnU-Net's default, and A36's untuned default. The 60 new cases are about 10 % of 620. They
are not up-weighted: no evidence says by how much, and the effect would be below the locked 100's resolution (§4.1).

## 3. The recipe

### 3.1 Warm start, not from scratch, with a pre-registered fallback

**The evidence against warm starts.** Ash & Adams (NeurIPS 2020, arXiv:1910.08475, Table 1) show warm-started
networks generalising worse than freshly initialised ones trained on the same full data. For example, ResNet-18 on
CIFAR-10 with SGD reaches 51.7 % warm against 56.2 % from scratch. They report the gap shrinking as the first-round
share of the data grows (§2.1 and their appendix Figure 10).

**Why it should be small here.** Their setting is far from ours:

| Factor | Ash & Adams | Janus 1-L |
|---|---|---|
| First round's share of the data | 50 % | 560 / 620 = 90 % |
| Augmentation | none | full nnU-Net augmentation |
| Learning rate | constant 0.001, no schedule | warm-up to 1e-2, then poly |

**Why warm is still the right first choice:**
1. **No recipe comparison is resolvable.** Warm against scratch is a recipe claim. With seed noise its MDE is
   ≥ 0.04 (Round 10, all five advocates), and on the 100 a single pair resolves 0.011–0.020. The choice is
   therefore made on cost and risk, not on a test.
2. **Cost.** Two warm seeds cost ≈ 30 GPU-h. One scratch seed costs ≈ 53. The warm pair also buys the replicate
   (D28's intent) and the first measurement of seed noise on the ImageCAS-X reference (A22 left it open). Track 1-F
   and every later pool decision need that number.
3. **It is the path that follows.** Pool fine-tunes are warm (A36). An adopted a1 becomes their parent.

**The fallback (pre-registered).** If the decision (§4) fails, run **one** from-scratch run: Janus 0's own recipe,
1000 epochs, on the 620, ≈ 53 GPU-h. It is judged by the same rule against Janus 0.
- If it passes, it is Janus 1-L.
- If it fails too, Janus 0 stays as track 1-L's model and the recipe goes back to Round 2.

Shrink-and-perturb (Ash & Adams §4) is not used. It is untested on nnU-Net, and adding it would make the first
Trillium job a new-recipe experiment.

### 3.2 Trainer, epochs, plans, augmentation

- **Load:** the full Janus 0 network, deep-supervision heads included (A17a). Stock `-pretrained_weights` skips
  `.seg_layers.` and would restart the heads.
- **Schedule:** per-iteration linear warm-up over 2500 iterations to 1e-2, then poly to 0. SGD with Nesterov
  momentum 0.99, nnU-Net's weight decay. 250 epochs × 250 iterations, batch 2, patch 256³ at 0.5 mm.
- **Plans: Janus 0's plans file, field by field, including `foreground_intensity_properties_per_channel`.** No
  fingerprint and no planning step on the 620. nnU-Net's CT normalisation clips and z-scores with the dataset's
  foreground statistics, so re-planning on 620 cases would shift every input the warm network sees. The launcher
  copies the plans and refuses if the network built from them does not load Janus 0's state dict strictly.
- **Augmentation:** nnU-Net's defaults with **mirroring off**, in training and at inference, as for Janus 0. Mirroring
  swaps the left and right trees; TopCoW's organisers attribute a team's L/R swaps to it (arXiv:2312.17670, §5.1,
  cited in `nnUNetTrainer_segtrain_coronary.py`).
- **The repository's A17a trainer cannot be used as is.**
  - `nnUNetTrainer_segtrain_finetune` inherits `nnUNetTrainer_segtrain_coronary`, which refuses to train unless the
    plans carry the fixed CT window. Janus 0 was trained on nnU-Net's default window (Round 8), so the trainer would
    refuse.
  - The icx4 venv also has no `segtrain`.

  The launcher therefore ships a self-contained trainer, `nnUNetTrainerJanus1L(nnUNetTrainerICX4)`. It keeps icx4's
  no-mirroring, deadline stop and resume, and copies `finetune_load.load_finetune_source` and
  `WarmupPolyScheduler` verbatim, hash-pinned as `segtrain_tf1.py` is (§8).
- **Checkpoint:** `checkpoint_final.pth` only. nnU-Net also writes `checkpoint_best.pth`, selected by pseudo-Dice
  on fold-0 val, which here is the locked 100. Using it would be a selection on the decision set, so the launcher
  never exports or scores it.
- **Seeds:** `SEED=1` (a1) and `SEED=2` (a2) seed Python, NumPy and torch at trainer start and are logged. nnU-Net v2
  sets no seed of its own, and GPU nondeterminism means a seed does not reproduce a run bitwise. Run-to-run
  variation from nondeterminism alone matches that from changing the seed (Summers & Dinneen, ICML 2021,
  arXiv:2103.04514).

### 3.3 What is not changed, and why

| Lever | Why not in Janus 1-L's first job |
|---|---|
| Larger network or other preset | The 60G ResEnc plan is already above nnU-Net's XL preset, and ResEnc presets are nnU-Net Revisited's recommended baseline (Isensee et al., MICCAI 2024, arXiv:2404.09556). A different size cannot be warm-started from Janus 0 |
| Topology loss (e.g. Skeleton Recall, Kirchhoff et al., ECCV 2024, arXiv:2404.03010) | In-repo evidence: topology losses "recover branches but do not connect them" ([[Delta - Topology losses on coronaries are verified, and they recover branches but do not connect them]]). Whether LCx's deficit is breaks, naming or extent is not yet known (§7). It is a Round 2 candidate if the 60-case analysis shows breaks |
| Class-weighted CE for LCx | Same: it needs the error decomposition first. icx4's `ce_class_weights.json` hook exists if it does |
| Ensembling a1 + a2 | Reported only (§4.4). Shipping an ensemble is a separate, pre-registered decision |
| Pseudo-labels on unlabelled CT | Pool volumes include sealed, D35 and reserved patients, and the 200 non-ImageCAS-X ImageCAS cases include the sealed quality-0 20. The guard surface is large and the gain unmeasured. Not now |

### 3.4 Lumen width and extent

**Width is not a training target for 1-L:**
- tF1 decides (A28), and a one-voxel width difference costs tF1 almost nothing ([[Delta - If reads keep a seed's extent, A10 fails a model that is exactly ImageCAS-X, through precision alone, while a one-voxel width difference costs almost nothing]]).
- Resampling to 0.5 mm is not the cause: the label round trip keeps Dice 0.994
  ([[Atlas - Resampling to 0.5 mm isotropic loses nothing measurable, 0.7-0.8 mm does]]).
- The model's boundary sits on a dim partial-volume rim (≈ 237 HU against 372 HU in the overlap). That is a
  calibration of where p = 0.5 falls, not a missing structure.

**Option W, report only, at no training cost.**
- a1, a2 and Janus 0 save softmax probabilities for the locked 100 (needed for the ensemble report anyway).
- Foreground is labelled where 1 − p(background) > t, the class is the argmax over the four vessels, with
  t ∈ {0.5, 0.4, 0.3, 0.2}.
- t is chosen on the locked 100's **even-hash half**, as the value whose median volume ratio is closest to 1.
- It is **reported on the odd half:** plain and tolerant Dice, volume ratio, decisive tF1 Δ against t = 0.5.
- The decisive export always stays argmax (t = 0.5). Option W is offered to the lead for Dice-based uses
  (prelabels, a future calibre use) only if its odd-half tF1 Δ is ≥ −0.002.

**Extent:** centreline recall and precision are balanced (0.94 / 0.95). No extent lever. Guard L3 makes sure 1-L
does not lose extent.

## 4. The pre-registered decision on the locked 100

[[Bridge - On the locked 100 a paired decision resolves 0.011-0.020 tF1, so 60 more cases cannot be shown to help and Janus 1-L is adopted on non-inferiority]]

### 4.1 What the 100 can and cannot see

- **MDE** (paired, 80 % power, two-sided 5 %): 0.011 at the measured spreads, 0.014 pessimistic, 0.020 harsh.
- **What +60 cases should buy:** 0.0006–0.0045 macro tF1 (power law, exponents −0.07 to −0.5; Hestness et al. 2017,
  arXiv:1712.00409, Figure 4: ImageNet top-1 −0.309).
- **A superiority gate** would show a true +0.005 gain only 15–28 % of the time.

### 4.2 The rule

**Scoring.** Both arms are scored by the same job:
- tF1 @ 1.5 mm with the A1c-pinned `segtrain.tf1` (sha256 `24441cf8…5254`);
- in-job TotalSegmentator aortas (A1);
- decisive trees only (flagged and provisional out, A1a/A1b);
- Janus 0 is **re-predicted from its checkpoint in the same job**, on the same software;
- percentile bootstrap over cases, B = 10 000, seed 302.

| # | Check | Rule |
|---|---|---|
| L0 | Identity | Janus 0 re-predicted on Trillium reproduces its Fir val-80 decisive macro within 0.005 of **0.909**, and each class within 0.01. Otherwise **stop**: nothing is decided until the difference is explained |
| L1 | Non-inferiority (macro) | Lower 95 % bound of Δ(a1 − Janus 0) **> −0.015** |
| L2 | No class lost | No class's mean Δ (LM, LAD, LCx, RCA) **< −0.03** |
| L3 | No extent lost (A38 G3) | No class's binary centreline recall against ImageCAS-X (`r10_dice_check.measure`) falls by more than **0.02** |
| L4 | Replicate | a2's macro Δ point estimate **> −0.015** |
| L5 | FP (A15) | a1's FP components per case **≤ 1** |

- **ADOPT** if L1–L5 all hold. **a1 ships**, never the better of a1 and a2. It is named under D34/D45 by the PM.
- The verdict is worded **"better than Janus 0"** only if ADOPT holds and L1's lower bound is **> 0**. Otherwise it is
  worded **"non-inferior to Janus 0 at 0.015, adopted for its larger training set"**. This follows CONSORT's
  non-inferiority reporting: the margin is pre-specified, and superiority is claimed only from the same interval
  (Piaggio et al. 2012, JAMA 308:2594, doi:10.1001/jama.2012.87802).
- **Locked-20 sign (report only, after A26):** Δ on the 20 open-36 cases alone is reported. A sign reversal is
  reported, not acted on.

### 4.3 Operating characteristics (simulated; m = 0.015)

| True effect | P(adopt): measured spreads | pessimistic | harsh |
|---|---|---|---|
| −0.02 | ≤ 0.002 | 0.000 | 0.002 |
| −0.01 | 0.25–0.28 | 0.15 | 0.09 |
| 0 | 0.94–0.98 | 0.76 | 0.47 |
| +0.005 | ≥ 0.99 | 0.94 | 0.73 |
| LCx alone −0.05 | ≤ 0.014 | 0.029 | 0.031 |

- **Why 0.015.** m = 0.010 fails a neutral model in up to 58 % of studies. m = 0.020 adopts a −0.01 model in up to
  81 %.
- **The weak point is the harsh spread.** There a neutral model passes only half the time. The decision report states
  the measured SD of Δ, so the judge can see which regime the result came from. The rule is not changed after the
  look.

### 4.4 Reported beside the decision (report only; none of it decides)

- Per-class Δ with CIs, for a1 and a2.
- **σ_g from a1 − a2:** the first seed-noise measurement on the ImageCAS-X reference (A22). It goes to Round 2 and
  track 1-F.
- **Ensemble E = mean softmax of a1 and a2:** decisive tF1 and Δ against Janus 0. Exploratory: shipping E would need
  its own pre-registered decision.
- **Option W** (§3.4).
- **Dice set:** plain Dice, tolerant Dice, volume ratio, centreline precision and FP per case (A41's measures).

**Looks.** The locked 100 is used **once per candidate model**. Fallback S is a new candidate and gets its own look.
Every other number in §4.4 is labelled exploratory. Track 1-F's models are compared on the same 100, at their own
looks.

## 5. Trillium jobs (the lead runs them; account `def-aso22`)

**Prerequisite:** the `trillium/janus1l` launcher (§8). Every command below assumes it is merged on `dev`.

| # | Where | What | GPU-h |
|---|---|---|---|
| T0 | Fir login, then Trillium login | Copy Janus 0's checkpoint and plans to Trillium, with checksums | 0 |
| T1 | Trillium, 2 concurrent jobs | a1 and a2: prepare 720 cases (≈ 0.8 h), train 250 epochs (≈ 12.6 h), predict the locked 100 with probabilities for a1/a2 and Janus 0 (≈ 0.8 h), aortas for the 100 (≈ 0.6 h), tF1 (≈ 0.3 h) | ≈ 15 each, **≈ 30** (range 28–34; ceiling 2 × 23.6) |
| T2 | Trillium login, CPU | Decision report (§4) | 0 |
| T3 | Trillium, if ADOPT | a1 predicts all 1000 ImageCAS cases (sealed ones predicted, never scored) | ≈ 3–4 |
| S | Trillium, only if T2 fails | From scratch, 1000 epochs on 620, then as T1: three chained jobs | ≈ 53 |

**T0: copy Janus 0 before Fir's 60-day scratch purge.** Janus 0 was trained 2026-10-21, so the purge falls around
2026-12-20.

```sh
# Fir login node
DEST=~/projects/def-aso22/$USER/icx4; [ -d ~/projects/def-aso22 ] || DEST=$HOME/icx4-keep; mkdir -p $DEST
F=$SCRATCH/icx4/nnunet_results/Dataset715_ICX4/nnUNetTrainerICX4__nnUNetResEncUNetPlans_60G_iso05__3d_fullres/fold_0
[ -s $DEST/checkpoint_final.pth ] || cp $F/checkpoint_final.pth $DEST/
cp $SCRATCH/icx4/nnunet_preprocessed/Dataset715_ICX4/{nnUNetResEncUNetPlans_60G_iso05.json,dataset.json} $DEST/
cp $SCRATCH/icx4/r9_tf1_val.json $DEST/                     # Janus 0's val-80 rows, for L0
(cd $DEST && sha256sum checkpoint_final.pth *.json > SHA256SUMS && cat SHA256SUMS && pwd)
# Trillium login node (scp asks for your Fir login and MFA; Globus between the two clusters works too)
mkdir -p $SCRATCH/janus0 && cd $SCRATCH/janus0
scp 'fir.alliancecan.ca:<the DEST printed above>/{checkpoint_final.pth,nnUNetResEncUNetPlans_60G_iso05.json,dataset.json,r9_tf1_val.json,SHA256SUMS}' .
sha256sum -c SHA256SUMS
```

**T1: two concurrent warm fine-tunes.** `ROOT` is the Trillium folder holding `cases/`, the one icx14 ran from.

```sh
module load StdEnv/2023 python/3.11.5
mkdir -p $SCRATCH/asclepius && cd $SCRATCH/asclepius
git -C repo pull --ff-only || git clone -b dev https://github.com/christianGRogers/Asclepius.git repo
ROOT=<folder with cases/>; rm -rf $ROOT/experiments/janus1l && cp -r repo/trillium/janus1l $ROOT/experiments/janus1l
cd $ROOT/experiments/janus1l
export J1L_FROM=$SCRATCH/janus0/checkpoint_final.pth J1L_PLANS=$SCRATCH/janus0/nnUNetResEncUNetPlans_60G_iso05.json
J1L_DRYRUN=1 ./janus1l                                   # prints the checks below; submits nothing
SEED=1 J1L_WORK=$SCRATCH/j1l_a1 ./janus1l
SEED=2 J1L_WORK=$SCRATCH/j1l_a2 ./janus1l
grep SBATCH $SCRATCH/j1l_a1/job.sh                       # --gpus-per-node=1 --time=23:50:00 --account=def-aso22
./janus1l status $SCRATCH/j1l_a1                         # after ~2 h: s/epoch, expect ~181-183
```

**Check each printout:**
- `locked100 sha256 0090cf9b…`, `train620 sha256 fcd8aaa0…`, `sealed in either list: 0`;
- `source: Janus 0 sha256 <as SHA256SUMS>`, `state dict: strict load, heads included`;
- `plans: Janus 0's, intensity properties unchanged`;
- `checkpoint scored: checkpoint_final`;
- the A1c hash line;
- `train 620 / val 100`.

**T2: the decision** (login node, CPU, ≈ 10 min, when both say `DONE`):

```sh
./janus1l collect $SCRATCH/j1l_a1 && ./janus1l collect $SCRATCH/j1l_a2
./janus1l decide $SCRATCH/j1l_a1 $SCRATCH/j1l_a2 --janus0-val $SCRATCH/janus0/r9_tf1_val.json > results/decision_1L.md
```

**Send back on #302:** both `results-*` folders and `results/decision_1L.md`. They hold no weights, no volumes and no
sealed case.

**T3: only if ADOPT** (≈ 3–4 GPU-h): `J1L_WORK=$SCRATCH/j1l_a1 ./janus1l predict-all`.

**S: only if T2 does not adopt** (≈ 53 GPU-h, three chained jobs):
`J1L_INIT=scratch EPOCHS=1000 CHAIN=3 SEED=1 J1L_WORK=$SCRATCH/j1l_s1 ./janus1l`, then T2 with `$SCRATCH/j1l_s1`
alone. There is no replicate, so L4 does not apply.

**Total:** ≈ 34 GPU-h if adopted. ≈ 83 at worst (T1 + S), ceiling 118.

## 6. When pool reads arrive

Round 10's machinery (A33–A39) applies, with **the adopted Janus 1-L as the parent**:
- **Training:** the 620 plus every trainable read (A11′ uniform, each read a sample). The task is A36's 717, with
  ImageCAS-X 620 in place of 560.
- **Validation:** the locked 100 replaces val 80 everywhere val 80 is a guard (A38 G2/G3). G2's margin moves from
  −0.02 at n = 80 to −0.015 at n = 100, the same as L1.
- **Decision:** D35 still decides pool gain (G1), and its start thresholds (A39) are unchanged.
- **Not waiting for reads is safe.** Janus 1-L changes no pool rule, and a pool fine-tune of 1-L is judged against
  1-L and Janus 0 as A38 says.

**What a read must pass to join training (code, §8):**
- D40: voxels in two or more **vessel** classes become the ignore label.
- **D44's extended reads collapse to four by territory before D40:**
  - D1–D3 and S1–S3 → LAD; OM1, OM2 and the ramus → LCx (D1b).
  - SN, conus and RMA → RCA.
  - **PDA and PLB by the side they arise from** (D25: left-sided → LCx). D44 lists them under RCA, but a
    left-dominant PDA must not become RCA.
- **Materials** (stent, calcified and non-calcified plaque) are not lumen classes and are dropped *before* D40. A
  vessel voxel that an annotator also marked as plaque would otherwise become ignore. This reads D40, so it is
  question **Q2** for the lead.
- **TotalSegmentator-source volumes** are trained on only if the guard clears them of being twins of a sealed pool
  patient. Today the twin list exists only for Janus-M (`configs/janusm/ts-twins-r1.json`).

## 7. What would change the plan

| Result | Then |
|---|---|
| L0 fails (Janus 0 does not reproduce on Trillium) | Stop. Find the cause (software, aortas, preprocessing) before any decision |
| ADOPT, "better" | a1 is Janus 1-L, and the parent of pool fine-tunes |
| ADOPT, non-inferior only (the expected case) | Same, worded as non-inferior |
| Not adopted; both a1 and a2 have Δ < 0 | The warm-start penalty: run S |
| Not adopted on L2 or L3 in one class only | Class review on the 60 new training cases first (not on the locked 100), then S |
| S not adopted | Janus 0 stays as 1-L. Round 2 reopens the recipe, starting from the 60-case error analysis |
| Measured SD of Δ > 0.06 | The result is reported as under-powered. The rule is unchanged |
| \|a1 − a2\| macro > 0.02 on the locked 100 | Later recipe decisions need ≥ 2 runs per arm (A37) |
| The 60-case error analysis shows LCx loses mainly to breaks | Round 2: a topology-loss arm. Naming errors: the namer or class weighting. Extent: nothing |

**The 60-case error analysis (proposed for Round 2; CPU, Fir login node, no new GPU).**
- Janus 0's predictions for dev-44 and the 16 already exist on Fir, and Janus 0 never trained on them.
- Splitting their LCx tF1 loss into breaks, naming and extent tells Round 2 which lever to test.
- It does not touch the locked 100.
- Round 2 writes the script. This round only reserves the cases.

## 8. Code that must ship (a `role:swe` issue for the PM to open after the ruling; not built here)

**`trillium/janus1l`**, built from `trillium/icx4`, which is proven on Trillium as icx14:
1. **The split, pinned.** The launcher, `prepare.py` and the trainer refuse unless the train/val lists hash to
   `fcd8aaa0…` / `0090cf9b…` (from `experiments/Bridge/j1l_r1/split620.json`). They refuse any case in
   `sealed_test.json`. This adds a `locked100` guard beside `sealed.py`, of the `segtrain.pool_seal` kind.
2. **Warm start.**
   - `nnUNetTrainerJanus1L`: verbatim, hash-pinned copies of `finetune_load` and `WarmupPolyScheduler`, plus
     icx4's no-mirroring, deadline and resume.
   - The launcher copies Janus 0's plans as the new dataset's plans (dataset id: the next free one the SWE pins;
     717 stays A36's).
   - It skips fingerprinting and planning, and refuses on any non-strict load.
   - `J1L_INIT=scratch` gives Janus 0's own 1000-epoch recipe on the 620.
3. **Scoring.**
   - `checkpoint_final` only.
   - Probabilities saved for the locked 100.
   - Janus 0 re-predicted in-job.
   - Aortas and the A1c tF1 on the locked 100 only.
   - `decide` implements §4 exactly (L0–L5, wording, report items) and prints the measured SD of Δ.
4. **Reads (later, §6).**
   - The D44 → four collapse by side for PDA/PLB.
   - Materials dropped before D40 (if the lead agrees, Q2).
   - The twin check for TotalSegmentator-source volumes.

## 9. Questions for the lead

- **Q1 (no D-number).** Ship a single checkpoint (a1), with the a1 + a2 ensemble reported only. **Recommended:
  yes.** Shipping an ensemble doubles inference and needs its own decision.
- **Q2 (reads D40; only before the first pool export into a 1-L fine-tune).** Are D44's material classes dropped
  before D40's overlap rule, so a vessel voxel also marked as plaque stays a vessel voxel? **Recommended: yes.**
- **Action, not a decision.** Copy Janus 0 off Fir's scratch now (T0). The 60-day purge falls around 2026-12-20.

## 10. Evidence index

| Claim | Source |
|---|---|
| Split, hashes, development overlap | [[Bridge - The D45 split is 620 and 100 as stated, and 11 of the locked 100 were once declared development cases]]; `experiments/Bridge/j1l_r1/split620.py` |
| MDE, data-scaling gain, operating characteristics | [[Bridge - On the locked 100 a paired decision resolves 0.011-0.020 tF1, so 60 more cases cannot be shown to help and Janus 1-L is adopted on non-inferiority]]; `locked100_power.py` / `.json` |
| Measured paired spreads | [[Atlas - Run-to-run noise in both measured pairs is per case, so a 35-patient decision set resolves about 0.02-0.035 tF1 and A22's 0.013 overstates it]] |
| Trillium 181–182 s/epoch | `trillium-results/icx14/results/training_log_*.txt`, `job2/results/training_log_*.txt` |
| Warm-start penalty and its conditions | Ash & Adams, NeurIPS 2020, arXiv:1910.08475, Table 1, §2.1, §3, §4 |
| Learning-curve exponents | Hestness et al. 2017, arXiv:1712.00409, Figure 4 (ImageNet top-1 −0.309; −0.07 to −0.35 across domains) |
| Non-inferiority reporting | Piaggio et al., JAMA 2012;308:2594, doi:10.1001/jama.2012.87802 |
| Nondeterminism equals seed variation | Summers & Dinneen, ICML 2021, arXiv:2103.04514 |
| ResEnc baselines | Isensee et al., MICCAI 2024, arXiv:2404.09556 |
| Skeleton Recall loss | Kirchhoff et al., ECCV 2024, arXiv:2404.03010 |
| Width is not a tF1 problem | [[icx4 - Results]] (Dice check); [[Delta - If reads keep a seed's extent, A10 fails a model that is exactly ImageCAS-X, through precision alone, while a one-voxel width difference costs almost nothing]]; [[Atlas - Resampling to 0.5 mm isotropic loses nothing measurable, 0.7-0.8 mm does]] |

No sealed case, no pool read and no TotalSegmentator twin was read for this plan. No GPU job was run.
