---
aliases: [Kilo E7]
tags: [janus-m, experiment, power, paired-cohort, lge, transmurality, kilo, paired-scar, round3]
status: done
round: 3
path: jm/paired-scar
updated: 2026-10-30
code: experiments/JanusM/Kilo/e7_power_ja32.py
issue: christianGRogers/Asclepius#179
---

# Kilo E7: at the JA32 bars, the transmurality endpoint passes only if CT grades extent about as well as the LGE readers

**Question** (Round 2 ruling §7 item 2). JA32 sets three deciding endpoints, each judged on its 95 % patient-bootstrap
lower bound, once:
- segment sensitivity ≥ 0.75;
- segment specificity ≥ 0.93;
- transmurality agreement ≥ A_dev − 0.10, where A_dev is the LGE inter-reader agreement measured on the 40
  development patients.

How large must the seal be for ≥ 80 % joint power (JA28), under weak and strong clustering? How many patients does
≥ 270 ischaemic scarred segments need at 50 % and 70 % enrichment? And which endpoint binds?

**Answer.**
- **Sensitivity and specificity do not bind** under weak clustering. Sensitivity reaches ≈ 0.9 power at 120 patients
  (50 % enrichment) and ≈ 0.94 at 120 (70 %).
- **The ≥ 270-segment floor binds at 50 % enrichment.** At this model's 3.25 scarred segments per scar patient, it needs
  ≈ 170 patients at 50 % and ≈ 125–140 at 70 %. The merged engine's Golf model (4.0 per patient) gives 136 and 97.
  The number per patient is a cohort property, and development measures it.
- **The transmurality endpoint binds, and decides the study.** JA32's bar is a lower bound against a margin of 0.10.
  At ≈ 200–300 scar-on-both segments the lower bound sits ≈ 0.06–0.07 under the point estimate. The CT's point
  agreement must therefore come within ≈ 0.03 of the readers', not within 0.10.
  - At the extent error my Round 2 rule measured (SD 0.12, E5), joint power is ≈ 0.1 at any N up to 300.
  - It reaches 0.80 only when CT extent error is about the readers' own (SD 0.08 vs 0.07), and then only at
    ≈ 240–300 patients.
- **The development anchor is noisy.** A_dev from 40 patients spans 0.63–0.80 (5th–95th percentile) around a true
  0.72. Measuring it on every double-read patient (development + seal; JA32 already puts two readers on every
  patient) narrows that to 0.68–0.76. At sd_s 0.08 that raises joint power from 0.76 to 0.90 (300 patients, 50 %) and
  from 0.74 to 0.87 (200, 70 %).
- **The rule rewards noisy readers.** With noisier readers (agreement 0.56), the anchor falls below 0.60 in most
  studies. The endpoint then becomes report-only, and joint power rises to 0.80–0.90 at 140–200 patients, although
  the CT is no better.
- **A paired test** (CT against each single reader, minus reader against reader, on the seal) removes the anchor's
  noise but is stricter (CT vs a single reader 0.67 against CT vs adjudicated 0.70). It is not a fix, and is reported
  as a negative result.

## Method

`e7_power_ja32.py` is a CPU simulation with no image and no case id. Seed 20261030; 300 studies per cell, each with
a 300-draw patient bootstrap.

**Truth.**
- A share `enrich` ∈ {0.5, 0.7} of patients has one ischaemic scar in one territory. The AHA map is from secondary
  sources only (JA14), weighted LAD 0.5, RCA 0.3, LCx 0.2.
- A scar covers 1 + Binomial(n_territory − 1, p_k) segments, with p_k 0.45 (base) or 0.25 (smaller infarcts).
- True transmurality is Beta(1.6, 1.6).
- 17 segments per patient.

**CT** (E6's model; calibrated so pooled sensitivity ≈ 0.84 and specificity ≈ 0.98, Gatti 2025):
- detection logistic(−0.2 + 5 T + u) for a scarred segment and logistic(−4.3 + u) for a scar-free one;
- patient effect u ~ N(0, sd_u). sd_u = 0.8 is "weak" clustering (E6's ICC of CT-positive ≈ 0.03) and 1.6 is "strong".
  Strong clustering also lowers the pooled sensitivity to 0.81 and specificity to 0.96, so its rows mix both effects;
- graded extent T + N(0, 0.05) per patient + N(0, sd_s) per segment, with sd_s ∈ {0.08, 0.10, 0.13, 0.20}.

**LGE readers** (an assumption; no paired-reader Kim-bin agreement is quoted in this round's sources, and development
measures it):
- each reader detects a scar with probability logistic(1 + 12 T), about 0.98 pooled, and calls a scar-free segment
  with probability 0.01;
- each reads extent T + N(0, sd_r). sd_r 0.07 gives an inter-reader exact-bin agreement among scar-on-both segments
  of 0.72; sd_r 0.12 gives 0.56.

**Reference (JA32):**
- two independent reads;
- a third on any presence disagreement or a ≥ 2-bin difference;
- presence by majority; extent the median of three, else the mean of two.

**The rule, per study:**
- development: 40 patients, ≥ 25 with MI. A_dev = reader 1 vs reader 2 exact-bin agreement on scar-on-both segments;
- seal: N patients, scored against the reference;
- pass if all three lower bounds clear their bars. Transmurality is report-only if A_dev < 0.60 (JA32).

**Variants:**
- **P (paired):** the mean over readers of agreement(CT, reader k) − agreement(reader 1, reader 2) on the seal, lower
  bound ≥ −0.10.
- **S (pooled anchor):** JA32's statistic and margin, with the anchor measured over all double-read patients
  (`results_e7s_power_pooled_anchor.json`, `--only-s`).

## Results

### Calibration (20 000 patients per row)

| sd_s | CT sens / spec vs reference | CT tbin vs adjudicated reference | CT tbin vs one reader | Reader vs reader |
|---|---|---|---|---|
| 0.08 | 0.84 / 0.98 | 0.70 | 0.67 | 0.73 |
| 0.10 | 0.85 / 0.98 | 0.67 | 0.64 | 0.72 |
| 0.13 | 0.84 / 0.98 | 0.61 | 0.59 | 0.72 |
| 0.20 | 0.85 / 0.98 | 0.51 | 0.50 | 0.72 |

### Joint power at the JA32 bars (weak clustering, sd_r 0.07, p_k 0.45)

| sd_s | Enrichment | N = 120 | 160 | 200 | 240 | 300 |
|---|---|---|---|---|---|---|
| 0.08 | 50 % | 0.50 | 0.57 | 0.66 | 0.68 | 0.76 |
| 0.08 | 70 % | 0.57 | 0.69 | 0.73 | 0.73 | 0.79 |
| 0.10 | 50 % | 0.26 | 0.36 | 0.43 | 0.45 | 0.42 |
| 0.10 | 70 % | 0.38 | 0.41 | 0.47 | 0.50 | 0.50 |
| 0.13 | 50 % | 0.09 | 0.12 | 0.12 | 0.19 | 0.14 |
| 0.13 | 70 % | 0.09 | 0.10 | 0.14 | 0.15 | 0.16 |
| 0.20 | either | ≤ 0.03 | | | | |

Sensitivity power in the same rows is 0.85–0.96 at 120, and specificity power is 1.00 everywhere. The transmurality
endpoint is what holds joint power down.

### Strong clustering (sd_u 1.6)

At sd_s 0.08, 50 %, sensitivity power is 0.40 at 120 and 0.62 at 300, with specificity ≥ 0.96 from 140. Joint power
is ≤ 0.46 at 300. These rows also carry the lower pooled sensitivity (0.81), so they are a stress case, not a pure
clustering effect.

### Scarred segments (mean per study; P(≥ 270) in brackets)

| p_k (segments per scar patient) | 50 %: N = 140 | 160 | 200 | 70 %: N = 120 | 140 |
|---|---|---|---|---|---|
| 0.45 (3.25) | 227 (0.01–0.03) | 260 (0.31–0.35) | 325 (0.96–0.99) | 272 (0.52–0.64) | 318 (0.98–1.00) |
| 0.25 (2.25) | 157 (0.00) | 180 (0.00) | 224 (0.00); ≈ 250–300 needed (0.47 at 240) | 189 (0.00) | 219 (0.00); ≈ 170–200 needed |

### The anchor

| | 5th / 50th / 95th percentile |
|---|---|
| A_dev, 40 development patients | 0.63 / 0.72 / 0.80 |
| Pooled over development + seal (N = 120) | 0.68 / 0.72 / 0.77 |
| Pooled (N = 300) | 0.69 / 0.72 / 0.75 |

Joint power, JA32's anchor → pooled anchor:

| | N = 200 | 240 | 300 |
|---|---|---|---|
| sd_s 0.08, 50 % | 0.66 → 0.74 | 0.68 → 0.85 | 0.76 → 0.90 |
| sd_s 0.08, 70 % | 0.74 → 0.87 | 0.77 → 0.92 | 0.79 → 0.97 |
| sd_s 0.10, 50 % / 70 % | 0.43 → 0.40 / 0.44 → 0.45 | | |

### The noisy-reader paradox (sd_s 0.13, sd_r 0.12)

The anchor is 0.56, and it is < 0.60 in ≈ 75 % of studies (≈ 95 % when pooled). Transmurality is then report-only.

| | N = 120 | 160 | 200 |
|---|---|---|---|
| Joint power, 50 % | 0.70 | 0.79 | 0.85 |
| Joint power, 70 % | 0.77 | 0.82 | 0.87 |

Here CT transmurality is worse than in the sd_r 0.07 rows (0.58 vs 0.61), yet the study passes more often.

## What it changes

1. **Sizing (item 2).** Seal = max(120, the N for ≥ 270 ischaemic scarred segments, the N for 80 % power on
   sensitivity and specificity). The scarred segments per patient are measured on development. **Prefer 70 %
   enrichment** (≥ 30 % LGE-negative still holds): it needs ≈ 125–140 patients rather than ≈ 170 at this infarct size.
2. **Transmurality cannot be powered by more patients unless CT extent error is near the readers'.** Above sd_s ≈ 0.10
   the power curve is flat. JA28's "the seal may only grow at ≥ 80 % joint power" then has no finite answer. The
   re-powering must therefore cap growth (I propose 240) and say what happens at the cap: the transmurality endpoint
   is reported with its CI, and only presence can lose "not validated" (Kilo v3 §4).
3. **Anchor:** measure it on every double-read patient, with its own CI reported. The margin stays 0.10 (JA32).
4. **Close the noisy-reader loophole.** If the anchor is < 0.60, the Kim bin keeps "not validated" whatever happens.
   Only presence can be validated, because the reference itself cannot grade extent reproducibly.
5. **Reconciliation with the merged engine** (#187, `janusm.scar.power`). The two agree once matched on the CT's bin
   agreement; E9 runs the engine itself over it. The engine's default (Golf, q = 0.25) has CT bin agreement ≈ 0.81,
   above any anchor − 0.10 up to 0.8, so in its grid transmurality never binds. In both models the endpoint binds
   once CT agreement falls to within ≈ 0.03 of the anchor.

**Limits.** No real paired data. The reader model is assumed. E5's sd_s 0.12 is one synthetic LIE; the shared
benchmark's E-V / E-D agreement and development replace it.
