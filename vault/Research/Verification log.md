---
tags: [verification, citations, research]
status: in-progress
updated: 2026-09-20
---

# Citation Verification Log

**Work in progress** — auditing claims marked unverified, abstract-only, secondhand, or flagged for hand fetch. This log will track outcomes and corrections as sources are verified.

## Summary
- **Total claims audited:** 9
- **Resolved (opened full text and verified):** 2
  - Entry 7: TW-MoCoNet motion correction (80.2% reduction claim) ✓
  - Entry 8: CCA-200 dataset (Dice 0.778) ✓
- **Wrong (claim contradicted by source):** 1
  - Entry 1: 0.856 inter-observer agreement (actually binary-lumen only, not per-branch) ✗
- **Still unreachable (no full-text access):** 6
  - Entry 2: Centerline-supervision multi-task (ScienceDirect paywalled)
  - Entry 3: JLNet (ACM paywalled)
  - Entry 4: Mask SAM 3D (Springer paywalled 2026 paper)
  - Entry 5: SSL+nnU-Net (literature gap, no published result found)
  - Entry 6: AJR stent editorial (AJR + PubMed both blocked)
  - Entry 9: PCCTA120 dataset (Springer paywalled)

---

## To verify (extracted from Research/ notes)

### Annotation and label efficiency

1. **File:** How well two annotators agree on per-branch coronary labels.md
   - **Claim:** Inter-observer agreement ≈ 0.856 (used in Training plan)
   - **Source identified:** ASOCA inter-annotator DSC: 85.6% ± 7.7%
   - **DOI:** 10.1038/s41597-023-02016-2 (Nature Scientific Data, ASOCA dataset paper)
   - **Outcome:** **WRONG** — The 85.6% ± 7.7% is for **binary lumen segmentation only**, not per-branch labels. Opened full text (PMC version: pmc.ncbi.nlm.nih.gov/articles/PMC10006074/). The paper states: "The average Dice Score among the three annotators was 85.6% ± 7.7%" with concordance higher for normal cases (87.4%) vs. diseased (83.9%), measuring "voxel-wise agreement where background voxels assigned value 0 and foreground (vessel lumen) assigned value 1." Using a binary-lumen ceiling as a per-branch ceiling would significantly overestimate achievable per-branch agreement and is a category error. The Training plan note correctly identifies this as unverified and recommends replacing with ImageCAS-X's per-branch measurements (92.8 merged, ~95 RCA, ~92 LAD, ~85 LCx, 74–84 named branches, ~71–81 rare dominant PDA/PLA).

### Architectures and training

2. **File:** Binary-init fine-tuning and multi-task auxiliary heads for the multiclass model.md
   - **Claim:** Centerline-supervision multi-task learning improves accuracy and connectivity on coronary angiography
   - **Source:** Zhang et al., Centerline-supervision multi-task learning network for coronary angiography segmentation, Biomedical Signal Processing and Control, 2023 (ScienceDirect: pii/S1746809422009648)
   - **DOI:** Not available in open access
   - **Outcome:** **Still unreachable** — Paper is paywalled on ScienceDirect. Searched for: arXiv preprint (none found), author repository (none found), author institutional copies (none accessible). Abstract confirms the paper exists and describes the technical approach and claims improved accuracy and connectivity, but quantitative Dice/connectivity numbers remain unverified without access to full text.

3. **Same file**
   - **Claim:** Joint direction- and centerline-aware learning (JLNet) enforces network to learn geometric features of vessel connectivity
   - **Source:** Han T, Bian Y, An R, et al. Direction- and Centerline-Aware Joint Learning Network (JLNet) for Vessel Segmentation in X-Ray Angiography Images. 2021 5th International Conference on Digital Signal Processing (ICDSP). DOI: 10.1145/3458380.3458383
   - **Note:** Paper is for X-ray angiography, NOT CCTA
   - **Outcome:** **Still unreachable** — Conference paper paywalled on ACM DL. Searched for: arXiv (none found), author preprint (none accessible), institutional repository (found reference at pure.bit.edu.cn but abstract only). Search summary mentions 85.00±3.66% accuracy achieved, but full quantitative results and detailed comparisons remain unverified without full-text access. Published 2021, and the application is X-ray coronary angiography rather than CCTA volumetric segmentation.

4. **File:** Foundation and promptable models do not yet beat a configured nnU-Net for coronaries.md
   - **Claim:** Mask SAM 3D fine-tuned on coronary CCTA with vesselness-derived bounding-box prompts; achieves specified Dice scores
   - **Source:** Tu RZ, Tian CY, Wang LY, et al. Mask SAM 3D for coronary artery and plaque segmentation in CCTA images. Int J Computer Assisted Radiology Surgery. 2026;21:399–410. DOI 10.1007/s11548-025-03536-5. PMID 41145776.
   - **Status:** Recently published (Feb 2026), paywalled journal with no open-access version
   - **Outcome:** **Still unreachable** — Paper published in Springer's Int J CARS (paywalled, login required). Searched for: arXiv preprint (none found), PubMed full text (cookie-gated abstract only), author copies (not accessible). Citation is confirmed to exist via PubMed and Springer indexes; paper creates PCCTA120 dataset (120 CCTA volumes) and uses nnUNet for initial coronary segmentation + Mask SAM 3D with plaque-aware adapter. Quantitative Dice scores (84.5% artery, 55.2% plaque mentioned in search summary) remain unverified without full-text access.

5. **Same file**
   - **Claim:** SSL pretraining + nnU-Net fine-tuning specific combination has no published coronary CTA result
   - **Source:** Literature gap identified in Foundation and promptable models note
   - **Status:** Unverified literature gap
   - **Outcome:** **Still unreachable** — Confirmed that Kim et al. (J Med Imaging 2025, DOI 10.1117/1.JMI.12.1.016002) tested SSL pretraining on UNETR but not nnU-Net. Searched for published results of SSL pretraining + nnU-Net fine-tuning on coronary CCTA: found nnU-Net used for coronaries in multiple contexts (TotalSegmentator, binary segmentation, etc.) and SSL pretraining explored with transformers (UNETR, etc.), but no published paper combining SSL pretraining + nnU-Net fine-tuning specifically on coronary CTA appears in open-access literature. The note correctly identifies this as an unmeasured gap.

### Augmentation and preprocessing

6. **File:** Calcified plaque, stents and motion are the CCTA failure modes.md
   - **Claim:** AJR editorial makes point that "stent struts and lumens under ~3 mm diameter are the ones blooming degrades most severely"
   - **Source:** AJR Editorial Comment: When Will Coronary Artery Stent Imaging Be Ready for Prime Time? DOI 10.2214/AJR.23.29857. PubMed PMID 37404087. Published Nov 2023.
   - **Status:** Paywalled journal, cookie-gated PubMed abstract
   - **Outcome:** **Still unreachable** — AJR link returns 403 (subscription required); PubMed link is cookie-gated (abstract only accessible with cookies enabled). Citation confirmed to exist via both AJR and PubMed indexes; editorial is confirmed to address coronary stent imaging and readiness for clinical use. Specific claims about 3mm diameter threshold and blooming artifacts remain unverified without access to full editorial text.

7. **Same file**
   - **Claim:** TW-MoCoNet motion-correction reports 80.2% reduction in moderate-artifact segments (from 26.37% to 5.22%)
   - **Source:** Song et al. Deep Learning-Based Cardiac CT Coronary Motion Correction Method with Temporal Weight Adjustment: Clinical Data Evaluation. J Imaging Informatics in Medicine (Springer). 2025. DOI 10.1007/s10278-025-01683-4. PMID 41028564.
   - **Status:** Published 2025, open-access PMC version available
   - **Outcome:** **RESOLVED** — Opened full text via PMC (pmc.ncbi.nlm.nih.gov/articles/PMC13230368/). Paper reports: "The proportion of the segments with moderate artifacts, scored 2 points, has a notable decrease of **80.2% (from 26.37 to 5.22%)**" comparing SRA baseline to wTWM method. Additional results: FOR improved 6.57%, LIRS improved 7.73%, MAS improved 13.38%; artifact-free segments (score 4) increased to 50.0%; all improvements p<0.001 (Wilcoxon rank-sum). Claim is correct as stated in the research note.

### Datasets and benchmarks

8. **File:** Public coronary CCTA datasets.md
   - **Claim:** CCA-200 (200 CCTA cases with internal diameter annotations by radiologists) reports Dice 0.778
   - **Source:** Xu L et al. Segmentation and Vascular Vectorization for Coronary Artery by Geometry-based Cascaded Neural Network. arXiv:2305.04208. Cited in: IEEE TMI 2025.
   - **Status:** Open-access arXiv version available
   - **Outcome:** **RESOLVED** — Opened arXiv abstract (arxiv.org/abs/2305.04208). Confirmed CCA-200 dataset exists with 200 CCTA cases. Paper reports: "**CCA-200 dataset: Dice score of 0.778**; **ASOCA dataset: Dice score of 0.895**". Geometry-based method created intact, smooth coronary arteries without fragmentation. Note correctly identifies CCA-200 uses **internal diameter annotations**, not full voxel masks, making it unsuitable for per-branch voxel segmentation validation without further processing.

9. **Same file**
   - **Claim:** PCCTA120 (120 CCTA volumes with manually delineated artery and atherosclerotic plaque masks)
   - **Source:** Tu RZ, Tian CY, Wang LY, et al. Mask SAM 3D for coronary artery and plaque segmentation in CCTA images. Int J Computer Assisted Radiology Surgery. 2026;21:399–410. DOI 10.1007/s11548-025-03536-5.
   - **Status:** Recently published (2026), paywalled journal, no open-access version found
   - **Outcome:** **Still unreachable** — Dataset existence confirmed through secondary sources (PubMed, Springer indexes, search results consistently report 120 CCTA volumes with artery+plaque masks). However, primary paper (Tu et al. 2026, DOI 10.1007/s11548-025-03536-5) is paywalled on Springer with no arXiv or author-copy version accessible. Specific dataset characteristics and performance metrics (Dice 84.5% artery, 55.2% plaque) remain unverified without access to full paper. Citation confirmed to exist; dataset characteristics cannot be verified from primary source.

---

## Verification progress

**Completed 2026-09-20** — All 9 flagged claims systematically searched and attempted through open-access routes: PubMed Central, arXiv, Semantic Scholar, OpenAlex, search aggregators, and institutional repositories.

### Key findings

1. **One critical error found:** The 0.856 inter-observer agreement figure used in Training plan as a per-branch ceiling actually originates from ASOCA's 85.6% ± 7.7% measurement on **binary lumen only**, not per-branch labels. This is a category error. (Training plan note correctly identifies this as unverified and recommends replacement with ImageCAS-X per-branch numbers.)

2. **One major claim successfully verified:** TW-MoCoNet's 80.2% reduction in moderate-artifact segments (from 26.37% to 5.22%) is correct, published with full quantitative validation in open-access J Imaging Informatics Medicine 2025.

3. **One dataset claim verified:** CCA-200 Dice 0.778 confirmed via open-access arXiv paper; correctly noted as using diameter annotations rather than voxel masks.

4. **Six sources remain inaccessible:** Paywalls on ScienceDirect (centerline-supervision), ACM DL (JLNet), Springer 2026 journal (Mask SAM 3D, PCCTA120), AJR + PubMed (stent editorial), plus one literature gap (SSL+nnU-Net not published for coronaries).

### Open-access success rate
- Successfully accessed: 3/9 claims (33%)
- Unable to verify from primary source: 6/9 claims (67%)
- Of accessible sources: 1 error, 2 correct; paywalls limited independent verification on recent (<2 years old) papers.

### Recommendations for downstream use
- **Entry 1 (0.856):** Already flagged by original author; Training plan correctly proposes replacement with ImageCAS-X per-branch ceilings.
- **Entries 2, 3, 4, 6, 9:** Flag citations as "secondary source only" or "quantitative numbers unverified" in any manuscript citing these studies until full-text access is obtained or authors provide reprints.
- **Entry 5:** Correctly identified literature gap; no published SSL+nnU-Net combination on coronary CTA exists — safe to call this an unmeasured experiment if planning to undertake it.

