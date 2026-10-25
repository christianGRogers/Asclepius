---
tags: [plans/experiment, D35, decision-set, A17, A22, A30, pool, statistics, round10]
author: Bridge
round: 10
updated: 2026-10-25
issue: christianGRogers/Asclepius#113
---

# A 35-patient D35 decision set is drawn from eight sources and is read by mid-queue

**Question (issue #113, D35).** Set the D35 decision set's size, salt and draw; reconcile the two counts quoted for
it; say how it meets the seal's extension reserve (A30, D32); and say what it can resolve for paired fine-tune
comparisons on Janus 0's numbers.

**Answer.**
- **The counts.** "About 50 of about 347" was counted on the retired name rule (517 − 150 − 20 = 347) and still
  included ImageCHD. On real patients (D32/D33) there are **235 non-sealed, non-ImageCHD patients**, of whom 74 are in
  the spacing-suspect sets that tF1 cannot score in mm (D29). The scorable universe is the **161 primary non-sealed
  patients**, and 100 of them are the seal's reserve. The wave-1 note's "198 open" is a different quantity (every
  stratum, after the reserve) and includes 63 ImageCHD and 74 spacing-suspect patients.
- **Size: 35 patients (47 volumes)**, which is 15 % of the 235, as D35 words it.
- **Draw:** primary stratum, outside the seal and its 200-step (`extension_order[:50]`); proportional by source,
  then the smallest sha256(`asclepius-decision-round10-pool:` + patient) within source. It spans **eight sources**
  (Taiwan 16, Mendeley-SDN 5, EpicardialFat 4, VMR 4, Kaggle-CAD 3, CardiacCT15 1, RIDER 1, TotalSegmentator 1).
  Drawing outside the whole 100-patient reserve instead would leave 61 patients from five sources and a set that is
  71 % Taiwan.
- **The reserve stays at 100 and stays intact.** Decision patients are looked at, so none can join the seal. The
  250 step is re-stated now, before any read exists, as the next 50 patients of the extension order that are not
  decision patients (14 entries skipped), continued by the Round 9 rule over the 13 needed primary patients the order
  never listed. That is D32's skip rule applied to decision patients instead of sealed ones; the seal's salted
  ranking is unchanged.
- **Resolution.** For a fine-tune (two seeds) against the fixed Janus 0 on all 35 patients, the smallest effect
  detected with 80 % power is **0.018–0.029 macro tF1** if the pool is as varied as val (up to 0.036 at 1.5×). The
  case term alone is 0.018; the rest is seed noise, bounded on our own master-size models (below).
- **Timing.** 23 of the 35 scoring volumes are served by the end of the QC-annotatable block (queue position 242),
  27 by 300 and all by 600.

## Method

CPU only, no image read. Code in `experiments/Bridge/r10/`:
- `counts.py` → `counts.json`: patients by stratum, seal and reserve (`segtrain.pool_seal.ingest_patient`);
- `draw_d35.py` → `decision_set_proposal.json`: the draw, the re-stated reserve, the serving positions;
- `queue_timeline.py` → `queue_timeline.json`: what exists at each queue position;
- `d35_power.py` → `d35_power.json`: paired noise from the two master-size pairs in the repository, and the MDE table.

## 1. Counts

| Stratum | Sealed | Reserved (`extension_order[:100]`) | Open | Note |
|---|---|---|---|---|
| Primary | 150 (305 vols) | 100 (144 vols) | 61 (69 vols) | the only stratum tF1 can score and A10 counts |
| Report-only (ImageCHD) | 20 | — | 63 | excluded from D35 by its own text; trainable |
| Spacing-suspect (ImageALCAPA, HOCMvalvesSeg, CCA200-HF) | — | — | 74 | unscorable in mm until re-gridded (D29); trainable with care |
| **All** | 170 | 100 | 198 | 468 real patients, 675 volumes |

| Count quoted | Formula | Value |
|---|---|---|
| Atlas, #43: "about 347" | name-rule patients 517 − 150 − 20 | 347 (retired rule; includes ImageCHD) |
| Wave-1 note: "198 open" | 468 − 170 − 100 | 198 (every stratum) |
| D35 as written, on real patients | non-sealed, non-ImageCHD | **235** → 15 % = **35** |
| Scorable for decisions | primary, non-sealed | 161 |

## 2. Why 35 and why outside the 200-step only

- **Size.** 35 is D35's own 15 % on the corrected count. A bigger set buys little (§4: with two seeds the MDE falls only from 0.029
  at 35 to 0.027 at 61) and costs training reads one for one.
- **Never the seal.** A decision patient's reads are inspected and decide recipe choices, so a decision patient that
  later joined the seal would score a model selected partly on it. The set is therefore disjoint from the seal and
  from both pre-registered extension steps.
- **Why the 200-step is kept whole and the 250-step is re-stated.** The extension order round-robins by source, so
  its first 100 entries take most patients of the small sources. Excluding all 100 leaves five sources. Excluding
  the first 50 and re-stating the next 50 around the decision set keeps both steps at 50 patients, keeps every
  extension patient unseen, and lets the decision set cover eight sources. The cost is that the 250 step is now
  slightly more Taiwan-heavy than the original order; the primary seal of 150 is unchanged.
- **Training cost is the same either way:** 26 open primary patients (28 volumes) remain for training until the seal
  size is decided, plus 63 ImageCHD and 74 spacing-suspect volumes; then whatever the reserve releases (§3).

## 3. Timing in the D23 serving order (D30: unchanged)

Queue position = how many of the 675 volumes have both reads approved. Sealed volumes are read like any other.

| Position | Decision patients scored | Open primary patients (A31 measurements) | Trainable pool volumes now | … if the seal stays 150 | … if 200 |
|---|---|---|---|---|---|
| 150 | 11 | 15 | 6 | 53 | 26 |
| 200 | 19 | 38 | 21 | 74 | 44 |
| **242** (end of QC-annotatable) | **23** | **49** | 28 | **93** | 60 |
| 300 | 27 | 53 | 28 | 121 | 76 |
| 450 | 29 | 55 | 90 | 203 | 142 |
| 675 | 35 | 61 | 165 | 303 | 231 |

Two consequences:
1. **Before the seal size is decided, wave 1 has almost nothing to train on** (28 volumes at position 242). The
   reserve is where most early primary reads sit. So rule C ([[Bridge - On Janus 0's spread the 150-patient seal is under-powered unless reads and model fail on the same patients]])
   must run first, on the ~49 open primary patients read by position 242, and the reserve must be released before
   Janus 1 trains.
2. **The decision set is about two-thirds read by the end of the annotatable block.** Seven scoring volumes sit in
   sources served late (positions 445–600). The first decision uses the decision patients read at the time, which
   the serving order fixes, not the results; the rest confirm when read, as open-36 does for val.

## 4. What the set can resolve

**Paired noise, measured on the master-size network** (per-case decisive tF1, same val 80):

| Pair | What differs | Paired SD of macro tF1 | Macro Δ (case SE) |
|---|---|---|---|
| atlas3 F1 − F0 | two warm fine-tunes from one checkpoint, same seed and data; an FP term under 0.1 % of the loss | 0.038 | +0.0047 (0.0043) |
| atlas2 B − run 1 | two from-scratch trainings, different CT window | 0.041 | −0.0027 (0.0046) |

Per class the paired SDs are larger (warm pair: LM 0.124, LAD 0.043, LCx 0.065, RCA 0.054), so per-class decisions
are coarser than macro ones.

**Run-to-run noise.** Both macro differences are inside case noise. Pooled over the two pairs, the run-to-run SD is
**0.000 at the maximum likelihood, with an upper 95 % bound of 0.012** (`d35_power.sigma_run_pooled`). A22's prior
of 0.013 came from Crucible's smaller network; the master-size data do not contradict it, but they put it at the edge
of what is plausible, not the middle. A22 stands; the first Janus-1 job measures the fine-tune's own run-to-run
noise with its two seeds (D28's fallback).

**MDE** (two-sided 5 %, 80 % power; SE² = sd²·f²/n + σ²(1/m_a + 1/m_b)):

| Design | f | n = 20 | 30 | **35** | 40 | 61 |
|---|---|---|---|---|---|---|
| Warm FT (2 seeds) vs fixed Janus 0, σ = 0.012 | 1.0 | 0.033 | 0.030 | **0.029** | 0.029 | 0.027 |
| same | 1.5 | 0.043 | 0.037 | **0.036** | 0.034 | 0.031 |
| Case term only (σ = 0) | 1.0 | 0.024 | 0.019 | **0.018** | 0.017 | 0.014 |
| Warm FT vs warm FT, 1 seed each, σ = 0.013 | 1.0 | 0.057 | 0.055 | **0.055** | 0.054 | 0.053 |
| Scratch vs warm, 2 seeds each, σ = 0.013 | 1.0 | 0.045 | 0.042 | **0.041** | 0.041 | 0.039 |

Two things follow:
- **The decision set can judge "does fine-tuning on pool reads help on the pool" (one arm, two seeds, against a
  fixed Janus 0) to about 0.02–0.03.** Domain-shift gains from in-domain fine-tuning are usually larger than that;
  if they are not, the honest verdict is "not detected".
- **It cannot judge warm against from-scratch, or one LR against another, below about 0.04–0.05** without three or
  more seeds per arm. That is a reason to make the first Janus-1 job a single, well-seeded question.

## Freezing

`decision_set_proposal.json` records the pool-list and seal sha256 it was drawn from. It becomes binding only if the
judge adopts it. It must then be copied byte for byte into `configs/segqueue14/` with a pinned sha256 and a guard
in `segtrain` that refuses its volumes in `convert` and the trainer exactly as the seal is refused, together with the
re-stated reserve (role:swe issue). Until then, no read of a listed patient may be exported for analysis.

## Limits

- The paired SDs are on ImageCAS val, scored against one expert read. On the pool they are multiplied by f and
  carry read noise; the table shows f = 1.5.
- Two pairs give a 2-df bound on run-to-run noise; the two seeds of the first Janus-1 job add the first direct
  measurement on a fine-tune from Janus 0.
- The timeline assumes the queue is read in order. If annotators work several positions ahead, the counts arrive
  earlier, not later.
