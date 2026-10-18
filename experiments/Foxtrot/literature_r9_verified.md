# Verified literature for 4-class coronary (LM/LAD/LCx/RCA) nnU-Net ResEnc plan

Compiled 2026-10-18. Every number below marked "verified: read in source" was read by me in the downloaded PDF/HTML/README text. Items I could not open or confirm are flagged "could not verify" and collected at the end.

---

## 3. nnU-Net Revisited and original nnU-Net

**Isensee F, Wald T, Ulrich C, Baumgartner M, Roy S, Maier-Hein K, Jaeger PF. "nnU-Net Revisited: A Call for Rigorous Validation in 3D Medical Image Segmentation." MICCAI 2024. arXiv:2404.09556.** — verified: read in source (arXiv PDF + nnU-Net repo `documentation/resenc_presets.md`).

- Presets: paper Sec. 3.1: "we introduce new nnU-Net ResEnc presets, which use nnU-Net's existing automatic adaptation of batch and patch sizes to target varying VRAM budgets ("M", "L", "XL")". All trainings on single A100 40GB.
- VRAM targets (repo README `documentation/resenc_presets.md`, verbatim): "nnU-Net ResEnc M: similar GPU budget to the standard UNet configuration. Best suited for GPUs with 9-11GB VRAM. Training time: ~12h on A100"; "ResEnc L: requires a GPU with 24GB VRAM. ~35h"; "ResEnc XL: requires a GPU with 40GB VRAM. ~66h". README also says "We recommend nnU-Net ResEnc L as the new default nnU-Net configuration!"
- **Table 1** (DSC %, 5-fold CV, trained from scratch; columns BTCV/ACDC/LiTS/BraTS/KiTS/AMOS, VRAM [GB], RT [h]):
  - nnU-Net (org.): 83.08 / 91.54 / 80.09 / 91.24 / 86.04 / 88.64; 7.70 GB; 9 h
  - ResEnc M: 83.31 / 91.99 / 80.75 / 91.26 / 86.79 / 88.77; 9.10 GB; 12 h
  - ResEnc L: 83.35 / 91.69 / 81.60 / 91.13 / 88.17 / 89.41; 22.70 GB; 35 h
  - ResEnc XL: 83.28 / 91.48 / 81.19 / 91.18 / 88.67 / 89.68; 36.60 GB; 66 h
  - MedNeXt L k3: 84.70 / 92.65 / 82.14 / 91.35 / 88.25 / 89.62; 17.3 GB; 68 h
  - SwinUNETR: 78.89 / 91.29 / 76.50 / 90.68 / 81.27 / 83.81
  - SwinUNETRV2: 80.85 / 92.01 / 77.85 / 90.74 / 84.14 / 86.24
  - nnFormer: 80.86 / 92.40 / 77.40 / 90.22 / 75.85 / 81.55
  - CoTr: 81.95 / 90.56 / 79.10 / 90.73 / 84.59 / 88.02
  - No-Mamba Base: 83.69 / 91.89 / 80.57 / 91.26 / 85.98 / 89.04
  - U-Mamba Bot: 83.51 / 91.79 / 80.40 / 91.26 / 86.22 / 89.13
  - U-Mamba Enc: 82.41 / 91.22 / 80.27 / 90.91 / 86.34 / 88.38
  - A3DS SegResNet: 80.69 / 90.69 / 79.28 / 90.79 / 81.11 / 87.27
- Headline finding (verbatim, Results): "CNN-based U-Nets yield best performance." "In contrast to prior claims, Transformer-based architectures (SwinUNETR, nnFormer, CoTr) fail to match the performance of CNNs. This includes not matching performance of the original nnU-Net". "comparison against the previously missing baseline "No-Mamba Base" reveals that the mamba layers actually have no effect on performance". Note honestly: MedNeXt (a ConvNeXt CNN) "consistently stands out with the best performance on all datasets except KiTS", so ResEnc is not the top on every column; ResEnc XL is best on KiTS (88.67) and ResEnc L/XL near-top on AMOS.
- Appendix Table 2 (KiTS fold 0): ResEnc M 87.91 (11.39 GPU h, 8805 MB, patch 128×128×128); ResEnc L 88.60 (35.28 GPU h, 24223 MB, patch 160×224×192).
- Note: none of the benchmark datasets is coronary/vascular.

**Isensee F, Jaeger PF, Kohl SAA, Petersen J, Maier-Hein KH. "nnU-Net: a self-configuring method for deep learning-based biomedical image segmentation." Nature Methods 2021;18:203–211. doi:10.1038/s41592-020-01008-z.** — verified: bibliographic record via Crossref (title, journal, vol 18, pp 203–211, authors, online 7 Dec 2020). Body not re-read (no numbers needed from it).

---

## 6. Topology-aware losses

**Kirchhoff Y, Rokuss MR, Roy S, Kovacs B, Ulrich C, Wald T, Zenk M, Vollmuth P, Kleesiek J, Isensee F, Maier-Hein K. "Skeleton Recall Loss for Connectivity Conserving and Resource Efficient Segmentation of Thin Tubular Structures." ECCV 2024. arXiv:2404.03010.** — verified: read in source (arXiv PDF).

- Datasets (Table 1): Roads, DRIVE (retinal vessels, 2D), Cracks, ToothFairy (inferior alveolar canal, 3D CT), TopCoW (Circle of Willis, 3D, 200 samples, binary and multi-class, 13 vessel classes). **No coronary/CCTA dataset.** The closest vascular 3D evidence is TopCoW (CTA+MRA intracranial arteries).
- **Table 2** (nnU-Net backbone, test set; Dice / clDice / β0 err / β1 err):
  - TopCoW binary: default nnUNet 93.55 / 98.25 / 0.743 / 1.800; +clDice loss 93.64 / 98.35 / 0.514 / 1.986; +Skeleton Recall 93.72 / 98.48 / 0.500 / 1.586
  - TopCoW multi-class: default nnUNet 85.36 / 93.68 / 0.137 / 0.0571; +clDice loss "– Out Of Memory –"; +Skeleton Recall 86.59 / 94.35 / 0.151 / 0.056
  - DRIVE (5-fold CV): default 80.87 / 80.26 / 57.00 / 22.80; +clDice 81.05 / 80.68; +SkelRecall 80.99 / 80.83 / 38.75 / 21.50
- Overhead (Sec. 5.3, verbatim): clDice loss "leads to approximately 88% additional training time and 52% more VRAM consumption compared to the plain nnUNet backbone when averaged across our 5 datasets (excluding multi-class TopCoW)", whereas Skeleton Recall needs "only an additional 8% training time and 2% higher VRAM consumption".
- Relevance: multi-class TopCoW is the most analogous published setting to our 4-class tree (multi-label vessel components), +1.23 Dice / +0.67 clDice; clDice loss OOM in that multi-class 3D setting.

**Shit S, Paetzold JC, Sekuboyina A, Ezhov I, Unger A, Zhylka A, Pluim JPW, Bauer U, Menze BH. "clDice — a Novel Topology-Preserving Loss Function for Tubular Structure Segmentation." CVPR 2021. arXiv:2003.07311.** — verified: read in source (arXiv PDF).

- Datasets (Sec. 5.1): DRIVE, Massachusetts Roads, CREMI (2D); synthetic 3D vessels and Vessap (3D mouse-brain microvasculature). **No coronary dataset.**
- Table 1, Vessap (3D), U-Net 1 ch: soft-dice Dice 87.46 / clDice 91.18; Lc α=0.5 Dice 87.82 / clDice 93.03. U-Net 2 ch: soft-dice 87.98 / 90.16; Lc α=0.4 88.57 / 93.25.

---

## 1a. ImageCAS-X (the label source for our model) — what it does and does NOT report

**Bransby KM, Øksnebjerg E, Kjær K, Kirkeby J, El Youssef Y, Jiménez A, Pedersson PR, de Knegt MC, Kofoed KF, Paulsen RR. "ImageCAS-X: a dataset and benchmark for coronary artery segmentation and centerline extraction in coronary CT angiography." arXiv:2608.30404v1 [cs.CV], 31 Aug 2026.** Data: Zenodo doi:10.5281/zenodo.21887809 (record checked via Zenodo API: published 2026-08-11, licence cc-by-4.0, files ImageCAS-X_dataset.zip 1.44 GB + pretrained_weights.zip 1.64 GB; ImageCAS volumes stay on Kaggle under Apache 2.0). Code: github.com/kitbransby/ImageCAS-X. — verified: read in source (arXiv PDF, full text incl. supplement).

- Cohort: 1,000 ImageCAS scans, Guangdong Provincial People's Hospital 2012–2018, single Siemens 128-slice dual-source scanner; 200 excluded (114 motion, 76 step artefacts, ...), **800 retained**; split **560 train / 80 val / 160 test** (random 70/10/20). Dominance: 729 (91.1%) right, 41 (5.1%) left, 30 (3.8%) co-dominant. Disease: 388 (48.5%) diseased.
- Labels: 14 segment classes (Supp. Table 4): 1 LM, 2 LAD, 3 LCx, 4 D1, 5 D2, 6 OM1, 7 OM2, 8 IM (ramus), 9 RCA, 10 R-PDA, 11 R-PLA, 12 L-PDA, 13 L-PLA, 14 Other (D3/D4/OM3/OM4). LAD/LCx/RCA not split proximal/mid/distal. Segment names propagated to voxels by nearest centerline point. → **Maps cleanly to our 4 territories**: LM={1}; LAD={2,4,5}; LCx={3,6,7,8,12,13}; RCA={9,10,11}; class 14 needs D vs OM disambiguation (it pools D3/D4 with OM3/OM4 — so "Other" cannot be assigned to a territory by ID alone).
- Benchmark preprocessing: isotropic 0.5 mm, HU clip [−200, 1000]; RTX 5090 32 GB; 1,000 epochs × 250 iters.
- **Table 1 — INTER-OBSERVER (not model) per-segment agreement, 160 test scans**, lumen DSC (%):
  LM 91.9 ± 13.7 (n=155); LAD 92.3 ± 6.7 (160); LCx 84.8 ± 19.8 (159); D1 79.9 ± 28.7; D2 82.9 ± 24.3; OM1 74.1 ± 32.3; OM2 77.7 ± 29.1; IM 80.6 ± 24.5; RCA 95.3 ± 5.0 (160); R-PDA 82.6 ± 21.9; R-PLA 83.6 ± 18.6; L-PDA 75.1 ± 29.0 (n=8); L-PLA 70.9 ± 27.2 (n=9); Other 81.3 ± 17.0; All segments 92.8 ± 3.1. Segment-presence agreement 95.3% overall. Text: "the main branches (LM, LAD, LCx and RCA) were the best segmented (DSC 84.8–95.3), while the side branches were consistently worse (70.9–83.6)." Inter-observer DSC is called "the upper-bound of agreement" because both annotators edited the same auto centerlines/U-Net initialisation.
- **Table 2 — MODEL results are BINARY LUMEN ONLY** (160 test scans; DSC % / HD95 mm / β err / clDice):
  TotalSegmentator 70.5 ± 6.2 / 19.59 / 4.6 / 76.0; 3D-FFR-UNet 84.9 / 15.93 / 4.8 / 89.8; ADE-HTL 87.7 / 2.97 / 1.5 / 93.2; Swin-UNETR 87.9 / 3.18 / 3.8 / 92.5; ImageCAS method 87.9 / 4.45 / 4.7 / 91.7; **nnU-Net 89.8 ± 3.2 / 7.08 / 5.6 / 92.3**; nnU-Net + clDice 90.0 ± 3.5 / 9.70 / 8.0 / 91.7; **CAS-Net 91.2 ± 2.8 / 2.99 / 1.9 / 93.3 (best)**; Inter-observer 92.8 ± 3.1 / 2.46 / 0.4 / 95.4; original ImageCAS labels vs ImageCAS-X 41.8 ± 6.7 / 16.15 / 7.0 / 78.2.
  (Note: inter-observer β err is 0.2 ± 0.4 in Table 1 "All segments" row but 0.4 ± 0.4 in Table 2 — internal inconsistency in the preprint.)
- Table 3 (inference): nnU-Net 153.9 M params (5 models), 2.5 GB peak, 102.3 s; CAS-Net 6.8 M, 15.5 s; analysts 2,100 s (35 min/scan).
- **ImageCAS-X does NOT report per-segment or per-territory MODEL accuracy, and no multi-class model.** A 4-class LM/LAD/LCx/RCA model trained on ImageCAS-X would therefore be (as far as I can find) the first per-territory model result on this dataset; the only per-segment yardstick is the inter-observer Table 1.
- Also states CAT08 and the MICCAI 2012 challenge data "were limited in scale and are no longer publicly available" and ASOCA "comprises only 60 cases".

## 2. TotalSegmentator `coronary_arteries`

**Wasserthal J, Breit HC, Meyer MT, Pradella M, Hinck D, Sauter AW, Heye T, Boll DT, Cyriac J, Yang S, Bach M, Segeroth M. "TotalSegmentator: Robust Segmentation of 104 Anatomic Structures in CT Images." Radiology: Artificial Intelligence 2023;5(5):e230024. doi:10.1148/ryai.230024.** — metadata verified via Crossref.

GitHub (github.com/wasserth/TotalSegmentator, master at commit a026545, 14 Oct 2026) — verified: read in source (README, CHANGELOG.md, totalsegmentator/map_tasks_config.py):
- README lists `coronary_arteries` ("also works on non-contrast images") and `coronary_arteries_LEGACY` ("previous version of the coronary_arteries task used until v2.12.0") under "**Available with a license** (free licenses available for non-commercial usage ... For a commercial license contact jakob.wasserthal@usb.ch)". → not Apache-2.0 open; needs (free academic) licence key.
- **Single binary class** `coronary_arteries` (map_to_binary.py: `1: "coronary_arteries"`) — no LM/LAD/LCx/RCA split, so it cannot serve as a per-branch baseline.
- CHANGELOG: Release 1.4.0 "add coronary artery model"; Release 2.5.0 "update `coronary_arteries` task: increased number of training subjects, including non-contrast images"; Release 2.13.0 (17.03.2026) "update `coronary_arteries` task: new skeleton-recall model with slightly increased accuracy. The previous version is now available as `coronary_arteries_LEGACY`."
- map_tasks_config.py: coronary_arteries = task 509 "Dataset509_coronary_arteries_cm_nativ_400subj_SKELETON", trainer `nnUNetTrainerSkeletonRecall`, resample 0.7 mm iso, crop to heart (+20 voxels), `"commercial": True`; LEGACY = task 507 "Dataset507_coronary_arteries_cm_nativ_400subj".
- **Training data: could not verify.** Neither README, changelog nor config names the source; the folder name only implies ~400 subjects, contrast + native ("cm_nativ"). I found no statement that ImageCAS was used, so contamination when testing on ImageCAS cannot be confirmed or excluded. (The 70.5 DSC in ImageCAS-X Table 2 suggests it was not trained on ImageCAS-X labels; ImageCAS-X authors attribute the gap to annotation quality/protocol or distribution shift.)
- **Published accuracy:** the only number I found is ImageCAS-X Table 2: TotalSegmentator (zero-shot) DSC 70.5 ± 6.2, HD95 19.59 mm, clDice 76.0 on the 160 ImageCAS-X test scans (version not stated in the preprint). No accuracy for the coronary task in the README.

## 4c. ImageCAS (original)

**Zeng A, Wu C, Lin G, Xie W, Hong J, Huang M, et al. (Xu X corresponding). "ImageCAS: A large-scale dataset and benchmark for coronary artery segmentation based on computed tomography angiography images." Computerized Medical Imaging and Graphics 2023;109:102287. doi:10.1016/j.compmedimag.2023.102287 (Crossref-verified); preprint arXiv:2211.01607.** — verified: read in source (arXiv preprint text; I did not access the CMIG version of record, numbers could differ slightly there).

- 1,000 3D CTA, Siemens 128-slice dual-source scanner, Guangdong Provincial People's Hospital; 414 F / 586 M.
- Protocol (Sec. 5.1): "Experiments were evaluated using a 4-fold cross-validation approach, with a training set of 750 cases (50 cases are used for validation) and a test set of 250 cases." GitHub README: "An official data split is also prepared for fair comparison." (split is per-fold; README also notes duplicate "(1)" cases removed on 2023-04-17; dataset on Kaggle since 2023-11-01: kaggle.com/datasets/xiaoweixumedicalai/imagecas).
- **Table 4** (Dice % / HD mm / AHD mm): Direct segmentation 3D FCN 80.58 / 28.67 / 0.85; Patch 3D U-Net 72.01; TreeConvGRU 68.78; GCN 70.61; **Baseline (3D U-Net + U-Net++, coarse+dilation+multi-patch ensemble) 82.96 / 27.22 / 0.818**. Table 3: single 64³ patch with dilation 82.70.
- Binary label (whole coronary tree, no branch names). ImageCAS-X reports these original labels agree with ImageCAS-X at only DSC 41.8 (see 1a), so ImageCAS-original Dice values are not comparable to ImageCAS-X Dice values.

## 1b. Kim JN et al., J Med Imaging 2025 — NOT a per-vessel result

**Kim JN, Song Y, Wu H, Subramaniam A, Lee J, Makhlouf MHE, et al. "Improving coronary artery segmentation with self-supervised learning and automated pericoronary adipose tissue segmentation: a multi-institutional study on coronary computed tomography angiography images." J Med Imaging 2025;12(1):016002 (pp. 1–14). doi:10.1117/1.JMI.12.1.016002. PMCID PMC11831809.** — metadata verified (Crossref); abstract verified (Europe PMC API, verbatim). Body/tables read via WebFetch of the PMC page (the fetch tool extracts/quotes; PMC raw HTML is behind a captcha for curl and the article is not in the PMC OA XML set) — verified: read in source via WebFetch quotation; recommend the judge-facing claim cite Table 1 only.

- Data: Site I = University Hospitals Cleveland, 188 CCTA → 140 after exclusions (multiple scanners, Supp. Table S1), split 91 train / 23 val / 26 internal test; **Site II = Mackay Memorial Hospital, Taipei, 83 → 73 volumes, external test** (Siemens SOMATOM Definition Flash).
- Targets: "major coronary arteries, specifically the LAD, LCX, and RCA" (aorta excluded from training labels). **The paper does not state a multi-class output, and every Dice table reports one overall coronary Dice — no per-vessel (LAD/LCx/RCA) Dice for the network.** The LAD/LCX/RCA split is done afterwards by a geometric post-processing step ("identifies multi-class LAD, LCX, and RCA segments using the spatial-geometrical information", Fig. 2 caption) for PCAT.
- **Table 1** (overall Dice, internal Site I / external Site II): **nnU-net (patch 112×128×160) 0.794 (0.059) / 0.741 (0.081)**, decrement 0.053; UNETR-pretrained 128³ 0.787 (0.058) / 0.757 (0.059); Unet 128³ 0.754 / 0.696; Attention-Unet 128³ 0.769 / 0.697. → Your remembered 0.794 / 0.741 is correct, **but it is an aggregate major-coronary Dice, not a "3-class LAD/LCx/RCA" per-class result**; do not describe it as per-branch.
- Table 4 (PCAT pipeline, per-vessel but proximal segments only): proximal LAD Dice 0.916 (Site I) / 0.906 (Site II); proximal RCA 0.864 / 0.848.
- Abstract: "achieving Dice scores up to 0.787 after self-supervised pretraining".

## 1c. Centerline/segment-level anatomical LABELLING (learned) — not voxel Dice

**Yang H, Zhen X, Chi Y, Zhang L, Hua X-S. "CPR-GCN: Conditional Partial-Residual Graph Convolutional Network in Automated Anatomical Labeling of Coronary Arteries." CVPR 2020. arXiv:2003.08560.** — verified: read in source (arXiv v4 PDF).
- Data: private, **511 subjects** (Alibaba DAMO / clinic; single source, scanners not stated), two-expert two-phase annotation; centerlines pre-extracted; images resampled to 0.5 mm; **5-fold CV (no external test)**. 6,760 segments (Table 2).
- Task: classify centerline segments into 11 classes RCA, R-PDA, R-PLB, AM, LM, LAD, LCX, RI, D, OM, S (side branches labelled separately, not merged into territory). Territory mapping is possible (D,S→LAD; OM→LCX; R-PDA/R-PLB/AM→RCA) but RI is its own class and PDA/PLB are always under RCA ("R-PLB, R-PDA, and AM are from RCA").
- **Table 3** (Recall / Precision / F1 per class):
  - CPR-GCN: RCA 0.994/0.987/0.990; LM 0.994/0.984/0.989; LAD 0.990/0.986/0.988; LCX 0.982/0.971/0.976; RI 0.921/0.896/0.909; D 0.936/0.883/0.909; OM 0.896/0.933/0.914; R-PDA 0.930/0.946/0.938; R-PLB 0.944/0.947/0.945; S 0.954/0.974/0.964; mean 0.958/0.954/0.955.
  - TreeLab-Net (re-implemented): RCA F1 0.949; LM 0.983; LAD 0.942; LCX 0.924; mean F1 0.871.
  - Conventional (Cao et al.): RCA 0.922; LM 0.987; LAD 0.920; LCX 0.821; mean F1 0.857.
- Metric is segment classification on given centerlines, **not voxel overlap**; not directly comparable to a voxel Dice.

**Wu D, Wang X, Bai J, Xu X, Ouyang B, Li Y, Zhang H, Song Q, Cao K, Yin Y. "Automated anatomical labeling of coronary arteries via bidirectional tree LSTMs." Int J Comput Assist Radiol Surg 2019;14:271–280. doi:10.1007/s11548-018-1884-6.** (This IS "TreeLab-Net".) — verified: abstract read (Europe PMC); full text not accessed (paywalled).
- 436 CCTA, 10-fold CV. Abstract: "the four main branch classes, LM, LAD, LCX and RCA, have the area under the curve (AUC) higher than 97%. Other major side branch classes, D, OM, and R-PLB, also have AUC higher than 90%." Per-class F1 values in the paper body: could not verify.

**Wang X, Ma J, Li J. "Point Transformer for Coronary Artery Labeling." arXiv:2305.02533 (2023; Raysight, industry).** — verified: read in source (arXiv PDF).
- 373 CCTA (320 train / 53 test), single source; labels LM, LAD, LCX, RCA, D, OM, PLB, PDA; point cloud from the given coronary segmentation → labels mapped back to voxels and centerlines. Voxel classification mean accuracy 93.12% (12,288 points, Table 3). Table 1 (centerline branch-level precision, %): LM 100.0, LAD 99.03, LCX 94.2, RCA 98.2, D 93.4, OM 86.5. Caveat: Table 1 places their numbers next to other papers' numbers obtained on different datasets.

**Hampe N, et al. "Graph attention networks for segment labeling in coronary artery trees." Proc SPIE Medical Imaging 2021: Image Processing, p.50. doi:10.1117/12.2581219.** — existence verified via Crossref only; numbers could not verify.

**Zhang Z, Zhao Z, Wang D, Zhao S, Liu Y, Liu J, Wang L. "Topology-Preserving Automatic Labeling of Coronary Arteries via Anatomy-aware Connection Classifier" (TopoLab). MICCAI 2023. arXiv:2307.11959.** — verified: read in source (arXiv PDF + GitHub README zutsusemi/MICCAI2023-TopoLab-Labels).
- Data: **orCaScore (MICCAI 2014 challenge), 72 CCTA, which the authors re-annotated with "vessel segmentation and anatomical categories"**, 5-fold CV; plus in-house 1,200 CTA (800/200/200 split). 14 segment classes. Metrics: segment-count-weighted mean recall/precision/F1 over centerline segments + topology-violation rates.
- **Table 1 (orCaScore, 5-fold mean)**: TopoLab recall 87.13 / precision 88.31 / F1 87.23; CPR-GCN F1 82.72; TreeLab-Net 83.12; CorLab-Net 82.15; TaG-Net 82.14. **Table 2 (in-house test)**: TopoLab F1 92.19; CPR-GCN 90.84; TreeLab-Net 88.52. Per-class numbers are only in the supplement (not checked).
- Public labels: GitHub README says labels are **centerline point sets + segment class in JSON** (not voxel masks), zip password via a Baidu link; "After 2024-09-30 this repo will NOT be maintained"; images must be obtained from the original orCaScore challenge.
- **Practical relevance**: orCaScore + TopoLab labels are a public, non-ImageCAS CCTA cohort with branch names → a possible external per-territory test (centerline-level: map predicted voxel class onto labelled centerline points, compute per-territory recall/precision/overlap). Image download route for orCaScore not verified by me.

**Zhang S, Gharleghi R, Singh S, Moses D, Adikari D, Sowmya A, Beier S. "LWT-ARTERY-LABEL: A Lightweight Framework for Automated Coronary Artery Identification." arXiv:2508.06874 (9 Aug 2025).** — verified: read in source (arXiv PDF).
- Train: Coronary Atlas 380 cases (Auckland), 5-fold; internal test GeoCAD 70 pts (Sydney); **external test orCaScore 72 cases**. 13 classes. Centerline segment labelling (neural net + rule-based topology constraints).
- **Table 2** (Recall / Precision / F1 %): GeoCAD: LM 95.45/98.44/96.92; LAD 96.97/92.75/94.81; LCx 93.94/89.86/91.85; RCA 96.77/98.36/97.56; avg F1 93.17. orCaScore (external): LM, LAD, LCx, RCA all 100.0/100.0/100.0; RI F1 73.85; OM2 80.65; D3 81.25; avg 93.21/94.00/93.26.
- Table 3 (orCaScore weighted F1): TreeLab-Net 83.12, CPR-GCN 82.72, CorLab-Net 82.15, TaG-Net 82.14, TopoLab 87.23, LWT 93.26 (comparators copied from TopoLab Table 1).

**Ren P, He Y, Guo N, Luo N, Li F, Wang Z, Yang Z. "A deep learning-based automated algorithm for labeling coronary arteries in computed tomography angiography images." BMC Med Inform Decis Mak 2023;23:249. doi:10.1186/s12911-023-02332-y. PMC10626726.** — verified: read in source (PMC XML). Caveat: the DL part is a 3D U-Net for myocardium; labelling itself is rule/distance-transform based (not a learned per-branch classifier).
- 157 patients, single centre (Beijing Friendship Hospital), 16 SCCT segments on centerlines; expert review. Overall segment-presence accuracy 96.2%; average overlap 94.0%; "labels for three main arteries, namely, RCA, LAD, and LM, consistently achieved a 100.0% accuracy rate"; pCx 99.4%, LCx 96.2%; R-PLB 79.0%, D2 88.5%, RI 84.7% (Table 2 / text). Inter-expert disagreement highest for OM1 20.6%, R-PLB 19.1%, OM2 15.9%.

## 1d. Voxel-level per-branch (LM/LAD/LCx/RCA) Dice by a learned model on CCTA

**Summerfield N, He Q, Kuo A, Ghanem AI, Zhu S, Ruff C, Pan J, Kumar A, Nagpal P, Zhao J, Dong M, Glide-Hurst CK. "Modality-AGnostic Image Cascade (MAGIC) for Multi-Modality Cardiac Substructure Segmentation." arXiv:2506.10797 (2025).** — verified: read in source (arXiv PDF incl. appendix tables).
- nnU-Net-backbone multi-decoder model; 20 cardiac substructures incl. **RCA, LMCA, LADA, LCx as separate voxel classes** (radiotherapy contouring guidelines). CCTA: n=65, **single institution**, GE scanner (SnapShot Freeze 2), 0.49×0.49×0.63 mm; per modality split train 25 / val 5 / **test 10** (internal only).
- **Table B4 (CCTA, test, DSC MAGIC / unimodal nnU-Net)**: Coronary arteries 0.77 ± 0.12 / 0.77 ± 0.13; **LMCA 0.73 ± 0.07 / 0.72 ± 0.10; LADA 0.80 ± 0.06 / 0.80 ± 0.06; RCA 0.86 ± 0.04 / 0.87 ± 0.03; LCx 0.67 ± 0.16 / 0.67 ± 0.16**; NSD(3 mm) LMCA 0.95, LADA 0.96, RCA 0.96, LCx 0.90.
- Sim-CT (non-contrast) coronary DSC 0.60; MR-Linac 0.50. TotalSegmentator coronary task on Sim-CT: "failed to produce anything useable for the coronary arteries (DSC of 0.01)" (non-contrast planning CT; older TS version).
- Caveat: radiotherapy-style vessel contours (likely main trunks only; side-branch convention not stated in what I read), tiny test set (n=10). Still the only voxel-level 4-vessel (LM/LAD/LCx/RCA) CCTA Dice I could find and verify. Ordering RCA > LAD > LM > LCx matches the ImageCAS-X inter-observer ordering (RCA 95.3 > LAD 92.3 > LM 91.9 > LCx 84.8).

**Non-CCTA but relevant per-branch voxel result (planning CT, radiotherapy): Guthier CV, Kehayias CE, et al. "Clinical Validation and Prospective Deployment of an Automated Deep Learning-Based Coronary Segmentation and Cardiac Toxicity Risk Prediction System." arXiv:2511.14971.** — verified: read in source (arXiv PDF main text; per-structure table is in supplement, not read).
- 3D U-Net (ResNet encoders) segmenting heart, LV, LM, LAD, LCX, right and posterior descending coronary arteries on RT planning CT (non-contrast and contrast); internal n=70, external n=283. Abstract: median Dice 0.95 heart, "0.87 (0.82-0.90)/1.9 mm for the LAD"; text: "worst performance was observed with left main coronary auto-segmentation (Dice 0.40 [IQR=0.29])". Not CCTA; cite only as evidence that LM is the hardest per-vessel class by Dice.

---

## 4a. ASOCA

**Gharleghi R, Adikari D, Ellenberger K, Webster M, Ellis C, Sowmya A, Ooi S, Beier S. "Annotated computed tomography coronary angiogram images and associated data of normal and diseased arteries." Scientific Data 2023;10:128. doi:10.1038/s41597-023-02016-2. PMC10006074.** — verified: read in source (PMC full-text XML, CC BY).
- **40 labelled cases (20 normal, 20 diseased)** = ASOCA training set; plus 20 test images (10 normal, 10 diseased) released **without** ground truth ("Ground truth annotation ... for these cases is not publicly available"; evaluation via asoca.grand-challenge.org).
- Scanner: GE LightSpeed 64, retrospective ECG gating; in-plane 0.3–0.4 mm, z 0.625 mm. Single source (Coronary Atlas, Auckland).
- **Binary lumen label** ("background voxels assigned a value of 0 and the foreground (vessel lumen) assigned a value of 1"); all vessels > 1 mm; final GT = majority vote of 3 annotators. Centrelines (VTP), meshes (STL), calcium scores also provided. No branch names.
- **Inter-annotator**: "The average Dice Score among the three annotators was 85.6% ± 7.7% ... average HD of 5.92 ± 7.3 mm"; normal vs diseased 87.4% vs 83.9% (p = 0.01). NB: Table 1 compares each annotator **against the final majority-vote ground truth** ("compare variability between annotators compared to the final ground truth"), not pairwise.
- Access/licence: "The dataset is available on the UK Data Service (https://reshare.ukdataservice.ac.uk/855916/)"; "The dataset can be used for research and commercial purposes. Researchers request access on the UK Data Service ... and provide evidence of ethics review and approval, or waiver". Article is CC BY 4.0.
- Also states the Rotterdam (MICCAI 2012) dataset "is also no longer publicly available from the challenge website (https://coronary.bigr.nl/)".

**Gharleghi R, Adikari D, Ellenberger K, Ooi S-Y, Ellis C, Chen C-M, ... Sowmya A, Beier S. "Automated segmentation of normal and diseased coronary arteries – The ASOCA challenge." Comput Med Imaging Graph 2022;97:102049. doi:10.1016/j.compmedimag.2022.102049. PMID 35334316 (CC BY 4.0).** — verified: read in source (publisher PDF from UNSWorks repository, hdl.handle.net/1959.4/unsworks_81255; ScienceDirect itself blocked my fetch).
- 60 patients total; 40 training (20 healthy / 20 diseased) released with labels, "the other 20 cases withheld to test"; 35 participants; ranking = sum of Dice rank and HD95 rank. Training data also listed on Synapse (doi:10.7303/SYN25684144).
- **Table 1 (test set, mean ± SD; Dice / HD95 mm / precision / recall)**: **Submission 1 (top-ranked) 0.87 ± 0.04 / 4.16 ± 7.3 / 0.94 / 0.81**; Submission 2 (lowest HD) 0.84 ± 0.05 / 2.34 ± 2.92; Submission 3 0.86 ± 0.07 / 6.22; Submission 4 0.87 ± 0.05 / 6.57; Submissions 5–8: 0.80, 0.84, 0.78, 0.73. Majority-vote ensembles: Top-3 0.88 ± 0.04 / 1.56 ± 2.55; Top-5 0.88 ± 0.04 / 1.73; Top-7 0.87 ± 0.04 / 1.61.
- Healthy vs diseased: "higher Dice scores (0.851 vs 0.829, p = 0.006) and lower Hausdorff distance (3.02 mm vs 6.97 mm, p = 0.0004)". Precision ≥ ~0.9 but recall "significantly lower" — distal branches missed; "even an ensemble of the top three performing participants is missing large segments of the left circumflex artery". Limitation stated: "all data has been collected from one medical centre".
- Top submissions were U-Net/nnU-Net-based (Table 2 lists nnU-Net (Isensee et al.) for two submissions).
- Secondary (Seg2RefineNet Sci Rep 2025): "Qiu et al. reported a Dice score of 0.8853 and an HD of 1.07 mm. Similarly, Yan et al. achieved a Dice score of 0.837" (ASOCA-trained; secondary citation only).

## 4b. CAT08 (Rotterdam coronary centerline challenge)

**Schaap M, Metz CT, van Walsum T, van der Giessen AG, Weustink AC, Mollet NR, et al. "Standardized evaluation methodology and reference database for evaluating coronary artery centerline extraction algorithms." Med Image Anal 2009;13(5):701–714. doi:10.1016/j.media.2009.06.003.** — metadata verified via Crossref; original full text not accessed. Composition verified via a secondary source that read the original:

**Wolterink JM, van Hamersvelt RW, Viergever MA, Leiner T, Išgum I. "Coronary artery centerline extraction in cardiac CT angiography using a CNN-based orientation classifier." arXiv:1810.03143v2 (Med Image Anal 2019).** — verified: read in source (arXiv PDF, Sec. 2.1):
- "We included all 32 CCTA images from a publicly available evaluation framework ... (Schaap et al., 2009), the MICCAI 2008 Coronary Artery Tracking Challenge (CAT08)"; Siemens Sensation 64 or Somatom Definition (dual source); mean voxel 0.32 × 0.32 × 0.4 mm³.
- "the centerline and radius of four major coronary arteries were manually annotated in a consensus reading by three experts. These arteries were the left anterior descending (LAD), left circumflex (LCX) and right coronary artery (RCA), and a fourth vessel selected as a side-branch of the LAD, LCX or RCA."
- "The training set consists of 8 CCTA images with reference annotations ... and the test set consists of 24 CCTA images for which no reference annotations are provided." → **No LM centerline, no voxel masks; test references withheld.**
- Availability: ImageCAS-X (arXiv:2608.30404) states CAT08 and the 2012 dataset "are no longer publicly available"; the original site http://coronary.bigr.nl/centerlines/ now redirects to a GitLab-Pages login (HTTP 401, checked 2026-10-18); https://cat08.grand-challenge.org/ returns 404; a Zenodo search for "CAT08 coronary" / "coronary artery tracking" returned no mirror. → **Treat CAT08 as not currently obtainable** (could not find any mirror).

---

## 5. Models trained on ImageCAS tested on another CCTA cohort (external)

**Khan & Liatsis. "Seg2RefineNet: a novel DL-based framework for 2D CCTA image-based segmentation and 3D volume-based refinement." Sci Rep 2025;15:41096. doi:10.1038/s41598-025-24953-1. PMC12635082.** — verified: read in source (PMC full-text XML).
- Trained on ImageCAS original labels with the original split "700 volumes for training, 50 for validation, and 250 for testing". ImageCAS test: "mean dice score of 0.8313, and mean HD of 12.95 mm".
- **Table 3 "Cross-Dataset Generalizability Performance" (train ImageCAS → zero-shot test ASOCA 40 cases)**: 3D-UNet DSC 0.651, HD 45.23 mm, gap 0.069/4.27; CFNet 0.704, 38.67 mm, gap 0.126/19.84; **Seg2RefineNet 0.767 ± 0.056, HD 29.19 ± 0.71 mm, gap 0.064/16.24**. Text: "only 6.4% DSC performance drop". (So 83.13 → 76.70 Dice is confirmed.)
- Binary segmentation; original ImageCAS labels (which ImageCAS-X shows agree with expert relabelling at DSC 41.8).

**Zhang S, Gharleghi R, Singh S, Shen C, Adikari D, Zhang M, Moses D, Vickers D, Sowmya A, Beier S. "Optimising Generalisable Deep Learning Models for CT Coronary Segmentation: A Multifactorial Evaluation." J Imaging Inform Med 2025 (online 18 Sep 2025; 39(3):2680–2694). doi:10.1007/s10278-025-01677-2. PMC13230296.** — verified: read in source (PMC XML). **Correction: this is NOT ImageCAS-trained**: trained (5-fold) on **ASOCA (40)**, tested on **GeoCAD (70, Sydney, "more modern scanners")**; ensemble of nnU-Net 3d_fullres default + Swin-UNETR + EfficientNet-LinkNet (majority vote). Binary tree, plus per-segment Dice by post-hoc VMTK splitting.
- Text: ASOCA "around 0.9", GeoCAD "approximately 0.8". **Table 4** (DSC ASOCA hold-out / GeoCAD external by calcification): none 0.90 ± 0.03 / 0.82 ± 0.07; low 0.86 ± 0.03 / 0.79 ± 0.09; moderate 0.87 ± 0.04 / 0.81 ± 0.09; high 0.85 ± 0.10 / 0.82 ± 0.07.
- Per-segment (LM, LAD, LCx, D1, OM1, RCA) Dice shown **only as a bar chart (Fig. 3), no numbers in text**; text: gap "most noticeable in the LM, LAD, LCx ... and D1 segments ... OM1 and RCA segments did not show significant differences". → per-vessel external drop exists but numbers not extractable.

**ImageCAS-X itself has no external test** (all 160 test scans are ImageCAS/Guangdong, one scanner). I found **no published model trained on ImageCAS-X labels and tested on another cohort** (searched arXiv titles/abstracts; the newest related preprint, arXiv:2609.31740 "Beyond Volume Overlap: Surface Matching for Topology-Aware Coronary Artery Segmentation", mentions ImageCAS and ASOCA but I did not verify its protocol/numbers).


---

## Summary: what maps to our 4 territory classes

| Source | Learned? | Level | Classes ↔ our 4 | Test | LM | LAD | LCx | RCA |
|---|---|---|---|---|---|---|---|---|
| ImageCAS-X Table 1 (arXiv:2608.30404) | inter-observer (human) | voxel DSC | LM/LAD/LCx/RCA trunks + side branches separate | 160 internal | 91.9 | 92.3 | 84.8 | 95.3 |
| MAGIC Table B4 (arXiv:2506.10797) | yes (nnU-Net-based) | voxel DSC | LMCA/LADA/LCx/RCA (RT contours) | 10 internal, 1 centre | 0.73 | 0.80 | 0.67 | 0.86 |
| CPR-GCN Table 3 (arXiv:2003.08560) | yes (GCN) | centerline-segment F1 | trunks; side branches separate | 5-fold CV, 511 | 0.989 | 0.988 | 0.976 | 0.990 |
| LWT-ARTERY-LABEL Table 2 (arXiv:2508.06874) | yes | centerline-segment F1 (%) | trunks; side branches separate | GeoCAD 70 / orCaScore 72 external | 96.92 / 100 | 94.81 / 100 | 91.85 / 100 | 97.56 / 100 |
| Kim JN JMI 2025 Table 1 | yes (nnU-Net) | voxel DSC, **aggregate only** | no per-vessel network Dice | internal 26 / external 73 | – | – | – | – (overall 0.794 / 0.741) |

Consistent pattern across sources: LCx is the hardest main vessel (lowest inter-observer DSC 84.8 in ImageCAS-X; lowest per-vessel DSC 0.67 in MAGIC; lowest trunk F1 in CPR-GCN/LWT), RCA the easiest; LM is short so its Dice is noisy (MAGIC 0.73; RT planning-CT model 0.40).

## Could NOT find / could NOT verify (do not cite as fact)

1. **Any published per-territory (LM/LAD/LCx/RCA) voxel Dice from a model trained on ImageCAS-X** — none found; ImageCAS-X reports only binary-lumen model results (Table 2) and per-segment inter-observer agreement (Table 1).
2. **Kim JN et al. JMI 2025 as a "3-class LAD/LCx/RCA" Dice** — the 0.794 / 0.741 numbers exist (Table 1, nnU-net), but they are a single overall Dice; no per-vessel network Dice is reported. Body text read via WebFetch quotation (PMC page captcha-blocked for curl).
3. **TotalSegmentator coronary training data** (ImageCAS or not) — not stated in README/CHANGELOG/config; only "Dataset509_coronary_arteries_cm_nativ_400subj_SKELETON". Contamination on ImageCAS cannot be confirmed or ruled out. No accuracy published by the TotalSegmentator authors for this task that I could find.
4. **Wu D et al. 2019 (TreeLab-Net) per-class F1** — only the abstract (AUC > 97% for LM/LAD/LCX/RCA) verified.
5. **Hampe N et al. SPIE 2021** — existence only (Crossref); no numbers.
6. **CAT08 original paper body** — composition verified via Wolterink et al. arXiv:1810.03143 instead; no current download mirror found (original site behind login, grand-challenge 404, nothing on Zenodo).
7. **TopoLab per-class (LM/LAD/LCx/RCA) numbers** — only in supplement, not read; orCaScore image download route not verified.
8. **Zhang S et al. JIIM 2025 per-segment Dice** — only shown in a figure (Fig. 3), no numbers; and this study is ASOCA→GeoCAD, not ImageCAS.
9. **Skeleton Recall / clDice coronary results** — neither paper evaluates on coronary CCTA; only TopCoW (intracranial) / Vessap / DRIVE vessel results exist. (TotalSegmentator's current coronary_arteries model uses nnUNetTrainerSkeletonRecall, per its config + changelog "slightly increased accuracy", without numbers.)
