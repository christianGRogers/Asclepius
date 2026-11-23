---
tags: [plans, candidate, janus-1f, branches, partial-labels, fir, round3, D44, D45, D47, D49, D50]
author: Atlas
track: 1-F
round: 3
version: 3
updated: 2026-11-23
issue: christianGRogers/Asclepius#303
---

# Atlas v3 (Janus 1-F): the scorer of record is frozen and passes its 35 checks; F-A15 needs two line changes; L2 as written fails a correct branch; T_L needs a name map; stage 1 is converged

## 0. In one paragraph

The plan in force is Delta v2 as amended (F-A1 to F-A26). This candidate does not reopen it. It answers the round-2
ruling's §5 items 1–8 with code and CPU evidence from the D45 training 620 (labels only). Code is in
`experiments/Atlas/j1f_r3/`; the write-up is [[Atlas - Janus 1-F round 3, the scorer of record is frozen, two F-A15 lines move with F-A25's counts, and L2 fails a correct branch]].

**What I found:**
1. **The scorer of record exists and is frozen** (`j1f_scorer.py`, sha256 **`5221032f3dc086d686b63fa946149a215ac00738a87fd9669d7faa15962b2e5b`**).
   - It is round 2's file, with its collapse replaced by an import of SegQueue's `collapse_to_four` (pinned by sha256,
     as `tf1.py` is), and the pooled statistics and gate arithmetic added.
   - **It passes 35 of 35 checks on training cases:** Delta's 30 on Delta's six fixtures; my 5 real-case
     perturbations; and the synthetic self-test.
   - **On the 620,** its reference pieces equal round 2's census piece for piece (620 of 620 cases identical (0 differences in piece count, voxels or length > 0.01 mm)). So F-A15's lines were
     simulated on exactly what it counts.
   - SegQueue's collapse equals D25 on every voxel outside "Other" and 255 (0 voxels in 0 of 620 cases).
2. **F-A15's lines survive the scorer's counts but not F-A25's locked counts.**
   - Re-run with F-A25's counts (97/64/84/40/98/99), the round-2 rule gives three different numbers:
     - **D1 presence 0.93** (frozen: 0.94);
     - **PLB recall 0.90** (frozen: 0.89);
     - **PLB presence 0.95** (frozen: 0.94).
   - With the frozen 0.94, a human-level D1 fails up to **10.3 %** of the time, against the rule's ≈ 5 %.
   - I propose re-freezing those three (§2.1). `j1f_gates.json` carries F-A15 as ruled, with its test, until the judge
     chooses.
3. **Stage 2's L2 ("no voxel more than 30 mm from predicted coronary foreground") false-fails a correct model** if
   the foreground excludes the stage-2 class itself, and is vacuous if it includes it.
   - On the 620, a traced side branch reaches more than 30 mm from its trunk in 189 (LAD), 266 (LCx) and 469 (RCA) of 620 of cases.
   - **Per component it works:** no correctly placed piece starts more than 0.5 mm from the trunk.
   - I propose L2 per component (§2.5).
   - L1 (0.02) and K1 (0.05) hold for an exact model. Their behaviour under a 1–2 voxel width error is in §2.5.
4. **T_L cannot be built from F and T alone.** F-A20 deletes the probabilities chunk by chunk.
   - `decode.py` adds a one-byte **NAMES** map (the three within-territory argmaxes, packed). From it, T and T_L are
     pure functions of files.
   - The Q-F2-3 rule (`verdict.py`) is written for both answers and sits inside J1F-A's one look (§2.6).
5. **Step T settles item 7.**
   - `batch_dice` is False, so stage 2's leaf-Dice stays per sample and `leaf_skip` is not needed.
   - There is no class-weighted CE, so J1F-A's unweighted DiceCE is Janus 0's loss.
   - **`nnUNet_compile`:** the repository answers what Fir's grep has not. `trillium/icx4/lib/job_body.sh` exports
     `nnUNet_compile=f` from the file's first commit (`2de3f2f`, 2026-10-17) and has never changed it. Janus 0's
     checkpoint dates from 2026-10-21. J1F-A pins `f`.

**Converged?** For **stage 1 (J1F-A), yes**, once the judge picks between F-A15 as ruled and my three re-derived lines
(§2.1). Every other stage-1 item is settled here with code, and both Q-F2 answers are written in. **Stage 2 is not
converged**, and need not be: its numbers are frozen before J1F-2 is submitted (F-A22), and L2's definition needs a
ruling (§2.5). Details are in §2.8.

## 1. Inputs, independence, data

**Binding:**
- D45, D46, **D47** (round 1's answers);
- **D49** (track 1-L round 2: Q-R2-2 allows the D60 quality-0 CTs label-free; nothing here uses them);
- **D50** (Job 0 may run on Fir; L0 there is a determinism check only);
- D8, D22, D25, D27/D32, D35, D40 as amended by D47 Q4;
- F-A1 to F-A26.

**Read:**
- the round-2 ruling;
- the 1-F master plan;
- my v2;
- the round-2 holder Delta v2 (§8 for the spec, and its 30-check test from commit `4e49be9`);
- track 1-L's master plan (Step T, Job 0) and its round-2 ruling (L-A21);
- the nnU-Net 2.8.1 wheel's `export_prediction.py` (what `--save_probabilities` writes).

**Independence.**
- I did not open any round-3 candidate of this track, any `* v3.md` under `Candidates/Janus 1-F/`, or any
  `exp/j1f-r3-*` branch.
- I read the repository's `git log` for one file (`job_body.sh`) and Delta's round-2 commit.

**Data (CPU, this container):**
- ImageCAS-X segmentations of the **620 training cases only**, plus `Descriptors.xlsx`, fetched by round 2's
  `fetch_620.py`. Before any read it asserts the 620's pin (`1350cb1f…1152`) and that no member is locked.
- Every script asserts the pin, or membership in the 620, before it opens a label.
- **Not read:**
  - any locked-100, sealed-80 or quality-0 label (the locked-100 numbers used are F-A25's published counts);
  - the sealed pool;
  - any TotalSegmentator twin;
  - any CT;
  - any model output.
- Nothing ran on Fir, SciNet or Trillium.

**Results posted on #302 (Step T), as given to me:**
- Janus 0's 3d_fullres `batch_dice` is False;
- no training log shows class-weighted CE;
- `nnUNet_compile` is still unverified on Fir.

**Not yet run:** F0-r2, Job 0 (track 1-L). The lead has not answered Q-F2-1 to Q-F2-3.

## 2. The eight items

### 2.1 Item 1: the scorer file of record

**The file:** `experiments/Atlas/j1f_r3/j1f_scorer.py`, sha256 **`5221032f…2e5b`** (printed by
`python j1f_scorer.py selftest`).

**What changed from round 2's `2da3cb1a…886c`. Nothing else moved:**

| | Round 2 | Round 3 |
|---|---|---|
| Collapse | its own one-voxel-ring rule | **`segqueue14.labels.collapse_to_four`**, imported, with `labels.py` pinned at import (`5f69b5be…0a4b`, F-A17). It runs on the map's foreground box; `collapse4(…, stats)` returns SegQueue's counts (components, fallback), which `collect` reports for F, T and T_L |
| Pooling and gate | none | `aggregate` (pooled per-piece recall and naming, per-case presence agreement, as exact fractions) and `gate` (each line inclusive, against `j1f_gates.json`; "≥ 4 of 6") |
| Self-test | the toy | plus three F-A17 cases (see the list below), and the gate arithmetic |

The three F-A17 cases added to the self-test:
- **chain:** a left PLB reached only through its PDA goes to the LCx;
- **fallback:** an unattached PDA falls back to the RCA and is counted;
- **diagonal join:** a PLB joined to the RCA only diagonally falls back to the RCA and is counted.

**One behaviour to know.** SegQueue counts contact by **shared faces**, so a branch joined to its parent only along a
diagonal counts as unattached. It is still sent to the RCA, and counted as a fallback.
- It cost nothing on the references: 0 fallbacks in 1,296 (1,203 to the RCA, 93 to the LCx) PDA/PLB components on the 620.
- On predictions, `collect` prints the fallback count beside F and T, as F-A17 already requires.

**Its tests, on training fixtures only (`test_scorer.py` → `test_scorer.log`): 35 of 35 pass.**
- **Part A, Delta's test (30 checks), ported unchanged** in cases, perturbations and assertions:
  - c0585, c0875, c0987, c0287, c0920, c0761, chosen by sha256(`asclepius-j1f-r2-scorertest:` + id);
  - SegQueue's collapse = D25 outside "Other" (6 of 6);
  - identity → recall, presence and naming 1 and branch tF1 1, for all six gated classes;
  - a one-voxel grey dilation → recall 1, naming 1;
  - D1/D2 swapped and PDA/PLB swapped → detected, misnamed;
  - OM2 drawn as LCx → detected, misnamed, agreement < 1;
  - OM2 removed → recall 0.
  - (Delta's log has 31 lines: the 31st is "ALL PASS".)
- **Part B, my round-2 real-case checks as assertions** (c0217):
  - identity;
  - D1/D2 swapped;
  - OM folded into the LCx (detected, misnamed, presence lost);
  - PLB removed (missed);
  - PDA kept to 40 % of its length (missed).
- **Part C:** the synthetic self-test.

**The 620 (`check_620.py` → `check_620.jsonl`, `summarise_620.py` → `summary_620.json`):**

| Check | Result |
|---|---|
| SegQueue's collapse vs D25, outside "Other" and 255 | 0 voxels in 0 of 620 cases |
| The same, inside "Other" | 40 voxels in 2 cases (round 2's ring disagreed on 40 "Other" voxels in 2 cases; "Other" has no D25 class of its own, so these are not errors) |
| PDA/PLB components; SegQueue fallbacks | 1,296 (1,203 to the RCA, 93 to the LCx); 0 |
| F-A18's expected line `{d3 47, d4_to_lad 2, other_lcx 20, other_nearest 1, other_ignore 8}` | equal: `{d3 47, d4_to_lad 2, other_lcx 20, other_nearest 1, other_ignore 8}` |
| Reference pieces vs round 2's `census_r2.jsonl` (count, voxels, length per piece) | 620 of 620 cases identical (0 differences in piece count, voxels or length > 0.01 mm) |
| Cases with each class present at 5 mm (D1, D2, D3, OM1, OM2, Ramus, PDA, PLB) | 611 / 358 / 47 / 540 / 228 / 149 / 607 / 609 (round 2's census exactly) |

**So the piece distribution F-A15 was simulated on is the scorer's own.** The ruling's §7 trigger ("the amended
scorer's per-piece counts differ") does not fire.

**But F-A25's locked counts move three lines** (`gate_refreeze.py` → `gate_refreeze.json`). I re-ran round 2's
simulation unchanged, with two inputs swapped:
- the pieces from this round's scorer;
- the locked counts of record (F-A25: D1 97, D2 64, OM1 84, OM2 40, PDA 98, PLB 99, against round 1's
  98/64/84/40/96/96).

| | Lines by the rule (5th percentile, worst scenario, round down) | Human-level false-fail of the frozen F-A15 lines, worst of 9 | of the re-derived lines | P(reject): omission +0.10 / misnaming 0.10 / 0.20, frozen → re-derived |
|---|---|---|---|---|
| Round-1 counts | **= F-A15** | worst class 7.1 %, verdict 0.3 % | — | 99.7 / 57.7 / 99.9 % |
| **F-A25 counts** | **D1 presence 0.93; PLB recall 0.90, presence 0.95**; the other 15 unchanged | **D1 10.3 %**; others ≤ 7.1 %; verdict 0.35 % | D1 5.7 %, PLB 5.2 %; all ≤ 7.1 %; verdict 0.4 % | 99.9 / 58.7 / 99.95 % → 99.9 / 57.2 / 99.95 % |

- **D1 has one fewer locked case with a D1** (97). The human 5th percentile of presence agreement drops by one case,
  and 0.94 then fails a human-level D1 up to 10.3 % of the time.
- **PLB has three more cases** (99). Its 5th percentiles rise, and the rule tightens it, which F-A6 allows before
  submission.
- **F-A25 called these differences "within the rounding of the lines".** For D1's presence line they are not: it is a
  binomial line at n ≈ 100, where one case is one point.

**Proposed (P-r3-1):** re-freeze those three lines by F-A15's own rule at F-A25's counts:
- D1 presence **0.93**;
- PLB recall **0.90**;
- PLB presence **0.95**.

The rest stay as ruled. If the judge prefers to keep F-A15 exactly, the cost is a D1 false-fail of ≈ 10 % instead of
≈ 5 %. That is still under the ruling's 20 % line, so either choice is defensible. The point of a rule is to apply it to
the counts of record.

### 2.2 Item 2: `configs/janus1/j1f_gates.json` and its test

- **The file** is `experiments/Atlas/j1f_r3/j1f_gates.json`, sha256
  **`c14190cb4b796a895cae37207b5968f28b7be0d6f40b1fa3f0fbd68dc0d9db68`**. It holds F-A15 exactly, with `k_of_6: 4`.
  - The swe copies it byte for byte to `configs/janus1/j1f_gates.json` (a config that ships goes through the swe issue,
    not my PR).
  - If P-r3-1 is adopted, the three numbers change, and the file and its hash are re-posted before J1F-A is submitted.
- **`test_gates.py`:**
  - the file equals F-A15's table;
  - every class exactly on its lines passes (6 of 6), because the lines are inclusive and compared as exact fractions;
  - **OM2 recall 59/100 fails, 60/100 passes, 61/100 passes**;
  - OM2 failing alone still gives 5 of 6, a pass;
  - with D2's naming and PLB's presence also failing, it is 3 of 6, so "not adopted";
  - a class with no detected piece fails.
  - Output: `test_gates ok`.

### 2.3 Item 3: the J1F-A command block, with a disk estimate

**Disk** (`npz_size.py`, one training case, c0099, 512 × 512 × 206; `summary_620.json` for the 620's grids):
- nnU-Net 2.8.1 writes `np.savez_compressed(…, probabilities=…)` at the original grid, 13 channels.
- **Uncompressed ceiling:** C × voxels × bytes. The median 620 grid is 72.1 M (512 × 512 × 275, the grid of 384 of the 620 and also the largest; smallest 43.5 M) voxels, so **3.75 GB per case in
  float32** (1.87 GB in float16). The largest is **3.75 GB**.
- **Measured on c0099 with a network-like synthetic softmax:** float32 **2.34 GB** (83 % of its 2.81 GB uncompressed, 96 s to write); float16 0.027 GB, because the far-field probabilities underflow to 0 in half precision. So a float32 npz barely compresses and the ceiling is the right planning number.
- **Peak disk for one chunk of 10, at the 620's largest grid: 37.5 (float32; 18.7 in float16) GB**, against 375 GB for all 100 at the
  median grid (F-A20's chunking is what keeps it under ≈ 0.1 TB).
- Fir's `$SCRATCH` quota is 19 TiB (the compute-inventory note), so either fits. Chunking also bounds the time a
  locked-100 probability file exists.

**The block.** These are the lead's commands, for `trillium/janus1f` as specified in §2.4. The swe issue writes the
code; the commands do not change.

```sh
# Fir login node (fir.alliancecan.ca), inside tmux
module load StdEnv/2023 python/3.11.5
cd $SCRATCH/asclepius && git -C repo fetch origin dev && git -C repo checkout dev && git -C repo pull --ff-only
source $HOME/icx14-venv/bin/activate
pip install --no-deps -e repo                       # L-A21: editable, so the sealed lists resolve
export JANUS0=$SCRATCH/janus0_out
[ -f $JANUS0/SHA256SUMS ] || export JANUS0=~/projects/def-aso22/$USER/janus0   # Step T's $KEEP copy
(cd $JANUS0 && sha256sum -c SHA256SUMS) || { echo "STOP: Janus 0 copy differs"; exit 1; }
export J1F_WORK=$SCRATCH/janus1f
rm -rf $SCRATCH/janus1f_code && cp -r repo/trillium/janus1f $SCRATCH/janus1f_code && cd $SCRATCH/janus1f_code

./janus1f check            # self-tests + dry run (no job); post the whole printout on #303. Stop on any FAIL.
./janus1f prep             # one CPU job: dataset 719, labels, plans moved, preprocess. Prints its job id.
./janus1f status           # repeat until "prep DONE"
J1F_RUN=a1 ./janus1f train # chains 2 GPU jobs, then predict (afterok)
J1F_RUN=a2 ./janus1f train # D47 Q8: concurrent, fold 1, report only
./janus1f status           # s/epoch; after epoch 150 it shows fitcheck.json (STALL / LEAK lines, if any)
./janus1f collect          # one CPU job after a1's predict; refuses a second run (looks ledger)
```

**The SBATCH headers the dry run prints, and the launcher writes:**

| Job | Header |
|---|---|
| prep (CPU) | `--account=def-aso22 --cpus-per-task=16 --mem=64G --time=4:00:00` |
| train, each link (GPU) | `--account=def-aso22_gpu --gpus-per-node=h100:1 --cpus-per-task=12 --mem=280G --time=23:50:00` |
| predict (GPU) | `--account=def-aso22_gpu --gpus-per-node=h100:1 --cpus-per-task=12 --mem=280G --time=8:00:00` |
| collect (CPU) | `--account=def-aso22 --cpus-per-task=16 --mem=64G --time=6:00:00` |

- **The GPU account changes.** The master plan's "Fir, `def-aso22`" is corrected to `def-aso22_gpu` for GPU jobs, with
  explicit cores and memory. Fir's bundle is 12 cores / 280 GB per H100 (compute-inventory note).
- **Inside `predict`** (per run, F-A20 with the NAMES map):

```sh
for k in 0 1 2 3 4 5 6 7 8 9; do                    # chunks of 10 locked ids, in sorted order
  nnUNetv2_predict -i $J1F_WORK/chunks/$k -o $J1F_WORK/pred_$RUN/raw_$k -d 719 -c 3d_fullres \
    -tr nnUNetTrainer_janus1f -p nnUNetResEncUNetPlans_60G_iso05 -f $FOLD -chk checkpoint_final.pth \
    --save_probabilities --disable_tta -npp 3 -nps 3
  python lib/decode.py write $J1F_WORK/pred_$RUN/raw_$k $JANUS0/pred_fir $J1F_WORK/pred_$RUN/maps
  # writes <id>_F.nii.gz, <id>_NAMES.nii.gz, <id>_T.nii.gz (uint8, the npz's grid and affine) and
  # <id>.decoded.json {sha256 of decode.py, of the npz, of the three maps}
  rm -f $J1F_WORK/pred_$RUN/raw_$k/*.npz $J1F_WORK/pred_$RUN/raw_$k/*.pkl $J1F_WORK/pred_$RUN/raw_$k/*.nii.gz
done
```

- **`collect` reads only maps with a `.decoded.json` marker.**
  - It rebuilds T from NAMES and Janus 0's map, and checks it against `predict`'s T byte for byte.
  - It builds T_L only if `$JANUS1L_MAPS` is set, and only under §2.6's conditions.

**Send back on #303:**
- `check`'s printout;
- `status` after 20 epochs and after epoch 150, with `fitcheck.json`;
- `results/DECISION.md` and `results/verdict.json`;
- the `.out` of any failed job.

Never a volume, never a weight file.

### 2.4 Item 4: the converged stage-1 spec, as one diff against `janus1l` (L-A21)

**Shared, imported from `trillium/janus1l/lib/`, not copied:**
- the editable install;
- the split guard and both seal guards;
- Step T's plans copy, `move_plans_between_datasets`, the L-A21 plans check (equal once `dataset_name` and
  `image_reader_writer` are removed; a changed percentile refuses);
- Janus 0's fingerprint placed, and no `plan_experiment` or `extract_fingerprint`;
- the chain logic;
- `SEGTRAIN_SAVE_EVERY=10`, `SEGTRAIN_MAX_SECONDS` = walltime − 30 min, `SEGTRAIN_ITERATIONS`/`SEGTRAIN_EPOCHS`
  unset;
- `checkpoint_best` never read;
- the looks ledger;
- `status`.

**The diff:**

| Item | `janus1l` (L-A21) | `janus1f` |
|---|---|---|
| Cluster, header | Trillium | **Fir**, §2.3's headers (`def-aso22_gpu` for GPU) |
| Dataset | 718, `territory.to_four` | **719**, `j1f_scorer.stage1_labels` (13 values + 255), the same function `collect` uses for the locked-100 references. `check` prints its 620 line; `prep` refuses unless it equals `{d3 47, d4_to_lad 2, other_lcx 20, other_nearest 1, other_ignore 8}` (F-A18; F0-r2 is the independent copy on Fir) |
| `nnUNet_compile` | "as Janus 0's" | **`f`**, pinned (§2.7) |
| Val | 10 lowest-id tuning-60 cases | **the 20 fit-check training cases** (F-A5, F-A20); two identical entries, a1 = fold 0, a2 = fold 1 |
| Trainer | `nnUNetTrainer_janus1l` (final validation a no-op) | `nnUNetTrainer_janus1f`, the same plus: (i) a parent-copy load of every `seg_layers` head from `configs/janus1/j1f_parents.json`; (ii) the step-0 identity; (iii) the fit check at epochs 150 and 300 (`fitcheck.json`, `STALL` per F-A5) |
| Epochs | 250 | 500 (2 links) |
| Threshold | t_C (L-A15), `transfer` | **none** (argmax, F-A6); no `transfer` mode |
| Predict | folds 0, 1 on the locked 100 and D60; E by `nnUNetv2_ensemble` | a1 (then a2) on the locked 100 only, in chunks of 10, `--save_probabilities --disable_tta`; **`decode.py write`** → F, NAMES, T, marker; then delete the npz, pkl and nnU-Net's own argmax (§2.3). No ensemble (a2 is never ensembled, D47 Q8) |
| Collect | H1 → H2 → H3 | **V → B, then the verdict of `verdict.py`** (F, T; T_L under §2.6). The branch scorer and gates are refused unless their sha256 equal the posted values (`5221032f…`, `c14190cb…` or its P-r3-1 successor). Reports: F-A9, fallback counts, T's collapse-vs-territory voxel count, V_L/T_L as §2.6 says |

**Self-tests (`./janus1f check`), each failing on a broken fixture first:**
1. L-A21's 1–4, 6 and 9 (the V part), unchanged. Its 5 (t) and 7–8 (ensemble) do not apply.
2. **Parent copy** (`decode.py`, test 2): territory sums equal Janus 0's softmax within 1e-5, and F's territory equals
   Janus 0's argmax on every voxel. Fixture: one head row not copied, which must fail.
3. **Hierarchical decode** (`decode.py`, test 1): F's territory is the argmax of the summed probabilities. A plain
   13-way argmax moves ≈ 10 % of voxels across territories on random logits (tripwire > 1 %).
4. **F-A19's T test** (`decode.py`, test 3): a left PDA inside Janus 0's LCx territory is named PDA by T, and T's
   territory is Janus 0's map bit for bit.
5. **NAMES:** compose(Janus 0, NAMES) equals the direct within-territory argmax from probabilities (`decode.py`,
   test 4), and a corrupt NAMES map refuses.
6. **F-A20's val test:** no locked id in `splits_final.json`, and val ⊂ the 620 equals F-A5's fit-check list. Fixture:
   one locked id in val, which must refuse.
7. **The scorer:** `test_scorer.py` (35 checks) and `test_gates.py`.
8. **The verdict:** `verdict.py selftest`, both Q-F2-3 answers (§2.6).
9. **Labels:** `stage1_labels` + SegQueue's collapse equals `territory.to_four` outside "Other" and 255, on Delta's six
   cases. Fixture: one L-PDA voxel written as RCA, which must fail.
10. **The locked 100 is never scored before `collect`:** no `summary.json` for any fold after `train`, and
    `perform_actual_validation` is a no-op.

**Refusals:**
- everything in Delta v2 §8.6, except "plans byte-identical", which L-A21's check replaces;
- a scorer, gates, `labels.py` or `decode.py` hash mismatch;
- a missing Janus 0 Fir prediction for any locked case (never re-predicted silently);
- `$JANUS1L_MAPS` set but incomplete (fewer than 100 maps, or a map's grid differs from Janus 0's);
- `nnUNet_compile` set to anything but `f` in the job environment.

### 2.5 Item 5: F-A22's stage-2 numbers, with their false-fail on the 620

**The difficulty.** ImageCAS-X has none of the six stage-2 classes. "A reference treated as a prediction" therefore
scores 0 on L1 and K1 and passes L2 trivially, whatever the lines. That measures nothing.

**What I measured instead** (`check_620.py`): each host's **traced** side branches play its stage-2 class, because they
are branches of the same calibre leaving the same trunk.
- The LAD's D1–D3 stand in for S1–S3.
- The LCx's OM1, OM2 and Ramus stand in for an SN off the circumflex.
- The RCA's PDA and PLB (where SegQueue sends them to the RCA) stand in for SN, conus and RMA.
- The model paints them exactly (k = 0), or one or two voxels too wide (k = 1, 2), the width spread a human-level model
  has (Table 1 DSC ≈ 0.8).
- Rates are over 10 000 random 100-case draws from the 620 (20-case draws for K1, the fit-check size).

| Number | As ruled | k = 0 (exact) | k = 1 | k = 2 | Proposal |
|---|---|---|---|---|---|
| **L1** theft share, pooled (LAD / LCx / RCA) | ≤ 0.02 (one-sided 1.25 %) | 0 / 0 / 0 | 0.0058 / 0.0078 / 0.0056 | 0.0168 / **0.0210** / 0.0104 | keep 0.02 |
| P(L1 fails) on a 100-case draw, point / upper bound | | 0 / 0 | 0 / 0 on every host | LCx 0.78 / 1.00; LAD 0.0002 / 0.11; RCA 0 / 0 | |
| **K1** in-lumen share, 20 cases (LAD / LCx / RCA) | ≤ 0.05 | 0 / 0 / 0 | 0.012 / 0.012 / 0.005 (p95 of draws ≤ 0.015) | 0.017 / 0.016 / 0.006 (p95 ≤ 0.020) | keep 0.05 |
| P(K1 writes LEAK) | | 0 | 0 | 0 | |
| **L2 per voxel**, class excluded from the foreground: cases with a piece > 30 mm (LAD / LCx / RCA) | ≥ 95 % of cases clean | 189 / 266 / 469 of 620 | | | **fails a correct model**: P(fail) = 1.00 on every host |
| **L2 per component**: cases with a piece starting > 30 mm from the trunk | | 0 / 0 / 0 | | | P(fail) = 0 |

**L2, as written, is ambiguous, and both readings are wrong:**
- **If "predicted coronary foreground" includes the stage-2 class itself,** every voxel of a connected branch is at
  0 mm. L2 catches only a detached blob. That was its intent, but by accident of definition.
- **If it excludes the class** (the only reading under which the 30 mm number means anything), a correct branch fails
  whenever it runs more than 30 mm from its trunk.
  - The 620's side branches: piece max distance p50/p90/p95 = LAD 19.9 / 35.4 / 39.8 mm, LCx 21.5 / 46.3 / 50.8 mm, RCA 39.5 / 51.0 / 55.0 mm (max 67.2 mm).
  - A real RMA runs along the acute margin and a septal deep into the septum, so the real classes are no shorter.
- **Proposed (P-r3-2): L2 per 26-component.**
  - In ≥ 95 % of locked cases, no stage-2 component of ≥ 20 voxels has its **nearest** voxel more than 30 mm from the
    stage-1 foreground (LM and the trunks with their stage-1 branches).
  - On the 620 a correctly placed piece's nearest voxel is at 0.5 mm at most, so a correct model passes
    (P(fail) = 0). A blob painted in the atrium or the myocardium, which is what L2 is for, does not.

**L1 and K1:** both keep their numbers. An exact or one-voxel-wide model passes L1 in every 100-case draw (pooled theft ≤ 0.008, 95th percentile of draws ≤ 0.009) and K1 in every 20-case draw (≤ 0.015). L1 fires on a model two voxels too wide on the LCx (0.021; P(fail) 0.78 at the point, 1.00 at the bound), so 0.02 also catches gross over-painting at junctions, which the gate should see. K1 does not fire even at k = 2 (≤ 0.020), so 0.05 has room for real origins. These are surrogate rates: the real classes are untraced, so the first extended reads should re-check them before J1F-2, as they re-set the band.

**The 95 % in L2, and the one-sided 1.25 %:** kept, because the null above is far from both lines.

### 2.6 Item 6: Q-F2-1 to Q-F2-3, planned for both answers

**Q-F2-1 (the sealed pool in extended mode).**

| Answer | Consequence for 1-F |
|---|---|
| **Yes** (recommended in round 2) | The 150 sealed pool patients are read in extended mode. Their extended classes are scored **once, inside D27's single acceptance look, as a report** (branch counts and, where ≥ 20 patients, recall and naming with the scorer of record, after D47's collapse for the four-class read). Never earlier, never deciding stage 2, never training. Nothing in J1F-A or J1F-2 changes |
| **No** | SN, Conus and RMA stay counts only until a larger held-out set exists (ruling §7). S1–S3 are decided on D35's tiers as F-A22 says. Nothing in J1F-A changes |

**Q-F2-2 (Job B, ≈ 22 GPU-h).**

| Answer | Consequence |
|---|---|
| **No** (recommended) | F-A23's rule. A J1F-2 class trained too early costs one ≈ 15 GPU-h run and is caught by F-A22 |
| **Yes** | Job B runs on Fir after a1's `collect` (never before: it must not delay a1/a2). It uses a 60-case hold-out **of the 620** and never touches the locked 100, so it costs no look. Its spec is written by the round after the answer; nothing in J1F-A changes |

**Q-F2-3 (may a released 1-F carry Janus 1-L's vessels?).** The rule is written now (`verdict.py`, self-tested). It
applies only if the answer is yes **and** Janus 1-L is adopted, with its locked-100 maps copied to Fir, before 1-F's
`collect` starts.

1. If V and B pass on F, and **V_L** passes (F's collapsed vessels are non-inferior to 1-L's by V's own rule), ship
   **F**.
2. If V and B pass on F but V_L fails, ship **T_L** if B passes on T_L; otherwise ship F.
3. If V or B fails on F, ship **T_L** if B passes on T_L; otherwise T if B passes on T; otherwise not adopted.

Conditions around the rule:
- **When V_L is tested.** Only after V and B have passed on F (a fixed sequence), at one-sided 2.5 %. It decides
  whose vessels ship, never whether a branch model is adopted.
- **T_L needs no V.** Its four classes are 1-L's adopted map, which passed 1-L's own guard against Janus 0.
- **Inside the first look.** T_L is a third reading of the same predictions, so it costs no new look on the locked 100.
- **The name map.** T_L = compose(1-L's map, NAMES). NAMES is why T_L can be built after `predict` has deleted the
  probabilities. Without it, T_L would need a re-prediction (a second inference of the locked 100).

**If the answer is no or unanswered,** or 1-L is not adopted before `collect`:
- the verdict is as ruled (F, else T, else not adopted);
- V_L and T_L are reports, when 1-L is adopted.

**If 1-L is adopted only after `collect`:** T_L can still be composed from the NAMES files. It is then a report, like
a2, and never ships. Making it shippable would be a new look.

**1-L's maps on Fir.**
- They are 1-L's exported E, at t_C, as uint8 four-class NIfTI files, copied from Trillium with their sha256 list.
- `collect` refuses them unless all 100 are present on Janus 0's grid.
- No 1-L inference runs on Fir. D50's Fir exception was for Job 0 only.

### 2.7 Item 7: Step T's results and what they settle; F0-r2 and Job 0

| Result (#302) | Consequence |
|---|---|
| Janus 0's 3d_fullres `batch_dice` **False** | F-A21 stands: stage 2's leaf-Dice per sample, `batch_dice: false` asserted. **`leaf_skip` is not needed** |
| **No class-weighted CE** in any training log | J1F-A's unweighted DiceCE (F-A2) **is** Janus 0's loss. No loss re-decision (the L-A20 branch does not fire) |
| `nnUNet_compile` **unverified** on Fir | The repository settles it. `trillium/icx4/lib/job_body.sh` exports `nnUNet_def_n_proc=8 nnUNet_compile=f`; `git log -S nnUNet_compile` shows only the file's first commit (`2de3f2f`, 2026-10-17, "Four classes again … (D25)"). That is before Janus 0's checkpoint (2026-10-21), so every icx4 job that trained Janus 0 ran it eager. **J1F-A pins `nnUNet_compile=f`** and `check` refuses anything else. The Fir grep in Step T stays useful as a cross-check, and its absence blocks nothing: V compares against Janus 0's prediction files, not a re-run, so compile mode cannot move the baseline |
| **F0-r2 not run** | It stays a precondition. `check` prints the same line from `stage1_labels` on Fir's copy, and `prep` refuses unless it matches. Any difference in F0-r2's pins or counts: stop (ruling §7) |
| **Job 0 not run** (track 1-L) | Nothing in 1-F waits on it: 1-F decodes at argmax and has no t\*. Under D50, if Job 0 runs on Fir, its probabilities are 1-L's. 1-F's T and V still read Step T's `pred_fir` copy, never a re-prediction |

### 2.8 Item 8: is the plan converged?

**Settled by this round** (I would not reopen any of them):

| §5 item | State |
|---|---|
| 1. Scorer of record | **Settled.** `5221032f…`, 35/35 on training fixtures, pieces = census_r2 on the 620. Open only on the D1/PLB line choice, which is item 1's sub-point P-r3-1 |
| 2. `j1f_gates.json` | **Settled** for F-A15 as ruled (`c14190cb…`). It changes only if P-r3-1 is adopted |
| 3. Command block | **Settled** (§2.3), with the GPU account corrected to `def-aso22_gpu` |
| 4. Stage-1 spec | **Settled** (§2.4). The swe issue can be filed after this round's ruling |
| 6. Q-F2-1 to Q-F2-3 | **Settled as rules for both answers.** The lead's answers choose the branch; no round is needed after them |
| 7. Step T | **Settled**: no loss change, no `leaf_skip`, `nnUNet_compile=f` |

**Not settled:**

| Item | What is left | Blocks J1F-A? |
|---|---|---|
| 1 (P-r3-1) | F-A15 as ruled, or re-derived at F-A25's counts (D1 presence 0.93, PLB 0.90 / 0.95) | **Yes, until the judge picks.** It is one number in a JSON file either way |
| 5. Stage 2's numbers | L2's definition (P-r3-2); L1/K1 width tolerance | No: frozen before J1F-2, never after (F-A22) |
| F0-r2 | Not run | No, but `prep` refuses until its line matches |

**My view:** the ruling can declare **stage 1 converged** in round 3 and file the `role:swe` issue (F-A12). Stage 2 is
converged in shape and stays provisional in its numbers until J1F-2, as F-A22 already allows.

## 3. Proposed amendments

| # | What | Replaces |
|---|---|---|
| **P-r3-1** | Re-derive F-A15 at F-A25's counts by its own rule: D1 presence 0.93, PLB recall 0.90, PLB presence 0.95 | three cells of F-A15 |
| **P-r3-2** | L2 per 26-component (nearest voxel > 30 mm), not per voxel | F-A22 L2's wording |
| **P-r3-3** | `decode.py`: F + **NAMES** + T per case; T_L = compose(1-L, NAMES); `collect` re-derives T from NAMES | F-A20's "decode writes F and T" |
| **P-r3-4** | Q-F2-3's rule as `verdict.py` (inside J1F-A's look; only if 1-L is adopted before `collect`) | F-A24's "round 3 writes the rule" |
| **P-r3-5** | `nnUNet_compile=f`, pinned, from the repository's history | "as Janus 0's" |
| **P-r3-6** | GPU headers `--account=def-aso22_gpu --gpus-per-node=h100:1 --cpus-per-task=12 --mem=280G` | the master plan's `def-aso22` for J1F-A |
| **P-r3-7** | The scorer of record `5221032f…`, its tests `test_scorer.py` + `test_gates.py`, the gates file `c14190cb…` (or its P-r3-1 successor) | F-A16's "hash posted by round 3" |

## 4. Cost

| Job | GPU-h | Change |
|---|---|---|
| F0-r2 | 0 | — |
| J1F-A a1 (incl. predict ≈ 1–2) | ≈ 30–32 (ceiling 47.7) | none |
| a2 (D47 Q8) | ≈ 30 | none |
| collect | 0 (≈ 4 h on 16 cores: three readings × 100 × ≈ 110 s, plus V) | — |
| J1F-B | 0, or ≈ 22 if Q-F2-2 is yes | — |
| J1F-2 | ≈ 15, when F-A23's counts are met | — |

## 5. What would change this plan

| Observation | Then |
|---|---|
| F0-r2's line differs from `stage1_labels`' 620 line | Stop. The PM finds which copy differs |
| The Fir grep shows `nnUNet_compile` other than `f` in the job body that trained Janus 0 | P-r3-5 is re-set to that value. V is unaffected (files) |
| 1-L's locked-100 maps arrive on a different grid or are incomplete | T_L and V_L are not computed; the verdict is as ruled |
| A real npz of a 13-channel prediction is larger than this estimate | The chunk size drops from 10 to 5. Nothing else changes |
| The first extended reads put a stage-2 class's components > 30 mm from the tree in > 5 % of reads | L2's 30 mm is re-set from those reads before J1F-2, as the band is |

## 6. Evidence

| Claim | Evidence (`experiments/Atlas/j1f_r3/`) |
|---|---|
| Scorer hash, collapse import, gate arithmetic | `j1f_scorer.py`, `python j1f_scorer.py selftest` |
| 35/35 checks on training fixtures | `test_scorer.py` → `test_scorer.log` |
| Collapse = D25, pieces = census_r2, 'Other' line, stage-2 null, grid sizes | `check_620.py` → `check_620.jsonl`; `summarise_620.py` → `summary_620.json` |
| F-A15 at F-A25's counts | `gate_refreeze.py` → `gate_refreeze.json`, `gate_refreeze.out` (round 2's `gate_sim.py`, unchanged) |
| Gates file and its test | `j1f_gates.json`, `test_gates.py` → `test_gates.out` |
| Decode, NAMES, T, T_L | `decode.py selftest` |
| Q-F2-3 rule | `verdict.py selftest` |
| npz size | `npz_size.py` → `npz_size.out` |
| `nnUNet_compile=f` | `trillium/icx4/lib/job_body.sh` l. 38; `git log -S nnUNet_compile -- trillium/icx4/lib/job_body.sh` → `2de3f2f` (2026-10-17) only |
| nnU-Net's npz | nnunetv2 2.8.1 wheel, `inference/export_prediction.py` l. 100 |
