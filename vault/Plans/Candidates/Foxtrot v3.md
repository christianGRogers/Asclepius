---
tags: [plans, candidate, amendments, fp-gate, round8]
author: Foxtrot
round: 8
version: 3
updated: 2026-10-11
---

# Foxtrot v3: F3 (A20) withdrawn — atlas2's FPs sit on the heart, and the ROI rule removes none of them

## 1. Thesis

Decision: **improve by narrowing.** v3 is [[Foxtrot v2]] minus F3.

- The model recipe stays the master's.
- A17a and A17b (my F1 and F2) stand.
- F4 (pretraining) stays a conditional, unscheduled proposal.

A20's second condition was pre-registered before atlas2: ≥ 25 % of raw FP components more than 25 mm from
TotalSegmentator heart ∪ aorta. **It fails.**

Evidence: [[Foxtrot - On atlas2's val FPs the heart-and-aorta ROI rule removes nothing, because the FPs sit on the heart]].

- **17 of the 80 val CTs are cached.** On those, exactly: **0 of 26** FP components lie beyond 25 mm. The
  maximum distance is 12.8 mm and the median 1.7 mm. The rule deletes 0 components. FP/case (1.53) and
  tF1 are unchanged. All 17 cases reproduce atlas2's tF1 and FP counts exactly before the rule.
- **The other 63 are unknown.** The census-only bound gives ≤ 16.8 % (run 1) and ≤ 19.2 % (B), assuming a
  reference-to-ROI maximum of 16.5 mm. They are not counted as passing.
- **`confident_other`** (94 in run 1): median 3.4 mm from the reference, and two-thirds within 5 mm. On the
  measured cases, all are within 12.8 mm of the heart. They are epicardial, not background clutter.

## 2. Changes to the recipe

1. **Remove F3/A20 from the deployed output.** The heart masks are not needed for A20 any more. A1's aorta
   producer (A21) is unaffected, and the v2 cohort-check job proposal is withdrawn with it.
2. **No replacement filter.** The confident FPs lie 1–5 mm from the tree, which is where real but
   unlabelled vessel would sit. No geometric deletion rule there can carry a "removes no reference vessel"
   guarantee, and A15 rightly forbids one without it.

## 3. What this says about A15's "reopens the recipe"

The census routes 79 % `confident_other` to a recipe change. My measurement narrows what such a change has
to explain. These FPs are **confident, epicardial, near-tree and not ImageCAS-X vessel**. Before anyone
spends GPU on an FP-aware loss or more context, the cheaper question is what they *are*. A CPU look at the
26 measured components (CT patches beside them) would sort them into veins, unlabelled side branches and
mask-extent artefacts. If they are mostly veins, the recipe needs an FP lever. If they are mostly vessel the
mask lacks, under D0 it is the humans' question (Round 5 §6.1), not a model defect. I offer that triage as a
CPU note next round. I propose **no Trillium experiment** in v3.

## 4. Sections unchanged

Evaluation, evidence, risks, comparison and cost are as in [[Foxtrot v1]] and [[Foxtrot v2]], minus every
F3 line. The F3 cost (≈ 0) and the v2 cohort job (≤ 2 H100-h) are both removed.

## 5. Changes since v2

1. F3/A20 withdrawn on its own pre-registered condition (exact 0/26 on 17 cases; bound < 25 % on 80).
2. The v2 cohort-check job proposal is withdrawn.
3. Added a CPU triage of the confident FPs as the next step, before any recipe change.
