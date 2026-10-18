---
aliases: [Roles and channels, Development process]
tags: [process, roles, slack]
status: draft
updated: 2026-10-18
---

# Roles and channels (draft)

Three agent roles do the work; the **project lead** (a person) decides. Every piece of
work is a GitHub issue, every change is a pull request, and Slack is where the work
is asked for, discussed and watched. Nothing here changes a human decision
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
- Runs the release train: merges `dev` → `main` when CI is green and the change is
  ready for annotators, and checks the release and the janus deploy afterwards.
- Posts a daily status (done / in progress / blocked / needs the lead) in `#standup`.
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

1. The lead asks in `#lead` (or anywhere; the PM picks it up).
2. The PM opens an issue with an owner role and acceptance criteria, and posts it in
   that role's channel.
3. The owner starts a **thread per issue** in its channel, and works it there: plan,
   progress, questions. The thread title is the issue number and title.
4. A role that needs another role opens or comments on an issue and links it in the
   other role's channel — never a side conversation that nobody else can find.
5. The PR (SWE) or vault note (researcher) closes the issue. The PM confirms the
   acceptance criteria, then reports it done in `#standup`.
6. Decisions needed on the way go to the lead in `#lead` as one question with options
   and a recommendation; the answer is recorded as a D-number.

GitHub is the system of record; Slack is the conversation. Anything worth keeping
from a Slack thread ends up in the issue, the PR or the vault.

## Slack channels

| Channel | Who posts | What goes there |
|---|---|---|
| `#lead` | Lead, PM | Requests, decision questions, approvals. Kept short. |
| `#standup` | PM | Daily status; weekly summary of what shipped. |
| `#decisions` | PM (after the lead decides) | One message per new D-number, linking [[Human decisions]]. Read-only for everyone else. |
| `#research` | Researcher, lead | One thread per experiment issue. Trillium commands for the lead to run. |
| `#eng` | SWE, lead | One thread per issue / PR. Design questions, review discussion. |
| `#releases` | GitHub app, PM | SegQueue releases, janus deploys, `main` merges. |
| `#ci` | GitHub app | CI failures and check results (noisy; muted by default). |
| `#annotators` (optional) | Lead, PM | What annotators need to know: new versions, workflow changes. |

Rules of thumb: one thread per issue; @-mention the role channel's agent only in its
own channel; no credentials, tokens or patient data in Slack, ever.

## Making it work in Slack (Claude in Slack, "Claude Tag")

What the platform supports today, from the Claude in Slack docs
(<https://claude.com/docs/claude-tag/overview.md>):

- **One Claude identity per workspace.** The three roles are not three bots: each role
  is a **channel** with its own custom instructions, repository grant and model. You
  watch and steer a role by reading and replying in its channel.
- **Each thread is one session** in a cloud sandbox. A reply continues it; a new task
  is a new thread. Anyone in the thread can steer it.
- **Agents do not talk to each other in Slack.** Claude ignores other bots' messages,
  so the hand-off between roles is GitHub: the PM's issue, the researcher's note, the
  SWE's PR. With the GitHub app posting to `#releases` and `#ci`, you see the whole
  flow in Slack anyway.
- **Repository access** is granted per channel; the session clones the repo when the
  message names it, and reads `CLAUDE.md` and `.claude/skills`. PRs are authored by the
  Claude GitHub App.

Setup (an Owner of the claude.ai org; needs a Team or Enterprise plan):

1. claude.ai → Admin settings → Claude Tag → *Start setup*. Enable *Routines* if asked.
2. Add the Claude app to the Slack workspace (<https://claude.com/claude-for-slack>).
3. In any channel: `/invite @Claude`, then a Slack admin sends `@Claude connect`; paste
   the pairing code into the setup page.
4. Connect GitHub and grant `christianGRogers/Asclepius` to `#research`, `#eng` and
   `#lead` (and `#standup` if the PM should read the repo there).
5. Give each channel an org-shared cloud environment (a personal one makes channel
   sessions fail) and set a spend limit.
6. Paste the channel instructions below into each channel's custom instructions.
7. Install the GitHub app for Slack and subscribe `#releases` and `#ci` to the repo.
8. Check: `@Claude what can you access from this channel?` in each channel.

### Channel instructions (paste into each channel)

**`#lead` and `#standup` — PM / engineering manager**

> You are the PM / engineering manager for the Asclepius repository
> (christianGRogers/Asclepius). Read `vault/Process/Roles and channels.md` first and
> follow it. Turn requests into GitHub issues with an owner role (`role:research` or
> `role:swe`), acceptance criteria and links; keep the plan and board current; bring
> decisions to the project lead as one question with options and a recommendation,
> and record a D-number in `vault/Plans/Human decisions.md` only after the lead
> answers. You do not write production code or run experiments. In `#standup`, post
> done / in progress / blocked / needs the lead.

**`#research` — Researcher**

> You are the researcher for the Asclepius repository. Read
> `vault/Process/Roles and channels.md` and `vault/Plans/Human decisions.md` first.
> Work one issue per thread on an `exp/<slug>` branch. Write every experiment up in
> `vault/Plans/Experiments/` and link it from the issue. Give Trillium work as commands
> for the project lead to run; never run jobs yourself. Anything that must ship goes to
> the SWE as an issue. Never post data, credentials or patient information.

**`#eng` — Software engineer**

> You are the software engineer for the Asclepius repository. Read
> `vault/Process/Roles and channels.md` and `CONTRIBUTING.md` first and follow them:
> `feat/` / `fix/` branches into `dev`, tests, the PR template, CI green before merge,
> `dev` → `main` only through a PR. Bump `__version__` only when annotators should get
> the change. Deploy to janus only with the *SegQueue14 on janus* workflow from `main`.
> Label and metric questions go to the researcher, scope and priority to the PM.

## Open questions for the lead

- Is the claude.ai org on a Team or Enterprise plan? Claude in Slack needs one.
- Who merges `dev` → `main`: the PM agent, or only the lead?
- Should the PM open GitHub issues on its own, or propose them in `#lead` first?
- Labels to create: `role:research`, `role:swe`, `needs-lead`, `blocked`.
