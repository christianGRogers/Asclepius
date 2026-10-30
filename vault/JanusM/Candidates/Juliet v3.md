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
| 1. One shared synthetic-LIE benchmark | §1, E8, `experiments/JanusM/bench_lie/` | 630 cases on 20 real hearts and the phantom, with rules pre-registered and agreed with Golf and Kilo. **P-K struck** (calls scar in scar-free hearts). **P-G: verdict open** until the v2 re-run (v1 lacked JA30's endocardial exclusion; disclosed on #179). **P-J, E-V and E-D survive.** P-G's spill share is 0.00–0.02 |
| 2. The merged power script at the JA32 bars | §2, E9 | #187's run gives a 120–240-patient seal. But at a 2 % registration-failure rate, JA29's per-segment intention-to-diagnose keeps joint power below 0.80 at every N ≤ 320; a split accounting needs 160–200 |
| 3. LGE read form and registration check form | §3, `experiments/JanusM/Juliet/r3/` | written for the Janus-M queue, with a synthetic LGE mock-up (5 patients with truth) and an example panel; form-entry time estimated, viewing time measured on the mock-up by the queue's own timestamps |
| 4. JA27 intake checker | §4 | every JA27 requirement mapped to a DICOM attribute or a manifest field, with what a failing patient becomes |
| 5. Registration QC cuts, and a phase check | §5, E8 | Cuts at the 95th percentile of aligned development cases, plus a new check, **`rim_dark`**. It catches phase mismatch (AUC 0.98–0.99, where the JA29 trio scores 0.07–0.56) and misregistration (0.988). With a **4 mm** MI mask, the 4 mm-shift residual falls from 1.33 to 0.30 mm (median) |
| 6. JA25 hand-over | §6 | **complete**: the harness, JM-0R v2, the decision script, `calibrate` and the table writer are all on `dev` and synced here (#222); this path runs `jm0r_decide.py` unchanged when the lead posts JM-0R; JM-0 has not run yet |
| 7. Path summary for the lead | §7 | updated |

## 1. The shared synthetic-LIE benchmark (item 1)

Golf and Kilo agreed on #179 that Juliet builds it and that all three use it (Golf's E8 is a cross-check on his own
generator). The full note is [[Juliet - On the shared LIE benchmark P-K and P-G are struck under JA29 registration, and a 4 mm mask with a cavity-rim check fixes registration and catches phase mismatch]].

**What it is.**
- **Hearts:** 23 guard-checked public TotalSegmentator v2.0.1 hearts (Golf's 22 ∪ Kilo's 15; 0 refused). 20 had LV
  contrast. Juliet's R2 phantom is added.
- **First pass:** the real first-pass CT and labels.
- **LIE:** synthetic inside the heart, the real chest outside.
- **Grid:** blood below, equal to or above scar × CNR 3 or 5 × five motions:
  - none;
  - the heart moving 4 mm against a static chest;
  - + 3 % scale;
  - + 5 % phase change;
  - Kilo's whole-image non-rigid motion.

  That is **630 cases**.
- **Truth** is both volume share and depth extent. Golf's scar mix is used, which includes thin bin-1 scars.
- **Per case,** the scarred LIE, its scar-free twin and a blood→remote copy share one noise draw.
- **Arms:** every JA29 stage, the emulated chain, two variants and an oracle.
- **Re-use:** `results.jsonl.gz` holds every per-segment value, so any rule can be re-scored without re-running.

**Strikes, by the rules pre-registered on #179** (JA29 chain, CNR 5, motion none or rigid):

| Menu item | Verdict | Why |
|---|---|---|
| P-K | **struck** | specificity on scar-free hearts 0.006–0.31, and 0.006–0.056 even on true borders: its half-way threshold re-fits to noise when a heart has no scar |
| P-G | **open (v2 re-run)**. In v1, struck as JA29 stands | v1's P-G lacked JA30's 1 mm endocardial exclusion (a benchmark bug Golf found; disclosed on #179). v1, without the exclusion: specificity 0.78–0.86 when the heart moves, from registration; on true borders 0.99–1.00; with §5's registration ≥ 0.985. The v2 verdict replaces this line |
| P-J | survives | sensitivity 0.76–0.84; both specificities ≥ 0.96. Its bin-1 sensitivity is 0.00–0.30 on the chain. With §5's registration, its sensitivity is ≥ 0.89 (bin 1: ≥ 0.60) |
| E-V / E-D | both survive | exact bin agreement on scar-on-both 0.90 / 0.89 (volume truth), 0.94 / 0.93 (depth truth) |

- **The spill share of Golf's core rule** (Golf's counterfactual) **is 0.00–0.02.** P-G's sensitivity is scar, not
  blood.
- **What development then chooses between:** P-J alone, or P-J and P-G if the judge adopts §10's A2 (presence); and
  E-V or E-D (extent).
- **#181's shipped modules** should reproduce `scores.json` on these cases arm by arm (§9).

## 2. The merged power script (item 2)

**The script is #182 (PR #187, `janusm.scar.power` on `janusm.scar.scoring`), not merged at the time of writing.**
#187 already ran it at the JA32 bars (400 × 400, Golf's cohort, anchors 0.6–0.8). Its seal sizes, with no
registration failures, are:

| Clustering (patient logit SD) | 50 % of patients scarred | 70 % scarred |
|---|---|---|
| weak (0.7) | **136** (the ≥ 270-segment rule binds; power alone needs 100–120) | **120** (the floor) |
| strong (1.2) | **240** | **160** |

≥ 270 scarred segments needs 136 patients at 50 % scar and 97 at 70 %. This candidate does not re-run that table: it
would reproduce #187's own numbers. The table is #187's, and it is re-run when #187 merges.

**What this candidate adds is E9**
([[Juliet - At a 2 percent registration-failure rate, counting a failed patient's scar-free segments as false calls sinks the JA32 study at any size]]):
#187's engine, imported unchanged, under two accountings of a not-graded patient.

| Weak clustering | p_fail 0 | **p_fail 0.02** | p_fail 0.05 |
|---|---|---|---|
| JA29 as written (every LGE-negative segment of a not-graded patient is a false call) | N 120 | **no N ≤ 320** (0.79 at 320) | none |
| Split (LGE-positive segments missed; LGE-negative segments leave specificity; not-graded rate upper 95 % ≤ 0.10 as its own bar) | N 120 | **N 200** (50 % scar), **160** (70 %) | none |

**The failure rate decides the size more than clustering or enrichment do.** So:
- the JA28 re-powering must feed development's measured registration-failure rate into `seal_size()`;
- §10 proposes the split accounting as an amendment.

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

  The images are drawn from geometry; no case is opened. The stacks are not committed (the repository ignores
  `*.nii.gz`); `python lge_mockup.py` regenerates them byte for byte from a fixed seed. `truth.json` and the panel are
  committed.
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

**How the cuts are set (fixed now, run once on development).**
1. **The aligned reference.** Development patients whose R0 and heart-masked rigid MI agree within 0.5 mm (both
   estimates are logged, JA29), and whose reader check passes at R0.
2. **Each cut** (fat-like, blood-like, above-blood, rim_dark) is the **95th percentile** of that value over the
   aligned reference, per protocol key (§4) when a key has ≥ 15 aligned development patients, pooled otherwise.
3. **If fewer than 15 development patients are aligned at R0,** the cuts are taken from the benchmark's aligned cases
   at the matching blood/CNR level. The benchmark's own cuts are recorded in `bench_lie/scores.json` (`qc_cuts`). The
   freeze PR records which source was used.
4. The cuts are frozen with JA28's freeze, before any seal patient is registered. They never move after.

**What the benchmark shows about them (E8).**
- **The JA29 trio separates moved from aligned scans only moderately:** AUC fat-like 0.82, blood-like 0.80,
  above-blood 0.69. At their 95th-percentile cuts, **11 % of 4 mm-moved cases pass QC at R0** and are graded about
  4 mm off.
- **`rim_dark` separates them at AUC 0.988.** With it in the QC, 0 of 504 moved cases are kept at R0.
  `rim_dark` is the share of the carried cavity's 2 mm inner rim below (remote + blood) / 2 on the smoothed LIE.

**A truth-free phase check exists: `rim_dark`.**
- It separates a 5 % phase mismatch from rigid misalignment at AUC 0.98–0.99, and from Kilo's non-rigid motion at
  0.985–0.992, at every blood level. The JA29 trio scores 0.07–0.56 there.
- **The mechanism:** when the LIE's cavity is smaller, the carried cavity's rim lies on myocardium.
- **The rule:** a patient whose `rim_dark` exceeds its cut *after* the chain has registered is the reader check's
  "wall thickness differs" case. It goes to the JA27 phase-unmatched stratum, never to the primary analysis.
- **Its limit:** it needs LIE blood brighter than remote myocardium. It was tested at blood 30–90 HU above remote. A
  protocol where blood equals remote myocardium on the LIE would blind it; the intake's protocol key (§4) shows when.

**The mask.**
- JA29's 10 mm dilation admits enough static chest to pull rigid MI toward R0: median residual 1.24 mm against
  0.30 mm with a **4 mm** mask, after a 4 mm heart shift.
- The 4 mm mask costs nothing on aligned scans (0.17 against 0.09 mm, both well under the 0.5 mm tolerance of Juliet
  R2 E6).
- §10 proposes it, together with `rim_dark`. [E10 LINE]

## 6. The JA25 hand-over (item 6)

| Shared Stage A code | On `dev` | On `jm/paired-scar` (checked 2026-10-30, 13:10 UTC) |
|---|---|---|
| JA15 harness `src/janusm/harness.py` + tests | yes (#180 → #183; point-to-plane API #198) | **yes** (dev sync #222) |
| JM-0R v2 `experiments/JanusM/fir/jm0r_readout.py` (canonical half-max sign, `decision_inputs`) | yes (#193/#197) | **yes** |
| The decision script `experiments/JanusM/fir/jm0r_decide.py` (rules R0–R10 of `jm/rest-ccta`'s JA43) | yes (#197) | **yes** |
| `janusm.calibrate` (detectable depth) | yes (#198, #211) | **yes** |
| The table writer `janusm.report` + `janusm.reference` (Tables A and B, JA18/JA19 as amended by JA48) | yes (#199) | **yes** |
| JM-0R's numbers | **none**: Job JM-0 has not been run, so there is nothing to apply | — |

**The hand-over is complete.** Both paths import one harness, one JM-0R, one decision script and one table writer.
`jm/paired-scar` holds no copy or variant of any of them.

**What this path does, pre-registered:**
1. **JM-0R's numbers.** When the lead posts JM-0R's aggregate JSON (on #142 and #143), this path runs
   `experiments/JanusM/fir/jm0r_decide.py` on it **unchanged**, records R0–R10 exactly as `jm/rest-ccta` does, and
   adds no path-B parameter. Path B adds no Stage A rule (JA25). Juliet's `fir/edges_m0.py` stays unrun (LQ18).
2. **Table writer.** Path B scores **path A's** Tables A and B against LGE (JA33): `janusm.report` run on the paired
   cohort's first-pass CCTA with its recorded phase. No variant is written here.
3. **Watch.** Any later change to these modules lands on `dev` and reaches this path by the PM's sync. A path-B
   commit that edits one of them is a JA25 violation and should be refused in review.

## 7. Path summary for the lead (item 7, Round 2 §8 updated)

| | Path A, `jm/rest-ccta` | Path B, `jm/paired-scar` (after Round 3) |
|---|---|---|
| Assumes | no reference for scar or ischaemia | the lead obtains a paired CCTA + same-session LIE + CMR LGE cohort (data requirements only, D31) |
| Stage A | built and calibrated (JA15–JA24, JA37–JA49); shipped | **identical** (JA25); the same shipped code, synced from `dev` (#222) |
| "Scarring" in the brief | inferred, from calibrated research flags | **measured**: presence and Kim bin on LIE against LGE, plus path A's flags against LGE |
| What Round 3 settled | — | a shared benchmark: P-K struck; P-G struck unless registration is fixed; P-J, E-V, E-D go to development. A phase check (`rim_dark`). The forms, the mock-up, the intake checker. The seal size from the merged engine |
| Seal size | — | 120–240 patients (#187; weak/strong clustering, 50–70 % scar), **if the registration-failure rate is ~0**. At 2 % failure, JA29's accounting needs > 320; the split accounting (§10 A1) needs 160–200 |
| Committed compute | ≈ 15 GPU-h | the same + ≈ 3 GPU-h once the cohort exists; scar is CPU |
| Extra reader time | none | ≈ 55 CMR reader-hours (planning figure until the mock-up timing replaces it) + about 3 min per patient for the registration check |
| Main risks | flags with no measured sensitivity | the cohort never arrives; the registration-failure rate on real data; non-rigid misalignment (≈ 1.5 mm RMS defeats every rule after rigid/affine) |
| If the cohort never arrives | — | path B reduces to path A exactly; nothing built is lost |

**In short:** Round 3 turned path B's rule menu into one survivor plus one conditional (P-J; P-G with the registration
fix), found a registration flaw (the 10 mm mask) and its fix, and found the phase check Round 2 lacked. The study
stands or falls on the cohort and on its registration-failure rate. Both are measured on the first 40 development
patients, before anything is claimed.

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

Each is backed by a Round 3 experiment. All are for the judge to accept or reject.

- **A1. Count a not-graded patient as missed scar, not as false calls (E9).**
  - **The change:** a not-graded patient's LGE-positive segments stay misses, and its LGE-negative segments leave the
    specificity denominator. A fourth deciding bar is added: the not-graded patient rate, upper 95 % ≤ 0.10.
  - **Why:** under JA29 as written, 2 % failure keeps joint power below 0.80 at every N ≤ 320. Under A1, N = 200
    (50 % scar) or 160 (70 %).
  - **Alternative:** Kilo's graded-only + yield (#179) is more powerful but charges sensitivity less. Either fixes the
    problem; A1 is the more conservative.
- **A2. Mask the registration metric to classes 1–4 dilated 4 mm (not 10 mm), and add `rim_dark` to the QC (E8).**
  - With both, the median residual after a 4 mm heart shift falls from 1.33 to 0.30 mm (p90 3.65 → 0.44), and no
    moved case passes QC at R0.
  - **If P-G's v2 verdict is a strike under JA29's registration that A2 removes, P-G is reinstated** when A2 is
    adopted. In v1, which lacked the exclusion, P-G passed every bar with A2.
- **A3. `rim_dark` above its cut after registration routes a patient to the phase-unmatched stratum (E8, item 5).**
  It is the truth-free phase check Round 2 lacked (AUC 0.98–0.99).
- **A4. The LGE reference rule (§3.1.4).** Agreement is the shared presence and the **lower** of two adjacent bins.
  Adjudication applies only on a presence disagreement or a difference of ≥ 2 bins. The inter-reader anchor is
  computed on the unadjudicated reads.
- **A5. Reader qualification on the mock-up (§3.3).** Bin agreement ≥ 0.80 on the mock scarred segments, and every
  pattern correct, before a CMR reader reads a cohort patient.
- **A6. Non-rigid misalignment.** If development's logged registration residuals show a non-rigid component of about
  1.5 mm RMS (the benchmark's `nonrigid` motion defeats every rule after rigid or affine registration), the JA29
  B-spline development arm is opened before seal grading. No new GPU is needed.

## 11. Held-out record and limits

- **Hearts:** 23 public TotalSegmentator v2.0.1 cardiac CTs (the union of Golf's 22 and Kilo's 15). The whole list
  went through `janusm.guard.refuse(..., source="TotalSegmentator")` before the first byte was fetched (guard v2,
  711 refused overall): **0 of the 23 refused**. The guard runs again per heart in `bench.load_heart`. Images stayed
  outside the repository; no case id appears in an experiment note except as a heart label in the shared lists
  Golf and Kilo already committed. No twin was used.
- **The LGE mock-up** is drawn from geometry; no case is opened.
- **Limits:**
  - **The benchmark** is synthetic LIE in real anatomy: homogeneous tissue, no microvascular obstruction, no beam
    hardening, one scar draw per heart and condition, and 20 real hearts from one public dataset.
  - **The QC cuts** are emulated from the other half of the hearts.
  - **The registration** is SimpleITK's Mattes MI. E10 repeats the mask test on the shipped module.
  - **E9** uses Golf's cohort model.
  - **The reader-time figure** is an estimate until the mock-up is timed.
  - **The DICOM fields** are as named in PS3.6. Vendors' phase reporting varies, which is why §4 falls back to text,
    flagged.
