---
tags: [janus-m, experiment, guard, held-out, totalsegmentator, twins, round2, paired-scar]
author: Golf
round: 2
path: jm/paired-scar
updated: 2026-10-30
issue: christianGRogers/Asclepius#143
code: experiments/JanusM/Golf/guard_r2.py
---

# The JA12 twin rule refuses 707 of 1228 public TotalSegmentator subjects, and 106 of the 130 cardiac ones

## Question

Round 1 ruling §6 item 7: apply JA12's twin rule to the public TotalSegmentator metadata and report how many
subjects it refuses. A **twin** is a public subject who matches a coronary-held-out TotalSegmentator subject on sex
and institute, with age within ±5 years and any study type (ruling §4). The ruling expected "a few public training
cases" to be lost.

The guard also has to exist before Golf opens any public case this round. The shared guard (#138) has not landed on
`dev` yet, so Golf extends its Round 1 `heldout.py` to JA12's full list.

## Method

`experiments/JanusM/Golf/guard_r2.py`, CPU, seconds. It refuses, by patient:

1. everything `heldout.py` refuses: the pool seal (primary, report-only, extension order), every Round 10 D35 draw,
   and the A14 sealed 100;
2. the ImageCAS-X **val 80** and the whole **test split** (160 = A14's 80 + open 36 + dev 44). These come from the
   committed `splits.json`, and the guard will not run on any other file (sha256 prefix `a53bd426cddc`);
3. **PLOS-Peng2016**, the whole source;
4. all **16** TotalSegmentator subjects in the coronary pool list, sealed or not;
5. every **twin**. Golf checks v1 (Zenodo 6802614) and v2.0.1 (Zenodo 10047292) metadata separately, because
   institute letters are relabelled between the versions (India R1). A blank sex or age counts as a match, so the
   guard errs towards refusing.

Only `meta.csv` was read from each archive, by HTTP range request. No image was downloaded for this step. The guard
refuses to load unless the twin list it was built with names the same 16 held-out subjects as today's pool list.
The committed `guard_r2_twins.json` holds both `meta.csv` hashes, the counts and the refused s-numbers. It holds no
ages.

## Result

| | v1 (1204 subjects) | v2.0.1 (1228 subjects) |
|---|---|---|
| Held-out subjects found in the metadata | 16 / 16 | 16 / 16 |
| Twins | 639 | 671 |
| **Refused (union, by s-number)** | | **707** |
| Of which cardiac study types | | **106** |

- **Twins per held-out subject: 112–302.** Most held-out subjects come from institute I, which contributed most of
  the dataset. Sex plus a 10-year age window then matches a large share of that institute's patients.
- **The effect on the cardiac cases Janus-M could use,** from the project's list of 130 cardiac ids
  (`tools/ccta/totalseg_cardiac_ids.json`):
  - gated-like: 116 → **22** allowed;
  - other contrast: 14 → **2** allowed.

  In all, **106 of the 130 cardiac ids are refused** (held-out subjects and twins together; 24 pass).
- **Golf's own Round 1 E2 set:** 20 of its 24 cases are now refused as possible twins.
  - None of the 24 is a held-out subject by s-number; the R1 guard and the judge's search both confirm this.
  - Under the new rule they are only *possible* second studies of a held-out patient. No coronary quantity was ever
    computed on them, and E2's committed numbers are about geometry, not about any held-out patient.
  - **This is disclosed here and in the PR.** If the lead or the PM wants it, Golf's R1 E2 numbers can be re-derived
    on the 22 cases that pass today.
- **Checks:**
  - `s0655` → refused (seal);
  - a val-80 case → refused;
  - `c0000` (train) → allowed;
  - any PLOS-Peng2016 case → refused.

## What it changes

1. **"A few public training cases" is wrong by two orders of magnitude.** The rule as written removes 58 % of the
   public dataset and 83 % of its cardiac cases.
2. **On this path the cost is affordable.**
   - Path B's images are ImageCAS-X train (JA5) and, for scar, an institutional paired cohort. Public
     TotalSegmentator cardiac data was only ever a report-only stratum or optional pretraining.
   - Golf therefore **accepts the over-refusal** and does not ask for a looser rule.
   - The 22 + 2 that pass are enough for CPU experiments on real anatomy (E5 uses the 22).
3. **For the lead (on both paths):**
   - A tighter twin rule would lose fewer cases. Possible extra conditions are scanner model and kVp in v2, or a
     ±4-year window (the jitter bound India measured).
   - But every tighter rule admits more true second studies, and TotalSegmentator publishes no patient id to check
     against.
   - Golf recommends keeping the rule as written, since nothing on path B depends on these cases.
4. **The shared guard (#138) should take this rule and its sha-pinned twin list as they are.** Golf's `guard_r2.py`
   is a stop-gap until #138 lands, and is replaced by it.
