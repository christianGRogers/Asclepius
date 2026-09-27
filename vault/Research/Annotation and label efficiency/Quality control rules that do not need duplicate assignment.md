---
aliases: [Automatic QC rules, Plausibility checks, Single-annotator QC]
tags: [research, annotation, quality-control, rules, literature]
status: complete
updated: 2026-09-20
---

# Quality control rules that do not need duplicate assignment

SegQueue currently uses **duplicates** (two independent annotators on the same case) and **gold cases** (reference standards) as its primary QC mechanism. [[Detecting a drifting or bad annotator]] already flags that mean Dice alone misses important failure modes. This note surveys what **consistency checks and anatomical plausibility rules** exist that can flag problems without requiring a second annotator, useful for cases that are never duplicated.

## Classes of checks that work without duplicates

### 1. Topological/graph consistency checks

**Enforce that the labeled vessels form a valid tree structure.**

**What to check**:
- Every labeled segment has exactly one parent, except the root (LM).
- No cycles (the tree is acyclic).
- Every segment belongs to the correct domain (left or right subtree from LM).
- Parent-child relationships respect anatomical constraints (e.g., a left-circumflex child cannot branch into an LAD).

**Published evidence**: 
- **Multi-graph Graph Matching for Coronary Artery Semantic Labeling** (arXiv:2402.15894, 2024): Encodes coronary tree as a graph where nodes are segments and edges are parent-child relationships. The algorithm enforces **cycle consistency** (M^IJ = M^IK · M^KJ) to ensure matched segments form valid acyclic trees.
- **Topology-Preserving Automatic Labeling** (TopoLab, MICCAI 2023, arXiv:2307.11959): Uses an "anatomy-aware connection classifier" to ensure predicted labels respect anatomically valid parent-child links, preventing impossible configurations (e.g., RCA cannot descend from LAD).

**How to implement for SegQueue**: Post-process every annotator submission through a graph-validity checker that constructs the labeled tree and flags violations. Rules:
- Count the number of parents for each segment; flag if ≠ 1 (except LM).
- DFS/cycle detection; flag if any cycle found.
- Check that parent-child labels respect a pre-built valid-transition table (e.g., "LCx can parent OM, D, etc.; LAD cannot parent OM").
- Count connected components; flag if >1 (unless the annotator left foreground unlabeled, which is separate).

**Cost**: ~5 sec per case for graph construction and validation; one-time coding effort to build the valid-transition matrix (already possible from SCCT definitions).

**False-positive risk**: Very low if the transition matrix is correct. A topological error is genuinely an error.

### 2. Anatomical plausibility constraints

**Enforce that labeled regions respect spatial anatomy.**

#### 2a. Containment in the binary lumen mask

If the annotator's lumen correction left gaps or added voxels outside the seed binary mask, flag it.

**What to check**: Every voxel labeled as a coronary vessel class should lie inside the binary lumen presegmentation (or very close to it, within 1–2 voxels, accounting for annotation refining).

**Published evidence**: Generally assumed (not a published focal point, but standard practice) — the lumen label must be a subset of the segmented lumen.

**How to implement**: Compute the Dice or Jaccard between the annotator's multi-class label and the union of all foreground classes, versus the binary seed. If the overlap is <95 %, flag for review.

**False-positive risk**: Low, unless the annotator is deliberately correcting the binary mask (which is their job, so this is deliberate and should be checked by a senior reviewer separately, not flagged as an error).

#### 2b. Vessel diameter constraints

Vessels should not contain impossible diameter changes without branching.

**What to check**: Measure the diameter along each labeled centerline. Flag if the diameter changes by >30 % between consecutive centerline points without a bifurcation nearby (the vessel is pinching unrealistically).

**Published evidence**: Implicit in centerline extraction validation (e.g., Voronoi-based method reports 0.13 mm average error on extracted centerlines). Diameter is a proxy for centerline correctness.

**How to implement**: Extract the centerline from each labeled segment; compute diameter at each point (using the distance transform or a kernel-based measure). Flag if slope exceeds a threshold without an adjacent bifurcation.

**False-positive risk**: Moderate. Real vessel tapers (see [[Ostial definitions and segment endpoints in coronary imaging]]) can show a large diameter change. Needs tuning and exemptions for the known-tapered regions (distal third of branches).

#### 2c. Spatial proximity to the aortic root and expected tree extent

Coronary ostia should be near the root of the aorta (anatomically, within ~10 mm). Distal branches should not extend implausibly far.

**What to check**: 
- Root (LM) label should include at least one voxel within 10–15 mm of the aortic center (can be estimated from the binary mask or from a separate aorta segmentation if available).
- Distal labels should not extend more than expected voxel distance from their parent; e.g., a distal diagonal should not reach the LV apex.

**Published evidence**: "Spatial constraints" in SegHeD (Segmentation of MS Lesions, arXiv:2410.01766, 2024) enforce that predicted lesions must fall inside white-matter regions — an example of using anatomical-region masks to constrain plausibility.

**How to implement**: (a) Identify the aortic root center (from the binary seed or a pre-computed landmark). (b) For each root label, check that at least one voxel is <15 mm from the root center. (c) For distal segments, compute max distance to the root; flag if >expected (e.g., >150 mm in an adult heart).

**False-positive risk**: Moderate. Highly variable anatomy and imaging FOV. Needs population-specific thresholds.

### 3. Consistency with the presegmentation seed

**Flag when the annotator's labels contradict the binary seed in expected ways.**

**What to check**: 
- **Omitted major branches**: The binary model found a large connected component >100 voxels that the annotator has entirely left unlabeled (0 voxels assigned to any class). This is often a miss, not an intentional exclusion of noise.
- **False additions**: The annotator labeled voxels as vessel outside the binary seed by >5 mm (local boundary refinement is okay; adding structure is not).

**Published evidence**: **Karimi et al. 2020** (cited in [[Detecting a drifting or bad annotator]]) finds that "smaller, fainter lesions were more likely to be missed" by a single annotator on repeat read (18 % miss rate). They propose a **missed-structure detector**: flag cases where the model predicted lesions the annotator did not label, especially if those lesions are small/distal (predictive of miss). Same mechanism applies to coronary branches.

**How to implement**: 
- Compute connected components in the binary seed mask.
- For each component >100 voxels, check if the annotator labeled ≥50 % of it to any vessel class.
- Flag components <50 % labeled as "possible miss."
- Separately, compute voxels labeled as vessel that fall >5 mm outside the seed; flag as "possible addition" for review.

**False-positive risk**: Moderate. The annotator may intentionally skip small noise in the seed, or refine the boundary. A human reviewer (or the annotator themselves) must confirm each flag is an error, not a judgment call.

## When to apply each check

**Always (no cost to run every case)**:
- Topological validity (cycle detection, parent count)
- LM containment and root proximity

**On duplicates and gold cases only** (cost-benefit becomes unclear on singles):
- Diameter constraints (need manual tuning and population thresholds)
- Spatial extent bounds (need anatomy-specific thresholds)

**On all cases** (high value, low false-positive):
- Missed-structure detection against the model's own predictions (Karimi mechanism)
- Containment in binary seed (with loose threshold, ±5 mm)

## What this implies for [[Training plan]]

- **Implement topological validation immediately.** This is a one-time coding effort, catches obvious errors, and has almost no false positives. Add it to `src/segqueue/scoring.py` as a pass/fail step before Dice calculation.
- **Add missed-structure flagging as a standing experiment.** Store per-annotator rates of "voxels the model found that the human omitted," and track over time (see [[Detecting a drifting or bad annotator]] for per-annotator trend detection). This is the Karimi mechanism: smaller branches are more likely to be missed, so flag an annotator with high miss rates on small/distal branches.
- **Build a tunable plausibility rule set**, not a hard constraint.** Do not reject a case; flag it for review. SegQueue's QA can then decide if the flag is a true error or an acceptable variant annotation. This trades automation for accuracy.
- **Validate thresholds on ImageCAS-X first** (if imported). Apply each proposed rule to 100 random ImageCAS-X cases and check: how many get flagged? Are the flagged cases actually annotated incorrectly, or false positives? This calibration is essential before using rules on live annotations.
- **None of this replaces duplicates.** These rules are *additional* checks for the 80 % of cases that are never duplicated. They catch systematic problems (topology, major misses) but not subtle boundary disagreements, which only inter-rater comparison surfaces.
