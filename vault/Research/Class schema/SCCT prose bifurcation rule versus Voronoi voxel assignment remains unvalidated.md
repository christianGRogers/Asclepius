---
aliases: [Bifurcation rule validation, Prose vs Voronoi comparison, SCCT vs ImageCAS-X]
tags: [research, class-schema, bifurcation, literature, unresolved]
status: complete
updated: 2026-09-20
---

# SCCT prose bifurcation rule versus Voronoi voxel assignment remains unvalidated

The existing note [[Bifurcation ownership and carina voxel assignment]] flags one unresolved question: **do SCCT's prose boundary rules ("a daughter branch owns its own ostium, parent continues past it") and ImageCAS-X's nearest-centerline Voronoi rule produce the same voxel assignment at a bifurcation?** This note confirms: nobody has published a comparison. If voxel-level comparability with SCCT reporting ever matters, this gap must be closed by the project itself.

## SCCT's prose rule for bifurcation ownership

The SCCT 2014 reporting standard defines segment boundaries in prose, using anatomical landmarks. For bifurcations, the rule is structural: **a bifurcation belongs to the parent by default; the daughter branch begins exactly where it visibly originates (its ostium)**. Examples from the 18-segment model:

- Segment 6 (pLAD): "End of LM to the first large septal or D1 >1.5 mm, whichever is most proximal"
  - This says the parent (LAD) ends where the daughter (D1) *starts* — at the ostium.
- Segment 13 (mLCx): "In the AV groove, distal to OM1, to the end of the vessel or the origin of the L-PDA"
  - Again, the parent ends where the child originates.

The implicit mechanism: **the carina (the region where parent and daughter lumens meet) stays with the parent, by convention.**

## ImageCAS-X's Voronoi rule for bifurcation ownership

[[Bifurcation ownership and carina voxel assignment]] already summarizes this: ImageCAS-X assigns each lumen voxel to the name of its **nearest labelled centerline point**. This is a Voronoi partition of the lumen mask by centerline points. Consequence at a bifurcation:

- If the parent centerline and daughter centerline are labeled differently
- And a carina voxel is equidistant from (or closer to) the daughter's centerline point
- Then that carina voxel becomes part of the daughter class, not the parent

This is **different from the prose rule** because the Voronoi rule asks "which centerline is geometrically closer," not "what does the anatomical boundary say." At an angle branching off at a shallow angle, some carina voxels might lie closer to the daughter centerline than to the parent, causing Voronoi to assign them to the daughter where SCCT would keep them with the parent.

## Whether the two conventions agree: no published comparison exists

A thorough search of the literature (PubMed Central, arXiv, Europe PMC, Semantic Scholar) found **no published study comparing voxel-level output of these two rules on actual coronary data**. The closest evidence is:

1. **ImageCAS-X itself**: The paper states their protocol follows SCCT guidelines for segment definitions but does not claim pixel-for-pixel identity with SCCT voxel assignments. They report inter-annotator agreement numbers (see [[How well two annotators agree on per-branch coronary labels]]) but not a direct comparison against SCCT-defined boundaries.

2. **General vessel-labeling literature**: One search result mentioned (in abstract/search summary form, not a full paper read) that "voxel-level labeling can be mapped to centerline-level labeling based on the highest overlap rate," which is the reverse direction (inferring centerline labels from voxel overlap), not the comparison we need.

3. **Clinical radiology standards**: SCCT guidelines are written in prose for human radiologists reading reports. They are not formalized as voxel-assignment rules. No radiologist paper formalizes "the carina belongs to the parent" as a testable voxel rule.

## What this means for the project

**This is not a blocking gap.** Here's why:

1. **Taper tapering is more important than carina geometry.** The distal branches taper away and become sub-resolution; the uncertainty there (where exactly does the branch end?) is larger than any sub-voxel disagreement about which centerline owns a carina voxel. Fixing the taper rule matters more than resolving this one.

2. **The difference is small in voxel count.** The carina region is a few voxels wide — often 2–3 voxels in a 0.35 mm voxel-spaced volume. Any disagreement between the two rules affects a handful of voxels per branch point. The branch volumes are hundreds or thousands of voxels; this is noise at the level of Dice.

3. **Consistency matters more than ground truth.** The reason to pick one rule is to be predictable, not to match some hidden ground truth. ImageCAS-X's Voronoi rule is deterministic: given a labeled centerline, the voxel assignment is fully determined. SCCT's prose rule requires interpretation. Voronoi is the better choice on consistency grounds alone.

4. **A spot-check is cheap.** If [[Training plan]] or a future phase ever needs to compare this project's per-voxel predictions to SCCT segment volumes for clinical reporting, a hand-checked 5–10 case comparison (both rules applied to the same images) takes an afternoon and would reveal if the rules diverge materially. Before claiming voxel-level comparability with SCCT, do that spot-check.

## What this implies for [[Training plan]]

- No change to the recommendation to use ImageCAS-X's nearest-centerline Voronoi rule (already in [[Bifurcation ownership and carina voxel assignment]] and [[Proposed changes]]).
- If future work ever requires claiming voxel-level comparability with SCCT segment volumes (e.g., for CAD-RADS plaque reporting), flag this as a pre-condition: do a spot-check on 5–10 cases with both rules and document whether the disagreement is clinically negligible.
- This is a **future risk** (flagged, not a blocker). The current project's evaluation uses per-class Dice, clDice, and branch detection — none of which depend on whether a single carina voxel goes to the parent or daughter.
