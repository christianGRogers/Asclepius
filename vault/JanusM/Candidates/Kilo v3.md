---
tags: [janus-m, candidate, round3, paired-scar, lge, late-iodine-enhancement, transmurality, registration, kilo]
author: Kilo
round: 3
version: 3
path: jm/paired-scar
updated: 2026-10-30
issue: christianGRogers/Asclepius#179
---

# Kilo v3 (path `jm/paired-scar`): score presence on a cohort sized for it, check phase before trusting a border, and stop pretending transmurality is easy

## 0. In one paragraph

**Kilo v3 is Kilo v2 as amended by JA25–JA36** (path A's JA15–JA24 bind Stage A through JA25). It settles §7
items 1–7 of the Round 2 ruling. Three of its findings change the ruling, and one of them is against my own Round 2
rule:

- **P-K, my FWHM presence rule, fails on a heart with no scar** (E8). Its threshold is set by the brightest segment, so
  on an LGE-negative heart it falls to ≈ 1.2 robust SD above remote and calls every segment. P-K is struck. A floored
  version (P-K\*) is not enough. **P-G (Golf's core rule) is the presence rule I carry forward**, with P-J as the
  other candidate. The shared benchmark (Juliet, `bench_lie/`) decides, by the rules agreed on #179.
- **A truth-free phase check exists** (E8). The LIE's half-way edge across the carried endocardium, averaged over the
  6 remote segments, moves with a 5 % phase change by ⟨E8⟩ mm. The blood-like and bright-wall QC values do not see it.
  It becomes a JA29 step: a phase-suspect patient is not re-registered (registration cannot fix phase); it goes to
  the phase-unmatched stratum unless the CCTA can be re-reconstructed at the LIE's phase.
- **The seal is sized by presence; transmurality is a claim the seal may not be able to power** (E7, E9 on the merged
  engine). JA32's transmurality bar puts a 0.10 margin on a lower bound. At ≈ 200–300 scar-on-both segments the
  CT's point agreement must therefore come within ≈ 0.03 of the readers'. At the extent error measured in Round 2 the
  power curve is flat. So the seal is sized on sensitivity, specificity and the ≥ 270-segment floor, with growth
  capped at 240. Transmurality is scored once and can validate the Kim bin, but no seal growth is chased for it.
- **Registration failure gets its own deciding endpoint instead of being counted as false calls** (E9, on the merged
  engine). JA29's worst-case rule drops joint power to 0.37–0.66 at 2 % whole-patient failure and to ≈ 0.03 at 5 %.
  Proposed instead:
  - accuracy on graded patients;
  - a deciding **yield** endpoint: the not-graded share, upper 95 % bound ≤ 0.10;
  - a pre-registered switch to "no call" scoring if failures fall preferentially on scarred hearts.

  This holds 0.88–1.00 at 2 % failure and 0.63–0.89 at 5 %, and fails at 10 %, as JA29 intends.

**Committed compute: unchanged** (≈ 3 GPU-h PB-0, only once the cohort exists; Scar-0 and Scar-1 on CPU; voxel head
≈ 55 GPU-h conditional). **No Fir command is due this round** (JA34).

**New evidence this round** (CPU; code in `experiments/JanusM/Kilo/`; images outside the repository; no held-out case
read, scored or trained on):
- [[Kilo - E7 At the JA32 bars the transmurality endpoint passes only if CT grades extent about as well as the LGE readers]]
- [[Kilo - E8 ⟨title⟩]]
- [[Kilo - E9 On the merged engine, worst-case counting of registration failures sinks specificity, and a yield endpoint fixes it]]
- The shared benchmark results for the JA30 menu (§3), from Juliet's `bench_lie/`.

**Held-out cases.** My 13 hearts (the non-skipped cases of Round 2 E5) passed `janusm.guard.refuse(...,
source="TotalSegmentator")` on today's branch (guard v2: 16 held-out + 695 twins = 711 refused; 0 of mine refused).
The fetcher refused every held-out id and twin before the first byte was downloaded. E8 calls the guard for the whole
run and again per heart before any file is opened. Juliet's benchmark does the same for its 23 hearts. No Round 1
case list is reused without the guard. No held-out subject is named in this round's notes, and a twin is called "a
twin".

## 1. What this plan takes as given

**Base:** Kilo v2, as amended by JA25–JA36, unchanged except where §3–§8 propose a change for the judge. Stage A is
path A's JA15–JA24 by reference (JA25), and path B adds only JA33's scoring of path A's own flags against LGE.

**Carried lead questions, as stated assumptions** (each the rulings' recommendation; each stays the lead's):

| | Assumed | Effect on this plan if decided otherwise |
|---|---|---|
| LQ1 | B (this path) | path deleted (M2) |
| LQ2 | (a) four classes, no RV myocardium | none: scar is LV only |
| LQ3 | (a) `heartchambers_highres` under its licence | Scar-0 needs first-pass borders: under (b), Janus-M 1 becomes a prerequisite |
| LQ4 | (a) ImageCAS-X train for Stage A | none on the paired cohort |
| LQ5 | (a) 200 border double reads after A39 | none; the LGE reads (§5) are separate |
| LQ6–LQ8 | the Round 1 recommendations | none |
| LQ9 | (a) a one-line note on the twin record, no seal change | none |
| LQ10–LQ12 | path A's recommendations (Round 2 rest-ccta §5) | as on path A, by JA25 |
| LQ13 | (a) JA27–JA28 as written | §4 sizes within (a): 70 % enrichment preferred |
| LQ14 | (a) single-energy LIE accepted, stratified | none |
| LQ15 | (a) CT–CMR ≤ 90 days; MI ≥ 90 days | the intake checker's windows (§6) move with it |
| LQ16 | (a) two CMR readers + adjudication on every patient | under (b), the anchor (§4) is measured on development only |
| LQ17 | (a) the JA32 rule | §4 proposes three amendments to (a), not (b) |
| LQ18 | (a) JM-0R once; `edges_m0.py` not run | none |

## 2. §7 items 1–7, settled

| Item | Settlement | Where |
|---|---|---|
| 1. One shared synthetic-LIE benchmark | Juliet builds it (`experiments/JanusM/bench_lie/`), Golf and I reuse it; strike rules agreed on #179 before any result, with my amendments 1a–1c (spill by Golf's counterfactual; specificity on LGE-negative hearts; no empty menu). My E8 adds the non-rigid E5 motion and LGE-negative hearts on my own 13. **Struck: P-K.** ⟨bench⟩ | §3 |
| 2. The merged power script at the JA32 bars | The engine is #187. E7 (my generator, reader noise and a noisy anchor) and E9 (the engine itself) agree once matched. **Seal = max(120, ≥ 270 scarred segments, 80 % power for presence); 70 % enrichment preferred (≈ 125–140 vs ≈ 170 at 50 %); growth capped at 240**. Three JA32 amendments | §4 |
| 3. The LGE read form and the registration check form | Field-by-field, with automatic checks, adjudication and blinding, for the existing Janus-M queue's state machine. Entry time ≈ 1 min per LGE read (keystroke-level estimate); total read time is **not measured here**: no reader is in this session. It is measured from queue timestamps on the first 5 development patients | §5 |
| 4. The JA27 intake checker | DICOM header fields that prove each requirement (tags checked against the DICOM data dictionary), and what a patient failing each becomes | §6 |
| 5. The registration QC cuts | Set on development against the reader check, which is blind to QC; provisional cuts from the benchmark and E8 until then. The truth-free phase check is the edge offset (E8) | §7 |
| 6. The JA25 hand-over | **Done for code.** The JA15 harness, JM-0R, the geometry module and the guard are byte-identical on `dev`, `jm/paired-scar` and `jm/rest-ccta` (#180 → #183, #186). **Not done:** the table writer (JA19) exists on no branch, and JM-0R has not been run, so there are no numbers to apply yet | §8 |
| 7. The path summary | Updated | §10 |

## 3. Item 1: the shared benchmark and what it strikes

### 3.1 Agreed on #179 before any result

- **Builder:** Juliet; one generator, one scorer, 23 hearts (TotalSegmentator v2.0.1 masks, my 15 and Golf's 22,
  guard first), plus her phantom; blood below / equal to / above scar; CNR 3 and 5; motion none, rigid, rigid + 3 %
  scale, rigid + 5 % phase; truth as volume share and as depth extent; a scar-free twin per case.
- **Strike rules** (Juliet's, with my 1a–1c and Golf's two additions, all accepted by the three of us):
  1. a presence candidate is struck at CNR 5, motion none or rigid, any blood level, if its point sensitivity
     < 0.75 or point specificity < 0.93, or its spill share > 0.25 (spill = (sens_full − sens_blood→remote) /
     sens_full, Golf's counterfactual), **or its specificity on the scar-free twins < 0.93** (1b);
  2. an extent candidate is struck if its exact Kim-bin agreement on scar-on-both segments < 0.60 under both truths;
  3. CNR 3, scale and phase are reported, never striking;
  4. registration is reported, never struck;
  5. if every presence candidate is struck, none is; the one with the highest minimum sensitivity among those passing
     the specificity bars goes to development, and Scar-1 becomes expected (1c).

### 3.2 My own check before the benchmark result: P-K fails on a heart with no scar (E8)

⟨E8 table: P-K / P-K* / P-G sensitivity, specificity on scarred hearts, specificity on scar-free hearts, by blood
level, CNR 5, aligned and after rigid⟩

- **Why.** P-K's threshold is remote + ½ (p99 of the brightest segment's core − remote). In a scarred heart, that is
  ⟨E8⟩ robust SD above remote. In a scar-free heart, the brightest segment is noise and the threshold falls to
  ⟨E8⟩ SD, so ≥ 5 % of every segment passes. My Round 2 E5 never tested it, because every heart there had 5 scarred
  segments.
- **P-K\*** (a floor at remote + 3 SD) fixes noise but not spill: on scar-free hearts its specificity is ⟨E8⟩.
- **I withdraw P-K.** JA30's menu keeps P-J and P-G. I do not propose P-K\* as a new menu item: it fails the same
  strike rule.

### 3.3 The benchmark's verdict

⟨bench⟩

## 4. Item 2: sizing at the JA32 bars, and three amendments to JA32

### 4.1 What binds

| | Result | Source |
|---|---|---|
| Sensitivity | ≈ 0.9 power at 120 under weak clustering; ≈ 0.4 at 120 under strong clustering with pooled sensitivity 0.81 | E7; engine #187 (240 at 50 %, 160 at 70 % under strong clustering) |
| Specificity | never binds with no registration failures; **binds at any N** with ≥ 2–5 % failures under JA29's worst-case rule (E9: 0.44–0.67 power at 2 %) | E7; E9; #187 |
| ≥ 270 scarred segments | ≈ 170 patients at 50 %, ≈ 125–140 at 70 % (3.25 segments per scar patient); 136 / 97 at 4.0 per patient (engine) | E7; #187 |
| Transmurality | binds whenever CT exact-bin agreement is within ≈ 0.03 of the anchor; flat in N above extent-error SD ≈ 0.10. On the engine: joint power 0.88–0.99 at agreement 0.73, 0.23–0.35 at 0.66 (anchor 0.72) | E7; E9 part A |

### 4.2 The seal size

- **Seal = max(120, N for ≥ 270 ischaemic scarred segments, N for ≥ 80 % joint power on sensitivity, specificity and
  yield)**, computed by `janusm.scar.power` on development numbers (JA28), capped at **240**.
- **Enrichment: target 70 % LGE-positive** (still ≥ 30 % LGE-negative, JA27). At this round's infarct sizes it needs
  ≈ 125–140 patients against ≈ 170 at 50 %, for the same scarred segments.
- **Planning figure for the lead:** 40 development + ≈ 140 seal at 70 % enrichment; ≈ 170 at 50 %.
- **Transmurality is powered only if development shows it can be.** On development, if the measured CT bin agreement
  is ≥ the anchor − 0.03, the seal size also covers transmurality at 80 % (up to the cap). Otherwise the size is the
  presence size, and transmurality is scored once at that size, with its CI and no growth.

### 4.3 Three amendments to JA32 (for the judge)

1. **Anchor on every double-read patient.** JA32 already puts two readers on every patient. The anchor = their
   exact-bin agreement over development + seal, with its own CI. E7: the 5th–95th spread falls from 0.63–0.80 to
   0.69–0.75 at 300 patients, and joint power at sd_s 0.08 rises from 0.76 to 0.90. The margin (0.10) is unchanged and
   is not re-set on development.
2. **An anchor < 0.60 validates presence only.** If the LGE readers cannot agree on Kim bins, the Kim bin keeps "not
   validated" whatever happens. JA32 currently makes transmurality report-only and lets the study pass, so noisier
   readers make passing easier (E7: joint power 0.70 → 0.85 as reader agreement falls from 0.72 to 0.56).
3. **Registration failure: graded-only accuracy plus a deciding yield endpoint** (replaces JA29's worst-case rule in
   the primary analysis).
   - **Yield:** a fourth deciding endpoint, the not-graded patient share, with upper 95 % bound ≤ 0.10.
   - **Guard:** if the LGE-positive segment share among not-graded patients is ≥ 1.5× that among graded patients
     (bootstrap lower bound > 1), the **no-call** analysis becomes primary instead. In no-call, a not-graded segment
     is "no scar called": a miss if LGE-positive, correct if LGE-negative.
   - **Reported beside it:** worst-case (JA29 as written) and no-call.
   - **E9, engine #187, 50 % / 70 % enrichment, joint power at N = 120–240:**

     | Failure rate | Worst case | No call | Graded-only + yield |
     |---|---|---|---|
     | 2 % | 0.37–0.66 | 0.65–0.96 | 0.88–1.00 |
     | 5 % | ≤ 0.05 | 0.32–0.60 | 0.63–0.89 |
     | 10 % | 0 | ≤ 0.10 | ≤ 0.08 |

     Planning assumes ≤ 2 % failure; development measures it.

## 5. Item 3: the two forms

Both run in the existing Janus-M read queue (`janusm_reads`): same states (assigned → submitted → automatic check →
accepted or returned), same rule that a reader is never served another read of the same case. The submission body
is a JSON form, not a mask. Forms are a `role:swe` item (JA35 item 5); this is their spec.

### 5.1 LGE segment read (CMR readers; blind to every CT)

**Served:** the CMR study's LGE short-axis stack and long-axis views, and cine if present. Never the CT, the LIE,
the other reader's form or any Janus-M output.

**Header (per read):**

| Field | Values |
|---|---|
| Image quality | diagnostic / limited / non-diagnostic |
| Coverage base to apex | complete / incomplete |
| Any LGE | yes / no |
| Reader confidence | 1–3 |

**Per AHA segment 1–17:**

| Field | Values | When |
|---|---|---|
| Presence | yes / no / not assessable | always |
| Pattern | subendocardial, transmural (ischaemic); mid-wall, epicardial, patchy (non-ischaemic) | if yes |
| Kim bin | 1–25 / 26–50 / 51–75 / 76–100 % | if yes |

**The Kim-bin definition printed on the form (JA32):** "Estimate the share of this segment's myocardium that is
hyperenhanced, in percent of tissue (Kim 2000). Think of the scar's thickness through the wall and its extent across
the segment together." An example panel shows one segment at each bin.
- The panel is a figure in the queue's help, drawn from synthetic segments, not from any patient.
- The same text is used for the CT-extent choice on development (JA30), so CT and LGE grade the same quantity.

**Automatic checks** (submission returned to the reader if any fails):
- every segment answered;
- pattern and bin present exactly when presence = yes;
- "Any LGE = no" only if all 17 presences are no or not assessable;
- ≤ 3 segments not assessable, unless image quality is non-diagnostic, in which case the patient is "LGE not
  assessable" (an exclusion from the primary).

**Adjudication (JA32):** a third CMR reader reads, blind to the first two reads, only the segments with a presence
disagreement or a ≥ 2-bin difference. Reference = majority presence, and the median of three for the bin.

**Anchor:** reader 1 vs reader 2, exact Kim bin on segments both call scar, over every double-read patient (§4.3
item 1).

### 5.2 Registration check (one CT reader; blind to LGE and to every QC value)

**Served:** for one patient, three short-axis LIE slices (basal, mid, apical; the AHA rings' centres) with the
carried borders overlaid, and the first-pass CCTA at the same slices side by side. The reader sees no QC value, so
the check can calibrate the QC cuts (§7).

| Field | Values |
|---|---|
| Per slice | pass / fail |
| If fail, reason | endocardium off; epicardium off; whole contour shifted; cavity size mismatch (phase); image unreadable |
| Patient result | pass if all three pass |
| On fail | the reader drags the CT into place once (the manual initial shift, mm, logged); the chain re-runs from it; the reader checks again |
| Second fail | **not graded** |

### 5.3 Reader time

- **Not measured in this round.** No CMR or CT reader is in this session, and a mock-up time from a non-reader would
  be misleading.
- **Data-entry time is estimated** by the keystroke-level model (Card 1980; mental preparation 1.35 s, point 1.1 s,
  click 0.2 s per answer):
  - LGE form: 17 presence answers ≈ 45 s, plus ≈ 5 s per scarred segment → **≈ 1 min** at 3–4 scarred segments;
  - registration check: 3 decisions ≈ 8 s, plus one reason if failed.
- **Image review is the rest,** and it is not modelled. LQ16's 10 min per LGE read stays an estimate.
- **Measured** as claim-to-submit time from the queue's own timestamps on the first 5 development patients (both
  readers), and posted with the development numbers. If the median exceeds 15 min, LQ16's reader-hours are restated
  before the seal's reads are scheduled.

## 6. Item 4: the JA27 intake checker

**Order (fail-closed):**
1. The de-identified manifest's patient keys are hashed and passed through `janusm.guard.refuse` **before any file
   is opened**.
2. The JA28 split is assigned by the salted hash at this point.
3. Then only DICOM headers are read (no pixel data) to classify series and check fields.
4. The output is one row per patient (tier, strata, eligibility, the recorded fields) in
   `configs/janusm/paired-r2.json`. It holds no identifier and no date.

**Fields, tag numbers checked against the DICOM data dictionary (pydicom 3, 2026-10-30):**

| Requirement (JA27) | Fields | Rule | A patient failing it becomes |
|---|---|---|---|
| De-identified | Patient Identity Removed (0012,0062); De-identification Method (0012,0063); Burned In Annotation (0028,0301) | YES; present; NO | **quarantined**: not opened further, back to the lead |
| Dates never stored | Longitudinal Temporal Information Modified (0028,0303); Study Date (0008,0020), Acquisition DateTime (0008,002A) | (0028,0303) = MODIFIED, and the modification is **one constant shift per patient** (PS3.15 §E.3.6 also allows aggregation, e.g. to the first of the month, which destroys day offsets); the checker computes day offsets and drops the dates. If dates were aggregated, the manifest must carry the day offsets instead | quarantined if neither a constant shift nor manifest offsets exist |
| Same session, same frame | Study Instance UID (0020,000D); **Frame of Reference UID (0020,0052)**; Image Position (0020,0032) and Orientation (0020,0037) (Patient); Table Position (0018,9327) | first-pass and LIE share the frame of reference | **R0 not trusted**: the chain starts at heart-masked rigid; recorded (not an exclusion) |
| LIE 5–10 min | Acquisition Time (0008,0032) of LIE − first pass; Contrast/Bolus Start Time (0018,1042) | 4–12 min accepted | **delay stratum** (report-only); missing → the same |
| ECG-gated | Cardiac Synchronization Technique (0018,9037) | PROSPECTIVE or RETROSPECTIVE on both | first pass ungated → excluded; LIE ungated → T1 only |
| **Phase** | Nominal Percentage of Cardiac Phase (0020,9241); else Trigger Time (0018,1060) ÷ R-R (from Heart Rate (0018,1088) or R-R Interval Time Nominal (0020,9251)) | \|first pass − LIE\| ≤ 5 % R-R | seal/development only if a matched first-pass reconstruction exists or raw data allow one; otherwise the **phase-unmatched stratum**; either phase missing → the same stratum. Vendor private phase tags are mapped on development, never trusted blind |
| Slices | Slice Thickness (0018,0050); Spacing Between Slices (0018,0088) | first pass ≤ 0.75 mm; LIE ≤ 1.0 mm | first pass fails → excluded (Stage A needs it); LIE fails → T1 only |
| Protocol, recorded | KVP (0018,0060); Convolution Kernel (0018,1210); Manufacturer (0008,0070) and Model (0008,1090); CTDIvol (0018,9345); Multi-energy CT Acquisition (0018,9361); Monoenergetic Energy Equivalent (0018,937C) | recorded | dual-energy / single-energy / low-dose strata (LQ14) |
| CMR | Magnetic Field Strength (0018,0087); Sequence Name (0018,0024); Scanning Sequence (0018,0020); Inversion Time (0018,0082); Image Type (0008,0008) | LGE present; PSIR recorded where the vendor marks it | no LGE series → T3 / excluded from T1–T2; coverage is the reader's (§5.1) |
| CT–CMR window | day offsets | ≤ 90 days | excluded; or the 90–180-day stratum if LQ15 (c) is chosen |
| Infarct age | manifest offset of the index MI | ≥ 90 days before both scans, or no known MI | **acute stratum** if < 90 days |
| Interval events | manifest: MI, PCI, CABG or cardiac surgery between CT and CMR | none | excluded |
| Device or metal over the LV | manifest flag; the registration reader can also flag it | none | excluded |
| Prior CABG | manifest | — | kept for scar; left out of territory analyses (JA33) |
| Non-ischaemic pattern | from the LGE reads | — | **non-ischaemic stratum** after reading |
| Phase, truth-free | the edge offset (§7), after registration | \|offset\| ≤ cut | phase-suspect → as "phase" above |

**What the checker never does:** open pixel data before the guard; keep a date, name, accession number or UID in the
repository (UIDs are compared in memory and written only as "same / different"); or decide a stratum that needs a
reader (pattern, coverage).

## 7. Item 5: the registration QC cuts

### 7.1 What E8 shows

⟨E8 results: null distributions; flag rates; edge offset vs truth⟩

### 7.2 The procedure

1. **QC values per patient**, after each JA29 stage, on the LIE smoothed to FWHM 1.5 mm (JA30):
   - fat-like share and blood-like share of the carried wall (Juliet);
   - the share of the wall brighter than the LIE blood median (Kilo);
   - **the edge offset**: the signed distance from the carried endocardium at which the mean LIE profile over the 6
     remote segments crosses half-way between blood and remote wall (E8);
   - the spread (IQR) of the per-segment edge offsets, which picks up residual translation.
2. **Provisional cuts**, before development, from the benchmark's registered, phase-matched null, per blood level:
   the 95th percentile (one-sided for the shares; two-sided 2.5–97.5 % for the edge offset). ⟨E8 / bench values⟩
3. **Development sets the cuts once.** The registration reader check (§5.2), blind to QC, is the arbiter.
   - For each QC value, the cut is the smallest that keeps ≥ 95 % of reader-passed development patients passing.
     This protects against false fails, since the reader check runs on every patient anyway.
   - The share of reader-failed patients each cut catches is reported.
   - A QC value that catches < 50 % of reader fails is dropped from the chain, but stays reported.
   - The cuts are frozen in the freeze PR with the development numbers (JA30's freeze).
4. **Phase is a separate branch, not a registration step.** If |edge offset| exceeds its cut after rigid (and affine,
   if kept), the patient is phase-suspect: no further registration, the reader sees the flag only after the reader's
   own check, and the patient goes to the phase-unmatched stratum unless a CCTA reconstruction at the LIE's phase
   exists. Registration cannot fix a phase change (Juliet E6), so re-registering would only hide it.
5. **The edge offset needs blood ≠ remote wall on LIE.** If |blood − remote| < 2 robust SD of remote, it is "not
   evaluable", and the patient's phase rests on the DICOM phase fields alone (§6).

## 8. Item 6: the JA25 hand-over

| Shared code | `dev` | `jm/paired-scar` | `jm/rest-ccta` |
|---|---|---|---|
| `src/janusm/harness.py` (JA15) | c070324 | c070324 | c070324 |
| `tests/test_janusm_harness.py` | 09acd09 | 09acd09 | 09acd09 |
| `experiments/JanusM/fir/jm0r_readout.py` (JA23) | b62a710 | b62a710 | b62a710 |
| `tests/test_janusm_jm0r_readout.py` | 6d075a2 | 6d075a2 | 6d075a2 |
| `src/janusm/geometry.py`, `tests/test_janusm_geometry.py` | ef636f9, 994a3e9 | same | same |
| `src/janusm/guard.py`, `configs/janusm/ts-twins-r1.json` | fac7e7a, 68b468b | same | same |
| Table writer (JA19) | — | — | — |

(Git blob ids, 2026-10-30.) **Confirmed: both paths run one implementation** of the harness, JM-0R, geometry and the
guard (#180 → #183; synced by #185 and #186).

**Still open:**
- **The table writer** (JA19, a `role:swe` issue on path A) is not built on any branch. When it lands it moves to
  `dev` the same way, and JA33 scores its output, not a copy.
- **JM-0R's numbers** do not exist yet (the lead runs it after Job JM-0). When they do, this path applies them exactly
  as `jm/rest-ccta` does, by JA25: JA17's TPR gate, JA18's fat-cut start, JA20's septal-arc and geodesic checks. Path B
  adds one use: JM-0R's endocardial half-maximum offset on first-pass CCTA is the prior for the LIE edge-offset null
  (§7). A first-pass border that sits off the half-maximum carries that offset into the LIE.

## 9. What results would change this plan

| Result | Change |
|---|---|
| The benchmark strikes P-G and keeps P-J (or the reverse) | the surviving one goes to development alone; JA30's choice step is skipped |
| The benchmark strikes every presence candidate | rule 5 (1c): the least bad goes to development; Scar-1 (JA31) is planned, not conditional |
| Development: CT bin agreement ≥ anchor − 0.03 | the seal is also sized for transmurality, up to 240 |
| Development: CT bin agreement < anchor − 0.03 | presence-sized seal; transmurality scored once, no growth (§4.2) |
| Development: anchor < 0.60 | only presence can be validated (§4.3 item 2) |
| Development: not-graded share > 10 % | seal grading stops until the chain is revised on development (JA29) |
| Development: phase-suspect share > 20 % | the LIE phase requirement is not being met; the lead is told before any seal patient is read |
| Development: scarred segments per scar patient ≠ 3.25 | the ≥ 270 floor's N is recomputed by the engine |
| JM-0R: first-pass endocardial half-maximum offset > 0.5 mm | the edge-offset null is re-centred on it (§7) |

## 10. Item 7: path B against path A, for the lead (updated)

| | Path A, `jm/rest-ccta` | Path B, `jm/paired-scar` |
|---|---|---|
| Assumes | no reference for scar or ischaemia | the lead obtains a paired CCTA + same-session LIE + CMR LGE cohort (data requirements only, D31) |
| Stage A | built and calibrated: specificity only (JA18) | **identical, one implementation** (JA25 hand-over confirmed, §8) |
| "Scarring" | inferred: thinning, fat and hypoattenuation as research flags | **measured**: scar presence on LIE scored against LGE; Kim bin validated only if the readers agree (anchor ≥ 0.60) and CT matches them |
| Scar rule | — | P-G or P-J, chosen on the shared benchmark and then development; P-K struck |
| Registration | — | R0 → QC → heart-masked rigid → affine; **a truth-free phase check routes phase-mismatched patients out** |
| Cohort | none | 40 development + **≈ 140 seal at 70 % enrichment** (≈ 170 at 50 %); never more than 240 |
| Reader time | none | ≈ 180 patients × 2 CMR reads + adjudication; entry ≈ 1 min each, image time to be measured on the first 5 |
| Committed compute | ≈ 15 GPU-h | the same + ≈ 3 GPU-h once the cohort exists |
| Main risk | flags with no measured sensitivity | the cohort never arrives; registration failures; or CT extent too noisy for transmurality, leaving presence the only validated claim |
| If the cohort never arrives | — | path B reduces to path A exactly |

**In short:** path B is path A plus one validation study. Its realistic outcome is a validated scar-presence call and
a Kim bin that stays "research" unless CT extent proves as reproducible as the CMR readers'.

## 11. Code that must ship (`role:swe`; the PM opens them; I don't build them in this PR)

1. **#181 (registration + Scar-0) additions:** the edge offset and its per-segment spread as QC outputs (E8's
   `edge_offset`, `nearest_segment`, half-voxel-corrected signed distance); a "phase-suspect" status beside passed /
   re-registered / not graded; P-K removed from the menu.
2. **#182 / #187 (power + scoring) additions:**
   - options to resolve not-graded segments as "no call" or graded-only (E9's `score_study` shows both on the
     engine's own functions);
   - the yield endpoint (not-graded patient share, upper bound ≤ 0.10) and the selective-failure guard;
   - the anchor computed over all double-read patients, with its CI;
   - "anchor < 0.60 ⇒ presence-only claim" in `decide`;
   - a 240 cap in `seal_size`.
3. **The intake checker** (JA35 item 3) as specified in §6.
4. **The two forms** (JA35 item 5) as specified in §5, with automatic checks and adjudication routing, and
   claim-to-submit timestamps exported for §5.3.

## 12. References

New or newly used this round; all others as Kilo v2 with JA14, JA24 and JA36 applied.

| Reference | Identifier | Used for |
|---|---|---|
| Card SK, Moran TP, Newell A. The keystroke-level model for user performance time with interactive systems. Commun ACM 1980;23(7):396–410 | 10.1145/358886.358895 (checked at Crossref, 2026-10-30) | §5.3 entry-time estimate |
| DICOM PS3.6 Data Dictionary (tags as in pydicom 3's copy of the dictionary, checked 2026-10-30) | dicom.nema.org/medical/dicom/current/output/chtml/part06/ | §6 tag numbers |
| DICOM PS3.15 §E.3.6, Retain Longitudinal Temporal Information Options (the modified-dates option; (0028,0303) = MODIFIED; aggregation allowed) | dicom.nema.org/medical/dicom/current/output/chtml/part15/sect_E.3.6.html (excerpt read via search, 2026-10-30; the page itself returned 503) | §6 day offsets |
| Kim RJ et al. N Engl J Med 2000;343:1445–1453 | 10.1056/NEJM200011163432003 | the read form's "percent of tissue" wording (segment-scoring definition unverified from the abstract, JA36) |
| Gatti M et al. Eur Radiol 2025;35:3054–3067 | 10.1007/s00330-024-11283-5 | E7 calibration (segment sensitivity 0.86, specificity 0.98) |
| Mattes D et al. IEEE Trans Med Imaging 2003;22:120–128 | 10.1109/TMI.2003.809072 | registration (E8) |

JA36 corrections apply to everything carried from Kilo v2. In particular: Palmisano 2020's 3.54 is the CNR of
ischaemic scars; Ohta 2018 is a heart-failure cohort; Klambauer 2026 is SCAD; Dixon 2016 is for clusters of two;
Ibrahim 2010 supports a ≥ 7-day floor only.
