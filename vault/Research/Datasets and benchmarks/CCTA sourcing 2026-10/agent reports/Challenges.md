# Challenges agent: grand-challenge / MICCAI / ISBI / TCIA / Synapse (2026-10-12)

**Bottom line:** challenge datasets are small, and most of the well-known CCTA sets are now gated or gone. Across all challenge, TCIA and Synapse sources I found **~1,250 contrast cardiac CT scans that are new (not ImageCAS)**:
- ~265 are open right now (ImageCHD 110, ALCAPA 30, HOCM 27, CHD68 68 (likely duplicate), TCIA 3, AortaSeg/AVT T3 aside).
- ~600 more need one email or one signature (CARE-LA 300, CARE-WHS 144, MM-WHS 60, orCaScore 72, ASOCA 40+20).

No 2023–2026 MICCAI or ISBI challenge released CCTA images.

## Ranked (best first)

1. **CARE 2026, LA track, Task 3 (CT).** T2, 300 pts. Fuzhou, Siemens Force, 0.3–0.8 mm × 0.5 mm. Labels: LA, PV, LAA. Registration is closed; email [contact removed] / [contact removed]. **Licence is CC BY-NC-ND, and ND blocks sharing new labels; ask for a written exception.** https://www.zmic.org.cn/care_2026/track_leftatrium/
2. **ASOCA.** T1, 40 CCTA (20 normal + 20 CAD), plus 20 test images that are not in the deposit. UK Data Service SN 855916, closed access. The lead registers with UKDS, then emails [contact removed]; ethics evidence may be asked. Licence: UKDS EUL. https://reshare.ukdataservice.ac.uk/855916/ . Kaggle mirrors (ayuuushsri/asoca-dataset, ayushsri2004/asoca-data) look unauthorised; don't use them.
3. **CARE-WHS / Whole Heart (2024–26), CT part.** T2, 144 CT from 5 centres; Center A is probably MM-WHS. Post-challenge requests go to the same emails as item 1. https://www.zmic.org.cn/care_2026/track_wholeheart/
4. **ImageCHD.** T2, 110 congenital-heart CTA (Siemens Flash, 0.75 mm, mostly children). **Open:** anonymous Kaggle API download works, CC BY-NC 4.0, 8.9 GB in a 13-part zip.
   - Tested: last part downloaded, an image extracted, contrast confirmed.
   - The NIfTI files have no voxel spacing (pixdim = 1). Real spacing is in the bundled xlsx.
   - Intensities look like HU+1024.
   - https://www.kaggle.com/datasets/xiaoweixumedicalai/imagechd
5. **orCaScore.** T1, 72 CCTA. Each comes with a non-contrast calcium-scoring scan, which is excluded. Closed to new registrations since Aug 2025; email [contact removed]. https://orcascore.grand-challenge.org/Data/
6. **MM-WHS 2017, CT part.** T2, 60 cardiac CTA. The lead signs the agreement and emails it to [contact removed]; download is from MEGA. The agreement forbids redistributing the data. https://zmiclab.github.io/zxh/0/mmwhs/
7. **ImageALCAPA.** T2, 30 CTA with **LCA/RCA labels**. Open on Kaggle, CC BY-NC, 2.6 GB. Tested: one image extracted, contrast peak about +500 HU. https://www.kaggle.com/datasets/xiaoweixumedicalai/imagealcapa
8. **HOCMvalvesSeg.** T2, 27 adult HOCM cardiac CT. Open on Kaggle, individual .nii files, 1.15 GB.
   - Tested: the data is **8-bit windowed (0–255) with spacing stripped**, so it is not HU.
   - https://www.kaggle.com/datasets/xiaoweixumedicalai/hocmvalvesseg
9. **CHD68.** T2, 68 cases. Kaggle, CC BY-NC. Very likely a subset of ImageCHD, so count it as 0 new.
10. **TCIA.** T2, only 3 patients with gated contrast cardiac CTA, all verified by download: VAREPOP-APOLLO AP-26JK (TAVR protocol) and NSCLC Radiogenomics AMC-015 and AMC-027. These are probably already in IDC.json.
    - I scanned all 156 public NBIA collections. TCIA has no cardiac or coronary collection, and the limited-access collections are head-and-neck or brain.
11. **Collaboration lead: Coronary Atlas (UNSW/Auckland).** Reportedly more than 500 CTCA scans; this is a secondary claim. ASOCA is a subset. Contact [contact removed].
12. **Lost or unavailable:**
    - **CAT08:** 32 CCTA.
    - **Rotterdam 2012 stenosis/lumen challenge:** 48 CCTA. coronary.bigr.nl is dead; ask Erasmus MC (Theo van Walsum).
    - **LASC'13 CT:** 30 scans. figshare has only the MRI part.
    - ZMIC hosts whole-heart *labels* for all three sets, but no images (zips checked).
13. **T3 sources (aortic or chest CTA, low value):**
    - **Open:** ImageTAAD (120, Kaggle, 27 GB), ImageTBAD (100, Kaggle), AVT (56, CC BY 4.0, figshare; only the 18 Dongyang scans are new).
    - **Registration or DUA:** AortaSeg24 (50, DocuSign DUA), SegTHOR (60, contrast mixed).
14. **Excluded:**
    - X-ray angiography (ARCADE, CoronARe).
    - MRI or echo cardiac challenges (CMRxRecon, MBAS, MVSeg, CARE MRI tracks).
    - Synapse: no CCTA image projects found.
    - DTU STACOM-2025 LAA dataset: new labels on ImageCAS, so a **duplicate**.

## What the project lead must do
- **No sign-up or signature needed:** the Kaggle sets (items 4, 7, 8). Download is anonymous; licence is CC BY-NC.
- **Accounts or agreements needed:** UKDS for ASOCA, the MM-WHS agreement, the AortaSeg24 DocuSign.
- **Emails:** CARE (items 1 and 3), orCaScore, Coronary Atlas, Erasmus MC.

All test files were deleted, and sourcing/tmp_Challenges/ is empty. Details and exact URLs for each source are in Challenges.json.
