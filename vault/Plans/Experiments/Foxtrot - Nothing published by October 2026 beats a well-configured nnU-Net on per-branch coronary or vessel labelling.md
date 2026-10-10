---
tags: [plans, experiment, literature, architecture, foundation-model, nnunet, coronary, vessel, round6]
author: Foxtrot
round: 6
updated: 2026-10-10
---

# Nothing published by October 2026 beats a well-configured nnU-Net on per-branch coronary or vessel labelling

## Question

Round 6, Q5. Has any work published or released in 2024–2026 beaten a well-configured nnU-Net
(ResEnc presets, the "Revisited" protocol) on per-branch or multi-class coronary labelling, or on a
comparable thin-vessel labelling task? Has any of it changed best practice for a part of the master
recipe? The parts are architecture, foundation or promptable models, losses, patch and resolution,
training on several annotators, post-processing, and pretraining.

## Method

I searched the web: arXiv, medRxiv, MICCAI/CVPR proceedings, GitHub, and challenge pages for ImageCAS,
ImageCAS-X, ASOCA, TopCoW and TopBrain. Every paper cited below was downloaded and its text
extracted (`curl` + `pdftotext`, scratch copies in `$SCR/work/Foxtrot/fetch/`). I read every number
quoted here in the source table myself. Code claims were checked in the released repositories:

- `github.com/kitbransby/ImageCAS-X`, cloned read-only into scratch;
- the installed `nnunetv2` 2.8.1.

What the vault already holds was not re-derived. That covers nnU-Net Revisited, SAM-Med3D, VISTA3D,
CT-FM and the ImageCAS-X benchmark table
([[nnU-Net still beats transformer and Mamba architectures, and ResEnc is the only upgrade worth paying for]],
[[Foundation and promptable models do not yet beat a configured nnU-Net for coronaries]],
[[State of the art on ImageCAS]]). Where I add to that material, I say so.

## Result

### 1. Multi-class vessel-labelling challenges: the winners are all nnU-Net

| Source (verified) | Task | What it reports |
|---|---|---|
| Yang, Musio, Ma et al., *The TopCoW Challenge — Topology-Aware Circle of Willis Segmentation for CT and MR Angiography*, arXiv:2312.17670v5 (14 Jul 2026), accepted at NEJM AI (doi 10.1056/AIdbp2500994) | 13-class Circle of Willis labelling, CTA and MRA, 2023 and 2024 editions | "All top teams based their architectures on nnUNet." More than half used two stages, "localization followed by segmentation, which allowed the model to localize segmentation training to a sub-volume, reduce false positives in the background". The two shifts from 2023 to 2024 were mixed-modality training and "topological optimization", mostly Skeleton Recall. Only one 2024 team used extra data. |
| Yang, Shi, Huang et al., *TopBrain Segmentation Challenge for Whole Brain Vessel Anatomy*, medRxiv doi 10.64898/2026.05.28.26354312 (30 May 2026), **preprint** | 40+ vessel classes, CTA and MRA | 11 of 15 teams used nnU-Net, and "all top-3 teams for both modalities used nnUNet". CTA, Table 3: winner UZH Dice 79.1, clDice 83.3, β₀ error 0.77. The team that **fine-tuned the vessel foundation model vesselFM** (UTRad) ranked 9th of 11, with Dice 55.8, clDice 58.9, β₀ error 11.8 and 5714 background-contamination voxels (winner: 540). On MRA, the one team using a ResEnc-L with nnSSL self-supervised pretraining on about 1.7k MRA (CLAIM) came 4th: Dice 77.6 against 82.4 and 81.4 for the top two. |

Comparing the two highest-ranked pretrained entries with the nnU-Net-from-scratch winners, TopBrain gives
no evidence that pretraining or a foundation model beats a well-used nnU-Net on fine-grained vessel
labelling. The one vessel foundation model entered lost by 23 Dice points on CTA. The authors' own
summary: "the choice of framework is far less decisive than how it is used". The top teams' levers
were two-stage pipelines (binary, then multi-class), anatomical sub-grouping, mixed-modality data
and post-processing.

### 2. Coronary papers claiming to beat nnU-Net: none does so against a well-configured one

| Source (verified) | Claim | Why it does not transfer to the master |
|---|---|---|
| Bransby et al., ImageCAS-X, arXiv:2608.30404v1 (preprint), Table 2 | **CAS-Net** (Dong et al., *MedIA* 85:102745, 2023): DSC 91.2, HD95 2.99 mm, β err 1.9. **nnU-Net**: 89.8, 7.08 mm, 5.6 (binary lumen, 160 test cases) | (a) The nnU-Net arm ran through nnU-Net's own planner (`models/nnunet/model.py`: `nnUNetv2_plan_and_preprocess`, default 3d_fullres). Table 3 gives 153.9 M parameters for 5 models, which is the plain ~31 M U-Net. Delta read the released plans as patch 96 × 160 × 160 at native 0.5 × 0.35 × 0.35 mm ([[Delta - A released nnU-Net cuts 3 of 8 test trees that Dice scores at 0.84-0.92]]), a 48 × 56 × 56 mm field. CAS-Net's config (`configs/cas_net.json`) uses 128 × 160 × 160 at 0.5 mm iso, a 64 × 80 × 80 mm field. (b) nnU-Net used its automatic CT window on lumen-only foreground. The master fixes exactly this ([[Atlas - nnU-Net's automatic CT window on lumen labels flattens 38 percent of the heart box]]). (c) The gap is mostly topological (β err 5.6 vs 1.9, HD95 7.1 vs 3.0), not overlap (1.4 DSC). That is the master's open FP problem, not its accuracy. The master's 128 mm patch is already larger than either. **Not a win over a well-configured nnU-Net; a pointer to context and FP behaviour.** |
| Sultan et al., *A Neighborhood Attention Transformer Network for Enhanced 3D Segmentation of the Left Anterior Descending Artery*, arXiv:2608.12274v1 (12 Aug 2026), Tables 1–2 | NA-UNETR beats nnU-Net by +3.1 Dice on 20 in-house LAD scans, and by +1.5 on ImageCAS (79.49 vs 77.98) | Their nnU-Net scores **77.98 on ImageCAS**, below the original 2023 ImageCAS baseline (82.96, [[State of the art on ImageCAS]]), and a weakened baseline fails the Revisited test. The authors report the LAD difference as not significant (p > 0.05, n = 20). Their MedNeXt (77.20) is also below their nnU-Net. |
| Qiu et al., *A topology-preserving three-stage framework for fully-connected coronary artery extraction* (CorSegRec), arXiv:2504.01597v1 | ASOCA Dice 88.53, HD95 1.07 mm, against ADE-HTL 86.08, 5.25 mm | Stage 1 **is** nnU-Net; the rest is post-processing (component filtering by a cascade forest, random-walk reconnection). There is **no nnU-Net-alone row** in Table 1, so the gain over nnU-Net is not reported. ImageCAS-X excluded it as not reproducible from the text. The component filtering would be a deletion filter, which A2/A15 exclude from "raw". |

No paper found reports **per-branch (LM/LAD/LCx/RCA) segmentation by a learned model** on ImageCAS or
ImageCAS-X. ImageCAS-X's 14-segment numbers are inter-observer only, as the vault already records.
The master's round-5 model (tF1 0.846–0.895 bounds, swap rate 0.9 %) has no published comparator.

### 3. Large-scale pretraining and foundation models

Covered in detail in
[[Foxtrot - Large-scale CT pretraining gains about one Dice point on organs, has no vessel evidence, and cannot be loaded into the master's network]].
The summary:

- **MedNeXt-v2** (Roy, Kirchhoff, … Isensee, Maier-Hein, arXiv:2512.17774, Dec 2025, DKFZ) is pretrained
  supervised on 18k CT (CADS subset). Over six datasets it reaches mean DSC 83.70 at a 192³ fine-tune
  patch, against 81.65 for ResEnc-L from scratch. No dataset is vascular.
- **CADS (ResEnc-L, 22k CT)**, fine-tuned: 82.55, i.e. +0.90 over the same architecture from scratch.
- **TotalSegmentator-CT weights**: 81.20 against 80.57 for nnU-Net from scratch.
- **Revisiting MAE pre-training** (Wald et al., CVPR 2025): +2 DSC over the same plans from scratch on brain
  MRI. Its own Table 9 shows the warning case for us. On a **0.5 × 0.43 × 0.43 mm** angiography target (ToF
  aneurysms), every 1 mm-pretrained model lost to dynamic from-scratch nnU-Net: S3D 28.72 against 42.61.
- **vesselFM fine-tuned**: 9th of 11 in TopBrain CTA (above).

### 4. Losses, patch, multi-annotator, post-processing

- **Loss.** TopCoW 2024 and TopBrain top teams add Skeleton Recall or cbDice (Kirchhoff et al., ECCV 2024,
  arXiv:2404.03010, verified to exist). No new evidence on coronaries. ImageCAS-X's nnU-Net + clDice
  worsened β err from 5.6 to 8.0 (vault). The Round 5 deprioritisation of A4 stands.
- **Patch/context.** MedNeXt-v2 reports that scaling the fine-tune patch from 128³ to 192³ (×3.375 volume)
  is its best variant: 83.70 against 82.95. This agrees with the master's 256³ choice. ImageCAS-X's
  CAS-Net-vs-nnU-Net gap goes in the same direction (larger field won).
- **Several annotators.** I found nothing in 2024–2026 that supersedes the vault's fusion note or
  Crucible's GPU result (A11′).
- **Post-processing / FP.** TopCoW states the background-FP purpose of ROI localisation. ADE-HTL, the
  method with the best β err in ImageCAS-X (1.5), uses **TotalSegmentator `heartchambers_highres` masks at
  inference** (ImageCAS-X `README.MD`, method table). TotalSegmentator's own coronary task uses a heart crop
  (vault). Four TopBrain teams used connected-component removal. Under A2/A15 a deletion step is not
  "raw", so this needs the evidence the judge asked for:
  [[Foxtrot - The ImageCAS reference lies wholly within 15 mm of a TotalSegmentator heart-and-aorta ROI]].

## What it implies

1. **No architecture, foundation-model or pretraining result justifies changing the master's model.**
   The two benchmarks with multi-class vessel labels (TopCoW, TopBrain) are won by nnU-Net. The only
   coronary benchmark where nnU-Net lost (ImageCAS-X) used a default-configured nnU-Net: 48–56 mm patch,
   automatic window. On both points the master already departs from that default.
2. **What the literature does point at is the master's open problem, FPs and topology.** The
   CAS-Net/ADE-HTL vs nnU-Net gap is in β err and HD95. The TopCoW/TopBrain levers are ROI localisation,
   binary-then-multiclass stages and component removal. That makes an ROI rule the literature-backed
   candidate for the A15/A16 census branch "far-from-tree FP".
3. **Pretraining stays off the critical path.** See the pretraining note. The expected gain is about one
   Dice point on organs, it is unmeasured on vessels, and it is negative in the one fine-spacing vessel
   case.

## Limits

- Searches are not exhaustive. Grand-challenge leaderboards for ASOCA and TopCoW were not scraped
  table by table; I relied on the organisers' papers.
- TopBrain and ImageCAS-X are preprints. NA-UNETR and CorSegRec are preprints.
- Delta's reading of the released ImageCAS-X nnU-Net plans (PlainConvUNet, 96 × 160 × 160) and the
  repository's docstring (`-pl nnUNetPlannerResEncM`) disagree. The parameter count in ImageCAS-X Table 3
  (153.9 M / 5 = 30.8 M) supports the plain U-Net. Either way it is a default-configured nnU-Net, not the
  master's.
- I cloned the public ImageCAS-X repository read-only into scratch to read its configs. This is the only
  git command I ran, and it was not on the project repository.
