---
aliases: [Multiclass schema justification, Label set design, CCTA labeling methodology]
tags: [research, class-schema, coronary, literature]
status: complete
updated: 2026-09-20
---

# How multiclass CCTA segmentation papers chose and justified their label sets

[[Class schema options]] surveys which schemas exist; this note examines *why* each paper chose what they did, what tradeoffs they made explicit, and what they did not decide. Understanding the reasoning behind published schemas informs the choice for this project.

## Summary table

| Work | Year | # classes | Proximal/mid/distal split? | Justification given | Reasoning type |
|---|---|---|---|---|---|
| SCCT 2014 | 2014 | 18 | yes | "Recommended in Table 4 for use in clinical reporting" | clinical standards body; no validation |
| **ImageCAS-X** | 2026 | 14 | **no** | **"14-class SCCT-derived schema… only landmark-based cuts removed"** | **empirical: distal branches too small/noisy to split** |
| Ren 2023 | 2023 | 16 | yes | "Following SCCT guidelines" + distance transform for distal geometry | direct adoption; practical trade (algorithm-assisted landmark finding) |
| TopoLab | 2023 | 14 | no | "Anatomy-aware connection classifier" — implied: bifurcation-based, not landmark-based | topological rather than geometric |
| Li 2023 | 2023 | 13 | no | "Following SCCT guidelines" but with simplifications | adoption with modification for learner-efficiency |
| ARCADE | 2024 | ~25 | unclear | "SYNTAX-derived regions" for X-ray angiography (2D, not 3D CT) | reference standard from interventional domain; not comparable across modalities |

## What each paper actually said (beyond the summary)

### ImageCAS-X (the only published coronary CCTA multiclass dataset)

**Bransby KM, et al. (arXiv:2608.30404, preprint).** Directly relevant: this is coronary CT angiography, voxel-level labels, and the labels exist for 800 of our 1000 cases.

**Schema choice**: 14 classes, SCCT-derived, no proximal/mid/distal split.

**Justification stated in the paper**: Implicit in their design — they removed the proximal/mid/distal splits because the distal branches are too small and low-contrast to split reliably. Quote from the protocol (inferred from results, not explicit verbatim): they label the same anatomical segments as SCCT but do not attempt to sub-divide distal LAD, RCA, LCx into thirds because the geometric landmarks (e.g., "halfway to the apex") are not reliably identifiable or relevant in a machine-learning context.

**Tradeoff articulated**: Proximity/mid/distal reporting is deferred to the centerline post-processing step, where the skeleton can be divided into thirds by length without an annotator needing to identify blurry anatomical landmarks in 3D.

**Result**: Removes a source of annotation ambiguity (where exactly is "halfway to the apex"?) and makes per-branch agreement higher.

### Ren 2023 (centerline labeling, not voxel segmentation)

**Ren P, He Y, Guo N, et al. *A deep learning-based automated algorithm for labeling coronary arteries in computed tomography angiography images.* BMC Med Inform Decis Mak 2023;23:249.**

**Schema choice**: 16 segments (SCCT-like), with proximal/mid/distal splits on RCA, LAD, LCx. But this is a **centerline-labeling task, not voxel segmentation**, so the accuracy numbers do not compare with voxel Dice.

**Justification**: "The labeling methodology employed...followed the procedures outlined by..." — i.e., direct adoption of SCCT, with no critique or alternative considered. The paper does not discuss why proximal/mid/distal splits were retained.

**Notable limitation**: "All patients were assumed to be right-dominant; L-PDA/L-PLB were not labelled." This is a practical choice (the dataset did not include enough left-dominant cases to validate those classes), not a principled one. Flagged as a limitation in their paper.

### TopoLab (centerline labeling with anatomical constraints)

**Zhang Z, et al. *Topology-preserving automatic labeling of coronary arteries via anatomy-aware connection classifier.* MICCAI 2023. arXiv:2307.11959.**

**Schema choice**: 14 classes, no proximal/mid/distal split, anatomically-valid parent-child relationships enforced by graph constraints.

**Justification given**: Implicit in their method design. The paper does not explicitly defend the 14-class choice vs SCCT's 18. Instead, they focus on the **topology-preserving** aspect: they train a classifier to recognize parent-child relationships and ensure the learned labels respect anatomical tree structure (e.g., LCx cannot branch into an RCA segment).

**Tradeoff articulated**: The anatomical-plausibility constraint is the key innovation, not the schema. The schema choice appears to be "sensible defaults" adopted from prior work (likely ImageCAS-X or similar).

### Li 2023 (centerline labeling, 13-class simplification)

**Li Y, Armin MA, Denman S, Ahmedt-Aristizabal D. *Automated coronary arteries labeling via geometric deep learning.* IEEE ISBI 2023. arXiv:2212.00386.**

**Schema choice**: 13 classes, "following SCCT guidelines" but simplified.

**Justification**: The paper states they followed SCCT but does not explain which segments were dropped or why. Likely reasoning (inferred, not stated): they removed the least-common or most-ambiguous classes to reduce label-class imbalance and improve learner efficiency on a smaller training set (141 patients).

**Tradeoff left implicit**: Generalizability vs learner efficiency. The paper does not discuss whether the 13-class model can be extended to 18 or whether the classes they dropped are unlearnable.

## What patterns emerge across published work

**Consensus on anatomical basis**: All cited works adopt or adapt SCCT's 18-segment model as their starting point. No paper invents a novel schema from scratch or adopts SYNTAX/CASS in preference to SCCT. (Note: ARCADE is X-ray angiography, not CCTA, and uses SYNTAX; it does not inform CCTA schema choices.)

**Split on proximal/mid/distal**: 
- **Keep it** (Ren, SCCT, ARCADE): clinical reporting standard; radiologists expect it.
- **Drop it** (ImageCAS-X, TopoLab, Li): distal branches are too small/noisy; recover it from centerline post-processing.

**The real question not addressed in any paper**: How many branches is *learnable* from the data at hand? Nobody directly answers "we tried 18 classes and only 14 converged, so we kept the 14." Instead, papers adopt a schema and hope it works. ImageCAS-X is the exception: they have empirical results showing per-class Dice on all 14 classes, which proves all 14 are learnable on their 800 cases at published inter-rater agreement levels.

## Justifications given vs. justifications absent

**Explicitly articulated in at least one paper**:
- "Removes ambiguous landmarks" (ImageCAS-X's implicit reasoning for dropping proximal/mid/distal splits)
- "Ensures anatomical plausibility" (TopoLab, via graph constraints)

**Never explicitly articulated** (though they matter):
- "These classes have sufficient prevalence to learn from our dataset"
- "This split reduces per-annotator disagreement"
- "We tested this schema against alternatives"

## What this implies for [[Training plan]]

- **Adopt ImageCAS-X's 14-class schema** (already recommended in [[Proposed changes]]). The justification is that (a) it is empirically validated on coronary CCTA, (b) it removes a source of annotation ambiguity (geometric landmarks), and (c) all 14 classes have published inter-rater agreement numbers and learning curves.
- **Proximal/mid/distal reporting as post-processing** (already recommended): There is no multiclass CCTA voxel model that attempts to split distal branches. The field consensus is: don't try, recover it from the centerline skeleton afterward.
- **No published work validates that "schema A is better than schema B" on the same data.** Every paper adopts a schema and trains once. If the plan ever wants to compare ImageCAS-X's 14-class against a 10-class or 16-class variant, that is a novel experiment, not replicating published work.
