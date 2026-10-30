---
aliases: [Janus-M Round 2 paired-scar]
tags: [janus-m, plans, judgement, round2, path-paired-scar, myocardium, scar, lie, lge]
author: Janus-M Round 2 judge (path jm/paired-scar)
round: 2
path: jm/paired-scar
status: ruling
updated: 2026-10-30
issue: christianGRogers/Asclepius#143
---

# Janus-M Round 2, path `jm/paired-scar`: the judgement

**Ruling in one paragraph.** Path B keeps the Round 1 structure (four learned borders, computed layers,
Janus-M 0 = `heartchambers_highres` + geometry) and adds a scar grade that is **computed inside class 1 on the
same-session late-iodine (LIE) scan, never learned as a class**, and scored per AHA segment against CMR LGE on a
paired cohort that exists here only as data requirements (D31).
- **Base: [[Kilo v2]].** It fixes the endpoints best: presence first, then transmurality agreement among scarred
  segments, measured against the LGE readers' own disagreement. It also shows (E6) that weighted κ over all
  segments cannot size or decide the study.
- **Amended by JA25–JA36**, which take:
  - from [[Juliet v2]]: the cohort tiers, the phase-match and shared-frame-of-reference requirements, the QC-first
    registration order with a heart mask, the presence cut learned from LGE-negative segments, and two LGE readers
    on every patient;
  - from [[Golf v2]]: the affine stage, the core-presence rule as a candidate, the 80-patient floor for any claim,
    a CPU segment-level Scar-1, and the culprit-vessel territory check.
- **Stage A on this path is path A's** (JA15–JA24 of `Round 2 - rest-ccta.md`, imported by reference in JA25). Path B
  adds what path A cannot do: it scores those same Stage A flags against LGE.
- **The three scar rules were each tested on a different synthetic LIE**, as the Round 1 border simulations were.
  So the development set chooses the rule from a pre-registered menu, by a fixed criterion, and Round 3 builds one
  shared LIE benchmark (§7).
- **No fork** (§6).

Rules kept: the judge ran no experiment, opened no image, downloaded no data and read no held-out case. The checks
below read committed JSON, committed code and configs, issue #143, the sibling ruling on `jm/rest-ccta` (read-only),
and public bibliographic records (Europe PMC abstracts, Crossref). Twin and held-out lists were compared by
membership and count only; no list is reproduced here.

---

## 1. What was checked, for all three

### 1.1 Key numbers against committed JSON: all match

| Advocate | Claim | File | Match |
|---|---|---|---|
| Kilo | E5 rigid: endocardial ASSD 0.80 mm (p90 0.91), wall blood share 4 %; R0 2.88 mm | `results_e5_lie_registration.json` | yes |
| Kilo | E5b after rigid: sens 0.83 [0.78, 0.88], spec 0.986 [0.97, 1.00], transmurality agreement 0.70 [0.62, 0.76] | `results_e5b_hybrid.json` | yes (0.830 / 0.986 / 0.696) |
| Kilo | E6: P(sens lb > 0.75) 0.95 at 120, 0.72 at 60 (sd_s 0.13); transmurality agreement 0.73 / 0.63 / 0.52 | `results_e6_power.json` | yes |
| Juliet | E5: pass rate 0.93 at 60 (f_MI 0.5); weak pipeline 0.02–0.05 | `e5_cohort_power.json` | yes (0.927) |
| Juliet | E6: heart-masked MI residual 0.26–0.56 mm; whole-field 5.2 mm at d = 10 | `e6_registration.json` | yes (table values) |
| Golf | E5 typical, affine: ASSD 0.61 mm; rule P 0.87 / 0.84 / 0.75 / 0.99; plain T specificity 0.45 | `lie_reg.json` | yes |
| Golf | E6: power all three 0.80 at 80, 0.89 at 120 (base) | `cohort_power.json` | yes |

### 1.2 The PM's points, verified

**(1) Registration: different methods and tolerances.** True, and the reason is the same as in Round 1: **each
advocate built a different synthetic late scan**, so the numbers do not transfer between them.

| | Kilo E5 | Juliet E6 | Golf E5 |
|---|---|---|---|
| Hearts | 13 real (TS v1, 1.5 mm masks) | 1 idealised 3-D phantom, 4 seeds | 11 real (TS v2.0.1), 1 mm |
| Blood vs scar on LIE | blood 110 < scar 150 (easy) | 130 vs 150 (C 60), **130 = 130** (C 40) | **blood = scar** (hard) |
| What moves | the **whole image**, incl. chest | **the heart only**; spine, lungs static | the whole image |
| Motion | rigid + 1.5 mm RMS non-rigid | translation + rotation; one 5 % phase case | translation, rotation, **3–6 % scale**, 1–2 mm non-rigid |
| Best method, residual | rigid 0.80 mm (floor set by the non-rigid field) | heart-masked rigid 0.26–0.56 mm | affine 0.61 mm |

- **Kilo's "rigid is enough" and "masking adds nothing"** hold only when the chest moves with the heart, which Kilo
  says. Its 0.78–0.82 mm floor across all methods is the non-rigid field that no rigid or affine transform can
  remove; it is not a registration accuracy.
- **Juliet's whole-field failure** is the only test of a heart that moves against a static chest. Golf already uses
  a heart mask, and Kilo's masked arm (R3) is no worse (0.78 vs 0.80). So the mask costs nothing and protects
  against the case only Juliet tested.
- **Golf's affine gain** comes from the scale term in its motion model; with no scale (Kilo), affine equals rigid.
- **Juliet's phase case is the most important registration result of the round:** a 5 % cavity change halves
  bin accuracy on scarred segments, and neither QC number sees it. It becomes a data requirement (JA27).

**(2) Cohort size: the simulations agree; the bars differ.**

| | Kilo E6 | Juliet E5 | Golf E6 |
|---|---|---|---|
| Scar patients | 70 % | 50 % (+10 % unrecognised in the rest) | 50 % |
| Detection | sens 0.84, spec 0.98 | 0.86 / 0.98 | by bin, pooled 0.84; spec 0.98 |
| Clustering | logit SD 0.8 (ICC of CT-positive 0.03, weak) | logit SD 0.8 | logit SD 0.7 (1.2 as stress) |
| **Sensitivity bar** (lower 95 %) | **0.75** | **0.70** | **0.75** |
| Other bars | none in the power calc (sensitivity only) | κ_w ≥ 0.60, spec ≥ 0.90 | κ_w ≥ 0.60, spec ≥ 0.93 |
| Power target | 95 % | 90 % | 80 % (min), ~90 % (rec.) |
| **Result** | 120 seal + 40 dev | 60 validation + 30 calibration | 120 seal (min 80) + ≥ 40 dev |

- At matched scarred segments the sensitivity CI is the same in all three: ± 0.065 at 136 segments (Kilo) and
  ± 0.068 at 132 (Juliet).
- **Juliet's 60 is a consequence of its 0.70 bar.** Its own mean sensitivity at 60 is 0.836 with half-width 0.068,
  so the lower bound sits near 0.77: it clears 0.70 easily and 0.75 only about two times in three, which is Kilo's
  0.72 and Golf's 0.62 at 60.
- **All three find κ over all segments non-binding**: it passes in ≥ 97 % of Juliet's cohorts at every N, Golf
  calls it "easy", and Kilo shows it barely moves when the grading error grows 2.5-fold (0.86 → 0.80). It cannot
  decide whether the grading works (JA32).
- **All three calibrate to Gatti 2025's pooled reader performance** (0.86 / 0.98). That is what published readers
  achieve, not what any rule in this round achieves on its own phantom (Kilo 0.83; Golf 0.75 at CNR 5, far less at
  CNR 3). The cohort is therefore sized for a pipeline as good as published readers, and **the development set is
  the go/no-go**, not the size.

**(3) Scar rule.** Confirmed as stated. All three agree on the structure, presence first and then the Kim bin, and
differ on each step:

| | Presence | Extent (Kim bin) | Remote |
|---|---|---|---|
| Kilo | FWHM threshold, ≥ 5 % of the segment's voxels | remote + 3 SD, **volume share** | core voxels of 6 darkest segments, median + robust SD |
| Juliet | depth-binned extent T ≥ τ, **τ = p99 of T in LGE-negative development segments**, per protocol | half-way threshold, **depth-binned transmural extent** | darkest segment |
| Golf | **core rule**: ≥ 5 % after opening, ignoring 1 mm at the endocardium | remote + 3 SD, volume share | mid-wall third of 4 darkest segments |

**One finding none of them states.** Golf's core rule has sensitivity **0.69 with exact borders** and **0.75 after
affine registration** (`lie_reg.json`). It does better with registration error than without: the 1 mm exclusion
removes thin bin-1 scars by construction, and the residual outward bias (+0.22 mm) carries blood signal into the
core. **Its 0.75 is partly spill.** That is one more reason the rule must be chosen on real LGE (JA30).

**Which quantity a Kim bin is.** Kilo and Golf grade the scar's volume share of a segment. Juliet grades
depth-binned transmural extent and argues that a volume share reads a 15 % scar as 8 %. Each advocate's phantom uses
its own definition as truth, so each looks right on its own phantom. Kim 2000's abstract speaks of "transmural
extent" and "more than 75 percent of tissue", which fits either reading. **The LGE read form defines it** (JA32), and
the CT measure that agrees best with that read is chosen on development (JA30).

**(4) Held-out handling.**
- **Kilo, s1237.** Confirmed by the notes, #143 (03:26 UTC) and the committed JSON: the re-run's case list does not
  contain it, rates moved ≤ 0.03 and distances ≤ 0.11 mm. s1237 is a twin under the shared rule, not a held-out
  subject, and no coronary quantity was computed. The PM put it on the lead's twin question (LQ9 on `jm/rest-ccta`).
- **Golf, Round 1 cases.** 20 of the 24 ids in `Golf/ts_cases.json` are refused by today's list. Confirmed; none is
  a held-out subject.
- **The guard on this branch now refuses 711** (`configs/janusm/ts-twins-r1.json`: 710 twins ∪ 16 held-out; JA22,
  #171). **Every case used this round passes it:** Kilo E5's 13 (plus the 2 skipped), Golf E5's 12 (s0832 included)
  and Golf E7's 6. The re-pin did not newly refuse any Round 2 input.
- **One stale record.** `Kilo/results_e4_twins.json` lists 18 "open" cardiac ids, 3 of which (s1237 among them) the
  shared guard refuses. It is a record of Kilo's v1-only rule, not an allow-list, and JA22 already forbids reusing
  Round 1 or 2 case lists without the guard. No change is needed beyond JA36's note.
- **Held-out names in committed text.** No committed file on this branch contains held-out data. Several notes name
  held-out s-numbers in prose, as the Round 1 ruling did. Kilo's notes also name the held-out subject a twin was
  matched to. That pairing reveals that the two share sex and institute and are within 5 years of age. These are
  public metadata, but from now on notes say "a twin" without naming the held-out partner (JA36).
- **Juliet** opened no case (all synthetic). Its `guard_r2.gate()` runs first, and its output scan found 0 ids.
- **Golf s0832** (#176): its E5 numbers already include it (`lie_reg.json` note "11 of 12"; the 12th passes the
  guard). No conclusion here depends on it.

**(5) The asks for the lead,** merged in §5:
- Kilo PB1–PB4;
- Juliet PB-Q1–Q4;
- Golf PB-Q1–Q5. Golf's PB-Q1 is LQ1 itself, and its PB-Q5 is answered by JA22 on the trunk; neither is re-asked.
- **Juliet's `fir/edges_m0.py`.** It computes the endocardial and epicardial half-maximum offsets, with the same sign
  convention (positive = the label's myocardium reaches past the image edge), on the same inputs as JM-0R
  (`experiments/JanusM/fir/jm0r_readout.py` on `jm/rest-ccta`). JM-0R already computes both quantities. Unlike
  JM-0R, **`edges_m0.py` calls no JA12 guard and checks neither the frozen JM-0 list nor the `splits.json` hash.**
  It folds into JM-0R and is not run (JA34, LQ18).

### 1.3 Citations (24 resolved; abstracts read at Europe PMC, bibliographic records at Crossref)

All 24 exist and their bibliographic details match: Gatti 2025, Ibrahim 2010, Gerber 2006, Bettencourt 2013, Ohta
2018, Palmisano 2020, Palmisano 2022, Klambauer 2026, Hamdy 2019, Engblom 2009, Pokorney 2012, Ingkanisorn 2004,
Wang 2011, Mahnken 2005, Schelbert 2012, Amado 2004, van Assen 2020, Dixon 2016, Liu 1993, Kim 2000, Nacif 2012,
Mattes 2003, Lowekamp 2013, Maes 1997.

**Numbers confirmed against the abstracts:**
- **Gatti 2025:** 14 studies, 526 patients, 5758 segments; segment sensitivity 0.86 (0.79–0.91), specificity 0.98
  (0.96–0.99); patient-level 0.96 / 0.95; dual-energy 0.93. ✓
- **Ibrahim 2010:** 18.3 → 12.9 → 11.3 → 11.6 % (days 1, 7, 35, 180), 17 patients. ✓
- **Gerber 2006:** late hyperenhancement 82 %, κ 0.61; 16 acute + 21 chronic patients. ✓
- **Bettencourt 2013:** low-dose delayed enhancement, sensitivity 53 %, specificity 98 %. ✓
- **Ohta 2018:** iodine-density images 92 % (195/213) and 98 % (481/491). ✓
- **Palmisano 2020:** per-segment sensitivity 85 % vs 62 %; missed scars non-ischaemic, burden < 6 %. ✓
- **Hamdy 2019:** CNR 6.4 ± 2.5 at 7 min, 6.1 ± 2.2 at 5 min (n.s.); 5 min recommended. ✓
- **Engblom 2009:** 64 % of the one-year reduction in the first week. ✓
- **Pokorney 2012:** 32 % fall to 4 months, a further 12 % between 4 and 14 months. ✓
- **Ingkanisorn 2004:** acute 16 ± 12 → 11 ± 9 %; chronic 11 ± 4 vs 12 ± 7 %. ✓
- **Wang 2011:** κ 0.85; 0.82 transmural, 0.52 subendocardial; 11 patients. ✓
- **Mahnken 2005:** κ 0.878, 28 patients. ✓
- **Schelbert 2012:** unrecognised MI in 17 % of 936, aged 67–93. ✓
- **Amado 2004:** canine, FWHM r² 0.94. ✓
- **Liu 1993:** diaphragm range 8.3 mm without feedback, 1.3 mm with. ✓
- **Nacif 2012:** CT vs MR ECV r 0.82, 24 subjects. ✓

**Context errors (the numbers are right; the population or the comparison is narrower than stated):**
- **Kilo, Palmisano 2020.** Kilo E5 writes "detected scars 3.54, missed 2.33". The abstract compares missed scars
  (2.33) with **ischaemic** scars (3.54), not with detected ones.
- **Kilo, Ohta 2018** is a **heart-failure** cohort, half with non-ischaemic LGE, scored for "any" delayed
  enhancement. It is not a post-MI population.
- **Kilo, Klambauer 2026** is 17 patients with **spontaneous coronary artery dissection**, mostly acute. It is
  correctly cited for a 5-min late scan, but no accuracy figure transfers.
- **Kilo, Dixon 2016** gives a design-effect method for clusters of **two** (twins, paired organs). It is not a
  method for 17 segments per patient. Kilo's patient bootstrap is what is actually used, and it is correct.
- **Kilo, Ibrahim 2010** "stable from day 7 to day 180". The abstract reports 12.9 → 11.3 % between days 7 and 35,
  with "all P < .001", and calls the later changes "minor". It supports a ≥ 7-day floor, not stability. Pokorney
  2012 (Juliet) shows a further 12 % fall between 4 and 14 months. This weakens Kilo's ≥ 30-day floor (JA27).
- **Golf, Ingkanisorn 2004.** The abstract gives no follow-up interval, so it supports "chronic infarct size is
  reproducible" but not the 90-day number. Juliet's Ibrahim + Engblom + Pokorney set does support it.
- **Palmisano 2022** (Kilo) is troponin-positive acute chest pain, mostly myocarditis. It is cited correctly, for a
  10-min late scan only.

**Not verifiable from the abstract:**
- van Assen 2020's "5–15 min". The abstract is a review summary; Juliet cites the open full text.
- Kim 2000's segment-scoring definition (the abstract does not settle area versus depth, §1.2 (3)).

---

## 2. Scorecards

Scale 1–5, as in Round 1:
- **(a)** reasoning;
- **(b)** evidence;
- **(c)** fit to path B and to data the project could obtain;
- **(d)** risk and cost (5 = low risk, cheap).

### Kilo v2: grade the scar inside the borders Janus-M already draws, and size the proof on sensitivity

| | Score | Why |
|---|---|---|
| (a) Reasoning | **5** | The best statistical argument of the round: weighted κ over all segments is dominated by agreeing scar-free segments, so it can neither size nor decide the study (E6). Transmurality agreement among scarred segments, held against the LGE readers' own agreement, mirrors JA8 and is the right primary. The two-threshold rule is explained by mechanism (3 SD calls blood spill; FWHM under-reads extent). Registration failures count against the pipeline. Thinning is tested against transmural scar, not any scar |
| (b) Evidence | **4** | 13 real hearts, an oracle arm that isolates the rule's own error, bootstrap CIs; every number matches. Deducted: the easy LIE (blood darker than scar; chest moves with the heart, so masking cannot show a benefit; both disclosed); the s1237 opening (a twin, not a held-out patient; disclosed promptly and re-run); four context slips (§1.3) |
| (c) Fit | **4** | The most complete cohort specification, written cleanly as requirements. But every patient needs same-session LIE (no CCTA + LGE tier), and S1 needs ≥ 60 further paired patients |
| (d) Risk / cost | **4** | ≈ 3 GPU-h committed, only once data exists; S1 ≈ 55 GPU-h conditional. One LGE reader on the seal is cheap but weakens the reference |

### Juliet v2: one border model, two scans, and a paired cohort that can prove the scar map

| | Score | Why |
|---|---|---|
| (a) Reasoning | **4** | The tiers let the plan degrade gracefully (T1 = CCTA + LGE validates Stage A without any LIE). The QC-first order keeps an aligned scan instead of moving it. Phase match is made a data requirement, with evidence that no QC sees a mismatch. τ is learned from LGE-negative segments per protocol. LGE is never used as a voxel label. Deducted: the size follows from a lenient 0.70 sensitivity bar, and quadratic κ over all segments is kept as an endpoint although its own E5 shows it never binds |
| (b) Evidence | **3** | Every number matches and every citation checked is correct, with unverified items named. But all of it is one idealised phantom (rigid heart, homogeneous tissue, 1 mm grid, 16 scarred segments per condition, 4 seeds), and no real anatomy was used this round. Its whole-field failure and its phase case are nonetheless the two results no one else produced. `edges_m0.py` lacks the JA12 guard |
| (c) Fit | **5** | The best match to obtainable data: T1 without LIE, a shared frame of reference, recorded phases, per-protocol τ, and a 90-patient minimum |
| (d) Risk / cost | **4** | Cheapest cohort, CPU only. Risk: at the adopted 0.75 bar its 60 validation patients have about 0.7 power. The learned head's 20–30 GPU-h is unsourced |

### Golf v2: borders from the first pass, scar from the late scan, truth from LGE

| | Score | Why |
|---|---|---|
| (a) Reasoning | **4** | Plans for Scar-0 to fail instead of hoping. Scar-1 is a segment-level model trained on the reference itself (development LGE), with no voxel labels and no GPU. The 80-patient floor for any seal claim. The culprit vessel as the only territory reference in the project. Deducted: §4.5's margin clip(0.5 r̃, 0.15, 0.35) loosens with noisy reads, the flaw `jm/rest-ccta` rejected (JA16); the core rule's sensitivity is partly spill (§1.2) and this is not noticed; the phase match is "where the protocol allows" |
| (b) Evidence | **4** | 11 (12) real hearts, the hard bright-blood case, four registration methods, a half-split τ, two CNRs; E7 independently reproduces the harness `jm/rest-ccta` adopted (JA15); E4 matches the shared guard id for id. Numbers match. Deducted: assumed misalignment levels; Ingkanisorn cited for a number its abstract lacks |
| (c) Fit | **4** | ~160 patients, all with LIE. Most of §4 (Stage A margins, TPR, fat) is superseded by path A's JA16–JA18 |
| (d) Risk / cost | **5** | ≈ 3 GPU-h committed; Scar-0 and Scar-1 both CPU; the cheapest conditional route |

**Totals (of 20):** Kilo 17, Golf 17, Juliet 16.

**Kilo is the base, on the tie-break.** What path B must fix before any paired patient exists is **what counts as
proof**: the endpoints, the bars and the size. Kilo's answer is the most complete and the most conservative, and its
E6 is the reason the round can drop κ as a deciding endpoint. Golf's cheaper conditional route and harder test case,
and Juliet's data requirements and registration order, enter as amendments.

---

## 3. Rulings where they disagree

| Item | Kilo | Juliet | Golf | **Ruling** |
|---|---|---|---|---|
| Stage A | trunk, unchanged | trunk, + `edges_m0` | trunk + own margins, TPR, fat | **path A's JA15–JA24 by reference** (JA25) |
| Cohort tiers | LIE + LGE for all | T1 / T2 / T3 | LIE + LGE for all; CTP optional | **T2 primary; T1 accepted for Stage A only; T3 report-only** (JA27) |
| Infarct age | ≥ 30 days | ≥ 90 days | ≥ 90 days | **≥ 90 days for the primary; acute stratum report-only** (JA27, LQ15) |
| Phase match | same gating and phase | ≤ 5 % R-R or reconstructable | where the protocol allows | **recorded always; matched within 5 % R-R for the seal** (JA27) |
| Size | 120 + 40 dev | 60 + 30 calibration | 120 (min 80) + ≥ 40 dev | **seal ≥ 120 and ≥ 270 scarred segments; no claim below 80; dev 40** (JA28) |
| Registration | rigid MI, heart crop | R0 → QC → heart-masked rigid MI | scanner coords → masked rigid → affine | **R0 → QC → heart-masked rigid → affine; no B-spline** (JA29) |
| Presence | FWHM ≥ 5 % voxels | T ≥ τ from LGE-negative | core rule | **pre-registered menu, chosen once on development** (JA30) |
| Extent | 3 SD volume share | depth-binned extent | 3 SD volume share | **menu of two, chosen on development against the LGE read** (JA30) |
| Learned step | nnU-Net voxel head; +60 patients | voxel head, 20–30 GPU-h | segment-profile ordinal model, CPU | **Golf's CPU Scar-1 first; voxel head only if that fails, with more patients** (JA31) |
| LGE reads | 2 on dev, 1 on seal | 2 + adjudication, all | 2 + consensus, all | **2 + adjudication on every patient** (JA32, LQ16) |
| Endpoints | sens ≥ 0.75, spec ≥ 0.95, transmurality vs readers − 0.10 | κ_w ≥ 0.60, sens ≥ 0.70, spec ≥ 0.90 | sens ≥ 0.75, spec ≥ 0.93, κ_w ≥ 0.60 | **sens ≥ 0.75, spec ≥ 0.93, transmurality vs readers − 0.10; κ reported** (JA32) |
| Stage A vs LGE | AUC; thinning vs Kim ≥ 3 | AUC lb > 0.70 / drop if CI covers 0.5 | AUC lb ≥ 0.70 | **path A's own flags scored; Kilo's targets, Juliet's two-sided rule** (JA33) |
| JM-0 add-on | none | `edges_m0.py` | geometry function | **JM-0R, run once for both paths** (JA34) |

**Why these bars.** Each sits about 0.03–0.04 below the lower limit of Gatti 2025's pooled 95 % CI (sensitivity
0.79 → 0.75; specificity 0.96 → 0.93). That is one consistent rule, and it accepts a pipeline that reads LIE about as
well as published readers. Juliet's 0.70 / 0.90 would accept a pipeline worse than the published lower limits. Kilo's
specificity of 0.95 sits only 0.01 below the pooled limit and buys nothing: specificity passes at every N in all
three simulations.

---

## 4. Binding amendments (JA25–JA36; path `jm/paired-scar`)

- **JA25 — Stage A on this path is path A's.**
  - `Round 2 - rest-ccta.md` **JA15–JA24 apply here as written**: the error model and units (JA15), the final
    margins and E8 re-powering (JA16), rest TPR (JA17), the calibrated signs (JA18), Tables A and B (JA19), depth,
    sectors and territories (JA20), border protocol v1 (JA21), the twin rule (JA22), JM-0R (JA23) and the citation
    record (JA24).
  - Superseded on this path: Golf v2 §4.5 (margins that loosen with noisy reads), §4.6 (TPR window 1.00–1.18 and
    the 0.1st-percentile fat cut) and Juliet's seed shift on a measured epicardial bias. These are replaced by JA16,
    JA17 and JA18 respectively.
  - **Shared code.** The JA15 harness, JM-0R and the table writer are trunk-shaped work built on `jm/rest-ccta`.
    The PM moves them to `dev` (or merges them into this path) through `role:swe` PRs, so both paths run one
    implementation. Golf E7 (`Golf/harness.py`) is an independent reproduction of JA15's model and is kept as a test
    reference, not as a second implementation.
  - **What path B adds to Stage A:** the LGE validation of JA33. Nothing else changes.
- **JA26 — Scar is computed inside class 1, never learned as a class.**
  - JA1 is unchanged: four learned classes. Scar is a per-voxel call inside the **registered** class 1 on the LIE
    grid, aggregated per AHA segment 1–17.
  - **Outputs per segment:** presence; Kim bin (0 / 1–25 / 26–50 / 51–75 / 76–100 %); scar share; deepest depth u
    reached (JA2); territory (JA4/JA20). Per territory: the share of its segments scar-present.
  - **Labels:**
    - every scar output is "research output, not validated" until JA32 passes on the paired seal;
    - every output also carries the patient's registration status (passed, re-registered, not graded).
  - **LGE is never a voxel label.** It is a different scan, modality and time, and its role is the per-segment
    reference (Juliet, Golf).
- **JA27 — The paired cohort: data requirements only (D31).** No text addressed to anyone outside the project, here
  or anywhere in the repository. Whether and how such data is obtained is the lead's (D19).
  - **Tiers** (a patient may be in more than one):
    - **T2 (primary):** first-pass CCTA + same-session LIE + CMR LGE. It validates the scar grade and the Stage A
      signs.
    - **T1:** first-pass CCTA + CMR LGE, no LIE. It validates the Stage A signs only (JA33).
    - **T3:** stress CTP + invasive FFR. Report-only and not sized.
  - **Population:**
    - adults;
    - known or suspected CAD;
    - enriched for prior MI (target 50–70 % with LGE scar), with **≥ 30 % of patients LGE-negative**;
    - new to the project, and the de-identified manifest passes the JA12 guard by patient before any image is opened.
  - **Strata, never pooled into the primary:**
    - **acute:** index MI < 90 days before either scan;
    - **non-ischaemic LGE pattern** (mid-wall, epicardial, patchy);
    - **phase-unmatched** (below);
    - prior CABG, which is kept for scar but left out of territory analyses.
  - **Exclusions:** a device or metal artefact over the LV on either modality; any MI, PCI, CABG or cardiac surgery
    between the CT and the CMR.
  - **First-pass CCTA:** ECG-gated; slice ≤ 0.75 mm; reconstruction phase (% R-R), kV, kernel and vendor recorded.
  - **LIE:**
    - same session and same injection as the CCTA, 5–10 min after contrast, slice ≤ 1.0 mm;
    - ECG-gated, with the gating phase recorded;
    - delay, kV or energy mode, dose and kernel recorded;
    - dual-energy or photon-counting with iodine or low-keV maps preferred and recorded; single-energy accepted
      (LQ14);
    - **original DICOM geometry kept:** `FrameOfReferenceUID`, `ImagePositionPatient`, `ImageOrientationPatient`,
      table position, acquisition time.
  - **Phase match (Juliet E6).**
    - The phase of both scans is recorded in every case.
    - **Seal and development patients** must have the LIE within 5 % R-R of a CCTA reconstruction, or CCTA raw data
      that allow a reconstruction at the LIE's phase.
    - Others form the phase-unmatched stratum.
  - **CMR:**
    - within **90 days** of the CT, either order;
    - LGE short-axis stack from base to apex, plus long-axis views;
    - PSIR preferred; field strength, sequence and delay recorded;
    - cine optional.
  - **Infarct age:** ≥ 90 days before both scans for the primary analysis (LQ15).
  - **Per-patient fields:** offsets in days only (index MI, CT–CMR), never dates; age band; sex; scanner and protocol
    fields; heart rate at each acquisition; culprit or revascularised vessel if known; haematocrit if ECV is wanted.
  - **Form:**
    - de-identified before arrival, with no burned-in text;
    - kept only in a restricted collection on the project's Girder;
    - never committed;
    - no name, date, accession number or other identifier in the repository, an issue or a PR.
  - **T3:** FFR within 90 days of the CTP with no intervening revascularisation of that vessel; stressor, timing and
    beam-hardening correction recorded.
- **JA28 — Size, split and re-powering.**
  - **Development: 40 T2 patients**, ≥ 25 with prior MI. Used once each for:
    - registration QC cuts;
    - the JA30 rule choice;
    - the LGE inter-reader agreement;
    - re-powering;
    - Scar-1 if it is triggered.
  - **Paired seal: ≥ 120 T2 patients and ≥ 270 ischaemic-pattern LGE-scarred segments**, whichever needs more
    patients. At 50 % enrichment that may mean about 135 patients.
    - **Below 80 there is no seal claim** (Golf): the cohort is development-only and every scar output stays
      research.
  - **Split, by batch-stable salted hash.**
    - A patient is development if `int(sha256('asclepius-janusm-paired-r2:' + pseudonym)[:8], 16) / 2**32 < 0.25`,
      and seal otherwise.
    - Assignment is fixed at intake, before any image of that patient is opened, so later batches do not reshuffle
      earlier ones.
    - The development target is 40; the cut 0.25 is re-stated in the freeze if the expected total differs.
    - The lists are frozen in `configs/janusm/paired-r2.json` (sha256-pinned; a `role:swe` PR) before any LIE of a
      seal patient is graded.
    - The JA12 guard refuses seal patients in every development step.
  - **Re-powering, once, on development, before any seal patient is graded.**
    - Measure the patient clustering, the scarred segments per patient, sensitivity, and the LGE inter-reader
      agreement.
    - Re-run the merged power script (JA35 item 4) for the JA32 endpoints.
    - The seal may only grow, at ≥ 80 % power for all three JA32 endpoints jointly.
    - It is scored once.
- **JA29 — LIE-to-CCTA registration.**
  - **Direction:** the first-pass CT is moving, the LIE is fixed. Grading happens on the LIE grid, so LIE noise is
    never resampled (Golf).
  - **Carried:** myocardium and cavity through their signed distances; segments and depth u by nearest neighbour.
  - **Chain, stopping at the first stage that passes QC (Juliet's order):**
    1. **R0, scanner coordinates** through the shared frame of reference.
    2. **QC:** the fat-like and blood-like shares of the carried wall on the smoothed LIE (Juliet), plus the share
       of the wall brighter than the LIE blood median (Kilo). The cuts are set on development.
    3. If QC fails, **Mattes MI rigid, with the metric masked to classes 1–4 dilated 10 mm**.
    4. Then **affine with the same mask**. It is kept only if it lowers the QC values against rigid.
  - **B-spline is not in the pipeline.** Kilo and Golf found no gain at typical motion; Juliet warns it would
    deform the scar. It is a development arm only if the failure rate exceeds 10 %.
  - **Reader check, every patient:**
    - pass or fail on three short-axis slices (basal, mid, apical), with the carried borders over the LIE and the
      first-pass scan side by side;
    - blind to LGE;
    - a fail is re-registered once from a manual initial shift.
  - **A second fail is "not graded".** In the primary analysis a not-graded segment counts as wrong: a miss if
    LGE-positive, a false call if LGE-negative. Graded-only results are reported beside them.
  - **A failure rate > 10 % on development** stops seal grading until the method is revised on development.
  - **Logged per patient:** the registration's estimated shift. This replaces every assumed breath-hold
    displacement in this round.
- **JA30 — Scar-0: a rule, no training, chosen once on development from a pre-registered menu.**
  - **Common steps:**
    - smooth the registered LIE (Gaussian FWHM 1.5 mm);
    - **remote** = the core voxels (≥ 1 voxel inside both carried borders) of the 6 lowest-median segments, with
      median and robust SD (1.4826 × MAD) (Kilo, with the mid-wall idea of Golf).
  - **Presence candidates:**
    - **P-K:** ≥ 5 % of the segment's voxels above remote + ½ (p99 of the brightest segment's core − remote)
      (Kilo);
    - **P-J:** extent T ≥ τ, with τ the p99 of T over LGE-negative development segments, per scanner protocol when
      a protocol has ≥ 15 development patients, pooled otherwise (Juliet);
    - **P-G:** ≥ 5 % above remote + 3 SD after a 1-voxel opening, ignoring 1 mm at the carried endocardium (Golf).
  - **Extent candidates:**
    - **E-V:** the share of the segment's voxels above remote + 3 SD (Kilo, Golf);
    - **E-D:** depth-binned transmural extent, from 10 bins of u per 3° × 2 mm column, averaged over the segment
      (Juliet).
  - **Choice, on development, against the double LGE read:**
    - **presence:** the candidate with the highest segment sensitivity among those whose specificity lower bound is
      ≥ 0.95 (cluster bootstrap); ties go to the earlier in the list;
    - **extent:** the candidate with the higher transmurality agreement among scar-on-both segments;
    - a present segment reads at least bin 1.
  - **Fixed once.** The constants above are fixed now. Development may change only the choice and τ. The choice is
    recorded with its development numbers in the freeze PR, before any seal grading.
  - **Round 3** narrows the menu on one shared LIE benchmark (§7 item 1). A candidate that fails there is struck
    before development.
- **JA31 — Learned steps, conditional and in order.**
  - **Trigger:** Scar-0's development point estimates miss a JA32 bar, or its sensitivity lower bound is < 0.70, with
    registration QC passing.
  - **Scar-1 (Golf), CPU:**
    - **inputs:** the per-segment LIE profile over 10 depth bins, normalised (LIE − remote) / (blood − remote),
      plus thickness and a local registration residual;
    - **model:** ordinal logistic over the 5 Kim classes;
    - **training:** on development LGE labels with patient-grouped 5-fold CV; never fitted on the seal.
    - It replaces Scar-0 only if its grouped-CV point estimates clear every JA32 bar and beat Scar-0 on sensitivity.
    - Development is then spent, so the re-powering (JA28) uses the pre-Scar-1 numbers.
  - **Voxel head (Kilo S1 / Juliet), only if Scar-1 also fails:**
    - one nested value "scar ⊂ class 1", loss computed only inside the registered wall;
    - inputs: LIE, CCTA, class-1 mask, depth u, and the iodine or low-keV map where present;
    - nnU-Net v2 `3d_fullres`, mirroring off;
    - **≈ 55 GPU-h** (icx4's measured rate; Juliet's 20–30 is unsourced);
    - trained on reader-drawn LIE masks (drawn with LGE shown) from **≥ 60 further T2 patients that are never seal
      patients** (a new data requirement);
    - scored like Scar-0, against LGE segment reads.
- **JA32 — The scar reference and the acceptance rule (paired seal, one look).**
  - **LGE reads:**
    - read fresh from images, never from clinical reports;
    - **two CMR readers per patient, independently, blind to every CT**;
    - per segment 1–17: presence; pattern (ischaemic: subendocardial or transmural; non-ischaemic: mid-wall,
      epicardial or patchy); Kim bin;
    - adjudication by a third reader on any presence disagreement or a difference of ≥ 2 bins.
  - **The read form defines a Kim bin** as the reader's estimate of the hyperenhanced share of the segment's
    myocardium (Kim 2000's "percent of tissue"), with an example panel. The development set then picks the CT extent
    measure that matches it (JA30).
  - **Primary endpoints:**
    - ischaemic-pattern segments of the seal;
    - intention-to-diagnose (JA29);
    - 95 % patient-cluster bootstrap, lower bounds.

    | Endpoint | Bar |
    |---|---|
    | Segment sensitivity for presence | ≥ **0.75** |
    | Segment specificity | ≥ **0.93** |
    | Transmurality agreement (Kim bin, scar-on-both segments) | ≥ the development LGE inter-reader agreement on the same statistic **− 0.10** |

  - **If the development inter-reader agreement is < 0.60,** the third endpoint is reported only and the decision rests
    on presence (Kilo, Golf).
  - **Reported, never deciding:**
    - linear- and quadratic-weighted κ over all segments;
    - patient-level sensitivity and specificity;
    - Bland–Altman of scar share;
    - per-territory and per-protocol results;
    - the not-graded rate;
    - the graded-only analysis;
    - every stratum of JA27.
  - **Margins** are fixed by this ruling and are not re-set on development, as JA16 does for borders. Development sets
    only the reader-agreement anchor.
  - **What passing gives:** scar presence and bin lose "not validated" for scanners and protocols like the seal's.
    Nothing else does.
- **JA33 — Stage A signs and territories against LGE.**
  - **What is scored:** the flags path A ships (JA18): the per-territory thinning flag, subendocardial
    hypoattenuation and fat, the composite, and per-segment values. They are computed on the paired first-pass CCTA
    by the same code, with the cohort's recorded phase. Path B validates path A's table, not a variant of it.
  - **Targets, per segment and per territory, against LGE:**
    - thinning against **transmural scar (Kim ≥ 3)** (Kilo);
    - hypoattenuation, fat and the composite against any ischaemic scar;
    - rest TPR (only if JA17 lets it into the table) against any ischaemic scar.
  - **Analysis:**
    - AUC with a patient-cluster bootstrap;
    - sensitivity and specificity at the JA18 cut, with any change to the cut made on development only;
    - T1 and T2 patients both count.
  - **Labels:**
    - a sign loses "not validated" for such populations if its seal AUC lower bound is ≥ 0.70;
    - it is **dropped from the table** if its CI covers 0.5 (Juliet).
  - **Territories:** for each LGE-positive ischaemic patient with a recorded culprit vessel, the share of scarred
    segments inside that vessel's territory is compared between Euclidean and geodesic assignment (paired bootstrap
    over patients). **On this path that comparison replaces JA20's ≥ 10 % disagreement rule** for choosing the
    primary method (Golf, Juliet).
- **JA34 — Compute and Fir.**
  - **No new Fir command this round.** Paired data does not exist.
  - **Committed on this path beyond the trunk and JA25:** PB-0, Janus-M 0 seeds and geometry on the cohort's
    first-pass CCTA, ≈ 3 GPU-h, written as exact commands only once the frozen manifest and its Girder layout exist.
  - **CPU:** registration and Scar-0, and Scar-1 if triggered.
  - **Conditional:** the voxel head, ≈ 55 GPU-h.
  - **JM-0R.** Path B takes its JM-0 add-on from JM-0R (JA23), run once, with the summary posted on #142 **and**
    #143. Juliet's `fir/edges_m0.py` is not run: JM-0R computes the same offsets, under the guard.
- **JA35 — Code that must ship (`role:swe`, labelled `jm/paired-scar`, opened by the PM).**
  1. **The LIE registration module** (JA29): the chain, QC and logging, with Juliet E6's static-chest phantom and
     Kilo E5's case as tests.
  2. **The Scar-0 module** (JA30): every menu candidate, on the shared geometry module.
  3. **Cohort intake and freeze** (JA27, JA28):
     - hash the keys;
     - run the JA12 guard;
     - check the JA27 fields and windows from DICOM headers and day offsets;
     - assign by the JA28 hash;
     - write `configs/janusm/paired-r2.json`.
  4. **One power script** for the JA32 endpoints: Golf's patient-clustered study, with Kilo's transmurality endpoint
     and its reader-anchored bar. It replaces the three.
  5. **The LGE segment read form** in the Janus-M read queue (JA32) and the registration pass/fail form (JA29).
  6. **The scoring harness:** cluster bootstrap, intention-to-diagnose, strata.
  7. (Conditional) the Scar-1 fitter and the voxel-head dataset builder.

  Items 1, 2, 4 and 6 can be built and tested on phantoms now. Items 3 and 5 wait until the lead pursues the cohort.
- **JA36 — Record and citations.** Round 1's JA14 and path A's JA24 stand. Added:
  - Palmisano 2020's 3.54 is the CNR of ischaemic scars, not of detected scars;
  - Ohta 2018 is a heart-failure cohort, half non-ischaemic;
  - Klambauer 2026 is SCAD;
  - Dixon 2016 is for clusters of two;
  - Ibrahim 2010 supports a ≥ 7-day floor, not stability to day 180;
  - Ingkanisorn 2004's abstract carries no 90-day figure;
  - Kim 2000's segment-scoring definition is unverified from the abstract.

  **Held-out record:**
  - Kilo opened s1237, a twin under the shared rule and not a held-out patient (re-run without it);
  - Golf's Round 1 E2 used 20 cases now refused as twins;
  - `Kilo/results_e4_twins.json`'s "open" list is a record, not an allow-list.

  **From now on** an experiment note says "a twin" without naming the held-out subject it matches.

---

## 5. Questions for the lead (each with a recommendation; none is a fork)

**Carried unchanged, as assumptions:**
- LQ2–LQ8 (Round 1 §5), each with its Round 1 recommendation. All three candidates assumed the same.
- **LQ9–LQ12** (`Round 2 - rest-ccta.md` §5) bind this path too, because Stage A is path A's (JA25). LQ9 covers
  s1237 and Golf's Round 1 twins, which the PM has already added to it.

**Not re-asked:**
- Golf PB-Q1 is LQ1 itself.
- Golf PB-Q5 (keep the twin rule) is decided by JA22 on the trunk (#171).

### LQ13 — The paired cohort's shape (Juliet PB-Q1, Golf PB-Q2 and PB-Q4, Kilo PB2)

- **Options:**
  - (a) JA27–JA28 as written: T2 primary (40 development + ≥ 120 seal, ≥ 270 scarred segments, no claim below 80);
    T1 accepted for Stage A validation; T3 optional; non-ischaemic, acute and phase-unmatched patients as
    report-only strata;
  - (b) Juliet's smaller T2 (30 + 60) with a 0.70 sensitivity bar;
  - (c) T1 only (no LIE): Stage A validation, no scar grade.
- **Recommendation: (a).** (b) passes a pipeline below the published lower limit. (c) is the fallback this plan
  already contains if no LIE exists (§6).

### LQ14 — Single-energy LIE (Kilo PB1)

- **Options:**
  - (a) accept it, record the energy mode, kV and dose, and stratify;
  - (b) require dual-energy or photon-counting.
- **Recommendation: (a).** The pooled single-energy segment sensitivity (0.86) clears the 0.75 bar, and requiring
  dual-energy narrows the eligible pool. Low-dose protocols (Bettencourt 2013: 0.53) are reported as their own
  stratum.

### LQ15 — Timing windows (Kilo PB4, Juliet PB-Q2)

- **Options:**
  - (a) CT–CMR ≤ 90 days and index MI ≥ 90 days before both scans;
  - (b) MI ≥ 30 days (Kilo);
  - (c) CT–CMR ≤ 180 days if the cohort is too small.
- **Recommendation: (a)**, with (c) only as a pre-stated fallback, reported as a stratum. Infarct size keeps falling
  after day 30 (Ibrahim 2010; Pokorney 2012: a further 12 % between 4 and 14 months).

### LQ16 — LGE reader time (Kilo PB3, Juliet PB-Q4, Golf PB-Q3)

- **Options:**
  - (a) fresh reads by two CMR readers on every patient, with adjudication: about 160 × 2 × 10 min ≈ 55
    reader-hours (an estimate), plus about 3 min per patient for the registration check;
  - (b) two readers on development and one on the seal (Kilo, ≈ 35 h);
  - (c) clinical reports.
- **Recommendation: (a).** The seal's reference is what the claim rests on. (c) rarely gives Kim bins per segment.
  These are CMR readers, separate from the Stage A border reads, in the Janus-M queue after them.

### LQ17 — The success rule (Juliet PB-Q3)

- **Options:**
  - (a) JA32: sensitivity ≥ 0.75, specificity ≥ 0.93, transmurality agreement ≥ the LGE readers' − 0.10, all lower
    bounds, one look;
  - (b) Juliet's κ_w ≥ 0.60, sensitivity ≥ 0.70, specificity ≥ 0.90.
- **Recommendation: (a).** κ over all segments passes whatever the grading error (all three E-power studies), and
  (b)'s bars sit below the published pooled lower limits.

### LQ18 — Juliet's CPU add-on and JM-0R

- **Options:**
  - (a) run JM-0R once, after Job JM-0, and post its summary on #142 and #143; do not run `edges_m0.py`;
  - (b) run `edges_m0.py` as well.
- **Recommendation: (a).** JM-0R computes the same half-maximum offsets with the same sign, behind the JA12 guard,
  the frozen JM-0 list and the `splits.json` hash; `edges_m0.py` has none of the three. One job, 0 GPU-h, serves both
  paths. This extends LQ11.

---

## 6. Forking question: **no fork**

The cap allows one fork (2 of 4 paths are active). The only candidate is **whether the paired data will include
same-session LIE (T2) or only CCTA + LGE (T1)**. It is not a fork:
- **T1-only is a strict subset of this plan.** It is JA33 without JA29–JA32: the same cohort specification, reads and
  code, minus the scar grade.
- A separate path would duplicate everything for no structural difference. JA27's tiers already handle it.

Every other open question (LQ13–LQ18) changes a bar, a window, a reader count or a compute choice, not the
structure.

---

## 7. What Round 3 on this path must settle

1. **One shared synthetic-LIE benchmark**, the scar analogue of JA15, on which every menu item of JA29–JA30 runs:
   - Kilo's 13 and Golf's 22 guard-allowed hearts, plus Juliet's phantom;
   - blood below, equal to and above scar;
   - a heart that moves against a static chest;
   - scale and a 5 % phase change;
   - CNR 3 and 5;
   - truth both as volume share and as depth extent.

   A candidate that fails on it is struck before development. In particular, measure the spill share of Golf's
   core-rule sensitivity.
2. **The merged power script** (JA35 item 4), re-run at the JA32 bars: the seal size under weak and strong
   clustering, and how many patients ≥ 270 ischaemic scarred segments needs at 50 % and 70 % enrichment.
3. **The LGE read form and the registration check form**, written for the queue (JA32, JA29), with the Kim-bin
   definition and examples, and the reader time measured on a mock-up.
4. **The JA27 intake checker**: which DICOM fields prove phase, frame of reference and timing, and what a patient
   failing each one becomes (stratum or exclusion).
5. **The registration QC cuts**: how they are set on development, and a truth-free check that does catch a phase
   mismatch, if one exists. Juliet found none.
6. **The JA25 hand-over**: confirm that the shared Stage A code (harness, JM-0R, table writer) is on `dev` or merged
   here, so both paths run one implementation; then apply JM-0R's numbers here as `jm/rest-ccta` does.
7. **The path summary for the lead on #143** (§8 below, updated).

Not for Round 3: the seal size itself. It needs development data, and JA28 already fixes how it is set.

---

## 8. Path B against path A, for the lead

| | Path A, `jm/rest-ccta` | Path B, `jm/paired-scar` |
|---|---|---|
| Assumes | no reference for scar or ischaemia | the lead obtains a paired CCTA + LIE + CMR LGE cohort (data requirements only, D31) |
| Stage A (borders, layers, segments, territories, Tables A and B) | built and calibrated: specificity only, sensitivity never stated (JA18) | **identical** (JA25) |
| "Scarring" in the brief | inferred: thinning, fat and hypoattenuation as calibrated research flags | **measured**: scar presence and Kim bin on LIE, scored against LGE, plus path A's flags scored against LGE (JA33) |
| Reference standard | read-vs-read border agreement | the same, plus two CMR readers per segment |
| Territories | Euclidean primary; geodesic measured | decided against the culprit vessel (JA33) |
| Committed compute | ≈ 15 GPU-h (with LQ12) | the same + ≈ 3 GPU-h once the cohort exists; scar is CPU |
| Extra reader time | none | ≈ 55 CMR reader-hours + registration checks |
| Main risk | flags with no measured sensitivity | the cohort never arrives; or Scar-0 at real CNR sits at the 0.75 floor (Golf E5) |
| If the cohort never arrives | — | path B reduces to path A exactly; nothing built here is lost |

**In short:** path B is path A plus one validation study. Choosing B costs nothing on Stage A. Its whole value
depends on whether a same-session LIE + LGE cohort of about 160 patients can be had, and that is the lead's
question, outside the repository.
