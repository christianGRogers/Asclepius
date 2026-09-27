---
tags: [review, verification, decision-record]
status: complete
updated: 2026-09-26
slice: Research/Metrics and clinical validation, proposals §2.4, §3.1-§3.3
---

# Review 05 — metrics, acceptance thresholds and clinical validation

Reviewer 5 of 10. Slice: `vault/Research/Metrics and clinical validation/` (15 notes) +
`vault/Research/Class schema/Handover/Acceptance thresholds.md`, read against
`vault/Training method/Training plan.md` "Evaluation" (lines 132–142) and
`vault/Proposed changes to the training plan.md` §2.4, §3.1, §3.2, §3.3.

---

## 1. Verdict

The metric *pool* is right and now properly cited — Metrics Reloaded genuinely licenses demoting Dice for
small-and-noisy classes, clDice for tubes, MASD over HD, NSD for annotation slop, and detection metrics for
variably-present classes; TopCoW is the correct precedent and the notes read its code honestly.
The *numbers attached to that pool are largely wrong or unanchored*: the NSD tolerance programme is
arithmetically self-defeating on this cohort's own published inter-rater distances, the ~0.5 Dice "noise
floor" is ~3.6× too small against a seed variance that is published on this exact dataset and that the vault
missed, and the aggregation claim ("2–5 points") understates the real effect by a factor of 2–5 while
attributing it to the wrong classes.
The five-tier acceptance table is not estimable below Tier 2 and its one hard number (Betti-0 ≤ 1) is
anchored on a differently-defined, differently-scoped quantity that the same table it cites reports correctly
one column over.
The framing problem is worse than the vault states: on the only study that measured both, the two metrics it
proposes to *gate* on move against the clinical endpoint.
Biggest gap: nothing in the pool measures lumen calibre, which is the quantity every downstream task the
vault itself surveyed actually needs; and one citation (clDice → "Moccia et al. 2018, IEEE TMI") is a
composite that does not exist.

---

## 2. Errors found

Ranked by how much the plan changes. Arithmetic shown where it carries the argument.

### 2.1 The per-class NSD tolerance programme is self-defeating, and the arithmetic is available today

**Vault says.** `NSD tolerance selection...md:22–28, 58–75`; `Proposed changes...md:311–314` (§3.2);
`Metrics.../Proposed changes.md` E15, M12. The 1.5 mm default is "indefensible" (~4 voxels); derive τ per
class as the 95th percentile of inter-annotator surface distances (Nikolov's method); use one voxel
(≈0.35 mm) meanwhile.

**Actually true.** The premise is right (1.5 mm ≈ 4.3 voxels at 0.35 mm; Metrics Reloaded's τ guidance is
confirmed verbatim — "should be chosen according to inter-rater variability"). Both proposed remedies fail:

*(a) A τ from inter-rater variability is, on this cohort, wider than the vessel.* ImageCAS-X Table 1
(fetched in full, arXiv:2608.30404 HTML) reports **inter-observer ASSD per segment**: LM 0.40, RCA 0.32,
LAD 0.48, LCx 1.85, D1 2.53, **OM1 3.47**, L-PDA 2.82 mm; HD95 per segment 1.41 → 10.14 mm. The 95th
percentile of a distance distribution necessarily exceeds its mean, so τ(OM1) > 3.47 mm ≈ **10 voxels** on a
vessel ~1.5–2.5 mm across. NSD(τ) is then identically 1.0 for any prediction roughly in the right place.
Applied literally to the real numbers, Metrics Reloaded's rule destroys the metric for precisely the classes
it was invoked to rescue. No annotation overlap set is needed to know this — it is in the same table the
vault quotes for the human ceiling.

*(b) One voxel is not "tight", it is more lenient than Dice.* Take the vault's own uniform-dilation model
(`Why Dice misreads...md:34–47`, arithmetic verified). A 3-voxel-diameter tube (r = 1.5) predicted one voxel
too fat: every predicted surface point lies exactly 1 voxel = 0.35 mm from the reference surface, so
**NSD(τ = 0.35 mm) = 1.00** — perfect — while Dice = 2r²/(r²+(r+1)²) = 2(2.25)/(2.25+6.25) = **0.53**. That
same error is a 3 → 5 voxel diameter change, i.e. (5/3)⁴ = **7.7× the Poiseuille resistance**, exactly the
FFR-CT failure `What downstream...md:120–133` says NSD must catch.

*(c) There is no usable dynamic range in between.* At τ → 0, NSD degenerates to a Dice over boundary voxels;
on an r = 1.5 disc (9 voxels per cross-section) only the centre voxel is interior under 6-connected erosion,
so ~8/9 of voxels are surface voxels and surface-Dice ≈ Dice. So the **entire** behaviour of NSD on a
3-voxel tube is spanned by one voxel of tolerance: ≈ Dice at one end, ≡ 1.0 at the other. Worse, surface
distances on a voxel lattice are quantised at {0, 0.35, 0.495, 0.606, 0.70, …} mm, so every τ in
[0.35, 0.49) mm is the *same metric*. A per-class τ table with entries like 0.38 vs 0.45 mm is a
distinction with no effect.

**Fix.** (i) Drop NSD as a gated metric for every class below trunk calibre; keep it for LM/LAD/RCA/LCx
where τ from human ASSD (0.32–1.85 mm) is genuinely smaller than the vessel, and report τ per class.
(ii) Replace it for the thin classes with a **calibre metric** — mean signed and absolute radius error per
centerline point, plus minimum-lumen-diameter error per segment. ImageCAS-X ships centerlines and radii
(§0 of Proposed changes), so this is computable before any annotation. (iii) Reconsider Metrics Reloaded's
*other* boundary branch, **Boundary IoU** (DG7.1: preferable "if contour errors are thought of as crucial
inconsistencies that should be assessed") — which is the branch the project's own FFR-CT rationale selects,
and which appears nowhere in the vault. (iv) Delete E15/M12 as written; the per-class τ table is
unpublishable not because of cross-paper comparability but because it would encode a lattice artefact.

### 2.2 The ~0.5 Dice "noise floor" is wrong, and the seed variance is published on this exact dataset

**Vault says.** `Proposed changes...md:354–359` (§3.4): ResEnc L gained +2.13 (KiTS), +0.77 (AMOS), +0.37 in
an isolated ablation, therefore "a paired difference under ~0.5 Dice is inside the noise";
`Architectures.../nnU-Net still beats...md:113` same. `Deciding whether a paired experiment...md:93–102`
correctly flags that single-run-per-arm cannot separate configuration from seed, but supplies no number and
says seed variance is unmeasured; a grep of the whole vault finds no seed-variance figure anywhere.

**Actually true.** 0.5 is not a noise estimate at all — it is the *low end of published effect sizes*, which
is a different quantity. The real number exists. BCS (Owusu-Ansah et al., STACOM 2026, arXiv:2607.28327),
Table 2, ImageCAS 250-case test set, mean over 3 seeds, caption verbatim:
**"Seed std: ≤0.018 (rates), ≤2.0 (HD95), ≤1.1 (β₀), ≤4.5 pp (FFR)."**
So seed σ on Dice/clDice is up to **1.8 points**, not 0.5 — and the vault already cites this table for
STU-Net's 0.818 (`Handover/Acceptance thresholds.md:55`) without extracting the caption.

Consequences, with arithmetic:
- One run per arm ⇒ σ of the paired difference = √2 × 1.8 = **2.5 Dice points**, larger than *every*
  published ResEnc effect (+2.13, +0.77, +0.37).
- Seed pairs needed at 80 % power: (2.8 × 2.5 / Δ)². For Δ = 2.13 → **11 paired runs**; for Δ = 0.77 →
  **83**. The ResEnc experiment as designed cannot resolve its own expected effect.
- The paired per-case Wilcoxon will nevertheless be significant: with per-case difference SD ≈ 2 points and
  n = 160, minimum detectable difference ≈ 2.8 × 2 / √160 = **0.44 points**. The test measures test-set
  variance and treats seed variance as zero, so it will reliably certify pure seed noise as significant.
- The Tier 1 gate "Betti-0 error ≤ 1" sits **inside** the published β₀ seed std (≤ 1.1).

**Fix.** (i) Measure it: two seeds of the identical binary config on one fold — one extra 24 h job — and
publish σ. (ii) Replace "p < 0.05 vs 0" with a **superiority margin**: require the bootstrap CI lower bound
on the paired difference to exceed the measured seed σ, not 0. (iii) State in §3.4 that mean Dice cannot
settle ResEnc and decide it on the per-class detection/centerline endpoints where effects are larger, or on
cost (ResEnc's 2–4× wall-clock against a 24 h walltime) — and say so rather than presenting a one-run
comparison as decisive.

### 2.3 Aggregation: the gap is 10.4 points, not 2–5, and it comes from the wrong classes

**Vault says.** `Proposed changes...md:305–308` (§3.2) and `Per-class Dice aggregation...md:12, 60`
(E19): macro and micro "differ by 2–5 Dice points on this class distribution, **because** the
dominance-dependent branches appear in under 1 % of cases". `Per-class Dice aggregation...md:79–81`: the
ImageCAS-X "All segments" row (92.8 ± 3.1) "is computed as a macro mean over the 14 segment classes".

**Actually true.** Three errors in one paragraph.

*Prevalence.* ImageCAS-X Table 1 (verified): L-PDA n = **8**/160 = 5.0 %, L-PLA n = **9**/160 = 5.6 %. The
same note's own table (`:32–37`) says 5.0 % and 5.6 %, contradicting its own line 12. "Under 1 %" is wrong
by 5×, and it is repeated in §3.2 of the review document and in the project's framing generally.

*"All segments" is not a macro mean.* Verified per-segment DSCs:
91.9, 92.3, 84.8, 79.9, 82.9, 74.1, 77.7, 80.6, 95.3, 82.6, 83.6, 75.1, 70.9, 81.3 → Σ = 1153.0,
**macro mean = 1153.0 / 14 = 82.36**. The "All segments" row is 92.8 with n = 160 and is the merged /
whole-scan lumen figure (the paper quotes the same 92.8 for "lumen segmentation"). It cannot be a macro
mean over classes; the arithmetic settles it without needing the paper's wording.

*Size and cause of the gap.* Aggregation moves the **human ceiling itself by 10.4 points** (82.4 macro vs
92.8 merged). Micro/volume-weighted sits between: trunks carry most lumen volume, so micro ≈ 0.8 × 92 +
0.2 × 79 ≈ 89 ⇒ macro-vs-micro ≈ **7 points**. And the cause is the seven mid-prevalence side branches, not
the rare ones: dropping L-PDA and L-PLA gives (1153.0 − 75.1 − 70.9)/12 = 1007.0/12 = **83.9**, i.e. those
two classes explain **1.5 of the 10.4 points**.

*Consequence the vault has not drawn.* `Training plan.md:140–141` and Tier 0 calibrate against 82.96 /
89.8 / 92.8 — all **merged binary lumen** numbers. A 14-class macro Dice can never approach them; the human
pair itself only reaches 82.4 on that metric. Any table that puts a multiclass macro mean next to 92.8 is
comparing incommensurable quantities.

**Fix.** Rewrite §3.2's first bullet with the measured numbers (82.4 macro / 92.8 merged / ≈89 micro on the
human reference) and the correct mechanism. State that the merged calibration targets belong only to the
merged view, and report the merged Dice of the multiclass model alongside its macro mean so the comparison
to published work is made on the right object.

### 2.4 Presence percentages in the aggregation note are badly wrong

`Per-class Dice aggregation...md:31` gives "Common side branches (D1, D2, OM1, OM2, IM, R-PDA, R-PLA) |
46–155 | **87.5–98.8 %**". The counts are right; the percentages are not. 43/160 = 26.9 % (IM),
46/160 = 28.8 % (OM2), 91/160 = 56.9 % (D2), 132/160 = 82.5 % (OM1), 155/160 = 96.9 % (D1). True range
**26.9 – 96.9 %**. "Other" is 14/160 = **8.8 %**, rarer than either dominance class in the *previous*
tier. This understates the imbalance by up to 3× and, taken at face value, would move IM and OM2 out of
Tier 3 into Tier 2 (a gated tier) on a false prevalence.

### 2.5 The five-tier table is not estimable below Tier 2, and the numbers have no anchor there

**Vault says.** `Acceptance thresholds...md:138–189`, promoted as "provisionally closable **[reported]**"
in §2.4. Tier 2 gates detection F1 ≥ 0.85 (D1, D2, OM1, R-PDA, R-PLA); Tier 3 gates detection F1 ≥ 0.75
(IM, OM2, Other); Tier 4 (L-PDA, L-PLA) correctly ungated.

**Actually true.** Tier 1's Dice numbers ("within 5 points of the human value") are a stated rule applied to
verified per-class figures — defensible, if arbitrary in the choice of 5. Everything from Tier 2 down is
intuition: 0.85 and 0.75 have no cited origin anywhere in the folder, and the notes do not claim one.
More importantly the tiers are not *estimable*:

- Tier 3 "Other": n = 14. A detection recall point estimate of 0.75 has a 95 % Wilson interval of roughly
  [0.49, 0.90] — the gate cannot distinguish pass from a coin flip.
- Tier 3 IM (n = 43), OM2 (n = 46): 95 % interval half-width on a 0.75 recall ≈ ±0.13. A 0.75 gate is
  decided by ±2 cases.
- Tier 4 is right to be ungated, but the rare classes still enter the headline macro mean, and they
  dominate its variance. Using ImageCAS-X's per-class SDs as the per-case SD proxy, SE(class) = SD/√n:
  L-PDA 29.0/√8 = 10.25, L-PLA 27.2/√9 = 9.07, Other 17.0/√14 = 4.55, OM2 4.29, IM 3.74, … RCA 0.40.
  SE(macro) = √(Σ SE²)/14 = √269.9 / 14 = **1.17 points**, so a **±2.3-point 95 % interval on the headline
  number** — and (105.1 + 82.3)/269.9 = **69 % of that variance comes from the two classes present in 8 and
  9 cases.** The macro mean is not a usable decision variable: its interval is wider than every experiment's
  expected effect and wider than the seed noise in §2.2.

**Also wrong in Tier 0 / Tier 1.**
- Tier 0 has two gates, "ImageCAS original masks ≥ 82.96 %" and "ImageCAS-X labels ≥ 89.8 % (reproduce their
  nnU-Net)", without saying which training set each belongs to. §1.5 establishes the two label sets disagree
  at 41.8 % Dice, so a model trained on ImageCAS masks cannot reach 89.8 against ImageCAS-X labels. As
  written the second gate silently requires a *second* binary run trained on ImageCAS-X's 640 — not in the
  plan's §3 sequence — and, if scored on the sealed 160, collides with the §2.2 leakage trap because §3
  trains the binary model on all 1000 ImageCAS cases including those 160.
- Tier 1's **Betti-0 ≤ 1 gate is mis-anchored on three counts.** (a) It cites "ImageCAS-X's inter-observer
  Betti error of 0.2–0.4", which is the **merged-lumen** aggregate; the same Table 1 gives the per-segment
  column, and the per-trunk values are **LM 0.00, LAD 0.10, LCx 0.08, RCA 0.08**. A per-trunk gate of ≤ 1 is
  an order of magnitude looser than the anchor it claims. (b) ImageCAS-X's β_err is defined over **two
  dimensions — components *and* loops** (verified from the methods text), i.e. β₀+β₁, so the anchor is not a
  Betti-0 number; and `Topology...md:160–163` (E8) justifies choosing plain Betti-0 *for comparability with
  ImageCAS-X's reported numbers*, which is therefore self-defeating. (c) "≤ 1" is not defined as a per-case
  maximum or a mean over cases; the two readings differ by an order of magnitude in strictness, and under
  the mean reading the gate is inside the published β₀ seed std of 1.1.

**Fix.** Move every gate onto the granularity where it is estimable. §2.1 already gives the project three
reporting granularities from one model; the **4-class trunk view has n = 155–160 for every class**, so that
is the only view where a five-tier-style gate can be decided. Recommendation: gates live on the 4-class and
merged views; the 14-class table is reported, never gated; Tiers 2–4 become "report with CI and n", which is
what the statistics support. Re-anchor the Betti gate on the per-trunk column (0.00–0.10), define it as
"per case, β₀ error = 0 in ≥ 95 % of cases", and state whether β₀ or β₀+β₁ is being compared.

### 2.6 The metrics the table gates on move *against* the clinical endpoint

`Acceptance thresholds...md:28–36, 191–214` argues honestly that these thresholds measure agreement with a
human reference, not clinical utility — and then sets the gates on Dice and Betti-0 anyway. BCS Table 2
(verified) is the one study that measured both on ImageCAS:

| Arch | Dice base → soft-BCS | β₀ base → soft-BCS | FFR-CT decision agreement |
|---|---|---|---|
| CT-FM | 0.809 → 0.807 | 4.3 → 4.6 | 75.4 % → 85.5 % |
| STU-Net | 0.818 → 0.813 | 2.9 → 4.0 | 77.5 % → 86.8 % |
| SwinUNETR | 0.799 → 0.788 | 7.9 → 8.3 | 78.5 % → 88.0 % |

Dice falls, β₀ error *worsens*, and clinical decision agreement rises ~10 pp in all three. **The proposed
acceptance table would have rejected the configuration that most improved the clinically relevant
endpoint.** This is a stronger version of the vault's own "Dice demoted" argument and it undermines gating
on β₀ as well, which nothing in the folder anticipates. Also note ±4.5 pp seed std on the FFR figure, so the
~10 pp gap is ≈2.2 σ — real but not enormous.

**Fix.** State this in §2.4 explicitly. Add a downstream decision-agreement endpoint (BCS, or per-segment
stenosis-category agreement derived from minimum lumen diameter) as a reported, non-gated primary; do not
let Dice or β₀ veto a configuration on their own.

### 2.7 The handover draft's FFR-CT numbers were right; the "correction" should be reverted

`Acceptance thresholds...md:53–60` "corrects" the handover draft by marking its "75–79 % for baselines,
85–88 % with Skeleton Recall or soft-BCS" as **unverified**, having only read the abstract. BCS Table 2
gives baselines **75.4 / 77.5 / 78.5 %** and soft-BCS **85.5 / 86.8 / 88.0 %**. The handover was accurate;
the correction is over-cautious and should be withdrawn (with the ±4.5 pp seed std added).

### 2.8 ASOCA's licence is wrong, and it gates the external-validation experiment

**Vault says.** §3.7 licence table: "ASOCA (40 cases) | **CC BY 4.0** | External-validation results
publishable", marked **[verified]**. §3.3 schedules scoring the binary model on those 40 cases.

**Actually true.** 40 labelled cases is correct (ASOCA: 60 total — 40 training with three-annotator labels,
20 test unlabelled). The licence is not. UK Data Service ReShare 855916 (the dataset of record) is
**Safeguarded / closed access**: "All requests are subject to the permission of the data owner or his/her
nominee. Please email the contact person for this data collection to request permission to access the data",
under the **UKDS End User Licence**. The **CC BY-SA 4.0** on that record covers the *preprint manuscript*
only. The Grand Challenge page likewise requires accepting dataset terms of use.

**Fix.** Correct the §3.7 row to "UKDS End User Licence, Safeguarded — access by permission of the data
owner; redistribution of data or derived labels not permitted; results publishable." Start the access
request now: §3.3 is otherwise blocked on an approval with an unknown turnaround, and it is currently
written as if the data were a download.

### 2.9 The Betti cancellation example is wrong, and Betti-1 is a free metric the plan omits

**Vault says.** `Topology...md:91–114`; E16/M13: plain Betti-0 is "cancellation-blind to a dropped branch
plus a hallucinated fragment", therefore Betti *matching* error (Stucki et al., ICML 2023 / arXiv:2407.04683)
is needed.

**Actually true.** The *conclusion* survives; the worked example does not. Betti-0 error is defined
**per class** as |b₀(pred) − b₀(gt)| (TopCoW `cls_avg_b0.py`, which the vault read). The example at
`:95–100, 108–114` builds cancellation from a broken branch in one class plus a hallucinated fragment
"elsewhere in the same class's label (another +1 in the opposite direction of **some other class**)" — under
a per-class absolute difference those do not cancel; they sum to 2. Real cancellation requires both errors
*within one class* (drop the whole branch, hallucinate a fragment of it elsewhere: b₀ = 1 = gt, error 0).
The example must be rewritten or the argument reads as confused.

**And the cheap fix is not persistent homology.** (i) Report **signed** Δb₀ (or the raw pair
(b₀ pred, b₀ gt)) instead of the absolute value — that alone reveals the drop-one/hallucinate-one pattern.
(ii) Add **per-component class purity**, already in §3.2. (iii) Add **Betti-1**: a coronary tree is acyclic,
so b₁(reference) = 0 by construction for every class and for the merged mask (barring a rare fistula or
collateral ring). b₁(pred) > 0 is therefore a *pure false-bridge counter* — exactly the failure
`Topology...md:150` says clDice is fooled by — and it needs no persistent-homology dependency (b₁ = b₀ − χ +
b₂ from the Euler characteristic of the voxel complex). ImageCAS-X's β_err already includes loops, so
reporting β₀ alone is also **not comparable** to the number E8 cites comparability with. Together (i)–(iii)
deliver most of M13's value at ~none of its cost, and M13/E16 can drop off the critical path.

**Also: "component count against expected" is ill-posed as written.** `Training plan.md:138`. Per class the
expected count is 1, which is well defined — but a class transected by a total occlusion or a large
calcified gap legitimately has reference b₀ = 2, so the correct comparator is the reference's own b₀, which
is what Betti-0 error already computes. For the merged mask the expectation genuinely varies (2, sometimes 3
with a separate conus origin), so "against expected" there is undefined. Delete the phrase; keep
|b₀ pred − b₀ gt| per class plus the raw counts, and state the merged expectation as a descriptive range.

### 2.10 The NaN policy silently blends detection into Dice and breaks the paired test

**Vault says.** §3.2 and E4/E21: absent-in-both skipped; present-in-one scored at the worst value (Dice 0,
a finite distance bound). `Deciding whether...md:146–150`: exclude a pair only when the policy says skip,
"do not silently drop one-sided-absence pairs".

**What the vault has not noticed.**

*(a) Per-class "Dice" stops being Dice.* With one-sided absence scored 0, the per-class mean factorises as
mean = (n_both-present / n_scored) × mean(Dice | both present). For L-PDA: a model detecting 4/8 with
conditional Dice 0.70 scores 0.35; a model detecting 8/8 with conditional Dice 0.35 also scores **0.35**.
Indistinguishable. Gating on detection F1 *and* reporting this number double-counts detection while the
notes claim they measure different things. Fix: report conditional Dice (both-present cases only) and the
detection rate as two separate numbers; never the blend.

*(b) The scored case set becomes model-dependent, which breaks pairing.* False-positive cases enter the
denominator, so two arms of a paired experiment are averaged over different case sets. Worse, `wilcoxon()`
"drops pairs with a NaN in either arm" — so a case where arm A predicted a spurious L-PDA (scored 0) and arm
B correctly predicted nothing (skipped ⇒ NaN) is **deleted from the paired test**. That discards exactly the
discordant cases the rare-class comparison depends on. Fix: fix the scored case set from the *reference*
(cases where the class is present in the reference), score false positives in detection precision, and use
that fixed set for every paired test.

*(c) The finite distance bound is an arbitrary scale factor on the mean.* mean MASD = (1−p)·mean_true +
p·B, so two models with identical geometry and different miss rates differ by B·Δp. TopCoW's B = 90 mm is
sized for a head CTA; the image diagonal here is √(179² + 179² + 87.5²) ≈ **268 mm** (512×512×250 at
0.35 mm), which is what Metrics Reloaded actually recommends. The choice can flip rankings.
`How to measure branch detection...md:139–140` correctly says the bound must be justified, not inherited,
but `Acceptance thresholds...md:221–225` then says to adopt TopCoW's rules "verbatim". Resolve it, and
prefer reporting the miss rate and the conditional distance separately over a single blended number.

### 2.11 Multiple comparisons are never mentioned anywhere

`Deciding whether a paired experiment...md` is otherwise the best-reasoned note in the folder (paired
Wilcoxon, bootstrap over cases not rows, effect sizes, pre-registration) but contains **no mention of
family-wise error or FDR**, and prescribes per-class testing, which multiplies the family.

Exposure: §3.4 ranks 6 experiments (+ ResEnc, heart-crop, rotation, binary-init, patch budget already in
§3/§5 ⇒ 10–11 comparisons). Metrics per comparison: Dice, clDice, NSD, MASD, HD95, detection F1, β₀ = 7.
Classes: 14, at three reporting granularities. Core five experiments × 7 metrics × 14 classes = **490
tests**; the full list ≈ **1 078**. At uncorrected α = 0.05 that is ~24–54 expected false positives, against
true effects of ≤2 points sitting inside a seed σ of 1.8. The false-to-true discovery ratio is the problem,
not the p-values individually.

**The fix, named.** (i) Pre-register **one primary endpoint per experiment** — one metric on one class group
(for this project: per-class detection F1 on Tier 1+2, or clDice on trunks) — with a superiority margin
equal to the measured seed σ (§2.2). (ii) Everything else is explicitly exploratory: report effect +
bootstrap CI, **no p-values**. (iii) If per-class p-values are wanted, Holm within one experiment × one
primary metric (family = 14 classes), Benjamini–Hochberg across the exploratory grid. (iv) Spend the budget
on seeds, not endpoints: 3 seeds per arm on one endpoint is worth more than 1 seed per arm on 490.

### 2.12 The clDice citation in the CAT08 note does not exist

**Vault says.** `Centerline extraction metrics from CAT08...md:56`: "**Centerline Dice (clDice)** (Moccia et
al. 2018, 'Towards Automatic Coronary Calcium Scoring in a Screening Study with Low-Dose Chest CT,' IEEE
TMI; further developed in 2020s vessel-segmentation literature)".

**Actually true.** clDice is **Shit, Paetzold, Sekuboyina, Ezhov, Unger, Zhylka, Pluim, Bauer, Menze,
"clDice — a Novel Topology-Preserving Loss Function for Tubular Structure Segmentation", CVPR 2021**
(openaccess.thecvf.com; code github.com/jocpae/clDice).

I checked each component of the vault's citation separately against Crossref:
- **"Moccia et al. 2018" is a real paper** — Moccia, De Momi, El Hadji, Mattos, *Blood vessel segmentation
  algorithms — Review of methods, datasets and evaluation metrics*, Computer Methods and Programs in
  Biomedicine 2018, doi:10.1016/j.cmpb.2018.02.001. Topically plausible as something an agent consulted.
- **The title is a near-match to a different paper by different authors** — Lessmann, Išgum, Setio, de Vos,
  Ciompi, de Jong, Oudkerk, Mali, Viergever, van Ginneken, *Deep convolutional neural networks for
  automatic coronary calcium scoring in a screening study with low-dose chest CT*, SPIE Medical Imaging
  2016, doi:10.1117/12.2216978 (and Išgum et al., *Automatic Coronary Calcium Scoring in Low-Dose Chest
  Computed Tomography*, IEEE TMI 2012, doi:10.1109/tmi.2012.2216889 — which supplies the "IEEE TMI").
- **No work with the vault's exact title exists** in Crossref, and none of the above has anything to do with
  clDice.

**Verdict, stated plainly:** this is **not a fabricated paper** — it is a **composite misattribution
assembled from three real sources**: a real author-year (Moccia 2018, vessel-metrics review), a title
approximating a real calcium-scoring paper by unrelated authors, a venue borrowed from a third, and the whole
thing attached to a claim none of them makes. The citation *as written* does not exist, and the attribution
of clDice is false. It must be struck and replaced with Shit et al., CVPR 2021 before any of this reaches a
manuscript. This is the only citation in my slice that failed this way; every other one I could reach
resolved to a real source saying roughly what the vault says it says.

### 2.13 The CAT08 note misreads the metrics it dismisses

**Vault says.** `Centerline...md:12–52, 94` and E25: CAT08 defined "three metrics"; overlap accuracy uses
"a distance tolerance (e.g., 2 mm)" and is "reported as % at multiple tolerances (e.g. 1 mm, 2 mm, 3 mm,
5 mm)"; "OTF"; **do not use CAT08 metrics**.

**Actually true.** The Rotterdam framework (Schaap et al., Med Image Anal 2009) defines **four** measures:
**OV** (total overlap), **OF** (overlap until first error), **OT** (overlap of the clinically relevant part,
**radius ≥ 0.75 mm**, i.e. 1.5 mm diameter), **AI** (accuracy inside). The vault omits OT entirely and
misnames OF. Critically, **the tolerance is not a fixed distance at all**: "a point of the reference standard
is marked as true positive if the distance to at least one of the connected points on the evaluated
centerline is less than **the annotated radius**" — a per-point, **calibre-adaptive** tolerance. There are no
multiple fixed tolerances.

This matters twice over. First, the recommendation to discard CAT08 rests on a misreading. Second, CAT08's
radius-scaled tolerance is **the principled answer to the τ problem in §2.1**: a tolerance proportional to
the local reference radius is scale-free, needs no per-class table, cannot exceed the vessel, and is a
published, 2009-vintage convention with cross-paper precedent. And OT independently encodes the same 1.5 mm
clinical-relevance floor that `What downstream...md:80–90` derives from CAD-RADS/SCCT/SYNTAX — three
lineages plus CAT08 converging on the same cut. One further inconsistency inside the folder: `What
downstream...md:185–195` names OT correctly ("overlap of the clinically relevant portion") while the CAT08
note does not.

Two smaller errors in the same note: `:58` "skeletonization (Euler characteristic = number of connected
components = number of 'skeleton trees')" — χ = b₀ − b₁ + b₂, not b₀. And the CAT08 figures quoted in
`What downstream...md:190–193` (OV 99.97 %, OF 100 %, OT 99.98 %, AI 0.13 mm) are implausible for an
algorithm on CAT08, where the second-observer reference itself sits near 97 %; the note flags them as
secondary/unverified, and they should not be quoted as a "ceiling" until the row is identified.

### 2.14 CLAIM: the vault is one version behind, and all its item numbers are from the superseded checklist

`CLAIM and TRIPOD+AI...md:33–36` cites only **CLAIM 2020** (Mongan, Moy, Kahn, Radiol Artif Intell
2020;2(2):e200029) and maps items 14, 16, 18, 20–21, 28, 29, 32, 37. A **2024 Update** exists and is what a
2026 reviewer will apply: **Tejani, Klontzas, Gatti, Mongan, Moy, Park, Kahn; "Checklist for Artificial
Intelligence in Medical Imaging (CLAIM): 2024 Update", Radiology: Artificial Intelligence, July 2024,
doi:10.1148/ryai.240300**. The 2024 version restructures and renumbers, so every item number in the note is
stale even where the substance transfers. The note's own conclusions (uncertainty on every number,
same-source-data limitation, failure-case examples) are correct and survive; the citation and numbering must
be redone against 2024.

### 2.15 The uncertainty note has no sources, and one of its recommendations is not executable

`Confidence and uncertainty estimation in segmentation.md` contains **zero citations** — 113 lines resting
on "a survey of 2023–2025 segmentation papers" that names none, with cost figures (5–20×, 20–50×, <5 %)
given without provenance. Two concrete errors:
- **"Enable dropout during test time" (E30, `:82–88`) is not possible.** nnU-Net v2's default
  configurations instantiate no dropout layers, so MC dropout requires retraining, not a test-time flag.
- **The cheapest epistemic uncertainty is already paid for and the note says it is expensive.** nnU-Net's
  standard workflow trains 5 folds and ensembles them, and §2.2 already commits to all five folds for the
  final config; `--save_probabilities` writes softmax. So per-voxel ensemble disagreement and softmax
  entropy cost **zero extra training** for the configuration that matters. The note's "ensembles = 5–20×
  inference" framing leads to the wrong conclusion.

It also omits **calibration** entirely (reliability diagrams / ECE / Brier on the voxel and presence
outputs), which is the part of this subject a reviewer would actually ask about.

### 2.16 Two dangling references

- `Metrics.../Proposed changes.md:88–92` (E32–E36) cites its evidence as "Research-stage reporting
  guidelines (new note)" / "same". **No such note exists** in the folder (15 files, none by that name). Five
  proposals with no traceable source.
- `Topology...md:124–136` reproduces a VesSAP table extracted "via automated tooling … not manually
  cross-checked", with a "Dice ↓ better" orientation the note itself calls unusual. The note handles this
  honestly, but the table should be deleted rather than carried: the qualitative claim it supports
  ("Betti matching error fell by roughly a third") does not need it, and a table nobody has read against the
  PDF will eventually be quoted.

---

## 3. Weak reasoning / unsupported leaps

1. **§2.4's "provisionally closable" is the wrong status.** Two of the five tiers cannot be estimated, the
   one hard number is mis-anchored (§2.5), and the gated metrics contradict the clinical endpoint (§2.6).
   The honest status is "structure agreed, numbers open", which is where `Training plan.md:154` already has
   it. Closing it now converts an open question into a false floor that later results will be compared
   against.
2. **The NSD note argues itself out of its own recommendation and does not notice.**
   `NSD tolerance...md:102–118` concludes one voxel is "almost certainly **too tight** for trunks", then
   recommendation 2 at `:125` adopts one voxel "for every class". §3.2 and the acceptance table inherit the
   contradiction.
3. **"Two independent routes arriving at the same pool"** (`How to measure branch detection...md:42–44`) is
   weaker corroboration than claimed: TopCoW's authors overlap with the Metrics Reloaded author group
   (Paetzold, and the challenge is DKFZ/TUM-adjacent), and TopCoW postdates and cites the framework. It is
   one lineage applied twice, not two independent arrivals.
4. **Regulatory κ is used as a calibration anchor for a segmentation threshold.**
   `Acceptance thresholds...md:120–136` is careful to say κ 0.49–0.55 "is not a segmentation-Dice number and
   is not directly comparable", and then uses it to argue what "good enough for a real product" has meant.
   Those κ values compare a plaque-quantification *output* against a *different clinical method* — a
   method-comparison statistic, not an agreement-with-reference-standard one. It cannot calibrate a Dice
   gate in either direction and should be cut to one sentence of context.
5. **"Human ceiling" is treated as a precision ceiling when for several classes it is a definition
   disagreement.** OM1's inter-observer DSC of 74.1 with ASSD 3.47 mm is not two observers jittering a
   boundary; it is two observers disagreeing about *which vessel is OM1*. Setting a threshold relative to
   that number gates the model on schema ambiguity. The class-schema work should be cited as the remedy, not
   the metric.
6. **"Expect a 5–8 Dice-point drop" on ASOCA conflates domain shift with label-convention shift.** The
   three supporting measurements are real (`External validation...md:51, 107, 121–124`: ImageCAS→ASOCA 6.4,
   ASOCA→GeoCAD 8.0, Kim internal→external 5.3), so the *number* is evidenced. The *inference* — "a larger
   one signals overfitting to ImageCAS's single-centre protocol" — is not: §1.5 measures 41.8 % Dice between
   two annotations of the *same scans*, so an annotation-convention mismatch between ImageCAS and ASOCA
   could dominate the drop entirely. Fix: control for it — score with clDice and detection F1 alongside Dice
   (both less sensitive to boundary convention), restrict to a common diameter floor, and state the two
   cohorts' annotation protocols side by side as TRIPOD+AI 20c asks.
7. **"Don't use micro" is asserted, not argued.** Micro is the right summary for one real question ("how
   much of the lumen did we label correctly, weighted by how much lumen there is"). The defensible position
   is to report macro, micro and merged with all three labelled — not to pick one.
8. **Metrics Reloaded is treated as prescriptive where it is a consensus decision aid.** It supplies no
   thresholds (the note says so at `:30`) and its own pitfall list warns that hyperparameter choices (τ, IoU
   threshold, connectivity) are pitfalls in their own right. Citing it for the pool is right; citing it for
   authority over the τ *value* is exactly the pitfall.

---

## 4. What's missing — extensions that would change a decision

Ordered by how much they change.

1. **A calibre metric. This is the largest hole in the evaluation.** Every downstream task the vault surveyed
   needs diameter: CAD-RADS grades diameter stenosis; FFR-CT resistance goes as diameter⁴; and
   ImageCAS-X reports local DSC correlating with lumen diameter at ρ = +0.89, i.e. Dice is *confounded by*
   calibre rather than measuring it. Yet `What downstream...md:106–110` identifies "minimum lumen diameter
   along the centerline" as the metric that matters, and no item in E1–E36 computes it. Add: (a) mean signed
   and mean absolute **radius error per centerline point**, per class — signed matters, because systematic
   over-thickness is the failure mode NSD certifies as perfect (§2.1); (b) **minimum-lumen-diameter error
   per segment**, the quantity clinical reads use. Both are computable today from ImageCAS-X's shipped
   centerlines and radii, before any annotation exists. This changes the acceptance table (a calibre row),
   the NSD decision, and what the manuscript can claim.
2. **A downstream decision-agreement endpoint.** BCS Table 2 is proof that this is measurable on ImageCAS
   and that it moves ~10 pp between configs while Dice moves 0.5 and β₀ moves the wrong way (§2.6). Either
   compute BCS (bifurcation connectedness at reference bifurcations — cheap, no CFD) or a per-segment
   stenosis-category agreement from minimum diameter. This is the "clinical utility" the vault correctly
   says it lacks, and it is far cheaper than the outcome study it imagines would be needed.
3. **CAT08's OV / OF / OT, computed on centerlines extracted from the prediction, with the radius-scaled
   tolerance.** OF per class answers the question this project exists to answer — *how far along each named
   branch do we track before failing* — which no metric in the current pool measures. OT restricts to
   radius ≥ 0.75 mm, giving a clinically-scoped score alongside the full one. This reverses E25 and supplies
   the tolerance convention §2.1 needs.
4. **Evaluate rare classes as a presence-detection problem, not a segmentation problem.** Per-class Dice at
   n = 8 is hopeless (§2.5). Per-class *presence* prediction pools all 160 cases (8 positives, 152
   negatives) and supports an ROC/PR curve with a real CI, plus calibration. That is a genuine power gain
   for Tiers 3–4 and turns "we cannot say anything about L-PDA" into a reportable, if modest, result. It also
   gives the uncertainty note its one clearly useful job.
5. **Measure the human ceiling as a paired comparison, not a quoted number.** ImageCAS-X's 160-case
   two-analyst overlap is published per class. Run the project's own harness on annotator-2-vs-annotator-1
   and report **model-minus-human paired differences with CIs** on the same cases. On these case counts that
   is the only defensible form an "acceptance threshold" can take: not "Dice ≥ 87", but "not more than
   X points below the human pair, 95 % CI". It also neutralises the aggregation problem in §2.3, because
   both sides are aggregated identically.
6. **A scalar label-swap statistic.** The AHA confusion matrix is proposed (E-pool, M4) but no summary
   number. LAD↔LCx, D↔OM, R-PDA↔R-PLA are *swaps*, which one-vs-rest Dice reports as two mediocre scores.
   Report a normalised swap rate per confusable pair, plus left-system↔right-system off-diagonal mass as a
   single chirality-failure number (which also gives the mirroring decision in §4 of the plan a measurable
   endpoint).
7. **Calibration.** No reliability diagram, ECE or Brier anywhere, on either the voxel softmax or per-class
   presence. Free from the 5-fold ensemble §2.2 already commits to. Also the honest answer to "what does the
   released model output" (E31).
8. **Seed variance as a first-class experiment.** §2.2 makes this the cheapest high-value run in the plan:
   two seeds, same config, one fold. It sets the superiority margin for every subsequent comparison and it is
   currently nowhere in §3.4's ranked list. It should be priority 0.
9. **Move the gates to the granularity where they are estimable.** §2.1 already produces 14-class, merged
   and 4-class views from one model at no cost. Nobody connected that to the thresholds. The 4-class view has
   n = 155–160 per class and is the only view where a gate can be decided; state that, and the five-tier
   table becomes coherent instead of aspirational.

---

## 5. Confidence, and what I could not check

**High confidence (primary source read this session).**
ImageCAS-X Table 1 in full, including per-segment n, DSC, HD95, β_err, clDice, ASSD, and the β_err
two-dimensional (components + loops) definition — arXiv:2608.30404 HTML. BCS Table 2 caption and results
including the seed-std line — arXiv:2607.28327 HTML; abstract and OR 2.16 [1.23, 4.18] confirmed from the
abstract page. ASOCA composition (60/40/20) and access conditions — asoca.grand-challenge.org and UKDS
ReShare 855916. clDice provenance — CVPR 2021 Open Access. The Moccia / Lessmann / Išgum citation forensics
— Crossref API queries. CLAIM 2024 Update existence and authorship. CAT08's four measures and the
annotated-radius tolerance. Metrics Reloaded's existence, Nature Methods reference, the τ-from-inter-rater
guidance, the clDice-for-tubular recommendation, and DG7.1's NSD-vs-Boundary-IoU split.
All arithmetic in this report is mine and reproducible from numbers stated here.

**Medium confidence.**
The Metrics Reloaded **problem-fingerprint path** as I have characterised it. I verified the framework's
structure and the specific recommendations the vault quotes, but the supplementary decision-guide figures
(DG7.1–7.3, the FP tables, Extended Data SN 2.x) did not render for me — the PDF is large and the PMC copy
returned only the main text. My reading of the path is: FP1.1 semantic segmentation multi-class → S-overlap
gives DSC by default, **plus clDice for FP3.3 tubular**; FP3.1 (small relative to grid) + FP4.3.1 (noisy
reference) jointly license demoting DSC, and FP3.1/FP3.5 (touching at bifurcations) push toward re-phrasing
as detection/instance — which the plan correctly declines while adopting the compromise the framework itself
suggests, a per-class detection metric with a stated localisation criterion; FP2.5.7 (compensate annotation
imprecision) → **NSD**, *or* Boundary IoU where contour error is the crucial thing; FP2.5.6 distance
penalisation → **MASD** default, HD95 for outliers; FP4.6/FP5.2 (empty reference/prediction possible) → the
NaN rules; FP6 small-test-set → CIs and per-case values. On that reading the vault's pool is faithful, and
the framework's recommendations it **omits** are: **Boundary IoU** (the other half of DG7.1, and the half
its own FFR-CT rationale selects); a **volume/size-based metric** for a task whose downstream quantity is
calibre; **calibration assessment** of the probabilistic output; and reporting the DSC-vs-clDice pair
without IoU, which the vault does get right. Treat the FP-item numbering as indicative rather than quoted.
Also medium: my macro-vs-micro estimate of ≈89 for micro (the 82.4 macro and 92.8 merged figures are exact;
micro is modelled from a 75–85 % trunk volume share).

**Could not check.**
- Metrics Reloaded's **NaN-handling recommendation** and the worked examples the vault quotes (DSC 0.90 vs
  0.60; HD 6.76 vs 11.10) — these live in the supplementary notes, which I could not render. The vault's
  version is internally consistent and matches the framework's philosophy; I neither confirmed nor refuted
  the verbatim wording. The vault's own reading of it is anyway the right one.
- **Nikolov et al.** (the 95th-percentile-of-surface-distances method for τ) — I ran out of search budget
  before reaching it, so it remains the two-hop citation the vault honestly flags. My §2.1 argument does not
  depend on it: it holds for *any* τ derived from this cohort's inter-annotator distances.
- **Stucki et al.** (Betti matching, ICML 2023 / arXiv:2407.04683) — not independently opened. My §2.9
  critique is of the vault's *argument*, not of Stucki's method, and does not require the paper.
- **TopCoW's NEJM AI record** (doi:10.1056/AIdbp2500994) and its evaluation code — not opened. The vault
  read the code directly and its quotes are specific and internally consistent; I have no reason to doubt
  them, and the one ambiguity it flags (union vs intersection in `generate_cls_avg_dict.py`) it flags
  correctly.
- **CAD-RADS 2.0 primary text**, **Fernández-Martínez 2024**, and the CMS LCDs — all behind the same walls
  the vault records. Its flagging is accurate; I add nothing.
- The **CAT08 figures** (OV 99.97 / AI 0.13 mm) — I judge them implausible for an algorithm row but could
  not identify the row.
- A **second seed-variance estimate**. Everything in §2.2 rests on one caption in one preprint. It is the
  best number available and it is on the right dataset, but it should be re-read from the PDF before it goes
  in a manuscript, and the project's own two-seed run (extension 8) should replace it as the operative
  figure.
