---
aliases: [Foxtrot ship choice a1 or E]
tags: [plans, experiment, janus1-L, D45, D46, ensemble, power, cpu]
status: done (CPU, 2026-11-15)
issue: christianGRogers/Asclepius#302
track: 1-L
---

# On real replicate runs, the two-run ensemble cuts the paired spread against the baseline by a quarter, so reading it in a1's place sharpens the one look

**Question.** [[Janus 1-L Round 1]] §5 item 1 asks whether the candidate read on the locked 100 should be **a1** (one
warm run) or **E** (the mean softmax of a1 and its replicate a2). It also asks how E would be tested without a second
look. D46 Q6 accepts an ensemble in principle if round 2 pre-registers it. This note measures what reading E *in a1's
place*, in the same H1 → H2 → H3 sequence, does to that one look.

**Code.** `experiments/Foxtrot/j1l_r2/ship_choice_sim.py` → `results/ship_choice_sim.json`
(sha256 `33f6fe2a…c2c`). It runs in 2 s on CPU and reads only the committed per-case files in `trillium-results/`.
No image, label, locked-100 score or sealed case is read.

## 1. Data: the only replicate pair on this network family

| Role in the simulation | Run | Source |
|---|---|---|
| Janus 0 (the baseline) | **B**, the Round 6 window-ablation run (from scratch) | `trillium-results/round6/atlas2/results/per_case_b.json` |
| a1 | **F0**, a 200-epoch warm fine-tune | `trillium-results/round7/atlas3/per_case_F0.json` |
| a2 | **F1**, the same warm fine-tune from the same base, with an FP term at weight 1e-4 | `…/per_case_F1.json` |

- All three were scored on the same val-80 cases, with A1 ostia and the pinned tF1, flagged classes left out (A1b).
- F0 and F1 are as close to a1/a2 as the repository has: same base, same schedule, same data. F1's extra loss term
  stayed at 0.0001 from first to last epoch (atlas3's `SUMMARY.md`), so the pair is a near-replicate.
- **E's per-case score is taken as the mean of its members' per-case scores.** That is an approximation. An
  ensemble's tree-F1 is not the mean of its members' tree-F1: where one member connects a branch and the other cuts
  it, E may do either. On average the approximation is neutral, and it gives E **no ensemble gain**. A gain
  (δ_E) is added separately, as a hypothesis.

## 2. Measured

| Quantity | Value |
|---|---|
| SD of the per-case paired difference, a1 − J0 (F0 − B) | **0.0455** |
| SD of the per-case paired difference, E − J0 ((F0 + F1)/2 − B) | **0.0339** (−25 %) |
| SD of the per-case difference between the two replicates (F1 − F0) | 0.0382 |
| Cases where the two replicates differ by more than 0.05 macro tF1 | **11 %** (9 of 80) |
| Mean F1 − F0 | +0.0047 (case SE 0.0043) |
| One-df estimate of the run-level term σ_g from that pair | **0.0013** |
| MDE (80 % power, two-sided 5 %, n = 100), a1 read | 0.0128 |
| MDE, E read | **0.0095** |

**What this says.**
- **The run-to-run noise on this family is per case, not per run.** The two replicates land 0.005 apart on the mean,
  inside case noise, so σ_g looks small (one df, so this is weak evidence; A37's floor of 0.012 is a ceiling here).
  This matches Atlas's finding in [[Atlas - Run-to-run noise in both measured pairs is per case, so a 35-patient decision set resolves about 0.02-0.035 tF1 and A22's 0.013 overstates it]].
- **But per case the replicates disagree a lot:** SD 0.038, and one case in nine moves by more than 0.05. A single
  run carries that per-case noise into every prediction it ships. Averaging two runs halves its variance per case.
- **That is what sharpens the paired test.** E − J0 carries half of the members' idiosyncratic noise, so its
  per-case SD drops by a quarter, and the MDE on the locked 100 falls from 0.013 to 0.0095.
- **Foxtrot v1's argument therefore changes ground.** v1 argued that E removes a seed lottery on the *mean*. The
  measured σ_g says that lottery is small. The real gain is per case: E's predictions are more stable patient by
  patient, and E's comparison with Janus 0 is less noisy.

## 3. Simulated: the one look with a1 or with E as the candidate

**Method.**
- Per draw, 100 cases are resampled with replacement from the 80. They are resampled jointly, so each case keeps
  its J0/a1/a2 structure.
- Every per-case difference is centred, then shifted by the true effect δ, plus run-level terms
  g₁, g₂ ~ N(0, σ_g²). E gets (g₁ + g₂)/2 + δ_E.
- H1's macro clause: the lower 95 % t-bound > −0.02. The Q4 bar (D46): the lower bound > −0.015. H3: the lower
  bound > 0. 20 000 draws per cell.
- Class guards, L3 and FP are not modelled. They act on both candidates alike to first order.

**P(pass) for a1 / E, with no ensemble gain (δ_E = 0):**

| True δ | σ_g | H1 (−0.02) | Q4 adopt (−0.015) | H3 (tF1 superior) | SD of the shipped model's true effect |
|---|---|---|---|---|---|
| 0 | 0 | 0.98 / **1.00** | 0.87 / **0.99** | 0.04 / 0.03 | 0 / 0 |
| 0 | 0.005 | 0.93 / **1.00** | 0.80 / **0.95** | 0.11 / 0.09 | 0.005 / **0.0035** |
| 0 | 0.012 | 0.80 / **0.93** | 0.68 / **0.81** | 0.25 / 0.23 | 0.012 / **0.0085** |
| +0.005 | 0.005 | 0.98 / 1.00 | 0.93 / 1.00 | 0.30 / **0.37** | 0.005 / 0.0035 |
| −0.010 | 0.005 | 0.57 / 0.76 | 0.30 / 0.38 | 0.003 / 0.000 | 0.005 / 0.0036 |
| −0.015 | 0 | 0.24 / 0.32 | **0.04 / 0.02** | 0 / 0 | 0 / 0 |

**With a modest ensemble gain (δ_E = +0.003), σ_g = 0.005:** at δ = 0, H3 rises from 0.11 (a1) to **0.23** (E); at
δ = +0.005, from 0.30 to **0.61**.

**Reading.**
- **A neutral model is adopted more often with E** under both H1 and the Q4 bar, because the interval is tighter.
  That holds with no ensemble gain at all.
- **A model truly at −0.015, the Q4 margin, is adopted less often with E** (0.02 against 0.04). The sharper test
  separates the margin better in both directions.
- **A model at −0.01 passes Q4 more often with E** (0.38 against 0.30). That is the rule doing what the lead set:
  −0.01 lies inside the −0.015 margin, so it *is* non-inferior by D46 Q4's definition. The margin is the lead's, and
  L-A7 forbids moving it.
- **H3 is not helped by the variance reduction alone** (0.11 against 0.09 at δ = 0). It is helped only if the
  ensemble really gains.
- **The shipped model's distance from its family mean shrinks by √2** (0.005 → 0.0035 at σ_g = 0.005).

## 4. What it does not show

- **No ensemble gain is measured.** The repository has no saved probabilities of two replicate runs, so E itself
  cannot be built here. δ_E is a hypothesis. External evidence gives its direction for Dice, not its size for tF1
  at M = 2 (Mehrtash et al., IEEE TMI 2020, doi:10.1109/TMI.2020.3006437, Table II, M = 50).
- **The pair is one pair, on val 80, from Round 7's recipe** (200 epochs, before D45). Janus 1-L's a1/a2 will
  differ in length and data. The real E − J0 SD is measured at the look and is reported beside the verdict.
- **The linear approximation could fail for tree-F1** where breaks are all or nothing. In one direction, two members
  that each draw a thin distal branch one voxel apart can average below 0.5 and break it. That risk is why E is
  read at the frozen export threshold t\* below 0.5, if Rule W picks one. In the other direction, a branch that
  only one member connects survives when its averaged probability clears t\*.

## 5. What it changes

- [[Candidates/Janus 1-L/Foxtrot v2|Foxtrot v2]] §1 pre-registers **E in a1's place**, in the same H1 → H2 → H3
  sequence, with one look. E − a1 is a report.
- The ground for E is now measured per-case stability and a sharper decision, not the mean seed lottery.
- No margin, guard or α changes.
