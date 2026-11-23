---
tags: [plans, candidate, track-1-F, round3, janus1-f, D44, D45, D47, fir, locked100, partial-labels, scorer, gates, swe-spec]
author: Foxtrot
track: 1-F
round: 3
version: 3
updated: 2026-11-23
issue: christianGRogers/Asclepius#303
---

# Foxtrot v3 (Janus 1-F): the scorer and the gates frozen by hash, J1F-A's commands written, two stage-2 lines re-cut so a correct model passes them, and stage 1 ready to rule converged

**What this is.** Round 3's answers to [[Janus 1-F Round 2]] §5, items 1–8, on top of the plan in force (Delta v2 as
amended by F-A1 to F-A26) and D45 to D50. It does not re-argue §0 of that ruling.

**Evidence.** CPU only, on D45's 620 training labels:
[[Foxtrot - The amended scorer reproduces the simulated pieces on all 620, and a correct stage-2 model fails L1 and K1 as ruled]].
Code: `experiments/Foxtrot/j1f_r3/`.

**Data rules kept.**
- Only the 620 training labels were fetched (`fetch_620.py`, which asserts the 620's pin and requests no other
  member). Every script asserts the pin again.
- No locked-100 label, sealed case, quality-0 case, D60 CT or TotalSegmentator twin was opened. The locked-100
  numbers below are the counts F-A25 already states.
- Nothing ran on Fir, SciNet or Trillium. Every job is the lead's, as commands (§4).

**Independence.** I read no round-3 candidate of this track, no `exp/j1f-r3-*` branch and no other advocate's
`j1f_r3` folder. Two things reached me without being opened:
- dev's log (`git log`, to branch) shows that the Delta and Crucible v3 PRs are merged;
- one `grep -l j1f_gates` over `experiments/Bridge/` listed three file names under `experiments/Bridge/j1f_r3/`.

I opened none of them. #302's comments were read for Step T's results; they include track 1-L's round-3 summaries,
which say nothing about 1-F.

**What has run.** Step T is done (#302): no class-weighted CE in Janus 0's three logs, `batch_dice` False in its
3d_fullres plans, and `nnUNet_compile` not yet confirmed from Fir's own copy. F0-r2 and Job 0 have not run. The lead
has not answered Q-F2-1 to Q-F2-3. §7 plans for both answers to each.

## 0. The answers in one table, and convergence

| §5 item | Answer | State |
|---|---|---|
| 1. Scorer of record | `experiments/Foxtrot/j1f_r3/j1f_scorer.py`, sha256 **`50826b26…8252`**: Atlas's file with SegQueue's collapse imported and pinned. ⟨PASS⟩ checks pass on six training fixtures. **On all 620, its pieces equal the census F-A15 was simulated on, case for case** | **Settled** |
| 2. `j1f_gates.json` | F-A15's 18 lines, sha256 **`b268a2fc…05de`**. Its test: OM2 recall 0.59 fails; 0.60 (24 of 40) and 0.61 pass; every line's edge; the 4-of-6 edge; a wrong hash refuses | **Settled** |
| 3. J1F-A commands | §4: `check`, `prep`, `train` (a1, a2), the chunked `predict`/`decode`, `collect`, with the Fir header and a disk estimate of ⟨NPZ⟩ GB per locked case | **Settled** |
| 4. Stage-1 spec as one diff against `janus1l` | §5: 21 rows of diff, 14 refusals, 15 self-tests, including F-A19's T test and F-A20's val test, both as runnable reference code (`decode_ref.py`) | **Settled** |
| 5. F-A22's stage-2 numbers | **L1 at 0.02 fails a correct model** (child-over-parent ostia already take ⟨L1⟩ of the LAD group's centreline). **K1 at 0.05 fires on correct septals up to ⟨K1L⟩ mm.** **L2 as worded fails correct septals longer than 35–40 mm** and, with the 1.25 % bound, fails on a single case. Re-cut: L1 and K1 count only runs > 3 mm; L2 measures detached components; 95 % is read as a count | **Settled for submission; frozen before J1F-2** |
| 6. Q-F2-1 to Q-F2-3 | Unanswered. Q-F2-1 and Q-F2-2 change nothing in J1F-A. Q-F2-3 is written both ways (§7), and **T_L's rule sits inside J1F-A's one look** | **Settled for both answers** |
| 7. Step T and F0-r2 | No class-weighted CE: the loss stays. `batch_dice` False: leaf-Dice stays, no `leaf_skip`. **`nnUNet_compile` can be read from the training logs Step T already kept** (nnU-Net prints `Using torch.compile...`). F0-r2: a check with a stop rule, run by `check` before `prep` | **Settled as rules; two posted lines outstanding** |
| 8. Converged? | **Yes for stage 1 (J1F-A and a2)**, on two conditions that are checks, not choices: F0-r2's three lines and the compile `grep` are posted and match. Stage 2 is not up for convergence: its numbers are frozen before J1F-2, as F-A22 allows | §9 |

**Why I call stage 1 converged.** Every §5 item that can change what J1F-A does is now a file with a hash, a command
or a pre-written rule:
- Nothing left open is a design choice.
- The two outstanding inputs, F0-r2 and the compile line, each have a pre-stated outcome table. Neither has a branch
  that sends the plan back to a round, except "the counts differ: stop", which F-A26 already rules.
- The lead's three questions do not touch J1F-A's recipe. Q-F2-3 touches its look, and both answers are written.

## 1. Item 1: the scorer of record

### 1.1 The file

`experiments/Foxtrot/j1f_r3/j1f_scorer.py`, sha256 `50826b26667c999e8e193effe54e60f7832c9166c863c284554491276d8e8252`.

It is Atlas's round-2 `j1f_scorer.py` (`2da3cb1a…886c`) with three edits and no other change:

| Edit | What |
|---|---|
| Header | names the file of record and the change |
| Import | `segqueue14.labels` is imported after its sha256 is asserted (`5f69b5be…0a4b`), as `tf1.py` already is (`24441cf8…5254`) |
| `collapse4` | Atlas's one-voxel ring is replaced by `collapse_to_four` (F-A17). It returns the four-class map **and** SegQueue's contact statistics, so `collect` can report fallbacks (F-A17). It raises if two vessels overlap |

**Every scoring definition is Atlas's, byte for byte** (F-A16): pieces are 26-components of ≥ 20 voxels; the
centreline is the whole reference tree's skeleton restricted to the piece; presence is at 5 mm; detection is ≥ 50 %
within 1.5 mm of predicted vessel of any class; naming is a strict majority, ties wrong; there is one tF1 root per
piece. `score_case`, `pieces_of` and `stage1_labels` are unchanged. `diff` against Atlas's file is 4 hunks.

**One change to Atlas's self-test, and why.** Its synthetic PLB meets its RCA only along an edge (diagonal), with no
shared face. SegQueue counts face contact (`_grow` is the 6-neighbourhood), so that component is an unattached
fallback, and the fallback is the RCA. The self-test now asserts exactly that: the left PDA goes to the LCx by
contact, the PLB to the RCA by fallback, `fallback == 1`. **On every reference map of the 620 the fallback count is
⟨FB⟩** (§1.3). On predictions, a branch that touches its vessel only diagonally will fall back to the RCA. `collect`
counts it, as F-A17 says. For a left PDA that is a voxel error of the collapse, so the count must be read beside V.

### 1.2 Its tests, on training fixtures only

`test_scorer.py`. The fixtures are the six training cases Delta v2 chose (smallest
sha256(`asclepius-j1f-r2-scorertest:` + id): c0585, c0875, c0987, c0287, c0920, c0761). The references are built
with the scorer's own `stage1_labels`. **⟨PASS⟩ of ⟨NCHK⟩ checks pass** (`results/test_scorer.log`):

| Source | Checks |
|---|---|
| Atlas's synthetic self-test | identity; D1/D2 swap; D2 dropped; D2 folded into the LAD; OM1 truncated; D1 cut off from its origin (tF1 falls, detection does not); the left PDA to the LCx by contact; `stage1_labels` on a toy map |
| New, F-A17 | a left PDA touching only its PLB, which touches the LCx, goes to the LCx (the chain rule) with 0 fallbacks; with the PLB removed, it falls back to the RCA and is counted |
| Delta's, per fixture | the collapse equals `territory.to_four` (D25) on every non-"Other", non-255 voxel; fallbacks 0 |
| Delta's, per gated class | identity: recall, presence agreement and naming 1, branch tF1 1; a one-voxel dilation into background keeps recall and naming 1 |
| Delta's, by perturbation | D1/D2 swap: recall 1, naming 0; PDA/PLB swap: the same; OM2 → LCx: recall 1, naming 0, agreement < 1; OM2 → background: recall 0 |
| Atlas's, by perturbation | a one-voxel erosion keeps recall ≥ 0.8 and naming 1; OM folded into the LCx: recall 1, naming 0; PLB dropped: recall 0, every other class unchanged; PDA cut to 30 % of its length: recall 0 |

**One expectation of mine was wrong, and is now a report.** The first run asserted that a PDA truncated to 40 % of its
length is missed. It was missed in 3 of 6 pieces: 40 % kept plus the 1.5 mm tolerance covers 0.44–0.58 of the
centreline, which straddles the 50 % detection line. That is the definition working as written, not a defect. The
check now cuts to 30 % (recall 0) and prints the 40 % value as a report. **Read B1 knowing this: a branch drawn for
the proximal ~45 % of its length counts as detected.**

### 1.3 On all 620: the pieces F-A15 was simulated on (`pass_r3.py`)

The amended scorer was run on every training label (full volume cropped to the tree's box + 12 voxels; every rule is
local or geodesic, and c0000's pieces are identical to the uncropped run).

⟨PASS620⟩

**So F-A15's lines need no re-freeze** (ruling §7, row "per-piece counts differ"): Atlas's `gate_sim.proposed_lines`,
re-derived from the amended scorer's pieces, gives the same 18 numbers.

### 1.4 What `collect` pins

`collect` refuses unless all four of these match the values posted on #303:
- `j1f_scorer.py` `50826b26…8252` (moved unchanged to `trillium/janus1f/lib/`; its two pinned imports resolve to
  `src/`);
- `src/segqueue14/labels.py` `5f69b5be…0a4b`;
- `src/segtrain/tf1.py` `24441cf8…5254`;
- `configs/janus1/j1f_gates.json` `b268a2fc…05de`.

**Versions.** The hashes above freeze the code, not the libraries. The skeleton comes from scikit-image's
`skeletonize`. Atlas's round-2 self-test reproduces its own sha256 line here under numpy 2.5.3, scipy 1.18.1 and
scikit-image 0.26.0. `check` prints the venv's versions and re-runs `test_scorer.py` on Fir, so a library that moves a
skeleton shows up there, before `collect`, not after.

## 2. Item 2: `configs/janus1/j1f_gates.json`

The file is `experiments/Foxtrot/j1f_r3/j1f_gates.json`, sha256
`b268a2fc51c94a248141f4d21e3ef66d155db838b640688a39b41014032905de`. The swe copies it byte-identical to
`configs/janus1/j1f_gates.json`.

| Class | recall ≥ | presence agreement ≥ | naming ≥ |
|---|---|---|---|
| D1 | 0.81 | 0.94 | 0.83 |
| D2 | 0.76 | 0.84 | 0.86 |
| OM1 | 0.75 | 0.90 | 0.78 |
| OM2 | 0.60 | 0.81 | 0.78 |
| PDA | 0.89 | 0.97 | 0.90 |
| PLB | 0.89 | 0.94 | 0.92 |

`k_of_6: 4`; "value ≥ line passes"; recall pooled over reference pieces, naming over detected pieces, presence over
the 100 cases.

`gates.py` is the decision layer `collect` uses (`pool` over `score_case` outputs, then `decide`). Its self-test:
- the file's 18 numbers equal F-A15's table;
- **OM2 recall 0.59 fails; 0.61 passes; 24 of 40 pieces (0.60) passes**;
- each of the 18 lines at line − 0.01 fails that class only, and B still passes (5 of 6);
- two failing classes pass B (4 of 6); three fail it;
- a gates file whose sha256 is not the posted one is refused;
- pooling: naming is over detected pieces only, and recall over pieces across cases.

## 3. Item 7 first: what Step T settled, and the two lines still to post

| Step T result (#302) | Consequence for 1-F |
|---|---|
| `class-weighted CE` 0 times in each of the three logs; `ce_class_weights.json` absent | **J1F-A's loss stays DiceCE, unweighted.** No round-3 loss decision is needed (ruling §7, row 2, does not fire) |
| `batch_dice` of Janus 0's 3d_fullres plans: `False` | **Stage 2 keeps leaf-Dice with `batch_dice: false`** (F-A21). `leaf_skip` is not built |
| `nnUNet_compile`: Fir's `job_body.sh` not found | **Read it from the logs Step T kept.** nnU-Net 2.8.1's `nnUNetTrainer.initialize` writes `Using torch.compile...` into the training log whenever it compiles (`nnUNetTrainer.py` l. 246). The three logs are in `$KEEP` |
| The keep copy is in the lead's Fir home (`$HOME/janus0-keep`) | J1F-A reads `JANUS0=$HOME/janus0-keep` on Fir, with `$SCRATCH/janus0_out` as the fallback |

**The compile line** (Fir login node, seconds):

```sh
K=$HOME/janus0-keep/nnunet_results/Dataset715_ICX4/nnUNetTrainerICX4__nnUNetResEncUNetPlans_60G_iso05__3d_fullres/fold_0
for f in $K/training_log_*.txt; do echo "$(basename $f) $(grep -c 'Using torch.compile' $f)"; done
```

| Output | `nnUNet_compile` for J1F-A |
|---|---|
| every log ≥ 1 | `t` (nnU-Net's default) |
| every log 0 | `f` |
| mixed | the last log's (the chunk that produced `checkpoint_final`) |

- Compilation changes speed and floating-point order, not the recipe. A mismatch would not be a reason to stop. It is
  pinned only so J1F-A matches Janus 0 (L-A21).
- `check` prints the value it will export, and the launcher refuses an unset `JANUS0_COMPILE`.
- **Post on #303:** the three lines.

**F0-r2** has not run. It is unchanged from [[Master plan - Janus 1-F]] §5, with one correction: its `srun` is a
CPU job and stays on `def-aso22`. `check` (§4) re-runs the same counts and refuses `prep` until they match.

| F0-r2 shows | Then |
|---|---|
| both pins and `{'d3': 47, 'd4_to_lad': 2, 'other_lcx': 20, 'other_nearest': 1, 'other_ignore': 8}` | `prep` may run |
| a pin differs | Stop. The PM finds which split copy differs (F-A26) |
| pins match, counts differ | Stop. Fir's label copy differs from Zenodo's (F-A26) |

**The converter of record** (F-A18) is the one F0-r2 runs, `experiments/Foxtrot/j1f_r2/labels_r2.py`'s `map13`
(sha256 `7d1441e3…bf74`). It is Delta's map with D47 (A) hard-wired and F-A3's 255 rule. **On all 620 it agrees
with the scorer's `stage1_labels` on every voxel** (⟨CONVDIFF⟩ voxels differ, §1.3). So the converter the labels are
written with and the converter the scorer's tests build references with are the same function, twice. The swe moves
`map13` to `src/segtrain/j1f_labels.py` unchanged in logic, pinned by the moved file's hash.

## 4. Item 3: the J1F-A command block

### 4.1 Before J1F-A (login node, 0 GPU-h)

1. Post the compile lines and F0-r2's three lines (§3).
2. **The scorer identity (F-A8):** the A1c scorer re-scores Janus 0's own Fir predictions of the val 80. It must give
   decisive macro 0.909 ± 0.003, each class within 0.01. This is CPU on Fir's own files; it does not wait for Job 0.

```sh
module load StdEnv/2023 python/3.11.5
source $HOME/icx14-venv/bin/activate
R=$SCRATCH/asclepius/repo; J0=$HOME/janus0-keep; W=$SCRATCH/j1f_identity; mkdir -p $W
git -C $R fetch origin dev && git -C $R checkout dev && git -C $R pull --ff-only
python -c "
import json; L = json.load(open('$J0/lists.json'))
json.dump({'val': [c for c in L['locked100'] if c not in L['locked20_of_open36']]}, open('$W/split_val80.json', 'w'))"
srun --account=def-aso22 --time=1:00:00 --cpus-per-task=8 --mem=32G \
  python $R/experiments/Atlas/r9_score_icx4.py --pred $J0/pred_fir --icx $J0/icx --aorta $J0/aorta \
  --layout $SCRATCH/icx4/layout.json --splits $W/split_val80.json --set val --np 8 --out $W/identity_val80.json
python -c "import json; print(json.load(open('$W/identity_val80.json'))['summary'])"
```

**Post:** the `summary` line. Outside 0.909 ± 0.003, or a class outside ± 0.01: stop. The PM finds the cause before
anything is trained.

### 4.2 The launcher (`trillium/janus1f/janus1f`, built by the swe to §5)

```sh
cd $SCRATCH/asclepius && git -C repo pull --ff-only && source $HOME/icx14-venv/bin/activate
pip install --no-deps -e repo                       # editable (L-A21): the sealed list resolves from the repo
export JANUS0=$HOME/janus0-keep J1F_WORK=$SCRATCH/janus1f JANUS0_COMPILE=<t|f from §3>
F=repo/trillium/janus1f/janus1f
$F check        # self-tests (§5.3), pins, F0-r2's counts, versions, SBATCH headers; post the printout on #303
$F prep         # CPU job: Dataset 719, plans moved + checked, fingerprint placed, preprocess; ≈ 1 h
$F train a1     # fold 0: two chained 23:50 jobs (afterok), fit checks at epochs 150 and 300
$F train a2     # fold 1, concurrent, its own seed (D47 Q8), if the allocation allows
$F status       # s/epoch, epochs, chain, fitcheck.json, STALL or LEAK if written
$F predict      # afterok a1 (and a2): §4.3; ≈ 1.5 GPU-h per run
$F collect      # login node: §4.4; the one look; refuses a second run
```

**Every GPU job's header** (Fir; the account must be the GPU one):

```sh
#SBATCH --account=def-aso22_gpu
#SBATCH --gpus-per-node=h100:1
#SBATCH --cpus-per-task=12
#SBATCH --mem=280G
#SBATCH --time=23:50:00
```

These are icx4's Fir values (`trillium/icx4/icx4` l. 232–234), which trained Janus 0. `prep` is a CPU job on
`def-aso22` (`--cpus-per-task=16 --mem=64G --time=3:00:00`).

**Train, as the launcher submits it** (a1; a2 is `-f 1` and `SEGTRAIN_SEED=2`):

```sh
export nnUNet_compile=$JANUS0_COMPILE SEGTRAIN_CT_WINDOW=off SEGTRAIN_SAVE_EVERY=10 SEGTRAIN_SAVE_PROBABILITIES=0
export SEGTRAIN_MAX_SECONDS=84000                    # 23:50 - 30 min
export SEGTRAIN_FINETUNE_FROM=$JANUS0/nnunet_results/Dataset715_ICX4/nnUNetTrainerICX4__nnUNetResEncUNetPlans_60G_iso05__3d_fullres/fold_0/checkpoint_final.pth
export SEGTRAIN_FINETUNE_HEADS=parent_copy:$SCRATCH/asclepius/repo/configs/janus1/j1f_parents.json
unset SEGTRAIN_ITERATIONS SEGTRAIN_EPOCHS
nnUNetv2_train 719 3d_fullres 0 -tr nnUNetTrainer_janus1f -p nnUNetResEncUNetPlans_60G_iso05 $CONTINUE
# $CONTINUE is empty in link 1 and "--c" in link 2 (the chain's afterok job)
```

### 4.3 Predict and decode, in chunks of 10 (F-A20)

```sh
P="-d 719 -c 3d_fullres -tr nnUNetTrainer_janus1f -p nnUNetResEncUNetPlans_60G_iso05 -chk checkpoint_final.pth \
   --disable_tta --save_probabilities -npp 2 -nps 2 -device cuda"
for run in a1 a2; do f=$([ $run = a1 ] && echo 0 || echo 1)
  for k in 0 1 2 3 4 5 6 7 8 9; do
    I=$J1F_WORK/in_l100/chunk$k; O=$J1F_WORK/raw_$run/chunk$k    # chunk k = locked ids 10k..10k+9 (sorted)
    nnUNetv2_predict -i $I -o $O -f $f $P
    python -m janus1f.decode --run $run --chunk $k --probs $O --janus0 $JANUS0/pred_fir --out $J1F_WORK/maps_$run
    # decode writes F, T and G for the 10 cases, then deletes $O's .npz, .pkl and nnU-Net's own .nii.gz argmax
  done
done
```

`decode` writes three maps per case and a marker file with their sha256s:

| Map | What |
|---|---|
| F | F-A4's hierarchical decode |
| G | three uint8 channels: the argmax within {LAD, D1, D2, D3}, within {LCx, OM1, OM2, Ramus, PDA, PLB}, within {RCA, PDA, PLB} |
| T | G selected by Janus 0's territory (F-A19); its four classes are Janus 0's file, asserted bit-equal |

**Why G is new.** T_L (§7) needs 1-F's names inside 1-L's territories. 1-L's maps may only exist after `predict` has
deleted the probabilities. G is enough to form T and T_L later from files: a few MB per case instead of a re-run.

**Disk.** One locked case's npz is 13 × X × Y × Z float32, written with `np.savez_compressed`
(`export_prediction.py`). ⟨NPZTEXT⟩

- **Chunk of 10, one run:** ⟨CHUNK⟩ GB of npz on `$SCRATCH` at its peak.
- **Unchunked (100 cases × 2 runs):** ⟨FULL⟩ GB. That is why F-A20 chunks.
- **Memory:** each export holds the float32 array plus its resampling copy, about 2 × the raw size. `-npp 2 -nps 2`
  keeps it under 280 G.
- **Kept after decode:** F, T and G for 100 cases × 2 runs, about ⟨KEPT⟩ GB.

**If track 1-L's Job 0 posts `du -sh $SCRATCH/j1l_job0/probs`** (5 classes), 1-F's per-case npz is about 13/5 of its
per-case figure. Use that number instead of mine if it is larger.

### 4.4 Collect (login node, CPU, ≈ 2 h)

`collect --scorer-sha256 50826b26… --gates-sha256 b268a2fc…`:
1. writes the looks ledger **before** it scores anything, and refuses if a ledger exists;
2. checks every map's `decode` marker;
3. V on F (A1c scorer, F's collapse through `j1f_scorer.collapse4`, Janus 0's in-job aortas), with the contact
   fallbacks counted;
4. B on the reading that would ship (`gates.pool`, `gates.decide`);
5. the verdict table, then V_L and T_L if §7's condition holds;
6. F-A9's reports, a2's reports;
7. `DECISION.md` and `verdict.json`.

**Send back on #303:**
- `check`'s printout;
- `status` after epoch 20 and after epoch 150, with `fitcheck.json`;
- `results/` (no weights, no volumes);
- the `.out` of any failed job.

### 4.5 Cost

| Job | GPU-h |
|---|---|
| a1 (500 epochs at ≈ 192–210 s, two links; two fit checks ≈ 0.3) | ≈ 29–31 (ceiling 47.7) |
| a2 | ≈ 29–31 |
| predict + decode (a1 and a2) | ≈ 3 |
| **Stage 1** | **≈ 61–65** |

## 5. Item 4: the stage-1 spec, as one diff against `janus1l` (L-A21)

`trillium/janus1l` does not exist yet (#306 is built after 1-L converges). The diff is therefore against **L-A21's
text**. Shared parts are imported from `trillium/janus1l/lib/`, not copied: the split guard, the sealed guard, the
plans check, the chain/resume logic, the looks ledger and `status`.

### 5.1 The diff

| # | `janus1l` (L-A21) | `janus1f` |
|---|---|---|
| 1 | Dataset 718, labels by `territory.to_four` | **Dataset 719**, labels by `j1f_labels.map13` (F-A18), 13 classes + `ignore: 255` |
| 2 | 5-class head, strict load | 13-class head: non-head tensors strict and bitwise; every `seg_layers` 1×1×1 conv (deep supervision included) by parent copy from `configs/janus1/j1f_parents.json`, children's biases − log k |
| 3 | val = the 10 lowest-id tuning cases | **val = the 20 fit-check cases** (pin `3f3b696c…1330`), both entries |
| 4 | 250 epochs | **500 epochs** |
| 5 | no in-training check | **fit check** at epochs 150 and 300 on the 20 fit-check cases (F-A5): per-class Dice → `fitcheck.json`; `STALL` at 150 |
| 6 | — | **K1r** at each fit check (§6, stage 2 only; inert in stage 1) |
| 7 | predict: folds 0 and 1 on the locked 100 and D60, E by `nnUNetv2_ensemble` | **predict: a1 and a2 on the locked 100 only, chunked (§4.3); no ensemble; no D60** |
| 8 | export at t_C (`threshold_export.py`) | **no threshold**: decode F, T, G from probabilities (argmax) |
| 9 | `transfer` (Rule T) | **none** |
| 10 | `collect` refuses without `select.json` and `rule_t.json` hashes | `collect` refuses without the scorer, gates, `labels.py` and `tf1.py` hashes (§1.4) |
| 11 | gate L-A16/L-A17, D49 | **V** (F-A6 as amended: L3 on the scorer's `recall`), then **B** (`gates.py`), the verdict table, F-A24's reports, §7's T_L rule |
| 12 | baseline: Janus 0 re-predicted (J0T on Trillium) | **baseline: Fir's own Janus 0 predictions** (`$JANUS0/pred_fir`, F-A8) |
| 13 | `SEGTRAIN_SAVE_PROBABILITIES=0` | the same |
| 14 | `nnUNet_compile` as Janus 0's (`f` in 1-L's text) | **from §3's log lines**, exported as `JANUS0_COMPILE` |
| 15 | Trillium header | **Fir header**, `def-aso22_gpu` (§4.2) |
| 16 | `JANUS0=$SCRATCH/janus0` | `JANUS0=$HOME/janus0-keep` (Step T's Fir route), fallback `$SCRATCH/janus0_out` |
| 17 | — | `check` re-runs F0-r2's counts on the 620 and the scorer's tests on the six fixtures |
| 18 | — | `decode` (a CPU module) and its marker; `collect` reads marked maps only |
| 19 | — | a2's `fitcheck.json` is printed, never read by the stall rule (D47 Q8) |
| 20 | — | contact fallbacks counted for F, T and T_L |
| 21 | — | `collect` reports Ramus and D3 with n and CI, and the rule-ordinal reading (F-A9) |

### 5.2 Refusals (`check` has a failing fixture for each)

1. A sealed or locked id in Dataset 719's training list, or in `splits_final.json`.
2. The split file's hash (`19b832fe…4dd3`) or either list pin.
3. The fit-check 20's pin, or a fit-check id outside the 620.
4. The plans check (L-A21): Janus 0's plans once `dataset_name` and `image_reader_writer` are removed; a changed
   percentile refuses.
5. A missing `dataset_fingerprint.json` in Dataset 719's preprocessed folder.
6. Any `plan_experiment` or `extract_fingerprint` call (a mocked `PATH` fails them).
7. A parent-copy identity error: territory sums not within 1e-5 of Janus 0's, or the hierarchical decode not equal to
   Janus 0's argmax, on a random batch and every deep-supervision output.
8. A dataset id in use.
9. The converter's counts on the 620 not equal to F0-r2's line.
10. The scorer, gates, `labels.py` or `tf1.py` hash.
11. `batch_dice: true` in the moved plans (F-A21's assertion; Step T says `False`).
12. `SEGTRAIN_ITERATIONS` or `SEGTRAIN_EPOCHS` set; `JANUS0_COMPILE` unset.
13. A locked case without a Fir Janus 0 prediction.
14. A second `collect` (the looks ledger), and a `collect` that finds an unmarked map.

### 5.3 Self-tests (each fails on a broken fixture before any submission)

1–5. L-A21's tests 1 (split), 2 (sealed refusals at every mode), 3 (no plan step; plans check), 4 (strict load), 5
     (fingerprint; sealed list resolves).
6. L-A21's test 6 (the trainer diff from live objects), with 13 classes, 500 epochs, ignore 255, val = fit-check 20,
   final validation a no-op, CE weight None.
7. **Parent copy** (Delta §8.3 item 1): sums within 1e-5, decode = Janus 0's argmax; fixture: one head row not
   copied.
8. **Hierarchical decode** (Delta §8.3 item 2): territories = argmax of summed probabilities; plain argmax differs on
   > 1 % of voxels of a parent-copied head; fixture: a decode that takes a plain argmax.
9. **F-A19's T test** (`decode_ref.py`): a PDA-most-likely voxel inside Janus 0's LCx territory is named PDA; T's
   four classes equal Janus 0's map; **fixture: round 2's LCx set without PDA/PLB, which must fail.**
10. **F-A20's val test** (`decode_ref.py`): `splits_final.json` has two identical entries, train = the 620, val = the
    fit-check 20; fixtures: a locked id as val, and a locked id as fit-check case, both refused.
11. **The scorer's tests** (`test_scorer.py`, §1.2) on the six training fixtures.
12. **The gates' tests** (`gates.py selftest`, §2).
13. **Labels** (Delta §8.3 item 4): every Dataset 719 training label collapses to `territory.to_four` except 255 and
    the "Other" voxels; fixture: one L-PDA voxel written as RCA.
14. **No locked-100 number before `collect`:** after `train`, no `validation/` folder and no `summary.json` exist for
    either fold.
15. **Decode's chunk hygiene:** after a mocked chunk, no `.npz`, `.pkl` or nnU-Net `.nii.gz` remains, and every F,
    T and G map carries its marker.

`decode_ref.py` holds runnable reference code for items 9 and 10 and the step-0 identity of the decode
(`python decode_ref.py selftest` passes; the splits it builds hash to `d44d2a24…73fd`).

## 6. Item 5: F-A22's stage-2 numbers, on ImageCAS-X references treated as a prediction

### 6.1 How a "correct stage-2 prediction" was built

ImageCAS-X traced no stage-2 class, so the reference alone has nothing to false-fail. `stage2_falsefail.py` adds a
correct stage-2 prediction to each of the 620 references in two ways:
- **Synthetic septals:** three straight tubes leaving the LAD centreline at 15, 30 and 45 % of its arc, aimed at the
  nearest PDA voxel (through the septum). Radius 0.6, 0.75 or 1.0 mm; length 10 to 60 mm.
- **Real geometry:** a traced branch relabelled as the stage-2 class, D2 (LAD group), OM2 (LCx group) or PLB (RCA
  group).

**Both are painted child over parent**, as D47 Q4 trains them: the branch's ostium voxels inside the parent's lumen
are called the branch. A real branch is grown one voxel into its parent for this.

For power, one wrong model: the septals plus the LAD lumen within ± 5 mm of arc of each origin called S ("the
thief").

**The rules, as F-A22 states them:**
- **L1:** per parent group, the share of reference centreline predicted as a stage-2 class. Pooled over the 100
  cases; one-sided 1.25 % upper bound ≤ 0.02.
- **L2:** in ≥ 95 % of cases, no stage-2 voxel more than 30 mm from predicted coronary foreground.
- **K1:** per stage-2 class, the share of its voxels inside ImageCAS-X's traced lumen, on the 20 fit-check cases,
  ≤ 0.05.

False-fail = the share of 400 random 100-case sets from the 620 on which the correct prediction fails.

### 6.2 Results

⟨STAGE2⟩

### 6.3 What changes, frozen now and binding on J1F-2

| Rule | As ruled | Proposed | Why |
|---|---|---|---|
| **L1** | stage-2 share of the parent's reference centreline, bound ≤ 0.02 | **L1r:** the same, counting only stolen centreline points in 26-connected runs longer than **3 mm**; bound ≤ **0.02** | ⟨L1WHY⟩ |
| **L2** | no stage-2 voxel > 30 mm from predicted coronary foreground in ≥ 95 % of cases | **L2d:** no stage-2 26-component whose **nearest** voxel is > **30 mm** from all other predicted coronary foreground (any class, other stage-2 components included), in **≥ 95 of the 100 cases, read as a count** | ⟨L2WHY⟩ |
| **K1** | share of each stage-2 class's voxels inside traced lumen, fit-check 20, ≤ 0.05 | **K1r = L1r on the fit-check 20**, at each fit check; `LEAK` above **0.02** at the last check | ⟨K1WHY⟩ |
| 95 % | as above | count rule, not a bound | With n = 100, a one-sided 1.25 % Clopper–Pearson lower bound is below 0.95 as soon as one case fails (99 of 100 gives ⟨CP99⟩). Read with the bound, "95 %" means "100 %" |

- **The run length (3 mm)** is longer than any ostial overlap measured here and shorter than the thief's runs (≈ 10
  mm each). It is a property of the rule, not tuned on any model output.
- **L2d still catches what L2 was for:** paint in the ventricle, the aorta or the fat. A blob of stage-2 voxels 30 mm
  from everything fails it whatever its size. A long correct septal, connected to its LAD, never does. A septal broken
  into pieces with gaps under 30 mm never does either, because each piece is within its gap of the next.
- **The first extended reads can still move these numbers** before J1F-2 is submitted (F-A22): the measured septal
  lengths replace my synthetic sweep.

## 7. Item 6: the lead's three questions, both ways

**None of them changes J1F-A's recipe, data or cost.** Q-F2-3 changes what its one look may ship.

### Q-F2-1 (sealed pool in extended mode)

| Answer | Consequence |
|---|---|
| **Yes** | At the seal's single acceptance look (D27, A19), the stage-2 classes are scored on the extended reads as a report, with the D35 tiers' counts printed first. Nothing in J1F-A or J1F-2 waits for it, and it never decides stage 2 |
| **No** | SN, Conus and RMA stay counts only until a larger held-out set exists. D35 can report S1 at most (F-A22 S) |

### Q-F2-2 (Job B, ≈ 22 GPU-h)

| Answer | Consequence |
|---|---|
| **Yes** | Job B runs after J1F-A's verdict, from a1, on Fir's queue after a2. Its result may raise F-A23's thresholds before J1F-2, never lower them |
| **No** (recommended) | F-A23's rule only. Revisit after a near-miss J1F-2 failure |

### Q-F2-3 (T_L: 1-L's vessels with 1-F's names)

**If no:** V_L and T_L are reports only (F-A24 as ruled).

**If yes:** this rule, inside J1F-A's one look. It is pre-registered now, so it needs no other round.

- **Condition:** Janus 1-L is adopted (#302's `collect` says "adopted") before J1F-A's `collect` starts. The ledger
  records which. If it is not, the rule is void and F-A24's reports are skipped.
- **Inputs:** 1-L's shipped locked-100 maps (E at t_C, four classes), copied to Fir by Step T's tar route with their
  sha256 posted on #303. G (§4.3) gives 1-F's names inside 1-L's territories at any time after `decode`.
- **Readings:**
  - **F**, as now;
  - **T**, Janus 0's vessels with 1-F's names;
  - **T_L**, 1-L's vessels with 1-F's names (G selected by 1-L's territory, F-A19's sets). T_L's four classes are
    1-L's maps, asserted bit-equal.
- **V_L:** V's rule (lower bound of Δ decisive macro tF1 > −0.02, no class mean Δ < −0.03, L3, FP ≤ 1), F collapsed
  against **1-L's** maps, one-sided 2.5 %.
- **Which reading ships**, read in order, each row only if the rows above do not apply:

| V (F vs Janus 0) | V_L (F vs 1-L) | B on | Ships |
|---|---|---|---|
| pass | pass | F ≥ 4 of 6 | **F** |
| pass | fail | T_L ≥ 4 of 6 | **T_L** |
| pass | fail | T_L < 4 of 6, F ≥ 4 of 6 | **F**, with V_L's failure in `DECISION.md` |
| fail | — | T_L ≥ 4 of 6 | **T_L** |
| fail | — | T_L < 4 of 6, T ≥ 4 of 6 | **T** |
| otherwise | | | **not adopted** |

- **Why T_L replaces T when F's vessels fail:** both carry vessels that already passed their own track's verdict.
  1-L's passed Janus 0's line with a better-than-Janus-0 or Q4 verdict, so it is the vessel model of record.
- **Why F ships over T_L only when V_L passes:** this is Crucible's rule. Its effect is that a released 1-F never has
  vessels shown worse than the best vessel model.
- **Error rates.** V_L is one more test inside the same look and the same sequence. A reading ships only through
  pre-registered rows, never by the best score. T_L's B uses the same lines as F's; its names are F's names, so its B
  is F's B up to 1-L's territory changes.
- **Cost:** one tar of 100 uint8 maps; CPU at `collect`.

## 8. Corrections this round finds

| Where | Text | Correction | Why |
|---|---|---|---|
| Master plan §5, F-A10 | GPU jobs on `def-aso22` | `--account=def-aso22_gpu` for every GPU job; `def-aso22` for CPU (`srun` of F0-r2, `prep`, the identity) | Fir's GPU allocation is `def-aso22_gpu` (D50; the lead's instruction for #303) |
| Master plan §5, Step T | `$KEEP` under `~/projects/def-aso22` | `$HOME/janus0-keep` on Fir, as Step T ran; the rsync line replaced by the tar route | #302, Step T part 1 |
| Delta v2 §8.6 | plans "byte-identical" | L-A21's plans check (F-A20) | already ruled; listed because §5.1 imports it |
| Delta v2 §8.3 item 3 | "test_branch_score.py's 31 checks" | `test_scorer.py` on the scorer of record (§1.2) | F-A16 moved the definitions to Atlas's file |
| Atlas v2's self-test | PLB → RCA by contact | by fallback (edge-only contact) | SegQueue counts face contact (§1.1) |
| F-A22 | L1, L2, K1 | L1r, L2d, K1r (§6.3) | a correct model fails them |
| F-A23 | (silent) | detection counts a branch drawn for its proximal ~45 % | §1.2's truncation report |

## 9. Item 8: converged?

**Stage 1 (J1F-A, a2): converged, on two posted checks.**

| Was open after round 2 | Now |
|---|---|
| Scorer hash (F-A16) | `50826b26…8252`, tested on training fixtures; pieces identical on all 620 |
| Gates file (F-A15) | `b268a2fc…05de`, tested |
| Commands (Delta §8.1 as amended) | §4, with the chunked predict and its disk estimate |
| Spec (one diff) | §5 |
| Loss after Step T | unweighted DiceCE, unchanged |
| `batch_dice` | `False`: leaf-Dice, no `leaf_skip` |
| `nnUNet_compile` | a `grep` of Step T's kept logs, with its outcome table |
| F0-r2 | a check with a stop rule (F-A26); `check` repeats it |
| Q-F2-3 | both answers written; T_L inside the first look |
| Q-F2-1, Q-F2-2 | stage 2 only |

**What would still send stage 1 back to a round:** F0-r2's counts differing (F-A26: stop), the identity in §4.1
failing (F-A8: stop), or the swe finding that a spec item cannot be built as written. Each is a stop, not a choice
made now.

**Stage 2: not up for convergence.** F-A22 lets its numbers move until J1F-2 is submitted. §6.3's are my proposal
for that freeze. They wait for the first extended reads (band width, F-A21) and the read counts (F-A23).

**What the PM can do once this round rules:** file the `role:swe` issue for `trillium/janus1f` from §5, with §1.4's
four hashes and §4's commands, and release a1 and a2 (≈ 61–65 GPU-h on `def-aso22_gpu`) after the two posted checks
of §3 match.

## 10. What would change this plan

| Observation | Change |
|---|---|
| The compile lines are mixed | the last log's value (§3) |
| F0-r2's pins or counts differ | stop (F-A26) |
| The §4.1 identity misses 0.909 ± 0.003 | stop (F-A8) |
| `check` on Fir prints different library versions and `test_scorer.py` fails there | stop before `prep`; the swe pins the venv's scikit-image to the version that passes |
| Job 0's `du -sh` per case × 13/5 exceeds §4.3's estimate | chunks of 5 instead of 10 |
| 1-L is adopted after J1F-A's `collect` | T_L is never formed for this look; F-A24's reports only |
| The first extended reads show septals longer than 40 mm or ostia overlapping the parent by more than 3 mm | §6.3's run length and L2d's distance are re-set from the reads before J1F-2, never after |

## 11. Files in this PR

`experiments/Foxtrot/j1f_r3/`:
- `j1f_scorer.py` (sha256 `50826b26…8252`): the scorer of record (§1);
- `j1f_gates.json` (sha256 `b268a2fc…05de`) and `gates.py`: the gates and the decision layer (§2);
- `test_scorer.py`: the scorer's tests (§1.2);
- `decode_ref.py`: reference F/T decode and the split builder, with self-tests (§5.3 items 9–10);
- `pass_r3.py`, `summarise_pass.py`: the 620 pass (§1.3);
- `stage2_falsefail.py`, `summarise_stage2.py`: item 5 (§6);
- `npz_size.py`: the disk estimate (§4.3);
- `fetch_620.py`: the sharded fetch of the 620's labels only;
- `results/`: `pass_r3_620.jsonl` (per-case counts, no voxels), `pass_summary.json`, `test_scorer.log` / `.json`,
  `stage2_620.jsonl`, `stage2_summary.json`, `npz_size_*.json`.

Note: [[Foxtrot - The amended scorer reproduces the simulated pieces on all 620, and a correct stage-2 model fails L1 and K1 as ruled]].
