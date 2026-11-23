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

### 1. The scorer of record, on training fixtures and the 620

| Check | Result |
|---|---|
| `test_scorer.py`: Delta's 30 checks (6 hash-chosen training cases), 5 real-case checks on c0217, the synthetic self-test | **35 / 35 pass** (`test_scorer.log`) |
| SegQueue's collapse vs D25, outside "Other" and 255 | **0 voxels** in 620 cases (40 "Other" voxels in 2 cases differ; "Other" has no D25 class) |
| PDA/PLB components; fallbacks | 1,296 (1,203 to the RCA, 93 to the LCx); **0 fallbacks** |
| F-A18's 'Other' line | `{d3 47, d4_to_lad 2, other_lcx 20, other_nearest 1, other_ignore 8}`, as expected |
| Pieces vs `census_r2.jsonl` (count, voxels, length) | **identical** in 620 of 620 cases |

So the per-piece distribution F-A15 was simulated on is the scorer's own.

- **One behaviour of SegQueue's rule:** contact is face contact. A branch joined to its parent only diagonally counts
  as unattached, falls back to the RCA, and is counted.
- **The self-test has a case for it.** On the 620 references it never happens (0 fallbacks).

### 2. F-A15 at F-A25's counts (`gate_refreeze.out`)

| Locked counts | Lines by the rule | Worst human false-fail, frozen F-A15 | Worst, re-derived | P(reject): omission +0.10 / misnaming 0.10 / 0.20 |
|---|---|---|---|---|
| Round 1 (98/64/84/40/96/96) | = F-A15 | 7.1 % (verdict 0.3 %) | — | 99.7 / 57.7 / 99.9 % |
| **F-A25 (97/64/84/40/98/99)** | **D1 presence 0.93; PLB recall 0.90, presence 0.95** | **D1 10.3 %** (others ≤ 7.1 %) | D1 5.7 %, PLB 5.2 % (all ≤ 7.1 %) | 99.9 / 58.7 / 99.95 % → 99.9 / 57.2 / 99.95 % |

### 3. Disk

- **Grids:** the 620's grids are at most 512 × 512 × 275 (72.1 M voxels, 384 of 620 cases).
- **Uncompressed ceiling:** a 13-channel float32 npz is at most **3.75 GB per case**. A chunk of 10 is 37.5 GB; all
  100 at once would be 375 GB.
- **Measured on c0099** (54.0 M voxels):
  - float32 writes **2.34 GB** (83 % of uncompressed, 96 s);
  - float16 writes 0.027 GB, because the far field underflows to 0.
- **Planning number:** the float32 ceiling.

### 4. Stage 2's numbers under the surrogate (`summary_620.json`)

| | LAD | LCx | RCA |
|---|---|---|---|
| L1 pooled theft, k = 0 / 1 / 2 | 0 / 0.0058 / 0.0168 | 0 / 0.0078 / **0.0210** | 0 / 0.0056 / 0.0104 |
| P(L1 > 0.02), 100-case draws, k = 2 (point / upper bound) | 0.0002 / 0.11 | **0.78 / 1.00** | 0 / 0 |
| K1 in-lumen share, k = 1 / 2 (p95 of 20-case draws) | 0.015 / 0.020 | 0.015 / 0.020 | 0.006 / 0.007 |
| Pieces | 1,012 | 909 | 599 |
| Piece max distance from the stage-1 foreground, p50 / p90 / p95 / max (mm) | 19.9 / 35.4 / 39.8 / 60.0 | 21.5 / 46.3 / 50.8 / 62.3 | 39.5 / 51.0 / 55.0 / 67.2 |
| Cases failing L2 **per voxel** (> 30 mm) | 189 | 266 | 469 |
| Cases failing L2 **per component** (nearest voxel > 30 mm) | 0 | 0 | 0 |
| Piece nearest distance, max (mm) | 0.45 | 0.45 | 0.5 |

**What the surrogate shows:**
- **L1 and K1** never fire for an exact or one-voxel-wide model. L1 fires on the LCx at two voxels too wide.
- **L2 per voxel** fails a correct model in every 100-case draw on every host.
- **L2 per component** never does.

### 5. T_L and the verdict

- `decode.py selftest` passes. A plain 13-way argmax moves 9.8 % of voxels across territories on random logits.
- On the T test, T names a left PDA inside Janus 0's LCx territory PDA and keeps Janus 0's territory bit for bit.
- compose(Janus 0, NAMES) equals the direct within-territory argmax.
- `verdict.py selftest` passes for both answers to Q-F2-3.

### 6. `nnUNet_compile`

- `trillium/icx4/lib/job_body.sh` l. 38 exports `nnUNet_compile=f`.
- `git log -S nnUNet_compile` on it shows only its first commit, `2de3f2f` (2026-10-17). That is before Janus 0's
  checkpoint (2026-10-21).

## What it changes

- **F-A16:** the scorer of record is `5221032f…` (P-r3-7). The swe copies it byte for byte, with `test_scorer.py` and
  `test_gates.py` as its tests.
- **F-A15:** three cells, re-derived by F-A15's own rule at F-A25's counts (P-r3-1), or kept as ruled at a D1
  false-fail of ≈ 10.3 %.
- **F-A22's L2:** per component (P-r3-2). L1 0.02, K1 0.05, 95 % and 30 mm are kept.
- **F-A20:** `decode` also writes NAMES (P-r3-3), so T_L exists for Q-F2-3 (P-r3-4).
- **F-A20's `nnUNet_compile` "as Janus 0's":** pinned to `f` (P-r3-5).
- **J1F-A's GPU header:** `def-aso22_gpu`, 12 cores, 280G (P-r3-6).
