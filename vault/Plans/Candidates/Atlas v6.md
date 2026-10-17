---
tags: [plans, candidate, master, nnunet, multiclass]
author: Atlas
round: 6
version: 6
updated: 2026-10-10
---

# Atlas v6 — the master recipe under the Round 5 ruling: aorta ostium of record, frozen metric, two reads without name-conflict `ignore`, and run 2 built

## 00. What changed with the Round 5 ruling (v6)

v6 is v5 conformed to [[Round 5]] (A1 revised, A1a–c, A2 narrowed, A4 absent-LM guard, A7 settled, A11′, A15,
A16), with Atlas run 2 **built** (`trillium/atlas2/`, READY) and pre-registered in
[[Atlas - Pending Trillium run 2, A1 re-score, FP census and the window ablation]].

| Ruling | What v6 does |
|---|---|
| **A1** ostium of record = reference centreline voxel nearest the TotalSegmentator aorta, per component and side; `thick`/`pool_thick` cross-check, > 5 mm flags | §3 rewritten; run 2 re-scores run 1 with it (TotalSegmentator on the node, weights fetched on the login node) |
| **A1a** no aorta → decides nothing; **A1b** flagged trees reported apart and out of decisive aggregates; **A1c** metric frozen by hash | Run 2 refuses to start unless `segtrain.tf1` has the frozen sha256 (`3c737cbc…9253`); every decisive number is "unflagged, aorta-present" |
| **A2** P1 removed; P1′ only on Delta's stricter table | §2.6: P1 struck; P1′ waits for Delta; P2 stays |
| **A4** absent-LM proxies/reads never auto-excluded on `lm`/`ostium` triggers | §2.1 (A4 QA and the A11′ third-read triggers) |
| **A7** R and H retired as shipping candidates | §2.6: QA only (A4, decision extractor, structural audit) |
| **A11′** each read a sample, **no name-conflict `ignore`** | §1 / §2.1: the voxel rule is gone; the case-level third-read rule stays; A11 test re-specified (A11′ vs agree-or-ignore, decided against the reads, only if A12a finds habits) |
| **A15** FP gate stays (≤ 1/case, raw), an acceptance criterion; the census routes the lever | §2.6 and §3; run 2's census categories pre-registered |
| **A16** run 2 approved, R1 at full length after it; Skeleton Recall (ablation A4) deprioritised | §2.0/§2.5/§2.4; run 2 also predicts the 36 clean open test cases for Bridge |
| Contested fact: c0717 / c0560 are ostium artefacts (Delta, 69 RCA truth points) | Accepted; v5's "≈ 6/80 real" becomes **≈ 4/80 real partial mid-tree cuts (3 LCx)** |
| Corrected tF1 | Only the bounds 0.846–0.895 stand until run 2's A1 re-score; v5's 0.871 was an optimistic selection and is withdrawn as an estimate |



## 0. What the first GPU run measured (round 5)

Source: [[Atlas - Trillium R0 and short R1 results]] (`trillium-results/round5/atlas/`) and Bridge's inference-only
arms on the same checkpoint (A13 worked as designed).

| Question | Measured | Consequence in this plan |
|---|---|---|
| R0 speed / memory (A6) | **174.9 s / epoch**, 55.6 GiB reserved, loader wait 0.02 % | Passes; 1000 epochs = **48.6 H100-h**; loader and memory levers and the fallback patch retired (§2.5) |
| Does the direct model name well? | Swaps 0.9 %; R −0.013, H −0.013 vs its own names; oracle headroom +0.010 | **A7: ship the model's names**; R and H stay QA (§2.6) |
| Cut trees (clDice − tF1 > 0.10) | 17 flagged, but 11 are whole-tree zeros caused by the provisional `thick` ostium (RCA root 32–64 mm off in 5 of 13 RCAs with an ImageCAS-X start point); ≈ 6/80 real | LAD/LCx "few cuts" (gap 0.017 / 0.021); RCA middle band (0.070) until re-scored with the A1 ostium; P1′ stays Delta's C2 decision (§2.6, §3) |
| tF1 @1.5 | 0.846 as scored; 0.871 with the better of two provisional ostium rules; ≤ 0.900 (clDice) | Provisional (A9); biased low on the RCA |
| FP gate (≤ 1, raw) | **1.49** per case (CI 1.21–1.78), broad (38/80 cases ≥ 2); weakly tracks ImageCAS-X vessel beyond the mask (ρ 0.27) | **Fails.** Pre-registered first suspect: the window → A2 ablation now, after an FP census (§2.0, §2.5) |
| Fingerprint window on full data | [−169, 719] HU (training used the fixed [−300, 1300], verified in the plans file) | The default would clip calcium; A2 is the paired test |

The plan below is v4 with these results folded in; the recipe itself does not change.

## 1. Thesis

Train **one** nnU-Net v2 ResEnc model end to end on 4-class labels (LM, LAD, LCx, RCA). The recipe is unchanged from
v2:

- 0.5 mm isotropic, 256³ (128 mm) patch;
- fixed CT window [−300, 1300] HU, no mirroring;
- nnU-Net default loss, sampling and inference overlap (tile step 0.5).

The project lead's decisions ([[Human decisions]]) are binding:

- the **original ImageCAS mask, split into 4 classes**, is target, seed and reference (D0, D4);
- side branches go to their parent's class, the **territory** rule (D1);
- the **ramus intermedius → LCx** (D1b);
- tF1 tolerance **1.5 mm** (D3);
- **every case is read twice** (D2).

The labels therefore all live in one convention, the one the plan's projected proxy already uses. Training can
start before any human label exists: ImageCAS-X names projected onto the ImageCAS mask, territory read-out, ramus →
LCx.

Two reads per case (D2) are used as two samples, not fused into one target (**A11′**, Round 5):

- **Training.** Each read is its own training sample and keeps its own labels, names and extent alike. There is no
  name-conflict `ignore` (the Round 3 voxel rule was measured on the GPU: −0.008 vs both-as-samples against the
  truth, −0.035 against the reads; Crucible's run).
- **Wholesale disagreement.** A case where the reads disagree wholesale goes to a third read and stays out of
  training until then.
- **Ramus-only disagreement.** This is settled by D1b (ramus → LCx), never by a third read.

**Scoring** is the mean tF1 against each read (A10). **Human-level** means non-inferior, per class, to the inter-read
tF1 of the same cases, with a 0.02 margin. The code for all of this exists and is self-tested (`fuse_reads.py`).

Everything after the network is a set of switchable, pre-registered competitors scored on val by one tF1
implementation (A1, A9):

- post-processing P1′ (only if Delta's stricter pre-registered table passes) and P2;
- a single global vessel-probability threshold, chosen on val and frozen (A15; counts as raw output).

Rule renaming R and hybrid decoding H are retired (A7); the namer is QA only. P1 is removed (A2). The FP gate is
computed on the raw prediction and is an acceptance criterion for the final model, not a gate on training (A15).

## 2. Recipe

### 2.0 Order of work

| Step | When | Blocks | Cost |
|---|---|---|---|
| ~~R0 + short R1~~ **done** (round 5) | — | — | 21.8 h |
| **Run 2: FP census + A2 window ablation** (`trillium/atlas`, §2.5) | next GPU job | R1 full length (the window) | one 1-GPU job, ≤ 23:50 |
| CPU prep | now | R1 | Territory proxy for 640 ImageCAS-X train/val cases; A4 QA (Bridge's labeller, ramus → LCx) over all 800; TotalSegmentator aorta on all 1000; tF1 port to `src/segtrain/metrics.py` with the A1 ostium; bridge-audit wrapper; R/H wrappers; **read-fusion script** (§2.1) |
| R1, 1000 epochs, winning window | after run 2 | ablations, post-processing judgement | **48.6 H100-h** (three chained jobs) |
| Labelling (two reads per case) | from now; sealed test first | waves (§2.7) | team |

No human decision blocks R1 any more. D0 was taken on 2026-10-05.

### 2.1 Labels

**Splits** (unchanged):

| Set | Cases | Use |
|---|---|---|
| ImageCAS-X train / val | 560 / 80 | proxy until team reads exist |
| ImageCAS-X test | 160 | 80 sealed; 80 enter training only with team reads |
| quality-0 | 200 | 20 sealed; rest only with team reads |

The sealed test is labelled first.

**Proxy (before team reads).** For each mask voxel, the ImageCAS-X class of the nearest ImageCAS-X voxel within
2 mm; geodesic inheritance inside the mask for the rest. The 14 classes are read out by D1/D1b:

- LM ← LM;
- LAD ← LAD, D1, D2, D-Other;
- LCx ← LCx, OM1, OM2, L-PDA, L-PLA, OM-Other, **IM**;
- RCA ← RCA, R-PDA, R-PLA.

**A4 QA on the proxy, re-run with ramus → LCx on both sides**
([[Atlas - With ramus to LCx the proxy QA ignores 0.3 percent of voxels and excludes 11.6 percent of cases]]):

- **Voxel rule.** Voxels where the proxy and Bridge's frozen namer (`RAMUS = 'LCx'`) disagree become `ignore`. The
  median is **0.29 %** of named voxels per case, and in the median case all of them lie within 10 mm of the carina.
- **Exclusion.** Cases with a wholesale disagreement (ostium > 5 mm, LM Dice < 0.5, or LAD↔LCx swap > 5 %) are
  **excluded until a human reviews them**: 20 of 172 (11.6 %).
- **Ramus-only exemption.** A case whose only flag is a swap that disappears once ImageCAS-X ramus voxels are left
  out is **not excluded** (7 cases). Its disagreeing voxels keep the proxy's (expert) name instead of `ignore`.
- **Namer accuracy under D1b** (A7, Bridge): 88.2 % of 76 held-out cases fully right, swaps 7.9 %.
- **Absent-LM guard (A4, Round 5).** A proxy with no LM is never excluded on the `lm` or `ostium` triggers; it is
  marked for review instead (2 of the 3 R−D swaps were absent-LM cases; 11 of 800 ImageCAS-X cases have no LM).

**Two reads per case (D2): training-label form A11′ (Round 5).** Each read is its own sample with its own labels:
no voxel of a read dataset is `ignore` because the other read named it differently. (`fuse_reads.py` keeps the A11
voxel rule as a switch, `training_samples(A, B, form='a11')`; the default form is now `both`.)

| Voxel state (inside the ImageCAS mask) | Sample from read A | Sample from read B |
|---|---|---|
| Both reads: same class (incl. both background) | that class | that class |
| Both reads: vessel, different classes (e.g. LAD vs LCx at the carina) | **A's class** | **B's class** |
| One read: vessel; the other: background (extent difference) | A's own label | B's own label |
| Outside the mask | background | background |

Each case contributes two training identifiers (`<case>_rA`, `<case>_rB`). nnU-Net samples cases uniformly, so a
double-read case is seen as often as two single-read cases. The epoch is still 250 iterations, so there is no extra
GPU cost.

**Case rule (A11).** A third read adjudicates when any of these holds:

- inter-read macro tF1 < 0.80;
- ostium disagreement > 5 mm;
- carina (LM end) disagreement > 5 mm;
- LAD↔LCx swap > 5 %;
- Bridge's decision extractor flags a different ostium, LM end, LAD/LCx side or tree identity.

The A4 absent-LM guard applies: a read with no LM never triggers on the ostium or carina rule alone; it goes to
review.

Until adjudicated, the case is out of training; it is never voxel-masked. The overruled read is then replaced by the
adjudicator's.

**Ramus-only disagreement** never goes to a third read. It is detected geometrically: the LAD↔LCx swap is the only
trigger, and the swapped voxels are one branch (one component, ≤ 25 % of LAD+LCx) leaving within 10 mm of the carina.
D1b resolves it by setting that branch to LCx in both reads (`apply_d1b`).

**Self-test** on real proxy labels with simulated second reads
([[Atlas - Fusion and acceptance code for two reads, self-tested on simulated second reads]]):

- a 5 mm carina shift → 0.05–1.2 % of voxels `ignore`, no adjudication;
- a distal RCA truncation → 0 `ignore` under A11 (extent kept) vs 5–7 % under agree-or-ignore;
- a whole LAD/LCx swap → adjudication;
- the non-inferiority check passes a model 0.01 above inter-read and fails one 0.05 below.

**A11 test (re-specified, Round 5).** Runs **only if A12a detects annotator habits**. At the first wave with ≥ 150
double-read training cases, A11′ (default) against agree-or-ignore, 250 epochs each, decided by **tF1 against the
reads** (A10) with the carina anchor reported alongside. The challenger replaces A11′ only with a CI excluding 0 in
its favour; otherwise A11′ stays. (The Round 3 A11 voxel rule is retired; the two-arm GPU evidence is simulated,
one seed, so A11′ is a default, not a closed question.)

Why not the alternatives:

- **STAPLE / majority vote.** With two raters, majority vote reduces to agree-or-ignore, and STAPLE cannot estimate
  rater weights ([[Fusing multiple annotations and learning from noisy labels]]).
- **Soft labels.** Need a custom loss. Deferred until the A11 test shows that disagreement information matters.
- **Intersection with disagreements as background.** Never used: it teaches background on real vessel.
- **Name-conflict `ignore` (old A11).** Measured worse against the reads (−0.035, CI excluding 0) and not better
  against the truth (Crucible's GPU run); retired.

**Mixing team reads and proxy.** Team reads replace the proxy case by case: two samples once both reads exist. A case with only one team read so
far uses that read as a single sample with its own labels (A11′; no `ignore` against the proxy).

**Convention keeping (A3, run in the direction D0 implies).**

- Every case is tagged `seed=girder`.
- A per-case monitor on every wave compares each read's union with the ImageCAS mask, flagging a read **drawn
  thin** (union Dice vs the ImageCAS mask < 0.9, or calibre closer to ImageCAS-X than to the mask).
- A wave halts if more than 10 % of reads are flagged.
- Flagged reads are excluded and redone.
- The sealed test is single-convention by construction.

**Wave-1 double-read report (A12, one CPU report on the first 50 double-read cases).** It replaces the four plans'
separate first-20/50 checks and contains:

- inter-read tF1 per class;
- fraction of voxels `ignore` under A11, and their location relative to the carina;
- Bridge's decision-vs-diffuse attribution of naming disagreement (≥ 80 % decision-shaped is pre-registered);
- Delta's components of A∩B against each read;
- Crucible's noise-model refit and re-run of its fusion simulation;
- adjudication rate (against the labelling lead's ceiling);
- thin-read flags (A3);
- proxy vs reads (tF1, swap rate): if < 0.80, proxies are dropped from the next wave.

**Pre-registered expectation (Atlas):** `ignore` ≤ 2 % of mask voxels in the median case, mostly at the carina. If
disagreement turns out diffuse or correlated, the A11 case rule is revisited before any team read enters training.

### 2.2 Preprocessing (unchanged)

- nnU-Net v2.8.1 `3d_fullres`, never `3d_lowres`.
- **0.5 mm iso**: lossless for image and labels
  ([[Atlas - Resampling to 0.5 mm isotropic loses nothing measurable, 0.7-0.8 mm does]],
  [[Atlas - On the thin convention a 0.5 mm round trip cuts no tree]]); the thick ImageCAS convention loses less
  still.
- **Fixed window [−300, 1300] HU.** The default fingerprint window on these labels would be ≈ [−164, 640] HU and
  would saturate calcium
  ([[Atlas - nnU-Net's automatic CT window on lumen labels flattens 38 percent of the heart box]]).
- No crop.

### 2.3 Model

- ResEnc U-Net, `ResEncUNetPlanner -gpu_memory_target 60 -overwrite_target_spacing 0.5 0.5 0.5`. Re-planned on 6
  real preprocessed cases this round: **256³, batch 2, spacing 0.5**, the same as the cohort-wide sweep.
  - 142 M parameters, 69 TFLOP per step;
  - tree fits one patch in 98 % of cases; LM in 97 % of LAD-centred patches.
- `ignore` label = 5, used by the A4 proxy QA only (A11′ read datasets carry none).
- **Fallback, measured** ([[Atlas - The fallback 192 × 256 × 256 patch at 0.5 mm, measured]]): ResEnc XL preset at
  0.5 mm, 192 × 256 × 256.
  - It holds the left tree in 93.5 % and the whole tree in 91.5 % of cases, which confirms v2's figures.
  - But only **85 %** of LAD-centred patches contain the LM (97 % for the master).
  - It is the last resort, after the loader and memory levers in §2.5. **Retired in round 5: R0 fits at 55.6 GiB.**

### 2.4 Loss, sampling, augmentation

- Dice + CE with the `ignore` label (nnU-Net-native).
- Default sampling.
- Defaults with mirroring off.
- Rotation is ablation A3, and a loader-cost lever.
- Skeleton Recall (ablation A4) is **deprioritised** (Round 5): its documented effect is more components, against
  the failing FP gate, and connectivity has ≈ 0.004 headroom. It runs only if run 2's census or R1 shows recall-type
  distal losses.

### 2.5 R0 and the compute model (A6)

**Pre-measured on CPU**
([[Atlas - Without a GPU, nnU-Net's own loader and a saved-tensor count bound R0]]):

- **Activation memory.** A saved-tensor count of the exact 256³ × 2 network on PyTorch's meta device gives
  65.7 GiB fp32 (unique tensors; 98.6 GiB counting every save). Calibrated against the ResEnc L preset (its 0.5 mm
  analogue counts 27.1 GiB fp32 unique; the nnU-Net authors measured 22.7 GB actual), the master should peak near
  **≈ 54 GB** (≈ 50–62 GB). That is under the 75 GB acceptance and the 80 GB card. The fallback should peak near 41 GB.
  If R0 still exceeds 75 GB, the first lever is batch 1 or activation checkpointing, which keeps the 128 mm context,
  before the fallback patch.
- **Loader.** nnU-Net's own data pipeline costs **10.3 CPU-s per batch** on 2 real preprocessed cases at 256³
  (single process, contended VM). With 22 workers that is ≈ 0.47 s per batch, against a GPU step of 0.4–1.2 s. The
  run is therefore near the loader/GPU boundary, which is why R0 times loader wait separately. Preprocessing needs
  ~10 GB per worker, so cap it at 10 workers.

**Compute forecast (v4):** 17.2 EFLOP per 1000 epochs, i.e. 27–85 H100-h, central 45.

**Measured (round 5, replaces the forecast):** 174.9 s / epoch at 12 workers (175.3 at 22), GPU step 0.65 s, loader
wait 0.02 %, peak 42.5 GiB allocated / 55.6 GiB reserved. The memory model (≈ 54 GB) was right; the run is GPU-bound.
**R1 = 48.6 H100-h.** The short R1's EMA pseudo-Dice plateaus from epoch ~150; R1 still runs the full 1000 (nnU-Net's
default; the poly tail is where the last gain sits), but if the 412-epoch model and R1 differ by < 0.01 tF1 on val,
the fine-tunes in §2.7 keep 250 epochs and the final from-scratch model may use 500 (decided on R1 val, recorded
before the final run).

**Run 2: built as `trillium/atlas2/` (`./atlas2`, same contract; A16)**
([[Atlas - Pending Trillium run 2, A1 re-score, FP census and the window ablation]]). It reuses run 1's outputs on
`$SCRATCH/atlas` through the A13 manifest, and refuses to run unless the vendored `segtrain.tf1` has the frozen hash
(A1c).

1. **Phase A** (≈ 1 h before training; no training):
   - TotalSegmentator aortas (`total_fast`, roi aorta; weights downloaded on the login node) for the 80 val and the 36
     clean open test cases;
   - run 1's val re-scored with the A1 ostium (flagged trees apart, A1b), FP gate, **FP census** (A15), a global
     vessel-probability threshold sweep, and ostium validation against ImageCAS-X start points (validation only);
   - the **36 clean open test cases** (A14 `open_icx_test`, cross-checked against both sealed lists) predicted with run
     1's checkpoint, softmax saved, with proxy references and aortas, for Bridge's out-of-sample test.
2. **Phase B** (≈ 20 h): the A2 window ablation. Run 1's recipe with nnU-Net's default window (restored from run 1's
   fingerprint, [−169, 719]); 412 epochs; same split; scored by the same code; paired against run 1.

**Pre-registered decision (accepted, A16).** The window is chosen by paired decisive tF1 (CI excludes 0); on a tie, by
fewer FP components. The census routes the FP lever (A15): mostly `low_confidence` → a single global threshold, chosen
on val and frozen, adopted only if tF1 is not worse (CI) and FP falls; mostly `icx_vessel` → the humans (Round 5 §6);
mostly `confident_other` → the recipe reopens (FP-aware loss or context), open to any advocate with evidence.

**Run 1 (done; kept for the record): R0 + short R1** (`trillium/atlas/`, one 1-GPU 23:50 job;
[[Atlas - Pending Trillium run, R0 benchmark and a short R1 scored by tree-F1]]). It does three things:

1. **Benchmark.** 4 epochs each at `nnUNet_n_proc_DA` = 12 and 22, timing loader wait separately from the CUDA step,
   and recording peak allocated and reserved VRAM.
2. **Short R1.** Trains on the 560 ImageCAS-X training cases (projected proxy, D0/D1/D1b convention) for as many
   epochs as fit (~250–450), with a full poly-LR schedule over that length.
3. **Score.** Predicts the 80 val cases at tile step 0.5 and scores them by tF1, FP gate, swap rate and cut-tree
   count.

R0's figures then replace every forecast in this section, and the val numbers are the first real 4-class evidence
for P1′/R/H.

**A13.** The final validation runs with `--npz`, saving the 80 val softmax volumes, and nnU-Net keeps
`checkpoint_final.pth`. `results/manifest.json` gives every path (checkpoint, plans, softmax, reference labels, env)
and the exact `nnUNetv2_predict` command. Bridge's D/R/H/O and Delta's inference variants can then run as
inference-only jobs against this model instead of two ~20 h trainings. Weights and softmax stay on `$SCRATCH`, and
no sealed case is touched (train = ImageCAS-X train, val = ImageCAS-X val).

**Acceptance:** ≤ 306 s/epoch, peak ≤ 75 GB.

On failure, in order:

1. More workers.
2. GPU spatial transform.
3. Halved spatial-augmentation probabilities (if loader-bound).
4. Batch 1 or activation checkpointing (if over VRAM).
5. Fallback patch.

**Runs** (H100-h forecast):

| Run | H100-h |
|---|---|
| Run 1: R0 + short R1 | 21.8 (spent) |
| Run 2: Phase A + A2 window ablation (412 epochs) | ≤ 23.8 |
| R1, 1000 epochs, winning window | 48.6 (measured) |
| A0 control, 250 epochs | ~12 |
| A1 native spacing (only if A5 triggers) | ~12 |
| A3 no rotation (after R1) | ~12 |
| A4 Skeleton Recall | deprioritised; only on census/R1 evidence |
| **A11 test** (A11′ vs agree-or-ignore), only if A12a finds habits | ~25 |

Ablation rule: paired tF1 CI excludes 0.

**Inference:** tile step 0.5, Gaussian, no TTA; **`--save_probabilities`** on every val and test case (A7).

### 2.6 Post-processing (A2, A7, A8)

**Always on:** threshold; drop components < 100 voxels; never delete ≥ 100 voxels; never force left and right apart.

**FP gate on this raw output.**

**Candidates, each adopted only if it wins on val by tF1 (CI):**

| Step | What | Adoption rule |
|---|---|---|
| ~~P1~~ | ~~3 mm bridging~~ | **Removed** (A2, Round 5) |
| P1′ | Gap-centred re-inference + 3 mm bridging | Only if Delta's stricter pre-registered table passes (mean ≥ +0.002, CI > 0, no case worse by > 0.01, gain in gap cases, FP joins < true joins); else connectivity work becomes a QA report |
| P2 | Label repair | CI |
| T | One global vessel-probability threshold (A15), chosen on val, frozen; part of the raw output | tF1 not worse (CI) **and** FP falls; only if run 2's census says FPs are mostly `low_confidence` |
| ~~R / H~~ | ~~Rule renaming / hybrid decoding~~ | **Retired** (A7): −0.013 each, O − D under 0.01. The namer is QA only (A4, decision extractor, structural audit) |

A component-level deletion filter is **not** raw (it breaches "never delete ≥ 100 voxels") and may only be proposed
with census evidence that it removes no reference vessel (A15).

The **bridge audit** (Delta's) is binding for P1′.

Order: T (if routed) → P1′ (if Delta's table passes) → P2.

### 2.7 How labels arriving over time are used

| Team reads | Action |
|---|---|
| 0 | Run 1 done; **run 2** (`trillium/atlas2`: A1 re-score, FP census, A2 window, open-36 predictions); then R1 at full length with the winning window (A13: checkpoint and val softmax kept); A0/A3 after R1; T/P1′/P2 judged on R1 val |
| first 50 double-read cases | Wave-1 report (A12) |
| sealed test (100 cases × 2 reads) | Both reads kept separately (never fused). Adjudicated where triggered. Frozen. Inter-read ceiling on these 100 |
| every wave | Convention monitor (thin-read flags, 10 % halt); A11′ samples; adjudication queue (A4 absent-LM guard); annotator QA |
| ≥ 150 double-read training cases | Fine-tune 250 epochs on {team samples ∪ proxy}; **A11 test only if A12a found habits** |
| +300 / +600 | Fine-tune 250 epochs; at ≥ 600, paired team-only vs team + proxy |
| all 900 | Final from scratch (1000 epochs, or 500 under the R1 epoch rule), A11′ unless the A11 test replaced it; 5-fold only if it beats single by tF1 |

## 3. Evaluation

**Decisive metric:** macro tF1 @ **1.5 mm** (D3), from `src/segtrain/tf1.py` only (A9), **frozen by hash** (A1c:
sha256 `3c737cbcc0ba24d38f923a52a28d479b34b579d6943f4c55a8cae48f66ad9253`). Every script that decides (run 2, the R1
report, sealed scoring) checks the hash and refuses on a mismatch; a change needs an evidence note, regression tests
and an announcement in the round it is made.

**Ostium of record (A1, revised in Round 5):** the reference centreline voxel nearest the TotalSegmentator aorta,
per tree component and per side (any skeleton degree), within 5 mm. `thick` and `pool_thick` cross-check it; a
disagreement > 5 mm, or a tree not touching the aorta, **flags** the tree.

- **A1a.** A tF1 computed without an aorta mask is reported but decides nothing.
- **A1b.** Flagged trees are reported separately and left out of decisive aggregates until a human has reviewed them;
  paired comparisons may include them (shared ostia). Per class, a class is "flagged" when the tree (component and
  side) holding it carries a flagged ostium. The flag rate under the revised rule is due from Delta before wave 1.
- Validation only: distance of each ostium of record to the ImageCAS-X start point of its side.

**Round-5 finding: `thick` alone is not usable on this reference.** On the short R1's val, the RCA root chosen by the
thickest-endpoint rule is 32–64 mm from the ImageCAS-X start point in 5 of 13 RCAs (ImageCAS RCAs often end bluntly
at mid calibre), and the resulting all-or-nothing zeros flip between two near-identical implementations. No number
scored with `thick` alone (all of round 5, every plan) is decision-grade for absolute tF1; paired differences under
shared ostia remain valid. The aorta masks for the 80 val cases are a CPU prerequisite of the R1 report.

**FP gate (A15):** on the raw prediction, ≤ 1 per case — an **acceptance criterion for the final model**, not a gate
on further training. No model measured meets it yet (master 1.49, released ImageCAS-X model 1.22). Run 2's census
classifies every FP component (pre-registered: `icx_vessel` if ≥ 50 % of its voxels lie within 1 mm of ImageCAS-X
vessel; else `low_confidence` if the 90th percentile of its vessel probability < 0.90; else `confident_other`) and
routes the lever (§2.5). If FPs are mostly real vessel outside the mask, whether they count is the clinical lead's
decision (Round 5 §6), not the tournament's.

**Reference with two reads (A10).** The decisive per-case score is **the mean of the model's tF1 against read A
and against read B**. No fused reference is built. In an adjudicated case, the overruled read is replaced by the
adjudicator's read (`fuse_reads.case_score`).

**The 1000-case inter-rater ceiling (D2).** For every case, inter-rater tF1 is the mean of read 1 scored against
read 2 and read 2 against read 1, per class. It is used four ways:

1. **Acceptance (A10).** Per class, on the sealed test: the lower bound of the paired bootstrap 95 % CI of
   (model mean-against-reads tF1 − inter-read tF1), over the same cases, must be **> −0.02**
   (`fuse_reads.acceptance`). The 0.02 margin is for the clinical lead to confirm once (ruling §6).
2. **Human-normalised score.** For each case, model tF1 ÷ inter-rater tF1, reported by stratum (dominance, disease,
   quality). A model at 1.0 is "as good as a second annotator".
3. **Difficulty stratification.** Results are reported per tertile of inter-rater tF1, so a model failing only
   where humans also disagree is distinguishable from one failing on easy cases.
4. **Annotator QA.** Per annotator, the running mean of their agreement with their co-reader. An annotator whose
   agreement drifts below the cohort's 10th percentile over 20 cases is re-trained. This uses the same numbers and
   needs no extra reads.

**Reported alongside:** per-class clDice, Dice, HD95, β₀, swap rate, LM length, detection, bridge audit; and a
**secondary cross-convention benchmark** against ImageCAS-X on the 80 sealed ImageCAS-X cases. That benchmark carries
the 0.19 tF1 convention cost and is never decisive
([[Crucible - A perfect segmentation in the wrong lumen convention loses 0.19 tree-F1]]).

**Acceptance:**

- per class, non-inferior to inter-read tF1 at margin 0.02 (paired bootstrap lower bound > −0.02);
- FP ≤ 1 per case on the raw prediction;
- swap rate < 5 %.

## 4. Evidence

The v2 evidence table stands. New this round:

| Claim | Evidence |
|---|---|
| R0 175 s/epoch, 55.6 GiB; short R1 tF1 0.846 (provisional), swaps 0.9 %, FP 1.49; 11/17 cut flags are ostium artefacts | [[Atlas - Trillium R0 and short R1 results]] |
| R and H lose to the direct model's names (−0.013 each); oracle headroom +0.010 | Bridge round-5 Trillium results (`trillium-results/round5/bridge/`) |
| Fallback 192 × 256 × 256: 93.5 % / 91.5 % / LM visible 85 % | [[Atlas - The fallback 192 × 256 × 256 patch at 0.5 mm, measured]] |
| A4 with ramus → LCx: 0.29 % ignore, 11.6 % excluded, 7 ramus-only cases exempted | [[Atlas - With ramus to LCx the proxy QA ignores 0.3 percent of voxels and excludes 11.6 percent of cases]] |
| A10/A11 code: forms, adjudication, ramus exemption, scoring, non-inferiority, self-tested | [[Atlas - Fusion and acceptance code for two reads, self-tested on simulated second reads]] |
| Trillium run saves checkpoint and val softmax, with a manifest (A13) | [[Atlas - Pending Trillium run, R0 benchmark and a short R1 scored by tree-F1]] |
| Activation memory ≈ 54 GB predicted; nnU-Net loader 10.3 CPU-s per batch | [[Atlas - Without a GPU, nnU-Net's own loader and a saved-tensor count bound R0]] |
| Two independent splits of the same mask disagree on 0.26 % of voxels, at the carina | [[Atlas - The rule labeller disagrees with the projected proxy on 0.3 percent of voxels, all at the carina]] |
| Majority vote ≈ STAPLE when raters are few; STAPLE needs raters to weight | [[Fusing multiple annotations and learning from noisy labels]] (Karimi et al. 2020) |
| Bridging alone +0.01, half its joins FP | [[Delta - Real bridging on 17 nnU-Net predictions gains little alone, half its 3 mm joins are false positives, and gap-centred re-inference makes it work]] |
| Cross-checked ostium 116/116 | [[Delta - Two cheap ostium rules find 116 of 116 true ostia, and their disagreement flags every miss]] |
| Rule naming within 0.007–0.037 of oracle | [[Bridge - On real stage-1 output, the two-stage namer is within 0.01-0.03 tree-F1 of perfect naming]] |

## 5. Risks and early detection

| Risk | Early signal | Response |
|---|---|---|
| Reads disagree on extent, not just names | Wave-1 report (A12): extent vs name disagreement away from the carina | Revisit the third-read case rule before team reads enter training; brief annotators |
| Annotator habits make A11′ adopt one reader's carina | A12a habit test | Run the re-specified A11 test (A11′ vs agree-or-ignore, against the reads) |
| Wholesale disagreement common | Adjudication rate > 15 % on the first 100 | Re-instruct; third reads budgeted |
| Annotators draw thin despite D0 | Per-read thin flag; wave halt at 10 % | Exclude and redo |
| ~~Over-VRAM / loader-bound~~ | Retired by R0 (55.6 GiB, loader wait 0.02 %) | — |
| Repair hides FPs | Gate on raw output; audit | — |
| Cut rate | **≈ 4/80 real partial cuts (3 LCx)** after the ostium artefacts (Atlas 11/17, Delta 13/17) | P1′ only on Delta's stricter table |
| FP gate fails (1.49/case) | Run 2 census (A15) | Window (A2); global threshold T; else the humans; confident hallucinations reopen the recipe |
| A1-scored tF1 well below 0.87 | Run 2 Phase A | Reopens the recipe (Round 5 §5): FP-aware loss or a different context |
| Many flagged trees (A1b) | Flag rate in run 2 / Delta's count | Reviewer budget is the labelling lead's decision (Round 5 §6) |
| TotalSegmentator fails on the node | `logs/aorta.log` in run 2 | Affected cases are provisional (A1a); aortas can be recomputed on CPU (~40 s/case) and the CPU re-score re-run |
| Metric drift | Hash check (A1c) | Run 2 and every decisive script refuse on a mismatch |

## 6. Comparison

The plan conforms to D0–D5 and integrates A1–A16. No challenger proposes a rival recipe; each competes on additions,
and the master's model, checkpoint and softmax serve them (A13): Bridge's open-36 test and Delta's P1′ both run on
the master's run 1 without extra training. What v6 adds to v5:

- **The judge's A1/A1a–c and A15/A16 implemented in a runnable job** (`trillium/atlas2`), with the metric pinned by
  hash and the census categories fixed before any result.
- **A11′ adopted** (Crucible's measurement over the judge's own Round 3 rule): fewer moving parts, never worse in any
  measured regime.
- **Bridge's out-of-sample data produced** in the same job: the 36 clean open test cases, predicted with the
  master's checkpoint, softmax saved, never a sealed case.

The open decisive facts are run 2's A1 tF1, its FP census and the window decision; then R1 at full length; then the
wave-1 report. Each has a pre-registered rule here.

## 7. Cost

**GPU:** ≈ 230–470 H100-h (+≈ 25 h for the A11 test, only if A12a finds habits). Spent: 21.8 h (run 1). Next: run 2
(≤ 23.8 h; it *is* ablation A2, so A2's line is absorbed; Phase A adds ≈ 1 h of GPU for aortas and the open-36
predictions); then R1 48.6 h (three chained 23:50 jobs). Skeleton Recall (~12 h) is no longer planned.

**CPU (on the node, overlapping training):** run 1's re-score and census ≈ 6 core-min per case × 80, plus B's after
training.

**Human, new:** review of flagged trees before sealed scoring (A1b; rate due from Delta); third reads for
wholesale-disagreement cases (≈ 10 %, ≈ 100 reads over 1000 cases); the per-wave monitor review.

**Engineering:** `trillium/atlas2` (done); `fuse_reads.py` default form switched to `both` (A11′; done, `training_samples`).

## 8. Changes since v5

1. **Round 5 ruling integrated** (§00): A1 ostium of record and A1a–c (frozen hash; flagged trees apart); P1 removed;
   A4 absent-LM guard; R/H retired; **A11′** (no name-conflict `ignore`; A11 test conditional and judged against the
   reads); A15 FP gate as acceptance criterion with census routing; Skeleton Recall deprioritised.
2. **Run 2 built**: `trillium/atlas2/` (`./atlas2`), READY. Phase A: TotalSegmentator aortas, A1 re-score of run 1
   with the frozen metric, FP census, threshold sweep, open-36 predictions + softmax for Bridge. Phase B: A2 window
   ablation, 412 epochs, paired. Tested on CPU (dry runs in both layouts, refusal paths, job body end to end on 2 real
   cases, shellcheck).
3. **Corrections accepted:** c0717 and c0560 are ostium artefacts (≈ 4/80 real cuts, not 6); 0.871 withdrawn as an
   estimate; bounds 0.846–0.895 until the A1 re-score.
4. **Cost:** run 2 absorbs ablation A2; R1 48.6 h follows it.

## 9. Changes since v4 (v5)

1. **R0 measured** (175 s / epoch, 55.6 GiB): forecasts replaced; loader/memory levers and the fallback patch retired;
   R1 = 48.6 H100-h.
2. **A7 settled on the short R1:** R and H lose to the model's own names; both stay QA.
3. **Cut trees re-read:** 11 of 17 flags are provisional-ostium artefacts; ≈ 6/80 real; LAD/LCx "few cuts", RCA
   middle band pending the A1 ostium. `thick`-only scores declared non-decisive for absolute tF1 (§3).
4. **FP gate fails (1.49):** run 2 = FP census + A2 window ablation, with a pre-registered decision (§2.5).
5. **Window verified:** training used [−300, 1300]; the full-data fingerprint window is [−169, 719].
6. **Implementation:** the R1 path is in `src/segtrain` (task 712; [[Atlas - Implementation of the R1 training path]]).

## 10. Changes in v4 (kept for the record)

1. **A10.**
   - Scoring is the mean tF1 against each read; there is no fused reference. This fixes v3 §2.7's "fused … frozen",
     which contradicted §3.
   - Adjudicated cases replace the overruled read.
   - Acceptance is per-class non-inferiority to inter-read tF1 (margin 0.02, paired bootstrap), replacing "−5 points".
2. **A11.**
   - Default training form: each read is a sample, name disagreements `ignore`, extent kept.
   - Case-level third read on Atlas's triggers or Bridge's decision extractor; ramus-only is resolved by D1b.
   - The pre-registered A11 test replaces A5r.
   - Implemented in `experiments/Atlas/fuse_reads.py` and self-tested.
3. **A4 re-run with ramus → LCx:** 0.29 % ignore, 11.6 % excluded, 7 cases exempted as ramus-only; ramus-only
   disagreement voxels keep the proxy's name.
4. **A7:** namer accuracy re-quoted (88.2 %, 7.9 %).
5. **A2:** support rule withdrawn; P1′ judged only against step-0.5 default inference.
6. **A12:** one wave-1 double-read report on 50 cases replaces the first-20 check.
7. **A13:** the Trillium job saves `--npz` softmax and the final checkpoint and writes `results/manifest.json`
   (tested on CPU); it runs first.

## 11. Changes in v3 (kept for the record)

1. **Conforms to the human decisions.**
   - D0/D4: target = split ImageCAS mask; option A removed; monitor flags thin reads.
   - D1/D1b: territory, ramus → LCx; trunk-mode A4 dropped; namer switch = LCx.
   - D3: 1.5 mm fixed.
   - D5: no redo.
2. **Two reads (D2):**
   - fusion rule (agreement / `ignore` / third-read adjudication);
   - A5r (both reads as samples);
   - soft labels deferred;
   - first-20 check redefined on double reads;
   - scoring = mean of tF1 against each read.
3. **1000-case inter-rater ceiling:** per-class acceptance, human-normalised score, difficulty tertiles, annotator QA.
4. **A1–A9 of Round 2 integrated:**
   - ostium cross-check;
   - FP gate on the raw prediction;
   - Delta's audit;
   - P1 demoted, P1′ judged against step 0.5;
   - R with Bridge's rule; `--save_probabilities`, H;
   - ramus switch;
   - A9.
5. **Fallback measured** and demoted behind memory and loader levers.
6. **R0 pre-measurements:** memory model (≈ 54 GB) and nnU-Net loader throughput (10.3 CPU-s per batch).
7. **R0 + short R1 prepared as a Trillium run** (`trillium/atlas/`): tested on CPU in both case layouts; tF1 scorer
   identical to Delta's on 6 pairs; results feed P1/P1′/R and replace the GPU-hour forecasts.
