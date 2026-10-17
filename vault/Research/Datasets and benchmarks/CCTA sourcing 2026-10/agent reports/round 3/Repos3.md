# Repos3 (round 3): Zenodo, Figshare (+ Figshare+, institutional), Mendeley Data, Dryad

Status: **done (2026-10-13). The territory is exhausted. Nothing new could be ingested.**

## Method (all API-driven, fully paginated)
- **Zenodo records API.** 131 query terms, each run two ways: title AND-match and phrase match, across all resource
  types (3,227 unique hits). Also boolean CT x cardiac queries per resource type, `file_type` facets (nrrd, nii, gz,
  raw, img, npz, dcm, mha), keyword-field queries, 15 relevant communities (including monzino, simcor, stopstorm and
  cardiology) and 23 multilingual queries (zh, ja, pt, es, de, fr, it, ru, tr, pl).
- **Figshare search API.** All item types, up to 10,000 hits per term (23,319 unique). Full article details fetched
  for 12,085 of them (files, licence, description); the rest were noise such as supplementary tables and figures.
  Also collections search and `:author:` searches on every uploader who already posted a cardiac CT (Xuesong Lu,
  Siriapisith, Pengling Ren, Ruifeng Chen).
- **Figshare+ (prefix 10.25452), all records via DataCite.** The only cardiac record is the pig set, already known.
- **Mendeley Data.** Server-rendered search pages for 132 terms (6,566 hits), then public-api file listings for
  about 3,700 records, plus a re-sweep of 143 records tied to SDN Naples contributors. DICOM headers were sampled by
  range read where needed.
- **Dryad v2 search** (66 hits) and **DataCite** by DOI prefix (10.17632, 10.25452, 10.6084, 10.5061, 10.5281).
- **Related identifiers.** DataCite `relatedIdentifier` queries for every known cardiac CT dataset DOI and for the
  key papers (ImageCAS, MM-WHS, TotalSegmentator, CAT08, Baskaran).
- **Web search** for figshare private links and for Zenodo and Mendeley cardiac CT deposits.
- Scripts are in /home/user/ccta/tools/ccta/round3/repos3_*.py. Harvest metadata is in round3/work_Repos3/ (no images).

## Ingested
None. Every open human cardiac contrast CT in these four repositories is either already in CCTA-Pool, already in
the round 1 and 2 reports, or claimed by another round-3 agent (figshare private links went to Modelling;
figshare 3452651 to Journals).

## Needs decision (licence unclear)
None new.

## Needs account / request (new this round, all Zenodo restricted, none requested)
These are all "Dataset related to the article ..." deposits, mostly from Centro Cardiologico Monzino. Each needs an
access request on its Zenodo record:
- TAVI landing zone: 18787638, 14808738
- CAD-RADS: 10667324 open but metadata only, 7504213 closed
- ECV CT: 10648226, 10648225
- Stress CTP: 13837738, 10648243, 18242105
- Structural valve degeneration: 6481707
- Others: 8131322 pre-TAVI annulus sizing, 5147922 LAA thrombus delayed CT, 3690825 in-stent CTP,
  14859120 myocardial bridging, 7613098 DL CT perfusion

Value is unknown and most probably hold tables only.

## Dead ends and duplicates checked this round
- **TotalSegmentator v3.0.0 (Zenodo 22688904, 1,939 CT).** I read meta.csv by range request. All 130 cardiac
  study-type cases are v2 ids: 116 are already ingested and 14 are non-contrast. The ~700 new cases are non-cardiac.
- **figshare "cardiac data 1..15"** (Xuesong Lu, 15 articles 1375504..1378609): byte-identical archives to figshare
  1379059, already ingested.
- **KCL figshare 16473828** (7 TMVR patients, 69 GB, ODC-By): CFD pressure and velocity fields only.
- **Out of scope (abdominal aorta):**
  - figshare 19090052 (AAA CT, Siriapisith)
  - Zenodo 19182978 and 15477710 (4D CTA of AAA)
  - Zenodo 10932957 (AAA meshes)
- **Not cardiac:**
  - Zenodo 15244881 (chest, head and knee DICOM compilation, CC BY-NC)
  - Mendeley rb26k7tgdk (Erdheim-Chester): its CT is abdominal
  - Mendeley w4mv8ypsr3: JPEGs only
- **Meshes, models or CFD only:** Zenodo 10577973 (CobivecoX ToF meshes), 10203116, 13829891, 7253863, 10526554;
  figshare 20465142, 3452651 (claimed by Journals), 16964929.
- **Software snapshots with no CT:** Zenodo 21342464 (VascuNet), 14870126 (AAOCA), 20342734 (CardiacAR Unity),
  22696740, 7334353 (videos).
- **No images:** SDN Mendeley spreadsheets (38bv2jv583, fryknpmt8s, 3dbttznwrz, trnjpmsym3, fj78mnykjn);
  Uchida PCAT records (histology slides).
- **2D only:** Mendeley 6m4kb3vffg (2D uint8 from public sets); figshare 22132479, 19945032, 30911237 (journal
  figures and JPEGs).
- **Animal or phantom:** figshare 28303637 (mouse micro-CT), 7435532 (calcium phantom).
- **Dryad:** no human cardiac CT volumes.
- **Figshare surgical videos:** about 150 CTSNet/Frontiers media items.
