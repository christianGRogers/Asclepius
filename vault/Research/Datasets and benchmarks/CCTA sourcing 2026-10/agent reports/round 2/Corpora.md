# Round 2, "Corpora" agent: general open CT corpora with cardiac or contrast-chest CT inside (2026-10-12)

Territory: large, openly downloadable general CT collections, and whether their per-scan metadata lets
us pull out contrast cardiac or chest CT. Structured detail is in `Corpora.json`. Per-case HU results
and metadata are in `tmp_Corpora/ts/` (no images are kept).

## Bottom line

**The one real find is TotalSegmentator v2.0.1: 130 contrast cardiac and thoracic-aorta CTs, open,
CC BY 4.0, ~1.7 GB, selectable from `meta.csv`. It is independent of ImageCAS, Guangdong and TCIA.**
The catch: every image was resampled to **1.5 mm isotropic**, and many are cropped to the heart. That
leaves the proximal and mid coronaries visible but blurred. Call it T2 (low-res). Everything else in
this territory is T3 venous-phase volume, a duplicate of TCIA/IDC data, or a dead end.

## Ranked sources

| # | Source | Tier | Contrast scans | Size | Licence | Access | Verified |
|---|---|---|---|---|---|---|---|
| 1 | **TotalSegmentator v2.0.1** cardiac subset ([Zenodo 10047292](https://zenodo.org/records/10047292); per-case mirror [HF MedOtter/totalsegmentator-cardiac](https://huggingface.co/datasets/MedOtter/totalsegmentator-cardiac)) | T2 (1.5 mm) | **130** of 144 cardiac-labelled studies | ~1.7 GB | CC BY 4.0 | open | all 144 measured |
| 1b | same corpus, angiography whole-body / TAP | T3 | 67 (mostly arterial) | ~3 GB | CC BY 4.0 | open | 9 measured |
| 1c | same corpus, other thorax-covering studies | T3-low | ~230 estimated (mostly venous) | ~8 GB | CC BY 4.0 | open | 83 of ~440 measured |
| 2 | [Kidney abnormality thorax-abdomen CT (Radboudumc), Zenodo 8014290](https://zenodo.org/records/8014290) | T3-low (venous) | 215 | 38 GB | CC BY 4.0 | open | 1 viewed |
| 3 | [autoPET FDG-PET-CT-Lesions (TCIA)](https://www.cancerimagingarchive.net/collection/fdg-pet-ct-lesions/) | T3-low (venous, 3 mm) | 952 series / 854 patients | ~283 GB | CC BY 4.0 | open (NBIA API) | 1 measured |
| 4 | [MSD Task06_Lung](http://medicaldecathlon.com/) | T3 (mixed) | ~60 of 96 (estimate) | 9.2 GB | CC BY-SA 4.0 | open | 3 viewed; duplicate of TCIA NSCLC-Radiogenomics |
| 5 | [AortaSeg-60, Zenodo 18147026 (2026)](https://zenodo.org/records/18147026) | T3 (aortic CTA) | 50 (40 arterial + 10 venous) | 15.9 GB | CC0 | open | README only; download failed (Zenodo TLS errors) |
| 6 | [FUMPE CTPA, figshare 4107803](https://figshare.com/collections/_/4107803) | T3 (CTPA) | 35 | 1.6 GB | CC BY 4.0 | open | 1 measured |
| 7 | [ChestPathCT5-S100, Zenodo 18256797 (2026)](https://zenodo.org/records/18256797) | T3 | ~20-40 (20 PE CTPA) | 9.4 GB | CC0 | open | listing only |

### 1. TotalSegmentator: how to select and fetch

- **Selection.** Use `meta.csv` (semicolon-separated, inside the zip) and its `study_type` column.
  Results by study type, as contrast scans / total:

  | study_type | Contrast / total |
  |---|---|
  | `ct heart-thorakale aorta` | 41 / 46 |
  | `ct aortic valve` (TAVI CTA) | 33 / 34 |
  | `ct heart` | 28 / 34 |
  | `ct angiography thorax` | 14 / 14 |
  | `ct left artrium` (pre-ablation LA CTA) | 13 / 13 |
  | `ct coronary arteries` | 0 / 3 (non-contrast calcium scans; drop them) |

  The full list of 130 contrast IDs, plus the 14 non-contrast IDs to skip, is in `Corpora.json`
  (notes field) and `tmp_Corpora/ts/card_ids.json`.
- **Verification.** Each case was downloaded, the median HU was measured inside its own aorta and
  left-atrium masks, and the file was deleted.
  - The median over the 130 contrast cases is about 400 HU; 124 are at or above 250 HU.
  - All are Siemens scanners: Flash, Edge, AS+, Force.
  - I viewed `s0738`: a heart-cropped CTA with dense left-heart contrast, the aortic root and the
    proximal coronaries.
- **Download, fast route (tested at ~8 MB/s).**
  `https://huggingface.co/datasets/MedOtter/totalsegmentator-cardiac/resolve/main/<id>/ct.nii.gz`.
  Enumerate cases with `https://huggingface.co/api/datasets/MedOtter/totalsegmentator-cardiac`. The
  mirror's HU values are identical to the Zenodo zip (checked on s0671).
- **Download, official route.** One 23.6 GB zip:
  `https://zenodo.org/api/records/10047292/files/Totalsegmentator_dataset_v201.zip/content`.
  It supports range requests, so `remotezip` can extract `meta.csv` and `<id>/ct.nii.gz` alone
  (tested). Ranges run at only ~0.3 MB/s and drop TLS now and then.
- **Caveats.**
  - The images are 1.5 mm resampled; the original thin slices are not public.
  - TS-v2 has no coronary label.
  - Duplicates: Zenodo 16274177 (TAVRP-PL, 578 TS scans with TAVR pseudo-labels), several HF
    mirrors, and Academic Torrents (v1).

### 2-7. T3 notes

- **Radboud kidney set.** Portal-venous thorax-abdomen CT. Case 184 viewed (1.5 mm, 594 mm z-range).
- **autoPET.** Pick series with `p.v.` in SeriesDescription; 61 others are "nativ" (non-contrast).
  - Enumerate: `getSeries?Collection=FDG-PET-CT-Lesions&Modality=CT`.
  - Fetch: `getImage?SeriesInstanceUID=` on the NBIA v1 API.
  - Blood pool is ~150-200 HU. Probably already inside the IDC agent's "~3,600 venous" bucket.
- **MSD Lung.** Contrast lung-cancer CTs, 0.6-1.25 mm. These are TCIA patients, so not new.
- **AortaSeg-60.** New and CC0, but untested. The institution is not named.
- **FUMPE.** 1 mm CTPA from a NeuViz 16 scanner, `ContrastBolusAgent=C+`.

## Dead ends and duplicates (confirmed)

- **CADS (22k CT, HF `mrmrx/CADS-dataset`).** Re-hosts 28 public sets (NLST, STOIC, LIDC, KiTS…);
  nothing new. HF "auto" gate needs a free account.
- **AbdomenAtlas 1.1/3.0.** Abdomen; metadata shows 403 arterial-phase scans out of 9,262.
  CC BY-NC-SA.
- **SAROS.** Labels on TCIA scans; images come from IDC/TCIA collections already covered.
- **Abdomen only:** AMOS, AbdomenCT-1K, FLARE, KiTS, WORD, BTCV, CT-ORG (CT-ORG's chest share was not
  checked).
- **Other no's:** HECKTOR, LIDC/LUNA (mostly non-contrast).
- **CTRG-Chest-548K volumes (HF).** uint8, windowed, no spacing; not HU.
- **M3D-Cap.** Radiopaedia 8-bit PNG stacks; returns 401 without an HF login.
- **Account needed (none created):** BIMCV-R / BIMCV-COVID19+, and CAD-PE (IEEE DataPort, 91 CTPA).
- **RadGenome-ChestCT** is CT-RATE, already covered.

## Housekeeping

All test downloads were deleted; `tmp_Corpora/` holds only metadata and HU tables (~1 MB). The
largest single file held was the 88 MB autoPET series. My scripts are in `scripts_Corpora/`.
Note: I briefly moved, then restored, files that belong to another agent in `round2/scripts/`
(that directory was recreated at 19:08).
