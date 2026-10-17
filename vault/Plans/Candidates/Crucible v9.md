---
tags: [plans, candidate, fine-tuning, proxy-labels, double-reads, seeds, round-8]
author: Crucible
round: 8
version: 9
updated: 2026-10-11
---

# Crucible v9 — A11′ stands on two seeds but for a different reason; recipe decisions under 0.02 need two seeds; the proxy admission test uses D6's per-class 0.05

## 0. Improve or start again?

**Improve v8.**

- The fine-tuning recipe is unchanged. That covers the proxy admission test, team-only vs team + proxy decided at 300, identical initialisation for comparisons, a final model trained from scratch, and the frozen team val fold.
- Round 8 brings three changes:
  1. the seed-2 result: [[Crucible - Two-reads experiment pooled over two seeds]];
  2. human decisions D6 (margin 0.05 per class) and D7 (keep the outline; noted corrections only);
  3. the corrections these force to v8's evidence.

## 1. Thesis

Two training runs on identical data and reads give the following.

**Robust across the seeds:**

- Every two-read target beats a single read against the truth. both − single is +0.023, seed-random CI [+0.003, +0.042].
- Union is the worst arm against the reads (−0.032 [−0.054, −0.011]). The mechanism repeats: union's ignore band is filled with one annotator's LM in both runs.
- Truth labels are no better than two reads (oracle − both +0.000).
- agree ≈ both.

**Not robust:**

- The sign of a11 − both. The seed × contrast interaction excludes 0: +0.020 vs the truth and +0.046 vs the reads.
- both − single against the reads.
- v8's "the truth-trained arm loses 0.011 against the reads".

So:

1. **A11′ stands.** The pre-registered narrowing row never fires, and the pooled a11 − both against the truth is +0.002 [−0.020, +0.024]. But A11′'s grounds are now "simplest, never worse, and it removes a failure mode that the ignore band shows in 1 of 2 a11 runs and 2 of 2 union runs". The grounds are no longer "a11 is significantly worse on A10". That claim was seed 1 only.
2. **Run-to-run variance must be in the plan.** A single run moves a case by 0.02–0.05 tF1, and an arm mean by up to 0.025. Any recipe decision whose effect is under 0.02 needs ≥ 2 seeds, with seed pre-registered as a factor.

## 2. Changes to the master plan (proposed)

| Item | Current | **v9** |
|---|---|---|
| A11′ | Each read is its own sample, no `ignore` (Round 5, seed 1) | **Unchanged.** Rationale restated, as in §1. The conditional A11 test is withdrawn: under D0/D7 the only conflicts it would ignore are in the carina band, where the failure mode lives |
| GPU arm decisions | One run per arm | **A18-seeds (new):** a pooled effect under 0.02 tF1 needs ≥ 2 seeds with seed as a factor. The decision uses the seed-random CI; otherwise the result is "no difference detected". This applies to every advocate's ablation, e.g. Atlas's window ablation B (−0.0027, one seed each, 368 vs 412 epochs) |
| Proxy admission test (v8, A17) | Proxy vs reads non-inferior to inter-read within 0.02 | **Within D6's margin, 0.05 per class**, the same construction as model acceptance (`segtrain.reads.acceptance`, now 0.05 per class). The test admits a proxy iff it would pass as a model, so proxies and models are judged by the same rule |
| Team-only vs team + proxy at ≥ 300 (v8) | One paired run | **Two seeds per arm** if the first pair's pooled difference is under 0.02 (A18-seeds). That adds ≈ 24 H100-h only in that case |
| A3 convention monitor | Halt at > 10 % thin reads | **D7:** halt at > 10 % *un-noted* departures. Noted major-error corrections are listed but do not halt. Implemented: `CaseReads.corrected` / `first_reads_report(corrections=...)` |
| A10 acceptance | Margin 0.02 | **0.05 per class (D6).** Implemented as `NONINFERIORITY_MARGIN = 0.05` |

## 3. Evaluation

Unchanged otherwise (A1, A9, A10 with the 0.05 per-class margin from D6). Every pooled GPU comparison reports three things: the per-seed contrasts, the fixed-seed pooled CI, and the seed-random CI.

## 4. Evidence (corrected)

| Claim | Evidence |
|---|---|
| Two reads > one vs truth: +0.023 [+0.003, +0.042] seed-random; all four two-read targets positive in both seeds | [[Crucible - Two-reads experiment pooled over two seeds]] |
| Union worst vs reads: −0.032 [−0.054, −0.011]; LM vs read B 0.507 / 0.533, 21–22 of 50 cases below 0.5 in each run | same |
| a11 − both: s1 −0.008, s2 +0.012, pooled +0.002 [−0.020, +0.024]; interaction +0.020 [+0.006, +0.035] | same |
| a11's LM collapse vs read B: 22/50 cases in seed 1, 5/50 in seed 2 (both: 2–6/50) | same |
| Training-run SD: arm means 0.001–0.025; per case 0.02–0.05 | same |
| **Corrected:** truth-trained vs two reads against the reads −0.005 [−0.016, +0.005] pooled (v8 said −0.011, seed 1) | same |
| Proxy vs team targets (CPU, unchanged): team-read target − proxy +0.013 to +0.028 vs reads | [[Crucible - The expert proxy is a different teacher than the team, and calibrating it does not fix that]] |

## 5. Risks

| Risk | Detection | Response |
|---|---|---|
| A18-seeds doubles GPU cost for small effects | It applies only when the first pair's effect is under 0.02 | Small effects are reported as "no difference" rather than buying seeds, unless a decision hinges on them |
| A11′'s remaining support is a failure mode seen in 1/2 a11 runs | union shows it in 2/2. The wave-1 report measures LM against each read | If team reads show no LM habits (A12a), the question is moot in practice |
| D7 corrections are under-noted, so real redraws hide in notes | The monitor still flags and lists every noted correction | The judge reviews the noted-corrections list per wave. A rising share is itself a re-instruction trigger |

## 6. Next Trillium experiment

**Not proposed.**

- A seed 3 of both / a11 / union (3 arms × about 2 H100-h each = about 6 H100-h, plus inference) could narrow a11 − both further. But no decision depends on it: A11′ stands whichever sign wins, because the pre-registered narrowing row requires a11 < both.
- GPU time is better spent on the recipe question that Round 8's FP census reopened (A15). I defer to that.

## 7. Cost

- CPU: seconds (pooling script).
- GPU: none now. A18-seeds adds a second seed only for sub-0.02 decisions.
- Human: none.

## 8. Changes since v8

- Seed-2 pooled analysis, with A11′ re-grounded and the conditional A11 test withdrawn.
- A18-seeds is proposed.
- The admission test is moved to D6's 0.05 per class.
- v8's oracle-vs-reads claim is corrected.
- reads.py now implements D6, D7 and A1c; see [[Crucible - Implementation of segtrain.reads]].
