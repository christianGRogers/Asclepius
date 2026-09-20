---
aliases: [Class count vs sample size, Learnable class granularity, How many classes]
tags: [research, class-schema, coronary, sample-size, literature]
status: draft
updated: 2026-09-19
---

# How many classes remain learnable given roughly 1000 cases

[[Class schema options]] recommends 14 classes + background on the grounds
that it is the SCCT model with only non-reproducible cuts removed and labels
already exist for 800 of our cases. This note asks the question from the
other direction: independent of what schema is anatomically "correct," what
does the literature say about how many classes a cohort of roughly 1000 CCTA
volumes can actually support, and where does our 14-class choice sit against
that? Companion note: [[Seeding annotation with model predictions and label
efficiency]] in the annotation folder, which asks the same question about
total case count rather than class count.

## There is no published rule, and I did not find one pretending to be a rule

Searched directly for a general minimum-examples-per-class heuristic for
medical image segmentation and for nnU-Net's own behaviour on long-tailed
class distributions specifically; neither produced a citable number. The
class-imbalance literature (a 2025/2026 review found in search, not read in
full — flagged) documents the *problem* — "class imbalance... leading to
biases... causing models to overlook or misclassify minority classes" — and
the standard *mitigations* (resampling, cost-sensitive loss, augmentation,
transfer learning), all of which [[Training plan]] §5 already lists as a
standing experiment (class-balanced, vessel-anchored patch sampling). None of
that literature gives a number like "N examples of a class are enough." The
honest position is that this has to be read off the one directly relevant
measurement we have — ImageCAS-X's own per-class results — rather than a
general rule.

## What published multiclass CCTA segmentation papers actually chose, and why

Extending the table already in [[Class schema options]] with two papers read
this session, both from CCTA voxel/segment classification rather than
centerline labelling:

| Work | Classes | Cases (labelled) | Why they chose that granularity, in their own words |
|---|---|---|---|
| ImageCAS-X 2026 | 14 + background | 800 (560/80/160 split) | SCCT 18-segment model, collapsed proximal/mid/distal because "they depend on side branch positions which are highly variable" (already quoted in [[Class schema options]]) |
| **Kim et al. 2025**, J Med Imaging 12(1):016002, doi:10.1117/1.JMI.12.1.016002 | **3** (LAD, LCx, RCA only) | 140 internal (91 train/23 val/26 test) + 73 external test | Explicitly "focused on these three branches rather than the complete coronary tree, emphasizing clinical significance over comprehensive coverage" (extraction verified against the PMC full text, PMC11831809) |
| **Föllmer et al. 2024**, Insights Imaging 15:250, doi:10.1186/s13244-024-01827-0 | 13 segments (SCCT-derived, non-contrast calcium scoring, not lumen segmentation) | 1514 patients (455 test) | Explicitly *reduced* from the full 16-segment SCCT model because "differentiation of side branches such as segment 12 (first obtuse marginal) and segment 14 (second obtuse marginal)... is very challenging on non-contrast CT" — a modality-driven reduction, not a sample-size-driven one, but the same direction of pressure |
| SCCT 2014 reporting model | 18 | n/a — a reporting convention, not a trained model | Clinical completeness; not constrained by any training-sample argument |

The pattern across every paper that actually trained a model, not just wrote a
reporting standard, is **fewer classes than the clinical reporting standard
defines**, and every one of them states a reason — either "the boundary
criterion is not reproducible" (ImageCAS-X), "the modality cannot resolve it"
(Föllmer), or "clinical significance over comprehensive coverage" (Kim et
al.) — none of which is "we did not have enough cases," stated as such,
though the Kim et al. reduction (3 classes on 140 cases) versus ImageCAS-X's
(14 classes on 800 cases) is at minimum *consistent with* a class-count/
sample-size trade-off even where the authors frame it as a clinical choice.

## The one number we actually have: per-class effective sample size in ImageCAS-X

Already tabulated in full in [[Class schema options]] and [[How well two
annotators agree on per-branch coronary labels]]; restated here specifically
against the "is this class learnable" question, sorted by *n* (cases in which
the class is present, out of 160 test cases — train/val proportions assumed
similar since ImageCAS-X does not report per-split per-class counts):

| Class | Presence rate (test, n/160) | Human inter-observer DSC |
|---|---|---|
| LAD, RCA | 100% | 92–95 |
| LCx | 99% | 85 |
| LM, D1 | 97% | 92 / 80 |
| R-PDA | 94% | 83 |
| R-PLA | 92% | 84 |
| OM1 | 83% | 74 |
| IM | 27% | 81 |
| D2 | 57% | 83 |
| OM2 | 29% | 78 |
| Other | 9% | 81 |
| L-PLA | 6% | 71 |
| L-PDA | 5% | 75 |

Reading this as an "is it learnable" curve rather than an "is it present"
curve: **presence rate and human DSC are not the same axis, and they diverge
in an informative way.** L-PDA is present in only 5% of cases yet humans agree
on its boundary reasonably well (75 DSC) *when it exists* — the difficulty
there is presence detection (is this a left-dominant heart at all), not
boundary drawing. OM1, by contrast, is present in 83% of cases — plenty of
training examples — yet has one of the worst human agreement scores (74 DSC),
because the difficulty there is genuinely boundary ambiguity (where does OM1
end and OM2 begin), not scarcity. **A class schema decision driven only by
"is there enough data" would keep OM1 (common) and might drop L-PDA (rare);
the evidence says the opposite classes are the risk** — OM1's problem is not
fixable by more data because it is a human-agreement ceiling problem, while
L-PDA's problem *is* a data problem and *is*, in principle, fixable by
targeted case selection (see [[Seeding annotation with model predictions and
label efficiency]] §"stratify by dominance").

## Kim et al.'s data-scaling curve, as indirect evidence

Not a labelled-class-count scaling study, but the nearest thing found to a
scaling curve for this exact cohort: their self-supervised pretraining
ablation on ImageCAS (1000 volumes, unlabelled for this purpose) found
performance gains "plateaued beyond 600 volumes." That is evidence about
representation learning, not about how many *labelled per-branch* examples a
class needs, and should not be over-read as answering this note's question —
it is included because it is the only case-count-vs-performance curve
available on our exact dataset, and it puts an upper bound of sorts on how
much unlabelled volume is worth having: beyond ~600 cases, additional volume
without labels stopped helping their pretraining task.

## Where this leaves the 14-class recommendation

Nothing here contradicts [[Class schema options]]'s recommendation. What it
adds:

1. **14 classes is not an outlier choice** — it is within the range other
   groups have shrunk to from the 16–18-class clinical standard, and the two
   papers that went coarser (Kim et al. to 3, Föllmer to 13-but-non-contrast)
   both gave modality- or reproducibility-driven reasons, which is the same
   reasoning ImageCAS-X used to go from 18 to 14, just applied less
   aggressively.
2. **The two rarest classes (L-PDA, L-PLA) are a genuine open risk**, not
   because 14 is too many classes in general but because those two
   specifically sit at ~5% prevalence with no scaling argument that adding
   more *randomly selected* cases fixes it — only targeted selection does
   (already proposed in [[Seeding annotation with model predictions and
   label efficiency]]).
3. **A further reduction below 14 should not be justified by "not enough
   data"** without checking which axis (presence rate or boundary agreement)
   is actually the constraint for the specific class being considered for
   removal — the OM1/L-PDA contrast above shows the two axes point in
   different directions.

## What this implies for [[Training plan]]

- No change to the schema decision. This note supplies the sample-size
  reasoning [[Class schema options]]'s recommendation did not fully spell out,
  and narrows the open risk to two named classes rather than "the schema in
  general."
- Reinforces [[Proposed changes]] item 2c (derived-dominance sanity check) and
  the annotation folder's proposal to stratify case selection by predicted
  dominance — both are now supported by a second, independent line of
  reasoning (presence-rate scarcity is fixable by selection; boundary-
  agreement scarcity is not).
