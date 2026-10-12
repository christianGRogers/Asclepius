# CCTA sourcing, round 2 (2026-10-12): IMMEDIATE DOWNLOADS ONLY

The project lead wants more CT scans showing the coronary arteries, labels not needed, and this round
targets ONLY sources that can be downloaded right now with no request, no DUA, no approval wait.
(A free account with a click-through licence is acceptable only if no human approval is involved —
but you must not create accounts yourself; just note it.) Quality bar is low: the lead said "don't be
too strict on quality". Any contrast-enhanced CT where the coronaries are visible counts.

## Already found — do NOT re-report these (they are ingested or already requested)
ImageCAS / ImageCAS-X and every mirror or derivative of them; ImageCHD; CHD68; ImageALCAPA;
HOCMvalvesSeg; ImageTAAD; ImageTBAD; Kaggle younesselbrag "Coronary Artery Diseases Random Samples";
Kaggle victorsix HeartSR; Vascular Model Repository (vascularmodel.com); Figshare 1379059
"cardiac ct data_15sets"; Mendeley 9wv3fkxstx; OsiriX demo; IDC/TCIA incidental cardiac CT
(RIDER Lung PET-CT, NSCLC Radiogenomics AMC-015/027, VAREPOP-APOLLO AP-26JK, TCGA-OV); ASOCA and its
Kaggle copies; CAT08 and its copies; MM-WHS and its copies; CARE 2024/2026; orCaScore; MultiD4CAD;
CSM_CCTA (arXiv 2609.00909); Coronary Atlas; ICADD; MIDRC; RSNA PE; INSPECT; CT-RATE; 3C COVID cardiac
CT (Zenodo 10801492); AVT; AortaSeg24; SegTHOR; SCAPIS; Stanford AIMI catalogue.
Full detail: /home/user/ccta/vault/Research/Datasets and benchmarks/CCTA sourcing 2026-10/ (summary +
agent reports/*.json). Read the summary first so you don't duplicate.

## Tiers
T1 ECG-gated CCTA; T2 other contrast cardiac CT (coronaries visible); T3 non-gated contrast chest/aortic
CT where coronaries are partly visible. T3 IS WANTED this round if openly downloadable (report counts
and size; the lead will decide on T3 volume). Exclude non-contrast, MRI, X-ray, ultrasound.

## Deliverable
`round2/<YourName>.json` (same fields as round 1: name, url, tier, n_scans {number, unit}, est_size_gb,
format, labels, license, access, steps_to_access, provenance/duplicates, verified, notes) and
`round2/<YourName>.md` (ranked, URLs cited). For EVERY open T1/T2 source (and T3 sources > 50 scans),
download one file/series (≤ 1 GB), confirm it is contrast CT of the chest/heart (aortic root/LV blood
pool ~250–600 HU, or note if not HU-calibrated), record the exact download URL pattern and how to
enumerate all cases (file list API, manifest, index page), then delete it. Put tests under
`round2/tmp_<YourName>/`; never hold more than 2 GB; local disk is ~8 GB free and shared.

## Rules
Verify, don't guess; mark unverified claims. Never create accounts, sign, or request anything. Never
upload anywhere, never touch Girder, never run git. Note licences (NC / ND / redistribution) precisely.
Be polite to servers. Today is 2026-10-12.
