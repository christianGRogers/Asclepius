---
aliases: [Master plan]
tags: [plans, master]
status: living
round: 1
updated: 2026-10-04
---

# Master plan

**In force: [[Atlas v1]], as amended by the judge in [[Round 1]].** Won round 1
against [[Bridge v1]], [[Crucible v1]] and [[Delta v1]].

The plan text is the candidate file; the amendments below are binding and
override it where they conflict. Full reasoning, scorecards and what would
change the ruling: [[Round 1]].

## In one paragraph

One four-class nnU-Net v2 ResEnc model, trained directly at 0.5 mm isotropic
with a 256³ patch (a 128 mm patch holds the whole tree in ~98 % of cases), a
fixed CT window instead of nnU-Net's automatic one, mirroring off. Training
starts now on proxy labels — ImageCAS-X's per-branch names projected onto our
cases — and team labels replace the proxies case by case as they arrive.

## Binding amendments (Round 1)

- **A1 (from Delta):** every decision is made on macro **tree-F1 @ 1.5 mm**
  (centreline F1 crediting only centreline connected to the ostium), gated on
  false-positive components per case. Dice and clDice are reported, not decisive.
- **A2 (from Delta):** ≤ 3 mm gap bridging and label repair are a switchable
  post-processing step, judged on the validation fold by tree-F1.
- **A3 (from Crucible):** the lumen convention (Girder masks vs expert lumen) goes
  to humans; R1 waits at most a week, then trains on ImageCAS-X lumen or Atlas's
  proxy accordingly.
- **A4 (from Bridge and Crucible):** the rule-based branch namer checks every proxy
  label, team label and prediction; where it disagrees with the proxy, those voxels
  are `ignore`.
- **A5 (from Delta):** if the first 20 team labels are drawn thin, the
  native-spacing ablation becomes mandatory.
- **A6:** the R0 benchmark (VRAM, s/epoch, loader) runs before any other GPU job.
