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

{{NOTE_SCORER}}

### 2. The gates file

`test_gates.py`: 11 of 11 pass. OM2 recall 0.59 fails, 0.60 and 0.61 pass, and a tampered or incomplete file is
refused. Gates sha256 `b4b88e73877e4644825b0aed06a11ae90b00134c1f8fc5441803422c2e7c8e3f`.

### 3. The npz

{{NOTE_NPZ}}

### 4. F-A22's measures on a perfect model

{{NOTE_ITEM5}}

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

- **F-A16:** the scorer's sha256 can be posted: `{{SCORER_SHA}}`. **F-A15's lines need no re-freeze**: the pieces
  are the simulated ones, row for row.
- **F-A15:** `configs/janus1/j1f_gates.json` can be copied byte-identically from this branch.
- **F-A20:** `decode` should also write the name maps. They make T_L possible after the npz is deleted, and
  compress to almost nothing because they are kept only near the predicted tree.
- **F-A22:** keep 0.02, 30 mm, 95 % and 0.05, but write L1 in its **nearest-label** form and L2 in its **per-component**
  form. In the other two forms a perfect model fails.
- **Convergence:** with these, every §5 item of the round-2 ruling has an answer that does not wait on a cluster run.
  See [[Candidates/Janus 1-F/Crucible v3|Crucible v3]] §8.
