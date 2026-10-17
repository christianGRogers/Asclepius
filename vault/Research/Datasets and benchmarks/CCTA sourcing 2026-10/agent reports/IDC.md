# IDC (NCI Imaging Data Commons): CCTA sourcing summary

Searched with idc-index 0.13.0 (IDC data release v25): 1,044,191 series, 270,830 CT series in 100 collections, 179 collections in total.
I joined the main index with `ct_index` (ScanOptions, kernel, slice thickness) and `contrast_index` (ContrastBolusAgent) and ran regex searches over Study/SeriesDescription, BodyPart, ScanOptions (Siemens `TPxxPC`/`OSCRATE`/`BESTPHASE` ECG tags), ImageType and kernels.
No IDC collection is cardiac by design (none of the collection descriptions mention cardiac or coronary). Every hit below is an incidental scan inside a cancer or COVID collection.

**Bottom line: IDC adds about 17 patient IDs / 18 studies of T1/T2 (~10.7 GB, all CC BY, open download, no login), plus about 293 patients of T3 CTPA/CTA chest.** It is small but clean, and independent of ImageCAS.

## Ranked sources
1. **RIDER Lung PET-CT incidental cardiac CTAs: T1/T2, 13 patient IDs / 14 studies / 16 series, 9.1 GB, CC BY 3.0.**
   GE LightSpeed VCT, 2005-06, 0.625 mm "SS Segment/SS Cine 30-75 BPM" (ECG-gated SnapShot). Most SS Segment series are 10-phase stacks.
   - Coronary CTA studies 2522924559 and 2019259100 were downloaded and show contrast: aortic root about 500-570 HU in 2522924559. In 4767464492 enhancement was weaker (about 230 HU).
   - The four >1 GB CCTA series (2416820556, 7701645091, 1822442188, 2991299498) and 2857227961 were not downloaded; contrast is inferred from the protocol.
   - Most patients are duplicated under two RIDER IDs; I confirmed one pair is pixel-identical, and the manifest keeps one ID per pair.
   - Some cardiac "SS Cine" series are non-contrast calcium scores and were excluded. About 30 "CT CARDIAC CTA CORONARY" studies hold only a timing bolus and are unusable.
   - https://doi.org/10.7937/k9/tcia.2015.ofip7tvm
2. **NSCLC Radiogenomics gated chest CTA: T2, 2 patients (AMC-015, AMC-027), 0.73 GB, CC BY 3.0.** Verified: Isovue 370, Siemens ECG tags, BestDiast/BestSyst at 1 mm, blood pool about 400 HU. https://doi.org/10.7937/k9/tcia.2017.7hs46erv
3. **VAREPOP-APOLLO TAVR cardiac CTA: T2, 1 patient (AP-26JK), 0.81 GB, CC BY 4.0.** Verified: Protocol TAVR, ECG-gated, 0.6 mm. https://doi.org/10.7937/ghkn-md15
4. **TCGA-OV pericarditis gated delayed CT: T2 (marginal), 1 patient, 25 slices at 3 mm, CC BY 3.0.** Verified.
5. **T3, CTPA or CTA chest/aorta: about 316 studies / 293 patients in 24 collections.**
   - Main collections: covid_19_ny_sbu (124 patients, CC BY 4.0; one CTPA verified), midrc_ricord_1b (32) and midrc_ricord_1a (21), both **CC BY-NC 4.0, non-commercial**; lidc_idri (25); acrin_nsclc_fdg_pet (19); covid_19_ar (17).
   - Any contrast chest CT: about 3,600 patients, mostly venous-phase staging scans of low value.

Excluded:
- 4D-Lung: its "GATED" series are respiratory 4D-CT, not cardiac.
- NLST: non-contrast.
- midrc_ricord_1a "CARDIAC CORONARY CTA": only a 3 mm thoraco-abdominal arterial series (counted as T3).

## Tested download recipe (no credentials)
```
pip install idc-index            # bundles s5cmd
S5=$(python -c "import s5cmd,os;print(os.path.join(os.path.dirname(s5cmd.__file__),'bin','s5cmd'))")
$S5 --no-sign-request --endpoint-url https://s3.amazonaws.com run sourcing/IDC_T1T2_manifest.s5cmd   # 24 series, ~10.7 GB
# or, per series:
idc download <SeriesInstanceUID> --download-dir out/
# or in python:
from idc_index import IDCClient; IDCClient().download_from_selection(seriesInstanceUID=[...], downloadDir='out')
```
- The manifest writes `idc_ccta/<collection>/<PatientID>/<SeriesUID>/`.
- The full series list with UIDs, sizes and licences is in `sourcing/IDC_T1T2_series.csv`.
- I tested the s5cmd manifest (on the tcga_ov line), python `download_from_selection` (11 series) and s5cmd `cp` (2 series). Speed was about 20-25 MB/s. All test downloads were deleted.
- Note that disk is about 6 GB free: download the manifest in two halves.
- Attribution: cite each TCIA collection DOI and IDC (Fedorov et al., RadioGraphics 2023).
