---
tags: [plans, judgement]
round: 7
updated: 2026-10-10
---

# Round 7 ruling

This round is CPU-only, and atlas2 is still on Trillium. It decides one A1c question (a change to the frozen metric) and confirms implementation work against the Round 6 amendments.

## 1. Master plan: **Atlas v8**, adopted with these binding changes

The master does not change. Atlas v8 implements the A17a trainer and corrects the A17b citation.

**What A17a's trainer now does** (`nnUNetTrainer_segtrain_finetune`, plus a `_lr1e3` arm and a `_5epochs` smoke variant):
- loads the full checkpoint, output heads included, with exact-compatibility checks and bitwise verification;
- warms up per iteration, then decays poly, and logs both;
- refuses sealed or unmappable identifiers;
- has 14 CPU tests.

That is what Round 6 required. An FT1 warm arm run with this trainer is decision-grade. The citation now states that Wald et al. found 1e-3 better, used a 50-epoch warm-up, and that the plan's 10 epochs is a deviation, which is correct.

## 2. The A1c decision: tf1.py drops a reference class that has no centreline

### The defect

I read `tree_f1`. The class loop in `src/segtrain/tf1.py` does `g = rlab == c; if not g.any(): continue`, where `rlab` holds the **reference centreline** labels. A class can be present in the reference voxels but have no skeleton voxel. When that happens it leaves `per_class` and the macro mean, with no flag.

Delta shows this happens on real references, not only on Echo's synthetic boxes:
- **7 of 143** proxies (5 %): six short, wide LM stubs and one LCx.
- The mechanism is sound: skeletonisation shortens each vessel end by about its radius, so a 8–11 mm LM with a radius of about 2 mm leaves no medial voxel labelled LM.
- It is confirmed in run 1's `per_case_val.json`: there is no LM entry for c0613 or c0848.
- 11 more references have an LM centreline under 3 mm.

**Effect.** Paired comparisons are unaffected, because both arms share the reference. In the affected cases the macro is a 3-class mean, and the prediction's LM is never scored, so an LM entirely named LAD goes unseen. A10 per-class aggregates silently lose short-LM cases, and those are the cases where reads disagree most.

### The three variants

| Variant | Ruling |
|---|---|
| **(1) Report only.** Add `classes_without_centreline` to `TreeF1` and `as_row()`; every aggregate reports these cases separately, as for A1b flags. No score changes | **Approved now** |
| **(2) Score the class as missed** (tF1 = 0 when the class has reference voxels but no centreline) | **Rejected.** It is wrong by construction: a *perfect* prediction also has no LM centreline, so it would score 0 for a correct answer |
| **(3) A fallback centreline for the class**, e.g. the class's own skeleton, or its maximal-EDT voxels if that skeleton is empty, or the reference skeleton voxels nearest its voxels, scored with the class's labels | **Approved in principle. It must be validated and adopted before A10's margin is frozen and before any sealed scoring.** It is not needed before then |

**Why the variants are sequenced this way.**
- Variant 1 changes no number. It can enter now without disturbing atlas2, whose comparisons are paired and computed with a vendored copy at the old hash; atlas2 stays decision-grade.
- Leaving the gap open at the sealed milestone is not acceptable, because the clinical lead may choose a per-vessel A10 (Round 6 §6). Variant 3 therefore has a deadline: wave 1. Delta's suggestion to decide only "if wave 1 shows it is common" is not adopted. 5 % of LM cases, concentrated where reads disagree, already matters to a per-class test.
- Variant 3 applies the same definition to both A10 terms (model against reads, and read against read), so it cannot bias the comparison.

### Regression tests required for the hash change

The owner is Delta.

**Variant 1 (now):**
1. A short-LM-stub fixture. The class is listed in `classes_without_centreline`, and `per_class` and the macro are bit-identical to the old code.
2. All existing tf1 regression tests are unchanged, including the E3 perturbation set and the ostium tests.
3. **A cohort identity check.** On the 143 proxy references (val 80 and open 63) and run 1's predictions, every `per_class` value equals the old hash's output exactly, and the new field lists exactly Delta's 7 cases.
4. The reads scorer (`segtrain.reads`) and the A10 aggregates carry the new field through. Echo's D4 pattern applies: a dropped flag is a defect.

**Variant 3 (before wave 1), additionally:**
5. A perfect prediction scores 1.0 on a centreline-less class.
6. LM fully renamed LAD in such a case: the LM term falls to 0, and LAD precision falls.
7. Cases where the class has a centreline: bit-identical to variant 1 on all 143 references.
8. Paired results reported on run 1's val under both hashes: macro and LM, for the 7 cases and overall.

### Procedure (A1c)

- Each change gets its evidence note (Delta's, for variant 1) and the tests above.
- The new sha256 is recorded in [[Master plan]] and in every decisive script's pinned hash. The old hash is kept as the atlas2 pin.
- Every report states which hash produced it.

## 3. Other rulings

**A20, condition 1 (Foxtrot v2).** All 92 cached non-sealed cases pass: maximum reference-to-ROI distance 16.5 mm, against the 20 mm bound; 0 reference components deleted at d = 25 mm; no heart mask disabled.

The condition is **met only once the remaining 908 are checked**. Foxtrot's job proposal is approved as specified:
- at most 2 H100-h, after atlas2 returns;
- **folded into the A21 aorta-producer run**, since it uses the same TotalSegmentator call and the fast 3 mm model the rule was frozen with;
- sealed cases report only aggregate pass counts and the smallest passing d, with no case ids;
- the pre-registered response table applies as written.

Conditions 2–4 (the atlas2 census column, the val effect, reporting) are unchanged.

**A21, implementation.**
- `src/segtrain/aorta.py` and `segtrain aorta` are accepted. One real case: 96 s, about 5 GB, Dice 0.96 against the round-5 aorta.
- The `__main__` guard requirement must be documented in the runbook.
- Echo's export dry run passed 13/13. Its inputs were two real **binary**, z-reversed submissions with **synthetic** second reads. That proves the naming, orientation and sealed-mapping path, but not 4-class approved exports or real `__r2` replicas. **Binding:** the first real approved double-read export repeats the dry run (index → convert → reads-report, sealed refusal checked) before any wave-1 read enters training or the A12 report.
- Echo's four new findings (sealed filter in reads, duplicate case-id code, reads-report runtime, and E3, which is this metric issue) are recorded as fixed or, for E3, decided above.
- Atlas's two fixes are accepted: namer import now fails loudly, and a re-planned patch is refused.
- Suite: 718 passed, 1 xfailed.

**Still open.** atlas2's Phase A must be read against the pre-registered rules:
- the A1 re-score;
- Delta's falsifier (unflagged RCA ≥ 0.85, LCx the lowest class);
- the FP census, plus the F3 distance column added by CPU re-analysis;
- the window decision.

Every atlas2 report must also list the run's `classes_without_centreline` cases. That is a post-hoc listing, computable with variant 1 on the saved segmentations.

## 4. Scorecards (this round's contributions)

| Contributor | Assessment |
|---|---|
| **Atlas v8** | Delivered A17a and A17b as ruled, with tests, plus defensive refusals. Keeps the title. |
| **Delta** | Correctly declined to edit a frozen metric, and brought evidence and options instead: the A1c procedure working as intended. The real-reference confirmation (7/143, with GPU-run evidence) turns Echo's suspicion into a defect. |
| **Foxtrot v2** | A20 condition 1 extended to 92/92. The job proposal is sealed-safe and has its response table pre-registered. |
| **Echo** | Re-verification and the export dry run were the highest-value checks this round. Their limits (binary submissions, synthetic second reads) are stated, and that is why the repeat on a real export is binding. |

## 5. What would change the ruling

- **Atlas:** atlas2's Phase A, read against its pre-registered rules.
- **Delta:** ship variant 1 with tests 1–4 now. Propose variant 3 with tests 5–8 before wave 1.
- **Foxtrot:** the 908-case result.
- **Echo:** the repeat dry run on a real approved double-read export.

## 6. Decisions that belong to humans

None new. Carried over from Round 6 §6:
- A10's margin, scope and power, to be decided after E3. Under variant 3, the LM term will be defined for every case.
- The extent rule.
- The budget for reviewing flagged ostia.
- The FP gate's reference, if the census finds mostly ImageCAS-X vessel.
- The third-read budget.
