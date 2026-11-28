# janus1f: J1F-A on Fir (track 1-F, stage 1)

This launcher trains Janus 1-F stage 1 (J1F-A) and decides it once on the locked 100.

- Issue: #392. Track: #303.
- Plan: [`vault/Plans/Master plan - Janus 1-F.md`](../../vault/Plans/Master%20plan%20-%20Janus%201-F.md) §5, step 4.
- Spec: Delta v3 §4, as amended by F-A27 to F-A35 ([[Janus 1-F Round 3]], F-A36).
- **The lead runs every job.** Nothing here runs by itself.

## The lead's commands

Run these on `fir.alliancecan.ca`, inside `tmux`:

```sh
module load StdEnv/2023 python/3.11.5
cd $SCRATCH/asclepius && git -C repo fetch origin dev && git -C repo checkout dev && git -C repo pull --ff-only
source $HOME/icx14-venv/bin/activate && pip install --no-deps -e repo        # L-A21: editable
export JANUS0=$HOME/janus0-keep; [ -f $JANUS0/SHA256SUMS ] || export JANUS0=$SCRATCH/janus0_out
(cd $JANUS0 && sha256sum -c SHA256SUMS)                                       # four OK lines
export J1F_WORK=$SCRATCH/janus1f; mkdir -p $J1F_WORK
export J1F_SCORER_SHA256=5221032f3dc086d686b63fa946149a215ac00738a87fd9669d7faa15962b2e5b
export J1F_GATES_SHA256=198b3b158098d846358971ad8a85f22eda7f9a76c00f0e1ee798e15171191406
export JANUS0_COMPILE=f                                                       # the value job 1 gave (F-A33)
L=$SCRATCH/asclepius/repo/trillium/janus1f/janus1f

$L check | tee $J1F_WORK/check.txt    # login node. Post it on #303
$L prep                               # CPU job (def-aso22, 16 cores, 64G, 3:00:00). Run it before ~2026-12-20 (D55 Q-F3-3)
$L status                             # after prep: the plans check and the label counts
J1F_RUN=a1 $L train                   # fold 0: two chained 23:50 GPU links (afterok)
J1F_RUN=a2 $L train                   # fold 1, concurrent, report only (D47 Q8, D55 Q-F3-2)
$L status                             # epoch, s/epoch, step-0 identity, fitcheck.json (150, 300), STALL
J1F_RUN=a1 $L predict                 # afterok: 10 chunks of 10; F, T, G decoded; each chunk's npz deleted
J1F_RUN=a2 $L predict                 # report only
$L collect                            # CPU job: opens the looks ledger first, then V, B and the verdict
```

**Send back on #303:**
- `check.txt`;
- `status` after `prep`, after epoch 20, and after epoch 150 (with `fitcheck.json`);
- chunk 0's `du -sh` (`$J1F_WORK/results/du_a1.txt`);
- `results/DECISION.md`, `results/verdict.json` and `results/looks.json`;
- the `.out` of any job that failed (`$J1F_WORK/logs/`).

Never send a volume, a weight file, or a per-case locked map.

`J1F_DRYRUN=1` writes and prints every job script without loading modules or submitting anything.

## What each mode does and refuses

**Every mode** first runs `sha256sum -c SHA256SUMS` on Janus 0 (F-A34). Every mode except `status` refuses an exported `J1F_SCORER_SHA256` or `J1F_GATES_SHA256` that is not the hash of record.

### `check`

`check` runs on the login node and prints:
- `JANUS0_COMPILE`. It refuses if it is unset or is not `t` or `f` (F-A33).
- The Janus 0 sums.
- The editable install.
- The numpy, scipy, scikit-image, nnU-Net and torch versions.
- **The four pins:**
  - scorer `5221032f…2e5b`;
  - gates `198b3b15…1406`;
  - `labels.py` `5f69b5be…0a4b`;
  - `tf1.py` `24441cf8…5254`.
- Every self-test (`python -m janus1f.selftest`). Each one first fails on a broken fixture.
- The scorer's own tests on its six training fixtures (`lib/test_scorer.py`, F-A28).
- F0-r2's split lines, re-derived from `$SCRATCH/icx4/icx` (Bridge v3 §4).
- Whether the trainer is importable.
- Janus 0's Fir predictions for all 100 locked cases.
- Every SBATCH header.

Any mismatch stops `check`.

### `prep`

`prep` builds `Dataset719_J1F` from **the 620 only**:
- Labels come from the scorer's `stage1_labels`, the one converter (F-A28).
- 255 is written as **13** (F-A29).
- `dataset.json` has `"ignore": 13`.
- Step T's plans are moved with `-tp` equal to `-sp` and checked (L-A21, Step T's sha256, `batch_dice` False).
- Janus 0's fingerprint is placed.
- Then `nnUNetv2_preprocess` runs, and nothing else.

`prep` refuses on any of these:
- the converter counts differ from F0-r2's line (`d3` 47, `d4_to_lad` 2, `other_lcx` 20, `other_nearest` 1, `other_ignore` 8);
- a 255 is left in a label;
- a locked, sealed or unknown id is in `imagesTr`, `labelsTr` or the preprocessed folder;
- a used dataset id;
- a class-weight file;
- an incomplete CT or label set (it prints icx4's fetch steps).

### `train`

The trainer is `nnUNetTrainer_janus1f` (`src/segtrain/nnunet_ext/`):
- It loads Janus 0 by parent copy (`configs/janus1/j1f_parents.json`). Non-head tensors must match bitwise.
- At step 0 it checks the identity: territory sums within 1e-5 and the decode equal to Janus 0's argmax.
- It runs 500 epochs.
- It refuses a locked id in the split, and any val that is not the 20 fit-check cases.
- After epochs 150 and 300 it writes `fitcheck.json`. At epoch 150 it writes `STALL` if D1, OM1, PDA or PLB is below 0.10.
- Its final validation is a no-op.

### `predict`

`predict` links the locked CTs into 10 chunks; no other id is allowed. For each chunk it:
1. refuses with less than 40 GB free;
2. runs `nnUNetv2_predict --save_probabilities --disable_tta`;
3. records `du -sh`;
4. runs `python -m janus1f.decode`, which writes F, T and G with a sha256 marker and deletes the chunk's npz, pkl and argmax export.

It refuses a missing Janus 0 baseline.

### `collect`

1. Checks the four pins.
2. Opens `results/looks.json` **before scoring anything**. A second run refuses.
3. Checks every map against its marker, and rebuilds T from G byte for byte.
4. Runs V on F against Janus 0: the A1c scorer via `experiments/Atlas/r9_score_icx4.py`, one-sided 2.5 %.
5. Runs B on F and T with the scorer of record and `configs/janus1/j1f_gates.json`.
6. Applies the verdict table, including F-A32's T_L rule when it applies.
7. Writes `DECISION.md` and `verdict.json`.

**D55 Q-F3-1:** `collect` waits for Janus 1-L's verdict only if all three hold:
- `J1F_Q_F2_3` is `yes` (the default);
- 1-L is not yet adopted;
- 1-L's `collect` had been submitted when a1's `predict` ended (`J1F_JANUS1L_COLLECT_SUBMITTED=1`).

The wait lasts at most 14 days. To apply F-A32, set `J1F_JANUS1L_ADOPTED=1` and `J1F_JANUS1L_MAPS=<dir>`.

## Data rules (#392)

- Only the 620 D45 training cases are trained on or labelled.
- The locked 100's CTs are only linked for `predict`. Their labels are read only by `collect`.
- No label of the 80 sealed test or 20 quality-0 cases is read; the split guard refuses them everywhere.
- The sealed pool is never read.
- No TotalSegmentator-dataset twin case is read. V's ostia use icx4's in-job aorta masks, as master plan §3 says.

## Files

| File | What |
|---|---|
| `janus1f` | The launcher (six modes) |
| `lib/j1f_scorer.py` | The scorer of record, a byte copy of `experiments/Atlas/j1f_r3/j1f_scorer.py` (F-A28) |
| `lib/test_scorer.py` | Its tests on six training fixtures, a byte copy of Atlas's |
| `lib/janus1f/` | `pins`, `split`, `parents`, `decode`, `plans`, `dataset`, `predict_inputs`, `ledger`, `verdict`, `sbatch`, `collect`, `selftest` |
| `../../configs/janus1/j1f_gates.json` | The gate file of record, a byte copy of `experiments/Judge/j1f_r3/j1f_gates.json` (F-A27) |
| `../../configs/janus1/j1f_parents.json` | The parent-copy rule |
| `../../configs/janus1/split-2026-11.json` | The D45 split, pinned `19b832fe…4dd3` (#306 §1) |

#306's `trillium/janus1l` is not on dev yet. The shared pieces Delta v3 §4 expected to import from it live in `lib/janus1f/`, one module each, so `janus1l` can import them later: the split and seal guards, the plans check, the ledger and the chain.
