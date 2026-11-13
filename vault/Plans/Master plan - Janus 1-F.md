---
aliases: [Master plan - Janus 1-F, Janus 1-F plan]
tags: [plans, master, track-1-F, janus1-f, branches, D44, D45, fir, locked100, partial-labels]
status: living
track: 1-F
round: 1
updated: 2026-11-12
issue: christianGRogers/Asclepius#303
---

# Master plan, track 1-F (Janus 1-F)

**In force: [[Candidates/Janus 1-F/Delta v1|Delta v1]] (track 1-F), as amended by the judge in
[[Janus 1-F Round 1]] (F-A1 to F-A13).**
- The amendments are binding and override the candidate text where they conflict.
- This file is the track's plan.
- The main [[Master plan]] (Delta v10, Round 10) still governs the pool-driven work, D35 and the seal.
- Track 1-L ([[Master plan - Janus 1-L]]) shares the split (L-A1 = F-A1), the vessel guard (H1 = V) and Step T.

**Binding decisions:**
- **D45:** the classes, the split, Fir; the lead runs every job.
- **D44:** the extended classes are optional per read.
- **D8:** ImageCAS-X's lumen.
- **D25, D1, D1b:** the four-class collapse by territory.
- **D22:** ImageCAS-X is not re-annotated.
- **D27/D32:** the seals.
- **D35:** decides pool questions only.
- **D40:** overlaps become ignore.
- **D34:** naming.

**Status: round 1 of at least 3.** Training does not start before round 3 (#303). Step T and F0 can run now.

## In one paragraph

**Janus 1-F is Janus 0 grown into the branches ImageCAS-X traced, then, later, into the ones it did not.**

**Stage 1 (J1F-A):**
- A 13-output nnU-Net: bg, LM, LAD, LCx, RCA, D1, D2, D3, OM1, OM2, Ramus, PDA, PLB.
- Warm from Janus 0. Each branch output is a copy of its parent's, with territory biases lowered by log of the
  territory size, so at step 0 it **is** Janus 0, territory for territory.
- Decoded hierarchically: territory first, then the branch within it.
- 500 epochs on D45's 620, with Janus 0's plans and mirroring off.

**The locked 100** decides with a fixed sequence:
- the vessels must hold Janus 0's line (track 1-L's H1);
- then six branch classes must pass detection and naming lines.
- If 1-F's own vessels fail, the shipped model is **T**: Janus 0's four classes, with 1-F naming the branches inside
  each territory.

**Stage 2** adds S1–S3, SN, Conus and RMA, which ImageCAS-X never traced and so labels as background:
- from extended pool reads;
- through a label-set (marginal) loss;
- only when per-class read counts are met, never on a date.

## 1. Classes and labels (F-A3, F-A4)

| 1-F class | Stage 1 label from ImageCAS-X | Gated on the locked 100? |
|---|---|---|
| LM, LAD, LCx, RCA | same | V (collapsed) |
| D1, D2, OM1, OM2 | same | yes (98, 64, 84, 40 locked cases) |
| PDA, PLB | R-PDA, R-PLA; L-PDA/L-PLA per Q1 | yes (96, 96) |
| Ramus | IM | report (24) |
| D3 | first LAD-side "Other" piece | report (7) |
| (LAD) | later LAD-side "Other" pieces (D4+) | — |
| (LCx) | LCx-side "Other" (OM3+) | — |
| ignore (255) | "Other" touching only the RCA, or nothing (8 pieces on the 620) | — |
| S1–S3, SN, Conus, RMA | **not traced**: background. No head in stage 1 | stage 2, pool reads only |

**Decoding:** the territory is the argmax of the summed probabilities over {bg}, {LM}, {LAD, D1, D2, D3}, {LCx, OM1,
OM2, Ramus} and {RCA, PDA, PLB}; the class is the argmax inside it.

**Four-class collapse for scoring:** by origin.
- D1–D3 → LAD; OM1, OM2, Ramus → LCx.
- A PDA or PLB component goes to the vessel it touches most.
- Under Q1 (C) it goes to the RCA always, with Janus 0's reference relabelled the same way.

## 2. Recipe, J1F-A (F-A2)

| Item | Setting |
|---|---|
| Start | Janus 0 `checkpoint_final.pth` (Dataset715) via A17a's `finetune_load`: non-head tensors strict and bitwise; heads by parent copy; the loader refuses unless territory sums equal Janus 0's within 1e-5 and the hierarchical decode equals Janus 0's argmax |
| Plans | Janus 0's `plans.json` byte-identical (`nnUNetv2_move_plans_between_datasets`, then `nnUNetv2_preprocess`); no fingerprint, no `plan_experiment`; `SEGTRAIN_CT_WINDOW=off`; Dataset 719 |
| Schedule | 500 epochs × 250 iterations, batch 2; 2500-iteration linear warm-up to 1e-2, then poly |
| Loss | DiceCE, unweighted, deep supervision, ignore label 255 |
| Fixed | mirroring off; default augmentation otherwise; uniform sampling; `checkpoint_final` only; `--disable_tta` |
| Validation | fold 0 = the locked 100, display only, never read for a decision or a stop |
| Stall check (F-A5) | at epochs 150 and 300, Dice on 20 fixed **training** cases (smallest sha256(`asclepius-j1f-fitcheck:` + id)); at 150, D1, OM1, PDA or PLB < 0.10 writes `STALL` and the PM may cancel |
| Runs | a1 only; a2 if the lead says yes (Q8), report only |

## 3. The pre-registered decision on the locked 100 (F-A6, F-A7)

**Inputs:**
- **Baseline:** Janus 0's own Fir predictions, at argmax.
- **Scoring:** the A1c scorer (`24441cf8…5254`) with icx4's in-job aortas, which cover all 100. A1a/A1b exclusions
  apply.
- **Statistics:** paired by case, 10 000 bootstrap resamples, one-sided 2.5 % lower bounds.
- **Order:** a fixed sequence.

**V, the vessels, on F.** All four must hold:
- the lower bound of Δ decisive macro tF1 is above −0.02;
- no class's mean Δ is below −0.03;
- track 1-L's L3 recall guard holds;
- FP components per case ≤ 1.

**B, the six gated classes** (D1, D2, OM1, OM2, PDA, PLB), on the reading that ships:
- **B1, detection.** Both must hold:
  - branch-level detection recall ≥ 0.80;
  - presence agreement ≥ ImageCAS-X's inter-observer agreement − 0.05: D1 0.919, D2 0.844, OM1 0.894, OM2 0.825,
    PDA 0.938, PLB 0.912.
- **B2, naming:** naming accuracy ≥ 0.85.

**Verdicts:**

| V | B | Ships |
|---|---|---|
| pass | ≥ 4 of 6 pass | **F**. Failing classes, Ramus and D3 ship folded into their parent |
| fail | ≥ 4 of 6 pass on T | **T** (Janus 0's four classes by construction) |
| either | < 4 of 6 | Not adopted. Round N+1 chooses the next design; no automatic GPU run |

**One look.** Nothing on the locked 100 chooses an epoch, a checkpoint, a reading, a weight or a stop. Locked labels
may be counted for eligibility only.

**Round 2 may change B's numbers before J1F-A is submitted, never after.**

## 4. Stage 2 (F-A11; details are round 2's)

- **Loss:** marginal CE plus leaf-Dice.
- **Label sets:**
  - ImageCAS-X background near the traced tree → {bg, S1–S3, SN, Conus, RMA};
  - a 4-class read's parent → {parent ∪ its children};
  - an extended read's drawn classes are singletons;
  - its parents depend on the "complete" flag (Q3);
  - overlaps → D40's ignore, or the child (Q4).
- **New heads** by parent copy from the shipped stage-1 model.
- **Provisional thresholds:**
  - **Train a class:** ≥ 30 trainable patients from ≥ 3 sources, with inter-read agreement ≥ 0.6 on ≥ 10 patients.
  - **Report a class:** ≥ 20 decision patients.
  - **Decide on or ship a class unfolded:** ≥ 30.

## 5. Jobs and commands (Fir, `def-aso22`; the lead runs every job)

| Job | What | Waits on | GPU-h |
|---|---|---|---|
| **Step T** | Track 1-L's Step T ([[Master plan - Janus 1-L]] §5, Fir part). Its `$KEEP` copy in project space protects both tracks from the scratch purge (~2026-12-20) | now (Q2) | 0 |
| **F0** | Split pins and label-conversion counts on Fir's own ImageCAS-X copy | now | 0 |
| J1F-A | Stage 1 + predict the locked 100 (logits) + F/T scoring + `DECISION.md` | `trillium/janus1f` (swe issue after round 2), `configs/janus1/split-2026-11.json`, Q1 | ≈ 29–31 (ceiling 47.7) |
| a2 | Replicate, report only | Q8 | + ≈ 29 |
| J1F-2 | Stage 2 | §4's counts | ≈ 15 |

### Step T

Use the Fir block in [[Master plan - Janus 1-L]] §5 unchanged. The Trillium half is 1-L's alone.

**Post on #302 and #303:** the three `SHA256SUMS` lines and the three counts (160, 160, 100).

### F0 (login node, 0 GPU-h; Foxtrot v1 §8)

On `fir.alliancecan.ca`, inside `tmux`:

```sh
module load StdEnv/2023 python/3.11.5
cd $SCRATCH/asclepius && git -C repo fetch origin dev && git -C repo checkout dev && git -C repo pull --ff-only
source $HOME/icx14-venv/bin/activate            # icx4's venv: nibabel, scipy, scikit-image via nnU-Net
J=$SCRATCH/asclepius/repo/experiments/Foxtrot/j1f
mkdir -p $SCRATCH/j1f && cd $SCRATCH/j1f
python $J/split620.py $SCRATCH/icx4/icx $SCRATCH/asclepius/repo/trillium/icx4/sealed_test.json split620.json
python - <<'EOF'
import json, hashlib
d = json.load(open('split620.json'))
for k in ('train620', 'locked100'):
    print(k, hashlib.sha256('\n'.join(sorted(d[k])).encode()).hexdigest())
EOF
srun --account=def-aso22 --time=1:00:00 --cpus-per-task=8 --mem=32G \
    python $J/make_labels_1f.py stats $SCRATCH/icx4/icx split620.json labels_1f_stats.json 8
python -c "import json; s=json.load(open('labels_1f_stats.json'))['summary']; print(s['other'], s['cases_with_D3'])"
```

**Expected:**
- `train620 1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152`;
- `locked100 bbd9c687818956e2d5664b06fd8c8bd02ddb031e9b9d08036d59cc0e1a4d5895`;
- `{'other_diag': 50, 'other_marg': 20, 'other_amb': 8, 'd3_from_other': 47, 'd3_set': 1, 'd4_to_lad': 2} 47`.

Any difference: stop and tell the PM.

**Send back on #303:** the three printed lines.

### J1F-A

**Commands are written when round 2 freezes the launcher's spec** ([[Janus 1-F Round 1]] §5, item 8). Its shape is
Delta v1 §9's, with these changes:
- the baseline is Fir's own Janus 0 predictions, not track 1-L's J0;
- decoding is hierarchical, from logits;
- the stall check runs at epochs 150 and 300.

## 6. Questions with the lead ([[Janus 1-F Round 1]] §6)

| Q | Topic | Recommendation |
|---|---|---|
| Q1 | Left-sided PDA/PLB and a circumflex SN: name and four-class collapse (SegQueue 0.18.0 says "always RCA") | (A) Name by course, collapse by origin; change SegQueue's collapse and instruction to match |
| Q2 | Step T now | Yes |
| Q3 | "Branch group complete" flag on extended reads | Yes, per parent group |
| Q4 | Child-in-parent overlaps in extended reads | Train as the child (amends D40 for extended reads only) |
| Q5 | Re-annotate ImageCAS-X for the six untraced classes (D22) | Not now |
| Q6 | D35 patients read in extended mode | Yes; counts only for SN, Conus, RMA |
| Q7 | Trace the six beyond the seed when extended classes are used | Yes, as an instruction for extended reads |
| Q8 | Replicate a2 on Fir | Yes if the allocation allows; report only |
| Q9 | Naming | The read model is Janus 1-F.1; the adopted model is Janus 1-F |

## 7. History

| Round | Holder | Ruling |
|---|---|---|
| 1 | Delta v1, amended (F-A1 to F-A13) | [[Janus 1-F Round 1]] |
