---
aliases: [Carina ownership, Bifurcation boundary, Voxel ownership at branch points]
tags: [research, class-schema, coronary, bifurcation, literature]
status: draft
updated: 2026-09-19
---

# Bifurcation ownership and carina voxel assignment

[[Class schema options]] already states the recommended rule for our project
(label the centerline, assign each lumen voxel to its nearest labelled
centerline point — ImageCAS-X's construction) and [[Clinical segment models
compared]] already covers which boundaries in SCCT/SYNTAX are topological
(at a bifurcation) versus geometric (a landmark in space). This note collects
the evidence for *why* the centerline-nearest-point rule is the right
mechanism, what alternatives exist in the literature, and how disagreement at
a bifurcation is actually measured once it happens.

## The question, precisely

At a bifurcation, the parent vessel's lumen and the daughter branch's lumen
share a physical carina region — voxels that are, at the resolution of a CT
scan, plausibly part of either vessel. A class schema needs an answer to "does
this voxel belong to the parent or the daughter" that (a) two annotators will
reproduce, and (b) is well-defined even where the anatomy itself does not
present a sharp geometric edge (the tunica media of two confluent tubes is
continuous, not seamed).

## Three mechanisms found in the literature, and which we should use

### 1. Nearest-labelled-centerline-point (ImageCAS-X's construction) — recommended

Already the project's recommended rule, from [[Class schema options]]:
ImageCAS-X's own wording, "segment names were propagated to every lumen voxel
in the segmentation mask by assigning each voxel the name of its nearest
centerline point." This is, formally, a **Voronoi partition of the lumen mask
by the labelled centerline points** — every voxel's owner is whichever
centerline segment is geometrically closest, which is deterministic given a
labelled centerline and requires no separate boundary-drawing act by the
annotator. A general description of the same mechanism, independent of
ImageCAS-X, turned up in this session's search of the vessel-labelling
literature (search-summary level, not a specific paper read in full — flagged
accordingly): "voxel-level labeling can be mapped to centerline-level
labeling based on the highest overlap rate between voxel-level segmentation
and the dilated centerline," which is the same idea run in the opposite
direction (centerline label inferred from voxel overlap, rather than voxel
label assigned from centerline) — evidence that nearest-centerline assignment
is a recognised, reusable construction in the field, not an ImageCAS-X-specific
invention.

**Why this is the right choice for us, restated with the mechanism made
explicit**: it turns an annotator's job from "paint a boundary in 3D at a
carina, a task with no sharp visual edge to trace" into "click points down
each vessel's centreline and assign each a branch name," a task with a clear,
checkable action (did every centerline point get a label) and no freehand
boundary-drawing step at all. It is also exactly what `docs/SEGQUEUE.md`
already describes the extension doing structurally — *Draw tube* places
points down a centreline and a radius — so the labelling tool this project has
already built is a natural fit for centerline-first, not voxel-painted,
per-branch labels. This was already the recommendation in [[Class schema
options]]; the addition here is that it is a load-bearing reason the
project's own annotation tooling (not just the published schema) should be
built around centerlines for the multiclass step, which is a note for
whoever owns the SegQueue extension, not a decision this folder makes.

### 2. A fixed geometric rule at the ostium of the daughter branch

The alternative implicit in SCCT/SYNTAX's *text* definitions (already covered
in [[Clinical segment models compared]]) is a fixed anatomical rule stated in
prose — "pLAD ends at the first large septal or D1 >1.5mm, whichever is most
proximal" — which places the boundary at the *daughter's origin*, i.e. the
daughter branch starts exactly where it visibly leaves the parent, and the
parent's own class continues past that point unchanged (the LAD does not stop
being "LAD" because a diagonal has left it). This is a different mechanic
from nearest-centerline assignment: under SCCT's rule, the *carina itself*
stays with the parent trunk by convention, whereas under nearest-centerline
assignment, whichever of the two centerlines is geometrically closer to a
given carina voxel wins, which could assign some carina voxels to the
daughter if its centerline curves close to the wall on that side. Neither
mechanism is validated against the other in anything I read — this is a real,
unresolved difference between "how radiologists are told to define the
boundary in prose" and "how ImageCAS-X actually computed it," and I did not
find a paper that measured whether the two produce materially different voxel
sets. **Flagged as open**: if voxel-level comparability with SCCT reporting
ever matters (e.g. computing a segment's total plaque volume for CAD-RADS-
style reporting), the two conventions should be checked against each other on
a handful of cases before assuming they agree.

### 3. Measuring disagreement *at* a bifurcation once it happens: weighted kappa that discounts the boundary

**Föllmer B, Tsogias S, Biavati F, et al. *Automated segment-level coronary
artery calcium scoring on non-contrast CT: a multi-task deep-learning
approach.* Insights Imaging 2024;15:250. doi:10.1186/s13244-024-01827-0.**
Already introduced in [[Sizing the overlap set and arbitrating disagreements]]
in the annotation folder; the relevant mechanism is restated here because it
answers a class-schema-adjacent question: **how do you score a boundary call
without treating a 1-voxel-off carina disagreement as equal to a wrong branch
name?** Their answer: a **weighted Cohen's kappa** giving a misclassification
between *adjoining* segments (e.g. proximal vs mid RCA) a weight of 0.5, and
any other misclassification a weight of 1.0. Reported result: model-vs-
reference weighted kappa 0.808, matching human-observer weighted kappa 0.809
almost exactly, on a 13-segment SCCT-derived schema, 1514 patients.

This is not a labelling-time mechanism (it does not tell an annotator what to
do at a carina) — it is an *evaluation-time* mechanism, and it is the correct
complement to the nearest-centerline labelling rule: label with the
deterministic Voronoi rule (mechanism 1), then, when scoring agreement or
model accuracy, discount confusion between anatomically adjacent classes
(parent/daughter pairs, or the LM/proximal-LAD/proximal-LCx triad) rather than
scoring every misclassification equally. This is squarely an evaluation-metric
decision, not a class-schema one — flagged to the metrics/acceptance-
thresholds owner rather than adopted here (see [[Handoffs]]).

## What published centerline-labelling works actually do, for corroboration

Already surveyed in [[Class schema options]] (Hampe 2024, Ren 2023, CPR-GCN,
TopoLab): every one of these is a **centerline-labelling** task, not a
voxel-painting task — the annotator or algorithm assigns a name to a
centerline point or segment, never a 3D lumen boundary. That is independent
convergent evidence, across four separate groups and datasets, that the field
has already settled on centerlines as the right *object* to label, even where
(as in Hampe, Ren, TopoLab) the end product is a classification of an
already-extracted centerline rather than a fresh segmentation. ImageCAS-X is
simply the one member of this group that also propagates the centerline
labels down into a full voxel mask, which is the extra step our project
specifically needs (we want a `3d_fullres` voxel segmenter, not a centerline
classifier).

## What this implies for [[Training plan]]

- No change to the schema recommendation already in [[Class schema options]]
  and [[Proposed changes]] — this note supports item 3 there (centerline-first
  labelling) with additional mechanism detail and a note that the SCCT-prose
  convention and the ImageCAS-X Voronoi convention are not verified to agree
  voxel-for-voxel at a carina.
- **Flag to the metrics/acceptance-thresholds owner** (via [[Handoffs]]):
  Föllmer et al.'s adjacent-segment-discounted weighted kappa is a ready-made
  evaluation mechanism for scoring bifurcation-boundary disagreement, whether
  or not the plan ever adopts a proximal/mid/distal split.
- **Open item, not resolved here**: whether SCCT's "daughter branch owns its
  own ostium, parent continues past it" convention and ImageCAS-X's
  nearest-centerline Voronoi convention produce the same voxel assignment at a
  carina. Worth a small check (a handful of cases, by hand) before any voxel-
  level comparison to SCCT-style reporting is claimed.
