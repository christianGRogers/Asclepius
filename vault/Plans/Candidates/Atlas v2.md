---
tags: [plans, candidate, master, nnunet, multiclass]
author: Atlas
round: 2
version: 2
updated: 2026-10-04
---

# Atlas v2 — one direct 4-class nnU-Net, trained on whichever lumen the humans choose, judged by tree-F1

## 1. Thesis

Train **one** nnU-Net v2 ResEnc model end to end on 4-class labels (LM, LAD, LCx, RCA), at **0.5 mm isotropic
with a 256³ (128 mm) patch**, a **fixed CT window** and **no mirroring**. Start as soon as the humans have fixed
the label convention: 640 of our cases already carry expert per-segment names (ImageCAS-X), so supervised
multiclass training does not have to wait for the team.

The convention decides only the **target**, never the recipe:

- **expert lumen** (option A): ImageCAS-X labels read out to 4 classes;
- **Girder seed** (option B): ImageCAS-X names projected onto our masks.

Every decision is judged by **tree-F1** (tF1): per-class centreline that is correctly named *and* connected to the
ostium. A model that cuts a tree loses there, whatever its Dice.

Two independent checks surround the one model:

- **Bridge's rule labeller** QA-filters the training labels (A4).
- The same labeller is also a **pre-registered competitor for the naming step**, scored on the same val
  predictions at zero GPU cost.

If the direct model's names lose to rules applied to its own vessel mask, the rules take over naming as a
post-processing step. Either way the evidence decides, not the plan's thesis.

What changed since v1:

- the ruling's amendments A1–A6 are built in, not appended;
- the open points are measured where a CPU allows:
  - proxy-vs-rules agreement (median 0.3 % of voxels, all at the carina);
  - a FLOP-calibrated R0 forecast;
  - the loader bottleneck;
  - whether 0.5 mm cuts a thin tree.

## 2. Recipe

### 2.0 Week-0 order of work (A3, A6)

| Step | When | Blocks | Who / cost |
|---|---|---|---|
| **D0: human decision meeting** (§5 of the ruling) | this week | R1 (waits ≤ 1 week, then defaults to B) | Clinical lead + labelling lead. Decides in writing: (1) lumen convention A or B; (2) side-branch convention, territory or trunk; (3) ramus intermedius → LAD, LCx or background; (4) confirm tF1 tolerance 1.5 mm; (5) labelling order (sealed test first); (6) whether 4-class seeds may be shown |
| **R0** | first GPU job, 1-GPU `debugjob` ≤ 2 h | every other GPU job | 2 H100-h. §2.5 |
| CPU prep | now | R1 | Proxy factory (both conventions, both side-branch variants); A4 QA over all 800; TotalSegmentator aorta on all 1000 (for the tF1 ostium); port Delta's tF1 into `src/segtrain/metrics.py` (~1 day); implement gap bridging (~1 day) |

All label variants are produced now, so D0 changes only which file R1 reads: no compute is wasted while waiting.

### 2.1 Labels: two conventions, one pipeline

| Set | Cases | Role |
|---|---|---|
| ImageCAS-X train / val | 560 / 80 | Training / monitoring fold. Proxy labels (below) until the team label for that case exists; then the team label |
| ImageCAS-X test | 160 | 80 go to the **sealed test** with 20 quality-0 cases. The other 80 are never proxy-trained; they enter training only with team labels |
| Quality-0 (ImageCAS-X excluded: motion, step) | 200 | No proxy. 20 go to the sealed test; the rest enter training only with team labels |

**Option A (expert lumen), if D0 chooses it.** The target is the ImageCAS-X lumen with ImageCAS-X names, read out
to 4 classes by the written side-branch rule. Trunk: LM ← 1, LAD ← 2, LCx ← 3, RCA ← 9, everything else
background. Territory: D1, D2, D-Other → LAD; OM, L-PDA, L-PLA, OM-Other → LCx; R-PDA, R-PLA → RCA; IM as D0 says.
SegQueue is re-seeded with the ImageCAS-X lumen (Crucible's no-code-change route), so the team's labels share this
convention.

**Option B (Girder seed; also the default if D0 is silent).** The target is our binary mask, partitioned:

- each mask voxel takes the ImageCAS-X class of the nearest ImageCAS-X voxel within 2 mm (86 % of voxels);
- the remaining voxels inherit a name by geodesic growth inside the mask;
- the 14 classes are then read out as in option A.

This is the convention the team produces when they split the Girder seed (`src/segqueue/protocol.py`,
`docs/SEGQUEUE.md`).

**A4 QA, built into the factory.** Bridge's frozen v3 labeller (4 mm bridging) runs on every proxy label.

- **Option B — voxel rule:** near voxels where the projected name ≠ the labeller's name become nnU-Net's `ignore`
  label. Measured on 172 cases: median **0.26 %** of near voxels per case, 100 % of them within 10 mm of the
  bifurcation (LM 2.7 %, LAD 0.18 %, LCx 0.23 %, RCA 0 %)
  ([[Atlas - The rule labeller disagrees with the projected proxy on 0.3 percent of voxels, all at the carina]]).
- **Option B — case rule:** if the ostium is off by > 5 mm, the LM Dice is < 0.5, or LAD↔LCx swaps exceed 5 %, the
  case is flagged. Flagged cases (10.5 %; ~65 of 640, ≈ 6 analyst-hours) are **excluded from R1 until reviewed**,
  not ignore-masked. In those cases one namer has failed wholesale and up to 70 % of voxels disagree; masking them
  would delete the case's supervision while keeping it in the sampler.
- **Option A:** the names are the experts' own, so there is no projection to distrust. A4 runs as case flags only
  (human review), with no voxel masking.

**Pre-registered convention check (empirical backstop to D0).** On the first 20 team labels, for each label variant
(the chosen one and its alternatives), report against the team labels:

- macro tF1;
- branch-swap rate;
- error within 10 mm of the carina vs elsewhere (ruling §4.1);
- **calibre**: Delta's E7 fraction of centreline in lumen < 4 voxels across (A5);
- merged-lumen Dice against ImageCAS-X lumen, which tells which convention the team actually drew.

Rules:

1. If the variant in use is not the best by macro tF1 (paired bootstrap), switch the proxy for the next wave.
2. If the best variant scores < 0.80 macro tF1, drop proxies from the next wave (team labels only, R1 weights as
   init).
3. If the team drew thin (calibre fraction near ImageCAS-X's 65 %), the spacing ablation A1 becomes mandatory and
   decisive (A5).

**Not adopted: Crucible's 14-class head.** Its purpose was to serve both side-branch conventions without
retraining. D0 fixes the convention before R1, and the convention check can still swap the read-out at the first
wave, at fine-tune cost. A 14-class head adds rare-class Dice terms (L-PDA in ~5 % of cases) with no experiment
showing they are harmless. Kept as an option if D0 leaves the side-branch rule open.

### 2.2 Preprocessing

- nnU-Net v2.8.1, `3d_fullres` only, **never `3d_lowres`**.
- **Target spacing 0.5 mm isotropic.** z is natively 0.5 mm in all 1000 cases; only in-plane is resampled
  (0.29–0.47 → 0.5 mm). Evidence:
  - CT power above 1 cycle/mm is at the noise floor in 12/12 cases;
  - centreline contrast is unchanged;
  - on the thin ImageCAS-X convention, label round-trip Dice is ≥ 0.985 per class at 0.5 mm, against class means of
    0.91–0.94 (per-class minima 0.83–0.87) at 0.8 mm
    ([[Atlas - Resampling to 0.5 mm isotropic loses nothing measurable, 0.7-0.8 mm does]]);
  - **new, on the thin convention:** in the 10 finest-pixel cases a 0.5 mm round trip leaves tree-F1 (0 mm tolerance) at ≥ 0.995 (mean 0.999, β₀ +0.1),
  while 0.8 mm cuts half of them (min 0.935, β₀ up to +7)
    ([[Atlas - On the thin convention a 0.5 mm round trip cuts no tree]]).
  Whether the *network* loses anything at 0.5 mm is ablation A1.
- **Fixed CT window [−300, 1300] HU** (mean 100, sd 400), written into the plans file. nnU-Net's default derives the
  window from labelled voxels:
  - option A: [65, 688] HU, which flattens 38 % of the heart box and maps calcium onto lumen;
  - option B: ≈ [−164, 640] HU, which still saturates calcium.
  ([[Atlas - nnU-Net's automatic CT window on lumen labels flattens 38 percent of the heart box]])
- No heart crop.

### 2.3 Model

- **ResEnc U-Net**, `ResEncUNetPlanner -gpu_memory_target 60 -overwrite_target_spacing 0.5 0.5 0.5`.
- Planner output on the real fingerprint: **256 × 256 × 256 patch, batch 2, 7 stages, 142 M parameters, 69 TFLOP
  per training step**
  ([[Atlas - Every case has 0.5 mm slices and nnU-Net's own planner fixes the patch menu]],
  [[Atlas - A 256³ training step costs 69 TFLOP, and the CPU loader may set the pace]]).
- Why this patch: the whole tree fits in one patch in 98 % of cases, and the LM is inside 97 % of LAD-centred
  training patches. For the ResEnc L preset at native spacing the figures are 0 % and 61 %
  ([[Atlas - A 128 mm patch at 0.5 mm holds the whole tree and the LM in almost every training patch]]).
- Why ResEnc: on nnU-Net Revisited's two large CT tasks, ResEnc L/XL gain +2.1/+2.6 Dice on KiTS and +0.8/+1.0 on
  AMOS over the original (Table 1, verified in
  [[Atlas - The recipe's external numbers checked against the source texts]]).
- Deep supervision on. 5 output channels; `ignore` label = 5 under option B.
- **Fallback if R0 fails:** ResEnc XL preset (~37 GB), 0.5 mm, patch 192 × 256 × 256, 12.9 EFLOP per 1000 epochs. Its
  128 × 128 × 96 mm box holds the left tree's extent in 93 % and the whole tree's in 92 % of the 153 measured cases.

### 2.4 Loss, sampling, augmentation

- **Dice + CE**, nnU-Net default.
- Skeleton Recall is ablation A4. It is judged by tF1 **after** A2 post-processing. On ImageCAS it recovered
  branches but increased component counts
  ([[Delta - Topology losses on coronaries are verified, and they recover branches but do not connect them]]).
- **Sampling: nnU-Net default.** Every class is in ≥ 98.5 % of random 128 mm patches, so no class-balanced sampler
  is needed.
- **Augmentation: nnU-Net defaults with mirroring off on all axes** (`nnUNetTrainerNoMirroring`). TopCoW's
  organisers attribute a winning team's L/R label swaps to mirroring (§5.1, verified).
- Rotation is ablation A3. It is also a **cost lever**: rotation and scaling draws are what make a 256³ sample
  expensive on the CPU (below).

### 2.5 Schedule, R0 and the compute forecast (A6)

**R0** (1-GPU `debugjob`, ≤ 120 min; a 1-GPU Trillium job gets 24 cores and 188 GiB):

1. `nnUNetTrainerBenchmark_5epochs` → peak VRAM, s/epoch.
2. One real epoch with `nnUNet_n_proc_DA` = 12 and = 20 → GPU utilisation and iterations/s, i.e. loader
   saturation.

**Forecast to test.** The network costs 17.2 EFLOP per 1000 epochs. Calibrated against nnU-Net Revisited's measured
35.28 A100-h for ResEnc L on KiTS (≈ 18 % of A100 peak), that is **27 H100-h if the H100 sustains the same fraction
of its peak, and 85 h if it only matches the A100's absolute rate**. Central plan: 45 h, two 24 h links.

**Loader risk.** A 256³ sample costs 0.1–1.4 s on the CPU when no spatial transform is drawn and 4.5–60 s when one
is (mean 6.5 s on a contended VM). That is 5–30 workers to keep up, against 24 cores.
([[Atlas - A 256³ training step costs 69 TFLOP, and the CPU loader may set the pace]])

**R0 acceptance:** ≤ 306 s/epoch (1000 epochs ≤ 85 h) and peak VRAM ≤ 75 GB. If R0 fails:

| Failure | Response |
|---|---|
| VRAM over | Fallback config (§2.3) |
| GPU < 70 % busy (loader-bound) | In order: raise workers to 22; move the spatial transform to the GPU; halve `p_rotation` / `p_scaling` (recorded as a recipe change, and A3 then tests it) |
| s/epoch over | Fallback config |

Every GPU-hour figure below is replaced by R0's measurement once it exists.

Training is a fixed 1000 epochs × 250 iterations; nnU-Net v2 has no early stopping. Checkpoints come every 50
epochs, and `--c` resumes across links.

| Run | What | Epochs | H100-h (forecast) |
|---|---|---|---|
| R0 | benchmark + loader saturation | 5 + 1 | 2 |
| R1 | Baseline on the D0-chosen target; train 560 (minus flagged), monitor val 80 | 1000 | ~45 (27–85) |
| A0 | Baseline, 250 epochs (shared control arm) | 250 | ~11 |
| A1 | Native spacing (160 × 320 × 320, equal compute). **Mandatory and decisive if A5 triggers** | 250 (1000 if mandatory) | ~11 (~45) |
| A2 | Default `CTNormalization` window | 250 | ~11 |
| A3 | Rotation off | 250 | ~11 |
| A4 | + Skeleton Recall, scored after A2 post-processing | 250 | ~12 |

Ablation rule: adopt a variant only if the paired per-case **tF1** difference on the val fold has a bootstrap 95 % CI
excluding 0 in its favour. A0–A4 run as parallel 1-GPU jobs. The binary-init warm start (v1's optional A5) is
**dropped**: its only source, the Girder masks, is either the wrong convention (option A) or already the extent of
the labels (option B).

### 2.6 Post-processing (A2): switchable, judged on the first real predictions

Fixed rules (always on):

- no largest-component logic;
- remove only components < 100 voxels;
- never delete a component ≥ 100 voxels;
- never force left and right apart.

Candidate steps, each **off until it wins on the val fold by tF1** (paired bootstrap) on R1's predictions:

- **P1 gap bridging** (Delta): vessel probability ≥ 0.5; join pieces ≥ 100 voxels to the ostium-bearing component
  of their tree if the gap is ≤ 3 mm (1-voxel-radius tube, class of the orphan). The ostium-bearing component is
  the one touching the TotalSegmentator aorta. False connections it creates are counted: new edges whose tube
  crosses reference background > 2 mm from any reference vessel.
- **P2 label repair** (Delta, `experiments/Delta/postproc.py`, with its regression test): islands relabelled; carina
  errors left alone and flagged.
- **P3 rule renaming** (Bridge's labeller, a **pre-registered competitor for the naming step**). Take the model's
  vessel mask (union of the 4 classes after P1), name it with Bridge's frozen labeller, and score it against the
  model's own names. If the rules win by tF1 on val, they replace the model's names. This answers the two-stage
  argument end to end on the same predictions, at no GPU cost (ruling §4, Bridge).

Each step is evaluated alone and in the order P1 → P2 / P3. The QA flags (Delta §2.5.6) are always computed.

### 2.7 How labels arriving over time are used

| Team labels in hand | Action | Cost |
|---|---|---|
| 0 | D0; R0; CPU prep; R1 + A0–A4 on the D0 target; post-processing P1–P3 judged on R1's val predictions; R1 4-class predictions seed the 200 quality-0 cases if D0 allows | ~95 H100-h |
| first 20 (ImageCAS-X cases) | Convention + calibre check (§2.1) → switch proxy variant / drop proxies / make A1 mandatory, as pre-registered | 2 analyst-hours |
| 100 sealed test (requested first) + 20 double reads | Decisive test set. Inter-rater tF1 ceiling per class | — |
| +150, +300, +600 training labels | Fine-tune the latest model 250 epochs on {team ∪ proxy}; the team label overrides per case; flagged cases re-enter once reviewed | 3 × ~11 h |
| ≥ 600 | Paired run, team-only vs team + proxy; keep the better | ~22 h |
| all 900 non-test | **Final**: from scratch, 1000 epochs. 5-fold ensemble only if the CV ensemble beats the single `all` model by tF1 (CI) | 45–225 h |

## 3. Evaluation (A1)

**Decisive metric: macro tree-F1 @ 1.5 mm** over LM, LAD, LCx, RCA, per case, then averaged over cases; paired
bootstrap 95 % CI for every comparison. Implementation: Delta's `perturb_metrics.score` / `analyse_preds.py`,
ported to `src/segtrain/metrics.py` with a regression test on Delta's E3 perturbations. For each class:

- recall = reference centreline named correctly that lies in a predicted component containing the ostium (pieces
  within 1.5 mm count as connected);
- precision = predicted centreline of the class inside reference voxels of the class.

The **ostium** is a centreline endpoint within 5 mm of the TotalSegmentator aorta, not the thickest-endpoint
heuristic. It is checked on 30 val cases against the ImageCAS-X-derived ostium before the sealed test is scored.

The **1.5 mm tolerance is fixed now**. Only the clinical lead may change it, once, before sealed-test scoring.

**Gate:** false-positive components per case (predicted components touching no reference vessel), ≤ 1 on average.

**Reported alongside, per class:**

- per-class clDice, Dice, HD95;
- β₀ against the reference's own count;
- branch-swap rate;
- LM length error;
- detection;
- for P1, false connections created.

All are stratified by dominance (729 R / 41 L / 30 co), disease and image quality.

**Sealed test:** 100 team-labelled cases (80 ImageCAS-X test + 20 quality-0), used only at milestones. Interim
test until it exists: the 160 ImageCAS-X test cases in the D0 convention.

**Acceptance:**

- tF1 within 5 points of the team's inter-rater tF1 on every class (20 double reads);
- FP components ≤ 1 per case;
- branch-swap rate < 5 %.

## 4. Evidence

| Claim | Evidence |
|---|---|
| z = 0.5 mm in all 1000; planner patch/batch menu; no early stopping in v2 | [[Atlas - Every case has 0.5 mm slices and nnU-Net's own planner fixes the patch menu]] |
| 0.5 mm is lossless for image and labels; 0.7–0.8 mm is not | [[Atlas - Resampling to 0.5 mm isotropic loses nothing measurable, 0.7-0.8 mm does]] |
| On the thin convention a 0.5 mm round trip does not cut trees (tF1) | [[Atlas - On the thin convention a 0.5 mm round trip cuts no tree]] |
| 128 mm patch: tree fits 98 %, LM visible to 97 % of LAD-centred patches; ResEnc L preset 0 % / 61 % | [[Atlas - A 128 mm patch at 0.5 mm holds the whole tree and the LM in almost every training patch]] |
| Default CT window erases fat / saturates calcium | [[Atlas - nnU-Net's automatic CT window on lumen labels flattens 38 percent of the heart box]] |
| 69 TFLOP per step; 27–85 H100-h per 1000 epochs; loader may bind | [[Atlas - A 256³ training step costs 69 TFLOP, and the CPU loader may set the pace]] |
| Proxy and rules disagree on 0.26 % of voxels, all at the carina; 10.5 % of cases flagged | [[Atlas - The rule labeller disagrees with the projected proxy on 0.3 percent of voxels, all at the carina]] |
| ResEnc gains, TopCoW mirroring and winners, Skeleton Recall, Gottlich plateau | [[Atlas - The recipe's external numbers checked against the source texts]] |
| Girder masks are the original ImageCAS labels, ~3.5× the expert lumen, ~47 % non-contrast tissue | [[Crucible - Original binary masks disagree with ImageCAS-X]], [[Bridge - ImageCAS-X names transfer onto our binary masks, which are three times fatter]] |
| Dice and per-class clDice cannot see cut trees; tF1 can | [[Delta - Dice cannot see the errors that break a coronary tree]], [[Delta - A released nnU-Net cuts 3 of 8 test trees that Dice scores at 0.84-0.92]] |
| Rule labeller: 95 % of held-out cases fully right on Girder masks | [[Bridge - A rule-based labeller names LM, LAD, LCx and RCA on our binary masks]] |
| Label repair fixes islands, not a wrong carina | [[Delta - Label repair fixes islands but cannot fix a wrong carina]] |

## 5. Risks and early detection

| Risk | Early signal | Response |
|---|---|---|
| D0 never happens; labels end up a mix of conventions | No written decision after 1 week; first-20 merged-lumen Dice vs ImageCAS-X lumen is bimodal | R1 on B; escalate; the convention check fixes the read-out per wave |
| Team convention matches no proxy variant | First-20 check: best macro tF1 < 0.80 | Team labels only from the next wave; R1 weights as init |
| Team draws thin and 0.5 mm costs connectivity | Calibre fraction (A5); A1 tF1 | A1 decisive; switch to native (equal compute) |
| R0: VRAM or s/epoch over budget | R0 | Fallback 192 × 256 × 256 |
| Loader-bound | R0 GPU utilisation < 70 % | More workers → GPU spatial transform → lower spatial-aug probability |
| Model cuts trees (Delta E8: 3/8 for a small-patch binary model) | tF1 recall vs per-class clDice gap on val; interior gaps > 3 mm | P1 bridging; flag cases; larger context already in place |
| Model mis-names along long vessels | Branch-swap rate on val; P3 beats model names | P3 rule renaming switched on |
| Proxy errors outside the carina | A4 flags; first-20 error outside 10 mm of the carina | Flagged cases held out; review |
| Quality-0 cases (20 %) unseen until labelled | Sealed test includes 20; stratified metrics | Prioritise their labelling |

## 6. Comparison

**Against v1 / the current master.** The same recipe, now coherent with the amendments:

- the convention decision gates R1, and both targets are prepared, so nothing waits on compute;
- every decision is made on tF1 with the FP gate;
- post-processing is switchable and judged;
- Bridge's labeller is both a filter and a measured competitor;
- R0 has a falsifiable forecast;
- the binary-init ablation is dropped as incoherent under both conventions.

**Against Bridge (binary → rules).** The ruling found the patch-context argument refuted at 128 mm. The remaining
question is whether rules name a predicted tree better than the network does. P3 answers that on the same val
predictions, so the master contains Bridge's best version at zero extra GPU cost and no 360 H100-h stage-1 arm.

**Against Crucible (expert lumen, 14-class).** Its convention finding is D0/option A here, with the same re-seeding
route. Its 14-class head is not adopted (§2.1: D0 makes it unnecessary, and it is unmeasured). Self-training on the
quality-0 cases is replaced by team labels, which arrive anyway.

**Against Delta (topology yardstick and repair).** Delta's metric, gate, bridging and repair are the master's
evaluation and post-processing, with an added false-connection count.

## 7. Cost

**GPU (forecast; R0 replaces it):**

- R0: 2 h
- R1: ~45 h (27–85)
- A0–A4: ~56 h (+34 h if A1 is mandatory at 1000 epochs)
- TotalSegmentator aorta, 1000 CTs: ≤ 10 h
- wave fine-tunes: ~33 h
- team-vs-mixed: ~22 h
- final: 45–225 h
- inference: ~3 h

**Total ≈ 220–470 H100-h** (low end: R1 at 45 h, single final model; high end: R1 at 85 h, A1 mandatory, 5-fold final); ~105 h of it before any team label exists.

**CPU:** proxy factory plus A4 QA over 800 cases, ~4 node-hours.

**Engineering:** tF1 port 1 day; bridging 1 day; P3 wrapper 0.5 day.

**Human:**

- D0 meeting;
- review of ~65 flagged proxy cases (~6 h);
- convention check (2 h);
- 20 double reads;
- labelling order (sealed test first).

## 8. Changes since v1

1. **A1:** decisive metric → macro tF1 @ 1.5 mm with an FP-component gate; aorta-contact ostium; tolerance frozen;
   ablation rule applied to tF1.
2. **A2:** post-processing P1 (bridging, with a false-connection count) and P2 (label repair), switchable and
   judged on val; Skeleton Recall judged after them.
3. **A3:** D0 gates R1 (≤ 1 week, default B); option A target defined; all variants prepared now.
4. **A4:** labeller QA specified and measured: voxel `ignore` for the carina disagreements (0.26 %); flagged cases
   (10.5 %) held out for review, not masked. Under option A, flags only. Added P3, the labeller as a naming
   competitor.
5. **A5:** calibre trigger in the first-20 check; A1 mandatory and decisive if the team draws thin. Measured that a
   0.5 mm round trip does not cut thin trees.
6. **A6:** R0 first, with a FLOP-calibrated forecast (27–85 h) and a new loader-saturation check.
7. **Inaccuracies fixed:**
   - 0.8 mm round trip is now stated as class means 0.91–0.94 with per-class minima 0.83–0.87;
   - window height is "≥ 92 % (256/277)" in the extent note;
   - nnU-Net Revisited numbers are from Table 1, not Table 2;
   - the external citations are now verified in a vault note.
8. **Dropped:** v1's optional binary-init ablation.
9. **Cost re-estimated:** 220–470 H100-h (was 240–460), now FLOP-calibrated.
