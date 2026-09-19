---
aliases: [Dice pitfalls, Dice on thin tubes]
tags: [research, evaluation, metrics, coronary, literature]
status: evidence-collected
updated: 2026-09-19
---

# Why Dice misreads a three-voxel coronary branch

[[Training plan]] says Dice "punishes boundary jitter and barely notices a
missing distal branch". This note pins that claim to a published pitfall
taxonomy and to arithmetic that anyone can redo, because it is the premise the
whole evaluation section rests on.

## Source

**Reinke A, Tizabi MD, Baumgartner M, Eisenmann M, Heckmann-Nötzel D, et al.
"Understanding metric-related pitfalls in image analysis validation." Nature
Methods 2024;21(2):182–194. doi:10.1038/s41592-023-02150-0.** Read in full from
arXiv:2302.01790v3 (same text with the supplementary notes). Companion paper to
[[Which metrics to report for thin tubular multiclass segmentation]]; where that
one prescribes, this one diagnoses. It is a Delphi-consensus catalogue of 37
pitfalls, illustrated with constructed examples rather than measurements on real
cohorts — so it establishes *that* a failure mode exists, not how big it is on
ImageCAS.

## The four pitfalls that hit this project

### 1. Overlap metrics are size-sensitive; single voxels move the score

> "Common metrics, for example, are sensitive to structure sizes, such that
> single-pixel differences may hugely impact the metric scores" ([P2.2]).

Arithmetic making the size explicit — **my own, not from any paper**. Take a
cylindrical vessel of radius *r* voxels, and a prediction that is uniformly one
voxel too fat along its whole length. Cross-sectional areas go as π*r*² and
π(*r*+1)², intersection is the reference, so

Dice = 2*r*² / (*r*² + (*r*+1)²)

| vessel radius | diameter at 0.35 mm | Dice for a uniform 1-voxel dilation |
|---|---|---|
| 1.5 voxels | ~1.05 mm | 0.53 |
| 2 voxels | ~1.4 mm | 0.62 |
| 3 voxels | ~2.1 mm | 0.72 |
| 5 voxels | ~3.5 mm | 0.83 |
| 10 voxels | ~7 mm | 0.91 |

The same physical error — half a voxel of boundary placement, which is inside
annotator noise — costs 0.09 on a proximal RCA and 0.38 on a distal diagonal.
A per-class Dice table therefore ranks classes by calibre before it ranks them
by segmentation quality. ImageCAS-X's reported correlation of local DSC with
lumen diameter (ρ = +0.89) is the empirical version of this arithmetic, though
I have not yet re-verified that paper myself (it is cited in the handover draft
`vault/Research/Class schema/Handover/Acceptance thresholds.md`).

### 2. Large structures dominate; a missing branch is invisible

> "Large structures completely dominate overlap-based metrics in semantic
> segmentation problems. While Prediction 1 perfectly segments all three small
> structures, the metric score (here: DSC) is much worse compared to the score
> of Prediction 2, with only one perfect prediction for the large structure."
> (Extended Data Fig. SN 2.13.)

Arithmetic again mine: if the distal third of a branch is 10 % of that class's
voxels and the model drops it entirely, class Dice is 2(0.9)/(1.9) = **0.947**.
A whole missing vessel segment costs five Dice points. Aggregate that into a
mean over classes and it disappears entirely. This is precisely why detection
and topology metrics are not garnish — they are the only members of the pool
that can see the failure this project most cares about.

Note this pitfall bites *within* a class here, not just across classes, because
a coronary "class" is itself a tapering tube whose proximal end outweighs its
distal end.

### 3. Overlap metrics are shape- and centreline-unaware; clDice is the fix

> "Common overlap-based metrics such as the DSC are unaware of complex structure
> shapes and treat Predictions 1 and 2 equally. The centerline Dice Similarity
> Coefficient (clDice) uncovers that Prediction 1 misses the fine-granular
> branches of the reference and favors Prediction 2, which focuses on the
> object's center line and better captures its fine branches."
> (Extended Data Fig. SN 2.14.)

Caveat recorded by the same paper: clDice inherits several of Dice's problems —
it is listed as affected by small structure sizes, high size variability,
boundary unawareness, nested-label violations, empty references, and inter-rater
variability in the pitfall tables (Extended Data Fig. SN 2.12, 2.13, 2.19, 2.20,
2.21 and Fig. 4a). **clDice is not boundary-aware and is not a replacement for a
distance metric.** It answers "is the tree there", not "is the lumen the right
width" — and for stenosis grading the width is the point (see
[[What downstream coronary tasks need from a segmentation]]).

### 4. Inter-rater variability is not modelled by overlap metrics

> "Assessing the performance of Annotator 2 while using an reference annotation
> created by Annotator 1 leads to a low DSC score because inter-rater
> variability is not taken into account by common overlap-based metrics. In
> contrast, the Normalized Surface Distance (NSD), applied with a threshold of
> τ = 1, captures this variability. It should be noted, however, that this
> effect occurs primarily in small structures as overlap-based metrics tend to
> be robust to variations in the object boundaries in large structures."
> (Extended Data Fig. SN 2.19.)

The last sentence is the one to keep: the whole problem is specific to small
structures, which is every class we have except the aorta-adjacent trunk
segments.

## Application-stage pitfalls that apply to us too

- **[P3.1] Implementation is not standardised.** "For metrics assessing
  structure boundaries, such as the ASSD, the exact boundary extraction method
  is not standardized. Thus, for example, the boundary extraction method
  implemented by the LiTS challenge and that implemented by Google DeepMind may
  produce different metric scores for the ASSD. This is especially critical for
  metrics that are sensitive to small contour changes, such as the HD." Our
  `_surface()` in `src/segtrain/metrics.py` uses a 6-connected erosion, which is
  one defensible choice among several; the surface definition, the connectivity,
  and the spacing handling all need to be stated in any write-up, because
  another group's "NSD at 1 mm" is not necessarily ours.
- **[P3.2] Aggregating over the whole dataset hides small structures.** They
  name TorchMetrics as computing DSC "as a global average over all pixels in the
  data set without considering their image or class of origin" and warn that
  "errors in small structures may be suppressed by correctly segmented larger
  structures in other images". `segtrain evaluate` already aggregates per case
  and per structure, so we are on the right side of this one — but
  `summarize()`'s `mean Dice` line pools every (case, structure) pair into one
  number, which is the pooled statistic this pitfall warns against.
- **[P3.3] Do not report Dice and IoU together.** "the DSC and IoU are closely
  related, so using both in combination would not provide any additional
  information". Also: rankings "are highly sensitive to altering the metric
  aggregation operators, the underlying data set, or the general ranking
  method", which is the reason the ResEnc-versus-plain comparison needs a
  stated, pre-registered decision rule rather than a leaderboard glance — see
  [[Deciding whether a paired experiment found a real difference]].
- **[P3.4] Box plots hide the tail.** "while a box plot provides basic
  information, it does not depict the distribution of metric values. This may
  conceal important information, such as specific images on which an algorithm
  performed poorly." Also flagged: non-determinism across runs "even with fixed
  seeds", and "reporting solely the results from the best run instead of proper
  cross-validation and reporting of the variability across different runs".

## What this implies for [[Training plan]]

- Keep the "Dice demoted" decision, and cite Reinke et al. 2024 for it; add the
  one-line reason that the penalty scales with 1/calibre, so per-class Dice is
  partly a measure of vessel size.
- Say explicitly that clDice does **not** cover boundary accuracy, so the metric
  pool needs clDice *and* a boundary/distance metric; clDice alone would let a
  systematically over-thick lumen through unnoticed, which is the error that
  breaks stenosis grading.
- Report per-case distributions (strip/violin, not box plots) and the number of
  runs, not only means.
- Drop IoU if it is ever added; Dice already carries that information.
- Document the surface-extraction convention used by `src/segtrain/metrics.py`
  alongside any published number.
