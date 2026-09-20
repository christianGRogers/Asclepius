---
aliases: [FDA clearance coronary AI, Cleerly, HeartFlow, CAD-RADS AI deployment]
tags: [research, evaluation, regulatory, coronary, clinical, literature]
status: evidence-collected
updated: 2026-09-19
---

# Regulatory and clinical deployment evidence for coronary CT AI

What accuracy level has actually cleared regulatory and reimbursement bars for
shipped coronary CT AI products, to calibrate what "good enough" means for
[[Acceptance thresholds for per-branch coronary segmentation]]. This is market
and policy evidence, not segmentation-benchmark evidence — none of it is
per-branch voxel Dice — but it answers a question none of the segmentation
literature can: what level of agreement with existing clinical practice was
judged sufficient to deploy.

**Short answer.** The bar cleared in practice is lower, and differently
shaped, than the ImageCAS-X human-ceiling numbers this project's own
acceptance thresholds are calibrated against. A cleared, reimbursed
plaque-quantification product agrees with existing visual/CAD-RADS clinical
assessment only moderately (kappa ≈ 0.49–0.55 against two established
methods in one study), yet is FDA-cleared and covered by Medicare — because
what got cleared and reimbursed is an **adjunctive, human-supervised** tool
used after a qualified reader has already interpreted the scan, not an
autonomous replacement for that reader. That framing, more than any specific
accuracy number, is the transferable lesson for this project.

## Sources actually read

- **AI-QCT vs established methods** — Khan H, Bansal K, Griffin WF, et al.
  *Assessment of atherosclerotic plaque burden: comparison of AI-QCT versus
  SIS, CAC, visual and CAD-RADS stenosis categories.* Int J Cardiovasc Imaging
  2024;40(6):1201–1209. doi:10.1007/s10554-024-03087-x. Read in full on PMC
  (PMC11213790).
- **FFR-CT validation and regulatory status** — Stankowski K, Pellizzon A,
  Signorelli L, et al. *FFR-CT: Technical Advances and Implementation in
  Clinical Practice.* J Imaging 2026;12(5):202. doi:10.3390/jimaging12050202.
  Already read in full for [[What downstream coronary tasks need from a
  segmentation]]; the DISCOVER-FLOW/NXT/meta-analysis numbers and the HeartFlow
  regulatory statement are re-used here in the deployment framing rather than
  the geometric-accuracy framing.
- **CMS coverage policy** — Centers for Medicare & Medicaid Services, Local
  Coverage Determination and Billing/Coding Article, *Artificial Intelligence
  Enabled CT Based Quantitative Coronary Topography (AI-QCT)/Coronary Plaque
  Analysis (AI-CPA)* (multiple MAC-specific LCD numbers, e.g. L39851, L39913,
  A59813). Read via search-result synthesis of the CMS Medicare Coverage
  Database listings, **not the primary LCD PDF text itself** — the CMS site
  did not return readable content to this session's fetch tool. The coverage
  conditions below (trained/credentialed interpreters, AI-QCT performed only
  after CCTA is interpreted, coverage tied to CAD-RADS 1–3/intermediate-risk
  populations) are as summarised by the search tool from those listings and
  should be verified against a primary LCD document before being quoted with
  page-level specificity in any manuscript.
- Regulatory and validation facts about **Cleerly**, **HeartFlow** and
  **Elucid** (FDA clearance dates, CREDENCE/PACIFIC-1 AUCs, the 11,000-patient
  HeartFlow plaque cohort, the 95 %-vs-IVUS figure for the next-generation
  HeartFlow platform) are taken from **company press releases and trade-press
  coverage** (HeartFlow investor relations, Diagnostic Imaging,
  Cardiovascular Business, AuntMinnie) found via search, **not from a
  peer-reviewed source opened in this session**. These are marketing and
  trade-press claims, not verified study results, and are flagged as such
  throughout — useful for establishing that clearances exist and roughly what
  was claimed, not as citable accuracy numbers.

## What is actually cleared, and for what

Three named coronary CT AI product lines have FDA 510(k) clearance for
plaque/stenosis analysis on CCTA, in the order search results place their
first clearances: **Cleerly** (2020, described as the first such clearance),
**HeartFlow** Plaque Analysis (2022, with a "next generation" clearance in
2025), and **Elucid** (2024). A fourth, **cvi42 | Plaque**, is also named as
510(k)-cleared for adjunctive plaque quantification. **HeartFlow's FFR-CT
product is described, in the one source read in full here, as "the only
FDA-approved and CE-marked platform" for CFD-based FFR-CT specifically** — a
narrower claim than plaque quantification generally, and consistent with
FFR-CT's much higher geometric-accuracy bar (see [[What downstream coronary
tasks need from a segmentation]]).

All of this is **adjunctive** software: it runs on a CCTA that a credentialed
radiologist or cardiologist has already acquired and is expected to interpret.
This is not incidental — it is a condition of reimbursement. The CMS coverage
material (as summarised above, verify against the primary LCD before quoting)
states that AI-QCT/AI-CPA "shall not be performed until after the base study
(CCTA) has been completed and interpreted," and that reimbursement requires
the interpreting professional to be "appropriately trained and/or credentialed
by a formal residency/fellowship program." **The regulatory and reimbursement
apparatus for this class of product is built around AI as a second read after
a human first read, not as an autonomous diagnostic.** That is a structural
fact about how "good enough" was operationalised for the whole product
category, independent of any single accuracy number.

## The accuracy actually behind a cleared, reimbursed product

Khan et al. 2024 (105 consecutive chest-pain patients, read in full) compared
one FDA-cleared AI-QCT platform against four established assessment methods
on the same scans:

| Reference method | Agreement | Cohen's κ (95% CI) |
|---|---|---|
| Segment Involvement Score (SIS) | 93 % | 0.87 (0.79–0.96) |
| Visual assessment | 64.4 % | 0.488 (0.38–0.60) |
| Coronary artery calcium score (CACS) | 66.3 % | 0.488 (0.36–0.61) |
| CAD-RADS % stenosis category | 73.1 % | 0.55 (0.42–0.68) |

Two things stand out. First, **agreement with the method AI-QCT most directly
formalises (SIS, itself a segment count) is high (κ 0.87), while agreement
with the more subjective methods (visual read, CAD-RADS categorical grading)
is only moderate (κ ≈ 0.49–0.55)** — by conventional κ interpretation bands,
moderate agreement, not substantial or near-perfect. Second, and more
important for calibrating "good enough": **this is the accuracy profile of a
product that is already FDA-cleared and Medicare-reimbursed.** The paper
itself does not state a required accuracy threshold for clearance — the
clearance evidently did not turn on beating these established methods at
high κ, but on demonstrating the tool measures something clinically useful
(plaque burden) with adequate reproducibility, validated separately (see
below) against outcomes rather than against agreement with older, known-crude
methods.

Outcome-level validation, not segmentation-agreement validation, is where the
stronger numbers sit: Cleerly's ISCHEMIA product is described (trade-press,
not independently verified here) as reaching AUC 0.80 (CREDENCE cohort) and
0.85 (PACIFIC-1 cohort) for predicting significant ischemia in a combined
513-patient study, and a roughly 7-fold increase in adverse cardiovascular
events over 8-year follow-up for patients flagged abnormal. FFR-CT's own
validation trials, already read in full for [[What downstream coronary tasks
need from a segmentation]], show the same pattern: NXT trial per-patient AUC
0.90 vs invasive FFR, a 43-study meta-analysis at 82.2 % accuracy. **The
common thread: what got validated and cleared is agreement with a clinical
outcome or an invasive reference standard, not agreement with a
segmentation ground truth or with another imaging-derived method.**

## What this does and does not transfer to our project

This project is not seeking regulatory clearance, and none of the numbers
above are segmentation Dice — they are clinical-agreement and outcome
statistics for downstream products built on top of a segmentation step none
of these sources describe in per-branch voxel terms. Three things nonetheless
transfer:

1. **A deployed, reimbursed product's accuracy against *other imaging-based
   methods* is moderate (κ 0.49–0.55), not near the ImageCAS-X human
   inter-observer ceiling (92.8 % DSC) this project's own acceptance
   thresholds are anchored to.** That is not evidence our thresholds are too
   strict — the tasks are different (categorical plaque/stenosis grading vs
   voxel Dice) — but it is evidence that "matches human performance" is a
   research-quality bar, not the bar that determined clinical deployability
   for the closest analogous product category.
2. **Deployment success is currently defined by outcome/invasive-reference
   validation (AUC against ischemia, agreement with invasive FFR), not by
   segmentation-metric validation.** This project has no outcome data and is
   not positioned to produce any in this phase — worth stating explicitly as
   a limitation of any acceptance-threshold claim: our thresholds describe
   segmentation quality, not clinical validity, and the two are only linked
   by the downstream-task reasoning in [[What downstream coronary tasks need
   from a segmentation]], not by direct evidence.
3. **The regulatory framing (adjunctive, post-hoc, human-supervised) is a
   template for how this project's model should be framed once it leaves the
   training/evaluation phase**, independent of accuracy: presegmentation
   seeds for annotators (already [[Training plan]] §3's design) and any future
   clinical-facing use should preserve a human-in-the-loop framing rather than
   an autonomous one, consistent with how every cleared product in this
   category is actually used.

## What this implies for [[Training plan]]

1. **Do not set an acceptance threshold by analogy to a cleared product's
   accuracy number** — the tasks and validation designs are not comparable
   (categorical plaque grading vs voxel per-branch Dice; outcome-linked
   validation vs segmentation-ground-truth validation). Use this evidence only
   for the framing conclusion above.
2. **Note explicitly, wherever acceptance thresholds are stated, that they
   measure segmentation quality against a human-annotated reference, not
   validated clinical utility** — no outcome or invasive-reference study
   exists or is planned for this project's model, unlike every cleared product
   surveyed here.
3. **Frame any future deployment or annotator-facing use of this model as
   adjunctive**, consistent with the regulatory pattern found across every
   cleared coronary CT AI product in this search.

See [[What downstream coronary tasks need from a segmentation]] and
[[Acceptance thresholds for per-branch coronary segmentation]].
