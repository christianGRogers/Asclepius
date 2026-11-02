---
aliases: [Janus-M, Janus-M tournament]
tags: [janus-m, plans, decision-record, tournament, myocardium]
status: living
updated: 2026-10-30
---

# Janus-M: the myocardium model, planned by tournament

**Janus-M** is a second model line, separate from the coronary model (Janus, [[Master plan]] in `vault/Plans/`).
The lead's brief (2026-10-30, [[Human decisions]] D37): *a separate model that segments the layers of the
myocardium of the heart, in the context of stenosis diagnosis and scarring.*

Its plan is decided exactly as the coronary plan was (`vault/Plans/README.md`): several **advocates** each own
a candidate plan, research the published work, run CPU experiments, and argue for their plan; a **judge** who
runs no experiments reads the candidates and the evidence and rules which plan is the **Janus-M master plan**.
Rounds continue for as long as there is budget. Nothing is discarded.

## Kept separate

Everything for Janus-M lives here and under `experiments/JanusM/`. Nothing for Janus-M is written into
`vault/Plans/` or `experiments/<Advocate>/`, and nothing in the coronary plan changes because of Janus-M.

| Where | What | Who writes it |
|---|---|---|
| [[Janus-M master plan]] (`Master plan.md` here) | The Janus-M plan in force, and the round it won | Orchestrator, on the judge's ruling only |
| `Candidates/` | `<Advocate> v<N>.md`, never edited after its round | The owning advocate |
| `Judgements/` | `Round <N>.md` | The judge |
| `Experiments/` | One note per experiment | Any advocate |
| [[Janus-M plan ledger]] (`Plan ledger.md` here) | One line per plan version | Orchestrator |
| [[Janus-M decisions]] (`Human decisions.md` here) | The lead's Janus-M decisions, numbered M1, M2, … | Orchestrator, after the lead answers |
| `experiments/JanusM/<Advocate>/` | Experiment code | The owning advocate |

The Janus-M advocates are **Golf, Hotel, India, Juliet and Kilo**, so no name is shared with the coronary
tournament.

## The goal (the lead's words are fixed; the details are for the rounds)

Segment the **layers of the myocardium** on cardiac CT, **for stenosis diagnosis and scarring**. What follows is
open and is exactly what Round 1 must settle with evidence, then bring to the lead as questions:

- **The class schema.** Which structure (left-ventricular myocardium only, or both ventricles), and what
  "layers" means: for example the endocardial and epicardial borders, transmural thirds (subendocardial,
  mid-wall, subepicardial), the AHA 17-segment model, coronary-territory assignment, or a combination.
- **The clinical outputs** that make it useful for stenosis and scar: for example perfusion defects on
  CT perfusion, late iodine enhancement scar and its transmurality, wall thinning, fat, and how each maps
  to the coronary tree that Janus segments.
- **The data**: which CT phases and protocols (coronary CTA, CT perfusion, late-enhancement CT), which
  public datasets with myocardium labels exist and under what licence, what the project already holds on
  Girder (the pool in `SegQueue/cases` and the `CCTA-Pool` archive), and what reference standard a layer
  or scar label can have.
- **The model, the metric and the compute** (Fir, as for Janus; account `def-aso22`).

## Decision points: paths, not pauses (the lead, 2026-10-30, M2)

The tournament **never pauses for the lead**. When a ruling reaches a question only the lead can answer and the
options lead to materially different plans, the line **splits into paths**, one per option, and each is built out
in parallel. The lead later picks one path; the others are deleted.

- **The judge decides where to split.** Each ruling marks at most **one forking question** (the one whose options
  change the plan's structure most) and names its options, 2 or 3. Every other open question is carried as an
  assumption, using the judge's recommendation, and stays a question for the lead.
- **A path is a branch.** Path `<p>` lives on the long-lived branch `jm/<p>` (e.g. `jm/lv-thirds`), created from
  the ruling that forked it. Its candidates, rulings, experiment notes and code go there, under the same
  `vault/JanusM/` and `experiments/JanusM/` paths, and its round PRs merge into `jm/<p>`, never into `dev`.
  `dev` holds only the shared trunk (rounds before the first split). Deleting a path is deleting its branch,
  which only the lead does.
- **Each path has its own tournament.** Three advocates and a judge per path per round, drawn from Golf, Hotel,
  India, Juliet, Kilo (and Lima, Mike, November, Oscar, Papa if more are needed); each path's file
  `vault/JanusM/PATH.md` on its branch states the option it assumes and the fork it came from.
- **A path may build.** Besides plans, a path may write the code its plan needs (data tooling, training configs,
  Fir launchers) on its own branch, through `role:swe` issues labelled with the path. Nothing runs on Fir: jobs
  stay exact commands for the lead.
- **The cap.** At most **four paths are active** at once. A path's judge may split it again only while the cap
  allows; otherwise it carries the question as an assumption. A path the lead has not chosen keeps iterating.
- **Every path's summary** goes to the lead on the round issue: what the path assumes, what it has built, and how
  it compares with its siblings.

## Binding from the project

Every project-wide rule binds Janus-M: no credentials, tokens or patient data anywhere; never run SciNet or
Alliance jobs (Fir commands go to the lead as exact commands); D19 (the lead handles access requests) and
**D31** (never draft or store any email, letter or request to anyone outside the project). The coronary
seal (D27, D32, D33) and the sealed ImageCAS-X 80 (A14) stay sealed: Janus-M never reads, scores or trains on
a sealed case or a coronary D35 decision-set patient. A Janus-M decision that would touch a coronary
decision goes to the lead as a question.

## Rules of evidence

As in `vault/Plans/README.md`: an experiment note states what was run, on which cases, and the numbers; a
claim with no experiment or citation behind it is an opinion; citations are checked, and a paper that cannot
be found counts against its advocate. Experiments here run on CPU; GPU work is proposed and costed for Fir.
