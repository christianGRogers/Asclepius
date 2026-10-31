---
aliases: [Janus-M Round 4 paired-scar JA82 addendum]
tags: [janus-m, plans, judgement, round4, path-paired-scar, registration, phase, fallback]
author: Janus-M Round 4 judge (path jm/paired-scar), JA82 addendum
round: 4
path: jm/paired-scar
status: ruling
updated: 2026-10-31
issue: christianGRogers/Asclepius#266
---

# Janus-M Round 4, path `jm/paired-scar`: JA82 addendum (the fallback question)

**Ruling: (a). JA51 step 5 stays as shipped, and JA82's skip is not adopted** (JA88). The 10 mm fallback runs whenever
the last 4 mm stage fails QC. `register_lie(phase_check_before_fallback=False)` stays the default, and nothing on the
path turns it on. The 4 mm phase check stays logged but routes no patient. Routing stays on the final-stage edge offset
(JA84).

- **The non-rigid miss is a cost, not noise.** The skip worsens 13 of the 16 non-rigid cases it touches, by up to
  1.21 mm. The paired p90 cost is +0.33 mm, with a bootstrap SD of 0.18 (§2).
- **Most of the phase gain is already delivered.** A routed phase patient is graded on its last 4 mm stage, never on the
  fallback (JA85). On the benchmark, the skip's extra gain over that rule rests on **4 of 63** smaller-cavity cases (§3).
- **No narrower skip can be built from the routing flag.** At the 4 mm step, those 4 phase cases look the same as 8
  non-rigid cases where the fallback is right. A skip fitted to tell them apart would be fitted on the closed benchmark
  (JA87).

**What follows:**
- **#179 verdicts:** unchanged. The menu is still JA80's.
- **Phase grading:** unchanged from what #265 shipped.
- **Yield:** unchanged.
- **Lead question:** none (§6).
- **Shipping:** one report-only item, **PS4-S10** (§7). It lets development show whether unrouted phase patients are
  ending on the fallback.

**Rules kept.** The judge ran no experiment, registration or Fir job, opened no image, downloaded no data and read no
held-out case or twin list. The only installation was the Python package scipy, so that the committed `score_v3.py` could
be imported. The checks read `jm/paired-scar` at `78d1b14`:
- `bench_lie/scores_v3.json` → `ja82_replay`, `strike`, `strike_reported` and `phase`;
- `score_v3.py`: `chain`, `chain_ja82`, `ja82_replay` and `strike`;
- `registration.py`: `register_lie` and `Registration`.

Figures marked "judge's re-tabulation" are arithmetic on the committed `results_v3.jsonl.gz` rows, done with
`score_v3.py`'s own decision functions, as in Round 4 §1. They add no new arm, motion or stage. The bootstrap resamples
the 63 cases of a motion. All figures are at CNR 5, with n = 63 per motion. No case id is reproduced.

---

## 1. The committed replay, checked

| Bar (PS4-S5) | Committed (`ja82_replay.acceptance`) | Limit | Result | Issue #266 |
|---|---|---|---|---|
| #179 strike verdicts | `strike_verdicts_unchanged: true` (P-K struck; P-J, P-G, E-V, E-D survive under every chain) | unchanged | pass | ✓ |
| `phase` p90 | **1.201 mm** (median 0.270); shipped chain (g) 1.199 / 3.682 (median / p90) | ≤ 1.2 | miss by 0.001 | ✓ |
| `nonrigid` p90 | **2.543 mm**; shipped chain (g) 2.229 | within 0.3 of 2.23 | miss: 0.313 > 0.3 | ✓; the margin is 0.013 against the reference 2.23 the code uses. #266's 0.014 is against the measured 2.229 |

**Strike minima (`strike_reported`), bars: sensitivity ≥ 0.75, specificity ≥ 0.93, spill ≤ 0.25:**

| Chain | P-G min sens / spec / spec scar-free / max spill | P-J min sens / spec / spec scar-free / max spill |
|---|---|---|
| shipped (g) | 0.915 / 0.985 / 0.989 / 0.012 | 0.888 / 0.958 / 0.966 / 0.094 |
| JA82 (g + skip) | 0.915 / 0.985 / 0.992 / 0 | 0.865 / 0.950 / 0.961 / 0.078 |

- #266's strike figures are the JA82 chain's. ✓
- The skip leaves every verdict as it was. It does lower P-J's minimum sensitivity by 0.023 on the strike motions, where it
  touches 1 `none` case and 2 `rigid` cases. This decides nothing; it is recorded.

**Where the skip fires** (`tre_by_motion.skipped_step5`): `none` 1, `rigid` 2, `scale` 10, `aniso` 9, `phase` 50,
`phase_neg` 42, `nonrigid` 16.

## 2. Is the miss noise? Judge's re-tabulation

| Motion | Paired p90 change, JA82 − shipped (bootstrap mean ± SD) | JA82 p90's own bootstrap SD | Skipped cases: TRE change |
|---|---|---|---|
| `phase` (smaller cavity) | **−2.53 ± 0.33 mm** | 0.29 | 26 better (0.09–4.31 mm), 23 unchanged, 1 worse (+0.68) |
| `nonrigid` | **+0.33 ± 0.18 mm** | 0.21 | 13 worse (+0.03 to +1.21 mm), 2 unchanged, 1 better (−0.01) |

- **Both margins (0.001 and 0.013 mm) are far inside one SD.** At that margin the bars cannot tell a pass from a miss.
  Option (b), "adopt because the misses are noise", is right about the margins.
- **Option (b) is wrong about what they measure.** The `nonrigid` cost is about 1.9 SD from zero, and it is one-sided.
  When the skip fires on non-rigid motion, it nearly always throws away a better fallback.
- **The premise JA82 relied on was wrong for the stage it gates.** Round 4 cited the edge flag as "rare on non-rigid
  motion (10 / 74)". That is the **final-stage** flag over both CNRs (`phase["g|nonrigid"]`). The **4 mm-stage** flag the
  skip reads fires on 16 / 63 at CNR 5, against 9 / 63 at the final stage.
- **The bars were pre-registered, and JA82 said what a miss means.** Reading them loosely after the fact would undo the
  replay's purpose. (b) is not adopted.

## 3. What the skip would add to what already ships (judge's re-tabulation)

#265 grades a phase-suspect patient on its last 4 mm stage (`graded_stage`, JA85). So the fair comparison is not "JA82
against the bare shipped chain" (the 3.68 mm p90). It is "JA82 against the shipped chain once routed patients are graded
on the 4 mm stage".

| Motion | Shipped chain, final-stage flag graded on 4 mm (upper bound: every flagged patient routed) | JA82 chain |
|---|---|---|
| `phase` | median 0.271, p90 **1.539** | median 0.270, p90 **1.201** |
| `nonrigid` | median 1.633, p90 **2.273** | median 1.669, p90 **2.543** |

**The whole phase gap comes from 4 smaller-cavity cases.** Each ends on `rigid10` with a 4 mm flag but no final-stage
flag: 4 mm TRE 0.06–0.52 mm, `rigid10` TRE 2.45–4.21 mm. On non-rigid motion, **8 cases** show the same pattern (fallback
kept, 4 mm flag only), but there the fallback is better in 8 / 8 (4 mm 1.72–3.35 mm, `rigid10` 1.51–2.30 mm).

At the point of decision the two groups carry the same logged facts: QC failed at 4 mm, the edge offset flagged at 4 mm,
and the fallback was kept. **Option (c)**, a narrower skip that cannot touch `nonrigid`, would need a second
discriminator. That discriminator would be chosen on these same rows, and its "pre-registered re-replay" would re-read
the rows it was fitted on. JA87 closed the benchmark for this reason. (c) is not adopted.

**Rejected as well: a flag union**, where the 4 mm flag also routes and step 5 still runs. It would catch the 4 phase
cases without moving any registration. But it raises routing flags on non-rigid motion from 9 to 17 / 63, on `aniso`
from 6 to 11 and on `scale` from 11 to 13, and false flags on phase-matched hearts from 1 to 3 / 126. Each extra flag on
an inferred-phase patient is charged to yield as flag-only (JA85), and leaves the primary.

## 4. Option (d): leave it to development

Development has no TRE, so it cannot replay this question. What it can show is how often the case the skip was meant
for happens on real patients: the 4 mm flag fires, the fallback is kept, there is no final flag, and the patient is
therefore not routed. It can also show what the reader check does with those patients. **That count is now reported
(PS4-S10), and it decides nothing.** If it is large, a later judge has a reason, and real data, to reopen the question.
It does not reopen anything by itself.

## 5. Binding amendment (one)

- **JA88 — JA51 step 5 stays as shipped; JA82's skip is not adopted.** (Settles JA82. Amends nothing else.)
  - **Step 5 is JA51's.** If the last 4 mm stage fails QC, one 10 mm rigid run replaces it if the run passes QC or
    lowers the normalised maximum. This holds with JA81 (g) as the affine rule.
  - **`phase_check_before_fallback` stays `False` by default.** No pipeline, script or development run on this path
    sets it to `True`. It remains only for tests and the committed replay.
  - **Routing reads the final stage only** (JA84).
    - The 4 mm phase check (`phase_4mm`) is computed and logged whenever step 5 is reached. It routes no patient.
    - JA82's "a flag there also counts" lapses with the skip.
  - **JA85 is unchanged.** A phase-suspect patient is graded on its last 4 mm stage, never on the fallback. That rule,
    not the skip, is what protects routed phase patients.
  - **Unrouted phase patients rely on the reader check.** These are patients with only a 4 mm flag, or DICOM-matched
    patients the reader does not mark. They are graded on their final stage, as any ordinary patient is, and the reader
    check on every patient (JA51 step 6) is their guard.
  - **The question is closed on the benchmark.** No narrower skip and no second discriminator is fitted on the v3 rows
    (JA87). Only a later ruling can reopen it, and only on development evidence: PS4-S10's report together with reader
    outcomes.
  - **Consequences:**
    - **#179:** the verdicts and minima are the shipped chain (g)'s (§1). JA80's menu stands.
    - **Phase grading:** as #265 shipped. On the benchmark, the 4 / 63 unrouted smaller-cavity cases are the residual
      risk.
    - **Yield:** as #265 shipped. The skip would have raised routing flags on non-rigid motion from 9 to 16 / 63, and
      would have charged the inferred-phase patients among them to yield.
  - **Record:**
    - #266's `nonrigid` margin is 0.013 against the 2.23 mm reference the committed check uses;
    - Round 4's "10 / 74" was the final-stage flag over both CNRs, not the 4 mm-stage flag JA82 gates on (§2);
    - the JA82 chain lowers P-J's minimum sensitivity from 0.888 to 0.865, with every verdict unchanged.

## 6. Questions for the lead: none (no LQ41)

The bars were pre-registered, the evidence settles the question, and the ruling changes no claim, seal, cohort or cost.
Nothing in it belongs to the lead. **LQ40** and the questions Round 4 carried are unchanged.

## 7. Shipping (`role:swe`, labelled `jm/paired-scar`; code on `jm/paired-scar` in `src/janusm/scar/registration.py`)

- **PS4-S10 — Report unrouted 4 mm phase flags on development, and pin the default** (JA88). Report only; decides nothing.
  - **Wrong:**
    - the 4 mm phase check is logged per patient (`Registration.log()["phase_4mm"]`), but nothing counts the patients
      it flags that end up unrouted and graded on the fallback;
    - no test pins `phase_check_before_fallback=False` as `register_lie`'s default;
    - the module docstring and `register_lie`'s docstring cite the missed replay, but not JA88.
  - **Correct:**
    - `phase_4mm_only(reg: Registration) -> bool` is True iff all hold:
      - `reg.phase_4mm is not None and reg.phase_4mm.suspect`;
      - `not reg.phase_flag`;
      - `reg.final.name == STAGE_FALLBACK`;
    - `phase_4mm_only_report(registrations)`, placed next to `phase_suspect_needs_report`, returns:
      - `n`, `count` and `share`, with an exact (Clopper–Pearson) upper 95 % bound;
      - the reader-check outcomes of the counted patients, as `status` counts (passed / re-registered / not graded /
        phase suspect).

      It has no threshold and gates nothing;
    - both docstrings name JA88 as the reason the switch is off.
  - **Test:**
    - three mocked registrations (as in `test_ps3_s1_fallback_runs_only_when_the_4mm_stage_fails_qc`):
      - 4 mm flag, fallback kept, no final flag → counted;
      - 4 mm flag and a final flag → not counted;
      - no 4 mm flag → not counted;
    - the report on those three gives `count == 1`, `n == 3` and an upper bound above the share;
    - `inspect.signature(register_lie).parameters["phase_check_before_fallback"].default is False`;
    - the default path's `register_lie` results are byte-identical to today's.
