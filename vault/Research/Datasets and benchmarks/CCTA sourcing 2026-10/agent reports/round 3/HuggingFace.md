# HuggingFace (round 3) — Hugging Face territory

Status: done (2026-10-13). Territory exhausted: one new open cardiac CT source (CCA-200 train split, 20 CCTA), ingested.

Method: HF list API (`/api/{datasets,spaces,models}?search=`, ~150 query variants incl. Chinese; dataset tag filters
medical/biology/ct/3d/radiology/segmentation/cardiac/heart/nifti/dicom/modality:3d/healthcare/...; ~11.7k datasets with
descriptions), file listings of ~9,500 keyword-matching repos (datasets + spaces + models) scanned for volumetric
files (.nii/.nii.gz/.dcm/.nrrd/.mha/.vti + archives), full upload lists of all 108 authors hosting volumes
(+1,404 repos), HF README full-text search (`/api/search/full-text`, 50 queries x datasets/spaces/models, ~9.5k hits, 5.7k new repos scanned), every remaining dataset from the tag/search listings (+7.2k) and all spaces/models from the searches (+3.5k). ~24k repos file-listed in total.

## Ingested
| Dataset folder | Source | Tier | Cases | Licence | Notes |
|---|---|---|---|---|---|
| CCTA-Pool/CCA200-HF | https://huggingface.co/datasets/MedHK23/CCA | T1 | 20 uploaded (with labels) | GPL-3.0 (dataset card) | CCA-200 public train split (arXiv 2305.04208, Shanghai AI Lab/CUHK, own collection, not ImageCAS). HU int16, resampled 0.5 mm iso, 832x832x576, blood ~530 HU. label.nii.gz = binary coronary lumen. ~2.7 GB. Identical mirror: L10LYL/CCA. |

## Needs decision (licence unclear)
(none so far)

## Needs account / request (HF login + click/form)
- FLARE-MedFM/FLARE-Task4-CT-FM (gated auto, CC BY-NC): 13k CT, all abdominal/chest/PET public sets; no cardiac. Not worth it.
- FLARE-MedFM/FLARE26-MLLM-3D (manual gate): CT-RATE + AMOS only. No cardiac.
- gevaertlab/conflux-chest-ct (gated): synthetic chest CT. Not real.
- AI-CVM/Cardiac-CT (manual gate, CC BY-NC-ND): ImageCAS + MM-WHS labels only (known).

## Dead ends (checked)
- junma/CVPR-BiomedSegFM (CC BY-NC-SA, open): cardiac CT only CT_TotalSeg_cardiac (known corpus, npz); CT_Aorta / Aortic-Dissection are T3.
- CADS-dataset (mrmrx and ~12 copies): 22k CT from public sources; no cardiac source.
- BodyMaps/CancerVerse, AbdomenAtlas*, PanTS, Gastric-X, TriALS, CCSeg (costal cartilage), Lumina-Thorax (X-ray), Altoia/Embolism (CTPA).
- Ryan710/PC-CAC (CC BY 4.0): point clouds (.ply) only.
- Rcronshaw/ccta1: 45 web JPEGs (LoRA training set).
- Sai952002/cardio_test: "06_Cardiac_CT" is CSV tabular proxies.
- vishnusureshperumbavoor/dicom_public_dataset: one abdominal CT.
- Perle-ai/multimodal-ct-radiology-reports: abdominal 3-phase / chest / brain CT, DUA no-redistribution.
- DEPICT-RH/Multimodal-HC, BIC-MAC: low-dose non-contrast PET/CT.
- fxhjdxj/vessel_dataset_all: ImageCAS copy (995) + CAS2023 (brain) + Parse2022 (CTPA) + SEG.A (aorta, T3); no licence.
- zhouwugen/CTAdata: MM-WHS CT copy (unauthorised mirror).
- jethro682/imagecas, jethro682/total_64: ImageCAS/TotalSegmentator copies (known).
- MedOtter (186 mirrors): only cardiac CT is totalsegmentator-cardiac (known); Aortic-Dissection-Graz is T3; rest MRI/echo/other.
- YongchengYAO (31 "Lite" sets), AbdomenAtlas, MONAI testing_data/model zoo, kmin06/CVPR26-3DCTFMCompetition, MitakaKuma/*,
  huyquoctrinh/SpatialMed, FLARE-MedFM/*: no cardiac contrast CT.
- Spaces: IFMedTech/CT_Segmentation `sample_ct_cardio.nii.gz` is a non-gated thoraco-abdominal contrast CT at 1.25 mm
  (T3, provenance unstated); edureisMD/TotalSegmentator examples are 1.5 mm TotalSegmentator-style cases;
  Left_Atrium spaces use MSD MRI; trungthai1771 vessel_3ch.nrrd is synthetic.
- viennh2012/*, MedOtter/ACDC/EMIDEC/HVSMR, TaipingQu/*: cardiac MRI. CETUS/CardiacUDC: echo.
- BearSubj13/CoronaryDominance, MesserMMP/coronary-angiography-syntax: invasive X-ray angiography.
- chinmay55/VesselTok-data: centreline graphs only.
