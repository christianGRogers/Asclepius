---
tags: [plans/experiment, round10, D35, D27, D32, A30, pool, decision-set]
author: Delta
round: 10
updated: 2026-10-25
issue: christianGRogers/Asclepius#113
---

# After the seal and its reserve, only 61 primary pool patients are free, and 43 of them come from one source. A decision set with the seal's source mix must therefore come from the reserve

**Question.** D35 asks for a decision set of "about 15 % of the non-sealed, non-ImageCHD pool patients (about 50 of about 347)". The wave-1 note says 198 open patients. Which count is right? What can the set be drawn from? And how does it interact with A30's extension order?

**Method.**
- `experiments/Delta/r10/pool_census.py` counts real patients (`segtrain.pool_seal.ingest_patient`, D32/D33) by stratum (Bridge's rule), seal state and extension rank, per source.
- It reads only the pool list and the seal file (sha256 checked on load). No image or read is opened.
- `d35_draw.py` then draws a proposed set. Outputs: `pool_census.json` and `d35_decision_set_proposal.json`.

## Result 1: the counts reconcile

| Count | Value | Where it comes from |
|---|---|---|
| Name-rule keys − sealed keys | 517 − 170 = **347** | Atlas on #43 and D35. These are pre-D32 name-heuristic keys, not patients |
| Real patients in the pool | **468** | 311 primary, 83 ImageCHD (report-only), 74 spacing-suspect (CCA200-HF 20, HOCMvalvesSeg 24, ImageALCAPA 30) |
| Non-sealed, non-ImageCHD real patients | **235** | 161 primary + 74 spacing-suspect |
| Non-sealed, non-reserved, all strata | **198** | the wave-1 note: 61 primary + 63 ImageCHD + 74 spacing-suspect |

The primary stratum (A10's population) splits as follows:

| Primary | Patients |
|---|---|
| Sealed (D32) | 150 |
| Reserve, extension ranks 1–50 (the step to 200) | 50 |
| Reserve, ranks 51–100 (the step to 250) | 50 |
| Free | **61**: Taiwan AI CUP 43, Mendeley-SDN-cy54ttk3fj 8, EpicardialFat 5, VMR 4, Kaggle-CAD 1 |

So D35's "15 % of about 347 = about 50" rests on a stale count. 15 % of the real 235 is **35**.

The spacing-suspect 74 cannot be decision patients, because tF1's 1.5 mm tolerance is in mm and their spacing is wrong. The primary non-sealed 161 is therefore the frame. That is the same frame #114 and #116 use.

## Result 2: the free patients cannot be the decision set alone

- A within-source 15 % draw from the 61 free patients gives about **9 patients**.
- 70 % of the free patients are one source. 17 of the 22 primary sources have no free patient at all: seal plus reserve take about 80 % of every small source, because the extension order is round-robin by source.
- A decision set drawn there would share its source mix with the training patients (also mostly Taiwan) and not with the seal. A fine-tune that overfits Taiwan would win on it and lose at acceptance.

## Result 3: a proposed draw (`d35_draw.py`)

**The rule:**
- Eligible: the 161 non-sealed primary patients.
- N = 35.
- Allocation by source is proportional to the **primary pool**, which is the seal's own population. It uses the largest remainder, is capped by availability, and gives at least one patient to any source with 5 or more.
- Within each source, patients are ranked by `sha256('asclepius-decision-round10-pool:' + patient)`.

**The draw:**
- 35 patients, 51 volumes; `scoring_volume` as the seal's rule.
- File sha256 `1a75fe41…66b1`.
- Taiwan 11, SDN-cy54 5, EpicardialFat 4, VMR 4, Kaggle-CAD 3, CardiacCT15 2, RIDER 2, TotalSegmentator-cardiac 2, HeartSR 1, SLAWT 1.
- The draw takes 12 free patients, 11 reserve-200 patients and 12 reserve-250 patients.

**Interaction with A30.** The extension order is kept and **skips D35 patients**, as D32 skipped already-sealed ones. This leaves 78 extension entries, so the seal can still grow to **228**, not 250. Every remaining reserve patient stays untrained and uninspected until the seal size is fixed (#114).

**Trainable primary patients:**
- 49 now (the free 61 minus 12);
- 49 + 78 = 127 if the seal stays at 150;
- 49 + 28 = 77 if it grows to 200;
- 49 if it grows to 228.

## What it changes

- D35's size is **35, not 50**. This is the same percentage on the right count. Decision-set power saturates at seed noise well before 50 (the companion note).
- The decision set must come from the reserve if it is to look like the seal, and then the seal's ceiling is 228, not 250. D27 says "extendable to 200–250", so **a 228 ceiling is a question for the lead**. The alternative keeps 250 and draws only from the free 61, which gives a Taiwan-heavy set of about 9–12 patients.
- The pool is too small to serve acceptance (150–228), decisions (35) and training at once. Every patient the seal grows by is a training patient lost from the 17 primary sources that have no free patient.

## Limits

- Names only. Patient grouping is the project's guard (`ingest_patient`). No read exists yet, so nothing here depends on reads.
- Crucible's proposal (#116) uses the same frame and size with a different salt. The two draws differ only in the salt and the allocation base. The judge picks one.
