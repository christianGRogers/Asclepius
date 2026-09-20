---
aliases: [Branch splitting tools, Centerline-based splitting, Semi-automatic annotation tools]
tags: [research, annotation, label-efficiency, tools, literature]
status: complete
updated: 2026-09-20
---

# What tools exist for semi-automatic branch splitting of vessel segmentations

The project's [[Training plan]] commits to seeding annotators with the binary lumen model's predictions to enable branch splitting ("its predictions become the presegmentation seeds SegQueue hands annotators — splitting an existing tree is minutes"). This note surveys what semi-automatic tools and published methods exist for this task in coronary imaging and nearby vascular trees, and what time costs they report.

## CoronaryExplorer: the tool for coronary CT angiography

**Bransby KM, et al. *ImageCAS-X: a dataset and benchmark for coronary artery segmentation and centerline extraction in coronary CT angiography.* arXiv:2608.30404, 2026 (preprint, under review).** The paper describes CoronaryExplorer as the annotation tool used for 800 ImageCAS cases.

### Design and workflow

CoronaryExplorer is a **3D Slicer v5.10 extension** that implements a centerline-first branch-splitting workflow:

1. **Automated centerline initialization**: Centerlines are extracted automatically using a previously-validated method (not detailed in the paper), then presented to the annotator.
2. **Manual centerline refinement**: Analysts trim spurious segments, draw missing vessels by hand if the automatic extraction missed them, and correct the topology.
3. **Centerline naming**: Each centerline segment is assigned a name from the 14-class schema (ImageCAS-X's adaptation of SCCT 18-segment model).
4. **Automatic lumen propagation**: Once centerlines are named, the tool assigns each lumen voxel to the name of its nearest centerline point (Voronoi assignment — see [[Bifurcation ownership and carina voxel assignment]]).
5. **Lumen review**: Analysts review the propagated lumen mask and correct obvious errors (holes, leakage into neighboring structures).

### Time cost

The paper reports labor investment on 800 ImageCAS cases with binary lumen segmentations pre-provided:

- **Centerline correction**: 200 hours total across 800 cases = **15 minutes per case average**
- **Lumen correction**: 270 hours total = **20 minutes per case average**
- **Total per-case time with presegmentation**: ~**35 minutes per case**

For comparison: annotators labeling from scratch without presegmentation reported taking 3–5 hours per case in the FIVES retinal vessel dataset (Jin et al., Sci Data 2022; see [[Can non-experts label vessels as well as experts]]), though retinal vessels are a different modality and anatomy than coronary.

### Critical assumption

CoronaryExplorer's time budget assumes the input binary lumen mask is already correct — or at least, mostly correct. If the mask is a model prediction with systematic errors (e.g., missing fine branches, leaking into non-coronary vessels), the "lumen correction" phase will be longer. The paper does not separate time for fixing the presegmentation from time for naming it. This is noted because [[Seeding annotation with model predictions and label efficiency]] flags presegmentation bias: if the binary seed is worse than annotators expect, correction time rises and bias in the seed propagates forward.

## Related semi-automatic tools in nearby vascular trees

No other coronary-specific semi-automatic tool is documented in the open literature. The closest analogues in other vascular territories are:

### Brain vessel centerline annotation

**An automated framework for brain vessel centerline extraction**, reported in arXiv papers on cerebral vessel segmentation (search result: arXiv:2401.07041). The workflow is similar: automated centerline extraction from a segmentation, manual refinement, then propagation into a full mask via graph cuts or kernel regression. Time costs not reported in the search results accessed.

### Retinal vessel tracing

**Robust semi-automatic vessel tracing in the human retinal image by an instance segmentation neural network** (arXiv:2402.10055). Uses a learned model to detect vessel centerlines and branch points; annotators then interactively correct. Time costs: not extracted.

### General vascular tree methods (patent literature)

Multiple patents describe "methods for extracting centerline representation of vascular structures in medical images via optimal paths in computational flow fields" (USPTO 10206646) and "3D vessel segmentation with minimal cuts" (USPTO 8126232). These are implementations (not published research) and do not report validation or time costs.

## Centerline extraction accuracy: how good is the input to the branch-splitting workflow?

If centerlines are provided automatically, their accuracy sets the ceiling for how fast branch-splitting can proceed. The Voronoi-based 3D centerline extraction paper (Automated Coronary Artery Tracking with a Voronoi-Based 3D Centerline Extraction Algorithm, PMC10743762) reports high accuracy on pre-segmented coronary arteries:

- **Overlap (OV)**: 99.97% (fraction of true centerline points found)
- **Overlap until first error (OF)**: 100% (algorithm did not fail catastrophically before finding an error)
- **Clinically relevant overlap (OT, vessels >1.5 mm)**: 99.98%
- **Average inside error (AI)**: 0.13 mm (spatial error on correctly-extracted points)

This is good news for the branch-splitting workflow: if the binary lumen segmentation is correct, the automatic centerline extraction is extremely accurate and the annotator's job is mostly naming, not correcting the path. The caveat: this accuracy was measured on *manual* binary segmentations, not model predictions. A model-generated presegmentation with missing branches or false positives will degrade centerline accuracy proportionally.

## What this implies for [[Training plan]]

- **CoronaryExplorer's documented time** (~35 min/case with presegmentation, including both centerline and lumen correction) is the benchmark for branch-splitting cost in this project. This is what the presegmentation-seeding plan assumes.
- **The binary model quality is load-bearing**. If the binary model reaches ~0.83 Dice (the ImageCAS published benchmark), CoronaryExplorer's 35-min/case workflow holds. If the model is substantially worse (>5 % Dice drop), lumen-correction time will increase and [[Seeding annotation with model predictions and label efficiency]]'s bias caveat becomes acute.
- **No other open-source coronary-specific tool exists**. CoronaryExplorer is part of the ImageCAS-X dataset codebase (under MIT license, github.com/MathildeBS1/ImageCAS-X). If SegQueue's existing 3D Slicer extension (docs/SEGQUEUE.md) does not already implement centerline-first naming, CoronaryExplorer's design is the reference to follow for the multiclass step.
- **Centerline accuracy is not the bottleneck** — Voronoi-based methods extract coronary centerlines at 99.97 % overlap accuracy, which is well above what an annotator can verify by eye. The refinement step is correctness-checking and path-drawing for missed distal branches, not center-finding.
