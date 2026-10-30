---
aliases: [Janus-M Round 3 paired-scar]
tags: [janus-m, plans, judgement, round3, path-paired-scar, myocardium, scar, lie, lge, registration]
author: Janus-M Round 3 judge (path jm/paired-scar)
round: 3
path: jm/paired-scar
status: ruling
updated: 2026-10-30
issue: christianGRogers/Asclepius#179
---

# Janus-M Round 3, path `jm/paired-scar`: the judgement

**Ruling in one paragraph.** Round 3 settled what Round 2 left open (§7 items 1–7) on one shared benchmark, and the
answer moved the plan's weight **from the scar rule to the registration**.
- **The rule menu.** P-K is struck: it calls scar in hearts with no scar. P-J survives. P-G fails only because of
  JA29's registration, and comes back under the new chain.
- **The registration chain.** It changes in four ways: a 4 mm heart mask instead of 10 mm, `rim_dark` added to the QC
  values, a stricter rule for keeping affine, and a separate truth-free phase check (JA51–JA53).
- **Failed registrations.** A patient whose registration fails no longer turns ~15 scar-free segments into false
  calls. Its scarred segments count as misses, and a deciding yield bar is added (JA55).
- **Two claims.** The study now makes two claims in a fixed order: scar presence first, then the Kim bin, whose
  reader anchor comes from every patient's double read (JA56).
- **The seal.** It is sized on the presence claim, at a 70 % enrichment target, capped at 240 (JA57).
- **Forms and intake.** The LGE read form, the registration check form and the intake checker are fixed (JA58).

**Base:** the path plan stays **[[Kilo v2]] with JA25–JA36**, now amended by **JA50–JA59**. **[[Juliet v3]] scores
highest (18/20)** and supplies most of them. **No fork** (§6).

Rules kept: the judge ran no experiment, opened no image, downloaded no data and read no held-out case or twin list.
The checks below read committed JSON and code on `jm/paired-scar` at `bb8fde8`, issue #179 in full, the sibling
branch's judgement files by name and amendment number only, and two public DOI records (doi.org / Crossref). No case
id is reproduced here.

---

## 1. What was checked

### 1.1 The shared benchmark (`experiments/JanusM/bench_lie/`, v2 = `scores.json`, v1 = `scores_v1.json`)

**Verdicts under the rules pre-registered on #179** (CNR 5; motion none or rigid; any blood level; strike if
sensitivity < 0.75, specificity < 0.93, specificity on scar-free hearts < 0.93, or spill share > 0.25):

| Candidate | `strike` in `scores.json` (JA29 chain, 10 mm) | Deciding numbers, re-read | PM's note |
|---|---|---|---|
| P-K | struck | scar-free specificity 0.006–0.315; specificity 0.613 / 0.697 (bright or equal blood, rigid). On oracle borders, scar-free specificity is still 0.006–0.056 | ✓ |
| P-J | survives | sensitivity 0.761–0.840, specificity ≥ 0.958, scar-free ≥ 0.972 | ✓ |
| P-G | struck | specificity 0.797–0.880, scar-free 0.842–0.927, all under rigid motion; sensitivity 0.875–0.979 | ✓ ("about 0.80–0.88") |
| E-V / E-D | survive | exact-bin agreement 0.899 / 0.885 (volume truth), 0.939 / 0.925 (depth truth), under P-J | ✓ |

**P-G passes every bar on true borders and on the "4 mm + `rim_dark`" arm** (`strike_reported`):
- oracle: sensitivity ≥ 0.921, specificity ≥ 0.989, scar-free 1.00;
- `chain_m4_rim`: ≥ 0.915 / ≥ 0.985 / 1.00.

Confirmed. **The 4 mm mask alone does not rescue P-G** (`chain_m4`: specificity 0.897–0.921). `rim_dark` is needed as
well.

**Spill** (blood set to remote, same seed): ≤ 0.085 for every rule on the chain in the striking conditions, and ≤ 0.19
in any non-R0 arm. Confirmed (PM: ≤ 0.09).

**v2 against v1, every non-P-G number.** Compared field by field, all 720 presence cells and all 2 880 extent cells:
- **Sensitivity and specificity:** no cell moves.
- **Extent:** no cell moves.
- **Registration TRE:** no cell moves.
- **Scar-free specificity:** moves ≤ 0.003, in 3 cells.
- **Spill share:** moves 0.013 in one affine cell (not stated on #179).
- **QC AUCs:** move ≤ 0.001 in 4 cells (not stated on #179).
- **Two QC medians in the non-rigid row:** move by 0.0002.

All of these are consistent with the disclosed non-determinism of SimpleITK's multithreaded affine (18 of 630
cases). **v2 reproduces v1 outside P-G.** The P-G fix (`edt − 0.5 ≥ 1.0`) is in `menu.py:197`.

**Three things the benchmark's arms are, that the candidates' text does not say:**
1. **"4 mm mask + `rim_dark`" (`chain_m4_rim`) is R0 or 4 mm *rigid*, with no affine stage** (`score.py:170–172`). Its
   TRE equals `rigid_m4`'s in every moved condition (rigid 0.296 / 0.442 mm median / p90). The benchmark has never
   run affine with the 4 mm mask. **Juliet E10** did, on the shipped module, and affine there overshoots: p90
   1.62 mm at CNR 5 and 2.41 mm at CNR 3, against 0.67 / 0.78 mm for 4 mm rigid. JA51 is written around that.
2. **The benchmark's mask margins are city-block, not Euclidean.** It dilates by voxel iterations with face
   connectivity (`menu.py:54–55`); the shipped module dilates by Euclidean distance (`registration.py:246`). The
   benchmark's "10 mm" mask is therefore smaller than the module's, which is why the module does worse with 10 mm
   (E10: 3.4 mm median after a 4.2 mm shift, against the benchmark's 1.24 mm). E10 shows **Euclidean 4 mm** works on
   the module (0.24 mm median, p90 0.67 mm). JA51 specifies Euclidean.
3. **The benchmark's "affine lowers QC" compares the sum of fat-like and above-blood** (`score.py:118`). #188's
   reading 1 is "no QC value rises and their sum falls" over three values. They differ; JA51 replaces both.

**Benchmark against shipped `scar0.py`: two differences** (beyond the two #188 readings below):
- **P-G's denominator.** The benchmark divides P-G's called voxels by the wall that is ≥ 1 mm from the endocardium
  (`g_den`, `menu.py:199`). `scar0.py:335` divides by the whole segment. The benchmark's verdict was reached with the
  first, so the module follows it (JA54).
- **E-D's voxel cut.** The benchmark uses remote + 3 SD (`hi3`); `scar0.py:329` uses P-K's half-way cut (#188 reading
  3). This is Golf's finding, confirmed in code, and the reason P-J survives (§1.3).

### 1.2 Registration claims

| Claim | Source | Re-read | Match |
|---|---|---|---|
| 10 mm mask: rigid median 1.24 mm against 0.30 mm with 4 mm after a 4 mm heart shift; chain 1.33 / 3.65 (median / p90) | `scores.json` `registration` | rigid 1.236, `rigid_m4` 0.296; chain 1.329 / 3.649 | ✓ |
| QC trio keeps R0 on 14 of 126 moved cases; with `rim_dark`, 0 of 504 | `chain_rim_R0_kept` = 0 in every moved row | ✓ |
| `rim_dark` AUC 0.98–0.99 (phase vs rigid and vs non-rigid); 0.988 for misregistration at R0; trio 0.07–0.56 | `qc_auc` | 0.980–0.994; 0.988; 0.068–0.556 | ✓ |
| 4 mm costs little on aligned scans (0.17 vs 0.09 mm) | `registration[none]` | 0.172 / 0.094 | ✓ |
| E10, shipped module: 10 mm leaves 3.4 mm, 4 mm 0.24 mm after 4.2 mm | `Juliet/r3/e10_shipped_registration.json` | 3.399 / 0.238 (CNR 5, 21 hearts) | ✓ |
| Kilo E8: \|edge offset\| > 0.6 mm flags 90–100 % of phase cases, 0–10 % false flags; r = −0.80 with the true border error | `Kilo/results_e8_qc_phase_summary.json` | r −0.801; flag rates as stated | ✓ |
| Golf E9: affine log-det AUC 0.86 for a 5 % phase change | `Golf/lie_menu.json` `e9_phase_check` | 0.851–0.869 | ✓ |
| Golf E8: QC-gated chain doubles extent error against always-affine | `lie_menu.json` rows | E-V error SD 0.09–0.15 (chain) against 0.06–0.09 (affine) | ✓ in range; "about 1.5–2×" is the fair word |
| Golf E8: the chain stops at R0 in 18–30 % of cases | `chain_qc` | 18.2–30.3 % | ✓ |
| Kilo's non-rigid motion defeats every rule after rigid or affine | `scores.json` `nonrigid` | best-arm specificity 0.62–0.997 (P-J), 0.72–0.93 (P-G); oracle ≥ 0.966 | ✓ |

**One reading the candidates did not draw.** Most of Golf E8's chain penalty comes from stopping at R0 when the QC
passes a misaligned scan. That is exactly what `rim_dark` removes on the benchmark (R0 kept on 0 of 504 moved cases).
Golf's "always register" and Juliet's "R0 gate with `rim_dark`" treat the same failure. The evidence for affine, by
contrast, is mixed:
- Golf E8: affine is better when the motion has a scale term;
- E10: affine at 4 mm overshoots when it does not.

### 1.3 Bin 1 and the presence rules

- **Kilo:** E8's P-G bin-1 blindness (0.03) was a 1.5 mm-grid effect. **Confirmed:** on the benchmark's 1 mm grid,
  oracle P-G bin-1 sensitivity is 0.72–0.90 (v2, with the exclusion).
- **Golf:** P-J survives only with E-D's 3 SD cut. **Confirmed** in `lie_menu.json`:
  - half-way cut: ≤ 0.72 on exact borders;
  - 3 SD cut (`P-J3`): 0.86–0.96 on exact borders, 0.72–0.84 after affine.
- **Kilo:** pooled sensitivity ≈ 1 − (bin-1 share) for every surviving rule. **Holds on the JA29 chain only.** There,
  P-J's bin-1 sensitivity is 0.00–0.30. Under `chain_m4_rim` it is 0.60–1.00 for P-J and 0.60–0.94 for P-G. So
  thin-scar loss is mainly registration residual (Kilo's own correction on #179) and, at 1.5 mm, voxel size. The
  bin-1 share still matters (Golf: 37 % of scarred segments are bin 1 by volume truth under the pre-registered
  mix). So development reports it, and JA57 uses it.

### 1.4 Power and intention-to-diagnose

| Claim | Source | Re-read | Match |
|---|---|---|---|
| #187: seal 136 / 120 (weak, 50 / 70 %), 240 / 160 (strong); 270 segments need 136 / 97 | `Scar/ja32_power_r2.json` `seal_size`, `patients_for_270_segments` | as stated | ✓ |
| #187: at 2 % failure no N ≤ 320 reaches 0.80 under JA29 | `seal_size` p_fail 0.02 → `null` | ✓ |
| Kilo E9: joint power, 2 % failure, 50 %, N 120 / 160 / 240: worst case 0.39 / 0.50 / 0.61; no-call 0.65 / 0.78 / 0.91; graded-only + yield 0.88 / 0.95 / 0.99 | `Kilo/results_e9_engine_ja32.json` `B_failures` | 0.39 / 0.503 / 0.61; 0.65 / 0.78 / 0.913; 0.88 / 0.947 / 0.993 | ✓ |
| Juliet E9: the split accounting needs N 200 (50 %) and 160 (70 %) at 2 % failure; JA29's gives 0.79 at 320 | `Juliet/r3/e9_itd_power.json` | split 0.848 at 200 (50 %); segment 0.79 at 320 | ✓ |
| Golf E10: transmurality power does not respond to N; CT bin agreement must reach the readers'; ≥ 270 segments need 167 / 119 patients with Kilo's infarct size | `Golf/power_ja32.json`, `_sweep.json` | `segments_needed.kilo` 167 / 119; calibration at extent error 0.13: CT 0.60 against readers 0.69 | ✓ |
| Kilo E9 part A: at anchor 0.72, joint power 0.88–0.99 at CT agreement 0.73 and 0.23–0.35 at 0.66 | `A_transmurality` | as stated | ✓ |

**A point the candidates did not make, which decides JA55.** Kilo's selective-failure guard asks whether the
LGE-positive share among not-graded patients is ≥ 1.5× that among graded patients, with a bootstrap lower bound > 1.
At the planning failure rate (2 %), a 160-patient seal has about three not-graded patients. A ratio test on three
patients has almost no power, so the guard would rarely fire even when failures fall on scarred hearts. Juliet's A1
charges those failures to sensitivity directly, and needs no guard.

### 1.5 Forms, intake, hand-over

- **Forms.**
  - Golf's `forms/lge_read_form.json` and `reg_check_form.json` hold no identifier field; they list names, dates and
    accession numbers as "never entered". `mockup.html` makes no network call.
  - Juliet's `mock_lge/` commits only `truth.json`; its images are regenerated from geometry by `lge_mockup.py`.
  - Neither contains a request to anyone outside the project (D31).
- **Reader timing.** Juliet writes that the Janus-M queue "already stamps `assigned` and `submitted`"
  (`src/janusm_reads/protocol.py`). **It does not.** `janusm_reads` defines the states with no time field; only
  `src/segqueue/` stamps times. The timing Kilo and Juliet both rely on therefore needs a small change (PS3-S11).
- **DICOM tags.** The tags in the three intake specs agree with each other and with PS3.6 as the judge reads it. They
  were not machine-checked here, because pydicom is not installed and nothing was downloaded. PS3-S12's tests check
  them against pydicom's dictionary.
- **JA25 hand-over.** Confirmed: `git diff` between this branch and `origin/dev` is empty for `src/janusm/harness.py`,
  `report.py`, `reference.py` and `experiments/JanusM/fir/`. The table writer (`report.py`, `reference.py`) exists
  and is identical on both. Kilo v3 §8's "table writer exists on no branch" is stale. The bias guard in the shared
  harness is 0.3 mm (JA71 on `jm/rest-ccta`, #238).

### 1.6 Citations

- **Golf's Mattes 2003 DOI is wrong.** `10.1109/TMI.2002.808360` resolves to Sutton et al., "Fast, iterative image
  reconstruction for MRI in the presence of field inhomogeneities" (same journal, vol. 22, 178–188). Kilo's
  `10.1109/TMI.2003.809072` resolves to Mattes et al., "PET-CT image registration in the chest using free-form
  deformations", 22:120–128. ✓ for Kilo.
- Card, Moran & Newell 1980 (`10.1145/358886.358895`), Commun ACM 23:396–410. ✓
- Kim 2000 (`10.1056/NEJM200011163432003`), NEJM 343:1445–1453. ✓ Its segment-scoring definition remains
  unverified from the abstract (JA36). All three forms define the bin themselves, as JA32 requires.
- Kilo's DICOM PS3.15 §E.3.6 was read through a search excerpt (the page returned 503), and Kilo says so.

### 1.7 Held-out handling

- **The guard runs first in every Round 3 path that opens a heart.** The judge confirmed this by reading the code:
  - `bench_lie/fetch.py` (the whole list, then each heart) and `bench.load_heart`;
  - `Golf/fetch_ts_r3.py` and `lie_menu.py`;
  - `Kilo/e8_qc_phase.py` (the whole run, then each case);
  - `Juliet/r3/shipped_reg.py`, through `bench.load_heart`.
- **No experiment note of this round names a held-out subject** or the subject a twin matches (JA36), on a search
  of the eight notes.
- **The judge did not open, list or compare any twin or held-out list.**

---

## 2. Scorecards

Scale 1–5:
- **(a)** reasoning;
- **(b)** evidence;
- **(c)** fit to path B and to obtainable data;
- **(d)** risk and cost (5 = low risk, cheap).

### Juliet v3: one benchmark for every scar rule, and the forms, intake checks and QC cuts that make the study runnable

| | Score | Why |
|---|---|---|
| (a) Reasoning | **5** | Built the shared benchmark, posted the strike rules before any result, and took Kilo's and Golf's changes in writing. Disclosed both pre-result bugs (spill definition, phase build) and Golf's post-result catch. Re-ran with the same seeds and showed that every other number reproduces. Found the 10 mm mask flaw and then confirmed it on the shipped module (E10). A1 is the most defensible intention-to-diagnose rule (§1.4). A4's "lower of two bins" is a bias, not a rule (JA58 replaces it) |
| (b) Evidence | **4** | 630 cases, one scorer, every per-segment value committed; every number re-read matches. Deducted: the "4 mm + `rim_dark`" arm has no affine stage and city-block margins, and the text never says so (§1.1); "the queue already stamps times" is wrong (§1.5); §2 calls #187 unmerged |
| (c) Fit | **5** | The most complete intake mapping (a de-identification gate first, every JA27 row with an outcome), a synthetic LGE mock-up with truth, and a pre-registered JA25 use of `jm0r_decide.py` |
| (d) Risk / cost | **4** | CPU only. A5 would gate CMR readers on synthetic drawings (not adopted as a gate, JA58) |

### Kilo v3: score presence on a cohort sized for it, check phase before trusting a border, and stop pretending transmurality is easy

| | Score | Why |
|---|---|---|
| (a) Reasoning | **5** | Withdrew its own P-K on its own evidence before the benchmark posted, and corrected its own bin-1 over-generalisation. Found that transmurality is a claim the seal may not be able to power, and that the 0.60 floor rewards noisier readers. Proposed the yield endpoint. The best reasoned answers to #188's readings (normalising QC before comparing; why E-D shares E-V's cut) |
| (b) Evidence | **4** | E7–E9 match their JSON; E9 runs on the merged engine unchanged. Deducted: P-G figures under the proposed registration are v1's (0.98; v2 gives 0.915); "table writer exists on no branch" is stale; the edge offset is tested on Kilo's generator only |
| (c) Fit | **4** | The intake table is careful about dates (a constant shift per patient, or manifest offsets). Graded-only scoring with a guard that cannot fire at the expected failure counts is weaker than A1 (§1.4) |
| (d) Risk / cost | **4** | CPU only. Caps the seal at 240 |

### Golf v3: strike what fails on one benchmark, power the study on its binding endpoint, and fix the forms first

| | Score | Why |
|---|---|---|
| (a) Reasoning | **4** | Found the benchmark's missing P-G exclusion and E-D's voxel-cut dependency, the two catches that changed the record. Showed that development's anchor noise eats the −0.10 margin (all-patient anchor). Deducted: always-affine is argued from a generator with a scale term and is contradicted at 4 mm by E10. Making QC flags only, never gates, discards the one gate (`rim_dark`) that works |
| (b) Evidence | **4** | E8 is a real cross-check on 22 hearts, and E10's sweep is the clearest sizing evidence. Deducted: the Mattes DOI is wrong (§1.6); P-G figures are v1's (0.979 for A2; v2 0.915); "doubles" overstates 1.5–2× |
| (c) Fit | **4** | Machine-readable forms and a self-timing mock-up; a "hold" outcome for incomplete manifests; the six-panel Kim-bin example where E-V and E-D part company |
| (d) Risk / cost | **4** | CPU only. Always-affine risks overshoot on rigid motion (E10) |

**Totals (of 20):** Juliet 18, Kilo 17, Golf 16. Round 3 asks no candidate to replace the base. The path plan stays
Kilo v2 + JA25–JA36, now amended by JA50–JA59. Juliet's benchmark, registration and intake carry the most weight in
them.

---

## 3. Rulings where they disagree

| Item | Juliet v3 | Kilo v3 | Golf v3 | **Ruling** |
|---|---|---|---|---|
| Presence menu | P-J; P-G if A2 | P-J, P-G (4 mm) | P-J (3 SD), P-G | **P-J then P-G; P-K struck** (JA54) |
| E-D voxel cut (#188 reading 3) | 3 SD (benchmark) | 3 SD | 3 SD | **3 SD** (JA54) |
| Mask | 4 mm | 4 mm, 10 mm fallback | 4 mm | **Euclidean 4 mm; 10 mm one-shot fallback** (JA51) |
| R0 as a stop | yes, with `rim_dark` | yes | no, always register | **yes, but only with `rim_dark` in the QC** (JA51) |
| Affine kept when (#188 reading 1) | QC lowers | normalised QC | always, unless a sanity bound fails | **both a sanity bound and the normalised QC rule** (JA51) |
| Phase check | `rim_dark` | `rim_dark`, then the edge offset | `rim_dark`, log-det logged | **`rim_dark` primary, edge offset secondary, log-det logged** (JA52) |
| QC cuts | p95 of an aligned development reference | smallest cut keeping ≥ 95 % of reader-passed; drop weak values | p95 of reader-passed; flags only | **p95 of reader-passed development; shares indexed by blood contrast; weak values dropped from the gate** (JA53) |
| B-spline | development arm if residual ≈ 1.5 mm | none; reader check and yield | — | **benchmark arm in Round 4; development arm on a stated trigger** (JA53) |
| Failed patient | A1: LGE+ missed, LGE− out of specificity; yield bar | graded-only + yield + guard | Kilo's | **A1 + yield bar** (JA55, LQ25) |
| Transmurality anchor | unadjudicated, development | every double-read patient | every double-read patient | **every double-read patient, before seal CT is unblinded** (JA56) |
| Anchor < 0.60 | — | presence only; Kim bin not validated | also report against 0.50 | **Kim bin not validated; 0.50 reported** (JA56) |
| Claims | three endpoints jointly | sized on presence | transmurality decides | **two claims, fixed sequence** (JA56, LQ26) |
| Seal size | 160–200 at 2 % failure | max(…), 70 %, cap 240 | max(…), 70 % | **max(…), 70 % target, cap 240** (JA57, LQ27) |
| Adjudication reference | shared presence, lower bin | majority; median of 3 | — | **third blind read on any bin or presence disagreement; majority, else median** (JA58, LQ28) |
| #188 reading 5 (blood median) | 2 mm | ≥ 2 mm, 1-voxel fallback | 2–3 mm | **≥ 2 mm inside; 1 voxel if < 50 voxels remain** (JA51) |
| Frame of reference missing | seal-ineligible | not an exclusion | stays T2; stratum | **stratum, seal-eligible** (JA59) |
| LIE slice > 1.0 mm | seal-ineligible | T1 only | excluded from T2 | **T1 only** (JA59) |
| De-identification failure | quarantine the batch | quarantine the patient | hold | **quarantine the batch** (JA59) |
| Reader qualification (A5) | a gate on the mock-up | — | timing only | **practice and timing, never a gate** (JA58) |

---

## 4. Binding amendments (JA50–JA59; path `jm/paired-scar`)

- **JA50 — Stage A here tracks path A as it stands.** (Clarifies JA25.)
  - JA25 imports `jm/rest-ccta`'s Stage A as amended after Round 2: JA37–JA49, JA60–JA71 and any later Stage A
    amendment. It does so through the shared code on `dev`, not by copying text. The bias guard in force is the
    shared harness's 0.3 mm (JA71, #238).
  - The hand-over is complete: harness, JM-0R v2, `jm0r_decide.py`, `calibrate`, `reference` and `report` are
    identical on `dev` and here (§1.5).
  - When JM-0R's aggregate is posted, this path runs `jm0r_decide.py` on it **unchanged** and records its output as
    `jm/rest-ccta` does (Juliet §6). Path B adds no Stage A rule.
  - A path-B commit that edits a shared Stage A module is refused in review.
- **JA51 — The LIE registration chain.** (Replaces JA29's steps 1–4. JA29's direction, carried quantities, reader
  check and logging stand.)
  1. **R0**, scanner coordinates.
  2. **QC: four values on the smoothed LIE.**
     - **The values:** fat-like share, blood-like share, share brighter than the blood median, and **`rim_dark`**.
       `rim_dark` is the share of the carried cavity's 2 mm inner rim below (remote + blood median) / 2.
     - **The blood median** is taken ≥ 2 mm inside the carried cavity border, or 1 voxel inside if fewer than 50
       voxels remain (#188 reading 5, corrected).
     - **The stop:** R0 is kept only if all four pass their cuts (JA53).
  3. **Rigid Mattes MI**, the metric masked to classes 1–4 dilated by **4 mm (Euclidean)**.
  4. **Affine from rigid, with the same mask.** It is kept only if both hold:
     - **(a) a sanity bound:** |log det A| ≤ 0.15, and every scale and shear term within ± 15 % (Golf);
     - **(b) the normalised QC rule:** each QC value is divided by its cut; no normalised value rises, and their
       maximum falls (Kilo).

     This replaces #188's reading 1 and the benchmark's two-value sum.
  5. **The 10 mm fallback.** If the result still fails QC, one rigid run with a 10 mm Euclidean mask. It replaces
     the result only if it passes QC, or lowers the normalised maximum.
  6. **The phase step** (JA52). Then the **reader check on every patient**, as JA29 states. A fail is re-registered
     once from the reader's manual shift; a second fail is "not graded".

  **Why this chain.**
  - The benchmark's "4 mm + `rim_dark`" arm brings the 4 mm heart-shift residual to 0.30 / 0.44 mm and reinstates
    P-G. E10 confirms 4 mm on the shipped module.
  - That arm never ran affine. E10's 4 mm affine overshoots (p90 1.6–2.4 mm) when there is no scale. Golf E8's
    affine helps when there is. Hence (a) + (b), which Round 4 tests (§7).
- **JA52 — A truth-free phase check routes phase-mismatched patients out.** (Settles Round 2 §7 item 5's second
  half.)
  - **Primary flag:** `rim_dark` above its phase cut after the final stage. The benchmark's AUC is 0.98–0.99 at every
    blood level.
  - **Secondary flag:** Kilo's signed endocardial edge offset, over the 6 remote segments, half-voxel corrected.
    Provisional flag |offset| > 0.6 mm. Its point is to catch a *larger* LIE cavity, which `rim_dark` cannot see by
    construction.
  - **Logged only:** the affine log-determinant (AUC 0.86, Golf E9) and the edge-offset IQR.
  - **A flagged patient:**
    - is not re-registered (registration cannot fix phase);
    - is **not a registration failure**;
    - with DICOM-matched phase, goes to the phase-unmatched stratum if the reader also marks "cavity size differs
      (phase)";
    - with phase inferred from text (JA59), goes there on the flag alone.
  - **Not evaluable:** when (LIE blood median − remote) < 2 robust SD of remote. The patient's phase then rests on the
    DICOM fields and the reader.
  - **Stop rule:** a development phase-suspect share > 20 % is reported to the lead before any seal patient is read.
- **JA53 — QC cuts, set once on development, and the B-spline arm.** (Settles Round 2 §7 item 5.)
  - **Provisional cuts until development:** the benchmark's (`bench_lie/scores.json`, `qc_cuts`), at the matching
    blood level.
  - **On development:**
    - each value's cut is the **95th percentile over reader-passed development patients**; the reader is blind to
      every QC value;
    - per protocol key when a key has ≥ 15 such patients, pooled otherwise;
    - the fat-like, blood-like and brighter-than-blood cuts are fitted as functions of the patient's own
      blood-to-remote contrast, (blood median − remote) / robust SD of remote, which needs no scar (Kilo);
    - `rim_dark`'s phase cut is its p95 over phase-matched, reader-passed patients;
    - a value that catches < 50 % of reader fails is dropped from the R0 gate and stays logged;
    - cuts are frozen in the JA28 freeze and never moved.
  - **B-spline** is not in the chain. It is opened as a development arm if either:
    - the development first-check reader-fail rate is > 10 %, or
    - the not-graded rate is > 2 %.

    It is first run on the benchmark's non-rigid motion in Round 4 (§7), with control spacing ≥ 20 mm and the 4 mm
    mask. Kilo's non-rigid case (1.6–1.8 mm residual after every stage, specificity 0.62–0.93) is otherwise left to
    the reader check and the yield bar.
- **JA54 — The final Scar-0 menu.** (Amends JA30; settles Round 2 §7 item 1.)
  - **Presence, in order: P-J, P-G.**
    - **P-K is struck.** Its code stays for the record and cannot be chosen.
    - **P-G is reinstated only under JA51's chain.** If Round 4's run of the shipped chain strikes it by the same
      pre-registered rules, it is struck before development.
  - **Extent: E-V, E-D.** **E-D's voxel cut is remote + 3 SD**, the same as E-V's (#188 reading 3, corrected). E-V
    and E-D then differ only in how they aggregate (volume share against depth extent), which is what JA30 compares.
  - **P-G's share** is called voxels over the segment's wall ≥ 1 mm from the carried endocardium, as the benchmark
    scored it.
  - **P-J's τ** is fitted after the registration chain and its cuts are frozen, on LGE-negative development segments
    registered by that chain. τ absorbs registration error (on the 10 mm chain it cost P-J its bin-1 sensitivity).
  - **Deepest u:** #188's reading 4 stands. The median over columns is reported beside it (Golf).
  - **Reported on development and the seal:** sensitivity by LGE Kim bin, and the bin-1 share.
  - **Unchanged:** the choice rule, the fixed constants and the freeze (JA30). Spill strikes nothing (≤ 0.09).
- **JA55 — How a not-graded patient counts.** (Amends JA29's last two bullets and JA32's "intention-to-diagnose";
  LQ25.)
  - **Primary analysis:**
    - a not-graded patient's **LGE-positive segments are misses**;
    - its **LGE-negative segments leave the specificity denominator** (Juliet A1);
    - a fourth deciding endpoint: **yield**, the not-graded patient share, with upper 95 % bound **≤ 0.10**.
  - **Reported beside it:** worst case (JA29 as written), no-call, and graded-only.
  - **A failure** is a patient not graded after two reader fails (#188 reading 2, confirmed). Phase-suspect patients
    (JA52) are counted separately and are not failures.
  - **JA29's > 10 % stop** on development stands. Development's measured failure rate feeds `seal_size` (JA57).
  - **Why not graded-only plus the guard:** the guard cannot fire at the expected three or so failed patients
    (§1.4). A1 charges selective failure to sensitivity without one.
- **JA56 — Two claims, tested in a fixed order.** (Amends JA32's acceptance rule; LQ26.)
  - **Claim 1, scar presence.** Lower bounds: sensitivity ≥ 0.75 and specificity ≥ 0.93; upper bound: yield ≤ 0.10.
    One look. Passing removes "not validated" from **presence** only.
  - **Claim 2, the Kim bin.** Tested only if claim 1 passes; no multiplicity cost.
    - The bar: the lower bound of exact-bin agreement on scar-on-both segments ≥ anchor − 0.10.
    - **The anchor:** reader 1 against reader 2, exact Kim bin on segments both call scar, unadjudicated, over
      **every double-read patient (development + seal)**. It is computed before any seal CT value is unblinded
      (Golf, Kilo). Development keeps its own estimate for re-powering.
    - **If the anchor is < 0.60, the Kim bin cannot be validated:** it keeps "not validated", and the endpoint is
      also reported against a fixed 0.50 bar.
  - **Everything JA32 lists as reported stays reported.** Its margins stay fixed.
- **JA57 — Seal size and enrichment.** (Amends JA28 and JA31; LQ27.)
  - **Seal = max(120; N for ≥ 270 ischaemic-pattern scarred segments; N for ≥ 80 % power on claim 1)**:
    - every input is measured on development: scarred segments per scar patient, clustering, sensitivity by bin and
      bin-1 share, and the not-graded rate;
    - the size is run by `janusm.scar.power` with JA55's accounting;
    - **capped at 240**, and it only grows.
  - **Enrichment target 70 % LGE-positive.** JA27's ≥ 30 % LGE-negative floor is unchanged.
  - **Claim 2 is powered only if development shows it can be.** If development CT bin agreement (point) is
    ≥ development anchor − 0.03, the size also covers claim 2 at 80 %, up to the cap.
  - **If it is more than 0.03 below, Scar-1 is triggered on extent** before any seal grading (extends JA31's trigger),
    even if presence passes. If Scar-1 also misses, claim 2 is scored once at the presence size, with no growth.
  - **Planning figures for the lead** (#187's engine, weak clustering, 2 % failure under JA55):
    - ≈ 40 development + **≈ 160 seal at 70 %**;
    - ≈ 200 at 50 %;
    - strong clustering takes it to the 240 cap.
- **JA58 — The read forms.** (Settles Round 2 §7 item 3; for JA35 item 5.)
  - **LGE segment read (`lge17`):**
    - **Served:** CMR series only (LGE short-axis, long-axis, cine if present). Never a CT, a scar output, a
      clinical report or the other read. A blinding attestation is the first field (Golf).
    - **Patient header:** quality (diagnostic / limited / non-diagnostic, which ends the read); coverage; artefact;
      sequence (PSIR / magnitude); and "no LGE in any segment" as a one-action fast path, with the bull's-eye still
      confirmed.
    - **Per segment 1–17:**
      - presence: yes / no / not assessable;
      - if yes, pattern: subendocardial, transmural, mid-wall, epicardial, or patchy / RV insertion;
      - if yes, Kim bin 1–4;
      - MVO (yes / no), report-only;
      - "unsure" tick, report-only.
    - **Kim-bin text on the form:** "your estimate of the share of this segment's myocardium that is hyperenhanced,
      over all the short-axis slices that make up the segment (Kim 2000's 'percent of tissue'). It is a share of
      tissue, not the depth at the deepest point."
    - **The example panel:** Golf's six schematics A–F (B and C are where E-V and E-D part company), drawn from
      geometry by Juliet's `lge_mockup.py`. No patient image.
    - **Server checks:** every segment answered; pattern and bin present exactly when presence is yes; "any LGE = no"
      inconsistent with a present segment is rejected; a non-diagnostic read makes the patient "LGE not assessable",
      excluded and counted.
  - **Adjudication (`lge17_adjudicate`; amends JA32; LQ28):**
    - a third CMR reader, **blind to both reads**, reads only the segments where the two disagree on presence, or on
      the Kim bin among segments both call scar;
    - **the reference** is the majority, else the median of the three bins;
    - **the anchor** (JA56) uses the two unadjudicated reads.
    - Juliet's A4 ("the lower of two adjacent bins") is not adopted: it biases the reference downward by up to half
      a bin and favours a low-reading CT.
  - **Registration check (`regcheck`):**
    - **Shown:** three short-axis planes at 25 / 50 / 75 % of the carried LV long axis, chosen by code. The first
      pass and the LIE side by side, carried borders on both, with a toggle to hide them.
    - **Blinding:** blind to LGE and the scar output. The QC values and the JA52 flags are shown only after the
      decision.
    - **Answers:** pass / fail per slice. Reasons: shifted; rotated; endocardium off; epicardium off; **cavity size
      differs (phase)**; artefact; other.
    - **On a fail:** the reader moves the **carried borders** (first pass is moving, JA29) once; the chain re-runs
      from that shift.
  - **Reader time:**
    - the queue stamps claimed and submitted times on every read kind (PS3-S11);
    - entry time is ≈ 1 min per scarred LGE read (all three keystroke-level estimates agree);
    - review time is measured on Juliet's five synthetic mock patients by the project's own readers (LQ28), and on the
      first 5 development patients;
    - if the median exceeds 15 min, LQ16's reader-hours are restated before any seal read is scheduled.
  - **Mock-up agreement:** Juliet A5 is not a gate. It is practice, with timing and agreement against `truth.json`
    reported.
- **JA59 — The intake checker, and the record.** (Settles Round 2 §7 item 4; for JA35 item 3.)
  - **Order, fail-closed:**
    1. manifest;
    2. `janusm.guard.refuse` on every pseudonym;
    3. the JA28 split by salted hash;
    4. **the de-identification gate.** It reads headers only and requires all of:
       - Patient Identity Removed = YES;
       - De-identification Method present;
       - Burned In Annotation = NO;
       - Longitudinal Temporal Information Modified = MODIFIED with **one constant shift per patient**, or manifest
         day offsets.

       **Any failure quarantines the batch unopened** (Juliet), and the lead is told on the issue by count only;
    5. per-series header checks;
    6. one row per patient (tier, strata, reasons) in the restricted collection. Counts only go to the repository.
       UIDs are compared in memory and written as "same / different".
  - **Outcomes** (Juliet §4's table, with these rulings):

    | Requirement | Outcome on failure |
    |---|---|
    | Frame of reference missing | stratum "no shared frame"; **seal-eligible**; registration starts at heart-masked rigid from the centroids |
    | First-pass slice > 0.75 mm | excluded |
    | **LIE slice > 1.0 mm** | **T1 only** (hard, for presence: Kilo §3.2) |
    | First pass ungated | excluded |
    | LIE ungated | T1 only |
    | LIE delay outside 4–12 min, or unrecorded | delay stratum; inside 4–12 min it stays in the primary |
    | Phase from text only | marked "inferred", and must pass JA52 |
    | Phase unmatched | phase-unmatched stratum, unless raw data allow a reconstruction at the LIE's phase |
    | A required field missing | **hold** until it arrives (Golf) |
    | CT–CMR ≤ 90 days, infarct age ≥ 90 days, events between scans, device, CABG | as JA27 and LQ15 |

  - **Test:** synthetic DICOM headers only, one patient per outcome row. Tag names are checked against pydicom's
    dictionary.
  - **Record:**
    - Golf's Mattes DOI is wrong; use `10.1109/TMI.2003.809072`;
    - P-G figures under the proposed registration in Kilo v3 and Golf v3 are v1's; v2's (`scores.json`) bind;
    - Kilo v3 §8's "no table writer" is stale;
    - Juliet v3 §3.3's "the queue stamps times" is wrong for `janusm_reads`;
    - JA36's held-out rule was kept by every note this round.

---

## 5. Questions for the lead (each with a recommendation; none is a fork)

**Carried as assumptions:**
- LQ2–LQ18, with their rulings' recommendations, except as updated here.
- **LQ13 (a)** now reads with JA57's 70 % target and 240 cap.
- **LQ17 (a)** now reads with JA55–JA56.

### LQ25 — How a patient whose registration fails counts (Juliet A1, Kilo §4.3, the PM's #179 note)

- **Options:**
  - (a) JA55: scarred segments missed, scar-free segments out of specificity, plus a yield bar ≤ 0.10;
  - (b) graded-only accuracy, a yield bar, and Kilo's selective-failure guard;
  - (c) JA29 as written (every segment wrong).
- **Recommendation: (a).** (c) fails the study at any N once failures reach 5 % (#187; Kilo E9). (b) has more power
  (≈ 120 against ≈ 160 at 70 %), but its guard cannot detect failures that fall on scarred hearts at the expected
  counts. (a) charges them to sensitivity.

### LQ26 — Two claims instead of one joint pass (Kilo §4, Golf §5)

- **Options:**
  - (a) JA56: presence is claimed on sensitivity, specificity and yield; the Kim bin is tested only after presence
    passes, against an all-patient reader anchor, and cannot pass if the readers' own agreement is < 0.60;
  - (b) JA32 as written: three endpoints jointly, with transmurality dropped silently when the anchor is < 0.60.
- **Recommendation: (a).** Kilo E9 and Golf E10 both show the transmurality bar needs CT to grade bins about as well
  as the readers. Under (b) that would fail a working presence call, and noisier readers would make passing easier.

### LQ27 — Enrichment and seal planning size

- **Options:**
  - (a) target 70 % LGE-positive; plan on ≈ 40 + 160, cap 240;
  - (b) 50 %; plan on ≈ 40 + 200;
  - (c) no cap.
- **Recommendation: (a).** At Kilo's infarct sizes the ≥ 270-segment floor alone needs ≈ 170–190 patients at 50 %
  (Golf E10), against ≈ 120–130 at 70 %. The cap stops chasing a claim that N cannot buy.

### LQ28 — LGE reader time: adjudication of every disagreement, and timing on a mock-up

- **Options:**
  - (a) JA58: a third blind CMR read on every presence or bin disagreement (about a third of scarred segments, at
    readers' agreement ≈ 0.7). Two of the project's own readers time the five synthetic mock patients before the
    cohort is pursued;
  - (b) JA32 as written (adjudicate ≥ 2-bin differences only; no mock timing);
  - (c) (a) without the mock timing.
- **Recommendation: (a).** The added third reads are segment-level and short. The mock timing is the only way to
  replace LQ16's assumed 10 min before the lead commits reader time. It uses no outside party and no patient image.

---

## 6. Forking question: **no fork**

The cap would allow one (2 of 4 paths active). No open question changes this path's structure:
- **LQ25–LQ28** change an accounting rule, a claim's order, a size or reader hours.
- **The registration choices** are settled by the benchmark and the module, and Round 4 re-tests them.
- **The real fork, whether a paired cohort exists at all,** is LQ1, which created this path.

---

## 7. What Round 4 on this path must settle, and what the path waits on

**Round 4 (CPU only; strike rules as pre-registered on #179):**
1. **Run the shipped chain through the benchmark** (after PS3-S1–S7): JA51's chain exactly as shipped, with
   Euclidean masks. Add these arms and conditions:
   - 4 mm affine under JA51's rule; the 10 mm fallback; a B-spline arm on the non-rigid motion (JA53);
   - a −5 % phase case (larger LIE cavity), for the edge offset;
   - Golf's anisotropic 3 % / 6 % scale.

   **P-G is struck if it fails there** (JA54). P-J's τ is re-fitted under the shipped chain.
2. **Re-run the power engine** with PS3-S8–S10: the JA57 planning table at 0 / 2 / 5 % failure, both clusterings, 50 %
   and 70 % enrichment, both infarct-size models. Reproduce Juliet E9 and Golf E10 cells within Monte-Carlo error.
3. **The mock-up timing,** if the lead takes LQ28 (a).
4. **The path summary** for #143 (§8, updated).

**The path otherwise waits on the lead:**
- **LQ1:** whether a paired CCTA + same-session LIE + CMR LGE cohort is pursued, and data access to it (D19, outside
  the repository);
- **Job JM-0 and JM-0R:** for Stage A numbers, shared with path A.

Without a cohort, the scar work stops at Round 4: nothing further can be learned on synthetic LIE.

---

## 8. Path B against path A, for the lead (Round 2 §8, updated)

| | Path A, `jm/rest-ccta` | Path B, `jm/paired-scar` (after Round 3) |
|---|---|---|
| Assumes | no reference for scar or ischaemia | the lead obtains a paired CCTA + same-session LIE + CMR LGE cohort (data requirements only, D31) |
| Stage A | built and calibrated; bias guard 0.3 mm (JA71) | **identical code** (JA50) |
| Scar rule | — | P-J or P-G, chosen on development; P-K struck; E-V or E-D (3 SD) |
| Registration | — | R0 → `rim_dark`-gated QC → 4 mm rigid → affine only if sane and better → reader check; a truth-free phase check routes mismatches out |
| What passing gives | specificity-calibrated flags | **presence** validated on sensitivity, specificity and yield; the **Kim bin** only if CT grades as well as the readers |
| Cohort | none | 40 development + ≈ 160 seal at 70 % enrichment (≈ 200 at 50 %); never more than 240 |
| Reader time | none | ≈ 200 × 2 CMR reads + adjudication (≈ 55 h, to be replaced by measured time) + a registration check per patient |
| Committed compute | ≈ 15 GPU-h | the same + ≈ 3 GPU-h once the cohort exists; scar on CPU |
| Main risk | flags with no measured sensitivity | the cohort never arrives; non-rigid misalignment or a high failure rate on real data; a Kim bin no better than the readers |
| If the cohort never arrives | — | path B reduces to path A exactly |

---

## 9. Shipping (`role:swe`, labelled `jm/paired-scar`; code on `jm/paired-scar` in `src/janusm/scar/` unless stated)

Each item is one issue. "Test" names the check that proves it. No item reads a held-out case. Tests run on synthetic
phantoms in CI. The 20 real hearts are used only in an offline script that calls the guard first.

### `registration.py`

- **PS3-S1 — The 4 mm Euclidean mask, with a 10 mm fallback** (JA51 steps 3, 5).
  - **Wrong:** `MASK_DILATION_MM = 10.0` (line 66) admits the static chest. E10 leaves 3.4 mm median after a 4.2 mm
    shift.
  - **Correct:** the margin is a parameter, default 4.0 mm Euclidean (`edt <= margin`). One 10 mm rigid fallback runs
    only if the final 4 mm stage fails QC. It replaces the result only if it passes QC, or lowers the normalised
    maximum. The fallback is logged as its own stage.
  - **Test:** the static-chest phantom (`tests/janusm_synth.py`), heart shifted 4 mm: 4 mm rigid TRE < 0.5 mm, and
    10 mm rigid TRE > 1.0 mm on the same case. The fallback runs only when the 4 mm stage's QC fails (a mocked QC).
- **PS3-S2 — `rim_dark` and the blood median** (JA51 step 2; #188 reading 5).
  - **Wrong:** `QC` has three values. The blood median is one voxel inside the cavity (`qc()`, line 137).
  - **Correct:** `QC.rim_dark` is the share of the carried cavity's 2 mm inner rim (Euclidean) below (remote + blood
    median) / 2. `QCCuts.max_rim_dark` is required. The blood median is ≥ 2 mm inside, or 1 voxel inside if fewer
    than 50 voxels remain. NaN fails closed.
  - **Test:**
    - a phantom with the LIE cavity shrunk 5 % has `rim_dark` above the aligned phantom's by ≥ 0.2;
    - a 1 mm-grid phantom with a bright wall shows the 2 mm blood median free of wall partial volume (equal to the
      true blood level within 1 %).
- **PS3-S3 — Affine acceptance** (JA51 step 4; #188 reading 1).
  - **Wrong:** `affine_lowers_qc` compares raw sums. The shares differ 5–50-fold with blood level (Kilo E8).
  - **Correct:** affine is kept iff:
    - |log det A| ≤ 0.15, and every singular value and shear term of A is within ± 15 % of identity; and
    - the QC values divided by their cuts show no rise, and their maximum falls.
  - **Test:**
    - unit cases (sanity bound violated; one normalised value rises; maximum falls);
    - a phantom with a 3 % scale keeps affine;
    - a rigid-only 4 mm shift phantom where affine increases TRE rejects it.
- **PS3-S4 — The phase step** (JA52).
  - **Wrong:** there is no phase output; a phase mismatch passes as registered.
  - **Correct:**
    - `edge_offset_mm`: the signed distance from the carried endocardium, half-voxel corrected, at which the mean
      smoothed-LIE profile over the 6 remote segments crosses half-way between blood (−6 to −3 mm) and remote wall
      (+1.5 to +3.5 mm), in 0.5 mm bins. Kilo E8's definition; JA44's canonical sign, with conversion documented.
      Its per-segment IQR is logged too;
    - the affine log-determinant is logged;
    - a status `phase_suspect`, separate from passed / re-registered / not graded. It stops further registration
      and is excluded from `failure_rate`;
    - "not evaluable" when blood − remote < 2 robust SD.
  - **Test:**
    - phantoms at +5 % and −5 % cavity change are flagged (`rim_dark` for +5 %, the edge offset for −5 %);
    - the aligned phantom is not;
    - `failure_rate` ignores `phase_suspect`.
- **PS3-S5 — Fitting the QC cuts on development** (JA53).
  - **Wrong:** `QCCuts` has no fitting function.
  - **Correct:** `fit_qc_cuts(records)`:
    - **input:** development records (QC values, the reader's first-check pass or fail, protocol key, blood-to-remote
      contrast). JA12 guard first; fails closed;
    - **cuts:** p95 over reader-passed records, per protocol key with ≥ 15, pooled otherwise. The three shares are
      fitted against blood-to-remote contrast (a monotone fit, p95 band). `rim_dark`'s phase cut is fitted on
      phase-matched records;
    - **drop rule:** a value catching < 50 % of reader fails is marked `gate=False`;
    - **output:** a frozen JSON for `configs/janusm/paired-r2.json`;
    - **provisional cuts:** a loader for `bench_lie/scores.json` `qc_cuts`.
  - **Test:** synthetic records with known quantiles reproduce the cuts; a value uncorrelated with reader fails is
    dropped; a non-guarded id raises.

### `scar0.py`

- **PS3-S6 — The final menu** (JA54; #188 readings 3, 4).
  - **Wrong:**
    - E-D's voxel cut is P-K's half-way cut (line 329);
    - P-G's share is over the whole segment (line 335);
    - P-K is choosable.
  - **Correct:**
    - E-D uses `above_sd` (remote + 3 SD);
    - `share_pg` = called voxels / segment voxels with `d_endo_mm() >= 1.0`;
    - `PRESENCE = ("P-J", "P-G")`, with P-K still computed under a diagnostic key;
    - `deepest_*_median` (median over columns) added;
    - `for_scoring()` returns the per-segment Kim bin so scoring can report sensitivity by LGE bin.
  - **Test:**
    - a phantom where half-way and 3 SD cuts differ shows E-D following 3 SD;
    - a segment with a 1 mm endocardial rim of scar only gives `share_pg = 0`;
    - `choose_presence({"P-K": …})` raises.
- **PS3-S7 — The benchmark as a regression fixture** (JA54; Juliet §9).
  - **Wrong:** nothing ties the module to the benchmark that decided the menu.
  - **Correct:**
    - a CI test runs `bench_lie.bench.make_case` on the **phantom** heart (no download) for the striking conditions.
      It grades with `menu.grade` and with `scar0` on the oracle geometry, and asserts per-segment `ev`, `ed` and
      `pg_share` agree within 0.02;
    - an offline script `experiments/JanusM/bench_lie/module_parity.py` (guard first) does the same on the 20 real
      hearts and writes `module_parity.json`.
  - **Test:** the CI parity test passes; the script's summary is committed by the Round 4 advocates.

### `power.py` / `scoring.py`

- **PS3-S8 — JA55 accounting and the yield endpoint.**
  - **Wrong:** not-graded segments are scored only worst-case.
  - **Correct:** `itd_mode ∈ {"split", "worst", "nocall", "graded"}`, with `"split"` the default. Plus
    `yield_upper_bound` (patient bootstrap) and its ≤ 0.10 bar inside `decide`.
  - **Test:**
    - reproduce Juliet E9's split cells (N 200 at 50 %, 160 at 70 %, 2 % failure, weak clustering) within
      Monte-Carlo error;
    - reproduce Kilo E9's worst / no-call / graded cells;
    - a hand-built study with one failed scarred patient lowers sensitivity and leaves specificity unchanged under
      `"split"`.
- **PS3-S9 — Two claims** (JA56).
  - **Wrong:** `decide` tests three endpoints jointly and drops transmurality silently below 0.60.
  - **Correct:**
    - `decide` returns `presence_validated` and `kim_bin_validated`;
    - the second is evaluated only if the first passes;
    - the anchor is computed over all double-read patients from the two unadjudicated reads;
    - an anchor < 0.60 gives `kim_bin_validated = False`, with the 0.50-bar result reported.
  - **Test:** unit studies for each branch (presence fails; presence passes and the bin passes; the anchor is 0.55).
- **PS3-S10 — `seal_size` per JA57.**
  - **Correct:**
    - inputs: development failure rate, scarred segments per scar patient, extent error (per bin), sensitivity by
      bin, enrichment;
    - the cap is 240;
    - claim 2 enters the power target only if the development gap is ≥ −0.03.
  - **Test:** reproduce Golf E10's `segments_needed` (167 / 119, Kilo infarct size) and #187's 136 / 97 within
    Monte-Carlo error; the cap binds under strong clustering at 50 %.

### `src/janusm_reads/` (Janus-M read queue)

- **PS3-S11 — Read timing, and the three form kinds** (JA58).
  - **Wrong:** reads carry no claimed or submitted time (§1.5). The LGE and registration-check forms do not exist.
  - **Correct:**
    - **now:** every read records `claimed_at` and `submitted_at` (UTC) and exports their difference with no
      identifier;
    - **when the lead pursues the cohort, or takes LQ28 (a):** JSON form kinds `lge17`, `lge17_adjudicate` and
      `regcheck`, with JA58's fields and server checks (Golf's `forms/*.json` as the schema). Blinding is served by
      read set. The adjudicator sees only triggered segments. Plus a JanusMRead view with three planes and two
      images.
  - **Test:**
    - a timing round-trip on the phantom queue;
    - the server rejects each JA58 inconsistency;
    - Juliet's `mock_lge/truth.json` submitted as a read passes the checks;
    - the adjudication trigger fires on a 1-bin difference.

### `src/janusm/scar/intake.py` (new)

- **PS3-S12 — The intake checker** (JA59). It waits until the lead pursues the cohort.
  - **Correct:** JA59's order and outcome table. It reads headers only (pydicom, `stop_before_pixels=True`) and writes
    no identifier, date or UID.
  - **Test:** a synthetic header set (pydicom, no pixel data), one patient per outcome row, plus one batch with a
    burned-in flag that must be quarantined whole; tag keywords are asserted against pydicom's dictionary.
