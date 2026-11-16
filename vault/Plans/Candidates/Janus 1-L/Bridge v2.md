---
tags: [plans/candidate, bridge, janus1-l, D45, D46, trillium, locked100, round2]
author: Bridge
track: 1-L
round: 2
version: 2
updated: 2026-11-13
issue: christianGRogers/Asclepius#302
---

# Bridge v2 (Janus 1-L): a1 at t\* stays the one candidate, the 60-case error split is ready to run, and #306 is frozen with four fixes found in nnU-Net 2.8.1's own code

## 0. Position, and what changed since v1

Bridge v2 works inside the plan in force: [[Master plan - Janus 1-L]], which is Crucible v1 as amended by L-A1 to L-A12,
with the lead's answers in D46. It answers the eight items of [[Janus 1-L Round 1]] §5. **Step T and Job 0 have not
run**, so every number that depends on them is written as a rule with its outcomes laid out (§4).

**What I concede from v1:**
- **Rule W is the width lever** (L-A4). My Option W chose t on half the locked 100, and that is a look. I drop it.
- **The A17a trainer runs as is with `SEGTRAIN_CT_WINDOW=off`.** I was wrong that it "cannot be used as is" (the
  judge's §3.4).
- **L3 replaces my G3-as-written recall guard.** Delta's 31 % false-alarm finding stands.

**What v2 adds** (all CPU work in `experiments/Bridge/j1l_r2/`):

| Item | What | Where |
|---|---|---|
| §5.1 | What shipping E instead of a1 buys in P(adopt), under a run-level noise model | `mde_restate.py` → `mde_restate.json` |
| §5.3 | A pinned 40-case in-sample set for a t\* transfer report that never touches the locked 100 | `transfer40.py` → `transfer40.json` |
| §5.4 | The MDE restated from Job 0's Janus 0 SDs (one command) | `mde_restate.py --janus0` |
| §5.5 | **The 60-case error decomposition**: script, self-test, the lead's command, and a pre-registered reading | `error_decomp.py` |
| §5.7 | #306's frozen spec, with a diff of the two trainers and **four defects in the plan of record**, found by reading nnU-Net 2.8.1's source | §7 below |

**The four defects:**
1. **Training would crash at its first step.** nnU-Net 2.8.1 copies `dataset_fingerprint.json` in `on_train_start`
   (`nnUNetTrainer.py` l. 972). L-A2 says "no fingerprint", and Step T does not copy Janus 0's. **Step T must add one
   file.** It has not run yet, so this costs nothing now. After the Fir purge it would cost a re-fingerprint, and
   that does not reproduce Janus 0's file.
2. **The plans cannot be "byte-identical".** `nnUNetv2_move_plans_between_datasets` rewrites `dataset_name` and
   `image_reader_writer`. It also needs Janus 0's plans under `nnUNet_preprocessed/Dataset715_ICX4/`, which Step T
   does not create. A byte-identity self-test would fail every time.
3. **With fold val = the locked 100, nnU-Net scores the locked 100 by itself.** Its final validation writes
   `validation/summary.json` with per-class Dice the moment a1 ends, before a2 ends and outside `collect`. L-A7 says
   these numbers are computed once, after both runs. The fix: val = 10 training cases, and the locked 100 is
   predicted only in `collect`.
4. **The A14 sealed guard looks up its lists by a path relative to the installed package.** A non-editable `pip
   install` of segtrain into the venv makes the trainer refuse to start. The fix: install it editable, or set
   `SEGTRAIN_SEALED_LIST` and `SEGTRAIN_POOL_SEAL`.

## 1. The ship candidate: a1, not E (§5 item 1)

**Recommendation:**
- **a1 at t\* stays candidate C** (Janus 1-L.1) and the base for every pool fine-tune.
- E is predicted and reported, with a pre-registered E − a1 paired report.
- E is not put in a1's place for this look.

### 1.1 What E would buy, measured as P(adopt)

E is tested only by replacing a1 in H1–H3 (no second look), so the only question is whether E passes more often than
a1 would.

**The model** (`mde_restate.py`; closed-form normal approximation):
- A single run's true Δ against Janus 0 is N(μ, τ²), where τ is the run-to-run term.
- E's true Δ is N(μ + g, τ²/2), where g is E's own mean gain.
- The case-level standard error is SD/10.

**Two values of τ:**
- **0.004 (central).** The one measured warm pair (atlas3 F1 − F0, val 80) has mean +0.0047 and case SE 0.0043. That
  gives a 1-df estimate of τ ≈ 0.001.
- **0.012 (the floor).** This is A37's 95 % upper bound.

P(pass) for a1 → E, at a neutral recipe (μ = 0):

| τ | SD of Δ | g | H1 macro clause (> −0.02) | Q4 clause (> −0.015) | H3 (> 0) |
|---|---|---|---|---|---|
| 0.004 | 0.038 | 0 | 0.989 → 0.996 | 0.914 → 0.945 | 0.089 → 0.058 |
| 0.004 | 0.051 | 0 | 0.939 → 0.957 | 0.780 → 0.805 | 0.062 → 0.043 |
| 0.004 | 0.051 | 0.005 | 0.939 → 0.995 | 0.780 → 0.957 | 0.062 → 0.196 |
| 0.004 | 0.072 | 0.005 | 0.763 → 0.920 | 0.543 → 0.777 | 0.043 → 0.119 |
| 0.012 | 0.051 | 0 | 0.779 → 0.844 | 0.649 → 0.693 | 0.222 → 0.156 |
| 0.012 | 0.051 | 0.005 | 0.779 → 0.935 | 0.649 → 0.844 | 0.222 → 0.307 |

**Reading:**
- **Foxtrot's variance argument alone is worth 1–3 points at the measured τ.** It is worth 5–7 points only at A37's
  upper bound.
- **Almost all of E's advantage is g**, its mean gain over a single run. No source measures g at M = 2 for tree-F1:
  Mehrtash et al. is M = 50 and Dice. **g cannot be measured before the look.** Every ImageCAS-X case outside the
  locked 100 and the seal is in the 620, and there are no pool reads.
- So pre-registering E means betting on an unmeasured prior. That would be defensible if E cost nothing. It costs
  three things.

### 1.2 What E costs

1. **The parent chain.**
   - L-A11 makes the adopted Janus 1-L the parent of every pool fine-tune.
   - An ensemble cannot be warm-started. Either:
     - the pool child is one network judged against an ensemble parent, so D35's gain test and the G2 guard charge
       every pool fine-tune g before it starts; or
     - every pool wave trains two children and re-ensembles them, which costs about +14 GPU-h per wave, for good.
   - With a1, the parent, the shipped model and the decision object are one network.
2. **The t\* transfer is weaker for E** (an argument, not a measurement).
   - t\* is chosen on one network's probabilities.
   - Averaging two networks pulls disagreeing rim voxels toward the middle. That is the band where t\* < 0.5 acts.
   - So the threshold should move E's volume more than a1's, in the direction of FP and over-widening.
3. **Twice the inference**, for every later use: prelabels, SegQueue and the 1000-case export.

### 1.3 What is pre-registered for E (reports only)

- E's H1–H3 numbers against Janus 0.
- **E − a1, paired**, on decisive macro tF1 and whole-tree Dice, with 95 % CIs.
- **If both lower bounds are > 0**, the verdict records "E is better than a1 on the locked 100 (exploratory)". E then
  becomes the candidate for the track's **next** decision set: the first D35 read, or a later held-out set. It is
  never adopted on this look.

**If the judge prefers E anyway** (D46 Q6 allows it), the only valid form is this:
- E replaces a1 as C in H1–H3, frozen before Job P;
- a1, not E, is the parent of pool fine-tunes;
- G2 compares the pool child against a1;
- D35's gain test compares the child against E, and states g's share.

The E-vs-a1 table above is the price.

## 2. The H1-pass/H2-fail branch, and the wording (§5 item 2)

**D46 Q3 and Q4 are binding.** Q3: Dice counts only after H1. Q4: a non-inferior, not-better a1 is adopted if H1's
lower bound is > −0.015. The five outcomes:

| Outcome | Ships | Verdict text (pre-registered; brackets are filled from `collect`) |
|---|---|---|
| H1 fails | Janus 0 | "Janus 1-L.1 is not adopted: [the failing clause]. Janus 0 remains the track's model." |
| H1 passes, H2 fails, H1 LB ≤ −0.015 | Janus 0 | "Janus 1-L.1 is non-inferior to Janus 0 at 0.02 in tree-F1 (Δ [m], 95 % CI [l, u]) but not at 0.015, and not shown better in lumen width. Janus 0 remains." |
| H1 passes, H2 fails, H1 LB > −0.015 (Q4) | **C = a1 at t\*** | "Janus 1-L is non-inferior to Janus 0 at a pre-specified margin of 0.015 in tree-F1 (Δ [m], 95 % CI [l, u]). It is not shown better in tree-F1 or in lumen width (whole-tree Dice Δ [d], 95 % CI [dl, du]). It is adopted for its larger training set." |
| H1, H2 pass, H3 fails | **C** | "Janus 1-L is better than Janus 0 in lumen width: whole-tree Dice Δ [d] (lower bound [dl]), volume ratio [v0] → [v1]. Its tree-F1 is non-inferior at 0.02 (Δ [m], 95 % CI [l, u]). A tree-F1 gain was not shown. [Share sentence]." |
| H1, H2, H3 pass | **C** | As above, with "and in tree-F1 (lower bound [l] > 0)". |

**Rules for the wording:**
- **What ships under Q4 is C, the tested object** (a1 at t\*). a1 at argmax was never a candidate. Its locked-100
  numbers are a report, so shipping it would be a second, unplanned look.
- **The share sentence** is pre-registered from the L-A6 report (Janus 0 at t\* against Janus 0 at argmax), with
  s = Dice gain of Janus 0 at t\* / Dice gain of C:
  - s ≥ 0.8: "Most of the width gain is the export threshold; the fine-tune adds [1 − s]."
  - s ≤ 0.2: "Most of the width gain is the fine-tune."
  - otherwise: "The threshold and the fine-tune each contribute."
- **CONSORT form** (Piaggio et al. 2012): every non-inferiority claim prints the two-sided 95 % CI beside the margin,
  and superiority is claimed only from that same interval.
- **One gap for the lead (Q-B1).** Under Q4, C could ship with its whole-tree Dice shown *worse* than Janus 0's (the
  upper bound of the Dice Δ < 0). That can happen if t\* transfers badly (§3). D46 Q4 does not exclude this, and I do
  not add a clause to a D-number. The verdict must then say "lumen width worse than Janus 0", and I ask the lead
  whether Q4 should exclude this case.

## 3. The t\* transfer (§5 item 3)

**t\* stays frozen. No pre-registered alternative is better**, for two reasons.

**Why freezing is safe:**
- **A shift can only cost power, not a wrong adoption.**
  - If a1's rim probabilities sit lower than Janus 0's, t\* under-widens, and H2 loses power.
  - If they sit higher, t\* over-widens: FP and the guards rise, and H1 (FP ≤ 1, L3, the class guard) refuses.
  - In neither direction is a worse model adopted beyond H1's own error rates.
- **Every alternative needs out-of-sample probabilities from a1, and there are none.** a1 trains on every non-locked,
  non-sealed ImageCAS-X case.

**How a shift would show without a locked-100 number: report T, in sample on both models.**
- **The set:** 40 train-560 cases. Janus 0 and a1 both trained on them.
  - They are pinned in `transfer40.json`: the smallest `sha256('asclepius-j1l-r2-transfer:' + id)`, list sha256
    `586d728c…647a`.
  - No locked or sealed id is in it.
- **What `collect` does:** predicts the 40 with Janus 0 and with a1, with probabilities (≈ 0.7 GPU-h). Then, on CPU,
  it scores whole-tree Dice and the volume ratio at the five grid t for each model.
- **What it reports:** Δt_in = t_opt(a1, in sample) − t_opt(Janus 0, in sample), and each model's volume ratio at
  t\*.
- **Why in sample:** the two models are equally in sample there (1000 and 1250 epochs on the same 560), so a
  difference between them is a calibration shift, not a held-out effect. It is biased as an *estimate* of a1's
  out-of-sample optimum. That is why it does not choose.

**The pre-registered trigger.** If |Δt_in| ≥ 0.10 (two grid steps):
- the verdict says "t\* transfer doubtful (in-sample shift [Δt_in])";
- the next model in the track re-derives its threshold on its own held-out data (the first D35 reads);
- **C is unchanged.**

After the verdict, L-A6's "C's Dice at every t" shows the locked-100 transfer, as a report.

## 4. Job 0 (§5 item 4): what each result changes

### 4.1 The decision table

| Job 0 result | Then |
|---|---|
| Identity check fails (L-A8) | Stop. Nothing below is read. Round 3 plans around the cause |
| t\* = 0.50 | The export lever is empty, and H2 tests the network alone. The pre-registered prior that H2 passes falls sharply. §6's 0.45 mm swap becomes eligible |
| t\* ∈ {0.45, 0.40} | As predicted (Crucible's E1). The plan of record runs unchanged |
| t\* ∈ {0.35, 0.30} | Possible rim miscalibration. Before training, round 3 reads FP per case and the per-class recall at t\* on the 60. If FP at t\* > FP(0.5) + 0.05, the decomposition's `stray` share is read first |
| Dice at t\* on the 60 > 0.03 under 0.934, with volume ratio ≥ 0.95 | The grid binds. §6's 0.45 mm swap becomes eligible |
| Restated tF1 MDE > 0.025 (§4.2) | H1 and Q4 stay as decided (L-A7). The verdict prints "under-powered regime". The fallback S (§6) weighs less, because its own look would be as weak |

### 4.2 The MDE restatement, ready now

`mde_restate.py --janus0 $W/scores/locked100_janus0_argmax.json`. The method:
- take Janus 0's exact per-class SDs on the locked 100;
- rescale the two measured paired shapes (atlas2 scratch pair, atlas3 warm replicate) class by class;
- report SD(Δ), MDE = 2.80·SD/10, and P(pass) of H1, Q4 and H3 at chosen true effects.

Run now on round 1's recovered SDs, it reproduces round 1's pessimistic row:

| Shape | SD(Δ) | MDE | P(H1 \| 0) | P(H1 \| −0.01) | P(Q4 \| 0) | P(H3 \| +0.005) |
|---|---|---|---|---|---|---|
| Scratch pair × Janus 0's spread | 0.0506 | 0.0142 | 0.977 | 0.506 | 0.842 | 0.165 |
| Warm replicate × Janus 0's spread | 0.0532 | 0.0149 | 0.964 | 0.468 | 0.805 | 0.154 |

**Post on #302 with Job 0's outputs:** the `scenarios` block of `mde_restate.json`.

## 5. The 60-case error decomposition (§5 item 5)

### 5.1 The script

`experiments/Bridge/j1l_r2/error_decomp.py`. It is self-tested (`--selftest`, about 1 min of CPU).

**What it reads:**
- Job 0's argmax export of the tuning 60 (`$W/thr/t0.50`);
- the ImageCAS-X labels, aortas and CTs from Step T.

**What it refuses:**
- any case outside the tuning 60, so never the locked 100 or a sealed case;
- any case where its recomputed recall and precision differ from the frozen A1c `tree_f1` by more than 1e-9.

So the decomposition adds up to the metric of record.

**Every centreline point goes into exactly one category:**

| Group | Recall side (reference centreline of class c) | Precision side (predicted centreline of c) |
|---|---|---|
| **Breaks** | `break`: predicted c, but its piece is not connected to an ostium. `fragment`: in a < 100-voxel piece tF1 drops. `gap`: not predicted, an interior run. `root`: not predicted, the run holds the ostium | — |
| **Naming** | `name`: predicted as another vessel class | `pname`: lies in another reference class |
| **Extent** | `distal`: not predicted, a run ending at a tip. Also reported: the share below A23's contrast line (0.3 × aortic HU) | `overextent`: > 1.5 mm outside the reference, in a rooted piece |
| Other | `absent_fb` (fallback points, A1c) | `edge`: ≤ 1.5 mm outside (width jitter). `stray`: unrooted FP |

**The ceiling of each group** is the mean gain in tF1, per class and as a decisive macro, if that group alone were
fixed:
- missed points become hits;
- wrong predicted points are removed;
- for naming, they move to their true class.

A ceiling is the most a perfect fix could buy, not a forecast.

**Self-test fixtures** (each reproduces `tree_f1` exactly):

| Fixture | Comes out as |
|---|---|
| A 3 mm cut | gap + break |
| LCx drawn as LAD | naming (LCx's naming ceiling = 1.0) |
| Distal truncation | distal |
| An FP bar | stray |
| An attached over-extension | overextent |
| A locked-100 id | refused |

A side finding: skimage 0.26 skeletonises an even-width bar or a cube to **no points at all**. So an isolated FP
blob is invisible to tF1's precision, which is one more reason A15's FP gate is separate.

### 5.2 The lead's command

On the Trillium login node, after Job 0, in the icx14 venv; ≈ 20–40 CPU-min:

```sh
source $HOME/icx14-venv/bin/activate
R=$SCRATCH/asclepius/repo; W=$SCRATCH/j1l_job0; J0=$SCRATCH/janus0
git -C $R pull --ff-only
python $R/experiments/Bridge/j1l_r2/error_decomp.py --selftest
python $R/experiments/Bridge/j1l_r2/error_decomp.py --pred $W/thr/t0.50 --icx $J0/icx --aorta $J0/aorta \
  --layout $W/layout.json --np 8 --out $W/scores/error_decomp_tuning60.json
python $R/experiments/Bridge/j1l_r2/mde_restate.py --janus0 $W/scores/locked100_janus0_argmax.json --out $W/scores/mde_restate.json
```

**Post on #302:** the printed `summary` block, which holds no per-case rows and no volumes, and the `scenarios`
block of `mde_restate.json`.

### 5.3 The pre-registered reading

It is applied to each group's **macro** ceiling. It is printed by the script as `verdict`.

| Ceiling | Reading |
|---|---|
| ≥ 0.030 | An arm of that kind is worth a run in a later round: topology for breaks (e.g. Skeleton Recall), class weighting or the namer for naming. **Why:** a real arm recovers part of a ceiling; 0.030 ≈ 2 × the central MDE, so half of it is visible |
| 0.015–0.030 | Only if a no-training test on these 60 first recovers half of it (bridging under A2's audit, or renaming) |
| < 0.015 | No arm. Even a perfect fix sits under the locked 100's MDE |

**Two more rules:**
- **For extent:** if > 50 % of the `distal` points sit below A23's contrast line, the extent loss is unreachable
  reference, and no extent arm is proposed whatever its ceiling.
- **LCx is named separately:** the script reports its largest group. Bridge v1's claim, that LCx's deficit decides
  the lever, is tested here.

**This decides nothing for Janus 1-L.1.** Round 1 fixed the recipe. The decomposition feeds the round that follows
the verdict, and §6's fallback choice.

## 6. The fallback when H1 fails (§5 item 6)

### 6.1 S is pre-registered now, with its own look

**Why now:** a fallback chosen after seeing *how* a1 failed on the locked 100 is chosen with locked-100 information.
Fixing S's trigger, recipe and test before any look keeps it clean.

**The trigger** (all from numbers `collect` already prints):
- H1 fails;
- **and** a1 at argmax and a2 both have a macro point Δ < 0 against Janus 0. That is the warm-start signature
  (Ash & Adams) in both runs, whatever the threshold did.

If H1 fails otherwise (one class, FP, or L3 with a1 at argmax ≥ 0), there is no S. Janus 0 stays, and the next round
diagnoses from the 60-case decomposition and aggregates (L-A5).

**The recipe:** Janus 0's own recipe, from scratch: 1000 epochs, `nnUNetTrainerICX4`, Janus 0's plans, on the 620.
- **Cost:** 1000 × 181 s ≈ 50.3 h of training, ≈ 53 GPU-h in all, in 3 chained 23:50 jobs.
- No replicate.

**The test:** **Janus 1-L.2** = S at t\*, in the same H1–H3 sequence, against Janus 0, in one look.
- t\* stays Janus 0's.
- Report T (§3) is repeated for S.

**The error cost:**
- Two candidates in the track: a −0.02 model is adopted with probability ≤ 2 × 0.2 % (Bridge v1 §4.3).
- The power cost is nil: S does not need a1 to have failed by a margin.

### 6.2 The 0.45 mm run is not pre-registered as the H1 fallback

- **It answers a different failure.** Its value is width (H2): Crucible's ceiling 0.956 against 0.934. H1 is about
  tree-F1.
- **Combining two changes confounds them.** A from-scratch run at a new spacing that fails could not tell the round
  which change hurt.

**One Job-0 contingency is pre-registered, because it uses no locked-100 number.**
- **If** Job 0 makes the 0.45 mm swap eligible (§4: t\* = 0.50, or the grid binds), **then** S is pre-registered at
  0.45 mm instead of 0.5 mm.
- **Cost:** ≈ 55–60 GPU-h. It needs a plans step and a view check (115 mm).
- **When:** round 3 freezes that before any training job.

Otherwise the 0.45 mm run is left to the round after the verdict.

## 7. #306's spec, frozen (§5 item 7)

### 7.1 The trainers, diffed

`nnUNetTrainerICX4` (Janus 0) against `nnUNetTrainer_segtrain_finetune` → `_coronary` → `_segtrain` (A17a), read
at source, with nnU-Net 2.8.1's base class:

| Setting | ICX4 | A17a fine-tune | Same? |
|---|---|---|---|
| Loss | `super()._build_loss()`: DiceCE + deep supervision. A class-weight hook is read only if `$W/ce_class_weights.json` exists | Inherited, no hook | **Yes**, if the launcher never creates that file (a self-test asserts it is absent) |
| Mirroring, training | `nnUNetTrainerNoMirroring`: axes None | Own override: axes None | Yes |
| Mirroring, inference | `inference_allowed_mirroring_axes = None` | Same | Yes |
| Foreground oversampling | 0.33 (base) | 0.33 (base) | Yes |
| Batch, patch, spacing | Plans | Plans (the same configuration, checked by `finetune_load`) | Yes |
| Iterations | 250 train / 50 val per epoch (base) | 250 / 50 | Yes |
| Optimiser | SGD, Nesterov 0.99, wd 3e-5, poly per epoch from 1e-2 | SGD, Nesterov 0.99, wd 3e-5; per-iteration warm-up to 1e-2, then poly | **Intended difference** (A17a) |
| Epochs | 1000 (`ICX4_EPOCHS`) | 250 | Intended |
| Checkpoint every | 10 epochs | 50 (base), unless `SEGTRAIN_SAVE_EVERY` | **Set `SEGTRAIN_SAVE_EVERY=10`** |
| Chain stop | `ICX4_DEADLINE`: ends via `on_train_end`; resumes from `checkpoint_final` | `SEGTRAIN_MAX_SECONDS`: pauses with `checkpoint_latest`, no `on_train_end` | Different mechanics, same effect. 250 × 181 s = 12.6 h fits one 23:50 job |
| Final validation | Skipped when stopped early | Always; saves the softmax (`SEGTRAIN_SAVE_PROBABILITIES=1`) | See defect 3 |
| Sealed refusal | Launcher only (`lib/sealed.py`) | Also in the trainer (`sealed_guard`) | Stricter. See defect 4 |
| CT window check | None | Present; `SEGTRAIN_CT_WINDOW=off` | L-A2 |
| `torch.compile` | `nnUNet_compile=f` (`job_body.sh`) | Env var, not the trainer | **Set `nnUNet_compile=f`**, so the speed matches the costing basis |

**Conclusion:** "the same recipe" holds, apart from the intended schedule and length, once `SEGTRAIN_SAVE_EVERY=10`,
`nnUNet_compile=f` and the absent class-weight file are fixed by the launcher.

### 7.2 The four defects and their fixes

| # | Defect (source) | Fix |
|---|---|---|
| 1 | `on_train_start` does `shutil.copyfile(<preprocessed>/dataset_fingerprint.json, …)` (`nnUNetTrainer.py` l. 972). With no fingerprint step, a1 and a2 die at start | **Step T copies Janus 0's `$M/dataset_fingerprint.json`** (nnU-Net copied it into the model folder when Janus 0 trained). P places it in the new preprocessed folder. It is unused for training. Do not re-fingerprint |
| 2 | `move_plans_between_datasets` needs `nnUNet_preprocessed/Dataset715_ICX4/<plans>.json`, then rewrites `dataset_name` and `image_reader_writer` (`move_plans_between_datasets.py` l. 23–57) | P first copies Step T's `plans.json` to `$nnUNet_preprocessed/Dataset715_ICX4/nnUNetResEncUNetPlans_60G_iso05.json`. **The self-test compares the two plans with `dataset_name` and `image_reader_writer` removed**, which must be equal, and still runs `finetune_load.check_compatible`. L-A2's "byte-identical" should read "identical except those two fields" |
| 3 | Fold val = the locked 100: the final validation writes `fold_k/validation/summary.json` (Dice on the locked 100) when each run ends, and the pseudo-Dice of every epoch is a locked-100 number | **`splits_final.json` val = the 10 lowest-id cases of the tuning 60** (also in training). nnU-Net only warns (`nnUNetTrainer.py` l. 651). Nothing else changes: val is never back-propagated, and `checkpoint_final` is used. The locked 100 is predicted only in `collect`, after both runs. This also saves ≈ 0.7 GPU-h per run |
| 4 | `sealed_guard` → `proxy.load_sealed()` and `pool_seal` find their files at `Path(__file__).parents[2]`. That path exists only in a checkout. With no list, the trainer refuses | `pip install -e $R` (editable), **or** export `SEGTRAIN_SEALED_LIST=$R/trillium/sealed_test.json` and `SEGTRAIN_POOL_SEAL=$R/configs/segqueue14/sealed-pool-2026-10.json`. The dry run prints both |

**The amended Step T line** (added after the `cp $M/plans.json …` line of [[Master plan - Janus 1-L]] §5):

```sh
cp $M/dataset_fingerprint.json $L/$M/ && (cd $L && sha256sum $M/dataset_fingerprint.json >> SHA256SUMS)
```

### 7.3 The launcher's interface (`trillium/janus1l/janus1l`)

All of it is CPU-light on the login node, except the GPU jobs named.

| Mode | Does | GPU-h |
|---|---|---|
| `JANUS1L_DRYRUN=1 ./janus1l` | Prints the self-tests below; submits nothing | 0 |
| `./janus1l prepare` (P) | Dataset 718 = 620 + locked 100 with `territory.to_four` labels. Places Janus 0's plans and fingerprint (fixes 1, 2), runs `move_plans`, `nnUNetv2_preprocess -c 3d_fullres`, and writes `splits_final.json` (two identical entries; val = 10 tuning cases). **No `plan_experiment`** | ≈ 1 (CPU on the GPU node) |
| `./janus1l train a1` and `train a2` | Fold 0 / fold 1, `nnUNetTrainer_segtrain_finetune`, with `SEGTRAIN_FINETUNE_FROM=$J0/…/checkpoint_final.pth`, `SEGTRAIN_CT_WINDOW=off`, `SEGTRAIN_SAVE_EVERY=10`, `SEGTRAIN_MAX_SECONDS=84600`, `nnUNet_compile=f`. `afterok:P`, concurrent, chain-resumable with `--c` | ≈ 12.6 each |
| `./janus1l collect` | `afterok:a1:a2`. (i) Predicts the locked 100 with a1, a2 and E (`-f 0 1`), `--disable_tta --save_probabilities`. (ii) Predicts transfer40 with Janus 0 and a1 (§3). (iii) Exports at t\* (`threshold_export.py`, t\* from `select.json`, sha256 checked). (iv) Scores with `r9_score_icx4.py`. (v) Runs `decide.py gate`, implementing L-A5 to L-A8, the §1.3 E report, §2's wording and report T | ≈ 3 |
| `./janus1l status` | s/epoch, epoch, `DONE` | 0 |

**The dry run's self-tests**, each printing one line, refusing on any failure:
1. **Split pins:** both list hashes of L-A1 and the file hash `19b832fe…4dd3`. No sealed id and no locked id in
   train; locked 100 ∩ split val = ∅.
2. **The sealed refusal works:** a planted sealed id makes the guard raise.
3. **No plan step:** no `plan_experiment`/`extract_fingerprint` call in the job body (grep). The plans equal Janus 0's
   minus the two fields. `check_compatible` passes.
4. **Strict load:** a CPU build of the network from the plans loads Janus 0's state dict strictly, heads included,
   bitwise (`finetune_load.load_full_state`).
5. **t\* applied:** `select.json` exists, its sha256 matches the value posted on #302 (`J1L_SELECT_SHA256`), and the
   export uses `chosen_t`.
6. **Trainer equivalence:** the table of §7.1 printed from the live classes (oversampling, iterations, mirroring
   axes, loss class, absent class-weight file, `save_every`).
7. **Fixes 1–4:** the fingerprint is present, `SEGTRAIN_SEALED_LIST` resolves, val ∩ locked 100 = ∅.

**The lead's commands, once #306 is merged and Job 0's `select.json` is posted:**

```sh
cd $SCRATCH/asclepius && git -C repo pull --ff-only
rm -rf experiments/janus1l && cp -r repo/trillium/janus1l experiments/janus1l && cd experiments/janus1l
export J0=$SCRATCH/janus0 J1L_JOB0=$SCRATCH/j1l_job0 J1L_SELECT_SHA256=<the sha256 posted on #302>
JANUS1L_DRYRUN=1 ./janus1l          # seven self-test lines, all OK
./janus1l submit                    # P, then a1 + a2 (afterok P), then collect (afterok a1:a2)
./janus1l status                    # after ~2 h: expect ~181 s/epoch
```

**Send back:** `collect`'s `SUMMARY.md` and `gate.json`. They hold no volumes, no weights and no sealed case.

## 8. D28 and naming (§5 item 8)

- **D28** ("the first retrained decision adds a second seed to its control") is met by a2 (D46 Q5): a replicate of
  the candidate, never shipped. Janus 0, the control, cannot gain a seed after the fact. a2 measures σ_g, which D28
  was for.
- **Naming** (D46 Q7, D34, D45):

| Model | Name |
|---|---|
| a1 at t\* | **Janus 1-L.1** |
| S, if triggered (§6) | Janus 1-L.2 |
| The adopted one | **Janus 1-L** |
| a2, E, Janus 0 at t\*, a1 at argmax | Reports under 1-L.1; no number |
| A later pool fine-tune of Janus 1-L | The next 1-L.n in the order read |

## 9. Questions for the lead

**Q-B1.** Under D46 Q4, should a non-inferior a1 still be adopted when its whole-tree Dice is shown *worse* than
Janus 0's (upper bound of the Dice Δ < 0)?
- **Recommended: no.** Add "and Dice not shown worse" to Q4. D8 makes the lumen the target.
- Without an answer, the verdict adopts it and says "lumen width worse".

**Q-B2. Step T: add `dataset_fingerprint.json`** (§7.2, defect 1).
- This is an action, not a decision. It must happen before the Fir purge, about 2026-12-20.

## 10. Cost

| Job | GPU-h |
|---|---|
| Job 0 (unchanged) | 3–4 |
| P | ≈ 1 |
| a1 + a2 (concurrent) | ≈ 25 (2 × 12.6; final validation now on 10 cases) |
| `collect`: 3 × 100 locked predictions + 80 transfer predictions + scoring | ≈ 3 |
| **First jobs in total** | **≈ 32–33** (ceiling ≈ 60) |
| S, only on §6's trigger | +≈ 53 (0.5 mm) or +≈ 55–60 (0.45 mm, if Job 0 swaps it) |

The decomposition and the MDE restatement are CPU, on the login node.

## 11. What would change this plan

| Observation | Then |
|---|---|
| Job 0 results | §4's table |
| The decomposition's macro ceiling for breaks ≥ 0.030 | The next round proposes a topology arm. If naming, a naming arm. If < 0.015 everywhere, no recipe arm; the next lever is data (pool reads) |
| a2 − a1 gives σ_g > 0.012 | §1's table moves to the τ = 0.012 rows. E's case strengthens, for the **next** decision, not this one |
| E − a1 lower bounds > 0 on both tF1 and Dice (§1.3) | E becomes the track's next candidate on a fresh set |
| \|Δt_in\| ≥ 0.10 (§3) | "t\* transfer doubtful". The next model re-derives its threshold |
| The lead answers Q-B1 yes | §2's Q4 row gains "and Dice upper bound ≥ 0" |

## 12. Evidence index

| Claim | Source |
|---|---|
| E against a1 in P(adopt); MDE restated | `experiments/Bridge/j1l_r2/mde_restate.py`, `mde_restate.json` (inputs: `trillium-results/round6/atlas2`, `round7/atlas3`) |
| τ ≈ 0.001 from the measured warm pair; 0.012 is A37's bound | atlas3 F1 − F0, val 80: mean +0.0047, SD 0.0382, SE 0.0043 (computed here); [[Round 10]] A37 |
| The error decomposition reproduces the A1c `tree_f1` | `error_decomp.py --selftest` (6 fixtures, R/P equal to 1e-9) |
| The fingerprint is copied at training start | nnU-Net 2.8.1 `training/nnUNetTrainer/nnUNetTrainer.py` l. 971–973 (wheel read 2026-11-13) |
| `move_plans` rewrites the dataset name and the reader, and needs the source preprocessed plans | nnU-Net 2.8.1 `experiment_planning/plans_for_pretraining/move_plans_between_datasets.py` l. 23–57 |
| val ⊂ train is a warning | nnU-Net 2.8.1 `nnUNetTrainer.py` l. 651–652 |
| The final validation scores the val fold | nnU-Net 2.8.1 `nnUNetTrainer.py` `perform_actual_validation` (l. ~1262 onward) |
| Base sampling and optimiser constants | nnU-Net 2.8.1 `nnUNetTrainer.py` l. 153–158, 196 |
| The trainer chain | `src/segtrain/nnunet_ext/nnUNetTrainer_segtrain{,_coronary,_finetune}.py`, `ct_window.py`, `sealed_guard.py`, `finetune_load.py`; `trillium/icx4/lib/icx4_trainers.py`, `job_body.sh` |
| Non-inferiority reporting | Piaggio et al., JAMA 2012;308:2594 |
| Warm-start penalty | Ash & Adams, NeurIPS 2020, arXiv:1910.08475 |
| Ensembles at M = 50, Dice | Mehrtash et al., IEEE TMI 2020 (as cited by Foxtrot v1; not re-read here) |

No sealed case, no locked-100 number, no pool read and no other advocate's round-2 branch was read for this plan. No
GPU job was run.
