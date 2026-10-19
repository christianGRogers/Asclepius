---
tags: [plans/experiment, wave-1, A30, A31, D26, D27, seal, statistics, tools]
author: Bridge
round: 9
updated: 2026-10-19
issue: christianGRogers/Asclepius#87
---

# Wave 1: measurement plan and tools

Round 9 pre-registered three measurements on the first team reads (A31). It also asked for a check of the seal
list's patient grouping before wave 1 (A30). The tools exist now, before any read exists, so that wave 1 is
measured exactly as pre-registered. Code: `experiments/Bridge/wave1/`.

**Headline: the A30 grouping check failed.** 60 volumes of sealed patients were outside the D27 seal file (§1).
**Resolved by D32/D33 (2026-10-19, #93):** the seal is now 150 real patients and every one of their 305 volumes,
and the tools defer to the project's guard (`segtrain.pool_seal`).

## 1. A30: the seal's patient grouping, checked against the ingest code

**What was checked.** For every one of the 26 sources, how each pool name was built and what it means for the
patient. Evidence comes from the ingest code, in order of preference:
- `tools/ccta/ingest_open.py`, `ingest_idc.py`, `ingest_aicup.py`, `ingest_totalseg.py`, `round3/*`;
- then the sourcing reports and the QC CSV.

The per-source table, with file:line evidence, is `experiments/Bridge/wave1/a30_qc_per_source.md`. The numbers
are reproduced by `a30_grouping_qc.py` (`a30_grouping_qc_d27.json` for the D27 file; `a30_grouping_qc.json` for the
seal in force).

**Finding: six real patients are under-grouped. No over-grouping was found.**

| Cause | Evidence | Effect |
|---|---|---|
| The four Mendeley-SDN case-report records in `SDN_CASES` (37nnfyh3x9, 4643nn2z44, 7x9kb53262, spb25zt2c4) are **one patient each**. In their names, `sNNN` is a DICOM **series** number, not a subject | `ingest_open.py`: "(one patient) … All cases share patient_id"; `patient_id=f'SDN-{did}'`; `case = f's{series:03d}' + ('_p<phase>' or '_f<frame>')` | The heuristic makes one "patient" per series |
| The `_fNN` frame suffix (one 4D sequence per patient) is **not stripped** | Slicer table: `TruncalValve_4DCT` (21 phases of one adolescent), `CTCardioSeq` (10 phases); "one case per phase (`<name>_fNN`)", `patient_id=name`. Also SDN-4643nn2z44 `s010_fNN` | One "patient" per frame |

**Consequences for the D27 seal** (`sealed_pool_proposal.json`, sha256 `8f529842…1183`):

| | Name heuristic | Ingest-code patients |
|---|---|---|
| Patients in the pool | 517 | **469** |
| Primary-stratum patients | 360 | **312** |
| Sealed primary keys | 150 | **133** real patients. SDN-4643nn2z44 alone takes 10 slots |
| Extension order (150 entries) | 150 | **119** new real patients; 31 entries belong to already-sealed patients |
| Volumes of sealed patients **outside** the seal file | 0 | **60**: SDN-spb25zt2c4 31, SDN-4643nn2z44 13, Slicer TruncalValve_4DCT 8, SDN-37nnfyh3x9 5, SDN-7x9kb53262 2, Slicer CTCardioSeq 1 |

- **Leakage:** a fine-tune that respects the seal file would train on 60 volumes of patients that A10 scores.
- **Power:** at 133 real patients, P(pass a human-level model) is 0.935 if the pool is like ImageCAS val, and
  0.48 if it is 1.5× more varied. At 150 real patients it is 0.964 and 0.58 (`power.py`, Round 9 model).

**Weaker items (no change proposed):**
- IDC RIDER stores some people under two RIDER IDs. RIDER-2522924559 (sealed) and RIDER-2551730224 (extension
  #79) may be one 81-year-old woman: same age and sex, three studies within six weeks. The evidence is
  medium-weak. Merging them would be the cautious choice.
- Figshare-23057000 `PA0`/`PA1`: there is no evidence either way (different reconstructions), so they are kept
  apart as required.
- TotalSegmentator, Kaggle, Taiwan AI CUP, EpicardialFat, SLAWT, CCA200, HOCM, ImageCHD and ImageALCAPA release no
  patient id. They rest on the dataset descriptions (one volume per case id). Byte-identical cross-source
  duplicates are excluded by the ingest's sha256 check.

**Resolution (D32 option A, D33; #93, merged 2026-10-19).**
- `experiments/Bridge/r9/reseal_d32.py` rebuilt the seal from the D27 file (sha256 `8f529842…1183`, at `4469ed4`):
  1. every volume of every sealed real patient is sealed;
  2. D33 merges RIDER-2551730224 into sealed RIDER-2522924559 and drops its extension entry;
  3. 17 patients are topped up from the pre-registered extension order;
  4. the extension order is recomputed on real patients.
- The result is **150 real patients, 305 volumes** (+ 20 ImageCHD), with **0** volumes of a sealed patient
  outside the file (`a30_grouping_qc.py` on the file in force; on the D27 file it gives 61, the 60 plus the
  RIDER twin). The extension order is 101 real patients. The new pinned sha256 is `e71141b4…0690`.
- Power at 150 real patients: 0.964 if the pool is like ImageCAS val, 0.581 if 1.5× more varied.
- After D32 and the 100 reserved extension patients, wave-1 analysis can use **206 volumes from 198 real
  patients**.

**What was done before the decision (kept as the record).**
- The seal file is **not** changed, because it is the D27 acceptance set.
- The finding went to the PM for the lead on 2026-10-19, with a proposed fix as a separate, explicit PR:
  1. seal every volume of the six patients (adds the 60 volumes; keeps the draw);
  2. top up from the pre-registered extension order, skipping entries of sealed patients, until there are 150
     real patients (17 more);
  3. recompute the extension order on real patients.
- Until then, the wave-1 tools refused by the **ingest-code patient** as well as by the file. All 60 volumes
  were refused. #91 made the project's guard do the same, and the tools now use that guard (`common.Seal`).

## 2. What runs on wave 1, on what

Input: the SegQueue14 export of approved reads (`segqueue14-export --replicas all`), **non-sealed volumes
only**. Alongside it:
- the TotalSegmentator seeds (`SegQueue/seeds-totalseg`);
- icx4's predictions on the same volumes;
- TotalSegmentator aortas for the A1 ostium, made with `segtrain aorta` on the read volumes.

```sh
python experiments/Bridge/wave1/score_wave1.py --reads EXPORT --seeds SEEDS --pred ICX4_POOL_PRED \
    --aorta AORTAS --out wave1/per_volume.jsonl --nproc 8 [--skip-sealed]
python experiments/Bridge/wave1/report_wave1.py wave1/per_volume.jsonl \
    --val ICX4_SCORE/per_case.jsonl --out wave1/report        # icx4's own val per-case tF1 (Delta's scorer)
```

**Refusal comes before opening.** `score_wave1.py` checks every export folder name against:
- the seal, through the project's guard (`segtrain.pool_seal`: by volume and by real patient, hash-checked);
- the 100 extension patients the seal could grow into (so an extension never adds already-inspected patients);
- the pool list (an unknown name cannot be proven unsealed).

By default, any hit is an error. `--skip-sealed` skips and counts instead. The report re-checks every row. The
tF1 is the pinned `segtrain.tf1` (A1c hash `24441cf8…5254`), checked at start.

**Scored per volume** (tF1 @ 1.5 mm, per class, flagged classes kept apart (A1b), rows without an aorta marked
provisional (A1a)):

| Comparison | Definition | Feeds |
|---|---|---|
| inter | Read A vs read B, mean of both directions (as `segtrain.reads.inter_read_tf1`) | k; the seed flag |
| model | icx4's prediction against each read, averaged over the reads (A10's left side) | f, k; per source |
| seed | The seed against each read, symmetric, averaged over the reads (definition below) | the seed flag |
| seed edit | Share of each read's voxels outside the seed, and of the seed removed (report only) | reading the seed flag |

**The seed comparison.** The seed is binary, and D26 starts every class as a full copy of it. So it is first
**named with the read's own classes**: each seed voxel takes the class of the nearest read voxel, in mm. Seed
components the reader deleted whole (a vein, a blob) are left out. Naming then agrees by construction, and the
score measures only how much of the kept vessels' **extent** is the seed's: 1.0 means the reader added and
removed nothing.

## 3. What each outcome triggers (A31, applied as written)

All patient-level numbers are on the **primary** stratum (D29: anomalous anatomy and spacing-suspect sets are
reported apart). A patient with several volumes contributes their mean.

| Measurement | Rule | Outcome → action |
|---|---|---|
| **f** = SD(model-vs-read, pool patients) / SD(icx4 val per-case tF1), per class | f > 1.2 in any class | Extend the seal along its pre-registered order **before any sealed read is scored**: to 200, or to 250 if the re-run power at 200 (δ = 0) is below 0.8. If 250 is still under 0.8, report to the lead; the seal grows no further by rule |
| **k** = SD(inter-read) / SD(model-vs-read), per class | k > 1.2 in any class | Same as f |
| Power re-run | `power.p_pass` on icx4's own val distribution with the measured f, k and scorable share, n = 150/200/250, δ = 0 and −0.02 | Sizes the extension; reported in every case |
| **Seed-vs-read** vs inter-read, per class | seed-vs-read ≥ inter-read − 0.02 | Reads are seed-anchored in that class. The A23 diagnostic is reported first beside A10, and Round 9 L5 goes to the lead |
| **Model-vs-read per source**, patient-bootstrap CIs | — | Report only (A31.3); decides nothing at n ≈ 30 |

## 4. Tests, and what they showed about the rules

`pytest experiments/Bridge/wave1` (11 tests, about 10 s) covers:
- the tF1 pin;
- the heuristic reproducing the seal file;
- the real-patient grouping (468 patients after D33; `PA0` and `PA1` apart) and the seal file keyed by it;
- refusal of sealed, reserved, leaked and unknown volumes before any file is opened;
- seed naming (a read equal to the seed scores 1.0 and the deleted vein is ignored; a read that cuts the LAD
  short scores lower in the LAD only);
- the power function reproducing Round 9 (0.966 and 0.58 at n = 150);
- the report's trigger, extension list and seed flag on constructed rows;
- dropping provisional rows and refusing a sealed row.

`selftest.py` runs the whole chain on 24 synthetic patients, each placed under the name of a real open pool
volume:
- tree phantoms beside an aorta;
- a TotalSegmentator-like seed with its own errors and a vein;
- two reads;
- a prediction.

Its output is in `selftest_result.json` and `selftest_WAVE1_*.md`.

| Synthetic wave | Seed-vs-read (LM / LAD / LCx / RCA) | Inter-read | Seed flag | Reads adding nothing to the seed |
|---|---|---|---|---|
| Independent readers | 0.80 / 0.75 / 0.64 / 0.72 | 0.94 / 0.96 / 0.98 / 0.96 | none | 0 of 48 |
| Anchored (reads = seed minus the vein) | 1.0 / 1.0 / 1.0 / 0.71 | 1.0 / 1.0 / 1.0 / 0.71 | all four | 48 of 48 |

A sealed folder placed in the export stopped the scorer before anything was opened.

**Two things the tests taught about the pre-registered rules.** Neither changes a rule; both change how a result
should be read.

1. **The f/k trigger fires often by chance at wave-1 sizes** (`trigger_false_alarm.py`, 20 000 simulations).
   When truly f = k = 1, "f or k > 1.2 in any class" fires:

   | Primary patients | P(fires by chance) |
   |---|---|
   | 30 | 71 % |
   | 50 | 54 % |
   | 100 | 29 % |
   | 150 | 18 % |

   The reason is that eight SD ratios are each estimated from a few dozen patients. The error is the cautious one:
   a larger seal, which costs fine-tuning data, never validity. So it is applied as written. But a triggered
   extension on the first 50 patients is weak evidence that the pool is harder. The report prints this rate and
   the bootstrap CIs beside the verdict. This is Bridge's own rule (v8 §5), and the fault is Bridge's: it should
   have been sized for its false-alarm rate.
2. **The seed flag needs the seed to be clearly worse than a reader.** If the seed were as accurate as a reader,
   seed-vs-read would beat inter-read without any anchoring, because each read is one error from the truth while
   two reads are two errors apart. The first phantom showed exactly this. The flag is sound only because the real
   seed is known to be poor: TotalSegmentator scores 70.5 Dice on ImageCAS-X (arXiv 2608.30404, Table 2). That is
   why the report adds the **edit sizes**. Anchoring shows as reads that add nothing to the seed and remove only
   whole components; a good seed with independent readers would not look like that.

## Limits

- No real read, seed or prediction was available here. Every number in §4 is synthetic. The code paths were
  exercised; the effect sizes mean nothing.
- The seeds are on Girder (`SegQueue/seeds-totalseg`) and were not fetched. The real-seed run is the first wave-1
  run itself.
- f uses icx4's val per-case tF1 as the denominator. Until icx4 has been scored, the self-test uses run 1's
  (another model and convention).
