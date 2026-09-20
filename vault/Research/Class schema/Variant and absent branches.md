---
aliases: [Absent branches, Ramus intermedius, Dominance policy, Variant branches]
tags: [research, class-schema, coronary, anatomy, literature]
status: draft
updated: 2026-09-19
---

# Variant and absent branches

The part of the class schema that a segmentation framework handles badly by
default: classes that exist in some patients and not others. For coronary
arteries there are three such groups — the ramus intermedius, the
dominance-dependent PDA/PLB, and the higher-order diagonals and marginals.
This note collects the prevalence figures and the policies published works
adopted. Companion notes: [[Class schema options]],
[[Clinical segment models compared]].

## How often each variant occurs

| Variant | Prevalence | Source |
|---|---|---|
| Ramus intermedius | **25.2 %** (95 % CI 8.7–54.5), 46 studies, 25,602 hearts | Dai et al. 2025, meta-analysis |
| LM trifurcation | 22.7 % (95 % CI 7.4–51.7) | Dai et al. 2025 |
| LM quadrifurcation / pentafurcation | 3.7 % (1.5–8.5) / 1.3 % (0.035–3.5) | Dai et al. 2025 |
| RI on CCTA | 1202 of 4866 CCTA examinations (24.7 %, my arithmetic) | Zhang et al. 2023 |
| IM present, our cohort | 43 of 160 test cases (26.9 %, my arithmetic) | ImageCAS-X |
| Right dominance | 91.1 % | ImageCAS-X, 800 scans |
| Left dominance | 5.1 % | ImageCAS-X |
| Co-dominance | 3.8 % | ImageCAS-X |
| Right / left / co-dominance | 89.7 % / 8.0 % / 2.3 %, 677 patients | Prada Mancilla et al. 2026 |
| L-PDA present, our cohort | 8 of 160 test cases (5.0 %) | ImageCAS-X |
| L-PLA present, our cohort | 9 of 160 test cases (5.6 %) | ImageCAS-X |
| D2 / OM2 present, our cohort | 91 / 46 of 160 | ImageCAS-X |

Three independent sources put the ramus intermedius at ~25 %, including our own
cohort at 26.9 %. That is a usable prior: **roughly one case in four has an IM,
and roughly one in twenty has left-sided PDA/PLA.**

Size: the pooled RI proximal diameter is 2.21 mm (95 % CI 2.02–2.39, 923 hearts)
and mean length 49.1 mm (565 RIs), with individual ranges 1.54–2.74 mm and
6.6–103.7 mm (Dai et al. 2025). At ~0.35 mm voxels an RI is therefore ~6 voxels
across and comfortably above both the 1.5 mm clinical reporting threshold and
the ~1 mm annotation floor discussed in [[Clinical segment models compared]].
The IM is *not* a small vessel; it is a **frequently absent** one. Those are
different problems and want different solutions.

### Sources

- Dai Y, Constantini S, Montalbano MJ, Loukas M. *A meta-analysis and simplified
  nomenclature for diagonal coronary artery and ramus intermedius across adult
  and pediatric hearts.* Clin Anat 2025;39(3):305–324. doi:10.1002/ca.70034.
  Read on PMC (PMC12988317).
- Zhang DQ, Xu YF, Dong YP, Yu SJ. *Coronary computed tomography angiography
  study on the relationship between the ramus intermedius and atherosclerosis in
  the bifurcation of the left main coronary artery.* BMC Med Imaging
  2023;23:53. doi:10.1186/s12880-023-01009-2. Read on PMC (PMC10091592).
- Prada Mancilla WA, Díaz K, Ortiz F. *Coronary dominance on coronary CT
  angiography: prevalence and potential implications for electrocardiographic
  correlation.* J Clin Med 2026;15(13):5258. doi:10.3390/jcm15135258.
- ImageCAS-X: Bransby KM et al., arXiv:2608.30404 (2026, preprint).
- Li Y, Armin MA, Denman S, Ahmedt-Aristizabal D. *Automated coronary arteries
  labeling via geometric deep learning.* IEEE ISBI 2023. arXiv:2212.00386.

## The naming problem underneath the RI

Dai et al.'s reason for writing the meta-analysis is directly relevant to a
class schema. Verbatim: "subsequent literature has shown little consensus on its
classification or nomenclature. Terms such as ramus intermedius, ramus
diagonalis, median artery, left ventricular artery, and diagonal branch of
anterior interventricular artery have been used interchangeably."

Their proposal goes further than any imaging guideline: reclassify the whole
spectrum, RI included, as "diagonal arteries", "a unified and functionally
consistent group defined by their course and perfusion territories", on the
grounds that RI and the diagonals supply the same anterolateral territory and
differ only in origin (RI from the LM, diagonals from the LAD).

I would **not** adopt that for this project, for one concrete reason: origin is
exactly what a voxel model can see and a perfusion territory is not. The RI/D1
distinction is a topological fact in the image (does the vessel leave the LM or
the LAD?), whereas merging them discards the trifurcation finding that both
SCCT and SYNTAX consider worth reporting. But the paper is the right citation
for *why* annotators will disagree here, and it argues for spelling the
RI-versus-D1 rule out in the protocol rather than assuming it is obvious.

## What published works did about absent classes

| Work | Ramus | Left-dominant PDA/PLB | Policy for a class with no vessel |
|---|---|---|---|
| SCCT 2014 | segment 17, only "in case of a trifurcation" | separate segments 15 (L-PDA) and 18 (L-PLB) | segment simply not reported |
| SYNTAX 2005 | segment 12, "belongs to the circumflex territory" | segment 15 "when present"; segment 14 "may be absent or a division of obtuse marginal branch" | not scored |
| ImageCAS-X 2026 | own class (IM) | own classes (L-PDA, L-PLA) | class is empty; dominance derived from which are non-empty |
| Hampe 2024 | no RI class | folded: "L-PDA segments were labeled as LCX, and the L-PLB segments were labeled as OM" | class never absent, because it is folded away |
| Ren 2023 | RI is a class | **excluded** L-PDA and L-PLB; "all patients exhibited right coronary dominance" | avoided by cohort selection |
| Li 2023 (ISBI) | Ramus is a class ("R") | L-PDA and L-PLB are classes | acknowledged as the failure mode (quote below) |

Li et al. are unusually candid about the cost, verbatim: "only one third of
subjects have R branches, and even fewer show L-PDA and R-PDA branches. We note
that it is difficult even for experts to label these three branches due to their
structures." (Their dataset: 141 patients, Wuhan Union Medical College Hospital,
2020–2022; two experts label each branch independently, then "differences are
discussed and voted upon by three experts". Weighted F1 0.805 over 13 SCCT-based
classes, five-fold CV.) Their inclusion of **R-PDA** among the rare branches is
surprising, since R-PDA is present in ~90 % of hearts and in 150 of 160 cases in
ImageCAS-X; I take it at face value as written but treat it as likely specific
to their cohort or a typo for L-PLB. Flagged as unexplained.

So the field splits into three strategies:

1. **Keep the class and accept the imbalance** (ImageCAS-X, Li, Ren for RI).
2. **Fold the rare class into its neighbour** (Hampe: L-PDA → LCX, L-PLB → OM).
   SYNTAX's own definition of segment 14 shows the fold is anatomically
   defensible.
3. **Select the cohort so the problem disappears** (Ren: right-dominant only).
   Not available to us — our cohort is fixed and contains ~41 left-dominant and
   ~30 co-dominant cases.

## Two branches some schemas have and SCCT does not: acute marginal and septal

The SCCT 18-segment model has no acute marginal (AM) and no septal (S) class.
The CASS 28-segment model has both (segment 10 "RV", segment 17 "Septal", per
SCCT's Table 5), Hampe 2024 has both, and ImageCAS's own prose names "acute
marginal 1" among the vessels its radiologists identified (see
[[Class schema options]]).

The evidence says leave both out:

- **Septal** was Hampe 2024's *worst* class by a wide margin: F1 **0.54**,
  against 0.90 for RCA and 0.86 for LAD, in a 10-class centerline-labelling task
  on 104 patients. Septals are numerous, short, and dive into the myocardium.
- **Acute marginal** did better there (F1 0.84), so it is not intrinsically
  hard. The argument against it is compatibility: ImageCAS-X excluded these
  vessels from tracing altogether. Verbatim: "Septal perforators, acute
  marginals and nodal arteries were not traced." Adding an AM class therefore
  means either relabelling their 800 cases or training a class that is empty in
  every imported case — which teaches the model that AM does not exist.
- The same sentence rules out **nodal arteries** (SA and AV nodal branches).
  Worth stating in our protocol explicitly, since an annotator who sees a
  prominent SA nodal branch leaving the proximal RCA has to know whether to
  trace it. Under the adopted schema: no.

If an AM class is ever wanted, it has to be a deliberate relabelling project
with its own annotation round, not a schema tweak.

## Recommendation

**Strategy 1, with strategy 2 available at evaluation time.**

1. **Keep IM, L-PDA and L-PLA as classes.** The IM at ~25 % is not rare enough
   to justify folding, and folding it would discard the trifurcation. L-PDA and
   L-PLA at ~5 % are rare, but they are the *only* encoding of dominance in the
   label map; delete them and the model can no longer express a left-dominant
   heart at all.
2. **Derive dominance, never input it.** ImageCAS-X's rule, restated: right
   dominance = PDA and PLA from the RCA; left = PDA from the LCx; co-dominance =
   PDAs or PLAs from both, or a PDA from the RCA without a PLA from the RCA. A
   post-process reads this off the predicted label map, and the ~91/5/4 split
   becomes a free sanity check on a held-out set.
3. **Write the RI-versus-D1 rule explicitly** in the annotation protocol: a
   vessel is IM only if it arises from the left main itself, between the LAD and
   the LCx (SCCT segment 17; Dai et al. show the terminology is genuinely
   contested, so "obvious" is not good enough). Quadrifurcation (3.7 %) needs a
   stated fallback — the extra vessel goes to "Other".
4. **Report a merged view alongside the 14-class view.** Publishing both a
   14-class result and a Hampe-style merged result (L-PDA → LCx, L-PLA → OM)
   costs nothing at evaluation time, is comparable with more of the literature,
   and separates "the model cannot find this vessel" from "the model cannot name
   this vessel".
5. **Absent classes must be scored explicitly, not silently.** A class present
   in neither reference nor prediction should not enter a mean Dice as either 0
   or 1. The evaluation convention is the metrics owner's call, not mine; the
   schema-side requirement is simply that the label map carries the absence and
   the class list is fixed across cases.

## Still open

- Whether ImageCAS-X's "Other" class absorbs a quadrifurcation's extra LM branch
  or whether such a vessel is labelled IM. Not stated in what I read; check
  against the released label maps.
- Whether co-dominant cases (3.8 % of our cohort) end up with both R-PDA and
  L-PDA non-empty under their protocol. Their dominance definition implies yes,
  but I did not see it stated as a labelling instruction.

## What this implies for [[Training plan]]

- The class schema keeps IM, L-PDA and L-PLA; dominance is derived, not
  declared. This is part of item 1 of [[Proposed changes]].
- Add a derived-dominance check to the evaluation as a cheap cohort-level sanity
  test (expected ~91 % right / ~5 % left / ~4 % co-dominant).
- The rare-class prevalences here (~5 % for L-PDA/L-PLA, ~27 % for IM) are the
  input the sampling and metrics owners need; they are recorded here rather than
  acted on, since those topics belong to other agents.
