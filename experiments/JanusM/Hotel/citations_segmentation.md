# Verified literature: segmentation / data / geometry side
(LV-myocardium layer segmentation on cardiac CT: stenosis diagnosis and scar)

Compiled 2026-10-30. How each entry was checked:
- **Metadata** (title, journal, volume, pages, DOI) was checked against the Crossref API (`api.crossref.org/works/<doi>`) and/or the PubMed E-utilities record.
- **Numbers** were read from the abstract, or from the full-text PDF where I extracted it locally (arXiv). The location is given for every number.
- **Not reachable:** ahajournals.org (Circulation) returned HTTP 403, so the Cerqueira statement's body text is **not** quoted (see the UNVERIFIED section).

---

## 1. Whole-heart / myocardium CT segmentation benchmarks and datasets

### 1.1 MM-WHS challenge paper
Zhuang X, Li L, Payer C, Štern D, Urschler M, et al. Evaluation of algorithms for Multi-Modality Whole Heart Segmentation: an open-access grand challenge. *Medical Image Analysis* 2019;58:101537.
- **DOI / arXiv:** 10.1016/j.media.2019.101537 (Crossref verified); arXiv:1902.07880
- **Opened:** https://arxiv.org/pdf/1902.07880 (full text extracted)
- **Numbers:**
  - 120 volumes in total: 60 CT and 60 MRI (abstract).
  - 10 CT algorithms and 11 MRI algorithms were evaluated, from 12 groups (abstract).
  - Split: training 20 CT + 20 MRI; test 40 CT + 40 MRI. Only the test *images* were released (Sec. 2.3).
  - CT came from two 64-slice Philips scanners (CCTA protocol, two sites in Shanghai). In-plane resolution 0.78×0.78 mm, average slice thickness 1.60 mm (Sec. 2.1).
  - Seven labelled structures: LV, RV, LA, RA, LV myocardium (Myo), AO, PA (Sec. 2.2).
  - Manual labelling took about 6–10 h per image (Sec. 2.2).
  - **CT whole-heart Dice (Table 4):** GUT 0.908 ± 0.086 (best), KTH 0.894 ± 0.030, CUHK1 0.890 ± 0.049, CUHK2 0.886 ± 0.047, UCF 0.879 ± 0.079, SEU (multi-atlas) 0.879 ± 0.023. Average over all CT methods: 0.872 ± 0.087.
  - Mean WHS Dice of all evaluated methods (Sec. 5.1): 0.872 ± 0.087 for CT, higher than for MRI (0.824).
- **Caveat:** per-structure **Myo Dice for CT is shown only as boxplots (Fig. 4)**. No table gives a numeric Myo-only CT Dice. Fig. 6 prints the median-case and worst-case WHS Dice per team, e.g. GUT median case 0.912. Do not quote a "Myo Dice" from this paper.
- **Use for the plan:** the canonical CT benchmark with LV-myocardium labels (label value 205). Use it for the 20-train / 40-test framing and as the WHS Dice ceiling (~0.91) that a layer model must not degrade.

### 1.2 MM-WHS data terms (dataset homepage)
- **Opened:** https://zmiclab.github.io/zxh/0/mmwhs/data.html and https://zmiclab.github.io/zxh/0/mmwhs/ (raw HTML fetched)
- **Terms, quoted from the page:**
  - "The Recipient(s) commit to not disseminate the Data to any third party."
  - Download requires that you "agree with the conditions above and the terms in the registration form (please sign the form and send to the organizers.)". The form is `res/Data_Access_Agreement_for_Participants.pdf`.
  - Banner: "Maintainance of MMWHS has been ended. Please refer to latest event in CARE for more data."
- **Data page numbers:**
  - 60 CT/CTA + 60 MRI.
  - Training split described as "20 CT and 20 MRI representative"; test split 40 CT + 40 MRI.
  - Label values: LV 500, RV 600, LA 420, RA 550, **Myo 205**, AO 820, PA 850.
- **Required citations listed on the page:** [1] Zhuang 2019 TPAMI and [2] Zhuang & Shen 2016 MedIA (entries 1.3 and 1.4).
- **Use for the plan:** a signed agreement is required, redistribution is prohibited, and the dataset is no longer maintained. The plan must not redistribute derived layer labels made from MM-WHS images.

### 1.3 Zhuang & Shen 2016 (original MM-WHS-era atlas paper)
Zhuang X, Shen J. Multi-scale patch and multi-modality atlases for whole heart segmentation of MRI. *Medical Image Analysis* 2016;31:77–87.
- **DOI:** 10.1016/j.media.2016.02.006 (Crossref verified; also linked from the MM-WHS data page)
- **Numbers:** none extracted.
- **Use for the plan:** a required citation when using MM-WHS data.

### 1.4 Zhuang 2019 TPAMI
Zhuang X. Multivariate mixture model for myocardial segmentation combining multi-source images. *IEEE TPAMI* 2019;41(12):2933–2946.
- **DOI:** 10.1109/TPAMI.2018.2869576 (Crossref verified)
- **Numbers:** none extracted.
- **Use for the plan:** a required citation for MM-WHS, and also for MyoPS/CARE data.
- **Note:** the brief called this "Zhuang 2016 TPAMI". The TPAMI paper is 2019. The 2016 paper is the MedIA paper in 1.3.

### 1.5 CARE 2026 whole-heart track (successor to MM-WHS)
- **Opened:**
  - https://www.zmic.org.cn/care_challenges/
  - https://zmic.org.cn/care_2026
  - https://www.zmic.org.cn/care_2026/track_wholeheart/
- **Numbers (track page, data table):**

  | Split | CT | MRI |
  |---|---|---|
  | Training | 60 (centres A, B, G; 20 each) | 46 |
  | Validation | 30 | 20 |
  | Test | 54 (A 20, B 14, H 20) | 36 |

  - Same 7 labels and values as MM-WHS (Myo = 205).
  - Rules: "Only automatic methods are acceptable". External data is allowed only if it was public before 10 July 2026.
  - **No data licence is stated.** Registration is closed. Post-challenge access is gated (D19: the lead's, outside the repository).
  - Required citations: Zhuang 2016, Zhuang 2019, Gao 2023 (BayeSeg).
- **Modality clarification:**
  - CARE-Whole Heart is **CT + MRI**.
  - CARE-Myocardium (https://www.zmic.org.cn/care_2026/track_myocardium/) is **MRI only**: multi-sequence CMR (bSSFP cine, LGE, T2) for MyoPS and cine-only for CineMyoPS. Labels: scar 2221, edema 1220, LV 500, myocardium 200, RV 600.
  - MyoPS cases: training 220, validation 15, test 65. CineMyoPS: training 64, validation 15, test 45. These counts are my sums from the track page's data tables.
- **Use for the plan:** the largest current multi-centre CT set with LV-Myo labels (60 training CT). Access is by request and no licence is stated, so do not assume it can be redistributed. Its scar labels are CMR, not CT.

### 1.6 TotalSegmentator (v1 paper)
Wasserthal J, Breit H-C, Meyer MT, Pradella M, Hinck D, et al. TotalSegmentator: robust segmentation of 104 anatomic structures in CT images. *Radiology: Artificial Intelligence* 2023;5(5):e230024.
- **DOI / arXiv:** 10.1148/ryai.230024 (Crossref verified); arXiv:2208.05868
- **Opened:** https://arxiv.org/pdf/2208.05868 (full text extracted)
- **Numbers:**
  - 1204 CT examinations; 104 structures (27 organs, 59 bones, 10 muscles, 8 vessels) (abstract).
  - Test Dice 0.943; 0.932 vs 0.871 against another public model (abstract).
  - Application set of 4004 whole-body CTs (abstract).
  - The v1 class list includes heart myocardium, heart atrium left/right, heart ventricle left/right and pulmonary artery (Supplement S1).
- **Important caveats (Supplement S3):** the heart subpart labels came from an **in-house model**. It was trained on contrast CT, its labels were transferred to registered native CT, and it was then used to predict heart subparts in the TotalSegmentator dataset. These labels are model-derived, not expert manual labels. The paper also lists, as a typical failure, that "heart subpart segmentation is inaccurate for native images" (Supplement S6). Per-class heart Dice appears only as a bar chart (Fig. S1), with no numeric table, so **no heart-specific Dice can be quoted**.
- **Use for the plan:** a pre-trained LV-myocardium prior or initialiser. Do not use its heart labels as layer ground truth.

### 1.7 TotalSegmentator dataset licence and the v2 heartchambers_highres task
- **Opened:**
  - Zenodo API: https://zenodo.org/api/records/6802614, …/10047292, …/6802613
  - README: https://raw.githubusercontent.com/wasserth/TotalSegmentator/master/README.md
  - Task details: …/resources/heartchambers_highres_details.md
- **Zenodo records:**

  | Record | Version | Contents | Licence | Date |
  |---|---|---|---|---|
  | 6802614 | v1.0 | "104 important anatomical structures in 1204 CT images" | CC BY 4.0 | 2022-07-06 |
  | 10047292 | v2.0.1 | 117 structures, 1228 CT | CC BY 4.0 | 2023-10-27 |
  | 6802613 (concept DOI cited in the paper) | resolves to v3.0.0 (record 22688904) | 117 structures, 1939 CT | CC BY 4.0 | 2026-09-10 |

- **README findings:**
  - The `total` task is Apache-2.0. In the v2 class table, `heart` is a single class (class 51).
  - **heartchambers_highres** (myocardium, atrium_left, ventricle_left, atrium_right, ventricle_right, aorta, pulmonary_artery) is listed under "Available with a license (free licenses available for non-commercial usage …; for a commercial license contact …)". A key is set with `totalseg_set_license`.
- **heartchambers_highres details page:**
  - 1559 training images (1502 training, 57 validation), built from paired contrast and non-contrast scans with labels transferred by registration.
  - Resolution 0.7265625 × 0.72265625 × 1.0 mm.
  - "Dice across all classes on the validation set: 0.950".
- **Use for the plan:**
  - The CC BY 4.0 data permits redistribution of derived labels, with attribution.
  - The sub-mm myocardium model needs an academic licence key and a separate commercial licence.
  - Its 0.950 Dice is averaged over all classes, not myocardium-specific.

### 1.8 ImageCHD
Xu X, Wang T, Zhuang J, Yuan H, et al. ImageCHD: a 3D computed tomography image dataset for classification of congenital heart disease. MICCAI 2020, LNCS, pp. 77–87.
- **DOI / arXiv:** 10.1007/978-3-030-59719-1_8 (Crossref verified); arXiv:2101.10799
- **Opened:**
  - https://arxiv.org/pdf/2101.10799v2 (full text)
  - GitHub README: https://raw.githubusercontent.com/XiaoweiXu/ImageCHD-A-3D-Computed-Tomography-Image-Dataset-for-Classification-of-Congenital-Heart-Disease/master/README.md
- **Numbers:**
  - 110 3D CT images (abstract). Siemens Biograph 64. Ages 1 month to 40 years, mostly 1 month to 2 years.
  - Image size 512×512×(129–357); typical voxel size 0.25×0.25×0.5 mm³.
  - 16 CHD types (Sec. 3).
  - Seven labelled substructures: LV, RV, LA, RA, Myo, AO, PA. The README label map gives myocardium = label 5.
  - Each image was segmented by a single radiologist, taking about 1–1.5 h (Sec. 3).
  - Baseline Dice (Table 3): LV 77.7, RV 74.6, LA 77.9, RA 81.5, great vessels 66.5, blood pool 86.5 (%). **Myo is not reported separately.**
- **Licence:** **none stated** in the README. Access is a link/password requested by email; since 2023-11-01 it is also hosted on Kaggle.
- **Use for the plan:** a paediatric/CHD out-of-distribution myocardium test set only. Its anatomy and voxel size are atypical for adult stenosis and scar work, and its licence is unclear.

### 1.9 nnU-Net
Isensee F, Jaeger PF, Kohl SAA, Petersen J, Maier-Hein KH. nnU-Net: a self-configuring method for deep learning-based biomedical image segmentation. *Nature Methods* 2021;18(2):203–211.
- **DOI:** 10.1038/s41592-020-01008-z (Crossref + PubMed verified)
- **Opened:** PubMed record (efetch)
- **Numbers:** surpasses most existing approaches on 23 public datasets (abstract).
- **Use for the plan:** the default baseline and backbone for the layer-segmentation model.

---

## 2. Deep-learning LV-myocardium segmentation on CCTA

### 2.1 Zreik et al. 2018
Zreik M, Lessmann N, van Hamersvelt RW, Wolterink JM, Voskuil M, Viergever MA, Leiner T, Išgum I. Deep learning analysis of the myocardium in coronary CT angiography for identification of patients with functionally significant coronary artery stenosis. *Medical Image Analysis* 2018;44:72–85.
- **DOI:** 10.1016/j.media.2017.11.008 (Crossref + PubMed, PMID 29197253)
- **Opened:** PubMed abstract (efetch)
- **Numbers (abstract):**
  - 166 patients with invasive FFR.
  - LV-myocardium segmentation evaluated in 20 images: **Dice 0.91**, mean absolute boundary distance 0.7 mm.
  - 20 CCTA scans trained the autoencoder; classification was run on the remaining 126 (10-fold CV repeated 50×).
  - AUC 0.74 ± 0.02. Specificity 0.77 / 0.71 / 0.59 at sensitivity 0.60 / 0.70 / 0.80.
- **Use for the plan:** the direct precedent that rest-CCTA myocardium alone carries an FFR signal, plus the CT LV-myo Dice ≈ 0.91 reference.

### 2.2 van Hamersvelt et al. 2019 (clinical follow-up)
van Hamersvelt RW, Zreik M, Voskuil M, Viergever MA, Išgum I, Leiner T. Deep learning analysis of left ventricular myocardium in CT angiographic intermediate-degree coronary stenosis improves the diagnostic accuracy for identification of functionally significant stenosis. *European Radiology* 2019;29(5):2350–2359.
- **DOI:** 10.1007/s00330-018-5822-3 (PubMed PMID 30421020; PMCID PMC6443613)
- **Numbers (abstract):**
  - 126 patients; 64% had functionally significant stenosis.
  - AUC 0.76 (DS + deep-learning LVM) vs 0.68 (DS only).
  - Specificity 48.4% vs 31.1%; sensitivity 84.6% vs 92.6%.
- **Use for the plan:** shows the added value of myocardium analysis over stenosis grading in intermediate lesions.

### 2.3 Baskaran et al. 2020, JACC Cardiovascular Imaging (chambers + LV myocardial mass)
Baskaran L, Maliakal G, Al'Aref SJ, et al. Identification and quantification of cardiovascular structures from CCTA: an end-to-end, rapid, pixel-wise, deep-learning method. *JACC Cardiovasc Imaging* 2020;13(5):1163–1171.
- **DOI:** 10.1016/j.jcmg.2019.08.025 (PubMed PMID 31607673)
- **Numbers (abstract):**
  - 166 patients; 70:20:10 split.
  - **LV myocardium (LVM) median Dice 0.920 (IQR 0.811–0.944)**; overall median Dice 0.9246.
  - LVM r = 0.94; mean difference 6.41 g (95% CI −8.71 to 21.52).
- **Use for the plan:** a second independent CT LV-myo Dice ≈ 0.92 reference. Its wide IQR (lower quartile 0.81) argues for per-case QC.

### 2.4 Baskaran et al. 2020, PLOS ONE (the paper named in the brief)
Baskaran L, Al'Aref SJ, Maliakal G, et al. Automatic segmentation of multiple cardiovascular structures from cardiac computed tomography angiography images using deep learning. *PLOS ONE* 2020;15(5):e0232573.
- **DOI:** 10.1371/journal.pone.0232573 (Crossref + PubMed PMID 32374784)
- **Numbers (abstract):**
  - 206 patients.
  - Overall median Dice 0.820. RV wall 0.685; LA wall 0.625; coronary sinus 0.720.
- **Caveat:** this paper does **not** segment the LV myocardium. Its structures are aorta, SVC/IVC, PA, coronary sinus, RV wall and LA wall. Cite 2.3 instead for LV myo.
- **Use for the plan:** evidence that thin walls (RV and LA walls, Dice 0.63–0.69) are much harder than the LV myocardium. This is relevant to thin sub-layers.

### 2.5 Bruns et al. 2022
Bruns S, Wolterink JM, van den Boogert TPW, et al., Išgum I. Deep learning-based whole-heart segmentation in 4D contrast-enhanced cardiac CT. *Computers in Biology and Medicine* 2022;142:105191.
- **DOI:** 10.1016/j.compbiomed.2021.105191 (PubMed PMID 35026571)
- **Numbers (abstract):**
  - 1509 TAVI patients (21,605 3D images). Development set 12, test set 1497.
  - Mean Dice 0.89 ± 0.10 (3D, 12 patients) and 0.89 ± 0.08 (2D, 81 patients).
  - Rated "clinically useful" (grade 1) in 98.5% of cases for LV cavity and myocardium.
- **Use for the plan:** evidence that very few dense labels (12) plus large-scale visual QC can scale. This is a template for a label-efficient layer-annotation protocol.

---

## 3. Segment models and coronary-territory assignment

### 3.1 AHA 17-segment statement (metadata verified; body text not opened)
Cerqueira MD, Weissman NJ, Dilsizian V, Jacobs AK, Kaul S, Laskey WK, Pennell DJ, Rumberger JA, Ryan T, Verani MS; AHA Writing Group on Myocardial Segmentation and Registration for Cardiac Imaging. Standardized myocardial segmentation and nomenclature for tomographic imaging of the heart. *Circulation* 2002;105(4):539–542.
- **DOI:** 10.1161/hc0402.102975 (Crossref verified)
- **Co-publication:** *Int J Cardiovasc Imaging* 2002;18(1):539–42 (PubMed PMID 12135124).
- **Opened:** Crossref and PubMed only. The ahajournals full text returned HTTP 403.
- **Use for the plan:** the standard for reporting per-segment layer metrics. See UNVERIFIED for its territory text.

### 3.2 Ortiz-Pérez et al. 2008 (17-segment vs. culprit artery, CMR)
Ortiz-Pérez JT, Rodríguez J, Meyers SN, Lee DC, Davidson C, Wu E. Correspondence between the 17-segment model and coronary arterial anatomy using contrast-enhanced cardiac magnetic resonance imaging. *JACC Cardiovasc Imaging* 2008;1(3):282–293.
- **DOI:** 10.1016/j.jcmg.2008.01.014 (PubMed PMID 19356440)
- **Numbers (abstract):**
  - 93 post-MI patients after primary PCI.
  - **23% of hyperenhanced segments were discordant with the empirically assigned coronary distribution.**
  - Four segments (basal anteroseptal, mid-anterior, mid-anteroseptal, apical anterior) were 100% specific for LAD.
  - No segment was 100% specific for RCA or LCx. Basal anterolateral was 98% specific for LCx.
  - Background states that standardized assignment "is currently based on empirical assumptions".
- **Use for the plan:** quantitative justification for patient-specific territories instead of fixed AHA mapping.

### 3.3 Pereztol-Valdés et al. 2005 (SPECT during balloon occlusion)
Pereztol-Valdés O, Candell-Riera J, Santana-Boado C, et al. Correspondence between left ventricular 17 myocardial segments and coronary arteries. *European Heart Journal* 2005;26(24):2637–2643.
- **DOI:** 10.1093/eurheartj/ehi496 (PubMed PMID 16183694)
- **Numbers (abstract):**
  - 50 patients: 24 LAD, 15 RCA, 11 LCx.
  - Only 9 of 17 segments corresponded to a single artery: 8 to LAD, 1 (basal anterolateral) to LCx.
  - No segment could be attributed exclusively to the RCA.
  - Inferoseptal segments: LAD or RCA. Inferior and inferolateral: RCA or LCx. Mid-anterolateral: LAD or LCx.
- **Use for the plan:** a second independent modality confirming the ambiguity of territory assignment.

### 3.4 Termeer et al. 2009 (patient-specific Voronoi territories from CT/MRI)
Termeer M, Oliván Bescós J, Breeuwer M, Vilanova A, Gerritsen F, Gröller E, Nagel E. Patient-specific coronary artery territories. SCMR 2009 abstract no. 999 (*J Cardiovasc Magn Reson* supplement; supplement page not verified).
- **Opened:** https://www.cg.tuwien.ac.at/research/publications/2009/termeer-2009-scmr/termeer-2009-scmr-abstract.pdf (text extracted)
- **Method:** the LAD, LCx and RCA centrelines are projected onto the epicardial mesh, and a "Voronoi diagram … using a Euclidean geodesic distance metric" gives the territories.
- **Numbers:** in-house evaluation on 5 subjects only. Qualitative: one clinician preferred the patient-specific map.
- **Quote:** the AHA mapping "is based on population averages".
- **Use for the plan:** the origin of the geodesic nearest-artery idea. It is a conference abstract, so cite it as such.
- **Not found:** the brief's "Patient-specific mappings between myocardial and coronary anatomy" (Termeer et al.); see UNVERIFIED.

### 3.5 Kurata et al. 2015 (Voronoi CT territories vs. SPECT)
Kurata A, Kono A, Sakamoto T, et al., Nieman K. Quantification of the myocardial area at risk using coronary CT angiography and Voronoi algorithm-based myocardial segmentation. *European Radiology* 2015;25(1):49–57.
- **DOI:** 10.1007/s00330-014-3388-2 (PubMed PMID 25173626)
- **Numbers (abstract):**
  - 34 patients.
  - CTA-based myocardial area at risk 28.3 ± 14.0% of LV volume.
  - Correlation with SPECT-based area at risk: r = 0.531 (SSS), 0.494 (SDS), 0.814 (SSS/SDS).
- **Use for the plan:** clinical validation that CT Voronoi territories track perfusion territories.

### 3.6 Ide et al. 2017 (histological validation in swine)
Ide S, Sumitsuji S, Yamaguchi O, Sakata Y. Cardiac computed tomography-derived myocardial mass at risk using the Voronoi-based segmentation algorithm: a histological validation study. *J Cardiovasc Comput Tomogr* 2017;11(3):179–182.
- **DOI:** 10.1016/j.jcct.2017.04.007 (PubMed PMID 28431861)
- **Numbers (abstract):**
  - 15 ex-vivo swine hearts.
  - CT vs. dye mass at risk: LAD 50.8% vs 49.8%; LCx 36.6% vs 32.2%; RCA 23.0% vs 25.9%.
  - r = 0.92 / 0.96 / 0.96.
- **Use for the plan:** ground-truth (dye) validation of geodesic/Voronoi territory assignment.

### 3.7 van Driest et al. 2022 (Voronoi area at risk vs. CT perfusion)
van Driest FY, Bijns CM, van der Geest RJ, et al., Scholte AJHA. Correlation between quantification of myocardial area at risk and ischemic burden at cardiac computed tomography. *Eur J Radiol Open* 2022;9:100417.
- **DOI:** 10.1016/j.ejro.2022.100417 (PubMed PMID 35402660; PMCID PMC8983940)
- **Numbers (abstract):**
  - 42 patients; 77 lesions.
  - Mean area at risk 59% vs. ischaemic burden 23%.
  - r = 0.564 for ≥50% stenosis; r = 0.708 for ≥70% stenosis.
- **Use for the plan:** a CT-only (CCTA + CTP) comparison. It shows that Voronoi territories overestimate perfused-defect extent unless stenosis severity is considered.

---

## 4. Transmural (layer) geometry: Laplace thickness and coordinates

### 4.1 Jones, Buchbinder & Aharon 2000
Jones SE, Buchbinder BR, Aharon I. Three-dimensional mapping of cortical thickness using Laplace's equation. *Human Brain Mapping* 2000;11(1):12–32.
- **DOI:** 10.1002/1097-0193(200009)11:1<12::AID-HBM20>3.0.CO;2-K (Crossref + PubMed PMID 10997850)
- **Method (abstract):** solve ∇²ψ = 0 in the tissue, with separate Dirichlet boundary conditions on the two boundaries. Thickness is the path length along the streamlines of the normalised gradient of ψ, so it is "uniquely defined for any point". Normal cortex is 2–4 mm thick.
- **Use for the plan:** the definition of a normalised transmural depth ψ ∈ [0, 1] (endocardium = 0, epicardium = 1). Layers are then iso-bands of ψ, e.g. subendocardial ψ < 1/3.

### 4.2 Yezzi & Prince 2003
Yezzi AJ Jr, Prince JL. An Eulerian PDE approach for computing tissue thickness. *IEEE Trans Med Imaging* 2003;22(10):1332–1339.
- **DOI:** 10.1109/TMI.2003.817775 (Crossref + PubMed PMID 14552586)
- **Method (abstract):** thickness is the length of correspondence trajectories that follow a smooth vector field. Two PDEs are solved with upwind finite differences, and no explicit trajectory tracing is needed. Tested on 2 simulations and 2 MRI datasets.
- **Use for the plan:** an efficient voxel-wise computation of distance from the endocardium and from the epicardium. Their sum gives the wall thickness and their ratio gives the transmural depth.

### 4.3 Bayer et al. 2012 (Laplace–Dirichlet rule-based fibres)
Bayer JD, Blake RC, Plank G, Trayanova NA. A novel rule-based algorithm for assigning myocardial fiber orientation to computational heart models. *Ann Biomed Eng* 2012;40(10):2243–2254.
- **DOI:** 10.1007/s10439-012-0593-5 (Crossref + PubMed PMID 22648575; PMC3518842)
- **Opened:** PubMed abstract; https://pmc.ncbi.nlm.nih.gov/articles/PMC3518842/
- **Numbers and method:**
  - Activation with LDRB vs. DTI fibres: relative differences ≤ 6%, mean activation-time differences ≤ 3.15 ms, correlations ≥ 0.99 (abstract).
  - The full text uses Laplace solutions with Dirichlet conditions on the epicardium and on the LV/RV endocardium (transmural ϕ_epi).
  - Canine-model angles: α_endo = 40°, α_epi = 250°, β_endo = 265°, β_epi = 25°.
- **Use for the plan:** precedent for a Laplace transmural coordinate in the LV wall, including how the septum is handled (ϕ_epi ≈ 0 within the septum).

### 4.4 Bayer et al. 2018 (Universal Ventricular Coordinates)
Bayer J, Prassl AJ, Pashaei A, Gomez JF, Frontera A, Neic A, Plank G, Vigmond EJ. Universal ventricular coordinates: a generic framework for describing position within the heart and transferring data. *Medical Image Analysis* 2018;45:83–93.
- **DOI:** 10.1016/j.media.2018.01.005 (PubMed PMID 29414438)
- **Method and numbers (abstract):**
  - Four coordinates computed from Laplace solutions with appropriate boundary conditions.
  - Mapping errors were below the element size. Fibre directions transferred with < 5° difference over most of the ventricles.
  - Papillary muscles "required further definition outside of the UVC framework".
- **Use for the plan:** a transmural × apicobasal × rotational coordinate system for layer-by-segment reporting and for transferring labels across patients. The plan must define its own handling of papillary muscles and trabeculae.

---

## 5. Layer-wise (subendocardial vs. transmural) CT evidence

### 5.1 George et al. 2009 (transmural perfusion ratio)
George RT, Arbab-Zadeh A, Miller JM, et al., Lima JA. Adenosine stress 64- and 256-row detector computed tomography angiography and perfusion imaging: a pilot study evaluating the transmural extent of perfusion abnormalities to predict atherosclerosis causing myocardial ischemia. *Circ Cardiovasc Imaging* 2009;2(3):174–182.
- **DOI:** 10.1161/CIRCIMAGING.108.813766 (PubMed PMID 19808590; PMCID PMC3035629)
- **Numbers (abstract):**
  - 40 patients (64-row n = 24; 256-row n = 16).
  - Transmural perfusion ratio = subendocardial attenuation / subepicardial attenuation.
  - CTA + CTP: sensitivity / specificity / PPV / NPV 86 / 92 / 92 / 85% per patient, and 79 / 91 / 75 / 92% per vessel or territory.
- **Use for the plan:** the clinical rationale for segmenting endocardial and epicardial layers on CT. The transmural perfusion ratio is a direct downstream readout.

### 5.2 Mushtaq et al. 2023 (subendocardial vs. transmural CTP defect)
Mushtaq S, Pontone G, Conte E, et al., Andreini D. Diagnostic accuracy of subendocardial vs. transmural myocardial perfusion defect for the detection of in-stent restenosis or progression of coronary artery disease after percutaneous coronary intervention. *J Cardiovasc Comput Tomogr* 2023;17(4):277–280.
- **DOI:** 10.1016/j.jcct.2023.05.005 (PubMed PMID 37248106)
- **Definitions (abstract):**
  - "Subendocardial" defect: hypo-enhancement involving > 25% but < 50% of the wall thickness.
  - "Transmural" defect: hypo-enhancement involving > 50% of the wall thickness.
- **Numbers (abstract):**
  - 150 patients.
  - Vessel-level accuracy 93.5% (subendocardial) vs 87.7% (transmural). Sensitivity 87.9% vs 46.9%; specificity 94.9% vs 97.9%.
  - Patient-level accuracy 86.6% vs 68%.
- **Use for the plan:** a clinical definition of transmural-extent thresholds (25% and 50%) that layer outputs should support.
- **Data:** Zenodo 10.5281/zenodo.8123699 is **restricted access**.

---

## 6. Public data with myocardial scar or perfusion labels

### Search summary
**Conclusion: I found no public, openly downloadable CT dataset with voxel-level myocardial scar (late iodine enhancement) or perfusion-defect labels.**

What I searched:
- **Zenodo API** (type=dataset), with these queries:
  - `"myocardial perfusion" CT`
  - `"late iodine enhancement"` (0 hits)
  - `myocardial infarction CT segmentation dataset`
  - `"CT perfusion" myocardium`
  - `cardiac CT scar`
- **Web searches** covering TCIA, Kaggle/HuggingFace/PhysioNet and "late enhancement CT open dataset".
- **The CARE challenge pages.**

What turned up:
- **Restricted Zenodo records.** All CT-perfusion and CT-fibrosis records found are restricted access, with no files listed. All appear to come from the Monzino/Pontone/Andreini group:
  - 7613098: deep-learning CTP; supplement to 10.1007/s00259-022-05732-w
  - 8123699: subendocardial vs. transmural; entry 5.2
  - 14616112: ADVANTAGE 2 dynamic CTP; *Radiology* 10.1148/radiol.232225; labelled CC BY 4.0 but restricted
  - 3690825: CTP vs. CTA in in-stent restenosis
  - 8206519: deep-learning myocardial fibrosis on early-enhancement CT; 10.3389/fcvm.2023.1151705
  - 18242896: computational MBF prediction; 10.1016/j.cmpb.2025.108990

  These are candidates for a data-access request, not open data.
- **PhysioNet "Myocardial perfusion scintigraphy image database v1.0.0":** SPECT, not CT (seen in search results only; not opened).
- **Scar label sets exist only for CMR:**
  - EMIDEC: 150 DE-MRI exams, 50 normal and 100 MI (Lalande et al., *MedIA* 2022;79:102428; DOI 10.1016/j.media.2022.102428; PubMed PMID 35500498).
  - MyoPS 2020: 45 paired bSSFP/LGE/T2 CMR. Mean submitted Dice 0.614 ± 0.231 for scar and 0.644 ± 0.153 for edema (Li et al., *MedIA* 2023;87:102808; DOI 10.1016/j.media.2023.102808; PubMed PMID 37087838; abstract). The MyoPS homepage (zmiclab.github.io/zxh/0/myops20/) confirms LGE / T2 / bSSFP CMR.
  - CARE 2026 CARE-Myocardium: MRI only (entry 1.5).
- **Public CT with coronary geometry but no myocardial outcome labels**, useful for territory construction:
  - **ImageCAS:** Zeng A, et al. ImageCAS: a large-scale dataset and benchmark for coronary artery segmentation based on computed tomography angiography images. *Comput Med Imaging Graph* 2023;109:102287. DOI 10.1016/j.compmedimag.2023.102287; PubMed PMID 37634975. The README says "about 1000 3D CTA images"; download link and password by email, also on Kaggle; no licence stated.
  - **ASOCA:** Gharleghi R, et al. Automated segmentation of normal and diseased coronary arteries – the ASOCA challenge. *Comput Med Imaging Graph* 2022;97:102049. DOI 10.1016/j.compmedimag.2022.102049; PubMed PMID 35334316. Described as 40 cases in a 2025 paper (PMID 40968338); the 20 normal / 20 diseased split appeared only in search summaries.
- **Use for the plan:** CT scar and perfusion supervision must come from a private or partner cohort. Options are paired CT + CMR LGE registered across modalities, CTP, or the restricted Monzino Zenodo records on request. Alternatively, the plan can be weakly supervised (patient- or territory-level FFR labels, as in Zreik 2018). The plan should state this gap explicitly.

---

## UNVERIFIED (keep out of the main reference list, or verify before use)

1. **Cerqueira 2002, body text.** The metadata is verified (entry 3.1). I could **not** open the full text (ahajournals 403) to confirm:
   - its exact wording on assigning segments to LAD/RCA/LCx territories;
   - any statement on the variability of coronary supply;
   - the claimed ~35% / 35% / 30% basal / mid / apical mass split, which appeared only in a search-engine summary.

   Do not quote these. For the "population averages / empirical" point, cite Ortiz-Pérez 2008 (3.2) or Termeer 2009 (3.4), which both say so in text I read.
2. **Termeer et al., "Patient-specific mappings between myocardial and coronary anatomy".** Not located. A PubMed search on Termeer returned nothing. The only verified Termeer item is the 2009 SCMR abstract (3.4). The book chapter (Dagstuhl / Scientific Visualization ~2010) is unverified.
3. **"Kim/Cerci et al." CT-based territory paper.** Not located. Kurata 2015, Ide 2017 and van Driest 2022 (3.5–3.7) are verified substitutes.
4. **Per-structure LV-myocardium CT Dice from MM-WHS.** It exists only as boxplots (Fig. 4), so no number can be cited. The GUT team paper (Payer et al., STACOM 2017) may report one, but I did not check it.
5. **Per-class heart Dice for TotalSegmentator v1.** Only Fig. S1, a bar chart without numbers.
6. **ImageCHD and ImageCAS licences.** No licence is stated in either GitHub README. The Kaggle page licences were not checked.
7. **ASOCA 20 normal / 20 diseased split and its licence.** Seen only in search summaries. The challenge site and Data paper were not opened.
8. **EMIDEC licence (CC BY-NC-SA 4.0).** Seen only in a search-result summary of a dataset index; not verified on the EMIDEC site.
