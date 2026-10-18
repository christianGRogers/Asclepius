---
tags: [plans, experiment, audit, class-schema, d25, icx4, sealed-test]
author: Echo
updated: 2026-10-18
issue: christianGRogers/Asclepius#49
---

# Audit for the four-class schema (D25)

## Question

[[Human decisions]] D25 (2026-10-17) reverses D9: **four classes, LM, LAD, LCx, RCA**, with side
branches by territory (D1) and the ramus as LCx (D1b). This audit asks two things:

1. Does anything in the repository still assume 14 classes or the D9 restructure? For each place,
   is it **stale** (must change), **intentional** (the collapse table, the record of past decisions)
   or **live and needed**?
2. Does the 14 → 4 collapse that icx4 trains on match D25 exactly, including "Other" → the nearest
   LAD/LCx voxel?

## Setup

- `git grep` for `14-class`, `fourteen`, `icx14`, `D9`, `14 classes` and every copy of the ImageCAS-X →
  4 table (`ICX14_TO_4`, `ICX_TO_4`, `_ICX_TERRITORY`, `TERRITORY`, `to_four`, `icx_to_territory`),
  on `dev` at `743fe90`. Every hit outside Candidates/ and Judgements/ was read in context.
- `experiments/Echo/icx4_collapse_check.py` (CPU, no data). It compares the five copies of the table
  value by value against D25, checks each copy's handling of "Other", and compares the voxel-index and
  mm versions of "nearest LAD/LCx" on 200 synthetic trees at ImageCAS spacing (0.35, 0.35, 0.5 mm).
- The full test suite: `pytest` gave 834 passed, 74 skipped. `tests/test_icx4_territory.py`,
  `test_segqueue14_shared.py` and `test_reads.py` (120 tests) all pass. `ruff check .` is clean.
- `trillium/sealed_test.json` against `trillium/icx4/lib/prepare.py` and `score.py`.

## Result

### 1. The collapse matches D25 exactly on values 1–13

ImageCAS-X numbering is from its Suppl. Table 4, as transcribed in
[[Crucible - ImageCAS-X is real and its 800 cases are our cases c(id-1)]].

| Class | ImageCAS-X values | D25 wording |
|---|---|---|
| LM (1) | 1 LM | — |
| LAD (2) | 2 LAD, 4 D1, 5 D2 | diagonals → LAD |
| LCx (3) | 3 LCx, 6 OM1, 7 OM2, 8 IM, 12 L-PDA, 13 L-PLA | obtuse marginals, ramus (D1b), left PDA/PLA → LCx |
| RCA (4) | 9 RCA, 10 R-PDA, 11 R-PLA | right PDA/PLA → RCA |
| nearest LAD/LCx | 14 Other (D3/D4, OM3/OM4) | "Other" → the nearest LAD/LCx |

All five copies agree with this, value by value, with **0 mismatches**:
`src/segqueue14/labels.py` `ICX14_TO_4`, `src/segtrain/reads.py` `icx_to_territory`,
`src/segtrain/proxy.py` `ICX_TO_4`, `src/segtrain/namer.py` `icx_to_four` and
`trillium/icx4/lib/territory.py` `to_four`.

### 2. "Other" is handled three ways; only icx4's is exactly D25

| Implementation | Other (14) → | Verdict |
|---|---|---|
| `trillium/icx4/lib/territory.py` (icx4 training labels and score) | nearest LAD/LCx voxel, distance **in mm** | **D25.** |
| `segtrain.reads.icx_to_territory` (reads report's ImageCAS-X cross-check) | nearest LAD/LCx voxel, distance **in voxel indices** | Close, not exact. Fix in #56. |
| `segtrain.namer.icx_to_four`, `segtrain.proxy.ICX_TO_4` | 0, then named by the tree it hangs off (namer) or grown geodesically (proxy) | Intentional (D0-era projection onto the original mask). |
| `server/girder_segqueue14/scoring.py` `scoreAgainst` | **0 (dropped from the reference)**; 14-class reference detected by `max > 4` | Deviates from D25; dormant under D23. Fix in #57. |

Size of the voxel-vs-mm difference. In the synthetic worst case (an Other blob placed between an LAD
and an LCx), **9.0 % of Other voxels** (2230 / 24 697) took a different class, and **132 of 200**
cases differed. Real data will differ far less. Other is present in **76 of the 640** icx14 training
cases (`trillium-results/icx14/job2/results/label_census.json`) and is ~0.5 % of ImageCAS-X voxels
([[Crucible - Original binary masks disagree with ImageCAS-X]]). Most Other voxels touch their own
parent, where both measures agree. `tests/test_icx4_territory.py` pins the two implementations only
at isotropic 0.5 mm, so it cannot see the difference.

Edge case, the same in every copy: an Other voxel in a volume with no LAD/LCx becomes background. This
cannot happen on ImageCAS-X (Other is by definition a D or OM branch). No action.

### 3. Sealed test: icx4 as written would score the 80 sealed cases

`trillium/icx4/lib/score.py` scores every ImageCAS-X test case (160). That includes the 80 in
`sealed_icx_test`, which [[Sealed test]] says are "never used for a decision, a threshold or an
inspection" before a milestone. The seal is intact today: icx14 stopped before its scoring stage
(no test scores in `trillium-results/icx14/`), and icx4 has not run. The 20 sealed quality-0 cases
are among the 200 that ImageCAS-X does not cover, so icx4 never trains on them. **Fix before icx4's
first run: #55** (score open-36 and dev-44 only, reported apart), landing with #54 (decisive tF1).

### 4. Audit table

Verdicts: **stale** = must change; **intentional** = correct as is (collapse table, record of past
decisions); **live** = live and needed.

| Path | Finding | Verdict | Action |
|---|---|---|---|
| `vault/Plans/Master plan.md` (banner) | Says the plan is superseded by the 14-class restructure (D8–D10, `trillium/icx14`) | stale | **Left to the Round 9 judge** (#48 owns the Master plan). The judge should replace the banner with the 4-class Fir plan. |
| `vault/Plans/Plan ledger.md` | No 14-class text; it stops at Round 8 and records neither D9 nor D25 | live | None; the judge adds Round 9. |
| `vault/Plans/README.md` ("goal") | Four classes ✓, but RCA "optional" (D13: LM is the optional one), data = binary masks on 1000 cases, compute = Trillium, protocol = `src/segqueue/` | stale | **Fixed:** a binding "as of 2026-10-18" box (D25, D8/D12, D13, D22/D23/D26, protocol 15, compute per round) over the Round 1 brief, which is kept. |
| `vault/Plans/Human decisions.md` ("restructure of 2026-10-11" section) | Says the four-class grouping of D1/D1b is superseded | stale (as a live reading) | **Fixed:** a "partly reversed by D25" note. The D-table is untouched. |
| `vault/Proposed changes to the training plan.md` §2.1 | "Adopt the ImageCAS-X 14-class schema"; status "awaiting review" | stale | **Marked historical** (banner, `status: historical`). |
| `vault/Training method/Training plan.md` | Pre-tournament plan (2026-09-19); class schema "undecided"; status "living" | stale | **Marked historical**; `vault/README.md` entry says so. |
| `vault/Plans/Experiments/icx14 - *.md` (2 notes) | `status: in progress`; the second note recommends releasing jobs 3–4 | stale (status) | **Marked historical.** Its trunk Dice is not comparable to territory Dice; the resume fix is carried into icx4. |
| `vault/Plans/Candidates/*`, `Judgements/*` | 14-class mentions | intentional (record) | None. |
| `vault/Review/*`, `vault/Research/*`, `CCTA sourcing` | ImageCAS-X's 14-class schema as a fact about the dataset or literature | intentional | None. |
| `trillium/README.md` | Banner: "Current run: `icx14/`" | stale | **Fixed:** names `icx4/` (D25, Dataset 715) and points to Round 9. |
| `trillium/icx14/` | The cancelled 14-class run | intentional (record) | **Banner** "Historical. Do not run." Keep, not delete (see #51): icx4 reuses its venv and the resume note cites its `job_body.sh`. |
| `trillium/icx4/lib/territory.py` + `tests/test_icx4_territory.py` | Matches D25 exactly; test isotropic only | live | Anisotropic pin test in #56. |
| `trillium/icx4/lib/score.py` | Scores all 160 test cases, including 80 sealed | **stale vs A14** | **#55** (with #54). |
| `trillium/icx4/icx4` | Venv `$HOME/icx14-venv`, marker `.icx14_ok` | live (cosmetic) | None; renaming would rebuild a working venv. |
| `src/segtrain/reads.py` `icx_to_territory` | Voxel-index distance for Other | stale (inexact) | **#56.** |
| `src/segtrain/namer.py`, `src/segtrain/proxy.py` | Their own copies of the 1–13 table, Other → 0 by design | intentional | Optional dedup in #56. |
| `configs/labels/coronary_icx4.yaml` | The four classes, values 1–4; pinned to `labels.py` | live | None. |
| `configs/labels/coronary_icx14.yaml` | Comment says SegQueue14 submissions and prelabels carry these values and cites a test that does not exist | stale (comment) | **Fixed:** now "ImageCAS-X source values, not a training/annotation label set"; values unchanged. |
| `configs/tasks/` | Only 710/711 (lumen) and 712 (`coronary_branches`, D0 proxy on the original mask); nothing for `coronary_icx4` | live gap | For the **Round 9 judge**: if the winning plan trains on SegQueue14 reads through `segtrain convert` (which carries the A14 sealed-case refusals), it needs a task config. Not opened as an issue until the route is chosen. |
| `docs/TRAINING-R1.md` | 4-class, but on the D0 target (task 712, original mask) | stale (D8) | **Marked historical**, pointing to `trillium/icx4` and Round 9. |
| `docs/TRAINING-PHASE1.md` | Already marked superseded; its "4 classes to 14" line is an example | intentional | None. |
| `src/segqueue14/labels.py` | Four classes; `ICX14_TO_4` with Other → 0 and a pointer to segtrain | intentional / live | Comment "(D10, D12)" in #58. |
| `src/segqueue14/plan.py` | Comment cites the 14-class model and `trillium/icx14/lib/layout.py` | stale (comment) | #58. |
| `src/segqueue14/scoring.py`, `protocol.py` | "fourteen distance transforms"; prelabel "(D8, D10)" | stale (comment) | #58. |
| `server/girder_segqueue14/prelabels.py` | Examples `icx14-v1`; docstring "value above 14" (code checks > 4) | stale (comment) | #58. |
| `server/girder_segqueue14/export.py` | "a 4-class export fed to a 14-class task": a generic warning | intentional | None. |
| `server/girder_segqueue14/scoring.py` | Other dropped; `max > 4` detection | stale vs D25 (dormant) | **#57**, after #50. |
| `server/girder_segqueue14/models/case.py` | "14-class model's prediction (D10)" | stale (comment) | #58. |
| `server/girder_segqueue14/pyproject.toml` | Description "14-class prelabel correction" | stale (metadata) | #58. |
| `segqueue14` / `SegQueue14` names throughout | Historical name; protocol 15 serves four classes | intentional | None (explained in `src/segqueue14/__init__.py`, `slicer/SegQueue14/README.md`). |
| Dataset id 714 | Used by both atlas2 (`AtlasProxyDefaultWindow`) and icx14 | intentional (record) | None; icx4 uses 715, unique. |

## What it changes

- **For Round 9 advocates (#48):** the collapse in `trillium/icx4/lib/territory.py` is D25, and they
  can cite it as is. Any plan that runs icx4 must not score the sealed 80 (#55). Plans should report
  open-36 and dev-44 apart. icx14's trunk Dice (LM 0.90, LAD 0.90, LCx 0.86, RCA 0.93 at epoch 455) is
  not a 4-class territory result. A plan that trains on team reads through segtrain needs a
  `coronary_icx4` task config.
- **For the Round 9 judge:** replace the Master plan's 14-class banner. Decide the segtrain task
  config with the winning route.
- **Code (`role:swe`):** #55 (sealed 80 in icx4 score), #56 (segtrain mm "Other" + anisotropic pin),
  #57 (SegQueue14 reference collapse; after #50), #58 (SegQueue14 wording; #50 may absorb).
- **What would change this audit:** a decision that the restructure retired A14's sealed test (none
  is recorded; #48 says the sealed test stays sealed). Or an ImageCAS-X release whose label numbering
  differs from Suppl. Table 4 (the icx4 `prepare.py` range check 0–14 would not catch a renumbering).
