# Round 3, agent "Journals": data journals and article supplements (2026-10-13)

Status: in progress.

## Ingested
| Dataset folder | Source | Tier | Cases | Size | Licence | Notes |
|---|---|---|---|---|---|---|
| `PLOS-Peng2016-CCTA-JPEG` | PLOS ONE 2016 supplement S1–S19 File (figshare 3452651), Peng et al., doi:10.1371/journal.pone.0157490 | T1 | 17 patients (S17, S18 absent from the deposit) | 0.58 GB | CC BY 4.0 | Coronary CTA of FFR patients, Shenzhen Sun Yat-Sen Cardiovascular Hospital 2015 (not the ImageCAS hospital). Released as **8-bit windowed JPEG** slices: not HU (`hu_calibrated=false`), lossy. No spacing in the files: in-plane from the burnt-in 1 cm ruler (0.29–0.38 mm), slice spacing **assumed 0.5 mm** (206–304 slices = at most 160 mm, consistent with a 320-row volume scan). Ruler overlay zeroed. Orientation checked on the preview (anterior up, R on left, superior first). |
| `BMC-BEO2017-SerialStenosis-CCTA` | Biomed Eng Online 2017 "Hemodynamics analysis of the serial stenotic coronary arteries", Additional files 1–2 (springernature figshare 5589196 / 5589220, split RAR) | T1 | 1 patient × 2 phases (`P1_s5` BestDiast 70 %, complete, 112 slices; `P1_s6` BestSyst 40 %, instances 133–206 only) | 0.06 GB | CC BY 4.0 (+CC0 data) | Siemens Definition Flash prospective sequential CCTA, HU, 0.36×0.36×0.5 mm, same hospital/group as the PLOS set. Partial heart coverage (the deposit is missing the first RAR volume). Archive file names carry patient name/dates: never stored. |

## Needs decision (unclear licence)

## Needs account / request

## Dead ends
- GigaScience / GigaDB (DataCite prefix 10.5524, 15 heart/cardiac records): no CT; only a perfusion MRI set and genomics.
- Medical Physics "Library of realistic 4D digital beating heart models" (10.1002/mp.17945): XCAT phantom models, distributed like XCAT (licensed), no CT volumes.
- MedIA 2018 SLAWT left-atrial-wall CT database (Karim et al.): hosted on cardiacatlas.org challenges, which is gone (404).
- figshare 26068273 (LA wall shear stress, Nat Cardiovasc Res): VTK meshes only.
- figshare "cardiac data 1–15" (1375504 … 1378650): byte-identical copies (same MD5) of figshare 1379059, already ingested.
- Zenodo 17048090 (four-chamber heart models from clinical CT): a version of known Zenodo 19351401, meshes only.
- Zenodo 4309958 / 5571925 / 5004620 (bi-atrial SSM, 100 atria) and 4593739 (four-chamber SSM cohort): meshes only.
- Zenodo 10203115 (4D coronary CFD meshes, Sci Rep 2024): STL only.
- figshare 8047742 (CT-FFR benchmark supplement): clinical tables + 1D/3D meshes, no images.
- Data in Brief / Sci Data / GigaScience / Med Phys / JORS dataset articles, Crossref + Europe PMC title/abstract sweep 2015–2026: every cardiac CT dataset paper found is already known (ASOCA, MultiD4CAD, 3C, AVT, ImageTBAD, pig 4D CT, HVSMR is MRI); the rest are tabular data notes (calcified-plaque tables, CCTA vs SPECT tables, peri-aortic fat measurements), X-ray angiography, or phantoms.
- medRxiv crawl (all 112,803 records 2019-06 to 2026-10, title+abstract): no cardiac CT image release beyond ICADD (known, on request).
- Commun Med 2023 LAA 4D-CT flow (PMC9922288), Diagnostics/Front CVM ablation CT segmentation (Zenodo 4309958 = meshes; CT "not permitted for public release"), Tomography 2023 LVEF dose (OSF, images deleted per ethics): no images.
