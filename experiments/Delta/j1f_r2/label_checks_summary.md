**train620** (620 cases): 1296 PDA/PLB components decided; 93 to the LCx; fallbacks 0 (unattached 0, tie 0). Left-sided (L-PDA/L-PLA) voxels 112379; LCx-reference voxels sent to the RCA 0; RCA-reference voxels sent to the LCx 0; cases with any mismatch: 0 []
**locked100** (100 cases): 217 PDA/PLB components decided; 16 to the LCx; fallbacks 0 (unattached 0, tie 0). Left-sided (L-PDA/L-PLA) voxels 19797; LCx-reference voxels sent to the RCA 0; RCA-reference voxels sent to the LCx 0; cases with any mismatch: 0 []

**Band** (120 training cases, hash-chosen). Released background (mm³), median [p10, p90] per case, and as a multiple of the case's tree volume:

| Host | 4 mm | 8 mm | 15 mm | 25 mm |
|---|---|---|---|---|
| LAD | 10k [8k, 12k]; ×5 | 37k [28k, 43k]; ×18 | 123k [95k, 143k]; ×60 | 341k [266k, 395k]; ×168 |
| LCx | 7k [4k, 10k]; ×4 | 26k [14k, 34k]; ×12 | 89k [54k, 114k]; ×43 | 258k [163k, 325k]; ×128 |
| RCA | 10k [8k, 12k]; ×5 | 33k [27k, 40k]; ×16 | 109k [91k, 129k]; ×54 | 310k [265k, 359k]; ×152 |
| union | 27k [22k, 32k]; ×13 | 90k [75k, 106k]; ×46 | 298k [253k, 341k]; ×151 | 803k [684k, 934k]; ×410 |

A 256³ patch at 0.5 mm is 2 097k mm³.

Share of a **traced** side branch's voxels within w of its own trunk (median over cases [p10]); p90 and max distance (median over cases):

| Branch (trunk) | 4 mm | 8 mm | 15 mm | 25 mm | p90 dist mm | max dist mm | cases |
|---|---|---|---|---|---|---|---|
| D1 (LAD) | 0.21 [0.11] | 0.45 [0.27] | 0.80 [0.52] | 1.00 [0.80] | 17.6 | 21.1 | 117 |
| D2 (LAD) | 0.17 [0.10] | 0.38 [0.24] | 0.77 [0.50] | 1.00 [0.74] | 20.1 | 24.3 | 61 |
| OM1 (LCx) | 0.17 [0.08] | 0.38 [0.19] | 0.75 [0.41] | 1.00 [0.65] | 17.9 | 20.7 | 100 |
| OM2 (LCx) | 0.16 [0.07] | 0.37 [0.19] | 0.92 [0.38] | 1.00 [0.57] | 14.8 | 17.6 | 40 |
| R-PDA (RCA) | 0.13 [0.08] | 0.23 [0.16] | 0.41 [0.28] | 0.67 [0.47] | 34.7 | 38.3 | 115 |
| R-PLA (RCA) | 0.12 [0.07] | 0.23 [0.14] | 0.42 [0.26] | 0.73 [0.44] | 31.2 | 35.1 | 114 |
