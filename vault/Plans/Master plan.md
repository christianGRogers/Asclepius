---
aliases: [Master plan]
tags: [plans, master]
status: living
round: 3
updated: 2026-10-08
---

# Master plan

**In force: [[Atlas v3]], as amended by the judge in [[Round 3]].** Won round 1
(as [[Atlas v1]]) and held the title in rounds 2 and 3; round 3 was against
[[Bridge v3]], [[Crucible v4]] and [[Delta v3]]. All three challengers now keep the master's
model, data, schedule and deciding metric, and compete on additions to it.

The plan text is the candidate file; the amendments below are binding and
override it where they conflict. Full reasoning, scorecards and what would
change the ruling: [[Round 3]] (earlier: [[Round 2]], [[Round 1]]).

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

## Round 3 changes (summary; full wording in [[Round 3]] §1)

- **A1:** ostia found per tree component, so cases with no left main are handled.
- **A2:** the support rule is withdrawn. Re-inference (P1′) stays unproven and is
  judged only against tile step 0.5.
- **A3:** the convention monitor now flags reads drawn *thin* (the decided
  convention is the original ImageCAS mask).
- **A4:** no trunk mode; a ramus-only disagreement never excludes a case.
- **A7:** the namer is cited at 88.2 % of 76 held-out cases fully right (swaps 7.9 %)
  under ramus → LCx.
- **A10 (from Crucible):** score by mean tF1 against each read; accept a model if it
  is non-inferior to inter-read tF1 within 0.02.
- **A11 (judge's synthesis, untested):** each read is a training sample; voxels
  where the reads name the vessel differently are `ignore`; extent differences are
  kept; decision-level disagreements go to a third reader.
- **A12:** one report on the first 50 double reads (refits every simulated-read result).
- **A13:** Atlas's Trillium run goes first and saves the val softmax and final
  checkpoint; Bridge's and Delta's questions can then run inference-only on it.
  Delta's decisions may use only the 80 non-sealed test cases.

## Human decisions

Recorded in [[Human decisions]] (2026-10-05) and binding on every plan:
the original ImageCAS mask (current Girder mask) is the lumen target, seed and
reference; territory side-branch rule, ramus → LCx; every case labelled twice;
no four-class starting labels; tF1 tolerance fixed at 1.5 mm; no relabelling
cost. Nothing is open.
