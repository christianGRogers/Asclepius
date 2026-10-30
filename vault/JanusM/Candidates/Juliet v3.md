---
tags: [janus-m, plans, candidate, scar, lie, path-b]
author: Juliet
round: 3
version: 3
path: jm/paired-scar
updated: 2026-10-30
issue: christianGRogers/Asclepius#179
---

# Juliet v3: one benchmark for every scar rule, and the forms, intake checks and QC cuts that make the paired study runnable

**Path `jm/paired-scar`.** The plan in force is the Master plan on this branch: [[Kilo v2]] with JA25–JA36, on the
trunk (JA1–JA14) and path A's Stage A (JA15–JA24, by JA25). **Juliet v3 is that plan, unchanged except where
§10 proposes an amendment, plus the seven settlements Round 2 §7 asks for.** Every JA binds.

## 0. What this candidate settles

| Ruling §7 item | Where | In one line |
|---|---|---|
| 1. One shared synthetic-LIE benchmark | §1, `experiments/JanusM/bench_lie/` | [BENCH-ONE-LINE] |
| 2. The merged power script at the JA32 bars | §2 | [POWER-ONE-LINE] |
| 3. LGE read form and registration check form | §3, `experiments/JanusM/Juliet/r3/` | written for the Janus-M queue, with a synthetic LGE mock-up (5 patients with truth) and an example panel; form-entry time estimated, viewing time measured on the mock-up by the queue's own timestamps |
| 4. JA27 intake checker | §4 | every JA27 requirement mapped to a DICOM attribute or a manifest field, with what a failing patient becomes |
| 5. Registration QC cuts, and a phase check | §5 | [QC-ONE-LINE] |
| 6. JA25 hand-over | §6 | harness and JM-0R are on `dev` (#183); this branch has not synced `dev` yet; the table writer is not built; JM-0R has not run, so there are no numbers to apply |
| 7. Path summary for the lead | §7 | updated |

## 1. The shared synthetic-LIE benchmark (item 1)

[BENCHMARK SECTION]

## 2. The merged power script (item 2)

[POWER SECTION]

## 3. The LGE read form and the registration check form (item 3)

Both are read kinds in the Janus-M read queue (`src/janusm_reads/`, `slicer/JanusMRead/`), served apart from the
border reads and from SegQueue14. The form is a JSON submission validated by the server, not a label map. Built by
JA35 item 5 when the lead pursues the cohort; specified here.

### 3.1 LGE segment read (`kind = "lge17"`)

**Who and what.** Two CMR readers per patient, independently, **blind to every CT and to each other** (JA32). The
queue serves only the CMR series of the patient (LGE short axis, LGE long axes, cine if present) and never the CT,
the LIE, the pipeline's output or the other reader's form. A third reader adjudicates (§3.1.4).

#### 3.1.1 Patient header

| Field | Values | Rule |
|---|---|---|
| `quality` | diagnostic / limited / non-diagnostic | non-diagnostic ends the form; the patient is "LGE not evaluable" (excluded from scoring, counted) |
| `sequence_used` | PSIR / magnitude IR / both | as read |
| `nulling` | adequate / myocardium not nulled | "not nulled" → `quality` cannot be diagnostic |
| `any_lge` | yes / no | **no** sets every segment to absent in one action (the fast path for LGE-negative patients) |

#### 3.1.2 Per segment 1–17 (AHA, Cerqueira 2002)

| Field | Values | Rule |
|---|---|---|
| `evaluable` | yes / no (artefact, not covered, partial volume at the base or apex) | "no" segments are excluded from the segment's scoring and counted |
| `present` | yes / no | LGE that a reader would report clinically |
| `pattern` | ischaemic-subendocardial / ischaemic-transmural / non-ischaemic-mid-wall / non-ischaemic-epicardial / patchy-indeterminate | required if present; any non-ischaemic or patchy pattern puts the segment in the JA27 non-ischaemic stratum |
| `kim_bin` | 1 (1–25 %) / 2 (26–50 %) / 3 (51–75 %) / 4 (76–100 %) | required if present; definition below |
| `mvo` | yes / no | a dark core inside enhancement (report-only) |
| `unsure` | tick | optional; ticked when torn between two bins (the lower is entered) |

**The Kim bin, as JA32 defines it:** *the reader's estimate of the hyperenhanced share of the segment's myocardium*
("percent of tissue", Kim 2000, [10.1056/NEJM200011163432003](https://doi.org/10.1056/NEJM200011163432003); its
segment-scoring definition is unverified from the abstract, JA36). Concretely:
- **Share, not depth.** Estimate the share of the whole segment's myocardium that is enhanced, over every slice
  that holds the segment. A scar reaching 80 % of the wall's depth over half the segment's arc is about 40 %:
  bin 2, not bin 4.
- **Segments by slices.** Basal, mid and apical short-axis thirds; 6, 6 and 4 sectors; 17 is the cap beyond the
  cavity. Sector zero is the anterior RV insertion.
- **On a boundary,** enter the lower bin and tick `unsure`.
- **Example panel:** `experiments/JanusM/Juliet/r3/lge_bin_panel.png`. It shows one synthetic mid-ventricular short
  axis per bin (14, 36, 62 and 91 % of segment 8), plus a mid-wall and an epicardial pattern. The panel is
  synthetic, drawn from geometry in `lge_mockup.py`. No patient image is in it.

#### 3.1.3 Checks the server runs on submit

- Every segment has `evaluable`, and every present segment has a pattern and a bin.
- `any_lge = no` with a present segment is rejected.
- A form that marks a segment present and non-evaluable is rejected.

#### 3.1.4 Adjudication (`kind = "lge17_adjudicate"`)

- **Triggered per segment:** the two reads disagree on `present`, or differ by ≥ 2 bins (JA32).
- **What the third reader sees:** the CMR plus both forms for the triggered segments only. They choose one of the
  two answers or enter their own.
- **The reference** is the adjudicated value where triggered, else the two readers' shared presence and the **lower
  of two adjacent bins**. Taking the lower bin is pre-registered so the reference does not depend on reader order.
- **Development inter-reader agreement (JA32's anchor)** is computed on the two **unadjudicated** reads.

### 3.2 Registration check (`kind = "regcheck"`, JA29)

| Shown | Not shown |
|---|---|
| Three short-axis slices (basal, mid, apical) of the LIE with the carried borders (endocardium, epicardium) over it, beside the same slices of the first pass with its own borders | LGE, the scar output, the QC numbers (shown only after the decision, to avoid anchoring) |

| Field | Values |
|---|---|
| `decision` | pass / fail |
| `reason` (if fail) | borders in blood / borders in fat / rotated / wall thickness differs between scans (phase) / LIE artefact / other |
| `shift_mm` (if fail) | a manual initial shift (x, y, z), used for one re-registration |

- A second fail makes the patient "not graded". In the primary analysis that counts every segment as wrong (JA29).
- **"Wall thickness differs between scans" is a reason of its own.** A phase mismatch is what no QC number catches
  (Juliet R2 E6; §5). The reader is the remaining check, and the reason feeds the phase stratum.

### 3.3 Reader time

**The ruling asks for reader time "measured on a mock-up".** Nobody in this round can sit a CMR reader in front of
a mock-up, so this candidate supplies the mock-up, a measurement that needs no new tool, and an estimate.

- **The mock-up.** `experiments/JanusM/Juliet/r3/mock_lge/`: 5 synthetic patients, short-axis LGE stacks of 10 slices
  (8 mm, 1.5 mm in-plane), with `truth.json` per segment (presence, pattern, share, Kim bin).

  | Mock patient | Content |
  |---|---|
  | A | no LGE |
  | B | LAD scar in bins 1–4 |
  | C | inferior transmural scar |
  | D | non-ischaemic mid-wall stripe |
  | E | small lateral bin-1 scars, plus an epicardial scar |

  The images are drawn from geometry; no case is opened.
- **The measurement.** The queue already stamps `assigned` and `submitted` per read (`src/janusm_reads/protocol.py`).
  Each CMR reader reads the five mock patients through the real `lge17` form before any cohort read. The median
  `submitted − assigned` per patient is the measured reader time, and agreement with `truth.json` is the reader's
  qualification:
  - bin agreement ≥ 0.80 on the mock scarred segments;
  - every pattern correct on D and E.
- **Form-entry estimate (keystroke-level model;** Card, Moran & Newell 1980,
  [10.1145/358886.358895](https://doi.org/10.1145/358886.358895): mental act 1.35 s, pointing 1.1 s, keystroke or
  click about 0.2 s):
  - an LGE-negative patient takes about 10 s (the header plus `any_lge = no`);
  - a scarred segment takes about 9 s (three decisions of about 2.65 s each, plus MVO);
  - a patient with 4 scarred segments takes about 50 s of entry.
- **Viewing time** dominates and is not modelled. The ruling's 10 min per reader per patient (LQ16) stays the
  planning figure until the mock-up timing replaces it. The registration check is about 10 s of entry plus viewing.
  The ruling's 3 min stays the planning figure.

## 4. The JA27 intake checker (item 4)

Runs on a batch before any pixel of it is read for analysis. Built by JA35 item 3. Order matters: steps 1–2 read no
DICOM at all.

1. **Manifest and guard.**
   - **Required per patient:** pseudonym, tier claimed, age band, sex, day offsets (index MI → CT, CT → CMR, CT →
     FFR), events between the scans (MI, PCI, CABG, surgery: yes/no), prior CABG, device, culprit or revascularised
     vessel (if known), haematocrit (optional).
   - `janusm.guard.refuse(pseudonyms, ...)` runs on the whole manifest. **Any hit refuses the batch.**
   - The JA28 split is assigned now, from the pseudonym, before any image exists for the project.
2. **De-identification gate (headers only, no pixel data).**
   - **Longitudinal Temporal Information Modified (0028,0303) must be `MODIFIED`.** Dates are shifted, per DICOM
     PS3.15 Annex E, "Retain Longitudinal Temporal Information With Modified Dates Option", which keeps intervals
     within a patient.
   - Patient's Name and ID equal the pseudonym or are empty.
   - Burned In Annotation (0028,0301) is `NO`.
   - **A failure quarantines the whole batch unopened**, and the lead is told on the issue. No name, date or
     accession number is ever written to the repository, an issue or a PR (JA27).
3. **Per-series header checks** (DICOM PS3.6 names), and what a failing patient becomes:

| Requirement (JA27) | Attributes read | Pass | Fail → |
|---|---|---|---|
| CCTA and LIE in one session | Study Instance UID (0020,000D) equal | same study | not T2 (T1 if CMR present) |
| Shared frame of reference | Frame of Reference UID (0020,0052) equal; Image Position/Orientation (Patient) (0020,0032/0037) present | same FoR | **seal-ineligible** (registration starts from a centroid, not R0); development or stratum "no shared frame" |
| Gated, both scans | Cardiac Synchronization Technique (0018,9037) ≠ NONE; Cardiac Signal Source (0018,9085) | gated | not T2 |
| Phase recorded, both scans | Nominal Percentage of Cardiac Phase (0020,9241); else Nominal Cardiac Trigger Delay Time (0020,9153) or Trigger Time (0018,1060) with Heart Rate (0018,1088), % = delay ÷ (60 000 / HR) × 100; else a "NN %" in Series Description (0008,103E) or Image Comments (0020,4000), flagged "phase from text" | a phase for each | **phase-unmatched stratum** |
| Phase matched | the LIE's % R-R within 5 of some CCTA series' % R-R (each reconstructed phase is its own series) | matched (the closest CCTA series is used) | **phase-unmatched stratum** unless the manifest says raw data allow a reconstruction at the LIE's phase |
| LIE delay 5–10 min | Acquisition Time (0008,0032) of the LIE minus Contrast/Bolus Start Time (0018,1042), else minus the first-pass Acquisition Time | 5.0–10.0 min | stratum "delay off-protocol"; unrecorded → stratum "delay unrecorded" |
| First-pass slice ≤ 0.75 mm, LIE ≤ 1.0 mm | Slice Thickness (0018,0050); spacing from Image Position (Patient) | within | seal-ineligible; stratum "thick slices" |
| Protocol fields recorded | KVP (0018,0060), Convolution Kernel (0018,1210), Manufacturer (0008,0070), Manufacturer's Model Name (0008,1090), CTDIvol (0018,9345), Multi-energy CT Acquisition (0018,9361), Image Type (0008,0008) | recorded | missing values recorded as missing. They are protocol keys: P-J's τ and the LQ14 strata group by (vendor, energy mode, kV band, delay band) |
| CMR LGE, base to apex + long axes | Magnetic Field Strength (0018,0087), Sequence Name (0018,0024), Inversion Time (0018,0082); short-axis slice count × spacing ≥ the CCTA LV length | covered | not T1/T2 (no reference) |
| CT → CMR ≤ 90 days | manifest offset | ≤ 90 | 91–180: stratum (LQ15 c fallback); > 180: excluded |
| Infarct age ≥ 90 days before both scans | manifest offset | ≥ 90 | **acute stratum**; unknown MI date with LGE scar → stratum "MI age unknown" |
| No event between the scans | manifest | none | **excluded** |
| No device artefact over the LV | manifest, then the registration check's "LIE artefact" | none | **excluded** |
| Prior CABG | manifest | — | kept for scar; left out of territory analyses (JA27) |
| Non-ischaemic pattern | the LGE read (§3.1), after intake | — | **non-ischaemic stratum** (per segment) |

- **Output:** per patient, the tier, the split, the stratum list and the reasons, written to the restricted
  collection with `configs/janusm/paired-r2.json`'s freeze (JA28). Counts only go to the repository.
- **The checker's own test** is a synthetic DICOM set (pydicom, no pixel data from any person), with one patient
  per failure row above.

## 5. Registration QC cuts, and a phase check (item 5)

[QC SECTION]

## 6. The JA25 hand-over (item 6)

| Shared Stage A code | Status (2026-10-30, 08:00 UTC) |
|---|---|
| JA15 harness `src/janusm/harness.py` + tests | **on `dev`** (#180, merged as #183) |
| JM-0R `experiments/JanusM/fir/jm0r_readout.py` + tests | **on `dev`** (#183) |
| The table writer (JA18, JA19) | **not built**: `jm/rest-ccta`'s Round 3 (#167, item 4) is specifying it |
| On `jm/paired-scar` | **neither yet**: `dev` has not been merged into this branch since #183 |
| JM-0R's numbers | **none**: Job JM-0 has not been run, so there is nothing to apply |

**What this path does, pre-registered:**
1. **The PM merges `dev` into `jm/paired-scar`** once #183 is in (a sync, not a candidate change). Both paths then
   import one `janusm.harness` and one `jm0r_readout.py`. Juliet's `fir/edges_m0.py` stays unrun (LQ18).
2. **The table writer** is built once, on `dev`, from `jm/rest-ccta`'s specification, and synced into both paths.
   This path writes no variant (JA33 validates path A's table, not a variant of it).
3. **JM-0R's numbers:** when the lead posts JM-0R's aggregate JSON on #142 and #143, this path applies **the same
   decision procedure `jm/rest-ccta`'s Round 3 ruling adopts**, verbatim, with no path-B parameter. Path B adds no
   Stage A rule (JA25).

## 7. Path summary for the lead (item 7, Round 2 §8 updated)

[PATH SUMMARY]

## 8. Assumptions carried

- **LQ2–LQ8** (Round 1), **LQ9–LQ12** (`jm/rest-ccta` Round 2, binding here by JA25), and **LQ13–LQ18** (Round 2 on
  this path), each on its ruling's recommendation:
  - LQ13 (a): T2 primary, 40 + ≥ 120, ≥ 270 scarred segments, no claim below 80;
  - LQ14 (a): single-energy accepted and stratified;
  - LQ15 (a): ≤ 90 days and MI ≥ 90 days;
  - LQ16 (a): two CMR readers on every patient;
  - LQ17 (a): JA32's bars;
  - LQ18 (a): JM-0R, not `edges_m0.py`.
- **No new lead question** except the one §10 raises.

## 9. Code that must ship (specified, not built; `role:swe`, opened by the PM, JA35)

1. **#181 (registration and Scar-0):**
   - Its tests should include **`experiments/JanusM/bench_lie/` as a regression fixture**. The module, run on the
     benchmark's cases, must reproduce `bench_lie/scores.json` within Monte-Carlo error, arm by arm.
   - `bench_lie/menu.py` is the reference implementation of the ruling's text, not the module.
2. **The `lge17`, `lge17_adjudicate` and `regcheck` read kinds** (§3): a JSON-form read type in `janusm_reads`, the
   server checks of §3.1.3, and the Slicer panel. Test on `r3/mock_lge/` only.
3. **The intake checker** (§4), tested on a synthetic DICOM set.
4. **#182** re-runs as §2 states.

## 10. Proposed amendments for the judge

[AMENDMENTS]

## 11. Held-out record and limits

- **Hearts:** 23 public TotalSegmentator v2.0.1 cardiac CTs (the union of Golf's 22 and Kilo's 15). The whole list
  went through `janusm.guard.refuse(..., source="TotalSegmentator")` before the first byte was fetched (guard v2,
  711 refused overall): **0 of the 23 refused**. The guard runs again per heart in `bench.load_heart`. Images stayed
  outside the repository; no case id appears in an experiment note except as a heart label in the shared lists
  Golf and Kilo already committed. No twin was used.
- **The LGE mock-up** is drawn from geometry; no case is opened.
- **Limits:** [LIMITS]
