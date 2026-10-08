---
tags: [plans, experiment, pending, trillium, gpu, topology, post-processing, tree-f1]
author: Delta
round: 3
updated: 2026-10-08
status: pending — prepared, not yet run
---

# PENDING (Trillium, 1 × H100 ≤ 24 h): does gap-centred re-inference beat nnU-Net's default inference on a thick-convention 4-class model?

## Question

All of the real-prediction evidence for P1′ (gap-centred re-inference before ≤ 3 mm bridging), and for
bridging generally, comes from one model and one setting: ImageCAS-X's released *binary* nnU-Net
(96 × 160 × 160 patch, thin lumen), run at tile step 0.75 with oracle names (Round 2 ruling, C1 and
C3). The project has since decided ([[Human decisions]]) on the **thick** convention: the original
ImageCAS mask, split into four classes (territory rule, ramus → LCx). This run asks four things, on a
real **4-class** model trained on that convention:

1. How often does a master-class model cut trees? Measured by rooted recall @ 1.5 mm < 0.9.
2. Does P1′ beat **nnU-Net's default inference (tile step 0.5)**? This is the control the judge asked for.
3. Does ≤ 3 mm bridging alone, or the support rule, help? And how many false-positive joins does each make?
4. Does label repair help on real 4-class names?

## Method (code: `trillium/delta/`, entry point `./delta`)

**Data.** The thick reference and target are built on the login node and inside the job:
- ImageCAS-X names are fetched from Zenodo by HTTP range read (18 MB).
- Each ImageCAS mask voxel takes the 4-class name of the nearest ImageCAS-X voxel. Territory rule;
  ramus → LCx; "Other" goes to its nearest named neighbour.
- Train on the ImageCAS-X train + val lists (640). Test on the ImageCAS-X test list (160, never trained on).

**Model.** nnU-Net v2.8.1 with these settings:
- `nnUNetPlannerResEncL` at 0.5 mm isotropic;
- the master's fixed CT window [−300, 1300] HU (mean 100, sd 400);
- `nnUNetTrainerDelta`: no mirroring, 250 epochs (the master's ablation length), checkpoint every 10
  epochs, and a deadline-aware epoch budget so training ends ≥ 5 h before the walltime.

ResEnc-L rather than the master's 256³ / 60 GB configuration, so that the whole run fits in 24 h. Its
128-voxel patch is still far larger than the released model's.

**Inference per test case.** Two full passes, at tile step 0.5 (default) and at 0.75. Then, for each:
- deployable anchors: the 2 largest predicted components within 3 mm of the contrast blood pool;
- re-inference: one gap-centred window per un-anchored piece within 15 mm, max-fused on vessel probability;
- variants:
  - raw;
  - raw + bridge 3 mm;
  - raw + label repair;
  - re-inference;
  - re-inference + bridge;
  - re-inference + support-gated bridge;
  - re-inference + support-gated bridge + repair.

**Metrics.** Scored on the thick reference:
- tF1 at 1.5 mm and at 0 mm, using the model's real names;
- ostia from the two cross-checked cheap rules, with flagged trees counted;
- macro Dice, rooted recall;
- the raw FP gate (before repair), FP after repair, and the bridge audit (true join / FP join / cross-tree).

**Outputs.** `results/SUMMARY.md`, `results.json`, `per_case.jsonl`, and training logs, with paired
bootstrap CIs for each comparison C1–C7.

**Tested on CPU here.** Both case layouts are detected, the dry-run prints the job script, and an
end-to-end smoke run (5 cases, 1 epoch, 64³ patch) passes; see Delta v3 §2.

## What result would change which decision

| Result | Decision |
|---|---|
| C2 (s05 + P1′ vs s05 raw) CI > 0 and no case worse | P1′ is adopted into the master's post-processing (A2), on by default |
| C2 CI includes 0, or any case worse by > 0.01 | **P1′ is dropped**; the master keeps nnU-Net's default inference |
| C1 (tile 0.5 vs 0.75) > 0 and C3 ≈ C2 | the CPU-side P1′ gains were an overlap artefact; drop P1′ |
| C4 (bridging alone) ≈ 0, or FP joins ≥ true joins | A2's P1 bridging is removed rather than left switchable |
| C5 (support rule) ≤ 0 | the support rule is dropped. CPU evidence already points this way, see Delta v3 |
| C6 (label repair) CI > 0 | P2 label repair goes on by default |
| cut-tree rate on the thick convention ≤ 1 case in 160 | the connectivity stage becomes QA-only; the A5 calibre trigger stays off |
| cut-tree rate ≥ 5 % | connectivity stays a first-class model-selection criterion; tF1 remains decisive |

## Limits (stated in advance)

- One run, one seed, ResEnc-L rather than the master's exact configuration, 250 epochs.
- The thick reference is a proxy (ImageCAS-X names projected onto the ImageCAS mask). No team label exists yet.
- The blood-pool anchor is used instead of TotalSegmentator, which needs about 7 GB and a weights download.
