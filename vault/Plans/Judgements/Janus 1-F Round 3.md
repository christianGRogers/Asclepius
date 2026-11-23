---
tags: [plans, judgement, track-1-F, round3, janus1-f, D44, D45, D47, D49, D50, fir, locked100, partial-labels, gates, scorer, swe-spec, convergence]
track: 1-F
round: 3
updated: 2026-11-23
issue: christianGRogers/Asclepius#303
---

# Janus 1-F, Round 3 ruling

This is the third round of track 1-F (D45, #303): the training plan for **Janus 1-F**, run by the lead on **Fir**.
The five round-3 candidates are in `Candidates/Janus 1-F/`:
- [[Candidates/Janus 1-F/Atlas v3|Atlas v3]];
- [[Candidates/Janus 1-F/Bridge v3|Bridge v3]];
- [[Candidates/Janus 1-F/Crucible v3|Crucible v3]];
- [[Candidates/Janus 1-F/Delta v3|Delta v3]] (the holder);
- [[Candidates/Janus 1-F/Foxtrot v3|Foxtrot v3]].

Each candidate's Experiments note and its code under `experiments/<advocate>/j1f_r3/` were read with it.

**Binding inputs:**
- D45 to D50, D47 above all;
- [[Janus 1-F Round 1]] (F-A1 to F-A13) and [[Janus 1-F Round 2]] (F-A14 to F-A26), its §5 items and its §6
  questions;
- [[Janus 1-L Round 2]] (L-A13 to L-A25), where the tracks share mechanics.

**Facts in since round 2:**
- **Step T is done on both clusters** (#302, 2026-11-23). Janus 0's 3d_fullres plans have `batch_dice: False`. No
  training log shows class-weighted CE (0 in each of the three logs, dated 2026-10-18, 10-19 and 10-20), and
  `ce_class_weights.json` is absent. The purge-safe copy is `$HOME/janus0-keep` on Fir. `nnUNet_compile` is not yet
  confirmed from Fir's own files.
- **F0-r2 and Job 0 (track 1-L) have not run.**
- **The lead has not answered Q-F2-1 to Q-F2-3.**

**What the judge ran.** Every number this ruling leans on was re-run on CPU in this container (§2). Two new scripts:
- `experiments/Judge/j1f_r3/l2_forms.py` tests the five proposed L2 forms on a correct stage-2 branch drawn with a
  gap;
- `experiments/Judge/j1f_r3/rerun_rows.py` re-runs each advocate's per-case function on hash-chosen training cases
  and compares the rows with the committed ones.

The judge also wrote the gate file of record, `experiments/Judge/j1f_r3/j1f_gates.json` (F-A27), with its test.
- **Data read:** the ImageCAS-X segmentations of the **620 training cases only**, fetched by Atlas's
  `fetch_620.py` (it asserts the 620's pin `1350cb1f…1152` and fetches no other member); and, for the locked 100,
  **counts only**, from the committed census rows (`experiments/Delta/j1f_r1/census.json`): no locked label volume
  was opened.
- **Not read:** no locked-100, sealed, quality-0 or D60 label or CT, no TotalSegmentator twin, no pool read, no model
  output.
- Nothing ran on Fir, SciNet or Trillium.

**This round rules stage 1 (J1F-A, with a2) converged**, on the conditions in §3.10. Stage 2 (J1F-2) stays
provisional, as F-A22 allows.

## 0. Where the five agree

Nobody needs to argue these points again.

- **The scorer counts what F-A15 was simulated on.** Each advocate amended Atlas's round-2 scorer with SegQueue's
  collapse, ran it over all 620, and found the reference pieces equal to `census_r2.jsonl` case for case (piece
  count, voxels, length to 0.01 mm). Round 2's §7 trigger "the per-piece counts differ" does not fire.
- **SegQueue's collapse on the 620:** 0 voxels off D25 outside "Other" and 255; 1,296 PDA/PLB components (1,203 to the
  RCA, 93 to the LCx), 0 fallbacks. SegQueue counts **face** contact, so on a prediction a branch that meets its
  parent only along an edge falls back to the RCA, counted. `collect` prints the count beside V (F-A17).
- **The converter's line holds on the 620:** `{'d3': 47, 'd4_to_lad': 2, 'other_lcx': 20, 'other_nearest': 1,
  'other_ignore': 8}`, by four independent implementations.
- **Step T changes nothing in the recipe.** No class-weighted CE, so J1F-A's unweighted DiceCE is Janus 0's loss.
  `batch_dice` is False, so stage 2 keeps per-sample leaf-Dice and `leaf_skip` is never built.
- **GPU jobs on Fir use `--account=def-aso22_gpu`**, with explicit cores and memory; CPU jobs stay on `def-aso22`.
- **The locked 100's npz is 13 float32 channels at native size** (nnU-Net 2.8.1 `export_prediction.py` l. 100), up to
  3.75 GB raw per case. A chunk of 10 is budgeted at ≤ 38 GB (37.5 GB at the 620's largest grid).
- **T and T_L need name maps.** F-A20 deletes the probabilities chunk by chunk, so `decode` must keep 1-F's
  within-territory names (Atlas's NAMES, Crucible's N, Delta's within-group maps, Foxtrot's G).
- **T_L's verdict rule**, if the lead says yes to Q-F2-3, is the same table in all five (§3.7). It sits inside J1F-A's
  one look.
- **Q-F2-1 and Q-F2-2 do not touch J1F-A.** Q-F2-3 touches only what its one look can ship.
- **Stage 2 as ruled false-fails a correct model on at least one of L1, L2 and K1** (Atlas, Bridge, Delta and
  Foxtrot; Crucible on L1's and L2's literal forms). **"≥ 95 % of cases" in L2 must be a point count**: with a
  one-sided 1.25 % Clopper–Pearson bound, 99 clean cases of 100 give 0.938 and fail (Bridge, Crucible, Delta,
  Foxtrot).
- **Stage 1 is ready to rule converged** (all five).

## 1. Ruling: Delta v3 keeps the plan, as amended (F-A27 to F-A36)

**[[Candidates/Janus 1-F/Delta v3|Delta v3]] is the plan in force for track 1-F**, on top of F-A1 to F-A26 and D47.
It keeps the holder's seat for three reasons.
1. **It is the only candidate that found both nnU-Net defects the spec would have hit** (§4.2):
   - the ignore label must be **13** on disk (Bridge found this too);
   - **the locked 100 must not be in Dataset 719 at all.** Delta v2, Bridge v3 and Crucible v3 all put the locked
     100's images (Crucible: images and labels) into the training dataset. `nnUNetv2_preprocess` would read and
     write them, and any later plan step or stray fold would find them.
2. **Its plans check is pinned to Step T's posted hashes** (`plans_check.py`), with `-tp` equal to `-sp`,
   `batch_dice` False asserted, and the fingerprint byte-identical.
3. **Its re-definitions of L1 and K1 measure the right thing** (stolen trunk runs; the lumen core), and its
   `L2_rule_table` is the clearest statement of why L2's 95 % must be a point count.

**Its weak points, fixed by amendment:**
- **Its scorer drops `stage1_labels`** and keeps the converter in a separate hashed file. Two hashed functions would
  have to stay equal (F-A28 keeps one: the scorer's).
- **Its L2′ ("touching no predicted voxel and > 30 mm from the tree")** is replaced by Foxtrot's L2d, which is
  defined the same way on what matters and is simpler to state (F-A30).
- **Its K1′ (lumen core, 0.10)** works, but the training flag and the look's theft gate then measure different
  things. Foxtrot's K1r is L1r on the fit-check 20 (F-A30).
- **Its `nnUNet_compile` rule** ("Fir's own `job_body.sh` if found") cannot be met: the file is not on Fir (#302).
  The training logs answer it (F-A33).
- **Its GPU headers ask for 96 G**; icx4's Fir values, which trained Janus 0, are 12 cores and 280 G (F-A34).

**What the others contribute:**
- **Atlas v3:**
  - **the scorer file of record** (F-A28), with the pooled statistics and the gate arithmetic inside the hashed
    file;
  - **P-r3-1: F-A15's own rule, re-applied at F-A25's locked counts, moves three cells** (F-A27). Nobody else ran
    the rule on the counts of record;
  - the repository history of `nnUNet_compile` (F-A33);
  - the clearest statement that literal L2 is either vacuous or wrong.
- **Bridge v3:**
  - **the ignore value 13**, from nnU-Net 2.8.1's `LabelManager` (F-A29);
  - L2's Clopper–Pearson arithmetic (0.938 at 99 of 100);
  - the junction-painting model that shows why K1 as ruled fires on correct short branches (D47 Q4);
  - `check` re-prints F0-r2's lines.
- **Crucible v3:**
  - **`prep` must run before the Fir purge**, because it reads `$SCRATCH/icx4` (§4 and Q-F3-3);
  - the 14-day window for 1-L's verdict (Q-F3-1);
  - the per-component form of L2 and the nearest-label form of L1, which point the same way as the adopted forms.
- **Foxtrot v3:**
  - **L1r, K1r and L2d** (F-A30);
  - **the compile `grep` over Janus 0's kept training logs**, with its outcome table (F-A33);
  - the G maps (F-A31) and the F-A8 identity command (§4);
  - the detection report: a branch drawn for its proximal ~45 % counts as detected (F-A35);
  - checks for library drift on Fir (`check` prints the venv's versions and re-runs the scorer's tests).

### Binding amendments (track 1-F, Round 3)

F-A1 to F-A26 stay in force except where these change them. They override the candidate text where they conflict.

**F-A27. B's lines of record (amends F-A15; Atlas P-r3-1).**

| Class | B1 recall ≥ | B1 presence agreement ≥ | B2 naming ≥ |
|---|---|---|---|
| D1 | 0.81 | **0.93** | 0.83 |
| D2 | 0.76 | 0.84 | 0.86 |
| OM1 | 0.75 | 0.90 | 0.78 |
| OM2 | 0.60 | 0.81 | 0.78 |
| PDA | 0.89 | 0.97 | 0.90 |
| PLB | **0.90** | **0.95** | 0.92 |

- **Why three cells move.** F-A15 is "the 5th percentile of a human-level model's statistic, worst of nine
  scenarios, rounded down", and it was run at round 1's locked counts (98/64/84/40/96/96). F-A25 made 97/64/84/40/98/99
  the counts of record (D47 (A), 5 mm). Run at those counts, the same rule gives D1 presence 0.93, PLB recall 0.90 and
  PLB presence 0.95, and the other 15 cells unchanged. The judge re-derived it from the committed census counts
  (§2).
- **What it buys.** With the frozen 0.94, a human-level D1 fails up to 10.3 % of the time, twice the rule's ≈ 5 %.
  With 0.93 it is 5.7 %. PLB tightens (worst false-fail 3.0 % → 5.2 %), which F-A6 allows before submission. The
  verdict's false-fail stays ≤ 0.4 %, and its power is unchanged within simulation noise (§2).
- **F-A25's "within the rounding of the lines" is withdrawn for D1 presence.** It is a binomial line at n ≈ 100, where
  one case is one point.
- **The file of record is `experiments/Judge/j1f_r3/j1f_gates.json`, sha256
  `198b3b158098d846358971ad8a85f22eda7f9a76c00f0e1ee798e15171191406`**, in the scorer of record's format
  (`k_of_6: 4`). Its test (`test_gates.py` → `test_gates.out`) checks OM2 recall 59/100 fails and 60 and 61 pass,
  each moved cell's edge (D1 presence 92 fails, 93 passes; PLB recall 89/90; PLB presence 94/95), 5 of 6 passes,
  3 of 6 fails, and a class with no detected piece fails.
- The swe copies it byte-identical to `configs/janus1/j1f_gates.json`. The five advocates' gate files (`c14190cb…`,
  `16ce8954…`, `b4b88e73…`, `09ddb06f…`, `b268a2fc…`) are superseded.

**F-A28. The scorer of record (settles §5 item 1; amends F-A16 and F-A18).**
- **The file is Atlas's `experiments/Atlas/j1f_r3/j1f_scorer.py`, sha256
  `5221032f3dc086d686b63fa946149a215ac00738a87fd9669d7faa15962b2e5b`.** The swe copies it byte-identical to
  `trillium/janus1f/lib/j1f_scorer.py`. Both sit three directories below the repository root, so its pinned imports
  (`src/segtrain/tf1.py` `24441cf8…5254`, `src/segqueue14/labels.py` `5f69b5be…0a4b`) resolve unchanged and the hash
  does not move.
- **Why Atlas's file, not Foxtrot's (`50826b26…8252`).** Both carry the same scoring definitions and SegQueue's
  collapse, and both pass their tests here. The difference is what the hash covers:
  - Atlas's file holds `aggregate` (pooled per-piece recall and naming, per-case presence agreement, as exact
    fractions) and `gate` (inclusive lines, "≥ 4 of 6"). So the hash that `collect` checks covers the decision
    arithmetic too;
  - Foxtrot's decision layer is `gates.py`, which none of its four pins covers;
  - F-A16 named Atlas's file; Atlas's edit is the smallest that adds the decision layer.
  - Bridge's (`7e6875a3…`), Crucible's (`c2786b2e…`) and Delta's (`d615c7e7…`) are equivalent amendments and are
    superseded.
- **One converter (amends F-A18).** The scorer's `stage1_labels` is **the** ImageCAS-X → 1-F converter: `prep` writes
  Dataset 719's labels with it, and `collect` builds the locked references with it. It equals Delta's map with D47 (A)
  hard-wired and F-A3's 255 rule on every voxel of the 620 (Foxtrot, against `labels_r2.map13`; 0 voxels differ), and
  it prints the converter line. Delta's `j1f_labels.py` is not a second hashed converter.
- **Its tests**, on training fixtures only, are `test_scorer.py` (35 checks: Delta's 30 on Delta's six cases, Atlas's
  five real-case perturbations, the synthetic self-test) and the judge's `test_gates.py`.
- **`check` also prints the venv's numpy, scipy and scikit-image versions and re-runs `test_scorer.py` on Fir**
  (Foxtrot). A skeleton that moves with a library version stops `check`, not `collect`.

**F-A29. Dataset 719 (amends F-A2, F-A3 and F-A20; Bridge, Delta).**
- **Ignore is 13 on disk.** nnU-Net 2.8.1's `LabelManager` asserts `ignore_label == max(labels) + 1`
  (`label_handling.py` l. 40–42), and `verify_dataset_integrity` asserts consecutive labels. `dataset.json` reads
  `{"background": 0, …, "PLB": 12, "ignore": 13}`. `prep` writes the converter's 255 as 13. The scorer keeps 255
  (`collect` builds references with `stage1_labels` directly). This is also segtrain's own convention
  (`ignore = n_classes + 1`, `src/segtrain/plans.py`).
- **Dataset 719 holds the 620 only.** The locked 100's CTs are linked into a predict input folder by `predict`; their
  labels are read only by `collect`. A self-test links one locked id into `imagesTr` and must refuse.
- **Plans:** Step T's `plans.json` placed as `Dataset715_ICX4/nnUNetResEncUNetPlans_60G_iso05.json`;
  `nnUNetv2_move_plans_between_datasets -s 715 -t 719 -sp nnUNetResEncUNetPlans_60G_iso05 -tp
  nnUNetResEncUNetPlans_60G_iso05`; `plans_check.py` (L-A21's check, Step T's sha256 `b7178bbc…3cc2` and fingerprint
  `e41c772f…7e05`, `batch_dice` False).
- **Self-tests added:** a label file with a 255 refuses; `"ignore": 255` refuses; `"ignore": 13` builds nnU-Net's
  `LabelManager`.

**F-A30. Stage 2's leakage gates (amends F-A22; settles §5 item 5).** The numbers stay; three measures change.

| Gate | As ruled (F-A22) | Ruled now | Line |
|---|---|---|---|
| **L1r**, theft | share of each parent group's reference centreline predicted as a stage-2 class | the same, **counting only stolen centreline points in 26-connected runs longer than 3 mm** (Foxtrot's `runs`; Delta's L1′) | ≤ **0.02**, one-sided 1.25 % upper bound, pooled |
| **L2d**, far paint | no stage-2 voxel > 30 mm from predicted coronary foreground, in ≥ 95 % of cases | **no stage-2 26-component (≥ 20 voxels) whose nearest voxel is > 30 mm from every other predicted coronary voxel** (any class, other stage-2 components included) | **≥ 95 of the 100 cases, a point count** |
| **K1r**, training flag | share of a stage-2 class's voxels inside ImageCAS-X's traced lumen, fit-check 20, > 0.05 | **L1r's statistic on the 20 fit-check training cases**, at each fit check | `LEAK` above **0.02** at the last check; the PM may cancel |

- **Why L1r.** A correct model trained child over parent (D47 Q4) paints each ostium over its parent. Literal L1 then
  measures ostium thickness: three correct septals take 0.0166 of the LAD group at r = 0.6 mm (pass) and 0.0225 at
  r = 0.75 mm (false-fail 100 %) (Foxtrot); one voxel of ostium bleed fails the LCx 98 % of the time (Delta). Ostium
  runs are under 3 mm (longest 2.8 mm at one voxel, Delta); a model that calls 10 mm of LAD a septal still takes 0.142
  under L1r, seven times the line (Foxtrot's thief).
- **Why L2d.** Literal L2 measures a branch's length: a correct straight branch longer than ≈ 30 mm crosses it in every
  case (Bridge, Delta, Foxtrot, Atlas, Crucible). L2d measures a gap. It is the only one of the five component forms
  that also passes **a correct branch the model draws in pieces** (the judge's check, §2): Bridge's L2′ (islands
  > 5 mm from stage-1 foreground) fails a branch drawn with a 3 mm gap in most cases, because the distal piece is
  measured against the trunk it left, not the piece it continues.
- **Why K1r.** K1 as ruled is the ostial overlap over the branch's volume, so it falls as 1/length: a correct septal
  ≤ 20 mm writes `LEAK` at every radius tried (Foxtrot), and at 30 mm four of six classes do so 61–99 % of the time
  (Bridge). Atlas and Crucible found K1 safe (≤ 0.02 at a one- or two-voxel bleed) because their stand-ins are
  ImageCAS-X's D/OM/PDA/PLB branches, median centreline 38–56 mm per class (scorer of record, 620); Delta's same stand-ins with the bleed confined to the parent
  already fail 21 % of the time. Septals, the SN and the conus can be short, and D47 Q4 trains their ostia over the
  parent. K1r is 0 on every correct septal and 0.137 on the thief. One statistic then serves training (K1r)
  and the look (L1r).
- **Reports beside them, never deciding:** literal L1, L2 and K1; Delta's lumen-core K1′; each stage-2 class's
  farthest-voxel distance and outside-band volume (K3).
- **Still provisional.** The stand-ins are ImageCAS-X's D/OM/PDA/PLB and synthetic tubes. The first extended reads
  re-check 3 mm and 30 mm before J1F-2 is submitted, as they re-set the band (F-A21), never after.

**F-A31. Decode keeps name maps (amends F-A20; Atlas P-r3-3, Crucible, Delta, Foxtrot).**
- Per locked case, `decode` writes **F**, **T** and **G**: three uint8 maps holding the argmax within {LAD, D1, D2, D3},
  within {LCx, OM1, OM2, Ramus, PDA, PLB} and within {RCA, PDA, PLB} (F-A19's sets), at every voxel, on the npz's grid.
  Then it deletes the chunk's npz, pkl and nnU-Net's own argmax export, and writes a marker with every map's sha256.
- **T is G selected by Janus 0's territory**; its four classes are Janus 0's file, asserted bit-equal. `collect`
  rebuilds T from G and Janus 0's map and checks it byte for byte.
- **T_L is G selected by Janus 1-L's shipped map**, under the same assertion. So T_L needs no probabilities and no
  re-prediction.
- G is not sparsified (Crucible's 1 − p_bg ≥ 1e-3 mask is not used): 1-L's foreground may reach where 1-F's background
  is confident, and T_L must still name it.

**F-A32. T_L's verdict rule, in force only if the lead answers Q-F2-3 "yes" (settles §5 item 6; amends F-A24).**
- **When it applies:** Janus 1-L is **adopted** (its own `DECISION.md` says so) and its 100 shipped locked-100 maps are
  on Fir (by Step T's tar route, sha256 posted on #303, all 100 on Janus 0's grid) **before J1F-A's `collect` opens the
  looks ledger**. The ledger records whether the rule applies. Otherwise F-A24 stands: V_L and T_L are reports, and a
  1-L adopted after `collect` gets T_L as a report only.
- **The sequence** (V and B as ruled; V_L is V's own four clauses with 1-L's maps as the baseline, one-sided 2.5 %,
  read only after V and B):

| V (F vs Janus 0) | V_L (F vs 1-L) | B (F-A27, ≥ 4 of 6) | Ships |
|---|---|---|---|
| pass | pass | on F | **F** |
| pass | fail | on T_L | **T_L** |
| pass | fail | fails on T_L, passes on F | **F**, with "vessels below Janus 1-L" in `DECISION.md` |
| fail | — | on T_L | **T_L** |
| fail | — | fails on T_L, passes on T | **T** |
| any | — | fails on every reading | not adopted |

- **It is one look.** F, T and T_L are pre-registered readings of one network's single prediction, named in the
  ledger before anything is scored. V_L chooses which already-adopted vessels ship; it adopts nothing new. 1-L's maps
  were scored by 1-L's own look.
- The rule is Atlas's `verdict.py`, which passes its self-test here; the swe ports it into `collect`.

**F-A33. `nnUNet_compile` (amends F-A20's "as Janus 0's"; settles §5 item 7).**
- **The lead reads it from Janus 0's kept training logs** (§4, job 1). nnU-Net 2.8.1 prints `Using torch.compile...`
  whenever it compiles (`nnUNetTrainer.py` l. 246), so the count is the direct record of what Janus 0 ran.

| `grep -c 'Using torch.compile'` over the three logs | `JANUS0_COMPILE` for J1F-A and a2 |
|---|---|
| 0 in every log (expected) | `f` |
| ≥ 1 in every log | `t` |
| mixed | the last log's (the link that wrote `checkpoint_final`) |

- **The repository agrees with "0".** `trillium/icx4/lib/job_body.sh` exports `nnUNet_compile=f` from its first
  commit (`2de3f2f`), which reached dev on 2026-10-17 by #31's merge (`8021d4c`) and was never changed
  (`git log -S nnUNet_compile`). Janus 0's logs start on 2026-10-18. #302's note that the file "reached dev on
  2026-10-29" is not what dev's history shows. The `grep` still decides, because Fir's checkout may have differed.
- `check` refuses an unset `JANUS0_COMPILE` and prints the value. Compile mode moves speed and float order only;
  V compares against Janus 0's prediction files, so it cannot move the baseline.

**F-A34. Fir's job headers and paths (amends F-A10 and the master plan §5).**
- **GPU** (train links, predict): `--account=def-aso22_gpu --gpus-per-node=h100:1 --cpus-per-task=12 --mem=280G`,
  `--time=23:50:00` per train link (`SEGTRAIN_MAX_SECONDS=84000`), `--time=6:00:00` for predict. These are icx4's Fir
  values (`trillium/icx4/icx4` l. 232–234), which trained Janus 0.
- **CPU** (`prep`, `collect`, F0-r2, the identity check): `--account=def-aso22`, `--cpus-per-task=16 --mem=64G`.
- **`JANUS0=$HOME/janus0-keep`** (where Step T kept it), falling back to `$SCRATCH/janus0_out`; `sha256sum -c
  SHA256SUMS` before every mode.
- **`predict` refuses with less than 40 GB free** before a chunk, and writes `du -sh` of chunk 0's npz before deleting
  it (posted; chunks of 5 if it exceeds 4 GB per case).

**F-A35. Detection, read as written (report; Foxtrot).** A reference piece is detected when ≥ 50 % of its centreline
lies within 1.5 mm of predicted vessel. A branch drawn for its proximal ~45 % plus the tolerance can therefore count
as detected (Foxtrot: 3 of 6 pieces at 40 %). `DECISION.md` says so beside B1. Nothing changes.

**F-A36. Stage 1 is converged; the `role:swe` issue is filed now (F-A12).**
- **The spec is Delta v3 §4 as amended by F-A27 to F-A35**, with:
  - Atlas v3 §2.4's and Foxtrot v3 §5.3's self-tests (F-A19's T test with the old LCx set as the broken fixture;
    F-A20's val test with a locked id as val; the G round trip; chunk hygiene);
  - Bridge v3 §4's F0-r2 re-print in `check`;
  - the refusals of Delta v3 §4.5 plus an unset `JANUS0_COMPILE`, a 255 or a locked id in Dataset 719, and a
    scorer, gate-file or `labels.py` hash that differs from F-A27/F-A28.
- **The four hashes `collect` pins:** scorer `5221032f…2e5b`, gates `198b3b15…1406`, `labels.py` `5f69b5be…0a4b`,
  `tf1.py` `24441cf8…5254`.
- **Conditions before money is spent** (none is a plan choice; each has a stop rule):
  1. F0-r2's three lines match (F-A26). Otherwise stop.
  2. The compile line is posted (F-A33).
  3. The F-A8 identity reproduces 0.909 ± 0.003, each class within 0.01. Otherwise stop.
  4. `check` passes on Fir.
- **Before J1F-A's `collect`:** the lead's answer to Q-F2-3 is on record (it decides whether F-A32 applies).

**Recorded only:**
- D50 does not reach 1-F. Job 0's place changes nothing here: V's baseline is Fir's own Janus 0 predictions, kept
  by Step T (100 of 100).
- Q-F2-1 and Q-F2-2 change nothing in stage 1. Their consequences for stage 2 are written in §3.8.
- Committed when released: a1 ≈ 29–31 GPU-h, a2 the same, predict ≈ 1–1.5 per run, so **≈ 61–65 GPU-h** on
  `def-aso22_gpu` (ceiling ≈ 98).

## 2. Scorecards

Scores are out of 5: (a) reasoning, (b) evidence including spot-checks, (c) fit to D44–D50, the earlier amendments
and Fir, and (d) risk and cost.

| Candidate | (a) Reasoning | (b) Evidence | (c) Fit | (d) Risk/cost | Verdict |
|---|---|---|---|---|---|
| **Delta v3** | 4.5. Answers every item; each re-definition keeps the ruled number and says what it now measures. Weak: two hashed converters; its compile rule waits on a file that does not exist on Fir | 5. 37/37 checks; the census and summary re-derive byte-identically; per-case rows re-run equal (below); reference code for every 1-F test | 5. The only spec that keeps the locked 100 out of Dataset 719; plans pinned to Step T's hashes | 4.5. 96 G headers below icx4's 280 G | **Track 1-F's plan**, as amended |
| **Atlas v3** | 5. P-r3-1 applies the line rule to the counts of record, which F-A25 had waved off; the repository history of the compile flag | 5. `gate_refreeze` re-runs byte-identically, and the three moved cells move again under a different case order; the scorer self-test and `test_gates` pass | 4.5. Keeps 255 on disk (the nnU-Net defect missed); the locked 100 not separated from Dataset 719 explicitly | 5. 0 extra GPU | **Scorer of record (F-A28), lines (F-A27)** adopted |
| **Foxtrot v3** | 5. The sharpest stage-2 analysis: child-over-parent ostia, the run filter, a gap measure, one statistic for training and the look; the compile `grep` | 5. Stage-2 and 620 summaries re-derive byte-identically from its rows; rows re-run equal; 51 scorer checks; `decode_ref` self-test | 4.5. Keeps 255 on disk; decision layer outside its pinned files | 5. 0 extra GPU | **L1r, L2d, K1r (F-A30), G (F-A31), the compile rule (F-A33), the identity command** adopted |
| **Bridge v3** | 4.5. The ignore-13 defect and L2's bound arithmetic are exact. Weak: L2′'s 5 mm fails a correct branch drawn in pieces; it repeats #302's mistaken date for `job_body.sh` | 4. Scorer, gates and decode self-tests pass. Its 620 and stage-2 per-case rows are kept off the repository, so its summaries could not be re-derived; its findings are corroborated by Delta and Foxtrot | 4. Puts the locked 100's images in Dataset 719 | 5. 0 extra GPU | **Ignore = 13 (F-A29)**, L2's point count and the junction model adopted; L2′ and K1′ not adopted |
| **Crucible v3** | 4. Clear item-by-item answers; the purge deadline for `prep`; the 1-L window. Weak: K1 kept on the evidence of long D/OM stand-ins, where an ostial overlap is a small share; short branches trained child over parent (D47 Q4) fail it | 4.5. Scorer, gates and decode self-tests pass; its 620 summary re-derives byte-identically; rows re-run equal | 3.5. Keeps 255 on disk (training would die at step one); the locked 100's labels in Dataset 719 | 4.5. 0 extra GPU | **The purge deadline and the 14-day window (Q-F3-1, Q-F3-3)** adopted; its L1 and L2 forms superseded by the equivalent adopted ones |

### Spot-checks this round

**Hashes and self-tests (no data):**

| File | sha256 | Self-test here |
|---|---|---|
| Atlas `j1f_scorer.py` | `5221032f…2e5b` | `selftest ok`; `test_gates ok`; `decode.py selftest ok` (a plain argmax moves 9.8 % of voxels across territories); `verdict.py selftest ok` |
| Bridge `j1f_scorer.py` | `7e6875a3…ff78` | `selftest ok`; `test_gates.py` ALL PASS; `decode_ref.py` ALL PASS |
| Crucible `j1f_scorer.py` | `c2786b2e…a03e` | `selftest ok`; `test_gates.py` and `decode_ref.py selftest` ALL PASS |
| Delta `j1f_scorer.py` | `d615c7e7…d808` | `selftest ok`; `j1f_gate`, `j1f_decode`, `plans_check`, `j1f_labels` selftests ok |
| Foxtrot `j1f_scorer.py` | `50826b26…8252` | `selftest ok`; `gates.py selftest ok`; `decode_ref.py selftest ok` |
| `src/segqueue14/labels.py`, `src/segtrain/tf1.py` | `5f69b5be…0a4b`, `24441cf8…5254` | as pinned |
| Judge `j1f_gates.json` | `198b3b15…1406` | `test_gates ok` against the scorer of record |

**The three F-A27 cells.**
- `Atlas/j1f_r3/gate_refreeze.py check_620.jsonl` re-ran here: stdout and json **byte-identical** to the committed
  `gate_refreeze.out` and `.json`.
- Re-run on round 2's `census_r2.jsonl` (the same pieces in a different case order, so a different random stream),
  the rule moves **the same three cells to the same values**. The false-fail of the frozen D1 0.94 is 10.25 % in both
  orders; of the re-derived 0.93, 5.65 %.
- **F-A25's counts re-derived from counts only** (`Delta/j1f_r1/census.json`, the locked rows' centreline lengths,
  no volume opened): D1 97, D2 64, OM1 84, OM2 40, PDA 98, PLB 99 at 5 mm.

**The 620 numbers.**
- Each advocate's summariser, re-run on its committed per-case rows, reproduces its committed summary
  **byte-identically**: Atlas `summary_620.json`, Crucible `summary620.json`, Delta `census620_summary.json`,
  Foxtrot `pass_summary.json` and `stage2_summary.json`. Bridge's rows are not in the repository.
- **Per-case rows re-run** (`Judge/j1f_r3/rerun_rows.py`, the 6 training cases with the smallest
  sha256(`asclepius-j1f-r3-judge-rows:` + id)): ROWS_RESULT.

**L2 forms on a correct branch drawn with a gap** (`Judge/j1f_r3/l2_forms.py` → `l2_forms_summary.json`; the
120 training cases with the smallest sha256(`asclepius-j1f-r3-judge-l2:` + id); stand-ins D2 / OM2 / PLB-to-RCA,
relabelled as one stage-2 class; a gap of 3 mm or 8 mm cut at half the branch's geodesic length; false-fail = share of
2 000 random 100-case sets with fewer than 95 clean cases):

L2_TABLE

**Not re-run:** Bridge's `stage2_sim.py` and `run620.py` (their per-case rows are not committed, and the 120-case
sweep is a few CPU-hours); Delta's `npz_size.py` and the other npz estimates (synthetic, and superseded by the posted
`du` of chunk 0). No ruling number rests on them alone.

## 3. Rulings on the contested points and on §5's items

### 3.1 The ignore value (§5 item 4)

**13 on disk, 255 in the scorer (F-A29).** Bridge is right, and so is Delta: nnU-Net 2.8.1 asserts
`ignore_label == max(all_labels) + 1`, read here in the wheel (`label_handling.py` l. 40–42). With labels 0–12 an ignore
of 255 dies when the trainer builds its `LabelManager`, before the first step. Atlas, Crucible and Foxtrot kept 255.
Nothing in the definition changes: the same voxels are ignored; only the stored value moves.

### 3.2 The stage-2 leakage gates (§5 item 5)

| Gate | Atlas | Bridge | Crucible | Delta | Foxtrot | Ruling |
|---|---|---|---|---|---|---|
| L1 | keep literal (fails LCx at two voxels) | keep literal (margin 0.003) | nearest-label form | runs ≥ 3 mm | **L1r**, runs > 3 mm | **L1r** (Delta = Foxtrot up to the 3 mm edge) |
| L2 | per component, nearest > 30 mm from stage-1 | **islands > 5 mm** from stage-1 | per component, gap > 30 mm to non-stage-2 | no touch and > 30 mm | **L2d**: nearest > 30 mm from all other foreground | **L2d** |
| L2's 95 % | bound kept | point count | point count | point count | point count | **point count** |
| K1 | keep 0.05 | L1 statistic, 0.03 | keep 0.05 | lumen core, 0.10 | **K1r** = L1r, 0.02 | **K1r** |

- **L1.** Crucible's nearest-label form passes a one-voxel bleed (≤ 0.0077) but was not tried on thick ostia; the run
  filter is robust to radius (Foxtrot: 0 at r = 0.6–0.75, 0.0002 at 1.0) and keeps the thief at 0.142. Bridge's
  literal L1 passes its 0.6 mm tubes with 0.003 of room; at 0.75 mm it does not.
- **L2.** Every component form passes a correct whole branch. The judge's check separates them on a correct branch
  drawn in pieces (§2). Atlas's, Crucible's and Delta's forms pass it as long as the distal piece is within 30 mm of the
  stage-1 tree; L2d passes it whenever each piece is within 30 mm of the next, which is the property that matters.
  Bridge's 5 mm fails it. L2d still fails any blob 30 mm from everything, whatever its size.
- **K1.** Bridge's K1′ (unfiltered theft on the fit-check 20 at 0.03) sits on the same edge as literal L1: correct
  ostia of r = 1.0 mm give 0.030 (Foxtrot). Delta's core form passes correct ostia but measures something different
  from the look's L1r. K1r makes the training flag and the look agree.

### 3.3 Atlas's P-r3-1: the three F-A15 cells (§5 item 1)

**Adopted (F-A27).** The rule F-A15 adopted is a procedure, not a table; applied to the counts F-A25 made of record it
gives three different cells. Keeping 0.94 would leave D1 at twice the per-class false-fail the rule was built for.
Tightening PLB is permitted before submission (F-A6), and costs nothing in the verdict's error rates (§2). Delta,
Crucible and Foxtrot checked the lines at round 1's counts, where they are indeed unchanged.

### 3.4 The scorer of record (§5 item 1)

**Atlas's `j1f_scorer.py`, sha256 `5221032f3dc086d686b63fa946149a215ac00738a87fd9669d7faa15962b2e5b` (F-A28).**
Foxtrot's `50826b26…8252` is a correct, smaller edit of the same file, but its pooling and gate live in `gates.py`,
outside every hash `collect` checks. A scorer of record must pin what decides, not only what measures. Atlas's file
does both and was the file F-A16 named.

### 3.5 `nnUNet_compile` (§5 item 7)

**The lead runs the `grep` in §4, job 1, and posts the three counts (F-A33).** Atlas's history is right and is
corroboration: `nnUNet_compile=f` has been in icx4's job body on dev since 2026-10-17, the day before Janus 0's first
log. Foxtrot's `grep` is the confirmation, because it reads what Janus 0's own trainer wrote. Bridge, Crucible and
Delta pin `f` without confirmation; that is the expected outcome but not the evidence.

### 3.6 The command block and the spec (§5 items 3 and 4)

Delta v3 §3–§4 as amended: Dataset 719 of the 620 only, ignore 13, the chunked predict with G, the headers of F-A34,
the four pins of F-A36. The commands are in [[Master plan - Janus 1-F]] §5. The diff against `janus1l` is Delta v3
§4.1 with F-A27 to F-A34 applied.

### 3.7 T_L (§5 item 6, Q-F2-3)

All five wrote the same table (F-A32). Two details are settled here:
- **V_L uses all four of V's clauses** (Atlas, Bridge, Foxtrot); Delta's version left out L3.
- **The 1-L window** (Crucible): `collect` may wait up to 14 days after a1's `predict` for 1-L's verdict, if 1-L's
  `collect` has been submitted. That wait is fixed before anything is scored, so it is not a choice made on data. It
  is the lead's to allow: Q-F3-1.

### 3.8 Q-F2-1 and Q-F2-2, both ways (§5 item 6)

| Question | Yes | No |
|---|---|---|
| **Q-F2-1** sealed pool in extended mode | Extended classes scored once, inside D27's single acceptance look, as a report with n and CI by the scorer of record. Never earlier, never deciding J1F-2, never setting the band or a read threshold; the band and floor scripts refuse a sealed-pool patient | SN, Conus and RMA stay counts only until a larger held-out set exists; S1 can reach D35's report tier at best |
| **Q-F2-2** Job B | J1F-B (≈ 22 GPU-h) after J1F-A's verdict, after a2, before any extended read trains; a 60-case hold-out of the 620; it may raise F-A23's thresholds, never lower them; no look | F-A23's rule; revisit after a near-miss J1F-2 failure |

### 3.9 Step T and F0-r2 (§5 item 7)

Step T settles the loss (unweighted DiceCE) and `batch_dice` (False; `leaf_skip` is not built). F0-r2 has not run; it
is §4's job 2, and `check` re-prints it. Its stop rule is F-A26's.

### 3.10 Convergence (§5 item 8)

**Stage 1 (J1F-A and a2) is converged.** Every item of round 2's §5 that can change what J1F-A does is now a file with
a hash, a command or a rule written for every outcome. The swe issue (F-A12) is filed after this ruling merges.
**It is converged on these conditions**, each a check with a stop rule, not a choice:
1. F0-r2 prints its three expected lines;
2. the compile counts are posted (F-A33 sets the value);
3. the F-A8 identity reproduces 0.909 ± 0.003;
4. `check` passes on Fir with the four pins of F-A36;
5. the lead's answer to Q-F2-3 is on record before `collect` opens the ledger.

**Stage 2 (J1F-2) is not converged and need not be.** Its shape is fixed (F-A21, F-A22 as amended by F-A30, F-A23).
Its numbers (band width, 3 mm, 30 mm, read thresholds) are frozen from the first extended reads before J1F-2 is
submitted, never after.

## 4. The first Fir jobs

All are the lead's. Jobs 1–3 are 0 GPU-h and can run now. Job 4 waits on the swe build.

**1. The compile line** (Fir login node, seconds; F-A33):

```sh
K=$HOME/janus0-keep/nnunet_results/Dataset715_ICX4/nnUNetTrainerICX4__nnUNetResEncUNetPlans_60G_iso05__3d_fullres/fold_0
for f in $K/training_log_*.txt; do echo "$(basename $f) $(grep -c 'Using torch.compile' $f)"; done
```

Expected: three lines ending in `0`. Post them on #303.

**2. F0-r2** (login node, then one CPU job; F-A26): the block in [[Master plan - Janus 1-F]] §5, unchanged. Its
`srun` is a CPU job and stays on `def-aso22`. Post the three printed lines.

**3. The F-A8 identity** (one CPU job; Foxtrot v3 §4.1): Janus 0's own Fir predictions of the val 80, re-scored by the
A1c scorer:

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

Expected: decisive macro 0.909 ± 0.003, each class within 0.01. Otherwise stop; the PM finds the cause. Post the
`summary` line. It reads `$SCRATCH/icx4/layout.json` (the CTs), so it must run before the purge.

**4. J1F-A** (after the swe build; the full block is in [[Master plan - Janus 1-F]] §5): `check` (login node), `prep`
(CPU), `train` a1 and a2 (two chained GPU links each), `predict` (GPU), `collect` (CPU). Every GPU job's header is

```sh
#SBATCH --account=def-aso22_gpu
#SBATCH --gpus-per-node=h100:1
#SBATCH --cpus-per-task=12
#SBATCH --mem=280G
#SBATCH --time=23:50:00      # train links; 6:00:00 for predict
```

**`prep` must run before the scratch purge (~2026-12-20):** it reads the 620's CTs and labels from `$SCRATCH/icx4`.
After the purge it refuses and prints icx4's fetch steps (Q-F3-3).

## 5. What round 4 (or the J1F-2 freeze) must settle

Stage 1 needs no further round. Before J1F-2 is submitted, a ruling must:
1. re-set the band per class group from the trainable extended reads (F-A21) and post it with its sha256;
2. re-check L1r's 3 mm and L2d's 30 mm on the same reads (F-A30), and K1r's 0.02;
3. confirm each class's read count and inter-read floor (F-A23), with the scorer of record;
4. apply Q-F2-1's and Q-F2-2's answers (§3.8);
5. re-derive F-A27's lines if a measured second-reader branch study exists before J1F-A is submitted (round 2's §7).

## 6. Questions for the lead

None of these changes a D-number unless it says so. Each has a recommendation. Q-F2-1 to Q-F2-3 are still open from
round 2; Q-F3-1 to Q-F3-3 are new this round.

**Q-F2-1. May the 150 sealed pool patients be read in extended mode?** (Crucible v2 §6; round 2.)
- **Recommended: yes**, on round 2's conditions: the extended classes are scored only inside the seal's single
  acceptance look, as a report, never earlier, never deciding J1F-2, never setting a band or threshold (§3.8). "No"
  costs only the report on SN, Conus and RMA.

**Q-F2-2. Run Job B (J1F-B, ≈ 22 GPU-h on Fir) after J1F-A?** (Bridge v2 B-v2-4, Delta v2 §5; round 2.)
- **Recommended: no for now.** Fir's order is a1, a2, then J1F-2 when counts allow. Revisit if a J1F-2 class fails
  with its count within 1.5× of its threshold (F-A23).

**Q-F2-3. If Janus 1-L is adopted, may a released Janus 1-F carry 1-L's vessels (T_L)?** (Crucible v2 §9, Bridge
v2 §10; round 2. Bridge v3 §0 and Delta v3 §8 ask that it be answered before J1F-A.)
- **Recommended: yes.** The rule is now written (F-A32), adds no look and costs no GPU. It keeps 1-F from shipping
  vessels shown worse than the project's best adopted vessel model.
- **Please answer before J1F-A is submitted; it must be on record before `collect`.**

**Q-F3-1. May J1F-A's `collect` wait up to 14 days for Janus 1-L's verdict?** (Crucible v3 §6.3.)
- **The problem:** T_L can ship only if 1-L is adopted before 1-F's `collect`. The two tracks run on different
  clusters and may finish days apart.
- **Recommended: yes**, only if Q-F2-3 is yes and 1-L's `collect` has been submitted when a1's `predict` ends. The
  wait is fixed now, before any 1-F number exists, so it cannot be steered by results. If 1-L has no verdict after
  14 days, `collect` runs and T_L is a report.

**Q-F3-2. Release a1 and a2 together, ≈ 61–65 GPU-h on `def-aso22_gpu`?** (D47 Q8 runs a2 "if the allocation
allows"; Bridge v3 §3.3, Foxtrot v3 §4.5.)
- **Recommended: yes**, once jobs 1–3 of §4 match and `check` passes. a2 runs concurrently and is report only.
  If the allocation is short, a1 alone (≈ 31 GPU-h) is enough for the verdict.

**Q-F3-3. Should the `role:swe` build for `trillium/janus1f` be prioritised so that `prep` runs before the Fir scratch
purge (~2026-12-20)?** (Crucible v3 §3.2, §8.)
- **The problem:** `prep` and the F-A8 identity read the CTs and labels in `$SCRATCH/icx4`. Step T kept Janus 0 and the
  160, not the 720 training-and-locked CTs.
- **Recommended: yes.** If the build is late, run jobs 1–3 of §4 now anyway, and accept a re-fetch of the CTs after the
  purge (icx4's fetch steps, ≈ 91 GB, resumable) as the fallback. Nothing is lost but time.

## 7. What would change this ruling

| Observation | Then |
|---|---|
| The compile counts are ≥ 1 in every log, or mixed | `JANUS0_COMPILE` = `t`, or the last log's (F-A33). Nothing else changes |
| F0-r2's pins or counts differ | Stop. The PM finds which copy differs (F-A26) |
| The F-A8 identity misses 0.909 ± 0.003, or a class by > 0.01 | Stop before any GPU job. The PM finds the cause |
| `check` on Fir fails `test_scorer.py` with different library versions | Stop before `prep`; the swe pins the venv's scikit-image to the version that passes |
| Chunk 0's npz exceeds 4 GB per case | Chunks of 5 (F-A34) |
| The lead answers Q-F2-3 no | F-A24 stands; F-A32 is void; G is still written |
| 1-L is adopted after 1-F's `collect`, or after Q-F3-1's window | T_L is a report only; making it shippable would be a new look |
| A measured second-reader branch study arrives before J1F-A is submitted | F-A27's lines are re-derived by the same rule, and the gate file and its hash change before submission, never after |
| The first extended reads show septals longer than 40 mm or ostia over the parent longer than 3 mm | L2d's 30 mm and L1r's 3 mm are re-set from the reads before J1F-2 (§5) |
| J1F-A's fit check writes `STALL` | F-A5: the PM may cancel; round N+1 chooses the next design |
