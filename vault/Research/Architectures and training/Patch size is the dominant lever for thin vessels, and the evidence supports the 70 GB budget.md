---
aliases: [Patch size evidence, 70 GB patch budget, Large patch training]
tags: [research/architecture, patch-size, resolution, nnunet, evidence]
status: solid
updated: 2026-09-19
---

# Patch size is the dominant lever for thin vessels, and the evidence supports the 70 GB budget

Sub-question: does training at native resolution with very large patches (the
~70 GB, ~256³ plan in [[Training plan]] §2) actually buy accuracy on vessels, or is
it an expensive way to buy nothing? Second question: patch size or batch size, if
VRAM has to be split?

## Input resolution: the largest single effect measured on this cohort

Zeng, Wu, Lin, Xie, Hong, Huang, Zhuang, Bi, Pan, Ullah, Khan, Wang, Shi, Li, Xu.
*ImageCAS: A large-scale dataset and benchmark for coronary artery segmentation
based on computed tomography angiography images.* **Computerized Medical Imaging
and Graphics** 2023, DOI
[10.1016/j.compmedimag.2023.102287](https://doi.org/10.1016/j.compmedimag.2023.102287).
Read via the author preprint (arXiv:2211.01607). This is our exact dataset: 1000
CCTA volumes, 4-fold CV with 750 train / 50 val / 250 test, all baselines trained
30 epochs (~21 000 iterations) on one RTX 3090 24 GB.

Direct (whole-image) segmentation, varying only the input size (§5.2.1, their
Fig. 4a) — **512 × 512 × 256 beat 256 × 256 × 128 by 7.38 % Dice (p < 0.0001) and
beat 128 × 128 × 128 by 12.32 % Dice (p < 0.0001)**. For comparison, in the same
paper the attention-gate module was worth 1.34 % (p < 0.0001) and going from 4 to 12
channels 2.13 % (p < 0.0001). Resolution is roughly six to nine times the size of
any architectural knob they turned.

Patch size, inside their patch-based pipeline (their Table 3), measured on the same
cohort:

| Patch | Dice, no dilation | Dice, with dilation |
|---|---|---|
| 16³ | 79.56 | 77.80 |
| 32³ | 81.22 | 82.27 |
| 64³ | 82.34 | 82.70 |

16³ vs 32³ p < 0.0001, 16³ vs 64³ p < 0.0001, 32³ vs 64³ p < 0.001 (without
dilation). Their stated reason is the plain one: "a larger patch size obtains a
significantly higher Dice score than a smaller one, which is expected as a larger
patch size has a larger receptive field and thus can capture better context
information." Note the saturation: with their dilated-vessel pre-segmentation
supplying context, 32³ → 64³ became non-significant (p > 0.05). Context can be
bought either by a bigger patch or by handing the network a prior; we are buying it
with the patch.

**Caveat worth writing down.** Both curves stop far below our operating point. The
largest patch ImageCAS tested is 64³ (~0.26 M voxels); our planner is being asked
for ~17–20 M voxels. Nothing in this paper says the gain continues to 256³, and the
dilation column shows the curve *does* flatten once context is sufficient. The
honest claim the plan can make is "small patches are demonstrably harmful on this
data", not "256³ is demonstrably optimal".

## Patch size vs batch size

nnU-Net's own rule (Isensee et al., *Nat Methods* 18:203–211, 2021, condensed in
[[Research context]]) is to spend VRAM on patch size first and hold batch size at a
minimum of 2, precisely to maximise spatial context.

The one published ablation that separates the two components on a large
multi-structure task is Isensee, Ulrich, Wald, Maier-Hein, *Extending nnU-Net is all
you need* (BVM 2023; read as arXiv:2208.10791), on **AMOS2022** (500 CT + 100 MRI,
15 organs), 5-fold CV Dice, Task 1:

| Step | Dice |
|---|---|
| nnU-Net default (patch 64×160×160, spacing 2.0×0.69×0.69, bs 2) | 88.64 |
| + configuration changes (patch 128×192×192, spacing 1.5×1.0×1.0) | 89.08 |
| + residual encoder | 89.45 |
| + batch size raised 2 → 5 | 89.57 |

Reading: re-specifying spacing and patch size was worth +0.44 Dice, the residual
encoder a further +0.37, and **raising batch size from 2 to 5 only +0.12**. That
ordering is exactly the plan's ordering, measured. It also puts the ResEnc gain
(§3.3 of the plan) in the same league as getting the geometry right, not above it.

Independent corroboration that patch size is a first-class training variable rather
than a memory detail: Fischer, Felsner, Osuala, Kiechle, Lang, Peeken, Schnabel,
*Progressive Growing of Patch Size* (MICCAI 2024, arXiv:2407.07853), who make patch
size a curriculum inside nnU-Net and beat standard nnU-Net training on 7 of the 10
Medical Segmentation Decathlon tasks at roughly 50 % of the runtime. Their result is
about efficiency, not final accuracy, but it only works because patch size changes
what the network learns.

## The counter-evidence to keep in view

nnU-Net Revisited (see
[[nnU-Net still beats transformer and Mamba architectures, and ResEnc is the only upgrade worth paying for]])
scaled the *same* architecture family across 9.1 / 22.7 / 36.6 GB. Going from the
22.7 GB preset to the 36.6 GB preset improved KiTS by 0.50 and AMOS by 0.27 Dice and
made BTCV, ACDC and LiTS slightly *worse*, for nearly double the training time.
Compute scaling is not free accuracy; it pays on hard, large, fine-structured tasks
and stops paying otherwise. Coronary arteries at 0.35 mm are about as far toward the
"hard and fine" end as CT segmentation gets, which is why the argument still points
our way — but the expectation should be a couple of Dice points at most from the
patch budget alone, with the real gain in distal branch *detection* rather than in
Dice. Dice is not the metric that will show this; see the plan's evaluation section.

## What this implies for [[Training plan]]

1. **§2's patch budget is supported, and the supporting number should be the
   in-paper one:** +7.38 % Dice for 512²×256 over 256²×128 and +12.32 % over 128³
   (ImageCAS, p < 0.0001 both). The plan currently states the second figure only.
2. **State the limit of the evidence.** Measured patch-size gains on ImageCAS stop at
   64³ and flatten once context is otherwise available. The 70 GB budget is an
   extrapolation, so it deserves a cheap check rather than an assumption — see
   proposal in `Proposed changes.md` for a paired planner run at ~24 GB (a ResEnc-L
   equivalent) against ~70 GB on the binary model, which costs one extra chained job
   and turns the extrapolation into a measurement on our own data.
3. **Keep batch size at 2.** The only published separation of the two effects puts
   batch 2 → 5 at +0.12 Dice against +0.44 for patch/spacing. The plan's gate (c)
   "batch size 2" is right, and it should be read as *do not let the planner trade
   patch voxels for batch* rather than as a bare sanity check.
4. **Do not expect the accuracy story to show up in Dice.** Budget the evaluation
   (branch detection rate, clDice) as the place where a large patch is expected to
   pay.

Related: [[Cascade and low-resolution stages cost more than they buy on 0.35 mm vessels]].
