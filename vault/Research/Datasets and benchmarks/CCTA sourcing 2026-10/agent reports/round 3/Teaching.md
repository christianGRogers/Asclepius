# Round 3, agent "Teaching" (2026-10-13): final

Territory: teaching files, DICOM sample sites, software demo/test data, tutorials linking a cardiac CTA.

**Bottom line:** nothing new with an open licence, so nothing was ingested (0 cases, 0 GB, no Girder folder
created). This corner is effectively exhausted. Every viewer/toolkit sample library either has no cardiac CT or
reuses the known Slicer samples (CTACardio, CTCardioSeq) or OsiriX sets. Two contrast cardiac CTs can be
downloaded right now but have no open licence (they need a decision).

## Ingested
None.

## Needs decision (downloadable now, licence missing or restrictive)
1. **OsiriX CARDIX + MAGIX on the Kheops public demo server.** https://demo.kheops.online uses a demo token
   published in the Kheops docs (github.com/OsiriX-Foundation/KheopsDocumentation, docs/tokens/curl.md):
   `https://demo.kheops.online/api/link/B18jTXCzTrQzj1ZednqHUY/studies` (DICOMweb; zip via `?accept=application/zip`).
   I verified the study, series and instance metadata. I did not download any pixel data.
   - CARDIX: 1 series, 452 images, Philips Brilliance 64, 0.67 mm slices, 0.40 mm pixels, contrast: **T1 CCTA**.
   - MAGIX: Siemens Sensation 64, "CardiacCirc 3.0 B20f 0-90%", 10 phases x 76 images at 3 mm: T1, low z-resolution.
   - The server also holds DIASTOLIX (already known from round 1) and some non-cardiac sets.
   - OsiriX terms are research/teaching only, no redistribution, so these are not open.
2. **Aliza MS sample "4D Cardio (Nifti)".** Google Drive id 0ByBLJ2-U1t9xVzRjYWdhRWFOUGc (anim3.nii.gz, 95 MB),
   linked from https://www.aliza-dicom-viewer.com/download/datasets.
   - I downloaded and viewed it: 462x364x50 voxels x 9 phases, 0.47x0.47x1.5 mm, int16 in HU, blood pool about 350-440 HU.
   - It is a gated multi-phase contrast cardiac CT, but covers only 75 mm in z (LV, LA, aortic root). Count it as T2.
   - Origin and licence are not stated. File deleted.
3. **Radiopaedia** (from round 2): 8-bit stacks under CC BY-NC-SA 3.0, many CCTA cases.
   - The site returns HTTP 406 to scripts. Its terms reportedly restrict automated download and ML reuse (I could not check the page).
   - Not scraped; the lead decides.

## Needs account / subscription / request
- IEEE DataPort "CADx" 3D coronary CTA NIfTI (222 MB): https://ieee-dataport.org/documents/cadx. Needs an IEEE DataPort subscription.
- Curtin University "Computed tomography images of cardiovascular disease" (50 cases, DICOM):
  https://researchdata.edu.au/computed-tomography-images-cardiovascular-disease/3609. Contact the data manager.
- Univ. Minnesota Visible Heart Lab DICOM: request form at https://www.vhlab.umn.edu/atlas/histories/dicom-request.shtml.
- Medality "Cardiac CT practice cases" (52 DICOM cases): https://medality.com/course/radiology-cardiac-ct-practice-cases/. Paid course.
- OsiriX library direct download: needs Premium membership. I could not test Wayback copies (web.archive.org resets from this sandbox).
- Embodi3D: account (round 2).

## Dead ends (checked, no new open contrast cardiac CT)
- **Viewer and vendor sample sites:**
  - Weasis demo: conformance test images only.
  - ITK-SNAP data page: brain MRI and echo.
  - MITK-Data "3D+t-Heart" is MRI.
  - InVesalius: head CT only.
  - Aliza: the rest is MR/US/test data; its Toshiba CT is a liver scan (checked).
  - 3DICOM library: lung, skull, arm.
  - MediModel samples: dental and skull.
  - dwv: single slices.
  - neurolabusc dcm_qa_ct / NITRC dcm2nii: phantom and head CT.
  - NEMA sample directories: removed.
  - Saga IT: Cloudflare-blocked, and its content comes from IDC.
  - Materialise / Mimics, MicroDicom, Santesoft, IMAIOS: no public cardiac data (some sites unreachable).
- **Toolkit test data:**
  - TotalSegmentator test files: 3 mm abdominal CT.
  - MONAI / MONAI Label: Task02 heart MRI and other MSD tasks.
  - nnU-Net and pydicom: nothing cardiac.
  - Biomedisa "heart": HVSMR MRI.
  - ChimeraX: TCIA RIDER lung.
  - Heartbeat4D: code only.
- **data.kitware.com Girder (walked 13 collections):**
  - Trame "heart.nii.gz" is an ex-vivo heart MRI.
  - VolView "CTA-Chest.mha" (0.86x0.86x0.6 mm) is a non-gated contrast chest CTA: T3, provenance undocumented.
  - The rest is CTACardio, head/neck CTA or liver.
- **Slicer discourse (search API plus the pieper/slicer-discourse-archive mirror):** shared cardiac data are the known
  Slicer samples or user videos.
- **YouTube** (about 60 tutorial video descriptions read through the innertube API): links point only to Slicer samples
  (CTA-cardio2.nrrd = CTACardio), MSD, an OSF crocodile CT, and Kaggle nikhilroxtomar (already excluded: chest-CT heart masks).
- **Others:**
  - Brown Digital Repository / RI Hospital Holoimage CTA hearts: meshes only.
  - NIH 3D: meshes (and claimed by the Modelling agent).
  - gts.ai CardioScans: a Kaggle re-host (Kaggle agent's territory).
  - Wikimedia Commons: API rate-limited from this IP. It holds only 8-bit images/videos anyway; not searched.
  - XNAT Central: unreachable (502).
