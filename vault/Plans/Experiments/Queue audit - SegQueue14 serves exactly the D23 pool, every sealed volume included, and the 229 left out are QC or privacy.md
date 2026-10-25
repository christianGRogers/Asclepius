---
tags: [plans/experiment, segqueue14, D22, D23, D27, D29, D32, D35, A33, A34, pool, audit]
author: researcher
updated: 2026-10-25
issue: christianGRogers/Asclepius#126
---

# Queue audit: SegQueue14 serves exactly the D23 pool, every sealed volume included, and the 229 left out are QC or privacy

**Question (#126).** Are the 675 cases SegQueue14 serves on janus exactly the cases the project decided to annotate:
none missing, none extra, none duplicated, each with its CT and seed and the right number of reads?

**Verdict: the queue is right. No case should be added, removed or re-weighted.** Every check the issue asks for
passes. One thing could not be checked from the snapshot (the serve order), and five things are worth the lead's eye.
None of them is a reason to change the queue's membership.

## Setup

- Inputs: the PM's read-only snapshot of janus on 2026-10-25 (`experiments/QueueAudit/snapshot-2026-10-25/`).
  - the queue table (`GET /segqueue14/review/cases`, every page);
  - the item names in `SegQueue/cases` and `SegQueue/seeds-totalseg`.
- Repository files compared against it:
  - `configs/segqueue14/pool-2026-10.txt` (D23);
  - `configs/segqueue14/sealed-pool-2026-10.json` (D27/D32/D33);
  - the ingest QC table (`vault/Research/Datasets and benchmarks/CCTA sourcing 2026-10/QC volume reports.csv`);
  - the five Round 10 D35 draws.
- Patients: `segtrain.pool_seal.ingest_patient`, the project's own rule.
- Script: `experiments/QueueAudit/audit_queue.py`. It writes `audit_2026-10-25.json`, with the sha256 of every input.
  `tests/test_queue_audit.py` pins the headline numbers.
- Method: CPU only, names only. No image, seed or read was opened, and no read exists yet.

## Result

### 1. Queue against the pool list

- **Same set.** The queue has 675 rows, 675 distinct case names and 675 distinct volumes. The pool list has 675
  distinct entries. No name is in one and not the other.
- Every case name is its volume's stem, and every `dataset` is the name's `<Source>` prefix.
- **Reads and state.**
  - Every case wants 2 reads (D11 unlabelled, D23).
  - Approved, active, retired and blind duplicates: all 0. No reference, no prelabel version (seeded, D23/D26).
- **Tiers.** All 675 cases carry tier `new-dataset`, at one priority. That is what `populatePool` writes. D23's three
  blocks are expressed as serve order, not as tiers.
- **The three blocks match QC exactly.**

  | Block | Volumes | Matches QC |
  |---|---|---|
  | QC annotatable | 242 | all QC "yes", none from a spacing-suspect source |
  | QC limited | 359 | all QC "limited", none from a spacing-suspect source |
  | Header spacing suspect | 74 | ImageALCAPA 30, HOCMvalvesSeg 24, CCA200-HF 20 (19 "yes", 55 "limited") |

- **Order: not checkable from this snapshot.**
  - The review endpoint sorts by name and returns no `serveOrder` or priority.
  - `populatePool` sets each case's serve order to its line in the pool list, and `/next` serves by priority, then
    serve order. So the order is right if the populate run used this file. The seal file's
    `pool_list_sha256` (`9f968a08…`) is this file's hash.
  - To confirm on the server: one more read-only pull of `serveOrder` per case. It should equal the line index.

### 2. CT and seed

- All 675 queued volumes have their CT in `SegQueue/cases`.
- All 675 have `<name>__totalseg-coronary.nii.gz` in `SegQueue/seeds-totalseg` (D22/D23 naming).
- The seed folder holds exactly those 675 seeds: none extra, none misnamed.

### 3. The 904 pool CTs and the 229 left out

- **What is in `SegQueue/cases` (1304 items).**
  - 904 pool CTs: exactly the 904 lines of the ingest QC table, no more and no fewer.
  - 200 ImageCAS CTs and 200 `ImageCAS__NNNN__mask` items, the D22 ImageCAS part. D23 queues none of them.
- **Why 229 are left out.** Every one is explained:

  | Reason | Volumes |
  |---|---|
  | QC "not annotatable" | 212 |
  | PLOS-Peng2016: burned-in patient text, pending the lead (QC 16 limited, 1 yes) | 17 |
  | Unexplained | **0** |

- **By source:**

  | Source | Left out |
  |---|---|
  | TotalSegmentator-cardiac | 114 |
  | ImageCHD | 27 |
  | IDC-rider_lung_pet_ct | 21 |
  | PLOS-Peng2016-CCTA-JPEG | 17 (pending) |
  | Slicer-SampleData | 16 |
  | Mendeley-SDN-spb25zt2c4 | 13 |
  | Figshare-EpicardialFat-CE | 6 |
  | HOCMvalvesSeg | 3 |
  | IDC-varepop_apollo | 3 |
  | VMR-Coronary | 3 (including the two corrupt 0157 SVGD_1/_2) |
  | Zenodo-STOPSTORM | 3 |
  | BMC-BEO2017 | 1 |
  | IDC-nsclc_radiogenomics | 1 |
  | Mendeley-SDN-4643nn2z44 | 1 |

  The full per-volume list is `3_left_out.left_out_list` in the JSON.
- **What QC saw in the 212.** In 181 the coronaries are not visible, or barely visible, in a full-heart field of
  view. The rest have a partial heart, no heart, or no contrast.
- **None should be in the queue.**
  - No QC "no" volume is queued, and no QC "yes"/"limited" volume is missing except PLOS.
  - PLOS is the lead's privacy decision (QC report). If the lead clears it, 17 volumes would join after the current
    675.
  - Every source D23 includes is in the queue. PLOS is the only source QC kept that the queue lacks.

### 4. Real patients behind the 675 volumes

- **468 patients**, the seal file's own count.
  - By stratum: 311 primary, 83 ImageCHD (report-only, D29), 74 spacing-suspect (excluded from A10 until re-gridded,
    D29).
  - 59 patients have more than one volume.
- **By source (patients / volumes):**

  | Source | Patients | Volumes |
  |---|---|---|
  | Taiwan-AICUP | 100 | 100 |
  | ImageCHD | 83 | 83 |
  | Mendeley-SDN-cy54ttk3fj | 40 | 80 |
  | Figshare-EpicardialFat-CE | 34 | 34 |
  | ImageALCAPA | 30 | 30 |
  | VMR-Coronary | 30 | 30 |
  | Kaggle-CAD | 28 | 28 |
  | HOCMvalvesSeg | 24 | 24 |
  | CCA200-HF | 20 | 20 |
  | TotalSegmentator-cardiac | 16 | 16 |
  | Figshare-CardiacCT15 | 15 | 15 |
  | IDC-RIDER | 13 | 69 |
  | Kaggle-HeartSR | 10 | 10 |
  | SLAWT2016 | 9 | 9 |
  | Slicer-SampleData | 3 | 16 |
  | Figshare-23057000 | 2 | 2 |
  | IDC-nsclc | 2 | 3 |
  | Mendeley-SDN-spb25zt2c4 | 1 | 34 |
  | Mendeley-SDN-4643nn2z44 | 1 | 23 |
  | Mendeley-SDN-7x9kb53262 | 1 | 23 |
  | Mendeley-SDN-37nnfyh3x9 | 1 | 12 |
  | IDC-varepop | 1 | 9 |
  | Mendeley-9wv3fkxstx | 1 | 2 |
  | BMC-BEO2017, Figshare-DCM3, Zenodo-AtrialFibre | 1 each | 1 each |

- **The seal is fully in the queue.**
  - All 150 primary sealed patients (305 volumes) and all 20 sealed ImageCHD patients (20 volumes) are queued.
  - All 170 scoring volumes are queued.
  - No queued volume of a sealed patient is missing from the seal file.
  - So every sealed patient will get its two reads, and acceptance can be scored.
- **The extension order and the D35 draws.** All 101 extension-order entries are queued, all primary, none sealed.
  Every patient of every draw is queued, none is sealed, and all are primary:

  | Draw | Patients | Volumes | In extension 1–100 | Entry 101 |
  |---|---|---|---|---|
  | **Delta (A33, adopted subject to Q1)** | 35 | 51 | 23 | 0 |
  | Atlas (fallback if Q1 is declined) | 35 | 42 | 0 | 1 |
  | Bridge (Q1 option b) | 35 | 47 | 14 | 0 |
  | Crucible (not adopted) | 35 | 47 | 23 | 1 |
  | Foxtrot (refused) | 50 | 72 | 50 | 0 |

- **Accounting under A33 (Delta's draw; the A34 reserve is the extension order minus D35, 78 patients):**

  | Group | Patients | Volumes | Reads |
  |---|---|---|---|
  | Sealed, primary (A10) | 150 | 305 | 610 |
  | Sealed, ImageCHD report-only | 20 | 20 | 40 |
  | D35 decision set | 35 | 51 | 102 |
  | Reserve (A34) | 78 | 106 | 212 |
  | Open primary | 48 | 56 | 112 |
  | Open ImageCHD | 63 | 63 | 126 |
  | Open spacing-suspect | 74 | 74 | 148 |
  | **Total** | **468** | **675** | **1350** |

  - This reproduces Round 10's numbers: 244 allowed volumes, 325 sealed and 106 reserved refused.
- **Accounting under the Atlas fallback (reserve = extension order 1–100):**
  - sealed 150 + 20, the same as above;
  - D35 35 patients, 42 volumes, 84 reads;
  - reserve 100 patients, 144 volumes, 288 reads;
  - open primary 26 patients, 27 volumes, 54 reads;
  - open ImageCHD and spacing-suspect as above.
- **Frozen until the lead answers Q1:** 135 patients and 186 volumes. That is the union of the three Q1 draws and the
  whole extension order.

### 5. The read budget (1350)

- **Sealed: 650 reads (48 %).** 610 primary and 40 ImageCHD.
- **D35: 102 reads** (Atlas fallback: 84).
- **Reserve: 212 reads** (Atlas fallback: 288).
- **Open: 386 reads** (Atlas fallback: 328).
  - 112 open primary (Atlas fallback: 54);
  - 126 ImageCHD;
  - 148 spacing-suspect.
- Before A35 sizes the seal, only the open primary and open ImageCHD reads are trainable under A33's definition:
  **238 reads**. The spacing-suspect reads are held until re-gridding.

### 6. Other findings (none changes the queue's membership)

1. **A rotated volume is a D35 scoring volume.**
   - `VMR-Coronary__0157_H_CORO_SVGD_0` is the scoring volume of a Delta D35 patient. The QC report flags it as
     rotated 180° in the axial plane. It is the patient's only usable volume (`_1` and `_2` are corrupt and left out).
   - `VMR-Coronary__0148_H_CORO_SVGD` has the same flag, and its patient is reserve (extension position 81).
   - Reads and predictions share the voxel grid, so scoring stays consistent. But Janus 0 has never seen an
     upside-down chest, so this patient may measure orientation rather than the recipe question D35 asks.
   - Options for the lead: fix the orientation before the case is read (a `role:swe` job), or keep the case and
     report it as flagged. Nothing in the queue needs to change for either.
2. **14 queued volumes show no visible coronaries in QC**, and D13 refuses any read with LAD, LCx or RCA empty.
   - The volumes: 13 ImageCHD (1005, 1023, 1030, 1037, 1043, 1070, 1075, 1109, 1110, 1127, 1132, 1139, 1141) and
     `Mendeley-SDN-spb25zt2c4__s018_p75`. That is 28 reads.
   - An annotator who cannot see the vessels can only release such a case. The only way out of the queue is a
     reviewer's `retire`.
   - Three are sealed: ImageCHD 1075 and 1141 are report-only scoring volumes, and s018_p75 belongs to a sealed
     patient (not its scoring volume).
   - This is expected to touch only the ImageCHD report-only stratum and one phase of one patient. It is worth
     telling reviewers that retiring with a reason is the intended outcome there.
3. **`ImageCHD__1129`** is a sealed report-only scoring volume. QC notes "z spacing worth checking", but it is not
   in D29's spacing-suspect set. The impact is low (report-only), but its tF1 should be read with that note.
   (`ImageCHD__1126`, flagged with it, is QC "no" and left out.)
4. **Duplicates.**
   - No two queued names collide, even with case and punctuation ignored.
   - Every near-duplicate QC names is another phase or series of the same ingest patient:
     - RIDER-1563443119 CINE ×3 and RIDER-2522924559;
     - the single-patient Mendeley-SDN records 37nnfyh3x9, spb25zt2c4, 7x9kb53262 and 4643nn2z44;
     - the Slicer TruncalValve frames.
   - So none crosses a seal, D35 or training boundary.
   - Byte-identical volumes under two names cannot be ruled out from names alone. A size or checksum column in the
     next pull would settle it.
5. **Orientation "unclear":** ImageCHD 1022 and 1030 (possible left-right flip or dextrocardia) and
   Mendeley-SDN-7x9kb53262 s010_p15 and p90 (sealed patient).
   - A real left-right header flip would put the left and right coronaries on the wrong sides for annotators. This
     is worth one look by the lead or a reviewer before those cases are read.

## What it changes

- **Nothing in the queue.** Its membership, seeds and reads are what D22, D23, D27/D32/D33, D29 and A33/A34 say.
- **Open items for the lead (via the PM):**
  1. One more read-only pull of `serveOrder` (and file size) per case, to close the order and duplicate checks.
  2. Decide on VMR 0157 SVGD_0 (D35 scoring volume) and VMR 0148 (reserve): fix the orientation before reading, or
     keep them and report them as flagged.
  3. Tell reviewers that the 14 cases with no visible coronaries may need `retire` under D13. Three are sealed.
  4. PLOS-Peng2016 (17) stays out until the lead's privacy decision. If cleared, it is appended after the 675.
