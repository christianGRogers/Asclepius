# Asia / non-English sources — ranked summary (agent "Asia", 2026-10-12)

**Bottom line:** No new large Chinese CCTA release (2022–2026) has appeared since ImageCAS. The open, new scans in this territory are ImageCAS's sibling datasets from Guangdong Provincial People's Hospital (GDPH) on Kaggle. They are cardiac or aortic CTA, not adult CCTA, and add about 167 new T2 cardiac CTAs (ImageCHD 110 + ALCAPA 30 + HOCM 27), all CC BY-NC 4.0. Asia also has one real T1 cohort, ICADD from India (70 ECG-gated CCTA). It is available on request only.

## Ranked (best first)

1. **ImageCHD**, T2, 110 patients, 8.9 GB, open — https://www.kaggle.com/datasets/xiaoweixumedicalai/imagechd
   Congenital heart disease cardiac CTA, Siemens Definition Flash, 2017–18. Tested: I read the central directory of the last zip part and extracted case 1001. Blood pool is about 530–650 HU, so contrast is confirmed. Caveats: stored values are HU+1024, the NIfTI spacing is a 1 mm placeholder (real spacing is in the xlsx), and the xlsx contains birth and acquisition dates. **CHD68** (https://www.kaggle.com/datasets/xiaoweixumedicalai/chd68-segmentation-dataset-miccai19) is very likely a subset of ImageCHD, so I do not count it separately.
2. **ImageALCAPA**, T2, 30 patients, 2.6 GB, open — https://www.kaggle.com/datasets/xiaoweixumedicalai/imagealcapa
   Includes **LCA/RCA labels**. Tested: contrast peak at about 400 HU. The coronary anatomy is anomalous (ALCAPA) and most patients are children.
3. **HOCMvalvesSeg**, T2, 27 adults, 6.5 GB, open — https://www.kaggle.com/datasets/xiaoweixumedicalai/hocmvalvesseg
   Tested by direct per-file download. Images are **uint8 windowed (no HU)** with placeholder spacing, so they are lossy. Same hospital and scanner as ImageCAS, so some patients could overlap; this cannot be checked.
4. **ICADD (India)**, T1, 70 ECG-gated CCTA (DICOM) with invasive FFR, unlabelled. Available on request from the corresponding author ([contact removed]), possibly with a sub-contract or fee — https://www.medrxiv.org/content/10.1101/2023.05.13.23289934v1. Verified from the preprint full text (Philips Brilliance 64, retrospective gating).
5. **CARE 2024 WHS++ CT**, T2 (CCTA protocol), 104 volumes, about 70 released, registration required — https://www.zmic.org.cn/care_2024/track5/. It probably includes the **MM-WHS** CT set (60, Shanghai, signed DUA, no redistribution) — https://zmiclab.github.io/zxh/0/mmwhs/data.html. The Challenges agent lists both.
6. **Figshare "cardiac ct data_15sets"**, T2, 15 dual-source cardiac CTs from a Chinese university group, **CC BY 4.0**, open — https://figshare.com/articles/dataset/cardiac_ct_data_15sets/1379059. Tested: downloaded 8.rar (72 MB), which holds one registered phase per patient. Intensities are normalised float (not HU) and the volume is cropped to 1 mm slices. Contrast-filled chambers are visible.
7. **ImageTAAD** (120, 26.9 GB) and **ImageTBAD** (100, 13.4 GB), T3 aortic dissection CTA from GDPH, open on Kaggle. I tested TAAD: the scan runs neck to femoral and gating is not documented. The **pulmonary vessel set** (95 patients, Kaggle "mytest") is T3 and I did not verify it.
8. **NTUH CCTA (Taiwan)**, T1, restricted. The sample set is closed to new applications; the formal set goes through review at lions.nchc.org.tw — https://scidm.nchc.org.tw/dataset/ntuh_ccta. NCHC hosts cannot be reached from this sandbox, so this entry rests on search snippets only.
9. **CADx (Pakistan, IEEE DataPort)**, needs a subscription, 223 MB "reconstructed from 2D slices". Probably derivative and of low value — https://ieee-dataport.org/documents/cadx

## Nothing found / duplicates
- **Korean AI-Hub:** I searched the catalogue directly (심장, 관상동맥, 심혈관, 혈관). It has no cardiac or coronary CT; only ECG, echo and 2D carotid CT/MRI, all behind the application-only safe zone.
- **No CCTA image releases found** on ScienceDB (DataCite prefix 10.57760 search), Tianchi, Baidu AI Studio, Gitee or CNGBdb, in either Chinese or English searches. ModelScope and OpenXLab need a login, so those two are not fully checked. Chinese plaque studies with 10k–16k patients (e.g. https://github.com/MEI243/PS-CTA-Plaque-Atlas) keep their images in-house.
- **ImageCAS duplicates:** the Kaggle original, ImageCAS-X, "Awakening ImageCAS" (Zenodo 10.5281/zenodo.23243093, which adds ostium and centreline labels and may help the 14-class labels), and the HyperAI, OpenDataLab, Zhihu and CSDN mirrors. These add no new scans.

## Notes for the project lead
- Every GDPH set is **CC BY-NC 4.0**, so commercial use is barred. Shared derivative labels must carry attribution and the same non-commercial restriction.
- Kaggle per-file downloads worked **without login** today. For bulk download, the proper route is a free Kaggle account and API token (`kaggle datasets download -d xiaoweixumedicalai/<slug>`). After unzipping, rename `*.change2zip` to `*.zip` and run `7z x`.
- Nothing in this territory needed a Chinese phone number. The GDPH sets moved from email or Baidu links to Kaggle in 2023–2025.
