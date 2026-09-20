---
aliases: [Ostium definition, Segment endpoints, Tapered vessel resolution]
tags: [research, class-schema, coronary, anatomy, literature]
status: complete
updated: 2026-09-20
---

# Ostial definitions and segment endpoints in coronary imaging

Where does a coronary vessel end when it tapers below imaging resolution? The SCCT 2014 reporting standard leaves this implicit. This note collects what the anatomy and imaging literature say about ostia and tapering, and identifies what must be defined for our annotation protocol.

## Definition: ostium

The **ostium** of a coronary artery is its point of origin from the aorta, formally at the aortic wall. In coronary CT angiography (CCTA), an ostium is visible as the vessel's entry point into the field of view. For anatomical labelling, the ostium marks where a segment *begins*, not where it ends.

**Clinical importance**: Anomalous coronary ostia (abnormal locations or slit-like orifices) are a known arrhythmia risk and are defined clinically as an ostium positioned more than 5 mm above the sinotubular junction. This distinction is purely diagnostic (is this an anomaly?) and does not affect normal segment labeling.

## The taper problem: where does a segment end when the vessel vanishes below resolution?

A coronary artery does not end with a sharp cut. Instead, it tapers — the lumen diameter progressively narrows as the vessel branches and its flow diminishes. This is universal in coronary anatomy: main trunks measure **4.5 ± 0.5 mm** in diameter, while distal left anterior descending branches measure **1.9 ± 0.4 mm**. CCTA imaging resolution is approximately **1.5 mm**, meaning smaller distal branches approach or fall below the resolution limit.

### What this means for labeling

The tapered distal segments — those narrowest branches that imaging resolves only as a faint tube or blur — present an annotator with an ambiguous boundary: "how much of the taper must be visible before I label it as part of this segment?" The answer matters because:

1. **Inter-annotator agreement depends on a rule.** Two annotators will mark different endpoints on a sub-resolution taper unless told explicitly when to stop. (Existing evidence: ImageCAS-X's per-class DSC spreads are largest on the distal branches; see [[How well two annotators agree on per-branch coronary labels]].)

2. **A rule affects what the model can learn.** If the training protocol marks "visible to 1 mm diameter" and the test protocol marks "visible to 1.5 mm," the model will appear to make false-negative errors on cases where annotators happen to differ.

3. **A rule is recoverable after segmentation.** Because distal diameter is recoverable from a centerline (the 3D skeleton of the lumen), the taper boundary can be moved downstream at reporting time without changing the labeled data — a leverage point for experiments.

### Published guidance (what exists and what doesn't)

**SCCT 2014 reporting standard**: defines endpoints for the proximal/mid/distal cuts (e.g., "pRCA ends at the acute margin") but does not address the sub-resolution taper. The word "distal" appears in segment definitions (e.g., "dLAD from end of mid LAD to end of LAD") but "end of LAD" is left as "to the end of the vessel," without a rule for disappearance.

**ImageCAS-X (Bransby et al., arXiv:2608.30404, 2026, preprint)**: labels 800 coronary segmentations at 14 classes. The paper states their protocol follows SCCT guidelines but does not explicitly state a rule for sub-resolution tapers. The resulting labeled dataset shows this ambiguity in the data: distal branches have large inter-annotator disagreement. Candidate rule (not stated as explicit policy): the manual correcters stopped labeling when the vessel became sub-resolution in the view they were working with — a practical if not standardized choice.

**No published agreement** on a bright-line rule for taper endpoints exists in the literature I accessed. The most common implicit approach is "label as far as you can see," which trades reproducibility for the virtue of including all visible structures.

## What this implies for [[Training plan]]

- **A taper rule is needed for the annotation protocol**, alongside other segment-boundary policies. Recommend one of:
  1. **Diameter-based** (e.g., "label the vessel until it narrows below 1.0 mm diameter, measured from the centerline"), which is objective and recoverable but harsh on low-contrast distal branches.
  2. **Visibility-based** (e.g., "label the portion that is clearly delineated as lumen in the plane of view; stop when confidence drops to 50%"), which is fuzzy but matches clinical reading. Requires exemplar images in the annotator guideline.
  3. **Centerline-following** (e.g., "follow the automated centerline extraction; label it if the skeleton continues"), which defers the boundary decision to the centerline algorithm and is reproducible but outsources a judgment call.
  4. **Adopt ImageCAS-X's implicit rule** (stop when sub-resolution), which trades standardization for consistency with the existing 800-case dataset if imported.

- **This is lower-stakes than the bifurcation rule** (which vessel owns the carina voxels) because tapering is not a topological ambiguity — the branch is unambiguously child of its parent — only a visibility one. Small mistakes here barely affect training (the taper region is tiny voxel-wise) compared to a systematic carina-ownership error.

- **Recommend a 5–10 case spot-check** once the rule is drafted: two annotators working from guidelines, checking agreement on taper endpoints in cases with obvious small distal branches. If agreement is >95% Dice, the rule is clear enough to proceed; if <90%, the guideline needs exemplar images or rewording.
