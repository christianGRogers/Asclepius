# Round 2, agent "Sweep": Kaggle / HF / GitHub / Zenodo / Figshare / Mendeley / OSF / Dryad / data.world (2026-10-12)

Full fields are in `Sweep.json`. Every source below was opened and a sample was downloaded, checked and deleted, unless marked otherwise. The test folder `round2/tmp_Sweep/` is empty.

## Bottom line

- **New open T1 (ECG-gated CCTA): 44 patients, all from IRCCS SDN Naples on Mendeley Data, CC BY 4.0.** The main one is a 40-patient retrospective-gated Siemens Force CCTA set with diastolic and systolic phases. Four more single-case records add 4 patients.
- **New T2: 100 Taiwanese cardiac CTA patients with an unclear licence** (AI CUP competition data re-hosted on HF/Kaggle). Also 40 post-contrast cardiac CT (Figshare, CC BY), plus a pig 4D contrast cardiac CT set (CC BY, animal).
- **New T3 (>50): 137 aortic CTA from Tongji Hospital** (Mendeley, CC BY 4.0). Plus about 1,100 Basel thorax CT that have been resampled to 1.5–2 mm, which is low value.
- Dead or empty: data.world (site closed), Dryad, OSF and GitHub. Zenodo was swept with about 65 query variants (full-text plus title-restricted, up to 8 pages each) and turned up no new human CCTA.

## Ranked sources

| # | Source | Tier | Scans | Size | Licence | Verified sample |
|---|---|---|---|---|---|---|
| 1 | [Mendeley cy54ttk3fj – SDN "Normal patterns of LV rest myocardial perfusion, 3rd-gen DSCT"](https://data.mendeley.com/datasets/cy54ttk3fj/1) | **T1** | **40 pts** (Diast + Sist = 80 vols) | 9.1 GB | CC BY 4.0 | Force, CCT_Retro_FC, 0.75 mm / 0.26 mm px, Iopamiro, p99.5 ≈ 480 HU |
| 2 | [Mendeley 7x9kb53262 – SDN coronary artery fistula](https://data.mendeley.com/datasets/7x9kb53262/1) | T1 | 1 pt (multi-phase) | 3.0 GB | CC BY 4.0 | Force CCT_Retro, DS_CorCTA 0–95 %, 70 kVp |
| 3 | [Mendeley 37nnfyh3x9 – SDN RCA agenesis](https://data.mendeley.com/datasets/37nnfyh3x9/1) | T1 | 1 pt | 1.3 GB | CC BY 4.0 | GE Revolution, CARDIO RETRO HiRes, 0.625 mm |
| 4 | [Mendeley 4643nn2z44 – SDN coronary AV fistula](https://data.mendeley.com/datasets/4643nn2z44/1) | T1 (likely) | 1 pt (~10 phase series) | 1.1 GB | CC BY 4.0 | Force 0.75 mm; tags de-identified, so gating is inferred |
| 5 | [Mendeley spb25zt2c4 – SDN cardiac paraganglioma](https://data.mendeley.com/datasets/spb25zt2c4/1) | T1 | 1 pt (CT + MR mixed) | 3.8 GB | CC BY 4.0 | Force CCT_Retro, DS_CorCTA BestDiast |
| 6 | [HF benchang1110/cardiac_segmentation](https://huggingface.co/datasets/benchang1110/cardiac_segmentation) (+ PNG copies [Kaggle f74096386/aicup-aortic-valve](https://www.kaggle.com/datasets/f74096386/aicup-aortic-valve), [HF ChiWei085](https://huggingface.co/datasets/ChiWei085/ML2025_HW_Cardiac_Muscle)) | T2 (probably gated) | **100 pts** | 10.6 GB NIfTI | **unclear**: Taiwan AI CUP competition data re-hosted | HU NIfTI 0.42/0.5 mm, vessel pool 330–400 HU, coronaries visible |
| 7 | [Figshare 17039813 – epicardial fat, post-contrast cardiac CT](https://figshare.com/articles/dataset/17039813) | T2 | 40 CE vols (+ NC) | 4.9 GB | CC BY 4.0 | NRRD in HU, heart-cropped, 2.5 mm slices |
| 8 | [Figshare+ 30398977 – pig contrast 4D cardiac CT](https://doi.org/10.25452/figshare.plus.30398977) | T2, **animal** | ~60 contrast scans × 10–11 phases | 154 GB | CC BY 4.0 | Canon, contrast-filled chambers/aorta |
| 9 | Mendeley Tongji aortic-dissection CTA: [2yxbmchmgg](https://data.mendeley.com/datasets/2yxbmchmgg/1), [5b3wx7mkk6](https://data.mendeley.com/datasets/5b3wx7mkk6/1), [4yfcyv5xsk](https://data.mendeley.com/datasets/4yfcyv5xsk/1) | T3 | **137 pts** | 33 GB DICOM | CC BY 4.0 | UIH uCT 780 "Aorta CTA", CE, 1.5 mm |
| 10 | [Zenodo 20272295 – TotalSegmentator pleural/pericardial effusion](https://zenodo.org/records/20272295) | T3 (low) | 600 thorax CT, mixed contrast | 9 GB | CC BY 4.0 | 1.5 mm iso; 1 of 3 sampled contrast |
| 11 | [Zenodo 6384747](https://zenodo.org/records/6384747) + [8328230](https://zenodo.org/records/8328230) – Basel pericardial effusion | T3 (very low) | ~500, 2 mm iso | 4.5 GB | CC BY 4.0 | 2 mm resampled |
| 12 | [Zenodo 22688904 – TotalSegmentator v3](https://zenodo.org/records/22688904) | T3 | 1,939 CT (all regions) | 37 GB | CC BY 4.0 | not sampled (update of the round-1 TS v2 family) |
| 13 | [Zenodo 18256797 ChestPathCT5-S100](https://zenodo.org/records/18256797) | T3 | 20 PE + 67 others | 9.4 GB | CC0 | not sampled (proxy TLS errors) |
| 14 | [Zenodo 7075320 paediatric chest lymphoma](https://zenodo.org/records/7075320) | T3 | 30 | 3.2 GB | CC BY 4.0 | not sampled |
| 15 | [Mendeley vmjfr7jrvy – SDN acute aortic dissection](https://data.mendeley.com/datasets/vmjfr7jrvy/1) | T3 | 1–3 pts | 2.0 GB | CC BY 4.0 | venous-phase thorax CT |
| 16 | [Kaggle abbymorgan/heart-ct (PCIR)](https://www.kaggle.com/datasets/abbymorgan/heart-ct) | T3 | 1 series | 0.06 GB | CC0 | "CTA AORTA", 2.5 mm, 2001 |

Unverified lead: [IEEE DataPort "CCTA Dataset with DSA-based annotation"](https://doi.org/10.21227/8b1q-7q94) is listed Open Access and CC BY (per OpenAlex). It needs a free IEEE login, and the site does not resolve from this sandbox.

## How to download and list cases

- **Mendeley (SDN and Tongji):** `GET https://data.mendeley.com/public-api/datasets/<id>` returns a JSON file list with `download_url`. A `User-Agent` header must be sent; Python's default User-Agent gets a 403. The servers support HTTP Range, so the zip central directories were listed remotely.
  - cy54ttk3fj has 40 patient folders in `Diast.zip` and in `Sist.zip`.
  - In the Tongji zips, each top-level folder is one patient.
- **Hugging Face:** list with `https://huggingface.co/api/datasets/benchang1110/cardiac_segmentation/tree/main/train_image`, download with `.../resolve/main/train_image/patientNNNN.nii.gz`.
- **Figshare:** `https://ndownloader.figshare.com/files/<id>`, with Range support.
  - Pig tars: 66226196, 59113601, 59117399, 66229397, 59124065, 59132822. They are uncompressed, so the 512-byte tar headers can be walked by range to pull one phase.
  - Epicardial zip: 31584917.

## Notes and caveats

- **SDN Naples** is the IRCCS Synlab SDN research hospital, Mendeley owner account "Direzione Scientifica SDN". It shares complete DICOM studies with its case reports in J Cardiovasc Comput Tomogr and similar journals.
  - I screened about 120 of its records. Its other imaging records are PET/MR/oncology.
  - None overlap with the round-1 Mendeley 9wv3fkxstx, which belongs to a different owner (WANG).
- **The AI CUP cohort** is high quality: 0.42 mm in-plane, 0.5 mm slices, and coronaries visible. Its permission to redistribute is doubtful, so the lead should decide; same handling as HeartSR in round 1.
- **The Tongji aortic CTA** is non-gated chest-abdomen-pelvis CTA, so the coronaries are at best partly visible.
- **Excluded items** are listed in the last JSON entry for dedupe. They include:
  - the Moroccan .mrb thorax scans (portal-venous phase)
  - RSNA intracranial-aneurysm derivatives
  - CE-LAA (pathology slides)
  - mesh-only Zenodo heart cohorts
  - MR-PET SDN archives
  - synthetic CONFLUX
  - MedOtter re-hosts of known sets
