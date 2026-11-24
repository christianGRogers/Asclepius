---
aliases: [Master plan - Janus 1-F, Janus 1-F plan]
tags: [plans, master, track-1-F, janus1-f, branches, D44, D45, D47, D50, fir, locked100, partial-labels, converged-stage1]
status: living
track: 1-F
round: 3
updated: 2026-11-23
issue: christianGRogers/Asclepius#303
---

# Master plan, track 1-F (Janus 1-F)

**In force: [[Candidates/Janus 1-F/Delta v3|Delta v3]] (track 1-F), as amended by the judge in
[[Janus 1-F Round 1]] (F-A1 to F-A13), [[Janus 1-F Round 2]] (F-A14 to F-A26) and [[Janus 1-F Round 3]] (F-A27 to
F-A36).**
- The amendments are binding and override the candidate text where they conflict.
- This file is the track's plan.
- The main [[Master plan]] (Delta v10, Round 10) still governs the pool-driven work, D35 and the seal.
- Track 1-L ([[Master plan - Janus 1-L]]) shares the split (L-A1 = F-A1), the vessel guard (H1 = V), Step T, the
  launcher base (L-A21) and the look budget (L-A18 = F-A22).

**Binding decisions:**
- **D45:** the classes, the split, Fir; the lead runs every job.
- **D47:** round 1's answers, all as recommended. A left PDA/PLB is named PDA/PLB and collapses to the vessel it leaves.
  Also: the "complete" flags, child over parent, D35 in extended mode, trace beyond the seed, a2, and the names Janus
  1-F.1 / Janus 1-F.
- **D44:** the extended classes are optional per read.
- **D8:** ImageCAS-X's lumen.
- **D25, D1, D1b:** the four-class collapse by territory.
- **D22:** ImageCAS-X is not re-annotated.
- **D27/D32:** the seals.
- **D35:** decides pool questions only.
- **D40,** as amended by D47 Q4: overlaps become ignore.
- **D34:** naming.

**Status: stage 1 (J1F-A, a2) converged in round 3** ([[Janus 1-F Round 3]] §3.10), on five checks with stop rules:
F0-r2's lines, the compile counts, the F-A8 identity, `check` on Fir, and the lead's Q-F2-3 answer before `collect`.
The `role:swe` issue for `trillium/janus1f` is filed now (F-A12, F-A36). **Stage 2 (J1F-2) stays provisional**: its
numbers are frozen from the first extended reads before J1F-2 is submitted (F-A22, F-A30). Step T is done (#302).
Questions Q-F2-1 to Q-F2-3 and Q-F3-1 to Q-F3-3 are with the lead (§6).

## In one paragraph

**Janus 1-F is Janus 0 grown into the branches ImageCAS-X traced, then, later, into the ones it did not.**

**Stage 1 (J1F-A):**
- A 13-output nnU-Net: bg, LM, LAD, LCx, RCA, D1, D2, D3, OM1, OM2, Ramus, PDA, PLB.
- Warm from Janus 0 by parent copy, so at step 0 it **is** Janus 0, territory for territory.
- Decoded hierarchically.
- 500 epochs on D45's 620, with Janus 0's plans and mirroring off.
- Validated in training only on 20 training cases. **The locked 100 is touched once, at `collect`.**

**The locked 100** decides with a fixed sequence:
- the vessels hold Janus 0's line (V = track 1-L's H1);
- then each of six branch classes passes **per-class** detection, presence and naming lines, calibrated to ImageCAS-X's
  own second analyst;
- at least 4 of 6 must pass.
- If 1-F's own vessels fail, the shipped model is **T**: Janus 0's four classes, named by 1-F.

**Stage 2 (J1F-2)** adds S1–S3, SN, Conus and RMA from extended pool reads:
- marginal CE plus per-sample leaf-Dice;
- territory-specific background sets in a band that the first extended reads re-set;
- only when per-class read counts are met;
- one more look on the locked 100, at one-sided 1.25 %, with a leakage gate.

## 1. Classes, labels, decoding, collapse (F-A3, F-A17 to F-A19)

| 1-F class | Stage 1 label from ImageCAS-X | Gated on the locked 100? |
|---|---|---|
| LM, LAD, LCx, RCA | same | V (collapsed) |
| D1, D2, OM1, OM2 | same | yes (97, 64, 84, 40 locked cases at 5 mm) |
| PDA, PLB | R-PDA ∪ L-PDA, R-PLA ∪ L-PLA (D47 Q1 (A)) | yes (98, 99) |
| Ramus | IM | report (24) |
| D3 | first LAD-side "Other" piece | report (7) |
| (LAD) | later LAD-side "Other" pieces (D4+) | — |
| (LCx) | LCx-side "Other" (OM3+) | — |
| ignore (255 in the scorer; 13 on disk, F-A29) | "Other" touching only the RCA, or nothing (8 pieces on the 620) | — |
| S1–S3, SN, Conus, RMA | **not traced**: background. No head in stage 1 | stage 2, pool reads only |

**Converter (F-A18, F-A28):** the scorer of record's `stage1_labels` (Delta's map with D47 (A) hard-wired and the 255
rule; equal to it on every voxel of the 620). One function writes Dataset 719's labels and builds `collect`'s
references. Expected on the 620: D3 47, D4 → LAD 2, LCx-side "Other" → LCx 20, nearest 1, ignore 8.

**Ignore on disk (F-A29):** nnU-Net 2.8.1 requires the ignore label to be max + 1, so Dataset 719's files and
`dataset.json` carry **13**, not 255. The scorer keeps 255.

**Decoding F:** the territory is the argmax of the summed probabilities over {bg}, {LM}, {LAD, D1, D2, D3}, {LCx, OM1,
OM2, Ramus} and {RCA, PDA, PLB}. The class is the argmax inside it.

**Decoding T (F-A19):**
- The territory is Janus 0's argmax.
- Inside Janus 0's LCx territory the class runs over {LCx, OM1, OM2, Ramus, **PDA, PLB**}; inside the RCA territory,
  over {RCA, PDA, PLB}.
- T's four classes **are** Janus 0's map, asserted bit-equal.
- **Name maps (F-A31):** `decode` writes **G**, three uint8 maps (the argmax within {LAD, D1, D2, D3}, within {LCx,
  OM1, OM2, Ramus, PDA, PLB}, within {RCA, PDA, PLB}). T is G selected by Janus 0's territory; T_L is G selected by
  Janus 1-L's shipped map. Neither needs the probabilities.

**Collapse (F-A17):** SegQueue's `collapse_to_four` / `assign_contact_branches` (`src/segqueue14/labels.py`), imported
and pinned. One implementation for pool reads and 1-F:
- D1–D3 → LAD;
- OM1, OM2, Ramus → LCx;
- each PDA/PLB component → the vessel with the most face contact, with the chain rule; RCA on a tie or no contact,
  counted.

On ImageCAS-X's references it reproduces every side label (1,296 of 1,296 components on the 620, 0 fallbacks).

## 2. Recipe, J1F-A (F-A2, F-A20)

| Item | Setting |
|---|---|
| Start | Janus 0 `checkpoint_final.pth` (Dataset715) via A17a's `finetune_load`: non-head tensors strict and bitwise; every `seg_layers` head by parent copy (`configs/janus1/j1f_parents.json`). It refuses unless the territory sums equal Janus 0's within 1e-5 **and** the hierarchical decode equals Janus 0's argmax |
| Dataset | **Dataset 719 = the 620 only** (F-A29). The locked 100's CTs are linked into a predict input folder by `predict`; their labels are read only by `collect`. Labels 0–12, **ignore 13** |
| Plans | Step T's `plans.json` placed as `Dataset715_ICX4/nnUNetResEncUNetPlans_60G_iso05.json`, `nnUNetv2_move_plans_between_datasets -s 715 -t 719 -sp nnUNetResEncUNetPlans_60G_iso05 -tp nnUNetResEncUNetPlans_60G_iso05`, then `nnUNetv2_preprocess` only. **L-A21's plans check**, pinned to Step T's sha256 (`b7178bbc…3cc2`, fingerprint `e41c772f…7e05`), `batch_dice` False. Janus 0's `dataset_fingerprint.json` placed. No `plan_experiment`, no `extract_fingerprint`. `SEGTRAIN_CT_WINDOW=off` |
| Schedule | 500 epochs × 250 iterations, batch 2; 2500-iteration linear warm-up to 1e-2, then poly |
| Loss | DiceCE, unweighted (Step T: Janus 0 had no class weights), deep supervision, ignore label 13 |
| Fixed | mirroring off; default augmentation otherwise; uniform sampling; `checkpoint_final` only (`checkpoint_best` never read); `--disable_tta`; `SEGTRAIN_SAVE_EVERY=10`; `SEGTRAIN_MAX_SECONDS` = walltime − 30 min; **`nnUNet_compile` = `JANUS0_COMPILE`, read from Janus 0's training logs (F-A33; expected `f`)**; editable segtrain install |
| Validation | `splits_final.json`: two identical entries, train = the 620, **val = the 20 fit-check training cases**. `perform_actual_validation` is a no-op. **The locked 100 is never validated on** |
| Stall check (F-A5) | at epochs 150 and 300, Dice on the 20 fit-check cases (smallest sha256(`asclepius-j1f-fitcheck:` + id)); at 150, D1, OM1, PDA or PLB < 0.10 writes `STALL` and the PM may cancel. It reads a1 only |
| Runs | a1 = fold 0; a2 = fold 1, concurrent, its own seed, report only (D47 Q8) |
| Predict | locked 100 in chunks of 10, `--save_probabilities --disable_tta`; `decode` writes F, T and G with a marker, then deletes the chunk's npz, pkl and nnU-Net's own argmax export. ≤ 38 GB per chunk; refuses with < 40 GB free; posts chunk 0's `du -sh`. `collect` reads only marked maps |
| Fir headers (F-A34) | GPU: `--account=def-aso22_gpu --gpus-per-node=h100:1 --cpus-per-task=12 --mem=280G`, `--time=23:50:00` per train link, `6:00:00` for predict. CPU: `--account=def-aso22 --cpus-per-task=16 --mem=64G`. `JANUS0=$HOME/janus0-keep` |

## 3. The pre-registered decision on the locked 100 (F-A6, F-A7, F-A15, F-A16, F-A22, F-A27, F-A28, F-A32)

**Inputs:**
- **Baseline:** Janus 0's own Fir predictions, at argmax.
- **Vessel scoring:** the A1c scorer (`24441cf8…5254`) with icx4's in-job aortas, which cover all 100. A1a/A1b
  exclusions apply.
- **Branch scoring:** the scorer of record (F-A28): `experiments/Atlas/j1f_r3/j1f_scorer.py`, sha256
  `5221032f3dc086d686b63fa946149a215ac00738a87fd9669d7faa15962b2e5b`, copied byte-identical to
  `trillium/janus1f/lib/`. It holds the definitions, SegQueue's collapse, the pooling and the gate.
- **Gate file of record (F-A27):** `experiments/Judge/j1f_r3/j1f_gates.json`, sha256
  `198b3b158098d846358971ad8a85f22eda7f9a76c00f0e1ee798e15171191406`, copied byte-identical to
  `configs/janus1/j1f_gates.json`.
- **Statistics:** paired by case, 10 000 bootstrap resamples, one-sided 2.5 % lower bounds.
- **Order:** a fixed sequence.
- **Budget:** at most two candidate looks in the track. J1F-A (with F and T) is the first.

**V, the vessels, on F.** All four must hold:
- the lower bound of Δ decisive macro tF1 is above −0.02;
- no class's mean Δ is below −0.03;
- L3 (reading the scorer's `recall`) holds;
- FP components per case ≤ 1.

**B, the six gated classes, on the reading that ships** (`configs/janus1/j1f_gates.json`):

| Class | recall ≥ | presence agreement ≥ | naming ≥ |
|---|---|---|---|
| D1 | 0.81 | **0.93** | 0.83 |
| D2 | 0.76 | 0.84 | 0.86 |
| OM1 | 0.75 | 0.90 | 0.78 |
| OM2 | 0.60 | 0.81 | 0.78 |
| PDA | 0.89 | 0.97 | 0.90 |
| PLB | **0.90** | **0.95** | 0.92 |

- **Definitions:**
  - recall and naming are pooled over reference **pieces**;
  - presence = centreline ≥ 5 mm;
  - detection = ≥ 50 % of the centreline within 1.5 mm of predicted vessel of any class;
  - naming = strict majority of the covered centreline.
- **Error rates:**
  - a human-level model fails any one class ≤ 16 % of the time under every human model tried, and "< 4 of 6" ≤ 2 %;
  - a model with twice a human's errors is rejected 94 % of the time ([[Janus 1-F Round 2]] §2).
  - F-A27 re-applied F-A15's rule at F-A25's locked counts (97/64/84/40/98/99): D1 presence 0.94 → 0.93 (its
    human-level false-fail 10.3 % → 5.7 %), PLB recall 0.89 → 0.90 and presence 0.94 → 0.95 ([[Janus 1-F Round 3]]).
- **Detection, read as written (F-A35):** a branch drawn for its proximal ~45 % can count as detected; `DECISION.md`
  says so beside B1.

**Verdicts:**

| V | B | Ships |
|---|---|---|
| pass | ≥ 4 of 6 pass | **F** (Janus 1-F.1). Failing classes, Ramus and D3 ship folded into their parent |
| fail | ≥ 4 of 6 pass on T | **T** (Janus 0's four classes by construction) |
| either | < 4 of 6 | Not adopted. Round N+1 chooses the next design (class weights, F3, or a graph namer); no automatic GPU run |

**One look.** Nothing on the locked 100 chooses an epoch, a checkpoint, a reading, a weight or a stop. Locked labels
may be counted for eligibility only.

**If Janus 1-L is adopted first (F-A24, F-A32):**
- **If the lead answers Q-F2-3 "no", or 1-L is not adopted (with its maps on Fir) before `collect` opens the
  ledger:** V_L (F against 1-L's maps) and T_L (G selected by 1-L's map) are reports.
- **If "yes" and 1-L is adopted in time,** T_L is a third pre-registered reading of the same look, and V_L (V's four
  clauses against 1-L's maps, read only after V and B) chooses whose vessels ship:

| V (F vs Janus 0) | V_L (F vs 1-L) | B (≥ 4 of 6) | Ships |
|---|---|---|---|
| pass | pass | on F | **F** |
| pass | fail | on T_L | **T_L** |
| pass | fail | fails on T_L, passes on F | **F**, with "vessels below Janus 1-L" in `DECISION.md` |
| fail | — | on T_L | **T_L** |
| fail | — | fails on T_L, passes on T | **T** |
| any | — | fails on every reading | not adopted |

- `collect` may wait up to 14 days for 1-L's verdict if the lead allows it (Q-F3-1).

## 4. Stage 2 (F-A11, F-A21 to F-A23)

- **Loss:** marginal CE + **leaf-Dice per sample**, smooth 1e-5, **`batch_dice: false` asserted** (`leaf_skip` if
  Janus 0's plans say true).
- **ImageCAS-X background sets, in a band around each host:**
  - LAD and D1–D3 → {bg, S1, S2, S3};
  - RCA → {bg, RMA};
  - proximal RCA (30 mm) → {bg, RMA, SN, Conus};
  - proximal LCx (20 mm from the LM) → {bg, SN};
  - elsewhere → {bg}.
  - Traced-class voxels are never in a set.
- **Band width:** 15 mm until the trainable extended reads re-set each group to its 95th-percentile drawn distance
  (≥ 10 reads), clamped to [8, 25] mm. It is posted with its sha256 before J1F-2.
- **Extended reads:**
  - a complete group's parent is a singleton, otherwise {parent ∪ children} (D47 Q3);
  - a child over its own parent is the child; other overlaps are ignore (D47 Q4; 255 in the scorer, the trainer's ignore value on disk).
- **Heads:** new heads by parent copy from the shipped stage-1 model (S1–S3 ← LAD; SN, Conus, RMA ← RCA).
- **Train a class:**
  - ≥ 30 trainable patients from ≥ 3 sources with ≥ 5 patients each;
  - inter-read agreement ≥ 0.6 on ≥ 10 double-read patients, measured with the scorer of record;
  - after a near-miss failure (count within 1.5× of the line), the line rises to 1.5×.
- **No Job B** unless the lead says so (Q-F2-2).
- **During training: K1r (F-A30).** L1r's statistic on the 20 fit-check training cases at each fit check. Above 0.02
  at the last check, the job writes `LEAK`, and the PM may cancel.
- **J1F-2's look** (the track's second; every bound one-sided 1.25 %):
  1. V′ against the shipped stage-1 model (Janus 0 reported);
  2. B′ on stage 1's shipped classes;
  3. **L1r** (F-A30): ≤ 0.02 of each parent group's reference centreline taken by stage-2 classes, **counting only
     stolen points in 26-connected runs longer than 3 mm** (upper bound);
  4. **L2d** (F-A30): in **≥ 95 of the 100 cases (a point count)**, no stage-2 26-component (≥ 20 voxels) whose
     nearest voxel is more than 30 mm from every other predicted coronary voxel;
  5. S: D35 tiers (decide ≥ 30, report ≥ 20, else counts).
  - Failing V′ or B′: not adopted. A class failing L1, L2 or S ships folded.
  - Reports only: literal L1, L2 and K1, Delta's lumen-core K1, and each class's farthest-voxel distance and
    outside-band volume.
  - The first extended reads re-check 3 mm, 30 mm and 0.02 before J1F-2 is submitted, never after.
- **Scoring set:** D35 in extended mode. It can report S1 at most; SN, Conus and RMA are counts only. Whether the
  sealed pool may be read in extended mode is Q-F2-1.

## 5. Jobs and commands (Fir; the lead runs every job)

**Accounts (F-A34):** GPU jobs `--account=def-aso22_gpu --gpus-per-node=h100:1 --cpus-per-task=12 --mem=280G`; CPU jobs
`--account=def-aso22`. Janus 0 is in `$HOME/janus0-keep` (Step T), with `$SCRATCH/janus0_out` as the fallback.

| Job | What | Waits on | GPU-h |
|---|---|---|---|
| Step T | Done 2026-11-23 (#302): `batch_dice` False, no class-weighted CE, SHA256SUMS posted | — | 0 |
| **1. Compile line** | `grep -c 'Using torch.compile'` over Janus 0's three kept training logs (F-A33) | now | 0 |
| **2. F0-r2** | Split pins and the converter's counts on Fir's own ImageCAS-X copy (F-A26) | now | 0 |
| **3. F-A8 identity** | Janus 0's Fir val-80 predictions re-scored: 0.909 ± 0.003 | now; **before the purge** (reads `$SCRATCH/icx4`) | 0 |
| J1F-A (a1) | `check`, `prep`, train, chunked predict/decode, `collect` | the swe build (F-A36); jobs 1–3 matching; `prep` before ~2026-12-20 (Q-F3-3) | ≈ 30–32 (ceiling 47.7) |
| a2 | Replicate, report only (D47 Q8) | as a1; Q-F3-2 | + ≈ 30 |
| J1F-B | Job B | Q-F2-2 (recommended: not now) | ≈ 22 |
| J1F-2 | Stage 2 | §4's counts; the J1F-2 freeze ([[Janus 1-F Round 3]] §5) | ≈ 15 |

### 1. The compile line (login node, seconds; F-A33)

```sh
K=$HOME/janus0-keep/nnunet_results/Dataset715_ICX4/nnUNetTrainerICX4__nnUNetResEncUNetPlans_60G_iso05__3d_fullres/fold_0
for f in $K/training_log_*.txt; do echo "$(basename $f) $(grep -c 'Using torch.compile' $f)"; done
```

Expected: three lines ending in `0`, so `JANUS0_COMPILE=f`. Every log ≥ 1: `t`. Mixed: the last log's. **Post the
three lines on #303.**

### 2. F0-r2 (login node + one short CPU job, 0 GPU-h; Foxtrot v2 §13)

On `fir.alliancecan.ca`, inside `tmux`:

```sh
module load StdEnv/2023 python/3.11.5
cd $SCRATCH/asclepius && git -C repo fetch origin dev && git -C repo checkout dev && git -C repo pull --ff-only
source $HOME/icx14-venv/bin/activate
J=$SCRATCH/asclepius/repo/experiments/Foxtrot
mkdir -p $SCRATCH/j1f && cd $SCRATCH/j1f
python $J/j1f/split620.py $SCRATCH/icx4/icx $SCRATCH/asclepius/repo/trillium/icx4/sealed_test.json split620.json
python - <<'EOF'
import json, hashlib
d = json.load(open('split620.json'))
for k in ('train620', 'locked100'):
    print(k, hashlib.sha256('\n'.join(sorted(d[k])).encode()).hexdigest())
EOF
srun --account=def-aso22 --time=2:00:00 --cpus-per-task=8 --mem=32G python - <<'EOF'
import json, os, sys, numpy as np, nibabel as nb
sys.path[:0] = [os.path.expandvars('$SCRATCH/asclepius/repo/experiments/Foxtrot/j1f_r2')]
import labels_r2 as L
ids = json.load(open('split620.json'))['train620']
tot = {'d3': 0, 'd4_to_lad': 0, 'other_lcx': 0, 'other_nearest': 0, 'other_ignore': 0}
for c in ids:
    im = nb.load(os.path.expandvars(f'$SCRATCH/icx4/icx/{int(c[1:]) + 1}.coronary.nii.gz'))
    raw = np.asarray(im.dataobj).astype(np.uint8); raw = raw[L.crop(raw, 4)]
    _, info = L.map13(raw, np.array(im.header.get_zooms()[:3], float))
    for k in tot: tot[k] += info[k]
print(tot)
EOF
```

**Expected:**
- `train620 1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152`;
- `locked100 bbd9c687818956e2d5664b06fd8c8bd02ddb031e9b9d08036d59cc0e1a4d5895`;
- `{'d3': 47, 'd4_to_lad': 2, 'other_lcx': 20, 'other_nearest': 1, 'other_ignore': 8}`.

Any difference: stop and tell the PM. **Send back on #303:** the three printed lines.

### 3. The F-A8 identity (one CPU job, 0 GPU-h; Foxtrot v3 §4.1)

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

Expected: decisive macro **0.909 ± 0.003**, each class within 0.01. Otherwise stop; the PM finds the cause before
anything trains. **Post the `summary` line on #303.**

### 4. J1F-A (after the `role:swe` build of `trillium/janus1f`; F-A36)

On `fir.alliancecan.ca`, inside `tmux`:

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

$L check | tee $J1F_WORK/check.txt    # login node: self-tests, pins, F0-r2's counts, versions, SBATCH headers. Post it
$L prep                               # CPU job (def-aso22, 16 cores, 64G, 3:00:00): Dataset 719 = the 620, ignore 13,
                                      # plans moved (-tp = -sp) and checked, fingerprint placed, preprocess only
$L status                             # after prep: plans check and label counts
J1F_RUN=a1 $L train                   # fold 0: two chained GPU links, afterok
J1F_RUN=a2 $L train                   # fold 1, concurrent, its own seed, report only (D47 Q8, Q-F3-2)
$L status                             # s/epoch, epoch, fitcheck.json after epochs 150 and 300, STALL if written
J1F_RUN=a1 $L predict                 # afterok: the locked 100 in 10 chunks; decode F, T, G; delete each chunk's npz
J1F_RUN=a2 $L predict                 # report only
$L collect                            # CPU job: opens the looks ledger first; V on F, B, the verdict; refuses a 2nd run
```

**Every GPU job's header, as the launcher writes it:**

```sh
#SBATCH --account=def-aso22_gpu
#SBATCH --gpus-per-node=h100:1
#SBATCH --cpus-per-task=12
#SBATCH --mem=280G
#SBATCH --time=23:50:00               # each train link (SEGTRAIN_MAX_SECONDS=84000); 6:00:00 for predict
```

**Train, as the launcher submits each link** (a1; a2 is fold 1 with its own seed):

```sh
export nnUNet_compile=$JANUS0_COMPILE SEGTRAIN_CT_WINDOW=off SEGTRAIN_SAVE_EVERY=10 SEGTRAIN_SAVE_PROBABILITIES=0
export SEGTRAIN_MAX_SECONDS=84000
export SEGTRAIN_FINETUNE_FROM=$JANUS0/nnunet_results/Dataset715_ICX4/nnUNetTrainerICX4__nnUNetResEncUNetPlans_60G_iso05__3d_fullres/fold_0/checkpoint_final.pth
export SEGTRAIN_FINETUNE_HEADS=parent_copy:$SCRATCH/asclepius/repo/configs/janus1/j1f_parents.json
unset SEGTRAIN_ITERATIONS SEGTRAIN_EPOCHS
nnUNetv2_train 719 3d_fullres 0 -tr nnUNetTrainer_janus1f -p nnUNetResEncUNetPlans_60G_iso05 $CONTINUE   # "--c" in link 2
```

**Predict, per chunk k = 0..9** (the locked ids sorted, 10 per chunk):

```sh
[ $(df --output=avail -B1G $J1F_WORK | tail -1) -ge 40 ] || { echo "REFUSE: < 40 GB free"; exit 3; }
nnUNetv2_predict -i $J1F_WORK/in_l100/chunk$k -o $J1F_WORK/raw_$J1F_RUN/chunk$k -d 719 -c 3d_fullres \
  -tr nnUNetTrainer_janus1f -p nnUNetResEncUNetPlans_60G_iso05 -f $FOLD -chk checkpoint_final.pth \
  --save_probabilities --disable_tta -npp 2 -nps 2
du -sh $J1F_WORK/raw_$J1F_RUN/chunk$k                 # chunk 0's line is posted; > 40 GB: chunks of 5
python -m janus1f.decode --run $J1F_RUN --chunk $k --probs $J1F_WORK/raw_$J1F_RUN/chunk$k \
  --janus0 $JANUS0/pred_fir --out $J1F_WORK/maps_$J1F_RUN   # F, T, G + marker; deletes the npz, pkl, argmax export
```

**Send back on #303:** `check.txt`; `status` after `prep`, after epoch 20 and after epoch 150 (with `fitcheck.json`);
chunk 0's `du -sh`; `results/DECISION.md`, `results/verdict.json` and `results/looks.json`; the `.out` of any failed
job. Never a volume, a weight file or a per-case locked map.

## 6. Questions with the lead

**Answered (D47):** round 1's Q1–Q9, all as recommended.

**Open ([[Janus 1-F Round 2]] §6 and [[Janus 1-F Round 3]] §6):**

| Q | Topic | Source | Recommendation |
|---|---|---|---|
| Q-F2-1 | Read the 150 sealed pool patients in extended mode? | Crucible v2 | Yes, if the extended classes are scored only inside the seal's single acceptance look, as a report, never deciding stage 2 |
| Q-F2-2 | Run Job B (≈ 22 GPU-h) after J1F-A? | Bridge v2, Delta v2 | Not now; revisit after a near-miss stage-2 failure |
| Q-F2-3 | If 1-L is adopted, may a released 1-F carry 1-L's vessels (T_L)? | Crucible v2, Bridge v2; timing from Bridge v3, Delta v3 | Yes; the rule is written (F-A32). Answer before J1F-A is submitted; it must be on record before `collect` |
| Q-F3-1 | May `collect` wait up to 14 days for 1-L's verdict? | Crucible v3 | Yes, only if Q-F2-3 is yes and 1-L's `collect` is already submitted |
| Q-F3-2 | Release a1 and a2 together (≈ 61–65 GPU-h on `def-aso22_gpu`)? | D47 Q8; Bridge v3, Foxtrot v3 | Yes, once §5's jobs 1–3 match and `check` passes |
| Q-F3-3 | Prioritise the `janus1f` swe build so `prep` runs before the purge (~2026-12-20)? | Crucible v3 | Yes; run jobs 1–3 now regardless; the fallback is a re-fetch of the CTs |

## 7. History

| Round | Holder | Ruling |
|---|---|---|
| 1 | Delta v1, amended (F-A1 to F-A13) | [[Janus 1-F Round 1]] |
| 2 | Delta v2, amended (F-A14 to F-A26) | [[Janus 1-F Round 2]] |
| 3 | Delta v3, amended (F-A27 to F-A36); **stage 1 converged** | [[Janus 1-F Round 3]] |
