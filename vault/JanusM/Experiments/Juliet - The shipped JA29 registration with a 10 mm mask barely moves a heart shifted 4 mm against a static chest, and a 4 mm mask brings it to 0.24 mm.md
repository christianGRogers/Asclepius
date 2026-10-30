---
tags: [janus-m, experiment, registration, lie, path-b, round3]
author: Juliet
round: 3
path: jm/paired-scar
updated: 2026-10-30
issue: christianGRogers/Asclepius#179
code: experiments/JanusM/Juliet/r3/shipped_reg.py
---

# E10: the shipped JA29 registration with a 10 mm mask barely moves a heart shifted 4 mm against a static chest; a 4 mm mask brings it to 0.24 mm

## Question

E8 found that JA29's metric mask (classes 1–4 dilated 10 mm) admits enough static chest to pull rigid MI back toward
R0. That was with the benchmark's SimpleITK reference. Does the **shipped** module, `janusm.scar.registration`
(#181/#188, at `jm/paired-scar` `1524550`), show the same, and does a 4 mm mask fix it?

## Method

**Cases.** The shared benchmark's generator (`bench_lie/bench.py`); each heart goes through `janusm.guard.refuse`
first. 21 hearts: 20 real plus the phantom; 3 were skipped for no LV contrast.

**Conditions.** Blood equal to scar, under three settings:
- **rigid, CNR 5:** the heart moves 4 mm / 2° against the static chest;
- **rigid, CNR 3:** the same;
- **none, CNR 5:** aligned scans.

**The module.** `prepare_first_pass` and `register_lie` exactly as shipped: Mattes MI, Powell, two levels, 30k samples.
- `MASK_DILATION_MM` is set to 10 (JA29) or 4 before `prepare_first_pass`.
- The QC cuts are set to −1, so R0 always fails and the rigid and affine stages run on every case.
- **Residual** = the mean distance over the truth wall between the module's transform and the true map.

The run was interrupted once by a container restart and resumed from its log. Hearts already complete were kept.

## Result

Residual in mm, median / p90 over 21 hearts:

| Condition | R0 | **10 mm: rigid** | 10 mm: affine | **4 mm: rigid** | 4 mm: affine |
|---|---|---|---|---|---|
| rigid, CNR 5 | 4.23 | **3.40 / 4.24** | 2.92 / 3.89 | **0.24 / 0.67** | 0.34 / 1.62 |
| rigid, CNR 3 | 4.26 | **3.28 / 4.13** | 2.89 / 4.05 | **0.26 / 0.78** | 0.59 / 2.41 |
| none, CNR 5 | 0 | 0.12 / 0.18 | 0.12 / 0.20 | 0.28 / 0.41 | 0.43 / 1.90 |

1. **The shipped module with JA29's 10 mm mask hardly registers.** The median residual is 3.4 mm, from 4.2 mm at the start.
   That is worse than E8's SimpleITK reference (1.24 mm). The shipped Powell search on 30k sampled points settles near
   the start when much of the mask is static.
2. **With a 4 mm mask it lands at 0.24–0.26 mm (median),** inside the 0.5 mm tolerance of Juliet R2 E6.
3. **On aligned scans the 4 mm mask costs 0.16 mm** (0.28 against 0.12). JA29's QC-first order keeps R0 there anyway.
4. **Affine on the 4 mm mask is sometimes worse than rigid** (p90 1.6–2.4 mm). JA29's rule, keep affine only if it
   lowers the QC values, is needed, and it should compare against rigid on the same mask.

## What it changes

- **A2 holds on the shipped code.** Set `MASK_DILATION_MM = 4.0` in `janusm.scar.registration` (one constant), and
  add `rim_dark` to its QC. This is a `role:swe` item if the judge adopts A2.
- **Until then, the shipped registration should not grade any paired patient whose heart moved between scans.**
- **Limits.**
  - Synthetic LIE and one blood level.
  - The QC was forced, so this measures the stages, not the chain's choice.
  - 21 hearts.
