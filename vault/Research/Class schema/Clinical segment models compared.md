---
aliases: [Segment models, SCCT vs SYNTAX, Reporting segment models]
tags: [research, class-schema, coronary, guidelines, literature]
status: draft
updated: 2026-09-19
---

# Clinical segment models compared

The clinical nomenclature our class schema has to answer to. Four models are in
active use, they disagree about the ramus intermedius and about how dominance is
encoded, and only one of them was designed to be drawn on an axial CT volume.
Companion note: [[Class schema options]], which covers what deep-learning works
actually chose.

## The four models

| Model | Segments | Primary use | Read? |
|---|---|---|---|
| AHA (Austen 1975) | 15 | the ancestor of all the others | **No** — see "Not accessed" |
| CASS | 28 | optional alternative in SCCT reporting | via SCCT Table 5 |
| SYNTAX (Sianos 2005) | 16, with lettered sub-branches | PCI/CABG decision scoring, invasive angiography | Yes |
| **SCCT (Leipsic 2014)** | **18** | **CCTA interpretation and reporting** | **Yes, in full** |

Citations:

- Leipsic J, Abbara S, Achenbach S, Cury R, Earls JP, Mancini GBJ, Nieman K,
  Pontone G, Raff GL. *SCCT guidelines for the interpretation and reporting of
  coronary CT angiography: a report of the Society of Cardiovascular Computed
  Tomography Guidelines Committee.* J Cardiovasc Comput Tomogr 2014;8(5):342–358.
  doi:10.1016/j.jcct.2014.07.003. Read in full (SCCT-hosted PDF).
- Sianos G, Morel MA, Kappetein AP, et al. *The SYNTAX Score: an angiographic
  tool grading the complexity of coronary artery disease.* EuroIntervention
  2005;1(2):219–227. Read the segment definitions on the EuroIntervention site.
- CASS 28-segment model: reproduced as Table 5 of SCCT 2014, citing
  *Myocardial infarction and mortality in the Coronary Artery Surgery Study
  (CASS) randomized trial.* N Engl J Med 1984;310:750–758. I read SCCT's Table 5,
  not the NEJM paper.
- Popov M, et al. *Dataset for automatic region-based coronary artery disease
  diagnostics using X-ray angiography images.* Sci Data 2024;11:20.
  doi:10.1038/s41597-023-02871-z. Read on PMC (PMC10764944). The one public
  dataset built on the SYNTAX schema.

## Where they disagree, and why it matters to us

### 1. The ramus intermedius

- **SCCT**: its own segment, number 17, defined as a "Vessel originating from
  the left main between the LAD and LCx **in case of a trifurcation**".
- **SYNTAX**: segment 12, "Intermediate/anterolateral artery: Branch from
  trifurcating left main other than proximal LAD or LCX. **It belongs to the
  circumflex territory.**"

So SYNTAX gives the RI its own number but assigns it to the LCx *territory* for
scoring, while SCCT treats it as a peer of LAD and LCx. Both agree on the
anatomical trigger (a trifurcating left main), which is the part an annotator
needs. A schema that has an IM class is compatible with both; a schema that
folds RI into LCx is compatible with SYNTAX's territory logic but loses the
trifurcation information.

### 2. Dominance

Neither model has a dominance *flag*. Both encode dominance structurally, by
which numbered segments exist:

- **SCCT**: segment 4 = "PDA from RCA", 15 = "PDA from LCx", 16 = "PLB from
  RCA", 18 = "PLB from LCx". A right-dominant tree simply has no 15 or 18. The
  definition of segment 13 (mid + distal LCx) even ends "…to the end of the
  vessel or origin of the L-PDA (left PDA)".
- **SYNTAX**: segment 4 is the PDA, segment 15 is "Posterior descending: Most
  distal part of dominant left circumflex **when present**", segment 14 is
  "Left posterolateral: Running to the posterolateral surface of the left
  ventricle. **May be absent or a division of obtuse marginal branch**",
  segment 16 is "Posterolateral branch from RCA…distal to the crux".

The consequence for a voxel model: **dominance is not a label, it is a pattern
of which classes are non-empty.** That is exactly what the ImageCAS-X protocol
does (see [[Class schema options]]) and it is the reason a schema with separate
R-/L- PDA and PLA classes is worth its two rare classes: dominance comes out for
free and can be validated against the ~90 % right / 5–8 % left / 2–4 %
co-dominant prevalence reported in the literature.

SYNTAX also shows the *clinical* weight of getting this right: "In a right
dominant system, the right coronary artery (RCA) supplies approximately 16% and
the left coronary artery (LCA) 84% of the flow to the left ventricle (LV)",
whereas "In a left dominant system the RCA does not contribute to the blood
supply of the ventricle." The scoring weights change with dominance.

Note SYNTAX segment 14's alternative reading — the left posterolateral "may be
… a division of obtuse marginal branch". That is the same ambiguity Hampe 2024
resolved by folding L-PLB into OM (see [[Class schema options]]), and it is a
real anatomical ambiguity, not a mistake by either group.

### 3. Where one segment ends and the next begins

This is the decisive difference for an annotation protocol. SCCT's Appendix 1
(quoted in full in [[Class schema options]]) defines boundaries by a mix of two
kinds of landmark:

- **Topological** (a bifurcation): LM ends at the LAD/LCx bifurcation;
  pLAD ends at the first large septal or D1 > 1.5 mm; pLCx ends at the origin of
  OM1; dRCA ends at the origin of the PDA.
- **Geometric** (a point in space with no branch there): pRCA/mRCA at "one-half
  the distance to the acute margin of heart"; mRCA/dRCA at the acute margin;
  mLAD/dLAD at "one-half the distance to the apex".

SYNTAX has the same structure: segment 1 is "From the ostium to one half the
distance to the acute margin", segment 6 is "Proximal to and including first
major septal branch", segment 7 is "LAD immediately distal to origin of first
septal branch".

The geometric cuts are the problem. There is nothing in the image at the
half-way point; two annotators will place it differently, and the disagreement
lands in the middle of a large, high-Dice trunk where it costs many voxels.
ImageCAS-X dropped these cuts explicitly: "We do not distinguish between
proximal, mid and distal segments of the left anterior descending (LAD) and left
circumflex (LCx) because they depend on side branch positions which are highly
variable."

**They can be recovered later.** Given a labelled centerline and the two
landmarks (acute margin, apex), the proximal/mid/distal cuts are arithmetic. So
they belong in a reporting post-process, not in the class schema.

### 4. Minimum vessel size

- SYNTAX: lesions are scored in "vessels >1.5 mm diameter"; a bifurcation side
  branch counts at "a minimal diameter of 1.5mm".
- SCCT: the pLAD/mLAD boundary uses a septal or diagonal ">1.5 mm in size".
- ImageCAS-X (a labelling protocol, not a guideline): do not trace a branch
  whose most distal diameter is < 1 mm; an extra D/OM becomes "Other" if
  > 1.8 mm at its origin.

1.5 mm is the clinical convention and 1–1.8 mm is what the one per-branch
labelling protocol used. At ~0.35 mm voxels, 1.5 mm is 4–5 voxels across: right
at the limit the plan already identifies as the reason for native spacing.

## The SYNTAX schema as a segmentation target: the one data point

ARCADE (Popov et al., Sci Data 2024) is the only public dataset I found built on
the SYNTAX model: 1500 X-ray coronary angiography images annotated into
"25 different regions based on the SYNTAX Score", plus 1500 more for stenosis.
Annotation was "originally annotated by one expert" and then "cross-validated by
two doctors with the highest expertise", with inter-rater Dice reported in the
range 0.73–0.90.

Their baseline vessel-segmentation result was **Dice 0.49** (YOLOv8, original
images). That is not directly comparable to CCTA work — 2D projection X-ray has
vessel overlap and foreshortening that a 3D volume does not — but it is a
caution: a 25-class SYNTAX-style schema on a modality where the classes are
genuinely visible still produced a sub-0.5 baseline, and the inter-rater floor
of 0.73 shows the humans were not certain either.

## What this means for the schema

1. **Follow SCCT, not SYNTAX, for naming.** SCCT is the CCTA reporting standard,
   and SCCT 2014 itself says its model is "adapted for coronary CTA … an axially
   based version of this standard model". SYNTAX was built for invasive
   angiography and its weights, not for labelling voxels.
2. **Keep dominance structural.** Separate R-PDA, R-PLA, L-PDA, L-PLA classes
   (SCCT segments 4, 16, 15, 18). Do not add a dominance class or a dominance
   input; derive it.
3. **Keep IM as a class**, triggered by a trifurcating LM, per both models.
4. **Drop the geometric proximal/mid/distal cuts from the class schema** and
   recover them in reporting. Both guidelines define them; neither defines them
   in a way two annotators can reproduce on a volume.
5. **Adopt 1.5 mm as the reporting-relevant branch threshold** and ~1 mm as the
   annotation floor, matching SYNTAX/SCCT and ImageCAS-X respectively.

All five are consistent with the ImageCAS-X 14-class schema recommended in
[[Class schema options]]; this note is the clinical-nomenclature justification
for that recommendation.

## Not accessed

- **Austen WG, et al.** *A reporting system on patients evaluated for coronary
  artery disease. Report of the Ad Hoc Committee for Grading of Coronary Artery
  Disease, Council on Cardiovascular Surgery, American Heart Association.*
  Circulation 1975;51(4 Suppl):5–40. The original 15-segment model.
  ahajournals.org returned HTTP 403 to a non-browser fetch, and the Chrome
  extension / UofT proxy was unavailable in this session. Everything above about
  the AHA model is taken from SCCT 2014, which states its model is "derived and
  adjusted from the report by Austen et al."
- **CAD-RADS 2.0** (Cury RC, Leipsic J, Abbara S, et al., JACC Cardiovasc
  Imaging 2022;15(11):1974–2001, doi:10.1016/j.jcmg.2022.07.002; also Radiol
  Cardiothorac Imaging, doi:10.1148/ryct.220183). Both publisher sites returned
  403 and it is not in PMC. Relevant because the segment involvement score
  counts diseased segments and therefore depends on the segment model; whether
  it mandates the 18-segment model is **unverified**.
- **SCCT 2021 Expert Consensus Document** (Narula J, et al., J Cardiovasc Comput
  Tomogr 2021;15(3):192–217, doi:10.1016/j.jcct.2020.11.001, PMC8713482). Not
  yet checked for any update to the segment model; the fetch was interrupted.
- The SYNTAX definitions were read from the EuroIntervention article page rather
  than the publisher PDF; page numbers (219–227) come from a secondary listing.

## What this implies for [[Training plan]]

Nothing on its own — it is the justification layer under [[Class schema options]].
The concrete proposal is item 1 of [[Proposed changes]].
