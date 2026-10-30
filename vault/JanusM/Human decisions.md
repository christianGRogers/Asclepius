---
aliases: [Janus-M decisions]
tags: [janus-m, decision-record]
status: living
updated: 2026-10-30
---

# Janus-M decisions

The lead's decisions for the Janus-M line, numbered M1, M2, …, recorded only after the lead answers.
They are binding for Janus-M. The project-wide decisions in `vault/Plans/Human decisions.md` that are not
specific to the coronary model also bind (D19, D31; the coronary seals stay sealed).

| # | Question | Decision | Status |
|---|---|---|---|
| M1 | Does the myocardium model exist, and how is it kept? (D37) | **Yes.** A separate model line, **Janus-M**, for segmenting the layers of the myocardium in the context of stenosis diagnosis and scarring. Its plan is decided by its own tournament, kept in `vault/JanusM/` and `experiments/JanusM/`, apart from the coronary plan. Models in the line are numbered in reading order: the first read is Janus-M 0. | Decided 2026-10-30 |
| M2 | What happens at a decision point? | **Never pause.** At a question only the lead can answer whose options change the plan, the judge forks the line into paths, one per option, each built out in parallel on its own branch `jm/<path>` by its own advocates and judge; the lead later chooses one path and the others are deleted. At most one fork per ruling and four active paths (README, "Decision points"). | Decided 2026-10-30 |
