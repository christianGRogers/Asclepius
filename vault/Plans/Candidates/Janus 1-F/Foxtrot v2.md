---
tags: [plans, candidate, track-1-F, round2, janus1-f, D44, D45, D47, fir, locked100, partial-labels]
author: Foxtrot
track: 1-F
round: 2
version: 2
updated: 2026-11-22
issue: christianGRogers/Asclepius#303
---

# Foxtrot v2 (Janus 1-F): freeze the scorer and the gates on a human-level simulation, keep F-A11's read rule, take leaf-Dice and a measured band, and carry track 1-L's round-2 mechanics into the launcher

**What this is.** Round 2's answers to [[Janus 1-F Round 1]] §5, items 1–11, on top of the plan in force (Delta v1 as
amended by F-A1 to F-A13) and the lead's answers in **D47**. It does not re-argue §0 of the ruling.

**Evidence.** CPU only, on D45's 620 training labels and nothing else:
[[Foxtrot - On the 620, human-level branches false-fail OM2's round-1 gate up to 44 percent of the time, leaf-Dice is the only Dice term that both learns a drawn septal and stops an intruder, and the stall check needs PDA and PLB grouped]].
Code: `experiments/Foxtrot/j1f_r2/`.

**Data rules kept.** Only the 620 training labels were fetched (`../j1f/fetch_620.py`, which refuses anything else) and
every script asserts the 620's L-A1 pin. No locked-100, sealed, quality-0 or TotalSegmentator-twin label was opened.
The locked-100 counts used below are the ones the round-1 ruling already states (F-A7). Nothing ran on Fir, SciNet or
Trillium. **Step T and F0 have not run**; §13 says what each would change.

{{BODY}}
