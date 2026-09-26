---
tags: [review, verification, decision-record]
status: complete
updated: 2026-09-26
slice: Research/Class schema, proposals §2.1
---

# Review 02 — Class schema

Reviewer 2 of 10. Slice: `vault/Research/Class schema/` (12 notes) against §2.1 of
`vault/Proposed changes to the training plan.md` and the plan's open item at
`vault/Training method/Training plan.md:146-148`.

---

## 1. Verdict (5 lines)

The schema choice is defensible and I would keep it, but §2.1 is written as closed when
three of its four supporting claims are wrong or unsupported. Adopting ImageCAS-X's
14 classes is right — the labels exist, the lineage is genuine. But "the SCCT 18-segment
model with the landmark-based cuts removed" is inexact (it also removes two perfectly
reproducible bifurcation-defined cuts, and silently drops septals, acute marginals and
nodal arteries from the label map entirely); "Other" is a trash bin that provably breaks
both proposed merges; "costs nothing" is false in two specific, fixable ways; and the
nearest-centerline Voronoi rule is understated by ~100× in voxel terms — its boundary is
the **angle-bisector plane**, not a 2–3-voxel carina, and at a 20° diagonal it hands
~13 mm³ (~300 voxels) of LAD trunk to D1. Two of the 14 classes (L-PDA n=8, L-PLA n=9 of
160) are **statistically unmeasurable** on the sealed test set and the plan should say so
rather than list them as a "risk". The single biggest unexamined fork is not 14-vs-4: it
is one-stage 14-class voxel model vs. binary lumen + centerline naming, which
`Training plan.md:103-104` already licenses and the class-schema folder never evaluates.

---

## 2. Errors found, ranked by what changes the plan

### E1. "Other" cannot be merged, so "fourteen merges down to four" is false

**Vault says:** `Proposed changes to the training plan.md:190-193` — "Report at three
granularities from the same model — 14-class, a Hampe-style merge, and 4-class trunks.
Fourteen merges down to four; four never splits into fourteen. Costs nothing". Repeated at
`Research/Class schema/Proposed changes.md:48-58` and `Class schema options.md:286-289`.

**Actually true:** Class 14 is `Other (D3, D4, OM3, OM4)` — verified verbatim from
ImageCAS-X Supplementary Table 4 (arXiv:2608.30404). D3/D4 are LAD-territory branches;
OM3/OM4 are LCx-territory branches. One label, two parents. So:

| Merge target | Where class 14 goes |
|---|---|
| 4-class trunks | D3/D4 → LAD, OM3/OM4 → LCx — **undefined** |
| Hampe-style 10 | D3/D4 → D, OM3/OM4 → OM — **undefined** |

The merge hierarchy is not a tree. It is also incomplete for **IM**: Hampe's 10 classes are
LM, LAD, LCX, RCA, D, S, OM, AM, R-PDA, R-PLB (verified, PMC11095121) — there is **no
ramus/IM class**, so IM has no Hampe destination either.

**Evidence:** Hampe et al., J Med Imaging 2024;11(3):034001, PMC11095121 — class list and
per-class F1 (RCA 0.90, LAD 0.86, AM 0.84, LCX 0.74, OM 0.74, D 0.73, LM 0.70, R-PLB 0.69,
R-PDA 0.69, S 0.54) match the vault's transcription at `Class schema options.md:256-258`
exactly. ImageCAS-X Supp. Table 4 confirmed via arXiv HTML.

**Fix:** Split class 14 at import into `Other-diagonal` and `Other-marginal` (15 classes).
The parent vessel is already known from the centerline tree ImageCAS-X ships, so this needs
**no re-annotation** and no new voxels — it is a relabel of the same mask. That makes the
merge a proper tree and removes the incoherence in E2. Then state the merge tables
explicitly in the plan, including IM's destination (SYNTAX puts the ramus in the circumflex
territory — segment 12 "belongs to the circumflex territory" — so IM→LCx for the 4-class
view; IM has no Hampe destination and the Hampe-granularity report must say so).

---

### E2. "Other" is a trash bin, not a class, and is unlearnable as defined

**Vault says:** kept as a class with only "Other is a mixed bag" as the recorded objection
(`Class schema options.md:271`).

**Actually true:** three independent defects, each quantified.

1. **Ordinal membership.** Class 14 means "the *third or fourth* diagonal/marginal".
   Membership depends on how many similar branches lie proximal to the voxel — non-local
   information. A `3d_fullres` patch of ~256³ at 0.35 mm is ~90 mm; it frequently will not
   contain D1 and D2 to count from. Even D1-vs-D2 is ordinal; D3-vs-D2 is worse.
2. **Size-relative inclusion.** ImageCAS-X (verified verbatim): extra D/OM branches were
   labelled Other "if they were at least as large as the first or second branches or
   >1.8 mm in diameter at the most proximal end." The *same vessel* is class 14 in one
   patient and unlabelled (background) in another. That is definitional label noise, not
   observer noise, and no amount of data fixes it.
3. **Presence agreement is worse than chance-ish.** Other is present in 14/160 test cases
   (8.8%) with presence agreement 88.8% → the two analysts disagreed on presence in ~18 of
   160 cases, i.e. **more cases than the class is present in**. (Caveat: the vault itself
   hedges the column reading at `Class schema options.md:174-175`; I read the same table
   and agree with its transcription but not with dismissing this row.)

**Fix, in order of preference:** (a) split as in E1 — this alone fixes defect 1 partially
and defect 3's interpretability; (b) additionally exclude class 14 from the class-balanced
sampler and from per-class acceptance thresholds, reporting it only as "unnamed side
branch, binary"; (c) if it is kept unsplit, map it to nnU-Net v2's `ignore` label so it
neither trains nor scores — supported (`MIC-DKFZ/nnUNet documentation/ignore_label.md`),
but note open issue #2884 reports the ignore label misbehaving with more than one label,
and this sacrifices the "union of classes = lumen" property that the binary comparison
needs.

---

### E3. The Voronoi bifurcation boundary is an angle-bisector plane, not a 2–3-voxel carina — the vault is off by ~100×

**Vault says:** `Research/Class schema/SCCT prose bifurcation rule versus Voronoi voxel
assignment remains unvalidated.md:49` — "The carina region is a few voxels wide — often
2–3 voxels in a 0.35 mm voxel-spaced volume. Any disagreement between the two rules affects
a handful of voxels per branch point. The branch volumes are hundreds or thousands of
voxels; this is noise at the level of Dice." Echoed in `Research/Class schema/Proposed
changes.md:131-132`.

**Actually true:** Work the rule out. Take the parent frame with the branch point at the
origin, `s` along the parent axis, `d` lateral toward the daughter, daughter leaving at
branch angle θ. Distance from a voxel to the parent centerline is `d`; to the daughter ray
is `|s·sinθ − d·cosθ|`. The voxel goes to the daughter iff

&nbsp;&nbsp;&nbsp;&nbsp;`d > s · tan(θ/2)`

i.e. the boundary is exactly the **bisector of the branching angle**, a plane at θ/2 to the
parent axis through the branch point. It leaves the parent lumen (radius r) only at

&nbsp;&nbsp;&nbsp;&nbsp;`s* = r / tan(θ/2)`,&nbsp;&nbsp;&nbsp;&nbsp;
and the parent-lumen volume it hands to the daughter is `V = (2/3)·r³ / tan(θ/2)`.

| Parent Ø | θ | s* (mm) | V (mm³) | voxels @0.35 mm iso |
|---|---|---|---|---|
| 3.0 mm (pLAD) | 20° (diagonal) | **8.5** | **12.8** | **~298** |
| 3.0 mm | 40° | 4.1 | 6.2 | ~144 |
| 3.0 mm | 70° (obtuse marginal) | 2.1 | 3.2 | ~75 |

A D1 of ~0.8 mm mean radius and 40 mm length is ~80 mm³. So at a shallow diagonal the
wedge is **~16% of D1's total volume**, sitting inside the LAD trunk, 8.5 mm long. That is
two orders of magnitude off "2–3 voxels", and it is **not** noise.

Consequences the vault does not draw:

- **Anatomically indefensible.** The rule assigns lumen that is unambiguously inside the
  parent trunk to the side branch, and the assignment gets *worse* the shallower the branch.
- **It biases the downstream measurement ImageCAS-X exists for.** Their stated motivation is
  per-segment "plaque and perivascular quantification" (verified from the abstract). Plaque
  and PCAT sitting in the LAD just past the D1 ostium is attributed to D1. This is a flaw in
  the dataset, not only in adopting it.
- **Does it cap Dice?** Partially, and the scaling is the interesting part. The interface has
  **no image evidence** — nothing in the CT marks the bisector plane — so localisation error
  there is irreducible. Interface area inside the cylinder scales as ~`πr²/(2·sin(θ/2))`;
  Dice loss for the daughter ≈ `A·ε/V_daughter`. At r=1.5 mm, V=80 mm³, ε=0.35 mm (one
  voxel): **~9 Dice points at θ=20°, ~2.7 at θ=70°, <1 for a trunk**. So the rule costs
  single-digit-to-~9 Dice points on shallow-angle small branches and ~nothing on trunks.
  That is the mechanism behind the vault's own most anomalous number: **D1 has human
  inter-observer DSC 79.9 ± 28.7 despite being present in 155/160 cases**, while RCA (few
  shallow trunk branches) gets 95.3 ± 5.0. The vault has this data
  (`Class schema options.md:182`, `:187`) and never connects it to the labelling rule.
- **Error amplification.** The wedge position is set by where the annotator puts the
  daughter's first centerline point. A 1 mm shift along the parent moves ~πr²/2 = 3.5 mm³
  (~82 voxels, ~4% of D1); a 5° angle error at θ=20° moves ~25% of the wedge. Centerline
  placement error at the ostium is *amplified* into voxel-label disagreement by ~1/tan(θ/2).

**Fix (cheap, exact, no re-annotation):** replace Euclidean-nearest-centerline-point with
either (a) **geodesic (within-lumen) distance** along the centerline tree, or (b) truncate
the daughter's centerline at the point where it exits the parent's maximal inscribed sphere
(the bifurcation "core"), then run Euclidean Voronoi. Both are deterministic, both keep the
carina with the parent (SCCT-consistent), and both are computable from the centerlines and
masks ImageCAS-X already ships. Then **measure the wedge directly** on the imported 800
cases — it is a ~20-line script, not an annotation round — and report it. If you keep
ImageCAS-X's rule for headline comparability, emit the corrected variant as a paired
experiment and say which number is which.

---

### E4. The class-schema folder's own proposal states the opposite of its evidence note

**Vault says:** `Research/Class schema/Proposed changes.md:128-131` — "The SCCT reporting
standard's prose definition … and ImageCAS-X's nearest-centerline Voronoi rule **produce the
same voxel assignment** at a bifurcation — but this has never been validated in the
literature."

**Actually true:** the note it cites says the opposite. `SCCT prose bifurcation rule versus
Voronoi voxel assignment remains unvalidated.md:31` — "This is **different from the prose
rule**"; and `Bifurcation ownership and carina voxel assignment.md:76-80` spells out the
divergence. The proposal asserts agreement; the evidence asserts disagreement. Whichever
sentence a reader takes to the plan changes what gets built.

**Fix:** delete the assertion. Per E3 the two rules demonstrably differ, and by a large
margin at shallow angles.

---

### E5. "SCCT's prose rule is that the carina stays with the parent" is the vault's inference, attributed to SCCT

**Vault says:** `SCCT prose bifurcation rule … .md:14` — "For bifurcations, the rule is
structural: **a bifurcation belongs to the parent by default**"; `:21` — "The implicit
mechanism: the carina … stays with the parent, by convention." It derives this from segment
6's boundary ("End of LM to the first large septal or D1 >1.5 mm").

**Actually true:** segment 6's definition is an **intra-vessel subdivision** rule — which
*part of the LAD* a lesion is in — not an ownership rule between LAD and D1. SCCT says
nothing about whether a carina voxel belongs to LAD or D1, because it is a 2D angiographic
reporting convention with no voxel semantics. The note half-admits this at `:41` ("No
radiologist paper formalizes 'the carina belongs to the parent' as a testable voxel rule")
and then states it as SCCT's rule at `:14` and `:21`. Separately, SYNTAX's wording for the
same boundary is "**proximal to and including** first major septal branch" — i.e. the
*opposite* inclusion — so even the intra-vessel reading is not stable across standards.

**Fix:** stop attributing a voxel-ownership convention to SCCT. State the project's own rule
and justify it on reproducibility and on the plaque-attribution argument in E3, which does
not need a guideline to back it.

**Caveat on my own evidence:** I could not open SCCT 2014 full text (Elsevier 403; the
SCCT-hosted PDF the vault says it read was not reachable for me). The segment-6 wording
above is the SYNTAX form, corroborated from a secondary source. Treat the vault's Appendix 1
transcription as **unverified by me**, not as refuted.

---

### E6. "The SCCT 18-segment model with the landmark-based cuts removed" is inexact, and what is lost is bigger than the vault records

**Vault says:** `Proposed changes to the training plan.md:185-187`; `Class schema
options.md:80-90`, `:319-323`, `:131-142`.

**The mapping, worked out:** SCCT 18 → 13 named classes (+ Other = 14):

| Collapse | Boundary removed | Reproducible? |
|---|---|---|
| 1,2,3 → RCA | pRCA\|mRCA = half-way to acute margin | **no** (geometric) |
| | mRCA\|dRCA = at the acute margin | **no** (geometric) |
| 6,7,8 → LAD | pLAD\|mLAD = first large septal or D1 >1.5 mm | **yes** (a branch origin) |
| | mLAD\|dLAD = half-way to the apex | **no** (geometric) |
| 11,13 → LCx | pLCx\|LCx = origin of OM1 | **yes** (a branch origin) |

So 18 → 13 is arithmetically exact (and 4→R-PDA, 5→LM, 9→D1, 10→D2, 12→OM1, 14→OM2,
15→L-PDA, 16→R-PLA, 17→IM, 18→L-PLA all map 1:1). But **two of the five removed cuts are
bifurcation-defined and perfectly reproducible**, so "the landmark-based cuts removed"
overstates what was dropped. And the vault's stated rationale is not the paper's:
ImageCAS-X says it collapsed them because "they depend on **side branch positions which are
highly variable**, and **for consistency** we also consider the RCA as a single segment"
(verified verbatim) — a variable-anatomy and consistency argument, not the
non-topological-landmark argument the vault asserts at `:85-90` and `:319-323`. The vault
quotes the real sentence at `:139-142` while omitting the RCA clause, then reasons from a
different premise.

**What is silently lost, beyond the cuts:**

1. **Septal perforators, acute marginals and nodal arteries are not labelled at all.**
   Verified verbatim from ImageCAS-X: "Septal perforators, acute marginals and nodal
   arteries were not traced." The vault does record this — but only in
   `Variant and absent branches.md:134-137`, and never surfaces it in §2.1 or in
   `Class schema options.md`'s account of what the mapping loses. Two consequences the vault
   misses:
   - These vessels are **visible in CCTA and labelled background**. The model is being
     taught to suppress real vessels. At an LAD/septal bifurcation there is no septal
     centerline, so the Voronoi rule claims part of the septal ostium for LAD and the rest
     becomes background — the label boundary cuts across a real vessel arbitrarily.
   - The ImageCAS-X **lumen** is therefore not "the coronary lumen". Phase 1 trains
     `Dataset710` on original ImageCAS masks (which include plaque, pulmonary vessels and
     coronary veins per §1.5) and `Dataset711` on ImageCAS-X's lumen. The two runs disagree
     about foreground *by construction*, and 710's output is what seeds annotators. This
     partly explains the 41.8% Dice between the two label sets and it is worth one sentence
     in §2.1, since `configs/labels/coronary_lumen.yaml` currently asserts the two sources
     are interchangeable ("Both ImageCAS's merged masks and ImageCAS-X's lumen annotation
     are a single vessel/background volume … there is nothing here to choose").
   - It also breaks the Hampe merge a second way: Hampe has **S** and **AM** as classes, and
     AM is Hampe's third-best class (F1 0.84). A "Hampe-style" report from this schema can
     cover at most 8 of Hampe's 10 classes.
2. **The pLAD boundary is not recoverable even in principle**, because it is defined by the
   first large septal — a vessel this schema does not trace.

**Fix:** rewrite the §2.1 rationale as "the SCCT 18-segment model with the
proximal/mid/distal subdivisions collapsed (two of them reproducible, three landmark-based),
and with septals, acute marginals and nodal arteries excluded from labelling", and record the
exclusion as a limitation rather than a detail in a companion note.

---

### E7. "Proximal/mid/distal can be recovered from a centerline and a few landmarks" is an unsupported leap that the plan leans on

**Vault says:** `Class schema options.md:88-90` ("recoverable after the fact from a
centerline and a few landmarks"), `:319-323`, `:370-371`, and
`Proposed changes to the training plan.md:183-184` ("those are reported from the centerline
afterwards").

**Actually true:** the three landmark cuts need the **acute margin of the heart** and **half
the distance to the apex**. Neither is a coronary structure. Neither is in the label map,
and neither is in ImageCAS-X's shipped centerlines or descriptors. Recovering them requires
a myocardium/epicardium segmentation the project does not have and has not scoped. The fourth
boundary (pLAD\|mLAD) needs the first septal, which this schema does not label (E6).

So the claim that nothing clinical is lost by dropping the cuts is not supported. This
matters because per-segment reporting *including* proximal/mid/distal is what SCCT and
CAD-RADS actually require, and it is the downstream task the project invokes to justify
per-branch labelling at all.

**Fix:** either scope a cardiac-landmark step (TotalSegmentator's heart-chamber tasks would
give the apex and plausibly the acute margin cheaply), or state plainly that
proximal/mid/distal reporting is **out of scope**, and stop offering it as a free future
extra.

---

### E8. The taper rule is already determined by the two datasets the project compares against, and the vault treats it as open

**Vault says:** `Proposed changes to the training plan.md:198-200` and
`Ostial definitions and segment endpoints in coronary imaging.md:42-46` — three "candidates"
(diameter <1.0 mm / visibility / follow-the-centerline), "pick one … and calibrate on 5–10
cases"; `:38` — "No published agreement on a bright-line rule for taper endpoints exists in
the literature I accessed."

**Actually true:** two of the four datasets that matter already state the same number.

| Dataset | Distal cutoff | Source |
|---|---|---|
| **ASOCA** | "All coronary vessels with a diameter **larger 1 mm**, representing 1–2 voxels, were included in the segmentation" — plus "In segments showing significant imaging artefacts … the rest of the vessel was ignored" | doi:10.1038/s41597-023-02016-2, PMC10006074 — **verified verbatim** |
| **ImageCAS-X** | side branches not traced where "the diameter at the most distal point was **<1 mm**"; extra D/OM branches only if ≥D1/D2 size or **>1.8 mm at the most proximal end** | arXiv:2608.30404 — **verified verbatim** |
| ImageCAS (original) | none stated; masks include plaque, pulmonary vessels, coronary veins | vault §1.5, [verified] |
| ARCADE | n/a — 2D X-ray projection; no diameter-based cutoff is even definable | PMC10764944 |
| CAT08 | **unreachable** (Schaap et al., Med Image Anal 2009;13(5):701–714; bigr.nl cert failure, Elsevier 403) | — |

So "diameter <1.0 mm at the most distal point" is not one of three equal candidates: it is
what ASOCA and ImageCAS-X both use, and it is the only choice that makes your numbers
comparable with either. The vault already cites the ASOCA paper in §1.1 of the consolidated
proposals without noticing it answers this question.

**And the vault did notice the cross-dataset-comparison risk in principle**
(`Ostial…md:28`) but did not check whether a mismatch exists — so it recorded the risk and
missed that the risk is already resolved in its favour.

**Fix:** write the rule as ImageCAS-X's, verbatim, in the annotation protocol: **trace to
the most distal point at which lumen diameter is ≥1 mm; do not trace a side branch whose
connection to the parent is unclear; extra D/OM branches only if ≥D1/D2 or >1.8 mm at
origin.** Add ASOCA's artefact clause (stop at an artefact that makes the rest unassessable)
— see E12. Then the 5–10-case exercise is a *training* exercise for annotators, not a
decision.

---

### E9. The taper calibration is under-powered and gated on the wrong statistic

**Vault says:** `Ostial…md:50` and `Research/Class schema/Proposed changes.md:118-121` —
"5–10 case spot-check … If agreement is >95% Dice, the rule is clear enough to proceed; if
<90%, the guideline needs exemplar images or rewording." And `Ostial…md:48` — the taper is
"lower-stakes than the bifurcation rule … the taper region is tiny voxel-wise".

**Actually true, two separate problems.**

1. **Dice is nearly blind to the thing being calibrated.** Take a vessel tapering linearly
   from 1.75 mm to 0.5 mm radius over 80 mm. Moving the cutoff from 1.0 mm to 1.5 mm
   diameter removes the last **16 mm of 80 mm of centerline (20%)** but only **19 of
   351 mm³ of volume (5.5%)**. A rule on which two annotators disagree about a fifth of
   every distal vessel would **pass** the vault's >95%-Dice gate. And the plan's own headline
   metrics are clDice and **branch detection rate** (`Training plan.md:136-138`) — both
   length-dominated. So the taper is **not** lower-stakes than carina ownership; on the
   metrics the plan says it cares about it is higher-stakes.
2. **n=5–10 cannot resolve it.** Endpoint pairs cluster by case and by annotator pair, so
   the effective n is roughly the case count. A 95% CI on a proportion at n=8 is about
   ±35 points; you cannot distinguish a 90%-agreement rule from a 70% one.

**Fix:** gate on **terminal-point distance (mm) per branch** and **clDice / centerline-length
ratio**, not whole-vessel Dice; and size the exercise by branch-endpoint pairs, not cases —
target ≥100 small-branch endpoints across ≥25 cases with two annotators, which is still
cheap and is the same overlap set the annotation protocol needs anyway.

---

### E10. `Ostial…md:20` gets CCTA resolution wrong by 3–4×, and the error is what makes the taper look low-stakes

**Vault says:** "CCTA imaging resolution is approximately **1.5 mm**, meaning smaller distal
branches approach or fall below the resolution limit." Framing throughout that note is
"sub-resolution taper".

**Actually true:** ImageCAS voxels are 0.29–0.45 mm near-isotropic (the plan's own
`Training plan.md:24`); ASOCA is 0.3–0.4 mm in-plane / 0.625 mm slice (verified); CAT08 is
0.32 × 0.32 × 0.4 mm. Clinical CCTA spatial resolution is ~0.4–0.6 mm in-plane. **1.5 mm is
the SCCT side-branch *naming* threshold** (segment 6: "first large septal or D1 >1.5 mm"),
not a resolution. A 1.9 mm distal LAD is 4–6 voxels across and well resolved; a 1.0 mm
branch is ~3 voxels across and visible. Also unsourced in that note: "main trunks measure
4.5 ± 0.5 mm" and "distal LAD 1.9 ± 0.4 mm" carry no citation.

**Fix:** correct the number and drop the "sub-resolution" framing; it is the premise behind
both E9's Dice gate and the "tiny voxel-wise" dismissal.

---

### E11. L-PDA and L-PLA are not a "risk" — they are unmeasurable, and the plan should say so

**Vault says:** `How many classes remain learnable given roughly 1000 cases.md:122-127` —
"a genuine open risk"; `Variant and absent branches.md:149-153` — keep them.

**Actually true:** on the sealed 160-case test set, L-PDA is present in 8 cases and L-PLA in
9. With the observed human per-class SD (L-PDA 29.0, L-PLA 27.2), the standard error of a
mean per-class Dice is 29.0/√8 = **10.3 points**. To detect a 5-point paired difference at
80% power with σ_d ≈ 15 you need ~71 cases *containing the class* — at 5% prevalence, ~1400
scans. This cohort has 800.

So no experiment run on this data can say anything about L-PDA/L-PLA Dice, and no ablation
(sampling, loss, ResEnc) can be adjudicated on them either. The vault's conclusion (keep
them) is still right — they are the only encoding of dominance in the label map and they cost
nothing to keep — but the *reason* is different and it changes what gets reported.

**Fix:** keep both classes; state in the plan that they are reported as **presence/absence
(dominance classification), never as per-class Dice**, and that the cohort cannot support a
Dice claim about them. Add a power note to the acceptance-thresholds work so nobody sets a
per-class Dice threshold on n=8.

**Related, and specific:** §2c's derived-dominance sanity check
(`Research/Class schema/Proposed changes.md:60-68`) is less diagnostic than advertised.
ImageCAS-X's co-dominance includes "a PDA from the RCA **without** a PLA from the RCA", so
the derivation reads *co-dominant* whenever **R-PLA** is missed — and R-PLA is present in
147/160 with human DSC 83.6. Imperfect R-PLA recall will inflate apparent co-dominance, so a
deviation from 91/5/4 is ambiguous between "the rare classes collapsed" and "R-PLA is
under-detected". Report the three-way confusion, not just the prevalence.

---

### E12. Lower-priority factual discrepancies

- **`Class schema options.md:324-326` and `:361-362` overstate "comparability".** The
  ImageCAS-X benchmark is **binary lumen only** — eight methods (TotalSegmentator, 3D-FFR-UNet,
  ADE-HTL, Swin-UNETR, ImageCAS, nnU-Net, nnU-Net+clDice, CAS-Net), all outputting a single
  foreground class, and Table 1's per-segment figures are **inter-observer only, with no
  per-segment model results**. Verified from the arXiv HTML. So there is **no published
  14-class voxel result to be comparable with**. What you get is a shared *schema* so that
  others can compare to you later — worth having, but it is not the comparability the vault
  claims, and it means the learnability question is entirely unanswered by the only source
  cited for it.
- **ARCADE numbers** (`SYNTAX segmentation and the ARCADE dataset.md:60`, `:75`, `:85`;
  proposals §2e at `:88-92`). Primary (PMC10764944): the `categories` field carries ids
  **1 to 26**, not 25; inter-rater Dice **0.62–0.97, mean 0.84**, not "0.73–0.90"; YOLOv8
  multiclass vessel segmentation **0.47** (best with contrast-enhanced images), not "0.49
  (original images)". None of this changes §2e's conclusion, but three numbers in a
  [verified]-adjacent note do not match the source.
- **AHA 1975 arithmetic.** Secondary sources put Austen et al. (Circulation 1975;51(4
  Suppl):5–40) at **15 segments**. SCCT is quoted as adding segment 17 (RI) and 18 (L-PLB) —
  15 + 2 = 17, not 18. Either the base is 16 or a third segment was added. The vault's
  `Class schema options.md:48-51` reproduces SCCT's "minimal alterations" sentence without
  reconciling the count. Cosmetic, but it is the kind of thing a reviewer will ask.

---

## 3. Weak reasoning and unsupported leaps

1. **"Costs nothing" (`proposals:192`) is false twice.** Beyond E1: (a)
   `Class schema options.md:286-289` says a 14-class model can be reported at trunk
   granularity "by relabelling its output". Relabelling the **argmax** is provably worse than
   arg max of **summed probabilities**: with p(LAD)=0.30, p(D1)=0.30, p(RCA)=0.35, argmax
   gives RCA (wrong tree); summing the left-tree group gives 0.60 > 0.35 (right tree). Merge
   in probability space, one line of code — that is the difference between "costs nothing"
   being true and false. (b) nnU-Net's `3d_fullres` default is Dice+CE with a soft Dice
   averaged over foreground classes; going 4 → 14 classes cuts each trunk's share of the
   Dice-term gradient from 1/4 to 1/14, a 3.5× reduction. Whether a 14-class model matches a
   purpose-trained 4-class model *at the 4-class task* is an empirical question nobody has
   measured, and the vault asserts the answer. Measure it — it is one extra cheap run and it
   is the only honest basis for the "free downward merge" claim.
2. **The learnability note reaches "no change to the schema decision"
   (`How many classes…md:113`, `:136`) from an admitted absence of evidence.** It states
   correctly at `:20-34` that no per-class-N rule exists, then argues from *what other groups
   chose* — which is a survey of conventions, not evidence about learnability — and from
   *human* per-class agreement, which bounds the ceiling but says nothing about whether a
   model reaches it. That is not wrong, but the note's confident closing ("Nothing here
   contradicts…") is stronger than its own content.
3. **Absence is treated as "the class has no voxels" and nothing more**
   (`Variant and absent branches.md:92`, `:169-173`). A 14-way softmax **cannot abstain**: it
   will place voxels somewhere in every case. So false-positive IM on the ~73% of cases
   without one is a specific, predictable failure that needs a per-case presence rule (e.g. a
   minimum connected-component volume) defined as part of the schema, not deferred to the
   metrics owner. Same for D2 (57%) and OM2 (29%).
4. **"Consistency matters more than ground truth" (`SCCT prose…md:51`) is used to close a
   question that E3 shows is substantive.** A deterministic rule that is systematically wrong
   is still systematically wrong; determinism buys reproducibility, not validity, and the
   plaque-attribution use case needs validity.
5. **`Ostial…md:36` invents an ImageCAS-X taper rule** — "Candidate rule (not stated as
   explicit policy): the manual correcters stopped labeling when the vessel became
   sub-resolution". The paper does state a rule (<1 mm distal diameter, E8). The note
   speculates where the source is explicit.

---

## 4. What's missing — extensions that would change a decision

Ranked.

1. **The fork the folder never opens: one-stage 14-class voxel model vs. binary lumen +
   centerline naming.** Every difficulty number the vault collected says the lumen is easy
   (human 92.8, nnU-Net 89.8) and the *naming* is hard (human 74–84 per branch; Hampe's
   model 0.74 overall). That is an argument for factoring the problem, not for one softmax.
   And `Training plan.md:103-104` **already licenses it** — "Graph reasoning is welcome
   downstream — branch naming on an extracted centerline" — with the correct guard ("must
   never be able to lose a vessel the voxel model found"). The §4 ruling against tree/graph
   models applies to them as the *primary segmenter*, not to naming a centerline extracted
   from the voxel model's own binary output. A two-stage design also delivers what E1, E7 and
   E11 say the one-stage design cannot: arbitrary re-merge granularity without retraining,
   proximal/mid/distal once landmarks exist, and presence/absence as a first-class output.
   This should be a decided comparison, not an omission. It is also nearly free: Phase 1's
   binary model is stage 1.
2. **Absent LM — the one case where a *trunk* class is absent.** Separate LAD and LCx ostia
   (absent left main) occurs in roughly 0.4–1% of people. The schema has no rule for it: LM
   is simply empty, which will read as a trunk-class failure on the classes the acceptance
   thresholds will be tightest on. The vault's absent-class analysis covers only IM and
   PDA/PLA. Needs one line in the protocol and an exclusion from the LM per-class mean.
3. **Stents, grafts, chronic total occlusions, and "not assessable".** ImageCAS is a clinical
   cohort. A stented LAD has an artefact-corrupted lumen; a CTO has no lumen distal to the
   occlusion; a bypass graft has no segment in SCCT's 18 at all. Under any taper or visibility
   rule these are indistinguishable from a vessel that simply ended — so the model is trained
   that vessels stop where disease is worst, which is precisely where per-segment reporting
   matters. The schema needs a **`not-assessable`** label (nnU-Net `ignore`) and a flag or
   exclusion for grafted cases. **ASOCA already does a version of this** ("In segments showing
   significant imaging artefacts affecting the vessel that would make further segmentation
   unfeasible, the rest of the vessel was ignored") — precedent the vault cites the paper for
   but did not pick up. Nothing in the 12 notes mentions stents, grafts or occlusions.
4. **Anomalous origin and course.** The schema assumes an LM from the left sinus and an RCA
   from the right. An RCA from the left cusp is still "RCA" and is fine. A **single coronary
   artery** or a **duplicated LAD** has no representation at all, and the `Other` class cannot
   absorb it under its own D3/D4/OM3/OM4 definition. Decide whether anomalous cases are
   excluded, flagged, or mapped, and check how many of the 800 are anomalous — the
   ImageCAS-X descriptors may already say.
5. **Verify the 2026 SCCT update before fixing the schema.** A newer version of the guideline
   the whole §2.1 rationale rests on exists: *Interpretation and Reporting of Coronary
   Computed Tomographic Angiography (2026 Update): An expert consensus document of the
   Society of Cardiovascular Computed Tomography*, J Cardiovasc Comput Tomogr 2026
   (ScienceDirect PII **S1934592526004806**). The vault cites only Leipsic 2014 and nowhere
   notes that an update exists. **I could not open it** (Elsevier 403 on both the article and
   a news summary), so I cannot say whether it retains the 18-segment model. If it changed the
   segmentation model or the nomenclature, "SCCT-derived" means something different and the
   published-comparability argument shifts. One library fetch closes this; it should happen
   before the schema is written into the plan.
6. **A bifurcation-connectedness metric, which the plan's metric list lacks.** *Same Branches,
   Different Trees: A Bifurcation Connectedness Metric for Coronary Artery Segmentation and
   FFR-CT Decision Agreement*, arXiv:2607.28327, defines a Bifurcation Connectedness Score
   (plus a differentiable soft-BCS for use as a loss term) for exactly the failure the plan
   cares about — "high Dice yet sever a bifurcation, dropping the downstream subtree and
   reversing the treatment decision", with an odds ratio of 2.16 [1.23, 4.18] for FFR-CT
   decision agreement in severe disease. This is directly relevant to a **multiclass** model,
   where the Voronoi wedge (E3) pinches the parent's label at every ostium and a class-label
   discontinuity can sever parent from daughter without either class losing much volume.
   Neither the class-schema folder nor `Training plan.md:136-139` has anything that detects
   this. Hand to the metrics owner alongside the Föllmer weighted kappa the vault already
   found.
7. **Measure the wedge, don't spot-check it by hand.** `SCCT prose…md:53` proposes "a
   hand-checked 5–10 case comparison … takes an afternoon". The right version is a script over
   all 800 imported cases: for every bifurcation in the shipped centerline tree, record branch
   angle θ, parent radius r, and the volume of parent-side lumen assigned to the daughter.
   That gives the real distribution of the E3 wedge, per class, for free, before any
   annotation decision. If the median diagonal wedge really is 10–16% of D1's volume, that
   alone justifies changing the assignment rule.

---

## 5. Confidence, and what I could not check

**High confidence:** ImageCAS-X's schema, class IDs, protocol quotes, dominance counts
(729/41/30), split (560/80/160), the 41.8% figure, and the binary-only nature of its benchmark
— all read from the arXiv HTML, and the vault's transcription is accurate everywhere I
checked. Hampe's 10 classes and per-class F1 — read on PMC11095121, matches the vault exactly.
ASOCA's 1 mm cutoff and the 85.6 ± 7.7% binary-lumen figure — read verbatim on PMC10006074.
The E1/E2 merge and "Other" arguments follow from the verified class definition and need no
further source.

**My own arithmetic, not measured:** the E3 bifurcation geometry (`d > s·tan(θ/2)`,
`s* = r/tan(θ/2)`, `V = (2/3)r³/tan(θ/2)`), the Dice-loss estimates, the E9 taper
volume-vs-length split, and the E11 power calculation. These are derivations from the stated
rule and stated numbers. They are falsifiable by the script in extension 7, and that is how
they should be settled.

**Unreachable (not confirmed, not refuted):**
- **SCCT 2014 full text / Appendix 1 verbatim** — Elsevier 403 on the journal, and the
  SCCT-hosted PDF the vault says it read was not reachable for me. The 18-segment list and the
  "segment 17 = ramus intermedius, segment 18 = left posterolateral" additions are corroborated
  by independent secondary sources; the individual boundary wordings in
  `Class schema options.md:57-77` are **unverified by me**. Given how much of §2.1 rests on
  them, one reviewer with library access should read Appendix 1 directly.
- **SCCT 2026 update** — exists (PII S1934592526004806); its segment model unreachable.
- **CAT08 / Schaap et al. 2009 distal-endpoint definition** — bigr.nl TLS certificate failure,
  Elsevier 403. So the E8 table has a hole; I did not assume a value.
- **Austen et al. 1975 full text** — not opened; the 15-vs-18 arithmetic is from secondary
  sources.
- **ImageCAS-X's actual released label maps** — not downloaded. Every claim about what the
  labels contain is from the paper. The vault's own open items
  (`Variant and absent branches.md:176-182`: does `Other` absorb a quadrifurcation's extra LM
  branch; do co-dominant cases have both R-PDA and L-PDA non-empty) can only be closed against
  the files, and both bear on E1 and E11.
- **Whether any published work trains a ≥10-class voxel coronary segmenter with per-class
  Dice** — I searched and found none; every multiclass work I reached (Hampe, Ren, Li, TopoLab,
  CPR-GCN, and the 2025–26 X-ray works) labels centerlines or 2D projections. So the vault's
  statement that "no published work validates one schema against another on the same data" is,
  as far as I can establish, correct — and the stronger statement is also true: **nobody has
  published a per-class Dice for a multiclass CCTA voxel segmenter at all.** That is an
  argument for doing it, and an argument for not assuming it works.
