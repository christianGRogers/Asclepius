# Round 2: Catalogues, software sample data and demo servers (agent "Catalogues", 2026-10-12)

**Scope.** I checked the gfahrni open cardiovascular imaging catalogue (all 23 CT rows, from the Zenodo snapshot CSV), awesome-style GitHub lists, Hugging Face dataset search, Grand Challenge public archives, the AWS Open Data Registry plus AWS Marketplace/ADX, and Google Cloud. I also checked software sample data (3D Slicer core, SlicerHeart and other Slicer extensions, SimpleITK, vmtk, VolView), demo servers (Orthanc, OHIF, DICOM Library, Medical Connections), vendor and viewer sample pages (OsiriX/Pixmeo, Rubo, RadiAnt, MedDream, NEMA, Siemens/GE/Canon/Philips), and teaching-file and museum sites (Radiopaedia, Embodi3D, MorphoSource). Every open T1/T2 source below was downloaded and rendered, then deleted. Large zip/tar archives were tested by HTTP range-reading a single member: `round2/scripts_Catalogues/rzip.py` and `rtar.py`.

**Bottom line.** This territory adds **no large new CCTA cohort**. What it does add:

1. A **TotalSegmentator cardiac-protocol subset**: about 127 contrast cardiac-protocol CTs (several of them CCTA-like), CC BY 4.0, open now, single cases extractable. The catch is that every image is resampled to 1.5 mm isotropic.
2. **Four single open cardiac CTs from Slicer and SlicerHeart.** Best of these is a full-resolution **21-phase gated cardiac CT** (TruncalValve_4DCT).
3. **Three open T3 sets, now tested**: AortaSeg-60 (50 contrast, CC0), ChestPathCT5-S100 (20 CTPA, CC0) and MSD Task06 Lung (96, venous phase).
4. **One free but account-gated T1 lead**: the OneMedNet CCTA samples on AWS Data Exchange. They need an AWS account and a EULA, the sample size is unknown, and I did not test them.

## Ranked list

| # | Source | Tier | Scans | Size | Licence | Access | Tested |
|---|---|---|---|---|---|---|---|
| 1 | TotalSegmentator v2 cardiac-protocol subset, https://zenodo.org/records/10047292 | **T1/T2 at 1.5 mm** | ~127 of 1,228 | 23.6 GB zip (per-case range read works) | CC BY 4.0 | open | yes (6 cases; CCTA blood pool ~540 HU) |
| 2 | SlicerHeart **TruncalValve_4DCT**, https://github.com/SlicerHeart/SlicerHeart/releases/download/TestingData/TruncalValve_4DCT.seq.nrrd | **T1** | 1 patient × 21 phases, 0.6×0.6×0.7 mm | 1.27 GB | BSD-3 repo (data licence unstated) | open | yes, blood pool ~527 HU |
| 3 | Slicer **CTACardio**, https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/3b0d4eb1a7d8ebb0c5a89cc0504640f76a030b4e869e33ff34c564c3d3b88ad2 | T2 | 1, 0.93×0.93×1.25 mm | 64 MB | Slicer licence per maintainers; source undocumented | open | yes, ~374 HU |
| 4 | SlicerHeart **PDA_CT** (infant CTA), …/TestingData/PDA_CT.nrrd | T2 | 1, 0.3×0.3×0.5 mm | 55 MB | BSD-3 repo | open | yes, ~462 HU |
| 5 | AortaSeg-60, https://zenodo.org/records/18147026 | T3 | 50 contrast (40 arterial, 10 venous) + 10 unenhanced | 15.9 GB | **CC0** | open | yes (Young_01, whole-aorta CTA incl. heart) |
| 6 | OneMedNet CCTA free samples (AWS ADX), https://aws.amazon.com/marketplace/pp/prodview-tsjnviqmaw3ie and https://aws.amazon.com/marketplace/pp/prodview-tmre53jcrzttg | T1 | sample size unstated; listings describe 117 and 130 pt / 260 studies | ? | vendor EULA | AWS account + $0 subscription; approval process unknown | no |
| 7 | Slicer **CTCardioSeq** (10-phase), https://github.com/Slicer/SlicerDataStore/releases/download/SHA256/d1a1119969acead6c39c7c3ec69223fa2957edc561bc5bf384a203e2284dbc93 | T1 (low-res) | 1 × 10 phases, 1.15×1.15×2 mm | 13 MB | as Slicer | open | yes, ~438 HU |
| 8 | ChestPathCT5-S100, https://zenodo.org/records/18256797 | T3 | 20 CTPA (PE zip) | 1.36 GB (9.4 GB all) | **CC0** | open | yes (PE_001) |
| 9 | MSD Task06_Lung, https://msd-for-monai.s3-us-west-2.amazonaws.com/Task06_Lung.tar | T3 (weak) | 96 | 9.2 GB | CC BY-SA 4.0 | open | yes (2 cases, venous phase) |
| 10 | Slicer CTPCardioSeq (perfusion, 2 mm) | T2 (very low value) | 1 × 26 frames | 20 MB | as Slicer | open | yes |
| 11 | DICOM Library CT sample, https://www.dicomlibrary.com/ | T3 | 1 body oncology CT | 0.5 GB | none (user upload) | open | yes |
| - | OsiriX library cardiac sets (AGECANONIX, CARDIX, FOURDIX, GOUDURIX, MAGIX, TOUTATIX, FIVIX; T3 TRAGICOMIX, OBELIX), https://www.osirix-viewer.com/resources/dicom-image-library/ | T1/T2 | 9 studies | ~0.8 GB | research/teaching, no redistribution | **paid Premium membership now**; no mirrors found | no |
| - | Figshare private link https://figshare.com/s/caa70792c43ac01d8175 ("de-identified cardiac CT, DICOM, chamber/vessel annotations") | T2? | ? | ? | ? | bot wall; needs one manual click | **unverified** |

## 1. TotalSegmentator v2 cardiac subset (new detail on a round-1 entry)

Round 1 (`Repos.json`) graded TotalSegmentator as T3 from the record alone. The `meta.csv` inside the zip, which I extracted by range read, gives a study type for each case:

- 46 "ct heart-thorakale aorta"
- 34 "ct aortic valve" (TAVI-planning style)
- 34 "ct heart"
- 13 "ct left artrium"
- 3 "ct coronary arteries"

There are also about 31 thoracic or whole-body CT angiographies. Almost all were scanned on Siemens Definition Flash/Edge/Force at University Hospital Basel. **Every image is resampled to 1.5 mm isotropic**, which limits coronary use. Even so, the main coronaries are often visible on contrast cardiac scans at that spacing.

How to get one case: run `python3 -I rzip.py "https://zenodo.org/records/10047292/files/Totalsegmentator_dataset_v201.zip?download=1" "sXXXX/ct.nii.gz" out.nii.gz`. Each call re-reads the large central directory, so it takes about 1–3 minutes, and Zenodo sometimes drops TLS (retry). The more practical route is to download the 23.6 GB zip once and filter it by `meta.csv`.

Test results:
- **s0671** (left atrium): contrast cardiac CT, LA/LV/aorta bright. **T2.**
- **s0230** (heart-thoracic aorta): contrast chest CTA. **T2/T3.**
- **s0085** ("coronary arteries"): **non-contrast**, so it is a calcium-score scan.
- **s0738** ("ct heart"): tight-FOV CCTA, blood pool ~540 HU. **T1-like.**
- **s0270** ("ct heart"): contrast cardiac CT. **T1/T2.**
- **s0189** ("ct aortic valve"): TAVI-type arterial CTA from chest to pelvis. **T2/T3.**

**Verdict:** about 127 usable contrast cardiac scans: all study types above except the 3 "coronary arteries" calcium scans. This is the largest open, permissively licensed pool in this round, but only at 1.5 mm. Filter by aortic-root HU before ingesting, because some "ct heart" cases may be calcium scans.

## 2. Software sample data

- **3D Slicer core SampleData**, from `Modules/Scripted/SampleData/SampleData.py`:
  - CTACardio: contrast thoracic CT with the heart in view.
  - CTCardioSeq: 10-phase cardiac CT, downsampled.
  - CTPCardioSeq: 2 mm perfusion series.
  - CTChest: **non-contrast**, excluded.
  - CTAAbdomenPanoramix: the OsiriX PANORAMIX abdominal CTA.
  - CTLiver: MSD liver_100.

  Maintainers state that the sample data are covered by the Slicer licence (discourse.slicer.org/t/33260). The source institution of CTACardio is undocumented.
- **SlicerHeart** (`ValveAnnulusAnalysis.py`): PDA_CT (infant CTA, with a vasculature segmentation) and TruncalValve_4DCT, a "4D gated CT of adolescent with truncus arteriosus s/p repair", 21 frames at full resolution. The other SlicerHeart samples are echo or fluoro.
- **No other cardiac CT samples**:
  - Slicer extensions (GitHub code search of `registerCustomSampleDataSource`, more than 200 hits; LinFloNet reuses CTACardio, SeqSeg and CalciumScoring reuse brain MRIs).
  - SimpleITK notebooks (POPI is non-contrast 4D lung).
  - vmtk-test-data (cropped aorta, not HU).
  - VolView (only CTA head/neck and cardiac MRI; hosted on data.kitware.com Girder, which I did not touch).
- GitHub release-asset listing pages and the API are blocked from this sandbox, so I could not enumerate the release assets of SlicerTestingData or SlicerHeart beyond what the code references.

## 3. Demo servers and sample libraries

- **Orthanc demo**: 8 OsiriX-derived studies, none cardiac.
- **OHIF demo DICOMweb**: 83 studies. The contrast chest CTs there are TCIA cases (COVID-19-NY-SBU, NSCLC, LIDC-style), so they belong to IDC territory. No cardiac studies.
- **DICOM Library**: one CT sample, a Lithuanian two-phase oncology body CT. The tokenised download works.
- **OsiriX/Pixmeo**: the library is now behind a paid Premium membership. It contains 7 cardiac and coronary CT studies plus 2 thoracic or whole-body CTAs. I found no public mirrors on Kaggle, Hugging Face, Zenodo or GitHub.
- **Rubo Medical**: XA and US samples only.
- **RadiAnt**: no sample data.
- **NEMA multiframe CT samples**: removed (404).
- **Medical Connections public PACS**: the port is blocked from here, and it holds user uploads anyway.
- **MedDream**: viewer only.
- **Siemens, GE, Canon, Philips**: no public DICOM downloads found.

## 4. Catalogues and registries

- **gfahrni catalogue**: all 23 CT rows map to the brief's exclusion list or round 1, except **ChestPathCT5-S100** (new) and KiPA22 (kidney, excluded). ImageVessel is in fact cropped to one lung with the heart out of view, so it is excluded. "3D CAS Images" uses ImageCAS file naming and voxel sizes, so it is an ImageCAS duplicate.
- **Awesome lists** (sfikas, adalca, openmedlab, linhandev, beamandrew): nothing new.
- **Hugging Face search**: nothing new. CTRG-Chest-548K volumes are uint8, not HU, so excluded.
- **Grand Challenge archives**: none cardiac, and downloads need a login.
- **AWS Open Data Registry**: 13 CT datasets. The only ones checked here are MSD (above) and STOIC2021 (2 of 2 sampled scans were non-contrast, excluded). RATIC is abdominal and controlled access.
- **AWS Marketplace/ADX**: OneMedNet free CCTA samples (row 6).
- **Google Cloud**: only IDC, which is already covered.
- **Papers with Code**: retired.

## 5. Excluded or not downloadable

- **Radiopaedia**: only 8-bit image stacks, CC BY-NC-SA, no DICOM or HU export.
- **Embodi3D**: returns 403 to scripts; a free account is said to be needed (unverified).
- **MorphoSource**: animal and specimen micro-CT, mostly restricted download.
- **Teaching files** (MedPix, Eurorad and similar): JPEG only. The University of Minnesota Visible Heart Lab provides DICOM only on request.
