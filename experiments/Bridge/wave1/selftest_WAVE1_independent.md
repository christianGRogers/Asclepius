# Wave-1 report (Round 9 A31)

24 volumes scored, 0 errors, 0 without an aorta; 24 patients ({'primary': 24, 'anomalous': 0, 'spacing_suspect': 0}).

## A31.1 f and k (primary stratum)

| Class | val SD (n) | f [95 % CI] (n) | k [95 % CI] (n) | scorable share |
|---|---|---|---|---|
| LM | 0.0813 (72) | 0.372 [0.277, 0.442] (23) | 1.98 [0.825, 3.471] (23) | 0.958 |
| LAD | 0.0783 (72) | 0.643 [0.469, 0.759] (23) | 1.133 [0.358, 1.614] (23) | 0.958 |
| LCx | 0.1111 (72) | 0.53 [0.356, 0.66] (23) | 0.546 [0.179, 1.053] (23) | 0.958 |
| RCA | 0.0793 (56) | 0.357 [0.096, 0.559] (18) | 3.356 [1.71, 12.976] (18) | 0.75 |

**Extension rule (f or k > 1.2):** triggered by LM k=1.98, RCA k=3.356 → **extend the seal to 200 patients** along the pre-registered order, before any sealed read is scored.
- Read with care: at 24 primary patients this pre-registered rule fires by chance about 82% of the time even when f = k = 1 (trigger_false_alarm.py, n = 20). Its error is the cautious one (a larger seal), so it is applied as written; the CIs above show whether the trigger is clear of noise.

| n | P(all 4 pass), δ = 0 | per class | P(all 4), δ = −0.02 |
|---|---|---|---|
| 150 | 1.0 | {'LM': 1.0, 'LAD': 1.0, 'LCx': 1.0, 'RCA': 1.0} | 0.917 |
| 200 | 1.0 | {'LM': 1.0, 'LAD': 1.0, 'LCx': 1.0, 'RCA': 1.0} | 0.978 |
| 250 | 1.0 | {'LM': 1.0, 'LAD': 1.0, 'LCx': 1.0, 'RCA': 1.0} | 0.993 |

## A31.2 Seed-vs-read against inter-read

| Class | seed-vs-read [CI] (n) | inter-read [CI] (n) | seed-anchored (≥ inter − 0.02) |
|---|---|---|---|
| LM | 0.7995 [0.6861, 0.8956] (23) | 0.9422 [0.9163, 0.9621] (23) | False |
| LAD | 0.7487 [0.6631, 0.8274] (23) | 0.9617 [0.9363, 0.9814] (23) | False |
| LCx | 0.6403 [0.5169, 0.7443] (23) | 0.9796 [0.9647, 0.9897] (23) | False |
| RCA | 0.7204 [0.6175, 0.8216] (18) | 0.9613 [0.9141, 0.9991] (18) | False |

Seed edits (report only): reads add 0.4533 [0.4205, 0.4858] of their voxels beyond the seed and remove 0.5609 [0.5377, 0.5825] of the seed; 0 of 48 reads add nothing to it.

## A31.3 Model-vs-read per source (report only)

| Source | stratum | patients | macro [CI] | LM | LAD | LCx | RCA |
|---|---|---|---|---|---|---|---|
| Figshare-CardiacCT15 | primary | 1 | 0.9413 None | 0.9348 | 0.9918 | 0.8718 | 0.9666 |
| Figshare-EpicardialFat-CE | primary | 3 | 0.9499 [0.9352, 0.9592] | 0.9417 | 0.931 | 0.9428 | 0.9964 |
| Kaggle-CAD-RandomSamples | primary | 2 | 0.9058 None | 0.9296 | 0.8905 | 0.8504 | 0.9921 |
| Mendeley-SDN-cy54ttk3fj | primary | 4 | 0.9558 [0.9429, 0.9734] | 0.932 | 0.9417 | 0.9515 | 0.9981 |
| Taiwan-AICUP-CardiacCT | primary | 13 | 0.9449 [0.928, 0.9599] | 0.9456 | 0.9375 | 0.9277 | 0.9768 |
| VMR-Coronary | primary | 1 | 1.0 None | None | None | None | 1.0 |
