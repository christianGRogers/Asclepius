---
tags: [experiment, janus-1f, round3, branches, scorer, gates, stage2, decode, D45, D47, D50]
author: Atlas
updated: 2026-11-23
issue: christianGRogers/Asclepius#303
code: experiments/Atlas/j1f_r3/
---

# Atlas - Janus 1-F round 3, the scorer of record is frozen, two F-A15 lines move with F-A25's counts, and L2 fails a correct branch

For [[Candidates/Janus 1-F/Atlas v3|Atlas v3]].
- **Data:** CPU work on the **D45 training 620**, labels only.
- **Not read:** no locked-100, sealed-80 or quality-0 label; no CT; no model output; no TotalSegmentator twin.
- **Locked-100 numbers:** F-A25's published counts only.
- **Where it ran:** nothing on Fir, SciNet or Trillium.

## Questions (Janus 1-F Round 2 ruling, §5)

1. Does the scorer, with SegQueue's collapse imported, pass Delta's and Atlas's checks on training fixtures? Do its
   pieces on the 620 equal the distribution F-A15's lines were simulated on? (item 1)
2. Do F-A15's lines still follow from their own rule at F-A25's locked counts? (items 1, 2)
3. How large is one locked case's `--save_probabilities` npz? (item 3)
4. What false-fail rates do F-A22's stage-2 numbers (L1 0.02, L2 30 mm / 95 %, K1 0.05) give for a correct model?
   (item 5)
5. Can T_L be built at all once F-A20 deletes the probabilities? (item 6)
6. Which `nnUNet_compile` did Janus 0 train with? (item 7)

## Setup

| Script | What |
|---|---|
| `j1f_scorer.py` | Round 2's scorer with `collapse4` → `segqueue14.labels.collapse_to_four` (pinned), plus `aggregate` and `gate` (exact fractions); sha256 **`5221032f…2e5b`** |
| `test_scorer.py` → `test_scorer.log` | Delta's `test_branch_score.py` (commit `4e49be9`) ported: same 6 cases, perturbations and assertions. Plus Atlas's round-2 real-case checks on c0217, plus the synthetic self-test |
| `check_620.py` → `check_620.jsonl`; `summarise_620.py` → `summary_620.json` | per case: SegQueue collapse vs D25, the 'Other' line, the scorer's pieces, the stage-2 surrogate (L1, K1, L2), grid size |
| `gate_refreeze.py` → `gate_refreeze.json` | round 2's `gate_sim.py`, unchanged, with this round's pieces and F-A25's counts |
| `j1f_gates.json`, `test_gates.py` → `test_gates.out` | F-A15 as a file (sha256 **`c14190cb…db68`**) and its test |
| `decode.py` | F, a one-byte NAMES map, and compose (T, T_L); self-test |
| `verdict.py` | J1F-A's verdict with the Q-F2-3 rule for both answers; self-test |
| `npz_size.py` → `npz_size.out` | one training case's grid, a network-like 13-channel softmax, saved as nnU-Net saves it |

**The stage-2 surrogate.** ImageCAS-X has none of the six stage-2 classes. A reference "treated as a prediction" is
therefore trivially clean on L1, K1 and L2. Each host's traced side branches play its stage-2 class instead:
- **LAD:** D1–D3 for S1–S3;
- **LCx:** OM1, OM2 and Ramus for a circumflex SN;
- **RCA:** PDA/PLB that collapse to the RCA, for SN, conus and RMA.

The model paints them exactly (k = 0) or one or two 6-connected voxels too wide (k = 1, 2). Rates come from 10 000
100-case draws (20-case draws for K1).

## Results

«RESULTS»

## What it changes

- **F-A16:** the scorer of record is `5221032f…` (P-r3-7). The swe copies it byte for byte, with `test_scorer.py` and
  `test_gates.py` as its tests.
- **F-A15:** three cells, re-derived by F-A15's own rule at F-A25's counts (P-r3-1), or kept as ruled at a D1
  false-fail of ≈ «D1FF».
- **F-A22's L2:** per component (P-r3-2). L1 0.02, K1 0.05, 95 % and 30 mm are kept.
- **F-A20:** `decode` also writes NAMES (P-r3-3), so T_L exists for Q-F2-3 (P-r3-4).
- **F-A20's `nnUNet_compile` "as Janus 0's":** pinned to `f` (P-r3-5).
- **J1F-A's GPU header:** `def-aso22_gpu`, 12 cores, 280G (P-r3-6).
