---
tags: [plans/candidate, bridge, statistics]
author: Bridge
round: 6
updated: 2026-10-10
---

# Bridge v6: make the final evaluation able to say "human-level"

## 0. Position

Bridge v5 stands: naming goes to the network, and the namer is QA only (A4 with the absent-LM guard,
the A11 decision extractor, a structural audit). v6 adds nothing to the model. It answers Round 6 Q3
and proposes changes to the **evaluation**. Evidence:
[[Bridge - At n = 100 the A10 rule rejects a human-level model, and most open-set tests cannot see their effect]].

**One retraction.** My v5 §2.3 "gated subtree renaming" is withdrawn. Its plausible gain (≤ ~0.005) is
below the MDE on the 36 clean open cases (0.011–0.026), so the test could not decide anything. The
structural audit stays as a report.

## 1. Findings

1. **A10 as written rejects a human-level model.** With a per-case contrast SD of 0.14–0.19, a model
   exactly at inter-read level (δ = 0) has these chances of passing:
   - 20–32 % per class;
   - about **0 %** on all four classes;
   - 6 % even after trimming the tails.

   Passing with 70 % probability needs δ ≈ +0.04 in every class. In practice this is a superiority
   test. The type-I side is fine.
2. **What the sets can see** (80 % power, macro):
   - retrained-model contrasts: ≈ 0.020 at n = 100 and 0.022 at n = 80;
   - same-prediction contrasts: 0.007–0.015;
   - per class: LM and RCA are 2–3 times worse.
   - The 27–36 open cases detect about 0.016–0.039. Delta's P1′ headroom (≤ 0.004) and my renaming gain
     cannot be seen there.
3. **Multiplicity.** About 11 "adopt if CI excludes 0" decisions feed one final model. Under a global
   null that is a 24 % chance of at least one false adoption, mostly on the reused val 80.
   - Per-class results and forced choices need no correction.
   - A10's all-classes rule is an intersection-union test, so it needs none either.
   - The open issue is cumulative adoption, plus an unspecified number of sealed-test "milestones".
4. **FP gate and epoch rule** are point-estimate rules near their thresholds:
   - a true FP rate of 1.1 passes 16 % of the time;
   - a true epoch gain of 0.01 is called "< 0.01" 49 % of the time.

## 2. Proposed amendments

| # | Change | Cost |
|---|---|---|
| E1 | **A10 margin, a human decision taken with the power table:** either (a) a 0.05 margin per class, with macro primary at 0.04; or (b) 0.02 on macro only as the primary, per class descriptive with a floor (no class point estimate below −0.05). Frozen before the sealed reads are scored. | none |
| E2 | **The A1b review before sealed scoring is mandatory.** Removing artefact tails roughly doubles A10's power. | reviewer time already budgeted under A1b |
| E3 | **Re-estimate the A10 contrast SD on wave-1 reads** (the R1 model scored against real double reads, on CPU) before E1 is frozen. | CPU |
| E4 | **One decisive look at the sealed test** (the final model), plus at most one pre-declared interim look that changes no decision. | none |
| E5 | **Every decision table states its MDE at its n.** A test whose expected effect is below the MDE is reported-only, and the default stays. On this basis P1′ and the gated renaming are closed now. | none |
| E6 | **A final confirmatory test of the stacked recipe:** final model vs the R1 baseline, paired, on the sealed test. Training-recipe adoptions must also keep their sign on the open 36. | none |
| E7 | **FP gate:** the point estimate on the 100 sealed cases decides, with the CI reported. **Epoch rule:** keep 250 epochs only if the upper CI of the gain is < 0.02. | none |

## 3. What this changes for each owner

- **Atlas:** decision tables gain an MDE column (E5). The epoch rule gains a CI condition (E7). The
  final report adds the confirmatory test (E6).
- **Crucible:** `reads.acceptance` already supports `classes=` and `margin=`, so E1(b) needs no code.
  E3 belongs in the wave-1 (A12) report.
- **Delta:** P1′ is closed by E5. The open-36 predictions can go to the A1b flag-rate count, where 36
  cases give a usable ±0.13.
- **The clinical lead:** decides E1, using the table in the evidence note.

## 4. Risks

| Risk | Response |
|---|---|
| The simulated contrast SD is wrong for real reads | E3 re-measures it before E1 is frozen |
| A wider margin accepts a worse model | The type-I side stays at ≤ 7 % per class at the margin; E1(b) adds a per-class floor |
| Fewer adoptions (E5) leave real small gains on the table | The gains in question are ≤ 0.005 and cannot be confirmed at any available n |

## 5. Cost

No GPU. CPU only for E3.
