---
aliases: [Public coronary CCTA datasets, ASOCA, CAT08, orCaScore, ARCADE, Dataset landscape]
tags: [research, coronary, dataset, benchmark, literature]
status: draft
updated: 2026-09-19
---

# Public coronary CCTA datasets

The wider public dataset landscape beyond ImageCAS/ImageCAS-X (covered in
[[State of the art on ImageCAS]]): what else exists, what each one actually
labels, who annotated it and how well they agreed, and its licence. Referenced
from [[State of the art on ImageCAS]] and [[Fold schemes and split ratios]].

**Short answer.** Nothing public rivals ImageCAS/ImageCAS-X in scale, and
nothing except ImageCAS-X ships **per-branch voxel** labels on CCTA. ASOCA is
the standard external-validation set (40 labelled CCTA cases, CC BY 4.0, with a
directly relevant number: its published inter-annotator Dice is **85.6 %**,
which is very likely the true source of the "inter-observer ≈ 0.856" figure
[[Research context]] and [[State of the art on ImageCAS]] could not trace — see
§4). CAT08 and orCaScore label different things (centerlines; calcium) and CAT08
is no longer reliably downloadable. ARCADE and CARDIAG are per-branch, but on
X-ray angiography, a different modality with vessel foreshortening and overlap
that CCTA does not have. No 2023–2026 release supersedes ImageCAS-X as the
per-branch CCTA benchmark.

## Sources actually read

- **ASOCA** — Gharleghi R, Adikari D, Ellenberger K, Ooi SY, Ellis C, Chen CM,
  Gao R, He Y, Hussain R, Lee CY, Li J, Li J, Liu Y, Ma X, Ma Z, Noga M, Punithakumar
  K, Sean Tan LW, Wei X, Xia B, Yang Y, Zhang C, Zhu H, Zhu J, Hayat M, Sowmya A,
  Beier S. *Automated segmentation of normal and diseased coronary arteries – The
  ASOCA challenge.* Comput Med Imaging Graph 2022;97:102049.
  doi:10.1016/j.compmedimag.2022.102049. Abstract/metadata read via PubMed;
  ScienceDirect full text not opened (see "Not accessed").
- **ASOCA data descriptor** — Gharleghi R, Chen N, Sowmya A, Beier S. *Annotated
  computed tomography coronary angiogram images and associated data of normal
  and diseased arteries.* Sci Data 2023;10:128. doi:10.1038/s41597-023-02016-2.
  Read in full on PMC (PMC10006074).
- **CAT08** — Schaap M, Metz CT, van Walsum T, et al. *Standardized evaluation
  methodology and reference database for evaluating coronary artery centerline
  extraction algorithms.* Med Image Anal 2009;13(5):701–714.
  doi:10.1016/j.media.2009.06.003. Not opened directly; details taken from a
  secondary source (Automated Coronary Artery Tracking with a Voronoi-Based 3D
  Centerline Extraction Algorithm, PMC10743762) that quotes the dataset
  composition and confirms the original host is currently unreachable — flagged
  as such, not independently verified against the original paper.
- **orCaScore** — Wolterink JM, Leiner T, de Vos BD, van Hamersvelt RW, Viergever
  MA, Išgum I. *An evaluation of automatic coronary artery calcium scoring
  methods with cardiac CT using the orCaScore framework.* Med Phys
  2016;43(5):2361–2373. Not opened directly (ResearchGate abstract page only);
  challenge scope read from the Grand Challenge site `orcascore.grand-challenge.org`.
- **ARCADE** — Popov M, Amanturdieva A, Zhaksylyk N, Alkanov A, Saniyazbekov A,
  Aimyshev T, Ismailov E, Bulegenov A, Kolesnikov A, Kulanbayeva A, Kuzhukeyev A,
  Sakhov O, Kalzhanov A, Temenov N, Fazli S. *Dataset for automatic region-based
  coronary artery disease diagnostics using X-ray angiography images.* Sci Data
  2024;11:20. doi:10.1038/s41597-023-02871-z. Read in full on PMC (PMC10764944).
- **CARDIAG** — Lau DB, Malinowski H, Szyjut J, Brzeski A, Dziubich T, Targoński
  R, Figatowski T, Zielińska N. *CARDIAG: A Dense Segment Classification
  Benchmark of Deep Learning Architectures for Coronary Angiography.*
  arXiv:2607.22139v1, 24 Jul 2026 — **preprint, not peer reviewed.** Read via
  arXiv HTML.
- **Cross-dataset generalisation on CCTA**: Khan U, Liatsis P. *Seg2RefineNet: a
  novel DL-based framework for 2D CCTA image-based segmentation and 3D
  volume-based refinement.* Sci Rep 2025;15:41096.
  doi:10.1038/s41598-025-24953-1. Read in full on PMC (PMC12635082). And Zhang S,
  Gharleghi R, Singh S, Shen C, Adikari D, Zhang M, Moses D, Vickers D, Sowmya A,
  Beier S. *Optimising Generalisable Deep Learning Models for CT Coronary
  Segmentation: A Multifactorial Evaluation.* J Imaging Inform Med
  2025;39(3):2680–2694. doi:10.1007/s10278-025-01677-2. Read in full on PMC
  (PMC13230296). Both are discussed in more depth in
  [[External validation and cross-dataset generalisation for coronary segmentation]].

Not accessed: ASOCA's own ScienceDirect full text (403 to non-browser fetch;
no browser/institutional-login tool was available in this session — see the
final report); orCaScore's Medical Physics paper in full (abstract/ResearchGate
listing only); CAT08's own Med Image Anal paper (details below are from a
paper that cites it, flagged inline).

## ASOCA — the standard second CCTA lumen benchmark

- **40 cases with ground truth**: 20 normal, 20 with obstructive coronary
  disease, each with voxel-wise lumen annotation, a centreline, and a lumen
  mesh; plus **20 further test cases (10 normal, 10 diseased) released without
  ground truth** for the original MICCAI 2020 challenge leaderboard. (Some
  secondary sources describe this as "40 training / 20 test" — that is the
  challenge-era split; the Scientific Data descriptor's headline number of
  labelled cases is 40.)
- **Acquisition**: retrospective ECG-gated 64-slice GE Lightspeed scanner,
  contrast (Omnipaque 350), end-diastolic phase saved. In-plane resolution
  0.3–0.4 mm, slice thickness 0.625 mm — coarser through-plane than ImageCAS's
  near-isotropic ~0.35 mm, and anisotropic rather than near-isotropic.
- **Label definition**: coronary lumen only (binary, not per-branch), "all
  coronary vessels with a diameter larger than 1 mm, representing 1–2 voxels."
  No sub-branch classes.
- **Annotation**: three independent experts segmented in 3D Slicer
  (thresholding + manual per-slice contour correction); final ground truth is
  **majority vote, at least two of three agreeing.**
- **Inter-annotator agreement (the number that matters most for us)**: mean
  DSC **85.6 % ± 7.7 %** (normal 87.4 %, diseased 83.9 %); HD95 **5.92 ± 7.3 mm**
  (normal 4.45 mm, diseased 7.38 mm). Source: Sci Data 2023 descriptor, PMC10006074.
- **Licence**: **CC BY 4.0** (the Scientific Data descriptor states this
  explicitly); access is via a request form through the UK Data Service
  (`reshare.ukdataservice.ac.uk/855916`), not an open download — a registration
  step, not a paywall.

### The 0.856 figure, traced

[[Research context]] and [[State of the art on ImageCAS]] both flag that
[[Training plan]]'s "inter-observer agreement ≈ 0.856" cannot be sourced from
either ImageCAS or ImageCAS-X. ASOCA's inter-annotator DSC of **85.6 % ± 7.7 %**
on binary lumen is a near-exact numeric match. This is circumstantial — no
citation trail connects the plan's figure to this specific paper, and 0.856 is
close enough to 85.6 % that it could equally be a transcription of the mean
"87.4/83.9" pooled figure, or an independent coincidence — but it is the only
published binary coronary inter-observer number in this literature search that
lands on 0.856 to three significant figures on the original ImageCAS masks or
any adjacent dataset. Recorded here as the most probable source, not a
confirmed one.

## CAT08 — centerlines, not voxels, and likely no longer downloadable

- MICCAI 2008 Coronary Artery Tracking challenge, evaluated through the
  "Rotterdam Coronary Artery Algorithm Evaluation Framework."
- **8 training CCTA scans with 32 manually labelled reference centerlines**
  (4 vessels per case: RCA, LAD, LCx, one large side branch), **24 test scans
  with 96 centerlines** extracted for scoring, for 128 total.
- **Label type: 1D centerlines with radius at each point, not a voxel mask.**
  It answers "did you find the vessel's path", not "did you get the lumen
  boundary right" — a fundamentally different task from ours.
- **Availability**: the original host (`coronary.bigr.nl/centerlines`) is
  reported as unreachable in a 2023-era paper (PMC10743762, read for this
  reason rather than as a primary CAT08 source). Treat CAT08 as **effectively
  retired** for new work; several 2010s centerline-extraction papers depend on
  it, but a 2026 project should not plan around downloading it. Licence:
  unknown, never independently verified.

## orCaScore — calcium scoring, a different clinical question entirely

- MICCAI 2014 Challenge on Automatic Coronary Calcium Scoring.
- **36 non-contrast, ECG-triggered CT scans** (18 GE Lightspeed VCT, 18 Toshiba
  Aquilion ONE), four academic hospitals in Belgium and the Netherlands.
- **Label type: calcified lesions** (location, coronary-artery assignment,
  per-patient Agatston-equivalent score, cardiovascular risk category) on
  **non-contrast** CT — no lumen, no contrast-enhanced vessel, not the same
  imaging protocol as ImageCAS/our data at all.
- Relevant to us only tangentially: calcium is the confound the
  [[Datasets and benchmarks/Public coronary CCTA datasets|generalisation
  literature]] below repeatedly names as the thing that breaks lumen
  segmentation (see §4). orCaScore itself is not a lumen-segmentation resource
  and should not be treated as a candidate training or validation set for this
  project.
- Licence and full case-level access: not verified (challenge appears closed to
  new registration as of August 2025 per the Grand Challenge page).

## ARCADE and CARDIAG — per-branch, but X-ray, not CCTA

Both are included because the task explicitly asks for per-branch/multiclass
releases; both are a **different modality** (2D X-ray coronary angiography,
not 3D CCTA) and are noted for schema comparison, not as training-data
candidates.

- **ARCADE** (Popov et al., Sci Data 2024): **3,000 X-ray frames** (1,500 for
  vessel "semantic" segmentation into **25 SYNTAX-derived segment classes**,
  1,500 for stenosis). Splits: 1,000 train / 200 public validation / 300 private
  test. **Six cardiologists** annotated with CVAT; two-stage process (one expert
  annotates, two senior cardiologists cross-validate to consensus).
  **Inter-annotator DSC 0.73–0.90** across ten benchmark images, disagreement
  concentrated at "class borders and inclusion/exclusion of smaller vessels" —
  the same failure mode ImageCAS-X and Choudhary et al. report for distal/side
  branches on CCTA (see [[Class schema options]]), now independently observed
  on a different modality. **Licence: CC0** (public domain). Baseline:
  YOLOv8 multiclass Dice **0.49**; a plain U-Net trained on ARCADE and
  fine-tuned externally reached Dice 0.75 (binary vessel presence, not
  per-segment).
- **CARDIAG** (Lau et al., arXiv:2607.22139v1, 2026, **preprint**): 644
  angiographic sequences from 114 patients, five centres in Northern Poland,
  **26 SYNTAX-derived classes**. Built explicitly as a response to quality
  problems the authors identify in ARCADE — "high concern towards the quality
  of the labels," missing metadata/patient identifiers, and no leakage-safe
  split. CARDIAG adds explicit catheter masks, annotator-uncertainty labels,
  full DICOM metadata, and **institution/patient-stratified splits** "enabling
  genuine generalization assessment." Annotated by three interventional
  cardiologists (≥3 years' experience each); on a 10-image validation subset,
  inter-observer Dice **0.87** (0.9072 with uncertainty-weighting) and Fleiss'
  κ **0.76** for stenosis labelling.

The ARCADE→CARDIAG critique is directly relevant to our own annotation
protocol even though the modality differs: a later, better-resourced group
re-annotated a predecessor dataset specifically because it lacked
patient-level split hygiene and leakage controls — the same trap
[[Fold schemes and split ratios]] documents for ImageCAS vs ImageCAS-X, arrived
at independently on X-ray angiography.

## Other 2024–2026 releases found and ruled out or noted

- **CCA-200** (cited by a geometry-based coronary vectorisation paper, IEEE TMI
  2025; **not independently opened**, so treated as unverified secondhand):
  200 CCTA cases, ground truth is **internal diameter annotation**, not a full
  lumen or per-branch mask. Reported Dice for one geometry-based method:
  0.778 on CCA-200, 0.895 on ASOCA. Wrong label type for our purposes
  (diameter series, not voxel mask); flagged for completeness, not usable as a
  training or validation source without confirming what "diameter annotation"
  actually ships as.
- **PCCTA120** (cited by a 2026 joint artery+plaque segmentation paper on
  PubMed/Springer; **not independently opened**): 120 CCTA volumes with manual
  artery **and** atherosclerotic plaque masks — relevant to plaque analysis as
  a downstream task (see the acceptance-thresholds note) but binary artery
  labelling, not per-branch, as far as the secondary description goes. Not
  verified directly; flag before use.
- No 2023–2026 release found, other than ImageCAS-X, ships **per-branch voxel**
  labels on 3D CCTA. This was searched specifically and repeatedly (see the
  query log implicit in this note's sourcing) and the finding in
  [[State of the art on ImageCAS]] §4 — "no published per-branch state of the
  art" — stands for the wider dataset landscape too, not just for ImageCAS
  itself.

## What this implies for [[Training plan]]

1. **ASOCA is the right external-validation set** for the binary calibration
   run: public, CC BY 4.0 (registration required, not a paywall), a different
   scanner vendor (GE vs ImageCAS's Siemens) and different acquisition
   protocol (anisotropic 0.625 mm slices vs near-isotropic ~0.35 mm), which is
   exactly the domain shift an internal-only Dice number cannot detect. See
   [[External validation and cross-dataset generalisation for coronary
   segmentation]] for what happens to Dice when this shift is actually
   measured (a 6.4-point drop on ImageCAS→ASOCA in one 2025 paper).
2. **Replace "inter-observer agreement ≈ 0.856" with a sourced statement**:
   either the ImageCAS-X figures already adopted in [[State of the art on
   ImageCAS]] (92.8 % binary, per-class table), or, if the plan wants a
   second-dataset corroboration, ASOCA's 85.6 % ± 7.7 % — cited as ASOCA, not
   as an ImageCAS number, since it measures a different cohort's annotators.
3. **CAT08 and orCaScore are not usable** for this project as they stand: CAT08
   labels centerlines and is likely undownloadable, orCaScore labels calcium on
   non-contrast CT. Neither should appear as a benchmark comparator for a
   lumen or per-branch Dice number.
4. **No public per-branch CCTA dataset besides ImageCAS-X exists as of this
   search.** This hardens [[Class schema options]]'s recommendation to adopt
   the ImageCAS-X schema: it is not one option among several published
   per-branch CCTA label sets, it is the only one.
5. ARCADE/CARDIAG's annotation-quality lesson — leakage-safe,
   institution/patient-stratified splits, and explicit uncertainty labelling —
   is a concrete, transferable practice for our own annotation protocol, even
   though the modality differs. Flagged to the annotation-protocol agent in
   `Handoffs.md`.

See [[State of the art on ImageCAS]], [[Fold schemes and split ratios]],
[[External validation and cross-dataset generalisation for coronary
segmentation]] and [[Proposed changes]].
