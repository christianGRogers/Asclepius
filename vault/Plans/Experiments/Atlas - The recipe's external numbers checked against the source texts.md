---
tags: [plans/experiment, citations, verification]
author: Atlas
round: 2
updated: 2026-10-04
---

# The recipe's external numbers, checked against the source texts

## Question

The Round 1 ruling (§2, Atlas (b) iii) noted that the master plan cites the ResEnc gains, the TopCoW mirroring rule
and the Gottlich plateau with identifiers, but no vault note verified them. Are they what the sources say?

## Method

Full text fetched on 2026-10-04 from arxiv.org/html (HTML render of the paper, read as text) for arXiv:2404.09556,
2312.17670 and 2404.03010. The abstract of doi:10.1007/s10278-023-00804-1 was read via the Europe PMC REST API
(PMC10406754). Each claim was grep'd verbatim; quotes below are copied, not paraphrased.

## Result

| Plan claim | Source | Verbatim / table row | Verdict |
|---|---|---|---|
| ResEnc L/XL over the original nnU-Net: KiTS +2.1/+2.6, AMOS +0.8/+1.0; 9 / 35 / 66 A100-h | Isensee et al., *nnU-Net Revisited*, MICCAI 2024, arXiv:2404.09556, Table 1 (main results). Columns BTCV, ACDC, LiTS, BraTS, KiTS, AMOS, VRAM [GB], RT [h] | "nnU-Net (org.) 83.08 91.54 80.09 91.24 86.04 88.64 7.70 9 · ResEnc M … 86.79 88.77 9.10 12 · ResEnc L … 88.17 89.41 22.70 35 · ResEnc XL … 88.67 89.68 36.60 66". RT: "Runtime measured in GPU hours on A100 40GB PCIe" | **Correct.** (The plan said "Table 2"; it is the main results table. Their Table 2 is a KiTS fold-0 ablation that gives ResEnc L **35.28 GPU-h**, which this note uses as a calibration point.) |
| Mirroring must be off for multiclass vessels | Yang et al., *TopCoW*, arXiv:2312.17670, §5.1 | "However, it is important to turn off the mirror augmentation in nnUnet for multiclass segmentation to avoid left and right labels being wrongly flipped such as in some predictions by team 'sjtu_eiee_2-426lab'" | **Correct**, and stronger than quoted: a winning team's L/R swaps are attributed to mirroring |
| Every winning team used nnU-Net; WilliWillsWissen listed first on both multiclass tracks | same, §4.3 and §5.1 | "The winning teams for the CTA track were 'WilliWillsWissen', 'NexToU', 'organizers', and 'sjtu_eiee_2-426lab'. For the MRA track … 'WilliWillsWissen', 'organizers', 'refrain', and 'NexToU'." "5. All winning teams used nnUNet: … as the basis of the architecture or used it along with other custom architecture setup." WilliWillsWissen (App. A): "patch-based 3D nnUNet … clDice and … SkelRecall … 5-fold cross-validation ensemble" | **Correct.** NexToU was a two-stage design (low-res binary nnU-Net then full-res); the plan states this |
| Skeleton Recall +1.2 Dice on 13-class TopCoW; clDice OOM | Kirchhoff et al., ECCV 2024, arXiv:2404.03010, Table 2 | "TopCoW multi-class Default nnUNet 85.36 93.68 … + clDice Loss – Out Of Memory – + Skeleton Recall Loss (Ours) 86.59 94.35" | **Correct** (+1.23 Dice, +0.67 clDice) |
| Anatomical CT structures plateau at tens of cases | Gottlich et al., J Digit Imaging 2023, doi:10.1007/s10278-023-00804-1 | "For segmenting non-neoplastic kidney regions on CT … number of training-validation images needed to reach the plateaus of 54 … For the KiTS21 dataset … 3D … 440" | **Correct**, single-organ analogue only |

## What it implies

All five external claims in the master plan hold as stated. One table number was mislabelled (Table 2 → Table 1).
The KiTS fold-0 figure (ResEnc L, 35.28 A100-h) gives a calibration for the compute estimate in
[[Atlas - A 256³ training step costs 69 TFLOP, and the CPU loader may set the pace]].

## Limits

HTML renders of arXiv papers can mangle tables. The rows were cross-checked against the surrounding prose: the
nnU-Net Revisited text gives ResEnc M "11h, 9GB; 87.91 %" on KiTS fold 0, consistent with the 12 h / 9.10 GB in
Table 1.
