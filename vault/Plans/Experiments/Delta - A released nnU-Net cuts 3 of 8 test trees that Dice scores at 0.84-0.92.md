---
tags: [plans, experiment, topology, real-predictions, nnunet, metrics, post-processing]
author: Delta
round: 1
updated: 2026-10-04
---

# A released nnU-Net cuts 3 of 8 test trees that Dice scores at 0.84–0.92

## Question

Simulated errors ([[Delta - Dice cannot see the errors that break a coronary tree]]) show what
metrics *could* miss. What do **real** CNN errors on our CTs look like: how often is a tree cut, how
long are the gaps, is there sub-threshold signal in them (can a probability-map step bridge them),
and do Dice / clDice notice?

## Method

- Model: **ImageCAS-X's released nnU-Net** (binary lumen, `3d_fullres`, PlainConvUNet, patch
  96 × 160 × 160 at native 0.5 × 0.35 × 0.35 mm; `pretrained_weights.zip`, Zenodo
  10.5281/zenodo.21887809; fold 0, `checkpoint_best.pth`, extracted by HTTP range read). Trained on
  the ImageCAS-X lumen (640 cases); our cases below are in ImageCAS-X's **test** list, so no fold saw them.
- Cases: the 8 ImageCAS-X test cases with a CT in our cache — c0111, c0150, c0250, c0407, c0526,
  c0675, c0750, c0900 (three of them downloaded for this).
- Inference on CPU with nnU-Net v2.8.1's `nnUNetPredictor` (`experiments/Delta/nnunet_infer.py`):
  CT cropped to the reference tree's bounding box + 10 mm (CPU budget; so false positives far from
  the tree are **not** counted), mirroring TTA off, tile step 0.75 (default 0.5), ~10–20 min/case.
- Analysis (`analyse_preds.py`, summary `summarise_an.py`) against the ImageCAS-X lumen with its
  4-class subtree labels (the model is binary; predicted voxels take the nearest reference class, so
  label metrics here measure only coverage and connectivity). Post-processing variants: `t50` (threshold
  0.5 + drop components < 100 voxels — ImageCAS-X's own protocol), `t30`, and **hysteresis** (≥ 0.2 or
  ≥ 0.1 kept if connected to ≥ 0.5). Rooted recall and tree-F1 as in the perturbation note, plus the
  same **with a gap tolerance d** (prediction dilated by d/2 before finding the pieces connected to an
  ostium, i.e. gaps < d bridged) for d = 1.5 and 3 mm. Every missed stretch of reference centreline
  is recorded: interior gap vs distal truncation, length, reference diameter, max probability inside.

## Result

**Per case (t50):**

| Case | Dice | macro Dice | per-class clDice | β₀ err | rooted recall | rooted @1.5 mm | rooted @3 mm | tree-F1 | tree-F1 @1.5 mm |
|---|---|---|---|---|---|---|---|---|---|
| c0111 | 0.903 | 0.907 | 0.959 | 0 | 0.932 | 0.932 | 0.932 | 0.959 | 0.959 |
| c0150 | 0.940 | 0.926 | 0.853 | 1 | 0.965 | 0.965 | 0.965 | 0.853 | 0.853 |
| c0250 | 0.921 | 0.926 | 0.983 | 1 | 0.943 | 0.977 | 0.977 | 0.971 | 0.983 |
| **c0407** | 0.845 | 0.868 | 0.935 | 6 | **0.549** | 0.659 | 0.887 | 0.694 | **0.756** |
| **c0526** | 0.919 | 0.902 | 0.938 | 3 | **0.398** | 0.829 | 0.829 | 0.238 | **0.850** |
| **c0675** | 0.839 | 0.854 | 0.880 | 9 | **0.535** | 0.778 | 0.778 | 0.647 | **0.829** |
| c0750 | 0.900 | 0.903 | 0.910 | 1 | 0.917 | 0.917 | 0.917 | 0.909 | 0.909 |
| c0900 | 0.910 | 0.904 | 0.962 | 0 | 0.967 | 0.967 | 0.967 | 0.962 | 0.962 |
| **mean** | 0.897 | 0.899 | 0.927 | 2.6 | 0.776 | 0.878 | 0.907 | 0.779 | 0.888 |

Per-class rooted recall in the three cut cases, at gap tolerance 0 / 1.5 / 3 mm:

| Case | LM | LAD | LCx | RCA |
|---|---|---|---|---|
| c0675 | 1.00 / 1.00 / 1.00 | **0.06** / 0.96 / 0.96 | 0.97 / 0.97 / 0.97 | **0.47 / 0.47 / 0.47** |
| c0407 | 1.00 / 1.00 / 1.00 | **0.38** / 0.73 / 0.95 | 0.79 / 0.79 / 0.79 | **0.27 / 0.27** / 0.96 |
| c0526 | 0.00 / 0.97 / 0.97 | 0.00 / 1.00 / 1.00 | 0.00 / **0.37 / 0.37** | 0.95 / 0.95 / 0.95 |

c0675's LAD is 96 % covered but cut from its LM by a sub-1.5 mm gap — closed by the tolerance — while
its RCA is cut by a 23.4 mm gap that no tolerance closes. c0526 at zero tolerance is a **metric
artefact**: the prediction stops just short of the reference ostium tip (LM centreline 97 % covered);
at 1.5 mm what remains is a real 9.1 mm LCx gap. c0407's breaks are 1.5–3 mm.

**Missed reference centreline (8 cases, t50):** 270 mm in 50 stretches (~34 mm per case); 70 % of it
distal truncation, 30 % interior gaps; reference diameter at the misses median 0.63 mm (EDT) — the
thinnest vessels; by class RCA 140 mm, LCx 88 mm, LAD 41 mm, LM 0.4 mm. **Interior gaps: 22**;
11 ≤ 1.5 mm, 17 ≤ 4 mm, **5 > 4 mm** (23.4, 9.1, 7.8, 7.3, 6.8 mm). Inside the gaps the maximum
probability is < 0.1 in 14 of 22.

**Post-processing:**

| Variant (mean of 8) | Dice | rooted recall | tree-F1 | FP components |
|---|---|---|---|---|
| t50 | 0.897 | 0.776 | 0.779 | 1.25 |
| t30 | 0.900 | 0.776 | 0.778 | 1.25 |
| hysteresis 0.2 | 0.900 | 0.777 | 0.776 | 1.50 |
| hysteresis 0.1 | 0.901 | 0.796 | 0.785 | 1.50 |
| t50 + gaps ≤ 1.5 mm bridged | — | 0.878 | 0.888 | — |
| t50 + gaps ≤ 3 mm bridged | — | 0.907 | 0.907 | — |

(The bridged rows are the gap-tolerant metrics, i.e. what a step that joins pieces within d mm would
give, before any extra false connections it might make.)

**Metric agreement across the 8 cases** (Spearman with tree-F1 @1.5 mm): Dice 0.52, per-class
clDice 0.69, macro Dice 0.81, binary clDice 0.81.

## What it implies

1. **Cut trees are not rare on real output: 3 of 8 test cases** have 45–60 % of the tree disconnected
   from its ostium at zero tolerance and 17–34 % still at 1.5 mm (an RCA cut by 23 mm in c0675, an LCx
   by 9 mm in c0526, LAD and RCA by 1.5–3 mm gaps in c0407) — while Dice is 0.84–0.92 and per-class
   clDice 0.88–0.94. The deciding metric must see this.
2. **The decisive metric needs a gap tolerance.** Zero tolerance reads an ostium-tip shortfall as a cut
   (c0526: 0.24 → 0.85 at 1.5 mm). I therefore define the deciding metric as **tree-F1 @ 1.5 mm**
   (gaps < 1.5 mm count as connected; the reference ostium is matched within 1.5 mm) — the same
   tolerance BCS's FFR solver applies before computing flow.
3. **Hysteresis on the probability map buys little** (rooted 0.776 → 0.796): most gaps carry almost no
   probability (max < 0.1 in 14/22). The repair that works is **geometric bridging** of pieces within
   1.5–3 mm (0.776 → 0.878 / 0.907). Gaps > 4 mm (5 of 22, but they hold most of the disconnected
   length) are beyond any safe bridging — they are a model problem (thin RCA/LCx), which is where a
   training-side change (bigger patch, Skeleton Recall) has to act and be measured.
4. For Bridge v1: 17/22 real interior gaps are ≤ 4 mm, so its 4 mm graph bridging would reconnect most
   of them for *naming*; the 5 longer gaps are the cases where a graph namer would orphan a subtree.
5. Where misses happen: distal, sub-millimetre (EDT) vessels, RCA and LCx most. This is the size
   regime of the ImageCAS-X lumen convention, not of our ~2× thicker masks.

## Limits

- One fold of one released model, 8 cases, binary output; small-patch configuration (96 × 160 × 160),
  i.e. *weaker* context than the 128 mm patches the candidates propose — those may cut less.
- CT cropped to the reference bbox + 10 mm: distant false positives not counted; tile step 0.75 and no
  TTA (both slightly below nnU-Net's default inference).
- The ostium is the thickest reference centreline endpoint (LM end preferred), not the aorta contact;
  the 1.5 mm tolerance absorbs the tip artefact this causes.
- Bridged rows are metric tolerances, not an implemented bridging step; a real step could also join
  false-positive blobs to the tree (1.25 FP components per case here).
