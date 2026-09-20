---
aliases: [External validation, Cross-dataset generalisation, Domain shift coronary segmentation]
tags: [research, coronary, dataset, benchmark, generalisation, literature]
status: draft
updated: 2026-09-19
---

# External validation and cross-dataset generalisation practice

What happens when a coronary segmentation model trained on one CCTA cohort is
scored on another, and what the literature says drives the drop. Relevant to
[[Training plan]] because the whole plan is calibrated against internal,
same-cohort numbers (ImageCAS official split, ImageCAS-X split) and currently
has no external-validation step at all.

**Short answer.** Every cross-dataset measurement found agrees on direction and
rough size: training on ImageCAS and testing zero-shot on a different CCTA
cohort costs on the order of **5–13 Dice points**, concentrated in distal/thin
vessels, and the two largest reported drivers are **scanner/acquisition
protocol** (contrast enhancement, edge sharpness) and **calcification burden**
— not architecture. No coronary paper found reports external validation of a
*per-branch* model; every number below is binary lumen.

## Sources actually read

- Khan U, Liatsis P. *Seg2RefineNet: a novel DL-based framework for 2D CCTA
  image-based segmentation and 3D volume-based refinement.* Sci Rep
  2025;15:41096. doi:10.1038/s41598-025-24953-1. Read in full on PMC
  (PMC12635082).
- Zhang S, Gharleghi R, Singh S, Shen C, Adikari D, Zhang M, Moses D, Vickers D,
  Sowmya A, Beier S. *Optimising Generalisable Deep Learning Models for CT
  Coronary Segmentation: A Multifactorial Evaluation.* J Imaging Inform Med
  2025;39(3):2680–2694. doi:10.1007/s10278-025-01677-2. Read in full on PMC
  (PMC13230296).
- Kim JN, Song Y, Wu H, et al. *Improving coronary artery segmentation with
  self-supervised learning and automated pericoronary adipose tissue
  segmentation: a multi-institutional study on coronary computed tomography
  angiography images.* J Med Imaging 2025;12(1):016002.
  doi:10.1117/1.JMI.12.1.016002. Cited via the handover draft
  `vault/Research/Class schema/Handover/Acceptance thresholds.md`; its
  internal/external numbers are re-verified and re-stated here in the
  cross-dataset framing rather than the acceptance-threshold framing.
  (Original PMC ID given there: PMC11831809.)

## The measurements

### ImageCAS → ASOCA, binary lumen, zero-shot

Seg2RefineNet (Khan & Liatsis 2025): trained on ImageCAS's official 700/50/250
split, Dice **83.13 %** on the ImageCAS test fold, HD **12.95 mm**. Applied
zero-shot (no fine-tuning) to ASOCA's 40 cases: Dice **76.70 %**, HD
**29.19 mm** — a **6.4-point Dice drop** and a **more than doubled Hausdorff
distance**. Their stated cause, from qualitative review of failures: the model
"under-segment[ed] the arterial tree" specifically in "fine thin vessels …
particularly as we moved further away from the root of the arterial tree" —
i.e. the drop concentrates in exactly the distal/thin-branch territory this
project's multiclass model exists to label. The Hausdorff blow-up (more than
double, while Dice drops only 6 points) is itself informative: it is the
pitfall [[Why Dice misreads a three-voxel coronary branch]] describes — Dice
under-reacts to a dropped or truncated thin branch while a distance metric
reacts sharply.

### ASOCA → GeoCAD (private, 70 cases), and what predicts the drop

Zhang et al. 2025 is the more mechanistic of the two: three architectures
(nnU-Net, Swin-UNETR, EfficientNet-LinkNet), 5-fold CV on ASOCA (40 cases,
retrospective ECG-gated 64-slice GE), tested externally on GeoCAD (70 cases,
multi-centre, mixed GE/Siemens scanners, prospective ECG-gating, "more modern
acquisition protocols," greater disease diversity — not public).

| Calcification group | Dice on ASOCA (internal) | Dice on GeoCAD (external) | p |
|---|---|---|---|
| None | 0.90 ± 0.03 | 0.82 ± 0.07 | 0.001 |
| Low | 0.86 ± 0.03 | 0.79 ± 0.09 | 0.006 |
| Moderate | 0.87 ± 0.04 | 0.81 ± 0.09 | 0.055 |
| High | 0.85 ± 0.10 | 0.82 ± 0.07 | 0.548 |

Two findings matter beyond the raw drop:

1. **The internal-external gap is largest where calcification is lowest or
   absent** (0.08 points, p = 0.001) and *shrinks to non-significant* at high
   calcification (0.03 points, p = 0.548). Read carefully: this does not mean
   calcified vessels generalise better in absolute terms — high-calcification
   Dice is lower on both sets to start with (0.85 internal vs 0.90 for
   no-calcification internal) — it means calcification's *penalty* is largely
   already priced into the internal number, whereas the acquisition-protocol
   gap shows up as a *generalisation* penalty specifically in the easy cases.
2. **What correlates with test-set DSC**: artery contrast enhancement
   (r = 0.408, p < 0.001) and edge sharpness (r = 0.239, p = 0.046), both
   positively. Vessel curvature: "minimal impact." Sex-linked vessel-size
   effects reached significance in specific branches — **OM1 in males**
   (p = 0.036), **RCA in females** (p < 0.001) — which is, as far as this
   search found, the only published *per-branch* generalisation-relevant
   result on CCTA, even though it is a covariate analysis rather than a
   segmentation benchmark.
3. Authors' own framing: prospective ECG-gating and modern scanners (GeoCAD)
   produced sharper boundaries than ASOCA's retrospective gating, and they
   attribute part of the internal/external gap to acquisition methodology
   rather than to patient population per se.

### Multi-institutional, 3-class (LAD/LCx/RCA)

Kim et al. 2025 (already summarised for acceptance thresholds in
`vault/Research/Class schema/Handover/Acceptance thresholds.md`, re-checked
here): nnU-Net trained with self-supervised pretraining, evaluated internally
(University Hospitals Cleveland, 26 CCTA) at Dice **0.794 ± 0.059**, and
externally (Mackay Memorial Hospital, Taiwan, 73 CCTA, different scanner
population) at Dice **0.741 ± 0.081** — a **5.3-point drop**, same direction and
similar magnitude to the binary-lumen numbers above, now shown on a 3-class
multiclass task specifically. An SSL-pretrained UNETR dropped less (0.787 →
0.757, 3.0 points), which the authors offer as evidence that self-supervised
pretraining on unlabelled multi-institutional data narrows the generalisation
gap — a plausible but single-comparison finding, not independently confirmed
here.

## What this converges on

Three independent groups, three dataset pairs, one direction and a consistent
rough size:

| Train → Test | Task | Internal Dice | External Dice | Drop |
|---|---|---|---|---|
| ImageCAS → ASOCA | binary lumen | 83.1 | 76.7 | 6.4 pts |
| ASOCA → GeoCAD (no calc.) | binary lumen | 90.0 | 82.0 | 8.0 pts |
| Cleveland → Mackay (Taiwan) | 3-class (LAD/LCx/RCA) | 79.4 | 74.1 | 5.3 pts |

None of these is our exact configuration (different architectures, different
patch/crop strategies, different training budgets), so the table is a
**direction-and-order-of-magnitude prior**, not a number to plan a threshold
against. But the consistency across binary and 3-class tasks, and across three
non-overlapping author groups, is stronger evidence than any single paper.

## What no one has measured

- **Per-branch external validation.** Nothing found scores a 10+ class
  per-branch model across datasets. Given the internal per-class spread
  ImageCAS-X reports (70.9–95.3 DSC across branches, see [[State of the art on
  ImageCAS]]) and a ~5–8 point external penalty on the coarser tasks above, a
  naive expectation is that the smallest/rarest branches (L-PDA, L-PLA, OM2)
  would see the external penalty *compound* with their already-poor internal
  score — but this is reasoning by analogy, not a measured number, and should
  be labelled as such in any write-up.
- **External validation using our own multiclass model against ASOCA or
  ImageCAS-X's held-out 160.** Not done by anyone, because the per-branch label
  sets differ (ASOCA has none). The only clean external check available to
  this project without new annotation is running the **binary** model on ASOCA.

## What this implies for [[Training plan]]

1. **Add an external-validation step for the binary calibration run**: score
   the ImageCAS-trained binary model on ASOCA's 40 labelled cases (CC BY 4.0,
   registration via UK Data Service — see [[Public coronary CCTA datasets]]).
   Expect a Dice drop on the order of 5–8 points based on the table above;
   treat anything larger as a signal of overfitting to ImageCAS's single
   scanner/single-centre protocol, which [[Research context]] already flags as
   a named limitation of the source data.
2. **Report contrast enhancement and edge sharpness alongside any external
   result**, not just Dice, since Zhang et al. 2025 found these the strongest
   correlates of external performance — a cheap, image-derived QA check that
   can flag *why* a case failed rather than just that it did.
3. **Do not expect calcification to be the whole story.** It matters for
   absolute Dice but, per Zhang et al., contributes less to the
   internal-vs-external *gap* than acquisition protocol does. Any failure
   analysis should separate "hard because calcified" from "hard because this
   scanner/protocol differs from training."
4. **No external per-branch benchmark exists to calibrate against.** The
   multiclass model's external validity is, for now, unmeasurable outside our
   own held-out set. This is worth stating explicitly in any manuscript rather
   than silently reporting only internal numbers — the publication-checklist
   guidance in [[CLAIM and TRIPOD+AI checklists for a coronary segmentation
   manuscript]] treats an undisclosed absence of external validation as a
   completeness gap, not a neutral omission.

See [[Public coronary CCTA datasets]], [[State of the art on ImageCAS]] and
[[Proposed changes]].
