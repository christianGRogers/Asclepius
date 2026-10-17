# Literature sourcing: CCTA and cardiac CT released through papers (2018–2026)

Agent: Literature. Date: 2026-10-12. Full records are in `Literature.json` (46 entries).

**Method.** I searched Europe PMC (titles, abstracts and full text), Semantic Scholar (rate-limited, so only partly), the Zenodo, figshare, Dryad, Mendeley, Kaggle and Hugging Face APIs, and the web. arXiv's API returned "Rate exceeded" every time, so I reached arXiv papers through web search. I read the data-availability statements of each candidate paper in Europe PMC full text. I used one survey catalogue as a lead list: the CSV of Touray et al. (EJR-AI 2026), https://github.com/gfahrni/open-cardiovasc-imaging-datasets. I then checked each lead on its hosting page.

**Bottom line.** Papers have released very few new, open, ECG-gated CCTA volumes. Beyond ImageCAS and ASOCA, the open ones are small: about 30 in VMR, 29 on Kaggle and about 230 congenital/HOCM cases. The largest new pools need a request or a DUA.

## Ranked: genuinely new scans

| # | Source | Tier | New scans | Access | Verified |
|---|---|---|---|---|---|
| 1 | **Multicenter CCTA report benchmark (CSM_CCTA)**, arXiv 2609.00909. https://openi.pcl.ac.cn/OpenMedIA/CSM_CCTA | T1 | **818 patients / 3,021 series**, 4 Chinese hospitals | On request: email [contact removed] | Read paper and README |
| 2 | **MultiD4CAD** (Sci Data 2025). https://zenodo.org/records/15148653 | T1 (gated, Siemens AS+) | 118 | DUA + Zenodo access request, about 2 working days | Read paper and record |
| 3 | **ASOCA** (UK Data Service). https://reshare.ukdataservice.ac.uk/855916/ | T1 | 60 (40 labelled + 20 test) | Email [contact removed], then UKDS registration | Read both pages |
| 4 | **WHS++ (CARE 2024)**. https://www.zmic.org.cn/care_2024/track5/ | T2/T1 (coronary-CTA protocol) | 104 CT, 70 released; probably includes MM-WHS's 60 | Registration + signed agreement PDF | Read page |
| 5 | **MM-WHS CT**. https://zmiclab.github.io/zxh/0/mmwhs/ | T2 | 60 | Signed form, then MEGA link | Read page |
| 6 | **Vascular Model Repository (VMR)**. https://www.vascularmodel.com/dataset.html | T1/T2 | 31 coronary CT (Kawasaki, CAD, vein grafts); also 40 aorta CT and 30 pulmonary CT | **Open download** | **Tested** |
| 7 | **ImageCHD** (110) and **CHD68** (68, probably overlaps ImageCHD). https://www.kaggle.com/datasets/xiaoweixumedicalai/imagechd | T2 (congenital) | about 110 | Open download (Kaggle API, no login) | File list only (split zip over 2 GB) |
| 8 | **ImageALCAPA**. https://www.kaggle.com/datasets/xiaoweixumedicalai/imagealcapa | T2 | 30 (labels include LCA/RCA) | Open download | File list only |
| 9 | **HOCMvalvesSeg**. https://www.kaggle.com/datasets/xiaoweixumedicalai/hocmvalvesseg | T2 | 27 | Open download | **Tested**; stored as **uint8 windowed, not HU** |
| 10 | **Kaggle "Coronary Artery Diseases Random Samples"**. https://www.kaggle.com/datasets/younesselbrag/cases-coronaries-altries-diseases-cases-ct | T1 (Philips iCT 256 coronary CTA) | 29 patients / 58 series | Open download (CC0 claimed, provenance unknown) | **Tested** |
| 11 | **Coronary Atlas** (UNSW/Auckland). https://www.unsw.edu.au/research/svmg/research/coronary-atlas | T1 | Unknown; possibly hundreds (ASOCA is a subset) | On request: [contact removed], with ethics approval | Read page |
| 12 | Other on-request leads | T1 | 70 to 1,642 | Mostly on request | Read statements |

The other on-request leads in row 12:

- **AAOCA Bern/Zurich.** Contact Dr C. Gräni. Approval can take up to one year.
- **ICADD.** 70 CCTA with FFR. Contact S. Ansumali at JNCASR.
- **CCA-200.** 200 cases. No link has been published.
- **orCaScore.** 72 paired CCTA + calcium-score CT. Closed to new registrations since August 2025.
- **CAT08 / CLS12 (Rotterdam).** 32 and 48 CCTA. The site is dead; contact Erasmus MC.
- **Linköping 4D-CT.** On request from the corresponding author.
- **TUM plaque cohort.** 1,642 CCTA, but access is on-site in Munich only.

## Tested download recipes (all files deleted afterwards)

- **VMR.** `curl -O https://www.vascularmodel.com/svprojects/0066_H_CORO_H.zip` (316 MB). The image is in `Images/*.vti`; read it with `vtk.vtkXMLImageDataReader`.
  - Spacing is stored in **cm**.
  - Result: 512×512×276, 0.39×0.39×0.5 mm, HU −1024 to 1976, aorta about 500 HU. Contrast cardiac CTA confirmed visually.
  - To list the cases: `https://www.vascularmodel.com/dataset/dataset-svprojects.csv`, filtered to Anatomy=Coronary and Images=1.
- **Kaggle single file, no login.** `curl -L -o f https://www.kaggle.com/api/v1/datasets/download/<owner>/<dataset>/<url-encoded path>`.
  - HOCM `17_image.nii`: 512×512×378 uint8, contrast cardiac CTA.
  - younesselbrag `case56/.../IMG100`: Coronary CTA protocol, iodine, 0.9 mm, 99th percentile 518 HU.
  - The whole-dataset endpoint redirects (302) to a signed GCS URL.
- **3C COVID cardiac CT.** Downloaded the 372 MB RAR from Zenodo. It is a pulmonary-phase "ANGIO THORACIQUE" scan, so **T3**.

## Duplicates of ImageCAS or MM-WHS (no new scans)

These add labels only, but several are useful for 14-class work:

- **ImageCAS-X:** 800 cases with lumen, segments and centrelines. https://zenodo.org/records/21887809
- **Hansen et al. LAA/10-class labels:** covers all of ImageCAS. https://github.com/Bjonze/Public-Cardiac-CT-Dataset
- **Awakening ImageCAS:** ostia and centrelines. https://zenodo.org/records/23243094
- **Bi-Atrial Model Repository:** https://zenodo.org/records/21900735
- **Mirrors and re-uploads:**
  - Kaggle "3D CAS Images": 200 ImageCAS cases re-licensed as Apache-2.0.
  - Hugging Face AI-CVM/Cardiac-CT: ImageCAS + MM-WHS.
  - Hugging Face jethro682/imagecas.
  - Kaggle ASOCA mirrors: unauthorised, do not use.
- The "public dataset" cited by the AAOCA paper is TotalSegmentator, not CCTA.

## Low value or excluded

- **2D-only releases.**
  - Mendeley Ohio State: 500 patients, but only straightened-artery mosaic images.
  - Dryad/Kaggle Baskaran: 206 patients, released as PNG overlays.
- **T3 (counts only).** 3C (134), ImageTBAD (100), ImageTAAD (120), AVT (56), AortaSeg24 (100), and the PE sets: RSPECT, INSPECT, RadFusion, FUMPE.
- **Excluded.**
  - Zenodo "Aortic Root Segmentation for TAVI": tested, and it is fluoroscopy, not CT.
  - Stanford COCA: non-contrast.
  - Bujny et al.: non-contrast.
  - Coronary microvascular disease set: PET/CT, no CCTA.
  - OneMedNet: commercial vendor.
  - ARCADE and similar: X-ray angiography.

## What the project lead must sign or send

These are listed in order of value.

1. Email [contact removed] to ask for the CSM_CCTA benchmark (818 patients).
2. MultiD4CAD:
   - Sign the DUA at https://zenodo.org/records/15063937.
   - Email it with the subject "MultiD4CAD Request access".
   - Request access on https://zenodo.org/records/15148653.
3. ASOCA: email [contact removed], then register with the UK Data Service.
4. WHS++: register at http://zmic.org.cn/care_2024/eval/register?track=WHS%2B%2B and upload the signed agreement. Alternatively, sign the MM-WHS form.
5. Coronary Atlas: email [contact removed] with ethics approval.
6. Optional:
   - Gräni (AAOCA, slow).
   - Ansumali (ICADD).
   - orCaScore and Erasmus MC organisers, for old challenge data.

Licences: everything from the Xu lab on Kaggle (ImageCHD, ImageALCAPA, HOCM, ImageTBAD, ImageTAAD) is **CC BY-NC 4.0**. VMR allows research and development use with attribution. The younesselbrag set claims CC0, but its legal provenance is unknown, so the lead should check it before shared labels go out on it.
