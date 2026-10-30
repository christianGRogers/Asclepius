---
tags: [janus-m, plans, candidate, round3, paired-scar, scar, LIE, LGE, registration, power, forms]
author: Golf
round: 3
version: 3
path: jm/paired-scar
updated: 2026-10-30
issue: christianGRogers/Asclepius#179
---

# Golf v3: strike what fails on one benchmark, power the study on its binding endpoint, and fix the forms first

*Path `jm/paired-scar` (LQ1 option B). A complete Janus-M plan. The base is the path master plan: [[Kilo v2]] with
JA25–JA36, plus path A's JA15–JA24 for Stage A (JA25). This plan settles §7 items 1–7 of
[[Janus-M Round 2 paired-scar]].*

## 1. The plan in one paragraph

**Path B stays Kilo v2 + JA25–JA36. Round 3's evidence moves the plan's weight from the scar rule to the
registration and the reference.**
- **The scar rule** (shared benchmark + Golf E8, §4):
  - **P-K is struck** on both;
  - **P-J survives, but only on the 3 SD E-D voxel cut.** With the half-way cut, its sensitivity is ≤ 0.73;
  - **P-G as JA30 defines it holds:** 0.75–0.81 / 0.98–1.00 after affine (E8). Its sensitivity is not spill
    (≤ 0.05); spill costs specificity instead. The benchmark's P-G strike scored a P-G without its 1 mm exclusion,
    and P-G passes there too with a 4 mm mask;
  - **both P-J and P-G go to development**, where JA30's choice rule picks;
  - JA30's P-G misses most bin-1 scars, so its pooled sensitivity follows the cohort's bin-1 share.
- **Registration, not the rule, limits the Kim bin** (both runs agree). On exact borders, every extent measure is
  nearly right. JA29's chain, which stops at R0 when QC passes and vetoes affine by QC, doubles the extent error
  against always-affine (E8). On the benchmark, the 10 mm mask leaves 1.2 mm against 0.3 mm with 4 mm, and the QC
  shares barely tell good registrations from bad ones. Golf proposes:
  - always rigid → affine, with QC values as reader flags (§8.2);
  - the mask margin set by the benchmark (4 mm);
  - Juliet's `rim_dark` as the phase check (AUC 0.98–0.99).

  That also brings whole-patient failure to the ≈ 2 % that the specificity endpoint needs (§8.3).
- **The transmurality endpoint decides the study, and patients cannot buy it (E10, §5).** At 160 patients it needs
  the CT's Kim-bin agreement to at least equal the LGE readers' own. Golf proposes four things:
  - the anchor from every patient's double read;
  - closing the 0.60-floor loophole;
  - a seal sized by the ≥ 270-segment floor at 70 % enrichment (≈ 120–130 patients);
  - Scar-1 triggered on extent if development misses by > 0.03.
- **What the cohort needs is now concrete and checkable:** the LGE read form and the registration check form
  (§6, with a mock-up and entry times), the intake checker's DICOM fields and outcomes (§7), and a truth-free phase
  flag (§8.2).
- **Stage A** is one implementation (§9): the shared code is byte-identical on `dev` and both paths. Nothing on Stage
  A changes; path A's Round 3 amendments arrive with the code.

## 2. Evidence this round (CPU; code in `experiments/JanusM/Golf/`; notes in `vault/JanusM/Experiments/`)

- **E8 + E9, the JA30 menu, the spill share and a phase check, on 22 real hearts** (Golf's generator, a cross-check
  beside the shared benchmark).
  [[Golf - On real hearts P-G is the only presence rule that holds, its sensitivity is not spill, and the registration chain, not the rule, limits the Kim bin]]
  - `lie_menu.py`, `lie_menu_summary.py`; results `lie_menu.json`, `lie_menu_raw.json.gz`.
  - 22 hearts × 3 motions × 3 blood levels × 2 CNR; R0, rigid, affine, the emulated chain, and exact borders; every
    LIE also scar-free and with blood at remote.
- **E10, the merged power study at the JA32 bars**, with two simulated LGE readers and the reader-anchored
  transmurality bar.
  [[Golf - At the JA32 bars the transmurality endpoint, not sensitivity, sets the paired seal, and it needs CT bin agreement at least equal to the readers']]
  - `power_ja32.py`; results `power_ja32.json` (84 cells × 1000 studies) and `power_ja32_sweep.json`.
- **Forms and reader time:** `forms/lge_read_form.json`, `forms/reg_check_form.json`, `forms/mockup.html`, and
  `forms/klm_time.py` → `klm_time.json`.
- **The shared benchmark** (Juliet's `bench_lie`) is the common ground for item 1 (§4.2). `bench_spill.py` (Golf) was
  written to run the spill counterfactual on it. It was not run, because the benchmark adopted the same definition
  natively.
- **The JA25 hand-over check** (§9): by file and `git diff` against the remote branches.

**Held-out handling.**
- `janusm.guard.refuse` (guard v2, 711 refused) runs on the whole 22-heart list before the first download
  (`fetch_ts_r3.py`), before E8 starts (`lie_menu.guarded_ids`), and again on each heart in the loader. All 22 pass.
- No coronary or Janus-M hold-out, and no TotalSegmentator twin, was opened, read or scored. No Round 1 case list
  was reused without the guard; the 22 are the v2.0.1 `gated_like` ids that pass it today.
- No experiment note names a held-out subject or the subject a twin matches (JA36).

## 3. Assumptions carried (LQ2–LQ18)

Each is the rulings' recommendation, held until the lead answers.

| Q | Assumed | If the lead decides otherwise |
|---|---|---|
| LQ2–LQ8 | Round 1 recommendations (LV only; `heartchambers_highres`; ImageCAS-X train; 200 border reads; MM-WHS low priority; released coronary patients for training only; coronary seal as is) | Stage A changes as path A's plan says; nothing in §4–§9 here depends on them |
| LQ9 | (a) a note on the Round 1 record, no seal change | none here |
| LQ10 | (a) the reader types a CAD-RADS 2.0 grade in the read queue | none here |
| LQ11 | (a) JM-0R once after JM-0 | §9's hand-over table waits for whichever job runs |
| LQ12 | (a) seeds on the reference population committed | none here (path A's JA18 calibration) |
| LQ13 | (a) JA27–JA28 as written | (c) T1-only: §6's LGE form and §7's checker still apply; §4, §5's scar endpoints and §8 drop out |
| LQ14 | (a) single-energy LIE accepted and stratified | (b) the intake checker (§7) excludes single-energy studies instead of stratifying them |
| LQ15 | (a) CT–CMR ≤ 90 days, MI ≥ 90 days | (c) the checker moves 91–180-day patients from exclusion to a stratum |
| LQ16 | (a) two CMR readers + adjudication on every patient | (b) §5's reader-anchor variant needs both reads on development at least; see §5.3 |
| LQ17 | (a) JA32 bars | (b) §5's sizes fall; this plan's argument against (b) stands |
| LQ18 | (a) JM-0R only | none |

## 4. §7 item 1: one shared synthetic-LIE benchmark, and what it strikes

### 4.1 Who built what

- **The shared benchmark is Juliet's** (`experiments/JanusM/bench_lie/`, #179). Golf agreed on #179 within the first
  hour, and Golf and Kilo each proposed changes before any result. Juliet adopted the counterfactual spill
  definition, specificity on scar-free hearts (Kilo 1b), the "menu never empties" rule (1c), Golf's scar mix with
  sensitivity by bin, and the oracle arm.
- **Its pre-registered strike rules decide** (all at CNR 5, motion `none` or `rigid`, on the JA29 chain):
  - a presence candidate is struck if sensitivity < 0.75, specificity < 0.93, specificity on scar-free hearts
    < 0.93, or spill share > 0.25, at any blood level;
  - an extent candidate is struck if its bin agreement on scar-on-both segments is < 0.60 under both truth
    definitions.
- **Golf E8 is a cross-check on Golf's own generator and 22 hearts**
  ([[Golf - On real hearts P-G is the only presence rule that holds, its sensitivity is not spill, and the registration chain, not the rule, limits the Kim bin]]).
  It adds the always-affine arm, the per-bin and spill tables, and E9's phase check.

### 4.2 The benchmark's verdict (`bench_lie` at `0cb2b11`, `scores.json`; posted on #179 at 13:01 UTC)

21 hearts (3 skipped for no LV contrast) plus the phantom; 630 cases. Pre-registered rules, as agreed on #179
before any result:

| Candidate | JA29 chain as written (10 mm mask) | Chain with a 4 mm mask | 4 mm mask + `rim_dark` phase step |
|---|---|---|---|
| P-K | **struck** (scar-free specificity 0.006–0.32) | struck | struck |
| P-J | **survives** (min sensitivity 0.761) | survives (0.773) | survives (0.888) |
| P-G | **struck on specificity** (0.78–0.86, rigid motion; min sensitivity 0.955) | struck (0.90–0.92) | **survives** (min sensitivity 0.979) |
| E-V | survives (bin agreement 0.90 vol / 0.94 depth) | survives (0.93 / 0.97) | survives |
| E-D (3 SD voxel cut) | survives (0.89 / 0.93) | survives (0.91 / 0.95) | survives |

Spill share on the chain is ≤ 0.08 for every candidate (≤ 0.13 with the 4 mm mask). No candidate is struck on spill.

**Where E8 agrees:**
- **P-K is struck.** Both find it collapses where there is no scar.
- **Spill is not what limits any rule's sensitivity** (benchmark ≤ 0.08; E8 ≤ 0.05 for P-G).
- **E-V and the 3 SD E-D are both sound extent measures** once the borders are right.
- **The registration stage, not the rule, decides the result.** On the benchmark's static chest, the 10 mm mask
  leaves rigid at 1.24 mm median TRE, against 0.30 mm with a 4 mm mask. With a 3 % scale, affine (1.26 mm) beats
  rigid (2.19 mm), and the chain (1.69 mm) loses part of that gain. Both runs find the chain leaves accuracy on
  the table.
- **P-J with a 3 SD E-D is viable.** Re-scored that way, E8's P-J (`P-J3` in `lie_menu.json`) has sensitivity
  0.86–0.96 on exact borders and 0.72–0.84 after affine, at specificity ≥ 0.98, against ≤ 0.73 with the half-way
  cut. P-J's survival therefore depends on E-D's voxel cut being 3 SD (§11.1, reading 3).

**Where E8 disagrees, and why: P-G.** The benchmark's P-G does not apply JA30's "ignoring 1 mm at the carried
endocardium".
- `menu.py` keeps `d_endo >= 1.0` with `d_endo = edt(~cav)`. Every wall voxel next to the cavity has `d_endo` = 1.0,
  so no wall voxel is excluded.
- The shipped `scar0.py`, E8 and Kilo E8 drop that first layer.
- **Effect 1:** the benchmark's P-G detects 0.976 of nominal-15 %-depth segments on exact borders (from
  `results.jsonl.gz`), against 0.41–0.53 (E8) and 0.03 (Kilo E8). Its min sensitivity of 0.955 is that of a rule
  without the exclusion.
- **Effect 2:** the first wall layer is where blood spill lands after a 1.2 mm residual, so the benchmark's
  specificity strike on P-G is very likely the missing exclusion plus the 10 mm mask. With the exclusion, E8 has
  P-G's specificity at 0.98–1.00 after affine.
- Reported on #179 at once. A re-grade with `d_endo > 1.0` settles it; it needs no new registration.

**Golf's reading for the judge:**
- The pre-registered verdict stands as computed: P-K struck; P-J, E-V and E-D kept. P-G is struck on the chain as
  written, and kept with a 4 mm mask and `rim_dark`.
- But the P-G that was scored is not JA30's P-G. JA30's P-G, as `scar0.py` implements it, trades bin-1 sensitivity
  for specificity: E8 has it at 0.75–0.81 / 0.98–1.00 after affine.
- **Both P-J (3 SD E-D) and P-G should go to development**, and JA30's choice rule then picks on real LGE: the
  highest sensitivity among candidates whose specificity lower bound is ≥ 0.95.
- **The registration change matters more than the rule choice.** A 4 mm mask (benchmark) or always-affine (E8)
  turns P-G from struck to kept.

### 4.3 Golf E8 (cross-check), and what it adds

CNR 5, 22 hearts, sensitivity / specificity:

| | Exact borders | After always-affine | After the JA29 chain |
|---|---|---|---|
| **P-K** | 0.77–0.80 / **0.42–0.43** | 0.80–0.86 / 0.54–0.71 | 0.77–0.82 / 0.56–0.71 |
| **P-G** | 0.78–0.82 / 1.00 | 0.75–0.81 / 0.98–1.00 | 0.71–0.78 / 0.92–0.99 |
| **P-J** (half-way E-D) | 0.66–0.72 / 0.98–1.00 | 0.69–0.70 / 0.97–0.99 | 0.45–0.66 / 0.98–1.00 |
| **P-J** (3 SD E-D, as `bench_lie`) | 0.86–0.96 / 0.98–0.99 | 0.72–0.84 / 0.98–1.00 | 0.66–0.75 / 0.98–1.00 |

1. **P-K fails on specificity everywhere.** Its half-way threshold falls to noise where there is no scar. Kilo has
   withdrawn it.
2. **P-J depends on E-D's voxel cut.** With the half-way cut, its sensitivity is ≤ 0.73 even on exact borders,
   because τ (p99 of scar-free extent) sits above bin-1 extents. With the 3 SD cut (the benchmark's), it is
   0.86–0.96 on exact borders and 0.72–0.84 after affine, at specificity ≥ 0.98 (§4.2).
3. **P-G holds:** specificity ≥ 0.98 after affine, and sensitivity 0.75–0.81.
4. **Sensitivity by true bin, every rule:** bins 2–4 ≈ 1.00; bin 1 0.41–0.53 (P-G, exact) and 0.08–0.24 (P-J).
   Pooled sensitivity ≈ 1 − bin-1 share × (1 − bin-1 sensitivity). E8 uses the pre-registered mix (depths 15 / 35 /
   60 / 90 % with equal weight), but by volume-share truth 37 % of scarred segments are bin 1, not 25 %. A curved
   wall's inner layers hold less tissue, so some 35 %-depth scars fall under 25 % of the segment. P-G then sits at
   ≈ 0.80. **The JA32 sensitivity endpoint therefore rides on the cohort's
   bin-1 share**, which the development set measures (JA28).
5. **The spill share of P-G's sensitivity (the §7 item 1 measurement): ≤ 0.05** on exact, rigid, affine and chain
   borders, at every blood level. Only unregistered R0 borders (≈ 2 mm off) reach 0.19–0.21. **Spill costs
   specificity, not sensitivity:** P-G's false-call rate on the chain is 0.014–0.076 with blood, and ≤ 0.011 with
   blood at remote. The Round 2 reading ("its 0.75 is partly spill") came from v2's mid-wall remote. Under JA30's
   remote, P-G's sensitivity is highest on exact borders, and what it misses is bin 1, which its 1 mm exclusion
   cuts by design (Kilo E8: bin-1 sensitivity 0.03 aligned).
6. **Extent:** on exact borders, every measure is nearly right (bin agreement 0.88–0.96, extent error SD 0.02–0.08).
   After always-affine, E-V 0.81–0.89 against volume truth and E-D3 0.83–0.92 against depth truth, with SD
   0.06–0.13. **After the chain, 0.61–0.85, with SD 0.09–0.15.** E-D with the half-way voxel cut is the weakest
   (0.73–0.81 after affine).

### 4.4 What Golf proposes for the menu

| Item | Proposal | Why |
|---|---|---|
| P-K | **struck** | specificity 0.42 on exact borders (E8), 0.005 on scar-free hearts (Kilo E8); the benchmark's rule 1b |
| P-J | **kept, on the 3 SD E-D**; the first in the menu order (Kilo) | survives the benchmark; E8: 0.72–0.84 / ≥ 0.98 after affine with the 3 SD cut, ≤ 0.73 with the half-way cut |
| P-G | **kept, as JA30 and `scar0.py` define it (1 mm excluded)**, against the benchmark's chain-as-written strike | the benchmark scored P-G without its exclusion (§4.2); E8: 0.75–0.81 / 0.98–1.00 after affine; kept on the benchmark too with a 4 mm mask and `rim_dark` |
| E-V | kept; the primary under the read form's volume-share definition (§6.1) | best against volume truth |
| E-D | **its voxel cut is remote + 3 SD** (E-D3), not the half-way cut | E-D3 beats half-way E-D against both truths; the half-way cut inherits P-K's collapse in scar-free segments |
| Bin 1 | a reported per-bin sensitivity on development and the seal; Scar-1's first target if JA31 triggers | every rule misses most bin-1 scars |

## 5. §7 item 2: the merged power study at the JA32 bars

**E10** (`Golf/power_ja32.py`, `power_ja32.json`, `power_ja32_sweep.json`; note
[[Golf - At the JA32 bars the transmurality endpoint, not sensitivity, sets the paired seal, and it needs CT bin agreement at least equal to the readers']]).

**The merged model** (the reference for #182):
- Golf R2 E6's patient clustering and patient bootstrap;
- Kilo R2 E6's continuous transmurality, territory-contiguous infarcts, and its separate detection and measurement
  steps, calibrated to Gatti 2025's pooled 0.86 / 0.98;
- **two simulated LGE readers**, so that JA32's third bar is anchored as JA32 says: development inter-reader
  agreement minus 0.10, and report-only below 0.60.

1000 studies per cell, 500 bootstrap draws; base: 50 % enrichment, clustering τ = 0.8, CT extent error 0.13,
reader error 0.08 (reader bin agreement 0.69).

### 5.1 The ≥ 270 scarred-segment floor (JA28)

| Infarct size model | 50 % enrichment: median (p90) patients | 70 % enrichment |
|---|---|---|
| Kilo: 1 + Bin(n_territory − 1, 0.45) segments (mean 3.3) | **167 (187)** | **119 (130)** |
| Golf R2: 1 + Poisson(3) (mean 4) | 135 (155) | 97 (108) |

JA28's "about 135 at 50 %" holds for Golf's larger infarcts only. With Kilo's, **the floor alone needs ≈ 170–190
patients at 50 % enrichment**. That makes the segment floor, not the 120-patient floor, the binding size at 50 %. The merged engine (#187)
uses Golf's infarct size and gets the same 136 at 50 %, and 240 / 160 under strong clustering for joint power at
its default extent error. The difference between Golf's and Kilo's infarct sizes is what development must
measure.

### 5.2 Seal size under weak and strong clustering, per endpoint

Power at the JA32 bars (lower 95 % bounds, one look), CT extent error 0.13:

| | τ 0.4 (weak) | τ 0.8 (base) | τ 1.2 (strong) |
|---|---|---|---|
| Sensitivity ≥ 0.75, 50 % enrichment: N for power ≥ 0.80 | 80 (0.87) | 100 (0.83) | 200 (0.83; 0.77 at 160) |
| Sensitivity, 70 % enrichment | 80 (0.94) | 80 (0.86) | 135 (0.84) |
| Specificity ≥ 0.93 | ≥ 0.99 at every N | ≥ 0.99 | ≥ 0.99 |
| **Transmurality, all three jointly** | **0.25 at 200** | **0.25 at 200** | **0.18 at 200** |

- **Sensitivity sizes the seal exactly as in Round 2** (≈ 100 at base, ≈ 135–200 under strong clustering).
  Specificity never binds.
- **The transmurality endpoint does not respond to N.** At extent error 0.13 the CT's bin agreement with the
  reference (0.60) sits 0.09 below the readers' own (0.69). Its lower bound clears "readers − 0.10" only by
  chance, at any size.
- A pipeline at the weak setting (sensitivity 0.75) fails at every N (power ≤ 0.007), as it should.

### 5.3 What the transmurality endpoint needs, and a fix to its anchor

Sweep over CT extent error × reader error (`power_ja32_sweep.json`; joint power, 1000 studies):

| Gap = CT bin agreement − reader agreement (point) | N = 120, dev anchor | N = 160, dev anchor | N = 160, all-patient anchor |
|---|---|---|---|
| +0.07 | 0.83 | 0.91 | 0.93 |
| +0.04 | 0.76 | 0.86 | 0.94 |
| 0.00 | 0.61 | 0.71 | 0.79 |
| −0.04 | 0.40 | 0.50 | 0.50 |
| −0.09 | 0.17 | 0.20 | 0.11 |

- **Finding 1: the −0.10 margin is not the margin you get.** The CT is compared with an adjudicated reference,
  which is less noisy than a single reader, so the CT can match the readers. But to pass with 80 % power at 160
  patients, **the CT's bin agreement must at least equal the readers' agreement**, not sit 0.10 below it. The
  lower bound's width (≈ 0.07 with ~250 scar-on-both segments) and the development anchor's own noise (40
  patients) use up the margin.
- **Finding 2: the 0.60 floor rewards worse readers.** With reader error 0.12, reader agreement is ≈ 0.57. The
  anchor is then below 0.60 in ~70 % of studies, the endpoint drops out (JA32), and joint power at extent error 0.13 rises from 0.17
  (reader error 0.08) to 0.68–0.72 at 120. That is the opposite of what a reference standard should do.
- **Finding 3: an anchor from every patient's double read discriminates better.** Every patient already has two
  reads (JA32, LQ16). Reader agreement involves no CT value, so computing the anchor over development + seal
  leaks nothing about the pipeline. It raises power for a good pipeline (0.93 vs 0.91; 0.79 vs 0.71 at gap 0) and
  lowers it for one at the bar (0.11 vs 0.20 at gap −0.09). The development anchor passes a borderline pipeline
  by luck more often.

### 5.4 Proposed amendments (for the judge)

1. **Anchor:** the JA32 transmurality anchor is the inter-reader agreement over **every paired patient's double
   read** (development + seal), computed before any CT value of a seal patient is unblinded. Development keeps its
   own estimate for re-powering (JA28).
2. **Floor:** keep JA32's report-only rule below 0.60, but also report the endpoint against a fixed **0.60 − 0.10 =
   0.50** bar in that case, so poor readers cannot make the scar grade look validated by default.
3. **Size:** JA28's seal = max(120; the ≥ 270-segment N, ≈ 170–190 at 50 % or ≈ 120–130 at 70 % enrichment, by the
   development infarct sizes; the sensitivity N). Of these, **70 % enrichment** is what keeps the seal near 130.
   JA27's "50–70 %" should therefore target 70 %, with the ≥ 30 % LGE-negative floor unchanged.
4. **Development go/no-go for extent (extends JA31's trigger):** if the chosen extent measure's development bin
   agreement with the reference is more than **0.03 below** the development reader agreement (point estimates),
   the third endpoint cannot be powered at any feasible N. Scar-1 is then triggered on extent before any seal
   grading, even if presence passes. In E10's terms the CT extent error must be ≲ the readers' (here ≲ 0.08 of
   wall share). E8 (§4.3): after always-affine registration, E-V's error SD is 0.06–0.09, at that limit; after the
   JA29 chain it is 0.09–0.15, beyond it. Hence §8.2.

## 6. §7 item 3: the LGE read form and the registration check form

Both forms are written as machine-readable specs for the Janus-M read queue (JA35 item 5):
`experiments/JanusM/Golf/forms/lge_read_form.json` and `reg_check_form.json`. A clickable, self-timing mock-up of
both is `forms/mockup.html`. It has no data and makes no network call.

### 6.1 The LGE segment read (JA32)

- **Who:** two CMR readers per patient, independently, in a separate read set (`lge`) of the `janusm-readers`
  group. A third CMR reader adjudicates.
- **Blinding, enforced by the queue:** the reader is served the CMR series only, never a CT, scar map, clinical
  report or other read. The first field is an attestation checkbox.
- **Per patient:** LGE quality (diagnostic / limited / non-diagnostic), base-to-apex coverage, artefacts, and a
  "no LGE in any segment" button. The button sets every assessable segment to "no", and the reader still confirms
  the bull's-eye.
- **Per segment 1–17** (Cerqueira 2002 model, as a bull's-eye and a list):
  - presence: no / yes / not assessable;
  - if yes, pattern: subendocardial or transmural (ischaemic); mid-wall, epicardial, or patchy / RV insertion
    (non-ischaemic);
  - if yes, Kim bin 1–4.
- **The Kim-bin definition printed on the form:** "your estimate of the share of this segment's myocardium that is
  hyperenhanced, over all the short-axis slices that make up the segment (Kim 2000's 'percent of tissue'). It is a
  share of tissue, not the depth at the deepest point." This follows JA32. Kim 2000's segment-scoring wording is
  unverified from the abstract (JA36), so the form, not the paper, fixes the definition.
- **Example panel (six schematics, in the spec):**
  - A: a thin rim along the whole endocardium → bin 1;
  - B: scar to half the wall depth along the whole segment → **bin 2** (the inner half of a curved wall holds about
    45 % of its tissue for a 10 mm wall around a 25 mm cavity radius);
  - C: transmural scar over half the segment's width → **bin 2** (the depth is 100 %, but the share is half);
  - D: three-quarter depth along the whole segment → bin 3;
  - E: transmural along the whole segment → bin 4;
  - F: bright blood against a dark endocardium with no wall enhancement → bin 0, or "not assessable" if the border
    cannot be told from the blood.

  Panels B and C are where the two CT extent measures (E-V, E-D) part company, so the readers' answers on them
  decide which one matches the read (JA30).
- **Adjudication (JA32):** any segment where the readers differ on presence or by ≥ 2 bins. The third reader sees
  the CMR series and both reads of the flagged segments only.
- **Derived, never entered:** the reference value per segment; the ischaemic-pattern flag (the JA32 primary set);
  and the inter-reader agreement on the Kim bin over scar-on-both segments, which is the JA32 anchor (§5.3).
- **Never entered:** names, dates, accession numbers, or free text that could identify the patient.

### 6.2 The registration check (JA29)

- **Who:** any `janusm-readers` member with the `lie-reg` read set. A border reader is enough.
- **Blind to LGE and to every scar output.** The scar map is never drawn on these views.
- **Shown:** three short-axis planes at 25 %, 50 % and 75 % of the carried LV long axis, chosen by code. Each shows
  the first-pass CT (left) and the LIE (right) in the same plane and zoom, with the carried endocardium and
  epicardium drawn on both. A toggle shows the LIE without borders.
- **Per slice:** pass / fail. On a fail, one or more reasons: shifted, rotated, **cavity size differs (phase)**,
  artefact, other.
- **Patient result:** pass only if all three slices pass.
- **On a fail:** the reader drags the LIE to a manual initial shift on the mid slice, the chain re-runs once from
  it, and the same form is shown again. A second fail is "not graded" and counts as wrong (JA29).
- **Logged by code, not entered:** the chain stage that passed, the estimated shift, the log-determinant of the
  transform, the QC values, the E9 edge offsets, and the reader's decision and time.

### 6.3 Reader time, measured on the mock-up

- **Entry time** (keystroke-level model, Card, Moran & Newell 1980; `forms/klm_time.py`):

  | Form | Seconds |
  |---|---|
  | LGE read, scar-free patient | 15.9 |
  | LGE read, scarred patient (3 positive segments, the E10 mean) | 60.7 |
  | LGE read, 7 positive segments | 92.7 |
  | Registration check, pass | 9.3 |
  | Registration check, one slice fails | 14.6 |

  Over 160 patients, 60 % scarred and two readers, entering the reads takes about **3.8 reader-hours**.
- **Review time dominates, and no model gives it.** LQ16's estimate of 10 min per patient per reader (≈ 55 h) is an
  assumption, not a measurement. The mock-up is built to measure it: it times each read from Start to Submit.
- **What I propose (no outside contact):** before the cohort is pursued, two of the project's own readers time
  five mock reads each, on public CMR images the project may already use, or on the phantom alone. LQ16's
  reader-hours are then restated from those times. If no CMR images are available inside the project, the estimate
  stays an assumption and says so.

## 7. §7 item 4: the JA27 intake checker

The checker (JA35 item 3) runs on the de-identified manifest and DICOM headers, before any image is opened. Its
first step is `janusm.guard.refuse` on every patient pseudonym (JA27). Each check returns pass, a named stratum, an
exclusion, or **hold**. Hold means the manifest is incomplete; the patient is held until the field arrives, never
guessed. DICOM tags are from the DICOM standard, PS3.3 (Information Object Definitions) and PS3.6 (Data
Dictionary).

### 7.1 Same session, same frame of reference (JA27, JA29)

| Check | Fields | Outcome if it fails |
|---|---|---|
| CCTA and LIE are one session | `StudyInstanceUID` (0020,000D) equal; or the same `FrameOfReferenceUID` and acquisition times ≤ 30 min apart | **exclusion** from T2 (the patient may still be T1) |
| Shared frame of reference | `FrameOfReferenceUID` (0020,0052) equal across the CCTA and LIE series | **R0 unavailable**: the patient stays in T2, and registration starts from the image centres (under §8.2, R0 is only logged anyway). Reported as a stratum |
| Geometry kept | `ImagePositionPatient` (0020,0032), `ImageOrientationPatient` (0020,0037) and `PixelSpacing` (0028,0030) present on every slice; `TablePosition` (0018,9327), or `TableHeight` (0018,1130), where present | **hold** |
| No patient move | the same `TableHeight` on both series where recorded; R0's estimated shift logged | logged only |

### 7.2 Phase (JA27; seal and development need a match)

| Check | Fields | Outcome |
|---|---|---|
| ECG-gated | `CardiacSynchronizationTechnique` (0018,9037) is PROSPECTIVE or RETROSPECTIVE, or `TriggerTime` (0018,1060) present | not gated: **exclusion** from T2 |
| LIE phase | `NominalPercentageOfCardiacPhase` (0020,9241) if present; else `TriggerTime` ÷ (60 000 / `HeartRate` (0018,1088)) × 100; else the manifest's recorded % R-R | no source: **phase-unmatched stratum** |
| CCTA reconstruction phases | the same fields for each reconstructed CCTA phase series; retrospective raw data available (manifest field) | none recorded: **phase-unmatched stratum** |
| Phase match | \|LIE % R-R − nearest CCTA reconstruction % R-R\| ≤ 5, or raw data allow a reconstruction at the LIE's phase | **phase-unmatched stratum** (never pooled into the primary) |
| Heart rate | `HeartRate` at each acquisition | recorded; the difference is a covariate |

Phase taken from a series description or another vendor-private text is marked **inferred**, and E9's check
(§8.2) is required to pass for that patient to stay in the primary analysis.

### 7.3 Timing (JA27)

| Check | Fields | Outcome |
|---|---|---|
| LIE delay 5–10 min | LIE `AcquisitionTime` (0008,0032) minus `ContrastBolusStartTime` (0018,1042); else minus the CCTA's `AcquisitionTime` | outside 5–10 min: **stratum** (delay recorded); no time at all: **hold** |
| CT–CMR ≤ 90 days | manifest day offset (never dates) | 91–180 days: **stratum** only if LQ15 (c) is taken; else **exclusion** |
| Index MI ≥ 90 days before both scans | manifest day offsets | **acute stratum** |
| No event between CT and CMR | manifest flags: MI, PCI, CABG, cardiac surgery | **exclusion** |

### 7.4 Acquisition and form

| Check | Fields | Outcome |
|---|---|---|
| CCTA slice ≤ 0.75 mm; LIE slice ≤ 1.0 mm | `SliceThickness` (0018,0050), `SpacingBetweenSlices` (0018,0088) or the z-step of `ImagePositionPatient` | **exclusion** from T2 for the LIE; from all tiers for the CCTA |
| Recorded acquisition | `KVP` (0018,0060), `ConvolutionKernel` (0018,1210), `Manufacturer` (0008,0070), `ManufacturerModelName` (0008,1090), `CTDIvol` (0018,9345) | **hold** if kV or kernel is missing |
| Energy mode (LQ14) | the attributes of the Multi-energy CT Image module (PS3.3) where present; otherwise `ImageType` (0008,0008) values and the manifest's energy-mode field | stratum: single-energy / dual-energy / photon-counting; low dose (by CTDIvol, cut set before intake) is its own stratum |
| CMR LGE | `MagneticFieldStrength` (0018,0087), `InversionTime` (0018,0082), `SequenceName` (0018,0024); PSIR from the manifest or `ImageType`; short-axis stack from `ImageOrientationPatient` | missing short axis: **exclusion**; others recorded |
| De-identified | `PatientIdentityRemoved` (0012,0062) = YES; `BurnedInAnnotation` (0028,0301) = NO | **hold** (never opened until fixed) |
| Device or metal over the LV | manifest flag (a header cannot show it) | **exclusion** |

### 7.5 Output

One row per patient in the restricted Girder collection: tier(s), every stratum, the JA28 hash assignment, the
check results, and nothing that identifies the patient. The summary counts (no ids) go into the freeze PR for
`configs/janusm/paired-r2.json`. The checker is tested on synthetic DICOM headers only.

## 8. §7 item 5: registration QC cuts, and a truth-free phase check

### 8.1 What E8 shows about the QC values and the chain

- **The three QC shares do not choose the stage well.** With cuts set on the other half of the hearts (p95 over
  registrations with ASSD ≤ 1 mm), on chest and static motion at CNR 5: 13–17 of 66 registrations pass QC though
  their endocardial ASSD is > 1 mm, and 12–14 of 66 fail QC though they are good. The shares depend on blood and
  scar brightness: a bright scar raises "brighter than blood" in a well-registered heart.
- **The chain's two decisions cost accuracy:**
  - it stops at R0 in 18–30 % of non-phase cases (R0's median ASSD is 1.9–2.0 mm);
  - "keep affine only if it lowers QC" kept affine in 15–32 % of cases, although affine had the lower ASSD in
    **87.5 %**.

  As a result, the chain's extent error SD is 0.09–0.15 against 0.06–0.09 for always-affine. By E10 (§5.3), that is
  the difference between an unpowerable transmurality endpoint and a powerable one.
- **JA29's mask:** on the benchmark, the 10 mm mask lets a static chest pull rigid MI back toward R0 (median TRE
  1.24 mm, against 0.30 mm with 4 mm). In E8's static motion, masked rigid reaches ASSD
  0.81–0.85 mm and affine 0.61–0.65 mm, while unmasked rigid stays at 1.77–1.79 mm. The mask matters, and its
  margin should be 4 mm.

### 8.2 Proposed registration rule and QC cuts (amends JA29 steps 1–4; for the judge)

1. **Always run** heart-masked rigid, then affine from it. R0 is logged, not a stopping point.
2. **Affine is the result** unless it fails a sanity bound: |log det| > 0.15 (a 15 % volume change), or a shear or
   scale term outside ± 15 %. Then rigid is the result. QC values no longer choose between them.
3. **QC values become flags for the reader check, not gates.** Each is logged, and a value above its development
   p95 puts a "check carefully" marker on that patient's registration form (§6.2).
4. **How the cuts are set on development (40 patients):**
   - the reader check (JA29) is the reference;
   - each QC value's cut = its p95 over development registrations the reader passed;
   - the mask margin is **4 mm** on the benchmark's evidence (static chest: rigid 0.30 mm vs 1.24 mm TRE); E8's
     softer static model shows the mask matters (masked 0.81–0.85 mm vs unmasked 1.77–1.79 mm);
   - **logged for the record, never re-set on the seal.**
5. **The phase check (truth-free).** **Primary: Juliet's `rim_dark`**, the share of the carried cavity's 2 mm
   inner rim reading myocardium-dark. On the benchmark it separates the 5 % phase change from rigid and non-rigid
   motion with AUC 0.98–0.99 at every blood level. The JA29 QC shares reach only 0.07–0.56 there (`scores.json`,
   `qc_auc`). E8 did not compute `rim_dark`. Secondary: E9's heart-masked affine **log-determinant**, which
   measures the heart's volume change between the two scans.
   - On E8 it separates a 5 % phase change from breath-hold motion with AUC 0.86 (0.85–0.87 by blood level). A cut
     at 0.035 flags 76 % of phase cases with 17 % false flags; at 0.045, 52 % and 9 %. Breath-hold motion here
     includes a 3 % scale, so in phase-matched patients the false-flag rate should be lower.
   - **Kilo E8's** remote-segment endocardial half-maximum offset (|offset| > 0.6 mm flags 90–100 % of phase cases,
     0–10 % false flags) is stronger on Kilo's generator. Golf's all-segment version reached only AUC 0.66–0.75 (by blood level and
     stage), as scarred segments bias it.
   - **Rule:** a patient is phase-flagged if `rim_dark` exceeds its development p95 over phase-matched patients
     (with the log-determinant and Kilo's offset reported beside it). A flag on a patient whose phase match comes from DICOM moves the patient to the phase-unmatched
     stratum only if the reader also marks "cavity size differs (phase)". A flag on a patient whose phase is
     **inferred** (§7.2) moves the patient regardless.
   - On the benchmark, `rim_dark` is the strongest of the four phase checks tested. The others stay as logged
     numbers, not gates.

### 8.3 Failed registrations and the specificity endpoint (the PM's question on #179)

The engine (#187) shows that under JA29's intention-to-diagnose, a whole-patient failure turns ~15 LGE-negative
segments into false calls. At 5 % failure the study cannot pass at any N. Kilo E9 (same engine) compares three
rules.

- **Golf supports Kilo's proposal:** graded-only accuracy, plus a deciding yield endpoint (not-graded share, upper
  95 % bound ≤ 0.10), with the selective-failure guard. If LGE-positive segments are ≥ 1.5× as common among
  not-graded patients (lower bound > 1), the "no call" analysis becomes primary.
- **What E8 adds:** with always-affine (§8.2), the share of registrations > 1 mm endocardial ASSD falls from
  21–32 % (the chain) to **2.3 %** (chest and static motion; 10.6 % with a 5 % phase change, which is a stratum).
  That is Kilo E9's planning value of ≤ 2 % whole-patient failure, reached by the registration rule rather than
  assumed. It is confirmed on development as the reader-check failure rate, not a QC rate. JA29's 10 % development stop stays as the hard limit.
- **One correction to the engine's reading 2** (#188): "the development failure rate counts patients not graded
  after two reader checks" is right for the stop rule. The yield endpoint should use the same definition, so that
  one number serves both.

## 9. §7 item 6: the JA25 hand-over

Checked against the remote branches on 2026-10-30, after the PM's trunk syncs #202 and #204, by file and by
`git diff` (no code run):

| Shared Stage A code | On `dev` | `jm/rest-ccta` vs `dev` | `jm/paired-scar` vs `dev` |
|---|---|---|---|
| JA15 harness, `src/janusm/harness.py` + tests (#180/#183, then #198's point-to-plane API) | yes | identical | **identical** |
| JM-0R v2, `experiments/JanusM/fir/jm0r_readout.py` + tests (#197; canonical sign, JA44) | yes | identical | **identical** |
| JM-0R decision script, `experiments/JanusM/fir/jm0r_decide.py` (JA43) | yes | identical | **identical** |
| Geometry module, `src/janusm/geometry.py` | yes | identical | **identical** |
| Reference population and table writer, `src/janusm/reference.py`, `src/janusm/report.py` (#199; JA19 as amended by JA48) | yes | identical | **identical** |
| Detectable depth, `src/janusm/calibrate.py` (#198, JA40) | yes | identical | **identical** |
| Guard, `src/janusm/guard.py` | yes | identical | **identical** |

Across `src/janusm`, `tests` and `experiments/JanusM/fir`, the only difference between `jm/paired-scar` and `dev` is
path B's own `src/janusm/scar/` and its three test files.

- **One implementation is in place.** JA25 is met in code: both paths run the same harness, JM-0R, decision
  script, table writer and guard.
- **Path A's Round 3 amendments to Stage A** (JA37 onward on `jm/rest-ccta`, e.g. JA43 decision rules, JA44's sign,
  JA48's tables) arrive here with the code. Golf reads JA25 as importing them too, because Stage A on this path *is*
  path A's. The judge should state that, since JA25 names only JA15–JA24.
- **JM-0R's numbers:** none exist. JM-0R runs after Job JM-0 (LQ11), and no JM-0 aggregate has been posted.
  `jm0r_decide.py` runs once on its `summary.json`, and **this path applies its output as `jm/rest-ccta` does, with
  no path-B variant**: rest TPR in or out of the table (JA17), the provisional fat cut (JA18), the septal-arc column
  (JA20), and detectable depth (JA40).
  - **Territories on this path** are then decided by JA33's culprit-vessel test, not by the ≥ 10 % rule (JA33).
  - **One path-B use:** JM-0R's endocardial half-maximum offset and 10–90 % edge width on first-pass CCTA set the
    expected spread of the E9 / Kilo E8 edge offset on the paired cohort's first pass (§8.2). They are read in
    JA44's canonical sign (+ = the region bounded by the border extends beyond the image half-maximum), which is
    the opposite of the sign in Golf E9's code (+ = the LIE edge lies outward of the carried border, for the
    endocardium). A §8.2 implementation must convert.
- **Golf E7 (`Golf/harness.py`)** stays a test reference only (JA25); nothing imports it.

## 10. §7 item 7: path summary for the lead

An update of the Round 2 ruling's §8, for #143. Path A's column is unchanged.

| | Path A, `jm/rest-ccta` | Path B, `jm/paired-scar` (after Round 3) |
|---|---|---|
| Assumes | no reference for scar or ischaemia | a paired CCTA + same-session LIE + CMR LGE cohort the lead obtains (data requirements only, D31) |
| Stage A | built and calibrated: specificity only (JA18) | **identical, one implementation** (JA25): harness, JM-0R v2, decision script, table writer and guard byte-identical on `dev` and both paths (§9) |
| Scar grade | none | Scar-0 from a menu narrowed on one shared benchmark (§4): P-K struck; P-J (3 SD E-D), P-G (with its 1 mm exclusion), E-V and E-D kept for development |
| What limits the scar grade | — | **registration, not the rule** (E8): on exact borders the extent error is ≤ 0.08 of wall share; after the JA29 chain it is 0.09–0.15, and 0.06–0.09 with always-affine registration (§8.2) |
| Reference standard | read-vs-read border agreement | the same, plus two CMR readers per segment, read on a fixed form (§6) |
| Seal size | — | max(120; ≥ 270 scarred segments ≈ 120–130 patients at 70 % enrichment or ≈ 170–190 at 50 %; the sensitivity N) |
| What decides pass/fail | — | **the transmurality endpoint**: it needs CT bin agreement ≥ the readers' own, which no number of patients buys (E10) |
| Phase mismatch | — | recorded by the intake checker (§7); flagged without truth by `rim_dark` (benchmark AUC 0.98–0.99), with the affine log-determinant beside it (§8.2) |
| Committed compute | ≈ 15 GPU-h (with LQ12) | the same + ≈ 3 GPU-h once the cohort exists; scar on CPU |
| Extra reader time | none | form entry ≈ 4 h (measured by model); image review ≈ 55 CMR reader-hours (an assumption until timed on the mock-up) |
| Main risk | flags with no measured sensitivity | **the cohort never arrives**; or registration residuals keep the transmurality endpoint out of reach and Scar-1 (or the voxel head, ≈ 55 GPU-h, ≥ 60 more patients) is needed |
| If the cohort never arrives | — | path B reduces to path A exactly; nothing built here is lost |

**In short:** path B is path A plus one validation study. Round 3 shows the study is **feasible to specify and to
read**, but its pass rests on the transmurality endpoint, and that endpoint is set by how well the late scan is
registered, not by the rule or the patient count. The lead's question is unchanged: can a same-session LIE + LGE
cohort of about 130–190 patients, enriched to about 70 % prior MI, be had?

## 11. Code that must ship, and the six readings of #188

JA35 items 1, 2, 4 and 6 are built and merged on this path: `src/janusm/scar/registration.py`, `scar0.py`
(#188) and `power.py`, `scoring.py` (#187). Golf builds none of it here. The PM opens and assigns new issues
(JA35).

### 11.1 The six readings #188 asked advocates to confirm

| # | #188's reading | Golf | Evidence |
|---|---|---|---|
| 1 | affine "lowers QC" = no QC value rises and their sum falls | **Confirm as a reading of JA29; propose replacing the rule** (§8.2: affine unless a sanity bound fails) | E8: the QC rule kept affine in 15–32 % of cases, though affine had the lower ASSD in 87.5 % |
| 2 | development failure rate = patients not graded after two reader checks | **Confirm**, and use the same count for Kilo's yield endpoint (§8.3) | — |
| 3 | E-D's voxel cut = the half-way (P-K) cut | **Correct to remote + 3 SD** (as `bench_lie` reads it); P-J survives the benchmark only on this cut | E8: E-D3 beats half-way E-D against both truths after affine (0.76–0.85 / 0.83–0.92 vs 0.75–0.81 / 0.73–0.76); the half-way cut inherits P-K's collapse where there is no scar |
| 4 | deepest u = the far edge of the deepest depth bin called scar in any E-D column | **Confirm**; report it per segment as the median over columns as well, since the "any column" maximum is set by one noisy column | — |
| 5 | QC's blood median over the carried cavity core (1 voxel inside) | **Correct to ≥ 2–3 mm inside** (Juliet: 2 mm; E8: 3 mm erosion): one voxel inside still takes papillary muscle and partial volume | — |
| 6 | reader forms out of scope | Specified here: §6 and `forms/` | — |

### 11.2 What still has to be built or changed

1. **Registration module (#188), amendments if the judge takes §8.2:**
   - always rigid → affine; the sanity bound replaces the QC comparison;
   - QC values become logged flags with development cuts (`QCCuts` stays a required input);
   - `rim_dark` as the phase flag; the affine's log-determinant (already in the stage parameters) and Kilo's
     remote-segment endocardial offset logged beside it;
   - the mask margin as a parameter, 4 mm on the benchmark's evidence.
2. **Scar-0 module (#188):** E-D's voxel cut to 3 SD (reading 3); P-K removed from the menu config if struck
   (kept in code for the record); sensitivity by true bin in `for_scoring()`'s report.
3. **Power and scoring (#187):**
   - an option for the transmurality anchor from every patient's double read (§5.3–5.4);
   - Kilo's graded-only + yield primary and the selective-failure guard (§8.3);
   - the extent error per bin as an input, so the re-powering on development uses the measured extent error,
     not q = 0.25. `power_ja32.py` is the reference for the reader-anchored transmurality endpoint, and the engine
     should reproduce its cells.
4. **Intake checker (JA35 item 3):** §7's tables as code, tested on synthetic DICOM headers. It waits until the
   lead pursues the cohort.
5. **Read forms (JA35 item 5):** `forms/lge_read_form.json` and `forms/reg_check_form.json` as queue form
   definitions, served only from the restricted paired collection, with one new JanusMRead view for the
   registration check (three planes, two images, borders on both). It waits until the lead pursues the cohort.
6. **The shared benchmark** stays experiment code. Its generator is the fixture source for the module tests.

## 12. Compute

- **This round:** CPU only, in this container. No Fir, SciNet or Alliance job.
- **The path's committed compute is unchanged** (JA34): ≈ 3 GPU-h once the cohort exists; scar steps on CPU; the
  voxel head (≈ 55 GPU-h) only if Scar-1 fails.

## 13. Citations

Round 1's JA14, path A's JA24 and this path's JA36 corrections bind.

| Source | Used for | Checked |
|---|---|---|
| Kim RJ et al. N Engl J Med 2000;343:1445–1453. doi:10.1056/NEJM200011163432003 | Kim bins; "percent of tissue" | abstract; its segment-scoring definition is unverified (JA36), so the form defines it |
| Cerqueira MD et al. Circulation 2002;105:539–542. doi:10.1161/hc0402.102975 | the 17-segment model and default territories | abstract; the territory figure is confirmed only by secondary sources (JA14) |
| Gatti M et al. Eur Radiol 2025;35:3054–3067. doi:10.1007/s00330-024-11283-5 | pooled LIE segment sensitivity 0.86, specificity 0.98 (the E10 calibration) | abstract (confirmed by the Round 2 judge) |
| Card SK, Moran TP, Newell A. Commun ACM 1980;23(7):396–410. doi:10.1145/358886.358895 | the keystroke-level model and its operator times | bibliographic record; operator times as commonly tabulated from the paper |
| Mattes D et al. IEEE Trans Med Imaging 2003;22:120–128. doi:10.1109/TMI.2002.808360 | the MI metric in E8 | confirmed by the Round 2 judge |
| DICOM PS3.3 and PS3.6 (NEMA, current edition, dicom.nema.org) | the tags in §7 | the standard's data dictionary |
| Ibrahim 2010; Pokorney 2012; Bettencourt 2013 | timing windows and the low-dose stratum, as JA27 and JA36 state them | carried from the Round 2 record; no new claim |
