---
aliases: [Kilo E8]
tags: [janus-m, experiment, registration, qc, phase, lie, scar-rule, kilo, paired-scar, round3]
status: done
round: 3
path: jm/paired-scar
updated: 2026-10-30
code: experiments/JanusM/Kilo/e8_qc_phase.py, experiments/JanusM/Kilo/e8_summarise.py
issue: christianGRogers/Asclepius#179
---

# Kilo E8: a truth-free edge offset sees a 5 % phase change that the QC shares miss, and P-K calls scar in every scar-free heart

**Questions.**
1. Round 2 ruling §7 item 5: how should the JA29 QC cuts be set, and is there a truth-free number that catches a
   cardiac-phase mismatch? Juliet E6 found that a 5 % cavity change halves bin accuracy and that neither the fat-like
   nor the blood-like share sees it.
2. My objection 1b on #179: is my Round 2 presence rule, P-K, specific on a heart with **no** scar? Round 2 E5 never
   tested it, because every heart had five scarred segments.

**Answers.**
- **The edge offset sees phase.**
  - **Definition:** the signed distance from the carried endocardium at which the mean LIE profile over the 6 remote
    segments crosses half-way between blood and remote wall.
  - **With a 5 % phase change** it moves to −1.35 / +1.17 mm (median; cavity smaller / larger). After E5's motion and
    heart-masked rigid registration it is −1.35 / +1.00 mm.
  - **When phase-matched,** it stays within −0.04 to +0.32 mm (5th–95th percentile) if aligned, and −0.53 to +0.78 mm
    after E5's motion and rigid.
  - **Cut |offset| > 0.6 mm:** it flags 90–100 % of phase-mismatched patients at every blood level, with 0–10 % false
    flags on phase-matched, registered patients.
- **The QC shares are blind to the dangerous direction.** When the LIE cavity is smaller (Juliet's case: the carried
  border sits inside the true wall and misses subendocardial scar), the blood-like and bright-wall shares flag 0–10 %
  of patients. They catch a larger LIE cavity only when blood is at least as bright as scar.
- **The spread of per-segment offsets (IQR) sees residual translation.** It flags 83–96 % of unregistered E5 cases, and
  ≤ 13 % of phase cases.
- **P-K fails on scar-free hearts.** Its specificity on hearts with no scar is **0.005** aligned (CNR 5), and
  0.05–0.21 after E5's motion. The threshold falls from a median 2.9 robust SD above remote (scarred hearts) to 1.3 SD
  (scar-free), so ≥ 5 % of every segment passes. It also loses specificity on scarred hearts when blood is brighter
  than scar and a non-rigid residual remains (0.48).
- **P-K\* (a floor at remote + 3 SD) is not enough.** On scar-free hearts it reaches 1.00 / 0.98 with blood below or
  equal to scar, but 0.61 with blood above, and 0.38–0.65 after E5's motion with bright blood: 3-SD spill.
- **P-G is specific everywhere but blind to bin-1 scars by construction.**
  - Specificity on scar-free hearts is ≈ 1.00, except 0.84 with a larger LIE cavity and bright blood.
  - **Sensitivity in bin 1 (1–25 %) is 0.03** aligned. Its 1 mm endocardial exclusion removes thin subendocardial
    scar.
  - After E5's motion bin 1 rises to 0.15 and bin 2 falls to 0.83. The rise is spill: registration carries blood
    into the core, as the Round 2 ruling found for Golf's E5.
  - Pooled sensitivity is 0.72–0.77 at CNR 5, set by the bin-1 share of the scar mix (here ≈ 25 %).
- **E-V extent** is unbiased at CNR 5 (mean error −0.01 to +0.01, SD 0.03–0.04 aligned). At CNR 3 it under-reads by
  0.13–0.17 (SD 0.08), and exact-bin agreement collapses (0.03–0.36).

## Method

**Hearts.** The 13 enhanced public TotalSegmentator v1 cardiac CTs (Zenodo 6802614, CC BY 4.0; model-made masks at
1.5 mm) that my Round 2 E5 used.
- `janusm.guard.refuse(..., source="TotalSegmentator")` passes the whole list (0 refused; guard v2, 711 refused),
  and again each heart before its files are opened.
- The fetcher refused every held-out id and twin before downloading.
- Two further cases on disk were skipped for no LV contrast (as in Round 2).
- Images stay outside the repository.

**Per heart, two repetitions** (seed = case number + 8):
- **Scars:** as E5, five segments of 1–16, subendocardial, depth τ ∈ {0.15, 0.40, 0.65, 0.90, random}. A scar-free
  version of the heart uses the same noise.
- **Phase:** e ∈ {−0.05, 0, +0.05}. The LIE endocardium is at s = −e·R_eq on the half-voxel-corrected signed distance
  s of the first-pass cavity (R_eq = the cavity's equivalent-sphere radius, 25–30 mm, so the shift is 1.3–1.5 mm). The
  epicardium is fixed. Partial volume is kept: a 1.4 mm shift on a 1.5 mm grid is not lost to rounding. Scar follows
  the wall. Truth = the scar's volume share of the LIE wall, partial volumes counted.
- **LIE contrast:**
  - remote 85 HU; scar 85 + 60;
  - blood 85 + {30, 60, 90} (below / equal to / above scar);
  - fat −80; other soft tissue 40 + 0.45 (CT − 40); lung and air unchanged;
  - PSF 0.6 voxel; noise SD 60 / CNR, with CNR ∈ {3, 5}.
- **Motion:** none; or E5's (whole image: rotation N(0, 3°), translation N(0, 4 mm), plus a smooth non-rigid field,
  RMS 1.5 mm, 20 mm correlation). This is the condition the shared benchmark does not carry.
- **Registration:** R0 (scanner coordinates) and heart-masked rigid Mattes MI (E5's R3, mask = chambers + wall dilated
  10 mm), first pass moving, LIE fixed. Labels carried by nearest neighbour.
- **QC and grading** on the LIE smoothed to FWHM 1.5 mm, with remote = the core voxels of the 6 lowest-median segments
  (JA30):
  - fat-like (< 0 HU), blood-like (> remote + 0.8 (blood − remote)) and bright-wall (> blood median) shares of the
    carried wall;
  - the edge offset (0.5 mm bins, −6 to +4 mm), over the 6 remote segments and per segment;
  - P-K, P-G (≥ 5 % above remote + 3 SD after a 1-voxel opening, ignoring 1 mm at the carried endocardium), E-V;
  - P-K\* = P-K and E-V ≥ 0.05. This is exactly P-K with its threshold floored at remote + 3 SD, because the two
    thresholds are nested.
- **Summary:** heart-cluster bootstrap (300 draws) for sensitivity and scar-free specificity. Cuts are set on the
  phase-matched, registered null (motion E5, R3) per blood level.

`results_e8_qc_phase_summary.json` holds every table below. `results_e8_qc_phase_raw.json.gz` holds every row: 3432
carried results, per-segment calls and truth. It contains public case numbers only, all guard-allowed.

## Results

### Edge offset against the true border error

| Phase, motion | True signed endocardial error (mm; + = the carried border is inside the true wall) | Edge offset, 5th / 50th / 95th (mm) |
|---|---|---|
| −5 %, none | −1.45 | +1.04 / +1.17 / +1.33 |
| −5 %, E5 + rigid | −1.42 | +0.77 / +1.00 / +1.15 |
| 0, none | +0.03 | −0.04 / −0.01 / +0.32 |
| 0, E5 + rigid | +0.05 | −0.52 / −0.10 / +0.46 |
| +5 %, none | +1.51 | −1.70 / −1.37 / −0.96 |
| +5 %, E5 + rigid | +1.62 | −1.90 / −1.35 / −0.82 |

Over all scarred rows, r = −0.80 between the edge offset and the true signed error. The slope is −0.64: partial
volume and the PSF shrink it.

### What each QC value flags

Cuts: the 95th percentile of the phase-matched, registered null (one-sided for the shares, 2.5–97.5 % for the
offset), or |offset| > 0.6 mm. Each cell is the share flagged.

| Blood vs scar | Case | Fat-like | Blood-like | Bright wall | Offset IQR | Offset (null 95 % band) | \|Offset\| > 0.6 mm |
|---|---|---|---|---|---|---|---|
| below | unregistered E5 | 0.38 | 0.46 | 0.23 | **0.96** | 0.46 | 0.62 |
| below | +5 % (cavity smaller), registered | 0.04 | 0.06 | 0.06 | 0.06 | 0.94 | **0.90** |
| below | −5 % (cavity larger), registered | 0.10 | 0.12 | 0.08 | 0.00 | 0.88 | **1.00** |
| equal | unregistered E5 | 0.35 | 0.58 | 0.65 | 0.83 | 0.56 | 0.52 |
| equal | +5 %, registered | 0.06 | 0.04 | 0.10 | 0.13 | 1.00 | **1.00** |
| equal | −5 %, registered | 0.06 | 0.23 | 0.25 | 0.00 | 1.00 | **1.00** |
| above | unregistered E5 | 0.35 | 0.94 | 0.94 | 0.96 | 0.62 | 0.62 |
| above | +5 %, registered | 0.06 | 0.02 | 0.00 | 0.00 | 1.00 | **1.00** |
| above | −5 %, registered | 0.06 | 0.96 | 0.98 | 0.00 | 1.00 | **1.00** |
| | **false flags on the phase-matched, registered null** | 0.05 by construction | | | | 0.05 by construction | **0.10 / 0.00 / 0.00** |

Null QC values (phase-matched, E5 + rigid; 5th / 50th / 95th):

| Blood vs scar | Fat-like | Blood-like | Bright wall | Offset IQR (mm) |
|---|---|---|---|---|
| below | 0.01 / 0.04 / 0.08 | 0.14 / 0.19 / 0.26 | 0.11 / 0.15 / 0.22 | 0.50 / 0.80 / 1.16 |
| equal | 0.01 / 0.04 / 0.08 | 0.08 / 0.10 / 0.16 | 0.03 / 0.05 / 0.07 | 0.57 / 0.86 / 1.33 |
| above | 0.01 / 0.04 / 0.08 | 0.02 / 0.03 / 0.05 | 0.00 / 0.00 / 0.01 | 0.46 / 0.64 / 1.02 |

The blood-like and bright-wall shares depend on the blood level by a factor of 5–50, so a pooled cut is meaningless.
The edge offset is in millimetres and its null hardly moves with blood level.

### Presence rules (CNR 5, phase-matched; sensitivity and scar-free specificity with heart-bootstrap 95 % CI)

| Motion / registration | Blood | P-K sens | P-K spec, scar-free hearts | P-K\* spec, scar-free | P-G sens | P-G spec, scar-free | Spec on scarred hearts, P-K / P-G |
|---|---|---|---|---|---|---|---|
| none / R0 | below | 0.96 [0.92, 0.99] | 0.005 [0.00, 0.01] | 1.00 | 0.75 [0.72, 0.78] | 1.00 | 1.00 / 1.00 |
| none / R0 | equal | 0.98 | 0.005 | 0.98 | 0.75 | 1.00 | 1.00 / 1.00 |
| none / R0 | above | 0.99 | 0.005 | 0.61 [0.56, 0.65] | 0.75 | 1.00 | 0.99 / 1.00 |
| E5 / rigid | below | 0.91 | 0.05 [0.01, 0.10] | 0.99 | 0.72 [0.65, 0.77] | 1.00 | 0.99 / 0.99 |
| E5 / rigid | equal | 0.95 | 0.15 [0.10, 0.21] | 0.65 [0.61, 0.70] | 0.76 [0.71, 0.81] | 1.00 | 0.84 / 0.99 |
| E5 / rigid | above | 0.99 | 0.21 [0.15, 0.27] | 0.38 [0.32, 0.43] | 0.77 [0.72, 0.81] | 1.00 | 0.48 / 0.99 |

Sensitivity by true Kim bin, CNR 5:

| | Bin 1 (n 96) | Bin 2 (96) | Bin 3 (96) | Bin 4 (102) |
|---|---|---|---|---|
| P-K, aligned / E5 + rigid | 0.92 / 0.79 | 1.00 / 1.00 | 1.00 | 1.00 |
| P-G, aligned / E5 + rigid | **0.03 / 0.15** | 0.94 / 0.83 | 1.00 | 1.00 |

At CNR 3, P-G's bin 2 drops to 0.51 / 0.36, so its pooled sensitivity is 0.52–0.65.

### Phase and grading

With the LIE cavity larger (−5 %) and blood at or above scar, P-K's specificity on scarred hearts falls to 0.01–0.06:
the carried wall contains blood. P-G holds (0.85–1.00). Exact-bin agreement (E-V, on segments scar on both) is:
- 0.97 aligned at CNR 5;
- 0.56–0.75 at −5 % (aligned) and 0.91–0.94 at +5 %;
- after E5's motion, 0.74–0.78 with no phase change, 0.72–0.77 at +5 % and 0.38–0.62 at −5 %.

## What it changes

1. **P-K is withdrawn** from JA30's menu, by its author. P-K\* is not proposed: it fails the scar-free specificity
   strike rule (1b on #179) whenever blood is at least as bright as scar.
2. **The presence menu has a real trade-off**, which the benchmark and then development must face:
   - the only rule here that sees bin-1 scar is not specific;
   - the only one that is specific (P-G) cannot see bin 1;
   - P-J, with its cut learned from LGE-negative segments and no endocardial exclusion, is the candidate between them.

   P-G's pooled sensitivity is set by the bin-1 share: ≈ 0.75 when a quarter of scarred segments are bin 1, so it sits
   on the JA32 bar. The development set's LGE reads measure that share.
3. **A JA29 phase step** (Kilo v3 §7):
   - after registration, |edge offset| > 0.6 mm (provisional; re-set on development against the reader check) marks
     the patient **phase-suspect**;
   - such a patient is not re-registered (rigid cannot fix it);
   - the patient goes to the phase-unmatched stratum unless the CCTA can be reconstructed at the LIE's phase.
4. **QC cuts per blood level, or relative.** The blood-like and bright-wall shares must be read against the patient's
   own blood-to-remote contrast. The offset IQR is the translation check: it catches 83–96 % of unregistered cases.
5. **CNR 3 is not gradeable for extent** by E-V (bias −0.15). The JA27 LIE protocol fields (dose, kV, energy mode) and
   the measured CNR become a stratum, and development measures CNR.

**Limits.**
- Synthetic LIE with label-assigned intensities on 1.5 mm model-made masks.
- The phase change is an endocardial shift with the epicardium fixed, which is Juliet's model in real anatomy. A real
  phase change also moves the base and twists.
- The edge offset needs blood ≠ remote wall on LIE. Here the smallest contrast was 30 HU at CNR 3; when blood equals
  remote it is undefined (Kilo v3 §7 item 5).
- The shared benchmark (Juliet, `bench_lie/`) decides strikes. This note is my own check, beside it.
