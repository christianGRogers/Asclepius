---
tags: [plans, judgement]
round: 2
updated: 2026-10-04
---

# Round 2 ruling

## 1. Master plan: **Atlas v2**, adopted with these binding changes

The master does not change hands. All three challengers now keep the master's model, data, schedule and deciding metric unchanged, and add parts to it. Crucible says outright that it "has no remaining claim to be a separate plan". So the question this round is which additions are evidenced well enough to bind, and which Round 1 amendments the new evidence revises.

Atlas v2 folds A1–A6 in coherently. It measured the A4 cost (0.26 % of voxels ignored, 10.5 % of cases flagged) and the 0.5 mm target-level connectivity on the thin convention. It gave R0 a falsifiable forecast, and it verified its external citations. It keeps the title.

**Revised Round 1 amendments**

- **A1 (revised, from Delta v2): the ostium procedure.**
  - The tF1 ostium is aorta contact (TotalSegmentator, ≤ 5 mm) on Trillium for all 1000 cases.
  - It is cross-checked against Delta's two cheap rules (`thick`, `pool_thick`). A tree where the rules disagree by > 5 mm is flagged for a human, not scored silently.
  - The 30-case check in Atlas v2 §3 uses ImageCAS-X `start_points` as truth, as Delta did.

  Evidence: 116/116 ostia under the cross-checked procedure. Each cheap rule failed once, never on the same tree. The cheap rules alone are not enough: `thick` misses c0526-right by 41 mm.
- **A2 (revised, from Delta v2): bridging is demoted, and the FP gate moves.**
  - **The FP-component gate is computed on the raw prediction** (threshold, then drop components < 100 voxels), before any bridging or repair. This is binding.
  - **Delta's bridge audit replaces Atlas's ">2 mm off-reference tube" false-connection count.** The audit records, per case: bridges made, orphans with no reference support, cross-tree joins, and FP components before and after. This is also binding.
  - **3 mm bridging alone (P1 as written) stays switchable but is not expected to pass.** Measured on 17 real predictions, it bought +0.010 tF1@1.5. 5 of its 12 joins attached false-positive blobs, which lowered the FP count from 1.18 to 0.88: that is gaming the gate. Delta has retracted its v1 claim of 0.78 → 0.91; that figure was a metric tolerance, and I withdraw any reliance on it.
  - **Gap-centred re-inference + support-gated bridging (Delta §2.2 steps 2–3) is added as candidate P1′.** It is judged on R1's val fold by tF1, like P1–P3. It is **unproven**; see §3 C1.
- **A3 (strengthened, from Crucible v2): procedures that keep one convention.** All are CPU or human cost only.
  - A **per-case convention monitor** on every wave: team-union Dice against the ICX lumen and against the Girder mask, plus calibre. More than 10 % of a wave in the wrong convention halts the wave for re-instruction.
  - **Seed tagging** (`seed=girder` / `seed=icx`). Cases in the minority convention are excluded from training and from the sealed test until redone.
  - **Single-convention sealed test.** Every sealed case passes the monitor before it is frozen.

  Crucible's randomised 20/20 seed trial is **recommended, not binding**, because running it is a labelling-lead decision (§5).
- **A4 (revised, accepting Atlas v2's measured form).**
  - Voxel `ignore` applies only to near voxels where proxy and labeller disagree (median 0.26 %, all within 10 mm of the carina).
  - Cases with a wholesale disagreement (ostium > 5 mm, LM Dice < 0.5, or LAD↔LCx swap > 5 %) are **excluded until reviewed**, not masked.
  - If D0 chooses the **trunk** side-branch convention, the trunk-mode comparison must be implemented and re-measured before R1 uses it. Atlas did not run it.
- **A5, A6: unchanged.**

**New amendments**

- **A7 (from Bridge v2): rule renaming as a naming competitor.** Atlas v2's P3 is binding, with Bridge's adoption rule: ship R only if the paired tF1 CI excludes 0 in its favour *and* its swap rate is no higher. Two additions:
  - val and test inference **save softmax** (`--save_probabilities`), so Bridge's hybrid decoding H can be scored at zero GPU cost;
  - H enters as candidate P3b. It is **unmeasured** and gets no prior weight.
- **A8 (from Bridge v2): the ramus is a switch.** The ramus intermedius rule is a namer switch set from D0's written rule, before any naming comparison is scored.
- **A9: no comparison may mix ostium definitions.** Every number in the vault so far uses the `thick` heuristic or ad-hoc crops. From R1 on, only the ported `src/segtrain` tF1 (A1 ostium, regression-tested on E3) may decide anything. Re-implementations (Crucible's `r2_eval.py`) are provisional.

**Not adopted this round**

- Delta's A5 "distal-gap sampling" arm. It is unmeasured, and its trigger (residual long gaps on R1) does not yet exist. Delta may re-propose it with R1 val evidence.
- Crucible's 14-class head, marginal loss and self-training, which Crucible has itself withdrawn.

## 2. Scorecards

Scores are out of 5.

### Atlas v2: winner (amended)

| | Score | Notes |
|---|---|---|
| (a) Reasoning | 4.5 | It integrates the amendments without contradiction. Preparing both label conventions now means D0 costs no compute. Excluding failed cases rather than ignore-masking them is correct reasoning: masking 70 % of a case while keeping it in the sampler wastes the case. Dropping the binary-init ablation is correctly argued: under A it is the wrong convention, and under B it is already the label extent. |
| (b) Evidence | 4 | New notes check out against the plan. Proxy QA: 0.26 % ignored, 100 % within 10 mm of the carina, 18/172 flagged. Thin round trip: tF1@0 ≥ 0.995 at 0.5 mm; at 0.8 mm, 5/10 cases fall below 0.99. FLOPs: 69 TFLOP per step, 17.2 EFLOP, 27–85 h. Citations are verified verbatim. Three caveats: (i) the fallback claim (XL 192 × 256 × 256 "holds left tree 93 %, whole tree 92 % of 153 cases") **appears in no experiment note**, so it is an assertion until added; (ii) the thin round trip covers 10 deliberately hardest cases and only the target level, so the network question is still A1's; (iii) the loader timings come from one CT on a contended 4-core VM, an order of magnitude only, as the note says. |
| (c) Fit | 4.5 | Fits 1 × H100 and 24 h links. R0 fits a 2 h `debugjob`. Its P1 audit and gate order were defective (Delta), and A2 now fixes them. |
| (d) Risk/cost | 4 | 220–470 H100-h. The main open risk is loader saturation at 256³, which only R0 can settle. |

**Verdict:** keeps the title.

### Bridge v2

| | Score | Notes |
|---|---|---|
| (a) Reasoning | 4 | It correctly narrowed v1 to the defensible claim: naming a predicted tree is cheap, so test whether rules out-name the network on its own mask. The oracle arm is a valid **upper bound on naming at a fixed lumen**. It is not an upper bound on a direct model, whose lumen may be better: a 128 mm patch and multiclass supervision could change it. Bridge states this limit. |
| (b) Evidence | 4 | This is the first end-to-end measurement. The numbers match the note: 0.881 vs 0.918 overall, and with the ramus excluded −0.007 [−0.011, −0.004], the same on the 13 never-seen cases; naming bridges took c0675 from 0.215 to 0.765. Caveats: (i) the headline "0.007" excludes ramus voxels; the honest current figure is **−0.037** until the ramus rule is written; (ii) **pending/unfinished**: c0041 and c0907 were not run, and the thin-lumen ceiling (0.990) covers only 63 of 160 cases, interrupted, so treat it as provisional; (iii) shared confounds with Delta's E8: one small-patch binary model, tile step 0.75, a crop to the reference bbox + 10 mm that hides distant false positives, and the `thick` ostium, which misses c0526-right by 41 mm (c0526 is in this sample, though it affects both arms alike); (iv) H and the aorta-preferred ostium are unmeasured. |
| (c) Fit | 4.5 | Zero GPU, convention-agnostic, slots in after A2. |
| (d) Risk/cost | 4.5 | About 2 CPU-minutes per case. One wrong naming join (c0407, −0.021). |

**Verdict:** its contribution is adopted (A7, A8). It cannot win the plan, because its plan *is* the master plus a post-hoc comparison. It wins the naming step outright if R beats D on val.

### Crucible v2

| | Score | Notes |
|---|---|---|
| (a) Reasoning | 4 | It correctly identifies the convention as the largest lever still open, and sets out procedures that make a mixed state detectable early. It honestly withdrew its unmeasured recipe parts. The claim that the mismatch "is larger than any recipe effect" is true as a scale statement. It is not a quality verdict, and the note itself says so (implication 3). |
| (b) Evidence | 3 | **0.806 tF1 for a perfect thick proxy against a thin reference** (10 cases): the precision loss, 0.764, is on branches the expert did not trace. It is consistent with Bridge's and Delta's convention notes. Weaknesses: (i) one direction only; **the reverse scoring is pending**, so the "−0.19 either way" in the §2.1 table and the "about 0.19 noise" for mixtures are **extrapolations**; (ii) it uses a re-implemented tF1 on crops with the `thick` ostium (c0526 is again in the sample); (iii) the proxy omits the geodesic step; (iv) **the thin/thick/14-class CPU training arm is unfinished**: the first inference pass was invalidated by an InstanceNorm tiling bug, re-inference is running, and nothing from it may be cited. Its 28 mm patch also makes it weak evidence on cuts even once it finishes. |
| (c) Fit | 4 | Adds no GPU cost and fits the master directly. |
| (d) Risk/cost | 4.5 | The cost is human: re-seeding half a day, plus logging. |

**Verdict:** its procedures become A3. As a plan it offers nothing separate.

### Delta v2

| | Score | Notes |
|---|---|---|
| (a) Reasoning | 4.5 | It retracted its own v1 overclaim on measurement. It found that bridging both hides FPs from the gate and evades Atlas's audit; that is a real logical defect in the master, correctly diagnosed. Re-looking before bridging is a principled answer: the 3 mm joins cannot be told apart by size (FP orphans were 104–1052 voxels, true ones 396–3999). |
| (b) Evidence | 3.5 | **Bridging:** an implemented step on 17 cases with a full audit. Solid, and it overturns Round 1 reliance. **Ostium:** 116 trees against an independent truth source. Solid, though the aorta rule was tested on only 5 cases and agrees with that truth partly by construction; there are no absent-LM cases. **Re-inference** (0.829 → 0.854, CI [0.000, 0.057], no case worse) is weak for four reasons: (i) **confounded by tile step 0.75** against nnU-Net's default 0.5, and the control is **unfinished**; (ii) the gain sits in 3 of 16 cases; (iii) the window was 96 × 160 × 160, and under the master's 256³ patch a "gap-centred window" is close to a shifted tile, so the gain may shrink or vanish; (iv) oracle names. **The support rule is a proposal, not a measurement.** |
| (c) Fit | 4.5 | Same model. Post-processing only. |
| (d) Risk/cost | 4 | Seconds per case on a GPU. The A5 arm is about 11 h and unmeasured. |

**Verdict:** the most consequential correction this round (A1, A2 revised). It does not win, for the same structural reason as Bridge: its plan is the master with a different post-processing block.

## 3. Contested facts and confounds

**C1. Does bridging repair cut trees?** **Accept Delta v2 over Delta v1:** an implemented step beats a metric tolerance. Bridging alone adds +0.01, half the joins are FP, and the gate is gamed. Re-inference + bridging is **unproven**:
- the control at tile step 0.5 is unfinished;
- the CI touches 0;
- the evidence comes from a small-patch model.

If the tile-step-0.5 control matches re-inference, the right recipe is simply nnU-Net's default overlap and P1′ should be dropped. That must be settled before P1′ is judged on R1.

**C2. Naming bridges (Bridge, 4 mm) vs FP joins (Delta, 3 mm).** These do not contradict each other. Bridge's joins edit only the naming graph, so tF1 connectivity is untouched. Delta's joins edit voxels, so tF1 is affected. Both results stand. Bridge's single wrong join (c0407) is the naming analogue of Delta's FP joins. If R is adopted, its joins go into the same audit.

**C3. How common are cut trees?** Every real-prediction number in the vault (Delta E8 and E10, Bridge's E2E) shares one model, one fold, a 48 × 56 × 56 mm patch, tile step 0.75, no TTA, a crop to the reference box, and the thin convention. That is one confound set, not independent replication. **The master's real cut rate is unknown until R1.**

**C4. Ostium definition across notes.** Bridge's E2E, Crucible's 0.19 and Atlas's thin round trip all use the `thick` heuristic. Delta shows it fails on c0526-right (41 mm), and c0526 appears in Bridge's and Crucible's samples. In Bridge's paired design and Atlas's round trip it cancels between arms. In Crucible's single-arm absolute number it may bias the figure slightly. Hence A9.

**C5. The size of the convention cost.** Accept 0.806 one-way on 10 cases. Treat the reverse direction and the "mixture" figure as unknown.

## 4. What would change the ruling

**Atlas (to keep the title):**
1. Put the fallback-configuration extent figures (93 % / 92 %) in a note, or delete them.
2. Run R0 and replace the 27–85 h forecast and the loader estimate with measurements.
3. Implement A2 as revised: gate before repair, Delta's audit.
4. If D0 picks trunk, implement and measure trunk-mode A4.
5. On R1 val, report D vs R vs H and P1/P1′ under the A9 metric, as pre-registered.

**Bridge:** No CPU-side result can now displace the master. The next decisive fact is the R vs D comparison on R1's val fold. Before R1:
- finish the 160-case thin ceiling and c0041/c0907;
- re-score with the ramus switch set to D0's rule, quoting the all-classes figure, not the ramus-excluded one;
- measure the aorta-preferred ostium.

**Crucible:**
1. Finish the reverse-direction scoring (a perfect thin model against a thick reference). Without it, the price list D0 receives is half empty.
2. Re-run the thin/thick arm with valid inference, and report it as cut/recall differences only, as it says.
3. Re-score with the ported tF1.

**Delta:**
1. Finish the tile-step 0.5 control on the cut cases. This decides whether P1′ exists.
2. Measure the support rule (joins kept vs blocked, against the reference).
3. Run TotalSegmentator on more than 5 cases and include an absent-LM case in the ostium validation.

## 5. Decisions that belong to humans

Carried over from Round 1 §5, all still open:

1. **D0 lumen convention** (expert lumen vs Girder seed). The decision now comes with a measured one-way price: 0.19 tF1 for a perfect model trained in the wrong convention. The decision remains clinical and project-level.
2. **Side-branch convention and the ramus rule.** The ramus moves tF1 by up to 0.15 in a case and is present in 9 of 19 sampled cases, so it is the biggest naming lever.
3. **Labelling order** (sealed test first) and double reads.
4. **The tF1 tolerance**, which the clinical lead may change once.
5. **Whether 4-class seeds are shown to annotators.** Running Crucible's randomised 20/20 seed trial to inform this is the labelling lead's call.

New:

6. **Whether cases already labelled from Girder seeds are redone or kept**, if option A is chosen. This is a labour cost the project must accept.
