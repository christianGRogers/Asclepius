---
tags: [janus-m, experiment, data, pool, seal, D27, D35, A34]
author: Hotel
round: 1
updated: 2026-10-30
issue: christianGRogers/Asclepius#130
---

# After the coronary hold-outs, the pool leaves Janus-M 41 volumes, and none of them is both HU-true and spacing-true at scale

## Question

Janus-M may never read, score or train on a coronary-sealed patient (D27, D32, D33), and Hotel also keeps out the
A34 reserve and every Round 10 D35 draft. Once those patients are removed, what can the project's CCTA pool give a
myocardial-layer model? Layer work needs the whole heart in view, usable contrast, HU-calibrated voxels and true
sub-millimetre spacing.

## Method

`experiments/JanusM/Hotel/pool_census.py` reads only repository files: no CT and no Girder.
- **The QC report:** `vault/Research/Datasets and benchmarks/CCTA sourcing 2026-10/QC volume reports.csv`, with 904 volumes.
- **The pinned D27 seal:** `configs/segqueue14/sealed-pool-2026-10.json`, loaded through `segtrain.pool_seal`, so the hash
  is verified. The seal's `extension_order` is the A34 reserve.
- **The union of all five Round 10 D35 drafts:** Atlas, Bridge, Crucible, Delta and Foxtrot. A33 freezes the union
  until Q1 is answered, so the union is the cautious reading.

Patients are grouped with the ingest code's patient rule (`segtrain.pool_seal.ingest_patient`). A patient is held out if
**any** of its volumes is sealed, reserved or drafted.

The same rule is also a guard, `experiments/JanusM/Hotel/coronary_holdout.py` (`PoolGuard`). Every Hotel script
refuses a held-out volume through it, and so does the fetch script for the lead. It was checked on three names:
- `TotalSegmentator-cardiac__s0655` → coronary seal;
- `Figshare-CardiacCT15__pat1` → reserve;
- `CCA200-HF__CCA_00` → free.

## Result

| Patients (642 in the QC report) | n |
|---|---|
| Coronary seal (D27/D32/D33) | 170 |
| Seal reserve (A34) | 101 |
| In a D35 draft (union) | 60 |
| Free, ImageCHD (congenital; own stratum under D29) | 90 |
| **Free, other** | **221** |

The 221 free patients, by source:

| Source | Free patients |
|---|---|
| TotalSegmentator-cardiac (1.5 mm) | 114 |
| ImageALCAPA (spacing lost) | 30 |
| HOCMvalvesSeg (uint8) | 27 |
| CCA200-HF | 20 |
| PLOS-Peng2016-CCTA-JPEG | 17 |
| Figshare-EpicardialFat-CE | 6 |
| VMR-Coronary | 3 |
| Zenodo-STOPSTORM | 3 |
| Slicer-SampleData | 1 |

Free patients with whole heart in view, good or moderate contrast and in-plane spacing ≤ 0.5 mm: **41**. With good
contrast only, the count is 25. The 41 come from four sources, and their QC notes limit them:

| Source | n | What the QC report says |
|---|---|---|
| CCA200-HF | 20 | Resampled 0.5 mm grids. On several volumes, the header spacing "looks ~2× overstated" (e.g. CCA_00, _05, _08, _12, _13). |
| PLOS-Peng2016-CCTA-JPEG | 14 | "uint8 JPEG-derived (0-255, not HU)". |
| Figshare-EpicardialFat-CE | 6 | Contrast-enhanced cardiac CT. |
| Slicer-SampleData | 1 | Contrast-enhanced cardiac CT. |

None of the 221 free patients has more than one volume. The pool therefore offers Janus-M no systolic/diastolic pair
and no late-phase partner.

The list is `experiments/JanusM/Hotel/janusm_r1_pool_volumes.tsv`, which gives name, CCTA-Pool item id, source,
resolution and contrast. `draw_janusm_seal.py` draws a proposed Janus-M seal from it before any image is opened:
- **Sealed:** 13 patients.
- **Decision set:** 9 patients.
- **Train:** 19 patients.
- **Salt:** `asclepius-janusm-seal-r1:`. The draw is per source; a source with fewer than 3 patients is used for training only.
- **File:** `janusm_seal_proposal_r1.json`.

## What it implies

1. **The pool cannot carry Janus-M.** The coronary hold-outs took almost every well-calibrated, true-resolution
   volume. That is right, and Janus-M must not undo it. What is left is two kinds of volume:
   - spacing-suspect volumes (CCA200-HF). These are useless for thickness in mm until they are re-gridded, the same rule
     D29 applies to the 74 coronary spacing-suspect volumes;
   - non-HU volumes (PLOS). These are usable for borders but not for any HU output.

   In this pool, a myocardial thickness is also a spacing check: an LV wall that measures about 20 mm means a
   header twice too large. Job M0 reports it per volume.
2. **The 41 volumes are a geometry pilot and a small sealed test, not a training set.** Training data must come from
   outside the pool:
   - public TotalSegmentator v1 cardiac CT (CC BY 4.0, 1.5 mm). The project already holds 114 of these patients as free pool volumes;
   - MM-WHS and CARE 2026 whole-heart CT, both gated (D19);
   - a retrospective export from the lead's hospital (the lead's decision).
3. **No scar or perfusion reference can come from the pool.** It has no paired CMR, no late phase and no stress phase.
4. **When A35 releases the reserve patients that are not sealed, Janus-M gains them.** They are the best-calibrated
   pool volumes. The census is re-run then, and nothing is drawn from them before that.
