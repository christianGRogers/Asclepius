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

{{SUMMARY}}

## 2. Evidence this round (CPU; code in `experiments/JanusM/Golf/`; notes in `vault/JanusM/Experiments/`)

{{EVIDENCE}}

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

{{ITEM1}}

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
patients at 50 % enrichment**. That makes the segment floor, not the 120-patient floor, the binding size at 50 %.

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
   wall share); E8 (§4) shows how far the Scar-0 extent measures are from that.

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
| Shared frame of reference | `FrameOfReferenceUID` (0020,0052) equal across the CCTA and LIE series | **R0 unavailable**: the patient stays in T2, but the chain starts at rigid (JA29 step 3). Reported as a stratum |
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

{{ITEM5}}

## 9. §7 item 6: the JA25 hand-over

Checked on 2026-10-30 against the remote branches, by file and by `git diff` (no code run):

| Shared Stage A code (JA25) | On `jm/rest-ccta` | On `dev` | On `jm/paired-scar` |
|---|---|---|---|
| JA15 harness, `src/janusm/harness.py` + `tests/test_janusm_harness.py` | yes | **yes, byte-identical** (#180, merged as #183) | **not yet** |
| JM-0R, `experiments/JanusM/fir/jm0r_readout.py` + `tests/test_janusm_jm0r_readout.py` | yes | **yes, byte-identical** (#183) | **not yet** |
| Geometry module, `src/janusm/geometry.py` | yes | yes, identical | yes, identical |
| #177's additions to `tests/test_janusm_geometry.py` | yes | yes, identical | **not yet** (24 lines behind `dev`) |
| JA19 table writer (Tables A and B) | **not built** | no | no |

- **One implementation is in place on the trunk.** Both pieces this path needs from path A are on `dev` with no
  diff against `jm/rest-ccta`.
- **What is left is a sync, not code:** the PM merges `dev` into `jm/paired-scar` (#180's acceptance says the PM
  syncs into both paths). This PR does not do it: it would bring trunk changes into an advocate PR. Until then, no
  path-B code may import `janusm.harness`.
- **The table writer does not exist on either path yet** (JA19, a `role:swe` item on `jm/rest-ccta`). When it is
  built there, it moves to `dev` the same way, and JA33 (§10) scores its output, not a path-B copy.
- **JM-0R's numbers:** none exist yet. JM-0R runs after Job JM-0 (LQ11), and no JM-0 aggregate has been returned.
  When it is, this path applies the same pre-registered decisions as `jm/rest-ccta`, with no path-B variant:
  - JA17's three conditions decide whether rest TPR enters the table;
  - JA18's fat cut is set provisionally, and Lima's detectable-depth simulation is re-run with the measured `cv_n`;
  - JA20's septal-arc column is dropped if < 10 % of mass changes segment, and the geodesic-vs-Euclidean
    disagreement is recorded. **On this path the territory method is then decided by JA33's culprit-vessel test**,
    not by the ≥ 10 % rule (JA33).
  - **One path-B use:** JM-0R's endocardial half-maximum offset and 10–90 % edge width on first-pass CCTA set the
    expected E9 offset spread on the paired cohort's first pass (§8.2), so a phase flag is judged against the
    first pass's own edge width.
- **Golf E7 (`Golf/harness.py`)** stays a test reference only, as JA25 says; it is not imported anywhere.

## 10. §7 item 7: path summary for the lead

{{ITEM7}}

## 11. Code that must ship (specs; built by `role:swe`, not in this PR)

What each JA35 item needs from this round. The PM opens and assigns the issues (JA35); Golf builds none of
them here.

1. **LIE registration module (#181, JA35 item 1).** In addition to the chain, QC and logging:
   - log, per patient and stage, the transform's **translation norm and log-determinant**, and E9's **edge
     offsets** (median endocardial and epicardial offset, and dthick; `lie_menu.edge_offsets` is the reference
     implementation, on a half-voxel signed distance);
   - the QC rule is "all QC values ≤ their cuts", with the cuts a **config input** (set once on development, §8.1),
     never constants in code;
   - affine is kept only if **every** QC value is ≤ rigid's (JA29 step 4, read literally); ties keep rigid;
   - fixtures: Juliet E6's static-chest phantom, Kilo E5's case, and one `bench_lie` case per motion type
     (chest, static, phase5).
2. **Scar-0 module (#181, JA35 item 2).** Every JA30 candidate, with JA30's constants as defaults. Three
   details the ruling leaves open, which E8 had to fix and which the module should fix the same way:
   - "core" = voxels ≥ 1 voxel inside both carried borders = one binary erosion of the carried wall;
   - P-K's "brightest segment" = the highest **core median**, and its p99 is over that segment's core;
   - E-D's voxel threshold is P-K's half-way threshold (Juliet's rule), with a 3 SD variant (E-D3) behind a flag;
   - plus §4's struck list: a candidate struck on the benchmark stays in the module (for the record) but is
     removed from the JA30 menu config.
3. **Power and scoring (#182, JA35 items 4 and 6).** Use `experiments/JanusM/Golf/power_ja32.py` as the merged
   reference: it already joins Golf R2 E6's clustering and bootstrap with Kilo R2 E6's continuous transmurality and
   territory model, and adds the two readers and the JA32 anchor. The module should:
   - reproduce `power_ja32.json` within Monte-Carlo error (a regression test);
   - expose the anchor source as a parameter (development only, as JA32 says, or every patient's double read,
     §5.3), so the lead's choice is a config line;
   - report each endpoint's power separately as well as jointly, since the transmurality endpoint binds (§5).
4. **The shared benchmark** (`experiments/JanusM/bench_lie/`, Juliet, #179) is experiment code, not shipped. Its
   generator becomes the #181 test fixture source. It should carry `mask_source` per heart (TS v1 at 1.5 mm vs
   v2.0.1 at 1 mm), and call `janusm.guard.refuse` on the whole list before any download.
5. **Intake checker (JA35 item 3):** §7's tables as code, tested on synthetic DICOM headers; outputs as §7.5.
   Waits until the lead pursues the cohort (JA35).
6. **Read forms (JA35 item 5):** `forms/lge_read_form.json` and `forms/reg_check_form.json` as the queue's form
   definitions, in a new read set each, served only from the restricted paired collection. The JanusMRead module
   needs one new view for the registration check (three planes, two images side by side, borders on both).
   Waits until the lead pursues the cohort (JA35).

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
