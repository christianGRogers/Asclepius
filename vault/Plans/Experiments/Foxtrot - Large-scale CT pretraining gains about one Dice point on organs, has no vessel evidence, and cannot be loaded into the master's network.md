---
tags: [plans, experiment, literature, pretraining, nnunet, mednext, round6]
author: Foxtrot
round: 6
updated: 2026-10-10
---

# Large-scale CT pretraining gains about one Dice point on organs, has no vessel evidence, and cannot be loaded into the master's network

## Question

The master trains its ResEnc model from random initialisation on the proxy (R1), then fine-tunes per
wave. Two questions follow:

- Would public large-scale CT pretrained weights give a better R1 or final model? Candidates are
  TotalSegmentator, CADS, MedNeXt-v2, STU-Net and vesselFM.
- Can those weights be used with the master's network at all?

## Method

1. Read the result tables of the papers below. Text was extracted from the arXiv PDFs; numbers were
   copied from the tables.
2. Read `nnunetv2/run/load_pretrained_weights.py` in the installed nnU-Net 2.8.1, the version the master
   pins, and nnU-Net's `documentation/pretraining_and_finetuning.md` (master branch, fetched 2026-10-10).

## Result

### Published gains (mean DSC; none of the datasets is a vessel tree unless stated)

**Roy, Kirchhoff, Ulrich, Rokuss, Wald, Isensee, Maier-Hein, *MedNeXt-v2: Scaling 3D ConvNeXts for
Large-Scale Supervised Representation Learning in Medical Image Segmentation*, arXiv:2512.17774v1,
19 Dec 2025, Table 4.** It uses six datasets: pediatric CT organs, knee MR, ToothFairy CBCT, brain
metastases MR, pancreatic tumour MR and CTSpine1k. The cell is DSC/NSD, and the mean is over the six.

| Model | Pretraining | Mean DSC / NSD |
|---|---|---|
| nnU-Net, from scratch | — | 80.57 / 78.49 |
| ResEnc-L, from scratch | — | 81.65 / 79.72 |
| MedNeXt-v2, from scratch | — | 82.31 / 80.34 |
| nnU-Net, TotalSegmentator-CT weights | TotalSeg-CT | 81.20 / 78.86 |
| ResEnc-L, CADS weights | CADS-Organ (22k CT) | 82.55 / 80.31 |
| STU-Net-L | AbdomenAtlas 1.0 | 81.83 / 79.56 |
| MedNeXt-v2 base, 128³ fine-tune | CADS subset, 18k CT | 82.95 / 81.06 |
| MedNeXt-v2, **192³** fine-tune ("Patch × 1.5") | CADS subset | **83.70 / 81.77** |

The authors' own reading:

- Pretraining helps tumours most ("Tumor classes benefit massively"). For organs, "results are more
  mixed with the larger networks showing moderate to no gains".
- "Modality-specific pretraining offers negligible benefit once full finetuning is applied."
- Pretraining ran at a 128³ patch for 1500 epochs on 4 × A100. Fine-tuning used AdamW at peak LR 1e-3 with
  a 50-epoch warm-up, for 300 epochs.

**Ye et al., *SegBook*, arXiv:2411.14525v1 (Nov 2024), Table 4, "Vessel" column.** STU-Net pretrained on
TotalSegmentator labels, against nnU-Net from scratch:

| Model | Vessel DSC |
|---|---|
| nnU-Net (from scratch) | 80.46 |
| STU-Net-base, from scratch | 80.19 |
| STU-Net-base, pretrained | 81.24 |
| STU-Net-large, pretrained | 82.06 |
| STU-Net-huge, pretrained | 82.00 |

Vessel datasets include MSD hepatic vessel, Parse22 (pulmonary artery) and SMILE-UHURA. There is no
coronary set. The baseline is default nnU-Net, not ResEnc at a large patch.

**Wald et al., *Revisiting MAE pre-training for 3D medical image segmentation*, CVPR 2025, arXiv:2410.23132.**

- Table 4: average DSC over 11 brain-MRI tasks is S3D 72.37, from scratch with the same plans 70.40, and
  dynamic nnU-Net 69.40. The authors read this as "+2 DSC points".
- Table 9: on ToF angiography aneurysms (D12, median spacing **0.50 × 0.43 × 0.43 mm**), the dynamic
  from-scratch nnU-Net scores **42.61**, the 1 mm-plans from-scratch model 22.76, and S3D-pretrained
  **28.72**. The paper attributes this to the spacing mismatch with its 1 mm pretraining.

**Vessel foundation model in a benchmark.** In TopBrain 2025 CTA, vesselFM fine-tuned ranked 9th of 11,
with Dice 55.8 against 79.1 for the nnU-Net winner
([[Foxtrot - Nothing published by October 2026 beats a well-configured nnU-Net on per-branch coronary or vessel labelling]]).

### Can the weights be loaded into the master's network?

- `load_pretrained_weights` (nnU-Net 2.8.1) **asserts** that every non-segmentation key of the target
  network exists in the checkpoint with the same shape. Otherwise it fails with "The pretrained weights do
  not seem to be compatible with your network".
- The nnU-Net documentation says the plans must be "aligned between the two tasks". The pretraining run
  must be redone with the fine-tuning dataset's plans (`nnUNetv2_move_plans_between_datasets`).
- The master's network comes from `ResEncUNetPlanner -gpu_memory_target 60` at 0.5 mm with a 256³ patch.
  The real plans file (`trillium-results/round5/atlas/results/nnUNetResEncUNetPlans_60G_iso05.json`) gives:
  `ResidualEncoderUNet`, **7 stages**, features [32, 64, 128, 256, 320, 320, 320], blocks
  [1, 3, 4, 6, 6, 6, 6], 142 M parameters ([[Atlas v5]] §2.3). A checkpoint with fewer stages lacks the keys
  of stage 7, and one with other widths fails the shape check. A CADS ResEnc-L or
  TotalSegmentator checkpoint was planned for a different spacing and patch, so its topology differs.
  MedNeXt-v2 is a different architecture.
- **Using any of these weights therefore means changing the master's network**, or re-pretraining on 18–22k
  CTs with the master's plans (thousands of GPU-hours; MedNeXt-v2 pretrained for 1500 epochs on 4 GPUs).
  Partial loading would need a custom loader that nnU-Net does not ship.

## What it implies

1. **The expected gain is small and unmeasured on vessels.**
   - Supervised CT pretraining of the same backbone: +0.9 mean DSC (CADS over ResEnc-L).
   - TotalSegmentator weights: +0.6 (over nnU-Net).
   - The best pretrained ConvNeXt: +2.05 over ResEnc-L from scratch, half of it from the larger fine-tune
     patch (82.95 at 128³, 83.70 at 192³).
   - On vessel tasks the gain is +0.8 to +1.6 Dice over default nnU-Net (SegBook).
   - The one fine-spacing vessel case (MAE Table 9) went the wrong way by 14 Dice.
2. **The master's data regime is the one where pretraining helps least.** It has 560–900 labelled cases
   of one structure. SegBook finds the smallest fine-tuning gains on medium-sized sets (about +1 %). The
   MAE paper's gains concentrate in low-data runs.
3. **The master's 128 mm context would have to be given up** to adopt MedNeXt-v2. Its fine-tune patch is
   192³ at the pretraining spacing; at 0.5 mm that is 96 mm. Context is the master's best-supported lever
   ([[Atlas - A 128 mm patch at 0.5 mm holds the whole tree and the LM in almost every training patch]]).
4. **Conclusion:** pretraining does not displace the master. It is at most a conditional, costed proposal
   if the final model misses A10 acceptance ([[Foxtrot v1]] §F4).

## Limits

- Pretraining numbers are from the authors' own benchmarks (DKFZ for MedNeXt-v2, CADS and the MAE paper).
  No independent replication was found.
- No paper measures CT-pretrained weights on coronary CTA at 0.5 mm. The vessel evidence is SegBook's
  default-nnU-Net baseline and one MRI angiography task.
- I did not inspect the CADS or MedNeXt-v2 checkpoints themselves. The incompatibility claim follows
  from nnU-Net's loader code and the fact that topology depends on the plans; it is not a load attempt.
