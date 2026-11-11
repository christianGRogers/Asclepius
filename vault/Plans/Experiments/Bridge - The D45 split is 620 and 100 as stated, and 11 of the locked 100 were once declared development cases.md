---
tags: [plans/experiment, janus1-l, D45, split, locked100]
author: Bridge
round: 1 (track 1-L)
updated: 2026-11-11
issue: christianGRogers/Asclepius#302
code: experiments/Bridge/j1l_r1/split620.py
---

# The D45 split is 620 and 100 as stated, and 11 of the locked 100 were once declared development cases

**Question.** D45 fixes the Janus 1 ImageCAS-X split in words. Which 20 of open-36 are locked and which 16 are
trained on? Does the rule give exactly 620 and 100, with no sealed case? Which of the locked 100 were inspected
during development?

**Method.** `experiments/Bridge/j1l_r1/split620.py` reads only id lists, never an image, label or score:
- ImageCAS-X's own train/val/test split (`trillium-results/icx14/results/splits.json`, 560/80/160);
- `trillium/sealed_test.json` (sealed 80, open-36, dev-44, sealed quality-0 20, declared development cases).

It ranks open-36 by `sha256('asclepius-janus1-locked100:' + c-id)`, with c-ids as in [[Sealed test]]. The 20
smallest are locked and the other 16 are trained on.

**Result.** Every check passes (`split620.json`):

| Check | Result |
|---|---|
| train 560 + dev 44 + 16 of open-36 = 620 distinct | pass |
| val 80 + 20 of open-36 = 100 distinct | pass |
| The two lists are disjoint | pass |
| No sealed ImageCAS-X or sealed quality-0 case is in either | pass |
| Every non-sealed ImageCAS-X case is in exactly one list | pass |

- **Locked 20 (from open-36):** c0068, c0102, c0251, c0271, c0323, c0327, c0470, c0545, c0592, c0620, c0644,
  c0805, c0807, c0824, c0827, c0841, c0908, c0946, c0957, c0996.
- **Trained 16 (from open-36):** c0123, c0195, c0340, c0416, c0430, c0435, c0447, c0617, c0624, c0660, c0726,
  c0758, c0772, c0877, c0971, c0984.
- **sha256 of the comma-joined sorted lists:** locked 100 `0090cf9bc279…876c7`, train 620 `fcd8aaa0bc7f…77ef8`
  (full values in the JSON). A launcher should refuse unless its lists hash to these.

**Development cases inside the locked 100.** 11 of the 100 were declared as development cases in Rounds 1–4:
c0039, c0152, c0224, c0225, c0400, c0514, c0564, c0566, c0591, c0606, c0950. All 11 are in val 80, and none in the
locked 20.
- They were inspected on the retired D0 convention, before any four-class model existed.
- Janus 0 and every Janus 1-L candidate share that history. A **paired** comparison of the two on the same cases is
  therefore not biased toward either one.
- An absolute number on the 100 (for example "Janus 1-L scores 0.91") carries that small optimism. It is reported
  as is, as val 80 always has been.

A further 147 declared development cases are in the training 620. That is harmless: training on a case is not
deciding on it.

**What it changes.** The split can be pinned in code as these two lists and their hashes (Bridge v1 §8). Janus 0
never trained on the 60 newly trainable cases (dev-44 and the 16), so its errors on them are honest held-out errors.
Any error analysis that shapes a Round 2 recipe should use those 60, not the locked 100.
