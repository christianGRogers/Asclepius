---
tags: [plans/experiment, proxy-labels, qa, ramus, amendment-a4]
author: Atlas
round: 4
updated: 2026-10-08
---

# With ramus → LCx, the proxy QA ignores 0.3 % of voxels and excludes 11.6 % of cases

## Question

Amendment A4 (Round 3) requires two things before R1:

- the A4 QA must be re-run with ramus → LCx (D1b) on both sides, the projected proxy and Bridge's namer;
- a disagreement that is **only about the ramus** must never exclude a case. The namer cannot tell a ramus from an
  early diagonal by geometry; Bridge measured 88.2 % of held-out cases fully right and 7.9 % swaps under D1b.

What do the voxel `ignore` cost and the case exclusions become?

## Method

The same 172 cases (76 held out from Bridge's development) and the same frozen namer (`rerank_learned`, learned
ostium weights, 4 mm naming bridges) as
[[Atlas - The rule labeller disagrees with the projected proxy on 0.3 percent of voxels, all at the carina]], with
three changes:

- **Ramus → LCx on both sides.** The proxy counts ImageCAS-X IM (ramus) voxels as LCx; the namer runs with
  `RAMUS = 'LCx'`.
- **Ignore is reported twice:** for all near voxels, and with ImageCAS-X ramus voxels left out.
- **Ramus-only exemption:** a case flagged only by the LAD↔LCx swap is exempt when, with ImageCAS-X ramus voxels left
  out, the swap is ≤ 5 %. Ostium (> 5 mm) and LM (Dice < 0.5) flags are never exempt.

Script: `experiments/Atlas/proxy_qa.py` (`RAMUS=LCx`; `RAMUS=inherit` reproduces the Round-2 run). Bridge's code
is used read-only.

## Result

| | Round 2 (ramus = inherit) | **Round 4 (ramus → LCx)** |
|---|---|---|
| Voxels set to `ignore`, median per case | 0.26 % | **0.29 %** |
| p90 per case | 1.3 % | 5.2 % |
| … ImageCAS-X ramus voxels left out (median / p90) | — | 0.27 % / 2.8 % |
| Share of a case's ignored voxels within 10 mm of the carina (median / mean) | 100 % / 93 % | 100 % / 89 % |
| Cases flagged by ostium > 5 mm / LM Dice < 0.5 / swap > 5 % | 8 / 9 / 10 | 8 / 9 / 20 |
| **Exempted as ramus-only** | — | **7** |
| **Cases excluded until reviewed** | 18 (10.5 %) | **20 (11.6 %)**; 27 without the exemption |
| Held-out cases excluded | 6 / 76 | 6 / 76 (4 exempted) |

45 of 172 cases contain an ImageCAS-X ramus; in those, ramus voxels are a median 4.8 % of the named voxels.

## What it implies

1. **Setting the ramus to LCx doubles the swap flags** (10 → 20). That is the namer's known ramus/diagonal confusion
   showing up; the exemption removes 7 of them. The excluded fraction rises only from 10.5 % to 11.6 %, about 74 of
   640 training/val cases, roughly 6–7 analyst-hours of review.
2. **The typical case is unchanged** (median `ignore` 0.29 %, still at the carina). The heavier tail (p90 5.2 %) is
   mostly ramus voxels: with them left out, p90 is 2.8 %.
3. **Recipe change (v4).** In a ramus-only-exempt case, the voxels where the two disagree are **not** set to
   `ignore`. The proxy's name for them is the expert's (ImageCAS-X traced the ramus, and D1b maps it to LCx), while
   the namer's is the one that is known to fail. Elsewhere the A4 voxel rule is unchanged.

## Limits

- Two namers, neither of them truth.
- The exemption test uses ImageCAS-X's own ramus labels. That is only possible on the proxy, where an expert name
  exists. For two human reads, the same exemption needs the geometric test in `fuse_reads.py` (one swapped branch
  leaving within 10 mm of the carina, ≤ 25 % of LAD+LCx).
- 172 of 640 cases.
