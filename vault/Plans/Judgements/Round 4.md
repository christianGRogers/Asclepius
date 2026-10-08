---
tags: [plans, judgement]
round: 4
updated: 2026-10-08
---

# Round 4 ruling

## 1. Master plan: **Atlas v4**, adopted with these binding changes

Atlas v4 keeps the title. It implements A10 and A11 in code (`fuse_reads.py`), and the self-test confirms the logic:

- a carina shift becomes `ignore` (0.05–1.2 %);
- a truncation keeps its extent (0 % `ignore`, against 5–7 % under agree-or-ignore);
- a wholesale swap goes to a third read;
- the non-inferiority check passes a model at +0.01 and fails one at −0.05.

It also re-ran A4 under D1b: 0.29 % of voxels `ignore`, 20/172 cases excluded, 7 exempted as ramus-only. And it made its Trillium run serve the other two (A13).

No challenger offers a rival recipe. Each says so explicitly. This round's work is procedural, and three procedural defects need binding fixes.

### Revised amendments

**A1: confirmed with data.** The per-component ostium procedure, re-run on 62 cases with 130 true ostia (including all 3 absent-LM cases): 127 agreed and right, 3 flagged with one rule right, **0 silent errors** (Delta v4 §3). Bridge's measured negative is accepted: an aorta-*preferred* re-rank changed 0 of 39 choices. The namer may add the A1 aorta-contact point as an extra ostium **candidate**. That is untested and is a candidate change only, judged by A7 on R1 val.

**A2: confirmed on the decided reference.** Bridging alone still attaches a piece touching no reference vessel in 6 of 13 joins against the thick mask (46 %; it was 5/13 against the thin reference). P1 stays in, as expected to fail. The raw FP gate and the audit stand. P1′ is decided only by Delta's Trillium C2 comparison on the open 80 (see A14).

**A4: Atlas v4's change accepted.** In a ramus-only-exempt proxy case, the disagreeing voxels keep the proxy's expert name rather than becoming `ignore`. This is sound: ImageCAS-X traced the ramus, D1b maps it, and the namer is the side known to fail there.

**A11: kept, with its test made conditional.** Crucible shows (§3 C2) that a test judged against the reads cannot choose between fusion rules. The pre-registered A11 test on real reads therefore:
- **runs only if A12 detects annotator habits or a team-wide bias** (§2.1 below);
- is otherwise skipped, and A11 stays. This saves 22–33 H100-h.

If it runs, an alternative replaces A11 only if it beats A11 on the **carina-anchor** criterion (A12b) with a CI excluding 0, *and* is no worse in tF1 against the reads. Crucible's Trillium arm `a11` vs `both` against the truth, under opposite habits, is the prior that decides whether this matters at all:
- if `a11 ≥ both`, A11 stands even under habits;
- if `a11 < both` with the CI excluding 0, A11's name-conflict `ignore` is narrowed to cases where the annotators share no detected habit.

**A12: extended (from Crucible v5).** The wave-1 report adds:
- **A12a, annotator habits.** Per-annotator mean carina (LM-end) position and truncation radius. Two annotators whose offsets differ by > 1 mm (permutation test) count as having habits.
- **A12b, carina anchor.** Per case, the geodesic offset of each read's LM end from the ImageCAS-X LM end projected onto the same centreline. A mean offset with a CI excluding ±1 mm, after subtracting the convention floor below, flags a **team-wide bias**, and that triggers re-instruction before further labelling.
- **Prerequisite (binding, CPU, before wave 1).** Measure the **convention noise floor** of the anchor: the offset distribution between the projected proxy's LM end (ImageCAS-X names on the thick mask) and ImageCAS-X's own LM end, on ≥ 100 cases. Crucible asserts that LM-end position is "largely convention-independent", but no note measures it. If the floor's spread exceeds ~1 mm, A12b cannot detect a 1 mm bias, and its threshold must be restated from the floor.
- The anchor is **diagnostic only**. Under D0 the team's reads are the reference. ImageCAS-X can trigger re-instruction; it never scores a model.

**A13: confirmed.** Bridge and Delta now run inference-only on Atlas's checkpoint and softmax (≤ 4 h and ≤ 10 h). Atlas's manifest records `sealed_cases_touched: false`.

**Atlas's pending decision table.** The row "val tF1 within a few points of per-class clDice" is still not a number, although Round 3 asked for one. It is now fixed as: per-class clDice − tF1 ≤ 0.03 → few cuts; > 0.10 → many cuts; anything between → P1′ is judged on its merits.

### New amendments

**A14: the official sealed list** (ruling on question 1; reasoning in §3 C1).
1. **Sealed test = 80 ImageCAS-X test cases + 20 quality-0 cases**, chosen by a hash rule whose salt is fixed by this ruling, not by an advocate: rank by `sha256('asclepius-sealed-round4:' + case_id)`.
2. **Excluded before ranking:** every case that is in any advocate's *development* set, meaning a case whose per-case output was inspected while choosing the rules, thresholds or weights of a component that may ship. The excluded cases are:
   - Bridge's `devset3` and the cases used to fit the ostium weights (`ostium_w_dev2.json`);
   - Delta's P1′ development cases (c0407, c0113, c0675, c0526) and its label-repair design cases (c0039, c0099, c0162, c0224, c0291);
   - Atlas's A4 threshold cases are not excluded, because the thresholds were fixed before looking (stated in the note);
   - any further case an advocate declares.
3. **Selection.** The first 80 remaining ImageCAS-X test cases are sealed and the rest are open. The same procedure applies to the 200 quality-0 cases, sealing the first 20.
4. **Who publishes.** The orchestrator, or Atlas acting for it, computes and publishes `vault/Plans/Sealed test.md` (and `sealed_test.json` where `./delta` reads it) **before any Trillium job runs**. Every advocate must list its development cases there within the same step. Delta's `icx_test_split.json` is superseded and is used only if the published list is missing.
5. **Open 80.** These may be used for post-processing decisions (Delta's C2) and enter training once team-read. Sealed cases are scored only at milestones, against team reads.

## 2. Scorecards

Scores are out of 5.

### Atlas v4: winner (amended)

| | Score | Notes |
|---|---|---|
| (a) Reasoning | 4.5 | It integrates A1–A13 coherently. It fixed the v3 inconsistency (no fused reference). The ramus-only exemption, and keeping the expert's name there, are well argued. |
| (b) Evidence | 4 | The new notes match the plan: 0.29 %, 20/172, 7 exempt; the self-test table checks out. The self-test is a code test on 3 cases, which is what it claims to be. The ≈ 10 % adjudication estimate is still extrapolated from automatic namers; the A12 report will measure it. |
| (c) Fit | 4.5 | Complete. It never published a sealed list, a gap present since v1 and now fixed by A14. The decision-table row is still vague. |
| (d) Risk/cost | 4 | Unchanged. Making the A11 test conditional saves 22–33 h. |

**Verdict:** keeps the title.

### Crucible v5

| | Score | Notes |
|---|---|---|
| (a) Reasoning | 4.5 | The key insight is sound and important: **a score against the reads measures agreement with the team, so it cannot see a bias the readers share, and it cannot rank fusion rules that differ only against the truth.** It withdrew its v4 "+0.06" claim (0.000 under a shared ambiguity), which is honest. |
| (b) Evidence | 3 | The table matches the note. Under opposite habits with FILL, the ignore-fusions gain +0.018 to +0.026, CIs excluding 0; in the worst case they lose −0.075. Against the reads, all fusions sit within ±0.002. A11 is never worse than −0.001 elsewhere. All of it is a hand-built error model on 14 cases, K = 8, with the plurality idealisation; Crucible flagged the jitter row as a tie artefact. The anchor's convention-independence is **asserted, not measured** (hence the A12 prerequisite). Two inconsistencies in the pending GPU note: it says "five arms" in two places while describing six, and its row "score against the fused reference" contradicts A10. Both are cosmetic, and A10 governs. |
| (c) Fit | 4.5 | CPU-only additions. Pairing across habit groups is a scheduling request to the labelling lead (§5). |
| (d) Risk/cost | 4.5 | Minutes of CPU. |

**Verdict:** A12a/A12b and the conditional A11 test come from it.

### Delta v4

| | Score | Notes |
|---|---|---|
| (a) Reasoning | 4.5 | It saw that no sealed list existed, the most consequential hygiene gap in the tournament, and disclosed its own prior contact with cases its split seals. Its C4 answer partly refutes its own Round 3 hypothesis (6/13 joins still false). |
| (b) Evidence | 4 | C4: 13 bridges on 18 cases, a small sample from a thin-trained model, as noted. Ostium per component: 130 ostia, 0 silent errors, a strong result for a procedure. The P1′ uncut-case control at step 0.5 is not done (OOM). That is acceptable because the Trillium rule "no case worse by > 0.01" covers it. |
| (c) Fit | 4.5 | Inference-only on Atlas's checkpoint, on the open 80. |
| (d) Risk/cost | 4.5 | ≤ 10 H100-h. |

**Verdict:** A1 is confirmed and A14 originates here, with a judge-fixed salt and development-set exclusions.

### Bridge v4

| | Score | Notes |
|---|---|---|
| (a) Reasoning | 4 | It narrowed honestly ("no recipe that beats the master"). It withdrew the unmeasured branch/jitter lumen rule, and it diagnosed the remaining ostium failures as candidate-generation, not ranking, failures. |
| (b) Evidence | 3.5 | The aorta-preferred negative (0/39 changed) is clean, though only 4 of the 39 cases are held out. The H change (mean-softmax unary, 0.5-nat LM prior) was tuned on a fake test, not on val, which is correct practice. |
| (c) Fit | 4.5 | The inference-only A13 mode is verified on CPU, including a correct rejection of a 0-byte checkpoint. |
| (d) Risk/cost | 5 | ≤ 4 H100-h. |

**Verdict:** its case stands or falls on the D/R/H/O result.

## 3. Contested points

### C1. The sealed list (question 1)

**Is a hash split the right mechanism?** Yes. It is deterministic, reproducible and outcome-blind. One residual doubt is that the advocate who proposed it also chose the salt, and could in principle have tried several salts. There is no evidence of that, but a judge-fixed salt removes the doubt at no cost (A14).

**Does prior inspection contaminate a case?** That depends on *what* was done with it. A sealed test exists so that the final number is an unbiased estimate of performance against **team reads**, with no system choice made by looking at those cases. Three kinds of contact:

1. **Labels of the sealed reference.** These are team reads, and none exist. No contact is possible.
2. **Per-case design exposure:** a case's output was inspected while rules, thresholds or weights of a shippable component were being chosen. That is genuine, if small, contamination, because the shipped system has seen the case's image and geometry. It applies to:
   - Bridge's namer rules and ostium weights, whose dev set includes ImageCAS-X test cases (c0150, c0250, c0675, c0750, c0900, c0951 are disclosed);
   - Delta's P1′ (c0675, c0526 among the four development cases);
   - the label-repair absorption cap (c0039).

   R and P1′ are pre-registered competitors that may ship, so their development cases must not be sealed.
3. **Frozen-method evaluation or aggregate statistics:** a fixed method scored on a case (Bridge's 160-case ceiling, Bridge's E2E "never seen" cases, Crucible's convention test), or the case contributing to a cohort statistic (Atlas's patch extents, header stats). This does **not** contaminate, because no choice was conditioned on that case's result. This is the ordinary held-out evaluation logic the whole tournament relies on.

**Should the sealed set be drawn from cases nobody has examined?** That is not achievable. Bridge's frozen ceiling run scored all 160 ImageCAS-X test cases, and cohort-wide header and mask surveys touched nearly every case. It is also not necessary, by the distinction above. The correct rule is to exclude design-exposed cases and accept evaluation-exposed ones, which is A14. Delta's list seals c0526 and c0675, both design cases for P1′ and evaluated against thin labels, so it must not be adopted unchanged. Removing perhaps 20–30 test-list cases still leaves well over 80 to rank.

One process requirement follows: **the published list must exist before any Trillium job runs**, since Delta's run chooses its open 80 from it.

### C2. A10 cannot distinguish fusion rules (question 2)

**Accept Crucible's logic, with its scope.** Under D0 the reference *is* the team's reads. A10 is therefore the right acceptance metric: it measures what the project defined as correct. But it is the wrong instrument for choosing a **training** rule, for two reasons:
- each fusion's optimum is close to the readers' plurality, so all fusions score alike against the reads (±0.002);
- where fusions differ against the truth (opposite habits), the difference lies in carina *position*, which the reads themselves disagree about.

Hence the conditional A11 test, judged on an external anchor (A11, A12).

**On the proposed carina-position check: adopt it as a diagnostic, after one validation.** Two cautions:
1. ImageCAS-X's carina carries its own inter-observer error (LM Dice 91.9) and a lumen-convention offset. Only a **floor-corrected** mean and per-annotator *differences* are interpretable, hence the binding noise-floor prerequisite.
2. A team-wide bias, if found, is fixed by **re-instruction**, not by fusion. Crucible says the same, and the decision of what the carina convention *is* stays with humans (§5).

**A10's 0.02 margin.** Crucible now shows a converged model may only *tie* inter-read under a shared ambiguity. The margin is therefore not lenient, and could be strict. This remains a clinical-lead decision (Round 3 §6.1), now with that evidence attached.

### C3. Does bridging attach false positives because of the convention?

Only partly. Accept Delta's C4: 6/13 joins are still false against the thick reference.

## 4. The experiment set (question 3)

| Run | Mode | Question | Remaining issue |
|---|---|---|---|
| Atlas | Trains, 256³ master config, ≤ 24 h, **first** | R0; first real 4-class tF1, FP, swaps, cuts; saves checkpoint, softmax, manifest | The vague decision row is fixed above. No A4 QA, so its tF1 is not quite the master's (acknowledged). It touches no test case |
| Bridge | Inference-only on Atlas's 80 val, ≤ 4 h | D/R/H/O and the A7 rule | None. It shares Atlas's softmax, so no re-prediction is needed |
| Delta | Inference-only on Atlas's checkpoint, open 80, steps 0.5/0.75, ≤ 10 h | Cut rate; P1′ vs default; bridging, repair; bridge audit | **It must read the A14 list, not its own.** It waits if Atlas is queued; Bridge uses `afterany`. Both are fine |
| Crucible | Trains, 6 arms, simulated habit reads, small default patch, 200/50 ICX train/val, ≤ 24 h | Under opposite habits, does the network fill the ignored band (a11 vs both against the truth)? | Conditional on the error model, as before. It now asks the one question CPU cannot answer (FILL vs worst case). Independent of the other three |

**Redundancy:** resolved. One master-config training serves three questions, and Crucible's run is a different question on a different model by design. Total ≈ 62 H100-h, down from ≈ 96.

**Coverage:** the questions that can be answered before team reads are covered:
- feasibility;
- the real cut, swap and FP rates;
- naming competitors;
- connectivity post-processing;
- the one open fusion mechanism.

**Gaps, unchanged and acceptable:**
- real two-read behaviour (only wave 1 can show it, via A12);
- the A1 aorta-contact ostium in the runs (absolutes stay provisional under A9; paired differences are valid);
- quality-0 performance (no labels);
- the ablations (A0–A4, after R1).

**New gap, cheap:** the A12b noise-floor measurement (CPU).

## 5. What would change the ruling

- **Atlas (to keep the title):**
  - Publish the A14 sealed list before any Trillium run.
  - Port tF1 to `src/segtrain` (A9).
  - Wire Bridge's decision extractor into `fuse_reads.py`; it is still a separate call.
  - Run R0, and report against the now-numeric decision table.
  - A short R1 with swap rate ≥ 5 % or many cuts reopens the title to the competitor that fixes it.
- **Bridge:** The D/R/H/O result decides everything. If R or H wins by A7 on Atlas's val and again on R1, naming passes to Bridge's stage. It must also declare its full development-case list for A14.
- **Crucible:** Measure the A12b convention noise floor on ≥ 100 cases. Without it, the anchor's 1 mm thresholds are unfounded. The GPU result then decides the narrowing rule in A11.
- **Delta:** Its Trillium C2 comparison on the A14 open 80 decides P1′. It must declare its development cases for A14 and point `./delta` at the published list.

## 6. Decisions that belong to humans

1. **The A10 margin (0.02).** Still for the clinical lead. The new evidence: under a shared carina ambiguity a converged model only ties inter-read, so 0.02 may be strict, not lenient.
2. **Pairing reads across annotator habit groups** (Crucible), if A12a finds habits. This is a scheduling choice for the labelling lead.
3. **If A12b finds a team-wide carina bias:** whether the team's carina convention is re-instructed toward ImageCAS-X's, or kept as the project's own definition. Under D0 the team's split is the reference, so "bias" relative to ImageCAS-X becomes a correction only if the clinical lead says the ImageCAS-X carina is the anatomically intended one.
4. **Third-read budget ceiling** (carried over from Round 3).
