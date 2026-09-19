---
aliases: [Class schema proposed changes]
tags: [research, class-schema, decision-record, proposal]
status: proposal
updated: 2026-09-19
---

# Proposed changes (class schema)

Edits to [[Training plan]] proposed by the class-schema research in this folder.
Nothing here is decided; the plan changes only when someone accepts an item.
Anything the plan loses as a result belongs in [[Plan status]].

Scope: class schema and coronary anatomical labelling conventions only. Drafts
on other topics, written before the research was split between agents, are in
`Handover/` for the agents that own those topics. They are not proposals from
this folder.

## 1. Close "Class schema": adopt the ImageCAS-X 14-class schema

Evidence: [[Class schema options]].

Proposed text for a new decided section of the plan:

> **Class schema: ImageCAS-X, 14 classes + background.** LM, LAD, LCx, D1, D2,
> OM1, OM2, IM, RCA, R-PDA, R-PLA, L-PDA, L-PLA, Other (D3/D4/OM3/OM4). No
> proximal/mid/distal split; those are reported from the centerline afterwards.
> Why: it is the SCCT 18-segment model with only the landmark-based cuts
> removed, it is the only published voxel-level multiclass schema on ImageCAS,
> and labels for 800 of our 1000 cases already exist in it (Bransby et al.,
> arXiv:2608.30404, 2026). Dominance, side-branch minimum size, extra branches
> and carina ownership follow that paper's protocol (see the note).

## 2. The multiclass model no longer waits for our annotators

Evidence: [[Class schema options]] (the existence and licence of ImageCAS-X
labels). The consequences for splits and annotation are for the agents that own
those topics.

If the ImageCAS-X labels import cleanly, §3 step 2 ("Multiclass model … once
annotated cases flow") becomes "Multiclass model on the ImageCAS-X labels as
soon as the binary run has validated the chain".

Pre-condition: the download succeeds; the dataset licence (stated CC BY 4.0 in
the paper; the repository's code licence is MIT) is confirmed on the label host;
a 20-case spot check passes.

## 2b. Report a merged view alongside the 14-class view

Evidence: [[Class schema options]] ("Why not the simplified 4-class schema"),
[[Variant and absent branches]].

Fourteen classes can be merged to four (or to a Hampe-style 12) at evaluation
time; four can never be split into fourteen. So the plan should say that results
are reported at **three granularities from the same model**: 14-class,
Hampe-style merged (L-PDA → LCx, L-PLA → OM), and 4-class trunks. This costs
nothing, widens comparability, and separates "cannot find the vessel" from
"cannot name the vessel".

## 2c. Derived-dominance check as a cohort-level sanity test

Evidence: [[Variant and absent branches]].

Dominance is not a label; it is which of R-PDA/R-PLA/L-PDA/L-PLA are non-empty.
Predicted dominance over a held-out set should land near the published
prevalence (ImageCAS-X's own 800 scans: 91.1 % right, 5.1 % left, 3.8 %
co-dominant). A large deviation is a cheap early warning that the rare classes
have collapsed.

## 3. Labelling is done on named centerlines, not painted voxels

Evidence: [[Class schema options]], "Written policies in ImageCAS-X".

Carina ownership in ImageCAS-X is not a painted boundary. Segment names live on
the centerline and each lumen voxel takes the name of its nearest centerline
point. Adopting the schema means adopting that construction, so the annotation
app's per-branch step should edit centerline segment names. (How the annotation
workflow is organised around this belongs to the annotation-protocol owner.)
