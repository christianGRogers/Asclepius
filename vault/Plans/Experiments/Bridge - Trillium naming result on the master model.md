---
tags: [plans/experiment, branch-labelling, A7, A13, trillium, result]
author: Bridge
round: 5
updated: 2026-10-09
---

# On the master model, neither rule renaming nor grammar decoding beats the network's own names

## Question

The pre-registered A7 test, run on the Atlas master model (A13, inference only) and its 80 validation
cases, scored against Atlas's own proxy labels. Do rule renaming (R) or grammar decoding (H) of the
network's foreground name the tree better than the network does itself (D)? How much naming headroom
does D leave (O, oracle names on D's foreground)?

## Result

Per-case files: `trillium-results/round5/bridge/results/` (`results.json`, `cases/*.json`).

| Arm | tF1 @1.5 | LM | LAD | LCx | RCA | Cases with a swap |
|---|---|---|---|---|---|---|
| D, network names | **0.847** | 0.956 | 0.879 | 0.818 | 0.748 | 0 |
| R, rule renaming | 0.834 | 0.932 | 0.865 | 0.812 | 0.748 | 3 |
| H, grammar decoding | 0.833 | 0.910 | 0.875 | 0.814 | 0.748 | 0 |
| O, oracle names | 0.856 | 0.968 | 0.889 | 0.834 | 0.749 | 0 |

| Paired | Mean | 95 % CI | Better / worse cases |
|---|---|---|---|
| R − D | −0.013 | [−0.025, −0.002] | 22 / 51 |
| H − D | −0.013 | [−0.022, −0.006] | 20 / 51 |
| O − D | +0.010 | [+0.005, +0.015] | 63 / 5 |

**A7 verdict, as pre-registered:** neither R nor H is adopted. Both CIs lie below 0, and R adds swaps.
Under the other pre-registered rule ("O − D < 0.01 → the thesis is closed"), O − D = 0.0097 is just
under the line. **The claim that structure out-names the master network is refuted on this model.**

## Where R loses

- **All of R's net loss sits in 10 cases.** Across all 80 cases, R − D sums to −1.02. The worst 10
  cases sum to −1.13, so the other 70 are slightly *positive* (+0.11 in total).
- **Three swaps account for −0.70 of the −1.02.** All three are namer errors; D named these cases
  correctly. The namer was re-run on the ImageCAS mask for each:
  - **c0133 and c0956: absent left main.** ImageCAS-X has no LM voxels; the LAD and LCx arise
    separately, 2.5–2.8 mm apart. The rules always look for an LM bifurcation. On D's lumen they put it
    29–32 mm downstream, so the "LM" swallows the proximal LAD. On the thick ImageCAS mask the same
    rules still name LAD and LCx at Dice 0.95–0.99, so the error appears with the predicted lumen.
    11 of the 800 ImageCAS-X cases (1.4 %) have no LM.
  - **c0848: a plain wrong LAD/LCx split.** The namer fails on the thick mask too: LM 31.5 mm, and most
    of the LCx named LAD (LCx Dice 0.24). The scored reference has no LM centreline in this case.
- **The LM boundary is the other loss.** R's LM tF1 is −0.024 (35 cases worse by more than 0.02). The
  namer ends the LM at a different point from the proxy's ImageCAS-X convention, and a few mm on a
  ~10 mm vessel costs a lot of LM tF1. Excluding the three swap cases, R's LAD (+0.001) and LCx (+0.006)
  are slightly *better* than D's; the loss is the LM.

## Where H loses

- H has no swaps. Its whole loss is the **LM**: −0.046 mean, with 34 cases worse by more than 0.02.
  Examples: c0311 LM −0.89, c0733 −0.68.
- The connected-LM grammar with a 0.5-nat LM prior moves the LM end; it does not fix anything D got
  wrong.
- H's per-case gains do not track the oracle headroom (correlation −0.07).

## What the +0.010 oracle headroom consists of

- **It is concentrated.** 0.54 of the 0.77 summed gain comes from 8 cases with O − D > 0.03.
- **There are two kinds:**
  1. **D's LM end in the wrong place:** c0424 (LM +0.29), c0225 (+0.25), c0368 (+0.10).
  2. **Diffuse LAD/LCx mislabelling:** c0866, c0024, c0717, c0973, c0741, c0311. D's centreline name
     accuracy in these is 0.92–0.95: stretches of a vessel carry the other class. This is exactly what
     subtree inheritance fixes. R recovers part of it (c0024 +0.064, c0866 +0.053, c0717 +0.049), and
     in the 12 cases with O − D > 0.02 R is better than D in 6.
- RCA headroom is about 0.

## Reading

- The master network names well: centreline name accuracy is 0.991, with no swaps.
- The rules help where D's names are structurally inconsistent, but they hurt more:
  - where the anatomy breaks their model (absent LM);
  - where their LM-end convention differs from the label convention.
- A variant the rules cannot represent also matters for **A4**. The `lm`/`ostium` wholesale triggers
  would exclude correct proxies of absent-LM cases.

## Caveats

- One model, one fold, 80 cases, scored against proxies. Ostia come from the reference (provisional
  per A9).
- Whether the namer's own decisions are right was checked only for the three swap cases, on the thick
  mask.
- The R1 human reads, not the proxies, are the deciding reference.
