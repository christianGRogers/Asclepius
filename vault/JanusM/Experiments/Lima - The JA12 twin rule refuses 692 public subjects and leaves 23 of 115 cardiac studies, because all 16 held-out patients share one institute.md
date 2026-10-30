---
tags: [janus-m, experiment, round2, rest-ccta, guard, held-out, totalsegmentator]
author: Lima
round: 2
path: jm/rest-ccta
updated: 2026-10-30
issue: christianGRogers/Asclepius#142
---

# Lima E1: the JA12 twin rule refuses 692 public subjects and leaves 23 of 115 cardiac studies, because all 16 held-out patients share one institute

**Question (Round 1 ruling §6 item 7).** Applied to the public TotalSegmentator `meta.csv`, how many subjects does
JA12's twin rule refuse? The ruling expected "a few public training cases".

**Setup.** Metadata only: no image was opened for this experiment.
- `experiments/JanusM/Lima/heldout.py` collects every TotalSegmentator s-number named in the coronary held-out and
  pool files: the SegQueue14 pool list, the pool seal, `trillium/icx4/sealed_test.json`, every JSON or text file
  under `experiments/*/r10*/` and every config. It refuses to run with fewer than 16 ids. It finds **16**, as
  India, Kilo and the judge did.
- `twins.py` reads the two public `meta.csv` files, v1 (Zenodo 6802614, 1204 subjects) and v2.0.1 (Zenodo 10047292,
  1228 subjects). Each was fetched by one HTTP range read and kept in a scratch folder, never committed.
- **The rule, as JA12 states it.** A twin is any other subject in the same release with:
  - the same sex;
  - the same institute letter;
  - an age within ±5 years;
  - any study type.

  A missing sex or age counts as a match. The match is made within each release, because institute letters are
  relabelled between v1 and v2 (India R1). The union over both releases is refused.
- **Disclosure.** Applying the rule requires the age, sex and institute of the 16 held-out subjects, so their
  `meta.csv` rows were read. Nothing else about them was read: no image, no mask, no label, no score.

**Result** (`experiments/JanusM/Lima/twins.json`):

| | v1 | v2.0.1 | union |
|---|---|---|---|
| subjects | 1204 | 1228 | |
| twins | 624 | 656 | **692** |
| refused in total (held-out + twins) | | | **708** |
| cardiac-protocol studies* | 130 | 130 | |
| of which held out | 15 | 15 | |
| of which twins | 87 | 87 | 92 |
| **cardiac studies left for Janus-M** | | | **23** |

\* Study types `ct heart`, `ct heart-thorakale aorta`, `ct aortic valve`, `ct coronary arteries` and
`ct left artrium`, as in India's and Golf's fetchers.

- **Why so many.** All 16 held-out subjects come from **one institute**: H in v1 and I in v2. That institute holds
  881 of the 1204 v1 subjects. Their ages run from 47 to 77 and both sexes occur, so ±5 years around 16 ages covers
  most of that institute's adults.
- **Tighter age windows** (v1 alone; cardiac twins / cardiac studies left):

  | Age window | Cardiac twins | Cardiac studies left |
  |---|---|---|
  | ±5 years | 87 | 28 |
  | ±4 years | 84 | 31 |
  | ±2 years | 66 | 49 |
  | ±0 years | 17 | 98 |

  India measured age jitter of up to 4 years between the two releases, so a window below ±4 years would not be
  safe. **The metadata cannot narrow the rule further.**

**What it changes.**
1. **The ruling's cost estimate is wrong.** The twin rule refuses 57 % of the public release and **80 % (92 of 115)
   of the non-held-out cardiac studies**, not a few cases. That is the price of a guard by sex, institute and
   jittered age when the held-out patients all come from the largest institute.
2. **It costs Janus-M little.** Under JA5 the public TotalSegmentator cardiac set is at most optional pretraining
   and a report-only stratum, never a seal, decision set or border reference. JA9 also dropped pretraining. Lima
   therefore **keeps JA12's rule as written** and ships the 23-subject allowed list.
3. **It affects Round 1's public-data experiments.** Golf's 24, Kilo's 39 and India's 64 public cases were chosen
   before the rule existed, so most of them would now count as twins. None was a held-out patient, so this is not
   a breach. Their geometry results stand as evidence about 1.5 mm model-made labels. But **no later round should
   reuse those case lists without `heldout.check`**.
4. **For the shared JA12 guard (#138):** compute twins per release, with the union refused, and pin the held-out
   list's hash in the twin file. Lima's `heldout.py` refuses to run if `twins.json` was built from a different
   held-out list.

**Held-out cases opened in this experiment: none.** Lima's E2 and self-test fetches (`fetch_ts.py`) ran after this
guard. `check(sid)` runs before any file of a subject is requested, and only the 23 allowed subjects were fetched.
