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
