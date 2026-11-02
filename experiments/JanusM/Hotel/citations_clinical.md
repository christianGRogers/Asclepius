# Clinical literature: LV myocardial layers on cardiac CT (perfusion, LIE/ECV, fat, thinning, AI)

How each entry was checked (2026-10-30):
- Bibliographic data and abstract: pulled from the PubMed record (NCBI E-utilities efetch of the PMID, the same content as https://pubmed.ncbi.nlm.nih.gov/<PMID>/).
- DOI: each one resolved with an HTTP 302 from https://doi.org/<DOI> to the publisher page (all 43 resolved).
- Numbers marked **[full text]**: grepped from the PMC full-text HTML. The section or table is named.
- All other numbers are copied from the abstract as given. No numbers were computed or recalled from memory.

---

## 1. Myocardial CT perfusion (stress CTP, TPR, dynamic CTP, meta-analyses)

### 1.1 Rochitte CE, George RT, Chen MY, et al. (CORE320). Computed tomography angiography and perfusion to assess coronary artery stenosis causing perfusion defects by single photon emission computed tomography: the CORE320 study. *Eur Heart J* 2014;35(17):1120-30.
- DOI: 10.1093/eurheartj/eht488 · PMID 24255127 · PMC6693293
- URL opened: https://pubmed.ncbi.nlm.nih.gov/24255127/ (DOI resolves to academic.oup.com/eurheartj/article/35/17/1120/2465942)
- Numbers (abstract):
  - 16 centres, 381 patients.
  - Prevalence of obstructive CAD: 38% by ICA+SPECT and 59% by ICA alone.
  - Patient-level AUC of integrated CTA+CTP was 0.87 (95% CI 0.84-0.91). It was 0.90 (0.87-0.94) in patients without prior MI and 0.93 (0.89-0.97) in patients without prior CAD.
  - For CTA ≥50% plus a CTP defect: sensitivity 80% (72-86), specificity 74% (68-80), PPV 65%, NPV 86%.
- Use for the plan: shows that subendocardial perfusion on CT adds diagnostic value over CTA. This is the reference result for "myocardium + stenosis" combined reading.

### 1.2 George RT, Arbab-Zadeh A, Miller JM, et al. Adenosine stress 64- and 256-row detector computed tomography angiography and perfusion imaging: a pilot study evaluating the transmural extent of perfusion abnormalities to predict atherosclerosis causing myocardial ischemia. *Circ Cardiovasc Imaging* 2009;2(3):174-82.
- DOI: 10.1161/CIRCIMAGING.108.813766 · PMID 19808590 · PMC3035629
- URLs opened: https://pubmed.ncbi.nlm.nih.gov/19808590/ and https://pmc.ncbi.nlm.nih.gov/articles/PMC3035629/
- Numbers:
  - (abstract) 40 patients. CTA+CTP per patient: sensitivity/specificity/PPV/NPV 86/92/92/85%. Per vessel: 79/91/75/92%.
  - (abstract) TPR defined as subendocardial attenuation density divided by subepicardial attenuation density.
  - **[full text, "CT Myocardial Perfusion Image Analysis"]** The software "automatically and equally divided the myocardium into three myocardial layers: the subendocardial, midmyocardial, and subepicardial layers". Analysis used a 16-segment model.
  - **[full text, "CT Transmural Perfusion Ratio…"]** In normal territories (224 segments) TPR was 1.12±0.13. TPR was abnormal when <0.99, i.e. more than 1 SD below the normal mean. TPR was 0.91±0.10 in territories with 70-100% stenosis (Discussion).
  - **[full text, Methods]** Effective dose was 16.8 mSv for 64-row CT, and 21.6 mSv for 256-row CT rest+stress combined.
- Use for the plan: origin of the endo/mid/epi three-layer split and of the TPR<0.99 threshold. This is the main precedent for a layer-wise segmentation target.

### 1.3 Kühl JT, Linde JJ, Fuchs A, et al. Patterns of myocardial perfusion in humans evaluated with contrast-enhanced 320 multidetector computed tomography. *Int J Cardiovasc Imaging* 2012;28(7):1739-47.
- DOI: 10.1007/s10554-011-9986-z · PMID 22143171
- URL opened: https://pubmed.ncbi.nlm.nih.gov/22143171/
- Numbers (abstract):
  - Each of 16 segments was split into three layers (endo, mid, epi).
  - At rest the endo/epi ratio was 0.99 in the septum and 1.23 in non-septal segments (P<0.001).
  - Under adenosine the non-septal endo/epi ratio fell by 18%, from 1.23 to 1.05.
  - Rest attenuation density was lower in the lateral wall, matching NH3-PET.
- Use for the plan: normal rest layer ratios vary by region (septum vs free wall). Any layer-based biomarker needs region-specific normalisation.

### 1.4 Kühl JT, George RT, Mehra VC, et al. Endocardial-epicardial distribution of myocardial perfusion reserve assessed by multidetector computed tomography in symptomatic patients without significant coronary artery disease: insights from the CORE320 multicentre study. *Eur Heart J Cardiovasc Imaging* 2016;17(7):779-87.
- DOI: 10.1093/ehjci/jev206 · PMID 26341292 · PMC5006103
- URL opened: https://pubmed.ncbi.nlm.nih.gov/26341292/
- Numbers (abstract):
  - 149 CORE320 patients without obstructive CAD, analysed in 3 layers × 13 segments.
  - Myocardial perfusion reserve (MPR) was 124% [IQR 45, 235] in the subepicardium vs 68% [22, 102] in the subendocardium (P<0.001).
  - Septal MPR was 55% vs 89% inferolateral and 124% anterolateral.
- Use for the plan: multicentre evidence that CT resolves transmural (layer) perfusion differences in humans.

### 1.5 Ko BS, Cameron JD, Leung M, et al. Combined CT coronary angiography and stress myocardial perfusion imaging for hemodynamically significant stenoses in patients with suspected coronary artery disease: a comparison with fractional flow reserve. *JACC Cardiovasc Imaging* 2012;5(11):1097-111.
- DOI: 10.1016/j.jcmg.2012.09.004 · PMID 23153909
- URL opened: https://pubmed.ncbi.nlm.nih.gov/23153909/
- Numbers (abstract):
  - 40 patients, FFR ≤0.8 as reference, TPR <0.99 threshold.
  - CTA alone: sensitivity 95%, specificity 78%. Adding visual CTP or TPR raised specificity to 95%, with sensitivity 87% and 71% respectively.
  - AUC: CTA+visual 0.93, CTA alone 0.85, CTA+TPR 0.79.
- Use for the plan: a cautionary result. A crude whole-layer TPR did worse than visual reading, which motivates more accurate layer delineation and learned features.

### 1.6 Takx RA, Blomberg BA, El Aidi H, et al. Diagnostic accuracy of stress myocardial perfusion imaging compared to invasive coronary angiography with fractional flow reserve: meta-analysis. *Circ Cardiovasc Imaging* 2015;8(1):e002666.
- DOI: 10.1161/CIRCIMAGING.114.002666 · PMID 25596143
- URL opened: https://pubmed.ncbi.nlm.nih.gov/25596143/
- Numbers (abstract):
  - 37 studies, 2048 patients, 4721 vessels.
  - Patient-level pooled negative likelihood ratio: CT 0.12 (0.04-0.33), MRI 0.14 (0.10-0.18), PET 0.14 (0.02-0.87), SPECT 0.39 (0.27-0.55), echo 0.42 (0.30-0.59).
  - Vessel-level pooled NLR: CT 0.22 (0.12-0.39).
- Use for the plan: stress CTP rules out disease about as well as MRI and PET.

### 1.7 Celeng C, Leiner T, Maurovich-Horvat P, et al. Anatomical and Functional Computed Tomography for Diagnosing Hemodynamically Significant Coronary Artery Disease: A Meta-Analysis. *JACC Cardiovasc Imaging* 2019;12(7 Pt 2):1316-1325.
- DOI: 10.1016/j.jcmg.2018.07.022 · PMID 30219398
- URL opened: https://pubmed.ncbi.nlm.nih.gov/30219398/
- Numbers (abstract):
  - 54 articles, 5,330 patients.
  - Vessel-level pooled specificity: CTP 0.86 (0.76-0.93), FFRCT 0.78, TAG 0.77, CTA 0.61 (0.54-0.68). Combining CTA with a functional test gave specificity 0.80-0.92.
  - Dynamic vs static CTP: sensitivity 0.85 vs 0.72, specificity 0.81 vs 0.90.
- Use for the plan: the specificity gap of CTA alone (0.61) is the clinical problem that myocardial analysis targets.

### 1.8 Nous FMA, Geisler T, Kruk MBP, et al. (SPECIFIC). Dynamic Myocardial Perfusion CT for the Detection of Hemodynamically Significant Coronary Artery Disease. *JACC Cardiovasc Imaging* 2022;15(1):75-87.
- DOI: 10.1016/j.jcmg.2021.07.021 · PMID 34538630 · PMC8741746
- URL opened: https://pubmed.ncbi.nlm.nih.gov/34538630/
- Numbers (abstract):
  - 9 centres; 114 patients completed the protocol; 74/289 vessels (26%) were significant.
  - Per vessel, CTA ≥50%: sensitivity 96%, specificity 72%, accuracy 78%. CTA+CT-MPI: sensitivity 84%, specificity 89%, accuracy 88%.
  - AUC 0.79 for absolute MBF and 0.82 for relative MBF.
  - Median DLP 313 mGy·cm for CT-MPI and 138 mGy·cm for CTA.
- Use for the plan: multicentre benchmark for dynamic CTP. It also shows the extra dose that the perfusion scan adds over CTA.

### 1.9 Lubbers M, Coenen A, Kofflard M, et al. Comprehensive Cardiac CT With Myocardial Perfusion Imaging Versus Functional Testing in Suspected Coronary Artery Disease: The Multicenter, Randomized CRESCENT-II Trial. *JACC Cardiovasc Imaging* 2018;11(11):1625-1636.
- DOI: 10.1016/j.jcmg.2017.10.010 · PMID 29248657
- URL opened: https://pubmed.ncbi.nlm.nih.gov/29248657/
- Numbers (abstract):
  - 268 patients randomised. Invasive angiograms without a class I revascularisation indication: 1.5% in the CT arm vs 7.2% (p=0.035).
  - Further testing needed: 13% vs 37%.
  - Median cumulative dose 3.1 mSv (IQR 1.6-7.8) in the CT arm vs 0 mSv.
- Use for the plan: randomised evidence that tiered CT with perfusion changes management.

### 1.10 Pontone G, Baggiano A, Andreini D, et al. Stress Computed Tomography Perfusion Versus Fractional Flow Reserve CT Derived in Suspected Coronary Artery Disease: The PERFECTION Study. *JACC Cardiovasc Imaging* 2019;12(8 Pt 1):1487-1497.
- DOI: 10.1016/j.jcmg.2018.08.023 · PMID 30343073
- URL opened: https://pubmed.ncbi.nlm.nih.gov/30343073/
- Numbers (abstract):
  - 147 patients.
  - Vessel-level specificity: cCTA 76%, cCTA+FFRCT 94%, cCTA+stress-CTP 95%.
  - AUC vessel/patient: cCTA 0.89/0.90, +FFRCT 0.93/0.94, +CTP 0.92/0.93. No difference between FFRCT and CTP.
- Use for the plan: static CTP and FFRCT are comparable. A myocardium-based method should be compared against FFRCT.

### 1.11 Andreini D, Mushtaq S, Trabattoni D, et al. Diagnostic Accuracy of Dynamic Stress Myocardial CT Perfusion Compared with Invasive Physiology in Patients with Stents: The Advantage 2 Study. *Radiology* 2024;313(3):e232225.
- DOI: 10.1148/radiol.232225 · PMID 39688482
- URL opened: https://pubmed.ncbi.nlm.nih.gov/39688482/
- Numbers (abstract):
  - 156 patients with 504 stents.
  - Against FFR: CTP sensitivity/specificity/accuracy 89.0/82.8/84.7% vs CCTA 60.0/61.9/61.5%.
  - Diagnostic rate: CTP 98.7% vs CCTA 95.6%.
  - Effective dose of stress CTP+CCTA: 10.4 ± 2.7 mSv.
- Use for the plan: myocardium-based assessment works where the lumen cannot be read (stents). Supports a stent subgroup.
- (Design paper, also verified: Andreini D et al., *J Cardiovasc Comput Tomogr* 2018;12(5):411-417, DOI 10.1016/j.jcct.2018.06.003, PMID 29933938.)

---

## 2. Rest CCTA first-pass hypoattenuation (infarct and ischaemia)

### 2.1 Nikolaou K, Sanz J, Poon M, et al. Assessment of myocardial perfusion and viability from routine contrast-enhanced 16-detector-row computed tomography of the heart: preliminary results. *Eur Radiol* 2005;15(5):864-71.
- DOI: 10.1007/s00330-005-2672-6 · PMID 15776243
- URL opened: https://pubmed.ncbi.nlm.nih.gov/15776243/
- Numbers (abstract):
  - 30 patients; MRI was the reference.
  - Routine CTA detected 10 of 11 MIs: sensitivity 91%, specificity 79%, accuracy 83%.
  - It detected 3 of 6 non-infarct perfusion defects: sensitivity 50%, specificity 92%.
  - Infarct size was systematically underestimated against DE-MRI (P<0.01).
- Use for the plan: rest CCTA alone finds chronic MI but not reliably ischaemia. This sets realistic expectations.

### 2.2 Nieman K, Cury RC, Ferencik M, et al. Differentiation of recent and chronic myocardial infarction by cardiac computed tomography. *Am J Cardiol* 2006;98(3):303-8.
- DOI: 10.1016/j.amjcard.2006.01.101 · PMID 16860013
- URL opened: https://pubmed.ncbi.nlm.nih.gov/16860013/
- Numbers (abstract):
  - Attenuation was measured at consecutive transmural positions with thin slices parallel to the wall.
  - Infarct attenuation: long-standing MI −13 ± 37 HU, acute MI 26 ± 26 HU, normal controls 73 ± 14 HU (p<0.001).
  - Infarct minus remote: 89 ± 41 HU (chronic) vs 55 ± 33 HU (recent).
  - Long-standing MI was associated with wall thinning (p<0.01).
- Use for the plan: direct HU evidence for a transmural profile analysis. Chronic infarct falls to near-fat HU, so the model must separate it from lipomatous metaplasia.

### 2.3 Nieman K, Shapiro MD, Ferencik M, et al. Reperfused myocardial infarction: contrast-enhanced 64-section CT in comparison to MR imaging. *Radiology* 2008;247(1):49-56.
- DOI: 10.1148/radiol.2471070332 · PMID 18372464
- URL opened: https://pubmed.ncbi.nlm.nih.gov/18372464/
- Numbers (abstract):
  - 21 patients ≤5 days after reperfused MI.
  - First-pass hypoenhanced area: 11 ± 6% of LV mass on CT vs 7 ± 4% on MR (R²=0.72).
  - Delayed enhancement: 13 ± 9% on CT vs 15 ± 7% on MR (R²=0.55). Delayed hyperenhancement was seen on CT in 11 of 15 scans.
  - MR had far better CNR than CT on delayed images (P<.001).
- Use for the plan: first-pass CT hypoenhancement agrees with MR. Late CT has low CNR, which is a label-noise caveat.

### 2.4 Cury RC, Nieman K, Shapiro MD, et al. Comprehensive assessment of myocardial perfusion defects, regional wall motion, and left ventricular function by using 64-section multidetector CT. *Radiology* 2008;248(2):466-75.
- DOI: 10.1148/radiol.2482071478 · PMID 18641250 · PMC2797649
- URL opened: https://pubmed.ncbi.nlm.nih.gov/18641250/
- Numbers (abstract):
  - 102 patients (34 with acute MI).
  - Perfusion defect plus wall-motion abnormality detected acute MI with sensitivity 94% (32/34) and specificity 97% (66/68).
  - Perfusion-defect size vs SPECT: r=0.48.
- Use for the plan: rest CCTA perfusion defects are clinically readable for acute MI.

### 2.5 Osawa K, Miyoshi T, Miki T, et al. Diagnostic Performance of First-Pass Myocardial Perfusion Imaging without Stress with Computed Tomography (CT) Compared with Coronary CT Angiography Alone, with Fractional Flow Reserve as the Reference Standard. *PLoS One* 2016;11(2):e0149170.
- DOI: 10.1371/journal.pone.0149170 · PMID 26894686 · PMC4764509
- URL opened: https://pubmed.ncbi.nlm.nih.gov/26894686/
- Numbers (abstract):
  - 53 patients, 75 vessels; FFR <0.8 was positive.
  - Per-vessel AUC: CCTA+rest first-pass MPI 0.81 (0.73-0.90) vs CCTA 0.70 (0.61-0.81), P=0.036.
  - Rest MPI reclassified 38% of CCTA false positives as true negatives.
- Use for the plan: the rest-only CCTA myocardium carries information that predicts FFR. This is the core premise of the plan.
- Related (verified): Osawa K et al., *Heart* 2014;100(13):1008-15, DOI 10.1136/heartjnl-2013-305468, PMID 24763490. In 145 patients against ICA, per-vessel AUC rose from 0.84 to 0.89 (p=0.02) and specificity from 87% to 94% (abstract).

### 2.6 Han D, Lee JH, Rizvi A, et al. Incremental role of resting myocardial computed tomography perfusion for predicting physiologically significant coronary artery disease: A machine learning approach. *J Nucl Cardiol* 2018;25(1):223-233.
- DOI: 10.1007/s12350-017-0834-y · PMID 28303473
- URL opened: https://pubmed.ncbi.nlm.nih.gov/28303473/
- Numbers (abstract):
  - 252 patients; FFR <0.80.
  - AUC: CT stenosis 0.68 (0.62-0.74) vs stenosis+resting CTP with gradient boosting 0.75 (0.69-0.81), P=.001. NRI 0.52.
- Use for the plan: an ML baseline for rest-CCTA myocardial features vs FFR.

### 2.7 Xiong G, Kola D, Heo R, et al. Myocardial perfusion analysis in cardiac computed tomography angiographic images at rest. *Med Image Anal* 2015;24(1):77-89.
- DOI: 10.1016/j.media.2015.05.010 · PMID 26073787 · PMC4536577
- URL opened: https://pubmed.ncbi.nlm.nih.gov/26073787/
- Numbers (abstract):
  - LV segmentation error: endocardium 1.00 ± 0.39 mm, epicardium 1.06 ± 0.43 mm.
  - Features: normalised perfusion intensity, TPR and wall thickness.
  - AdaBoost against QCA: accuracy 0.70, sensitivity 0.79, specificity 0.64.
- Use for the plan: the closest prior work. Endo/epi surface model plus TPR and thickness features from rest CCTA. This is a baseline to beat.

### 2.8 Thomas DM, Larson CW, Cheezum MK, et al. Rest-Only Myocardial CT Perfusion in Acute Chest Pain. *South Med J* 2015;108(11):688-94.
- DOI: 10.14423/SMJ.0000000000000372 · PMID 26539951
- URL opened: https://pubmed.ncbi.nlm.nih.gov/26539951/
- Numbers (abstract):
  - 183 ED CCTAs; 4 patients (stated as 1.4% in the abstract) had obstructive CAD.
  - TPR <0.99 was applied to rest CCTA using a 17-segment model.
- Use for the plan: only a 4-patient case series. Cite at most as evidence that TPR has been applied to routine rest CCTA, not as evidence of accuracy.

---

## 3. Late iodine enhancement (LIE) and CT-ECV vs CMR

### 3.1 Gerber BL, Belge B, Legros GJ, et al. Characterization of acute and chronic myocardial infarcts by multidetector computed tomography: comparison with contrast-enhanced magnetic resonance. *Circulation* 2006;113(6):823-33.
- DOI: 10.1161/CIRCULATIONAHA.104.529511 · PMID 16461822
- URL opened: https://pubmed.ncbi.nlm.nih.gov/16461822/
- Numbers (abstract):
  - 16 acute and 21 chronic MI patients.
  - Segmental concordance with CE-MR: early hypoenhancement 92% (κ=0.54); late hyperenhancement 82% (κ=0.61).
  - Size correlation: r=0.93 (early) and r=0.89 (late).
  - Iodine kinetics resembled gadolinium (rabbit hearts).
- Use for the plan: the foundational validation of LIE against LGE. Gives a label-agreement ceiling of κ≈0.6.

### 3.2 Bettencourt N, Ferreira ND, Leite D, et al. CAD detection in patients with intermediate-high pre-test probability: low-dose CT delayed enhancement detects ischemic myocardial scar with moderate accuracy but does not improve performance of a stress-rest CT perfusion protocol. *JACC Cardiovasc Imaging* 2013;6(10):1062-1071.
- DOI: 10.1016/j.jcmg.2013.04.013 · PMID 24011773
- URL opened: https://pubmed.ncbi.nlm.nih.gov/24011773/
- Numbers (abstract):
  - 105 patients; CMR-LGE was the reference.
  - Low-dose CT delayed enhancement: accuracy 90%, sensitivity 53%, specificity 98%, PPV 82%, NPV 91%.
  - Adding CTDE did not improve CAD detection: 90/77/77/90% vs 90/81/80/90% without it.
- Use for the plan: low-dose LIE misses scar (sensitivity 53%). This supports learning scar cues from the arterial phase rather than relying on LIE.

### 3.3 Ohta Y, Kitao S, Yunaga H, et al. Myocardial Delayed Enhancement CT for the Evaluation of Heart Failure: Comparison to MRI. *Radiology* 2018;288(3):682-691.
- DOI: 10.1148/radiol.2018172523 · PMID 29989514
- URL opened: https://pubmed.ncbi.nlm.nih.gov/29989514/
- Numbers (abstract):
  - 44 patients, dual-energy CT.
  - Iodine-density images: segment sensitivity 92% (195/213), specificity 98% (481/491).
  - AUC: iodine 0.97, 40-keV images 0.95.
  - Inter-reader κ: 0.82 (iodine) and 0.72 (40 keV).
- Use for the plan: dual-energy and iodine maps give the best LIE labels.

### 3.4 Gatti M, De Filippo O, Cura Curà G, et al. Diagnostic accuracy of late iodine enhancement on cardiac CT for myocardial tissue characterization: a systematic review and meta-analysis. *Eur Radiol* 2025;35(6):3054-3067.
- DOI: 10.1007/s00330-024-11283-5 · PMID 39702631
- URL opened: https://pubmed.ncbi.nlm.nih.gov/39702631/
- Numbers (abstract):
  - 14 studies, 526 patients, 5,758 segments.
  - Patient level: sensitivity 0.96 (0.88-0.99), specificity 0.95 (0.88-0.98), HSROC AUC 0.98.
  - Segment level: sensitivity 0.86 (0.79-0.91), specificity 0.98 (0.96-0.99), AUC 0.97.
  - Dual-energy raised segment sensitivity to 0.93.
- Use for the plan: the best current summary of LIE vs LGE. Cite this for "LIE is a valid scar reference".

### 3.5 Palmisano A, Vignale D, Benedetti G, et al. Late iodine enhancement cardiac computed tomography for detection of myocardial scars: impact of experience in the clinical practice. *Radiol Med* 2020;125(2):128-136.
- DOI: 10.1007/s11547-019-01108-7 · PMID 31784926
- URL opened: https://pubmed.ncbi.nlm.nih.gov/31784926/
- Numbers (abstract):
  - 40 patients, 680 segments.
  - Per-segment sensitivity: 85% for the experienced reader vs 62% for the less experienced reader. Specificity 99%.
  - Missed scars were mostly non-ischaemic, had burden <6%, and lower CNR (2.33 vs 3.54).
- Use for the plan: LIE reading depends on the reader. This argues for automated layer-wise scar quantification.

### 3.6 Palmisano A, Vignale D, Tadic M, et al. Myocardial Late Contrast Enhancement CT in Troponin-Positive Acute Chest Pain Syndrome. *Radiology* 2022;302(3):545-553.
- DOI: 10.1148/radiol.211288 · PMID 34874200
- URL opened: https://pubmed.ncbi.nlm.nih.gov/34874200/
- Numbers (abstract):
  - 84 patients.
  - Adding a late-enhancement scan at 10 minutes raised the diagnostic rate from 50% (42/84) to 90% (76/84), P<.001.
- Use for the plan: clinical value of adding a late scan to a CTA protocol.

### 3.7 Kokawa T, Kitagawa K, Nakamura S, et al. Myocardial late enhancement using dual-source CT: intraindividual comparison of single-energy shuttle and dual-energy acquisition. *Insights Imaging* 2025;16(1):64.
- DOI: 10.1186/s13244-025-01944-4 · PMID 40120007 · PMC11929652
- URLs opened: https://pubmed.ncbi.nlm.nih.gov/40120007/ and https://pmc.ncbi.nlm.nih.gov/articles/PMC11929652/
- Numbers:
  - (abstract) 15 patients. Inter-observer κ for infarct detection: 0.981 in shuttle mode vs 0.808 in DE mode.
  - **[full text, "Radiation dose" + Table 4]** DLP of the CT-LE scan: 149.1 ± 16.7 mGy·cm (shuttle) vs 224.7 ± 43.6 mGy·cm (DE). Other DLPs: CCTA 168.4 ± 65.8, stress dynamic CTP 224.8 ± 44.0, pre-contrast 47.8 ± 5.5. Whole exam 822.0 ± 132.0 mGy·cm.
- Use for the plan: a concrete dose for the added late scan, which is about the same DLP as the CCTA itself. Effective dose is not stated in mSv; any mSv figure would need a conversion factor (e.g. k≈0.014-0.026 mSv/mGy·cm), and that is our assumption, not the paper's.

### 3.8 Klambauer K, Klotz E, Moser LJ, et al. Myocardial Late Enhancement With Photon-Counting Detector CT in Spontaneous Coronary Artery Dissection: Prospective Comparison With Cardiac MRI. *Invest Radiol* 2026;61(1):32-40.
- DOI: 10.1097/RLI.0000000000001203 · PMID 40273434 · PMC12662126
- URL opened: https://pubmed.ncbi.nlm.nih.gov/40273434/
- Numbers (abstract):
  - 17 patients, 24 paired scans; late enhancement acquired 5 minutes after contrast.
  - Agreement with LGE: κ=0.832 in the acute phase, 0.944 against LGE plus edema, and 0.956 at follow-up.
- Use for the plan: photon-counting LIE now agrees almost perfectly with CMR.

### 3.9 Nacif MS, Kawel N, Lee JJ, et al. Interstitial myocardial fibrosis assessed as extracellular volume fraction with low-radiation-dose cardiac CT. *Radiology* 2012;264(3):876-83.
- DOI: 10.1148/radiol.12112458 · PMID 22771879 · PMC3426854
- URL opened: https://pubmed.ncbi.nlm.nih.gov/22771879/
- Numbers (abstract):
  - 24 subjects. CT-ECV vs MR-ECV: r=0.82.
  - Mean dose 1.98 ± 0.16 mSv per cardiac CT acquisition.
- Use for the plan: the first CT-ECV paper. Supports "a few mSv or less" for an added equilibrium scan.

### 3.10 Kurita Y, Kitagawa K, Kurobe Y, et al. Estimation of myocardial extracellular volume fraction with cardiac CT in subjects without clinical coronary artery disease: A feasibility study. *J Cardiovasc Comput Tomogr* 2016;10(3):237-41.
- DOI: 10.1016/j.jcct.2016.02.001 · PMID 26968674
- URL opened: https://pubmed.ncbi.nlm.nih.gov/26968674/
- Numbers (abstract):
  - 38 subjects. Normal CT-ECV 26.1 ± 2.0% (range 22.6-30.0%).
  - ICC: inter-observer 0.968, intra-observer 0.971.
  - ECV rose with age (r=0.46). Women 27.1% vs men 25.5%.
- Use for the plan: normal ECV reference range for CT.

### 3.11 Treibel TA, Bandula S, Fontana M, et al. Extracellular volume quantification by dynamic equilibrium cardiac computed tomography in cardiac amyloidosis. *J Cardiovasc Comput Tomogr* 2015;9(6):585-92.
- DOI: 10.1016/j.jcct.2015.07.001 · PMID 26209459 · PMC4684159
- URL opened: https://pubmed.ncbi.nlm.nih.gov/26209459/
- Numbers (abstract):
  - 26 amyloid vs 27 aortic stenosis patients.
  - ECV-CT vs ECV-CMR: r²=0.85 at 5 minutes and 0.74 at 15 minutes.
  - ECV-CT 0.54 ± 0.11 (amyloid) vs 0.28 ± 0.04 (AS), with no overlap.
- Use for the plan: CT-ECV. **Note:** the requested "Treibel 2015 Circ Cardiovasc Imaging" is actually this JCCT paper (see UNVERIFIED).

### 3.12 Han D, Lin A, Kuronuma K, et al. Cardiac Computed Tomography for Quantification of Myocardial Extracellular Volume Fraction: A Systematic Review and Meta-Analysis. *JACC Cardiovasc Imaging* 2023;16(10):1306-1317.
- DOI: 10.1016/j.jcmg.2023.03.021 · PMID 37269267
- URL opened: https://pubmed.ncbi.nlm.nih.gov/37269267/
- Numbers (abstract):
  - 13 studies, 383 patients.
  - Pooled CT-ECV vs CMR-ECV correlation: 0.90 (0.86-0.95). Mean difference 0.96% (0.14-1.78%).
  - Correlation by technique: dual-energy 0.94 vs single-energy 0.87 (P=0.01).
- Use for the plan: meta-analytic agreement of CT-ECV with CMR.

### 3.13 Zhang H, Guo H, Liu G, et al. CT for the evaluation of myocardial extracellular volume with MRI as reference: a systematic review and meta-analysis. *Eur Radiol* 2023;33(12):8464-8476.
- DOI: 10.1007/s00330-023-09872-x · PMID 37378712
- URL opened: https://pubmed.ncbi.nlm.nih.gov/37378712/
- Numbers (abstract):
  - 17 studies, 459 patients, 2,231 segments.
  - Per patient: mean difference 0.07% (LOA −0.42 to 0.55%), r=0.89. Per segment: r=0.84.
  - Septal segments r=0.88 vs non-septal 0.76 (p=0.009).
- Use for the plan: segment-level CT-ECV is noisier outside the septum, which is relevant to per-layer and per-segment targets.

### 3.14 Aquino GJ, O'Doherty J, Schoepf UJ, et al. Myocardial Characterization with Extracellular Volume Mapping with a First-Generation Photon-counting Detector CT with MRI Reference. *Radiology* 2023;307(2):e222030.
- DOI: 10.1148/radiol.222030 · PMID 36719292
- URL opened: https://pubmed.ncbi.nlm.nih.gov/36719292/
- Numbers (abstract):
  - 29 participants.
  - Dual-energy PCD-CT vs MRI: r=0.82 (mid-ventricular) and 0.91 (global); ICC 0.81 and 0.90.
  - Dual-energy overestimated ECV by about 2%; single-energy underestimated it by about 3%.
  - CTDIvol 10.1 vs 16.8 mGy (40% lower with dual-energy).
- Use for the plan: photon-counting CT-ECV; the systematic bias matters for harmonising labels across scanners.

---

## 4. Myocardial fat (lipomatous metaplasia) in chronic infarct

### 4.1 Ichikawa Y, Kitagawa K, Chino S, et al. Adipose tissue detected by multislice computed tomography in patients after myocardial infarction. *JACC Cardiovasc Imaging* 2009;2(5):548-55.
- DOI: 10.1016/j.jcmg.2009.01.010 · PMID 19442939
- URL opened: https://pubmed.ncbi.nlm.nih.gov/19442939/
- Numbers (abstract):
  - LV fat in 62% (33/53) of MI patients vs 3% (2/63) of controls.
  - Location: subendocardial in 94% (30/32), mid-wall 3%, subepicardial 3%.
  - Infarct age 8.2 ± 4.4 years with fat vs 2.2 ± 2.6 years without. Fat present in 89% (30/35) with infarct age ≥3 years; none with infarct age <10 months.
- Use for the plan: the key reason a *layer* model matters. Fat sits in the subendocardial layer and confounds perfusion and LIE reading.

### 4.2 Zafar HM, Litt HI, Torigian DA. CT imaging features and frequency of left ventricular myocardial fat in patients with CT findings of chronic left ventricular myocardial infarction. *Clin Radiol* 2008;63(3):256-62.
- DOI: 10.1016/j.crad.2007.08.007 · PMID 18275865
- URL opened: https://pubmed.ncbi.nlm.nih.gov/18275865/
- Numbers (abstract):
  - LV myocardial fat in 51% of 47 patients with CT evidence of chronic MI.
  - Typically thin linear or curvilinear and subendocardial, often with wall thinning and/or calcification.
- Use for the plan: confirms the prevalence (about 50-60%) and the subendocardial pattern.

### 4.3 Xu L, Khoshknab M, Berger RD, et al. Lipomatous Metaplasia Enables Ventricular Tachycardia by Reducing Current Loss Within the Protected Corridor. *JACC Clin Electrophysiol* 2022;8(10):1274-1285.
- DOI: 10.1016/j.jacep.2022.07.005 · PMID 36266004 · PMC11148646
- URLs opened: https://pubmed.ncbi.nlm.nih.gov/36266004/ and https://pmc.ncbi.nlm.nih.gov/articles/PMC11148646/
- Numbers:
  - (abstract) 30 patients (INFINITY study). 83 of 84 VT-critical corridors (99%) traversed or were adjacent to LM, vs 13 (4%) of non-VT corridors.
  - **[full text, Methods]** "LM volume was identified from CT images as myocardial area with attenuation ranging from −180 to 0 HU and volume >1 mm²". Scar was defined on LGE as >60% of maximal signal and not LM at <0 HU on CT.
  - **[full text, Table 3]** Median LM attenuation: −30.1 HU (critical corridors) vs −23.3 HU (non-critical).
- Use for the plan: a verified CT HU window for intramyocardial fat (−180 to 0 HU) and its clinical relevance for VT substrate.

---

## 5. Wall thinning in chronic infarct

### 5.1 Shah DJ, Kim HW, James O, et al. Prevalence of regional myocardial thinning and relationship with myocardial scarring in patients with coronary artery disease. *JAMA* 2013;309(9):909-18. (This is a CMR study.)
- DOI: 10.1001/jama.2013.1381 · PMID 23462787 · PMC3979456
- URL opened: https://pubmed.ncbi.nlm.nih.gov/23462787/
- Numbers (abstract):
  - Thinning defined as end-diastolic wall thickness ≤5.5 mm. Present in 19% (201/1055) of CAD patients.
  - Scar extent in thinned regions was 72%, but 18% of thinned regions had ≤50% scar.
  - After revascularisation, thickness in limited-scar regions went from 4.4 to 7.5 mm.
- Use for the plan: thinning alone is not scar. A layer-wise enhancement map adds information beyond thickness.

### 5.2 Komatsu Y, Cochet H, Jadidi A, et al. Regional myocardial wall thinning at multidetector computed tomography correlates to arrhythmogenic substrate in postinfarction ventricular tachycardia. *Circ Arrhythm Electrophysiol* 2013;6(2):342-50.
- DOI: 10.1161/CIRCEP.112.000191 · PMID 23476043
- URL opened: https://pubmed.ncbi.nlm.nih.gov/23476043/
- Numbers (abstract):
  - 13 patients. Area with CT wall thickness <5 mm correlated with endocardial low voltage (R=0.82).
  - 87% (469/538) of LAVA lay within the <5 mm area.
  - Very late LAVA: 93% were in areas <3 mm.
- Use for the plan: CT thickness thresholds of <5 mm and <3 mm have electrophysiological meaning.

### 5.3 Yamashita S, Sacher F, Hooks DA, et al. Myocardial wall thinning predicts transmural substrate in patients with scar-related ventricular tachycardia. *Heart Rhythm* 2017;14(2):155-163.
- DOI: 10.1016/j.hrthm.2016.11.012 · PMID 28104088
- URL opened: https://pubmed.ncbi.nlm.nih.gov/28104088/
- Numbers (abstract):
  - 42 patients. Wall thinning <5 mm in 86%; severe thinning <2 mm in 48%.
  - Severe thinning by aetiology: ischaemic 77%, post-myocarditis 27%, DCM 0%.
- Use for the plan: CT thinning thresholds (<5 mm and <2 mm) that are used in clinical VT work.

### 5.4 Takigawa M, Martin R, Cheniti G, et al. Detailed comparison between the wall thickness and voltages in chronic myocardial infarction. *J Cardiovasc Electrophysiol* 2019;30(2):195-204.
- DOI: 10.1111/jce.13767 · PMID 30288836
- URL opened: https://pubmed.ncbi.nlm.nih.gov/30288836/
- Numbers (abstract):
  - 12 patients. Of multicomponent electrograms, 86.4% lay in CT wall thickness <4 mm and 97.1% in <5 mm.
  - Critical VT sites were located in areas 1-4 mm thick.
- Use for the plan: supporting evidence for the thinning thresholds.
- (Nieman 2006, entry 2.2, also shows thinning in chronic MI on CCTA, p<0.01.)

---

## 6. AI on the CCTA myocardium for functionally significant stenosis

### 6.1 Zreik M, Lessmann N, van Hamersvelt RW, et al. Deep learning analysis of the myocardium in coronary CT angiography for identification of patients with functionally significant coronary artery stenosis. *Med Image Anal* 2018;44:72-85.
- DOI: 10.1016/j.media.2017.11.008 · PMID 29197253
- URL opened: https://pubmed.ncbi.nlm.nih.gov/29197253/
- Numbers (abstract):
  - 166 patients with invasive FFR.
  - LV myocardium segmentation: Dice 0.91, mean absolute distance 0.7 mm (20 images).
  - Classification (126 scans, 50 repeats of 10-fold CV): AUC 0.74 ± 0.02.
  - At sensitivity 0.60, 0.70 and 0.80, specificity was 0.77, 0.71 and 0.59.
- Use for the plan: the main AI baseline. It used a whole-myocardium encoding with no layer separation.

### 6.2 van Hamersvelt RW, Zreik M, Voskuil M, et al. Deep learning analysis of left ventricular myocardium in CT angiographic intermediate-degree coronary stenosis improves the diagnostic accuracy for identification of functionally significant stenosis. *Eur Radiol* 2019;29(5):2350-2359.
- DOI: 10.1007/s00330-018-5822-3 · PMID 30421020 · PMC6443613
- URL opened: https://pubmed.ncbi.nlm.nih.gov/30421020/
- Numbers (abstract):
  - 126 patients; 64% had functionally significant stenosis.
  - AUC 0.76 (degree of stenosis + DL) vs 0.68 (degree of stenosis only).
  - Sensitivity/specificity: 84.6%/48.4% (combined) vs 92.6%/31.1% (stenosis only, ≥50%).
- Use for the plan: the clinical framing. DL analysis of the myocardium raises CCTA specificity in intermediate stenosis. The target to beat with layer-aware features.

---

## 7. Clinical reality: how often CTP/LIE is done, and the dose of the added scan

### 7.1 Catapano F, Moser LJ, Francone M, et al. Competence of radiologists in cardiac CT and MR imaging in Europe: insights from the ESCR Registry. *Eur Radiol* 2024;34(9):5666-5677.
- DOI: 10.1007/s00330-024-10644-4 · PMID 38418626 · PMC11364788
- URLs opened: https://pubmed.ncbi.nlm.nih.gov/38418626/ and https://pmc.ncbi.nlm.nih.gov/articles/PMC11364788/
- Numbers:
  - (abstract) 432,265 exams in total (CT and MRI). Annual CT submissions rose from 3,368 to 15,267 (2011-2022). Suspected CAD was the CT indication in 59%.
  - **[full text, Table 3 "Medication for cardiac CT"]** "Adenosine for myocardial perfusion study": 15 of 205,999 cardiac CTs (0.01%); 9 of 121,051 suspected-CAD CTs.
  - **[full text, Results]** By contrast, pharmacological stress was used in 25.4% of MRIs (57,428/226,266).
- Use for the plan: in real-world European practice, stress CTP is almost never acquired. Rest CCTA is the data that actually exists.
- Caveat: this is a medication field, and regadenoson for CT is not listed. Treat 0.01% as an indicator, not an exact CTP rate.

### 7.2 Dose of the added perfusion or late scan (pulled from entries above)
- Late-enhancement scan DLP: 149-225 mGy·cm, vs CCTA 168 mGy·cm (Kokawa 2025, Table 4).
- One CT-ECV acquisition: 1.98 mSv (Nacif 2012).
- Dynamic CT-MPI: median DLP 313 mGy·cm vs CTA 138 mGy·cm (Nous 2022).
- Stress CTP+CCTA: 10.4 ± 2.7 mSv (Andreini 2024).
- Tiered CT arm: median 3.1 mSv (Lubbers 2018).
- Early 64/256-row rest+stress CTP: 16.8 and 21.6 mSv (George 2009, full text).

---

## UNVERIFIED / not found / corrections

- **"Treibel et al. 2015 Circ Cardiovasc Imaging" (CT-ECV):** not found in that journal. The verified 2015 Treibel CT-ECV paper is in *J Cardiovasc Comput Tomogr* (entry 3.11). Treibel TA et al., *Heart* 2015, "Extracellular volume quantification in isolated hypertension…", was not checked. Do not cite the Circ CV Imaging version.
- **"Scully et al. 2020 meta-analysis" of ECV:** no such meta-analysis was found. Scully PR 2020 papers do exist: *JACC Cardiovasc Imaging* 2020;13:2177-2189 (DOI 10.1016/j.jcmg.2020.05.029, ECV-CT in TAVR; title confirmed only via PubMed esummary, abstract not read, no numbers taken), and a 2018 review in *Curr Cardiol Rep*. For meta-analyses use Han 2023 (3.12) or Zhang 2023 (3.13).
- **"Gupta M et al." on myocardial fat on CT:** not located. Zafar 2008 (4.2) covers it.
- **Fat HU thresholds "<−10 HU" or "<−30 HU":** not verified in any paper I opened. The only verified CT fat window is −180 to 0 HU (Xu 2022, full text). The Ichikawa 2009 threshold is in the paywalled full text and was not read.
- **"Pontone ADVANTAGE (static CTP in stents)" primary results:** only the design paper (JCCT 2018) and Advantage 2 (Radiology 2024) were verified. Andreini D et al., *JACC Cardiovasc Imaging* 2020;13:732-742 (DOI 10.1016/j.jcmg.2019.05.031, "CT Perfusion Versus Coronary CT Angiography in Patients With Suspected In-Stent Restenosis or CAD Progression") appeared in a PubMed search. Its abstract was not read and no numbers were taken.
- **A large outcome or accuracy study of rest-CCTA TPR:** not found. Evidence is limited to small studies (Osawa 2014/2016, Han 2018, Xiong 2015) and one case series (Thomas 2015).
- **Rodriguez-Granillo CT wall-thinning thresholds:** not found. The thinning thresholds above come from Komatsu, Yamashita, Takigawa and Shah (CMR).
- **Effective dose (mSv) of a late scan with modern scanners:** only DLP is verified (Kokawa). Converting DLP to mSv uses a k-factor, which is our assumption.
- **Mendoza DD et al.** "Viability imaging by cardiac computed tomography", *J Cardiovasc Comput Tomogr* 2010;4:83-91 (DOI 10.1016/j.jcct.2010.01.019, PMID 20430338): exists, but it is a review. Not read for numbers.
