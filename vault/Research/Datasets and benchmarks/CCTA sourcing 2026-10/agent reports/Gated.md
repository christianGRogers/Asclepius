# Gated / registration / DUA sources: ranked summary (agent "Gated", 2026-10-12)

**Bottom line.** None of the large gated corpora is a big, easy source of new ECG-gated CCTA. The large CT corpora (INSPECT, RSNA PE, CT-RATE, Merlin) are CTPA (T3), non-contrast or abdominal. The large real CCTA cohorts (SCAPIS, SCOT-HEART, CONFIRM, ISCHEMIA, PROMISE) are restricted to their own countries or available only by collaboration. Ranked by new T1/T2 scans per unit of effort:

| # | Source | Tier | New scans | Effort / wait | Labels shareable? |
|---|--------|------|-----------|---------------|-------------------|
| 1 | **MIDRC** https://data.midrc.org | T1 ~78, T2 ~97 studies (+~6,400 T3 CTPA/CTA chest) | ~175 cardiac | Free login + click-through DUA, ~1 h; every annotator registers individually | **Yes**: DUA cl.10 explicitly allows "annotations and overlays"; images may not be redistributed |
| 2 | **Local LHSC/St Joseph's retrospective CCTA** (Western/Lawson REB) | T1/T2 | likely thousands (unverified) | REB + privacy export, ~2–4 months | If approved and de-identified |
| 3 | **SCAPIS** https://www.scapis.org/how-to-apply/requirements/ | T1 | ~25,000 CCTA (publication figure) | Very high: Swedish PI + Swedish ethics approval + GDPR/confidentiality assessment for a foreign party; fee 6,000 + 45,000 SEK + VAT; BankID download; 6–12 months | No: new variables must be returned to SCAPIS; co-authors from all 6 sites |
| 4 | SCOT-HEART (/2), CONFIRM/CONFIRM2, ISCHEMIA, PROMISE core labs | T1 | 2k–27k each | Collaboration only. BioLINCC releases **tabular data only** for ISCHEMIA/PROMISE | No |
| 5 | **RSNA-STR PE (RSPECT)** https://registry.opendata.aws/rsna-pulmonary-embolism-detection/ | T3 | >12,000 CTPA | Anonymous S3 download (534 GB zip, HEAD tested OK) | Grey zone: "no redistribution of any portion" |
| 6 | **INSPECT** (Stanford AIMI, Redivis) | T3 | 20,078 CTPA (23,248 in paper) | Redivis account + Stanford DUA, approval wait | Needs AIMI written permission |

**Checked and excluded or unavailable:**
- **Stanford AIMI catalogue.** I read all 23 datasets in its sitemap. It has no CCTA. COCA is gated *non-contrast* calcium scoring; the other CT sets are CTPA (INSPECT, RadFusion, the CTPA set) and head CT (SinoCT). https://aimi.stanford.edu/datasets/coca-coronary-calcium-chest-ct
- **CT-RATE** (non-contrast, CC BY-NC-SA). https://huggingface.co/datasets/ibrahimhamamci/CT-RATE
- **Merlin** (abdominal CT).
- **RAD-ChestCT** (reportedly non-contrast).
- **MedTrinity-25M** (2D images aggregated from existing public sets, so duplicates).
- **RSNA challenges since 2020** (cervical spine, abdominal trauma, lumbar MRI, aneurysm, 2026 knee MRI). None is cardiac.
- **UK Biobank** (cardiac MRI only) and **NAKO** (MRI only).
- **MESA and Framingham** (non-contrast calcium CT).
- **EUCanImage/EUCAIM** (cancer only). **Euro-BioImaging** is a service infrastructure, not a dataset.
- **Korean AI-Hub.** No coronary CT dataset turned up in searches. Health data can be analysed only inside the online "safe zone" (no download), and the dataset page states *"내국인만 데이터 신청이 가능합니다"* (only Korean nationals may apply). So a Canadian lab is not eligible. https://www.aihub.or.kr/aihubdata/data/view.do?dataSetSn=71798
- **J-MID** (1.68M CT/MR cases). Access is limited to Japanese JRS member facilities. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12257222/
- **Canadian sources** (OHDP, ICES, CorHealth, CANUE). These hold no images. CIROC in Calgary is mostly cardiac MRI (unverified).

**What the project lead must sign up for (in order):**
1. **MIDRC.** Register at https://data.midrc.org and accept the non-commercial DUA. Each annotator must register as well.
2. **Western REB / Lawson.** Ask the LHSC cardiac CT group whether a retrospective CCTA export is feasible.
3. **Optional, T3 only:** RSNA PE (no sign-up; the terms apply on use) and INSPECT (Redivis + Stanford DUA).
4. **SCAPIS.** Only worth pursuing with an existing Swedish collaborator.

**Verification notes.** The MIDRC counts come from an anonymous public Guppy aggregation of the CT `study_description` field. They are approximate and I downloaded no images. No T1/T2 open-download source fell in this territory, so no download recipe was required. I made no accounts, accepted no DUAs and kept no files. Full details are in `Gated.json`.
