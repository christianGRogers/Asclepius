---
tags: [plans/experiment, trillium, pending, fp-gate, loss, a24, round8]
author: Atlas
round: 8
updated: 2026-10-11
status: pending
---

# Atlas - Pending Trillium run 3, the FP-aware loss pilot

`trillium/atlas3/` (`./atlas3`) is the run approved by [[Round 8]] as **A24**. It goes before R1. It is one 1×H100
job of at most 23:50 under the same contract (account `def-aso22`, no arguments, never writes to Girder).

**Why.** Run 2's census routed the FP lever to the recipe (A15). 79 % of raw FP components are confident structures
beside the tree, mostly cardiac veins
([[Atlas - Trillium run 2 results, the A1 re-score, the window ablation and what the confident false positives are]]).
They are about 0.8 % of the predicted volume, so DiceCE barely penalises them, while the gate counts each one.

## Design (the five A24 conditions, as built)

1. **Pairing.** F0 (plain) and F1 (FP-aware, λ = 1, γ = 2, band 1.5 mm) make the loss the only difference.
   - **Same start.** Both warm-start from run 2's arm B `checkpoint_final.pth` (default window), with the A17a
     trainer, which loads the heads and warms the LR up before poly.
   - **Same seed (12345) and same data and augmentation stream.** The augmenters are deterministic
     `MultiThreadedAugmenter`s with fixed worker seeds, and the case sampler is seeded too. On CPU, F0, a repeat of F0
     and F1 produce bit-identical batches.
   - **Equal epochs**, set once from the time left before training starts, so each poly schedule completes. That is
     200 each at run 2's measured 175.85 s/epoch, with F1 budgeted at ×1.1.
   - If an arm still pauses, the result is reported, not decided.
2. **Decision table** (A22-amended; `decide_fp_term`). Paired F1 − F0, 80 val cases:
   - **Adopt** if FP per case falls with the case CI excluding 0, **and** the decisive tF1's seed-inclusive CI
     (SE = √(SE²_case + 0.013²)) has its lower bound above −0.01.
   - **Not adopted** if FP does not fall. R1 then runs plain.
   - **Not adopted, trade-off to the humans** if FP falls but tF1's upper bound is below −0.01.
   - **Second seed of both arms** (≈ 20 h, before R1, and it measures σ_seed) if FP falls but the tF1 interval
     straddles −0.01.
   - A single-seed tF1 difference inside ±0.02 is labelled "no difference detected".
   - MDEs: FP 0.41 per case; tF1 0.010–0.022 (case term).
   - Note that σ_seed alone contributes ±0.025 to the CI. Unless F1 is better by more than about 0.016, a falling FP
     count leads to **"second seed needed"**, not to adoption. That is the A22 rule working as intended.
3. **Reported alongside, per class:**
   - recall on ImageCAS-X-traced centreline;
   - recall on mask-only low-HU centreline (Delta's split: > 1 mm from ImageCAS-X, smoothed HU < 0.3 × median aortic
     HU);
   - the A23 contrast-supported tF1;
   - all three by the frozen module's own recall rule.
   - If F1 lowers mask-only low-HU recall while traced recall holds, the term is pulling against vein-like structure
     that some masks label. The label-noise reading in A24.3 then gains weight.
4. **The D7 sentence is corrected** in [[Atlas v10]] (below).
5. **Metric.** `segtrain.tf1` sha256 `24441cf8df0f000bd956c7dd9d8ae1daac866cfb14df1d174441d00e54f05254`
   (fallback centreline default), vendored verbatim. The entry point and the job refuse any other hash.

**Reuse.** No aorta is recomputed: run 2's 80 TotalSegmentator masks are reused. Phase A of run 2 took 3.7 h for
them. Run 1's references and B's preprocessed dataset are read in place.

## Budget

| Stage | Time |
|---|---|
| setup, hash check, schedule | minutes |
| F0: 200 epochs × 176 s + final validation with softmax | ≈ 9.8 h + 0.75 h |
| F1: 200 epochs × ≈ 193 s + final validation | ≈ 10.7 h + 0.75 h |
| F0 scored on CPU during F1; F1 scored after | ≈ 0.5 h |
| report | minutes |
| **total** | **≈ 22.5 h** of 23:50 |

## Expectations, stated before the run (Atlas)

These are expectations only; the table decides.
- F1 reduces `confident_other` FP components by about a third. The gate itself (≤ 1 per case) is still not met.
- tF1 is unchanged within ±0.01, so the verdict is likely **"second seed needed"**.
- Recall on traced centreline is unchanged. Recall on mask-only low-HU centreline falls slightly, which would support
  the label-noise reading.

## Tested on CPU

- **Dry runs.** Both case layouts pass against fake run-1 and run-2 trees. A tampered metric file is refused, and so
  is a missing run 2.
- **Job body.** It ran end to end with a stub trainer: equal-epoch schedule, both arms scored with the pinned metric
  (recall split and A23 on a real case), report and decision.
- **Arms.** `tests/test_fppilot.py`, with real nnU-Net components on CPU:
  - the term is confined to confident voxels beyond the band, and its gradients stay off the band and the tree;
  - the arms see identical batches;
  - only F1 carries the term.
- **Suite.** 733 passed, 47 skipped; ruff and shellcheck are clean.

## Limits

- **One seed** unless the table calls for a second.
- **A warm start from a truncated B** (368 epochs, not annealed). Both arms share it, so the comparison is fair, but
  absolute numbers sit near B's.
- **λ and γ are not tuned.** λ = 1 and γ = 2 are the pre-registered values, and tuning them would be a new decision
  under A19.
