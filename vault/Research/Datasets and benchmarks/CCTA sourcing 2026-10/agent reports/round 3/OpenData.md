# Round 3, agent "OpenData": government and cloud open-data portals (2026-10-13)

## Bottom line
My territory has very little left. I found **one new open patient** and ingested it. It is an IDC/TCIA RIDER Lung PET-CT patient that round 1 missed because the series has no description. Every other portal is either a dead end or controlled access.

## Ingested
- **CCTA-Pool / `IDC-rider_lung_pet_ct`** (existing dataset folder, same source): patient **RIDER-1563443119**, 5 cases, about 0.50 GB, licence CC BY 3.0, https://doi.org/10.7937/k9/tcia.2015.ofip7tvm
  - **Scanner and protocol:** GE LightSpeed VCT, ScanOptions CINE MODE, 0.625 mm slices, 250 mm FOV, BodyPart CHEST, StudyDescription "Unspecified CT", no SeriesDescription. This is the same SnapShot-cine protocol as the round-1 "SS Cine" cases.
  - **Series:** three series (…496669, 1008 slices split into 3 volumes; …508860; …844232), each 512×512×336.
  - **Contrast:** whole-chest coverage with contrast; the aortic root and LV look bright on the preview. hu_p99 is about 350, and the median of voxels between 150 and 800 HU is about 240, so contrast is moderate. I have graded it T2: gating is likely but not proven, and DICOM cardiac-phase tags are absent.
  - **Possible repeats:** the 5 volumes may be repeat reconstructions or phases of one acquisition. All have distinct sha256.
  - **Duplicates:** this patient does not match any known RIDER duplicate pair by slice count or size.
- **Code:** `tools/ccta/round3/opendata_idc_search.py` (search), `opendata_hu_probe.py` (preview and HU check), `opendata_idc_rider_extra.csv` (fed to the existing `ingest_idc.py`, unmodified).

## IDC re-search (idc-index 0.13 / data v25, which is still the newest release; no v26 found)
I joined all 270,830 CT series with `ct_index` and `contrast_index`, then searched:
- **ScanOptions:** Siemens ECG tags `TPxxPC`, `BPM`, `BESTPH`, `PULSTART`. All hits are either already known or respiratory 4D-CT tags in RPM (`nsclc_radiomics`, `ct_vs_pet_ventilation_imaging`, `lctsc`).
- **Low pitch**, cardiac kernels (B26f, I26f, Bv40, Philips XC*, Toshiba FC43+) and cardiac ImageType values.
- **Small reconstruction FOV** (≤260 mm) with thin slices on the chest. This query found RIDER-1563443119.
- **Other RIDER leftovers I checked** (series ≤1.25 mm, ≥80 slices):
  - 2623772839 and 3333320954 ("W CAL" SS Cine): non-contrast calcium scans.
  - 2266952716: non-contrast, with metal artefact.
  - 2034182966: phantom.
  - 1344035392, 3084258403, 1836251657, 2828741099, 4838364823: duplicate IDs of known patients (identical sizes).
- **Collections added in v22–v25** (CMB-*, EAY131, VAREPOP-APOLLO beyond AP-26JK, Spinal-Multiple-Myeloma): no cardiac contrast CT. The other VAREPOP CTAs are PE or abdominal studies, i.e. T3.

## Dead ends (nothing cardiac contrast CT)
- **TCIA:** the website API lists 240 collections. The 2025–2026 additions (UCSD-BMETS, Pedi-Cranial-CT, EAY131, CPTAC-STAD, HANCOCK, …) contain none. Every public NBIA collection is also in IDC.
- **AWS Open Data Registry:** all 1,238 dataset YAMLs grepped. CT entries are MSD, RSNA sets, STOIC, RATIC, UCSF-RMAC and ENHANCE.PET (whole-body PET/CT), so nothing new.
- **Azure Open Datasets:** no medical imaging.
- **Google Cloud:** only IDC; the legacy `gcs-public-data--healthcare-tcia-*` buckets are closed to anonymous access.
- **Source Cooperative:** geospatial only.
- **Academic Torrents:** full `database.xml` (2,877 torrents) checked. CT entries are TotalSegmentator, APOLLO (= VAREPOP), NSCLC, LIDC and similar; the cardiac entries are echo or MRI only.
- **data.gov:** the new catalog search returns only literature records, NIST phantoms and USGS cores.
- **data.europa.eu:** the hub search hits are mostly Zenodo (Repos3's territory) plus a Swedish CTPA set (T3).
- **Other national portals:**
  - UK: data.gov.uk (0 hits).
  - Australia: data.gov.au (annual reports only).
  - Canada: open.canada.ca blocks scripts.
  - NZ: catalogue.data.govt.nz no response.
- **DataCite prefixes** (FRDR, Borealis, UNSW, Monash, Sheffield, Glasgow): theses only, plus the known ASOCA and Borealis K1INBL.
- **UK Data Service ReShare:** only 855916 (ASOCA, known) and 857706 (FISH&CHIPS, 1 MB of tabular data).
- **Project Imaging-X survey** (arXiv 2603.27460): no cardiac CT beyond known sets.

## Needs account or request (not ingested)
- **BioData Catalyst:** imaging is controlled access (dbGaP DAR plus eRA Commons login). The cardiac-relevant studies are:
  - phs004423 MESA CT Cardiac, about 6,800 subjects. Probably non-contrast calcium-score CT.
  - phs004665 ROMICAT-II, 1,000 subjects.
  - phs004872 PROMISE, 10,003 subjects.
  - phs004706 ISCHEMIA-CKD.

  For ROMICAT-II, PROMISE and ISCHEMIA-CKD it is not stated whether the CCTA images are included. They are BioLINCC accessions, likely tabular data.
  - ARIC, JHS, HCHS/SOL and FHS imaging projects: modalities unclear.
- **Curtin University "Computed tomography images of cardiovascular disease"** (50 patients, DICOM, aortic aneurysm/CAD/carotid): researchdata.edu.au record 3609 is now deleted. Access was "contact the dataset manager".

## Needs decision
None.
