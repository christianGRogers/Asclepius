---
tags: [plans/experiment, janus1-l, D45, split, seal]
author: Atlas
track: 1-L
round: 1
updated: 2026-11-11
issue: christianGRogers/Asclepius#302
code: experiments/Atlas/j1l/split_check.py
---

# Janus 1-L: the D45 split rebuilt from the repo's lists gives 620 and 100, with no sealed case

**Question.** D45 fixes the split by rule: 620 training cases (ImageCAS-X train 560 + the 44 dev cases + 16 of
open-36) and 100 locked validation cases (val 80 + the 20 of open-36 with the smallest
`sha256('asclepius-janus1-locked100:' + id)`). Does the rule, applied to the lists already in the repo, give exactly
those counts, disjoint, with no sealed case? Which 20 are locked? The lists must be pinned before anything is trained.

**Method.** `experiments/Atlas/j1l/split_check.py` (CPU, standard library, seconds). It reads only id lists:
- `trillium/sealed_test.json` (A14: sealed 80, open 36, dev 44, sealed quality-0 20);
- ImageCAS-X's own train/val/test filelists as recorded by the icx14 job
  (`trillium-results/icx14/results/splits.json`; the same filelists icx4 reads in `trillium/icx4/lib/prepare.py`).

No image, label or score is opened. Output: `experiments/Atlas/j1l/split_j1l.json`.

## Result

| Check | Value |
|---|---|
| ImageCAS-X train / val / test | 560 / 80 / 160 |
| Test = sealed 80 + open 36 + dev 44 | yes |
| Train 620 / locked 100 | **620 / 100** |
| Train ∩ locked | none |
| Sealed ImageCAS-X 80 in train or locked | none |
| Sealed quality-0 20 in train or locked | none (quality-0 cases are outside ImageCAS-X's 800) |
| Train 620 + locked 100 + sealed 80 | exactly the 800 ImageCAS-X cases |
| sha256 of the sorted locked-100 ids (`\n`-joined) | `bbd9c687818956e2d5664b06fd8c8bd02ddb031e9b9d08036d59cc0e1a4d5895` |
| sha256 of the sorted train-620 ids (`\n`-joined) | `1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152` |

**The 20 locked open-36 cases:** c0068, c0102, c0251, c0271, c0323, c0327, c0470, c0545, c0592, c0620, c0644, c0805,
c0807, c0824, c0827, c0841, c0908, c0946, c0957, c0996.

**The 16 open-36 cases that join training:** c0123, c0195, c0340, c0416, c0430, c0435, c0447, c0617, c0624, c0660,
c0726, c0758, c0772, c0877, c0971, c0984.

## What it changes

- The rule is consistent with the lists in the repo. The two hashes above are what a launcher must check before it
  trains (refuse on mismatch), next to the A14 sealed check it already runs.
- **60 of the 620 training cases (dev 44 + open 16) were never seen by Janus 0**, which trained on train 560 only.
  Janus 0's predictions on them are honest held-out predictions. They are the only ImageCAS-X cases where anything about
  Janus 0's output (e.g. a width threshold) can be fitted without touching the locked 100. After Janus 1-L trains on
  them they lose that property, so any such fit must happen on Janus 0's outputs. [[Janus 1-L Atlas v1]]
  uses this for its width calibration (Job W).
- Open-36 no longer exists as a confirmation set: 20 of it is locked and 16 trains. The locked 100 is the one
  decision set for ImageCAS-X questions in this track; val 80 and locked 20 are reported apart for sign only.
