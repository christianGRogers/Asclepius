---
aliases: [Master plan]
tags: [plans, master]
status: living
round: 2
updated: 2026-10-04
---

# Master plan

**In force: [[Atlas v2]], as amended by the judge in [[Round 2]].** Won round 1
(as [[Atlas v1]]) and held the title in round 2 against [[Bridge v2]],
[[Crucible v2]] and [[Delta v2]]. All three challengers now keep the master's
model, data, schedule and deciding metric, and compete on additions to it.

The plan text is the candidate file; the amendments below are binding and
override it where they conflict. Full reasoning, scorecards and what would
change the ruling: [[Round 2]] (and [[Round 1]] for history).

## In one paragraph

One four-class nnU-Net v2 ResEnc model, trained directly at 0.5 mm isotropic
with a 256³ patch (a 128 mm patch holds the whole tree in ~98 % of cases), a
fixed CT window instead of nnU-Net's automatic one, mirroring off. Training
starts now on proxy labels — ImageCAS-X's per-branch names projected onto our
cases — and team labels replace the proxies case by case as they arrive.

## Binding amendments (as of Round 2)

Round 1's A1–A6 as revised in Round 2, plus A7–A9. The full wording is in
[[Round 2]] §1; this is the summary.

- **A1 — ostium:** tree-F1 (tF1 @ 1.5 mm) decides everything. The ostium is
  aorta contact (TotalSegmentator, ≤ 5 mm), cross-checked by Delta's two cheap
  rules; disagreement > 5 mm is flagged for a human.
- **A2 — false positives and bridging:** the FP-component gate is computed on the
  **raw** prediction, before any repair. Delta's bridge audit is binding. 3 mm
  bridging alone stays switchable but is weak (+0.01 tF1; 5 of 12 joins were FP).
  Gap-centred re-inference + support-gated bridging (P1′) is a candidate, unproven.
- **A3 — one convention:** a per-case convention monitor on every labelling wave
  (halt the wave if > 10 % is in the wrong convention), seed tagging, and a
  single-convention sealed test. The lumen convention itself is a human decision.
- **A4 — QA namer:** voxel `ignore` only near the carina where proxy and rule
  namer disagree; cases with wholesale disagreement are excluded until reviewed.
- **A5 — calibre trigger** and **A6 — R0 benchmark first:** unchanged.
- **A7 — rule renaming competes with the model's own names** (ship only if the
  paired tF1 CI excludes 0 and swaps do not rise); save softmax at val/test so
  Bridge's hybrid decoding can be scored later.
- **A8 — the ramus rule is a switch** set from the humans' written rule.
- **A9 — one implementation:** only the ported `src/segtrain` tF1 may decide.

## Open human decisions

Lumen convention (a perfect model in the wrong convention loses 0.19 tF1);
side-branch and ramus rule; labelling order; the tF1 tolerance; whether
annotators see 4-class seeds; whether Girder-seeded cases are redone. See
[[Round 2]] §5.
