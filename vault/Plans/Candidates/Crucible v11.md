---
tags: [plans, candidate, round-10, fir, four-class, D35, D27, A10, A17, A22, A31, Janus]
author: Crucible
round: 10
version: 11
updated: 2026-10-25
issue: christianGRogers/Asclepius#113
---

# Crucible v11: a 35-patient decision set drawn across the reserve, a seal sized on D35's measured contrast, and a cheap warm Janus 1 gated on ImageCAS-X

## 0. Improve or start again?

**Improve.** v10's frame held: icx4 is now Janus 0, A10 sits on the pool seal (D27), and seed anchoring was v10's
warning (A31.2). Janus 0's real numbers change three of v10's positions:

1. **v10's P3/P4 (from scratch on ImageCAS-X + pool) is dropped for Janus 1.** No affordable decision set can tell
   warm from scratch (§4), and scratch costs about 4× as much. From-scratch survives only as the recommendation for
   the final retrain (§11, L-c).
2. **The seal question becomes "how correlated are reader and model errors?"** On Janus 0's spread, 150 sealed
   patients are enough if the errors correlate and are not if they are independent. D35 is where this gets measured
   (§3).
3. **Seed anchoring has a measured mechanism.** It is **extent**, not width, and it rewards a model for learning the
   seed (§5). v10 flagged the risk; v11 sizes it and closes the loophole with a gate.

This round's evidence (CPU; code in `experiments/Crucible/r10/`):
- [[Crucible - The open pool after the seal and its reserve is 61 patients from 5 sources, so D35 must be drawn across the reserve]]
- [[Crucible - On Janus 0's spread 150 sealed patients are enough only if reader and model errors correlate, and D35 beyond 35 patients buys almost nothing]]
- [[Crucible - Seed-anchored extent, not lumen width, is what biases A10 on the pool, and it rewards a model for learning the seed]]
- An external citation check (§9). Every item was read at source; five were reworded to what the source says.
- `role:swe` #116: the D35 freeze and guard, task 716 v2, pool fetch and inference, and a Janus 1 Fir launcher.

## 1. Thesis

1. **"About 50 of about 347" is a stale count.**
   - On real patients (D32/D33) the non-sealed, non-ImageCHD pool is **235**, and D35's own 15 % of it is **35**.
   - The primary stratum open after the seal and its 100-patient reserve is **61 patients from 5 sources**, 43 of
     them Taiwan AI CUP.
   - A decision set drawn from those 61 would be unrepresentative and would starve training. So **D35 is drawn
     across the reserve**, within source, and the seal's extension order skips it.
2. **35 patients is the right size.** A22's seed term dominates the variance, so 35 → 50 patients improves the
   minimum detectable effect by only 0.003–0.004. D35 resolves about **0.04–0.05 macro tF1**.
3. **The acceptance set: 150 is not safe on Janus 0's spread unless errors correlate.**
   - P(pass a human-level model) at 150 is 0.76 with independent errors and 0.995 at ρ = 0.5.
   - The seal is sized by **rule D**: the A10 contrast measured on D35 (Janus 0 vs the reads, minus inter-read).
     This replaces A31.1's f/k > 1.2 trigger, which fires 71 % of the time by chance at 30 patients.
   - Default **200** if D35 is not read in time. Cap **227**.
4. **Janus 1 = a warm fine-tune of Janus 0**, on task 716 v2 with ImageCAS-X replay. It is accepted only if it beats
   Janus 0 on D35 **and** holds Janus 0's line on val 80. About 30 Fir GPU-h for both A17 LR arms.
5. **Seed-anchored reads bias A10 through extent.**
   - If anchored readers keep about 75 % of the true centreline, a model that traces the true tree fails A10 by
     0.10–0.12, while a model that learned the seed passes.
   - Width (Janus 0's thin rim) costs about 0.02.
   - The val-80 gate is what stops a fine-tune from buying D35 by shortening vessels.

## 2. The D35 decision set

### 2.1 Counts, reconciled

| | Patients | Note |
|---|---|---|
| Pool (D32/D33 grouping) | 468 (675 volumes) | Not 517: the name heuristic over-split six patients (#87) |
| Sealed | 150 primary + 20 ImageCHD | D27/D32/D33 |
| Non-sealed, non-ImageCHD | **235** | 161 primary + 74 spacing-suspect. "About 347" = 517 − 170, a pre-D32 count |
| Wave-1 note's "198 open" | 198 | Correct, but = 61 primary + 63 ImageCHD + 74 spacing-suspect |
| **Primary, not sealed, not reserved** | **61** (69 volumes) | Sources: Taiwan 43, cy54ttk3fj 8, EpicardialFat 5, VMR 4, Kaggle-CAD 1 |
| Primary reserve (first 100 of the extension order) | 100 (144 volumes) | In five sources every non-sealed patient is reserved |

### 2.2 The rule (frozen before any read of these patients is looked at)

- **Population: the 161 non-sealed primary-stratum patients, reserve included.**
  - Excluded: ImageCHD (D35).
  - Excluded: the three spacing-suspect sources. A mm-based tF1 on a suspect grid decides nothing; D29 keeps them out
    of A10 for the same reason.
- **Size: 35 patients** = D35's 15 % of the real base (235), drawn from its scorable part.
- **Draw:**
  - within source, rank = sha256(`asclepius-d35-round10:` + patient id) ascending;
  - per-source quota by largest remainder of 35 × n_source / 161, with ≥ 1 from every source with ≥ 5 eligible
    patients (the seal's rule).
  - Result (`experiments/Crucible/r10/d35_proposal.json`): Taiwan 12, cy54ttk3fj 5, EpicardialFat 4, VMR 4,
    Kaggle-CAD 3, CardiacCT15 2, TotalSegmentator 2, IDC-rider 1, HeartSR 1, SLAWT 1. That is 35 patients and
    47 volumes, 23 of the patients from the reserve.
- **Patient level:**
  - every volume of a D35 patient is in D35 and is never trained on;
  - decisions score each patient's first volume in serve order (`scoring_volume`, as the seal does);
  - a patient's other volumes are reported.
- **The reserve and the extension order:**
  - A30's extension order is used **skipping D35 patients**, as D32 skipped already-sealed patients. The seal can
    then grow to **227**, not 250.
  - **The seal file is not changed.** The skip is applied when (if) the seal is extended, and is pre-registered
    here.
  - Reserve patients not in D35 stay uninspected until the seal size is fixed (§3), then are released to training.
- **Freeze:**
  - #116 writes `configs/segqueue14/d35-decision-set-2026-10.json` from the committed script, pinned by sha256;
  - the guard refuses D35 patients in training (convert and trainer) and allows them for scoring;
  - the wave-1 tools read the reserve from the same module.
  - **Until #116 merges, no pool read is exported for analysis or training.** Nothing is lost, because no read
    exists yet.

### 2.3 What it buys (paired fine-tune comparisons, Janus 0's spread)

MDE at 80 % power, two-sided α 0.05, including A22's σ_seed = 0.013:

| n patients | Macro, 1 seed/arm | Macro, 2 seeds/arm | LCx, 1 seed/arm |
|---|---|---|---|
| 30 | 0.051 | 0.044 | 0.055–0.074 |
| **35** | **0.049** | **0.042** | 0.052–0.070 |
| 50 | 0.046 | 0.038 | 0.048–0.062 |

- The SDs are the measured paired SDs of trained-network pairs (warm–warm 0.038, scratch–scratch 0.041 macro),
  scaled by Janus 0's / run 1's per-case spread (1.82). Unscaled, the 35-patient MDE is 0.041.
- At f = 1.25 (a harder pool), add about 0.006.
- **D35 can see a domain-adaptation gain of about 0.05 or more. It cannot see warm vs scratch** (§4).
- It also hosts every A31 measurement (§5).

### 2.4 When D35's reads arrive

- Under D23's order (unchanged by D30), **25 of the 35 D35 patients are double-read after about 480 reads** (35 % of
  the 1350-read queue). All 35 are done at about 1190, because TotalSegmentator-cardiac is served last.
- Served first, the 47 volumes would be done after 94 reads. That changes D23's order, so it goes to the lead
  (§11, L-d).

## 3. The acceptance set (A31.1, D27)

**Re-powered on Janus 0's own spread.** Bridge's model, run-1 shape rescaled to Janus 0's per-class SD (LM 0.121,
LAD 0.126, LCx 0.135, RCA 0.079):

| | n = 150 | n = 200 | n = 250 |
|---|---|---|---|
| f = k = 1, independent errors | 0.76 | 0.90 | 0.96 |
| f = k = 1, ρ = 0.5 | 0.995 | 1.0 | 1.0 |
| f = 1.2, independent | 0.51 | 0.71 | 0.85 |

- A model 0.05 worse than a reader passes 0.000 of the time at 150.
- Round 9's "0.97 at 150" used run 1's spread, which is narrower than Janus 0's.

**The sizing rule (rule D), replacing A31.1's f/k > 1.2.**
1. When ≥ 25 D35 patients are double-read, compute per patient and class d = mean over reads of tF1(Janus 0 vs read)
   − inter-read tF1. Decisive trees only (A1/A1b), primary stratum.
2. Centre each class's d at 0 and bootstrap P(all four classes pass D6) at n = 150, 200, 227. The function is
   `p_pass_d` in `experiments/Crucible/r10/r10_seal_rule.py`.
3. The seal becomes the smallest n with P ≥ 0.80. If none reaches it, the seal is 227 and the shortfall is reported
   to the lead.
4. The seal file is extended along the extension order (skipping D35) in one explicit PR, before any sealed read is
   scored. The rest of the reserve is released to training.
5. **If 25 D35 patients are not double-read by the time Janus 1 must train, the seal is 200** (the rule's
   f = k = 1, ρ = 0 answer). The remaining 27 reserve patients are released then.

**Why rule D.** Simulated on Janus 0-shaped worlds, 30 wave-1 patients:
- when errors correlate (ρ = 0.5), rule D keeps the seal at 150–155 with power ≥ 0.96, while f/k extends to about
  200–220;
- when errors are independent, rule D reaches 0.86 expected power at f = 1 (f/k: 0.91);
- in hard worlds both cap.

Rule D measures the quantity A10 depends on. f/k measures two of its three ingredients and assumes the third
(ρ = 0).

## 4. Janus 1: the pool fine-tune recipe

**Warm, not from scratch, costed on Janus 0's real numbers** (192 s/epoch on Fir, A25):

| Option | GPU-h per run | A22 runs | Total | What D35 can say |
|---|---|---|---|---|
| **Warm from Janus 0**, task 716 v2, 250 epochs (A17a trainer: full load, 10-epoch warm-up, poly) | about 13.3 training + about 1.5 preprocessing + 0.5 prediction ≈ **15** | 2 LR arms (A17a 1e-2, A17b 1e-3) | **≈ 30** | Janus 1 vs Janus 0 (MDE about 0.05) |
| From scratch on ImageCAS-X 560 + pool, 1000 epochs (v10 P3/P4) | about 54 + 2 + 1 ≈ 57 | 2 seeds (A22: arms differ < 0.02) | ≈ 115 | Nothing about warm vs scratch: the ImageCAS-era scratch–scratch paired SD gives MDE about 0.05, and the expected difference is < 0.02 |

- Ash & Adams (NeurIPS 2020, arXiv:1910.08475, Table 1) show warm-started networks generalise worse than fresh ones
  trained on the same full data. On CIFAR-10 / ResNet-18 / SGD: 51.7 vs 56.2 % accuracy.
- That is a reason to make the **final** model fresh (§11, L-c). It is not worth 115 GPU-h now for an effect D35
  cannot see.
- Ghafoorian et al. (MICCAI 2017, arXiv:1702.07841): **two** target-domain images fine-tuned to Dice 0.63, against
  0.15 from scratch (0.76 in-domain, 0.005 unadapted). Warm adaptation needs few target cases, which the first
  wave supplies.

**Task 716 v2** (#116; task 716 on `dev` lacks all three):

| Change | Why |
|---|---|
| **ImageCAS-X train 560 is replayed** beside the pool reads; each read is a sample (A11′) | Sequential fine-tuning on a new domain forgets the old one. Gonzalez et al. (arXiv:2010.11008 v1, Table II): prostate, joint 0.77 vs sequential 0.60 Dice on Decathlon. Kirkpatrick et al. (PNAS 2017) for the general case. Replay is the plain remedy |
| **nnU-Net fold-0 val = ImageCAS-X val 80**; no pool read is held out by `segtrain index` | Val 80 is Janus 0's own fold, so the forgetting check comes out of the job itself. Today `segtrain index` would hold out 30 % of pool reads on its own unstratified hash, a second decision set competing with D35 |
| **D35 and reserved patients are refused** in convert and the trainer | D35 must never be trained on; the reserve must stay uninspected until §3 decides |
| Training pool | non-sealed, non-D35, non-reserved primary reads + non-sealed ImageCHD reads (trainable; reported apart under D29) + released reserve. Spacing-suspect volumes are out until re-gridded |

- Kept: icx4's adopted plans, mirroring off, the 60 GB ResEnc network, 250 epochs (`FINETUNE_EPOCHS`).
- Sampling: uniform per sample. Pool reads are about 17 % of samples at first and up to about 37 % once the reserve
  is released.
- No pool-weighting arm. It is an untested knob, and D35 could not resolve it.

**Decision rules for Janus 1 (pre-registered):**

1. **Arm choice (1e-2 vs 1e-3).**
   - The arm comparison is not a superiority test (its MDE is about 0.05).
   - Take **1e-2** (A17's primary) unless it fails the val-80 gate (rule 3) and 1e-3 passes; then take 1e-3.
   - If both fail, Janus 1 is not adopted and Janus 0 stays.
2. **Adopt Janus 1 over Janus 0** if, on D35, the paired macro tF1 gain's seed-inclusive 95 % CI excludes 0.
   - Patient bootstrap; σ_seed = 0.013 added as `r9_score_icx4.paired()` adds it.
   - Otherwise "no gain detected"; Janus 0 stays and Janus 1 is still reported.
   - Per class and per source are reported, and decide nothing (n ≈ 1–12 per source).
3. **The val-80 gate (forgetting and seed-learning).**
   - Janus 1's decisive macro tF1 on val 80 is non-inferior to Janus 0's 0.909 at margin 0.01, with A22's seed term
     in the CI.
   - No class's recall of ImageCAS-X centreline falls by more than 0.02.
   - Open-36 must agree in sign (A26).
   - This is the guard §5 shows is needed: anchored reads reward shortening vessels, and ImageCAS-X does not.
4. **FP gate (A15):** reported on val 80 and D35. It decides only at acceptance.
5. Every Janus k after Janus 1 (more reads, a released reserve) repeats rules 1–4 against its predecessor and against
   Janus 0.

## 5. What seed-anchored team reads measure (A31.2, A31.3, A31.4, L5 groundwork)

**What convention do reads redrawn from a TotalSegmentator seed follow?**
- **Width:** whatever the reader draws (D12). It barely matters to tF1. In the phantom, one voxel of width moves the
  A10 contrast by about 0.02, so Janus 0's rim, one voxel inside ImageCAS-X's (#43), is a second-order term.
- **Extent:** if readers anchor, the seed's. Inter-read cannot see this: anchored pairs agree at 0.95–1.00 whatever
  the seed misses.
- With about 25 % of the centreline missing, a full-extent model's A10 contrast is −0.10 to −0.12 (fail). A
  seed-like model's is −0.01 to −0.02 (pass), though it scores 0.88–0.91 against the truth.
- **A10 on anchored pool reads is biased against a model that traces ImageCAS-X's extent, and a decision set made of
  such reads rewards learning the seed.**

**What is measured, and where:**

| Measurement | Set | Reported | Decides |
|---|---|---|---|
| Seed-vs-read vs inter-read per class (A31.2's flag, Bridge's tool) | D35 + every non-sealed read | With seed-edit sizes (reads adding nothing to the seed; seed removed only as whole components) | The flag → L5 to the lead, as Round 9 set |
| **Extent signature** (new): model-vs-read recall and precision per class; A23 contrast-supported tF1 of the model's extra centreline | D35 | Beside the flag | Reading only. Anchoring shows as precision ≪ recall on contrast-filled extra centreline, with reads that add nothing |
| Rule D contrast d per class (§3) | D35 | With patient-bootstrap CIs | **The seal size** |
| Model-vs-read per source (A31.3) | D35 (+ open training reads for Janus 0 only) | CIs, 1–12 patients per source | Nothing (as Round 9) |
| **Pre-read domain check** (A31.4), report only | Non-sealed, non-reserved volumes (P0 job) | Per source: Janus 0 vs seed plain Dice, **1-voxel-tolerant Dice and volume ratio** (Atlas's addition, `r10_dice_check.measure()`), and the **share of Janus 0's centreline inside the seed** | Nothing. But a source where that share is < 0.85 is one where anchored reads would cost a correct model about 0.05 of A10, a prediction made before any read is seen |

**Per-source domain shift.** The pool is 10 non-sealed primary sources.
- Kim et al. (J Med Imaging 12(1):016002, 2025, Table 1) measured a cross-site Dice drop of 0.053 for nnU-Net on CCTA
  (0.794 internal vs 0.741 external; two sites).
- The M&Ms challenge (Campello et al., IEEE TMI 2021, DOI 10.1109/TMI.2021.3090082, Table IX) found drops of about
  1–6 % DSC on unseen vendors for strong methods, larger for weaker ones.
- So a per-source effect of a few points is expected, and none is resolvable on 1–12 patients per source. The
  aggregate on D35 decides; the per-source table is for the lead.

## 6. The left-tree ostium residual (P2's 0.0079; report only)

- The 0.0079 sits in the left tree in a few val cases: 4.3 % of ostia are more than 2 mm from the expert start, the
  CI's lower bound is 0, and open-36 shows 0.
- **It does not bias A10.** In model-vs-read and inter-read alike, the ostium is found on the **reference read**
  with the same A1 rule. An ostium misplacement shifts both sides of D6's contrast together, to first order.
- On D35 and the seal there is no expert start point, so A1 is the only rule anyway.
- **Report only:** list, per val case, the TotalSegmentator-ostium-to-start distance and the per-class tF1 delta for
  the cases > 2 mm. Delta's `score_tf1.py` already writes both; CPU, minutes, on the existing Fir files.
- No rule change is proposed, and P2 stays closed.

## 7. The Fir jobs (for the lead; account `def-aso22`)

All jobs: 1 × H100 80 GB (`h100:1`), 12 cores, 280 G, 23:50, partition `gpubase_bygpu_b3`, charged to
`def-aso22_gpu`. **Preconditions for both: #116 merged into `dev`** (the D35 freeze and guard, task 716 v2, the
pool fetch and inference, the Janus 1 launcher). The script names below are #116's.

### Job P0: Janus 0 on the non-sealed pool volumes (now, before any read exists). About 2–3 GPU-h

- **Inputs:** D35 (47 volumes), trainable non-reserved primary (the 49 patients of the open 61 not drawn into D35), and ImageCHD and
  spacing-suspect non-sealed (137, report only).
- **Never:** sealed or reserved volumes.
- **Outputs:** Janus 0 predictions and TotalSegmentator aortas (needed for A1 on every later read).
- **Uses:** the Janus 0 baseline on D35; the pre-read domain check (§5).

```sh
# Fir login node, inside tmux
module load StdEnv/2023 python/3.11.5
cd $SCRATCH/asclepius && git -C repo pull --ff-only
python3 repo/trillium/pool/fetch_pool.py --purpose d35 --purpose train --purpose report pool   # CT only; refuses sealed/reserved before any request; resumable
mkdir -p experiments && rm -rf experiments/pool && cp -r repo/trillium/pool experiments/pool && cd experiments/pool
ICX4_CLUSTER=fir ./predict_pool.sh --model $SCRATCH/icx4/nnunet_results/Dataset715_ICX4 --cases $SCRATCH/asclepius/pool --out $SCRATCH/janus0_pool
squeue -u $USER                      # one job; prediction about 0.5 h, aortas about 1.5 h
```

**Then, on the login node (CPU), the pre-read domain check (report only):**

```sh
source $HOME/icx14-venv/bin/activate && cd $SCRATCH/asclepius/repo
python experiments/Bridge/wave1/domain_check.py --pred $SCRATCH/janus0_pool/pred --seeds <seeds-totalseg dir> --out $SCRATCH/janus0_pool/domain_check.json   # #116 item; per source: Dice, tolerant Dice, volume ratio, centreline-in-seed share
```

**Send back:** `domain_check.json`, and the job's `slurm-*.out` if it fails. No sealed volume is fetched or written.

### Job J1: Janus 1, two A17 LR arms (when the start conditions hold). About 30 GPU-h

**Start when all hold:**
1. #116 is merged and P0 is done.
2. ≥ 25 D35 patients are double-read, so rule D has fixed the seal and the reserve is resolved. Under D23's order
   this is about 480 reads; if the lead serves D35 first, about 100 reads plus the training reads below.
3. ≥ 40 trainable primary patients are double-read (about 340 reads with the reserve released).

If condition 2 is not met by then, apply §3's default (seal 200) and go.

```sh
# Girder host: export approved reads (sealed excluded by the export; D35/reserve flagged by the #116 guard)
segqueue14-export --out /srv/segqueue14/export-janus1 --replicas all
# Fir login node, after copying the export to $SCRATCH/janus1_export
cd $SCRATCH/asclepius && git -C repo pull --ff-only
mkdir -p experiments && rm -rf experiments/janus1 && cp -r repo/trillium/janus1 experiments/janus1 && cd experiments/janus1
ICX4_CLUSTER=fir ARM=lr1e2 SEED=1 CHAIN=2 EXPORT=$SCRATCH/janus1_export ./janus1
ICX4_CLUSTER=fir ARM=lr1e3 SEED=1 CHAIN=2 EXPORT=$SCRATCH/janus1_export JANUS1_WORK=$SCRATCH/janus1_lr1e3 ./janus1
grep SBATCH $SCRATCH/janus1/job.sh   # --gpus-per-node=h100:1 --cpus-per-task=12 --mem=280G --time=23:50:00 --account=def-aso22
./janus1 status                      # s/epoch; expect about 190-200 (icx4: 192)
```

**Check the printout:**
- `refused: sealed N, d35 35-patient set M, reserved R` (non-zero counts are expected and correct);
- `train: ImageCAS-X 560 + pool <k> reads`;
- `fold-0 val: ImageCAS-X val 80`;
- the A1c hash line.

**Cost:** each arm is about 15 GPU-h in one 23:50 job (CHAIN=2 leaves a spare that exits in a minute). Range 13–20,
ceiling 2 × 47.

**When `DONE`:**

```sh
./janus1 collect     # results/: val-80/open-36/dev-44 decisive tF1 (in-job aortas), D35 model-vs-read tF1 (score_wave1 with the D35 guard), paired vs Janus 0
```

**Send back** on #113 or its successor: both arms' `results/` (SUMMARY.md, results.json, per-case JSON). The reader
applies §4's rules.

**Not now:** a second seed. It is needed only if a decision rests on an effect under 0.02 (A22), and none of §4's
rules does.

## 8. What would change the plan

| Result | Where | Then |
|---|---|---|
| Rule D picks 227 and P(pass) still < 0.8 | D35 | Report to the lead. A10 is under-powered for the pool. Options: accept with the shortfall stated, or reallocate (a lead decision; changes D27's 150–250) |
| Seed flag fires **and** the extent signature appears (precision ≪ recall on contrast-filled extra centreline) | D35 | L5 is live. §4's val-80 gate becomes binding at acceptance too (recommended answer, §11) |
| Pre-read: the share of Janus 0's centreline inside the seed is < 0.85 in a source | P0 | Expect that source's A10 contrast to be biased about −0.05. Report before reads; decide nothing |
| Janus 1 fails the val-80 gate in both arms | J1 | No Janus 1. Next: the same at 1e-3 with 125 epochs, or replay-weighted. A new arm, costed then |
| Janus 1's D35 gain CI excludes 0 and is ≥ 0.05 | J1 | Janus 1 becomes the base for Janus 2 (released reserve, more reads) |
| No gain detected on D35 | J1 | Janus 0 stays the base. The domain gap is below D35's resolution. Acceptance proceeds on whichever model passes the gates |
| D35 per-source table shows one source with model-vs-read ≥ 0.15 below the rest | D35 | Report. Check that source's QC (spacing, contrast phase) before any training on it |
| D35 inter-read < 0.80 in a class | D35 | A12 re-instruction trigger (unchanged) |

## 9. External evidence (each checked at source, 2026-10-25)

| Source | What it says (table/figure) | Use here |
|---|---|---|
| Ash & Adams, NeurIPS 2020, arXiv:1910.08475 | Table 1: warm start (50 %→100 % data) vs fresh: CIFAR-10 ResNet-18 SGD 51.7 vs 56.2; CIFAR-100 ResNet Adam 35.0 vs 41.4. Fig. 7: shrink-perturb (λ = 0.6) matches fresh accuracy, online setting | The final model should be fresh (§11). Natural images only |
| Ghafoorian et al., MICCAI 2017, arXiv:1702.07841 | WMH MRI, protocol change: unadapted 0.005 Dice; 2 target images: fine-tuned 0.63 vs scratch 0.15 (in-domain 0.76); Fig. 2a by training-set size | Warm adaptation needs few target cases |
| Tajbakhsh et al., IEEE TMI 2016, DOI 10.1109/TMI.2016.2535302 | Fine-tuning ≥ scratch in 4 tasks and more robust to small training sets (abstract) | Same direction. ImageNet source, so weak for our case |
| Kirkpatrick et al., PNAS 2017, DOI 10.1073/pnas.1611835114 | Sequential training forgets earlier tasks; EWC slows learning on important weights | Why task 716 v2 replays ImageCAS-X |
| Gonzalez, Sakas, Mukhopadhyay, arXiv:2010.11008 (v1, 2020) | Table II, prostate T2: joint vs naive sequential Dice 0.77 vs 0.60 (Decathlon), 0.72 vs 0.55 (in-house) | Forgetting in medical segmentation; joint training as the upper bound |
| Bouthillier et al., MLSys 2021, arXiv:2103.03098 | Fig. 3: variance from data sampling, seeds and ordering is the order of published improvements; randomise sources of variation | Supports A22's seed term and §2.3's plateau |
| Christodoulou et al., arXiv:2409.17763 | 221 segmentation papers, 1 with CIs; the runner-up is inside the CI in > 60 % | Why every D35 rule states its MDE |
| Kim et al., J Med Imaging 12(1):016002, 2025, DOI 10.1117/1.JMI.12.1.016002 | Table 1: nnU-Net CCTA Dice 0.794 internal vs 0.741 external (Cleveland → Taipei) | Expected size of per-site shift (§5) |
| Campello et al. (M&Ms), IEEE TMI 2021, DOI 10.1109/TMI.2021.3090082 | Table IX: −1 to −6 % DSC on unseen vendors for strong methods; up to −51 % for weak ones | Multi-vendor shift is real but modest for strong methods |
| Constantinou et al. (OSAIRIS), Clin Oncol 2025, DOI 10.1016/j.clon.2024.10.032 | Planted errors in AI contours: 28 % (head and neck) and 19 % (prostate) survived clinical editing ("anchoring bias") | Readers keep part of what they start from (§5) |
| Fort & Sagot, LAW IV 2010, ACL W10-1807 | Pre-annotation turned random errors into systematic ones copied from the tagger; best annotator 98.1 → 95.8 with a weak pre-annotator | Same mechanism, NLP |
| ImageCAS-X, arXiv:2608.30404, Table 2 | TotalSegmentator 70.5 ± 6.2 Dice against the expert lumen; nnU-Net 89.8; inter-observer 92.8 | The seed is far from ImageCAS-X's lumen, so anchoring is not benign |

Reworded after the check:
- Ghafoorian: the numbers are for 2 images only.
- Gonzalez: v1 authors; Table II averages over orderings.
- M&Ms: the drop is modest for strong methods.
- Rädsch et al. (Nat Mach Intell 2023): not used. Its finding is about example images in instructions, not
  pre-labels.
- Bouthillier: the dominant variance is data sampling, not seeds.

## 10. Risks

| Risk | Detection | Response |
|---|---|---|
| D35 reads arrive late (D23 order) | Read counts | §3's default seal 200 at Janus 1 time; L-d asks to serve D35 first |
| Rule D is noisy at 25–30 patients | Its own bootstrap CIs, reported | Its target (0.8) is met in expectation in the simulated worlds; 227 is the cap |
| Janus 1 learns seed extent | Val-80 gate (§4.3); D35 extent signature | Not adopted |
| ImageCHD in training changes the left-tree prior | Val-80 gate, D35 per class | Remove ImageCHD from 716 v2 in the next Janus if a class drops |
| #116 is not merged when reads start | — | Nothing is exported for analysis or training until it is. The queue itself is unaffected (D23) |
| D35's 12 Taiwan patients dominate the aggregate | Per-source table | Proportional by design (Taiwan is 35 % of eligible patients). Reported |

## 11. Questions for the lead (not assumed in the plan)

- **L5 (seed-anchored acceptance). Recommended:**
  - A10 on the seal stands as D6's test;
  - the accepted model must also be non-inferior to Janus 0 on val 80 (margin 0.01, A22's seed term) and must not
    trip A26's sealed-80 red flag;
  - the D35 extent signature is reported beside A10.
  - Reason: anchored reads cannot tell a correct full-extent model from one that learned the seed; ImageCAS-X can.
- **L6 (ASOCA). Recommended: not now.** The pool already gives 10 scorable external sources, and D35 samples all of
  them.
- **L-c (final retrain). Recommended: from scratch** (Ash & Adams), one seed, about 60–70 GPU-h, when every
  non-sealed read is in.
  - Data: ImageCAS-X train 560 + all trainable pool reads.
  - **Keep val 80 and open-80 untrained**, so the final model can still be checked against Janus k before its single
    seal look.
  - Spending val 80 would remove the only seed-free decision set.
- **L-d (new; changes D23/D30's order). Serve D35's 47 volumes first?** It costs annotators nothing (same reads,
  different order). It brings rule D and every A31 measurement forward from about 480 reads to about 100.
  Recommended: yes.
- **L-e (seal file). Approve the extension skip rule** (the extension order skips D35 patients; cap 227) as part of
  D35. It changes no listed sealed patient.

## 12. Cost

- **CPU here:** about 30 min (census, draws, power, rule simulation, 64-case phantom sweep).
- **Fir:**

  | Job | GPU-h |
  |---|---|
  | P0 | 2–3 |
  | J1 | about 30 |
  | Later Janus k | about 15–30 each |
  | Final from scratch (if L-c) | 60–70 |
  | **Total from now** | **about 110–135** |

- **Annotators:** nothing beyond D23. L-d only reorders.

## 13. Changes since v10

- icx4 is Janus 0 (D34). Its real spread replaces run 1's in every power figure.
- **New:** the D35 decision set (35 patients across the reserve, salt `asclepius-d35-round10:`, 47 volumes), the
  extension skip (cap 227), and rule D for the seal size.
- **Dropped:** the from-scratch P3/P4 arms for the first fine-tune. They are below D35's resolution and cost 4×.
  From-scratch survives for the final retrain only.
- **New:** task 716 v2 (ImageCAS-X replay, val 80 as fold-0 val, D35/reserve refusal) and the val-80 gate.
- **New:** the seed-extent mechanism and its D35 signature. Width is shown second-order.
- **Kept:** A11′ (each read a sample), A22 (the seed rule), A26/A28, the territory collapse, no label change.
