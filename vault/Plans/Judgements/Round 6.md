---
tags: [plans, judgement]
round: 6
updated: 2026-10-10
---

# Round 6 ruling

This round was CPU-only, and atlas2 (A16) is still running. Every number below is checked against the advocates' notes and, where stated, against code. No new GPU result exists apart from Delta's P1′ run, which completed after Round 5.

## 1. Master plan: **Atlas v7**, adopted with these binding changes

The master does not change. Atlas v7 §2.7 is the first concrete fine-tuning recipe, and its skeleton is sound:

- one 160-case decision set;
- at most one comparative decision per wave;
- frozen plans, window and normalisation;
- non-regression every wave;
- final model from scratch.

Crucible v8 was written against Atlas v6. Most of its points (a relative proxy test, deciding team-only at 300, identical initialisation in comparison arms) are already in v7. Foxtrot v1 challenges nothing structural and finds two real defects in the warm-start mechanics. Delta, Bridge and Echo contribute evaluation and implementation corrections.

### Resolved since Round 5 (by pre-registered rules)

**A2: closed.** Delta's run on the master checkpoint (27 clean open cases) gave:

- C2 = +0.0007, CI [−0.0061, +0.0059];
- primary read −0.0017;
- 3 cases worse by more than 0.01;
- re-inference adds 0.18 FP components per case.

All four of Delta's v5 requirements fail. **P1′, P1 and P2 leave the recipe.** Default nnU-Net inference at tile step 0.5 stands. Two caveats: n = 27, because Delta's own launcher silently dropped 17 cases (disclosed, and fixed); and the run used the old cheap ostium rules. Neither caveat rescues P1′: the measured headroom is 0.004, below the 0.016–0.019 MDE at this n.

### Amendments

**A17: fine-tuning recipe = Atlas v7 §2.7, with five changes.**

**A17a. Fine-tune trainer (from Foxtrot F1).** This is a precondition, not an option. Foxtrot's code reading of nnU-Net 2.8.1 is accepted: `load_pretrained_weights` skips `.seg_layers.`, so every deep-supervision head is re-initialised, and no LR warm-up exists in nnU-Net, `src/segtrain` or `trillium/`. Atlas v7's "all layers" plus "10-epoch linear warm-up" therefore cannot be run with existing code. Before FT1, the trainer owner (Atlas) must ship `nnUNetTrainer_segtrain_finetune`, which:
- loads the full state dict, including `seg_layers`, and asserts identical plans, classes and keys;
- ramps the LR linearly over a stated number of iterations, then applies poly decay;
- logs both;
- comes with a CPU test, as Foxtrot specified.

**An FT1 warm arm run on stock `-pretrained_weights` is not decision-grade.**

**A17b. Correct the citation; keep the 1e-2 peak; add Foxtrot's F2 fallback.**
- Atlas v7 point 4 misreads Wald et al. (CVPR 2025). The paper supports warm-up, but found a **1e-3** peak better than 1e-2 for fine-tuning (71.76 vs 71.02), and its warm-up was 50 epochs, not 10. The v8 text must say so, and must state the 10-epoch warm-up as a deviation from the source.
- The 1e-2 peak is kept as the primary arm on Atlas's first-principles argument. With every data source present there is nothing to forget, and the purpose of a warm fine-tune is to move the model *away* from the proxy's convention. Crucible's simulation (team reads beat the proxy as a teacher by +0.013 to +0.028 on the A10 score) favours a higher LR. The MAE paper's setting (SSL, a new task, brain MRI) is not ours.
- **F2 is adopted as pre-registered.** If FT1-warm at 1e-2 fails non-inferiority, one warm arm at 1e-3 runs before warm starts are retired (12.2 H100-h, only in that branch).

**A17c. The proxy admission test (from Crucible v8) has consequences.** Atlas v7's W1 test (proxy vs reads, non-inferior to inter-read within 0.02 per class) is the right construction. Atlas's "any class failing → proxies stay until W4" leaves a measured problem unaddressed for two waves. Rule:
- If the W1 admission test fails in any class, **the proxy-drop test moves forward to W3**, replacing warm-vs-scratch as W3's one decision.
- Warm-vs-scratch then moves to W4.
- If W1 passes, Atlas's order stands.
- The absolute "< 0.80" rule stays only as a backstop. Crucible shows it cannot fire, because the proxy scores 0.91–0.93 against the reads in every simulated regime.

**A17d. Scope of the proxy question.** This is a first-principles point both plans missed. **The final model never trains on proxies.** D2 reads every case twice, and Atlas v7 W6 has every ImageCAS-X training case read. The proxy-drop decision therefore governs only interim models (W4/W5). Its stakes are QA quality and wave-to-wave comparability, not the shipped model. This is why the warm initialisation shared by the W4 arms (Crucible's identical-init rule, already in v7) is acceptable: it would bias team-only upward only for a decision that does not reach the final.

**A17e. The decision set is Atlas's 160, not Crucible's 50.** Atlas's power note gives these MDEs: 0.010 at the noise floor and 0.022 for a label-form change at n = 80; 0.007–0.015 at n = 160. A 50-case fold could not resolve the 0.01 margins the recipe uses. Crucible's underlying point, one frozen comparison set across all waves, is what the 160-case set already is.

The 44 development cases in the open 80 may serve as decision cases. They were inspected for components that are now retired (the namer as a shipping step, P1′), not for the fine-tuning recipe.

**A18: A10 acceptance is suspended pending a human decision, and frozen before any sealed read is scored** (from Bridge v6 E1–E3; §5 below).

Bridge's power analysis is accepted as a *provisional* fact. Its contrast SD (0.14–0.19) comes from simulated reads on a small model, and the master's own per-case SD is at least as large. Under A10 as written (per class, 0.02 margin, n = 100), a model exactly at inter-read level passes all four classes with probability ≈ 0, so the rule acts as a superiority test of about +0.04 per class. The type-I side is fine: a model 0.02 worse passes at most 7 % of the time per class.

Two binding steps before the clinical lead decides:
- **E3:** re-estimate the A10 contrast SD on the master model scored against the wave-1 reads (CPU) and update the power table.
- **E2:** the A1b flagged-tree review is **mandatory** before sealed scoring. Bridge estimates that removing artefact tails roughly doubles power.

**A19: multiplicity and the sealed test** (from Bridge v6, modified).
- **E4, adopted.** The sealed test gets **one decisive look** (the final model), plus at most one pre-declared interim look that changes no decision. A sealed guard is added (Echo's suspicion, now binding): `reads-report`, `tf1` and `name` refuse sealed cases by default and need an explicit milestone flag.
- **E5, adopted.** Every decision table states its MDE at its n. A test whose pre-registered expected effect is below its MDE is reported only, and the default stays.
- **E7, adopted.**
  - The FP gate is read as the **point estimate** on the 100 sealed cases, with its CI reported.
  - The epoch rule keeps 250/500 epochs only if the gain's **upper** CI bound is < 0.02.
- **E6, replaced.** Bridge's "final vs R1 baseline" cannot detect a false adoption: a team-read final model will beat a proxy-only R1 whatever was adopted. Instead: if **two or more non-forced adoptions** reach the final recipe, one control is trained from scratch at the final stage on the same final data with every non-forced adoption reverted. The stacked recipe ships only if it is non-inferior to that control on the 160-case decision set, margin 0.01.
  - Non-forced adoptions: threshold T, A3 rotation, 5-fold ensemble, F3.
  - Forced choices, which need no correction: window, A11 form, warm vs scratch, proxy drop.

  With P1′, P1, P2, R, H and Skeleton Recall gone, the remaining non-forced family is about 4, not 11, which puts the family-wise false-adoption risk near 10 %.
- **Per-class results never decide an adoption.** This is now stated as a rule.

**A20: Foxtrot's F3 (heart ∪ aorta ROI component rule) is allowed under A15, conditionally.** A15 permits a component-deletion filter only with evidence that it removes no reference vessel. F3 is the right kind of filter:
- it is computed from the CT alone, by a frozen external model;
- it is fixed **now**, before any FP component has been inspected (d = 25 mm, min-distance rule, disabled when the heart mask is < 5000 voxels at 3 mm);
- it cannot touch a predicted component that overlaps the reference, as long as every reference voxel lies within d of the ROI.

That guarantee currently rests on **40 cases** (maximum 16.5 mm). Adoption needs all four of the following:
1. **Reference-side guarantee on the whole cohort (CPU).** TotalSegmentator `heart, aorta` on all 1000 CTs, which A1 already requires for the aorta. The maximum reference-to-ROI distance must stay ≤ d − 5 mm in every non-sealed case; otherwise d is raised, before any prediction is examined. Sealed cases are checked by an automated pass that reports only pass/fail.
2. **What atlas2's census must show (pre-registered now, before its results are seen).** atlas2's census categories (`icx_vessel`, `low_confidence`, `confident_other`) do not measure ROI distance. A CPU re-analysis of atlas2's saved val segmentations adds one column: each FP component's minimum distance to heart ∪ aorta. F3 proceeds only if **≥ 25 %** of raw FP components lie beyond 25 mm.
3. **The effect.** On val, FP components per case fall, with a paired CI excluding 0, and macro tF1 is not lower (this is guaranteed for reference-touching components; the check confirms the implementation).
4. **Reporting.** The raw FP count is always reported beside the filtered one.

If all four hold, F3 is part of the deployed output, and **the A15 gate is read on the deployed output**. Rationale: A2's raw-gate rule exists to stop repairs (joins) from hiding FPs. F3 removes components far from the heart by a rule fixed in advance, and it hides nothing near the tree.

F3 counts as a non-forced adoption under A19.

**A21: implementation (from Echo).** Echo's 13 defects are recorded as fixed by their owners, with tests. The suite is 679 passed, and the `tf1.py` hash is unchanged (3c737cbc…9253). The critical D2 sealed leak via SegQueue names (`imagecas_NNNN`, `__r2`) was the most important finding of the round. Binding additions:
- **A dry run of one real approved SegQueue export** through index → convert → reads-report must pass before wave 1 (Echo's recommendation).
- **An aorta producer** (a batch TotalSegmentator step) must be in `src/segtrain` before any decisive tF1 is computed outside a Trillium job (A1a).
- Echo's remaining suspicions go to their owners as tasks. These are: silent skeleton class loss, silent A4 skip when the namer fails to import, patch pinning, and LM present in one read only (that last case is ruled a decision disagreement, so it triggers a third read).

**Delta v7: Phase A falsifier accepted as pre-registered.** For unflagged trees: RCA A1-tF1 ≥ 0.85; class order LM > LAD ≈ RCA > LCx; RCA gain ≥ 0.07. If RCA comes in below 0.84, or is still the lowest class, Delta's Q2 taxonomy fails on its main term.

The miss census (Delta §2C, CPU) is approved, to run on the atlas2 segmentations once they are copied off $SCRATCH. The joined-tree reference list (§2D) goes to the labelling lead.

## 2. Scorecards

Scores are out of 5.

| Candidate | (a) Reasoning | (b) Evidence | (c) Fit | (d) Risk/cost | Verdict |
|---|---|---|---|---|---|
| **Atlas v7** | 4.5. A coherent recipe with an explicit power basis. It missed that the final model never sees proxies (A17d). | 3.5. The power note is sound but borrows SD from a small simulated model, as it says. **The Wald et al. citation is misread** (the paper prefers 1e-3, with a 50-epoch warm-up), and "all layers" is false under stock nnU-Net. | 4. The warm arm is not implementable as written (A17a). | 4.5. ≈ 170 H100-h R1 → final, every fine-tune in one job. | **Keeps the title**, with A17a–e |
| **Foxtrot v1** (new) | 5. The most precise contribution of the round: two code-level facts that would have invalidated FT1 silently, and a filter that is safe by construction. | 4.5. Primary sources quoted, code read. The ROI guarantee rests on 40 cases, which Foxtrot states. The literature survey is plausible; I cannot verify its citations under my constraints and do not rely on them for any binding rule. | 5 | 5. F1 costs half a day of engineering; F2 and F3 are conditional; F4 is conditional and costed. | F1, F2 and F3 adopted (A17a, A17b, A20). F4 noted as a conditional proposal, not scheduled |
| **Crucible v8** | 4.5. The relative admission test is correct, and the honest negative on proxy calibration (−0.009 under team bias) is to its credit. | 3. Every proxy-vs-team number is simulated (14 cases); the GPU support (oracle 0.778 vs both 0.789 against the reads) is one seed. | 4. Written against v6. Its 50-case fold is underpowered. | 5. CPU only. | Admission-test consequence adopted (A17c); fold size rejected (A17e) |
| **Bridge v6** | 5. Turned the acceptance rule's power into a question the humans can actually answer, and withdrew its own renaming test once it showed the test could not decide anything. | 4. Real per-case distributions; the A10 contrast SD is simulated, as stated. | 5 | 5. No GPU. | E2–E5 and E7 adopted; E6 replaced (A18, A19) |
| **Delta v7** | 4.5. A falsifiable taxonomy, stated before the result. | 3.5. The RCA/ostium decomposition is solid. The extent attribution is correlational (ρ 0.33–0.57), as it says. The flag rate (27 % of trees; 95 % of unflagged trees right) is measured. | 3.5. Its extent rule conflicts with D0/D4 (§3 C5). | 5 | Phase A falsifier and miss census adopted; extent rule referred to humans |

## 3. Rulings on the questions put

### C1. The fine-tuning recipe

The recipe is Atlas v7 §2.7, as amended by A17. Where the plans differ:

- **Warm start.** Atlas's FT1 test (warm 250 vs scratch 500, margin 0.01) stands. It is a forced choice that only saves compute (about 24 H100-h if warm wins), and the final model is from scratch either way. It is valid only with the A17a trainer.
- **LR.** 1e-2 primary, 1e-3 fallback (A17b).
- **Proxy timing.** The admission test has teeth (A17c), and the question's scope is interim only (A17d).
- **Decision set.** 160 cases (A17e).

### C2. A10's margin

This decision belongs to the humans; see §5 for exactly what is to be decided. The tournament's ruling is limited to three points: the rule as written is effectively a superiority test (accepted, provisionally); its contrast SD must be re-estimated on real reads first (E3); and it must be frozen before sealed scoring.

### C3. Multiplicity

A19 governs. With the closures, the family is small, so a stacked-recipe control replaces a Holm correction.

### C4. F3 against A15's "never delete ≥ 100 voxels"

The "never delete" rule protects reference vessel. F3 is the one deletion rule that can prove, on the reference side, that it cannot delete reference vessel. It is therefore allowed under A15's exception once the cohort-wide check, the atlas2 census column and the val effect are in (A20). What atlas2's census must show first: **≥ 25 % of raw FP components with a minimum distance > 25 mm from TotalSegmentator heart ∪ aorta.** If FPs sit on the epicardium (veins, side branches outside the mask), F3 does nothing, and A15's other branches apply.

### C5. Delta's extent rule against D0/D4

**This is a human decision; the tournament cannot adopt it.** Delta's rule ("every branch ≥ 1.5 mm at origin, to where it falls below 1 mm") has two halves:

- **Adding vessel the mask lacks** is impossible under D4: edits are confined to the mask.
- **Trimming sub-rule branches the mask contains** is mechanically possible, since the protocol's "stop where the lumen is no longer confidently distinguishable" already allows trimming. But it would redefine D0's reference from "the original ImageCAS mask, split" to "the mask, split and trimmed by rule".

Scoring sub-rule branches as `ignore` would change the frozen metric's inputs, which falls under A1c, and would also depart from D0. The evidence is correlational. It is relevant but not decisive: on a thick reference whose extent varies case to case, an irreducible error floor is plausible from first principles, and Delta's miss census can localise it.

The options for the humans are listed in §5.

### C6. Does the master change?

No.

## 4. Contested facts

1. **What Wald et al. found about the fine-tuning LR.** **Foxtrot is accepted** over Atlas. It quotes the paper's observation (ii) and Table 3; Atlas's summary attributed the paper's pretraining hyper-parameters to its fine-tuning.
2. **What nnU-Net's warm start transfers.** **Foxtrot's code reading is accepted.** It is specific (a named skip list and docstring), and Atlas's text cites no code.
3. **When proxies should be tested for removal.** Atlas v7 and Crucible v8 converged on 300 cases. The remaining difference (whether a failed admission test changes anything) is resolved by A17c.
4. **How large a decision set is needed.** Atlas's 160 against Crucible's 50: **160 is accepted**, on both advocates' own power numbers.

## 5. What would change the ruling

**Atlas, to keep the title:**
- Ship the A17a trainer and its test before FT1.
- Fix the citation (A17b).
- Report atlas2 under the frozen metric with the Delta falsifier and the F3 census column.
- Pass the A21 dry run before wave 1.

An atlas2 census showing confident hallucinations near the tree (`confident_other`) would reopen the recipe.

**Foxtrot:** F4 (pretraining) gets an arm only under its own trigger. Before then, measure the reference-to-ROI maximum on all non-sealed cases.

**Crucible:** On wave 1, re-run the proxy-vs-team comparison on real reads (the admission test). If proxies fail it, the A17c reordering takes effect.

**Bridge:** After E3, publish the power table on real reads. That is the input to the human margin decision.

**Delta:** Phase A against the pre-registered falsifier. Then the miss census, to locate the RCA/LCx residual.

## 6. Decisions that belong to humans

1. **A10's acceptance rule (clinical lead).** Taken once, after the E3 re-estimate on wave-1 reads, before any sealed read is scored. Decide:
   - **(i) The margin δ.** By how much may the model fall short of a second team reader and still count as human-level: 0.02, 0.04 or 0.05 tF1?
   - **(ii) Per vessel or on average.** Must the claim hold for every class (LM, LAD, LCx, RCA) or for macro tF1, with a per-class safety floor?
   - **(iii) The power you accept.** At n = 100 (Bridge, provisional), a 0.02 per-class margin passes a truly human-level model with probability ≈ 0 on all four classes. A model must be about 0.04 better than a reader to pass with 70 % probability.

   The options:
   - **(a)** 0.05 per class, with macro primary at 0.04;
   - **(b)** 0.02 on macro only, with per-class point estimates no lower than −0.05;
   - **(c)** keep 0.02 per class, and accept that the claim effectively means "better than a second reader";
   - **(d)** enlarge the sealed test. 80 % power at δ = 0 needs about 380–680 cases per class, taken out of training.

   The type-I risk of accepting a worse model is low under (a) and (b): ≤ 7 % per class at the margin.
2. **Extent rule (labelling lead with the clinical lead).** The options:
   - **(a)** status quo: split only, trimming left to the reader's confidence;
   - **(b)** a written trimming-only rule inside the mask (e.g. drop branches < 1.5 mm at origin, stop below 1 mm). This amends D0's reference definition;
   - **(c)** a scoring-side `ignore` for sub-rule branches. This amends D0, and the metric inputs fall under A1c.

   Adding vessel outside the mask is not an option under D4.
3. **Flagged-ostium review budget (labelling lead).** About 0.55 flagged trees per case: roughly 9 reader-hours over 1000 cases, or about 1 hour for the 100 sealed cases. This review is now mandatory before sealed scoring (A18, E2).
4. **The FP gate's reference** (carried over from Round 5), if atlas2's census finds most FPs are `icx_vessel`.
5. Carried over: the third-read budget, and pairing reads across habit groups if A12a finds habits.
