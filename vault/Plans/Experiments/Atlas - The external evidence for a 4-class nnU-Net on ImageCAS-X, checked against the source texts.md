---
aliases: [Atlas R9 literature]
tags: [plans, experiment, literature, round9, fir, nnunet, coronary]
author: Atlas
round: 9
status: done
updated: 2026-10-18
issue: christianGRogers/Asclepius#48
---

# The external evidence for a 4-class nnU-Net on ImageCAS-X, checked against the source texts

**Question (Round 9, #48 item 3).** Which published numbers can a 4-class Fir plan rest on, and how do our own
numbers compare with published per-branch coronary results?

**Method.** Every source below was fetched on 2026-10-18 (arXiv PDFs through `pdftotext`, DOIs through Crossref,
code from the nnU-Net and TotalSegmentator repositories). Each number was found in the extracted text. Atlas
re-checked the two numbers the plan leans on hardest by eye: ImageCAS-X Table 1, and nnFoundation Table F30
(hepatic vessel, nnU-Net, 150 vs 1000 epochs: 0.638 vs 0.669). Rows marked **[WF]** come from PubMed Central pages
that could only be read through a summarising fetch tool. **Do not quote a digit from a [WF] row** until someone
has read the table by eye. Alliance pages were read as raw wikitext (the site blocks plain fetches).

## What it changes (summary; the plan is [[Atlas v11]])

1. **No published model segments LM/LAD/LCx/RCA voxels on ImageCAS or ImageCAS-X.** The searches are listed below.
   So no external number can rank our 4-class model directly. The nearest yardstick is **ImageCAS-X's own
   inter-observer DSC per main segment** (Table 1, same cohort, same lumen):

   | | LM | LAD | LCx | RCA |
   |---|---|---|---|---|
   | inter-observer DSC | 91.9 | 92.3 | 84.8 | 95.3 |
   | icx14 val pseudo-Dice at ~epoch 450 (14-class) | 0.90–0.91 | 0.90–0.91 | 0.83–0.85 | 0.92–0.93 |

   The icx14 numbers come from [[icx14 - job 2 restarted from scratch (resume bug), R-PLA appears at epoch 440]].

   **Comparable in kind:** the same reference cohort and lumen, and main segments without their side branches in
   both rows.

   **Not comparable:**
   - nnU-Net pseudo-Dice is patch-level, on val, with the LR still at 0.006. The inter-observer DSC is per case on
     the test split.
   - Neither row is a 4-class territory Dice. The 4-class Dice includes the side branches, which are harder at
     the tips.

   The model's main segments are already within about 1–2 points of a second analyst, and **LCx is the weakest
   class for humans too** (84.8 ± 19.8). So an LCx deficit is partly label ambiguity, not only a model failure.

2. **The end-to-end per-branch comparator closest to our tF1 is Hampe et al. 2024.** It uses automatic tree
   extraction and naming, with segment-level F1: LM 0.70, LAD 0.86, LCx 0.74, RCA 0.90 **[WF]**, on 25 test cases.
   Centreline labellers given the *reference* tree score 0.92–0.99 (CPR-GCN, Table 3). That is an upper bound on
   naming alone, not comparable to tF1, which also counts detection and connectivity. Our run-1 tF1 (macro 0.896;
   LM 0.966, LAD 0.901, LCx 0.846, RCA 0.883; [[Round 8]]) was on the **thick** ImageCAS mask, so it is not
   comparable to ImageCAS-X numbers either (convention cost 0.19 tF1:
   [[Crucible - A perfect segmentation in the wrong lumen convention loses 0.19 tree-F1]]). The 4-class icx4 model
   must be re-scored on ImageCAS-X before any absolute comparison is made ([[Atlas v11]] §7).
3. **Schedule.** nnU-Net's default is 1000 epochs × 250 minibatches with poly LR (exponent 0.9). The authors say
   shorter training "empirically result[s] in diminished segmentation performance", but give no numbers. The only
   measured from-scratch nnU-Net comparison found is nnFoundation Table F30 (preprint), 150 vs 1000 epochs:
   - **hepatic vessel** 0.638 vs 0.669;
   - **inferior alveolar canal (a thin tube)** 0.560 vs 0.713;
   - heart 0.925 vs 0.927.

   Thin tubular targets lose the most from a short schedule. This is why [[Atlas v11]] keeps 1000 epochs although
   our own pseudo-Dice curves flatten early ([[Atlas - Validation pseudo-Dice of the four main vessels flattens by epoch 100-200, but thin structures need the full schedule]]).
4. **Single fold vs 5-fold.** No vessel evidence was found. On brain tumours with 1351 cases (BraTS-GoAT, preprint),
   fold 0 vs a 5-fold ensemble was 0.8310 vs 0.8315. A 5-fold ensemble is not worth 5× the GPU on present
   evidence. A **second seed** buys A22's σ_seed as well as an ensemble member.
5. **Topology losses.** Skeleton Recall gave +1.2 Dice and +0.7 clDice on 13-class TopCoW (Table 2), with more than
   90 % less overhead than clDice. On our own cohort, clDice made topology worse (ImageCAS-X Table 2: β error 5.6 →
   8.0). Skeleton Recall stays a candidate lever, not part of the first Fir job.
6. **TotalSegmentator `coronary_arteries` is binary** (no per-branch labels) and Apache-2.0. Since 2.13.0 (17 March
   2026) it has been a Skeleton Recall model. Its only published accuracy is ImageCAS-X's zero-shot DSC of 70.5
   (version not stated). It is the seed for the pool (D23), so it can serve only as a **binary** cross-check of the
   4-class model on the pool, not as a reference for names.
7. **Fir** (section B): 4 × H100 SXM5 80 GB per node, 1 × EPYC 9454 (48 cores). The bundle is **12 cores / 288 GB
   per GPU** (use ≤ 280 GB). Half the nodes are MIG, so request a full `h100:1`. Jobs run up to 7 days in nested
   walltime partitions, and the shorter ones get more scheduling opportunities. Jobs inherit the submitting shell's
   environment (so `ICX4_EPOCHS` set at submission reaches the trainer). **A job over the bundle is charged as the
   maximum over GPU, cores and memory**: `h100:1` with 24 cores counts as 2 GPUs for fairshare.

**Vault errors found while spot-checking** (not fixed here: other notes are not Atlas's to edit; reported on #48):
`Research/Architectures and training/Training schedule length and early stopping…` says nnU-Net v2 early-stops
(it does not), gives the poly exponent as 2 (it is 0.9), attributes Revisited to *Nat Methods* 2021, and quotes
0.856 (ASOCA's inter-annotator DSC) as ImageCAS's inter-observer agreement.

## A. Citation table

| # | Short name | Full reference | DOI / arXiv | Numbers we may quote | Where read | Verified how |
|---|---|---|---|---|---|---|
| 1 | nnU-Net | Isensee F, Jaeger PF, Kohl SAA, Petersen J, Maier-Hein KH. nnU-Net: a self-configuring method for deep learning-based biomedical image segmentation. *Nat Methods* 18:203–211 (2021) | 10.1038/s41592-020-01008-z; preprint arXiv:1904.08128v2 | "all networks are trained for 1000 epochs with one epoch being defined as iteration over 250 minibatches"; SGD, Nesterov µ = 0.99, initial LR 0.01; poly LR "(1 − epoch/epoch_max)^0.9"; loss = CE + Dice; "Shorter trainings than this default empirically result in diminished segmentation performance" (no numbers given); each configuration is trained as a 5-fold CV and "The 5 models resulting from training on 5 individual folds are subsequently used as an ensemble for predicting test cases" | arXiv v2: Methods "Training schedule" (p. 16–17) and Suppl. B.1 "Blueprint Parameters" (p. 24) | Nature HTML is paywalled (references only). Preprint PDF fetched and grep'd. Code cross-check: `nnUNetTrainer.py`: `initial_lr=1e-2`, `weight_decay=3e-5`, `num_iterations_per_epoch=250`, `num_val_iterations_per_epoch=50`, `num_epochs=1000`, SGD momentum 0.99 nesterov; `polylr.py` `exponent=0.9`; **no early stopping in v2** (fixed `for epoch in range(current_epoch, num_epochs)`); `save_every=50` epochs |
| 2 | nnU-Net Revisited | Isensee F, Wald T, Ulrich C, Baumgartner M, et al. nnU-Net Revisited: A Call for Rigorous Validation in 3D Medical Image Segmentation. MICCAI 2024, LNCS | 10.1007/978-3-031-72114-4_47; arXiv:2404.09556 | Table 1 (DSC %, VRAM GB, RT = "GPU hours on A100 40GB PCIe"): org. 7.70 GB / 9 h; ResEnc M 9.10 / 12; L 22.70 / 35; XL 36.60 / 66. KiTS: 86.04 / 86.79 / 88.17 / 88.67. AMOS: 88.64 / 88.77 / 89.41 / 89.68. Appendix Table 2 (KiTS fold 0): ResEnc L 35.28 GPU-h, 24223 MB, patch 160×224×192, 88.60. Headline: "CNN-based U-Nets yield best performance"; Transformers "fail to match the performance of CNNs … including … the original nnU-Net"; for U-Mamba, "the mamba layers actually have no effect on performance". All trainings were from scratch on 1× A100 40 GB with 5-fold CV. Presets (repo `documentation/resenc_presets.md`): M "9-11GB VRAM … ~12h on A100", L "24GB VRAM … ~35h", XL "40GB VRAM … ~66h"; the doc shows how to scale the target to 80 GB | Table 1, §4 text, Appendix Table 2; resenc_presets.md lines 50–53 | PDF fetched and grep'd; docs fetched raw. The vault's Atlas check of these numbers is confirmed exactly |
| 3 | ImageCAS | Zeng A, Wu C, Lin G, et al. ImageCAS: A large-scale dataset and benchmark for coronary artery segmentation based on CTA images. *Comput Med Imaging Graph* 109:102287 (2023) | 10.1016/j.compmedimag.2023.102287; arXiv:2211.01607 | 1000 patients, Siemens 128-slice dual-source; "512×512×(206−275) voxels, a planar resolution of 0.29-0.43 mm², and spacing of 0.25-0.45 mm"; 4-fold CV, "training set of 750 cases (50 cases are used for validation) and a test set of 250 cases"; "30 epochs (about 21,000 iterations)", Adam, LR 0.002; Table 4: baseline **82.96 %** Dice, HD 27.2169 mm, AHD 0.8180 mm; direct 3D FCN 80.58 % | §3 "ImageCAS dataset", §4/5 implementation, Table 4 | arXiv v2 PDF grep'd; DOI checked on Crossref (CMIG published version not opened) |
| 4 | ImageCAS-X | Bransby KM, Øksnebjerg E, Kjær K, … Paulsen RR. ImageCAS-X: a dataset and benchmark for coronary artery segmentation and centerline extraction in CCTA. **Preprint**, "under review" | arXiv:2608.30404v1 | 800 retained of 1000 (200 excluded: 114 motion, 76 step artefacts …); "training (70%, 560 cases), validation (10%, 80 cases), and test (20%, 160 cases)"; every test case re-annotated by a second analyst. Table 1 has **14 segment rows** (LM, LAD, LCx, D1, D2, OM1, OM2, IM, RCA, R-PDA, R-PLA, L-PDA, L-PLA, Other); **inter-observer** DSC: LM 91.9±13.7 (n 155), LAD 92.3±6.7, LCx 84.8±19.8, RCA 95.3±5.0, all 92.8±3.1, presence agreement 95.3 %. Table 2 (binary lumen, 160 test): nnU-Net 89.8±3.2 / HD95 7.08 / β err 5.6; nnU-Net+clDice 90.0 / 9.70 / 8.0; CAS-Net 91.2±2.8 / 2.99 / 1.9; TotalSegmentator zero-shot 70.5±6.2; inter-observer 92.8±3.1 / 2.46 / 0.4; original ImageCAS labels 41.8±6.7. Setup: 0.5 mm iso, 1000 epochs × 250 minibatches, nnU-Net with SGD (others Adam), RTX 5090 32 GB. Table 3: nnU-Net 153.9 M params summed over 5 models. **No per-segment model performance**: the benchmark is binary lumen only | §Data Subsets, Tables 1–3, §Quantitative Results | PDF grep'd. Confirms the vault's "State of the art on ImageCAS" tables digit for digit |
| 5 | ASOCA | Gharleghi R, Adikari D, Ellenberger K, et al. Automated segmentation of normal and diseased coronary arteries – The ASOCA challenge. *Comput Med Imaging Graph* 97:102049 (2022); data descriptor Gharleghi et al., *Sci Data* 10:128 (2023) | 10.1016/j.compmedimag.2022.102049; 10.1038/s41597-023-02016-2 | 40 training CCTA (20 normal, 20 diseased) + 20 test (10 + 10); binary lumen. MICCAI ranking page: best Dice **0.867** (R. Gao, final rank 1, HD95 4.165 mm; J. Ma also 0.867, HD95 6.575); 8 teams, Dice 0.725–0.867. Inter-annotator DSC 85.6 ± 7.7 % (Sci Data; vault-verified) | asoca.grand-challenge.org/MICCAI_Ranking/ table; challenge home page | Ranking page fetched (curl). CMIG full text returned 403, so whether the paper's Table matches the live page is **not verified**; the page warns results "will continue to be updated" |
| 6 | CAT08 (Rotterdam) | Schaap M, Metz CT, van Walsum T, et al. Standardized evaluation methodology and reference database for evaluating coronary artery centerline extraction algorithms. *Med Image Anal* 13(5):701–714 (2009) | 10.1016/j.media.2009.06.003; PMC3843509 | 32 CTA datasets (8 training, 24 test), 4 vessels each: **RCA, LAD, LCX + one large side branch** (D1 ×14, D2 ×6, optional diagonal ×6, OM1 ×2, PDA ×2, AM ×2); 96 evaluated centrelines; 13 algorithms. Measures (§4.4): **OV** overlap of the whole vessel; **OF** overlap until first error (errors in the first 5 mm ignored); **OT** overlap of the clinically relevant part (diameter ≥ 1.5 mm, i.e. radius ≥ 0.75 mm); **AI** accuracy inside. A point is a TP if it lies within the annotated radius (no fixed mm tolerance) | §4.1, 4.2, 4.4, 4.5 | Abstract via Europe PMC; body **[WF]** from PMC3843509 |
| 7 | TotalSegmentator | Wasserthal J, Breit H-C, Meyer MT, et al. TotalSegmentator: Robust Segmentation of 104 Anatomic Structures in CT Images. *Radiol Artif Intell* 5(5):e230024 (2023) | 10.1148/ryai.230024; arXiv:2208.05868 | Paper: 1204 CTs, 104 structures, resampled to 1.5 mm; **no coronary class in the paper**. Repo: `coronary_arteries` task added in **release 1.4.0**; training set enlarged in 2.5.0; replaced in **2.13.0 (17 Mar 2026)** by a "new skeleton-recall model with slightly increased accuracy" (old one kept as `coronary_arteries_LEGACY`). It is **binary** (`map_to_binary.py`: `"coronary_arteries": {1: "coronary_arteries"}`), listed under "Openly available for any usage (Apache-2.0 license)", not the licensed tasks. No per-branch labels. Only published accuracy found: ImageCAS-X Table 2 zero-shot DSC **70.5 ± 6.2** (version not stated) | arXiv abstract/§Methods; README lines 59, 107–108; CHANGELOG; map_to_binary.py | Fetched raw; Crossref DOI |
| 8a | CPR-GCN (+ TreeLab-Net, Cao reimplemented) | Yang H, Zhen X, Chi Y, et al. CPR-GCN: Conditional Partial-Residual Graph Convolutional Network in Automated Anatomical Labeling of Coronary Arteries. CVPR 2020 | 10.1109/CVPR42600.2020.00386; arXiv:2003.08560 | 511 private CCTA, two experts plus consensus, **centreline-branch labelling** (centrelines given), 5-fold CV, 0.5 mm. Table 3 F1: **CPR-GCN** RCA 0.990, LM 0.989, LAD 0.988, LCX 0.976, mean 0.955; **TreeLab-Net** (reimpl.) RCA 0.949, LM 0.983, LAD 0.942, LCX 0.924, mean 0.871; **Conventional (Cao 2017)** RCA 0.922, LM 0.987, LAD 0.920, LCX 0.821, mean 0.857 | Table 3, §4.1 | PDF grep'd |
| 8b | TreeLab-Net (original) | Wu D, Wang X, Bai J, et al. Automated anatomical labeling of coronary arteries via bidirectional tree LSTMs. *IJCARS* 14(2):271–280 (2019) | 10.1007/s11548-018-1884-6 | 436 CCTA, 10-fold CV, centreline labelling; abstract: LM, LAD, LCX, RCA "have the area under the [PR] curve (AUC) higher than 97%" | Abstract only | Europe PMC abstract. Full text paywalled; per-branch F1 from the original paper **not verified** (use 8a's reimplementation) |
| 8c | Cao 2017 | Cao Q, Broersen A, de Graaf MA, et al. Automatic identification of coronary tree anatomy in coronary computed tomography angiography. *Int J Cardiovasc Imaging* 33(11):1809–1819 (2017) | 10.1007/s10554-017-1169-0; PMC5677991 | 83 CCTA, 1149 segments, rule/model-based labelling of extracted centrelines; "In all cases, the proximal parts of main branches including LM were labeled correctly"; 89.2 % (right-dominant) / 83.6 % (left-dominant) of segments labelled in agreement, vs expert-expert 97.6 / 87.6 % | Abstract | Europe PMC abstract only |
| 8d | Hampe 2024 | Hampe N, van Velzen SGM, Wolterink JM, et al. Graph neural networks for automatic extraction and labeling of the coronary artery tree in CT angiography. *J Med Imaging* 11(3):034001 (2024) | 10.1117/1.JMI.11.3.034001; PMC11095121 | 104 CCTA (2 centres), 79 train / 25 test, 10 AHA classes, **fully automatic** (tracking + GNN). Tree extraction R/P/F1 0.84/0.87/0.85 (Table 2). Labelling F1 on automatic trees (Table 3): LM 0.70, LAD 0.86, LCX 0.74, RCA 0.90, mean 0.74. On reference trees (Table 8): LM 0.85, LAD 0.95, LCX 0.85, RCA 0.95, mean 0.91; undivided segments only (Tables 8–9): mean 0.95 | Tables 2, 3, 8, 9 | Europe PMC abstract (0.85, 0.74) plus **[WF]** for the tables |
| 8e | Ren 2023 | Ren P, He Y, Guo N, et al. A deep learning-based automated algorithm for labeling coronary arteries in CTA images. *BMC Med Inform Decis Mak* 23:249 (2023) | 10.1186/s12911-023-02332-y; PMC10626726 | 157 CCTA (all right-dominant), U-Net segmentation → skeleton → 16 SCCT segments; reference = expert-corrected algorithm output. Table 2 presence: LM, pLAD, mLAD, pRCA, mRCA 100 %; LCx recall 96.2 %, F1 98.1 %; overall presence accuracy 96.2 %, average overlap 94.0 % | Table 2, abstract | **[WF]** |
| 8f | Kim 2025 (partial) | Kim JN, Song Y, Wu H, et al. Improving coronary artery segmentation with self-supervised learning and automated PCAT segmentation: a multi-institutional study on CCTA. *J Med Imaging* 12(1):016002 (2025) | 10.1117/1.JMI.12.1.016002; PMC11831809 | **Voxel** segmentation, LAD/LCX/RCA labels (no LM class), 140 + 73 external CCTA. Aggregate Dice nnU-Net 0.794 (internal) / 0.741 (external), UNETR-SSL 0.787 / 0.757 (Table 1). Per-vessel only proximal LAD 0.916 / RCA 0.864 (Table 4); **no LCX** | Tables 1, 4 | **[WF]**; it is unclear whether Table 4 scores the model output or the PCAT region, so re-read before quoting |
| 9a | nnFoundation (epoch budget) | Ulrich Harsy C, Wald T, Gotkowski K, Kirchhoff Y, … (DKFZ). nnFoundation: 3D Foundation Models for Radiology. **Preprint** | arXiv:2609.26924v1 | Suppl. Table F30, **nnU-Net from scratch, 150 vs 1000 epochs** (DSC): MSD Hepatic Vessel 0.638 vs 0.669; ToothFairy (inferior alveolar canal, thin tube) **0.560 vs 0.713**; HaNSeg 0.417 vs 0.546; MSD Liver 0.748 vs 0.812; MSD Heart 0.925 vs 0.927; Spleen 0.959 vs 0.967. The pretrained nnFoundationCNN keeps "99.16% of its full-schedule performance" at 150 epochs (Fig. 4c,d) | Table F30 (p. S61 onward), Fig. 4 caption | PDF grep'd; row attribution re-checked by printing the blocks |
| 9b | nnU-Net code variants | MIC-DKFZ/nnUNet `variants/training_length/nnUNetTrainer_Xepochs.py` | github | Ready-made trainers for 1, 2, 5, 10, 20, 50, 100, 250, 500, 750, 2000, 4000 and 8000 epochs (`nnUNetTrainer_250epochs` sets `num_epochs = 250`). No published DKFZ 250-vs-1000 result was found | code | fetched raw |
| 9c | Fold-0 vs 5-fold ensemble | Kirscher T, et al. Assessing nnU-Net Generalization across Brain Tumor Populations in BraTS-GoAT 2026. **Preprint** | arXiv:2609.15524 | 1351 training cases, 1000 epochs/fold. Official validation (450 cases), Table 1 / §3.2: mean DSC 5-fold+TTA **0.8315** vs fold-0+TTA **0.8310**; "Five folds gave no clear paired DSC improvement over fold 0"; with TTA every 5-fold DSC/NSD change "within 0.0008 of zero"; without TTA, ensembling raised NSD by 0.0056–0.0082 | §3.2–3.3, Table 1 | PDF grep'd. Brain tumour, not vessels |
| 9d | 1000 vs 1250 epochs, 5 vs 15 folds | (MRI head-and-neck tumour, nnU-Net v2) | arXiv:2412.06610 | DSC_agg 0.73 (1000 ep) → 0.74 (1250 ep); 5-fold vs 15-fold ensemble "similar validation DSCagg of 0.74" | §Results text | PDF grep'd; small, no significance test |
| 10a | Skeleton Recall | Kirchhoff Y, Rokuss M, Roy S, et al. Skeleton Recall Loss for Connectivity Conserving and Resource Efficient Segmentation of Thin Tubular Structures. ECCV 2024, LNCS | 10.1007/978-3-031-72980-5_13; arXiv:2404.03010 | Table 2 (nnU-Net backbone): TopCoW multi-class (13 classes) Dice 85.36 → **86.59**, clDice 93.68 → 94.35, β0 0.137 → 0.151 (slightly worse), clDice loss "Out Of Memory"; TopCoW binary 93.55 → 93.72; ToothFairy 71.80 → 74.42 (clDice loss 72.36). Abstract: "reducing computational overheads by more than 90%" vs differentiable-skeleton losses; clDice OOM "exceeded the memory capacity of an A100 40GB GPU" on 13 classes (§5.3, Fig. 7) | Table 2, §5.3, Figs 6–7 | PDF grep'd. The per-dataset overhead bars in Fig. 6 do not extract cleanly, so they were not quoted |
| 10b | clDice | Shit S, Paetzold JC, Sekuboyina A, et al. clDice – a Novel Topology-Preserving Loss Function for Tubular Structure Segmentation. CVPR 2021, pp. 16555–16564 | 10.1109/CVPR46437.2021.01629; arXiv:2003.07311 | Table 1 (U-Net, 2D/3D, not CT): Roads Dice 76.23 → 76.66 (α 0.1), clDice 86.83 → 88.17 (α 0.5), β0 0.491 → 0.312–0.375; CREMI clDice 95.86 → 96.21. Gains are a few tenths to ~1.5 points and depend on α. Counter-evidence on our cohort: ImageCAS-X Table 2, nnU-Net+clDice β err 5.6 → 8.0 | Table 1 | PDF grep'd |

### Comparability of the per-branch comparators to our metric (tF1 at 1.5 mm on centrelines from 4-class voxel output)

| Comparator | Input to the labeller | Unit scored | Metric | Comparable to ours? |
|---|---|---|---|---|
| CPR-GCN / TreeLab / Cao (8a–c) | **reference centrelines** | branch segment | per-class P/R/F1 | Upper bound on naming only; no extraction error. Our tF1 includes detection, so it should come out lower. Note: CPR-GCN's printed Recall and Precision formulas appear swapped (Recall = tp/(tp+fp) as printed) |
| Hampe 2024 (8d) | **automatic** tree | segment | F1 | **Closest end-to-end analogue** (detection plus naming), but a different matching rule, AHA 10 classes, n = 25 test |
| Ren 2023 (8e) | automatic (U-Net skeleton) | segment presence / overlap | accuracy, F1 | Weak: the reference is a corrected algorithm output, so it is biased upward |
| Kim 2025 (8f) | voxel model | voxels | Dice | Voxel Dice, 3 classes, no LM, partial per-vessel numbers |
| ImageCAS-X Table 1 (4) | two humans | voxels per segment | DSC | Human ceiling on the **same cohort**; not a model result |

**No published model reports LM/LAD/LCx/RCA voxel segmentation on ImageCAS or ImageCAS-X.** Searches run 2026-10-18: "multi-class coronary artery segmentation CCTA LAD LCX RCA Dice per branch nnU-Net"; "coronary CTA … left main LAD LCx RCA voxel-wise multi-label Dice per vessel"; "automatic coronary artery segment labeling CCTA nnU-Net SCCT segments Dice". Wang 2025 (Med Phys, 10.1002/mp.17642) and Zhang 2025 (J Imaging Inform Med, 10.1007/s10278-025-01677-2) were checked: neither reports per-vessel model Dice in its tables (Zhang plots binary-split segment DSC in Fig. 3 only) **[WF]**.

## B. Fir cluster (docs.alliancecan.ca, read 2026-10-18; revision timestamps in brackets)

| Fact | Value (quoted) | Page |
|---|---|---|
| GPU nodes | "160 · 48 [cores] · 1125G or 1152000M · 1 x AMD EPYC 9454 (Zen 4) @ 2.75 GHz, 256MB cache L3 · 7.84TB NVMe · 4 x NVidia H100 SXM5 (80 GB memory), connected via NVLink" | https://docs.alliancecan.ca/wiki/Fir (Node characteristics) [rev 2026-07-21] |
| GPU-node CPU layout | "1 × AMD EPYC 9454 (Zen 4) @ 2.75 GHz processor with 48 physical cores … NPS=4"; 4 NUMA nodes × 2 CCDs × 6 cores; recommends `--ntasks-per-node=4 --cpus-per-task=12` | Fir |
| Full-GPU request | "'''One H100-80gb''' : `--gpus=h100:1`"; `--gpus-per-node=h100:2/3/4` | Fir (GPU instances) |
| MIG | "Approximately half of the GPU nodes are configured with MIG technology, and only 3 GPU instance sizes": 1g.10gb, 2g.20gb, 3g.40gb (`--gpus=nvidia_h100_80gb_hbm3_3g.40gb:1`) | Fir; https://docs.alliancecan.ca/wiki/Using_GPUs_with_Slurm [rev 2026-03-27] |
| Per-GPU bundle | Fir H100-80gb: RGU per GPU **12.2**; "Bundle per GPU **12 cores, 288 GB**"; "Recommended per GPU **12 cores, 280 GB**"; 3g.40gb: 6 cores, 144 GB (rec. 6 cores, 140 GB). Cluster RGU ratio: 0.98 cores and 23.6 GB per RGU | https://docs.alliancecan.ca/wiki/Allocations_and_compute_scheduling#Ratios_in_bundles [rev 2026-09-25] |
| Charging when a job exceeds the bundle  | "Research groups are charged for the maximum number of RGU-core-memory bundles they use." "Research groups using more cores than RGUs or memory per RGU-core-memory bundle will be charged by core. For example, a researcher requests 1 RGU, 5 cores, and 5 GB of memory. The request is for 1.66 bundles worth of cores … This job request will be counted as 1.66 RGU equivalents". So **h100:1 with `--cpus-per-task=24` on Fir = 24/12 = 2 bundles: charged as 2 GPUs' worth (≈ 24.4 RGU) for fairshare**, the max over GPU, core and memory. The same rule applies to memory above 288 GB | Allocations_and_compute_scheduling (GPU bundle section) |
| Default CPU/memory | GPU jobs: "a number of CPU cores (default is `1`)"; the recommended maximum is the bundle table. Running_jobs: 256 MB per core default (vault-verified) | Using_GPUs_with_Slurm "Requesting CPU cores and system memory" |
| Env export  | "**Jobs inherit environment variables** — By default a job will inherit the environment variables of the shell where the job was submitted … It is best to include the line `module purge` in your job script … If you wish to suppress this inheritance, use the `--export=none` directive". So the default is Slurm `--export=ALL`. The docs say nothing about a site-set `SBATCH_EXPORT=NONE`. Also: `SBATCH_ACCOUNT` set in the environment "takes priority" over `#SBATCH --account` in the script | https://docs.alliancecan.ca/wiki/Running_jobs §"Jobs inherit environment variables" [rev 2026-09-01] |
| Max walltime | "Each job should have a duration of at least one hour (at least five minutes for test jobs) and the maximum job duration is 7 days (168 hours)." | Fir (Site-specific policies) |
| Partitions by walltime | "There are partitions for jobs of 3 hours or less, 12 hours or less, 24 hours (1 day) or less, 72 hours (3 days) or less, 7 days or less"; "longer jobs are restricted to use only a fraction of the cluster"; "A shorter job will have more scheduling opportunities than an otherwise-identical longer job." Partitions nest ("Matryoshka"), and there are by-node and by-core variants | https://docs.alliancecan.ca/wiki/Job_scheduling_policies [rev 2026-04-01] |
| > 24 h jobs | Allowed ("[[Fir]], Narval, Nibi and Rorqual up to 7 days"), but they go into smaller partitions. "Backfilling will primarily benefit jobs with short time limits, e.g. under 3 hours." Priority uses fair tree; "Past usage is discounted with a half-life of one week" | Job_scheduling_policies |
| $SLURM_TMPDIR | "Fir · 7T [space in $SLURM_TMPDIR] · 7.84T [disk]"; space is shared with other jobs on a partial node | https://docs.alliancecan.ca/wiki/Using_node-local_storage [rev 2025-08-29] |
| Other | Compute nodes have full internet access; crontab is not supported; storage is 51 PB DDN Lustre; GPU nodes on InfiniBand NDR at 2:1 blocking | Fir |

**Inconsistencies on the pages:**
- Fir's node table says **4 × H100** per GPU node, but its GPU-node "Layout" says "2 NVidia H100 80GB accelerators", followed by "The 4 node accelerators are interconnected by SXM5". The 4-GPU reading agrees with 48 cores = 4 × 12 and 1152000M = 4 × 288 GB.
- The Fir and MIG pages give 1g.10gb as "1/8th of the computing power", while the Allocations page says "a GPU instance of profile 1g is worth 1/7 of an A100 or H100 GPU".
- The bundle (288 GB) and the "recommended" value (280 GB) differ. Request ≤ 280 GB to stay inside one bundle.

## Caveats / could not verify

1. **Vault errors found while spot-checking** (`Research/Architectures and training/Training schedule length and early stopping…md`):
   - It says nnU-Net uses "early stopping if validation loss does not improve…". **False for v2**: there is no early stopping, and it runs a fixed 1000 epochs.
   - It gives the LR as `0.01×(1−epoch/1000)²`. The **exponent is 0.9**.
   - It says "validation every 50 training iterations". In fact each epoch runs 50 validation minibatches, and a checkpoint is saved every 50 epochs.
   - It attributes the Revisited benchmark to "Nat Methods 2021".
   - It still quotes ~0.856 as the ImageCAS inter-observer agreement.
2. ImageCAS-X's inter-observer β err is **0.2 ± 0.4 in Table 1 (all segments) but 0.4 ± 0.4 in Table 2**. The vault calls this a text-vs-table difference; it is in fact table vs table.
3. Hampe 2024: the vault's "0.95 on reference trees vs 0.74 = 21 points" mixes settings. Like-for-like (ensemble, all segments) is **0.91 vs 0.74**; 0.95 is the undivided-segments subset **[WF]**.
4. **Not verified:**
   - ASOCA CMIG paper tables (403). Only the live MICCAI ranking page was read.
   - TreeLab-Net original per-branch F1 (paywalled).
   - nnU-Net Nature Methods final text (paywalled); the arXiv v2 preprint was used instead.
   - Any published accuracy for TotalSegmentator's `coronary_arteries` other than ImageCAS-X's zero-shot 70.5, whose version is unstated.
5. **No source gives nnU-Net single-fold vs 5-fold ensemble gain on vessels.** The best evidence is brain tumour with 1351 cases (≈ +0.0005 DSC). nnU-Net 2021 only states the 5-fold ensemble as the default, without an ablation number.
6. **No DKFZ-published 250-vs-1000-epoch ablation was found.** The nnFoundation Table F30 150-vs-1000 numbers are the best substitute: a preprint, mixed datasets, no coronary set, but they include hepatic vessels and the thin inferior alveolar canal, both with large losses at 150 epochs.
7. Preprints: ImageCAS-X, nnFoundation, BraTS-GoAT, 2412.06610. Every **[WF]** row should be re-read by eye before a digit is quoted.
