---
tags: [plans, judgement]
round: 3
updated: 2026-10-08
---

# Round 3 ruling

## 1. Master plan: **Atlas v3**, adopted with these binding changes

Atlas v3 keeps the title. It is the only candidate that states the full recipe and conforms to every one of [[Human decisions]] D0–D5:

- the split ImageCAS mask is target, seed and reference;
- the territory rule;
- ramus → LCx;
- two reads per case;
- tF1 tolerance 1.5 mm.

Its new evidence also closes Round 2's open asks. The fallback patch is measured (93.5 % / 91.5 %, LM visible to 85 % of LAD-centred patches). A calibrated memory model (≈ 54 GB) and nnU-Net's own loader cost (10.3 CPU-s per batch) bound R0. And R0 is prepared as a real job.

All three challengers again keep the master's model. They contribute on the new open question, two reads per case, and on post-processing. Crucible v4 disagrees with the master substantively on the acceptance rule and on the fusion default, and wins the first of these (A10).

### Revised Round 1–2 amendments

**A1 (extended): ostium per tree component.** The cross-checked ostium rules run per tree component, so absent-LM cases (≈ 3 %) get two left ostia. Evidence: 9/9 ostia within 1.4 mm in the three absent-LM cases (Delta v3 §2). Only 3 such cases have been checked, and the 68-case per-component re-run is pending, so this is adopted as a procedure, not as a validated number.

**A2 (revised): post-processing.**
- The **support rule is withdrawn.** Measured, it kept all 4 FP joins and blocked 2 true ones, and it cost c0407 0.938 → 0.806.
- **P1′ (gap-centred re-inference + 3 mm bridging) stays a candidate**, judged only against nnU-Net's default inference at tile step 0.5. The tile-step confound from Round 2 is answered for the 4 cut cases: default overlap +0.003, P1′ +0.103. "Never worse" is withdrawn (c0526 −0.008).
- P1′ remains **unproven on the master**. The evidence is n = 4, a binary small-patch model, the thin convention and oracle names.
- The raw-prediction FP gate and Delta's bridge audit remain binding.

**A3 (direction reversed by D0).** The convention monitor flags reads drawn **thin**: union Dice against the ImageCAS mask < 0.9, or calibre nearer ImageCAS-X than the mask. A wave halts if more than 10 % of its reads are flagged. Crucible's seed trial is withdrawn (D4). Seed tagging is kept, though trivial now that every case is `seed=girder`. ImageCAS-X is a secondary, never-decisive cross-check, and the 0.19 / 0.25 convention cost applies only there.

**A4 (revised).**
- Trunk mode is withdrawn (D1).
- The A4 QA must be re-run with the namer's ramus switch at LCx before R1. Atlas lists this as pending.
- **A ramus-only disagreement between proxy and namer never excludes a case.** The namer cannot separate a ramus from an early diagonal by geometry (9 caught, 3 diagonals mislabelled; Bridge, "88 percent" note), so a ramus-only flag would exclude good proxy cases.

**A5: unchanged.** The calibre trigger is expected to stay off under D0.

**A6: unchanged, with one consequence.** **The Atlas Trillium run goes first.** The Bridge and Delta runs each train a model, and none may precede R0 (see A13).

**A7 (re-quoted).** R and H use ramus → LCx. Every plan must cite the namer's accuracy under D1b: **88.2 % of 76 held-out cases fully right, swaps 7.9 %**. The Round 1 figure of 94.9 % is superseded. The A7 adoption rule is unchanged.

**A8: settled.** The ramus switch is set to LCx (D1b).

**A9: unchanged.** All four Trillium runs score tF1 with a provisional ostium (`thick`, the blood pool, or reference-derived). Their **paired** differences are usable, and their absolute tF1 values are provisional.

### New amendments

**A10 (from Crucible v4): acceptance and scoring.**
- **Scoring.** The decisive per-case score is the **mean tF1 against each read**. All four plans now agree on this. No fused reference is built for decisive scoring. This corrects Atlas v3's §2.7 "sealed test fused … frozen", which contradicts its own §3.
- **Adjudicated cases.** The read whose decision was overruled is replaced in scoring by the adjudicator's read.
- **Acceptance.** Replace "≥ inter-rater − 5 points". Per class on the sealed test, the model's mean-against-reads tF1 must be **non-inferior to the inter-read tF1 of the same cases, with margin 0.02**: the lower bound of the paired bootstrap 95 % CI of (model − inter-read) must be > −0.02. The FP gate (≤ 1 per case, raw) and the swap rate (< 5 %) stay.
- **Why** (first principles, independent of Crucible's simulation): "as close to a read as another reader is" is the natural definition of human-level. A −5-point allowance has no derivation. A model trained on many reads averages out idiosyncrasies, so it should *exceed* read-vs-read agreement. The simulation's +0.057 illustrates this, and it is conditional on symmetric, independent errors. Atlas's human-normalised score, difficulty tertiles and annotator QA are kept.

**A11: training on two reads** (judge's synthesis; see §3 C1).
- **Case level.** A third read adjudicates any case that trips Atlas's wholesale triggers (inter-read macro tF1 < 0.80, ostium or LM disagreement > 5 mm, LAD↔LCx swap > 5 %) or Bridge's decision extractor (ostium, LM end, LAD/LCx side, tree identity). A ramus-only disagreement is resolved by D1b, not by a third read. The case stays out of training until adjudicated, and is never voxel-masked.
- **Voxel level, default.** **Each read is a separate training sample.** In both samples, voxels that both reads call vessel but give *different classes* are `ignore`. Voxels where the reads differ in **extent** (one says vessel, the other background) keep each read's own label. This form runs natively in nnU-Net.
- **Pre-registered test (replaces Atlas's A5r).** At the first wave with ≥ 150 double-read training cases, run the A11 default against Atlas's agree-or-ignore (and pure both-as-samples, if budget allows), 250 epochs, paired by tF1 against reads on val. The winner by CI is adopted; **if neither wins, the A11 default stays**.
- **Never** use the voxel intersection with disagreements as background (Delta). Atlas's `ignore` is not an intersection, so this bars only a form nobody proposed as default.

**A12: one wave-1 double-read report.** On the first 50 double-read cases, a single CPU report replaces four separate first-20/50 checks:
- inter-read tF1 per class;
- `ignore` fraction and its location relative to the carina (Atlas);
- the decision-vs-diffuse attribution of naming disagreement (Bridge; the ≥ 80 % expectation is pre-registered);
- components of A∩B vs each read (Delta);
- the refit of Crucible's noise model (carina SD, truncation radius, slip rates), followed by a re-run of `r4_fusion.py`;
- the adjudication rate, and the thin-read flags.

If disagreement turns out diffuse or correlated, A11's case-level rule is revisited before any team read enters training.

**A13: run order and sealed-set hygiene for the Trillium experiments.**
- **Order.** Atlas's run first (R0 gate). It must **save the val softmax (`--npz`) and the final checkpoint**, so that Bridge's D/R/H/O and Delta's inference variants can, at the lead's option, be run against it as inference-only jobs, sparing two ~20 h trainings (§4).
- **Sealed set.** Delta's prepared run evaluates on all 160 ImageCAS-X test cases, and 80 of those are the master's sealed test. **Decisions from that run may use only the 80 non-sealed test cases.** Results on the sealed 80 are not computed, or not looked at.

## 2. Scorecards

Scores are out of 5.

### Atlas v3: winner (amended)

| | Score | Notes |
|---|---|---|
| (a) Reasoning | 4 | Conforms fully. Its fusion logic for names is sound: with two raters there is no majority, so disagreement becomes `ignore` plus adjudication. But it applies the same rule to **extent** disagreement ("one read names it, the other leaves it unlabelled → ignore") without arguing for it. That discards supervision for distal vessels exactly where rooted recall is decided (Crucible's point). The "−5 points" acceptance has no derivation. |
| (b) Evidence | 4 | The new notes check out: fallback 0.935 / 0.915 / LM 0.85; memory 65.7 GiB fp32 unique → ≈ 54 GB after calibration; loader 10.3 CPU-s per batch; planner on real cases 256³ / batch 2; fingerprint window [−165, 658] as predicted. The memory figure rests on one calibration point (ResEnc L, 22.7 GB) and an assumed equal AMP ratio; R0 will settle it. Its fusion argument cites the 0.26 % proxy-vs-namer disagreement as what "two humans splitting one mask are expected to look like". That is an analogy from two automatic namers, not evidence about humans. The ≈ 10 % adjudication estimate is similarly extrapolated (Bridge's stand-in gives 21 %). |
| (c) Fit | 4.5 | Fits 1 × H100 and 24 h links. R0 + short R1 in one 23:50 job. |
| (d) Risk/cost | 4 | 220–470 H100-h + 22 h. The loader margin is thin (≈ 0.47 s supply vs 0.4–1.2 s demand per step). |

**Verdict:** keeps the title. Its acceptance rule and extent-fusion are amended (A10, A11).

### Crucible v4

| | Score | Notes |
|---|---|---|
| (a) Reasoning | 4.5 | It identified the two weakest points in the master's two-read design and argued both from first principles: (1) single-read scoring and "inter-rater − 5" mis-set the bar; (2) agree-or-ignore discards one-sided truncation. It is honest that at the population optimum every fusion is equivalent, so differences are finite-data effects that only training can show. |
| (b) Evidence | 3 | The simulation is internally coherent: optimum 0.953–0.957, truth vs one read 0.922, median-annotator model 0.933, inter-read 0.900, model > inter-read in 20/24 cases. But **every number rests on a hand-built, independent, symmetric error model** with no lumen-boundary jitter other than truncation. LM is under-agreed (0.81 vs ImageCAS-X 0.92). It uses a provisional tF1 (thickest-voxel ostium on T) and 24 cases. "The truth scores below the median annotator against one read" is close to tautological under its error model, but it is a valid warning against single-read scoring. The GPU run is pending (see §4). |
| (c) Fit | 4.5 | Zero extra GPU. Its proposals are nnU-Net-native. |
| (d) Risk/cost | 4 | The main risk is correlated real errors, and it pre-registers the refit that would detect them. |

**Verdict:** its acceptance and scoring rule are adopted (A10). Its fusion default is adopted in part (A11). It does not win, because it carries no recipe of its own.

### Bridge v3

| | Score | Notes |
|---|---|---|
| (a) Reasoning | 4 | Sound: under D1, a case's names are fixed by a few discrete decisions, so a naming disagreement is better adjudicated per decision than masked per voxel. It re-quoted its own numbers downward (0.949 → 0.882) without being asked, and that is creditable. |
| (b) Evidence | 3.5 | The new numbers match the notes. Held-out: 0.882, swaps 7.9 %. E2E with ramus → LCx: −0.010 [−0.016, −0.005] on 21 cases, now with c0041 and c0907. Ceiling over all 160 cases: 0.973. Ostium within 5 mm in 90.7 %. The decision-attribution result (87 %, 99.7 % held-out) uses a **stand-in whose second "read" is a rule namer, which fails as decisions by construction**, as Bridge notes. It says little about diffuse human errors. Disclosure is good: the 3-decision first version and its 68.7 % diffuse share are both reported. The aorta-preferred ostium is still unimplemented. |
| (c) Fit | 4 | Its decision-level adjudication is compatible with D4: the namer's choice is a suggestion, not a seed. Its lumen rule (union for whole branches, `ignore` for thin jitter) needs a branch/jitter classifier nobody has measured. |
| (d) Risk/cost | 4 | Adjudication load is unknown; the stand-in gives 21 %, mostly ramus, which D1b should reduce. |

**Verdict:** its decision extractor is adopted as an adjudication trigger (A11). Its naming competitor stays in A7.

### Delta v3

| | Score | Notes |
|---|---|---|
| (a) Reasoning | 4.5 | It ran the control it was asked for, reported the result even though it is unflattering (c0526 worse; support rule fails), and dropped what failed. It correctly re-reads all its connectivity evidence as thin-convention-specific and predicts cuts will be rarer under D0. The warning against using the intersection is sound. |
| (b) Evidence | 3.5 | The control table matches the note: 0.744 → 0.847 on step 0.5 + P1′, against 0.740 → 0.744 for overlap alone. It covers 4 cut cases only; the 12 uncut cases were not re-run at step 0.5. Same model, same thin reference, same oracle names as before. Absent-LM ostia: 9/9, but only 3 cases. |
| (c) Fit | 4 | Its fusion proposal ("ignore in the class loss only") needs a custom loss, which nnU-Net does not provide. A11 uses the native full `ignore` instead, which costs only proximal vessel supervision at the carina. |
| (d) Risk/cost | 4 | P1′ adds about 2 windows per case. |

**Verdict:** A1 and A2 are revised from its evidence. The pending run is what can settle P1′.

## 3. Contested points

**C1. How to train on two reads.** The positions:
- Atlas: agreement, everything else `ignore`;
- Crucible: both reads as samples;
- Bridge: decision adjudication, union for whole branches, `ignore` for jitter;
- Delta: both reads or soft labels, never intersection, name disagreement ignored in the class loss only.

**No plan has finite-data evidence on real reads, and none can until wave 1.** I decide on first principles.

- **Names and extent are different kinds of disagreement.**
  - A name disagreement inside a vessel both reads keep (the carina band) is a boundary convention. Training on both labels teaches LAD/LCx as interchangeable there. `ignore` is right (Atlas, Bridge, Delta concur).
  - An extent disagreement is mostly one-sided truncation under D4: edits are confined to the mask, so readers can only trim. `ignore` there removes the evidence that the vessel continues. Under both-as-samples the model learns the per-voxel majority (Crucible), and under the averaged scoring of A10 that is the score-optimal target.
- **A whole-subtree name error is a decision.** Masking part of it leaves the rest training on whichever read was kept (Bridge, implication 2). Adjudication is the right tool.

A11 composes these three conclusions. It is a synthesis, **unmeasured**, and the A11 test decides it. Crucible's GPU run should add this hybrid as a sixth arm if it can, at the cost of one code change and one arm's time.

**C2. The acceptance rule.** **Accept Crucible.** "Inter-rater − 5" allows a model to be worse than a second reader by an amount nobody derived. A non-inferiority test against inter-read agreement is the standard construction. The 0.02 margin is Crucible's own, and I accept it as a value judgement that is tight but measurable on 100 sealed cases × 4 classes. I flag that a per-class test on LM (short, low agreement) will have wide CIs. If LM cannot be decided at n = 100, its result is reported, not used as a gate.

**C3. The size of the P1′ gain.** On the 4 cut cases, accept Delta's controlled number (+0.103 over default overlap). Its size on the master is unknown. All four calibration sources share one small-patch binary thin-convention model, and Delta expects cuts to be rarer on thick masks (4 % of centreline below 4 voxels across, against 65 %).

**C4. Whether "FP joins" are false.** Delta now suspects that the re-predicted "FP" orphans are vessels the thin reference never traced. That is plausible: the thick masks carry ~21 % more centreline. It is untested. Bridging's FP audit must be re-read against the thick reference before any P1 or P1′ decision.

## 4. The four pending Trillium experiments

| Run | Question | Decision table | Sound? |
|---|---|---|---|
| **Atlas** R0 + short R1 (256³, 560/80, ~250–450 epochs) | Does the master fit and run? First real 4-class tF1, FP gate, swaps, cuts | VRAM/s-epoch → schedule or levers; loader > 30 % → recipe change; swaps ≥ 5 % → R likely; FP > 1 → window suspects | **Sound, but one row is vague.** "tF1 within a few points of per-class clDice" must be a number: use the existing "clDice − tF1 > 0.10 → many cuts" cut-off symmetrically, i.e. ≤ 0.03 → few cuts. It omits A4 QA (≈ 0.3 % of voxels, 10 % of cases), so its tF1 is not the master's. That is acceptable as a first look. **Must run first** (A6). |
| **Bridge** D/R/H/O (same config, ~19.5 h, 560/80) | Do rules or grammar decoding out-name a real direct model? | The A7 rule; O − D < 0.01 closes the thesis; swaps revive C1 | **Sound and decisive for A7.** **Largely redundant with Atlas's run:** same data, split, configuration and val set. It is best run as CPU/inference-only on Atlas's saved softmax (A13). Run as prepared, it is a second seed. Its result then binds only once confirmed on R1, as it states. |
| **Delta** P1′ / bridging / repair (ResEnc **L** at 0.5 mm, 250 epochs, train 640, test 160, tile steps 0.5 and 0.75) | Cut rate on thick 4-class; P1′ vs default; bridging/support/repair | P1′ on only if CI > 0 and no case worse by > 0.01; bridging removed if FP ≥ true joins; P2 on if CI > 0; cut rate ≤ 1/160 → QA-only | **The table is sound and appropriately strict.** Three defects. (i) **ResEnc L at 0.5 mm is an 80 × 112 × 96 mm patch**: whole tree in 1 patch in fewer cases than 256³, LM context lower. Its cut and swap rates are an *upper* bound for the master, and P1′'s gain may not transfer downward. (ii) **It touches the 80 sealed cases**; A13 fixes this. (iii) Running it on Atlas's checkpoint (inference only) would remove (i) and save ~20 h. |
| **Crucible** two-read fusion (simulated reads, default 3d_fullres 96 × 160 × 160 at native spacing, 200/50, 5 arms, equal steps) | Which training target wins with two reads? | both > single and ≥ others → both; agree/union beat both → fusion with `ignore`; none beats single → second read is for evaluation/QA; single-read bias > 0.03 → never score on one read | **Sound as a conditional experiment, not as a decision.** Its reads come from the same symmetric, independent error model as the CPU simulation, so it can only test finite-data consequences *of that model*. Its result is a prior for the A11 test on real reads, not a replacement for it. The fourth row is already decided by A10. The equal-steps fairness rule is correct. Add the A11 hybrid as an arm if feasible. |

**Together, do they answer the questions that matter?** Mostly.
- **Covered:** R0 feasibility, first real master-class tF1, cut rate, swap rate, the naming competitor, the post-processing competitors, and a first look at fusion.
- **Gaps:**
  1. Nothing measures **real** two-read behaviour. Only wave 1 can (A12).
  2. None uses the A1 aorta-contact ostium, so absolutes are provisional (A9).
  3. The ablations (window, rotation, Skeleton Recall, spacing) are untested. That is correct: they follow R1.
  4. Performance on quality-0 scans is untested, since no labels exist for them.
- **Redundancy:** three of the four runs train a near-master 4-class model on the same proxy. With Atlas's checkpoint and softmax saved (A13), Bridge's and Delta's questions need inference, not training. The lead may run them as prepared; the extra trainings then serve as seed replicates, but cost ~40 H100-h for that.

## 5. What would change the ruling

**Atlas (to keep the title):**
1. Run R0, and report peak VRAM, s/epoch and loader-wait share. If any acceptance fails, apply the pre-registered levers in order.
2. Report short-R1 val tF1, FP gate, swaps and cut count, with the vague row made numeric.
3. Implement A10 and A11 in `fuse_reads.py` and the scorer. Re-run A4 with ramus → LCx under the ramus-only exemption.
4. If the short R1 shows swaps ≥ 5 % or a large cut rate, the title is open to whoever's competitor fixes it (R/H or P1′).

**Crucible:** The fusion question will be settled by the A11 test, not by simulation. Before wave 1, Crucible must:
- show that its conclusions survive a **correlated** error model (both readers stop at the same stenosis, a shared carina bias);
- add boundary jitter beyond truncation;
- run the A11 hybrid in its GPU job.

If real wave-1 errors match its refit model, its default carries more weight.

**Bridge:** The pending D/R/H/O comparison is the whole case. If R or H wins by the A7 rule on a real direct model, and then again on R1, naming becomes Bridge's. For the two-read claim it must show, on wave 1, that human naming disagreement is decision-shaped (≥ 80 %), and it must implement the aorta-preferred ostium.

**Delta:** The pending run, with the A13 fixes, is the whole case for P1′. In addition:
- re-read the bridge audit against the thick reference (C4);
- finish the 68-case per-component ostium run;
- report P1′ on the uncut cases at step 0.5, where "no case worse" must also hold.

## 6. Decisions that belong to humans

D0–D5 are taken and are applied above. Remaining:

1. **The 0.02 non-inferiority margin in A10** is a value judgement about what "human-level" must mean clinically. The tournament proposes it; the clinical lead should confirm or change it once, before sealed-test scoring.
2. **Third-read budget.** The adjudication rate is unknown: 10 % (Atlas) to 21 % (Bridge's stand-in, mostly ramus). The labelling lead must approve a ceiling, e.g. 20 % of cases, and the A12 report will show whether it holds.
3. **Trillium run order and form.** Running Bridge's and Delta's experiments as prepared, or as inference-only on Atlas's checkpoint (A13), is the project lead's call on compute. The ruling's recommendation is Atlas first, then inference-only.
