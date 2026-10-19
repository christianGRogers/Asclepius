<!-- A30 per-source QC, written by a research subagent from the repository's ingest code and sourcing reports (2026-10-19).
Its headline numbers were re-derived independently by a30_grouping_qc.py (a30_grouping_qc.json): 469 patients, 133 real
sealed patients, 60 leaked volumes. The extension-order figure here (125) counts per entry; a30_grouping_qc.json counts 119
distinct new patients (it also merges extension entries of one patient with each other). -->

# A30 QC: patient keys in the sealed pool proposal (Bridge r9)

Inputs: `configs/segqueue14/pool-2026-10.txt` (675 volumes), `experiments/Bridge/r9/seal_pool.py` and
`experiments/Bridge/r9/sealed_pool_proposal.json`. Re-running `python3 experiments/Bridge/r9/seal_pool.py configs/segqueue14/pool-2026-10.txt 150 20`
reproduces the JSON byte for byte (checked with `cmp`). Nothing in the repo was changed.

Heuristic key = `<Source>__<2nd field>`, with one trailing `(_tp\d+|_p\d+|_(diast|syst)|_s\d+)` removed.
"S" = in `primary.patients` (sealed), "R" = `report_only.patients`, "E#n" = position n in `primary.extension_order`.

## Bottom line

- **The heuristic under-groups 6 real patients and leaks them.** Four Mendeley-SDN case-report records are
  **one patient per record**. In them, `sNNN` is the **DICOM series number**, not a subject. The ingest code
  also sets one `patient_id=SDN-<record>` for every case in a record. On top of that, the `_fNN` frame suffix
  (Mendeley-SDN-4643nn2z44 `s010_fNN` and Slicer `*_fNN`) is not in the regex at all, so every frame becomes
  its own "patient".
- **Effect on the proposal:** the 150 sealed primary keys are really **133 patients**. **60 volumes that belong
  to sealed patients are outside the seal** and could be trained on: SDN-spb25zt2c4 31, SDN-4643nn2z44 13,
  Slicer TruncalValve 8, SDN-37nnfyh3x9 5, SDN-7x9kb53262 2, Slicer CTCardioSeq 1. One patient
  (Mendeley-SDN-4643nn2z44) takes **10 of the 150 sealed slots**.
  - Pool totals: 517 patients become **469**; the primary stratum's 360 become **312**.
  - The 150 extension entries are really **125 patients**, and **31** of them belong to a patient that is already sealed.
- **No over-grouping was found.** Every suffix the regex strips is a phase, time point, series or
  reconstruction of the same patient, in every source where it fires. No `_p\d+` is a patient and no stripped
  `_s\d+` is a subject. The `sNNN` fields are not stripped, so they are not over-grouped either: they are the
  under-grouping above.
- **One cross-ID suspicion inside IDC RIDER is worth acting on conservatively:** RIDER-2522924559 (sealed)
  and RIDER-2551730224 (E#79). See the duplicates section.
- Every other source groups correctly as far as the evidence goes. Several cannot be verified at patient level
  because the source publishes no patient id. Those are marked "unverifiable" below, with the reason.

## Per-source table

| Source | Vols | Heuristic keys | What the name fields mean (evidence) | Verdict | Sealed / extension patients affected |
|---|---|---|---|---|---|
| BMC-BEO2017-SerialStenosis-CCTA | 1 | 1 | `P1` is a constant set by the ingest for this one-patient deposit; `_sN` = DICOM SeriesNumber (`tools/ccta/round3/journals_suppdicom.py:28` `patient='P1'`, `:104` `case=f"{patient}_s{SeriesNumber}"`, description `:29-36` "One patient … BestDiast 70 % and BestSyst 40 %"). | correct (`_s5` stripped → P1) | P1 = E#1. Only s5 is in the pool (s6 is QC "no"). |
| CCA200-HF | 20 | 20 | `CCA_NN` = file number N of the HF `train/images/N.nii.gz` (`round3/huggingface_cca.py:41`). The dataset is "20 CCTA with CAD", i.e. one volume per patient (`:34-37`). No patient id is published. | correct (assumed 1 file = 1 patient; not documented further) | none (excluded stratum: spacing suspect) |
| Figshare-23057000 | 2 | 2 | `PA0`/`PA1` = the two NIfTI file names in "Test Data.rar" (`ingest_open.py:1225`). The deposit says "Two CCTA data", with no provenance (`ingest_open.py:1205-1207`). They are different reconstructions: in-plane 0.416 vs 0.430 mm, blood pool median 450 vs 389 HU (`agent reports/round 2/Institutional.json:38,44`; QC csv). Nothing says whether they are the same or two patients. | unverifiable; kept apart as required (no evidence of the same patient) | PA1 = S, PA0 = E#2. If they were one patient, PA0 would leak. Low risk, no evidence either way. |
| Figshare-CardiacCT15 | 15 | 15 | `patN` = archive number N (`N.rar`) = patient; `tpK` = time-point number in the .mhd name (`ingest_open.py:827,840-841`). The release is "one registered phase per patient" (`:819`); `Asia.json` says "15 patients (one registered time-phase volume per archive)". Every pool volume is `tp0`, one per patient. | correct (tp = phase of the same patient) | 6 S (pat5, 6, 7, 10, 13, 15), 9 in E. All one volume each, no leak. |
| Figshare-DCM3-Pulmonary35 | 1 | 1 | Constant case name for a single-study deposit (`round3/modelling_dcm3.py:73`). `_Pulmonary_35` is not touched by the regex. | correct | E#4 |
| Figshare-EpicardialFat-CE | 34 | 34 | `CENNN` = the released file id `Epicardial_{train,test}_CE/CENNN_CE.nrrd` (`ingest_open.py:1173`). There are 40 unique ids, CE001-020 train and CE021-040 test (`round 2/Institutional.json:21,27`). Only the post-contrast series is stored, so there is one volume per id. That an id is a patient is implied, not documented. | correct (assumed id = patient) | 14 S, rest E. No multi-volume keys. |
| HOCMvalvesSeg | 24 | 24 | Integer = released case id `N_image.nii` (`ingest_open.py:644,647`). The set is "27 patients (1 volume each)" (`Asia.json`, `Literature.json`). | correct | none (excluded stratum) |
| IDC-nsclc_radiogenomics | 3 | 2 | 2nd field = DICOM PatientID; 3rd = slug(SeriesDescription)_UID6, with `_pNN` for multi-volume series (`tools/ccta/ingest_idc.py:48,64`). `IDC_T1T2_series.csv`: AMC-015 and AMC-027 each have one study with BestDiast/BestSyst. | correct | AMC-015 = S (1 vol), AMC-027 = E#6 (Diast and Syst grouped) |
| IDC-rider_lung_pet_ct | 69 | 14 | Same as above: 2nd field = PatientID (`ingest_idc.py:48`). `_pNN` sits in the 3rd field, which the heuristic ignores. RIDER-1563443119 comes from `round3/opendata_idc_rider_extra.csv` (same PatientID). **Caveat:** RIDER stores the same people under several RIDER IDs (`agent reports/IDC.json:6-7`, `IDC.md`: "almost every patient appears twice under two different RIDER-IDs"; a pixel-identical pair was confirmed). The manifest kept one ID per known pair, so no known twin ID is in the pool. The IDC agent still estimates "about 12 distinct people, since one 81-year-old woman seems to have 3 studies". | correct by PatientID; **possible under-grouping across IDs** (2522924559 / 2551730224, see the duplicates section) | 6 S (1563443119, 2267469717, 2522924559, 2857227961, 2991299498, 3114425590). 2551730224 = E#79. |
| IDC-varepop_apollo | 9 | 1 | PatientID AP-26JK; one study, 0-100 % multiphase plus BestDiast (`IDC_T1T2_series.csv`). | correct | E#8 (9 vols grouped) |
| (IDC, cross-collection) | — | — | No PatientID appears in two collections (checked over all of `IDC_T1T2_series.csv`). | correct | — |
| ImageALCAPA | 30 | 30 | Integer = released case id `N_image.nii.gz` (`ingest_open.py:601-602`). The set is "30 patients (1 volume each)" (`Asia.json`). | correct within the source; possible overlap with ImageCHD (duplicates section) | none (excluded stratum) |
| ImageCHD | 83 | 83 | `1000+idx` from the xlsx idx = released case id `ct_<id>_image` (`ingest_open.py:501,560`). The set is "110 patients (1 volume each)" (`Asia.json`, `Challenges.json`). | correct within the source | 20 R; no multi-volume keys |
| Kaggle-CAD-RandomSamples | 28 | 28 | `caseNN` = Kaggle folder `data3Dicom/caseNN/` (`ingest_open.py:694-697`); one NIfTI per folder. `Literature.json`: "29 patients (case56-case84), 58 series"; `Repos.json`: case56-84, 2022 studies, InstitutionName erased. | correct (folder = patient per two agent reports; no DICOM PatientID kept in repo) | 12 S, 16 E, one volume each |
| Kaggle-HeartSR | 10 | 10 | `PNN` = Kaggle folder `HeartSR/PNN/HR/` (`ingest_open.py:932-935`). The set is "10 patients" (`:916,927`; `Repos.json`); only the HR series is stored. | correct | 4 S (P04, P05, P08, P09), 6 E |
| Mendeley-9wv3fkxstx | 2 | 1 | `P00001` is a constant set by the ingest (one-patient case report); `_sNNN` = DICOM SeriesNumber 403/404, "two phases" (`ingest_open.py:867-869,905`). | correct | E#11 (both grouped) |
| **Mendeley-SDN-37nnfyh3x9** | 12 | **5** | Record = "A case report of right coronary artery agenesis", **one patient** (`ingest_open.py:1403-1404,1451-1454` "(one patient) … All cases share patient_id"; `:1492` `patient_id=f'SDN-{did}'`; `round 2/Sweep.json`: "1 patient"). `sNNN` = **DICOM SeriesNumber** and `_pNN` = cardiac phase % (`ingest_open.py:1476-1477`). QC also says s004_p60 ≈ s003 and s004_p70 ≈ s302_p82, same patient. | **under-grouped** (5 keys → 1 patient) | S: s004 (5 vols), s303 (2). Leaked: s003 = E#12, s302 = E#28, s301 = E#43 (5 vols) |
| **Mendeley-SDN-4643nn2z44** | 23 | **23** | Record = "A case of coronary arterio-venous fistula", **one patient** (`ingest_open.py:1405-1406,1451-1454,1492`; `Sweep.json` "1 patient (~10 phase series)"). `sNNN` = SeriesNumber. `_fNN` = k-th untagged phase block of series 10 (`ingest_open.py:1418,1476-1477`, frame_note `:1495-1497`). **`_f\d+` is not in the regex**, so every frame is its own key. | **under-grouped** (23 keys → 1 patient) | S: s010_f00, f01, f04, f06, f07, f11, f17, f18, f19, s012 (**10 sealed slots**). Leaked 13 vols: s008 (E#131), s009 (E#92), s010_f02/03/05/08/09/10/12/13/14/15/16 (E#111, 70, 29, 119, 13, 82, 102, 57, 125, 44, 137) |
| **Mendeley-SDN-7x9kb53262** | 23 | **4** | Record = "Case report of coronary artery fistula", **one patient** (`ingest_open.py:1399-1402,1451-1454,1492`; `Sweep.json` "1 patient (multi-phase)"). `s007/8/9/10` = SeriesNumbers; `s010_pNN` = phase % of series 10. | **under-grouped** (4 keys → 1 patient) | S: s009, s010 (20 vols). Leaked: s007 = E#14, s008 = E#30 |
| Mendeley-SDN-cy54ttk3fj | 80 | 40 | `PNN` = patient folder N in both `Diast.zip` and `Sist.zip`; `_diast/_syst` = best-diastolic / best-systolic reconstruction (`ingest_open.py:1359-1369,1387` `patient_id=f'P{pid:02d}'`; `:1349-1352`). The pairing by folder number is supported by the QC csv: diast and syst have identical voxel spacing in 39 of 40 patients, and the 40th (P04) differs only by rounding, 0.28 vs 0.29 mm. Patient-specific in-plane spacing ranges from 0.24 to 0.43 mm. | correct | 17 S, all with both phases inside the seal; rest E. No leak. |
| **Mendeley-SDN-spb25zt2c4** | 34 | **7** | Record = "Multimodality imaging of a cardiac paraganglioma: A case report", **one patient** (`ingest_open.py:1407-1409,1451-1454,1492`; `Sweep.json` "1 patient (CT + MR mixed)"). `sNNN` = SeriesNumber; `_pNN` = phase %. QC also notes s014 "anatomy matches s017" and "closely resembles s013". | **under-grouped** (7 keys → 1 patient) | S: s013, s016, s017. Leaked 31 vols: s009 (E#32), s012 (E#46), s014 ×18 (E#59), s018 ×11 (E#16) |
| SLAWT2016-CT | 9 | 9 | `CT_N` = released file `CT_N.nii` (`round3/modelling_slawt.py:74`). The challenge set is 10 ECG-gated CTAs (`:3-4,62-64`). `_N` is not matched by the regex. | correct (assumed 1 file = 1 patient, as in the challenge) | 4 S (CT_3, 4, 7, 9), 5 E |
| **Slicer-SampleData** | 16 | **16** | `TruncalValve_4DCT_fNN` and `CTCardioSeq_fNN` = frame NN of **one** 4D sequence each: "21 phases" of one adolescent and "10-phase gated cardiac CT" (`ingest_open.py:1107-1120` SLICER table, `:1128`, `:1136,1144`; `patient_id=name` `:1150`). `CTACardio` is a separate sample of undocumented origin (`round 2/Catalogues.json`). `_f\d+` is not in the regex. | **under-grouped** (16 keys → 3 patients: TruncalValve_4DCT, CTCardioSeq, CTACardio) | S: CTACardio, CTCardioSeq_f08, TruncalValve f07/f08/f13/f15/f17. Leaked: CTCardioSeq_f01 (E#48); TruncalValve f00/f01/f04/f05/f09/f14/f16/f19 (E#18, 94, 73, 61, 104, 34, 84, 113) |
| Taiwan-AICUP-CardiacCT | 100 | 100 | `patientNNNN` = HF file name (`ingest_aicup.py:41`). The cohort is "100 patients (0001-0050 train, 0051-0100 test)" (`round 2/Sweep.json`). | correct | 42 S, rest E, one volume each |
| TotalSegmentator-cardiac | 16 | 16 | `sNNNN` = TotalSegmentator image id (`ingest_totalseg.py:22,35-36`). `totalseg_cardiac_ids.json` meta gives only age, sex, institute, study_type, scanner and kVp, with **no patient id**. Whether two image ids can be the same patient is not documented in the repo. | unverifiable at patient level (treated as 1 id = 1 patient) | 7 S, 9 E. Only weak demographic coincidences (duplicates section). |
| VMR-Coronary | 30 | 30 | Field = VMR project Name; a `_k` suffix is added only when a project has several .vti files (`ingest_open.py:787,806`). Only `0149_H_CORO_SVGD_0` has one in the pool, and it is the project's only pool volume. Public `dataset-svprojects.csv` (vascularmodel.com, read 2026-10-19): every pool project has a distinct legacy id (OSMSC `0002_0001…0189_0001`, `O<num>[_year]`, `AKD30xx`, `RCKDxx`). | correct within projects; cross-project same patient unverifiable | 12 S, 15 E. The `_0` suffix is harmless today, but a future `_1` volume of 0149 would be under-grouped. |
| Zenodo-21855641-AtrialFibre | 1 | 1 | `Zvag` = patient folder name; one of six patients, the only one with CT (`ingest_open.py:1249-1251,1254,1263` `patient_id=case`). | correct | E#22 |

## Concrete mis-groupings (exact volumes → corrected patient key)

Corrected keys follow the ingest's own `patient_id` field (`ingest_open.py:1150,1492`).

1. `Mendeley-SDN-37nnfyh3x9__SDN-37nnfyh3x9` (12 volumes, 1 patient). Replaces heuristic keys `__s003`, `__s004`, `__s301`, `__s302`, `__s303`:
   s003; s004_p40, p50, p60, p70, p80; s301_p63, p87; s302_p58, p82; s303_p38, p62.
2. `Mendeley-SDN-4643nn2z44__SDN-4643nn2z44` (23 volumes, 1 patient). Replaces 23 keys:
   s008; s009; s012; s010_f00 … s010_f19 (20 frames).
3. `Mendeley-SDN-7x9kb53262__SDN-7x9kb53262` (23 volumes, 1 patient). Replaces `__s007`, `__s008`, `__s009`, `__s010`:
   s007; s008; s009; s010_p0, p5, p10, p15, p20, p25, p30, p35, p40, p45, p50, p55, p60, p65, p70, p75, p80, p85, p90, p95.
4. `Mendeley-SDN-spb25zt2c4__SDN-spb25zt2c4` (34 volumes, 1 patient). Replaces `__s009`, `__s012`, `__s013`, `__s014`, `__s016`, `__s017`, `__s018`:
   s009; s012; s013; s016; s017; s014_p0, p15, p20, p25, p30, p35, p40, p45, p50, p55, p60, p65, p70, p75, p80, p85, p90, p95; s018_p20, p25, p30, p40, p45, p50, p55, p65, p70, p75, p80.
5. `Slicer-SampleData__TruncalValve_4DCT` (13 volumes, 1 patient): TruncalValve_4DCT_f00, f01, f04, f05, f07, f08, f09, f13, f14, f15, f16, f17, f19.
6. `Slicer-SampleData__CTCardioSeq` (2 volumes, 1 patient): CTCardioSeq_f01, CTCardioSeq_f08.
   (`Slicer-SampleData__CTACardio` stays its own key.)
7. Optional, conservative (evidence medium/weak): merge `IDC-rider_lung_pet_ct__RIDER-2551730224__SS-Cine-30-65-BPM-100CC-240_865880.nii.gz`
   into `IDC-rider_lung_pet_ct__RIDER-2522924559`.

A fix inside the heuristic would be to add `_f\d+` to the suffix regex and, for the four SDN case-report records,
key on the record (or read `patient_id` from the Girder item metadata, which the ingest wrote for every source
that has one). After the fix: 469 patients in total (468 with item 7), 312 primary (311), and 133 distinct
patients in the current 150 sealed keys. Changing the salted draw is the judge's decision. This QC only reports.

Over-grouping found: **none**. Every multi-volume heuristic key that was checked is one patient:
- IDC (PatientID);
- cy54ttk3fj `P<NN>`, supported by the spacing match;
- Mendeley-9wv3fkxstx `P00001`;
- BMC `P1`;
- inside the SDN records, all the `sNNN_pXX` groups, which are phases of the same one patient.

## Cross-source and cross-id duplicate suspicions

Exact copies are ruled out by construction. `tools/ccta/ccta_ingest.py:3,128-130` skips any converted NIfTI
whose sha256 is already in CCTA-Pool. Also, no two of the 675 pool files share a byte size
(`trillium/totalseg/inputs.json`). What remains is "same patient, different file":

| # | Suspicion | Evidence | Strength | Affected |
|---|---|---|---|---|
| 1 | RIDER-2522924559 and RIDER-2551730224 are the same 81-year-old woman | Both are 081Y F. 2522924559 has studies on 2006-04-08 (CCTA) and 2006-04-15 ("TRIPLE RO"); 2551730224 has 2006-05-18 ("CTA CHEST") (`IDC_T1T2_series.csv`). The IDC agent: "Probably about 12 distinct people, since one 81-year-old woman seems to have 3 studies" (`agent reports/IDC.json:6`). RIDER is known to duplicate people under different IDs (`IDC.json:7`). Not pixel-checked. | medium-weak | 2522924559 = S (13 vols); 2551730224 = E#79. Merging costs one extension patient. |
| 2 | ImageALCAPA patients also in ImageCHD | Same hospital, scanner and years, and ALCAPA is a congenital heart disease: "Possible patient overlap with ImageCHD … not checkable" (`agent reports/Asia.json`). ImageCHD's `chd_diagnoses` (with a coronary-anomaly column) is in Girder item metadata, not in the repo, so it could narrow this down. | weak / unverifiable | ImageCHD 20 R; ImageALCAPA is excluded now, but it moves to report_only once its spacing is fixed |
| 3 | Guangdong sets (ImageCHD, ImageALCAPA, HOCMvalvesSeg) overlap ImageCAS (training data, not in the pool) | Same hospital and scanner; the agents say overlap "cannot be ruled out" (`ingest_open.py:38-40` GUANGDONG note; `Asia.json`). HOCM is adults, the same population as ImageCAS. | weak / unverifiable | Leak into the ImageCAS-X training side if these are sealed: ImageCHD R; HOCM later |
| 4 | SDN 7x9kb53262 and SDN 4643nn2z44 are one patient (both SDN coronary-fistula case reports) | Same institution and scanner, but different exam years (2018 vs 2019), kVp (70 vs 110), series layout and QC voxel sizes (0.36×0.36×1.0 vs 0.32/0.64 mm) (`round 2/Sweep.json`). Nothing points to the same person. | weak (topic only) | Both have sealed keys |
| 5 | SDN case-report patients also among the 40 cy54ttk3fj "normal perfusion" patients | Same institution, scanner and protocol (CCT_Retro_FC). Not checkable: no ids or dates were kept. | weak / unverifiable | cy54 17 S; SDN records S |
| 6 | VMR Kawasaki cases repeated across the two KD cohorts (OSMSC 0067-0074 vs AKD/RCKD 0169-0176) | Only age and sex coincide: 0169 (AKD3058, M 18) vs 0174 (RCKD24, M 18); 0068 (M 14) vs 0176 (RCKD26, M 14); 0071 (M 26) vs 0170 (M 28). The legacy ids and source papers differ (`dataset-svprojects.csv`). | weak | 0169 S / 0174 E#51; 0068 S / 0176 not sealed or extended; 0170 S / 0071 E#107 |
| 7 | TotalSegmentator s0936 and s1002 are one patient | Both are 67 M, Basel, SOMATOM Flash, but different study types (heart-thoracic aorta 80 kV vs aortic valve 120 kV) (`totalseg_cardiac_ids.json`). No patient id is released. | weak | s0936 E#115, s1002 E#75 (neither sealed) |
| 8 | Figshare-23057000 PA0/PA1 are one patient | No evidence either way. The two differ in in-plane spacing and blood-pool HU. | unverifiable | PA1 S, PA0 E#2 |
| 9 | Slicer CTACardio is the same patient as CTCardioSeq | Both are undocumented Slicer samples, with different FOV and resolution (0.93×0.93×1.25 chest-abdomen vs 1.15×1.15×2 downsampled heart). | unverifiable, no positive evidence | CTACardio S, CTCardioSeq_f08 S, CTCardioSeq_f01 E#48 |
| 10 | Philips iCT 256 sets (Kaggle-CAD, SLAWT2016, DCM3) overlap | They share a scanner and a 0.4-0.45 mm increment protocol only. Kaggle-CAD studies date from 2022 (`Repos.json`); SLAWT was released in 2016. | none beyond scanner type | — |
| 11 | BMC-BEO2017 and PLOS-Peng2016 (same hospital and group) | `journals_suppdicom.py:34-35`. PLOS is not in the pool. | n/a for this pool | — |

## What remains unverifiable (honest limits)

- **No source-level patient id exists in the repo for these sources:** TotalSegmentator, Kaggle-CAD, CCA200,
  SLAWT, EpicardialFat, Taiwan-AICUP, HOCM, ImageALCAPA, ImageCHD, Figshare-23057000 and Slicer CTACardio.
  "One case id = one patient" rests on the dataset descriptions or the agent reports, not on DICOM PatientIDs.
  The Girder item metadata (`source_ids`, `patient_id`, DICOM tags from `dicom_extra`) was not read here,
  because that needs a token. It may settle some cases, for example whether the Kaggle-CAD folders have
  distinct PatientIDs.
- **The SDN records** are taken as one patient each from the record titles ("a case report") and the ingest's
  `patient_id`. The DICOM PatientID inside the records was not recorded in the repo.
