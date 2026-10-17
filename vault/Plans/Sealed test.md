---
aliases: [Sealed test]
tags: [plans, evaluation, decision-record]
status: frozen
updated: 2026-10-08
---

# Sealed test

The official sealed test set, computed under amendment A14 of [[Round 4]] and
published before any Trillium job ran. Machine-readable copy:
`trillium/sealed_test.json` (and `trillium/atlas/sealed_test.json`, where
`./delta` reads it). Script: `trillium/make_sealed_test.py`.

**Rule.** Every case an advocate declared as development (per-case output
inspected while choosing a rule, threshold or weight of a component that may
ship; `experiments/<Name>/dev_cases.txt`) is removed first. The rest are ranked
by `sha256('asclepius-sealed-round4:' + case_id)`; the first 80 ImageCAS-X test
cases and the first 20 quality-0 cases are sealed.

**Use.** Sealed cases are scored only at milestones, against team reads. They
are never used for a decision, a threshold or an inspection before then.

## Counts

| Group | Total | Excluded (development) | Sealed | Open |
|---|---|---|---|---|
| ImageCAS-X test | 160 | 44 | 80 | 36 |
| Quality-0 | 200 | 24 | 20 | — |

Declared development cases: Atlas 43, Bridge 152, Crucible 52, Delta 77.

**Consequence the judge should weigh.** Only 36 ImageCAS-X test cases are
both non-sealed and untouched by development. The 44 excluded development cases are also
non-sealed, but each was inspected by at least one advocate, so a decision that uses
them is biased toward whichever advocate tuned on them.

## Sealed ImageCAS-X test (80)

c0002, c0008, c0013, c0029, c0040, c0042, c0044, c0051, c0062, c0079, c0084, c0086, c0087, c0094, c0101, c0138, c0174, c0210, c0272, c0273, c0279, c0283, c0299, c0305, c0315, c0334, c0353, c0367, c0376, c0380, c0388, c0395, c0421, c0422, c0453, c0460, c0472, c0473, c0487, c0495, c0501, c0506, c0511, c0542, c0548, c0568, c0656, c0666, c0668, c0682, c0685, c0686, c0689, c0697, c0724, c0737, c0756, c0757, c0767, c0788, c0798, c0811, c0812, c0816, c0829, c0831, c0836, c0843, c0868, c0873, c0889, c0910, c0931, c0934, c0936, c0940, c0972, c0983, c0992, c0994

## Sealed quality-0 (20)

c0022, c0157, c0164, c0222, c0228, c0254, c0258, c0352, c0394, c0433, c0478, c0499, c0531, c0670, c0678, c0684, c0871, c0879, c0886, c0905

## Open ImageCAS-X test, never used in development (36)

c0068, c0102, c0123, c0195, c0251, c0271, c0323, c0327, c0340, c0416, c0430, c0435, c0447, c0470, c0545, c0592, c0617, c0620, c0624, c0644, c0660, c0726, c0758, c0772, c0805, c0807, c0824, c0827, c0841, c0877, c0908, c0946, c0957, c0971, c0984, c0996

## Non-sealed ImageCAS-X test cases excluded as development (44)

c0041, c0099, c0108, c0111, c0113, c0124, c0128, c0137, c0147, c0150, c0172, c0217, c0243, c0250, c0264, c0270, c0341, c0362, c0405, c0407, c0464, c0465, c0508, c0526, c0543, c0553, c0579, c0615, c0658, c0674, c0675, c0679, c0750, c0753, c0774, c0789, c0846, c0900, c0906, c0907, c0927, c0951, c0953, c0979
