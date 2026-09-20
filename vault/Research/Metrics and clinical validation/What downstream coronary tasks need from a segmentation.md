---
aliases: [Downstream coronary tasks, Clinical use cases for coronary segmentation]
tags: [research, evaluation, metrics, coronary, clinical, literature]
status: evidence-collected
updated: 2026-09-19
---

# What downstream coronary tasks need from a segmentation

[[Training plan]]'s evaluation section measures Dice, clDice, NSD, branch
detection and topology, but none of those numbers says whether a segmentation
is *clinically usable*. Usability is defined by what the segmentation feeds
into. This note surveys the four downstream uses that matter for a coronary
model — stenosis grading / CAD-RADS, FFR-CT / flow modelling, plaque analysis,
and centerline extraction — and what each one needs geometrically. It is the
evidence base for [[Acceptance thresholds for per-branch coronary
segmentation]].

**Short answer.** Every downstream task cited a **1.5 mm minimum vessel
diameter** as the point below which clinical grading stops (three independent
guideline documents agree on this number). Below that, tasks diverge sharply
in what they need: stenosis grading needs the diameter profile along the
vessel to be right, not the volume; FFR-CT needs it enough to worry about
because flow resistance scales with the diameter to the fourth power, so
segmentation error compounds nonlinearly and gets worse distally; plaque
quantification needs the lumen/wall boundary, which a lumen-only mask by
definition cannot give directly; centerline extraction is the one task with a
published, extremely tight accuracy figure (sub-0.15 mm) because it is a much
easier geometric problem than volumetric segmentation.

## Sources actually read

- **CAD-RADS 2.0** — Cury RC, Leipsic J, Abbara S, et al. *CAD-RADS™ 2.0 – 2022
  Coronary Artery Disease-Reporting and Data System: An Expert Consensus
  Document of SCCT, ACC, ACR, and NASCI.* JACC Cardiovasc Imaging
  2022;15(11):1974–2001. doi:10.1016/j.jcmg.2022.07.002. **Primary text not
  opened** — JACC and RSNA (`pubs.rsna.org/doi/full/10.1148/ryct.220183`) both
  returned HTTP 403 to non-browser fetch in this session, the same wall the
  class-schema agent hit. The stenosis-category table and the 1.5 mm/Modifier N
  details below are read from **radiologyassistant.nl**'s clinical summary
  page, a secondary source that a practising radiologist would recognise as
  authoritative for the category boundaries but is not the primary document —
  verify against the JACC PDF (or via UofT proxy) before quoting a number from
  this section in anything published.
- **FFR-CT lumen sensitivity** — Fernández-Martínez et al. *Impact of minimal
  lumen segmentation uncertainty on patient-specific coronary simulations: A
  look at FFRCT.* Int J Numer Methods Biomed Eng 2024;40(6):e3822.
  doi:10.1002/cnm.3822. **Abstract and a secondary description read only** —
  Wiley returned HTTP 403 to direct fetch and the institutional repository
  mirror (`dehesa.unex.es`) was unreachable in this session. 14 patient-specific
  coronary models; qualitative finding quoted below, exact mm/percentage
  figures not verified.
- **FFR-CT technical/clinical review** — Stankowski K, Pellizzon A, Signorelli
  L, et al. *FFR-CT: Technical Advances and Implementation in Clinical
  Practice.* J Imaging 2026;12(5):202. doi:10.3390/jimaging12050202. Read in
  full on PMC (PMC13208309).
- **Automated calcium quantification** — Lee JO, Park EA, Park D, Lee W. *Deep
  Learning-Based Automated Quantification of Coronary Artery Calcification for
  Contrast-Enhanced Coronary Computed Tomographic Angiography.* J Cardiovasc
  Dev Dis 2023;10(4):143. doi:10.3390/jcdd10040143. Read in full on PMC
  (PMC10146297).
- **Centerline extraction accuracy** — the CAT08/Rotterdam framework numbers
  (Schaap et al. 2009) quoted via [[Public coronary CCTA datasets]]'s source
  chain; the specific accuracy figures below (OV 99.97 %, AI 0.13 mm) are from
  a secondary source (PMC10743762) describing a well-performing CAT08-era
  method, not from Schaap et al. directly — flagged the same way as in
  [[Public coronary CCTA datasets]].

## 1. Stenosis grading and CAD-RADS

CAD-RADS reports the single most severe luminal narrowing (diameter reduction)
per vessel/patient, on a 7-category scale (0, 1 <25 %, 2 25–49 %, 3 50–69 %,
4A 70–99 % one/two-vessel, 4B left-main >50 % or three-vessel ≥70 %, 5 total
occlusion), determined per-segment on the **SCCT 16/17/18-segment model**
already adopted in [[Class schema options]].

Two numbers matter for a segmentation model:

- **1.5 mm minimum diameter for grading.** "All coronary arteries >1.5 mm
  diameter are graded for stenosis severity" (secondary source, see caveat
  above). This is the same threshold SCCT 2014 and SYNTAX use for defining a
  reportable side branch (see [[Clinical segment models compared]]) — three
  independent guideline lineages converge on 1.5 mm as the point below which
  formal grading stops, even though ImageCAS-X's *annotation* floor is lower
  (1 mm to trace a branch at all, per [[Class schema options]]). That gap
  matters: our class schema traces vessels the clinical read does not formally
  grade, so a distal-branch Dice number below 1.5 mm diameter is informative
  for the model but not itself a clinical-usability gate.
- **Modifier N (non-diagnostic).** A segment >1.5 mm that cannot be assessed —
  motion, noise, or (by direct analogy) a segmentation failure — forces the
  whole read to CAD-RADS N when the alternative reading would have been 0–2,
  because "coronary CTA is not able to guide patient management" in that case.
  This is the clinical analogue of the branch-detection-rate metric in
  [[How to measure branch detection and score absent branches]]: a *missed*
  vessel is not a small Dice penalty, it is a category failure that changes
  what a clinician can act on. It argues for weighting detection failures on
  trunk/near-trunk segments (>1.5 mm) far more heavily than a Dice-point loss
  would suggest.

What stenosis grading does **not** need: total lumen volume, or a
perfect boundary along a whole segment. It needs the **minimum lumen
diameter along the vessel's centerline profile** to be right at the tightest
point — a metric closer to "cross-sectional diameter at the narrowest cut" than
to Dice, which averages error over the whole segment. Quantitative CTA
diameter methods are documented to be **biased** (17.3–22.9 % systematic
underestimation of stenosis severity vs QCA in one study found in this
search), and diameter stenosis alone is reported to correlate only weakly with
invasive FFR (r ≈ 0.30) — evidence that diameter-based grading is itself an
imperfect proxy for flow-limiting disease, independent of segmentation
quality. **Not independently verified beyond the search snippet** — flagged
for follow-up rather than treated as settled.

## 2. FFR-CT and flow modelling

FFR-CT computes fractional flow reserve from CFD simulation on the segmented
lumen geometry: "accurate coronary lumen segmentation is crucial as FFR-CT
depends on computational fluid dynamics simulation with the well-delineated
coronary lumen." The mechanistic reason segmentation error matters more here
than for a Dice-style comparison: **stenosis resistance in Poiseuille flow
scales with diameter to the fourth power**, so a small diameter measurement
error at a narrow point produces a disproportionately large resistance (and
therefore FFR) error. This is a physical argument, not a segmentation
benchmark result, but it is the reason the field treats geometric accuracy as
categorically more important for FFR-CT than for a stenosis-grading read.

Fernández-Martínez et al. 2024 measured this directly by perturbing lumen
segmentation on 14 patient-specific models and re-running the CFD: **FFR-CT
sensitivity to segmentation uncertainty increases both distally and with
stenosis severity**, and they recommend "exact and thorough segmentation" (or
falling back to invasive FFR) specifically for "moderate or severe distal
coronary lesions" when the computed FFR-CT sits near the 0.80 treatment
cutoff. That 0.80 cutoff is itself the number a segmentation error could flip
a patient across.

Clinical stakes and current diagnostic performance, for context (not our
model's numbers): the NXT trial reports **per-patient AUC 0.90 (95 % CI
0.87–0.94)** for FFR-CT vs 0.81 for CT stenosis alone against invasive FFR,
correctly reclassifying 68 % of CCTA-alone false positives; a 43-study,
>7,000-vessel meta-analysis gives accuracy 82.2 %, sensitivity 80.9 %,
specificity 83.1 %. **HeartFlow** is stated to be the only FDA-approved and
CE-marked FFR-CT platform (see [[Regulatory and clinical deployment evidence
for coronary CT AI]] for the regulatory detail).

Implication for us: **a distal-branch acceptance threshold cannot be set by
Dice alone if FFR-CT is a stated downstream use**, because the failure mode
that breaks FFR-CT (a locally wrong diameter at the tightest point) is exactly
what Dice under-weights (see [[Why Dice misreads a three-voxel coronary
branch]]) and what MASD/NSD are better positioned to catch, provided the
tolerance is tight enough to see a sub-millimetre diameter error rather than
average it away.

## 3. Plaque analysis

Automated calcium/plaque quantification (Lee et al. 2023, contrast-enhanced
CCTA, n not restated here — read for its accuracy figures) reports
**concordance correlation 0.90–0.97 (volume) and 0.97 (Agatston) internally**,
falling to **0.76–0.94 / 0.82–0.88 externally**, with **14.2 % of patients
reclassified to a different cardiovascular risk category** on the external
set. Two things carry over to us:

1. **The internal→external drop pattern matches** what
   [[External validation and cross-dataset generalisation for coronary
   segmentation]] finds for lumen segmentation — a several-point, sometimes
   double-digit, degradation off the training distribution, here measured on a
   different clinical endpoint (calcium score, not Dice).
2. **A quantitative structural gap for our project**: plaque quantification
   needs the **outer vessel wall boundary**, not just the lumen. ImageCAS-X's
   labels, and our own schema built on them (see [[Class schema options]]),
   are **lumen-only** — "outer wall rather than lumen" inclusion is explicitly
   named as one of the three failure modes that make the original ImageCAS
   masks score only 41.8 % DSC against re-annotation (see [[State of the art
   on ImageCAS]]). A lumen segmentation, however accurate, is not itself a
   plaque-quantification tool; if plaque analysis is a genuine downstream goal
   for this project, that is a **schema gap**, not a metrics gap, and belongs
   to the class-schema agent — flagged in `Handoffs.md`.

## 4. Centerline extraction

The one downstream task with genuinely tight, already-achieved accuracy
numbers, because it is geometrically a much smaller problem (a 1D path, not a
3D volume). A well-performing CAT08-era method (read via PMC10743762, a
secondary description of Schaap-framework results, not Schaap et al.
directly) reports **overlap accuracy 99.97 %, overlap-until-first-error
100 %, overlap of the clinically relevant portion 99.98 %, and mean error
distance inside the vessel of 0.13 mm** — sub-voxel at our spacing. This is
the number to keep in view as a ceiling: whatever the multiclass voxel model
achieves, a downstream centerline step applied to a good segmentation can be
extremely accurate, which is also why [[Class schema options]] recommends
centerline-based label propagation (assign each lumen voxel to its nearest
labelled centerline point) rather than voxel-painted boundaries — the
centerline is the part of this problem that is nearly solved.

## What this means for acceptance thresholds, in one table

| Downstream task | What it needs from the segmentation | Failure mode a mean Dice hides |
|---|---|---|
| CAD-RADS / stenosis grading | correct minimum diameter at the tightest point, per segment ≥1.5 mm | Modifier N: one missed segment fails the whole read |
| FFR-CT / flow modelling | diameter accuracy that scales as error⁴ in resistance, worst distally | a small local error near the treatment cutoff (FFR 0.80) |
| Plaque analysis | outer wall boundary (not in our lumen-only schema) | schema gap, not a metric one — see `Handoffs.md` |
| Centerline extraction | topological correctness of the path | already near-solved (0.13 mm) if the lumen mask is topologically right |

## What this implies for [[Training plan]]

1. **1.5 mm is a defensible clinical-relevance floor** for gating acceptance
   thresholds on trunk/near-trunk segments, independent of and corroborating
   the 1 mm/1.5 mm annotation-floor numbers already in [[Class schema
   options]] and [[Clinical segment models compared]]. Distal branches below
   1.5 mm remain scientifically interesting (they are this project's
   contribution) but should not be gated against a clinical-grading standard
   that itself does not grade them.
2. **A missed segment >1.5 mm should be weighted as a category failure, not a
   Dice point**, when the plan discusses what "good enough" means — this
   directly supports gating on detection rate for trunk/common branches over
   gating on Dice, which [[Acceptance thresholds for per-branch coronary
   segmentation]] adopts.
3. **If FFR-CT-style downstream use is ever a stated goal, distal-branch
   diameter accuracy (not volumetric Dice) becomes the metric that matters**,
   and the NSD tolerance should be tight enough to catch a sub-millimetre
   diameter error rather than average across the branch — see [[NSD tolerance
   selection for sub-millimetre coronary vessels]].
4. **Plaque analysis is not achievable from a lumen-only mask.** Flag as a
   schema question, not an evaluation one, for the class-schema/annotation
   agents.
5. **Centerline accuracy is not the bottleneck.** The voxel segmentation is;
   once it is topologically correct, downstream centerline extraction is
   expected to be highly accurate on the evidence above.

See [[Acceptance thresholds for per-branch coronary segmentation]],
[[Regulatory and clinical deployment evidence for coronary CT AI]] and
[[Proposed changes]].
