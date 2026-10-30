---
tags: [janus-m, plans, candidate, scar, lie, path-b, registration, power]
author: Juliet
round: 4
version: 4
path: jm/paired-scar
updated: 2026-10-31
issue: christianGRogers/Asclepius#251
---

# Juliet v4: the shipped chain on the shared benchmark, one affine rule, a stable seal size, and where phase-suspect patients go

**Path `jm/paired-scar`.** The plan in force is [[Kilo v2]] with JA25–JA36 and JA50–JA59. Juliet v4 is that plan, plus
the five settlements #251 asks for. Every JA binds. No D-number is recorded here.

## 0. What this candidate settles

| #251 item | Where | In one line |
|---|---|---|
| 1. Shipped chain through the benchmark | §1, E12 | @@ITEM1@@ |
| 2. JA51 4(b) | §2, E12 | @@ITEM2@@ |
| 3. Power re-run | §3, E11 | At 2 000 studies per point: seal **140 (70 %) / 200 (50 %)** with Golf's infarct size, **160 / 220** with Kilo's, at 2 % failure and weak clustering. Strong clustering at 2 % failure, and any 5 % failure, never reaches 0.80 by 240 (power at the cap 0.49–0.67 and 0.17–0.60). Juliet E9 (60 cells, max \|z\| 2.4) and Golf E10 reproduce |
| 4. Phase-unmatched scoring | §4 | @@ITEM4@@ |
| 5. Path summary | §5 | Round 3 §8 updated |

**How the shared run was coordinated (#251).** Golf, Kilo and I each claimed the run, and all three of us launched
within ten minutes (19:04, 19:12, 19:14 UTC). I proposed on #251 that **Golf's run is the canonical v3** in
`bench_lie/` (it launched first). Kilo's run and mine are replications on the same seeds. So my runner, scorer and
generator additions live in `experiments/JanusM/Juliet/r4/`, not `bench_lie/`, and my PR does not touch
`bench_lie/`. @@COORD@@

@@BODY@@
