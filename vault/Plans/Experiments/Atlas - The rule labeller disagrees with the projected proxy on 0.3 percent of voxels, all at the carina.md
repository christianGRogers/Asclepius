---
tags: [plans/experiment, proxy-labels, qa, imagecas-x, amendment-a4]
author: Atlas
round: 2
updated: 2026-10-04
---

# The rule labeller disagrees with the projected proxy on 0.3 % of voxels, all at the carina

## Question

Amendment A4 makes Bridge's frozen rule labeller the QA layer on every proxy label. Where the labeller and the
ImageCAS-X-projected proxy disagree on a voxel, that voxel becomes nnU-Net's `ignore` label; where they disagree on
the LM, the ostium or the LAD/LCx split, the case is flagged for human review. Before adopting it:

- how many proxy voxels would be ignored?
- where are they?
- how many cases get flagged, i.e. how much human review does A4 cost?

This is also the only check of the proxy's naming possible before team labels exist (ruling §4.1): two independent
namers, one projected from expert labels and one from geometry rules, measured against each other.

## Method

- Cases: all **172** cases for which Bridge has cached skeleton extractions with ImageCAS-X counts
  (`$SCR/work/Bridge/ex/`); 76 are outside Bridge's development set (held out).
- Proxy: per mask voxel, the ImageCAS-X class of the nearest ImageCAS-X voxel within 2 mm. Bridge's `extract.py`
  stores these counts per skeleton vertex, using the territory mapping: D → LAD; OM, L-PDA, L-PLA → LCx;
  R-PDA, R-PLA → RCA. Only voxels whose projected class is LM/LAD/LCx/RCA count ("near" voxels, ~85 % of the mask).
- Labeller: Bridge's frozen v3, run exactly as in Bridge's `final_report.sh`: `rerank_learned` with
  `ostium_w_dev2.json`, plus the 4 mm component bridging that A4 specifies. Bridge's code was imported read-only.
- Per case:
  - ignored voxels = near voxels where proxy ≠ labeller;
  - their position relative to the labeller's LM bifurcation;
  - flags: LM Dice (proxy vs labeller) < 0.5; ostium error > 5 mm against the ImageCAS-X-derived ostium (Bridge's
    definition); LAD↔LCx swap > 5 % of LAD+LCx voxels.
- Script: `experiments/Atlas/proxy_qa.py`.

## Result

| | All 172 | Held-out 76 |
|---|---|---|
| Ignored voxels / near voxels, median per case | **0.26 %** | 0.27 % |
| p90 / max per case | 1.3 % / 69.5 % | 1.0 % / 60.8 % |
| Pooled over voxels | 1.95 % | 1.85 % |
| Ignored, by proxy class (median per case) | LM 2.7 %, LAD 0.18 %, LCx 0.23 %, RCA 0.0 % | LM 2.5 %, LAD 0.19 %, LCx 0.24 %, RCA 0.0 % |
| Share of a case's ignored voxels within 10 mm of the bifurcation (median) | **100 %** | 100 % |
| **Flagged cases** | **18 / 172 (10.5 %)** | 6 / 76 (7.9 %) |
| — ostium > 5 mm / LM Dice < 0.5 / LAD↔LCx swap > 5 % (overlapping) | 8 / 9 / 10 | 3 / 4 / 3 |
| Labeller failures (single tree etc.) | 2 | 1 |

LM agreement (Dice of proxy LM vs labeller LM), median 0.967.

## What it implies

1. **In a typical case the proxy and the rules agree on everything except a few millimetres at the carina.** That
   is exactly where an LM/LAD/LCx boundary is a convention, so masking those voxels with `ignore` costs ~0.3 % of
   supervision and removes the one place where projection and rules legitimately differ. A4's voxel rule is cheap.
2. **The pooled 2 % is driven by a few cases where one namer failed wholesale**, with up to 70 % of the voxels
   disagreeing. Voxel-level `ignore` is the wrong tool for those: it would delete most of the case's supervision.
   The plan therefore treats them by A4's case rule. The 10.5 % of cases flagged are **excluded from R1 training
   until a human reviews them** (~18 of 172, i.e. ~65 of the 640 training/val cases, ~5 min each ≈ 6 analyst-hours),
   not ignore-masked.
3. The proxy's naming is therefore consistent with an independent geometric namer in ~90 % of cases. Whether it
   matches the **team's** convention can only be measured on team labels. The pre-registered first-20 check stays.

## Limits

- This compares two namers, neither of which is truth. Where both are wrong in the same way (e.g. a ramus called
  LAD by both), nothing is flagged.
- The proxy here uses territory mapping. Under trunk mapping, side-branch voxels become background in the proxy
  but stay named by the labeller. A4 must then compare only on trunk-named voxels; the script would need a
  trunk-mode mask (not run).
- The flag thresholds (0.5, 5 mm, 5 %) are my choice. They were fixed before looking at the flag counts and not
  tuned.
- The 172 cases are those Bridge extracted (random order), not the full 640.
