---
tags: [plans/experiment, round10, A31, A10, D6, D27, power, seal]
author: Foxtrot
round: 10
updated: 2026-10-25
issue: christianGRogers/Asclepius#113
---

# On Janus 0's spread the 150-patient seal passes a human-level model 78 percent of the time, so it should grow to 200 now

**Question (A31.1, Round 9 §6.2).** The seal was sized at 150 patients from run 1's per-case spread. Re-run on Janus 0's
own val spread, is 150 enough for A10 (D6: per class, non-inferior to inter-read tF1 within 0.05, all four classes),
or should the seal extend to 200–250 (D27)?

**Method.** `experiments/Foxtrot/r10/repower.py`. It uses Bridge's power model unchanged
(`experiments/Bridge/wave1/power.py`, the function A31.1 named):
- model-vs-read and inter-read per-case tF1 are resampled from a real per-case distribution;
- the pool spread is f × val's; the inter-read spread is k × the model's;
- a class passes when the lower 95 % bound of mean(model − inter + δ) > −0.05; all four classes must pass;
- each class keeps Janus 0's scorable share (LM 78/80, RCA 75/80, LAD and LCx 80/80).

**Janus 0's per-case file is on Fir only** (`$SCRATCH/icx4/r9_tf1_val.json`). Its per-class SD is therefore
recovered from the 95 % bootstrap CIs posted on #43 (SD ≈ CI width / 3.92 × √n). It is then imposed on run 1's
per-case shape: the model uses only deviations from the mean, so run 1's location does not enter.

**Check first:** with run 1's spread and Round 9's settings, the code gives 0.964 at n = 150. Bridge's Round 9 figure
is 0.966, so the code reproduces it (the test is in `experiments/Foxtrot/r10/test_r10.py`).

## Janus 0 is more spread out than run 1

| | LM | LAD | LCx | RCA | Macro |
|---|---|---|---|---|---|
| Janus 0 val per-case SD (from the CI) | 0.121 | 0.126 | 0.135 | 0.079 | 0.117 |
| Run 1 val per-case SD (Round 9's basis) | 0.081 | 0.078 | 0.111 | 0.079 | 0.064 |
| Ratio | 1.49 | 1.61 | 1.22 | 1.00 | 1.82 |

The means are higher, but Janus 0 has a heavier lower tail on the left tree: a few broken trees, as the CI's
asymmetry shows (macro 0.909, CI 0.880–0.932). The **LM and LAD SDs are per-class CIs from Delta's expert-ostium
scorer**, the only per-class CIs posted. Under the TotalSegmentator ostium of record, the left-tree means are
0.010–0.011 lower, and the SDs, if anything, larger.

## P(a human-level model passes A10), δ = 0

| Pool spread, inter-read spread | n = 150 | n = 200 | n = 250 |
|---|---|---|---|
| f = 1 (pool like val), k = 1 | **0.78** | **0.91** | 0.97 |
| f = 1, k = 1.2 | 0.66 | 0.85 | 0.93 |
| f = 1.2 (the A31 trigger line), k = 1 | 0.51 | 0.74 | 0.86 |
| f = 1.2, k = 1.2 | 0.39 | 0.61 | 0.75 |
| f = 1.5, k = 1 | 0.23 | 0.42 | 0.56 |
| *Run 1's spread (Round 9), f = 1* | *0.97* | *0.99* | *1.00* |
| *Run 1's spread, f = 1.5* | *0.62* | *0.81* | *0.90* |

- **At δ = −0.02** (a model 0.02 worse than a second reader), P(pass) is 0.14 / 0.29 / 0.41 at f = k = 1. So A10
  separates "as good as a reader" from "0.02 worse" only weakly at any size.
- **Per class:** LCx is the binding class in every row (0.90 at n = 150, f = k = 1). RCA passes almost always.

## What it means

1. **150 is not enough, even in the best case.**
   - On Janus 0's spread, a model exactly as good as a second reader fails A10 more than one time in five if the
     pool is like val. It fails half the time at the A31 trigger line.
   - Round 9's "0.79–0.97" rested on run 1's narrower spread.
   - Bridge's own extension rule ("extend to 200, or to 250 if the re-run power at 200 is below 0.8") already
     points to at least 200 at f = k = 1. It does so before any wave-1 read is seen.
2. **Extend the seal to 200 now, along the pre-registered order (positions 1–50), before any read exists.**
   - Doing it before wave 1 removes the f/k trigger's false-alarm problem for this step: it fires by chance
     54–71 % of the time at 30–50 patients (Bridge, `trigger_false_alarm.py`).
   - It also means the extension never depends on data that has been seen.
   - The 72 volumes are already refused by the wave-1 tools, so nothing changes for the annotators.
3. **250 buys +0.06 (f = 1) to +0.14 (f = 1.5).** It costs the only patients a pool decision set can come from
   ([[Foxtrot - After the seal and its reserve only 61 primary pool patients are open, so the D35 set must come from the extension order]]).
   The candidate proposes 200 + D35, and puts 250 to the lead as the alternative.
4. **The numbers are for Janus 0.** The final model is a fine-tune on pool reads, and its pool spread is what A10
   will see. If fine-tuning narrows the left-tree tail, power rises. If the pool is harder, f > 1, power falls.
   Wave 1 measures f and k on the open and D35 patients (n ≈ 111, false-alarm rate about 29 %), and the table is
   re-run then.

## Limits

- The SDs are recovered from CIs, not from the per-case file. **The lead can settle this with one file:**
  `$SCRATCH/icx4/r9_tf1_val.json` (val 80, no sealed case). `repower.py` then takes it in place of the CI-derived
  spread.
- Bridge's model treats the inter-read score as independent of the model's score, with k × its spread. The real
  relationship is unknown until wave 1.
