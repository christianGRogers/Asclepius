---
tags: [plans, candidate, master, nnunet, multiclass]
author: Atlas
round: 4
version: 4
updated: 2026-10-08
---

# Atlas v4 — one direct 4-class nnU-Net on the split ImageCAS mask; two reads as two samples; human-level means non-inferior to a second read

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

Two reads per case (D2) are used as two samples, not fused into one target (A11):

- **Training.** Each read is its own training sample. Voxels that both reads call vessel but name differently are
  `ignore` in both samples. Where the reads differ in extent, each sample keeps its own read.
- **Wholesale disagreement.** A case where the reads disagree wholesale goes to a third read and stays out of
  training until then.
- **Ramus-only disagreement.** This is settled by D1b (ramus → LCx), never by a third read.

**Scoring** is the mean tF1 against each read (A10). **Human-level** means non-inferior, per class, to the inter-read
tF1 of the same cases, with a 0.02 margin. The code for all of this exists and is self-tested (`fuse_reads.py`).

Everything after the network is a set of switchable, pre-registered competitors scored on val by one tF1
implementation (A1, A9):

- post-processing P1, P1′, P2;
- rule renaming R and hybrid decoding H.

The FP gate is computed on the raw prediction.

## 2. Recipe

### 2.0 Order of work

| Step | When | Blocks | Cost |
|---|---|---|---|
| **R0 + short R1** (the prepared Trillium run, `trillium/atlas`) | first GPU job | every other GPU job | one 1-GPU job, ≤ 24 h (§2.5) |
| CPU prep | now | R1 | Territory proxy for 640 ImageCAS-X train/val cases; A4 QA (Bridge's labeller, ramus → LCx) over all 800; TotalSegmentator aorta on all 1000; tF1 port to `src/segtrain/metrics.py` with the A1 ostium; bridge-audit wrapper; R/H wrappers; **read-fusion script** (§2.1) |
| R1 | after R0 | ablations, post-processing judgement | ~45 H100-h |
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

**Two reads per case (D2): training-label form (A11), implemented in `experiments/Atlas/fuse_reads.py`.**

| Voxel state (inside the ImageCAS mask) | Sample from read A | Sample from read B |
|---|---|---|
| Both reads: same class (incl. both background) | that class | that class |
| Both reads: vessel, different classes (e.g. LAD vs LCx at the carina) | `ignore` | `ignore` |
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

**Pre-registered A11 test** (replaces v3's A5r). At the first wave with ≥ 150 double-read training cases, compare
these forms for 250 epochs each, paired by tF1 against reads on val:

- the A11 form (default);
- agree-or-ignore;
- pure both-as-samples, if budget allows.

The winner by CI is adopted. If none wins, the A11 form stays.

Why not the alternatives:

- **STAPLE / majority vote.** With two raters, majority vote reduces to agree-or-ignore, and STAPLE cannot estimate
  rater weights ([[Fusing multiple annotations and learning from noisy labels]]).
- **Soft labels.** Need a custom loss. Deferred until the A11 test shows that disagreement information matters.
- **Intersection with disagreements as background.** Never used (A11): it teaches background on real vessel.

**Mixing team reads and proxy.** Team reads replace the proxy case by case: two samples once both reads exist. A case with only one team read so
far uses that read as a single sample, with name disagreements against the proxy set to `ignore`.

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
- `ignore` label = 5, used by A4 and the fusion rule.
- **Fallback, measured** ([[Atlas - The fallback 192 × 256 × 256 patch at 0.5 mm, measured]]): ResEnc XL preset at
  0.5 mm, 192 × 256 × 256.
  - It holds the left tree in 93.5 % and the whole tree in 91.5 % of cases, which confirms v2's figures.
  - But only **85 %** of LAD-centred patches contain the LM (97 % for the master).
  - It is the last resort, after the loader and memory levers in §2.5.

### 2.4 Loss, sampling, augmentation

- Dice + CE with the `ignore` label (nnU-Net-native).
- Default sampling.
- Defaults with mirroring off.
- Rotation is ablation A3, and a loader-cost lever.
- Skeleton Recall is ablation A4, judged after post-processing.

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

**Compute forecast (unchanged):** 17.2 EFLOP per 1000 epochs, i.e. **27–85 H100-h**, central 45.

**R0 is prepared as the project's Trillium run, and it runs first (A13)** (`trillium/atlas/`, one 1-GPU 23:50 job;
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
| R0 + short R1 (prepared Trillium run) | ≤ 24 |
| R1, 1000 epochs | ~45 |
| A0 control, 250 epochs | ~11 |
| A1 native spacing (only if A5 triggers) | ~11 |
| A2 default window | ~11 |
| A3 no rotation | ~11 |
| A4 Skeleton Recall | ~12 |
| **A11 test** (A11 form vs agree-or-ignore, + pure both-as-samples if budget), first wave with ≥ 150 double-read cases | ~22–33 |

Ablation rule: paired tF1 CI excludes 0.

**Inference:** tile step 0.5, Gaussian, no TTA; **`--save_probabilities`** on every val and test case (A7).

### 2.6 Post-processing (A2, A7, A8)

**Always on:** threshold; drop components < 100 voxels; never delete ≥ 100 voxels; never force left and right apart.

**FP gate on this raw output.**

**Candidates, each adopted only if it wins on val by tF1 (CI):**

| Step | What | Adoption rule |
|---|---|---|
| P1 | 3 mm bridging | CI + clean bridge audit; not expected to pass (+0.010, half its joins FP) |
| P1′ | Gap-centred re-inference + 3 mm bridging (support rule withdrawn) | Judged only against nnU-Net's default inference at tile step 0.5; unproven on the master (n = 4, small-patch model) |
| P2 | Label repair | CI |
| R | Bridge's rule renaming, ramus = LCx (88.2 % of held-out cases fully right, 7.9 % swaps under D1b) | CI excludes 0 **and** swap rate no higher (A7) |
| H | Hybrid decoding from saved softmax | Same as R; no prior weight |

The **bridge audit** (Delta's) is binding: bridges made, unsupported orphans, cross-tree joins, FP before/after.

Order: P1/P1′ → P2 → R/H.

### 2.7 How labels arriving over time are used

| Team reads | Action |
|---|---|
| 0 | Trillium R0 + short R1 first (A13), saving checkpoint and val softmax for inference-only reuse; CPU prep; R1 + A0–A4; P1′/P2/R/H judged on R1 val |
| first 50 double-read cases | Wave-1 report (A12) |
| sealed test (100 cases × 2 reads) | Both reads kept separately (never fused). Adjudicated where triggered. Frozen. Inter-read ceiling on these 100 |
| every wave | Convention monitor (thin-read flags, 10 % halt); A11 samples; adjudication queue; annotator QA |
| ≥ 150 double-read training cases | Fine-tune 250 epochs on {team samples ∪ proxy}; **pre-registered A11 test** |
| +300 / +600 | Fine-tune 250 epochs; at ≥ 600, paired team-only vs team + proxy |
| all 900 | Final from scratch, 1000 epochs, on the label form that won the A11 test; 5-fold only if it beats single by tF1 |

## 3. Evaluation

**Decisive metric:** macro tF1 @ **1.5 mm** (D3), from the ported `src/segtrain` implementation only (A9).

**Ostium (A1):** TotalSegmentator aorta contact ≤ 5 mm, cross-checked with `thick` / `pool_thick`. A disagreement
> 5 mm is flagged to a human. The check is validated on 30 val cases against ImageCAS-X `start_points`.

**FP gate:** on the raw prediction, ≤ 1 per case.

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
| Reads disagree on extent, not just names | Wave-1 report (A12): extent vs name disagreement, `ignore` > 2 % median away from the carina | Revisit the A11 case rule before team reads enter training; brief annotators |
| Wholesale disagreement common | Adjudication rate > 15 % on the first 100 | Re-instruct; third reads budgeted |
| Annotators draw thin despite D0 | Per-read thin flag; wave halt at 10 % | Exclude and redo |
| Over-VRAM at 256³ | Memory model (≈ 54 GB) vs R0 | Batch 1 or checkpointing before fallback |
| Loader-bound | Loader note vs R0 | Workers → GPU spatial transform → lower augmentation probabilities |
| Repair hides FPs | Gate on raw output; audit | — |
| Cut rate unknown (all vault predictions share one small-patch model) | R1 val | P1′ / R judged then |

## 6. Comparison

The plan conforms to D0–D5 and integrates A1–A13. What v4 adds:

- **Crucible's acceptance rule (A10)**, adopted and implemented.
- **The judge's A11 synthesis** as the default training form, adopted and implemented. Atlas v3's agree-or-ignore
  is kept only as the pre-registered competitor.
- **The A4 re-run under D1b**, with the ramus-only exemption measured: 7 cases kept.
- **A Trillium run that serves all four plans.** Bridge's naming comparison (D/R/H/O) and Delta's P1′ can be scored
  on the master's own model and val softmax without two extra trainings (A13).

The open decisive facts are R1 val (swap rate, cut rate, R vs H vs D, P1′) and the wave-1 report. Both have
pre-registered rules in this plan.

## 7. Cost

**GPU:** ≈ 220–470 H100-h (+22–33 h for the A11 test); the first ≤ 24 h is the Trillium R0 + short R1 run, whose checkpoint and softmax also serve Bridge's and Delta's inference-only variants (A13).

**Human, new:** third reads for wholesale-disagreement cases. Expected ≈ 10 %, from the 10.5 % wholesale rate between
the two automatic namers, ≈ 100 extra reads over 1000 cases. Also the per-wave monitor review.

**Engineering:** `fuse_reads.py` (0.5 day).

## 8. Changes since v3

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

## 9. Changes in v3 (kept for the record)

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
