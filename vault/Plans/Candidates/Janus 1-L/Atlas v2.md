---
aliases: [Janus 1-L Atlas v2]
tags: [plans, candidate, janus1-l, D45, D46, trillium, four-class, round2]
author: Atlas
track: 1-L
round: 2
updated: 2026-11-15
issue: christianGRogers/Asclepius#302
---

# Atlas v2 (track 1-L): a1 at a label-free-checked t\*, one look, and every fallback named before the look

## In one paragraph

**The plan in force stands:** [[Candidates/Janus 1-L/Crucible v1|Crucible v1]] with L-A1 to L-A12, and D46 answers
every round-1 question for the lead. This version answers the eight items of [[Janus 1-L Round 1]] §5. Step T and
Job 0 have not run, so every number they produce is a branch in the plan (§4), not a premise.

**What Atlas v2 changes, in order of weight:**
1. **The ship candidate stays a1** (item 1). E stays a report. Shipping E would make the shipped model and the parent
   of every pool fine-tune two different objects, and no E − a1 evidence can be collected before the look without
   spending the locked 100. E's case is re-opened at the first pool step, where D35 gives an independent set (§1).
2. **t\* gets a label-free transfer check, Rule T** (item 3). Forty unlabelled, unsealed ImageCAS cases, outside every
   decision set, measure how far the threshold widens Janus 0's tree and a1's tree. If a1's rim has sharpened or
   softened by a grid step, the candidate is a1 at the matched threshold t_T. No locked-100 number and no label is
   used. The rule and its code are in this PR (§3).
3. **The 60-case error decomposition exists as code** (item 5): `experiments/Atlas/j1l/r2_error_decomp.py`, self-tested
   against the frozen metric. It splits every lost centreline point into breaks, naming, extent and holes, and gives
   the counterfactual tF1 of fixing each. **An arm is worth a run only if its perfect fix on the 60 is worth at least
   the locked-100 MDE (0.011).** That retires my round-1 arm b unless the numbers say otherwise (§5).
4. **The fallbacks are mapped to causes now** (item 6). The from-scratch run S is pre-registered with a trigger that
   reads only reports. The 0.45 mm run is a width arm triggered by Job 0, not an H1 fallback (§6).
5. **#306's spec is frozen** with three fixes the trainer diff turned up (item 7): nnU-Net's final validation must be
   skipped (it would score the locked 100 per run, before the look, and write about 100 GB of probabilities), the
   checkpoint interval must be 10 epochs, not 50, and Janus 0's run must be shown to have trained without
   `ce_class_weights.json` (§7).

**Cost:** ≈ 34–36 GPU-h, as L-A9's 32–34 plus about 1.5 for Rule T. Ceiling about 60.

## 0. What D46 settled, and what it leaves to this round

| D46 | Effect here |
|---|---|
| Q1, Q2 | Step T and Job 0 are the lead's, before round 2 relies on t\*. They have not run: §4 plans for each outcome |
| Q3 | Dice decides after tF1 non-inferiority. H2 is a co-decider (item 2) |
| Q4 | A non-inferior, not-shown-better a1 is adopted if H1's lower bound is > −0.015 (item 2) |
| Q5 | a2 runs, report only |
| Q6 | An ensemble is acceptable in principle if pre-registered. This round says whether to (item 1: not now) |
| Q7 | The candidate read is Janus 1-L.1; the adopted model is Janus 1-L (item 8) |
| Q8 | Pool reads: materials dropped before D40; material-only voxels are background. Affects only L-A11's later step |

## 1. The ship candidate: a1, with E reported (item 1)

**The options, all with one look:**

| Option | What is tested in H1–H3 | Base for pool fine-tunes |
|---|---|---|
| **A (recommended)** | a1 at t\* (or t_T, §3) | a1 |
| B | E at t\* replaces a1 in the same sequence; a1 is a report | a1 (D46 Q6's wording) |
| C (Delta v1's ladder) | E, and E − a1 > 0, then a1 | a1 |

C spends two tests on one set. Its rung 1 needs a second interval (E − a1) and its rung 2 is read only after rung 1
fails, so it is a best-of with extra steps. L-A7 rules it out, and nobody defends it now.

**Why A over B.**
1. **No E − a1 evidence can exist before the look.** The 60 tuning cases go into training; the 180 unlabelled cases
   have no ImageCAS-X reference; the locked 100 is the look itself. E would therefore be chosen on prior alone:
   Mehrtash et al. (M = 50, Dice, not tF1; Foxtrot's own caveat) and nnU-Net's 5-fold default. The prior is real, but
   it says "small and in the right direction", and at M = 2 nobody has a size.
2. **The lineage breaks under B.** L-A11 starts every pool fine-tune from one network (a1). Its forgetting guard
   (G2/L3) compares the child with its parent on the locked 100, and D35's G1 compares it with the shipped model. Under
   B the shipped model is an ensemble, so G1 would ask a single child to beat a two-network ensemble: a handicap of
   exactly the unmeasured ensemble gain. Fixing that means training two children at every pool step, which doubles
   every later fine-tune (≈ +15 GPU-h each) for a gain nobody has measured.
3. **t\* is tuned on one network.** Averaging two softmaxes softens the rim where the runs disagree, so E's rim is a
   different calibration object from Janus 0's. Rule T could be applied to E, but that is one more transfer on top
   of an unmeasured gain.
4. **The variance argument is answered by a2, not by shipping E.** a2 measures σ_g (L-A6). If |a1 − a2| > 0.02 macro,
   A37's ≥ 2-runs rule already applies to every later recipe claim. A large σ_g is also the evidence that would make
   ensembles worth their cost from the pool step on (below).

**What E needs to become a candidate later (pre-registered now):**
- **Where:** the first pool step (L-A11), on **D35's decision reads**, the first ImageCAS-X-independent labelled set
  that is not the locked 100.
- **What:** E_pool (two pool children, mean softmax) against the single child, paired by patient on D35. One test, at
  the point Δ macro tF1 > 0 with lower bound > −0.005; Delta's MDE for E − a1 (0.005–0.010) says D35's ~50 patients
  will see only a large gain, which is the gain worth doubling every fine-tune for.
- **Trigger to even run it:** σ_g from a1/a2 ≥ 0.01 macro, or E − a1 on the locked 100 (a report here) ≥ +0.005. Below
  both, E is dropped for the track.
- **If the lead prefers B now,** the clean form is: E at t\* replaces a1 in H1–H3 unchanged; Rule T is computed on E
  instead of a1; a1 stays the pool parent; and G1 at the pool step compares the child with **a1**, not E, with E's
  advantage stated. Option B is coherent, only more expensive later.

## 2. The verdict branches and their wording (item 2)

D46 Q3 and Q4 fix the rules; this section fixes the words, so the result text cannot be written after the numbers.

| Outcome | Verdict | What ships | Wording of record |
|---|---|---|---|
| H1 fails | Not adopted | Janus 0 | "Janus 1-L.1 was not shown non-inferior to Janus 0 in tree-F1 on the locked 100 (Δ m [lo, hi]; guard that failed: …). Janus 0 stays." |
| H1 passes, LB > −0.015, H2 fails | Adopted (D46 Q4) | **a1 at the tested threshold** | "Non-inferior to Janus 0 at a margin of 0.015 in tree-F1 (Δ m [lo, hi]), not shown better in lumen width (whole-tree Dice Δ d [lo, hi]) or tree-F1. Adopted for its larger training set." |
| H1 passes, −0.02 < LB ≤ −0.015, H2 fails | Not adopted | Janus 0 | "Non-inferior at 0.02 but not at the 0.015 the lead set for adoption without a gain (D46 Q4)." |
| H1 + H2, H3 fails | Adopted (D46 Q3) | a1 at the tested threshold | "Better than Janus 0 in lumen width (whole-tree Dice +d [lo, hi]) and not worse in tree-F1 (Δ m, lower bound lo > −0.02). A tree-F1 gain was not shown. Of the Dice gain, s % is reached by Janus 0 at the same threshold (L-A6)." |
| H1 + H2 + H3 | Adopted | a1 at the tested threshold | As above, "… and better in tree-F1 (lower bound lo > 0)." |

**Three rules the table depends on:**
- **What ships is what was tested.** In the Q4 branch, a1 ships at t\* (or t_T), even though H2 failed. Switching to
  argmax after the look would ship an untested candidate chosen on a report.
- **The share sentence is mandatory** whenever H2 passes. If Janus 0 at t\* already reaches ≥ 80 % of the Dice gain,
  the verdict adds: "the width gain is mainly the export rule; the fine-tune's own contribution is not shown." This is
  my round-1 decomposition (L-A6) turned into wording, and it keeps "better" honest about where the gain came from.
- **H1's guards are part of the wording.** A Q4 adoption names the class with the smallest mean Δ and its value, so a
  reader sees what "non-inferior" spent.

## 3. t\* transfer: Rule T, label-free and off every decision set (item 3)

### 3.1 How a calibration shift would show

| Signal | When it is seen | What it can do |
|---|---|---|
| **Rule T on U40** (this section) | Before the look | Moves the candidate's threshold by grid steps |
| a2's U40 curve beside a1's | Before the look | Report: if a1 and a2 shift differently, the shift is seed noise, not recipe |
| C's Dice and volume ratio at every t on the locked 100 (L-A6) | After the look | Report only; informs the next model, never this one |
| Pool reads at t\* vs 0.5 on D35 (Crucible v1 §2.1) | At the pool step | Report; a team convention wider or narrower than ImageCAS-X shows here |

The training-set behaviour of a1 is not a signal: a1 has fitted the 60 and the 560, so its rim there is biased
toward the labels.

### 3.2 Why a label-free check is enough to act on

A rim shift is a property of the network's probabilities, not of the labels. If a1 is sharper at the boundary than
Janus 0 (likely after 250 more epochs on the same labels, because DiceCE keeps pushing rim probabilities toward 0 or
1), the same t\* adds fewer voxels, and the thin-lumen fix partly undoes itself. That can be measured by how much a
threshold **widens each model's own tree**, on any CT, with no reference.

### 3.3 Rule T (pre-registered; `experiments/Atlas/j1l/r2_transfer.py`)

- **U40:** the 40 cases with the smallest `sha256('asclepius-j1l-transfer:' + id)` among the **180** ImageCAS cases
  that ImageCAS-X does not label and that are not sealed (D22's 200 unlabelled minus the 20 sealed quality-0).
  - **Pins** (sorted ids joined by `\n`): the 180 `5788ea4a…affec`; U40 `f9ccf5c4…b212`. The list is in
    `experiments/Atlas/j1l/u40.json`.
  - No ImageCAS volume is in the SegQueue14 pool list (`configs/segqueue14/pool-2026-10.txt`), so U40 is in neither
    the D27 pool seal nor D35. The script refuses any id outside the 180.
  - No label of a U40 case is read. These are the cases SegQueue annotators would get prelabels for; a prediction of
    them is what Janus 0 already did for the hand-off.
- **Inflation curve:** r_M(t) = Σ vol_M(t) / Σ vol_M(0.50) over U40, with vol the voxels whose summed vessel
  probability is ≥ t. It measures the widening alone: a model that draws more branches has more volume at every t,
  and the ratio cancels it.
- **The rule:**
  - target = r_J0(t\*);
  - **t_T** = the grid t whose r_a1(t) is closest to the target; ties to the larger t;
  - t_T = 0.50 if t\* = 0.50, or if a1's own vol(0.50) on U40 already reaches Janus 0's vol(t\*) (a1 learned the width);
  - t_T is posted on #302 (`transfer.json` and its sha256) **before** `collect` scores the locked 100.
- **The candidate is a1 at t_T.** When nothing shifted, t_T = t\* and the plan is L-A4's unchanged.
- **Why not re-run Rule W on a1:** a1 has trained on the 60, so its Dice there is a training score.
- **Why not leave t\* frozen with only the after-look report:** the report cannot act on this model, and the failure it
  would find, a sharpened rim that hands H2 back to chance, is the one this track's adoption depends on.
- **Self-test:** the same profile keeps t\*; a rim twice as sharp moves 0.40 → 0.35; a locked id is refused.
- **Cost:** Janus 0, a1 and a2 predict U40 with probabilities in the E + collect job: 120 predictions, ≈ 1.5 GPU-h. The
  `.npz` files are reduced to curves and deleted.

**Risk I accept:** matching inflation assumes the right width for a1 is "Janus 0's width at t\*". If a1 had genuinely
learned a wider boundary, the guard clause catches it (its own vol(0.50) reaches Janus 0's vol(t\*)). A partial
learned widening would make t_T slightly too low; H1's FP and class guards still see the cost.

## 4. Job 0 has not run: what each result changes (item 4)

The lead runs Step T and Job 0 on Fir and Trillium. **Nothing below changes a margin** (L-A7).

| Job 0 result | Then |
|---|---|
| **L0 fails** (val-80 macro outside 0.909 ± 0.003, a class beyond 0.01, or < 95 % of cases within 0.01 of Fir) | Stop (L-A8). The usual causes, in order: the aortas (A1 ostia), the CT layout (`pool_thick`), the nnU-Net version, the plans copy. No training job is submitted until it passes |
| **t\* = 0.50** | The export lever is empty. H2 tests the network alone, and its pass probability is near α (0.025, Crucible's power note). The expected verdict becomes the Q4 branch. Rule T is moot. The 0.45 mm width arm (§6.2) becomes the width plan, as Janus 1-L.2 |
| **t\* ∈ {0.45, 0.40}** (Crucible's prediction) | The plan as written |
| **t\* = 0.35 or 0.30**, or FP rises at every t < 0.50 | Rim miscalibration or dim neighbours. Before any training job: a calibration report on the 60 (reliability of the summed vessel probability in rim bins). If FP passes Rule W's guard, t\* stands; Rule T matters most here, because a deep threshold is the most sensitive to a sharper a1 |
| **Dice at t\* more than 0.03 below 0.934** on the 60, with volume ratio ≥ 0.95 | The bias is gone and the grid binds: the 0.45 mm arm (§6.2) is triggered, after a1's look |
| **Rule W's Dice gain on the 60 < 0.005** | H2 is unlikely to pass even if t\* transfers; say so in the verdict's expectation line before the look |
| **Janus 0's per-case SD on the locked 100** | Restates the stated MDE (formula below). Never moves −0.02, −0.015 or −0.03 |
| **The decomposition (§5)** | Decides which arm, if any, follows a1 |

**Restating the MDE from Job 0 (a report written before training):**
- tF1: SD_Δ = SD_J0 · √(2(1 − ρ)), with ρ = 1 − SD_Δ,old² / (2 SD_old²) from the three paired val-80 files
  (SD_Δ 0.038–0.046, Foxtrot). MDE₈₀ = 2.80 · SD_Δ / √n, n = the decisive cases (≈ 100).
- Dice: the same with Janus 0's per-case whole-tree Dice SD (round 1: 0.010–0.023 paired, MDE 0.003–0.006).
- Posted as one line on #302 with Job 0's outputs.

## 5. The 60-case error decomposition (item 5)

**Code:** `experiments/Atlas/j1l/r2_error_decomp.py` (self-tested; CPU; refuses any locked-100 or sealed id).

**What it does.** It re-runs the frozen metric's recall computation (the same crop, ostia, 1.5 mm growth and
small-component cleaning as icx4's in-job score) and keeps the reason each reference centreline point is lost:

| Group | Points | Meaning | Lever it would justify |
|---|---|---|---|
| **BREAKS** | `break_disc` (drawn but not rooted) + `break_gap` (the cut itself) | A vessel cut off from its ostium | A connectivity lever. **Not** Skeleton Recall, which recovers branches without connecting them (BCS, Delta's verified note) |
| **NAMING** | `naming` (+ `in_other` on the precision side) | Drawn and rooted, wrong class | The namer or class balance; no topology arm |
| **EXTENT** | `distal` (a tip or side branch stopped early) + `absent` (a tree not drawn) | Missing vessel | **Skeleton Recall** (recovers branches: Kirchhoff et al., Table 2) |
| HOLE | `hole` | A gap under 1.5 mm, bridged | Width-like; the threshold should shrink it |

Self-tested on synthetic trees: a 3 mm cut → break_gap + break_disc; a 1 mm hole → hole; an LCx named LAD → naming;
a short LCx → distal; no RCA → absent. In every case the `hit` fraction equals the frozen metric's recall exactly, and
on real cases the script records any mismatch per case.

**Counterfactual gains.** For each group, tF1 is recomputed with that group's lost points counted as found. It is an
upper bound on what a perfect fix of that group alone buys (not additive).

**The decision rule (pre-registered here; applied by the next round, from Janus 0's outputs only):**
- **A group justifies a training arm in 1-L only if its macro counterfactual gain on the 60 is ≥ 0.011**, the
  locked-100 MDE's lower end. A perfect fix worth less cannot be seen on the locked 100, and 1-L has no other set.
- **If EXTENT qualifies** and is the largest group in LCx: Skeleton Recall (w = 1.0, Kirchhoff et al.) is the next arm,
  as a1's recipe plus the loss, two runs (A37), its own look as Janus 1-L.2.
- **If BREAKS qualifies:** no ready lever. The next round reviews connectivity options; Skeleton Recall is excluded
  by the evidence.
- **If NAMING qualifies:** a namer or class-weight question, decided off the locked 100 first.
- **If none qualifies:** no topology or extent arm in 1-L. The track's remaining lever is width (§6.2), and tF1 gains
  wait for the pool.
- The same script run on t\* (`--pred $W/thr/t<t*>`) reports what the threshold does to HOLE and BREAKS.

**The lead's command** (Trillium login node, after Job 0; CPU, ≈ 30–45 min):

```sh
source $HOME/icx14-venv/bin/activate
R=$SCRATCH/asclepius/repo; W=$SCRATCH/j1l_job0; J0=$SCRATCH/janus0
git -C $R pull --ff-only
python $R/experiments/Atlas/j1l/r2_error_decomp.py --selftest
for t in 0.50 $(python -c "import json;print(json.load(open('$W/select.json'))['chosen_t'])"); do
  python $R/experiments/Atlas/j1l/r2_error_decomp.py --pred $W/thr/t$t --icx $J0/icx --aorta $J0/aorta \
    --layout $W/layout.json --lists $R/experiments/Crucible/j1l_r1/lists.json --np 8 \
    --out $W/scores/decomp_tuning60_t$t.json | tail -40
done
```

**Post on #302:** the two printed `summary` blocks (no per-case volumes; the JSON's `worst5` lists only case ids and
fractions).

## 6. The fallbacks, mapped to causes now (item 6)

Every further candidate costs one more look at the locked 100. **So what follows a failure is chosen by a rule fixed
now, reading only reports and Janus 0's outputs, never by browsing the locked-100 numbers.** Each new candidate takes
the next 1-L number (D46 Q7) and gets exactly one look.

### 6.1 H1 fails: run S only on the warm-start signature

**S** (Bridge v1 §3.1): Janus 0's own recipe from scratch on the 620, 1000 epochs, Janus 0's plans, mirroring off,
`checkpoint_final`; ≈ 53 GPU-h at 181 s/epoch, three chained 23:50 jobs. Judged by the same H1–H3 against Janus 0,
at the threshold Rule W gives on Janus 0 (t\*, with Rule T applied to S).

| H1 fails, and the reports show | Cause | Then |
|---|---|---|
| a1 **and** a2 at argmax both have point Δ macro tF1 < 0 | The warm-start penalty (Ash & Adams), seen twice | **S runs, pre-registered, as Janus 1-L.2.** No round needed |
| a1 or a2 at argmax ≥ 0, a1 at t\* fails | The threshold, not the data | No retraining. The track drops the threshold for its next candidate. **a1 at argmax is not adopted**: choosing it after seeing it pass is a best-of. Width moves to §6.2 |
| One class fails (L2 or L3) in a1 only, not in a2's report | Seed noise in one class | Round N+1, from the decomposition on the 60, not the locked 100 |
| FP (A15) fails | The threshold adding dim components | As the threshold row |

S is not pre-registered on any other signature, because nothing else says scratch would help.

### 6.2 The 0.45 mm run is a width arm, not an H1 fallback

It answers "the grid binds", which Job 0 can show before a1 ever trains (Crucible §7: ceiling 0.934 at 0.5 mm,
0.956 at 0.45 mm; 115 mm view; from scratch, ≈ 55–60 GPU-h).
- **Trigger:** Job 0's t\* = 0.50, **or** Dice at t\* still more than 0.03 under 0.934 with volume ratio ≥ 0.95.
- **When:** after a1's look, whatever its verdict, so that the two do not share a look.
- **Its own look,** as the next 1-L number, against the then-current 1-L model (Janus 0 or a1), with H1 on tF1 and H2 on
  Dice. Pre-registered here so the trigger is mechanical; its exact recipe is the next round's.

## 7. #306, frozen (item 7)

### 7.1 The trainer diff (`nnUNetTrainerICX4` against `nnUNetTrainer_segtrain_finetune` → `_coronary` → `_segtrain`)

Read at source in this round:

| Setting | Janus 0 (`nnUNetTrainerICX4`, nnU-Net 2.8.1) | A17a (`nnUNetTrainer_segtrain_finetune`) | Same? |
|---|---|---|---|
| Loss | nnU-Net's DiceCE with deep supervision, plus an **optional class-weighted CE** if `$W/ce_class_weights.json` exists | nnU-Net's DiceCE with deep supervision; no weight hook | **Same only if Janus 0 had no weight file** (§7.2, T-check) |
| Mirroring | Off (`nnUNetTrainerNoMirroring`), training and inference | Off (same override, training and inference) | Yes |
| Sampling, oversampling | nnU-Net default dataloader, `oversample_foreground_percent` 0.33 | Not overridden: the same | Yes |
| Iterations | 250 per epoch, 50 val iterations | Not overridden (unless `SEGTRAIN_ITERATIONS`, which must be unset) | Yes |
| Optimiser | SGD, Nesterov 0.99, weight decay 3e-5, poly per epoch from 1e-2, 1000 epochs | SGD, Nesterov 0.99, weight decay 3e-5, warm-up 2500 iterations then poly per iteration, peak 1e-2, 250 epochs | Intended difference (L-A2) |
| Checkpoint interval | 10 epochs | nnU-Net's default **50**, unless `SEGTRAIN_SAVE_EVERY` | **No: set `SEGTRAIN_SAVE_EVERY=10`** (a kill loses ≤ 30 min, not 2.5 h) |
| Deadline | `ICX4_DEADLINE`, stops two epochs early | `SEGTRAIN_MAX_SECONDS` from process start; pauses without `on_train_end` so `checkpoint_latest` survives | Equivalent if the launcher sets it (≈ 23 h 05 min) |
| Final validation | Runs on the fold's val after the last chunk | Runs on the fold's val (**= the locked 100**) and **saves every case's softmax** (`SEGTRAIN_SAVE_PROBABILITIES` defaults to 1) | **No: must be skipped** (§7.2) |
| CT window | Plans' own (nnU-Net default) | Checks the fixed window unless `SEGTRAIN_CT_WINDOW=off` | `off`, as ruled (L-A2) |
| Sealed guard | In the launcher | `refuse_sealed` on train and val ids in `on_train_start` | Stricter; fine |

**The final validation is the one real hazard.** With fold val = the locked 100, nnU-Net's `perform_actual_validation`
predicts and scores all 100 at the end of each run, writes `summary.json` with per-case Dice, and here also writes
about 1 GB of probabilities per case. That is a locked-100 score of a1 alone, produced before a2 finishes, against
L-A7's "computed once, after both runs are done". It also fills ≈ 200 GB of scratch for two runs.

### 7.2 The spec

**Step T additions** (it has not run, so they cost nothing now):

```sh
# on Fir, in Step T, after the cp lines:
cp $M/fold_0/training_log_*.txt $L/$M/fold_0/ 2>/dev/null; ls $SCRATCH/icx4/ce_class_weights.json 2>&1 | tail -1
grep -c "class-weighted CE" $L/$M/fold_0/training_log_*.txt     # expect 0 in every file
```

Post on #302 with the Step T lines. **If a log shows class-weighted CE, stop:** the A17a trainer would not reproduce
Janus 0's loss, and #306 must add the hook before a1 runs.

**The launcher, `trillium/janus1l/janus1l`** (built from `trillium/icx4`; #306 §1–§2 as amended by L-A10 and here):

| Command | Does | Refuses unless |
|---|---|---|
| `JANUS1L_DRYRUN=1 ./janus1l` | Prints the split pins, `sealed 0`, the Janus 0 checkpoint and `plans.json` sha256, the job scripts | — |
| `./janus1l prepare` (**P**, ≈ 1 GPU-h) | Dataset 718 = the 620 + the locked 100, labels by `territory.to_four`; Janus 0's `plans.json` moved with `nnUNetv2_move_plans_between_datasets`; `nnUNetv2_preprocess`; `splits_final.json` with two identical entries | both list pins (L-A1) and the file hash `19b832fe…4dd3`; no sealed id; **no `plan_experiment`**; `plans.json` byte-identical to Janus 0's (sha256 compared) |
| `./janus1l train a1` / `train a2` (23:50, chain-resumable, `afterok` P) | `nnUNetv2_train 718 3d_fullres 0|1 -tr nnUNetTrainer_janus1l -p nnUNetResEncUNetPlans_60G_iso05` with `SEGTRAIN_FINETUNE_FROM=$JANUS0/…/checkpoint_final.pth`, `SEGTRAIN_CT_WINDOW=off`, `SEGTRAIN_SAVE_EVERY=10`, `SEGTRAIN_MAX_SECONDS=83100`, `SEGTRAIN_SAVE_PROBABILITIES=0`; **final validation skipped** (`nnUNetTrainer_janus1l`: a three-line subclass of `nnUNetTrainer_segtrain_finetune` whose `perform_actual_validation` returns at once; trainer name logged) | Job 0's `select.json` present and its sha256 equal to the one posted (`JANUS1L_SELECT_SHA`); L0 passed (`identity_val80.json`); `SEGTRAIN_ITERATIONS` and `SEGTRAIN_EPOCHS` unset |
| `./janus1l status [a1|a2]` | epoch, s/epoch, LR, chain position | — |
| `./janus1l transfer` (**part of E + collect**, `afterok` a1 and a2; ≈ 1.5 GPU-h) | Janus 0, a1, a2 predict U40 with probabilities; `r2_transfer.py curve` for each; `rule` for a1 (and a2 as a report); writes `transfer.json`, prints its sha256; deletes the `.npz` | U40 pin `f9ccf5c4…b212`; t\* from `select.json` |
| `./janus1l collect` (≈ 1 GPU-h + CPU) | Predicts the locked 100 with a1 (`-f 0`), a2 (`-f 1`), E (`-f 0 1`), `--disable_tta`, probabilities saved; exports each at every grid t; scores everything once with `r9_score_icx4.py` at A1c; applies L-A5 (H1–H3, L3, FP) to **a1 at t_T** against Janus 0 at argmax (Job 0's file); writes the L-A6 reports, σ_g, the val-80/locked-20 split, the 89 never-inspected cases, the §2 wording filled in | `transfer.json` present and its sha256 equal to `JANUS1L_TRANSFER_SHA` (posted before); every candidate scored exactly once (a ledger file refuses a second run) |

**Self-tests** (`./janus1l --selftest`, CPU, before any submission):
- the split pins and the file hash; a locked id or a sealed id in training is refused;
- no plan step: `plans.json` sha256 before and after P are equal to Janus 0's;
- the strict load: `finetune_load` on a mismatched plans file refuses; on the real one, bitwise equality;
- t\* and t_T applied: `threshold_export.py --selftest`, `r2_transfer.py --selftest`, and a synthetic case exported at
  0.40 differs from 0.50;
- `decide.py --selftest` and `r2_error_decomp.py --selftest`;
- the trainer diff above as assertions: `nnUNetTrainer_janus1l` has no mirror axes, `oversample_foreground_percent`
  0.33, 250 iterations, `save_every` 10, and its `perform_actual_validation` does nothing.

**Cost (L-A9 basis, 181 s/epoch):** P ≈ 1; a1, a2 ≈ 13.5 each; transfer ≈ 1.5; collect ≈ 1 → **≈ 30.5 + Job 0 (3–4)
≈ 34–35 GPU-h**, ceiling about 60.

## 8. D28 and naming (item 8)

- **D28:** satisfied by a2 (D46 Q5). a2 is a replicate, never shipped, and gives σ_g for 1-L and 1-F.
- **Janus 1-L.1** = a1 at t_T (t_T = t\* unless Rule T moved it). It is the only model the decision reads as a
  candidate. a2, E, Janus 0 at t\*, and every argmax export are reports under 1-L.1 and take no number.
- **Janus 1-L.2, .3, …** = S (§6.1) or the 0.45 mm run (§6.2) or a §5 arm, each in the order its trigger fires, each
  with one look recorded in `collect`'s ledger.
- **Janus 1-L** = whichever of those the verdicts adopt; until one is, Janus 0 stays the track's model.

## 9. What would change this plan

| Observation | Then |
|---|---|
| Step T's log check finds class-weighted CE in Janus 0's run | Stop; #306 adds the weight hook to the A17a path before a1 |
| Job 0: any row of §4 | As §4 says |
| Rule T: a1 and a2 shift in opposite directions on U40 | The shift is seed noise. t_T still applies to a1 (pre-registered), and the report says so |
| σ_g ≥ 0.01, or E − a1 ≥ +0.005 on the locked 100 (reports) | E's case opens at the pool step (§1) |
| The decomposition finds no group ≥ 0.011 | No extent or topology arm in 1-L |
| The lead prefers E now (D46 Q6) | §1's option B, as written there |

## 10. Code in this PR (CPU; no data touched)

| File | What | Check |
|---|---|---|
| `experiments/Atlas/j1l/r2_error_decomp.py` | §5's decomposition, on the frozen metric | `--selftest`: hit = frozen recall on every fixture; each failure lands in its group; refusals |
| `experiments/Atlas/j1l/r2_transfer.py` | §3's Rule T | `--selftest`: same calibration keeps t\*, sharper rim lowers it; refusals |
| `experiments/Atlas/j1l/u40.json` | The U40 list, its source, both pins | Re-derived by `r2_transfer.py u40` |

## 11. Sources

- Round-1 ruling, L-A1 to L-A12; D46; Crucible v1 (§3.1, §7, its Job 0 script read in full); Bridge v1 §3.1 and §7;
  Delta v1 §3.3–§4; Foxtrot v1 §3.3 and §4.3.
- Code read at source this round: `src/segtrain/tf1.py` (`tree_f1`, `fp_components`); `trillium/icx4/lib/tf1_score.py`;
  `trillium/icx4/lib/icx4_trainers.py`; `src/segtrain/nnunet_ext/` (`nnUNetTrainer_segtrain`, `_coronary`, `_finetune`,
  `ct_window`); `trillium/fetch_cases.py` (D22's 200 unlabelled cases); `configs/segqueue14/` (no ImageCAS volume in the
  pool list).
- External evidence is unchanged from round 1 and the verified notes (Ash & Adams; Kirchhoff et al.; BCS; Mehrtash et
  al. as Foxtrot cites it). No new external claim is made.
