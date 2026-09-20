---
aliases: [ACCEPTANCE-THRESHOLDS, Acceptance criteria, Evaluation thresholds, Acceptance thresholds]
tags: [research, coronary, evaluation, metrics, clinical, literature]
status: living
updated: 2026-09-19
---

# Acceptance thresholds for per-branch coronary segmentation

[[Training plan]]'s "Still open" list names acceptance thresholds for the
evaluation metrics (Dice, clDice, branch detection rate, NSD, component count,
MASD/AHD) as unresolved. This note closes it with a tiered, per-class,
downstream-task-anchored proposal. It **supersedes**
`vault/Research/Class schema/Handover/Acceptance thresholds.md`, an earlier
draft written before the research was split between agents — its citations are
re-verified here, one correction is made (the BCS decision-agreement
percentages it reports could not be re-confirmed and are marked accordingly),
and its recommendation is extended with the downstream-task, topology, NSD-
tolerance and regulatory evidence gathered since.

**Short answer.** No paper publishes a per-branch *voxel* multiclass result on
ImageCAS or any other CCTA cohort, and no guideline states a clinical
usability threshold for per-branch coronary segmentation — this remains true
after a wider search of the 2023–2026 literature (see [[Public coronary CCTA
datasets]]). What exists, and is used to build the thresholds below: (a)
per-class **human inter-observer** DSC/clDice/Betti-error on our exact cohort
(ImageCAS-X); (b) a published, coded evaluation convention for
variably-present vessel classes (TopCoW); (c) evidence for *why* trunk
detection matters more than distal Dice (CAD-RADS's Modifier N, FFR-CT's
diameter⁴ sensitivity); (d) evidence that deployed, reimbursed coronary CT AI
products cleared regulatory bars at only moderate agreement with prior
methods, not at the human-inter-observer ceiling. The recommendation: gate
trunks and detection, report distal classes with confidence intervals and no
gate, and set the trunk gate closer to the deployed-product accuracy band than
to the human ceiling, because the human ceiling is a research target, not
evidence of what was needed for any coronary CT product to be judged useful.

## Sources actually read (this note's own search, beyond the handover draft)

- **ImageCAS-X** — Bransby KM, et al. arXiv:2608.30404v1, 2026 (preprint).
  Already read in full for [[State of the art on ImageCAS]] and [[Class
  schema options]]; the per-class table is not re-derived here.
- **TopCoW** — Yang K, et al. NEJM AI 2026;3(8). doi:10.1056/AIdbp2500994.
  Already read in full for [[How to measure branch detection and score absent
  branches]].
- **CAD-RADS 2.0**, **FFR-CT geometric sensitivity**, **plaque/centerline
  downstream requirements** — all already read for [[What downstream coronary
  tasks need from a segmentation]]; not re-cited in full here.
- **BCS** — Owusu-Ansah M, Lee K, Venugopal V, Jawaid MM, Duan W, Brown J.
  *Same Branches, Different Trees: A Bifurcation Connectedness Metric for
  Coronary Artery Segmentation and FFR-CT Decision Agreement.* STACOM 2026
  (MICCAI workshop). arXiv:2607.28327, submitted 30 Jul 2026 — **preprint, not
  peer reviewed. Abstract read only in this session** — the full PDF was not
  fetched. **Correction to the handover draft**: it reports FFR-CT
  decision-agreement figures of "75–79 % for baselines, 85–88 % with Skeleton
  Recall or soft-BCS training." That specific pair of numbers could not be
  re-confirmed from the abstract in this session and should be treated as
  **unverified** until the full text is read. What *is* independently
  confirmed from the abstract: BCS scores connectedness at each ground-truth
  bifurcation; higher BCS is associated with closer FFR-CT decision agreement,
  most clearly in severe disease (odds ratio 2.16, 95 % CI 1.23–4.18); and
  soft-BCS and Skeleton Recall training "recover the same branches but build
  different trees" — i.e. branch detection and branch connectedness are
  empirically separable properties, which is directly relevant to why this
  project's metric pool needs both a detection metric and a topology metric
  (see [[Topology and connectivity metrics for coronary trees]]), not one
  standing in for the other.
- Regulatory calibration — [[Regulatory and clinical deployment evidence for
  coronary CT AI]], written in this session from primary sources (Khan et al.
  2024, read in full) and flagged secondary sources (trade press, CMS listing
  synthesis).
- **Kim 2025** — Kim JN, et al. J Med Imaging 2025;12(1):016002.
  doi:10.1117/1.JMI.12.1.016002. Re-verified in [[External validation and
  cross-dataset generalisation for coronary segmentation]]; the 3-class
  internal/external numbers are re-used from there.

Not accessed (unchanged from the handover draft, re-attempted in this
session): the ASOCA challenge paper's ScienceDirect full text (403, no
institutional-login tool available); Choudhary et al. 2011 stenosis
inter-observer study (paywalled, abstract only, already noted in [[Class
schema options]]).

## What is published: binary lumen, for calibration

Unchanged from the handover draft and [[State of the art on ImageCAS]] —
reproduced here for a single reference table:

| Label set / test set | Method | DSC | Other |
|---|---|---|---|
| ImageCAS original masks, official 250-case test fold | ImageCAS baseline | 82.96 % | HD 27.22 mm, AHD 0.818 mm |
| ImageCAS-X labels, 160-case test | nnU-Net | 89.8 ± 3.2 % | HD95 7.08 mm, Betti err 5.6 |
| ImageCAS-X labels, 160-case test | CAS-Net (best) | 91.2 ± 2.8 % | HD95 2.99 mm, Betti err 1.9 |
| ImageCAS-X labels, 160-case test | **inter-observer** | **92.8 ± 3.1 %** | HD95 2.46 mm, Betti err 0.4, clDice 95.4 % |

## What is published: per-class human ceiling on our cohort

ImageCAS-X's per-segment inter-observer table (already reproduced in full in
[[Class schema options]] and [[State of the art on ImageCAS]]) is the ceiling
every threshold below is set relative to. In one line: trunks 84.8–95.3 DSC,
side branches 70.9–83.6 DSC, with standard deviations of 14–32 points and two
classes (L-PDA n=8, L-PLA n=9) too small in the 160-case test set to support
any per-class claim.

## What is new since the handover draft: why the gate belongs on detection, not Dice

[[What downstream coronary tasks need from a segmentation]] adds a mechanism
the handover draft did not have: **CAD-RADS's Modifier N** shows that a single
missed segment above 1.5 mm forces a whole-read failure ("coronary CTA is not
able to guide patient management"), not a small metric penalty — a structural,
independent reason (not just intuition) that a missed trunk/common branch
should be weighted as a category failure. And **FFR-CT's diameter⁴ sensitivity**
plus the BCS paper's OR 2.16 finding (higher connectedness → closer FFR-CT
decision agreement, most clearly in severe disease) together argue that for
any branch a downstream flow model would touch, **connectedness and diameter
accuracy matter more than aggregate Dice**, and the two are separable
properties (BCS abstract, confirmed above) — so the metric pool must report
both a detection/connectedness number and a Dice/distance number per class,
never one only.

## What is new since the handover draft: the regulatory calibration point

[[Regulatory and clinical deployment evidence for coronary CT AI]] adds a
second anchor the handover draft did not have: a **deployed, FDA-cleared,
Medicare-reimbursed** coronary plaque product agrees with established clinical
methods at only **κ ≈ 0.49–0.55** (moderate) against visual read and CAD-RADS
category, and κ 0.87 against the one method it most directly formalises
(SIS). This is not a segmentation-Dice number and is not directly comparable
to our per-branch DSC — but it recalibrates what "good enough for a real
product" has actually meant in this clinical space: **substantially below the
92.8 % human inter-observer ceiling this project's own thresholds are set
against.** The honest reading is that the ImageCAS-X ceiling is the right
number for a *research* target (how good could a model be), while a materially
lower bar has, in practice, been what determined deployability for adjacent
products — and this project is not currently pursuing deployment, so the
research target remains the correct one to report against, with this
comparison stated as context rather than as a lowered goal.

## Recommended thresholds

Provisional, anchored on the published human ceiling and now also on the
downstream-task and regulatory evidence above. Test set: the sealed
160-case ImageCAS-X test set (see [[Fold schemes and split ratios]]).

**Tier 0 — binary sanity.** ImageCAS original masks, official fold: DSC ≥
82.96 % (else the pipeline itself is broken, not a model-quality question).
ImageCAS-X labels: DSC ≥ 89.8 % (reproduce their nnU-Net) as the calibration
gate before any multiclass claim is trusted.

**Tier 1 — trunks (LM, LAD, LCx, RCA).** Gate on *both* per-class DSC and
detection: DSC within 5 points of the human value (≥ 87, 87, 80, 90 for
LM/LAD/LCx/RCA respectively); **detection 100 % for LAD/RCA, ≥ 97 % for
LM/LCx** (these are the classes present in essentially every case, so a
missed detection here is unambiguously a model failure, not a schema
ambiguity). Add, new to this note: **Betti-0 error ≤ 1 per trunk class**,
anchored on ImageCAS-X's inter-observer Betti error of 0.2–0.4 and CAS-Net's
measured 1.9 — a trunk that is topologically broken should fail acceptance
even if its Dice looks acceptable, per the cancellation-blindness argument in
[[Topology and connectivity metrics for coronary trees]].

**Tier 2 — common branches (D1, D2, OM1, R-PDA, R-PLA).** Gate on detection F1
(IoU ≥ 0.25, TopCoW's rule) ≥ 0.85; DSC and MASD reported with 95 % CI, not
gated — per-class human SD of 20–30 points on this tier means a Dice gate
would pass or fail on annotator noise, not model quality (already the
handover draft's reasoning, unchanged). **New**: report **BCS or an
equivalent connectedness measure** for this tier specifically, since these are
the branches a downstream FFR-CT model is most likely to touch and where the
BCS paper's OR 2.16 finding concentrates ("most clearly in severe disease").

**Tier 3 — variably present (IM, OM2, Other).** Gate on detection F1
including TN (a model correctly predicting absence counts as a pass, per
TopCoW's four-way rule) ≥ 0.75; DSC reported only.

**Tier 4 — rare (L-PDA, L-PLA).** No gate. Report with bootstrap CI (see
[[Deciding whether a paired experiment found a real difference]]); n = 8 and 9
in the ImageCAS-X test set is too small to support a pass/fail decision either
way, and forcing one would be exactly the kind of underpowered claim [[CLAIM
and TRIPOD+AI checklists for a coronary segmentation manuscript]] and Metrics
Reloaded both warn against.

**Topology, all tiers.** Report Betti-0 error and, for the final configuration
only (not every ablation), Betti matching error — see [[Topology and
connectivity metrics for coronary trees]]. No fixed gate beyond Tier 1's
Betti-0 ≤ 1 until the multiclass baseline sets a reference point for the other
tiers.

**NSD, all tiers.** Report with the class-specific τ from the annotation
overlap set once it exists; interim τ = one voxel (≈0.35 mm), per [[NSD
tolerance selection for sub-millimetre coronary vessels]]. Never report an NSD
value without its τ alongside it.

## Why this shape (updated reasoning)

- **Per class, not global** — unchanged from the handover draft: human DSC
  spans 70.9–95.3 across classes on this cohort, so one threshold is either
  trivial (RCA) or unachievable (L-PLA).
- **Detection gates the branches; Dice reports but does not gate them** —
  unchanged reasoning (Dice SD too high on small classes to be a fair gate),
  now reinforced by an independent clinical mechanism: CAD-RADS's Modifier N
  treats a missed segment as a category failure, which is structurally a
  detection-style gate, not a Dice-style one.
- **Topology gets its own gate on trunks, and its own report everywhere else**
  — new in this note. The handover draft listed Betti error as "report; no
  gate until the baseline sets a reference." This note tightens that for
  Tier 1 only, because the human ceiling there (0.2–0.4) is tight enough, and
  the clinical stakes of a broken trunk high enough (it feeds both CAD-RADS's
  whole-vessel read and any FFR-CT model), to justify a concrete number rather
  than "report and wait."
- **The human ceiling is a research target; the regulatory evidence is context,
  not a lowered bar** — new in this note. Nothing here proposes weakening the
  ImageCAS-X-anchored thresholds because a deployed product cleared a lower
  bar; the point is only to state, honestly, that these thresholds describe
  segmentation quality against an expert reference, not validated clinical
  utility, exactly as [[Regulatory and clinical deployment evidence for
  coronary CT AI]] concludes.

## What this implies for [[Training plan]]

1. **Close "Acceptance thresholds"** with the five-tier table above, marked
   provisional until the multiclass baseline exists, replacing the handover
   draft.
2. **In "Evaluation"**: adopt TopCoW's absent-class rules verbatim (union of
   present labels; one-sided absence → Dice 0, a stated finite HD95/MASD
   bound; detection IoU ≥ 0.25 with TN for absent–absent) — unchanged from the
   handover draft, now cross-referenced to [[How to measure branch detection
   and score absent branches]] and [[Proposed changes]] item E4/E5.
3. **Add Betti-0 ≤ 1 as a concrete gate for the four trunk classes**, the one
   new hard number this note adds beyond the handover draft's proposal.
4. **State explicitly that these thresholds measure segmentation quality
   against a human reference, not clinical validity** — the regulatory note's
   conclusion, and a disclosure [[CLAIM and TRIPOD+AI checklists for a
   coronary segmentation manuscript]] would expect in any write-up.
5. **Replace "inter-observer agreement ≈ 0.856"** with the sourced figures
   already proposed in [[Proposed changes]] (Datasets and benchmarks folder,
   item D4): ImageCAS-X's 92.8 % (preferred, same cohort) or ASOCA's
   85.6 % ± 7.7 % (the more likely original source of the untraced figure).
6. **Mark the BCS paper's specific decision-agreement percentages as
   unverified** pending a full read, while keeping its OR 2.16 and
   branches-vs-connectedness-are-separable findings as confirmed — a
   correction to the handover draft's uncritical citation of those numbers.

See [[What downstream coronary tasks need from a segmentation]], [[Topology
and connectivity metrics for coronary trees]], [[NSD tolerance selection for
sub-millimetre coronary vessels]], [[Regulatory and clinical deployment
evidence for coronary CT AI]], [[How to measure branch detection and score
absent branches]] and [[Proposed changes]].
