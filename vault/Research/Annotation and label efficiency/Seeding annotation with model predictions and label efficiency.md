---
aliases: [Label efficiency, Pre-segmentation bias, Pseudo-labels, Self-training, Active learning coronary]
tags: [research, annotation, label-efficiency, weak-supervision, segqueue, literature]
status: draft
updated: 2026-09-19
---

# Seeding annotation with model predictions and label efficiency

The project's actual bottleneck, per `docs/SEGQUEUE.md`: "per-segment coronary
labels that do not exist publicly." [[Training plan]] already commits to
seeding annotators with the binary lumen model's predictions ("its predictions
become the presegmentation seeds SegQueue hands annotators — splitting an
existing tree is minutes; drawing one is an hour"). This note asks the
questions that commitment raises: does pre-segmentation measurably bias what
annotators produce, what cheaper-than-full-manual routes exist between a
binary mask and per-branch labels, and how many fully-labelled cases a
multiclass model actually needs. Companion notes: [[Can non-experts label
vessels as well as experts]], [[Fusing multiple annotations and learning from
noisy labels]].

## Does pre-segmentation bias the annotator toward its own errors?

Two directly relevant experiments, from different fields, pointing in the same
direction with an important caveat between them.

### It does not cost quality, and it saves real time — outside medical imaging

**Mikulová M, Straka M, Štěpánek P, Štěpánková B, Hajič J. *Quality and
Efficiency of Manual Annotation: Pre-annotation Bias.* arXiv:2306.09307v1,
2023.** Read in full via the arXiv HTML. This is **dependency-parsing
annotation of text, not medical imaging** — cited for method and direction
only.

Design: four annotators in stable pairs annotated eight ~1,250-word datasets
under eight conditions crossing {pre-parsed by a model, from scratch} with
four levels of tool support; gold standards built by resolving disagreements.
Result, verbatim in substance: annotation accuracy "remained, more or less,
the same for both modes of annotation" (fluctuation ~0.5 points; unlabelled
attachment score 96.5% both modes, labelled attachment 95.0% pre-parsed vs
94.5% from-scratch — pre-parsed was marginally *better*, not worse). Time:
from-scratch annotation took "almost 1.7 times longer" than correcting
pre-parsed data, extrapolated to roughly 2000 hours saved per annotation pass
on their 2-million-token project. Pre-annotation also *increased* inter-
annotator agreement (their Table 3) rather than reducing it.

### It can, when the seed is trusted uncritically — and the danger compounds once a network learns from the correction

**Shwartzman O, Gazit H, Shelef I, Riklin-Raviv T. *The Worrisome Impact of an
Inter-rater Bias on Neural Network Training.* arXiv:1906.11872v2, 2020.** Full
citation and detail in [[Fusing multiple annotations and learning from noisy
labels]]. Their ICH dataset compared a fully manual segmentation against a
segmentation from "an interactive segmentation tool" whose "proposal
segmentation [was] generated automatically, following its correction based on
mouse clicks" — a presegmentation-and-correct workflow, i.e. exactly SegQueue's
design. Networks trained on the two sources diverged systematically, and the
divergence was *more* visible in the trained network's predictions than in the
raw annotation difference.

### Reconciling the two

The Mikulová result says correcting a decent pre-annotation does not, on its
own, make annotators lazier or less accurate — a genuine finding against the
"anchoring bias" worry, in a domain where the gold standard was built by
adjudicating disagreement so any drift toward the seed would have shown up as
reduced accuracy, and did not. The Shwartzman result says that when the seed
itself carries a systematic bias (their tool used a *different, less careful*
manual process, not a bad model), that bias propagates and a downstream DNN
sharpens it. The difference is not "pre-segmentation is safe" vs "unsafe"; it
is that **pre-segmentation transmits whatever bias is in the seed**, and
correcting it does not obviously catch a bias the annotator was never asked to
look for. Two concrete implications for our protocol:

- The seed matters more than the correction step. A binary lumen model
  trained to nnU-Net's usual standard (no known systematic directional bias)
  is a safer seed than, say, a fast heuristic thresholding tool would be.
- **QA has to look for bias in the direction annotators agree with the seed,
  not just disagreement with each other.** Two annotators who both trust a
  wrong seed will agree with each other and both be wrong — this is invisible
  to inter-rater agreement and only shows up against a gold reference or a
  held-out expert check (see [[Sizing the overlap set and arbitrating
  disagreements]]).

Related, already in [[Can non-experts label vessels as well as experts]]:
Rädsch et al. 2023 found the *dominant* lever on annotation quality is
picture-based instructions, and that improvement was entirely in avoiding
severe (score-zero) errors, not boundary tidiness — a presegmentation is a
kind of picture-based instruction (it shows the annotator roughly where the
vessel is), so the two findings are consistent with each other: seeding likely
helps for the same reason exemplar images help, by preventing the
"labelled the wrong thing entirely" failure, while boundary-level accuracy is
set by something else (training depth, per Skandarani 2021, also in that
note).

## Cheaper-than-full-manual routes from a binary mask to per-branch labels

Three published, directly comparable results, in increasing order of how
little supervision they need.

### Self-training from a small fraction of manually-split branches

**Zhang Z, Zhang X, Qi Y, Yang G. *Partial Vessels Annotation-based Coronary
Artery Segmentation with Self-training and Prototype Learning.* MICCAI 2023.
arXiv:2307.04472.** Read the abstract in full via the arXiv abstract page
(the PDF exceeded this session's fetch size limit; body content below is from
the abstract only — **flagged, not independently verified beyond it**).

They define "partial vessels annotation" (PVA): annotators label only some of
the vessels/branches per case (not all cases fully labelled, some fully
unlabelled — a sparse per-branch labelling budget), then a three-stage
framework (1) learns local vessel features and propagates labels into
unlabelled regions, (2) learns global tree structure from the propagated
labels and corrects propagation errors, (3) uses feature-prototype similarity
to refine test-time output. Verbatim result: "outperforms the competing
methods under PVA (24.29% vessels), and achieves comparable performance in
trunk continuity with the baseline model using full annotation (100%
vessels)." That is, roughly a quarter of the branch-labelling effort reached
parity with full per-branch annotation on their clinical CCTA data (dataset
size and institution not extracted from the abstract — **unverified,
retrieve the full text before relying on the number**).

This is the closest published analogue to our situation: it is coronary CCTA,
it is per-branch (not binary), and its whole premise — full per-branch
labelling is too expensive, so label a fraction and propagate — is our
problem statement.

### Weak, patch-level labels instead of pixel-wise ones (a different vascular tree, but the same annotation-cost argument)

**Dang VN, Galati F, Cortese R, Di Giacomo G, Marconetto V, Mathur P, Lekadir
K, Lorenzi M, Prados F, Zuluaga MA. *Vessel-CAPTCHA: an efficient learning
framework for vessel annotation and segmentation.* Preprint submitted to
Elsevier (Medical Image Analysis), arXiv:2101.09321v4, 2021.** Read the first
three pages in full via the fetched PDF; remainder not read — **method
described from the introduction and abstract only.**

Cerebrovascular tree (TOF-MRA and SWI brain angiography), not coronary. The
method: instead of pixel-wise voxel labels, an annotator only tags whether
each 2D patch of the volume contains a vessel or not (binary patch label, "in
a setup similar to the CAPTCHAs used to differentiate humans from bots"). Those
weak tags are used to (a) synthesise pixel-wise pseudo-labels via clustering
and (b) train a classifier network that both expands the labelled set further
without more human input and acts as a noise filter on low-quality patches.
Verbatim: "reducing the annotation time by ~77% w.r.t. learning-based
segmentation methods using pixel-wise labels for training," at "state-of-the-
art accuracy." Not per-branch (binary vessel/no-vessel), so it answers a
different question than ours (branch *identity*, not just presence) but is
strong evidence that binary presence tagging at the patch level is a
severalfold cheaper substitute for pixel painting when the downstream model
can be trusted to fill in the boundary.

### General framework: semi-supervised + noisy-label self-correction, not vessel-specific

**Wang S, et al. *Annotation-efficient deep learning for automatic medical
image segmentation.* Nat Commun 2021;12:5915. doi:10.1038/s41467-021-26216-9.**
Read via PMC (PMC8501087) in full.

Their AIDE framework treats semi-supervised learning (some cases unlabelled)
and unsupervised domain adaptation as special cases of noisy-label learning,
on the reasoning that a pseudo-label generated for an unlabelled case *is* a
noisy label, so one self-correction mechanism handles all three. Headline
result: on breast tumour ultrasound segmentation, "comparable segmentation
results to those obtained by fully supervised models with access to 100%
training data annotations... are achieved with AIDE by utilizing only 10% of
the annotations" (DSC 0.690±0.251 AIDE-10% vs 0.722±0.208 fully supervised,
p = 0.061, not significant). On a liver segmentation task, 30 labelled +
954 unlabelled ("97% noise" in their framing) reached DSC 86.9% against
88.5% from 331 fully labelled cases (p = 0.079, not significant). **Not
vessel or coronary-specific**; no discussion of tubular structures or of
bootstrapping a fine multiclass task from a coarse binary one — cited for the
general magnitude (roughly 10× fewer full annotations, no significant loss)
rather than for any coronary-specific number.

## How many fully-labelled cases does a multiclass model actually need?

No published number exists for *per-branch coronary* segmentation
specifically — this is the honest state of the evidence, assembled from
adjacent numbers:

- **ImageCAS-X trained and evaluated its per-branch model on 560 train / 80
  val / 160 test** (see [[Class schema options]]) and reached the per-class
  ceiling numbers reported in [[How well two annotators agree on per-branch
  coronary labels]]. That is an existence proof that ~560 fully-labelled
  cases suffices to reach human-ceiling agreement per class on this exact
  anatomy and modality — the nearest thing to a real answer we have.
- **Kim et al. 2025** (J Med Imaging 12(1):016002, doi:10.1117/1.JMI.12.1.016002
  — read via PMC, PMC11831809) ran a *data-scaling ablation for
  self-supervised pretraining*, not the labelled fine-tuning set, but the
  shape of the curve is informative: "pretraining with as few as 50 CCTA
  volumes led to modest improvement, with further gains as the pretraining
  dataset size increased," and performance "plateaued beyond 600 volumes."
  Their actual *labelled* fine-tuning set for the 3-class (LAD/LCx/RCA) task
  was small — 91 train / 23 val at the internal site — reaching internal Dice
  0.787–0.794 depending on model. That is a coarser (3-class, no branches)
  task than ours reaching a usable result on under 100 labelled cases, which
  is a lower bound in the wrong direction: it says trunks need less, not what
  branches need.
- **The general nnU-Net/segmentation data-scaling literature** (see search
  summary, not independently verified against a single paper I opened) puts
  "diminishing returns beyond several hundred cases" as a common finding
  across organ segmentation tasks with a handful of classes; our schema has
  14, several of them rare (L-PDA/L-PLA present in ~5% of cases, per
  [[Variant and absent branches]]), so **the effective sample size for the
  rarest classes, not the case count, is what should set the target** — at
  ~5% prevalence, 560 cases gives ~28 positive examples of L-PDA, which is
  already visibly unstable in ImageCAS-X's own reported ± spreads (DSC
  75.1 ± 29.0 on n=8 in their *test* set).

**Practical reading for this project:** if the ImageCAS-X import succeeds
(560/80/160, see [[Class schema options]] §"Still unverified"), the *trunk and
common-branch classes* (LM, LAD, LCx, RCA, D1, R-PDA, R-PLA — present in
≥90% of cases) are very likely adequately sampled already. The *rare classes*
(L-PDA, L-PLA, and to a lesser extent OM2/IM) will not be, regardless of how
many total cases are labelled, unless labelling is deliberately enriched
toward left-dominant and co-dominant hearts — a stratified rather than random
sampling policy for whichever cases our own annotators pick up next. This is
a concrete, checkable proposal for whoever owns fold/split policy — flagged
in [[Handoffs]].

## What this implies for [[Training plan]]

- The plan's presegmentation-seeding decision (§3) is supported by the
  Mikulová result (no quality cost, large time savings) with the Shwartzman
  caveat attached: bias in the seed is not caught by correction alone, so QA
  needs a check *against the seed*, not only inter-annotator agreement (see
  [[Detecting a drifting or bad annotator]]).
- **A pseudo-label / self-training pass is worth a scheduled experiment**,
  modelled on Zhang et al. 2023's partial-vessels-annotation result: label a
  fraction of branches per case (or fully label a fraction of cases) and
  propagate/self-train the rest, rather than assuming every training case
  needs full human per-branch correction. This is the single most direct lever
  available for cutting annotator hours, and it is coronary-specific published
  evidence, not an inference from another organ.
- **Stratify which cases get annotated first by predicted/known dominance**,
  once the binary model or a cheap heuristic can estimate it, so the rare
  L-PDA/L-PLA classes are not left to random sampling to find.
- No number in this note should be read as "N cases is enough" for our
  schema — the honest position is ~560 looks sufficient for common classes on
  this exact task (ImageCAS-X's own result) and insufficient by construction
  for the rare ones at any total N under stratification.
