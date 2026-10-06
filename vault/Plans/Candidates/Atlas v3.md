---
tags: [plans, candidate, master, nnunet, multiclass]
author: Atlas
round: 3
version: 3
updated: 2026-10-05
---

# Atlas v3 — one direct 4-class nnU-Net on the split ImageCAS mask, trained on two reads, judged by tree-F1

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

Two reads per case change two things. First, **the training target becomes the agreement of the two reads; where
they disagree, nnU-Net's `ignore` label**. Two raters give no majority to vote with, and on an independent pair of
namers splitting the same mask the disagreement is a thin shell at the carina. Cases where the reads disagree
wholesale go to a third reader instead of being masked. Second, **the inter-rater tF1 is known for every case**. It
gives a 1000-case per-class ceiling, an acceptance rule per class, and a per-case difficulty score for stratifying
results and catching annotator drift.

Everything after the network is a set of switchable, pre-registered competitors scored on val by one tF1
implementation (A1, A9):

- post-processing P1, P1′, P2;
- rule renaming R and hybrid decoding H.

The FP gate is computed on the raw prediction.

## 2. Recipe

### 2.0 Order of work

| Step | When | Blocks | Cost |
|---|---|---|---|
| **R0** (1-GPU `debugjob`, ≤ 120 min) | first GPU job | every other GPU job | 2 H100-h (§2.5) |
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

**A4 QA on the proxy, measured form**
([[Atlas - The rule labeller disagrees with the projected proxy on 0.3 percent of voxels, all at the carina]]):

- voxels where proxy ≠ Bridge's frozen labeller (ramus switch = LCx) → `ignore`: median 0.26 %, all within 10 mm of
  the carina;
- cases with a wholesale disagreement (ostium > 5 mm, LM Dice < 0.5, LAD↔LCx swap > 5 %; 10.5 %) are **excluded
  until a human reviews them**.

That measurement used Bridge's territory counts, which match D1, so no trunk-mode re-measurement is needed. One item
is pending: Bridge's labeller must be re-run with the ramus switch at LCx before R1. It changes IM voxels only.

**Two reads per case (D2): the fusion rule.** For every case with two team reads, `fuse_reads.py` produces one
training label:

| Voxel state (inside the ImageCAS mask) | Training label |
|---|---|
| Both reads give the same class (incl. both background) | that class |
| Reads give different named classes (e.g. LAD vs LCx at the carina) | `ignore` |
| One read names it, the other leaves it unlabelled (a branch one annotator dropped) | `ignore` |
| Outside the mask | background (no read can label there: edits are confined to the mask) |

**Case rule.** If the two reads disagree wholesale, the case goes to a **third read (adjudication)** and stays out of
training until resolved. "Wholesale" is tested between the two reads, scoring one against the other (A9
implementation, both directions):

- inter-rater macro tF1 < 0.80, or
- an ostium or LM disagreement > 5 mm, or
- an LAD↔LCx swap > 5 %.

After adjudication, the target is the majority of three reads per voxel, with residual three-way ties → `ignore`.

Why this rule and not the alternatives:

- **STAPLE / majority vote with two raters.** Majority vote has no majority wherever two raters differ, so it
  reduces to this table. STAPLE's per-rater weights need more than two raters per case, or many shared cases, to
  estimate. Where it was compared head to head (Karimi et al., MedIA 2020, Gleason, six raters), STAPLE did not beat
  majority vote ([[Fusing multiple annotations and learning from noisy labels]]).
- **Both reads as separate samples.** This trains the network on contradictory targets at exactly the disagreement
  voxels. Its expected effect is calibrated, not sharper, boundaries. It is cheap to test (two identifiers per case;
  same 250 iterations per epoch, so no extra GPU), and enters as **ablation A5r**.
- **Soft labels** (mean of the two one-hots). nnU-Net's Dice+CE takes hard labels, so this needs a custom loss.
  Deferred until A5r shows that keeping disagreement information helps at all.
- **Cost of `ignore`.** On an independent pair of namers splitting the same mask (projected proxy vs rules), the
  disagreement is 0.26 % of voxels per case, all at the carina. Two humans splitting one mask are expected to look
  like this, not like two humans drawing two lumens. The first 20 double-read cases measure it for real (below).

**Mixing team reads and proxy.** Fused team labels replace the proxy case by case. A case with only one team read so
far uses that read, with the proxy-vs-read disagreement set to `ignore`.

**Convention keeping (A3, run in the direction D0 implies).**

- Every case is tagged `seed=girder`.
- A per-case monitor on every wave compares each read's union with the ImageCAS mask, flagging a read **drawn
  thin** (union Dice vs the ImageCAS mask < 0.9, or calibre closer to ImageCAS-X than to the mask).
- A wave halts if more than 10 % of reads are flagged.
- Flagged reads are excluded and redone.
- The sealed test is single-convention by construction.

**First-20 check (pre-registered), on the first 20 double-read cases:**

1. Inter-rater tF1 (per class), fraction of voxels set to `ignore`, and where they lie relative to the carina.
   *Prediction:* `ignore` ≤ 2 % of mask voxels in the median case, mostly at the carina. If it is larger, the
   disagreement is about extent, not names. The fusion rule then needs re-examination before the next wave, and A5r
   is promoted to run on that wave.
2. Proxy vs fused team label: macro tF1, swap rate. If < 0.80, proxies are dropped from the next wave.
3. Calibre (A5): with thick ImageCAS labels the spacing ablation A1 is expected not to trigger. If the reads come
   out thin, A1 becomes mandatory and decisive.

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
  **55 GB** (≈ 50–62 GB). That is under the 75 GB acceptance and the 80 GB card. The fallback should peak near 41 GB.
  If R0 still exceeds 75 GB, the first lever is batch 1 or activation checkpointing, which keeps the 128 mm context,
  before the fallback patch.
- **Loader.** LOADER_SUMMARY

**Compute forecast (unchanged):** 17.2 EFLOP per 1000 epochs, i.e. **27–85 H100-h**, central 45.

**R0 protocol:**

1. `nnUNetTrainerBenchmark_5epochs`: peak VRAM, s/epoch.
2. One epoch each at `nnUNet_n_proc_DA` = 12 / 20 / 22.
3. Compare against the predictions above; R0's figures then replace every forecast.

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
| R0 | 2 |
| R1, 1000 epochs | ~45 |
| A0 control, 250 epochs | ~11 |
| A1 native spacing (only if A5 triggers) | ~11 |
| A2 default window | ~11 |
| A3 no rotation | ~11 |
| A4 Skeleton Recall | ~12 |
| **A5r both reads as samples**, on the first wave with ≥ 150 double-read cases, vs fused-agreement | ~22 |

Ablation rule: paired tF1 CI excludes 0.

**Inference:** tile step 0.5, Gaussian, no TTA; **`--save_probabilities`** on every val and test case (A7).

### 2.6 Post-processing (A2, A7, A8)

**Always on:** threshold; drop components < 100 voxels; never delete ≥ 100 voxels; never force left and right apart.

**FP gate on this raw output.**

**Candidates, each adopted only if it wins on val by tF1 (CI):**

| Step | What | Adoption rule |
|---|---|---|
| P1 | 3 mm bridging | CI + clean bridge audit; not expected to pass (+0.010, half its joins FP) |
| P1′ | Gap-centred re-inference + support-gated bridging | Judged only against the tile-step-0.5 baseline |
| P2 | Label repair | CI |
| R | Bridge's rule renaming, ramus = LCx | CI excludes 0 **and** swap rate no higher |
| H | Hybrid decoding from saved softmax | Same as R; no prior weight |

The **bridge audit** (Delta's) is binding: bridges made, unsupported orphans, cross-tree joins, FP before/after.

Order: P1/P1′ → P2 → R/H.

### 2.7 How labels arriving over time are used

| Team reads | Action |
|---|---|
| 0 | R0; CPU prep; R1 + A0–A4 on the proxy; P1–H judged on R1 val |
| first 20 double-read cases | First-20 check (§2.1) |
| sealed test (100 cases × 2 reads) | Fused, adjudicated where needed, frozen. Inter-rater ceiling on these 100 |
| every wave | Convention monitor (thin-read flags, 10 % halt); fusion; adjudication queue |
| ≥ 150 double-read training cases | Fine-tune 250 epochs on {fused team ∪ proxy}; **A5r** (separate samples vs fused agreement) |
| +300 / +600 | Fine-tune 250 epochs; at ≥ 600, paired team-only vs team + proxy |
| all 900 | Final from scratch, 1000 epochs, on the label form that won A5r; 5-fold only if it beats single by tF1 |

## 3. Evaluation

**Decisive metric:** macro tF1 @ **1.5 mm** (D3), from the ported `src/segtrain` implementation only (A9).

**Ostium (A1):** TotalSegmentator aorta contact ≤ 5 mm, cross-checked with `thick` / `pool_thick`. A disagreement
> 5 mm is flagged to a human. The check is validated on 30 val cases against ImageCAS-X `start_points`.

**FP gate:** on the raw prediction, ≤ 1 per case.

**Reference with two reads.** The decisive score of a model on a case is **the mean of its tF1 against read 1 and
against read 2**. Adjudicated cases use the majority-of-three label. This uses both reads without inventing a fused
truth for scoring, and it keeps the model on the same footing as a human.

**The 1000-case inter-rater ceiling (D2).** For every case, inter-rater tF1 is the mean of read 1 scored against
read 2 and read 2 against read 1, per class. It is used four ways:

1. **Per-class ceiling and acceptance.** On the sealed test, the model's per-class tF1 must be ≥ the inter-rater
   per-class tF1 − 5 points, both from the same cases. This replaces v2's 20-case ceiling.
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

- per-class tF1 ≥ inter-rater − 5 points;
- FP ≤ 1 per case;
- swap rate < 5 %.

## 4. Evidence

The v2 evidence table stands. New this round:

| Claim | Evidence |
|---|---|
| Fallback 192 × 256 × 256: 93.5 % / 91.5 % / LM visible 85 % | [[Atlas - The fallback 192 × 256 × 256 patch at 0.5 mm, measured]] |
| Activation memory ~55 GB predicted; loader throughput measured with nnU-Net's own pipeline | [[Atlas - Without a GPU, nnU-Net's own loader and a saved-tensor count bound R0]] |
| Two independent splits of the same mask disagree on 0.26 % of voxels, at the carina | [[Atlas - The rule labeller disagrees with the projected proxy on 0.3 percent of voxels, all at the carina]] |
| Majority vote ≈ STAPLE when raters are few; STAPLE needs raters to weight | [[Fusing multiple annotations and learning from noisy labels]] (Karimi et al. 2020) |
| Bridging alone +0.01, half its joins FP | [[Delta - Real bridging on 17 nnU-Net predictions gains little alone, half its 3 mm joins are false positives, and gap-centred re-inference makes it work]] |
| Cross-checked ostium 116/116 | [[Delta - Two cheap ostium rules find 116 of 116 true ostia, and their disagreement flags every miss]] |
| Rule naming within 0.007–0.037 of oracle | [[Bridge - On real stage-1 output, the two-stage namer is within 0.01-0.03 tree-F1 of perfect naming]] |

## 5. Risks and early detection

| Risk | Early signal | Response |
|---|---|---|
| Reads disagree on extent, not just names (larger `ignore`) | First-20: `ignore` > 2 % median, away from the carina | Re-examine fusion; run A5r on that wave; brief annotators |
| Wholesale disagreement common | Adjudication rate > 15 % on the first 100 | Re-instruct; third reads budgeted |
| Annotators draw thin despite D0 | Per-read thin flag; wave halt at 10 % | Exclude and redo |
| Over-VRAM at 256³ | Memory model (~55 GB) vs R0 | Batch 1 or checkpointing before fallback |
| Loader-bound | Loader note vs R0 | Workers → GPU spatial transform → lower augmentation probabilities |
| Repair hides FPs | Gate on raw output; audit | — |
| Cut rate unknown (all vault predictions share one small-patch model) | R1 val | P1′ / R judged then |

## 6. Comparison

The plan now conforms to D0–D5. Option-A machinery and the trunk/territory switch are removed. What v3 adds over v2
and over the challengers is a concrete, cheap answer to the two-reads question:

- agreement plus `ignore`, adjudication for wholesale disagreement;
- A5r as a test of the main alternative;
- a scoring rule that uses both reads;
- the 1000-case ceiling used per class, per case and per annotator.

The challengers' adopted parts (A1–A9) are unchanged in role.

## 7. Cost

**GPU:** ≈ 220–470 H100-h (+22 h for A5r); ~105 h before any team read.

**Human, new:** third reads for wholesale-disagreement cases. Expected ≈ 10 %, from the 10.5 % wholesale rate between
the two automatic namers, ≈ 100 extra reads over 1000 cases. Also the per-wave monitor review.

**Engineering:** `fuse_reads.py` (0.5 day).

## 8. Changes since v2

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
6. **R0 pre-measurements:** memory model and nnU-Net loader throughput.
