---
tags: [janus-m, experiment, data, seal, census, round1]
author: Golf
round: 1
updated: 2026-10-30
issue: christianGRogers/Asclepius#130
code: experiments/JanusM/Golf/census.py, experiments/JanusM/Golf/janusm_seal.py
---

# The coronary seal, D35 draws and reserve leave Janus-M 164 of 675 pool volumes, so its adult data is ImageCAS

## Question

The README says Janus-M never reads, scores or trains on a sealed case or a D35 decision-set patient. Which
SegQueue14 pool volumes are left for Janus-M? Do they include the pool sources that matter for the myocardium:
ImageCHD (myocardium labels), the SDN normal-perfusion cohort (`Mendeley-SDN-cy54ttk3fj`), the epicardial-fat set,
and the TotalSegmentator cardiac cases?

## Method

`census.py` reads only repository files and opens no image. It walks `configs/segqueue14/pool-2026-10.txt` (675
volumes) and drops, in this order:

1. **Sealed:** every volume of a sealed patient, primary or report-only, via `segtrain.pool_seal.load_pool_seal()`
   (sha256-pinned; D27, D32, D33).
2. **D35 draws:** every patient in any of the three Round 10 candidate draws (Delta, Atlas, Bridge). A33 freezes
   their union until the lead answers Q1.
3. **Reserve:** every patient on the seal's `extension_order` (101 entries). A34 keeps the reserve untrained and
   uninspected.

Patients are grouped with `segtrain.pool_seal.ingest_patient`, the rule the guard itself uses.

## Result

**164 volumes from 163 patients are open to Janus-M.**

| Source | Pool volumes | Sealed | D35 draws | Reserve | Janus-M allowed (patients) | Myocardium relevance |
|---|---|---|---|---|---|---|
| ImageCHD | 83 | 20 | 0 | 0 | **63 (63)** | myocardium label 5; congenital, mostly children |
| ImageALCAPA | 30 | 0 | 0 | 0 | 30 (30) | spacing lost (D29 suspect) |
| Taiwan-AICUP-CardiacCT | 100 | 43 | 21 | 11 | 25 (25) | adult CCTA, no myocardium label |
| HOCMvalvesSeg | 24 | 0 | 0 | 0 | 24 (24) | uint8 windowed, not HU |
| CCA200-HF | 20 | 0 | 0 | 0 | 20 (20) | suspect spacing |
| Mendeley-SDN-cy54ttk3fj (normal perfusion) | 80 | 36 | 24 | 18 | **2 (1)** | normal rest-perfusion reference |
| Figshare-EpicardialFat-CE | 34 | 15 | 8 | 11 | **0** | epicardial fat mask |
| TotalSegmentator-cardiac | 16 | 8 | 2 | 6 | **0** | myocardium label |
| every other source (18) | 288 | 203 | 28 | 57 | 0 | |

Full table and the volume list: `experiments/JanusM/Golf/census.json`.

## What it implies

- **The pool cannot carry Janus-M.** The three pool sets with myocardium value have 0, 1 and 0 usable adult
  patients. The two cohorts Janus-M would most want are gone: the 40-patient SDN normal-perfusion cohort ([[#Forte2020]])
  and the epicardial-fat set. The usable remainder is mostly congenital (ImageCHD), suspect-spacing or windowed.
- **ImageCAS is the adult source.** Its 1000 ECG-gated CCTA are not pool volumes, so the pool seal, the reserve and
  D35 cannot touch them. Only the coronary A14 seal applies: 80 ImageCAS-X test cases and 20 quality-0 cases. That
  leaves **900** cases.
- **The TotalSegmentator cardiac cases outside the pool are clean too.** 114 of the 130 in CCTA-Pool are not pool
  volumes (101 of the 116 "gated_like"). Their myocardium labels are CC BY 4.0. E2 uses them.
- **Proposed Janus-M seal, drawn now:** `janusm_seal.py` ranks the 900 allowed ImageCAS cases by
  `sha256('asclepius-janusm-sealed-r1:' + case)`:
  - the first 60 form the **Janus-M seal**;
  - the next 40 form the **Janus-M decision set**;
  - 800 may be trained on.

  The list is in `janusm_seal_proposal.json`. Its overlap with coronary groups that are not sealed is allowed,
  because the coronary model is never scored on it: 3 open-36 cases and 3 dev-44 cases fall in the Janus-M seal.
  The quality-0 cases in it carry a known image-quality stratum, which the plan reports separately.
- **The guard Janus-M uses:** every Janus-M job takes its case list through `segtrain.pool_seal.apply(..., mode="refuse")`
  and `trillium/icx4/lib/sealed.refuse_sealed`. A pool volume therefore needs this census's allowed list, and an
  ImageCAS case must be outside A14. Both guards exist today, so nothing new has to ship for this.

## Reference

- <a id="Forte2020"></a>Forte E, Punzo B, Gentile F, et al. Normal patterns of left ventricle rest myocardial perfusion
  assessed by third-generation cardiac computed tomography. *Clin Physiol Funct Imaging* 2020;40:30-36.
  doi:10.1111/cpf.12598 (data: Mendeley doi:10.17632/cy54ttk3fj.1, CC BY 4.0; ingested by
  `tools/ccta/ingest_open.py sdn-perfusion` as DICOM diastolic + systolic reconstructions).
