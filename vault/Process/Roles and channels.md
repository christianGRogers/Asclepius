---
aliases: [Roles and channels, Development process]
tags: [process, roles, slack]
status: living
updated: 2026-10-18
---

# Roles and channels

Three agent roles do the work; the **project lead** (a person) decides. Every piece of
work is a GitHub issue, every change is a pull request, and each role runs as its own
Claude Code cloud session, started and supervised by the PM. Instructions per role:
`.claude/roles/`. Nothing here changes a human decision
([[Human decisions]]): only the project lead adds or reverses a D-number.

## The roles

### PM / engineering manager

Owns *what happens next and whether it is done*.

- Turns the project lead's requests into GitHub issues: one outcome each, with an
  owner role (`role:research` or `role:swe`), acceptance criteria and links.
- Keeps the plan current ([[Master plan]], [[Plan ledger]]) and the board in order:
  what is in progress, blocked, waiting on the lead.
- Brings decisions to the lead as a short question with a recommendation, and records
  the answer as a D-number in [[Human decisions]] once the lead has given it.
- Starts and supervises a Claude Code session per role issue, merges green role PRs into
  `dev`, and opens the `dev` → `main` PR for the lead to merge.
- Reports status (done / in progress / blocked / needs the lead) when asked.
- Does not write production code or run experiments.

### Researcher

Owns *what the model and the data should be, with evidence*.

- Designs and runs experiments: data sourcing and QC (CCTA-Pool, ImageCAS-X), label
  conventions, training recipes (`trillium/`), evaluation and the sealed test.
- Writes each experiment up in `vault/Plans/Experiments/` (question, setup, result,
  what it changes) and links it from the issue.
- Prepares Trillium jobs as commands for the lead to run; never runs on SciNet itself.
- Works on `exp/<slug>` branches; hands anything that must ship (a tool, a pipeline
  change, a label-set change) to the SWE as an issue rather than merging it.
- Flags data-licence and PHI questions to the PM for the lead; never publishes data.

### Software engineer

Owns *the code that annotators and the server run*.

- SegQueue / SegQueue14 (Girder plugin, Slicer module, shared protocol), `src/segtrain`,
  `tools/`, CI and the janus deploy workflow.
- Works on `feat/` / `fix/` / `ci/` / `chore/` branches into `dev` (CONTRIBUTING §4),
  with tests, and a PR that follows the template; drives its own PRs to green.
- Bumps `__version__` only when a change should reach annotators, and says so in the PR.
- Deploys to janus only through *Actions → SegQueue14 on janus*, after the PR is on `main`.
- Hands questions about labels, metrics or data back to the researcher, and scope or
  priority questions to the PM.

### Project lead (a person)

Asks for work, answers decision questions, approves anything irreversible or
annotator-facing (releases that change the workflow, data deletion, accounts,
spending), and runs the Trillium commands.

## How work moves

1. The lead asks the PM (its Claude Code session, or an issue labelled `needs-lead`).
2. The PM opens an issue per outcome with an owner label and acceptance criteria.
3. The PM starts a **Claude Code cloud session for that role** on the repo at `dev`, tagged
   `role:<role>` and `issue:<n>`, told to read `.claude/roles/<role>.md` and work the issue.
4. The role session works on its own branch, comments progress on the issue, and opens a
   PR into `dev` (SWE) or a vault note PR (researcher). It never merges.
5. The PM checks on each role session and its PR, steers it if stuck, merges green PRs into
   `dev`, and archives the session when the issue closes.
6. When `dev` is ready, the PM opens the `dev` -> `main` PR; **the lead merges it**.
7. Decisions go to the lead as one question with options and a recommendation; the answer
   becomes a D-number.

GitHub is the system of record. To watch the agents: the session list at claude.ai/code
(filter by tag `role:swe`, `role:research`, `role:pm`; open any session to read or steer
it), and the issues and PRs. Role instructions live in `.claude/roles/`.

Labels: `role:swe`, `role:research`, `needs-lead`, `blocked`.

## Slack (optional)

Slack is a notification feed, not where work is delegated: Claude in Slack has one
identity per workspace and ignores other bots, so one channel's agent cannot hand work to
another. Useful channels: `#lead` (requests and decisions), `#releases` and `#ci` (the
GitHub app: `/github subscribe christianGRogers/Asclepius`), and role channels if the lead
wants to start a role thread by hand (`@Claude in #eng: take #57`).

## Open questions for the lead

- Decided 2026-10-18: the lead merges `dev` → `main`; the PM merges green role PRs into
  `dev` and may open issues and start role sessions for work the lead asked for.
