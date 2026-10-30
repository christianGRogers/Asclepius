# Verified citations: segmenting LV myocardial layers on cardiac CT (perfusion, scar)

Verified 2026-10-30. Bibliographic data (authors, title, journal, year, vol:pages, DOI, PMID, PMCID) were pulled from the NCBI PubMed E-utilities record (`https://pubmed.ncbi.nlm.nih.gov/<PMID>/`), unless another URL is given. Numbers come from the **abstract** unless another location (table, section, figure) is named. Where a number is in the full text and I could not read it, the entry says so.

Corrections to the brief:
- **Nieman "Reperfused MI 64-slice CT vs MR" is 2008**, Radiology 247:49, not 2006. The 2006 Nieman paper is a different one, in Am J Cardiol (see Nieman2006).
- **"Punzo et al. 2020" lists Forte E as first author.** Punzo B is the creator of the linked Mendeley dataset.
- **"Lee HJ 2016 JACC CVI" is Radiology 2016.** The JACC CVI 2016 DECT-ECV paper is Hong YJ et al. (rabbit model). Both are listed.
- **Nacif's ECV paper is Radiology 2012.** A follow-up 3D toolkit paper appeared in JCCT 2013.
- **The Termeer "patient-specific mapping" exists in two forms:** an IEEE TVCG 2008 paper and a JCMR 2009 SCMR abstract.

---

## 1. AHA 17-segment model and coronary territories

- **Cerqueira2002**: Cerqueira MD, Weissman NJ, Dilsizian V, et al. "Standardized myocardial segmentation and nomenclature for tomographic imaging of the heart. A statement for healthcare professionals from the Cardiac Imaging Committee of the Council on Clinical Cardiology of the American Heart Association." *Circulation* 2002;105:539-542. DOI 10.1161/hc0402.102975. PMID 11815441. Also reprinted in Int J Cardiovasc Imaging 2002;18:539-42 (PMID 12135124).
  - Content: defines the 17-segment model (basal 1-6, mid 7-12, apical 13-16, apex 17) and the assignment of segments to coronary territories.
  - The commonly quoted mapping is LAD 1, 2, 7, 8, 13, 14, 17; RCA 3, 4, 9, 10, 15; LCx 5, 6, 11, 12, 16. It is in the paper's territory figure. **The publisher full text returned HTTP 403, so I could not check the figure myself.** The mapping is confirmed only by secondary sources (Radiopaedia "cardiac segmentation model"). Cite the figure only after checking the PDF.
  - Verified via https://pubmed.ncbi.nlm.nih.gov/11815441/

- **OrtizPerez2008**: Ortiz-Pérez JT, Rodríguez J, Meyers SN, Lee DC, Davidson C, Wu E. "Correspondence between the 17-segment model and coronary arterial anatomy using contrast-enhanced cardiac magnetic resonance imaging." *JACC Cardiovasc Imaging* 2008;1:282-293. DOI 10.1016/j.jcmg.2008.01.014. PMID 19356440.
  - Abstract: 93 post-STEMI patients.
  - Per segment, **23% of hyperenhanced segments were discordant** with the empirically assigned coronary territory.
  - HE in the basal anteroseptal, mid-anterior, mid-anteroseptal or apical anterior segment was **100% specific for LAD**.
  - **No segment was 100% specific for RCA or LCx.** Basal anterolateral HE was **98% specific for LCx**.
  - Verified via https://pubmed.ncbi.nlm.nih.gov/19356440/

- **Javadi2010**: Javadi MS, Lautamäki R, Merrill J, et al. "Definition of vascular territories on myocardial perfusion images by integration with true coronary anatomy: a hybrid PET/CT analysis." *J Nucl Med* 2010;51:198-203. DOI 10.2967/jnumed.109.067488. PMID 20080895.
  - Abstract: 71 patients with 82Rb PET/CT plus CTA.
  - **72% (51/71) had ≥1 segment that differed from standard AHA assignment.**
  - **112 of 1,207 segments (≈9.3%) were reassigned.** Of the reassigned segments:
    - RCA to LCx: 39%
    - LCx to LAD: 30%
    - LAD to LCx: 12%
    - LAD to RCA: 11%
  - Dog validation against ex vivo staining gave κ = 0.80.
  - Defect/remote uptake ratio improved from 0.81±0.12 to 0.75±0.13 (P = 0.0014).
  - Verified via https://pubmed.ncbi.nlm.nih.gov/20080895/

- **Mahnken2010**: Mahnken AH, et al. (4 authors). "The culprit lesion and its consequences: combined visualization of the coronary arteries and delayed myocardial enhancement in dual-source CT: a pilot study." *Eur Radiol* 2010;20:2834-2843. DOI 10.1007/s00330-010-1864-x. PMID 20574631.
  - Abstract: CT-only fusion of CCTA and late-phase CT.
  - In patients, **10/96 segments** showed a discrepancy between infarct distribution and the empirical territory when compared with the true coronary branching pattern.
  - Mixture-model late-enhancement segmentation versus manual: κ = 0.839 in animals, 0.770 in patients.
  - Verified via https://pubmed.ncbi.nlm.nih.gov/20574631/

- **Termeer2008**: Termeer M, Oliván Bescós J, Breeuwer M, et al. "Visualization of myocardial perfusion derived from coronary anatomy." *IEEE Trans Vis Comput Graph* 2008;14:1595-1602. DOI 10.1109/TVCG.2008.180. PMID 18989015.
  - A method paper with no headline numbers. It simulates perfusion and patient-specific coronary territories purely from a 3D anatomical tomographic scan, and displays them as bull's-eye plots.
  - Verified via https://pubmed.ncbi.nlm.nih.gov/18989015/

- **Termeer2009**: Termeer M, Oliván Bescós J, Breeuwer M, Vilanova A, Gerritsen F, Gröller E, Nagel E. "Patient-specific coronary artery supply territory AHA diagrams." *J Cardiovasc Magn Reson* 2009;11(Suppl 1):P103. This is an SCMR 2009 abstract. DOI 10.1186/1532-429X-11-S1-P103 (Crossref).
  - Qualitative only: 5 patients, rated by one clinician. **No numbers to quote.**
  - Verified via https://www.cg.tuwien.ac.at/research/publications/2009/termeer-2009-scmr/ and the Crossref API.

- **Stalikas2025**: Stalikas N, et al. (41 authors). "Vessel-Specific Myocardial Mass in Patients With Stable Coronary Artery Disease." *J Am Heart Assoc* 2025;14:e039013. DOI 10.1161/JAHA.124.039013. PMID 41195772. PMCID PMC12887209.
  - Abstract: CCTA **Voronoi** method, 948 patients, 9,228 branches.
  - Median LV mass 141 g.
  - Share of LV mass subtended by each main artery: LAD 42.5% [IQR 37.9-48.1], LCx 28.8%, RCA 26.4% [20.9-31.9]. The LCx IQR is printed garbled in the abstract, so do not quote it.
  - Verified via https://pubmed.ncbi.nlm.nih.gov/41195772/

## 2. Deep-learning LV myocardium segmentation on CT; wall thickness

- **Zhuang2019 (MM-WHS)**: Zhuang X, Li L, Payer C, et al. (34 authors). "Evaluation of algorithms for Multi-Modality Whole Heart Segmentation: An open-access grand challenge." *Med Image Anal* 2019;58:101537. DOI 10.1016/j.media.2019.101537. PMID 31446280. PMCID PMC6839613.
  - 120 volumes: 60 CT and 60 MRI. Each modality is split 20 training / 40 test (Section 2, data).
  - CT resolution is **0.78×0.78 mm in-plane, mean slice thickness 1.60 mm** (data description).
  - **Table 3, CT whole-heart Dice:** GUT 0.908±0.086, KTH 0.894±0.030, CUHK1 0.890±0.049.
  - **Per-structure CT myocardium Dice is shown only as boxplots (Fig. 4), not in a table. I could not extract it, so it is left out.**
  - Verified via https://pmc.ncbi.nlm.nih.gov/articles/PMC6839613/

- **Wasserthal2023 (TotalSegmentator)**: Wasserthal J, Breit HC, Meyer MT, et al. (12 authors). "TotalSegmentator: Robust Segmentation of 104 Anatomic Structures in CT Images." *Radiol Artif Intell* 2023;5:e230024. DOI 10.1148/ryai.230024. PMID 37795137. PMCID PMC10546353.
  - Abstract: 1,204 CTs, 104 structures. Overall test Dice **0.943**; on an external set, 0.932 versus 0.871 for a comparator model.
  - v1 class list includes `heart_myocardium` (class 44), plus `heart_atrium_left/right` and `heart_ventricle_left/right` (classes 45-48). Source: v1.5.7 README.
  - **In v2 these classes moved to the `heartchambers_highres` subtask.** That subtask is licence-gated: free academic licence, commercial licence by contact. Source: master README and resources/improvements_in_v2.md.
  - heartchambers_highres details:
    - 1,559 training images (1,502 training / 57 validation), with paired contrast and non-contrast scans.
    - Working resolution 0.7266×0.7227×1.0 mm.
    - **Dice across all classes on validation: 0.950.** No per-class myocardium Dice is given.
    - Source: resources/heartchambers_highres_details.md.
  - Code is Apache-2.0 for the open tasks.
  - Verified via https://pubmed.ncbi.nlm.nih.gov/37795137/ ; https://github.com/wasserth/TotalSegmentator (README, v1.5.7 README, resources/*.md)

- **TotalSegDataset**: "Dataset with segmentations of 104 important anatomical structures in 1204 CT images." Zenodo, v1.0, 2022-07-06. DOI 10.5281/zenodo.6802614. Concept DOI 10.5281/zenodo.6802613.
  - **Licence: CC BY 4.0**, per the Zenodo API.
  - The latest version under the concept DOI is v3.0.0, "117 important anatomical structures in 1939 CT images" (DOI 10.5281/zenodo.22688904), also CC BY 4.0. In v2 the heart chambers moved out of `total`, so check that the version you download actually contains myocardium masks.
  - The README says 1,228 subjects are downloadable.
  - Verified via https://zenodo.org/api/records/6802614 and https://zenodo.org/api/records/6802613

- **Xu2020 (ImageCHD)**: Xu X, Wang T, Zhuang J, Yuan H, Huang M, Cen J, Jia Q, Dong Y, Shi Y. "ImageCHD: A 3D Computed Tomography Image Dataset for Classification of Congenital Heart Disease." MICCAI 2020, LNCS pp. 77-87. DOI 10.1007/978-3-030-59719-1_8. arXiv 2101.10799.
  - 110 CT volumes, size 512×512×(129-357).
  - **Typical voxel 0.25×0.25×0.5 mm³** (paper, dataset section).
  - Labels: LV 1, RV 2, LA 3, RA 4, **myocardium 5**, aorta 6, PA 7 (GitHub README).
  - **The paper reports no myocardium Dice.** Its Table 3 omits Myo.
  - **Licence: CC BY-NC 4.0**, on Kaggle `xiaoweixumedicalai/imagechd`, per the Kaggle API.
  - Population is congenital heart disease, aged 1 month to 40 years, so it is not representative of ischaemic adult LV.
  - Verified via https://arxiv.org/abs/2101.10799 ; https://ar5iv.labs.arxiv.org/html/2101.10799 ; GitHub README ; Kaggle API `datasets/list?user=xiaoweixumedicalai` ; Crossref.

- **Zreik2018**: Zreik M, Lessmann N, van Hamersvelt RW, et al. (8 authors). "Deep learning analysis of the myocardium in coronary CT angiography for identification of patients with functionally significant coronary artery stenosis." *Med Image Anal* 2018;44:72-85. DOI 10.1016/j.media.2017.11.008. PMID 29197253.
  - Abstract, 166 patients with invasive FFR.
  - Multiscale CNN LV myocardium segmentation on 20 images: **Dice 0.91, mean absolute distance 0.7 mm**.
  - Autoencoder plus SVM classifier for functionally significant stenosis: **AUC 0.74±0.02** (126 scans, 50 × 10-fold cross-validation).
  - Specificity 0.77 / 0.71 / 0.59 at sensitivity 0.60 / 0.70 / 0.80.
  - Verified via https://pubmed.ncbi.nlm.nih.gov/29197253/

- **vanHamersvelt2019**: van Hamersvelt RW, Zreik M, Voskuil M, Viergever MA, Išgum I, Leiner T. "Deep learning analysis of left ventricular myocardium in CT angiographic intermediate-degree coronary stenosis improves the diagnostic accuracy for identification of functionally significant stenosis." *Eur Radiol* 2019;29:2350-2359. DOI 10.1007/s00330-018-5822-3. PMID 30421020. PMCID PMC6443613.
  - Abstract, 126 patients.
  - **AUC 0.76 (degree of stenosis + DL LV myocardium) vs 0.68 (degree of stenosis only).**
  - Sensitivity/specificity: 84.6%/48.4% for the combined method vs 92.6%/31.1% for stenosis only.
  - Verified via https://pubmed.ncbi.nlm.nih.gov/30421020/

- **Isensee2021 (nnU-Net)**: Isensee F, Jaeger PF, Kohl SAA, Petersen J, Maier-Hein KH. "nnU-Net: a self-configuring method for deep learning-based biomedical image segmentation." *Nat Methods* 2021;18:203-211. DOI 10.1038/s41592-020-01008-z. PMID 33288961.
  - The abstract says it surpasses most existing approaches on **23 public datasets**.
  - Verified via https://pubmed.ncbi.nlm.nih.gov/33288961/

- **Bruns2020**: Bruns S, Wolterink JM, Takx RAP, et al. (8 authors). "Deep learning from dual-energy information for whole-heart segmentation in dual-energy and single-energy non-contrast-enhanced cardiac CT." *Med Phys* 2020;47:5048-5060. DOI 10.1002/mp.14451. PMID 32786071.
  - Abstract: 18 dual-layer CT patients, 7 labels including LV myocardium.
  - On virtual non-contrast images, **average Dice 0.897±0.034** (average across structures, not myocardium alone) and ASSD 1.42±0.45 mm.
  - LV myocardium volume bias in non-contrast CT vs CCTA: −19 mL [−67; 30].
  - Verified via https://pubmed.ncbi.nlm.nih.gov/32786071/

- **Chen2025 (CT wall thickness norms)**: Chen J, et al. (7 authors). "Left ventricular wall thickness discrepancies at end-diastole and mid-diastole: Reference values for cardiac CT." *Clin Imaging* 2025;118:110390. DOI 10.1016/j.clinimag.2024.110390. PMID 39709864.
  - Abstract: 187 healthy subjects, AHA 17-segment model.
  - **Global LV wall thickness 5.7±0.8 mm at end-diastole vs 6.5±0.9 mm at mid-diastole.**
  - Thickest segment is segment 2: 8.1±1.5 mm at end-diastole.
  - Upper limits at end-diastole: **9.9 mm (women), 11.7 mm (men)**.
  - Wall thins from base to apex.
  - Verified via https://pubmed.ncbi.nlm.nih.gov/39709864/

- **Lin2008**: Lin FY, Devereux RB, Roman MJ, et al. (11 authors). "Cardiac chamber volumes, function, and mass as determined by 64-multidetector row computed tomography: mean values among healthy adults free of hypertension and obesity." *JACC Cardiovasc Imaging* 2008;1:782-786. DOI 10.1016/j.jcmg.2008.04.015. PMID 19356515.
  - Abstract, 103 adults.
  - LV mass / height^2.7 = 24.3±11.0 g/m^2.7.
  - Relative wall thickness 0.16-0.44.
  - 3D LVEDV 144±71 mL.
  - Verified via https://pubmed.ncbi.nlm.nih.gov/19356515/

## 3. Myocardial CT perfusion (CTP)

- **Rochitte2014 (CORE320)**: Rochitte CE, George RT, Chen MY, et al. (30 authors). "Computed tomography angiography and perfusion to assess coronary artery stenosis causing perfusion defects by single photon emission computed tomography: the CORE320 study." *Eur Heart J* 2014;35:1120-1130. DOI 10.1093/eurheartj/eht488. PMID 24255127. PMCID PMC6693293.
  - Abstract: 381 patients, 16 centres. Reference standard is ICA ≥50% plus a SPECT defect, **not FFR**.
  - Per-patient AUC of integrated CTA-CTP: **0.87 (0.84-0.91)**.
  - Sensitivity 80%, specificity 74%, PPV 65%, NPV 86%.
  - Verified via https://pubmed.ncbi.nlm.nih.gov/24255127/

- **George2014 (CORE320 CTP vs SPECT)**: George RT, Mehra VC, Chen MY, et al. "Myocardial CT perfusion imaging and SPECT for the diagnosis of coronary artery disease: a head-to-head comparison from the CORE320 multicenter diagnostic performance study." *Radiology* 2014;272:407-416. DOI 10.1148/radiol.14140806. PMID 24865312. PMCID PMC4263655.
  - Abstract, reference standard ICA ≥50%.
  - CTP: sensitivity 88%, specificity 55%, Az 0.78.
  - SPECT: sensitivity 62%, specificity 67%, Az 0.69 (P = .001).
  - Verified via https://pubmed.ncbi.nlm.nih.gov/24865312/

- **Pontone2019a (PERFECTION, static CTP vs FFR)**: Pontone G, Baggiano A, Andreini D, et al. (24 authors). "Stress Computed Tomography Perfusion Versus Fractional Flow Reserve CT Derived in Suspected Coronary Artery Disease: The PERFECTION Study." *JACC Cardiovasc Imaging* 2019;12:1487-1497. DOI 10.1016/j.jcmg.2018.08.023. PMID 30343073.
  - Abstract: 147 patients, reference standard ICA + invasive FFR.
  - **cCTA + stress CTP, vessel level:** sensitivity 92%, specificity 95%, NPV 97%, PPV 87%, accuracy 94%.
  - **cCTA + stress CTP, patient level:** sensitivity 98%, specificity 87%.
  - AUC (vessel / patient): cCTA 0.89 / 0.90; cCTA+FFRCT 0.93 / 0.94; cCTA+CTP 0.92 / 0.93.
  - Verified via https://pubmed.ncbi.nlm.nih.gov/30343073/

- **Pontone2019b (dynamic CTP)**: Pontone G, Baggiano A, Andreini D, et al. (25 authors). "Dynamic Stress Computed Tomography Perfusion With a Whole-Heart Coverage Scanner in Addition to Coronary Computed Tomography Angiography and Fractional Flow Reserve Computed Tomography Derived." *JACC Cardiovasc Imaging* 2019;12:2460-2471. DOI 10.1016/j.jcmg.2019.02.015. PMID 31005531.
  - Abstract: 85 patients, vessel-based, reference standard invasive FFR.
  - Sensitivity/specificity: cCTA 83%/66%; cCTA+FFRCT 86%/75%; cCTA+CTP 73%/86%.
  - AUC: cCTA 0.826; +FFRCT 0.876; +CTP 0.878; +FFRCT+CTP **0.919**.
  - Effective dose of stress CTP: 5.3±0.7 mSv.
  - Verified via https://pubmed.ncbi.nlm.nih.gov/31005531/

- **Andreini2024 (ADVANTAGE 2)**: Andreini D, et al. (32 authors). "Diagnostic Accuracy of Dynamic Stress Myocardial CT Perfusion Compared with Invasive Physiology in Patients with Stents: The Advantage 2 Study." *Radiology* 2024;313:e232225. DOI 10.1148/radiol.232225. PMID 39688482.
  - Abstract: 156 stented patients, territory-based analysis.
  - **Against FFR:** CTP sensitivity 89.0%, specificity 82.8%, accuracy 84.7%, vs CCTA 60.0%, 61.9%, 61.5%.
  - Against IMR: CTP accuracy 82.9%.
  - Verified via https://pubmed.ncbi.nlm.nih.gov/39688482/

- **Takx2015 (meta-analysis)**: Takx RA, Blomberg BA, El Aidi H, et al. (8 authors). "Diagnostic accuracy of stress myocardial perfusion imaging compared to invasive coronary angiography with fractional flow reserve meta-analysis." *Circ Cardiovasc Imaging* 2015;8:e002666. DOI 10.1161/CIRCIMAGING.114.002666. PMID 25596143.
  - Abstract: 37 studies, 2,048 patients.
  - **Pooled negative likelihood ratio for CT:** 0.22 (0.12-0.39) at vessel level, **0.12 (0.04-0.33)** at patient level.
  - For comparison: MRI 0.16 / 0.14; SPECT 0.47 / 0.39.
  - Pooled sensitivity and specificity per modality are in the paper's tables; I did not read them.
  - Verified via https://pubmed.ncbi.nlm.nih.gov/25596143/

- **Lu2018 (dynamic CTP meta-analysis)**: Lu M, et al. (5 authors). "Dynamic stress computed tomography myocardial perfusion for detecting myocardial ischemia: A systematic review and meta-analysis." *Int J Cardiol* 2018;258:325-331. DOI 10.1016/j.ijcard.2018.01.095. PMID 29433968.
  - Abstract: 13 studies, 482 patients. Reference standards are mixed (MR, SPECT, PET, FFR).
  - Myocardial blood flow, pooled sensitivity/specificity:

    | Level | Sensitivity | Specificity |
    |---|---|---|
    | Segment | 0.83 | 0.90 |
    | Artery | 0.85 | 0.81 |
    | Patient | 0.93 | 0.82 |

  - Verified via https://pubmed.ncbi.nlm.nih.gov/29433968/

- **Kono2014 (relative MBF)**: Kono AK, Coenen A, Lubbers M, et al. (10 authors). "Relative myocardial blood flow by dynamic computed tomographic perfusion imaging predicts hemodynamic significance of coronary stenosis better than absolute blood flow." *Invest Radiol* 2014;49:801-807. DOI 10.1097/RLI.0000000000000087. PMID 25014013.
  - Abstract: 42 patients, 91 FFR vessels.
  - Hyperaemic MBF 75.6±22.5 vs 98.3±23.1 mL/100mL/min (ischaemic vs non-ischaemic).
  - **AUC: MBF ratio 0.85 vs absolute MBF 0.75.**
  - Remote MBF ranged from 60.7 to 167.2 mL/100mL/min.
  - Verified via https://pubmed.ncbi.nlm.nih.gov/25014013/

- **Patel2020 (SCCT CTP consensus)**: Patel AR, Bamberg F, Branch K, et al. (12 authors). "Society of cardiovascular computed tomography expert consensus document on myocardial computed tomography perfusion imaging." *J Cardiovasc Comput Tomogr* 2020;14:87-100. DOI 10.1016/j.jcct.2019.10.003. PMID 32122795.
  - PubMed has no abstract. **I quote no numbers from it.** Cite it for protocol and terminology only.
  - Verified via https://pubmed.ncbi.nlm.nih.gov/32122795/

- **George2009 (transmural perfusion ratio, TPR)**: George RT, Arbab-Zadeh A, Miller JM, et al. (11 authors). "Adenosine stress 64- and 256-row detector computed tomography angiography and perfusion imaging: a pilot study evaluating the transmural extent of perfusion abnormalities to predict atherosclerosis causing myocardial ischemia." *Circ Cardiovasc Imaging* 2009;2:174-182. DOI 10.1161/CIRCIMAGING.108.813766. PMID 19808590. PMCID PMC3035629.
  - TPR = subendocardial attenuation / subepicardial attenuation.
  - Methods: myocardium split into **3 layers** (subendocardial, mid, subepicardial). Images in short axis, **3 mm slices** at end-diastole, with beam-hardening correction for the 256-row data.
  - Results section: **normal TPR 1.12±0.13; abnormal threshold <0.99.**
  - Abstract: CTA + CTP sensitivity/specificity 86%/92% per patient, 79%/91% per vessel, against QCA + SPECT.
  - Verified via https://pmc.ncbi.nlm.nih.gov/articles/PMC3035629/

- **Mushtaq2023 (subendocardial vs transmural defect)**: Mushtaq S, Pontone G, Conte E, et al. (20 authors). "Diagnostic accuracy of subendocardial vs. transmural myocardial perfusion defect for the detection of in-stent restenosis or progression of coronary artery disease after percutaneous coronary intervention." *J Cardiovasc Comput Tomogr* 2023;17:277-280. DOI 10.1016/j.jcct.2023.05.005. PMID 37248106.
  - Abstract: 150 patients, ADVANTAGE sub-analysis.
  - Definitions: subendocardial defect = hypo-enhancement **>25% but <50%** of wall thickness; transmural = **>50%**.
  - Vessel-level accuracy 93.5% (subendocardial) vs 87.7% (transmural).
  - Sensitivity 87.9% vs 46.9%; specificity 94.9% vs 97.9%.
  - Patient-level accuracy 86.6% vs 68%.
  - Verified via https://pubmed.ncbi.nlm.nih.gov/37248106/

- **Forte2020 (normal rest perfusion by layer)**: Forte E, Punzo B, Gentile F, et al. (6 authors). "Normal patterns of left ventricle rest myocardial perfusion assessed by third-generation cardiac computed tomography." *Clin Physiol Funct Imaging* 2020;40:30-36. DOI 10.1111/cpf.12598. PMID 31578827.
  - Abstract: 40 normal subjects, third-generation dual-source CT.
  - **Subendocardial relative normalised attenuation (rnMAD) is higher than intramyocardial and subepicardial in all territories (P<0.001).**
  - **Septal TPR is the lowest:** 1.06±0.06 in diastole, 1.05±0.06 in systole.
  - Basal TPR is lower than mid and apical.
  - Verified via https://pubmed.ncbi.nlm.nih.gov/31578827/

- **Punzo2020data**: Punzo B. "Raw data - Normal patterns of left ventricle rest myocardial perfusion assessed by third-generation cardiac computed tomography." Mendeley Data, 2020. DOI 10.17632/cy54ttk3fj.1.
  - **Licence CC BY 4.0** (DataCite rightsList).
  - Resolves to https://data.mendeley.com/datasets/cy54ttk3fj/1.
  - **File contents were not listed by the API.** It is described only as "Research data", so it is probably tabular measurements rather than images or labels. Check before relying on it.
  - Verified via https://api.datacite.org/dois/10.17632/cy54ttk3fj.1 and https://doi.org/api/handles/10.17632/cy54ttk3fj.1

## 4. Late iodine enhancement (LIE) CT and CT-ECV vs MRI

- **Gatti2025 (LIE meta-analysis)**: Gatti M, et al. (15 authors). "Diagnostic accuracy of late iodine enhancement on cardiac CT for myocardial tissue characterization: a systematic review and meta-analysis." *Eur Radiol* 2025;35:3054-3067. DOI 10.1007/s00330-024-11283-5. PMID 39702631.
  - Abstract: 14 studies, 526 patients, 5,758 segments. Reference standard is CMR LGE.
  - **Patient level:** sensitivity 0.96 (0.88-0.99), specificity 0.95 (0.88-0.98), HSROC AUC 0.98.
  - **Segment level:** sensitivity 0.86 (0.79-0.91), specificity 0.98 (0.96-0.99), AUC 0.97.
  - Dual-energy CT raises segment-level sensitivity to 0.93.
  - Verified via https://pubmed.ncbi.nlm.nih.gov/39702631/

- **Nieman2008**: Nieman K, Shapiro MD, Ferencik M, et al. (10 authors). "Reperfused myocardial infarction: contrast-enhanced 64-Section CT in comparison to MR imaging." *Radiology* 2008;247:49-56. DOI 10.1148/radiol.2471070332. PMID 18372464.
  - Abstract: 21 patients, scanned ≤5 days after reperfused MI.
  - First-pass hypoenhanced area: CT 11±6% vs MR 7±4% of LV, **R² = 0.72**.
  - Delayed enhancement: CT 13±9% vs MR 15±7%, **R² = 0.55**. Delayed enhancement was seen on CT in only 11/15 scans.
  - Delayed hypoenhancement (microvascular obstruction): R² = 0.85.
  - MR had much better CNR for delayed imaging (P < .001).
  - Verified via https://pubmed.ncbi.nlm.nih.gov/18372464/

- **Penso2023 (DL scar from early-phase CT)**: Penso M, Babbaro M, Moccia S, et al. (12 authors). "A deep-learning approach for myocardial fibrosis detection in early contrast-enhanced cardiac CT images." *Front Cardiovasc Med* 2023;10:1151705. DOI 10.3389/fcvm.2023.1151705. PMID 37424918. PMCID PMC10325686.
  - Abstract: 50 patients. 44,187 LV segments (AHA 16-segment) were labelled from late-CT tracings that were themselves guided by CMR.
  - **Segment classification: accuracy 71%, AUC 0.76 (0.72-0.81).** Bull's-eye agreement with CMR 89%.
  - The data are on Zenodo 10.5281/zenodo.8206519 (**restricted access**).
  - Verified via https://pubmed.ncbi.nlm.nih.gov/37424918/ ; https://zenodo.org/api/records/8206519

- **Nacif2012 (CT-ECV)**: Nacif MS, Kawel N, Lee JJ, et al. (10 authors). "Interstitial myocardial fibrosis assessed as extracellular volume fraction with low-radiation-dose cardiac CT." *Radiology* 2012;264:876-883. DOI 10.1148/radiol.12112458. PMID 22771879. PMCID PMC3426854.
  - Abstract, 24 subjects. **CT-ECV vs MR-ECV r = 0.82.**
  - Dose 1.98±0.16 mSv per acquisition.
  - Verified via https://pubmed.ncbi.nlm.nih.gov/22771879/

- **Nacif2013 (3D ECV toolkit)**: Nacif MS, Liu Y, Yao J, et al. "3D left ventricular extracellular volume fraction by low-radiation dose cardiac CT: assessment of interstitial myocardial fibrosis." *J Cardiovasc Comput Tomogr* 2013;7:51-57. DOI 10.1016/j.jcct.2012.10.010. PMID 23333188. PMCID PMC4124745.
  - Abstract: ECV = (ΔHU_myo / ΔHU_blood) × (1 − Hct).
  - ECV: 41±6% (systolic heart failure), 33±2% (healthy), 35±5% (diastolic heart failure).
  - Verified via https://pubmed.ncbi.nlm.nih.gov/23333188/

- **Lee2016 (dual-energy ECV, Radiology)**: Lee HJ, Im DJ, Youn JC, et al. (9 authors). "Myocardial Extracellular Volume Fraction with Dual-Energy Equilibrium Contrast-enhanced Cardiac CT in Nonischemic Cardiomyopathy: A Prospective Comparison with Cardiac MR Imaging." *Radiology* 2016;280:49-57. DOI 10.1148/radiol.2016151289. PMID 27322972.
  - Abstract, 30 subjects.
  - Bland-Altman CT vs MR: **bias −0.06%, 95% limits of agreement −1.19 to 1.79**.
  - Inter-observer ICC 0.987.
  - Verified via https://pubmed.ncbi.nlm.nih.gov/27322972/

- **Hong2016 (JACC CVI, rabbit)**: Hong YJ, Kim TK, Hong D, et al. (13 authors). "Myocardial Characterization Using Dual-Energy CT in Doxorubicin-Induced DCM: Comparison With CMR T1-Mapping and Histology in a Rabbit Model." *JACC Cardiovasc Imaging* 2016;9:836-845. DOI 10.1016/j.jcmg.2015.12.018. PMID 27236517.
  - Abstract. CT-ECV vs MR-ECV r = 0.888.
  - Correlation with histological collagen volume fraction: r = 0.925 (CT), 0.961 (MR).
  - Verified via https://pubmed.ncbi.nlm.nih.gov/27236517/

- **Treibel2015**: Treibel TA, Bandula S, Fontana M, et al. (11 authors). "Extracellular volume quantification by dynamic equilibrium cardiac computed tomography in cardiac amyloidosis." *J Cardiovasc Comput Tomogr* 2015;9:585-592. DOI 10.1016/j.jcct.2015.07.001. PMID 26209459. PMCID PMC4684159.
  - Abstract. ECV_CT vs ECV_CMR: **r² = 0.85 at 5 min, 0.74 at 15 min** after bolus.
  - ECV_CT 0.54±0.11 (amyloid) vs 0.28±0.04 (aortic stenosis).
  - Verified via https://pubmed.ncbi.nlm.nih.gov/26209459/

- **Ohta2020 (dual-energy iodine-map ECV, segmental)**: Ohta Y, et al. (9 authors). "Investigation of myocardial extracellular volume fraction in heart failure patients using iodine map with rapid-kV switching dual-energy CT: Segmental comparison with MRI T1 mapping." *J Cardiovasc Comput Tomogr* 2020;14:349-355. DOI 10.1016/j.jcct.2019.12.032. PMID 31892473.
  - Abstract: 23 patients, 331 segments.
  - CT-ECV 31.6±9.1 vs MR-ECV 33.2±9.1.
  - **All segments r = 0.837**; mid-septal r = 0.895; inferior r = 0.793.
  - Verified via https://pubmed.ncbi.nlm.nih.gov/31892473/

- **Zhang2023 (CT-ECV meta-analysis)**: Zhang H, et al. (8 authors). "CT for the evaluation of myocardial extracellular volume with MRI as reference: a systematic review and meta-analysis." *Eur Radiol* 2023;33:8464-8476. DOI 10.1007/s00330-023-09872-x. PMID 37378712.
  - Abstract: 17 studies, 459 patients, 2,231 segments.
  - **Per patient:** mean difference 0.07%, **pooled r = 0.89**.
  - **Per segment:** mean difference 0.44%, r = 0.84.
  - Iodine-map ECV r = 0.94 vs subtraction ECV r = 0.84.
  - Septal r = 0.88 vs non-septal r = 0.76.
  - Verified via https://pubmed.ncbi.nlm.nih.gov/37378712/

## 5. Scar features on first-pass CCTA: hypoattenuation, thinning, fat

- **Nieman2006**: Nieman K, Cury RC, Ferencik M, et al. (9 authors). "Differentiation of recent and chronic myocardial infarction by cardiac computed tomography." *Am J Cardiol* 2006;98:303-308. DOI 10.1016/j.amjcard.2006.01.101. PMID 16860013.
  - Abstract. Measured with transmural ROIs on thin wall-parallel slices.
  - Attenuation: **long-standing MI −13±37 HU; acute MI 26±26 HU; normal 73±14 HU** (P<0.001).
  - Infarct-minus-remote difference: 89±41 HU (old) vs 55±33 HU (recent).
  - **Long-standing MI is associated with wall thinning (P<0.01).**
  - Verified via https://pubmed.ncbi.nlm.nih.gov/16860013/

- **Ichikawa2009 (fat in infarcts, by layer)**: Ichikawa Y, Kitagawa K, Chino S, et al. (10 authors). "Adipose tissue detected by multislice computed tomography in patients after myocardial infarction." *JACC Cardiovasc Imaging* 2009;2:548-555. DOI 10.1016/j.jcmg.2009.01.010. PMID 19442939.
  - Abstract. **LV intramyocardial fat in 62% (33/53) of prior-MI patients vs 3% (2/63) of controls.**
  - Location: **subendocardial in 94%**, mid-wall 3%, subepicardial 3%.
  - Fat lay in the infarct-related artery territory in 97%.
  - Fat in 89% of infarcts ≥3 years old; in none <10 months old.
  - Verified via https://pubmed.ncbi.nlm.nih.gov/19442939/

- **Rodrigues2016 + Cardiac Fat Database (epicardial fat)**: Rodrigues ÉO, Morais FF, Morais NA, et al. (6 authors). "A novel approach for the automated segmentation and volume quantification of cardiac fats on computed tomography." *Comput Methods Programs Biomed* 2016;123:109-128. DOI 10.1016/j.cmpb.2015.09.017. PMID 26474835.
  - Abstract: mean Dice 97.6%.
  - Dataset: **20 non-contrast cardiac CT scans, about 1,000 slices**, labelled for epicardial fat, mediastinal fat and pericardium gap.
  - **Terms: "use ... as you want as long as you reference our published work." No formal licence.**
  - Verified via https://pubmed.ncbi.nlm.nih.gov/26474835/ ; http://visual.ic.uff.br/en/cardio/ctfat/

- **Commandeur2019 (EAT deep learning)**: Commandeur F, Goeller M, Razipour A, et al. (14 authors). "Fully Automated CT Quantification of Epicardial Adipose Tissue by Deep Learning: A Multicenter Study." *Radiol Artif Intell* 2019;1:e190045. DOI 10.1148/ryai.2019190045. PMID 32090206. PMCID PMC6884062.
  - Abstract: n = 850. **DL vs expert R = 0.974**, bias 0.53 cm³.
  - Not a public dataset.
  - Verified via https://pubmed.ncbi.nlm.nih.gov/32090206/

## 6. Transmurality and transmural (Laplace) coordinates

- **Kim2000**: Kim RJ, Wu E, Rafael A, et al. (9 authors). "The use of contrast-enhanced magnetic resonance imaging to identify reversible myocardial dysfunction." *N Engl J Med* 2000;343:1445-1453. DOI 10.1056/NEJM200011163432003. PMID 11078769.
  - Abstract: 50 patients. 804/2,093 segments were dysfunctional.
  - **Contractility improved in 78% (256/329) of dysfunctional segments without hyperenhancement, but in only 1 of 58 segments with >75% transmural hyperenhancement.**
  - The commonly cited "50% transmurality" cut-off comes from the paper's graded analysis (Results, figure), which **I could not access. Quote the abstract numbers only.**
  - Verified via https://pubmed.ncbi.nlm.nih.gov/11078769/

- **Jones2000**: Jones SE, Buchbinder BR, Aharon I. "Three-dimensional mapping of cortical thickness using Laplace's equation." *Hum Brain Mapp* 2000;11:12-32. DOI 10.1002/1097-0193(200009)11:1<12::aid-hbm20>3.0.co;2-k. PMID 10997850. PMCID PMC6872107.
  - Abstract: thickness defined as the path length along field lines of ∇²ψ = 0 between the two boundaries.
  - Verified via https://pubmed.ncbi.nlm.nih.gov/10997850/

- **Bayer2018 (UVC)**: Bayer J, Prassl AJ, Pashaei A, et al. (8 authors). "Universal ventricular coordinates: A generic framework for describing position within the heart and transferring data." *Med Image Anal* 2018;45:83-93. DOI 10.1016/j.media.2018.01.005. PMID 29414438.
  - Abstract: 4 coordinates from solutions of Laplace's equation, including a transmural coordinate.
  - Mapping errors were smaller than one element; fibre directions differed by <5° over most of the ventricles.
  - Verified via https://pubmed.ncbi.nlm.nih.gov/29414438/

- **Schuler2021 (Cobiveco)**: Schuler S, Pilia N, Potyagaylo D, Loewe A. "Cobiveco: Consistent biventricular coordinates for precise and intuitive description of position in the heart - with MATLAB implementation." *Med Image Anal* 2021;74:102247. DOI 10.1016/j.media.2021.102247. PMID 34592711.
  - Abstract: normalised distances along bijective trajectories gave **better linearity than Laplace solutions**.
  - **More than 4-fold improvement** in transfer/linearity error on 36 geometries.
  - Permissive open-source code.
  - Verified via https://pubmed.ncbi.nlm.nih.gov/34592711/

## 7. Public CT datasets with myocardium / scar / perfusion labels

- **MM-WHS data access** (see Zhuang2019 for the dataset itself):
  - 60 CT volumes (20 training with labels; the 40 test labels are held out).
  - **Access requires a signed Data Access Agreement sent to the organisers.** The recipient commits "to not disseminate the Data to any third party."
  - The page names no explicit licence and says nothing on commercial use; check the agreement PDF.
  - The page asks users to cite Zhuang TPAMI 2019, Zhuang & Shen MedIA 2016, Wu & Zhuang TPAMI 2023 and Gao et al. MedIA 2023.
  - Verified via https://zmiclab.github.io/zxh/0/mmwhs/
- **TotalSegmentator CT dataset**: CC BY 4.0 on Zenodo; see TotalSegDataset above.
- **ImageCHD**: CC BY-NC 4.0 on Kaggle, includes a myocardium label; see Xu2020 above.
- **ASOCA (coronary lumen only, no myocardium label)**: Gharleghi R, Adikari D, Ellenberger K, et al. (21 authors). "Automated segmentation of normal and diseased coronary arteries - The ASOCA challenge." *Comput Med Imaging Graph* 2022;97:102049. DOI 10.1016/j.compmedimag.2022.102049. PMID 35334316.
  - Verified via https://pubmed.ncbi.nlm.nih.gov/35334316/
- **Cardiac Fat Database** (Rodrigues2016): epicardial and mediastinal fat labels, no myocardium label.
- **CT perfusion and CT scar datasets: none are openly downloadable with labels.**
  - Zenodo searches found only **restricted-access** "raw data" records from the Centro Cardiologico Monzino (Pontone) group. No files are publicly listed.
  - 10.5281/zenodo.8123699: subendocardial vs transmural CTP, ADVANTAGE (restricted, no licence given).
  - 10.5281/zenodo.14616112: ADVANTAGE 2 dynamic CTP (restricted, CC BY 4.0 metadata).
  - 10.5281/zenodo.10648243: stress-only dynamic CTP (restricted).
  - 10.5281/zenodo.18242896: computational MBF framework (restricted).
  - 10.5281/zenodo.8206519: Penso 2023 early-CT fibrosis (restricted).
  - Verified via `https://zenodo.org/api/records/<id>`. Each has `access_right: restricted` and an empty file list.
  - The Mendeley Punzo2020data record is CC BY 4.0 but appears to hold tabular data only.
  - I did not search TCIA systematically, so **absence there is UNVERIFIED.**

## 8. CT resolution, partial volume and beam hardening

- **Resolution of public CCTA data:**
  - MM-WHS CT: 0.78×0.78 mm in-plane, 1.6 mm mean slice thickness (Zhuang2019).
  - TotalSegmentator heartchambers_highres: works at about 0.73×0.72×1.0 mm.
  - ImageCHD: typical voxel 0.25×0.25×0.5 mm.
  - Set these against LV wall thickness of about 5.7 mm at end-diastole (Chen2025). A three-layer split (George2009) therefore leaves only about 2-3 voxels per layer at 0.7-0.8 mm voxels. **This is my own inference, not a cited number.**
- **Liu2026 (photon-counting detector CT resolutions)**: Liu Y, et al. (9 authors). "Deep Learning-Based Automated Coronary Plaque Quantification with Ultra-high Resolution Photon-Counting Detector CT at Different Spatial Resolutions." *Acad Radiol* 2026;33:3340-3349. DOI 10.1016/j.acra.2026.04.026. PMID 42161742.
  - Abstract, 70 patients. Reconstructions at **0.6 mm (standard), 0.4 mm (high) and 0.2 mm (ultra-high) slice thickness**.
  - Higher resolution reduced the measured plaque volume and stenosis in calcified lesions, but raised perceived noise.
  - Verified via https://pubmed.ncbi.nlm.nih.gov/42161742/
- **Kitagawa2010 (beam hardening in CTP)**: Kitagawa K, George RT, Arbab-Zadeh A, Lima JA, Lardo AC. "Characterization and correction of beam-hardening artifacts during dynamic volume CT assessment of myocardial perfusion." *Radiology* 2010;256:111-118. DOI 10.1148/radiol.10091399. PMID 20574089.
  - Abstract: phantom plus canine model (n = 5).
  - **Correlation of CT perfusion metric with microsphere MBF went from r = 0.60 to 0.74 after correction** (P > .05).
  - Verified via https://pubmed.ncbi.nlm.nih.gov/20574089/
- **So2016 (scanner-level artefact correction)**: So A, Imai Y, Nett B, et al. (11 authors). "Technical Note: Evaluation of a 160-mm/256-row CT scanner for whole-heart quantitative myocardial perfusion imaging." *Med Phys* 2016;43:4821. DOI 10.1118/1.4957389. PMID 27487900.
  - Abstract, phantom. Beam-hardening shifts in the water wall around the contrast-filled chambers fell **from >±30 HU to ≤±5 HU** (7 HU in one region at 100 kVp).
  - Verified via https://pubmed.ncbi.nlm.nih.gov/27487900/

---

## UNVERIFIED / left out
- Cerqueira 2002 territory figure: segment-to-artery list not read in the primary source (403). Recommend reading the PDF before quoting.
- MM-WHS per-structure CT myocardium Dice (figure only).
- Kim 2000 "50%" threshold wording (full text not accessed).
- Esposito 2016, Oda 2019/2020, Aikawa photon-counting LIE, and Gupta "fatty metaplasia": not located or verified, so left out. Gatti2025 covers the LIE pooled evidence.
- Kurata Voronoi territory paper: not found under that author. Stalikas2025 is used instead as the CCTA Voronoi reference.
- WHS++ / CARE 2024 whole-heart challenges: not checked.
