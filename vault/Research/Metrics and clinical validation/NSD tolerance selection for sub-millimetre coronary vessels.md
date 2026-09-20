---
aliases: [NSD tolerance, Surface Dice tolerance, tau selection]
tags: [research, evaluation, metrics, coronary, literature]
status: evidence-collected
updated: 2026-09-19
---

# NSD tolerance selection for sub-millimetre coronary vessels

[[Which metrics to report for thin tubular multiclass segmentation]] already
establishes, from Metrics Reloaded, that the NSD tolerance τ "can be set
according to the inter-rater variability" and flags
`DEFAULT_NSD_TOLERANCE_MM = 1.5` in `src/segtrain/metrics.py` as indefensible
at coronary spacing. This note supplies the operational method for deriving τ
from data, evidence for what values comparable projects have actually used,
and a concrete interim recommendation until our own annotation-overlap set
exists.

**Short answer.** The published method for choosing τ (Nikolov et al.,
DeepMind/Google, head-and-neck radiotherapy) is: **τ = the 95th percentile of
minimum surface distances between two independent expert annotations of the
same structure**, computed per structure. We do not yet have that number for
any coronary branch. Until we do, the defensible interim value is **one voxel
at native spacing (≈0.35 mm)** — tighter than any general-purpose default in
the literature, which is the correct direction to err for a structure whose
whole diameter is 3–6 voxels, but every NSD number reported before the
annotation-overlap set exists must be labelled as provisional and carry its τ
explicitly.

## Sources actually read

- **Metrics Reloaded** — already read in full for [[Which metrics to report
  for thin tubular multiclass segmentation]]; DG7.1's guidance ("can be set
  according to the inter-rater variability or, if not available, heuristics")
  is the framework-level instruction this note operationalises.
- **Nikolov S, Blackwell S, Zverovitch A, et al.** *Deep learning to achieve
  clinically applicable segmentation of head and neck anatomy for
  radiotherapy.* Published as Nikolov S, et al. *J Med Internet Res*
  2021;23(7):e26151. doi:10.2196/26151 (preprint: arXiv:1809.04430). **Not
  independently opened in this session** — both the JMIR page and the arXiv
  PDF failed to return readable content to this session's fetch tooling (the
  PDF exceeded the tool's size handling; the JMIR HTML returned empty). The
  operational method quoted below (95th-percentile-of-minimum-surface-distance)
  is taken from a **secondary source** — a paper (found via web search, not
  independently opened either, so not separately citable here) that states it
  used "values for τ … taken from Nikolov et al. … calculated per organ at
  risk using the 95th percentile of minimum surface distances between
  segmentations created by two expert observers." This is a **two-hop
  citation**: flagged clearly, and the Nikolov paper itself should be read
  directly before this method is presented as verified in any manuscript.
- Search-level corroboration (not individually opened, so not citable):
  multiple 2020s papers found via search using NSD/surface-Dice tolerances in
  the 1–1.5 mm range (≈3 voxels at typical 0.5 mm-class spacing) as a
  heuristic default when no inter-rater number was available — consistent
  with, and the likely origin of, the 1.5 mm default already in
  `src/segtrain/metrics.py`.

## The method: τ from inter-rater variability, operationalised

The two-step recipe, as described (via the two-hop citation above):

1. For a pair of independent expert annotations of the same case, compute,
   for every point on annotator A's surface, the distance to the *nearest*
   point on annotator B's surface (and vice versa) — this is exactly what
   `src/segtrain/metrics.py`'s `surface_distances()` already computes for
   Dice/NSD/HD95.
2. Take the **95th percentile** of that pooled distance distribution, per
   structure, across an inter-rater overlap set. That becomes τ for that
   structure: boundary disagreement at or below the level 95 % of genuine
   expert-vs-expert disagreement falls under is treated as noise, not error.

This is a *per-structure* number by construction — a trunk (LM, wide,
easy to trace) and a distal branch (3–4 voxels, hard to trace) are expected to
get **different** τ values, which matches this project's per-class evaluation
design far better than a single global tolerance would.

## Why 1.5 mm (the code's current default) is the wrong order of magnitude here

`DEFAULT_NSD_TOLERANCE_MM = 1.5` in `src/segtrain/metrics.py` reads, in the
module's own docstring, as "one voxel at 1.5 mm isotropic … about the level of
agreement two human annotators would reach" — a heuristic built for
whole-body, TotalSegmentator-class data. At our native ~0.35 mm spacing:

- 1.5 mm ≈ **4 voxels**.
- A distal branch at 1.5–2 mm diameter (already the number [[Training
  plan]] uses to describe "a few voxels") is **itself** only 4–6 voxels across.
- An NSD computed with τ = 1.5 mm would therefore certify a boundary as
  "within tolerance" even when the predicted lumen is offset by nearly the
  vessel's own radius — enough to silently pass a systematically over- or
  under-thick lumen through the metric undetected, which is precisely the
  failure mode [[What downstream coronary tasks need from a segmentation]]
  identifies as breaking FFR-CT (diameter error compounds as the fourth power
  in flow resistance).

At one voxel (≈0.35 mm), τ is well under a single vessel radius for every
class except perhaps the largest trunk segments, which is the direction
Metrics Reloaded's heuristic fallback implies when no inter-rater number
exists ("if not available, heuristics" — the paper does not specify which
heuristic, so "tightest defensible default for the structure size" is a
reasoned choice, not a cited one).

## What ImageCAS-X's numbers imply, indirectly

ImageCAS-X does not report NSD as such (its reported metrics are DSC, HD95,
Betti error and clDice — see [[State of the art on ImageCAS]]), so it cannot
directly supply τ. But its HD95 numbers give an indirect sanity check: human
inter-observer HD95 on binary lumen is **2.46 mm** (Table 2), which — if
interpreted loosely as "95 % of boundary disagreement falls within about this
distance," the same population statistic NSD's τ is built from at a stricter
percentile framing — is over six voxels at native spacing. This is *not* the
same computation as Nikolov's per-surface-point 95th percentile (HD95 is a
directed maximum-based statistic per case, not a pooled per-point one), so it
should not be read as "the" τ, only as evidence that the eventual
inter-rater-derived τ for trunk classes will likely land somewhere in the
low-single-digit-mm range, not at one voxel — meaning the one-voxel interim
default is almost certainly **too tight** for trunks and roughly right or
still generous for the thinnest distal branches. This asymmetry is exactly why
a single global τ is wrong and a per-class one, once measurable, is needed.

## What this implies for [[Training plan]]

1. **The NSD tolerance is not a single number for this project.** State this
   explicitly in the evaluation section, replacing the current single
   `DEFAULT_NSD_TOLERANCE_MM`.
2. **Interim default: one voxel (native spacing, ≈0.35 mm) for every class**,
   documented as provisional, until the annotation-overlap set — already being
   sized by the annotation-protocol agent — produces a real per-class
   inter-rater distance distribution. Report τ next to every NSD value; an
   NSD without its τ is uninterpretable (already stated in [[Which metrics to
   report for thin tubular multiclass segmentation]], restated here as the
   concrete number to use meanwhile).
3. **Once the overlap set exists, compute τ per class as the 95th percentile
   of pooled inter-annotator surface-point distances**, using
   `src/segtrain/metrics.py`'s existing `surface_distances()` function
   directly on annotator-pair cases — no new geometry code is needed, only a
   script that calls it on the overlap set and takes the percentile.
4. `src/segtrain/metrics.py`'s `normalized_surface_distance()` already accepts
   `tolerance_mm` as a parameter (good — no signature change needed); what is
   missing is a per-class tolerance *table* rather than one module-level
   constant, and a script to derive it from the overlap set. See [[Proposed
   changes]].

See [[Which metrics to report for thin tubular multiclass segmentation]],
[[What downstream coronary tasks need from a segmentation]] and [[Proposed
changes]].
