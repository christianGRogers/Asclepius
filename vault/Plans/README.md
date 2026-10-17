---
aliases: [Plan tournament, Plans]
tags: [plans, decision-record, tournament]
status: living
updated: 2026-10-04
---

# Plan tournament

The training plan is decided by competition rather than by one author. Several
**advocate** agents each own a candidate plan, run experiments on the real case
data, research prior and related methods, and argue for their plan. One **judge**
agent — who runs no experiments and does no research — reads the candidates and
the evidence and decides, from first principles and the evidence presented, which
plan is the **master plan**. Losing advocates either improve their plan or start
again from scratch. Rounds continue for as long as there is budget.

Nothing is discarded. Every version of every plan stays here.

## The goal (fixed, not up for debate)

Build a model that, given a CCTA volume of the heart, segments four classes plus
background: `left_main` (1), `left_anterior_descending` (2), `left_circumflex`
(3), `right_coronary_artery` (4) — the SegQueue protocol in
`src/segqueue/` and `GET /segqueue/project`.

- **Data:** 1000 CCTA cases on the Girder server (SegQueue collection, `cases`
  folder). Today each case has the CT and a **binary** whole-tree lumen mask
  (`coronary_arteries.nii.gz`). A labelling team is producing the four-class
  per-branch labels for **all 1000**; they arrive over time and are not
  available yet.
- **Compute:** SciNet Trillium, 1 × H100 80 GB per job, 24 h walltime, job-chain
  resume.
- **Label protocol:** lumen only; LM = ostium to the LAD/LCx bifurcation; LAD
  along the anterior interventricular groove; LCx along the left AV groove; RCA
  optional (may be small/absent in left-dominant systems); stop where the lumen
  is no longer confidently distinguishable.

## Layout

| Where | What | Who writes it |
|---|---|---|
| [[Master plan]] | The plan currently in force, and the round it won | Orchestrator, on the judge's ruling only |
| `Candidates/` | Every version of every candidate plan: `<Advocate> v<N>.md`. Never edited after the round it was submitted in; a revision is a new file | The owning advocate |
| `Judgements/` | One ruling per round: `Round <N>.md` | The judge |
| `Experiments/` | One note per experiment: question, method, result, what it implies. Code lives in the repo at `experiments/<advocate>/` | Any advocate |
| [[Plan ledger]] | One line per plan version: author, round, fate | Orchestrator |

## Rules of evidence

- An experiment note states what was run, on which cases, and the numbers. A
  claim with no experiment or citation behind it is an opinion and is judged as one.
- Citations are checked: a paper that cannot be found is worse than no citation.
- Experiments here run on CPU (no GPU in the tournament environment). Anything
  that needs an H100 is a *proposed* experiment, costed, not a result.
