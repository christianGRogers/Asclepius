---
tags: [plans, judgement]
round: 8
updated: 2026-10-11
---

# Round 8 ruling

This round rests on two GPU results: atlas2 (the A1 re-score, the FP census and the window ablation) and Crucible's second seed. I checked both raw `SUMMARY.md` files against the notes, and every number quoted below matches:

- **Run 1 under A1:** decisive macro tF1 0.896 (LM 0.966, LAD 0.901, LCx 0.846, RCA 0.883); 44/316 trees flagged.
- **Window ablation (B − run 1):** tF1 −0.0027 [−0.0118, +0.0062]; FP −0.188 [−0.475, +0.100]; B ran 368 epochs.
- **FP census:** 79 % `confident_other`.
- **Crucible seed 2:** a11 − both +0.012 [+0.000, +0.026] against the truth and +0.011 against the reads. Seed 1 gave −0.008 and −0.035.

Human decisions D6 (A10 margin 0.05 per class) and D7 (keep the outline; noted major-error corrections only) bind from now on.

## 1. Master plan: **Atlas v9**, adopted with these binding changes

The master does not change. Run 1 scored 0.896 under the A1 ostium, above the 0.87 line that would have reopened the recipe, so the recipe stands. The one part that reopens is the FP lever, because the census routes 79 % of FP components to `confident_other`. Atlas's response (a pilot of an FP-aware loss before R1) is the right next step, with the conditions in A24.

### Amendments

**A10, reinstated by D6.** The margin is **0.05 per class**, for each of LM, LAD, LCx and RCA, against inter-read tF1 on the sealed test. Bridge v7's S1 (macro primary at 0.02) is overridden. Bridge's E2/S2 requirement stands: the A1b review of flagged sealed trees must be complete before sealed scoring, because flagged trees cut the RCA's n by about 30 %.

**A1c, a new metric hash: the fallback centreline becomes the decisive default.** This was Delta's proposal, and Round 7 required it before A10 was frozen; D6 has now frozen A10. The evidence:

- On all 116 run-1 predictions the report-only hash is bit-identical, and its new field lists exactly the expected 6 cases (test 3).
- The fallback changes no decisive aggregate, because all 6 cases have a flagged left ostium.
- It does expose 2 real LM errors (c0772, c0807: LM about 0.29) that the old default hid (test 8).

Binding conditions:

1. Round 7 tests 5–7 (a perfect prediction scores 1.0; LM renamed LAD scores 0; bit-identity where a centreline exists) must pass in the suite.
2. The new sha256 is pinned in [[Master plan]] and in every decisive script **before run 3 is scored**.
3. For one round, every decisive report shows both hashes paired.
4. The old hash stays the pin for atlas2's results.

**A15/A20: F3 withdrawn (from Foxtrot v3); A20 retired.** The pre-registered condition (≥ 25 % of FP components beyond 25 mm of heart ∪ aorta) fails:

- exactly 0 of 26 FP components on the 17 val CTs Foxtrot measured;
- at most 17–19 % on all 80, by the census bound;
- 91 of 94 `confident_other` components lie within 25 mm of the coronary tree (Atlas).

The 908-case cohort job is withdrawn with it. **The A1 aorta requirement is not withdrawn.** Every decisive tF1 still needs TotalSegmentator aortas. Atlas measured about 112 s per case on the node for a full CT, so aortas must be computed before jobs or on crops (A21's producer); they must not be computed inside a training job's walltime.

**A2 window: default, by the pre-registered rule, recorded as a tie-break.** I uphold the rule as written:

- tF1 tied (CI −0.012 to +0.006);
- fewer FP components in B (point estimate), so default wins.

A pre-registered rule is applied as written unless its premise has been falsified, and nothing here falsifies it. The window is a forced choice with small stakes. Atlas's argument is sound: the truncation (368 of 412 epochs, LR left at 1.3e-3) handicaps the winning arm, both on FP (the low-LR tail cleans up stray components) and on tF1.

What is **not** claimed: that default reduces FP. That CI crosses 0, and Bridge's MDE is 0.42 per case (Bridge S5, adopted). Atlas's two guards are binding:

- R1-default must be non-inferior to run 1 on decisive tF1 (lower bound > −0.01). Window and epoch count are confounded in this check, so it is a red-flag check, not a test of the window.
- LCx decisive tF1 below 0.83 on R1 val triggers a review of calcified LCx cases. The default window clips at 719 HU, B's LCx was −0.018 (CI to −0.043), and the LCx is now the weakest class.

**A22: the seed rule (Bridge S3 and S4, Crucible's A18-seeds).** Seed variance is now evidenced at network level. In Crucible's runs, a11 − both against the reads changed sign between seeds (−0.035, then +0.011); the seed × contrast interaction excludes 0; and arm means move by up to 0.025. So:

- **Retrained-network decisions** (ablations, team-only vs team + proxy, 5-fold vs single, any loss change):
  - the CI includes a seed term, SE = √(SE²_case + σ²_seed), with **σ_seed = 0.013** on macro tF1 until it is measured on the master;
  - a pooled effect under 0.02 needs **≥ 2 seeds** to be decided; otherwise it is "no difference detected" and the default stays.
- **Forced choices** may stay single-seed and are labelled as such.
- **Decisions on fixed predictions** (post-processing, inference settings, naming) keep case-only CIs.
- **Equal epochs** are a precondition of any paired training comparison (S4). An arm stopped at a deadline is compared at the control's matching epoch, or the comparison is reported, not decided. Every future job sets its epoch count from the time actually left before training starts, so that the poly schedule completes. That is Atlas's own lesson from atlas2.
- **Measuring σ_seed.** Bridge's standalone seed replicate of the window (≈ 40 H100-h) is **not approved**: the window is settled and forced. σ_seed is measured by adding a second seed to the control arm of the first retrained decision that needs it (A23 below, if its result is near the threshold, or the A3 rotation ablation).

**A11′: stands, re-grounded (Crucible v9).** Pooled over 2 seeds, a11 − both against the truth is +0.002 [−0.020, +0.024]. The narrowing row never fires. The Round 5 claim that a11 is significantly worse against the reads was seed-1 only and is **withdrawn**. A11′ stays on the grounds of simplicity, never being worse, and removing a failure mode:

- the ignore band is filled with one annotator's LM in 1 of 2 a11 runs and 2 of 2 union runs;
- union is the worst arm against the reads in both seeds (−0.032 [−0.054, −0.011]).

The conditional A11 test is **withdrawn**: agree ≈ both in both seeds, so there is no effect for it to detect. Two-read targets beat one read against the truth (+0.023, CI seed-random [+0.003, +0.042]), so D2's second read is worth training on.

**A17c, the proxy admission test, now at D6's 0.05 per class (Crucible v9).** A proxy is admitted if and only if it would pass as a model. The construction is coherent. One consequence: in every simulated regime the proxy sits within ±0.015 of inter-read, so this test will rarely fire. The operative proxy decision is therefore the W4 team-only vs team + proxy run, under A22. The stakes are interim only (A17d).

**A3 under D7 (implemented by Crucible).** A wave halts only on more than 10 % **un-noted** departures from the outline. Noted major-error corrections are listed per wave and do not halt. A rising share of noted corrections is a re-instruction trigger.

**A23 (adopted from Delta v8 §C): a report-only extent diagnostic.** Every decisive tF1 is reported beside "tF1 on contrast-supported reference", meaning reference centreline below 0.3 × median aortic HU is excluded from recall. It decides nothing. The per-read share of low-HU centreline is added to the A3 report, for information only, never as a halt trigger. If it is ever made decisive, A1c applies.

**A24: run 3 (Atlas's FP-aware loss pilot) is approved before R1, with conditions.**

Why it is justified now:
- The census routes the FP lever to the recipe (79 % confident; p90 ≥ 0.94; neither a threshold nor ROI rule removes them).
- Atlas's anatomy reading is specific and evidenced: vessel-calibre tubes 1–14 mm beside the tree, in epicardial fat, core about 0.45 of the adjacent lumen on 21 components; that is, **cardiac veins**, with a minority of unannotated small branches.
- The mechanism is plausible: these structures are about 0.8 % of predicted volume, nearly free under DiceCE, while the gate counts components.
- The pilot costs at most 21 h, uses warm fine-tunes from B (A17a trainer), and nothing urgent waits on R1, because no team reads exist yet.
- Running R1 first and changing its loss afterwards would waste 48.6 h.

Conditions:
1. **Pairing.** F0 (plain) and F1 (FP-aware, λ = 1, γ = 2) start from the same checkpoint with the same seed and the same data and augmentation stream, so that the loss is the only difference. Both arms get equal epochs (A22). If the walltime is short, both are shortened equally, with the schedule completing.
2. **Decision table (Atlas's, amended for A22).** Adopt the FP term only if:
   - FP components per case fall, with the CI excluding 0 (MDE about 0.41 per case);
   - **and** decisive tF1 is non-inferior at margin 0.01, *with the seed term included*.

   A single-seed tF1 result inside ±0.02 is then reported as "no difference detected". Adoption may rest on the FP effect plus tF1 non-inferiority under the seed-inclusive CI. If that CI cannot exclude −0.01, a second seed of both arms (about 20 h) decides before R1, and the run counts as this round's σ_seed measurement.
3. **Report alongside, per class:** recall on ImageCAS-X-traced centreline, recall on mask-only low-HU centreline (Delta's split), and the A23 diagnostic.
   - Reason, from the interaction of Delta's census and Atlas's census: the training target appears to treat vein-like, low-contrast structure inconsistently. The model misses low-HU mask vessel (HU 39–91, against an aorta at 472) while predicting veins outside the mask. That is the signature of label noise on veins, not only of a weak loss.
   - The FP term acts only on voxels more than 1.5 mm from any label, so it cannot directly suppress in-mask vessel. But if veins are labelled vessel in some masks and background in others, the term will pull against those labels. The per-class split shows whether it does.
4. **Atlas's risk sentence must be corrected.** Atlas says suppressing real unannotated branches "is the intended behaviour" under D0 and D7. **D7 lists "a missing vessel segment" (and "a vein") as a major error readers may correct**, so a few real branches may enter team reads. That is rare, which is why it does not block the pilot; but the statement as written is wrong.
5. The metric is the new A1c hash (fallback default), pinned before scoring.

**R1 at full length (48.6 h)** runs after run 3: default window, plus the FP term if A24 adopts it. If run 3's verdict is "no difference detected", R1 runs plain.

**Foxtrot's FP triage (CPU) is approved as a report**, not a gate on run 3. It should extend Atlas's 21-component enhancement analysis (veins vs unlabelled branches vs mask artefacts) to as many cases as have CTs. It matters for two things: interpreting run 3, and the human question below if the term fails.

## 2. Scorecards (this round)

Scores are out of 5.

| Candidate | Reasoning | Evidence | Fit | Risk/cost | Verdict |
|---|---|---|---|---|---|
| **Atlas v9** | 4.5. Applied its window rule honestly and named both signals it could not explain away (LCx, flagged trees). The FP anatomy reading is the most useful single analysis of the round. | 4. The census is solid. The vein reading rests on 21 components with CT; the remaining 73 have only mean HU. Its Phase A time forecast was wrong by 4×, which caused the truncation. | 4. The D7 sentence is wrong (A24.4). | 4. Run 3 at ≤ 21 h. | **Keeps the title** |
| **Delta v8** | 4.5. Its falsifier passed as written, and it volunteered the like-for-like gain (0.065–0.067, just under 0.07) and that RCA is still last once flagged trees are counted. | 4. The miss census replicates the module exactly. The HU evidence covers 17 cases and is biased toward the artefact cases, as stated. | 3. Its extent rule (§B) contradicts D7. | 5 | Fallback default adopted; diagnostic adopted (A23); extent rule refused (§3 C5) |
| **Crucible v9** | 5. Corrected its own Round 5 headline on a second seed and re-grounded A11′ on what survives. | 4. Two seeds with a proper seed-random CI. Still simulated reads and a small model. | 5 | 5 | A11′ re-grounded; A18-seeds folded into A22; admission test at 0.05 |
| **Bridge v7** | 4.5. Real A1-scored variance (per-case SD 0.064, sealed MDE about 0.012), and the seed problem quantified. | 4 | 3.5. S1 is overridden by D6. | 4. The 40 h window replicate is not approved. | S2–S5 adopted (A22); S1 overridden |
| **Foxtrot v3** | 5. Withdrew its own amendment on its own pre-registered condition, and counted only measured cases as passing. | 4.5 | 5 | 5 | F3/A20 withdrawn; triage approved |

## 3. Rulings on the questions put

### C1. The window

Default, by the pre-registered tie-break. It is recorded as "not shown better", with both guards binding. Bridge is right that the FP difference is within noise. The rule was pre-registered precisely to break ties on a forced choice, and a tie-break is allowed to be a coin flip.

### C2. R1, and whether run 3 comes first

Run 3 comes first, under A24's conditions; R1 follows. Run 3 is justified because the census reopened the FP lever by a pre-registered route, and the pilot is cheap relative to R1. R1 waits on it because it would bake in the loss.

### C3. Foxtrot's withdrawal

Accepted. A20 is retired, and the A1 aortas remain required.

### C4. Crucible's pooled result and the seed rule

A11′ stands, on different grounds than before. The seed rule is A22. Under A22, both A11′ itself and Round 5's A11′ adoption are single-seed-era decisions. A11′ survives because the narrowing row never fired in either seed, and simplicity breaks the tie.

### C5. Delta's falsifier, its fallback, and its extent rule under D7

- **The falsifier passed as written.** I note the honest caveat: the gain clause compared unflagged trees now with all trees before, and the like-for-like gain of 0.065–0.067 falls just under 0.07. The taxonomy's main term (the provisional ostium) is confirmed.
- **The fallback default:** adopted (A1c above).
- **The extent rule is refused.** D7 is a human decision, taken knowing of Delta's earlier proposal ("Delta's proposed extent rule is therefore not adopted as a general rule"). A rule like "lumen with contrast, ≥ 1 mm, to where it is no longer distinguishable" would license general redrawing. D7 permits only noted major-error corrections.
- **What D7 does allow is the narrow version of Delta's point.** A vein inside the mask, or a missing vessel segment, is a major error a reader may correct and note. If Delta's low-HU mask-only vessel is partly veins, D7 already lets readers remove them case by case.
- **The tournament's contribution:** Delta's per-read low-HU share in the A3 report (A23) will show how often readers use that permission, and the wave-1 miss census will show whether recall on the remaining mask-only vessel rises once the reads are cleaner. Whether to widen D7 is for the humans, and only with that evidence.

### C6. Does the master change?

No.

## 4. Contested facts

1. **Does a11 hurt against the reads?** No. Seed 1's −0.035 reversed to +0.011 in seed 2. The **pooled two-seed result is accepted** (Crucible v9), and the single-seed claim is withdrawn.
2. **Does the truncation of B void the window comparison?** No. Its bias runs against the winner, so the verdict stands, though no effect size does (Atlas, Bridge).
3. **What are the confident FPs?** Mostly cardiac veins, on location, calibre, a fat ring and enhancement of about 0.45 of the adjacent lumen (21 components). The reading is accepted as the working hypothesis, not as a label. Foxtrot's triage extends it.
4. **Is the remaining recall loss a model failure?** Mostly not. The model recalls 93–97 % of expert-traced centreline. The loss sits on low-contrast mask-only vessel (Delta). This is accepted for run 1; it must be re-checked on team reads.

## 5. What would change the ruling

- **Atlas:**
  - Run 3 under A24, reported with the per-class recall split.
  - Correct the D7 sentence.
  - Then R1 with the R1 guards.
  - If the FP term fails, the gate's achievability goes to the humans with the census as evidence.
- **Delta:**
  - Pin the new hash, with tests 5–7 shown passing.
  - Run the miss census again on wave-1 reads.
  - If run 3 shows the FP term suppresses in-mask low-HU recall, that is evidence for the label-noise reading of the veins.
- **Crucible:** none pending. The proxy admission test and A12a run on wave 1.
- **Bridge:** σ_seed on the master from the first A22-triggered second seed. Publish the updated power table under D6.
- **Foxtrot:** the FP triage note.

## 6. Decisions that belong to humans

1. **The FP gate's achievability (A15), if run 3 fails.** The confident FPs are mostly veins beside the tree. They are real errors under D0, but no lever measured so far removes them. The clinical lead may then need to decide between three options:
   - keep ≤ 1 per case as a hard gate;
   - redefine the count, for example as components carrying arterial-phase contrast;
   - accept a higher rate with a stated clinical rationale.
2. **Whether to widen D7**, only if the wave-1 A23/A3 reports show readers are not using the vein/missing-segment permission while low-HU mask vessel dominates the loss.
3. Carried over: the flagged-ostium review budget (now a power requirement under D6), and the third-read budget.
