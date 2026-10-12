# Round 2: institutional and national research-data repositories (agent "Institutional", 2026-10-12)

Scope: university and national data repositories (Zenodo, figshare and its institutional instances, Dataverse instances, 4TU, DANS, Edmond, ETH, UK, Australian and Japanese repositories, Mendeley Data). I also searched for data deposits behind cardiac CT papers in biomechanics, CFD, TAVI and LAA work. Every source listed as open was tested by download unless marked otherwise, and all test files were deleted afterwards. The machine-readable list is `Institutional.json`. Case IDs for the TotalSegmentator subset are in `Institutional_TotalSegmentator_cardiac_ids.csv`.

## Bottom line

Institutional repositories add **about 45 new human contrast cardiac CTs at native resolution**, all open with no sign-up:

- 40 post-contrast cardiac CTs from Thailand (2.5 mm slices).
- 2 true CCTA volumes (0.42 × 0.625 mm).
- 1 CCTA from an atrial fibre-mapping study (0.4 × 0.625 mm).
- 3 low-quality contrast cardiac CTs from STOPSTORM.

The largest open pool is the **TotalSegmentator v2 cardiac-protocol subset: 127 contrast cardiac CTs, but resampled to 1.5 mm**. The Catalogues and Corpora agents found this independently, so count it once.

There is also a large **porcine** contrast cardiac CT set (60 pig-sessions, 154 GB) if animal data is acceptable.

Almost every 2023–2026 biomechanics, CFD, TAVI or LAAO paper deposit I found on Zenodo is **restricted** (most of them from Centro Cardiologico Monzino, Milan) or holds meshes only.

## Ranked open sources (new this round)

| # | Source | Tier | New scans | Size | Licence | Tested |
|---|---|---|---|---|---|---|
| 1 | [TotalSegmentator v2, cardiac-protocol subset](https://zenodo.org/records/10047292) (Basel) | T2, 1.5 mm isotropic | 127 (+14 T3 CTA thorax) | about 1.2 GB of members, in a 23.6 GB zip | CC BY 4.0 | yes, 6 cases |
| 2 | [Epicardial fat CT, Siriapisith et al.](https://figshare.com/articles/dataset/_/17039813) (Mahidol/Siriraj) | T2 (gating not verified) | 40 post-contrast | 4.95 GB zip | CC BY 4.0 | yes |
| 3 | [figshare 23057000 "Test Data.rar"](https://figshare.com/articles/dataset/Test_Data_rar/23057000) | T1 | 2 CCTA | 0.11 GB | CC BY 4.0 | yes |
| 4 | [Atrial fibre-mapping CT, Zenodo 21855641](https://zenodo.org/records/21855641) | T1/T2 | 1 | 85 MB member | CC BY 4.0 | yes |
| 5 | [STOPSTORM contouring benchmark, Zenodo 22127731](https://zenodo.org/records/22127731) | T2 (resampled, low quality) | 3 | 0.17 GB | CC BY 4.0 | yes |
| 6 | [Pig contrast/non-contrast cardiac CT, Figshare+ 30398977](https://plus.figshare.com/articles/dataset/_/30398977) | T2, animal | 60 pig-sessions, multi-phase | 154 GB | CC BY 4.0 | yes, 1 phase |
| 7 | [ChestPathCT5-S100 PE subset, Zenodo 18256797](https://zenodo.org/records/18256797) | T3 | 20 CTPA | 1.36 GB | CC0 | zip listing only |
| 8 | [PCIR "CTA AORTA", Zenodo 18225140](https://zenodo.org/records/18225140) | T3 | 1 | 25 MB | CC0 | yes |
| – | FUMPE ([figshare Patient01–35](https://figshare.com/articles/dataset/Patient01/6265292)) | T3 | 35 (already a round-1 mention) | 1.6 GB | CC BY 4.0 | metadata only |

### 1. TotalSegmentator v2 cardiac-protocol subset

Round 1 listed TotalSegmentator only as T3. Its `meta.csv`, which I pulled out of the zip by HTTP range read, gives these cardiac study types:

| Study type | Scans |
|---|---|
| `ct heart-thorakale aorta` | 46 |
| `ct aortic valve` (TAVI planning) | 34 |
| `ct heart` | 34 |
| `ct left artrium` | 13 |
| `ct angiography thorax` (T3) | 14 |

The 3 `ct coronary arteries` cases are calcium-score scans; I checked s0085 and it is non-contrast.

Blood pool in the sampled cases:

| Case | Study type | Blood pool (HU) |
|---|---|---|
| s0738 | heart | about 470–525 |
| s0270 | heart | about 325 |
| s0671 | left atrium | median 334 |
| s0189 | aortic valve | median 238 |
| s0230 | heart-thorakale aorta | median 234 |

What to know before using it:
- **Every volume is resampled to 1.5 mm isotropic**, so the coronaries show only coarsely.
- Some headers have non-orthonormal direction cosines. SimpleITK refuses those files; nibabel reads them.
- **Fetching:** range-read single members from `https://zenodo.org/api/records/10047292/files/Totalsegmentator_dataset_v201.zip/content`. Each case is at `sXXXX/ct.nii.gz`, and the case IDs are in the CSV.
- The Corpora agent also reports a per-case Hugging Face mirror.

### 2. Epicardial fat CT (Thailand)

- **Contents:** 40 post-contrast cardiac CTs as HU-calibrated int32 NRRD, 512×512×64 at 0.40×0.40×2.5 mm, with epicardial-fat masks. The same zip also holds about 56 non-contrast scans.
- **Check:** in CE001 the blood-pool mode is 450–475 HU.
- **Download:** `https://ndownloader.figshare.com/files/31584917` (supports Range).
- **Members:** `dataset/Epicardial_{train,test}_CE/CE0NN_CE.nrrd`.
- **Limits:** 2.5 mm slices; ECG gating is not stated.

### 3. Two CCTA volumes (figshare 23057000, uploader Pengling Ren)

- **Contents:** PA0 and PA1, NIfTI 512×512×256 at 0.42–0.43 mm in-plane with 0.625 mm slices. Blood pool is about 450 and 425 HU.
- **Download:** `https://ndownloader.figshare.com/files/40794539` (RAR; extract with `bsdtar`). File 40795820 is a duplicate upload.
- **Provenance:** none stated. It is not ImageCAS: ImageCAS slice spacing is 0.25–0.45 mm.

### 4. Atrial fibre-mapping study (Zenodo 21855641)

- **Contents:** only one of the 6 patients (Zvag) includes the CT: `Zvag/CT_Volume.nrrd`, 0.396×0.396×0.625 mm, blood pool about 460 HU.
- **Download:** `https://zenodo.org/api/records/21855641/files/Zvag.zip/content`.
- The other patients ship segmentations and meshes only.

### 5. STOPSTORM contouring benchmark (Zenodo 22127731)

- **Contents:** 3 VT-radioablation cases. Each has a contrast cardiac CT deformed onto the planning-CT grid (0.94–1.56 mm in-plane, 1.5–2 mm slices).
- **Check:** blood-pool medians are 301, 263 and 207 HU.
- **Value:** low.

### 6. Pig cardiac CT (Figshare+ 30398977, Norway)

- **Contents:** 10 pigs scanned over 6 rounds, with contrast and non-contrast series, multi-phase NIfTI.
- **Format:** six 22–35 GB tar files with no index, so you have to stream them. In Round-1 the first contrast phase starts about 1.2 GB into the tar.
- **Check:** the tested phase shows contrast (median 386 HU in the 150–1000 HU window). The value range (-3897 to 21945) is unusual, so I have not fully confirmed HU calibration.
- **Use:** only if porcine data is acceptable.

## Searched with no open contrast cardiac CT found

**DataCite API**, about 40 queries covering every DataCite repository: CCTA, cardiac/coronary CT, CTA, TAVI/TAVR, LAA/LAAO, FFR-CT, CFD, 3D printing, aortic root/valve, epicardial, mitral, pulmonary vein, photon-counting, dual-energy, congenital, dissection, PE. I also filtered by DOI prefix for 4TU, DANS, Edmond, RADAR, ETH, Leeds, Oxford, Edinburgh, Bristol, Imperial, UCL, Cambridge, Sydney, Monash, Melbourne, Auckland, UNSW, KU Leuven, DataverseNL, Sheffield, Heidelberg and others.

**Repository APIs:**
- Zenodo search API (about 30 queries).
- figshare search API across all institutional instances (16 queries).
- Dataverse search on Harvard, Borealis, Edmond, DANS Life Sciences, DataverseNO and Recherche Data Gouv. DataverseNL returned HTTP 500 and SciELO Data returned 403, so I relied on DataCite for those two.
- Mendeley Data, via DataCite prefix 10.17632.
- OpenAIRE Graph API, including Portuguese and Spanish terms.
- CiNii Research (Japan).

The 4TU search endpoint ignores its query, so DataCite covered 4TU. SimTK search renders in JavaScript and returned nothing usable.

**Restricted** (Zenodo `access_right=restricted`, no files):
- Monzino-style "Dataset related to the article …" records, 20+ of them. These cover pre-TAVI CTA, LAA thrombus, TAVI root DL, landing zone, BAV TAVI, PPVI, ATAA, TEVAR CFD, Marfan PVAT, CABG CCTA, RVOT 4D-CT, photon-counting aorta and the PNRR HURRICANE FTGM data.
- FairPE.
- PE digital-subtraction CTPA.
- Dan-R.
- AAOCA segmentation (Zenodo 14808413).
- ASOCA Zenodo 4531428, already known.

**Meshes or STL only:**
- Zenodo 19351401: 50 four-chamber heart models.
- Zenodo 14504006: 10 LA models.
- KCL figshare 16473780: 3 LA meshes from CCTA.
- Charité figshare 28846238 and 19328687.
- Zenodo 16601454.

**Not CT volumes:**
- figshare 30688691: CCTA-XCA pickles, about 98.5% compressible, consistent with masks.
- Zenodo 19219901: fluoroscopy frames.
- Zenodo 22842865: markups only.

**Duplicates:**
- Borealis K1INBL is the same as Dryad 3863028 (Baskaran 2D blends).

**Not opened:**
- Mendeley vj83jj6fvt: 52 breast RT planning CTs as .mat. These are probably non-contrast; unverified.

## Rules check

I created no accounts, sent no requests or signatures, did no uploads and did not touch Girder or git. At most about 260 MB was on disk at once, and all test files were deleted. The scratch scripts are in my scratchpad and not in `round2/`.
