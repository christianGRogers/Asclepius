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
| LM | 0.7995 [0.6907, 0.8953] (23) | 0.9422 [0.9162, 0.9629] (23) | False |
| LAD | 0.7487 [0.6564, 0.8295] (23) | 0.9617 [0.9355, 0.981] (23) | False |
| LCx | 0.6403 [0.5236, 0.7433] (23) | 0.9796 [0.9652, 0.9899] (23) | False |
| RCA | 0.7204 [0.6142, 0.817] (18) | 0.9613 [0.9135, 0.9991] (18) | False |

Seed edits (report only): reads add 0.4533 [0.4207, 0.4848] of their voxels beyond the seed and remove 0.5609 [0.5376, 0.5822] of the seed; 0 of 48 reads add nothing to it.

## A31.3 Model-vs-read per source (report only)

| Source | stratum | patients | macro [CI] | LM | LAD | LCx | RCA |
|---|---|---|---|---|---|---|---|
| Figshare-EpicardialFat-CE | primary | 3 | 0.9452 [0.9352, 0.9592] | 0.9254 | 0.9525 | 0.9302 | 0.9797 |
| Mendeley-SDN-cy54ttk3fj | primary | 4 | 0.9304 [0.9058, 0.955] | 0.9525 | 0.8955 | 0.8974 | 0.9974 |
| Taiwan-AICUP-CardiacCT | primary | 17 | 0.9501 [0.9354, 0.9638] | 0.9409 | 0.9426 | 0.9304 | 0.9833 |
