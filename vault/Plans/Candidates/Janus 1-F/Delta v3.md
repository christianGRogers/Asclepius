---
tags: [plans, candidate, janus1-F, track-1F, round3, fir, D44, D45, D47, D49, D50, locked100, partial-labels, gates, scorer, swe-spec, convergence]
author: Delta
track: 1-F
round: 3
version: 3
updated: 2026-11-23
issue: christianGRogers/Asclepius#303
---

# Delta v3 (Janus 1-F): the scorer, the gate file and the stage-1 spec are frozen as tested code; three of F-A22's stage-2 lines measure the wrong thing and are re-defined, with their numbers kept; the plan is converged except for the lead's three answers, whose consequences are written for both outcomes

## 0. Position and what changed

**I hold the track's plan** ([[Master plan - Janus 1-F]]: Delta v2 as amended by F-A1 to F-A26). This version answers
every item of [[Janus 1-F Round 2]] §5. Where the ruling settled a point, I implement it and do not argue it again.
Where a measurement below shows a settled number misbehaving, I say so and propose the smallest change (§11).

**Facts in since round 2:**
- **Step T is done** (#302, 2026-11-23). For this track it posts:
  - Janus 0's 3d_fullres plans have **`batch_dice: False`**;
  - **no training log shows class-weighted CE** (0 in each of the three logs), and `ce_class_weights.json` is absent;
  - the SHA256SUMS of the checkpoint (`a0fb75de…3ca43`), `plans.json` (`b7178bbc…3cc2`), `dataset_fingerprint.json`
    (`e41c772f…7e05`) and `lists.json` (`7ecc464b…fd56`);
  - Fir's locked-100 predictions: 100 of 100;
  - the purge-safe copy is in the lead's Fir home (`$HOME/janus0-keep`), since `~/projects/def-aso22` does not exist;
  - **`nnUNet_compile` is not confirmed** from Fir's own copy of icx4's `job_body.sh`.
- **F0-r2 has not run.** Job 0 (track 1-L) is queued and has not run. It does not touch this track (§7.3).
- **The lead has not answered Q-F2-1 to Q-F2-3.** §6 writes the plan for each answer.
- **D49 and D50** are in force. Neither changes a 1-F term (§7.3).

**New evidence this round** (CPU; code in `experiments/Delta/j1f_r3/`; note:
[[Delta - Janus 1-F round 3, the scorer and gates are frozen as tested code, and three of F-A22's stage-2 lines fail a correct model]]):
1. **The scorer of record exists and has a hash** (§1): `j1f_scorer.py`, sha256 **`d615c7e7…d808`**. 37 of 37
   checks pass on six training cases. Its reference pieces equal the pieces F-A15 was simulated on, case by case,
   on all 620 (§1.3).
2. **The gate file exists and has a hash** (§2): `j1f_gates.json`, sha256 **`09ddb06f…fc5f`**, with the OM2
   0.59 / 0.61 test.
3. **The converter of record, amended** (F-A18), reproduces the expected line on all 620 (§1.4).
4. **The stage-1 spec as one diff against `janus1l`** (§4), with reference code for every 1-F-specific test:
   decode F, decode T (F-A19's left-PDA test), parent copy, `splits_final` (F-A20's no-locked-id test), the chunked
   decode loop and `collect`'s marker check, and the plans check pinned to Step T's hashes.
5. **Two spec defects found in nnU-Net 2.8.1's source** (§4.2): the ignore label must be written as **13** on disk,
   not 255; and the locked 100 must not be in Dataset 719 at all.
6. **The npz size** (§3.3): 3.75 GB raw per locked case (all 620 are 512 × 512 × ≤ 275); about 1.1–1.5 GB deflated on a
   synthetic estimate. A chunk of 10 needs ≤ 40 GB.
7. **F-A22's numbers on the 620** (§5): with ImageCAS-X's own side branches standing in for stage-2 classes,
   **literal L2 fails a perfect model** (only 9 % of cases pass). **L1 and K1 fail a model whose only error is an
   ostium painted one voxel too wide** (L1 on the LCx 98 % of the time; K1 21 %). Each gets a re-definition that such
   a model passes (0 %) and a real leak does not, with the ruled numbers kept.

**Independence.** I did not open any other round-3 candidate of this track or any `exp/j1f-r3-*` branch. To read
Step T's results I read #302, whose comment thread includes the five track-1-L round-3 summaries (mine among them).
Those concern 1-L. One fact in them touches this plan: `move_plans` should get `-tp` equal to `-sp`. I had already
read `move_plans_between_datasets.py` in nnU-Net 2.8.1's wheel for §4.2 and reached the same line independently.

## 1. The scorer file of record (§5 item 1)

### 1.1 The file

**`experiments/Delta/j1f_r3/j1f_scorer.py`, sha256 `d615c7e74a07dd5c1d030c5b69441b25d1dc8e6a0014c569699162bf7e09d808`.**

It is Atlas's round-2 `j1f_scorer.py` (`2da3cb1a…886c`) with exactly F-A16/F-A17's change and one consequence of
F-A18:
- **`collapse4` is SegQueue's.** It calls `segqueue14.labels.collapse_to_four` and asserts the sha256 of
  `src/segqueue14/labels.py` (`5f69b5be…0a4b`) at import, as it already does for `tf1.py` (`24441cf8…5254`). It returns
  SegQueue's counts (components, fallbacks, ties) for `collect` to report (F-A17). Atlas's one-voxel ring is deleted.
- **`stage1_labels` is deleted from the scorer.** F-A18 makes `j1f_labels.py` the converter of record. Two converters
  in two hashed files would be two definitions of the reference.
- **Every line from `# geometry` to the self-test is Atlas's, byte for byte** (checked by `diff`). So the pieces,
  lengths, roots, presence, detection and naming are the ones F-A15's lines were simulated on.

### 1.2 The tests (on training fixtures only)

`test_j1f_scorer.py` runs on the six training cases round 2 used (smallest sha256(`asclepius-j1f-r2-scorertest:` +
id): c0585, c0875, c0987, c0287, c0920, c0761; none locked). **37 of 37 pass** (`test_j1f_scorer.log`), after three
synthetic self-tests:
- **Atlas's self-test**, kept, with two checks added: SegQueue's chain rule (a PDA reached only through a PLB that
  leaves the LCx goes to the LCx, 0 fallbacks); and an unattached PDA falls back to the RCA and is counted.
- **The converter's self-test** (§1.4) and **the gate file's** (§2).
- **Delta's round-2 checks, ported to the per-piece scorer:**
  - SegQueue's collapse equals D25 on every non-"Other", non-255 voxel (6 cases);
  - identity: recall, presence and naming 1, and branch tF1 1.000, per class;
  - a one-voxel dilation: recall 1, naming 1;
  - D1 ↔ D2 swapped: recall 1, naming 0;
  - PDA ↔ PLB swapped: recall 1, naming 0;
  - OM2 → LCx: detected, not named, presence drops;
  - OM2 → background: recall 0.
- **Added:**
  - 255 in a prediction scores as background (identity numbers unchanged);
  - an OM2 cut back to the 30 % of its centreline nearest its root is not detected.

### 1.3 Does the scorer count what F-A15 was simulated on?

F-A15's lines come from Atlas's `gate_sim.py`, which draws the number of pieces per case from
`experiments/Atlas/j1f_r2/census_r2.jsonl`. `census620.py` ran the scorer of record's `pieces_of` on the converter of
record's labels, for all 620 training cases.

**Result: the same pieces, case by case, on all 620.**
- For every case and all eight branch classes, the list of pieces (voxel count and length to 0.01 mm) equals
  `census_r2.jsonl`'s: **0 of 620 cases differ** (`census620_summary.json`, `pieces_vs_census_r2`).
- The piece distribution F-A15 drew from is therefore exactly the scorer's:
  - D1 611 × 1;
  - D2 359 × 1;
  - OM1 540 × 1;
  - OM2 229 × 1;
  - PDA 543 × 1, 62 × 2, 3 × 3;
  - PLB 600 × 1, 10 × 2.
- **Atlas's `gate_sim.py`, re-run on this census** (sorted by case), writes `gate_sim.json` and its stdout
  **byte-identical** to the round-2 files F-A15 was frozen from (`gate_sim_on_census620.json`, `.out`).

So the ruling's §7 row "the amended scorer's per-piece counts differ" does not fire, and **F-A15 stays frozen as
ruled.** By construction the scorer's per-piece recall on a reference scored against itself is 1. The
human-level recall distribution behind the lines is the simulation's, drawn on exactly these pieces.

### 1.4 The converter of record (F-A18)

`j1f_labels.py`: Delta's round-1 converter with D47 (A) hard-wired (L-PDA → PDA, L-PLA → PLB; the switch removed) and
F-A3's ignore rule ("Other" touching neither the LAD side nor the LCx side → 255).

**Result on all 620:**
- **Converter counts:** `{'d3': 47, 'd4_to_lad': 2, 'other_lcx': 20, 'other_nearest': 1, 'other_ignore': 8}`. This is
  exactly F-A18's and F0-r2's expected line.
- **The collapse check:**
  - `collapse4` (SegQueue's) equals `territory.to_four` (D25) on **every** voxel outside "Other" and 255: 0
    mismatches.
  - Inside "Other", 40 voxels in 2 cases differ. These are round 1's known 40 voxels: nearest-voxel assignment
    against piece-wise side.
- **SegQueue's contact rule:** 1 296 PDA/PLB components, 93 to the LCx, **0 fallbacks** (0 ties, 0 unattached). This
  is round 2's figure, now on the converter of record.

## 2. `configs/janus1/j1f_gates.json` (§5 item 2)

**`experiments/Delta/j1f_r3/j1f_gates.json`, sha256 `09ddb06f4fc5f8265588b3fa6ea65d4d0cc010f0839b8a245a3e224dc7f4fc5f`.**
The swe copies it byte-identical to `configs/janus1/j1f_gates.json`.
- **Contents:** F-A15's 18 lines; `min_passing` 4; the three statistics' definitions in words; and pins of the scorer
  (`d615c7e7…`), `labels.py` and `tf1.py`.
- **`j1f_gate.py`** applies it:
  - pooled per-piece recall and naming, and per-case presence agreement;
  - **inclusive comparisons in exact fractions** (a line of 0.60 is 60/100, so 24/40 passes; no float edge);
  - `check_gates_file` refuses a file whose sha256 differs from the posted value, or whose scorer pin differs from
    the scorer on disk.

**The test the ruling asks for** (`j1f_gate.py selftest`):

| OM2 fixture | Recall | Expected | Result |
|---|---|---|---|
| 59 of 100 pieces detected | 0.59 | fail | fail |
| 60 of 100 | 0.60 | pass (inclusive) | pass |
| 61 of 100 | 0.61 | pass | pass |
| 24 of 41 (≈ locked OM2's piece count) | 0.585 | fail | fail |
| 25 of 41 | 0.610 | pass | pass |

The same self-test checks that the naming and presence lines bite on their own, and that 4 of 6 passes while 3 of 6
does not.

## 3. The J1F-A command block (§5 item 3)

### 3.1 Where things are on Fir

| Item | Path |
|---|---|
| Repository | `$SCRATCH/asclepius/repo` (dev) |
| venv | `$HOME/icx14-venv` (nnunetv2 2.8.1) |
| Janus 0 (Step T) | `$SCRATCH/janus0_out`, with `$HOME/janus0-keep` as the purge-safe copy. Both hold `SHA256SUMS` |
| ImageCAS-X on Fir | labels `$SCRATCH/icx4/icx/<n>.coronary.nii.gz`; CTs as icx4's layout |
| Work | `$SCRATCH/janus1f` (nnU-Net raw, preprocessed and results for Dataset 719; predictions; `results/`) |

### 3.2 The block

The launcher is `trillium/janus1f/janus1f` (§4), built by the swe issue filed after convergence. Its SBATCH headers
are fixed in §4.4. **The lead runs:**

```sh
# once per session, on fir.alliancecan.ca, inside tmux
module load StdEnv/2023 python/3.11.5
cd $SCRATCH/asclepius && git -C repo fetch origin dev && git -C repo checkout dev && git -C repo pull --ff-only
source $HOME/icx14-venv/bin/activate && pip install --no-deps -e repo
export JANUS0=$SCRATCH/janus0_out; [ -f $JANUS0/SHA256SUMS ] || export JANUS0=$HOME/janus0-keep
(cd $JANUS0 && sha256sum -c SHA256SUMS)                  # four OK lines
export J1F_WORK=$SCRATCH/janus1f
export J1F_GATES_SHA256=09ddb06f4fc5f8265588b3fa6ea65d4d0cc010f0839b8a245a3e224dc7f4fc5f
export J1F_SCORER_SHA256=d615c7e74a07dd5c1d030c5b69441b25d1dc8e6a0014c569699162bf7e09d808
export nnUNet_compile=f                                    # §7.2; set to Janus 0's value if Fir's own job_body.sh is found
L=$SCRATCH/asclepius/repo/trillium/janus1f/janus1f

$L check   | tee $J1F_WORK/check.txt                       # 1. login node, 0 GPU-h: self-tests + dry run. Post it
$L prep                                                    # 2. CPU job, ~1 h: Dataset 719 (the 620 only), plans, preprocess
$L status                                                  #    after prep: prints the plans check and the label counts
J1F_RUN=a1 $L train                                        # 3. two chained 23:50 GPU links, fold 0
J1F_RUN=a2 $L train                                        #    D47 Q8, concurrent, fold 1, its own seed (if allocated)
$L status                                                  # 4. s/epoch, epoch, fitcheck.json (epochs 150, 300), STALL/LEAK
J1F_RUN=a1 $L predict                                      # 5. afterok: locked 100 in 10 chunks of 10 (§3.3)
J1F_RUN=a2 $L predict                                      #    report only
$L collect                                                 # 6. CPU job: opens the look (ledger), scores, writes results/
```

**Send back on #303:**
- `check.txt`;
- `status` after `prep`, after 20 epochs and after epoch 150 (with `fitcheck.json`);
- the first `predict` chunk's `du -sh` line (it sizes the rest, §3.3);
- `results/DECISION.md`, `results/verdict.json` and `results/looks.json` (no weights, no volumes, no per-case
  maps);
- the `.out` of any job that failed.

**What `check` refuses on** (each is a self-test that must fail on a broken input, §4.3):
- Janus 0's `SHA256SUMS` not OK;
- the scorer, the gate file or `j1f_labels.py` not matching the exported hashes;
- F0-r2's three lines not posted, or different (`check` prints them for comparison);
- `nnUNet_compile` unset.

### 3.3 Predict and decode, chunked, with the disk it needs

**What nnU-Net 2.8.1 writes** (read in the wheel: `inference/export_prediction.py`, `predict_from_raw_data.py`):
- logits accumulate as float16 on the 0.5 mm grid;
- they are resampled to the native grid, still float16;
- softmax runs in float32 ("softmax etc is not implemented for half");
- the result is un-cropped to the full image and saved with `np.savez_compressed`.

So each npz is **13 float32 channels at native shape**.
- **Raw size.** All 620 training cases are 512 × 512 × (206 to 275), at most 72.1 M voxels. That gives **3.75 GB raw
  per case**, the hard upper bound.
- **Deflated (estimate).** `npz_size.py` builds smooth synthetic logits from one training case's labels (c0014, 206
  slices), then runs the same float16 → resample → float32 softmax → deflate steps: **1.13 GB** (ratio 2.5). Scaled to
  275 slices that is about 1.5 GB. Real logits may compress better or worse; this is an estimate, not a measurement.
- **Per chunk of 10:** about 15 GB expected, 37.5 GB at most, plus 10 small argmax exports.

**The loop** (`predict`, one GPU job per run; reference code `j1f_decode.decode_chunk`):

```sh
# inside the predict job, for each chunk k = 0..9 (cases: the locked 100 sorted, 10 per chunk)
[ $(df --output=avail -B1G $J1F_WORK | tail -1) -ge 40 ] || { echo "REFUSE: < 40 GB free"; exit 3; }
ln -sf <the chunk's 10 CTs> $J1F_WORK/in/chunk$k/
nnUNetv2_predict -i $J1F_WORK/in/chunk$k -o $J1F_WORK/tmp/chunk$k -d 719 -c 3d_fullres \
  -p nnUNetResEncUNetPlans_60G_iso05 -tr nnUNetTrainer_janus1f -f $FOLD -chk checkpoint_final.pth \
  --save_probabilities --disable_tta -npp 2 -nps 2
du -sh $J1F_WORK/tmp/chunk$k                                # chunk 0's line is posted
python -m janus1f.decode chunk $J1F_WORK/tmp/chunk$k $J1F_WORK/decoded/$J1F_RUN $JANUS0/pred_fir
#   writes per case F, T and the three within-group maps (uint8), then deletes the .npz, .pkl and nnU-Net's .nii.gz
#   and writes the marker; refuses if anything is left in tmp/chunk$k
```

- **The locked CTs are linked into a predict input folder.** They are not in Dataset 719 (§4.2).
- **Decoded output per case:** about 0.4 MB (five uint8 maps, deflated). `collect` reads only maps whose marker matches
  their F (`collect_inputs`).
- **Memory.** One case's float32 probabilities are 3.75 GB, and nnU-Net makes about three such copies at export.
  With `-npp 2 -nps 2` the job asks for 96 GB (§4.4).

### 3.4 `collect`

A CPU job (scoring 100 cases with skeletons is too heavy for a login node). In this order:
1. **The look is opened before anything is scored.** `results/looks.json` gets `{"look": 1, "candidate": "J1F-A",
   "readings": ["F", "T"] (+ "T_L" under §6.3), "opened": <UTC>}`. A third entry refuses (F-A22).
2. **V on F:**
   - F collapsed by the scorer's `collapse4`;
   - the A1c scorer with icx4's in-job aortas, paired with Janus 0's Fir predictions (`$JANUS0/pred_fir`);
   - 10 000 bootstrap resamples, one-sided 2.5 %.
3. **B on F and on T:** `score_case` for each locked case, then `j1f_gate.aggregate` with the pinned gate file.
4. **The verdict table** (master plan §3).
5. **Reports:**
   - contact fallbacks for F and T;
   - D3 and Ramus with n and CI;
   - the rule-ordinal reading;
   - a2;
   - V_L and T_L when 1-L is adopted (§6.3).

## 4. The converged stage-1 spec, as one diff against `janus1l` (§5 item 4)

`trillium/janus1f` **imports** from `trillium/janus1l/lib/` (L-A21 as frozen): the split guard, the sealed guard, the
plans check, the chain logic, `status`, the looks ledger and the editable-install check. It copies none of them.
Below is everything that differs.

### 4.1 The diff

| Item | `janus1l` (L-A21) | `janus1f` |
|---|---|---|
| Cluster, account | Trillium, `def-aso22` | **Fir**, `def-aso22_gpu` for GPU jobs, `def-aso22` for CPU jobs |
| Dataset | 716-ish, 4 classes | **719**, `Dataset719_J1F`: **the 620 only**; 14 labels on disk: 0–12 and **ignore = 13** (§4.2) |
| Label writer | `territory.to_four` | **`j1f_labels.map13`** (sha-pinned), 255 → 13 when written. `prep` refuses unless the summed counts equal F0-r2's posted line |
| Plans | Janus 0's, moved; L-A21 check | the same, **pinned to Step T's hashes** (`plans_check.py`: plans `b7178bbc…`, fingerprint `e41c772f…`); `move_plans … -sp nnUNetResEncUNetPlans_60G_iso05 -tp nnUNetResEncUNetPlans_60G_iso05`; **`batch_dice` False asserted** |
| Fingerprint | Step T's, placed | the same |
| Output head | 5, strict | **13**: non-head tensors strict and bitwise; every `seg_layers` head (deep supervision included) by parent copy (`configs/janus1/j1f_parents.json`) |
| Step-0 identity | n/a | **territory sums of the 13-channel softmax = Janus 0's 5-channel softmax within 1e-5, and decode F = Janus 0's argmax**, on one real training patch, before the first step; refuses otherwise |
| `splits_final.json` | train 620, val 10 tuning | train 620, **val = the 20 fit-check cases** (F-A5's list, sha256 `3f3b696c…1330`); two identical entries |
| Final validation | skipped | skipped (`perform_actual_validation` no-op) |
| Fit check | none | **F-A5:** epochs 150 and 300, the 20 val cases predicted, decoded as F, Dice per class to `fitcheck.json`; `STALL` at 150 if D1, OM1, PDA or PLB < 0.10 |
| Loss | DiceCE, no weights | DiceCE, no weights (Step T: none in Janus 0's logs), ignore label 13 |
| Epochs | 250 | **500** (two 23:50 links) |
| `nnUNet_compile` | Janus 0's | `f` unless Fir's own `job_body.sh` says otherwise (§7.2); `check` refuses it unset |
| Predict | E via `nnUNetv2_ensemble --save_npz` | **one fold per run, never ensembled** (a2 is report only); chunked, `--save_probabilities --disable_tta`, decode, delete (§3.3) |
| Reading(s) | C at t_C | **F and T** (argmax, hierarchical), plus T_L under §6.3. **No threshold, no Rule W, no Rule T** |
| Decision | H1 → H2 → H3, Q4 | **V → B (4 of 6) → verdict table**; the gate file pinned |
| Scorer | A1c `tf1.py` | A1c for V; **`j1f_scorer.py`** for B (pinned) |
| Looks | ≤ 2 (L-A18) | ≤ 2: J1F-A, then J1F-2 (F-A22) |

### 4.2 Two defects the v2 spec would have hit, found in nnU-Net 2.8.1's source

1. **The ignore label.** `LabelManager` asserts that an ignore label equals `max(labels) + 1`
   (`utilities/label_handling/label_handling.py` l. 40–42), and `verify_dataset_integrity` asserts consecutive labels.
   With 13 classes, ignore must be **13** on disk. The converter's 255 is the scorer's convention. `prep` writes
   255 → 13, and `dataset.json` reads `{..., "PLB": 12, "ignore": 13}`. A self-test writes one 255 voxel and expects
   `prep` to refuse.
2. **The locked 100 is not in Dataset 719.** Delta v2's `prep` put the 620 and the locked 100 into one dataset.
   Under F-A20 the locked cases are in no split. But `nnUNetv2_preprocess` would still read their labels and write
   preprocessed copies, and a later `nnUNetv2_plan` or a mistaken fold would find them. Dataset 719 holds the 620.
   The locked CTs are linked into the predict input folder only. Their labels are read only by `collect`.

`move_plans_between_datasets` (read in the same wheel) also needs `nnUNet_preprocessed/Dataset715_ICX4/` to exist,
holding Janus 0's `plans.json` as `nnUNetResEncUNetPlans_60G_iso05.json`, and needs `Dataset719_J1F/` created
first. With `-tp` equal to `-sp` it rewrites `dataset_name` and `image_reader_writer` only (`plans_name` keeps its
value). That is exactly L-A21's check.

### 4.3 Self-tests (`check`; each must fail on a broken input)

**Imported from `janus1l`, unchanged:** split pins, seals, no plan step, strict load, L3 (for V), the ledger.

**1-F's own**, with reference code (all pass here: `j1f_decode.py selftest`, `plans_check.py selftest`,
`j1f_gate.py selftest`, `j1f_labels.py selftest`, `test_j1f_scorer.py`):

| # | Test | Broken fixture that must fail |
|---|---|---|
| 1 | Parent copy: territory sums within 1e-5 of Janus 0's softmax; decode F = Janus 0's argmax | one head row (OM2) left at random init |
| 2 | Decode F = argmax of summed group probabilities, then argmax inside; differs from plain argmax on > 1 % of random voxels | a plain-argmax decode |
| 3 | **F-A19's T test:** a voxel in Janus 0's LCx territory whose most likely 1-F class is PDA is named PDA; a PDA in the RCA territory stays PDA | T with F's groups inside the LCx territory (cannot name it) |
| 4 | T's four classes equal Janus 0's map bit for bit; the within-group maps decode any later four-class map (T_L) the same way | — (assertion inside `decode_t`) |
| 5 | **F-A20's val test:** no locked id in `splits_final.json`; two identical entries; val = the 20 fit-check cases | a locked id in val; a locked id in train; one entry only |
| 6 | Chunked decode deletes the npz, pkl and argmax export; `collect` refuses a map without its marker | a removed marker |
| 7 | Plans: equal to Janus 0's but for `dataset_name` and `image_reader_writer`; Step T's sha256; `batch_dice` False; fingerprint byte-identical | a changed percentile; `batch_dice` True; a plans file that is not Step T's |
| 8 | The scorer's 37 checks on the six training cases | (inside the suite: swaps, erasures, a truncated OM2) |
| 9 | Gates: OM2 0.59 fails, 0.60 and 0.61 pass; 4 of 6 | the same suite |
| 10 | Converter: L-PDA/L-PLA keep their names; first LAD-side "Other" is D3; RCA-only and unattached "Other" → 255 | the same suite |
| 11 | Ignore on disk is 13; a 255 in a written label refuses | one 255 voxel |
| 12 | No locked case in Dataset 719 (raw, preprocessed) | one locked id linked into imagesTr |

### 4.4 SBATCH headers (Fir)

| Job | Header |
|---|---|
| `prep` | `--account=def-aso22 --cpus-per-task=16 --mem=64G --time=3:00:00` |
| `train` (each link) | `--account=def-aso22_gpu --gpus-per-node=h100:1 --cpus-per-task=12 --mem=96G --time=23:50:00`; `nnUNet_n_proc_DA=10` |
| `predict` | `--account=def-aso22_gpu --gpus-per-node=h100:1 --cpus-per-task=8 --mem=96G --time=4:00:00` |
| `collect` | `--account=def-aso22 --cpus-per-task=16 --mem=64G --time=4:00:00` |

### 4.5 Refusals (Delta v2 §8.6, as amended)

The launcher refuses:
- a sealed or locked case in Dataset 719 or in `splits_final.json`;
- plans failing §4.1's check (not "byte-identical", which always fails: F-A20);
- a parent-copy identity error above 1e-5;
- a used dataset id;
- a scorer, gate-file or converter sha256 mismatch;
- converter counts differing from F0-r2's posted line;
- a missing Janus 0 baseline prediction for any locked case;
- an incomplete CT or label set (it prints icx4's idempotent fetch steps and stops);
- less than 40 GB free before a predict chunk;
- a third look.

## 5. F-A22's stage-2 numbers on the 620 (§5 item 5)

### 5.1 The test

ImageCAS-X has no stage-2 class, so "ImageCAS-X references treated as a prediction" contain no stage-2 voxel. On the
literal reading, every gate passes trivially, which tests nothing. So `census620.py` uses **ImageCAS-X's own side
branches as stand-ins** for stage-2 classes of the same calibre (round 1: median radius 0.61–0.67 mm):
- D1–D3 for S1–S3 on the LAD;
- OM1, OM2 and Ramus on the LCx;
- PDA and PLB for Conus, RMA and SN on the RCA.

The "prediction" is the reference with the stand-ins relabelled as stage-2 classes. It is then perturbed in one way
only: **each stand-in bled k voxels into the traced vessel it touches** (k = 0, 1, 2; 26-dilation), which is an ostium
painted too wide.
- **k = 0** is a perfect stage-2 model.
- **k = 1** (0.35 mm) is the smallest error any segmentation network makes.

**Draws:**
- **L1 and L2:** 2 000 random 100-case draws from the 620 (the locked 100's size).
- **K1:** 2 000 random 20-case draws (the fit check's size), and the 20 fit-check cases themselves.
- **Bounds:** F-A22's, one-sided 1.25 % by case bootstrap.

**Results** (`census620_summary.json`; P = probability over 2 000 draws):

| Gate (as ruled) | Perfect stand-in (k = 0) | Ostium 1 voxel wide (k = 1) | 2 voxels (k = 2) |
|---|---|---|---|
| **L1** 0.02, upper bound | passes (share 0) | LAD 0.015, **LCx 0.020**, RCA 0.010 pooled; **P(fail) LCx 0.98** | LAD 0.038, LCx 0.048, RCA 0.018; P(fail) 1.00 / 1.00 / 0.31 |
| **L2** literal (stage-2 voxel > 30 mm from the nearest stage-1 voxel) | **only 9 % of cases pass**; per-case max distance median 41 mm, p95 54.5 mm; P(fail) 1.00 | the same | the same |
| **K1** 0.05, 20 cases | passes (share 0) | LAD 0.046, LCx 0.044 pooled; **P(> 0.05) 0.21** | ≈ 0.10; P = 1.00 |

**Why each fails a correct model:**
- **L2 literal.** A correct branch is attached to the tree. Its far end lies 30–55 mm from the nearest voxel of
  another class, because a branch of a few centimetres runs away from its trunk. By group, the share of cases beyond
  30 mm is LAD 27 %, LCx 37 % and RCA 79 %. Septal perforators run perpendicular into the septum, and the RMA runs down
  the acute margin, so the real classes are no shorter. **No line between 30 and 50 mm is safe** (88 % of cases within
  50 mm). The measure is wrong, not the number.
- **L1 literal.** A stage-2 label that reaches one or two trunk-centreline points at its ostium is not theft. But on a
  thin distal LCx (median trunk centreline 70 mm, p10 41 mm) a one-voxel ostium already reaches 2 %. **Stolen runs are
  short:** the longest run of stolen trunk centreline is 2.8 mm at k = 1 and 5.6 mm at k = 2, over all 620 cases.
- **K1.** An ostium painted one voxel wide puts about 4.5 % of a D/OM-sized branch's voxels into the traced lumen's
  rim. Inside the lumen's **core** (the traced lumen less its one-voxel rim) the share is 1.3 % (p95 over 20 cases
  1.6–1.8 %).

**The re-definitions, measured on the same draws:**

| Gate (proposed) | k = 0 | k = 1 | k = 2 |
|---|---|---|---|
| **L1′:** only stolen runs ≥ 3 mm of trunk centreline count; line 0.02, upper bound | 0 | 0 (no run ≥ 3 mm) | pooled ≤ 0.007; **P(fail) 0** |
| **L2′:** stage-2 components touching no predicted voxel of any class, > 30 mm from the predicted tree | 0 | 0 | 0 |
| **K1′:** the lumen core, line 0.10 | 0 | ≤ 0.018 (p95 on 20); P 0 | ≤ 0.061 (p95); P 0 |

**Power is kept:**
- **L1′.** A model that labels 10 mm of the LAD trunk as a septal in every case steals 9 % of a median LAD trunk
  (110 mm; 12 % at p10), more than four times the line. On the LCx (median 70 mm) it is 14 %.
- **K1′.** A septal head painted over the LAD lumen puts most of its voxels into the core, so a leak gives shares far
  above 0.10.
- **L2′.** It still catches paint far from the heart. A broken but correct branch leaves a fragment a few millimetres
  from its own proximal part, not 30 mm.

**L2's 95 % with a bound.** A per-case pass share needs about 99 of 100 clean cases for its one-sided 1.25 % lower
bound to clear 0.95. A model with stray far islands in 1 % of cases fails that bound 26 % of the time (2 %: 60 %). The
point rule "≥ 95 of 100 cases clean" fails it 0.05 % of the time (2 %: 1.6 %; 5 %: 38 %; 10 %: 94 %)
(`L2_rule_table`).

### 5.2 What I propose (§11, F3-4)

**Keep all four numbers (0.02, 30 mm, 95 %, K1's place in the fit check) and change what three of them measure:**
1. **L1′:** the share of each parent group's reference trunk centreline that lies in a **run of ≥ 3 mm** predicted as
   a stage-2 class is ≤ 0.02, with the one-sided 1.25 % upper bound. 3 mm is twice D3's 1.5 mm tolerance; ostium
   paint stays below it (longest run 2.8 mm at k = 1).
2. **L2′:** in **≥ 95 of the 100** locked cases, no stage-2 voxel lies in a 26-component that touches no predicted
   coronary voxel **and** is more than 30 mm from the predicted tree. This is a point count, not a bound: it is a fold
   tripwire, not an adoption claim, and the bound fails a model with 1 % stray islands a quarter of the time.
3. **K1′:** the share of each stage-2 class's predicted voxels inside the **core** of ImageCAS-X's traced lumen (the
   traced lumen less its one-voxel rim) on the 20 fit-check cases. Above **0.10** at the last check, `LEAK`. 0.05 on
   the core would flag a two-voxel ostium 30–36 % of the time.
4. **Reports added:** the literal L1, L2 and K1, so that the judge can see both forms.

Caveat: the stand-ins are D/OM/PDA/PLB-sized. Septals and the conus may be smaller, which raises the ostium share
in K1 (its denominator is smaller). That is why K1′'s line is 0.10, with the measured p95 at k = 2 being 0.06.

## 6. Q-F2-1 to Q-F2-3: the plan under each answer (§5 item 6)

None is answered. **No answer blocks J1F-A.** Each answer's consequence is written here, so the judge can rule the plan
converged with the questions open.

### 6.1 Q-F2-1: may the 150 sealed pool patients be read in extended mode?

| Answer | Consequence |
|---|---|
| **Yes** (on the ruling's three conditions) | Nothing in J1F-A or J1F-2 changes. S stays on D35 (F-A22). The extended classes are scored on the seal **once, inside D27's single acceptance look, as a report**: per class, n, detection, naming and precision with CI, by the scorer of record. The seal's own four-class read is unchanged (D47 Q1 collapses extended reads to four). No 1-F decision uses them. |
| **No** | SN, Conus and RMA stay counts only until a larger held-out set exists. S1 can reach D35's report tier at best. Nothing else changes. |

### 6.2 Q-F2-2: run Job B (≈ 22 GPU-h on Fir) after J1F-A?

| Answer | Consequence |
|---|---|
| **No** (recommended) | F-A23 as ruled. The first stage-2 class trains at ≥ 30 trainable patients from ≥ 3 sources with ≥ 5 each, with the inter-read floor. After a near-miss failure the line rises to 1.5×. |
| **Yes** | Job B runs after a1's verdict and before J1F-2, on Fir: B30 + Ball, 200 epochs each, OM2 and PLB thinned on a 60-case hold-out of the 620 (Delta v2 §5). It needs the stage-2 label-set trainer, so it waits for that trainer's CPU tests (F-A21). **Rule:** within 0.05 of Ball on recall, presence and naming for both classes → the train line stays 30; otherwise 60. It never touches the locked 100, so it costs no look. Priority stays a1, then a2, then Job B. |

### 6.3 Q-F2-3: if Janus 1-L is adopted, may a released 1-F carry 1-L's vessels (T_L)?

**Built either way.** `decode` keeps three uint8 within-group maps per locked case (§3.3). T_L, 1-L's territories
with 1-F's names under F-A19's sets, can then be built at `collect` from 1-L's maps alone, with no probabilities and
no GPU (§4.3 test 4).

**If no:** F-A24 unchanged. V_L and T_L are reports when 1-L is adopted before `collect`.

**If yes, T_L's verdict rule** (pre-registered now, applied only if Janus 1-L is adopted before J1F-A's `collect`):
1. **V** on F against Janus 0 (unchanged).
2. **V_L** on F against Janus 1-L's shipped locked-100 maps. This is V's own rule: the lower bound of Δ decisive macro
   tF1 is above −0.02, no class's mean Δ is below −0.03, and FP components per case ≤ 1. It is one-sided 2.5 %,
   paired by case, with 10 000 resamples.
3. **B** on F, on T and on T_L (F-A15's lines, 4 of 6).

| V | V_L | B | Ships |
|---|---|---|---|
| pass | pass | F ≥ 4 of 6 | **F** |
| pass | fail | T_L ≥ 4 of 6 | **T_L** (1-L's vessels by construction, 1-F's names) |
| pass | fail | T_L < 4, F ≥ 4 | **F**, with "vessels below Janus 1-L" in `DECISION.md` |
| fail | — | T_L ≥ 4 of 6 | **T_L** in T's place |
| fail | — | T_L < 4, T ≥ 4 | **T** |
| any | — | < 4 of 6 on every reading | not adopted (as ruled) |

**Why this costs no new look:**
- **Inside J1F-A's single look.** T_L is a third pre-registered reading, recorded in `looks.json` before scoring, like
  F and T.
- **It adds no adoption test against Janus 0.** 1-L's vessels already passed 1-L's own H1 against Janus 0. V_L only
  chooses which of two pre-registered vessel sources ships.
- **It moves no line.**

**If 1-L is adopted only after J1F-A's `collect`,** T_L is not part of J1F-A's verdict. Scoring it later would open the
locked 100 again, which is a look. The within-group maps are kept, and a later round may put T_L into the track's
second look (J1F-2) by pre-registering it there.

**What the lead's machine moves:** 1-L's 100 shipped maps (uint8 NIfTI, well under 1 GB), from Trillium to Fir by
Step T's tar route, with a sha256 posted on both sides.

## 7. Step T and F0-r2 (§5 item 7)

### 7.1 Step T: two of its three answers are final

| Step T result | Consequence | Settled? |
|---|---|---|
| No class-weighted CE in any of Janus 0's three logs; no `ce_class_weights.json` | **J1F-A's loss is unweighted DiceCE** (as planned). L-A20's question is moot for 1-F. `prep` still refuses if a weight file appears | **Yes** |
| 3d_fullres `batch_dice: False` | **Stage 2 is leaf-Dice per sample** (F-A21). `leaf_skip` is not built. `plans_check.py` asserts False | **Yes** |
| Hashes posted | Pinned in `plans_check.py` and `check` (§4.1) | **Yes** |
| `nnUNet_compile` not confirmed | §7.2 | rule written |

### 7.2 `nnUNet_compile`: a rule for both outcomes

- **What compile changes.** `torch.compile` changes kernels and speed, not the network or its weights. Its numerical
  differences are at float rounding level, far below the 1e-5 identity check that `train` runs at step 0 under the
  same setting.
- **If the lead finds Fir's own icx4 `job_body.sh`:** set `nnUNet_compile` to its value, and post the line.
- **If not, use `f`.** That is the repository's icx4 value and track 1-L's plan value. A1c's step-0 identity and
  parent-copy checks run under it.
- **`check` refuses it unset**, so the choice is printed and posted before any GPU time is spent.

### 7.3 What has not run

| Job | Status | What it blocks |
|---|---|---|
| **F0-r2** | not run | `prep` (it refuses until the three lines are posted and match: `train620 1350cb1f…`, `locked100 bbd9c687…`, `{'d3': 47, 'd4_to_lad': 2, 'other_lcx': 20, 'other_nearest': 1, 'other_ignore': 8}`). Nothing in the plan text waits on it. Any difference: stop, and the PM finds which copy differs |
| **Job 0 (1-L)** | queued | nothing in 1-F. V's baseline is Janus 0's Fir predictions, which Step T copied (100 of 100) |

- **D50** lets Job 0 run on Fir under `def-aso22_gpu`. It does not change 1-F's baseline, which was always Fir's own
  predictions.
- **D49** answers 1-L's questions. Q-R2-2's D60 use is not needed by 1-F.

## 8. Convergence (§5 item 8)

| §5 item | Settled? | Why |
|---|---|---|
| 1. Scorer of record | **Yes** | File, hash `d615c7e7…`, 37/37 on training fixtures; pieces equal the simulated ones (§1.3) |
| 2. Gate file | **Yes** | File, hash `09ddb06f…`, the 0.59 / 0.61 test |
| 3. J1F-A command block | **Yes** | §3. Two values are read at run time, not decided here: F0-r2's lines and `nnUNet_compile`. Each has its refusal |
| 4. Stage-1 spec diff | **Yes** | §4, with reference code for every 1-F test, and two nnU-Net defects fixed |
| 5. F-A22's numbers | **Yes, if F3-4 is ruled** | §5. Literal L2 fails a perfect model; literal L1 and K1 fail a one-voxel ostium error. The re-definitions pass both and keep every line |
| 6. Q-F2-1 to Q-F2-3 | **No: only the lead can answer.** Not blocking | §6 writes the plan for each answer |
| 7. Step T, F0-r2 | **Step T: yes. F0-r2: not run** | Its result gates `prep`, not the plan |
| 8. Converged? | **Yes, except item 6** | See below |

**My reading: the plan is converged.**
- Every item except 6 is settled with tested code.
- Item 6 has a written consequence for every answer, so the swe issue (F-A12) can be filed now.
- **Before `prep`:** the lead posts F0-r2's three lines and the `nnUNet_compile` line.
- **Before J1F-A's `collect`:** the lead answers Q-F2-3, because it decides whether T_L is a reading in the look.
- **Before J1F-2:** the lead answers Q-F2-1 and Q-F2-2. Neither changes stage 1.

## 9. Cost

| Job | GPU-h | When |
|---|---|---|
| F0-r2 | 0 | now |
| prep | 0 (CPU ≈ 1 h) | after F0-r2 |
| J1F-A a1 (incl. fit checks) | ≈ 29–31 (ceiling 47.7) | after the swe issue |
| a2 (D47 Q8) | ≈ 29–31 | concurrent |
| predict | ≈ 1 per run (≈ 4 h wall for 10 chunks) | afterok |
| collect | 0 (CPU ≈ 1–2 h) | after a1's predict |
| Job B | ≈ 22, only if Q-F2-2 = yes | after a1's verdict |
| **Committed when released** | **≈ 60–64** | |

## 10. What would change this plan

| If… | Then |
|---|---|
| F0-r2's lines differ | Stop before `prep`; the PM finds which copy differs |
| Fir's own `job_body.sh` turns up with `nnUNet_compile` ≠ `f` | Use its value; nothing else changes |
| The first predict chunk is above 40 GB | Chunks of 5; post the new `du` |
| The judge keeps L2's literal definition | It fails a correct stage-2 model in most cases (§5); L2 then reports only, and F-A22's other gates carry far paint |
| The lead answers Q-F2-3 yes and 1-L is adopted before `collect` | §6.3's table decides |
| The lead answers Q-F2-2 yes | §6.2's Job B, after a1's verdict |
| `test_j1f_scorer.py` fails on the swe's copy | The copy is not byte-identical; the swe re-copies; no line changes |

## 11. Proposed amendments

| # | Amends | Change |
|---|---|---|
| F3-1 | F-A16 | The scorer of record is `j1f_scorer.py`, sha256 `d615c7e7…d808`; its tests are `test_j1f_scorer.py` (37 checks) plus the three self-tests |
| F3-2 | F-A15 | The gate file is `j1f_gates.json`, sha256 `09ddb06f…fc5f`; comparisons inclusive, in exact hundredths |
| F3-3 | F-A2, F-A18, F-A20 | Dataset 719 holds the 620 only; ignore is 13 on disk; the plans check is pinned to Step T's hashes; `-tp` = `-sp` |
| F3-4 | F-A22 | L1 counts stolen trunk-centreline runs ≥ 3 mm (0.02, upper bound unchanged); L2 counts stage-2 islands touching no predicted voxel, > 30 mm away, with ≥ 95 of 100 cases clean as a point count; K1 counts the traced lumen's core, line 0.10 (§5) |
| F3-5 | F-A21 | `batch_dice: False` is final (Step T); `leaf_skip` is not built |
| F3-6 | F-A20 | `nnUNet_compile` = Fir's own value if found, else `f`; `check` refuses it unset |
| F3-7 | F-A24 | T_L's verdict rule (§6.3), in force if Q-F2-3 = yes; the within-group maps are kept either way |
| F3-8 | §5 item 8 | The plan is converged except for the lead's answers; the swe issue may be filed |

## 12. Evidence and code (`experiments/Delta/j1f_r3/`)

| File | What |
|---|---|
| `j1f_scorer.py` | The scorer of record (§1) |
| `j1f_labels.py` | The converter of record (§1.4) |
| `j1f_gates.json`, `j1f_gate.py` | The gate file and its reader (§2) |
| `test_j1f_scorer.py`, `test_j1f_scorer.log` | 37/37 on six training cases (§1.2) |
| `j1f_decode.py` | Decode F and T, within-group maps, parent copy, `splits_final`, the chunk loop (§3.3, §4.3) |
| `plans_check.py` | L-A21's check pinned to Step T's hashes (§4.1) |
| `splits_final_j1f.json` | The F-A20 split file (train 620, val the 20 fit-check cases) |
| `npz_size.py`, `npz_size.json` | §3.3 |
| `census620.py`, `summarise_census.py`, `census620_summary.json` | §1.3, §1.4, §5 |

**Not opened:** no locked-100 label (this round reads the 620 only; the locked counts quoted are the published ones),
no sealed or quality-0 case, no CT, no TotalSegmentator twin, no model output. Nothing ran on Fir, SciNet or Trillium.
