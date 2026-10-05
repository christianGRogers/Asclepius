---
tags: [plans, candidate, topology, post-processing, ostium]
author: Delta
round: 3
version: 3
updated: 2026-10-04
status: in progress — results being filled in
---

# Delta v3 — settle P1′ with its control, measure the support rule, and make the ostium per tree

## 1. Decision: improve, not restart

All challengers have converged on the master's recipe, and I have no measured training-side
alternative. A materially different recipe would be an assertion, not evidence. So v3 does the three
things the Round 2 ruling (§4) says would change it:

1. **The tile-step-0.5 control for gap-centred re-inference (P1′).** If nnU-Net's default overlap
   alone recovers what re-inference recovered, P1′ is dropped.
2. **The support rule measured**: joins kept versus blocked, scored against the reference.
3. **Ostium validation extended**: an absent-LM case, and the rules applied per tree component.

The two cases left unfinished in v2 (c0846, c0951) are included.

PENDING — jobs running (`experiments/Delta/r4_*`): step-0.5 inference on 8 cases, then re-inference on
them; re-inference with support-rule audit on all 18 step-0.75 cases; per-component ostium
validation on 71 cases including c0020, c0141 and c0196 (absent LM).

First result: on **c0020** (LM absent, three trees, three true ostia), both cheap rules applied per
component find all three ostia within 1.4 mm, and they agree.
