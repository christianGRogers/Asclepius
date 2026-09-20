---
aliases: [Proposed changes, Architecture proposals]
tags: [research/architecture, proposal, decision-record]
status: living
updated: 2026-09-19
---

# Proposed changes to the training plan

Concrete edits to [[Training plan]] proposed by the architecture-and-training
research thread, each with the note that carries the evidence. Nothing here has been
applied; this folder does not edit the plan.

## 1. Correct the cascade-trigger threshold (factual error)

**Where:** §2, gate (a); and the header comment of
`configs/tasks/Dataset710_Coronary.yaml` (line ~11).
**Now:** "patch fraction ≥ 12.5 % so no cascade is planned".
**Proposed:** "patch fraction ≥ 25 % — nnU-Net v2's `lowres_creation_threshold` —
so the patch sees at least a quarter of the median volume. If a `3d_lowres` entry is
written anyway, it is harmless: `configuration: 3d_fullres` decides what trains, and
preprocessing can be limited with `-c 3d_fullres`."
**Why:** verified in nnU-Net source at tags `v2.5.1`, `v2.6.2` and `master` —
`self.lowres_creation_threshold = 0.25`. The plan's estimated 27–30 % patch fraction
is a few points clear of the real threshold, not double it.
**Evidence:** [[Cascade and low-resolution stages cost more than they buy on 0.35 mm vessels]].

## 2. State the resolution evidence with both ImageCAS numbers

**Where:** §1.
**Now:** "−12.3 % Dice going from 512²×256 to 128³".
**Proposed:** add the intermediate point — "−7.38 % at 256²×128 and −12.32 % at 128³,
both p < 0.0001" — because the intermediate point is the one that resembles a
low-resolution cascade stage, and it alone is six times the size of the attention
module (1.34 %) in the same ablation.
**Evidence:** [[Patch size is the dominant lever for thin vessels, and the evidence supports the 70 GB budget]].

## 3. Write down the expected effect size for the paired ResEnc run

**Where:** §3.3.
**Proposed:** add "Expected effect: on the two discriminative datasets in nnU-Net
Revisited, ResEnc L gained +2.13 (KiTS) and +0.77 (AMOS) Dice over the plain
nnU-Net; the AMOS2022 ablation in *Extending nnU-Net is all you need* isolates the
residual encoder at +0.37. A paired difference under ~0.5 Dice is inside the noise
and the plain configuration stays." Also note the runtime: ResEnc L was 3.9× the
plain nnU-Net's training time in that benchmark, which is the binding constraint
against a 24 h walltime.
**Evidence:** [[nnU-Net still beats transformer and Mamba architectures, and ResEnc is the only upgrade worth paying for]].

## 4. Add Mamba-based U-Nets to §4 "explicitly ruled out"

**Proposed:** "**Mamba-based U-Nets.** nnU-Net Revisited's 'No-Mamba Base' ablation —
the same network with the Mamba blocks removed — matched or beat both U-Mamba
variants on five of six datasets at lower VRAM. There is no measured contribution
from the state-space blocks to buy."
**Evidence:** same note as (3).

## 5. Add a patch-budget sanity experiment to §5 (standing experiments)

**Proposed:** plan the binary model twice — `--gpu-mem 24` (≈ the published ResEnc-L
operating point) and `--gpu-mem 70` — and train both on the same fold. The published
patch-size curves on ImageCAS stop at 64³, and nnU-Net Revisited showed VRAM scaling
going *negative* on three of six datasets between its 22.7 GB and 36.6 GB presets.
One extra chained job converts the plan's central extrapolation into a measurement
on our own data, and it can run before any per-branch labels exist.
**Evidence:** [[Patch size is the dominant lever for thin vessels, and the evidence supports the 70 GB budget]].

## 6. Take a position on ensembling

**Where:** evaluation section.
**Proposed:** one sentence. Both ImageCAS-scale papers show ensembles winning
(82.96 % via coarse+patch ensemble; DSC 0.8337 via a 3D nnU-Net ensemble), and the
5-fold models exist anyway — but inference cost is already 3–4× up from the no-crop
decision, so ensembling is a reporting option, not the deployed configuration.
**Evidence:** [[Cascade and low-resolution stages cost more than they buy on 0.35 mm vessels]].

## 7. Rule out promptable/foundation segmentation models by name, with evidence

**Where:** §4 "explicitly ruled out".
**Proposed:** "**Promptable/foundation 3D segmentation models (SAM-Med3D, MedSAM,
VISTA3D) as the primary segmenter.** MedSAM's own literature documents a structural
weakness on vessel-like branching structures (ambiguous box prompts); the one
purpose-built vascular foundation model (vesselFM) scores 29.69 Dice zero-shot on
its only CT vascular benchmark and was never measured against a from-scratch
nnU-Net; VISTA3D reports no coronary class and uses 128³ patches, the exact
resolution [[Patch size is the dominant lever for thin vessels, and the evidence
supports the 70 GB budget]] shows costs 12+ Dice points on this cohort."
**Evidence:** [[Foundation and promptable models do not yet beat a configured nnU-Net for coronaries]].

## 8. Correct the mechanism behind the "class-balanced sampling" standing experiment

**Where:** §5.
**Now:** "nnU-Net's default picks one random foreground class for a third of
patches; with many classes of wildly different volume — some absent in many
patients — rare branches starve."
**Proposed:** "nnU-Net's default already samples uniformly among the foreground
classes *present in a given case* for the oversampled third of patches
(`DataLoader3D.get_bbox`, verified in source) — that step is not where starvation
comes from. The starvation is at case-selection frequency: a class present in only
a fraction of the 1000 cases gets attention only when one of those cases is drawn,
at the same rate as any other case, with no compensation for cohort-wide rarity. A
fix should reweight case selection or per-case oversampled-slot allocation by
class rarity, not the already-uniform per-case class choice."
**Evidence:** [[Class-balanced and vessel-anchored patch sampling for rare distal branches]].

## 9. Schedule binary-init fine-tuning as a higher-priority cheap experiment

**Where:** §3.2 / §5.
**Proposed:** move "binary-init fine-tuning vs from-scratch" from an unranked
standing experiment to the first thing tried once any per-branch labels exist,
since it costs nothing beyond a checkpoint the plan already produces at §3.1. Add
the supporting analogy: in-domain SSL pretraining on this exact cohort (UNETR,
ImageCAS) measured +4.8 Dice internal / +4.1 external over training from scratch,
with the gain largest when fine-tuning data is scarcest — which is exactly the
early-annotation regime the multiclass model starts in.
**Evidence:** [[Binary-init fine-tuning and multi-task auxiliary heads for the multiclass model]].

## 10. Name the downstream-graph-labelling failure mode explicitly in §4

**Where:** §4, the sentence "Graph reasoning is welcome downstream... but must
never be able to lose a vessel the voxel model found."
**Proposed:** add the measured mechanism: "Measured directly on CCTA (Hampe et al.,
J Med Imaging 2024): anatomical-labelling F1 on a graph network's own automatically
extracted coronary trees was 0.74, against 0.95 on reference (manually extracted)
trees — a 21-point gap attributable entirely to upstream extraction error, with the
authors attributing it to missed septal branches and ostium-leak pruning. The
lesson generalises: any pruning/refinement step inside a downstream graph stage is
where a real vessel can be silently deleted, and is the step to audit hardest."
**Evidence:** [[Downstream graph labelling of coronary branches is a second stage, never the segmenter]].

## 11. Schedule deep supervision as a standing experiment with conditional activation

**Where:** §5 "Standing experiments."
**Proposed:** add "**Deep supervision (DBDS variant)**: add intermediate supervision losses at encoder and decoder branches of the network. Use a default α (intermediate-loss weight) in range 0.1–0.4, tuned by validation loss during training. Same fold/harness as multiclass baseline. Acceptance criterion: convergence speed (epoch count to early-stop) improves and final validation Dice does not drop >1 pp; if both hold, this becomes the default trainer going forward. Conditional on multiclass labeling; does not block binary model."
**Evidence:** [[Deep supervision and patch overlap for segmenting tubular structures at native resolution]].

## 12. Confirm patch-overlap percentage and tune as post-baseline lever

**Where:** §2 gates / evaluation section.
**Proposed:** "(f) Confirm from `nnUNetv2_find_best_configuration` output that sliding-window inference overlap is 50%. If the multiclass baseline shows excessive fragmentation (β₀ component count >> expected anatomy), rerun inference from the best-validation checkpoint with 90% overlap (via trainer override) and measure Dice, HD95, and component count. Accept 90% overlap only if Dice improves >1 pp and component count moves toward expected."
**Evidence:** [[Deep supervision and patch overlap for segmenting tubular structures at native resolution]].

## 13. Add per-class validation Dice monitoring for multiclass convergence decisions

**Where:** Evaluation and training monitoring section.
**Proposed:** "Log per-class validation Dice at every 500 epochs during multiclass training, up to early-stopping. If any class (especially rare branches with <50 mean voxels per case) shows continued improvement past the mean-loss early-stopping point (validation loss plateau for 60 epochs), note this disagreement. If rare-class Dice is still <50 % at the loss-based stop, consider a third 24-h job to extend training — decision deferred to inspection of the specific run."
**Evidence:** [[Training schedule length and early stopping on a 24-hour walltime with job-chain resume]].
