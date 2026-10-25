---
tags: [plans/experiment, statistics, A10, A30, A31, D6, D27, seal, power, round10]
author: Bridge
round: 10
updated: 2026-10-25
issue: christianGRogers/Asclepius#113
---

# On Janus 0's spread the 150-patient seal is under-powered unless reads and model fail on the same patients

**Question (A31.1, issue #113).** Round 9 put P(a human-level model passes A10 at 150 sealed patients) at 0.97,
computed on run 1's per-case tF1. Re-run on Janus 0's own spread: is 150 enough, or should the seal extend to
200–250 (D27)? And what rule should decide the extension on wave-1 reads?

**Answer.**
- On Janus 0's spread, **150 patients pass a human-level model 0.76 of the time** even if the pool is exactly as
  varied as ImageCAS val (Round 9: 0.97). 200 gives 0.91, 250 gives 0.97. The reason is that Janus 0's per-case
  tF1 is wider than run 1's in every class except RCA (LAD 0.126 vs 0.078; LCx 0.135 vs 0.111).
- **The answer turns on one unmeasured number:** ρ, how far model-vs-read and inter-read tF1 go down on the
  same patients. Round 9's model assumed ρ = 0. At ρ = 0.5, 150 patients pass 0.996 of the time, and 0.89 even if
  the pool is 1.2× more varied and reads 1.2× noisier.
- So the seal should **not** be extended on this surrogate. Wave 1 should measure the one quantity A10 depends on,
  **s_d** = SD over patients of (model-vs-read − inter-read) per class, which already contains f, k and ρ, and set
  the seal size from it by re-powering (rule C below), with the whole 100-patient reserve kept untouched until then.
- Bridge's own as-written trigger (f or k > 1.2 in any class) extends the seal 47–67 % of the time when nothing is
  wrong. A re-power rule extends 6–9 % of the time with the same power when extension is needed.

## Method

CPU only. Code: `experiments/Bridge/r10/power_r10.py` → `power_r10.json`; `extension_rule.py` →
`extension_rule.json`.

**Janus 0's spread.** Its per-case val tF1 is on Fir (`$SCRATCH/icx4/r9_tf1_val.json`), not in the repository.
What is here: the decisive per-class means (r9 scorer) and per-class 95 % bootstrap CIs on the same 80 cases
(Delta's scorer, expert ostia; #43). The per-case SD is recovered as (hi − lo) / 3.92 × √n. A surrogate per-case
distribution per class is then run 1's per-case shape on the same val 80 (atlas2 `per_case_run1.json`, unflagged
trees) mapped to Janus 0's mean and SD and clipped to [0, 1]:

| Class | Janus 0 mean (r9) | CI (Delta), n | Recovered SD | run 1 SD (Round 9's input) |
|---|---|---|---|---|
| LM | 0.945 | 0.924–0.977, 78 | 0.121 | 0.081 |
| LAD | 0.903 | 0.884–0.939, 80 | 0.126 | 0.078 |
| LCx | 0.857 | 0.835–0.894, 80 | 0.135 | 0.111 |
| RCA | 0.938 | 0.917–0.953, 75 | 0.079 | 0.079 |

SDs recovered from percentile bootstrap CIs are approximate (±10–20 %). The plan therefore pre-registers the exact
re-run on Janus 0's real rows (one CPU minute on Fir, `power_r10.py --val`), whose numbers replace these.

**Power model.** Round 9's, unchanged except for one parameter (the judge reproduced Round 9's version; this script
gives 0.972 on run 1 at n = 150 against Round 9's 0.966, the difference being the simulation seed). Model-vs-read per
patient is resampled from the class's per-case distribution with spread × f; inter-read with spread × k f; ρ
correlates the two within a patient. A class passes when the lower 95 % bound of mean(model − inter + δ) > −0.05
(D6); all four must pass. Scorable share per class as on val (LM 78/80, RCA 75/80).

## Results

P(all four classes pass), δ = 0 (the model is exactly as good as a second reader):

| n patients | f = k = 1, ρ = 0 | f = 1, k = 1.2 | f = k = 1.2 | f = 1.5, k = 1 | f = k = 1, **ρ = 0.5** | f = k = 1.2, ρ = 0.5 |
|---|---|---|---|---|---|---|
| 100 | 0.47 | 0.35 | 0.16 | 0.08 | — | — |
| **150** | **0.76** | 0.64 | 0.37 | 0.23 | **0.996** | 0.89 |
| 200 | 0.91 | 0.84 | 0.59 | 0.40 | 1.00 | 0.98 |
| 250 | 0.97 | 0.93 | 0.75 | 0.56 | 1.00 | 0.99 |
| 300 | 0.99 | 0.97 | 0.86 | 0.69 | 1.00 | 1.00 |

The binding classes are LCx, then LAD and LM; RCA passes ≥ 0.89 everywhere. With δ = −0.02 (a model 0.02 worse than
a reader, which D6 should still accept), P(pass) at 150 is 0.14 at ρ = 0 and 0.58 at ρ = 0.5.

**Why ρ matters so much.** A10's statistic is the per-patient difference d = model-vs-read − inter-read, and its SD
is s_d = √(s_m² + s_i² − 2ρ s_m s_i). At ρ = 0.5 and s_m = s_i, s_d falls by a factor √2 from the independent case.
Positive ρ is plausible (a low-contrast or motion-blurred scan is hard for the model and for the second reader
alike), but nothing in the repository measures it: every earlier read was simulated.

## The extension rule on wave-1 reads

The power depends only on s_d per class and the scorable share. Wave 1 measures s_d directly on non-sealed,
non-reserved pool patients (the D35 decision set and the open primary patients, about 49–61 by the end of the
QC-annotatable block, [[Bridge - A 35-patient D35 decision set is drawn from eight sources and is read by mid-queue]]).

**Rule C (proposed): choose the smallest of 150 / 200 / 250 whose re-powered P(all four pass, δ = 0) ≥ 0.80**,
computing P_c = Φ(0.05 √(n·keep_c) / ŝ_d,c − 1.96) from the measured ŝ_d; if 250 is still below 0.80, seal 250 and
report to the lead. The reserve patients not needed are then released to training.

**Rule C, simulated from the seal as it stands (150)**, with ŝ_d estimated on 49 wave-1 patients (normal per-case
differences, 4000 runs per row; `extension_rule.py`, `RULE_C=1`):

| Truth | True power at 150 / 200 / 250 | Rule C picks 150 / 200 / 250 | Power after | Mean seal |
|---|---|---|---|---|
| f = k = 1, ρ = 0 | 0.77 / 0.91 / 0.97 | 0.30 / 0.67 / 0.03 | 0.87 | 186 |
| f = k = 1, **ρ = 0.5** | 0.99 / 1.00 / 1.00 | **1.00** / 0 / 0 | 0.99 | **150** |
| f = 1, k = 1.2, ρ = 0.3 | 0.86 / 0.96 / 0.99 | 0.77 / 0.23 / 0 | 0.88 | 162 |
| f = k = 1.2, ρ = 0.5 | 0.84 / 0.95 / 0.99 | 0.66 / 0.34 / 0 | 0.87 | 167 |
| f = k = 1.2, ρ = 0 | 0.35 / 0.57 / 0.73 | 0 / 0 / 1.00 | 0.73 | 250 |
| f = 1.5, k = 1, ρ = 0 | 0.21 / 0.38 / 0.55 | 0 / 0 / 1.00 | 0.55 | 250 |

At 35 or 61 wave-1 patients the rows change by at most 0.04. The rule seals more only when the measured spread
asks for it, and stays at 150 when reads and model fail together.

**Against the as-written ratio trigger** (rule A: f or k > 1.2 in any class; rule B: the same re-power with f and k
instead of s_d; both simulated for the 200 → 250 step, `extension_rule.py`):

| Truth (wave 1 of 61 patients) | Power at 200 / 250 | A extends | B extends | Power after A / after B |
|---|---|---|---|---|
| f = k = 1 | 0.91 / 0.97 | **0.47** | **0.06** | 0.94 / 0.92 |
| f = 1.2, k = 1 | 0.72 / 0.85 | 0.96 | 0.91 | 0.85 / 0.84 |
| f = 1, k = 1.2 | 0.82 / 0.92 | 0.96 | 0.49 | 0.92 / 0.87 |
| f = k = 1.2 | 0.57 / 0.73 | 1.00 | 0.99 | 0.73 / 0.73 |
| f = 1.5, k = 1 | 0.38 / 0.55 | 1.00 | 1.00 | 0.55 / 0.55 |

At 35 wave-1 patients A's false alarm is 0.67 and B's 0.09. A re-power rule keeps nearly all of A's protection
and drops most of its false alarms, so it keeps about 50 patients' reads in training that A would seal for
nothing. The normal-form power used by the rules matches the resampling model within 0.03 (150: 0.768 vs 0.762;
200 at f = k = 1.2: 0.567 vs 0.592).

## What it changes

- **A31.1's trigger is replaced** by rule C on the measured s_d (fault and fix are Bridge's: v8 §5 set the ratio
  trigger without sizing its false-alarm rate).
- **The seal is not extended now.** Extending to 200 on the surrogate would withhold 50 patients (72 volumes) that
  ρ may show are not needed. Nothing is lost by waiting, provided the whole reserve stays untrained and uninspected
  until rule C has run, and rule C runs before the first pool fine-tune is trained.
- **Measure ρ explicitly in the wave-1 report** (per class, with a patient bootstrap CI). It is the number that
  decides how much of the pool acceptance costs.
- `experiments/Bridge/wave1/report_wave1.py` gains s_d, ρ and rule C (code, in this PR's §-referenced follow-up;
  the f/k columns stay as a report).

## Limits

- Janus 0's per-case shape is a surrogate (run 1's shape at Janus 0's mean and SD). The exact re-run is one command
  on Fir and is pre-registered to replace it.
- The pool's f, k and ρ are unknown until wave 1; the table brackets them.
- Classes are simulated independently; a patient who is hard in LAD is often hard in LCx, which makes "all four
  pass" a little more likely than shown. The tables are cautious in that direction.
