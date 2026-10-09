---
tags: [plans/candidate, bridge]
author: Bridge
round: 5
updated: 2026-10-09
---

# Bridge v5: the namer becomes a QA instrument, not a naming stage

## 0. Decision: improve by narrowing; no restart

Round 5 settled the question v4 existed to measure
([[Bridge - Trillium naming result on the master model]]):

- R − D = −0.013 [−0.025, −0.002]
- H − D = −0.013 [−0.022, −0.006]
- O − D = +0.010 [+0.005, +0.015]

By the A7 rule, neither R nor H is adopted. By my own pre-registered rule (O − D < 0.01 → thesis closed),
the headroom of 0.0097 closes the "structure out-names the network" thesis on the master model. I
withdraw it.

There is nothing to restart *to*. Bridge has no model recipe that beats the master, and v1's two-stage
segmentation lost in Round 1. What survives is where the evidence still points:

- the namer is a reliable, network-independent second opinion on *decisions*;
- the master's remaining naming errors are concentrated and structural.

v5 keeps only those roles.

## 1. Thesis (narrowest)

The master network names coronary trees well: 0.991 centreline name accuracy, no swaps. What it gets
wrong, it gets wrong in a few cases and in two shapes:

- the LM end misplaced;
- stretches of a vessel carrying the other class (D centreline accuracy 0.92–0.95 in 6 of 80 cases).

A structural namer is the right tool to **detect** both, and the wrong tool to **overwrite** them. It fails
on anatomy it cannot represent (absent LM) and on its own LM-end convention.

## 2. Recipe

### 2.1 Model, data, metric

The master (Atlas, A1–A14, D0–D5), unchanged. Bridge proposes no GPU work.

### 2.2 The namer's roles

| Role | What | Status |
|---|---|---|
| A4 QA of proxies | `segtrain.namer.disagreement`: ignore at name disagreements, wholesale exclusion, ramus exemption | Built; equal to the frozen run on 163 cases ([[Bridge - Implementation of namer]]) |
| A4 absent-LM guard | A label with no LM is never excluded on `lm`/`ostium`; it is marked for review | **New in v5**, built and tested. Two of the three Round-5 swaps were this variant |
| A11/A12 decision extractor | `extract_decisions` and `compare` flags as the adjudication trigger, plus the decision-vs-diffuse attribution | Built |
| **Structural audit of D (new, report only)** | On R1 val/test, flag cases where the master's LAD or LCx is not one connected subtree, or where the namer's LM end and D's differ by > 5 mm. A reviewer looks at them; no label is changed | CPU, proposed |
| A7 renaming (R) / grammar decoding (H) | Withdrawn as shipping candidates | Closed by Round 5 |

### 2.3 One pre-registered follow-up (CPU, on R1, optional)

**Gated subtree renaming:**

- **Rule.** Keep D's names, including D's LM, everywhere. Only where D's LAD or LCx is fragmented,
  i.e. a class not one connected piece of the skeleton, does R's LAD/LCx subtree assignment replace
  D's below D's own LM end.
- **Motivation (post hoc, so not claimable).** On the Round-5 val, outside the three swap cases, R's
  LAD/LCx tF1 was slightly above D's (+0.001/+0.006). R recovered 0.05–0.06 in the cases where D's
  names were diffuse.
- **Adoption** only by the A7 rule on R1 data not seen in Round 5: CI > 0 and no extra swaps.
  Otherwise it stays closed.
- **Cost:** CPU scoring only.

## 3. Evaluation

The master's own. Bridge's single test is the §2.3 rule; the §2.2 audit is a report.

## 4. Evidence

| Claim | Number | Note |
|---|---|---|
| Neither R nor H beats D | −0.013 / −0.013, CIs below 0 | [[Bridge - Trillium naming result on the master model]] |
| Naming headroom on D's lumen | +0.010, 74 % of it from 10 cases | same note |
| R's swaps are namer errors | 3/3 (2 absent-LM variants, 1 wrong split) | same note; checked on the thick masks |
| Absent LM in ImageCAS-X | 11 / 800 | same note |
| The library namer equals the frozen one | 0.896 vs 0.896 fully right, same failures, 163 cases | [[Bridge - Implementation of namer]] |

## 5. Risks

| Risk | Response |
|---|---|
| The audit flags too many cases for reviewers | Cap at the top-k by fragmentation; report the rate on R1 val first |
| The gated renaming was motivated on the Round-5 val | Tested only on unseen R1 data; pre-registered here |
| Proxy-scored conclusions differ on human reads | R1's human-read scoring decides (A10); the gate is re-tested there |

## 6. Cost

- **GPU:** 0.
- **CPU:** the audit and the §2.3 test take minutes per case set.
- **Human:** only the audited cases, if the master adopts the audit.

## 7. Changes since v4

- The A7 thesis is withdrawn after Round 5.
- R and H are removed as candidates.
- `segtrain.namer` is shipped and validated.
- An absent-LM guard is added to A4.
- A report-only structural audit of D is proposed.
- One gated renaming rule is pre-registered for R1.
