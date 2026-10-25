---
tags: [plans/experiment, round10, A31, A10, D6, D27, seal, power]
author: Atlas
round: 10
updated: 2026-10-25
issue: christianGRogers/Asclepius#113
code: experiments/Atlas/r10_seal_power.py
---

# On Janus 0's own spread, the 150-patient seal passes a human-level model 0.79 of the time if reads vary independently of the model, and more if hard cases are shared

**Question.** Round 9 (A31.1) asked for the A10 power table to be re-run on Janus 0's own per-case val tF1 before
the seal size is fixed. Is 150 enough, or should the seal extend to 200–250 (D27)?

**Method.**
- Bridge's power function, `experiments/Bridge/wave1/power.py`, which Round 9 reproduced exactly:
  - per-case model-vs-read tF1 is resampled from a base distribution per class, with spread f × base;
  - inter-read is an **independent** draw with spread k × f × base;
  - a class passes when the lower 95 % bound of mean(model − inter + δ) > −0.05 (D6), and all four must pass.
- **Base distribution.** Janus 0's per-case file is on Fir. The base here is run 2 B's per-case per-class tF1 on the
  same 80 val cases, linearly rescaled to Janus 0's per-class mean and its CI-derived SD (#43), and clipped to [0, 1].
  The CI → SD conversion matches run 1's direct SD to 0.0002.
  - Base SD: LM 0.118, LAD 0.122, LCx 0.135, RCA 0.073.
  - Round 9's base (run 1): 0.081, 0.078, 0.111, 0.079.
- **Scorable shares:** LM 78/80, RCA 75/80 unflagged (val).
- **Check:** on run 1's base, the function gives 0.972 at n = 150, f = k = 1 (Round 9: 0.966; simulation noise).
- **Added:** a correlated variant, where the inter-read score of a case shares a fraction ρ of the model's deviation
  on that case (hard images are hard for readers too). ρ = 0 is Bridge's model.

## Results: P(all four classes pass), k = 1

| f | δ | ρ | n = 150 | 200 | 250 | Binding class at 150 |
|---|---|---|---|---|---|---|
| 1.0 | 0 | 0 | **0.789** | 0.928 | 0.972 | LCx 0.89 |
| 1.0 | 0 | 0.3 | 0.960 | 0.993 | 0.999 | |
| 1.0 | 0 | 0.5 | 0.996 | 1.000 | 1.000 | |
| 1.25 | 0 | 0 | 0.479 | 0.705 | 0.837 | LCx 0.73 |
| 1.25 | 0 | 0.3 | 0.767 | 0.913 | 0.966 | |
| 1.5 | 0 | 0 | 0.246 | 0.452 | 0.586 | LCx 0.57 |
| 1.0 | −0.02 | 0 | 0.148 | 0.307 | 0.437 | LCx 0.49 |
| 1.0 | −0.02 | 0.5 | 0.617 | 0.822 | 0.915 | |
| 1.0 | −0.03 | 0 | 0.013 | 0.040 | 0.068 | |
| 1.0 | −0.05 | 0 | 0.000 | 0.000 | 0.000 | |

With k = 1.2, every entry is lower: 0.679 / 0.858 / 0.939 at f = 1, δ = 0. The full grid is in
`experiments/Atlas/r10/seal_power.json`.

## Reading

1. **Round 9's 0.97 at 150 does not survive Janus 0's spread.** Janus 0's per-case tF1 varies 1.2–1.6× more than
   run 1's in LM, LAD and LCx (RCA about the same), because the ImageCAS-X reference traces further. Under Bridge's independent-draw model,
   a model exactly as good as a second reader passes at 150 patients **0.79** of the time even if the pool varies
   like val. That is below the 0.8 that Bridge's own extension rule uses. It is 0.93 at 200 and 0.97 at 250. The
   binding class is always the LCx.
2. **The independent-draw model is the conservative end.** If a hard image lowers both model-vs-read and inter-read
   tF1 (ρ > 0), the contrast's variance falls by 2ρσ². At ρ = 0.3, 150 patients give 0.96. Nothing measured so far
   says what ρ is, but **wave 1 measures the contrast directly**: model-vs-read and inter-read on the same patients.
3. **A mean offset matters far more than the spread.** At δ = −0.02, no seal size in D27's range reaches 0.5 under
   independence. δ < 0 is exactly what seed-anchored reads produce
   ([[Atlas - Seed-anchored reads can fail a human-level model under D6, and the A31.2 seed flag does not see it]]).
   Extending the seal cannot fix an anchoring offset. Only L5 or the reads can.
4. **f/k > 1.2 is a noisy trigger.** It fires 54 % of the time by chance at 50 patients (Bridge's own simulation),
   and it ignores ρ.

## What it changes

- **Do not change the seal now.** The deciding number, the per-patient contrast SD, is measured on wave 1's
  non-sealed primary patients, which are exactly the D35 decision set plus the 26 trainable patients.
- **Proposed A31.1′ (replaces "f or k > 1.2 → extend").**
  - Re-run the power on the **measured contrast**: per patient, model-vs-read minus inter-read, per class, on the
    primary non-sealed patients with two reads (≥ 50 patients).
  - The seal takes the smallest of 150 / 200 / 250 whose power at δ = 0 is ≥ 0.8, both at the measured contrast SD
    and at its patient-bootstrap 80th percentile (the cautious side, as Bridge intended).
  - If 250 is still under 0.8, report to the lead; the seal grows no further by rule (as A31.1).
  - The f/k table stays as a report.
- **Read beside the size decision, not instead of it:** the mean contrast δ̂ and the anchoring signature (the
  precision–recall gap). A δ̂ near −0.02 is an L5 question, not a seal-size question.
- **Limits.**
  - The base is a rescaled run-2 shape, not Janus 0's own per-case file. `--janus0 $SCRATCH/icx4/r9_tf1_val.json`
    reruns everything on the real file in seconds.
  - Bridge's model resamples patients rather than using one volume per patient. The patient as the unit is kept.
