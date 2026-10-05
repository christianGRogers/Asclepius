---
aliases: [Human decisions, D0]
tags: [plans, decision-record, human]
status: living
updated: 2026-10-05
---

# Human decisions

Decisions the judge ruled belong to the project, not the tournament (see
[[Round 1]] §5 and [[Round 2]] §5). Recorded as given by the project lead on
2026-10-05. They are binding on every candidate plan from Round 3 on; a plan
that contradicts one of them cannot win.

| # | Question | Decision | Status |
|---|---|---|---|
| D1 | Side-branch convention | **Territory.** A branch takes the class of its parent: diagonals → LAD, obtuse marginals → LCx, RCA's PDA and PLV → RCA. | Decided |
| D1b | Ramus intermedius | Not yet stated (it has no single parent trunk under the territory rule) | **Open** |
| D2 | Labelling order and double reads | **Every case is labelled twice**, by two annotators. The team is large enough for this. | Decided |
| D3 | tF1 gap tolerance | Not yet decided; question re-asked explicitly | **Open** |
| D4 | Starting labels shown to annotators | **No four-class starting labels.** Annotators start from the single-class ImageCAS segmentation (the original ImageCAS lumen mask, annotated by physicians) and split it into the four classes. | Decided |
| D5 | Redoing Girder-seeded cases | **Moot: no labelling has happened yet**, so nothing needs redoing. | Decided |
| D0 | Lumen convention | Implied by D4: the team works from the original ImageCAS mask — the current Girder mask, "convention B / thick" in the tournament's terms. **Awaiting explicit confirmation.** | Pending confirmation |

## What these change in the master plan

- **D0/D4 (if confirmed):** the training target, the seed and the reference are
  all the original ImageCAS mask, split into four classes. This is the master
  plan's default (option B, the projected proxy). The A3 convention monitor runs
  in the direction that flags cases drawn *thin*. Crucible's randomised seed trial
  is withdrawn: no four-class seeds are shown, so there is nothing to randomise.
  The 0.19 tF1 mismatch cost ([[Crucible - A perfect segmentation in the wrong lumen convention loses 0.19 tree-F1]])
  applies only when comparing against ImageCAS-X, which becomes a secondary,
  cross-convention benchmark rather than the reference.
- **D1:** the proxy labels and the rule namer use the territory mapping
  (ImageCAS-X D1, D2, D-Other → LAD; OM, L-PDA, L-PLA, OM-Other → LCx; R-PDA,
  R-PLA → RCA). The trunk-mode comparison in A4 is no longer needed.
- **D2:** with every case read twice, the inter-rater ceiling is measured on all
  1000 cases, not on a 20–30-case subset, and every training case has two labels.
  How to use two reads per case in training (fusion, consensus, disagreement as
  `ignore`, soft labels, or both reads as separate samples) is now an open
  *technical* question for the tournament. See [[Fusing multiple annotations and learning from noisy labels]].
- **D5:** no relabelling cost under any option.
