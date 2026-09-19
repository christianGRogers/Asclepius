---
aliases: [Metric choice, Metrics Reloaded for coronaries]
tags: [research, evaluation, metrics, coronary, literature]
status: evidence-collected
updated: 2026-09-19
---

# Which metrics to report for thin tubular multiclass segmentation

What a published, consensus metric-selection framework says our metric pool
should be, applied to per-branch coronary segmentation. The [[Training plan]]
"Evaluation" section already names most of these; this note supplies the
citation, the conditions under which each is recommended, and the places where
the plan and `src/segtrain/metrics.py` diverge from the recommendation.

## The source

**Maier-Hein L, Reinke A, Godau P, Tizabi MD, Buettner F, et al. "Metrics
reloaded: recommendations for image analysis validation." Nature Methods
2024;21(2):195–212. doi:10.1038/s41592-023-02151-z.** Read in full from the
arXiv version of record (arXiv:2206.01653v8, same text plus the supplementary
notes, which is where the decision guides live); the DOI and the Nature Methods
volume/pages were confirmed from the PMC copy (PMC11182665). Quotations below
are verbatim from the supplementary notes and are cited by their internal
identifiers (FP = problem fingerprint item, DG = decision guide, S = subprocess).

It is a Delphi-consensus framework, not an experiment: it tells you which metric
answers which question, and it is the document a reviewer will expect a 2026
segmentation paper to have followed. It does **not** supply thresholds — see
[[Acceptance thresholds for per-branch coronary segmentation]].

## Our problem fingerprint

Filling in the fingerprint items that drive the recommendations:

| Fingerprint item | Our value | Why |
|---|---|---|
| FP1.1 problem category | semantic segmentation, multi-class | one label map, classes are named branches, not repeated instances |
| FP2.3 importance of centre(line) | TRUE | downstream use is centreline/lumen-based; see [[What downstream coronary tasks need from a segmentation]] |
| FP3.1 small structures relative to grid | TRUE for distal branches | 1.5–2 mm vessel at ~0.35 mm spacing is 4–6 voxels across; the plan already says 3–4 |
| FP3.3 tubular shape | TRUE | the defining property of the task |
| FP3.6 disconnected target structures | TRUE | the coronary tree is 2–3 trees, and a single branch class can be split by a calcified gap |
| FP4.3.1 high inter-rater variability | TRUE | per-branch human DSC ranges roughly 71–95 on this cohort (see the acceptance-thresholds note) |
| FP4.6 empty reference possible | TRUE | ramus intermedius, L-PDA/L-PLA are absent in most patients |
| FP5.2 empty prediction possible | TRUE | same classes |

Almost every fingerprint item that changes the recommendation is TRUE for us.
That is the reason a single mean Dice is the wrong summary for this project,
and it is now a citable reason rather than an opinion.

## What the framework recommends, given that fingerprint

### Overlap metric: DSC by default, clDice *in addition* for tubes

> "we recommend using them by default unless the target structures are
> consistently small, relative to the grid size (FP3.1), *and* the reference may
> be noisy (FP4.3.1). […] we recommend the DSC or IoU (default recommendation),
> the F Score (preferred when there is a preference for either False Positive
> (FP) or False Negative (FN)) or the centerline Dice Similarity Coefficient
> (clDice) (for tubular structures)."

And in Suppl. Note 2.3:

> "In the specific case of tubular structures (FP3.3), the centerline Dice
> Similarity Coefficient (clDice) (Fig. SN 3.4) as an increasingly used variant
> of the DSC can also be applied (optionally in addition to the DSC)."

Two readings matter here.

1. The escape clause from DSC requires small structures **and** a noisy
   reference. Both hold for our distal branches, so the framework does license
   demoting DSC — but only for those classes. For LM/LAD/RCA trunks DSC stays a
   reasonable default. This is exactly the "Dice is kept but demoted" position
   in [[Training plan]], and it now has a citation with a stated condition.
2. clDice is recommended as a *metric* for tubular structures. That is
   independent of whether clDice is used as a loss, which belongs to another
   agent's topic.

The framework also explicitly blesses adding connectivity metrics:

> "Also, the clDice can be complemented by application-specific connectivity
> metrics, for instance in the case of tubular structures."

which is where component counts and Betti-0 errors enter legitimately (see
[[Topology and connectivity metrics for coronary trees]]).

### Boundary metric: NSD, and the tolerance comes from inter-rater variability

> "If annotation imprecisions should be compensated for (FP2.5.7), our default
> recommendation is the Normalized Surface Distance (NSD)."

On choosing the tolerance τ (DG7.1, NSD versus Boundary IoU):

> "NSD: Boundary distances below the tolerance threshold will be considered TP
> (deviations do not count as errors). This parameter can be set according to
> the inter-rater variability or, if not available, heuristics."

This is the single most actionable sentence in the paper for us. `DEFAULT_NSD_
TOLERANCE_MM = 1.5` in `src/segtrain/metrics.py` was chosen as "one voxel at
1.5 mm isotropic" — a TotalSegmentator-era heuristic. At ~0.35 mm coronary
spacing, 1.5 mm is four voxels and roughly the radius of a distal vessel: an NSD
with that tolerance would score a prediction as boundary-perfect while it
covered a tube of the wrong calibre. The tolerance must be re-derived from our
own annotation overlap set, which is the same set the annotation-protocol agent
is sizing. Until that number exists, τ = 0.35 mm (one voxel) is the defensible
heuristic, and the tolerance must be reported next to every NSD value — an NSD
without its τ is uninterpretable.

### Distance metric: MASD by default, HD95 only if you want an outlier number

> "In the case of distance-based penalization, Mean Average Surface Distance
> (MASD) (Fig. SN 3.25) is our default recommendation, as it has mathematical
> advantages over Average Symmetric Surface Distance (ASSD) (Fig. SN 3.22 […])
> and is not as sensitive to annotation outliers as Hausdorff Distance (HD) and
> its variants (Fig. SN 3.24)."

MASD versus ASSD (DG7.2): ASSD pools all boundary distances into one list and
takes the mean, so "if one boundary is much larger than the other, this boundary
will impact the mean much more"; MASD averages each direction separately and
then sums, so "the reference and prediction boundaries contribute equally". For
a class where the model predicts a stub of a long vessel, ASSD is dominated by
the reference surface and MASD is not — for us MASD is the better-behaved
choice, with the documented corner case that "if the Prediction is very small
(here: one pixel) and located close to the reference boundary, the MASD will be
much lower compared to the ASSD". That corner case is a real risk for a barely
detected distal branch, so MASD must never be read without the detection metric
beside it.

HD versus HD95 (DG7.3): the X-percentile variant "should therefore be used
instead if spatial outliers should be disregarded". Their worked example makes
the size point concretely — one erroneously annotated pixel gives DSC 0.95,
IoU 0.90, **HD 11.31, HD95 6.79, ASSD 0.67, MASD 0.63, NSD 0.88** (units are
pixels in a synthetic figure, Extended Data Fig. SN 2.23), with the comment that
a single bad pixel hurts "especially in the case of the HD when applied to small
structures".

This *partly* contradicts [[Training plan]], which says "Distances as **AHD**,
not HD, which single outliers dominate." The framework agrees that raw HD is
wrong and that an averaged surface distance is the default; it would have us
call the averaged one MASD rather than AHD (ImageCAS's "AHD" is an average
symmetric surface distance, i.e. ASSD-family, so the plan's intent is right and
only the name and the exact definition need fixing). The framework does not
deprecate HD95 — it positions it as the metric you choose when you deliberately
want the outlier penalised by distance. Both are defensible and they answer
different questions; the honest reporting is MASD as the headline distance and
HD95 alongside, which is also what `hausdorff95` in `src/segtrain/metrics.py`
already computes for SegQueue's annotator QA.

### Aggregation: per case first, then across cases; macro average over classes

> "pixels of the same image are highly correlated. Hence, to respect the
> hierarchical data structure, metric values should first be computed per image
> and then be aggregated over the set of images."

`aggregate()` in `src/segtrain/metrics.py` already does this correctly
(per-case `ClassScore`s, averaged per structure afterwards). Note the framework
also observes "the commonly used DSC is mathematically identical to the popular
F1 Score applied at pixel level", which is why a pooled-over-dataset Dice is a
different and wrong number.

For combining classes: macro averaging "indicating equal importance for each
class […] and an interest to compensate for potential class imbalance", or
weighted averaging where importance differs. For us the trunk classes matter
more clinically than OM2, so a single macro mean is a reporting convenience,
never the acceptance gate.

### Missing values: their default is the *opposite* of ours

> "We recommend handling of 'Not a Number's (NaNs) by setting the corresponding
> metric value to the worst possible value […] In the case of distance-based
> metrics such as the HD, the image diagonal can be chosen, for example."

Their worked example: DSC values 0.94, NaN, 0.87, 0.90, NaN, 0.89 give **mean
0.90 if NaNs are ignored and 0.60 if NaNs are set to 0** (Extended Data
Fig. SN 2.5); for HD, 6.76 ignoring versus 11.10 setting to the image diagonal
(Fig. SN 2.6).

`src/segtrain/metrics.py` deliberately does the opposite — its docstring argues
that scoring an absent structure as 0 "would drag every whole-body average down
in proportion to how often the field of view is limited". Both are right about
different cases, and the distinction the code does not currently draw is:

- **absent in reference and absent in prediction** — a correct call. Scoring it
  0 is wrong; the framework's own object-detection guidance agrees, recommending
  "to exclude NaN cases from metric computation except when an empty prediction
  corresponds to an empty reference, in which case PPV, and in extension F
  Score, should be set to 1."
- **present in one and absent in the other** — a real, total failure. Today
  `dice_score` returns 0.0 for this (correct), but `hausdorff95` returns `inf`
  and `agreement()` serialises it to `None`, so it vanishes from any mean. That
  is the case the framework says must be set to a worst-case bound, and it is
  the case that matters most for a missed distal branch. TopCoW's published code
  uses a fixed `HD95_UPPER_BOUND = 90` mm for exactly this (recorded in the
  handover draft; verification of that code is pending).

So the fix is not "follow Metrics Reloaded" but "split the two NaN cases", which
is a concrete change to `src/segtrain/metrics.py`; see [[Proposed changes]].

### Small test sets and reporting

- "Small test set size — Recommendation of confidence intervals for all
  metrics." (Fig. SN 1.x pitfall table.) Our rare classes will be present in
  single-digit numbers of test cases; CIs are mandatory there, not optional.
- "Insufficient domain relevance of metric score differences — Report on the
  quality of the reference (e.g. intra-rater and inter-rater variability).
  Choose the number of decimal places such that they reflect both relevance and
  uncertainties of the reference. More than one decimal number is often not
  useful given the typically high inter-rater variability." Our tables currently
  print four decimal places (`evaluate.summarize`).
- "Avoid combining closely related metrics […] when choosing metrics to be used
  in algorithm ranking" — DSC and IoU are the same information; do not report
  both and do not let both vote in a ranking.
- "Include a visualization of the raw metric values […] and report the full
  confusion matrix". The plan's AHA-segment confusion matrix is squarely in line
  with this; the raw-values visualisation (per-case dot/box plot, not just a
  mean) is not yet in the plan.

### One recommendation we should *not* follow blindly

FP3.1 (small structures) carries "recommendation to consider the problem an
object detection problem", and FP3.5 (overlapping/touching structures) says to
"phrase problem as instance segmentation rather than semantic segmentation
problem". Our branches touch at bifurcations, which literally triggers FP3.5.
Re-phrasing the whole task as instance segmentation is not on the table — the
model is a voxel semantic segmenter by decision 1 of [[Training plan]] — but the
right compromise is the one the framework itself suggests for instance problems:
keep semantic segmentation and add an explicit **detection metric per class**
with a localisation criterion and a stated threshold, so that "did we find this
branch at all" is measured separately from "how well did we outline it". That
is the branch-detection-rate item already in the plan; see
[[How to measure branch detection and score absent branches]].

## Metric pool this implies, per class

| Question | Metric | Notes |
|---|---|---|
| Did we find the branch? | detection TP/FP/FN/TN with a stated localisation criterion, aggregated as F1 | the gate for small classes |
| Is the centreline right? | clDice | recommended by FP2.3/FP3.3 |
| Is the volume overlap right? | DSC | keep for trunks; report but do not gate for distal branches |
| Is the boundary right, allowing for annotation slop? | NSD with τ from inter-rater variability | τ must be reported |
| How far wrong on average? | MASD (mm) | replaces the plan's "AHD" as the named metric |
| How far wrong at worst? | HD95 (mm) | already implemented; needs a finite worst-case bound |
| Is the topology right? | Betti-0 error / connected-component count vs expected | see the topology note |
| Are branches confused with each other? | per-segment confusion matrix | framework asks for the full confusion matrix |

## What this implies for [[Training plan]]

- Cite Metrics Reloaded for the metric pool; the "Evaluation" paragraph is
  already consistent with it and should say so.
- Rename "AHD" to **MASD** and define it, or state explicitly that AHD means the
  ImageCAS average symmetric surface distance and is kept for comparability with
  their Table 4. Do not report bare HD.
- Add the NSD tolerance as an explicit, reported parameter, and say it will be
  set from the annotation overlap set rather than left at 1.5 mm.
- Add "confidence intervals on every per-class metric" and "per-case raw values,
  not just means" to the evaluation section.
- State the NaN policy in two halves (absent–absent excluded; one-sided absence
  scored at the worst bound), because the current code and the framework
  disagree and the disagreement is resolvable.
