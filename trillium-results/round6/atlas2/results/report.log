# Atlas run 2: A1 re-score and FP census of run 1, and the A2 window ablation

Generated 2026-10-10 22:54:47. Machine-readable: `results.json`; per case: `per_case_run1.json`, `per_case_b.json`; FP components: `census_run1.json`, `census_b.json`.

Metric: `segtrain.tf1` sha256 `3c737cbcc0ba24d38f923a52a28d479b34b579d6943f4c55a8cae48f66ad9253` (frozen hash match: True). Ostium of record: centreline voxel nearest the TotalSegmentator aorta (A1). Decisive aggregate: aorta present (A1a), flagged trees left out (A1b).

| arm | decisive macro tF1 @1.5 | per class LM / LAD / LCx / RCA (unflagged) | flagged trees | macro incl. flagged | FP comps / case | provisional cases |
|---|---|---|---|---|---|---|
| run 1 (fixed window [−300, 1300]) | 0.896 (n=80) | 0.966 / 0.901 / 0.846 / 0.883 | 44/316 | 0.884 | 1.49 (42/80 ≤ 1) | 0 |
| B (default window) | 0.893 (n=80) | 0.966 / 0.899 / 0.828 / 0.883 | 44/316 | 0.870 | 1.30 (49/80 ≤ 1) | 0 |

## Window decision (A16, rule fixed before the run)

Paired B − run 1 on 80 cases: decisive tF1 -0.0027 [-0.0118, 0.0062] (B better/worse in 42/38 cases); FP -0.188 [-0.475, 0.100] per case.

**Winner: default** — tF1 tie (CI -0.0118..+0.0062); FP B−A -0.188 per case.

Caution: B completed 368 epochs, not 412; the pairing is weakened.

### FP census, run 1 (fixed window [−300, 1300])

| category | components | share | mm³ | share of volume |
|---|---|---|---|---|
| confident_other | 94 | 0.79 | 6653 | 0.87 |
| icx_vessel | 18 | 0.15 | 926 | 0.12 |
| low_confidence | 7 | 0.06 | 55 | 0.01 |

Majority by count: **confident_other** (A15 routing: low_confidence → global threshold; icx_vessel → question for the humans; confident_other → reopens the recipe).

Global vessel-probability threshold (A15; val only, not yet chosen):

| t | macro tF1 (all trees) | FP comps / case |
|---|---|---|
| 0.5 | 0.884 | 1.49 |
| 0.6 | 0.883 | 1.48 |
| 0.7 | 0.883 | 1.34 |
| 0.8 | 0.882 | 1.27 |
| 0.9 | 0.869 | 1.31 |
| 0.95 | 0.868 | 1.23 |

Ostium validation (ImageCAS-X start points, validation only): 160 ostia, median 2.0 mm, 143 within 5 mm, 32 flagged, 5 silent misses (> 5 mm, unflagged).

### FP census, B (default window)

| category | components | share | mm³ | share of volume |
|---|---|---|---|---|
| confident_other | 78 | 0.75 | 6068 | 0.88 |
| icx_vessel | 20 | 0.19 | 727 | 0.11 |
| low_confidence | 6 | 0.06 | 69 | 0.01 |

Majority by count: **confident_other** (A15 routing: low_confidence → global threshold; icx_vessel → question for the humans; confident_other → reopens the recipe).

Global vessel-probability threshold (A15; val only, not yet chosen):

| t | macro tF1 (all trees) | FP comps / case |
|---|---|---|
| 0.5 | 0.871 | 1.30 |
| 0.6 | 0.871 | 1.24 |
| 0.7 | 0.870 | 1.21 |
| 0.8 | 0.864 | 1.21 |
| 0.9 | 0.857 | 1.15 |
| 0.95 | 0.859 | 1.15 |

Ostium validation (ImageCAS-X start points, validation only): 160 ostia, median 2.0 mm, 143 within 5 mm, 32 flagged, 5 silent misses (> 5 mm, unflagged).

## The 36 clean open test cases (for Bridge)

Predicted 36/36 with run 1's checkpoint, softmax saved; paths and command in `open36_manifest.json` (volumes stay on $SCRATCH). No sealed case was touched.

Reading: `vault/Plans/Experiments/Atlas - Pending Trillium run 2, A1 re-score, FP census and the window ablation.md`.
