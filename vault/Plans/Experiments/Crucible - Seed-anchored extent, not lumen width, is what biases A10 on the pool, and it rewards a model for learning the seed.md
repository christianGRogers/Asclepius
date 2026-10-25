---
tags: [plans/experiment, round-10, A31, A10, D26, L5, seed-anchoring, synthetic]
author: Crucible
round: 10
updated: 2026-10-25
issue: christianGRogers/Asclepius#113
---

# Seed-anchored extent, not lumen width, is what biases A10 on the pool, and it rewards a model for learning the seed

**Question (A31.2, Round 9 L5).** Under D26 every class starts as a full copy of the TotalSegmentator seed. Janus 0
draws the lumen about one voxel inside ImageCAS-X's (#43). If readers keep the seed:
- what convention do the reads follow;
- what does that do to A10;
- and what does a fine-tune decided on such reads learn?

**Method.** `experiments/Crucible/r10/r10_seed_extent.py` → `r10_seed_extent.json`. CPU, 64 synthetic cases.
- Phantom: Bridge's (`experiments/Bridge/wave1/synth.py`: four classes beside an aorta, 0.5 mm voxels).
- Scoring: the pinned `segtrain.tf1` (A1c `24441cf8…5254`) with the A1 aorta ostium.
- The seed keeps a share τ of each LAD/LCx/RCA distal segment, τ ∈ {1, 0.8, 0.6, 0.4}. That is 100 %, about 87 %,
  about 76 % and about 65 % of each class's centreline.
- Reads:
  - **anchored**: two readers keep the seed's extent (τ × U(0.95, 1)), each with their own path jitter;
  - **independent**: two readers draw the true extent (U(0.85, 1)).
- Models:
  - **full**: the true extent, one voxel thinner (Janus 0-like);
  - **seed-like**: the seed's extent, which is what fine-tuning on anchored reads teaches.

Effect sizes are the phantom's, not the pool's.

## Result (16 cases per level; A10 contrast = model-vs-reads tF1 − inter-read tF1; D6 fails below −0.05)

| Seed keeps | Class | Inter-read, anchored | Full model: contrast vs anchored reads (precision) | Seed-like model: contrast vs anchored reads | Full model: tF1 vs truth | Seed-like model: tF1 vs truth |
|---|---|---|---|---|---|---|
| 100 % | LAD / LCx / RCA | 0.95 / 0.97 / 1.00 | +0.01 / −0.01 / −0.00 | +0.00 / −0.03 / −0.02 | 0.99 / 0.99 / 1.00 | 0.98 / 0.98 / 1.00 |
| ~87 % | LAD / LCx / RCA | 0.97 / 0.98 / 1.00 | −0.06 (0.90) / −0.05 (0.93) / −0.03 (0.95) | −0.05 / −0.04 / −0.01 | 0.98 / 0.99 / 1.00 | 0.95 / 0.95 / 0.98 |
| ~76 % | LAD / LCx / RCA | 0.95 / 0.99 / 1.00 | **−0.12 (0.78) / −0.10 (0.81) / −0.12 (0.82)** | −0.02 / −0.01 / −0.01 | 0.99 / 0.99 / 1.00 | 0.88 / 0.90 / 0.91 |
| ~65 % | LAD / LCx / RCA | 0.97 / 0.97 / 0.97 | **−0.18 (0.71) / −0.16 (0.70) / −0.14 (0.73)** | −0.03 / −0.01 / +0.01 | 0.99 / 0.98 / 1.00 | 0.81 / 0.82 / 0.85 |

**Width control.** Against independent reads (LAD/LCx/RCA, all four levels):

| Model | Mean contrast | Range |
|---|---|---|
| Full extent, one voxel thinner (Janus 0-like) | −0.020 | −0.045 to +0.007 |
| Same model drawn at the readers' width | −0.003 | −0.021 to +0.020 |

So one voxel of width costs about 0.02 of A10 in this phantom. A quarter of the extent costs 0.10–0.12.

LM, which the seed does not shorten here, stays within ±0.04 throughout. That is the phantom's noise.

## Reading

1. **Width moves tF1 a little; extent moves it a lot.**
   - tF1's precision asks whether the predicted centreline lies inside the reference voxels. A one-voxel width
     difference mostly leaves the centreline inside: about 0.02 here.
   - Distal extent the reads lack becomes predicted centreline outside the reference, so precision falls: 0.10–0.18.
   - So the convention that matters most for A10 is **how far each vessel is drawn**. Janus 0's thin rim (#43) is a
     second-order term: about 0.02, inside D6's 0.05 margin but not free.
2. **Anchored reads agree with each other whatever the seed misses.** Inter-read stays 0.95–1.00 at every τ. A10's
   right-hand side cannot reveal the bias.
3. **A correct model fails A10.** Once the seed misses about a quarter of the centreline, a model that traces the
   true tree (tF1 vs truth 0.99) has a contrast of −0.10 to −0.12 and fails D6. A model that learned the seed
   passes (−0.01 to −0.02) while scoring 0.88–0.91 against the truth.
4. **D35 would pick the seed-like model.** A fine-tune decided only on anchored reads is rewarded for shortening
   vessels. The guard has to come from a reference that is not seed-anchored: **ImageCAS-X val 80** (expert,
   seed-free).
5. **The signature is visible in D35's reads without ground truth.** All three hold at once:
   - model-vs-read precision falls well below model-vs-read recall;
   - the model's extra centreline is contrast-filled (A23's contrast-supported tF1);
   - reads add little to the seed (Bridge's seed-edit sizes, A31.2).

## What it changes

- **A31.2 reporting on D35.** Report model-vs-read recall and precision per class, beside the seed edit sizes and
  A23. The seed flag (seed-vs-read ≥ inter-read − 0.02) gets this signature as its reading.
- **A fine-tune gate.** Every Janus k is accepted onto D35 only if it is also **non-inferior to Janus 0 on val 80**
  (decisive macro, margin 0.01, with A22's seed term), and no class's ImageCAS-X recall falls by more than 0.02.
- **L5 (the lead's).** If reads prove seed-anchored, A10 on the seal is biased against a full-extent model. The
  recommended answer:
  - A10 stands;
  - the accepted model must also hold the ImageCAS-X line (the val-80 gate above, and A26's sealed-80 red flag);
  - the D35 extent diagnostic is reported beside A10.
- **The pre-read domain check (A31.4) can predict the bias before any read exists.** On non-sealed volumes only,
  report the share of Janus 0's centreline that lies inside the TotalSegmentator seed, per source. That share is τ.
  Below about 0.85 in a source, anchored reads would cost a correct model about 0.05 of A10 there.

## Limits

- Synthetic phantom, 16 cases per level, no side branches. Real seeds also add veins and miss side branches, so the
  pool's τ is unknown until the domain check or wave 1.
- TotalSegmentator scores 70.5 Dice against ImageCAS-X (arXiv:2608.30404, Table 2), but how that splits between
  width, extent and false positives is not published.
- How strongly readers anchor is a human factor. Constantinou et al. (Clin Oncol 2025, DOI
  10.1016/j.clon.2024.10.032) found 19–28 % of errors planted in AI contours survived clinical editing, but that
  study covers radiotherapy contours, not coronary trees.
