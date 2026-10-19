# Wave-1 report (Round 9 A31)

24 volumes scored, 0 errors, 0 without an aorta; 24 patients ({'primary': 24, 'anomalous': 0, 'spacing_suspect': 0}).

## A31.1 f and k (primary stratum)

| Class | val SD (n) | f [95 % CI] (n) | k [95 % CI] (n) | scorable share |
|---|---|---|---|---|
| LM | 0.0813 (72) | 3.781 [2.645, 4.476] (23) | None None (23) | 0.958 |
| LAD | 0.0783 (72) | 3.151 [2.289, 3.74] (23) | None None (23) | 0.958 |
| LCx | 0.1111 (72) | 3.289 [2.6, 3.649] (23) | None None (23) | 0.958 |
| RCA | 0.0793 (56) | 4.992 [3.789, 5.54] (21) | 1.169 [0.993, 1.306] (21) | 0.875 |

**Extension rule (f or k > 1.2):** triggered by LM f=3.781, LAD f=3.151, LCx f=3.289, RCA f=4.992 → **extend the seal to None patients** along the pre-registered order, before any sealed read is scored.
- f or k not measurable in every class (fewer than 3 primary patients with values)

## A31.2 Seed-vs-read against inter-read

| Class | seed-vs-read [CI] (n) | inter-read [CI] (n) | seed-anchored (≥ inter − 0.02) |
|---|---|---|---|
| LM | 1.0 [1.0, 1.0] (23) | 1.0 [1.0, 1.0] (23) | True |
| LAD | 1.0 [1.0, 1.0] (23) | 1.0 [1.0, 1.0] (23) | True |
| LCx | 1.0 [1.0, 1.0] (23) | 1.0 [1.0, 1.0] (23) | True |
| RCA | 0.7143 [0.5238, 0.9048] (21) | 0.7143 [0.5238, 0.9048] (21) | True |

Seed edits (report only): reads add 0.0 [0.0, 0.0] of their voxels beyond the seed and remove 0.1714 [0.1593, 0.1841] of the seed; 48 of 48 reads add nothing to it.

**Seed-anchored in LM, LAD, LCx, RCA.** A10 would compare the model with a seed-anchored pair: report the A23 diagnostic first beside A10, and put Round 9 L5 to the lead.

## A31.3 Model-vs-read per source (report only)

| Source | stratum | patients | macro [CI] | LM | LAD | LCx | RCA |
|---|---|---|---|---|---|---|---|
| Figshare-CardiacCT15 | primary | 1 | 0.4554 None | 0.7901 | 0.8032 | 0.0879 | 0.1404 |
| Figshare-EpicardialFat-CE | primary | 3 | 0.5652 [0.4558, 0.6394] | 0.4856 | 0.5953 | 0.5441 | 0.6357 |
| Kaggle-CAD-RandomSamples | primary | 2 | 0.64 None | 0.4121 | 0.4135 | 0.8845 | 0.85 |
| Mendeley-SDN-cy54ttk3fj | primary | 4 | 0.6158 [0.4098, 0.8372] | 0.6282 | 0.7221 | 0.7069 | 0.4061 |
| Taiwan-AICUP-CardiacCT | primary | 13 | 0.5793 [0.4544, 0.6974] | 0.5766 | 0.6072 | 0.5566 | 0.5493 |
| VMR-Coronary | primary | 1 | 0.3718 None | 0.5612 | 0.5543 | 0.0 | None |
