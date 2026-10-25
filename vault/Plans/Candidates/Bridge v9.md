---
tags: [plans/candidate, bridge, statistics, evaluation, fir, four-class, D35, D27, round10]
author: Bridge
round: 10
updated: 2026-10-25
issue: christianGRogers/Asclepius#113
---

# Bridge v9: after Janus 0, decide the seal on wave 1's own spread, keep the reserve whole, and ask Janus 1 one question

## 0. Position

Janus 0 (icx4, D34) is the base: val-80 decisive tF1 0.909 [0.880, 0.932], A26 passed, A15 met, P2 withdrawn. The
recipe stands and is not relitigated. What follows Janus 0 is mostly a question of **which patients are used for
what**, and the numbers in the repository answer more of it than the drafts on #43 assumed. Five findings drive this
plan; each has a note and code in this PR.

1. **The D35 counts were off.** "About 50 of about 347" was counted on the retired name rule and included ImageCHD.
   On real patients the scorable pool for decisions is **161 primary non-sealed patients, 100 of whom are the seal's
   reserve**. D35's own 15 % of the 235 non-sealed, non-ImageCHD patients is **35**.
   ([[Bridge - A 35-patient D35 decision set is drawn from eight sources and is read by mid-queue]])
2. **The 150-patient seal is not 0.97-powered on Janus 0.** Janus 0's per-case spread is wider than run 1's, and at 150
   patients a human-level model passes A10 **0.76** of the time if the pool is like val. But the same number is
   **0.996** if model-vs-read and inter-read fall on the same hard patients (ρ = 0.5), and nothing has measured ρ. So
   the seal is **sized at wave 1 from the one quantity A10 depends on** (rule C), not extended on a surrogate now.
   ([[Bridge - On Janus 0's spread the 150-patient seal is under-powered unless reads and model fail on the same patients]])
3. **Seed-anchored reads move A10 through extent, not width.** On the 80 ImageCAS-X val trees, if both reads keep a
   seed's early stopping points, a model with ImageCAS-X's extent scores 0.24–0.75 tF1 below inter-read in LAD, LCx
   and RCA: A10 would fail a perfect model. With one read anchored the bias flips. A31.2's flag separates the cases
   cleanly (LM excepted), and the signature on real reads is a precision-only deficit.
   ([[Bridge - Seed-anchored reads move A10 through where vessels stop, not through lumen width]])
4. **Run-to-run noise on the master-size network is small, so the decision set's size matters.** Two warm
   fine-tunes from one checkpoint, and two from-scratch trainings, both differ by less than case noise on val 80;
   pooled, the run-to-run SD is at most 0.012 (95 %). A fine-tune with two seeds against the fixed Janus 0 can then
   be judged on 35 decision patients to about **0.02–0.03** macro tF1; warm against from-scratch cannot be judged
   below about 0.04 without three or more seeds per arm.
5. **The wave-1 training path as it stands would not run the plan.** Task 716 trains on pool reads only (no
   ImageCAS-X rehearsal); `segtrain index` would hold out its own 15 % val + 15 % test of pool reads by hash; nothing
   refuses decision-set or reserve volumes; and `segtrain scinet` can only write `--gpus-per-node=<int>`, so on Fir
   it may land on a MIG slice. One role:swe issue (#118, §12) covers all four.

**Janus 1** is therefore one well-seeded question: does a warm fine-tune from Janus 0 on ImageCAS-X train 560 plus
the wave-1 pool reads beat Janus 0 on the D35 decision set, without losing more than 0.02 on val 80? From-scratch
training on ImageCAS-X + pool (Crucible P3/P4) is kept for the final model, where it costs one run instead of a
seeded comparison.

## 1. What Janus 0 settles and what it leaves (read from #43 and the results note)

| Item | Janus 0 | Consequence here |
|---|---|---|
| Decisive val-80 macro tF1 | 0.909 [0.880, 0.932]; LM 0.945, LAD 0.903, LCx 0.857, RCA 0.938 | The base model. Per-class spreads (§3) re-power A10 |
| A15 (FP ≤ 1 per case) | 0.36 on val | Met; the FP lever is closed; FP stays an acceptance criterion |
| Whole-tree Dice | 87.9 on the open 80; tolerant (1 voxel) 0.97; volume ratio 0.86 | Lumen width, a boundary convention. tF1 is unaffected; seeds and reads are compared with tolerant Dice beside plain Dice (§5) |
| P2 | withdrawn (val Δ 0.0079) | The left-ostium residual is report-only (§6) |
| Seed noise | not measured (D28: no Job B) | Bounded here at ≤ 0.012 on master-size pairs (§4); the first Janus-1 job measures it on a fine-tune (two seeds, D28's fallback) |

## 2. The D35 decision set

**Proposed, to be frozen by the judge** (`experiments/Bridge/r10/decision_set_proposal.json`, drawn by
`draw_d35.py` from pool list sha256 `9f968a08…7554` and the seal in force sha256 `e71141b4…0690`):

| | Value |
|---|---|
| Size | **35 patients, 47 volumes.** 15 % of the 235 real non-sealed, non-ImageCHD patients (D35's own rule on the corrected count) |
| Universe | Primary stratum (A10's stratum; ImageCHD out by D35, the 74 spacing-suspect patients out because tF1 cannot score them in mm, D29), **not sealed, not in the seal's 200-step** (`extension_order[:50]`): 111 patients |
| Salt | `asclepius-decision-round10-pool:` |
| Draw | Proportional allocation by source over the 111 (largest remainder, ties by source name); within each source the patients with the smallest sha256(salt + patient) |
| Sources | 8: Taiwan-AICUP 16, Mendeley-SDN-cy54 5, EpicardialFat-CE 4, VMR 4, Kaggle-CAD 3, CardiacCT15 1, RIDER 1, TotalSegmentator 1 |
| Scoring volume | The patient's first volume in the D23 serving order (earliest read); every volume of a decision patient is withheld from training |
| Use | Decides pool fine-tune and recipe questions (A17, A22) by paired model-vs-read tF1 against both reads. **Never trained on.** Val 80 keeps ImageCAS-X questions; the seal keeps its single acceptance look (A19) |

**Reconciling the counts** (`counts.py`):

| Quoted | What it counted | On real patients (D32/D33) |
|---|---|---|
| "about 347" (Atlas, #43) | name-rule patients 517 − 150 − 20, ImageCHD included | non-sealed, non-ImageCHD: **235**; scorable primary: **161** |
| "198 open" (wave-1 note) | 468 − 170 sealed − 100 reserved, every stratum | primary open outside the reserve: **61** (+ 63 ImageCHD + 74 spacing-suspect) |

**The reserve and the extension order.** Decision patients are inspected, so none may ever join the seal. Two ways
to keep them apart were compared:
- outside the whole reserve (`extension_order[:100]`): 61 eligible patients from **five** sources, a set 71 %
  Taiwan;
- **outside the 200-step only, with the 250-step re-stated now** (chosen): the 250-step becomes the next 50 patients
  of `extension_order[50:]` that are not decision patients (14 skipped), continued by the Round 9 rule over primary
  patients the order never listed (13 used). This is D32's skip rule applied to decision patients. No read exists
  yet, so nothing is selected on data; the salted ranking is unchanged; both steps stay at 50 unseen patients.

The training cost is the same either way: until the seal size is decided, 26 open primary patients (28 volumes)
plus 63 ImageCHD and 74 spacing-suspect volumes are trainable.

**Power** (`d35_power.py`; paired SDs measured on the master-size network, §4):

| Comparison on the 35 decision patients | Pool like val (f = 1) | f = 1.5 |
|---|---|---|
| Fine-tune (2 seeds) vs the fixed Janus 0, run-to-run σ ≤ 0.012 | MDE **0.029** (case term alone 0.018) | 0.036 |
| Two recipes, 1 seed each, σ = 0.013 (A22 prior) | 0.055 | 0.059 |
| Warm vs from-scratch, 2 seeds each | 0.041 | 0.046 |

So the set answers "does fine-tuning on pool reads help on the pool" to the size that matters, and does not answer
recipe-vs-recipe questions below 0.04. One question per job (§4).

**Freezing.** The judge adopts the file; a role:swe PR copies it byte for byte to
`configs/segqueue14/decision-set-2026-10.json` with a pinned sha256 and makes `segtrain` refuse its volumes in
`convert` and the trainer exactly as the seal is refused, together with the re-stated reserve. Until that merges, no
read of a listed patient is exported for analysis. Bridge's wave-1 tools already refuse the reserve and the seal;
they allow the decision set.

## 3. The acceptance set (D27), re-powered on Janus 0 (A31.1)

**Janus 0's per-case spread** (recovered from its per-class bootstrap CIs on val 80): LM 0.121, LAD 0.126, LCx
0.135, RCA 0.079, against run 1's 0.081 / 0.078 / 0.111 / 0.079 that Round 9 used. Re-run (`power_r10.py`; it gives
0.972 on run 1, reproducing Round 9's 0.966):

| P(human-level model passes all four classes) | 150 | 200 | 250 |
|---|---|---|---|
| f = k = 1, ρ = 0 (Round 9's model) | **0.76** | 0.91 | 0.97 |
| f = k = 1.2, ρ = 0 | 0.37 | 0.59 | 0.75 |
| f = k = 1, **ρ = 0.5** | **0.996** | 1.00 | 1.00 |
| f = k = 1.2, ρ = 0.5 | 0.89 | 0.98 | 0.99 |

**Recommendation: do not extend now; size the seal at wave 1 by rule C, before any fine-tune trains on reserve
patients.**
- **Rule C:** on the primary non-sealed, non-reserved patients read so far (the decision set and the open primary
  patients, about 49 by the end of the QC-annotatable block), measure per class s_d = SD over patients of
  (model-vs-read − inter-read), with Janus 0 as the model. Seal the smallest of 150 / 200 / 250 whose re-powered
  P(all four pass, δ = 0) = Π_c Φ(0.05 √(n·keep_c) / ŝ_d,c − 1.96) is ≥ 0.80; 250 if none, and report to the lead.
  Then release the reserve patients not sealed to training.
- **Why s_d and not f and k:** A10's power depends only on s_d and the scorable share, and s_d already contains f,
  k and ρ. Simulated on 49 wave-1 patients, rule C keeps 150 every time when ρ = 0.5, moves to 200 two-thirds of the
  time when ρ = 0 and the pool is like val (power after 0.87), and seals 250 whenever the pool is clearly harder.
  The as-written trigger (f or k > 1.2 in any class) extends 47–67 % of the time when nothing is wrong; that fault is
  Bridge's (v8 §5), and rule C replaces it. `report_wave1.py` now computes s_d, ρ and rule C beside the f/k report.
- **Why not extend to 200 now on the surrogate:** it withholds 50 patients (72 volumes) that a measured ρ may show are
  not needed, and waiting costs nothing, provided the reserve stays untrained and uninspected until rule C has run,
  and rule C runs before Janus 1 trains (§7).
- **Pre-registered exact re-run:** the surrogate SDs are ±10–20 %. `power_r10.py --val $SCRATCH/icx4/r9_tf1_val.json`
  on Fir (one CPU minute) replaces the table above. It changes no decision now: rule C decides at wave 1 either way.
- **D27's wording** ("extendable to 200–250 on wave-1 evidence") is respected: the size is set on wave-1 reads.
  Replacing the f/k trigger by rule C is a change to A31.1, put to the judge; it does not touch a D-number.

## 4. The pool fine-tune recipe: Janus 1

**Evidence on noise** (`d35_power.py`, the two master-size pairs on the same val 80):

| Pair | Paired SD (macro) | Macro Δ (case SE) |
|---|---|---|
| atlas3 F1 − F0: two warm fine-tunes from one checkpoint, same seed and data | 0.038 | +0.0047 (0.0043) |
| atlas2 B − run 1: two from-scratch trainings | 0.041 | −0.0027 (0.0046) |

Pooled run-to-run SD: **0.000 point, ≤ 0.012 at 95 %.** Nondeterminism alone typically produces as much
run-to-run variation as a seed change (Summers & Dinneen 2021), so F1 − F0 is a fair re-run.

**Warm fine-tune, not from-scratch, for Janus 1.**

| | Warm fine-tune from Janus 0 (A17a, Atlas F3) | From scratch on ImageCAS-X + pool (Crucible P3/P4) |
|---|---|---|
| Fir cost per run | 250 epochs × ~192 s ≈ 13.3 h + ~1 h preprocess/predict ≈ **14–15 GPU-h** | 1000 epochs ≈ 53 h + ~3 h ≈ **55–60 GPU-h** |
| What A22 needs to compare it with Janus 0 | 2 seeds (D28's fallback) = ~30 GPU-h, MDE 0.029 on D35 | 2 seeds = ~115 GPU-h; vs the warm arm, MDE 0.041 |
| Literature | Fine-tuning ≥ training from scratch, with the gap widest on small data (Tajbakhsh 2016); pretrained weights mainly speed convergence on large data (Raghu 2019) | The cleaner final model once all reads exist: no history of the ImageCAS-X-only optimum |
| Forgetting | Plain fine-tuning forgets the old task (Li & Hoiem 2018); rehearsal of old data limits it under scanner shift in CT (Perkonigg 2021) → **train on ImageCAS-X train 560 + the pool reads** | None by construction |

Wave 1 has 60–120 trainable pool volumes (§7), which is small next to 560: the setting where warm starts help and a
from-scratch run mostly re-learns ImageCAS-X. From-scratch is kept for the **final model** (the lead's open "final
retrain"), where it is one run, not a seeded comparison.

**The Janus-1 job (Fir F2, §8): three runs, concurrent.**
- **W1, W2:** warm fine-tune from Janus 0, A17a trainer, peak LR 1e-2 with warm-up, 250 epochs, two seeds (separate
  runs; nnU-Net does not fix its seed). Data: ImageCAS-X train 560 (collapsed by `territory.py`) + every trainable
  pool read at the trigger, each read a sample (A11′). nnU-Net's fold-0 val split = **ImageCAS-X val 80**, so its
  end-of-training validation predicts val 80 for the forgetting guard; no pool read is held out by `segtrain index`.
- **L:** the same with peak LR 1e-3 (A17b fallback), one seed.
- Cost **≈ 45 GPU-h** (3 × 14–15), one 23:50 job each.

**Decision rule (pre-registered).** Scored by `segtrain.tf1` at the A1c hash `24441cf8…5254` with TotalSegmentator
aortas (A1), model-vs-read averaged over both reads, flagged trees apart (A1b).

| Result | Then |
|---|---|
| D35: mean(W1, W2) − Janus 0 macro tF1, lower 95 % bound > 0 (case bootstrap over the decision patients read, plus the seed term from the two seeds, at least σ = 0.012) **and** val 80: lower bound of the same difference > −0.02 | **The recipe is adopted.** The better-on-D35 of W1/W2 is read as **Janus 1** (D34); its seed-pair difference is the first measured σ on a fine-tune |
| D35 gain not detected, val guard passes | "Not detected" (no adoption). Janus 0 stays; the question repeats at the next wave with more reads; no new arm is added |
| W fails the val guard and L passes both | L's recipe is adopted (A17b fallback), read as Janus 1 |
| Any class on D35 down by more than 0.05 (point) | Report and review that class's worst decision patients before adoption, whatever the macro says |
| Sign reverses on the late-read decision patients (confirmation, as open-36 for val) | Reported, not reversed (A26's rule, carried over) |

**Task 716 does not fit as is** (#88): it trains on pool reads alone, uses `segtrain index`'s default 15 % val + 15 %
test split of pool reads, refuses only the D27 seal, and submits through `segtrain scinet`, which cannot request a
full H100 on Fir. The fix is a task 717 (or 716 v2) with: ImageCAS-X train 560 + pool reads, val = ImageCAS-X val
80, no pool hold-out, refusal of the decision set and the reserve, and a Fir GPU string. It is a role:swe issue
(#118); task 716's plans adoption and the A17 trainer are reused unchanged.

## 5. What seed-anchored reads measure (A31.2, L5)

**Width.** Janus 0 draws the lumen about one voxel inside ImageCAS-X's (#43: plain Dice 0.88, 1-voxel-tolerant
0.97, volume ratio 0.86). Reads redrawn from a TotalSegmentator seed take whatever width the annotator draws (D12).
tF1 is a centreline score with a 1.5 mm tolerance, so width conventions do not move A10.

**Extent** is what tF1 sees, and anchoring acts on it. Measured on the 80 val references
([[Bridge - Seed-anchored reads move A10 through where vessels stop, not through lumen width]]; seeds and readers
modelled as calibre cut-offs, the model = ImageCAS-X's own extent):

| Readers | LAD contrast (model − inter) | LCx | RCA | LM |
|---|---|---|---|---|
| Both independent | +0.006 | +0.002 | +0.001 | 0.000 |
| Both anchored, seed keeps 56 % of the centreline | **−0.34** | **−0.38** | **−0.24** | −0.002 |
| Both anchored, seed keeps 34 % | −0.58 | −0.64 | −0.34 | −0.003 |
| One anchored, one not (34 %) | +0.30 | +0.32 | +0.21 | +0.005 |

[MILD]

Reading:
- **If anchoring happens, it decides A10.** The margin is 0.05.
- **Its direction depends on how many reads are anchored.** Both anchored: biased against an expert-extent model.
  One anchored: biased for any model.
- **A fine-tune on anchored reads learns the seed's extent.** Janus 1 would then pass A10 by stopping where
  TotalSegmentator stops: a silent move away from D8. The Janus-1 val-80 guard (§4) is what catches that.
- **A31.2's flag works in LAD, LCx and RCA.** When both reads are anchored, seed-vs-read equals inter-read exactly;
  with independent readers it sits 0.25–0.80 below. In LM the flag fires either way.

**Proposed for wave 1:**
- **A31.2** is read per class with LM excluded, together with the seed-edit sizes. Both reads of a patient
  anchored = the bias case.
- **A10's report gives recall and precision per class** for model-vs-read and inter-read. A precision-only deficit
  with recall near 1 is an extent mismatch.
- **The A31 domain check** reports plain Dice, 1-voxel-tolerant Dice, volume ratio (`r10_dice_check.measure`) and tF1,
  per source, for Janus 0 against the TotalSegmentator seed. The check is defined on Fir F1's outputs and run on CPU
  once the seeds are on Fir. A source flagged only by a width difference is not domain shift. Model-vs-read per
  source stays report-only (A31.3; n ≈ 5–16 patients per source in the decision set).

## 6. The left-tree ostium residual (report only)

P2's 0.0079 sits entirely in the left tree (LM +0.010, LAD +0.011, LCx +0.011) and in a few val cases (4.3 % of
ostia > 2 mm from the expert start). Bridge's earlier work found the left ostium is the crux of naming and that the
learned ostium already touches the pool ([[Bridge - An aorta-preferred ostium changes nothing, because the learned ostium already touches the pool]]).
What matters for the plan:
- **Paired decisions are unaffected.** Every comparison here (Janus 1 vs Janus 0 on D35 or val, model-vs-read vs
  inter-read in A10) scores both sides against the same reference with the same A1 ostium, so a constant left-tree
  offset cancels. It would bias a paired result only if a fine-tune changed how the prediction roots at the left
  ostium, and that shows up as an LM change, which the per-class table reports.
- **Absolute model-vs-expert numbers are about 0.008 conservative on the left tree.** Report Delta's expert-start
  sensitivity beside the sealed-80 milestone (A26), as a second line, never decisive.
- No GPU and no new rule.

## 7. Order of operations and when wave-1 reads are sufficient

Queue position = volumes of the D23 order (`pool-2026-10.txt`, unchanged by D30) with both reads approved
(`queue_timeline.py`):

| Position | Decision patients scored | Open primary patients for rule C | Trainable pool volumes: before rule C / seal 150 / seal 200 |
|---|---|---|---|
| 200 | 19 | 38 | 21 / 74 / 44 |
| **242** (end of QC-annotatable) | **23** | **49** | 28 / **93** / 60 |
| 300 | 27 | 53 | 28 / 121 / 76 |
| 450 | 29 | 55 | 90 / 203 / 142 |

1. **Now:** the judge freezes the decision set and the re-stated reserve; the swe PR lands the guard. The lead runs
   Fir F0 (CPU, one minute) and Fir F1 (Janus 0 on the 212 allowed volumes + aortas, ~3–4 GPU-h). Neither needs a
   read.
2. **At position ≈ 242** (both reads approved for the QC-annotatable block): export, `score_wave1.py`,
   `report_wave1.py` (CPU). Rule C sets the seal size; the lead confirms the seal-file PR (D32 precedent); the
   remaining reserve is released.
3. **Janus 1 (Fir F2) starts when both hold:** ≥ 60 trainable pool volumes (≥ 120 read samples) and ≥ 20 decision
   patients scored. If rule C keeps 150 or 200, that is position ≈ 242; if it seals 250, it is position ≈ 450 (after
   the ImageCHD block).
4. **Decision** on the decision patients read by then; the late ones (positions 445–600) confirm.

Nothing in the queue order changes (D30). Serving the 12 late decision volumes earlier would make the decision set
complete at position ≈ 242; that touches D23/D30 and is put to the lead as a question (§11 Q3), not assumed.

## 8. Fir jobs for the lead (copy-paste)

Account `def-aso22` (charged to `def-aso22_gpu`); one full H100 SXM5 (`h100:1`), 12 cores, 280 G per job, as icx4.

**F0, now: the exact A10 re-power on Janus 0's own rows (login node, CPU, ~1 min).**

```sh
source $HOME/icx14-venv/bin/activate && cd $SCRATCH/asclepius/repo && git pull --ff-only
python experiments/Bridge/r10/power_r10.py --val $SCRATCH/icx4/r9_tf1_val.json --out $SCRATCH/icx4/r10_power_exact.json
```

Send back: the printed table (it contains no case data). It replaces §3's surrogate table; no decision waits on it.

**F1, now or any time before wave 1 is scored: Janus 0 on the allowed pool volumes, plus aortas (~3–4 GPU-h).**

```sh
cd $SCRATCH/asclepius/repo && git pull --ff-only
bash experiments/Bridge/r10/fir/janus0_pool.sh prepare    # login node: refuses sealed + reserved, fetches 212 CTs (~19 GB) from Girder, stages them
bash experiments/Bridge/r10/fir/janus0_pool.sh submit     # prints the #SBATCH lines, then submits one 6 h job
bash experiments/Bridge/r10/fir/janus0_pool.sh status     # when done: pred 212, aorta 212 of 212
```

- Check the printed header: `--account=def-aso22`, `--gpus-per-node=h100:1`, `--cpus-per-task=12`, `--mem=280G`,
  `--time=06:00:00`. If any line differs, `scancel` it and tell the PM.
- `prepare` must print `{"allowed": 212, "of_which_decision_set": 47, "refused": {"sealed": 325, "reserved": 138}, …}`.
- Send back: the `status` line and `logs/aorta.log`'s `FAILED` lines, if any. No prediction or CT leaves Fir.
- It reuses icx4's venvs and TotalSegmentator weights (`$HOME/icx14-venv`, `$HOME/icx4-tseg-venv`,
  `$SCRATCH/icx4/totalseg`). Copy `$SCRATCH/janus0-pool/pred` to PROJECT or HOME within a month (60-day purge).

**F2, at the §7 trigger, after the role:swe issue #118 has merged: Janus 1, three concurrent runs (~45 GPU-h).**

```sh
# reads export (Girder host): segqueue14-export --out /srv/segqueue14/export-wave1 --replicas all ; move it to $SCRATCH/wave1
cd $SCRATCH/asclepius/repo && git pull --ff-only && source $HOME/icx14-venv/bin/activate
ICX4=$SCRATCH/icx4/nnunet_results/Dataset715_ICX4/nnUNetTrainerICX4__nnUNetResEncUNetPlans_60G_iso05__3d_fullres/fold_0/checkpoint_final.pth
segtrain index   --root $SCRATCH/wave1 --layout nested
segtrain convert --task 717 --zenodo-root $SCRATCH/wave1 --icx-root $SCRATCH/icx4      # refuses A14, D27, D35 and reserved reads
segtrain plan    --task 717 --zenodo-root $SCRATCH/wave1 \
                 --plans-from $SCRATCH/icx4/nnunet_preprocessed/Dataset715_ICX4/nnUNetResEncUNetPlans_60G_iso05.json
segtrain preprocess --task 717
segtrain scinet submit --task 717 --fold 0 --finetune-from $ICX4 --runs-root $SCRATCH/runs-w1 --dry-run   # header: h100:1, 12, 280G, def-aso22
segtrain scinet submit --task 717 --fold 0 --finetune-from $ICX4 --runs-root $SCRATCH/runs-w1
segtrain scinet submit --task 717 --fold 0 --finetune-from $ICX4 --runs-root $SCRATCH/runs-w2
segtrain scinet submit --task 717 --fold 0 --finetune-from $ICX4 --runs-root $SCRATCH/runs-l --arm lr1e3
```

The `--icx-root` flag, task 717 and the Fir GPU string are what the swe issue adds; the commands are final once it
merges, and the swe PR's own test runs `--dry-run` against them. Scoring (CPU) after the three runs: predict the
decision set's scoring volumes with each model (`nnUNetv2_predict`, ~0.2 GPU-h each, in the same jobs) and run
`score_wave1.py` on the decision patients for Janus 0, W1, W2 and L; the paired comparison is a few lines over its
`per_volume.jsonl` (part of the swe issue's acceptance test).

**Cost, Round 10 → Janus 1:** F0 0; F1 ≈ 3–4 GPU-h; F2 ≈ 45 GPU-h. Total **≈ 50 GPU-h**. The final from-scratch
model, when all reads exist, is ≈ 55–60 GPU-h, one run, outside this round.

## 9. What would change the plan

| Evidence | Change |
|---|---|
| F0's exact re-power differs from the surrogate by more than 0.05 at 150 | §3's table is replaced; rule C is unchanged (it uses wave-1's own s_d) |
| Rule C at wave 1 picks 250 and 250 is still < 0.80 | Report to the lead: acceptance at D6's margin is under-powered on this pool at any affordable n; D6's design (per class, all four) is the lead's |
| Wave-1 ρ ≥ 0.5 in every class | The seal stays 150 and 100 reserve patients go to training |
| Seed-vs-read ≥ inter-read − 0.02 and reads add nothing to the seed's extent (A31.2) | §5's reading applies: A10 on the pool is biased against an ImageCAS-X-extent model; L5 goes to the lead with the measured bias |
| Janus 1's two seeds differ by > 0.02 macro on D35 | σ_ft is large; every later fine-tune decision needs ≥ 3 seeds; the recipe question becomes more expensive |
| Fine-tune gain on D35 ≥ 0.03 with val non-inferior | The final model is warm-started too unless a from-scratch run (one, no comparison) is cheaper to defend; the lead decides on the final retrain |
| A gain on D35 with a val loss beyond 0.02 | Domain trade-off: the deployment population is the pool, but D6 is per class; the lead is asked whether ImageCAS-X performance is a constraint |

## 10. Risks

| Risk | Response |
|---|---|
| The decision set is two-thirds read by position 242 | The first decision uses those 23+; late ones confirm; serving them early is a question to the lead (§11) |
| Rule C runs on ~49 patients, mostly from the QC-annotatable sources | Its false-alarm rate is low and its error is the cautious one; the report prints per-source s_d |
| A decision patient leaks into training before the guard merges | The swe guard is the gate for F2; Bridge's wave-1 tools already refuse the seal and the reserve, and the export of decision reads is for scoring only |
| The swe issue is late | F2 waits; F0 and F1 do not depend on it |
| Spacing-suspect volumes in training distort scale | They are a minority of the samples; nnU-Net's scale augmentation covers ±30 %; they can be dropped from F2 by one exclude list if the re-grid QC is not done |

## 11. Questions for the lead

1. **Replace A31.1's f/k trigger by rule C** (seal size from the measured s_d at wave 1), keeping D27's 150–250 range?
   Bridge recommends yes: same protection, about one-tenth of the false alarms (§3).
2. **L5 (seed anchoring).** If wave 1 flags anchoring in LAD, LCx or RCA:
   - **first**, an annotator instruction (no D-number change): trace each vessel past the seed's end to where the
     lumen is no longer distinguishable, then re-measure on the next 30 reads;
   - **if it persists**, A10 on the pool is not the test D6 intends. The lead chooses between two options:
     - accept the seed's extent as the pool convention, which changes D8's meaning for the pool and what Janus 1
       learns;
     - also require the sealed-80 model-vs-ImageCAS-X look (A26) to pass a pre-set line.

   Bridge recommends the instruction now, before wave 1, since it costs nothing and protects D8.
3. **Serve the 12 late decision-set volumes earlier?** It moves 12 volumes up the queue (no volume added or dropped)
   so the decision set is complete by position ≈ 242. This touches D23/D30, so it is the lead's call; without it the
   plan works on the 23 read by then.
4. **Final model: warm or from scratch?** (The lead's open "final retrain".) Bridge recommends deciding after Janus 1:
   if the warm fine-tune's gain is ≥ 0.03, the final model is one from-scratch run on everything not sealed (≈ 55–60
   GPU-h), checked once against the last warm model on D35 and val 80 for non-inferiority.
5. **L6 (ASOCA):** not now; the pool already has 26 external sources.

## 12. role:swe issue: #118 (linked from #113)

"Wave-1 fine-tune path for Round 10": (a) freeze the decision set and the re-stated reserve as pinned config files;
(b) refuse both in `convert` and the trainer, like the D27 seal (the reserve releasable by an explicit PR after rule
C); (c) task 717: ImageCAS-X train 560 (collapsed) + pool reads, fold-0 val = ImageCAS-X val 80, no pool hold-out,
plans adopted from 715; (d) a Fir GPU string for `segtrain scinet` (`h100:1`, 12 cores, 280G); (e) an acceptance test
that dry-runs §8 F2's commands.

## 13. External evidence

All checked 2026-10-25 (DOI, arXiv or publisher page).

| Claim | Source | Used for |
|---|---|---|
| Fine-tuned CNNs match or beat fully trained ones in medical imaging, and are more robust to training-set size | Tajbakhsh et al., *IEEE TMI* 35(5):1299–1312 (2016), doi 10.1109/TMI.2016.2535302 | Warm start for Janus 1 (§4) |
| Transfer from pretrained weights adds little on large medical datasets; its main effect is faster convergence | Raghu, Zhang, Kleinberg, Bengio, NeurIPS 2019, arXiv 1902.07208 | Why the from-scratch final model is defensible once all reads exist (§4) |
| Fine-tuning on a new task degrades the old one unless something preserves it | Li & Hoiem, *Learning without Forgetting*, *IEEE TPAMI* 40:2935–2947 (2018), doi 10.1109/TPAMI.2017.2773081 | ImageCAS-X 560 kept in the fine-tune data; the val-80 guard (§4) |
| Rehearsal of a diverse memory of earlier data limits forgetting under scanner/domain shift, including CT | Perkonigg et al., *Nat Commun* 12:5678 (2021), doi 10.1038/s41467-021-25858-z | Same (§4) |
| Every source of nondeterminism (seed, GPU nondeterminism, a one-bit weight change) gives similar run-to-run variability | Summers & Dinneen, ICML 2021, PMLR 139:9913–9922, arXiv 2103.04514 | Reading atlas3's same-seed re-run as a run-to-run sample (§4) |
| Sample sizes for paired (cross-over) superiority and non-inferiority designs with normal data | Julious, *Stat Med* 23:1921–1986 (2004), doi 10.1002/sim.1783 | MDE and power formulas (§2, §3) |
| Error bars on segmentation rankings are wider than the gaps reported | Christodoulou et al., MICCAI 2024, arXiv 2409.17763 (Fig. 3, Fig. 4b) | Stating every decision's MDE (§2) |
| Scanner/site effects are learnable from images and inflate within-site estimates | Glocker et al., arXiv 1910.04597 (2019) | Per-source reporting and the decision set drawn within source (§2, §5) |
| Adjustment from an anchor is insufficient | Tversky & Kahneman, *Science* 185:1124–1131 (1974), doi 10.1126/science.185.4157.1124 | The anchoring mechanism behind A31.2 (§5) |
| In a clinical deployment of a deep-learning auto-contouring tool (pelvic organs, MR-guided RT), planners often kept the automatic contours unmodified, and the authors report some automation bias | Abdulkadir et al., *Med Phys* 50(10):5969–5977 (2023), doi 10.1002/mp.16676 (abstract read via Europe PMC; full text not reached) | Real-world evidence that an edited starting mask anchors the final one (§5) |
| TotalSegmentator zero-shot coronary Dice 70.5 ± 6.2 against ImageCAS-X | ImageCAS-X, arXiv 2608.30404, Table 2 (verified Round 9) | The seed is clearly worse than a reader, so A31.2's flag is interpretable (§5) |
| Multi-institutional coronary CTA segmentation | Kim et al., *J Med Imaging* 12(1):016002 (2025) (verified Round 9) | Multi-source shift in CCTA (§5) |

## 14. Cost

- **CPU here:** done (counts, draw, power, extension rule, queue timeline, anchoring on 80 references, tests).
- **Fir:** ≈ 50 GPU-h to Janus 1 (F1 3–4, F2 ≈ 45). F0 is a login-node minute.
- **SWE:** one issue (§12).
- **Training reads withheld:** the decision set's 47 volumes permanently; the reserve's 138 until rule C runs, then
  only what it seals.
