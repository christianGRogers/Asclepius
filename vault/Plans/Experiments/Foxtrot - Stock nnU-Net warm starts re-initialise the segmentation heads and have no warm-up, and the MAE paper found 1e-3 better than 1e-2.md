---
tags: [plans, experiment, literature, fine-tuning, nnunet, code-check, round6]
author: Foxtrot
round: 6
updated: 2026-10-10
---

# Stock nnU-Net warm starts re-initialise the segmentation heads and have no warm-up, and the MAE paper found 1e-3 better than 1e-2

## Question

[[Atlas v7]] §2.7.3 specifies the per-wave fine-tune as follows. Its point 4 rests this on Wald et al.
(CVPR 2025).

> **Warm** (`-pretrained_weights` = the last accepted model, all layers): 250 epochs; SGD Nesterov …
> LR linear 0 → 1e-2 over the first 10 epochs (2,500 iterations), then poly to 0.

Point 4 says of that paper: "fine-tuning nnU-Net without warm-up 'significantly reduces performance', and
warm-up adds 0.6–1 DSC. The same paper fine-tunes with nnU-Net's own SGD 1e-2 poly schedule."

Three things need checking:

- Does `-pretrained_weights` transfer "all layers"?
- Does nnU-Net provide the warm-up?
- What does the cited paper say about the peak LR?

## Method

- Read `nnunetv2/run/load_pretrained_weights.py` and `run_training.py` (nnU-Net 2.8.1, installed here and
  pinned by the master), and `src/segtrain/nnunet_ext/*.py`. Searched `src/` and `trillium/` for any
  warm-up or LR override.
- Re-read Wald et al., *Revisiting MAE pre-training for 3D medical image segmentation*, CVPR 2025,
  arXiv:2410.23132: §4 "Fine-tuning strategy", Table 3 and Appendix A.

## Result

1. **Not all layers.** `load_pretrained_weights` builds
   `skip_strings_in_pretrained = ['.seg_layers.']` and transfers only keys without it. The docstring:
   "Segmentation layers (the 1x1(x1) layers that produce the segmentation maps) identified by keys ending
   with '.seg_layers') are not transferred!" The nnU-Net docs agree: "all layers except the segmentation
   layers will be used". With deep supervision, every output head of the warm model is re-initialised,
   even though the classes are identical across waves.
2. **No warm-up exists.** A `-pretrained_weights` run is a fresh `nnUNetTrainer` training at
   `initial_lr = 1e-2` with `PolyLRScheduler` from epoch 0. The nnU-Net docs: "So far there are no specific
   nnUNet trainers for fine tuning … You can however easily write your own trainers with learning rate ramp
   up". Neither `src/segtrain` (`nnUNetTrainer_segtrain`, `…_coronary`) nor `trillium/` contains a warm-up
   or a fine-tune trainer (grep for `warm`, `pretrained`, `initial_lr`, `optimizer`). The only hit is a
   comment in `trillium/atlas/lib/report.py`.
3. **The paper's LR finding goes the other way.** Its §4 lists three observations:
   - "(i) Warm-up stages are essential: Not applying a warm-up step significantly reduces performance.
     Including a warm-up for both the encoder and decoder boosts accuracy by 0.6 to 1 DSC points." Atlas
     quotes this correctly.
   - "(ii) Learning rate adjustments matter: Reducing the peak learning rate to 1e-3 during fine-tuning
     consistently yields better results than the default 1e-2, with the best performance seen when
     fine-tuning both the encoder and decoder with lower learning rates."
   - "(iii) Freezing encoder weights is detrimental."

   Table 3's best row (full transfer, both warm-ups, peak 1e-3) averages **71.76**. The same schedule at
   1e-2 averages 71.02, and at 1e-4 70.95. "SGD 1e-2 poly" in the paper is the *pretraining* and baseline
   hyper-parameter set (Appendix A), not the fine-tuning optimum. The warm-up was 12.5k steps, i.e. 50
   nnU-Net epochs, not 10. MedNeXt-v2 (arXiv:2512.17774) also fine-tunes at peak 1e-3 with a 50-epoch
   warm-up.

## What it implies

1. **Atlas v7's warm-start arm, as written, cannot be run with the code that exists.** A fine-tune
   trainer has to be written that:
   - loads *all* layers, including `seg_layers`, since the classes are identical (a few lines: copy the
     state dict without the skip list);
   - ramps the LR.

   Until it exists, "warm" in FT1 would mean stock nnU-Net: heads reset, no warm-up, peak 1e-2 at epoch 0.
   That is the configuration the MAE paper found worst, and FT1's warm-vs-scratch decision would be
   judging that rather than the intended recipe. This is a pre-condition to put in the plan before FT1, not
   a reason to drop warm starts.
2. **The citation supports warm-up but not the 1e-2 peak.** Atlas's own reason for 1e-2 (unlearn the
   proxy's naming habits, nothing to forget with all data present) is a first-principles argument. It is
   different from the MAE setting (SSL to a new task), and it may well be right for same-task continuation.
   The evidence note, however, should not say the paper fine-tunes at 1e-2. The peak LR is untested on our
   task. Making it the second arm of FT1 would cost a third 250-epoch run, about 12 H100-h. Whether that is
   worth it is Q1's decision (Atlas/Crucible); I flag it, I do not claim it.
3. **The warm-up length should be stated in steps from a source.** 10 epochs is 2,500 iterations, a fifth
   of the cited 12.5k.

## Limits

- The MAE paper's fine-tuning is SSL-pretrained to a new task on brain MRI. Its LR optimum need not
  carry to warm-starting the same task from a model trained on proxy labels.
- Text extraction dropped Table 3's check marks. The configuration of each row (which weights were
  transferred, which warm-ups ran) is therefore inferred from row order. The last three rows differ only
  in LR, and the prose quoted above (observations i–iii) confirms that reading.
- I did not run a fine-tune (no GPU). Points 1 and 2 of the result are code facts for nnU-Net 2.8.1.
