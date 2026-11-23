---
aliases: [Master plan - Janus 1-F, Janus 1-F plan]
tags: [plans, master, track-1-F, janus1-f, branches, D44, D45, D47, fir, locked100, partial-labels]
status: living
track: 1-F
round: 2
updated: 2026-11-23
issue: christianGRogers/Asclepius#303
---

# Master plan, track 1-F (Janus 1-F)

**In force: [[Candidates/Janus 1-F/Delta v2|Delta v2]] (track 1-F), as amended by the judge in
[[Janus 1-F Round 1]] (F-A1 to F-A13) and [[Janus 1-F Round 2]] (F-A14 to F-A26).**
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

**Status: round 2 of at least 3.** Training does not start before round 3 rules the plan converged (#303). Step T and
F0-r2 can run now. Questions Q-F2-1 to Q-F2-3 are with the lead (§6).

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
| ignore (255) | "Other" touching only the RCA, or nothing (8 pieces on the 620) | — |
| S1–S3, SN, Conus, RMA | **not traced**: background. No head in stage 1 | stage 2, pool reads only |

**Converter (F-A18):** Delta's `j1f_labels.py`, with D47 (A) hard-wired and the 255 rule. Expected on the 620: D3 47,
D4 → LAD 2, LCx-side "Other" → LCx 20, nearest 1, ignore 8.

**Decoding F:** the territory is the argmax of the summed probabilities over {bg}, {LM}, {LAD, D1, D2, D3}, {LCx, OM1,
OM2, Ramus} and {RCA, PDA, PLB}. The class is the argmax inside it.

**Decoding T (F-A19):**
- The territory is Janus 0's argmax.
- Inside Janus 0's LCx territory the class runs over {LCx, OM1, OM2, Ramus, **PDA, PLB**}; inside the RCA territory,
  over {RCA, PDA, PLB}.
- T's four classes **are** Janus 0's map, asserted bit-equal.

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
| Plans | Step T's `plans.json` copied, `nnUNetv2_move_plans_between_datasets`, then `nnUNetv2_preprocess` only. **L-A21's plans check** (equal once `dataset_name` and `image_reader_writer` are removed). Janus 0's `dataset_fingerprint.json` placed. No `plan_experiment`, no `extract_fingerprint`. `SEGTRAIN_CT_WINDOW=off`. Dataset 719 |
| Schedule | 500 epochs × 250 iterations, batch 2; 2500-iteration linear warm-up to 1e-2, then poly |
| Loss | DiceCE, unweighted, deep supervision, ignore label 255 |
| Fixed | mirroring off; default augmentation otherwise; uniform sampling; `checkpoint_final` only (`checkpoint_best` never read); `--disable_tta`; `SEGTRAIN_SAVE_EVERY=10`; `SEGTRAIN_MAX_SECONDS` = walltime − 30 min; `nnUNet_compile` as Janus 0's; editable segtrain install |
| Validation | `splits_final.json`: two identical entries, train = the 620, **val = the 20 fit-check training cases**. `perform_actual_validation` is a no-op. **The locked 100 is never validated on** |
| Stall check (F-A5) | at epochs 150 and 300, Dice on the 20 fit-check cases (smallest sha256(`asclepius-j1f-fitcheck:` + id)); at 150, D1, OM1, PDA or PLB < 0.10 writes `STALL` and the PM may cancel. It reads a1 only |
| Runs | a1 = fold 0; a2 = fold 1, concurrent, its own seed, report only (D47 Q8) |
| Predict | locked 100 in chunks of 10, `--save_probabilities --disable_tta`; `decode` writes F and T, then deletes the chunk's npz and nnU-Net's own argmax export. `collect` reads only `decode`'s maps |

## 3. The pre-registered decision on the locked 100 (F-A6, F-A7, F-A15, F-A16, F-A22)

**Inputs:**
- **Baseline:** Janus 0's own Fir predictions, at argmax.
- **Vessel scoring:** the A1c scorer (`24441cf8…5254`) with icx4's in-job aortas, which cover all 100. A1a/A1b
  exclusions apply.
- **Branch scoring:** the scorer of record (F-A16): Atlas's `j1f_scorer.py` definitions, with SegQueue's collapse.
  Its sha256 is posted by round 3.
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
| D1 | 0.81 | 0.94 | 0.83 |
| D2 | 0.76 | 0.84 | 0.86 |
| OM1 | 0.75 | 0.90 | 0.78 |
| OM2 | 0.60 | 0.81 | 0.78 |
| PDA | 0.89 | 0.97 | 0.90 |
| PLB | 0.89 | 0.94 | 0.92 |

- **Definitions:**
  - recall and naming are pooled over reference **pieces**;
  - presence = centreline ≥ 5 mm;
  - detection = ≥ 50 % of the centreline within 1.5 mm of predicted vessel of any class;
  - naming = strict majority of the covered centreline.
- **Error rates:**
  - a human-level model fails any one class ≤ 16 % of the time under every human model tried, and "< 4 of 6" ≤ 2 %;
  - a model with twice a human's errors is rejected 94 % of the time ([[Janus 1-F Round 2]] §2).

**Verdicts:**

| V | B | Ships |
|---|---|---|
| pass | ≥ 4 of 6 pass | **F** (Janus 1-F.1). Failing classes, Ramus and D3 ship folded into their parent |
| fail | ≥ 4 of 6 pass on T | **T** (Janus 0's four classes by construction) |
| either | < 4 of 6 | Not adopted. Round N+1 chooses the next design (class weights, F3, or a graph namer); no automatic GPU run |

**One look.** Nothing on the locked 100 chooses an epoch, a checkpoint, a reading, a weight or a stop. Locked labels
may be counted for eligibility only.

**If Janus 1-L is adopted first:**
- V_L (F against 1-L's maps) and T_L (1-L's territories, 1-F's names) are reports.
- Whether T_L may ship is Q-F2-3.

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
  - a child over its own parent is the child; other overlaps are 255 (D47 Q4).
- **Heads:** new heads by parent copy from the shipped stage-1 model (S1–S3 ← LAD; SN, Conus, RMA ← RCA).
- **Train a class:**
  - ≥ 30 trainable patients from ≥ 3 sources with ≥ 5 patients each;
  - inter-read agreement ≥ 0.6 on ≥ 10 double-read patients, measured with the scorer of record;
  - after a near-miss failure (count within 1.5× of the line), the line rises to 1.5×.
- **No Job B** unless the lead says so (Q-F2-2).
- **During training: K1.** The share of each new class's voxels inside ImageCAS-X's traced lumen, on the 20 fit-check
  cases. Above 0.05 at the last check, the job writes `LEAK`.
- **J1F-2's look** (the track's second; every bound one-sided 1.25 %):
  1. V′ against the shipped stage-1 model (Janus 0 reported);
  2. B′ on stage 1's shipped classes;
  3. L1: ≤ 0.02 of each parent group's reference centreline taken by stage-2 classes;
  4. L2: in ≥ 95 % of cases, no stage-2 voxel more than 30 mm from predicted coronary foreground;
  5. S: D35 tiers (decide ≥ 30, report ≥ 20, else counts).
  - Failing V′ or B′: not adopted. A class failing L1, L2 or S ships folded.
  - Round 3 may change these numbers before J1F-2 is submitted.
- **Scoring set:** D35 in extended mode. It can report S1 at most; SN, Conus and RMA are counts only. Whether the
  sealed pool may be read in extended mode is Q-F2-1.

## 5. Jobs and commands (Fir, `def-aso22`; the lead runs every job)

| Job | What | Waits on | GPU-h |
|---|---|---|---|
| **Step T** | Track 1-L's Step T ([[Master plan - Janus 1-L]] §5, Fir part, with L-A20's additions). Its `$KEEP` copy protects both tracks from the scratch purge (~2026-12-20) | now | 0 |
| **F0-r2** | Split pins and the D47 converter's counts on Fir's own ImageCAS-X copy (F-A26) | now | 0 |
| J1F-A | Stage 1 + chunked predict/decode of the locked 100 + F/T scoring + `DECISION.md` | convergence; the swe issue (F-A12); `configs/janus1/split-2026-11.json`; the scorer hash (F-A16); `j1f_gates.json` (F-A15) | ≈ 29–31 (ceiling 47.7) |
| a2 | Replicate, report only (D47 Q8) | as J1F-A | + ≈ 29 |
| J1F-B | Job B | Q-F2-2 (recommended: not now) | ≈ 22 |
| J1F-2 | Stage 2 | §4's counts | ≈ 15 |

### Step T

Use the Fir block in [[Master plan - Janus 1-L]] §5 unchanged. The Trillium half is 1-L's alone.

**Post on #302 and #303:** what the 1-L block asks for (the four `SHA256SUMS` lines, the three counts 160 / 160 /
100, the `grep -c` counts, the `ls` line, the `nnUNet_compile` line). **For 1-F, also post** the output of this line,
run in the same session after the block (F-A21):

```sh
python3 -c "import json; p=json.load(open('$SCRATCH/janus0_out/nnunet_results/Dataset715_ICX4/nnUNetTrainerICX4__nnUNetResEncUNetPlans_60G_iso05__3d_fullres/plans.json')); print(p['configurations']['3d_fullres'].get('batch_dice'))"
```

Expected: `False`. `True` switches stage 2 to `leaf_skip`; nothing in stage 1 changes.

### F0-r2 (login node + one short CPU job, 0 GPU-h; Foxtrot v2 §13)

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

### J1F-A

**Commands are written by the round that rules the plan converged** ([[Janus 1-F Round 2]] §5, item 3). The shape is
Delta v2 §8.1:
- modes `check`, `prep`, `train`, `predict`, `collect`, `status`;
- with F-A16 to F-A20's corrections.

## 6. Questions with the lead

**Answered (D47):** round 1's Q1–Q9, all as recommended.

**Open ([[Janus 1-F Round 2]] §6):**

| Q | Topic | Source | Recommendation |
|---|---|---|---|
| Q-F2-1 | Read the 150 sealed pool patients in extended mode? | Crucible | Yes, if the extended classes are scored only inside the seal's single acceptance look, as a report, never deciding stage 2 |
| Q-F2-2 | Run Job B (≈ 22 GPU-h) after J1F-A? | Bridge, Delta | Not now; revisit after a near-miss stage-2 failure |
| Q-F2-3 | If 1-L is adopted, may a released 1-F carry 1-L's vessels (T_L)? | Crucible, Bridge | Yes in principle; round 3 writes the rule before J1F-A is submitted |

## 7. History

| Round | Holder | Ruling |
|---|---|---|
| 1 | Delta v1, amended (F-A1 to F-A13) | [[Janus 1-F Round 1]] |
| 2 | Delta v2, amended (F-A14 to F-A26) | [[Janus 1-F Round 2]] |
