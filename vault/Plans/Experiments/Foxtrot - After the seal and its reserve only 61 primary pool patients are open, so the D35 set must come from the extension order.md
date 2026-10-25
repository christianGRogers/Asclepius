---
tags: [plans/experiment, round10, D35, D27, D32, A30, seal, pool]
author: Foxtrot
round: 10
updated: 2026-10-25
issue: christianGRogers/Asclepius#113
---

# After the seal and its reserve, only 61 primary pool patients are open, so the D35 set must come from the extension order

**Question.** D35 holds out "about 15 % of the non-sealed, non-ImageCHD pool patients (about 50 of about 347)". The
wave-1 note says 198 patients are open once the seal and its 100-patient extension reserve (D32) are set aside. Which
count is right, which patients can a decision set actually be drawn from, and how does it interact with the seal's
pre-registered extension order (A30)?

**Method.** `experiments/Foxtrot/r10/d35_frame.py` reads only names: the pool list
(`configs/segqueue14/pool-2026-10.txt`, 675 volumes) and the seal file in force
(`configs/segqueue14/sealed-pool-2026-10.json`, D32 pin `e71141b4…`). Patients are the project's real patients
(`segtrain.pool_seal.ingest_patient`, D32/D33). Strata are Bridge's (`experiments/Bridge/r9/seal_pool.py`): primary;
report-only (ImageCHD, ImageALCAPA); excluded (the three suspect-spacing sets). The reserve is the first 100 entries
of the extension order, as the wave-1 tools refuse them (`experiments/Bridge/wave1/common.py`). No image, read or
prediction is opened. Output: `experiments/Foxtrot/r10/results/d35_frame.json`.

## Result

| Stratum | Sealed | Reserved (extension to 200 / 250) | Open | Total |
|---|---|---|---|---|
| Primary | 150 patients (305 volumes) | **100 (144 volumes)** | **61 (69 volumes)** | 311 |
| Report-only (ImageCHD) | 20 | — | 63 | 83 |
| Excluded (suspect spacing) | — | — | 74 | 74 |
| **All** | 170 | 100 | 198 | 468 |

**The two counts reconcile like this:**
- **"About 347"** (Atlas's summary on #43, carried into D35) is 517 − 150 − 20. 517 is the **name-heuristic** patient
  count that D32 retired. That heuristic under-grouped six real patients, so it gives 48 too many. The figure also
  includes the excluded stratum and the reserve.
- **"198 open"** (wave-1 note) is right: 468 real patients − 170 sealed − 100 reserved. But only **61** of them are
  primary. The other 137 are ImageCHD (congenital, its own stratum under D29) or suspect-spacing (outside A10 until
  re-gridded).
- On real patients, the non-sealed, non-ImageCHD count is **235** (161 primary, 74 excluded). The non-sealed
  **primary** count, reserve included, is **161**.

**The open primary patients are mostly one source.**

| Source | Open primary patients |
|---|---|
| Taiwan-AICUP-CardiacCT | 43 |
| Mendeley-SDN-cy54ttk3fj | 8 |
| Figshare-EpicardialFat-CE | 5 |
| VMR-Coronary | 4 |
| Kaggle-CAD-RandomSamples | 1 |
| The other 17 primary sources | **0**: the seal and its round-robin extension order took every one of their patients |

The extension order's two halves are far more even:

| Extension positions | Patients (volumes) | Sources |
|---|---|---|
| 1–50 (the seal grows to 200) | 50 (72) | 10 sources, 4–6 patients each |
| 51–100 (the seal grows to 250) | 50 (72) | 8 sources, 2–9 each: Kaggle-CAD 9, SDN-cy54ttk3fj 9, Taiwan 9, EpicardialFat 8, VMR 8, TotalSegmentator-cardiac 3, CardiacCT15 2, IDC-RIDER 2 |
| 101 | 1 (1) | VMR-Coronary |

## What it means

1. **A D35 set cannot be drawn from the open patients alone.**
   - 15 % of the 61 open primary patients is 9, which is too few to decide anything.
   - "About 50" of them would leave 11 primary patients to train on, 9 of them from Taiwan.
   - And 70 % of any within-source draw from the open 61 is Taiwan.
2. **The patients D35 needs are the seal's reserve.** 100 of the 161 non-sealed primary patients sit in the extension
   order, which the wave-1 tools already refuse to open. So there are two ways to make a decision set:
   - **from the extension order's second half (positions 51–100).** This caps the seal at 200 patients;
   - **from the open 61.** This keeps 250 reachable, but the set is small and mostly Taiwan.

   Every option is a trade between three uses of the same 161 patients: seal size (power of A10), the size of the
   decision set (power of fine-tune decisions), and how much is left for fine-tuning. The power side of the trade is
   in [[Foxtrot - On Janus 0's spread the 150-patient seal passes a human-level model 78 percent of the time, so it should grow to 200 now]]
   and [[Foxtrot - A 50-patient decision set resolves model choices to 0.02-0.05 tF1, but recipe choices stay above 0.04 because seed noise dominates]].
3. **Positions 51–100 are already a valid D35 draw.**
   - The order was ranked by a salted sha256 within source (salt `asclepius-sealed-round9-pool:`, round-robin
     across sources) and rebuilt on real patients on 2026-10-19 (D32).
   - Since then, the tools have refused it. No read of it has been opened.
   - Using it adds no new salt and no new choice, so it cannot be salt-shopped. The list is a deterministic function
     of the pinned seal file: `experiments/Foxtrot/r10/d35_proposal.py` writes it, with hashes, to
     `d35_proposal.json` (50 patients, 72 volumes).
4. **"About 15 %" and "about 50" cannot both hold.** 50 patients is 31 % of the non-sealed primary patients (21 % of
   the non-sealed, non-ImageCHD ones). This is the lead's call. The candidate keeps the count (50) the lead was
   shown.
5. **The training frame for fine-tuning is small.**
   - It holds 61 open primary patients + 1 (extension position 101), 63 ImageCHD, and 74 suspect-spacing patients
     once re-gridded.
   - At two reads each, that is about 140 primary reads and 266 with ImageCHD.
   - If the seal stays at 150, positions 1–50 are released as well (another 50 patients, 72 volumes).
   - Crucible v10's P3 trigger ("≥ 300 open pool reads", from a heuristic count of 315 open patients) is out of
     reach on primary reads under any option.
6. **A gap in the training path (for `role:swe`).** Task 716 (`configs/tasks/Dataset716_CoronaryICX4Wave1.yaml`)
   refuses the 150 + 20 sealed patients through `segtrain.pool_seal`. It does **not** refuse the 100 reserve
   patients, and no D35 guard exists. A wave-1 fine-tune run today would train on patients that the seal may absorb
   and that D35 would decide on.

## Limits

- Names only. Whether every pool volume is annotatable is QC's call. The counts use the pool list in force.
- The suspect-spacing stratum's re-gridding is not scheduled anywhere. Until it is, those 74 patients are neither
  trainable nor scorable.
