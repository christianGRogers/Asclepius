---
tags: [plans/experiment, round10, D35, D27, D32, seal, decision-set, pool]
author: Atlas
round: 10
updated: 2026-10-25
issue: christianGRogers/Asclepius#113
code: experiments/Atlas/r10_decision_set.py
---

# On real patients, 61 primary pool patients sit outside the seal and its reserve, so the D35 decision set is 35 of them, in two tranches

**Question.** D35 holds out "about 15 % of the non-sealed, non-ImageCHD pool patients (about 50 of about 347)" as the
wave-1 decision set. The wave-1 note says 198 open patients once the seal and its 100-patient extension reserve are
set aside. Which count is right? What can the decision set be drawn from without touching D27's seal or its
200–250 extension? And what does the draw look like?

**Method.**
- `experiments/Atlas/r10_decision_set.py` (CPU; no image or read is opened, and none exists for the draw to see).
- Every volume of `configs/segqueue14/pool-2026-10.txt` is grouped into its real patient by the project's rule
  (`segtrain.pool_seal.ingest_patient`, D32/D33). The seal is loaded through the guard, which checks its pinned
  sha256 `e71141b4…0690`.
- Each patient goes into exactly one bucket. The script asserts that the guard refuses every volume of a sealed
  patient and none of an open one.
- Output: `experiments/Atlas/r10/decision_set_proposal.json`, sha256
  `bc47690cc1b0acb50037f19ea05ae0619444c1ed1396be592082371b022b6042`.

## 1. The accounting (468 real patients, 675 volumes)

| Bucket | Patients | Volumes | Note |
|---|---|---|---|
| Sealed, primary (D27/D32) | 150 | 305 | the A10 set |
| Sealed, report-only ImageCHD | 20 | 20 | D29 stratum |
| **Reserve**: extension order entries 1–100 | 100 | 144 | the seal grows into these at 200 (1–50) and 250 (51–100). Their reads stay uninspected and untrained until A31.1 decides the size |
| Extension order entry 101 | 1 | 1 | VMR-Coronary |
| Open primary (in none of the above) | 60 | 68 | |
| ImageCHD, not sealed | 63 | 63 | report-only stratum (D29) |
| Spacing-suspect (ImageALCAPA 30, HOCMvalvesSeg 24, CCA200-HF 20) | 74 | 74 | out of A10 until re-gridded (D29) |

**Reconciling the two counts.**
- **"About 347" (Atlas on #43) was wrong twice.** It was 517 − 170 on the pre-D32 name heuristic (517 "patients",
  now 468 real ones), and it **included** the 63 open ImageCHD patients. The error is Atlas's.
- On real patients:
  - non-sealed: 298;
  - non-sealed and non-ImageCHD: **235** (161 primary + 74 spacing-suspect). 15 % of that is **35.2**.
- **The wave-1 note's 198** is right, and it is a different quantity: the patients wave-1 analysis may open now.
  198 = 61 primary (60 open + entry 101) + 63 ImageCHD + 74 spacing-suspect.
- **What a decision set can be drawn from is the 61.**
  - It should be primary-stratum only, because it decides what is best for the population A10 scores.
  - It must not touch the seal (D27).
  - It must not touch the reserve. A reserve patient whose reads had decided a recipe could not later be sealed,
    so the extension to 250 that D27 allows would become impossible.
  - The spacing-suspect sets are out because tF1's 1.5 mm tolerance is in mm.

## 2. The 61 eligible patients are mostly one source

The seal is proportional by source, and its extension order is round-robin across sources (the first 50 take 4–6
from each of ten sources). Between them they exhaust every small source. What is left:

| Source | Primary patients (all) | Sealed | Reserve | Eligible |
|---|---|---|---|---|
| Taiwan-AICUP-CardiacCT | 100 | 43 | 14 | **43** |
| Mendeley-SDN-cy54ttk3fj | 40 | 18 | 14 | 8 |
| Figshare-EpicardialFat-CE | 34 | 15 | 14 | 5 |
| VMR-Coronary | 30 | 13 | 13 | 3 + 1 (entry 101) |
| Kaggle-CAD-RandomSamples | 28 | 13 | 14 | 1 |
| 17 other sources | 79 | 48 | 31 | 0 |

So 70 % of the eligible patients are Taiwan AI CUP, against 32 % of the primary stratum and 29 % of the seal.

## 3. The draw (proposed)

- **Size: 35 patients** (42 volumes). That is D35's own "about 15 %" of the 235 non-sealed, non-ImageCHD patients.
  The "about 50" rested on the miscount above.
- **Salt** `asclepius-decision-round10-pool:`. Within a source, patients are ranked by sha256(salt + patient), the
  same construction as the seal's.
- **Allocation.** Each source gets its share of the **whole primary stratum**, capped at what it has eligible
  (water-filling, then largest remainder). This brings the decision set as close to the seal's mix as the 61 allow:
  - Taiwan 18 of 43, Mendeley-SDN-cy54ttk3fj 7 of 8, EpicardialFat 5 of 5, VMR 4 of 4, Kaggle 1 of 1;
  - Taiwan's share is 51 %. Proportional-to-eligible would have made it 71 %.
- **Patient level.** Every volume of a drawn patient is in the decision set. A patient's score is the mean over its
  volumes and its two reads, as in the wave-1 report.
- **Trainable before the extension decision:** the other 26 eligible patients (25 of them Taiwan), plus the 63
  ImageCHD patients. The 74 spacing-suspect patients are trainable only once re-gridded.
- **Second tranche, pre-registered now.** A31.1 ends the seal at 150, 200 or 250 patients. What it releases is the
  back of the reserve: all 100 at 150, entries 51–100 at 200, none at 250. Released patients join the decision set
  one at a time until it holds 50. Each step takes the source furthest below its primary-stratum share, then the
  lowest salted rank. The rest of the released reserve becomes trainable. The lists are in the JSON:

  | Seal ends at | Released | Join the decision set (15) |
  |---|---|---|
  | 150 | 100 | Kaggle-CAD 4, TotalSegmentator 3, Figshare-CardiacCT15 2, IDC-RIDER 2, Kaggle-HeartSR 2, SLAWT 1, VMR 1 |
  | 200 | 50 | Kaggle-CAD 5, TotalSegmentator 3, Figshare-CardiacCT15 2, IDC-RIDER 2, VMR 2, EpicardialFat 1 |
  | 250 | 0 | none: the decision set stays at 35 |

  A reserve patient's reads are not looked at before release (the reserve rule), so the second tranche is as clean
  as the first.

## 4. When its reads exist (the serve order is fixed, D30)

The pool list is in serve order. For each decision-set patient, the position of its first volume in the 675-volume
queue:

- 20 of 35 by position 196, 27 by 277, 30 by 565, 35 by 600;
- the last 8 are QC-"limited" Taiwan volumes near the end of the queue.

The 26 trainable patients are all served by position 222 (one at 500). The first 300 queue positions also hold 94
reserve volumes. So by about position 300 (≈ 45 % of the queue), there are:

- about 52 open primary patients with reads: what A31.1's measurement uses (D35's 27 + 25 trainable);
- most of the reserve's reads, ready to be released as training data once the extension is decided.

## What it changes

- D35's count becomes **35**, not "about 50". This is the size Round 10 sets: 15 % as D35 says, on real patients. If
  the seal stops below 250, a pre-registered second tranche takes it to 50.
- **The decision set is Taiwan-heavy until the second tranche.** Every decision on it reports Taiwan and non-Taiwan
  beside the pooled number. Per-source decisions are impossible on it (A31.3 stays report-only).
- **The freeze and its guard are code that must ship** (`role:swe`). The proposal file is copied byte for byte to
  `configs/segqueue14/decision-set-2026-10.json`, sha256-pinned. Training refuses any volume of a decision-set
  patient, as it refuses the seal. A refusal of **reserve** patients is also needed, for as long as the extension is
  undecided: task 716's guard refuses the seal but not the reserve today.
- **Limit.** The patient grouping is the project's (`ingest_patient`) and inherits D32's QC. No read was used, so the
  draw cannot have been steered by results.
