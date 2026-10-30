---
tags: [janus-m, experiment, round3, paired-scar, LIE, registration, scar, spill, phase]
author: Golf
round: 3
path: jm/paired-scar
updated: 2026-10-30
issue: christianGRogers/Asclepius#179
code: experiments/JanusM/Golf/lie_menu.py, experiments/JanusM/Golf/lie_menu_summary.py
results: experiments/JanusM/Golf/lie_menu.json, experiments/JanusM/Golf/lie_menu_raw.json.gz
---

# Golf E8 + E9: on real hearts P-G is the only presence rule that holds, its sensitivity is not spill, and the registration chain, not the rule, limits the Kim bin

## Question

Round 2 paired-scar ruling §7 items 1 and 5:
- Run every JA29–JA30 menu item on real anatomy, under blood below, equal to and above scar, a heart moving
  against a static chest, a 5 % phase change, CNR 3 and 5, and truth both as volume share and as depth extent.
- Measure the spill share of P-G's sensitivity.
- Find a truth-free check that catches a phase mismatch.

This is **Golf's cross-check on Golf's own generator**. The shared benchmark (`bench_lie`, Juliet, #179) runs the
same menu on 23 hearts plus a phantom, and **its numbers decide the strikes**. Where the two can be compared, the
candidate (Golf v3 §4) sets them side by side.

## Setup

- **Hearts:** the 22 public TotalSegmentator v2.0.1 `gated_like` CTs that pass `janusm.guard` (guard v2, 711
  refused). The guard runs on the whole list first, then on each heart before it is read. Released labels;
  1 mm grid; heart + 25 mm.
- **Scar:** one territory per heart (LAD / RCA / LCx in turn). Each segment's depth is drawn from {0, 15, 35, 60,
  90 %} with equal weight, plus a ±5 % smooth jitter. Among the scarred segments, 37 % are bin 1 by volume share
  (37 of 101).
- **LIE:**
  - remote myocardium 90 HU; scar 150 HU;
  - blood 120 / 150 / 180 HU (below / equal / above);
  - fat −80 HU; elsewhere the real CT compressed to 35 %;
  - 1 mm PSF; correlated noise SD 60 / CNR.

  Each LIE also has three variants with the same noise: no scar (a scar-free heart), blood at remote, and both.
- **Motion:**
  - `chest`: the whole image moves, 4 mm, 2°, 3 % scale along a random axis, 1 mm smooth field;
  - `static`: the same, applied to the heart only, with the chest static;
  - `phase5`: chest motion plus a 5 % short-axis cavity shrink with the wall area kept.
- **Registration (JA29):** the first-pass CT is moving and the LIE fixed; Mattes MI, masked to classes 1–4
  dilated 10 mm. Arms:
  - R0, rigid, and affine (from rigid);
  - for `static`, an unmasked rigid;
  - `exact`, the true moved borders;
  - **the chain**, emulated with QC cuts set on the other half of the hearts. Each cut is the p95 of that QC value
    over registrations with endocardial ASSD ≤ 1 mm, a stand-in for the reader check. The chain stops at R0 if
    QC passes; else rigid, with affine kept only if no QC value rises.
- **Scar-0 (JA30), its constants exactly:**
  - FWHM 1.5 mm; remote = the core (one erosion) of the 6 lowest-median segments, median and 1.4826 MAD;
  - P-K, P-G (≥ 5 %), and P-J (E-D ≥ τ, with τ = p99 over scar-free segments of the other half of the hearts,
    per blood level and CNR);
  - E-V; E-D with P-K's half-way voxel cut (Juliet E6, and `scar0.py`'s reading); E-D3 with the remote + 3 SD cut
    (`bench_lie`'s reading).
- **Spill share** = (sens − sens with blood at remote) / sens, at the same registration and noise. The same is
  computed for the false-call rate.
- **E9 (truth-free numbers per registration):**
  - the transform's log-determinant;
  - the LIE half-maximum edge offset from the carried endocardium and epicardium (median over segments) and their
    difference (dthick);
  - the three JA29 QC shares.
- 22 hearts × 3 motions × 3 blood levels × 2 CNR = 396 LIEs, about 3 h on 4 CPUs.

## Result (CNR 5 unless stated; pooled over the 22 hearts)

**Presence: sensitivity / specificity** (specificity counts negative segments of scarred hearts and every segment
of the scar-free variant):

| Motion, blood | P-K exact | P-G exact | P-G affine | P-G chain | P-J exact | P-J chain |
|---|---|---|---|---|---|---|
| chest, below | 0.78 / **0.42** | 0.78 / 1.00 | 0.81 / 1.00 | 0.71 / 0.96 | 0.72 / 0.99 | 0.45 / 0.98 |
| chest, equal | 0.78 / **0.42** | 0.80 / 1.00 | 0.81 / 0.99 | 0.73 / **0.93** | 0.66 / 1.00 | 0.55 / 0.99 |
| chest, above | 0.78 / **0.42** | 0.80 / 1.00 | 0.80 / 0.98 | 0.78 / 0.99 | 0.66 / 0.99 | 0.66 / 0.98 |
| static, below | 0.77 / **0.43** | 0.82 / 1.00 | 0.77 / 1.00 | 0.72 / 0.96 | 0.72 / 0.99 | 0.55 / 0.98 |
| static, equal | 0.77 / **0.42** | 0.82 / 1.00 | 0.75 / 0.99 | 0.72 / **0.92** | 0.66 / 0.99 | 0.59 / 0.99 |
| static, above | 0.78 / **0.42** | 0.82 / 1.00 | 0.76 / 0.98 | 0.75 / 0.97 | 0.67 / 0.98 | 0.64 / 1.00 |

- **P-K fails on specificity in every condition**: 0.42 on exact borders, and 0.50–0.74 after any registration.
  Its half-way threshold falls to noise in segments without scar (Kilo E8 found the same on scar-free hearts).
- **P-J fails on sensitivity even on exact borders** (0.66–0.73), and 0.45–0.66 on the chain.
- **P-G:** 0.78–0.82 / 1.00 on exact borders; 0.75–0.81 / 0.98–1.00 after affine; 0.71–0.78 / 0.92–0.99 on the
  chain.

**Sensitivity by true bin (P-G, exact borders): 0.41–0.53 / 1.00 / 1.00 / 1.00.** P-J's bin 1 is 0.08–0.24. Every
rule detects bins 2–4 almost always and bin 1 rarely. **Pooled sensitivity ≈ 1 − (bin-1 share) × (1 − bin-1
sensitivity)**: with 37 % bin-1 segments here, ≈ 0.80.

**The spill share of P-G's sensitivity is ≤ 0.05** on exact, rigid, affine and chain borders, at every blood
level and motion. It reaches 0.19–0.21 only on unregistered R0 borders (≈ 2 mm ASSD) with blood ≥ scar, in the
static-chest and phase motions. **Spill shows up as
false calls instead.** On the chain, P-G's false-call rate is 0.014–0.076 with blood, against ≤ 0.011 with blood at
remote. That is what pulls the chain's specificity to 0.92–0.93 at equal blood. On affine borders it is ≤ 0.017.

So the Round 2 judge's reading ("its 0.75 is partly spill") is not borne out on these hearts. Under JA30's remote,
P-G's sensitivity on exact borders (0.78–0.82) is higher than on any registered border, and what is missed is bin 1,
cut by the 1 mm exclusion. Spill costs specificity, not sensitivity.

**Extent (P-G-called scar-on-both segments; bin agreement vs volume / vs depth truth; SD of the extent error, in
wall share):**

| Motion, blood | E-V exact | E-V affine | E-V chain | E-D affine | E-D3 affine |
|---|---|---|---|---|---|
| chest, below | 0.90 / 0.95, 0.02 | 0.89 / 0.85, 0.07 | 0.62 / 0.61, 0.15 | 0.81 / 0.74, 0.08 | 0.85 / 0.92, 0.09 |
| chest, equal | 0.89 / 0.94, 0.03 | 0.85 / 0.82, 0.06 | 0.70 / 0.70, 0.13 | 0.78 / 0.74, 0.09 | 0.83 / 0.92, 0.08 |
| chest, above | 0.90 / 0.95, 0.03 | 0.86 / 0.83, 0.08 | 0.85 / 0.83, 0.09 | 0.77 / 0.75, 0.10 | 0.85 / 0.89, 0.10 |
| static, below | 0.89 / 0.96, 0.02 | 0.84 / 0.82, 0.09 | 0.61 / 0.60, 0.14 | 0.75 / 0.73, 0.11 | 0.79 / 0.87, 0.13 |
| static, equal | 0.89 / 0.96, 0.03 | 0.81 / 0.79, 0.09 | 0.62 / 0.64, 0.14 | 0.75 / 0.75, 0.11 | 0.76 / 0.84, 0.13 |
| static, above | 0.88 / 0.95, 0.03 | 0.84 / 0.82, 0.08 | 0.83 / 0.80, 0.10 | 0.76 / 0.76, 0.11 | 0.78 / 0.83, 0.12 |

- **On exact borders every extent measure is nearly right** (extent error SD 0.02–0.08).
- **The chain doubles the extent error** against always-affine: 0.09–0.15 vs 0.06–0.09. It stops at R0 in
  18–30 % of non-phase cases, and keeps rigid where affine was better: affine had the lower endocardial ASSD in
  87.5 % of non-phase cases, but the chain kept it in only 15–32 %.
- **E-V matches volume truth best** (0.81–0.89 after affine), and **E-D3 matches depth truth best** (0.83–0.92).
  E-D with the half-way voxel cut is the worst on both (0.73–0.81).

**The chain's QC** (cuts from the other half; "bad" = endocardial ASSD > 1 mm):

| Motion | CNR | Stopped at R0 | QC fail | Truly bad | QC pass but bad | QC fail but good |
|---|---|---|---|---|---|---|
| chest | 5 | 26 % | 23 % | 27 % | 17 / 66 | 14 / 66 |
| static | 5 | 18 % | 20 % | 21 % | 13 / 66 | 12 / 66 |
| phase5 | 5 | 24 % | 50 % | 71 % | 19 / 66 | 5 / 66 |

The three QC shares barely separate good registrations from bad ones in either direction. They are blood- and
scar-dependent: a bright scar raises "brighter than blood" in a well-registered heart.

**E9, the truth-free phase check** (AUC, phase5 vs chest and static, all blood levels, CNR 5):

| Number | After rigid | After affine |
|---|---|---|
| affine log-determinant (heart volume change) | — | **0.86** (0.85–0.87 by blood level) |
| median endocardial half-maximum offset, all segments | 0.72 | 0.68 |
| wall-thickness mismatch (dthick) | 0.50 | 0.57 |

- The log-determinant reads +0.023 (median) for the breath-hold motion and +0.047 with the 5 % phase change. Note
  that the breath-hold motion here includes a 3 % scale, itself a heart-volume change.
- A cut at 0.035 flags 76 % of phase cases with 17 % false flags; at 0.045, 52 % and 9 %. In a phase-matched patient
  with no scale term, the false-flag rate should be lower; this run cannot show it.
- My edge offset, a median over all segments, is weaker than Kilo's E8 version (the 6 remote segments only, |offset|
  > 0.6 mm flagging 90–100 %). Restricting it to remote segments keeps scarred, blood-bright segments out of the
  profile, which is the likely difference.
- dthick does not work.

## What it changes

1. **Strike P-K** (specificity ≤ 0.74 everywhere). **P-J is not viable as written** (sensitivity ≤ 0.73 even on
   exact borders, because τ = p99 of scar-free T sits above bin-1 extents). **P-G is the presence rule to take to
   development.** The benchmark's pre-registered rules decide formally.
2. **The bin-1 blind spot is shared by every rule.** The JA32 sensitivity endpoint therefore depends on the
   cohort's bin-1 share. Development should report sensitivity by bin, and Scar-1's first job is bin 1.
3. **Registration: always run masked rigid then affine; do not stop at R0, and do not let QC veto affine.** QC
   values are logged and shown to the reader, and they can trigger the reader's attention, but they do not choose
   the stage. This halves the extent error that E10 says decides the study.
4. **E-D's voxel cut: 3 SD, not half-way** (against `scar0.py`'s reading 3). The extent menu becomes E-V vs E-D3.
   The read form (volume share) favours E-V.
5. **Phase check:** the heart-masked affine's log-determinant, with the flag cut set on development as the p95 over
   phase-matched patients. Kilo's remote-segment edge offset is the second check. Both are compared on the shared
   benchmark.

## Limits

- One generator (mine); a synthetic LIE with homogeneous tissue; a single scar territory per heart; one seed per
  condition.
- The QC "reader" is a truth threshold (ASSD ≤ 1 mm).
- The 3 % scale in the breath-hold motion is a modelling choice that makes "no phase change" a 3 % volume change.
- CNR 3 numbers are in `lie_menu.json` and show the same pattern, with chain extent agreement down to 0.55–0.60.
