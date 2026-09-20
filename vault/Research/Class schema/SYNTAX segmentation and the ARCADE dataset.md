---
aliases: [SYNTAX score segments, ARCADE dataset, SYNTAX-based labelling]
tags: [research, class-schema, coronary, syntax, arcade, literature]
status: draft
updated: 2026-09-19
---

# SYNTAX segmentation and the ARCADE dataset

[[Clinical segment models compared]] already covers the SYNTAX 16-segment
model's definitions and where it disagrees with SCCT. This note goes one level
deeper on the two things that note left thin: what SYNTAX's segmentation is
*for* (a scoring weight, not a naming convention, which changes what "correct"
means), and ARCADE, the one public dataset built on it — what it actually
ships, what its baseline achieved, and whether any of it transfers to CCTA
voxel work.

## SYNTAX is a weighted lesion score, and the segment model exists to carry the weights

**Sianos G, Morel MA, Kappetein AP, et al. *The SYNTAX Score: an angiographic
tool grading the complexity of coronary artery disease.* EuroIntervention
2005;1(2):219–227.** Already read for [[Clinical segment models compared]];
revisited here for what the segments are *doing* in the score, not just their
boundaries.

Every SYNTAX segment carries a fixed weighting factor before any lesion is
even considered — the LM is weighted highest, distal small branches lowest —
and the total score sums (number of lesions × segment weight × diameter-
reduction and lesion-complexity multipliers) across the whole tree. The
segment identity is therefore not primarily an anatomical label to a
SYNTAX-trained reader; it is *which weight this lesion gets multiplied by*.
This matters for whether SYNTAX's segment definitions are a good target for a
voxel classifier: they were authored to be reproducible enough for a
weighting scheme to be defensible in an invasive-angiography reading room, not
to be a voxel-accurate 3D boundary. [[Clinical segment models compared]]
already shows SYNTAX shares SCCT's problem of geometric (non-topological) cuts
for several segments (segment 1 at "one half the distance to the acute
margin," etc.) — the same argument against adopting those cuts as class
boundaries applies here without new evidence, restated for completeness.

## ARCADE: the public SYNTAX-schema dataset, and what its numbers actually mean

**Popov M, Amanturdieva A, Zhaksylyk N, et al. *Dataset for automatic
region-based coronary artery disease diagnostics using X-ray angiography
images.* Sci Data 2024;11:20. doi:10.1038/s41597-023-02871-z.** Read in full
on PMC (PMC10764944) for [[Clinical segment models compared]]; the numbers
below are drawn from that same full read, expanded here.

- **Modality: 2D X-ray coronary angiography (XCA), not CT.** This is the
  single most important fact about ARCADE for our purposes — it is a
  projection image with vessel overlap and foreshortening, not a 3D volume.
  Nothing about the segmentation *task difficulty* on ARCADE transfers
  quantitatively to CCTA; only the *class definitions* (which vessel gets
  which name and number) transfer, because those come from the SYNTAX
  document itself, not from the imaging modality.
- **Two independent tasks on two independent 1200-image sets**: "Syntax"
  (vessel region segmentation into named SYNTAX segments) and "Stenosis"
  (atherosclerotic-plaque region segmentation), each split 1000 train / 200
  validation, per Popov et al.'s own description, which I read directly.
- **25 segments.** The paper's own count, from the text I read directly:
  images are annotated into "25 different regions based on the SYNTAX Score."
  A grand-challenge task page for the same dataset (`arcade.grand-challenge.org`,
  fetched separately this session, not peer-reviewed) states class names
  follow "the Syntax Score methodology" without giving a count, and a
  secondary search-engine summary of unclear provenance claimed "26 different
  regions" and "6,180 masks across 25 segmentation classes" elsewhere on the
  same site. **I take 25 as authoritative** (it is the number in the
  peer-reviewed Scientific Data paper, which I read directly) and flag the
  "26" figure as an unverified discrepancy in secondary/challenge-site
  material, not a contradiction I could resolve — if ARCADE labels are ever
  imported or compared against, verify the class count against the actual
  released annotation files, not either number quoted here.
- **Annotation provenance**: "originally annotated by one expert" then
  "cross-validated by two doctors with the highest expertise," with inter-
  rater Dice reported in the range **0.73–0.90** — already cited in
  [[Clinical segment models compared]], repeated here because it is the only
  inter-rater figure in this whole research thread that comes from invasive
  angiography rather than CCTA, and it brackets the same 0.7–0.9 range CCTA
  studies report (ImageCAS-X 0.71–0.95 per branch, see [[How well two
  annotators agree on per-branch coronary labels]]) despite the very
  different imaging physics. That convergence is weak but real evidence that
  branch-identity disagreement is intrinsic to coronary anatomy's variability,
  not an artefact of CT partial-volume effects or XCA projection ambiguity
  specifically.
- **Baseline result: Dice 0.49** (YOLOv8, original images, already cited in
  [[Clinical segment models compared]]). Restated with the caveat sharpened:
  this is a segmentation-*and*-classification task into 25 fine-grained named
  regions on a 2D projection with vessel crossing and foreshortening — a
  much harder rendering of "classify this pixel into one of 25 vessel
  identities" than a 3D CCTA volume, where vessels do not visually overlap.
  **Do not read 0.49 as a difficulty benchmark for a 14-class 3D CCTA task**;
  read it only as confirmation that a 20-25-class SYNTAX-derived schema is
  hard even for the people who defined it, which is consistent with
  [[Class schema options]]'s recommendation to use the coarser (14-class,
  no proximal/mid/distal) ImageCAS-X schema instead of the full 18- or
  SYNTAX 16/25-segment models for voxel work.

## What ARCADE does and does not add to the class-schema decision

- It **confirms** SYNTAX's own numbering and naming (already used in
  [[Clinical segment models compared]] for the RI/dominance comparison), on an
  independent, publicly released, peer-reviewed dataset — useful as a
  cross-check that the SCCT/SYNTAX segment definitions this project has
  already adopted policies from are not being misread from a single source.
- It **does not** offer a 3D voxel-level annotation to import (unlike
  ImageCAS-X) — the images are 2D XCA frames, and even if labels were
  reprojected they would not carry 3D lumen geometry.
- It is the **only public evidence on how a full SYNTAX-granularity (~25
  class) schema performs as a segmentation target**, and that evidence
  (Dice 0.49 baseline, inter-rater 0.73–0.90) supports [[Class schema
  options]]'s existing recommendation against going that fine, rather than
  adding a new consideration.

## What this implies for [[Training plan]]

Nothing that changes the recommendation already made in [[Class schema
options]] (adopt ImageCAS-X's 14-class schema). This note's contribution is
evidentiary support, from an independent dataset and modality, for two claims
that recommendation already rests on: (1) SYNTAX/SCCT's finer geometric cuts
are not what a voxel classifier should target, and (2) branch-identity
disagreement at the 0.7–0.9 Dice / kappa level is a property of coronary
anatomy itself, observed across CT and X-ray, expert and cross-validated
annotation, not an artefact of any one project's protocol. See [[Proposed
changes]] for the standing recommendation this supports.
