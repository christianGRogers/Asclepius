---
aliases: [Atlas run 3 result]
tags: [plans, experiment, trillium, fp]
status: done
updated: 2026-10-12
---

# Atlas run 3 result: the FP-aware loss was too weak to test

Results: `trillium-results/round7/atlas3/` (SUMMARY.md, results.json). Pinned metric hash matched;
no sealed case touched. Both arms warm-started from run 2's B, same seed and data, 200 epochs each.

| arm | decisive macro tF1 | LM / LAD / LCx / RCA | FP comps / case |
|---|---|---|---|
| F0 (plain) | 0.891 | 0.948 / 0.896 / 0.841 / 0.875 | 1.31 |
| F1 (+ FP term) | 0.895 | 0.959 / 0.901 / 0.846 / 0.882 | 1.27 |

Paired F1 − F0 on 80 val cases: tF1 +0.005 (case CI −0.003..0.014; seed-inclusive −0.022..0.032),
FP −0.04 per case (CI −0.35..0.26). The pre-registered rule (A24.2) gives **not adopted: no FP
reduction detected**.

**Why this is not evidence against FP-aware losses.** The FP term's epoch mean was 0.00007 → ~0.0005
over training, against a total loss of about −0.88: under 0.1 % of the loss, so it can hardly have
shaped the gradients (λ = 1, focal γ = 2, 1.5 mm band; the focal factor and the narrow band leave few
voxels contributing). The pilot tested "this term at this weight", not the idea. A fair test would
scale λ until the term is ~5–20 % of the loss.

**Status under the restructure (D8–D10).** The four-class plan is superseded; nothing here changes
the icx14 run. If stray vessels (veins) remain a problem in icx14's predictions, revisit with a
properly weighted term in the D15 fine-tune.
