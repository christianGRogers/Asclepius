---
tags: [plans, candidate, tree-f1, ostium, extent, miss-census, a1c, round8]
author: Delta
round: 8
version: 8
updated: 2026-10-11
---

# Delta v8: the taxonomy held; the remaining error is the reference's, so the next lever is the labelling rule, not the model

## 1. Decision: improve

[[Delta - Phase A confirms the RCA was an ostium artefact, and the remaining loss is mask vessel without contrast]]:

- **The pre-registered falsifier passes as written.**
  - Unflagged RCA scores 0.883 (≥ 0.85).
  - The order is LM 0.966 > LAD 0.901 ≈ RCA 0.883 > LCx 0.846.
  - The gain is 0.112 (≥ 0.07).
  - The Q2 taxonomy survived its test. The like-for-like gain is 0.065–0.067, which I report alongside.
- **The miss census locates the remainder.**
  - The model recalls 93–97 % of expert-traced centreline in every class.
  - Most remaining recall loss is ImageCAS-mask vessel that ImageCAS-X does not trace (55 % / 67 % / 28 % of it lost for LAD / LCx / RCA). On the 17 cases with a CT, it has median HU 39–91, against an aorta of 472.
  - The precision loss is mostly predicted vessel outside the mask.
  - Naming and connectivity cost ≤ 0.03 per class.
- **The A1c checks pass on run 1's predictions.** 116 of 116 are bit-identical, and the new field lists exactly 6 cases (6 of my 7; the seventh has no prediction). The opt-in fallback changes nothing decisive. It does expose 2 LM errors (LM about 0.29) that the default hides.

## 2. Proposals

### A. Make the fallback centreline the default for per-class reporting, before A10's margin is frozen (A1c; judge's decision)

- The Round 7 deadline is wave 1. The evidence now covers all 116 run-1 predictions: there is no decisive change (the 6 cases are all A1b-flagged), while 2 of 6 LM scores move from silently absent to visibly wrong.
- A per-vessel A10 needs those LM cases scored.
- **Proposal:**
  - `fallback_centreline=True` becomes the decisive default from the next hash on;
  - the old default stays available for paired reports;
  - tests 5–8 are already in place.

### B. An extent rule for team reads, now with location evidence (for the labelling lead; supersedes v7 §2B)

- D0 keeps the ImageCAS mask as the target.
- The census shows that the training target contains vessel the image does not support (median 39–91 HU) and that experts do not trace, and the model leaves 55–67 % of it on the LAD and LCx.
- A model cannot learn which of these an annotator included. This is the dominant remaining loss after the ostium fix.
- **Proposal:** the two-read protocol states one extent rule ("lumen with contrast, ≥ 1 mm diameter, to where it is no longer distinguishable"). Crucible's A3 monitor reports, per read, the share of centreline below 0.3 × aortic HU.
- No metric change follows from this.

### C. Report-only diagnostic (CPU; no hash change)

- Report `tF1 on contrast-supported reference` next to every decisive tF1: the reference centreline below 0.3 × median aortic HU is excluded from recall.
- It answers, per model, "how much of the gap is the mask's extent".
- It decides nothing; the decisive tF1 is unchanged. A1c governs only if it is ever made decisive.

### D. No new GPU experiment from me

The model-side levers have little to act on: recall on traced vessel is 93–97 %, and naming plus connectivity is ≤ 0.03. Atlas's window ablation (−0.0027, a tie) fits this. If the humans adopt the extent rule, the experiment that would matter is retraining on team reads, which is wave 1's job, not a Delta arm.

## 3. Risks

| Risk | Response |
|---|---|
| Mask-only low-HU vessel is real, tiny vessel the model should learn | Then the extent rule says so and readers draw it consistently. The census re-run on wave-1 reads shows whether recall on it rises |
| The HU check covers 17 cases with a bias toward the round-5 artefact cases | The CTs of all 80 val cases are on Trillium. A CPU re-run there (about 1 h) would replace the 17-case estimate. Proposal only |
| The fallback default changes per-class LM numbers in about 5 % of cases | Paired reports under both hashes, as Round 7 requires; the decisive macro is unchanged on run 1 |

## 4. Changes since v7

- Falsifier scored: it passed, with the like-for-like caveat.
- Miss census done: remaining loss located in mask-only, low-HU vessel.
- A1c tests 3 and 8 done on run-1 predictions.
- The fallback is proposed as the default.
- The extent rule is restated with the census evidence.
- A report-only contrast-supported diagnostic is added.
