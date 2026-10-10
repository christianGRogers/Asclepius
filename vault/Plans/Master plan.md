---
aliases: [Master plan]
tags: [plans, master]
status: living
round: 7
updated: 2026-10-10
---

# Master plan

**In force: [[Atlas v8]], as amended by the judge in [[Round 7]].** Won round 1
(as [[Atlas v1]]) and held the title in rounds 2–7. All three challengers now keep the master's
model, data, schedule and deciding metric, and compete on additions to it.

The plan text is the candidate file; the amendments below are binding and
override it where they conflict. Full reasoning, scorecards and what would
change the ruling: [[Round 7]] (earlier: [[Round 6]] … [[Round 1]]).

## In one paragraph

One four-class nnU-Net v2 ResEnc model, trained directly at 0.5 mm isotropic
with a 256³ patch (a 128 mm patch holds the whole tree in ~98 % of cases), a
fixed CT window instead of nnU-Net's automatic one, mirroring off. Training
starts now on proxy labels — ImageCAS-X's per-branch names projected onto our
cases — and team labels replace the proxies case by case as they arrive.

## Binding amendments (as of Round 2)

Round 1's A1–A6 as revised in Round 2, plus A7–A9. The full wording is in
[[Round 2]] §1; this is the summary.

- **A1 — ostium:** tree-F1 (tF1 @ 1.5 mm) decides everything. The ostium is
  aorta contact (TotalSegmentator, ≤ 5 mm), cross-checked by Delta's two cheap
  rules; disagreement > 5 mm is flagged for a human.
- **A2 — false positives and bridging:** the FP-component gate is computed on the
  **raw** prediction, before any repair. Delta's bridge audit is binding. 3 mm
  bridging alone stays switchable but is weak (+0.01 tF1; 5 of 12 joins were FP).
  Gap-centred re-inference + support-gated bridging (P1′) is a candidate, unproven.
- **A3 — one convention:** a per-case convention monitor on every labelling wave
  (halt the wave if > 10 % is in the wrong convention), seed tagging, and a
  single-convention sealed test. The lumen convention itself is a human decision.
- **A4 — QA namer:** voxel `ignore` only near the carina where proxy and rule
  namer disagree; cases with wholesale disagreement are excluded until reviewed.
- **A5 — calibre trigger** and **A6 — R0 benchmark first:** unchanged.
- **A7 — rule renaming competes with the model's own names** (ship only if the
  paired tF1 CI excludes 0 and swaps do not rise); save softmax at val/test so
  Bridge's hybrid decoding can be scored later.
- **A8 — the ramus rule is a switch** set from the humans' written rule.
- **A9 — one implementation:** only the ported `src/segtrain` tF1 may decide.

## Round 3 changes (summary; full wording in [[Round 3]] §1)

- **A1:** ostia found per tree component, so cases with no left main are handled.
- **A2:** the support rule is withdrawn. Re-inference (P1′) stays unproven and is
  judged only against tile step 0.5.
- **A3:** the convention monitor now flags reads drawn *thin* (the decided
  convention is the original ImageCAS mask).
- **A4:** no trunk mode; a ramus-only disagreement never excludes a case.
- **A7:** the namer is cited at 88.2 % of 76 held-out cases fully right (swaps 7.9 %)
  under ramus → LCx.
- **A10 (from Crucible):** score by mean tF1 against each read; accept a model if it
  is non-inferior to inter-read tF1 within 0.02.
- **A11 (judge's synthesis, untested):** each read is a training sample; voxels
  where the reads name the vessel differently are `ignore`; extent differences are
  kept; decision-level disagreements go to a third reader.
- **A12:** one report on the first 50 double reads (refits every simulated-read result).
- **A13:** Atlas's Trillium run goes first and saves the val softmax and final
  checkpoint; Bridge's and Delta's questions can then run inference-only on it.
  Delta's decisions may use only the 80 non-sealed test cases.

## Round 4 changes (summary; full wording in [[Round 4]] §1)

- **A14 — the official sealed test:** 80 ImageCAS-X test cases + 20 quality-0
  cases, ranked by `sha256('asclepius-sealed-round4:' + case_id)` after excluding
  every advocate's development cases. Published in [[Sealed test]] before any
  Trillium job runs; supersedes Delta's `icx_test_split.json`.
- **A11's test** runs only if wave 1 shows annotator habits or team bias, judged on
  a carina anchor against ImageCAS-X rather than against the reads.
- **A12** adds Crucible's habit test and carina anchor as diagnostics only, after
  the anchor's noise floor is measured.
- **A1/A2 confirmed** on new evidence (0 silent ostium errors in 130; bridging still
  6/13 false-positive joins on the thick reference).
- Atlas's decision-table row for the short R1 is now numeric (≤ 0.03 / > 0.10).

## Round 5 changes (first GPU results; full wording in [[Round 5]] §1)

Measured on Trillium: R0 passes (175 s/epoch, 55.6 GiB; 1000 epochs ≈ 48.6 h). A
412-epoch R1 on the proxy scores macro tF1 0.846 under the provisional ostium; the
judge accepts only the bounds 0.846–0.895 until the A1 re-score. The FP gate fails
(1.49/case).

- **A1 — ostium of record:** the reference centreline voxel nearest the
  TotalSegmentator aorta, per tree component and side (`segtrain.tf1`). A tF1 without
  an aorta mask decides nothing (A1a); flagged trees are reported separately (A1b).
  **Metric frozen (A1c):** `src/segtrain/tf1.py` sha256 `3c737cbcc0ba24d38f923a52a28d479b34b579d6943f4c55a8cae48f66ad9253`, last changed in commit `e2d9677`.
- **A2:** bridging (P1) removed; P1′ survives only if Delta's stricter pre-registered
  table passes (≤ ~0.004 to gain).
- **A4:** absent-LM cases are never auto-excluded.
- **A7:** rule renaming (R) and grammar decoding (H) retired; the namer stays QA only.
- **A11′:** each read is a separate training sample with no name-conflict `ignore`;
  the third-read trigger stays.
- **A15:** the FP gate (≤ 1/case, raw) stays as an acceptance criterion for the final
  model; no model has met it. The FP census chooses the lever.
- **A16:** Atlas run 2 — Phase A (FP census + re-score with the A1 rule, no training)
  and Phase B (window ablation, 412 epochs, paired against run 1). Full-length R1 waits
  for run 2's winning window.

## Round 6 changes (CPU round while Atlas run 2 is on Trillium; full wording in [[Round 6]] §1)

- **Closed:** P1′, P1 and P2 failed their own pre-registered tests and leave the recipe.
- **A17 — fine-tuning as team reads arrive:** a dedicated fine-tune trainer comes first
  (stock nnU-Net re-initialises the output heads and has no warm-up); LR 1e-2 with a
  1e-3 fallback arm, and Atlas's citation corrected (the source prefers 1e-3); if the
  proxy fails the wave-1 admission test, the proxy-drop test moves to wave 3. The final
  model never trains on proxies.
- **A18 — A10 suspended** until the clinical lead sets the acceptance margin (see below).
- **A19 — evaluation discipline:** one decisive look at the sealed test; every decision
  table states its minimum detectable effect; a stacked-recipe control replaces E6.
- **A20 — heart+aorta ROI filter (Foxtrot F3):** allowed only after a check on all 1000
  masks and an atlas2 census showing ≥ 25 % of FP components lie beyond 25 mm.
- **A21 — implementation (from Echo's audit):** 13 defects found, all fixed with tests
  (one critical: a sealed-case leak via SegQueue case names). Binding: a dry run of one
  real approved SegQueue export through index → convert → reads-report passes before
  wave 1; a batch aorta producer (TotalSegmentator) lives in `src/segtrain` before any
  decisive tF1 is computed outside a Trillium job (A1a); Echo's remaining suspicions go to
  their owners.

## Round 7 changes (full wording in [[Round 7]])

- **A1c change approved — report-only:** `segtrain.tf1` reports any reference class with
  no centreline voxels (7 of 143 references: short wide LM ×6, LCx ×1) instead of skipping
  it silently. No score changes, so atlas2's results under the old hash stay
  decision-grade. **New frozen hash (A1c):** `src/segtrain/tf1.py` sha256 `9bb77e24c5b8959d37752e260c78e4e589101687a7fe45f130b188670af90608`; field `TreeF1.classes_without_centreline`. atlas2 keeps the previous pin (`3c737cbc…`, copy at `experiments/Delta/tf1_3c737cbc.py`); scores are identical between the two. Scoring such
  a class as missed is **rejected** (a perfect prediction has no centreline there
  either). A minimum-centreline fallback is approved in principle, to be validated before
  wave 1 and before any A10 or sealed scoring.
- A17a fine-tune trainer and A17b citation done; A20(i) ROI check passes on 92 cases, the
  remaining 908 to run with the aorta producer after atlas2; A21 aorta producer built and
  the SegQueue export dry run passed on test submissions — it must be repeated on the
  first real four-class double-read export before wave 1.

## Open human decisions (Round 6)

- **Acceptance margin (A18).** At n = 100, A10 as written ("within 0.02 of inter-read
  tF1") rejects a model exactly as good as a second reader. The clinical lead chooses the
  margin, per-class or macro, and the accepted power: e.g. 0.05 per class; 0.02 on macro
  with a per-class floor; keep 0.02 (in effect a superiority test); or a larger sealed set.
- **Reference extent.** Delta proposes a written rule for how much vessel a read should
  contain. Under D0/D4 annotators do not redraw the mask, so any such rule redefines the
  reference and is the project lead's decision.

## Human decisions

Recorded in [[Human decisions]] (2026-10-05) and binding on every plan:
the original ImageCAS mask (current Girder mask) is the lumen target, seed and
reference; territory side-branch rule, ramus → LCx; every case labelled twice;
no four-class starting labels; tF1 tolerance fixed at 1.5 mm; no relabelling
cost. Nothing is open.
