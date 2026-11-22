---
tags: [plans, experiment, track-1F, round-2, janus-1F, D45, D47, partial-labels, gates, scorer]
author: Crucible
track: Janus 1-F
round: 2
status: done
updated: 2026-11-22
issue: christianGRogers/Asclepius#303
---

# Janus 1-F round 2: the B gates, the branch scorer and stage 2's Dice term, on the 620

For [[Candidates/Janus 1-F/Crucible v2|Crucible v2]], answering [[Janus 1-F Round 1]] §5, items 1, 2, 4, 6, 7 and 10.
CPU only. No GPU job, no model output, no CT.

## Data rules kept

- `fetch620.py` downloads ImageCAS-X's file lists (Zenodo 10.5281/zenodo.21887809, CC BY 4.0) first, builds D45's
  split from ids alone (`j1f_r1/split.py`), and then downloads **only the 620 training label files**. No label of the
  locked 100, the sealed 80 or the quality-0 20 is fetched, so none is opened. The split reproduces both pins
  (`train620 1350cb1f…1152`, `locked100 bbd9c687…5895`).
- Locked-100 numbers used: Delta's published class counts only (F-A7).
- `Descriptors.xlsx` is not opened: it lists every case, sealed ones included. Dominance is read from the 620's labels.
- No TotalSegmentator output, no pool read, nothing on Fir.

## Questions

1. How often do F-A6's B lines fail a model that is as good as a second ImageCAS-X reader, at the locked counts?
2. Does a single scorer module implement §5 item 2's definitions exactly (self-score 1, perturbations as predicted)?
3. Presence at 3 mm or 5 mm: what changes?
4. Stage 2: which Dice term lets an untraced class be learned, and how much background does each band release?
5. What does D35 in extended mode yield for the untraced classes?
6. What do Shi et al. report, exactly?
7. One census of record: trunk twigs and dominance.

## Setup

| Script | What it does |
|---|---|
| `fetch620.py` | Range-requests the file lists, then the 620 training labels only |
| `branch_score.py` | The frozen definitions: `to_1f` (Delta v1's map with `--left-pda name`, D47 Q1 (A); "Other" touching neither side → 255, F-A3), pieces, length, presence, detection, naming, branch tF1 (A1c, one root per piece), collapse by origin, hierarchical decoding |
| `census620.py` | Per case: the 1-F map and its collapse check against `territory.to_four`; pieces at 3 and 5 mm; self-score and three perturbations (first 20–60 cases with tF1); background bands at 8 and 15 mm (on a ~1 mm grid); trunk twigs |
| `dominance620.py` | Left/right posterior branches from the labels |
| `sim_gates.py` | Item 1's simulation |
| `dice_toy.py`, `dice_toy_rest.py` | Item 4's Dice-term toy, and the resume of its grid after the session stopped |
| `untraced_yield.py` | Item 6's yield grid |
| `summarise.py`, `report.py` | Tables |

@@RESULTS@@

## What it changes

In [[Candidates/Janus 1-F/Crucible v2|Crucible v2]]:
- F-A6's B1 recall line becomes per-class (human recall − 0.10) and B2's naming line 0.80 (§1.3 there);
- `branch_score.py` is the scorer of record, frozen by its sha256 (§2);
- stage 2 keeps leaf-Dice, per sample, with `batch_dice: false` pinned (§4.1);
- the band is territory-specific, provisional, and re-measured on the first extended reads (§4.2);
- §10's numbers are the census of record for the 620.
