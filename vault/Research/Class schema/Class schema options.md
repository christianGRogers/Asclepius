---
aliases: [CLASS-SCHEMA, Class schema, Coronary class schema]
tags: [research, coronary, class-schema, annotation, literature]
status: draft
updated: 2026-09-19
---

# Class schema options

The central open question in [[Training plan]]: how many coronary vessels are
their own class, and the written policy for bifurcation ownership, absent
branches and dominance-dependent PDA/PLV. This note records what the published
schemas are and what they decided, with the evidence attached.

**Headline finding.** A multiclass label set for our exact cohort now exists:
**ImageCAS-X** (Bransby et al., arXiv 2026) gives per-branch voxel labels for
800 of the 1000 ImageCAS scans under CC BY 4.0, in a 14-class SCCT-derived
schema. That changes the question from "which schema do we invent" to "do we
adopt theirs" (recommendation: yes; see the end of this note). It also bears on
the annotation plan; see [[Annotation protocol evidence]].

Two companion notes carry the detail: [[Clinical segment models compared]] (the
AHA / CASS / SYNTAX / SCCT reporting models and where they disagree) and
[[Variant and absent branches]] (prevalence of the ramus intermedius,
dominance-dependent PDA/PLA, and what each work did about classes that are
sometimes absent). Proposals are in [[Proposed changes]].

## Sources actually read

| Short name | Citation | What it is |
|---|---|---|
| SCCT 2014 | Leipsic J, Abbara S, Achenbach S, et al. *SCCT guidelines for the interpretation and reporting of coronary CT angiography.* J Cardiovasc Comput Tomogr 2014;8:342–358. doi:10.1016/j.jcct.2014.07.003 | The reporting standard. Read in full from the SCCT-hosted PDF: §5.3, Fig. 1, Table 5, Appendix 1. |
| ImageCAS-X | Bransby KM, Øksnebjerg E, Kjær K, Kirkeby J, El Youssef Y, Jiménez A, Pedersson PR, de Knegt MC, Kofoed KF, Paulsen RR. *ImageCAS-X: a dataset and benchmark for coronary artery segmentation and centerline extraction in coronary CT angiography.* arXiv:2608.30404, 2026 (preprint, under review). Repo: github.com/MathildeBS1/ImageCAS-X | Per-branch voxel labels + centerlines + meshes on 800 ImageCAS scans. Read via the arXiv HTML. |
| Hampe 2024 | Hampe N, van Velzen SGM, Wolterink JM, Collet C, Henriques JPS, Planken N, Išgum I. *Graph neural networks for automatic extraction and labeling of the coronary artery tree in CT angiography.* J Med Imaging 2024;11(3):034001. doi:10.1117/1.JMI.11.3.034001 | Centerline labelling, 10 classes. Read on PMC (PMC11095121). |
| Ren 2023 | Ren P, He Y, Guo N, et al. *A deep learning-based automated algorithm for labeling coronary arteries in computed tomography angiography images.* BMC Med Inform Decis Mak 2023;23:249. doi:10.1186/s12911-023-02332-y | Labelling, 16 segments. Read on PMC (PMC10626726). |
| CPR-GCN | Yang H, Zhen X, Chi Y, Zhang L, Hua X. *CPR-GCN: Conditional partial-residual graph convolutional network in automated anatomical labeling of coronary arteries.* CVPR 2020. arXiv:2003.08560 | Abstract only read; class list not obtained. Cited for scale (511 subjects), nothing else. |
| Prada Mancilla 2026 | Prada Mancilla WA, Díaz K, Ortiz F. *Coronary dominance on coronary CT angiography: prevalence and potential implications for electrocardiographic correlation.* J Clin Med 2026;15(13):5258. doi:10.3390/jcm15135258 | Dominance prevalence. Read on PMC. |
| Li 2023 | Li Y, Armin MA, Denman S, Ahmedt-Aristizabal D. *Automated coronary arteries labeling via geometric deep learning.* IEEE ISBI 2023. arXiv:2212.00386 | 13 SCCT-based classes, 141 patients. Read via arXiv HTML. |
| TopoLab | Zhang Z, Zhao Z, Wang D, Zhao S, Liu Y, Liu J, Wang L. *Topology-preserving automatic labeling of coronary arteries via anatomy-aware connection classifier.* MICCAI 2023. arXiv:2307.11959 | 14 classes; orCaScore (72 CTA) + in-house 1200 CTA. Read via arXiv HTML; per-class results are in supplementary material I could not open. |
| ARCADE | Popov M, et al. *Dataset for automatic region-based coronary artery disease diagnostics using X-ray angiography images.* Sci Data 2024;11:20. doi:10.1038/s41597-023-02871-z | 25 SYNTAX regions, X-ray angiography. Read on PMC (PMC10764944). |

Hampe, Ren and CPR-GCN are **centerline-labelling** works (they name segments
of an extracted tree), not voxel segmenters. Their schemas are relevant; their
accuracy numbers are not comparable with voxel Dice.

## The reference standard: SCCT 18-segment model

SCCT 2014 §5.3 adopts the 1975 AHA segmentation (Austen et al.) "with minimal
alterations", and adds two segments to it: "a left posterolateral branch is
identified as segment 18, and a ramus intermedius branch has been added as
segment 17." Table 4 lists "Use of SCCT axial coronary segmentation model" as
*recommended* in a report. Table 5 gives the CASS 28-segment model as an
optional alternative.

Appendix 1 (verbatim definitions, abbreviated):

| # | Segment | Boundary as defined by SCCT |
|---|---|---|
| 1 | pRCA | Ostium of RCA to one-half the distance to the acute margin of the heart |
| 2 | mRCA | End of proximal RCA to the acute margin of the heart |
| 3 | dRCA | End of mid RCA to origin of the PDA |
| 4 | R-PDA | PDA from RCA |
| 5 | LM | Ostium of LM to bifurcation of LAD and LCx |
| 6 | pLAD | End of LM to the first large septal or D1 (>1.5 mm), whichever is most proximal |
| 7 | mLAD | End of proximal LAD to one-half the distance to the apex |
| 8 | dLAD | End of mid LAD to end of LAD |
| 9 | D1 | First diagonal |
| 10 | D2 | Second diagonal |
| 11 | pLCx | End of LM to the origin of OM1 |
| 12 | OM1 | First OM traversing the lateral wall of the LV |
| 13 | LCx (mid + distal) | In the AV groove, distal to OM1, to the end of the vessel or the origin of the L-PDA |
| 14 | OM2 | Second marginal |
| 15 | L-PDA | PDA from LCx |
| 16 | R-PLB | PLB from RCA |
| 17 | RI | Vessel from the LM between LAD and LCx *in case of a trifurcation* |
| 18 | L-PLB | PLB from LCx |

Footnote: "Additional nomenclature may be added, for example, D3, R-PDA2 …"

Two things matter for us:

1. **Dominance is encoded by having separate segments per origin**
   (4 vs 15, 16 vs 18). A right-dominant heart simply has no 15 or 18.
   There is no "PDA" class whose parent varies.
2. **Several proximal/mid/distal cuts are not at bifurcations.** The pRCA/mRCA
   cut is half-way to the acute margin; mRCA/dRCA is *at* the acute margin;
   mLAD/dLAD is half-way to the apex. These are geometric landmarks an
   annotator must estimate in 3D, not topological events. They are the least
   reproducible boundaries in the model, and they are recoverable after the
   fact from a centerline and a few landmarks.

## What published multiclass works actually use

| Work | Task | # classes | Proximal/mid/distal split? | Dominance policy | Ramus / absent branches |
|---|---|---|---|---|---|
| SCCT 2014 | reporting | 18 | yes (RCA, LAD; LCx p vs mid+distal) | separate R-/L- segments | RI = segment 17, only if trifurcation |
| **ImageCAS-X 2026** | **voxel segmentation, ImageCAS** | **14 + background** | **no** | separate R-PDA, R-PLA, L-PDA, L-PLA | IM is its own class; D3/D4/OM3/OM4 → "Other" |
| Hampe 2024 | centerline labelling | 10 | no | "L-PDA segments were labeled as LCX, and the L-PLB segments were labeled as OM" | RI not a class |
| Ren 2023 | centerline labelling | 16 | yes (RCA, LAD, LCx) | all patients right-dominant; L-PDA/L-PLB **not labelled** | RI is a class |
| Li 2023 | centerline labelling | 13, "following SCCT guidelines" | no | L-PDA and L-PLB are classes | Ramus ("R") is a class; authors flag R, L-PDA and R-PDA as the hard ones |
| TopoLab 2023 | centerline labelling | 14 | not stated in the text I read | not stated | RI is a class; dominance not discussed |
| SYNTAX 2005 | invasive scoring | 16 + lettered sub-branches | yes (RCA, LAD) | segment 15 L-PDA "when present"; 14 "may be absent or a division of obtuse marginal branch" | RI = segment 12, "belongs to the circumflex territory" |
| ARCADE 2024 | X-ray instance segmentation | 25 (SYNTAX) | yes | not stated | follows SYNTAX numbering |

ImageCAS-X class IDs (their Supplementary Table 4): 1 LM, 2 LAD, 3 LCx, 4 D1,
5 D2, 6 OM1, 7 OM2, 8 IM (intermediate), 9 RCA, 10 R-PDA, 11 R-PLA, 12 L-PDA,
13 L-PLA, 14 Other (D3, D4, OM3, OM4).

### ImageCAS itself named a class set — and then shipped merged masks

Worth knowing, because it tells us what the original radiologists had in mind.
ImageCAS §3 says the labelled coronary artery includes "the left main coronary
artery, left anterior descending coronary artery, left circumflex coronary
artery, right coronary artery, diagonal 1, diagonal 2, diagonal 3, obtuse
marginal branch 1, obtuse marginal branch 2, obtuse marginal branch 3, ramus
intermedius, posterior descending arteries, acute marginal 1 and other blood
vessels according to the AHA naming convention". But Fig. 1's caption states:
"Note that subclasses of coronary arteries are not further individually
labeled", and the limitations section lists it as a known gap: "Third, no
detailed labels is provided. That is, subclasses of coronary artery including
left main coronary artery, left anterior descending coronary artery, etc. are
not separated."

That named set is close to ImageCAS-X's 14 classes, with two differences worth
noting: ImageCAS names a third diagonal and a third obtuse marginal as classes
(ImageCAS-X puts D3/D4/OM3/OM4 into "Other"), and it names **acute marginal 1**,
which ImageCAS-X does not have as a class at all but Hampe 2024 does ("AM",
F1 0.84, its third-best class). AM is the one plausible 15th class; see
[[Variant and absent branches]] for why I would still leave it out.

ImageCAS-X states its lineage explicitly. Verbatim: "Current guidelines
recommend that pathological findings be reported per vessel segment"; each
branch segment "was manually classified according to the 18-segment naming
convention"; and the tracing was checked as "ensuring the final coronary tree
conformed to the established 18-segment model". So the 14 classes are the SCCT
18-segment model with the proximal/mid/distal subdivisions collapsed, not an
independent invention.

Their stated reason for dropping the proximal/mid/distal split (verbatim):
"We do not distinguish between proximal, mid and distal segments of the left
anterior descending (LAD) and left circumflex (LCx) because they depend on side
branch positions which are highly variable."

### Written policies in ImageCAS-X (the only voxel-level multiclass protocol found)

- **Dominance** — "Right coronary dominance is defined by the presence of
  posterior descending artery (PDA) and posterior lateral artery (PLA) from the
  right coronary artery (RCA), and left dominance is defined by a PDA from the
  left circumflex artery (LCx). Co-dominance by the presence of PDAs or PLAs from
  both RCA and LCx, or the presence of a PDA from the RCA without a PLA from the
  RCA." Dominance is therefore an *output* of labelling, not an input to it.
- **Main vs side branch at a bifurcation** — "determined by the direction and
  course of the artery rather than by its size."
- **Minimum branch** — side branches were not traced "where the connection to
  the parent vessel was unclear, where the branch could not be clearly
  delineated, or where the diameter at the most distal point was <1 mm."
- **Extra branches** — additional D and OM branches labelled "Other" "if they
  were at least as large as the first or second branches or >1.8 mm in diameter
  at the most proximal end."
- **Absent branches** — handled implicitly: a class with no voxels in a case is
  absent. Per-segment presence counts in their 160-case test set show how often
  (next section).
- **Voxel ownership at the carina itself** — settled by construction, not by a
  written rule: segment names live on the *centerline*, and "Segment names were
  propagated to every lumen voxel in the segmentation mask by assigning each
  voxel the name of its nearest centerline point." So a carina voxel belongs to
  whichever branch's centerline is closer: a Voronoi split of the lumen by
  labelled centerline. Annotators label centerline segments; they never paint a
  boundary in the lumen.

## How rare each class is, and how hard for humans

ImageCAS-X re-annotated its 160 test cases by a second analyst. Per-segment
inter-observer results (their Table 1; *n* = test cases in which the segment is
present, as I read the column; "Agreement" appears to be presence agreement, %):

| Segment | n / 160 | Agreement % | DSC % | clDice % |
|---|---|---|---|---|
| LM | 155 | 96.9 | 91.9 ± 13.7 | 95.6 ± 17.6 |
| LAD | 160 | 100.0 | 92.3 ± 6.7 | 96.4 ± 7.9 |
| LCx | 159 | 99.4 | 84.8 ± 19.8 | 87.3 ± 23.0 |
| D1 | 155 | 96.9 | 79.9 ± 28.7 | 85.0 ± 30.2 |
| D2 | 91 | 89.4 | 82.9 ± 24.3 | 88.1 ± 25.3 |
| OM1 | 132 | 94.4 | 74.1 ± 32.3 | 79.8 ± 34.2 |
| OM2 | 46 | 87.5 | 77.7 ± 29.1 | 83.7 ± 30.6 |
| IM | 43 | 89.4 | 80.6 ± 24.5 | 89.2 ± 25.2 |
| RCA | 160 | 100.0 | 95.3 ± 5.0 | 98.2 ± 6.0 |
| R-PDA | 150 | 98.8 | 82.6 ± 21.9 | 88.4 ± 22.3 |
| R-PLA | 147 | 96.2 | 83.6 ± 18.6 | 89.4 ± 18.4 |
| L-PDA | 8 | 100.0 | 75.1 ± 29.0 | 81.6 ± 31.8 |
| L-PLA | 9 | 96.9 | 70.9 ± 27.2 | 77.7 ± 30.3 |
| Other | 14 | 88.8 | 81.3 ± 17.0 | 86.7 ± 16.2 |
| All (binary) | 160 | 95.3 | 92.8 ± 3.1 | 95.4 ± 3.6 |

Dataset for every number above: ImageCAS-X test set, 160 ImageCAS scans,
two trained analysts. Read the numbers with the caveat that I extracted this
table through an HTML-to-text conversion; the headline rows were checked
twice and matched.

Dominance in the 800 ImageCAS-X scans: "729 (91.1%) right dominant, 41 (5.1%)
left dominant, and 30 (3.8%) co-dominant". Independent CCTA cohort for
comparison: 677 patients, right 89.7 %, left 8.0 %, co-dominance 2.3 %
(Prada Mancilla 2026, dominance defined by PDA origin).

What this says:

- **L-PDA and L-PLA are very rare classes** (8 and 9 of 160 test cases) and the
  hardest for humans (DSC 75 / 71). In a 1000-case cohort, expect on the order
  of 50–90 cases containing them. Of all our classes they are the most likely
  to starve under default sampling (see [[Training plan]] §5).
- **IM is present in roughly a quarter of cases** (43/160). A model must learn
  to output *nothing* for it in the other three quarters; per-class Dice is
  undefined in those cases and must be handled explicitly in evaluation (see
  [[Acceptance thresholds]]).
- **Branch classes sit 10–20 Dice points below the trunks for humans.** The
  whole-tree 92.8 % hides this entirely. A per-branch acceptance threshold has
  to be set per class, not globally.

## The difficulty ordering is the same across tasks, modalities and decades

A useful independent check, because it is not a segmentation study at all.
Choudhary G, Atalay MK, Ritter N, Shin V, Grand D, Pearson C, Kirchner RM, Wu WC.
*Interobserver reliability in the assessment of coronary stenoses by
multidetector computed tomography.* J Comput Assist Tomogr 2011;35(1):126–134.
doi:10.1097/RCT.0b013e3181f80bef. **Abstract only** — the full text is paywalled
and the browser/UofT proxy was unavailable; the numbers below are from the
abstract, which reports them directly.

Five readers, 40 CCTA studies, stenosis severity graded per segment on a
5-point scale, ICC computed per segment:

> "The reliability was good to moderate in the right coronary artery, left main
> artery, left anterior descending artery and branches, and the proximal
> circumflex (ICC: 0.44-0.75) but fair to poor for the posterior descending
> artery, the posterolateral branch, the obtuse marginal branches, and the
> distal circumflex (ICC: 0.15-0.39). The ICC correlated with the reference
> diameter."

The split — trunks and proximal LCx reliable, PDA / posterolateral / OM /
distal LCx unreliable — is the same ordering as ImageCAS-X's per-segment
inter-observer Dice (RCA 95.3 … OM1 74.1, L-PLA 70.9) and the same as Hampe
2024's per-class F1 (RCA 0.90 … R-PDA 0.69, S 0.54). And the stated cause is
the same: **ICC tracks vessel diameter**, just as ImageCAS-X reports
"local DSC score increases with lumen diameter (ρ = +0.89, p<0.001)".

That consistency matters for the schema decision in two ways. It says the hard
classes are hard for intrinsic anatomical reasons rather than because of any
one annotation protocol, so no schema will make OM2 or L-PLA easy. And it says
the difficulty is predictable from diameter, so per-class expectations can be
set in advance instead of discovered after training.

## Centerline-labelling results, for difficulty ranking only

Not comparable to voxel Dice; cited for the *ordering* of classes.

- Hampe 2024 (104 patients, two Dutch/Belgian hospitals, Siemens), per-class
  labelling F1: RCA 0.90, LAD 0.86, AM 0.84, LCX 0.74, OM 0.74, D 0.73,
  LM 0.70, R-PLB 0.69, R-PDA 0.69, S 0.54; overall 0.74.
- Ren 2023 (157 patients, Beijing Friendship Hospital, all right-dominant):
  lowest per-class F1 was RI at 79.3 %; R-PLB accuracy 79.0 %, D2 88.5 %,
  RI 84.7 %; trunks at or near 100 %.

The ordering agrees with ImageCAS-X's human variability: trunks easy, RCA
easiest, small side branches and the posterolateral/PDA territory hardest.

## Options

| Option | Classes | For | Against |
|---|---|---|---|
| A. 4-class trunks (LM/LAD/LCx/RCA; branches folded into parent) | 4 + bg | Highest agreement; matches `plan-v1`'s old set | Discards the per-branch labelling that is the project's contribution; folding D/OM into parents makes parent Dice meaningless for branch detection |
| **B. ImageCAS-X 14-class** | 14 + bg | Published, SCCT-derived, **labels already exist for 800 of our 1000 cases**, direct comparability, written policies for dominance/extra branches | Two very rare classes (L-PDA, L-PLA); "Other" is a mixed bag |
| C. B with L-PDA→LCx, L-PLA→OM2/Other (Hampe-style fold) | 12 + bg | Removes the two starving classes | Breaks compatibility with ImageCAS-X labels; the fold loses the dominance signal that the label map otherwise encodes for free |
| D. Full SCCT 18 with proximal/mid/distal | 18 + bg | Clinical reporting granularity | Landmark cuts (acute margin, half-way to apex) are non-topological and low-reproducibility; ImageCAS-X rejected them for this reason; derivable from a centerline afterwards |

### Why not the simplified 4-class schema (option A)

It is the tempting option: the trunks are the classes everyone agrees on
(ImageCAS-X inter-observer DSC 91.9–95.3 for LM/LAD/RCA; Choudhary's readers
reliable on RCA, LM, LAD and proximal LCx and unreliable on everything distal),
and it is what `plan-v1` used. The published 3-class point of comparison is Kim
et al. 2025 (LAD, LCX, RCA on CCTA; nnU-Net Dice 0.794 internal / 0.741
external), which shows the coarse task is not trivially solved either.

The decisive argument against it is one-directional information:

- **14 classes can be merged to 4 at any time; 4 cannot be split into 14.**
  A 14-class model can be scored, reported and shipped at trunk granularity by
  relabelling its output — so option A is available *for free* as an evaluation
  view of option B, exactly as the Hampe-style fold is (option C).
- Folding D1/D2/OM1/OM2/IM into their parents does not simplify the anatomy, it
  hides it: a model that misses D1 entirely still scores well on "LAD" if D1's
  voxels were counted as LAD all along. Branch detection, the metric this
  project cares about, stops existing.
- It abandons the project's stated contribution. [[Training plan]] §3 is
  explicit that "The contribution is the per-branch labelling."

Worth noting how little is available off the shelf here: **TotalSegmentator**,
the most widely used general CT segmentation tool, ships coronary arteries as a
**single binary class**. Verified directly from its source:
`totalsegmentator/map_to_binary.py` in wasserth/TotalSegmentator defines task
`coronary_arteries` (509) with exactly one label, `coronary_arteries`, plus a
`coronary_arteries_LEGACY` (507) with the same single label. There is no
per-branch coronary schema in general tooling to inherit; ImageCAS-X is the only
one on our cohort. (The TotalSegmentator *paper* — Wasserthal et al., Radiology:
Artificial Intelligence 2023 — I did not open; the claim above rests on the code,
not the paper, and the publication details come from a search listing.)

## Recommendation

**Adopt option B, the ImageCAS-X 14-class schema, as the schema of record.**

Why:

1. **Labels on our exact cohort exist.** If the release holds up (verify the
   download and licence before relying on it), 800 cases arrive labelled,
   which is more than the annotation team could produce in any realistic time.
   Every deviation from their schema makes those labels unusable without
   relabelling. See [[Proposed changes]].
2. **It is the SCCT model with only the low-reproducibility cuts removed.**
   Dominance handling (separate R-/L- PDA and PLA) is exactly SCCT's segments
   4/15/16/18. Proximal/mid/distal can be recovered at report time from a
   centerline plus landmarks, which is the "graph reasoning downstream" that
   [[Training plan]] §4 already allows.
3. **Comparability.** It is the only published voxel-level multiclass schema on
   ImageCAS I found. Any result we publish in it is directly comparable.
4. **The rare classes are a sampling problem, not a schema problem.** Folding
   L-PDA/L-PLA (option C) is available as an *evaluation-time* merge — report
   both the 14-class and a merged view — without touching the labels.

Policies to write into the annotation protocol, taken from ImageCAS-X unless
marked:

- Dominance is derived from which vessel gives the PDA/PLA; annotators label
  what they see, the dominance field is computed.
- Main vs side branch at a bifurcation: by direction and course, not size.
- Do not trace a side branch whose most distal diameter is < 1 mm or whose
  connection to its parent is unclear.
- D3/D4/OM3/OM4 go to "Other" if at least as large as D1/D2/OM1/OM2 or
  > 1.8 mm at the origin; smaller ones are not labelled.
- IM only when the LM trifurcates (SCCT definition of segment 17).
- Carina ownership: **label the centerline, then assign each lumen voxel the
  label of its nearest centerline point** (ImageCAS-X's construction). This
  replaces a painted boundary with a reproducible rule, and it means our
  annotation app should expose centerline-segment labelling, not voxel painting,
  for the per-branch step.

## Still unverified

- That the ImageCAS-X data is actually downloadable today. The repository
  README points to Kaggle for the volumes and to a project website for the
  labels, with a layout of `segmentations/<scan_id>.coronary.nii.gz`,
  `centerlines/*.vtk`, `surfaces/*.vtk` and `filelist/{train,val,test,exclude}.txt`.
  I did not download anything. The repository's `LICENSE` is **MIT** (that
  covers the code); the paper states the *dataset* is CC BY 4.0. Confirm on the
  label host before import.
- Whether their annotation tool (CoronaryExplorer) produced labels that pass our
  own QA. Spot-check 20 cases before bulk import.

## What this implies for [[Training plan]]

- **Close "Class schema"** with the ImageCAS-X 14-class schema (+ background).
  Reason: SCCT-derived, published on our cohort, labels already exist.
- The multiclass model no longer has to wait for our annotators: it can train
  on 800 ImageCAS-X cases as soon as the binary run has validated the chain.
  The annotation team's role shifts from *producing* the training set to
  QA, the 200 excluded cases (if usable at all), and an independent test set.
- Class-balanced sampling (§5) moves from "worth trying" to necessary:
  L-PDA/L-PLA appear in ~5 % of cases.
- Proximal/mid/distal reporting becomes a post-processing step on the
  centerline, not a class.

Concrete edits are proposed in [[Proposed changes]].
