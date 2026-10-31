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

## 1. The plan in one paragraph

**The shipped chain passes the benchmark. P-J and P-G both survive, and the path stays Kilo v2 + JA25–JA36 + JA50–JA59.
Round 4 moves three things: the affine rule, how the phase step flags, and what failure rate the seal can afford.**
- **Item 1, the shipped chain on the shared benchmark (v3, 518 cases, 20 hearts + phantom; §3).**
  - **P-G survives JA54's strike** on JA51's chain as shipped: sensitivity ≥ 0.915, specificity ≥ 0.985, scar-free
    specificity ≥ 0.989, spill ≤ 0.012.
  - **P-J survives** with τ re-fitted under the chain: ≥ 0.888 / ≥ 0.958 / ≥ 0.972, spill ≤ 0.125.
  - **P-K stays struck.** E-V and E-D survive (exact-bin agreement 0.91–0.96).
  - Assembling the chain from logged stages matches the shipped `register_lie` end to end (9 of 9 cases, identical
    TRE).
  - **`module_parity` fails on E-D on real hearts** (89 of 2 028 segments; max 0.19). One constant causes it: the
    module keeps E-D columns of ≥ 6 depth bins, the benchmark ≥ 4. With 4, 18 of 18 failing cases pass. Spec
    PS4-G1.
- **What the benchmark shows the chain is not doing.**
  - **The provisional QC cuts make the gate meaningless.** They are p95 of *perfectly aligned* R0 images, so 4 mm
    rigid passes QC on 0 of 63 rigid-motion cases at TRE 0.26 mm. Every patient therefore falls through to affine
    and the 10 mm fallback.
  - **The fallback is harmful on phase mismatch.** It replaces rigid (0.26 mm) on 37 of 74 phase cases, raising the
    median TRE to 0.88 mm (p90 3.75 mm).
  - **A 3 % or 3 / 3 / 6 % scale is left uncorrected** by every literal-rule chain. Specificity on those hearts is
    0.48–0.89, against ≥ 0.96 on true borders.
  - **B-spline, as configured, is worse than rigid** (median TRE 2.2 mm) and fails pre-registered rule 4.
- **Item 2, the affine rule (§4).**
  - **Pre-registered pick: rule (g)** (sanity bound; normalised maximum does not rise; and affine passes QC or
    |log det| ≥ 0.02). It is Golf's own candidate, so I state the margin: it beat (b) by 0.035 mm of p90, just
    outside the 0.02 mm tie margin. Under Kilo's pre-registered criterion, on the same rows, (g) also leads: 2.91 against
    (b)'s 2.98, with no harmful keeps on rigid motion (§4.2).
  - **Independent of the pick, (g) also keeps the correct affine on the PS3-S3 phantom; (b) does not.** The
    PS3-S3 test has a sign error of its own: it expects log det > +0.03, and the correct value is −0.081.
  - (c) and always-affine re-strike both P-J and P-G on rigid motion.
- **Item 3, power (§5).** Both checks reproduce within Monte-Carlo error: Juliet E9 (z −0.13, +0.09) and Golf E10's
  segments-needed.
  - **The planning figure is ≈ 130–150 at 70 % and ≈ 180–200 at 50 %** (weak clustering, 2 % failure, 1 500 sims a
    point). The #248 engineer's and the ruling's figures are both inside the noise of a 300- or 400-sim grid rule.
  - **The seal tolerates about 2 % failure at its planning size and about 3 % at the 240 cap.** Under strong
    clustering even 1 % failure leaves 240 underpowered.
  - So `seal_size` should say what power it delivers, and the lead should hear before grading if it is < 0.80.
- **Item 4, the phase-unmatched stratum (§6).**
  - A flagged phase mismatch cannot be scored in the primary: P-J specificity falls to 0.21–0.54 when the LIE cavity
    is larger.
  - Scoring it as a JA55 failure would charge sensitivity for a data property. In the larger-cavity case the CT
    still finds 0.94–0.99 of scarred segments.
  - **Proposal:** JA27's `phase_unmatched` stratum, excluded from primary accuracy. Patients routed out **on the
    truth-free flag alone** also count in the yield numerator, so routing out cannot be used to shed hard patients.
  - **The edge offset becomes the primary flag:**
    - it flags 1 of 148 phase-matched cases falsely (`rim_dark`: 95 of 148 at the shipped cut, 14–18 of 74 rigid cases
      at a JA53-style cut);
    - it catches 95 % of larger-cavity cases and 78 % of smaller-cavity ones.

    `rim_dark` keeps its AUC 0.999 for the smaller cavity, but becomes a reader-confirmed flag.
- **Item 5:** the path summary for #143 (§7).

---

## 2. What was run, and what I disclosed on #251 before results

- **The shared benchmark v3** (`bench_lie/run_v3.py`, `score_v3.py`), proposed and pre-registered in Golf's first #251
  comment (2026-10-30, before the run started). Our three claims crossed and three runs started within ten minutes.
  On #251, Juliet and Kilo agreed that **Golf's run is the canonical v3** and theirs are replications. Kilo found every
  stage TRE identical on the 96 cases his rows share with Golf's.
  - Same hearts, guard first on the whole list and per heart. The v2 conditions keep v2's seed string, so their
    images are v2's.
  - **New motions:**
    - `phase_neg`: LIE cavity grown 5 % of its equivalent radius;
    - `aniso`: 3 / 3 / 6 % scale in a random frame, random sign.
  - **Arms:** the shipped `janusm.scar.registration` stages (rigid 4 mm, affine 4 mm, rigid 10 mm, all Euclidean),
    graded by `menu.grade`, which #179's strike rules were written against.
- **Disclosed on #251 before full results** (comments of 19:04 and 23:00 UTC):
  1. **B-spline narrowed** to `nonrigid` (all) and `rigid` at CNR 5. Reason: run time.
  2. **`free_fixed` dropped.** It fed only the reported `spill_twin`.
  3. **Two run incidents, both fixed.** A crash on an empty carried wall: now recorded as ungradable, and its
     scarred segments count as misses (1 arm in 518 cases, a B-spline arm). And ITK threading.
  4. **The CNR cut.** The remaining 20 hearts ran at **CNR 5 only**. CNR 3 is a reported subset on 4 hearts (77
     cases).
     - I had scored those 4 hearts before this cut, to debug the scorer, and said so on #251.
     - #179's strike rules read CNR 5 only, so they are untouched.
     - The affine-pick constraint was still checked at both CNRs, which is stricter than announced.
  5. **Post-hoc chains, labelled and report-only:** fallback kept only if it passes QC, and no fallback. They strike
     nothing.
- **Not disclosed on #251 beforehand** (added after an interim look at 12 hearts, report-only, striking nothing):
  - the JA53-style `rim_dark` phase cut;
  - the registered-patient QC cuts (`qc_cuts_registered`), with their chains (`*_regcuts`).

  Every verdict in §3.1 is also stated without them.
- **Golf R4 experiments** (`experiments/JanusM/Golf/r4/`):
  - **E11:** `module_parity` on the 20 hearts, and `parity_ed_cause` (the E-D column minimum);
  - **E11b:** `chain_parity` (`register_lie` end to end against the assembled chain);
  - **E11c:** `ruleg_plugin` (the PS3-S3 tests under rules g and b);
  - **E12:** `power_r4`, the planning table;
  - **E12b:** `power_fail_tolerance`.
- **Rules kept:**
  - CPU only, no Fir, SciNet or Alliance job;
  - the guard runs first in every path that opens a heart;
  - no held-out case or TotalSegmentator twin list read;
  - no image anywhere in the PR;
  - nothing in `src/` changed;
  - no request to anyone outside the project.

---

## 3. Item 1: the shipped chain through the shared benchmark

### 3.1 The strike (pre-registered; CNR 5, motion `none` and `rigid`, every blood level; JA51 literal)

| Rule | Min sensitivity | Min specificity | Min scar-free spec. | Max spill | Verdict |
|---|---|---|---|---|---|
| P-K | 0.977 | 0.885 | **0.006** | 0.074 | **struck** (as Round 3) |
| P-J (τ re-fitted under the chain) | 0.888 | 0.958 | 0.972 | 0.125 | **survives** |
| **P-G** | **0.915** | **0.985** | **0.989** | 0.012 | **survives → JA54's reinstatement stands** |

| Extent (exact Kim-bin agreement on scar-on-both, pooled) | volume truth | depth truth | Verdict |
|---|---|---|---|
| E-V under P-J / P-G | 0.923 / 0.924 | 0.959 / 0.961 | survives |
| E-D under P-J / P-G | 0.906 / 0.908 | 0.942 / 0.945 | survives |

- **P-J's τ under the chain** (p99 of E-D on scar-free segments of the other half, CNR 5) is 0.073–0.214 by blood
  level. That is within 0.013 of τ on true borders (0.068–0.223). On the 4 mm chain, τ no longer has to absorb
  registration error, which it did on JA29's 10 mm chain.
- **Bin 1** (chain, CNR 5, `none` / `rigid`): P-J 0.60–1.00, P-G 0.60–0.90. Bins 2–4 are 1.00 for both. As in Round
  3, thin scar is where sensitivity is lost (JA54's reporting by bin stands).
- **The same verdicts hold under** (g), (a), (b), never-affine, both post-hoc fallback variants and the
  registered-patient cuts: P-G ≥ 0.910 / 0.981 / 0.989, P-J ≥ 0.865 / 0.950 / 0.966.
- **(c) and always-affine re-strike both:** P-G specificity 0.916–0.920, P-J sensitivity 0.716. That happens through
  affine overshoot on rigid motion (§4).
- **CNR 3 subset** (4 hearts, report only): P-G sensitivity is 0.67–0.94, against 0.92–0.98 at CNR 5. P-J
  specificity at `below` / `equal` with rigid motion is 0.887 / 0.911. These are too few hearts for a verdict, but at
  CNR 3 P-G's sensitivity at `equal` blood and P-J's specificity would both be near the bars.

### 3.2 Registration, by motion (TRE median / p90 mm; 74 cases a motion: 63 at CNR 5 + 11 at CNR 3)

| Motion | R0 | rigid 4 mm | affine 4 mm | rigid 10 mm | **chain (JA51 literal)** | chain (g) | chain, fallback only if it passes QC* |
|---|---|---|---|---|---|---|---|
| none | 0 / 0 | 0.33 / 0.55 | 0.44 / 1.55 | 0.12 / 0.23 | **0.11 / 0.32** | 0.11 / 0.32 | 0.13 / 0.50 |
| rigid | 4.15 / 4.57 | 0.26 / 1.13 | 0.48 / 2.26 | 3.50 / 4.30 | **0.27 / 1.10** | 0.27 / 1.10 | 0.26 / 1.13 |
| scale 3 % | 4.28 / 4.76 | 1.98 / 2.88 | 0.57 / 2.07 | 3.52 / 4.42 | **1.84 / 2.69** | 1.79 / 2.62 | 1.94 / 2.86 |
| aniso 3/3/6 % | 4.45 / 5.11 | 2.66 / 4.12 | 0.41 / 2.67 | 4.11 / 4.95 | **2.79 / 4.50** | **1.04** / 4.11 | 2.58 / 4.05 |
| phase (cavity −5 %) | 4.18 / 4.61 | 0.26 / 0.90 | 0.47 / 2.08 | 3.20 / 4.34 | **0.88 / 3.75** | 0.88 / 3.75 | **0.26 / 0.90** |
| phase_neg (cavity +5 %) | 4.15 / 4.63 | 0.29 / 0.96 | 0.56 / 2.59 | 3.47 / 4.35 | **0.30 / 0.91** | 0.32 / 0.94 | 0.29 / 0.96 |
| nonrigid (Kilo) | 6.77 / 10.21 | 1.85 / 2.89 | 2.03 / 3.34 | 1.65 / 2.18 | **1.65 / 2.26** | 1.65 / 2.20 | 1.85 / 2.85 |

\* post-hoc, report only.

What the table shows about the shipped chain:
1. **The QC gate does not gate.**
   - The provisional cuts (p95 of R0 on *aligned* images, the benchmark's and `load_provisional_qc_cuts`'s
     definition) sit at the QC values of a perfect registration. `rim_dark`'s cut is 0.001–0.06.
   - So 4 mm rigid passes QC on **0 of 63** rigid-motion cases at CNR 5 (TRE 0.26 mm median), 0 of 63 aniso and 3
     of 63 scale.
   - Every patient falls through to affine and the fallback, and their acceptance rules decide the result.
   - With cuts defined as JA53 defines them for development (p95 over registered, reader-passed patients; emulated
     as 4 mm rigid with TRE < 1 mm on matched motions, other half), R0 is kept on 57 of 74 aligned cases, and 4 mm
     rigid passes QC on 37 of 63 rigid-motion cases. Presence verdicts are unchanged (§3.1).
   - **So provisional cuts must come from registered cases, not aligned ones** (spec PS4-G5).
2. **The 10 mm fallback is good for whole-image motion and bad for phase.**
   - On `nonrigid` it improves on rigid 4 mm (1.65 against 1.85 mm). There the chest moves too, and the 10 mm mask
     sees it.
   - On `phase` it replaces a 0.26 mm rigid result on 37 of 74 cases: chain median 0.88 mm, p90 3.75 mm. "Lowers the
     normalised maximum" admits a wrong registration that hides the phase signal.
   - Keeping it only when it passes QC fixes phase and costs nonrigid 0.2 mm. Phase-mismatched patients leave the
     primary analysis anyway (§6), so **I do not propose changing step 5 on this evidence alone**. I report it to the
     judge as a known cost.
3. **Scale is not corrected under the literal rule.**
   - Affine fixes scale when it is allowed to (aniso 0.41 mm, scale 0.57 mm median). The literal rule keeps it on 4
     of 74 scale and 13 of 74 aniso cases.
   - The resulting chain borders cost specificity: P-J 0.48–0.69, P-G 0.61–0.89 at CNR 5, against ≥ 0.96 / ≥ 0.99 on
     true borders.
   - Rule (g) keeps affine on 15 / 41 cases and brings the aniso median TRE from 2.79 to 1.04 mm. P-J specificity on
     aniso goes from 0.65–0.78 to 0.76–0.82; P-G sensitivity at `below` blood goes from 0.53 to 0.85.
   - Scale is not a strike motion, but a heart that changes shape between the scans is what affine is for.
4. **Kilo's non-rigid motion is still not solved** (chain 1.65 mm; P-J specificity 0.70–0.82, P-G 0.74–0.90).
   Round 3's ruling stands: the reader check and the yield bar carry it.
5. **The affine stage's sanity bound fails on 11 of 74 scale and 11 of 74 aniso cases.** These are true 3–6 %
   scales, so the shipped Powell affine occasionally wanders: a 12-parameter Powell from rigid, 2 000 evaluations
   per level. This is not a rule question. It is recorded for the engineer: affine runs with a scale-only stage
   first, or more evaluations.

### 3.3 B-spline (JA53; pre-registered rule 4: report only)

- **Settings:** SimpleITK B-spline from rigid 4 mm, 20 mm control spacing, 4 mm Euclidean mask, LBFGSB (100
  iterations, 2 levels).
- **Results:**
  - **nonrigid:** median TRE 2.06 mm (p90 4.18), against the chain's 1.65 / 2.26;
  - **rigid at CNR 5:** 2.17 mm (p90 4.82), against 0.27.
- **Presence on nonrigid:** P-J specificity 0.96–0.99, but its sensitivity collapses to 0.12–0.56. P-G specificity
  is 0.42–0.82.
- **Rule 4's verdict:** the first half holds (P-J specificity ≥ 0.93 on nonrigid). The second fails: it raises
  rigid's median TRE by 1.9 mm. **Not worth a development arm as configured.**
- **JA53's trigger** (reader-fail > 10 % or not-graded > 2 %) should then open a *different* non-rigid method, or
  the stated-power report of §5.4. It should not open this B-spline. A regularised B-spline is beyond this round.

### 3.4 Module parity (PS3-S7) and chain parity

- **`bench_lie/module_parity.json`** (guard first; 20 hearts, 120 cases; CNR 5, `none` / `rigid`, every blood level,
  oracle geometry): **62 of 120 cases pass.**
  - E-V: max |diff| 0.0004;
  - P-G share: 0.0015;
  - **E-D: 0.191**, with 89 of 2 028 segments over 0.02.
- **The cause** (`Golf/r4/parity_ed_cause.json`): `scar0.JA30Constants.column_min_bins = 6` against the benchmark's
  `ok = ccnt >= 4`. With only that constant set to 4, passed through `scar0(constants=…)`, **18 of 18** failing cases
  pass (max 0.0006).
  - The CI phantom passes because its wall is thick enough that no column has 4–5 bins.
  - JA54's extent verdict was reached at ≥ 4, so the module should follow it, as JA54 did for P-G's denominator
    (spec PS4-G1).
- **`Golf/r4/chain_parity.json`:** the shipped `register_lie`, run end to end with score_v3's cuts on the phantom
  and two hearts (rigid, aniso, phase_neg; CNR 5; equal blood), ends on the assembled chain's final stage in **9 of
  9** cases, with identical TRE. The benchmark's chain *is* the shipped chain.

---

## 4. Item 2: the JA51 4(b) affine rule

### 4.1 The candidates, scored as whole chains (pre-registered on #251)

| Rule | Scale motions*: TRE median / p90 | none / rigid within 0.05 mm of never-affine (every blood × CNR) | New strike | Qualifies |
|---|---|---|---|---|
| JA51 4(b) literal | 1.54 / 3.76 | yes | — | yes |
| (a) no rise in the 3 wall shares; max falls | 1.54 / 3.76 (identical to literal) | yes | — | yes |
| (b) max falls; no value newly crosses its cut | 0.91 / 3.46 | yes | — | yes |
| (c) sanity alone when \|log det\| ≥ 0.02 | 0.82 / 3.68 | **no** (rigid p90 1.87–3.47 against 0.29–1.12) | **P-J, P-G** | no |
| **(g) (Golf):** max does not rise, and (passes QC or \|log det\| ≥ 0.02) | 0.88 / **3.43** | yes | — | **yes → pick** |
| never-affine | 1.75 / 4.07 | — | — | reference |
| always-affine-if-sane | 0.87 / 3.68 | **no** | **P-J, P-G** | no |

\* `scale`, `aniso`, `phase`, `phase_neg`, pooled (296 cases).

- **The pick by the pre-registered rule is (g).** Lowest p90 among qualifying rules (3.43). The nearest is (b), 3.46,
  0.035 mm away, outside the 0.02 mm tie margin.
  - The pooled p90 is dominated by the fallback on phase cases (§3.2), which no affine rule touches. So the margin is
    small, and (g) being my own rule is a reason to look past it.
  - Three things separate them, and all three favour (g):
    1. **On rigid motion, (g) keeps affine on 0 of 74 cases; (b) keeps it on 8 of 74.** E10's overshoot happens
       exactly there. (g)'s "|log det| ≥ 0.02 or QC passes" clause is what refuses an affine that found no scale.
    2. **On aniso, (g) keeps affine on 41 cases against (b)'s 38.** Median TRE 1.04 against 1.58; P-G sensitivity at
       `below` blood 0.85 against 0.76.
    3. **On the PS3-S3 phantom, (g) keeps the correct affine; (b) rejects it** (E11c, `ruleg_ps3_s3.json`).
- **Why the literal rule (and (a)) fails, measured.** Correcting a misregistration lowers some normalised shares and
  raises others: `rim_dark` when the LIE heart is larger; blood-like and above-blood when smaller (#243). Requiring
  "no value rises" therefore rejects most correct affines. It kept affine on 4 of 74 scale cases, although affine's
  TRE beat rigid's on 67 of them. (a) changes nothing on the benchmark because the rising value is usually a wall
  share, not `rim_dark`.
- **Why (c) fails.** On rigid-only motion the 4 mm affine often finds a spurious |log det| ≥ 0.02 (E10's overshoot).
  Letting the sanity bound decide alone keeps it.

### 4.2 The same rows under Kilo's and Juliet's pre-registered criteria

On #251, Kilo and Juliet agreed that Golf's run is the canonical v3 and theirs are replications. Kilo reports that
every stage TRE on the 96 cases his rows share with Golf's agrees exactly. Each of us pre-registered a different way
to choose the affine rule. (g) was not in their candidate sets, so I scored it under Kilo's criterion on the same
rows. That criterion is the lowest pooled p90 over `rigid`, `scale` and `aniso` at CNR 5, eligible only if ≤ 10 %
of rigid cases keep an affine that is worse by > 0.25 mm.

| Rule | Pooled p90 (median), CNR 5, rigid + scale + aniso | Harmful keeps on rigid (affine kept, worse by > 0.25 mm) |
|---|---|---|
| JA51 literal / (a) | 3.53 (1.74) | 0 / 63 |
| (b) | 2.98 (1.12) | 0 / 63 |
| (c), \|log det\| ≥ 0.02 | 3.46 (0.51) | 7 / 63 |
| **(g)** | **2.91** (0.93) | **0 / 63** |
| never / always | 4.11 (1.89) / 3.46 (0.64) | 0 / 63; 13 / 63 |

- **My literal, (b) and (c) values match Kilo's table on #251** (3.53, 2.98, 3.46). So the scorers agree.
- **(g) leads under Kilo's criterion too.**
- **Juliet's criterion** (pooled p90 over rigid, scale, aniso3, aniso6 on her rows) picked (c). Both Kilo and I find
  that (c) keeps overshooting affines on rigid motion and re-strikes P-G.
- **What all three criteria agree on:** the literal rule should go; (c) is unsafe; the answer is (b) or (g). (g)
  differs from (b) by also requiring that a kept affine either passes QC or shows a scale. That clause is what
  removes (b)'s 8 rigid-motion keeps and keeps the PS3-S3 phantom's correct affine.

### 4.3 Proposed rule (replaces JA51 4(b); for the judge)

> **4. Affine from rigid, with the same mask, is kept only if all hold:**
> - (a) the sanity bound (unchanged): |log det A| ≤ 0.15, and every scale and shear term within ± 15 %;
> - (b′) **the normalised QC maximum does not rise:** max over the gated values of value / cut, for affine,
>   ≤ the same for rigid;
> - (c′) **and either** the affine result passes QC, **or** it found a scale: |log det A| ≥ 0.02 (≈ 2 % in volume, 0.7 % linear).

- **The rule in plain words:** affine is kept when it is sane, does not make the worst QC value worse, and either
  passes QC or has a real scale to show for itself.
- **What it still cannot do:** fix a scale on a patient whose rigid registration already passes QC, because affine is
  never tried then. With registered-patient cuts (PS4-G5), rigid passes QC on 15 of 63 scale and 6 of 63 aniso cases
  at CNR 5, which leaves their scale uncorrected. Whether that matters on real hearts is a development question, not a
  benchmark one. I leave JA51 step 4's position in the chain unchanged.
- **The PS3-S3 test.** Under (g), the phantom with a 3 % scale keeps affine, ends on it, and lowers TRE. The test's
  last assertion (`log_det > 0.03`) has the wrong sign: in the module's convention (LIE fixed, first pass moving),
  a LIE heart 3 % *larger* gives log det = −0.081. It should read `abs(log_det) > 0.03`. Spec PS4-G4.

---

## 5. Item 3: the power engine, re-run (Golf E12, `Golf/r4/power_r4.py`)

### 5.1 Set-up

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

### 5.2 Reproductions (all within Monte-Carlo error)

| Cell | Recorded | Now (1 500 sims) | z |
|---|---|---|---|
| Juliet E9, split, weak, 2 %, 50 %, N 200 | 0.848 (400 sims) | 0.845 | −0.13 |
| Juliet E9, split, weak, 2 %, 70 %, N 160 | 0.865 (400 sims) | 0.867 | +0.09 |
| Golf E10 segments for 270, Kilo size, 50 / 70 % (median / p90) | 167 / 187; 119 / 130 | 167 / 186; 119 / 131 | — |
| Golf E10 segments for 270, Golf size, 50 / 70 % | 135 / 155; 97 / 108 | 135 / 153; 97 / 107 | — |

### 5.3 The planning table (claim 1; seal = max(120; 270-segment N; N80), cap 240)

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

### 5.4 What this changes

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
   the seal by 20–40 patients between two runs on the same inputs. Spec PS4-G2 (§8): sims ≥ 1 000 by default, with
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
     stated decision. Spec PS4-G3 (§8).

---

## 6. Item 4: how the phase-unmatched stratum is scored

### 6.1 What the benchmark says about phase-flagged hearts (chain, CNR 5 unless stated)

| | `phase` (LIE cavity −5 %) | `phase_neg` (LIE cavity +5 %) | phase-matched (`none` + `rigid`) |
|---|---|---|---|
| Flagged by the edge offset (\|offset\| > 0.6 mm) | 58 / 74 (78 %) | 70 / 74 (95 %) | **1 / 148** |
| Flagged by `rim_dark`, shipped phase cut (= R0 QC cut) | 73 / 74 | 3 / 74 | **95 / 148** |
| Flagged by `rim_dark`, JA53-style phase cut (p95 of the final stage on matched cases, other half) | 73 / 74 | 0 / 74 | 14 / 74 rigid, 0 / 74 none |
| AUC against `rigid` | `rim_dark` 0.999; edge offset 0.982 | edge offset 0.994; `rim_dark` 0.024 | — |
| P-J sensitivity / specificity, all cases | 0.73–0.87 / 0.87–0.96 | 0.94–0.99 / **0.21–0.54** | 0.89–1.00 / 0.96–1.00 |
| P-G sensitivity / specificity, all cases | 0.75–0.80 / 0.85–0.95 | 0.94–0.99 / 0.52–0.96 | 0.92–0.98 / 0.99–1.00 |

Three readings:
1. **A phase-mismatched heart cannot be scored in the primary.**
   - With a larger LIE cavity, the carried wall takes in blood, and P-J's specificity falls to 0.21–0.54.
   - With a smaller one, sensitivity falls to 0.73–0.87.
   - Kept in the primary, a 5–10 % phase-mismatch share would fail specificity because of a reconstruction choice,
     not the method.
2. **Nor is it a registration failure.**
   - Under JA55's split, a not-graded patient's scarred segments are misses. On `phase_neg` the CT finds
     0.94–0.99 of them.
   - E12b (§5.4) shows the seal tolerates about 2–3 % failure. Charging phase mismatch there would spend the whole
     budget on a data property.
3. **The flag that routes a patient out must have few false flags.**
   - `rim_dark`'s cut does not transfer across hearts: its baseline after registration varies by heart.
   - With the shipped default it flags 95 of 148 phase-matched cases; even with a JA53-style cut, 19 % of rigid
     cases.
   - The rigid-motion patients it flags are well registered: P-G specificity 0.94–1.00, P-J sensitivity
     0.93–1.00.
   - Routing them out loses good patients, and does so selectively. The edge offset falsely flags 1 of 148.

### 6.2 Proposal (amends JA52's routing and JA55's accounting; for the judge)

1. **The flags (amends JA52).**
   - **Primary flag:** the edge offset (|offset| > 0.6 mm), which sees both directions.
   - **`rim_dark`** stays a QC value and a flag. On its own, `rim_dark` routes a patient out only with the reader's
     "cavity size differs (phase)".
   - Both still need contrast ≥ 2 SD (otherwise "not evaluable", as JA52).
2. **The status.** `phase_suspect` becomes a final status (`FINAL_STATUSES`). `scar0.for_scoring` maps it to the
   JA27 stratum `phase_unmatched`, already in `scoring.STRATA` and `EXCLUDED_FROM_PRIMARY`.
   - **Out of the primary:** the patient leaves the primary sensitivity and specificity, and the yield denominator.
   - **Its own stratum:** it is scored on every segment, as `scoring.score` already does for a stratum, and
     reported.
3. **Who counts toward yield (amends JA55).**
   - **Charged:** a patient routed out **on a truth-free flag alone** (DICOM says phase matched and the reader did not
     mark "cavity size differs"; or phase was inferred from text, JA59) is counted in the yield numerator and stays in
     its denominator, but is still not scored in the primary.
   - **Not charged:** a patient whose mismatch is **confirmed independently** (DICOM fields, or the reader) is not
     charged.
   - **Why:** this bounds how many patients an algorithm can remove without anyone confirming it. The yield bar
     (≤ 0.10) already exists and costs nothing new.
   - **Expected cost:** the benchmark's edge-offset false-flag rate is 0.7 %. At that rate, flag-only routing costs
     the yield endpoint almost nothing.
4. **Stop rule.** JA52's > 20 % phase-suspect report to the lead stands. The judge may also want a second line:
   flag-only routing > 3 % on development is reported, since at that rate it eats the seal's power (E12b).

Spec PS4-G6 (§8).

---

## 7. Item 5: path summary for #143 (Round 3 §8, updated)

| | Path A, `jm/rest-ccta` | Path B, `jm/paired-scar` (after Round 4) |
|---|---|---|
| Assumes | no reference for scar or ischaemia | the lead obtains a paired CCTA + same-session LIE + CMR LGE cohort (data requirements only, D31) |
| Stage A | built and calibrated; bias guard 0.3 mm | identical code (JA50) |
| Scar rule | — | **P-J or P-G, both surviving the shipped chain** (P-G ≥ 0.915 / 0.985; P-J ≥ 0.888 / 0.958); P-K struck; E-V or E-D (3 SD) |
| Registration | — | R0 → QC (cuts from *registered* development patients) → 4 mm rigid → affine if sane, not worse on QC and (passing or scaled) → 10 mm fallback → reader check; phase routed out on the edge offset |
| What passing gives | specificity-calibrated flags | **presence** validated on sensitivity, specificity and yield; the **Kim bin** only if CT grades as well as the readers |
| Cohort | none | 40 development + **≈ 150 seal at 70 % enrichment** (≈ 200 at 50 %); never more than 240 |
| What breaks it | — | a registration-failure rate above **≈ 2–3 %**, or strong patient clustering. Either leaves even 240 under 0.80 power; the lead is told before grading (§5.4) |
| Reader time | none | ≈ 190 × 2 CMR reads + adjudication + a registration check per patient (to be replaced by measured time, JA58) |
| Committed compute | ≈ 15 GPU-h | the same + ≈ 3 GPU-h once the cohort exists; scar on CPU |
| Main risk | flags with no measured sensitivity | the cohort never arrives; non-rigid misalignment (still ≈ 1.6 mm on the benchmark) raising the failure rate on real data; a Kim bin no better than the readers |
| If the cohort never arrives | — | path B reduces to path A exactly. Nothing further can be learned on synthetic LIE; Round 4 is the last benchmark round this path needs |

---

## 8. Code that must ship (`role:swe` specs, for the judge to adopt or amend; nothing in `src/` was changed)

- **PS4-G1 — E-D column minimum** (`scar0.JA30Constants.column_min_bins`).
  - **Wrong:** 6, against the benchmark's 4, so `module_parity` fails on real hearts (E-D max 0.19).
  - **Correct:** 4.
  - **Test:** `module_parity.py` on the 20 hearts passes (it does at 4: `parity_ed_cause.json`). Add a CI phantom
    with a wall thin enough to make 4- and 5-bin columns.
- **PS4-G2 — `seal_size` Monte-Carlo stability.**
  - **Correct:** default `sims ≥ 1 000`. Log the interpolated N80 and its ±2 SE band beside the grid N80
    (`power_r4_table.py`'s method).
  - **Test:** two seeds on the same inputs give seals within one grid step.
- **PS4-G3 — Stated power at the returned size** (JA57).
  - **Correct:** `seal_size` returns `power_at_seal`, plus `underpowered = power_at_seal < 0.80`.
  - `scoring` / the development report puts it in front of the lead before seal grading.
  - **Test:** strong clustering at 2 % failure gives `seal = 240, underpowered = True` (E12: power 0.61–0.69).
- **PS4-G4 — The affine rule** (§4.2).
  - **Correct:** `qc_rule_accepts` becomes "normalised max does not rise, and (affine passes QC or |log det| ≥
    0.02)". `affine_accepted` passes the log det.
  - Fix the PS3-S3 test's sign (`abs(log_det) > 0.03`) and turn the xfail into a pass.
  - Rewrite the unit test's "one normalised value rises" case, which the new rule keeps by design.
  - **Test:** the existing "affine that increases TRE is rejected" still passes (it does under (g): E11c).
- **PS4-G5 — Provisional QC cuts from registered cases.**
  - **Correct:** `load_provisional_qc_cuts` reads `bench_lie/scores_v3.json` `qc_cuts_registered`, which is p95 over
    4 mm rigid results with TRE < 1 mm on matched motions. It sets `max_rim_dark_phase` from
    `rim_dark_phase_cuts_ja53` instead of leaving it `None`.
  - **Test:** on the benchmark's rigid-motion phantom case, rigid passes QC with these cuts.
- **PS4-G6 — The phase-unmatched stratum** (§6.2).
  - **Correct:**
    - `PHASE_SUSPECT` is in `FINAL_STATUSES`;
    - `for_scoring` gives such a patient the `phase_unmatched` stratum and a `phase_route` of `flag_only` or
      `confirmed`;
    - `scoring.score` counts `flag_only` patients in the yield numerator and denominator;
    - JA52's primary flag is the edge offset; `rim_dark` alone needs the reader's confirmation.
  - **Test:** a hand-built study with one flag-only and one confirmed phase patient: both leave primary accuracy;
    only the first moves yield.

---

## 9. Compute, and the record

- **Compute.** CPU only, on this session's 4 cores:
  - the benchmark: ≈ 10.5 h wall, 518 cases;
  - module parity: ≈ 25 min;
  - power E12 / E12b: ≈ 70 / 30 min.

  No Fir, SciNet or Alliance job.
- **Hearts.** 23 public TotalSegmentator v2.0.1 cardiac CTs and the phantom, guard first. Three are skipped (no LV
  contrast), as in v2. No held-out case, no twin list, no image committed; JSON holds per-segment numbers only.
- **For the record:**
  - JA54's P-G reinstatement holds on the shipped chain (§3.1).
  - Round 3 §1.1's "4 mm + `rim_dark`" arm had no affine stage. v3's shipped chain does, and that stage is where the
    literal 4(b) fails (§4).
  - The provisional cuts that `load_provisional_qc_cuts` reads come from v2's R0-aligned values. On v3 they gate
    nothing (§3.2). On real development patients JA53's p95 over reader-passed patients replaces them anyway; until
    then, PS4-G5.
