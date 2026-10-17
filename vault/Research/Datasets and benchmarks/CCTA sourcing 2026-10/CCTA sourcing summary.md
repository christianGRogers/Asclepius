---
aliases: [CCTA sourcing summary, More CCTA]
tags: [research, dataset, ccta, sourcing]
status: living
updated: 2026-10-12
---

# CCTA sourcing summary (2026-10-12)

Six agents searched for CT scans of the coronary arteries beyond ImageCAS (D17: unlabelled scans
count; keep annotators busy). Their raw catalogues (132 entries, every claim marked verified or not)
are in `agent reports/`. Tiers: **T1** ECG-gated CCTA, **T2** other contrast cardiac CT, **T3**
non-gated contrast chest/aortic CT.

**Bottom line.** Nothing public is anywhere near ImageCAS's size. About **270 new contrast cardiac
scans** can be downloaded today without signing anything; about **1,000–2,000 more** sit behind one
email or one signature; the largest realistic source is a retrospective export from the project
lead's own hospital (LHSC / St Joseph's, via the Western/Lawson REB).

## 1. Open download now (being ingested into Girder `CCTA-Pool`)

| Source | Tier | Scans | Licence | Notes |
|---|---|---|---|---|
| ImageCHD (Kaggle, Guangdong) | T2 | 110 | CC BY-NC 4.0 | congenital, mostly children; NIfTI = HU+1024, spacing in bundled xlsx (strip birth/scan dates) |
| ImageALCAPA (Kaggle, Guangdong) | T2 | 30 | CC BY-NC 4.0 | anomalous coronary origin; has LCA/RCA labels; spacing lost in header |
| HOCMvalvesSeg (Kaggle, Guangdong) | T2 | 27 | CC BY-NC 4.0 | uint8 windowed, not HU (lossy) |
| "Coronary Artery Diseases Random Samples" (Kaggle younesselbrag) | T1 | 28 | stated CC0, **provenance unverified** | Philips iCT 256 CCTA, 0.9 mm |
| Vascular Model Repository (vascularmodel.com) | T1/T2 | 31 coronary (+40 aorta, +30 pulmonary) | research use with attribution | `.vti`, spacing in cm |
| IDC / TCIA incidental cardiac CT | T1/T2 | 17 patients, 24 series | CC BY 3.0/4.0 | RIDER Lung PET-CT (GE gated, multi-phase), NSCLC Radiogenomics ×2, VAREPOP-APOLLO TAVR ×1 |
| Figshare "cardiac ct data_15sets" | T2 | 15 | CC BY 4.0 | cropped, normalised (not HU) |
| Mendeley 9wv3fkxstx; OsiriX demo | T1 | 2 | CC BY / demo | single cases |

Guangdong sets come from ImageCAS's hospital: different cohorts, but patient overlap cannot be ruled
out. CHD68 is a subset of ImageCHD (not counted).

**Held for the project lead:** HeartSR (Kaggle victorsix, 10 Italian 0.6 mm CCTA, *no licence
stated*). **Not used:** Kaggle copies of ASOCA / CAT08 / MM-WHS (unauthorised redistribution; get
them officially below).

## 2. One email or signature away (ranked by new scans per effort)

| Source | Tier | Scans | What the project lead does |
|---|---|---|---|
| Multicenter CCTA report benchmark (arXiv 2609.00909) | T1 | 818 patients / 3,021 series, 4 Chinese hospitals | email [contact removed] |
| Coronary Atlas (UNSW / Auckland) | T1 | "hundreds" (>500 per press; ASOCA is a subset) | email [contact removed] with ethics approval |
| CARE 2026 LA (300) + Whole Heart (144) | T2 | 444 | email [contact removed]; licence is CC BY-NC-**ND**, ask for an exception to share labels |
| MultiD4CAD (Sci Data 2025, Palermo) | T1 | 118 | sign the DUA on Zenodo 15148653 (~2 working days) |
| MIDRC | T1/T2 (+T3) | ~78 CCTA + ~97 cardiac (+~6,400 CTPA) | free login + click-through DUA; **each annotator must register** |
| orCaScore | T1 | 72 | email [contact removed] (registration closed Aug 2025) |
| ICADD (India) | T1 | 70 (with invasive FFR) | email [contact removed] (may need contract/fee) |
| MM-WHS | T2 | 60 | sign the agreement, download from MEGA (no redistribution) |
| ASOCA | T1 | 40 (+20 test) | register at UK Data Service 855916, email [contact removed] |
| Rotterdam CAT08 + 2012 stenosis | T1 | 80 | email Erasmus MC (Theo van Walsum); site is gone |

## 3. Long-term, large

- **Own institution (LHSC / St Joseph's via Western/Lawson REB):** likely thousands of CCTA, ~2–4
  months for a retrospective export. Recommended. (Unverified estimate.)
- **SCAPIS (Sweden, ~25,000 CCTA):** only through a Swedish PI; ethics, ~51,000 SEK, labels returned.
- SCOT-HEART, CONFIRM, ISCHEMIA, PROMISE: collaboration only (BioLINCC has tabular data only).

## 4. T3 (lower value: non-gated chest/aortic CTA)

RSNA PE (12k CTPA, 534 GB, no redistribution), INSPECT (20k CTPA, Stanford DUA), IDC contrast chest
CT (~300 patients CTPA/aortic), 3C COVID cardiac CT (134), ImageTAAD (120), ImageTBAD (100), AVT (56).
Not ingested unless the project lead asks.

## 5. Dead ends and duplicates

No CCTA in: Stanford AIMI catalogue (COCA is non-contrast), CT-RATE, Merlin, UK Biobank (MRI),
MESA/Framingham (calcium), Korean AI-Hub (nationals only; no coronary CT), J-MID (Japanese members),
Chinese platforms (ScienceDB, Tianchi, AI Studio, Gitee, CNGBdb), PhysioNet, OSF, Dataverse, Academic
Torrents, Synapse, TCIA beyond 3 patients, MICCAI/ISBI 2023–2026. 2D-only: Dryad/Kaggle 206-patient
overlays, Ohio State mosaics. ImageCAS duplicates (labels only): ImageCAS-X, Awakening ImageCAS
(ostia + centrelines — useful for 14-class work), DTU STACOM LAA labels, Bi-Atrial models, HF
AI-CVM/Cardiac-CT, several Kaggle splits.
