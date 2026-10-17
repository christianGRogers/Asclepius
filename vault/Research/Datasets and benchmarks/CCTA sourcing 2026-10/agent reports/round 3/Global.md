# Round 3 — agent "Global" (non-English / regional open data), 2026-10-13
Status: **finished** — territory exhausted; nothing new and openly licensed to ingest.

## Ingested
(none — no new open, licensed contrast cardiac CT found in this territory)

## Needs decision (licence unclear)
(none)

## Needs account / request
- **Taipei Veterans General Hospital "Cardiac CT Image Dataset (Atrial Fibrillation)"**, Taiwan Medical AI & Data Portal (NYCU), https://data.dmc.nycu.edu.tw/dataset/d10-ct
  T2 (contrast pulmonary-vein / LA CT, plus some "CAD" CCTA series), 1,000 patients, ~55 GB DICOM, LA contour as DICOM-SEG, 2005–2018.
  "This data set requires application to access"; licence "No License Provided". The public CSV manifest (d10.csv, 91k rows,
  1,193 patient IDs) points to an internal 10.x WADO server, so nothing is downloadable. Study descriptions include
  "CT OF PULMONARY VEINS", "Specials^1_CAD", "Coronary CTA Survey Self-Pay", "CAD&PV" — i.e. some true CCTA. Contact via the portal.
- **IEEE DataPort "CCTA DATASET"** (Xiyue Han, Beijing Inst. of Technology, DOI 10.21227/8b1q-7q94), 150 MB zip of curved-MPR
  CCTA images (*.avi/*.csv) with DSA-based labels — needs an IEEE DataPort subscription; 2D curved-MPR derivatives, low value.

## Dead ends (searched, nothing open and new)
- ModelScope (dolphin dataset API, ~25 queries zh/en): only ImageCAS derivative (GDAsyou/StrucDiff_MeSSiTemp_ImageCas), M3D-Seg
  (no cardiac set), sepsis/lung CT, Aneumo (CFD). qsq12138/ruijin_qianzhan_ct is private.
- ScienceDB native search API (www.scidb.cn query service, ~30 zh/en queries, datacite mirrors excluded): no cardiac CT images;
  CCTA hits are all DataCite mirrors of arXiv/figshare records; "10-case CT and X-ray DICOM" (sciencedb.32821) is head.
- OpenXLab/OpenDataLab: backend API down (500); downloads need login anyway. Gitee API: resets/empty.
- Taiwan NYCU portal: 18 datasets, only d10-ct is cardiac (above). NCHC SciDM unreachable.
- DataCite native-language queries (zh/ja/ko/ru/es/pt/fr/de/it/pl/tr/fa/ar): only tabular/PDF records.
- Dataverse: search API on all 150 installations in the IQSS list (14 queries each): nothing cardiac-CT. Bot-walled (non-JSON):
  Fudan, PKU(partial), CORA/CSUC, heiDATA, e-cienciaDatos, SciELO Data, KU Leuven, UChile, UMinho — covered via DataCite prefixes instead.
- figshare (incl. J-STAGE Data) native-term search: nothing.
- Hugging Face: zhouwugen/CTAdata = MM-WHS copy (not used); others empty/text.
- MosMed (mosmed.ai) unreachable; no MosMedData cardiac set is known (COVID/LDCT only).
- AIKosh (IndiaAI): JS app, no cardiac CT found by search; downloads need sign-in.
- VinDr: no cardiac CT; KAIST "multiphase cardiac CT" (TIB LDM record 10.57702/rz053ven) is a paper-mention catalogue entry, no files.
- OpenI (openi.pcl.ac.cn, Pengcheng Lab), Gitee, ScienceDB-adjacent Chinese hosts frequently reset connections from this sandbox; OpenI could not be searched.
- Baidu AI Studio / Tianchi: search pages redirect to login; downloads need an account (not created).
- HyperAI (hyper.ai) cardiac/CT search (48 pages): only MRI/echo/lung/TCIA mirrors; ImageCAS mirror already known.
- KISTI DataON (Korea): search endpoint 404; Korean AI-Hub already known (nationals only).
- CiNii Research data (Japan, ja/en): only CSV/supplement records (e.g. Mendeley fzmwgtx7wf = CT-MBF CSV).
- EUDAT B2FIND (European aggregator): phrase search returns nothing relevant.
- DataCite by regional prefixes (MOST Wiedzy, Aperta, RepOD, e-cienciaDatos, CORA, heiDATA, KU Leuven, SciELO, UChile): nothing.
- DataCite English title search excluding big repos: only SCAPIS/UNSW/UKDS (known), meshes, CSVs (Loughborough TAVI FE = CSV).
- Kaggle user xiaoweixumedicalai (GDPH): 13 datasets, all already known (ImageCAS/CHD/ALCAPA/HOCM/TAAD/TBAD/CHD68 + echo/lung/breast).
- Mendeley kxfbxpfbrg (Zhejiang, 220 AF LA/LAA): meshes only (9 MB). Zenodo 10579450: 30 LA STL.
- Web searches in zh, ja, ko, ru, tr, fa, ar, es, pt, fr, de, it, pl: only known sets (ImageCAS, ASOCA, Coronary Atlas, ICADD, CADx, NTUH).
- Curtin cardiac CT (researchdata.edu.au/.../3609) is claimed by OpenData — not touched.
