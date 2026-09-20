---
aliases: [Foundation models, SAM-Med3D, MedSAM, VISTA3D, CT-FM, vesselFM, Pretraining evidence]
tags: [research/architecture, foundation-model, pretraining, sam, coronary, evidence]
status: solid
updated: 2026-09-19
---

# Foundation and promptable models do not yet beat a configured nnU-Net for coronaries

Sub-question: does any promptable or self-supervised foundation model (SAM-Med3D,
MedSAM, VISTA3D, CT-FM, vesselFM) beat, or meaningfully cheapen, a purpose-trained
nnU-Net for per-branch coronary segmentation — either used directly, or as a
pretrained initialisation to fine-tune?

## Promptable segmentation models: a structural mismatch with thin branching anatomy

- **MedSAM** (Ma, He, Li, Han, Wang, Wang. *Segment anything in medical images.*
  Nature Communications 15:654, 2024, DOI
  [10.1038/s41467-024-44824-z](https://doi.org/10.1038/s41467-024-44824-z)). MedSAM
  processes 3D volumes slice-by-slice with bounding-box prompts, not as a true 3D
  model. Independent review of the SAM-for-medical-imaging literature (Zhang, Liu,
  Zhang, et al., *Segment Anything Model for Medical Image Segmentation: Current
  Applications and Future Directions*, read as arXiv:2401.03495v1) documents MedSAM's
  own stated weakness on **"vessel-like branching structures"**, attributed
  specifically to bounding-box prompts being ambiguous for thin, branching anatomy —
  a box drawn around a bifurcating tree necessarily also boxes in the background
  between branches. This is the same structural argument [[Training plan]] §4 makes
  against graph/tree pre-segmentation: a representation built for compact,
  box-shaped objects does not fit a tree.
- **SAM-Med3D** (Wang, Ye, Wang, He, et al. *SAM-Med3D: Towards General-purpose
  Segmentation Models for Volumetric Medical Images*, read as arXiv:2310.15161v3).
  Unlike MedSAM, it is genuinely volumetric (3D image encoder, prompt encoder, mask
  decoder, trained end-to-end rather than adapting a frozen 2D SAM). Evaluated on 16
  datasets, but the published evaluation reports no isolated result for vascular or
  other thin tubular structures — organs, bone, brain and cardiac chambers dominate
  the benchmark. Coronary-specific use exists only as downstream adaptation, not from
  the base model: *Mask SAM 3D for coronary artery and plaque segmentation in CCTA
  images* (Int J CARS, 2026, DOI
  [10.1007/s11548-025-03536-5](https://doi.org/10.1007/s11548-025-03536-5)) fine-tunes
  a SAM-3D-family model with **vesselness-derived bounding-box prompts** specifically
  because raw box prompts do not work on vessels — I could only reach the PubMed
  record (PMID 41145776) this session; the quantitative Dice is **unverified,
  flagged for hand fetch**.
- **VISTA3D** (He, Guo, Yang, et al. *VISTA3D: A Unified Segmentation Foundation
  Model For 3D Medical Imaging*, CVPR 2025, read as arXiv:2406.05285). A SegResNet
  backbone over 128³ sliding windows, 127 supported classes, strong on solid organs.
  No coronary-artery class is reported in the paper's tables (searched; not found),
  and its patch size is an order of magnitude below the ~256³ patch [[Training
  plan]] §2 budgets for exactly the reason argued there: small patches lose distal
  branches.
- **vesselFM** (Wittmann, Glandorf, Paetzold, et al. *vesselFM: A Foundation Model
  for Universal 3D Blood Vessel Segmentation*, read as arXiv:2411.17386, the paper's
  own Table 2). This is the one foundation model actually built for vessels, trained
  on 115k real patches (23 datasets, MRA/CTA/X-ray/µCT/microscopy) plus 500k
  domain-randomised and 10k generative-model patches, MONAI U-Net backbone (31.4M
  params). Its own zero-shot numbers on held-out data: OCTA 46.94 Dice, brain-vessel
  EM 67.49, MRA (SMILE-UHURA) 74.66, and **CT (MSD8, hepatic vessel) 29.69 Dice** —
  the only CT vascular number in the paper, and roughly half what a purpose-trained
  nnU-Net scores on comparable liver-vessel CT tasks. No coronary CTA dataset appears
  among vesselFM's 23 training sources or its evaluation set — coronaries are absent
  from this foundation model entirely, and its one CT vascular result is weak
  zero-shot. The paper compares itself only against other foundation models
  (SAM-Med3D, MedSAM-2, VISTA3D, tUbeNet), never against an nnU-Net trained from
  scratch on the target task, so it makes no claim of beating a purpose-built model.
- **TotalSegmentator's own coronary models are nnU-Net, not a foundation model.**
  Already recorded in [[Mirroring is ruled out for multiclass, and it is a chirality
  problem, not only a left-right one]] and `Handoffs.md`: `coronary_arteries_LEGACY`
  (task 507) and the current task 509
  (`Dataset509_coronary_arteries_cm_nativ_400subj_SKELETON`) are both nnU-Net v2
  trainers (`nnUNetTrainer_DASegOrd0_NoMirroring`, then `nnUNetTrainerSkeletonRecall`)
  with a heart crop and 0.7 mm resampling — TotalSegmentator's "foundation" framing is
  a shared 127-class label taxonomy over many task-specific nnU-Nets, not one prompted
  or pretrained backbone doing coronary work. It is evidence that the leading
  general-CT segmentation product chose nnU-Net for this exact structure, not evidence
  that a foundation model does.

## Does CT self-supervised pretraining help, as an initialisation rather than a prompt model?

Two different questions get conflated in this literature: pretrain-then-fine-tune on
a *large general CT corpus* (CT-FM), versus pretrain-then-fine-tune *within the
target task's own cohort* (SSL on ImageCAS itself). Only the second has been measured
on coronary CTA.

- **CT-FM** (project-lighter/CT-FM, `github.com/project-lighter/CT-FM`; SegResEncoder,
  77M params, SimCLR-style contrastive pretraining on 148,000 CT scans). Its own
  reported segmentation benchmark is whole-body TotalSegmentator-label transfer (mean
  Dice 0.898), where the repository itself states **plain nnU-Net does better** because
  of nnU-Net's ensembling, which CT-FM's fine-tuning pipeline does not use. No
  coronary or vessel-specific number is published for CT-FM. It is evidence that a
  148k-scan contrastive pretraining corpus does not close the gap to nnU-Net even on
  its own reported benchmark, and it has not been tested on the anatomy this project
  cares about.
- **In-cohort SSL pretraining, measured directly on ImageCAS coronaries.** Kim, Song,
  Wu, et al., *Improving coronary artery segmentation with self-supervised learning
  and automated pericoronary adipose tissue segmentation: a multi-institutional study
  on coronary computed tomography angiography images*, J Med Imaging (Bellingham)
  12(1):016002, 2025, DOI
  [10.1117/1.JMI.12.1.016002](https://doi.org/10.1117/1.JMI.12.1.016002). SSL
  pretrained a **UNETR** (not nnU-Net) on up to 800 unlabelled ImageCAS volumes, then
  fine-tuned on a separate two-site labelled cohort (Site I: 91/23/26 train/val/test;
  Site II: 73 external test). Results, Dice, 128³ patch:

  | Config | Site I (internal) | Site II (external) |
  |---|---|---|
  | UNETR, no SSL | 0.739 | 0.716 |
  | UNETR + SSL (800-volume pretrain) | 0.787 | 0.757 |

  +4.8 Dice internal, +4.1 external, both from SSL pretraining alone on the same
  architecture. Gains plateaued past ~600 pretraining volumes. In a low-label regime
  (their extreme test: pretrain on 79 cases, fine-tune on 1) pretrained models scored
  0.56 vs 0.38 for non-pretrained — a much larger relative gain when labels are scarce
  than when they are plentiful. The paper's own comparison notes nnU-Net **scored
  higher than UNETR at Site I** but degraded more from internal to external
  validation, i.e. **nnU-Net was more accurate in-distribution but less robust
  out-of-distribution** than the SSL-pretrained transformer, on this cohort. Neither
  point is a case against nnU-Net for our task — our test distribution is the same
  ImageCAS cohort the binary model trains on — but it is the one place in this
  literature search where an architecture choice traded accuracy for external
  robustness on coronary CTA specifically, worth remembering if the model is ever
  deployed outside ImageCAS. This paper does not test SSL-then-fine-tune with
  nnU-Net as the fine-tuned architecture; that specific combination is **unverified**.

## What this implies for [[Training plan]]

1. **No foundation or promptable model earns a run.** Every one that reports a
   CT/CTA vascular number (vesselFM's MSD8 result) is weak zero-shot; every one
   built for coronaries specifically wraps an nnU-Net anyway (TotalSegmentator); the
   two SAM variants have a documented structural weakness on branching anatomy that
   matches the tree/graph argument [[Training plan]] §4 already makes. This
   corroborates, rather than revises, the existing decision in [[nnU-Net still beats
   transformer and Mamba architectures, and ResEnc is the only upgrade worth paying
   for]].
2. **In-cohort self-supervised pretraining is the one pretraining strategy with a
   direct, positive, coronary-CTA measurement** — but on UNETR, not nnU-Net, and the
   gain (+4–5 Dice) was measured against a non-pretrained UNETR baseline that itself
   trailed nnU-Net at Site I. Whether an nnU-Net-compatible SSL pretraining step
   (e.g. contrastive or reconstruction pretraining of the encoder on unlabelled
   ImageCAS volumes before supervised fine-tuning) would add anything on top of
   nnU-Net's own strong from-scratch performance is an open, cheap-ish experiment,
   not a settled question — see the sibling note on binary-init fine-tuning, which
   is the more directly relevant version of "does pretraining help" for this plan
   (a binary-lumen nnU-Net is itself a form of in-domain pretraining).
3. **CT-FM's own documentation that nnU-Net beats it on nnU-Net's home benchmark**
   (TotalSegmentator labels) is a useful data point to cite if a reviewer asks "why
   not use an off-the-shelf CT foundation model": the foundation model's own authors
   report losing to nnU-Net.
4. **Flag for hand-fetch:** *Mask SAM 3D for coronary artery and plaque segmentation
   in CCTA images* (Int J CARS 2026, DOI 10.1007/s11548-025-03536-5) is the one
   paper found that fine-tunes a SAM-3D variant specifically on coronary CCTA; its
   quantitative comparison against nnU-Net is unverified pending full-text access.

Related: [[nnU-Net still beats transformer and Mamba architectures, and ResEnc is the only upgrade worth paying for]],
[[Binary-init fine-tuning and multi-task auxiliary heads for the multiclass model]].
Collected in [[Proposed changes]].
