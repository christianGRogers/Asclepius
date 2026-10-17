---
tags: [plans, experiment, trillium, gpu, topology, post-processing, tree-f1, result, round5]
author: Delta
round: 5
updated: 2026-10-10
status: done — P1′, P1 bridging and P2 repair fail their pre-registered tests
---

# Trillium P1′ result on the master model: gap-centred re-inference gains +0.0007, so post-processing leaves the recipe

## Question

Does P1′ (gap-centred re-inference, then ≤ 3 mm bridging) beat nnU-Net's default inference on the master-configuration model? Bridging alone (P1), the support rule and label repair (P2) are tested alongside. The decision table was pre-registered in [[Delta - PENDING Trillium run - does gap-centred re-inference beat nnU-Net's default inference on a thick-convention 4-class model]] and sharpened in [[Delta v5]] before any result was seen.

## Setup

- **Model.** Atlas's checkpoint (ResEnc 60 GB plan, 256³ patch, 0.5 mm isotropic, `checkpoint_final.pth`), inference only (A13).
- **Reference.** The thick convention: the ImageCAS mask split by ImageCAS-X names, territory rule, ramus → LCx.
- **Variants.** Two tile steps (0.5, nnU-Net's default; and 0.75), each run with raw output, bridging, repair, re-inference, the support rule, and combinations.
- **Output.** `trillium-results/round5/delta/results/` (SUMMARY.md, per_case.jsonl, split.json, log).

### Which cases were scored, and why 17 are missing

- **Scored:** 63 of the 80 open ImageCAS-X test cases, namely 27 of the 36 clean-open cases and 36 of the 44 development cases. The 100 sealed cases were never predicted (`n_sealed_excluded = 100`).
- **The 17 missing cases:** 9 clean-open (c0123, c0841, c0877, c0908, c0946, c0957, c0971, c0984, c0996) and 8 development (c0846, c0900, c0906, c0907, c0927, c0951, c0953, c0979).
- **Cause: my bug, not the split.**
  - Their ImageCAS-X segmentation files were absent from `$SCRATCH/delta_icx`: an earlier fetch had been interrupted.
  - `./delta` only re-ran the fetch when `filelist/test.txt` was missing, and the interrupted fetch had already written it.
  - `prepare` then logged "17 unusable" and **dropped** the cases (FileNotFoundError) instead of failing.
  - Every one of the files exists in the Zenodo archive and in our local copies.
- **Bias.** The missing cases are mostly high ImageCAS-X ids, where the interrupted extraction stopped. That has nothing to do with outcomes, so there is no selection bias, only lost power: the decision rests on n = 27, not 36.
- **Fixed in `trillium/delta`.**
  - The launcher now fetches until 800 segmentations are present.
  - `prepare` now refuses to evaluate if any input file is missing.

### Which ostium rule these numbers use

- **Rule.** `RefTree` from deltalib (A1 as of Round 3). Per reference tree component, the rule of record is `thick`: the thickest centreline endpoint, LM endpoints preferred. It is cross-checked against `pool_thick`, with the blood pool taken from the CT, and a disagreement above 5 mm flags the tree.
- **No TotalSegmentator aorta masks were used.** These are the provisional cheap rules. 11 of 53 reference trees on the clean cases were flagged.
- **Consequences under A1a.**
  - The **absolute** tF1 values decide nothing. On the thick reference these rules are wrong for about 1 tree in 8, sometimes silently ([[Delta - On the thick reference the cheap ostium rules miss 1 in 8 ostia silently, which made 13 of the 17 cut trees]]).
  - The `cut_cases` count (17 of 27 with rooted recall below 0.9) is mostly that artefact. It is not read as a cut rate.
- **Why the paired comparisons stand.** Both arms of every comparison are scored against the same reference with the same roots. A misplaced root lowers both arms alike. It dilutes a real effect but cannot create one.
- **Robustness to the ostium choice.** C2 was computed four ways (all cases or unflagged cases only, `thick` roots or `pool_thick` roots); see the table below. No version is positive.

## Results (clean open, n = 27; tF1 at 1.5 mm; paired bootstrap 95 % CI)

| Comparison | Δ tF1 | 95 % CI | better / worse |
|---|---|---|---|
| **C2** P1′ (step 0.5, re-inference + support-gated bridge) vs step 0.5 raw | **+0.0007** | [−0.0061, +0.0059] | 15 / 9 |
| C2, **pre-registered primary read** (v5): `pool_thick` roots, unflagged cases (n = 17) | **−0.0017** | [−0.0116, +0.0059] | — / 6 |
| C2, `pool_thick` roots, all 27 | +0.0014 | [−0.0056, +0.0072] | — / 8 |
| C1 tile 0.5 vs 0.75, raw | −0.0064 | [−0.0217, +0.0022] | 2 / 1 |
| C3 P1′ on step 0.75 vs step 0.5 raw | +0.0075 | [−0.0050, +0.0253] | 15 / 9 |
| C4 bridging alone | +0.0002 | [−0.0012, +0.0019] | 5 / 7 |
| C5 support rule | +0.0001 | [−0.0000, +0.0002] | 1 / 0 |
| C6 label repair | 0.0000 | [0, 0] | 0 / 0 |
| C2 on all 63 open cases (development included; reported only) | +0.0041 | [−0.0027, +0.0138] | — / 27 |

### Other numbers

- **Raw FP gate.** 1.19 per case on the clean cases, against 1.49 on Atlas's val.
- **Re-inference adds FP components.** 1.19 → 1.37 per case before bridging; bridging then hides some of them (1.00).
- **Bridge audit.** 22 joins, 10 of them false-positive joins and 0 cross-tree.
- **Gap sites.** Gap sites (un-anchored pieces within 15 mm) are found in 26 of 27 cases, so they do not single out cut cases.
- **Strict vs decided tolerance.** At 0 mm, bridging lifts tF1 from 0.807 to 0.835. At the decided 1.5 mm it changes nothing, because what ≤ 3 mm bridging joins is almost all gaps the 1.5 mm tolerance already forgives.
- **How P1′ makes cases worse.** Three cases lose more than 0.01: c0617 −0.066, c0470 −0.020, c0068 −0.015. In c0617, max-fusing the re-inferred window renames part of the LM (LM tF1 0.98 → 0.79) and adds 4 FP components. The window's names are less reliable than the full-volume pass.

## Against the pre-registered table

| v5 requirement | Result | Verdict |
|---|---|---|
| 1. Primary read: `pool_thick` roots, unflagged | −0.0017 [−0.0116, +0.0059] | fail |
| 2. C2 mean ≥ +0.002, CI > 0, no case worse by > 0.01 | +0.0007; CI includes 0; 3 cases worse by > 0.01 | **fail** |
| 3. Gain concentrated in gap-site cases | sites in 26/27 cases; mean gain there +0.0007 | fail (not testable as framed) |
| 4. FP joins < true joins; re-inference adds ≤ 0.1 FP per case | 10 vs 12 (pass); **+0.18** (fail) | fail |
| v4 table: C4 ≈ 0 → P1 removed; C5 ≤ 0 → support rule dropped; C6 CI not > 0 → repair stays off | +0.0002; +0.0001; 0 | P1 removed; support rule dropped; P2 off |

This is the outcome I predicted in v5 from the 0.004-per-case ceiling measured on Atlas's val. The master model rarely cuts trees once the ostium is right, the 1.5 mm tolerance already forgives small gaps, and what P1′ adds (new names in the window, new FP pieces) costs as much as it repairs.

## Decision (by the pre-registered rules)

- **P1′ is dropped.** nnU-Net's default inference (tile step 0.5) stands.
- **P1 bridging and P2 label repair are removed** from the recipe. They are not left switchable.
- **What stays from my work, as QA:**
  - the raw-prediction FP gate (A2);
  - the bridge-audit record, for anyone who bridges in an analysis;
  - the A1 ostium, revised to aorta-first per side in `segtrain.tf1`.

## Limits

- n = 27, one model, one seed. The effect would need to be about 10 times larger to matter.
- The reference is the projected proxy, not a team read.
- No aorta re-score of these predictions. The per-case score files were deleted after scoring, and an aorta re-score would not change paired differences that are ≈ 0 under all four ostium readings.
