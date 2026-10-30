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
  (spheres) and against continuum truth on 24 real 0.5 mm walls. ⟨E9 one-line⟩
- **Item 3:** E10 re-runs Lima's E3 unchanged, with a segment shape and cv_n measured on 0.5 mm walls and a
  measurement error tied to JA8's acceptance edge. ⟨E10 one-line⟩ JM-0R's own `cv_n` and shape then replace these,
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

⟨E9 section⟩

## 5. Item 3: Lima's E3 with a measured shape and cv_n (E10)

⟨E10 section⟩

## 6. Item 4: the three `role:swe` specifications

These are written to be pasted into issues on this path (label `path:jm-rest-ccta`), built on `jm/rest-ccta`.

### 6.1 The JA15 estimator module (fixture of #170)

- **`janusm.measure`** (or inside `janusm.geometry`), pure numpy and scipy, one implementation used by the harness,
  the read checks, the anchoring report and the scorer:
  - `assd(ref, test, spacing, border)` — symmetric surface-voxel ASSD on the myocardium-facing border (endocardial:
    LV-pool voxels touching label 1; epicardial: label-1 voxels touching labels 0, 3 or 4);
  - `signed_bias(ref, test, spacing, border)` — **⟨E9 winner⟩**;
  - `segment_thickness(labels, spacing, affine)` — per AHA segment, ⟨E9 thickness winner⟩ of d_endo + d_epi − h; JA8's
    co-primary is the median over segments 1–16 of |model − mean read|.
- **Tests** (from E9; tolerance ±0.05 mm unless stated):
  - spheres, r_p 15–25 mm, wall 6–11 mm, random sub-voxel centre, 0.5 mm grid, one border moved by ±0.3 and ±0.5:
    `signed_bias` within ±0.05 (⟨E9 sphere numbers⟩); `segment_thickness` change within ±0.05; `assd` within
    ⟨E9 assd tol⟩ of |b| (its known +0.04 voxel bias is documented, not hidden);
  - `janusm_reads.phantom.heart` with `move_border(…, ±0.5)`: the same, both borders;
  - a constant-shift and a random-field case from `harness_r2.py`'s U, with E9's continuum truth.
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
| ⟨E9 change row⟩ | ⟨⟩ |
| The first 20 decision double reads | §6.3 RC and κ, E8 seal size, then the reference config is built and pinned |
| R2 fails | Thinning ships only after the hand-measurement alignment |

## 12. Citations

All carried from Rounds 1–2, as checked there (JA14, JA24). New in this round: none.

- **[Bland 1986]** Bland JM, Altman DG. *Lancet* 1986;1(8476):307–310. doi:10.1016/S0140-6736(86)90837-8. RC.
- **[Cury 2022]** CAD-RADS 2.0. *J Cardiovasc Comput Tomogr* 2022;16(6):536–557. doi:10.1016/j.jcct.2022.07.002.
- **[Kurata 2015]**, **[Ide 2017]**: whole-territory Voronoi (nearest-vessel) mass (JA24).
- **[Lima E3]**: `experiments/JanusM/Lima/calibrate_sim.py`, imported unchanged by E10.
