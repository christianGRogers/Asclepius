---
tags: [plans/experiment, two-reads, fusion, acceptance, amendment-a10, amendment-a11, code]
author: Atlas
round: 4
updated: 2026-10-08
---

# Fusion and acceptance code for two reads, self-tested on simulated second reads

## Question

Ruling 3 (§5, Atlas item 3) asks the master to **implement A10 and A11** in its fusion and scoring code. Does the
code do what the rules say? This is a code test, not evidence about real annotators: real two-read behaviour is the
A12 wave-1 report.

## Method

`experiments/Atlas/fuse_reads.py`, using `trillium/atlas/lib/tf1.py` (identical to Delta's scorer on 6 pairs).

- **Training forms:** `a11_samples` (A11 default), `agree_or_ignore`, `both_as_samples`.
- **Case level:** `adjudication`. Triggers are inter-read macro tF1 < 0.80, ostium > 5 mm, carina (LM end) > 5 mm,
  and LAD↔LCx swap > 5 %. There is a geometric **ramus-only** exemption (the swap is the only trigger; the swapped
  voxels are one branch, ≤ 25 % of LAD+LCx, leaving within 10 mm of the carina), and `apply_d1b` resolves it.
- **Scoring:** `case_score` (mean tF1 against each read; an adjudicated read is replaced).
- **Acceptance:** `acceptance`, per-class paired bootstrap non-inferiority with margin 0.02.

Self-test `experiments/Atlas/fuse_reads_selftest.py`:

- read A = the projected proxy label of 3 real cases (c0000, c0050, c0125; split ImageCAS mask, territory, ramus →
  LCx);
- read B = A with one simulated disagreement each:
  1. the first 5 mm of LCx after the carina renamed LAD;
  2. the distal 15 % (by z) of the RCA dropped;
  3. all LCx within 12 mm of the carina renamed LAD;
  4. LAD and LCx swapped entirely.

Acceptance is checked on 100 synthetic cases: a model 0.01 above inter-read, and one 0.05 below.

## Result

| Simulated second read | `ignore` (A11), % of A's vessel voxels | `ignore` (agree-or-ignore) | Extent voxels kept as each read's own | Third read? | Ramus-only? | Inter-read tF1 | LAD↔LCx swap |
|---|---|---|---|---|---|---|---|
| 5 mm carina shift | 0.05–1.2 % | same | 0 | no | no | 0.992–0.999 | 0.1–2 % |
| Distal RCA truncation | **0** | **5.0–6.9 %** | 5–10 k voxels | no | no | 0.966–0.978 | 0 |
| 12 mm of LCx at the carina renamed | 1.4–3.9 % | same | 0 | no | in c0050 (swap 6.4 %, one branch at the carina); no in the others (swap < 5 %) | 0.978–0.992 | 2.9–6.4 % |
| LAD and LCx fully swapped | 47–61 % | same | 0 | **yes** (all 3) | no (swap 100 % > 25 %) | 0.50 | 100 % |

| Acceptance check (100 synthetic cases) | LM | LAD | LCx | RCA |
|---|---|---|---|---|
| model = inter-read + 0.01 | pass | pass | pass | pass |
| model = inter-read − 0.05 | fail | fail | fail | fail |

A model identical to read A, scored against reads A and B with a 5 mm carina shift, gets mean tF1 0.996–0.999.

## What it implies

1. **The code follows A10 and A11.**
   - Name disagreements become `ignore` in both samples.
   - Extent differences are kept: A11 keeps the truncated branch in read A's sample, whereas agree-or-ignore masks
     5–7 % of the vessel.
   - A wholesale swap goes to a third read.
   - A single carina-level branch swap is treated as ramus-only and resolved by D1b.
   - Non-inferiority passes and fails where it should.
2. **The A11 test will compare different things on extent-heavy disagreement.** On name-only disagreement the two
   forms produce the same `ignore` fraction. They differ only where reads differ in extent, which is exactly what
   the wave-1 report (A12) will measure.
3. **A reading the rules imply, made explicit.** A ramus-only case also lowers inter-read tF1. In the code the
   inter-read-tF1 trigger therefore does not send a ramus-only case to a third read on its own.

## Limits

- Simulated second reads on 3 cases test the logic, not the size of real disagreement.
- The ramus-only test is geometric. It cannot tell a ramus from an early diagonal: that is the D1b ambiguity itself,
  and Bridge's 88.2 % / 7.9 % applies.
- Bridge's decision extractor (one of the A11 triggers) is not wired into `fuse_reads.py`. It is a separate call, to
  be OR-ed in when the wave-1 pipeline is assembled.
- The port to `src/segtrain` (A9) is still to do.
