---
aliases: [STAPLE, Label fusion, Noisy label learning, Multi-rater fusion]
tags: [research, annotation, label-fusion, noisy-labels, segqueue, literature]
status: draft
updated: 2026-09-19
---

# Fusing multiple annotations and learning from noisy labels

SegQueue will, by design, sometimes hold two or more annotations of the same
case — blind duplicates, gold-case re-annotation, and any arbitration re-work
(`src/segqueue/policy.py`: `duplicate_rate = 0.05`). Two questions follow: how
should those multiple annotations become one training label, and — the deeper
version of the same question — how should a model be trained at all when every
label it sees, single or fused, carries some annotator error? Companion notes:
[[How well two annotators agree on per-branch coronary labels]] (the ceiling
these methods are fusing around), [[Sizing the overlap set and arbitrating
disagreements]], [[Detecting a drifting or bad annotator]].

## STAPLE: the standard label-fusion algorithm

**Warfield SK, Zou KH, Wells WM. *Simultaneous truth and performance level
estimation (STAPLE): an algorithm for the validation of image segmentation.*
IEEE Trans Med Imaging 2004;23(7):903–921. doi:10.1109/TMI.2004.828354.**

I could not get a working fetch of the primary text in this session (arXiv has
no copy; the journal and the Harvard CRL project page both refused automated
fetch). The description below is assembled from how STAPLE is characterised
in every secondary source I *did* read in full — Karimi et al. 2020 (below,
which cites and uses it directly), and cross-checked against several other
papers' methods sections found in search. **Treat the mechanism description as
reliable, the paper itself as unread.**

STAPLE is an expectation–maximization algorithm that takes a set of
segmentations of the same image from different raters and simultaneously
estimates (a) the most likely true segmentation and (b) a sensitivity/
specificity performance-level estimate for each rater, iterating between the
two (E-step: given current performance estimates, re-estimate the true label;
M-step: given the current true-label estimate, re-estimate each rater's
performance). The result is a probabilistic consensus segmentation, not a
per-voxel vote, and a byproduct — a performance score per rater — that is
itself useful QA signal (see [[Detecting a drifting or bad annotator]]).

Its stated advantage over majority voting is exactly that byproduct: majority
voting counts every rater equally regardless of demonstrated reliability;
STAPLE down-weights a rater who is consistently estimated to be less accurate.

## Where STAPLE was tested directly against majority voting and against learned fusion

**Karimi D, Dou H, Warfield SK, Gholipour A. *Deep learning with noisy labels:
exploring techniques and remedies in medical image analysis.* Med Image Anal
2020;65:101759. doi:10.1016/j.media.2020.101759.** Read in full via the arXiv
preprint (arXiv:1912.02911v4, March 2020); the published version is the
citation of record. Warfield is a co-author, which is worth noting given
STAPLE is his own method and the paper still finds it beaten.

Their Gleason-grading experiment (Section V-B) is the cleanest head-to-head
available: six pathologists independently graded the same prostate cancer
tissue microarray cores from the Gleason2019 challenge dataset (Cohen's kappa
among the general pathologists **0.40–0.60** on this task — verbatim, their
citation of the challenge's own reported figure). They trained a MobileNet
classifier under seven different ways of turning six noisy labels into one
training signal, then tested against a STAPLE-estimated reference truth built
from all six pathologists:

| Training label source | Cancerous vs benign acc / AUC | High- vs low-grade acc / AUC | % large errors |
|---|---|---|---|
| Single pathologist (avg of 6) | 0.80 / 0.78 | 0.65 / 0.61 | 0.07 |
| Majority vote (pixel-wise) | 0.86 / 0.87 | 0.73 / 0.74 | 0.03 |
| STAPLE | 0.84 / 0.86 | 0.73 / 0.72 | 0.03 |
| STAPLE + iMAE loss | 0.93 / 0.91 | 0.76 / 0.79 | 0.03 |
| Minimum-loss label (per-patch, pick the label giving lowest training loss) | 0.88 / 0.88 | 0.80 / 0.82 | 0.03 |
| **Annotator confusion estimation** (learn a confusion matrix per annotator jointly with the network, method of Tanno et al., their ref [94]) | **0.92 / 0.93** | **0.80 / 0.82** | **0.01** |

Dataset for every number: Gleason2019 challenge TMA cores, 5-fold
cross-validation, MobileNet classifier. Repeated with only 3 of the 6
pathologists' labels available for training and the other 3 held out to build
the test reference ("3-3" rows): the ordering is the same but the numbers all
drop a little (STAPLE 0.86/0.86, STAPLE+iMAE 0.90/0.88, annotator-confusion
0.90/0.88), which the authors attribute to the estimated truth becoming less
reliable with fewer raters.

Two things this experiment says directly to us:

1. **Plain STAPLE is not the best available option**, even though it beats a
   single rater and roughly matches majority vote. A method that *learns*
   per-annotator error jointly with the segmentation/classification model
   (annotator confusion estimation) beat it by 4–9 points and, notably, had
   the lowest catastrophic-error rate (0.01 vs 0.03) — the exact failure mode
   [[Can non-experts label vessels as well as experts]] flags as the one that
   matters most for QA.
2. **STAPLE's own inventor's group, in a 2020 review, does not recommend it as
   the default anymore.** That is a stronger statement than citing a
   competing lab's benchmark.

### Karimi's fetal-brain experiment: a large noisy dataset beat a small clean one

Karimi et al.'s third experiment (Section V-C) is closer to our situation
structurally: 65 fetuses had one manually-segmented "clean" DW-MRI image each,
while 2497 further images (11–95 per fetus) had only machine-synthesised
"noisy" segmentations at varying accuracy. Verbatim: at their lowest synthetic
noise level, "the test DSC achieved by the baseline CNN (0.889) was higher
than that achieved by the same model trained on the clean dataset (0.878),
which consisted of approximately 40 times fewer images." Their best method —
training two CNNs and iteratively relabelling the noisy set from each other's
predictions plus the original noisy label, whichever gave lower loss — beat
both, and specifically reduced HD95 (worst-case error), not just mean Dice.

Read against our plan: the binary lumen model's presegmentations plus
annotator correction produce something structurally identical to Karimi's
"noisy dataset" (see [[Seeding annotation with model predictions and label
efficiency]]) — machine output, human-corrected, imperfect. This experiment is
direct evidence that training on a much larger corrected-but-imperfect set can
outperform training on a small, fully-curated one, which bears on how much we
should worry about small residual annotation error once volume is high.

## The taxonomy of methods for training on noisy labels

Karimi et al.'s six categories (their Table I), which cover the general
machine-learning literature and then are re-surveyed specifically for medical
imaging in their Section IV:

1. **Label cleaning and pre-processing** — identify and fix or discard
   mislabelled training samples before or during training (e.g. training a
   classifier on a small clean subset to flag likely-wrong labels in the rest).
2. **Network architecture** — add a "noise layer" to the end of the network
   that models a transition matrix between true and observed (noisy) labels,
   learned jointly with the main weights.
3. **Loss functions** — replace cross-entropy with a noise-tolerant loss (MAE,
   or corrections like iMAE) that down-weights the influence of samples whose
   loss is anomalously high, on the reasoning that a well-trained model's high
   loss on an easy-looking example is itself evidence the label is wrong.
4. **Data re-weighting** — similar idea, implemented as a per-sample training
   weight rather than a loss-function change; often estimated with a small
   clean reference set.
5. **Data and label consistency** — exploit feature-space similarity between
   samples of the same nominal class to catch and down-weight outliers.
6. **Training procedures** — curriculum learning, co-teaching (train two
   networks, only back-propagate where they agree), knowledge distillation,
   mixup.

For us, category 2/4 (annotator confusion modelling, exemplified by Tanno et
al.'s method, above) has the best direct evidence on a segmentation-adjacent
task, and category 3 (noise-robust loss, e.g. MAE/iMAE) is the cheapest to try
first since it requires no change to the labels or the data pipeline, only the
loss function — which sits next to the clDice/cbDice loss experiment
[[Training plan]] already lists as open.

### One further relevant finding: rater bias, not just rater noise, is amplified by training a DNN on it

**Shwartzman O, Gazit H, Shelef I, Riklin-Raviv T. *The Worrisome Impact of an
Inter-rater Bias on Neural Network Training.* arXiv:1906.11872v2, 2020
(eess.IV, MICCAI-workshop style preprint; venue of record not stated on the
preprint itself — treat as a preprint).** Read in full via the arXiv PDF.

Two datasets: 21 MS-lesion MRI scans each labelled by two raters of different
experience (4 vs 10 years), and 28 ICH CT scans each labelled once manually
and once by "an interactive segmentation tool" whose "proposal segmentation
[was] generated automatically, following its correction based on mouse
clicks" from the user — i.e. a presegmentation-plus-correction workflow
structurally identical to what SegQueue will run. Training identical 3D U-Nets
on each rater's labels and testing cross-rater, they report a **systematic,
consistent underestimate of MS-lesion load** when the network is trained on
the less experienced rater's annotations, and state that this bias "is
amplified and becomes more consistent" in the network's *predictions*
compared with the raw annotations it was trained on — the DNN did not average
out the rater's bias, it sharpened it. The same held for the ICH
manual-vs-tool-assisted comparison: "differences in ICH volumes calculated
based on outputs of identical DNNs, each trained on annotations from a
different source[,] were more consistent and larger than the differences
between the manual and semi-manual annotations used for training."

This is a different failure mode than random noise (which fusion and
noise-robust losses target): a **consistent, one-directional bias in one
annotator's habits does not average away — it gets amplified once a network
generalises from it**, and it shows up more clearly in the network's outputs
than in the raw labels themselves. Practically: a classifier-DNN trained to
tell which rater produced a set of labels performed *better* when given
network *predictions* trained on each rater than when given the raters' raw
annotations — meaning the bias becomes more, not less, detectable after
training, which is a usable QA signal (see [[Detecting a drifting or bad
annotator]]) but also a warning that a systematically-biased annotator's
labels will not be diluted away by pooling with others; they need to be caught
and corrected at the source.

## What this implies for [[Training plan]]

- SegQueue's blind duplicates and gold cases should not be reduced to a single
  scalar (mean Dice against each other or against the gold reference) and
  discarded. They are exactly the raw material STAPLE, majority vote or
  annotator-confusion estimation need, and Karimi's result says the third
  option is worth building even though it is more engineering than the other
  two: it is the only method in the one directly comparable experiment that
  both scored highest and made the fewest catastrophic errors.
- If effort only allows one method for the final training label on cases with
  more than one annotation, **prefer majority vote over plain STAPLE** for
  this project specifically: in Karimi's experiment they tied or majority
  vote edged ahead, and majority vote requires no extra estimation step,
  which matters given [[Training plan]]'s per-branch classes are frequently
  absent (STAPLE's sensitivity/specificity performance model was built for a
  present/absent binary structure per rater, and its behaviour on a class
  that is legitimately empty in most cases is not validated by anything I
  read).
- A noise-robust loss (MAE-family, or a mixture with Dice+CE) is a cheap
  standing experiment, in the same spirit as the loss-function items already
  open in [[Training plan]] (owned by the loss agent — flagged in
  [[Handoffs]], not decided here).
- The Shwartzman finding is a concrete argument for [[Detecting a drifting or
  bad annotator]]'s recommendation to track per-annotator systematic direction
  of error (not just magnitude), and for never letting one annotator's
  volume of submitted cases grow large before that check runs — a consistent
  bias compounds with scale in exactly the way random error does not.
