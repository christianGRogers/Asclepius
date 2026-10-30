---
tags: [janus-m, experiment, held-out, guard, totalsegmentator, twin-rule, path-rest-ccta]
author: Hotel
round: 2
path: jm/rest-ccta
updated: 2026-10-30
issue: christianGRogers/Asclepius#142
---

# The twin rule refuses 695 public TotalSegmentator subjects and leaves 23 cardiac studies, and Round 1 used exact matches

Round 1 ruling §6 item 7: apply the JA12 twin rule to the public TotalSegmentator `meta.csv` and report the refused
count.

## What was run

- **Guard first.** `experiments/JanusM/Hotel/guard_r2.py` is Hotel's Round 2 guard, used until the shared JA12 guard
  (#138) lands on `dev`. It refuses, by patient:
  - the pool seal (D27/D32/D33) and its A34 reserve;
  - every Round 10 D35 draw;
  - the whole pool list;
  - A14's sealed 100, the ImageCAS-X test split (sealed 80, open 36, dev 44) and val 80;
  - PLOS-Peng2016;
  - every TotalSegmentator s-number named in those files, and every twin of one.

  It also checks the pinned seal hash and the JA6 `splits.json` hash (`a53bd426cddc`), and stops on fewer than five
  D35 files or 16 TotalSegmentator ids. It found 16 held-out s-numbers:
  - 8 sealed: s0465, s0655, s0871, s0972, s0980, s1097, s1106, s1345;
  - 8 in the reserve: s0356, s0368, s0738, s0839, s0846, s0879, s0936, s1002.

  This matches the ruling's count. All 16 are institute "H" in v1.
- **Data: metadata only.** The two public `meta.csv` files:
  - v1: Zenodo 6802614, 1204 subjects;
  - v2.0.1: Zenodo 10047292, 1228 subjects; institute letters relabelled, two blank sexes, five blank institutes.

  Each was pulled out of its archive by an HTTP range request. **No CT and no mask was downloaded or opened.**
- **The rule (ruling §4):** a twin is a public subject with the same sex and institute as a held-out subject, age
  within ±5 years, any study type. A blank field matches anything, so the rule errs toward refusing. It is applied to
  each file and the union is refused.
- **Scripts:** `experiments/JanusM/Hotel/r2/e1_twins.py` produces `e1_twins.json`; `r2/e1_chance.py` produces
  `e1_chance.json`.

## Results

| | v1 | v2.0.1 | Union |
|---|---|---|---|
| Subjects | 1204 | 1228 | 1228 |
| Twins refused | 624 | 659 | **695** |

- **Cardiac studies.** v1 has 130 cardiac-type studies: "ct heart", "heart-thorakale aorta", "aortic valve",
  "coronary arteries" and "left artrium".
  - 15 are held out by s-number. The 16th held-out subject, s0871, is typed "ct angiography thorax".
  - 92 are twins.
  - **23 remain.**
- **Why the rule refuses so much.** 881 of the 1204 v1 subjects come from one institute (H), and every held-out
  subject is from H. With an 11-year age window and two sexes, most H subjects are some held-out subject's twin.

**Exact matches.** Seven v1 subjects share age, sex, institute *and* study type with a held-out subject:

| Public | Held-out match | Its status | Study type |
|---|---|---|---|
| s0767 | s0846 | reserve (A34) | ct heart |
| s0848 | s1106 | sealed | ct heart |
| s0717, s0822, s1073, s1269 | s0972 | sealed | ct heart-thorakale aorta |
| s1280 | s1097 | sealed | ct left artrium |

- **Against chance.** If 16 non-held-out subjects are drawn with the same study types and institutes (2000 draws),
  they collect a mean of **4.81** such matches (95th percentile 9). Seven or more occur in **24 %** of draws. So the
  exact matches are what coincidence predicts in a 1204-subject release dominated by one institute. They are **not
  evidence of the same patient**, and they cannot be ruled out as the same patient either.
- **India's check.** The ruling records India's check that "no other v1 subject shares a held-out subject's age,
  sex, institute and study type". On the v1 `meta.csv`, seven do.

## Disclosure: Round 1 results used refused subjects

| Advocate (file checked) | Ids in file | Exact matches | Twins (union rule) |
|---|---|---|---|
| Golf (`ts_cases.json`) | 24 | s0767, s1073 | 20 |
| **Hotel (`e1_ts_cardiac_results.json`)** | 26 | **s0767, s0848** | 20 |
| India (`results/summary.json`) | 64 | s0717, s0767, s0822, s1073, s1269, s1280 | 49 |
| Juliet (`real_labels.json`) | 12 | none | 9 |
| Kilo (`results_e123_grid05.json`) | 40 | s0767, s0848 | 31 |

None of these files contains a held-out s-number itself; the judge checked that, and it holds.

- **Hotel's own Round 1 E1 opened s0767 and s0848.**
  - What was read and computed: their public 1.5 mm CT and public heart masks; HU profiles, thirds, edges and
    segments.
  - What was not: no coronary label exists for these subjects, none was read, no Janus model was run, and no coronary
    quantity was computed.
  - These two files are still on `dev` and on this branch as Round 1 records. Hotel does not edit them, because
    candidates and their evidence are not edited after their round.
- **What this means:**
  - If a twin were the same patient, the harm is bounded exactly as the ruling's §4 says: the study entered a Janus-M
    simulation, never a coronary score.
  - The chance analysis above says the exact matches are most likely different patients.
  - **No Round 2 Hotel experiment opens any TotalSegmentator case.**
- **For the PM and the lead.** Whether Round 1 numbers computed on twins need a note in the Round 1 record is the
  PM's call; Hotel recommends a one-line note, nothing more. Whether the reserve and seal entries above change
  anything under D27 is the lead's call, as LQ8 is. Hotel recommends no change: no coronary quantity was computed on
  any of these studies.

## What it changes

1. **Public TotalSegmentator v1 is almost gone as a Janus-M source.** 23 cardiac studies remain after the rule. That
   is enough for a code smoke test, not for pretraining. This agrees with JA9 dropping the pretraining stage.
2. **The rule over-refuses by design, and its cost is now known:** 695 of 1228 subjects. A sharper rule needs a
   patient key that TotalSegmentator does not publish. Hotel recommends keeping the rule as written.
3. **For the shared guard (#138):**
   - apply the rule to both `meta.csv` files and refuse the union, because blank v2 fields widen it;
   - pin both files by hash;
   - stop if a held-out id is missing from a meta file. `guard_r2.twins()` does this.
