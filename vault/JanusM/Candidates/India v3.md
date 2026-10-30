---
aliases: [India v3]
tags: [janus-m, plans, candidate, round-3, india, myocardium, path-rest-ccta]
status: submitted
round: 3
path: jm/rest-ccta
advocate: India
updated: 2026-10-30
issue: christianGRogers/Asclepius#167
---

# India v3: path A, ready to apply the moment JM-0 reports

**Advocate:** India. **Round:** 3, path `jm/rest-ccta` (LQ1 option A). **Base:** the master plan in force:
[[Hotel v2]] with JA1–JA24 ([[Janus-M Round 1]], [[Janus-M Round 2 rest-ccta]]). **Evidence:**
[[India - R3 E9-E10 estimators validated, detectable depth, and the JM-0R rules]] (code `experiments/JanusM/India/`,
numbers `results/e9_estimators.json`, `results/e10_detectable_depth.json`).

## 1. The plan in one paragraph

India v3 changes nothing structural. It settles ruling R2 §7 items 2–5 and pre-registers item 1:
- **Item 1** becomes a script, `jm0r_rules.py`. It turns JM-0R's aggregates, or the three fallback add-ons', into
  the ten decisions the rulings pre-register, and it was written before any output exists.
- **Item 2:** E9 tests every candidate implementation of ASSD, signed bias and segment thickness against exact truth
  (40 spheres) and against continuum truth on 24 real 0.5 mm walls. **The volume estimator (ΔV / A) passes JA16's
  test**: a known 0.5 mm shift in each direction, on each border, recovered to within ±0.05 mm in ≥ 96 % of real
  walls and all spheres. **So the signed-bias guard becomes 0.3 mm** (with an outward under-read of up to 0.05 mm
  near 0.3 mm, disclosed). India R2's voxel-centre estimator fails it
  everywhere and must not be used.
- **Item 3:** E10 re-runs Lima's E3 unchanged, with a segment shape and cv_n measured on 0.5 mm walls and a
  measurement error tied to JA8's acceptance edge. The measured shape matches Lima's (r = 0.97); cv_n = 0.053.
  At the error of a model on JA8's edge, rule C finds 80 % of territories thinned by **≈ 30 %** (35–40 % if cv_n
  is really 0.10), with ≤ 3.6 % of null patients flagged. JM-0R's own `cv_n` and shape then replace these,
  through R9 of the rules script.
- **Item 4:** the table writer, the reference-population config and F1's RC per territory, specified as three
  `role:swe` issues (§6).
- **Item 5:** protocol v1, final, with the six changes the built queue (#155, #161) needs to match JA21 (§7).

## 2. What is unchanged

JA1–JA24 as ruled: four learned classes; equal-thickness depth; fixed sectors with the septal-arc column; Euclidean
territories with "shared"; ImageCAS-X train only; the frozen `configs/janusm/sealed-r1.json`; two reads per seal and
decision case; JA8 with JA16's final margins; Janus-M 0 = seed + geometry, Janus-M 1 only if it fails; Stage A signs
calibrated for specificity only (JA18); Tables A and B (JA19); JM-0R as one CPU job (JA23).

## 3. Item 1: the pre-registered decision procedure for JM-0 / JM-0R

**It runs when the lead posts JM-0R's aggregate JSON on #142** (or the three fallback scripts' JSONs, JA23):

```sh
python experiments/JanusM/India/jm0r_rules.py JM0R.json --sig-m <E10's sig_m at JA8's edge> --out decisions.json
# fallback, if the lead ran the three committed add-ons instead (missing ones as '-'):
python experiments/JanusM/India/jm0r_rules.py --fallback lima_summary.json india_addon.json hotel_aggregate.json \
    --sig-m <...> --out decisions.json
```

It is CPU-only, reads aggregates only (no case, no image), and anyone may run it, the judge included. It applies:

| Rule | Input (JM-0R key) | Decision, fixed now |
|---|---|---|
| R1 halves (JA2) | `halves_segment_share` | Per segment, as the module computes; if > 25 % of segments, Table A's header states the layer count per segment |
| R2 thickness definition (Hotel v2 §4.4) | `thickness_median_mm` | Pass if within 4.2–8.0 mm (1.5 mm of 5.7–6.5). Otherwise no thinning flag ships until readers hand-measure 20 decision cases and the definition is aligned |
| R3 seed offsets (JA16, JA17) | `endo_/epi_halfmax_offset_mm_median` | \|endo\| > 0.25 mm: TPR needs the snap tool. Either > 0.5 mm: request the ≈ 100 training reads at the first decision look. Either > 0.3 mm: the seed is expected to fail the 0.3 mm guard (if §4 validates it) |
| R4 rest TPR (JA17) | edge, endo offset, guarded free-wall TPR | Edge > 2 mm: not computed. Edge ≤ 1.5, \|endo\| ≤ 0.25 and TPR 0.99–1.15: shown as a z-score. Edge and TPR pass but offset fails: shown only after the snap tool. Otherwise research export only. The share < 0.99 is printed, never gated |
| R5 fat cut (JA18) | `fat_grid` | The least strict (c, V) with ≤ 5 % of hearts carrying a cluster, in the order c = 0, −30, −50, −100 HU, and V = 5, 20, 50 mm³ within each c; then Hotel's patient-noise candidate. Provisional; fixed once on the reference population |
| R6 septal-arc column (JA20) | `septal_arc_mass_changed_median` | Kept if ≥ 10 % of mass changes segment; else dropped |
| R7 geodesic (JA20) | `geodesic_segments_changed_share` | ≥ 10 %: Table B adds geodesic mass beside Euclidean, Euclidean stays primary, and the lead rules (LQ13). Else geodesic is dropped |
| R8 AHA failures (JA3) | `aha_frame_fail_share` | A failing case shows "AHA frame failed" and no segment table. > 10 % of cases: a `role:swe` fix before any read |
| R9 detectable depth (JA18) | `cv_n`, `segment_shape`, sig_m | E10's `detectable_depth()` with JM-0R's inputs; the page prints the result (§5) |
| R10 ET vs Laplace (JA20) | `et_laplace_third_agreement_median` | Reported only |

**Fallback mapping** (`merge_fallback`): every sign convention is reconciled to "+ = label border outward of the
image edge". Hotel's endocardial offset is + into the blood, so it is negated. The fallback TPR is Hotel's fixed 1 mm
guard, not JA17's adaptive band, and the decision says so.

**The JM-0R output contract** (proposed for #169, so that the rules read it without a mapping): the keys in the
table above, as aggregates over the 40 cases (median unless named), plus `n_ok`. All other JM-0R outputs stay as
JA23 lists them.

## 4. Item 2: the JA15 estimators, validated (E9)

**Set-up.** Each candidate implementation is run on binary masks only (as a read or a model gives them) and compared
with a truth that does not depend on voxels:
- **40 spheres** (pool radius 15–25 mm, wall 6–11 mm, random sub-voxel centre, 0.5 mm grid), one border moved by
  ±0.3 or ±0.5 mm: the truth is exact;
- **24 real walls** (public TotalSegmentator v1 shapes on JA15's 0.5 mm grid, after `janusm.guard.refuse`), one
  border's SDF moved by ±0.3 or ±0.5 mm, alone or with independent random fields (RMS 0.25 mm, 8 mm) on both
  borders. The truth is the **continuum** mean outward displacement of the zero level set (ΔV / A on the continuous
  fields, by the coarea formula), because the zoomed SDF's slope is not 1 (median |∇| 1.05).

**Signed bias, error = estimate − truth (mm), a 0.5 mm shift, no random field:**

| Estimator | Spheres: worst median (share within ±0.05) | Real walls: endo in / out, epi in / out, median (share within ±0.05) |
|---|---|---|
| Voxel centres (India R2) | 0.12 (0 %) | −0.07 (0 %), −0.13 (0 %), −0.08 (0 %), −0.11 (0 %) |
| Symmetrised voxel centres | 0.04 (100 %) | +0.01 (100 %), −0.05 (63 %), −0.01 (100 %), −0.02 (100 %) |
| **Volume, ΔV / Ā** | **0.001 (100 %)** | **−0.02 (96 %), −0.03 (100 %), −0.02 (100 %), −0.01 (100 %)** |

- **JA16's test, as written** ("recover a known 0.5 mm shift, in each direction, to within ±0.05 mm in the JA15
  harness"): **the volume estimator passes.** The 0.3 mm guard applies, measured by it.
- **Its residual error, disclosed.** On real walls the volume estimator reads consistently **0.01–0.09 mm too far
  inward** (median error −0.006 to −0.029 at 0.5 mm; −0.04 to −0.09 at 0.3 mm; down to −0.08 with random error on
  top). For the guard this means:
  - an **outward** bias is read up to ≈ 0.05 mm low (worst medians: −0.047 endo, −0.041 epi at 0.3 mm), so a true
    outward bias of up to ≈ 0.35 mm can pass a 0.3 mm guard;
  - an **inward** bias is read up to 0.09 mm high, so the guard fires early, never late.

  The guard is therefore stated as "0.3 mm, with ±0.05 mm at 0.5 mm shifts and up to 0.05 mm outward
  under-reading near 0.3 mm", not as an exact bar.
- **Realised vs nominal shifts.** A nominal 0.5 mm SDF shift realises 0.94–0.99 of itself on the endocardium and
  0.84–0.90 on the epicardium (where 1.5 mm staircase labels meet the RV). E5's bias rows were nominal; JA15 already
  indexes by realised ASSD, so no ruling changes.

**ASSD.** Voxel-surface ASSD reads high by +0.04 mm (0.5 mm shift) and +0.06 mm (0.3 mm) on spheres; on real walls,
+0.04 to +0.09 mm at 0.5 mm. The surface-voxel convention costs about one-tenth of a voxel at every comparison. JA8 decides on
d = model-vs-read − read-vs-read, in which this common offset largely cancels. **One implementation is chosen:
`segtrain.metrics.surface_distances`**, the one `janusm_reads.anchoring` already uses. The myocardium-facing
variant differs from it by ≤ 0.05 mm.

**Segment thickness.** The JA2 thickness (d_endo + d_epi − h, median over the segment's voxels, then the median over
segments 1–16) recovers sphere shifts within ±0.007 mm. On real walls it agrees with the approximate truth (the
difference of the two continuum border shifts) within 0.07 mm at 0.5 mm and 0.11 mm at 0.3 mm. The mean-over-voxels
and mid-wall variants are no better, so **JA8's definition stays**.

## 5. Item 3: Lima's E3 with a measured shape and cv_n (E10)

**Measured on 22 public hearts, JA15's 0.5 mm walls** (`e10_detectable_depth.py`):
- **Segment shape** (median thickness ÷ the heart's median, segments 1–16): r = 0.97 with Lima's 1.5 mm self-test
  shape; the largest difference is 0.08.
- **cv_n = 0.053** (robust SD of log relative thickness after the shape). Label error adds to it and model smoothing
  removes from it, so it is neither bound; Lima swept 0.06–0.15.
- **The measurement error at JA8's edge.** Under U, segment-thickness error SD is **0.24 mm** at a realised ASSD of
  0.21 mm and **0.43 mm** at 0.36 mm. A model accepted by JA8 (d ≤ 0.25 mm over read-vs-read) sits around the second.

**Lima's E3, unchanged, with these inputs** (mixed phase, prevalence 0.1, rule C, ≤ 5 % null patients flagged):

| cv_n | sig_m 0 | sig_m 0.24 mm | sig_m 0.43 mm | Null false-flag rate (max over depths) |
|---|---|---|---|---|
| 0.053 (measured) | 20 % | 25 % | **30 %** | ≤ 3.6 % |
| 0.06 | 20 % | 25 % | 30 % | ≤ 3.5 % |
| 0.10 | 35 % | 35 % | 40 % | ≤ 3.5 % |

(Depth: the relative thinning at which rule C finds ≥ 80 % of infarct territories. The measured and Lima's shapes
give the same depths. All-end-diastolic gives the same as mixed phase: rule C cancels phase, as Lima found.)

**What the page prints, provisionally:** "In simulation, this rule finds about 80 % of territories thinned by 30 %
or more; it is not a sensitivity." JM-0R's `cv_n` and shape replace these inputs through R9 (§3), and the reads' RC
replaces sig_m once the first 20 decision double reads exist (§6.3).

**The composite pattern's population rate** needs seeds on the reference population (LQ12). None exist, so it is
computed by the reference builder (§6.2) and printed there.

## 6. Item 4: the three `role:swe` specifications

These are written to be pasted into issues on this path (label `path:jm-rest-ccta`), built on `jm/rest-ccta`.

### 6.1 The JA15 estimator module (fixture of #170)

- **`janusm.measure`** (or inside `janusm.geometry`), pure numpy and scipy, one implementation used by the harness,
  the read checks, the anchoring report and the scorer:
  - `assd(ref, test, spacing, border)` — `segtrain.metrics.surface_distances` on the border's object (endocardial:
    label 2; epicardial: labels 1 + 2), as `janusm_reads.anchoring` already does;
  - `signed_bias(ref, test, spacing, border)` — **ΔV / Ā**: the signed voxel-count change in a 2 mm band
    around the myocardium-facing border, divided by the mean of the two borders' areas (marching cubes on each mask
    smoothed by one voxel, the faces in the band);
  - `segment_thickness(labels, spacing, affine)` — per AHA segment, the median over voxels of d_endo + d_epi − h; JA8's
    co-primary is the median over segments 1–16 of |model − mean read|.
- **Tests** (from E9; tolerance ±0.05 mm unless stated):
  - spheres, r_p 15–25 mm, wall 6–11 mm, random sub-voxel centre, 0.5 mm grid, one border moved by ±0.3 and ±0.5:
    `signed_bias` within ±0.01 (E9: ≤ 0.002); `segment_thickness` change within ±0.02 (E9: ≤ 0.007);
    `assd` within +0.08 of |b| (its known +0.04 to +0.06 surface-voxel offset is documented, not hidden);
  - `janusm_reads.phantom.heart` with `move_border(…, ±0.5)`: the same, both borders;
  - two real walls from E9 (a ±0.5 mm shift per border), with E9's continuum truth: `signed_bias` within ±0.05.
- **Version:** `GEOMETRY_VERSION` bumps when any of the three changes a number.

### 6.2 The reference-population config (JA18)

`configs/janusm/reference-r1.json`, sha256-pinned in the guard's `PINNED`, written by
`tools/janusm/build_reference.py` (new), merged **before any seal read**:

| Field | Content |
|---|---|
| `cases` | The 420 ImageCAS-X train cases left after seal, decision and JM-0 (from `sealed-r1.json`), with its sha256 and `splits.json`'s |
| `borders` | Which model (Janus-M 0 = `heartchambers_highres` version + `GEOMETRY_VERSION`; or Janus-M 1's checkpoint hash) |
| `phase_note` | "this population, phase-uncertain" (JA18) |
| `thinning` | Rule C (Lima E3): the 16-segment shape vector, the per-segment right-half scales, the cut k and the null false-flag rate it achieves (≤ 0.05) |
| `hypoattenuation` | The same rule on guarded core HU relative to the patient's remote median, guard = JA17 band |
| `fat` | The final (c, V), from R5's order, and its null rate |
| `composite` | The measured per-patient rate of Hotel's composite; whether it needs two contiguous segments (> 5 %) |
| `rc` | F1's RC per sign per territory (§6.3), with n and its 95 % CI |
| `kappa` | Read-to-read κ per sign (JA18), on the decision set |
| `construct` | The four construct-check results (JA18), never used to tune |
| `detectable_depth` | R9's printed number, with its inputs |
| `guard_purpose` | `reference`: the builder calls `janusm.guard.refuse(cases, purpose=…)` first and refuses any seal, decision or JM-0 case |

### 6.3 F1's repeatability coefficient per territory (from the reads)

On the **first 20 decision cases with two reads**, for each sign s ∈ {thinning, hypoattenuation, fat} and each
territory T ∈ {LAD, LCx, RCA}:
1. Compute the sign's patient-relative deviation, D = (territory mean − remote median), on read 1's borders and on
   read 2's. Segments come from each read's own AHA frame (frame jitter is part of read noise); the territory map
   comes from the same ImageCAS-X reference tree for both reads (JA4).
2. Δ = D₁ − D₂ per case. RC_T = 1.96 × SD(Δ) (Bland & Altman 1986: RC = 1.96 × √2 × single-read SD).
3. **Heteroscedasticity check:** if Spearman ρ(|Δ|, mean D) > 0.4, RC is computed on log ratios and applied
   multiplicatively.
4. Report RC_T with its 95 % CI (χ² on n − 1 = 19 df); the **point estimate** is the F1 floor (JA18), and the CI is
   printed beside it.
5. A territory whose RC exceeds the thinning cut's own scale (the rule C cut × the segment scale, in mm) cannot flag
   at all; that is reported, not hidden.

The same 20 cases give κ per sign (JA18's gate) and set the seal size (JA16, E8). No other use.

### 6.4 The table writer (JA19)

`janusm.table` (new): `write_tables(case_id, labels, ct, spacing, affine, coronary, reader_grades, reference)` →
a JSON document and a rendered one-page HTML (Tables A and B, the header, the bull's-eye), deterministic for fixed
inputs:
- **Header:** phase ("unrecorded" on ImageCAS), spacing, endocardial 10–90 % edge and half-maximum offsets, AHA
  orientation and septal arc, territory source, `GEOMETRY_VERSION`, the reference config's sha256, and R9's
  detectable-depth sentence.
- **Table A** (17 rows × layers): JA19's columns. A thinning, hypoattenuation or fat **flag** is printed only if
  rule C (territory, contiguous), F1 (RC) and κ all pass; otherwise the value and its population percentile are
  printed, never a flag. Rest TPR only if R4 allows it.
- **Table B** (LAD, LCx, RCA): the reader's CAD-RADS 2.0 grade of the worst lesion (typed in the read queue; never
  computed), patient-specific mass and share with the AHA-default mass beside it, segments with "shared" (share
  < 0.6), flags, and **one of Hotel's four fixed phrases**, chosen by a table of (grade ≥ CAD-RADS 3, pattern
  present) and never free text.
- **Every cell** carries "research output, not validated: no scar or perfusion reference".
- **Never written:** a sensitivity, "scar", "ischaemia", 5.5 mm, −10 HU or 0.99.
- **Guard:** `janusm.guard.refuse([case_id], purpose=…)` first; seal cases only under seal scoring.
- **Tests:** the phantom heart with a planted thin, fat territory gives the "chronic-infarct-like geometry" phrase,
  and the same phantom without it gives "no geometric sign"; a missing reader grade prints "not graded", never a
  guess.

## 7. Item 5: protocol v1, final, and what the queue must change

**Protocol v1** is Hotel v2 §5.4 items 1–7 with JA21's settlements. The final text for the queue:

1. **Labels (JA1):** 1 LV myocardium (compact wall, septum included); 2 LV blood pool; 3 RV blood pool; 4 LA blood pool.
   Nothing else is drawn.
2. **Papillary muscles and trabeculae are label 2.** The endocardium is the compact-wall surface; where trabeculae
   merge with it, the border goes at the outer edge of the blood-filled recesses.
3. **Half-maximum rule.** Each border lies halfway in HU between its two plateaus (blood/core myocardium; core
   myocardium/epicardial fat on the free wall; core myocardium/RV blood on the septum).
   - **Window:** plateau-centred by default: level = (p₁ + p₂)/2, width ≈ 1.5 × |p₁ − p₂|, from the seed's plateaus.
   - **Check at submission:** median offset per border ≤ **0.5 mm**: accepted. Above: returned **once** with the
     profile plot; a second failure is accepted and **flagged**.
4. **Basal limits.** LV pool and myocardium end at the mitral annulus plane and the aortic valve plane. The LA runs to
   the mitral annulus; pulmonary veins and **the appendage are excluded beyond their ostia**. **Check:** labels 2 and
   4 never touch, and label 2 extends ≤ 3 mm above the fitted mitral plane.
5. **RV pool** from the tricuspid annulus to the pulmonary valve, trabeculae included.
6. **Seeds** coarsened to 2 mm and smoothed; 10 of 60 seal cases read from blank; no other model output is shown.
7. **Per vessel (LQ10 a):** the reader types the CAD-RADS 2.0 grade of the worst lesion in LAD, LCx and RCA, and may
   mark one lesion point per vessel. About 1–2 min per case (estimate).

**Anchoring (per wave, JA21), fixed now:**
- per border, gap = mean seed-vs-read ASSD on blank reads − mean seed-vs-read ASSD on seeded reads; seeded reads cannot
  accept a model if the **upper 95 % bootstrap bound** of (gap − mean seeded inter-read ASSD) exceeds **0.2 mm**
  (cases resampled, blank and seeded independently, 2,000 draws);
- a wave in which more than half of the seeded reads change < 5 % of seed voxels is flagged, and the reader re-reads
  one blank case before continuing.

**What the built queue must change to match JA21** (a `role:swe` issue on `dev`, where #155 and #161 live):

| # | Where | Now | Protocol v1 |
|---|---|---|---|
| 1 | `janusm_reads/checker.py` `CheckConfig.tolerance_mm` | 1.0 mm, fail | 0.5 mm; return once; second failure accepted and flagged (needs a per-read "returned" counter in the queue state) |
| 2 | `checker.check_conventions` | LV–RV pool contact, holes, islands | add: labels 2 and 4 never touch; label 2 ≤ 3 mm above the fitted mitral plane (least-squares plane of LV-pool voxels touching LA) |
| 3 | `janusm_reads/anchoring.py` `wave_report` | point-estimate gap > inter-read (placeholder) | the bootstrap rule above, 0.2 mm; plus the changed-share rule (> half of reads < 5 %) |
| 4 | `slicer/JanusMRead` | opens at window 800 / level 300 | opens plateau-centred from the seed's plateaus |
| 5 | `janusm_reads/protocol.py` submission | labels only | adds per-vessel CAD-RADS 2.0 (0, 1, 2, 3, 4A, 4B, 5, N) and an optional lesion point (world mm) |
| 6 | protocol text in the reader README | appendage not stated | "LA appendage excluded beyond its ostium" (JA21) |

## 8. Assumptions carried (LQ2–LQ12, the rulings' recommendations)

| Question | Assumed |
|---|---|
| LQ2 | LV myocardium + LV, RV, LA pools |
| LQ3 | `heartchambers_highres` under its non-commercial licence, key typed by the lead |
| LQ4 | ImageCAS-X train 560 + quality-0 180 |
| LQ5 | 200 double reads + 10 blank, separate queue, after the coronary wave-1 start |
| LQ6 | MM-WHS, external check only, low priority |
| LQ7 | Released coronary patients: training only, by PR |
| LQ8 | s0655: coronary seal kept |
| LQ9 | Round 1 twins: a note on the record, no seal change |
| LQ10 | Readers type a per-vessel CAD-RADS 2.0 grade (a) |
| LQ11 | JM-0R once after Job JM-0, or the fallback if JM-0 returns first |
| LQ12 | Seeds on the reference population become committed (≈ 12 GPU-h) |
| **LQ13 (new, conditional)** | Only if R7 fires (≥ 10 % of segments change territory): which territory rule is primary. Recommendation: Euclidean, since it is what Kurata 2015 and Ide 2017 validate (JA24) |

## 9. Compute

Unchanged from the ruling: JM-0 ≤ 1 GPU-h; JM-0R 0 GPU-h (CPU, ≤ 2 h); seeds on seal + decision ≈ 2; reference seeds ≈
12 (LQ12); Janus-M 1 ≈ 55 only if Janus-M 0 fails. `jm0r_rules.py`, E9 and E10 are CPU, here.

## 10. Held-out disclosure (this round)

- Every case E9 and E10 opened went through **`janusm.guard.refuse_one(sid, source="TotalSegmentator")`** (the
  shared guard, JA22) before any byte was read, and also through India's R2 guard inside the loader. Both agree on all
  299 local public subjects: 0 refused.
- The cases are **public TotalSegmentator v1 masks fetched in Round 2 after the twin rule**; no Round 1 list was
  reused (JA22). No CT was read in Round 3.
- No held-out subject, twin, ImageCAS case or pool case was opened.

## 11. What would change this plan

| Result | Change |
|---|---|
| JM-0R arrives | `jm0r_rules.py` runs; its ten decisions replace the "undecided" rows; R9's depth goes on the page |
| The JA15 module's `signed_bias` fails its fixture tests (§6.1) | The guard falls back to 0.5 mm (JA16) until it passes |
| The first 20 decision double reads | §6.3 RC and κ, E8 seal size, then the reference config is built and pinned |
| R2 fails | Thinning ships only after the hand-measurement alignment |

## 12. Citations

All carried from Rounds 1–2, as checked there (JA14, JA24). New in this round: none.

- **[Bland 1986]** Bland JM, Altman DG. *Lancet* 1986;1(8476):307–310. doi:10.1016/S0140-6736(86)90837-8. RC.
- **[Cury 2022]** CAD-RADS 2.0. *J Cardiovasc Comput Tomogr* 2022;16(6):536–557. doi:10.1016/j.jcct.2022.07.002.
- **[Kurata 2015]**, **[Ide 2017]**: whole-territory Voronoi (nearest-vessel) mass (JA24).
- **[Lima E3]**: `experiments/JanusM/Lima/calibrate_sim.py`, imported unchanged by E10.
