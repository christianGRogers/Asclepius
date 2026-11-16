---
aliases: [Master plan - Janus 1-L, Janus 1-L plan]
tags: [plans, master, track-1-L, janus1-l, four-class, trillium, D45, D46, locked100, ensemble]
status: living
track: 1-L
round: 2
updated: 2026-11-15
issue: christianGRogers/Asclepius#302
---

# Master plan, track 1-L (Janus 1-L)

**In force: [[Candidates/Janus 1-L/Delta v2|Delta v2]] (track 1-L), as amended by the judge in
[[Janus 1-L Round 1]] (L-A1 to L-A12) and [[Janus 1-L Round 2]] (L-A13 to L-A25).**
- The amendments are binding and override the candidate text where they conflict. Where a round-2 amendment changes a
  round-1 one, the round-2 text wins.
- This file is the track's plan. The main [[Master plan]] (Delta v10, Round 10) still governs the pool-driven work,
  D35 and the seal.
- Track 1-F (#303) has its own plan and shares only the split (L-A1).

**Binding decisions:**
- **D45:** the split, Trillium, the lead runs every job.
- **D46:** the lead's answers to round 1 (Q1–Q8).
- **D25 and D8:** four classes by territory, on ImageCAS-X's lumen.
- **D27/D32:** the seals.
- **D35:** decides pool questions only.
- **D34:** naming.
- **D40:** overlaps become ignore, for pool reads.

**Status: round 2 of at least 3.** The training jobs do not start before the round that rules the plan converged
(round 3 at the earliest, and only once Step T and Job 0 have run: [[Janus 1-L Round 2]] §5). **Step T is urgent:**
Fir's scratch purge is about 2026-12-20.

## In one paragraph

**Janus 1-L is Janus 0 fine-tuned warm on D45's 620 ImageCAS-X cases, twice.**
- The repository's A17a trainer, 250 epochs, peak LR 1e-2, Janus 0's plans (identical except `dataset_name` and
  `image_reader_writer`), mirroring off.
- **a1** and **a2** are folds 0 and 1 of the same split entry.
- **The candidate is their ensemble E** (mean softmax), read in a1's place (L-A14; subject to the lead's Q-R2-1).

**Janus 0's one measured defect, a lumen drawn about one voxel thin, is fixed at export.**
- **Rule W** chooses a foreground threshold t\* on Janus 0's own probabilities for the 60 training cases it never saw,
  by Dice with tF1, FP and recall guards. It is frozen before training.
- **Rule T** carries the width t\* gives, not the number, to the candidate. It does this by matching local radius on
  the shared centreline of 60 unlabelled quality-0 CTs (D60). It is frozen before the look.

**The locked 100 judge E at t_C against Janus 0 once, in a fixed sequence:**
- H1: tF1 non-inferior at −0.02, with class, recall and FP guards;
- H2: whole-tree Dice superior;
- H3: tF1 superior.

"Better than Janus 0" means H1 and H2. A non-inferior, not-better candidate is adopted if H1's lower bound is above
−0.015 (D46 Q4). One fallback, a from-scratch run S, is pre-registered with its own look at 1.25 %.

**Cost:** ≈ 33–35 Trillium GPU-h, Job 0 included; S, only if triggered, +≈ 53.

## 1. Data

| Set | Cases | Use |
|---|---|---|
| **Train 620** | ImageCAS-X train 560 + dev 44 + c0123 c0195 c0340 c0416 c0430 c0435 c0447 c0617 c0624 c0660 c0726 c0758 c0772 c0877 c0971 c0984 | Training (folds 0 and 1, identical) |
| ↳ **tuning 60** | dev 44 + those 16; never trained on by Janus 0 | Job 0 chooses t\* on Janus 0's probabilities for them, before any Janus 1-L training. The 10 lowest ids are nnU-Net's fold val (in-sample display only, L-A21) |
| **Locked 100** | val 80 + c0068 c0102 c0251 c0271 c0323 c0327 c0470 c0545 c0592 c0620 c0644 c0805 c0807 c0824 c0827 c0841 c0908 c0946 c0957 c0996 | The one decision (§3). Never trained on, never used to choose anything, never nnU-Net's val |
| **D60** | 60 unlabelled ImageCAS quality-0 CTs (`experiments/Delta/j1l_r2/drift60.json`, pin `916e8a18…004e`) | Rule T only: Janus 0's and the candidate's predictions compared. No label or mask read. Subject to Q-R2-2 |
| Sealed | ImageCAS-X test 80 + quality-0 20 | **Never read, predicted, scored or trained on** |

- **Pins (L-A1):** sha256 of the sorted ids joined by `\n`:
  - locked 100: `bbd9c687818956e2d5664b06fd8c8bd02ddb031e9b9d08036d59cc0e1a4d5895`;
  - train 620: `1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152`.
- **File of record:** `experiments/Delta/j1l_r1/janus1_split_proposal.json` (sha256 `19b832fe…4dd3`), which goes to
  `configs/janus1/split-2026-11.json` under #306.
- **Labels:** ImageCAS-X as drawn (D8), collapsed by `trillium/icx4/lib/territory.py` (D25, D1, D1b), exactly as
  dataset 715.
- **Pool reads:** none in Janus 1-L. When A39's counts are met, the pool fine-tune of Round 10 runs from the adopted
  Janus 1-L (L-A11, L-A19):
  - **member-wise:** pool a1′ starts from a1, pool a2′ from a2, and the candidate is E′;
  - the 620 are the replay set;
  - the locked 100 replace val 80 in G2 and in G3, in L3's form;
  - D35 decides;
  - D44 reads collapse to four by territory before D40, with PDA and PLB by side;
  - material classes follow D46 Q8.

## 2. Recipe (L-A2, L-A3, L-A21)

| Item | Setting |
|---|---|
| Start | Janus 0 `checkpoint_final.pth` (Dataset715), `nnUNetTrainer_segtrain_finetune` (A17a) via the subclass `nnUNetTrainer_janus1l`, full strict load with heads, bitwise-checked, sha256 logged |
| Plans | Janus 0's `plans.json` moved with `nnUNetv2_move_plans_between_datasets` (`ResEnc`, 0.5 mm iso, 256³, batch 2, nnU-Net's default CT normalisation). It must equal Janus 0's except `dataset_name` and `image_reader_writer`. Then `nnUNetv2_preprocess`. **No fingerprint step, no plan step.** Janus 0's `dataset_fingerprint.json` is placed in the preprocessed folder |
| Window check | `SEGTRAIN_CT_WINDOW=off`; `finetune_load` compares plans and normalisation field by field instead |
| Schedule | 2500-iteration linear warm-up to 1e-2, then poly; SGD with Nesterov 0.99; 250 epochs × 250 iterations |
| Loss, augmentation | DiceCE with deep supervision, no class weights (Janus 0's logs must show none, L-A20); nnU-Net default augmentation, **mirroring off** in training and inference |
| Sampling | Uniform over the 620 |
| Validation | Fold val = 10 tuning cases (in-sample display). **nnU-Net's final validation is skipped.** `checkpoint_best` is never read |
| Environment | `SEGTRAIN_SAVE_EVERY=10`, `SEGTRAIN_SAVE_PROBABILITIES=0`, `SEGTRAIN_MAX_SECONDS` = walltime − 30 min, `nnUNet_compile` as Janus 0's (`f`); segtrain installed editable (or `SEGTRAIN_SEALED_LIST` and `SEGTRAIN_POOL_SEAL` set) |
| Checkpoint, inference | `checkpoint_final` only; `--disable_tta`; probabilities saved for the locked 100 and D60 |
| Runs | **a1** = fold 0, **a2** = fold 1 (the same split entry), concurrent. **C = E** = `nnUNetv2_ensemble` of the two folds' probabilities (L-A14). If a2 does not finish within two chained jobs, C = a1 |
| Export | **t_C** = t\* (Job 0, §2.1), moved only by Rule T (§2.2); applied to C, with every report made at t_C too |
| Not in this plan | Skeleton Recall or other topology loss, the 1e-3 arm, class-weighted CE, a new spacing (except as S's form, L-A18), from-scratch training (except S) |

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

### 2.2 Rule T: carrying the width to the candidate (L-A15)

- **Reference:** Janus 0 at t\* on D60, its skeleton and its local radius (EDT).
- **Measure:** dr(t), the 10 %-trimmed mean of C(t)'s radius minus Janus 0's, on the reference centreline points C(t)
  covers, pooled over D60.
- **Choice:** t_C is the t ≤ 0.50 on {0.50, 0.45, …, 0.25} with the smallest |dr|. Ties within 0.005 mm go to t\*, then
  to the larger t.
- **Scope:** if t\* was held back by a guard (Dice at t\* more than 0.002 below the grid's best), t_C = t\*.
- **Code:** `experiments/Delta/j1l_r2/rule_t.py`. It runs on C's probabilities; a1's and a2's dr are reports.
- **Frozen:** `rule_t.json` and its sha256 are posted on #302 before `collect` scores anything.
- If the lead declines D60 (Q-R2-2), t_C = t\*.

## 3. The decision on the locked 100 (L-A5 to L-A8, L-A14 to L-A18)

**Before anything is read: the identity check (L0).**
- Janus 0 re-predicted on Trillium reproduces Fir's val-80 decisive macro **0.909 ± 0.003**.
- Each class is within 0.01 of LM 0.945, LAD 0.903, LCx 0.857 and RCA 0.938.
- ≥ 95 % of cases agree within 0.01 against Fir's own predictions.
- **Otherwise stop.**

**The comparison.**
- **Candidate C** = E at t_C (Janus 1-L.1). **Baseline** = Janus 0 at argmax (Trillium, Job 0).
- Decisive tF1 @ 1.5 mm at A1c `24441cf8…5254`, with Janus 0's A1 aortas.
- A1a/A1b exclusions.
- Paired by case; bootstrap 10 000; one-sided 2.5 % bounds.
- **One look per candidate model. At most two candidate looks in the track** (C, and S if triggered).

| # | Test | Passes when |
|---|---|---|
| **H1** | tF1 non-inferior, nothing lost | Lower bound Δ macro tF1 > −0.02; no class mean Δ < −0.03; recall guard **L3** holds; C's FP components ≤ 1 per case |
| **H2** | Width | Lower bound Δ whole-tree Dice > 0 |
| **H3** | tF1 superior | Lower bound Δ macro tF1 > 0 |

**L3, the recall guard,** on the scorer's per-class `recall` (L-A17). For no class may either hold:
- the 10 %-trimmed mean Δ is < −0.02;
- or its mean is < −0.02 with a 95 % upper bound < 0.

Its stated false-alarm rate is 3–8 %, and up to about 19 % under a broad shift. The report prints each class's excess
kurtosis of the recall Δ.

**Verdicts (fixed sequence; the wording of record is [[Janus 1-L Round 2]] L-A16):**

| Outcome | Verdict |
|---|---|
| H1 fails | Not adopted; Janus 0 stays; S if its trigger fires (§3.1) |
| H1 passes, lower bound in (−0.02, −0.015], H2 fails | Not adopted |
| H1 passes, lower bound > −0.015, H2 fails | **Adopted** (D46 Q4), "non-inferior at 0.015, not shown better" (and, if the lead answers Q-R2-3 yes, only if Δ Dice is not shown worse) |
| H1 + H2 | **Adopted**: "better than Janus 0 in lumen width, tF1 non-inferior at 0.02", with the share sentence |
| H1 + H2 + H3 | As above, "and in tF1" |

- **What ships is C exactly as tested,** E at t_C. Never an argmax export, never a1 alone after the look.
- **The share sentence:** s = (Janus 0 at t_C − Janus 0 at argmax) / (C − Janus 0 at argmax), in Dice. At s ≥ 0.8 it
  says most of the gain is the threshold.

**Reports, which decide nothing:**
- Janus 0 at t_C (the threshold alone);
- a1, a2, a1 at t_C, a1 at argmax, and E − a1 with its CI;
- σ_g = |a1 − a2| / √2, with A37's ≥ 2-runs rule if |a1 − a2| > 0.02;
- C's Dice and volume ratio at every t (the transfer of t_C);
- per-class tF1, Dice, tolerant Dice, volume ratio, centreline recall and precision, FP;
- val 80 and locked 20 apart;
- the 89 never-inspected cases.

### 3.1 The fallback S (L-A18)

- **Trigger:** H1 fails, **and** a1 at argmax and a2 at argmax both have a point Δ macro tF1 < 0 against Janus 0,
  **and** L0 passed. Never on one class, L3 or FP alone with a member ≥ 0.
- **Run:** Janus 0's recipe from scratch on the 620, 1000 epochs, one run, final validation skipped, ≈ 53 GPU-h. Its
  form (0.5 mm or 0.45 mm) is decided by round 3 from Job 0.
- **Look:** Janus 1-L.2 at t\* with Rule T on S, against Janus 0, in the same H1 → H2 → H3, with **every bound at
  one-sided 1.25 %**.
- **Runs only with the lead's allocation** (Q-R2-4). If S fails, Janus 0 stays.

## 4. Cost (L-A25; Trillium, 1 × H100, `def-aso22`, 181 s/epoch)

| Job | What | Waits on | GPU-h |
|---|---|---|---|
| **T** | Copy Janus 0 off Fir (with fingerprint and logs); set up on Trillium | **now** (before ~2026-12-20) | 0 |
| **0** | Janus 0 on the 160 with probabilities; Rule W; baseline and identity scores | T | **3–4** (ceiling 6) |
| 0-CPU | Decomposition (L-A22) and MDE restatement (L-A23) on the login node | 0 | 0 |
| P | Dataset 718 with Janus 0's plans; preprocess | #306, the converged round | ≈ 1 |
| a1, a2 | 250 epochs × 181 s = 12.6 h each, concurrent, no final validation | P | ≈ 25–27 |
| predict | Folds 0 and 1 on the locked 100 and D60; Janus 0 on D60; E by `nnUNetv2_ensemble` | a1, a2 | ≈ 3 |
| transfer, collect | Rule T; then the one look and the reports | predict | 0 (CPU) |
| | **Total** | | **≈ 33–35** (ceiling ≈ 60) |
| S | Only on its trigger and the lead's allocation | the verdict | +≈ 53 (0.45 mm: ≈ 55–60) |

## 5. Commands for the first jobs (the lead runs them)

### Step T: on Fir's login node (copy Janus 0 before the scratch purge; < 3 GB)

**Changed in round 2 (L-A20):**
- the fingerprint copy;
- the training logs and the class-weight check;
- the `nnUNet_compile` line.

```sh
cd $SCRATCH/icx4
L=$SCRATCH/janus0_out; mkdir -p $L/icx $L/aorta $L/pred_fir
M=nnunet_results/Dataset715_ICX4/nnUNetTrainerICX4__nnUNetResEncUNetPlans_60G_iso05__3d_fullres
mkdir -p $L/$M/fold_0 && cp $M/plans.json $M/dataset.json $M/dataset_fingerprint.json $L/$M/ && cp $M/fold_0/checkpoint_final.pth $L/$M/fold_0/
cp $M/fold_0/training_log_*.txt $L/$M/fold_0/
curl -sSL https://raw.githubusercontent.com/christianGRogers/Asclepius/dev/experiments/Crucible/j1l_r1/lists.json -o $L/lists.json
for c in $(python3 -c "import json;print(' '.join(json.load(open('$L/lists.json'))['job0']))"); do
  n=$((10#${c:1} + 1)); cp icx/$n.coronary.nii.gz $L/icx/; cp aorta/${c}_aorta.nii.gz $L/aorta/; done
for c in $(python3 -c "import json;print(' '.join(json.load(open('$L/lists.json'))['locked100']))"); do
  cp predictions/$c.nii.gz $L/pred_fir/ 2>/dev/null || echo "no Fir prediction for $c"; done
ls $L/icx | wc -l; ls $L/aorta | wc -l; ls $L/pred_fir | wc -l      # expect 160, 160, 100
grep -c "class-weighted CE" $L/$M/fold_0/training_log_*.txt          # expect 0 for every file
ls $SCRATCH/icx4/ce_class_weights.json 2>&1 | tail -1                # expect "No such file or directory"
grep -rn "nnUNet_compile" $SCRATCH/icx4/lib/job_body.sh 2>/dev/null || echo "job_body.sh not found"
(cd $L && sha256sum $M/fold_0/checkpoint_final.pth $M/plans.json $M/dataset_fingerprint.json lists.json > SHA256SUMS && cat SHA256SUMS)
KEEP=~/projects/def-aso22/$USER/janus0; [ -d ~/projects/def-aso22 ] || KEEP=$HOME/janus0-keep
mkdir -p $KEEP && cp -r $L/. $KEEP/ && echo "kept in $KEEP"          # survives the purge
rsync -av $L/ $USER@trillium-gpu.alliancecan.ca:/scratch/$USER/janus0/
```

**Post on #302:**
- the four `SHA256SUMS` lines;
- the three counts;
- the `grep -c` counts;
- the `ls` line;
- the `nnUNet_compile` line.

**If any `grep -c` count is above 0, stop** ([[Janus 1-L Round 2]] L-A20).

### Step T: on Trillium (`trillium-gpu.alliancecan.ca`, inside `tmux`)

```sh
cd $SCRATCH/janus0 && sha256sum -c SHA256SUMS
module load StdEnv/2023 python/3.11.5
mkdir -p $SCRATCH/asclepius && cd $SCRATCH/asclepius
git clone -b dev https://github.com/christianGRogers/Asclepius.git repo || git -C repo pull --ff-only
python3 repo/trillium/fetch_cases.py cases      # ~91 GB, resumable, all 1000 CTs (D60 included); asks for the Girder login once
[ -d $HOME/icx14-venv ] || virtualenv --no-download $HOME/icx14-venv
source $HOME/icx14-venv/bin/activate
pip install --no-index --upgrade pip && pip install --no-index torch && pip install nnunetv2==2.8.1 remotezip nibabel scipy scikit-image
T=$(python -c 'import nnunetv2,os;print(os.path.join(os.path.dirname(nnunetv2.__file__),"training","nnUNetTrainer","variants","icx4"))')
mkdir -p $T && touch $T/__init__.py && cp repo/trillium/icx4/lib/icx4_trainers.py $T/
python repo/experiments/Crucible/j1l_r1/threshold_export.py --selftest && python repo/experiments/Crucible/j1l_r1/decide.py --selftest
```

### Job 0 (≈ 3–4 GPU-h; D46 Q2)

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

### After Job 0: the decomposition and the MDE (login node, CPU, ≈ 1 h; L-A22, L-A23)

Run these only if L0 passed.

```sh
source $HOME/icx14-venv/bin/activate
R=$SCRATCH/asclepius/repo; W=$SCRATCH/j1l_job0; J0=$SCRATCH/janus0
git -C $R pull --ff-only
T=$(python -c "import json;print('%.2f' % json.load(open('$W/select.json'))['chosen_t'])")
python $R/experiments/Bridge/j1l_r2/error_decomp.py --selftest
for t in 0.50 $T; do
  python $R/experiments/Bridge/j1l_r2/error_decomp.py --pred $W/thr/t$t --icx $J0/icx --aorta $J0/aorta \
    --layout $W/layout.json --np 8 --out $W/scores/error_decomp_tuning60_t$t.json
done
python $R/experiments/Delta/j1l_r2/mde_from_job0.py $W/scores/locked100_janus0_argmax.json
```

**Post on #302:**
- the two printed `summary` blocks (no per-case rows, no volumes);
- the MDE printout.

**Never post:** a file of a sealed case. No job writes one.

### Training jobs (not yet)

P, a1, a2, predict, transfer and collect run from `trillium/janus1l` (#306), built to [[Janus 1-L Round 2]] L-A21
after the round that rules the plan converged. That round writes their exact commands.

## 6. What is still open

[[Janus 1-L Round 2]]:
- §5 lists what round 3 must settle. Round 3 can rule the plan converged only once Step T and Job 0 have run and the
  lead has answered;
- §6 has the lead's questions Q-R2-1 to Q-R2-4;
- §7 says what would change the ruling.
