---
aliases: [Branch detection rate, Absent class scoring, TopCoW conventions]
tags: [research, evaluation, metrics, coronary, literature]
status: evidence-collected
updated: 2026-09-19
---

# How to measure branch detection and score absent branches

[[Training plan]] asks for a "branch detection rate (was the vessel found at
all)" but does not define it, and the class schema will contain branches that
are simply absent in many patients (ramus intermedius; left-dominant PDA/PLV).
Both problems are solved, published and coded in a peer-reviewed multiclass
vessel benchmark, so we should adopt that convention rather than invent one.

## Source

**Yang K, Musio F, Ma Y, Juchler N, Paetzold JC, et al. "The TopCoW Challenge —
Topology-Aware Circle of Willis Segmentation for CT and MR Angiography."
NEJM AI 2026;3(8). doi:10.1056/AIdbp2500994** (open access via PMC13496301;
earlier preprint arXiv:2312.17670). The evaluation code is
`CoWBenchmark/TopCoW_Eval_Metrics` on GitHub, which I read directly; quotations
marked *(code)* are verbatim from that repository's `topcow24_eval/` tree.

Why this benchmark and not a coronary one: TopCoW is the closest published
analogue to our task — **multiclass, per-vessel, thin tubular, with
variably-present classes** (13 Circle-of-Willis components on CTA and MRA, some
of which are anatomically absent in a large share of patients, exactly like the
ramus intermedius). No coronary benchmark I have found publishes a per-branch
voxel multiclass evaluation protocol. The anatomy differs; the *evaluation
problem* is the same one.

## The metric set they used

> "the multiclass CoW segmentation predictions were evaluated using Dice
> similarity coefficient (Dice score), centerline Dice, Hausdorff distance at
> 95th percentile, and connected component error."

plus "average F1 score for detection" of the variably-present components and a
variant-classification accuracy. Note the shape: **overlap + centreline +
distance + topology + detection**, which is the same five-way pool that
[[Which metrics to report for thin tubular multiclass segmentation]] derives
independently from Metrics Reloaded. Two independent routes arriving at the same
pool is about as much corroboration as this kind of question gets.

## Detection: the definition to copy

> "Positive detection was defined as at least 25% intersection over union
> between the predicted and ground truth masks."

And in the code *(code, `constants.py`)*: `IOU_THRESHOLD = 0.25`, with the
four-way assignment in `detection_grp2_labels.py`:

- label present in ground truth and IoU ≥ 0.25 → **TP**
- label present in ground truth and IoU < 0.25 → **FN**
- label absent from ground truth but present in prediction → **FP**
- label absent from both → **TN**

F1 is then aggregated over cases per class. Three things this gets right for us:

1. **It is a per-class, per-case binary decision**, so "did we find the ramus"
   is measured on the cases where a ramus exists and is not diluted by the 73 %
   where it does not.
2. **It counts TN.** A model that correctly predicts no left PDA in a
   right-dominant patient is rewarded. Any metric pool without TN turns
   "correctly absent" into "no information", and with dominance-dependent
   classes that is most of the dataset.
3. **The threshold is loose on purpose.** IoU ≥ 0.25 for a 3-voxel tube is
   "found the right vessel in roughly the right place", not "outlined it well".
   Metrics Reloaded supports this explicitly: "recommendation of lower object
   detection localization threshold in case of small sizes" (FP3.1) and again
   for high size variability (FP3.2).

IoU ≥ 0.25 is nevertheless a hyperparameter someone chose, not a derived
quantity; Metrics Reloaded calls threshold choice a pitfall in its own right
([P3.1], "Suboptimal choices of hyperparameters"). We should report detection F1
at 0.25 for comparability with TopCoW **and** at a second, stricter value
(0.5) so the sensitivity of the conclusion to the threshold is visible.

## Scoring a class present in only one of the two masks

From the code *(code, `cls_avg_dice.py`)*:

> "If not, DSC is automatically set to 0 due to FP or FN"
> `if (not np.any(gt_label_arr)) or (not np.any(pred_label_arr)): return 0`

and `HD95_UPPER_BOUND = 90` *(code, `constants.py`)* — a fixed 90 mm stand-in
so a one-sided absence contributes a finite, worst-case distance instead of
infinity or a silent drop. That is Metrics Reloaded's NaN rule ("setting the
corresponding metric value to the worst possible value […] the image diagonal
can be chosen") given a concrete implementation.

For Betti-0 *(code, `cls_avg_b0.py`)*: 26-connectivity
(`N26 = 3  # full connectivity of input.ndim is used`), an empty mask has
`b0 = 0`, and the per-class error is `Betti_0_error = abs(pred_b0 - gt_b0)`.

For clDice *(code, `clDice.py`)*: skeletons from scikit-image
(`skeletonize` in 2D, `skeletonize_3d` in 3D), `cl_score` returns 0 when a
skeleton is empty, and clDice is the harmonic mean
`2 * tprec * tsens / (tprec + tsens)`, returning 0 when the denominator is 0.

**One detail I could not fully verify:** `generate_cls_avg_dict.py` carries the
comment "returned cls_avg_dict only considers all labels (classes) that are
present in both gt and pred to compute the class-average-metric per case", which
reads as an intersection, while `cls_avg_dice.py` scoring a one-sided label as 0
only makes sense if the label set is the **union**. I did not read
`extract_labels()` itself. Treat the union reading as probable but unconfirmed;
if we adopt this, we implement the union explicitly rather than inheriting the
ambiguity.

## Published numbers, and what they are not

From the paper: top teams reached "over 90% Dice similarity coefficient scores"
on CoW components, "over 80% F1 scores for detecting key vessel components", and
"over 70% balanced accuracy in CoW variant classification"; median Dice was
"above 80% across modalities and test sets". Inter-rater agreement on 40 CTA
cases was reported for *variant classification*, not segmentation: "Balanced
accuracies between the raters were 88% for AV and 78% for PV. Cohen's kappa
scores were 83% for AV and 72% for PV." The paper points to a supplementary
section (S7) for voxel-level inter-observer agreement, which I did not retrieve.

These are brain arteries on CTA/MRA. **They are not a target for coronaries**
and must never be quoted as one in our write-ups — they calibrate what a
well-run multiclass vessel benchmark looks like, nothing more. The one
transferable observation is directional and matches the coronary literature:
large components segment near 90 % Dice, the small variably-present ones do not,
and the authors fall back to detection F1 for exactly those.

## Proposed operational definition for us

Per case, per class *c*:

- `present_gt = |ref_c| > 0`, `present_pred = |pred_c| > 0`
- detection outcome by the TopCoW four-way rule at IoU ≥ 0.25 (report 0.5 too)
- Dice, clDice, NSD(τ): computed when both present; **0** when exactly one is
  present; **skipped** when neither is present
- HD95 and MASD: computed when both present; a fixed worst-case bound when
  exactly one is present (90 mm is TopCoW's choice; for a heart-sized field of
  view our own bound should be stated and justified, not inherited); skipped
  when neither
- Betti-0 error with 26-connectivity, empty mask ⇒ b0 = 0
- **Branch detection rate** = per-class recall over cases where the branch is
  present in the reference (this is the quantity [[Training plan]] names);
  **detection F1** = the aggregate that also punishes hallucinated branches.
  Report both: recall alone can be gamed by predicting every class everywhere.

Per class over the test set: detection F1, recall, the count of cases present,
and the distribution (not just the mean) of every continuous metric.

## What this implies for [[Training plan]]

- Define "branch detection rate" in the plan as per-class recall at IoU ≥ 0.25
  with the TopCoW four-way rule, and add detection F1 beside it. Cite Yang et
  al., NEJM AI 2026.
- Add the absent-class scoring rule to the plan explicitly (one-sided absence
  scored at the worst value; absent-in-both skipped, not scored 0), because this
  is the rule that decides whether the ramus intermedius class looks good or
  catastrophic, and it must be fixed before any number is quoted.
- `src/segtrain/metrics.py` needs: detection outcomes and IoU per class, a
  finite worst-case bound for one-sided absence in `hausdorff95`, Betti-0 /
  component counting, and clDice. See [[Proposed changes]].
