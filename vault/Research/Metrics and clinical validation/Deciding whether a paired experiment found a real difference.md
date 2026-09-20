---
aliases: [Statistical comparison of runs, Paired model comparison, Is the difference real]
tags: [research, evaluation, metrics, statistics, coronary, literature]
status: evidence-collected
updated: 2026-09-19
---

# Deciding whether a paired experiment found a real difference

[[Training plan]] §3/§5 schedules several paired experiments on the same
fold — ResEnc vs plain U-Net, heart-crop vs no-crop, binary-init vs
from-scratch, rotation-ablation vs default — but nowhere states how the plan
will decide a difference is real rather than noise. This note collects what is
published on that decision for segmentation benchmarks specifically, and gives
a concrete procedure built from `src/segtrain/evaluate.py`'s existing
`wilcoxon()` helper.

**Short answer.** Use a **paired, per-case test** (Wilcoxon signed-rank, which
`src/segtrain/evaluate.py` already implements) plus a **bootstrap confidence
interval on the paired difference**, computed by resampling test *cases* (not
pooled metric values) with replacement — never compare two single numbers.
Two independent literatures back this: the segmentation-metrics literature
(Metrics Reloaded, already in [[Which metrics to report for thin tubular
multiclass segmentation]]) warns that rankings are unstable under
resampling and aggregation choice; the ML-benchmarking literature (Bouthillier
et al. 2021) shows that seed-to-seed variance alone can exceed a published
"improvement." nnU-Net's own validation protocol (already read in full for
[[Research context]]) already does the bootstrapped-ranking version of this on
ten Decathlon datasets, so this is not a new standard for the plan to adopt —
it is the standard the plan's own reference method already uses, made
explicit for our case.

## Sources actually read

- **Metrics Reloaded** — Maier-Hein L, Reinke A, et al. Nat Methods
  2024;21(2):195–212. doi:10.1038/s41592-023-02151-z. Already read in full for
  [[Which metrics to report for thin tubular multiclass segmentation]];
  re-cited here for its ranking-stability guidance specifically.
- **Reinke et al., metric pitfalls** — Nat Methods 2024;21(2):182–194.
  doi:10.1038/s41592-023-02150-0. Already read in full for [[Why Dice misreads
  a three-voxel coronary branch]]; the [P3.4] pitfall on box plots and
  non-determinism is re-used here.
- **Maier-Hein L, Eisenmann M, Reinke A, et al.** *Why rankings of biomedical
  image analysis competitions should be interpreted with care.* Nat Commun
  2018;9:5217. doi:10.1038/s41467-018-07619-7. **Abstract only read** — full
  text not opened in this session (no fetch blocker encountered; simply not
  pursued past the abstract given time budget). The one verified claim below
  is from the abstract itself, which states it directly. **Flagged for a full
  read before anything from it is quoted with page-level specificity.**
- **Bouthillier X, Delaunay P, Bronzi M, et al.** *Accounting for Variance in
  Machine Learning Benchmarks.* Proc Mach Learn Syst (MLSys) 2021;3.
  arXiv:2103.03098. **Abstract and author's own summary page read, not the
  full PDF** — the PDF returned as unparsable binary in this session. The one
  verified claim below (that seed/init/hyperparameter variance alone can
  exceed the between-method gap) is from the abstract and summary and is
  **not quoted with the paper's own CIFAR-10 numbers**, because those numbers
  were not independently verified here. Flagged for a full read before citing
  specific figures.
- **nnU-Net** — Isensee et al., preprint arXiv:1904.08128v2. Already read in
  full for [[Research context]]; the bootstrapped-ranking protocol (Figure 6,
  nine blueprint variants ranked on ten Decathlon datasets) is re-used here as
  worked practice from a method this plan already adopts wholesale.
- `src/segtrain/evaluate.py` (`wilcoxon()`) and `src/segtrain/metrics.py`
  (`aggregate()`, `nanmean()`) — read as code, not a citation; see "What the
  code already has" below.

## What "a real difference" requires, and why a single mean is not enough

Three independent problems compound if a paired experiment is judged on two
headline Dice numbers:

1. **Per-case values are correlated within a case and across structures**, so
   an unpaired test (or eyeballing two means) throws away the exact structure
   that makes a paired test powerful: both configurations were scored on the
   *same* cases, so case-level difficulty (a heavily calcified scan, a
   left-dominant patient) should be differenced out, not averaged over twice.
   This is the same aggregation principle Metrics Reloaded states for
   per-image vs pooled metrics (already quoted in [[Which metrics to report
   for thin tubular multiclass segmentation]]: "pixels of the same image are
   highly correlated … metric values should first be computed per image").
2. **Rankings are sensitive to aggregation and resampling choice.** Metrics
   Reloaded's own pitfall table states directly (already quoted in [[Why Dice
   misreads a three-voxel coronary branch]]): rankings "are highly sensitive
   to altering the metric aggregation operators, the underlying data set, or
   the general ranking method." Maier-Hein et al. 2018's abstract states the
   same conclusion at competition scale: "the rank of an algorithm is
   generally not robust to a number of variables such as the test data used
   for validation, the ranking scheme applied and the observers that make the
   reference annotations." Two independent papers by an overlapping author
   group, five years apart, reaching the same conclusion from different
   angles (metric pitfalls vs challenge rankings) is reasonably strong
   corroboration even though neither gives us a number to plug in directly.
3. **Training-run variance (seed, init, data order) is a real confound**, not
   just test-set noise. Bouthillier et al.'s framing (read at abstract level,
   flagged above) is that a single-seed comparison conflates "configuration A
   beats configuration B" with "this particular run of A beat this particular
   run of B," and that seed-to-seed variance in deep learning benchmarks can
   be large enough to swallow a claimed improvement. For our plan, this bears
   directly on the ResEnc-vs-plain and crop-vs-no-crop comparisons: a single
   training run per arm cannot distinguish a real architectural effect from a
   lucky seed, and neither [[Training plan]] §3 nor §5 currently commits to
   more than one run per arm.

## What the code already has, and what it is missing

`src/segtrain/evaluate.py`'s `wilcoxon(a, b)` is a correctly-implemented
paired Wilcoxon signed-rank test: it drops pairs with a NaN in either arm
(rather than imputing), and refuses a p-value ("returns `None`") when fewer
than 6 pairs remain or every pair is tied. That is the right test for
per-case Dice (bounded, non-normal, naturally paired across two runs scored on
the same held-out cases) and needs no change.

What it does not have:

- **No effect size alongside the p-value.** A Wilcoxon p-value says a
  difference is unlikely to be chance; it says nothing about whether the
  difference is clinically or practically large enough to matter — the same
  point [[Which metrics to report for thin tubular multiclass segmentation]]
  makes about decimal places ("more than one decimal number is often not
  useful given the typically high inter-rater variability"). A median paired
  difference, reported in the same units as the metric, is the minimum
  addition.
- **No bootstrap CI helper.** `wilcoxon()` answers "is there a difference";
  nothing in the module answers "how big, with what uncertainty." The
  practice found across several 2025-era medical-imaging papers in this
  search (not individually citable — these were search-synthesis results, not
  opened papers, so treated as corroborating common practice rather than as a
  source) is: **resample the set of paired cases with replacement (not the
  pooled metric values), recompute the paired difference each time, and take
  the 2.5th/97.5th percentile of the resulting distribution as a 95 % CI.**
  This resamples at the level the correlation actually lives at (the case),
  which a naive bootstrap over (case, structure) rows would violate for a
  multiclass structure, since a case's classes are not independent draws.
- **No seed-variance accounting.** Even a significant Wilcoxon result from one
  training run per arm cannot separate a configuration effect from a seed
  effect. The plan's standing experiments (§5) do not currently budget more
  than one run per arm for ResEnc-vs-plain or crop-vs-no-crop.

## A worked procedure for this project's paired experiments

For any of the plan's standing experiments (ResEnc vs plain, crop vs no-crop,
rotation ablation, binary-init vs from-scratch):

1. **Same fold, same test cases, both arms** — already the plan's design
   (§3, §5).
2. **Per case, per class**: compute the metric difference (e.g. Dice_B −
   Dice_A). Exclude a (case, class) pair only when the NaN policy from
   [[How to measure branch detection and score absent branches]] says to skip
   it (absent in both); do not silently drop one-sided-absence pairs, since
   that is the failure the experiment most needs to see.
3. **Wilcoxon signed-rank** on the paired per-case differences (already
   implemented), separately per class — not pooled across classes, for the
   aggregation reason above.
4. **Bootstrap the paired difference**: resample cases with replacement
   (≥ 1,000 resamples), recompute the mean paired difference per resample,
   report the 95 % percentile interval. An interval that excludes 0 and a
   Wilcoxon p < 0.05 should agree; when they do not (small n, ties), trust the
   bootstrap CI's shape over the point p-value.
5. **State n up front for every rare class.** L-PDA/L-PLA-scale classes
   (single digits of test cases, see [[Class schema options]]) cannot support
   either test meaningfully — report the difference and the CI width, and say
   explicitly that the class is underpowered, rather than reporting a p-value
   that implies more confidence than six data points can carry.
6. **Where budget allows more than one seed per arm** (nnU-Net's own
   Figure 6 protocol bootstraps across configurations on ten *datasets*, which
   is the multi-seed idea at challenge scale), prefer it for the
   **ResEnc-vs-plain decision specifically**, since [[Training plan]] states
   this becomes "the config" going forward — a decision with that much
   downstream weight should not rest on a single training run per arm if the
   24-hour walltime budget can stretch to two.

## What this implies for [[Training plan]]

1. **Add a decision rule to §5** for every standing experiment: paired
   Wilcoxon per class plus a bootstrap CI on the paired difference,
   pre-registered before the runs finish (i.e., decide the test before seeing
   the result), rather than an informal comparison of two leaderboard numbers.
2. **Flag the single-run-per-arm risk explicitly** for ResEnc-vs-plain, given
   its stated downstream weight ("winner becomes the config"). If a second
   seed is not affordable, say so in the write-up rather than silently
   presenting a one-run comparison as decisive.
3. **Never rank classes or configurations by a pooled mean alone** — this
   restates [P3.3]/[P3.4] from [[Why Dice misreads a three-voxel coronary
   branch]] in the comparison context specifically.
4. `src/segtrain/evaluate.py` needs a bootstrap-CI helper alongside
   `wilcoxon()`; see [[Proposed changes]] (M9).

See [[Proposed changes]], [[Which metrics to report for thin tubular
multiclass segmentation]] and [[Why Dice misreads a three-voxel coronary
branch]].
