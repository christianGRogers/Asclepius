---
aliases: [Janus-M path paired-scar]
tags: [janus-m, path]
status: active
updated: 2026-10-30
---

# Janus-M path: `jm/paired-scar`

**Forked from:** the Janus-M Round 1 ruling (`vault/JanusM/Judgements/Round 1.md`, PR #137, commit `56e2e09`),
on its forking question **LQ1**: *does the project pursue paired CT + reference data for scar and ischaemia?*

**This path assumes:** **B. Paired scar data.** The project pursues paired CT + reference data. Stage A as on the trunk, plus: the paired-cohort specification (CCTA + late-enhancement CT with CMR LGE within a fixed window; stress CTP with FFR where present), written as data requirements with **no request text** (D31); LIE registration to first-pass borders; Kim-bin grading with scar presence first; a scar head inside class 1 scored against LGE; and the validation plan for the Stage A signs against LGE.

**Sibling path:** `jm/rest-ccta`. **Rules:** `vault/JanusM/README.md`, "Decision points" (M2). Everything on this path stays on
this branch: round PRs merge into `jm/paired-scar`, never into `dev`. The lead keeps one path; the other is deleted.

**Round 2 advocates on this path:** Golf, Juliet, Kilo.

**Shared trunk work** (JA13 role:swe issues: geometry module, JA12 guard, JA6 freeze, read protocol and queue) is built on
`dev`; merge `dev` into this branch to pick it up.
