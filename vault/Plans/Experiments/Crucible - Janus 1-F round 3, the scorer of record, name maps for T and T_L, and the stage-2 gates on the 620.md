---
tags: [experiment, track-1F, round-3, janus-1F, scorer, gates, stage-2, D45, D47]
author: Crucible
updated: 2026-11-23
issue: christianGRogers/Asclepius#303
candidate: "[[Candidates/Janus 1-F/Crucible v3|Crucible v3]]"
---

# Crucible - Janus 1-F round 3, the scorer of record, name maps for T and T_L, and the stage-2 gates on the 620

## Question

[[Janus 1-F Round 2]] §5 asks round 3 for CPU evidence on four things:
1. Does the scorer of record (Atlas's definitions with SegQueue's collapse) count, on the 620, the same pieces that
   F-A15's lines were simulated on?
2. Does the gates file pass an OM2 recall of 0.61 and fail 0.59?
3. How much disk does one locked case's 13-class npz take, for the chunked predict-and-decode?
4. How often do F-A22's stage-2 measures (L1 theft ≤ 0.02, L2 far paint ≤ 30 mm in ≥ 95 % of cases, K1 ≤ 0.05) fail
   a perfect model, with ImageCAS-X references treated as the prediction?

A fifth question came up while writing the decode: can T, and a later T_L, be built after the probabilities are
deleted?

## Setup

- **Data:** the 620 D45 training label files of ImageCAS-X (Zenodo 10.5281/zenodo.21887809, CC BY 4.0), fetched by
  `experiments/Crucible/j1f_r2/fetch620.py`. It builds the split from the id lists first (pins
  `1350cb1f…1152` / `bbd9c687…5895`) and downloads no other label file. **No CT, no locked, sealed or quality-0
  label, no TotalSegmentator twin, no pool read and no model output.** Nothing ran on a cluster.
- **Code:** `experiments/Crucible/j1f_r3/`.
  - `j1f_scorer.py`: Atlas's round-2 scorer (sha256 `2da3cb1a…886c`) with `collapse4` replaced by
    `segqueue14.labels.collapse_to_four` (pinned `5f69b5be…0a4b`), plus `aggregate`, `load_gates` and `verdict`.
  - `j1f_gates.json`: F-A15's lines.
  - `test_scorer.py`, `test_gates.py`, `decode_ref.py`: the tests.
  - `pass620.py`, `summarise.py`: one pass over the 620.
  - `npz_size.py`: the disk estimate.
- **The stage-2 proxy.** ImageCAS-X traces no stage-2 class, so its traced side branches stand in, per host:
  - D1–D3 for the LAD group (as S1–S3);
  - OM1, OM2 and the ramus for the LCx group (as SN off the LCx);
  - PDA and PLB for the RCA group (as SN, Conus and RMA).
  Each measure was taken on the exact reference and on the reference with the proxies bled one voxel into their parent.
  For K1, the proxies were removed from the "traced" map and the predicted branch was the proxy dilated by one voxel.

## Result

### 1. The scorer of record

- **sha256 `c2786b2ee2228a40eb966d74c1f319963869f7f3196da3af6ff768c9901ca03e`.** Atlas's self-test (extended) and Delta's checks on his six training cases: all pass.
- **Pieces:** all 620 case rows equal Atlas's `census_r2.jsonl`, piece by piece (voxels and length). F-A15 was simulated on exactly these pieces.

| Class | Cases with it | Pieces | Cases with > 1 piece | `census_r2.jsonl`: cases / pieces |
|---|---|---|---|---|
| D1 | 611 | 611 | 0 | 611 / 611 |
| D2 | 359 | 359 | 0 | 359 / 359 |
| OM1 | 540 | 540 | 0 | 540 / 540 |
| OM2 | 229 | 229 | 0 | 229 / 229 |
| PDA | 608 | 676 | 65 | 608 / 676 |
| PLB | 610 | 620 | 10 | 610 / 620 |
| D3 | 47 | 47 | 0 | 47 / 47 |
| Ramus | 149 | 149 | 0 | 149 / 149 |

- **Collapse (F-A17):** 1,296 PDA/PLB components, 0 fallbacks, 0 voxels different from `territory.to_four` outside "Other" and 255.
- **Face contact.** SegQueue counts face contact, Atlas's ring counted 26-neighbours. A branch touching its vessel only diagonally falls back to the RCA, counted. This never happens on the references; on predictions `collect` prints the count.
- **Identity:** recall, naming and presence 1.0 on every piece of every class.
- **One-voxel erosion** (a model one voxel too thin everywhere): 2 of 6 classes fail their lines, by losing whole thin branches.

| Class | Pieces | Recall | Presence agreement | Naming | Passes F-A15 |
|---|---|---|---|---|---|
| D1 | 611 | 0.874 | 0.898 | 1.000 | **no** |
| D2 | 359 | 0.905 | 0.948 | 1.000 | yes |
| OM1 | 540 | 0.867 | 0.900 | 1.000 | yes |
| OM2 | 229 | 0.956 | 0.982 | 1.000 | yes |
| PDA | 676 | 0.766 | 0.921 | 1.000 | **no** |
| PLB | 620 | 0.911 | 0.961 | 1.000 | yes |

### 2. The gates file

`test_gates.py`: 11 of 11 pass. OM2 recall 0.59 fails, 0.60 and 0.61 pass, and a tampered or incomplete file is
refused. Gates sha256 `b4b88e73877e4644825b0aed06a11ae90b00134c1f8fc5441803422c2e7c8e3f`.

### 3. The npz

- Case c0014 (512×512×206), a 13-channel softmax made from its label: **2.39 GB** float32 compressed, 0.44 GB float16, 2.81 GB raw.
- Upper bound from Atlas's measured untrained 5-class npz (1.25 GB) scaled to 13 channels: 3.25 GB.
- **Plan on 3.3 GB per case, ≈ 33 GB per chunk of 10,** deleted before the next chunk (F-A20).

### 4. F-A22's measures on a perfect model

False-fail is the share of 4 000 draws of 100 cases (K1: 20 cases) that cross the line, with F-A22's one-sided 1.25 % bound where it has one.

| Measure | Form | Version | LAD group | LCx group | RCA group | Perfect model fails |
|---|---|---|---|---|---|---|
| L1 theft (pooled; case p90) | nearest-label | exact | 0.0000 (0.0000) | 0.0000 (0.0000) | 0.0000 (0.0000) | 0.0 % |
| L1 theft (pooled; case p90) | nearest-label | bleed1 | 0.0061 (0.0119) | 0.0077 (0.0172) | 0.0056 (0.0106) | 0.0 % |
| L1 theft (pooled; case p90) | proximity (≤ 1.5 mm) | exact | 0.0525 (0.0842) | 0.0548 (0.1053) | 0.0210 (0.0309) | 100.0 % |
| L1 theft (pooled; case p90) | proximity (≤ 1.5 mm) | bleed1 | 0.0648 (0.1028) | 0.0682 (0.1288) | 0.0250 (0.0348) | 100.0 % |
| L2 far paint (median / p95 / max mm; cases ≤ 30 mm) | per voxel | exact | 42.94 / 57.05 / 67.22 mm | 8.6 % of cases | | point rule 100.0 %; with a lower bound 100.0 % |
| L2 far paint (median / p95 / max mm; cases ≤ 30 mm) | per voxel | bleed1 | 43.04 / 57.06 / 67.33 mm | 8.6 % of cases | | point rule 100.0 %; with a lower bound 100.0 % |
| L2 far paint (median / p95 / max mm; cases ≤ 30 mm) | per component (gap) | exact | 0.35 / 0.4 / 0.5 mm | 100.0 % of cases | | point rule 0.0 %; with a lower bound 0.0 % |
| L2 far paint (median / p95 / max mm; cases ≤ 30 mm) | per component (gap) | bleed1 | 0.35 / 0.4 / 0.45 mm | 100.0 % of cases | | point rule 0.0 %; with a lower bound 0.0 % |
| K1 leak (mean over the 620; case p95; the 20 fit-check cases) | all proxies | exact | 0.0000 | 0.0000 | 0.0000 | 0.0 % |
| K1 leak (mean over the 620; case p95; the 20 fit-check cases) | all proxies | dilate1 | 0.0096 | 0.0166 | 0.0082 | 0.0 % |
| K1 per group (mean; case p95) | per group | dilate1 | 0.0137 (0.0264) | 0.0150 (0.0368) | 0.0062 (0.0126) | 0.0 % |

- **L1:** a proximity form counts every ostium as theft and fails a perfect model; the nearest-label form stays under 0.008 even with a one-voxel bleed.
- **L2:** a per-voxel form measures a branch's length (median 42.94 mm), not a detached blob, and fails a perfect model; the per-component gap is ≤ 0.5 mm.
- **K1:** a one-voxel-blurred perfect branch leaks 0.010 of its voxels into the traced lumen on average, far under 0.05.
- **Limit:** this measures false-fail only. The traced branches are a stand-in for septals, SN, conus and RMA, and no leaking model was simulated, so power is not measured here.

### 5. Name maps

`decode_ref.py` (12 of 12 pass):
- Three uint8 maps per case hold the argmax inside each of F-A19's naming sets: {LAD, D1, D2, D3}; {LCx, OM1, OM2,
  Ramus, PDA, PLB}; {RCA, PDA, PLB}. They are kept only on Janus 0's foreground and where 1 − p_bg ≥ 1e-3, and are 0
  elsewhere, where a territory voxel takes its trunk class.
- Any four-class territory map named from them is **bit-equal** to the same reading computed from the probabilities.
- So T (Janus 0's territories) and T_L (1-L's, which may only exist later) need no npz.
- A left PDA inside Janus 0's LCx territory is named PDA. Delta v2's LCx set (no PDA/PLB) fails this test, as it
  should.
- `splits_final` refuses a locked id as val, which is L-A21's leak.

## What it changes

- **F-A16:** the scorer's sha256 can be posted: `c2786b2ee2228a40eb966d74c1f319963869f7f3196da3af6ff768c9901ca03e`. **F-A15's lines need no re-freeze**: the pieces
  are the simulated ones, row for row.
- **F-A15:** `configs/janus1/j1f_gates.json` can be copied byte-identically from this branch.
- **F-A20:** `decode` should also write the name maps. They make T_L possible after the npz is deleted, and
  compress to almost nothing because they are kept only near the predicted tree.
- **F-A22:** keep 0.02, 30 mm, 95 % and 0.05, but write L1 in its **nearest-label** form and L2 in its **per-component**
  form. In the other two forms a perfect model fails.
- **Convergence:** with these, every §5 item of the round-2 ruling has an answer that does not wait on a cluster run.
  See [[Candidates/Janus 1-F/Crucible v3|Crucible v3]] §8.
