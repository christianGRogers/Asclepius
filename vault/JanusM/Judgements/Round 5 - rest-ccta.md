---
aliases: [Janus-M Round 5 rest-ccta]
tags: [janus-m, plans, judgement, round5, path-rest-ccta, myocardium, build-check]
author: Janus-M Round 5 judge (path jm/rest-ccta)
round: 5
path: jm/rest-ccta
status: ruling
updated: 2026-10-30
issue: christianGRogers/Asclepius#223
---

# Janus-M Round 5, path `jm/rest-ccta`: the judgement

**Ruling in one paragraph.** Every Round 4 fix (R4-S1 … R4-S23; #216–#220) merged with each test Round 4 §7 names,
and every one of those tests passes. No item came back as unwritable. The single test that could not be written
as specified is R4-S4's "within 0.05 mm": the open-base check **failed**, and the test pins that failure.
- **The bias guard is 0.5 mm** (JA61), as recorded.
- **Three gaps sit outside the named tests.**
  - **Four code defects**, confirmed in the code (§1.2). None has touched a case:
    - S3 crashes on JA60's own `{"ED": 1.0}`;
    - the JA66 plane falls back to the read's own gap;
    - the lesion-point bounds check fails open;
    - `admin/wave` can move cases that already have reads.
  - **Tests that are weaker than the ruling:** 8–12 of them, depending on the advocate's count. One of them cannot
    fail, and one runs in no CI job.
  - **#219's open-base remedy, as worded, removes the epicardium it is meant to measure.** All three advocates
    show this.
- **JA70–JA79** do the following:
  - define the cut-cap band;
  - pre-register the one validation that can return the guard to 0.3 mm (it needs a phantom nobody has seen);
  - ratify or reject each engineer's judgement call;
  - close the four defects.
- **One consolidated shipping list** (§7, R5-S1 … R5-S12), grouped by module. **Four items block the first read
  wave.**
- **No fork.**
- **The path now waits only on the lead's JM-0 / JM-0R and on these fixes** (§8). No further build-check round is
  needed.

Rules kept:
- The judge ran no experiment, opened no image, downloaded nothing, and read no held-out case or TotalSegmentator
  twin.
- Checks read committed code, tests and JSON on `jm/rest-ccta` at `eb11818`, and issues #223 and #205.
- No id was read or printed.

---

## 1. What was checked

### 1.1 The advocates' numbers against their committed JSON: all match

| Advocate | Claim | File | Match |
|---|---|---|---|
| Hotel | Shipped band: A epi 0.0678, B epi 0.0504; `plane` A 0.0155 / B 0.0193 / C 0.0119; `literal` epi undefined on A and B, 0.0388 on C | `Hotel/r5/e11_open_base_remedy.json` | yes |
| India | Shipped E6-open 0.0678, capsule 0.0504; `cap` 0.015 / 0.0238; E4 shells unchanged (0.0038 / 0.0019); `literal` undefined | `India/r5/b1_band_remedy.json` | yes |
| India | `detectable_depth(…, phase_mix={"ED": 1.0})` → `KeyError: 'MD'`; the three-key form gives 0.45 | `India/r5/a1_phase_mix.json` | yes |
| Lima | India open: shipped epi 0.0678, `cap_plane` 0.0158; validator at 3 offsets: shipped 0.0504 (fail), `cap_plane` 0.0238 (pass) | `Lima/r5/e1_open_base_remedy.json` | yes |
| Lima | LA-capped heart: shipped epi 0.0168 (pass), `literal` 0.0518 (fail), `cap_plane` identical to shipped | `Lima/r5/e2_la_capped_heart.json` | yes |
| Lima | The capsule passes at `n_offsets=1` (worst 0.0467) | none committed | **not in a file**. The tautology is visible in the test itself (§1.2 item 6), so the finding stands without the number |

### 1.2 The PM's notes, verified in the code

1. **`population` raises on JA60's own mix (all three).** **True.**
   - `calibrate.population` indexes `phase_mix[k]` for every phase (`calibrate.py` 118).
   - `detectable_depths` validates through `_phase_key` (338), which fills missing phases with 0, but then passes
     the raw dict on (355).
   - The error is a `KeyError`, which R9's `except ValueError` (`jm0r_decide.py` 386) would not catch.
   - Only #218's three-key `HYPO_PHASE_MIX` (`reference.py` 621) keeps shipped callers working.
2. **The lesion-point bounds check fails open (all three).** **True.**
   - `rest.submit` logs an error when `ctWorldBounds(case)` is `None` (`rest.py` 246–249).
   - `niftihead.points_outside(points, None)` then returns `[]` (`src/janusm_reads/niftihead.py` 118–119), so the
     points are accepted unchecked.
3. **`admin/wave` can move cases with accepted reads (Hotel H5-4; Lima L4-14).** **True.**
   - `adminWave` runs `update_many(… {'$set': {'wave': wave}})` on any named case (`rest.py` 373), with no check of
     accepted reads or third-read state.
   - `_seededDoubleRead(wave)`, and therefore `third_read_cases` and Rules 1–2, follow the new membership.
   - India's "fails closed" holds only after a report has been made. A move before the report silently changes
     which reads the report counts.
4. **The JA66 plane falls back to the read's own gap when a seed exists but cannot be fitted (India SW5-D1).**
   **True.**
   - `mitral_plane` appends the seed source only if the seed has both label 2 and label 4 (`checker.py` 330–335).
   - It then always appends the read's own gap (336–338), and the first source with enough points wins.
   - So two cases fall back to the read's gap:
     - a seed with no LA, or with too few interface points;
     - a blank case populated without `checkSeedFileId`.
   - That is the hole JA66 closed.
5. **`adminThirdReads` trusts the admin's `rule2.flagged` (Lima L4-22, Hotel H5-5, India SW5-D3).** **True, and
   bounded.**
   - The server recomputes the seeded set and the draw, and refuses any other list (`rest.py` 395–413).
   - It reads `flagged` as sent (401).
   - So an admin can open third reads on an unflagged wave, but only on the server's own draw.
6. **The JA61 capsule test cannot fail (Lima L4-4).** **True.**
   - `test_validate_bias_estimator_open_base` runs `n_offsets=1` and allows a worst of 0.06.
   - It asserts `bias_guard_mm == (0.3 if passed else 0.5)`, which is true of any result
     (`test_janusm_harness.py` 563–573).
   - The 0.0504 mm failure that `BIAS_GUARD_VALIDATED_MM`'s comment cites (`harness.py` 84–91) is at 3 offsets,
     which no test runs.
   - The guard constant is pinned only by the India test (`assert not passed`, 555–556), and the failing epicardial
     rows there have no upper bound (Lima L4-3).
7. **R4-S17's `decide()` test runs in no CI job (Lima L4-12).** **True.**
   - `test_r4s17_a_crash_or_an_unchecked_read_never_spends_the_return` skips without girder
     (`test_janusm_reads.py` 897–898).
   - The main job installs no girder (`ci.yml` 117).
   - The Mongo job runs three other files (`ci.yml` 205–206).
   - The Mongo test `test_r4s17_a_crash_never_spends_the_return` covers "crash, then failure". Nothing in CI covers
     "a genuine return, then could not be checked".
8. **R4-S4's docstring lacks JA37's disclosed error (Lima L4-6).** **True.**
   - `signed_bias` says the real-wall error "is not known from phantoms alone" (`harness.py` 329–330).
   - JA37 disclosed it: up to 0.05 mm low outward and 0.09 mm high inward near 0.3 mm (India E9).
   - The module docstring (`harness.py` 56–58) still says 0.03 mm where JA65 says 0.035 (India).

**Further checks:**
- **R3's note is dropped when S3 refuses or the median is missing (Hotel H5-2).** **True:** `R3_NOTE` is appended
  only in the `else` branch (`jm0r_decide.py` 402–403).
- **The missing-median record contradicts itself (India SW5-A2).** **True:** the text says the page "prints the
  provisional 45 % … until it can be computed" (380), while `numbers_only` is true (407).
- **AHA fall-backs are counted only over the 20 RC cases (India SW5-C1).** **True:** `fell` sums over `rc_rows`
  (`reference.py` 611). Reads 21–40 feed κ and ICC uncounted.
- **The transfer check runs per comparison.** **True:** `transfer()` runs `transfer_fn` on each of the three
  comparisons' first 20 rows. The guard is the max of theirs and `BIAS_GUARD_VALIDATED_MM`
  (`score_decision.py` 222–236).
- **The guard runs after the manifests are read.** **True:** `main` reads the manifests before `guard_cases`
  (341–346). The manifests hold names, not images; the guard needs those names.
- **No JM-0 / JM-0R aggregate is posted.** #205 has three comments, and none is an aggregate. #223 has candidate
  notices only.

### 1.3 The open-base record (Round 4 §8 item 3)

- **R4-S4's validation FAILED.** All three advocates reproduce it:
  - India's E6-open phantom: worst 0.068 mm (epicardium, ±0.5 mm);
  - the cut capsule at 3 offsets: 0.0504 mm;
  - the endocardium is within 0.015 / 0.024 mm.
- `BIAS_GUARD_VALIDATED_MM = 0.5`, and the scorer never goes below it.
- **Under JA61 the guard is 0.5 mm** unless JA71 below is met.

### 1.4 Disclosures

- **Held-out cases.** All three advocates disclose that no case, image or label was opened. Every script builds
  analytic phantoms and calls `guard.refuse([])` first. No committed Round 5 file names a held-out or twin id
  (checked by file listing, not by opening any list).
- **No outside-request text** appears in any candidate (D31).

---

## 2. Scorecards

Scale 1–5:
- **(a)** reasoning;
- **(b)** evidence;
- **(c)** fit to the path and how ready the specs are;
- **(d)** risk and cost (5 = low risk, cheap).

### Hotel v5: the fixes hold; one prescribed input crashes; the remedy works only as a plane

| | Score | Why |
|---|---|---|
| (a) | **5** | Found the `KeyError`, the `admin/wave` reassignment and the fail-open bounds check. Gives the clearest account of why the literal remedy fails (no aorta or pericardium label). Its read-like phantom C (60° open outflow, two tilts) is the only one shaped like a read |
| (b) | **5** | E11: 104 configurations × 4 variants, committed, and every number matches. Audit rows cite file and line |
| (c) | **4** | Specs are ready, but it missed the JA66 plane-order defect (the only remedy-free defect that blocks the first read wave) and the R4-S17 CI gap |
| (d) | **4** | `plane` uses one global plane; its non-planar fall-back (`rim15`) gives up a third of the band. It sends the bounds check down the crash path, which counts a server fault against the read |

### India v5: the fixes test by test, the cap remedy, and its sensitivity

| | Score | Why |
|---|---|---|
| (a) | **5** | The only advocate to find the JA66 plane-order defect, the uncounted fall-backs on reads 21–40, and the missing-median record that contradicts itself. Its cap rule needs no plane, and handles any number of openings |
| (b) | **5** | b1, b2 and a1 are committed. **b2 is the only evidence that the cap verdict does not depend on a tuned value** (all 9 settings pass) |
| (c) | **4** | It accepts `admin/wave` with an argument that holds only after a report. It missed the capsule test's tautology and the R4-S17 CI gap |
| (d) | **4** | It would restore 0.3 mm at the freeze on a band designed after seeing the failure, with no unseen phantom. Its rule loses up to 41 % of the band on oblique walls, and it does not say which faces |

### Lima v4: the most complete bullet audit, and the pre-registration principle

| | Score | Why |
|---|---|---|
| (a) | **5** | Found that the capsule test cannot fail, the R4-S17 test that runs in no CI job, and the missing JA37 disclosure. It is the only advocate to say a remedy found after the fact needs a fresh validation, and that a read can have more than one opening |
| (b) | **4** | E1 and E2 are committed and match. Deducted: the 0.0467 mm single-offset figure is in no committed file |
| (c) | **4** | 22 specs, the most granular; several are one-line test edits that belong in one issue. It missed the JA66 plane-order defect and the R9 record's contradiction |
| (d) | **5** | Holds 0.5 mm until a pre-registered check passes, and keeps the band a no-op where the base meets the LA |

**Totals (of 20):** Hotel 18, India 18, Lima 18.

- This round audits the build. It chooses no plan, so **no candidate replaces the base**: the master plan stays
  [[Hotel v3]] + JA37–JA49 + JA60–JA69, now + JA70–JA79.
- On the three-way tie, **India v5 is the round's lead audit**. It found the one remedy-free defect that would have
  acted on the first read wave (SW5-D1), and its sensitivity sweep is what lets JA70 fix the cap rule's parameters
  before validation. The amendments take from all three:
  - the band, from Hotel's and Lima's plane and India's cap rule;
  - the validation, from Lima's principle.

---

## 3. Rulings where they disagree

| Item | Hotel | India | Lima | **Ruling** |
|---|---|---|---|---|
| #219 remedy as worded | reject (no epicardium left) | reject | reject | **rejected** (JA70) |
| Cap definition | one plane through the open faces, 1 mm; `rim15` if non-planar | normal within 45° of the nearest open face, reach 20 mm | plane per connected opening, one voxel | **a plane per connected opening (1.0 mm, reach 20 mm); India's 45° / 20 mm rule where an opening is not planar** (JA70) |
| Restores 0.3 mm? | only after the full check passes | yes, at the freeze, if the re-run passes | only after a fresh pre-registered check **and** the transfer check | **only if JA71's pre-registered check passes, including one phantom not yet built; the transfer check stays final** (JA71) |
| When the guard must be known | — | at the freeze | at the freeze | **before the first decision-scoring run**, not the freeze (JA71) |
| `population` raises on an omitted phase | reject | reject | reject | **rejected; an omitted phase is 0** (JA73) |
| `numbers_only` whenever no depth | accept | accept, fix the text | accept | **accepted; the text and R3's note follow** (JA74) |
| Full phase-mix dict to S3 | accept | accept | accept | **accepted, kept** (JA75) |
| E_T > 0 per read | accept | accept | accept | **accepted** (JA75) |
| Two-value septal-arc cell | accept | accept | accept | **accepted** (JA75) |
| LM lesion point labels LAD and LCx | accept | accept | accept | **accepted; no number until a distal mass is ruled** (JA75) |
| Transfer check per comparison | accept | accept | accept; ratify, and add a union count | **ratified, with the union count** (JA72) |
| `phantom.heart()` 2 mm gap | accept | accept | accept | **accepted** (JA78) |
| `adminThirdReads` takes the report | accept; check its consistency | accept; store its sha | accept with a reservation | **accepted; the server recomputes `flagged` from the report's rows and stores its sha** (JA78) |
| `POST admin/wave` | reject as written | accept | accept; refuse moves unless `force` | **endpoint accepted; a case with any accepted read or third-read state never changes wave; no `force`** (JA78) |
| 0.3.0, 426 for 0.2.x | accept | accept | accept | **accepted** (JA78) |
| Unseeded plane fall-back | — | could not be checked | — | **could not be checked; a blank case without a check seed is refused** (JA76) |
| No CT box with lesion points | crash path | 400 | 409 | **409 at submit; the read stays open; nothing is counted; the PM is alerted** (JA77) |
| "Before opening any file" (JA62) | — | as built, it is the only workable reading | reword, or move the guard | **reworded: before any image, mask, label or read file** (JA72) |

---

## 4. Binding amendments (JA70–JA79; path `jm/rest-ccta`)

- **JA70 — JA61's band also excludes the cut cap.** (Amends JA61.)
  - **The remedy as worded is rejected.** "Exclude ≤ 3 mm of any pool or myocardium face that adjoins label 0"
    removes the epicardium. JA1's labels have no aorta, pericardium or fat, so the free epicardium adjoins label 0
    everywhere. The measured effect:
    - empty or undefined in 96 of 96 epicardial rows on the open phantoms;
    - on the LA-capped heart, 18 % of the band survives, and that remnant fails (Lima E2, Hotel C).
  - **The definition.** `harness.ja37_band(ref_labels, spacing, border)` keeps JA61's steps. It then also removes
    the voxels within 3.0 mm of every **cap face**, found as follows:
    1. **Openings.** Group the LV-pool faces that adjoin label 0 into 26-connected components. Each component is
       one opening.
    2. **The plane.** For each opening, fit a least-squares plane through its face centroids.
    3. **Planar openings** (RMS distance of those centroids to their plane ≤ **1.0 mm**). A cap face is a solid
       (labels 1 ∪ 2) face adjoining label 0 that lies within **1.0 mm** of the plane and within **20 mm** of the
       opening's faces.
    4. **Non-planar openings.** A cap face is a solid face adjoining label 0 within **20 mm** of the opening's
       faces, whose outward normal (the gradient of the solid smoothed by one voxel) is within **45°** of the
       nearest open face's normal. This is India's rule.
    5. **No opening** (closed shells; a pool that opens only into label 4): the band is JA61's, bit for bit.
  - **Record.** The function returns, per border, the share of JA61's band kept and the form used per opening
    (`plane`, `normal`). The scorer writes both into its output.
  - **The parameters (1.0 mm, 20 mm, 45°) are fixed by this ruling.** They are not tuned after JA71's run.
- **JA71 — The only way back to a 0.3 mm guard: one pre-registered check.** (Amends JA61's fall-back clause.)
  - **The check** is `validate_bias_estimator(open_base=True)`, extended, run once on JA70's band. Its rows are:
    - **A:** India's E6-open phantom: two grids, three walls, both borders, ±0.3 / ±0.5 mm (48 rows);
    - **B:** the cut capsule at the default 3 offsets (144 rows);
    - **C:** Hotel's read-like heart with a 60° open outflow, tilts 0° and 23°;
    - **D:** the harness's LA-capped heart (Lima E2). JA70's band must equal JA61's bit for bit;
    - **E (new; nobody has run it):** an LA-capped heart whose aortic opening sits beside the LA, off the mitral
      plane, at two grids, both borders and ±0.3 / ±0.5 mm, plus one variant whose outflow is cut on a curved
      surface, so that the non-planar branch runs;
    - **F:** E4's closed shells, which must be unchanged.
  - **Pass** means all of:
    - |error| ≤ **0.05 mm** on every row of A, B, C and E;
    - D and F unchanged;
    - each phantom keeps ≥ **50 %** of JA61's epicardial band;
    - the non-planar branch is exercised on E.

    The tolerance is not changed.
  - **If it passes,** `BIAS_GUARD_VALIDATED_MM` becomes 0.3, and `HARNESS_VERSION` becomes 1.3.0.
  - **If it fails,** the guard is 0.5 mm for the whole r1 seal. No further band variant is tried for r1.
  - **When.** The item (R5-S3) must merge, with either verdict, **before the first decision-scoring run**
    (R4-S23's `--run`). It need not hold the freeze PR, because no read can show the guard's effect before
    decision scoring. If it has not merged by then, the guard is 0.5 mm for r1.
  - **The transfer check stays the last word on real walls** (JA37, JA62, JA72). A failure there sets 0.5 mm
    whatever JA71 says.
  - **Why the new phantom.** A band defined after seeing a failure, and validated only on the phantoms that showed
    it, is fitted to them (Lima). Phantom E has a geometry none of the three advocates ran: an aortic opening
    beside the LA, and a curved cut.
- **JA72 — The transfer check and the scorer's order, ratified.** (Amends JA37, JA62.)
  - **Per comparison.** The transfer check runs on the first 20 rows of each comparison: model-vs-read 1,
    model-vs-read 2 and read-vs-read. It fails if any one comparison's median |vol − pp| on either border exceeds
    0.05 mm. That can only raise the guard. A pooled median lies between the parts' medians, so this is never laxer
    than JA37's pooled reading.
    - The higher chance of a spurious failure with six medians is accepted, because the cost of a spurious failure
      is the conservative guard.
  - **The union count.** Besides the per-comparison counts, the output reports `n_cases_over_limit`: the number of
    distinct cases (of the first 20) with any comparison and border over 0.05 mm. No ids.
  - **JA62's "before opening any file"** reads: **before opening any image, mask, label or read file**. The
    `sealed-r1.json` list (hash-checked) and the export manifests may be read first, because they are where the
    guard's names come from. No code change.
- **JA73 — S3's phase mix: an omitted phase is 0.** (Amends JA60's implementation; rejects #217's call.)
  - Every `calibrate` entry point (`population`, `simulate`, `detectable_depth(s)`, `population_factor`) takes a
    partial mix, read through `_phase_key`: an omitted phase is 0.
  - A `ValueError` is raised on an unknown key, a negative or non-finite weight, or a sum ≠ 1. A `KeyError` is never
    raised.
  - `{"ED": 1.0}` and `{"ED": 1, "MD": 0, "SYS": 0}` give the same depth for the same seed.
  - `CALIBRATE_VERSION` 1.1.1; no number changes.
- **JA74 — R9's record, every branch.** (Ratifies #217's call; amends JA60's R9 branches.)
  - `numbers_only` is true whenever no depth is computed or the depth is None. This covers:
    - a missing median;
    - an S3 refusal;
    - a depth not reached by 0.60.

    In each case JA41 cannot be evaluated.
  - **The outcome text matches.** The missing-median branch says "numbers only; the footer prints 45 % labelled
    provisional (JA40)", as the refusal branch does.
  - **R3's note is appended in every branch** when R3 fails, computed or not.
  - The JA69 precedence note in `jm0r_readout.py` (the pooled flag is reported; R7 uses the case median) moves from a
    comment into the module docstring.
- **JA75 — #218's calls ratified, and fall-backs counted on every read.** (Amends JA63, JA64, JA69.)
  - **The full phase-mix dict** stays in `reference.HYPO_PHASE_MIX`. It is harmless after JA73.
  - **The relative RC** needs E_T > 0 for **both reads** of every pair. This is JA64's "each read's territory has an
    expected level" read literally, and it guarantees a positive divisor.
  - **The septal-arc cell** shows two values, the arc wall and the arc relative subendocardial HU, each with its
    percentile, under a header naming both. Elsewhere it shows "—". R7 keeps or drops the whole column.
  - **An LM lesion point** labels both LAD and LCx with "distal mass: not computed (report v1)". No number is
    attached. Whether LM's distal mass is split or shared is ruled with the distal-mass definition, if one is ever
    ruled.
  - **Fall-backs.** Every AHA fall-back is counted over **all reads the population uses**: the RC's first 20, and
    κ / ICC's reads 21–40. It is reported in `rc["decisions"]` and in the report header (JA63's "never silent").
- **JA76 — JA66's plane order, final.** (Amends JA66.)
  - **The read's own gap is never a plane source for a queued case.** It stays in `checker.mitral_plane` only for
    phantom tests that pass `seed=None` explicitly.
  - **A seed or check seed that yields no fittable 2–4 interface** is "could not be checked": JA68's crash path
    (returned, not counted, PM alerted). It is never fitted to the read.
  - **A blank case with no `checkSeedFileId`** is refused by `check.py` before checking, and the PM is alerted.
  - `populate.py --backfill-check-seeds` uploads check seeds for blank cases populated before #220. The protocol
    document names the step.
  - Hinge points stay a code-only fall-back (JA66), behind the seed and never behind the read.
- **JA77 — JA67's bounds check fails closed.** (Amends JA67.)
  - **No world box.** When a submission carries lesion points and the case's CT world box cannot be read,
    `rest.submit` refuses with **409** ("CT bounds unavailable; lesion points cannot be checked"). The read stays
    open and unchanged; no attempt, return or crash is counted; and the PM is alerted.
  - **No points.** A submission without lesion points is not affected.
  - **Why not the crash path:** the fault is the server's (a case it cannot read), not the read's. The reader's work
    is kept, and nothing is accepted unchecked.
- **JA78 — Waves and third reads.** (Amends JA68; ratifies #220's calls.)
  - **`POST admin/wave` is accepted, with one limit.** A case that has any accepted read, `thirdReadWanted`, or an
    open third read never changes wave: the server answers 409, with no `force`. Setting the same wave again is
    allowed. Every change is logged with the admin and the old and new waves.
  - **`adminThirdReads` takes the anchoring report and checks it.**
    - **Flag.** The server recomputes Rule 2's flag from the report's own seeded rows (`anchoring`'s rule, with
      shares over seed voxels). It refuses if the flag disagrees with `rule2.flagged`, or if the rows are not the
      wave's seeded double reads (as now).
    - **One report per wave.** It stores the report's sha256 on the wave, and refuses a different report for that
      wave later. The export records the hash.
  - **`phantom.heart()` keeps its 2 mm mitral gap by default.** Under JA66 a gap-less heart cannot pass, and the
    gap-less shape stays available explicitly.
  - **The client 0.3.0, with 426 for protocol 1** (every 0.1.x and 0.2.x client), is ratified. The wire
    `PROTOCOL_VERSION` 2 decides; `border_protocol` stays 1.
- **JA79 — The named tests are the contract; record.**
  - **The contract.** A test the ruling names must:
    - be able to fail on a wrong implementation;
    - run in at least one CI job that refuses skips.

    A test that asserts its own result (the capsule test) or that skips in every job (R4-S17's `decide()` test) is
    a defect, fixed by R5-S4 and R5-S11.
  - **The guard constant** is pinned by tests that assert the verdict at the validator's default settings, with the
    worst error to ±0.005 mm.
  - **`signed_bias`'s docstring** carries JA37's disclosure, and the module's tolerance reads 0.035 mm (JA65).
  - **Record:**
    - R4-S1 … R4-S23 merged with every named test;
    - R4-S4's open-base validation FAILED (0.068 / 0.0504 mm), so the guard is 0.5 mm unless JA71 passes;
    - four code defects found (§1.2 items 1–4), none acting on a case;
    - no JM-0 / JM-0R aggregate posted, so R0–R10 have no value, and the provisional 45 % stands (JA60).

---

## 5. Questions for the lead (each with a recommendation; none is a fork)

**Carried unchanged, as assumptions:** LQ2–LQ12, LQ19–LQ22 and LQ30–LQ34, with their recommendations. LQ30's
"first read wave" now also waits on the four items marked in §7.

### LQ35 — Path A with a 0.5 mm bias guard

- **The facts:**
  - If JA71 fails, or the transfer check fails on real reads, a model whose true signed bias is 0.3–0.5 mm passes
    the bias guard.
  - JA8's d bound (upper 95 % ≤ 0.25 mm per border) and the 1.0 mm ASSD guard still bind. A uniform 0.4 mm shift
    raises ASSD by about that much, and so it is caught by d unless read-vs-read noise is large.
  - The guard is a specificity check on systematic border placement. Thickness and thirds inherit any bias it
    lets through.
- **Options:**
  - (a) accept 0.5 mm as path A's guard if JA71 or the transfer check fails, stated on every page;
  - (b) treat a 0.5 mm guard as a reason to train Janus-M 1 before the seal;
  - (c) count it against path A in the path choice.
- **Recommendation: (a).** d is the primary metric and does not depend on the guard. (b) spends ≈ 55 GPU-h on a
  number no read has yet measured.

### LQ36 — No Round 6 build check

- **The facts:**
  - Every item in §7 is engineering with a named test.
  - JA71's verdict is a test result with a pre-registered pass rule, recorded in R5-S3's PR.
  - Nothing else on the path can be argued without JM-0 / JM-0R.
- **Options:**
  - (a) pause rounds: the PM checks each R5-S item at merge against its named test, and the next round opens when
    the JM-0 / JM-0R aggregates are posted;
  - (b) one more build-check round after §7 merges.
- **Recommendation: (a).** Round 5 found four code defects and no change of plan. A Round 6 check would cost three
  advocates and a judge for what the PM can check at merge.

---

## 6. Forking question: **no fork**

The cap would allow one (2 of 4 paths active). Nothing open on this path changes its structure:
- JA70–JA79 are measurement rules and code fixes;
- LQ35 and LQ36 are acceptance and timing.

The one structural question is still LQ1 (path A against path B), answered by the lead's path choice. LQ33 and LQ35
inform it.

---

## 7. Shipping (`role:swe`; one issue each; label `path:jm-rest-ccta`; cite this ruling and #223)

This list consolidates and replaces Hotel H5-1 … H5-7, India SW5-A1 … SW5-E1 and Lima L4-1 … L4-22. Shared Stage A
code goes on **`dev`** and is synced to both paths. Items are grouped by module, so each group can go to one
engineer.

**Blocks:**
- **The first read wave:** R5-S7, R5-S8, R5-S9, R5-S11.
- **Opening any third read:** R5-S10.
- **The first decision-scoring run:** R5-S3, R5-S4, R5-S12.
- **The freeze PR:** nothing new (R4-S4's verdict is already recorded).

### Group A — the detectable depth (`src/janusm/calibrate.py`, `experiments/JanusM/fir/jm0r_decide.py`, `jm0r_readout.py`)

- **R5-S1 — S3 takes a partial phase mix (JA73).**
  - **Wrong:** `population()` indexes `phase_mix[k]` (`calibrate.py` 118), so `{"ED": 1.0}` raises `KeyError: 'MD'`.
    `detectable_depths` passes the raw dict (355). The only test stubs `simulate`.
  - **Correct:**
    - normalise once through `_phase_key` in `detectable_depths` and `population`, and pass the full dict on;
    - record the full mix in `inputs`;
    - raise `ValueError` (never `KeyError`) on a bad mix;
    - `CALIBRATE_VERSION` 1.1.1.
  - **Tests:**
    - unstubbed, `detectable_depth(0.088, LIMA_SHAPE, 1.0, seed=31000, measured_median_mm=6.3,
      phase_mix={"ED": 1.0})` equals the three-key call;
    - `{"ED": 0.5}` and `{"XX": 1.0}` raise `ValueError`;
    - E7's rows still reproduce.
- **R5-S2 — R9's record in every branch; JA69's note in a docstring (JA74).**
  - **Wrong:**
    - the missing-median text says the page prints 45 % while `numbers_only` is true (`jm0r_decide.py` 380, 407);
    - `R3_NOTE` is added only when S3 computes (402–403);
    - JA69's precedence is a comment (`jm0r_readout.py` 594–597).
  - **Correct:**
    - the missing-median text names "numbers only" and the provisional footer;
    - R3's note is appended in all three branches;
    - the note moves into the module docstring.
  - **Tests:**
    - in `test_r9_missing_median_is_not_decidable`, the string says "numbers only";
    - R3 fails with cv_n = 0 → both the NOT DECIDABLE line and R3's note;
    - R3 fails with a missing median → R3's note;
    - `"case median" in jm0r_readout.__doc__`.

### Group B — the harness (`src/janusm/harness.py`, `tests/test_janusm_harness.py`)

- **R5-S3 — The cut-cap band and its pre-registered check (JA70, JA71).** *Blocks the first decision-scoring run.*
  - **Wrong:** JA61's band keeps the cut myocardial cap. It adds area with no volume change, so the epicardium
    under-reads by 11–13 % on open phantoms, and the check fails.
  - **Correct:**
    - `ja37_band` implements JA70 exactly: openings by 26-connectivity; a plane per opening at 1.0 mm and 20 mm when
      the RMS is ≤ 1.0 mm; otherwise the 45° / 20 mm normal rule;
    - it returns the kept share and the form per opening;
    - `validate_bias_estimator(open_base=True)` gains phantoms C, D and E (JA71). E is new, built in
      `janusm.harness` and committed with the item;
    - `BIAS_GUARD_VALIDATED_MM` is set from JA71's verdict, with no other edit;
    - `HARNESS_VERSION` 1.3.0;
    - the report goldens' version line is regenerated.
  - **Reference implementations:**
    - `experiments/JanusM/Hotel/r5/e11_open_base_remedy.py` (`plane`);
    - `experiments/JanusM/Lima/r5/e1_open_base_remedy.py` (`cap_plane`);
    - `experiments/JanusM/India/r5/b1_band_remedy.py` (`cap_faces`).
  - **Tests:**
    - JA71's rows A–F, with the verdict asserted and the worst error per phantom pinned to ±0.005 mm;
    - D's band is bit-identical to JA61's;
    - on E, at least one opening takes the `normal` form;
    - a lateral epicardial face on label 0, more than 20 mm from any opening, is never removed;
    - the literal remedy's empty epicardial band is pinned as the reason it was not taken;
    - `BIAS_GUARD_VALIDATED_MM == (0.3 if verdict else 0.5)`, with the verdict computed in the test at the default
      settings.
  - **The PR body states the verdict and the guard,** and the PM copies them to #223. If it fails, the guard is
    0.5 mm for r1, and no other variant is tried.
- **R5-S4 — Harness tests that can fail; docstrings (JA79).** *Blocks the first decision-scoring run (with R5-S3).*
  - **Wrong:**
    - `test_validate_bias_estimator_open_base` runs `n_offsets=1` and asserts its own result;
    - the India test leaves the failing epicardial ±0.5 rows unbounded;
    - E4's band test is endocardium only;
    - `signed_bias` says the real-wall error "is not known";
    - the module says 0.03 mm;
    - the transfer check has no mixed-border or exactly-0.05 case.
  - **Correct and tests:**
    - the capsule test runs at the default 3 offsets (marked slow, run in CI) and asserts the verdict that sets the
      constant;
    - until R5-S3 merges, it asserts `passed is False` with worst 0.0504 ± 0.002 mm, and the India test asserts
      every epicardial ±0.5 row in (0.05, 0.075] with worst 0.068 ± 0.003 mm (R5-S3 then replaces both pins);
    - E4 in the band on the epicardium, with two centre jitters;
    - `signed_bias`'s docstring carries "up to 0.05 mm low outward and 0.09 mm high inward near 0.3 mm (India E9)",
      tested by `"0.09" in H.signed_bias.__doc__`;
    - the module says 0.035;
    - transfer: endocardium median 0.04 with epicardium 0.06 → fail, 0.5; a median of exactly 0.05 → pass.

### Group C — reference population and table (`src/janusm/reference.py`, `report.py`, `features.py`, `tests/`)

- **R5-S5 — Fall-backs counted on every read; the header line (JA75).**
  - **Wrong:**
    - `fell` counts only the RC's 20 cases (`reference.py` 611);
    - κ / ICC's reads 21–40 are uncounted;
    - the report header's fall-back note (`report.py` 332–334) is untested.
  - **Correct:** count fall-backs over every read the population uses, reported per use (RC, κ / ICC) and in total,
    in `rc["decisions"]` and the header.
  - **Tests:**
    - a forced fall-back on read 25 is counted;
    - a report built with `segment_territory` dropped has `territory_map == "aha_fallback"`, and the note appears in
      the markdown.
- **R5-S6 — Group C tests end to end (JA79; no code change).**
  - **S7:** a fixture where patients ≠ positions, for n_T and for step 3's χ² switch bound. A LAD SD between the
    values bound and the patients bound stays pooled.
  - **S8:** the relative switch with d and E produced by `case_state`, not built by hand.
  - **S9:** a value-level test that `features.case_features` puts a fat cluster in its patient-map territory, and
    that D moves when that territory changes.
  - **S12:** a phantom in `tests/janusm_synth.py` whose real `geometry.territories(method="geodesic")` majority
    differs on one segment. It is "shared" only with R8 on.
  - **S13:** the round trip through the real export, either by calling `export.readRecord` in the Mongo job, or by
    moving the mapping into one girder-free helper that both the export and `grades_from_read_record` use.
  - **`halves_note`** is tested False as well as True.

### Group D — the read queue (`src/janusm_reads/`, `server/girder_janusm/`, `slicer/JanusMRead/`, `docs/JANUSM-READ-PROTOCOL.md`)

- **R5-S7 — JA66's plane order, final (JA76).** ***Blocks the first read wave.***
  - **Wrong:**
    - a seed or check seed with no fittable 2–4 interface falls through to the read's own gap (`checker.py`
      330–342);
    - a blank case without `checkSeedFileId` is fitted to itself, silently.
  - **Correct:**
    - `mitral_check` takes `queued=True` from `check.py`, which removes the read source;
    - an unfittable seed is "could not be checked" (JA68's path);
    - `check.py` refuses, and alerts on, a blank case with no `checkSeedFileId`;
    - add `populate.py --backfill-check-seeds`;
    - document the step in protocol doc §7.
  - **Tests:**
    - a seed without label 4 → "could not be checked", never source `read`;
    - Mongo: a blank case with no check seed is refused and alerted, with `crashes` + 1 and `returns` unchanged;
    - Mongo: backfill sets `checkSeedFileId`, and the seed is still never served (404).
- **R5-S8 — The bounds check fails closed (JA77).** ***Blocks the first read wave.***
  - **Wrong:** `ctWorldBounds` is None → `points_outside` returns `[]`, and the points are accepted
    (`rest.py` 246–250; `niftihead.py` 118).
  - **Correct:**
    - `points_outside(points, None)` raises;
    - `rest.submit` answers 409 `ct_bounds_unavailable` when there are lesion points and no box;
    - the read stays open, and attempts, returns and crashes are unchanged;
    - the PM is alerted (ERROR log naming the case).
  - **Tests:**
    - Mongo: a case whose CT header cannot be parsed refuses a form with a point (409, no counter moves), and accepts
      a form without points;
    - unit: `points_outside(…, None)` raises.
- **R5-S9 — Wave membership frozen once read (JA78).** ***Blocks the first read wave.***
  - **Wrong:** `adminWave` `$set`s `wave` on any case (`rest.py` 373).
  - **Correct:**
    - 409 for any named case whose wave differs and that has an accepted read, `thirdReadWanted`, or an open third
      read;
    - no partial update: all or none;
    - the same wave again → 200;
    - log every change.
  - **Tests (Mongo):**
    - a case with an accepted read in wave 1 → 409 to wave 2, and nothing moved;
    - an unread case moves;
    - a mixed list → 409, and nothing moved.
- **R5-S10 — `adminThirdReads` checks the report (JA78).** *Blocks opening any third read.*
  - **Wrong:** `rule2.flagged` is taken as sent (`rest.py` 401).
  - **Correct:**
    - recompute `flagged` from the report's seeded rows with `anchoring`'s Rule 2 (shares over seed voxels, strict
      `<` 5 %, strictly more than half), and refuse on disagreement;
    - store the report's sha256 on the wave, and refuse a different report for that wave later;
    - `export` writes the hash.
  - **Tests (Mongo):**
    - a report with `flagged: true` whose rows do not flag → 400;
    - a second, different report for a wave that already has one → 400;
    - the export carries the hash.
- **R5-S11 — Read-queue tests that can fail and that run (JA79).** ***Blocks the first read wave*** (its first
  bullet).
  - **R4-S17 in CI:**
    - add a Mongo test: a genuine failure (`returns` = 1), then a plane-less submission → returned, unflagged,
      `returns` 1, `crashes` 1;
    - and either run `tests/test_janusm_reads.py -k r4s17` in the Mongo job, or move `decide` to a girder-free
      module.
  - **PM alert:** assert the "COULD NOT BE CHECKED" ERROR log for a plane-less read.
  - **S16:** a phantom whose LA shadow exceeds radius + 3 mm, so that `footprintMm` equals the shadow; deleting the
    shadow term must fail it.
  - **S18:**
    - 4.94 % of the union / 5.2 % of the seed, run through `wave_report`, is not "following";
    - exactly 5 % through `wave_report` is not "following" (changing `<` to `<=` must fail it).
  - **S19:**
    - cases with unequal read counts, so that the read-weighted and case-weighted bounds differ, and the shipped
      value is the read-weighted one;
    - the shared-draw contrast calls the implementation with a shared-index stub.
  - **S21:** an export with a competing wave that has accepted reads (`--wave 1` excludes it).
  - **Slicer:** a reopen where the summed `seconds` exceeds the last attempt's alone. The reading clock pauses while
    a check is pending (Lima's note), with a self-test.

### Group E — decision scoring (`tools/janusm/score_decision.py`, `tests/test_janusm_score_decision.py`)

- **R5-S12 — The scorer's union count and tests that exercise d (JA72, JA79).** *Blocks the first decision-scoring
  run.*
  - **Wrong:**
    - read 2 is read 1 in the known-d test, so d's subtraction is never exercised;
    - the 0.5 verdict is shown on fake rows only;
    - the in-list `third` filter (187) is untested;
    - order is checked against the function under test;
    - nothing asserts that the reader key is never written;
    - there is no union count;
    - the `--run` success path and its `.sha256` are untested.
  - **Correct:** add `transfer_check.n_cases_over_limit` (the union over comparisons and borders, first 20; no
    ids).
  - **Tests:**
    - read 2 = read 1 with the epicardium +0.3 mm exactly: d on every row equals the mean model-vs-read pp minus
      read-vs-read pp, within 0.035 mm;
    - a phantom on which vol and pp disagree gives `passed` False and a 0.5 guard;
    - read-vs-read failing alone flips `passed`;
    - `decision_order()` equals `sealed-r1.json["decision"]` as a list (no id printed);
    - an in-list `third: True` record is dropped, and the case still counts on its two reads;
    - no reader id and no key digest appears in the output bytes;
    - a `main --run` success under a stubbed Slurm environment writes the JSON and a matching `.sha256`;
    - an `open` / `nib.load` spy shows no image, mask, label or read file opened before `guard.refuse`, and stderr
      names `HeldOutError` for a held-out id;
    - correct #216's "18 tests" in the test file's header if it is cited.

### Conditional (unchanged)

- **R4-S24 — `build_reference.py --model jm0|jm1`:** only if Janus-M 1 is trained.
- **R4-S25 — The seal scorer takes the frozen size:** only once JA16's sizing PR exists.
- **R4-S26 — Snap tool:** only if R4 fires.

**Not adopted:**
- the #219 remedy as worded (JA70);
- Hotel's `rim15` fall-back, replaced by India's normal rule, which keeps more band and is shown insensitive (b2);
- India's restoring 0.3 mm on phantoms A–B alone (JA71);
- Lima's `force=true` on `admin/wave`;
- Hotel's crash path for an unreadable CT box (JA77);
- Lima's export-manifest hash in place of a recomputed flag (JA78 does both: recompute and store).

---

## 8. What the next round on this path must settle

**The path waits only on the lead's Job JM-0 / JM-0R and on §7's fixes.** Nothing else on it can be argued without
data. If LQ36 (a) is taken, there is no Round 6 build check:
- the PM checks each R5-S item at merge against the test named here;
- R5-S3's PR records JA71's verdict and the guard, which the PM copies to #223.

**The next round opens when JM-0 / JM-0R aggregates are posted.** It then:
1. **Runs `jm0r_decide.py` on the posted aggregates** and records each R0–R10 outcome as the plan's value. R9's depth
   replaces the provisional 45 %. R5-S2 should merge first, so that R9's record is exact in every branch.
2. **Records the guard in force:**
   - JA71's verdict;
   - the transfer check, once the first 20 decision double reads exist (R4-S23 with R5-S12).

After that, everything stays mechanical:
- the decision reads;
- d and the seal size;
- the RC;
- κ / ICC;
- the reference population (360);
- the table.

## Path summary for the lead (for #223)

- **Path A** still delivers a reproducible rest-CCTA geometry table: 17 segments × layers, with a roll-up per artery
  beside the reader's CAD-RADS 2.0 grade.
- **Round 4's 23 fixes all merged with their tests.** Round 5 found four further code defects, all fixed by the
  items above; none has touched a case:
  - a crash on the ruled hypoattenuation input;
  - a mitral check that can still fit itself;
  - lesion points accepted when the CT box is unknown;
  - waves that can be reshuffled after reads.

  Two tests could not fail or never ran; they are hardened.
- **The bias guard is 0.5 mm.** The open-base check failed because the phantom's cut cap adds area without volume.
  A cap-only band passes every phantom the advocates ran. It returns the guard to 0.3 mm only if a pre-registered
  check passes, including a new phantom, and the transfer check on real reads still has the last word. If it does
  not pass, d remains the primary metric (LQ35).
- **Waiting on:** Job JM-0 / JM-0R, §7's fixes (four of them block the first read wave), and the reads.
- **Against `jm/paired-scar`:** unchanged. Path B adds a scar reference this path never has; everything here is its
  Stage A.
