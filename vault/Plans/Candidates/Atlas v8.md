---
tags: [plans, candidate, master, nnunet, multiclass]
author: Atlas
round: 6
version: 8
updated: 2026-10-10
---

# Atlas v8 — the master recipe with the fine-tuning recipe made runnable: the A17a fine-tune trainer shipped, the citation corrected, A17 conformed

## 0000. Round 6 ruling (A17–A20): what v8 changes

| Ruling | v8 |
|---|---|
| **A17a** a fine-tune trainer that loads the heads and warms up | **Shipped:** `src/segtrain/nnunet_ext/nnUNetTrainer_segtrain_finetune.py` (§2.7.3) with CPU tests (`tests/test_finetune.py`, 14 tests) |
| **A17b** the citation was misread | Corrected in §2.7.1 point 4: Wald et al. found **1e-3 better than 1e-2** for fine-tuning (71.76 vs 71.02) with a **50-epoch** warm-up. v8 keeps peak 1e-2 as the primary arm on its own argument, states the 10-epoch warm-up as a deviation, and pre-registers the **1e-3 fallback arm** (Foxtrot F2) |
| **A17c** a failed admission test has consequences | §2.7.4: if W1 fails in any class, the proxy-drop test moves to W3 and warm-vs-scratch to W4 |
| **A17d** the final model never trains on proxies | §2.7.4: the proxy question governs interim models only |
| **A17e** the decision set is 160 | Unchanged (it was v7's) |
| **A18–A20** (acceptance suspended pending the humans; multiplicity; the F3 ROI rule) | Binding as written in [[Round 6]]; nothing in Atlas's fine-tuning recipe conflicts. F3 is a post-processing candidate under A15 once its preconditions are met |

## 000. Round 6 (Q1): the fine-tuning recipe in one table

Full recipe in §2.7. Evidence: [[Atlas - One wave can only be judged to about 0.01 tree-F1, so the fine-tuning recipe makes few per-wave decisions]]
(CPU, from the round-5 GPU results), the literature cited in §2.7, and run 1's measured 175 s/epoch.

| Question | v7's answer |
|---|---|
| When do team labels replace the proxy? | Case by case, the moment both reads of a case exist (two samples, A11′); the proxy of that case is dropped. Unread ImageCAS-X cases keep their proxy |
| Which cases are read first? | Sealed 100 → val 80 → open ImageCAS-X test 80 (the **160-case decision set**) → training cases: A4-excluded and absent-LM proxies first, then quality-0 (no proxy) interleaved with the remaining ImageCAS-X train in a fixed hash order |
| Warm start or scratch? | Fine-tunes warm-start from the last accepted model **if** the one pre-registered test at the first fine-tune (warm 250 epochs vs scratch 500, on the decision set, margin 0.01) says it is non-inferior. **The final model is always trained from scratch** |
| Epochs and LR per wave | 250 epochs (12.2 H100-h), nnU-Net's SGD defaults, peak LR 1e-2 reached by a **2,500-iteration (10-epoch) linear warm-up**, then poly decay, stepped per iteration; the full network, output heads included, loaded by the A17a trainer; 1e-3 is the pre-registered fallback arm; plans, window and normalisation frozen at R1 |
| Proxy/team mixing | All current data every wave (team pairs + unread proxies), no per-sample weights: a read case contributes two samples, a proxy case one |
| When are proxies dropped entirely? | (a) wave-1 proxy-vs-read tF1 < 0.80 (A12, unchanged); (b) at 300 team-read training cases, if team-only is non-inferior to team + proxy (margin 0.01); (c) in any case once every ImageCAS-X training case is read |
| What is re-validated each wave? | One comparative decision at most (above); every wave: non-regression vs the previous model on the decision set, swap rate, FP components, flag rate, proxy-vs-read drift, A3/A11/A12 monitors. Nothing else is re-tuned |
| Cost | ≈ 170 H100-h from R1 to the final model (+24 h if the A11 test triggers) |

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

**Wave-1 double-read report (A12, one CPU report on the first 50 *non-sealed* double-read cases, i.e. the val wave W1, §2.7.2).** It replaces the four plans'
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

### 2.7 Fine-tuning as team reads arrive (Round 6, Q1)

#### 2.7.1 What the recipe rests on

1. **Reads and proxies share extent; they differ in names.** Under D4 the annotators split the ImageCAS mask, the
   same mask the proxy splits. A read and the proxy can therefore differ only in names (carina position, side-branch
   assignment, ramus, LM end), unless a read is drawn thin, which A3 flags. Two independent automatic splits of the
   same mask disagree on 0.26 % of voxels, all at the carina
   ([[Atlas - The rule labeller disagrees with the projected proxy on 0.3 percent of voxels, all at the carina]]).
   The proxy is therefore *plausibly* read-grade. v7 **tests** that before relying on it (§2.7.4) instead of
   assuming it.
2. **The second read is worth training on.** In Crucible's GPU run, both reads as samples beat a single read by
   +0.030 [+0.010, +0.050] against the truth, and the oracle labels did not beat two noisy reads. Hence A11′, and
   hence each read case enters as two samples.
3. **Warm starts can generalise worse than fresh training on the same data.** Ash & Adams (*On Warm-Starting Neural
   Network Training*, NeurIPS 2020) report this gap at similar final training loss, and shrink-and-perturb closes
   much of it. Iterative-labelling projects train their final model independently of the intermediate ones:
   TotalSegmentator (Wasserthal et al., Radiol AI 2023) retrained after 5 → 20 → 100 → 1204 corrected cases. v7
   follows both: the waves may warm-start, the final model never does.
4. **nnU-Net fine-tuning needs a learning-rate warm-up.** Wald et al. (*Revisiting MAE pre-training for 3D medical
   image segmentation*, CVPR 2025) is the source, and it says more than v7 reported.
   - Without warm-up, fine-tuning "significantly reduces performance"; warm-up adds 0.6–1 DSC.
   - It found a **1e-3 peak better than 1e-2** for fine-tuning (71.76 vs 71.02).
   - Its warm-up was **50 epochs** (12.5k iterations).
   - v7 misread the paper as fine-tuning at nnU-Net's 1e-2 (corrected per Round 6, A17b).

   **v8 keeps 1e-2 as the primary arm**, on an argument of its own, not on this paper:
   - With every data source present there is nothing to forget.
   - The purpose of a warm fine-tune is to move the model *away* from the proxy's naming convention, which a low LR
     would preserve.
   - Crucible's simulation (team reads beat the proxy as a teacher by +0.013 to +0.028 on the A10 score) points the
     same way.
   - The paper's setting (self-supervised pre-training, a new task, brain MRI) is not ours.

   **The 10-epoch (2,500-iteration) warm-up is a stated deviation** from the paper's 50 epochs. It is chosen because
   our source and target tasks are identical (same classes, same images, same plans), so the optimiser starts near a
   solution rather than from a representation of a different task. **The 1e-3 arm is pre-registered** as the fallback
   (Foxtrot F2; §2.7.4).
5. **No forgetting by construction.** Every wave trains on all current data: team pairs plus unread proxies. The
   forgetting that Lifelong nnU-Net (González et al., Sci Rep 2023) measures when fine-tuning on new data only
   cannot arise.
6. **Label quality matters most in-distribution.** Jaus et al. (*Good Enough: Is it Worth Improving your Label
   Quality?*, 2025) find that in-domain CT segmentation gains from better labels down to a small quality threshold,
   while pre-training is insensitive to label quality. That is the case for replacing proxies with reads case by
   case, rather than only pre-training on proxies.
7. **A wave can be judged to about 0.01 only on a large fixed set** (CPU note above).
   - Paired retraining noise is SD 0.031 at the floor and 0.069 for a label-form change.
   - On 80 cases the detectable difference is 0.010–0.022.
   - On 160 cases it is 0.007–0.015; a 0.01 non-inferiority margin then holds for SD ≤ 0.05.
   - Hence one decision set of 160 team-read cases, and at most one comparative decision per wave.
8. **Cost is per epoch, not per case.** An nnU-Net epoch is 250 iterations × batch 2 whatever the dataset size. At
   run 1's 175 s, 250 epochs take 12.2 H100-h, 500 take 24.3 and 1000 take 48.6.

#### 2.7.2 Labelling order and waves

| Wave | Cases read (2 reads each) | Cumulative training cases with reads | Triggers |
|---|---|---|---|
| W0 | Sealed test 100 | 0 | Frozen; scored only at milestones. Nothing is computed from these reads before then, including A12 |
| W1 | ImageCAS-X val 80 | 0 | Decision set, part 1. R1 re-scored against the reads (A10, A1). **A12 wave-1 report on these** (the first 50 *non-sealed* double reads; A12 must not inspect sealed reads). Proxy-as-third-reader test (§2.7.4) |
| W2 | Open ImageCAS-X test 80 (A14) | 0 | Decision set complete (160). Read after Bridge's open-36 test, which runs against the proxy. The 44 development cases among them were inspected for other components, not for fine-tuning, so the bias the [[Sealed test]] note warns of does not apply to these decisions |
| W3 | 150 training cases | 150 | **FT1**: warm vs scratch (the one comparative decision of the wave) |
| W4 | +150 | 300 | **FT2**; team-only vs team + proxy (proxy-drop test) |
| W5 | +300 | 600 | FT3 |
| W6 | the rest | 740 (560 ImageCAS-X train + 180 quality-0) | **Final from scratch**; T re-confirmed once; sealed milestone |

**Order of training cases within W3–W6** (fixed in advance; no adaptive selection, so the decision set and the order
stay unbiased):

1. The A4-excluded proxies (wholesale namer disagreement, ≈ 11.6 % of ImageCAS-X cases): they are out of training
   until read.
2. Absent-LM cases (A4 guard).
3. The 180 non-sealed quality-0 cases, which have no proxy at all, interleaved 1 : 3 with the remaining ImageCAS-X
   train cases.
4. Ties broken by `sha256('asclepius-waves:' + case)`.

#### 2.7.3 What each wave trains

**Data.**
- A read case contributes two samples (A11′), and its proxy is dropped.
- An unread ImageCAS-X case contributes its proxy (A4 `ignore` as now).
- A4-excluded proxies and unread quality-0 cases contribute nothing.
- nnU-Net samples identifiers uniformly, so read cases weigh 2 : 1 against proxies without any custom weighting.

**Frozen across waves.** Fixing these is what makes warm starts and paired comparisons valid. Only the dataset
changes.
- R1's plans file: spacing 0.5 mm, 256³ patch, batch 2, architecture.
- The CT window.
- The normalisation constants. If run 2's default window wins, its fingerprint values are frozen and never
  re-extracted.
- The trainer: mirroring off.
- Inference: tile step 0.5, no TTA, threshold T.
- Each wave preprocesses only its new cases and links the rest.

**Initialisation and schedule.**
- **Warm** = trainer `nnUNetTrainer_segtrain_finetune`, with `SEGTRAIN_FINETUNE_FROM` = the last accepted model's
  `checkpoint_final.pth`. Never use stock `-pretrained_weights`: nnU-Net 2.8.1 skips every `.seg_layers.` key, which
  re-initialises all deep-supervision heads (Foxtrot F1, A17a).
  - **The load.** The A17a trainer loads the whole state dict, heads included. It refuses unless plans, CT
    normalisation, output classes (`ignore` aside) and keys are identical, then verifies every tensor bitwise and
    logs the source's sha256 and epoch.
  - **The schedule.** 250 epochs; SGD Nesterov, momentum 0.99, weight decay 3e-5 (nnU-Net defaults). LR linear from
    1e-2/2500 to 1e-2 over the first **2,500 iterations** (`SEGTRAIN_WARMUP_ITERS`), then poly (exponent 0.9) to 0,
    stepped every iteration.
  - **Inherited invariants.** It inherits every invariant of the master trainer: fixed-window check, no mirroring,
    val softmax saved, and the A14 refusal of sealed or unmappable training/validation identifiers under every
    name.
  - **The fallback arm.** `nnUNetTrainer_segtrain_finetune_lr1e3` is the same at peak 1e-3. It is a separate class, so
    the two arms' result folders never collide.
  - **Tests** (CPU, `tests/test_finetune.py`):
    - on a tiny network: the heads are bitwise identical after the load, while nnU-Net's own loader leaves them
      random;
    - incompatible sources (classes, spacing, window, architecture) are refused;
    - the LR is 1e-2/2500 at iteration 0, 0.5e-2 mid-ramp, 1e-2 at the end of the ramp, and then decays poly;
    - the real trainer classes load a coronary-trainer checkpoint completely.
  - Peak 1e-2 rather than 1e-3: with all data present there is nothing to forget, and a low LR would preserve the
    proxy's naming habits. Avoiding that gap is the purpose of a warm start's fine-tune (point 3).
- **Scratch:** the R1 recipe, 500 epochs, or 1000 if the R1 epoch rule (Round 5, A16) says R1 and the 412-epoch
  model differ by ≥ 0.01.

#### 2.7.4 The decisions, all pre-registered

All decisions use the decision set (160 cases; 80 at W1): decisive tF1 against the reads (A10), A1 ostium, frozen
metric, flagged trees apart (A1b), paired bootstrap 95 % CI.

| When | Decision | Rule |
|---|---|---|
| W1 | **Is the proxy read-grade?** (the admission test) Per class, tF1(proxy vs reads, mean over A and B) − inter-read tF1 | Non-inferior (CI lower bound > −0.02) for every class → order below unchanged. **Any class failing → the proxy-drop test moves to W3** (replacing warm vs scratch as W3's one decision), and warm vs scratch moves to W4 (A17c). Proxy-vs-read macro tF1 < 0.80 stays only as a backstop (A12) |
| W3 (W4 if W1 failed) | **Warm or scratch for the waves?** FT1-warm (A17a trainer, peak 1e-2, 250 epochs) vs FT1-scratch (500), same data | Warm adopted for the later waves if non-inferior (CI lower bound of warm − scratch > −0.01). **If it fails, one warm arm at peak 1e-3 runs** on the same data (`_lr1e3`, 12.2 H100-h, Foxtrot F2, A17b), with the same rule, before warm starts are retired. If both fail, later waves train from scratch at 500 epochs |
| W4 (W3 if W1 failed) | **Drop proxies?** FT on team + proxy vs FT on team only (300 read cases; 150 if moved to W3), same initialisation | Proxies dropped from the next wave on if team-only is non-inferior (margin 0.01). Otherwise kept until W6, when no unread ImageCAS-X case remains. **Scope (A17d):** this governs interim models only, because the final model never trains on proxies (every ImageCAS-X training case is read by W6). That is also why a shared warm initialisation of both arms is acceptable |
| every wave | **Non-regression** of the new model vs the previous accepted one | Accepted unless the CI lower bound < −0.01. A rejected wave keeps the previous model, and its data is checked (A3 thin reads, adjudication backlog) before the next wave |
| W6 | **Ship** | Final-from-scratch vs the last fine-tune on the decision set: the better by CI ships; on a tie, the from-scratch model. Then the sealed milestone (A10 acceptance, A15 FP gate) |

**Re-validated every wave, no decisions attached** (reported, compared with the previous wave):
- per-class decisive tF1;
- swap rate (< 5 %);
- FP components per case (acceptance ≤ 1 only at the final, A15);
- flagged-tree rate (A1b);
- proxy-vs-read agreement on the newly read training cases (drift of the third-reader result);
- A3 thin-read monitor, adjudication rate, annotator QA, and the A12a habit test on all reads so far (which can
  trigger the A11 test).

**Not re-tuned per wave** (multiplicity; point 7): window, plans, threshold T (re-confirmed once at W6), P1′ and P2
(decided once on R1, re-checked at W6).

**A11 test** (Round 5, conditional): if A12a finds habits, it runs at W3 as a third FT1 arm (A11′ vs
agree-or-ignore, warm, 250 epochs), judged against the reads.

#### 2.7.5 Cost

| Step | H100-h |
|---|---|
| R1 (1000 epochs, winning window) | 48.6 |
| W3: FT1-warm 250 + FT1-scratch 500 | 12.2 + 24.3 |
| W4: FT2 team + proxy, FT2 team-only | 12.2 + 12.2 |
| W5: FT3 | 12.2 |
| W6: final from scratch (1000, or 500 by the epoch rule) | 48.6 (24.3) |
| **Total, R1 → final** | **≈ 170** (≈ 146) |
| A11 test, only if triggered | + 12.2 |

Every fine-tune fits one 23:50 job. R1 and a 1000-epoch final are three chained jobs each. If FT1 rejects warm
starts, W4 and W5 cost +12.2 h each.

#### 2.7.6 Expectations, stated before any read exists (Atlas)

These are expectations only; the rules above decide.
- The proxy passes the third-reader test for LAD, LCx and RCA. The LM is the class most likely to fail: carina
  convention, and the LM end is where the reads themselves disagree most.
- Warm 250 is non-inferior to scratch 500.
- Team-only at 300 cases is *not* yet non-inferior to team + proxy (the proxies add ~350 cases of correct extent),
  so proxies stay until W6.

**Considered and not adopted.**
- **Naming the 180 quality-0 masks with R1's predictions** as extra proxies (model names transferred onto the mask,
  as the ImageCAS-X projection does). R1 names at 0.991 centreline accuracy, so these proxies would be good. But
  they are self-training on the model's own errors, and the cases are read by W6 anyway. It becomes a candidate
  only if W1 shows the ImageCAS-X proxies are read-grade *and* reading lags far behind training.
- **Per-sample loss weights for proxies:** not in nnU-Net, and the 2 : 1 sample count already weights reads.
- **Shrink-and-perturb warm starts:** not adopted by default. It is the first remedy if FT1 rejects plain warm starts
  (one extra 12.2 h arm at W4).

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

**Team-read phase (v7 §2.7.5):** ≈ 170 H100-h from R1 to the final model (≈ 146 with a 500-epoch final), +12 h
if the A11 test triggers; every fine-tune is one 23:50 job.

**CPU (on the node, overlapping training):** run 1's re-score and census ≈ 6 core-min per case × 80, plus B's after
training.

**Human, new:** review of flagged trees before sealed scoring (A1b; rate due from Delta); third reads for
wholesale-disagreement cases (≈ 10 %, ≈ 100 reads over 1000 cases); the per-wave monitor review.

**Engineering:** `trillium/atlas2` (done); `fuse_reads.py` default form switched to `both` (A11′; done, `training_samples`).

## 8. Changes since v7

1. **A17a shipped:** `nnUNetTrainer_segtrain_finetune`, plus the `_lr1e3` fallback arm and a `_5epochs` smoke
   variant.
   - It loads the full checkpoint, heads included, with exact-compatibility checks and bitwise verification.
   - It warms up per iteration, then decays poly, and logs both.
   - It inherits the master trainer's invariants. The master trainer now also refuses sealed or unmappable
     identifiers at `on_train_start` (`sealed_guard`).
   - 14 CPU tests.
2. **A17b:** the Wald et al. citation is corrected (1e-3 better; 50-epoch warm-up). Peak 1e-2 is kept as the
   primary arm, with the reason given. The 10-epoch warm-up is stated as a deviation. The 1e-3 fallback arm is
   pre-registered.
3. **A17c/d:** a failed W1 admission test moves the proxy-drop test to W3; the proxy question is interim-only.

## 8a. Changes since v6 (v7)

1. **§2.7 rewritten as a concrete fine-tuning recipe** (Round 6, Q1):
   - labelling order: sealed → val → open test → training, in a fixed priority order;
   - a 160-case decision set;
   - one pre-registered comparative decision per wave (W1 proxy-as-third-reader, W3 warm vs scratch, W4 proxy drop);
   - non-regression every wave; a frozen plans/window/normalisation;
   - 250-epoch warm fine-tunes with a 10-epoch LR warm-up; the final model always from scratch;
   - cost ≈ 170 H100-h.
2. **A12 moved off the sealed reads:** the wave-1 report uses the first 50 non-sealed double reads (val), since the
   sealed reads may not be inspected before the milestone.
3. **New CPU evidence:** paired retraining noise 0.031–0.069, so a wave is judged to about 0.01 only on ≥ 160 cases
   ([[Atlas - One wave can only be judged to about 0.01 tree-F1, so the fine-tuning recipe makes few per-wave decisions]]).

## 8b. Changes since v5 (v6)

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
