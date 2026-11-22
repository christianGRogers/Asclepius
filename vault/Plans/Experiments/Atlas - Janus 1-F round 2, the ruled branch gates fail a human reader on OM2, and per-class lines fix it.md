---
tags: [experiment, janus-1f, round2, branches, gates, scorer, band, census, D45, D47]
author: Atlas
updated: 2026-11-22
issue: christianGRogers/Asclepius#303
code: experiments/Atlas/j1f_r2/
---

# Atlas - Janus 1-F round 2, the ruled branch gates fail a human reader on OM2, and per-class lines fix it

For [[Candidates/Janus 1-F/Atlas v2|Atlas v2]]. Everything here is CPU work on the **D45 training 620** (labels
only). No locked-100, sealed or quality-0 label was fetched. The locked-100 counts are Delta v1's published label
counts (F-A7).

## Questions

1. Do F-A6's B lines (recall ≥ 0.80, naming ≥ 0.85, presence ≥ Table 1 − 0.05, "4 of 6") fail a model that is as good
   as ImageCAS-X's own second analyst, at the locked-100 counts? (ruling §5, item 1)
2. Can the branch scorer be written and frozen now, and does it behave on real references? (item 2)
3. How much background does a stage-2 band release, and how much of a side branch's course does it cover? (item 4)
4. One census of record for the 620 (item 10).
5. What D35 can yield for the six untraced classes (item 6).
6. Shi et al.'s two sets of numbers (item 7).

## Setup

| Script | What |
|---|---|
| `fetch_620.py` | ImageCAS-X segmentations + `Descriptors.xlsx` for the 620 only; asserts the 620's pin and disjointness from the locked 100 before any read |
| `j1f_scorer.py` | F-A3 labels (D47 Q1 = A), F-A4 origin collapse, and every B measure; imports the pinned `tf1.py`; synthetic self-test |
| `census_r2.py` → `census_r2.jsonl`; `summarise_r2.py` → `census_r2_summary.json` | per case: collapse check, pieces, bands, side-branch distance from parent, trunk spurs, posterior branches |
| `gate_sim.py` → `gate_sim.json` | the human-level simulation |
| `validate_scorer.py` → `validate_scorer.json` | the scorer on a real case with known perturbations |
| `untraced_yield.py` → `untraced_yield.out` | D35 yields |
| `head13_check.py` → `head13_check.out` | step-0 identity of the adopted 13-output head |

**The human-level model.**
- It is calibrated to ImageCAS-X Table 1 (arXiv:2608.30404): per segment, n, presence agreement, and centreline
  clDice mean ± SD. The second analyst was "selected at random, following the same protocol without review from the
  lead analyst and blinded to the first set of labels".
- **Omission rate:** m = (160(1 − A)/2) / (n + 160(1 − A)/2), from exchangeable analysts.
- **When both drew the segment:** a two-part mixture fitted to clDice's mean and SD. The low part is a misplaced
  branch, split between "detected but misnamed" (share s) and "missed".
- **Scenarios:** nine, with σ_h ∈ {0.05, 0.08, 0.12} × s ∈ {0, 0.5, 1}.
- **Counts:** the locked counts (98, 64, 84, 40, 96, 96), with pieces per case drawn from the 620.

## Results

### 1. The gates as ruled (central scenario; range over nine)

| | D1 | D2 | OM1 | OM2 | PDA | PLB | verdict |
|---|---|---|---|---|---|---|---|
| human-level false-fail | 0.4 % [0.1–8] | 6.6 % [6–22] | 4.0 % [2–47] | **59 % [47–81]** | 0 % | 0.3 % | 0.1 % [0.1–6] |

- **OM2's expected recall for a human is 0.73–0.82,** because a second analyst omits OM2 in 18 % of the cases the
  first drew it. No 0.80 line can be passed reliably.
- **OM1's failure is naming when the low part is ordinal shifts** (s = 1): human naming 0.85.

### 2. Per-class lines at a human's 5th percentile, worst scenario per statistic

| | D1 | D2 | OM1 | OM2 | PDA | PLB |
|---|---|---|---|---|---|---|
| recall ≥ | 0.81 | 0.76 | 0.75 | 0.60 | 0.89 | 0.89 |
| naming ≥ | 0.83 | 0.86 | 0.77 | 0.78 | 0.90 | 0.92 |
| presence ≥ | 0.94 | 0.84 | 0.90 | 0.81 | 0.97 | 0.94 |
| false-fail, nine scenarios | 1.8–6.1 % | 3.5–6.6 % | 1.8–7.3 % | 2.7–6.9 % | 1.3–5.4 % | 2.6–6.5 % |

- **Verdict false-fail ≤ 0.3 %.**
- **Power** (the verdict rejects): omission +0.10 → 100 %; misnaming +0.10 → 54 % (57 % as ruled); misnaming +0.20 →
  99.8 %; icx14's "all parent" → 100 %.

### 3. The scorer

- **The synthetic self-test passes.**
- **On a real case (c0217):** identity 1.0; D1/D2 swap detected and misnamed; OM folded into LCx detected, misnamed,
  presence lost; PLB dropped missed; PDA truncated to 40 % missed.
- **A one-voxel erosion of the tree removes D1 and the PDA altogether.** Branches are at the grid floor.
- **Cost:** ≈ 110 s per case per reading.
- **Origin collapse vs `territory.to_four` on the 620:** ⟨COLLAPSE⟩.

### 4. Bands and side-branch distance from the parent (620)

⟨BANDTABLE⟩

### 5. Census of record (620)

⟨CENSUS⟩

### 6. D35 yields (35 patients)

- **Report (≥ 20 patients with 80 % assurance):** needs π ≥ 0.63.
- **Decide (≥ 30):** needs π ≥ 0.89.
- Recall 0.8 is known to ± 0.14–0.21.

### 7. Shi et al.

- **Single version (v1, 2020-07-08).** Table 3's "All" column:
  - .874 is the fully labelled set only;
  - .900 is F plus one partial set with standard losses;
  - **.921 is the marginal loss on all five sets;**
  - .931 adds exclusion.
- **The marginal-vs-full comparison is .921 vs .874.** Delta's .900 is not a marginal row.

### 8. Head identity (13 outputs, random logits)

- Territory-sum error is 1.3e-15, and the hierarchical territory equals Janus 0's argmax on 100 % of voxels.
- A plain argmax moves 4.8 % (logit scale 10), 16 % (scale 3) or 42 % (scale 1) of voxels across territories.

## What it changes

- **F-A6's B lines must be replaced before J1F-A is submitted** (ruling §8's trigger fires on OM2, and on OM1 and D2
  in some scenarios). Atlas v2's P1 gives calibrated per-class lines.
- **The scorer can be frozen by hash now** (P5), with the collapse under D47 Q1.
- **The stage-2 band should be 15 mm and territory-restricted** (P2), with a leakage gate (P3).
- **The launcher must validate on training cases only and decode in memory** (P6).

## Limits

- **clDice is a proxy for "≥ 50 % of the centreline within 1.5 mm".** It has no tolerance, so the rates in §1 are
  upper bounds in that respect.
- **The low-mode split s is unknown.** That is why every line takes its statistic's worst case.
- **Side branches traced by ImageCAS-X stand in for untraced ones.** Septals run into the septum, not along the
  epicardium, so their distances may differ.
- **One real case in the scorer validation,** plus the synthetic fixture.
- **I saw the title and four lines of Delta's round-2 note** in one grep output, and did not open it.
