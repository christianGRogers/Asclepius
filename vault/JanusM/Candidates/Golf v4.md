---
tags: [janus-m, plans, candidate, round4, paired-scar, scar, LIE, registration, power, benchmark]
author: Golf
round: 4
version: 4
path: jm/paired-scar
updated: 2026-10-31
issue: christianGRogers/Asclepius#251
---

# Golf v4: the shipped chain on the shared benchmark, one affine rule, and what failure rate the seal can afford

*Path `jm/paired-scar` (LQ1 option B). The base is the path plan: [[Kilo v2]] with JA25–JA36 and JA50–JA59. This note
settles #251 items 1–5 (= Round 3 ruling §7 items 1, 2 and 4, plus the affine rule and the phase-unmatched stratum).
Code and JSON are in `experiments/JanusM/bench_lie/` (v3, shared) and `experiments/JanusM/Golf/r4/`.*

<!-- BENCH-SUMMARY -->

---

## 4. Item 3: the power engine, re-run (Golf E12, `Golf/r4/power_r4.py`)

### 4.1 Set-up

- **Engine:** `janusm.scar.power.simulate_studies` with Golf's cohort, scored by `janusm.scar.scoring` as shipped
  (SCAR_VERSION 1.1.0). JA55 split accounting with the yield bar; JA56 claim 1 (sensitivity, specificity and
  yield).
- **Settings:** JA57's planning inputs (`JA32_BASE`: bin error 0.25, specificity 0.98, `bin_tau` 1.0, Golf's
  sensitivity by bin).
- **Grid:** 24 cells:
  - failure 0, 2 or 5 %;
  - clustering weak (τ 0.7) or strong (1.2);
  - enrichment 50 or 70 %;
  - infarct size Golf's (1 + Poisson(3): 3.99 scarred segments per scar patient) or Kilo's (3.25).
- **Simulations:** N = 80–320 in steps of 20, with **1 500 studies per point** and 400 bootstrap replicates. The
  Monte-Carlo SE at power 0.80 is 0.010.
- **Reading N80** (`power_r4_table.py`):
  - by `seal_size`'s grid rule;
  - by linear interpolation of the first crossing;
  - with a band from moving every grid point ±2 MC SE.

### 4.2 Reproductions (all within Monte-Carlo error)

| Cell | Recorded | Now (1 500 sims) | z |
|---|---|---|---|
| Juliet E9, split, weak, 2 %, 50 %, N 200 | 0.848 (400 sims) | 0.845 | −0.13 |
| Juliet E9, split, weak, 2 %, 70 %, N 160 | 0.865 (400 sims) | 0.867 | +0.09 |
| Golf E10 segments for 270, Kilo size, 50 / 70 % (median / p90) | 167 / 187; 119 / 130 | 167 / 186; 119 / 131 | — |
| Golf E10 segments for 270, Golf size, 50 / 70 % | 135 / 155; 97 / 108 | 135 / 153; 97 / 107 | — |

### 4.3 The planning table (claim 1; seal = max(120; 270-segment N; N80), cap 240)

| Clustering | Enrich | Failure | Infarct size | Power at 160 / 200 / 240 | N80 (interp, MC band) | N80 (grid) | Seal |
|---|---|---|---|---|---|---|---|
| weak | 70 % | 0 % | Golf / Kilo | 0.99 / 1.00 / 1.00; 0.98 / 1.00 / 1.00 | ≤ 80 | 80 | **120** (floor) |
| weak | 70 % | **2 %** | Golf | 0.86 / 0.92 / 0.96 | **128** (119–137) | 140 | **129–140** |
| weak | 70 % | **2 %** | Kilo | 0.85 / 0.90 / 0.96 | **145** (138–152) | 160 | **146–160** |
| weak | 70 % | 5 % | both | 0.41–0.44 / 0.45–0.52 / 0.57–0.60 | never ≤ 320 (0.68–0.72 at 320) | — | 240 (cap), **underpowered** |
| weak | 50 % | 0 % | Golf / Kilo | 0.97 / 0.99 / 1.00; 0.94 / 0.97 / 0.99 | 85 / 99 | 100 | 136 / 167 (segments) |
| weak | 50 % | **2 %** | Golf | 0.75 / 0.84 / 0.90 | **182** (172–191) | 200 | **182–200** |
| weak | 50 % | **2 %** | Kilo | 0.71 / 0.81 / 0.85 | **196** (189–208) | 200 | **197–200** |
| weak | 50 % | 5 % | both | 0.32–0.35 / 0.38–0.42 / 0.44–0.45 | never ≤ 320 | — | 240, underpowered |
| strong | 70 % | 0 % | Golf / Kilo | 0.80 / 0.89 / 0.93; 0.77 / 0.84 / 0.89 | 162 / 173 | 180 | 162–180 |
| strong | 70 % | **2 %** | both | 0.47–0.52 / 0.53–0.60 / **0.64–0.69** | never ≤ 320 (0.76–0.77 at 320) | — | 240, **underpowered** |
| strong | 50 % | 0 % | Golf / Kilo | 0.67 / 0.77 / 0.84; 0.61 / 0.71 / 0.80 | 217 / 240 | 220 / 260 | 217–240 |
| strong | 50 % | 2 % or 5 % | both | ≤ 0.56 at 240 | never ≤ 320 | — | 240, underpowered |

Claim 2 jointly (presence and the Kim bin at anchor 0.70) gives the same N80 in every cell to within 1 patient. At
bin error 0.25 the Kim-bin bar almost never binds after presence passes, so sizing on claim 1 alone (JA57) loses
nothing here.

### 4.4 What this changes

1. **Why the #248 engineer saw ≈ 120 / ≈ 180 and the ruling ≈ 160 / ≈ 200.**
   - Near 0.80 the curves are shallow: about +0.02 to +0.04 of power per 20 patients. At 300 simulations the MC SE is
     0.023, so `seal_size`'s grid rule ("the first N from which power *stays* ≥ 0.80") moves by one or two grid steps
     from noise alone.
   - The infarct-size model moves N by another 15–20 patients: Kilo's smaller infarcts need more.
   - At 1 500 simulations, the 2 % / weak cells are **70 %: 128 (Golf size) to 145 (Kilo size); 50 %: 182 to 196**.
     The ruling's ≈ 160 / ≈ 200 are the Kilo-size grid values, and the engineer's ≈ 120 / ≈ 180 are low-side noise
     on the Golf size. Both are inside the band.
2. **Planning figure (replaces JA57's "≈ 160 / ≈ 200").** At weak clustering and 2 % failure the seal is **≈ 130–150 at
   70 %** and **≈ 180–200 at 50 %**. Plan the lead's cohort on **150 at 70 %**, the Kilo-size value rounded up. The
   development-measured inputs then set the real size (JA57 unchanged).
3. **`seal_size` should use ≥ 1 000 simulations and say how it read N80.** At its default 400 the grid rule can move
   the seal by 20–40 patients between two runs on the same inputs. Spec PS4-G2 (§9): sims ≥ 1 000 by default, with
   the interpolated N80 and its MC band logged beside the grid value. The JA57 rule itself is unchanged.
4. **The 240 cap does not buy power where the plan is weakest** (E12b, `power_fail_tolerance.py`, 1 000 studies a
   cell). Claim 1 power at 240:

   | Clustering, enrichment | 0.5 % | 1 % | 1.5 % | 2 % | 3 % | 4 % |
   |---|---|---|---|---|---|---|
   | weak, 70 % | 1.00 | 0.99 | 0.95–0.99 | 0.93–0.96 | **0.86–0.87** | 0.72–0.76 |
   | weak, 50 % | 0.97–0.98 | 0.93–0.96 | 0.91–0.93 | 0.86–0.88 | 0.74–0.78 | 0.58–0.64 |
   | strong, 70 % | 0.82–0.89 | 0.79–0.83 | 0.71–0.76 | 0.61–0.67 | 0.46–0.53 | 0.34–0.35 |
   | strong, 50 % | 0.71–0.78 | 0.64–0.71 | 0.55–0.61 | 0.52–0.55 | 0.37–0.39 | 0.27–0.29 |

   **The failure rate the seal tolerates is about 3 % at the cap (weak clustering, 70 %), and about 2 % at the
   planning size.** JA29's development stop (not-graded > 10 %) lets the study proceed at failure rates where no seal
   ≤ 240 can pass claim 1. Under strong clustering, even 1 % failure leaves 240 short.
5. **Proposed amendment (for JA57 and JA29's stop; for the judge).**
   - After development, `seal_size` reports the claim 1 power **at the size it returns**, not only the size.
   - If that power is < 0.80, which happens when the cap binds, the lead is told **before any seal patient is
     graded**. The report gives the measured failure rate and clustering, and the power at 240.
   - The lead then chooses: proceed and accept the stated power; reduce failure (development's B-spline arm,
     JA53, or reader re-checks); or stop.
   - JA29's > 10 % stop stays as the hard floor. **This changes no bar.** It turns a silent underpowered seal into a
     stated decision. Spec PS4-G3 (§9).

---

<!-- ITEM4 -->

<!-- ITEM5 -->
