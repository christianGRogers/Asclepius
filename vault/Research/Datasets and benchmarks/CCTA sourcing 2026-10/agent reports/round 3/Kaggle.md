# Round 3 agent "Kaggle" (2026-10-13) — living report

Territory: Kaggle datasets (anonymous search API, uploaders, competitions, notebooks).

**Bottom line:** Kaggle is saturated. One new open cardiac CTA source was found and ingested (5 CCTA, mrdurch);
everything else that is cardiac CT on Kaggle is already known (Xu-lab sets, CAD-RandomSamples, HeartSR, OsiriX
sample, ImageCAS + mirrors, ASOCA/CAT08/MM-WHS mirrors, AVT, Taiwan AI CUP PNGs) or out of scope.

**Method:** 809 search queries (English + FR/DE/ES/IT/PT/TR/ID/PL/VI/ZH/JA/KO/RU/AR/HI; anatomy, pathology,
procedures, scanners SOMATOM Force/Definition Flash/Revolution/Aquilion/iCT/IQon/LightSpeed..., file types
dcm/nii/nrrd/mhd, nnU-Net/TotalSegmentator/SAM terms, challenge names), several with minSize filters to get past
popular non-imaging hits, plus the "heart conditions" and "health conditions" tag listings: 49,386 unique datasets
seen. 4,647 candidate datasets (cardiac/vascular/CT words, >5-30 MB) had their file lists probed for 3-D volume
files (nii/dcm/nrrd/mhd/mha/vti/IMA/extensionless DICOM/npz/h5/mrb); every cardiac-looking volume set was opened
(DICOM tags or volume + preview PNG). All datasets of every uploader who posted cardiac CT were listed
(xiaoweixumedicalai, younesselbrag, victorsix, grantmcnatt, apette, abbymorgan, f74096386, ahanafabidsazid,
ayuuushsri, ayushsri2004, christopheronyiuke, mohammadmohaisen, manar18, kiuyha, arioobarzan, saurabhshahane,
mrdurch, hasanbarimani). Scripts: /home/user/ccta/scripts/round3/kaggle_*.py.

## Ingested
- **Kaggle-mrdurch-WS3D-Cardiac** (T1, 5 CCTA of 512x512x280-320 voxels, about 0.8 GB as released (uncompressed int16), CC0 stated, provenance_verified=false): https://www.kaggle.com/datasets/mrdurch/weakly-supervised-3d-cardiac-image-segmentation . 0.43x0.43x0.5 mm HU, Chinese hospital (undocumented). Source file names are patient names: NOT stored (cases numbered 1-5, name hash only). label.nii.gz = label_GT (1 LV myo, 2 LV blood, 3 "RV" per README but looks like LA on case1; 255 ignore). Lead should decide whether to keep it given the leaked-name provenance.

## Needs decision (unclear licence)
- Nothing new. (Known: HeartSR victorsix/cardiac-ct-lr-hr, no licence; CAT08/ASOCA/MM-WHS Kaggle mirrors, unauthorised.)
- Provenance decision: Kaggle-mrdurch-WS3D-Cardiac (above) is CC0 as stated but the uploader exposed patient names in file names.

## Needs account / request
- Kaggle competitions list and notebooks (kernels) API answer 401 without login, so competition data pages and
  notebook inputs could not be enumerated anonymously (would need a free Kaggle account + API token; not created).
  Competition data also needs rule acceptance. No Kaggle competition with cardiac CT is known (RSNA STR PE = CTPA,
  T3, no redistribution; RSNA 2025 aneurysm = head CTA). Notebook inputs that matter surface as datasets anyway.

## Dead ends (checked, not cardiac contrast CT or duplicates)
- adamhuan/multiphase-ct-anigography-2-datasets: head/neck CTA (LightSpeed VCT).
- falahgatea/heart-ct-images: same PCIR "CTA AORTA" series as abbymorgan/heart-ct (T3, known).
- nikhilroxtomar/ct-heart-segmentation: NLST low-dose non-contrast chest CT.
- MRI/echo sets under "heart" names: zyh1104/human-heart-data, anfaalhossain/camus-humanheart, mohan1111/chd-dataset (CAMUS echo), khiem20092004/* & nhuquynhvothi/humanheart (ACDC MRI), luhtookyaw (MSD LA MRI), snikhilrao HVSMR (MRI), cemil4gpu/vesselwall (carotid MRI).
- 2D-only (PNG/JPG/BMP): kvipularya, ramimatiz, yossefmostafa, klu2000030172 (Mendeley CCTA atherosclerosis MPR PNGs), saurabhshahane & arioobarzan (PNG blends), tiengtieng123 (ARCADE XA), tvd3323 (XA BMP), rahult25, enhancedmachinen & licethyaneth (aorta PNG slices), myhelloful1, killa92, enasemad.
- sandorkonya/ct-lung-heart-trachea-segmentation: OSIC non-contrast heart masks.
- hasanbarimani/4-cta-binary-multi-label-2025-06-22: 4 ImageCAS cases (101-104, ImageCAS shapes/naming) with extra labels — ImageCAS derivative.
- infobayai/medical-ct-scan: HRCT thorax, non-contrast.
- Head/neck CTA (RSNA 2025 aneurysm derivatives: shymaaelbana/*, devkumarbiswas/*, varsha1dewangan, dennisfong/*, matsrobben; CMHA intracranial aneurysm amirmmahdavikia/*): not cardiac.
- manar18/aortic-vessel-tree-avt-cta: AVT (T3, known).
- xiaoweixumedicalai/mytest: pulmonary vessel set (T3, known).
- tmcdlcourse/anon-chest-ct: SOMATOM Force chest-abdomen contrast, non-gated (T3).
- oussmd/data-ct-thorax-moroccan-3d-mrb: RT-planning thorax CT in Slicer scenes, non-contrast, 3 mm.
- Generic CT sets (lung/LIDC/NLST/OSIC/COVID/MosMed, abdomen/FLARE/AMOS/KiTS/LiTS, brain/CQ500, Mayo LDCT, phantoms, TCIA mirrors): not cardiac.
- xiaoweixumedicalai/cardiacudc-dataset, echocp, abnormcardiacechovideos, regional-wall-motion: echo.
- xiefei/humanheart, zx1122112/heartmri: CAMUS echo / MRI npz slices. kara6776/cardiac-test-dataset: 2D RGB 150x150 arrays.
- junyasato/ai-medical-contest2024-imagestr (CC BY, 357 vols): abdominal/torso CT, 1 mm resampled — not cardiac. liaoguoying/niidataset: abdominal arterial phase. nd905114/ct-mr: RSNA aneurysm CTA + MR. rakshithamallik/nnunet: LUNA lung CT.
- arjunashokbhandary/gsoc-coca-segment: 48 Stanford COCA gated NON-contrast calcium CTs (out of scope).
- rohitzzzz/segthor-dataset: SegTHOR RT-planning thoracic CT (T3, licence unknown).
- yyowoing/ctaidataset: abdomen/pelvis arterial+venous phase (GE). kmader/ct-scans-before-and-after: TCIA registration pairs.
- younesselbrag/coronary-artery-diseaes-dataset-normal-abnormal: 2D JPG (Jordan).
- Tag/'heart conditions' listings: ECG (MIT-BIH etc.), RSNA PE npy (CTPA, T3), CAMUS echo, mammography — nothing cardiac CT.
- Leads outside Kaggle seen in passing (other agents' territory): Mendeley fj78mnykjn; IEEE DataPort "3D CCTA NIfTI for CAD classification".
