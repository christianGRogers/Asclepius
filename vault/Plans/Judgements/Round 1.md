---
tags: [plans, judgement]
round: 1
updated: 2026-10-04
---

# Round 1 ruling

## 1. Master plan: **Atlas v1**, adopted with these binding changes

Atlas v1 wins. Two other candidates (Crucible, Delta) adopt its training recipe wholesale, having checked its measurements. The recipe rests on the most direct evidence in the vault: the planner run on the real 1000-case fingerprint, the spectrum and label round trip at 0.5 mm, the patch-extent analysis that models nnU-Net's real sampling, and the CT-window defect. It has the most complete schedule and the most complete plan for using labels as they arrive. Its weaknesses are real, and each one is fixed by an evidenced part of a losing plan:

- **A1 (from Delta v1): change the deciding metric.** Every decision is made on **macro tree-F1 @ 1.5 mm** (Delta §3). That metric is per-class centreline F1 in which recall counts only centreline that is correctly named *and* connected to the ostium. It is gated by **false-positive components per case** (acceptance ≤ 1 on average). Per-class clDice, Dice, HD95, β₀ against the reference's own count, branch-swap rate and LM length error are reported alongside it. Two conditions:
  - Before the sealed test is scored, the ostium must be defined by contact with the aorta (TotalSegmentator, ≤ 5 mm), not by the thickest-endpoint heuristic.
  - The 1.5 mm tolerance is fixed now. Only the clinical lead may change it, and only once, before sealed-test scoring.

  Atlas's ablation rule stays as written (paired bootstrap CI excluding 0), applied to tF1.
- **A2 (from Delta v1): add post-processing as a switchable, judged step.** Add Delta's geometric gap bridging (≤ 3 mm, pieces ≥ 100 voxels joined to the component that carries the ostium) and Delta's label repair (`postproc.py`, with its regression test: correct labels unchanged, islands repaired, carina no worse). Both are judged on the val fold by tF1 on the first real 4-class predictions. Neither is on by default until then. Never delete a component ≥ 100 voxels; never force left and right apart. Atlas's A4 (Skeleton Recall) is compared **after** this post-processing, as Delta specifies.
- **A3 (from Crucible v1): escalate the lumen convention to humans before R1.** R0, preprocessing and the proxy factory run now. R1 waits at most one week for the human decision in §5. If that decision is "expert lumen" (Crucible option A), the R1 training target becomes the ImageCAS-X lumen with ImageCAS-X names (Crucible §2.3, 4-class read-out). If it is "keep the Girder seed", or no decision arrives, R1 trains on Atlas's projected proxy. Either way, the side-branch convention (territory vs trunk) and the ramus rule are requested in writing in the same meeting. Atlas's pre-registered check on the first 20 team labels stays as the empirical backstop.
- **A4 (from Bridge v1 and Crucible v1): use the rule-based namer as QA.** Run Bridge's frozen v3 labeller (with 4 mm bridging) on every proxy label, every team label and every val prediction. Disagreement on the LM, the ostium or the LAD/LCx split flags the case for human review. Where the labeller and the projected proxy disagree on a voxel, that voxel is set to nnU-Net's `ignore` label in the proxy. This is cheap (CPU), and both the labeller's measured accuracy (95 % of held-out cases fully right) and the projection's known weak spot (nearest-voxel naming at crossings) justify it.
- **A5 (from Delta v1): add a calibre trigger.** On the first 20 team labels, re-run Delta's calibre measurement (E7): the fraction of centreline in lumen < 4 voxels across. If the team draws thin (as under option A, where this fraction is 65 % on ImageCAS-X), the spacing ablation A1 (native vs 0.5 mm) becomes **mandatory** and is judged by tF1, not optional.
- **A6: run R0 before any other GPU job.** Every GPU-hour figure in every plan is extrapolated. R0 must log peak VRAM, s/epoch and loader saturation for ResEnc at 60 GB, 0.5 mm iso, 256³. If the 256³ patch does not fit, use Atlas's documented fallback (40 GB, 192 × 256 × 256).

## 2. Scorecards

Scores are out of 5.

### Atlas v1: winner (amended)

| | Score | Notes |
|---|---|---|
| (a) Reasoning | 4.5 | The argument for a single direct model is sound. With labels available on day 0 (ImageCAS-X names), a second stage buys only whole-tree context, and Atlas measures that context directly. It correctly identifies the CT-window defect and the absence of early stopping. Its argument for training on the thick masks ("the team will partition them") is correct under the status quo, but it never asks whether the status quo should hold. That is Crucible's point, and Atlas misses it. |
| (b) Evidence | 4 | Spot-checked quotes agree with their notes. Window: [65, 688] HU and 37.8 % flattened. Patch: 98 % / 97 % / 7 % / 61 %. Spectrum: noise floor in 12/12 CTs. Round-trip Dice at 0.5 mm: ≥ 0.985. Three small inaccuracies: (i) "0.83–0.94 at 0.8 mm" mixes per-class minima (0.83) with means (0.91–0.94); (ii) "≥ 92 %" vs the note's "≥ 93 %" (256/277 = 92.4 %, so the plan's figure is the right one); (iii) the ResEnc gains, the TopCoW mirroring quote and the Gottlich plateau are cited with identifiers but no vault note verifies them. None of these is load-bearing for the ruling. The 40–60 H100-h estimate is openly labelled as an extrapolation. Weaknesses: the patch analysis used thin ImageCAS-X trunk trees (Delta's survey of our thicker masks puts p95 extent at 127 × 110 × 104 mm, still inside 128³). The resolution result measures image content, not network accuracy, as Atlas itself concedes, and A1 is the test. |
| (c) Fit | 4 | Fits 1 × H100 and 24 h links. Starts on day 0. Clear policy as labels arrive. Sealed test drawn first. The decisive metric was blind to cut trees; A1 above fixes this. |
| (d) Risk/cost | 4 | 240–460 H100-h, ~120 of them before any team label exists. Main risks: (1) training on the convention the humans may abandon (fixed by A3); (2) proxy mis-naming at crossings (fixed by A4). |

**Verdict:** the best-evidenced and most complete recipe. It wins with the amendments above.

### Bridge v1

| | Score | Notes |
|---|---|---|
| (a) Reasoning | 3 | The factorisation (vessel vs name) is elegant, and the observation that naming is a handful of discrete decisions per tree is well supported. But the central argument for two stages (a patch cannot see the bifurcation) is refuted at the patch size the other plans use (see §3, C1). Two-stage error compounding is real: real gaps > 4 mm orphan subtrees (Delta E8), and Bridge's own note shows naming collapses with unbridged breaks. |
| (b) Evidence | 4 | The best-run experiment programme this round: frozen code, md5-pinned, a held-out set, iteration history disclosed (the v1 drop from 96 % to 79 % is reported), and an honest negative (the generic learner). The quoted numbers match the notes: 98.9 % pooled, 94.9 %, swap rate 3.4 %, ostium 0.983, 0.929 from 5 cases. Caveats: the "98.9 % pooled voxel agreement" counts only the ~85 % of our voxels within 2 mm of an ImageCAS-X vessel. The truth is ImageCAS-X names projected onto our masks, so the labeller's naming is scored against a labelling that shares its nearest-skeleton logic. All results are on **reference** masks. Robustness to stage 1 rests on simulated, uniformly placed 2 mm breaks; the note itself admits real breaks cluster and can be longer. There is no end-to-end number at all. |
| (c) Fit | 2.5 | Stage 1 trains on the Girder masks, which Crucible shows are 47 % non-contrast tissue. Under option A that target is wrong; under option B it is right. The deciding metric (mean per-class Dice) is dominated by the lumen convention (Delta E7: two references of the same vessels agree at Dice 0.42) and blind to cuts (E3). |
| (d) Risk/cost | 2 | ≈ 790 H100-h (360 for stage 1, 430 for the comparator), roughly double the others, and it pays for a full direct-model arm as falsification. Its pre-registered abandonment rule is commendable. |

**Verdict:** loses as the segmentation route. Its labeller is adopted as QA and proxy filter (A4) and is the best naming evidence in the vault.

### Crucible v1

| | Score | Notes |
|---|---|---|
| (a) Reasoning | 4 | Found the most consequential fact of the round: the binary masks are the original ImageCAS labels, and most of their volume is not contrast lumen. It reasoned correctly that the training target and the evaluation reference must share one convention, and it offers both branches (A/B). It honestly narrowed its own thesis: SSL machinery dropped, self-training kept only for the 200 cases nobody has labelled. |
| (b) Evidence | 4 | The numbers check out. Dice 0.412 reproduces the paper's 41.8. Ratio 3.58×. 29.2 + 17.9 = 47.1 % of mask voxels at median 16–38 HU. Side branches 26.6 %. Rule namer: LM failures in 23/61 cases on Girder masks. HU rule: 0.779. The ImageCAS-X identity and mapping were reproduced independently by Bridge and Atlas. But its distinctive *training* choices (14-class output, marginal loss, M2 self-training on quality-0 scans) have no experiment behind them, only citations. The annotation-time benefit is explicitly unmeasured. "Not lumen" for the 27 % shell is HU-inferred, and partial volume is plausible there (shell median 116 HU), as its own limits note says. |
| (c) Fit | 3 | Its recommended route (option A) depends on a project decision outside the tournament's remit, namely re-seeding SegQueue. "Weakly dominates Atlas" overstates the case. In world B, M1 (~50 H100-h on a thin, 14-class target) is not Atlas's model and must be retrained. Under option A the label convention is thin: 65 % of centreline sits in lumen < 4 voxels across, and the one model trained on it cuts 3 of 8 test trees (Delta E8). Crucible decides on per-class clDice, which scored those cut trees at 0.88–0.94. |
| (d) Risk/cost | 3.5 | 280–480 H100-h. The 14-class head adds Dice instability for rare classes (L-PDA in 5 % of cases), which it acknowledges. Its seeds from M1 for the 200 non-ICX cases carry the same anchoring risk it warns about. |

**Verdict:** right about the data, not yet right about the recipe. Its convention finding becomes amendment A3 and §5.

### Delta v1

| | Score | Notes |
|---|---|---|
| (a) Reasoning | 4.5 | The clearest first-principles argument of the round. Downstream uses walk the tree from the ostium, so a cut tree is the catastrophic failure, and the deciding metric must see it. It concedes, on its own data, that most missed centreline is distal truncation (70 %) and that topology losses do not connect trees. It dropped its localiser on measurement (E1). |
| (b) Evidence | 3.5 | E3 (5 cases, simulated) and E8 (8 real cases) support the metric argument. E3: five proximal breaks give Dice 0.971, per-class clDice 0.972 and rooted recall 0.301. E8: c0675 has per-class clDice 0.880 with rooted recall 0.535, against c0750 at 0.910 and 0.917. The quotes match. **Overstatement:** §1 says bridging raises "rooted recall 0.78 → 0.91 on real output". The E8 note says those rows are *gap-tolerant metrics*, "not an implemented bridging step", and come "before any extra false connections it might make". That is an upper bound, not a measured repair. Evidence base for E8: one fold of a *binary*, small-patch (48 × 56 × 56 mm) model on the thin convention. It is the weakest context of any proposal, and Delta acknowledges it. Spearman figures on 8 cases are fragile. Label repair (98.5 % of islands fixed) is measured on simulated islands only. tF1's ostium definition is still a heuristic. |
| (c) Fit | 4 | Its recipe is Atlas's, so it fits equally. Its schedule drops Atlas's window and rotation ablations and makes the spacing ablation conditional. That is cheaper, but it leaves Atlas's measured-but-unablated choices unverified. |
| (d) Risk/cost | 4 | 170–370 H100-h, the cheapest. The tF1 harness must be ported (≈ 1 day), and bridging still has to be built (≈ 1 day). |

**Verdict:** the plan contributes no new training recipe; its contribution is the yardstick and a safe repair. Both are imported (A1, A2, A5). It loses only because its own recipe is Atlas's with fewer checks.

## 3. Contested facts

**C1. Can a patch see the bifurcation? (Bridge 0.47–0.56 vs Atlas 0.97)** **Accept Atlas.** The two numbers answer different questions. Bridge assumes a patch is placed uniformly among all positions containing the voxel, with no image bounds; its own note calls this "idealised". Atlas models nnU-Net's `get_bbox` centring for forced-foreground patches and clamps to the image. The images are only 83–138 mm tall, so a 128 mm patch spans nearly the whole height. Atlas also reports random-patch class presence (LM in 0.985 of patches). Atlas's method is sounder for the question that matters, which is what the network sees in training. Bridge's concern remains valid for the shipped presets (7 % / 61 %), which nobody proposes to use. Residual caveat: containing the LM is necessary, not sufficient (Atlas's own limit). Branch-swap rate on val is the check.

**C2. Are the Girder masks the lumen? (Crucible vs Atlas/Bridge/Delta)** There is no dispute on the measurement. Four independent estimates agree: ratio 3.3–3.6×, Dice 0.41–0.43, about 90 % of ImageCAS-X centreline inside our mask. Atlas's window note independently finds per-case median HU of 44–161 inside our masks. **I accept Crucible's characterisation:** most of the excess is non-contrast tissue. The dispute is normative (which convention the project should label), and that belongs to humans (§5).

**C3. Deciding metric (Dice / per-class clDice / tF1).** **Accept Delta.** E7 shows Dice scores the lumen convention, not the tree (0.42 between references of the same vessels). E3 shows both Dice and per-class clDice rank a tree cut at the LM above one missing 30 % of distal branches. On label errors, tF1 equals per-class clDice exactly (E3), so Atlas and Crucible lose nothing by adopting it. Its blind spot (false-positive blobs) is covered by the FP gate. The E8 sample is small, but the argument is mainly definitional: a metric that does not condition on connectivity cannot see disconnection.

**C4. How long are real gaps? (Bridge's 4 mm graph bridging vs Delta's real gaps)** **Accept Delta's E8 as the better estimate of real gaps**: 22 interior gaps, 17 of them ≤ 4 mm, but the 5 longer ones carry most of the disconnected length. Bridge's breaks are simulated at a uniform 2 mm. E8 is pessimistic: thin convention, small patch, binary model. It must be re-measured on the master's first val predictions.

**C5. Does resampling destroy thin vessels? (Training plan vs Atlas)** **Accept Atlas at 0.5 mm** for image content and labels. The network-level effect is unmeasured. A1 tests it, and amendment A5 makes A1 mandatory if the labels are thin.

**C6. Early stopping in nnU-Net v2.** Atlas (source check, v2.8.1) is accepted over the vault's schedule note. Crucible and Delta concur.

**Verified outside the vault:** `src/segqueue/protocol.py` states that the seed is loaded "so the annotator splits a tree rather than drawing one". This supports the premise shared by Atlas, Bridge and Delta that team labels will partition the seed. That edits are *confined* to the seed rests on `slicer/` and `docs/` files, which I did not read. Three advocates cite them consistently.

## 4. What would change the ruling

**Atlas (to keep the title):**
1. Show that the projected proxy is close to the team's convention. On the first 20 team labels, report macro tF1 and branch-swap rate of each proxy variant against the team labels, including bifurcation-localised error.
2. Report R0's measured VRAM and s/epoch, and replace the 40–60 h extrapolation with the measured figure.
3. Report R1's branch-swap rate and tF1 on val, with and without A2 post-processing. Swaps along long vessels would revive Bridge's argument.
4. If the humans choose option A, show that 0.5 mm iso does not cost connectivity on the thin convention (A1 judged by tF1).

**Bridge:** One number is missing: an **end-to-end** result. Name real stage-1 predictions (or the released ImageCAS-X nnU-Net output Delta already ran on 8 cases), score them by tF1 against the same direct-model baseline, and show the two-stage route is not worse on swaps or cuts. Second, address the lumen convention: stage 1 cannot train on Girder masks if the project chooses option A. Third, bring the cost down: the comparator arm should share the master's runs, not duplicate them.

**Crucible:** If the humans choose option A, the label-target question is settled in Crucible's favour, which A3 already provides. To win outright, Crucible must show that its distinctive choices pay. The 14-class head with summed read-out must be no worse on 4-class tF1 (its own A1). Its thin-convention model must not cut trees at E8's rate under the 128 mm patch and A2 post-processing. And a measured annotator-time or agreement benefit from re-seeding (its own proposed randomised 20/20 test) would turn an argument into evidence.

**Delta:** Delta's ideas are already in the master. To win the plan itself, Delta needs recipe-level evidence that the master lacks: an **implemented** bridging step evaluated on real 4-class predictions (not a gap-tolerant metric), including the false connections it creates. It also needs tF1 validated with the aorta-contact ostium on ≥ 30 cases, ideally with evidence that tF1 tracks a downstream task (e.g. CPR or FFR feasibility) better than per-class clDice.

## 5. Decisions that belong to humans

1. **Lumen convention and the SegQueue seed (urgent, before R1 and before much more labelling).** Should the team split the Girder masks (thick, ~47 % non-contrast tissue by HU) or draw the expert lumen (re-seed with ImageCAS-X lumen for 800 cases and model output for 200)? The goal says "lumen only". The tournament has measured what each option means, but choosing is a clinical and project call that depends on downstream use (stenosis, plaque, FFR vs. visualisation) and on annotator cost. Whichever is chosen, it must be written down before more team labels accumulate, so that the labels are not a mix of the two.
2. **Side-branch convention (territory vs trunk) and the ramus intermedius rule.** This moves 25–36 % of each left-tree class's voxels. It is a protocol decision, and the protocol hints do not answer it.
3. **Labelling order.** Request the 100-case sealed test first (80 ImageCAS-X test + 20 image-quality-0), plus 20–30 double reads for the inter-rater ceiling.
4. **The tF1 gap tolerance (1.5 mm) and the acceptance thresholds.** The clinical lead may change them once, before sealed-test scoring.
5. **Whether model predictions or ImageCAS-X-derived 4-class maps may be shown to annotators as seeds.** Anchoring bias is a cost; speed is the benefit. Decide with Crucible's randomised time measurement if possible.
