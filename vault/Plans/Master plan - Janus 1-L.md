---
aliases: [Master plan - Janus 1-L, Janus 1-L plan]
tags: [plans, master, track-1-L, janus1-l, four-class, trillium, D45, locked100]
status: living
track: 1-L
round: 1
updated: 2026-11-11
issue: christianGRogers/Asclepius#302
---

# Master plan, track 1-L (Janus 1-L)

**In force: [[Candidates/Janus 1-L/Crucible v1|Crucible v1]] (track 1-L), as amended by the judge in
[[Janus 1-L Round 1]] (L-A1 to L-A12).**
- The amendments are binding and override the candidate text where they conflict.
- This file is the track's plan. The main [[Master plan]] (Delta v10, Round 10) still governs the pool-driven work,
  D35 and the seal.
- Track 1-F (#303) has its own plan and shares only the split (L-A1).

**Binding decisions:**
- **D45:** the split, Trillium, the lead runs every job.
- **D25 and D8:** four classes by territory, on ImageCAS-X's lumen.
- **D27/D32:** the seals.
- **D35:** decides pool questions only.
- **D34:** naming.
- **D40:** overlaps become ignore, for pool reads.

**Status: round 1 of at least 3.** The recipe and decision below are the plan of record. The training jobs do not
start until round 3 at the earliest (#302). Step T and Job 0 are recommended now ([[Janus 1-L Round 1]] Q1, Q2).

## In one paragraph

**Janus 1-L is Janus 0 fine-tuned warm on D45's 620 ImageCAS-X cases.**
- The repository's A17a trainer, 250 epochs, peak LR 1e-2, Janus 0's plans byte-identical, mirroring off.
- Two runs: **a1** is the pre-registered ship candidate; **a2** is its replicate. Their ensemble **E** is reported.

**Janus 0's one measured defect, a lumen drawn about one voxel thin, is fixed at export.** A foreground threshold t\* is
chosen on Janus 0's own probabilities for the 60 training cases it never saw. It is chosen by Dice, with tF1, FP and
recall guards, and frozen before training.

**The locked 100 judge a1 at t\* against Janus 0 once, in a fixed sequence:**
- H1: tF1 non-inferior at −0.02, with class, recall and FP guards;
- H2: whole-tree Dice superior;
- H3: tF1 superior.

"Better than Janus 0" means H1 and H2.

**Cost:** ≈ 32–34 Trillium GPU-h, plus Job 0 at ≈ 3–4.

## 1. Data

| Set | Cases | Use |
|---|---|---|
| **Train 620** | ImageCAS-X train 560 + dev 44 + c0123 c0195 c0340 c0416 c0430 c0435 c0447 c0617 c0624 c0660 c0726 c0758 c0772 c0877 c0971 c0984 | Training (folds 0 and 1, identical) |
| ↳ **tuning 60** | dev 44 + those 16; never trained on by Janus 0 | Job 0 chooses t\* on Janus 0's probabilities for them, before any Janus 1-L training |
| **Locked 100** | val 80 + c0068 c0102 c0251 c0271 c0323 c0327 c0470 c0545 c0592 c0620 c0644 c0805 c0807 c0824 c0827 c0841 c0908 c0946 c0957 c0996 | Fold val (display only), and the one decision (§3). Never trained on, never used to choose anything |
| Sealed | ImageCAS-X test 80 + quality-0 20 | **Never read, predicted, scored or trained on** |

- **Pins (L-A1):** sha256 of the sorted ids joined by `\n`:
  - locked 100: `bbd9c687818956e2d5664b06fd8c8bd02ddb031e9b9d08036d59cc0e1a4d5895`;
  - train 620: `1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152`.
- **File of record:** `experiments/Delta/j1l_r1/janus1_split_proposal.json` (sha256 `19b832fe…4dd3`), which goes to
  `configs/janus1/split-2026-11.json` under #306.
- **Labels:** ImageCAS-X as drawn (D8), collapsed by `trillium/icx4/lib/territory.py` (D25, D1, D1b), exactly as
  dataset 715.
- **Pool reads:** none in Janus 1-L. When A39's counts are met, the pool fine-tune of Round 10 runs from the adopted
  Janus 1-L (L-A11):
  - the 620 are the replay set;
  - the locked 100 replace val 80 in G2 and in G3, in L3's form;
  - D35 decides;
  - D44 reads collapse to four by territory before D40, with PDA and PLB by side;
  - material classes are handled as the lead answers Q8.

## 2. Recipe (L-A2, L-A3)

| Item | Setting |
|---|---|
| Start | Janus 0 `checkpoint_final.pth` (Dataset715), `nnUNetTrainer_segtrain_finetune` (A17a), full strict load with heads, bitwise-checked, sha256 logged |
| Plans | Janus 0's `plans.json` byte-identical (`nnUNetResEncUNetPlans_60G_iso05`: ResEnc, 0.5 mm iso, 256³, batch 2, nnU-Net's default CT normalisation). `nnUNetv2_move_plans_between_datasets`, then `nnUNetv2_preprocess`. **No fingerprint, no plan step** |
| Window check | `SEGTRAIN_CT_WINDOW=off`; `finetune_load` compares plans and normalisation field by field instead |
| Schedule | 2500-iteration linear warm-up to 1e-2, then poly; SGD with Nesterov 0.99; 250 epochs × 250 iterations |
| Loss, augmentation | DiceCE with deep supervision; nnU-Net default augmentation, **mirroring off** in training and inference |
| Sampling | Uniform over the 620 |
| Checkpoint, inference | `checkpoint_final` only; `--disable_tta`; probabilities saved for the locked 100 |
| Runs | **a1** = fold 0 (ship candidate); **a2** = fold 1, the same split entry (replicate, never shipped in a1's place; subject to Q5); **E** = `-f 0 1` (report) |
| Export | **t\*** from Job 0 (§2.1), applied unchanged to a1, a2 and E |
| Not in this plan | Skeleton Recall or other topology loss, the 1e-3 arm, class-weighted CE, a new spacing, from-scratch training (all open for later rounds: [[Janus 1-L Round 1]] §5) |

### 2.1 Rule W: the export threshold (L-A4)

- **Data:** Janus 0's probabilities on the tuning 60 (Job 0).
- **Grid:** t ∈ {0.50, 0.45, 0.40, 0.35, 0.30}. A voxel is vessel where the summed vessel probability is ≥ t; its
  class is the argmax among the four vessels.
- **Choice:** the highest mean whole-tree Dice, subject to:
  - tF1 ≥ tF1(0.50) − 0.005;
  - FP per case ≤ FP(0.50) + 0.10;
  - no class's centreline recall falls.
- **Ties** (Dice within 0.002) go to the larger t.
- **Code:** `experiments/Crucible/j1l_r1/decide.py select`.
- **Frozen:** `select.json` and its sha256 are posted on #302 before any training job is submitted.

## 3. The decision on the locked 100 (L-A5 to L-A8)

**Before anything is read: the identity check (L0).**
- Janus 0 re-predicted on Trillium reproduces Fir's val-80 decisive macro **0.909 ± 0.003**.
- Each class is within 0.01 of LM 0.945, LAD 0.903, LCx 0.857 and RCA 0.938.
- ≥ 95 % of cases agree within 0.01 against Fir's own predictions.
- **Otherwise stop.**

**The comparison.**
- **Candidate C** = a1 at t\*. **Baseline** = Janus 0 at argmax (Trillium).
- Decisive tF1 @ 1.5 mm at A1c `24441cf8…5254`, with Janus 0's A1 aortas.
- A1a/A1b exclusions.
- Paired by case; bootstrap 10 000; one-sided 2.5 % bounds.
- **One look per candidate model.**

| # | Test | Passes when |
|---|---|---|
| **H1** | tF1 non-inferior, nothing lost | Lower bound Δ macro tF1 > −0.02; no class mean Δ < −0.03; recall guard **L3** holds; C's FP components ≤ 1 per case |
| **H2** | Width | Lower bound Δ whole-tree Dice > 0 |
| **H3** | tF1 superior | Lower bound Δ macro tF1 > 0 |

**L3, the recall guard.** For no class may either hold:
- the 10 %-trimmed mean Δ of traced centreline recall (`recall_icx_traced`) is < −0.02;
- or its mean is < −0.02 with a 95 % upper bound < 0.

**Verdicts (fixed sequence):**

| Outcome | Verdict |
|---|---|
| H1 fails | Not adopted; Janus 0 stays |
| H1 passes, H2 fails | Non-inferior, not shown better. Janus 0 stays, unless the lead answers Q4 yes, in which case a1 is adopted if H1's lower bound is > −0.015, worded as such |
| H1 + H2 | **Janus 1-L = a1 at t\***: "better than Janus 0 in lumen width, tF1 non-inferior" |
| H1 + H2 + H3 | As above, "and in tF1" |

**Reports, which decide nothing:**
- Janus 0 at t\* (the threshold alone);
- a1 at argmax (the data alone);
- a2 and E;
- σ_g = |a1 − a2| / √2, with A37's ≥ 2-runs rule if |a1 − a2| > 0.02;
- C's Dice and volume ratio at every t (the transfer of t\*);
- per-class tF1, Dice, tolerant Dice, volume ratio, centreline recall and precision, FP;
- val 80 and locked 20 apart;
- the 89 never-inspected cases.

The verdict states the share of the Dice gain that Janus 0 at t\* already reaches.

## 4. Cost (L-A9; Trillium, 1 × H100, `def-aso22`)

| Job | What | Waits on | GPU-h |
|---|---|---|---|
| **T** | Copy Janus 0 off Fir; set up on Trillium | now (before ~2026-12-20) | 0 |
| **0** | Janus 0 on the 160 (tuning 60 + locked 100) with probabilities; Rule W; baseline and identity scores | T | **3–4** (ceiling 6) |
| P | Dataset of the 720 with Janus 0's plans; preprocess | #306, rounds 2–3 | ≈ 1 |
| a1, a2 | 250 epochs × 181 s = 12.6 h; predict the locked 100; score | P | ≈ 13.5 each |
| E, collect | `-f 0 1` on the locked 100; scoring and the §3 report | a1, a2 | ≈ 1 |
| | **Total** | | **≈ 32–34 + Job 0** (ceiling ≈ 60) |

## 5. Commands for the first jobs (the lead runs them)

### Step T: on Fir's login node (copy Janus 0 before the scratch purge; < 3 GB)

```sh
cd $SCRATCH/icx4
L=$SCRATCH/janus0_out; mkdir -p $L/icx $L/aorta $L/pred_fir
M=nnunet_results/Dataset715_ICX4/nnUNetTrainerICX4__nnUNetResEncUNetPlans_60G_iso05__3d_fullres
mkdir -p $L/$M/fold_0 && cp $M/plans.json $M/dataset.json $L/$M/ && cp $M/fold_0/checkpoint_final.pth $L/$M/fold_0/
curl -sSL https://raw.githubusercontent.com/christianGRogers/Asclepius/dev/experiments/Crucible/j1l_r1/lists.json -o $L/lists.json
for c in $(python3 -c "import json;print(' '.join(json.load(open('$L/lists.json'))['job0']))"); do
  n=$((10#${c:1} + 1)); cp icx/$n.coronary.nii.gz $L/icx/; cp aorta/${c}_aorta.nii.gz $L/aorta/; done
for c in $(python3 -c "import json;print(' '.join(json.load(open('$L/lists.json'))['locked100']))"); do
  cp predictions/$c.nii.gz $L/pred_fir/ 2>/dev/null || echo "no Fir prediction for $c"; done
ls $L/icx | wc -l; ls $L/aorta | wc -l; ls $L/pred_fir | wc -l      # expect 160, 160, 100
(cd $L && sha256sum $M/fold_0/checkpoint_final.pth $M/plans.json lists.json > SHA256SUMS && cat SHA256SUMS)
KEEP=~/projects/def-aso22/$USER/janus0; [ -d ~/projects/def-aso22 ] || KEEP=$HOME/janus0-keep
mkdir -p $KEEP && cp -r $L/. $KEEP/ && echo "kept in $KEEP"          # survives the purge
rsync -av $L/ $USER@trillium-gpu.alliancecan.ca:/scratch/$USER/janus0/
```

**Post on #302:** the three `SHA256SUMS` lines and the three counts.

### Step T: on Trillium (`trillium-gpu.alliancecan.ca`, inside `tmux`)

```sh
cd $SCRATCH/janus0 && sha256sum -c SHA256SUMS
module load StdEnv/2023 python/3.11.5
mkdir -p $SCRATCH/asclepius && cd $SCRATCH/asclepius
git clone -b dev https://github.com/christianGRogers/Asclepius.git repo || git -C repo pull --ff-only
python3 repo/trillium/fetch_cases.py cases      # ~91 GB, resumable; asks for the Girder login once
[ -d $HOME/icx14-venv ] || virtualenv --no-download $HOME/icx14-venv
source $HOME/icx14-venv/bin/activate
pip install --no-index --upgrade pip && pip install --no-index torch && pip install nnunetv2==2.8.1 remotezip nibabel scipy scikit-image
T=$(python -c 'import nnunetv2,os;print(os.path.join(os.path.dirname(nnunetv2.__file__),"training","nnUNetTrainer","variants","icx4"))')
mkdir -p $T && touch $T/__init__.py && cp repo/trillium/icx4/lib/icx4_trainers.py $T/
python repo/experiments/Crucible/j1l_r1/threshold_export.py --selftest && python repo/experiments/Crucible/j1l_r1/decide.py --selftest
```

### Job 0 (≈ 3–4 GPU-h; recommended before round 2, Q2)

```sh
cd $SCRATCH/asclepius/repo/experiments/Crucible/j1l_r1 && sbatch job0_janus0_probs.sh
squeue -u $USER --name j1l-job0
```

**When it has ended:**

```sh
cd $SCRATCH/asclepius/repo/experiments/Crucible/j1l_r1 && tail -12 j1l-job0-*.out
source $HOME/icx14-venv/bin/activate
R=$SCRATCH/asclepius/repo; W=$SCRATCH/j1l_job0; J0=$SCRATCH/janus0
python -c "
import json; L = json.load(open('$R/experiments/Crucible/j1l_r1/lists.json'))
json.dump({'val': [c for c in L['locked100'] if c not in L['locked20_of_open36']]}, open('$W/split_val80.json', 'w'))"
python $R/experiments/Atlas/r9_score_icx4.py --pred $W/thr/t0.50 --pair $J0/pred_fir --icx $J0/icx --aorta $J0/aorta \
  --layout $W/layout.json --splits $W/split_val80.json --set val --np 8 --out $W/scores/identity_val80.json
sha256sum $W/select.json
```

**Read:**
- `summary` is Trillium's val-80 decisive macro and per-class tF1. It must be 0.909 ± 0.003, each class within 0.01.
- `paired` is the per-case agreement with Fir's predictions.

**Post on #302:**
- the `.out` tail;
- the `summary` and `paired` blocks of `identity_val80.json`;
- `select.json`, with its sha256 line.

**Never post:** a file of a sealed case. No job writes one.

### Training jobs (not yet)

P, a1, a2 and E run from `trillium/janus1l` (#306, as amended by L-A10). Its commands are fixed by the round that
freezes #306's spec ([[Janus 1-L Round 1]] §5, item 7).

## 6. What is still open

[[Janus 1-L Round 1]]:
- §5 lists what round 2 must settle;
- §6 has the lead's questions Q1–Q8;
- §7 says what would change the ruling.
