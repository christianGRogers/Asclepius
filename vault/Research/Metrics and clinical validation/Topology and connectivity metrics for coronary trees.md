---
aliases: [Betti error, Topology metrics, Connected component metrics, Betti matching]
tags: [research, evaluation, metrics, topology, coronary, literature]
status: evidence-collected
updated: 2026-09-19
---

# Topology and connectivity metrics for coronary trees

[[Training plan]] asks for "connected-component count against expected" and
[[Which metrics to report for thin tubular multiclass segmentation]] derives,
from Metrics Reloaded, that clDice "can be complemented by application-specific
connectivity metrics" for tubular structures. This note is the connectivity
metric itself: what Betti-number error measures, its published failure mode,
and the fix (Betti matching error) that a 2023–2024 line of work supplies.

**Short answer.** Betti-0 error (connected-component count mismatch) is cheap,
already adopted by the closest published analogue to our task (TopCoW) and by
ImageCAS-X on our exact cohort, and should be the default. But it is
**cancellation-blind**: a model that drops one real branch and hallucinates an
unrelated fragment elsewhere scores the same Betti-0 error as a perfect
prediction, because plain Betti counting has no notion of *which* component
went missing. Betti matching error fixes this by requiring components to be
spatially matched before being counted, and has been demonstrated specifically
on a vessel dataset. Recommendation: report both — Betti-0 error for
comparability with TopCoW/ImageCAS-X, Betti matching error as the metric that
actually distinguishes "wrong in the way that matters" from "wrong but
cancels out."

## Sources actually read

- **TopCoW** — Yang K, Musio F, Ma Y, et al. NEJM AI 2026;3(8).
  doi:10.1056/AIdbp2500994, plus its evaluation code
  `CoWBenchmark/TopCoW_Eval_Metrics`. Already read in full for [[How to
  measure branch detection and score absent branches]]; the Betti-0
  implementation details (26-connectivity, empty-mask convention) are re-used
  here rather than re-derived.
- **Betti matching, theory** — Stucki N, Paetzold JC, Shit S, Menze B, Bauer
  U. *Topologically Faithful Image Segmentation via Induced Matching of
  Persistence Barcodes.* Proc 40th Int Conf Mach Learn (ICML)
  2023;202:32698–32714 (PMLR). Read the paper's summary/abstract and the
  method description via the PMLR listing and OpenReview page, **not the full
  PDF** — flagged as such; the specific claim used below ("resolves the
  limitations of the Betti number error … spatially correct matching") is from
  material describing the paper, not a page-numbered quote from the PDF
  itself.
- **Betti matching, efficient/3D implementation and vessel evaluation** —
  Stucki N, Bürgin V, Paetzold JC, Bauer U. *Efficient Betti Matching Enables
  Topology-Aware 3D Segmentation via Persistent Homology.* arXiv:2407.04683v1,
  2024 — **preprint, not peer reviewed.** Read in full via the arXiv HTML
  rendering (the PDF itself did not parse in this session's fetch tool).
- Class-schema/annotation agent's `Handoffs.md`
  (`vault/Research/Annotation and label efficiency/Handoffs.md`) supplied one
  fact re-used and re-attributed here: "ImageCAS-X reports Betti error and
  clDice per segment alongside DSC and ASSD; their inter-observer Betti error
  is 0.0–0.25 per segment … their best model CAS-Net has aggregate Betti error
  1.9 ± 1.5 against an inter-observer 0.2 ± 0.4." This is the same ImageCAS-X
  paper already read in full for [[State of the art on ImageCAS]]; the
  per-segment breakdown (as opposed to the aggregate 1.9/0.2/0.4 already in
  that note) was not independently re-extracted from the source table here and
  should be checked against ImageCAS-X's own Table 2/supplementary material
  before being quoted per-segment.

## Betti-0 error: what it is, and its convention in the closest published protocol

Betti-0 is the number of connected components. Betti-0 **error** per class is
`|b0(pred) − b0(gt)|`. TopCoW's implementation, already documented in [[How to
measure branch detection and score absent branches]], uses full
26-connectivity and defines an empty mask as `b0 = 0`. Two published numbers
anchor what a "good" Betti-0 error looks like on a vessel tree:

- **ImageCAS-X (our exact cohort, binary lumen)**: inter-observer Betti error
  0.4 ± 0.4 (Table 2) vs 0.2 in the running text — the internal inconsistency
  already flagged in [[State of the art on ImageCAS]] — and best model
  (CAS-Net) 1.9 ± 1.5, nnU-Net 5.6 ± 3.5. The gap between the human ceiling
  (≈0.2–0.4) and even the best model (1.9) is itself informative: humans very
  rarely disagree about *how many pieces* a coronary tree has, even when they
  disagree substantially about voxel boundaries (DSC 84.8–95.3 on the same
  trunks). Topology and overlap are measuring genuinely different failure
  modes, not two views of the same one.
- **ImageCAS-X, per-segment inter-observer Betti error**: reported in
  `Handoffs.md` as 0.0–0.25 per segment — i.e. per individual branch class,
  humans essentially never disagree on component count. This number is
  re-stated here from the handoff rather than independently re-verified
  against ImageCAS-X's table in this session; treat it as probable but
  unconfirmed pending a direct check.
- **TopoLab / MICCAI 2023** (already catalogued in [[Class schema options]] as
  a centerline-labelling work, not re-opened here): not a Betti-error source,
  noted only to avoid double-citing it as one.

## The cancellation problem, and why it matters specifically for a coronary tree

Plain Betti-0 counting has a documented weakness that is directly relevant to
a multiclass coronary model: **it has no spatial correspondence between
predicted and reference components.** A prediction that breaks a real distal
branch into two pieces (b0 = 2 where the reference has 1: error = 1) and
*separately* merges two unrelated structures elsewhere (b0 = 1 where the
reference has 2: error = 1 in the opposite direction, but summed as another
1) can land at the same aggregate Betti-0 error as a prediction with one
clean, isolated mistake. Stucki et al.'s stated motivation for Betti matching
is exactly this: the induced-matching construction forces each predicted
topological feature to be matched to the *spatially corresponding* reference
feature (via persistent homology barcodes) before counting an error, so a
component that is merely miscounted in aggregate but spatially wrong is not
treated the same as one that is genuinely, spatially correct.

For a coronary tree specifically — two or three physically separate trees per
patient, each of which can be broken by a calcified gap or falsely joined
across a bifurcation — this cancellation risk is not hypothetical. A model
that systematically drops the distal quarter of D1 (breaking it into a stub +
a disconnected remnant, +1 error) while hallucinating a spurious calcified-rib
fragment elsewhere in the same class's label (another +1 in the opposite
direction of some other class) is exactly the pattern plain Betti-0 error
cannot distinguish from a model that makes one clean mistake per case.

## The vessel-specific evidence for Betti matching

The efficient 3D implementation (Stucki et al. 2024, preprint) was tested
directly on **VesSAP**, a 3D vessel segmentation dataset (brain vasculature,
not coronary — the closest tubular-structure analogue found in this search).
Measured on a VesSAP subset, training with a Betti-matching-aware loss term
(`DiceBetti`, α = 0.01) against plain Dice loss:

| Loss | Dice ↓ (as reported; lower value in their table) | Betti matching error ↓ | clDice ↑ |
|---|---|---|---|
| Dice loss | 0.286 | 3551.0 | 0.783 |
| DiceBetti (α=0.01) | 0.315 | 2242.5 | 0.723 |
| clDice baseline | 0.297 | 2078.5 | 0.750 |

(Table reproduced as extracted from the paper via automated tooling in this
session, **not manually cross-checked against the PDF**, and the Dice
"↓ better" framing in the source is unusual — flagged rather than resolved;
do not quote these exact figures without re-verifying the table's orientation
directly.) The number that matters regardless of the table's exact
orientation is qualitative and stated in the text: Betti matching error fell
by roughly a third relative to plain Dice-loss training. This is a **loss**
result — belongs to the losses/topology agent's territory, flagged in
`Handoffs.md` — but the same paper's contribution, the **Betti matching error
metric**, is ours: it is usable purely as an evaluation number regardless of
what loss trained the model, exactly as clDice is usable as a metric
independent of whether clDice was also a loss term (see [[Why Dice misreads a
three-voxel coronary branch]]).

## What this means for our metric pool

| Metric | Answers | Caveat |
|---|---|---|
| Betti-0 error (count mismatch) | "did we get the right number of pieces" | cancellation-blind; cheap; matches TopCoW/ImageCAS-X for comparability |
| Betti matching error | "are the pieces we have the *right* pieces, spatially" | more expensive (persistent homology); no coronary-specific number published yet, only a vessel analogue (VesSAP, brain) |
| clDice | "is the centreline covered" | not topology-aware in the connectivity sense — a clDice of 1.0 does not imply zero Betti error, since clDice can be fooled by a thin bridging artefact that Betti error would also miss in the opposite direction (a spurious voxel bridge merges two skeleton fragments, raising clDice's sensitivity term while *lowering* Betti-0 count) |

The three metrics are not redundant with each other, which is itself worth
stating in a write-up: a coronary tree evaluation that reports only Dice and
clDice, without a component-count metric, cannot distinguish "the tree is
whole but slightly misshapen" from "the tree is in the wrong number of
pieces."

## What this implies for [[Training plan]]

1. **Adopt Betti-0 error with 26-connectivity** (TopCoW's convention, already
   proposed in [[Proposed changes]] item E8) as the baseline topology metric,
   for direct comparability with ImageCAS-X's own reported numbers on this
   cohort.
2. **Add Betti matching error as a second-tier topology metric**, computed at
   least for the final multiclass configuration (not every ablation — it is
   more expensive), specifically because plain Betti-0 error cannot see the
   drop-one-branch-hallucinate-elsewhere failure this project is most
   concerned about. No coronary-specific number exists to calibrate against
   yet; treat any value reported as this project's own baseline rather than a
   comparison to a published figure.
3. **State explicitly in any write-up that Betti-0, clDice and Dice measure
   different things** and a good score on one does not imply a good score on
   another — this is now evidenced by three independent metrics behaving
   differently on the same ImageCAS-X models (Betti err 5.6 vs clDice 92.3 vs
   Dice 89.8 for nnU-Net, per [[State of the art on ImageCAS]]).
4. `src/segtrain/metrics.py` needs a Betti-0 implementation (proposed as M3 in
   [[Proposed changes]]); Betti matching error is a larger addition
   (persistent homology library dependency) and should be scoped separately,
   flagged here as a new item.

See [[Which metrics to report for thin tubular multiclass segmentation]],
[[How to measure branch detection and score absent branches]] and [[Proposed
changes]].
