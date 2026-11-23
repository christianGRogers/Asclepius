---
tags: [plans, candidate, track-1F, round-3, janus-1F, fir, partial-labels, D44, D45, D47, scorer, gates, swe-spec]
author: Crucible
track: Janus 1-F
round: 3
version: 3
updated: 2026-11-23
issue: christianGRogers/Asclepius#303
---

# Crucible v3 (Janus 1-F): stage 1 can be ruled converged. The scorer and the gates are frozen by hash, T and T_L decode from three small name maps, and two of F-A22's stage-2 measures need their exact form written down, or a perfect model fails them

**Status of the inputs.**
- **The plan in force is Delta v2, as amended by F-A14 to F-A26**, on top of F-A1 to F-A13 and D47. This candidate
  answers [[Janus 1-F Round 2]] §5. It amends the plan; it does not replace it.
- **Binding:** D45, D46, D47, D49 and D50. Nothing here contradicts them:
  - D50 moves only 1-L's Job 0, and only Job 0;
  - D49's Q-R2-2 (D60 label-free) is not used by this track.
- **What has run:**
  - **Step T is done** (#302). Janus 0's 3d_fullres plans have `batch_dice: False`, and no training log shows
    class-weighted CE. Janus 0's `nnUNet_compile` setting is still unverified.
  - **F0-r2 has not run.**
  - **Job 0 (track 1-L) is queued.** Nothing in 1-F waits on it.
  - **The lead has not answered Q-F2-1 to Q-F2-3.** §6 plans for both answers to each.
- **Data used:**
  - the 620 D45 training label files only, fetched by `experiments/Crucible/j1f_r2/fetch620.py`, which builds the
    split from id lists first and downloads no other label file;
  - for the locked 100, only the published counts (F-A7, F-A25).
  - No CT, no locked, sealed or quality-0 label, no TotalSegmentator twin, no pool read and no model output.
  - Nothing ran on Fir, SciNet or Trillium.
- **Independence.** I did not read the other round-3 candidates of this track, their Experiments notes or their
  `exp/j1f-r3-*` branches.
- **Code:** `experiments/Crucible/j1f_r3/`. **Experiments note:**
  [[Crucible - Janus 1-F round 3, the scorer of record, name maps for T and T_L, and the stage-2 gates on the 620]].

## 0. Thesis

1. **The scorer of record exists and is pinned (item 1).**
   - `experiments/Crucible/j1f_r3/j1f_scorer.py` is Atlas's round-2 file with one change of substance: its collapse is
     now an import of SegQueue's `collapse_to_four`, pinned by `labels.py`'s sha256. It also gains `aggregate` and
     `verdict`, which read F-A15's lines.
   - **sha256 `{{SCORER_SHA}}`.**
   - Delta's 31 checks and Atlas's self-test pass on it, on Delta's six training cases.
   - **On all 620, it finds exactly the pieces F-A15 was simulated on:** 620 of 620 case rows are equal to Atlas's
     `census_r2.jsonl`, piece by piece, voxel count and length. **So F-A15's lines need no re-freeze.**
2. **The gates file exists and is pinned (item 2).** sha256 `b4b88e73877e4644825b0aed06a11ae90b00134c1f8fc5441803422c2e7c8e3f`.
   A fixture with OM2 recall 0.59 fails, 0.60 and 0.61 pass, and a tampered file is refused.
3. **T and T_L need no probabilities after `decode` (item 3).** `decode` writes F and three uint8 **name maps**, the
   argmax inside each of F-A19's naming sets. T is Janus 0's territories named from them, bit-for-bit what T would be
   from the probabilities. T_L is the same with 1-L's territories, which may arrive after the npz is gone. The npz of
   one 13-class case is about **{{NPZ_GB}} GB** at float32; a chunk of 10 peaks near **{{CHUNK_GB}} GB**.
4. **The converged stage-1 spec is one diff against `janus1l` (item 4).** It adds F-A19's T test and F-A20's val test,
   and each fails on a broken fixture (`decode_ref.py`).
5. **F-A22's numbers stay (item 5), but two of its measures must be written in the form that does not fail a perfect
   model.** On the 620, with ImageCAS-X's traced side branches standing in for the stage-2 classes:
   - **L1 (theft)** in the nearest-label form is {{L1_NEAREST}}; in a proximity form (centreline within 1.5 mm of a
     stage-2 voxel) it is {{L1_PROX}}, and a perfect model fails 0.02 {{L1_PROX_FF}} of the time. **Write the nearest-label
     form.**
   - **L2 (far paint)** measured per voxel puts a genuine long branch's tip {{L2_VOX}} from the rest of the tree, and fails
     a perfect model {{L2_VOX_FF}}. Measured per 26-component as its gap to the tree, it is {{L2_COMP}}. **Write the
     component form.**
   - **K1** on a perfect, one-voxel-blurred branch is {{K1_D1}} (pooled), far under 0.05.
6. **Q-F2-1 to Q-F2-3 change reports, never stage 1's commands (item 6).** T_L's rule is written (§6.3) and sits
   inside J1F-A's one look.
7. **Step T settles item 7.** `batch_dice` is false, so `leaf_skip` is not needed; no class weights, so F-A2's
   unweighted DiceCE stands. `nnUNet_compile` is set explicitly to `f` and printed; F0-r2 runs inside `check`.
8. **My answer to item 8: stage 1 (J1F-A) is converged.** §8 lists what is settled and what is not.

## 1. Item 1: the scorer file of record

### 1.1 The file

`experiments/Crucible/j1f_r3/j1f_scorer.py`, **sha256 `{{SCORER_SHA}}`**.

| Part | Source | Changed? |
|---|---|---|
| `stage1_labels` (ImageCAS-X → 1-F, D47 (A), F-A3's 255 rule) | Atlas | no |
| Pieces, centreline, length, root, presence, detection, naming, branch tF1 (A1c `24441cf8…5254`, checked at import) | Atlas | no |
| **`collapse4`** | **`segqueue14.labels.collapse_to_four`**, imported; `labels.py` checked at import against `5f69b5be…0a4b` | **yes (F-A17)** |
| `NAMES` | Atlas + the six stage-2 values (13 S1 … 18 RMA), so J1F-2's maps collapse through the same function | extended |
| `aggregate` | new: per class, pooled over **pieces** (recall = detected / pieces, naming = named / detected), presence agreement over cases | new |
| `load_gates`, `verdict` | new: reads `j1f_gates.json`, refuses on a sha256 mismatch or a missing class; a NaN fails; B = ≥ 4 of 6 | new |

- **One behavioural difference from Atlas's collapse, found by the self-test.** SegQueue counts **face** contact.
  Atlas's ring counted 26-neighbours. A PDA or PLB that touches its vessel only along a diagonal therefore has no
  contact and falls back to the RCA, counted.
  - On ImageCAS-X's references this never happens: **{{FALLBACK}} fallbacks in {{COMPONENTS}} components on the 620**,
    and 0 voxels different from D25 outside "Other" and 255.
  - On a prediction it can. `collect` prints the fallback count for F and T (F-A17), so a prediction where it matters
    is visible.
  - This is what pool reads get too, which is F-A17's point. I do not propose changing SegQueue.
- **The file sits three directories below the repository root**, as `trillium/janus1f/lib/` will. So the swe can copy
  it byte-identically, and its relative pins resolve unchanged.

### 1.2 Tests (`test_scorer.py`, `test_scorer.log`)

- **Atlas's self-test**, extended: the chain rule (a PDA reached only through a PLB that leaves the LCx goes to the
  LCx), stage-2 values collapse by SegQueue's `PARENT`, 255 → 0, and `aggregate`/`verdict` on the toy.
- **Delta's 31 checks**, on Delta's six training cases (c0585, c0875, c0987, c0287, c0920, c0761, chosen by
  `asclepius-j1f-r2-scorertest:`), against this file's API:
  - 6 × collapse equals D25 on every non-"Other" voxel, now with 0 fallbacks asserted;
  - per gated class: identity recall, presence and naming 1; identity branch tF1 1; one-voxel dilation recall 1 and
    naming 1;
  - swaps D1/D2 and PDA/PLB: recall 1, naming 0;
  - OM2 → LCx: recall 1, naming 0, presence below 1; OM2 → background: recall 0.
- **Result: {{TEST_RESULT}}.**

### 1.3 The 620 match the distribution F-A15 was simulated on (`pass620.py`, `summarise.py`)

F-A15's lines come from `Atlas/j1f_r2/gate_sim.py`, which draws pieces per case from `census_r2.jsonl`. The scorer of
record, run over all 620:

{{PIECE_TABLE}}

- **Every one of the 620 rows is equal** to `census_r2.jsonl`'s: the same pieces, the same voxel counts, the same
  lengths to 0.01 mm. The collapse change does not touch pieces. **No re-run of `gate_sim.py` is needed (§7 of the
  ruling's "what would change").**
- **The reference scored against itself:** recall, naming and presence are 1.0 for every class, on every piece.
- **The reference eroded by one voxel**, labels kept (a model that draws every vessel one voxel thin):

{{ERODE_TABLE}}

  A one-voxel-thin model loses whole thin branches (Atlas's round-2 observation), and the per-piece recall shows it.
  This is a report, not a line; it says the gate sees lumen width only through whole-branch loss.
- **Converter counts on the 620 (F-A18):** {{CONV}}.

## 2. Item 2: `configs/janus1/j1f_gates.json`

- The file is `experiments/Crucible/j1f_r3/j1f_gates.json`, **sha256
  `b4b88e73877e4644825b0aed06a11ae90b00134c1f8fc5441803422c2e7c8e3f`**. The swe copies it byte-identically to
  `configs/janus1/j1f_gates.json`, and the value above is the one posted on #303.
- It holds F-A15's 18 lines, `k_of_6` 4, and the scorer constants it was simulated with (presence 5 mm, tol 1.5 mm,
  detection 0.5, pieces ≥ 20 voxels). `load_gates` refuses a file whose constants differ from the scorer's.
- **`test_gates.py` (11 checks, all pass, `test_gates.log`):**
  - OM2 recall 0.59 fails, **0.60 passes** (the line is inclusive), 0.61 passes; B still passes with five classes;
  - D1, D2 and OM2 failing: 3 of 6, B fails;
  - naming is named / detected;
  - PDA presence 0.93 fails its 0.97 line;
  - a file with OM2's line changed to 0.59 is refused by sha256, and a file without PLB is refused.

## 3. Item 3: the full J1F-A command block

### 3.1 Disk: one case's npz (`npz_size.py`)

- **Measured:** a 13-channel float32 softmax of training case {{NPZ_CASE}} ({{NPZ_SHAPE}}, {{NPZ_VOX}} M voxels), made
  from its label (each class blurred by σ = 1 voxel, a 1e-6 noise floor), written by `np.savez_compressed` as nnU-Net
  does: **{{NPZ_GB}} GB** (float16: {{NPZ_F16}} GB). Uncompressed it is {{NPZ_RAW}} GB.
- **Upper bound:** Atlas's Trillium note measured 1.25 GB for an **untrained** 5-class npz. Scaled to 13 channels that
  is 3.25 GB per case. An untrained network's softmax is noise everywhere and compresses worst.
- **Plan on 3.3 GB per case.** A chunk of 10 then peaks at **≈ 33 GB** of npz, plus nnU-Net's argmax exports
  (< 10 MB per case). `decode` deletes both before the next chunk (F-A20). F, T's inputs and the name maps add about
  4 × 1 MB per case, kept.
- **RAM:** one case's probabilities are 13 × 72 M × 4 B ≈ 3.7 GB in memory, and nnU-Net's export holds two or three at
  once. The predict job asks for 120 GB.

### 3.2 The commands

The launcher is `trillium/janus1f/janus1f`, built by the swe issue (F-A12) to §4. Every GPU job is on Fir with
`--account=def-aso22_gpu --gpus-per-node=h100:1` and explicit `--cpus-per-task` and `--mem`; CPU jobs use
`--account=def-aso22`.

**Environment, once per session** (on `fir.alliancecan.ca`, inside `tmux`):

```sh
module load StdEnv/2023 python/3.11.5
cd $SCRATCH/asclepius && git -C repo fetch origin dev && git -C repo checkout dev && git -C repo pull --ff-only
source $HOME/icx14-venv/bin/activate
pip install --no-deps -e repo                       # editable: the sealed list resolves (L-A21)
rm -rf experiments/janus1f && cp -r repo/trillium/janus1f experiments/janus1f && cd experiments/janus1f
export JANUS0=$SCRATCH/janus0_out                   # Step T's folder; $KEEP is the fallback
export J1F_WORK=$SCRATCH/janus1f
export J1F_GATES_SHA256=b4b88e73877e4644825b0aed06a11ae90b00134c1f8fc5441803422c2e7c8e3f
export J1F_SCORER_SHA256={{SCORER_SHA}}
export nnUNet_compile=f                             # explicit (§7); printed by check
```

**1. `check` (login node, 0 GPU-h).** Self-tests (§4.3), then a dry run. It includes F0-r2 (F-A26):

```sh
./janus1f check 2>&1 | tee $J1F_WORK/check.txt
```

It prints, and refuses on any difference:
- `train620 1350cb1f…1152` and `locked100 bbd9c687…5895`;
- the converter counts on Fir's own 620 + 100: `{'d3': 47, 'd4_to_lad': 2, 'other_lcx': 20, 'other_nearest': 1,
  'other_ignore': 8}` on the 620 (F0-r2's line; the locked 100's counts are printed, not compared);
- Step T's four `SHA256SUMS` lines, re-checked (`sha256sum -c`);
- 100 Janus 0 Fir predictions present, with their sha256 list written to `$J1F_WORK/baseline.sha256`;
- `batch_dice False` from Janus 0's plans (F-A21), and no `ce_class_weights.json`;
- the scorer, gates, `labels.py` and `tf1.py` sha256;
- `nnUNet_compile=f`;
- every SBATCH header below.

**2. `prep` (CPU job, ≈ 1 h).** Dataset 719: the 620 + the locked 100, ids `cNNNN`, labels by F-A18's converter.
Step T's `plans.json` placed as `Dataset715_ICX4/nnUNetResEncUNetPlans_60G_iso05.json`, then
`nnUNetv2_move_plans_between_datasets`, then `nnUNetv2_preprocess` only; Janus 0's `dataset_fingerprint.json`
placed; `splits_final.json` written by `decode_ref.splits_final` (train = the 620, val = the 20 fit-check cases).

```sh
./janus1f prep        # submits: --account=def-aso22 --cpus-per-task=16 --mem=64G --time=3:00:00
```

**Run `prep` before 2026-12-20.** It reads the CTs and the 720 labels from `$SCRATCH/icx4`, which the scratch purge
removes; Step T kept only Janus 0 and the 160. After the purge, `prep` refuses and prints icx4's own fetch steps.

**3. `train` (two concurrent chains, ≈ 29–31 GPU-h each; a2 per D47 Q8).**

```sh
J1F_RUN=a1 ./janus1f train     # fold 0
J1F_RUN=a2 ./janus1f train     # fold 1, its own seed; report only
# each link: --account=def-aso22_gpu --gpus-per-node=h100:1 --cpus-per-task=12 --mem=120G --time=23:50:00
# SEGTRAIN_MAX_SECONDS=84600 (walltime - 30 min), SEGTRAIN_SAVE_EVERY=10, two links, afterok
./janus1f status               # s/epoch, epochs done, chain state; fitcheck.json after epochs 150 and 300
```

The fit check writes `STALL` at epoch 150 (F-A5) and K1's stage-1 counterpart is not computed (K1 is stage 2's).

**4. `predict` (after a1's last link, ≈ 1–2 GPU-h).** The locked 100 in chunks of 10:

```sh
./janus1f predict              # --account=def-aso22_gpu --gpus-per-node=h100:1 --cpus-per-task=12 --mem=120G --time=4:00:00
```

For each chunk: `nnUNetv2_predict -chk checkpoint_final.pth --save_probabilities --disable_tta -f 0 -npp 2 -nps 2`
into `$J1F_WORK/tmp_chunk/`; then `decode` writes per case `F/<id>.nii.gz`, `N/<id>_{LAD,LCx,RCA}.nii.gz` (the name
maps, §4.2) and `T/<id>.nii.gz` (Janus 0's Fir territories named by N), stamps each with a marker holding the
checkpoint's sha256, and **deletes the chunk's `.npz`, `.pkl` and nnU-Net's own `.nii.gz`** before the next chunk.
`predict` scores nothing. a2 is predicted the same way into its own folder, if it ran.

**5. `collect` (login node, 0 GPU-h).** Once only (the looks ledger):

```sh
./janus1f collect              # writes results/DECISION.md, results/verdict.json
```

It refuses without: the two posted sha256 (scorer, gates); a marker on every F/T/N map; a second entry in the ledger.
It scores V on F (collapsed by F-A17) against Janus 0's Fir predictions with the A1c scorer and icx4's aortas, then B
on the reading that ships, then the verdict table (§6.3 if Q-F2-3 is yes). It prints the collapse fallback counts for
F and T.

**Send back on #303:** `check.txt`; `status` at epoch 20 and after epoch 150, with `fitcheck.json`; `results/`
(no weights, no volumes); the `.out` of any failed job. **Never post** a locked case's map.

## 4. Item 4: the converged stage-1 spec, as one diff against `janus1l`

### 4.1 Shared with L-A21, imported from `trillium/janus1l/lib/`, unchanged

Editable install and the printed sealed paths; the plans move, `preprocess` only and the fingerprint placed; L-A21's
plans check (equal once `dataset_name` and `image_reader_writer` are removed; a changed percentile refuses); the split
file and its pins; `SEGTRAIN_CT_WINDOW=off`, `SEGTRAIN_SAVE_EVERY=10`, `SEGTRAIN_SAVE_PROBABILITIES=0`,
`SEGTRAIN_MAX_SECONDS`; `SEGTRAIN_ITERATIONS`/`SEGTRAIN_EPOCHS` unset; `checkpoint_best` never read;
`perform_actual_validation` a no-op; the chain logic; `status`; the looks ledger; self-tests 1–6 of L-A21.

### 4.2 The diff

| Item | `janus1l` (L-A21) | `janus1f` |
|---|---|---|
| Cluster | Trillium, `def-aso22` | **Fir**: GPU `--account=def-aso22_gpu --gpus-per-node=h100:1 --cpus-per-task=12 --mem=120G`; CPU `--account=def-aso22` |
| Dataset | 718, `territory.to_four` | **719**, F-A18's converter (Delta's `j1f_labels.py`, D47 (A) hard-wired, F-A3's 255) |
| Label check | — | `collapse4` (the scorer of record) of every 719 label equals `territory.to_four` outside "Other" and 255, with 0 fallbacks; converter counts = F0-r2's line |
| `splits_final.json` val | 10 lowest-id tuning cases | **the 20 fit-check training cases** (smallest sha256(`asclepius-j1f-fitcheck:` + id)) |
| Trainer | `nnUNetTrainer_janus1l` | `nnUNetTrainer_janus1f`: the same plus the parent-copy head build (`configs/janus1/j1f_parents.json`) with its two step-0 identity checks, and the fit check at epochs 150 and 300 (F-A5) |
| Epochs | 250 | **500** |
| Loss | DiceCE, no weights | the same, 13 classes, ignore 255; **`batch_dice: false` asserted** (F-A21; Step T: false) |
| `nnUNet_compile` | "as Janus 0's" | **`f`, explicit and printed** (§7) |
| `predict` | folds + `nnUNetv2_ensemble --save_npz` | fold 0 (and fold 1 if a2 ran); chunks of 10; `--save_probabilities --disable_tta`; **`decode` writes F, N and T, then deletes the npz and nnU-Net's export** |
| Baseline | Janus 0 on Trillium (Job 0) | **Fir's own Janus 0 predictions** from Step T (`$JANUS0/pred_fir`), sha256 list fixed at `check` |
| Threshold | t\*, Rule T | none: 1-F reads at argmax (F's hierarchical decode) |
| `collect` | H1–H3 | V (= H1) on F collapsed by F-A17; B on the reading that ships, via `j1f_scorer.verdict` and the gates file; F-A9's reports; F-A24's V_L/T_L when 1-L is adopted; §6.3's rule if Q-F2-3 is yes |
| `transfer` | Rule T | not used |

### 4.3 Self-tests added (`./janus1f check`; each must fail on its broken fixture)

7. **Parent copy** (Delta §8.3 test 1): territory sums equal Janus 0's within 1e-5 and the hierarchical decode equals
   Janus 0's argmax, for every deep-supervision output. Fixture: one head row not copied.
8. **Hierarchical decode** (Delta test 2; `decode_ref.py` checks 1–2): F's territory is the argmax of the group sums;
   a plain argmax differs on > 1 % of random voxels. Fixture: a decode that takes the plain argmax.
9. **F-A19's T test** (`decode_ref.py` checks 3–5): T from the name maps equals T from the probabilities on every
   voxel; T's vessels are Janus 0's; **a left PDA inside Janus 0's LCx territory is named PDA**. Fixture: Delta v2's
   LCx naming set without PDA/PLB, which names it LCx and fails.
10. **F-A20's val test** (`decode_ref.py` checks 9–11, and `check_splits_file` on the file `prep` wrote): two identical
    entries, val inside the 620, **no locked or sealed id anywhere in `splits_final.json`**. Fixture: a locked id as
    val, which is L-A21's leak.
11. **The scorer:** `j1f_scorer.py selftest` and `test_scorer.py` on Delta's six training cases (§1.2).
12. **The gates:** `test_gates.py` (§2).
13. **Labels:** the converter on a 3-case fixture gives its counts; an L-PDA voxel written as RCA fails the collapse
    check.
14. **The locked 100 is never scored before `collect`:** no `summary.json` and no `validation/` folder exists after
    `train`; `predict` writes no score.

### 4.4 Refusals added (Delta §8.6, corrected)

A locked or sealed id in training or as val; plans not equal by L-A21's check (**not** byte-identity, which always
fails); a parent-copy identity error above 1e-5; dataset 719 already in use; a scorer, gates, converter, `labels.py`
or `tf1.py` sha256 mismatch; a missing Janus 0 baseline for any locked case; `batch_dice: true`; a converter count
different from F0-r2's line; a CT or label set incomplete (then icx4's fetch steps are printed).

## 5. Item 5: F-A22's stage-2 numbers on the 620

### 5.1 How a perfect model was made

ImageCAS-X traces no stage-2 class. So its traced side branches stand in, host by host, as F-A21 places the stage-2
classes: **D1–D3 for the LAD group** (S1–S3 leave the LAD as the diagonals do), **OM1, OM2 and the ramus for the LCx
group** (SN off the LCx), **PDA and PLB for the RCA group** (SN, Conus, RMA). The reference is the prediction. Two
versions: exact, and with the proxy classes bled one voxel into their parent (a realistic ostium error). For K1 the
proxies are removed from the "traced" map, as ImageCAS-X would leave an untraced branch as background
(`pass620.py`).

### 5.2 Results ({{N5}} cases with a proxy branch)

{{ITEM5_TABLE}}

False-fail = the share of 4 000 draws of 100 cases (K1: 20 cases) in which the measure crosses its line, with
F-A22's one-sided 1.25 % bound where it has one.

### 5.3 What I propose (amends F-A22's text; the numbers stay)

| Number | Keep? | The form to write into the spec |
|---|---|---|
| **L1 = 0.02** | **keep** | **nearest-label:** a reference centreline point of the parent group is stolen when its **nearest predicted coronary voxel** carries a stage-2 class. Pooled over the locked cases, upper bound one-sided 1.25 %. The proximity form (any stage-2 voxel within 1.5 mm) counts every ostium as theft and fails a perfect model ({{L1_PROX_FF_SHORT}}) |
| **L2 = 30 mm, 95 %** | **keep** | **per component:** a stage-2 26-component is far paint when its **nearest** distance to the predicted non-stage-2 coronary foreground exceeds 30 mm. The per-voxel form measures a branch's length, not a gap ({{L2_VOX_SHORT}}) |
| **K1 = 0.05** | **keep** | as ruled: the share of a stage-2 class's predicted voxels inside ImageCAS-X's traced lumen, on the 20 fit-check training cases, at the last fit check |

- **L2's 95 % is a point share, not a bound.** With a 1.25 % lower bound, 99 of 100 passing cases gives 0.94 and fails.
  {{L2_BOUND_NOTE}}
- **No number changes.** The forms above are the ones under which the round-2 numbers mean what the ruling says they
  mean. They are frozen before J1F-2 is submitted (F-A22).
- **A guard for Q-F2-1's "yes" (§6.1):** the band re-set (F-A21) and the inter-read floor (F-A23) read only
  **trainable** extended reads. Their scripts refuse a read of a sealed-pool patient (D27's guard, by patient).

## 6. Item 6: Q-F2-1 to Q-F2-3, both answers

Nothing in §3's commands depends on any answer. `decode` writes the name maps either way.

### 6.1 Q-F2-1 (the sealed pool in extended mode; my question)

| Answer | Consequence |
|---|---|
| **Yes** (with the ruling's three conditions) | The 150 sealed patients' reads are made in extended mode. The extended classes are scored **only inside D27's single acceptance look (A19), as a report**: per class n, detection and naming with CI. They never decide J1F-2 (whose S tier stays D35's), never set the band, never set a read threshold, and are never read earlier. The refusals of §5.3 enforce the last three. SN, Conus and RMA can then be reported once, at acceptance |
| **No** | The seal's reads stay as they are. SN, Conus and RMA stay counts only until a larger held-out set exists (ruling §7). Nothing else changes |

### 6.2 Q-F2-2 (Job B)

| Answer | Consequence |
|---|---|
| **No** (recommended, as the ruling) | F-A23's rule. Fir's priority is a1, then a2 |
| **Yes** | J1F-B (≈ 22 GPU-h) runs after a1 and a2 on Fir, never before. Its only output is F-A23's per-class thresholds, re-set **before** J1F-2 is submitted. It reads no locked case |

### 6.3 Q-F2-3 (may a released 1-F carry 1-L's vessels?)

**If no:** F-A24 as ruled. V_L and T_L are reports.

**If yes, the rule (inside J1F-A's one look):**
- **Inputs, fixed before `collect`:** 1-L's shipped locked-100 maps (E at t_C, the files 1-L's own `collect` scored),
  copied to Fir with their sha256 list posted on #303. T_L = `name_territory(1-L's map, N)`, so it needs no
  re-prediction and no probabilities.
- **Timing:** if 1-L's verdict is still pending when J1F-A's `predict` ends, `collect` waits up to 14 days for it, then
  runs with whatever is adopted then. That window is written now, so the wait is not a choice made after seeing
  anything.
- **The sequence** (V and B unchanged; V_L uses V's own rule with 1-L's maps as the baseline):

| V (F vs Janus 0) | V_L (F vs 1-L) | Ships |
|---|---|---|
| pass | pass | **F**, if B passes on F (as ruled) |
| pass | fail | **T_L**, if B passes on T_L; else **F**, if B passes on F, with V_L's failure written into `DECISION.md` |
| fail | — | **T_L**, if B passes on T_L; else **T**, if B passes on T (as ruled) |
| any | — | B fails on every eligible reading: not adopted (as ruled) |

- **Why this is still one look.** Every reading comes from the same J1F-A network in one `collect` run, in a fixed
  order. V_L can only move the release from F to T_L, whose vessels are an already-adopted model's. It never adopts a
  model on a test it could pass by chance in a second try.
- **Why T_L, not T, when V fails.** Both have adopted vessels. T_L's are the better ones by 1-L's own verdict.

## 7. Item 7: Step T and F0-r2

| Result | Consequence |
|---|---|
| `batch_dice: False` (Step T) | F-A21's per-sample leaf-Dice stands; `leaf_skip` is not needed. The assertion stays, so a changed plans file still refuses |
| No class-weighted CE in any log (Step T) | F-A2's unweighted DiceCE stands. Nothing to re-decide (as L-A20) |
| `nnUNet_compile` unverified | **Set `nnUNet_compile=f` explicitly, and print it.** `torch.compile` changes kernels, not the model's arithmetic beyond float tolerance. The step-0 identity checks (territory sums within 1e-5 of Janus 0, decode equal to Janus 0's argmax) run under the chosen setting, so they prove the start is Janus 0 either way. If Step T later shows `t`, nothing changes but speed |
| F0-r2 not run | **Folded into `check`** (§3.2 step 1): the two pins and the converter counts on Fir's own copy, refusing on any difference. It still can run alone now, as the master plan writes it |

## 8. Item 8: is the plan converged?

**Yes for stage 1 (J1F-A and a2).** Settled by this candidate's evidence:

| §5 item | Settled? | Why |
|---|---|---|
| 1. Scorer of record | **yes** | file and sha256 here; tests pass; 620 of 620 rows equal the simulated distribution |
| 2. Gates file | **yes** | file and sha256 here; the 0.59/0.61 test passes |
| 3. Command block | **yes** | §3, with the disk estimate |
| 4. Stage-1 spec | **yes** | §4, with the T and val tests and their broken fixtures |
| 5. Stage-2 numbers | **yes, as numbers**; their forms are written here | §5. The band width stays data-dependent by design (F-A21) |
| 6. Q-F2-1 to Q-F2-3 | **yes in both branches** | §6; none touches stage 1's commands |
| 7. Step T, F0-r2 | **yes** for Step T; **F0-r2 is folded into `check`** | §7 |

**Not settled, and not blocking J1F-A:**
- **F0-r2's numbers.** `check` refuses if they differ, so the risk is a stop, not a wrong run.
- **`nnUNet_compile`'s historical value.** Settled by setting it (§7).
- **The lead's three answers.** §6 covers both branches of each.
- **Stage 2 (J1F-2)** waits on read counts by design (F-A23). Its forms are fixed here; its band is re-set from reads.
- **The swe issue** is filed only after the ruling (F-A12). Converged means its spec is complete, not that its code
  exists. The self-tests in §4.3 are what show the code matches.

**Deadline.** `prep` reads `$SCRATCH/icx4` and must run before the purge (~2026-12-20). If convergence is ruled now,
the swe issue has about three weeks.

## 9. What would change this plan

| Observation | Then |
|---|---|
| `check` prints converter counts or pins different from F0-r2's line | Stop; the PM finds which copy differs |
| The swe's scorer copy has a different sha256 | `collect` refuses; the copy is fixed, never the posted hash |
| `prep` cannot run before the purge | It refuses and prints icx4's fetch steps; the lead re-fetches, then `prep` |
| The first extended reads give a stage-2 proxy unlike the traced branches (e.g. septals far longer than D1) | L2's component form is unaffected; L1's nearest-label form is unaffected. Only the band (F-A21) moves |
| A measured second-reader branch study arrives before J1F-A is submitted | F-A15's lines are recomputed by Atlas's rule; the gates file and its sha256 change before submission, never after |
| 1-L's adopted maps arrive after the 14-day window | T_L is reported later, never shipped by this look |

## 10. Evidence and code (`experiments/Crucible/j1f_r3/`)

| File | What |
|---|---|
| `j1f_scorer.py` | the scorer of record (sha256 `{{SCORER_SHA}}`) |
| `j1f_gates.json` | F-A15's lines (sha256 `b4b88e73…8e3f`) |
| `test_gates.py`, `test_gates.log` | §2 |
| `test_scorer.py`, `test_scorer.log` | §1.2 |
| `decode_ref.py`, `decode_ref.log` | F, name maps, T, T_L, `splits_final` and their self-tests (§4.3) |
| `pass620.py`, `summarise.py`, `summary620.json` | §1.3 and §5, on the 620 |
| `npz_size.py`, `npz_size.out` | §3.1 |
