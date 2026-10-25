---
tags: [plans/experiment, round-10, D35, D27, D32, A30, pool, seal]
author: Crucible
round: 10
updated: 2026-10-25
issue: christianGRogers/Asclepius#113
---

# The open pool after the seal and its reserve is 61 patients from 5 sources, so D35 must be drawn across the reserve

**Question.** D35 holds out "about 15 % of the non-sealed, non-ImageCHD pool patients (about 50 of about 347)".
The wave-1 note says 198 patients are open once the seal and its 100-patient extension reserve are set aside.
Which count is right? Where can a decision set come from? And when do its reads arrive in the D23 serve order?

**Method.**
- `experiments/Crucible/r10/r10_power.py` (`census`) and `r10_d35_draw.py`. CPU only.
- Inputs: `configs/segqueue14/pool-2026-10.txt` (D23 serve order) and the pinned seal (sha256 `e71141b4…0690`).
- Patients are grouped by the project's guard (`segtrain.pool_seal.ingest_patient`, D32/D33). Strata follow
  `experiments/Bridge/r9/reseal_d32.py`.
- No image or read is opened.

## 1. The counts

| Stratum | Sealed | Reserve (first 100 of the extension order) | Open | Total |
|---|---|---|---|---|
| Primary | 150 patients (305 volumes) | 100 (144) | **61 (69)** | 311 |
| Report-only (ImageCHD) | 20 (20) | — | 63 (63) | 83 |
| Spacing-suspect (ImageALCAPA, HOCMvalvesSeg, CCA200-HF) | — | — | 74 (74) | 74 |
| **All** | 170 | 100 | 198 | 468 patients / 675 volumes |

**Reconciliation.**
- **"About 347" is stale.** It is 517 name-heuristic patients (before D32) − 150 − 20 sealed. On real patients
  the pool has 468.
- **Non-sealed, non-ImageCHD: 235 patients.** That is 161 primary (100 of them reserved) + 74 spacing-suspect.
  15 % of 235 is **35**.
- **"198 open" is correct, but it is not a primary-stratum number.** It is 61 primary + 63 ImageCHD + 74
  spacing-suspect.
- **The primary stratum open today is 61 patients.** A 50-patient decision set drawn from the open patients would
  leave 11 primary patients to train on.

## 2. The open 61 come from 5 of the 10 sources that have non-sealed patients

| Source | Sealed | Reserve | Open |
|---|---|---|---|
| Taiwan-AICUP-CardiacCT | 43 | 14 | 43 |
| Mendeley-SDN-cy54ttk3fj | 18 | 14 | 8 |
| Figshare-EpicardialFat-CE | 15 | 14 | 5 |
| VMR-Coronary | 13 | 13 | 4 |
| Kaggle-CAD-RandomSamples | 13 | 14 | 1 |
| Figshare-CardiacCT15, IDC-rider, Kaggle-HeartSR, SLAWT2016, TotalSegmentator-cardiac | 7 / 7 / 5 / 5 / 8 | 8 / 6 / 5 / 4 / 8 | **0** |
| 12 single-patient or all-sealed sources | 21 | 0 | 0 |

The extension order fills each source's non-sealed patients first, so in five sources **every** non-sealed
patient is reserved.

Two consequences:
- A decision set drawn only from the open 61 would be 70 % Taiwan AI CUP and would cover 5 sources.
- Until the reserve is released, a fine-tune sees pool reads from those same 5 sources only.

The reserve exists for one purpose: so that a seal extension (A31.1) adds uninspected patients. Here it also
decides which domains the first fine-tune can see.

## 3. A draw across the reserve (Crucible v11's proposal)

`r10_d35_draw.py` → `experiments/Crucible/r10/d35_proposal.json`:

| | Value |
|---|---|
| Population | 161 non-sealed primary-stratum patients, reserve included |
| Salt | `asclepius-d35-round10:` (rank = sha256(salt + patient id), ascending, within source) |
| Size | 35 patients, 47 volumes |
| Allocation | Proportional (largest remainder); ≥ 1 from every source with ≥ 5 eligible patients (the seal's rule). Taiwan 12, cy54ttk3fj 5, EpicardialFat 4, VMR 4, Kaggle-CAD 3, CardiacCT15 2, TotalSegmentator 2, IDC-rider 1, HeartSR 1, SLAWT 1 |
| Drawn from the reserve | 23 of 35 |
| Extension order after skipping D35 | 78 patients, so the seal can grow to **227** (not 250) |
| Trainable primary patients before the reserve is released | 49, in 5 sources |
| Trainable primary patients if the unused reserve is released | up to 126, in 10 sources |

## 4. When the reads arrive (D23 order, which D30 leaves unchanged)

The serve order is QC section, then source, alphabetically. The table counts the reads (2 per volume, sealed
volumes included, because annotators read them too) until the n-th patient's scoring volume has both reads:

| Group | n = 10 | n = 20 | n = 25 | n = 30 | All |
|---|---|---|---|---|---|
| D35 (35 patients) | 238 | 436 | 478 | 688 | 1186 (TotalSegmentator-cardiac is served last) |
| Trainable, reserve released (126) | — | — | 192 | 466 (n = 75) | 1202 |

The pool holds 1350 reads in all. So **25 D35 patients are double-read after about 480 reads (35 % of the
queue)**. If D35's 47 volumes were served first, they would be complete after 94 reads. That changes D23's order,
so it is the lead's call.

## What it changes

- D35's own fraction (15 %), applied to the real base (235), gives **35 patients**. Drawing them from the primary
  stratum keeps the set scorable: a mm-based tF1 on a suspect grid decides nothing, which is why D29 keeps those
  sources out of A10 too.
- **D35 has to be drawn across the reserve, and the reserve must be resolved early.** Otherwise the decision set is
  unrepresentative, and the first fine-tune sees 5 sources.
- The extension order skips D35 patients, as D32 skipped already-sealed patients. **The seal file does not
  change.** The skip applies at extension time and is pre-registered here.
- Task 716 as on `dev` refuses only the seal. It would train on D35 and reserve patients, and `segtrain index`
  would hold out another 30 % on its own hash. Filed as #116.

## Limits

- The serve-order timeline assumes reads complete roughly in list order. With many annotators, a few cases run in
  parallel.
- Patient grouping is the guard's (D32/D33). Sources without patient ids rest on their dataset descriptions.
