# Repos agent: general data repositories (2026-10-12)

Searched: Zenodo API, Figshare API, Mendeley Data API, Dryad, OSF, Harvard Dataverse, Hugging Face datasets API, Kaggle (unauthenticated list/view API, 50+ queries), PhysioNet (all 737 projects), Academic Torrents (full database.xml), AWS Open Data Registry (repo YAMLs), GitHub (repo search plus dataset-list repos). Full details are in `Repos.json`.

**Main finding:** there are about 110 genuinely new T1 CCTA scans that can be downloaded openly today. Two are new independent Kaggle uploads (38 patients). The rest are mirrors of known challenge sets (CAT08 32, ASOCA 40). Another roughly 170 T2 scans come from the Guangdong group (ImageCHD 110, ImageALCAPA 30, HOCM 27), plus MM-WHS 60.

**Kaggle download trick (verified):** single files download without an account:
`curl -L "https://www.kaggle.com/api/v1/datasets/download/<owner>/<slug>/<urlencoded path>"`. Large files arrive wrapped in a zip. File lists come from `.../api/v1/datasets/list/<owner>/<slug>?pageSize=200`.

## Ranked (best first)

1. **Coronary Artery Diseases Random Samples** (T1, about 28 complete CCTA studies, 5.1 GB DICOM, CC0)
   - https://www.kaggle.com/datasets/younesselbrag/cases-coronaries-altries-diseases-cases-ct
   - Tested: Philips iCT 256, "Coronary CTA 90-120KG /Cardiac", 0.9 mm, 40% phase, iodine, about 600 HU.
   - Institution unknown. New, not ImageCAS.
2. **HeartSR cardiac-ct-lr-hr** (T1, 10 patients, 2.7 GB DICOM, licence unknown)
   - https://www.kaggle.com/datasets/victorsix/cardiac-ct-lr-hr
   - Tested: Siemens SOMATOM Force, 0.6 mm retrospective ECG-gated CCTA, Italy, 2025, 862 HU.
   - Each patient has HR and LR series, so count 10, not 20.
3. **CAT08 Rotterdam** (T1, 32 CCTA, mhd/raw, 4.9 GB), Kaggle mirror inside https://www.kaggle.com/datasets/apette/heart-data
   - Tested: dataset00, 0.36 mm, about 420 HU.
   - The mirror's licence is unknown. The official route needs registration at http://coronary.bigr.nl/centerlines/.
4. **ASOCA** (T1, 40 CCTA, NRRD, 4.2 GB), Kaggle mirrors (apette/heart-data, ayuuushsri/asoca-dataset)
   - Tested: Normal_1, 469 HU.
   - ASOCA's own terms forbid third-party sharing, so use https://asoca.grand-challenge.org for anything shared.
5. **ImageCHD** (T2, 110 congenital CTA, 8.9 GB, CC BY-NC), https://www.kaggle.com/datasets/xiaoweixumedicalai/imagechd
   - Official author upload, split zip.
   - Tested one volume from the last part: contrast about 600 HU, but voxel spacing is lost in the header.
   - CHD68 is very likely a subset. Same hospital as ImageCAS but a different cohort.
6. **ImageALCAPA** (T2, 30 CTA with LCA/RCA labels, 2.6 GB, CC BY-NC), https://www.kaggle.com/datasets/xiaoweixumedicalai/imagealcapa
   - Tested one volume (contrast confirmed, spacing lost). Anomalous coronary origins.
7. **MM-WHS CT** (T2, 60, NIfTI, about 6 GB of CT), Kaggle mirrors, e.g. https://www.kaggle.com/datasets/mohammadmohaisen/mm-whs-2017-dataset
   - Tested ct_test_2001: 0.45/0.625 mm, 682 HU. The original requires registration.
8. **HOCMvalvesSeg** (T2, 27, CC BY-NC), https://www.kaggle.com/datasets/xiaoweixumedicalai/hocmvalvesseg
   - Tested: contrast confirmed, but stored as 8-bit windowed images (HU lost) with 1 mm header spacing.
9. **Single cases:** Mendeley 9wv3fkxstx (1 CCTA, CC BY, tested) https://data.mendeley.com/datasets/9wv3fkxstx/1, and the OsiriX DIASTOLIX sample (1 patient, tested) https://www.kaggle.com/datasets/grantmcnatt/cardiac-ct-dicom-dataset.
10. **Needs a DUA or access request** (project lead must request; I did not request anything):
    - MultiD4CAD, 118 cardiac CT with EAT/PAT labels: https://zenodo.org/records/15148653 (DUA on the record)
    - CorA "coronary artery labeling": https://zenodo.org/records/18603892 (restricted, contents unknown, could be an ImageCAS derivative)
11. **T3 (counts only, not chased):**
    - 3C Cardiac-CT-COVID19: about 134 patients, tested, non-gated CTPA, 44 GB, CC BY. https://zenodo.org/records/10801492
    - RSNA PE: more than 12k CTPA (AWS / Kaggle, non-commercial, no redistribution).
    - CT-RATE: about 25k chest CT (HF, gated).
    - Aortic sets: AortaSeg-60, Graz dissection (40), ImageTBAD (100), AVT (56).
    - TotalSegmentator / TAVRP-PL (578).

## Duplicates and non-data (do not count)
- **ImageCAS derivatives:** ImageCAS-X, Awakening ImageCAS, Bi-Atrial (Zenodo), HF AI-CVM/Cardiac-CT (973 ImageCAS images, gated), HF jethro682/imagecas, Kaggle ImageCAS splits (shakthipraveen, balaabinav27, jauadahmedsadik, rj1007, ahmedreda1609), and ahanafabidsazid/3d-cat-images (presumed ImageCAS, 135 GB, not opened).
- **No usable CT volumes:**
  - Figshare 30688691: labels and centerlines only.
  - Zenodo/Dryad 3863028: 206-patient CCTA, but only sparse 2D PNG overlays.
  - Mendeley fk6rys63h9: 2D MPV images.
  - Meshes and surface models: Zenodo 3890034, 4590294, 10579450; Mendeley kxfbxpfbrg.
  - SCAPIS heart-age saliency maps (Zenodo 13832059).
- **Nothing relevant found:** OSF, Harvard Dataverse, PhysioNet, Academic Torrents, Dryad (beyond the duplicate above), AWS (apart from RSNA PE). Google/IDC was left to the TCIA agent.

## Licence cautions for shared annotations
- Kaggle mirrors of CAT08, ASOCA and MM-WHS have unclear or violated redistribution terms. Get those through the official registrations.
- The Guangdong sets are CC BY-NC, so non-commercial labels only.
- The two new Kaggle T1 sets are CC0 (provenance unverified) and licence-unknown.

All test files were deleted; `sourcing/tmp_Repos/` is empty.
