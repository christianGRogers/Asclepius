---
aliases: [Human decisions, D0]
tags: [plans, decision-record, human]
status: living
updated: 2026-10-11
---

# Human decisions

Decisions the judge ruled belong to the project, not the tournament (see
[[Round 1]] §5 and [[Round 2]] §5). Recorded as given by the project lead on
2026-10-05. They are binding on every candidate plan from Round 3 on; a plan
that contradicts one of them cannot win.

| # | Question | Decision | Status |
|---|---|---|---|
| D1 | Side-branch convention | **Territory.** A branch takes the class of its parent: diagonals → LAD, obtuse marginals → LCx, RCA's PDA and PLV → RCA. | Decided |
| D1b | Ramus intermedius | **LCx**, always. (Matches the ImageCAS-X → 4-class mapping already used in the tournament's experiments.) | Decided |
| D2 | Labelling order and double reads | **Every case is labelled twice**, by two annotators. The team is large enough for this. | Decided |
| D3 | tF1 gap tolerance | **1.5 mm.** A gap in a predicted vessel up to 1.5 mm long is forgiven; a longer gap counts as a break and everything past it scores as missed. | Decided |
| D4 | Starting labels shown to annotators | **No four-class starting labels.** Annotators start from the single-class ImageCAS segmentation (the original ImageCAS lumen mask, annotated by physicians) and split it into the four classes. | Decided |
| D5 | Redoing Girder-seeded cases | **Moot: no labelling has happened yet**, so nothing needs redoing. | Decided |
| D0 | Lumen convention | **The original ImageCAS mask** (the current Girder mask; "convention B / thick" in the tournament's terms), split into four classes, is the target, the seed and the reference. Confirmed after being told ~47 % of its voxels sit at 16–38 HU. ImageCAS-X is a secondary cross-check only. | Decided |
| D6 | Acceptance margin (A18) | **0.05 per class.** The final model is accepted if, for each of LM, LAD, LCx and RCA, its tF1 against the team's reads is non-inferior to inter-read tF1 within 0.05. | Decided 2026-10-11 |
| D7 | Redrawing the mask outline | **Keep the outline**, except where the original ImageCAS segmentation has a **major error**, which is expected to be rare. Such corrections are allowed and must be recorded in the case note. | Decided 2026-10-11 |
| D8 | Lumen target (supersedes D0) | **ImageCAS-X exactly as drawn.** The original ImageCAS masks are no longer considered usable as labels. | Decided 2026-10-11 |
| D9 | Class schema | **All 14 ImageCAS-X classes**, no grouping into four vessels: LM, LAD, LCx, D1, D2, OM1, OM2, IM, RCA, R-PDA, R-PLA, L-PDA, L-PLA, Other. Supersedes the four-class goal and D1/D1b's grouping. | Decided 2026-10-11 |
| D10 | What annotators start from (supersedes D4) | **The 14-class model's prediction, on all 1000 cases**, including the 800 that already have ImageCAS-X labels. Annotators correct it in SegQueue, which must gain the 14 classes. | Decided 2026-10-11 |
| D11 | Reads per case (supersedes D2) | **One corrected read on the 800 ImageCAS-X cases** (ImageCAS-X is the second, expert read) plus ~10 % blind duplicates there; **two reads on the 200 cases ImageCAS-X does not cover.** | Decided 2026-10-12 |
| D12 | Outline (supersedes D7) | **Annotators may freely redraw the outline to the contrast-filled lumen**, consistent with D8. | Decided 2026-10-12 |
| D13 | Required classes | **LAD, LCx and RCA must be non-empty to submit**; the other 11 classes are optional. | Decided 2026-10-12 |
| D14 | Case order | **ImageCAS-X cases first** (scored automatically against ImageCAS-X), then the 200 unlabelled ones. | Decided 2026-10-12 |
| D15 | Prelabel refresh | **Yes, once**: after ~300 corrected cases, fine-tune and regenerate prelabels for the cases not yet done. | Decided 2026-10-12 |
| D16 | Held-out test | **The 160 ImageCAS-X test cases are annotated last** and kept out of the D15 refresh, so they stay a fair test of the model. | Decided 2026-10-12 |
| D17 | More data and parallel build | **Top priority: source as many CCTA scans as possible, unlabelled included**, so annotator time is never idle. Everything new (14-class SegQueue, new data) is built **in parallel with the live system** and replaces nothing until the project lead validates it. | Decided 2026-10-12 |
| D18 | SegQueue14 defaults | **Accepted as built:** review if mean Dice vs ImageCAS-X < 0.60, or LAD/LCx/RCA < 0.70, or a read pair agrees < 0.60 (adjustable in the `segqueue14.reference` setting); new datasets queue after the 200 unlabelled ImageCAS cases and before the 160 test cases; each annotator's first five reads are always reviewed; deploy by merging into main and installing from there, after validation. | Decided 2026-10-12 |
| D19 | Extra data sources | **HeartSR included** (no licence stated; flagged, not to be redistributed until clarified). The project lead handles the access emails and sign-ups (vault: CCTA sourcing 2026-10 / Access request emails). Girder upload minimum chunk size lowered to 1 MB so large CT can be uploaded through nginx. | Decided 2026-10-12 |

## The restructure of 2026-10-11 (D8–D10)

The project lead found ImageCAS-X and restructured the project: one model is trained on
ImageCAS-X's 14 classes as drawn (`trillium/icx14`), it predicts all 1000 cases, and the
annotators correct those predictions in SegQueue. D0, D4 and the four-class grouping of
D1/D1b are superseded; the tournament's master plan below is kept as history. D2 (two
reads per case), D3, D6 and D7 are to be re-confirmed for the corrected-prelabel workflow.
SegQueue's 14-class setup and its validation are deferred by the project lead.

## What these change in the master plan

- **D0/D4:** the training target, the seed and the reference are
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
- **D1b:** the A8 ramus switch is set to LCx.
- **D3:** the tF1 tolerance is fixed at 1.5 mm; the one permitted change has been used to confirm it.
- **D5:** no relabelling cost under any option.
- **D6:** A10 is reinstated with a 0.05 per-class margin (A18 resolved). Bridge's power
  analysis (Round 6) is the basis: at 0.05 a model as good as a second reader passes most
  of the time on 100 sealed cases.
- **D7:** the reference stays the ImageCAS mask's extent, split into four classes; a read
  may depart from it only to correct a major error, and says so in its note. The A3
  convention monitor must not halt a wave for noted corrections, but still flags reads
  that redraw the outline without a note. Delta's proposed extent rule is therefore not
  adopted as a general rule.
