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
- Read with care: at 24 primary patients this pre-registered rule fires by chance about 82% of the time even when f = k = 1 (trigger_false_alarm.py, n = 20). Its error is the cautious one (a larger seal), so it is applied as written; the CIs above show whether the trigger is clear of noise.
- f or k not measurable in every class (fewer than 3 primary patients with values)

## A31.2 Seed-vs-read against inter-read

| Class | seed-vs-read [CI] (n) | inter-read [CI] (n) | seed-anchored (≥ inter − 0.02) |
|---|---|---|---|
| LM | 1.0 [1.0, 1.0] (23) | 1.0 [1.0, 1.0] (23) | True |
| LAD | 1.0 [1.0, 1.0] (23) | 1.0 [1.0, 1.0] (23) | True |
| LCx | 1.0 [1.0, 1.0] (23) | 1.0 [1.0, 1.0] (23) | True |
| RCA | 0.7143 [0.5238, 0.9048] (21) | 0.7143 [0.5238, 0.9048] (21) | True |

Seed edits (report only): reads add 0.0 [0.0, 0.0] of their voxels beyond the seed and remove 0.1714 [0.1586, 0.1841] of the seed; 48 of 48 reads add nothing to it.

**Seed-anchored in LM, LAD, LCx, RCA.** A10 would compare the model with a seed-anchored pair: report the A23 diagnostic first beside A10, and put Round 9 L5 to the lead.

## A31.3 Model-vs-read per source (report only)

| Source | stratum | patients | macro [CI] | LM | LAD | LCx | RCA |
|---|---|---|---|---|---|---|---|
| Figshare-EpicardialFat-CE | primary | 3 | 0.565 [0.4554, 0.6394] | 0.4601 | 0.5676 | 0.55 | 0.6825 |
| Mendeley-SDN-cy54ttk3fj | primary | 4 | 0.5794 [0.4588, 0.7292] | 0.4909 | 0.5756 | 0.6617 | 0.5894 |
| Taiwan-AICUP-CardiacCT | primary | 17 | 0.5756 [0.4642, 0.6788] | 0.6076 | 0.6338 | 0.5437 | 0.5006 |
