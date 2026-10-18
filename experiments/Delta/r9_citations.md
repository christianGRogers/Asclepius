# Citation verification (fetched 2026-10-18)

Legend: **FT** = full text opened; **Abs** = abstract only; **No** = not opened.

---

## 1. Bransby et al., ImageCAS-X — FT (arXiv PDF v1, the only version)
Bransby KM, Øksnebjerg E, Kjær K, Kirkeby J, El Youssef Y, Jiménez A, Pedersson PR, de Knegt MC, Kofoed KF, Paulsen RR. "ImageCAS-X: a dataset and benchmark for coronary artery segmentation and centerline extraction in coronary CT angiography." arXiv:2608.30404v1 [cs.CV], 31 Aug 2026. Dataset: Zenodo doi:10.5281/zenodo.21887809 (the Zenodo API confirms the title "ImageCAS-X", published 2026-08-11, files `ImageCAS-X_dataset.zip` and `pretrained_weights.zip`). Code: github.com/kitbransby/ImageCAS-X.

**(a) Benchmark, Table 2** ("Quantitative comparison of vessel segmentation algorithms (top) and expert analysts (bottom)"). Values are mean ± SD on the 160 test cases.
Columns: lumen DSC % / lumen HD95 mm / β_err | centerline clDice / ASSD mm / HD95 mm.
- TotalSegmentator: 70.5±6.2 / 19.59±6.45 / 4.6±2.9 | 76.0±5.3 / 2.73±0.90 / 23.26±7.17
- 3D-FFR-UNet: 84.9±5.5 / 15.93±20.42 / 4.8±3.5 | 89.8±5.0 / 1.71±1.56 / 17.00±18.23
- ADE-HTL: 87.7±2.8 / 2.97±3.74 / 1.5±1.5 | 93.2±3.2 / 0.74±0.39 / 5.61±4.85
- Swin-UNETR: 87.9±2.7 / 3.18±3.68 / 3.8±2.3 | 92.5±3.0 / 0.78±0.36 / 6.16±5.11
- ImageCAS (method): 87.9±2.9 / 4.45±4.90 / 4.7±3.1 | 91.7±3.5 / 0.90±0.46 / 7.81±6.03
- **nnU-Net: 89.8±3.2 / 7.08±12.65 / 5.6±3.5 | 92.3±3.6 / 1.02±0.75 / 10.41±13.41**
- nnU-Net + clDice: 90.0±3.5 / 9.70±15.36 / 8.0±4.4 | 91.7±3.9 / 1.20±0.99 / 12.95±14.20
- **CAS-Net (best): 91.2±2.8 / 2.99±3.47 / 1.9±1.5 | 93.3±3.2 / 0.73±0.36 / 5.75±4.98**
- Inter-observer: 92.8±3.1 / 2.46±3.62 / 0.4±0.4 | 95.4±3.6 / 0.53±0.33 / 4.58±5.75
- Original ImageCAS labels vs ImageCAS-X: 41.8±6.7 / 16.15±8.25 / 7.0±6.7 | 78.2±6.9 / 2.23±0.94 / 18.89±8.91

**Inconsistency in the paper.** Inter-observer β_err is **0.4±0.4** in Table 2 but **0.2±0.4** in Table 1 ("All segments") and in the text ("β err was 0.2"). Cite the table you use.

Definition of β_err (Statistical Measures section): "Betti number error (β err) computed volumetrically … the first counts the number of connected components and the second counts the number of loops."

Quotes useful for the "Dice is the wrong deciding metric" argument:
- Section "Comparison between automated methods and human analysts", Fig. 6: "topological errors such as vessel breaks are present in all model predictions despite high DSC and clDice."
- Same section: "automated methods do not yet match human-level agreement on this dataset." CAS-Net is significantly worse than inter-observer on every metric (p<0.001 to 0.04).
- Same section: "the DSC inter-observer variability should be considered the upper-bound of agreement" (both annotators edited the same automatic centerlines and U-Net initialisation).
- Note: nnU-Net has the second-highest DSC (89.8) but one of the worst β_err (5.6) and HD95 (7.08 mm). nnU-Net+clDice raises DSC to 90.0 while β_err worsens to 8.0. Both are Table 2 numbers directly; this is a ready-made Dice-versus-topology dissociation.

**(b) Per-segment inter-observer agreement, Table 1** ("Inter-observer segmentation agreement per coronary segment"). Columns: n, Agreement %, DSC, HD95, β_err, clDice, ASSD, HD95(centerline).
- LM: n=155, 96.9%, DSC 91.9±13.7, HD95 1.41±5.58, β 0.00, clDice 95.6±17.6, ASSD 0.40, cl-HD95 1.45
- LAD: n=160, 100.0%, DSC 92.3±6.7, HD95 3.39±9.07, β 0.10±0.36, clDice 96.4±7.9, ASSD 0.48, cl-HD95 3.90
- LCx: n=159, 99.4%, DSC 84.8±19.8, HD95 8.59±15.30, β 0.08±0.29, clDice 87.3±23.0, ASSD 1.85, cl-HD95 9.02
- RCA: n=160, 100.0%, DSC 95.3±5.0, HD95 2.18±6.81, β 0.08±0.33, clDice 98.2±6.0, ASSD 0.32, cl-HD95 2.37
- Side branches: D1 79.9, D2 82.9, OM1 74.1, OM2 77.7, IM 80.6, R-PDA 82.6, R-PLA 83.6, L-PDA 75.1, L-PLA 70.9, Other 81.3 (DSC). All segments: DSC 92.8±3.1, agreement 95.3%.
- Caption: "Agreement is the percentage of scans in which both analysts either annotate that segment or both omit it. Remaining metrics were computed over the n scans in which both analysts annotated the segment."
- Text: "the main branches (LM, LAD, LCx and RCA) were the best segmented (DSC 84.8–95.3), while the side branches were consistently worse (70.9–83.6)."
- **The LCx is the hardest main branch: inter-observer DSC 84.8 and clDice 87.3.** Supplementary Fig. 8 is a dedicated LCx labelling guide.

**(c) Split, section "Data Subsets":** "800 annotated cases were randomly split into training (70%, 560 cases), validation (10%, 80 cases), and test (20%, 160 cases)." Each test case was re-annotated blind by a second analyst. 200 of the 1,000 ImageCAS scans were excluded for image quality.

**(d) Centerlines and start point.**
- Released. "Data Records": "centerlines and mesh surfaces as VTK files … Each centerline carries binary feature attributes that assign start, bifurcation, and end points to every vertex, and a categorical attribute that assigns a coronary segment to each vertex."
- Start point / ostium, section "Postprocessing": centerlines were regenerated from the corrected masks by skeletonisation (Lee et al. 1994) with Gaussian smoothing (σ=0.5 mm). Then "The aorta was segmented using TotalSegmentator's high resolution heart chambers model [29], and start points were assigned to centerline vertices with a degree of 1 lying within 5 mm of the aorta. End points were assigned to all remaining vertices of degree 1, and bifurcation points to vertices with a degree of 3 or more."
- Voxel segment labels come from nearest-centerline-point assignment.
- Segment model: modified 18-segment SCCT model. LAD, LCx and RCA are each a single segment (no proximal/mid/distal). There are 14 classes (Supplementary Table 4): LM=1, LAD=2, LCx=3, D1=4, D2=5, OM1=6, OM2=7, IM=8, RCA=9, R-PDA=10, R-PLA=11, L-PDA=12, L-PLA=13, Other=14. Table 1's caption points to "Supplementary Table 1" for the names, but the mapping is actually printed as Table 4. This is a minor typo in the paper.

**Is any learned model benchmarked on per-segment (multi-class) labels? No, not in this paper.**
- All benchmarked methods are evaluated as lumen (binary) segmentation. Supplement E.3: checkpoint selection uses "the mean lumen Dice". E.4: post-processing is "threshold at 0.5, followed by removal of connected components smaller than 100 voxels".
- Per-segment numbers (Table 1) exist only for inter-observer agreement.
- "Binary" is my reading of those sentences; the paper never says "binary" explicitly.
- Other relevant details: nnU-Net in the benchmark is the default nnU-Net (Table 3: 153.9M params summed over 5 models, 2.5 GB peak inference memory). It was trained with SGD at lr 0.01 on an RTX 5090 (32 GB), 0.5 mm isotropic resampling, 1,000 epochs. **ResEnc was not benchmarked.** The paper does not say which TotalSegmentator task was used for the zero-shot baseline.

---

## 7. Schaap et al. 2009 (CAT08) — FT (PMC author manuscript PMC3843509 / NIHMS478778, fetched via NCBI efetch)
Schaap M, Metz CT, van Walsum T, van der Giessen AG, Weustink AC, Mollet NR, et al. "Standardized evaluation methodology and reference database for evaluating coronary artery centerline extraction algorithms." *Medical Image Analysis* 13(5):701–714, 2009. doi:10.1016/j.media.2009.06.003 (confirmed via Crossref).

- **Section 4.4.1, definition of TP/FN (radius-based tolerance):** "A point of the reference standard is marked as true positive TPR_ov if the distance to at least one of the connected points on the evaluated centerline is less than the annotated radius and false negative FN_ov otherwise. A point on the centerline to be evaluated is marked as true positive TPM_ov if there is at least one connected point on the reference standard at a distance less than the radius defined at that reference point, and it is marked as false positive FP_ov otherwise." Correspondence between points uses Dijkstra-based minimal-length matching (Section 4.3).
- **Section 4.4.2, Overlap measures:**
  - **OV** "represents the ability to track the complete vessel … similar to the well-known Dice coefficient": OV = (‖TPM‖+‖TPR‖)/(‖TPM‖+‖TPR‖+‖FN‖+‖FP‖).
  - **OF**, "Overlap until first error (OF) determines how much of a coronary artery has been extracted before making an error … defined as the ratio of the number of true positive points on the reference before the first error (TPR_of) and the total number of reference points": OF = ‖TPR_of‖/(‖TPR_of‖+‖FN_of‖). "The first error is defined as the first FN_ov point when traversing from the start of the reference standard to its end while ignoring false negative points in the first 5 mm of the reference standard. Errors in the first 5 mm are not taken into account because of the strictness of this measure and the fact that the beginning of a coronary artery centerline is sometimes difficult to define …"
  - **OT** covers the "clinically relevant" part: segments with diameter ≥1.5 mm, i.e. reference truncated at the last point with radius ≥0.75 mm.
- **Scope:** 32 CTA datasets, 4 vessels each (RCA, LAD, LCX plus one large side branch), 128 reference centerlines. 13 algorithms were compared (Tables 5–7). The measures are per vessel, not per tree.
- **Relation to our tree-F1.** OF is the closest published analogue to "everything past a break is missed". Differences: OF's tolerance is the local annotated lumen radius, whereas ours is a fixed 1.5 mm. OF ignores the first 5 mm. OF is a recall-type measure only, with no precision side.

---

## 2. Shit et al., clDice — FT (arXiv:2003.07311)
Shit S, Paetzold JC, Sekuboyina A, Ezhov I, Unger A, Zhylka A, Pluim JPW, Bauer U, Menze BH. "clDice – a Novel Topology-Preserving Loss Function for Tubular Structure Segmentation." CVPR 2021, pp. 16560–16569. arXiv:2003.07311. The CVPR page range is as cited in ImageCAS-X ref [16]; I did not check it on the CVF site.

- **Definition (Section 2, "Let's Emphasize Connectivity", Eqs. 1–2):** Tprec(S_P,V_L) = |S_P ∩ V_L| / |S_P|. Tsens(S_L,V_P) = |S_L ∩ V_P| / |S_L|. "we define clDice to be the harmonic mean (also known as F1 or Dice) of both the measures: clDice(V_P,V_L) = 2 × Tprec×Tsens / (Tprec+Tsens)". Here S denotes skeletons and V denotes masks.
- **Dice is insensitive to topology (Section 1, Introduction):** "For evaluating segmentations in such tubular-network structures, traditional volume-based performance indices are sub-optimal. For example, Dice and Jaccard rely on the average voxel-wise hit or miss prediction … it is evident that a single-voxel shift in the prediction can change the topology of the whole network. Further, a globally averaged metric does not equally weight tubular-structures with large, medium, and small radii (cf. Fig 1)."
- **Fig. 1 caption:** "The two segmentation results achieve identical quality in terms of the traditional Dice score … From a topology or network perspective, the red segmentation is evidently preferred."

---

## 3. Metrics Reloaded — FT (PMC11182665 via NCBI efetch)
Maier-Hein L, Reinke A, Godau P, Tizabi MD, Buettner F, Christodoulou E, Glocker B, Isensee F, Kleesiek J, Kozubek M, Reyes M, Riegler MA, Wiesenfarth M, Kavur AE, Sudre CH, Baumgartner M, Eisenmann M, et al. "Metrics reloaded: recommendations for image analysis validation." *Nature Methods* 21:195–212, 2024. doi:10.1038/s41592-023-02151-z.

- **Main text, "Step 2 – Metric Selection", segmentation path ("Select overlap-based metric"):** "Depending on the specific properties of the problems, we recommend the DSC or IoU (default recommendation), the Fβ Score (…) or the centerline Dice Similarity Coefficient (clDice) (for tubular structures). Details can be found in Subprocess S6 for selecting overlap-based metrics (Extended Data Fig. 6)."
- **Table 1** (pitfall → how it is addressed), fingerprint items:
  - FP2.3: "Particular importance of structure center(line); recommendation of the centerline Dice Similarity Coefficient (clDice) as alternative to the common … (DSC) or (IoU) in segmentation problems (Subprocess S6, Extended Data Fig. 6)".
  - FP3.3: "Target structures feature tubular shape; recommendation of the clDice as alternative to the common DSC in segmentation problems (Subprocess S6, Extended Data Fig. 6) …"
- **Same Step 2 text:** "Key weaknesses of overlap-based metrics include shape unawareness and limitations when dealing with small structures or high size variability". The general recommendation is to complement overlap metrics with boundary-based metrics.
- **Caveat:** Metrics Reloaded recommends clDice as an *alternative* overlap metric for tubular structures. I did not find a sentence saying "Dice alone is insufficient for vessels" verbatim. The closest wording is the "shape unawareness" sentence above, plus the recommendation to pair overlap metrics with boundary metrics.
- Also useful: in multi-class problems, "dedicated metric pools for each class may need to be generated as relevant properties may differ from class to class".

---

## 4. TopCoW (Yang, Musio, Ma et al.) — FT (arXiv:2312.17670v5, 14 Jul 2026)
Yang K, Musio F, Ma Y, Juchler N, Paetzold JC, Al-Maskari R, …, Menze B (large consortium). "The TopCoW Challenge — Topology-Aware Circle of Willis Segmentation for CT and MR Angiography." arXiv:2312.17670 (v5). The v5 header says it was accepted in **NEJM AI**, with version of record doi:10.1056/AIdbp2500994. I did not open the NEJM AI page; please verify that DOI before citing.

- **Metrics, main text "Evaluation of Segmentation Algorithms":** "the multiclass CoW segmentation predictions were evaluated using Dice similarity coefficient (Dice score), centerline Dice (clDice), Hausdorff distance at 95th percentile, and connected component error." Beyond segmentation, there are also:
  - "average F1 score for detection of Acom, Pcoms, and 3rd-A2" (positive detection = IoU ≥25%)
  - variant balanced accuracy (VarBalAcc)
- **Supplement S10:** the 2023 edition used Dice, clDice and β0 error. 2024 added "HD95, average F1 score for detection …, VarBalAcc …, and balanced CoW topology match rate (TMR) … a custom composite metric combining detection, connectivity, and graph classification metrics: … the predicted segmentation needs to satisfy correct detection, correct neighborhood connectivity (connected to valid vessel classes), no 0-th Betti number errors, and not left-right flipped".
- **Ranking, S11:** "their rank positions for each metric were averaged to reach a ranking".
- **Was topology scored per class?** Partly.
  - β0 error is class-average. Table S6 caption: "class-average Dice …, centerline Dice (clDice) on merged binary mask, class-average 0-th Betti number (β0) error, class-average HD95 …".
  - **clDice was computed on the merged binary mask, not per class.** Table S15: "The clDice scores were computed on the merged binary class, the Dice scores and β0 errors were computed for each class separately".
  - TMR is a per-class/per-variant topology check.
- **Inter-rater, Supplement S7 / Table S2 (n=5):** Dice "around 90% or above" for most of the 13 classes, but "R-Pcom, L-Pcom, Acom, and 3rd-A2 had slightly lower Dice at 76-89%". Class-average Dice is about 90% and binary Dice about 95%.

---

## 5. ASOCA challenge — FT (UNSWorks repository PDF of the CC-BY published version)
Gharleghi R, Adikari D, Ellenberger K, Ooi SY, Ellis C, Chen CM, Gao R, He Y, Hussain R, Lee CY, Li J, Ma J, Nie Z, Oliveira B, Qi Y, Skandarani Y, Vilaça JL, Wang X, Yang S, Sowmya A, Beier S. "Automated segmentation of normal and diseased coronary arteries – The ASOCA challenge." *Computerized Medical Imaging and Graphics* 97:102049, 2022. doi:10.1016/j.compmedimag.2022.102049 (DOI confirmed; PMID 35334316).

- **Cases (Section 2.3):** 60 patients. "First we provided 40 cases, 20 normal and 20 diseased … with the other 20 cases withheld to test". 3 annotators, majority vote. MICCAI 2020; 8 final participants presented.
- **Binary only.** One vessel mask for the whole coronary tree; "only two distinct components for the left and right coronary trees". There are no per-branch labels.
- **Ranking:** separate ranks for Dice and 95th-percentile HD, summed.
- **Table 1** (test set, mean ± SD):
  - Submission 1 (top rank, nnU-Net based): Dice 0.87±0.04, HD 4.16±7.3, precision 0.94, recall 0.81
  - Submission 2 (lowest HD): Dice 0.84±0.05, HD 2.34±2.92
  - Top-3 ensemble: Dice 0.88±0.04, HD 1.56±2.55
  - The text says HD95 is used and the table header says "HD"; units are presumably mm, though the table does not state them.
- **Also reported:** a skeleton HD95 ("Topological Skeleton", e.g. Sub 1: 11.38±8.67). The text says recall is notably lower than precision, and "missing distal segments tend to reduce the recall".
- Fig. 4 text: even the top-3 ensemble "is missing large segments of the left circumflex artery" in a diseased case.
- **Note:** ImageCAS-X cites a different ASOCA paper as [19]: Gharleghi et al., *Scientific Data* 10:128 (2023), the dataset descriptor. I did not open that one.

---

## 6. ImageCAS (Zeng et al.) — FT of arXiv:2211.01607v2; published CMIG version not opened (paywalled)
Zeng A, Wu C, Lin G, Xie W, Hong J, Huang M, et al. "ImageCAS: A large-scale dataset and benchmark for coronary artery segmentation based on computed tomography angiography images." *Computerized Medical Imaging and Graphics* 109:102287, 2023. doi:10.1016/j.compmedimag.2023.102287 (confirmed via Crossref; PMID 37634975). Preprint: arXiv:2211.01607.

- 1,000 3D CTA images (Siemens 128-slice dual-source). Evaluation: "4-fold cross-validation approach, with a training set of 750 cases (50 cases are used for validation) and a test set of 250 cases."
- **Baseline:** Table 4 (arXiv v2): the baseline (3D U-Net + U-Net++, coarse + multi-patch ensemble) gets Dice 82.96%, HD 27.2169 mm, AHD 0.8180 mm. Other benchmarked methods: 3D FCN 80.58, patch 3D U-Net 72.01, TreeConvGRU 68.78, GCN 70.61.
- Table 3 holds the ablation (ensemble 82.96).
- Binary (whole-tree) labels.
- **Caveat:** these numbers come from the arXiv preprint. Check the table number and values against the CMIG version if possible. ImageCAS-X reports these original labels at DSC 41.8 against its own (Table 2).

---

## 8. nnU-Net Revisited — FT (arXiv:2404.09556v2)
Isensee F, Wald T, Ulrich C, Baumgartner M, Roy S, Maier-Hein K, Jäger PF. "nnU-Net Revisited: A Call for Rigorous Validation in 3D Medical Image Segmentation." MICCAI 2024 (LNCS). arXiv:2404.09556. I did not look up the LNCS DOI.

- **Main claim (Abstract):** "the recipe for state-of-the-art performance is 1) employing CNN-based U-Net models, including ResNet and ConvNeXt variants, 2) using the nnU-Net framework, and 3) scaling models to modern hardware resources."
- **Presets (Section 3.1):** "we introduce new nnU-Net ResEnc presets, which use nnU-Net's existing automatic adaptation of batch and patch sizes to target varying VRAM budgets ("M", "L", "XL")".
- **Measured VRAM (Table 1, "VRAM [GB]"):** nnU-Net org. 7.70; ResEnc M 9.10; **ResEnc L 22.70; ResEnc XL 36.60**. Training runtime is 9 / 12 / 35 / 66 GPU-h on an A100 40GB.
- **The paper does not literally state "24 GB" or "40 GB" as targets.** Those come from the official nnU-Net docs, `documentation/resenc_presets.md` in MIC-DKFZ/nnUNet (fetched):
  - "nnU-Net ResEnc M: … Best suited for GPUs with 9-11GB VRAM"
  - "nnU-Net ResEnc L: requires a GPU with 24GB VRAM. Training time: ~35h on A100"
  - "nnU-Net ResEnc XL: requires a GPU with 40GB VRAM. Training time: ~66h on A100"
  - Cite the docs for the targets and the paper's Table 1 for the measured values.

---

## 9. TotalSegmentator — FT (arXiv:2208.05868) + GitHub README
Wasserthal J, Breit HC, Meyer MT, Pradella M, Hinck D, Sauter AW, et al. "TotalSegmentator: Robust Segmentation of 104 Anatomic Structures in CT Images." *Radiology: Artificial Intelligence* 5(5):e230024, 2023. doi:10.1148/ryai.230024 (confirmed; PMC10546353).

- **Aorta:** yes, "aorta" is one of the 104 classes. Overall test Dice 0.943 (1.5 mm model; Abstract/Results).
- **Coronary arteries:** not in the paper. The README (master) lists a licensed task "**coronary_arteries**: coronary_arteries (also works on non-contrast images)". There is also "coronary_arteries_LEGACY … used until v2.12.0". It is a single binary class.
- **No peer-reviewed Dice for the coronary task found.** It is citable only as software (README / version).
- Also from the README: "heartchambers_highres: myocardium, atrium_left, ventricle_left, atrium_right, ventricle_right, aorta, pulmonary_artery". `resources/heartchambers_highres_details.md`: "Dice across all classes on the validation set: 0.950" (1,559 training images). ImageCAS-X used this model to find the aorta for centerline start points.
- **Citable coronary number for TotalSegmentator:** ImageCAS-X Table 2, zero-shot, DSC 70.5±6.2, clDice 76.0, β_err 4.6. ImageCAS-X does not name the task.

---

## 10. Per-branch coronary labelling with learned models

**(a) CPR-GCN — FT (arXiv:2003.08560v4).** Yang H, Zhen X, Chi Y, Zhang L, Hua X-S. "CPR-GCN: Conditional Partial-Residual Graph Convolutional Network in Automated Anatomical Labeling of Coronary Arteries." CVPR 2020.
- Private set of 511 CCTA, 5-fold CV.
- **Task:** classify *given centerline branch segments* (segment-level, not voxels) into 11 classes. The metric is per-class segment recall, precision and F1.
- The printed formulas in Section 4.1 appear to swap recall and precision ("Recall = tp/(tp+fp)"); this is likely a typo.
- **Table 3, CPR-GCN recall / precision / F1:** RCA 0.994/0.987/0.990; LM 0.994/0.984/0.989; LAD 0.990/0.986/0.988; LCX 0.982/0.971/0.976. Mean over classes 0.958 / 0.954 / 0.955.
- Table 3 also has baselines: TreeLab-Net LCX F1 0.924, conventional method LCX F1 0.821.

**(b) TreeLab-Net — Abstract only (paywalled; OpenAlex says closed).** Wu D, Wang X, Bai J, Xu X, Ouyang B, Li Y, Zhang H, Song Q, Cao K, Yin Y. "Automated anatomical labeling of coronary arteries via bidirectional tree LSTMs." *IJCARS* 14:271–280, 2019 (online Nov 2018). doi:10.1007/s11548-018-1884-6.
- Abstract: 436 CCTA, 10-fold CV. "the four main branch classes, LM, LAD, LCX and RCA, have the area under the curve (AUC) higher than 97%" (precision–recall curve).
- Segment-level labelling on centerlines. I could not see per-branch F1.

**(c) TopoLab — FT (arXiv:2307.11959).** Zhang Z, Zhao Z, Wang D, Zhao S, Liu Y, Liu J, Wang L. "Topology-Preserving Automatic Labeling of Coronary Arteries via Anatomy-aware Connection Classifier." MICCAI 2023.
- 14 segment classes.
- **Datasets:** orCaScore (72 CTA; the authors added vessel and label annotations, released at github.com/zutsusemi/MICCAI2023-TopoLab-Labels) and an in-house set of 1,200 scans.
- **Metrics:** segment-level recall, precision and F1, weighted average over classes. Two new topology metrics: viola (share of connections that violate topology) and violac (share of cases with any violation).
- **Table 1, orCaScore:** TopoLab R/P/F1 87.13 / 88.31 / 87.23; viola 1.52; violac 22.29%. CPR-GCN re-implemented: F1 82.72, violac 53.91%.
- Per-branch numbers are only in the supplement, which I did not open.

**(d) LWT-ARTERY-LABEL — FT (arXiv:2508.06874, Aug 2025).** Zhang S, Gharleghi R, Singh S, Moses D, Adikari D, Sowmya A, Beier S. "LWT-ARTERY-LABEL: A Lightweight Framework for Automated Coronary Artery Identification." Venue not checked.
- Centreline (VMTK) segment labelling; per-artery recall, precision and F1.
- **Table 2, GeoCAD (internal) R/P/F1:** LM 95.45/98.44/96.92; LAD 96.97/92.75/94.81; LCx 93.94/89.86/91.85; RCA 96.77/98.36/97.56.
- **Table 2, orCaScore:** LM, LAD, LCx and RCA are all 100.0.

**(e) Point Transformer for Coronary Artery Labeling — FT (arXiv:2305.02533).** Wang X, Ma J, Li J. Venue not checked (formatted like ISBI).
- 53 CCTA. Point-cloud voxel labelling, mapped to centerline branches by highest overlap.
- **Table 1** reports branch-level centerline labelling *precision*. Text: "precision of the main 4 segments (LM, LAD, LCX and RCA) were all >94%". Per-branch values are in that table.

**Summary for item 10.**
- All labelling works I found score **segment-level classification of centerline segments** with recall, precision and F1. Usually the centerlines are given or pre-extracted. None of them score voxel segmentation, and none count "everything past a break" as missed.
- **I found no 2023–2026 paper reporting learned multi-class (LM/LAD/LCx/RCA) *voxel segmentation* accuracy on a public CCTA set** in the time available.
- ImageCAS-X provides per-segment labels but benchmarks only binary lumen models.
- This is a gap the plan can claim, but phrase it as "we did not find" rather than "none exists".

---

## Not done / caveats
- ImageCAS: CMIG version not opened; numbers are from arXiv v2.
- TreeLab-Net: abstract only.
- Schaap: read from the PMC author manuscript; the publisher PDF was not opened, so section numbers are from the manuscript.
- TopCoW: NEJM AI DOI taken from the arXiv header, not checked.
- ImageCAS-X: inter-observer β_err is 0.2 vs 0.4 between Table 1 and Table 2.
