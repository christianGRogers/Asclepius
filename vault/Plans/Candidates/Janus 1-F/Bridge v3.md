---
tags: [plans/candidate, bridge, janus-1f, branches, partial-labels, fir, D45, D46, D47, D49, D50, round3]
author: Bridge
track: Janus 1-F
round: 3
updated: 2026-11-23
issue: christianGRogers/Asclepius#303
---

# Bridge v3 (Janus 1-F): the scorer, the gates and J1F-A's commands are ready; fix two launcher defects and three stage-2 numbers before they cost a run

## 0. Position in one paragraph

Bridge accepts the plan in force ([[Master plan - Janus 1-F]]: Delta v2 as amended by F-A1 to F-A26, with D47) and
answers the eight items of [[Janus 1-F Round 2]] §5 with CPU work in `experiments/Bridge/j1f_r3/`. **Stage 1 (J1F-A)
is converged in Bridge's view**, on two conditions. Neither one is a plan question:
- F0-r2 must print its expected lines (it is now also a `check` refusal);
- the lead's answer to Q-F2-3 must be on record before J1F-A is submitted. §6 writes both branches now, so either
  answer leaves nothing to decide.

**Stage 2 (J1F-2) is not converged, and it does not need to be yet.** Its numbers are frozen before J1F-2, never before
J1F-A (F-A22). This round finds that two of them would fail a correct stage-2 model (§5).

What this round finds:
1. **The scorer of record exists** (item 1): `j1f_scorer.py`, sha256 `7e6875a3…ff78`.
   - It is Atlas's file with SegQueue's `collapse_to_four` in place of the ring collapse.
   - Its pieces reproduce the census the F-A15 lines were simulated on, case for case, over the 620 (§1.3).
   - Delta's 31 checks and Atlas's perturbations pass on training cases.
2. **`j1f_gates.json`** (item 2), sha256 `16ce8954…1b6b`: OM2 recall 0.59 fails, 0.60 and 0.61 pass, and every one of
   the 18 lines bites 0.01 below its value.
3. **Two launcher defects would stop or break J1F-A** (item 4). Both are found in nnU-Net 2.8.1's own source:
   - **F-A3's ignore value 255 cannot be used.** nnU-Net asserts that the ignore label is the largest label + 1, so
     with 13 classes it must be **13**. Training would die at its first step. `collect` maps 13 back to 255.
   - Prediction writes **float32** probabilities at the original CT size: 3.5–3.75 GB per case before compression.
     The chunk of 10 needs up to **38 GB** of scratch (§3.2).
4. **F-A22's stage-2 numbers on a simulated correct model** (item 5), over 120 training cases:
   - **L2 (30 mm far paint) fails every correct model whose straight branches are longer than about 30 mm.** Read
     with a one-sided 1.25 % bound, it also needs 100 of 100 cases: at 99 of 100, the lower bound is 0.938. So when
     only 1–2 % of cases cross 30 mm, a correct model still fails 56–81 % of the time. **Proposed:** L2 counts
     **islands** (stage-2 components more than 5 mm from stage-1 foreground), on ≥ 95 of 100 cases. The 30 mm
     distance becomes a report.
   - **K1 (0.05 of stage-2 voxels inside the traced lumen) writes `LEAK`** for a correct model that paints each
     branch's first 2.5 mm over its host, as D47 Q4 teaches. With branches ≤ 20 mm it does so in essentially every
     draw, and at 30 mm for four of six classes 61–99 % of the time. **Proposed:** K1 reads L1's centreline
     statistic on the 20 fit-check cases, with `LEAK` above 0.03.
   - **L1 (0.02 theft) holds,** but with little room: the same correct model takes 1.6–1.7 % of the LAD and RCA
     centreline. **Kept.**
5. **Step T's results change nothing in the recipe** (item 7):
   - no class-weighted CE, so the loss stays unweighted DiceCE;
   - `batch_dice` False, so leaf-Dice stays and `leaf_skip` is not needed;
   - `nnUNet_compile` is pinned to `f` explicitly, and Fir's own setting, when found, is a report.

## 1. What this round read, and independence

- **Read:**
  - [[Human decisions]] (D44–D50);
  - [[Janus 1-F Round 2]] (all of it);
  - [[Master plan - Janus 1-F]];
  - [[Master plan - Janus 1-L]] §2 and §5, and [[Janus 1-L Round 2]] L-A20/L-A21;
  - my own [[Candidates/Janus 1-F/Bridge v2|Bridge v2]];
  - Delta v2 §8 (the spec the ruling adopts);
  - the code the ruling names: Atlas's `j1f_scorer.py`, `gate_sim.py` and `validate_scorer.py`; Delta's
    `branch_score.py` and `test_branch_score.py`; `src/segqueue14/labels.py`; Foxtrot's `fitcheck20.json`;
  - nnU-Net 2.8.1's wheel (`export_prediction.py`, `label_handling.py`, `move_plans_between_datasets.py`,
    `nnUNetTrainer.py`).
- **Read on #302:** Step T's two result comments.
  - That thread also carries the round-3 summaries of **track 1-L**. Bridge read them; they belong to the other
    track.
- **Not read:** no other round-3 candidate of this track, and no `exp/j1f-r3-*` branch.
- **Data:**
  - the ImageCAS-X segmentations of the **620 training cases only**, fetched by `experiments/Bridge/j1f_r2/fetch_seg620.py`
    (Zenodo 10.5281/zenodo.21887809, CC BY 4.0);
  - the split re-checked against the D45 pin `1350cb1f…1152`.
- **Not opened:** no locked-100, sealed, quality-0 or D60 label or CT, no model output and no pool read.
- **Nothing ran on Fir, SciNet or Trillium.**

## 2. Item 1: the scorer file of record

### 2.1 The file

**`experiments/Bridge/j1f_r3/j1f_scorer.py`, sha256 `7e6875a3cec72727572d4a5ab2675eec75b18b0b8daa94698a20b315dadfff78`.**
It is Atlas's round-2 file (`2da3cb1a…886c`) with exactly three changes:

| Change | Why |
|---|---|
| `collapse4` calls `segqueue14.labels.collapse_to_four`; `labels.py`'s sha256 `5f69b5be…0a4b` is asserted at import, beside `tf1.py`'s `24441cf8…5254` | F-A17. It returns the fallback counts (`components`, `fallback`, `fallbackTie`, `fallbackUnattached`, `byParent`), which `collect` reports for F and T. It works in the foreground's box, one voxel wider, because contact never reaches further |
| `stage1_labels` is removed | F-A18 makes `j1f_labels.py` the converter of record. Two converters in two hashed files would have to be kept in step |
| `load_gates`, `aggregate`, `verdict` are added | So the B reading is in the hashed file too: recall and naming pooled over pieces, presence agreement over cases, a line met at equality, ≥ 4 of 6. `load_gates` refuses a wrong sha256, a missing class, a line outside [0, 1], or `k_of_6`, `presence_mm` or `tol_mm` different from the scorer's |

**The definitions are Atlas's, unchanged:** pieces, centreline, length, root, presence at 5 mm, detection, naming by
strict majority, branch tF1. `pieces_of` and `score_case` are byte-identical to Atlas's.

### 2.2 Its tests

| Test | Where | Result |
|---|---|---|
| Atlas's synthetic self-test, plus three collapse tests and the gate reading | `python3 j1f_scorer.py selftest` | **ok** |
| — chain rule: a PLB hanging off a left PDA's tip, touching only the PDA, goes to the LCx | | ok |
| — an unattached PDA falls back to the RCA, and the count goes up by one | | ok |
| — OM2 recall 23/40 fails, 24/40 (= 0.60) passes, 25/40 passes; no detected piece gives naming NaN, which fails | | ok |
| Delta's 31 checks, ported to per-piece aggregation, on **the same six training cases** Delta's test names (`asclepius-j1f-r2-scorertest:` salt) | `test_scorer_cases.py` → `test_scorer_cases.out` | **RESULT_CASES** |
| Atlas's four real-case perturbations as checks: fold OM → LCx, drop PLB, truncate PDA to 40 %, erode by one voxel | same | (in the line above) |

**One finding from writing the tests.** Atlas's toy has a PLB that meets its RCA only diagonally.
- SegQueue's contact rule counts **face** contact only, so that PLB is an unattached component. It falls back to the
  RCA (the right answer here) and is counted.
- On a prediction, a branch that meets its parent only through an edge or a corner is therefore a fallback, not a
  wrong side. `collect` reports the count, and on the 620 references it is **0** (§2.3).

### 2.3 The 620: the scorer counts what the lines were simulated on

`run620.py` runs the scorer of record on each of the 620 training references, at native spacing, cropped to the tree
plus 8 voxels. The output is `run620_summary.json` (per-case rows stay off the repo, in the scratch run).

RESULT_620

### 2.4 What `collect` pins

- `j1f_scorer.py` `7e6875a3…ff78`;
- `src/segqueue14/labels.py` `5f69b5be…0a4b`;
- `src/segtrain/tf1.py` `24441cf8…5254`;
- `configs/janus1/j1f_gates.json` `16ce8954…1b6b`.

**The swe copies the scorer byte-identical** into `trillium/janus1f/lib/`. Its only relative path is the
`../../../src` import root: the swe replaces that one line with the repo root and re-posts the sha256.
- That is a one-line, reviewable change. The hash in the issue is the copied file's, and the copy must pass the same
  self-test.

## 3. Items 2 and 3: the gate file and the J1F-A commands

### 3.1 `configs/janus1/j1f_gates.json`

The file is proposed at `experiments/Bridge/j1f_r3/configs/j1f_gates.json`. The swe moves it to
`configs/janus1/j1f_gates.json` unchanged: **sha256 `16ce89544323414291401f3c1fb167d7db7af484a8f89b45e7279a15aac01b6b`.**
- **It holds F-A15's 18 lines**, equal to `experiments/Atlas/j1f_r2/gate_sim.json`'s `proposed_lines`, which the
  script checks;
- plus `k_of_6: 4`, `presence_mm: 5.0` and `tol_mm: 1.5`.

**`test_gates.py`** (all pass, no data read):

| Check | Result |
|---|---|
| The file's lines equal F-A15 | PASS |
| OM2 recall 0.59 → OM2 fails, B still passes (5 of 6) | PASS |
| OM2 recall 0.60 and 0.61 → OM2 passes | PASS |
| Each of the 18 lines holds at its value and fails 0.01 below | PASS |
| Three classes failing → 3 of 6, B fails | PASS |
| A changed file is refused by its sha256; `k_of_6 ≠ 4` is refused | PASS |

### 3.2 Disk for the chunked predict (F-A20)

nnU-Net 2.8.1 writes `np.savez_compressed(probabilities=…)`:
- in **float32** (logits are cast to float before the softmax: `label_handling.py` l. 138, `export_prediction.py`
  l. 101);
- at the CT's **original** shape, 13 channels.

`npz_size.py` measures this on two training cases (`npz_size.out`):

| Case shape | Uncompressed (the ceiling) | npz, smooth softmax | npz, softmax with noise of SD 0.5 in the logits |
|---|---|---|---|
| 512 × 512 × 275 | 3.75 GB | 0.02 GB | 3.23 GB |
| 512 × 512 × 259 | 3.53 GB | 0.02 GB | 3.04 GB |

- A real network falls between the two columns, and no model exists here to say where.
- **So a chunk of 10 is budgeted at its ceiling: ≤ 38 GB of npz,** plus ≈ 0.1 GB of exports. That is small against a
  Fir scratch quota, and it is what the chunking buys. Unchunked, the 100 would need up to 375 GB.
- **`decode` holds one case's float32 array (≤ 3.75 GB) and its group sums.** The predict job is sized at 96 GB.
- **The lead posts `du -sh` of the first chunk's npz.** That number replaces the ceiling for any later run.

### 3.3 The J1F-A command block for the master plan (§5, "J1F-A")

**Preconditions:**
- the `role:swe` issue is built (F-A12), filed after the round that rules convergence;
- `configs/janus1/split-2026-11.json`, `configs/janus1/j1f_gates.json` and the scorer copy are merged, with their
  hashes posted on #303;
- F0-r2 has printed its three expected lines.

**Account rules (Fir):** GPU jobs use `--account=def-aso22_gpu --gpus-per-node=h100:1` with explicit
`--cpus-per-task` and `--mem`. CPU jobs use `def-aso22`.

On `fir.alliancecan.ca`, inside `tmux`:

```sh
module load StdEnv/2023 python/3.11.5
cd $SCRATCH/asclepius && git -C repo fetch origin dev && git -C repo checkout dev && git -C repo pull --ff-only
source $HOME/icx14-venv/bin/activate
pip install --no-deps -e repo                                  # L-A21: editable, so the sealed list resolves
export JANUS0=$SCRATCH/janus0_out                              # Step T's Fir folder ($HOME/janus0-keep after a purge)
export J1F_WORK=$SCRATCH/janus1f && mkdir -p $J1F_WORK
export nnUNet_raw=$J1F_WORK/raw nnUNet_preprocessed=$J1F_WORK/pre nnUNet_results=$J1F_WORK/results
export nnUNet_compile=f                                        # §7; pinned, not inherited
L=$SCRATCH/asclepius/repo/trillium/janus1f
$L/janus1f check 2>&1 | tee $J1F_WORK/check.txt                # self-tests + dry run; post on #303. Stops on any REFUSE

# prep: dataset 719 (the 620 + the locked 100's images; labels with ignore = 13), plans moved, preprocess only
P=$(sbatch --parsable --account=def-aso22 --job-name=j1f-prep --time=4:00:00 --cpus-per-task=16 --mem=64G \
      --export=ALL --wrap "$L/janus1f prep")

# a1 = fold 0: two chained 24 h links (500 epochs ≈ 25-31 h); each link stops itself 30 min before its walltime
for RUN in a1 a2; do                                           # a2 = fold 1, report only (D47 Q8); drop it if the allocation is short
  X=$(sbatch --parsable --dependency=afterok:$P --account=def-aso22_gpu --gpus-per-node=h100:1 --cpus-per-task=12 \
        --mem=96G --time=24:00:00 --job-name=j1f-$RUN-1 --export=ALL,J1F_RUN=$RUN,SEGTRAIN_MAX_SECONDS=84600 \
        $L/jobs/train.sh)
  Y=$(sbatch --parsable --dependency=afterany:$X --account=def-aso22_gpu --gpus-per-node=h100:1 --cpus-per-task=12 \
        --mem=96G --time=24:00:00 --job-name=j1f-$RUN-2 --export=ALL,J1F_RUN=$RUN,SEGTRAIN_MAX_SECONDS=84600 \
        $L/jobs/train.sh)                                      # resumes from checkpoint_latest; refuses if link 1 died before epoch 10
  # predict: the locked 100 in chunks of 10, --save_probabilities --disable_tta -chk checkpoint_final.pth;
  # decode writes F and T, then deletes the chunk's npz and nnU-Net's own argmax export
  sbatch --dependency=afterok:$Y --account=def-aso22_gpu --gpus-per-node=h100:1 --cpus-per-task=12 --mem=96G \
        --time=6:00:00 --job-name=j1f-$RUN-pred --export=ALL,J1F_RUN=$RUN $L/jobs/predict.sh
done
$L/janus1f status                                              # s/epoch, epoch, chain state, fitcheck.json (epochs 150, 300)
```

**After `j1f-a1-pred` has ended** (`collect` is one look; it refuses a second run):

```sh
$L/janus1f status                                              # expect 100 F maps and 100 T maps with decode's marker, 0 npz left
cat $J1F_WORK/predict/a1/npz_chunk01.txt                      # du -sh of chunk 1's npz, written by predict before it deletes them
sbatch --account=def-aso22 --job-name=j1f-collect --time=4:00:00 --cpus-per-task=16 --mem=64G \
       --export=ALL,J1F_RUN=a1 --wrap "$L/janus1f collect"     # V on F, then B on the reading that ships; DECISION.md
```

**Send back on #303:**
- `check.txt`;
- `status` after epoch 20 and after epoch 150, with `fitcheck.json`;
- the first chunk's npz size;
- `results/DECISION.md` and `results/verdict.json` (no weights, no volumes, no per-case label);
- the `.out` of any failed job.

**Cost:** prep ≈ 1 CPU job. a1 ≈ 29–31 GPU-h (ceiling 48). a2 the same. Predict ≈ 1 GPU-h per run. `collect` is
CPU only: ≈ 25 s per case per reading on one core, from `run620.py`'s timing.

## 4. Item 4: the converged stage-1 spec, as one diff against `janus1l` (L-A21)

`trillium/janus1f` imports from `trillium/janus1l/lib/` what L-A21 freezes: the split guard, the sealed guard, the
plans check, the chain logic and `status`. The lines below are the whole difference.
- `+` is added for 1-F;
- `~` is changed;
- `=` is kept as L-A21 has it.

```diff
= install: pip install --no-deps -e repo (or SEGTRAIN_SEALED_LIST + SEGTRAIN_POOL_SEAL)
~ dataset: 718 -> 719; the 620 + the locked 100's images; labels by j1f_labels.py (F-A18: D47 (A) hard-wired, F-A3's ignore rule)
+ dataset.json labels: background 0 ... PLB 12, "ignore": 13       # nnU-Net 2.8.1 label_handling.py l. 41: ignore == max + 1; 255 would die at the first step
+ collect reads every reference through lab[lab == 13] = 255 before j1f_scorer (whose IGNORE is 255)
= plans: Step T's plans.json -> Dataset715 preprocessed as nnUNetResEncUNetPlans_60G_iso05.json; move_plans -sp nnUNetResEncUNetPlans_60G_iso05 (no -tp); preprocess only
= plans check: equal to Janus 0's once dataset_name and image_reader_writer are removed; a changed percentile refuses
= fingerprint: Step T's dataset_fingerprint.json into Dataset719's preprocessed folder; no extract_fingerprint, no plan_experiment
~ splits_final.json: two identical entries, train = the 620, val = the 20 fit-check cases (sha256 3f3b696c...1330, = Foxtrot's fitcheck20.json)
~ trainer: nnUNetTrainer_janus1f(nnUNetTrainer_janus1l): 13 outputs; non-head tensors strict and bitwise; every seg_layers head (deep supervision included) by parent copy (configs/janus1/j1f_parents.json)
= final validation: a no-op; checkpoint_best never read; SEGTRAIN_SAVE_EVERY=10; SEGTRAIN_MAX_SECONDS = walltime - 30 min; SEGTRAIN_ITERATIONS/EPOCHS unset
~ epochs: 250 -> 500
+ fit check (F-A5): epochs 150 and 300, the 20 fit-check cases, decode F, per-class Dice -> fitcheck.json; at 150 D1, OM1, PDA or PLB < 0.10 writes STALL; a1 only
+ K1 is not in stage 1 (no stage-2 class exists)
= loss: DiceCE, deep supervision, CE weight None (Step T: no class-weighted CE); ignore label 13; batch_dice as Janus 0's plans (False)
= mirroring off in training and inference; uniform sampling; --disable_tta
~ nnUNet_compile: as Janus 0's -> f, pinned in the job environment (§7)
~ predict: locked 100 only (no D60, no ensemble, no threshold): chunks of 10, --save_probabilities --disable_tta -chk checkpoint_final.pth
+ decode: F (hierarchical) and T (F-A19) per case, from the npz; then the chunk's npz and nnU-Net's argmax export are deleted; each map carries decode's marker
+ predict writes du -sh of chunk 1's npz to predict/<run>/npz_chunk01.txt before deleting it (the disk budget's measured value)
- transfer (Rule T), ensemble (E), threshold export: not in 1-F (1-F reads at argmax)
~ collect: V on F collapsed (A1c tF1, icx4's aortas, A1a/A1b exclusions, Janus 0's Fir predictions as baseline, L3 on the scorer's recall); then B on the reading that ships (j1f_scorer + j1f_gates.json); F, T, and (if 1-L is adopted) V_L/T_L as §6; writes DECISION.md, verdict.json; a looks ledger opened BEFORE the first score
```

**The self-tests (`janus1f check`; each must fail on a broken fixture before any submission).** These are Delta
§8.3 as amended by F-A16 to F-A20, plus the two the ruling asks for.

| # | Test | Broken fixture that must fail |
|---|---|---|
| 1 | L-A21's tests 1–4: split pins (`train620 1350cb1f…1152`, `locked100 bbd9c687…5895`), seals, no plan step, strict load | a sealed id in train; a mocked `plan_experiment` call; a changed percentile |
| 2 | Parent copy: on a random batch, the territory sums of the 13-channel softmax equal Janus 0's 5-channel softmax within 1e-5, and decode F equals Janus 0's argmax, for every deep-supervision output | one head row not copied |
| 3 | Decode F: territory = argmax of the group sums; plain argmax differs on > 1 % of random voxels (tripwire) | a decode that takes a plain argmax |
| 4 | **F-A19's T test:** a voxel in Janus 0's LCx territory where PDA is 1-F's best class is named PDA; T's four classes equal Janus 0's map bit for bit | the old T (LCx territory over {LCx, OM1, OM2, Ramus}) |
| 5 | **F-A20's val test:** no locked or sealed id anywhere in `splits_final.json`; two identical entries; val ⊂ train | a locked id in val; a locked id in train |
| 6 | Labels: `j1f_labels.py`'s totals on the 620 are `{'d3': 47, 'd4_to_lad': 2, 'other_lcx': 20, 'other_nearest': 1, 'other_ignore': 8}`; `collapse4` equals `territory.to_four` on every voxel outside "Other" and the ignore value | one L-PDA voxel written as RCA |
| 7 | **The ignore value:** `dataset.json` with `"ignore": 13` builds nnU-Net's `LabelManager`; label files hold no 255 | a file with 255, or `"ignore": 255` |
| 8 | The scorer: `j1f_scorer.py selftest`, `test_scorer_cases.py` on its six training cases, `test_gates.py` | a scorer whose sha256 differs |
| 9 | The locked 100 is never scored before `collect`: no `summary.json` and no validation folder for fold 0 after `train`; `collect` reads only maps with decode's marker; the ledger is written before the first score | a fold-0 `validation/` folder present |
| 10 | The trainer diff from live objects (L-A21 test 6) with 13 classes and 500 epochs | `num_epochs = 250` |

The reference implementations of tests 3–5 are in `decode_ref.py` (`decode_F`, `decode_T`, `splits`). Its self-test
passes, and it recomputes the fit-check 20 from the D45 split: sha256 `3f3b696c…1330`, equal to Foxtrot's
`fitcheck20.json`.

**Refusals (Delta §8.6, amended):**
- a sealed or locked case in training;
- **plans failing L-A21's check** (not "not byte-identical", which always fails);
- a parent-copy identity error above 1e-5;
- a used dataset id;
- a scorer, `labels.py`, `tf1.py`, `j1f_labels.py` or gate-file sha256 mismatch;
- a missing Janus 0 baseline prediction for any locked case;
- an incomplete CT or label set (the icx4 fetch steps are printed, and the job stops);
- **F0-r2's three lines not reproduced** by `check` (new: `check` re-runs F0-r2's print on the copy `prep` will use);
- a `"ignore"` value other than 13 in `dataset.json` (new).

## 5. Item 5: F-A22's stage-2 numbers on references treated as predictions

### 5.1 What "references as predictions" can and cannot show

- **ImageCAS-X's reference holds no stage-2 voxel.** Treated as a prediction, it gives L1 = 0, L2 passes and K1 = 0
  in every one of the 620 cases. So none of the four numbers false-fails the bare reference.
- **That says nothing about the lines,** which bite only on stage-2 paint. `stage2_sim.py` adds what a **correct**
  stage-2 model would paint, onto 120 hash-chosen training references:
  - six straight tubes (radius 0.6 mm): S1–S3 off the proximal LAD at 10 / 25 / 40 mm from its start, heading into
    the heart; Conus and SN off the proximal RCA at 5 / 12 mm; RMA off the RCA at 40 mm;
  - their length L swept over 10–50 mm. A straight tube is the worst case for a distance line;
  - two junction models:
    - **out:** the model never paints a traced voxel;
    - **junc:** the model also paints its host's lumen along the branch's first 2.5 mm, as a model trained on pool
      reads learns under D47 Q4 (a child drawn over its own parent trains as the child).
- **Each number is read as F-A22 words it, at one-sided 1.25 %,** on locked-size resamples (100 cases; 20 for K1).
- No anatomical claim rests on L: it is a sweep.

### 5.2 Results (`stage2_summary.json`)

**120 training cases** (hash-chosen, salt `asclepius-j1f-r3-bridge-stage2:`). Every simulated branch is correct by
construction, so every fail below is a **false** fail.

| Branch length L | Junction | L1 share taken, LAD / RCA group | L1 false-fail | Cases with a stage-2 voxel > 30 mm | **L2 false-fail** | L2′ false-fail | K1 share (range over the six classes) | **K1 `LEAK` rate** | K1′ `LEAK` rate |
|---|---|---|---|---|---|---|---|---|---|
| 10 mm | junc | 0.017 / 0.016 | 0 | 0 | 0 | 0 | 0.11–0.16 | **1.00** in all six | 0 |
| 20 mm | junc | 0.017 / 0.016 | 0 | 0 | 0 | 0 | 0.059–0.084 | **≥ 0.998** in all six | 0 |
| 30 mm | junc | 0.017 / 0.016 | 0 | 0.017 | **0.81** | 0 | 0.040–0.057 | S1 0.61, S2 0.07, S3 0, SN 0.98, Conus 0.99, RMA 0.82 | 0 |
| 30 mm | out | 0 / 0 | 0 | 0.008 | **0.56** | 0 | 0 | 0 | 0 |
| 40 mm | either | 0.017 / 0.016 (junc), 0 (out) | 0 | **1.00** | **1.00** | 0 | ≤ 0.043 (junc) | ≤ 0.002 | 0 |
| 50 mm | either | as above | 0 | **1.00** | **1.00** | 0 | ≤ 0.036 (junc) | 0 | 0 |

Reading the table:
- **L1 holds** in every scenario. A correct model that paints its junctions takes 1.6–1.7 % of the host group's
  centreline (LCx 0, since no stage-2 class leaves the LCx here, though SN may in a left-dominant heart). Its upper
  bound stayed under 0.02 in every resample. The margin is about 0.003.
- **L2 is the problem, for two reasons:**
  - **Its distance:** a straight correct branch longer than about 30 mm puts its tip beyond 30 mm in every case.
  - **Its bound:** at L = 30 mm only 0.8–1.7 % of cases cross the line, yet L2 false-fails 56–81 % of the time.
    The 1.25 % Clopper-Pearson lower bound of "≥ 95 % of 100" is 0.957 at 100 of 100 and **0.938 at 99 of 100**, so
    one case sinks it. As worded, L2 means "no case at all".
- **L2′ (islands > 5 mm from stage-1 foreground) never false-fails.** Correct branches are attached.
- **K1 as ruled counts the junction overlap,** so it measures branch length, not leakage:
  - at ≤ 20 mm it writes `LEAK` for every class in essentially every draw;
  - at 30 mm it writes `LEAK` for four of six classes 61–99 % of the time;
  - it falls below 0.05 only once branches reach about 40 mm.
  - In the `out` model it is 0. A correct model can fail K1, and a leaking model with long branches can pass it.
- **K1′ (L1's statistic on 20 cases, `LEAK` above 0.03) never false-fails.**

### 5.3 What Bridge proposes (for the J1F-2 ruling, not before)

| Number | Ruled | Proposed | Why |
|---|---|---|---|
| **L1** theft | ≤ 0.02 of each parent group's reference centreline, upper bound at 1.25 % | **keep** | A correct junction-painting model takes 1.6–1.7 %. It passes, with little room. Under D47 Q4, a reader who draws wider overlaps teaches more theft, so L1 is the right place for that cost to show |
| **L2** far paint | in ≥ 95 % of cases, no stage-2 voxel > 30 mm from predicted coronary foreground, lower bound at 1.25 % | **L2′: in ≥ 95 of the 100 cases (the point count, not a bound), no stage-2 26-component of ≥ 20 voxels lies wholly more than 5 mm from predicted stage-1 foreground.** The 30 mm distance is reported beside K3 | (1) A straight correct branch longer than ≈ 30 mm crosses the ruled L2's distance in **every** case. (2) Its 1.25 % lower bound needs 100 of 100 (99 → 0.938), so one long septal or one RMA sinks a correct class. L2′ catches what L2 was for, a stage-2 island painted away from the tree: a model with islands in 10 % of cases fails it with probability ≈ 0.94 (binomial, n = 100) |
| **K1** | > 0.05 of a stage-2 class's voxels inside the traced lumen, on the 20 fit-check cases, writes `LEAK` | **K1′: L1's centreline statistic on the 20 fit-check training cases; `LEAK` above 0.03 in any parent group** | The ruled K1 counts the junction overlap that D47 Q4 trains. A correct model with branches ≤ 20 mm writes `LEAK` in essentially every draw (four of six classes 61–99 % at 30 mm), so the PM would be invited to cancel a sound run. K1′ measures the same leak (stage-2 labels on traced vessel) where a branch's own junction barely moves it |
| **L2's 30 mm, if kept as a decision** | — | Re-set with the band: max(30 mm, the 99th percentile of drawn tip-to-host distance in the trainable extended reads) | The same reads that set the band (F-A21) measure how long the branches really are. No number about branch length is assumed here |
| **95 %** | — | as L2′ above | — |

**None of this touches stage 1.** F-A22's numbers are frozen before J1F-2 is submitted (F-A22's last line), and J1F-2
waits on extended reads that do not exist yet.

## 6. Item 6: Q-F2-1 to Q-F2-3, planned for both answers

The lead has not answered. Each branch is written now, so whichever answer comes needs no new round.

### Q-F2-1 (extended reads on the 150 sealed pool patients)

| Answer | Consequence |
|---|---|
| **Yes** (recommended in the ruling) | Nothing in stage 1 changes. Stage 2's S step gains a **report** tier on the seal, scored only at the seal's single acceptance look (A19, D27), never earlier and never deciding. J1F-2's own decision set stays D35. SegQueue's extended mode is turned on for sealed assignments by the PM; no code in 1-F reads them |
| **No** | Nothing in stage 1 changes. SN, Conus and RMA stay counts only until a larger held-out set exists (§7 of the ruling). S1 may still reach D35's report tier |

### Q-F2-2 (Job B, ≈ 22 GPU-h)

| Answer | Consequence |
|---|---|
| **No** (recommended) | F-A23's rule decides when a class trains. Fir's order: a1, a2, then J1F-2 when counts allow |
| **Yes** | J1F-B runs **after J1F-A's verdict and before any extended read trains**, on a 60-case hold-out of the 620, read against F-A15's lines (Bridge v2 §6). It uses no locked case and costs no look. F-A23's 30-patient rule stands until it reports |

### Q-F2-3 (may a released 1-F carry 1-L's vessels?)

**If no:** F-A24 stands. V_L and T_L are reports when 1-L is adopted before `collect`.

**If yes: T_L's verdict rule, inside J1F-A's one look** (it adds a reading, not a look).

**When it applies:** only if Janus 1-L is **adopted** (its own `collect` has run and its DECISION.md says adopted)
**before J1F-A's `collect` starts.**
- Then 1-L's shipped locked-100 maps are copied to Fir as files, by the tar route Step T used, with their sha256 posted
  on #303 before `collect`.
- If 1-L is adopted later, nothing in J1F-A's verdict changes. A swap is round N+1's question.

**The sequence (one-sided 2.5 %, as V):**
1. **V**, as ruled: F against Janus 0.
2. **B** on the reading that would ship, as ruled.
3. **V_L, now deciding:** F against 1-L's maps, by V's own four clauses (lower bound of Δ decisive macro tF1 above
   −0.02, no class mean below −0.03, L3, FP ≤ 1). It is read **only when V and B pass on F**.
4. **What ships:**

| V (F vs Janus 0) | B | V_L (F vs 1-L) | Ships |
|---|---|---|---|
| pass | ≥ 4 of 6 on F | pass | **F** |
| pass | ≥ 4 of 6 on F | fail | **T_L** (1-L's vessels, 1-F's names under F-A19), if B ≥ 4 of 6 on T_L; else F |
| fail | ≥ 4 of 6 on T_L | — | **T_L** |
| fail | < 4 of 6 on T_L, ≥ 4 on T | — | **T** |
| any | < 4 of 6 on every candidate reading | — | not adopted (as ruled) |

**Why this rule:**
- **It never ships vessels worse than the best adopted vessel model.** T_L's four classes are 1-L's map by
  construction (asserted as T's are).
- **It adds no look.** 1-L's maps were already scored by 1-L's own look. T_L is a pre-registered third reading of
  J1F-A's single look, as F and T are.
- **Its multiplicity is a choice between pre-registered readings, not an extra claim.** Each shipped reading passes
  B, and the vessel claim of whatever ships is that of the model whose vessels it carries.

**T_L's B is read on the same locked 100 with the same lines.**
- When 1-L's vessels are wider, a branch's detection can only gain from the 1.5 mm tolerance.
- B's naming is 1-F's own.

## 7. Item 7: Step T and F0-r2

| Result | Consequence |
|---|---|
| **No class-weighted CE** in Janus 0's three training logs; `ce_class_weights.json` absent | The loss stays unweighted DiceCE (L-A20's stop does not fire). Nothing changes |
| **`batch_dice` False** in Janus 0's 3d_fullres plans | Stage 2 keeps leaf-Dice per sample; `leaf_skip` is not needed. The stage-2 trainer still asserts False (F-A21) |
| **`nnUNet_compile` not yet found** on Fir; the repo's icx4 `job_body.sh` says `f`, but that file reached dev after Janus 0 trained | **Pin `nnUNet_compile=f` in every 1-F job's environment**, explicitly. The reasons follow below the table |
| **F0-r2 has not run** | It stays a precondition. `check` re-prints its three lines, and `prep` refuses unless they match (§4) |

**Why pinning `nnUNet_compile=f` settles it:**
- Compilation changes kernels and their numerical noise, not the loss, the optimiser, the schedule or any setting in
  the trainer diff.
- The parent-copy identity check (§4 test 2) runs the network at step 0 and refuses on any territory difference above
  1e-5, so a compiled/uncompiled mismatch that mattered would stop `check`.
- `f` is the setting every icx/atlas job body in the repo uses, and track 1-L's L-A21 reads it the same way.
- If the lead later finds Fir's copy with compile on, that is a report, not a recipe change.

**D50 does not reach 1-F.**
- J1F-A trains and predicts on Fir, where V's baseline (Janus 0's Fir predictions) was made, so no cross-cluster
  identity check is needed.
- If Job 0 runs on Fir under D50, it uses the same account rules as §3.3, and it never touches Dataset 719.

## 8. Item 8: is the plan converged?

| §5 item | Bridge's view |
|---|---|
| 1. Scorer of record | **Settled.** File and hash posted; tests pass; the 620 pieces match the simulated distribution (§2.3) |
| 2. `j1f_gates.json` | **Settled.** Hash posted; the 0.59 / 0.61 test passes |
| 3. J1F-A commands | **Settled** (§3.3), with the first chunk's measured npz size to be posted when it runs |
| 4. Stage-1 spec | **Settled**, with two corrections the ruling should adopt (the ignore value 13; F0-r2 in `check`) |
| 5. Stage-2 numbers | **Not settled, and need not be before J1F-A.** L2 and K1 as ruled fail a correct model; §5.3 proposes replacements. Frozen before J1F-2 |
| 6. Q-F2-1 to Q-F2-3 | **Settled as rules for both answers** (§6). The lead's Q-F2-3 answer must be recorded before J1F-A is submitted, because it changes what J1F-A's one look can ship |
| 7. Step T, F0-r2 | **Step T: settled** (§7). F0-r2: a precondition checked by `check`, not a plan question |
| 8. Converged? | **Stage 1: yes**, on the two conditions in §0. Stage 2: no, by design |

**What would make Bridge say "not converged" for stage 1:**
- the round finds a defect in §4's spec that a self-test cannot catch;
- the lead's Q-F2-3 answer needs a rule other than §6's;
- F0-r2's lines differ (F-A26: stop, and the PM finds which copy differs).

## 9. Proposed amendments

- **B-v3-1.** The scorer of record is `j1f_scorer.py` sha256 `7e6875a3…ff78` (§2). Copied byte-identical except its
  import root, and re-hashed in the issue.
- **B-v3-2.** `configs/janus1/j1f_gates.json` sha256 `16ce8954…1b6b` (§3.1).
- **B-v3-3.** Dataset 719's ignore value is **13**, not 255, and `collect` maps 13 → 255 before scoring (§4, test 7).
  F-A3's rule is unchanged: only the stored value changes.
- **B-v3-4.** J1F-A's command block is §3.3. Predict's chunk is budgeted at 38 GB of npz, and the first chunk's size is
  posted.
- **B-v3-5.** `check` re-prints F0-r2's lines, and `prep` refuses on a difference.
- **B-v3-6.** `nnUNet_compile=f`, pinned (§7).
- **B-v3-7** (for J1F-2's freeze, not now):
  - L2 → L2′ (islands > 5 mm, ≥ 95 of 100 as a point count);
  - K1 → K1′ (centreline theft on the 20 fit-check cases, `LEAK` above 0.03);
  - L1 kept at 0.02 (§5.3).
- **B-v3-8.** If Q-F2-3 is yes, §6's T_L rule enters J1F-A's DECISION.md before submission.

## 10. Evidence and code (`experiments/Bridge/j1f_r3/`)

| File | What |
|---|---|
| `j1f_scorer.py` | The scorer of record (§2) and its self-test |
| `test_scorer_cases.py` → `test_scorer_cases.out` | Delta's 31 checks and Atlas's perturbations on six training cases |
| `run620.py` → `run620_summary.json` | The scorer on the 620: pieces against Atlas's census, the collapse against D25, the identity |
| `configs/j1f_gates.json`, `test_gates.py` | Item 2 |
| `decode_ref.py` → `decode_ref.out` | Reference decode F and T (F-A19), `splits_final.json` (F-A20), the fit-check 20 |
| `npz_size.py` → `npz_size.out` | The predict chunk's disk (§3.2) |
| `stage2_sim.py`, `summarise_stage2.py` → `stage2_summary.json` | Item 5 |
| `README.md` | How to re-run each |

The Experiments note is [[Bridge - The 1-F scorer counts what the gates were simulated on, and two stage-2 lines would fail a correct model]].
