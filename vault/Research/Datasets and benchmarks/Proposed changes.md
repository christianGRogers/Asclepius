---
aliases: [Proposed changes (datasets and benchmarks)]
tags: [research, dataset, benchmark, proposed-changes]
status: living
updated: 2026-09-19
---

# Proposed changes

Concrete changes this topic's research argues for, in [[Training plan]].
Each carries the note that justifies it. Nothing here has been applied — the
plan is owned elsewhere. (No changes are proposed to `src/segtrain/`; this
topic is about data and evaluation cohorts, not code.)

## To [[Training plan]] fixed constraints / §3 (sequence)

| # | Change | Evidence |
|---|---|---|
| D1 | Demote the 82.96 % Dice figure explicitly: state it is an under-trained (21 k-iteration) baseline on labels a later re-annotation scores at 41.8 % DSC against, not the state of the art | [[State of the art on ImageCAS]] |
| D2 | Replace the calibration numbers with the ImageCAS-X table (nnU-Net 89.8 ± 3.2, CAS-Net 91.2 ± 2.8, inter-observer 92.8 ± 3.1, all binary lumen, ImageCAS-X's 160-case test set) for any comparison on the re-annotated labels | same |
| D3 | Treat the 1000 merged ImageCAS masks as weak labels (41.8 % DSC vs re-annotation, includes plaque/pulmonary vessels/coronary veins); design the annotator presegmentation UI so deletion is as cheap as drawing | same |
| D4 | Replace "inter-observer agreement ≈ 0.856" — untraceable to ImageCAS or ImageCAS-X — with a sourced figure. Two candidates: ImageCAS-X's 92.8 % (same cohort, preferred), or ASOCA's inter-annotator DSC of 85.6 % ± 7.7 % (different cohort, but a near-exact numeric match to the untraced 0.856, and the most likely original source) | [[State of the art on ImageCAS]], [[Public coronary CCTA datasets]] |
| D5 | State per-branch targets from ImageCAS-X Table 1 (main branches 84.8–95.3 DSC, side branches 70.9–83.6), with the caveat that no model comparator exists yet — only human inter-observer | [[State of the art on ImageCAS]] |
| D6 | Add nnU-Net+clDice's measured result on this cohort (+0.2 DSC, −2.4 Betti points) to the loss experiment description as a caution, not an assumed win | same |

## To [[Training plan]] fixed constraints (fold scheme)

| # | Change | Evidence |
|---|---|---|
| D7 | Binary calibration run: train on ImageCAS official `Split-1` (700/50), score on its 250 `Testing` cases against original masks — the only configuration in which "beat 82.96 %" is meaningful | [[Fold schemes and split ratios]] |
| D8 | Multiclass runs: seal the ImageCAS-X 160-case test set; 5-fold CV over the 640 train+val cases; ablations on fold 0 only, all 5 folds for the final config only (walltime budget) | same |
| D9 | Binary-init fine-tuning is only valid if the binary model's training set excludes all 160 ImageCAS-X test IDs — otherwise the multiclass test set has leaked through initialisation. Retrain the binary model on ImageCAS-X's 640, or drop the experiment | same |
| D10 | Report the official-split/ImageCAS-X-test-set ID intersection once computed, so the leakage risk is a documented fact, not a rediscoverable trap | same |
| D11 | Stratify our own 5-fold construction on coronary dominance and disease status (ImageCAS-X's `Descriptors.xlsx`: 729 right-/41 left-/30 co-dominant; 388 diseased/412 not) — unstratified folds can starve L-PDA/L-PLA, which exist only in left-/co-dominant cases | same |
| D12 | The 200 ImageCAS scans ImageCAS-X excluded for image quality stay out of every split unless reported as a separate "non-diagnostic" set | same |

## To [[Training plan]] (nnU-Net method notes, §1/§4)

| # | Change | Evidence |
|---|---|---|
| D13 | Correct the ImageCAS resolution-penalty figure to 12.32 % (512×512×256 vs 128³, p < 0.0001), stated in the paper's direction | [[Research context]] |
| D14 | Add mirroring **test-time augmentation** (not just training augmentation) to the list of things disabled for the multiclass model — nnU-Net applies both by default and the plan currently names only the training-time one | same |
| D15 | Acknowledge that nnU-Net's largest-component post-processing is a *measured, conditional* step in the original method (adopted only if cross-validation shows no per-class Dice loss), even though the plan is right to rule it out here on ImageCAS's own Fig. 8(b) evidence | same |

## To [[Training plan]] (external validation — new, not currently in the plan)

| # | Change | Evidence |
|---|---|---|
| D16 | Add an external-validation step for the binary calibration run: score the ImageCAS-trained model on ASOCA's 40 labelled cases (different scanner vendor, different acquisition protocol). Expect a ~5–8 point Dice drop based on three independent cross-dataset measurements; a larger drop signals overfitting to ImageCAS's single-centre/single-scanner protocol | [[External validation and cross-dataset generalisation for coronary segmentation]], [[Public coronary CCTA datasets]] |
| D17 | Report contrast enhancement and edge sharpness alongside any external-validation Dice — the strongest measured correlates of cross-dataset performance in the one paper that tested for them (Zhang et al. 2025) | same |
| D18 | State explicitly, in any manuscript, that no external per-branch benchmark exists — an undisclosed absence of external validation is a completeness gap under Metrics Reloaded / reporting-standards guidance, not a neutral omission | [[External validation and cross-dataset generalisation for coronary segmentation]] |
| D19 | No public dataset besides ImageCAS-X ships per-branch voxel CCTA labels (checked as of this search, 2023–2026 releases included) — this hardens rather than changes [[Class schema options]]'s recommendation; record it as corroboration | [[Public coronary CCTA datasets]] |

## ImageCAS stents and calcification (new, from this session)

| # | Change | Evidence |
|---|---|---|
| D20 | Check ImageCAS dataset metadata for stent prevalence, calcification burden (Agatston score), and disease-severity distribution before finalizing the binary model. If available in Girder copy or from ImageCAS authors, document prevalence; if not available, state this as a data-documentation gap | [[ImageCAS disease burden and calcification status]] |
| D21 | For external validation on ASOCA, stratify performance by calcification burden if per-case Agatston scores are available from the UK Data Service. A calcification-stratified Dice drop is direct evidence of whether blooming is a learned or un-learned failure mode | same |
| D22 | If stents are present in >5 % of ImageCAS cases, version-gate annotation interface so stented segments are annotated separately or flagged for auditor review; report performance by stent status. If stents are rare, accept stented segments as a known gap and disclose in manuscript | same |

## ImageCAS annotation protocol quality control (new, from this session)

| # | Change | Evidence |
|---|---|---|
| D23 | Explicitly state that ImageCAS's 1000 masks are weak labels: cite the 41.8 % Dice discrepancy between original ImageCAS and ImageCAS-X re-annotation (Bransby et al. 2026) as evidence of systematic bias in lumen-boundary definition. This is not a criticism; it is acknowledgment that "lumen" means different things to different annotators | [[ImageCAS annotation protocol and quality control]] |
| D24 | Design presegmentation UI for easy correction: deletion of false-positive pulmonary vessels and non-lumen plaque must be one-click. Drawing corrections are costlier; presegmentation is a seed, not a final prediction | same |
| D25 | Consider seeding per-branch annotation from ImageCAS-X labels (800 of 1000 scans available on Zenodo, CC BY 4.0) instead of original ImageCAS predictions. Trade-off: cleaner presegmentation vs. additional data access and license (already open-source compatible) | same |
| D26 | Specify upfront lumen-boundary definition for annotators (e.g., "innermost opacified border") and enforce with automatic tools (thresholding + Slicer). This is more rigorous than the original ImageCAS protocol (two readers + third arbiter, no explicit definition) | same |
| D27 | Report per-branch inter-observer agreement (DSC, clDice) on the annotation overlap set. This becomes the multiclass per-class ceiling, replacing reliance on ImageCAS-X numbers, and reveals any systematic biases (do certain branches get consistently undersegmented?) | same |

## Data licensing (new, from this session)

| # | Change | Evidence |
|---|---|---|
| D28 | ImageCAS (1000 original masks) has no public license. Seeking author permission is needed before releasing trained weights; alternatively, include a caveat that end-users must obtain ImageCAS access independently | [[Data licensing and model-weight release restrictions]] |
| D29 | ImageCAS-X (800 cases, Zenodo 10.5281/zenodo.21887809) is CC BY 4.0. Any multiclass model trained on ImageCAS-X can be released under CC BY 4.0 with attribution to Bransby et al. This covers model weights and removes licensing ambiguity | same |
| D30 | ASOCA (40 labelled cases) is CC BY 4.0 via UK Data Service. External-validation results are freely publishable and the model can be released under CC BY 4.0 with ASOCA attribution | same |
| D31 | Choose a license for per-branch labels created by this project (recommend CC BY 4.0 for consistency with ImageCAS-X) and state it explicitly in dataset release and GitHub | same |
| D32 | Include a "Data and code availability" section in any manuscript: which datasets were used for training, their licenses, whether model weights can be obtained and under what license/conditions, and data access (Zenodo/GitHub/email contact) | same |

## CCA-200 and PCCTA120 label format clarification (new, from this session)

| # | Change | Evidence |
|---|---|---|
| D33 | **CCA-200 is not suitable for voxel multiclass training.** It ships internal-diameter annotations (1D series), not voxel masks. If centerline-extraction evaluation becomes a goal, verify the diameter-series format from primary source first; it is a different task | [[CCA-200 and PCCTA120 label formats and suitability]] |
| D34 | **PCCTA120 requires primary-source verification.** The 2026 paper's full text must be read to determine whether it is a plaque dataset with a binary-lumen sidecar, a two-class lumen-plus-plaque dataset, or something else. Current evidence is too sparse to guide use; 30-minute hand fetch is needed | same |
| D35 | Record for the record: **no additional per-branch CCTA voxel datasets besides ImageCAS-X were found** in a 2023–2026 search (CCA-200 and PCCTA120 do not fill the gap). ASOCA (binary lumen, CC BY 4.0) remains the only external-validation option for binary segmentation | same |

## Open, not yet proposed

- Whether ASOCA's 20 unlabelled test cases (from the original MICCAI 2020
  challenge) are worth pursuing for a second, blinded external check — would
  need contacting the organisers; not investigated.
- ImageCAS stent prevalence and calcification distribution — flagged for
  direct check against Girder dataset or ImageCAS authors.
