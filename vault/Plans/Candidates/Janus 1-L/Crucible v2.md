---
tags: [plans, candidate, track-1-L, round-2, trillium, four-class, D45, D46, janus, lumen-width, locked-100, ensemble]
author: Crucible
track: 1-L
round: 2
version: 2
updated: 2026-11-13
issue: christianGRogers/Asclepius#302
---

# Crucible v2 (Janus 1-L): one candidate, the two-run ensemble; t* frozen behind a label-free drift check; one fallback, pre-registered

## 0. What changes from the plan in force

The plan in force is [[Candidates/Janus 1-L/Crucible v1|Crucible v1]] as amended by L-A1 to L-A12 ([[Janus 1-L Round 1]]),
and D46 accepted every one of the judge's recommendations. **Crucible v2 keeps all of it, and settles the eight items of
the ruling's §5:**

| §5 item | Crucible v2 | Section |
|---|---|---|
| 1. Ship candidate | **E** (mean softmax of a1 and a2) **replaces a1** as the one candidate in the same H1 → H2 → H3 sequence. One look. a1 becomes a report. If a2 does not finish, C reverts to a1, decided before the look | §1 |
| 2. Verdict branches | Written out for D46 Q3 and Q4, including the export shipped (always C as tested) | §2 |
| 3. t\* transfer | t\* stays frozen, behind **Rule T**: a label-free volume check on 40 quality-0 CTs outside every D45 list. If C's volume at t\* is outside ±3 % of Janus 0's, C is exported at the volume-matched t. Decided and posted before the look | §3 |
| 4. Job 0 | Not run. A table says what each possible result changes, and how the MDE is restated | §4 |
| 5. 60-case decomposition | `decompose60.py` (written and self-tested). It splits each class's tF1 loss into breaks, naming and extent, with one-type-removed counterfactuals. Commands below | §5 |
| 6. Fallback | **One fallback look, pre-registered now:** a from-scratch 620 run (S), triggered only by the warm-penalty signature, tested at one-sided 1.25 %. The 0.45 mm run is not a fallback; its trigger is Job 0's | §6 |
| 7. #306 | The frozen interface, self-tests and a trainer diff. The diff found one leak: the A17a trainer's **final validation scores the locked 100**. It must be skipped | §7 |
| 8. D28 and naming | Settled by D46 Q5 and Q7. E takes the name Janus 1-L.1 | §8 |

**This round's evidence** (CPU; code in `experiments/Crucible/j1l_r2/`; no image, label, read, locked-100 score or sealed
case opened):
- [[Crucible - Testing the two-run ensemble in a1's place raises a neutral model's non-inferiority pass rate and cuts the chance of shipping an unlucky draw, with no second look]]
  (`ensemble_oc.py`, `ensemble_oc.json`);
- `decompose60.py`: the 60-case error decomposition. Its self-test checks a perfect tree, a naming error, a cut and a
  missed segment, and the locked/sealed refusal. On every case it checks its own recall and precision against the frozen
  metric to 1e-9;
- `drift_check.py`: Rule T (case selection and decision), self-tested;
- a read of the two trainers' source (§7.3).

**Not done:** no GPU job, no Step T, no Job 0. Those are the lead's (D46 Q1, Q2).

## 1. The ship candidate: E, tested in a1's place

### 1.1 The rule

- **Candidate C = E at t_C.**
  - E = `nnUNetv2_predict -f 0 1` with Janus 1-L's dataset, nnU-Net's own mean of the two folds' softmax.
  - t_C = t\*, unless Rule T (§3) moves it. Either way t_C is fixed before the look.
- **E is tested instead of a1, not as well as it.** The sequence, margins and guards of L-A5 are unchanged, with E in
  a1's place. There is no E − a1 test and no ladder.
- **a1, a2 and a1 at t_C are reports.** None of them can be adopted from this look.
- **The fallback, fixed before any locked number exists:**
  - if a2 has not completed 250 epochs within its chain allowance (two 23:50 jobs), C = a1 at t_C;
  - if a1 has not completed, nothing is scored, and the PM reports the failure.

  Whether a run completed is a log fact, not a locked-100 number, so this choice spends nothing.

### 1.2 Why E

**The evidence** is [[Crucible - Testing the two-run ensemble in a1's place raises a neutral model's non-inferiority pass rate and cuts the chance of shipping an unlucky draw, with no second look]].

**What the swap does:**
1. **It helps the test that decides the expected outcome.** The most likely truth is a near-neutral recipe (60 more
   cases buy 0.001–0.005). Most adoptions will then come through H1 plus H2, or through H1 plus D46 Q4. With E in a1's
   place, P(H1) for a neutral recipe rises:
   - from 0.82 to 0.85–0.89 at S = 0.055 and σ_g = 0.008;
   - P(Q4 adoption) rises from 0.67 to 0.70–0.74.

   It is never lower, on any row.
2. **It removes most of the seed lottery from the model that ships.** At σ_g = 0.008, the chance that the adopted
   network is truly worse than Janus 0 by more than 0.01 falls from about 0.11 to 0.04–0.08. a1 ships one draw. E ships
   about half its variance.
3. **It spends nothing.** There is still one candidate and one look, and a2 runs anyway (D46 Q5). The extra cost is a
   second forward pass: about 1 GPU-min per case, about 2 GPU-h for the locked 100 and the drift set, and about 3–4
   GPU-h to predict all 1000 later.
4. **It is the shipped form nnU-Net itself recommends.** nnU-Net ensembles its fold models at inference by default
   (Isensee et al., arXiv:1809.10486, §2.4; as Delta and Foxtrot cited in round 1). Janus 0 is a single fold.

**What it does not do.**
- It does not make H3 (a tF1 gain) likelier, unless the ensemble has a real mean bonus. With none, H3's power is
  unchanged to 2 points.
- No source shows a two-run ensemble raising coronary tF1, and none is claimed.

**Why not keep a1 and add E behind it (Delta's ladder).** A ladder looks twice: E against Janus 0, then E against a1.
Its E − a1 step needs a gain of 0.005–0.010 to pass, which nothing predicts. A swap gets E's variance benefit without
either cost.

**Why not choose between a1 and E on non-locked data.** No labelled ImageCAS-X case is left outside the 620 and the
locked 100. The choice therefore has to be made a priori, which the simulation supports in every scenario.

### 1.3 The base for pool fine-tunes (L-A11)

**If E is adopted, both members are fine-tuned:**
- p1 is fine-tuned from a1, and p2 from a2, on the same data;
- the pool candidate is E_p = ensemble(p1, p2).

Round 10's pool design already runs two replicates per arm (A37/A38). Here each replicate starts from its own member,
so this costs nothing beyond what the pool round already spends.

**The forgetting guard** compares E_p with the adopted E on the locked 100 (G2/L3 as L-A11). That is an ensemble
against an ensemble, so the comparison is not tilted.

**If a1 is adopted** (the a2 fallback), pool fine-tunes start from a1 alone, as in L-A11.

## 2. The verdict branches (D46 Q3, Q4)

The tests are L-A5's. C is E at t_C. **The adopted export is always C exactly as tested.** No branch ships a variant,
such as C at argmax, that was not the tested candidate.

| Outcome | Verdict | Wording of record |
|---|---|---|
| H1 fails | **Not adopted.** Janus 0 stays | "Janus 1-L.1 was not shown non-inferior to Janus 0 in tree-F1 (lower bound L) [or: failed the <class / L3 / FP> guard]." G5 lists five cases for any class with point Δ < −0.05. §6 says what runs next |
| H1 passes, H2 fails, H1's lower bound > −0.015 | **Adopted (D46 Q4)** as Janus 1-L | "Non-inferior to Janus 0 in tree-F1 at a margin of 0.015 (Δ m, 95 % CI [L, U]); not shown better in lumen width (whole-tree Dice Δ m_D, lower bound L_D ≤ 0) or in tree-F1. Adopted for its larger training set." |
| H1 passes, H2 fails, lower bound in (−0.02, −0.015] | **Not adopted.** Janus 0 stays | "Non-inferior at 0.02 but not at 0.015; not shown better; Janus 0 is kept." |
| H1 and H2 pass, H3 fails | **Adopted (D46 Q3)** as Janus 1-L | "Better than Janus 0 in lumen width: whole-tree Dice +m_D (95 % CI [L_D, U_D]), of which Janus 0 at t_C alone reaches s %; tree-F1 non-inferior at a margin of 0.02 (lower bound L). A tree-F1 gain was not shown (Δ m, CI [L, U])." |
| H1, H2 and H3 pass | **Adopted** as Janus 1-L | As above, ending "… and better in tree-F1: +m (95 % CI [L, U], lower bound > 0)." |

**Notes on the branches:**
- **With H1 and H2 passing, adoption needs only H1's −0.02 bound.** The −0.015 bound applies only to the branch with no
  width gain (D46 Q4).
- **s %, the share of the Dice gain that the threshold alone explains,** = (Janus 0 at t_C − Janus 0 at argmax) / (C −
  Janus 0 at argmax), from the L-A6 reports.
  - If s ≥ 80 %, the verdict adds: "most of the width gain is the export threshold, which applies to Janus 0 as well".
  - This is still a report. **Janus 0 at t_C is never a candidate** (L-A6).
- **"Not shown better" is never written as "no better".** The locked 100 resolve tF1 differences of about 0.011–0.021
  (restated from Job 0, §4).

## 3. The t\* transfer: frozen, behind a label-free drift check (Rule T)

### 3.1 How a calibration shift would show

**Rule W's mechanism.** It picks t\* where Janus 0's lumen volume best matches ImageCAS-X's for Dice, on the tuning 60.
If the fine-tune moves the rim probabilities, the same t gives C a different volume. There are two cases:
- **C wider at a given t:** t\* overshoots, Dice falls and FP may rise.
- **C narrower:** t\* undershoots, and part of the width gain is lost.

**Where it could be seen:**

| Where it could show | Usable before the look? |
|---|---|
| C's probabilities on the tuning 60 | **No.** C trained on them, so its rim there is in-sample and over-confident. A check there is biased toward "C is wider". Reported only |
| C's Dice at every t on the locked 100 (L-A6's transfer report) | **No.** It is a locked-100 number. It is a report written after the verdict, and it explains a miss; it never moves t |
| **C's and Janus 0's predicted volumes on CTs outside all D45 lists, without labels** | **Yes.** No label, no locked case, no sealed case. This is Rule T |

### 3.2 Rule T (pre-registered; `experiments/Crucible/j1l_r2/drift_check.py`)

**The drift set U** (40 CTs). Start from ImageCAS's 200 quality-0 cases (ImageCAS-X's `exclude.txt`). They have no
ImageCAS-X label and are in no D45 list. Remove:
- the 20 sealed (A14);
- the 24 declared development cases;
- any D27 pool-sealed name.

Rank the rest by `sha256('asclepius-j1l-drift:' + id)` and take the first 40. **No label of a U case is ever read.**

**The rule:**
- **V_M(c, t)** = the voxels where network M's summed vessel probability is ≥ t, with t = 0.5 meaning argmax.
- **r(t)** = the median over U of V_C(c, t) / V_J0(c, t\*).
- **If 0.97 ≤ r(t\*) ≤ 1.03:** t_C = t\*. This is the expected case, and the frozen rule stands.
- **Otherwise:** t_C = the t on the grid 0.300, 0.325, …, 0.500 with r(t) closest to 1, ties to the larger t.
  - This keeps the volume at which Rule W found Janus 0's Dice optimum.
  - A case's label does not change between networks, so matching C's volume to Janus 0's at t\* keeps the volume ratio
    that Rule W chose.
- **Timing:** `drift.json` and its sha256 are posted on #302 **before** the locked 100 is scored. It is applied once,
  to C. Reports for a1 and a2 use t_C too.

**Why a ±3 % band and not always matching.**
- Rule W expects t\* to lift the volume ratio by about 9–10 % (0.867 → about 0.95). A 3 % shift is about a third of
  that, which is the smallest shift worth acting on.
- Inside the band, a fine-tune that genuinely drew a better boundary keeps its gain. Always-matching would cancel it.

**Its known weakness.** Quality-0 scans were set aside for image quality, so absolute volumes on U mean little. The
rule compares two networks on the same scans, which is what a calibration shift is. A non-quality-0 alternative would
be non-sealed pool CTs; it is not used, because their guard surface (D27, D35, reserve) is larger.

**Cost:** two inference passes on 40 cases (Janus 0 in Job 0's extension; C in the E job), about 1 GPU-h in all.

## 4. Job 0: not yet run. What each result would change

Job 0 is unchanged (L-A9). Round 2 cannot read `select.json`, so this is the pre-registered reading. **Add to Job 0:**
- Janus 0's probabilities on U (§3), about 0.5 GPU-h;
- `decompose60.py` at t = 0.50 and at t\* (§5), CPU.

**The U extension of Job 0** (Trillium; after Job 0, or in the same allocation). `exclude.txt` is ImageCAS-X's own
filelist; give its path.

```sh
source $HOME/icx14-venv/bin/activate
R=$SCRATCH/asclepius/repo; W=$SCRATCH/j1l_job0; J0=$SCRATCH/janus0; D=$R/experiments/Crucible/j1l_r2
python $D/drift_check.py --selftest
python $D/drift_check.py select --exclude <path to ImageCAS-X exclude.txt> > $W/drift_cases.json   # 40 ids, none sealed/locked/trained
mkdir -p $W/drift/in $W/drift/janus0
for c in $(python -c "import json;print(' '.join(json.load(open('$W/drift_cases.json'))['U']))"); do
  ln -sf $SCRATCH/asclepius/cases/$c/ct.nii.gz $W/drift/in/${c}_0000.nii.gz; done
export nnUNet_raw=$W/raw nnUNet_preprocessed=$W/pre nnUNet_results=$J0/nnunet_results nnUNet_compile=f
srun --account=def-aso22 --gpus-per-node=1 --time=01:00:00 nnUNetv2_predict -i $W/drift/in -o $W/drift/janus0 -d 715 \
  -c 3d_fullres -f 0 -tr nnUNetTrainerICX4 -p nnUNetResEncUNetPlans_60G_iso05 -chk checkpoint_final.pth \
  --disable_tta --save_probabilities -device cuda
sha256sum $W/drift_cases.json      # post on #302 with drift_cases.json; no prediction is scored, no label exists
```

| Job 0 result | What it changes |
|---|---|
| **Identity check fails** (val 80 not 0.909 ± 0.003, a class off by > 0.01, or < 95 % of cases within 0.01 of Fir's) | Stop (L-A8). Nothing else in this table is read until the PM has the cause |
| **t\* ∈ {0.45, 0.40}** (Crucible v1's prediction) | Nothing changes. H2 is expected to pass if the transfer holds (Rule T checks it) |
| **t\* = 0.35** | Plan unchanged. The verdict's s % is expected to be high. Rule T's band matters more (a lower t sits on a flatter part of the rim) |
| **t\* = 0.50** (no threshold helps) | The export lever is empty. H2 then tests the network alone, and its pass chance is low (the 60 cases buy little width). The likely end is the Q4 branch. **Round 3 decides** whether the 0.45 mm scratch run (ceiling 0.956, a 115 mm view, about 55–60 GPU-h) is added before the training jobs. It is not a fallback (§6) |
| **t\* = 0.30, or FP rises at every t < 0.5** | Rim miscalibration, or dim veins beside the tree. Round 3 fits a temperature on the tuning 60 (Janus 0's probabilities, CPU) and re-runs Rule W on the calibrated probabilities before any training. Rule T then compares calibrated with calibrated |
| **Dice at t\* still > 0.03 below 0.934, with volume ratio ≥ 0.95** | The bias is fixed and the grid binds. Same consequence as t\* = 0.50 for the 0.45 mm run |
| **Janus 0's per-case decisive macro SD on the locked 100, s_J0** | The MDE stated in the verdict is restated, as L-A7 allows: Ŝ = 0.038 × s_J0 / 0.065 (round 1's scaling: the warm pair's paired SD, scaled by Janus 0's spread over run 1's), and MDE = 2.8 × Ŝ / √100. **No margin changes.** If MDE > 0.025, the verdict's wording says so |
| **decompose60 (§5)** | Decides only later rounds' arms (§5.3). It changes nothing in the first jobs |

## 5. The 60-case error decomposition (Bridge §7; §5 item 5)

### 5.1 What it measures

`experiments/Crucible/j1l_r2/decompose60.py`. Per tuning case and class, each reference centreline point is exactly
one of:
- **hit:** predicted as the right class and rooted (what recall counts);
- **break:** predicted as the right class, but in a piece cut off from every ostium;
- **naming:** predicted as another vessel;
- **missed:** not predicted at all.

Each predicted centreline point is exactly one of:
- **correct:** inside the reference class (what precision counts);
- **naming:** inside another reference vessel;
- **overshoot:** outside every reference vessel.

**Each type's cost** is tF1_c with that type removed, minus the actual tF1_c:
- break: break points become hits;
- naming: naming points become hits and correct points on both sides;
- extent: missed points become hits, and overshoot points become correct.

**What it also reports:**
- which class each lost reference point was given (for example, LCx drawn as LAD);
- the number of cases where a break costs more than 0.05.

**How it is checked:**
- **Same path as the decisive score.** Each case goes through icx4's `tf1_score` (the crop, `find_ostia` with aorta
  and CT, the frozen A1c metric), and A1a/A1b are applied exactly.
- **On every case,** the script's hit fraction must equal `tree_f1`'s recall per class, and its correct fraction the
  precision, to 1e-9. A case that differs is listed and left out.
- **It refuses** any locked-100 or sealed id.

### 5.2 Commands (Trillium login node, CPU, after Job 0)

```sh
source $HOME/icx14-venv/bin/activate
R=$SCRATCH/asclepius/repo; W=$SCRATCH/j1l_job0; J0=$SCRATCH/janus0; T=$(python3 -c "import json;print('%.2f'%json.load(open('$W/select.json'))['chosen_t'])")
python $R/experiments/Crucible/j1l_r2/decompose60.py --selftest
for t in 0.50 $T; do
  python $R/experiments/Crucible/j1l_r2/decompose60.py --pred $W/thr/t$t --icx $J0/icx --aorta $J0/aorta \
    --layout $W/layout.json --np 20 --out $W/decompose60_t$t.json > $W/decompose60_t$t.summary.json
done
cat $W/decompose60_t*.summary.json
```

**Post on #302:** both `summary` files. They hold per-class means and counts only, and no image.

### 5.3 What it decides (later rounds only)

The decision is per class, starting with LCx (the weak class, 0.857 on val 80). Read it on argmax, t = 0.50.

| Largest share of the class's tF1 loss | Arm a later round may cost | Why |
|---|---|---|
| **break** (and > 0.02 of tF1 in absolute terms) | A connectivity arm. Skeleton Recall is the candidate, but on the record it recovers branches without connecting them (BCS: about twice the components on ImageCAS). A break-dominated loss is therefore an argument for a connectivity-aware export (a learned bridge) before a loss | Breaks are the one error a loss on topology targets |
| **naming** | The namer or class-weighted CE (icx4's hook exists). Read the confusion counts: LCx↔LAD is a territory question (D1b, ramus), not a loss question | A loss on topology does not fix labels |
| **extent** (missed or overshoot) | Nothing on the network. Check the label census (whether the 60 draw more distal extent than the 560) | Extent errors on the reference's own distal convention are not a model defect |
| No type above 0.01 | Nothing. Close the topology question for track 1-L | |

The same decomposition at t\* shows whether the threshold trades naming for width. Its naming cost must not rise by more
than 0.005. If it does, that is reported against Rule W's tF1 guard, which should already have caught it.

## 6. The fallback when H1 fails (§5 item 6)

**Pre-registered now: one fallback look, at most, in the whole track.**

| | |
|---|---|
| **Candidate S** | Janus 0's own recipe from scratch on the 620: Janus 0's plans, `nnUNetTrainerICX4`-equivalent settings (§7.3), 1000 epochs, one run. About 50 h of training at 181 s/epoch; **≈ 53 GPU-h** in three chained jobs (Bridge's S). Exported at t\*, with Rule T applied to S |
| **Trigger** (all of these) | H1 fails; **and** both a1's and a2's point Δ macro tF1 against Janus 0 are < 0 (the warm-start penalty signature, Ash & Adams); **and** L0 passed |
| **Not triggered by** | H1 failing through one class or L3 alone, with the macro point Δ ≥ 0. That is a class problem. The PM reads G5 and the tuning-60 decomposition of a1 (in-sample, report only) and Janus 0. Round N+1 decides. A scratch run would not address it |
| **Its look** | The same H1 → H2 → H3 sequence and wording, with S in C's place. **Every bound at one-sided 1.25 %** (the 97.5 % two-sided-equivalent bound becomes 98.75 %). Over two looks, the track's chance of a false adoption is ≤ 2.5 % + 1.25 % |
| **If S fails** | Janus 0 stays as track 1-L's model. The recipe question goes back to a round, with the decomposition in hand |

**Why S and not the 0.45 mm run as the fallback.**
- An H1 failure with both runs negative is a warm-start failure. S is the direct test of it.
- The 0.45 mm run is a width lever. Its triggers are Job 0's (§4): t\* = 0.50, or the grid binding. It answers H2, not
  H1.
- If it is triggered, round 3 decides whether it joins *before* the first look as the candidate's sibling (replacing
  the S fallback, so the track still has at most two looks), or waits.

**Why pre-register now.** A fallback chosen after seeing which test failed is a forking path. Fixing the trigger, the
candidate and the α now keeps the second look honest.

## 7. #306's spec, frozen (§5 item 7)

### 7.1 Launcher interface (`trillium/janus1l/janus1l`; Trillium header, `--account=def-aso22`, `--gpus-per-node=1`)

| Command | What it does | GPU-h |
|---|---|---|
| `JANUS1L_DRYRUN=1 ./janus1l` | Prints and checks:<br>- split pins (L-A1);<br>- `train 620 / val 100 / sealed 0 / locked-in-train 0`;<br>- Janus 0's checkpoint sha256 = Step T's `SHA256SUMS`;<br>- plans diff (below);<br>- `select.json` sha256 = the one posted on #302;<br>- A1c hash;<br>- the trainer diff result (§7.3).<br>Submits nothing | 0 |
| `./janus1l prepare` (P) | Dataset 718 from the 620 + the locked 100 (labels by `territory.to_four`, ids `cNNNN`). Then `nnUNetv2_move_plans_between_datasets -s 715 -t 718 -sp nnUNetResEncUNetPlans_60G_iso05 -tp nnUNetResEncUNetPlans_60G_iso05`, then `nnUNetv2_preprocess -d 718 -plans_name nnUNetResEncUNetPlans_60G_iso05 -c 3d_fullres`. **No fingerprint, no `plan_experiment`.** `splits_final.json` has two identical entries | ≈ 1 |
| `./janus1l train a1` / `a2` | Folds 0 / 1, `nnUNetTrainer_janus1l` (§7.2), chain-resumable (at most two 23:50 jobs each), concurrent. Writes `completed` markers | ≈ 13 each |
| `./janus1l predict` | After both are complete:<br>- a1 (`-f 0`), a2 (`-f 1`) and E (`-f 0 1`) on the locked 100 and on U;<br>- `-chk checkpoint_final.pth --disable_tta --save_probabilities`;<br>- the a2 fallback (§1.1) decided from the markers;<br>- then `drift_check.py decide` for C, which writes `drift.json`;<br>- then `threshold_export.py` for every model at t_C and at the Rule W grid.<br>**Scores nothing** | ≈ 2–3 |
| `./janus1l post` | Prints `drift.json`, its sha256 and the completion markers for #302. **Refuses to proceed to `collect`** until `JANUS1L_DRIFT_SHA=<posted sha>` is supplied | 0 |
| `./janus1l collect` | The one look:<br>- `r9_score_icx4.py` for C, then the reports (a1, a2, a1 at t_C, Janus 0 at t_C, Dice at every t);<br>- the gate implementing L-A5 to L-A8, §1 and §2 exactly: H1 (macro −0.02, class −0.03, L3 trimmed/CI, FP ≤ 1), H2, H3, the Q4 branch, the wording table, s %, σ_g, val-80/locked-20 parts, the 89 never-inspected cases;<br>- writes `results/` | 0 (CPU) |
| `./janus1l status` | s/epoch, epoch, chain state, markers | 0 |

**Plans check (P and the dry run).** `nnUNetv2_move_plans_between_datasets` rewrites `dataset_name`, so the plans are
not byte-identical after the move. The check is:
- the moved `plans.json`, with `dataset_name` removed, equals Janus 0's with `dataset_name` removed (canonical JSON);
- `finetune_load`'s strict comparison then runs at load.

L-A2's "byte-identical" should read "identical except `dataset_name`".

### 7.2 The trainer: `nnUNetTrainer_janus1l(nnUNetTrainer_segtrain_finetune)`, a thin subclass

| Setting | Why |
|---|---|
| **Final validation skipped** (always) | `nnUNetTrainer_segtrain_coronary` runs nnU-Net's final validation on fold val (here the locked 100). It writes `validation/summary.json`, with the locked-100 Dice of each run, and 100 probability files, at the end of training, **before the look**. That is a locked-100 number computed outside `collect` (L-A7). icx4's trainer has the same switch (`ICX4_SKIP_FINAL_VAL`). The locked-100 predictions come from `predict` instead |
| `SEGTRAIN_CT_WINDOW=off`, `SEGTRAIN_FINETUNE_FROM=$JANUS0/.../checkpoint_final.pth` | L-A2 |
| `SEGTRAIN_SAVE_EVERY=10` | icx4's checkpoint interval (the segtrain default is 50) |
| `SEGTRAIN_MAX_SECONDS` = walltime − 30 min | Chain stop (segtrain's equivalent of `ICX4_DEADLINE`) |
| `checkpoint_best.pth` never copied, read or scored | It is selected on locked-100 pseudo-Dice |

### 7.3 The trainer diff (read from source; #306's self-test must confirm it at runtime)

| Item | `nnUNetTrainerICX4` (Janus 0) | `nnUNetTrainer_segtrain_finetune` (A17a) | Same? |
|---|---|---|---|
| Class chain | NoMirroring ← nnUNetTrainer | coronary ← segtrain ← nnUNetTrainer | — |
| Mirroring, training and inference | off (`nnUNetTrainerNoMirroring`) | off (same override in `coronary`) | yes |
| Loss | nnU-Net DC + CE with deep supervision. **Optional class-weighted CE** if `$W/ce_class_weights.json` exists | stock DC + CE with deep supervision | **yes, if Janus 0 never had the file**. Check: `grep -c "class-weighted CE" training_log*` on Janus 0's Fir logs must be 0 (add the log to Step T's copy) |
| Sampling | nnU-Net default (oversample foreground 0.33, not probabilistic) | not overridden | yes |
| Iterations | 250 per epoch, 50 validation iterations, batch and patch from plans | the same | yes |
| Optimiser | SGD 1e-2, Nesterov 0.99, weight decay 3e-5, per-epoch poly over 1000 epochs | the same SGD; per-iteration 2500-iteration warm-up, then poly, over 250 epochs | by design |
| Final validation | runs unless stopped early | runs and saves probabilities | **no**: skip it in 1-L (§7.2) |
| Checkpoint interval | 10 | 50 unless `SEGTRAIN_SAVE_EVERY` | set to 10 |
| Window check | none | refuses without the fixed window | `off` (L-A2) |
| Sealed refusal | none in the trainer | `refuse_sealed` on train and val ids | stricter. Ids must be `cNNNN` |
| `nnUNet_compile` | as Janus 0's job set it | as the launcher sets it | the launcher copies icx4's value |

**The runtime self-test** (CPU, `ICX4_TEST_ITERS`-style, on a 2-case fake dataset with Janus 0's plans):
- instantiate both trainers;
- assert equality of:
  - the loss class and CE weight (None);
  - `oversample_foreground_percent` and `probabilistic_oversampling`;
  - `num_iterations_per_epoch` and `num_val_iterations_per_epoch`;
  - batch and patch size;
  - deep-supervision scales;
  - `weight_decay`, momentum and Nesterov;
  - `inference_allowed_mirroring_axes`;
  - the string form of the training transforms;
- assert the scheduler's first, warm-up-end and last LR;
- assert that final validation is skipped.

### 7.4 Self-tests #306 must pass before any training job

1. **Split pins** (L-A1): both list hashes and the file hash. The file is identical to Delta's proposal.
2. **Sealed refusal:** a sealed id in the train list, the val list, U or the tuning 60 → refusal at index, prepare,
   trainer, predict and decompose.
3. **Locked refusal:** a locked id in training, or in U → refusal.
4. **No plan step:** `prepare` never calls `nnUNetv2_plan_and_preprocess` or `extract_fingerprint`; the plans check of
   §7.1 passes.
5. **Strict load:** `finetune_load` loads Janus 0 strictly, with a bitwise tensor check and its sha256 logged. A
   one-byte change to the plans refuses.
6. **t_C applied:** `threshold_export` at t_C reproduces argmax at 0.5, and the exported locked-100 files are at the
   posted t_C.
7. **The look is single:** `collect` refuses without the posted drift sha, and refuses a second time if
   `results/gate.json` exists.
8. **The trainer diff** (§7.3).

## 8. D28 and naming (§5 item 8)

- **D28:** settled by D46 Q5. a2 runs either way. In this plan a2 is also half of the candidate, and σ_g = |a1 − a2| /
  √2 is still reported (L-A6). A37's rule (|a1 − a2| > 0.02 → ≥ 2 runs per arm later) stands.
- **Naming:** settled by D46 Q7.
  - **E** is the candidate read, so it takes **Janus 1-L.1** (the ruling's Q7 note: E takes 1-L.1 if round 2 makes it
    the candidate).
  - If the a2 fallback makes a1 the candidate, a1 takes 1-L.1.
  - The adopted model is **Janus 1-L**.
  - a1, a2 (as separate networks) and Janus 0 at t_C are reports under 1-L.1 and take no number.
  - S, if it runs, is read as **Janus 1-L.2**.

## 9. Cost

| Job | GPU-h | Change from the plan in force |
|---|---|---|
| Job 0 (+ U, + decompose on CPU) | 3.5–4.5 | +0.5 (U) |
| P | ≈ 1 | — |
| a1, a2 | ≈ 13.5 each | — |
| predict (a1, a2, E on the locked 100 and U) + export | ≈ 2–3 | +1 to 2 (E as the candidate, U) |
| collect | 0 | — |
| **Total** | **≈ 33–36** (ceiling ≈ 62) | +1.5 to 2.5 |
| Fallback S (only on its trigger) | ≈ 53 | pre-registered, new |

## 10. Risks

- **E's benefit may be small.** Two warm runs from one parent are correlated (κ near 1). The simulation shows the swap
  never hurts, so the downside is about 2 GPU-h.
- **Rule T on degraded scans.** Quality-0 noise could push r(t\*) outside the band by chance. With 40 cases and a
  median, a 3 % band is wider than the median's sampling error is likely to be. This is an assumption, not a
  measurement. Job 0's U predictions of Janus 0 give the spread of V_J0 across U as a sanity number.
- **S's 1.25 % bounds** make S harder to adopt. This is intended: it is the track's second look.
- **The final-validation leak** is real in the current trainer. If #306 ships without the skip, the per-run locked-100
  Dice exists before the look. The PM must not read it, and the gate must not use it. The skip removes the temptation.

## 11. External evidence

No new external source this round. The ones used were read at source in round 1 and spot-checked by the judge:
- Isensee et al., arXiv:1809.10486, §2.4 (fold ensembling at inference);
- Ash & Adams, arXiv:1910.08475 (warm-start penalty; the reason for S's trigger);
- Lipton et al., arXiv:1402.1892 (the threshold below 0.5);
- the FDA fixed-sequence guidance (one look, ordered tests; and the reason a second look takes its own α);
- BCS, arXiv:2607.28327 (Skeleton Recall's components), as verified in Delta's topology note.

## 12. Questions for the lead

None. D46 answered round 1's questions. Every choice above is a plan rule within them:
- the ensemble as candidate is D46 Q6's "if round 2 pre-registers it";
- the Q4 branch uses D46 Q4's −0.015;
- Dice after tF1 is D46 Q3.

**Action, not a decision:** Step T should also copy Janus 0's Fir `training_log*.txt` (for §7.3's CE-weights check):

```sh
cp $SCRATCH/icx4/nnunet_results/Dataset715_ICX4/nnUNetTrainerICX4__nnUNetResEncUNetPlans_60G_iso05__3d_fullres/fold_0/training_log_*.txt $L/
grep -c "class-weighted CE" $L/training_log_*.txt     # expect 0 for every file; post the counts on #302
```
